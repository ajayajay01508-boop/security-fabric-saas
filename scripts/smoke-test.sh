#!/usr/bin/env bash
# scripts/smoke-test.sh
# Run a rapid smoke test against a running local stack.
# Usage: bash scripts/smoke-test.sh [API_URL]

set -euo pipefail

API="${1:-http://localhost:8000}"
CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

PASS=0; FAIL=0

pass() { echo -e "  ${GREEN}✓${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${NC} $1"; ((FAIL++)); }

request() {
    local method="$1" url="$2" expected="$3"
    shift 3
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" "$@" 2>/dev/null || echo "000")
    if [ "$status" = "$expected" ]; then
        pass "HTTP $method $url → $status"
    else
        fail "HTTP $method $url → $status (expected $expected)"
    fi
    echo "$status"
}

echo -e "\n${CYAN}╔═══════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Security Fabric Smoke Tests     ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════╝${NC}\n"
echo -e "Target: ${CYAN}$API${NC}\n"

# ── Health ─────────────────────────────────────────────────────
echo "── Health Checks ──"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API/health" 2>/dev/null || echo "000")
[ "$STATUS" = "200" ] && pass "GET /health → 200" || fail "GET /health → $STATUS (expected 200)"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API/docs" 2>/dev/null || echo "000")
[ "$STATUS" = "200" ] && pass "GET /docs → 200" || fail "GET /docs → $STATUS (expected 200)"

# ── Auth flow ──────────────────────────────────────────────────
echo -e "\n── Auth Flow ──"
EMAIL="smoke_$(date +%s)@test.io"

REGISTER=$(curl -s -X POST "$API/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"smoke1234\",\"full_name\":\"Smoke Test\",\"organization\":\"CI\"}" \
    -w "\n%{http_code}" 2>/dev/null)
REG_STATUS=$(echo "$REGISTER" | tail -1)
[ "$REG_STATUS" = "201" ] && pass "POST /auth/register → 201" || fail "POST /auth/register → $REG_STATUS"

TOKEN_RESP=$(curl -s -X POST "$API/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$EMAIL&password=smoke1234" 2>/dev/null)
TOKEN=$(echo "$TOKEN_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")
[ -n "$TOKEN" ] && pass "POST /auth/token → got JWT" || fail "POST /auth/token → no token"

ME_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API/auth/me" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "000")
[ "$ME_STATUS" = "200" ] && pass "GET /auth/me → 200" || fail "GET /auth/me → $ME_STATUS"

UNAUTH=$(curl -s -o /dev/null -w "%{http_code}" "$API/auth/me" 2>/dev/null || echo "000")
[ "$UNAUTH" = "401" ] && pass "GET /auth/me (no token) → 401" || fail "GET /auth/me (no token) → $UNAUTH"

# ── Alerts ─────────────────────────────────────────────────────
echo -e "\n── Alerts ──"
ALERTS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API/alerts" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "000")
[ "$ALERTS_STATUS" = "200" ] && pass "GET /alerts → 200" || fail "GET /alerts → $ALERTS_STATUS"

STATS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API/alerts/stats" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "000")
[ "$STATS_STATUS" = "200" ] && pass "GET /alerts/stats → 200" || fail "GET /alerts/stats → $STATS_STATUS"

ALERT_404=$(curl -s -o /dev/null -w "%{http_code}" "$API/alerts/99999" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "000")
[ "$ALERT_404" = "404" ] && pass "GET /alerts/99999 → 404" || fail "GET /alerts/99999 → $ALERT_404"

# ── Telemetry ──────────────────────────────────────────────────
echo -e "\n── Telemetry ──"
TEL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/telemetry/ingest" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"source_ip":"1.2.3.4","destination_ip":"5.6.7.8","source_port":12345,"destination_port":80,"protocol":"TCP"}' \
    2>/dev/null || echo "000")
[ "$TEL_STATUS" = "200" ] && pass "POST /telemetry/ingest → 200" || fail "POST /telemetry/ingest → $TEL_STATUS"

TEL_UNAUTH=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/telemetry/ingest" \
    -H "Content-Type: application/json" \
    -d '{"source_ip":"1.2.3.4","destination_ip":"5.6.7.8","source_port":1234,"destination_port":80,"protocol":"TCP"}' \
    2>/dev/null || echo "000")
[ "$TEL_UNAUTH" = "401" ] && pass "POST /telemetry/ingest (no auth) → 401" || fail "POST /telemetry/ingest (no auth) → $TEL_UNAUTH"

# ── Payments ───────────────────────────────────────────────────
echo -e "\n── Payments ──"
SUB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/payments/subscribe" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"plan":"starter"}' 2>/dev/null || echo "000")
[ "$SUB_STATUS" = "200" ] && pass "POST /payments/subscribe → 200" || fail "POST /payments/subscribe → $SUB_STATUS"

PAY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API/payments/status" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || echo "000")
[ "$PAY_STATUS" = "200" ] && pass "GET /payments/status → 200" || fail "GET /payments/status → $PAY_STATUS"

# ── Summary ────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
TOTAL=$((PASS + FAIL))
echo -e "  Smoke tests: ${GREEN}$PASS${NC} passed, ${RED}$FAIL${NC} failed / $TOTAL total"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""
exit $FAIL
