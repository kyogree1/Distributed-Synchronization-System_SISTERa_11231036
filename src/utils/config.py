import os
from pydantic import BaseModel

class Settings(BaseModel):
    node_id: int = int(os.getenv("NODE_ID", "1"))
    node_port: int = int(os.getenv("NODE_PORT", "8001"))
    cluster_nodes: list[str] = os.getenv(
        "CLUSTER_NODES",
        "http://localhost:8001,http://localhost:8002,http://localhost:8003",
    ).split(",")

    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    election_timeout_min_ms: int = int(os.getenv("ELECTION_TIMEOUT_MIN", "1200"))
    election_timeout_max_ms: int = int(os.getenv("ELECTION_TIMEOUT_MAX", "2200"))
    heartbeat_interval_ms: int = int(os.getenv("HEARTBEAT_INTERVAL", "400"))

    cache_max_items: int = int(os.getenv("CACHE_MAX_ITEMS", "512"))
    queue_visibility_default_sec: int = int(os.getenv("QUEUE_VISIBILITY_DEFAULT_SEC", "30"))
    
    self_url: str = os.getenv("SELF_URL", "")

settings = Settings()
