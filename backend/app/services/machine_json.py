# backend/parsers/machine_json.py
import json
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ParsedShot:
    machine: str
    coffee: Optional[str]
    duration: float
    grind: Optional[float]
    dose: Optional[float]
    yield_g: Optional[float]
    time_axis: List[float] = field(default_factory=list)
    pressure: List[float] = field(default_factory=list)
    temperature: List[float] = field(default_factory=list)
    flow: List[float] = field(default_factory=list)
    weight: List[float] = field(default_factory=list)
    date: Optional[str] = None
    notes: Optional[str] = None
    errors: List[str] = field(default_factory=list)


def _safe_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _parse_timestamp(v) -> Optional[str]:
    if v is None:
        return None

    from datetime import datetime, timezone

    try:
        ts = float(v)
        if ts > 1e11:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except Exception:
        return str(v)


def parse_machine_json(raw: str) -> Optional[ParsedShot]:
    """
    Unterstützt nur ein Shot-JSON-Format:

    Root:
      - id
      - duration
      - timestamp
      - datapoints: []

    Datapoint:
      - timeInShot
      - pressure
      - pumpFlow
      - weightFlow
      - temperature
      - shotWeight
      - waterPumped (optional)
    """
    try:
        j = json.loads(raw)
    except json.JSONDecodeError as e:
        return ParsedShot(
            machine="Parse Error",
            coffee=None,
            duration=0.0,
            grind=None,
            dose=None,
            yield_g=None,
            errors=[str(e)],
        )

    if not isinstance(j, dict):
        return None

    pts = j.get("datapoints")
    if not isinstance(pts, list) or not pts:
        return ParsedShot(
            machine="Shot JSON",
            coffee=None,
            duration=0.0,
            grind=None,
            dose=None,
            yield_g=None,
            errors=["Ungültiges Format: 'datapoints' fehlt oder ist leer."],
        )

    first = pts[0] if pts else {}
    required = ["timeInShot", "pressure", "temperature", "shotWeight"]
    missing = [k for k in required if k not in first]

    if missing:
        return ParsedShot(
            machine="Shot JSON",
            coffee=None,
            duration=0.0,
            grind=None,
            dose=None,
            yield_g=None,
            errors=[f"Nicht unterstütztes Format. Fehlende Felder: {', '.join(missing)}"],
        )

    time_axis = []
    pressure = []
    temperature = []
    flow = []
    weight = []

    for p in pts:
        t = _safe_float(p.get("timeInShot"))
        pr = _safe_float(p.get("pressure"))
        temp = _safe_float(p.get("temperature"))
        pf = _safe_float(p.get("pumpFlow"))
        wf = _safe_float(p.get("weightFlow"))
        sw = _safe_float(p.get("shotWeight"))

        if t is None:
            continue

        time_axis.append(t / 1000.0)
        pressure.append(pr if pr is not None else 0.0)
        temperature.append(temp if temp is not None else 0.0)
        flow.append(pf if pf is not None else (wf if wf is not None else 0.0))
        weight.append(sw if sw is not None else 0.0)

    duration_raw = _safe_float(j.get("duration"))
    if time_axis:
        duration = float(time_axis[-1])
    elif duration_raw is not None:
        duration = duration_raw / 1000.0 if duration_raw > 300 else duration_raw
    else:
        duration = 0.0

    yield_g = weight[-1] if weight else None

    errors = []
    if not pressure:
        errors.append("Kein Druckprofil gefunden")
    if not temperature:
        errors.append("Kein Temperaturprofil gefunden")
    if not flow:
        errors.append("Kein Flow-Profil gefunden")
    if not weight:
        errors.append("Kein Gewichtsprofil gefunden")

    return ParsedShot(
        machine="Shot JSON",
        coffee=f"Shot {j.get('id')}" if j.get("id") is not None else None,
        duration=duration,
        grind=None,
        dose=None,
        yield_g=yield_g,
        time_axis=time_axis,
        pressure=pressure,
        temperature=temperature,
        flow=flow,
        weight=weight,
        date=_parse_timestamp(j.get("timestamp")),
        notes=None,
        errors=errors,
    )