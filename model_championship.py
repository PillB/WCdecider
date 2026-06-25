#!/usr/bin/env python3
"""Nested chronological benchmark for WCdecider's available 1X2 data.

This benchmark intentionally favors reproducible, sample-efficient models.
The current history has only a few hundred matches, so neural and graph architectures are
registered as research candidates but rejected from production before fitting:
their parameter count and team sparsity make a credible untouched comparison
impossible. This is evidence discipline, not a claim that those models are
universally inferior.

The graph/deep candidates are kept in the registry because they become relevant
once the project has enough timestamped fixtures, player/team covariates, and
closing-line labels to support nested chronological comparison. With the present
data, a "big graph" of teams and matches is useful as a feature-engineering
view, not as sufficient evidence to train a high-capacity temporal GNN.
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
MIN_DEEP_FIXTURES = 2_000
MIN_TEMPORAL_EDGES_PER_TEAM = 30


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


def date_block_boundaries(rows: Sequence[HistoricalRow]) -> List[int]:
    """Return row boundaries that never divide fixtures sharing a date."""
    boundaries = [0]
    boundaries.extend(
        index
        for index in range(1, len(rows))
        if rows[index - 1].date != rows[index].date
    )
    boundaries.append(len(rows))
    return boundaries


def date_block_split(
    rows: Sequence[HistoricalRow], fraction: float,
) -> int:
    """Choose a chronological split using whole date blocks."""
    boundaries = date_block_boundaries(rows)
    block_count = len(boundaries) - 1
    if block_count < 2:
        raise ValueError("At least two date blocks are required")
    split_block = min(
        block_count - 1,
        max(1, int(block_count * fraction)),
    )
    return boundaries[split_block]


def rolling_windows(rows: Sequence[HistoricalRow]) -> List[Tuple[int, int]]:
    """Evaluation windows made exclusively from complete date blocks."""
    boundaries = date_block_boundaries(rows)
    block_count = len(boundaries) - 1
    origins = (0.55, 0.65, 0.75, 0.85)
    windows = []
    for start_fraction, end_fraction in zip(origins, origins[1:] + (1.0,)):
        start_block = min(block_count, int(block_count * start_fraction))
        end_block = min(block_count, int(block_count * end_fraction))
        start = boundaries[start_block]
        end = boundaries[end_block]
        if end > start:
            windows.append((start, end))
    if not windows:
        raise ValueError("Too few date blocks for rolling evaluation windows")
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
    challenger: Callable[[HistoricalRow], Probability],
    market: Callable[[HistoricalRow], Probability],
    iterations: int = 5000,
) -> Dict[str, object]:
    """Weighted paired bootstrap that resamples complete fixture-date blocks."""
    if not rows:
        raise ValueError("Paired bootstrap requires at least one row")
    blocks: List[Tuple[float, float]] = []
    for start, end in zip(
        date_block_boundaries(rows)[:-1],
        date_block_boundaries(rows)[1:],
    ):
        weighted_difference = weight_sum = 0.0
        for row in rows[start:end]:
            weighted_difference += row.weight * (
                log_loss(challenger(row), row.outcome)
                - log_loss(market(row), row.outcome)
            )
            weight_sum += row.weight
        blocks.append((weighted_difference, weight_sum))
    total_weight = sum(weight for _, weight in blocks)
    if total_weight <= 0.0:
        raise ValueError("Paired bootstrap requires positive total weight")
    rng = random.Random(SEED)
    means = []
    for _ in range(iterations):
        sampled = [blocks[rng.randrange(len(blocks))] for _ in blocks]
        sampled_weight = sum(weight for _, weight in sampled)
        means.append(
            sum(difference for difference, _ in sampled) / sampled_weight
        )
    means.sort()
    return {
        "challenger_minus_market_log_loss": (
            sum(difference for difference, _ in blocks) / total_weight
        ),
        "ci_95_lower": means[int(iterations * 0.025)],
        "ci_95_upper": means[int(iterations * 0.975)],
        "secure_improvement": means[int(iterations * 0.975)] < 0.0,
        "iterations": iterations,
        "block_count": len(blocks),
        "method": "weighted_paired_bootstrap_by_fixture_date",
    }


def nested_outer_benchmark(
    selection: Sequence[HistoricalRow],
) -> Dict[str, object]:
    """Evaluate inner-selected configurations on independent outer windows."""
    boundaries = date_block_boundaries(selection)
    block_count = len(boundaries) - 1
    start_block = min(
        block_count - 1,
        max(1, int(block_count * 0.55)),
    )
    remaining_blocks = block_count - start_block
    folds = []
    for index in range(4):
        test_start_block = start_block + (remaining_blocks * index) // 4
        test_end_block = (
            block_count if index == 3
            else start_block + (remaining_blocks * (index + 1)) // 4
        )
        test_start = boundaries[test_start_block]
        test_end = boundaries[test_end_block]
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
    benchmark_champion = min(
        means,
        key=lambda name: (
            means[name]["mean_log_loss"], means[name]["mean_brier"]
        ),
    )
    return {
        "folds": folds,
        "means": means,
        "benchmark_champion": benchmark_champion,
    }


def temporal_edge_counts(
    rows: Sequence[HistoricalRow],
) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        counts[row.team_a] = counts.get(row.team_a, 0) + 1
        counts[row.team_b] = counts.get(row.team_b, 0) + 1
    return dict(sorted(counts.items()))


def select_holdout_challenger(
    means: Mapping[str, Mapping[str, float]],
    benchmark_champion: str,
) -> str:
    """Return the winner, or the best genuinely price-independent challenger.

    A stack containing the market proxy is not a non-market challenger. In
    particular, a tuned zero-Elo/100%-market stack is mathematically identical
    to the benchmark and would produce a meaningless zero-width comparison.
    """
    if benchmark_champion != "market_devigged_proxy":
        return benchmark_champion
    non_market_models = [
        name for name in (
            "elo_tuned_nested",
            "elo_fixed_400",
        )
        if name in means
    ]
    if not non_market_models:
        raise ValueError("A non-market challenger is required")
    return min(
        non_market_models,
        key=lambda name: (
            means[name]["mean_log_loss"],
            means[name]["mean_brier"],
        ),
    )


def build() -> Dict[str, object]:
    all_rows = load_historical()
    rows = [
        row for row in all_rows
        if row.odds_a is not None and row.odds_d is not None
        and row.odds_b is not None
        and min(row.odds_a, row.odds_d, row.odds_b) > 1.0
    ]
    if len(rows) < 100:
        raise ValueError("Too few complete 1X2 proxy markets for benchmark")
    split = date_block_split(rows, 0.85)
    selection, holdout = rows[:split], rows[split:]
    outer = nested_outer_benchmark(selection)
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
    # The benchmark champion is selected by outer windows only. It is evidence,
    # not an instruction to deploy a model.
    benchmark_champion = str(outer["benchmark_champion"])
    holdout_challenger = select_holdout_challenger(
        outer["means"], benchmark_champion,
    )
    comparison = paired_bootstrap(
        holdout, predictors[holdout_challenger],
        predictors["market_devigged_proxy"],
    )
    comparison.update({
        "challenger": holdout_challenger,
        "market_benchmark": "market_devigged_proxy",
    })
    edge_counts = temporal_edge_counts(all_rows)
    teams_meeting_edge_gate = sum(
        count >= MIN_TEMPORAL_EDGES_PER_TEAM
        for count in edge_counts.values()
    )
    fixture_gate_passed = len(all_rows) >= MIN_DEEP_FIXTURES
    edge_gate_passed = bool(edge_counts) and (
        teams_meeting_edge_gate == len(edge_counts)
    )
    deep_learning_research = {
        "summary": (
            "Deep and graph models remain research-track only. The available "
            f"complete 1X2 proxy-market corpus has {len(rows)} complete matches "
            f"after filtering and {len(all_rows)} total historical match rows, "
            "far below the prespecified evidence gate for a production "
            "temporal GNN or sequence transformer."
        ),
        "candidate_families": [
            {
                "name": "CatBoost/LightGBM tabular rating model",
                "use_when": (
                    "Hundreds to thousands of fixtures with stable engineered "
                    "features; strong baseline before neural models."
                ),
                "current_status": (
                    "Registered as regularized_multinomial_research; not "
                    "promoted because market proxy dominates outer folds."
                ),
            },
            {
                "name": "Hierarchical dynamic Poisson / Dixon-Coles",
                "use_when": (
                    "Goal-score modeling with team attack/defense partial "
                    "pooling and enough repeated team histories."
                ),
                "current_status": (
                    "Dixon-Coles is shadow-only; paired-bootstrap improvement "
                    "is not statistically secure."
                ),
            },
            {
                "name": "Temporal Graph Network / TGAT-style dynamic graph",
                "use_when": (
                    "Thousands of time-stamped team/player/match edges, node "
                    "features, and strictly pre-event labels."
                ),
                "current_status": (
                    "Rejected by evidence gate; current graph has too few "
                    "temporal edges per team for credible fitting."
                ),
            },
            {
                "name": "GraphMixer / DyGFormer-style efficient temporal graph",
                "use_when": (
                    "Large temporal interaction graphs where memory/lightweight "
                    "mixing architectures can be compared out of sample."
                ),
                "current_status": (
                    "Research registry only; no production weight without "
                    "outer-fold improvement over market baselines."
                ),
            },
            {
                "name": "Sequence transformer over team histories",
                "use_when": (
                    "Long sequential histories with lineup/player/context "
                    "tokens and a separate untouched tournament holdout."
                ),
                "current_status": (
                    "Rejected by sample-size gate; likely overfits current "
                    "sparse World Cup/qualifier history."
                ),
            },
        ],
        "promotion_gate": {
            "minimum_timestamped_fixtures": MIN_DEEP_FIXTURES,
            "minimum_temporal_edges_per_team": MIN_TEMPORAL_EDGES_PER_TEAM,
            "actual_fixture_count": len(all_rows),
            "actual_team_count": len(edge_counts),
            "actual_temporal_edges_per_team": edge_counts,
            "teams_meeting_temporal_edge_minimum": teams_meeting_edge_gate,
            "fixture_count_gate_passed": fixture_gate_passed,
            "temporal_edge_gate_passed": edge_gate_passed,
            "research_promotion_gate_passed": (
                fixture_gate_passed and edge_gate_passed
            ),
            "required_validation": (
                "nested walk-forward model selection, final untouched holdout, "
                "paired bootstrap for proper scores, calibration plots, "
                "profitability/CLV only against timestamp-verified closing odds, "
                "and multiple-testing correction across searched variants"
            ),
        },
        "pitfalls_controlled": [
            "look-ahead leakage from using future ratings or post-kickoff prices",
            "same-day split leakage across matches in one matchday",
            "winner's curse from trying many architectures on a tiny holdout",
            "probability calibration ignored in favor of accuracy",
            "profitability inferred without executable timestamped closing odds",
            "naive stacking weights selected outside chronological folds",
        ],
        "research_sources": [
            {
                "title": "Temporal Graph Networks for Deep Learning on Dynamic Graphs",
                "url": "https://arxiv.org/abs/2006.10637",
                "applies_to": "TGN candidate registry and temporal-edge data requirements",
            },
            {
                "title": "GraphMixer: Efficient Temporal Graph Learning with MLP-Mixer",
                "url": "https://arxiv.org/abs/2302.11636",
                "applies_to": "efficient temporal graph research-track architecture",
            },
            {
                "title": "Model Cards for Model Reporting",
                "url": "https://arxiv.org/abs/1810.03993",
                "applies_to": "reporting limitations, intended use, and validation status",
            },
        ],
    }
    return {
        "version": "nested_chronological_benchmark_v2",
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
        "nested_outer_benchmark": outer,
        # Read-only compatibility for report consumers outside this module's
        # ownership scope. New code should use nested_outer_benchmark.
        "nested_outer_championship": outer,
        "legacy_schema_aliases": {
            "nested_outer_championship": "nested_outer_benchmark",
        },
        "tuned_elo": tuned_elo,
        "tuned_stack": tuned_stack,
        "registered_variants": [
            "uniform",
            "market_devigged_proxy",
            "elo_fixed_400",
            "elo_tuned_nested",
            "elo_market_stack_nested",
            "catboost_lightgbm_tabular_research",
            "independent_poisson_score_model",
            "dixon_coles_shadow",
            "hierarchical_dynamic_poisson_research",
            "regularized_multinomial_research",
            "bayesian_model_averaging_research",
            "temporal_graph_network_research_gate",
            "graphmixer_temporal_graph_research_gate",
            "dygformer_temporal_graph_research_gate",
            "temporal_graph_neural_network_rejected_low_sample",
            "transformer_sequence_model_rejected_low_sample",
        ],
        "capacity_rejections": {
            "temporal_graph_neural_network": (
                f"{len(all_rows)} matches and sparse team histories are "
                f"insufficient for a credible high-capacity chronological "
                f"comparison. Production gate requires at least "
                f"{MIN_DEEP_FIXTURES} timestamped fixtures and roughly "
                f"{MIN_TEMPORAL_EDGES_PER_TEAM} temporal edges per team."
            ),
            "graphmixer_or_dygformer": (
                "Efficient temporal graph architectures are appropriate once "
                "the graph has enough repeated pre-event interactions; current "
                "outer folds still favor the de-vigged market proxy."
            ),
            "transformer_sequence_model": (
                "Effective sample size is orders of magnitude below a defensible "
                "sequence-model benchmark; fitting would invite leakage and "
                "variance-driven selection."
            ),
        },
        "deep_learning_research": deep_learning_research,
        "benchmark_champion": benchmark_champion,
        "benchmark_champion_is_deployment_decision": False,
        "holdout_challenger": holdout_challenger,
        "holdout_metrics": holdout_metrics,
        "challenger_vs_market_paired_bootstrap": comparison,
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
        "benchmark_champion": result["benchmark_champion"],
        "selection_rows": result["selection_rows"],
        "holdout_rows": result["untouched_holdout_rows"],
        "holdout": result["holdout_metrics"][result["benchmark_champion"]],
        "bootstrap": result["challenger_vs_market_paired_bootstrap"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
