#!/usr/bin/env python3
"""
WCdecider Backtest Framework (v4.1 — Expanded Historical)
==========================================================

Cross-validation across:
  - WC 2018 + 2022 group stages
  - 2023-2026 international friendlies/WCQ (football-data.co.uk, walk-forward Elo)
  - WC 2026 MD1-MD3 settled matches

Metrics: weighted multiclass Brier, log-loss, trap detection, stratified by competition.

Run: python3 wc_backtest_framework.py
      python3 wc_backtest_historical_loader.py  # rebuild CSV first
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from wc_ensemble_degree2 import brier_score_1x2, build_match_probs
from wc_model_v4_ensemble import (
    V4_DEFAULTS,
    MatchInputV4,
    dixon_coles_ou_bt_ts,
    three_way_1x2_v4,
)
from wc_model_v4_1_ensemble import (
    V41_DEFAULTS,
    market_implied_1x2,
    run_match_v41,
    stack_model_market,
)
from wc_replicable_pipeline import (
    apply_finetunes,
    compute_ou_bt_ts,
    expected_lambdas,
    three_way_1x2,
    two_way_win_prob,
)

CSV_PATH = Path(__file__).parent / "wc_backtest_historical_dataset.csv"


@dataclass
class HistoricalMatch:
    """Settled match for backtest."""
    name: str
    team_a: str
    team_b: str
    elo_a: float
    elo_b: float
    outcome: str  # A, D, B
    score: str
    o_win_a: float
    o_draw: Optional[float] = None
    o_win_b: Optional[float] = None
    o_soft_win_a: Optional[float] = None
    ha: float = 0.0
    fa: float = 0.0
    fb: float = 0.0
    mu: float = 2.25
    finetune: str = ""
    md: int = 0
    total_goals: Optional[int] = None
    competition: str = "WC_2026_GROUP"
    comp_weight: float = 1.0
    date: str = ""
    match_id: str = ""


# Legacy 9-match WC 2026 set (kept for regression)
HISTORICAL_MATCHES: List[HistoricalMatch] = []


def _load_from_csv() -> List[HistoricalMatch]:
    if not CSV_PATH.exists():
        from wc_backtest_historical_loader import build_full_dataset, save_csv
        save_csv(build_full_dataset(), CSV_PATH)

    matches = []
    with open(CSV_PATH, newline="") as f:
        for row in csv.DictReader(f):
            name = f"{row['team_a_name']} vs {row['team_b_name']} ({row['date']})"
            matches.append(HistoricalMatch(
                match_id=row.get("match_id", ""),
                name=name,
                date=row["date"],
                team_a=row["team_a"],
                team_b=row["team_b"],
                elo_a=float(row["elo_a_pre"]),
                elo_b=float(row["elo_b_pre"]),
                outcome=row["outcome"],
                score=row["score"],
                o_win_a=float(row["o_win_a"]),
                o_draw=float(row["o_draw"]) if row.get("o_draw") else 3.5,
                o_win_b=float(row["o_win_b"]) if row.get("o_win_b") else 4.0,
                total_goals=int(row["total_goals"]),
                competition=row.get("competition", "FRIENDLY"),
                comp_weight=float(row.get("comp_weight", 0.6)),
                finetune=row.get("finetune", ""),
                mu=float(row.get("mu", 2.25)),
            ))
    return matches


def get_all_matches(rebuild: bool = False) -> List[HistoricalMatch]:
    global HISTORICAL_MATCHES
    if rebuild or not CSV_PATH.exists():
        from wc_backtest_historical_loader import build_full_dataset, save_csv
        save_csv(build_full_dataset(), CSV_PATH)
    HISTORICAL_MATCHES = _load_from_csv()
    return HISTORICAL_MATCHES


def log_loss_1x2(probs: Tuple[float, float, float], outcome: str, eps: float = 1e-15) -> float:
    idx = {"A": 0, "D": 1, "B": 2}[outcome]
    return -math.log(max(eps, probs[idx]))


def model_v31_1x2(m: HistoricalMatch) -> Tuple[float, float, float]:
    ft = apply_finetunes({"finetune_applied": m.finetune})
    fa = m.fa + ft["rotation_penalty"]
    p_tw = two_way_win_prob(m.elo_a, m.elo_b, Ha=m.ha, Fa=fa, Fb=m.fb)
    return three_way_1x2(p_tw, opener_draw_boost=ft["opener_draw_boost"])


def model_v4_1x2(m: HistoricalMatch) -> Tuple[float, float, float]:
    ft = apply_finetunes({"finetune_applied": m.finetune})
    if "rule 21" in m.finetune.lower():
        ft["opener_draw_boost"] = V4_DEFAULTS["opener_draw_boost"]
    fa = m.fa + ft["rotation_penalty"]
    p_tw = two_way_win_prob(m.elo_a, m.elo_b, Ha=m.ha, Fa=fa, Fb=m.fb)
    return three_way_1x2_v4(p_tw, opener_draw_boost=ft["opener_draw_boost"])


def model_v4_1_stack_1x2(m: HistoricalMatch) -> Tuple[float, float, float]:
    """v4.1 research leg: 70/30 model+market stack (Iteration 5 best robust)."""
    p_model = model_v4_1x2(m)
    p_mkt = market_implied_1x2(m.o_win_a, m.o_draw, m.o_win_b)
    return stack_model_market(
        p_model, p_mkt, w_model=V41_DEFAULTS["mod_model_market_stack"]
    )


def brier_binary(p: float, event: bool) -> float:
    return (p - (1.0 if event else 0.0)) ** 2


def ou_outcome(total_goals: int, threshold: float = 2.5) -> bool:
    return total_goals > threshold


def weighted_mean(values: List[float], weights: List[float]) -> float:
    if not values:
        return float("nan")
    w = np.array(weights)
    v = np.array(values)
    return float(np.average(v, weights=w))


def evaluate_all_models(matches: Optional[List[HistoricalMatch]] = None) -> Tuple[Dict, Dict, Dict]:
    """Aggregate metrics with competition weights."""
    matches = matches or get_all_matches()
    models = ["v31_elo", "v4_elo", "v4_1_stack", "dc_ensemble_35", "market_implied"]
    agg: Dict[str, Dict[str, List[float]]] = {
        m: {"brier": [], "logloss": [], "weights": []} for m in models
    }
    ou_agg: Dict[str, List[float]] = {"dc_ou": [], "indep_ou": [], "weights": []}
    by_comp: Dict[str, Dict[str, List[float]]] = {}

    for m in matches:
        w = m.comp_weight
        p_v31 = model_v31_1x2(m)
        p_v4 = model_v4_1x2(m)
        p_v41 = model_v4_1_stack_1x2(m)

        for model_name, probs in [
            ("v31_elo", p_v31),
            ("v4_elo", p_v4),
            ("v4_1_stack", p_v41),
        ]:
            bs = brier_score_1x2(probs, m.outcome)
            ll = log_loss_1x2(probs, m.outcome)
            agg[model_name]["brier"].append(bs)
            agg[model_name]["logloss"].append(ll)
            agg[model_name]["weights"].append(w)
            by_comp.setdefault(m.competition, {}).setdefault(model_name, []).append(bs)

        # Market implied (devigged closing odds baseline)
        s = 1 / m.o_win_a + 1 / m.o_draw + 1 / m.o_win_b
        p_mkt = (1 / m.o_win_a / s, 1 / m.o_draw / s, 1 / m.o_win_b / s)
        agg["market_implied"]["brier"].append(brier_score_1x2(p_mkt, m.outcome))
        agg["market_implied"]["logloss"].append(log_loss_1x2(p_mkt, m.outcome))
        agg["market_implied"]["weights"].append(w)

        from wc_ensemble_degree2 import BacktestMatch
        bm = BacktestMatch(
            name=m.name, team_a=m.team_a, team_b=m.team_b,
            elo_a=m.elo_a, elo_b=m.elo_b, ha=m.ha, fa=m.fa, fb=m.fb,
            mu=m.mu, outcome=m.outcome, o_win_a=m.o_win_a,
            o_draw=m.o_draw, o_win_b=m.o_win_b,
            opener_draw_boost=0.07 if "rule 21" in m.finetune.lower() else 0.0,
            minnow_resilience_mult=1.16 if m.team_a == "ESP" else 1.0,
            rotation_penalty=-25.0 if m.team_a == "ESP" else 0.0,
        )
        p_dc = build_match_probs(bm)["ensemble_35_35_30"]
        agg["dc_ensemble_35"]["brier"].append(brier_score_1x2(p_dc, m.outcome))
        agg["dc_ensemble_35"]["logloss"].append(log_loss_1x2(p_dc, m.outcome))
        agg["dc_ensemble_35"]["weights"].append(w)

        if m.total_goals is not None:
            ft = apply_finetunes({"finetune_applied": m.finetune})
            fa = m.fa + ft["rotation_penalty"]
            la, lb = expected_lambdas(
                m.elo_a, m.elo_b, mu_total=m.mu, Ha=m.ha, Fa=fa, Fb=m.fb,
                minnow_resilience_mult=ft["minnow_resilience_mult"],
            )
            ou_dc = dixon_coles_ou_bt_ts(la, lb)
            ou_ind = compute_ou_bt_ts(la, lb)
            over = ou_outcome(m.total_goals)
            ou_agg["dc_ou"].append(brier_binary(ou_dc["p_over_25"], over))
            ou_agg["indep_ou"].append(brier_binary(ou_ind["p_over_25"], over))
            ou_agg["weights"].append(w)

    results = {}
    for model, metrics in agg.items():
        results[model] = {
            "mean_brier": weighted_mean(metrics["brier"], metrics["weights"]),
            "mean_logloss": weighted_mean(metrics["logloss"], metrics["weights"]),
            "n": len(metrics["brier"]),
        }

    ou_results = {
        "ou_dc_mean_brier": weighted_mean(ou_agg["dc_ou"], ou_agg["weights"]),
        "ou_indep_mean_brier": weighted_mean(ou_agg["indep_ou"], ou_agg["weights"]),
        "n_ou": len(ou_agg["dc_ou"]),
    }
    return results, ou_results, by_comp


def trap_analysis(matches: Optional[List[HistoricalMatch]] = None) -> List[Dict]:
    matches = matches or get_all_matches()
    rows = []
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
        out = run_match_v41(spec)
        rows.append({
            "match": m.name[:40],
            "comp": m.competition,
            "odds": m.o_win_a,
            "ev_r14": out.ev_rule14,
            "class": out.classification,
            "fav_won": m.outcome == "A",
            "would_bet_v41": out.ev_rule14 > 1.5 and out.classification not in ("PASS", "HALT"),
        })
    return rows


def hyperparameter_sweep(matches: Optional[List[HistoricalMatch]] = None) -> Dict:
    matches = matches or get_all_matches()
    boost_grid = [0.055, 0.06, 0.07, 0.08]
    mu_grid = [2.2, 2.25, 2.3, 2.4]
    best = {"brier": 999.0}
    for boost in boost_grid:
        for mu in mu_grid:
            bs, ws = [], []
            for m in matches:
                ft = apply_finetunes({"finetune_applied": m.finetune})
                fa = m.fa + ft["rotation_penalty"]
                p_tw = two_way_win_prob(m.elo_a, m.elo_b, Ha=m.ha, Fa=fa, Fb=m.fb)
                ob = boost if "rule 21" in m.finetune.lower() else 0.0
                p = three_way_1x2_v4(p_tw, opener_draw_boost=ob)
                bs.append(brier_score_1x2(p, m.outcome))
                ws.append(m.comp_weight)
            mean_bs = weighted_mean(bs, ws)
            if mean_bs < best["brier"]:
                best = {"brier": mean_bs, "opener_boost": boost, "mu": mu}
    return best


def run_full_backtest_report(rebuild: bool = False) -> Dict:
    matches = get_all_matches(rebuild=rebuild)
    print("=" * 78)
    print(f"WCdecider v4.1 EXPANDED BACKTEST — N={len(matches)} matches")
    print("Sources: WC 2018/2022 + football-data intl 2023-2026 + WC26 MD1-3")
    print("=" * 78)

    from collections import Counter
    comps = Counter(m.competition for m in matches)
    print("\n--- Dataset composition ---")
    for comp, n in comps.most_common():
        print(f"  {comp:<22} {n:>4}")

    results, ou_results, by_comp = evaluate_all_models(matches)
    print("\n--- Model Comparison (weighted mean Brier, lower=better) ---")
    brier_rank = sorted(
        [(k, v["mean_brier"]) for k, v in results.items()],
        key=lambda x: x[1],
    )
    for name, bs in brier_rank:
        n = results[name]["n"]
        print(f"  {name:<22} Brier={bs:.4f}  logloss={results[name]['mean_logloss']:.4f}  N={n}")

    print("\n--- Stratified Brier (v4_elo by competition) ---")
    for comp in sorted(by_comp.keys()):
        bs_list = by_comp[comp].get("v4_elo", [])
        if bs_list:
            print(f"  {comp:<22} mean={float(np.mean(bs_list)):.4f}  N={len(bs_list)}")

    print(f"\n--- O/U 2.5 weighted Brier (N={ou_results['n_ou']}) ---")
    print(f"  Dixon-Coles:         {ou_results['ou_dc_mean_brier']:.4f}")
    print(f"  Independent Poisson: {ou_results['ou_indep_mean_brier']:.4f}")

    traps = trap_analysis(matches)
    mod_bets = [t for t in traps if t["would_bet_v41"]]
    print(f"\n--- Trap Analysis (MOD favorites odds<2.5, N={len(traps)}) ---")
    print(f"  v4.1 would-bet count: {len(mod_bets)} / {len(traps)}")
    for t in traps[:8]:
        print(f"  {t['match']:<40} @{t['odds']:.2f} ev={t['ev_r14']:+.1f}% {t['class']} ({t['comp']})")
    if len(traps) > 8:
        print(f"  ... +{len(traps)-8} more")

    best = hyperparameter_sweep(matches)
    print("\n--- Hyperparameter sweep (weighted Brier, full dataset) ---")
    print(f"  Best: opener_boost={best.get('opener_boost')} mu={best.get('mu')} Brier={best['brier']:.4f}")

    winner = brier_rank[0][0]
    print("\n--- EXPANDED BACKTEST VERDICT ---")
    print(f"  1X2 winner: {winner} (Brier {brier_rank[0][1]:.4f})")
    mkt_brier = results.get("market_implied", {}).get("mean_brier", float("nan"))
    v4_brier = results.get("v4_elo", {}).get("mean_brier", float("nan"))
    if not math.isnan(mkt_brier) and not math.isnan(v4_brier):
        print(f"  v4 vs market implied: {v4_brier:.4f} vs {mkt_brier:.4f} (Δ={v4_brier-mkt_brier:+.4f})")
    v41_brier = results.get("v4_1_stack", {}).get("mean_brier", float("nan"))
    if not math.isnan(v41_brier) and not math.isnan(v4_brier):
        print(f"  v4.1 stack vs v4 anchor: {v41_brier:.4f} vs {v4_brier:.4f} (Δ={v41_brier-v4_brier:+.4f})")
    print(f"  Production: wc_model_v4_1_ensemble.py")

    return {
        "n": len(matches), "results": results, "ou_results": ou_results,
        "by_comp": by_comp, "traps": traps, "best_hp": best, "winner": winner,
    }


if __name__ == "__main__":
    run_full_backtest_report(rebuild=True)