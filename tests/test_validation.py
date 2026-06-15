"""
Schema and input validation tests.
Tests Pydantic models, validators, and constraint enforcement.
"""

import pytest
from pydantic import ValidationError
from app.schemas.flag import (
    RuleIn,
    RuleType,
    FlagCreate,
    EvalRequest,
    AttributeMatchParameters,
    PercentageRolloutParameters,
)


class TestRuleTypeEnum:
    """Tests for RuleType enum validation."""

    def test_valid_attribute_match_type(self):
        """Test valid ATTRIBUTE_MATCH rule type."""
        rule = RuleIn(
            rule_type=RuleType.ATTRIBUTE_MATCH,
            parameters={
                "attribute": "region",
                "operator": "in",
                "values": ["us"]
            }
        )
        assert rule.rule_type == RuleType.ATTRIBUTE_MATCH

    def test_valid_percentage_rollout_type(self):
        """Test valid PERCENTAGE_ROLLOUT rule type."""
        rule = RuleIn(
            rule_type=RuleType.PERCENTAGE_ROLLOUT,
            parameters={"attribute": "user_id", "percentage": 50}
        )
        assert rule.rule_type == RuleType.PERCENTAGE_ROLLOUT

    def test_invalid_rule_type_string(self):
        """Test that invalid rule type string is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RuleIn(
                rule_type="invalid_type",
                parameters={}
            )
        assert "rule_type" in str(exc_info.value)


class TestAttributeMatchParameters:
    """Tests for attribute_match parameter validation."""

    def test_valid_in_operator(self):
        """Test valid 'in' operator."""
        params = AttributeMatchParameters(
            attribute="region",
            operator="in",
            values=["us", "eu"]
        )
        assert params.operator == "in"

    def test_valid_eq_operator(self):
        """Test valid 'eq' operator."""
        params = AttributeMatchParameters(
            attribute="tier",
            operator="eq",
            values=["premium"]
        )
        assert params.operator == "eq"

    def test_invalid_operator(self):
        """Test that invalid operator is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AttributeMatchParameters(
                attribute="region",
                operator="contains",
                values=["us"]
            )
        assert "operator" in str(exc_info.value).lower()

    def test_default_operator_is_eq(self):
        """Test that operator defaults to 'eq'."""
        params = AttributeMatchParameters(
            attribute="region",
            values=["us"]
        )
        assert params.operator == "eq"

    def test_empty_attribute_rejected(self):
        """Test that empty attribute is rejected."""
        with pytest.raises(ValidationError):
            AttributeMatchParameters(
                attribute="",
                operator="in",
                values=["us"]
            )

    def test_empty_values_list_rejected(self):
        """Test that empty values list is rejected."""
        with pytest.raises(ValidationError):
            AttributeMatchParameters(
                attribute="region",
                operator="in",
                values=[]
            )

    def test_none_values_rejected(self):
        """Test that missing values is rejected."""
        with pytest.raises(ValidationError):
            AttributeMatchParameters(
                attribute="region",
                operator="in"
                # Missing values
            )


class TestPercentageRolloutParameters:
    """Tests for percentage_rollout parameter validation."""

    def test_valid_percentage_at_zero(self):
        """Test valid percentage value of 0."""
        params = PercentageRolloutParameters(
            attribute="user_id",
            percentage=0
        )
        assert params.percentage == 0

    def test_valid_percentage_at_100(self):
        """Test valid percentage value of 100."""
        params = PercentageRolloutParameters(
            attribute="user_id",
            percentage=100
        )
        assert params.percentage == 100

    def test_valid_percentage_mid_range(self):
        """Test valid percentage value in mid-range."""
        params = PercentageRolloutParameters(
            attribute="user_id",
            percentage=50
        )
        assert params.percentage == 50

    def test_negative_percentage_rejected(self):
        """Test that negative percentage is rejected."""
        with pytest.raises(ValidationError):
            PercentageRolloutParameters(
                attribute="user_id",
                percentage=-10
            )

    def test_percentage_over_100_rejected(self):
        """Test that percentage over 100 is rejected."""
        with pytest.raises(ValidationError):
            PercentageRolloutParameters(
                attribute="user_id",
                percentage=150
            )

    def test_empty_attribute_rejected(self):
        """Test that empty attribute is rejected."""
        with pytest.raises(ValidationError):
            PercentageRolloutParameters(
                attribute="",
                percentage=50
            )

    def test_missing_percentage_rejected(self):
        """Test that missing percentage is rejected."""
        with pytest.raises(ValidationError):
            PercentageRolloutParameters(
                attribute="user_id"
                # Missing percentage
            )


