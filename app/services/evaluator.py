import hashlib
import json
from typing import Any, Dict, Optional
from app.db.session import get_session
from app.models.flag import FeatureFlag
from app.cache.cache import FlagCache
from sqlmodel import select


class Evaluator:
    def __init__(self):
        self.cache = FlagCache()

    def _hash_user(self, value: str) -> int:
        h = hashlib.sha256(value.encode()).hexdigest()
        return int(h, 16) % 100

    def evaluate(self, flag_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Try cache first
        cached = self.cache.get(flag_name)
        if cached is None:
            # load from DB
            with get_session() as session:
                flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == flag_name)).first()
                if not flag:
                    return {"value": False, "reason": "flag_not_found"}
                self.cache.set(flag_name, {"default": flag.default, "rules": flag.rules})
                cached = self.cache.get(flag_name)

        # Evaluate rules in priority order
        rules = sorted(cached["rules"], key=lambda r: r.get("priority", 0), reverse=True)
        for r in rules:
            rtype = r.get("rule_type")
            params = r.get("parameters", {})
            on_state = r.get("on", True)
            if rtype == "attribute_match":
                attr = params.get("attribute")
                operator = params.get("operator", "eq")
                values = params.get("values", [])
                ctx_val = context.get(attr)
                if ctx_val is None:
                    continue
                if operator == "in" and str(ctx_val) in [str(v) for v in values]:
                    return {"value": on_state, "reason": f"rule:{r.get('id','') or 'attribute_match'}"}
                if operator == "eq" and str(ctx_val) == str(values[0]) if values else False:
                    return {"value": on_state, "reason": f"rule:{r.get('id','') or 'attribute_match'}"}
            elif rtype == "percentage_rollout":
                attr = params.get("attribute")
                pct = int(params.get("percentage", 0))
                ctx_val = context.get(attr)
                if ctx_val is None:
                    continue
                bucket = self._hash_user(str(ctx_val))
                if bucket < pct:
                    return {"value": on_state, "reason": f"rule:{r.get('id','') or 'percentage_rollout'}"}

        # fallback to default
        return {"value": cached.get("default", False), "reason": "default"}

    def invalidate_flag(self, flag_name: str):
        self.cache.invalidate(flag_name)
