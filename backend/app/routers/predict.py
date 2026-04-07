from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..deps import get_current_user
from ..models import User, Shot
from ..schemas import PredictRequest, PredictResponse
from ..services.ml_service import user_model_service

router = APIRouter(prefix="/predict", tags=["predict"])

@router.post("", response_model=PredictResponse)
def predict(payload: PredictRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = user_model_service.predict(
        db=db,
        user_id=user.id,
        bean_id=payload.bean_id,
        target_time=float(payload.target_time),
        dose=float(payload.dose or 18),
    )
    return PredictResponse(**result)

@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    shots = db.scalars(select(Shot).where(Shot.user_id == user.id)).all()
    with_target = [s for s in shots if s.target_time is not None]
    avg_dev = (
        sum(abs(s.actual_time - s.target_time) for s in with_target) / len(with_target)
        if with_target else None
    )
    return {
        "n_beans": len({s.bean_id for s in shots}),
        "n_shots": len(shots),
        "avg_dev": round(avg_dev, 2) if avg_dev is not None else None,
    }
