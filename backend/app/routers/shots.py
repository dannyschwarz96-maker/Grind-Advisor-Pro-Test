from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..deps import get_current_user
from ..models import User, Bean, Shot
from ..schemas import ShotCreate
from ..services.ml_service import user_model_service

router = APIRouter(prefix="/shots", tags=["shots"])

@router.get("")
def list_shots(bean_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Shot).where(Shot.user_id == user.id)
    if bean_id:
        stmt = stmt.where(Shot.bean_id == bean_id)
    shots = db.scalars(stmt.order_by(Shot.date.desc())).all()
    return [
        {
            "id": s.id,
            "bean_id": s.bean_id,
            "grind": s.grind,
            "actual_time": s.actual_time,
            "target_time": s.target_time,
            "dose": s.dose,
            "yield_g": s.yield_g,
            "machine": s.machine,
            "notes": s.notes,
            "date": s.date.isoformat(),
            "features": s.features_json,
            "timeseries": s.timeseries_json or {},
        }
        for s in shots
    ]

@router.post("")
def create_shot(payload: ShotCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bean = db.scalar(select(Bean).where(Bean.id == payload.bean_id, Bean.user_id == user.id))
    if not bean:
        raise HTTPException(status_code=404, detail="Bean not found")

    body = payload.model_dump()
    body["date"] = body.get("date") or None
    features = user_model_service.ensure_features(body)
    shot_kwargs = dict(
        user_id=user.id,
        bean_id=payload.bean_id,
        grind=payload.grind,
        actual_time=payload.actual_time,
        target_time=payload.target_time,
        dose=payload.dose,
        yield_g=payload.yield_g,
        machine=payload.machine,
        notes=payload.notes,
        features_json=features,
        timeseries_json=(payload.timeseries.model_dump() if payload.timeseries else {}),
    )
    if payload.date is not None:
        shot_kwargs["date"] = payload.date

    shot = Shot(**shot_kwargs)
    db.add(shot)
    db.commit()
    db.refresh(shot)
    user_model_service.invalidate(user.id)
    return {"ok": True, "id": shot.id}

@router.delete("/{shot_id}")
def delete_shot(shot_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    shot = db.scalar(select(Shot).where(Shot.id == shot_id, Shot.user_id == user.id))
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    db.delete(shot)
    db.commit()
    user_model_service.invalidate(user.id)
    return {"ok": True}
