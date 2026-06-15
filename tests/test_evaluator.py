"""
Unit tests for the flag evaluator service.
Tests evaluation logic, rule matching, caching, and error handling.
"""

import pytest
from app.db.session import init_db, get_session
from app.models.flag import FeatureFlag
from app.services.evaluator import Evaluator
from app.core.exceptions import (
    InvalidContextError,
    InvalidRuleDefinitionError,
    InvalidPercentageError,
    InvalidOperatorError,
)


@pytest.fixture(autouse=True)
def prepare_db(tmp_path, monkeypatch):
    """Initialize test database with temporary SQLite file."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    init_db()
    yield


class TestPercentageRollout:
    """Tests for percentage_rollout rule type."""

    def test_percentage_rollout_deterministic(self):
        """Test that percentage rollout is deterministic (same user always gets same result)."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="rollout",
                default=False,
                rules=[
                    {
                        "rule_type": "percentage_rollout",
                        "parameters": {"attribute": "user_id", "percentage": 50},
                        "on": True,
                        "priority": 10,
                        "id": "r1",
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Same user_id should always get same result
        r1 = ev.evaluate("rollout", {"user_id": "user-123"})
        r2 = ev.evaluate("rollout", {"user_id": "user-123"})
        assert r1["value"] == r2["value"]
        assert r1["reason"] == r2["reason"]

    def test_percentage_rollout_at_boundary_0(self):
        """Test that 0% rollout always returns False."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="rollout-0pct",
                default=False,
                rules=[
                    {
                        "rule_type": "percentage_rollout",
                        "parameters": {"attribute": "user_id", "percentage": 0},
                        "on": True,
                        "priority": 10,
                    }
                ],
            )
            s.add(f)
            s.commit()

        result = ev.evaluate("rollout-0pct", {"user_id": "any-user"})
        assert result["value"] is False
        assert result["reason"] == "default"

    def test_percentage_rollout_at_boundary_100(self):
        """Test that 100% rollout always returns True."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="rollout-100pct",
                default=False,
                rules=[
                    {
                        "rule_type": "percentage_rollout",
                        "parameters": {"attribute": "user_id", "percentage": 100},
                        "on": True,
                        "priority": 10,
                    }
                ],
            )
            s.add(f)
            s.commit()

        result = ev.evaluate("rollout-100pct", {"user_id": "any-user"})
        assert result["value"] is True
        assert "rule:" in result["reason"]

    def test_percentage_rollout_missing_context_attribute(self):
        """Test rollout when context is missing the bucketing attribute."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="rollout-missing-attr",
                default=True,
                rules=[
                    {
                        "rule_type": "percentage_rollout",
                        "parameters": {"attribute": "user_id", "percentage": 50},
                        "on": True,
                        "priority": 10,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Context missing 'user_id' attribute
        result = ev.evaluate("rollout-missing-attr", {"region": "us"})
        assert result["value"] is True  # Falls back to default
        assert result["reason"] == "default"

    def test_percentage_rollout_on_false(self):
        """Test percentage rollout with on=False (feature disabled when rule matches)."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="rollout-off",
                default=True,
                rules=[
                    {
                        "rule_type": "percentage_rollout",
                        "parameters": {"attribute": "user_id", "percentage": 100},
                        "on": False,  # Turn OFF when matched
                        "priority": 10,
                    }
                ],
            )
            s.add(f)
            s.commit()

        result = ev.evaluate("rollout-off", {"user_id": "user-123"})
        assert result["value"] is False  # Feature is turned OFF


