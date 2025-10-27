Perfect 🔥
Berikut ini versi lengkap `README.md` (bisa langsung kamu salin ke repo GitHub).
Strukturnya mengikuti standar dokumentasi proyek profesional: ada deskripsi, arsitektur, setup, cara menjalankan, dan semua **testing per langkah (locks, queue, cache)**.

---

# 🧩 Distributed Synchronization System

**Mata Kuliah:** Sistem Paralel dan Terdistribusi
**Judul Tugas:** Implementasi Distributed Synchronization System
**Dibuat oleh:** Muhammad Azka Yunastio
**Institut Teknologi Kalimantan (ITK)**
**Deadline:** 28 Oktober 2025

---

## 📘 Deskripsi Singkat

Proyek ini mengimplementasikan **sistem sinkronisasi terdistribusi** yang mensimulasikan perilaku *real-world distributed systems* menggunakan Python & Docker.

Terdiri atas **3 node FastAPI** yang berkomunikasi melalui **Raft Consensus Algorithm**, dengan dukungan:

* 🧱 **Distributed Lock Manager** — Shared/Exclusive lock + Deadlock Detection
* 📨 **Distributed Queue System** — Consistent Hashing + At-least-once Delivery
* ⚙️ **Distributed Cache Coherence** — Protokol **MESI** dengan invalidasi antar-node
* 🐳 **Containerization** — Multi-node orchestration dengan Docker Compose

---

## ⚙️ Stack Teknologi

| Komponen           | Teknologi                 |
| ------------------ | ------------------------- |
| Bahasa Pemrograman | Python 3.11               |
| Framework          | FastAPI + asyncio         |
| Consensus          | Raft Algorithm (custom)   |
| Storage            | Redis (state persistence) |
| Monitoring         | Prometheus Metrics        |
| Containerization   | Docker + Docker Compose   |

---

## 🧠 Arsitektur Sistem

```
          ┌────────────────────────────┐
          │        Redis Server        │
          │  (State + Queue Storage)   │
          └──────────┬─────────────────┘
                     │
 ┌───────────────────┼─────────────────────┐
 │                   │                     │
 ▼                   ▼                     ▼
┌──────────┐     ┌──────────┐         ┌──────────┐
│  Node 1  │     │  Node 2  │         │  Node 3  │
│ (Follower)│◀──▶│(Follower)│◀──────▶│ (Leader) │
│ Locks     │     │ Queue    │         │ Cache    │
└──────────┘     └──────────┘         └──────────┘
     ▲                ▲                    ▲
     │ REST API       │ REST API           │ REST API
     └────── Clients & Users send requests ┘
```

---

## 🧾 Struktur Folder

```
distributed-sync-system/
├── src/
│   ├── nodes/           ← lock_manager, queue_node, cache_node
│   ├── consensus/       ← raft consensus logic
│   ├── communication/   ← message passing & failure detector
│   └── utils/           ← config & metrics
├── docker/
│   ├── Dockerfile.node
│   └── docker-compose.yml
├── docs/                ← architecture, api_spec, deployment guide
├── benchmarks/          ← load testing script
├── requirements.txt
├── .env.example
├── main.py
└── README.md
```

---

## 🚀 Cara Menjalankan

### **1️⃣ Prasyarat**

Pastikan sudah terinstal:

* [x] **Docker Desktop** (Windows / Mac)
* [x] **Python 3.11+ (opsional, untuk development)**
* [x] Internet aktif untuk build image pertama kali

---

### **2️⃣ Clone Repository**

```bash
git clone https://github.com/azkayunastio/distributed-sync-system.git
cd distributed-sync-system
```

---

### **3️⃣ Setup Environment**

Salin file contoh:

```bash
copy .env.example .env
```

---

### **4️⃣ Build dan Jalankan Semua Node**

```bash
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d
```

---

### **5️⃣ Cek Status Node**

Gunakan command berikut untuk memastikan node aktif:

```bash
docker compose -f docker/docker-compose.yml ps
```

Kemudian uji di browser atau CMD:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

Output contoh:

```json
{"node_id":3,"port":8001,"role":2}   ← berarti node3 adalah LEADER
```

---

## 🌐 Web Interface (Swagger UI)

Setiap node punya Swagger otomatis:

