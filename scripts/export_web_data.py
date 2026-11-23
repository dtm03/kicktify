#!/usr/bin/env python
"""Export season backtest JSON for the Vercel frontend."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kicktipp.backtest import backtest_current_season  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=ROOT / "web" / "public" / "data" / "season_backtest.json",
    )
    parser.add_argument("--backend", choices=("poisson", "xgboost"), default="poisson")
    parser.add_argument("--season", type=int, default=None)
    args = parser.parse_args()

    data = backtest_current_season(season=args.season, backend=args.backend)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out} ({len(data['matchdays'])} matchdays)")


if __name__ == "__main__":
    main()