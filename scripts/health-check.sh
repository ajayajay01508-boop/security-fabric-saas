#!/usr/bin/env bash
# scripts/health-check.sh
# Check health of all running Docker Compose services.

set -uo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

PASS=0; FAIL=0; WARN=0

ok()   { echo -e "  ${GREEN}●${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}●${NC} $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}●${NC} $1"; ((WARN++)); }

http_check() {
    local name="$1" url="$2"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" 2>/dev/null || echo "000")
    [ "$code" = "200" ] && ok "$name ($url)" || fail "$name → HTTP $code"
}

echo -e "\n${CYAN}╔══════════════════════════════════╗${NC}"
echo -e "${CYAN}║  Security Fabric Health Check   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════╝${NC}\n"

# ── Application Services ───────────────────────────────────────
echo "── Application Services ──"
http_check "API Gateway"    "http://localhost:8000/health"
http_check "API Docs"       "http://localhost:8000/docs"
http_check "Dashboard UI"   "http://localhost:5173"

# ── Infrastructure ─────────────────────────────────────────────
echo -e "\n── Infrastructure ──"

# Postgres
PG=$(docker compose exec -T postgres pg_isready -U fabric 2>/dev/null | grep "accepting connections" || echo "")
[ -n "$PG" ] && ok "PostgreSQL (accepting connections)" || fail "PostgreSQL (not ready)"

# Redis
REDIS=$(docker compose exec -T redis redis-cli ping 2>/dev/null | tr -d '\r' || echo "")
[ "$REDIS" = "PONG" ] && ok "Redis (PONG)" || fail "Redis (no PONG: '$REDIS')"

# Kafka
KAFKA=$(docker compose exec -T kafka kafka-broker-api-versions \
    --bootstrap-server localhost:9092 2>/dev/null | grep "ApiVersions" | head -1 || echo "")
[ -n "$KAFKA" ] && ok "Kafka broker (responsive)" || warn "Kafka (could not verify — may still be starting)"

# ── Dev Tools ──────────────────────────────────────────────────
echo -e "\n── Dev Tools ──"
http_check "Kafka UI"   "http://localhost:8080"
http_check "MailHog UI" "http://localhost:8025"
http_check "Grafana"    "http://localhost:3000"
http_check "Prometheus" "http://localhost:9090"

# ── Docker container status ────────────────────────────────────
echo -e "\n── Container Status ──"
SERVICES="postgres redis zookeeper kafka api-gateway ai-detection-engine notification-worker voice-alert-service dashboard-ui"
for svc in $SERVICES; do
    STATE=$(docker compose ps --format json "$svc" 2>/dev/null | python3 -c "import sys,json; [print(r.get('State','unknown')) for r in [json.loads(l) for l in sys.stdin] if r]" 2>/dev/null | head -1 || echo "unknown")
    case "$STATE" in
        running) ok "Container: $svc (running)" ;;
        exited)  fail "Container: $svc (exited)" ;;
        *)       warn "Container: $svc ($STATE)" ;;
    esac
done

# ── Kafka topics ───────────────────────────────────────────────
echo -e "\n── Kafka Topics ──"
for topic in raw-telemetry threat-events alert-notifications voice-alerts; do
    EXISTS=$(docker compose exec -T kafka kafka-topics \
        --bootstrap-server localhost:9092 --list 2>/dev/null | grep "^${topic}$" || echo "")
    [ -n "$EXISTS" ] && ok "Topic: $topic" || warn "Topic: $topic (not found — may need kafka-init)"
done

# ── Summary ────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
TOTAL=$((PASS+FAIL+WARN))
echo -e "  Health: ${GREEN}$PASS OK${NC}  ${RED}$FAIL FAIL${NC}  ${YELLOW}$WARN WARN${NC}  / $TOTAL total"
echo -e "${CYAN}═══════════════════════════════════════${NC}"

if [ "$FAIL" -gt 0 ]; then
    echo -e "\n  ${RED}Some services are unhealthy. Run:${NC}"
    echo "    docker compose logs <service>"
    echo "    make up"
fi
echo ""
exit "$FAIL"
