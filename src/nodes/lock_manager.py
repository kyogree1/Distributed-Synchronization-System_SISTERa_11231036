from typing import Dict, Set
from fastapi import APIRouter, HTTPException
from src.consensus.raft import RaftNode, LEADER
from src.utils.metrics import locks_total
import src.nodes.base_node as base  # <— IMPORT MODUL, BUKAN VARIABEL

router = APIRouter(prefix="/locks", tags=["locks"])

# In-memory state
LOCK_TABLE: Dict[str, Dict[str, Set[str] | str]] = {}
WAIT_FOR: Dict[str, Set[str]] = {}

def apply_lock_command(cmd: dict):
    t = cmd.get("type")
    if t == "acquire":
        resource = cmd["resource"]
        client = cmd["client_id"]
        mode = cmd["mode"]  # shared|exclusive
        rec = LOCK_TABLE.setdefault(resource, {"holders": set(), "mode": "shared"})
        holders: Set[str] = rec["holders"]  # type: ignore
        cur_mode: str = rec["mode"]  # type: ignore
        if mode == "shared":
            if cur_mode == "exclusive" and len(holders) > 0:
                WAIT_FOR.setdefault(client, set()).update(holders)
            else:
                rec["mode"] = "shared"
                holders.add(client)
        else:
            if (
                (cur_mode == "exclusive" and len(holders) > 0)
                or (cur_mode == "shared" and len(holders) > 0 and (client not in holders or len(holders) > 1))
            ):
                WAIT_FOR.setdefault(client, set()).update(holders)
            else:
                rec["mode"] = "exclusive"
                holders.clear()
                holders.add(client)
    elif t == "release":
        resource = cmd["resource"]
        client = cmd["client_id"]
        rec = LOCK_TABLE.get(resource)
        if not rec:
            return
        holders: Set[str] = rec["holders"]  # type: ignore
        if client in holders:
            holders.remove(client)
            if len(holders) == 0:
                rec["mode"] = "shared"
        WAIT_FOR.pop(client, None)

def _detect_deadlock() -> list[list[str]]:
    visited: Set[str] = set()
    stack: Set[str] = set()
    cycles: list[list[str]] = []

    def dfs(u: str, path: list[str]):
        visited.add(u)
        stack.add(u)
        for v in WAIT_FOR.get(u, set()):
            if v not in visited:
                dfs(v, path + [v])
            elif v in stack:
                cycles.append(path + [v])
        stack.remove(u)

    for n in list(WAIT_FOR.keys()):
        if n not in visited:
            dfs(n, [n])
    return cycles

def _must_leader(raft: RaftNode | None):
    if raft is None:
        raise HTTPException(status_code=503, detail="RAFT not initialized")
    if raft.state != LEADER:
        raise HTTPException(status_code=409, detail="Not leader. Retry on leader node.")

@router.post("/acquire")
async def acquire_lock(body: dict):
    raft: RaftNode | None = base.RAFT  # <— ambil dari modul setiap request
    _must_leader(raft)
    resource = body["resource"]; client_id = body["client_id"]; mode = body.get("mode", "shared")
    ok = await raft.replicate_and_commit({  # type: ignore[arg-type]
        "type": "acquire", "resource": resource, "client_id": client_id, "mode": mode
    })
    locks_total.labels("acquire", mode).inc()
    if not ok:
        raise HTTPException(status_code=500, detail="Replication failed")
    dl = _detect_deadlock()
    return {"status": "ok", "deadlocks": dl, "lock_table": _export_table()}

@router.post("/release")
async def release_lock(body: dict):
    raft: RaftNode | None = base.RAFT
    _must_leader(raft)
    resource = body["resource"]; client_id = body["client_id"]
    ok = await raft.replicate_and_commit({  # type: ignore[arg-type]
        "type": "release", "resource": resource, "client_id": client_id
    })
    locks_total.labels("release", "-").inc()
    if not ok:
        raise HTTPException(status_code=500, detail="Replication failed")
    return {"status": "ok", "lock_table": _export_table()}

@router.get("/state")
async def state():
    return {"locks": _export_table(), "wait_for": {k: list(v) for k, v in WAIT_FOR.items()}}

def _export_table():
    out = {}
    for r, rec in LOCK_TABLE.items():
        out[r] = {"mode": rec["mode"], "holders": list(rec["holders"])}  # type: ignore
    return out
