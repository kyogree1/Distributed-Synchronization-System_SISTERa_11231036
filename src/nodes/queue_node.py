import time, json, hashlib
from typing import Any
from fastapi import APIRouter
from redis.asyncio import from_url as redis_from_url
from src.utils.config import settings
from src.utils.metrics import queue_msgs

router = APIRouter(prefix="/queue", tags=["queue"])

def _hash(s: str) -> int:
    return int(hashlib.sha1(s.encode()).hexdigest(), 16)

def _shard(topic: str, ring: list[str]) -> str:
    return ring[_hash(topic) % len(ring)]

REDIS = None
RING = [f"shard:{i}" for i in range(3)]
VIS_PREFIX = "vis:"
META_PREFIX = "meta:"

async def _init_redis():
    global REDIS
    if REDIS is None:
        REDIS = await redis_from_url(settings.redis_url)

@router.post("/publish")
async def publish(body: dict[str, Any]):
    await _init_redis()
    topic = body["topic"]
    payload = body.get("payload", {})
    msg_id = f"{int(time.time()*1000)}-{_hash(json.dumps(payload))%100000}"
    shard = _shard(topic, RING)
    await REDIS.rpush(f"{shard}:{topic}", msg_id)
    await REDIS.hset(f"{META_PREFIX}{msg_id}", mapping={"payload": json.dumps(payload), "topic": topic})
    queue_msgs.labels("publish", topic).inc()
    return {"status": "queued", "id": msg_id, "topic": topic, "shard": shard}

@router.post("/consume")
async def consume(body: dict[str, Any]):
    await _init_redis()
    topic = body["topic"]
    vt = int(body.get("visibility_timeout_sec", settings.queue_visibility_default_sec))
    shard = _shard(topic, RING)
    msg_id = await REDIS.lpop(f"{shard}:{topic}")
    if not msg_id:
        return {"status": "empty"}
    deadline = int(time.time()) + vt
    await REDIS.zadd(f"{VIS_PREFIX}{topic}", {msg_id: deadline})
    meta = await REDIS.hgetall(f"{META_PREFIX}{msg_id}")
    queue_msgs.labels("consume", topic).inc()
    return {"id": msg_id.decode() if isinstance(msg_id, bytes) else msg_id,
            "topic": topic,
            "payload": json.loads(meta.get(b"payload", b"{}"))}

@router.post("/ack")
async def ack(body: dict[str, Any]):
    await _init_redis()
    msg_id = body["id"]
    topic = body["topic"]
    await REDIS.zrem(f"{VIS_PREFIX}{topic}", msg_id)
    await REDIS.delete(f"{META_PREFIX}{msg_id}")
    queue_msgs.labels("ack", topic).inc()
    return {"status": "acked", "id": msg_id}

@router.post("/requeue_expired")
async def requeue_expired(body: dict[str, Any] | None = None):
    await _init_redis()
    topic = (body or {}).get("topic", "*")
    now = int(time.time())
    topics = ["orders","payments","events"] if topic == "*" else [topic]
    moved = 0
    for t in topics:
        expired = await REDIS.zrangebyscore(f"{VIS_PREFIX}{t}", min=0, max=now)
        for msg_id in expired:
            meta = await REDIS.hgetall(f"{META_PREFIX}{msg_id.decode()}")
            if not meta:
                await REDIS.zrem(f"{VIS_PREFIX}{t}", msg_id)
                continue
            shard = _shard(t, RING)
            await REDIS.rpush(f"{shard}:{t}", msg_id)
            await REDIS.zrem(f"{VIS_PREFIX}{t}", msg_id)
            moved += 1
    return {"status": "ok", "requeued": moved}
