"""Integrity tests for the June 22–27 production pipeline."""

from __future__ import annotations

import csv
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

import wc_june22_27_pipeline as pipeline

ROOT = Path(__file__).resolve().parent.parent


def read_rows(name: str):
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_canonical_fixture_file_has_32_unique_timezone_aware_rows():
    rows = read_rows("wc_2026_matches_june_22-27.csv")
    assert len(rows) == 32
    assert len({row["fixture_id"] for row in rows}) == 32
    assert all("T" in row["kickoff_lima"] and row["kickoff_lima"].endswith("-05:00") for row in rows)
    assert all(row["kickoff_utc"].endswith("Z") for row in rows)


def test_elapsed_result_file_has_40_unique_matches_through_june21():
    rows = read_rows("wc_2026_results_through_june21.csv")
    assert len(rows) == 40
    keys = {(row["date"], row["team_a"], row["team_b"]) for row in rows}
    assert len(keys) == 40
    assert max(row["date"] for row in rows) == "2026-06-21"
    assert all(row["source_result"].startswith("https://") for row in rows)


def test_pipeline_source_does_not_embed_current_odds_or_extract_prose_targets():
    source = inspect.getsource(pipeline)
    assert "prior_odds" not in source
    assert "documented_base_target" not in source
    assert "extract_documented" not in source


def test_three_way_probabilities_are_normalized_and_monotonic():
    equal = pipeline.three_way_elo(1800, 1800, 400, 0.18, 0.10)
    favorite = pipeline.three_way_elo(2000, 1700, 400, 0.18, 0.10)
    assert sum(equal) == pytest.approx(1.0)
    assert sum(favorite) == pytest.approx(1.0)
    assert favorite[0] > equal[0]
    assert favorite[2] < equal[2]


def test_asian_quarter_lines_split_into_adjacent_half_lines():
    assert pipeline.split_quarter_line(-1.25) == (-1.5, -1.0)
    assert pipeline.split_quarter_line(0.75) == (0.5, 1.0)
    assert pipeline.split_quarter_line(-1.0) == (-1.0,)


def test_asian_quarter_settlement_has_half_win_and_half_push():
    assert pipeline.settle_asian_handicap(1, -0.75, 2.0) == pytest.approx(
        (0.5, 0.5, 0.0, 0.5)
    )
    assert pipeline.settle_asian_handicap(0, 0.25, 2.0) == pytest.approx(
        (0.5, 0.5, 0.0, 0.5)
    )
    assert pipeline.settle_asian_handicap(-1, 0.75, 2.0) == pytest.approx(
        (0.0, 0.5, 0.5, -0.5)
    )


def test_handicap_total_parser_requires_two_explicit_lines():
    assert pipeline.parse_handicap_total_market(
        "-1.5 Handicap + Total Goals 2.5"
    ) == (-1.5, 2.5)
    assert pipeline.parse_handicap_total_market("Price Boost") is None


def test_expanded_market_schema_has_only_complete_supported_groups():
    fixtures = read_rows("wc_2026_matches_june_22-27.csv")
    rows = pipeline.load_and_merge_odds(fixtures)
    supported = {
        "1x2", "total_goals", "btts", "double_chance",
        "asian_handicap", "handicap_total_combo",
    }
    groups = {}
    for row in rows:
        if row["market_group_id"]:
            groups.setdefault(row["market_group_id"], []).append(row)
    assert sum(row["market_family"] == "total_goals" for row in rows) == 224
    assert sum(row["market_family"] == "btts" for row in rows) == 36
    assert sum(row["market_family"] == "asian_handicap" for row in rows) == 110
    assert sum(row["market_family"] == "handicap_total_combo" for row in rows) == 48
    for group in groups.values():
        family = group[0]["market_family"]
        if family not in supported or group[0]["is_complete_market"] != "true":
            continue
        selections = {row["selection_canonical"] for row in group}
        if family == "total_goals":
            assert selections == {"over", "under"}
        elif family == "btts":
            assert selections == {"yes", "no"}
        elif family == "asian_handicap":
            assert selections == {"home", "away"}
            lines = sorted(float(row["handicap_selected_line"]) for row in group)
            assert lines[0] == pytest.approx(-lines[-1])
        elif family == "handicap_total_combo":
            assert selections == {"home_over", "home_under", "away_over", "away_under"}


