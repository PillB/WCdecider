from __future__ import annotations

import csv
import json
from datetime import date

import pytest

import manual_odds_input_gui as manual


def test_manual_odds_simulation_writes_raw_schema_and_provenance(tmp_path):
    output = tmp_path / "manual_odds_20260627_20260629.csv"
    rows = manual.simulated_rows(date(2026, 6, 27), date(2026, 6, 29), output)

    csv_path, provenance_path, warnings = manual.write_rows(rows, output)

    assert warnings == []
    loaded = list(csv.DictReader(csv_path.open(newline="", encoding="utf-8")))
    assert len(loaded) == 5
    assert list(loaded[0]) == manual.RAW_FIELDS
    assert loaded[0]["source_image"].startswith("manual_user_input_")
    assert loaded[0]["source_image"] != "Screenshots"
    assert {
        row["selection_id"]
        for row in loaded
        if row["market_id"] == "match_result"
    } == {"home", "draw", "away"}

    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["schema"] == "manual_wcdecider_odds_v1"
    assert provenance["row_count_written"] == 5
    assert provenance["required_minimum"].startswith("complete 1X2")


def test_manual_odds_validation_rejects_bad_prices_and_flags_partial_1x2(tmp_path):
    output = tmp_path / "manual_odds_partial.csv"
    rows = manual.simulated_rows(date(2026, 6, 27), date(2026, 6, 29), output)

    rows[0].odds = "1.00"
    with pytest.raises(ValueError, match="Odds must be > 1.00"):
        manual.validate_rows(rows)

    rows = manual.simulated_rows(date(2026, 6, 27), date(2026, 6, 29), output)
    warnings = manual.validate_rows(rows[:2])
    assert warnings == [
        f"{rows[0].fixture_id} Betsson 1X2 incomplete; missing away."
    ]

