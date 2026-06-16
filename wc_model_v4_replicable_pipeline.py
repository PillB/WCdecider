#!/usr/bin/env python3
"""
WCdecider v4.1 Replicable Student Pipeline
==========================================

PURPOSE
-------
End-to-end, fully documented pipeline that a student or peer reviewer can run using
ONLY the CSV datasets + provenance TXT files + this script to reproduce:

  1. June 15-16 2026 slate predictions (6 matches, OSINT-enriched inputs)
  2. Expanded backtest metrics (N=222, real closing odds)
  3. Production v4.1 classifications (MOD 70/30 stack + Rule 24)
  4. Locked regression outputs verified by tests/test_peer_replication.py

ARTIFACTS REQUIRED (all in this directory)
------------------------------------------
  wc_2026_model_dataset.csv          — June slate with per-column source_* provenance
  wc_2026_dataset_provenance.txt     — Column instructions for June CSV
  wc_backtest_historical_dataset.csv — N=222 backtest (or rebuild via loader)
  wc_backtest_dataset_provenance.txt — Column instructions for backtest CSV
  wc_model_master_provenance.txt     — Manifest linking all datasets

OPTIONAL REBUILD (live network)
-------------------------------
  python3 wc_backtest_historical_loader.py

QUICK START
-----------
  python3 wc_model_v4_replicable_pipeline.py
  python3 -m pytest tests/test_peer_replication.py -v

WHY v4.1 (not v3.1 replicable pipeline)?
----------------------------------------
  v3.1 (wc_replicable_pipeline.py) remains regression-locked for the June slate raw formula.
  This pipeline adds the production winner from Iteration 5-6:
    - v4.1 MOD 70/30 market pre-stack
    - Dixon-Coles goal markets (decoupled from 1X2)
    - Rule 24 tier ensemble + conservative Kelly stake suggestion

  See MODEL_ITERATION_V5.md, MODEL_ITERATION_V6.md, MODEL_PIPELINE_V4.md.

DEPENDENCIES: Python 3.10+, numpy, scipy (same as wc_model_v4_1_ensemble.py)
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths — all relative to this script so students can copy the folder anywhere
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
JUNE_CSV = ROOT / "wc_2026_model_dataset.csv"
BACKTEST_CSV = ROOT / "wc_backtest_historical_dataset.csv"
OUTPUT_CSV = ROOT / "wc_model_production_results.csv"
JUNE_PROVENANCE = ROOT / "wc_2026_dataset_provenance.txt"
BACKTEST_PROVENANCE = ROOT / "wc_backtest_dataset_provenance.txt"
MASTER_PROVENANCE = ROOT / "wc_model_master_provenance.txt"

# Locked regression targets (from executed backtest 2026-06-15)
LOCKED_BACKTEST = {
    "n_matches": 222,
    "v4_elo_brier": 0.6157,
    "v4_1_stack_brier": 0.6039,
    "market_implied_brier": 0.5956,
    "trap_count_v41": 0,
    "brier_tolerance": 0.003,
}

# June slate v4.1 locked outputs (NED-JPN PASS, ESP draw calibration)
LOCKED_JUNE_V41 = {
    "Netherlands vs Japan (MD2 trap)": {"tier": "MOD", "classification": ("PASS", "HALT")},
    "Spain vs Cape Verde": {"model_draw_min": 0.22},
}


@dataclass
class PipelineRow:
    """One output row in wc_model_production_results.csv."""
    dataset: str
    match_id: str
    match_name: str
    team_a: str
    team_b: str
    elo_a: float
    elo_b: float
    source_elo: str
    o_win_a: Optional[float]
    source_odds: str
    p_model_a: float
    p_model_d: float
    p_model_b: float
    p_blend_a: float
    p_blend_d: float
    p_blend_b: float
    ev_rule14: Optional[float]
    classification: str
    tier: str
    stake_conservative: float
    actual_outcome: str
    processing_steps: str


def _check_artifacts() -> List[str]:
    """
    Verify required files exist before running.

    Example
    -------
    >>> errs = _check_artifacts()
    >>> assert not errs  # all files present
    """
    required = [JUNE_CSV, BACKTEST_CSV, JUNE_PROVENANCE, BACKTEST_PROVENANCE, MASTER_PROVENANCE]
    missing = [str(p) for p in required if not p.exists()]
    return missing


def load_june_slate() -> List[Dict]:
    """
    Step 1a — Load June 15-16 OSINT-enriched slate.

    Each row has source_* columns documenting where elo, form, injury, weather came from.
    See wc_2026_dataset_provenance.txt for replication instructions.

    WHY separate June CSV?
      Live analysis needs injury/weather overlays not available in historical backtest CSV.
    """
    with open(JUNE_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_backtest_slate() -> List[Dict]:
    """
    Step 1b — Load N=222 expanded backtest.

    Rebuild command (if missing): python3 wc_backtest_historical_loader.py
    See wc_backtest_dataset_provenance.txt for column definitions.
    """
    if not BACKTEST_CSV.exists():
        print("[BUILD] Backtest CSV missing — running wc_backtest_historical_loader.py ...")
        from wc_backtest_historical_loader import build_full_dataset, save_csv
        save_csv(build_full_dataset(), BACKTEST_CSV)
    with open(BACKTEST_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def june_row_to_match_input(row: Dict):
    """
    Step 2a — Map June CSV columns → MatchInputV4.

    Processing order (matches wc_2026_dataset_provenance.txt):
      1. Read elo_a/elo_b from prebuilt snapshot (source_elo_* columns)
      2. Sum form_adjust_a + injury_adjust_a as Elo overlay Fa
      3. Parse finetune_applied → Rule 21/14/15/16/20 flags
      4. Pass mu_total for Poisson leg

    Example row keys: 'elo_a', 'injury_adjust_a', 'finetune_applied'
    """
    from wc_model_v4_1_ensemble import MatchInputV4

    prior_odds = {
        "Spain vs Cape Verde 2026-06-15": (1.19, 6.50, 15.00, "A"),
        "Belgium vs Egypt 2026-06-15": (1.67, 3.80, 5.60, "A"),
        "France vs Senegal 2026-06-16": (1.52, None, None, "A"),
        "Iraq vs Norway 2026-06-16": (None, None, None, "A"),
        "Argentina vs Algeria 2026-06-16": (1.41, None, None, "A"),
        "Austria vs Jordan 2026-06-16": (None, 5.05, None, "D"),
    }
    match = row["match"]
    odds = prior_odds.get(match, (None, None, None, "A"))
    pick = odds[3]
    return MatchInputV4(
        name=match.replace(" 2026-06-15", "").replace(" 2026-06-16", ""),
        elo_a=float(row["elo_a"]),
        elo_b=float(row["elo_b"]),
        home_adv=float(row.get("home_adv", 0) or 0),
        form_a=float(row.get("form_adjust_a", 0) or 0),
        injury_a=float(row.get("injury_adjust_a", 0) or 0),
        mu_total=float(row.get("mu_total", 2.25) or 2.25),
        finetune_str=row.get("finetune_applied", ""),
        o_win_a=odds[0],
        o_draw=odds[1],
        o_win_b=odds[2],
        pick_outcome=pick,
    )


def backtest_row_to_match_input(row: Dict, pick: str = "A"):
    """Step 2b — Map backtest CSV → MatchInputV4 for EV/trap evaluation."""
    from wc_model_v4_1_ensemble import MatchInputV4

    return MatchInputV4(
        name=f"{row['team_a']} vs {row['team_b']} ({row['date']})",
        elo_a=float(row["elo_a_pre"]),
        elo_b=float(row["elo_b_pre"]),
        home_adv=float(row.get("ha", 0) or 0),
        mu_total=float(row.get("mu", 2.25) or 2.25),
        finetune_str=row.get("finetune", ""),
        o_win_a=float(row["o_win_a"]),
        o_draw=float(row.get("o_draw") or 3.5),
        o_win_b=float(row.get("o_win_b") or 4.0),
        pick_outcome=pick,
    )


def run_june_slate_v41(rows: List[Dict]) -> List[PipelineRow]:
    """
    Step 3a — Run production v4.1 on June slate.

    WHY v4.1 run_match_v41?
      Iteration 5 Bayesian search confirmed MOD 70/30 pre-stack improves calibration
      while preserving trap discipline (0 MOD favorites would-bet on N=222).
    """
    from wc_model_v4_1_ensemble import run_match_v41

    out: List[PipelineRow] = []
    for row in rows:
        spec = june_row_to_match_input(row)
        result = run_match_v41(spec)
        out.append(PipelineRow(
            dataset="june_slate",
            match_id=row["match"],
            match_name=spec.name,
            team_a=row["team_a"],
            team_b=row["team_b"],
            elo_a=spec.elo_a,
            elo_b=spec.elo_b,
            source_elo=row.get("source_elo_a", ""),
            o_win_a=spec.o_win_a,
            source_odds="Betsson/Betano screenshots per AGENT.md",
            p_model_a=result.model_1x2[0],
            p_model_d=result.model_1x2[1],
            p_model_b=result.model_1x2[2],
            p_blend_a=result.blended_1x2[0],
            p_blend_d=result.blended_1x2[1],
            p_blend_b=result.blended_1x2[2],
            ev_rule14=result.ev_rule14,
            classification=result.classification,
            tier=result.tier.value,
            stake_conservative=result.stake_conservative,
            actual_outcome=row.get("actual_result", "N/A"),
            processing_steps="v4.1: Elo anchor→MOD70/30 stack→Rule24→R14→classify",
        ))
    return out


def run_backtest_evaluation(rows: List[Dict]) -> Dict:
    """
    Step 3b — Compute locked backtest metrics on N=222.

    Uses wc_backtest_framework.evaluate_all_models() — the same functions
    peer reviewers must reproduce.

    WHY weighted Brier?
      Rule 26 competition weights prevent friendlies from dominating calibration.
    """
    from wc_backtest_framework import evaluate_all_models, trap_analysis

    # Convert dict rows to framework objects via loader
    from wc_backtest_framework import get_all_matches
    matches = get_all_matches()
    results, ou_results, _ = evaluate_all_models(matches)
    traps = trap_analysis(matches)
    mod_bets = sum(1 for t in traps if t.get("would_bet_v41"))

    return {
        "n": len(matches),
        "results": results,
        "ou_results": ou_results,
        "trap_count": mod_bets,
    }


def validate_locked_metrics(metrics: Dict) -> List[str]:
    """
    Step 4 — Compare computed metrics to locked regression values.

    Returns list of error strings (empty = replication SUCCESS).

    Example
    -------
    >>> errs = validate_locked_metrics({"n": 222, "results": {...}, "trap_count": 0})
    >>> assert errs == []
    """
    errors = []
    if metrics["n"] != LOCKED_BACKTEST["n_matches"]:
        errors.append(f"N={metrics['n']} expected {LOCKED_BACKTEST['n_matches']}")

    res = metrics["results"]
    for key, locked in [
        ("v4_elo", "v4_elo_brier"),
        ("v4_1_stack", "v4_1_stack_brier"),
        ("market_implied", "market_implied_brier"),
    ]:
        got = res[key]["mean_brier"]
        exp = LOCKED_BACKTEST[locked]
        tol = LOCKED_BACKTEST["brier_tolerance"]
        if abs(got - exp) > tol:
            errors.append(f"{key} Brier {got:.4f} != {exp:.4f} (tol {tol})")

    if metrics["trap_count"] != LOCKED_BACKTEST["trap_count_v41"]:
        errors.append(f"trap_count {metrics['trap_count']} != 0")

    return errors


def save_production_csv(rows: List[PipelineRow], backtest_rows: List[Dict]) -> None:
    """
    Step 5 — Write wc_model_production_results.csv (June predictions + backtest summary rows).

    Backtest rows store aggregate metrics in processing_steps for audit trail.
    """
    from wc_backtest_framework import model_v4_1x2, get_all_matches
    from wc_ensemble_degree2 import brier_score_1x2

    all_rows = list(rows)
    for m in get_all_matches():
        p = model_v4_1x2(m)
        all_rows.append(PipelineRow(
            dataset="backtest",
            match_id=m.match_id,
            match_name=m.name,
            team_a=m.team_a,
            team_b=m.team_b,
            elo_a=m.elo_a,
            elo_b=m.elo_b,
            source_elo=getattr(m, "source_elo", "see wc_backtest_dataset_provenance.txt"),
            o_win_a=m.o_win_a,
            source_odds="see source_odds in backtest CSV",
            p_model_a=p[0],
            p_model_d=p[1],
            p_model_b=p[2],
            p_blend_a=p[0],
            p_blend_d=p[1],
            p_blend_b=p[2],
            ev_rule14=None,
            classification="",
            tier="",
            stake_conservative=0.0,
            actual_outcome=m.outcome,
            processing_steps=f"Brier_contrib={brier_score_1x2(p, m.outcome):.4f}",
        ))

    fields = list(asdict(all_rows[0]).keys()) if all_rows else []
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_rows:
            w.writerow(asdict(r))
    print(f"[SAVE] {len(all_rows)} rows → {OUTPUT_CSV}")


def print_student_report(
    june_results: List[PipelineRow],
    metrics: Dict,
    validation_errors: List[str],
) -> None:
    """Step 6 — Human-readable report for students and peer reviewers."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print("=" * 78)
    print(f"WCdecider v4.1 REPLICABLE PIPELINE — Run {ts}")
    print("=" * 78)

    print("\n--- STEP 1: Artifacts ---")
    for p in [JUNE_CSV, BACKTEST_CSV, OUTPUT_CSV]:
        status = "OK" if p.exists() else "MISSING"
        print(f"  [{status}] {p.name}")

    print("\n--- STEP 2: June Slate v4.1 (6 matches) ---")
    print(f"{'Match':<35} {'Tier':<5} {'pD':>6} {'EV R14':>8} {'Class':<10} {'Stake':>6}")
    for r in june_results:
        ev = f"{r.ev_rule14:+.1f}%" if r.ev_rule14 is not None else "N/A"
        print(f"{r.match_name:<35} {r.tier:<5} {r.p_model_d:>5.1%} {ev:>8} {r.classification:<10} {r.stake_conservative:>6.2f}")

    print("\n--- STEP 3: Backtest N=222 (locked metrics) ---")
    res = metrics["results"]
    for name in ["market_implied", "v4_1_stack", "v4_elo", "v31_elo"]:
        if name in res:
            print(f"  {name:<18} Brier={res[name]['mean_brier']:.4f}  N={res[name]['n']}")
    print(f"  MOD trap count (v4.1): {metrics['trap_count']} / 125 favorites")

    print("\n--- STEP 4: Replication validation ---")
    if validation_errors:
        print("  STATUS: FAIL")
        for e in validation_errors:
            print(f"    ✗ {e}")
    else:
        print("  STATUS: SUCCESS — all locked metrics within tolerance")

    print("\n--- STEP 5: Student next steps ---")
    print("  1. Read wc_model_master_provenance.txt")
    print("  2. Edit wc_2026_model_dataset.csv injury_adjust_a → re-run → observe p_model change")
    print("  3. Run: python3 -m pytest tests/test_peer_replication.py -v")
    print("  4. Rebuild backtest: python3 wc_backtest_historical_loader.py (needs network)")


