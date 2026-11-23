# ml-for-kicktipp

Small machine-learning project for **Bundesliga match predictions** (e.g. Kicktipp): historical backtest in the browser, next matchday tips from committed JSON.

**No API keys** are required. Data comes from public sources (OpenLigaDB, football-data.co.uk, Transfermarkt injury list).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Requirements

- Python 3.10+ (tested on 3.12)
- Internet on the first run (then mostly local cache in `data/cache/` — **not** committed)

## CLI & notebook

```bash
pip install -r requirements.txt
python tipps.py
jupyter notebook bundesliga_kicktipp.ipynb
```

---

## Web app + Vercel (how it works)

The **public website** does **not** train a model when you click the button. Everyone sees the **same data**:

| File (committed in Git) | Purpose |
|-------------------------|---------|
| `web/public/data/season_backtest.json` | Finished matchdays: picks vs results, 3 hit rates |
| `web/public/data/live_prediction.json` | **Current** next-matchday tips |
| `web/public/data/prediction_gate.json` | Info text (kickoff, window) |

### Weekly update (recommended): GitHub Action

Workflow [`.github/workflows/weekly-kicktipp.yml`](.github/workflows/weekly-kicktipp.yml):

- Runs **every Monday 08:00 UTC** (or manually: *Actions → weekly-kicktipp → Run workflow*)
- Trains in CI, updates the JSON files, **commits and pushes**
- Vercel redeploys → **all visitors** see the new tips

**No secrets** required. After forking:

1. Enable **Actions** in the repo settings
2. Allow GitHub Actions to **write** commits (default on user forks)
3. Deploy `web/` on Vercel (root directory `web`)

### What the website button does

**Nächsten Spieltag predicten**:

1. Waits ~**5 seconds** (loading animation)
2. Loads **`/data/live_prediction.json`** from the deployed site (already computed by the Action)
3. Tips are **not** kept across reload — each visit shows only backtest history until you click predict again (same JSON from the repo every time)

No Python on Vercel at click time — fits the **free** Hobby plan.

**UX:** Reload → scroll = past matchdays only. Click predict → current tips appear for this session. Reload again → hidden until you click predict again.

**Local dev only:** real server training with `http://localhost:3000?train=1` (calls `/api/predict`).

### Manual update (without waiting for Monday)

```bash
pip install -r requirements.txt
python scripts/export_web_data.py --backend poisson
python scripts/export_prediction_status.py
python scripts/predict_and_save.py --force --backend xgboost
git add web/public/data/
git commit -m "chore: update kicktipp JSON"
git push
```

### For others using **your** public site

They only open the URL — same JSON as you. No setup.

### For others running **their own** fork

1. Fork, enable Actions, deploy Vercel (`web/`)
2. Same Monday workflow **or** manual script + push above
3. Optional: change cron in the workflow file

The source of truth for everyone is **Git + Vercel static files** (updated by the weekly Action).

---

## Local web dev

```bash
pip install -r requirements.txt
python scripts/export_web_data.py --backend poisson
python scripts/export_prediction_status.py
python scripts/predict_and_save.py --force
cd web && npm install && npm run dev
```

---

## Deploy on Vercel

1. Import repo
2. **Root Directory:** `web`
3. Build `prebuild` runs Python exports if the build image has Python; otherwise commit the three JSON files before deploy
4. **Free tier is enough** — no heavy `/api/predict` in production use

---

## Project layout

```
kicktipp/                      # Python model
web/                           # Next.js UI
web/public/data/*.json         # Committed — shared predictions
scripts/                       # export & predict
.github/workflows/weekly-kicktipp.yml
```