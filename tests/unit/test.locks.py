import pytest
from src.consensus.raft import RaftNode
from src.nodes.lock_manager import apply_lock_command

def test_apply_no_crash():
    rn = RaftNode(1, [], apply_fn=apply_lock_command)
    rn.log = []
    rn.current_term = 1
    # simulate one committed entry
    rn.log.append(type("e", (), {"term":1, "command":{"type":"acquire","resource":"r","client_id":"c","mode":"exclusive"}}))
    rn.commit_index = 0
    rn._apply_commits()
    assert True
