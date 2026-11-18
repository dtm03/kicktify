"""OpenLigaDB API – Bundesliga (bl1)."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

BASE = "https://api.openligadb.de"
LEAGUE = "bl1"
USER_AGENT = "ml-for-kicktipp/1.0"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": USER_AGENT})


def _get(path: str, *, use_cache: bool = True, cache_ttl_hours: float = 6.0) -> Any:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = path.strip("/").replace("/", "_")
    cache_file = CACHE_DIR / f"{safe}.json"
    if use_cache and cache_file.exists():
        age_h = (time.time() - cache_file.stat().st_mtime) / 3600.0
        if age_h < cache_ttl_hours:
            return json.loads(cache_file.read_text(encoding="utf-8"))

    url = f"{BASE}{path}"
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            resp = _SESSION.get(url, timeout=90)
            if resp.status_code == 404:
                raise FileNotFoundError(path)
            resp.raise_for_status()
            data = resp.json()
            if use_cache:
                cache_file.write_text(json.dumps(data), encoding="utf-8")
            return data
        except Exception as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"OpenLigaDB unreachable: {path}") from last_err


def get_current_matchday() -> dict[str, Any]:
    return _get(f"/getcurrentgroup/{LEAGUE}")


def get_matchday_matches(season: int | None = None, matchday: int | None = None) -> list[dict]:
    """Current matchday when season/matchday are None; else fixed season/matchday."""
    if season is None and matchday is None:
        return _get(f"/getmatchdata/{LEAGUE}")
    if matchday is None:
        return _get(f"/getmatchdata/{LEAGUE}/{season}")
    return _get(f"/getmatchdata/{LEAGUE}/{season}/{matchday}")


def get_season_matches(season: int) -> list[dict]:
    try:
        return _get(f"/getmatchdata/{LEAGUE}/{season}", use_cache=True, cache_ttl_hours=168.0)
    except FileNotFoundError:
        return []


def get_league_season_matches(league_shortcut: str, season: int) -> list[dict]:
    try:
        return _get(
            f"/getmatchdata/{league_shortcut}/{season}",
            use_cache=True,
            cache_ttl_hours=168.0,
        )
    except (FileNotFoundError, RuntimeError):
        return []


def final_score(match: dict) -> tuple[int, int] | None:
    if not match.get("matchIsFinished"):
        return None
    for r in match.get("matchResults") or []:
        if r.get("resultTypeID") == 2:
            return int(r["pointsTeam1"]), int(r["pointsTeam2"])
    return None


def parse_match_datetime(match: dict) -> datetime | None:
    raw = match.get("matchDateTime")
    if not raw:
        return None
    # API returns ISO local time without timezone
    return datetime.fromisoformat(raw)


def match_row(match: dict) -> dict | None:
    score = final_score(match)
    if score is None:
        return None
    home, away = score
    dt = parse_match_datetime(match)
    if dt is None:
        return None
    g = match.get("group") or {}
    return {
        "match_id": match["matchID"],
        "season": match.get("leagueSeason"),
        "matchday": g.get("groupOrderID"),
        "datetime": dt,
        "weekday": dt.weekday(),
        "home_team": match["team1"]["teamName"],
        "away_team": match["team2"]["teamName"],
        "home_goals": home,
        "away_goals": away,
    }


def upcoming_row(match: dict) -> dict:
    dt = parse_match_datetime(match)
    g = match.get("group") or {}
    return {
        "match_id": match["matchID"],
        "season": match.get("leagueSeason"),
        "matchday": g.get("groupOrderID"),
        "datetime": dt,
        "weekday": dt.weekday() if dt else None,
        "home_team": match["team1"]["teamName"],
        "away_team": match["team2"]["teamName"],
        "finished": bool(match.get("matchIsFinished")),
    }