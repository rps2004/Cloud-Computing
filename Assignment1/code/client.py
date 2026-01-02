#!/usr/bin/env python3
"""
Async client for Swarm + Kubernetes testing with summaries and plots.

Outputs:
- Assignment files:
    EE22B171dockerswarm10.txt
    EE22B171dockerswarm<count>.txt
    EE22B171kubernetes10.txt
    EE22B171kubernetes<count>.txt
- Plots:
    EE22B171_<target>_10_plot.png
    EE22B171_<target>_<count>_plot.png

Terminal summary includes requests sent, successes, failures, avg latency, throughput.
"""

import argparse
import asyncio
import time
import statistics
import sys
from typing import List, Tuple
import aiohttp
import matplotlib
matplotlib.use("Agg")   # safe for headless Docker/K8s
import matplotlib.pyplot as plt

# ---------------- Config ----------------
ROLL = "EE22B171"

INPUT_STRINGS_10 = [
    "5PKOHcL6OuxRd0xXHQ",
    "JHfJtHH9",
    "gZFEMAS2JA",
    "NkmPg9jT2uMwWvQ9",
    "lV0NTS",
    "tcmViV3cxd6J794H",
    "SKZpKaksPB1",
    "5ygFfJXEgn7ssgyuS",
    "mvZ5wv7qfk",
    "tD58eeUOLh"
]

DEFAULT_SWARM_URL = "http://localhost:5000/reverse"
DEFAULT_K8S_URL   = "http://localhost:52396/reverse"
DEFAULT_COUNT = 10000
DEFAULT_RATE = 300.0
DEFAULT_CONCURRENCY = 50

# ---------------- Helpers ----------------
def filename_for(target: str, n: int) -> str:
    if target == "swarm":
        return f"{ROLL}dockerswarm{n}.txt"
    elif target == "k8s":
        return f"{ROLL}kubernetes{n}.txt"
    else:
        raise ValueError("unknown target")

def save_plot(latencies: List[float], target: str, n: int):
    """Save response time plot."""
    if not latencies:
        return
    plt.figure(figsize=(8,5))
    plt.plot(range(1, len(latencies)+1), latencies, marker='o' if len(latencies) <= 200 else None)
    plt.xlabel("Request #")
    plt.ylabel("Response Time (s)")
    plt.title(f"Response Times ({target}, {n} requests)")
    plt.grid(True)
    fname = f"{ROLL}_{target}_{n}_plot.png"
    plt.tight_layout()
    plt.savefig(fname)
    plt.close()
    print(f"[INFO] Saved plot: {fname}")

# ---------------- HTTP -------------------
async def post_once(session, url, payload):
    t0 = time.perf_counter()
    try:
        async with session.post(url, json={"text": payload}) as resp:
            resp.raise_for_status()
            data = await resp.json()
        dt = time.perf_counter() - t0
        return True, dt, data.get("reversed", "")
    except Exception:
        return False, None, ""



# ---------------- Worker -----------------
async def worker(session, url, payload, sem, results, failures):
    async with sem:
        ok, rt, _ = await post_once(session, url, payload)
        if ok:
            results.append(rt)
        else:
            failures.append(1)