def test_score_market_calibration_is_chronological_and_non_actionable():
    config = pipeline.calibrate_score_model(pipeline.load_historical())
    assert config["selection_rows"] == 215
    assert config["holdout_rows"] == 38
    assert config["production_model"] == "tuned_elo_independent_poisson"
    assert config["shadow_model"] == "dixon_coles_low_score_correction"
    assert config["policy_status"].startswith("experimental_non_actionable")
    assert config["production_holdout"]["score_nll"] > 0
    assert config["production_holdout"]["over_2_5_brier"] < 1
    assert config["production_holdout"]["btts_brier"] < 1
    baselines = config["holdout_selection_rate_baselines"]
    assert 0.0 < baselines["selection_over_2_5_rate"] < 1.0
    assert 0.0 < baselines["selection_btts_rate"] < 1.0
    for comparison in config["shadow_paired_bootstrap"].values():
        assert comparison["iterations"] == 2000
        assert comparison["ci_95_lower"] <= comparison["ci_95_upper"]
    assert (
        config["shadow_paired_bootstrap"]["score_nll"][
            "statistically_secure_improvement"
        ]
        is False
    )


def test_dataset_a_and_b_are_disjoint_by_competition():
    rows = pipeline.load_historical()
    finals = {"WC_2018_GROUP", "WC_2022_GROUP", "WC_2026_GROUP"}
    dataset_a = [row for row in rows if row.competition in finals]
    dataset_b = [row for row in rows if row.competition not in finals]
    assert len(dataset_a) == 132
    assert len(dataset_b) == 121
    assert not ({id(row) for row in dataset_a} & {id(row) for row in dataset_b})


def test_all_odds_rows_reference_real_images_when_extractions_are_complete():
    if not all(path.exists() for path in pipeline.ODDS_PARTS):
        pytest.skip("Exact odds extraction workers are still running")
    fixtures = read_rows("wc_2026_matches_june_22-27.csv")
    rows = pipeline.load_and_merge_odds(fixtures)
    assert rows
    assert {row["app"] for row in rows} <= {"Betano", "Betsson"}
    assert all((ROOT / "Screenshots" / row["source_image"]).exists() for row in rows)
    assert all(len(row["source_sha256"]) == 64 for row in rows)
    manifest = pipeline.screenshot_manifest(rows)
    assert len(manifest) == 216
    assert len({row["source_image"] for row in manifest}) == 216


def test_research_tables_cover_every_fixture_with_direct_urls():
    if not all(path.exists() for path in pipeline.RESEARCH_PARTS):
        pytest.skip("Research workers are still running")
    fixtures = read_rows("wc_2026_matches_june_22-27.csv")
    rows = pipeline.load_research(fixtures)
    assert len(rows) == 32
    assert all("https://" in row["source_urls"] for row in rows.values())
    assert all(row["confidence"] for row in rows.values())


def test_ci_builds_site_before_browser_tests():
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    build_test_job = workflow.split("\n  deploy:", 1)[0]
    assert "actions/configure-pages@v5" in build_test_job
    assert "actions/upload-pages-artifact@v4" in build_test_job
    assert build_test_job.count("scripts/build_site.py") == 1
    assert build_test_job.index("- name: Generate field-level subagent audit manifest") < build_test_job.index(
        "- name: Generate JSON-driven report"
    )
    assert build_test_job.index("- name: Generate JSON-driven report") < build_test_job.index(
        "- name: Build exact site artifact"
    )
    assert build_test_job.index("- name: Build exact site artifact") < build_test_job.index(
        "- name: Run full pytest matrix"
    )
    assert build_test_job.index("- name: Run full pytest matrix") < build_test_job.index(
        "- name: Upload exact tested Pages artifact"
    )
    assert "needs: build-test" in workflow


