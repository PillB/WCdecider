#!/usr/bin/env python3
"""Nested chronological championship for WCdecider's available 1X2 data.

This championship intentionally favors reproducible, sample-efficient models.
The current history has only 253 matches, so neural and graph architectures are
registered as research candidates but rejected from production before fitting:
their parameter count and team sparsity make a credible untouched comparison
impossible. This is evidence discipline, not a claim that those models are
universally inferior.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Sequence, Tuple

from wc_june22_27_pipeline import (
    EPS, HistoricalRow, brier, load_historical, log_loss, three_way_elo,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "model_championship_results.json"
SEED = 42


Probability = Tuple[float, float, float]


def market_probability(row: HistoricalRow) -> Probability:
    inv = [1.0 / row.odds_a, 1.0 / row.odds_d, 1.0 / row.odds_b]
    total = sum(inv)
    return tuple(value / total for value in inv)  # type: ignore[return-value]


def blend(left: Probability, right: Probability, weight: float) -> Probability:
    return tuple(
        weight * a + (1.0 - weight) * b for a, b in zip(left, right)
    )  # type: ignore[return-value]


def evaluate(
    rows: Sequence[HistoricalRow],
    predictor: Callable[[HistoricalRow], Probability],
) -> Dict[str, float]:
    weighted_brier = weighted_log = weight_sum = 0.0
    for row in rows:
        probability = predictor(row)
        weighted_brier += brier(probability, row.outcome) * row.weight
        weighted_log += log_loss(probability, row.outcome) * row.weight
        weight_sum += row.weight
    return {
        "rows": len(rows),
        "brier": weighted_brier / weight_sum,
        "log_loss": weighted_log / weight_sum,
    }


def rolling_windows(rows: Sequence[HistoricalRow]) -> List[Tuple[int, int]]:
    """Expanding-origin evaluation windows inside the selection sample."""
    n = len(rows)
    origins = (0.55, 0.65, 0.75, 0.85)
    windows = []
    for start_fraction, end_fraction in zip(origins, origins[1:] + (1.0,)):
        start = int(n * start_fraction)
        end = int(n * end_fraction)
        if end > start:
            windows.append((start, end))
    return windows


def tune_elo(selection: Sequence[HistoricalRow]) -> Dict[str, float]:
    windows = rolling_windows(selection)
    candidates = []
    for divisor in (325.0, 350.0, 375.0, 400.0, 425.0, 450.0, 500.0):
        for draw_base in (0.14, 0.16, 0.18, 0.20, 0.22, 0.24):
            for draw_slope in (0.04, 0.06, 0.08, 0.10, 0.12, 0.14):
                folds = []
                predictor = lambda row, d=divisor, b=draw_base, s=draw_slope: (
                    three_way_elo(row.elo_a, row.elo_b, d, b, s)
                )
                for start, end in windows:
                    folds.append(evaluate(selection[start:end], predictor))
                candidates.append({
                    "divisor": divisor,
                    "draw_base": draw_base,
                    "draw_slope": draw_slope,
                    "mean_brier": sum(x["brier"] for x in folds) / len(folds),
                    "mean_log_loss": (
                        sum(x["log_loss"] for x in folds) / len(folds)
                    ),
                    "folds": folds,
                })
    return min(
        candidates,
        key=lambda item: (item["mean_log_loss"], item["mean_brier"]),
    )


def tune_stack(
    selection: Sequence[HistoricalRow], elo: Mapping[str, float],
) -> Dict[str, object]:
    """Tune Elo/market stacking weight inside rolling-origin folds."""
    windows = rolling_windows(selection)
    candidates = []
    for elo_weight in (0.0, 0.10, 0.20, 0.30, 0.40, 0.50,
                       0.60, 0.70, 0.80, 0.90, 1.0):
        predictor = lambda row, w=elo_weight: blend(
            three_way_elo(
                row.elo_a, row.elo_b, float(elo["divisor"]),
                float(elo["draw_base"]), float(elo["draw_slope"]),
            ),
            market_probability(row),
            w,
        )
        folds = [
            evaluate(selection[start:end], predictor)
            for start, end in windows
        ]
        candidates.append({
            "elo_weight": elo_weight,
            "market_weight": 1.0 - elo_weight,
            "mean_brier": sum(x["brier"] for x in folds) / len(folds),
            "mean_log_loss": sum(x["log_loss"] for x in folds) / len(folds),
            "folds": folds,
        })
    return min(
        candidates,
        key=lambda item: (item["mean_log_loss"], item["mean_brier"]),
    )


def paired_bootstrap(
    rows: Sequence[HistoricalRow],
    champion: Callable[[HistoricalRow], Probability],
    baseline: Callable[[HistoricalRow], Probability],
    iterations: int = 5000,
) -> Dict[str, float]:
    differences = [
        log_loss(champion(row), row.outcome)
        - log_loss(baseline(row), row.outcome)
        for row in rows
    ]
    rng = random.Random(SEED)
    means = []
    for _ in range(iterations):
        means.append(sum(
            differences[rng.randrange(len(differences))]
            for _ in differences
        ) / len(differences))
    means.sort()
    return {
        "champion_minus_baseline_log_loss": sum(differences) / len(differences),
        "ci_95_lower": means[int(iterations * 0.025)],
        "ci_95_upper": means[int(iterations * 0.975)],
        "secure_improvement": means[int(iterations * 0.975)] < 0.0,
        "iterations": iterations,
    }


def nested_outer_championship(
    selection: Sequence[HistoricalRow],
) -> Dict[str, object]:
    """Evaluate inner-selected configurations on independent outer windows."""
    start = max(80, int(len(selection) * 0.55))
    remaining = len(selection) - start
    width = max(1, remaining // 4)
    folds = []
    for index in range(4):
        test_start = start + index * width
        test_end = (
            len(selection) if index == 3
            else min(len(selection), test_start + width)
        )
        # Keep every same-date matchday entirely on one side of each boundary.
        while (
            test_start < len(selection)
            and test_start > 0
            and selection[test_start - 1].date == selection[test_start].date
        ):
            test_start += 1
        while (
            test_end < len(selection)
            and test_end > test_start
            and selection[test_end - 1].date == selection[test_end].date
        ):
            test_end += 1
        if test_start >= test_end:
            continue
        train = selection[:test_start]
        test = selection[test_start:test_end]
        elo = tune_elo(train)
        stack = tune_stack(train, elo)
        predictors = {
            "uniform": lambda row: (1 / 3, 1 / 3, 1 / 3),
            "market_devigged_proxy": market_probability,
            "elo_tuned_nested": lambda row, e=elo: three_way_elo(
                row.elo_a, row.elo_b, float(e["divisor"]),
                float(e["draw_base"]), float(e["draw_slope"]),
            ),
            "elo_market_stack_nested": lambda row, e=elo, s=stack: blend(
                three_way_elo(
                    row.elo_a, row.elo_b, float(e["divisor"]),
                    float(e["draw_base"]), float(e["draw_slope"]),
                ),
                market_probability(row),
                float(s["elo_weight"]),
            ),
        }
        folds.append({
            "fold": index + 1,
            "train_rows": len(train),
            "test_rows": len(test),
            "test_start": test[0].date.isoformat(),
            "test_end": test[-1].date.isoformat(),
            "train_end": train[-1].date.isoformat(),
            "selected_elo": {
                key: elo[key]
                for key in ("divisor", "draw_base", "draw_slope")
            },
            "selected_stack": {
                key: stack[key]
                for key in ("elo_weight", "market_weight")
            },
            "metrics": {
                name: evaluate(test, predictor)
                for name, predictor in predictors.items()
            },
        })
    model_names = tuple(folds[0]["metrics"])
    means = {
        name: {
            "mean_brier": sum(
                fold["metrics"][name]["brier"] for fold in folds
            ) / len(folds),
            "mean_log_loss": sum(
                fold["metrics"][name]["log_loss"] for fold in folds
            ) / len(folds),
            "positive_log_loss_folds_vs_market": sum(
                fold["metrics"][name]["log_loss"]
                < fold["metrics"]["market_devigged_proxy"]["log_loss"]
                for fold in folds
            ),
        }
        for name in model_names
    }
    champion = min(
        means,
        key=lambda name: (
            means[name]["mean_log_loss"], means[name]["mean_brier"]
        ),
    )
    return {"folds": folds, "means": means, "champion": champion}


def build() -> Dict[str, object]:
    all_rows = load_historical()
    rows = [
        row for row in all_rows
        if row.odds_a is not None and row.odds_d is not None
        and row.odds_b is not None
        and min(row.odds_a, row.odds_d, row.odds_b) > 1.0
    ]
    if len(rows) < 100:
        raise ValueError("Too few complete 1X2 proxy markets for championship")
    split = int(len(rows) * 0.85)
    selection, holdout = rows[:split], rows[split:]
    outer = nested_outer_championship(selection)
    tuned_elo = tune_elo(selection)
    tuned_stack = tune_stack(selection, tuned_elo)

    predictors: Dict[str, Callable[[HistoricalRow], Probability]] = {
        "uniform": lambda row: (1 / 3, 1 / 3, 1 / 3),
        "market_devigged_proxy": market_probability,
        "elo_fixed_400": lambda row: three_way_elo(
            row.elo_a, row.elo_b, 400.0, 0.18, 0.08
        ),
        "elo_tuned_nested": lambda row: three_way_elo(
            row.elo_a, row.elo_b, float(tuned_elo["divisor"]),
            float(tuned_elo["draw_base"]), float(tuned_elo["draw_slope"]),
        ),
        "elo_market_stack_nested": lambda row: blend(
            three_way_elo(
                row.elo_a, row.elo_b, float(tuned_elo["divisor"]),
                float(tuned_elo["draw_base"]), float(tuned_elo["draw_slope"]),
            ),
            market_probability(row),
            float(tuned_stack["elo_weight"]),
        ),
    }
    holdout_metrics = {
        name: evaluate(holdout, predictor)
        for name, predictor in predictors.items()
    }
    # Champion is selected by independent outer rolling windows, never the
    # final holdout or any profitability metric.
    champion_name = str(outer["champion"])
    comparison = paired_bootstrap(
        holdout, predictors[champion_name],
        predictors["market_devigged_proxy"],
    )
    return {
        "version": "nested_chronological_championship_v1",
        "rows": len(rows),
        "source_rows": len(all_rows),
        "excluded_missing_complete_1x2": len(all_rows) - len(rows),
        "selection_rows": len(selection),
        "untouched_holdout_rows": len(holdout),
        "selection_rule": (
            "inner rolling-origin tuning inside four expanding outer folds; "
            "minimum outer mean log loss then Brier; final holdout is "
            "evaluation-only"
        ),
        "nested_outer_championship": outer,
        "tuned_elo": tuned_elo,
        "tuned_stack": tuned_stack,
        "registered_variants": [
            "uniform",
            "market_devigged_proxy",
            "elo_fixed_400",
            "elo_tuned_nested",
            "elo_market_stack_nested",
            "independent_poisson_score_model",
            "dixon_coles_shadow",
            "hierarchical_dynamic_poisson_research",
            "regularized_multinomial_research",
            "bayesian_model_averaging_research",
            "temporal_graph_neural_network_rejected_low_sample",
            "transformer_sequence_model_rejected_low_sample",
        ],
        "capacity_rejections": {
            "temporal_graph_neural_network": (
                "253 matches and sparse team histories are insufficient for a "
                "credible high-capacity chronological comparison."
            ),
            "transformer_sequence_model": (
                "Effective sample size is orders of magnitude below a defensible "
                "sequence-model championship; fitting would invite leakage and "
                "variance-driven selection."
            ),
        },
        "champion": champion_name,
        "holdout_metrics": holdout_metrics,
        "champion_vs_market_paired_bootstrap": comparison,
        "profitability_status": (
            "blocked_no_timestamp_verified_closing_odds"
        ),
        "rival_500_percent_claim_status": (
            "unverified_requires_complete_timestamped_executable_bet_ledger"
        ),
    }


def main() -> None:
    result = build()
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "champion": result["champion"],
        "selection_rows": result["selection_rows"],
        "holdout_rows": result["untouched_holdout_rows"],
        "holdout": result["holdout_metrics"][result["champion"]],
        "bootstrap": result["champion_vs_market_paired_bootstrap"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
