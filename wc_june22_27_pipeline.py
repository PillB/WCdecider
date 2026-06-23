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
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

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
) -> Dict[str, float]:
    """Bootstrap challenger-minus-production loss on the same holdout rows."""
    if len(production) != len(challenger) or not production:
        raise ValueError("Paired bootstrap requires equal non-empty row losses")
    differences = [
        challenger[index][metric] - production[index][metric]
        for index in range(len(production))
    ]
    rng = random.Random(SEED)
    sampled_means = []
    for _ in range(iterations):
        sample = [
            differences[rng.randrange(len(differences))]
            for _ in range(len(differences))
        ]
        sampled_means.append(sum(sample) / len(sample))
    sampled_means.sort()
    lower = sampled_means[int(iterations * 0.025)]
    upper = sampled_means[int(iterations * 0.975)]
    return {
        "challenger_minus_production_mean": sum(differences) / len(differences),
        "ci_95_lower": lower,
        "ci_95_upper": upper,
        "iterations": iterations,
        "statistically_secure_improvement": upper < 0.0,
    }


def calibrate_score_model(rows: Sequence[HistoricalRow]) -> Dict[str, object]:
    """Select Elo-Poisson parameters before the untouched final holdout.

    Dixon-Coles is retained as a shadow challenger. Production remains
    independent Poisson unless a statistically secure improvement is shown.
    """
    holdout_start = int(len(rows) * 0.85)
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
        try:
            handicap = float(odd["handicap_selected_line"])
            total_line = float(odd["total_line"])
        except (TypeError, ValueError):
            return None
        selected = odd.get("selected_team")
        total_side = odd.get("combo_leg_2_selection")
        if selected not in {team_a, team_b} or total_side not in {"over", "under"}:
            return None
        for ga, gb, prob in matrix:
            margin = ga - gb if selected == team_a else gb - ga
            handicap_win = settle_line(margin, handicap) > 0
            total = ga + gb
            total_win = total > total_line if total_side == "over" else total < total_line
            if handicap_win and total_win:
                p_win += prob
            else:
                p_loss += prob
    else:
        return None

    ev = p_win * (price - 1.0) - p_loss
    return {"p_win": p_win, "p_push": p_push, "p_loss": p_loss, "ev": ev}


def normalize_market_schema(
    row: Dict[str, str], team_a: str, team_b: str,
) -> Dict[str, str]:
    """Attach explicit settlement fields without guessing ambiguous contracts."""
    market = row["market_id"]
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
            row["market_group_id"] = f"{row['fixture_id']}|{row['app']}|1x2"
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
            row["total_line"] = str(line)
            row["market_group_id"] = f"{row['fixture_id']}|{row['app']}|total|{line}"
    elif market in {"both_teams_to_score", "btts"}:
        canonical = "yes" if selection in {"yes", "si"} or selection_id == "yes" else "no" if selection == "no" or selection_id == "no" else ""
        if canonical:
            row["market_family"] = "btts"
            row["settlement_rule_id"] = "btts_full_time_v1"
            row["selection_canonical"] = canonical
            row["market_group_id"] = f"{row['fixture_id']}|{row['app']}|btts"
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
            row["market_group_id"] = f"{row['fixture_id']}|{row['app']}|double_chance"
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
            row["handicap_selected_line"] = str(line)
            row["handicap_home_line"] = str(line if selected == team_a else -line)
            row["market_group_id"] = (
                f"{row['fixture_id']}|{row['app']}|asian|{abs(line)}"
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
            or (family == "asian_handicap" and selections == {"home", "away"})
            or (
                family == "handicap_total_combo"
                and selections == {"home_over", "home_under", "away_over", "away_under"}
            )
        )
        for row in group:
            row["is_complete_market"] = "true" if complete else "false"


