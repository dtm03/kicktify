"""Simple baselines for backtest comparison (no model)."""

from __future__ import annotations

import numpy as np

from .metrics import kicktipp_points


def pick_always_home() -> str:
    """Classic home-advantage baseline."""
    return "2:1"


def pick_table_ppg(feats: dict[str, float]) -> str:
    h = float(feats["home_season_ppg"])
    a = float(feats["away_season_ppg"])
    if abs(h - a) < 0.15:
        return "1:1"
    if h > a:
        return "2:1"
    return "1:2"


def pick_form_xg(feats: dict[str, float]) -> str:
    gh = int(np.clip(round(float(feats["home_form_xgf"])), 0, 5))
    ga = int(np.clip(round(float(feats["away_form_xgf"])), 0, 5))
    if gh == 0 and ga == 0:
        return "1:1"
    return f"{gh}:{ga}"


def pick_bookmaker_favorite(odds: tuple[float, float, float] | None) -> str | None:
    """Bet365-style 1X2 odds → Kicktipp score (favourite + typical margin)."""
    if odds is None:
        return None
    h, d, a = odds
    if min(h, d, a) <= 0 or not np.isfinite([h, d, a]).all():
        return None
    fav = min(("H", h), ("D", d), ("A", a), key=lambda x: x[1])[0]
    if fav == "D":
        return "1:1"
    if fav == "H":
        return "2:1"
    return "1:2"


STRATEGY_LABELS: dict[str, str] = {
    "model": "Unser Modell",
    "home": "Immer Heimsieg (2:1)",
    "table": "Bessere Tabellenform (PPG)",
    "form_xg": "Bessere Form-xG",
    "bookmaker": "Buchmacher-Favorit (Bet365)",
}


def baseline_picks(feats: dict[str, float], odds: tuple[float, float, float] | None) -> dict[str, str | None]:
    return {
        "home": pick_always_home(),
        "table": pick_table_ppg(feats),
        "form_xg": pick_form_xg(feats),
        "bookmaker": pick_bookmaker_favorite(odds),
    }


def points_for_pick(pick: str | None, actual: str) -> int:
    if not pick:
        return 0
    return kicktipp_points(pick, actual)