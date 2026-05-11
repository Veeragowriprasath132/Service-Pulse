"""
app/ai/routing_agent.py
Intelligent Ticket Routing Agent using:
  - Rule-based keyword matching (fast, always available)
  - ML classification with scikit-learn (trained on ticket history)
  - Confidence scoring to pick the best strategy

The agent auto-assigns incoming tickets to the correct domain team.
"""
from __future__ import annotations

import os
import re
import pickle
import logging
import numpy as np
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Domain keyword rules ───────────────────────────────────
# These act as both a fallback and a training signal.
DOMAIN_RULES: dict[str, list[str]] = {
    "Network Ops": [
        "vpn", "network", "firewall", "switch", "router", "wifi", "wi-fi",
        "bandwidth", "dns", "dhcp", "ip address", "port", "connectivity",
        "ping", "traceroute", "vlan", "wan", "lan", "proxy", "packet loss"
    ],
    "Security": [
        "certificate", "ssl", "tls", "cert", "antivirus", "malware", "virus",
        "lockout", "password", "iam", "active directory", "compliance",
        "threat", "phishing", "breach", "vulnerability", "2fa", "mfa",
        "access control", "permission denied", "security alert"
    ],
    "Hardware": [
        "laptop", "desktop", "printer", "monitor", "keyboard", "mouse",
        "projector", "battery", "screen", "display", "hdmi", "usb",
        "hardware", "device", "peripheral", "cable", "dock", "webcam"
    ],
    "Software": [
        "software", "application", "office 365", "o365", "outlook", "teams",
        "license", "activation", "install", "uninstall", "windows", "os",
        "patch", "update", "browser", "chrome", "adobe", "crm", "erp"
    ],
    "Infra & Servers": [
        "server", "vmware", "esxi", "virtual machine", "vm", "active directory",
        "group policy", "gpo", "azure", "aws", "cloud", "backup", "restore",
        "onedrive", "sharepoint", "storage", "disk", "cpu", "memory", "ram"
    ],
    "BI & Analytics": [
        "power bi", "powerbi", "tableau", "dashboard", "report", "analytics",
        "ssrs", "data gateway", "gateway", "dataset", "refresh", "bi",
        "visualization", "chart", "kpi", "metrics", "excel", "pivot"
    ],
    "DB & Middleware": [
        "database", "sql", "mysql", "postgresql", "postgres", "oracle", "db",
        "query", "timeout", "replication", "api", "rest", "middleware",
        "connection pool", "stored procedure", "index", "table", "schema"
    ],
}

CATEGORY_TO_TEAM: dict[str, str] = {
    "Network":        "Network Ops",
    "Security":       "Security",
    "Hardware":       "Hardware",
    "Software":       "Software",
    "Infrastructure": "Infra & Servers",
    "BI & Analytics": "BI & Analytics",
    "Database":       "DB & Middleware",
}


# ── Simple ML model wrapper ───────────────────────────────

class RoutingModel:
    """
    Wraps a scikit-learn text classifier for ticket routing.
    Falls back to keyword rules when the model is not trained yet.
    """

    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.classes: list[str] = []

    def fit(self, texts: list[str], labels: list[str]) -> None:
        """Train on historical ticket text → team label pairs."""
        from sklearn.pipeline import Pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression

        self.model = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=10_000,
                sublinear_tf=True
            )),
            ("clf", LogisticRegression(max_iter=500, C=1.0))
        ])
        self.model.fit(texts, labels)
        self.classes = list(self.model.classes_)
        logger.info("Routing model trained on %d samples, classes: %s", len(texts), self.classes)

    def predict(self, text: str) -> tuple[str, float]:
        """Return (team_name, confidence) — confidence is 0-1."""
        if self.model is None:
            return self._keyword_route(text)
        proba = self.model.predict_proba([text])[0]
        idx   = int(np.argmax(proba))
        return self.classes[idx], float(proba[idx])

    def predict_all(self, text: str) -> list[tuple[str, float]]:
        """Return sorted list of (team, confidence) for all teams."""
        if self.model is None:
            return [(t, self._keyword_score(text, kws)) for t, kws in DOMAIN_RULES.items()]
        proba  = self.model.predict_proba([text])[0]
        return sorted(zip(self.classes, proba), key=lambda x: x[1], reverse=True)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info("Routing model saved to %s", path)

    @classmethod
    def load(cls, path: str) -> "RoutingModel":
        with open(path, "rb") as f:
            return pickle.load(f)

    # ── Keyword fallback ──────────────────────────────────
    def _keyword_route(self, text: str) -> tuple[str, float]:
        scores = {team: self._keyword_score(text, kws) for team, kws in DOMAIN_RULES.items()}
        best_team = max(scores, key=lambda t: scores[t])
        total = sum(scores.values()) or 1
        confidence = scores[best_team] / total
        return best_team, min(confidence, 0.95)

    @staticmethod
    def _keyword_score(text: str, keywords: list[str]) -> float:
        text_lower = text.lower()
        score = 0.0
        for kw in keywords:
            if kw in text_lower:
                # Longer keyword matches score higher
                score += len(kw.split()) * 1.5 if len(kw.split()) > 1 else 1.0
        return score


