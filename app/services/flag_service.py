from typing import Optional
from app.db.session import get_session
from app.models.flag import FeatureFlag
from app.schemas.flag import FlagCreate
from sqlmodel import select


class FlagService:
    def create_flag(self, payload: FlagCreate) -> FeatureFlag:
        with get_session() as session:
            existing = session.exec(select(FeatureFlag).where(FeatureFlag.name == payload.name)).first()
            if existing:
                raise ValueError("Flag already exists")
            flag = FeatureFlag(name=payload.name, default=payload.default, rules=[r.dict() for r in payload.rules])
            session.add(flag)
            session.commit()
            session.refresh(flag)
            return flag

    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        with get_session() as session:
            flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
            return flag

    def update_flag(self, name: str, payload: FlagCreate) -> FeatureFlag:
        with get_session() as session:
            flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
            if not flag:
                raise ValueError("Flag not found")
            flag.default = payload.default
            flag.rules = [r.dict() for r in payload.rules]
            session.add(flag)
            session.commit()
            session.refresh(flag)
            return flag

    def delete_flag(self, name: str) -> bool:
        with get_session() as session:
            flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
            if not flag:
                raise ValueError("Flag not found")
            session.delete(flag)
            session.commit()
            return True
