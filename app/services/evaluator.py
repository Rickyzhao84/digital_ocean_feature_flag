import hashlib
import json
from typing import Any, Dict, Optional
from enum import Enum
from app.db.session import get_session
from app.models.flag import FeatureFlag
from app.cache.cache import FlagCache
from app.core.logger import evaluator_logger
from app.core.exceptions import (
    InvalidContextError,
    InvalidRuleDefinitionError,
    InvalidPercentageError,
    InvalidOperatorError,
)
from sqlmodel import select


class Operator(str, Enum):
    """Supported operators for attribute_match rules."""
    EQUALS = "eq"
    IN = "in"


class Evaluator:
    def __init__(self):
        self.cache = FlagCache()

    def _hash_user(self, value: str) -> int:
        """Hash a user identifier to a bucket (0-99) using SHA256."""
        h = hashlib.sha256(value.encode()).hexdigest()
        return int(h, 16) % 100

    def _evaluate_attribute_match_rule(
        self, rule: Dict[str, Any], context: Dict[str, Any]
    ) -> Optional[bool]:
        """
        Evaluate an attribute_match rule.
        Returns True if rule matched and on_state should be True, False if matched but on_state is False.
        Returns None if rule didn't match.
        """
        params = rule.get("parameters", {})
        on_state = rule.get("on", True)

        # Validate rule structure
        attr = params.get("attribute")
        if not attr:
            evaluator_logger.warning(
                f"Invalid attribute_match rule: missing 'attribute' parameter"
            )
            raise InvalidRuleDefinitionError(
                "attribute_match rule missing required 'attribute' parameter"
            )

        operator = params.get("operator", "eq")
        values = params.get("values", [])

        # Validate operator
        if operator not in [Operator.EQUALS.value, Operator.IN.value]:
            raise InvalidOperatorError(
                f"Invalid operator '{operator}'. Must be 'eq' or 'in'"
            )

        # Validate values
        if not values:
            raise InvalidRuleDefinitionError(
                "attribute_match rule missing required 'values' parameter"
            )

        # Get context value
        ctx_val = context.get(attr)
        if ctx_val is None:
            evaluator_logger.debug(
                f"Context missing attribute '{attr}' for attribute_match rule"
            )
            return None  # Rule doesn't apply if attribute not in context

        # Evaluate operator
        matched = False
        if operator == Operator.IN.value:
            matched = str(ctx_val) in [str(v) for v in values]
        elif operator == Operator.EQUALS.value:
            matched = str(ctx_val) == str(values[0]) if values else False

        if matched:
            evaluator_logger.debug(
                f"attribute_match rule matched: {attr}={ctx_val} ({operator} {values})"
            )
            return on_state

        return None  # Rule didn't match

    def _evaluate_percentage_rollout_rule(
        self, rule: Dict[str, Any], context: Dict[str, Any]
    ) -> Optional[bool]:
        """
        Evaluate a percentage_rollout rule.
        Returns True if user is bucketed into rollout, False if on_state is False.
        Returns None if rule doesn't apply.
        """
        params = rule.get("parameters", {})
        on_state = rule.get("on", True)

        # Validate rule structure
        attr = params.get("attribute")
        if not attr:
            evaluator_logger.warning(
                f"Invalid percentage_rollout rule: missing 'attribute' parameter"
            )
            raise InvalidRuleDefinitionError(
                "percentage_rollout rule missing required 'attribute' parameter"
            )

        try:
            pct = int(params.get("percentage", 0))
        except (ValueError, TypeError):
            raise InvalidPercentageError(
                f"Invalid percentage value: {params.get('percentage')}. Must be an integer."
            )

        # Validate percentage range
        if pct < 0 or pct > 100:
            raise InvalidPercentageError(
                f"Invalid percentage value: {pct}. Must be between 0 and 100."
            )

        # Get context value
        ctx_val = context.get(attr)
        if ctx_val is None:
            evaluator_logger.debug(
                f"Context missing attribute '{attr}' for percentage_rollout rule"
            )
            return None  # Rule doesn't apply if attribute not in context

        # Hash and bucket
        bucket = self._hash_user(str(ctx_val))
        if bucket < pct:
            evaluator_logger.debug(
                f"percentage_rollout rule matched: bucket={bucket} < percentage={pct}"
            )
            return on_state

        return None  # User not bucketed into rollout

    def evaluate(self, flag_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a feature flag based on context attributes.
        Returns a dictionary with 'value' (bool) and 'reason' (str).
        """
        # Validate inputs
        if not flag_name or not flag_name.strip():
            evaluator_logger.error("Flag name cannot be empty")
            raise InvalidContextError("Flag name cannot be empty")

        if not isinstance(context, dict):
            evaluator_logger.error(
                f"Context must be a dictionary, got {type(context).__name__}"
            )
            raise InvalidContextError("Context must be a dictionary")

        evaluator_logger.debug(
            f"Attempting to retrieve {flag_name} from cache"
        )
        cached = self.cache.get(flag_name)
        if cached is None:
            evaluator_logger.debug(
                f"Cache miss for {flag_name}, loading from database"
            )
            # Load from DB
            with get_session() as session:
                flag = session.exec(
                    select(FeatureFlag).where(FeatureFlag.name == flag_name)
                ).first()
                if not flag:
                    evaluator_logger.warning(
                        f"Flag '{flag_name}' not found in database"
                    )
                    return {"value": False, "reason": "flag_not_found"}
                self.cache.set(
                    flag_name, {"default": flag.default, "rules": flag.rules}
                )
                evaluator_logger.debug(f"Flag '{flag_name}' loaded and cached")
                cached = self.cache.get(flag_name)
        else:
            evaluator_logger.debug(f"Cache hit for {flag_name}")

        # Evaluate rules in priority order (higher priority first)
        rules = sorted(
            cached["rules"], key=lambda r: r.get("priority", 0), reverse=True
        )
        evaluator_logger.debug(f"Evaluating {len(rules)} rules for {flag_name}")

        for rule in rules:
            rtype = rule.get("rule_type")
            rule_id = rule.get("id", rtype)

            try:
                result = None
                if rtype == "attribute_match":
                    result = self._evaluate_attribute_match_rule(rule, context)
                elif rtype == "percentage_rollout":
                    result = self._evaluate_percentage_rollout_rule(rule, context)
                else:
                    evaluator_logger.warning(
                        f"Unknown rule type '{rtype}' for flag '{flag_name}'"
                    )
                    raise InvalidRuleDefinitionError(
                        f"Unknown rule type: {rtype}"
                    )

                # If rule matched, return result
                if result is not None:
                    evaluator_logger.debug(
                        f"Rule matched for {flag_name}: {rtype} → {result}"
                    )
                    return {"value": result, "reason": f"rule:{rule_id}"}

            except (InvalidRuleDefinitionError, InvalidPercentageError, InvalidOperatorError) as e:
                evaluator_logger.error(
                    f"Error evaluating rule for {flag_name}: {str(e)}"
                )
                # Skip invalid rules and continue to next rule or default
                continue

        # No rules matched, use default
        default_value = cached.get("default", False)
        evaluator_logger.debug(
            f"No rules matched for {flag_name}, using default: {default_value}"
        )
        return {"value": default_value, "reason": "default"}

    def invalidate_flag(self, flag_name: str):
        """Invalidate the cached entry for a flag."""
        evaluator_logger.debug(f"Invalidating cache for flag '{flag_name}'")
        self.cache.invalidate(flag_name)
