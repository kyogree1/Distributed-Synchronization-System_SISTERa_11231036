import asyncio
import aiohttp
import time

# -------------------------------
# CONFIGURATION
# -------------------------------
URL = "http://localhost:8003/locks/state"  # Endpoint to test
N = 1000  # Total requests
C = 50    # Number of concurrent requests

success = 0
failed = 0
latencies = []


async def worker(session, idx):
    """Single worker task that sends a GET request and measures latency."""
    global success, failed
    start_time = time.perf_counter()
    try:
        async with session.get(URL) as resp:
            await resp.text()
            if resp.status == 200:
                success += 1
            else:
                failed += 1
    except Exception as e:
        failed += 1
    finally:
        elapsed = (time.perf_counter() - start_time) * 1000  # ms
        latencies.append(elapsed)


async def run():
    """Run benchmark with asynchronous batches."""
    print(f"[INFO] Starting benchmark...")
    print(f"[INFO] Target URL: {URL}")
    print(f"[INFO] Total Requests: {N}")
    print(f"[INFO] Concurrency Level: {C}")
    print("-" * 60)

    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        # Buat list task sebanyak N
        tasks = [worker(session, i) for i in range(N)]
        # Jalankan secara batch agar tidak overload
        for i in range(0, N, C):
            batch = tasks[i:i + C]
            await asyncio.gather(*batch)

    total_time = time.time() - start_time
    avg_latency = sum(latencies) / len(latencies)
    throughput = N / total_time

    print("\nBenchmark Results:")
    print("-" * 60)
    print(f"Total Requests      : {N}")
    print(f"Successful Requests : {success}")
    print(f"Failed Requests     : {failed}")
    print(f"Average Latency     : {avg_latency:.2f} ms")
    print(f"Total Time Taken    : {total_time:.2f} s")
    print(f"Throughput          : {throughput:.2f} req/sec")
    print("-" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n[INFO] Benchmark cancelled by user.")
