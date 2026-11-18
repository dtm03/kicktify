# ml-for-kicktipp

Small machine-learning project for **Bundesliga match predictions** (e.g. Kicktipp): load historical data, train a model, and output score tips for the **next matchday**.

**No API keys** are required. Data comes from public sources (OpenLigaDB, football-data.co.uk, Transfermarkt injury list).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Requirements

- Python 3.10+ (tested on 3.12)
- Internet on the first run (then mostly local cache in `data/cache/` — that folder is **not** committed to Git)

## Installation

```bash
git clone <your-repo-url>
cd ml-for-kicktipp
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS/Linux:**

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Get predictions (recommended)

```bash
python tipps.py
```

- Output in the **terminal**
- Also writes **`next_matchday_tips.html`** in the project folder (open in a browser)

Optional flags:

```bash
python tipps.py --seasons 2024 2027    # less history = faster training
python tipps.py --backend poisson      # instead of XGBoost
```

## Jupyter notebook

```bash
jupyter notebook bundesliga_kicktipp.ipynb
```

Run all cells from top to bottom.

## What the model uses

- **Current season & form** (recent matches, weighted heavily)
- **Table proxy**: points per game this season
- **Elo** for overall team strength
- Shot-based xG from football-data for form
- DFB-Pokal fixtures (workload), injury counts (Transfermarkt)

Predictions are **estimates**, not a guarantee of optimal Kicktipp points.

## Publishing this repo

| Topic             | Notes                                                               |
| ----------------- | ------------------------------------------------------------------- |
| **Secrets**       | None needed — no `.env` unless you add your own integrations        |
| **`.gitignore`**  | Excludes `data/cache/`, `.venv`, `__pycache__`, generated HTML tips |
| **Personal data** | None in the code; cache is only public football APIs                |
| **`ideas.md`**    | Personal notes — decide whether to commit before publishing         |

## Project layout

```
kicktipp/                 # model & data pipeline
tipps.py                  # CLI entry point
bundesliga_kicktipp.ipynb
requirements.txt
```
