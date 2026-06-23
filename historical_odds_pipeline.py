#!/usr/bin/env python3
"""Historical closing-odds acquisition, normalization, and audit pipeline.

The pipeline deliberately separates three evidence classes:

``timestamp_verified_bounded_close``
    Last complete named-bookmaker snapshot strictly before kickoff. This is the
    only fixed-odds class eligible for primary profitability validation.
``published_close_without_quote_timestamp``
    A provider-published closing column with no row-level quote timestamp.
``legacy_proxy_unknown_timestamp``
    Existing project odds whose exact bookmaker/timestamp semantics cannot be
    reconstructed. These are retained for reconciliation, never promoted.

Examples
--------
Build the public, redistribution-safe proxy inventory::

    python3 -B historical_odds_pipeline.py build

Normalize previously downloaded The Odds API JSON snapshots::

    python3 -B historical_odds_pipeline.py normalize-the-odds-api \
        --raw-dir private_data/the_odds_api --output private_data/closing_odds.csv

Download calls are intentionally separate from normalization. Paid-provider raw
payloads may have redistribution restrictions and must not be committed without
written permission.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parent
LEGACY = ROOT / "wc_backtest_historical_dataset.csv"
PROXY_OUT = ROOT / "historical_odds_proxy.csv"
COVERAGE_OUT = ROOT / "historical_odds_coverage.json"
PROVENANCE_OUT = ROOT / "historical_odds_provenance.txt"

CANONICAL_FIELDS = (
    "event_id", "competition", "season", "kickoff_utc", "home_team",
    "away_team", "bookmaker", "market_family", "market_period", "line",
    "selection", "decimal_odds", "snapshot_time_utc",
    "bookmaker_update_time_utc", "minutes_before_kickoff", "evidence_class",
    "is_primary_validation_eligible", "result_home_goals",
    "result_away_goals", "settlement", "source_provider", "source_url",
    "source_locator", "retrieved_at_utc", "raw_sha256", "license_note",
)


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_FIELDS,
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_score(score: str) -> Tuple[Optional[int], Optional[int]]:
    try:
        left, right = score.strip().split("-", 1)
        return int(left), int(right)
    except (AttributeError, TypeError, ValueError):
        return None, None


def canonical_legacy_date(value: str) -> str:
    """Normalize legacy ISO or day-first dates to YYYY-MM-DD."""
    value = value.strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported legacy date: {value}")


def settle_1x2(selection: str, home: Optional[int],
                away: Optional[int]) -> str:
    """Settle a regular-time 1X2 selection."""
    if home is None or away is None:
        return "unsettled"
    outcome = "home" if home > away else "away" if away > home else "draw"
    return "win" if selection == outcome else "loss"


def settle_total(selection: str, line: float, home: int, away: int) -> str:
    """Settle a full/half-goal total. Quarter lines are split by the caller."""
    total = home + away
    if selection == "over":
        return "win" if total > line else "push" if total == line else "loss"
    return "win" if total < line else "push" if total == line else "loss"


def settle_asian(selection: str, home_line: float, home: int, away: int) -> str:
    """Settle one full/half Asian handicap from the home-line convention."""
    adjusted = home + home_line - away
    home_result = "win" if adjusted > 0 else "push" if adjusted == 0 else "loss"
    if selection == "home":
        return home_result
    return {"win": "loss", "loss": "win", "push": "push"}[home_result]


def legacy_proxy_rows() -> List[Dict[str, object]]:
    """Convert existing historical 1X2 values into an explicitly proxy table."""
    source_hash = sha256(LEGACY)
    # This timestamp describes the deterministic public conversion contract,
    # not an unverifiable original quote retrieval.
    retrieved = "2026-06-22T00:00:00+00:00"
    rows: List[Dict[str, object]] = []
    for item in read_csv(LEGACY):
        home_goals, away_goals = parse_score(item.get("score", ""))
        match_date = canonical_legacy_date(item["date"])
        for selection, column in (
            ("home", "o_win_a"), ("draw", "o_draw"), ("away", "o_win_b")
        ):
            raw = (item.get(column) or "").strip()
            if not raw:
                continue
            try:
                price = float(raw)
            except ValueError:
                continue
            if not math.isfinite(price) or price <= 1.0:
                continue
            rows.append({
                "event_id": item["match_id"],
                "competition": item["competition"],
                "season": match_date[:4],
                "kickoff_utc": f"{match_date}T00:00:00+00:00",
                "home_team": item["team_a_name"],
                "away_team": item["team_b_name"],
                "bookmaker": "unknown_or_aggregate",
                "market_family": "1x2",
                "market_period": "full_time",
                "line": "",
                "selection": selection,
                "decimal_odds": price,
                "snapshot_time_utc": "",
                "bookmaker_update_time_utc": "",
                "minutes_before_kickoff": "",
                "evidence_class": "legacy_proxy_unknown_timestamp",
                "is_primary_validation_eligible": "false",
                "result_home_goals": (
                    "" if home_goals is None else home_goals
                ),
                "result_away_goals": (
                    "" if away_goals is None else away_goals
                ),
                "settlement": settle_1x2(
                    selection, home_goals, away_goals
                ),
                "source_provider": "WCdecider legacy loader",
                "source_url": item.get("source_odds", ""),
                "source_locator": (
                    f"wc_backtest_historical_dataset.csv:"
                    f"{item['match_id']}:{column}"
                ),
                "retrieved_at_utc": retrieved,
                "raw_sha256": source_hash,
                "license_note": (
                    "Existing project value retained for reconciliation only; "
                    "bookmaker and quote timestamp are not row-verifiable."
                ),
            })
    rows.sort(key=lambda row: (
        str(row["kickoff_utc"]), str(row["event_id"]),
        str(row["selection"]),
    ))
    return rows


def parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp lacks timezone: {value}")
    return parsed.astimezone(timezone.utc)


def normalize_the_odds_api_payloads(
    raw_dir: Path,
) -> List[Dict[str, object]]:
    """Normalize and choose latest complete pre-kickoff bookmaker markets.

    Expected payloads are unmodified The Odds API historical event snapshots.
    The function supports ``h2h``, ``totals`` and ``spreads``. It never treats
    a snapshot at or after kickoff as a close.
    """
    candidates: Dict[Tuple[object, ...], List[Dict[str, object]]] = defaultdict(list)
    for path in sorted(raw_dir.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshot_raw = payload.get("timestamp") or payload.get("previous_timestamp")
        events = payload.get("data", payload if isinstance(payload, list) else [])
        if not snapshot_raw or not isinstance(events, list):
            continue
        snapshot = parse_iso(snapshot_raw)
        raw_hash = sha256(path)
        for event in events:
            kickoff = parse_iso(event["commence_time"])
            if snapshot >= kickoff:
                continue
            for bookmaker in event.get("bookmakers", []):
                update_raw = bookmaker.get("last_update") or snapshot_raw
                update = parse_iso(update_raw)
                if update >= kickoff:
                    continue
                for market in bookmaker.get("markets", []):
                    family = {
                        "h2h": "1x2", "totals": "total_goals",
                        "spreads": "asian_handicap",
                    }.get(market.get("key"))
                    if not family:
                        continue
                    outcomes = market.get("outcomes", [])
                    required = 3 if family == "1x2" else 2
                    if len(outcomes) < required:
                        continue
                    group = (
                        event["id"], bookmaker["key"], family,
                        tuple(sorted(
                            str(outcome.get("point", ""))
                            for outcome in outcomes
                        )),
                    )
                    for outcome in outcomes:
                        name = str(outcome["name"])
                        if family == "1x2":
                            selection = (
                                "home" if name == event["home_team"]
                                else "away" if name == event["away_team"]
                                else "draw"
                            )
                            line = ""
                        elif family == "total_goals":
                            selection = name.lower()
                            line = outcome.get("point", "")
                        else:
                            selection = (
                                "home" if name == event["home_team"] else "away"
                            )
                            line = outcome.get("point", "")
                        candidates[group].append({
                            "event_id": event["id"],
                            "competition": event.get("sport_title", ""),
                            "season": kickoff.strftime("%Y"),
                            "kickoff_utc": kickoff.isoformat(),
                            "home_team": event["home_team"],
                            "away_team": event["away_team"],
                            "bookmaker": bookmaker["key"],
                            "market_family": family,
                            "market_period": "full_time",
                            "line": line,
                            "selection": selection,
                            "decimal_odds": float(outcome["price"]),
                            "snapshot_time_utc": snapshot.isoformat(),
                            "bookmaker_update_time_utc": update.isoformat(),
                            "minutes_before_kickoff": round(
                                (kickoff - max(snapshot, update)).total_seconds()
                                / 60.0,
                                3,
                            ),
                            "evidence_class": "timestamp_verified_bounded_close",
                            "is_primary_validation_eligible": "true",
                            "result_home_goals": "",
                            "result_away_goals": "",
                            "settlement": "unsettled",
                            "source_provider": "The Odds API",
                            "source_url": "https://the-odds-api.com/historical-odds-data/",
                            "source_locator": str(path.relative_to(raw_dir)),
                            "retrieved_at_utc": datetime.fromtimestamp(
                                path.stat().st_mtime, timezone.utc
                            ).isoformat(),
                            "raw_sha256": raw_hash,
                            "license_note": (
                                "Raw provider data may not be redistributed; "
                                "keep private unless written permission exists."
                            ),
                            "_group": group,
                            "_close_time": max(snapshot, update),
                        })
    # Keep every selection belonging to the latest observed complete group.
    latest: Dict[Tuple[object, ...], datetime] = {}
    for group, rows in candidates.items():
        latest[group] = max(row["_close_time"] for row in rows)
    output = []
    for group, rows in candidates.items():
        close = latest[group]
        chosen = [row for row in rows if row["_close_time"] == close]
        for row in chosen:
            row.pop("_group", None)
            row.pop("_close_time", None)
            output.append(row)
    output.sort(key=lambda row: (
        str(row["kickoff_utc"]), str(row["event_id"]),
        str(row["bookmaker"]), str(row["market_family"]),
        str(row["line"]), str(row["selection"]),
    ))
    return output


def acquire_the_odds_api_snapshot(
    sport: str, snapshot_time: str, markets: str, regions: str,
    raw_dir: Path,
) -> Path:
    """Download one authenticated historical snapshot without transforming it.

    The API key is read only from ``THE_ODDS_API_KEY`` and is never written to
    disk. The request URL stored in metadata excludes the secret.
    """
    api_key = os.environ.get("THE_ODDS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "THE_ODDS_API_KEY is required; no historical odds were fabricated"
        )
    parse_iso(snapshot_time)
    public_params = {
        "regions": regions,
        "markets": markets,
        "date": snapshot_time,
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    private_params = {**public_params, "apiKey": api_key}
    endpoint = (
        "https://api.the-odds-api.com/v4/historical/sports/"
        f"{urllib.parse.quote(sport, safe='')}/odds/"
    )
    request = urllib.request.Request(
        endpoint + "?" + urllib.parse.urlencode(private_params),
        headers={"User-Agent": "WCdecider/closing-odds-research-v1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        headers = {
            key.lower(): value for key, value in response.headers.items()
            if key.lower().startswith("x-requests-")
        }
    json.loads(body.decode("utf-8"))  # fail before writing malformed payload
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = snapshot_time.replace(":", "").replace("+", "_")
    payload_path = raw_dir / f"{sport}_{stamp}_{markets}.json"
    payload_path.write_bytes(body)
    metadata = {
        "provider": "The Odds API",
        "public_request_url": endpoint + "?" + urllib.parse.urlencode(
            public_params
        ),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_sha256": sha256(payload_path),
        "response_usage_headers": headers,
        "redistribution_note": (
            "Keep raw payload private unless provider permission allows "
            "redistribution."
        ),
    }
    payload_path.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload_path


def coverage(rows: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    """Return transparent row/event/source coverage summaries."""
    events = {row["event_id"] for row in rows}
    by_class = Counter(str(row["evidence_class"]) for row in rows)
    by_market = Counter(str(row["market_family"]) for row in rows)
    by_competition = Counter(str(row["competition"]) for row in rows)
    eligible = [
        row for row in rows
        if str(row["is_primary_validation_eligible"]).lower() == "true"
    ]
    return {
        "schema_version": "historical_closing_odds_v1",
        "rows": len(rows),
        "events": len(events),
        "primary_validation_rows": len(eligible),
        "primary_validation_events": len({
            row["event_id"] for row in eligible
        }),
        "by_evidence_class": dict(sorted(by_class.items())),
        "by_market_family": dict(sorted(by_market.items())),
        "by_competition": dict(sorted(by_competition.items())),
        "profitability_validation_status": (
            "eligible_timestamped_rows_available"
            if eligible else "blocked_no_timestamp_verified_closing_rows"
        ),
    }


def build_public_proxy() -> None:
    rows = legacy_proxy_rows()
    write_csv(PROXY_OUT, rows)
    summary = coverage(rows)
    COVERAGE_OUT.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    PROVENANCE_OUT.write_text(
        "\n".join([
            "# Historical odds provenance",
            "",
            "Primary source contract:",
            "- The Odds API historical snapshots: timestamp-verified bounded close.",
            "- Betfair historical exchange stream: conditional independent benchmark.",
            "- Football-Data closing columns: secondary timestampless proxy only.",
            "",
            "Current public build:",
            f"- Input: {LEGACY.name}",
            f"- Input SHA-256: {sha256(LEGACY)}",
            f"- Rows: {summary['rows']}",
            f"- Events: {summary['events']}",
            "- Evidence class: legacy_proxy_unknown_timestamp",
            "- Primary profitability eligibility: zero rows.",
            "",
            "Reason: exact bookmaker, quote timestamp, kickoff time, and raw source "
            "payload are not row-verifiable in the legacy table. Values are retained "
            "for reconciliation only and cannot support ROI/CLV claims.",
        ]) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    normalize = sub.add_parser("normalize-the-odds-api")
    normalize.add_argument("--raw-dir", required=True, type=Path)
    normalize.add_argument("--output", required=True, type=Path)
    acquire = sub.add_parser("acquire-the-odds-api")
    acquire.add_argument("--sport", required=True)
    acquire.add_argument("--snapshot-time", required=True)
    acquire.add_argument("--markets", default="h2h,spreads,totals")
    acquire.add_argument("--regions", default="eu")
    acquire.add_argument("--raw-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "build":
        build_public_proxy()
        print(f"Wrote {PROXY_OUT.name}, {COVERAGE_OUT.name}, and {PROVENANCE_OUT.name}")
        return
    if args.command == "acquire-the-odds-api":
        path = acquire_the_odds_api_snapshot(
            args.sport, args.snapshot_time, args.markets,
            args.regions, args.raw_dir,
        )
        print(f"Wrote private raw snapshot {path}")
        return
    rows = normalize_the_odds_api_payloads(args.raw_dir)
    if not rows:
        raise SystemExit("No eligible complete pre-kickoff snapshots found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output, rows)
    print(json.dumps(coverage(rows), sort_keys=True))


if __name__ == "__main__":
    main()
