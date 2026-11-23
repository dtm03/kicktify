"""When the next matchday may be predicted (once per matchday, before kickoff)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .openliga import get_current_matchday, get_matchday_matches, parse_match_datetime, upcoming_row

LIVE_PREDICTION_PATH = (
    Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "live_prediction.json"
)


def _load_saved_prediction() -> dict | None:
    if not LIVE_PREDICTION_PATH.exists():
        return None
    try:
        return json.loads(LIVE_PREDICTION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def upcoming_matchday_bundle() -> dict:
    """Next matchday with unfinished fixtures (current or next API group)."""
    raw = get_matchday_matches()
    upcoming_rows = [upcoming_row(m) for m in raw if not m.get("matchIsFinished")]
    if not upcoming_rows:
        cur = get_current_matchday()
        md = int(cur["groupOrderID"]) + 1
        season = raw[0].get("leagueSeason") if raw else 2025
        nxt = get_matchday_matches(season, md)
        upcoming_rows = [upcoming_row(m) for m in nxt if not m.get("matchIsFinished")]

    upcoming_rows = [r for r in upcoming_rows if r.get("datetime") is not None]
    if not upcoming_rows:
        raise RuntimeError("No upcoming fixtures found.")

    matchday = int(upcoming_rows[0]["matchday"])
    season = int(upcoming_rows[0]["season"])
    kickoffs = sorted(r["datetime"] for r in upcoming_rows)
    first_ko = kickoffs[0]
    last_ko = kickoffs[-1]
    return {
        "season": season,
        "matchday": matchday,
        "first_kickoff": first_ko.isoformat(),
        "last_kickoff": last_ko.isoformat(),
        "first_kickoff_display": first_ko.strftime("%a %d.%m.%Y %H:%M"),
        "fixture_count": len(upcoming_rows),
    }


def prediction_gate(*, strict_monday: bool = False, ignore_saved: bool = False) -> dict:
    """
    Rules:
    - Only the immediate next matchday (from OpenLigaDB).
    - Not after the first kickoff of that matchday.
    - At most one saved prediction per matchday (live_prediction.json).
    - optional strict_monday: button only on Mondays (before kickoff).
    """
    bundle = upcoming_matchday_bundle()
    now = datetime.now()
    first_ko = datetime.fromisoformat(bundle["first_kickoff"])
    saved = _load_saved_prediction()

    reasons: list[str] = []
    allowed = True

    if now >= first_ko:
        allowed = False
        reasons.append("Der Spieltag hat bereits begonnen.")

    if not ignore_saved and saved and saved.get("matchday") == bundle["matchday"]:
        allowed = False
        reasons.append(
            f"Spieltag {bundle['matchday']} wurde bereits vorhergesagt "
            f"(Stand: {saved.get('predicted_at', '?')})."
        )

    if strict_monday and now.weekday() != 0:
        allowed = False
        reasons.append("Vorhersage ist nur montags möglich (nächster Freitags-Spieltag).")

    # Typical BL rhythm: predict from Mon until first kickoff (Fri–Sun)
    if allowed and now.weekday() > 3 and now.date() < first_ko.date():
        pass  # Thu ok; Fri before KO still ok until first_ko check

    message = "Vorhersage möglich." if allowed else " ".join(reasons)
    return {
        "allowed": allowed,
        "message": message,
        "upcoming": bundle,
        "saved_prediction_matchday": saved.get("matchday") if saved else None,
    }