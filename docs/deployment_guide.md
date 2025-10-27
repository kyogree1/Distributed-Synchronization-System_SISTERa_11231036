# Deployment Guide
1. Salin `.env.example` ke `.env` (opsional; Compose sudah set env per service).
2. Jalankan: `docker compose -f docker/docker-compose.yml up --build`
3. Akses node:
   - Node1: http://localhost:8000/docs
   - Node2: http://localhost:8001/docs
   - Node3: http://localhost:8002/docs
4. Redis tersedia di `redis://localhost:6379/0`.
5. Scale nodes: `docker compose -f docker/docker-compose.yml up --scale node=5` (lihat komentar).
