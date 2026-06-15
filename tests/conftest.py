import sys
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# Ensure repository root is on sys.path so tests can import `app` package
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db.session import init_db, get_session
from app.main import app
from app.core.config import get_settings


@pytest.fixture(autouse=True)
def prepare_db(tmp_path, monkeypatch):
    """Initialize test database with temporary SQLite file."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    yield


@pytest.fixture
def client():
    """Provide a test client for FastAPI."""
    return TestClient(app)


@pytest.fixture
def admin_token() -> str:
    """Generate a valid admin JWT token."""
    settings = get_settings()
    payload = {
        "sub": "admin-user",
        "scopes": ["admin"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token


@pytest.fixture
def user_token() -> str:
    """Generate a valid non-admin JWT token."""
    settings = get_settings()
    payload = {
        "sub": "regular-user",
        "scopes": ["user"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token


@pytest.fixture
def expired_token() -> str:
    """Generate an expired JWT token."""
    settings = get_settings()
    payload = {
        "sub": "expired-user",
        "scopes": ["admin"],
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return token


@pytest.fixture
def invalid_token() -> str:
    """Generate an invalid JWT token (wrong secret)."""
    payload = {
        "sub": "invalid-user",
        "scopes": ["admin"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    # Encode with wrong secret
    token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
    return token


@pytest.fixture
def flag_factory():
    """Factory function to create test flags."""
    def _create_flag(
        name: str = "test-flag",
        default: bool = False,
        rules: Optional[list] = None
    ) -> Dict[str, Any]:
        return {
            "name": name,
            "default": default,
            "rules": rules or []
        }
    return _create_flag


@pytest.fixture
def attribute_match_rule_factory():
    """Factory function to create attribute_match rules."""
    def _create_rule(
        attribute: str = "region",
        operator: str = "in",
        values: Optional[list] = None,
        on: bool = True,
        priority: int = 0,
        rule_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "rule_type": "attribute_match",
            "parameters": {
                "attribute": attribute,
                "operator": operator,
                "values": values or ["us", "eu"]
            },
            "on": on,
            "priority": priority,
            "id": rule_id or "rule-1"
        }
    return _create_rule


@pytest.fixture
def percentage_rollout_rule_factory():
    """Factory function to create percentage_rollout rules."""
    def _create_rule(
        attribute: str = "user_id",
        percentage: int = 50,
        on: bool = True,
        priority: int = 0,
        rule_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "rule_type": "percentage_rollout",
            "parameters": {
                "attribute": attribute,
                "percentage": percentage
            },
            "on": on,
            "priority": priority,
            "id": rule_id or "rule-1"
        }
    return _create_rule


@pytest.fixture
def context_factory():
    """Factory function to create test contexts."""
    def _create_context(**kwargs) -> Dict[str, Any]:
        context = {
            "user_id": "user-123",
            "region": "us",
            "subscription_tier": "premium"
        }
        context.update(kwargs)
        return context
    return _create_context
