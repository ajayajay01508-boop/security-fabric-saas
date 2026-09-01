# Contributing to Security Fabric

Thank you for your interest in contributing. This document covers how to set up your development environment, the contribution workflow, and coding standards.

## Development Setup

```bash
git clone https://github.com/your-org/security-fabric-saas
cd security-fabric-saas
make setup          # copies .env, starts Docker Compose, runs migrations, seeds DB
```

Install pre-commit hooks (recommended):

```bash
pip install pre-commit
pre-commit install
```

## Workflow

1. **Fork** the repository and create a branch from `develop`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Write tests first.** Every new endpoint, service function, or utility must have tests.

3. **Run the test suite** before pushing:
   ```bash
   make test          # all tests
   make test-api      # API Gateway only
   make test-ai       # AI engine only
   make lint          # ruff + mypy
   ```

4. **Open a pull request** against `develop`. The PR template will guide you through the checklist.

## Coding Standards

### Python

- Formatter: `ruff format` (configured in `pyproject.toml`)
- Linter: `ruff check` (E, W, F, I, B, UP, S, N rules)
- Type hints on all public functions
- Async all the way — no synchronous DB or network calls in FastAPI routes
- Structured logging via `shared/python-utils/structured_logging.py` — no bare `print()`

### TypeScript / React

- Strict TypeScript — no `any` unless unavoidable
- Functional components only
- Custom hooks for all stateful logic (no logic in components)
- Tailwind for styling — no inline styles

### Git Commits

Follow Conventional Commits:

```
feat(api-gateway): add alert search endpoint
fix(ai-engine): correct 10-feature vector for ML model
infra(k8s): add PodDisruptionBudget for workers
docs: update CONTRIBUTING.md
test(auth): add JWT expiry edge case
```

Types: `feat` `fix` `infra` `docs` `test` `refactor` `perf` `chore`

## Adding a New Service

1. Create `services/<name>/` with `service.py`, `Dockerfile`, `.dockerignore`, `requirements.txt`
2. Add a `tests/` directory with `__init__.py`, `conftest.py`, and `test_<name>.py`
3. Register in `docker-compose.yaml` (with healthcheck)
4. Add a Kubernetes Deployment in `infrastructure/kubernetes/charts/`
5. Add Prometheus metrics and a Grafana panel
6. Add CI test job in `.github/workflows/ci-cd.yml`

## Adding a New API Endpoint

1. Add the route function to the appropriate router in `apps/api-gateway/app/routers/`
2. Add request/response Pydantic models
3. Write tests in `apps/api-gateway/tests/test_<router>.py`
4. Update the OpenAPI description string

## Security

Please do not open GitHub issues for security vulnerabilities. See [SECURITY.md](SECURITY.md) for the responsible disclosure process.
