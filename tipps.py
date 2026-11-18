#!/usr/bin/env python
"""CLI: predict scores for the next Bundesliga matchday."""

from __future__ import annotations

import argparse
from pathlib import Path

from tabulate import tabulate

from kicktipp import BundesligaPredictor


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundesliga Kicktipp score predictions")
    parser.add_argument(
        "--seasons",
        type=int,
        nargs=2,
        metavar=("FROM", "TO"),
        default=(2023, 2027),
        help="Training seasons (OpenLigaDB start year, exclusive end). Default: 2023 2027",
    )
    parser.add_argument(
        "--backend",
        choices=("xgboost", "poisson"),
        default="xgboost",
        help="Model backend (default: xgboost)",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=Path("next_matchday_tips.html"),
        help="HTML output path to open in a browser",
    )
    args = parser.parse_args()

    seasons = tuple(range(args.seasons[0], args.seasons[1]))
    print(f"Training on seasons {seasons[0]}–{seasons[-1]} (first run may take a few minutes).")
    p = BundesligaPredictor(seasons=seasons, model_backend=args.backend, use_dixon_coles=False)
    p.fit()
    tips = p.predict_next_matchday()

    print("\n=== Next matchday picks ===\n")
    print(tabulate(tips, headers="keys", tablefmt="simple", showindex=False))
    print("\n--- Copy into Kicktipp ---")
    for _, row in tips.iterrows():
        print(f"{row['Home']} – {row['Away']}: {row['Pick']}")

    html = tips.to_html(index=False, border=0)
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Bundesliga tips</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ccc;padding:8px;text-align:left}}
th{{background:#1a5f2a;color:#fff}}</style></head><body>
<h1>Bundesliga — next matchday tips</h1>
{html}
</body></html>"""
    args.html.write_text(page, encoding="utf-8")
    print(f"\nSaved table: {args.html.resolve()}")


if __name__ == "__main__":
    main()