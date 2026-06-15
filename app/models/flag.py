from typing import List, Optional
from sqlmodel import Field, SQLModel, Column, JSON
from datetime import datetime
from uuid import uuid4


class FlagRule(SQLModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    rule_type: str
    parameters: dict
    on: bool = True
    priority: int = 0


class FeatureFlag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    default: bool = Field(default=False)
    rules: List[dict] = Field(sa_column=Column(JSON), default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
