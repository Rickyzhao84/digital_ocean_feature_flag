from typing import Optional, List
from app.db.session import get_session
from app.models.flag import FeatureFlag
from app.schemas.flag import FlagCreate
from app.core.logger import flag_logger
from app.core.exceptions import (
    DuplicateFlagError,
    FlagNotFoundError,
    InvalidFlagNameError,
    InvalidRuleDefinitionError,
    DatabaseError,
)
from sqlmodel import select
from sqlalchemy.exc import IntegrityError


class FlagService:
    def _validate_flag_name(self, name: str) -> None:
        """Validate flag name format and constraints."""
        if not name or not name.strip():
            raise InvalidFlagNameError("Flag name cannot be empty")
        if len(name) > 255:
            raise InvalidFlagNameError("Flag name cannot exceed 255 characters")
        if not name.replace("_", "").replace("-", "").isalnum():
            raise InvalidFlagNameError(
                "Flag name must contain only alphanumeric characters, underscores, and hyphens"
            )

    def _serialize_rules(self, rules: list) -> list:
        """Serialize rule objects into dictionaries for storage."""
        serialized = []
        for rule in rules:
            rule_dict = rule.model_dump() if hasattr(rule, "model_dump") else rule
            serialized.append(rule_dict)
        return serialized

    def list_flags(self) -> List[FeatureFlag]:
        """Get all feature flags."""
        try:
            flag_logger.debug("Retrieving all flags from database")
            with get_session() as session:
                flags = session.exec(select(FeatureFlag)).all()
                flag_logger.debug(f"Retrieved {len(flags)} flags from database")
                return flags
        except Exception as e:
            flag_logger.error(f"Database error retrieving flags: {str(e)}")
            raise DatabaseError(f"Failed to retrieve flags: {str(e)}")

    def create_flag(self, payload: FlagCreate) -> FeatureFlag:
        """Create a new feature flag."""
        # Validate flag name
        self._validate_flag_name(payload.name)

        flag_logger.debug(f"Services: Creating flag '{payload.name}'")
        try:
            with get_session() as session:
                # Check for existing flag
                existing = session.exec(
                    select(FeatureFlag).where(FeatureFlag.name == payload.name)
                ).first()
                if existing:
                    flag_logger.error(f"Flag '{payload.name}' already exists")
                    raise DuplicateFlagError(f"Flag '{payload.name}' already exists")

                # Serialize rules (convert Pydantic models to dicts)
                serialized_rules = self._serialize_rules(payload.rules)

                flag = FeatureFlag(
                    name=payload.name,
                    default=payload.default,
                    rules=serialized_rules,
                )
                session.add(flag)
                session.commit()
                session.refresh(flag)
                flag_logger.info(
                    f"Services: Flag '{payload.name}' created successfully "
                    f"(default={flag.default}, rules={len(flag.rules)})"
                )
                return flag
        except DuplicateFlagError:
            raise  # Re-raise our custom exception
        except IntegrityError as e:
            flag_logger.error(f"Integrity error creating flag '{payload.name}': {str(e)}")
            raise DuplicateFlagError(f"Flag '{payload.name}' already exists")
        except Exception as e:
            flag_logger.error(f"Database error creating flag '{payload.name}': {str(e)}")
            raise DatabaseError(f"Failed to create flag: {str(e)}")

    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name."""
        try:
            flag_logger.debug(f"Services: Retrieving flag '{name}' from database")
            with get_session() as session:
                flag = session.exec(
                    select(FeatureFlag).where(FeatureFlag.name == name)
                ).first()
                if flag:
                    flag_logger.debug(f"Services: Flag '{name}' retrieved successfully")
                else:
                    flag_logger.warning(f"Services: Flag '{name}' not found")
                return flag
        except Exception as e:
            flag_logger.error(f"Database error retrieving flag '{name}': {str(e)}")
            raise DatabaseError(f"Failed to retrieve flag: {str(e)}")

    def update_flag(self, name: str, payload: FlagCreate) -> FeatureFlag:
        """Update an existing feature flag."""
        self._validate_flag_name(payload.name)

        flag_logger.debug(f"Services: Updating flag '{name}'")
        try:
            with get_session() as session:
                flag = session.exec(
                    select(FeatureFlag).where(FeatureFlag.name == name)
                ).first()
                if not flag:
                    flag_logger.error(f"Flag '{name}' not found")
                    raise FlagNotFoundError(f"Flag '{name}' not found")

                # Serialize rules (convert Pydantic models to dicts)
                serialized_rules = self._serialize_rules(payload.rules)

                flag.default = payload.default
                flag.rules = serialized_rules
                session.add(flag)
                session.commit()
                session.refresh(flag)
                flag_logger.info(
                    f"Services: Flag '{name}' updated successfully "
                    f"(default={flag.default}, rules={len(flag.rules)})"
                )
                return flag
        except FlagNotFoundError:
            raise  # Re-raise our custom exception
        except Exception as e:
            flag_logger.error(f"Database error updating flag '{name}': {str(e)}")
            raise DatabaseError(f"Failed to update flag: {str(e)}")

    def delete_flag(self, name: str) -> bool:
        """Delete a feature flag."""
        flag_logger.debug(f"Services: Deleting flag '{name}'")
        try:
            with get_session() as session:
                flag = session.exec(
                    select(FeatureFlag).where(FeatureFlag.name == name)
                ).first()
                if not flag:
                    flag_logger.error(f"Flag '{name}' not found")
                    raise FlagNotFoundError(f"Flag '{name}' not found")

                session.delete(flag)
                session.commit()
                flag_logger.info(f"Services: Flag '{name}' deleted successfully")
                return True
        except FlagNotFoundError:
            raise  # Re-raise our custom exception
        except Exception as e:
            flag_logger.error(f"Database error deleting flag '{name}': {str(e)}")
            raise DatabaseError(f"Failed to delete flag: {str(e)}")
