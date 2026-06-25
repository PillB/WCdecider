"""Integrity tests for the June 22–27 production pipeline."""

from __future__ import annotations

import csv
import hashlib
import inspect
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

import wc_june22_27_pipeline as pipeline
from scripts.generate_datapoint_audit import semantic_json_sha256

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


def test_elapsed_result_file_has_54_unique_matches_through_june24():
    rows = read_rows("wc_2026_results_through_june24.csv")
    assert len(rows) == 54
    keys = {(row["date"], row["team_a"], row["team_b"]) for row in rows}
    assert len(keys) == 54
    assert max(row["date"] for row in rows) == "2026-06-24"
    assert all(row["source_result"].startswith("https://") for row in rows)


def test_elapsed_fixture_probabilities_use_pre_result_elo_snapshots():
    results = read_rows("wc_2026_results_through_june24.csv")
    baseline = {
        row["team"]: float(row["elo"])
        for row in read_rows("wc_team_elo_baseline_june11.csv")
    }
    terminal, _, _, snapshots, contexts = pipeline.current_team_state(
        results, baseline
    )
    argentina_key = ("2026-06-22", "ARG", "AUT")
    portugal_key = ("2026-06-23", "POR", "UZB")
    assert snapshots[argentina_key] != (terminal["ARG"], terminal["AUT"])
    assert snapshots[portugal_key] != (terminal["POR"], terminal["UZB"])

    model_rows = {
        row["fixture_id"]: row
        for row in read_rows("wc_june22_27_model_dataset.csv")
    }
    for fixture_id, key in (
        ("2026-06-22-arg-aut", argentina_key),
        ("2026-06-23-por-uzb", portugal_key),
    ):
        assert float(model_rows[fixture_id]["elo_a_updated"]) == pytest.approx(
            snapshots[key][0], abs=0.001
        )
        assert float(model_rows[fixture_id]["elo_b_updated"]) == pytest.approx(
            snapshots[key][1], abs=0.001
        )
        assert int(model_rows[fixture_id]["form_games_a"]) == int(
            contexts[key]["form_a"]["games"]
        )
        assert int(model_rows[fixture_id]["form_games_b"]) == int(
            contexts[key]["form_b"]["games"]
        )
        assert int(model_rows[fixture_id]["form_gd_a"]) == int(
            contexts[key]["form_a"]["gf"] - contexts[key]["form_a"]["ga"]
        )
        assert int(model_rows[fixture_id]["form_gd_b"]) == int(
            contexts[key]["form_b"]["gf"] - contexts[key]["form_b"]["ga"]
        )


