#!/usr/bin/env python3
"""
scripts/load-test.py
────────────────────
Pure-stdlib load tester for the Security Fabric API.
No external dependencies (no locust, no k6).

Usage:
    python scripts/load-test.py                        # default settings
    python scripts/load-test.py --url http://localhost:8000 --workers 20 --duration 30
    python scripts/load-test.py --scenario telemetry   # flood telemetry endpoint
    python scripts/load-test.py --scenario auth        # auth endpoint only
    python scripts/load-test.py --scenario full        # all endpoints (default)
"""

import argparse
import json
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Stats:
    total: int = 0
    success: int = 0
    errors: int = 0
    latencies: list = field(default_factory=list)
    status_codes: dict = field(default_factory=lambda: defaultdict(int))
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, latency_ms: float, status: int):
        with self.lock:
            self.total += 1
            self.latencies.append(latency_ms)
            self.status_codes[status] += 1
            if 200 <= status < 300:
                self.success += 1
            else:
                self.errors += 1

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        s = sorted(self.latencies)
        idx = int(len(s) * p / 100)
        return s[min(idx, len(s) - 1)]

    @property
    def avg(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0


def http(method: str, url: str, data: Optional[dict] = None,
         headers: Optional[dict] = None, timeout: float = 10.0) -> tuple[int, float]:
    """Make an HTTP request and return (status_code, latency_ms)."""
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception:
        status = 0

    latency = (time.monotonic() - t0) * 1000
    return status, latency


def get_token(base_url: str) -> Optional[str]:
    """Register a test user and return JWT token."""
    email = f"loadtest_{int(time.time() * 1000)}@test.io"
    try:
        http("POST", f"{base_url}/auth/register", {
            "email": email, "password": "loadtest123",
            "full_name": "Load Test", "organization": "CI"
        })
        body = json.dumps({"username": email, "password": "loadtest123"}).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"username={email}&password=loadtest123".encode()
        req = urllib.request.Request(
            f"{base_url}/auth/token", data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["access_token"]
    except Exception as e:
        print(f"  [warn] Could not get token: {e}")
        return None


TELEMETRY_EVENT = {
    "source_ip": "10.0.0.1",
    "destination_ip": "192.168.1.1",
    "source_port": 54321,
    "destination_port": 80,
    "protocol": "TCP",
    "bytes_sent": 4096,
    "bytes_received": 8192,
    "packets": 20,
    "duration_ms": 150,
}


def worker_loop(base_url: str, scenario: str, token: Optional[str],
                stats: Stats, stop_event: threading.Event):
    auth = {"Authorization": f"Bearer {token}"} if token else {}

    while not stop_event.is_set():
        if scenario == "health":
            status, lat = http("GET", f"{base_url}/health")
        elif scenario == "auth":
            status, lat = http("GET", f"{base_url}/auth/me", headers=auth)
        elif scenario == "alerts":
            status, lat = http("GET", f"{base_url}/alerts", headers=auth)
        elif scenario == "telemetry":
            status, lat = http("POST", f"{base_url}/telemetry/ingest",
                               data=TELEMETRY_EVENT, headers=auth)
        else:  # full
            import random
            choice = random.choice(["health", "auth", "alerts", "telemetry"])
            if choice == "health":
                status, lat = http("GET", f"{base_url}/health")
            elif choice == "auth":
                status, lat = http("GET", f"{base_url}/auth/me", headers=auth)
            elif choice == "alerts":
                status, lat = http("GET", f"{base_url}/alerts", headers=auth)
            else:
                status, lat = http("POST", f"{base_url}/telemetry/ingest",
                                   data=TELEMETRY_EVENT, headers=auth)

        stats.record(lat, status)


def print_progress(stats: Stats, elapsed: float, duration: float):
    rps = stats.total / elapsed if elapsed > 0 else 0
    print(
        f"\r  {elapsed:5.1f}s/{duration}s | "
        f"req={stats.total:6d} | "
        f"ok={stats.success:6d} | "
        f"err={stats.errors:4d} | "
        f"rps={rps:7.1f} | "
        f"p50={stats.percentile(50):6.1f}ms | "
        f"p99={stats.percentile(99):7.1f}ms",
        end="", flush=True
    )


def run_load_test(base_url: str, workers: int, duration: int, scenario: str):
    print(f"\n  Target   : {base_url}")
    print(f"  Scenario : {scenario}")
    print(f"  Workers  : {workers}")
    print(f"  Duration : {duration}s\n")

    # Get auth token for authenticated scenarios
    token = None
    if scenario in ("auth", "alerts", "telemetry", "full"):
        print("  Getting auth token...", end=" ", flush=True)
        token = get_token(base_url)
        print("✓" if token else "✗ (unauthenticated endpoints only)")

    stats = Stats()
    stop_event = threading.Event()

    threads = [
        threading.Thread(
            target=worker_loop,
            args=(base_url, scenario, token, stats, stop_event),
            daemon=True,
        )
        for _ in range(workers)
    ]

    print()
    start = time.monotonic()
    for t in threads:
        t.start()

    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= duration:
                break
            print_progress(stats, elapsed, duration)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n  Interrupted.")

    stop_event.set()
    for t in threads:
        t.join(timeout=2)

    elapsed = time.monotonic() - start
    print_progress(stats, elapsed, duration)
    print("\n")

    # Final report
    rps = stats.total / elapsed if elapsed > 0 else 0
    print("  ─────────────────────────────────────────")
    print(f"  Requests     : {stats.total:,}")
    print(f"  Success      : {stats.success:,}  ({100*stats.success//max(stats.total,1)}%)")
    print(f"  Errors       : {stats.errors:,}")
    print(f"  Throughput   : {rps:.1f} req/s")
    print(f"  Avg latency  : {stats.avg:.1f}ms")
    print(f"  p50 latency  : {stats.percentile(50):.1f}ms")
    print(f"  p95 latency  : {stats.percentile(95):.1f}ms")
    print(f"  p99 latency  : {stats.percentile(99):.1f}ms")
    print(f"  Status codes : {dict(stats.status_codes)}")
    print("  ─────────────────────────────────────────")

    error_rate = stats.errors / max(stats.total, 1)
    if error_rate > 0.05:
        print(f"\n  ⚠  Error rate {error_rate:.1%} exceeds 5% threshold")
        return 1
    if stats.percentile(99) > 2000:
        print(f"\n  ⚠  p99 latency {stats.percentile(99):.0f}ms exceeds 2000ms threshold")
        return 1
    print(f"\n  ✓ Load test passed (error rate={error_rate:.1%}, p99={stats.percentile(99):.0f}ms)")
    return 0


def main():
    p = argparse.ArgumentParser(description="Security Fabric Load Tester")
    p.add_argument("--url",      default="http://localhost:8000", help="API base URL")
    p.add_argument("--workers",  type=int, default=10, help="Concurrent workers")
    p.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    p.add_argument("--scenario", default="full",
                   choices=["health", "auth", "alerts", "telemetry", "full"],
                   help="Which endpoint(s) to hammer")
    args = p.parse_args()

    print("╔═══════════════════════════════════════════╗")
    print("║   Security Fabric — Load Test             ║")
    print("╚═══════════════════════════════════════════╝")

    rc = run_load_test(args.url, args.workers, args.duration, args.scenario)
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
