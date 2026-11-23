#!/usr/bin/env python
"""Predict next matchday and write web/public/data/live_prediction.json."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kicktipp.backtest import save_live_prediction  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip prediction window guard (for GitHub Actions)",
    )
    parser.add_argument("--backend", choices=("xgboost", "poisson"), default="xgboost")
    args = parser.parse_args()
    payload = save_live_prediction(backend=args.backend, force=args.force)
    md = payload.get("matchday")
    print(f"Saved live prediction for matchday {md} ({len(payload['matches'])} matches)")


if __name__ == "__main__":
    main()