def test_updated_payload_separates_verified_elapsed_and_future_fixtures():
    payload = json.loads(
        (ROOT / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    statuses = [row["fixture_lifecycle_status"] for row in payload["predictions"]]
    assert statuses.count("elapsed_result_verified") == 14
    assert statuses.count("future") == 18
    for row in payload["predictions"]:
        rank_one = row["rank_one_comparison"]
        assert rank_one is not None
        assert rank_one["watchlist_label"]["en"]
        assert rank_one["watchlist_label"]["es"]
        assert rank_one["display"]["market"]["en"]
        assert rank_one["display"]["market"]["es"]
        assert rank_one["display"]["selection"]["en"]
        assert rank_one["display"]["selection"]["es"]
        if row["fixture_lifecycle_status"] == "future":
            expected_steps = (
                1 if row["freshness_status"].startswith("conditional_") else 6
            )
            assert len(rank_one["steps"]["en"]) == expected_steps
            assert len(rank_one["steps"]["es"]) == expected_steps
            assert rank_one["budget_simulation"]["stake"] == 0.0
            if expected_steps == 1:
                assert rank_one["steps"]["en"][0].startswith("STOP:")
            for step in rank_one["steps"]["en"]:
                assert "5.5 5.5" not in step
        else:
            assert rank_one["watchlist_status"] == "archived_result_no_bet"
            assert any("finished" in step for step in rank_one["steps"]["en"])


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
    rows = pipeline.load_historical()
    split = pipeline.date_block_split(rows, 0.85)
    assert config["selection_rows"] == split
    assert config["holdout_rows"] == len(rows) - split
    assert rows[split - 1].date < rows[split].date
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
        assert comparison["resampling_method"] == (
            "weighted_date_block_percentile_bootstrap"
        )
        assert comparison["block_count"] > 1
        assert comparison["ci_95_lower"] <= comparison["ci_95_upper"]
        assert comparison["numeric_tolerance"] == 1e-12
    assert (
        config["shadow_paired_bootstrap"]["over_2_5_brier"][
            "statistically_secure_improvement"
        ]
        is False
    )
    assert (
        config["shadow_paired_bootstrap"]["score_nll"][
            "statistically_secure_improvement"
        ]
        is False
    )


def test_temporal_folds_never_split_a_matchday():
    rows = pipeline.load_historical()
    selection = rows[: int(len(rows) * 0.85)]
    windows = pipeline.temporal_folds(selection)
    seen_dates = set()
    for window in windows:
        dates = {row.date for row in window}
        assert not seen_dates.intersection(dates)
        seen_dates.update(dates)


def test_production_holdout_split_never_divides_a_matchday():
    rows = pipeline.load_historical()
    split = pipeline.date_block_split(rows, 0.85)
    assert rows[split - 1].date < rows[split].date
    elo = pipeline.calibrate_elo(rows)
    score = pipeline.calibrate_score_model(rows)
    assert elo["selection_rows"] == score["selection_rows"] == split
    assert elo["holdout_rows"] == score["holdout_rows"] == len(rows) - split


def test_results_research_and_odds_are_cutoff_eligible():
    for row in pipeline.read_csv(pipeline.RESULTS_2026):
        assert datetime.fromisoformat(row["accessed_at"]) <= pipeline.RELEASE_AS_OF
        assert date.fromisoformat(row["date"]) <= pipeline.DATA_CUTOFF.date()

    fixtures = pipeline.read_csv(pipeline.FIXTURES)
    research = pipeline.load_research(fixtures)
    assert all(
        datetime.fromisoformat(row["accessed_at"]) <= pipeline.DATA_CUTOFF
        for row in research.values()
    )
    odds = pipeline.load_and_merge_odds(fixtures)
    for row in odds:
        captured = datetime.fromisoformat(
            row["capture_time"].replace(" -05:00", "-05:00")
        )
        assert captured <= pipeline.DATA_CUTOFF
        assert captured < datetime.fromisoformat(row["kickoff_local"])
        assert row["capture_time_derivation"] in {
            "verbatim_timezone_aware",
            "date_from_frozen_file_metadata:odds_june27.csv",
        }


def test_recommendation_probability_is_independent_of_quoted_market_probability():
    payload = json.loads(
        (ROOT / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    for fixture in payload["predictions"]:
        for comparison in fixture["market_comparisons"]:
            assert comparison["decision_probability_method"] == (
                "independent_structural_forecast_no_market_price_blend"
            )
            assert comparison["decision_model_weight"] == pytest.approx(1.0)
            assert comparison["decision_probability"] == pytest.approx(
                comparison["p_win"], abs=1e-6
            )
            assert comparison["decision_ev_pct"] == pytest.approx(
                comparison["ev_pct"], abs=0.011
            )


def test_research_mode_policy_is_gated_and_non_production():
    payload = json.loads((ROOT / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    metrics = json.loads((ROOT / "wc_june22_27_model_metrics.json").read_text(encoding="utf-8"))
    policy = metrics["research_mode_policy"]
    assert policy["toggle_available"] is True
    assert policy["selected_candidate"] == "dixon_coles_low_score_correction_shadow"
    assert policy["status"] == "research_gated_not_production"
    assert policy["production_recommendations_unchanged"] is True
    assert policy["promotion_requirements"]["minimum_timestamped_fixtures"] == 2000
    assert policy["promotion_requirements"]["minimum_temporal_edges_per_team"] == 30
    for row in payload["predictions"]:
        research = row["research_mode"]
        assert research["toggle_available"] is True
        assert research["default_state"] == "off_production_mode"
        assert research["selected_candidate"] == policy["selected_candidate"]
        assert research["promotion_status"] == "research_gated_not_production"
        assert research["production_recommendations_unchanged"] is True
        assert set(research["probabilities"]) == {"team_a_win", "draw", "team_b_win"}
        assert sum(research["probabilities"].values()) == pytest.approx(1.0, abs=2e-6)
        assert "common_markets" in research
        assert research["common_markets"]["policy_status"] == "experimental_non_actionable"
        assert research["top_recommendations_requested"] == 0
        assert research["top_recommendations_available"] == 0
        assert research["top_recommendations"] == []
        assert research["ranked_comparisons_requested"] == 4
        assert research["ranked_comparisons_available"] == len(
            research["ranked_comparisons"]
        )
        assert research["ranked_comparisons"]
        assert research["ranked_comparisons"][0]["decision_status"] == "ABSTAIN"
        assert "sensitivity analysis" in research["ranked_comparisons"][0]["why_ranked"]["en"]
        assert set(research["risk_profile_summary"]) == {
            "exploratory", "balanced", "cautious", "strict", "audit_only",
        }
        for recommendation in research["ranked_comparisons"]:
            assert set(recommendation["risk_lens"]) == {
                "exploratory", "balanced", "cautious", "strict", "audit_only",
            }
            assert all(
                lens["status"] in {"PASS", "HALT"}
                for lens in recommendation["risk_lens"].values()
            )
            assert recommendation["profitability_validation"] == (
                "not_validated_historical_market_odds"
            )
            for profile in pipeline.RISK_AVERSION_PROFILES:
                lens = recommendation["risk_lens"][profile["id"]]
                if recommendation["strength"] == "HALT":
                    assert lens["status"] == "HALT"
                if lens["status"] == "PASS":
                    assert recommendation["divergence_pp"] <= profile["max_divergence_pp"]
                    assert recommendation["stressed_ev_pct"] >= profile["min_stressed_ev_pct"]
                    assert recommendation["risk_grade"] in profile["allowed_risk_grades"]
                    if profile["id"] in {"cautious", "strict", "audit_only"}:
                        assert recommendation["price_gate_status"] == (
                            "at_or_above_model_fair_price"
                        )
        assert row["recommendation"] is None
        assert row["rank_one_comparison"]["decision_status"] == "ABSTAIN"
        assert set(row["risk_profile_summary"]) == {
            "exploratory", "balanced", "cautious", "strict", "audit_only",
        }
        assert len(row["risk_aversion_profiles"]) == 5
        profile_order = [
            "exploratory", "balanced", "cautious", "strict", "audit_only",
        ]
        pass_counts = [
            row["risk_profile_summary"][profile]["pass_count"]
            for profile in profile_order
        ]
        assert pass_counts == sorted(pass_counts, reverse=True)
        halt_loop = row["halt_improvement_loop"]
        assert halt_loop["automatic_resolution_allowed"] is False
        assert halt_loop["paired_candidates_compared"] == (
            row["supported_markets_evaluated"]
        )
        assert halt_loop["paired_production_halt_to_research_pass_count"] == len(
            halt_loop["paired_review_candidates"]
        )
        for candidate in halt_loop["paired_review_candidates"]:
            assert candidate["production_divergence_pp"] > 15.0 or (
                candidate["production_raw_ev_pct"] > 25.0
            )
            assert candidate["research_divergence_pp"] <= 15.0
            assert candidate["research_raw_ev_pct"] <= 25.0
        assert len(halt_loop["required_checks"]["en"]) == 4
        assert len(halt_loop["required_checks"]["es"]) == 4
        assert row["top_recommendations"] == []
        assert row["top_recommendations_requested"] == 0
        assert row["top_recommendations_available"] == 0
        for recommendation in row["ranked_comparisons"]:
            assert set(recommendation["risk_lens"]) == {
                "exploratory", "balanced", "cautious", "strict", "audit_only",
            }
            for profile in pipeline.RISK_AVERSION_PROFILES:
                lens = recommendation["risk_lens"][profile["id"]]
                if recommendation["strength"] == "HALT":
                    assert lens["status"] == "HALT"
                if lens["status"] == "PASS":
                    assert recommendation["divergence_pp"] <= profile["max_divergence_pp"]
                    assert recommendation["stressed_ev_pct"] >= profile["min_stressed_ev_pct"]
                    assert recommendation["risk_grade"] in profile["allowed_risk_grades"]
                    if profile["id"] in {"cautious", "strict", "audit_only"}:
                        assert recommendation["price_gate_status"] == (
                            "at_or_above_model_fair_price"
                        )


def test_research_shadow_stress_uses_dixon_coles_not_production_poisson():
    source = inspect.getsource(pipeline.build)
    assert "shadow_stress_matrices.append(" in source
    assert "dixon_coles_score_matrix(" in source
    assert "shadow_matrix, shadow_stress_matrices" in source


def test_risk_profiles_are_ordered_and_exploratory_is_distinct():
    payload = json.loads((ROOT / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    counts = {
        profile["id"]: 0 for profile in pipeline.RISK_AVERSION_PROFILES
    }
    for row in payload["predictions"]:
        for container in (row, row["research_mode"]):
            for recommendation in container["ranked_comparisons"]:
                for profile_id, lens in recommendation["risk_lens"].items():
                    counts[profile_id] += lens["status"] == "PASS"
    ordered = [counts[profile["id"]] for profile in pipeline.RISK_AVERSION_PROFILES]
    assert ordered == sorted(ordered, reverse=True)
    assert counts["exploratory"] > counts["balanced"]


def test_dataset_a_and_b_are_disjoint_by_competition():
    rows = pipeline.load_historical()
    # The persisted historical CSV contains only completed 2018/2022 World
    # Cups; load_historical appends the current batch's 40 completed 2026
    # fixtures from the cutoff-safe results source.
    finals = {"WC_2018_GROUP", "WC_2022_GROUP", "WC_2026_GROUP"}
    dataset_a = [row for row in rows if row.competition in finals]
    dataset_b = [row for row in rows if row.competition not in finals]
    assert len(dataset_a) == 150
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


def test_canonical_system_design_is_mandatory_and_cross_referenced():
    design = (ROOT / "WCDECIDER_SYSTEM_DESIGN.md").read_text(encoding="utf-8")
    assert "Fail-closed bankroll simulation" in design
    assert "Tooltip and responsive UI design" in design
    assert "Datapoint governance" in design
    assert "Deployment design" in design
    for filename in (
        "AGENT.md", "FUTURE_UPDATE_PROTOCOL.md",
        "PROJECT_UNDERSTANDING.md", "README.md", "ARCHITECTURE.md",
    ):
        assert "WCDECIDER_SYSTEM_DESIGN.md" in (
            ROOT / filename
        ).read_text(encoding="utf-8")


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
        for field in (
            "owner_evidence", "replication_1_evidence",
            "replication_2_evidence", "editor_evidence",
        ):
            assert row[field].startswith("reviews:")
            assert len(row[field].split(":")[1]) == 12


def test_datapoint_audit_stays_below_github_single_file_limit():
    manifest_path = ROOT / "wc_june22_27_datapoint_audit.csv"
    assert manifest_path.stat().st_size < 100_000_000


def test_research_recommendation_audit_uses_research_model_dependencies():
    rows = read_rows("wc_june22_27_datapoint_audit.csv")
    research_rows = [
        row for row in rows
        if "/research_mode/ranked_comparisons/" in row["json_pointer"]
    ]
    assert research_rows

    sample = research_rows[0]
    parts = sample["json_pointer"].strip("/").split("/")
    base = f"/predictions/{parts[1]}/research_mode"

    def datapoint_id(pointer: str) -> str:
        return hashlib.sha256(
            f"wc_june22_27_predictions.json:{pointer}".encode("utf-8")
        ).hexdigest()[:20]

    upstream = set(sample["upstream_datapoint_ids"].split(";"))
    expected = {
        datapoint_id(f"{base}/probabilities/team_a_win"),
        datapoint_id(f"{base}/probabilities/draw"),
        datapoint_id(f"{base}/probabilities/team_b_win"),
        datapoint_id(f"{base}/rho"),
    }
    production_team_a = datapoint_id(
        f"/predictions/{parts[1]}/probabilities/team_a_win"
    )
    assert expected <= upstream
    assert production_team_a not in upstream


def test_datapoint_audit_summary_matches_full_manifest_and_current_json():
    manifest_path = ROOT / "wc_june22_27_datapoint_audit.csv"
    summary_path = ROOT / "wc_june22_27_datapoint_audit_summary.json"
    assert manifest_path.exists()
    assert summary_path.exists()
    rows = read_rows(manifest_path.name)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected_paths = []
    for artifact in ("wc_june22_27_predictions.json", "wc_june22_27_model_metrics.json"):
        payload = json.loads((ROOT / artifact).read_text(encoding="utf-8"))
        expected_paths.extend(f"{artifact}:{pointer}" for pointer, _ in pipeline_json_leaves(payload))
    expected_paths = sorted(expected_paths)
    assert summary["final_status"] == "PASS"
    assert summary["blocked_rows"] == 0
    assert summary["audit_rows"] == len(rows)
    assert summary["expected_json_leaf_count"] == len(expected_paths)
    assert summary["artifact_bytes"] == manifest_path.stat().st_size
    assert summary["artifact_sha256"] == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert summary["predictions_sha256"] == hashlib.sha256(
        (ROOT / "wc_june22_27_predictions.json").read_bytes()
    ).hexdigest()
    assert summary["metrics_sha256"] == hashlib.sha256(
        (ROOT / "wc_june22_27_model_metrics.json").read_bytes()
    ).hexdigest()
    assert summary["expected_paths_sha256"] == hashlib.sha256(
        "\n".join(expected_paths).encode("utf-8")
    ).hexdigest()


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
    first_run = subprocess.run(
        [sys.executable, "-B", "scripts/generate_datapoint_audit.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    first = (ROOT / "wc_june22_27_datapoint_audit.csv").read_bytes()
    first_summary = (ROOT / "wc_june22_27_datapoint_audit_summary.json").read_bytes()
    second_run = subprocess.run(
        [sys.executable, "-B", "scripts/generate_datapoint_audit.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert (ROOT / "wc_june22_27_datapoint_audit.csv").read_bytes() == first
    assert (ROOT / "wc_june22_27_datapoint_audit_summary.json").read_bytes() == first_summary
    assert first_run.returncode == second_run.returncode == 0


def test_semantic_review_hash_ignores_only_sub_precision_float_noise():
    base = {"b": [0.12345678901234], "a": {"x": 1.0}}
    reordered_tiny_noise = {
        "a": {"x": 1.0},
        "b": [0.123456789012341],
    }
    material_change = {"a": {"x": 1.0}, "b": [0.12345679001234]}
    structural_change = {"a": {"x": 1.0}, "b": [0.12345678901234, 0.0]}
    assert semantic_json_sha256(base) == semantic_json_sha256(
        reordered_tiny_noise
    )
    assert semantic_json_sha256(base) != semantic_json_sha256(material_change)
    assert semantic_json_sha256(base) != semantic_json_sha256(
        structural_change
    )
    assert semantic_json_sha256({"x": -0.0}) == semantic_json_sha256(
        {"x": 0.0}
    )


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
        recommendation = row["rank_one_comparison"]
        assert row["recommendation"] is None
        assert row["top_recommendations"] == []
        assert row["top_recommendations_available"] == 0
        assert row["top_recommendations_requested"] == 0
        ranked = row["ranked_comparisons"]
        assert 1 <= len(ranked) <= 4
        assert row["ranked_comparisons_available"] == len(ranked)
        assert row["ranked_comparisons_requested"] == 4
        assert [item["rank"] for item in ranked] == list(
            range(1, len(ranked) + 1)
        )
        assert ranked[0] == recommendation
        keys = {
            (
                item["market_family"], item["selection_canonical"],
                item["line"],
            )
            for item in ranked
        }
        assert len(keys) == len(ranked)
        if len(ranked) < 4:
            assert row["ranked_comparisons_shortfall_reason"] == (
                "fewer_than_four_distinct_complete_sourced_events"
            )
        else:
            assert not row["ranked_comparisons_shortfall_reason"]
        for rank, item in enumerate(ranked, start=1):
            assert item["rank"] == rank
            assert item["decision_status"] == "ABSTAIN"
            assert item["actionability"]["actionable"] is False
            assert item["profitability_validation"] == (
                "not_validated_historical_market_odds"
            )
            assert item["source_image"]
            assert len(item["source_sha256"]) == 64
            assert item["price_gate_status"] in {
                "at_or_above_model_fair_price",
                "below_model_fair_price",
            }
            assert item["uncertainty"]["level"] in {"material", "high"}
            assert len(item["uncertainty"]["en"]) == 3
            assert len(item["uncertainty"]["es"]) == 3
            assert item["why_ranked"]["en"]
            assert item["why_ranked"]["es"]
            if row["fixture_lifecycle_status"] != "future":
                assert len(item["steps"]["en"]) == 2
                assert len(item["steps"]["es"]) == 2
            elif row["freshness_status"].startswith("conditional_"):
                assert len(item["steps"]["en"]) == 1
                assert item["steps"]["en"][0].startswith("STOP:")
                assert len(item["steps"]["es"]) == 1
            else:
                assert len(item["steps"]["en"]) == 6
                assert len(item["steps"]["es"]) == 6
            assert item["fair_odds"] > 1.0
            assert (
                item["p_win"] + item["p_push"] + item["p_loss"]
            ) == pytest.approx(1.0, abs=2e-6)
            reconstructed_ev = (
                item["p_win"] * (item["odds"] - 1.0) - item["p_loss"]
            ) * 100.0
            assert item["ev_pct"] == pytest.approx(
                reconstructed_ev, abs=0.011
            )
            reconstructed_fair = 1.0 + item["p_loss"] / item["p_win"]
            assert item["fair_odds"] == pytest.approx(
                reconstructed_fair, abs=0.0011
            )
        recommendations += 1
        assert recommendation["decision_status"] == "ABSTAIN"
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
        if recommendation["strength"] != "HALT":
            assert recommendation["selection_reason"] == (
                "highest_uncertainty_adjusted_expected_profit"
            )
        else:
            assert recommendation["selection_reason"] == (
                "all_model_edges_halted_select_highest_market_probability"
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
    assert payload["model"]["expanded_market_policy"]["recommendations_required"] == 0
    plan = payload["bankroll_simulation"]
    assert plan["currency"] == "PEN"
    assert plan["budget_per_app"] == 100.0
    app_counts = {"Betano": 0, "Betsson": 0}
    app_stakes = {"Betano": 0.0, "Betsson": 0.0}
    for row in payload["predictions"]:
        recommendation = row["rank_one_comparison"]
        assert row["recommendation"] is None
        budget = recommendation["budget_simulation"]
        app = recommendation["app"]
        app_counts[app] += 1
        app_stakes[app] += budget["stake"]
        assert budget["stake"] == 0.0
        assert budget["gross_return_if_full_win"] == pytest.approx(
            budget["stake"] * recommendation["odds"], abs=0.011
        )
        assert budget["steps"]["en"] == []
        assert budget["steps"]["es"] == []
        assert budget["price_gate_status"] in {
            "at_or_above_model_fair_price",
            "below_model_fair_price_forced_coverage_only",
        }
    assert sum(app_counts.values()) == 32
    assert set(app_counts) == {"Betano", "Betsson"}
    assert app_stakes["Betano"] == pytest.approx(0.0)
    assert app_stakes["Betsson"] == pytest.approx(0.0)
    assert plan["apps"]["Betano"]["total_stake"] == 0.0
    assert plan["apps"]["Betsson"]["total_stake"] == 0.0
    assert plan["apps"]["Betano"]["unallocated_budget"] == 100.0
    assert plan["apps"]["Betsson"]["unallocated_budget"] == 100.0


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
        assert row["recommendation"] is None
        assert row["rank_one_comparison"]["decision_status"] == "ABSTAIN"
        assert row["rank_one_comparison"]["budget_simulation"]["stake"] == 0.0


def test_asian_complete_groups_have_one_reciprocal_pair_only():
    fixtures = pipeline.read_csv(pipeline.FIXTURES)
    odds = pipeline.load_and_merge_odds(fixtures)
    groups = {}
    for row in odds:
        if (
            row["market_family"] == "asian_handicap"
            and row["is_complete_market"] == "true"
        ):
            groups.setdefault(row["market_group_id"], []).append(row)
    assert groups
    for rows in groups.values():
        assert len(rows) == 2
        assert {row["selection_canonical"] for row in rows} == {
            "home", "away",
        }
        selected_lines = sorted(
            float(row["handicap_selected_line"]) for row in rows
        )
        assert selected_lines[0] == pytest.approx(-selected_lines[1])
        assert len({
            float(row["handicap_home_line"]) for row in rows
        }) == 1


def test_combo_markets_are_source_only_until_contract_is_validated():
    payload = json.loads(
        (ROOT / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    assert not any(
        comparison["market_family"] == "handicap_total_combo"
        for row in payload["predictions"]
        for comparison in row["market_comparisons"]
    )