# ---------------- Run 10 -----------------
async def run_10(session, base_url: str, target: str):
    latencies: List[float] = []
    failures: List[int] = []
    lines: List[str] = []

    print(f"\n[INFO] Running 10-string test for {target}")
    for s in INPUT_STRINGS_10:
        ok, rt, rev = await post_once(session, base_url, s)

        if ok:
            latencies.append(rt)
            lines.append(f"Original: {s}")
            lines.append(f"Reversed: {rev}")   # <-- now use server response
            lines.append("--------------------")
        else:
            failures.append(1)


    avg = statistics.fmean(latencies) if latencies else 0.0
    lines.append(f"average_response_time={avg:.6f}")

    out_file = filename_for(target, 10)
    with open(out_file, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    save_plot(latencies, target, 10)

    print(f"[INFO] 10-string test summary:")
    print(f"  Requests: {len(INPUT_STRINGS_10)}")
    print(f"  Success:  {len(latencies)}")
    print(f"  Failures: {len(failures)}")
    print(f"  Avg latency: {avg:.6f}s")

# ---------------- Run count --------------
async def run_count(session, base_url: str, target: str, count: int, rate: float, concurrency: int):
    print(f"\n[INFO] Running {count}-request test for {target} (rate={rate}/s, conc={concurrency})")
    interval = 1.0 / rate if rate > 0 else 0.0
    sem = asyncio.Semaphore(concurrency)
    results: List[float] = []
    failures: List[int] = []
    tasks = []
    loop = asyncio.get_running_loop()
    t0 = time.perf_counter()

    for i in range(count):
        payload = INPUT_STRINGS_10[i % len(INPUT_STRINGS_10)]
        tasks.append(loop.create_task(worker(session, base_url, payload, sem, results, failures)))
        if interval > 0:
            await asyncio.sleep(interval)

    if tasks:
        await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - t0
    avg = statistics.fmean(results) if results else 0.0
    throughput = (len(results) / elapsed) if elapsed > 0 else 0.0

    out_file = filename_for(target, count)
    with open(out_file, "w", encoding="utf-8") as fh:
        fh.write(f"average_response_time={avg:.6f}\n")

    save_plot(results, target, count)

    print(f"[INFO] {count}-request test summary:")
    print(f"  Requests: {count}")
    print(f"  Success:  {len(results)}")
    print(f"  Failures: {len(failures)}")
    print(f"  Avg latency: {avg:.6f}s")
    print(f"  Elapsed wall time: {elapsed:.3f}s")
    print(f"  Throughput: {throughput:.2f} req/s")

# ---------------- Orchestration ----------
async def run_for_target(session, target: str, url: str, count: int, rate: float, concurrency: int):
    await run_10(session, url, target)
    await run_count(session, url, target, count, rate, concurrency)

# ---------------- Main -------------------
async def main_async(args):
    swarm_session = None
    k8s_session = None

    try:
        # If running against swarm (or both), keep the original default session
        if args.target in ("swarm", "both"):
            swarm_session = aiohttp.ClientSession()

        # If running against k8s (or both), create a k8s-specific session
        # that allows many simultaneous connections per host so kube-proxy/NodePort
        # will distribute TCP connections across pods.
        if args.target in ("k8s", "both"):
            # limit=0 means no global connection limit, limit_per_host sets concurrent connections per host
            k8s_connector = aiohttp.TCPConnector(limit=0, limit_per_host=args.concurrency)
            k8s_session = aiohttp.ClientSession(connector=k8s_connector)

        # Run targets using the appropriate session(s)
        if args.target in ("swarm", "both"):
            await run_for_target(swarm_session, "swarm", args.swarm_url, args.count, args.rate, args.concurrency)

        if args.target in ("k8s", "both"):
            if not args.k8s_url:
                print("[ERROR] --k8s-url required for target=k8s or both", file=sys.stderr)
                return
            await run_for_target(k8s_session, "k8s", args.k8s_url, args.count, args.rate, args.concurrency)

    finally:
        # close sessions cleanly (if they were created)
        if swarm_session is not None:
            await swarm_session.close()
        if k8s_session is not None:
            await k8s_session.close()

# ---------------- CLI --------------------
def parse_args():
    p = argparse.ArgumentParser(description="Async client with concurrency, summaries, and plots")
    p.add_argument("--target", choices=("swarm", "k8s", "both"), default="swarm")
    p.add_argument("--swarm-url", default=DEFAULT_SWARM_URL, help="Swarm endpoint (include /reverse)")
    p.add_argument("--k8s-url", default=DEFAULT_K8S_URL, help="K8s endpoint (include /reverse)")
    p.add_argument("--rate", type=float, default=DEFAULT_RATE, help="Target total requests per second")
    p.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of requests for heavy run")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Max in-flight requests")
    return p.parse_args()

# ---------------- Entrypoint -------------
if __name__ == "__main__":
    args = parse_args()
    print(f"[INFO] Starting client. target={args.target}, count={args.count}, rate={args.rate}/s, concurrency={args.concurrency}")
    t0 = time.perf_counter()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("[INFO] Interrupted by user. Exiting.")
        raise
    total_elapsed = time.perf_counter() - t0
    print(f"\n[INFO] Total wall-clock time: {total_elapsed:.3f}s")
