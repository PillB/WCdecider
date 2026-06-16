#!/usr/bin/env python3
"""Build static site artifact for GitHub Pages from wc_june16_2026_report.html."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "wc_june16_2026_report.html"
SITE = ROOT / "site"


def build() -> Path:
    if not REPORT.exists():
        raise FileNotFoundError(f"Report not found: {REPORT}")

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)

    shutil.copy2(REPORT, SITE / "index.html")

    # Optional: keep canonical filename reachable
    shutil.copy2(REPORT, SITE / "wc_june16_2026_report.html")

    print(f"[build_site] Wrote {SITE / 'index.html'} ({(SITE / 'index.html').stat().st_size:,} bytes)")
    return SITE


if __name__ == "__main__":
    build()