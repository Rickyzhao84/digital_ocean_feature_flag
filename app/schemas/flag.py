from typing import List, Optional, Any
from pydantic import BaseModel


class RuleIn(BaseModel):
    rule_type: str
    parameters: dict
    on: bool = True
    priority: int = 0


class FlagCreate(BaseModel):
    name: str
    default: bool = False
    rules: List[RuleIn] = []


class FlagOut(BaseModel):
    name: str
    default: bool
    rules: List[Any]


class EvalRequest(BaseModel):
    flag: str
    context: dict


class EvalResponse(BaseModel):
    flag: str
    value: bool
    reason: Optional[str]
