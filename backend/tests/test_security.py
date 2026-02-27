"""test_security.py — Unit tests for password hashing and JWT utilities."""
import time
from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    _decode_token,
)


def test_password_hash_and_verify():
    password = "supersecret42"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)


def test_wrong_password_fails_verify():
    hashed = get_password_hash("correct")
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token({"sub": "user123"}, timedelta(minutes=5))
    user_id = _decode_token(token, "access")
    assert user_id == "user123"


def test_refresh_token_roundtrip():
    token = create_refresh_token({"sub": "user456"})
    user_id = _decode_token(token, "refresh")
    assert user_id == "user456"


def test_access_token_rejected_as_refresh():
    token = create_access_token({"sub": "u"}, timedelta(minutes=1))
    assert _decode_token(token, "refresh") is None


def test_expired_token_returns_none():
    token = create_access_token({"sub": "u"}, timedelta(seconds=-1))
    assert _decode_token(token, "access") is None


def test_malformed_token_returns_none():
    assert _decode_token("not.a.token", "access") is None
