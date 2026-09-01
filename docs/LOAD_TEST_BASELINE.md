# Local Load-Test Baseline

Measured on commit `cred-sdet-complete` against the FastAPI `/health` route with the full middleware stack, using the repository's threshold-enforcing load harness.

| Parameter | Result |
|---|---:|
| Duration | 5 seconds |
| Concurrent workers | 10 |
| Requests | 3,256 |
| Successful responses | 3,256 (100%) |
| Errors | 0 |
| Throughput | 647.6 requests/second |
| Average latency | 15.4 ms |
| p95 latency | 18.8 ms |
| p99 latency | 90.9 ms |

Command:

```bash
python scripts/load-test.py --url http://127.0.0.1:8765 --workers 10 --duration 5 --scenario health
```

This is a reproducible local health-route baseline, not a claim of production capacity. Results will vary with hardware and deployment configuration.
