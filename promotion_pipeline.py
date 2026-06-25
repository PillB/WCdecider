#!/usr/bin/env python3
"""Build fail-closed evidence for model stacking and recommendation promotion.

The pipeline creates chronological out-of-fold (OOF) predictions for
price-independent models, selects calibration and stack parameters only on
data preceding each outer fold, and records explicit promotion gates.

This module deliberately does not modify production predictions. A good OOF
result is necessary but not sufficient: a newly sealed prospective holdout and
timestamp-qualified profitability evaluation are independently required.

Example:
    $ PYTHONDONTWRITEBYTECODE=1 python3 -B promotion_pipeline.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import model_championship as championship
from wc_june22_27_pipeline import (
    EPS,
    HistoricalRow,
    brier,
    expected_lambdas,
    log_loss,
    score_matrix,
    score_model_metrics,
    three_way_elo,
)


ROOT = Path(__file__).resolve().parent
OOF_OUTPUT = ROOT / "promotion_oof_predictions.csv"
RESULT_OUTPUT = ROOT / "recommendation_promotion_results.json"
REGISTRY = ROOT / "governance" / "prospective_holdout_registry.json"
REGISTRY_LOCK = (
    ROOT / "governance" / "prospective_holdout_registry.lock.json"
)
PREDICTIONS = ROOT / "wc_june22_27_predictions.json"
COVERAGE = ROOT / "historical_closing_odds_canonical_coverage.json"
PROTOCOL = ROOT / "RECOMMENDATION_STACKING_PROMOTION_PLAN.md"
SEED = 20260624
TEMPERATURES = (0.75, 0.85, 1.00, 1.15, 1.30, 1.50)
STACK_WEIGHTS = tuple(index / 10.0 for index in range(11))
MIN_RESEARCH_OOF_ROWS = 100
MIN_RESEARCH_CLASS_ROWS = 20
MIN_RESEARCH_DATE_BLOCKS = 20
MIN_PRODUCTION_OOF_ROWS = 300
MIN_PRODUCTION_CLASS_ROWS = 75
MIN_PRODUCTION_DATE_BLOCKS = 40
MIN_PRODUCTION_OUTER_FOLD_ROWS = 40
BOOTSTRAP_ITERATIONS = 5000
MODEL_PROMOTION_GATES = (
    "production_minimum_oof_rows",
    "production_minimum_class_rows",
    "production_minimum_date_blocks",
    "production_minimum_outer_fold_rows",
    "every_outer_fold_contains_all_outcome_classes",
    "research_temperature_not_on_search_boundary",
    "empirical_calibration_proper_score_noninferiority",
    "empirical_calibration_reliability_noninferiority",
    "empirical_calibration_secure_log_loss_noninferiority",
    "stack_secure_against_all_included_bases_after_holm",
    "stack_improves_at_least_three_of_four_folds_against_each_base",
    "stack_is_nontrivial_distinct_model_in_every_fold",
    "new_confirmatory_holdout_sealed_before_predictions",
    "confirmatory_holdout_evaluated",
)
RECOMMENDATION_PROMOTION_GATES = MODEL_PROMOTION_GATES + (
    "timestamp_qualified_profitability_rows_available",
    "minimum_profitability_sample_500_bets_250_fixtures",
    "positive_lower_roi_and_clv_bounds",
    "four_role_exact_hash_governance_pass",
)

Probability = Tuple[float, float, float]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def gates_authorize(
    gates: Mapping[str, bool], required: Sequence[str],
) -> bool:
    """Return true only when every explicitly named gate is present and true."""
    return all(gates.get(name) is True for name in required)


def normalize(probability: Iterable[float]) -> Probability:
    values = [max(EPS, float(value)) for value in probability]
    total = sum(values)
    return tuple(value / total for value in values)  # type: ignore[return-value]


def temperature_scale(
    probability: Probability, temperature: float,
) -> Probability:
    """Apply multiclass temperature scaling to probabilities.

    Raising probabilities to ``1 / temperature`` is equivalent to dividing
    log-probabilities by the temperature and applying softmax.
    """
    if temperature <= 0:
        raise ValueError("Temperature must be positive")
    return normalize(value ** (1.0 / temperature) for value in probability)


def poisson_outcome_probability(
    row: HistoricalRow, config: Mapping[str, float],
) -> Probability:
    lam_a, lam_b = expected_lambdas(
        row.elo_a,
        row.elo_b,
        float(config["mu_total"]),
        0.0,
        0.0,
        float(config["allocation"]),
        float(config["gap_scale"]),
        float(config["gap_intensity"]),
    )
    home = draw = away = 0.0
    for goals_a, goals_b, probability in score_matrix(lam_a, lam_b):
        if goals_a > goals_b:
            home += probability
        elif goals_a == goals_b:
            draw += probability
        else:
            away += probability
    return normalize((home, draw, away))


def tune_poisson(rows: Sequence[HistoricalRow]) -> Dict[str, float]:
    """Select a compact score-model grid on chronological inner windows."""
    windows = championship.rolling_windows(rows)
    candidates: List[Dict[str, float]] = []
    for mu_total in (2.25, 2.50, 2.75, 3.00):
        for allocation in (0.30, 0.35, 0.40):
            for gap_scale in (350.0, 420.0, 500.0):
                for gap_intensity in (0.0, 0.15, 0.30, 0.45):
                    metrics = [
                        score_model_metrics(
                            rows[start:end],
                            mu_total,
                            allocation,
                            gap_scale,
                            gap_intensity,
                        )
                        for start, end in windows
                    ]
                    candidates.append({
                        "mu_total": mu_total,
                        "allocation": allocation,
                        "gap_scale": gap_scale,
                        "gap_intensity": gap_intensity,
                        "mean_score_nll": sum(
                            item["score_nll"] for item in metrics
                        ) / len(metrics),
                    })
    return min(candidates, key=lambda item: item["mean_score_nll"])


def inner_cross_fitted_predictions(
    rows: Sequence[HistoricalRow],
) -> Tuple[List[HistoricalRow], List[Probability], List[Probability]]:
    """Generate genuine inner OOF base predictions.

    Each inner validation block is predicted by configurations selected only
    from the strict chronological prefix before that block.
    """
    validation_rows: List[HistoricalRow] = []
    elo_probabilities: List[Probability] = []
    poisson_probabilities: List[Probability] = []
    for start, end in championship.rolling_windows(rows):
        prefix = rows[:start]
        validation = rows[start:end]
        elo = championship.tune_elo(prefix)
        poisson = tune_poisson(prefix)
        validation_rows.extend(validation)
        elo_probabilities.extend([
            three_way_elo(
                row.elo_a,
                row.elo_b,
                float(elo["divisor"]),
                float(elo["draw_base"]),
                float(elo["draw_slope"]),
            )
            for row in validation
        ])
        poisson_probabilities.extend([
            poisson_outcome_probability(row, poisson) for row in validation
        ])
    return validation_rows, elo_probabilities, poisson_probabilities


def weighted_log_loss(
    rows: Sequence[HistoricalRow], probabilities: Sequence[Probability],
) -> float:
    denominator = sum(row.weight for row in rows)
    return sum(
        row.weight * log_loss(probability, row.outcome)
        for row, probability in zip(rows, probabilities)
    ) / denominator


def select_temperature(
    rows: Sequence[HistoricalRow], probabilities: Sequence[Probability],
) -> float:
    return min(
        TEMPERATURES,
        key=lambda temperature: weighted_log_loss(
            rows,
            [
                temperature_scale(probability, temperature)
                for probability in probabilities
            ],
        ),
    )


def blend(
    left: Probability, right: Probability, left_weight: float,
) -> Probability:
    return normalize(
        left_weight * left_value + (1.0 - left_weight) * right_value
        for left_value, right_value in zip(left, right)
    )


def select_stack_weight(
    rows: Sequence[HistoricalRow],
    elo_probabilities: Sequence[Probability],
    poisson_probabilities: Sequence[Probability],
) -> float:
    return min(
        STACK_WEIGHTS,
        key=lambda weight: weighted_log_loss(
            rows,
            [
                blend(elo, poisson, weight)
                for elo, poisson in zip(
                    elo_probabilities, poisson_probabilities
                )
            ],
        ),
    )


def outcome_index(outcome: str) -> int:
    return {"A": 0, "D": 1, "B": 2}[outcome]


def reliability_metrics(
    records: Sequence[Mapping[str, object]], model: str, bins: int = 10,
) -> Dict[str, object]:
    weighted_brier = weighted_log = weight_sum = 0.0
    class_brier = [0.0, 0.0, 0.0]
    class_probability = [0.0, 0.0, 0.0]
    class_observed = [0.0, 0.0, 0.0]
    top_bins: List[List[Tuple[float, float, float]]] = [
        [] for _ in range(bins)
    ]
    class_bins: List[List[List[Tuple[float, float, float]]]] = [
        [[] for _ in range(bins)] for _ in range(3)
    ]
    for record in records:
        probability = tuple(record[f"{model}_p_{suffix}"] for suffix in ("a", "d", "b"))
        probability = normalize(probability)
        outcome = str(record["outcome"])
        weight = float(record["weight"])
        weighted_brier += weight * brier(probability, outcome)
        weighted_log += weight * log_loss(probability, outcome)
        weight_sum += weight
        observed_index = outcome_index(outcome)
        for class_index in range(3):
            observed = 1.0 if class_index == observed_index else 0.0
            class_brier[class_index] += weight * (
                probability[class_index] - observed
            ) ** 2
            class_probability[class_index] += weight * probability[class_index]
            class_observed[class_index] += weight * observed
        predicted = max(range(3), key=lambda index: probability[index])
        confidence = probability[predicted]
        correct = 1.0 if predicted == observed_index else 0.0
        bin_index = min(bins - 1, int(confidence * bins))
        top_bins[bin_index].append((confidence, correct, weight))
        for class_index in range(3):
            confidence = probability[class_index]
            observed = 1.0 if class_index == observed_index else 0.0
            bin_index = min(bins - 1, int(confidence * bins))
            class_bins[class_index][bin_index].append(
                (confidence, observed, weight)
            )

    def summarize(
        groups: Sequence[Sequence[Tuple[float, float, float]]],
    ) -> Tuple[float, List[Dict[str, float]]]:
        error = 0.0
        summaries = []
        for index, group in enumerate(groups):
            if not group:
                summaries.append({
                    "bin": index,
                    "rows": 0,
                    "weight": 0.0,
                    "mean_confidence": 0.0,
                    "observed_rate": 0.0,
                })
                continue
            group_weight = sum(item[2] for item in group)
            confidence = sum(item[0] * item[2] for item in group) / group_weight
            observed = sum(item[1] * item[2] for item in group) / group_weight
            error += group_weight / weight_sum * abs(confidence - observed)
            summaries.append({
                "bin": index,
                "rows": len(group),
                "weight": group_weight,
                "mean_confidence": confidence,
                "observed_rate": observed,
            })
        return error, summaries

    top_ece, top_summary = summarize(top_bins)
    class_summaries = []
    class_eces = []
    for groups in class_bins:
        error, summary = summarize(groups)
        class_eces.append(error)
        class_summaries.append(summary)
    return {
        "rows": len(records),
        "date_blocks": len({record["date"] for record in records}),
        "brier": weighted_brier / weight_sum,
        "log_loss": weighted_log / weight_sum,
        "classwise_brier": {
            label: class_brier[index] / weight_sum
            for index, label in enumerate(("A", "D", "B"))
        },
        "calibration_in_the_large": {
            label: (
                class_probability[index] - class_observed[index]
            ) / weight_sum
            for index, label in enumerate(("A", "D", "B"))
        },
        "top_label_ece": top_ece,
        "mean_classwise_ece": sum(class_eces) / len(class_eces),
        "minimum_populated_bin_rows": min(
            (
                int(group["rows"])
                for group in top_summary
                if group["rows"]
            ),
            default=0,
        ),
        "top_label_bins": top_summary,
        "classwise_bins": class_summaries,
    }


def chronological_outer_folds(
    rows: Sequence[HistoricalRow],
) -> List[Tuple[Sequence[HistoricalRow], Sequence[HistoricalRow]]]:
    boundaries = championship.date_block_boundaries(rows)
    block_count = len(boundaries) - 1
    start_block = max(1, int(block_count * 0.55))
    remaining = block_count - start_block
    folds = []
    for index in range(4):
        test_start_block = start_block + remaining * index // 4
        test_end_block = (
            block_count
            if index == 3
            else start_block + remaining * (index + 1) // 4
        )
        train_end = boundaries[test_start_block]
        test_end = boundaries[test_end_block]
        if test_end > train_end:
            folds.append((rows[:train_end], rows[train_end:test_end]))
    return folds


def build_oof(rows: Sequence[HistoricalRow]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    records: List[Dict[str, object]] = []
    fold_metadata: List[Dict[str, object]] = []
    for fold_number, (train, test) in enumerate(
        chronological_outer_folds(rows), start=1
    ):
        elo = championship.tune_elo(train)
        poisson = tune_poisson(train)
        inner, inner_elo, inner_poisson = inner_cross_fitted_predictions(train)
        elo_temperature = select_temperature(inner, inner_elo)
        poisson_temperature = select_temperature(inner, inner_poisson)
        calibrated_inner_elo = [
            temperature_scale(probability, elo_temperature)
            for probability in inner_elo
        ]
        calibrated_inner_poisson = [
            temperature_scale(probability, poisson_temperature)
            for probability in inner_poisson
        ]
        elo_stack_weight = select_stack_weight(
            inner, calibrated_inner_elo, calibrated_inner_poisson
        )
        fold_metadata.append({
            "fold": fold_number,
            "train_rows": len(train),
            "test_rows": len(test),
            "train_end": train[-1].date.isoformat(),
            "test_start": test[0].date.isoformat(),
            "test_end": test[-1].date.isoformat(),
            "elo": {
                key: elo[key]
                for key in ("divisor", "draw_base", "draw_slope")
            },
            "poisson": {
                key: poisson[key]
                for key in (
                    "mu_total", "allocation", "gap_scale", "gap_intensity"
                )
            },
            "elo_temperature": elo_temperature,
            "poisson_temperature": poisson_temperature,
            "stack_elo_weight": elo_stack_weight,
            "stack_poisson_weight": 1.0 - elo_stack_weight,
            "selected_stack_duplicate_of": (
                "elo_calibrated"
                if elo_stack_weight == 1.0
                else "poisson_calibrated"
                if elo_stack_weight == 0.0
                else None
            ),
            "inner_oof_rows": len(inner),
            "inner_oof_start": inner[0].date.isoformat(),
            "inner_oof_end": inner[-1].date.isoformat(),
        })
        for row in test:
            fixed = three_way_elo(row.elo_a, row.elo_b, 400.0, 0.18, 0.08)
            tuned = three_way_elo(
                row.elo_a,
                row.elo_b,
                float(elo["divisor"]),
                float(elo["draw_base"]),
                float(elo["draw_slope"]),
            )
            poisson_probability = poisson_outcome_probability(row, poisson)
            calibrated_elo = temperature_scale(tuned, elo_temperature)
            calibrated_poisson = temperature_scale(
                poisson_probability, poisson_temperature
            )
            stack = blend(
                calibrated_elo, calibrated_poisson, elo_stack_weight
            )
            record: Dict[str, object] = {
                "fold": fold_number,
                "date": row.date.isoformat(),
                "competition": row.competition,
                "team_a": row.team_a,
                "team_b": row.team_b,
                "outcome": row.outcome,
                "weight": row.weight,
                "train_end": train[-1].date.isoformat(),
            }
            for name, probability in {
                "uniform": (1 / 3, 1 / 3, 1 / 3),
                "elo_fixed": fixed,
                "elo_tuned": tuned,
                "elo_calibrated": calibrated_elo,
                "poisson_tuned": poisson_probability,
                "poisson_calibrated": calibrated_poisson,
                "stack": stack,
            }.items():
                record.update({
                    f"{name}_p_a": probability[0],
                    f"{name}_p_d": probability[1],
                    f"{name}_p_b": probability[2],
                })
            records.append(record)
    return records, fold_metadata


def paired_date_block_bootstrap(
    records: Sequence[Mapping[str, object]],
    challenger: str,
    baseline: str,
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> Dict[str, object]:
    blocks: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for record in records:
        outcome = str(record["outcome"])
        challenger_probability = normalize(
            record[f"{challenger}_p_{suffix}"] for suffix in ("a", "d", "b")
        )
        baseline_probability = normalize(
            record[f"{baseline}_p_{suffix}"] for suffix in ("a", "d", "b")
        )
        blocks[str(record["date"])].append((
            log_loss(challenger_probability, outcome)
            - log_loss(baseline_probability, outcome),
            float(record["weight"]),
        ))
    ordered = [blocks[key] for key in sorted(blocks)]

    def mean(sample: Sequence[Sequence[Tuple[float, float]]]) -> float:
        numerator = sum(
            difference * weight
            for block in sample
            for difference, weight in block
        )
        denominator = sum(
            weight for block in sample for _, weight in block
        )
        return numerator / denominator

    rng = random.Random(SEED)
    samples = []
    for _ in range(iterations):
        samples.append(mean([
            ordered[rng.randrange(len(ordered))] for _ in ordered
        ]))
    samples.sort()
    observed = mean(ordered)
    return {
        "challenger": challenger,
        "baseline": baseline,
        "mean_log_loss_difference": observed,
        "ci_95_lower": samples[int(iterations * 0.025)],
        "ci_95_upper": samples[int(iterations * 0.975)],
        "one_sided_p_value": (
            1 + sum(sample >= 0.0 for sample in samples)
        ) / (iterations + 1),
        "secure_improvement": samples[int(iterations * 0.975)] < 0.0,
        "date_blocks": len(ordered),
        "iterations": iterations,
    }


def holm_adjust(
    comparisons: Sequence[Mapping[str, object]],
) -> List[Dict[str, object]]:
    ordered = sorted(
        comparisons, key=lambda item: float(item["one_sided_p_value"])
    )
    adjusted_so_far = 0.0
    adjusted: List[Dict[str, object]] = []
    count = len(ordered)
    for index, item in enumerate(ordered):
        adjusted_so_far = max(
            adjusted_so_far,
            min(1.0, (count - index) * float(item["one_sided_p_value"])),
        )
        updated = dict(item)
        updated["holm_adjusted_p_value"] = adjusted_so_far
        updated["holm_reject_0_05"] = adjusted_so_far < 0.05
        adjusted.append(updated)
    return sorted(adjusted, key=lambda item: str(item["baseline"]))


def fold_wins(
    records: Sequence[Mapping[str, object]],
    challenger: str,
    baseline: str,
) -> int:
    wins = 0
    for fold in sorted({int(record["fold"]) for record in records}):
        subset = [record for record in records if int(record["fold"]) == fold]
        difference = paired_date_block_bootstrap(
            subset, challenger, baseline, iterations=500
        )["mean_log_loss_difference"]
        wins += float(difference) < 0.0
    return wins


def write_oof(records: Sequence[Mapping[str, object]]) -> None:
    fields = list(records[0])
    with OOF_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def verify_registry(
    registry_path: Path = REGISTRY,
    predictions_path: Path = PREDICTIONS,
    protocol_path: Path = PROTOCOL,
    lock_path: Path = REGISTRY_LOCK,
) -> Dict[str, object]:
    """Verify a frozen registry without mutating it."""
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock["registry_sha256"] != sha256(registry_path):
        raise ValueError("Frozen registry lock hash mismatch")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    cohort = registry["cohorts"][0]
    if str(cohort["status"]).startswith("SEALED"):
        if cohort["prediction_artifact_sha256"] != sha256(predictions_path):
            raise ValueError("Frozen registry prediction hash mismatch")
    elif not str(cohort["status"]).startswith("INVALIDATED"):
        raise ValueError("Registry cohort must be sealed or invalidated")
    if registry["protocol_sha256"] != sha256(protocol_path):
        raise ValueError("Frozen registry protocol hash mismatch")
    return registry


def build() -> Dict[str, object]:
    rows = championship.load_historical()
    records, folds = build_oof(rows)
    write_oof(records)
    models = (
        "uniform",
        "elo_fixed",
        "elo_tuned",
        "elo_calibrated",
        "poisson_tuned",
        "poisson_calibrated",
        "stack",
    )
    metrics = {
        model: reliability_metrics(records, model) for model in models
    }
    outcome_counts = {
        outcome: sum(record["outcome"] == outcome for record in records)
        for outcome in ("A", "D", "B")
    }
    comparisons = holm_adjust([
        paired_date_block_bootstrap(records, "stack", baseline)
        for baseline in (
            "elo_tuned",
            "elo_calibrated",
            "poisson_tuned",
            "poisson_calibrated",
        )
    ])
    calibration_comparisons = {
        "elo_temperature_vs_raw": paired_date_block_bootstrap(
            records, "elo_calibrated", "elo_tuned"
        ),
        "poisson_temperature_vs_raw": paired_date_block_bootstrap(
            records, "poisson_calibrated", "poisson_tuned"
        ),
    }
    stack_secure_against_bases = all(
        comparison["secure_improvement"]
        and comparison["holm_reject_0_05"]
        for comparison in comparisons
    )
    stack_fold_wins = {
        baseline: fold_wins(records, "stack", baseline)
        for baseline in (
            "elo_tuned",
            "elo_calibrated",
            "poisson_tuned",
            "poisson_calibrated",
        )
    }
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    registry = verify_registry()
    gates = {
        "research_temperature_sample_rows": (
            len(records) >= MIN_RESEARCH_OOF_ROWS
        ),
        "research_temperature_sample_classes": (
            min(outcome_counts.values()) >= MIN_RESEARCH_CLASS_ROWS
        ),
        "research_temperature_sample_date_blocks": (
            len({record["date"] for record in records})
            >= MIN_RESEARCH_DATE_BLOCKS
        ),
        "research_temperature_not_on_search_boundary": all(
            fold["elo_temperature"] not in (
                min(TEMPERATURES), max(TEMPERATURES)
            )
            and fold["poisson_temperature"] not in (
                min(TEMPERATURES), max(TEMPERATURES)
            )
            for fold in folds
        ),
        "production_minimum_oof_rows": (
            len(records) >= MIN_PRODUCTION_OOF_ROWS
        ),
        "production_minimum_class_rows": (
            min(outcome_counts.values()) >= MIN_PRODUCTION_CLASS_ROWS
        ),
        "production_minimum_date_blocks": (
            len({record["date"] for record in records})
            >= MIN_PRODUCTION_DATE_BLOCKS
        ),
        "production_minimum_outer_fold_rows": (
            min(fold["test_rows"] for fold in folds)
            >= MIN_PRODUCTION_OUTER_FOLD_ROWS
        ),
        "every_outer_fold_contains_all_outcome_classes": all(
            {
                record["outcome"]
                for record in records
                if record["fold"] == fold["fold"]
            } == {"A", "D", "B"}
            for fold in folds
        ),
        "empirical_calibration_proper_score_noninferiority": (
            metrics["elo_calibrated"]["log_loss"]
            <= metrics["elo_tuned"]["log_loss"] + 0.002
            and metrics["elo_calibrated"]["brier"]
            <= metrics["elo_tuned"]["brier"] + 0.002
            and metrics["poisson_calibrated"]["log_loss"]
            <= metrics["poisson_tuned"]["log_loss"] + 0.002
            and metrics["poisson_calibrated"]["brier"]
            <= metrics["poisson_tuned"]["brier"] + 0.002
        ),
        "empirical_calibration_reliability_noninferiority": (
            metrics["elo_calibrated"]["top_label_ece"]
            <= metrics["elo_tuned"]["top_label_ece"]
            and metrics["elo_calibrated"]["mean_classwise_ece"]
            <= metrics["elo_tuned"]["mean_classwise_ece"]
            and metrics["poisson_calibrated"]["top_label_ece"]
            <= metrics["poisson_tuned"]["top_label_ece"]
            and metrics["poisson_calibrated"]["mean_classwise_ece"]
            <= metrics["poisson_tuned"]["mean_classwise_ece"]
        ),
        "empirical_calibration_secure_log_loss_noninferiority": all(
            comparison["ci_95_upper"] <= 0.0
            for comparison in calibration_comparisons.values()
        ),
        "stack_secure_against_all_included_bases_after_holm": (
            stack_secure_against_bases
        ),
        "stack_improves_at_least_three_of_four_folds_against_each_base": all(
            wins >= 3 for wins in stack_fold_wins.values()
        ),
        "stack_is_nontrivial_distinct_model_in_every_fold": all(
            fold["selected_stack_duplicate_of"] is None for fold in folds
        ),
        "new_confirmatory_holdout_sealed_before_predictions": False,
        "confirmatory_holdout_evaluated": False,
        "timestamp_qualified_profitability_rows_available": (
            int(coverage["primary_validation_rows"]) > 0
        ),
        "minimum_profitability_sample_500_bets_250_fixtures": False,
        "positive_lower_roi_and_clv_bounds": False,
        "four_role_exact_hash_governance_pass": False,
    }
    model_promotion_eligible = gates_authorize(
        gates, MODEL_PROMOTION_GATES
    )
    recommendation_authorized = gates_authorize(
        gates, RECOMMENDATION_PROMOTION_GATES
    )
    return {
        "version": "recommendation_stacking_promotion_v1",
        "status": "BLOCKED" if not recommendation_authorized else "PASS",
        "purpose": (
            "development OOF evidence and fail-closed promotion authorization"
        ),
        "candidate_registry": [
            {
                "name": model,
                "price_independent": True,
                "searched_for_production": model not in (
                    "uniform", "elo_fixed",
                ),
                "role": (
                    "baseline"
                    if model in ("uniform", "elo_fixed")
                    else "production_candidate"
                ),
            }
            for model in models
        ],
        "search_grids": {
            "temperature": list(TEMPERATURES),
            "stack_elo_weights": list(STACK_WEIGHTS),
            "bootstrap_iterations": BOOTSTRAP_ITERATIONS,
            "multiplicity_control": "Holm family-wise correction at alpha 0.05",
        },
        "oof_rows": len(records),
        "oof_date_blocks": len({record["date"] for record in records}),
        "oof_outcome_counts": outcome_counts,
        "outer_folds": folds,
        "metrics": metrics,
        "calibration_comparisons": calibration_comparisons,
        "stack_comparisons": comparisons,
        "stack_fold_wins": stack_fold_wins,
        "gates": gates,
        "model_promotion_eligible": model_promotion_eligible,
        "recommendation_authorized": recommendation_authorized,
        "production_effect": (
            "none_current_predictions_recommendations_and_stakes_unchanged"
        ),
        "prospective_registry": {
            "path": str(REGISTRY.relative_to(ROOT)),
            "sha256": sha256(REGISTRY),
            "lock_path": str(REGISTRY_LOCK.relative_to(ROOT)),
            "lock_sha256": sha256(REGISTRY_LOCK),
            "historical_cohort_status": registry["cohorts"][0]["status"],
            "confirmatory_cohort_status": registry[
                "next_confirmatory_cohort"
            ]["status"],
        },
        "profitability_evidence": {
            "coverage_contract": str(COVERAGE.relative_to(ROOT)),
            "primary_validation_rows": coverage["primary_validation_rows"],
            "primary_validation_events": coverage[
                "primary_validation_events"
            ],
            "status": coverage["profitability_validation_status"],
        },
    }


def main() -> None:
    result = build()
    RESULT_OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "oof_rows": result["oof_rows"],
        "stack_log_loss": result["metrics"]["stack"]["log_loss"],
        "model_promotion_eligible": result["model_promotion_eligible"],
        "recommendation_authorized": result["recommendation_authorized"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
