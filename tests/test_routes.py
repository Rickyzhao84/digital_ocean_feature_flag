"""
Integration tests for feature flag API routes.
Tests all CRUD operations and evaluation endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from app.db.session import get_session
from app.models.flag import FeatureFlag

class TestCreateFlag:
    """Tests for POST /flags endpoint."""

    def test_create_flag_success(self, client: TestClient, admin_token: str):
        """Test successful flag creation."""
        payload = {
            "name": "new_flag",
            "default": False,
            "rules": []
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "new_flag"
        assert data["default"] is False
        assert data["rules"] == []

    def test_create_flag_duplicate_name(self, client: TestClient, admin_token: str):
        """Test creating flag with duplicate name."""
        payload = {"name": "duplicate", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create first flag
        response1 = client.post("/flags", json=payload, headers=headers)
        assert response1.status_code == 200

        # Try to create flag with same name
        response2 = client.post("/flags", json=payload, headers=headers)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]

    def test_create_flag_invalid_name_empty(self, client: TestClient, admin_token: str):
        """Test creating flag with empty name."""
        payload = {"name": "", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422  # Pydantic validation error

    def test_create_flag_invalid_name_special_chars(self, client: TestClient, admin_token: str):
        """Test creating flag with invalid characters in name."""
        payload = {"name": "flag@#$%", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_create_flag_without_auth(self, client: TestClient):
        """Test creating flag without authentication."""
        payload = {"name": "unauth_flag", "default": False, "rules": []}
        response = client.post("/flags", json=payload)
        assert response.status_code == 403  # HTTPException raised by get_current_admin

    def test_create_flag_invalid_rule_type(self, client: TestClient, admin_token: str):
        """Test creating flag with invalid rule type."""
        payload = {
            "name": "bad_rules",
            "default": False,
            "rules": [
                {
                    "rule_type": "invalid_type",
                    "parameters": {},
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_create_flag_invalid_rule_missing_params(self, client: TestClient, admin_token: str):
        """Test creating flag with rule missing required parameters."""
        payload = {
            "name": "bad_params",
            "default": False,
            "rules": [
                {
                    "rule_type": "attribute_match",
                    "parameters": {
                        "attribute": "region"
                        # Missing 'operator' and 'values'
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_create_flag_invalid_percentage(self, client: TestClient, admin_token: str):
        """Test creating flag with percentage outside valid range."""
        payload = {
            "name": "bad_percentage",
            "default": False,
            "rules": [
                {
                    "rule_type": "percentage_rollout",
                    "parameters": {
                        "attribute": "user_id",
                        "percentage": 150  # Invalid
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422


class TestGetFlag:
    """Tests for GET /flags/{name} endpoint."""

    def test_get_flag_success(self, client: TestClient):
        """Test successfully retrieving a flag."""
        # Create flag
        with get_session() as session:
            flag = FeatureFlag(name="get-test", default=True, rules=[])
            session.add(flag)
            session.commit()

        response = client.get("/flags/get-test")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "get-test"
        assert data["default"] is True

    def test_get_flag_with_rules(self, client: TestClient):
        """Test retrieving flag with rules."""
        with get_session() as session:
            flag = FeatureFlag(
                name="get-with-rules",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {"attribute": "region", "operator": "in", "values": ["us"]},
                        "on": True,
                        "priority": 5
                    }
                ]
            )
            session.add(flag)
            session.commit()

        response = client.get("/flags/get-with-rules")
        assert response.status_code == 200
        data = response.json()
        assert len(data["rules"]) == 1


class TestUpdateFlag:
    """Tests for PUT /flags/{name} endpoint."""

    def test_update_flag_success(self, client: TestClient, admin_token: str):
        """Test successfully updating a flag."""
        # Create flag
        with get_session() as session:
            flag = FeatureFlag(name="update-test", default=False, rules=[])
            session.add(flag)
            session.commit()

        payload = {"name": "update-test", "default": True, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.put("/flags/update-test", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["default"] is True

    def test_update_flag_not_found(self, client: TestClient, admin_token: str):
        """Test updating non-existent flag."""
        payload = {"name": "nonexistent", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.put("/flags/nonexistent", json=payload, headers=headers)
        assert response.status_code == 404

    def test_update_flag_without_auth(self, client: TestClient):
        """Test updating flag without authentication."""
        with get_session() as session:
            flag = FeatureFlag(name="unauth-update", default=False, rules=[])
            session.add(flag)
            session.commit()

        payload = {"name": "unauth-update", "default": True, "rules": []}
        response = client.put("/flags/unauth-update", json=payload)
        assert response.status_code == 403

    def test_update_flag_non_admin_token(self, client: TestClient, user_token: str):
        """Test updating flag with non-admin token."""
        with get_session() as session:
            flag = FeatureFlag(name="user-update", default=False, rules=[])
            session.add(flag)
            session.commit()

        payload = {"name": "user-update", "default": True, "rules": []}
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.put("/flags/user-update", json=payload, headers=headers)
        assert response.status_code == 403


class TestDeleteFlag:
    """Tests for DELETE /flags/{name} endpoint."""

    def test_delete_flag_not_found(self, client: TestClient, admin_token: str):
        """Test deleting non-existent flag."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.delete("/flags/nonexistent", headers=headers)
        assert response.status_code == 404

    def test_delete_flag_without_auth(self, client: TestClient):
        """Test deleting flag without authentication."""
        with get_session() as session:
            flag = FeatureFlag(name="unauth-delete", default=False, rules=[])
            session.add(flag)
            session.commit()

        response = client.delete("/flags/unauth-delete")
        assert response.status_code == 403

    def test_delete_flag_non_admin_token(self, client: TestClient, user_token: str):
        """Test deleting flag with non-admin token."""
        with get_session() as session:
            flag = FeatureFlag(name="user-delete", default=False, rules=[])
            session.add(flag)
            session.commit()

        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.delete("/flags/user-delete", headers=headers)
        assert response.status_code == 403


