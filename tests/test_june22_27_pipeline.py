"""Integrity tests for the June 22–27 production pipeline."""

from __future__ import annotations

import csv
import inspect
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
