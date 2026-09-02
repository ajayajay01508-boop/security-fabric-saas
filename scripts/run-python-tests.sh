#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
export COVERAGE_FILE="$PROJECT_ROOT/.coverage"

run_suite() {
  local directory="$1"
  local coverage_target="$2"
  shift 2
  (
    cd "$PROJECT_ROOT/$directory"
    if [[ "${COVERAGE:-0}" == "1" ]]; then
      "$PYTHON_BIN" -m pytest "$@" -q --tb=short \
        --cov="$coverage_target" --cov-append --cov-branch \
        --cov-config="$PROJECT_ROOT/pyproject.toml" --cov-fail-under=0 --cov-report=
    else
      "$PYTHON_BIN" -m pytest "$@" -q --tb=short
    fi
  )
}

if [[ "${COVERAGE:-0}" == "1" ]]; then
  "$PYTHON_BIN" -m coverage erase
fi

run_suite "apps/api-gateway" "app" tests
run_suite "services/ai-detection-engine" "." tests
run_suite "services/notification-worker" "." tests
run_suite "services/voice-alert-service" "." tests
run_suite "shared/python-utils" "." tests
run_suite "." "scripts" tests/quality

if [[ "${COVERAGE:-0}" == "1" ]]; then
  cd "$PROJECT_ROOT"
  "$PYTHON_BIN" -m coverage report --show-missing --fail-under=80
  "$PYTHON_BIN" -m coverage xml -o coverage.xml
  "$PYTHON_BIN" -m coverage html -d htmlcov
fi
