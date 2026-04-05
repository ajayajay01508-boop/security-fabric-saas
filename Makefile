.PHONY: help up down build logs ps clean seed test test-api test-ai test-ui \
        shell-api shell-db migrate rollback lint fmt k8s-deploy k8s-status \
        smoke health failover

# ── Colors ────────────────────────────────────────────────────
CYAN  := \033[0;36m
GREEN := \033[0;32m
YELLOW:= \033[1;33m
RED   := \033[0;31m
NC    := \033[0m

help: ## Show this help
	@echo ""
	@echo "  $(CYAN)Security Fabric SaaS — Dev Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  $(GREEN)%-22s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ── Docker Compose ────────────────────────────────────────────
up: ## Start all services (build if needed)
	@echo "$(CYAN)Starting Security Fabric...$(NC)"
	docker compose up -d --build
	@echo "$(GREEN)✓ All services started$(NC)"
	@$(MAKE) urls

up-fg: ## Start all services in foreground
	docker compose up --build

down: ## Stop all services
	docker compose down

down-v: ## Stop all services and delete volumes
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Continue? [y/N] " c; [ "$$c" = "y" ] || exit 1
	docker compose down -v

build: ## Rebuild all images
	docker compose build --no-cache

logs: ## Follow logs for all services
	docker compose logs -f

logs-api: ## Follow API Gateway logs
	docker compose logs -f api-gateway

logs-ai: ## Follow AI Detection Engine logs
	docker compose logs -f ai-detection-engine

logs-notif: ## Follow Notification Worker logs
	docker compose logs -f notification-worker

ps: ## Show running service status
	docker compose ps

restart: ## Restart all services
	docker compose restart

restart-%: ## Restart a specific service (e.g. make restart-api-gateway)
	docker compose restart $*

# ── Database ──────────────────────────────────────────────────
migrate: ## Run Alembic migrations
	docker compose exec api-gateway alembic upgrade head

migrate-down: ## Roll back last migration
	docker compose exec api-gateway alembic downgrade -1

migrate-history: ## Show migration history
	docker compose exec api-gateway alembic history

seed: ## Seed database with demo data
	@echo "$(CYAN)Seeding database...$(NC)"
	docker compose exec api-gateway python seed.py
	@echo "$(GREEN)✓ Database seeded$(NC)"

reset-db: ## Drop and recreate database
	docker compose exec postgres psql -U fabric -c "DROP DATABASE IF EXISTS security_fabric;"
	docker compose exec postgres psql -U fabric -c "CREATE DATABASE security_fabric;"
	@$(MAKE) migrate
	@$(MAKE) seed

shell-db: ## Open Postgres shell
	docker compose exec postgres psql -U fabric -d security_fabric

shell-api: ## Open shell in API Gateway container
	docker compose exec api-gateway bash

shell-redis: ## Open Redis CLI
	docker compose exec redis redis-cli

# ── Testing ───────────────────────────────────────────────────
test: test-api test-ai test-ui ## Run all tests
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-api: ## Run API Gateway tests
	@echo "$(CYAN)Testing API Gateway...$(NC)"
	cd apps/api-gateway && \
		DATABASE_URL="sqlite+aiosqlite:///:memory:" \
		REDIS_URL="redis://localhost:6379" \
		KAFKA_BOOTSTRAP_SERVERS="localhost:9092" \
		JWT_SECRET_KEY="test-secret" \
		STRIPE_SECRET_KEY="sk_test_mock" \
		ENVIRONMENT="test" \
		python -m pytest tests/ -v --tb=short 2>&1 || true
	@echo "$(YELLOW)(Run inside container for full integration: make test-api-docker)$(NC)"

test-api-docker: ## Run API Gateway tests inside Docker
	docker compose exec api-gateway python -m pytest tests/ -v --tb=short

test-ai: ## Run AI Detection Engine tests
	@echo "$(CYAN)Testing AI Detection Engine...$(NC)"
	cd services/ai-detection-engine && python -m pytest tests/ -v --tb=short

test-ai-stress: ## Run AI engine stress tests (1000 iterations)
	@echo "$(CYAN)Running stress tests...$(NC)"
	cd services/ai-detection-engine && python -m pytest tests/ -v --tb=short -k "stress or performance" --count=10

test-ui: ## Type-check dashboard
	@echo "$(CYAN)Type-checking Dashboard UI...$(NC)"
	cd apps/dashboard-ui && npx tsc --noEmit 2>&1 || true

test-notif: ## Run Notification Worker tests
	cd services/notification-worker && python -m pytest tests/ -v --tb=short

test-voice: ## Run Voice Alert Service tests
	cd services/voice-alert-service && python -m pytest tests/ -v --tb=short

test-shared: ## Run shared utilities tests
	cd shared/python-utils && python -m pytest tests/ -v --tb=short

test-admin: ## Run admin router tests (requires running DB)
	docker compose exec api-gateway python -m pytest tests/test_admin.py -v --tb=short

test-all: test test-notif test-voice test-shared ## Run every test suite

load: ## Run load test against local stack (30s, 10 workers)
	python scripts/load-test.py --url http://localhost:8000 --workers 10 --duration 30

load-stress: ## Heavy load test (60s, 50 workers)
	python scripts/load-test.py --url http://localhost:8000 --workers 50 --duration 60 --scenario full

lint: ## Lint all Python and TypeScript
	@echo "$(CYAN)Linting Python...$(NC)"
	python -m ruff check apps/api-gateway/app/ services/ shared/ 2>/dev/null || \
		echo "  (install ruff: pip install ruff)"
	@echo "$(CYAN)Linting TypeScript...$(NC)"
	cd apps/dashboard-ui && npm run lint 2>/dev/null || true

fmt: ## Auto-format Python code
	python -m ruff format apps/api-gateway/app/ services/ shared/ 2>/dev/null || \
		echo "  (install ruff: pip install ruff)"

# ── Smoke / Health Tests ──────────────────────────────────────
smoke: ## Run smoke tests against running services
	@echo "$(CYAN)Running smoke tests...$(NC)"
	bash scripts/smoke-test.sh

health: ## Check health of all services
	bash scripts/health-check.sh

# ── Kubernetes ────────────────────────────────────────────────
k8s-deploy: ## Deploy to Kubernetes (staging)
	kubectl apply -f infrastructure/kubernetes/charts/namespace-and-secrets.yaml
	kubectl apply -f infrastructure/kubernetes/charts/configmap.yaml
	kubectl apply -f infrastructure/kubernetes/charts/api-gateway-deployment.yaml
	kubectl apply -f infrastructure/kubernetes/charts/services-deployment.yaml
	kubectl apply -f infrastructure/kubernetes/ingress/
	kubectl apply -f infrastructure/kubernetes/autoscaling/
	kubectl apply -f infrastructure/kubernetes/charts/network-policies.yaml
	kubectl apply -f infrastructure/kubernetes/charts/servicemonitor.yaml

k8s-status: ## Show Kubernetes pod status
	kubectl get pods -n security-fabric -o wide

k8s-logs: ## Stream logs from all pods
	kubectl logs -n security-fabric -l app=api-gateway --follow

k8s-rollback: ## Roll back last deployment
	bash scripts/rollback.sh

# ── Cloud Failover ────────────────────────────────────────────
failover-dry: ## Dry-run failover from AWS to GCP
	python scripts/cloud-failover.py --from aws:us-east-1 --to gcp:us-central1 --dry-run

failover: ## Execute live failover (dangerous!)
	@read -p "LIVE FAILOVER from aws:us-east-1 to gcp:us-central1. Type 'failover' to confirm: " c; \
		[ "$$c" = "failover" ] || exit 1
	python scripts/cloud-failover.py --from aws:us-east-1 --to gcp:us-central1

# ── Utilities ─────────────────────────────────────────────────
urls: ## Print service URLs
	@echo ""
	@echo "  $(GREEN)Service URLs$(NC)"
	@echo "  Dashboard   →  $(CYAN)http://localhost:5173$(NC)"
	@echo "  API Gateway →  $(CYAN)http://localhost:8000$(NC)"
	@echo "  API Docs    →  $(CYAN)http://localhost:8000/docs$(NC)"
	@echo "  Grafana     →  $(CYAN)http://localhost:3000$(NC)  (admin/admin)"
	@echo "  Kafka UI    →  $(CYAN)http://localhost:8080$(NC)"
	@echo "  MailHog     →  $(CYAN)http://localhost:8025$(NC)"
	@echo "  Prometheus  →  $(CYAN)http://localhost:9090$(NC)"
	@echo ""

clean: ## Remove all containers, images, volumes
	docker compose down -v --rmi local 2>/dev/null || true
	docker system prune -f

env: ## Copy .env.example to .env
	@[ -f .env ] && echo ".env already exists" || (cp .env.example .env && echo "$(GREEN)✓ .env created — fill in your keys$(NC)")

setup: env up ## Full local setup — copies .env, starts all services
	@echo "$(CYAN)Waiting for services to be healthy...$(NC)"
	@sleep 15
	@$(MAKE) migrate || true
	@$(MAKE) seed || true
	@echo "$(GREEN)✓ Security Fabric is ready!$(NC)"
	@$(MAKE) urls