# ── Singleton ─────────────────────────────────────────────
_routing_model: Optional[RoutingModel] = None


def get_routing_model() -> RoutingModel:
    global _routing_model
    if _routing_model is not None:
        return _routing_model

    from app.config import get_settings
    settings = get_settings()

    if os.path.exists(settings.routing_model_path):
        try:
            _routing_model = RoutingModel.load(settings.routing_model_path)
            logger.info("Loaded trained routing model from %s", settings.routing_model_path)
            return _routing_model
        except Exception as e:
            logger.warning("Could not load routing model: %s. Using keyword fallback.", e)

    logger.info("No trained routing model found — using keyword-based routing.")
    _routing_model = RoutingModel()
    # Bootstrap training on synthetic data from the rules
    _routing_model = _bootstrap_train(_routing_model)
    return _routing_model


def _bootstrap_train(model: RoutingModel) -> RoutingModel:
    """Create synthetic training data from keyword rules and train the model."""
    texts, labels = [], []
    for team, keywords in DOMAIN_RULES.items():
        for kw in keywords:
            texts.append(f"Issue with {kw} — need help with {kw} not working")
            labels.append(team)
            texts.append(f"Please resolve {kw} problem urgently")
            labels.append(team)
    try:
        model.fit(texts, labels)
    except Exception as e:
        logger.warning("Bootstrap training failed: %s", e)
    return model


# ── Public API ────────────────────────────────────────────

def route_ticket(
    subject: str,
    description: str = "",
    category: Optional[str] = None,
    db_teams: Optional[list] = None
) -> dict:
    """
    Route a ticket and return full routing result:
    {
      team_name, confidence, reasoning, alternative_teams
    }
    """
    # Category override — if user explicitly chose a category, trust it
    if category and category in CATEGORY_TO_TEAM:
        mapped = CATEGORY_TO_TEAM[category]
        return {
            "team_name": mapped,
            "confidence": 0.99,
            "reasoning": f"Explicitly categorised as '{category}' → auto-routed to {mapped}.",
            "alternative_teams": []
        }

    # ML + keyword routing
    full_text = f"{subject} {description}".strip()
    model = get_routing_model()
    top_teams = model.predict_all(full_text)[:3]

    best_team, best_conf = top_teams[0]
    alternatives = [
        {"team": t, "confidence": round(c, 3)}
        for t, c in top_teams[1:]
        if c > 0.05
    ]

    # Build human-readable reasoning
    matched_kws = [
        kw for kw in DOMAIN_RULES.get(best_team, [])
        if kw in full_text.lower()
    ]
    kw_str = ", ".join(f'"{k}"' for k in matched_kws[:5]) if matched_kws else "contextual analysis"
    reasoning = (
        f"Routed to {best_team} with {best_conf:.0%} confidence based on: {kw_str}. "
        f"Model used: {'ML classifier' if model.model else 'keyword rules'}."
    )

    return {
        "team_name": best_team,
        "confidence": round(best_conf, 3),
        "reasoning": reasoning,
        "alternative_teams": alternatives
    }
