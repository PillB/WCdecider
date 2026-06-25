import csv
import json
import hashlib
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

import historical_odds_pipeline as pipeline
import model_championship
import wc_backtest_historical_loader as historical_loader
from wc_june22_27_pipeline import HistoricalRow
from scripts import merge_research_metrics


@pytest.mark.parametrize(
    "competition,rows",
    [
        ("WC_2018_GROUP", historical_loader.WC_2018_GROUP),
        ("WC_2022_GROUP", historical_loader.WC_2022_GROUP),
    ],
)
def test_world_cup_group_contract_is_complete_and_pair_unique(
    competition, rows,
):
    assert len(rows) == 48
    pairs = [tuple(sorted((row[1], row[2]))) for row in rows]
    assert len(pairs) == len(set(pairs))
    appearances = {}
    for row in rows:
        for team in (row[1], row[2]):
            appearances[team] = appearances.get(team, 0) + 1
    assert len(appearances) == 32
    assert set(appearances.values()) == {3}
    built = historical_loader.build_wc_rows(
        competition, rows, "test canonical contract"
    )
    assert len(built) == 48
    assert len({row.match_id for row in built}) == 48


def test_repaired_historical_dataset_is_globally_chronological_and_has_no_obsolete_2026():
    rows = list(csv.DictReader(
        (pipeline.ROOT / "wc_backtest_historical_dataset.csv").open()
    ))
    dates = [
        historical_loader.parse_date(row["date"]) for row in rows
    ]
    assert dates == sorted(dates)
    assert not any(
        row["competition"] == "WC_2026_GROUP" for row in rows
    )


def test_public_legacy_inventory_is_explicitly_ineligible(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "PROXY_OUT", tmp_path / "proxy.csv")
    monkeypatch.setattr(pipeline, "COVERAGE_OUT", tmp_path / "coverage.json")
    monkeypatch.setattr(pipeline, "PROVENANCE_OUT", tmp_path / "provenance.txt")
    pipeline.build_public_proxy()
    rows = list(csv.DictReader((tmp_path / "proxy.csv").open()))
    coverage = json.loads((tmp_path / "coverage.json").read_text())
    historical_rows = list(csv.DictReader(
        (pipeline.ROOT / "wc_backtest_historical_dataset.csv").open()
    ))
    assert len(rows) == 3 * len(historical_rows)
    assert len({row["event_id"] for row in rows}) == len(historical_rows)
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


def test_distant_timestamped_snapshot_is_not_mislabeled_as_close(tmp_path):
    payload = {
        "timestamp": "2022-11-19T00:00:00Z",
        "data": [{
            "id": "event-distant", "sport_title": "FIFA World Cup",
            "commence_time": "2022-11-20T16:00:00Z",
            "home_team": "Qatar", "away_team": "Ecuador",
            "bookmakers": [{
                "key": "book-a", "last_update": "2022-11-19T00:00:00Z",
                "markets": [{"key": "h2h", "outcomes": [
                    {"name": "Qatar", "price": 3.2},
                    {"name": "Draw", "price": 3.1},
                    {"name": "Ecuador", "price": 2.3},
                ]}],
            }],
        }],
    }
    (tmp_path / "snapshot.json").write_text(json.dumps(payload))
    rows = pipeline.normalize_the_odds_api_payloads(tmp_path)
    assert {row["evidence_class"] for row in rows} == {
        "timestamp_verified_pre_event_snapshot"
    }
    assert {row["is_primary_validation_eligible"] for row in rows} == {"false"}


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


def test_football_data_contract_is_frozen_and_named_bookmaker_only():
    sources = pipeline.football_data_source_contract()
    assert len(sources) == 25
    assert len({source["source_id"] for source in sources}) == 25
    assert {source["competition"] for source in sources} == set(
        pipeline.FOOTBALL_DATA_COMPETITIONS.values()
    )
    assert all(source["url"].startswith("https://www.football-data.co.uk/") for source in sources)
    assert set(pipeline.FOOTBALL_DATA_BOOKMAKERS) == {
        "bet365", "pinnacle", "betfair_exchange",
    }


def test_football_data_normalization_is_deterministic_and_ineligible():
    first = pipeline.normalize_football_data()
    second = pipeline.normalize_football_data()
    assert first == second
    assert len(first) == 142349
    assert len({row["event_id"] for row in first}) == 8908
    assert {row["bookmaker"] for row in first} == {
        "bet365", "pinnacle", "betfair_exchange",
    }
    assert {row["market_family"] for row in first} == {
        "1x2", "total_goals", "asian_handicap",
    }
    assert {row["evidence_class"] for row in first} == {
        "published_close_without_quote_timestamp"
    }
    assert {row["is_primary_validation_eligible"] for row in first} == {"false"}
    assert all(float(row["decimal_odds"]) > 1.0 for row in first)
    assert all(row["settlement"] in {
        "win", "loss", "push", "half_loss_half_push", "half_push_half_win",
    } for row in first)


