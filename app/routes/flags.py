from fastapi import APIRouter, HTTPException, Depends
from app.schemas.flag import FlagCreate, FlagOut, EvalRequest, EvalResponse
from app.services.evaluator import Evaluator
from app.services.flag_service import FlagService
from app.core.security import get_current_admin

router = APIRouter()
evaluator = Evaluator()
flag_service = FlagService()


@router.post("/flags", response_model=FlagOut)
def create_flag(payload: FlagCreate, admin=Depends(get_current_admin)):
    try:
        flag = flag_service.create_flag(payload)
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flags/{name}", response_model=FlagOut)
def get_flag(name: str):
    flag = flag_service.get_flag(name)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)


@router.put("/flags/{name}", response_model=FlagOut)
def update_flag(name: str, payload: FlagCreate, admin=Depends(get_current_admin)):
    try:
        flag = flag_service.update_flag(name, payload)
        evaluator.invalidate_flag(name)
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/flags/{name}")
def delete_flag(name: str, admin=Depends(get_current_admin)):
    try:
        flag_service.delete_flag(name)
        evaluator.invalidate_flag(name)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/evaluate", response_model=EvalResponse)
def evaluate(req: EvalRequest):
    result = evaluator.evaluate(req.flag, req.context)
    return EvalResponse(flag=req.flag, value=result["value"], reason=result.get("reason"))
