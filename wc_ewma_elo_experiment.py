#!/usr/bin/env python3
"""
EWMA Elo experiment (Degree-5 temporal surrogate)
=================================================

Compare pre-match 1X2 Brier (v4_1x2) on football-data chronological internationals
(FRIENDLY + WC_QUALIFIER, N≈121) across three Elo regimes:

  1. static_snapshot — fixed ELO dict (wc_model_v3), no temporal updates
  2. walk_forward    — K=20 chronological updates (current elo_a_pre in loader)
  3. ewma            — K=20 raw path + per-team EWMA smooth (alpha=0.08)

Run: python3 wc_ewma_elo_experiment.py
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from wc_backtest_framework import HistoricalMatch, get_all_matches, model_v4_1x2
from wc_backtest_historical_loader import (
    build_football_data_matches,
    fetch_football_data_rows,
    init_elo_state,
    parse_date,
    update_elo,
)
from wc_ensemble_degree2 import brier_score_1x2

EWMA_ALPHA = 0.08
FD_COMPETITIONS = frozenset({"FRIENDLY", "WC_QUALIFIER"})


def static_elo(team: str) -> float:
    """Fixed snapshot; fall back to loader init for unmapped teams."""
    state = init_elo_state()
    return state.get(team, 1500.0)


def apply_ewma_smoothing(
    elo_ewma: Dict[str, float],
    elo_raw: Dict[str, float],
    teams: Tuple[str, str],
    alpha: float = EWMA_ALPHA,
) -> None:
    """In-place EWMA: elo_ewma <- (1-alpha)*elo_ewma + alpha*elo_raw for match teams."""
    for t in teams:
        prev = elo_ewma.get(t, elo_raw.get(t, 1500.0))
        raw = elo_raw.get(t, 1500.0)
        elo_ewma[t] = (1.0 - alpha) * prev + alpha * raw


def build_fd_chronological_matches() -> List[dict]:
    rows = fetch_football_data_rows()
    pending = build_football_data_matches(rows)
    pending.sort(key=lambda x: x["dt"])
    return pending


def assign_elo_regimes(pending: List[dict]) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Walk chronologically; attach pre-match elo for static / walk-forward / EWMA.
    Returns three parallel lists of dicts with keys elo_a, elo_b.
    """
    elo_raw = init_elo_state()
    elo_ewma = dict(elo_raw)

    static_rows: List[dict] = []
    wf_rows: List[dict] = []
    ewma_rows: List[dict] = []

    for p in pending:
        ta, tb = p["team_a"], p["team_b"]

        # Static: snapshot only (no post-match updates)
        sa = static_elo(ta)
        sb = static_elo(tb)
        static_rows.append({**p, "elo_a": sa, "elo_b": sb})

        # Walk-forward pre-match
        wa = elo_raw.get(ta, 1500.0)
        wb = elo_raw.get(tb, 1500.0)
        wf_rows.append({**p, "elo_a": wa, "elo_b": wb})

        # EWMA pre-match (smoothed trajectory)
        ea = elo_ewma.get(ta, elo_raw.get(ta, 1500.0))
        eb = elo_ewma.get(tb, elo_raw.get(tb, 1500.0))
        ewma_rows.append({**p, "elo_a": ea, "elo_b": eb})

        # Post-match K=20 update on raw path
        na, nb = update_elo(wa, wb, p["outcome"], ha=0.0, k=20.0)
        elo_raw[ta], elo_raw[tb] = na, nb
        apply_ewma_smoothing(elo_ewma, elo_raw, (ta, tb), alpha=EWMA_ALPHA)

    return static_rows, wf_rows, ewma_rows


def to_historical(row: dict) -> HistoricalMatch:
    name = f"{row['team_a_name']} vs {row['team_b_name']} ({row['date']})"
    return HistoricalMatch(
        match_id=row["match_id"],
        name=name,
        date=row["date"],
        team_a=row["team_a"],
        team_b=row["team_b"],
        elo_a=row["elo_a"],
        elo_b=row["elo_b"],
        outcome=row["outcome"],
        score=row["score"],
        o_win_a=row["o_win_a"],
        o_draw=row.get("o_draw", 3.3),
        o_win_b=row.get("o_win_b", 3.0),
        total_goals=row["total_goals"],
        competition=row["competition"],
        comp_weight=row["comp_weight"],
        finetune="",
        mu=2.25,
    )


def mean_brier(matches: List[HistoricalMatch]) -> Tuple[float, List[float]]:
    scores = []
    for m in matches:
        probs = model_v4_1x2(m)
        scores.append(brier_score_1x2(probs, m.outcome))
    return float(np.mean(scores)), scores


def mean_logloss(matches: List[HistoricalMatch]) -> float:
    from wc_backtest_framework import log_loss_1x2

    ll = [log_loss_1x2(model_v4_1x2(m), m.outcome) for m in matches]
    return float(np.mean(ll))


def market_brier(matches: List[HistoricalMatch]) -> float:
    bs = []
    for m in matches:
        s = 1 / m.o_win_a + 1 / m.o_draw + 1 / m.o_win_b
        p_mkt = (1 / m.o_win_a / s, 1 / m.o_draw / s, 1 / m.o_win_b / s)
        bs.append(brier_score_1x2(p_mkt, m.outcome))
    return float(np.mean(bs))


