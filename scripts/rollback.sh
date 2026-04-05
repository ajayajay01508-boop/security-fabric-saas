#!/usr/bin/env bash
# scripts/rollback.sh
# Roll back all deployments in security-fabric namespace to the previous revision.

set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
NS="security-fabric"

echo -e "\n${YELLOW}⚠  Security Fabric Rollback${NC}"
echo -e "Namespace: ${CYAN}$NS${NC}\n"

DEPLOYMENTS=$(kubectl get deployments -n "$NS" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null || echo "")

if [ -z "$DEPLOYMENTS" ]; then
    echo -e "${RED}No deployments found in namespace $NS${NC}"
    exit 1
fi

echo "Deployments to roll back:"
for d in $DEPLOYMENTS; do
    CURRENT=$(kubectl rollout history deployment/"$d" -n "$NS" 2>/dev/null | tail -2 | head -1 | awk '{print $1}')
    echo -e "  ${CYAN}$d${NC} (current revision: $CURRENT)"
done

echo ""
read -rp "Confirm rollback of all deployments? [y/N] " CONFIRM
[ "$CONFIRM" != "y" ] && { echo "Cancelled."; exit 0; }

echo ""
PASS=0; FAIL=0
for d in $DEPLOYMENTS; do
    echo -n "  Rolling back $d... "
    if kubectl rollout undo deployment/"$d" -n "$NS" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
        ((PASS++))
    else
        echo -e "${RED}✗${NC}"
        ((FAIL++))
    fi
done

echo ""
echo "Waiting for rollouts to complete..."
for d in $DEPLOYMENTS; do
    kubectl rollout status deployment/"$d" -n "$NS" --timeout=120s 2>/dev/null || true
done

echo ""
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo -e "  Rollback: ${GREEN}$PASS succeeded${NC}  ${RED}$FAIL failed${NC}"
echo -e "${CYAN}═══════════════════════════════════════${NC}"
echo ""

kubectl get pods -n "$NS"
exit "$FAIL"