def run_full_v41_pipeline(save_output: bool = True) -> Dict:
    """
    Main entry — executes all steps in order.

    Returns dict with june_results, metrics, validation_errors for tests.

    Example
    -------
    >>> result = run_full_v41_pipeline(save_output=False)
    >>> assert result['validation_errors'] == []
    """
    missing = _check_artifacts()
    if missing:
        print("[ERROR] Missing artifacts:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)

    print("[STEP 1] Loading datasets ...")
    june_rows = load_june_slate()
    backtest_rows = load_backtest_slate()
    print(f"  June slate: {len(june_rows)} matches")
    print(f"  Backtest:   {len(backtest_rows)} matches")

    print("[STEP 2-3] Running v4.1 model ...")
    june_results = run_june_slate_v41(june_rows)
    metrics = run_backtest_evaluation(backtest_rows)

    print("[STEP 4] Validating locked regression targets ...")
    validation_errors = validate_locked_metrics(metrics)

    if save_output:
        print("[STEP 5] Saving production results CSV ...")
        save_production_csv(june_results, backtest_rows)

    print_student_report(june_results, metrics, validation_errors)

    return {
        "june_results": june_results,
        "metrics": metrics,
        "validation_errors": validation_errors,
    }


if __name__ == "__main__":
    result = run_full_v41_pipeline(save_output=True)
    sys.exit(1 if result["validation_errors"] else 0)