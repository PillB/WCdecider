#!/usr/bin/env python3
"""Reproducible June 27–29, 2026 World Cup prediction pipeline.

This module is intentionally stdlib-only. It reads:

* ``wc_backtest_historical_dataset.csv`` — historical Dataset A/B source.
* ``wc_2026_results_through_june26.csv`` — elapsed 2026 World Cup results.
* ``wc_team_elo_baseline_june11.csv`` — frozen pre-tournament Elo baseline.
* ``wc_2026_matches_june_27-29.csv`` — canonical current fixtures.
* ``manual_odds_20260627_20260629.csv`` — expert-entered current odds.
* ``odds_june*.csv`` — archived screenshot-derived odds, used only where no
  current manual row exists for an active fixture and normalized market key.

It writes:

* ``wc_dataset_a_world_cups.csv`` — World Cup rows only.
* ``wc_dataset_b_supplementary.csv`` — qualifiers/friendlies.
* ``wc_june22_27_model_dataset.csv`` — current engineered match rows.
* ``wc_odds_june_22-27.csv`` — merged normalized screenshot odds.
* ``wc_june22_27_predictions.json`` — website source of truth.
* ``wc_june22_27_model_metrics.json`` — temporal validation and model metadata.

No target probability or live odd is embedded in this file. Missing inputs,
malformed probabilities, duplicate fixtures, or unsupported silent fallbacks
raise an exception.

Example:
    $ python3 wc_june22_27_pipeline.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
HISTORICAL = ROOT / "wc_backtest_historical_dataset.csv"
RESULTS_2026 = ROOT / "wc_2026_results_through_june26.csv"
ELO_BASELINE = ROOT / "wc_team_elo_baseline_june11.csv"
FIXTURES = ROOT / "wc_2026_matches_june_27-29.csv"
ODDS_PARTS = (
    ROOT / "odds_june22_23.csv",
    ROOT / "odds_june24.csv",
    ROOT / "odds_june25_26.csv",
    ROOT / "odds_june27.csv",
)
MANUAL_ODDS_PATTERN = "manual_odds_*.csv"
MANUAL_ODDS_PREFERRED_AFTER = date(2026, 6, 26)
MANUAL_SOURCE_PREFIX = "manual_user_input_"
RAW_ODDS_FIELDS = (
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
)
ODDS_CAPTURE_DATE_BY_FILE = {
    "odds_june27.csv": "2026-06-21",
}
RESEARCH_PARTS = (
    ROOT / "research_june22_23.csv",
    ROOT / "research_june24_25.csv",
    ROOT / "research_june26_27.csv",
)

DATASET_A_OUT = ROOT / "wc_dataset_a_world_cups.csv"
DATASET_B_OUT = ROOT / "wc_dataset_b_supplementary.csv"
MODEL_DATA_OUT = ROOT / "wc_june22_27_model_dataset.csv"
ODDS_OUT = ROOT / "wc_odds_june_22-27.csv"
PREDICTIONS_OUT = ROOT / "wc_june22_27_predictions.json"
METRICS_OUT = ROOT / "wc_june22_27_model_metrics.json"
PROVENANCE_OUT = ROOT / "wc_june22_27_provenance.txt"
SCREENSHOT_MANIFEST_OUT = ROOT / "wc_screenshot_manifest_june22_27.csv"
RESEARCH_OUT = ROOT / "wc_research_june22_27.csv"

SEED = 42
EPS = 1e-12
BOOTSTRAP_NUMERIC_TOLERANCE = 1e-12
DATA_CUTOFF = datetime.fromisoformat("2026-06-27T11:00:00-05:00")
RELEASE_AS_OF = datetime.fromisoformat("2026-06-27T11:00:00-05:00")
FRESHNESS_HORIZON_HOURS = 48
HOSTS = {"USA", "CAN", "MEX"}

TEAM_ALIASES = {
    "argentina": "ARG", "austria": "AUT", "france": "FRA", "iraq": "IRQ",
    "norway": "NOR", "senegal": "SEN", "jordan": "JOR", "algeria": "ALG",
    "portugal": "POR", "uzbekistan": "UZB", "england": "ENG", "ghana": "GHA",
    "panama": "PAN", "croatia": "CRO", "colombia": "COL", "congo dr": "COD",
    "dr congo": "COD", "congo democratic republic": "COD",
    "bosnia and herzegovina": "BIH", "qatar": "QAT", "switzerland": "SUI",
    "canada": "CAN", "scotland": "SCO", "brazil": "BRA", "morocco": "MAR",
    "haiti": "HAI", "south africa": "RSA", "south korea": "KOR",
    "korea republic": "KOR", "czech republic": "CZE", "czechia": "CZE",
    "mexico": "MEX", "ecuador": "ECU", "germany": "GER", "curacao": "CUR",
    "curaçao": "CUR", "ivory coast": "CIV", "cote d'ivoire": "CIV",
    "côte d’ivoire": "CIV", "côte d'ivoire": "CIV", "tunisia": "TUN",
    "netherlands": "NED", "japan": "JPN", "sweden": "SWE",
    "paraguay": "PAR", "australia": "AUS", "turkey": "TUR", "turkiye": "TUR",
    "türkiye": "TUR", "usa": "USA", "united states": "USA", "uruguay": "URU",
    "spain": "ESP", "cape verde": "CPV", "cabo verde": "CPV",
    "saudi arabia": "KSA", "egypt": "EGY", "iran": "IRN",
    "new zealand": "NZL", "belgium": "BEL",
    "bosnia y herzegovina": "BIH", "catar": "QAT", "suiza": "SUI",
    "canada": "CAN", "escocia": "SCO", "brasil": "BRA", "marruecos": "MAR",
    "sudafrica": "RSA", "corea del sur": "KOR", "republica checa": "CZE",
    "chequia": "CZE", "alemania": "GER", "curazao": "CUR",
    "costa de marfil": "CIV", "tunez": "TUN", "paises bajos": "NED",
    "japon": "JPN", "suecia": "SWE", "turquia": "TUR",
    "estados unidos": "USA", "ee uu": "USA", "espana": "ESP", "cabo verde": "CPV",
    "arabia saudita": "KSA", "egipto": "EGY", "iran": "IRN",
    "nueva zelanda": "NZL", "belgica": "BEL", "inglaterra": "ENG",
    "croacia": "CRO", "panama": "PAN", "argelia": "ALG", "jordania": "JOR",
    "francia": "FRA", "irak": "IRQ", "noruega": "NOR", "austria": "AUT",
    "rd congo": "COD", "congo democra": "COD", "uzbekistan": "UZB",
}

CODE_NAMES = {
    "ARG": ("Argentina", "Argentina"), "AUT": ("Austria", "Austria"),
    "FRA": ("France", "Francia"), "IRQ": ("Iraq", "Irak"),
    "NOR": ("Norway", "Noruega"), "SEN": ("Senegal", "Senegal"),
    "JOR": ("Jordan", "Jordania"), "ALG": ("Algeria", "Argelia"),
    "POR": ("Portugal", "Portugal"), "UZB": ("Uzbekistan", "Uzbekistán"),
    "ENG": ("England", "Inglaterra"), "GHA": ("Ghana", "Ghana"),
    "PAN": ("Panama", "Panamá"), "CRO": ("Croatia", "Croacia"),
    "COL": ("Colombia", "Colombia"), "COD": ("Congo DR", "RD Congo"),
    "BIH": ("Bosnia and Herzegovina", "Bosnia y Herzegovina"),
    "QAT": ("Qatar", "Catar"), "SUI": ("Switzerland", "Suiza"),
    "CAN": ("Canada", "Canadá"), "SCO": ("Scotland", "Escocia"),
    "BRA": ("Brazil", "Brasil"), "MAR": ("Morocco", "Marruecos"),
    "HAI": ("Haiti", "Haití"), "RSA": ("South Africa", "Sudáfrica"),
    "KOR": ("South Korea", "Corea del Sur"), "CZE": ("Czechia", "Chequia"),
    "MEX": ("Mexico", "México"), "ECU": ("Ecuador", "Ecuador"),
    "GER": ("Germany", "Alemania"), "CUR": ("Curacao", "Curazao"),
    "CIV": ("Ivory Coast", "Costa de Marfil"), "TUN": ("Tunisia", "Túnez"),
    "NED": ("Netherlands", "Países Bajos"), "JPN": ("Japan", "Japón"),
    "SWE": ("Sweden", "Suecia"), "PAR": ("Paraguay", "Paraguay"),
    "AUS": ("Australia", "Australia"), "TUR": ("Turkiye", "Turquía"),
    "USA": ("USA", "Estados Unidos"), "URU": ("Uruguay", "Uruguay"),
    "ESP": ("Spain", "España"), "CPV": ("Cape Verde", "Cabo Verde"),
    "KSA": ("Saudi Arabia", "Arabia Saudita"), "EGY": ("Egypt", "Egipto"),
    "IRN": ("Iran", "Irán"), "NZL": ("New Zealand", "Nueva Zelanda"),
    "BEL": ("Belgium", "Bélgica"),
}

SCREENSHOT_GROUPS = (
    (7523, 7528, "2026-06-22-arg-aut"), (7529, 7532, "2026-06-22-fra-irq"),
    (7533, 7536, "2026-06-22-nor-sen"), (7537, 7540, "2026-06-22-jor-alg"),
    (7541, 7544, "2026-06-23-por-uzb"), (7545, 7548, "2026-06-23-eng-gha"),
    (7549, 7551, "2026-06-23-pan-cro"), (7552, 7555, "2026-06-23-col-cod"),
    (7556, 7558, "2026-06-24-bih-qat"), (7559, 7561, "2026-06-24-sui-can"),
    (7562, 7564, "2026-06-24-sco-bra"), (7565, 7567, "2026-06-24-mar-hai"),
    (7568, 7570, "2026-06-24-rsa-kor"), (7571, 7573, "2026-06-24-cze-mex"),
    (7574, 7577, "2026-06-25-ecu-ger"), (7578, 7581, "2026-06-25-cur-civ"),
    (7582, 7585, "2026-06-25-tun-ned"), (7586, 7587, "2026-06-25-jpn-swe"),
    (7589, 7591, "2026-06-25-par-aus"), (7592, 7594, "2026-06-25-tur-usa"),
    (7595, 7597, "2026-06-26-nor-fra"), (7598, 7600, "2026-06-26-sen-irq"),
    (7601, 7603, "2026-06-26-cpv-ksa"), (7604, 7607, "2026-06-26-uru-esp"),
    (7608, 7610, "2026-06-26-egy-irn"), (7611, 7614, "2026-06-26-nzl-bel"),
    (7615, 7618, "2026-06-22-arg-aut"), (7619, 7623, "2026-06-22-fra-irq"),
    (7624, 7628, "2026-06-22-nor-sen"), (7629, 7633, "2026-06-22-jor-alg"),
    (7634, 7637, "2026-06-23-por-uzb"), (7638, 7642, "2026-06-23-eng-gha"),
    (7643, 7647, "2026-06-23-pan-cro"), (7648, 7652, "2026-06-23-col-cod"),
    (7653, 7656, "2026-06-24-sui-can"), (7657, 7660, "2026-06-24-bih-qat"),
    (7661, 7664, "2026-06-24-sco-bra"), (7665, 7668, "2026-06-24-mar-hai"),
    (7669, 7672, "2026-06-24-rsa-kor"), (7673, 7677, "2026-06-24-cze-mex"),
    (7681, 7681, "2026-06-24-sui-can"), (7682, 7685, "2026-06-25-ecu-ger"),
    (7686, 7688, "2026-06-25-cur-civ"), (7690, 7693, "2026-06-25-tun-ned"),
    (7694, 7697, "2026-06-25-jpn-swe"), (7698, 7701, "2026-06-25-par-aus"),
    (7702, 7705, "2026-06-25-tur-usa"), (7706, 7709, "2026-06-26-nor-fra"),
    (7710, 7713, "2026-06-26-sen-irq"), (7714, 7717, "2026-06-26-uru-esp"),
    (7718, 7721, "2026-06-26-cpv-ksa"), (7722, 7725, "2026-06-27-cro-gha"),
    (7726, 7729, "2026-06-27-pan-eng"), (7730, 7733, "2026-06-27-col-por"),
    (7734, 7737, "2026-06-27-cod-uzb"), (7738, 7741, "2026-06-27-jor-arg"),
    (7742, 7745, "2026-06-27-alg-aut"),
)


def read_csv(path: Path) -> List[Dict[str, str]]:
    """Read a UTF-8 CSV and reject duplicate headers."""
    if not path.exists():
        raise FileNotFoundError(f"Required input is missing: {path.name}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"Invalid or duplicate CSV headers: {path.name}")
        return list(reader)


def write_csv(path: Path, rows: Sequence[Mapping[str, object]], fields: Sequence[str]) -> None:
    """Write deterministic UTF-8 CSV output."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fields),
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def canonical_float_text(value: float) -> str:
    """Return stable line text and collapse signed zero to plain 0.0."""
    number = 0.0 if abs(value) < EPS else value
    return f"{number:.2f}".rstrip("0").rstrip(".") if number % 1 else f"{number:.1f}"


def normalize_promo_flag(value: object) -> str:
    """Normalize promo values to true/false; ambiguous promo labels become true."""
    text = str(value or "").strip().lower()
    if text in {"", "false", "0", "no", "n"}:
        return "false"
    if text in {"true", "1", "yes", "y"}:
        return "true"
    return "true"


def freshness_status(kickoff: datetime) -> str:
    """Return freshness from the data cutoff instead of fixture-date rules.

    Forecasts more than 48 hours after the verified cutoff are conditional and
    must be rebuilt with intervening results, lineups, and current prices.
    """
    horizon = (kickoff - DATA_CUTOFF).total_seconds() / 3600.0
    return (
        "current_snapshot"
        if horizon <= FRESHNESS_HORIZON_HOURS
        else "conditional_requires_rerun_after_intervening_matches"
    )


