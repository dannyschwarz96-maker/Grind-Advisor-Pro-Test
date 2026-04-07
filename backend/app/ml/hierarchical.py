# backend/ml/hierarchical.py
"""
Hierarchical Espresso ML Model
================================
Level 1 – Global:    alle Bezüge aller Bohnen
Level 2 – Roast:     gruppiert nach Hell / Mittel / Dunkel
Level 3 – Bean:      spezifisch pro Bohne

Modellwahl:
- wenig Daten        → Gaussian Process
- mehr Daten         → Gradient Boosting
- Vorhersageziel     → actual_time

Wichtig:
Das bestehende ML bleibt erhalten.
Verbessert wurde nur die Invertierung "welcher Mahlgrad ergibt target_time?",
damit keine instabilen Extrapolationen mehr entstehen.
"""

import numpy as np
import joblib
import os
from typing import Dict, List, Tuple
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
from sklearn.preprocessing import StandardScaler

from .features import features_to_vector


# ── Thresholds ────────────────────────────────────────────────────────────────
N_GP_MAX = 20
N_MIX_MIN = 5
N_BEAN_MAX = 40


def _blend_weight(n: int) -> float:
    """sigmoid: w ≈ 0 when n≈N_MIX_MIN, w ≈ 1 when n≈N_BEAN_MAX"""
    mid = (N_MIX_MIN + N_BEAN_MAX) / 2
    scale = (N_BEAN_MAX - N_MIX_MIN) / 6
    return float(1 / (1 + np.exp(-(n - mid) / max(scale, 1))))


def _make_gp() -> GaussianProcessRegressor:
    kernel = ConstantKernel(1.0) * RBF(length_scale=1.0) + WhiteKernel(noise_level=0.5)
    return GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=3,
        normalize_y=True
    )


def _make_gbm(n_samples: int) -> GradientBoostingRegressor:
    n_est = min(200, max(20, n_samples * 5))
    return GradientBoostingRegressor(
        n_estimators=n_est,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.8,
        min_samples_leaf=2,
        random_state=42,
    )


