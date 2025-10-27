from prometheus_client import Counter, Gauge, Histogram

request_latency = Histogram("dss_request_latency_seconds", "Latency of API requests", ["route"])
raft_role = Gauge("dss_raft_role", "Role: 0=follower,1=candidate,2=leader")
raft_term = Gauge("dss_raft_term", "Current term")
locks_total = Counter("dss_locks_total", "Total lock ops", ["op", "mode"])
queue_msgs = Counter("dss_queue_messages", "Queue messages ops", ["op", "topic"])
cache_ops = Counter("dss_cache_ops", "Cache ops", ["op"])
