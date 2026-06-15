from typing import Optional, List
from app.db.session import get_session
from app.models.flag import FeatureFlag
from app.schemas.flag import FlagCreate
from app.core.logger import flag_logger
from sqlmodel import select


class FlagService:
    def list_flags(self) -> List[FeatureFlag]:
        """Get all feature flags"""
        flag_logger.debug("Retrieving all flags from database")
        with get_session() as session:
            flags = session.exec(select(FeatureFlag)).all()
            flag_logger.debug(f"Retrieved {len(flags)} flags from database")
            return flags
    
    def create_flag(self, payload: FlagCreate) -> FeatureFlag:
        """Create a new feature flag"""
        flag_logger.debug(f"Services: Creating flag '{payload.name}'")
        with get_session() as session:
            existing = session.exec(select(FeatureFlag).where(FeatureFlag.name == payload.name)).first()
            if existing:
                flag_logger.error(f"Flag '{payload.name}' already exists")
                raise ValueError("Flag already exists")
            flag = FeatureFlag(name=payload.name, default=payload.default, rules=[r.dict() for r in payload.rules])
            session.add(flag)
            session.commit()
            session.refresh(flag)
            flag_logger.debug(f"Services: Flag '{payload.name}' created successfully")
            return flag

    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name"""
        flag_logger.debug(f"Services: Retrieving flag '{name}' from database")
        with get_session() as session:
            flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
            return flag

    def update_flag(self, name: str, payload: FlagCreate) -> FeatureFlag:
        """Update an existing feature flag"""
        flag_logger.debug(f"Services: Updating flag '{name}'")
        with get_session() as session:
            flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
            if not flag:
                flag_logger.error(f"Flag '{name}' not found")
                raise ValueError("Flag not found")
            flag.default = payload.default
            flag.rules = [r.dict() for r in payload.rules]
            session.add(flag)
            session.commit()
            session.refresh(flag)
            flag_logger.debug(f"Services: Flag '{name}' updated successfully")
            return flag

    def delete_flag(self, name: str) -> bool:
        """Delete a feature flag"""
        flag_logger.debug(f"Services: Deleting flag '{name}'")
        with get_session() as session:
            flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
            if not flag:
                flag_logger.error(f"Flag '{name}' not found")
                raise ValueError("Flag not found")
            session.delete(flag)
            session.commit()
            flag_logger.debug(f"Services: Flag '{name}' deleted successfully")
            return True