def load_and_merge_odds(fixtures: Sequence[Mapping[str, str]]) -> List[Dict[str, str]]:
    """Merge date-owned extractions and attach canonical fixture IDs."""
    canonical = {}
    canonical_ids = {fixture["fixture_id"] for fixture in fixtures}
    kickoff_by_id = {fixture["fixture_id"]: fixture["kickoff_lima"] for fixture in fixtures}
    teams_by_id = {}
    for fixture in fixtures:
        a, b = split_fixture(fixture["match"])
        canonical[frozenset((a, b))] = fixture["fixture_id"]
        teams_by_id[fixture["fixture_id"]] = (a, b)
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
            row = normalize_market_schema(row, *teams_by_id[row["fixture_id"]])
            unique = (
                row["fixture_id"], row["app"], row["market_id"], row["selection_id"],
                row["line"], row["odds"], row["source_image"],
            )
            if unique in seen:
                continue
            seen.add(unique)
            merged.append(row)
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
                handicap = float(row["handicap_selected_line"])
                selected = str(row["selected_team"])
                total_line = float(row["total_line"])
                total_side = str(row["combo_leg_2_selection"])
                margin = ga - gb if selected == team_a else gb - ga
                handicap_win = settle_line(margin, handicap) > 0
                total_win = (
                    ga + gb > total_line if total_side == "over"
                    else ga + gb < total_line
                )
                win, loss = (
                    (1.0, 0.0)
                    if handicap_win and total_win else (0.0, 1.0)
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
        "fair_odds": round(published_fair, 3),
        "ev_pct": round(published_ev, 2),
        "stressed_ev_pct": round(
            float(row["decision_stressed_ev_pct"]), 2
        ),
        "raw_model_ev_pct": round(float(row["ev_pct"]), 2),
        "decision_model_weight": row["decision_model_weight"],
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
        "profitability_validation": "not_validated_historical_market_odds",
        "source_image": row["source_image"],
        "source_sha256": row["source_sha256"],
    }


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
    if base_stake * len(rows) > budget or max_stake * len(rows) < budget:
        raise ValueError("Bankroll constraints cannot cover the selected rows")

    scores = {}
    for row in rows:
        rec = row["recommendation"]
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
    stakes = {row["fixture_id"]: base_stake for row in rows}
    remaining = budget - base_stake * len(rows)
    active = set(stakes)
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
        key: math.floor(value * 10.0 + 1e-9) / 10.0
        for key, value in stakes.items()
    }
    tenths_left = int(round((budget - sum(rounded.values())) * 10))
    order = sorted(
        rounded,
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


def app_navigation_steps(
    app: str, fixture: Mapping[str, object], recommendation: Mapping[str, object],
    stake: Optional[float],
) -> Dict[str, List[str]]:
    """Return bilingual novice steps for locating one exact sourced market."""
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
    line = str(recommendation.get("line") or "").strip()
    selection_with_line = f"{selection} {line}".strip()
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
            f"Choose exactly “{selection_with_line}”. Do not substitute a nearby handicap or total line.",
            f"Check the current decimal price. The saved screenshot price is {source_price:.2f}; the model fair-price threshold is {fair:.2f}.",
            final_en,
        ],
        "es": [
            f"Abre {app} y entra a Deportes → Fútbol → Mundial.",
            f"Busca {fixture_es} y confirma la fecha de inicio mostrada en esta tarjeta.",
            f"Abre el mercado llamado “{market_es}”.",
            f"Elige exactamente “{selection_with_line}”. No sustituyas por una línea de hándicap o total parecida.",
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
        "policy": "forced_all_match_coverage_educational_simulation",
        "warning": {
            "en": "This forced-coverage simulation spends the full budget even when EV or stressed EV is negative. It is not a profitability-validated staking system.",
            "es": "Esta simulación de cobertura forzada usa todo el presupuesto incluso cuando el EV o EV estresado es negativo. No es un sistema de apuestas con rentabilidad validada.",
        },
        "apps": {},
    }
    for app in ("Betano", "Betsson"):
        app_rows = [
            row for row in predictions
            if row["recommendation"]["app"] == app
        ]
        stakes = allocate_app_budget(app_rows)
        expected_net = gross_if_all_win = 0.0
        for row in app_rows:
            rec = row["recommendation"]
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
                "steps": app_navigation_steps(app, row, rec, stake),
                "warning": summary["warning"],
            }
        summary["apps"][app] = {
            "fixture_count": len(app_rows),
            "total_stake": round(sum(stakes.values()), 2),
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
    score_config = calibrate_score_model(historical)
    mu_total = float(score_config["mu_total"])

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
        la, lb = expected_lambdas(
            ratings[ta], ratings[tb], mu_total, fa + host_a, fb + host_b,
            float(score_config["allocation"]), float(score_config["gap_scale"]),
            float(score_config["gap_intensity"]),
        )
        matrix = score_matrix(la, lb)
        shadow_matrix = dixon_coles_score_matrix(
            la, lb, float(score_config["shadow_rho"])
        )
        candidate_rows = []
        expanded_rows = []
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
        for mu_multiplier, allocation_shift in (
            (0.90, 0.0), (1.10, 0.0), (1.0, -0.05), (1.0, 0.05)
        ):
            stress_la, stress_lb = expected_lambdas(
                ratings[ta], ratings[tb], mu_total * mu_multiplier, 0.0, 0.0,
                max(0.20, float(score_config["allocation"]) + allocation_shift),
                float(score_config["gap_scale"]),
                float(score_config["gap_intensity"]),
            )
            stress_matrices.append(score_matrix(stress_la, stress_lb))

        for odd in odds_by_fixture[fixture["fixture_id"]]:
            if odd["is_complete_market"] != "true":
                continue
            if odd["market_family"] not in {
                "1x2", "total_goals", "btts", "double_chance",
                "asian_handicap", "handicap_total_combo",
            }:
                continue
            evaluated = probability_and_ev(odd, ta, tb, p_base, matrix)
            if evaluated is None:
                continue
            ev_pct = evaluated["ev"] * 100.0
            if odd["market_family"] == "1x2":
                stressed_ev = (
                    max(0.0, evaluated["p_win"] - 0.03)
                    * (float(odd["odds"]) - 1.0)
                    - min(1.0, evaluated["p_loss"] + 0.03)
                ) * 100.0
                bucket = selection_bucket(odd, ta, tb)
                implied = market_consensus.get(
                    (odd["app"], bucket), 1.0 / float(odd["odds"])
                )
            else:
                stress_values = [
                    probability_and_ev(odd, ta, tb, p_base, stress_matrix)
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
            strength, confidence = classify(ev_pct, stressed_ev > 0.0, divergence)
            base_model_weight = 0.50 if odd["market_family"] == "1x2" else 0.35
            # Large model-market disagreements are precisely where model risk
            # is highest. Shrink harder toward the de-vigged source market.
            model_weight = base_model_weight * max(
                0.10, 1.0 - divergence / 25.0
            )
            # Preserve the model's push mass and interpret the de-vigged source
            # probability conditionally over decisive outcomes. This yields one
            # coherent decision win/push/loss distribution whose fair price and
            # EV reproduce exactly, including Asian quarter/full lines.
            market_push = float(evaluated["p_push"])
            market_win = (1.0 - market_push) * implied
            market_loss = (1.0 - market_push) * (1.0 - implied)
            decision_win = (
                model_weight * float(evaluated["p_win"])
                + (1.0 - model_weight) * market_win
            )
            decision_push = (
                model_weight * float(evaluated["p_push"])
                + (1.0 - model_weight) * market_push
            )
            decision_loss = (
                model_weight * float(evaluated["p_loss"])
                + (1.0 - model_weight) * market_loss
            )
            probability_total = decision_win + decision_push + decision_loss
            decision_win /= probability_total
            decision_push /= probability_total
            decision_loss /= probability_total
            market_ev_pct = (
                market_win * (float(odd["odds"]) - 1.0) - market_loss
            ) * 100.0
            decision_ev_pct = (
                decision_win * (float(odd["odds"]) - 1.0) - decision_loss
            ) * 100.0
            decision_stressed_ev_pct = (
                model_weight * stressed_ev
                + (1.0 - model_weight) * market_ev_pct
            )
            evaluated_row = {
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
                "decision_model_weight": model_weight,
                "strength": strength,
                "confidence": confidence,
                "policy_status": "experimental_non_actionable",
            }
            evaluated_row["recommendation_utility"] = recommendation_utility(
                evaluated_row
            )
            expanded_rows.append(evaluated_row)
            if odd["market_family"] == "1x2":
                candidate_rows.append(evaluated_row)
        ranked = sorted(candidate_rows, key=lambda row: row["ev_pct"], reverse=True)
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
        recommendation = (
            ranked_recommendations[0][0] if ranked_recommendations else None
        )
        recommendation_reason = (
            ranked_recommendations[0][1]
            if ranked_recommendations else "no_complete_sourced_market"
        )
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
        fixture_names = {
            "fixture": {
                "en": f"{names_a[0]} vs {names_b[0]}",
                "es": f"{names_a[1]} vs {names_b[1]}",
            }
        }
        for item in public_ranked_recommendations:
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
                ),
                "es": (
                    "Clasificada por utilidad conservadora de valor esperado "
                    "tras penalizar desacuerdo de mercado y riesgo del mercado."
                ),
            }
            item["steps"] = app_navigation_steps(
                str(item["app"]), fixture_names, item, None
            )
            if int(item["rank"]) == 1:
                item["steps"]["en"][-1] = (
                    "Treat rank one as the primary comparison, not a mandatory "
                    "bet. Recheck the selection, line, 90-minute settlement, "
                    "current price, and team news before deciding."
                )
                item["steps"]["es"][-1] = (
                    "Trata el rango uno como la comparación principal, no como "
                    "apuesta obligatoria. Revisa selección, línea, liquidación "
                    "a 90 minutos, cuota actual y noticias antes de decidir."
                )
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
            "recommendation": rec,
            "top_recommendations": public_ranked_recommendations,
            "top_recommendations_requested": 4,
            "top_recommendations_available": len(
                public_ranked_recommendations
            ),
            "top_recommendations_shortfall_reason": (
                ""
                if len(public_ranked_recommendations) == 4
                else "fewer_than_four_distinct_complete_sourced_events"
            ),
            "supported_markets_evaluated": len(expanded_rows),
            "recommendation_scope": "up to four distinct sourced recommendations are ranked per fixture by stressed EV, disagreement, and family-validation penalties; rank one remains the backward-compatible BEST_AVAILABLE field and historical profitability is not validated",
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
    bankroll_simulation = attach_bankroll_simulation(predictions)
    input_hashes = {
        path.name: sha256(path) for path in
        (HISTORICAL, RESULTS_2026, ELO_BASELINE, FIXTURES, *ODDS_PARTS, *RESEARCH_PARTS)
    }
    metrics = {
        "version": "june22_27_best_available_v3",
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
            "status": "best_available_recommendations_unvalidated_profitability",
            "reason": "No timestamped historical totals, BTTS, Asian-handicap, or combo prices exist for untouched profitability validation.",
            "priced_fixtures": len({
                row["fixture_id"] for row in odds
                if row["market_family"] in {
                    "total_goals", "btts", "asian_handicap",
                    "handicap_total_combo",
                }
                and row["is_complete_market"] == "true"
            }),
            "all_fixture_probability_coverage": 32,
            "recommendations_required": 32,
            "selection_rule": "maximize minimum(base EV, stressed EV) minus 0.35*model-market divergence and market-family uncertainty penalties",
        },
        "research_mode_policy": {
            "toggle_available": True,
            "default_state": "off_production_mode",
            "selected_candidate": "dixon_coles_low_score_correction_shadow",
            "selected_family": "hierarchical_dynamic_poisson_score_research",
            "status": "research_gated_not_production",
            "production_recommendations_unchanged": True,
            "why_selected": (
                "Dixon-Coles is the best currently feasible research-gated "
                "architecture from the expanded registry because it is "
                "football-specific, low-parameter, and reproducible with the "
                "available score data. High-capacity temporal graph and "
                "sequence models remain blocked by the sample-size/edge-count "
                "promotion gate."
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
        "input_hashes": input_hashes,
        "pipeline_sha256": sha256(Path(__file__)),
    }
    payload = {
        "schema_version": "2.0",
        "generated_at": "2026-06-21T23:59:00-05:00",
        "batch": {"start": "2026-06-22", "end": "2026-06-27", "fixture_count": 32},
        "model": metrics,
        "bankroll_simulation": bankroll_simulation,
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
            "- score-model parameter grid: base total goals {2.25,2.50,2.75,3.00}; allocation {.30,.35,.40}; Elo gap scale {350,420,500}; gap intensity {0,.15,.30,.45}.",
            "- expected goals: match total = base_mu + gap_intensity*abs(Elo gap)/400, bounded to [1.5,4.5], then split as .5 + allocation*tanh(Elo gap/gap_scale).",
            "- score grid: tuned independent Poisson scores 0..10, renormalized; Dixon-Coles rho {-0.15,-0.10,-0.05,0,.05,.10,.15} is evaluated as a shadow challenger only.",
            "- score-market outputs: totals 0.5–5.5, BTTS, double chance, total-goal buckets, top correct scores, and Asian handicaps are derived by exact score-grid summation.",
            "- Asian settlement: integer/half lines settle directly; quarter lines split the stake equally across adjacent half-lines and preserve win/push/loss equivalents.",
            "- handicap-plus-total settlement: the signed header handicap applies to selection 1/home and the opposite line to selection 2/away; the total leg and handicap leg are evaluated jointly on each score state.",
            "- visually checked combo semantics: IMG_7660.PNG confirms a negative home header; IMG_7677.PNG confirms the corresponding positive-home convention.",
            "- normalized odds schema: market family, period, settlement rule, selected team, canonical selection, handicap/total lines, combo legs, market group, completeness, transcription status, and confidence.",
            "- unsupported or ambiguous markets: result handicap, early payout, corners, heterogeneous boosts, and incomplete/truncated selections are retained as source rows but excluded from evaluation.",
            "- double-chance consistency: displayed fair prices and screenshot EV both use the same production score grid.",
            "- decision stack: 1X2 starts at 50% structural model / 50% de-vigged market; expanded families start at 35% / 65%; model weight shrinks further as divergence approaches 25pp.",
            "- recommendation utility: minimum(decision EV, stressed decision EV) minus 0.35*divergence, family uncertainty, and HALT penalties.",
            "- ranked recommendations: publish up to four score-state-distinct sourced events; rank one is the highest-utility non-HALT row, or the highest de-vigged market-probability fallback when every row is HALT. Missing ranks remain explicit.",
            "- expanded-market policy: recommendations are best-available comparisons; historical profitability remains unvalidated because the holdout has no timestamped totals/BTTS/Asian/combo prices for ROI or CLV.",
            "- price coverage: all 32 fixtures receive model probabilities/fair prices; EV is computed only for complete screenshot-derived source markets, currently on 12 fixtures.",
            "- recommendation labels: BEST_AVAILABLE is mandatory per fixture; PASS/HALT remain diagnostic and no label implies certainty.",
            "- metric_explanations: bilingual educational JSON generated from the published fixture values for 1/X/2, expected goals, totals, BTTS, and Asian handicap; these fields do not alter model probabilities.",
            "- bankroll simulation: S/100 is allocated separately within the recommendation's sourced app only; every assigned match receives at least S/1, no match exceeds S/10, remaining funds use positive stressed/base EV plus monotonic A>B>C>D risk bonuses, and stakes round to S/0.10 with exact app totals.",
            "- bankroll warnings: forced all-match coverage may include negative-EV/below-fair-price picks; gross return assumes a full win and the model-estimated net is explicitly unvalidated.",
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
