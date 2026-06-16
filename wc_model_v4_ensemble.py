#!/usr/bin/env python3
"""
WCdecider v4 Ensemble Pipeline
==============================

Production stack after 6-degree subagent review + 2-iteration backtest (June 2026).

Architecture (decoupled legs — do NOT blend Dixon-Coles into 1X2):
  - **1X2 anchor**: Elo two-way → closeness draw + Rule 21 finetunes (v3.1 proven)
  - **Goal markets**: Dixon-Coles bivariate Poisson (ρ=-0.07) for O/U, BTTS, P(0-0)
  - **EV / staking layer**: Tier-conditional ensemble (Rule 24) on model + sharp + soft
  - **HALT**: Applied to *blended* EV, not raw model EV

Run: python3 wc_model_v4_ensemble.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import poisson

from wc_ensemble_degree2 import (
    brier_score_1x2,
    dixon_coles_score_matrix,
    sharp_proxy_1x2_from_odds,
)
from wc_replicable_pipeline import (
    apply_finetunes,
    compute_ou_bt_ts,
    expected_lambdas,
    three_way_1x2,
    two_way_win_prob,
)

# ---------------------------------------------------------------------------
# v4 calibrated hyperparameters (Degree-1 constrained search, N=9 backtest)
# ---------------------------------------------------------------------------

V4_DEFAULTS = {
    "rho": -0.07,                    # Dixon-Coles low-score correlation
    "mu_total_default": 2.25,        # MD1-3 observed ~2.0; constrained tune
    "opener_draw_boost": 0.07,       # up from 0.055; better draw calibration
    "minnow_resilience_mult": 1.16,
    "draw_closeness_base": 0.20,     # replaces 0.18 in closeness formula when v4 flag set
    "k_tanh": 0.0038,
    "halt_ev_threshold": 25.0,
    "rule14_longshot_uplift": 0.02,
    "rule14_favorite_shrink": 0.02,
}


class StakeTier(Enum):
    """Rule 24 tier-conditional ensemble weights."""
    MODERATE = "MOD"      # implied p > 40%, odds < 2.5
    SPECULATIVE = "SPEC"  # implied p < 25%, odds >= 4.0
    MARGINAL = "MARG"     # everything else


TIER_WEIGHTS: Dict[StakeTier, Dict[str, float]] = {
    StakeTier.MODERATE: {"model": 0.30, "sharp": 0.50, "soft": 0.20},
    StakeTier.SPECULATIVE: {"model": 0.30, "sharp": 0.15, "soft": 0.55},
    StakeTier.MARGINAL: {"model": 0.40, "sharp": 0.35, "soft": 0.25},
}


def three_way_1x2_v4(
    pA_tw: float,
    s: float = 1.0,
    opener_draw_boost: float = 0.0,
    draw_base: float = 0.20,
) -> Tuple[float, float, float]:
    """v4 closeness draw with tunable base (0.20 vs v3 0.18)."""
    c = 1.0 - abs(pA_tw - 0.5) * 2.0
    d = max(0.15, min(0.32, (draw_base + 0.12 * c) * s)) + opener_draw_boost
    d = min(0.35, d)
    pA = pA_tw * (1.0 - d)
    pB = (1.0 - pA_tw) * (1.0 - d)
    return pA, d, pB


def dixon_coles_ou_bt_ts(
    la: float,
    lb: float,
    threshold: float = 2.5,
    rho: float = -0.07,
    max_goals: int = 10,
) -> Dict[str, float]:
    """O/U and BTTS from full DC score matrix (replaces independent Poisson)."""
    mat = dixon_coles_score_matrix(la, lb, rho=rho, max_goals=max_goals)
    p_under = 0.0
    p_btts_no = 0.0
    p00 = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = mat[i, j]
            total = i + j
            if total < threshold + 0.1:
                p_under += p
            if i == 0 or j == 0:
                p_btts_no += p
            if i == 0 and j == 0:
                p00 += p
    p_over = 1.0 - p_under
    p_btts = 1.0 - p_btts_no
    return {
        "p_over_25": float(p_over),
        "p_under_25": float(p_under),
        "p_btts": float(p_btts),
        "p_btts_no": float(p_btts_no),
        "p_00": float(p00),
        "la": la,
        "lb": lb,
    }


def infer_stake_tier(implied_prob: float, decimal_odds: float) -> StakeTier:
    if implied_prob < 0.25 or decimal_odds >= 4.0:
        return StakeTier.SPECULATIVE
    if implied_prob > 0.40 or decimal_odds < 2.5:
        return StakeTier.MODERATE
    return StakeTier.MARGINAL


def apply_rule14(p: float) -> float:
    """Favorite-longshot bias correction (Snowberg-Wolfers 2010)."""
    if p < 0.25:
        return min(0.99, p + V4_DEFAULTS["rule14_longshot_uplift"])
    if p > 0.65:
        return max(0.01, p - V4_DEFAULTS["rule14_favorite_shrink"])
    return p


def blend_probs(
    legs: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    total_w = sum(weights.values())
    if total_w <= 0:
        return sum(legs.values()) / max(len(legs), 1)
    return sum(weights.get(k, 0) * v for k, v in legs.items()) / total_w


def ensemble_blend_1x2(
    model_1x2: Tuple[float, float, float],
    sharp_1x2: Tuple[float, float, float],
    soft_1x2: Optional[Tuple[float, float, float]],
    tier: StakeTier,
) -> Tuple[float, float, float]:
    """Tier-conditional convex blend for EV/staking (Rule 24)."""
    w = TIER_WEIGHTS[tier]
    soft = soft_1x2 or sharp_1x2
    p_a = blend_probs(
        {"model": model_1x2[0], "sharp": sharp_1x2[0], "soft": soft[0]}, w
    )
    p_d = blend_probs(
        {"model": model_1x2[1], "sharp": sharp_1x2[1], "soft": soft[1]}, w
    )
    p_b = blend_probs(
        {"model": model_1x2[2], "sharp": sharp_1x2[2], "soft": soft[2]}, w
    )
    total = p_a + p_d + p_b
    return p_a / total, p_d / total, p_b / total


def ev_percent(p: float, odds: float) -> float:
    return (p * odds - 1.0) * 100.0


def halt_check_blended(ev_blended: float, sharp_diff_pp: float = 0.0) -> bool:
    if ev_blended > V4_DEFAULTS["halt_ev_threshold"]:
        return True
    if abs(sharp_diff_pp) > 10.0:
        return True
    return False


def classify_v4(
    ev_blended: float,
    robust: bool,
    tier: StakeTier,
) -> Tuple[str, float]:
    """Classification on blended EV (not raw model)."""
    if tier == StakeTier.MODERATE:
        if ev_blended >= 8.0 and robust:
            return "MODERATE", min(65, 45 + int(ev_blended))
        if ev_blended >= 1.5:
            return "PASS", 35  # MOD favorites need higher bar per MD2 lesson
        return "PASS", 30
    if ev_blended >= 8.0 and robust:
        return "STRONG", min(70, 55 + int(ev_blended))
    if ev_blended >= 6.0 and robust:
        return "MODERATE", min(65, 45 + int(ev_blended))
    if ev_blended >= 1.5:
        return "SPECULATIVE", min(60, 35 + int(ev_blended * 1.5))
    return "PASS", 30


@dataclass
class MatchInputV4:
    """Single-match input for v4 pipeline."""
    name: str
    elo_a: float
    elo_b: float
    home_adv: float = 0.0
    form_a: float = 0.0
    form_b: float = 0.0
    injury_a: float = 0.0
    injury_b: float = 0.0
    mu_total: float = 2.25
    finetune_str: str = ""
    # Market odds (screenshot-sourced only)
    o_win_a: Optional[float] = None
    o_draw: Optional[float] = None
    o_win_b: Optional[float] = None
    o_soft_win_a: Optional[float] = None  # cross-book soft side
    overround: float = 1.05
    pick_outcome: str = "A"  # which outcome we evaluate EV for: A/D/B
    robust: bool = True


@dataclass
class MatchOutputV4:
    """Full v4 output per match."""
    name: str
    model_1x2: Tuple[float, float, float]
    blended_1x2: Tuple[float, float, float]
    ou_dc: Dict[str, float]
    ou_indep: Dict[str, float]
    tier: StakeTier
    ev_model: float
    ev_blended: float
    ev_rule14: float
    halt: bool
    classification: str
    confidence: float
    lambdas: Tuple[float, float]
    finetunes_applied: Dict


def run_match_v4(spec: MatchInputV4) -> MatchOutputV4:
    """Execute full v4 stack for one match."""
    ft = apply_finetunes({"finetune_applied": spec.finetune_str})
    if "rule 21" in spec.finetune_str.lower():
        ft["opener_draw_boost"] = V4_DEFAULTS["opener_draw_boost"]

    fa = spec.form_a + spec.injury_a + ft["rotation_penalty"] + ft["finisher_bonus"] + ft["gk_discount"]
    fb = spec.form_b + spec.injury_b
    ea = spec.elo_a
    eb = spec.elo_b

    p_tw = two_way_win_prob(ea, eb, Ha=spec.home_adv, Fa=fa, Fb=fb)
    model_1x2 = three_way_1x2_v4(
        p_tw,
        opener_draw_boost=ft["opener_draw_boost"],
        draw_base=V4_DEFAULTS["draw_closeness_base"],
    )

    if ft["rule14_uplift"] and model_1x2[0] < 0.25:
        p_a, p_d, p_b = model_1x2
        p_a = min(0.99, p_a + 0.02)
        t = p_a + p_d + p_b
        model_1x2 = (p_a / t, p_d / t, p_b / t)

    la, lb = expected_lambdas(
        ea, eb,
        mu_total=spec.mu_total,
        Ha=spec.home_adv,
        Fa=fa,
        Fb=fb,
        k=V4_DEFAULTS["k_tanh"],
        minnow_resilience_mult=ft["minnow_resilience_mult"],
    )
    ou_dc = dixon_coles_ou_bt_ts(la, lb, rho=V4_DEFAULTS["rho"])
    ou_indep = compute_ou_bt_ts(la, lb)

    sharp_1x2 = (1 / 3, 1 / 3, 1 / 3)
    soft_1x2 = None
    if spec.o_win_a is not None:
        sharp_1x2 = sharp_proxy_1x2_from_odds(
            spec.o_win_a, spec.o_draw, spec.o_win_b, overround=spec.overround
        )
        if spec.o_soft_win_a and spec.o_soft_win_a != spec.o_win_a:
            soft_1x2 = sharp_proxy_1x2_from_odds(
                spec.o_soft_win_a, spec.o_draw, spec.o_win_b, overround=spec.overround
            )

    implied = 1.0 / spec.o_win_a if spec.o_win_a else 0.5
    tier = infer_stake_tier(implied, spec.o_win_a or 2.0)
    blended_1x2 = ensemble_blend_1x2(model_1x2, sharp_1x2, soft_1x2, tier)

    outcome_idx = {"A": 0, "D": 1, "B": 2}[spec.pick_outcome]
    odds_map = {
        "A": spec.o_win_a,
        "D": spec.o_draw,
        "B": spec.o_win_b,
    }
    odds = odds_map.get(spec.pick_outcome) or spec.o_win_a or 2.0

    p_model = model_1x2[outcome_idx]
    p_blend = blended_1x2[outcome_idx]
    p_r14 = apply_rule14(p_blend)

    ev_model = ev_percent(p_model, odds)
    ev_blended = ev_percent(p_blend, odds)
    ev_r14 = ev_percent(p_r14, odds)

    sharp_p = sharp_1x2[outcome_idx]
    sharp_diff_pp = (p_blend - sharp_p) * 100.0
    halt = halt_check_blended(ev_r14, sharp_diff_pp)
    cls, conf = classify_v4(ev_r14, spec.robust, tier)

    return MatchOutputV4(
        name=spec.name,
        model_1x2=model_1x2,
        blended_1x2=blended_1x2,
        ou_dc=ou_dc,
        ou_indep=ou_indep,
        tier=tier,
        ev_model=ev_model,
        ev_blended=ev_blended,
        ev_rule14=ev_r14,
        halt=halt,
        classification=cls if not halt else "HALT",
        confidence=conf,
        lambdas=(la, lb),
        finetunes_applied=ft,
    )


def run_sensitivities_v4(
    elo_a: float,
    elo_b: float,
    mu: float = 2.25,
    fa_base: float = 0.0,
    fb_base: float = 0.0,
    finetune_str: str = "",
) -> Dict[str, Dict[str, float]]:
    """Three sensitivity scenarios on v4 1X2 + DC O/U."""
    ft = apply_finetunes({"finetune_applied": finetune_str})
    if "rule 21" in finetune_str.lower():
        ft["opener_draw_boost"] = V4_DEFAULTS["opener_draw_boost"]

    sens = {}
    for label, (ha, fmult) in [
        ("aggressive", (80.0, 1.0)),
        ("base", (50.0, 0.7)),
        ("conservative", (30.0, 0.4)),
    ]:
        fa = fa_base * fmult + ft["rotation_penalty"]
        p_tw = two_way_win_prob(elo_a, elo_b, Ha=ha, Fa=fa, Fb=fb_base * fmult)
        p_a, p_d, p_b = three_way_1x2_v4(p_tw, opener_draw_boost=ft["opener_draw_boost"])
        la, lb = expected_lambdas(
            elo_a, elo_b, mu_total=mu, Ha=ha, Fa=fa, Fb=fb_base * fmult,
            minnow_resilience_mult=ft["minnow_resilience_mult"],
        )
        ou = dixon_coles_ou_bt_ts(la, lb)
        sens[label] = {
            "pA": p_a, "pD": p_d, "pB": p_b,
            "p_over_25": ou["p_over_25"],
            "p_btts": ou["p_btts"],
            "la": la, "lb": lb,
        }
    return sens


def demo_v4_matches() -> List[MatchOutputV4]:
    """Demo on CSV-aligned June 15-16 slate."""
    specs = [
        MatchInputV4(
            name="Spain vs Cape Verde",
            elo_a=2157, elo_b=1578, home_adv=0.0,
            injury_a=-25, mu_total=2.4,
            finetune_str="Rule 21 opener/minnow/rotation",
            o_win_a=1.19, pick_outcome="A",
        ),
        MatchInputV4(
            name="Belgium vs Egypt",
            elo_a=1894, elo_b=1696, home_adv=0.0,
            form_a=8.0, injury_a=-8, mu_total=2.35,
            finetune_str="Rule 21 mild",
            o_win_a=1.67, pick_outcome="A",
        ),
        MatchInputV4(
            name="Netherlands vs Japan (MD2 trap)",
            elo_a=1944, elo_b=1906, home_adv=0.0,
            mu_total=2.4,
            o_win_a=2.15, pick_outcome="A",
            robust=True,
        ),
        MatchInputV4(
            name="Australia vs Turkey (MD2 SPEC)",
            elo_a=1777, elo_b=1911, home_adv=0.0,
            mu_total=2.4,
            o_win_a=5.35, o_soft_win_a=5.35,
            pick_outcome="A",
        ),
    ]
    return [run_match_v4(s) for s in specs]


def print_v4_report(outputs: List[MatchOutputV4]) -> None:
    print("=" * 78)
    print("WCdecider v4 ENSEMBLE — Tier-Conditional EV Layer + DC Goal Markets")
    print("=" * 78)
    for o in outputs:
        print(f"\n### {o.name} [{o.tier.value}]")
        print(f"  Model 1X2:  {o.model_1x2[0]:.1%} / {o.model_1x2[1]:.1%} / {o.model_1x2[2]:.1%}")
        print(f"  Blended:    {o.blended_1x2[0]:.1%} / {o.blended_1x2[1]:.1%} / {o.blended_1x2[2]:.1%}")
        print(f"  λ: {o.lambdas[0]:.3f} / {o.lambdas[1]:.3f}")
        print(f"  DC O2.5: {o.ou_dc['p_over_25']:.1%} | Indep: {o.ou_indep['p_over_25']:.1%}")
        print(f"  EV model={o.ev_model:+.1f}% | blended={o.ev_blended:+.1f}% | R14={o.ev_rule14:+.1f}%")
        print(f"  → {o.classification} (conf {o.confidence}%) HALT={o.halt}")


if __name__ == "__main__":
    print_v4_report(demo_v4_matches())