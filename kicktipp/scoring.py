"""Kicktipp-Tore aus Erwartungswerten (weniger 1:1-Flut, stärkere Favoriten)."""

from __future__ import annotations

import numpy as np


def blend_goal_expectation(
    model_lam: float,
    form_goals_pg: float,
    form_xg_pg: float,
    *,
    elo_diff_signed: float,
) -> float:
    """Modell + aktuelle Torgefahr (Form schwerer als alte Saisons)."""
    lam = 0.45 * model_lam + 0.25 * form_goals_pg + 0.15 * form_xg_pg
    lam += 0.15 * form_goals_pg  # Form-Tore stärker
    if elo_diff_signed > 0:
        lam *= 1.0 + min(0.12, elo_diff_signed / 2400.0)
    elif elo_diff_signed < 0:
        lam *= 1.0 - min(0.10, abs(elo_diff_signed) / 2600.0)
    return float(lam)


def kicktipp_score(
    lam_h: float,
    lam_a: float,
    *,
    elo_diff: float,
    home_form_gf: float,
    away_form_gf: float,
    home_form_xgf: float,
    away_form_xgf: float,
    home_season_ppg: float,
    away_season_ppg: float,
    home_form_pts: float,
    away_form_pts: float,
) -> tuple[int, int]:
    lam_h = blend_goal_expectation(lam_h, home_form_gf, home_form_xgf, elo_diff_signed=elo_diff)
    lam_a = blend_goal_expectation(lam_a, away_form_gf, away_form_xgf, elo_diff_signed=-elo_diff)

    gh = int(np.clip(round(lam_h), 0, 5))
    ga = int(np.clip(round(lam_a), 0, 5))

    # Klare Favoriten laut Modell nicht durch Heimvorteil „überstimmen“
    if lam_a > lam_h + 0.18 and gh > ga:
        gh, ga = ga, gh
    elif lam_h > lam_a + 0.18 and ga > gh:
        gh, ga = ga, gh

    if gh == ga:
        table_edge = (home_season_ppg - away_season_ppg) * 130.0
        form_pts_edge = (home_form_pts - away_form_pts) * 90.0
        form_goals_edge = (home_form_gf - away_form_gf) * 70.0
        edge = 0.20 * elo_diff + 0.45 * table_edge + 0.25 * form_pts_edge + 0.10 * form_goals_edge
        tight_match = (
            lam_h < 1.45
            and lam_a < 1.45
            and abs(home_season_ppg - away_season_ppg) < 0.35
            and abs(edge) < 35
        )
        if tight_match:
            return gh, ga
        if edge > 40:
            gh = min(gh + 1, 5)
        elif edge < -40:
            ga = min(ga + 1, 5)
        elif edge > 12:
            gh = min(gh + 1, 5)
        elif edge < -12:
            ga = min(ga + 1, 5)

    return gh, ga