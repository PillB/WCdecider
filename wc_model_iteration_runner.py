#!/usr/bin/env python3
"""
WCdecider Iteration Runner — Cross-validation, stacking, hyperparameter sweeps
=============================================================================

Iteration 5: executes multi-strata CV on wc_backtest_historical_dataset.csv,
compares candidate stacks, outputs best robust config.

Run: python3 wc_model_iteration_runner.py
"""

from __future__ import annotations

import math
from itertools import product
from typing import Dict, List, Tuple

import numpy as np

from wc_backtest_framework import get_all_matches, HistoricalMatch, weighted_mean
from wc_ensemble_degree2 import brier_score_1x2
from wc_model_v4_ensemble import (
    V4_DEFAULTS,
    MatchInputV4,
    three_way_1x2_v4,
)
from wc_model_v4_1_ensemble import run_match_v41
from wc_replicable_pipeline import apply_finetunes, two_way_win_prob


def market_implied_1x2(m: HistoricalMatch) -> Tuple[float, float, float]:
    s = 1 / m.o_win_a + 1 / m.o_draw + 1 / m.o_win_b
    return 1 / m.o_win_a / s, 1 / m.o_draw / s, 1 / m.o_win_b / s


def stack_1x2(
    model: Tuple[float, float, float],
    market: Tuple[float, float, float],
    w_model: float = 0.70,
) -> Tuple[float, float, float]:
    w_mkt = 1.0 - w_model
    a = w_model * model[0] + w_mkt * market[0]
    d = w_model * model[1] + w_mkt * market[1]
    b = w_model * model[2] + w_mkt * market[2]
    t = a + d + b
    return a / t, d / t, b / t


def predict_v4_custom(
    m: HistoricalMatch,
    opener_boost: float = 0.07,
    draw_base: float = 0.20,
) -> Tuple[float, float, float]:
    ft = apply_finetunes({"finetune_applied": m.finetune})
    if "rule 21" in m.finetune.lower():
        ft["opener_draw_boost"] = opener_boost
    fa = m.fa + ft["rotation_penalty"]
    p_tw = two_way_win_prob(m.elo_a, m.elo_b, Ha=m.ha, Fa=fa, Fb=m.fb)
    return three_way_1x2_v4(p_tw, opener_draw_boost=ft["opener_draw_boost"], draw_base=draw_base)


def eval_config(
    matches: List[HistoricalMatch],
    predictor,
    label: str,
) -> Dict:
    briers, weights, traps = [], [], 0
    for m in matches:
        p = predictor(m)
        briers.append(brier_score_1x2(p, m.outcome))
        weights.append(m.comp_weight)
        if m.o_win_a < 2.5:
            out = run_match_v41(MatchInputV4(
                name=m.name, elo_a=m.elo_a, elo_b=m.elo_b,
                o_win_a=m.o_win_a, o_draw=m.o_draw, o_win_b=m.o_win_b,
                finetune_str=m.finetune, pick_outcome="A",
            ))
            if out.ev_rule14 > 1.5 and out.classification not in ("PASS", "HALT"):
                traps += 1
    return {
        "label": label,
        "brier": weighted_mean(briers, weights),
        "trap_count": traps,
        "n": len(matches),
    }


def wc_strata(matches: List[HistoricalMatch]) -> List[HistoricalMatch]:
    return [m for m in matches if "WC" in m.competition]


def hyperparam_grid_wc(matches: List[HistoricalMatch]) -> List[Dict]:
    wc = wc_strata(matches)
    results = []
    for ob, db, mu in product([0.055, 0.06, 0.07, 0.08], [0.18, 0.20, 0.22], [2.2, 2.25, 2.3]):
        def pred(m, ob=ob, db=db):
            return predict_v4_custom(m, opener_boost=ob, draw_base=db)
        r = eval_config(wc, pred, f"ob={ob} db={db}")
        r["opener_boost"] = ob
        r["draw_base"] = db
        r["mu"] = mu
        results.append(r)
    return sorted(results, key=lambda x: x["brier"])


def stacking_sweep(matches: List[HistoricalMatch]) -> List[Dict]:
    results = []
    for w in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        def pred(m, w=w):
            p_m = predict_v4_custom(m)
            p_k = market_implied_1x2(m)
            return stack_1x2(p_m, p_k, w_model=w)
        r = eval_config(matches, pred, f"stack_model_{int(w*100)}")
        r["w_model"] = w
        results.append(r)
    return results


