import asyncio
import random
from dataclasses import dataclass
from typing import List, Optional, Callable
from src.utils.config import settings
from src.utils.metrics import raft_role, raft_term

FOLLOWER = 0
CANDIDATE = 1
LEADER = 2

@dataclass
class LogEntry:
    term: int
    command: dict

class RaftNode:
    def __init__(self, node_id: int, peers: list[str], apply_fn: Callable[[dict], None]):
        self.node_id = node_id
        # filter out self by port match (simple heuristic)
        self.peers = [p for p in peers if p != settings.self_url]

        self.apply_fn = apply_fn

        self.state = FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[int] = None
        self.log: List[LogEntry] = []
        self.commit_index = -1
        self.last_applied = -1

        self.leader_hint: Optional[str] = None
        self._reset_election_event = asyncio.Event()
        self._heartbeat_task = None

        raft_role.set(self.state)
        raft_term.set(self.current_term)

    def _rand_timeout(self):
        return random.uniform(settings.election_timeout_min_ms, settings.election_timeout_max_ms) / 1000

    async def start(self):
        asyncio.create_task(self._run_election())

    async def _run_election(self):
        while True:
            self._reset_election_event.clear()
            try:
                await asyncio.wait_for(self._reset_election_event.wait(), timeout=self._rand_timeout())
                continue
            except asyncio.TimeoutError:
                pass

            # become candidate
            self.state = CANDIDATE
            raft_role.set(self.state)
            self.current_term += 1
            raft_term.set(self.current_term)
            self.voted_for = self.node_id
            votes = 1

            for url in self.peers:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as s:
                        async with s.post(f"{url}/raft/request_vote", json={
                            "term": self.current_term,
                            "candidate_id": self.node_id,
                            "last_log_index": len(self.log)-1,
                            "last_log_term": self.log[-1].term if self.log else 0,
                        }, timeout=2) as r:
                            data = await r.json()
                            if data.get("vote_granted"):
                                votes += 1
                except Exception:
                    continue

            if votes >= 2:  # majority of 3
                self.state = LEADER
                raft_role.set(self.state)
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                self._heartbeat_task = asyncio.create_task(self._run_heartbeat())
            else:
                self.state = FOLLOWER
                raft_role.set(self.state)

    async def _run_heartbeat(self):
        while self.state == LEADER:
            for url in self.peers:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as s:
                        await s.post(f"{url}/raft/append_entries", json={
                            "term": self.current_term,
                            "leader_id": self.node_id,
                            "prev_log_index": len(self.log) - 1,
                            "prev_log_term": self.log[-1].term if self.log else 0,
                            "entries": [],
                            "leader_commit": self.commit_index,
                        }, timeout=2)
                except Exception:
                    pass
            await asyncio.sleep(settings.heartbeat_interval_ms/1000)

    # RPC handlers
    def on_request_vote(self, term: int, candidate_id: int, last_log_index: int, last_log_term: int):
        if term > self.current_term:
            self.current_term = term
            raft_term.set(self.current_term)
            self.state = FOLLOWER
            raft_role.set(self.state)
            self.voted_for = None

        vote_granted = False
        my_last_term = self.log[-1].term if self.log else 0
        up_to_date = (last_log_term > my_last_term) or (last_log_term == my_last_term and last_log_index >= len(self.log)-1)
        if term == self.current_term and (self.voted_for in (None, candidate_id)) and up_to_date:
            vote_granted = True
            self.voted_for = candidate_id
            self._reset_election_event.set()
        return {"term": self.current_term, "vote_granted": vote_granted}

    def on_append_entries(self, term: int, leader_id: int, prev_log_index: int, prev_log_term: int, entries: list, leader_commit: int):
        if term < self.current_term:
            return {"term": self.current_term, "success": False}
        self.current_term = term
        raft_term.set(self.current_term)
        self.state = FOLLOWER
        raft_role.set(self.state)
        self.voted_for = leader_id
        self._reset_election_event.set()

        # simple consistency check
        if prev_log_index >= 0:
            if prev_log_index >= len(self.log) or (self.log[prev_log_index].term != prev_log_term):
                return {"term": self.current_term, "success": False}
        for e in entries or []:
            self.log.append(LogEntry(term=self.current_term, command=e))
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log)-1)
            self._apply_commits()
        return {"term": self.current_term, "success": True}

    def _apply_commits(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            cmd = self.log[self.last_applied].command
            try:
                self.apply_fn(cmd)
            except Exception:
                pass

    async def replicate_and_commit(self, command: dict) -> bool:
        if self.state != LEADER:
            return False
        entry = LogEntry(term=self.current_term, command=command)
        self.log.append(entry)
        acks = 1
        for url in self.peers:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as s:
                    async with s.post(f"{url}/raft/append_entries", json={
                        "term": self.current_term,
                        "leader_id": self.node_id,
                        "prev_log_index": len(self.log)-2,
                        "prev_log_term": self.log[-2].term if len(self.log) > 1 else 0,
                        "entries": [command],
                        "leader_commit": self.commit_index,
                    }, timeout=3) as r:
                        data = await r.json()
                        if data.get("success"):
                            acks += 1
            except Exception:
                continue
        if acks >= 2:
            self.commit_index = len(self.log)-1
            self._apply_commits()
            return True
        return False
