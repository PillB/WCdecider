#!/usr/bin/env python3
"""Manual Betsson/Betano odds entry tool for WCdecider.

This standalone script creates a local FastAPI web form for entering current
Betsson/Betano odds when screenshots are not available or are stale. It writes
CSV files using the same *raw odds input* columns already used by the
June 22–27 pipeline:

    fixture_id, fixture_display, kickoff_local, app, market_original,
    market_id, selection_original, selection_id, line, odds, promo,
    source_image, capture_time, notes

The exported rows are intended to replace or augment screenshot-transcribed
files such as ``odds_june27.csv`` in a future update. They deliberately mark
``source_image`` as a manual session token instead of a screenshot filename.
When the pipeline is updated to consume manual files, it should hash the saved
CSV/provenance file rather than looking for a screenshot image.

Required minimum per fixture/app
--------------------------------
For a fixture to be model-comparable, enter at least a complete 1X2 market:

* home win
* draw
* away win

Optional supported markets:

* total goals: over/under with a line such as 2.5
* BTTS: yes/no
* Asian handicap: home/away with opposite selected lines such as -0.5/+0.5
* double chance: home_or_draw, home_or_away, draw_or_away

Examples
--------
Launch local web form with default next three days from today:

    python3 manual_odds_input_gui.py

Launch local web form for June 27–29, 2026:

    python3 manual_odds_input_gui.py --start 2026-06-27 --end 2026-06-29

Headless simulation for validation:

    python3 manual_odds_input_gui.py --simulate --output tmp/manual_odds_demo.csv

Run built-in tests:

    python3 manual_odds_input_gui.py --self-test
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qs

try:
    from starlette.requests import Request
except ModuleNotFoundError:  # FastAPI web dependencies are optional for simulation/self-test.
    Request = object  # type: ignore[assignment]

RAW_FIELDS = [
    "fixture_id",
    "fixture_display",
    "kickoff_local",
    "app",
    "market_original",
    "market_id",
    "selection_original",
    "selection_id",
    "line",
    "odds",
    "promo",
    "source_image",
    "capture_time",
    "notes",
]

APPS = ("Betsson", "Betano")

MARKET_PRESETS = {
    "match_result": {
        "market_original": "Match Result",
        "selections": [
            ("home", "Home / Team 1"),
            ("draw", "Draw"),
            ("away", "Away / Team 2"),
        ],
        "line_required": False,
    },
    "total_goals": {
        "market_original": "Total Goals",
        "selections": [("over", "Over"), ("under", "Under")],
        "line_required": True,
    },
    "both_teams_to_score": {
        "market_original": "Both Teams To Score",
        "selections": [("yes", "Yes"), ("no", "No")],
        "line_required": False,
    },
    "asian_handicap": {
        "market_original": "Asian Handicap",
        "selections": [("home", "Home / Team 1"), ("away", "Away / Team 2")],
        "line_required": True,
    },
    "double_chance": {
        "market_original": "Double Chance",
        "selections": [
            ("home_or_draw", "Home or Draw"),
            ("home_or_away", "Home or Away"),
            ("draw_or_away", "Draw or Away"),
        ],
        "line_required": False,
    },
}

FORM_SECTIONS = (
    "Date range and output",
    "Fixture",
    "Market odds",
    "Rows to save",
    "Actions",
)
WEB_DEFAULT_HOST = "127.0.0.1"
WEB_DEFAULT_PORT = 8765


def web_layout_spec() -> Mapping[str, object]:
    """Return the expected local web form sections without importing FastAPI.

    Example
    -------
    >>> spec = web_layout_spec()
    >>> spec["default_url"].endswith(":8765/")
    True
    """
    return {
        "title": "WCdecider manual Betsson/Betano odds input",
        "default_url": f"http://{WEB_DEFAULT_HOST}:{WEB_DEFAULT_PORT}/",
        "sections": list(FORM_SECTIONS),
        "supported_apps": list(APPS),
        "supported_markets": sorted(MARKET_PRESETS),
        "save_format": "manual_wcdecider_odds_v1 CSV plus provenance JSON",
    }


@dataclass
class ManualOddsRow:
    """One user-entered raw odds row."""

    fixture_id: str
    fixture_display: str
    kickoff_local: str
    app: str
    market_original: str
    market_id: str
    selection_original: str
    selection_id: str
    line: str
    odds: str
    promo: str = "false"
    source_image: str = ""
    capture_time: str = ""
    notes: str = ""

    def as_dict(self) -> dict:
        """Return this row in canonical CSV column order."""
        return {field_name: str(getattr(self, field_name)) for field_name in RAW_FIELDS}


def slug(value: str) -> str:
    """Return a stable lowercase ASCII-ish slug for IDs."""
    text = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return text.strip("-") or "unknown"


def default_date_range(today: Optional[date] = None) -> Tuple[date, date]:
    """Return default next-three-days range, excluding today."""
    base = today or date.today()
    start = base + timedelta(days=1)
    end = base + timedelta(days=3)
    return start, end


def parse_date(value: str) -> date:
    """Parse an ISO date string."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid ISO date: {value}") from exc


