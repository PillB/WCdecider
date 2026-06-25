#!/usr/bin/env python3
"""Tests for wc_model_v4_ensemble.py and wc_backtest_framework.py."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from wc_model_v4_ensemble import (
    V4_DEFAULTS,
    MatchInputV4,
    StakeTier,
    apply_rule14,
    dixon_coles_ou_bt_ts,
    ensemble_blend_1x2,
    infer_stake_tier,
    run_match_v4,
    three_way_1x2_v4,
)
from wc_backtest_framework import (
    evaluate_all_models,
    get_all_matches,
    model_v4_1x2,
    trap_analysis,
)
from wc_ensemble_degree2 import brier_score_1x2


def test_v4_draw_boost_raises_draw_prob():
    pA, d, pB = three_way_1x2_v4(0.79, opener_draw_boost=0.07)
    pA0, d0, pB0 = three_way_1x2_v4(0.79, opener_draw_boost=0.0)
    assert d > d0
    assert d <= 0.35


def test_rule14_longshot_uplift():
    assert abs(apply_rule14(0.20) - 0.22) < 1e-9
    assert abs(apply_rule14(0.70) - 0.68) < 1e-9
    assert apply_rule14(0.40) == 0.40


def test_tier_inference():
    assert infer_stake_tier(0.20, 5.0) == StakeTier.SPECULATIVE
    assert infer_stake_tier(0.55, 1.80) == StakeTier.MODERATE
    assert infer_stake_tier(0.35, 2.80) == StakeTier.MARGINAL


def test_dc_ou_probs_sum_sensible():
    ou = dixon_coles_ou_bt_ts(1.5, 1.0, rho=-0.07)
    assert 0.0 < ou["p_over_25"] < 1.0
    assert abs(ou["p_over_25"] + ou["p_under_25"] - 1.0) < 1e-6
    assert 0.0 < ou["p_btts"] < 1.0


def test_spain_cv_v4_draw_calibration():
    """Spain 0-0: v4 should assign meaningful draw probability."""
    spec_win = MatchInputV4(
        name="Spain vs Cape Verde",
        elo_a=2157, elo_b=1578,
        injury_a=-25, mu_total=2.4,
        finetune_str="Rule 21 opener/minnow/rotation",
        o_win_a=1.19, pick_outcome="A",
    )
    out_win = run_match_v4(spec_win)
    assert out_win.model_1x2[1] > 0.22, f"draw too low: {out_win.model_1x2[1]}"
    assert out_win.ev_model < 0, "Spain win should be negative EV"

    spec_draw = MatchInputV4(
        name="Spain vs Cape Verde",
        elo_a=2157, elo_b=1578,
        injury_a=-25, mu_total=2.4,
        finetune_str="Rule 21 opener/minnow/rotation",
        o_win_a=1.19, o_draw=6.50, pick_outcome="D",
    )
    out_draw = run_match_v4(spec_draw)
    assert out_draw.model_1x2[1] > 0.25


def test_ned_jpn_v4_passes_mod_trap():
    """MD2 lesson: NED @2.15 should PASS under v4 tier blend."""
    spec = MatchInputV4(
        name="Netherlands vs Japan",
        elo_a=1944, elo_b=1906,
        o_win_a=2.15, pick_outcome="A",
    )
    out = run_match_v4(spec)
    assert out.tier == StakeTier.MODERATE
    assert out.classification in ("PASS", "HALT")


@pytest.mark.skip(reason="Archived v4 benchmark is not a current promotion gate.")
def test_backtest_v4_beats_v31_on_expanded_set():
    """On N=222 expanded set, v4_elo must edge v31_elo (DC blend not required to win)."""
    results, _, _ = evaluate_all_models()
    assert results["v4_elo"]["mean_brier"] <= results["v31_elo"]["mean_brier"]
    assert results["v4_elo"]["n"] >= 200


@pytest.mark.skip(reason="Persisted history intentionally excludes embedded 2026 rows.")
def test_backtest_expanded_dataset():
    from wc_backtest_framework import get_all_matches
    matches = get_all_matches()
    assert len(matches) >= 200, f"expected expanded dataset, got {len(matches)}"
    comps = {m.competition for m in matches}
    assert "WC_2018_GROUP" in comps
    assert "WC_2022_GROUP" in comps
    assert "WC_2026_GROUP" in comps
    assert "FRIENDLY" in comps


@pytest.mark.skip(reason="Archived embedded 2026 fixture was removed from history.")
def test_spain_cv_brier_improved_v4():
    from wc_backtest_framework import get_all_matches
    m = next(x for x in get_all_matches() if x.team_a == "ESP" and x.team_b == "CPV")
    p = model_v4_1x2(m)
    bs = brier_score_1x2(p, "D")
    assert bs < 1.1, f"Brier too high for draw outcome: {bs}"


def test_trap_analysis_no_mod_bets():
    traps = trap_analysis()
    mod_traps = [t for t in traps if t.get("would_bet_v41", t.get("would_bet_v4"))]
    assert len(mod_traps) == 0, "v4.1 should not recommend MOD favorites in backtest"
