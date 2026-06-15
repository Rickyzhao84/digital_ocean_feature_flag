from typing import List, Optional, Any, Dict, Union
from enum import Enum
from pydantic import BaseModel, Field, validator, root_validator


class RuleType(str, Enum):
    """Valid rule types for feature flag evaluation."""
    ATTRIBUTE_MATCH = "attribute_match"
    PERCENTAGE_ROLLOUT = "percentage_rollout"


class AttributeMatchParameters(BaseModel):
    """Parameters for attribute_match rule type."""
    attribute: str = Field(..., description="The context attribute to match against")
    operator: str = Field(default="eq", description="Comparison operator: 'eq' or 'in'")
    values: List[Any] = Field(..., description="Values to compare against")

    @validator("operator")
    def validate_operator(cls, v: str) -> str:
        """Ensure operator is one of the supported values."""
        if v not in ["eq", "in"]:
            raise ValueError(f"Invalid operator: {v}. Must be 'eq' or 'in'")
        return v

    @validator("attribute")
    def validate_attribute(cls, v: str) -> str:
        """Ensure attribute is not empty."""
        if not v or not v.strip():
            raise ValueError("Attribute cannot be empty")
        return v

    @validator("values")
    def validate_values(cls, v: List[Any]) -> List[Any]:
        """Ensure values is not empty."""
        if not v:
            raise ValueError("Values cannot be empty for attribute_match rule")
        return v


class PercentageRolloutParameters(BaseModel):
    """Parameters for percentage_rollout rule type."""
    attribute: str = Field(..., description="The context attribute to use for bucketing (typically user_id)")
    percentage: int = Field(..., ge=0, le=100, description="Percentage of users to include (0-100)")

    @validator("attribute")
    def validate_attribute(cls, v: str) -> str:
        """Ensure attribute is not empty."""
        if not v or not v.strip():
            raise ValueError("Attribute cannot be empty")
        return v


class RuleIn(BaseModel):
    """Base rule definition with type-specific parameters."""
    rule_type: RuleType = Field(..., description="The type of rule")
    parameters: Union[AttributeMatchParameters, PercentageRolloutParameters] = Field(
        ..., description="Rule-specific parameters"
    )
    on: bool = Field(default=True, description="Whether to return on_state when rule matches")
    priority: int = Field(default=0, ge=0, description="Rule evaluation priority (higher first)")
    id: Optional[str] = Field(default=None, description="Optional rule identifier")

    @root_validator(pre=True)
    def validate_rule_type(cls, values: Any) -> Any:
        """Validate that parameters match the rule_type."""
        rule_type = values.get("rule_type")
        params = values.get("parameters", {})

        # Convert string parameters dict to typed model if needed
        if isinstance(params, dict):
            try:
                if rule_type == RuleType.ATTRIBUTE_MATCH or rule_type == "attribute_match":
                    values["parameters"] = AttributeMatchParameters(**params)
                elif rule_type == RuleType.PERCENTAGE_ROLLOUT or rule_type == "percentage_rollout":
                    values["parameters"] = PercentageRolloutParameters(**params)
            except ValueError as e:
                raise ValueError(f"Invalid parameters for {rule_type}: {str(e)}")

        return values


class FlagCreate(BaseModel):
    """Request schema for creating or updating a feature flag."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        regex=r"^[a-zA-Z0-9_-]+$",
        description="Unique flag name (alphanumeric, underscores, and hyphens only)"
    )
    default: bool = Field(default=False, description="Default value when no rules match")
    rules: List[RuleIn] = Field(default_factory=list, description="List of evaluation rules")

    @validator("name")
    def validate_name(cls, v: str) -> str:
        """Ensure name is valid."""
        if not v or not v.strip():
            raise ValueError("Flag name cannot be empty")
        if len(v) > 255:
            raise ValueError("Flag name cannot exceed 255 characters")
        return v.strip()


class FlagOut(BaseModel):
    """Response schema for a feature flag."""
    name: str
    default: bool
    rules: List[Any]


class ContextIn(BaseModel):
    """Schema for evaluation context validation."""
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context attributes for rule evaluation"
    )

    @validator("context")
    def validate_context(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure context is a valid dictionary."""
        if not isinstance(v, dict):
            raise ValueError("Context must be a dictionary")
        return v


class EvalRequest(BaseModel):
    """Request schema for flag evaluation."""
    flag: str = Field(..., description="Name of the flag to evaluate")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context attributes for rule evaluation"
    )

    @validator("flag")
    def validate_flag(cls, v: str) -> str:
        """Ensure flag name is not empty."""
        if not v or not v.strip():
            raise ValueError("Flag name cannot be empty")
        return v.strip()

    @validator("context", pre=True, always=True)
    def validate_context(cls, v: Any) -> Dict[str, Any]:
        """Ensure context is a valid dictionary."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("Context must be a dictionary")
        return v


class EvalResponse(BaseModel):
    """Response schema for flag evaluation."""
    flag: str
    value: bool
    reason: Optional[str] = None
