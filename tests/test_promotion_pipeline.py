"""Promotion-pipeline chronology, calibration, stacking, and safety tests."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import promotion_pipeline as promotion


ROOT = Path(__file__).resolve().parent.parent


def test_temperature_scaling_is_normalized_and_identity_at_one():
    probability = (0.62, 0.23, 0.15)
    assert promotion.temperature_scale(probability, 1.0) == pytest.approx(
        probability
    )
    softened = promotion.temperature_scale(probability, 1.5)
    assert sum(softened) == pytest.approx(1.0)
    assert softened[0] < probability[0]
    assert all(value > 0.0 for value in softened)


def test_stack_is_convex_and_rejects_invalid_temperature():
    left = (0.6, 0.25, 0.15)
    right = (0.3, 0.3, 0.4)
    assert promotion.blend(left, right, 1.0) == pytest.approx(left)
    assert promotion.blend(left, right, 0.0) == pytest.approx(right)
    assert sum(promotion.blend(left, right, 0.4)) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="positive"):
        promotion.temperature_scale(left, 0.0)


def test_authorization_requires_every_named_gate():
    all_true = {
        name: True for name in promotion.RECOMMENDATION_PROMOTION_GATES
    }
    assert promotion.gates_authorize(
        all_true, promotion.RECOMMENDATION_PROMOTION_GATES
    )
    for name in promotion.RECOMMENDATION_PROMOTION_GATES:
        failed = dict(all_true)
        failed[name] = False
        assert not promotion.gates_authorize(
            failed, promotion.RECOMMENDATION_PROMOTION_GATES
        )
    missing = dict(all_true)
    missing.pop(promotion.RECOMMENDATION_PROMOTION_GATES[0])
    assert not promotion.gates_authorize(
        missing, promotion.RECOMMENDATION_PROMOTION_GATES
    )


def test_generated_oof_predictions_are_strictly_chronological():
    rows = list(csv.DictReader(
        (ROOT / "promotion_oof_predictions.csv").open(
            newline="", encoding="utf-8"
        )
    ))
    assert len(rows) >= promotion.MIN_RESEARCH_OOF_ROWS
    assert all(row["train_end"] < row["date"] for row in rows)
    for row in rows:
        for model in (
            "uniform", "elo_fixed", "elo_tuned", "elo_calibrated",
            "poisson_tuned", "poisson_calibrated", "stack",
        ):
            probability = sum(
                float(row[f"{model}_p_{suffix}"])
                for suffix in ("a", "d", "b")
            )
            assert probability == pytest.approx(1.0)


def test_promotion_result_is_fail_closed_and_complete():
    result = json.loads(
        (ROOT / "recommendation_promotion_results.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["status"] == "BLOCKED"
    assert result["model_promotion_eligible"] is False
    assert result["recommendation_authorized"] is False
    assert result["production_effect"] == (
        "none_current_predictions_recommendations_and_stakes_unchanged"
    )
    assert result["profitability_evidence"]["primary_validation_rows"] == 0
    assert len(result["outer_folds"]) == 4
    assert all(
        fold["train_end"] < fold["test_start"]
        for fold in result["outer_folds"]
    )
    assert all(
        comparison["holm_adjusted_p_value"]
        >= comparison["one_sided_p_value"]
        for comparison in result["stack_comparisons"]
    )
    assert {item["baseline"] for item in result["stack_comparisons"]} == {
        "elo_tuned", "elo_calibrated", "poisson_tuned",
        "poisson_calibrated",
    }
    assert set(result["calibration_comparisons"]) == {
        "elo_temperature_vs_raw", "poisson_temperature_vs_raw",
    }
    assert all(
        set(result["metrics"][model]["classwise_brier"]) == {"A", "D", "B"}
        and set(
            result["metrics"][model]["calibration_in_the_large"]
        ) == {"A", "D", "B"}
        for model in result["metrics"]
    )
    assert result["gates"][
        "stack_is_nontrivial_distinct_model_in_every_fold"
    ] is False
    assert result["gates"][
        "new_confirmatory_holdout_sealed_before_predictions"
    ] is False
    assert result["gates"][
        "timestamp_qualified_profitability_rows_available"
    ] is False
    candidates = {
        item["name"]: item for item in result["candidate_registry"]
    }
    assert candidates["elo_fixed"]["role"] == "baseline"
    assert candidates["elo_fixed"]["searched_for_production"] is False


def test_registry_does_not_mislabel_existing_cohort_as_confirmatory():
    registry = json.loads(
        (ROOT / "governance" / "prospective_holdout_registry.json").read_text(
            encoding="utf-8"
        )
    )
    cohort = registry["cohorts"][0]
    assert cohort["status"].startswith("INVALIDATED_NON_CONFIRMATORY")
    assert cohort["confirmatory_eligible"] is False
    assert len(cohort["prediction_artifact_sha256"]) == 64
    assert registry["next_confirmatory_cohort"]["status"] == "NOT_YET_SEALED"


def test_frozen_registry_is_verified_and_never_rewritten(tmp_path):
    registry_path = tmp_path / "registry.json"
    lock_path = tmp_path / "registry.lock.json"
    predictions_path = tmp_path / "predictions.json"
    protocol_path = tmp_path / "protocol.md"
    predictions_path.write_text('{"prediction": 1}\n', encoding="utf-8")
    protocol_path.write_text("# frozen\n", encoding="utf-8")
    registry = {
        "cohorts": [{
            "prediction_artifact_sha256": promotion.sha256(predictions_path),
            "status": "SEALED_NON_CONFIRMATORY",
        }],
        "protocol_sha256": promotion.sha256(protocol_path),
    }
    registry_path.write_text(
        json.dumps(registry, sort_keys=True) + "\n", encoding="utf-8"
    )
    lock_path.write_text(
        json.dumps({
            "registry_sha256": promotion.sha256(registry_path),
        }, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    before = registry_path.read_bytes()
    assert promotion.verify_registry(
        registry_path, predictions_path, protocol_path, lock_path
    ) == registry
    assert registry_path.read_bytes() == before
    predictions_path.write_text('{"prediction": 2}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="prediction hash mismatch"):
        promotion.verify_registry(
            registry_path, predictions_path, protocol_path, lock_path
        )

    predictions_path.write_text('{"prediction": 1}\n', encoding="utf-8")
    mutated = dict(registry)
    mutated["cohorts"] = [dict(registry["cohorts"][0])]
    mutated["cohorts"][0]["model_version"] = "mutated"
    registry_path.write_text(
        json.dumps(mutated, sort_keys=True) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="lock hash mismatch"):
        promotion.verify_registry(
            registry_path, predictions_path, protocol_path, lock_path
        )


def test_ci_regenerates_promotion_evidence_before_release_pipeline():
    workflow = (
        ROOT / ".github" / "workflows" / "deploy.yml"
    ).read_text(encoding="utf-8")
    promotion_step = "python3 promotion_pipeline.py"
    release_step = "python3 wc_june22_27_pipeline.py"
    assert workflow.count(promotion_step) == 1
    assert workflow.index(promotion_step) < workflow.index(release_step)
