"""Feature-Engineering aus Spielverlauf (ohne Data Leakage)."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

from .team_names import normalize_team

INITIAL_ELO = 1500.0
ELO_K = 20.0
HOME_ELO_ADV = 65.0
FORM_WINDOW = 5
ELO_SEASON_SHRINK = 0.50
GOAL_TO_XG = 0.92


def _points(goals_for: int, goals_against: int) -> float:
    if goals_for > goals_against:
        return 3.0
    if goals_for == goals_against:
        return 1.0
    return 0.0


def _expected_score(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


@dataclass
class TeamState:
    elo: float = INITIAL_ELO
    season_points: float = 0.0
    season_games: int = 0
    season_gf: float = 0.0
    season_ga: float = 0.0
    season_xgf: float = 0.0
    season_xga: float = 0.0
    career_points: float = 0.0
    career_games: int = 0
    recent: deque = field(default_factory=lambda: deque(maxlen=FORM_WINDOW))
    recent_xg: deque = field(default_factory=lambda: deque(maxlen=FORM_WINDOW))
    extra_kickoffs: list[datetime] = field(default_factory=list)


@dataclass
class FeatureBuilder:
    """Baut vor jedem Spiel Features nur aus Vergangenheit."""

    teams: dict[str, TeamState] = field(default_factory=lambda: defaultdict(TeamState))
    last_match_dt: dict[str, datetime | None] = field(default_factory=dict)

    def _team(self, name: str) -> TeamState:
        return self.teams[normalize_team(name)]

    def _form_stats(self, name: str) -> tuple[float, float, float]:
        st = self._team(name)
        if not st.recent:
            return 1.3, 1.3, 1.0
        items = list(st.recent)
        w_sum = pts = gf = ga = 0.0
        for idx, (g_for, g_against, _) in enumerate(reversed(items)):
            w = 2.0 if idx < 3 else 1.0
            w_sum += w
            pts += w * _points(g_for, g_against)
            gf += w * g_for
            ga += w * g_against
        return pts / w_sum, gf / w_sum, ga / w_sum

    def _xg_form(self, name: str) -> tuple[float, float]:
        st = self._team(name)
        if not st.recent_xg:
            _, gf, ga = self._form_stats(name)
            return gf * GOAL_TO_XG, ga * GOAL_TO_XG
        items = list(st.recent_xg)
        w_sum = xgf = xga = 0.0
        for idx, (xg_for, xg_against) in enumerate(reversed(items)):
            w = 2.0 if idx < 3 else 1.0
            w_sum += w
            xgf += w * xg_for
            xga += w * xg_against
        return xgf / w_sum, xga / w_sum

    def _load_stats(self, name: str, kickoff: datetime) -> tuple[int, int, int]:
        st = self._team(name)
        cutoff = kickoff - timedelta(days=14)
        extra_14d = sum(1 for dt in st.extra_kickoffs if cutoff <= dt < kickoff)
        european_14d = 0  # reserviert, falls Europa-Liga-Daten verfügbar
        midweek = sum(1 for dt in st.extra_kickoffs if cutoff <= dt < kickoff and dt.weekday() <= 3)
        return extra_14d, european_14d, midweek

    def snapshot(
        self,
        home: str,
        away: str,
        kickoff: datetime,
        weekday: int,
        *,
        home_injuries: int = 0,
        away_injuries: int = 0,
    ) -> dict[str, float]:
        home, away = normalize_team(home), normalize_team(away)
        h, a = self._team(home), self._team(away)
        h_form_pts, h_gf, h_ga = self._form_stats(home)
        a_form_pts, a_gf, a_ga = self._form_stats(away)
        h_xgf, h_xga = self._xg_form(home)
        a_xgf, a_xga = self._xg_form(away)

        h_ppg_season = h.season_points / h.season_games if h.season_games else 1.3
        a_ppg_season = a.season_points / a.season_games if a.season_games else 1.3
        h_season_xgf = h.season_xgf / h.season_games if h.season_games else 1.35
        a_season_xgf = a.season_xgf / a.season_games if a.season_games else 1.35

        h_rest = self._rest_days(home, kickoff)
        a_rest = self._rest_days(away, kickoff)
        h_extra, h_euro, h_mid = self._load_stats(home, kickoff)
        a_extra, a_euro, a_mid = self._load_stats(away, kickoff)

        elo_home_adj = h.elo + HOME_ELO_ADV
        return {
            "home_elo": h.elo,
            "away_elo": a.elo,
            "elo_diff": elo_home_adj - a.elo,
            "home_form_pts": h_form_pts,
            "away_form_pts": a_form_pts,
            "home_form_gf": h_gf,
            "home_form_ga": h_ga,
            "away_form_gf": a_gf,
            "away_form_ga": a_ga,
            "home_form_xgf": h_xgf,
            "home_form_xga": h_xga,
            "away_form_xgf": a_xgf,
            "away_form_xga": a_xga,
            "home_season_ppg": h_ppg_season,
            "away_season_ppg": a_ppg_season,
            "home_season_xgf": h_season_xgf,
            "away_season_xgf": a_season_xgf,
            "home_rest_days": h_rest,
            "away_rest_days": a_rest,
            "home_extra_14d": float(h_extra),
            "away_extra_14d": float(a_extra),
            "home_midweek_14d": float(h_mid),
            "away_midweek_14d": float(a_mid),
            "home_injuries": float(home_injuries),
            "away_injuries": float(away_injuries),
            "weekday": float(weekday),
            "is_friday": 1.0 if weekday == 4 else 0.0,
            "is_saturday": 1.0 if weekday == 5 else 0.0,
            "is_sunday": 1.0 if weekday == 6 else 0.0,
        }

    def _rest_days(self, team: str, kickoff: datetime) -> float:
        team = normalize_team(team)
        prev = self.last_match_dt.get(team)
        if prev is None:
            return 7.0
        delta = (kickoff - prev).total_seconds() / 86400.0
        return float(np.clip(delta, 2.0, 14.0))

    def observe(
        self,
        home: str,
        away: str,
        home_goals: int,
        away_goals: int,
        kickoff: datetime,
        *,
        new_season: bool = False,
        home_xg: float | None = None,
        away_xg: float | None = None,
    ) -> None:
        home, away = normalize_team(home), normalize_team(away)
        if new_season:
            for st in self.teams.values():
                st.elo = INITIAL_ELO + ELO_SEASON_SHRINK * (st.elo - INITIAL_ELO)
                st.season_points = 0.0
                st.season_games = 0
                st.season_gf = 0.0
                st.season_ga = 0.0
                st.season_xgf = 0.0
                st.season_xga = 0.0
                st.extra_kickoffs = []
                st.recent.clear()
                st.recent_xg.clear()

        hx = home_xg if home_xg is not None else home_goals * GOAL_TO_XG
        ax = away_xg if away_xg is not None else away_goals * GOAL_TO_XG

        h, a = self._team(home), self._team(away)
        hp = _points(home_goals, away_goals)
        ap = _points(away_goals, home_goals)

        for st, pts, gf, ga, xgf, xga in (
            (h, hp, home_goals, away_goals, hx, ax),
            (a, ap, away_goals, home_goals, ax, hx),
        ):
            st.season_points += pts
            st.season_games += 1
            st.season_gf += gf
            st.season_ga += ga
            st.season_xgf += xgf
            st.season_xga += xga
            st.career_points += pts
            st.career_games += 1
            st.recent.append((gf, ga, pts))
            st.recent_xg.append((xgf, xga))

        exp_home = _expected_score(h.elo + HOME_ELO_ADV, a.elo)
        exp_away = 1.0 - exp_home
        act_home = 1.0 if home_goals > away_goals else (0.5 if home_goals == away_goals else 0.0)
        act_away = 1.0 - act_home
        h.elo += ELO_K * (act_home - exp_home)
        a.elo += ELO_K * (act_away - exp_away)

        self.last_match_dt[home] = kickoff
        self.last_match_dt[away] = kickoff

    def observe_auxiliary(
        self,
        home: str,
        away: str,
        home_goals: int,
        away_goals: int,
        kickoff: datetime,
        *,
        is_european: bool = False,
    ) -> None:
        """Pokal/Europa: Belastung + leichte Form-Anpassung (Gewicht 0.45)."""
        home, away = normalize_team(home), normalize_team(away)
        weight = 0.65 if is_european else 0.45
        h, a = self._team(home), self._team(away)
        hx, ax = home_goals * GOAL_TO_XG * weight, away_goals * GOAL_TO_XG * weight

        h.recent.append((int(round(home_goals * weight)), int(round(away_goals * weight)), 0.0))
        a.recent.append((int(round(away_goals * weight)), int(round(home_goals * weight)), 0.0))
        h.recent_xg.append((hx, ax))
        a.recent_xg.append((ax, hx))
        h.extra_kickoffs.append(kickoff)
        a.extra_kickoffs.append(kickoff)

        prev_h, prev_a = self.last_match_dt.get(home), self.last_match_dt.get(away)
        if prev_h is None or kickoff > prev_h:
            self.last_match_dt[home] = kickoff
        if prev_a is None or kickoff > prev_a:
            self.last_match_dt[away] = kickoff


FEATURE_COLUMNS = [
    "home_elo",
    "away_elo",
    "elo_diff",
    "home_form_pts",
    "away_form_pts",
    "home_form_gf",
    "home_form_ga",
    "away_form_gf",
    "away_form_ga",
    "home_form_xgf",
    "home_form_xga",
    "away_form_xgf",
    "away_form_xga",
    "home_season_ppg",
    "away_season_ppg",
    "home_season_xgf",
    "away_season_xgf",
    "home_rest_days",
    "away_rest_days",
    "home_extra_14d",
    "away_extra_14d",
    "home_midweek_14d",
    "away_midweek_14d",
    "home_injuries",
    "away_injuries",
    "weekday",
    "is_friday",
    "is_saturday",
    "is_sunday",
]