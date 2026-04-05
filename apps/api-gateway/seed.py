#!/usr/bin/env python3
"""
Seed the database with demo users and sample alerts.
Usage (from project root):
    docker compose exec api-gateway python seed.py
    # or locally:
    cd apps/api-gateway && python seed.py
"""
import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_db, AsyncSessionLocal
from app.models.user import User
from app.models.alert import Alert, SeverityLevel, AlertStatus
from app.models.subscription import Subscription, PlanType, SubscriptionStatus
from app.core.security import hash_password

DEMO_USERS = [
    {"email": "admin@demo.io",   "password": "demo1234", "full_name": "Admin User",    "organization": "Demo Corp",      "plan": PlanType.PROFESSIONAL},
    {"email": "analyst@demo.io", "password": "demo1234", "full_name": "SOC Analyst",   "organization": "Demo Corp",      "plan": PlanType.STARTER},
    {"email": "free@demo.io",    "password": "demo1234", "full_name": "Free Tier User", "organization": "Startup Inc",   "plan": PlanType.FREE},
]

CLASSIFICATIONS = [
    ("Data Exfiltration",           SeverityLevel.CRITICAL),
    ("Command & Control",           SeverityLevel.CRITICAL),
    ("Ransomware Communication",    SeverityLevel.CRITICAL),
    ("DDoS",                        SeverityLevel.HIGH),
    ("SQL Injection",               SeverityLevel.HIGH),
    ("Lateral Movement",            SeverityLevel.HIGH),
    ("Brute Force SSH",             SeverityLevel.MEDIUM),
    ("DNS Tunneling",               SeverityLevel.MEDIUM),
    ("Port Scan",                   SeverityLevel.LOW),
    ("Anomalous Traffic",           SeverityLevel.LOW),
]

PROTOCOLS = ["TCP", "UDP", "HTTP", "HTTPS", "SSH", "FTP", "DNS"]


def random_ip():
    return f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def make_alert(hours_ago: float) -> dict:
    classification, severity = random.choice(CLASSIFICATIONS)
    status_weights = [AlertStatus.OPEN] * 5 + [AlertStatus.ACKNOWLEDGED] * 2 + [AlertStatus.RESOLVED] * 3
    return {
        "threat_id": str(uuid.uuid4()),
        "severity": severity,
        "status": random.choice(status_weights),
        "classification": classification,
        "source_ip": random_ip(),
        "destination_ip": random_ip(),
        "source_port": random.randint(1024, 65535),
        "destination_port": random.choice([22, 80, 443, 445, 1433, 3306, 3389, 6379, 4444]),
        "protocol": random.choice(PROTOCOLS),
        "confidence_score": round(random.uniform(0.5, 0.99), 3),
        "description": f"Automated detection: {classification} from {random_ip()}",
        "created_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    }


async def seed():
    print("🌱 Seeding database...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Create demo users
        for u_data in DEMO_USERS:
            from sqlalchemy import select
            existing = await db.execute(select(User).where(User.email == u_data["email"]))
            if existing.scalar_one_or_none():
                print(f"   skip existing user: {u_data['email']}")
                continue

            user = User(
                email=u_data["email"],
                hashed_password=hash_password(u_data["password"]),
                full_name=u_data["full_name"],
                organization=u_data["organization"],
                is_active=True,
            )
            db.add(user)
            await db.flush()

            sub = Subscription(
                user_id=user.id,
                plan=u_data["plan"],
                status=SubscriptionStatus.ACTIVE,
            )
            db.add(sub)
            print(f"   ✓ user: {u_data['email']}  plan={u_data['plan']}")

        # Create sample alerts spread over last 7 days
        alert_count = 0
        for hours_ago in [h * 0.5 for h in range(0, 340, 1)]:
            if random.random() < 0.4:  # ~40% chance each slot
                alert_data = make_alert(hours_ago)
                alert = Alert(**alert_data)
                db.add(alert)
                alert_count += 1

        await db.commit()

    print(f"✅ Seed complete: {len(DEMO_USERS)} users, {alert_count} alerts")
    print()
    print("Demo credentials:")
    for u in DEMO_USERS:
        print(f"   {u['email']}  /  {u['password']}  ({u['plan']})")


if __name__ == "__main__":
    asyncio.run(seed())
