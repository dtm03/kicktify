"""Training & Vorhersage (Poisson oder XGBoost + Dixon–Coles)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .dixon_coles import fit_rho
from .scoring import kicktipp_score
from .extra_fixtures import load_auxiliary_fixtures
from .features import FEATURE_COLUMNS, FeatureBuilder
from .team_names import normalize_team
from .football_data_xg import load_all_xg, lookup_xg
from .injuries import fetch_injury_counts, injury_penalty
from .openliga import (
    get_current_matchday,
    get_matchday_matches,
    get_season_matches,
    match_row,
    upcoming_row,
)

DEFAULT_SEASONS = tuple(range(2023, 2027))
MAX_GOALS_DISPLAY = 5
ModelBackend = Literal["poisson", "xgboost"]


@dataclass
class BundesligaPredictor:
    seasons: tuple[int, ...] = DEFAULT_SEASONS
    model_backend: ModelBackend = "xgboost"
    use_dixon_coles: bool = False
    home_model: Pipeline | None = None
    away_model: Pipeline | None = None
    history: pd.DataFrame | None = None
    builder: FeatureBuilder | None = None
    xg_history: pd.DataFrame | None = None
    aux_fixtures: pd.DataFrame | None = None
    dixon_coles_rho: float = 0.0
    injury_counts: dict[str, int] = field(default_factory=dict)

    def _make_pipeline(self) -> Pipeline:
        if self.model_backend == "xgboost":
            from xgboost import XGBRegressor

            reg = XGBRegressor(
                objective="count:poisson",
                n_estimators=450,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.85,
                colsample_bytree=0.85,
                reg_lambda=1.0,
                random_state=42,
                n_jobs=4,
            )
        else:
            reg = PoissonRegressor(alpha=0.05, max_iter=5000)
        return Pipeline([("scale", StandardScaler()), ("reg", reg)])

    def load_supplementary(self) -> None:
        self.xg_history = load_all_xg(self.seasons)
        self.aux_fixtures = load_auxiliary_fixtures(self.seasons)
        try:
            self.injury_counts = fetch_injury_counts()
        except Exception:
            self.injury_counts = {}

    def load_history(self) -> pd.DataFrame:
        rows: list[dict] = []
        for season in self.seasons:
            for m in get_season_matches(season):
                row = match_row(m)
                if row:
                    rows.append(row)
        if not rows:
            raise RuntimeError("Keine historischen Spiele von OpenLigaDB geladen.")
        df = pd.DataFrame(rows).sort_values("datetime").reset_index(drop=True)
        self.history = df
        return df

    def _replay_aux_until(self, builder: FeatureBuilder, until: pd.Timestamp) -> None:
        if self.aux_fixtures is None or self.aux_fixtures.empty:
            return
        if not hasattr(builder, "_aux_cursor"):
            builder._aux_cursor = 0  # noqa: SLF001
        i = builder._aux_cursor  # noqa: SLF001
        aux = self.aux_fixtures
        while i < len(aux) and aux.iloc[i]["datetime"] < until:
            r = aux.iloc[i]
            builder.observe_auxiliary(
                r["home_team"],
                r["away_team"],
                int(r["home_goals"]),
                int(r["away_goals"]),
                r["datetime"],
                is_european=bool(r.get("is_european")),
            )
            i += 1
        builder._aux_cursor = i  # noqa: SLF001

    def build_training_set(self, df: pd.DataFrame | None = None) -> pd.DataFrame:
        if self.xg_history is None:
            self.load_supplementary()
        df = df if df is not None else self.load_history()
        builder = FeatureBuilder()
        builder._aux_cursor = 0  # noqa: SLF001
        records: list[dict] = []
        current_season = None
        xg_df = self.xg_history if self.xg_history is not None else pd.DataFrame()

        for _, r in df.iterrows():
            season = r["season"]
            new_season = current_season is not None and season != current_season
            if new_season:
                builder._aux_cursor = 0  # noqa: SLF001
            current_season = season
            self._replay_aux_until(builder, r["datetime"])

            xg_pair = lookup_xg(xg_df, r["datetime"], r["home_team"], r["away_team"])
            home_inj = away_inj = 0
            feats = builder.snapshot(
                r["home_team"],
                r["away_team"],
                r["datetime"],
                int(r["weekday"]),
                home_injuries=home_inj,
                away_injuries=away_inj,
            )
            row = {
                **feats,
                "home_goals": r["home_goals"],
                "away_goals": r["away_goals"],
                "season": int(season),
            }
            records.append(row)

            home_xg = xg_pair[0] if xg_pair else None
            away_xg = xg_pair[1] if xg_pair else None
            builder.observe(
                r["home_team"],
                r["away_team"],
                int(r["home_goals"]),
                int(r["away_goals"]),
                r["datetime"],
                new_season=new_season,
                home_xg=home_xg,
                away_xg=away_xg,
            )

        self.builder = builder
        return pd.DataFrame(records)

    def fit(self, df: pd.DataFrame | None = None) -> "BundesligaPredictor":
        train = self.build_training_set(df)
        x = train[FEATURE_COLUMNS].astype(float)
        self.home_model = self._make_pipeline()
        self.away_model = self._make_pipeline()
        max_season = int(train["season"].max())
        weights = np.where(
            train["season"] == max_season,
            1.0,
            np.where(train["season"] == max_season - 1, 0.55, 0.22),
        )
        self.home_model.fit(x, train["home_goals"], reg__sample_weight=weights)
        self.away_model.fit(x, train["away_goals"], reg__sample_weight=weights)

        lam_h = self.home_model.predict(x)
        lam_a = self.away_model.predict(x)
        if self.use_dixon_coles:
            self.dixon_coles_rho = fit_rho(
                lam_h,
                lam_a,
                train["home_goals"].to_numpy(),
                train["away_goals"].to_numpy(),
            )
        return self

    def _clip_lambdas(self, lam_h: float, lam_a: float) -> tuple[float, float]:
        lam_h = float(np.clip(lam_h, 0.25, 3.5))
        lam_a = float(np.clip(lam_a, 0.15, 3.0))
        return lam_h, lam_a

    def _apply_injuries(self, home: str, away: str, lam_h: float, lam_a: float) -> tuple[float, float]:
        if not self.injury_counts:
            try:
                self.injury_counts = fetch_injury_counts()
            except Exception:
                return lam_h, lam_a
        hi = self.injury_counts.get(normalize_team(home), 0)
        ai = self.injury_counts.get(normalize_team(away), 0)
        return lam_h * injury_penalty(hi), lam_a * injury_penalty(ai)

    def _score_from_lambdas(self, lam_h: float, lam_a: float, feats: dict[str, float]) -> tuple[int, int]:
        gh, ga = kicktipp_score(
            lam_h,
            lam_a,
            elo_diff=float(feats["elo_diff"]),
            home_form_gf=float(feats["home_form_gf"]),
            away_form_gf=float(feats["away_form_gf"]),
            home_form_xgf=float(feats["home_form_xgf"]),
            away_form_xgf=float(feats["away_form_xgf"]),
            home_season_ppg=float(feats["home_season_ppg"]),
            away_season_ppg=float(feats["away_season_ppg"]),
            home_form_pts=float(feats["home_form_pts"]),
            away_form_pts=float(feats["away_form_pts"]),
        )
        return min(gh, MAX_GOALS_DISPLAY), min(ga, MAX_GOALS_DISPLAY)

    def _upcoming_matches(self) -> list[dict]:
        raw = get_matchday_matches()
        upcoming = [upcoming_row(m) for m in raw if not m.get("matchIsFinished")]
        if not upcoming:
            cur = get_current_matchday()
            md = int(cur["groupOrderID"]) + 1
            season = upcoming_row(raw[0])["season"] if raw else self.seasons[-1]
            try:
                nxt = get_matchday_matches(season, md)
                upcoming = [upcoming_row(m) for m in nxt if not m.get("matchIsFinished")]
            except Exception:
                upcoming = []
        return upcoming

    def predict_next_matchday(self) -> pd.DataFrame:
        if self.home_model is None or self.away_model is None or self.builder is None:
            raise RuntimeError("Modell nicht trainiert – zuerst .fit() aufrufen.")

        try:
            self.injury_counts = fetch_injury_counts()
        except Exception:
            pass

        matches = self._upcoming_matches()
        if not matches:
            raise RuntimeError("Keine anstehenden Spiele gefunden.")

        rows: list[dict] = []
        for m in matches:
            if m["datetime"] is None or m["weekday"] is None:
                continue
            home, away = m["home_team"], m["away_team"]
            hi = self.injury_counts.get(normalize_team(home), 0)
            ai = self.injury_counts.get(normalize_team(away), 0)
            feats = self.builder.snapshot(
                home,
                away,
                m["datetime"],
                int(m["weekday"]),
                home_injuries=hi,
                away_injuries=ai,
            )
            x = pd.DataFrame([feats])[FEATURE_COLUMNS].astype(float)
            lam_h = float(self.home_model.predict(x)[0])
            lam_a = float(self.away_model.predict(x)[0])
            lam_h, lam_a = self._clip_lambdas(lam_h, lam_a)
            lam_h, lam_a = self._apply_injuries(home, away, lam_h, lam_a)
            gh, ga = self._score_from_lambdas(lam_h, lam_a, feats)
            rows.append(
                {
                    "Spieltag": m["matchday"],
                    "Datum": m["datetime"].strftime("%a %d.%m.%Y %H:%M"),
                    "Heim": home,
                    "Gast": away,
                    "Tipp": f"{gh}:{ga}",
                    "Erwartung (xG)": f"{lam_h:.2f}:{lam_a:.2f}",
                    "Verletzte (H:A)": f"{hi}:{ai}",
                    "Modell": self.model_backend,
                }
            )
        out = pd.DataFrame(rows)
        return out.sort_values("Datum").reset_index(drop=True)

    def training_summary(self) -> dict[str, float]:
        if self.history is None or self.home_model is None:
            return {}
        df = self.history
        preds_h, preds_a = [], []
        b = FeatureBuilder()
        b._aux_cursor = 0  # noqa: SLF001
        current_season = None
        xg_df = self.xg_history if self.xg_history is not None else pd.DataFrame()

        for _, r in df.iterrows():
            season = r["season"]
            new_season = current_season is not None and season != current_season
            if new_season:
                b._aux_cursor = 0  # noqa: SLF001
            current_season = season
            self._replay_aux_until(b, r["datetime"])
            feats = b.snapshot(r["home_team"], r["away_team"], r["datetime"], int(r["weekday"]))
            x = pd.DataFrame([feats])[FEATURE_COLUMNS].astype(float)
            preds_h.append(float(self.home_model.predict(x)[0]))
            preds_a.append(float(self.away_model.predict(x)[0]))
            xg_pair = lookup_xg(xg_df, r["datetime"], r["home_team"], r["away_team"])
            b.observe(
                r["home_team"],
                r["away_team"],
                int(r["home_goals"]),
                int(r["away_goals"]),
                r["datetime"],
                new_season=new_season,
                home_xg=xg_pair[0] if xg_pair else None,
                away_xg=xg_pair[1] if xg_pair else None,
            )
        mae_h = float(np.mean(np.abs(np.array(preds_h) - df["home_goals"].values)))
        mae_a = float(np.mean(np.abs(np.array(preds_a) - df["away_goals"].values)))
        return {
            "mae_home_goals": mae_h,
            "mae_away_goals": mae_a,
            "n_matches": float(len(df)),
            "dixon_coles_rho": float(self.dixon_coles_rho),
        }