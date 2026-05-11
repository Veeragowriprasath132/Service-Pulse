"""
app/ai/sla_predictor.py
ML-based SLA breach prediction using scikit-learn.

Features used:
  - Priority (encoded)
  - Category (encoded)
  - Team historical SLA rate
  - Hour of day (tickets created late may breach more)
  - Day of week
  - Subject length / keyword risk signals
"""
from __future__ import annotations

import os
import pickle
import logging
import numpy as np
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Historical team SLA rates (used as a feature) ─────────
TEAM_SLA_RATES: dict[str, float] = {
    "Network Ops":     0.97,
    "Security":        0.94,
    "Hardware":        0.91,
    "Software":        0.89,
    "Infra & Servers": 0.78,
    "BI & Analytics":  0.93,
    "DB & Middleware":  0.88,
}

PRIORITY_BREACH_RISK: dict[str, float] = {
    "Critical": 0.45,
    "High":     0.30,
    "Medium":   0.15,
    "Low":      0.05,
}

# Keywords that historically correlate with SLA breach
HIGH_RISK_KEYWORDS = [
    "production", "prod", "critical", "down", "outage", "blocked", "urgent",
    "all users", "everyone", "multiple", "escalate", "deadline", "payment",
    "revenue", "customer", "breach", "data loss"
]

SLA_HOURS: dict[str, dict[str, float]] = {
    "Critical": {"response": 1, "resolution": 4},
    "High":     {"response": 2, "resolution": 8},
    "Medium":   {"response": 4, "resolution": 24},
    "Low":      {"response": 8, "resolution": 72},
}


class SLAPredictor:
    """
    Predicts probability of SLA breach for incoming tickets.
    Uses a Gradient Boosting classifier on engineered features.
    Falls back to a heuristic model if not trained.
    """

    def __init__(self):
        self.model = None
        self.feature_names: list[str] = []

    def _extract_features(
        self,
        priority: str,
        category: str,
        team_name: Optional[str] = None,
        subject: str = "",
        created_hour: Optional[int] = None,
        created_dow: Optional[int] = None
    ) -> list[float]:
        now = datetime.now(timezone.utc)
        hour = created_hour if created_hour is not None else now.hour
        dow  = created_dow  if created_dow  is not None else now.weekday()

        # Priority risk
        priority_risk = PRIORITY_BREACH_RISK.get(priority, 0.15)

        # Team historical SLA (inverted — lower SLA = higher risk)
        team_sla = TEAM_SLA_RATES.get(team_name or "", 0.90)
        team_risk = 1.0 - team_sla

        # Keyword risk
        text_lower = subject.lower()
        kw_hits = sum(1 for kw in HIGH_RISK_KEYWORDS if kw in text_lower)
        kw_risk = min(kw_hits * 0.1, 0.5)

        # Time risk — tickets created outside business hours or late Friday
        after_hours = 1.0 if (hour < 8 or hour > 18) else 0.0
        friday_risk = 0.2 if dow == 4 else 0.0   # Friday escalation risk
        weekend     = 1.0 if dow >= 5 else 0.0

        # Category encoding (simple ordinal by historical risk)
        category_risk_map = {
            "Infrastructure": 0.4, "Database": 0.35, "Network": 0.25,
            "Security": 0.20, "Software": 0.18, "Hardware": 0.15,
            "BI & Analytics": 0.12
        }
        cat_risk = category_risk_map.get(category, 0.2)

        return [
            priority_risk, team_risk, kw_risk,
            after_hours, friday_risk, weekend,
            cat_risk, float(hour) / 24.0, float(dow) / 6.0
        ]

    def fit(self, X: list[list[float]], y: list[int]) -> None:
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline

        self.model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(
                n_estimators=100, learning_rate=0.1,
                max_depth=4, random_state=42
            ))
        ])
        self.model.fit(X, y)
        logger.info("SLA predictor trained on %d samples", len(X))

    def predict_proba(
        self,
        priority: str,
        category: str,
        team_name: Optional[str] = None,
        subject: str = ""
    ) -> float:
        features = self._extract_features(priority, category, team_name, subject)

        if self.model:
            try:
                proba = self.model.predict_proba([features])[0]
                return float(proba[1])   # probability of breach (class 1)
            except Exception as e:
                logger.warning("Model prediction failed: %s. Using heuristic.", e)

        # Heuristic fallback
        return self._heuristic_predict(features)

    @staticmethod
    def _heuristic_predict(features: list[float]) -> float:
        """Weighted sum heuristic when model unavailable."""
        weights = [0.35, 0.25, 0.15, 0.10, 0.05, 0.05, 0.10, 0.02, 0.01]
        score = sum(w * f for w, f in zip(weights, features))
        return min(max(score, 0.0), 1.0)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: str) -> "SLAPredictor":
        with open(path, "rb") as f:
            return pickle.load(f)


