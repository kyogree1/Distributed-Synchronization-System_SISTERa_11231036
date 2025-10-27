from collections import OrderedDict
from typing import Any, Dict
from fastapi import APIRouter
from src.utils.config import settings
from src.utils.metrics import cache_ops
import aiohttp
import os

router = APIRouter(prefix="/cache", tags=["cache"])

class LRUCache:
    def __init__(self, max_items: int = 256):
        self.store: OrderedDict[str, Any] = OrderedDict()
        self.state: Dict[str, str] = {}
        self.max = max_items

    def get(self, key: str):
        if key in self.store:
            self.store.move_to_end(key)
            return self.store[key]
        return None

    def set(self, key: str, value: Any, state: str):
        self.store[key] = value
        self.store.move_to_end(key)
        self.state[key] = state
        if len(self.store) > self.max:
            self.store.popitem(last=False)

    def invalidate(self, key: str):
        if key in self.state:
            self.state[key] = "I"
        if key in self.store:
            del self.store[key]

CACHE = LRUCache(max_items=settings.cache_max_items)

async def _broadcast_invalidate(key: str):
    peers = os.getenv("CLUSTER_NODES", "").split(",")
    my = f"http://localhost:{settings.node_port}"
    async with aiohttp.ClientSession() as s:
        for url in peers:
            if not url or url == my:
                continue
            try:
                await s.post(f"{url}/cache/invalidate", json={"key": key}, timeout=2)
            except Exception:
                pass

@router.get("/get")
async def get_value(key: str):
    v = CACHE.get(key)
    if v is not None and CACHE.state.get(key) in ("M","E","S"):
        cache_ops.labels("hit").inc()
        return {"status": "hit", "key": key, "value": v, "state": CACHE.state.get(key)}
    cache_ops.labels("miss").inc()
    CACHE.set(key, None, "S")
    return {"status": "miss", "key": key, "value": None, "state": "S"}

@router.post("/set")
async def set_value(body: Dict[str, Any]):
    key = body["key"]; value = body["value"]
    await _broadcast_invalidate(key)
    CACHE.set(key, value, "M")
    cache_ops.labels("set").inc()
    return {"status": "ok", "key": key, "state": "M"}

@router.post("/invalidate")
async def invalidate(body: Dict[str, Any]):
    key = body["key"]
    CACHE.invalidate(key)
    cache_ops.labels("invalidate").inc()
    return {"status": "invalidated", "key": key}