class TestFlagCreateSchema:
    """Tests for FlagCreate schema validation."""

    def test_valid_flag_creation(self):
        """Test valid flag creation payload."""
        flag = FlagCreate(
            name="test-flag",
            default=False,
            rules=[]
        )
        assert flag.name == "test-flag"
        assert flag.default is False

    def test_flag_name_required(self):
        """Test that flag name is required."""
        with pytest.raises(ValidationError):
            FlagCreate(
                # Missing name
                default=False,
                rules=[]
            )

    def test_default_defaults_to_false(self):
        """Test that default value defaults to False."""
        flag = FlagCreate(name="test-flag", rules=[])
        assert flag.default is False

    def test_rules_defaults_to_empty_list(self):
        """Test that rules defaults to empty list."""
        flag = FlagCreate(name="test-flag")
        assert flag.rules == []

    def test_flag_name_with_valid_characters(self):
        """Test flag names with valid characters."""
        valid_names = [
            "simple-flag",
            "flag_with_underscore",
            "FLAG_ALL_CAPS",
            "flag-123",
            "f",
            "a" * 255  # Max length
        ]
        
        for name in valid_names:
            flag = FlagCreate(name=name)
            assert flag.name == name

    def test_flag_name_with_invalid_characters(self):
        """Test flag names with invalid characters are rejected."""
        invalid_names = [
            "flag@domain",
            "flag.with.dots",
            "flag with spaces",
            "flag#tag",
            "flag$var",
            ""  # Empty
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError):
                FlagCreate(name=name)

    def test_flag_name_too_long(self):
        """Test flag name exceeding 255 characters is rejected."""
        with pytest.raises(ValidationError):
            FlagCreate(name="a" * 256)

    def test_flag_with_percentage_rollout_rule(self):
        """Test flag with percentage_rollout rule."""
        flag = FlagCreate(
            name="rollout-flag",
            default=False,
            rules=[
                {
                    "rule_type": "percentage_rollout",
                    "parameters": {
                        "attribute": "user_id",
                        "percentage": 50
                    }
                }
            ]
        )
        assert len(flag.rules) == 1
        assert flag.rules[0].rule_type == RuleType.PERCENTAGE_ROLLOUT

    def test_flag_with_attribute_match_rule(self):
        """Test flag with attribute_match rule."""
        flag = FlagCreate(
            name="match-flag",
            default=False,
            rules=[
                {
                    "rule_type": "attribute_match",
                    "parameters": {
                        "attribute": "region",
                        "operator": "in",
                        "values": ["us", "eu"]
                    }
                }
            ]
        )
        assert len(flag.rules) == 1
        assert flag.rules[0].rule_type == RuleType.ATTRIBUTE_MATCH

    def test_flag_with_multiple_rules(self):
        """Test flag with multiple rules."""
        flag = FlagCreate(
            name="multi-rule",
            default=False,
            rules=[
                {
                    "rule_type": "percentage_rollout",
                    "parameters": {"attribute": "user_id", "percentage": 50},
                    "priority": 10
                },
                {
                    "rule_type": "attribute_match",
                    "parameters": {
                        "attribute": "region",
                        "operator": "in",
                        "values": ["us"]
                    },
                    "priority": 5
                }
            ]
        )
        assert len(flag.rules) == 2
        assert flag.rules[0].priority == 10
        assert flag.rules[1].priority == 5