class TestAttributeMatch:
    """Tests for attribute_match rule type."""

    def test_attribute_match_rule_in_operator(self):
        """Test attribute_match with 'in' operator."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="region-flag",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us", "eu"],
                        },
                        "on": True,
                        "priority": 5,
                        "id": "r2",
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Matching value
        result = ev.evaluate("region-flag", {"region": "us"})
        assert result["value"] is True
        assert "rule:" in result["reason"]

        # Non-matching value
        result = ev.evaluate("region-flag", {"region": "asia"})
        assert result["value"] is False
        assert result["reason"] == "default"

    def test_attribute_match_rule_eq_operator(self):
        """Test attribute_match with 'eq' operator."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="tier-flag",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "tier",
                            "operator": "eq",
                            "values": ["premium"],
                        },
                        "on": True,
                        "priority": 5,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Matching value
        result = ev.evaluate("tier-flag", {"tier": "premium"})
        assert result["value"] is True

        # Non-matching value
        result = ev.evaluate("tier-flag", {"tier": "free"})
        assert result["value"] is False
        assert result["reason"] == "default"

    def test_attribute_match_missing_context_attribute(self):
        """Test attribute_match when context is missing the attribute."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="attr-missing",
                default=True,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"],
                        },
                        "on": True,
                        "priority": 5,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Context missing 'region'
        result = ev.evaluate("attr-missing", {"user_id": "user-123"})
        assert result["value"] is True  # Falls back to default
        assert result["reason"] == "default"

    def test_attribute_match_numeric_values(self):
        """Test attribute_match with numeric context values."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="numeric-test",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "account_age_days",
                            "operator": "in",
                            "values": [30, 60, 90],
                        },
                        "on": True,
                        "priority": 5,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Numeric value in list
        result = ev.evaluate("numeric-test", {"account_age_days": 30})
        assert result["value"] is True

        # Numeric value not in list
        result = ev.evaluate("numeric-test", {"account_age_days": 45})
        assert result["value"] is False

    def test_attribute_match_string_conversion(self):
        """Test that values are converted to strings for comparison."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="string-convert",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "user_id",
                            "operator": "eq",
                            "values": ["123"],  # String in list
                        },
                        "on": True,
                        "priority": 5,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Integer context value should match string value in list
        result = ev.evaluate("string-convert", {"user_id": 123})
        assert result["value"] is True

    def test_attribute_match_on_false(self):
        """Test attribute_match with on=False."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="match-off",
                default=True,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"],
                        },
                        "on": False,  # Turn OFF when matched
                        "priority": 5,
                    }
                ],
            )
            s.add(f)
            s.commit()

        result = ev.evaluate("match-off", {"region": "us"})
        assert result["value"] is False  # Feature is OFF


class TestRulePriority:
    """Tests for rule priority and evaluation order."""

    def test_rule_priority_higher_wins(self):
        """Test that higher priority rules are evaluated first."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="priority-test",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"],
                        },
                        "on": False,  # Returns False
                        "priority": 10,  # Higher priority
                        "id": "high-priority",
                    },
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"],
                        },
                        "on": True,  # Would return True
                        "priority": 5,  # Lower priority
                        "id": "low-priority",
                    },
                ],
            )
            s.add(f)
            s.commit()

        # Should match high-priority rule first and return False
        result = ev.evaluate("priority-test", {"region": "us"})
        assert result["value"] is False
        assert "high-priority" in result["reason"]

    def test_rule_priority_default_zero(self):
        """Test that rules without priority default to 0."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="priority-default",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["us"],
                        },
                        "on": True,
                        # No priority specified (defaults to 0)
                    }
                ],
            )
            s.add(f)
            s.commit()

        result = ev.evaluate("priority-default", {"region": "us"})
        assert result["value"] is True  # Rule should still match


class TestDefaultValue:
    """Tests for default value fallback behavior."""

    def test_default_false(self):
        """Test default value when rules don't match."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="default-false",
                default=False,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["eu"],
                        },
                        "on": True,
                        "priority": 5,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # No rules match, should return default
        result = ev.evaluate("default-false", {"region": "us"})
        assert result["value"] is False
        assert result["reason"] == "default"

    def test_default_true(self):
        """Test default value when rules don't match."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="default-true",
                default=True,  # Default is ON
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "attribute": "region",
                            "operator": "in",
                            "values": ["eu"],
                        },
                        "on": False,  # Would turn OFF
                        "priority": 5,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # No rules match, should return default (True)
        result = ev.evaluate("default-true", {"region": "us"})
        assert result["value"] is True
        assert result["reason"] == "default"

    def test_empty_rules_returns_default(self):
        """Test that flag with no rules returns default value."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="no-rules",
                default=True,
                rules=[],  # No rules
            )
            s.add(f)
            s.commit()

        result = ev.evaluate("no-rules", {"user_id": "user-123"})
        assert result["value"] is True
        assert result["reason"] == "default"


class TestFlagNotFound:
    """Tests for when flag doesn't exist."""

    def test_flag_not_found_returns_false(self):
        """Test evaluation of non-existent flag returns False."""
        ev = Evaluator()
        result = ev.evaluate("nonexistent", {"user_id": "user-123"})
        assert result["value"] is False
        assert result["reason"] == "flag_not_found"


