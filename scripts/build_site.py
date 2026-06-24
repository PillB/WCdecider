#!/usr/bin/env python3
"""Build static site artifact for GitHub Pages from the latest report (index.html).
All previous report versions have been moved to archived/.

Per AGENT.md "Automated Update Protocol": Always run this after incrementing sections for new matches/screenshots.
This is step 5/6 in the automatic process (after HTML edits from pipeline + research).
See AGENT.md for full 7-step (screenshots → CSV → core pipeline retrain → sections + table + summary → tests + this build → deploy + live playwright validate of all matches layout)."""

from __future__ import annotations

import os
import shutil
import subprocess
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "index.html"
SITE = ROOT / "site"


def build() -> Path:
    if not REPORT.exists():
        raise FileNotFoundError(f"Report not found: {REPORT}")

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)

    build_sha = os.environ.get("GITHUB_SHA")
    if not build_sha:
        build_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    report_text = REPORT.read_text(encoding="utf-8").replace("__BUILD_SHA__", build_sha)
    (SITE / "index.html").write_text(report_text, encoding="utf-8")

    # Optional: keep canonical filename reachable (use latest name)
    (SITE / "wc_june22_27_full_report.html").write_text(report_text, encoding="utf-8")

    # Copy dynamic data files for JS population in deployed site (per architecture for dynamic cards/table from JSON)
    required = [
        ROOT / "wc_june22_27_predictions.json",
        ROOT / "wc_june22_27_model_metrics.json",
        ROOT / "wc_june22_27_model_dataset.csv",
        ROOT / "wc_odds_june_22-27.csv",
        ROOT / "wc_2026_matches_june_22-27.csv",
        ROOT / "wc_june22_27_provenance.txt",
        ROOT / "wc_screenshot_manifest_june22_27.csv",
        ROOT / "wc_research_june22_27.csv",
        ROOT / "wc_june22_27_datapoint_audit.csv",
        ROOT / "wc_june22_27_datapoint_audit_summary.json",
        ROOT / "historical_closing_odds_canonical_coverage.json",
        ROOT / "historical_closing_odds_canonical_provenance.txt",
        ROOT / "historical_closing_odds_sources.json",
        ROOT / "model_championship_results.json",
        ROOT / "HISTORICAL_ODDS_MODEL_CHAMPIONSHIP_PLAN.md",
    ]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Required deployment artifacts missing: {missing}")
    audit_path = ROOT / "wc_june22_27_datapoint_audit.csv"
    with audit_path.open(newline="", encoding="utf-8") as handle:
        audit_rows = list(csv.DictReader(handle))
    if not audit_rows or any(row.get("final_status") != "PASS" for row in audit_rows):
        raise ValueError("Datapoint audit is empty or contains non-PASS rows")
    for path in required:
        shutil.copy2(path, SITE / path.name)
        print(f"[build_site] Copied: {path.name}")

    # Also copy matches for potential enrichment if needed in future
    print(f"[build_site] Wrote {SITE / 'index.html'} ({(SITE / 'index.html').stat().st_size:,} bytes)")
    return SITE


if __name__ == "__main__":
    build()
