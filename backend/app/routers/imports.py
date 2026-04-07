from fastapi import APIRouter, Depends, HTTPException
from ..schemas import ImportParseRequest, ImportParseResponse
from ..deps import get_current_user
from ..models import User
from ..ml.features import extract_features
from ..services.machine_json import parse_machine_json

router = APIRouter(prefix="/import", tags=["import"])

@router.post("/parse", response_model=ImportParseResponse)
def import_parse(payload: ImportParseRequest, user: User = Depends(get_current_user)):
    shot = parse_machine_json(payload.raw_json)
    if shot is None:
        raise HTTPException(status_code=400, detail="Unbekanntes oder ungültiges Format")

    if shot.errors and not shot.time_axis and not shot.pressure:
        raise HTTPException(status_code=400, detail="; ".join(shot.errors))

    feats = extract_features(
        shot.time_axis,
        shot.pressure,
        shot.temperature,
        shot.flow,
        shot.weight,
        grind=shot.grind or 15.0,
        actual_time=shot.duration,
        target_time=None,
        dose=shot.dose,
        yield_g=shot.yield_g,
    )

    return ImportParseResponse(
        machine=shot.machine,
        coffee=shot.coffee,
        duration=shot.duration,
        grind=shot.grind,
        dose=shot.dose,
        yield_g=shot.yield_g,
        date=shot.date,
        notes=shot.notes,
        timeseries={
            "time_axis": shot.time_axis[:500],
            "pressure": shot.pressure[:500],
            "temperature": shot.temperature[:500],
            "flow": shot.flow[:500],
            "weight": shot.weight[:500],
        },
        features=feats,
        errors=shot.errors,
    )
