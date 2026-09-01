from datetime import UTC, datetime, timedelta

import pytest
from jose import JWTError, jwt

from app.core.config import settings
from app.core.token_service import create_access_token, create_refresh_token


def decode(token):
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def test_access_token_preserves_subject_and_claims():
    payload = decode(create_access_token({"sub": "42", "role": "analyst"}))
    assert payload["sub"] == "42"
    assert payload["role"] == "analyst"


def test_access_token_contains_future_expiry():
    payload = decode(create_access_token({"sub": "42"}))
    assert datetime.fromtimestamp(payload["exp"], UTC) > datetime.now(UTC)


def test_access_token_honors_custom_expiry():
    before = datetime.now(UTC)
    payload = decode(create_access_token({"sub": "42"}, timedelta(minutes=5)))
    expiry = datetime.fromtimestamp(payload["exp"], UTC)
    assert before + timedelta(minutes=4, seconds=55) <= expiry
    assert expiry <= before + timedelta(minutes=5, seconds=5)


def test_expired_access_token_is_rejected():
    token = create_access_token({"sub": "42"}, timedelta(seconds=-1))
    with pytest.raises(JWTError):
        decode(token)


def test_access_token_does_not_mutate_input():
    source = {"sub": "42"}
    create_access_token(source)
    assert source == {"sub": "42"}


def test_refresh_token_has_required_type_and_subject():
    payload = decode(create_refresh_token({"sub": "42"}))
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"


def test_refresh_token_expires_about_thirty_days_ahead():
    before = datetime.now(UTC)
    payload = decode(create_refresh_token({"sub": "42"}))
    expiry = datetime.fromtimestamp(payload["exp"], UTC)
    assert before + timedelta(days=29, hours=23) <= expiry
    assert expiry <= before + timedelta(days=30, minutes=1)


def test_refresh_token_does_not_mutate_input():
    source = {"sub": "42"}
    create_refresh_token(source)
    assert source == {"sub": "42"}