def test_datapoint_audit_covers_all_json_leaves_with_distinct_passed_reviewers():
    manifest_path = ROOT / "wc_june22_27_datapoint_audit.csv"
    assert manifest_path.exists()
    rows = read_rows(manifest_path.name)
    assert rows

    expected = set()
    for artifact in ("wc_june22_27_predictions.json", "wc_june22_27_model_metrics.json"):
        payload = json.loads((ROOT / artifact).read_text(encoding="utf-8"))
        expected.update((artifact, pointer) for pointer, _ in pipeline_json_leaves(payload))
    actual = {(row["output_artifact"], row["json_pointer"]) for row in rows}
    assert actual == expected

    for row in rows:
        reviewer_ids = [
            row["owner_subagent_id"], row["replication_1_subagent_id"],
            row["replication_2_subagent_id"], row["editor_subagent_id"],
        ]
        assert len(set(reviewer_ids)) == 4
        assert row["owner_result"] == "PASS"
        assert row["replication_1_status"] == "PASS"
        assert row["replication_2_status"] == "PASS"
        assert row["editor_status"] == "PASS"
        assert row["final_status"] == "PASS"
        assert len(row["value_sha256"]) == 64
        assert len(row["source_sha256"]) == 64
        assert len(row["mission_sha256"]) == 64


