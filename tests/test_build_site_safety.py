import csv
from pathlib import Path

import pytest

from scripts import build_site


def test_blocked_audit_preserves_existing_site(tmp_path, monkeypatch):
    """A failed release gate must not erase the last known-good site."""
    monkeypatch.setattr(build_site, "ROOT", tmp_path)
    monkeypatch.setattr(build_site, "REPORT", tmp_path / "index.html")
    monkeypatch.setattr(build_site, "SITE", tmp_path / "site")

    build_site.REPORT.write_text("<html>candidate</html>", encoding="utf-8")
    build_site.SITE.mkdir()
    sentinel = build_site.SITE / "last-known-good.txt"
    sentinel.write_text("preserve me", encoding="utf-8")

    required_names = [
        "wc_june22_27_predictions.json",
        "wc_june22_27_model_metrics.json",
        "wc_june22_27_model_dataset.csv",
        "wc_odds_june_22-27.csv",
        "wc_2026_matches_june_22-27.csv",
        "wc_june22_27_provenance.txt",
        "wc_screenshot_manifest_june22_27.csv",
        "wc_research_june22_27.csv",
        "wc_june22_27_datapoint_audit.csv",
        "wc_june22_27_datapoint_audit_summary.json",
        "historical_closing_odds_canonical_coverage.json",
        "historical_closing_odds_canonical_provenance.txt",
        "historical_closing_odds_sources.json",
        "model_championship_results.json",
        "HISTORICAL_ODDS_MODEL_CHAMPIONSHIP_PLAN.md",
    ]
    for name in required_names:
        (tmp_path / name).write_text("{}\n", encoding="utf-8")
    with (tmp_path / "wc_june22_27_datapoint_audit.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["final_status"])
        writer.writeheader()
        writer.writerow({"final_status": "BLOCKED"})

    with pytest.raises(ValueError, match="non-PASS"):
        build_site.build()

    assert sentinel.read_text(encoding="utf-8") == "preserve me"
