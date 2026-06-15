from fastapi import APIRouter, HTTPException, Depends
from app.schemas.flag import FlagCreate, FlagOut, EvalRequest, EvalResponse
from app.db.session import get_session
from app.models.flag import FeatureFlag
from app.services.evaluator import Evaluator
from sqlmodel import select
from app.core.security import get_current_admin

router = APIRouter()
evaluator = Evaluator()


@router.post("/flags", response_model=FlagOut)
def create_flag(payload: FlagCreate, admin=Depends(get_current_admin)):
    with get_session() as session:
        existing = session.exec(select(FeatureFlag).where(FeatureFlag.name == payload.name)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Flag already exists")
        flag = FeatureFlag(name=payload.name, default=payload.default, rules=[r.dict() for r in payload.rules])
        session.add(flag)
        session.commit()
        session.refresh(flag)
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)


@router.get("/flags/{name}", response_model=FlagOut)
def get_flag(name: str):
    with get_session() as session:
        flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)


@router.put("/flags/{name}", response_model=FlagOut)
def update_flag(name: str, payload: FlagCreate, admin=Depends(get_current_admin)):
    with get_session() as session:
        flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        flag.default = payload.default
        flag.rules = [r.dict() for r in payload.rules]
        session.add(flag)
        session.commit()
        session.refresh(flag)
        evaluator.invalidate_flag(name)
        return FlagOut(name=flag.name, default=flag.default, rules=flag.rules)


@router.delete("/flags/{name}")
def delete_flag(name: str, admin=Depends(get_current_admin)):
    with get_session() as session:
        flag = session.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
        if not flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        session.delete(flag)
        session.commit()
        evaluator.invalidate_flag(name)
        return {"ok": True}


@router.post("/evaluate", response_model=EvalResponse)
def evaluate(req: EvalRequest):
    result = evaluator.evaluate(req.flag, req.context)
    return EvalResponse(flag=req.flag, value=result["value"], reason=result.get("reason"))
