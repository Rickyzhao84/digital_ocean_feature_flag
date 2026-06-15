"""
Error handling and validation tests for the feature flag API.
Tests input validation, error responses, and edge cases.
"""

import pytest
from fastapi.testclient import TestClient
from app.db.session import get_session
from app.models.flag import FeatureFlag


class TestFlagNameValidation:
    """Tests for flag name validation."""

    def test_flag_name_too_long(self, client: TestClient, admin_token: str):
        """Test that flag names longer than 255 characters are rejected."""
        long_name = "a" * 256
        payload = {"name": long_name, "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_flag_name_valid_characters(self, client: TestClient, admin_token: str):
        """Test flag names with valid characters (alphanumeric, underscore, hyphen)."""
        valid_names = ["flag-1", "flag_2", "flag3", "FLAG_TEST-123"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        for name in valid_names:
            payload = {"name": name, "default": False, "rules": []}
            response = client.post("/flags", json=payload, headers=headers)
            assert response.status_code == 200, f"Name '{name}' should be valid"

    def test_flag_name_invalid_characters(self, client: TestClient, admin_token: str):
        """Test flag names with invalid characters are rejected."""
        invalid_names = ["flag@host", "flag#tag", "flag$var", "flag with space", "flag.name"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        for name in invalid_names:
            payload = {"name": name, "default": False, "rules": []}
            response = client.post("/flags", json=payload, headers=headers)
            assert response.status_code == 422, f"Name '{name}' should be invalid"


class TestRuleValidation:
    """Tests for rule definition validation."""

    def test_attribute_match_missing_attribute(self, client: TestClient, admin_token: str):
        """Test attribute_match rule with missing 'attribute' parameter."""
        payload = {
            "name": "missing-attr",
            "default": False,
            "rules": [
                {
                    "rule_type": "attribute_match",
                    "parameters": {
                        # Missing 'attribute'
                        "operator": "in",
                        "values": ["us"]
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_attribute_match_missing_values(self, client: TestClient, admin_token: str):
        """Test attribute_match rule with missing 'values' parameter."""
        payload = {
            "name": "missing-values",
            "default": False,
            "rules": [
                {
                    "rule_type": "attribute_match",
                    "parameters": {
                        "attribute": "region",
                        "operator": "in"
                        # Missing 'values'
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_attribute_match_empty_values(self, client: TestClient, admin_token: str):
        """Test attribute_match rule with empty values list."""
        payload = {
            "name": "empty-values",
            "default": False,
            "rules": [
                {
                    "rule_type": "attribute_match",
                    "parameters": {
                        "attribute": "region",
                        "operator": "in",
                        "values": []  # Empty list
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_attribute_match_invalid_operator(self, client: TestClient, admin_token: str):
        """Test attribute_match rule with invalid operator."""
        payload = {
            "name": "invalid-op",
            "default": False,
            "rules": [
                {
                    "rule_type": "attribute_match",
                    "parameters": {
                        "attribute": "region",
                        "operator": "contains",  # Invalid operator
                        "values": ["us"]
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_percentage_rollout_missing_attribute(self, client: TestClient, admin_token: str):
        """Test percentage_rollout rule with missing 'attribute' parameter."""
        payload = {
            "name": "rollout-missing-attr",
            "default": False,
            "rules": [
                {
                    "rule_type": "percentage_rollout",
                    "parameters": {
                        # Missing 'attribute'
                        "percentage": 50
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_percentage_rollout_missing_percentage(self, client: TestClient, admin_token: str):
        """Test percentage_rollout rule with missing 'percentage' parameter."""
        payload = {
            "name": "rollout-missing-pct",
            "default": False,
            "rules": [
                {
                    "rule_type": "percentage_rollout",
                    "parameters": {
                        "attribute": "user_id"
                        # Missing 'percentage'
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_percentage_rollout_invalid_percentage_negative(self, client: TestClient, admin_token: str):
        """Test percentage_rollout with negative percentage."""
        payload = {
            "name": "rollout-negative-pct",
            "default": False,
            "rules": [
                {
                    "rule_type": "percentage_rollout",
                    "parameters": {
                        "attribute": "user_id",
                        "percentage": -10  # Invalid
                    },
                    "on": True,
                    "priority": 0
                }
            ]
        }
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post("/flags", json=payload, headers=headers)
        assert response.status_code == 422

    def test_percentage_rollout_invalid_percentage_over_100(self, client: TestClient, admin_token: str):
        """Test percentage_rollout with percentage > 100."""
        payload = {
            "name": "rollout-over-100",
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

class TestContextValidation:
    """Tests for context validation during evaluation."""

    def test_evaluate_context_not_dict(self, client: TestClient):
        """Test that context must be a dictionary."""
        with get_session() as session:
            flag = FeatureFlag(name="ctx-test", default=False, rules=[])
            session.add(flag)
            session.commit()

        # Test with list instead of dict
        payload = {"flag": "ctx-test", "context": ["user-123"]}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 422

        # Test with string instead of dict
        payload = {"flag": "ctx-test", "context": "user-123"}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 422

    def test_evaluate_empty_flag_name(self, client: TestClient):
        """Test that flag name cannot be empty."""
        payload = {"flag": "", "context": {}}
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 422

    def test_evaluate_with_none_context(self, client: TestClient):
        """Test that None context is converted to empty dict."""
        with get_session() as session:
            flag = FeatureFlag(name="none-ctx", default=True, rules=[])
            session.add(flag)
            session.commit()

        # Pydantic should handle null -> empty dict conversion
        payload = {"flag": "none-ctx", "context": None}
        response = client.post("/evaluate", json=payload)
        # Should work with default empty dict
        assert response.status_code == 200
        assert response.json()["value"] is True


class TestErrorResponses:
    """Tests for proper error response formatting."""

    def test_duplicate_flag_error_message(self, client: TestClient, admin_token: str):
        """Test error message when creating duplicate flag."""
        payload = {"name": "duplicate-test", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create first flag
        response1 = client.post("/flags", json=payload, headers=headers)
        assert response1.status_code == 200

        # Try duplicate
        response2 = client.post("/flags", json=payload, headers=headers)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]

    def test_update_nonexistent_flag_error(self, client: TestClient, admin_token: str):
        """Test error when updating non-existent flag."""
        payload = {"name": "nonexistent-update", "default": False, "rules": []}
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.put("/flags/nonexistent-update", json=payload, headers=headers)
        assert response.status_code == 404

    def test_delete_nonexistent_flag_error(self, client: TestClient, admin_token: str):
        """Test error when deleting non-existent flag."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.delete("/flags/nonexistent-delete-xyz", headers=headers)
        assert response.status_code == 404
