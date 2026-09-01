# Security Fabric Test Strategy

## Quality objectives

Protect authentication, authorization, alert lifecycle and telemetry ingestion first. A release must preserve API contracts, reject unauthorized access, build the dashboard and pass supported browser workflows without suppressed failures.

## Test pyramid

- Unit tests validate security utilities, detection rules, service adapters and load-test calculations.
- API integration tests exercise routes against an isolated SQLite database with Kafka, Redis and Stripe boundaries controlled.
- Contract tests validate the generated OpenAPI document and required response schemas.
- Playwright tests cover critical user journeys in Chromium, Firefox, WebKit and a Pixel 7 mobile-browser profile.
- The load harness enforces error-rate and p99 latency thresholds against a running environment.
- CodeQL scans Python and JavaScript/TypeScript on pull requests and weekly.

## Test data and environments

Tests generate isolated users, tokens and alerts. CI uses non-production secrets and an in-memory database. Load results are only reported with the target, duration, concurrency and commit SHA; local measurements are never described as production capacity.

## Entry and exit criteria

Entry requires locked dependencies and valid configuration. Exit requires all automated tests, dashboard build, browser matrix and security scan to pass, with no hidden failure suppression. Any critical/high authorization, data-loss or credential-exposure defect blocks release.

## Defect severity

- Critical: authentication bypass, tenant-data exposure or secret disclosure.
- High: authorization failure, data corruption or unusable critical workflow.
- Medium: incorrect non-critical behavior with a workaround.
- Low: cosmetic, documentation or minor usability issue.

Every defect should be reproduced by a failing test, fixed in a pull request and linked to its issue whenever practical.
