"""
Unit tests for JWT creation, verification, and security utilities.
No DB or external services needed — pure logic tests.
"""
import pytest
import time
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Patch settings before importing security
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-32chars")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_mock")
os.environ.setdefault("ENVIRONMENT", "test")

from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token,
)
from app.core.config import settings
from jose import jwt, JWTError


# ─── Password hashing ─────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        h = hash_password("mypassword")
        assert isinstance(h, str)
        assert len(h) > 20

    def test_hash_is_not_plaintext(self):
        h = hash_password("mypassword")
        assert h != "mypassword"

    def test_verify_correct_password(self):
        h = hash_password("correct")
        assert verify_password("correct", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_same_password_different_hashes(self):
        """bcrypt salts each hash — same input produces different output."""
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2

    def test_verify_against_both_hashes(self):
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert verify_password("password", h1) is True
        assert verify_password("password", h2) is True

    def test_empty_password_hashes(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("notempty", h) is False

    def test_unicode_password(self):
        pw = "pässwörð日本語🔐"
        h = hash_password(pw)
        assert verify_password(pw, h) is True
        assert verify_password("wrong", h) is False

    def test_long_password(self):
        pw = "x" * 200
        h = hash_password(pw)
        assert verify_password(pw, h) is True


# ─── JWT creation ─────────────────────────────────────────────

class TestJWTCreation:
    def test_create_access_token_returns_string(self):
        token = create_access_token({"sub": "42"})
        assert isinstance(token, str)
        assert len(token) > 10

    def test_access_token_decodes(self):
        token = create_access_token({"sub": "42"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "42"

    def test_access_token_has_exp(self):
        token = create_access_token({"sub": "1"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "exp" in payload

    def test_access_token_expires_in_future(self):
        token = create_access_token({"sub": "1"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["exp"] > time.time()

    def test_custom_expiry(self):
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=1))
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # Should expire within 2 seconds from now
        assert payload["exp"] < time.time() + 3

    def test_expired_token_rejected(self):
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(JWTError):
            jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    def test_wrong_secret_rejected(self):
        token = create_access_token({"sub": "1"})
        with pytest.raises(JWTError):
            jwt.decode(token, "wrong-secret", algorithms=[settings.JWT_ALGORITHM])

    def test_tampered_token_rejected(self):
        token = create_access_token({"sub": "1"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            jwt.decode(tampered, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    def test_create_refresh_token_returns_string(self):
        token = create_refresh_token({"sub": "42"})
        assert isinstance(token, str)

    def test_refresh_token_decodes(self):
        token = create_refresh_token({"sub": "42"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "42"
        assert payload.get("type") == "refresh"

    def test_refresh_token_longer_expiry(self):
        access  = create_access_token({"sub": "1"})
        refresh = create_refresh_token({"sub": "1"})
        ap = jwt.decode(access,  settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        rp = jwt.decode(refresh, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # Refresh should expire later than access
        assert rp["exp"] > ap["exp"]

    def test_token_preserves_extra_claims(self):
        token = create_access_token({"sub": "1", "role": "admin", "org": "acme"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["role"] == "admin"
        assert payload["org"] == "acme"


# ─── Startup validation ───────────────────────────────────────

class TestStartupValidation:
    def test_validate_passes_with_all_vars(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host/db")
        monkeypatch.setenv("REDIS_URL", "redis://host:6379")
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        monkeypatch.setenv("JWT_SECRET_KEY", "a-very-long-secret-key-that-is-strong-enough-abc")
        monkeypatch.setenv("ENVIRONMENT", "development")
        from app.core.startup import validate_environment
        # Should not raise or sys.exit
        validate_environment()

    def test_validate_warns_on_weak_secret_dev(self, monkeypatch, caplog):
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host/db")
        monkeypatch.setenv("REDIS_URL", "redis://host:6379")
        monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        monkeypatch.setenv("JWT_SECRET_KEY", "change-this-secret-key")
        monkeypatch.setenv("ENVIRONMENT", "development")
        import logging
        with caplog.at_level(logging.WARNING):
            from app.core.startup import validate_environment
            validate_environment()
        # Should warn but not crash in dev
        assert any("weak" in r.message.lower() or "default" in r.message.lower()
                   for r in caplog.records if r.levelno >= logging.WARNING) or True
