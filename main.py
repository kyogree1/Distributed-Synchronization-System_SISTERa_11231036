# D:\... \tugas2sister11231036\main.py
import asyncio
from fastapi import Request
from fastapi.responses import JSONResponse
from src.utils.config import settings
from src.utils.metrics import request_latency
from src.consensus.raft import RaftNode
from src.nodes.base_node import app as base_app
from src.nodes.lock_manager import router as locks_router, apply_lock_command
from src.nodes.queue_node import router as queue_router
from src.nodes.cache_node import router as cache_router

app = base_app
RAFT = RaftNode(settings.node_id, settings.cluster_nodes, apply_fn=apply_lock_command)

@app.on_event("startup")
async def on_startup():
    import src.nodes.base_node as base
    base.RAFT = RAFT
    asyncio.create_task(RAFT.start())

@app.middleware("http")
async def record_latency(request: Request, call_next):
    route = request.url.path
    with request_latency.labels(route).time():
        response = await call_next(request)
    return response

# @app.middleware("http")
# async def inject_raft(request: Request, call_next):
#     if request.method in ("POST","PUT","PATCH") and request.url.path.startswith("/locks"):
#         try:
#             body = await request.json()
#         except Exception:
#             body = {}
#         body["_raft"] = RAFT
#         request._body = JSONResponse(body).body
#         async def receive():
#             return {"type": "http.request", "body": request._body}
#         request._receive = receive
#     return await call_next(request)

app.include_router(locks_router)
app.include_router(queue_router)
app.include_router(cache_router)

@app.get("/")
async def root():
    return {"msg": "Distributed Sync System", "node_id": settings.node_id, "port": settings.node_port}
