# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | ✅ Active  |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Email **security@security-fabric.io** with:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof of concept if possible)
- Affected component(s) and version(s)
- Any suggested mitigations

You will receive an acknowledgment within **48 hours** and a status update within **7 days**.

## Scope

In scope:
- Authentication and JWT handling (`apps/api-gateway/app/core/security.py`)
- API Gateway endpoints and middleware
- Kafka message integrity
- Kubernetes RBAC and network policies
- Terraform state and secrets management

Out of scope:
- Social engineering attacks
- Denial of service attacks against the demo environment
- Issues in third-party dependencies (report upstream)

## Security Measures

This project implements the following controls:

**Authentication:** JWT RS256 tokens with configurable expiry and refresh rotation.

**Transport:** All external traffic requires TLS via cert-manager + Let's Encrypt. Internal service-to-service traffic is secured by Istio mutual TLS (mTLS) in STRICT mode.

**Network isolation:** Kubernetes NetworkPolicies enforce default-deny with explicit allow rules per service. The AI detection engine has no ingress — it only communicates outbound to Kafka and Redis.

**Secrets:** No secrets are committed to version control. In production, secrets are injected via Kubernetes Secrets backed by AWS Secrets Manager or GCP Secret Manager. The `.pre-commit-config.yaml` includes detect-secrets and gitleaks hooks.

**Container security:** All images are scanned with Trivy on every push to `main`. Dockerfiles use non-root users where possible and multi-stage builds to minimise attack surface.

**Static analysis:** Bandit SAST runs on all Python code in CI. Checkov scans Terraform and Kubernetes manifests for misconfigurations.

**Rate limiting:** The API Gateway enforces sliding-window rate limits per IP (200 req/min global, 20/min for `/auth/token`).

**Dependency auditing:** `pip-audit` runs weekly on all Python requirements files.
