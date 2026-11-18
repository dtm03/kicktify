#!/usr/bin/env python
"""Tipps für den nächsten Bundesliga-Spieltag – einmal ausführen, fertig."""

from __future__ import annotations

import argparse
from pathlib import Path

from tabulate import tabulate

from kicktipp import BundesligaPredictor


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundesliga-Kicktipp-Tipps")
    parser.add_argument(
        "--seasons",
        type=int,
        nargs=2,
        metavar=("VON", "BIS"),
        default=(2023, 2027),
        help="Trainings-Saisons (Startjahr OpenLigaDB), Standard: 2023 2027",
    )
    parser.add_argument(
        "--backend",
        choices=("xgboost", "poisson"),
        default="xgboost",
        help="Modell (Standard: xgboost)",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=Path("tipps_naechster_spieltag.html"),
        help="HTML-Datei zum Öffnen im Browser",
    )
    args = parser.parse_args()

    seasons = tuple(range(args.seasons[0], args.seasons[1]))
    print(f"Training ({seasons[0]}–{seasons[-1]}) … kann beim ersten Mal ein paar Minuten dauern.")
    p = BundesligaPredictor(seasons=seasons, model_backend=args.backend, use_dixon_coles=False)
    p.fit()
    tips = p.predict_next_matchday()

    print("\n=== Tipps nächster Spieltag ===\n")
    print(tabulate(tips, headers="keys", tablefmt="simple", showindex=False))
    print("\n--- Zum Eintragen ---")
    for _, row in tips.iterrows():
        print(f"{row['Heim']} – {row['Gast']}: {row['Tipp']}")

    html = tips.to_html(index=False, border=0)
    page = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><title>Bundesliga Tipps</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ccc;padding:8px;text-align:left}}
th{{background:#1a5f2a;color:#fff}}</style></head><body>
<h1>Bundesliga – Tipps nächster Spieltag</h1>
{html}
</body></html>"""
    args.html.write_text(page, encoding="utf-8")
    print(f"\nTabelle gespeichert: {args.html.resolve()}")


if __name__ == "__main__":
    main()