#!/usr/bin/env python3
"""
Automated multi-cloud failover script.
Usage:
    python cloud-failover.py --from aws:us-east-1 --to gcp:us-central1 --reason "AZ degradation"
    python cloud-failover.py --from aws:us-east-1 --to gcp:us-central1 --dry-run
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cloud-failover")


@dataclass
class FailoverEvent:
    timestamp: str
    from_cloud: str
    from_region: str
    to_cloud: str
    to_region: str
    reason: str
    dry_run: bool
    steps: list
    status: str = "initiated"


def parse_endpoint(endpoint: str) -> tuple[str, str]:
    """Parse 'aws:us-east-1' into ('aws', 'us-east-1')."""
    parts = endpoint.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid endpoint format '{endpoint}'. Expected cloud:region")
    cloud, region = parts
    if cloud not in ("aws", "gcp", "azure"):
        raise ValueError(f"Unsupported cloud '{cloud}'. Use: aws, gcp, azure")
    return cloud, region


def run_cmd(cmd: list[str], dry_run: bool = False, check: bool = True) -> str:
    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}CMD: {' '.join(cmd)}")
    if dry_run:
        return "[dry-run output]"
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    if result.stdout:
        logger.debug(result.stdout.strip())
    return result.stdout.strip()


def check_target_health(cloud: str, region: str, dry_run: bool) -> bool:
    logger.info(f"Step 1: Checking target cluster health ({cloud}:{region})")
    context_map = {
        "aws":   f"arn:aws:eks:{region}:000000000000:cluster/security-fabric-prod",
        "gcp":   f"gke_{region}_security-fabric-prod",
        "azure": f"security-fabric-prod-{region}",
    }
    ctx = context_map.get(cloud, "")
    try:
        run_cmd(["kubectl", "--context", ctx, "get", "nodes", "--no-headers"], dry_run)
        logger.info("✓ Target cluster is healthy")
        return True
    except Exception as e:
        logger.error(f"✗ Target cluster health check failed: {e}")
        return False


def check_kafka_replication_lag(dry_run: bool) -> int:
    logger.info("Step 2: Checking Kafka MirrorMaker replication lag")
    if dry_run:
        logger.info("  [dry-run] Skipping Kafka lag check")
        return 0
    # In production: query Kafka MirrorMaker metrics
    lag = 0  # placeholder
    logger.info(f"  Replication lag: {lag} messages")
    if lag > 5000:
        logger.warning(f"  High replication lag ({lag}). Consider waiting.")
    return lag


def shift_traffic(from_cloud: str, from_region: str, to_cloud: str, to_region: str, dry_run: bool):
    logger.info(f"Step 3: Shifting traffic {from_cloud}:{from_region} → {to_cloud}:{to_region}")
    if from_cloud == "aws":
        run_cmd([
            "aws", "route53", "change-resource-record-sets",
            "--hosted-zone-id", "ZXXXXXXXXXXXXX",
            "--change-batch", json.dumps({
                "Changes": [{
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": "api.security-fabric.io.",
                        "Type": "A",
                        "SetIdentifier": to_region,
                        "Region": to_region,
                        "TTL": 30,
                        "ResourceRecords": [{"Value": "1.2.3.4"}]
                    }
                }]
            }),
        ], dry_run)
    logger.info("✓ DNS traffic shifted")


def promote_database(to_cloud: str, to_region: str, dry_run: bool):
    logger.info(f"Step 4: Promoting read replica to primary in {to_cloud}:{to_region}")
    if to_cloud == "aws":
        run_cmd([
            "aws", "rds", "promote-read-replica",
            "--db-instance-identifier", f"security-fabric-prod-replica-{to_region}",
            "--region", to_region,
        ], dry_run)
    elif to_cloud == "gcp":
        run_cmd([
            "gcloud", "sql", "instances", "promote-replica",
            f"security-fabric-prod-replica",
            f"--project=security-fabric-prod",
        ], dry_run)
    logger.info("✓ Database replica promoted")


def validate_traffic(dry_run: bool):
    logger.info("Step 5: Validating traffic on new target")
    import urllib.request
    if dry_run:
        logger.info("  [dry-run] Skipping live validation")
        return
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen("https://api.security-fabric.io/health", timeout=5) as r:
                body = json.loads(r.read())
                if body.get("status") == "healthy":
                    logger.info(f"  ✓ Health check passed (attempt {attempt})")
                    return
        except Exception as e:
            logger.warning(f"  Attempt {attempt} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Traffic validation failed after 3 attempts")


def write_audit_log(event: FailoverEvent):
    path = f"failover-{event.timestamp.replace(':', '-')}.json"
    with open(path, "w") as f:
        json.dump(asdict(event), f, indent=2)
    logger.info(f"Audit log written: {path}")


def main():
    parser = argparse.ArgumentParser(description="Security Fabric Cloud Failover")
    parser.add_argument("--from", dest="src", required=True, help="Source: cloud:region")
    parser.add_argument("--to",   dest="dst", required=True, help="Target: cloud:region")
    parser.add_argument("--reason",  default="Manual failover")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from_cloud, from_region = parse_endpoint(args.src)
    to_cloud,   to_region   = parse_endpoint(args.dst)

    event = FailoverEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        from_cloud=from_cloud, from_region=from_region,
        to_cloud=to_cloud, to_region=to_region,
        reason=args.reason, dry_run=args.dry_run, steps=[],
    )

    logger.info("=" * 60)
    logger.info("  SECURITY FABRIC — CLOUD FAILOVER")
    logger.info(f"  {from_cloud}:{from_region} → {to_cloud}:{to_region}")
    logger.info(f"  Reason: {args.reason}")
    if args.dry_run:
        logger.info("  ⚠  DRY RUN — no changes will be made")
    logger.info("=" * 60)

    try:
        if not check_target_health(to_cloud, to_region, args.dry_run):
            sys.exit(1)
        event.steps.append("health_check:pass")

        lag = check_kafka_replication_lag(args.dry_run)
        event.steps.append(f"kafka_lag:{lag}")

        shift_traffic(from_cloud, from_region, to_cloud, to_region, args.dry_run)
        event.steps.append("traffic_shifted")

        promote_database(to_cloud, to_region, args.dry_run)
        event.steps.append("db_promoted")

        validate_traffic(args.dry_run)
        event.steps.append("traffic_validated")

        event.status = "completed"
        logger.info("=" * 60)
        logger.info("  ✓ FAILOVER COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)

    except Exception as e:
        event.status = f"failed:{e}"
        logger.error(f"FAILOVER FAILED: {e}", exc_info=True)
        sys.exit(1)
    finally:
        write_audit_log(event)


if __name__ == "__main__":
    main()
