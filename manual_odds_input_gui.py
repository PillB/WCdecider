#!/usr/bin/env python3
"""Manual Betsson/Betano odds entry GUI for WCdecider.

This standalone script creates a small Tkinter GUI for entering current
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
Launch GUI with default next three days from today:

    python3 manual_odds_input_gui.py

Launch GUI for June 27–29, 2026:

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
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

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

GUI_SECTIONS = (
    "Date range and output",
    "Fixture",
    "Market odds",
    "Rows to save",
    "Actions",
)
GUI_DEFAULT_GEOMETRY = "1180x820"
GUI_MIN_SIZE = (980, 680)


def gui_layout_spec() -> Mapping[str, object]:
    """Return the expected visible GUI sections without opening Tk.

    This is intentionally headless-testable. The Tk implementation uses this
    as a contract: if a user sees an empty window, these sections are the
    minimum that must be visible after layout.

    Example
    -------
    >>> spec = gui_layout_spec()
    >>> "Fixture" in spec["sections"]
    True
    """
    return {
        "title": "WCdecider manual Betsson/Betano odds input",
        "geometry": GUI_DEFAULT_GEOMETRY,
        "min_width": GUI_MIN_SIZE[0],
        "min_height": GUI_MIN_SIZE[1],
        "sections": list(GUI_SECTIONS),
        "supported_apps": list(APPS),
        "supported_markets": sorted(MARKET_PRESETS),
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


def validate_decimal_odds(value: str) -> float:
    """Validate decimal odds and return as float."""
    try:
        number = float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"Odds must be numeric: {value!r}") from exc
    if number <= 1.0 or number > 1000.0:
        raise ValueError(f"Odds must be > 1.00 and realistic: {value!r}")
    return number


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


class ManualOddsGui:
    """Tkinter GUI controller."""

    def __init__(self, start: date, end: date, output_path: Path, append: bool = False):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.title("WCdecider manual Betsson/Betano odds input")
        self.output_path = output_path
        self.append = tk.BooleanVar(value=append)
        self.rows: List[ManualOddsRow] = []
        self.start_var = tk.StringVar(value=start.isoformat())
        self.end_var = tk.StringVar(value=end.isoformat())
        self.capture_var = tk.StringVar(value=normalize_capture_time(""))
        self.fixture_id_var = tk.StringVar()
        self.home_var = tk.StringVar()
        self.away_var = tk.StringVar()
        self.kickoff_var = tk.StringVar(value=f"{start.isoformat()}T15:00:00-05:00")
        self.app_var = tk.StringVar(value="Betsson")
        self.market_var = tk.StringVar(value="match_result")
        self.line_var = tk.StringVar()
        self.notes_var = tk.StringVar(value="manual user input")
        self.odds_vars = {}
        self._build()

    def _build(self) -> None:
        tk = self.tk
        ttk = self.ttk
        root = self.root
        pad = {"padx": 6, "pady": 4}

        root.geometry(GUI_DEFAULT_GEOMETRY)
        root.minsize(*GUI_MIN_SIZE)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        canvas = tk.Canvas(root, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        content = ttk.Frame(canvas, padding=8)
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")
        content.columnconfigure(0, weight=1)

        def sync_scroll_region(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def sync_content_width(event) -> None:
            canvas.itemconfigure(content_window, width=event.width)

        content.bind("<Configure>", sync_scroll_region)
        canvas.bind("<Configure>", sync_content_width)
        canvas.bind_all(
            "<MouseWheel>",
            lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"),
        )
        self.content_frame = content

        header = tk.Label(
            content,
            text=(
                "WCdecider manual odds input — fill fixture, select app/market, "
                "enter decimal odds, then Add market rows."
            ),
            anchor="w",
            justify="left",
            bg="#0f172a",
            fg="#e2e8f0",
            padx=10,
            pady=8,
        )
        header.grid(row=0, column=0, sticky="ew", **pad)

        top = ttk.LabelFrame(content, text="Date range and output")
        top.grid(row=1, column=0, sticky="ew", **pad)
        for i in range(6):
            top.columnconfigure(i, weight=1)
        ttk.Label(top, text="Start").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.start_var, width=12).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Label(top, text="End").grid(row=0, column=2, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.end_var, width=12).grid(row=0, column=3, sticky="ew", **pad)
        ttk.Label(top, text="Output").grid(row=0, column=4, sticky="w", **pad)
        ttk.Label(top, text=str(self.output_path)).grid(row=0, column=5, sticky="w", **pad)
        ttk.Checkbutton(top, text="Append to existing CSV", variable=self.append).grid(row=1, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(top, text="Capture time").grid(row=1, column=2, sticky="w", **pad)
        ttk.Entry(top, textvariable=self.capture_var, width=24).grid(row=1, column=3, columnspan=3, sticky="ew", **pad)

        fixture = ttk.LabelFrame(content, text="Fixture")
        fixture.grid(row=2, column=0, sticky="ew", **pad)
        for i in range(6):
            fixture.columnconfigure(i, weight=1)
        ttk.Label(fixture, text="Home/Team 1").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(fixture, textvariable=self.home_var).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Label(fixture, text="Away/Team 2").grid(row=0, column=2, sticky="w", **pad)
        ttk.Entry(fixture, textvariable=self.away_var).grid(row=0, column=3, sticky="ew", **pad)
        ttk.Label(fixture, text="Kickoff Lima ISO").grid(row=0, column=4, sticky="w", **pad)
        ttk.Entry(fixture, textvariable=self.kickoff_var).grid(row=0, column=5, sticky="ew", **pad)
        ttk.Label(fixture, text="Fixture ID optional").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(fixture, textvariable=self.fixture_id_var).grid(row=1, column=1, columnspan=2, sticky="ew", **pad)
        ttk.Label(fixture, text="App").grid(row=1, column=3, sticky="w", **pad)
        ttk.Combobox(fixture, textvariable=self.app_var, values=APPS, state="readonly", width=10).grid(row=1, column=4, sticky="w", **pad)

        market = ttk.LabelFrame(content, text="Market odds")
        market.grid(row=3, column=0, sticky="ew", **pad)
        for i in range(6):
            market.columnconfigure(i, weight=1)
        ttk.Label(market, text="Market").grid(row=0, column=0, sticky="w", **pad)
        combo = ttk.Combobox(market, textvariable=self.market_var, values=list(MARKET_PRESETS), state="readonly")
        combo.grid(row=0, column=1, sticky="ew", **pad)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_selection_inputs())
        ttk.Label(market, text="Line").grid(row=0, column=2, sticky="w", **pad)
        ttk.Entry(market, textvariable=self.line_var, width=8).grid(row=0, column=3, sticky="w", **pad)
        ttk.Label(market, text="Notes").grid(row=0, column=4, sticky="w", **pad)
        ttk.Entry(market, textvariable=self.notes_var).grid(row=0, column=5, sticky="ew", **pad)
        self.selection_frame = ttk.Frame(market)
        self.selection_frame.grid(row=1, column=0, columnspan=6, sticky="ew", **pad)
        self._refresh_selection_inputs()
        ttk.Button(market, text="Add market rows", command=self.add_market_rows).grid(row=2, column=0, sticky="w", **pad)

        table_frame = ttk.LabelFrame(content, text="Rows to save")
        table_frame.grid(row=4, column=0, sticky="nsew", **pad)
        content.rowconfigure(4, weight=1)
        columns = ("fixture", "app", "market", "selection", "line", "odds")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130)
        self.tree.grid(row=0, column=0, sticky="nsew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        ttk.Button(table_frame, text="Delete selected", command=self.delete_selected).grid(row=1, column=0, sticky="w", **pad)

        actions = ttk.LabelFrame(content, text="Actions")
        actions.grid(row=5, column=0, sticky="ew", **pad)
        ttk.Button(actions, text="Save / Done", command=self.save_done).grid(row=0, column=0, sticky="w", **pad)
        ttk.Button(actions, text="Quit without saving", command=root.destroy).grid(row=0, column=1, sticky="w", **pad)
        self.status = ttk.Label(actions, text="Enter fixture + odds. Minimum complete 1X2 per app is recommended.")
        self.status.grid(row=0, column=2, sticky="w", **pad)
        root.after(50, sync_scroll_region)

    def _refresh_selection_inputs(self) -> None:
        for child in self.selection_frame.winfo_children():
            child.destroy()
        self.odds_vars.clear()
        preset = MARKET_PRESETS[self.market_var.get()]
        for idx, (selection_id, label) in enumerate(preset["selections"]):
            var = self.tk.StringVar()
            self.odds_vars[selection_id] = var
            self.ttk.Label(self.selection_frame, text=f"{label} odds").grid(row=0, column=idx * 2, sticky="w", padx=6, pady=4)
            self.ttk.Entry(self.selection_frame, textvariable=var, width=10).grid(row=0, column=idx * 2 + 1, sticky="w", padx=6, pady=4)

    def _fixture_values(self) -> Tuple[str, str, str, str]:
        home = self.home_var.get().strip()
        away = self.away_var.get().strip()
        kickoff = self.kickoff_var.get().strip()
        if not home or not away:
            raise ValueError("Home and away teams are required.")
        if not kickoff:
            raise ValueError("Kickoff is required.")
        fixture_id = self.fixture_id_var.get().strip() or make_fixture_id(kickoff, home, away)
        fixture_display = f"{home} vs {away}"
        return fixture_id, fixture_display, home, away

    def add_market_rows(self) -> None:
        try:
            fixture_id, fixture_display, home, away = self._fixture_values()
            market_id = self.market_var.get()
            preset = MARKET_PRESETS[market_id]
            capture = normalize_capture_time(self.capture_var.get())
            source = make_manual_source_token(capture, self.output_path)
            added = 0
            for selection_id, label in preset["selections"]:
                odds = self.odds_vars[selection_id].get().strip()
                if not odds:
                    continue
                validate_decimal_odds(odds)
                selection_original = {
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
                }.get(selection_id, label)
                row = ManualOddsRow(
                    fixture_id=fixture_id,
                    fixture_display=fixture_display,
                    kickoff_local=self.kickoff_var.get().strip(),
                    app=self.app_var.get(),
                    market_original=preset["market_original"],
                    market_id=market_id,
                    selection_original=selection_original,
                    selection_id=selection_id,
                    line=self.line_var.get().strip(),
                    odds=odds,
                    promo="false",
                    source_image=source,
                    capture_time=capture,
                    notes=self.notes_var.get().strip(),
                )
                # Validate row-level requirements before appending.
                validate_rows([row])
                self.rows.append(row)
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        row.fixture_display,
                        row.app,
                        row.market_id,
                        row.selection_original,
                        row.line,
                        row.odds,
                    ),
                )
                added += 1
            if not added:
                raise ValueError("Enter at least one odds value for this market.")
            self.status.configure(text=f"Added {added} row(s). Total rows: {len(self.rows)}")
        except Exception as exc:  # GUI boundary: show clear user error.
            from tkinter import messagebox

            messagebox.showerror("Cannot add rows", str(exc))

    def delete_selected(self) -> None:
        selected = list(self.tree.selection())
        if not selected:
            return
        indices = [self.tree.index(item) for item in selected]
        for item in selected:
            self.tree.delete(item)
        for index in sorted(indices, reverse=True):
            del self.rows[index]
        self.status.configure(text=f"Deleted {len(selected)} row(s). Total rows: {len(self.rows)}")

    def save_done(self) -> None:
        try:
            csv_path, provenance_path, warnings = write_rows(
                self.rows, self.output_path, append=self.append.get()
            )
            message = f"Saved {len(self.rows)} row(s) to {csv_path}\nProvenance: {provenance_path}"
            if warnings:
                message += "\n\nWarnings:\n" + "\n".join(warnings)
            from tkinter import messagebox

            messagebox.showinfo("Saved manual odds", message)
            self.root.destroy()
        except Exception as exc:
            from tkinter import messagebox

            messagebox.showerror("Cannot save", str(exc))

    def run(self) -> None:
        """Start the GUI main loop."""
        self.root.mainloop()


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
    parser.add_argument("--diagnose-gui", action="store_true", help="Print expected GUI layout without opening a window.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0
    if args.diagnose_gui:
        print(json.dumps(gui_layout_spec(), indent=2, sort_keys=True))
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
    gui = ManualOddsGui(args.start, args.end, output, append=args.append)
    gui.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