class SingleModel:
    """Wraps either GP or GBM with a scaler. Target = actual_time."""

    GRIND_RANGE = (1.0, 50.0)

    def __init__(self):
        self.scaler = StandardScaler()
        self.estimator = None
        self.trained = False
        self.n_samples = 0
        self.use_gp = True
        self._X: List[np.ndarray] = []
        self._y: List[float] = []

    def add(self, feats: dict, actual_time: float):
        self._X.append(features_to_vector(feats))
        self._y.append(float(actual_time))

    def fit(self):
        if len(self._X) < 2:
            return

        X = np.array(self._X, dtype=float)
        y = np.array(self._y, dtype=float)

        self.n_samples = len(y)
        self.use_gp = self.n_samples <= N_GP_MAX

        Xs = self.scaler.fit_transform(X)
        self.estimator = _make_gp() if self.use_gp else _make_gbm(self.n_samples)
        self.estimator.fit(Xs, y)
        self.trained = True

    def _training_residual_sigma(self) -> float:
        if not self.trained or len(self._X) < 2:
            return 5.0
        X = np.array(self._X, dtype=float)
        y = np.array(self._y, dtype=float)
        Xs = self.scaler.transform(X)
        pred = self.estimator.predict(Xs)
        sigma = float(np.std(y - pred))
        return max(1.0, sigma)

    def predict_time(self, feats: dict) -> Tuple[float, float]:
        """Returns (predicted_actual_time, std_dev)."""
        if not self.trained:
            return float(feats.get("target_time", 27.0)), 5.0

        Xs = self.scaler.transform([features_to_vector(feats)])

        if self.use_gp:
            mu, sigma = self.estimator.predict(Xs, return_std=True)
            return float(mu[0]), float(max(sigma[0], 1.0))

        mu = self.estimator.predict(Xs)
        sigma = self._training_residual_sigma()
        return float(mu[0]), float(sigma)

    def _local_time_to_grind_slope(self, feats: dict, center_g: float) -> float:
        """
        Schätzt lokal dGrind/dTime rund um center_g.
        Das ist stabiler als eine globale Korrelation über alle Trainingsdaten.
        """
        offsets = [-2.0, -1.0, -0.5, 0.5, 1.0, 2.0]
        pts = []

        for off in offsets:
            g = float(np.clip(center_g + off, *self.GRIND_RANGE))
            t, _ = self.predict_time(dict(feats, grind=g))
            pts.append((g, t))

        grinds = np.array([p[0] for p in pts], dtype=float)
        times = np.array([p[1] for p in pts], dtype=float)

        if len(pts) < 2 or np.std(times) < 1e-6:
            return 0.5

        cov = float(np.cov(times, grinds, bias=True)[0, 1])
        var_t = float(np.var(times))
        if var_t < 1e-6:
            return 0.5

        slope = cov / var_t  # dGrind/dTime
        if not np.isfinite(slope):
            return 0.5

        return float(max(0.05, abs(slope)))

    def predict_grind(
        self,
        target_time: float,
        feats: dict,
        grind_lo: float = 1.0,
        grind_hi: float = 50.0
    ) -> Tuple[float, float, float]:
        """
        Robuste Invertierung:
        1. scannt die gesamte Modellkurve grind -> predicted_time
        2. sucht zuerst echte Nullstellen-Brackets
        3. nutzt sonst den besten Punkt mit minimalem Fehler
        4. berechnet Unsicherheit lokal statt aus globaler Korrelation

        Returns:
            (grind, lo_bound, hi_bound)
        """
        if not self.trained or len(self._X) < 2:
            g = float(np.clip(feats.get("grind", 15.0), grind_lo, grind_hi))
            return round(g, 1), None, None

        def f(g: float):
            t, s = self.predict_time(dict(feats, grind=float(g)))
            return float(t - target_time), float(s), float(t)

        # ── gesamte Kurve abtasten ────────────────────────────────────────────
        grid = np.linspace(grind_lo, grind_hi, 161)
        vals = []

        for g in grid:
            diff, sigma, t = f(g)
            vals.append((float(g), float(diff), float(sigma), float(t)))

        # Bester Punkt über den gesamten Bereich
        best_g, best_diff, best_sigma, best_t = min(vals, key=lambda x: abs(x[1]))

        # ── Suche nach echter Vorzeichenänderung (Bracket) ────────────────────
        bracket = None
        for i in range(len(vals) - 1):
            g1, d1, _, _ = vals[i]
            g2, d2, _, _ = vals[i + 1]

            if abs(d1) < 1e-6:
                bracket = (g1, g1)
                break

            if d1 * d2 <= 0:
                bracket = (g1, g2)
                break

        # ── Wenn bracket vorhanden: Bisection ────────────────────────────────
        if bracket is not None:
            lo, hi = bracket

            for _ in range(40):
                mid = 0.5 * (lo + hi)
                d_lo, _, _ = f(lo)
                d_mid, _, _ = f(mid)

                if abs(d_mid) < 1e-3 or abs(hi - lo) < 0.02:
                    lo = hi = mid
                    break

                if d_lo * d_mid <= 0:
                    hi = mid
                else:
                    lo = mid

            g = float(np.clip(0.5 * (lo + hi), grind_lo, grind_hi))
            _, sigma, _ = f(g)

        else:
            # ── Kein bracket: nicht extrapolieren, sondern besten Kurvenpunkt nehmen
            g = float(np.clip(best_g, grind_lo, grind_hi))
            sigma = float(best_sigma)

        # ── Lokale Unsicherheit in Grind-Raum übersetzen ─────────────────────
        slope_tg = self._local_time_to_grind_slope(feats, g)  # dGrind/dTime
        sigma_g = float(max(0.3, slope_tg * max(sigma, 1.0)))

        lo_g = float(np.clip(g - 1.96 * sigma_g, grind_lo, grind_hi))
        hi_g = float(np.clip(g + 1.96 * sigma_g, grind_lo, grind_hi))

        return round(g, 1), round(lo_g, 1), round(hi_g, 1)