* 🔹 Node 1 → [http://localhost:8001/docs](http://localhost:8001/docs)
* 🔹 Node 2 → [http://localhost:8002/docs](http://localhost:8002/docs)
* 🔹 Node 3 → [http://localhost:8003/docs](http://localhost:8003/docs)

---

## 🧪 Panduan Testing Lengkap

### 🟢 **1. Distributed Lock Manager**

Pastikan kirim request ke **LEADER (role: 2)**
Misal node3 adalah leader → gunakan port 8003.

```bash
:: Acquire EXCLUSIVE lock
curl -X POST http://localhost:8003/locks/acquire -H "Content-Type: application/json" -d "{\"resource\":\"res-A\",\"client_id\":\"cli-1\",\"mode\":\"exclusive\"}"

:: Lihat status lock di semua node
curl http://localhost:8001/locks/state
curl http://localhost:8002/locks/state
curl http://localhost:8003/locks/state

:: Release lock
curl -X POST http://localhost:8003/locks/release -H "Content-Type: application/json" -d "{\"resource\":\"res-A\",\"client_id\":\"cli-1\"}"
```

---

### 🟡 **2. Distributed Queue System**

Queue bisa diuji dari node mana pun (leader atau follower).

```bash
:: Publish 3 pesan
curl -X POST http://localhost:8001/queue/publish -H "Content-Type: application/json" -d "{\"topic\":\"orders\",\"payload\":{\"i\":1}}"
curl -X POST http://localhost:8001/queue/publish -H "Content-Type: application/json" -d "{\"topic\":\"orders\",\"payload\":{\"i\":2}}"
curl -X POST http://localhost:8001/queue/publish -H "Content-Type: application/json" -d "{\"topic\":\"orders\",\"payload\":{\"i\":3}}"

:: Consume pesan via node2 (visibility 10s)
curl -X POST http://localhost:8002/queue/consume -H "Content-Type: application/json" -d "{\"topic\":\"orders\",\"visibility_timeout_sec\":10}"

:: ACK pesan (ganti ID dengan hasil consume)
curl -X POST http://localhost:8002/queue/ack -H "Content-Type: application/json" -d "{\"id\":\"1761580776987-89864\",\"topic\":\"orders\"}"

:: Requeue pesan kadaluarsa
curl -X POST http://localhost:8001/queue/requeue_expired -H "Content-Type: application/json" -d "{\"topic\":\"orders\"}"
```

---

### 🔵 **3. Distributed Cache Coherence (MESI)**

Uji *cache invalidation* antar node.

```bash
:: Set data di node1
curl -X POST http://localhost:8001/cache/set -H "Content-Type: application/json" -d "{\"key\":\"k1\",\"value\":\"v1\"}"

:: Get di node2 (akan MISS)
curl "http://localhost:8002/cache/get?key=k1"

:: Get di node1 (akan HIT)
curl "http://localhost:8001/cache/get?key=k1"
```

## 🧩 Troubleshooting

| Masalah                                    | Penyebab                         | Solusi                                 |
| ------------------------------------------ | -------------------------------- | -------------------------------------- |
| Semua node `role=0`                        | SELF_URL salah di docker-compose | Pastikan tiap node punya SELF_URL unik |
| Error `Internal Server Error` saat acquire | RAFT belum diinisialisasi        | Pastikan pakai `base.RAFT` global      |
| `pipe not found` di Windows                | Docker Desktop belum aktif       | Jalankan Docker Desktop sebelum build  |
| Tidak bisa akses `localhost`               | Port conflict                    | Ubah mapping 8001–8003 di compose      |
| Swagger tidak muncul                       | Build belum selesai              | Jalankan ulang `docker compose up -d`  |

---

## 📈 Monitoring

Endpoint untuk Prometheus metrics:

```
http://localhost:8001/metrics
http://localhost:8002/metrics
http://localhost:8003/metrics
```

---

## 📹 Video Demonstration (Panduan)

Struktur video (10–15 menit):

1. Pendahuluan & Tujuan (1–2 menit)
2. Penjelasan Arsitektur (2–3 menit)
3. Live Demo Locks, Queue, Cache (5–7 menit)
4. Performance Testing (2–3 menit)
5. Kesimpulan & Tantangan (1–2 menit)

---

## 📎 Dokumentasi Tambahan

* Arsitektur & Algoritma → `docs/architecture.md`
* API Spec (Swagger YAML) → `docs/api_spec.yaml`
* Deployment & Troubleshooting → `docs/deployment_guide.md`
* Laporan PDF → `report_[NIM]_MuhammadAzkaYunastio.pdf`

---

## 🏁 Penutup

> “Distributed systems are hard — but they’re also inevitable.”
> – Jeff Hodges

Sistem ini mendemonstrasikan konsep *consistency, replication, dan fault-tolerance* dalam sistem terdistribusi modern dengan implementasi **RAFT + Redis + FastAPI + Docker**.