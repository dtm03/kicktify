"""Extra competitive fixtures (DFB-Pokal, European cups) for workload features."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from .openliga import final_score, get_league_season_matches, parse_match_datetime
from .team_names import normalize_team

AUX_LEAGUES = ("dfb",)
EURO_LEAGUES = ("cl", "el", "ucl", "uecl")


def _rows_for_league(shortcut: str, season: int) -> list[dict]:
    raw = get_league_season_matches(shortcut, season)
    rows: list[dict] = []
    for m in raw:
        score = final_score(m)
        if score is None:
            continue
        dt = parse_match_datetime(m)
        if dt is None:
            continue
        rows.append(
            {
                "datetime": dt,
                "home_team": normalize_team(m["team1"]["teamName"]),
                "away_team": normalize_team(m["team2"]["teamName"]),
                "home_goals": score[0],
                "away_goals": score[1],
                "competition": shortcut,
                "is_european": shortcut in EURO_LEAGUES,
            }
        )
    return rows


def load_auxiliary_fixtures(seasons: tuple[int, ...]) -> pd.DataFrame:
    rows: list[dict] = []
    for season in seasons:
        for league in AUX_LEAGUES + EURO_LEAGUES:
            rows.extend(_rows_for_league(league, season))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("datetime").reset_index(drop=True)