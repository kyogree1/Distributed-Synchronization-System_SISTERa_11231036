from locust import HttpUser, task, between

class DistributedSystemUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://localhost:8003"  # ← Tambahkan baris ini

    @task
    def check_locks(self):
        self.client.get("/locks/state")

    @task
    def acquire_release_lock(self):
        self.client.post("/locks/acquire", json={
            "resource": "res-A",
            "client_id": "cli-locust",
            "mode": "exclusive"
        })
        self.client.post("/locks/release", json={
            "resource": "res-A",
            "client_id": "cli-locust"
        })

    @task
    def queue_publish_consume(self):
        pub = self.client.post("/queue/publish", json={
            "topic": "orders",
            "payload": {"from": "locust", "val": 1}
        })
        self.client.post("/queue/consume", json={
            "topic": "orders",
            "visibility_timeout_sec": 5
        })