def normalize_capture_time(value: str) -> str:
    """Return timezone-aware capture timestamp text.

    Empty input is filled with current local time in ISO-like form. The existing
    raw odds files use strings such as ``2026-06-21 22:14 -05:00``; this helper
    follows that convention.
    """
    text = value.strip()
    if text:
        return text
    now = datetime.now().astimezone()
    offset = now.strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if offset else "-05:00"
    return f"{now:%Y-%m-%d %H:%M} {offset}"


def make_fixture_id(kickoff_local: str, team_home: str, team_away: str) -> str:
    """Create a deterministic fixture ID from date and teams."""
    day = kickoff_local[:10] if re.match(r"\d{4}-\d{2}-\d{2}", kickoff_local) else "unknown-date"
    return f"{day}-{slug(team_home)[:3]}-{slug(team_away)[:3]}"


def make_manual_source_token(capture_time: str, output_path: Path) -> str:
    """Create a source token that clearly is not a screenshot filename."""
    digest = hashlib.sha256(f"{capture_time}|{output_path}".encode("utf-8")).hexdigest()[:12]
    return f"manual_user_input_{digest}"


def selection_display_name(selection_id: str, home: str, away: str, fallback: str) -> str:
    """Return the canonical display label for a market selection."""
    return {
        "home": home,
        "away": away,
        "draw": "Draw",
        "over": "Over",
        "under": "Under",
        "yes": "Yes",
        "no": "No",
        "home_or_draw": f"{home} or Draw",
        "home_or_away": f"{home} or {away}",
        "draw_or_away": f"Draw or {away}",
    }.get(selection_id, fallback)


def validate_decimal_odds(value: str) -> float:
    """Validate decimal odds and return as float."""
    try:
        number = float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"Odds must be numeric: {value!r}") from exc
    if number <= 1.0 or number > 1000.0:
        raise ValueError(f"Odds must be > 1.00 and realistic: {value!r}")
    return number


