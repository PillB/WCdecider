#!/usr/bin/env python3
"""Reproducible June 22–27, 2026 World Cup prediction pipeline.

This module is intentionally stdlib-only. It reads:

* ``wc_backtest_historical_dataset.csv`` — historical Dataset A/B source.
* ``wc_2026_results_through_june21.csv`` — elapsed 2026 World Cup results.
* ``wc_team_elo_baseline_june11.csv`` — frozen pre-tournament Elo baseline.
* ``wc_2026_matches_june_22-27.csv`` — canonical current fixtures.
* ``odds_june*.csv`` — verbatim screenshot-derived odds.

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
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parent
HISTORICAL = ROOT / "wc_backtest_historical_dataset.csv"
RESULTS_2026 = ROOT / "wc_2026_results_through_june21.csv"
ELO_BASELINE = ROOT / "wc_team_elo_baseline_june11.csv"
FIXTURES = ROOT / "wc_2026_matches_june_22-27.csv"
ODDS_PARTS = (
    ROOT / "odds_june22_23.csv",
    ROOT / "odds_june24.csv",
    ROOT / "odds_june25_26.csv",
    ROOT / "odds_june27.csv",
)
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
DATA_CUTOFF = datetime.fromisoformat("2026-06-21T23:59:00-05:00")
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
    """Return ordered evaluation windows; configuration never sees future rows."""
    n = len(rows)
    start = max(40, int(n * 0.55))
    remaining = n - start
    width = max(1, remaining // folds)
    windows = []
    for i in range(folds):
        lo = start + i * width
        hi = n if i == folds - 1 else min(n, lo + width)
        if lo < hi:
            windows.append(list(rows[lo:hi]))
    return windows


def calibrate_elo(rows: Sequence[HistoricalRow]) -> Dict[str, object]:
    """Select parameters on pre-holdout rows and report untouched final holdout."""
    configs = []
    holdout_start = int(len(rows) * 0.85)
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


def expected_lambdas(elo_a: float, elo_b: float, mu_total: float, adj_a: float, adj_b: float) -> Tuple[float, float]:
    gap = (elo_a + adj_a) - (elo_b + adj_b)
    share = 0.5 + 0.34 * math.tanh(gap / 420.0)
    return max(0.12, mu_total * share), max(0.12, mu_total * (1.0 - share))


def settle_line(value: float, line: float) -> float:
    """Return 1 win, 0 push, -1 loss for one Asian line."""
    adjusted = value + line
    return 1.0 if adjusted > 1e-9 else -1.0 if adjusted < -1e-9 else 0.0


def split_quarter_line(line: float) -> Tuple[float, ...]:
    doubled = line * 2.0
    if abs(doubled - round(doubled)) < 1e-9:
        return (line,)
    return (math.floor(doubled) / 2.0, math.ceil(doubled) / 2.0)


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

    if market in {"total_goals", "number_of_goals", "number_of_goals_full_time"}:
        try:
            line = float(odd["line"])
        except (TypeError, ValueError):
            return None
        over = selection.startswith("over")
        under = selection.startswith("under")
        if not (over or under):
            return None
        for ga, gb, prob in matrix:
            value = (ga + gb) - line if over else line - (ga + gb)
            result = 1.0 if value > 1e-9 else -1.0 if value < -1e-9 else 0.0
            if result > 0: p_win += prob
            elif result == 0: p_push += prob
            else: p_loss += prob

    elif market in {"both_teams_to_score", "btts"}:
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

    elif market == "asian_handicap":
        try:
            line = float(odd["line"])
        except (TypeError, ValueError):
            return None
        selected = TEAM_ALIASES.get(selection)
        if selected is None and selection_id.startswith(("home", "1")):
            selected = team_a
        if selected is None and selection_id.startswith(("away", "2")):
            selected = team_b
        if selected not in {team_a, team_b}:
            return None
        lines = split_quarter_line(line)
        expected_net = 0.0
        full_win_equivalent = 0.0
        full_push_equivalent = 0.0
        for ga, gb, prob in matrix:
            margin = ga - gb if selected == team_a else gb - ga
            returns = []
            for subline in lines:
                result = settle_line(margin, subline)
                returns.append(price if result > 0 else 1.0 if result == 0 else 0.0)
            gross = sum(returns) / len(returns)
            expected_net += prob * (gross - 1.0)
            full_win_equivalent += prob * max(0.0, min(1.0, (gross - 1.0) / (price - 1.0)))
            full_push_equivalent += prob * (1.0 if abs(gross - 1.0) < 1e-9 else 0.0)
        return {
            "p_win": full_win_equivalent,
            "p_push": full_push_equivalent,
            "p_loss": max(0.0, 1.0 - full_win_equivalent - full_push_equivalent),
            "ev": expected_net,
        }
    else:
        return None

    ev = p_win * (price - 1.0) - p_loss
    return {"p_win": p_win, "p_push": p_push, "p_loss": p_loss, "ev": ev}


def load_and_merge_odds(fixtures: Sequence[Mapping[str, str]]) -> List[Dict[str, str]]:
    """Merge date-owned extractions and attach canonical fixture IDs."""
    canonical = {}
    canonical_ids = {fixture["fixture_id"] for fixture in fixtures}
    kickoff_by_id = {fixture["fixture_id"]: fixture["kickoff_lima"] for fixture in fixtures}
    for fixture in fixtures:
        a, b = split_fixture(fixture["match"])
        canonical[frozenset((a, b))] = fixture["fixture_id"]
    merged: List[Dict[str, str]] = []
    seen = set()
    for path in ODDS_PARTS:
        for row in read_csv(path):
            row = dict(row)
            if row.get("fixture_id") in canonical_ids:
                row["fixture_id"] = row["fixture_id"]
            else:
                a, b = split_fixture(row["fixture_display"])
                key = frozenset((a, b))
                if key not in canonical:
                    raise ValueError(f"Odds fixture absent from canonical schedule: {row['fixture_display']}")
                row["fixture_id"] = canonical[key]
            row["source_sha256"] = sha256(ROOT / "Screenshots" / row["source_image"])
            row["kickoff_local"] = kickoff_by_id[row["fixture_id"]]
            unique = (
                row["fixture_id"], row["app"], row["market_id"], row["selection_id"],
                row["line"], row["odds"], row["source_image"],
            )
            if unique in seen:
                continue
            seen.add(unique)
            merged.append(row)
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
                raise ValueError(f"Research row has unknown fixture_id: {fixture_id}")
            if fixture_id in merged:
                raise ValueError(f"Duplicate research row: {fixture_id}")
            if "https://" not in row["source_urls"]:
                raise ValueError(f"Research row lacks direct URL: {fixture_id}")
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
    if missing:
        raise ValueError(f"Research coverage is incomplete: {sorted(missing)}")
    return merged


def screenshot_manifest(odds: Sequence[Mapping[str, str]]) -> List[Dict[str, object]]:
    """Inventory every current screenshot, including images without transcribed selections."""
    odds_counts: Dict[str, int] = defaultdict(int)
    for row in odds:
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
            "app": "Betano" if number <= 7614 else "Betsson",
            "transcribed_selection_rows": odds_counts[path.name],
            "inventory_status": "odds_transcribed" if odds_counts[path.name] else "reviewed_no_supported_row",
        })
    if len(rows) != 216:
        raise ValueError(f"Expected 216 current screenshots, found {len(rows)}")
    return rows


def current_team_state(
    results: Sequence[Mapping[str, str]], baseline: Mapping[str, float],
) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], Dict[str, date]]:
    ratings = dict(baseline)
    form: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        "games": 0.0, "points": 0.0, "gf": 0.0, "ga": 0.0,
    })
    last_date: Dict[str, date] = {}
    for row in sorted(results, key=lambda item: item["date"]):
        ta, tb = row["team_a"], row["team_b"]
        sa, sb = int(row["score_a"]), int(row["score_b"])
        for team, gf, ga in ((ta, sa, sb), (tb, sb, sa)):
            form[team]["games"] += 1.0
            form[team]["gf"] += gf
            form[team]["ga"] += ga
            form[team]["points"] += 3.0 if gf > ga else 1.0 if gf == ga else 0.0
            last_date[team] = date.fromisoformat(row["date"])
        update_elo(ratings, ta, tb, sa, sb)
    return ratings, form, last_date


def form_adjustment(stats: Mapping[str, float]) -> float:
    games = max(1.0, stats.get("games", 0.0))
    ppg = stats.get("points", 0.0) / games
    gdpg = (stats.get("gf", 0.0) - stats.get("ga", 0.0)) / games
    return max(-45.0, min(45.0, (ppg - 1.35) * 12.0 + gdpg * 8.0))


def classify(ev_pct: float, robust: bool, divergence_pp: float) -> Tuple[str, int]:
    if divergence_pp > 15.0 or ev_pct > 25.0:
        return "HALT", 35
    # Policy profitability has not yet been validated out of sample.
    return "PASS", 30


def build() -> Dict[str, object]:
    fixtures = read_csv(FIXTURES)
    if len(fixtures) != 32 or len({row["fixture_id"] for row in fixtures}) != 32:
        raise ValueError("Canonical fixture file must contain exactly 32 unique fixtures")

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
    mu_total = 0.75 * mu_a + 0.25 * mu_b

    baseline_rows = read_csv(ELO_BASELINE)
    baseline = {row["team"]: float(row["elo"]) for row in baseline_rows}
    results = read_csv(RESULTS_2026)
    ratings, form, last_dates = current_team_state(results, baseline)
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
        # Tournament form is published descriptively but not added again to Elo:
        # current results have already changed the updated rating.
        fa, fb = 0.0, 0.0
        host_a = host_b = 0.0
        p_base = three_way_elo(
            ratings[ta], ratings[tb], float(best["divisor"]),
            float(best["draw_base"]), float(best["draw_slope"]),
            fa + host_a, fb + host_b,
        )
        la, lb = expected_lambdas(ratings[ta], ratings[tb], mu_total, fa + host_a, fb + host_b)
        matrix = score_matrix(la, lb)
        candidate_rows = []
        # Compute a de-vigged consensus for complete standard 1X2 markets.
        market_consensus: Dict[Tuple[str, str], float] = {}
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
        for odd in odds_by_fixture[fixture["fixture_id"]]:
            if odd["market_id"] != "match_result":
                continue
            evaluated = probability_and_ev(odd, ta, tb, p_base, matrix)
            if evaluated is None:
                continue
            ev_pct = evaluated["ev"] * 100.0
            # Conservative stress: move three percentage points against the selection.
            stressed_ev = ((max(0.0, evaluated["p_win"] - 0.03) * (float(odd["odds"]) - 1.0))
                           - min(1.0, evaluated["p_loss"] + 0.03)) * 100.0
            bucket = selection_bucket(odd, ta, tb)
            implied = market_consensus.get((odd["app"], bucket), 1.0 / float(odd["odds"]))
            divergence = abs(evaluated["p_win"] - implied) * 100.0
            strength, confidence = classify(ev_pct, stressed_ev > 0.0, divergence)
            candidate_rows.append({
                **odd,
                **evaluated,
                "ev_pct": ev_pct,
                "stressed_ev_pct": stressed_ev,
                "divergence_pp": divergence,
                "strength": strength,
                "confidence": confidence,
            })
        ranked = sorted(candidate_rows, key=lambda row: row["ev_pct"], reverse=True)
        complete_apps = [
            app for app, selections in grouped.items()
            if set(selections) == {"A", "D", "B"}
        ]
        if not complete_apps:
            raise ValueError(
                f"Fixture lacks a complete supported 1X2 market: {fixture['fixture_id']}"
            )
        halted = [row for row in ranked if row["strength"] == "HALT"]
        recommendation = halted[0] if halted else (ranked[0] if ranked else None)
        last_a = last_dates.get(ta)
        last_b = last_dates.get(tb)
        rest_a = (kickoff.date() - last_a).days if last_a else None
        rest_b = (kickoff.date() - last_b).days if last_b else None
        model_row = {
            "fixture_id": fixture["fixture_id"], "kickoff_lima": fixture["kickoff_lima"],
            "kickoff_utc": fixture["kickoff_utc"], "team_a": ta, "team_b": tb,
            "elo_a_baseline": baseline[ta], "elo_b_baseline": baseline[tb],
            "elo_a_updated": round(ratings[ta], 3), "elo_b_updated": round(ratings[tb], 3),
            "form_games_a": int(form[ta]["games"]), "form_games_b": int(form[tb]["games"]),
            "form_points_a": int(form[ta]["points"]), "form_points_b": int(form[tb]["points"]),
            "form_gd_a": int(form[ta]["gf"] - form[ta]["ga"]),
            "form_gd_b": int(form[tb]["gf"] - form[tb]["ga"]),
            "form_adjust_a": round(fa, 3), "form_adjust_b": round(fb, 3),
            "host_adjust_a": host_a, "host_adjust_b": host_b,
            "rest_days_a": rest_a, "rest_days_b": rest_b,
            "mu_total": round(mu_total, 5), "lambda_a": round(la, 5), "lambda_b": round(lb, 5),
            "p_win_a": round(p_base[0], 8), "p_draw": round(p_base[1], 8),
            "p_win_b": round(p_base[2], 8),
            "source_elo": "wc_team_elo_baseline_june11.csv + deterministic Elo updates from wc_2026_results_through_june21.csv",
            "source_form": "wc_2026_results_through_june21.csv",
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
        rec = recommendation
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
            "expected_goals": {"team_a": round(la, 3), "team_b": round(lb, 3)},
            "recommendation": None if rec is None else {
                "app": rec["app"], "market_id": rec["market_id"],
                "market_original": rec["market_original"],
                "selection_original": rec["selection_original"],
                "line": rec["line"], "odds": float(rec["odds"]),
                "p_win": round(rec["p_win"], 6), "p_push": round(rec["p_push"], 6),
                "ev_pct": round(rec["ev_pct"], 2),
                "stressed_ev_pct": round(rec["stressed_ev_pct"], 2),
                "strength": rec["strength"], "confidence": rec["confidence"],
                "source_image": rec["source_image"],
                "source_sha256": rec["source_sha256"],
            },
            "supported_markets_evaluated": len(candidate_rows),
            "recommendation_scope": "standard full-time 1X2 only; other markets are displayed as source data but not recommended",
            "freshness_status": freshness_status(kickoff),
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
    input_hashes = {
        path.name: sha256(path) for path in
        (HISTORICAL, RESULTS_2026, ELO_BASELINE, FIXTURES, *ODDS_PARTS, *RESEARCH_PARTS)
    }
    metrics = {
        "version": "june22_27_integrity_v1",
        "seed": SEED,
        "dataset_a_rows": len(dataset_a),
        "dataset_b_rows": len(dataset_b),
        "elapsed_wc2026_rows": len(results),
        "calibration": best,
        "mu_dataset_a": mu_a,
        "mu_dataset_b": mu_b,
        "mu_production": mu_total,
        "input_hashes": input_hashes,
        "pipeline_sha256": sha256(Path(__file__)),
    }
    payload = {
        "schema_version": "2.0",
        "generated_at": "2026-06-21T23:59:00-05:00",
        "batch": {"start": "2026-06-22", "end": "2026-06-27", "fixture_count": 32},
        "model": metrics,
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
            "WCdecider June 22–27, 2026 provenance",
            "=======================================",
            "",
            "Canonical fixtures: wc_2026_matches_june_22-27.csv",
            "Elapsed outcomes: wc_2026_results_through_june21.csv",
            "Pre-tournament Elo: wc_team_elo_baseline_june11.csv",
            "Historical Dataset A/B source: wc_backtest_historical_dataset.csv",
            "Screenshot-derived odds: odds_june22_23.csv, odds_june24.csv, odds_june25_26.csv, odds_june27.csv",
            "Complete screenshot inventory: wc_screenshot_manifest_june22_27.csv",
            "OSINT notes: research_june22_23.csv, research_june24_25.csv, research_june26_27.csv",
            "Sanitized canonical OSINT output: wc_research_june22_27.csv (post-cutoff sources are excluded).",
            "",
            "Column derivations:",
            "- updated Elo: sequential neutral-site World Cup Elo update with K=60 and goal-margin multiplier.",
            "- goal-margin multiplier: 1.0 for one-goal/draw, 1.5 for two goals, (11+margin)/8 for three or more.",
            "- form features: tournament games, points, goals for/against through June 21.",
            "- tournament form: descriptive only in production; no second adjustment after Elo updates.",
            "- probabilities: chronologically calibrated Elo three-way conversion.",
            "- parameter grid: divisor {350,400,450,500}; draw_base {.14,.16,.18,.20,.22}; draw_slope {.06,.08,.10,.12}.",
            "- selection split: first 85% by time; final 15% untouched holdout. Selection rows use four ordered windows after the first 55%.",
            "- expected goals: 75% Dataset A mean + 25% Dataset B mean; team share = .5 + .34*tanh(Elo gap/420).",
            "- score grid: independent Poisson scores 0..10, renormalized. It is descriptive only in this release.",
            "- EV/recommendations: standard full-time 1X2 markets only in this release.",
            "- stress EV: subtract 3 percentage points from selected win probability and add 3 points to loss probability.",
            "- classification: divergence >15pp or EV >25% HALT; all other selections PASS until recommendation-policy profitability is validated out of sample.",
            "- source_sha256: SHA-256 of the exact screenshot containing the price.",
            "",
            "Model selection:",
            "- Hyperparameters are selected on pre-holdout chronological windows and evaluated on an untouched final 15% holdout.",
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
