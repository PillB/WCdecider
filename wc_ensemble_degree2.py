#!/usr/bin/env python3
"""
WCdecider Degree-2 Ensemble: Dixon-Coles + Bradley-Terry-Davidson + Weighted Blend
===================================================================================

Moderate structural upgrade over independent Poisson:
  - Leg A (35%): Elo two-way → closeness draw (existing v3 1X2)
  - Leg B (35%): Dixon-Coles bivariate Poisson score matrix → 1X2 (rho parameter)
  - Leg C (30%): Sharp-proxy devigged from screenshot win odds

Backtests Spain-CV (0-0) and BEL-EGY (1-1) with multiclass Brier on 1X2.

Run: python3 wc_ensemble_degree2.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import poisson

# Reuse validated v3 primitives
from wc_model_v3 import (
    ELO,
    expected_lambdas,
    three_way_1x2,
    two_way_win_prob,
)

# ---------------------------------------------------------------------------
# Dixon-Coles (1997) tau adjustment — full score-matrix 1X2
# ---------------------------------------------------------------------------

def dc_tau(i: int, j: int, la: float, lb: float, rho: float) -> float:
    """Dixon-Coles dependence factor for score (i, j)."""
    if i == 0 and j == 0:
        return 1.0 - la * lb * rho
    if i == 0 and j == 1:
        return 1.0 + la * rho
    if i == 1 and j == 0:
        return 1.0 + lb * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def dixon_coles_score_matrix(
    la: float,
    lb: float,
    rho: float = -0.07,
    max_goals: int = 10,
) -> np.ndarray:
    """
    Build normalized DC-adjusted joint score matrix P[i,j].
    Negative rho raises mass on (0,0), (1,0), (0,1) and lowers (1,1) — classic low-score correlation.
    """
    raw = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            raw[i, j] = (
                dc_tau(i, j, la, lb, rho)
                * poisson.pmf(i, la)
                * poisson.pmf(j, lb)
            )
    raw = np.maximum(raw, 0.0)
    total = raw.sum()
    if total <= 0:
        raise ValueError("DC matrix degenerate — check lambdas/rho")
    return raw / total


def dixon_coles_1x2(
    la: float,
    lb: float,
    rho: float = -0.07,
    max_goals: int = 10,
) -> Tuple[float, float, float]:
    """1X2 from DC score matrix: P(A win), P(draw), P(B win)."""
    mat = dixon_coles_score_matrix(la, lb, rho, max_goals)
    p_draw = float(np.trace(mat))
    p_a = float(np.tril(mat, k=-1).sum())   # i > j
    p_b = float(np.triu(mat, k=1).sum())    # i < j
    return p_a, p_draw, p_b


def independent_poisson_1x2(la: float, lb: float, max_goals: int = 10) -> Tuple[float, float, float]:
    """1X2 from *independent* Poisson score matrix (rho=0, no tau). Baseline critique target."""
    mat = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            mat[i, j] = poisson.pmf(i, la) * poisson.pmf(j, lb)
    p_draw = float(np.trace(mat))
    p_a = float(np.tril(mat, k=-1).sum())
    p_b = float(np.triu(mat, k=1).sum())
    return p_a, p_draw, p_b


# ---------------------------------------------------------------------------
# Bradley-Terry-Davidson draw leg
# ---------------------------------------------------------------------------

def elo_to_bt_strength(elo: float, scale: float = 400.0) -> float:
    """Map Elo to BT log-strength (centered at 1500)."""
    return (elo - 1500.0) / scale


def bradley_terry_davidson_1x2(
    r_a: float,
    r_b: float,
    home: float = 0.0,
    delta: float = 0.82,
) -> Tuple[float, float, float]:
    """
    BTD extension with draw parameter delta.
    delta ~ draw propensity; 0.7-1.0 typical for international football.
    Ref: Davidson (1970); arXiv:2405.10247 Bayesian BTD for football.
    """
    exp_a = math.exp(r_a - r_b + home)
    denom = exp_a + 1.0 + delta
    p_a = exp_a / denom
    p_d = delta / denom
    p_b = 1.0 / denom
    return p_a, p_d, p_b


def btd_from_elo(
    elo_a: float,
    elo_b: float,
    ha: float = 0.0,
    fa: float = 0.0,
    fb: float = 0.0,
    delta: float = 0.82,
    elo_scale: float = 400.0,
) -> Tuple[float, float, float]:
    """BTD 1X2 from effective Elo ratings (+ home/form overlays as logit shift)."""
    eff_a = elo_a + ha + fa
    eff_b = elo_b + fb
    r_a = elo_to_bt_strength(eff_a, elo_scale)
    r_b = elo_to_bt_strength(eff_b, elo_scale)
    return bradley_terry_davidson_1x2(r_a, r_b, home=0.0, delta=delta)


def dc_btd_hybrid_1x2(
    la: float,
    lb: float,
    elo_a: float,
    elo_b: float,
    ha: float = 0.0,
    fa: float = 0.0,
    fb: float = 0.0,
    rho: float = -0.07,
    btd_delta: float = 0.82,
) -> Tuple[float, float, float]:
    """
    Degree-2 structural leg: DC score matrix for win/loss mass + BTD draw propensity.
    Rationale: raw DC 1X2 under-predicts draws in WC openers when lambdas are Elo-skewed;
    BTD supplies a literature-backed draw parameter (Davidson 1970) while DC retains rho
    correction on the low-score tail for combo markets.
    """
    p_dc_a, p_dc_d, p_dc_b = dixon_coles_1x2(la, lb, rho=rho)
    _, p_btd_d, _ = btd_from_elo(elo_a, elo_b, ha=ha, fa=fa, fb=fb, delta=btd_delta)
    # Allocate draw from BTD; split non-draw mass by DC win ratio
    p_d = min(0.40, max(0.10, p_btd_d))
    rem = 1.0 - p_d
    dc_win_ratio = p_dc_a / max(p_dc_a + p_dc_b, 1e-9)
    p_a = rem * dc_win_ratio
    p_b = rem * (1.0 - dc_win_ratio)
    total = p_a + p_d + p_b
    return p_a / total, p_d / total, p_b / total


# ---------------------------------------------------------------------------
# Sharp-proxy leg (devigged screenshot win odds → full 1X2)
# ---------------------------------------------------------------------------

def devig_two_way(p_a: float, p_b: float) -> Tuple[float, float]:
    """Remove overround from two implied probabilities."""
    s = p_a + p_b
    if s <= 0:
        return 0.5, 0.5
    return p_a / s, p_b / s


def devig_three_way(p_a: float, p_d: float, p_b: float) -> Tuple[float, float, float]:
    s = p_a + p_d + p_b
    if s <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return p_a / s, p_d / s, p_b / s


def sharp_proxy_1x2_from_odds(
    o_win_a: float,
    o_draw: Optional[float] = None,
    o_win_b: Optional[float] = None,
    overround: float = 1.05,
) -> Tuple[float, float, float]:
    """
    Construct sharp-proxy 1X2 from book prices.
    If only win odds available, allocate residual via WC opener draw prior (closeness-scaled).
    Sources: MD4 screenshots ESP 1.19, BEL 1.67 (Betano/Betsson 2026-06-15).
    """
    p_win_raw = 1.0 / o_win_a
    if o_draw is not None and o_win_b is not None:
        return devig_three_way(1 / o_win_a, 1 / o_draw, 1 / o_win_b)

    # Partial market: scale win to fair, split remainder with draw-heavy WC opener prior
    p_win = p_win_raw / overround
    p_win = min(0.92, max(0.05, p_win))
    # Residual split: draw share rises as match becomes less one-sided
    closeness = 1.0 - abs(p_win - 0.5) * 2.0
    draw_share_of_residual = 0.35 + 0.25 * closeness  # 0.35-0.60 of non-win mass
    residual = 1.0 - p_win
    p_draw = residual * draw_share_of_residual
    p_loss = residual - p_draw
    return devig_three_way(p_win, p_draw, p_loss)


# ---------------------------------------------------------------------------
# Ensemble blend + Brier
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {"elo": 0.35, "dc": 0.35, "sharp": 0.30}


def blend_1x2(
    legs: Dict[str, Tuple[float, float, float]],
    weights: Dict[str, float] = None,
) -> Tuple[float, float, float]:
    """Weighted convex combination of 1X2 legs; renormalize."""
    w = weights or DEFAULT_WEIGHTS
    p_a = p_d = p_b = 0.0
    for name, (a, d, b) in legs.items():
        wt = w.get(name, 0.0)
        p_a += wt * a
        p_d += wt * d
        p_b += wt * b
    total = p_a + p_d + p_b
    if total <= 0:
        return 1 / 3, 1 / 3, 1 / 3
    return p_a / total, p_d / total, p_b / total


def brier_score_1x2(probs: Tuple[float, float, float], outcome: str) -> float:
    """
    Multiclass Brier for 1X2.
    outcome: 'A' (home win), 'D' (draw), 'B' (away win)
    BS = sum_k (p_k - I_k)^2  — lower is better; perfect=0, naive uniform=0.667.
    """
    o_map = {"A": (1, 0, 0), "D": (0, 1, 0), "B": (0, 0, 1)}
    actual = o_map[outcome]
    return sum((p - a) ** 2 for p, a in zip(probs, actual))


def elo_leg_1x2(
    elo_a: float,
    elo_b: float,
    ha: float = 50.0,
    fa: float = 0.0,
    fb: float = 0.0,
    opener_draw_boost: float = 0.0,
) -> Tuple[float, float, float]:
    """Existing v3 Elo → closeness draw leg."""
    p_tw = two_way_win_prob(elo_a, elo_b, ha, 0.0, fa, fb)
    return three_way_1x2(p_tw, s=1.0, opener_draw_boost=opener_draw_boost)


# ---------------------------------------------------------------------------
# Match specs for backtest
# ---------------------------------------------------------------------------

@dataclass
class BacktestMatch:
    name: str
    team_a: str
    team_b: str
    elo_a: float
    elo_b: float
    ha: float
    fa: float
    fb: float
    mu: float
    outcome: str  # 'A', 'D', 'B'
    o_win_a: float
    o_draw: Optional[float] = None
    o_win_b: Optional[float] = None
    opener_draw_boost: float = 0.0
    minnow_resilience_mult: float = 1.0
    rotation_penalty: float = 0.0


BACKTEST_MATCHES = [
    BacktestMatch(
        name="Spain vs Cape Verde",
        team_a="ESP", team_b="CPV",
        elo_a=ELO["ESP"], elo_b=ELO["CPV"],
        ha=0.0, fa=-25.0, fb=0.0,  # rotation penalty per Rule 21
        mu=2.4,
        outcome="D",
        o_win_a=1.19,
        opener_draw_boost=0.055,
        minnow_resilience_mult=1.16,
        rotation_penalty=-25.0,
    ),
    BacktestMatch(
        name="Belgium vs Egypt",
        team_a="BEL", team_b="EGY",
        elo_a=ELO["BEL"], elo_b=ELO["EGY"],
        ha=0.0, fa=0.0, fb=0.0,  # CSV: form 8 + injury -8 = 0 (wc_2026_model_dataset.csv)
        mu=2.35,
        outcome="D",
        o_win_a=1.67,
        opener_draw_boost=0.055,
        minnow_resilience_mult=1.0,
        rotation_penalty=0.0,
    ),
]


def build_match_probs(
    m: BacktestMatch,
    rho: float = -0.07,
    btd_delta: float = 0.82,
    ensemble_weights: Dict[str, float] = None,
) -> Dict[str, Tuple[float, float, float]]:
    """All model legs + ensemble for one match."""
    fa = m.fa + m.rotation_penalty
    la, lb = expected_lambdas(
        m.elo_a, m.elo_b, mu_total=m.mu, Ha=m.ha,
        Fa=fa, Fb=m.fb,
        minnow_resilience_mult=m.minnow_resilience_mult,
    )

    elo_leg = elo_leg_1x2(
        m.elo_a, m.elo_b, ha=m.ha, fa=fa, fb=m.fb,
        opener_draw_boost=m.opener_draw_boost,
    )
    dc_leg = dixon_coles_1x2(la, lb, rho=rho)
    dc_btd_leg = dc_btd_hybrid_1x2(
        la, lb, m.elo_a, m.elo_b, ha=m.ha, fa=fa, fb=m.fb,
        rho=rho, btd_delta=btd_delta,
    )
    indep_leg = independent_poisson_1x2(la, lb)
    btd_leg = btd_from_elo(m.elo_a, m.elo_b, ha=m.ha, fa=fa, fb=m.fb, delta=btd_delta)
    sharp_leg = sharp_proxy_1x2_from_odds(m.o_win_a, m.o_draw, m.o_win_b)

    # Primary ensemble: Elo 35% / DC+BTD hybrid 35% / sharp 30%
    ensemble = blend_1x2(
        {"elo": elo_leg, "dc": dc_btd_leg, "sharp": sharp_leg},
        ensemble_weights or DEFAULT_WEIGHTS,
    )
    # Legacy pure-DC ensemble for comparison
    ensemble_pure_dc = blend_1x2(
        {"elo": elo_leg, "dc": dc_leg, "sharp": sharp_leg},
        ensemble_weights or DEFAULT_WEIGHTS,
    )

    return {
        "elo_v3": elo_leg,
        "indep_poisson": indep_leg,
        "dixon_coles": dc_leg,
        "dc_btd_hybrid": dc_btd_leg,
        "btd": btd_leg,
        "sharp_proxy": sharp_leg,
        "ensemble_35_35_30": ensemble,
        "ensemble_pure_dc": ensemble_pure_dc,
        "lambdas": (la, lb),
    }


def shock_sensitivity(
    m: BacktestMatch,
    rho_grid: List[float] = None,
    rotation_grid: List[float] = None,
    minnow_grid: List[float] = None,
) -> List[Dict]:
    """Sweep shock parameters; report draw prob and Brier for ensemble."""
    rho_grid = rho_grid or [-0.15, -0.10, -0.07, -0.05, -0.03, 0.0]
    rotation_grid = rotation_grid or [0, -15, -25, -40]
    minnow_grid = minnow_grid or [1.0, 1.08, 1.16, 1.20]
    rows = []

    for rho in rho_grid:
        probs = build_match_probs(m, rho=rho)
        bs = brier_score_1x2(probs["ensemble_35_35_30"], m.outcome)
        rows.append({
            "shock": "rho",
            "value": rho,
            "p_draw": probs["ensemble_35_35_30"][1],
            "brier": bs,
        })

    base = BacktestMatch(**{**m.__dict__})
    for rot in rotation_grid:
        base.rotation_penalty = rot
        base.fa = m.fa - m.rotation_penalty + rot  # keep total fa consistent
        probs = build_match_probs(base, rho=-0.07)
        bs = brier_score_1x2(probs["ensemble_35_35_30"], m.outcome)
        rows.append({
            "shock": "rotation_penalty",
            "value": rot,
            "p_draw": probs["ensemble_35_35_30"][1],
            "brier": bs,
        })

    for mm in minnow_grid:
        base = BacktestMatch(**{**m.__dict__})
        base.minnow_resilience_mult = mm
        probs = build_match_probs(base, rho=-0.07)
        bs = brier_score_1x2(probs["ensemble_35_35_30"], m.outcome)
        rows.append({
            "shock": "minnow_resilience",
            "value": mm,
            "p_draw": probs["ensemble_35_35_30"][1],
            "brier": bs,
        })

    return rows


def run_backtest_report() -> Dict:
    """Full Degree-2 backtest: Spain-CV + BEL-EGY, Brier comparison."""
    print("=" * 78)
    print("WCdecider DEGREE-2: DC + BTD + Ensemble (Elo 35% / DC 35% / Sharp 30%)")
    print("Backtest: Spain-CV (0-0) & BEL-EGY (1-1) | Metric: multiclass Brier 1X2")
    print("=" * 78)

    all_results = {}
    aggregate_brier: Dict[str, List[float]] = {}

    for m in BACKTEST_MATCHES:
        probs = build_match_probs(m, rho=-0.07)
        la, lb = probs["lambdas"]
        print(f"\n### {m.name} | Actual: DRAW | λA={la:.3f} λB={lb:.3f}")
        print(f"{'Model':<22} {'P(Win)':>8} {'P(Draw)':>8} {'P(Loss)':>8} {'Brier':>8}")
        print("-" * 58)

        match_brier = {}
        for model_name in [
            "elo_v3", "indep_poisson", "dixon_coles", "dc_btd_hybrid", "btd",
            "sharp_proxy", "ensemble_35_35_30", "ensemble_pure_dc",
        ]:
            if model_name == "lambdas":
                continue
            p = probs[model_name]
            bs = brier_score_1x2(p, m.outcome)
            match_brier[model_name] = bs
            aggregate_brier.setdefault(model_name, []).append(bs)
            print(f"{model_name:<22} {p[0]:>7.1%} {p[1]:>7.1%} {p[2]:>7.1%} {bs:>8.4f}")

        all_results[m.name] = {"probs": probs, "brier": match_brier}

        print(f"\n  Shock sensitivity (ensemble Brier, {m.name}):")
        sens = shock_sensitivity(m)
        for shock_type in ("rho", "rotation_penalty", "minnow_resilience"):
            subset = [r for r in sens if r["shock"] == shock_type]
            best = min(subset, key=lambda x: x["brier"])
            print(f"    {shock_type}: best Brier={best['brier']:.4f} at {best['value']} "
                  f"(P_draw={best['p_draw']:.1%})")

    print("\n" + "=" * 78)
    print("AGGREGATE BRIER (2-match mean; lower = better calibration on realized draws)")
    print("=" * 78)
    means = {k: np.mean(v) for k, v in aggregate_brier.items()}
    ranked = sorted(means.items(), key=lambda x: x[1])
    for name, mean_bs in ranked:
        delta = mean_bs - ranked[0][1]
        print(f"  {name:<22} mean Brier = {mean_bs:.4f}  (Δ vs best = {delta:+.4f})")

    # Rho calibration sweep (both matches)
    print("\n--- Rho calibration grid (ensemble, both matches) ---")
    rho_vals = [-0.15, -0.12, -0.10, -0.08, -0.07, -0.05, -0.03, 0.0]
    best_rho = None
    best_mean = 999.0
    for rho in rho_vals:
        bs_list = []
        for m in BACKTEST_MATCHES:
            p = build_match_probs(m, rho=rho)["ensemble_35_35_30"]
            bs_list.append(brier_score_1x2(p, m.outcome))
        mean_bs = float(np.mean(bs_list))
        marker = ""
        if mean_bs < best_mean:
            best_mean = mean_bs
            best_rho = rho
        print(f"  rho={rho:+.2f}  mean Brier={mean_bs:.4f}")
    print(f"  >>> Recommended rho (2-match backtest): {best_rho} (mean Brier={best_mean:.4f})")

    # Weight sensitivity (±10pp shifts)
    print("\n--- Ensemble weight sensitivity (±10pp from 35/35/30) ---")
    weight_scenarios = [
        ("baseline", {"elo": 0.35, "dc": 0.35, "sharp": 0.30}),
        ("more_sharp", {"elo": 0.25, "dc": 0.35, "sharp": 0.40}),
        ("more_dc", {"elo": 0.25, "dc": 0.45, "sharp": 0.30}),
        ("more_elo", {"elo": 0.45, "dc": 0.25, "sharp": 0.30}),
        ("equal", {"elo": 0.333, "dc": 0.333, "sharp": 0.334}),
    ]
    for label, w in weight_scenarios:
        bs_list = []
        for m in BACKTEST_MATCHES:
            p = build_match_probs(m, rho=best_rho, ensemble_weights=w)["ensemble_35_35_30"]
            bs_list.append(brier_score_1x2(p, m.outcome))
        print(f"  {label:<12} {w}  mean Brier={np.mean(bs_list):.4f}")

    return {"matches": all_results, "mean_brier": means, "best_rho": best_rho}


if __name__ == "__main__":
    run_backtest_report()