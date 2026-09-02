import logging

import pytest

from app.core import startup


def configure_required(monkeypatch, *, environment="development", secret="strong-test-secret"):
    values = {
        "DATABASE_URL": "postgresql://user:pass@db:5432/security",
        "REDIS_URL": "redis://redis:6379",
        "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
        "JWT_SECRET_KEY": secret,
        "ENVIRONMENT": environment,
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


def test_validate_environment_accepts_complete_development_config(monkeypatch, caplog):
    configure_required(monkeypatch)
    with caplog.at_level(logging.INFO):
        startup.validate_environment()
    assert "Environment validated" in caplog.text


def test_validate_environment_warns_but_continues_in_development(monkeypatch, caplog):
    for key in startup.REQUIRED_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "secret")
    monkeypatch.setenv("ENVIRONMENT", "development")
    with caplog.at_level(logging.WARNING):
        startup.validate_environment()
    assert "weak default" in caplog.text
    assert "ignored in development mode" in caplog.text


def test_validate_environment_aborts_unsafe_production(monkeypatch, caplog):
    configure_required(monkeypatch, environment="production", secret="test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/security")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_example")
    with caplog.at_level(logging.WARNING), pytest.raises(SystemExit) as exc:
        startup.validate_environment()
    assert exc.value.code == 1
    assert "known weak/default" in caplog.text
    assert "too short" in caplog.text
    assert "test key" in caplog.text
    assert "localhost" in caplog.text
    assert "Aborting" in caplog.text


def test_log_startup_banner_masks_credentials(monkeypatch, caplog):
    configure_required(monkeypatch, environment="staging")
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret-user:secret-pass@db:5432/security")
    with caplog.at_level(logging.INFO):
        startup.log_startup_banner()
    assert "STAGING" in caplog.text
    assert "db:5432/security" in caplog.text
    assert "secret-pass" not in caplog.text