def test_football_data_complete_market_and_line_invariants():
    rows = pipeline.normalize_football_data()
    groups = {}
    for row in rows:
        key = (
            row["event_id"], row["bookmaker"], row["market_family"], row["line"],
        )
        groups.setdefault(key, set()).add(row["selection"])
    expected = {
        "1x2": {"home", "draw", "away"},
        "total_goals": {"over", "under"},
        "asian_handicap": {"home", "away"},
    }
    complete = 0
    for key, selections in groups.items():
        if selections == expected[key[2]]:
            complete += 1
        else:
            assert selections < expected[key[2]]
    assert complete > 15000
    assert all(
        row["line"] == 2.5
        for row in rows if row["market_family"] == "total_goals"
    )


def test_quarter_handicap_and_timezone_conversion():
    assert pipeline.settle_asian("home", -0.25, 1, 1) == "half_loss_half_push"
    assert pipeline.settle_asian("away", -0.25, 1, 1) == "half_push_half_win"
    london = pipeline.parse_football_data_date("16/08/2024", "E0")
    london = london.replace(hour=20).astimezone(pipeline.timezone.utc)
    assert london.isoformat() == "2024-08-16T19:00:00+00:00"
    germany_feed_time = pipeline.parse_football_data_date("21/10/2022", "D1")
    germany_feed_time = germany_feed_time.replace(
        hour=19, minute=30
    ).astimezone(pipeline.timezone.utc)
    assert germany_feed_time.isoformat() == "2022-10-21T18:30:00+00:00"


def test_restricted_api_samples_reconcile_to_public_fixture_ids():
    if not any(pipeline.THE_ODDS_API_SAMPLE_RAW.glob("*.json")):
        pytest.skip("Restricted provider samples are intentionally absent")
    football_ids = {
        row["event_id"] for row in pipeline.normalize_football_data()
    }
    api_ids = {
        row["event_id"] for row in pipeline.normalize_the_odds_api_payloads(
            pipeline.THE_ODDS_API_SAMPLE_RAW
        )
    }
    assert len(api_ids) == 38
    assert api_ids <= football_ids


