from __future__ import annotations

import csv
import errno
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

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


def test_manual_web_layout_spec_has_visible_sections():
    spec = manual.web_layout_spec()

    assert spec["title"] == "WCdecider manual Betsson/Betano odds input"
    assert spec["sections"] == [
        "Date range and output",
        "Fixture",
        "Market odds",
        "Rows to save",
        "Actions",
    ]
    assert "match_result" in spec["supported_markets"]
    assert spec["supported_apps"] == ["Betsson", "Betano"]
    assert spec["default_url"] == "http://127.0.0.1:8765/"


def test_manual_web_diagnose_cli_prints_layout_spec(capsys):
    exit_code = manual.main(["--diagnose-web"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["default_url"] == "http://127.0.0.1:8765/"
    assert "Fixture" in payload["sections"]


def test_bind_available_server_socket_falls_forward_when_port_is_occupied(monkeypatch):
    created = []

    class FakeSocket:
        def __init__(self):
            self.closed = False
            self.bound_port = None
            created.append(self)

        def setsockopt(self, *_args):
            return None

        def bind(self, address):
            _host, port = address
            if port == 8765:
                raise OSError(errno.EADDRINUSE, "address already in use")
            self.bound_port = port

        def listen(self, _backlog):
            return None

        def getsockname(self):
            return ("127.0.0.1", self.bound_port)

        def close(self):
            self.closed = True

    monkeypatch.setattr(manual.socket, "socket", lambda *_args, **_kwargs: FakeSocket())

    chosen_socket, chosen_port, changed = manual.bind_available_server_socket(
        "127.0.0.1",
        8765,
        scan_limit=10,
    )

    assert changed is True
    assert chosen_port == 8766
    assert chosen_socket.closed is False
    assert created[0].closed is True


def test_manual_web_form_renders_required_sections_and_market_switching(tmp_path):
    output = tmp_path / "manual_odds.csv"
    html = manual.build_web_form_html(
        date(2026, 6, 27),
        date(2026, 6, 29),
        output,
        rows=[],
    )

    assert "WCdecider manual odds input" in html
    assert "Date range and output" in html
    assert "data-market-card='match_result'" in html
    assert "data-market-card='asian_handicap'" in html
    assert "syncMarketCards" in html
    assert "Tkinter" not in html


def test_rows_from_form_fields_match_pipeline_schema(tmp_path):
    output = tmp_path / "manual_odds.csv"
    rows = manual.rows_from_form_fields(
        {
            "home": "Peru",
            "away": "Japan",
            "kickoff_local": "2026-06-27T15:00:00-05:00",
            "app": "Betano",
            "market_id": "match_result",
            "odds_home": "2.20",
            "odds_draw": "3.10",
            "odds_away": "3.40",
            "notes": "web form test",
        },
        output,
    )

    assert len(rows) == 3
    assert [row.selection_id for row in rows] == ["home", "draw", "away"]
    assert rows[0].fixture_id == "2026-06-27-per-jap"
    assert rows[0].source_image.startswith("manual_user_input_")
    assert rows[0].as_dict().keys() == set(manual.RAW_FIELDS)


def test_fastapi_manual_odds_add_save_and_download(tmp_path):
    output = tmp_path / "manual_odds.csv"
    app = manual.create_fastapi_app(
        date(2026, 6, 27),
        date(2026, 6, 29),
        output,
    )
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["rows_in_memory"] == 0

    add = client.post(
        "/add",
        data={
            "home": "Peru",
            "away": "Japan",
            "kickoff_local": "2026-06-27T15:00:00-05:00",
            "app": "Betsson",
            "market_id": "match_result",
            "odds_home": "2.20",
            "odds_draw": "3.10",
            "odds_away": "3.40",
            "notes": "route test",
        },
    )
    assert add.status_code == 200
    assert "Added 3 row(s)" in add.text
    assert client.get("/health").json()["rows_in_memory"] == 3

    save = client.post("/save", data={})
    assert save.status_code == 200
    assert "Saved 3 row(s)" in save.text
    assert output.exists()
    assert output.with_suffix(".provenance.json").exists()

    download = client.get("/download")
    assert download.status_code == 200
    assert "Peru vs Japan" in download.text
