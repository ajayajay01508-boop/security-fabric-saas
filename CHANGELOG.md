# Changelog

All notable changes to Security Fabric are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2025-01-01

### Added

**Core Platform**
- FastAPI API Gateway with JWT authentication, CORS, and structured request logging
- Real-time threat event streaming via WebSocket backed by Redis Pub/Sub
- Kafka-based telemetry ingestion pipeline (`raw-telemetry` → ML inference → `threat-events`)
- AI Detection Engine with heuristic rules + trained GradientBoosting ML model (10-feature vector)
- Notification Worker with HTML email alerts via SMTP (MailHog in dev, SES in prod)
- Voice Alert Service with Twilio + AWS Polly TwiML for critical-severity incidents

**API Endpoints**
- `POST /auth/register` — user registration with bcrypt password hashing
- `POST /auth/token` — JWT access + refresh token issuance
- `GET /auth/me` — authenticated user profile
- `GET /alerts` — paginated alert listing with severity/status/search filters
- `GET /alerts/stats` — aggregate counts by severity and status
- `GET /alerts/export` — CSV export of alerts
- `PATCH /alerts/{id}/acknowledge` — mark alert as acknowledged
- `PATCH /alerts/{id}/resolve` — mark alert as resolved
- `POST /telemetry/ingest` — single event ingest to Kafka
- `POST /telemetry/ingest/batch` — batch ingest (up to 1000 events)
- `POST /payments/subscribe` — Stripe subscription management
- `GET /payments/status` — current subscription plan and status
- `WS /ws/threats` — live threat event stream (JWT-authenticated)
- `WS /ws/metrics` — live pipeline metrics stream
- `GET /metrics` — Prometheus metrics endpoint
- `GET /admin/users` — superuser user management
- `GET /admin/stats` — system-wide statistics
- `DELETE /admin/alerts/bulk-resolve` — bulk resolve old alerts

**Dashboard UI** (React + Vite + Tailwind)
- Login and registration pages with JWT auth
- Dashboard: live MetricsBar, SeverityChart donut, ThreatTimeline area chart, AlertsTable
- Alerts page: filter by severity/status, paginate, acknowledge/resolve inline
- Telemetry page: traffic simulator with configurable rate + manual event injection
- Billing page: plan cards (Free/Starter/Pro/Enterprise) with Stripe portal link
- Toast notification system for user feedback
- ErrorBoundary on all routes with reset capability
- 404 page with navigation back to dashboard

**Infrastructure**
- Docker Compose for local dev (14 services including MailHog, Kafka UI, Grafana)
- Terraform modules: AWS EKS, GCP GKE, AWS RDS with Secrets Manager integration
- Kubernetes manifests: Deployments, Services, Ingress (NGINX + cert-manager), HPA, KEDA
- Istio service mesh with STRICT mTLS and default-deny AuthorizationPolicies
- Kubernetes NetworkPolicies: default-deny-all with per-service allow rules
- Prometheus alert rules: HighThreatRate, KafkaConsumerLag, APIHighErrorRate, SlowInference, ServiceDown
- Grafana dashboards: Threat Overview, API Gateway, Kafka Pipeline
- Helm chart for production deployment
- Backup CronJob (daily pg_dump) and alert cleanup CronJob (weekly)

**Testing**
- API Gateway: 60+ tests across auth, alerts CRUD, payments, telemetry, security (JWT), rate limiting, metrics, admin
- AI Detection Engine: 16 unit tests + 800-round stress test + 10,000-prediction performance test
- Notification Worker: 24 tests covering email template rendering for all severities
- Voice Alert Service: 15 tests including 100-iteration TwiML stress test
- Shared utilities: 22 tests covering JSONFormatter, rate_limit, require_role, ServiceMetrics

**Security**
- Sliding-window rate limiting middleware (Redis-backed with in-process fallback)
- `X-RateLimit-*` response headers on all routes
- Startup environment validation with weak-secret detection
- Pre-commit hooks: ruff, mypy, detect-secrets, gitleaks, hadolint, Bandit
- GitHub Actions security workflow: Bandit SAST, Trivy container scan, Checkov IaC, pip-audit
- `.dockerignore` for all service images

**Developer Experience**
- `Makefile` with 30+ targets: `make setup`, `make test`, `make seed`, `make smoke`, `make health`
- `scripts/smoke-test.sh` — 18 endpoint checks against running stack
- `scripts/health-check.sh` — container, DB, Redis, Kafka, topic health
- `scripts/load-test.py` — pure-stdlib multi-threaded load tester with p50/p95/p99 stats
- `scripts/rollback.sh` — Kubernetes deployment rollback with confirmation
- `scripts/cloud-failover.py` — 5-step automated multi-cloud DNS+DB+Kafka failover
- `docker-compose.override.yml` for hot-reload in development
- `docker-compose.prod.yml` for production image deployment
- `docker-compose.test.yml` for CI test isolation
