"""
ml/model.py – Per-user grind advisor ML model

Key design decisions:
  1. Each user has their own model → grind scales are never mixed
  2. Grind size is Min-Max normalized per user → mill-agnostic
  3. Brew ratio (output/dose) is used instead of raw weight → standardized
  4. Model inversion via grid search → predict optimal grind for target time
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler


ROAST_ENCODING = {"light": 0.0, "medium": 0.5, "dark": 1.0}
MIN_SHOTS_FOR_TRAINING = 3


class UserGrindModel:
    """
    Trained per user. Predicts extraction_time from:
      - grind_size      (normalized to [0,1] relative to user's historical range)
      - brew_ratio      (brew_weight / dose – mill-agnostic, standardized)
      - roast_encoded   (light=0, medium=0.5, dark=1)
      - interaction     (grind_norm × brew_ratio)
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.model = LinearRegression()
        self.grind_scaler = MinMaxScaler()
        self.is_trained = False
        self.n_samples = 0
        self.grind_min: float | None = None
        self.grind_max: float | None = None
        self.r2: float | None = None

    # ── Feature Engineering ───────────────────────────────────────────────────

    def _build_features(
        self,
        grind_sizes: np.ndarray,
        brew_weights: np.ndarray,
        doses: np.ndarray,
        roasts: np.ndarray,
        fit_scaler: bool = False,
    ) -> np.ndarray:
        """Build feature matrix from raw shot data."""
        grinds = grind_sizes.reshape(-1, 1)

        if fit_scaler:
            grinds_norm = self.grind_scaler.fit_transform(grinds).flatten()
            self.grind_min = float(grind_sizes.min())
            self.grind_max = float(grind_sizes.max())
        else:
            grinds_norm = self.grind_scaler.transform(grinds).flatten()

        # Brew ratio: more meaningful than raw weight
        brew_ratio = brew_weights / np.where(doses > 0, doses, 18.0)
        brew_ratio_norm = np.clip((brew_ratio - 1.5) / 1.5, -1, 1)  # center around 2:1

        roasts_enc = np.array([ROAST_ENCODING.get(r, 0.5) for r in roasts])

        return np.column_stack([
            grinds_norm,
            brew_ratio_norm,
            roasts_enc,
            grinds_norm * brew_ratio_norm,  # interaction term
        ])

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, shots: list[dict]) -> dict:
        """
        Train the model on a user's shot history.
        shots: list of dicts with keys:
          grind_size, extraction_time, brew_weight, dose, roast (optional)

        Returns training metadata dict.
        """
        if len(shots) < MIN_SHOTS_FOR_TRAINING:
            return {
                "trained": False,
                "reason": f"minimum_{MIN_SHOTS_FOR_TRAINING}_shots_required",
                "n_shots": len(shots),
                "shots_needed": MIN_SHOTS_FOR_TRAINING - len(shots),
            }

        grind_sizes      = np.array([s["grind_size"] for s in shots], dtype=float)
        extraction_times = np.array([s["extraction_time"] for s in shots], dtype=float)
        brew_weights     = np.array([s.get("brew_weight") or 36.0 for s in shots], dtype=float)
        doses            = np.array([s.get("dose") or 18.0 for s in shots], dtype=float)
        roasts           = np.array([s.get("roast") or "medium" for s in shots])

        # Check for sufficient grind variance (can't train if all same grind)
        if grind_sizes.max() == grind_sizes.min():
            return {
                "trained": False,
                "reason": "insufficient_grind_variance",
                "n_shots": len(shots),
                "message": "Use at least 2 different grind sizes",
            }

        X = self._build_features(grind_sizes, brew_weights, doses, roasts, fit_scaler=True)
        self.model.fit(X, extraction_times)
        self.r2 = float(self.model.score(X, extraction_times))
        self.is_trained = True
        self.n_samples = len(shots)

        return {
            "trained": True,
            "n_samples": self.n_samples,
            "r2_score": round(self.r2, 3),
            "grind_range": [self.grind_min, self.grind_max],
            "confidence": self._confidence_label(self.r2, self.n_samples),
        }

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict_optimal_grind(
        self,
        target_time: float,
        brew_weight: float = 36.0,
        dose: float = 18.0,
        roast: str = "medium",
    ) -> dict:
        """
        Invert the model: find grind_size that produces target_time.
        Uses grid search over normalized grind space, then denormalizes.
        """
        if not self.is_trained:
            return {
                "error": "model_not_trained",
                "message": f"Need at least {MIN_SHOTS_FOR_TRAINING} shots with different grind sizes",
            }

        # Grid over [0, 1] in normalized grind space (1000 points)
        grind_norms = np.linspace(0, 1, 1000)
        brew_ratio = brew_weight / max(dose, 1)
        brew_ratio_norm = np.clip((brew_ratio - 1.5) / 1.5, -1, 1)
        roast_enc = ROAST_ENCODING.get(roast, 0.5)

        X_pred = np.column_stack([
            grind_norms,
            np.full(1000, brew_ratio_norm),
            np.full(1000, roast_enc),
            grind_norms * brew_ratio_norm,
        ])

        predicted_times = self.model.predict(X_pred)

        # Closest point to target time
        idx = int(np.argmin(np.abs(predicted_times - target_time)))
        optimal_norm = grind_norms[idx]
        predicted_at_optimal = float(predicted_times[idx])

        # Denormalize back to user's grind scale
        optimal_grind = float(
            self.grind_scaler.inverse_transform([[optimal_norm]])[0][0]
        )

        # Confidence: residual + sample count
        residual = abs(predicted_at_optimal - target_time)
        confidence = self._confidence_label(
            self.r2, self.n_samples, extra_penalty=residual > 3
        )

        # Direction hint: should user go coarser or finer?
        direction = self._direction_hint(target_time, predicted_times, grind_norms)

        return {
            "optimal_grind": round(optimal_grind, 1),
            "predicted_time": round(predicted_at_optimal, 1),
            "target_time": target_time,
            "confidence": confidence,
            "direction_hint": direction,
            "r2_score": round(self.r2, 3),
            "n_samples": self.n_samples,
            "grind_range": [self.grind_min, self.grind_max],
            "note": (
                f"Based on {self.n_samples} shots, "
                f"your grind scale: {self.grind_min}–{self.grind_max}"
            ),
        }

    def predict_time_for_grind(self, grind_size: float, brew_weight: float = 36.0,
                                dose: float = 18.0, roast: str = "medium") -> float | None:
        """Predict extraction time for a given grind (for chart overlay)."""
        if not self.is_trained:
            return None
        grind_norm = float(self.grind_scaler.transform([[grind_size]])[0][0])
        brew_ratio = brew_weight / max(dose, 1)
        brew_ratio_norm = np.clip((brew_ratio - 1.5) / 1.5, -1, 1)
        roast_enc = ROAST_ENCODING.get(roast, 0.5)
        X = np.array([[grind_norm, brew_ratio_norm, roast_enc, grind_norm * brew_ratio_norm]])
        return float(self.model.predict(X)[0])

    def get_regression_line(self, brew_weight: float = 36.0, dose: float = 18.0,
                             roast: str = "medium", n_points: int = 50) -> list[dict]:
        """Generate regression line data points for the frontend chart."""
        if not self.is_trained:
            return []
        grinds = np.linspace(self.grind_min, self.grind_max, n_points)
        times = [self.predict_time_for_grind(g, brew_weight, dose, roast) for g in grinds]
        return [{"grind": round(g, 2), "time": round(t, 2)} for g, t in zip(grinds, times)]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _confidence_label(self, r2: float, n: int, extra_penalty: bool = False) -> str:
        if extra_penalty or n < 5 or r2 < 0.5:
            return "low"
        if n < 10 or r2 < 0.75:
            return "medium"
        return "high"

    def _direction_hint(self, target_time: float, predicted_times: np.ndarray,
                        grind_norms: np.ndarray) -> str | None:
        """
        If model predicts target is outside the user's grind range,
        tell them which direction to go.
        """
        min_pred = predicted_times.min()
        max_pred = predicted_times.max()
        if target_time < min_pred:
            # Need shorter extraction → finer grind
            return "finer"
        if target_time > max_pred:
            # Need longer extraction → coarser grind
            return "coarser"
        return None
