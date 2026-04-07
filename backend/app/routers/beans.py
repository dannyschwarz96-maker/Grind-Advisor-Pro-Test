from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..deps import get_current_user
from ..models import User, Bean
from ..schemas import BeanCreate, BeanOut, BeanUpdate

router = APIRouter(prefix="/beans", tags=["beans"])

@router.get("", response_model=list[BeanOut])
def list_beans(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(Bean).where(Bean.user_id == user.id).order_by(Bean.created_at.desc())).all()

@router.post("", response_model=BeanOut)
def create_bean(payload: BeanCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bean = Bean(user_id=user.id, **payload.model_dump())
    db.add(bean)
    db.commit()
    db.refresh(bean)
    return bean

@router.put("/{bean_id}", response_model=BeanOut)
def update_bean(bean_id: str, payload: BeanUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bean = db.scalar(select(Bean).where(Bean.id == bean_id, Bean.user_id == user.id))
    if not bean:
        raise HTTPException(status_code=404, detail="Bean not found")
    for k, v in payload.model_dump().items():
        setattr(bean, k, v)
    db.commit()
    db.refresh(bean)
    return bean

@router.delete("/{bean_id}")
def delete_bean(bean_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    bean = db.scalar(select(Bean).where(Bean.id == bean_id, Bean.user_id == user.id))
    if not bean:
        raise HTTPException(status_code=404, detail="Bean not found")
    db.delete(bean)
    db.commit()
    return {"ok": True}