class TestEvaluateFlag:
    """Tests for POST /evaluate endpoint."""

    def test_evaluate_flag_default(self, client: TestClient):
        """Test evaluating flag returns default when no rules match."""
        with get_session() as session:
            flag = FeatureFlag(name="eval-default", default=True, rules=[])
            session.add(flag)
            session.commit()

        payload = {"flag": "eval-default", "context": {"user_id": "user-123"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is True
        assert data["reason"] == "default"

    def test_evaluate_flag_attribute_match_in(self, client: TestClient):
        """Test evaluating with attribute_match 'in' operator."""
        with get_session() as session:
            flag = FeatureFlag(
                name="eval-in",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us", "eu"]
                        },
                        "on": True,
                        "priority": 10,
                        "id": "rule-1"
                    }
                ]
            )
            session.add(flag)
            session.commit()

        # Test matching value
        payload = {"flag": "eval-in", "context": {"region": "us"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is True
        assert "rule:" in data["reason"]

        # Test non-matching value
        payload = {"flag": "eval-in", "context": {"region": "asia"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is False
        assert data["reason"] == "default"

    def test_evaluate_flag_attribute_match_eq(self, client: TestClient):
        """Test evaluating with attribute_match 'eq' operator."""
        with get_session() as session:
            flag = FeatureFlag(
                name="eval-eq",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "tier",
                            "operator": "eq",
                            "values": ["premium"]
                        },
                        "on": True,
                        "priority": 10,
                        "id": "rule-2"
                    }
                ]
            )
            session.add(flag)
            session.commit()

        # Test matching value
        payload = {"flag": "eval-eq", "context": {"tier": "premium"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is True

        # Test non-matching value
        payload = {"flag": "eval-eq", "context": {"tier": "free"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is False

    def test_evaluate_flag_percentage_rollout(self, client: TestClient):
        """Test evaluating with percentage_rollout rule."""
        with get_session() as session:
            flag = FeatureFlag(
                name="eval-percent",
                default=False,
                rules=[
                    {
                        "rule_type": "percentage_rollout",
                        "parameters": {
                            "attribute": "user_id",
                            "percentage": 50
                        },
                        "on": True,
                        "priority": 10,
                        "id": "rule-3"
                    }
                ]
            )
            session.add(flag)
            session.commit()

        # Consistent user gets consistent result
        payload = {"flag": "eval-percent", "context": {"user_id": "user-123"}}
        response1 = client.post("/evaluate", json=payload)
        response2 = client.post("/evaluate", json=payload)
        assert response1.json()["value"] == response2.json()["value"]

    def test_evaluate_flag_not_found(self, client: TestClient):
        """Test evaluating non-existent flag returns flag_not_found."""
        payload = {"flag": "nonexistent-flag", "context": {}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is False
        assert data["reason"] == "flag_not_found"

    def test_evaluate_flag_missing_context_attribute(self, client: TestClient):
        """Test evaluating when context is missing required attribute."""
        with get_session() as session:
            flag = FeatureFlag(
                name="eval-missing-ctx",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"]
                        },
                        "on": True,
                        "priority": 10
                    }
                ]
            )
            session.add(flag)
            session.commit()

        # Context missing 'region' attribute
        payload = {"flag": "eval-missing-ctx", "context": {"user_id": "user-123"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is False  # Falls back to default
        assert data["reason"] == "default"

    def test_evaluate_flag_empty_context(self, client: TestClient):
        """Test evaluating with empty context."""
        with get_session() as session:
            flag = FeatureFlag(name="eval-empty-ctx", default=True, rules=[])
            session.add(flag)
            session.commit()

        payload = {"flag": "eval-empty-ctx", "context": {}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is True
        assert data["reason"] == "default"

    def test_evaluate_flag_invalid_context_type(self, client: TestClient):
        """Test evaluating with invalid context (not a dict)."""
        payload = {"flag": "any-flag", "context": "not-a-dict"}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 422  # Pydantic validation error

    def test_evaluate_flag_rule_priority(self, client: TestClient):
        """Test that rules are evaluated in priority order."""
        with get_session() as session:
            flag = FeatureFlag(
                name="eval-priority",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"]
                        },
                        "on": False,  # Returns False when matched
                        "priority": 10,  # Higher priority
                        "id": "rule-high"
                    },
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"]
                        },
                        "on": True,  # Would return True
                        "priority": 5,  # Lower priority (evaluated second)
                        "id": "rule-low"
                    }
                ]
            )
            session.add(flag)
            session.commit()

        # Should match first rule (higher priority) and return False
        payload = {"flag": "eval-priority", "context": {"region": "us"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is False  # From high priority rule
        assert "rule-high" in data["reason"]

    def test_evaluate_flag_rule_on_false(self, client: TestClient):
        """Test rule with on=False returns False when matched."""
        with get_session() as session:
            flag = FeatureFlag(
                name="eval-on-false",
                default=True,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"]
                        },
                        "on": False,  # Returns False (i.e., turn OFF)
                        "priority": 10,
                        "id": "rule-off"
                    }
                ]
            )
            session.add(flag)
            session.commit()

        payload = {"flag": "eval-on-false", "context": {"region": "us"}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["value"] is False  # Rule matched but on=False
