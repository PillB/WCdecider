#!/usr/bin/env python3
"""Replace corrupted embedded World Cup group rows deterministically.

This migration preserves non-2018/2022 rows from the current historical file,
rebuilds both group stages from the corrected 48-fixture contracts in
``wc_backtest_historical_loader.py``, and writes deterministic CSV output.

It is an interim data repair. A later source-acquisition phase must replace the
embedded contracts with hash-bound authoritative raw fixture files.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wc_backtest_historical_loader import (
    OUTPUT_CSV,
    WC_2018_GROUP,
    WC_2022_GROUP,
    ExpandedMatch,
    build_wc_rows,
)
from datetime import datetime


def load_preserved(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            row for row in csv.DictReader(handle)
            if row["competition"] not in {
                "WC_2018_GROUP", "WC_2022_GROUP", "WC_2026_GROUP",
            }
        ]


def main() -> None:
    preserved = load_preserved(OUTPUT_CSV)
    repaired = [
        asdict(row) for row in (
            build_wc_rows(
                "WC_2018_GROUP", WC_2018_GROUP,
                "corrected embedded 2018 group-stage fixture contract",
            )
            + build_wc_rows(
                "WC_2022_GROUP", WC_2022_GROUP,
                "corrected embedded 2022 group-stage fixture contract",
            )
        )
    ]
    rows = repaired + preserved
    rows.sort(key=lambda row: (
        datetime.strptime(row["date"], "%d/%m/%Y"),
        row["competition"], row["team_a"], row["team_b"]
    ))
    fields = list(asdict(ExpandedMatch(
        match_id="", date="", competition="", comp_weight=0.0,
        team_a="", team_b="", team_a_name="", team_b_name="",
        elo_a_pre=0.0, elo_b_pre=0.0, outcome="", score="",
        total_goals=0, o_win_a=0.0, o_draw=0.0, o_win_b=0.0,
    )).keys())
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"Repaired {OUTPUT_CSV.name}: "
        f"2018={len(WC_2018_GROUP)}, 2022={len(WC_2022_GROUP)}, "
        f"preserved={len(preserved)}, total={len(rows)}"
    )


if __name__ == "__main__":
    main()
