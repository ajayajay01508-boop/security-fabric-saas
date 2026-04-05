#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${CYAN}[setup]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# ─── Check prerequisites ──────────────────────────────────────
check_cmd() { command -v "$1" &>/dev/null || die "Required tool not found: $1"; }
check_cmd docker
check_cmd kubectl
check_cmd helm

USE_KIND=true
if command -v kind &>/dev/null; then
  log "Using Kind for local cluster"
elif command -v minikube &>/dev/null; then
  log "Using Minikube for local cluster"
  USE_KIND=false
else
  die "Neither Kind nor Minikube found. Install one: https://kind.sigs.k8s.io/"
fi

# ─── Create cluster ────────────────────────────────────────────
if $USE_KIND; then
  if kind get clusters 2>/dev/null | grep -q "^security-fabric$"; then
    warn "Kind cluster 'security-fabric' already exists, skipping creation"
  else
    log "Creating Kind cluster..."
    cat <<EOF | kind create cluster --name security-fabric --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 80
        hostPort: 80
      - containerPort: 443
        hostPort: 443
  - role: worker
  - role: worker
EOF
    ok "Kind cluster created"
  fi
  kubectl cluster-info --context kind-security-fabric
else
  minikube start --profile security-fabric --cpus 4 --memory 8192 --driver docker
  minikube addons enable ingress --profile security-fabric
  ok "Minikube cluster started"
fi

KUBECTL="kubectl --context=${USE_KIND:+kind-}security-fabric"

# ─── Namespaces ────────────────────────────────────────────────
log "Creating namespaces..."
for ns in security-fabric ingress-nginx cert-manager istio-system monitoring; do
  $KUBECTL create namespace "$ns" --dry-run=client -o yaml | $KUBECTL apply -f -
done
ok "Namespaces ready"

# ─── Helm repos ────────────────────────────────────────────────
log "Adding Helm repositories..."
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx --force-update
helm repo add cert-manager https://charts.jetstack.io --force-update
helm repo add istio        https://istio-release.storage.googleapis.com/charts --force-update
helm repo add kedacore     https://kedacore.github.io/charts --force-update
helm repo add prometheus   https://prometheus-community.github.io/helm-charts --force-update
helm repo update
ok "Helm repos updated"

# ─── NGINX Ingress ─────────────────────────────────────────────
log "Installing NGINX Ingress..."
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --set controller.replicaCount=1 \
  --set controller.nodeSelector."kubernetes\.io/os"=linux \
  --wait --timeout 3m
ok "NGINX Ingress installed"

# ─── Cert-Manager ──────────────────────────────────────────────
log "Installing Cert-Manager..."
helm upgrade --install cert-manager cert-manager/cert-manager \
  --namespace cert-manager \
  --set installCRDs=true \
  --wait --timeout 3m
ok "Cert-Manager installed"

# ─── KEDA ──────────────────────────────────────────────────────
log "Installing KEDA..."
helm upgrade --install keda kedacore/keda \
  --namespace keda --create-namespace \
  --wait --timeout 3m
ok "KEDA installed"

# ─── Docker Compose for app services ───────────────────────────
log "Starting application services with Docker Compose..."
cd "$(dirname "$0")/.."
docker compose up -d --build
ok "Docker Compose services started"

# ─── Summary ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Security Fabric — Local Environment Ready${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Dashboard UI   →  ${CYAN}http://localhost:5173${NC}"
echo -e "  API Gateway    →  ${CYAN}http://localhost:8000${NC}"
echo -e "  API Docs       →  ${CYAN}http://localhost:8000/docs${NC}"
echo -e "  Grafana        →  ${CYAN}http://localhost:3000${NC}  (admin/admin)"
echo -e "  Kafka UI       →  ${CYAN}http://localhost:8080${NC}"
echo -e "  MailHog        →  ${CYAN}http://localhost:8025${NC}"
echo ""
echo -e "  Stop:  ${YELLOW}docker compose down${NC}"
echo -e "  Logs:  ${YELLOW}docker compose logs -f <service>${NC}"
echo ""