# ── Singleton ─────────────────────────────────────────────
_sla_predictor: Optional[SLAPredictor] = None


def get_sla_predictor() -> SLAPredictor:
    global _sla_predictor
    if _sla_predictor is not None:
        return _sla_predictor

    from app.config import get_settings
    settings = get_settings()

    if os.path.exists(settings.sla_model_path):
        try:
            _sla_predictor = SLAPredictor.load(settings.sla_model_path)
            logger.info("Loaded trained SLA predictor")
            return _sla_predictor
        except Exception as e:
            logger.warning("Could not load SLA predictor: %s", e)

    logger.info("Bootstrapping SLA predictor with synthetic data…")
    _sla_predictor = SLAPredictor()
    _bootstrap_sla_train(_sla_predictor)
    return _sla_predictor


def _bootstrap_sla_train(predictor: SLAPredictor) -> None:
    """Create synthetic training data and train the model."""
    import random
    random.seed(42)
    X, y = [], []

    for _ in range(500):
        priority = random.choice(["Critical","High","Medium","Low"])
        category = random.choice(list({
            "Infrastructure","Database","Network","Security","Software","Hardware","BI & Analytics"
        }))
        team  = random.choice(list(TEAM_SLA_RATES.keys()))
        subj  = random.choice(["production down", "slow query", "vpn issue", "printer broken"])
        feats = predictor._extract_features(priority, category, team, subj)
        # Label: high priority + low SLA team = more likely to breach
        breach_prob = (
            PRIORITY_BREACH_RISK.get(priority, 0.15) +
            (1 - TEAM_SLA_RATES.get(team, 0.9)) * 0.5
        )
        label = 1 if random.random() < breach_prob else 0
        X.append(feats)
        y.append(label)

    try:
        predictor.fit(X, y)
    except Exception as e:
        logger.warning("SLA bootstrap training failed: %s", e)


# ── Public API ────────────────────────────────────────────

def predict_sla_risk(
    priority: str,
    category: str,
    team_name: Optional[str] = None,
    subject: str = ""
) -> dict:
    predictor = get_sla_predictor()
    prob = predictor.predict_proba(priority, category, team_name, subject)

    if prob >= 0.7:
        risk_level = "critical"
        rec = f"Immediate attention required. Assign to a senior engineer and monitor closely. Consider escalating to {team_name or 'team'} lead."
    elif prob >= 0.45:
        risk_level = "high"
        rec = "High breach risk. Prioritise and assign within 30 minutes. Set checkpoint alerts."
    elif prob >= 0.20:
        risk_level = "medium"
        rec = "Moderate risk. Assign within the hour and ensure SLA timer is tracked."
    else:
        risk_level = "low"
        rec = "Low breach risk. Proceed with standard workflow."

    sla_hrs = SLA_HOURS.get(priority, SLA_HOURS["Medium"])
    predicted_hrs = sla_hrs["resolution"] * (0.7 + prob * 0.6)

    return {
        "breach_probability": round(prob, 3),
        "risk_level": risk_level,
        "predicted_resolution_hours": round(predicted_hrs, 1),
        "recommendation": rec
    }
