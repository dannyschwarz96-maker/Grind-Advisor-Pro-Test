# backend/ml/features.py
"""
Feature engineering from espresso shot time-series.
Converts raw pressure/flow/temp arrays into ML-ready feature vectors.
"""
import numpy as np
from typing import List, Optional, Dict, Any


def _safe(arr: list) -> np.ndarray:
    a = np.array(arr, dtype=float)
    return a[np.isfinite(a)]


def extract_features(
    time_axis:   List[float],
    pressure:    List[float],
    temperature: List[float],
    flow:        List[float],
    weight:      List[float],
    grind:       float,
    actual_time: float,
    target_time: Optional[float],
    dose:        Optional[float],
    yield_g:     Optional[float],
) -> Dict[str, Any]:
    """
    Returns a flat dict of features for ML.
    All features degrade gracefully if time-series is empty.
    """
    feats: Dict[str, Any] = {}

    # ── Core features (always available) ─────────────────────────────────────
    feats["grind"]       = float(grind)
    feats["actual_time"] = float(actual_time)
    feats["target_time"] = float(target_time) if target_time else float(actual_time)
    feats["time_delta"]  = feats["actual_time"] - feats["target_time"]
    feats["dose"]        = float(dose) if dose else 18.0

    if yield_g and dose and dose > 0:
        feats["ratio"]    = float(yield_g) / float(dose)
        feats["yield_g"]  = float(yield_g)
    else:
        feats["ratio"]   = 2.0      # sensible default
        feats["yield_g"] = feats["dose"] * 2.0

    # ── Time-series features ──────────────────────────────────────────────────
    t  = _safe(time_axis)
    p  = _safe(pressure)
    te = _safe(temperature)
    fl = _safe(flow)
    w  = _safe(weight)

    has_ts = len(t) > 5 and len(p) > 5

    if has_ts:
        duration = t[-1] - t[0] if len(t) > 1 else actual_time

        # Pressure features
        feats["pressure_max"]    = float(np.max(p))
        feats["pressure_mean"]   = float(np.mean(p))
        feats["pressure_rise"]   = _pressure_rise_slope(t, p)
        feats["pressure_std"]    = float(np.std(p))

        # Time to first drop: first moment pressure > 3 bar
        feats["time_to_first_drop"] = _time_to_first_drop(t, p, threshold=3.0)

        # Flow features
        if len(fl) > 5:
            mid = len(fl) // 2
            feats["flow_early_mean"] = float(np.mean(fl[:mid]))
            feats["flow_late_mean"]  = float(np.mean(fl[mid:]))
            feats["flow_ratio"]      = (feats["flow_late_mean"] + 1e-6) / (feats["flow_early_mean"] + 1e-6)
            feats["flow_max"]        = float(np.max(fl))
            feats["flow_std"]        = float(np.std(fl))
        else:
            feats.update(_flow_defaults())

        # Temperature features
        if len(te) > 5:
            feats["temp_mean"]    = float(np.mean(te))
            feats["temp_std"]     = float(np.std(te))
            feats["temp_drop"]    = float(te[0]) - float(te[-1]) if len(te) >= 2 else 0.0
        else:
            feats.update(_temp_defaults())

        # Weight / TDS proxy
        if len(w) > 5:
            feats["weight_final"] = float(w[-1])
            feats["flow_rate_avg"] = float(w[-1]) / duration if duration > 0 else 2.0
        else:
            feats["weight_final"]  = feats["yield_g"]
            feats["flow_rate_avg"] = feats["yield_g"] / actual_time if actual_time > 0 else 2.0

    else:
        # No time-series: fill with neutral defaults
        feats.update(_timeseries_defaults(actual_time))

    # ── Data quality flag ─────────────────────────────────────────────────────
    feats["has_timeseries"] = int(has_ts)
    feats["data_quality"]   = _data_quality_score(feats)

    return feats


def _pressure_rise_slope(t: np.ndarray, p: np.ndarray) -> float:
    """Slope of pressure during pre-infusion (first 20% of shot)."""
    n = max(1, len(t) // 5)
    if n < 2:
        return 0.0
    dt = t[n] - t[0]
    dp = p[n] - p[0]
    return float(dp / dt) if dt > 0 else 0.0


def _time_to_first_drop(t: np.ndarray, p: np.ndarray, threshold: float = 3.0) -> float:
    """Time until pressure exceeds threshold (pre-infusion end)."""
    idx = np.where(p > threshold)[0]
    if len(idx) == 0:
        return float(t[-1]) / 3.0   # fallback: 1/3 of total time
    return float(t[idx[0]])


def _flow_defaults() -> dict:
    return {"flow_early_mean": 1.5, "flow_late_mean": 1.5,
            "flow_ratio": 1.0, "flow_max": 3.0, "flow_std": 0.5}

def _temp_defaults() -> dict:
    return {"temp_mean": 93.0, "temp_std": 0.5, "temp_drop": 1.0}

def _timeseries_defaults(actual_time: float) -> dict:
    return {
        "pressure_max": 9.0, "pressure_mean": 8.5, "pressure_rise": 1.0,
        "pressure_std": 0.8, "time_to_first_drop": actual_time * 0.2,
        "flow_rate_avg": 2.0, "weight_final": 36.0,
        **_flow_defaults(), **_temp_defaults(),
    }

def _data_quality_score(feats: dict) -> float:
    """0–1 score for how much real data we have."""
    score = 0.5  # base for having grind + time
    if feats.get("has_timeseries"):
        score += 0.3
    if feats.get("dose") and feats["dose"] != 18.0:
        score += 0.1
    if feats.get("yield_g") and feats["yield_g"] != feats.get("dose", 18) * 2:
        score += 0.1
    return min(1.0, score)


# Feature names used for ML (must be consistent across train/predict)
FEATURE_NAMES = [
    "grind", "target_time", "dose", "ratio",
    "pressure_max", "pressure_mean", "pressure_rise", "pressure_std",
    "time_to_first_drop",
    "flow_early_mean", "flow_late_mean", "flow_ratio", "flow_max", "flow_std",
    "temp_mean", "temp_std", "temp_drop",
    "flow_rate_avg",
]

def features_to_vector(feats: dict) -> np.ndarray:
    return np.array([feats.get(k, 0.0) for k in FEATURE_NAMES], dtype=float)
