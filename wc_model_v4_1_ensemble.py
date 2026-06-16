#!/usr/bin/env python3
"""
WCdecider v4.1 Ensemble Pipeline
================================

Production stack after Iteration 5 (N=222 backtest + 6-degree subagent review).

Changes from v4.0:
  - **MOD EV layer**: pre-stack model 1X2 with devigged market implied (70/30)
    before Rule 24 tier blend — improves blended Brier, preserves trap discipline
  - **Rule 27**: MOD weight changes require trap_count=0 on expanded backtest
  - **Conservative Kelly** (Degree 6): optional stake suggestion with ±3pp draw bands

Unchanged from v4.0:
  - 1X2 anchor: Elo + Rule 21 (NOT blended with Dixon-Coles)
  - Goal markets: Dixon-Coles ρ=-0.07
  - SPEC/MARG tier weights (Rule 24)

Run: python3 wc_model_v4_1_ensemble.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from wc_model_v4_ensemble import (
    V4_DEFAULTS,
    MatchInputV4,
    MatchOutputV4,
    StakeTier,
    apply_rule14,
    classify_v4,
    dixon_coles_ou_bt_ts,
    ensemble_blend_1x2,
    ev_percent,
    halt_check_blended,
    infer_stake_tier,
    run_sensitivities_v4,
    three_way_1x2_v4,
)
from wc_replicable_pipeline import (
    apply_finetunes,
    compute_ou_bt_ts,
    expected_lambdas,
    two_way_win_prob,
)
from wc_ensemble_degree2 import sharp_proxy_1x2_from_odds

# ---------------------------------------------------------------------------
# v4.1 calibrated hyperparameters (Iteration 5 stacking sweep, N=222)
# ---------------------------------------------------------------------------

V41_DEFAULTS = {
    **V4_DEFAULTS,
    "mod_model_market_stack": 0.70,   # MOD tier: 70% model + 30% market before Rule 24
    "draw_band_pp": 0.03,             # Degree 6: ±3pp draw uncertainty for Kelly
    "kelly_fraction": 0.25,           # quarter-Kelly per AGENT.md
    "kelly_haircut": 0.57,            # conservative vs point-estimate Kelly (MD2 sim)
}


def market_implied_1x2(
    o_win_a: float,
    o_draw: Optional[float],
    o_win_b: Optional[float],
) -> Tuple[float, float, float]:
    """Devigged closing/market implied 1X2 from three-way odds."""
    od = o_draw if o_draw is not None else 3.5
    ob = o_win_b if o_win_b is not None else 4.0
    s = 1.0 / o_win_a + 1.0 / od + 1.0 / ob
    return 1.0 / o_win_a / s, 1.0 / od / s, 1.0 / ob / s


def stack_model_market(
    model: Tuple[float, float, float],
    market: Tuple[float, float, float],
    w_model: float = 0.70,
) -> Tuple[float, float, float]:
    """Convex stack of model anchor and market implied, renormalized."""
    w_mkt = 1.0 - w_model
    a = w_model * model[0] + w_mkt * market[0]
    d = w_model * model[1] + w_mkt * market[1]
    b = w_model * model[2] + w_mkt * market[2]
    t = a + d + b
    if t <= 0:
        return model
    return a / t, d / t, b / t


def model_for_ev_layer(
    model_1x2: Tuple[float, float, float],
    market_1x2: Tuple[float, float, float],
    tier: StakeTier,
) -> Tuple[float, float, float]:
    """
    v4.1: MOD tier pre-stacks model with market before Rule 24 blend.
    SPEC/MARG tiers use raw model anchor (longshot alpha preserved).
    """
    if tier == StakeTier.MODERATE:
        return stack_model_market(
            model_1x2,
            market_1x2,
            w_model=V41_DEFAULTS["mod_model_market_stack"],
        )
    return model_1x2


def conservative_kelly_stake(
    p_point: float,
    p_conservative: float,
    odds: float,
    bankroll: float = 200.0,
    kelly_fraction: float = 0.25,
    haircut: float = 0.57,
) -> float:
    """
    Degree 6: quarter-Kelly at conservative probability with draw-band haircut.
    Stake suggestion only — does not alter classification.
    """
    if odds <= 1.0 or p_conservative <= 0:
        return 0.0
    f_star = (p_conservative * odds - 1.0) / (odds - 1.0)
    if f_star <= 0:
        return 0.0
    stake = kelly_fraction * f_star * bankroll * haircut
    return max(0.0, round(stake, 2))


def draw_band_probs(
    p_a: float,
    p_d: float,
    p_b: float,
    band_pp: float = 0.03,
) -> Tuple[float, float, float]:
    """Shift ±band_pp from win mass onto draw for conservative Kelly."""
    d_up = min(0.35, p_d + band_pp)
    delta = d_up - p_d
    scale = max(1e-9, p_a + p_b)
    p_a_c = max(0.01, p_a - delta * (p_a / scale))
    p_b_c = max(0.01, p_b - delta * (p_b / scale))
    t = p_a_c + d_up + p_b_c
    return p_a_c / t, d_up / t, p_b_c / t


@dataclass
class MatchOutputV41(MatchOutputV4):
    """v4.1 output: adds EV-layer model leg and conservative Kelly stake."""
    model_ev_1x2: Tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3)
    market_implied_1x2: Tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3)
    stake_conservative: float = 0.0
    stake_point_kelly: float = 0.0


def run_match_v41(spec: MatchInputV4, bankroll: float = 200.0) -> MatchOutputV41:
    """Execute full v4.1 stack for one match."""
    ft = apply_finetunes({"finetune_applied": spec.finetune_str})
    if "rule 21" in spec.finetune_str.lower():
        ft["opener_draw_boost"] = V4_DEFAULTS["opener_draw_boost"]

    fa = spec.form_a + spec.injury_a + ft["rotation_penalty"] + ft["finisher_bonus"] + ft["gk_discount"]
    fb = spec.form_b + spec.injury_b

    p_tw = two_way_win_prob(spec.elo_a, spec.elo_b, Ha=spec.home_adv, Fa=fa, Fb=fb)
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
        spec.elo_a, spec.elo_b,
        mu_total=spec.mu_total,
        Ha=spec.home_adv,
        Fa=fa,
        Fb=fb,
        k=V4_DEFAULTS["k_tanh"],
        minnow_resilience_mult=ft["minnow_resilience_mult"],
    )
    ou_dc = dixon_coles_ou_bt_ts(la, lb, rho=V4_DEFAULTS["rho"])
    ou_indep = compute_ou_bt_ts(la, lb)

    mkt_1x2 = (1 / 3, 1 / 3, 1 / 3)
    sharp_1x2 = mkt_1x2
    soft_1x2 = None
    if spec.o_win_a is not None:
        mkt_1x2 = market_implied_1x2(spec.o_win_a, spec.o_draw, spec.o_win_b)
        sharp_1x2 = sharp_proxy_1x2_from_odds(
            spec.o_win_a, spec.o_draw, spec.o_win_b, overround=spec.overround
        )
        if spec.o_soft_win_a and spec.o_soft_win_a != spec.o_win_a:
            soft_1x2 = sharp_proxy_1x2_from_odds(
                spec.o_soft_win_a, spec.o_draw, spec.o_win_b, overround=spec.overround
            )

    implied = 1.0 / spec.o_win_a if spec.o_win_a else 0.5
    tier = infer_stake_tier(implied, spec.o_win_a or 2.0)
    model_ev = model_for_ev_layer(model_1x2, mkt_1x2, tier)
    blended_1x2 = ensemble_blend_1x2(model_ev, sharp_1x2, soft_1x2, tier)

    outcome_idx = {"A": 0, "D": 1, "B": 2}[spec.pick_outcome]
    odds_map = {"A": spec.o_win_a, "D": spec.o_draw, "B": spec.o_win_b}
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

    p_a_c, p_d_c, p_b_c = draw_band_probs(*blended_1x2, band_pp=V41_DEFAULTS["draw_band_pp"])
    idx = outcome_idx
    p_cons = (p_a_c, p_d_c, p_b_c)[idx]
    stake_cons = conservative_kelly_stake(
        p_blend, p_cons, odds, bankroll=bankroll,
        kelly_fraction=V41_DEFAULTS["kelly_fraction"],
        haircut=V41_DEFAULTS["kelly_haircut"],
    )
    f_pt = max(0.0, (p_r14 * odds - 1.0) / (odds - 1.0)) if odds > 1 else 0.0
    stake_pt = round(V41_DEFAULTS["kelly_fraction"] * f_pt * bankroll, 2)

    return MatchOutputV41(
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
        model_ev_1x2=model_ev,
        market_implied_1x2=mkt_1x2,
        stake_conservative=stake_cons,
        stake_point_kelly=stake_pt,
    )


def demo_v41_matches():
    """Demo on MD2 lesson matches + June 15-16 slate."""
    from wc_model_v4_ensemble import demo_v4_matches

    specs = [
        MatchInputV4(
            name="Spain vs Cape Verde",
            elo_a=2157, elo_b=1578, home_adv=0.0,
            injury_a=-25, mu_total=2.4,
            finetune_str="Rule 21 opener/minnow/rotation",
            o_win_a=1.19, o_draw=6.50, pick_outcome="D",
        ),
        MatchInputV4(
            name="Netherlands vs Japan (MD2 trap)",
            elo_a=1944, elo_b=1906, home_adv=0.0,
            mu_total=2.4,
            o_win_a=2.15, o_draw=3.40, o_win_b=3.50,
            pick_outcome="A",
        ),
        MatchInputV4(
            name="Australia vs Turkey (MD2 SPEC)",
            elo_a=1777, elo_b=1911, home_adv=0.0,
            mu_total=2.4,
            o_win_a=5.35, o_soft_win_a=5.35,
            o_draw=4.20, o_win_b=1.65,
            pick_outcome="A",
        ),
    ]
    return [run_match_v41(s) for s in specs]


def print_v41_report(outputs) -> None:
    print("=" * 78)
    print("WCdecider v4.1 ENSEMBLE — MOD 70/30 Market Stack + Rule 24 + DC Goals")
    print("=" * 78)
    for o in outputs:
        print(f"\n### {o.name} [{o.tier.value}]")
        print(f"  Model anchor:  {o.model_1x2[0]:.1%} / {o.model_1x2[1]:.1%} / {o.model_1x2[2]:.1%}")
        print(f"  Model EV leg:  {o.model_ev_1x2[0]:.1%} / {o.model_ev_1x2[1]:.1%} / {o.model_ev_1x2[2]:.1%}")
        print(f"  Market impl:   {o.market_implied_1x2[0]:.1%} / {o.market_implied_1x2[1]:.1%} / {o.market_implied_1x2[2]:.1%}")
        print(f"  Blended EV:    {o.blended_1x2[0]:.1%} / {o.blended_1x2[1]:.1%} / {o.blended_1x2[2]:.1%}")
        print(f"  EV model={o.ev_model:+.1f}% | blended={o.ev_blended:+.1f}% | R14={o.ev_rule14:+.1f}%")
        print(f"  Stake: cons={o.stake_conservative:.2f} | point ¼K={o.stake_point_kelly:.2f}")
        print(f"  → {o.classification} (conf {o.confidence}%) HALT={o.halt}")


if __name__ == "__main__":
    print_v41_report(demo_v41_matches())