def rows_from_form_fields(
    fields: Mapping[str, str],
    output_path: Path,
) -> List[ManualOddsRow]:
    """Build validated odds rows from local web form fields.

    The function is deliberately framework-free. FastAPI, tests, and any future
    UI can call this exact conversion path, which prevents the web form from
    saving a subtly different schema than the pipeline expects.

    Required keys are ``home``, ``away``, ``kickoff_local``, ``app`` and
    ``market_id``. Odds are read from keys named ``odds_<selection_id>``.

    Example
    -------
    >>> rows = rows_from_form_fields({
    ...     "home": "Peru", "away": "Japan",
    ...     "kickoff_local": "2026-06-27T15:00:00-05:00",
    ...     "app": "Betsson", "market_id": "match_result",
    ...     "odds_home": "2.20", "odds_draw": "3.10", "odds_away": "3.40",
    ... }, Path("manual_odds_demo.csv"))
    >>> len(rows)
    3
    """
    home = fields.get("home", "").strip()
    away = fields.get("away", "").strip()
    kickoff = fields.get("kickoff_local", "").strip()
    if not home or not away:
        raise ValueError("Home/Team 1 and Away/Team 2 are required.")
    if not kickoff:
        raise ValueError("Kickoff Lima ISO is required.")
    app = fields.get("app", "").strip() or APPS[0]
    if app not in APPS:
        raise ValueError(f"Unsupported app: {app!r}")
    market_id = fields.get("market_id", "").strip() or "match_result"
    if market_id not in MARKET_PRESETS:
        raise ValueError(f"Unsupported market_id: {market_id!r}")
    preset = MARKET_PRESETS[market_id]
    line = fields.get("line", "").strip()
    if preset["line_required"] and not line:
        raise ValueError(f"Line is required for {market_id}.")
    fixture_id = fields.get("fixture_id", "").strip() or make_fixture_id(kickoff, home, away)
    fixture_display = f"{home} vs {away}"
    capture = normalize_capture_time(fields.get("capture_time", ""))
    source = make_manual_source_token(capture, output_path)
    notes = fields.get("notes", "manual user input").strip()

    rows: List[ManualOddsRow] = []
    for selection_id, label in preset["selections"]:
        odds = fields.get(f"odds_{selection_id}", "").strip()
        if not odds:
            continue
        validate_decimal_odds(odds)
        rows.append(
            ManualOddsRow(
                fixture_id=fixture_id,
                fixture_display=fixture_display,
                kickoff_local=kickoff,
                app=app,
                market_original=preset["market_original"],
                market_id=market_id,
                selection_original=selection_display_name(selection_id, home, away, label),
                selection_id=selection_id,
                line=line,
                odds=odds,
                promo="false",
                source_image=source,
                capture_time=capture,
                notes=notes,
            )
        )
    if not rows:
        raise ValueError("Enter at least one decimal odds value for the selected market.")
    validate_rows(rows)
    return rows


def validate_rows(rows: Sequence[ManualOddsRow]) -> List[str]:
    """Validate rows and return non-fatal warnings.

    Fatal schema/odds issues raise ``ValueError``. Missing complete 1X2 markets
    are warnings because the user may intentionally save a partial draft, but
    the modeling pipeline should later block incomplete fixtures.
    """
    if not rows:
        raise ValueError("No odds rows to save.")
    warnings: List[str] = []
    seen = set()
    grouped_1x2 = {}
    for row in rows:
        if row.app not in APPS:
            raise ValueError(f"Unsupported app: {row.app!r}")
        if not row.fixture_id or not row.fixture_display:
            raise ValueError("Every row needs fixture_id and fixture_display.")
        if row.market_id not in MARKET_PRESETS:
            raise ValueError(f"Unsupported market_id: {row.market_id!r}")
        validate_decimal_odds(row.odds)
        if MARKET_PRESETS[row.market_id]["line_required"] and not row.line.strip():
            raise ValueError(f"Line is required for {row.market_id}: {row.fixture_display}")
        key = (
            row.fixture_id,
            row.app,
            row.market_id,
            row.selection_id,
            row.line,
            row.odds,
        )
        if key in seen:
            raise ValueError(f"Duplicate odds row: {key}")
        seen.add(key)
        if row.market_id == "match_result":
            grouped_1x2.setdefault((row.fixture_id, row.app), set()).add(row.selection_id)
    for (fixture_id, app), selections in sorted(grouped_1x2.items()):
        missing = {"home", "draw", "away"} - selections
        if missing:
            warnings.append(
                f"{fixture_id} {app} 1X2 incomplete; missing {', '.join(sorted(missing))}."
            )
    fixture_app_pairs = {
        (row.fixture_id, row.app) for row in rows
    }
    for fixture_id, app in sorted(fixture_app_pairs):
        if (fixture_id, app) not in grouped_1x2:
            warnings.append(f"{fixture_id} {app} has no 1X2 market.")
    return warnings


