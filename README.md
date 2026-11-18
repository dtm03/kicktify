# ml-for-kicktipp

Kleines ML-Projekt für **Kicktipp-Tipps** zur **1. Bundesliga**: historische Daten laden, Modell trainieren, Ergebnisse für den **nächsten Spieltag** ausgeben.

Es werden **keine API-Keys** benötigt. Datenquellen sind öffentlich (OpenLigaDB, football-data.co.uk, Transfermarkt-Liste der Verletzten).

## Voraussetzungen

- Python 3.10+ (getestet mit 3.12)
- Internet beim ersten Lauf (danach überwiegend lokaler Cache in `data/cache/` — dieser Ordner wird **nicht** ins Git committed)

## Installation

```bash
git clone <deine-repo-url>
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

## Tipps anzeigen (empfohlen)

```bash
python tipps.py
```

- Ausgabe in der **Konsole**
- zusätzlich Datei **`tipps_naechster_spieltag.html`** im Projektordner (im Browser öffnen)

Optional:

```bash
python tipps.py --seasons 2024 2027    # weniger History = schneller
python tipps.py --backend poisson      # statt XGBoost
```

## Jupyter Notebook

```bash
jupyter notebook bundesliga_kicktipp.ipynb
```

Alle Zellen von oben nach unten ausführen.

## Was das Modell nutzt (kurz)

- **Aktuelle Saison & Form** (letzte Spiele, schwer gewichtet)
- **Tabellennahe** Kennzahl: Punkte pro Spiel
- **Elo** als allgemeine Mannschaftsstärke
- Schuss-xG aus football-data für Form
- optional Pokal-Spiele (Belastung), Verletzungsliste (Transfermarkt)

Tipps sind **Schätzungen**, kein Anspruch auf optimale Kicktipp-Punkte.

## Repo / Datenschutz

| Thema | Hinweis |
|--------|--------|
| **Secrets** | Nicht nötig — nichts in `.env` anlegen, falls du nichts Eigenes hinzufügst |
| **`.gitignore`** | schließt `data/cache/`, `.venv`, `__pycache__`, generierte HTML-Tipps aus |
| **Personenbezogene Daten** | keine im Code; Cache nur öffentliche Fußball-APIs |
| **`ideas.md`** | private Notizen — vor Publish prüfen, ob du sie committen willst |

## Lizenz

Wenn du öffentlich veröffentlichst: Lizenz setzen (z. B. MIT) — sonst ist die Nutzung für andere unklar.

## Struktur

```
kicktipp/           # Modell & Datenlogik
tipps.py            # CLI-Einstieg
bundesliga_kicktipp.ipynb
requirements.txt
```