#!/usr/bin/env python3
"""Build static site artifact for GitHub Pages from the latest report (index.html).
All previous report versions have been moved to archived/.

Per AGENT.md "Automated Update Protocol": Always run this after incrementing sections for new matches/screenshots.
This is step 5/6 in the automatic process (after HTML edits from pipeline + research).
See AGENT.md for full 7-step (screenshots → CSV → core pipeline retrain → sections + table + summary → tests + this build → deploy + live playwright validate of all matches layout)."""

from __future__ import annotations

import shutil
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

    shutil.copy2(REPORT, SITE / "index.html")

    # Optional: keep canonical filename reachable (use latest name)
    shutil.copy2(REPORT, SITE / "wc_june17_21_full_report.html")

    # Copy dynamic data files for JS population in deployed site (per architecture for dynamic cards/table from JSON)
    JSON_DATA = ROOT / "wc_june17_21_predictions.json"
    if JSON_DATA.exists():
        shutil.copy2(JSON_DATA, SITE / "wc_june17_21_predictions.json")
        print(f"[build_site] Copied dynamic data: {SITE / 'wc_june17_21_predictions.json'}")

    # Also copy matches for potential enrichment if needed in future
    MATCHES = ROOT / "wc_2026_matches_june_17-21.csv"
    if MATCHES.exists():
        shutil.copy2(MATCHES, SITE / "wc_2026_matches_june_17-21.csv")

    print(f"[build_site] Wrote {SITE / 'index.html'} ({(SITE / 'index.html').stat().st_size:,} bytes)")
    return SITE


if __name__ == "__main__":
    build()