def write_rows(
    rows: Sequence[ManualOddsRow],
    output_path: Path,
    append: bool = False,
    provenance_path: Optional[Path] = None,
) -> Tuple[Path, Path, List[str]]:
    """Write odds rows and provenance JSON.

    Existing files can be appended. Header is written when creating a new file.
    """
    warnings = validate_rows(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    existing = output_path.exists() and append
    mode = "a" if existing else "w"
    with output_path.open(mode, newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS, lineterminator="\n")
        if not existing:
            writer.writeheader()
        for row in rows:
            writer.writerow(row.as_dict())
    provenance_path = provenance_path or output_path.with_suffix(".provenance.json")
    payload = {
        "schema": "manual_wcdecider_odds_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_csv": str(output_path),
        "row_count_written": len(rows),
        "append_mode": append,
        "fields": RAW_FIELDS,
        "required_minimum": "complete 1X2 rows per fixture/app: home, draw, away",
        "supported_markets": sorted(MARKET_PRESETS),
        "warnings": warnings,
        "notes": [
            "Rows are manually entered user observations, not screenshot OCR.",
            "source_image is a manual session token and must not be resolved in Screenshots/.",
            "Future pipeline ingestion should hash this CSV/provenance pair as source evidence.",
        ],
    }
    provenance_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path, provenance_path, warnings


def simulated_rows(
    start: date,
    end: date,
    output_path: Path,
    capture_time: str = "2026-06-26 09:00 -05:00",
) -> List[ManualOddsRow]:
    """Return deterministic sample rows for headless validation."""
    source = make_manual_source_token(capture_time, output_path)
    kickoff = f"{start.isoformat()}T15:00:00-05:00"
    fixture_id = make_fixture_id(kickoff, "Example Home", "Example Away")
    base = {
        "fixture_id": fixture_id,
        "fixture_display": "Example Home vs Example Away",
        "kickoff_local": kickoff,
        "app": "Betsson",
        "market_original": "Match Result",
        "market_id": "match_result",
        "line": "",
        "promo": "false",
        "source_image": source,
        "capture_time": capture_time,
        "notes": f"manual simulation for {start.isoformat()} to {end.isoformat()}",
    }
    return [
        ManualOddsRow(selection_original="Example Home", selection_id="home", odds="2.10", **base),
        ManualOddsRow(selection_original="Draw", selection_id="draw", odds="3.25", **base),
        ManualOddsRow(selection_original="Example Away", selection_id="away", odds="3.60", **base),
        ManualOddsRow(
            **{
                **base,
                "market_original": "Total Goals",
                "market_id": "total_goals",
                "selection_original": "Over",
                "selection_id": "over",
                "line": "2.5",
                "odds": "1.91",
            }
        ),
        ManualOddsRow(
            **{
                **base,
                "market_original": "Total Goals",
                "market_id": "total_goals",
                "selection_original": "Under",
                "selection_id": "under",
                "line": "2.5",
                "odds": "1.89",
            }
        ),
    ]


def run_self_test() -> None:
    """Run a small headless test suite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "manual_odds.csv"
        start = date(2026, 6, 27)
        end = date(2026, 6, 29)
        rows = simulated_rows(start, end, output)
        csv_path, provenance_path, warnings = write_rows(rows, output)
        assert csv_path.exists(), csv_path
        assert provenance_path.exists(), provenance_path
        with csv_path.open(newline="", encoding="utf-8") as handle:
            loaded = list(csv.DictReader(handle))
        assert len(loaded) == 5
        assert loaded[0]["source_image"].startswith("manual_user_input_")
        assert {row["selection_id"] for row in loaded if row["market_id"] == "match_result"} == {
            "home",
            "draw",
            "away",
        }
        assert warnings == []
        payload = json.loads(provenance_path.read_text(encoding="utf-8"))
        assert payload["schema"] == "manual_wcdecider_odds_v1"
        assert payload["row_count_written"] == 5
    print("manual_odds_input_gui.py self-test passed")


def _html_attrs(options: Iterable[str], selected: str) -> str:
    """Return escaped HTML option tags."""
    parts = []
    for option in options:
        chosen = " selected" if option == selected else ""
        parts.append(f'<option value="{html.escape(option)}"{chosen}>{html.escape(option)}</option>')
    return "\n".join(parts)


def _rows_table_html(rows: Sequence[ManualOddsRow]) -> str:
    """Return a compact HTML table for in-memory rows."""
    if not rows:
        return "<p class='muted'>No rows added yet.</p>"
    body = []
    for idx, row in enumerate(rows):
        body.append(
            "<tr>"
            f"<td>{idx + 1}</td>"
            f"<td>{html.escape(row.fixture_display)}</td>"
            f"<td>{html.escape(row.app)}</td>"
            f"<td>{html.escape(row.market_id)}</td>"
            f"<td>{html.escape(row.selection_original)}</td>"
            f"<td>{html.escape(row.line)}</td>"
            f"<td>{html.escape(row.odds)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>#</th><th>Fixture</th><th>App</th><th>Market</th>"
        "<th>Selection</th><th>Line</th><th>Odds</th></tr></thead><tbody>"
        + "\n".join(body)
        + "</tbody></table>"
    )


def build_web_form_html(
    start: date,
    end: date,
    output_path: Path,
    rows: Sequence[ManualOddsRow],
    append: bool = False,
    message: str = "",
    errors: Sequence[str] = (),
) -> str:
    """Build the complete manual odds web form HTML.

    The HTML is intentionally server-rendered and dependency-light: no bundled
    JS framework and no remote assets. That keeps the local data-entry tool
    usable on locked-down machines and easy to regression-test as plain text.
    """
    market_cards = []
    for market_id, preset in MARKET_PRESETS.items():
        inputs = []
        for selection_id, label in preset["selections"]:
            inputs.append(
                "<label>"
                f"<span>{html.escape(label)} odds</span>"
                f"<input name='odds_{html.escape(selection_id)}' inputmode='decimal' "
                "placeholder='e.g. 1.91'>"
                "</label>"
            )
        requires_line = "Line required" if preset["line_required"] else "No line required"
        market_cards.append(
            f"<details class='market-card' data-market-card='{html.escape(market_id)}'>"
            f"<summary>{html.escape(market_id)} — {html.escape(preset['market_original'])} "
            f"<small>{requires_line}</small></summary>"
            "<div class='grid'>"
            + "\n".join(inputs)
            + "</div></details>"
        )
    alerts = ""
    if message:
        alerts += f"<div class='alert ok'>{html.escape(message)}</div>"
    for error in errors:
        alerts += f"<div class='alert error'>{html.escape(error)}</div>"
    checked = " checked" if append else ""
    market_options = _html_attrs(MARKET_PRESETS.keys(), "match_result")
    app_options = _html_attrs(APPS, APPS[0])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WCdecider manual Betsson/Betano odds input</title>
  <style>
    :root {{ color-scheme: dark; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #020617; color: #e2e8f0; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 18px; }}
    h1 {{ font-size: 1.45rem; margin: 0 0 8px; }}
    h2 {{ font-size: 1rem; margin: 0 0 12px; color: #bfdbfe; }}
    .card {{ background: #0f172a; border: 1px solid #334155; border-radius: 14px; padding: 14px; margin: 12px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }}
    label span {{ display: block; font-size: .82rem; color: #94a3b8; margin-bottom: 5px; }}
    input, select {{ width: 100%; box-sizing: border-box; border-radius: 10px; border: 1px solid #475569; background: #020617; color: #e2e8f0; padding: 9px; }}
    button {{ border: 0; border-radius: 999px; background: #22c55e; color: #052e16; font-weight: 700; padding: 10px 16px; cursor: pointer; }}
    button.secondary {{ background: #38bdf8; color: #082f49; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
    .muted, small {{ color: #94a3b8; }}
    .alert {{ border-radius: 10px; padding: 10px 12px; margin: 10px 0; }}
    .ok {{ background: #064e3b; color: #d1fae5; }}
    .error {{ background: #7f1d1d; color: #fee2e2; }}
    details {{ border: 1px solid #334155; border-radius: 12px; padding: 10px; margin: 8px 0; }}
    summary {{ cursor: pointer; color: #e0f2fe; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
    th, td {{ border-bottom: 1px solid #334155; padding: 8px; text-align: left; vertical-align: top; }}
    .hidden {{ display: none; }}
    @media (max-width: 720px) {{ main {{ padding: 10px; }} table {{ display: block; overflow-x: auto; }} }}
  </style>
</head>
<body>
<main>
  <section class="card">
    <h1>WCdecider manual odds input</h1>
    <p class="muted">Local-only FastAPI form. Add one market at a time, then Save / Done to write the raw CSV and provenance JSON used by the model pipeline.</p>
    {alerts}
  </section>

  <form method="post" action="/add" class="card">
    <h2>Date range and output</h2>
    <div class="grid">
      <label><span>Start</span><input name="start" value="{start.isoformat()}"></label>
      <label><span>End</span><input name="end" value="{end.isoformat()}"></label>
      <label><span>Output CSV</span><input name="output_path" value="{html.escape(str(output_path))}" readonly></label>
      <label><span>Capture time</span><input name="capture_time" value="{html.escape(normalize_capture_time(''))}"></label>
    </div>

    <h2>Fixture</h2>
    <div class="grid">
      <label><span>Home/Team 1</span><input name="home" required></label>
      <label><span>Away/Team 2</span><input name="away" required></label>
      <label><span>Kickoff Lima ISO</span><input name="kickoff_local" value="{start.isoformat()}T15:00:00-05:00" required></label>
      <label><span>Fixture ID optional</span><input name="fixture_id" placeholder="auto-generated if blank"></label>
      <label><span>App</span><select name="app">{app_options}</select></label>
      <label><span>Market to add</span><select name="market_id">{market_options}</select></label>
      <label><span>Line, if market needs it</span><input name="line" placeholder="2.5, -0.5, +0.5"></label>
      <label><span>Notes</span><input name="notes" value="manual user input"></label>
    </div>

    <h2>Market odds</h2>
    <p class="muted">Fill only the odds boxes for the selected market. Complete 1X2 needs home, draw, and away.</p>
    {''.join(market_cards)}
    <div class="actions"><button type="submit">Add market rows</button></div>
  </form>

  <section class="card">
    <h2>Rows to save</h2>
    {_rows_table_html(rows)}
  </section>

  <section class="card">
    <h2>Actions</h2>
    <form method="post" action="/save" class="actions">
      <label style="width:auto"><input style="width:auto" type="checkbox" name="append"{checked}> Append to existing CSV</label>
      <button type="submit">Save / Done</button>
      <button class="secondary" formaction="/clear" formmethod="post">Clear unsaved rows</button>
      <a class="muted" href="/download">Download saved CSV</a>
    </form>
  </section>
</main>
<script>
  function syncMarketCards() {{
    const selected = document.querySelector("select[name='market_id']").value;
    document.querySelectorAll("[data-market-card]").forEach((card) => {{
      const active = card.dataset.marketCard === selected;
      card.classList.toggle("hidden", !active);
      card.open = active;
      card.querySelectorAll("input").forEach((input) => input.disabled = !active);
    }});
  }}
  document.querySelector("select[name='market_id']").addEventListener("change", syncMarketCards);
  syncMarketCards();
</script>
</body>
</html>
"""


def create_fastapi_app(start: date, end: date, output_path: Path, append: bool = False):
    """Create the local FastAPI manual odds app.

    FastAPI is imported lazily so headless tests and simulation still work in
    environments that have not installed web dependencies yet.
    """
    try:
        from fastapi import FastAPI
        from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FastAPI web mode requires dependencies: python3 -m pip install fastapi uvicorn"
        ) from exc

    app = FastAPI(title="WCdecider manual odds input", version="1.0")
    app.state.rows = []
    app.state.append = append

    def page(message: str = "", errors: Sequence[str] = ()) -> HTMLResponse:
        return HTMLResponse(
            build_web_form_html(
                start=start,
                end=end,
                output_path=output_path,
                rows=app.state.rows,
                append=app.state.append,
                message=message,
                errors=errors,
            )
        )

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return page()

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({**web_layout_spec(), "rows_in_memory": len(app.state.rows)})

    @app.post("/add", response_class=HTMLResponse)
    async def add_rows(request: Request) -> HTMLResponse:
        body = (await request.body()).decode("utf-8")
        fields = {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}
        try:
            added = rows_from_form_fields(fields, output_path)
            app.state.rows.extend(added)
            return page(message=f"Added {len(added)} row(s). Unsaved total: {len(app.state.rows)}.")
        except Exception as exc:
            return page(errors=[str(exc)])

    @app.post("/save", response_class=HTMLResponse)
    async def save(request: Request) -> HTMLResponse:
        body = (await request.body()).decode("utf-8")
        fields = {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}
        app.state.append = "append" in fields
        try:
            csv_path, provenance_path, warnings = write_rows(
                app.state.rows,
                output_path,
                append=app.state.append,
            )
            message = f"Saved {len(app.state.rows)} row(s) to {csv_path}; provenance: {provenance_path}."
            if warnings:
                message += " Warnings: " + " ".join(warnings)
            return page(message=message)
        except Exception as exc:
            return page(errors=[str(exc)])

    @app.post("/clear", response_class=HTMLResponse)
    async def clear() -> HTMLResponse:
        count = len(app.state.rows)
        app.state.rows.clear()
        return page(message=f"Cleared {count} unsaved row(s).")

    @app.get("/download")
    async def download():
        if output_path.exists():
            return FileResponse(output_path, filename=output_path.name)
        return page(errors=[f"No saved CSV exists yet at {output_path}."])

    return app


