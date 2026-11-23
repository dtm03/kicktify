"""Walk-forward backtest per matchday (pick vs actual)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .metrics import exact_hit, kicktipp_points, margin_hit, rate_summary, tendency_hit
from .openliga import get_matchday_matches, get_current_matchday, get_season_matches, load_consecutive_finished_rows, match_row
from .predictor import BundesligaPredictor, ModelBackend

LIVE_PREDICTION_PATH = (
    Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "live_prediction.json"
)


def _detect_season() -> int:
    try:
        raw = get_matchday_matches()
        if raw:
            return int(raw[0].get("leagueSeason", 2025))
    except Exception:
        pass
    return 2025


def predict_fixture_row(
    predictor: BundesligaPredictor,
    home: str,
    away: str,
    kickoff: datetime,
    weekday: int,
) -> dict:
    feats = predictor.builder.snapshot(home, away, kickoff, weekday, home_injuries=0, away_injuries=0)
    from .features import FEATURE_COLUMNS

    x = pd.DataFrame([feats])[FEATURE_COLUMNS].astype(float).fillna(0.0)
    lam_h = float(predictor.home_model.predict(x)[0])
    lam_a = float(predictor.away_model.predict(x)[0])
    lam_h, lam_a = predictor._clip_lambdas(lam_h, lam_a)
    gh, ga = predictor._score_from_lambdas(lam_h, lam_a, feats)
    return {
        "pick": f"{gh}:{ga}",
        "expected_xg": f"{lam_h:.2f}:{lam_a:.2f}",
        "kickoff_iso": kickoff.isoformat(),
        "kickoff_display": kickoff.strftime("%a %d.%m.%Y %H:%M"),
    }


def _match_flags(pick: str, actual: str) -> dict:
    return {
        "exact": exact_hit(pick, actual),
        "tendency": tendency_hit(pick, actual),
        "margin": margin_hit(pick, actual),
        "kicktipp_points": kicktipp_points(pick, actual),
    }


def backtest_current_season(
    *,
    season: int | None = None,
    train_seasons: tuple[int, ...] | None = None,
    backend: ModelBackend = "poisson",
    min_train_rows: int = 120,
) -> dict:
    season = season or _detect_season()
    if train_seasons is None:
        train_seasons = tuple(range(season - 2, season + 1))

    all_rows: list[dict] = []
    for y in train_seasons:
        if y == season:
            all_rows.extend(load_consecutive_finished_rows(y))
        else:
            for m in get_season_matches(y):
                row = match_row(m)
                if row:
                    all_rows.append(row)
    if not all_rows:
        raise RuntimeError("No match data for backtest.")

    full = pd.DataFrame(all_rows).sort_values("datetime").reset_index(drop=True)
    season_df = full[full["season"] == season].copy()
    if season_df.empty:
        raise RuntimeError(f"No finished matches for season {season}.")

    matchdays = sorted(int(x) for x in season_df["matchday"].dropna().unique())
    matchday_blocks: list[dict] = []
    all_flags: list[dict] = []

    predictor = BundesligaPredictor(seasons=train_seasons, model_backend=backend, use_dixon_coles=False)
    predictor.load_supplementary()

    for md in matchdays:
        md_matches = season_df[season_df["matchday"] == md].sort_values("datetime")
        if md_matches.empty:
            continue
        cutoff = md_matches["datetime"].min()
        train_df = full[full["datetime"] < cutoff]
        if len(train_df) < min_train_rows:
            continue

        finished = md_matches.dropna(subset=["home_goals", "away_goals"])
        if len(finished) == 0:
            continue

        predictor.fit(train_df)
        fixtures: list[dict] = []
        md_flags: list[dict] = []
        for _, r in finished.iterrows():
            pred = predict_fixture_row(
                predictor,
                r["home_team"],
                r["away_team"],
                r["datetime"],
                int(r["weekday"]),
            )
            actual = f"{int(r['home_goals'])}:{int(r['away_goals'])}"
            flags = _match_flags(pred["pick"], actual)
            md_flags.append(flags)
            all_flags.append(flags)
            fixtures.append(
                {
                    "home": r["home_team"],
                    "away": r["away_team"],
                    "pick": pred["pick"],
                    "actual": actual,
                    "kickoff": pred["kickoff_display"],
                    "expected_xg": pred["expected_xg"],
                    **flags,
                }
            )

        matchday_blocks.append(
            {
                "matchday": int(md),
                "stats": rate_summary(md_flags),
                "matches": fixtures,
            }
        )

    matchday_blocks.sort(key=lambda b: b["matchday"], reverse=True)

    return {
        "season": season,
        "season_stats": rate_summary(all_flags),
        "matchdays": matchday_blocks,
    }


def predict_next_matchday_payload(backend: ModelBackend = "xgboost") -> dict:
    season = _detect_season()
    seasons = tuple(range(season - 2, season + 1))
    p = BundesligaPredictor(seasons=seasons, model_backend=backend, use_dixon_coles=False)
    p.fit()
    df = p.predict_next_matchday()
    return {
        "season": season,
        "matchday": int(df["Matchday"].iloc[0]) if not df.empty else None,
        "predicted_at": datetime.now(timezone.utc).isoformat(),
        "matches": [
            {
                "home": row["Home"],
                "away": row["Away"],
                "pick": row["Pick"],
                "kickoff": row["Date"],
                "expected_xg": row["Expected (xG)"],
                "injuries": row["Injuries (H:A)"],
            }
            for _, row in df.iterrows()
        ],
    }


def save_live_prediction(
    payload: dict | None = None,
    *,
    backend: ModelBackend = "xgboost",
    force: bool = False,
) -> dict:
    from .matchday_window import prediction_gate

    if not force:
        gate = prediction_gate()
        if not gate["allowed"]:
            raise RuntimeError(gate["message"])
    payload = payload or predict_next_matchday_payload(backend=backend)
    LIVE_PREDICTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIVE_PREDICTION_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload