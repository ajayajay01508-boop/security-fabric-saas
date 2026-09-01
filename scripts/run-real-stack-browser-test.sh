#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
export DATABASE_URL="sqlite+aiosqlite:////tmp/security-fabric-browser.db"
export REDIS_URL="redis://127.0.0.1:6379"
export KAFKA_BOOTSTRAP_SERVERS="127.0.0.1:9092"
export JWT_SECRET_KEY="browser-test-secret-key-with-more-than-32-characters"
export SKIP_EXTERNAL_SERVICES=1
export ENVIRONMENT=test
rm -f /tmp/security-fabric-browser.db

cd "$PROJECT_ROOT/apps/api-gateway"
"$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >/tmp/security-fabric-browser-api.log 2>&1 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
        break
    fi
    sleep 1
done
curl -fsS http://127.0.0.1:8000/health >/dev/null

cd "$PROJECT_ROOT/apps/dashboard-ui"
REAL_API_E2E=1 npx playwright test e2e/real-api.spec.ts --project=chromium
