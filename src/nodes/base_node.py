from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette_exporter import PrometheusMiddleware, handle_metrics
from src.utils.config import settings
from src.consensus.raft import RaftNode

app = FastAPI(title="Distributed Sync System", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)

RAFT: RaftNode | None = None

@app.get("/health")
async def health():
    return {"node_id": settings.node_id, "port": settings.node_port, "role": getattr(RAFT, "state", -1)}

@app.post("/raft/request_vote")
async def request_vote(body: dict):
    return RAFT.on_request_vote(**body)  # type: ignore

@app.post("/raft/append_entries")
async def append_entries(body: dict):
    return RAFT.on_append_entries(**body)  # type: ignore
