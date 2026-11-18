"""Vereinsnamen zwischen Datenquellen vereinheitlichen."""

from __future__ import annotations

import re
import unicodedata

# OpenLigaDB / football-data / Transfermarkt
ALIASES: dict[str, str] = {
    "m'gladbach": "Borussia Mönchengladbach",
    "monchengladbach": "Borussia Mönchengladbach",
    "moenchengladbach": "Borussia Mönchengladbach",
    "borussia m'gladbach": "Borussia Mönchengladbach",
    "bayern munich": "FC Bayern München",
    "bayern munchen": "FC Bayern München",
    "fc bayern": "FC Bayern München",
    "rb leipzig": "RB Leipzig",
    "leverkusen": "Bayer 04 Leverkusen",
    "bayer leverkusen": "Bayer 04 Leverkusen",
    "dortmund": "Borussia Dortmund",
    "frankfurt": "Eintracht Frankfurt",
    "freiburg": "SC Freiburg",
    "hoffenheim": "TSG Hoffenheim",
    "mainz": "1. FSV Mainz 05",
    "mainz 05": "1. FSV Mainz 05",
    "union berlin": "1. FC Union Berlin",
    "werder bremen": "SV Werder Bremen",
    "bremen": "SV Werder Bremen",
    "wolfsburg": "VfL Wolfsburg",
    "stuttgart": "VfB Stuttgart",
    "augsburg": "FC Augsburg",
    "koln": "1. FC Köln",
    "köln": "1. FC Köln",
    "koeln": "1. FC Köln",
    "heidenheim": "1. FC Heidenheim 1846",
    "bochum": "VfL Bochum",
    "darmstadt": "SV Darmstadt 98",
    "hamburg": "Hamburger SV",
    "hsv": "Hamburger SV",
    "schalke": "FC Schalke 04",
    "hertha": "Hertha BSC",
    "pauli": "FC St. Pauli",
    "elversberg": "SV 07 Elversberg",
    "paderborn": "SC Paderborn 07",
}


def _strip(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s


def normalize_team(name: str) -> str:
    if not name:
        return name
    key = _strip(name)
    for fragment, canonical in ALIASES.items():
        if _strip(fragment) == key:
            return canonical
    if key in {_strip(v) for v in ALIASES.values()}:
        return name.strip()
    hit = ALIASES.get(key)
    if hit:
        return hit
    return name.strip()