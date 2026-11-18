"""Bundesliga injury list (Transfermarkt, cached)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .team_names import normalize_team

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
URL = "https://www.transfermarkt.de/bundesliga/verletztespieler/wettbewerb/L1"
CACHE_HOURS = 18.0


def fetch_injury_counts() -> dict[str, int]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "injuries_bundesliga.json"
    if cache.exists():
        age_h = (time.time() - cache.stat().st_mtime) / 3600.0
        if age_h < CACHE_HOURS:
            return {normalize_team(k): int(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}

    html = requests.get(
        URL,
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"},
    ).text
    soup = BeautifulSoup(html, "html.parser")
    counts: dict[str, int] = {}
    for tr in soup.select("table.items tr.odd, table.items tr.even"):
        club = None
        for a in tr.find_all("a", href=True):
            if "/startseite/verein/" in a["href"]:
                img = a.find("img")
                club = (img.get("alt") or img.get("title") if img else None) or a.get_text(strip=True)
                break
        if club:
            name = normalize_team(club)
            counts[name] = counts.get(name, 0) + 1

    cache.write_text(json.dumps(counts, ensure_ascii=False, indent=2), encoding="utf-8")
    return counts


def injury_penalty(injury_count: int) -> float:
    """Mild penalty for many listed injuries (big clubs often have long lists)."""
    return max(0.92, 1.0 - 0.008 * max(injury_count - 5, 0))