def sha256(path: Path) -> str:
    """Return the SHA-256 hash of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_many(paths: Sequence[Path]) -> str:
    """Return one SHA-256 over named source files in deterministic order."""
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        digest.update(b"\0")
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    table = str.maketrans({"–": "-", "—": "-", "’": "'", "í": "i", "é": "e",
                           "á": "a", "ó": "o", "ú": "u", "ç": "c", "ã": "a"})
    return " ".join(value.lower().translate(table).replace(".", "").split())


def split_fixture(display: str) -> Tuple[str, str]:
    """Map a display fixture to stable team codes."""
    normalized = normalize_text(display).replace(" v ", " vs ")
    if " vs " not in normalized:
        raise ValueError(f"Cannot parse fixture display: {display!r}")
    left, right = (part.strip() for part in normalized.split(" vs ", 1))
    if left not in TEAM_ALIASES or right not in TEAM_ALIASES:
        raise ValueError(f"Unknown team alias in fixture: {display!r}")
    return TEAM_ALIASES[left], TEAM_ALIASES[right]


def selection_bucket(odd: Mapping[str, str], team_a: str, team_b: str) -> str:
    """Map a standard 1X2 selection to A/D/B using IDs or visible team labels."""
    sid = normalize_text(odd.get("selection_id", ""))
    label = normalize_text(odd.get("selection_original", ""))
    code = TEAM_ALIASES.get(label)
    if sid in {"home", "1", "visible_home"} or code == team_a:
        return "A"
    if sid == "draw" or label in {"draw", "empate", "x"}:
        return "D"
    if sid in {"away", "2", "visible_away"} or code == team_b:
        return "B"
    return ""


def outcome_code(score_a: int, score_b: int) -> str:
    return "A" if score_a > score_b else "B" if score_b > score_a else "D"


def parse_historical_date(raw: str) -> date:
    return datetime.strptime(raw, "%d/%m/%Y").date()


@dataclass(frozen=True)
class HistoricalRow:
    date: date
    competition: str
    weight: float
    team_a: str
    team_b: str
    elo_a: float
    elo_b: float
    outcome: str
    score_a: int
    score_b: int
    odds_a: Optional[float]
    odds_d: Optional[float]
    odds_b: Optional[float]


def parse_score(raw: str) -> Tuple[int, int]:
    a, b = raw.strip().split("-", 1)
    return int(a), int(b)


def load_historical() -> List[HistoricalRow]:
    rows: List[HistoricalRow] = []
    for row in read_csv(HISTORICAL):
        # Canonical 2026 rows are replaced below to avoid stale or duplicated results.
        if row["competition"] == "WC_2026_GROUP":
            continue
        sa, sb = parse_score(row["score"])
        rows.append(HistoricalRow(
            date=parse_historical_date(row["date"]),
            competition=row["competition"],
            weight=float(row["comp_weight"]),
            team_a=row["team_a"].strip(),
            team_b=row["team_b"].strip(),
            elo_a=float(row["elo_a_pre"]),
            elo_b=float(row["elo_b_pre"]),
            outcome=row["outcome"].strip(),
            score_a=sa,
            score_b=sb,
            odds_a=float(row["o_win_a"]) if row["o_win_a"] else None,
            odds_d=float(row["o_draw"]) if row["o_draw"] else None,
            odds_b=float(row["o_win_b"]) if row["o_win_b"] else None,
        ))
    baseline = {row["team"]: float(row["elo"]) for row in read_csv(ELO_BASELINE)}
    ratings = dict(baseline)
    for row in sorted(read_csv(RESULTS_2026), key=lambda item: item["date"]):
        accessed_at = datetime.fromisoformat(row["accessed_at"])
        # Result evidence may be retrieved after the modeling cutoff, provided
        # the match itself finished by the cutoff and retrieval precedes the
        # release timestamp. Treating retrieval time as event time would reject
        # legitimate post-match verification.
        if accessed_at > RELEASE_AS_OF:
            raise ValueError(
                f"Result accessed after release timestamp: {row['date']} "
                f"{row['team_a']}-{row['team_b']}"
            )
        if date.fromisoformat(row["date"]) > DATA_CUTOFF.date():
            raise ValueError(
                f"Result dated after data cutoff: {row['date']} "
                f"{row['team_a']}-{row['team_b']}"
            )
        team_a, team_b = row["team_a"], row["team_b"]
        sa, sb = int(row["score_a"]), int(row["score_b"])
        ea, eb = ratings[team_a], ratings[team_b]
        rows.append(HistoricalRow(
            date=date.fromisoformat(row["date"]),
            competition="WC_2026_GROUP",
            weight=1.0,
            team_a=team_a,
            team_b=team_b,
            elo_a=ea,
            elo_b=eb,
            outcome=outcome_code(sa, sb),
            score_a=sa,
            score_b=sb,
            odds_a=None, odds_d=None, odds_b=None,
        ))
        update_elo(ratings, team_a, team_b, sa, sb)
    return sorted(rows, key=lambda item: item.date)


def expected_score(elo_a: float, elo_b: float, divisor: float = 400.0) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / divisor))


def goal_margin_multiplier(margin: int) -> float:
    margin = abs(margin)
    if margin <= 1:
        return 1.0
    if margin == 2:
        return 1.5
    return (11.0 + margin) / 8.0


def update_elo(
    ratings: Dict[str, float], team_a: str, team_b: str, score_a: int, score_b: int,
    k: float = 60.0,
) -> None:
    """Apply a neutral-site World Cup Elo update in place."""
    ea, eb = ratings[team_a], ratings[team_b]
    actual = 1.0 if score_a > score_b else 0.0 if score_a < score_b else 0.5
    delta = k * goal_margin_multiplier(score_a - score_b) * (actual - expected_score(ea, eb))
    ratings[team_a] = ea + delta
    ratings[team_b] = eb - delta


def three_way_elo(
    elo_a: float, elo_b: float, divisor: float, draw_base: float, draw_slope: float,
    adjustment_a: float = 0.0, adjustment_b: float = 0.0,
) -> Tuple[float, float, float]:
    """Convert Elo win expectancy into calibrated 1X2 probabilities."""
    p_two = expected_score(elo_a + adjustment_a, elo_b + adjustment_b, divisor)
    closeness = 1.0 - abs(p_two - 0.5) * 2.0
    p_draw = max(0.12, min(0.34, draw_base + draw_slope * closeness))
    p_a = p_two * (1.0 - p_draw)
    p_b = (1.0 - p_two) * (1.0 - p_draw)
    total = p_a + p_draw + p_b
    return p_a / total, p_draw / total, p_b / total


def brier(prob: Tuple[float, float, float], outcome: str) -> float:
    target = {"A": (1.0, 0.0, 0.0), "D": (0.0, 1.0, 0.0), "B": (0.0, 0.0, 1.0)}[outcome]
    return sum((p - y) ** 2 for p, y in zip(prob, target))


def log_loss(prob: Tuple[float, float, float], outcome: str) -> float:
    idx = {"A": 0, "D": 1, "B": 2}[outcome]
    return -math.log(max(EPS, prob[idx]))


def temporal_folds(rows: Sequence[HistoricalRow], folds: int = 4) -> List[List[HistoricalRow]]:
    """Return date-blocked ordered evaluation windows.

    A calendar date is the smallest split unit. This prevents matches from the
    same matchday appearing in adjacent tuning windows.
    """
    n = len(rows)
    start = max(40, int(n * 0.55))
    while start < n and rows[start - 1].date == rows[start].date:
        start += 1
    remaining = n - start
    width = max(1, remaining // folds)
    windows = []
    lo = start
    for i in range(folds):
        hi = n if i == folds - 1 else min(n, lo + width)
        while hi < n and rows[hi - 1].date == rows[hi].date:
            hi += 1
        if lo < hi:
            windows.append(list(rows[lo:hi]))
        lo = hi
    return windows


def date_block_split(
    rows: Sequence[HistoricalRow], fraction: float,
) -> int:
    """Return a chronological split index that never divides one date."""
    if not rows:
        raise ValueError("Date-block split requires at least one row")
    target = min(len(rows) - 1, max(1, int(len(rows) * fraction)))
    while target < len(rows) and rows[target - 1].date == rows[target].date:
        target += 1
    if target >= len(rows):
        target = min(len(rows) - 1, max(1, int(len(rows) * fraction)))
        while target > 0 and rows[target - 1].date == rows[target].date:
            target -= 1
    if target <= 0 or target >= len(rows):
        raise ValueError("Date-block split requires at least two date blocks")
    return target


def calibrate_elo(rows: Sequence[HistoricalRow]) -> Dict[str, object]:
    """Select parameters on pre-holdout rows and report untouched final holdout."""
    configs = []
    holdout_start = date_block_split(rows, 0.85)
    selection_rows = rows[:holdout_start]
    holdout_rows = rows[holdout_start:]
    windows = temporal_folds(selection_rows)
    for divisor in (350.0, 400.0, 450.0, 500.0):
        for draw_base in (0.14, 0.16, 0.18, 0.20, 0.22):
            for draw_slope in (0.06, 0.08, 0.10, 0.12):
                fold_scores = []
                for window in windows:
                    bs, ll, ws = 0.0, 0.0, 0.0
                    for row in window:
                        p = three_way_elo(row.elo_a, row.elo_b, divisor, draw_base, draw_slope)
                        bs += brier(p, row.outcome) * row.weight
                        ll += log_loss(p, row.outcome) * row.weight
                        ws += row.weight
                    fold_scores.append((bs / ws, ll / ws))
                configs.append({
                    "divisor": divisor, "draw_base": draw_base, "draw_slope": draw_slope,
                    "mean_brier": sum(x[0] for x in fold_scores) / len(fold_scores),
                    "mean_log_loss": sum(x[1] for x in fold_scores) / len(fold_scores),
                    "folds": [{"brier": x[0], "log_loss": x[1]} for x in fold_scores],
                })
    best = min(configs, key=lambda item: (item["mean_log_loss"], item["mean_brier"]))
    bs = ll = ws = 0.0
    for row in holdout_rows:
        p = three_way_elo(
            row.elo_a, row.elo_b, best["divisor"], best["draw_base"], best["draw_slope"]
        )
        bs += brier(p, row.outcome) * row.weight
        ll += log_loss(p, row.outcome) * row.weight
        ws += row.weight
    best["selection_rows"] = len(selection_rows)
    best["holdout_rows"] = len(holdout_rows)
    best["holdout_brier"] = bs / ws
    best["holdout_log_loss"] = ll / ws
    return best


def poisson_pmf(lam: float, goals: int) -> float:
    return math.exp(-lam) * lam ** goals / math.factorial(goals)


def score_matrix(lam_a: float, lam_b: float, max_goals: int = 10) -> List[Tuple[int, int, float]]:
    matrix = []
    for ga in range(max_goals + 1):
        for gb in range(max_goals + 1):
            matrix.append((ga, gb, poisson_pmf(lam_a, ga) * poisson_pmf(lam_b, gb)))
    total = sum(p for _, _, p in matrix)
    return [(a, b, p / total) for a, b, p in matrix]


def dixon_coles_score_matrix(
    lam_a: float, lam_b: float, rho: float, max_goals: int = 10,
) -> List[Tuple[int, int, float]]:
    """Return a normalized Poisson score grid with low-score correction.

    ``rho=0`` reproduces independent Poisson. The correction is used as a
    shadow challenger until its improvement is statistically established.

    Example:
        >>> round(sum(p for _, _, p in dixon_coles_score_matrix(1.4, 1.1, -0.05)), 12)
        1.0
    """
    matrix = []
    for ga in range(max_goals + 1):
        for gb in range(max_goals + 1):
            tau = 1.0
            if ga == 0 and gb == 0:
                tau = 1.0 - lam_a * lam_b * rho
            elif ga == 0 and gb == 1:
                tau = 1.0 + lam_a * rho
            elif ga == 1 and gb == 0:
                tau = 1.0 + lam_b * rho
            elif ga == 1 and gb == 1:
                tau = 1.0 - rho
            probability = poisson_pmf(lam_a, ga) * poisson_pmf(lam_b, gb)
            matrix.append((ga, gb, max(EPS, tau) * probability))
    total = sum(p for _, _, p in matrix)
    return [(a, b, p / total) for a, b, p in matrix]


def expected_lambdas(
    elo_a: float, elo_b: float, mu_total: float, adj_a: float, adj_b: float,
    allocation: float = 0.34, gap_scale: float = 420.0,
    gap_intensity: float = 0.0,
) -> Tuple[float, float]:
    gap = (elo_a + adj_a) - (elo_b + adj_b)
    match_mu = max(
        1.5, min(4.5, mu_total + gap_intensity * abs(gap) / 400.0)
    )
    share = 0.5 + allocation * math.tanh(gap / gap_scale)
    return (
        max(0.12, match_mu * share),
        max(0.12, match_mu * (1.0 - share)),
    )


def score_model_metrics(
    rows: Sequence[HistoricalRow], mu_total: float, allocation: float,
    gap_scale: float, gap_intensity: float = 0.0, rho: float = 0.0,
) -> Dict[str, float]:
    """Evaluate a score model with proper scores on chronological rows."""
    nll = over25 = btts = weight_sum = 0.0
    for row in rows:
        la, lb = expected_lambdas(
            row.elo_a, row.elo_b, mu_total, 0.0, 0.0, allocation, gap_scale,
            gap_intensity,
        )
        matrix = dixon_coles_score_matrix(la, lb, rho)
        observed = next(
            (prob for ga, gb, prob in matrix if ga == row.score_a and gb == row.score_b),
            EPS,
        )
        p_over25 = event_probability(matrix, lambda ga, gb: ga + gb > 2.5)
        p_btts = event_probability(matrix, lambda ga, gb: ga > 0 and gb > 0)
        y_over25 = 1.0 if row.score_a + row.score_b > 2.5 else 0.0
        y_btts = 1.0 if row.score_a > 0 and row.score_b > 0 else 0.0
        nll += -math.log(max(EPS, observed)) * row.weight
        over25 += (p_over25 - y_over25) ** 2 * row.weight
        btts += (p_btts - y_btts) ** 2 * row.weight
        weight_sum += row.weight
    return {
        "score_nll": nll / weight_sum,
        "over_2_5_brier": over25 / weight_sum,
        "btts_brier": btts / weight_sum,
    }


def score_model_row_losses(
    rows: Sequence[HistoricalRow], mu_total: float, allocation: float,
    gap_scale: float, gap_intensity: float = 0.0, rho: float = 0.0,
) -> List[Dict[str, float]]:
    """Return row-level proper-score losses for paired model comparison."""
    losses = []
    for row in rows:
        la, lb = expected_lambdas(
            row.elo_a, row.elo_b, mu_total, 0.0, 0.0, allocation, gap_scale,
            gap_intensity,
        )
        matrix = dixon_coles_score_matrix(la, lb, rho)
        observed = next(
            (prob for ga, gb, prob in matrix if ga == row.score_a and gb == row.score_b),
            EPS,
        )
        p_over25 = event_probability(matrix, lambda ga, gb: ga + gb > 2.5)
        p_btts = event_probability(matrix, lambda ga, gb: ga > 0 and gb > 0)
        losses.append({
            "date_ordinal": float(row.date.toordinal()),
            "weight": row.weight,
            "score_nll": -math.log(max(EPS, observed)),
            "over_2_5_brier": (
                p_over25 - (1.0 if row.score_a + row.score_b > 2.5 else 0.0)
            ) ** 2,
            "btts_brier": (
                p_btts - (1.0 if row.score_a > 0 and row.score_b > 0 else 0.0)
            ) ** 2,
        })
    return losses


def paired_bootstrap_mean_difference(
    production: Sequence[Mapping[str, float]],
    challenger: Sequence[Mapping[str, float]],
    metric: str,
    iterations: int = 2000,
) -> Dict[str, object]:
    """Date-block bootstrap weighted challenger-minus-production loss.

    Reported score metrics use competition weights, so the comparison must use
    the same estimand. Resampling whole dates also preserves within-matchday
    dependence instead of treating every match as independent.
    """
    if len(production) != len(challenger) or not production:
        raise ValueError("Paired bootstrap requires equal non-empty row losses")
    blocks: Dict[int, List[Tuple[float, float]]] = defaultdict(list)
    for index in range(len(production)):
        if production[index]["date_ordinal"] != challenger[index]["date_ordinal"]:
            raise ValueError("Paired bootstrap rows must share the same date")
        blocks[int(production[index]["date_ordinal"])].append((
            challenger[index][metric] - production[index][metric],
            production[index]["weight"],
        ))
    ordered_blocks = [blocks[key] for key in sorted(blocks)]

    def weighted_mean(sampled_blocks: Sequence[Sequence[Tuple[float, float]]]) -> float:
        numerator = sum(
            difference * weight
            for block in sampled_blocks
            for difference, weight in block
        )
        denominator = sum(
            weight for block in sampled_blocks for _, weight in block
        )
        return numerator / denominator

    rng = random.Random(SEED)
    sampled_means = []
    for _ in range(iterations):
        sample = [
            ordered_blocks[rng.randrange(len(ordered_blocks))]
            for _ in range(len(ordered_blocks))
        ]
        sampled_means.append(weighted_mean(sample))
    sampled_means.sort()
    lower = sampled_means[int(iterations * 0.025)]
    upper = sampled_means[int(iterations * 0.975)]
    point = weighted_mean(ordered_blocks)
    return {
        "challenger_minus_production_mean": round(point, 12),
        "ci_95_lower": round(lower, 12),
        "ci_95_upper": round(upper, 12),
        "iterations": iterations,
        "resampling_method": "weighted_date_block_percentile_bootstrap",
        "block_count": len(ordered_blocks),
        "numeric_tolerance": BOOTSTRAP_NUMERIC_TOLERANCE,
        "statistically_secure_improvement": (
            upper < -BOOTSTRAP_NUMERIC_TOLERANCE
        ),
    }


def calibrate_score_model(rows: Sequence[HistoricalRow]) -> Dict[str, object]:
    """Select Elo-Poisson parameters before the untouched final holdout.

    Dixon-Coles is retained as a shadow challenger. Production remains
    independent Poisson unless a statistically secure improvement is shown.
    """
    holdout_start = date_block_split(rows, 0.85)
    selection_rows = rows[:holdout_start]
    holdout_rows = rows[holdout_start:]
    windows = temporal_folds(selection_rows)
    candidates = []
    for mu_total in (2.25, 2.5, 2.75, 3.0):
        for allocation in (0.30, 0.35, 0.40):
            for gap_scale in (350.0, 420.0, 500.0):
                for gap_intensity in (0.0, 0.15, 0.30, 0.45):
                    fold_metrics = [
                        score_model_metrics(
                            window, mu_total, allocation, gap_scale,
                            gap_intensity,
                        )
                        for window in windows
                    ]
                    candidates.append({
                        "mu_total": mu_total,
                        "allocation": allocation,
                        "gap_scale": gap_scale,
                        "gap_intensity": gap_intensity,
                        "mean_score_nll": sum(x["score_nll"] for x in fold_metrics) / len(fold_metrics),
                        "mean_over_2_5_brier": sum(x["over_2_5_brier"] for x in fold_metrics) / len(fold_metrics),
                        "mean_btts_brier": sum(x["btts_brier"] for x in fold_metrics) / len(fold_metrics),
                    })
    best = min(
        candidates,
        key=lambda item: (
            item["mean_score_nll"], item["mean_over_2_5_brier"],
            item["mean_btts_brier"],
        ),
    )
    shadow = []
    for rho in (-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15):
        fold_metrics = [
            score_model_metrics(
                window, best["mu_total"], best["allocation"],
                best["gap_scale"], best["gap_intensity"], rho,
            )
            for window in windows
        ]
        shadow.append({
            "rho": rho,
            "mean_score_nll": sum(x["score_nll"] for x in fold_metrics) / len(fold_metrics),
            "mean_over_2_5_brier": sum(x["over_2_5_brier"] for x in fold_metrics) / len(fold_metrics),
            "mean_btts_brier": sum(x["btts_brier"] for x in fold_metrics) / len(fold_metrics),
        })
    best_shadow = min(shadow, key=lambda item: item["mean_score_nll"])
    production_holdout = score_model_metrics(
        holdout_rows, best["mu_total"], best["allocation"], best["gap_scale"],
        best["gap_intensity"],
    )
    shadow_holdout = score_model_metrics(
        holdout_rows, best["mu_total"], best["allocation"],
        best["gap_scale"], best["gap_intensity"], best_shadow["rho"],
    )
    production_losses = score_model_row_losses(
        holdout_rows, best["mu_total"], best["allocation"], best["gap_scale"],
        best["gap_intensity"],
    )
    shadow_losses = score_model_row_losses(
        holdout_rows, best["mu_total"], best["allocation"],
        best["gap_scale"], best["gap_intensity"], best_shadow["rho"],
    )
    selection_weight = sum(row.weight for row in selection_rows)
    selection_over_rate = sum(
        row.weight * (row.score_a + row.score_b > 2.5)
        for row in selection_rows
    ) / selection_weight
    selection_btts_rate = sum(
        row.weight * (row.score_a > 0 and row.score_b > 0)
        for row in selection_rows
    ) / selection_weight
    holdout_weight = sum(row.weight for row in holdout_rows)
    baseline_over_brier = sum(
        row.weight * (
            selection_over_rate - (row.score_a + row.score_b > 2.5)
        ) ** 2
        for row in holdout_rows
    ) / holdout_weight
    baseline_btts_brier = sum(
        row.weight * (
            selection_btts_rate - (row.score_a > 0 and row.score_b > 0)
        ) ** 2
        for row in holdout_rows
    ) / holdout_weight
    return {
        **best,
        "tuning_status": "proper_score_tuned_not_empirically_calibrated",
        "selection_rows": len(selection_rows),
        "holdout_rows": len(holdout_rows),
        "production_model": "tuned_elo_independent_poisson",
        "production_holdout": production_holdout,
        "shadow_model": "dixon_coles_low_score_correction",
        "shadow_rho": best_shadow["rho"],
        "shadow_selection": best_shadow,
        "shadow_holdout": shadow_holdout,
        "holdout_selection_rate_baselines": {
            "selection_over_2_5_rate": selection_over_rate,
            "selection_btts_rate": selection_btts_rate,
            "over_2_5_brier": baseline_over_brier,
            "btts_brier": baseline_btts_brier,
        },
        "shadow_paired_bootstrap": {
            metric: paired_bootstrap_mean_difference(
                production_losses, shadow_losses, metric
            )
            for metric in ("score_nll", "over_2_5_brier", "btts_brier")
        },
        "policy_status": "experimental_non_actionable_no_historical_market_odds",
    }


def settle_line(value: float, line: float) -> float:
    """Return 1 win, 0 push, -1 loss for one Asian line."""
    adjusted = value + line
    return 1.0 if adjusted > 1e-9 else -1.0 if adjusted < -1e-9 else 0.0


def split_quarter_line(line: float) -> Tuple[float, ...]:
    doubled = line * 2.0
    if abs(doubled - round(doubled)) < 1e-9:
        return (line,)
    return (math.floor(doubled) / 2.0, math.ceil(doubled) / 2.0)


def settle_asian_handicap(
    margin: int, line: float, price: float,
) -> Tuple[float, float, float, float]:
    """Return win/push/loss equivalents and expected net for one score.

    Quarter lines split the stake equally over adjacent half-lines.

    Example:
        >>> settle_asian_handicap(1, -0.75, 2.0)
        (0.5, 0.5, 0.0, 0.5)
    """
    returns = []
    for subline in split_quarter_line(line):
        result = settle_line(margin, subline)
        returns.append(price if result > 0 else 1.0 if result == 0 else 0.0)
    gross = sum(returns) / len(returns)
    win_equivalent = max(0.0, min(1.0, (gross - 1.0) / (price - 1.0)))
    push_equivalent = sum(abs(value - 1.0) < 1e-9 for value in returns) / len(returns)
    loss_equivalent = max(0.0, 1.0 - win_equivalent - push_equivalent)
    return win_equivalent, push_equivalent, loss_equivalent, gross - 1.0


def parse_handicap_total_market(market_original: str) -> Optional[Tuple[float, float]]:
    """Extract the signed home-handicap and total lines from a combo label."""
    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", market_original)
    if len(numbers) < 2:
        return None
    return float(numbers[0]), float(numbers[-1])


def event_probability(
    matrix: Sequence[Tuple[int, int, float]],
    predicate: Callable[[int, int], bool],
) -> float:
    """Sum score-grid probability for a Boolean event."""
    return sum(probability for ga, gb, probability in matrix if predicate(ga, gb))


def fair_decimal(p_win: float, p_push: float = 0.0) -> Optional[float]:
    """Return break-even decimal odds, accounting for push probability."""
    p_loss = max(0.0, 1.0 - p_win - p_push)
    return None if p_win <= EPS else 1.0 + p_loss / p_win


def asian_probability(
    matrix: Sequence[Tuple[int, int, float]], selected_home: bool, line: float,
) -> Dict[str, float]:
    """Return price-independent Asian win/push/loss stake equivalents."""
    p_win = p_push = p_loss = 0.0
    sublines = split_quarter_line(line)
    for ga, gb, probability in matrix:
        margin = ga - gb if selected_home else gb - ga
        results = [settle_line(margin, subline) for subline in sublines]
        p_win += probability * sum(result > 0 for result in results) / len(results)
        p_push += probability * sum(result == 0 for result in results) / len(results)
        p_loss += probability * sum(result < 0 for result in results) / len(results)
    return {"p_win": p_win, "p_push": p_push, "p_loss": p_loss}


def common_market_probabilities(
    matrix: Sequence[Tuple[int, int, float]],
) -> Dict[str, object]:
    """Generate standard score-derived markets for every fixture."""
    p_home = event_probability(matrix, lambda ga, gb: ga > gb)
    p_draw = event_probability(matrix, lambda ga, gb: ga == gb)
    p_away = event_probability(matrix, lambda ga, gb: ga < gb)
    totals = []
    for line in (0.5, 1.5, 2.5, 3.5, 4.5, 5.5):
        p_over = event_probability(matrix, lambda ga, gb, ln=line: ga + gb > ln)
        p_under = 1.0 - p_over
        totals.append({
            "line": line,
            "over_probability": round(p_over, 6),
            "over_fair_odds": round(1.0 / p_over, 3),
            "under_probability": round(p_under, 6),
            "under_fair_odds": round(1.0 / p_under, 3),
        })
    p_btts = event_probability(matrix, lambda ga, gb: ga > 0 and gb > 0)
    exact_goal_buckets = []
    for total in range(5):
        probability = event_probability(
            matrix, lambda ga, gb, target=total: ga + gb == target
        )
        exact_goal_buckets.append({
            "total_goals": str(total),
            "probability": round(probability, 6),
            "fair_odds": round(1.0 / probability, 3),
        })
    p_five_plus = event_probability(matrix, lambda ga, gb: ga + gb >= 5)
    exact_goal_buckets.append({
        "total_goals": "5+",
        "probability": round(p_five_plus, 6),
        "fair_odds": round(1.0 / p_five_plus, 3),
    })
    top_correct_scores = sorted(
        matrix, key=lambda score: score[2], reverse=True
    )[:5]
    handicaps = []
    for home_line in (-2.5, -1.5, -0.5, 0.0, 0.5, 1.5, 2.5):
        home = asian_probability(matrix, True, home_line)
        away = asian_probability(matrix, False, -home_line)
        handicaps.append({
            "home_line": home_line,
            "home_probability": round(home["p_win"], 6),
            "home_push": round(home["p_push"], 6),
            "home_fair_odds": round(fair_decimal(home["p_win"], home["p_push"]) or 0.0, 3),
            "away_line": -home_line,
            "away_probability": round(away["p_win"], 6),
            "away_push": round(away["p_push"], 6),
            "away_fair_odds": round(fair_decimal(away["p_win"], away["p_push"]) or 0.0, 3),
        })
    return {
        "totals": totals,
        "btts": {
            "yes_probability": round(p_btts, 6),
            "yes_fair_odds": round(1.0 / p_btts, 3),
            "no_probability": round(1.0 - p_btts, 6),
            "no_fair_odds": round(1.0 / (1.0 - p_btts), 3),
        },
        "double_chance": {
            "home_or_draw_probability": round(p_home + p_draw, 6),
            "home_or_draw_fair_odds": round(1.0 / (p_home + p_draw), 3),
            "home_or_away_probability": round(p_home + p_away, 6),
            "home_or_away_fair_odds": round(1.0 / (p_home + p_away), 3),
            "draw_or_away_probability": round(p_draw + p_away, 6),
            "draw_or_away_fair_odds": round(1.0 / (p_draw + p_away), 3),
        },
        "total_goals_buckets": exact_goal_buckets,
        "top_correct_scores": [
            {
                "home_goals": ga,
                "away_goals": gb,
                "probability": round(probability, 6),
                "fair_odds": round(1.0 / probability, 3),
            }
            for ga, gb, probability in top_correct_scores
        ],
        "asian_handicap": handicaps,
        "policy_status": "experimental_non_actionable",
    }


def result_probabilities_from_matrix(
    matrix: Sequence[Tuple[int, int, float]],
) -> Tuple[float, float, float]:
    """Return home/draw/away probabilities implied by a score grid."""
    return (
        event_probability(matrix, lambda ga, gb: ga > gb),
        event_probability(matrix, lambda ga, gb: ga == gb),
        event_probability(matrix, lambda ga, gb: ga < gb),
    )


def research_mode_payload(
    production_matrix: Sequence[Tuple[int, int, float]],
    research_matrix: Sequence[Tuple[int, int, float]],
    score_config: Mapping[str, object],
) -> Dict[str, object]:
    """Serialize the gated research-mode shadow model for one fixture.

    The current best feasible research candidate is Dixon-Coles because it is
    already fitted as a low-parameter score-grid correction. High-capacity
    temporal graph and sequence models remain registry-only until the published
    sample-size and temporal-edge gates are met.
    """
    prod_home, prod_draw, prod_away = result_probabilities_from_matrix(
        production_matrix
    )
    res_home, res_draw, res_away = result_probabilities_from_matrix(
        research_matrix
    )
    prod_common = common_market_probabilities(production_matrix)
    res_common = common_market_probabilities(research_matrix)
    prod_over = next(
        row for row in prod_common["totals"] if float(row["line"]) == 2.5
    )
    res_over = next(
        row for row in res_common["totals"] if float(row["line"]) == 2.5
    )
    return {
        "toggle_available": True,
        "default_state": "off_production_mode",
        "selected_candidate": "dixon_coles_low_score_correction_shadow",
        "selected_family": "hierarchical_dynamic_poisson_score_research",
        "selected_from_registry_reason": (
            "Best currently feasible research-gated architecture: it adds a "
            "low-parameter football-specific low-score dependence correction "
            "without violating the current sample-size gate. Temporal GNN, "
            "GraphMixer/DyGFormer, and transformer candidates remain "
            "registered but not fit for production."
        ),
        "promotion_status": "research_gated_not_production",
        "production_recommendations_unchanged": True,
        "why_not_production": (
            "The paired-bootstrap confidence interval for score NLL crosses "
            "zero and timestamp-verified historical closing odds are absent, "
            "so this mode is educational/shadow analysis only."
        ),
        "rho": float(score_config["shadow_rho"]),
        "probabilities": {
            "team_a_win": round(res_home, 6),
            "draw": round(res_draw, 6),
            "team_b_win": round(res_away, 6),
        },
        "deltas_vs_production": {
            "team_a_win_pp": round((res_home - prod_home) * 100.0, 3),
            "draw_pp": round((res_draw - prod_draw) * 100.0, 3),
            "team_b_win_pp": round((res_away - prod_away) * 100.0, 3),
            "over_2_5_pp": round(
                (
                    float(res_over["over_probability"])
                    - float(prod_over["over_probability"])
                ) * 100.0,
                3,
            ),
            "btts_yes_pp": round(
                (
                    float(res_common["btts"]["yes_probability"])
                    - float(prod_common["btts"]["yes_probability"])
                ) * 100.0,
                3,
            ),
        },
        "common_markets": res_common,
        "student_note": {
            "en": (
                "Research mode shows the best currently reproducible gated "
                "shadow model. It is useful for learning and sensitivity "
                "analysis, not for replacing the production recommendation."
            ),
            "es": (
                "El modo investigación muestra el mejor modelo sombra "
                "reproducible y limitado por evidencia. Sirve para aprender "
                "y analizar sensibilidad, no para reemplazar la recomendación "
                "de producción."
            ),
        },
    }


def metric_explanations(
    team_a_names: Tuple[str, str], team_b_names: Tuple[str, str],
    p_1x2: Tuple[float, float, float], lambda_a: float, lambda_b: float,
    common: Mapping[str, object],
) -> Dict[str, Dict[str, Dict[str, str]]]:
    """Create bilingual, fixture-specific help for every compact metric box.

    Each explanation separates the category definition, the exact displayed
    value, and a practical interpretation. These are educational UI fields,
    not additional model inputs or betting instructions.
    """
    over_25 = next(
        row for row in common["totals"] if float(row["line"]) == 2.5
    )
    ah_minus_half = next(
        row for row in common["asian_handicap"]
        if float(row["home_line"]) == -0.5
    )

    def entry(
        en_title: str, es_title: str, en_meaning: str, es_meaning: str,
        en_number: str, es_number: str, en_action: str, es_action: str,
    ) -> Dict[str, Dict[str, str]]:
        return {
            "en": {
                "title": en_title,
                "category_meaning": en_meaning,
                "number_meaning": en_number,
                "what_you_can_do": en_action,
            },
            "es": {
                "title": es_title,
                "category_meaning": es_meaning,
                "number_meaning": es_number,
                "what_you_can_do": es_action,
            },
        }

    probability_action_en = (
        "Use it to compare outcomes and fair prices. It is not certainty; "
        "check the current app price and late team news before deciding."
    )
    probability_action_es = (
        "Úsalo para comparar resultados y cuotas justas. No es certeza; "
        "revisa la cuota actual y noticias tardías antes de decidir."
    )
    team_a_en, team_a_es = team_a_names
    team_b_en, team_b_es = team_b_names
    return {
        "team_a_win": entry(
            f"{team_a_en} win probability", f"Probabilidad de victoria de {team_a_es}",
            "The model probability that the first listed team wins after 90 minutes.",
            "La probabilidad del modelo de que el primer equipo gane tras 90 minutos.",
            f"{p_1x2[0] * 100:.1f}% means roughly {p_1x2[0] * 100:.0f} wins in 100 comparable model scenarios.",
            f"{p_1x2[0] * 100:.1f}% significa aproximadamente {p_1x2[0] * 100:.0f} victorias en 100 escenarios comparables del modelo.",
            probability_action_en, probability_action_es,
        ),
        "draw": entry(
            "Draw probability", "Probabilidad de empate",
            "The model probability that the score is level after 90 minutes.",
            "La probabilidad del modelo de que el marcador termine igualado tras 90 minutos.",
            f"{p_1x2[1] * 100:.1f}% means roughly {p_1x2[1] * 100:.0f} draws in 100 comparable model scenarios.",
            f"{p_1x2[1] * 100:.1f}% significa aproximadamente {p_1x2[1] * 100:.0f} empates en 100 escenarios comparables del modelo.",
            probability_action_en, probability_action_es,
        ),
        "team_b_win": entry(
            f"{team_b_en} win probability", f"Probabilidad de victoria de {team_b_es}",
            "The model probability that the second listed team wins after 90 minutes.",
            "La probabilidad del modelo de que el segundo equipo gane tras 90 minutos.",
            f"{p_1x2[2] * 100:.1f}% means roughly {p_1x2[2] * 100:.0f} wins in 100 comparable model scenarios.",
            f"{p_1x2[2] * 100:.1f}% significa aproximadamente {p_1x2[2] * 100:.0f} victorias en 100 escenarios comparables del modelo.",
            probability_action_en, probability_action_es,
        ),
        "expected_goals_team_a": entry(
            f"Expected goals: {team_a_en}", f"Goles esperados: {team_a_es}",
            "Expected goals here is the model's average goal count for the first listed team across many simulated versions of this match.",
            "Goles esperados es el promedio de goles del modelo para el primer equipo en muchas simulaciones de este partido.",
            f"{lambda_a:.2f} is an average, not a score prediction. For example, 0.51 means about half a goal per simulated match, so both 0 and 1 goal remain common outcomes.",
            f"{lambda_a:.2f} es un promedio, no un marcador exacto. Por ejemplo, 0,51 significa cerca de medio gol por simulación, por lo que 0 y 1 gol siguen siendo resultados comunes.",
            "Use it to understand scoring strength and to inspect team-total, BTTS, or handicap markets. Do not read 0.51 as a 51% chance.",
            "Úsalo para entender la capacidad goleadora y revisar totales de equipo, ambos marcan o hándicap. No interpretes 0,51 como 51% de probabilidad.",
        ),
        "expected_goals_team_b": entry(
            f"Expected goals: {team_b_en}", f"Goles esperados: {team_b_es}",
            "Expected goals here is the model's average goal count for the second listed team across many simulated versions of this match.",
            "Goles esperados es el promedio de goles del modelo para el segundo equipo en muchas simulaciones de este partido.",
            f"{lambda_b:.2f} is an average, not a score prediction. A value below 1.00 suggests a lower scoring outlook but does not mean the team cannot score.",
            f"{lambda_b:.2f} es un promedio, no un marcador exacto. Un valor menor que 1,00 sugiere menor expectativa goleadora, pero no significa que el equipo no pueda marcar.",
            "Use it to understand the second team's scoring outlook and to inspect team-total, BTTS, or handicap markets. It is not a percentage.",
            "Úsalo para entender la expectativa goleadora del segundo equipo y revisar totales, ambos marcan o hándicap. No es un porcentaje.",
        ),
        "over_2_5": entry(
            "Over 2.5 total goals", "Más de 2,5 goles totales",
            "This wins when the match has at least 3 total goals after 90 minutes.",
            "Gana cuando el partido termina con al menos 3 goles totales tras 90 minutos.",
            f"{over_25['over_probability'] * 100:.1f}% is the model probability; {over_25['over_fair_odds']:.2f} is the model's break-even decimal price before bookmaker margin.",
            f"{over_25['over_probability'] * 100:.1f}% es la probabilidad del modelo; {over_25['over_fair_odds']:.2f} es la cuota decimal de equilibrio antes del margen de la casa.",
            "Compare the current Over 2.5 price with the fair price. A higher app price may be more attractive, but model and lineup risk still apply.",
            "Compara la cuota actual de Más de 2,5 con la cuota justa. Una cuota mayor puede ser más atractiva, pero siguen existiendo riesgos del modelo y alineaciones.",
        ),
        "under_2_5": entry(
            "Under 2.5 total goals", "Menos de 2,5 goles totales",
            "This wins when the match has 0, 1, or 2 total goals after 90 minutes.",
            "Gana cuando el partido termina con 0, 1 o 2 goles totales tras 90 minutos.",
            f"{over_25['under_probability'] * 100:.1f}% is the model probability; {over_25['under_fair_odds']:.2f} is its break-even decimal price.",
            f"{over_25['under_probability'] * 100:.1f}% es la probabilidad del modelo; {over_25['under_fair_odds']:.2f} es su cuota decimal de equilibrio.",
            probability_action_en, probability_action_es,
        ),
        "btts_yes": entry(
            "Both teams to score: Yes", "Ambos equipos marcan: Sí",
            "This wins only when each team scores at least one goal after 90 minutes.",
            "Gana solo cuando cada equipo marca al menos un gol tras 90 minutos.",
            f"{common['btts']['yes_probability'] * 100:.1f}% is the model probability; {common['btts']['yes_fair_odds']:.2f} is the fair decimal price.",
            f"{common['btts']['yes_probability'] * 100:.1f}% es la probabilidad del modelo; {common['btts']['yes_fair_odds']:.2f} es la cuota decimal justa.",
            "Compare with the app's BTTS Yes price and inspect both teams' expected goals. One weak attack can make this fragile.",
            "Compara con la cuota Ambos marcan Sí y revisa los goles esperados de ambos equipos. Un ataque débil puede volverla frágil.",
        ),
        "btts_no": entry(
            "Both teams to score: No", "Ambos equipos marcan: No",
            "This wins when at least one team finishes with zero goals.",
            "Gana cuando al menos un equipo termina con cero goles.",
            f"{common['btts']['no_probability'] * 100:.1f}% is the model probability; {common['btts']['no_fair_odds']:.2f} is the fair decimal price.",
            f"{common['btts']['no_probability'] * 100:.1f}% es la probabilidad del modelo; {common['btts']['no_fair_odds']:.2f} es la cuota decimal justa.",
            "Inspect the weaker team's expected goals and compare the current BTTS No price with the fair price.",
            "Revisa los goles esperados del equipo más débil y compara la cuota Ambos marcan No con la cuota justa.",
        ),
        "home_minus_0_5": entry(
            f"{team_a_en} -0.5 Asian handicap", f"{team_a_es} -0,5 hándicap asiático",
            "At -0.5, the first listed team must win after 90 minutes; a draw or loss loses the selection.",
            "Con -0,5, el primer equipo debe ganar tras 90 minutos; empate o derrota pierde la selección.",
            f"{ah_minus_half['home_probability'] * 100:.1f}% is the model win probability; {ah_minus_half['home_fair_odds']:.2f} is the break-even decimal price.",
            f"{ah_minus_half['home_probability'] * 100:.1f}% es la probabilidad de victoria del modelo; {ah_minus_half['home_fair_odds']:.2f} es la cuota decimal de equilibrio.",
            "Compare the current -0.5 price with the fair price. This is effectively a match-win bet without a draw refund.",
            "Compara la cuota actual -0,5 con la cuota justa. Es equivalente a apostar por la victoria, sin devolución por empate.",
        ),
    }


def probability_and_ev(
    odd: Mapping[str, str], team_a: str, team_b: str,
    p_1x2: Tuple[float, float, float], matrix: Sequence[Tuple[int, int, float]],
) -> Optional[Dict[str, float]]:
    """Evaluate a supported screenshot market with exact score enumeration."""
    market = odd["market_id"]
    selection = normalize_text(odd["selection_original"])
    price = float(odd["odds"])
    if price <= 1.0:
        return None

    p_win = p_push = p_loss = 0.0
    selection_id = normalize_text(odd.get("selection_id", ""))
    if market == "match_result":
        bucket = selection_bucket(odd, team_a, team_b)
        if bucket == "A":
            probability = p_1x2[0]
        elif bucket == "B":
            probability = p_1x2[2]
        elif bucket == "D":
            probability = p_1x2[1]
        else:
            return None
        ev = probability * price - 1.0
        return {"p_win": probability, "p_push": 0.0, "p_loss": 1.0 - probability, "ev": ev}

    family = odd.get("market_family", "")
    if family == "total_goals" or market in {"total_goals", "number_of_goals", "number_of_goals_full_time"}:
        try:
            line = float(odd.get("total_line") or odd["line"])
        except (TypeError, ValueError):
            return None
        over = odd.get("selection_canonical") == "over" or selection.startswith(("over", "mas de"))
        under = odd.get("selection_canonical") == "under" or selection.startswith(("under", "menos"))
        if not (over or under):
            return None
        for ga, gb, prob in matrix:
            net = 0.0
            win_eq = push_eq = loss_eq = 0.0
            for subline in split_quarter_line(line):
                value = (ga + gb) - subline if over else subline - (ga + gb)
                result = 1.0 if value > 1e-9 else -1.0 if value < -1e-9 else 0.0
                net += (price - 1.0 if result > 0 else 0.0 if result == 0 else -1.0)
                win_eq += 1.0 if result > 0 else 0.0
                push_eq += 1.0 if result == 0 else 0.0
                loss_eq += 1.0 if result < 0 else 0.0
            divisor = len(split_quarter_line(line))
            p_win += prob * win_eq / divisor
            p_push += prob * push_eq / divisor
            p_loss += prob * loss_eq / divisor

    elif family == "btts" or market in {"both_teams_to_score", "btts"}:
        yes = selection in {"yes", "si", "sí"} or selection_id == "yes"
        no = selection == "no" or selection_id == "no"
        if not (yes or no):
            return None
        for ga, gb, prob in matrix:
            event = ga > 0 and gb > 0
            if event == yes:
                p_win += prob
            else:
                p_loss += prob

    elif family == "double_chance":
        canonical = odd.get("selection_canonical")
        p_home = event_probability(matrix, lambda ga, gb: ga > gb)
        p_draw = event_probability(matrix, lambda ga, gb: ga == gb)
        p_away = event_probability(matrix, lambda ga, gb: ga < gb)
        probability = {
            "AD": p_home + p_draw,
            "AB": p_home + p_away,
            "DB": p_draw + p_away,
        }.get(canonical)
        if probability is None:
            return None
        return {
            "p_win": probability, "p_push": 0.0,
            "p_loss": 1.0 - probability, "ev": probability * price - 1.0,
        }

    elif family == "asian_handicap" or market == "asian_handicap":
        try:
            line = float(odd.get("handicap_selected_line") or odd["line"])
        except (TypeError, ValueError):
            return None
        selected = odd.get("selected_team") or TEAM_ALIASES.get(selection)
        if selected is None and selection_id.startswith(("home", "visible_home", "1")):
            selected = team_a
        if selected is None and selection_id.startswith(("away", "visible_away", "2")):
            selected = team_b
        if selected not in {team_a, team_b}:
            return None
        expected_net = 0.0
        full_win_equivalent = 0.0
        full_push_equivalent = 0.0
        full_loss_equivalent = 0.0
        for ga, gb, prob in matrix:
            margin = ga - gb if selected == team_a else gb - ga
            win_eq, push_eq, loss_eq, net = settle_asian_handicap(margin, line, price)
            expected_net += prob * net
            full_win_equivalent += prob * win_eq
            full_push_equivalent += prob * push_eq
            full_loss_equivalent += prob * loss_eq
        return {
            "p_win": full_win_equivalent,
            "p_push": full_push_equivalent,
            "p_loss": full_loss_equivalent,
            "ev": expected_net,
        }
    elif family == "handicap_total_combo":
        raise ValueError(
            "handicap_total_combo settlement is disabled until an app-specific "
            "push/void/half-result contract is implemented and tested"
        )
    else:
        return None

    ev = p_win * (price - 1.0) - p_loss
    return {"p_win": p_win, "p_push": p_push, "p_loss": p_loss, "ev": ev}


def normalize_market_schema(
    row: Dict[str, str], team_a: str, team_b: str,
) -> Dict[str, str]:
    """Attach explicit settlement fields without guessing ambiguous contracts."""
    market = row["market_id"]
    row["promo"] = normalize_promo_flag(row.get("promo", "false"))
    promo_group = "promo" if row["promo"] == "true" else "standard"
    group_source = "|".join(
        str(row.get(key, "")).strip().replace("|", "/")
        for key in ("source_kind", "source_file", "source_image", "notes")
    )
    selection = normalize_text(row.get("selection_original", ""))
    selection_id = normalize_text(row.get("selection_id", ""))
    row.update({
        "market_family": "unsupported",
        "market_period": "full_time",
        "settlement_rule_id": "",
        "selected_team": "",
        "selection_canonical": "",
        "handicap_home_line": "",
        "handicap_selected_line": "",
        "total_line": "",
        "combo_leg_1_type": "",
        "combo_leg_1_selection": "",
        "combo_leg_1_line": "",
        "combo_leg_2_type": "",
        "combo_leg_2_selection": "",
        "combo_leg_2_line": "",
        "market_group_id": "",
        "is_complete_market": "false",
        "transcription_status": "transcribed",
        "transcription_confidence": "high",
    })

    if market == "match_result":
        bucket = selection_bucket(row, team_a, team_b)
        if bucket:
            row["market_family"] = "1x2"
            row["settlement_rule_id"] = "full_time_1x2_v1"
            row["selection_canonical"] = bucket
            if row["promo"] == "false":
                row["market_group_id"] = (
                    f"{row['fixture_id']}|{row['app']}|{promo_group}|"
                    f"{group_source}|1x2"
                )
    elif market in {"total_goals", "number_of_goals", "number_of_goals_full_time"}:
        canonical = "over" if selection.startswith(("over", "mas de")) else "under" if selection.startswith(("under", "menos")) else ""
        try:
            line = float(row["line"])
        except (TypeError, ValueError):
            line = None
        if canonical and line is not None:
            row["market_family"] = "total_goals"
            row["settlement_rule_id"] = "asian_total_score_grid_v1"
            row["selection_canonical"] = canonical
            line_text = canonical_float_text(line)
            row["line"] = line_text
            row["total_line"] = line_text
            if row["promo"] == "false":
                row["market_group_id"] = (
                    f"{row['fixture_id']}|{row['app']}|{promo_group}|"
                    f"{group_source}|total|{line_text}"
                )
    elif market in {"both_teams_to_score", "btts"}:
        canonical = "yes" if selection in {"yes", "si"} or selection_id == "yes" else "no" if selection == "no" or selection_id == "no" else ""
        if canonical:
            row["market_family"] = "btts"
            row["settlement_rule_id"] = "btts_full_time_v1"
            row["selection_canonical"] = canonical
            if row["promo"] == "false":
                row["market_group_id"] = (
                    f"{row['fixture_id']}|{row['app']}|{promo_group}|"
                    f"{group_source}|btts"
                )
    elif market == "double_chance":
        name_a = normalize_text(CODE_NAMES[team_a][0])
        name_b = normalize_text(CODE_NAMES[team_b][0])
        has_a = name_a in selection or normalize_text(CODE_NAMES[team_a][1]) in selection
        has_b = name_b in selection or normalize_text(CODE_NAMES[team_b][1]) in selection
        has_draw = "draw" in selection or "empate" in selection
        canonical = "AB" if has_a and has_b else "AD" if has_a and has_draw else "DB" if has_b and has_draw else ""
        if canonical:
            row["market_family"] = "double_chance"
            row["settlement_rule_id"] = "double_chance_1x2_v1"
            row["selection_canonical"] = canonical
            if row["promo"] == "false":
                row["market_group_id"] = (
                    f"{row['fixture_id']}|{row['app']}|{promo_group}|"
                    f"{group_source}|double_chance"
                )
    elif market == "asian_handicap":
        try:
            line = float(row["line"])
        except (TypeError, ValueError):
            line = None
        selected = TEAM_ALIASES.get(selection)
        if selected is None and selection_id.startswith(("home", "visible_home", "1")):
            selected = team_a
        if selected is None and selection_id.startswith(("away", "visible_away", "2")):
            selected = team_b
        if selected is None:
            for alias, code in sorted(TEAM_ALIASES.items(), key=lambda item: -len(item[0])):
                if selection_id.startswith(alias.replace(" ", "_")):
                    selected = code
                    break
        if selected in {team_a, team_b} and line is not None:
            row["market_family"] = "asian_handicap"
            row["settlement_rule_id"] = "asian_handicap_score_grid_v1"
            row["selected_team"] = selected
            row["selection_canonical"] = "home" if selected == team_a else "away"
            selected_line = line
            home_line = line if selected == team_a else -line
            selected_text = canonical_float_text(selected_line)
            home_text = canonical_float_text(home_line)
            row["line"] = selected_text
            row["handicap_selected_line"] = selected_text
            row["handicap_home_line"] = home_text
            if row["promo"] == "false":
                row["market_group_id"] = (
                    f"{row['fixture_id']}|{row['app']}|{promo_group}|"
                    f"{group_source}|asian|home_line={home_text}"
                )
    elif market in {"handicap_total", "handicap_total_goals_2_5"}:
        parsed = parse_handicap_total_market(row["market_original"])
        side = "home" if selection_id.startswith(("home", "1")) else "away" if selection_id.startswith(("away", "2")) else ""
        total_side = "over" if selection_id.endswith("over") else "under" if selection_id.endswith("under") else ""
        if parsed and side and total_side:
            home_line, total_line = parsed
            selected = team_a if side == "home" else team_b
            selected_line = home_line if side == "home" else -home_line
            row["market_family"] = "handicap_total_combo"
            row["settlement_rule_id"] = "asian_handicap_and_total_v1"
            row["selected_team"] = selected
            row["selection_canonical"] = f"{side}_{total_side}"
            row["handicap_home_line"] = str(home_line)
            row["handicap_selected_line"] = str(selected_line)
            row["total_line"] = str(total_line)
            row["combo_leg_1_type"] = "asian_handicap"
            row["combo_leg_1_selection"] = side
            row["combo_leg_1_line"] = str(selected_line)
            row["combo_leg_2_type"] = "total_goals"
            row["combo_leg_2_selection"] = total_side
            row["combo_leg_2_line"] = str(total_line)
            row["market_group_id"] = (
                f"{row['fixture_id']}|{row['app']}|combo|{home_line}|{total_line}"
            )
    return row


def mark_complete_markets(rows: List[Dict[str, str]]) -> None:
    """Mark only structurally complete market groups as eligible for EV."""
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["market_group_id"]:
            grouped[row["market_group_id"]].append(row)
    for group in grouped.values():
        family = group[0]["market_family"]
        selections = {row["selection_canonical"] for row in group}
        complete = (
            (family == "1x2" and selections == {"A", "D", "B"})
            or (family == "total_goals" and selections == {"over", "under"})
            or (family == "btts" and selections == {"yes", "no"})
            or (family == "double_chance" and selections == {"AD", "AB", "DB"})
            or (
                family == "asian_handicap"
                and len(group) == 2
                and selections == {"home", "away"}
                and len({
                    float(row["handicap_home_line"]) for row in group
                }) == 1
                and sorted(
                    float(row["handicap_selected_line"]) for row in group
                )[0]
                == -sorted(
                    float(row["handicap_selected_line"]) for row in group
                )[1]
            )
            # Combo contracts remain source evidence only until app-specific
            # push/void/half-result settlement rules are documented and tested.
        )
        for row in group:
            row["is_complete_market"] = "true" if complete else "false"


def manual_odds_provenance_path(csv_path: Path) -> Path:
    """Return the required provenance sidecar path for a manual odds CSV."""
    return csv_path.with_suffix(".provenance.json")


def discover_manual_odds_files(root: Path = ROOT) -> List[Path]:
    """Discover root-level manual odds files created by the input GUI."""
    return sorted(root.glob(MANUAL_ODDS_PATTERN))


def validate_manual_odds_provenance(csv_path: Path) -> Mapping[str, object]:
    """Validate the manual CSV sidecar before trusting user-entered odds."""
    provenance_path = manual_odds_provenance_path(csv_path)
    if not provenance_path.exists():
        raise FileNotFoundError(
            f"Manual odds provenance is missing: {provenance_path.name}"
        )
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "manual_wcdecider_odds_v1":
        raise ValueError(
            f"Unsupported manual odds provenance schema: {provenance_path.name}"
        )
    if Path(str(payload.get("output_csv", ""))).name != csv_path.name:
        raise ValueError(
            f"Manual odds provenance output_csv does not match: {provenance_path.name}"
        )
    if tuple(payload.get("fields", ())) != RAW_ODDS_FIELDS:
        raise ValueError(
            f"Manual odds provenance fields do not match raw odds schema: "
            f"{provenance_path.name}"
        )
    row_count = sum(1 for _ in read_csv(csv_path))
    if int(payload.get("row_count_written", -1)) != row_count:
        raise ValueError(
            f"Manual odds provenance row_count_written does not match CSV: "
            f"{provenance_path.name}"
        )
    return payload


def parse_odds_capture_time(
    row: Dict[str, str], path: Path, source_kind: str,
) -> datetime:
    """Parse capture time while preserving screenshot date metadata behavior."""
    capture_raw = row.get("capture_time", "").strip()
    if source_kind == "screenshot" and re.fullmatch(r"\d{2}:\d{2}", capture_raw):
        capture_date = ODDS_CAPTURE_DATE_BY_FILE.get(path.name)
        if not capture_date:
            raise ValueError(
                f"Time-only odds capture lacks source-date metadata: "
                f"{path.name} {capture_raw}"
            )
        capture_raw = f"{capture_date} {capture_raw} -05:00"
        row["capture_time"] = capture_raw
        row["capture_time_derivation"] = (
            f"date_from_frozen_file_metadata:{path.name}"
        )
    elif source_kind == "manual_user_input":
        if re.fullmatch(r"\d{2}:\d{2}", capture_raw):
            raise ValueError(
                f"Manual odds capture_time must include date and timezone: {path.name}"
            )
        row["capture_time_derivation"] = "manual_user_input_verbatim_timezone_aware"
    else:
        row["capture_time_derivation"] = "verbatim_timezone_aware"
    capture_at = datetime.fromisoformat(capture_raw.replace(" -05:00", "-05:00"))
    if capture_at.tzinfo is None:
        raise ValueError(f"Odds capture_time must be timezone-aware: {path.name}")
    return capture_at


def odds_preference_key(row: Mapping[str, str]) -> Tuple[str, str, str, str, str]:
    """Return the row key where manual odds may replace screenshot odds."""
    return (
        row["fixture_id"],
        row["app"],
        row["market_id"],
        row.get("selection_canonical") or row["selection_id"],
        row["line"],
    )


def load_and_merge_odds(fixtures: Sequence[Mapping[str, str]]) -> List[Dict[str, str]]:
    """Merge screenshot odds plus preferred manual post-June-26 overrides."""
    canonical = {}
    canonical_ids = {fixture["fixture_id"] for fixture in fixtures}
    kickoff_by_id = {fixture["fixture_id"]: fixture["kickoff_lima"] for fixture in fixtures}
    teams_by_id = {}
    for fixture in fixtures:
        a, b = split_fixture(fixture["match"])
        canonical[frozenset((a, b))] = fixture["fixture_id"]
        teams_by_id[fixture["fixture_id"]] = (a, b)

    def canonical_fixture_id(raw: Mapping[str, str]) -> str:
        if raw.get("fixture_id") in canonical_ids:
            return raw["fixture_id"]
        a, b = split_fixture(raw["fixture_display"])
        key = frozenset((a, b))
        if key not in canonical:
            raise ValueError(
                f"Odds fixture absent from canonical schedule: "
                f"{raw['fixture_display']}"
            )
        return canonical[key]

    def normalize_raw_row(
        raw: Mapping[str, str],
        path: Path,
        source_kind: str,
        source_sha256: str,
    ) -> Dict[str, str]:
        row = dict(raw)
        row["fixture_id"] = canonical_fixture_id(row)
        row["source_kind"] = source_kind
        row["source_file"] = path.name
        row["source_sha256"] = source_sha256
        row["kickoff_local"] = kickoff_by_id[row["fixture_id"]]
        capture_at = parse_odds_capture_time(row, path, source_kind)
        kickoff_at = datetime.fromisoformat(row["kickoff_local"])
        if source_kind == "screenshot" and capture_at > DATA_CUTOFF:
            raise ValueError(
                f"Odds captured after data cutoff: {row['source_image']}"
            )
        if capture_at >= kickoff_at:
            raise ValueError(
                f"Odds captured at/after kickoff: {row['source_image']}"
            )
        return normalize_market_schema(row, *teams_by_id[row["fixture_id"]])

    screenshot_rows: List[Dict[str, str]] = []
    for path in ODDS_PARTS:
        for row in read_csv(path):
            try:
                canonical_fixture_id(row)
            except ValueError:
                continue
            screenshot_rows.append(normalize_raw_row(
                row,
                path,
                "screenshot",
                sha256(ROOT / "Screenshots" / row["source_image"]),
            ))

    manual_rows: List[Dict[str, str]] = []
    for path in discover_manual_odds_files(ROOT):
        validate_manual_odds_provenance(path)
        source_sha = sha256(path)
        for row in read_csv(path):
            fixture_id = canonical_fixture_id(row)
            kickoff_day = date.fromisoformat(kickoff_by_id[fixture_id][:10])
            if kickoff_day <= MANUAL_ODDS_PREFERRED_AFTER:
                continue
            normalized = normalize_raw_row(row, path, "manual_user_input", source_sha)
            manual_rows.append(normalized)

    manual_keys = {odds_preference_key(row) for row in manual_rows}
    candidate_rows = [
        row for row in screenshot_rows
        if odds_preference_key(row) not in manual_keys
    ] + manual_rows

    merged_by_key: Dict[Tuple[str, ...], Dict[str, str]] = {}
    for row in candidate_rows:
        unique = (
            *odds_preference_key(row),
            row.get("odds", ""),
            row.get("source_kind", ""),
            row.get("source_file", ""),
            row.get("source_image", ""),
            row.get("capture_time", ""),
            row.get("notes", ""),
            row.get("promo", "false"),
        )
        merged_by_key[unique] = row
    merged = list(merged_by_key.values())
    mark_complete_markets(merged)
    merged.sort(key=lambda item: (
        item["fixture_id"], item["app"], item["market_id"],
        item["selection_id"], item["line"], item["source_image"],
    ))
    return merged


def load_research(fixtures: Sequence[Mapping[str, str]]) -> Dict[str, Dict[str, str]]:
    """Load fixture-level OSINT notes and require exact canonical coverage."""
    canonical_ids = {fixture["fixture_id"] for fixture in fixtures}
    merged: Dict[str, Dict[str, str]] = {}
    for path in RESEARCH_PARTS:
        for row in read_csv(path):
            fixture_id = row["fixture_id"]
            if fixture_id not in canonical_ids:
                continue
            if fixture_id in merged:
                raise ValueError(f"Duplicate research row: {fixture_id}")
            if "https://" not in row["source_urls"]:
                raise ValueError(f"Research row lacks direct URL: {fixture_id}")
            accessed_at = datetime.fromisoformat(row["accessed_at"])
            if accessed_at > DATA_CUTOFF:
                raise ValueError(
                    f"Research row accessed after cutoff: {fixture_id}"
                )
            # Fail closed on sources dated after the declared June 21 cutoff.
            if "/jun/22/" in row["source_urls"] or "/2026/jun/22/" in row["source_urls"]:
                row = dict(row)
                row["team_news_summary"] = "Reliable post-opening-match updates were unavailable by the June 21 research cutoff."
                row["injuries_suspensions"] = "Unavailable by the June 21 cutoff; later match reports were excluded."
                row["predicted_lineup_notes"] = "No confirmed lineup was available by the June 21 cutoff."
                row["motivation_group_state"] = "Final-round qualification state depended on intervening matches and was unavailable by the cutoff."
                row["weather_venue_notes"] = "Venue is documented in the canonical fixture file; reliable match-time weather was unavailable."
                row["source_urls"] = "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/match-center"
                row["confidence"] = "low"
            merged[fixture_id] = row
    missing = canonical_ids - set(merged)
    for fixture in fixtures:
        fixture_id = fixture["fixture_id"]
        if fixture_id not in missing:
            continue
        merged[fixture_id] = {
            "fixture_id": fixture_id,
            "team_news_summary": (
                "No fixture-specific OSINT note was available by the active "
                "June 27 cutoff; report uses schedule and verified-result "
                "context only."
            ),
            "injuries_suspensions": "Unavailable in canonical research files by cutoff.",
            "predicted_lineup_notes": "Unavailable in canonical research files by cutoff.",
            "motivation_group_state": (
                "Knockout or final-round qualification context is inferred "
                "only from verified schedule/result sources."
            ),
            "weather_venue_notes": fixture["venue"],
            "source_urls": fixture["schedule_source"],
            "accessed_at": DATA_CUTOFF.isoformat(),
            "confidence": "low",
        }
    return merged


def screenshot_manifest(odds: Sequence[Mapping[str, str]]) -> List[Dict[str, object]]:
    """Inventory every current screenshot, including images without transcribed selections."""
    odds_counts: Dict[str, int] = defaultdict(int)
    for row in odds:
        if row.get("source_kind", "screenshot") == "screenshot":
            odds_counts[row["source_image"]] += 1
    rows = []
    for path in sorted((ROOT / "Screenshots").glob("IMG_*.PNG")):
        number = int(path.stem.split("_")[1])
        fixture_id = next(
            (fixture for lo, hi, fixture in SCREENSHOT_GROUPS if lo <= number <= hi), ""
        )
        if not fixture_id:
            raise ValueError(f"Screenshot is not assigned to a fixture: {path.name}")
        rows.append({
            "source_image": path.name,
            "source_sha256": sha256(path),
            "fixture_id": fixture_id,
            "app": "Betsson" if number <= 7614 else "Betano",
            "transcribed_selection_rows": odds_counts[path.name],
            "inventory_status": "odds_transcribed" if odds_counts[path.name] else "reviewed_no_supported_row",
        })
    if len(rows) != 216:
        raise ValueError(f"Expected 216 current screenshots, found {len(rows)}")
    return rows


def current_team_state(
    results: Sequence[Mapping[str, str]], baseline: Mapping[str, float],
) -> Tuple[
    Dict[str, float],
    Dict[str, Dict[str, float]],
    Dict[str, date],
    Dict[Tuple[str, str, str], Tuple[float, float]],
    Dict[Tuple[str, str, str], Dict[str, object]],
]:
    """Replay results and retain leakage-safe pre-match ratings per fixture."""
    ratings = dict(baseline)
    form: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        "games": 0.0, "points": 0.0, "gf": 0.0, "ga": 0.0,
    })
    last_date: Dict[str, date] = {}
    pre_match_ratings: Dict[Tuple[str, str, str], Tuple[float, float]] = {}
    pre_match_context: Dict[
        Tuple[str, str, str], Dict[str, object]
    ] = {}
    for row in sorted(results, key=lambda item: item["date"]):
        ta, tb = row["team_a"], row["team_b"]
        sa, sb = int(row["score_a"]), int(row["score_b"])
        key = (row["date"], ta, tb)
        if key in pre_match_ratings:
            raise ValueError(f"Duplicate result key during Elo replay: {key}")
        pre_match_ratings[key] = (ratings[ta], ratings[tb])
        pre_match_context[key] = {
            "form_a": dict(form[ta]),
            "form_b": dict(form[tb]),
            "last_date_a": last_date.get(ta),
            "last_date_b": last_date.get(tb),
        }
        for team, gf, ga in ((ta, sa, sb), (tb, sb, sa)):
            form[team]["games"] += 1.0
            form[team]["gf"] += gf
            form[team]["ga"] += ga
            form[team]["points"] += 3.0 if gf > ga else 1.0 if gf == ga else 0.0
            last_date[team] = date.fromisoformat(row["date"])
        update_elo(ratings, ta, tb, sa, sb)
    return ratings, form, last_date, pre_match_ratings, pre_match_context


def form_adjustment(stats: Mapping[str, float]) -> float:
    games = max(1.0, stats.get("games", 0.0))
    ppg = stats.get("points", 0.0) / games
    gdpg = (stats.get("gf", 0.0) - stats.get("ga", 0.0)) / games
    return max(-45.0, min(45.0, (ppg - 1.35) * 12.0 + gdpg * 8.0))


def classify(ev_pct: float, divergence_pp: float) -> Tuple[str, int]:
    """Flag only anomaly-level disagreement/EV; PASS is not robustness."""
    if divergence_pp > 15.0 or ev_pct > 25.0:
        return "HALT", 35
    # Policy profitability has not yet been validated out of sample.
    return "PASS", 30


def recommendation_utility(row: Mapping[str, object]) -> float:
    """Rank sourced choices by stressed expected profit and model risk."""
    family_penalty = {
        "1x2": 0.0,
        "total_goals": 1.5,
        "btts": 2.0,
        "double_chance": 2.0,
        "asian_handicap": 3.0,
        "handicap_total_combo": 6.0,
    }
    conservative_ev = min(
        float(row["decision_ev_pct"]),
        float(row["decision_stressed_ev_pct"]),
    )
    disagreement_penalty = 0.35 * float(row["divergence_pp"])
    halt_penalty = 100.0 if row["strength"] == "HALT" else 0.0
    return (
        conservative_ev
        - disagreement_penalty
        - family_penalty.get(str(row["market_family"]), 8.0)
        - halt_penalty
    )


def recommendation_risk_grade(row: Mapping[str, object]) -> str:
    """Return an evidence-relative A–D risk grade, never a certainty grade."""
    utility = float(row["recommendation_utility"])
    divergence = float(row["divergence_pp"])
    if utility >= 3.0 and divergence <= 7.5 and row["strength"] != "HALT":
        return "A"
    if utility >= 0.0 and divergence <= 10.0 and row["strength"] != "HALT":
        return "B"
    if utility >= -6.0 and divergence <= 15.0:
        return "C"
    return "D"


def recommendation_equivalence_key(
    row: Mapping[str, object], team_a: str, team_b: str,
) -> Tuple[object, ...]:
    """Identify equivalent selections by their score-state settlement vector.

    This catches differently labeled but identical contracts, such as home 1X2
    and home -0.5 Asian handicap, without relying on translated market text.
    """
    family = str(row["market_family"])
    states = []
    for ga in range(11):
        for gb in range(11):
            win = push = loss = 0.0
            if family == "1x2":
                bucket = str(row["selection_canonical"])
                event = "A" if ga > gb else "B" if gb > ga else "D"
                win, loss = (1.0, 0.0) if bucket == event else (0.0, 1.0)
            elif family == "double_chance":
                bucket = str(row["selection_canonical"])
                event = "A" if ga > gb else "B" if gb > ga else "D"
                win, loss = (
                    (1.0, 0.0) if event in set(bucket) else (0.0, 1.0)
                )
            elif family == "btts":
                event = ga > 0 and gb > 0
                selected = str(row["selection_canonical"]) == "yes"
                win, loss = (1.0, 0.0) if event == selected else (0.0, 1.0)
            elif family == "total_goals":
                line = float(row["total_line"])
                over = str(row["selection_canonical"]) == "over"
                results = []
                for subline in split_quarter_line(line):
                    value = (
                        ga + gb - subline if over else subline - (ga + gb)
                    )
                    results.append(
                        1.0 if value > 1e-9 else
                        -1.0 if value < -1e-9 else 0.0
                    )
                win = sum(value > 0 for value in results) / len(results)
                push = sum(value == 0 for value in results) / len(results)
                loss = sum(value < 0 for value in results) / len(results)
            elif family == "asian_handicap":
                line = float(row["handicap_selected_line"])
                selected = str(row["selected_team"])
                margin = ga - gb if selected == team_a else gb - ga
                win, push, loss, _ = settle_asian_handicap(
                    margin, line, 2.0
                )
            elif family == "handicap_total_combo":
                raise ValueError(
                    "handicap_total_combo equivalence is disabled until an "
                    "app-specific settlement contract is implemented"
                )
            else:
                return ("unsupported", family, row.get("selection_original"))
            states.append((round(win, 3), round(push, 3), round(loss, 3)))
    return (str(row.get("market_period") or "full_time"), tuple(states))


def rank_distinct_recommendations(
    rows: Sequence[Mapping[str, object]], team_a: str, team_b: str,
    limit: int = 4,
) -> List[Tuple[Mapping[str, object], str]]:
    """Rank distinct sourced candidates without fabricating a fourth choice.

    Non-HALT rows rank first by the frozen uncertainty-adjusted utility. HALT
    rows may fill otherwise unavailable ranks, but remain visibly investigative.
    Equivalent events from multiple screenshots/apps are deduplicated after
    retaining the strongest executable sourced price.
    """
    ordered = sorted(
        rows,
        key=lambda row: (
            row["strength"] == "HALT",
            -float(row["recommendation_utility"]),
            -float(row["decision_stressed_ev_pct"]),
            -float(row["decision_ev_pct"]),
            float(row["odds"]),
            str(row["app"]),
            str(row["source_image"]),
        ),
    )
    if rows and not any(row["strength"] != "HALT" for row in rows):
        fallback = max(
            rows,
            key=lambda row: (
                float(row["market_probability"]),
                -float(row["odds"]),
            ),
        )
        ordered = [fallback] + [row for row in ordered if row is not fallback]
    selected: List[Tuple[Mapping[str, object], str]] = []
    seen = set()
    for row in ordered:
        key = recommendation_equivalence_key(row, team_a, team_b)
        if key in seen:
            continue
        seen.add(key)
        reason = (
            "highest_uncertainty_adjusted_expected_profit"
            if row["strength"] != "HALT"
            else (
                "all_model_edges_halted_select_highest_market_probability"
                if not selected else
                "investigative_halt_ranked_after_all_non_halt_candidates"
            )
        )
        selected.append((row, reason))
        if len(selected) == limit:
            break
    return selected


def public_recommendation(
    row: Mapping[str, object], rank: int, reason: str,
) -> Dict[str, object]:
    """Serialize one ranked recommendation from a normalized evaluated row."""
    published_win = round(float(row["decision_probability"]), 6)
    published_push = round(float(row["decision_push_probability"]), 6)
    published_loss = round(1.0 - published_win - published_push, 6)
    published_ev = (
        published_win * (float(row["odds"]) - 1.0) - published_loss
    ) * 100.0
    published_fair = 1.0 + published_loss / published_win
    market_probability = round(float(row["market_probability"]), 6)
    double_discount_threshold = round(published_win * 0.5, 6)
    double_discount_pass = market_probability <= double_discount_threshold
    return {
        "rank": rank,
        "app": row["app"], "market_id": row["market_id"],
        "market_family": row["market_family"],
        "market_original": row["market_original"],
        "selection_original": row["selection_original"],
        "selection_canonical": row["selection_canonical"],
        "line": row["line"], "odds": float(row["odds"]),
        "p_win": published_win,
        "model_p_win": round(float(row["p_win"]), 6),
        "p_push": published_push,
        "p_loss": published_loss,
        "market_probability": market_probability,
        "fair_odds": round(published_fair, 3),
        "ev_pct": round(published_ev, 2),
        "stressed_ev_pct": round(
            float(row["decision_stressed_ev_pct"]), 2
        ),
        "raw_model_ev_pct": round(float(row["ev_pct"]), 2),
        "decision_model_weight": row["decision_model_weight"],
        "decision_probability_method": row["decision_probability_method"],
        "divergence_pp": round(float(row["divergence_pp"]), 2),
        "strength": row["strength"], "confidence": row["confidence"],
        "recommendation_utility": round(
            float(row["recommendation_utility"]), 2
        ),
        "risk_grade": recommendation_risk_grade(row),
        "decision_status": (
            "BEST_AVAILABLE" if rank == 1 else "RANKED_ALTERNATIVE"
        ),
        "selection_reason": reason,
        "margin_of_safety": {
            "method": "double_discount_probability_gate",
            "required_market_probability_max": double_discount_threshold,
            "observed_market_probability": market_probability,
            "passes": double_discount_pass,
            "entry_authorized": False,
            "explanation": {
                "en": (
                    "Research-only double-discount check: the saved market "
                    "implied probability must be no more than half the model "
                    "decision probability. This is a margin-of-safety flag, "
                    "not proof of profit or authorization to bet."
                ),
                "es": (
                    "Chequeo de doble descuento solo de investigación: la "
                    "probabilidad implícita de la cuota guardada debe ser como "
                    "máximo la mitad de la probabilidad de decisión del modelo. "
                    "Es una señal de margen de seguridad, no prueba de beneficio "
                    "ni autorización para apostar."
                ),
            },
        },
        "profitability_validation": "not_validated_historical_market_odds",
        "source_image": row["source_image"],
        "source_sha256": row["source_sha256"],
    }


RISK_AVERSION_PROFILES: Tuple[Dict[str, object], ...] = (
    {
        "id": "exploratory",
        "label_en": "Exploratory",
        "label_es": "Exploratorio",
        "description_en": "Shows more candidate edges for research review; never treats them as validated profit.",
        "description_es": "Muestra más ventajas candidatas para revisión; nunca las trata como beneficio validado.",
        "max_divergence_pp": 22.5,
        "min_stressed_ev_pct": -20.0,
        "allowed_risk_grades": {"A", "B", "C", "D"},
    },
    {
        "id": "balanced",
        "label_en": "Balanced",
        "label_es": "Balanceado",
        "description_en": "Current production lens: accepts normal PASS rows and leaves suspicious rows as HALT.",
        "description_es": "Lente actual de producción: acepta filas PASS normales y deja filas sospechosas como HALT.",
        "max_divergence_pp": 15.0,
        "min_stressed_ev_pct": -8.0,
        "allowed_risk_grades": {"A", "B", "C", "D"},
    },
    {
        "id": "cautious",
        "label_en": "Cautious",
        "label_es": "Cauteloso",
        "description_en": "Requires non-negative stressed EV and lower model-market disagreement.",
        "description_es": "Exige EV estresado no negativo y menor desacuerdo modelo-mercado.",
        "max_divergence_pp": 10.0,
        "min_stressed_ev_pct": 0.0,
        "allowed_risk_grades": {"A", "B", "C"},
    },
    {
        "id": "strict",
        "label_en": "Strict",
        "label_es": "Estricto",
        "description_en": "Keeps only cleaner A/B-grade candidates with a positive stressed cushion.",
        "description_es": "Mantiene solo candidatas A/B más limpias con colchón estresado positivo.",
        "max_divergence_pp": 7.5,
        "min_stressed_ev_pct": 2.0,
        "allowed_risk_grades": {"A", "B"},
    },
    {
        "id": "audit_only",
        "label_en": "Audit only",
        "label_es": "Solo auditoría",
        "description_en": "Demands very low disagreement and strong stress evidence; most rows become HALT.",
        "description_es": "Exige desacuerdo muy bajo y fuerte evidencia estresada; la mayoría pasa a HALT.",
        "max_divergence_pp": 5.0,
        "min_stressed_ev_pct": 3.0,
        "allowed_risk_grades": {"A"},
    },
)


def risk_lens_for_recommendation(
    recommendation: Mapping[str, object],
) -> Dict[str, Dict[str, object]]:
    """Return profile-specific PASS/HALT treatment for one public candidate.

    These profiles are transparent decision lenses over the same sourced
    candidate. They do not mutate the published production recommendation or
    create new odds.
    """
    risk_grade = str(recommendation["risk_grade"])
    divergence = float(recommendation["divergence_pp"])
    stressed = float(recommendation["stressed_ev_pct"])
    price_gate_ok = (
        recommendation.get("price_gate_status")
        == "at_or_above_model_fair_price"
    )
    results: Dict[str, Dict[str, object]] = {}
    for profile in RISK_AVERSION_PROFILES:
        profile_id = str(profile["id"])
        threshold_passes = (
            divergence <= float(profile["max_divergence_pp"])
            and stressed >= float(profile["min_stressed_ev_pct"])
            and risk_grade in profile["allowed_risk_grades"]
        )
        passes = (
            recommendation["strength"] != "HALT"
            and threshold_passes
            and (
                profile_id in {"exploratory", "balanced"}
                or price_gate_ok
            )
        )
        reasons = []
        if divergence > float(profile["max_divergence_pp"]):
            reasons.append("model_market_disagreement_too_high")
        if stressed < float(profile["min_stressed_ev_pct"]):
            reasons.append("stress_ev_below_profile_threshold")
        if risk_grade not in profile["allowed_risk_grades"]:
            reasons.append("risk_grade_too_weak_for_profile")
        if profile_id not in {"exploratory", "balanced"} and not price_gate_ok:
            reasons.append("source_price_below_model_fair_threshold")
        if not reasons:
            reasons.append("passes_profile_thresholds")
        results[str(profile["id"])] = {
            "status": "PASS" if passes else "HALT",
            "requires_manual_review": not passes or recommendation["strength"] == "HALT",
            "reasons": reasons,
            "explanation": {
                "en": (
                    f"{'PASS' if passes else 'HALT'} under this lens: candidate "
                    f"divergence {divergence:.1f}pp vs maximum "
                    f"{float(profile['max_divergence_pp']):.1f}pp; stressed EV "
                    f"{stressed:.1f}% vs minimum "
                    f"{float(profile['min_stressed_ev_pct']):.1f}%; risk grade "
                    f"{risk_grade} vs allowed "
                    f"{'/'.join(sorted(profile['allowed_risk_grades']))}; fair-price "
                    f"gate {'met' if price_gate_ok else 'not met'}."
                ),
                "es": (
                    f"{'PASS' if passes else 'HALT'} con este lente: desacuerdo "
                    f"{divergence:.1f}pp frente al máximo "
                    f"{float(profile['max_divergence_pp']):.1f}pp; EV estresado "
                    f"{stressed:.1f}% frente al mínimo "
                    f"{float(profile['min_stressed_ev_pct']):.1f}%; grado de riesgo "
                    f"{risk_grade} frente a los permitidos "
                    f"{'/'.join(sorted(profile['allowed_risk_grades']))}; umbral de "
                    f"cuota justa {'cumplido' if price_gate_ok else 'no cumplido'}."
                ),
            },
            "profile_label": {
                "en": profile["label_en"],
                "es": profile["label_es"],
            },
            "profile_description": {
                "en": profile["description_en"],
                "es": profile["description_es"],
            },
        }
    return results


def attach_recommendation_context(
    recommendations: List[Dict[str, object]], fixture_names: Mapping[str, object],
    mode: str,
) -> None:
    """Attach user-facing context shared by production and research rankings."""
    for item in recommendations:
        item["price_gate_status"] = (
            "at_or_above_model_fair_price"
            if float(item["odds"]) >= float(item["fair_odds"])
            else "below_model_fair_price"
        )
        item["uncertainty"] = {
            "level": (
                "high" if item["strength"] == "HALT"
                or float(item["divergence_pp"]) > 10.0 else "material"
            ),
            "en": [
                "Small, shifted historical holdout.",
                "Screenshot price and team information can move before kickoff.",
                "Historical profitability is not validated.",
            ],
            "es": [
                "Holdout histórico pequeño y con cambio de régimen.",
                "La cuota y la información de equipos pueden cambiar antes del inicio.",
                "La rentabilidad histórica no está validada.",
            ],
        }
        item["why_ranked"] = {
            "en": (
                "Ranked by conservative expected-value utility after "
                "market disagreement and family-risk penalties."
                if mode == "production" else
                "Ranked by the research-gated shadow model against the same "
                "screenshot odds. This is sensitivity analysis, not a "
                "production replacement."
            ),
            "es": (
                "Clasificada por utilidad conservadora de valor esperado "
                "tras penalizar desacuerdo de mercado y riesgo del mercado."
                if mode == "production" else
                "Clasificada por el modelo sombra de investigación contra "
                "las mismas cuotas de capturas. Es análisis de sensibilidad, "
                "no reemplazo de producción."
            ),
        }
        item["display"] = recommendation_display_labels(
            fixture_names, item
        )
        item["steps"] = app_navigation_steps(
            str(item["app"]), fixture_names, item, None
        )
        if int(item["rank"]) == 1:
            item["steps"]["en"][-1] = (
                "Treat rank one as the primary comparison, not a mandatory "
                "bet. Recheck the selection, line, 90-minute settlement, "
                "current price, and team news before deciding."
                if mode == "production" else
                "Treat this research-mode rank one as a sensitivity check "
                "only. Do not replace the production recommendation unless "
                "the model promotion gates are passed in a future release."
            )
            item["steps"]["es"][-1] = (
                "Trata el rango uno como la comparación principal, no como "
                "apuesta obligatoria. Revisa selección, línea, liquidación "
                "a 90 minutos, cuota actual y noticias antes de decidir."
                if mode == "production" else
                "Trata este rango uno de investigación solo como prueba de "
                "sensibilidad. No reemplaza la recomendación de producción "
                "salvo que futuras puertas de promoción se superen."
            )
        item["risk_lens"] = risk_lens_for_recommendation(item)


def authorize_recommendations(
    recommendations: Sequence[Dict[str, object]],
    freshness: str,
    lifecycle_status: str,
) -> None:
    """Apply fail-closed gates while retaining rows as comparisons."""
    for item in recommendations:
        reasons = []
        if lifecycle_status != "future":
            reasons.append("fixture_elapsed_requires_verified_result")
        if freshness != "current_snapshot":
            reasons.append("forecast_requires_intervening_match_rerun")
        if item["strength"] == "HALT":
            reasons.append("model_market_anomaly_halt")
        if float(item["ev_pct"]) <= 0.0:
            reasons.append("non_positive_expected_value")
        if float(item["stressed_ev_pct"]) <= 0.0:
            reasons.append("non_positive_stressed_expected_value")
        if item["price_gate_status"] != "at_or_above_model_fair_price":
            reasons.append("source_price_below_model_fair_price")
        if item["market_family"] == "handicap_total_combo":
            reasons.append("combo_settlement_contract_not_validated")
        # No timestamp-eligible policy backtest exists in this release.
        reasons.append("historical_profitability_not_validated")
        item["decision_status"] = "ABSTAIN"
        item["actionability"] = {
            "data_valid": (
                lifecycle_status == "future"
                and freshness == "current_snapshot"
            ),
            "model_valid": item["strength"] != "HALT",
            "price_valid": (
                float(item["ev_pct"]) > 0.0
                and float(item["stressed_ev_pct"]) > 0.0
                and item["price_gate_status"]
                == "at_or_above_model_fair_price"
            ),
            "settlement_valid": (
                item["market_family"] != "handicap_total_combo"
            ),
            "profitability_valid": False,
            "actionable": False,
            "reasons": reasons,
        }
        if lifecycle_status != "future":
            item["steps"] = {
                "en": [
                    "This match is finished. Use this row only to compare the archived pre-match model with the verified result.",
                    "Do not search for or place this selection as a current bet.",
                ],
                "es": [
                    "Este partido terminó. Usa esta fila solo para comparar el modelo previo con el resultado verificado.",
                    "No busques ni realices esta selección como apuesta actual.",
                ],
            }
        elif freshness != "current_snapshot":
            item["steps"] = {
                "en": [
                    "STOP: do not use the saved sportsbook steps or price. This forecast requires a rerun after intervening matches and current team-news checks.",
                ],
                "es": [
                    "ALTO: no uses los pasos ni la cuota guardada. Este pronóstico requiere una nueva ejecución tras partidos intermedios y revisión de noticias actuales.",
                ],
            }
        item["watchlist_status"] = (
            "archived_result_no_bet"
            if lifecycle_status != "future"
            else "conditional_watchlist_requires_rerun"
            if freshness != "current_snapshot"
            else "best_available_watchlist_zero_stake"
        )
        item["watchlist_label"] = {
            "en": (
                "Archived pre-match comparison"
                if lifecycle_status != "future"
                else "Best available watchlist — not an authorized bet"
            ),
            "es": (
                "Comparación previa archivada"
                if lifecycle_status != "future"
                else "Mejor opción para vigilar — no es una apuesta autorizada"
            ),
        }


def risk_profile_summary(
    recommendations: Sequence[Mapping[str, object]],
) -> Dict[str, Dict[str, object]]:
    """Summarize PASS/HALT counts for each risk-aversion profile."""
    summary: Dict[str, Dict[str, object]] = {}
    for profile in RISK_AVERSION_PROFILES:
        profile_id = str(profile["id"])
        statuses = [
            rec.get("risk_lens", {}).get(profile_id, {}).get("status", "HALT")
            for rec in recommendations
        ]
        pass_count = sum(1 for status in statuses if status == "PASS")
        summary[profile_id] = {
            "label": {"en": profile["label_en"], "es": profile["label_es"]},
            "description": {
                "en": profile["description_en"],
                "es": profile["description_es"],
            },
            "pass_count": pass_count,
            "halt_count": len(statuses) - pass_count,
            "total_ranked": len(statuses),
            "recommended_rank": next(
                (
                    int(rec["rank"])
                    for rec in recommendations
                    if rec.get("risk_lens", {}).get(profile_id, {}).get("status")
                    == "PASS"
                ),
                None,
            ),
        }
    return summary


def sourced_candidate_key(row: Mapping[str, object]) -> Tuple[object, ...]:
    """Identify the same executable screenshot candidate across model views."""
    return (
        row.get("app"),
        row.get("source_image"),
        row.get("market_group_id"),
        row.get("market_family"),
        row.get("selection_canonical"),
        row.get("line"),
        row.get("handicap_selected_line"),
        row.get("total_line"),
        float(row.get("odds") or 0.0),
    )


def evaluate_sourced_markets(
    odds_rows: Sequence[Mapping[str, str]], team_a: str, team_b: str,
    p_1x2: Tuple[float, float, float],
    matrix: Sequence[Tuple[int, int, float]],
    stress_matrices: Sequence[Sequence[Tuple[int, int, float]]],
    market_consensus: Mapping[Tuple[str, str], float],
    market_overround: Mapping[str, float],
) -> List[Dict[str, object]]:
    """Evaluate all complete supported sourced markets for one model view."""
    expanded_rows: List[Dict[str, object]] = []
    for odd in odds_rows:
        if odd["is_complete_market"] != "true":
            continue
        if odd["market_family"] not in {
            "1x2", "total_goals", "btts", "double_chance",
            "asian_handicap",
        }:
            continue
        evaluated = probability_and_ev(odd, team_a, team_b, p_1x2, matrix)
        if evaluated is None:
            continue
        ev_pct = evaluated["ev"] * 100.0
        if odd["market_family"] == "1x2":
            stressed_ev = (
                max(0.0, evaluated["p_win"] - 0.03)
                * (float(odd["odds"]) - 1.0)
                - min(1.0, evaluated["p_loss"] + 0.03)
            ) * 100.0
            bucket = selection_bucket(odd, team_a, team_b)
            implied = market_consensus.get(
                (odd["app"], bucket), 1.0 / float(odd["odds"])
            )
        else:
            stress_values = [
                probability_and_ev(odd, team_a, team_b, p_1x2, stress_matrix)
                for stress_matrix in stress_matrices
            ]
            stressed_ev = min(
                value["ev"] * 100.0
                for value in stress_values if value is not None
            )
            implied = market_consensus.get(
                (odd["market_group_id"], odd["selection_canonical"]),
                1.0 / float(odd["odds"]),
            )
        divergence = abs(evaluated["p_win"] - implied) * 100.0
        strength, confidence = classify(ev_pct, divergence)
        # The quoted price is a comparison signal, not an input to the
        # probability used to evaluate that same price. Earlier releases
        # blended the model toward the market and then calculated EV from the
        # blend, creating a circular estimand. Keep forecast and market
        # probability separate unless a stack has earned out-of-sample weight.
        decision_win = float(evaluated["p_win"])
        decision_push = float(evaluated["p_push"])
        decision_loss = float(evaluated["p_loss"])
        decision_ev_pct = ev_pct
        decision_stressed_ev_pct = stressed_ev
        evaluated_row: Dict[str, object] = {
            **odd,
            **evaluated,
            "ev_pct": ev_pct,
            "stressed_ev_pct": stressed_ev,
            "divergence_pp": divergence,
            "market_overround_pct": market_overround.get(
                odd["market_group_id"], 0.0
            ) * 100.0,
            "decision_probability": decision_win,
            "decision_push_probability": decision_push,
            "decision_loss_probability": decision_loss,
            "market_probability": implied,
            "decision_ev_pct": decision_ev_pct,
            "decision_stressed_ev_pct": decision_stressed_ev_pct,
            "decision_model_weight": 1.0,
            "decision_probability_method": (
                "independent_structural_forecast_no_market_price_blend"
            ),
            "strength": strength,
            "confidence": confidence,
            "policy_status": "experimental_non_actionable",
        }
        evaluated_row["recommendation_utility"] = recommendation_utility(
            evaluated_row
        )
        expanded_rows.append(evaluated_row)
    return expanded_rows


def allocate_app_budget(
    rows: Sequence[Dict[str, object]], budget: float = 100.0,
    base_stake: float = 1.0, max_stake: float = 10.0,
) -> Dict[str, float]:
    """Allocate a fixed educational bankroll across one app's recommendations.

    Every sourced recommendation receives a small base amount because the user
    requested all-match coverage. Remaining money is weighted toward stronger
    stressed EV and lower diagnostic risk, with a hard 10% per-bet cap. The
    output is rounded to S/0.10 and sums exactly to the declared budget.
    """
    if not rows:
        return {}
    actionable_rows = [
        row for row in rows
        if row["rank_one_comparison"]["decision_status"] == "ACTIONABLE"
    ]
    stakes = {row["fixture_id"]: 0.0 for row in rows}
    if not actionable_rows:
        return stakes
    if (
        base_stake * len(actionable_rows) > budget
        or max_stake * len(actionable_rows) < budget
    ):
        raise ValueError("Bankroll constraints cannot cover actionable rows")

    scores = {}
    for row in actionable_rows:
        rec = row["rank_one_comparison"]
        risk_bonus = {
            "A": 1.5,
            "B": 1.0,
            "C": 0.5,
            "D": 0.0,
        }[str(rec["risk_grade"])]
        score = (
            0.25
            + max(0.0, float(rec["stressed_ev_pct"])) / 5.0
            + max(0.0, float(rec["ev_pct"])) / 10.0
            + risk_bonus
        )
        scores[row["fixture_id"]] = score
    for row in actionable_rows:
        stakes[row["fixture_id"]] = base_stake
    remaining = budget - base_stake * len(actionable_rows)
    active = {row["fixture_id"] for row in actionable_rows}
    while remaining > 1e-9 and active:
        total_score = sum(scores[key] for key in active)
        if total_score <= 0:
            total_score = float(len(active))
        allocations = {
            key: remaining * (
                scores[key] / total_score if total_score else 1.0 / len(active)
            )
            for key in active
        }
        used = 0.0
        capped = set()
        for key, extra in allocations.items():
            room = max_stake - stakes[key]
            addition = min(room, extra)
            stakes[key] += addition
            used += addition
            if room <= extra + 1e-9:
                capped.add(key)
        remaining -= used
        active -= capped
        if used <= 1e-9:
            break

    rounded = {
        key: (
            math.floor(value * 10.0 + 1e-9) / 10.0
            if key in active or value > 0.0 else 0.0
        )
        for key, value in stakes.items()
    }
    tenths_left = int(round((budget - sum(rounded.values())) * 10))
    actionable_ids = {row["fixture_id"] for row in actionable_rows}
    order = sorted(
        actionable_ids,
        key=lambda key: (
            stakes[key] - rounded[key], scores[key], key
        ),
        reverse=True,
    )
    index = 0
    while tenths_left > 0:
        key = order[index % len(order)]
        if rounded[key] + 0.1 <= max_stake + 1e-9:
            rounded[key] = round(rounded[key] + 0.1, 1)
            tenths_left -= 1
        index += 1
    if abs(sum(rounded.values()) - budget) > 1e-6:
        raise ValueError("Rounded bankroll allocation does not sum to budget")
    return rounded


SIMULATION_PROFILE_POLICY = {
    "exploratory": {
        "singles_fraction": 0.90,
        "accumulator_fraction": 0.10,
        "max_single_fraction": 0.20,
    },
    "balanced": {
        "singles_fraction": 0.95,
        "accumulator_fraction": 0.05,
        "max_single_fraction": 0.15,
    },
    "cautious": {
        "singles_fraction": 0.70,
        "accumulator_fraction": 0.03,
        "max_single_fraction": 0.12,
    },
    "strict": {
        "singles_fraction": 0.50,
        "accumulator_fraction": 0.02,
        "max_single_fraction": 0.10,
    },
    "audit_only": {
        "singles_fraction": 0.25,
        "accumulator_fraction": 0.0,
        "max_single_fraction": 0.08,
    },
}


def allocate_educational_simulation(
    rows: Sequence[Dict[str, object]],
    profile_id: str,
    budget: float = 100.0,
) -> Dict[str, float]:
    """Allocate one hypothetical single to every current fixture."""
    if profile_id not in SIMULATION_PROFILE_POLICY:
        raise ValueError(f"Unknown simulation profile: {profile_id}")
    if budget <= 0:
        raise ValueError("Simulation budget must be positive")
    current = [
        row for row in rows
        if row["fixture_lifecycle_status"] == "future"
        and row["freshness_status"] == "current_snapshot"
        and row.get("rank_one_comparison")
    ]
    stakes = {row["fixture_id"]: 0.0 for row in rows}
    if not current:
        return stakes
    policy = SIMULATION_PROFILE_POLICY[profile_id]
    max_stake = budget * policy["max_single_fraction"]
    deployable = round(
        min(budget * policy["singles_fraction"], max_stake * len(current)),
        2,
    )
    base_stake = min(1.0, deployable / len(current))
    scores: Dict[str, float] = {}
    for row in current:
        rec = row["rank_one_comparison"]
        grade_bonus = {"A": 1.4, "B": 1.0, "C": 0.6, "D": 0.3}.get(
            str(rec["risk_grade"]), 0.2
        )
        scores[row["fixture_id"]] = max(
            0.1,
            0.5
            + grade_bonus
            + max(-10.0, min(10.0, float(rec["stressed_ev_pct"]))) / 20.0
            + max(-20.0, min(20.0, float(rec["ev_pct"]))) / 40.0,
        )
        stakes[row["fixture_id"]] = base_stake
    remaining = deployable - base_stake * len(current)
    active = {row["fixture_id"] for row in current}
    while remaining > 1e-9 and active:
        total_score = sum(scores[key] for key in active)
        used = 0.0
        capped = set()
        for key in sorted(active):
            extra = remaining * scores[key] / total_score
            room = max_stake - stakes[key]
            addition = min(room, extra)
            stakes[key] += addition
            used += addition
            if room <= extra + 1e-9:
                capped.add(key)
        remaining -= used
        active -= capped
        if used <= 1e-9:
            break
    rounded = {
        key: math.floor(value * 10.0 + 1e-9) / 10.0
        for key, value in stakes.items()
    }
    tenths_left = int(round((deployable - sum(rounded.values())) * 10))
    order = sorted(
        (row["fixture_id"] for row in current),
        key=lambda key: (stakes[key] - rounded[key], scores[key], key),
        reverse=True,
    )
    index = 0
    while tenths_left > 0:
        key = order[index % len(order)]
        if rounded[key] + 0.1 <= max_stake + 1e-9:
            rounded[key] = round(rounded[key] + 0.1, 1)
            tenths_left -= 1
        index += 1
    if abs(sum(rounded.values()) - deployable) > 1e-6:
        raise ValueError("Rounded simulation allocation does not match profile")
    return rounded


def attach_educational_stake_simulation(
    predictions: Sequence[Dict[str, object]],
) -> Dict[str, object]:
    """Attach S/100-per-app singles plus capped accumulator simulations."""
    apps: Dict[str, object] = {}
    for app in ("Betano", "Betsson"):
        app_rows = [
            row for row in predictions
            if row["rank_one_comparison"]["app"] == app
        ]
        current_rows = [
            row for row in app_rows
            if row["fixture_lifecycle_status"] == "future"
            and row["freshness_status"] == "current_snapshot"
        ]
        if not current_rows:
            apps[app] = {
                "status": "blocked_missing_current_transcribed_odds",
                "budget": 100.0,
                "cash_reserved": 100.0,
                "current_fixture_count": 0,
                "profiles": {},
                "required_user_input": {
                    "en": (
                        f"Current {app} screenshots or manually entered decimal "
                        "prices for every upcoming fixture."
                    ),
                    "es": (
                        f"Capturas actuales de {app} o cuotas decimales "
                        "ingresadas manualmente para cada partido próximo."
                    ),
                },
            }
            continue
        profiles: Dict[str, object] = {}
        for profile in RISK_AVERSION_PROFILES:
            profile_id = str(profile["id"])
            stakes = allocate_educational_simulation(app_rows, profile_id)
            singles_deployed = round(sum(stakes.values()), 2)
            accumulator_stake = round(
                100.0 * SIMULATION_PROFILE_POLICY[profile_id][
                    "accumulator_fraction"
                ],
                2,
            )
            accumulator_candidates = sorted(
                current_rows,
                key=lambda row: (
                    float(row["rank_one_comparison"]["recommendation_utility"]),
                    float(row["rank_one_comparison"]["stressed_ev_pct"]),
                    row["fixture_id"],
                ),
                reverse=True,
            )[:3]
            accumulator_legs = [
                {
                    "fixture_id": row["fixture_id"],
                    "fixture": row["fixture"],
                    "selection": row["rank_one_comparison"]["display"],
                    "odds": float(row["rank_one_comparison"]["odds"]),
                    "source_image": row["rank_one_comparison"]["source_image"],
                }
                for row in accumulator_candidates
            ]
            accumulator_odds = (
                math.prod(leg["odds"] for leg in accumulator_legs)
                if accumulator_legs else 0.0
            )
            for row in predictions:
                rec = row["rank_one_comparison"]
                stake = stakes.get(row["fixture_id"], 0.0)
                forced_reasons = []
                if stake > 0.0:
                    if rec["strength"] == "HALT":
                        forced_reasons.append("halt_candidate")
                    if float(rec["ev_pct"]) <= 0.0:
                        forced_reasons.append("non_positive_ev")
                    if float(rec["stressed_ev_pct"]) < 0.0:
                        forced_reasons.append("negative_stressed_ev")
                    if rec["price_gate_status"] != "at_or_above_model_fair_price":
                        forced_reasons.append("below_model_fair_price")
                    if rec["risk_lens"][profile_id]["status"] != "PASS":
                        forced_reasons.append("fails_selected_risk_lens")
                rec.setdefault("stake_simulation", {}).setdefault(
                    app, {}
                )[profile_id] = {
                    "stake": stake,
                    "share_of_app_budget_pct": round(stake, 1),
                    "gross_return_if_full_win": round(
                        stake * float(rec["odds"]), 2
                    ),
                    "coverage_policy": (
                        "forced_one_single_per_current_match"
                        if forced_reasons else "passes_simulation_filters"
                    ),
                    "forced_coverage_reasons": forced_reasons,
                }
            profiles[profile_id] = {
                "label": {
                    "en": profile["label_en"],
                    "es": profile["label_es"],
                },
                "budget": 100.0,
                "singles_deployed": singles_deployed,
                "accumulator_stake": accumulator_stake,
                "cash_reserved": round(
                    100.0 - singles_deployed - accumulator_stake, 2
                ),
                "single_fixture_count": len(current_rows),
                "max_single_pct": (
                    SIMULATION_PROFILE_POLICY[profile_id][
                        "max_single_fraction"
                    ] * 100.0
                ),
                "accumulator": {
                    "leg_count": len(accumulator_legs),
                    "legs": accumulator_legs,
                    "combined_decimal_odds": round(accumulator_odds, 3),
                    "gross_return_if_full_win": round(
                        accumulator_stake * accumulator_odds, 2
                    ),
                    "warning": (
                        "All legs must win; correlated uncertainty and stale "
                        "prices make this materially riskier than singles."
                    ),
                },
            }
        apps[app] = {
            "status": "available_from_transcribed_screenshot_odds",
            "budget": 100.0,
            "current_fixture_count": len(current_rows),
            "profiles": profiles,
        }
    return {
        "currency": "PEN",
        "budget_per_app": 100.0,
        "default_profile": "balanced",
        "policy": "educational_hypothetical_not_authorized",
        "apps": apps,
        "warning": {
            "en": (
                "Hypothetical budgeting aid only. It is not an authorized "
                "stake, profit forecast, or instruction to bet. Change the "
                "budget to scale amounts; re-check live odds and team news."
            ),
            "es": (
                "Solo ayuda hipotética de presupuesto. No es monto autorizado, "
                "pronóstico de beneficio ni instrucción para apostar. Cambia "
                "el presupuesto para escalar montos y revisa cuotas y noticias."
            ),
        },
    }


def complementary_bet_analysis(
    grouped_1x2: Dict[str, Dict[str, Dict[str, str]]],
    team_a_names: Tuple[str, str],
    team_b_names: Tuple[str, str],
    budget: float = 10.0,
) -> Dict[str, object]:
    """Analyze dutching and two-outcome hedge math from sourced 1X2 odds.

    A guaranteed same-match profit requires complete mutually exclusive and
    collectively exhaustive outcomes and ``sum(1 / decimal_odds) < 1``. The
    common "small longshot + larger favorite" idea is only a hedge when one
    outcome is intentionally left uncovered; it can still lose the full two-leg
    stake if the uncovered outcome lands. This function therefore separates
    full-cover arbitrage from uncovered two-outcome hedge candidates.

    Example
    -------
    >>> odds = {"A": 2.20, "D": 3.40, "B": 3.80}
    >>> inv_sum = sum(1.0 / value for value in odds.values())
    >>> inv_sum < 1.0
    True
    """
    labels = {
        "A": {"en": f"{team_a_names[0]} win", "es": f"Gana {team_a_names[1]}"},
        "D": {"en": "Draw", "es": "Empate"},
        "B": {"en": f"{team_b_names[0]} win", "es": f"Gana {team_b_names[1]}"},
    }
    app_analyses = []
    for app, selections in sorted(grouped_1x2.items()):
        if set(selections) != {"A", "D", "B"}:
            continue
        prices = {
            outcome: float(selections[outcome]["odds"])
            for outcome in ("A", "D", "B")
        }
        inverse_sum = sum(1.0 / price for price in prices.values())
        full_cover_stakes = {
            outcome: round(budget * (1.0 / prices[outcome]) / inverse_sum, 2)
            for outcome in ("A", "D", "B")
        }
        full_cover_gross = round(budget / inverse_sum, 2)
        full_cover_profit = round(full_cover_gross - budget, 2)
        full_cover_status = (
            "mathematical_arbitrage_available"
            if inverse_sum < 1.0 else "no_full_cover_arbitrage"
        )
        pair_candidates = []
        for covered in (("A", "B"), ("A", "D"), ("D", "B")):
            uncovered = next(
                outcome for outcome in ("A", "D", "B")
                if outcome not in covered
            )
            pair_inverse_sum = sum(1.0 / prices[outcome] for outcome in covered)
            pair_stakes = {
                outcome: round(
                    budget * (1.0 / prices[outcome]) / pair_inverse_sum, 2
                )
                for outcome in covered
            }
            pair_gross = round(budget / pair_inverse_sum, 2)
            pair_profit = round(pair_gross - budget, 2)
            pair_candidates.append({
                "covered_outcomes": list(covered),
                "covered_labels": {
                    outcome: labels[outcome] for outcome in covered
                },
                "uncovered_outcome": uncovered,
                "uncovered_label": labels[uncovered],
                "stakes": pair_stakes,
                "gross_return_if_covered_outcome": pair_gross,
                "profit_if_covered_outcome": pair_profit,
                "loss_if_uncovered_outcome": round(-budget, 2),
                "inverse_sum": round(pair_inverse_sum, 6),
                "status": "two_outcome_hedge_not_guaranteed",
            })
        pair_candidates.sort(
            key=lambda row: (
                row["profit_if_covered_outcome"],
                -row["inverse_sum"],
                row["uncovered_outcome"],
            ),
            reverse=True,
        )
        app_analyses.append({
            "app": app,
            "budget": budget,
            "odds": prices,
            "labels": labels,
            "source_images": {
                outcome: selections[outcome]["source_image"]
                for outcome in ("A", "D", "B")
            },
            "inverse_odds_sum": round(inverse_sum, 6),
            "bookmaker_margin_pct": round((inverse_sum - 1.0) * 100.0, 2),
            "full_cover": {
                "status": full_cover_status,
                "stakes": full_cover_stakes,
                "gross_return_any_outcome": full_cover_gross,
                "profit_any_outcome": full_cover_profit,
                "guaranteed_profit": inverse_sum < 1.0,
            },
            "best_two_outcome_hedge": pair_candidates[0],
            "two_outcome_candidates": pair_candidates,
        })
    best_full_cover = [
        row for row in app_analyses
        if row["full_cover"]["guaranteed_profit"]
    ]
    best_full_cover.sort(
        key=lambda row: row["full_cover"]["profit_any_outcome"],
        reverse=True,
    )
    best_two_outcome = sorted(
        app_analyses,
        key=lambda row: row["best_two_outcome_hedge"][
            "profit_if_covered_outcome"
        ],
        reverse=True,
    )
    return {
        "currency": "PEN",
        "budget": budget,
        "scope": "same_app_complete_1x2_screenshot_prices",
        "status": (
            "full_cover_arbitrage_available"
            if best_full_cover else "no_full_cover_arbitrage"
        ),
        "full_cover_arbitrage_available": bool(best_full_cover),
        "best_full_cover": best_full_cover[0] if best_full_cover else None,
        "best_two_outcome_hedge": (
            best_two_outcome[0] if best_two_outcome else None
        ),
        "apps": app_analyses,
        "warning": {
            "en": (
                "A true guaranteed arbitrage requires all mutually exclusive "
                "outcomes to be covered and the inverse-odds sum to be below 1. "
                "Two-outcome hedges can still lose the full stake on the "
                "uncovered outcome."
            ),
            "es": (
                "Un arbitraje garantizado real requiere cubrir todos los "
                "resultados mutuamente excluyentes y que la suma de inversas de "
                "cuotas sea menor que 1. Las coberturas de dos resultados aún "
                "pueden perder todo el monto si cae el resultado no cubierto."
            ),
        },
    }

def _legacy_attach_educational_stake_simulation_disabled(
    predictions: Sequence[Dict[str, object]],
) -> Dict[str, object]:
    """Attach five safety-filtered hypothetical S/100 portfolios."""
    profiles: Dict[str, object] = {}
    for profile in RISK_AVERSION_PROFILES:
        profile_id = str(profile["id"])
        stakes = allocate_educational_simulation(predictions, profile_id)
        deployed = round(sum(stakes.values()), 2)
        for row in predictions:
            rec = row["rank_one_comparison"]
            stake = stakes[row["fixture_id"]]
            exclusion_reasons = []
            if (
                row["fixture_lifecycle_status"] != "future"
                or row["freshness_status"] != "current_snapshot"
            ):
                exclusion_reasons.append("not_current_future_fixture")
            elif profile_id == "audit_only":
                exclusion_reasons.append("audit_only_profile_reserves_all_cash")
            else:
                if rec["strength"] == "HALT":
                    exclusion_reasons.append("halt_candidate")
                if float(rec["ev_pct"]) <= 0.0:
                    exclusion_reasons.append("non_positive_ev")
                if float(rec["stressed_ev_pct"]) < 0.0:
                    exclusion_reasons.append("negative_stressed_ev")
                if rec["price_gate_status"] != "at_or_above_model_fair_price":
                    exclusion_reasons.append("below_model_fair_price")
                if rec["risk_lens"][profile_id]["status"] != "PASS":
                    exclusion_reasons.append("fails_selected_risk_lens")
            rec.setdefault("stake_simulation", {})[profile_id] = {
                "stake": stake,
                "share_of_budget_pct": round(stake, 1),
                "gross_return_if_full_win": round(
                    stake * float(rec["odds"]), 2
                ),
                "profit_if_full_win": round(
                    stake * (float(rec["odds"]) - 1.0), 2
                ),
                "eligible_current_fixture": stake > 0.0,
                "exclusion_reasons": exclusion_reasons,
            }
        profiles[profile_id] = {
            "label": {
                "en": profile["label_en"],
                "es": profile["label_es"],
            },
            "budget": 100.0,
            "deployed": deployed,
            "cash_reserved": round(100.0 - deployed, 2),
            "fixture_count": sum(value > 0.0 for value in stakes.values()),
            "deployment_is_maximum_not_target": True,
        }
    return {
        "currency": "PEN",
        "base_budget": 100.0,
        "default_profile": "balanced",
        "policy": "educational_hypothetical_not_authorized",
        "profiles": profiles,
        "warning": {
            "en": (
                "Hypothetical budgeting aid only. It is not an authorized "
                "stake, profit forecast, or instruction to bet. Change the "
                "budget to scale amounts; re-check live odds and team news."
            ),
            "es": (
                "Solo ayuda hipotética de presupuesto. No es monto autorizado, "
                "pronóstico de beneficio ni instrucción para apostar. Cambia "
                "el presupuesto para escalar montos y revisa cuotas y noticias."
            ),
        },
    }


def recommendation_display_labels(
    fixture: Mapping[str, object],
    recommendation: Mapping[str, object],
) -> Dict[str, Dict[str, str]]:
    """Return localized market and selection labels without duplicating lines."""
    family = str(recommendation["market_family"])
    market_names = {
        "1x2": ("Match Result", "Resultado del partido"),
        "total_goals": ("Total Goals", "Total de goles"),
        "btts": ("Both Teams to Score", "Ambos equipos marcan"),
        "double_chance": ("Double Chance", "Doble oportunidad"),
        "asian_handicap": ("Asian Handicap", "Hándicap asiático"),
        "handicap_total_combo": (
            "Handicap + Total Goals", "Hándicap + Total de goles"
        ),
    }
    market_en, market_es = market_names.get(
        family, (str(recommendation["market_original"]),
                 str(recommendation["market_original"]))
    )
    selection = str(recommendation["selection_original"])
    canonical = str(recommendation.get("selection_canonical") or "")
    line = str(recommendation.get("line") or "").strip()
    selection_with_line = (
        selection
        if not line or line.lower() in selection.lower()
        else f"{selection} {line}".strip()
    )
    fixture_en = fixture["fixture"]["en"]
    fixture_es = fixture["fixture"]["es"]
    team_a_en, team_b_en = fixture_en.split(" vs ", 1)
    team_a_es, team_b_es = fixture_es.split(" vs ", 1)
    selection_en = {
        "A": team_a_en,
        "D": "Draw",
        "B": team_b_en,
        "yes": "Yes",
        "no": "No",
        "over": f"Over {line}".strip(),
        "under": f"Under {line}".strip(),
        "home": team_a_en,
        "away": team_b_en,
    }.get(canonical, selection_with_line)
    selection_es = {
        "A": team_a_es,
        "D": "Empate",
        "B": team_b_es,
        "yes": "Sí",
        "no": "No",
        "over": f"Más de {line}".strip(),
        "under": f"Menos de {line}".strip(),
        "home": team_a_es,
        "away": team_b_es,
    }.get(canonical, selection_with_line)
    return {
        "market": {"en": market_en, "es": market_es},
        "selection": {"en": selection_en, "es": selection_es},
    }


def app_navigation_steps(
    app: str, fixture: Mapping[str, object], recommendation: Mapping[str, object],
    stake: Optional[float],
) -> Dict[str, List[str]]:
    """Return bilingual novice steps for locating one exact sourced market."""
    display = recommendation_display_labels(fixture, recommendation)
    market_en = display["market"]["en"]
    market_es = display["market"]["es"]
    selection_en = display["selection"]["en"]
    selection_es = display["selection"]["es"]
    fixture_en = fixture["fixture"]["en"]
    fixture_es = fixture["fixture"]["es"]
    fair = float(recommendation["fair_odds"])
    source_price = float(recommendation["odds"])
    final_en = (
        f"Enter S/{stake:.2f} only for this budget simulation, review the bet "
        "slip, and confirm the selection, line, 90-minute settlement, and "
        "possible gross return before any real action."
        if stake is not None else
        "Treat this as an alternative, not an extra forced bet. Recheck the "
        "selection, line, 90-minute settlement, and current price before "
        "deciding whether it should replace rank one."
    )
    final_es = (
        f"Ingresa S/{stake:.2f} solo para esta simulación de presupuesto, "
        "revisa el cupón y confirma selección, línea, liquidación a 90 minutos "
        "y retorno bruto posible antes de cualquier acción real."
        if stake is not None else
        "Trátala como alternativa, no como apuesta adicional forzada. Revisa "
        "selección, línea, liquidación a 90 minutos y cuota actual antes de "
        "decidir si debe reemplazar al rango uno."
    )
    return {
        "en": [
            f"Open {app}, then Sports → Football → World Cup.",
            f"Search for {fixture_en} and confirm the kickoff date shown on this card.",
            f"Open the market named “{market_en}”.",
            f"Choose exactly “{selection_en}”. Do not substitute a nearby handicap or total line.",
            f"Check the current decimal price. The saved screenshot price is {source_price:.2f}; the model fair-price threshold is {fair:.2f}.",
            final_en,
        ],
        "es": [
            f"Abre {app} y entra a Deportes → Fútbol → Mundial.",
            f"Busca {fixture_es} y confirma la fecha de inicio mostrada en esta tarjeta.",
            f"Abre el mercado llamado “{market_es}”.",
            f"Elige exactamente “{selection_es}”. No sustituyas por una línea de hándicap o total parecida.",
            f"Revisa la cuota decimal actual. La cuota guardada en la captura es {source_price:.2f}; el umbral de cuota justa del modelo es {fair:.2f}.",
            final_es,
        ],
    }


def attach_bankroll_simulation(
    predictions: Sequence[Dict[str, object]],
) -> Dict[str, object]:
    """Attach a S/100 educational plan to each app's sourced recommendations."""
    summary = {
        "currency": "PEN",
        "budget_per_app": 100.0,
        "policy": "fail_closed_actionable_only_simulation",
        "warning": {
            "en": "No stake is allocated unless every actionability gate passes. Historical profitability is not validated, so this release allocates zero.",
            "es": "No se asigna monto salvo que todas las puertas de acción pasen. La rentabilidad histórica no está validada, por lo que esta versión asigna cero.",
        },
        "apps": {},
    }
    for app in ("Betano", "Betsson"):
        app_rows = [
            row for row in predictions
            if row["rank_one_comparison"]["app"] == app
        ]
        stakes = allocate_app_budget(app_rows)
        expected_net = gross_if_all_win = 0.0
        for row in app_rows:
            rec = row["rank_one_comparison"]
            stake = stakes[row["fixture_id"]]
            gross_return = stake * float(rec["odds"])
            expected_net += stake * float(rec["ev_pct"]) / 100.0
            gross_if_all_win += gross_return
            rec["budget_simulation"] = {
                "app_budget": 100.0,
                "stake": stake,
                "share_of_app_budget_pct": round(stake, 1),
                "screenshot_odds": float(rec["odds"]),
                "minimum_model_fair_odds": float(rec["fair_odds"]),
                "price_gate_status": (
                    "at_or_above_model_fair_price"
                    if float(rec["odds"]) >= float(rec["fair_odds"])
                    else "below_model_fair_price_forced_coverage_only"
                ),
                "gross_return_if_full_win": round(gross_return, 2),
                "profit_if_full_win": round(gross_return - stake, 2),
                "steps": (
                    app_navigation_steps(app, row, rec, stake)
                    if rec["decision_status"] == "ACTIONABLE"
                    else {"en": [], "es": []}
                ),
                "warning": summary["warning"],
            }
        summary["apps"][app] = {
            "fixture_count": len(app_rows),
            "total_stake": round(sum(stakes.values()), 2),
            "unallocated_budget": round(
                100.0 - sum(stakes.values()), 2
            ),
            "model_estimated_net": round(expected_net, 2),
            "gross_return_if_every_pick_fully_wins": round(
                gross_if_all_win, 2
            ),
            "risk_note": {
                "en": "Gross return assumes every selection fully wins; Asian pushes or half-results can reduce it. The model-estimated net is not historically validated.",
                "es": "El retorno bruto supone que todas las selecciones ganan completamente; nulos o medias liquidaciones asiáticas pueden reducirlo. El neto estimado no está validado históricamente.",
            },
        }
    return summary