def test_canonical_multi_provider_coverage_and_claim_boundary(tmp_path, monkeypatch):
    out = tmp_path / "canonical.csv"
    coverage_path = tmp_path / "coverage.json"
    provenance = tmp_path / "provenance.txt"
    manifest = tmp_path / "sources.json"
    sample_out = tmp_path / "samples.csv"
    manifest.write_text(
        (pipeline.ROOT / "historical_closing_odds_sources.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline, "COMBINED_OUT", out)
    monkeypatch.setattr(pipeline, "COMBINED_COVERAGE", coverage_path)
    monkeypatch.setattr(pipeline, "COMBINED_PROVENANCE", provenance)
    monkeypatch.setattr(pipeline, "CANONICAL_MANIFEST", manifest)
    monkeypatch.setattr(pipeline, "THE_ODDS_API_SAMPLE_OUT", sample_out)
    summary = pipeline.build_canonical_dataset()
    assert summary["rows"] == 142349
    assert summary["events"] == 8908
    assert summary["by_provider"] == {"Football-Data": 142349}
    assert summary["by_evidence_class"] == {
        "published_close_without_quote_timestamp": 142349,
    }
    assert summary["restricted_validation_sources"]["rows"] == 1311
    assert summary["restricted_validation_sources"]["events"] == 38
    assert summary["restricted_validation_sources"]["included_in_public_csv"] is False
    assert summary["primary_validation_rows"] == 0
    assert summary["profitability_validation_status"] == (
        "blocked_no_timestamp_verified_closing_rows"
    )
    assert out.stat().st_size < 100_000_000
    text = provenance.read_text()
    assert "BTTS closing prices are unavailable" in text
    assert "excluded from the public CSV" in text
    assert "systematically outdated since 2025-07-23" in text
    assert "does not yet authorize ROI/CLV/profitability claims" in text


def test_public_build_preserves_restricted_summary_without_private_payloads(
    tmp_path, monkeypatch
):
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        (pipeline.ROOT / "historical_closing_odds_sources.json").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline, "THE_ODDS_API_SAMPLE_RAW", tmp_path / "absent")
    monkeypatch.setattr(pipeline, "CANONICAL_MANIFEST", manifest)
    monkeypatch.setattr(pipeline, "COMBINED_OUT", tmp_path / "canonical.csv")
    monkeypatch.setattr(pipeline, "COMBINED_COVERAGE", tmp_path / "coverage.json")
    monkeypatch.setattr(pipeline, "COMBINED_PROVENANCE", tmp_path / "provenance.txt")
    summary = pipeline.build_canonical_dataset()
    assert summary["restricted_validation_sources"]["rows"] == 1311
    assert summary["restricted_validation_sources"]["events"] == 38
    rebuilt = json.loads(manifest.read_text())
    assert len(rebuilt["restricted_validation_sources"]) == 2
    assert rebuilt["restricted_validation_summary"] == {
        "rows": 1311, "events": 38,
    }


def historical_row(
    day, *, weight=1.0, outcome="A", team_a="A", team_b="B",
):
    return HistoricalRow(
        date=day,
        competition="TEST",
        weight=weight,
        team_a=team_a,
        team_b=team_b,
        elo_a=1500.0,
        elo_b=1500.0,
        outcome=outcome,
        score_a=1 if outcome == "A" else 0,
        score_b=1 if outcome == "B" else 0,
        odds_a=2.0,
        odds_d=3.0,
        odds_b=4.0,
    )


def test_inner_rolling_windows_keep_each_date_block_intact():
    rows = []
    first = date(2020, 1, 1)
    for offset in range(20):
        rows.extend([
            historical_row(first + timedelta(days=offset)),
            historical_row(first + timedelta(days=offset)),
        ])
    for start, end in model_championship.rolling_windows(rows):
        assert start == 0 or rows[start - 1].date < rows[start].date
        assert end == len(rows) or rows[end - 1].date < rows[end].date


def test_weighted_paired_bootstrap_resamples_fixture_date_blocks():
    rows = [
        historical_row(date(2020, 1, 1), weight=9.0, outcome="A"),
        historical_row(date(2020, 1, 1), weight=1.0, outcome="B"),
        historical_row(date(2020, 1, 2), weight=1.0, outcome="A"),
    ]
    challenger = lambda row: (0.8, 0.1, 0.1)
    market = lambda row: (0.2, 0.1, 0.7)
    result = model_championship.paired_bootstrap(
        rows, challenger, market, iterations=200,
    )
    expected = sum(
        row.weight * (
            model_championship.log_loss(challenger(row), row.outcome)
            - model_championship.log_loss(market(row), row.outcome)
        )
        for row in rows
    ) / sum(row.weight for row in rows)
    assert result["challenger_minus_market_log_loss"] == pytest.approx(expected)
    assert result["block_count"] == 2
    assert result["method"] == "weighted_paired_bootstrap_by_fixture_date"


def test_market_benchmark_winner_is_compared_with_best_non_market_challenger():
    means = {
        "market_devigged_proxy": {
            "mean_log_loss": 0.9, "mean_brier": 0.5,
        },
        "elo_fixed_400": {"mean_log_loss": 1.1, "mean_brier": 0.6},
        "elo_tuned_nested": {"mean_log_loss": 1.0, "mean_brier": 0.55},
        "elo_market_stack_nested": {
            "mean_log_loss": 0.9, "mean_brier": 0.5,
        },
    }
    assert model_championship.select_holdout_challenger(
        means, "market_devigged_proxy",
    ) == "elo_tuned_nested"
    assert model_championship.select_holdout_challenger(
        means, "elo_fixed_400",
    ) == "elo_fixed_400"


def test_model_benchmark_is_nested_and_does_not_claim_deployment_or_profitability():
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
    comparison = result["challenger_vs_market_paired_bootstrap"]
    assert comparison["iterations"] == 5000
    complete_rows = [
        row for row in model_championship.load_historical()
        if row.odds_a is not None and row.odds_d is not None
        and row.odds_b is not None
        and min(row.odds_a, row.odds_d, row.odds_b) > 1.0
    ]
    split = model_championship.date_block_split(complete_rows, 0.85)
    assert comparison["block_count"] == len({
        row.date for row in complete_rows[split:]
    })
    assert comparison["challenger"] != comparison["market_benchmark"]
    assert "temporal_graph_neural_network" in result["capacity_rejections"]
    assert result["benchmark_champion_is_deployment_decision"] is False
    outer = result["nested_outer_benchmark"]
    assert result["nested_outer_championship"] is outer
    assert result["legacy_schema_aliases"] == {
        "nested_outer_championship": "nested_outer_benchmark",
    }
    assert len(outer["folds"]) == 4
    assert outer["benchmark_champion"] == result["benchmark_champion"]
    assert all(
        fold["train_rows"] + fold["test_rows"] <= result["selection_rows"]
        for fold in outer["folds"]
    )
    assert all(
        fold["train_end"] < fold["test_start"]
        for fold in outer["folds"]
    )
    gate = result["deep_learning_research"]["promotion_gate"]
    assert gate["actual_fixture_count"] == result["source_rows"]
    assert gate["actual_team_count"] == len(
        gate["actual_temporal_edges_per_team"]
    )
    assert gate["research_promotion_gate_passed"] == (
        gate["fixture_count_gate_passed"]
        and gate["temporal_edge_gate_passed"]
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
