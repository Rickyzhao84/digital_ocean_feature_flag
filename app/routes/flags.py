from fastapi import APIRouter, HTTPException, Depends
from typing import List, Any, Dict
from app.schemas.flag import FlagCreate, FlagOut, EvalRequest, EvalResponse
from app.services.evaluator import Evaluator
from app.services.flag_service import FlagService
from app.core.security import get_current_admin
from app.core.logger import flag_logger
from app.core.exceptions import (
    DuplicateFlagError,
    FlagNotFoundError,
    InvalidFlagNameError,
    InvalidRuleDefinitionError,
    InvalidContextError,
    DatabaseError,
)

router = APIRouter()
evaluator = Evaluator()
flag_service = FlagService()


@router.get("/flags", response_model=List[FlagOut])
def list_flags():
    """List all feature flags"""
    flag_logger.info("Fetching all feature flags")
    try:
        flags = flag_service.list_flags()
        flag_logger.info(f"Successfully retrieved {len(flags)} feature flags")
        return [
            FlagOut(name=flag.name, default=flag.default, rules=flag.rules)
            for flag in flags
        ]
    except DatabaseError as e:
        flag_logger.error(f"Database error listing flags: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve flags")
    except Exception as e:
        flag_logger.error(f"Unexpected error listing flags: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/flags", response_model=FlagOut)
def create_flag(payload: FlagCreate, admin: Dict[str, Any] = Depends(get_current_admin)):
    """Create a new feature flag (requires admin)"""
    flag_logger.info(f"Creating new feature flag: {payload.name} (admin: {admin.get('sub')})")
    try:
        flag = flag_service.create_flag(payload)
        flag_logger.info(
            f"Successfully created feature flag: {payload.name} "
            f"(default={flag.default}, rules={len(flag.rules)})"
        )
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)
    except DuplicateFlagError as e:
        flag_logger.error(f"Duplicate flag error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidFlagNameError as e:
        flag_logger.error(f"Invalid flag name: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidRuleDefinitionError as e:
        flag_logger.error(f"Invalid rule definition: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        flag_logger.error(f"Database error creating flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create flag")
    except Exception as e:
        flag_logger.error(f"Unexpected error creating flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/flags/{name}", response_model=FlagOut)
def get_flag(name: str):
    """Get a specific feature flag"""
    flag_logger.info(f"Fetching feature flag: {name}")
    try:
        flag = flag_service.get_flag(name)
        if not flag:
            flag_logger.warning(f"Feature flag not found: {name}")
            raise HTTPException(status_code=404, detail=f"Flag '{name}' not found")
        flag_logger.info(f"Successfully retrieved feature flag: {name}")
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)
    except DatabaseError as e:
        flag_logger.error(f"Database error retrieving flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve flag")
    except Exception as e:
        flag_logger.error(f"Unexpected error retrieving flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/flags/{name}", response_model=FlagOut)
def update_flag(
    name: str, payload: FlagCreate, admin: Dict[str, Any] = Depends(get_current_admin)
):
    """Update a feature flag (requires admin)"""
    flag_logger.info(f"Updating feature flag: {name} (admin: {admin.get('sub')})")
    try:
        flag = flag_service.update_flag(name, payload)
        evaluator.invalidate_flag(name)
        flag_logger.info(
            f"Successfully updated feature flag: {name} "
            f"(default={flag.default}, rules={len(flag.rules)})"
        )
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)
    except FlagNotFoundError as e:
        flag_logger.error(f"Flag not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidFlagNameError as e:
        flag_logger.error(f"Invalid flag name: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidRuleDefinitionError as e:
        flag_logger.error(f"Invalid rule definition: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        flag_logger.error(f"Database error updating flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update flag")
    except Exception as e:
        flag_logger.error(f"Unexpected error updating flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/flags/{name}")
def delete_flag(name: str, admin: Dict[str, Any] = Depends(get_current_admin)):
    """Delete a feature flag (requires admin)"""
    flag_logger.info(f"Deleting feature flag: {name} (admin: {admin.get('sub')})")
    try:
        flag_service.delete_flag(name)
        evaluator.invalidate_flag(name)
        flag_logger.info(f"Successfully deleted feature flag: {name}")
        return {"ok": True}
    except FlagNotFoundError as e:
        flag_logger.error(f"Flag not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseError as e:
        flag_logger.error(f"Database error deleting flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete flag")
    except Exception as e:
        flag_logger.error(f"Unexpected error deleting flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/evaluate", response_model=EvalResponse)
def evaluate(req: EvalRequest):
    """Evaluate a feature flag based on user context"""
    flag_logger.debug(f"Evaluating flag '{req.flag}' with context: {req.context}")
    try:
        result = evaluator.evaluate(req.flag, req.context)
        flag_logger.info(
            f"Flag '{req.flag}' evaluated to: {result['value']} (reason: {result.get('reason')})"
        )
        return EvalResponse(flag=req.flag, value=result["value"], reason=result.get("reason"))
    except InvalidContextError as e:
        flag_logger.error(f"Invalid context: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        flag_logger.error(f"Error evaluating flag: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to evaluate flag")
