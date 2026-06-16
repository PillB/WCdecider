#!/usr/bin/env python3
"""
Peer replication tests — verify CSV + TXT + pipeline reproduce locked outputs.

A student or subagent should pass these tests using ONLY:
  - wc_2026_model_dataset.csv
  - wc_backtest_historical_dataset.csv
  - wc_*_provenance.txt files
  - wc_model_v4_replicable_pipeline.py
  - wc_model_v4_1_ensemble.py (+ dependencies)

Run: python3 -m pytest tests/test_peer_replication.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from wc_model_v4_replicable_pipeline import (
    BACKTEST_CSV,
    JUNE_CSV,
    LOCKED_BACKTEST,
    MASTER_PROVENANCE,
    OUTPUT_CSV,
    run_full_v41_pipeline,
    load_june_slate,
    load_backtest_slate,
    june_row_to_match_input,
    _check_artifacts,
)
from wc_replicable_pipeline import run_full_pipeline


def test_all_artifacts_present():
    missing = _check_artifacts()
    assert not missing, f"Missing: {missing}"


def test_june_csv_has_provenance_columns():
    rows = load_june_slate()
    assert len(rows) == 6
    required = ["source_elo_a", "source_injury_a", "finetune_applied", "processing_notes"]
    for col in required:
        assert col in rows[0], f"Missing column {col}"


def test_backtest_csv_row_count():
    rows = load_backtest_slate()
    assert len(rows) == LOCKED_BACKTEST["n_matches"]


def test_backtest_csv_has_source_columns():
    rows = load_backtest_slate()
    for col in ["source_result", "source_odds", "source_elo"]:
        assert col in rows[0], f"Missing {col}"


def test_v41_pipeline_replication_success():
    result = run_full_v41_pipeline(save_output=False)
    assert result["validation_errors"] == [], result["validation_errors"]


def test_locked_brier_values():
    result = run_full_v41_pipeline(save_output=False)
    res = result["metrics"]["results"]
    tol = LOCKED_BACKTEST["brier_tolerance"]
    assert abs(res["v4_elo"]["mean_brier"] - LOCKED_BACKTEST["v4_elo_brier"]) <= tol
    assert abs(res["v4_1_stack"]["mean_brier"] - LOCKED_BACKTEST["v4_1_stack_brier"]) <= tol
    assert abs(res["market_implied"]["mean_brier"] - LOCKED_BACKTEST["market_implied_brier"]) <= tol


def test_trap_discipline():
    result = run_full_v41_pipeline(save_output=False)
    assert result["metrics"]["trap_count"] == 0


def test_ned_jpn_pass_classification():
    from wc_model_v4_1_ensemble import run_match_v41
    from wc_backtest_framework import get_all_matches

    m = next(x for x in get_all_matches() if x.team_a == "NED" and x.team_b == "JPN")
    from wc_model_v4_replicable_pipeline import backtest_row_to_match_input
    import csv
    with open(BACKTEST_CSV) as f:
        row = next(r for r in csv.DictReader(f) if r["team_a"] == "NED" and r["team_b"] == "JPN")
    spec = backtest_row_to_match_input(row)
    out = run_match_v41(spec)
    assert out.classification in ("PASS", "HALT")
    assert out.ev_rule14 < 1.5


def test_v31_june_slate_still_replicates():
    """Regression: original v3.1 replicable pipeline unchanged."""
    results = run_full_pipeline(str(JUNE_CSV))
    france = next(r for r in results if "France" in r["match"])
    assert abs(france["p_win_a_raw"] - 54.0) < 1.0


def test_production_csv_written_on_full_run():
    run_full_v41_pipeline(save_output=True)
    assert OUTPUT_CSV.exists()
    lines = OUTPUT_CSV.read_text().strip().splitlines()
    assert len(lines) >= 228  # header + 6 june + 222 backtest