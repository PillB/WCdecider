#!/usr/bin/env python3
"""Build static site artifact for GitHub Pages from the latest report (wc_june17_21_full_report.html).
All previous report versions have been moved to archived/."""

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

    print(f"[build_site] Wrote {SITE / 'index.html'} ({(SITE / 'index.html').stat().st_size:,} bytes)")
    return SITE


if __name__ == "__main__":
    build()