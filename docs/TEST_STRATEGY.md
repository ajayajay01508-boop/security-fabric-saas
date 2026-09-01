# Security Fabric Test Strategy

## Quality objectives

Protect authentication, authorization, alert lifecycle and telemetry ingestion first. A release must preserve API contracts, reject unauthorized access, build the dashboard and pass supported browser workflows without suppressed failures.

## Test pyramid

- Unit tests validate security utilities, detection rules, service adapters and load-test calculations.
- API integration tests exercise routes against an isolated SQLite database with Kafka, Redis and Stripe boundaries controlled.
- Contract tests validate required response schemas and use Schemathesis to generate cases from the live OpenAPI document.
- Playwright tests cover critical user journeys in Chromium, Firefox, WebKit and a Pixel 7 mobile-browser profile.
- Playwright plus Axe checks login, dashboard and keyboard-only navigation for serious accessibility violations.
- A real-stack browser test verifies registration and login against the API and SQLite database without route mocks.
- Twelve Appium tests exercise a native Android login application on an Android emulator.
- The load harness enforces error-rate and p99 latency thresholds against a running environment.
- CodeQL scans Python and JavaScript/TypeScript on pull requests and weekly.

## Verified local performance baseline

The authenticated baseline uses five workers, 100 ms request pacing and three seconds per scenario against the real API with SQLite. On 1 September 2026, auth completed 135 requests at 44.9 req/s (p95 17.1 ms, p99 121.0 ms), alerts completed 140 at 46.6 req/s (p95 16.1 ms, p99 17.8 ms), and telemetry completed 140 at 46.6 req/s (p95 18.8 ms, p99 21.6 ms). All 415 requests succeeded. These are local regression thresholds, not production capacity claims.

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
