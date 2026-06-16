#!/usr/bin/env python3
"""
WCdecider Bayesian Model Search — 6 alternatives × 5 versions × zoom rounds
===========================================================================

Thompson-sampling + expected-improvement style search per architectural degree.
Each degree has 5 seed topologies; 2 zoom rounds sample 6 additional points each
around the posterior top-2 configs (12 zoom evals + 5 seeds = 17 per degree).

Composite objective (maximize):
  score = -weighted_brier
          - 0.15 * trap_count          # hard MOD-trap penalty
          - 0.03 * shock_miss_brier    # draw/upset calibration
          + 0.02 * spec_signal         # preserve longshot EV where justified

Run: python3 wc_bayesian_model_search.py
      python3 wc_bayesian_model_search.py --degree 2
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from wc_backtest_framework import (
    HistoricalMatch,
    get_all_matches,
    model_v4_1x2,
    weighted_mean,
)
from wc_ensemble_degree2 import brier_score_1x2, dixon_coles_1x2
from wc_model_v4_1_ensemble import (
    V41_DEFAULTS,
    market_implied_1x2,
    run_match_v41,
    stack_model_market,
)
from wc_model_v4_ensemble import (
    MatchInputV4,
    TIER_WEIGHTS,
    StakeTier,
    V4_DEFAULTS,
    three_way_1x2_v4,
)
from wc_replicable_pipeline import apply_finetunes, expected_lambdas, two_way_win_prob

RESULTS_PATH = Path(__file__).parent / "wc_bayesian_search_results.json"

SHOCK_KEYS = {
    ("ARG", "KSA"), ("GER", "JPN"), ("ESP", "CPV"),
    ("TUN", "FRA"), ("KOR", "GER"), ("BRA", "SUI"),
}

SPEC_CHECK = ("AUS", "TUR")


# ---------------------------------------------------------------------------
# Eval primitives
# ---------------------------------------------------------------------------

def eval_predictor(
    matches: List[HistoricalMatch],
    predictor: Callable[[HistoricalMatch], Tuple[float, float, float]],
) -> Dict[str, float]:
    briers, weights = [], []
    shock_briers = []
    for m in matches:
        p = predictor(m)
        bs = brier_score_1x2(p, m.outcome)
        briers.append(bs)
        weights.append(m.comp_weight)
        key = (m.team_a, m.team_b)
        if key in SHOCK_KEYS or (m.team_b, m.team_a) in SHOCK_KEYS:
            shock_briers.append(bs)
    return {
        "brier": weighted_mean(briers, weights),
        "shock_brier": float(np.mean(shock_briers)) if shock_briers else 0.0,
        "n": len(matches),
    }


def eval_traps(matches: List[HistoricalMatch], tier_weights: Optional[Dict] = None) -> int:
    traps = 0
    for m in matches:
        if m.o_win_a >= 2.5:
            continue
        spec = MatchInputV4(
            name=m.name, elo_a=m.elo_a, elo_b=m.elo_b,
            home_adv=m.ha, form_a=m.fa, form_b=m.fb,
            mu_total=m.mu, finetune_str=m.finetune,
            o_win_a=m.o_win_a, o_draw=m.o_draw, o_win_b=m.o_win_b,
            pick_outcome="A",
        )
        if tier_weights:
            orig = TIER_WEIGHTS[StakeTier.MODERATE].copy()
            TIER_WEIGHTS[StakeTier.MODERATE].update(tier_weights)
            out = run_match_v41(spec)
            TIER_WEIGHTS[StakeTier.MODERATE] = orig
        else:
            out = run_match_v41(spec)
        if out.ev_rule14 > 1.5 and out.classification not in ("PASS", "HALT"):
            traps += 1
    return traps


def eval_spec_signal(matches: List[HistoricalMatch]) -> float:
    for m in matches:
        if (m.team_a, m.team_b) != SPEC_CHECK:
            continue
        spec = MatchInputV4(
            name=m.name, elo_a=m.elo_a, elo_b=m.elo_b,
            o_win_a=m.o_win_a, o_draw=m.o_draw, o_win_b=m.o_win_b,
            pick_outcome="A",
        )
        out = run_match_v41(spec)
        return max(0.0, out.ev_rule14)
    return 0.0


def composite_score(
    brier: float,
    trap_count: int,
    shock_brier: float,
    spec_signal: float,
) -> float:
    return (
        -brier
        - 0.15 * trap_count
        - 0.03 * shock_brier
        + 0.02 * min(spec_signal, 20.0)
    )


@dataclass
class SearchConfig:
    degree: int
    version: str
    label: str
    params: Dict[str, Any]
    brier: float = 999.0
    trap_count: int = 999
    shock_brier: float = 999.0
    spec_signal: float = 0.0
    score: float = -999.0
    round_id: int = 0


# ---------------------------------------------------------------------------
# Degree-specific predictors (5 seed topologies each)
# ---------------------------------------------------------------------------

def _base_v4_probs(m: HistoricalMatch, params: Dict) -> Tuple[float, float, float]:
    ft = apply_finetunes({"finetune_applied": m.finetune})
    ob = params.get("opener_boost", V4_DEFAULTS["opener_draw_boost"])
    if "rule 21" in m.finetune.lower():
        ft["opener_draw_boost"] = ob
    fa = m.fa + ft["rotation_penalty"]
    p_tw = two_way_win_prob(m.elo_a, m.elo_b, Ha=m.ha, Fa=fa, Fb=m.fb)
    return three_way_1x2_v4(
        p_tw,
        opener_draw_boost=ft["opener_draw_boost"],
        draw_base=params.get("draw_base", V4_DEFAULTS["draw_closeness_base"]),
    )


def predictor_degree1(m: HistoricalMatch, params: Dict) -> Tuple[float, float, float]:
    return _base_v4_probs(m, params)


def predictor_degree2(m: HistoricalMatch, params: Dict) -> Tuple[float, float, float]:
    p_model = _base_v4_probs(m, params)
    mode = params.get("stack_mode", "global")
    w = params.get("stack_weight", 0.7)
    p_mkt = market_implied_1x2(m.o_win_a, m.o_draw, m.o_win_b)
    if mode == "mod_only" and m.o_win_a >= 2.5:
        return p_model
    if params.get("use_dc_1x2", False):
        ft = apply_finetunes({"finetune_applied": m.finetune})
        fa = m.fa + ft["rotation_penalty"]
        la, lb = expected_lambdas(
            m.elo_a, m.elo_b, mu_total=params.get("mu", m.mu),
            Ha=m.ha, Fa=fa, Fb=m.fb,
        )
        p_dc = dixon_coles_1x2(la, lb, rho=params.get("rho", -0.07))
        w_elo = params.get("w_elo", 0.65)
        a = w_elo * p_model[0] + (1 - w_elo) * p_dc[0]
        d = w_elo * p_model[1] + (1 - w_elo) * p_dc[1]
        b = w_elo * p_model[2] + (1 - w_elo) * p_dc[2]
        t = a + d + b
        p_model = (a / t, d / t, b / t)
    return stack_model_market(p_model, p_mkt, w_model=w)


def predictor_degree3(m: HistoricalMatch, params: Dict) -> Tuple[float, float, float]:
    """xG hybrid surrogate: form-based proxy when gap exceeds gate."""
    p_base = _base_v4_probs(m, params)
    gap = abs(m.elo_a - m.elo_b)
    gate = params.get("xg_gate", 400)
    if gap < gate:
        return p_base
    w_xg = params.get("xg_weight", 0.3)
    # Proxy: shift toward underdog when large gap (mimics xG mismatch signal)
    if m.elo_a > m.elo_b:
        p_fav, p_dog = p_base[0], p_base[2]
        shift = w_xg * 0.05
        p_a = max(0.05, p_fav - shift)
        p_b = min(0.95, p_dog + shift)
    else:
        p_a = min(0.95, p_base[0] + w_xg * 0.05)
        p_b = max(0.05, p_base[2] - w_xg * 0.05)
    p_d = p_base[1]
    t = p_a + p_d + p_b
    return p_a / t, p_d / t, p_b / t


def predictor_degree4(m: HistoricalMatch, params: Dict) -> Tuple[float, float, float]:
    """Tier-weighted blend at prediction level (topology probe)."""
    p_model = _base_v4_probs(m, params)
    p_mkt = market_implied_1x2(m.o_win_a, m.o_draw, m.o_win_b)
    implied = 1.0 / m.o_win_a
    if implied < 0.25 or m.o_win_a >= 4.0:
        w = params.get("spec_weights", {"model": 0.30, "sharp": 0.15, "soft": 0.55})
    elif implied > 0.40 or m.o_win_a < 2.5:
        w = params.get("mod_weights", {"model": 0.30, "sharp": 0.50, "soft": 0.20})
    else:
        w = params.get("marg_weights", {"model": 0.40, "sharp": 0.35, "soft": 0.25})
    a = w["model"] * p_model[0] + w["sharp"] * p_mkt[0] + w["soft"] * p_mkt[0]
    d = w["model"] * p_model[1] + w["sharp"] * p_mkt[1] + w["soft"] * p_mkt[1]
    b = w["model"] * p_model[2] + w["sharp"] * p_mkt[2] + w["soft"] * p_mkt[2]
    t = a + d + b
    return a / t, d / t, b / t


def predictor_degree5(m: HistoricalMatch, params: Dict) -> Tuple[float, float, float]:
    """EWMA surrogate: perturb Elo by recency proxy (fa/fb as temporal signal)."""
    alpha = params.get("ewma_alpha", 0.08)
    ft = apply_finetunes({"finetune_applied": m.finetune})
    fa = m.fa + ft["rotation_penalty"]
    # Temporal surrogate: blend static Elo with form-adjusted Elo
    ea = (1 - alpha) * m.elo_a + alpha * (m.elo_a + fa)
    eb = (1 - alpha) * m.elo_b + alpha * (m.elo_b + m.fb)
    if params.get("comp_boost_wc", False) and "WC" in m.competition:
        ea += 15 * alpha
    p_tw = two_way_win_prob(ea, eb, Ha=m.ha, Fa=0, Fb=0)
    ob = params.get("opener_boost", V4_DEFAULTS["opener_draw_boost"])
    if "rule 21" in m.finetune.lower():
        ob = params.get("opener_boost", ob)
    return three_way_1x2_v4(p_tw, opener_draw_boost=ob if "rule 21" in m.finetune.lower() else 0)


def predictor_degree6(m: HistoricalMatch, params: Dict) -> Tuple[float, float, float]:
    """Bayesian draw-band adjusted probabilities for staking topology probe."""
    p = _base_v4_probs(m, params)
    band = params.get("draw_band_pp", 0.03)
    d_up = min(0.35, p[1] + band)
    delta = d_up - p[1]
    scale = max(1e-9, p[0] + p[2])
    p_a = max(0.01, p[0] - delta * (p[0] / scale))
    p_b = max(0.01, p[2] - delta * (p[2] / scale))
    t = p_a + d_up + p_b
    return p_a / t, d_up / t, p_b / t


DEGREE_PREDICTORS = {
    1: predictor_degree1,
    2: predictor_degree2,
    3: predictor_degree3,
    4: predictor_degree4,
    5: predictor_degree5,
    6: predictor_degree6,
}


# ---------------------------------------------------------------------------
# Five seed topologies per degree
# ---------------------------------------------------------------------------

SEED_CONFIGS: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {"label": "D1-v1_prod", "opener_boost": 0.07, "draw_base": 0.20, "mu": 2.25},
        {"label": "D1-v2_wc_tune", "opener_boost": 0.08, "draw_base": 0.20, "mu": 2.20},
        {"label": "D1-v3_draw_heavy", "opener_boost": 0.07, "draw_base": 0.22, "mu": 2.25},
        {"label": "D1-v4_conservative", "opener_boost": 0.06, "draw_base": 0.18, "mu": 2.30},
        {"label": "D1-v5_timesplit", "opener_boost": 0.055, "draw_base": 0.18, "mu": 2.20},
    ],
    2: [
        {"label": "D2-v1_v41_prod", "rho": -0.07, "stack_mode": "mod_only", "stack_weight": 0.70},
        {"label": "D2-v2_global50", "rho": -0.07, "stack_mode": "global", "stack_weight": 0.50},
        {"label": "D2-v3_rho_tight", "rho": -0.10, "stack_mode": "global", "stack_weight": 0.60},
        {"label": "D2-v4_dc_blend", "rho": -0.07, "use_dc_1x2": True, "w_elo": 0.65, "stack_weight": 0.80},
        {"label": "D2-v5_draw_shock", "rho": -0.12, "stack_mode": "global", "stack_weight": 0.55},
    ],
    3: [
        {"label": "D3-v1_gate400_w30", "xg_gate": 400, "xg_weight": 0.30},
        {"label": "D3-v2_gate450_w40", "xg_gate": 450, "xg_weight": 0.40},
        {"label": "D3-v3_gate350_w20", "xg_gate": 350, "xg_weight": 0.20},
        {"label": "D3-v4_no_gate_w50", "xg_gate": 0, "xg_weight": 0.50},
        {"label": "D3-v5_form_only", "xg_gate": 9999, "xg_weight": 0.0},
    ],
    4: [
        {"label": "D4-v1_prod_pin50", "mod_weights": {"model": 0.30, "sharp": 0.50, "soft": 0.20}},
        {"label": "D4-v2_sharp55", "mod_weights": {"model": 0.25, "sharp": 0.55, "soft": 0.20}},
        {"label": "D4-v3_model35", "mod_weights": {"model": 0.35, "sharp": 0.45, "soft": 0.20}},
        {"label": "D4-v4_spec_soft60", "spec_weights": {"model": 0.25, "sharp": 0.15, "soft": 0.60}},
        {"label": "D4-v5_unified40", "mod_weights": {"model": 0.40, "sharp": 0.40, "soft": 0.20},
         "spec_weights": {"model": 0.40, "sharp": 0.40, "soft": 0.20}},
    ],
    5: [
        {"label": "D5-v1_ewma08", "ewma_alpha": 0.08, "comp_boost_wc": False},
        {"label": "D5-v2_slow05", "ewma_alpha": 0.05, "comp_boost_wc": False},
        {"label": "D5-v3_fast12", "ewma_alpha": 0.12, "comp_boost_wc": False},
        {"label": "D5-v4_static_wf", "ewma_alpha": 0.0, "comp_boost_wc": False},
        {"label": "D5-v5_ewma_wc_boost", "ewma_alpha": 0.08, "comp_boost_wc": True},
    ],
    6: [
        {"label": "D6-v1_prod_band03", "draw_band_pp": 0.03, "opener_boost": 0.07},
        {"label": "D6-v2_wide_band05", "draw_band_pp": 0.05, "opener_boost": 0.07},
        {"label": "D6-v3_tight_band02", "draw_band_pp": 0.02, "opener_boost": 0.07},
        {"label": "D6-v4_band04", "draw_band_pp": 0.04, "opener_boost": 0.08},
        {"label": "D6-v5_no_band", "draw_band_pp": 0.0, "opener_boost": 0.07},
    ],
}


PARAM_BOUNDS: Dict[int, Dict[str, Tuple[float, float]]] = {
    1: {"opener_boost": (0.04, 0.10), "draw_base": (0.16, 0.24), "mu": (2.0, 2.5)},
    2: {"rho": (-0.15, -0.03), "stack_weight": (0.45, 0.85), "w_elo": (0.55, 0.85)},
    3: {"xg_gate": (300, 500), "xg_weight": (0.0, 0.55)},
    4: {"mod_sharp": (0.40, 0.60), "mod_model": (0.20, 0.40)},
    5: {"ewma_alpha": (0.0, 0.15)},
    6: {"draw_band_pp": (0.0, 0.06), "opener_boost": (0.05, 0.09)},
}


def evaluate_config(
    degree: int,
    version: str,
    params: Dict,
    matches: List[HistoricalMatch],
    round_id: int = 0,
    tier_weights: Optional[Dict] = None,
) -> SearchConfig:
    pred_fn = DEGREE_PREDICTORS[degree]
    predictor = lambda m, p=params: pred_fn(m, p)
    metrics = eval_predictor(matches, predictor)
    tier_weights = None
    if degree == 4 and "mod_weights" in params:
        tier_weights = params["mod_weights"]
    traps = eval_traps(matches, tier_weights)
    spec_sig = eval_spec_signal(matches)
    score = composite_score(metrics["brier"], traps, metrics["shock_brier"], spec_sig)
    return SearchConfig(
        degree=degree,
        version=version,
        label=params.get("label", version),
        params=params,
        brier=metrics["brier"],
        trap_count=traps,
        shock_brier=metrics["shock_brier"],
        spec_signal=spec_sig,
        score=score,
        round_id=round_id,
    )


# ---------------------------------------------------------------------------
# Bayesian zoom: Thompson sampling on top configs
# ---------------------------------------------------------------------------

def _perturb_params(degree: int, base: Dict, rng: random.Random) -> Dict:
    """Sample neighbor in parameter space (uniform jitter within bounds)."""
    bounds = PARAM_BOUNDS[degree]
    out = dict(base)
    out["label"] = base.get("label", "zoom") + "_z"
    if degree == 1:
        for k in ("opener_boost", "draw_base", "mu"):
            lo, hi = bounds[k]
            out[k] = float(rng.uniform(lo, hi))
    elif degree == 2:
        lo, hi = bounds["rho"]
        out["rho"] = float(rng.uniform(lo, hi))
        lo, hi = bounds["stack_weight"]
        out["stack_weight"] = float(rng.uniform(lo, hi))
        out.setdefault("stack_mode", base.get("stack_mode", "global"))
    elif degree == 3:
        lo, hi = bounds["xg_gate"]
        out["xg_gate"] = float(rng.uniform(lo, hi))
        lo, hi = bounds["xg_weight"]
        out["xg_weight"] = float(rng.uniform(lo, hi))
    elif degree == 4:
        ms = float(rng.uniform(*bounds["mod_sharp"]))
        mm = float(rng.uniform(*bounds["mod_model"]))
        out["mod_weights"] = {"model": mm, "sharp": ms, "soft": round(1 - mm - ms, 2)}
    elif degree == 5:
        lo, hi = bounds["ewma_alpha"]
        out["ewma_alpha"] = float(rng.uniform(lo, hi))
        out["comp_boost_wc"] = base.get("comp_boost_wc", False)
    elif degree == 6:
        lo, hi = bounds["draw_band_pp"]
        out["draw_band_pp"] = float(rng.uniform(lo, hi))
        lo, hi = bounds["opener_boost"]
        out["opener_boost"] = float(rng.uniform(lo, hi))
    return out


def thompson_select(candidates: List[SearchConfig], n_pick: int, rng: random.Random) -> List[Dict]:
    """
    Thompson sampling: treat lower Brier as 'success'; Beta posterior per config family.
    Pick parents proportional to posterior mean, then perturb.
    """
    if not candidates:
        return []
    briers = np.array([c.brier for c in candidates])
    b_min, b_max = briers.min(), briers.max()
    # Success prob: invert normalized Brier
    success_p = 1.0 - (briers - b_min) / max(1e-9, b_max - b_min)
    alphas = 1.0 + success_p * 10
    betas = 1.0 + (1 - success_p) * 10
    draws = [rng.betavariate(a, b) for a, b in zip(alphas, betas)]
    ranked = sorted(zip(draws, candidates), key=lambda x: -x[0])
    parents = [c for _, c in ranked[: min(2, len(ranked))]]
    zooms = []
    for i, p in enumerate(parents):
        for _ in range(n_pick // 2):
            z = _perturb_params(p.degree, p.params, rng)
            z["label"] = f"{p.label}_zoom{i}_{len(zooms)}"
            zooms.append(z)
    return zooms[:n_pick]


def search_degree(
    degree: int,
    matches: List[HistoricalMatch],
    zoom_rounds: int = 2,
    zoom_per_round: int = 6,
    seed: int = 42,
) -> List[SearchConfig]:
    rng = random.Random(seed + degree)
    results: List[SearchConfig] = []

    # Round 0: five seed versions
    for i, params in enumerate(SEED_CONFIGS[degree]):
        cfg = evaluate_config(degree, f"v{i+1}", params, matches, round_id=0)
        results.append(cfg)

    # Zoom rounds: Thompson sample around top-2
    for rnd in range(1, zoom_rounds + 1):
        zoom_params = thompson_select(results, zoom_per_round, rng)
        for j, params in enumerate(zoom_params):
            cfg = evaluate_config(degree, f"zoom_r{rnd}_{j}", params, matches, round_id=rnd)
            results.append(cfg)

    return sorted(results, key=lambda c: -c.score)


def search_all_degrees(
    degrees: Optional[List[int]] = None,
    matches: Optional[List[HistoricalMatch]] = None,
) -> Dict[int, List[SearchConfig]]:
    matches = matches or get_all_matches()
    degrees = degrees or list(range(1, 7))
    all_results = {}
    for d in degrees:
        all_results[d] = search_degree(d, matches)
    return all_results


def print_report(all_results: Dict[int, List[SearchConfig]]) -> None:
    print("=" * 78)
    print("WCdecider BAYESIAN MODEL SEARCH — 6 degrees × 5 seeds × 2 zoom rounds")
    print("=" * 78)
    global_best = None
    for d in sorted(all_results.keys()):
        configs = all_results[d]
        best = configs[0]
        if global_best is None or best.score > global_best.score:
            global_best = best
        print(f"\n--- Degree {d}: {DEGREE_NAMES[d]} ---")
        print(f"  BEST: {best.label}  score={best.score:.4f}  Brier={best.brier:.4f}  "
              f"traps={best.trap_count}  shock={best.shock_brier:.3f}")
        print(f"  params: {json.dumps({k: v for k, v in best.params.items() if k != 'label'}, default=str)}")
        print("  Top 5:")
        for c in configs[:5]:
            print(f"    {c.label:<28} score={c.score:+.4f}  Brier={c.brier:.4f}  traps={c.trap_count}")

    print("\n--- GLOBAL BEST (composite score) ---")
    print(f"  Degree {global_best.degree}: {global_best.label}")
    print(f"  score={global_best.score:.4f}  Brier={global_best.brier:.4f}  traps={global_best.trap_count}")
    print("\n--- CROSS-DEGREE RANKING (best per degree) ---")
    bests = [(d, all_results[d][0]) for d in sorted(all_results.keys())]
    for d, c in sorted(bests, key=lambda x: -x[1].score):
        print(f"  D{d} {c.label:<28} score={c.score:+.4f}  Brier={c.brier:.4f}  traps={c.trap_count}")


DEGREE_NAMES = {
    1: "Variational Elo+Poisson",
    2: "Dixon-Coles + Stacking",
    3: "xG Hybrid (surrogate)",
    4: "Tier Ensemble Topology",
    5: "EWMA Temporal Elo",
    6: "Bayesian Draw-Band Kelly",
}


def save_results(all_results: Dict[int, List[SearchConfig]]) -> None:
    payload = {
        str(d): [asdict(c) for c in configs]
        for d, configs in all_results.items()
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\n[SAVE] {RESULTS_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--degree", type=int, default=0, help="Single degree 1-6, or 0=all")
    args = parser.parse_args()
    matches = get_all_matches()
    if args.degree:
        results = {args.degree: search_degree(args.degree, matches)}
    else:
        results = search_all_degrees(matches=matches)
    print_report(results)
    save_results(results)


if __name__ == "__main__":
    main()