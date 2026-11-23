"""Kicktipp-style hit rates: exact score, outcome (tendency), goal margin."""

from __future__ import annotations


def parse_score(text: str) -> tuple[int, int]:
    left, right = text.strip().split(":")
    return int(left), int(right)


def outcome(home: int, away: int) -> str:
    if home > away:
        return "H"
    if away > home:
        return "A"
    return "D"


def exact_hit(pick: str, actual: str) -> bool:
    return pick == actual


def tendency_hit(pick: str, actual: str) -> bool:
    ph, pa = parse_score(pick)
    ah, aa = parse_score(actual)
    return outcome(ph, pa) == outcome(ah, aa)


def margin_hit(pick: str, actual: str) -> bool:
    """Torabstand (3 Pkt): gleiche Tordifferenz inkl. Richtung — 2:1 vs 1:2 zählt nicht."""
    if not tendency_hit(pick, actual):
        return False
    ph, pa = parse_score(pick)
    ah, aa = parse_score(actual)
    return (ph - pa) == (ah - aa)


def kicktipp_points(pick: str, actual: str) -> int:
    """Kicktipp: 4 exakt, 3 Torabstand, 2 Tendenz — nur die höchste Kategorie zählt."""
    if exact_hit(pick, actual):
        return 4
    if margin_hit(pick, actual):
        return 3
    if tendency_hit(pick, actual):
        return 2
    return 0


def rate_summary(flags: list[dict]) -> dict:
    n = len(flags)
    if n == 0:
        return {
            "total": 0,
            "exact": 0,
            "tendency": 0,
            "margin": 0,
            "exact_pct": 0.0,
            "tendency_pct": 0.0,
            "margin_pct": 0.0,
            "kicktipp_points": 0,
            "kicktipp_points_max": 0,
            "kicktipp_points_avg": 0.0,
        }
    exact = sum(1 for f in flags if f["exact"])
    tendency = sum(1 for f in flags if f["tendency"])
    margin = sum(1 for f in flags if f["margin"])
    pts = sum(int(f.get("kicktipp_points", 0)) for f in flags)
    max_pts = n * 4
    return {
        "total": n,
        "exact": exact,
        "tendency": tendency,
        "margin": margin,
        "exact_pct": round(100.0 * exact / n, 1),
        "tendency_pct": round(100.0 * tendency / n, 1),
        "margin_pct": round(100.0 * margin / n, 1),
        "kicktipp_points": pts,
        "kicktipp_points_max": max_pts,
        "kicktipp_points_avg": round(pts / n, 2),
    }