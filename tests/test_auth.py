"""
Security and authentication tests for the feature flag API.
Tests JWT token validation, authorization, and access control.
"""

import pytest
from fastapi.testclient import TestClient
from app.db.session import get_session
from app.models.flag import FeatureFlag


class TestJWTAuthentication:
    """Tests for JWT authentication on protected endpoints."""

    def test_create_flag_with_valid_admin_token(self, client: TestClient, admin_token: str):
        """Test creating flag with valid admin token."""
        payload = {"name": "auth-test-1", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "auth-test-1"

    def test_create_flag_missing_token(self, client: TestClient):
        """Test creating flag without authentication token."""
        payload = {"name": "no-auth", "default": False, "rules": []}
        response = client.post("/flags", json=payload)
        # Should fail because auth is required
        assert response.status_code == 403

    def test_create_flag_malformed_auth_header(self, client: TestClient):
        """Test creating flag with malformed Authorization header."""
        payload = {"name": "malformed-auth", "default": False, "rules": []}
        headers = {"Authorization": "InvalidFormat"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 403

    def test_create_flag_missing_bearer_keyword(self, client: TestClient, admin_token: str):
        """Test creating flag with token but missing Bearer keyword."""
        payload = {"name": "missing-bearer", "default": False, "rules": []}
        headers = {"Authorization": admin_token}  # Missing "Bearer " prefix
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 403

    def test_create_flag_with_expired_token(self, client: TestClient, expired_token: str):
        """Test creating flag with expired JWT token."""
        payload = {"name": "expired-auth", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        # Expired token should fail
        assert response.status_code == 401

    def test_create_flag_with_invalid_token(self, client: TestClient, invalid_token: str):
        """Test creating flag with invalid JWT token (wrong secret)."""
        payload = {"name": "invalid-auth", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        # Invalid token should fail
        assert response.status_code == 401


class TestScopeAuthorization:
    """Tests for scope-based authorization (admin vs user)."""

    def test_create_flag_with_user_scope_fails(self, client: TestClient, user_token: str):
        """Test that user without admin scope cannot create flags."""
        payload = {"name": "user-create-fail", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        # User without admin scope should be forbidden
        assert response.status_code == 403
        assert "permissions" in response.json()["detail"]

    def test_update_flag_with_user_scope_fails(self, client: TestClient, user_token: str):
        """Test that user without admin scope cannot update flags."""
        with get_session() as session:
            flag = FeatureFlag(name="user-update-fail", default=False, rules=[])
            session.add(flag)
            session.commit()

        payload = {"name": "user-update-fail", "default": True, "rules": []}
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.put("/flags/user-update-fail", json=payload, headers=headers)
        assert response.status_code == 403

    def test_delete_flag_with_user_scope_fails(self, client: TestClient, user_token: str):
        """Test that user without admin scope cannot delete flags."""
        with get_session() as session:
            flag = FeatureFlag(name="user-delete-fail", default=False, rules=[])
            session.add(flag)
            session.commit()

        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.delete("/flags/user-delete-fail", headers=headers)
        assert response.status_code == 403


class TestPublicEndpoints:
    """Tests for endpoints that don't require authentication."""

    def test_list_flags_no_auth(self, client: TestClient):
        """Test listing flags doesn't require authentication."""
        with get_session() as session:
            flag = FeatureFlag(name="public-list", default=False, rules=[])
            session.add(flag)
            session.commit()

        response = client.get("/flags")
        assert response.status_code == 200
        assert any(f["name"] == "public-list" for f in response.json())

    def test_get_flag_no_auth(self, client: TestClient):
        """Test getting a specific flag doesn't require authentication."""
        with get_session() as session:
            flag = FeatureFlag(name="public-get", default=False, rules=[])
            session.add(flag)
            session.commit()

        response = client.get("/flags/public-get")
        assert response.status_code == 200
        assert response.json()["name"] == "public-get"

    def test_evaluate_flag_no_auth(self, client: TestClient):
        """Test evaluating a flag doesn't require authentication."""
        with get_session() as session:
            flag = FeatureFlag(name="public-eval", default=True, rules=[])
            session.add(flag)
            session.commit()

        payload = {"flag": "public-eval", "context": {"user_id": "user-123"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        assert response.json()["value"] is True
