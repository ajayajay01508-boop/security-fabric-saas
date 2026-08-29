# SECURITY FABRIC SAAS

> **Real-time threat detection infrastructure. ML-powered. Multi-cloud. Production-grade.**

A distributed security intelligence platform that ingests network telemetry, runs quantized ML inference at the edge, and delivers sub-second threat alerts across voice, push, and email channels — orchestrated across AWS, Azure, and GCP with automated failover.(LIVE DEMO:https://cloud-guard-de7c7.web.app/)

---

## TABLE OF CONTENTS

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Getting Started](#getting-started)
4. [Local Development](#local-development)
5. [Infrastructure & Deployment](#infrastructure--deployment)
6. [Service Reference](#service-reference)
7. [Security Model](#security-model)
8. [Monitoring & Observability](#monitoring--observability)
9. [Multi-Cloud Failover](#multi-cloud-failover)
10. [API Reference](#api-reference)
11. [Contributing](#contributing)

---

## ARCHITECTURE OVERVIEW

```
                        ┌─────────────────────────────────┐
                        │         INGRESS LAYER           │
                        │   NGINX + Cert-Manager (TLS)    │
                        └────────────────┬────────────────┘
                                         │
                        ┌────────────────▼────────────────┐
                        │          API GATEWAY            │
                        │    FastAPI · JWT · Rate Limit   │
                        │  /auth  /payments  /alerts      │
                        └──────┬──────────────┬───────────┘
                               │              │
              ┌────────────────▼──┐     ┌─────▼──────────────────┐
              │   DASHBOARD UI    │     │     KAFKA MESSAGE BUS   │
              │  React + Vite     │     │   (Event Stream Core)   │
              │  WebSocket / SSE  │     └─────┬──────────────┬────┘
              │  Redis Pub/Sub    │           │              │
              └───────────────────┘           │              │
                                   ┌──────────▼──┐   ┌──────▼──────────┐
                                   │ AI DETECTION │   │  NOTIFICATION   │
                                   │   ENGINE     │   │    WORKER       │
                                   │ PyTorch/ONNX │   │  Email · Push   │
                                   └──────┬───────┘   └─────────────────┘
                                          │
                                   ┌──────▼───────┐
                                   │ VOICE ALERTS │
                                   │ Twilio · AWS │
                                   │    Polly     │
                                   └──────────────┘

     Infrastructure: EKS · GKE · AKS   |   Service Mesh: Istio mTLS
     IaC: Terraform (modules/envs)      |   Autoscaling: KEDA (event-driven)
     Observability: Prometheus + Grafana
```

---

## SYSTEM COMPONENTS

### `apps/dashboard-ui` — React Dashboard
The primary operator interface. Real-time threat feeds, alert timelines, and analytics panels delivered via WebSocket connections backed by Redis Pub/Sub.

| Technology | Role |
|---|---|
| React + Vite | Component framework and dev server |
| Tailwind CSS | Utility-first styling |
| WebSockets | Live threat event streaming |
| Redis Pub/Sub | Backend push channel (via hooks) |

**Key directories:**
- `src/components/` — Charts, Auth panels, Alert tables
- `src/hooks/` — Custom hooks wrapping Redis Pub/Sub subscriptions

---

### `apps/api-gateway` — FastAPI Gateway
The single entry point for all client traffic. Handles authentication, routes to internal services, integrates Stripe for billing, and produces events to Kafka.

| Technology | Role |
|---|---|
| FastAPI | High-performance async HTTP |
| JWT | Stateless auth tokens |
| Stripe | Subscription billing |
| Kafka Producer | Event publishing to detection pipeline |

**Routers:** `/auth` · `/payments` · `/alerts`  
**Services:** `stripe_service.py` · `kafka_service.py`

---

### `services/ai-detection-engine` — ML Inference Service
Consumes raw telemetry events from Kafka, runs them through quantized PyTorch/ONNX models, and emits threat classifications back to the event bus.

| Technology | Role |
|---|---|
| PyTorch / ONNX | Model training and optimized inference |
| Kafka Consumer | Event ingestion |
| Quantized Models | Low-latency inference at edge |

**Pipeline:** `Kafka topic → processor.py → model inference → threat event`

---

### `services/voice-alert-service` — Voice Notification
Converts threat alerts into voice calls using Twilio and AWS Polly for natural-sounding speech synthesis.

---

### `services/notification-worker` — Async Alert Dispatch
Handles email and push notification delivery, consuming from alert queues with retry logic and delivery tracking.

---

## GETTING STARTED

### Prerequisites

| Tool | Minimum Version | Purpose |
|---|---|---|
| Docker | 24.x | Container runtime |
| Docker Compose | 2.x | Local orchestration |
| kubectl | 1.28+ | Kubernetes CLI |
| Helm | 3.x | Chart management |
| Terraform | 1.6+ | Infrastructure provisioning |
| Python | 3.11+ | Backend services |
| Node.js | 20+ | Dashboard UI |

### Cloud Credentials (for cloud deployments)

Configure credentials for your target cloud:

```bash
# AWS
aws configure

# GCP
gcloud auth application-default login

# Azure
az login
```

---

## LOCAL DEVELOPMENT

The fastest path to a running local environment uses Docker Compose with a local Kind or Minikube cluster.

### Option 1 — Docker Compose (Recommended for development)

```bash
# Clone and enter the repo
git clone <repo-url>
cd security-fabric-saas

# Start all services
docker compose up --build
```

Services will be available at:

| Service | URL |
|---|---|
| Dashboard UI | http://localhost:5173 |
| API Gateway | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Grafana | http://localhost:3000 |
| Kafka UI | http://localhost:8080 |

### Option 2 — Local Kubernetes (Kind / Minikube)

```bash
# Run the automated setup script
chmod +x scripts/setup-local.sh
./scripts/setup-local.sh
```

The script will:
1. Provision a local Kind cluster
2. Install NGINX Ingress and Cert-Manager
3. Deploy all Helm charts from `infrastructure/kubernetes/`
4. Seed Kafka topics and Redis

### Environment Variables

Copy and configure environment files before starting:

```bash
cp apps/api-gateway/.env.example apps/api-gateway/.env
cp apps/dashboard-ui/.env.example apps/dashboard-ui/.env
cp services/ai-detection-engine/.env.example services/ai-detection-engine/.env
```

**Core variables to configure:**

```env
# API Gateway
JWT_SECRET_KEY=your-secret-key
STRIPE_SECRET_KEY=sk_test_...
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_URL=redis://localhost:6379

# AI Detection Engine
MODEL_PATH=models/detector_quantized.onnx
KAFKA_CONSUMER_GROUP=ai-detection
KAFKA_TOPIC_TELEMETRY=raw-telemetry
KAFKA_TOPIC_THREATS=threat-events

# Voice Alert Service
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
AWS_REGION=us-east-1
```

---

## INFRASTRUCTURE & DEPLOYMENT

All cloud infrastructure is managed with Terraform. Kubernetes workloads are deployed via Helm charts.

### Terraform

```
infrastructure/terraform/
├── modules/          # Reusable: EKS, GKE, AKS, RDS, Kafka MSK
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

**Deploy to an environment:**

```bash
cd infrastructure/terraform/environments/prod

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

**Available modules:**

| Module | Provisions |
|---|---|
| `modules/eks` | AWS EKS cluster + node groups |
| `modules/gke` | GCP GKE Autopilot cluster |
| `modules/aks` | Azure AKS cluster |
| `modules/rds` | Managed PostgreSQL (multi-AZ) |
| `modules/kafka-msk` | AWS MSK (Managed Kafka) |

### Kubernetes / Helm

```
infrastructure/kubernetes/
├── ingress/      # NGINX Ingress Controller + Cert-Manager
├── istio/        # Service mesh, mTLS policies, traffic management
└── autoscaling/  # KEDA ScaledObjects for event-driven scaling
```

**Deploy all charts:**

```bash
# Install NGINX + TLS
helm upgrade --install ingress infrastructure/kubernetes/ingress/ \
  --namespace ingress-nginx --create-namespace

# Install Istio service mesh
helm upgrade --install istio infrastructure/kubernetes/istio/ \
  --namespace istio-system --create-namespace

# Deploy application charts
helm upgrade --install security-fabric infrastructure/kubernetes/ \
  --namespace security-fabric --create-namespace \
  -f infrastructure/kubernetes/values.prod.yaml
```

---

## SERVICE REFERENCE

### Shared Protobuf Definitions (`shared/proto/`)

All inter-service gRPC communication is defined in `.proto` files. Regenerate stubs after modifying:

```bash
# Python
python -m grpc_tools.protoc -I shared/proto \
  --python_out=. --grpc_python_out=. \
  shared/proto/*.proto
```

### Shared Python Utilities (`shared/python-utils/`)

Common decorators and utilities available to all Python services:

```python
from shared.python_utils.logging import structured_logger
from shared.python_utils.security import require_auth, rate_limit

logger = structured_logger(__name__)

@require_auth
@rate_limit(max_calls=100, period=60)
async def my_endpoint(request):
    logger.info("event", extra={"trace_id": request.trace_id})
```

---

## SECURITY MODEL

### Authentication Flow

```
Client → API Gateway (JWT validation) → Internal services (mTLS via Istio)
```

1. Client authenticates via `/auth/token` and receives a signed JWT
2. All requests to the API Gateway require a valid Bearer token
3. Internal service-to-service calls are secured by Istio mutual TLS
4. No internal service is exposed outside the mesh

### Network Policies

- All pods have default-deny ingress/egress
- Explicit `NetworkPolicy` objects permit only required traffic paths
- Istio `AuthorizationPolicy` enforces service identity at the mesh layer

### Secrets Management

- Kubernetes Secrets encrypted at rest (cloud KMS integration per environment)
- Terraform manages secret rotation for RDS credentials via AWS Secrets Manager / GCP Secret Manager
- No secrets committed to the repository — all values are injected at runtime

---

## MONITORING & OBSERVABILITY

Grafana dashboards and Prometheus rules are pre-configured in `infrastructure/monitoring/`.

### Available Dashboards

| Dashboard | Panels |
|---|---|
| **Threat Overview** | Detection rate, false positive ratio, severity distribution |
| **API Gateway** | Request latency (p50/p95/p99), error rates, auth failures |
| **Kafka Pipeline** | Consumer lag, throughput, partition health |
| **ML Engine** | Inference latency, model confidence scores, GPU/CPU utilization |
| **Infrastructure** | Pod status, node resource usage, HPA/KEDA scaling events |

### Key Metrics

```
# Threat detection rate (threats per minute)
rate(threat_events_total[1m])

# API Gateway p99 latency
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Kafka consumer lag
kafka_consumer_group_lag{group="ai-detection"}

# ML inference latency
histogram_quantile(0.95, rate(ml_inference_duration_seconds_bucket[5m]))
```

### Alerts

Pre-configured Prometheus alerting rules fire to the notification-worker for:
- Consumer lag > 10,000 messages (pipeline stall)
- API error rate > 5% over 5 minutes
- ML inference p99 > 500ms
- Any Kubernetes pod CrashLoopBackOff

---

## MULTI-CLOUD FAILOVER

Automated region and cloud failover is handled by `scripts/cloud-failover.py`.

```bash
# Trigger manual failover from AWS us-east-1 to GCP us-central1
python scripts/cloud-failover.py \
  --from aws:us-east-1 \
  --to gcp:us-central1 \
  --reason "AZ degradation detected"
```

### Failover Strategy

1. **Health check failure** detected by Prometheus alerting or manual trigger
2. Script updates DNS weights (Route 53 / Cloud DNS) to shift traffic
3. Kafka MirrorMaker 2 ensures topic replication is already in sync
4. RDS read replica in target cloud is promoted to primary
5. Rollback is a single command with full audit log

### Failover Runbook

| Step | Action | Command |
|---|---|---|
| 1 | Verify target cluster health | `kubectl --context=gcp get nodes` |
| 2 | Check Kafka replication lag | `kafka-consumer-groups --describe --group mirror-maker` |
| 3 | Execute failover | `python scripts/cloud-failover.py --from aws:us-east-1 --to gcp:us-central1` |
| 4 | Validate traffic shift | Check Grafana → Infrastructure dashboard |
| 5 | Notify stakeholders | Automated via notification-worker |

---

## API REFERENCE

Full interactive docs are available at `/docs` (Swagger UI) and `/redoc` when the API Gateway is running.

### Core Endpoints

```
POST   /auth/token              Obtain JWT access token
POST   /auth/refresh            Refresh an expiring token
DELETE /auth/token              Revoke token (logout)

GET    /alerts                  List recent threat alerts (paginated)
GET    /alerts/{id}             Get alert detail
PATCH  /alerts/{id}/acknowledge Mark alert as acknowledged

POST   /payments/subscribe      Create Stripe subscription
GET    /payments/status         Current subscription and usage
POST   /payments/portal         Generate Stripe billing portal URL
```

### WebSocket Streams

```
WS  /ws/threats                 Live threat event stream (requires JWT)
WS  /ws/metrics                 Real-time platform metrics
```

**Connection example:**

```javascript
const ws = new WebSocket(
  `wss://api.yourdomain.com/ws/threats?token=${accessToken}`
);

ws.onmessage = (event) => {
  const threat = JSON.parse(event.data);
  console.log(threat.severity, threat.source_ip, threat.classification);
};
```

---

## CONTRIBUTING

### Development Workflow

```bash
# 1. Create a feature branch
git checkout -b feature/your-feature-name

# 2. Start local environment
docker compose up --build

# 3. Run tests before committing
# Python services
pytest services/ai-detection-engine/tests/ -v
pytest apps/api-gateway/tests/ -v

# Dashboard UI
cd apps/dashboard-ui && npm run test

# 4. Lint checks
ruff check services/ apps/api-gateway/
cd apps/dashboard-ui && npm run lint

# 5. Open a pull request against main
```

### Commit Convention

```
feat(ai-engine): add anomaly threshold configuration
fix(api-gateway): handle Stripe webhook signature timeout
infra(terraform): add GKE Autopilot module
docs: update failover runbook
```

### Adding a New Service

1. Create directory under `services/`
2. Add a `Dockerfile` following the multi-stage pattern from existing services
3. Define gRPC interfaces in `shared/proto/` if the service communicates internally
4. Add a Helm chart under `infrastructure/kubernetes/`
5. Add Prometheus metrics and a Grafana dashboard panel
6. Register the service in `docker-compose.yaml` for local development

---

## LICENSE

See `LICENSE` for terms of use.

---

*Security Fabric SaaS — Built for operators who can't afford to miss a signal.*