class HierarchicalModel:
    """
    The main model container.
    Stores and trains models at 3 levels.
    """

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.global_model: SingleModel = SingleModel()
        self.roast_models: Dict[str, SingleModel] = {
            "Hell": SingleModel(),
            "Mittel": SingleModel(),
            "Dunkel": SingleModel(),
        }
        self.bean_models: Dict[str, SingleModel] = {}
        os.makedirs(model_dir, exist_ok=True)

    # ── Data ingestion ────────────────────────────────────────────────────────
    def add_bezug(self, bean_id: str, roast_level: str, feats: dict, actual_time: float):
        self.global_model.add(feats, actual_time)
        self.roast_models.setdefault(roast_level, SingleModel()).add(feats, actual_time)
        self.bean_models.setdefault(bean_id, SingleModel()).add(feats, actual_time)

    def rebuild_from_bezuege(self, bezuege: list, beans: dict):
        """Re-initialize all models from scratch (full retrain)."""
        self.global_model = SingleModel()
        self.roast_models = {
            "Hell": SingleModel(),
            "Mittel": SingleModel(),
            "Dunkel": SingleModel(),
        }
        self.bean_models = {}

        for b in bezuege:
            bean = beans.get(b.get("bean_id"))
            if not bean or not b.get("features"):
                continue

            self.add_bezug(
                b["bean_id"],
                bean.get("roast_level", "Mittel"),
                b["features"],
                b["actual_time"]
            )

        self._fit_all()

    def _fit_all(self):
        self.global_model.fit()
        for m in self.roast_models.values():
            m.fit()
        for m in self.bean_models.values():
            m.fit()

    def fit_incremental(self):
        """Call after adding a new bezug."""
        self._fit_all()

    # ── Prediction ────────────────────────────────────────────────────────────
    def predict(self, bean_id: str, roast_level: str, target_time: float, feats: dict) -> dict:
        bean_m = self.bean_models.get(bean_id)
        roast_m = self.roast_models.get(roast_level, self.roast_models["Mittel"])
        glob_m = self.global_model

        n_bean = bean_m.n_samples if (bean_m and bean_m.trained) else 0
        n_roast = roast_m.n_samples if (roast_m and roast_m.trained) else 0
        n_glob = glob_m.n_samples if glob_m.trained else 0

        if n_bean >= N_BEAN_MAX:
            g, lo, hi = bean_m.predict_grind(target_time, feats)
            level = "bean"
            n = n_bean

        elif n_bean >= N_MIX_MIN and n_roast >= 2:
            w = _blend_weight(n_bean)

            g_bean, lo_b, hi_b = bean_m.predict_grind(target_time, feats)
            g_roast, lo_r, hi_r = roast_m.predict_grind(target_time, feats)

            g = round(w * g_bean + (1 - w) * g_roast, 1)
            lo = round(w * (lo_b if lo_b is not None else g_bean) + (1 - w) * (lo_r if lo_r is not None else g_roast), 1)
            hi = round(w * (hi_b if hi_b is not None else g_bean) + (1 - w) * (hi_r if hi_r is not None else g_roast), 1)

            level = f"bean+roast (w={w:.2f})"
            n = n_bean

        elif n_roast >= 2:
            g, lo, hi = roast_m.predict_grind(target_time, feats)
            level = "roast"
            n = n_roast

        elif n_glob >= 2:
            g, lo, hi = glob_m.predict_grind(target_time, feats)
            level = "global"
            n = n_glob

        else:
            return {
                "grind": feats.get("grind", 15.0),
                "grind_lo": None,
                "grind_hi": None,
                "confidence": 5.0,
                "model_level": "none",
                "n_samples": 0,
                "explanation": "Zu wenig Daten. Bitte mindestens 2 Bezüge protokollieren."
            }

        conf = self._confidence(n, lo, hi, g)

        return {
            "grind": round(g, 1),
            "grind_lo": lo,
            "grind_hi": hi,
            "confidence": conf,
            "model_level": level,
            "n_samples": n,
            "explanation": self._explanation(level, n, conf, lo, hi),
        }

    def _confidence(self, n: int, lo, hi, g: float) -> float:
        size_c = min(1.0, (n - 1) / 30) * 50

        if lo is not None and hi is not None:
            width = hi - lo
            interval_c = max(0, 50 - width * 8)
        else:
            interval_c = 10

        return round(min(95, size_c + interval_c), 1)

    def _explanation(self, level: str, n: int, conf: float, lo, hi) -> str:
        lvl_map = {
            "bean": "Bohnen-spezifisches Modell",
            "roast": "Röstgrad-Modell",
            "global": "Globales Modell",
        }
        base = next((v for k, v in lvl_map.items() if k in level), level)
        band = f" · 95%-Band: ±{round((hi - lo) / 2, 1)}" if lo is not None and hi is not None else ""
        return f"{base} · {n} Bezüge · {conf}% Konfidenz{band}"

    # ── Persistence ───────────────────────────────────────────────────────────
    def save(self):
        joblib.dump(self, os.path.join(self.model_dir, "hierarchical_model.pkl"))

    @staticmethod
    def load(model_dir: str) -> "HierarchicalModel":
        path = os.path.join(model_dir, "hierarchical_model.pkl")
        if os.path.exists(path):
            try:
                return joblib.load(path)
            except Exception as e:
                print(f"[ML] Failed to load model: {e} – starting fresh")
        return HierarchicalModel(model_dir)
