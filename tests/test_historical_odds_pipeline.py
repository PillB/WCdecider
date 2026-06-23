import csv
import json
import hashlib
import re
from pathlib import Path

import pytest

import historical_odds_pipeline as pipeline
import model_championship
from scripts import merge_research_metrics


def test_public_legacy_inventory_is_explicitly_ineligible(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "PROXY_OUT", tmp_path / "proxy.csv")
    monkeypatch.setattr(pipeline, "COVERAGE_OUT", tmp_path / "coverage.json")
    monkeypatch.setattr(pipeline, "PROVENANCE_OUT", tmp_path / "provenance.txt")
    pipeline.build_public_proxy()
    rows = list(csv.DictReader((tmp_path / "proxy.csv").open()))
    coverage = json.loads((tmp_path / "coverage.json").read_text())
    assert len(rows) == 666
    assert len({row["event_id"] for row in rows}) == 222
    assert {row["evidence_class"] for row in rows} == {
        "legacy_proxy_unknown_timestamp"
    }
    assert {row["is_primary_validation_eligible"] for row in rows} == {"false"}
    assert coverage["primary_validation_rows"] == 0
    assert coverage["profitability_validation_status"] == (
        "blocked_no_timestamp_verified_closing_rows"
    )
    assert all(
        row["kickoff_utc"][4] == "-"
        and row["kickoff_utc"][7] == "-"
        and len(row["season"]) == 4
        for row in rows
    )
    first = (tmp_path / "proxy.csv").read_bytes()
    pipeline.build_public_proxy()
    assert (tmp_path / "proxy.csv").read_bytes() == first


def test_the_odds_api_normalizer_selects_latest_strictly_pre_kickoff(tmp_path):
    early = {
        "timestamp": "2022-11-20T14:00:00Z",
        "data": [{
            "id": "event-1", "sport_title": "FIFA World Cup",
            "commence_time": "2022-11-20T16:00:00Z",
            "home_team": "Qatar", "away_team": "Ecuador",
            "bookmakers": [{
                "key": "book-a", "last_update": "2022-11-20T13:59:00Z",
                "markets": [{"key": "h2h", "outcomes": [
                    {"name": "Qatar", "price": 3.2},
                    {"name": "Draw", "price": 3.1},
                    {"name": "Ecuador", "price": 2.3},
                ]}],
            }],
        }],
    }
    late = json.loads(json.dumps(early))
    late["timestamp"] = "2022-11-20T15:50:00Z"
    late["data"][0]["bookmakers"][0]["last_update"] = "2022-11-20T15:49:00Z"
    late["data"][0]["bookmakers"][0]["markets"][0]["outcomes"][2]["price"] = 2.4
    after = json.loads(json.dumps(late))
    after["timestamp"] = "2022-11-20T16:01:00Z"
    for name, payload in (("early.json", early), ("late.json", late),
                          ("after.json", after)):
        (tmp_path / name).write_text(json.dumps(payload))
    rows = pipeline.normalize_the_odds_api_payloads(tmp_path)
    assert len(rows) == 3
    assert {row["snapshot_time_utc"] for row in rows} == {
        "2022-11-20T15:50:00+00:00"
    }
    assert {row["is_primary_validation_eligible"] for row in rows} == {"true"}
    away = next(row for row in rows if row["selection"] == "away")
    assert away["decimal_odds"] == 2.4
    assert away["minutes_before_kickoff"] == pytest.approx(10.0)


def test_market_settlement_helpers_cover_pushes():
    assert pipeline.settle_1x2("draw", 1, 1) == "win"
    assert pipeline.settle_total("over", 2.0, 1, 1) == "push"
    assert pipeline.settle_total("under", 2.5, 1, 1) == "win"
    assert pipeline.settle_asian("home", -1.0, 2, 1) == "push"
    assert pipeline.settle_asian("away", -1.0, 2, 1) == "push"


def test_authenticated_acquisition_fails_closed_without_key(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("THE_ODDS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="THE_ODDS_API_KEY"):
        pipeline.acquire_the_odds_api_snapshot(
            "soccer_fifa_world_cup",
            "2022-11-20T15:50:00Z",
            "h2h,spreads,totals",
            "eu",
            tmp_path,
        )
    assert list(tmp_path.iterdir()) == []


def test_model_championship_is_nested_and_does_not_claim_profitability():
    result = model_championship.build()
    assert result["selection_rows"] + result["untouched_holdout_rows"] == (
        result["rows"]
    )
    assert result["untouched_holdout_rows"] > 0
    assert 0.0 <= result["tuned_stack"]["elo_weight"] <= 1.0
    assert result["profitability_status"] == (
        "blocked_no_timestamp_verified_closing_odds"
    )
    assert result["rival_500_percent_claim_status"].startswith("unverified")
    assert result["champion_vs_market_paired_bootstrap"]["iterations"] == 5000
    assert "temporal_graph_neural_network" in result["capacity_rejections"]
    outer = result["nested_outer_championship"]
    assert len(outer["folds"]) == 4
    assert outer["champion"] == result["champion"]
    assert all(
        fold["train_rows"] + fold["test_rows"] <= result["selection_rows"]
        for fold in outer["folds"]
    )
    assert all(
        fold["train_end"] < fold["test_start"]
        for fold in outer["folds"]
    )


def test_metrics_merge_reconciles_provenance_hash(tmp_path, monkeypatch):
    metrics = tmp_path / "metrics.json"
    championship = tmp_path / "championship.json"
    coverage = tmp_path / "coverage.json"
    provenance = tmp_path / "provenance.txt"
    metrics.write_text('{"pipeline_sha256":"x"}\n')
    championship.write_text('{"champion":"market"}\n')
    coverage.write_text('{"rows":0}\n')
    provenance.write_text(
        "- metrics.json: " + "0" * 64 + "\n", encoding="utf-8"
    )
    monkeypatch.setattr(merge_research_metrics, "METRICS", metrics)
    monkeypatch.setattr(merge_research_metrics, "CHAMPIONSHIP", championship)
    monkeypatch.setattr(merge_research_metrics, "COVERAGE", coverage)
    monkeypatch.setattr(merge_research_metrics, "PROVENANCE", provenance)
    merge_research_metrics.main()
    digest = hashlib.sha256(metrics.read_bytes()).hexdigest()
    assert f"- metrics.json: {digest}" in provenance.read_text()
