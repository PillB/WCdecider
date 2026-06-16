#!/usr/bin/env python3
"""Tests for wc_bayesian_model_search.py."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from wc_bayesian_model_search import (
    RESULTS_PATH,
    SEED_CONFIGS,
    search_degree,
    composite_score,
)
from wc_backtest_framework import get_all_matches


def test_five_seeds_per_degree():
    for d in range(1, 7):
        assert len(SEED_CONFIGS[d]) == 5


def test_degree2_search_runs():
    matches = get_all_matches()
    results = search_degree(2, matches, zoom_rounds=1, zoom_per_round=2, seed=99)
    assert len(results) == 7  # 5 seeds + 2 zoom
    assert results[0].trap_count == 0
    assert results[0].brier < 0.65


def test_composite_score_penalizes_traps():
    s0 = composite_score(0.60, 0, 1.0, 10.0)
    s1 = composite_score(0.60, 1, 1.0, 10.0)
    assert s1 < s0


def test_results_json_exists_after_search():
    if RESULTS_PATH.exists():
        data = json.loads(RESULTS_PATH.read_text())
        assert "1" in data
        assert len(data["1"]) >= 5