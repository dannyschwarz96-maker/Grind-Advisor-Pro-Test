import os
from pathlib import Path
from collections import defaultdict

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from ..config import settings
from ..models import User, Bean, Shot
from ..ml.hierarchical import HierarchicalModel
from ..ml.features import extract_features


class UserModelService:
    def __init__(self):
        self._cache = {}

    def _model_dir(self, user_id: str) -> str:
        p = Path(settings.model_dir) / user_id
        p.mkdir(parents=True, exist_ok=True)
        return str(p)

    def _load_model(self, user_id: str) -> HierarchicalModel:
        model = self._cache.get(user_id)
        if model is not None:
            return model
        model = HierarchicalModel.load(self._model_dir(user_id))
        self._cache[user_id] = model
        return model

    def invalidate(self, user_id: str):
        self._cache.pop(user_id, None)

    def rebuild_for_user(self, db: Session, user_id: str) -> HierarchicalModel:
        model = self._load_model(user_id)
        beans = {
            b.id: {
                "id": b.id,
                "roast_level": b.roast_level,
                "name": b.name,
            }
            for b in db.scalars(select(Bean).where(Bean.user_id == user_id)).all()
        }
        shots = db.scalars(
            select(Shot).options(selectinload(Shot.bean)).where(Shot.user_id == user_id)
        ).all()
        bezuege = []
        for s in shots:
            if not s.features_json:
                continue
            bezuege.append(
                {
                    "id": s.id,
                    "bean_id": s.bean_id,
                    "actual_time": s.actual_time,
                    "grind": s.grind,
                    "dose": s.dose,
                    "yield_g": s.yield_g,
                    "target_time": s.target_time,
                    "date": s.date.isoformat(),
                    "features": s.features_json,
                    "timeseries": s.timeseries_json or {},
                }
            )
        model.rebuild_from_bezuege(bezuege, beans)
        model.save()
        return model

    def ensure_features(self, shot_payload: dict) -> dict:
        ts = shot_payload.get("timeseries") or {}
        return extract_features(
            time_axis=ts.get("time_axis", []),
            pressure=ts.get("pressure", []),
            temperature=ts.get("temperature", []),
            flow=ts.get("flow", []),
            weight=ts.get("weight", []),
            grind=float(shot_payload["grind"]),
            actual_time=float(shot_payload["actual_time"]),
            target_time=shot_payload.get("target_time"),
            dose=shot_payload.get("dose"),
            yield_g=shot_payload.get("yield_g"),
        )

    def predict(self, db: Session, user_id: str, bean_id: str, target_time: float, dose: float = 18):
        model = self.rebuild_for_user(db, user_id)
        bean = db.get(Bean, bean_id)
        roast = bean.roast_level if bean else "Mittel"

        bean_shots = db.scalars(
            select(Shot).where(Shot.user_id == user_id, Shot.bean_id == bean_id).order_by(Shot.date.desc())
        ).all()

        roast_shots = db.scalars(
            select(Shot).join(Bean, Shot.bean_id == Bean.id).where(Shot.user_id == user_id, Bean.roast_level == roast)
        ).all()

        all_shots = db.scalars(select(Shot).where(Shot.user_id == user_id)).all()
        ref = bean_shots or roast_shots or all_shots

        def avg(shots, attr, default):
            vals = [float(getattr(s, attr)) for s in shots if getattr(s, attr) is not None]
            return sum(vals) / len(vals) if vals else default

        ref_grind = avg(ref, "grind", 15.0)
        ref_time = avg(ref, "actual_time", target_time)
        ref_dose = avg(ref, "dose", dose)

        feats = extract_features([], [], [], [], [],
            grind=ref_grind,
            actual_time=ref_time,
            target_time=target_time,
            dose=ref_dose,
            yield_g=None
        )
        return model.predict(bean_id, roast, target_time, feats)

user_model_service = UserModelService()