class TestInputValidation:
    """Tests for input validation in the evaluator."""

    def test_empty_flag_name_raises_error(self):
        """Test that empty flag name raises InvalidContextError."""
        ev = Evaluator()
        with pytest.raises(InvalidContextError):
            ev.evaluate("", {})

    def test_none_flag_name_raises_error(self):
        """Test that None flag name raises InvalidContextError."""
        ev = Evaluator()
        with pytest.raises(InvalidContextError):
            ev.evaluate(None, {})

    def test_non_dict_context_raises_error(self):
        """Test that non-dict context raises InvalidContextError."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(name="validation-test", default=False, rules=[])
            s.add(f)
            s.commit()

        with pytest.raises(InvalidContextError):
            ev.evaluate("validation-test", "not-a-dict")

    def test_invalid_rule_type_skips_rule(self):
        """Test that invalid rule types are skipped during evaluation."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="invalid-rule-type",
                default=True,
                rules=[
                    {
                        "rule_type": "unknown_type",
                        "parameters": {},
                        "on": True,
                        "priority": 10,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Should skip invalid rule and return default
        result = ev.evaluate("invalid-rule-type", {})
        assert result["value"] is True
        assert result["reason"] == "default"

    def test_invalid_percentage_value_skips_rule(self):
        """Test that percentage outside valid range (0-100) is handled."""
        ev = Evaluator()
        with get_session() as s:
            # Create a flag with invalid percentage stored (shouldn't happen with validation)
            # but test error handling if it does occur
            f = FeatureFlag(
                name="bad-percentage",
                default=True,
                rules=[
                    {
                        "rule_type": "percentage_rollout",
                        "parameters": {"attribute": "user_id", "percentage": 150},
                        "on": True,
                        "priority": 10,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Should skip invalid rule and return default
        result = ev.evaluate("bad-percentage", {"user_id": "user-123"})
        assert result["value"] is True
        assert result["reason"] == "default"

    def test_missing_attribute_in_rule_is_skipped(self):
        """Test that rule with missing attribute parameter is skipped."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(
                name="missing-attr-rule",
                default=True,
                rules=[
                    {
                        "rule_type": "attribute_match",
                        "parameters": {
                            "operator": "in",
                            "values": ["us"],
                            # Missing 'attribute'
                        },
                        "on": True,
                        "priority": 10,
                    }
                ],
            )
            s.add(f)
            s.commit()

        # Should skip invalid rule and return default
        result = ev.evaluate("missing-attr-rule", {})
        assert result["value"] is True
        assert result["reason"] == "default"


class TestCacheBehavior:
    """Tests for the caching behavior of the evaluator."""

    def test_first_evaluation_loads_from_db(self):
        """Test that first evaluation loads flag from database."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(name="cache-test", default=True, rules=[])
            s.add(f)
            s.commit()

        # Clear any potential cache
        ev.cache.invalidate("cache-test")

        # First evaluation should load from DB
        result = ev.evaluate("cache-test", {})
        assert result["value"] is True

    def test_second_evaluation_from_cache(self):
        """Test that second evaluation uses cached data."""
        ev = Evaluator()
        with get_session() as s:
            f = FeatureFlag(name="cache-hit", default=True, rules=[])
            s.add(f)
            s.commit()

        # First evaluation
        result1 = ev.evaluate("cache-hit", {})
        # Second evaluation (should be from cache)
        result2 = ev.evaluate("cache-hit", {})

        # Both should match because cache is consistent
        assert result1 == result2
