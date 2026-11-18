"""xG estimate from shot data (football-data.co.uk, D1)."""

from __future__ import annotations

import io
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from .team_names import normalize_team

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "football_data"
BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/D1.csv"


def _season_tag(openliga_year: int) -> str:
    """OpenLigaDB-Startjahr 2024 -> football-data 2425."""
    y, y2 = openliga_year % 100, (openliga_year + 1) % 100
    return f"{y:02d}{y2:02d}"


def _shot_xg(shots: float, sot: float) -> float:
    shots = max(float(shots or 0), 0.0)
    sot = max(float(sot or 0), 0.0)
    off = max(shots - sot, 0.0)
    return 0.03 * off + 0.35 * sot


def load_season_xg(openliga_season: int) -> pd.DataFrame:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tag = _season_tag(openliga_season)
    cache = CACHE_DIR / f"D1_{tag}.csv"
    if cache.exists():
        df = pd.read_csv(cache, parse_dates=["date"])
        return df

    url = BASE_URL.format(season=tag)
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=60, headers={"User-Agent": "ml-for-kicktipp/1.0"})
            if resp.status_code == 404:
                return pd.DataFrame()
            resp.raise_for_status()
            raw = pd.read_csv(io.BytesIO(resp.content))
            break
        except Exception as e:
            last_err = e
            time.sleep(1.0)
    else:
        raise RuntimeError(f"Could not load football-data URL: {url}") from last_err

    if raw.empty:
        return pd.DataFrame()

    df = raw.copy()
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam"])
    for col in ("HS", "AS", "HST", "AST", "FTHG", "FTAG"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["home_xg"] = df.apply(lambda r: _shot_xg(r.get("HS"), r.get("HST")), axis=1)
    df["away_xg"] = df.apply(lambda r: _shot_xg(r.get("AS"), r.get("AST")), axis=1)
    df["home_team"] = df["HomeTeam"].map(normalize_team)
    df["away_team"] = df["AwayTeam"].map(normalize_team)
    df["openliga_season"] = openliga_season
    out = df[
        ["Date", "home_team", "away_team", "home_xg", "away_xg", "FTHG", "FTAG", "openliga_season"]
    ].rename(columns={"Date": "date", "FTHG": "home_goals", "FTAG": "away_goals"})
    out.to_csv(cache, index=False)
    return out


def load_all_xg(seasons: tuple[int, ...]) -> pd.DataFrame:
    frames = [load_season_xg(s) for s in seasons]
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values("date")


def lookup_xg(
    xg_df: pd.DataFrame,
    kickoff: datetime,
    home: str,
    away: str,
) -> tuple[float, float] | None:
    if xg_df.empty:
        return None
    home, away = normalize_team(home), normalize_team(away)
    day = pd.Timestamp(kickoff.date())
    window = xg_df[(xg_df["date"].dt.date >= (day - pd.Timedelta(days=1)).date()) & (xg_df["date"].dt.date <= (day + pd.Timedelta(days=1)).date())]
    sub = window[(window["home_team"] == home) & (window["away_team"] == away)]
    if sub.empty:
        sub = window[(window["home_team"] == away) & (window["away_team"] == home)]
        if not sub.empty:
            r = sub.iloc[0]
            return float(r["away_xg"]), float(r["home_xg"])
        return None
    r = sub.iloc[0]
    return float(r["home_xg"]), float(r["away_xg"])