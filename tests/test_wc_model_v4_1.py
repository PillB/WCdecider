#!/usr/bin/env python3
"""Tests for wc_model_v4_1_ensemble.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from wc_model_v4_1_ensemble import (
    V41_DEFAULTS,
    MatchInputV4,
    StakeTier,
    model_for_ev_layer,
    run_match_v41,
    stack_model_market,
)
from wc_backtest_framework import evaluate_all_models, trap_analysis


def test_mod_tier_stacks_model_with_market():
    model = (0.60, 0.20, 0.20)
    market = (0.50, 0.25, 0.25)
    ev = model_for_ev_layer(model, market, StakeTier.MODERATE)
    stacked = stack_model_market(model, market, V41_DEFAULTS["mod_model_market_stack"])
    assert abs(ev[0] - stacked[0]) < 1e-9
    assert ev[0] < model[0], "MOD stack should pull toward market"


def test_spec_tier_uses_raw_model():
    model = (0.20, 0.25, 0.55)
    market = (0.15, 0.20, 0.65)
    ev = model_for_ev_layer(model, market, StakeTier.SPECULATIVE)
    assert ev == model


def test_ned_jpn_v41_passes_mod_trap():
    spec = MatchInputV4(
        name="Netherlands vs Japan",
        elo_a=1944, elo_b=1906,
        o_win_a=2.15, o_draw=3.40, o_win_b=3.50,
        pick_outcome="A",
    )
    out = run_match_v41(spec)
    assert out.tier == StakeTier.MODERATE
    assert out.model_ev_1x2 != out.model_1x2, "MOD should use stacked EV leg"
    assert out.classification in ("PASS", "HALT")


def test_v41_stack_beats_v4_on_expanded_set():
    results, _, _ = evaluate_all_models()
    assert results["v4_1_stack"]["mean_brier"] < results["v4_elo"]["mean_brier"]


def test_trap_analysis_no_mod_bets_v41():
    traps = trap_analysis()
    mod_traps = [t for t in traps if t["would_bet_v41"]]
    assert len(mod_traps) == 0


def test_conservative_kelly_non_negative():
    spec = MatchInputV4(
        name="Australia vs Turkey",
        elo_a=1777, elo_b=1911,
        o_win_a=5.35, o_draw=4.20, o_win_b=1.65,
        pick_outcome="A",
    )
    out = run_match_v41(spec)
    assert out.stake_conservative >= 0
    assert out.stake_point_kelly >= 0