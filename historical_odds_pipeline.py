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
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
LEGACY = ROOT / "wc_backtest_historical_dataset.csv"
PROXY_OUT = ROOT / "historical_odds_proxy.csv"
COVERAGE_OUT = ROOT / "historical_odds_coverage.json"
PROVENANCE_OUT = ROOT / "historical_odds_provenance.txt"
FOOTBALL_DATA_RAW = ROOT / "data" / "historical_odds_raw" / "football_data"
FOOTBALL_DATA_OUT = ROOT / "historical_closing_odds_football_data.csv"
FOOTBALL_DATA_MANIFEST = FOOTBALL_DATA_RAW / "manifest.json"
CANONICAL_MANIFEST = ROOT / "historical_closing_odds_sources.json"
FOOTBALL_DATA_COVERAGE = ROOT / "historical_closing_odds_football_data_coverage.json"
THE_ODDS_API_SAMPLE_RAW = ROOT / "private_data" / "the_odds_api_samples"
THE_ODDS_API_SAMPLE_OUT = ROOT / "private_data" / "historical_odds_the_odds_api_samples.csv"
COMBINED_OUT = ROOT / "historical_closing_odds_canonical.csv"
COMBINED_COVERAGE = ROOT / "historical_closing_odds_canonical_coverage.json"
COMBINED_PROVENANCE = ROOT / "historical_closing_odds_canonical_provenance.txt"
THE_ODDS_API_SAMPLE_URLS = {
    "historical-epl.json": (
        "https://public-odds-api-sample-data.s3.amazonaws.com/"
        "historical-epl.json"
    ),
    "historical-bundesliga.json": (
        "https://public-odds-api-sample-data.s3.amazonaws.com/"
        "historical-bundesliga.json"
    ),
}

FOOTBALL_DATA_COMPETITIONS = {
    "E0": "English Premier League",
    "D1": "German Bundesliga",
    "I1": "Italian Serie A",
    "SP1": "Spanish La Liga",
    "F1": "French Ligue 1",
}
FOOTBALL_DATA_TIMEZONES = {
    "E0": "Europe/London",
    "D1": "Europe/London",
    "I1": "Europe/London",
    "SP1": "Europe/London",
    "F1": "Europe/London",
}
TEAM_ALIASES = {
    "astonvilla": "astonvilla",
    "bayerleverkusen": "leverkusen",
    "bayernmunich": "bayernmunich",
    "borussiadortmund": "dortmund",
    "borussiamonchengladbach": "mgladbach",
    "brightonandhovealbion": "brighton",
    "eintrachtfrankfurt": "einfrankfurt",
    "fsvmainz05": "mainz",
    "herthaberlin": "hertha",
    "leedsunited": "leeds",
    "leicestercity": "leicester",
    "manchestercity": "mancity",
    "manchesterunited": "manunited",
    "newcastleunited": "newcastle",
    "norwichcity": "norwich",
    "scfreiburg": "freiburg",
    "tottenhamhotspur": "tottenham",
    "tsghoffenheim": "hoffenheim",
    "vflbochum": "bochum",
    "vflwolfsburg": "wolfsburg",
    "vfbstuttgart": "stuttgart",
    "westhamunited": "westham",
    "wolverhamptonwanderers": "wolves",
}
FOOTBALL_DATA_SEASONS = ("2122", "2223", "2324", "2425", "2526")

FOOTBALL_DATA_BOOKMAKERS = {
    "bet365": {
        "1x2": ("B365CH", "B365CD", "B365CA"),
        "total_goals": ("B365C>2.5", "B365C<2.5"),
        "asian_handicap": ("B365CAHH", "B365CAHA"),
    },
    "pinnacle": {
        "1x2": ("PSCH", "PSCD", "PSCA"),
        "total_goals": ("PC>2.5", "PC<2.5"),
        "asian_handicap": ("PCAHH", "PCAHA"),
    },
    "betfair_exchange": {
        "1x2": ("BFECH", "BFECD", "BFECA"),
        "total_goals": ("BFEC>2.5", "BFEC<2.5"),
        "asian_handicap": ("BFECAHH", "BFECAHA"),
    },
}
MAX_PRIMARY_CLOSE_MINUTES = 120.0

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


