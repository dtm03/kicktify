"""Dixon–Coles adjustment for draws and low-scoring results."""

from __future__ import annotations

import math

import numpy as np


def _poisson_pmf(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam**k) / math.factorial(k)


def tau(i: int, j: int, lam_h: float, lam_a: float, rho: float) -> float:
    if i == 0 and j == 0:
        return 1.0 - lam_h * lam_a * rho
    if i == 0 and j == 1:
        return 1.0 + lam_h * rho
    if i == 1 and j == 0:
        return 1.0 + lam_a * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_prob_matrix(lam_h: float, lam_a: float, rho: float, max_g: int = 6) -> np.ndarray:
    hs = np.arange(0, max_g + 1)
    aws = np.arange(0, max_g + 1)
    ph = np.array([_poisson_pmf(int(i), lam_h) for i in hs])
    pa = np.array([_poisson_pmf(int(j), lam_a) for j in aws])
    grid = np.outer(ph, pa)
    for i in range(min(2, max_g + 1)):
        for j in range(min(2, max_g + 1)):
            grid[i, j] *= tau(i, j, lam_h, lam_a, rho)
    total = grid.sum()
    if total > 0:
        grid /= total
    return grid


def most_likely_score(lam_h: float, lam_a: float, rho: float, max_g: int = 6) -> tuple[int, int]:
    grid = score_prob_matrix(lam_h, lam_a, rho, max_g=max_g)
    i, j = np.unravel_index(int(np.argmax(grid)), grid.shape)
    return int(i), int(j)


def fit_rho(
    lam_home: np.ndarray,
    lam_away: np.ndarray,
    goals_home: np.ndarray,
    goals_away: np.ndarray,
    grid: int = 21,
) -> float:
    """Rough MLE over a rho grid on training data."""
    rhos = np.linspace(-0.25, 0.08, grid)
    best_rho, best_ll = 0.0, -np.inf
    for rho in rhos:
        ll = 0.0
        for lh, la, gh, ga in zip(lam_home, lam_away, goals_home, goals_away, strict=False):
            gh_i, ga_i = int(gh), int(ga)
            if gh_i > 6 or ga_i > 6:
                gh_i = min(gh_i, 6)
                ga_i = min(ga_i, 6)
            p = _poisson_pmf(gh_i, lh) * _poisson_pmf(ga_i, la) * tau(gh_i, ga_i, lh, la, float(rho))
            ll += math.log(max(p, 1e-12))
        if ll > best_ll:
            best_ll, best_rho = ll, float(rho)
    return best_rho