def run_web_app(
    start: date,
    end: date,
    output_path: Path,
    append: bool = False,
    host: str = WEB_DEFAULT_HOST,
    port: int = WEB_DEFAULT_PORT,
) -> None:
    """Run the local FastAPI manual odds server."""
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FastAPI web mode requires dependencies: python3 -m pip install fastapi uvicorn"
        ) from exc
    app = create_fastapi_app(start, end, output_path, append=append)
    print(f"Open manual odds form: http://{host}:{port}/")
    uvicorn.run(app, host=host, port=port, log_level="info")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    default_start, default_end = default_date_range()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=parse_date, default=default_start, help="Start date YYYY-MM-DD; default tomorrow.")
    parser.add_argument("--end", type=parse_date, default=default_end, help="End date YYYY-MM-DD; default three days after today.")
    parser.add_argument("--output", type=Path, default=None, help="Output raw odds CSV path.")
    parser.add_argument("--append", action="store_true", help="Append to existing output CSV.")
    parser.add_argument("--simulate", action="store_true", help="Write deterministic sample rows without opening GUI.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in headless tests and exit.")
    parser.add_argument("--host", default=WEB_DEFAULT_HOST, help="FastAPI host; default 127.0.0.1.")
    parser.add_argument("--port", type=int, default=WEB_DEFAULT_PORT, help="FastAPI port; default 8765.")
    parser.add_argument("--diagnose-web", action="store_true", help="Print expected web form contract without starting the server.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0
    if args.diagnose_web:
        print(json.dumps(web_layout_spec(), indent=2, sort_keys=True))
        return 0
    if args.end < args.start:
        parser.error("--end must be on or after --start")
    output = args.output or Path(
        f"manual_odds_{args.start:%Y%m%d}_{args.end:%Y%m%d}.csv"
    )
    if args.simulate:
        rows = simulated_rows(args.start, args.end, output)
        csv_path, provenance_path, warnings = write_rows(rows, output, append=args.append)
        print(f"Saved simulated manual odds CSV: {csv_path}")
        print(f"Saved provenance JSON: {provenance_path}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"- {warning}")
        return 0
    try:
        run_web_app(
            args.start,
            args.end,
            output,
            append=args.append,
            host=args.host,
            port=args.port,
        )
    except RuntimeError as exc:
        parser.exit(2, f"{exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