def build() -> Dict[str, object]:
    fixtures = read_csv(FIXTURES)
    if not fixtures or len({row["fixture_id"] for row in fixtures}) != len(fixtures):
        raise ValueError("Canonical fixture file must contain unique fixtures")

    historical = load_historical()
    dataset_a = [row for row in historical if row.competition in {"WC_2018_GROUP", "WC_2022_GROUP", "WC_2026_GROUP"}]
    dataset_b = [row for row in historical if row.competition not in {"WC_2018_GROUP", "WC_2022_GROUP", "WC_2026_GROUP"}]
    fields_hist = (
        "date", "competition", "weight", "team_a", "team_b", "elo_a", "elo_b",
        "outcome", "score_a", "score_b", "odds_a", "odds_d", "odds_b",
    )
    write_csv(DATASET_A_OUT, [row.__dict__ for row in dataset_a], fields_hist)
    write_csv(DATASET_B_OUT, [row.__dict__ for row in dataset_b], fields_hist)

    best = calibrate_elo(historical)
    mu_a = sum((row.score_a + row.score_b) * row.weight for row in dataset_a) / sum(row.weight for row in dataset_a)
    mu_b = sum((row.score_a + row.score_b) * row.weight for row in dataset_b) / sum(row.weight for row in dataset_b)
    score_config = calibrate_score_model(historical)
    mu_total = float(score_config["mu_total"])

    baseline_rows = read_csv(ELO_BASELINE)
    baseline = {row["team"]: float(row["elo"]) for row in baseline_rows}
    results = read_csv(RESULTS_2026)
    result_by_key = {
        (row["date"], row["team_a"], row["team_b"]): row
        for row in results
    }
    verified_result_keys = {
        (row["date"], row["team_a"], row["team_b"])
        for row in results
    }
    (
        ratings, form, last_dates, pre_match_ratings, pre_match_context,
    ) = current_team_state(
        results, baseline
    )
    odds = load_and_merge_odds(fixtures)
    research = load_research(fixtures)
    research_fields = (
        "fixture_id", "team_news_summary", "injuries_suspensions",
        "predicted_lineup_notes", "motivation_group_state", "weather_venue_notes",
        "source_urls", "accessed_at", "confidence",
    )
    write_csv(RESEARCH_OUT, [research[key] for key in sorted(research)], research_fields)
    odds_fields = list(odds[0].keys())
    write_csv(ODDS_OUT, odds, odds_fields)
    manifest = screenshot_manifest(odds)
    write_csv(
        SCREENSHOT_MANIFEST_OUT, manifest,
        ("source_image", "source_sha256", "fixture_id", "app",
         "transcribed_selection_rows", "inventory_status"),
    )
    odds_by_fixture: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for odd in odds:
        odds_by_fixture[odd["fixture_id"]].append(odd)

    model_rows = []
    predictions = []
    for fixture in fixtures:
        ta, tb = split_fixture(fixture["match"])
        kickoff = datetime.fromisoformat(fixture["kickoff_lima"])
        result_key = (kickoff.date().isoformat(), ta, tb)
        fixture_ratings = pre_match_ratings.get(
            result_key, (ratings[ta], ratings[tb])
        )
        fixture_context = pre_match_context.get(result_key)
        # Tournament form is published descriptively but not added again to Elo:
        # current results have already changed the updated rating.
        fa, fb = 0.0, 0.0
        host_a = host_b = 0.0
        p_base = three_way_elo(
            fixture_ratings[0], fixture_ratings[1], float(best["divisor"]),
            float(best["draw_base"]), float(best["draw_slope"]),
            fa + host_a, fb + host_b,
        )
        la, lb = expected_lambdas(
            fixture_ratings[0], fixture_ratings[1], mu_total,
            fa + host_a, fb + host_b,
            float(score_config["allocation"]), float(score_config["gap_scale"]),
            float(score_config["gap_intensity"]),
        )
        matrix = score_matrix(la, lb)
        shadow_matrix = dixon_coles_score_matrix(
            la, lb, float(score_config["shadow_rho"])
        )
        # Compute de-vigged comparison probabilities for complete source markets.
        market_consensus: Dict[Tuple[str, str], float] = {}
        market_overround: Dict[str, float] = {}
        grouped: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(dict)
        for odd in odds_by_fixture[fixture["fixture_id"]]:
            if odd["market_id"] != "match_result":
                continue
            bucket = selection_bucket(odd, ta, tb)
            if bucket:
                grouped[odd["app"]][bucket] = odd
        for app, selections in grouped.items():
            if set(selections) != {"A", "D", "B"}:
                continue
            inv = {key: 1.0 / float(value["odds"]) for key, value in selections.items()}
            total_inv = sum(inv.values())
            for key in ("A", "D", "B"):
                market_consensus[(app, key)] = inv[key] / total_inv
        source_groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for odd in odds_by_fixture[fixture["fixture_id"]]:
            if odd["is_complete_market"] == "true":
                source_groups[odd["market_group_id"]].append(odd)
        for group_id, selections in source_groups.items():
            inverse_sum = sum(1.0 / float(row["odds"]) for row in selections)
            market_overround[group_id] = inverse_sum - 1.0
            for row in selections:
                market_consensus[(group_id, row["selection_canonical"])] = (
                    (1.0 / float(row["odds"])) / inverse_sum
                )

        stress_matrices = []
        shadow_stress_matrices = []
        for mu_multiplier, allocation_shift in (
            (0.90, 0.0), (1.10, 0.0), (1.0, -0.05), (1.0, 0.05)
        ):
            stress_la, stress_lb = expected_lambdas(
                fixture_ratings[0], fixture_ratings[1],
                mu_total * mu_multiplier, 0.0, 0.0,
                max(0.20, float(score_config["allocation"]) + allocation_shift),
                float(score_config["gap_scale"]),
                float(score_config["gap_intensity"]),
            )
            stress_matrices.append(score_matrix(stress_la, stress_lb))
            shadow_stress_matrices.append(
                dixon_coles_score_matrix(
                    stress_la, stress_lb, float(score_config["shadow_rho"])
                )
            )

        expanded_rows = evaluate_sourced_markets(
            odds_by_fixture[fixture["fixture_id"]], ta, tb, p_base, matrix,
            stress_matrices, market_consensus, market_overround,
        )
        shadow_p_base = result_probabilities_from_matrix(shadow_matrix)
        shadow_expanded_rows = evaluate_sourced_markets(
            odds_by_fixture[fixture["fixture_id"]], ta, tb, shadow_p_base,
            shadow_matrix, shadow_stress_matrices, market_consensus,
            market_overround,
        )
        expanded_ranked = sorted(
            expanded_rows,
            key=lambda row: (
                row["market_family"], -row["ev_pct"],
                row["app"], row["selection_canonical"],
            ),
        )
        complete_apps = [
            app for app, selections in grouped.items()
            if set(selections) == {"A", "D", "B"}
        ]
        if not complete_apps:
            raise ValueError(
                f"Fixture lacks a complete supported 1X2 market: {fixture['fixture_id']}"
            )
        ranked_recommendations = rank_distinct_recommendations(
            expanded_rows, ta, tb
        )
        shadow_ranked_recommendations = rank_distinct_recommendations(
            shadow_expanded_rows, ta, tb
        )
        recommendation = (
            ranked_recommendations[0][0] if ranked_recommendations else None
        )
        recommendation_reason = (
            ranked_recommendations[0][1]
            if ranked_recommendations else "no_complete_sourced_market"
        )
        form_a = (
            fixture_context["form_a"] if fixture_context else form[ta]
        )
        form_b = (
            fixture_context["form_b"] if fixture_context else form[tb]
        )
        last_a = (
            fixture_context["last_date_a"]
            if fixture_context else last_dates.get(ta)
        )
        last_b = (
            fixture_context["last_date_b"]
            if fixture_context else last_dates.get(tb)
        )
        rest_a = (kickoff.date() - last_a).days if last_a else None
        rest_b = (kickoff.date() - last_b).days if last_b else None
        model_row = {
            "fixture_id": fixture["fixture_id"], "kickoff_lima": fixture["kickoff_lima"],
            "kickoff_utc": fixture["kickoff_utc"], "team_a": ta, "team_b": tb,
            "elo_a_baseline": baseline[ta], "elo_b_baseline": baseline[tb],
            "elo_a_updated": round(fixture_ratings[0], 3),
            "elo_b_updated": round(fixture_ratings[1], 3),
            "form_games_a": int(form_a["games"]),
            "form_games_b": int(form_b["games"]),
            "form_points_a": int(form_a["points"]),
            "form_points_b": int(form_b["points"]),
            "form_gd_a": int(form_a["gf"] - form_a["ga"]),
            "form_gd_b": int(form_b["gf"] - form_b["ga"]),
            "form_adjust_a": round(fa, 3), "form_adjust_b": round(fb, 3),
            "host_adjust_a": host_a, "host_adjust_b": host_b,
            "rest_days_a": rest_a, "rest_days_b": rest_b,
            "mu_total": round(mu_total, 5), "lambda_a": round(la, 5), "lambda_b": round(lb, 5),
            "p_win_a": round(p_base[0], 8), "p_draw": round(p_base[1], 8),
            "p_win_b": round(p_base[2], 8),
            "source_elo": "wc_team_elo_baseline_june11.csv + deterministic Elo updates from wc_2026_results_through_june26.csv",
            "source_form": "wc_2026_results_through_june26.csv",
            "source_schedule": fixture["schedule_source"],
            "research_confidence": research[fixture["fixture_id"]]["confidence"],
            "research_sources": research[fixture["fixture_id"]]["source_urls"],
            "research_team_news": research[fixture["fixture_id"]]["team_news_summary"],
            "research_injuries": research[fixture["fixture_id"]]["injuries_suspensions"],
            "research_motivation": research[fixture["fixture_id"]]["motivation_group_state"],
            "research_weather": research[fixture["fixture_id"]]["weather_venue_notes"],
            "freshness_status": freshness_status(kickoff),
        }
        model_rows.append(model_row)
        names_a, names_b = CODE_NAMES[ta], CODE_NAMES[tb]
        complementary_analysis = complementary_bet_analysis(
            grouped, names_a, names_b
        )
        published_lambda_a = round(la, 3)
        published_lambda_b = round(lb, 3)
        common_markets = common_market_probabilities(matrix)
        research_mode = research_mode_payload(matrix, shadow_matrix, score_config)
        explanations = metric_explanations(
            names_a, names_b, p_base, published_lambda_a,
            published_lambda_b, common_markets
        )
        public_ranked_recommendations = [
            public_recommendation(row, rank, reason)
            for rank, (row, reason) in enumerate(
                ranked_recommendations, start=1
            )
        ]
        public_research_ranked_recommendations = [
            public_recommendation(row, rank, reason)
            for rank, (row, reason) in enumerate(
                shadow_ranked_recommendations, start=1
            )
        ]
        fixture_names = {
            "fixture": {
                "en": f"{names_a[0]} vs {names_b[0]}",
                "es": f"{names_a[1]} vs {names_b[1]}",
            }
        }
        attach_recommendation_context(
            public_ranked_recommendations, fixture_names, "production"
        )
        attach_recommendation_context(
            public_research_ranked_recommendations, fixture_names, "research"
        )
        fixture_freshness = freshness_status(kickoff)
        lifecycle_status = (
            "elapsed_result_verified"
            if result_key in verified_result_keys
            else "elapsed_requires_verified_result"
            if kickoff <= RELEASE_AS_OF
            else "future"
        )
        verified_result = result_by_key.get(result_key)
        authorize_recommendations(
            public_ranked_recommendations,
            fixture_freshness,
            lifecycle_status,
        )
        authorize_recommendations(
            public_research_ranked_recommendations,
            fixture_freshness,
            lifecycle_status,
        )
        production_risk_summary = risk_profile_summary(
            public_ranked_recommendations
        )
        research_risk_summary = risk_profile_summary(
            public_research_ranked_recommendations
        )
        research_mode["ranked_comparisons"] = (
            public_research_ranked_recommendations
        )
        research_mode["top_recommendations"] = []
        research_mode["ranked_comparisons_requested"] = 4
        research_mode["ranked_comparisons_available"] = len(
            public_research_ranked_recommendations
        )
        research_mode["ranked_comparisons_shortfall_reason"] = (
            ""
            if len(public_research_ranked_recommendations) == 4
            else "fewer_than_four_distinct_complete_sourced_events"
        )
        research_mode["top_recommendations_requested"] = 0
        research_mode["top_recommendations_available"] = 0
        research_mode["top_recommendations_shortfall_reason"] = (
            "release_blocked_all_rows_abstain"
        )
        research_mode["recommendation_scope"] = (
            "research-mode non-actionable comparisons are ranked with the "
            "gated shadow score model against the same sourced screenshot odds; "
            "they do not authorize a bet or validate profitability"
        )
        research_mode["risk_profile_summary"] = research_risk_summary
        production_rank_one_key = (
            public_ranked_recommendations[0]["market_family"],
            public_ranked_recommendations[0]["selection_canonical"],
            public_ranked_recommendations[0]["line"],
        )
        research_rank_one_key = (
            public_research_ranked_recommendations[0]["market_family"],
            public_research_ranked_recommendations[0]["selection_canonical"],
            public_research_ranked_recommendations[0]["line"],
        )
        shadow_by_candidate = {
            sourced_candidate_key(row): row for row in shadow_expanded_rows
        }
        paired_halt_reviews = []
        for production_row in expanded_rows:
            research_row = shadow_by_candidate.get(
                sourced_candidate_key(production_row)
            )
            if (
                research_row is not None
                and production_row["strength"] == "HALT"
                and research_row["strength"] == "PASS"
            ):
                paired_halt_reviews.append({
                    "app": production_row["app"],
                    "market_family": production_row["market_family"],
                    "market_original": production_row["market_original"],
                    "selection_original": production_row["selection_original"],
                    "line": production_row["line"],
                    "odds": float(production_row["odds"]),
                    "source_image": production_row["source_image"],
                    "production_divergence_pp": round(
                        float(production_row["divergence_pp"]), 2
                    ),
                    "research_divergence_pp": round(
                        float(research_row["divergence_pp"]), 2
                    ),
                    "production_raw_ev_pct": round(
                        float(production_row["ev_pct"]), 2
                    ),
                    "research_raw_ev_pct": round(
                        float(research_row["ev_pct"]), 2
                    ),
                })
        halt_improvement_loop = {
            "paired_candidates_compared": len(expanded_rows),
            "production_anomaly_halt_count": sum(
                row["strength"] == "HALT" for row in expanded_rows
            ),
            "research_anomaly_halt_count": sum(
                row["strength"] == "HALT" for row in shadow_expanded_rows
            ),
            "paired_production_halt_to_research_pass_count": len(
                paired_halt_reviews
            ),
            "paired_review_candidates": paired_halt_reviews,
            "research_rank_one_changed": (
                production_rank_one_key != research_rank_one_key
            ),
            "automatic_resolution_allowed": False,
            "status": (
                "paired_shadow_review_candidates_present"
                if paired_halt_reviews else
                "no_paired_shadow_reclassification"
            ),
            "required_checks": {
                "en": [
                    "Verify current app price and settlement line.",
                    "Verify lineup, injury, motivation, and weather freshness.",
                    "Compare production and research score distributions.",
                    "Require chronological out-of-sample evidence before changing production thresholds.",
                ],
                "es": [
                    "Verifica cuota actual y línea de liquidación.",
                    "Verifica vigencia de alineación, lesiones, motivación y clima.",
                    "Compara distribuciones de marcador de producción e investigación.",
                    "Exige evidencia cronológica fuera de muestra antes de cambiar umbrales de producción.",
                ],
            },
        }
        rec = (
            public_ranked_recommendations[0]
            if public_ranked_recommendations else None
        )
        market_comparisons = [{
            "app": row["app"],
            "market_family": row["market_family"],
            "market_original": row["market_original"],
            "selection_original": row["selection_original"],
            "selection_canonical": row["selection_canonical"],
            "selected_team": row["selected_team"],
            "handicap_line": (
                float(row["handicap_selected_line"])
                if row["handicap_selected_line"] else None
            ),
            "total_line": float(row["total_line"]) if row["total_line"] else None,
            "odds": float(row["odds"]),
            "p_win": round(row["p_win"], 6),
            "p_push": round(row["p_push"], 6),
            "fair_odds": round(
                fair_decimal(row["p_win"], row["p_push"]) or 0.0, 3
            ),
            "ev_pct": round(row["ev_pct"], 2),
            "stressed_ev_pct": round(row["stressed_ev_pct"], 2),
            "decision_probability": round(row["decision_probability"], 6),
            "decision_ev_pct": round(row["decision_ev_pct"], 2),
            "decision_stressed_ev_pct": round(
                row["decision_stressed_ev_pct"], 2
            ),
            "decision_model_weight": round(row["decision_model_weight"], 6),
            "decision_probability_method": row[
                "decision_probability_method"
            ],
            "market_probability": round(row["market_probability"], 6),
            "recommendation_utility": round(
                row["recommendation_utility"], 2
            ),
            "divergence_pp": round(row["divergence_pp"], 2),
            "market_overround_pct": round(row["market_overround_pct"], 2),
            "strength": row["strength"],
            "policy_status": row["policy_status"],
            "source_image": row["source_image"],
            "source_sha256": row["source_sha256"],
        } for row in expanded_ranked]
        predictions.append({
            "fixture_id": fixture["fixture_id"],
            "kickoff_lima": fixture["kickoff_lima"],
            "kickoff_utc": fixture["kickoff_utc"],
            "fixture": {"en": f"{names_a[0]} vs {names_b[0]}", "es": f"{names_a[1]} vs {names_b[1]}"},
            "group": fixture["group"], "venue": fixture["venue"],
            "probabilities": {
                "team_a_win": round(p_base[0], 6), "draw": round(p_base[1], 6),
                "team_b_win": round(p_base[2], 6),
            },
            "expected_goals": {
                "team_a": published_lambda_a,
                "team_b": published_lambda_b,
            },
            "score_market_model": {
                "production": "tuned_elo_independent_poisson",
                "shadow": "dixon_coles",
                "shadow_rho": score_config["shadow_rho"],
                "shadow_btts_yes_probability": round(
                    event_probability(
                        shadow_matrix, lambda ga, gb: ga > 0 and gb > 0
                    ),
                    6,
                ),
                "policy_status": "experimental_non_actionable",
            },
            "research_mode": research_mode,
            "common_markets": common_markets,
            "metric_explanations": explanations,
            "market_comparisons": market_comparisons,
            "complementary_bet_analysis": complementary_analysis,
            "expanded_price_coverage": {
                "has_total_price": any(
                    row["market_family"] == "total_goals"
                    for row in expanded_ranked
                ),
                "has_btts_price": any(
                    row["market_family"] == "btts" for row in expanded_ranked
                ),
                "has_asian_handicap_price": any(
                    row["market_family"] == "asian_handicap"
                    for row in expanded_ranked
                ),
                "has_combo_price": any(
                    row["market_family"] == "handicap_total_combo"
                    for row in expanded_ranked
                ),
            },
            "recommendation": (
                rec if rec and rec["decision_status"] == "ACTIONABLE" else None
            ),
            "rank_one_comparison": rec,
            "fixture_lifecycle_status": lifecycle_status,
            "verified_result": (
                {
                    "score_a": int(verified_result["score_a"]),
                    "score_b": int(verified_result["score_b"]),
                    "score": (
                        f"{verified_result['score_a']}-"
                        f"{verified_result['score_b']}"
                    ),
                    "source_url": verified_result["source_result"],
                    "accessed_at": verified_result["accessed_at"],
                }
                if verified_result else None
            ),
            "ranked_comparisons": public_ranked_recommendations,
            "top_recommendations": [],
            "risk_profile_summary": production_risk_summary,
            "halt_improvement_loop": halt_improvement_loop,
            "risk_aversion_profiles": [
                {
                    "id": str(profile["id"]),
                    "label": {
                        "en": str(profile["label_en"]),
                        "es": str(profile["label_es"]),
                    },
                    "description": {
                        "en": str(profile["description_en"]),
                        "es": str(profile["description_es"]),
                    },
                    "max_divergence_pp": float(profile["max_divergence_pp"]),
                    "min_stressed_ev_pct": float(
                        profile["min_stressed_ev_pct"]
                    ),
                    "allowed_risk_grades": sorted(
                        profile["allowed_risk_grades"]
                    ),
                }
                for profile in RISK_AVERSION_PROFILES
            ],
            "ranked_comparisons_requested": 4,
            "ranked_comparisons_available": len(
                public_ranked_recommendations
            ),
            "ranked_comparisons_shortfall_reason": (
                ""
                if len(public_ranked_recommendations) == 4
                else "fewer_than_four_distinct_complete_sourced_events"
            ),
            "top_recommendations_requested": 0,
            "top_recommendations_available": 0,
            "top_recommendations_shortfall_reason": (
                "release_blocked_all_rows_abstain"
            ),
            "supported_markets_evaluated": len(expanded_rows),
            "recommendation_scope": "up to four distinct sourced non-actionable comparisons are ranked per fixture by stressed EV, disagreement, and family-validation penalties; recommendation remains null, rank_one_comparison is audit-only, and historical profitability is not validated",
            "freshness_status": fixture_freshness,
            "risk_notes": {
                "en": [
                    "Football outcomes remain high variance even when expected value is positive.",
                    "Late lineup, injury, tactical, weather, or motivation changes can invalidate the estimate.",
                    "Re-check the exact app price before any decision; moved odds change expected value.",
                ],
                "es": [
                    "Los resultados de fútbol siguen teniendo alta varianza aunque el valor esperado sea positivo.",
                    "Cambios tardíos de alineación, lesión, táctica, clima o motivación pueden invalidar la estimación.",
                    "Vuelve a revisar la cuota exacta en la app; un cambio de cuota cambia el valor esperado.",
                ],
            },
            "research": {
                "confidence": research[fixture["fixture_id"]]["confidence"],
                "team_news": research[fixture["fixture_id"]]["team_news_summary"],
                "injuries_suspensions": research[fixture["fixture_id"]]["injuries_suspensions"],
                "predicted_lineup_notes": research[fixture["fixture_id"]]["predicted_lineup_notes"],
                "motivation_group_state": research[fixture["fixture_id"]]["motivation_group_state"],
                "weather_venue_notes": research[fixture["fixture_id"]]["weather_venue_notes"],
                "source_urls": research[fixture["fixture_id"]]["source_urls"].split(" | "),
                "accessed_at": research[fixture["fixture_id"]]["accessed_at"],
            },
        })

    model_fields = list(model_rows[0].keys())
    write_csv(MODEL_DATA_OUT, model_rows, model_fields)
    bankroll_simulation = attach_bankroll_simulation(predictions)
    educational_stake_simulation = attach_educational_stake_simulation(
        predictions
    )
    manual_odds_sources = discover_manual_odds_files(ROOT)
    manual_odds_provenance = [
        manual_odds_provenance_path(path) for path in manual_odds_sources
    ]
    input_hashes = {
        path.name: sha256(path) for path in
        (
            HISTORICAL, RESULTS_2026, ELO_BASELINE, FIXTURES,
            *ODDS_PARTS, *manual_odds_sources, *manual_odds_provenance,
            *RESEARCH_PARTS,
        )
    }
    metrics = {
        "version": "june22_27_v5_fail_closed_development_only",
        "seed": SEED,
        "dataset_a_rows": len(dataset_a),
        "dataset_b_rows": len(dataset_b),
        "elapsed_wc2026_rows": len(results),
        "calibration": best,
        "score_market_calibration": score_config,
        "mu_dataset_a": mu_a,
        "mu_dataset_b": mu_b,
        "mu_production": mu_total,
        "expanded_market_policy": {
            "status": "abstain_no_validated_recommendation_policy",
            "reason": (
                "Historical profitability is unvalidated, the nominal holdout "
                "has been used for development feedback, source prices are "
                "stale, and conditional fixtures require intervening results."
            ),
            "priced_fixtures": len({
                row["fixture_id"] for row in odds
                if row["market_family"] in {
                    "total_goals", "btts", "asian_handicap",
                    "handicap_total_combo",
                }
                and row["is_complete_market"] == "true"
            }),
            "all_fixture_probability_coverage": len(fixtures),
            "recommendations_required": 0,
            "selection_rule": (
                "rank independent structural-model EV and stressed EV; use "
                "market-implied probability only as a disagreement/risk "
                "diagnostic, never as an input to the probability evaluating "
                "that same quote"
            ),
        },
        "research_mode_policy": {
            "toggle_available": True,
            "default_state": "off_production_mode",
            "selected_candidate": "dixon_coles_low_score_correction_shadow",
            "selected_family": "hierarchical_dynamic_poisson_score_research",
            "status": "research_gated_not_production",
            "production_recommendations_unchanged": True,
            "why_selected": (
                "Dixon-Coles is the selected tested shadow candidate because "
                "it is football-specific, low-parameter, and reproducible "
                "with the available score data. Other registered candidates "
                "have not all been fit and compared, so this is not a claim "
                "that Dixon-Coles is globally best. High-capacity temporal "
                "graph and sequence models remain blocked by the "
                "sample-size/edge-count promotion gate."
            ),
            "why_not_promoted": (
                "Shadow paired-bootstrap intervals cross zero and no "
                "timestamp-verified historical closing odds exist for "
                "profitability validation."
            ),
            "promotion_requirements": {
                "minimum_timestamped_fixtures": 2000,
                "minimum_temporal_edges_per_team": 30,
                "validation": (
                    "nested walk-forward selection, untouched holdout "
                    "superiority, calibration checks, multiple-testing "
                    "control, and closing-line ROI/CLV validation"
                ),
            },
        },
        "evaluation_governance": {
            "current_holdout_status": (
                "development_validation_only_not_confirmatory"
            ),
            "reason": (
                "The nominal holdout informed prior development decisions and "
                "cannot be described as untouched or confirmatory."
            ),
            "new_sealed_holdout_required": True,
            "probability_release_status": "development_only",
            "recommendation_release_status": "blocked",
            "bankroll_release_status": "prohibited_zero_allocation",
        },
        "input_hashes": input_hashes,
        "pipeline_sha256": sha256(Path(__file__)),
    }
    payload = {
        "schema_version": "2.0",
        "generated_at": RELEASE_AS_OF.isoformat(),
        "data_cutoff": DATA_CUTOFF.isoformat(),
        "release_as_of": RELEASE_AS_OF.isoformat(),
        "lifecycle_policy_version": "fail_closed_v1",
        "batch": {
            "start": "2026-06-27",
            "end": "2026-06-29",
            "fixture_count": len(fixtures),
            "active_fixture_file": FIXTURES.name,
            "odds_source": "manual_odds_20260627_20260629.csv",
        },
        "model": metrics,
        "bankroll_simulation": bankroll_simulation,
        "educational_stake_simulation": educational_stake_simulation,
        "predictions": predictions,
        "glossary": {
            "ev": {
                "en": "Expected value estimates average long-run return, not the outcome of one match.",
                "es": "El valor esperado estima el retorno promedio a largo plazo, no el resultado de un solo partido.",
            },
            "strength": {
                "en": "PASS means no actionable recommendation. HALT means the apparent edge requires investigation and must not be treated as a bet.",
                "es": "PASS significa que no hay recomendación accionable. HALT significa que la ventaja aparente requiere investigación y no debe tratarse como apuesta.",
            },
        },
    }
    PREDICTIONS_OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    METRICS_OUT.write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    generated_hashes = {
        path.name: sha256(path) for path in
        (DATASET_A_OUT, DATASET_B_OUT, MODEL_DATA_OUT, ODDS_OUT,
         SCREENSHOT_MANIFEST_OUT, RESEARCH_OUT, PREDICTIONS_OUT, METRICS_OUT)
    }
    PROVENANCE_OUT.write_text(
        "\n".join([
            "WCdecider June 27–29, 2026 provenance",
            "=======================================",
            "",
            "Canonical fixtures: wc_2026_matches_june_27-29.csv",
            "Elapsed outcomes: wc_2026_results_through_june26.csv with verified June 25–26 results retrieved by 2026-06-27T11:00:00-05:00",
            "Pre-tournament Elo: wc_team_elo_baseline_june11.csv",
            "Historical Dataset A/B source: wc_backtest_historical_dataset.csv",
            "Screenshot-derived odds: odds_june22_23.csv, odds_june24.csv, odds_june25_26.csv, odds_june27.csv",
            "Manual odds source: manual_odds_20260627_20260629.csv with matching .provenance.json sidecar is preferred for active fixtures after 2026-06-26 at the normalized row key fixture_id/app/market_id/selection_canonical/line.",
            "Complete screenshot inventory: wc_screenshot_manifest_june22_27.csv",
            "Verified sportsbook UI boundary: IMG_7523–IMG_7614 = Betsson; IMG_7615–IMG_7745 = Betano.",
            "OSINT notes: research_june22_23.csv, research_june24_25.csv, research_june26_27.csv",
            "Sanitized canonical OSINT output: wc_research_june22_27.csv (post-cutoff sources are excluded).",
            "",
            "Column derivations:",
            "- updated Elo: sequential neutral-site World Cup Elo update with K=60 and goal-margin multiplier.",
            "- goal-margin multiplier: 1.0 for one-goal/draw, 1.5 for two goals, (11+margin)/8 for three or more.",
            "- form features: elapsed cards use strictly pre-match tournament state; future cards use tournament state through the June 23 cutoff.",
            "- tournament form: descriptive only in production; no second adjustment after Elo updates.",
            "- probabilities: chronologically proper-score-tuned Elo three-way conversion; empirical calibration is not claimed without reliability diagnostics.",
            "- parameter grid: divisor {350,400,450,500}; draw_base {.14,.16,.18,.20,.22}; draw_slope {.06,.08,.10,.12}.",
            "- selection split: first 85% by date block and final 15% development-validation block. This set informed prior development and is not a sealed confirmatory holdout.",
            "- score-model parameter grid: base total goals {2.25,2.50,2.75,3.00}; allocation {.30,.35,.40}; Elo gap scale {350,420,500}; gap intensity {0,.15,.30,.45}.",
            "- expected goals: match total = base_mu + gap_intensity*abs(Elo gap)/400, bounded to [1.5,4.5], then split as .5 + allocation*tanh(Elo gap/gap_scale).",
            "- score grid: tuned independent Poisson scores 0..10, renormalized; Dixon-Coles rho {-0.15,-0.10,-0.05,0,.05,.10,.15} is evaluated as a shadow challenger only.",
            "- score-market outputs: totals 0.5–5.5, BTTS, double chance, total-goal buckets, top correct scores, and Asian handicaps are derived by exact score-grid summation.",
            "- Asian settlement: integer/half lines settle directly; quarter lines split the stake equally across adjacent half-lines and preserve win/push/loss equivalents.",
            "- handicap-plus-total combos: retained as source evidence but disabled from completeness, EV, rankings, and recommendations until app-specific push/void/half-result contracts are documented and exhaustively tested.",
            "- normalized odds schema: market family, period, settlement rule, selected team, canonical selection, handicap/total lines, combo legs, market group, completeness, transcription status, and confidence.",
            "- odds source_kind/source_file: screenshot rows point to the original odds_june*.csv extraction and manual_user_input rows point to the manual_odds_*.csv file entered through the GUI.",
            "- unsupported or ambiguous markets: result handicap, early payout, corners, heterogeneous boosts, and incomplete/truncated selections are retained as source rows but excluded from evaluation.",
            "- double-chance consistency: displayed fair prices and screenshot EV both use the same production score grid.",
            "- quote evaluation: structural forecast probabilities remain independent of the quoted price; de-vigged market probabilities are used only for disagreement/risk diagnostics.",
            "- recommendation utility: minimum(decision EV, stressed decision EV) minus 0.35*divergence, family uncertainty, and HALT penalties.",
            "- ranked comparisons: publish up to four score-state-distinct sourced events for audit only; no comparison becomes actionable in this release.",
            "- actionability policy: every row is ABSTAIN because historical profitability is unvalidated, prices are stale, conditional fixtures require intervening results, and the nominal holdout is development-only.",
            "- price coverage: all active fixtures receive model probabilities/fair prices; EV is computed only for complete current source markets that pass market-completeness validation.",
            "- recommendation field: null for ABSTAIN rows; rank_one_comparison preserves the non-actionable audit comparison separately.",
            "- metric_explanations: bilingual educational JSON generated from the published fixture values for 1/X/2, expected goals, totals, BTTS, and Asian handicap; these fields do not alter model probabilities.",
            "- bankroll simulation: only ACTIONABLE rows may receive a stake; every ABSTAIN row receives S/0 and unallocated app budget is preserved.",
            "- stress EV: subtract 3 percentage points from selected win probability and add 3 points to loss probability.",
            "- classification: divergence >15pp or EV >25% HALT; all other selections PASS until recommendation-policy profitability is validated out of sample.",
            "- source_sha256: screenshot rows use the SHA-256 of the exact screenshot containing the price; manual rows use the SHA-256 of the manual CSV artifact.",
            "",
            "Model selection:",
            "- Hyperparameters are selected on chronological development windows. The final development-validation block is descriptive only; a new prospective sealed holdout is required.",
            "- Dataset A contains World Cup rows; Dataset B contains qualifiers/friendlies.",
            "- No current price is hard-coded in Python and no reported target is extracted from prose.",
            "",
            "Input hashes:",
            *[f"- {name}: {value}" for name, value in sorted(input_hashes.items())],
            f"- pipeline: {metrics['pipeline_sha256']}",
            "",
            "Generated artifact hashes:",
            *[f"- {name}: {value}" for name, value in sorted(generated_hashes.items())],
        ]) + "\n",
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    built = build()
    recommendations = sum(1 for row in built["predictions"] if row["recommendation"])
    print(f"Built {len(built['predictions'])} predictions; {recommendations} recommendation records.")
    print(f"JSON: {PREDICTIONS_OUT}")
