from fastapi import APIRouter, HTTPException, Depends
from typing import List
from app.schemas.flag import FlagCreate, FlagOut, EvalRequest, EvalResponse
from app.services.evaluator import Evaluator
from app.services.flag_service import FlagService
from app.core.security import get_current_admin
from app.core.logger import flag_logger

router = APIRouter()
evaluator = Evaluator()
flag_service = FlagService()


@router.get("/flags", response_model=List[FlagOut])
def list_flags():
    """List all feature flags"""
    flag_logger.info("Fetching all feature flags")
    flags = flag_service.list_flags()
    flag_logger.info(f"Successfully retrieved {len(flags)} feature flags")
    return [FlagOut(name=flag.name, default=flag.default, rules=flag.rules) for flag in flags]


@router.post("/flags", response_model=FlagOut)
def create_flag(payload: FlagCreate):
    """Create a new feature flag"""
    flag_logger.info(f"Creating new feature flag: {payload.name}")
    try:
        flag = flag_service.create_flag(payload)
        flag_logger.info(f"Successfully created feature flag: {payload.name} (default={flag.default}, rules={len(flag.rules)})")
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)
    except ValueError as e:
        flag_logger.error(f"Failed to create flag {payload.name}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flags/{name}", response_model=FlagOut)
def get_flag(name: str):
    """Get a specific feature flag"""
    flag_logger.info(f"Fetching feature flag: {name}")
    flag = flag_service.get_flag(name)
    if not flag:
        flag_logger.warning(f"Feature flag not found: {name}")
        raise HTTPException(status_code=404, detail="Flag not found")
    flag_logger.info(f"Successfully retrieved feature flag: {name}")
    return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)


@router.put("/flags/{name}", response_model=FlagOut)
def update_flag(name: str, payload: FlagCreate):
    """Update a feature flag"""
    flag_logger.info(f"Updating feature flag: {name}")
    try:
        flag = flag_service.update_flag(name, payload)
        evaluator.invalidate_flag(name)
        flag_logger.info(f"Successfully updated feature flag: {name} (default={flag.default}, rules={len(flag.rules)})")
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)
    except ValueError as e:
        flag_logger.error(f"Failed to update flag {name}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/flags/{name}")
def delete_flag(name: str, admin=Depends(get_current_admin)):
    """Delete a feature flag (requires admin)"""
    flag_logger.info(f"Deleting feature flag: {name} (admin: {admin.get('sub')})")
    try:
        flag_service.delete_flag(name)
        evaluator.invalidate_flag(name)
        flag_logger.info(f"Successfully deleted feature flag: {name}")
        return {"ok": True}
    except ValueError as e:
        flag_logger.error(f"Failed to delete flag {name}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/evaluate", response_model=EvalResponse)
def evaluate(req: EvalRequest):
    """Evaluate a feature flag based on user context"""
    flag_logger.info(f"Evaluating flag '{req.flag}' with context: {req.context}")
    result = evaluator.evaluate(req.flag, req.context)
    flag_logger.info(f"Flag '{req.flag}' evaluated to: {result['value']} (reason: {result.get('reason')})")
    return EvalResponse(flag=req.flag, value=result["value"], reason=result.get("reason"))
