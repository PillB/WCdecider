#!/usr/bin/env python3
"""Read-only preflight checks for WCdecider manual-odds releases."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable


FORBIDDEN_UI_TEXT = (
    "Best available watchlist",
    "ELI5: check this exact watchlist",
    "Open Football → World Cup",
    "Open Sports → Football → World Cup",
    "Full-cover arbitrage found",
    "No guaranteed full-cover arbitrage",
    "Step by step in ",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"FAIL\t{message}")


def ok(message: str) -> None:
    print(f"OK\t{message}")


def row_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def discover_manual_csvs(root: Path) -> Iterable[Path]:
    return sorted(root.glob("manual_odds_*.csv"))


def check_manual_sources(root: Path, failures: list[str]) -> None:
    csvs = list(discover_manual_csvs(root))
    if not csvs:
        fail("no manual_odds_*.csv files found", failures)
        return
    for csv_path in csvs:
        provenance_path = csv_path.with_suffix(".provenance.json")
        if not provenance_path.exists():
            fail(f"{csv_path.name} missing provenance sidecar", failures)
            continue
        provenance = load_json(provenance_path)
        rows = row_count(csv_path)
        if provenance.get("schema") != "manual_wcdecider_odds_v1":
            fail(f"{provenance_path.name} has unsupported schema {provenance.get('schema')!r}", failures)
        if provenance.get("output_csv") not in {csv_path.name, str(csv_path.name)}:
            fail(f"{provenance_path.name} output_csv does not match {csv_path.name}", failures)
        provenance_rows = provenance.get(
            "row_count",
            provenance.get("row_count_written", provenance.get("rows")),
        )
        if int(provenance_rows if provenance_rows is not None else -1) != rows:
            fail(f"{csv_path.name} row count {rows} != provenance {provenance_rows}", failures)
        recorded_sha = provenance.get("sha256") or provenance.get("output_sha256")
        if recorded_sha and recorded_sha != sha256(csv_path):
            fail(f"{csv_path.name} sha256 does not match provenance", failures)
        ok(f"{csv_path.name} rows={rows} provenance={provenance_path.name}")


def check_release_artifacts(root: Path, failures: list[str]) -> None:
    predictions_path = root / "wc_june22_27_predictions.json"
    metrics_path = root / "wc_june22_27_model_metrics.json"
    audit_path = root / "wc_june22_27_datapoint_audit_summary.json"
    release_path = root / "governance" / "release_validation_june22_27.json"
    for path in (predictions_path, metrics_path, audit_path, release_path):
        if not path.exists():
            fail(f"missing artifact {path.relative_to(root)}", failures)
            return

    predictions = load_json(predictions_path)
    metrics = load_json(metrics_path)
    audit = load_json(audit_path)
    release = load_json(release_path)

    if audit.get("final_status") != "PASS" or audit.get("blocked_rows") != 0:
        fail("datapoint audit is not PASS with blocked_rows=0", failures)
    else:
        ok(f"datapoint audit PASS rows={audit.get('audit_rows')}")

    if release.get("final_status") != "PASS":
        fail("release validation final_status is not PASS", failures)
    else:
        ok("release validation PASS")

    recommendation_count = sum(1 for row in predictions.get("predictions", []) if row.get("recommendation"))
    production_stake = sum(
        float(row.get("rank_one_comparison", {}).get("budget_simulation", {}).get("stake", 0.0))
        for row in predictions.get("predictions", [])
    )
    if recommendation_count != 0 or production_stake != 0.0:
        fail(f"production recommendation/stake not fail-closed recommendations={recommendation_count} stake={production_stake}", failures)
    else:
        ok("production recommendations and stakes are fail-closed")

    governance = metrics.get("evaluation_governance", {})
    if governance.get("recommendation_release_status") != "blocked":
        fail("metrics recommendation_release_status is not blocked", failures)
    else:
        ok("metrics recommendation release status is blocked")


def check_forbidden_ui_text(root: Path, failures: list[str]) -> None:
    checked = []
    for rel in ("scripts/generate_report.py", "index.html"):
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        checked.append(rel)
        for phrase in FORBIDDEN_UI_TEXT:
            if phrase in text:
                fail(f"forbidden UI phrase in {rel}: {phrase}", failures)
    if checked:
        ok(f"checked forbidden UI text in {', '.join(checked)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="WCdecider repo root")
    args = parser.parse_args()
    root = Path(args.repo).resolve()
    failures: list[str] = []

    check_manual_sources(root, failures)
    check_release_artifacts(root, failures)
    check_forbidden_ui_text(root, failures)

    if failures:
        print(f"BLOCKED\t{len(failures)} preflight failure(s)")
        return 1
    print("PASS\tmanual release preflight checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