def stratified_brier(
    rows: List[dict], regime_key: str = "elo"
) -> Dict[str, float]:
    by_comp: Dict[str, List[float]] = {}
    for row in rows:
        m = to_historical(row)
        bs = brier_score_1x2(model_v4_1x2(m), m.outcome)
        by_comp.setdefault(row["competition"], []).append(bs)
    return {c: float(np.mean(v)) for c, v in by_comp.items()}


def graph_neighbor_regularization_sketch() -> str:
    return """
GRAPH-REGULARIZED ELO (Degree-5 surrogate sketch)
-------------------------------------------------
Teams = nodes V; edges E from recent co-play / confederation / H2H.

Let r_i(t) be EWMA Elo before match t. After each match (i vs j):
  1. Standard K=20 raw update -> r_i', r_j'
  2. EWMA smooth: r_i <- (1-α) r_i + α r_i'  (α=0.08)
  3. Graph Laplacian regularizer (one step):
       r <- r - η L r,  L_ij = -w_ij (i≠j), L_ii = Σ_j w_ij
     Weights w_ij = exp(-Δt/τ) from last meeting; τ≈180 days.
     η ≈ 0.02 pulls neighbors toward similar strength (confederation block).

Objective (offline): min Σ_matches NLL(1X2 | r) + λ Σ_(i,j) w_ij (r_i - r_j)²
  λ≈0.1, solved via iterative EWMA + Laplacian smoothing (not full TGN).

Purpose: dampen isolated friendly spikes; propagate signal along UEFA↔UEFA,
  CONMEBOL↔UEFA test paths without full temporal GNN (N too small for TGN).
"""


def run_experiment() -> Dict:
    pending = build_fd_chronological_matches()
    n = len(pending)
    static_rows, wf_rows, ewma_rows = assign_elo_regimes(pending)

    static_matches = [to_historical(r) for r in static_rows]
    wf_matches = [to_historical(r) for r in wf_rows]
    ewma_matches = [to_historical(r) for r in ewma_rows]

    b_static, _ = mean_brier(static_matches)
    b_wf, _ = mean_brier(wf_matches)
    b_ewma, _ = mean_brier(ewma_matches)
    b_mkt = market_brier(wf_matches)

    # Cross-check walk-forward vs CSV elo_a_pre
    csv_matches = [
        m for m in get_all_matches()
        if m.competition in FD_COMPETITIONS
    ]
    csv_matches.sort(key=lambda m: parse_date(m.date))
    b_csv, _ = mean_brier(csv_matches)

    n_friendly = sum(1 for r in pending if r["competition"] == "FRIENDLY")
    n_wcq = sum(1 for r in pending if r["competition"] == "WC_QUALIFIER")

    ewma_beats_static = b_ewma < b_static
    ewma_beats_wf = b_ewma < b_wf

    return {
        "n_total": n,
        "n_friendly": n_friendly,
        "n_wcq": n_wcq,
        "alpha": EWMA_ALPHA,
        "brier": {
            "static_snapshot": b_static,
            "walk_forward_k20": b_wf,
            "ewma_alpha_008": b_ewma,
            "csv_elo_a_pre": b_csv,
            "market_implied": b_mkt,
        },
        "logloss": {
            "static_snapshot": mean_logloss(static_matches),
            "walk_forward_k20": mean_logloss(wf_matches),
            "ewma_alpha_008": mean_logloss(ewma_matches),
        },
        "stratified_ewma": stratified_brier(ewma_rows),
        "stratified_static": stratified_brier(static_rows),
        "ewma_beats_static": ewma_beats_static,
        "ewma_beats_walk_forward": ewma_beats_wf,
        "delta_ewma_vs_static": b_ewma - b_static,
        "delta_ewma_vs_wf": b_ewma - b_wf,
    }


def print_report(result: Dict) -> None:
    print("=" * 72)
    print("EWMA ELO EXPERIMENT — v4_1x2 multiclass Brier (lower = better)")
    print("=" * 72)
    print(f"N = {result['n_total']} football-data rows "
          f"(FRIENDLY={result['n_friendly']}, WC_QUALIFIER={result['n_wcq']})")
    print(f"EWMA α = {result['alpha']}")
    print()
    print("--- Mean Brier (v4_1x2) ---")
    for name, val in result["brier"].items():
        print(f"  {name:<22} {val:.4f}")
    print()
    print("--- Mean log-loss ---")
    for name, val in result["logloss"].items():
        print(f"  {name:<22} {val:.4f}")
    print()
    print("--- Stratified Brier (EWMA) ---")
    for comp, val in sorted(result["stratified_ewma"].items()):
        print(f"  {comp:<22} {val:.4f}")
    print()
    print("--- Stratified Brier (static snapshot) ---")
    for comp, val in sorted(result["stratified_static"].items()):
        print(f"  {comp:<22} {val:.4f}")
    print()
    d_s = result["delta_ewma_vs_static"]
    d_w = result["delta_ewma_vs_wf"]
    verdict = "YES" if result["ewma_beats_static"] else "NO"
    print(f"EWMA beats static snapshot? {verdict} (Δ = {d_s:+.4f})")
    print(f"EWMA vs walk-forward K=20: Δ = {d_w:+.4f} "
          f"({'EWMA better' if result['ewma_beats_walk_forward'] else 'WF better'})")
    print()
    print(graph_neighbor_regularization_sketch())


if __name__ == "__main__":
    res = run_experiment()
    print_report(res)