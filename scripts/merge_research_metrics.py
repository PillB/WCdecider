#!/usr/bin/env python3
"""Merge audited historical-odds and championship summaries into metrics JSON."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "wc_june22_27_model_metrics.json"
CHAMPIONSHIP = ROOT / "model_championship_results.json"
COVERAGE = ROOT / "historical_closing_odds_canonical_coverage.json"
PROVENANCE = ROOT / "wc_june22_27_provenance.txt"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update_provenance_hash(path: Path, digest: str) -> None:
    text = PROVENANCE.read_text(encoding="utf-8")
    pattern = rf"(- {re.escape(path.name)}: )[0-9a-f]{{64}}"
    updated, count = re.subn(pattern, rf"\g<1>{digest}", text)
    if count != 1:
        raise ValueError(
            f"Expected exactly one provenance hash entry for {path.name}"
        )
    PROVENANCE.write_text(updated, encoding="utf-8")


def main() -> None:
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    championship = json.loads(CHAMPIONSHIP.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    metrics["model_championship"] = championship
    metrics["historical_closing_odds"] = coverage
    METRICS.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    update_provenance_hash(METRICS, sha256(METRICS))
    print(
        "Merged model championship and historical-odds coverage into "
        f"{METRICS.name}"
    )


if __name__ == "__main__":
    main()