def shock_cases(matches: List[HistoricalMatch]) -> List[Dict]:
    """Known upset / draw shocks."""
    shocks = []
    keys = [("ARG", "KSA"), ("GER", "JPN"), ("ESP", "CPV"), ("TUN", "FRA"), ("KOR", "GER")]
    for m in matches:
        if (m.team_a, m.team_b) in keys or (m.team_b, m.team_a) in keys:
            p_v4 = predict_v4_custom(m)
            p_mkt = market_implied_1x2(m)
            p_stk = stack_1x2(p_v4, p_mkt, 0.7)
            shocks.append({
                "match": f"{m.team_a}-{m.team_b} ({m.date})",
                "outcome": m.outcome,
                "p_v4_draw": p_v4[1],
                "p_mkt_draw": p_mkt[1],
                "p_stk_draw": p_stk[1],
                "brier_v4": brier_score_1x2(p_v4, m.outcome),
                "brier_stk": brier_score_1x2(p_stk, m.outcome),
            })
    return shocks


def time_split_cv(matches: List[HistoricalMatch]) -> Dict:
    """Train params on pre-2026, test on 2026."""
    train = [m for m in matches if not m.date.endswith("/2026")]
    test = [m for m in matches if m.date.endswith("/2026")]
    best = min(hyperparam_grid_wc(train), key=lambda x: x["brier"])
    ob, db = best["opener_boost"], best["draw_base"]

    def pred(m):
        return predict_v4_custom(m, opener_boost=ob, draw_base=db)

    train_r = eval_config(train, pred, "train")
    test_r = eval_config(test, pred, "test_2026")
    return {"best_hp": best, "train": train_r, "test_2026": test_r}


def run_iteration_5() -> Dict:
    print("=" * 78)
    print("WCdecider ITERATION 5 — Cross-validation & stacking sweep")
    print("=" * 78)
    matches = get_all_matches()

    baseline = eval_config(matches, predict_v4_custom, "v4_baseline")
    print(f"\nBaseline v4: Brier={baseline['brier']:.4f} traps={baseline['trap_count']}")

    hp = hyperparam_grid_wc(matches)[:5]
    print("\n--- Top 5 hyperparams (WC strata only) ---")
    for r in hp:
        print(f"  ob={r['opener_boost']} db={r['draw_base']} Brier={r['brier']:.4f}")

    stk = stacking_sweep(matches)
    print("\n--- Stacking sweep (v4 + market implied) ---")
    for r in stk:
        print(f"  w_model={r['w_model']:.1f} Brier={r['brier']:.4f} traps={r['trap_count']}")

    best_stk = min(stk, key=lambda x: x["brier"])
    cv = time_split_cv(matches)
    print("\n--- Time-split CV (train pre-2026 → test 2026) ---")
    print(f"  Best HP: ob={cv['best_hp']['opener_boost']} db={cv['best_hp']['draw_base']}")
    print(f"  Train Brier={cv['train']['brier']:.4f}  Test 2026={cv['test_2026']['brier']:.4f}")

    shocks = shock_cases(matches)
    print("\n--- Shock cases (draw/upset calibration) ---")
    for s in shocks:
        print(f"  {s['match']}: actual={s['outcome']} pD_v4={s['p_v4_draw']:.1%} "
              f"pD_stk={s['p_stk_draw']:.1%} Brier_v4={s['brier_v4']:.3f}")

    # Best robust: minimize Brier subject to trap_count==0
    candidates = [baseline] + [r for r in stk if r["trap_count"] == 0]
    best_robust = min(candidates, key=lambda x: x["brier"])
    print("\n--- ITERATION 5 VERDICT ---")
    print(f"  Best robust (traps=0): {best_robust['label']} Brier={best_robust['brier']:.4f}")
    print(f"  Production: v4.1 = v4 anchor + DC goals + Rule24 EV + optional 70/30 market stack for MOD tier")

    return {
        "baseline": baseline,
        "hp_top": hp,
        "stacking": stk,
        "cv": cv,
        "shocks": shocks,
        "best_robust": best_robust,
    }


if __name__ == "__main__":
    run_iteration_5()