class TestEvalRequestSchema:
    """Tests for EvalRequest schema validation."""

    def test_valid_eval_request(self):
        """Test valid evaluation request."""
        req = EvalRequest(
            flag="test-flag",
            context={"user_id": "user-123"}
        )
        assert req.flag == "test-flag"
        assert req.context["user_id"] == "user-123"

    def test_flag_required(self):
        """Test that flag name is required."""
        with pytest.raises(ValidationError):
            EvalRequest(
                # Missing flag
                context={}
            )

    def test_empty_flag_name_rejected(self):
        """Test that empty flag name is rejected."""
        with pytest.raises(ValidationError):
            EvalRequest(flag="", context={})

    def test_context_defaults_to_empty_dict(self):
        """Test that context defaults to empty dict."""
        req = EvalRequest(flag="test-flag")
        assert req.context == {}

    def test_context_none_converted_to_dict(self):
        """Test that None context is converted to empty dict."""
        req = EvalRequest(flag="test-flag", context=None)
        assert req.context == {}

    def test_context_must_be_dict(self):
        """Test that context must be a dict."""
        with pytest.raises(ValidationError):
            EvalRequest(flag="test-flag", context="not-a-dict")

    def test_context_with_various_types(self):
        """Test context with various data types."""
        context = {
            "user_id": "user-123",
            "account_age_days": 30,
            "is_premium": True,
            "settings": {"theme": "dark"},
            "tags": ["beta", "vip"]
        }
        req = EvalRequest(flag="test-flag", context=context)
        assert req.context == context


class TestRuleInValidation:
    """Tests for RuleIn validation and polymorphism."""

    def test_rule_in_with_on_field(self):
        """Test RuleIn with explicit on value."""
        rule = RuleIn(
            rule_type=RuleType.ATTRIBUTE_MATCH,
            parameters={
                "attribute": "region",
                "operator": "in",
                "values": ["us"]
            },
            on=False
        )
        assert rule.on is False

    def test_rule_in_on_defaults_to_true(self):
        """Test that on defaults to True."""
        rule = RuleIn(
            rule_type=RuleType.ATTRIBUTE_MATCH,
            parameters={
                "attribute": "region",
                "operator": "in",
                "values": ["us"]
            }
        )
        assert rule.on is True

    def test_rule_in_with_priority(self):
        """Test RuleIn with priority field."""
        rule = RuleIn(
            rule_type=RuleType.ATTRIBUTE_MATCH,
            parameters={
                "attribute": "region",
                "operator": "in",
                "values": ["us"]
            },
            priority=100
        )
        assert rule.priority == 100

    def test_rule_in_priority_defaults_to_zero(self):
        """Test that priority defaults to 0."""
        rule = RuleIn(
            rule_type=RuleType.ATTRIBUTE_MATCH,
            parameters={
                "attribute": "region",
                "operator": "in",
                "values": ["us"]
            }
        )
        assert rule.priority == 0

    def test_rule_in_with_id(self):
        """Test RuleIn with optional id field."""
        rule = RuleIn(
            rule_type=RuleType.ATTRIBUTE_MATCH,
            parameters={
                "attribute": "region",
                "operator": "in",
                "values": ["us"]
            },
            id="custom-rule-id"
        )
        assert rule.id == "custom-rule-id"

    def test_rule_in_id_defaults_to_none(self):
        """Test that id defaults to None."""
        rule = RuleIn(
            rule_type=RuleType.ATTRIBUTE_MATCH,
            parameters={
                "attribute": "region",
                "operator": "in",
                "values": ["us"]
            }
        )
        assert rule.id is None

    def test_rule_in_negative_priority_rejected(self):
        """Test that negative priority is rejected."""
        with pytest.raises(ValidationError):
            RuleIn(
                rule_type=RuleType.ATTRIBUTE_MATCH,
                parameters={
                    "attribute": "region",
                    "operator": "in",
                    "values": ["us"]
                },
                priority=-1
            )