def football_data_source_contract() -> List[Dict[str, str]]:
    """Return the frozen public Football-Data acquisition matrix."""
    sources = []
    for season in FOOTBALL_DATA_SEASONS:
        for division, competition in FOOTBALL_DATA_COMPETITIONS.items():
            sources.append({
                "source_id": f"football-data-{season}-{division}",
                "provider": "Football-Data",
                "competition": competition,
                "division": division,
                "season": f"20{season[:2]}-20{season[2:]}",
                "url": (
                    "https://www.football-data.co.uk/mmz4281/"
                    f"{season}/{division}.csv"
                ),
                "timestamp_semantics": (
                    "Provider-published closing columns; no row-level quote "
                    "timestamp."
                ),
                "redistribution_note": (
                    "Public CSV used for reproducible research. No explicit "
                    "redistribution license was found; recheck provider terms "
                    "before republishing or commercial use."
                ),
                "terms_url": "https://www.football-data.co.uk/data.php",
            })
    return sources


def acquire_football_data(
    raw_dir: Path = FOOTBALL_DATA_RAW,
    manifest_path: Path = FOOTBALL_DATA_MANIFEST,
) -> List[Dict[str, object]]:
    """Download the frozen public source matrix with immutable hashes.

    Existing byte-identical files are retained. A changed upstream file is
    replaced, but both the new hash and retrieval time are recorded in the
    manifest so normalization remains auditable.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    acquired: List[Dict[str, object]] = []
    for source in football_data_source_contract():
        target = raw_dir / f"{source['source_id']}.csv"
        request = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "WCdecider/closing-odds-research-v2"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
            last_modified = response.headers.get("Last-Modified", "")
        if not body or b"," not in body[:2048]:
            raise ValueError(f"Unexpected non-CSV payload: {source['url']}")
        target.write_bytes(body)
        acquired.append({
            **source,
            "local_path": str(target.relative_to(ROOT)),
            "bytes": len(body),
            "sha256": sha256(target),
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "http_content_type": content_type,
            "http_last_modified": last_modified,
        })
    manifest = {
        "schema_version": "football_data_source_manifest_v1",
        "source_index": "https://www.football-data.co.uk/data.php",
        "source_index_accessed_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": acquired,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return acquired


def acquire_the_odds_api_samples(
    raw_dir: Path = THE_ODDS_API_SAMPLE_RAW,
) -> List[Dict[str, object]]:
    """Acquire official public historical sample snapshots with sidecars."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    acquired = []
    for filename, url in THE_ODDS_API_SAMPLE_URLS.items():
        request = urllib.request.Request(
            url, headers={"User-Agent": "WCdecider/closing-odds-research-v2"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
            last_modified = response.headers.get("Last-Modified", "")
        json.loads(body.decode("utf-8"))
        path = raw_dir / filename
        path.write_bytes(body)
        metadata = {
            "provider": "The Odds API official sample",
            "public_request_url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "raw_sha256": sha256(path),
            "http_content_type": content_type,
            "http_last_modified": last_modified,
            "redistribution_note": (
                "Provider terms prohibit redistribution as downloadable data. "
                "Keep raw and normalized sample rows private."
            ),
            "terms_url": "https://the-odds-api.com/terms-and-conditions.html",
        }
        path.with_suffix(".metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        acquired.append({"local_path": str(path.relative_to(ROOT)), **metadata})
    return acquired


def parse_football_data_date(value: str, division: str) -> datetime:
    """Parse provider-local dates and attach the competition timezone."""
    for pattern in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(value.strip(), pattern)
            return parsed.replace(tzinfo=ZoneInfo(
                FOOTBALL_DATA_TIMEZONES[division]
            ))
        except ValueError:
            continue
    raise ValueError(f"Unsupported Football-Data date: {value}")


def valid_decimal(value: object) -> Optional[float]:
    """Return a finite decimal price greater than one, otherwise ``None``."""
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 1.0 else None


def normalize_football_data(
    manifest_path: Path = FOOTBALL_DATA_MANIFEST,
) -> List[Dict[str, object]]:
    """Normalize named-bookmaker provider-published closing columns."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output: List[Dict[str, object]] = []
    for source in manifest["sources"]:
        path = ROOT / source["local_path"]
        if sha256(path) != source["sha256"]:
            raise ValueError(f"Raw hash mismatch: {path}")
        rows = read_csv(path)
        for row_number, item in enumerate(rows, start=2):
            date_value = (item.get("Date") or "").strip()
            home = (item.get("HomeTeam") or "").strip()
            away = (item.get("AwayTeam") or "").strip()
            if not date_value or not home or not away:
                continue
            kickoff = parse_football_data_date(date_value, source["division"])
            time_value = (item.get("Time") or "").strip()
            if time_value:
                try:
                    hour, minute = [int(part) for part in time_value.split(":")]
                    kickoff = kickoff.replace(hour=hour, minute=minute)
                except (TypeError, ValueError):
                    pass
            home_goals = item.get("FTHG", "")
            away_goals = item.get("FTAG", "")
            try:
                hg = int(float(home_goals))
                ag = int(float(away_goals))
            except (TypeError, ValueError):
                hg = ag = None
            kickoff = kickoff.astimezone(timezone.utc)
            event_id = canonical_event_id(kickoff, home, away)
            common = {
                "event_id": event_id,
                "competition": source["competition"],
                "season": source["season"],
                "kickoff_utc": kickoff.isoformat(),
                "home_team": home,
                "away_team": away,
                "market_period": "full_time",
                "snapshot_time_utc": "",
                "bookmaker_update_time_utc": "",
                "minutes_before_kickoff": "",
                "evidence_class": "published_close_without_quote_timestamp",
                "is_primary_validation_eligible": "false",
                "result_home_goals": "" if hg is None else hg,
                "result_away_goals": "" if ag is None else ag,
                "source_provider": "Football-Data",
                "source_url": source["url"],
                "retrieved_at_utc": source["retrieved_at_utc"],
                "raw_sha256": source["sha256"],
                "license_note": source["redistribution_note"],
            }
            for bookmaker, markets in FOOTBALL_DATA_BOOKMAKERS.items():
                bookmaker_license = common["license_note"] + (
                    " Football-Data warns that Pinnacle prices have been "
                    "systematically outdated since 2025-07-23."
                    if bookmaker == "pinnacle"
                    and source["season"] == "2025-2026"
                    else ""
                )
                h_col, d_col, a_col = markets["1x2"]
                for selection, column in (
                    ("home", h_col), ("draw", d_col), ("away", a_col)
                ):
                    price = valid_decimal(item.get(column))
                    if price is None:
                        continue
                    output.append({
                        **common, "bookmaker": bookmaker,
                        "license_note": bookmaker_license,
                        "market_family": "1x2", "line": "",
                        "selection": selection, "decimal_odds": price,
                        "settlement": settle_1x2(selection, hg, ag),
                        "source_locator": f"{path.name}:row={row_number}:column={column}",
                    })
                over_col, under_col = markets["total_goals"]
                for selection, column in (
                    ("over", over_col), ("under", under_col)
                ):
                    price = valid_decimal(item.get(column))
                    if price is None:
                        continue
                    output.append({
                        **common, "bookmaker": bookmaker,
                        "license_note": bookmaker_license,
                        "market_family": "total_goals", "line": 2.5,
                        "selection": selection, "decimal_odds": price,
                        "settlement": (
                            "unsettled" if hg is None else
                            settle_total(selection, 2.5, hg, ag)
                        ),
                        "source_locator": f"{path.name}:row={row_number}:column={column}",
                    })
                home_col, away_col = markets["asian_handicap"]
                try:
                    home_line = float(item.get("AHCh", ""))
                except (TypeError, ValueError):
                    home_line = None
                if home_line is not None:
                    for selection, column in (
                        ("home", home_col), ("away", away_col)
                    ):
                        price = valid_decimal(item.get(column))
                        if price is None:
                            continue
                        output.append({
                            **common, "bookmaker": bookmaker,
                            "license_note": bookmaker_license,
                            "market_family": "asian_handicap",
                            "line": home_line, "selection": selection,
                            "decimal_odds": price,
                            "settlement": (
                                "unsettled" if hg is None else
                                settle_asian(selection, home_line, hg, ag)
                            ),
                            "source_locator": (
                                f"{path.name}:row={row_number}:column={column}"
                            ),
                        })
    output.sort(key=lambda row: (
        str(row["kickoff_utc"]), str(row["event_id"]), str(row["bookmaker"]),
        str(row["market_family"]), str(row["line"]), str(row["selection"]),
    ))
    return output


def build_football_data_dataset() -> Dict[str, object]:
    """Build the normalized public closing-column dataset and coverage."""
    rows = normalize_football_data()
    write_csv(FOOTBALL_DATA_OUT, rows)
    summary = coverage(rows)
    summary["source_files"] = len(json.loads(
        FOOTBALL_DATA_MANIFEST.read_text(encoding="utf-8")
    )["sources"])
    summary["bookmakers"] = dict(sorted(Counter(
        str(row["bookmaker"]) for row in rows
    ).items()))
    summary["seasons"] = dict(sorted(Counter(
        str(row["season"]) for row in rows
    ).items()))
    FOOTBALL_DATA_COVERAGE.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def build_canonical_dataset() -> Dict[str, object]:
    """Build the redistribution-safe public corpus and restricted-source index."""
    football_rows = normalize_football_data()
    existing_manifest = (
        json.loads(CANONICAL_MANIFEST.read_text(encoding="utf-8"))
        if CANONICAL_MANIFEST.exists() else {}
    )
    sample_rows = normalize_the_odds_api_payloads(THE_ODDS_API_SAMPLE_RAW)
    if sample_rows:
        THE_ODDS_API_SAMPLE_OUT.parent.mkdir(parents=True, exist_ok=True)
        write_csv(THE_ODDS_API_SAMPLE_OUT, sample_rows)
        restricted_summary = {
            "rows": len(sample_rows),
            "events": len({row["event_id"] for row in sample_rows}),
        }
    else:
        restricted_summary = existing_manifest.get(
            "restricted_validation_summary", {"rows": 0, "events": 0}
        )
    rows = football_rows
    write_csv(COMBINED_OUT, rows)
    summary = coverage(rows)
    summary["by_provider"] = dict(sorted(Counter(
        str(row["source_provider"]) for row in rows
    ).items()))
    summary["by_bookmaker"] = dict(sorted(Counter(
        str(row["bookmaker"]) for row in rows
    ).items()))
    summary["close_window_minutes"] = MAX_PRIMARY_CLOSE_MINUTES
    summary["restricted_validation_sources"] = {
        "provider": "The Odds API",
        "rows": restricted_summary["rows"],
        "events": restricted_summary["events"],
        "included_in_public_csv": False,
        "reason": "Provider terms prohibit downloadable redistribution.",
    }
    COMBINED_COVERAGE.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raw_files = sorted(FOOTBALL_DATA_RAW.glob("*.csv"))
    football_manifest = json.loads(
        FOOTBALL_DATA_MANIFEST.read_text(encoding="utf-8")
    )
    restricted_sources = []
    for path in sorted(THE_ODDS_API_SAMPLE_RAW.glob("*.metadata.json")):
        metadata = json.loads(path.read_text(encoding="utf-8"))
        restricted_sources.append({
            "source_id": path.name.removesuffix(".metadata.json"),
            "provider": metadata["provider"],
            "public_request_url": metadata["public_request_url"],
            "retrieved_at_utc": metadata["retrieved_at_utc"],
            "raw_sha256": metadata["raw_sha256"],
            "access_class": "private_validation_only",
            "redistribution_note": metadata["redistribution_note"],
            "terms_url": metadata["terms_url"],
        })
    if not restricted_sources:
        restricted_sources = existing_manifest.get(
            "restricted_validation_sources", []
        )
    CANONICAL_MANIFEST.write_text(
        json.dumps({
            "schema_version": "historical_odds_source_manifest_v2",
            "public_sources": football_manifest["sources"],
            "restricted_validation_sources": restricted_sources,
            "restricted_validation_summary": restricted_summary,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    COMBINED_PROVENANCE.write_text(
        "\n".join([
            "# Canonical historical closing-odds provenance",
            "",
            "Scope:",
            "- Football-Data: five major European leagues, 2021-22 through 2025-26.",
            "- The Odds API official samples are retained only in ignored private validation storage and excluded from the public CSV.",
            "- Markets: regular-time 1X2, Over/Under 2.5, and Asian handicap where published.",
            "- BTTS closing prices are unavailable in these source files and remain missing.",
            "",
            "Evidence classes:",
            "- published_close_without_quote_timestamp: provider closing columns, no row quote time; not primary-validation eligible.",
            "- timestamp_verified_bounded_close: named-bookmaker snapshot within 120 minutes before kickoff; primary eligible.",
            "- timestamp_verified_pre_event_snapshot: timestamped but more than 120 minutes before kickoff; not a close.",
            "",
            "Canonical columns:",
            "- event_id: deterministic cross-provider fixture identifier.",
            "- competition, season, kickoff_utc, home_team, away_team: event identity.",
            "- bookmaker: named bookmaker or exchange key.",
            "- market_family, market_period, line, selection: normalized settlement contract.",
            "- decimal_odds: source-published decimal price.",
            "- snapshot_time_utc, bookmaker_update_time_utc, minutes_before_kickoff: temporal evidence when available.",
            "- evidence_class, is_primary_validation_eligible: claim boundary.",
            "- result_home_goals, result_away_goals, settlement: final-score settlement.",
            "- source_provider, source_url, source_locator, retrieved_at_utc, raw_sha256: row lineage.",
            "- license_note: redistribution/access warning.",
            "",
            f"Rows: {summary['rows']}",
            f"Events: {summary['events']}",
            f"Primary validation rows: {summary['primary_validation_rows']}",
            f"Canonical CSV SHA-256: {sha256(COMBINED_OUT)}",
            "",
            "Raw source files:",
            *[
                f"- {path.relative_to(ROOT)} | sha256={sha256(path)}"
                for path in raw_files
            ],
            "",
            "Claim boundary:",
            "- This corpus materially upgrades market-baseline and secondary closing-line research.",
            "- Pinnacle 2025-26 rows carry Football-Data's warning that those prices have been systematically outdated since 2025-07-23.",
            "- It does not yet authorize ROI/CLV/profitability claims because no row meets the timestamp-verified <=120-minute closing gate.",
        ]) + "\n",
        encoding="utf-8",
    )
    return summary


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
    """Settle an Asian handicap, including quarter-line split stakes."""
    def component(line: float) -> str:
        adjusted = home + line - away
        result = "win" if adjusted > 0 else "push" if adjusted == 0 else "loss"
        if selection == "home":
            return result
        return {"win": "loss", "loss": "win", "push": "push"}[result]

    doubled = home_line * 2.0
    if abs(doubled - round(doubled)) < 1e-9:
        return component(home_line)
    lower = math.floor(doubled) / 2.0
    upper = math.ceil(doubled) / 2.0
    ordered = sorted(
        (component(lower), component(upper)),
        key={"loss": 0, "push": 1, "win": 2}.get,
    )
    if ordered[0] == ordered[1]:
        return ordered[0]
    return f"half_{ordered[0]}_half_{ordered[1]}"


def canonical_event_id(kickoff: datetime, home: str, away: str) -> str:
    """Return a provider-independent fixture key using UTC date and teams."""
    def team_key(value: str) -> str:
        raw = "".join(char.lower() for char in value if char.isalnum())
        return TEAM_ALIASES.get(raw, raw)

    key = (
        f"{kickoff.astimezone(timezone.utc).date().isoformat()}|"
        f"{team_key(home)}|{team_key(away)}"
    )
    return "match-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


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
        if path.name.endswith(".metadata.json"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshot_raw = payload.get("timestamp") or payload.get("previous_timestamp")
        events = payload.get("data", payload if isinstance(payload, list) else [])
        if not snapshot_raw or not isinstance(events, list):
            continue
        snapshot = parse_iso(snapshot_raw)
        raw_hash = sha256(path)
        metadata_path = path.with_suffix(".metadata.json")
        metadata = (
            json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata_path.exists() else {}
        )
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
                        minutes_before = (
                            kickoff - max(snapshot, update)
                        ).total_seconds() / 60.0
                        primary_eligible = (
                            0.0 < minutes_before <= MAX_PRIMARY_CLOSE_MINUTES
                        )
                        candidates[group].append({
                            "event_id": canonical_event_id(
                                kickoff, event["home_team"], event["away_team"]
                            ),
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
                            "minutes_before_kickoff": round(minutes_before, 3),
                            "evidence_class": (
                                "timestamp_verified_bounded_close"
                                if primary_eligible else
                                "timestamp_verified_pre_event_snapshot"
                            ),
                            "is_primary_validation_eligible": (
                                "true" if primary_eligible else "false"
                            ),
                            "result_home_goals": "",
                            "result_away_goals": "",
                            "settlement": "unsettled",
                            "source_provider": "The Odds API",
                            "source_url": metadata.get(
                                "public_request_url",
                                "https://the-odds-api.com/historical-odds-data/",
                            ),
                            "source_locator": str(path.relative_to(raw_dir)),
                            "retrieved_at_utc": metadata.get(
                                "retrieved_at_utc",
                                datetime.fromtimestamp(
                                    path.stat().st_mtime, timezone.utc
                                ).isoformat(),
                            ),
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
    sub.add_parser("acquire-football-data")
    sub.add_parser("acquire-the-odds-api-samples")
    sub.add_parser("build-football-data")
    sub.add_parser("build-canonical")
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
    if args.command == "acquire-football-data":
        acquired = acquire_football_data()
        print(f"Downloaded {len(acquired)} Football-Data source files")
        return
    if args.command == "acquire-the-odds-api-samples":
        acquired = acquire_the_odds_api_samples()
        print(f"Downloaded {len(acquired)} official sample snapshots")
        return
    if args.command == "build-football-data":
        summary = build_football_data_dataset()
        print(json.dumps(summary, sort_keys=True))
        return
    if args.command == "build-canonical":
        summary = build_canonical_dataset()
        print(json.dumps(summary, sort_keys=True))
        return
    rows = normalize_the_odds_api_payloads(args.raw_dir)
    if not rows:
        raise SystemExit("No eligible complete pre-kickoff snapshots found")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output, rows)
    print(json.dumps(coverage(rows), sort_keys=True))


if __name__ == "__main__":
    main()
