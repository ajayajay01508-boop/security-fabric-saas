#!/bin/bash
set -e
echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

echo "Seeding demo data (if needed)..."
python seed.py || echo "Seed skipped (already done or error)"

echo "Starting API Gateway..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