def pipeline_json_leaves(value, pointer=""):
    if isinstance(value, dict):
        for key in sorted(value):
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from pipeline_json_leaves(value[key], f"{pointer}/{escaped}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from pipeline_json_leaves(item, f"{pointer}/{index}")
    else:
        yield pointer or "/", value


def test_audit_generator_is_deterministic():
    subprocess.run(
        [sys.executable, "-B", "scripts/generate_datapoint_audit.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    first = (ROOT / "wc_june22_27_datapoint_audit.csv").read_bytes()
    subprocess.run(
        [sys.executable, "-B", "scripts/generate_datapoint_audit.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert (ROOT / "wc_june22_27_datapoint_audit.csv").read_bytes() == first


def test_expanded_predictions_cover_all_fixtures_without_fabricated_prices():
    payload = json.loads(
        (ROOT / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    assert len(payload["predictions"]) == 32
    priced = 0
    recommendations = 0
    for row in payload["predictions"]:
        explanations = row["metric_explanations"]
        assert set(explanations) == {
            "team_a_win", "draw", "team_b_win",
            "expected_goals_team_a", "expected_goals_team_b",
            "over_2_5", "under_2_5", "btts_yes", "btts_no",
            "home_minus_0_5",
        }
        for explanation in explanations.values():
            assert set(explanation) == {"en", "es"}
            for language in ("en", "es"):
                assert set(explanation[language]) == {
                    "title", "category_meaning", "number_meaning",
                    "what_you_can_do",
                }
                assert all(explanation[language].values())
        assert f'{row["expected_goals"]["team_b"]:.2f}' in (
            explanations["expected_goals_team_b"]["en"]["number_meaning"]
        )
        assert row["common_markets"]["policy_status"] == "experimental_non_actionable"
        assert len(row["common_markets"]["totals"]) == 6
        assert len(row["common_markets"]["asian_handicap"]) == 7
        assert len(row["common_markets"]["total_goals_buckets"]) == 6
        assert len(row["common_markets"]["top_correct_scores"]) == 5
        assert sum(
            bucket["probability"]
            for bucket in row["common_markets"]["total_goals_buckets"]
        ) == pytest.approx(1.0, abs=6e-6)
        double_chance = row["common_markets"]["double_chance"]
        assert 0.0 < double_chance["home_or_draw_probability"] < 1.0
        assert 0.0 < double_chance["home_or_away_probability"] < 1.0
        assert 0.0 < double_chance["draw_or_away_probability"] < 1.0
        assert row["score_market_model"]["policy_status"] == "experimental_non_actionable"
        for comparison in row["market_comparisons"]:
            assert comparison["source_image"]
            assert len(comparison["source_sha256"]) == 64
            assert comparison["policy_status"] == "experimental_non_actionable"
        if any(row["expanded_price_coverage"].values()):
            priced += 1
        recommendation = row["recommendation"]
        assert recommendation is not None
        recommendations += 1
        assert recommendation["decision_status"] == "BEST_AVAILABLE"
        assert recommendation["risk_grade"] in {"A", "B", "C", "D"}
        assert recommendation["profitability_validation"] == (
            "not_validated_historical_market_odds"
        )
        assert recommendation["source_image"]
        assert len(recommendation["source_sha256"]) == 64
        assert recommendation["fair_odds"] > 1.0
        matching = [
            comparison for comparison in row["market_comparisons"]
            if comparison["app"] == recommendation["app"]
            and comparison["source_image"] == recommendation["source_image"]
            and comparison["market_family"] == recommendation["market_family"]
            and comparison["market_original"] == recommendation["market_original"]
            and comparison["selection_original"] == recommendation["selection_original"]
        ]
        assert matching
        selected_comparison = next(
            comparison for comparison in matching
            if comparison["recommendation_utility"]
            == recommendation["recommendation_utility"]
        )
        non_halt = [
            comparison for comparison in row["market_comparisons"]
            if comparison["strength"] != "HALT"
        ]
        if non_halt:
            assert recommendation["selection_reason"] == (
                "highest_uncertainty_adjusted_expected_profit"
            )
            assert selected_comparison["recommendation_utility"] == max(
                comparison["recommendation_utility"]
                for comparison in non_halt
            )
        else:
            assert recommendation["selection_reason"] == (
                "all_model_edges_halted_select_highest_market_probability"
            )
            assert selected_comparison["market_probability"] == max(
                comparison["market_probability"]
                for comparison in row["market_comparisons"]
            )
        common_dc = row["common_markets"]["double_chance"]
        for comparison in row["market_comparisons"]:
            if comparison["market_family"] != "double_chance":
                continue
            expected = {
                "AD": common_dc["home_or_draw_probability"],
                "AB": common_dc["home_or_away_probability"],
                "DB": common_dc["draw_or_away_probability"],
            }[comparison["selection_canonical"]]
            assert comparison["p_win"] == pytest.approx(expected, abs=2e-6)
    assert priced == 12
    assert recommendations == 32
    assert payload["model"]["expanded_market_policy"]["priced_fixtures"] == 12
    assert payload["model"]["expanded_market_policy"]["recommendations_required"] == 32


def test_full_build_emits_exactly_32_predictions_when_inputs_are_complete(tmp_path, monkeypatch):
    if not all(path.exists() for path in pipeline.ODDS_PARTS):
        pytest.skip("Exact odds extraction workers are still running")
    monkeypatch.setattr(pipeline, "DATASET_A_OUT", tmp_path / "a.csv")
    monkeypatch.setattr(pipeline, "DATASET_B_OUT", tmp_path / "b.csv")
    monkeypatch.setattr(pipeline, "MODEL_DATA_OUT", tmp_path / "model.csv")
    monkeypatch.setattr(pipeline, "ODDS_OUT", tmp_path / "odds.csv")
    monkeypatch.setattr(pipeline, "PREDICTIONS_OUT", tmp_path / "predictions.json")
    monkeypatch.setattr(pipeline, "METRICS_OUT", tmp_path / "metrics.json")
    monkeypatch.setattr(pipeline, "PROVENANCE_OUT", tmp_path / "provenance.txt")
    monkeypatch.setattr(pipeline, "SCREENSHOT_MANIFEST_OUT", tmp_path / "manifest.csv")
    monkeypatch.setattr(pipeline, "RESEARCH_OUT", tmp_path / "research.csv")
    payload = pipeline.build()
    assert len(payload["predictions"]) == 32
    assert len({row["fixture_id"] for row in payload["predictions"]}) == 32
    for row in payload["predictions"]:
        probs = row["probabilities"]
        assert sum(probs.values()) == pytest.approx(1.0, abs=2e-6)
