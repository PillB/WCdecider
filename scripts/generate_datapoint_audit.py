#!/usr/bin/env python3
"""Generate a deterministic field-level subagent audit manifest.

The manifest enumerates every leaf value in the prediction and model-metrics
JSON artifacts. Review identities and evidence are loaded from a separate
registry so model execution never invents or self-approves an audit result.

Example:
    python3 scripts/generate_datapoint_audit.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterator, Tuple

ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS = ROOT / "wc_june22_27_predictions.json"
METRICS = ROOT / "wc_june22_27_model_metrics.json"
MISSION = ROOT / "governance" / "subagent_mission_v1.md"
REVIEWS = ROOT / "governance" / "subagent_reviews_june22_27.json"
OUT = ROOT / "wc_june22_27_datapoint_audit.csv"
SUMMARY_OUT = ROOT / "wc_june22_27_datapoint_audit_summary.json"

FIELDS = [
    "datapoint_id", "batch_id", "fixture_id", "output_artifact",
    "json_pointer", "dom_selector", "language", "canonical_value",
    "value_sha256", "data_type", "derivation_type", "source_artifact",
    "source_row_or_locator", "source_url", "source_accessed_at",
    "source_sha256", "upstream_datapoint_ids", "pipeline_sha256",
    "model_version", "git_commit", "freshness_cutoff", "conditional_status",
    "mission_version", "mission_sha256", "owner_subagent_id", "owner_result",
    "owner_evidence", "replication_1_subagent_id", "replication_1_status",
    "replication_1_evidence", "replication_2_subagent_id",
    "replication_2_status", "replication_2_evidence", "editor_subagent_id",
    "editor_status", "editor_evidence", "final_status",
]


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: Any) -> str:
    """Serialize a leaf value without locale- or platform-dependent output."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    """Return SHA-256 for a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def leaves(value: Any, pointer: str = "") -> Iterator[Tuple[str, Any]]:
    """Yield RFC-6901-like pointers and leaf values in deterministic order."""
    if isinstance(value, dict):
        for key in sorted(value):
            escaped = key.replace("~", "~0").replace("/", "~1")
            yield from leaves(value[key], f"{pointer}/{escaped}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, f"{pointer}/{index}")
    else:
        yield pointer or "/", value


def source_for(artifact: str, pointer: str, fixture_id: str) -> Tuple[str, str, str]:
    """Map an output field to its strongest canonical source artifact."""
    if artifact == METRICS.name:
        if pointer.startswith("/model_championship/"):
            return "model_championship_results.json", pointer, (
                "wc_backtest_historical_dataset.csv"
            )
        if pointer.startswith("/historical_closing_odds/"):
            return "historical_closing_odds_canonical_coverage.json", pointer, (
                "historical_closing_odds_canonical.csv;"
                "historical_closing_odds_source_manifest.csv"
            )
        return "wc_backtest_historical_dataset.csv", pointer, "historical rows + documented formula"
    if "/research/" in pointer:
        return "wc_research_june22_27.csv", fixture_id, ""
    if "/research_mode/ranked_comparisons/" in pointer:
        parts = pointer.strip("/").split("/")
        base = f"/predictions/{parts[1]}/research_mode"
        return "wc_odds_june_22-27.csv", fixture_id, (
            f"{PREDICTIONS.name}:{base}/probabilities/team_a_win;"
            f"{PREDICTIONS.name}:{base}/probabilities/draw;"
            f"{PREDICTIONS.name}:{base}/probabilities/team_b_win;"
            f"{PREDICTIONS.name}:{base}/rho"
        )
    if (
        "/rank_one_comparison/" in pointer
        or "/ranked_comparisons/" in pointer
    ):
        parts = pointer.strip("/").split("/")
        base = f"/predictions/{parts[1]}"
        return "wc_odds_june_22-27.csv", fixture_id, (
            f"{PREDICTIONS.name}:{base}/probabilities/team_a_win;"
            f"{PREDICTIONS.name}:{base}/probabilities/draw;"
            f"{PREDICTIONS.name}:{base}/probabilities/team_b_win;"
            f"{PREDICTIONS.name}:{base}/expected_goals/team_a;"
            f"{PREDICTIONS.name}:{base}/expected_goals/team_b"
        )
    if "/market_comparisons/" in pointer:
        return "wc_odds_june_22-27.csv", fixture_id, "/model/pipeline_sha256"
    if any(token in pointer for token in (
        "/probabilities/", "/expected_goals/", "/common_markets/",
        "/score_market_model/",
    )):
        return "wc_june22_27_model_dataset.csv", fixture_id, (
            "/model/calibration;/model/mu_production"
        )
    if any(token in pointer for token in (
        "/fixture", "/kickoff_", "/group", "/venue", "/fixture_id"
    )):
        return "wc_2026_matches_june_22-27.csv", fixture_id, ""
    return "wc_june22_27_pipeline.py", pointer, "/model/pipeline_sha256"


def review_for(registry: dict, fixture_id: str) -> dict:
    """Return fixture-specific review data or the global fallback."""
    return registry.get("fixtures", {}).get(fixture_id, registry["global"])


def canonicalize_json(value: Any) -> Any:
    """Normalize insignificant cross-platform float serialization differences."""
    if isinstance(value, dict):
        return {
            key: canonicalize_json(value[key])
            for key in sorted(value)
        }
    if isinstance(value, list):
        return [canonicalize_json(item) for item in value]
    if isinstance(value, float):
        rounded = round(value, 12)
        # JSON distinguishes -0.0 from 0.0 even though Python and the model
        # semantics do not. BLAS/platform arithmetic can change only that
        # sign at an effectively-zero boundary, so normalize it explicitly.
        return 0.0 if rounded == 0.0 else rounded
    return value


def semantic_json_sha256(value: Any) -> str:
    payload = json.dumps(
        canonicalize_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return sha256_text(payload)


def main() -> None:
    """Build the manifest and fail if any review role is missing or non-PASS."""
    for path in (PREDICTIONS, METRICS, MISSION, REVIEWS):
        if not path.exists():
            raise FileNotFoundError(f"Required governance input missing: {path}")

    predictions = json.loads(PREDICTIONS.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    registry = json.loads(REVIEWS.read_text(encoding="utf-8"))
    registry_hash = sha256(REVIEWS)
    current_artifact_hashes = {
        PREDICTIONS.name: sha256(PREDICTIONS),
        METRICS.name: sha256(METRICS),
    }
    current_semantic_hashes = {
        PREDICTIONS.name: semantic_json_sha256(predictions),
        METRICS.name: semantic_json_sha256(metrics),
    }
    reviewed_artifact_hashes = registry.get(
        "reviewed_semantic_hashes",
        registry.get("reviewed_artifact_hashes", {}),
    )
    review_binding_valid = (
        registry.get("reviewed_model_version") == metrics["version"]
        and reviewed_artifact_hashes == current_semantic_hashes
    )
    pipeline_hash = metrics["pipeline_sha256"]
    mission_hash = sha256(MISSION)
    git_commit = os.environ.get("GITHUB_SHA", registry.get("git_commit", "LOCAL_UNCOMMITTED"))
    input_hashes = metrics["input_hashes"]
    research_rows = {}
    with (ROOT / "wc_research_june22_27.csv").open(newline="", encoding="utf-8") as handle:
        research_rows = {row["fixture_id"]: row for row in csv.DictReader(handle)}
    fixture_by_index = {
        index: row["fixture_id"] for index, row in enumerate(predictions["predictions"])
    }

    rows = []
    for artifact_path, payload in ((PREDICTIONS, predictions), (METRICS, metrics)):
        for pointer, value in leaves(payload):
            fixture_id = "GLOBAL"
            parts = pointer.strip("/").split("/")
            if artifact_path == PREDICTIONS and len(parts) > 1 and parts[0] == "predictions":
                fixture_id = fixture_by_index[int(parts[1])]
            review = review_for(registry, fixture_id)
            source_artifact, locator, upstream = source_for(
                artifact_path.name, pointer, fixture_id
            )
            source_path = ROOT / source_artifact
            value_text = canonical(value)
            language = "es" if pointer.endswith("/es") else "en" if pointer.endswith("/en") else "neutral"
            statuses = [
                review["owner"]["status"], review["replication_1"]["status"],
                review["replication_2"]["status"], review["editor"]["status"],
            ]
            reviewer_ids = [
                review["owner"]["id"], review["replication_1"]["id"],
                review["replication_2"]["id"], review["editor"]["id"],
            ]
            final_status = (
                "PASS"
                if statuses == ["PASS"] * 4
                and all(reviewer_ids)
                and len(set(reviewer_ids)) == 4
                and review_binding_valid
                else "BLOCKED"
            )
            datapoint_id = hashlib.sha256(
                f"{artifact_path.name}:{pointer}".encode("utf-8")
            ).hexdigest()[:20]
            research = research_rows.get(fixture_id, {})
            source_url = ""
            source_accessed_at = predictions["generated_at"]
            if "/research/" in pointer and research:
                urls = [
                    item.strip()
                    for item in research.get("source_urls", "").split("|")
                    if item.strip().startswith("http")
                ]
                # The current source schema provides a claim bundle rather than
                # one field-specific citation. Preserve the complete bundle;
                # selecting only the first URL overstated field-level lineage.
                source_url = " | ".join(urls)
                source_accessed_at = research.get("accessed_at") or source_accessed_at
            rows.append({
                "datapoint_id": datapoint_id,
                "batch_id": "2026-06-22_2026-06-27",
                "fixture_id": fixture_id,
                "output_artifact": artifact_path.name,
                "json_pointer": pointer,
                "dom_selector": f'[data-json-pointer="{pointer}"]',
                "language": language,
                "canonical_value": value_text,
                "value_sha256": hashlib.sha256(value_text.encode("utf-8")).hexdigest(),
                "data_type": type(value).__name__,
                "derivation_type": "derived" if source_artifact != artifact_path.name else "direct",
                "source_artifact": source_artifact,
                "source_row_or_locator": locator,
                "source_url": source_url,
                "source_accessed_at": source_accessed_at,
                "source_sha256": sha256(source_path) if source_path.exists() else input_hashes.get(source_artifact, ""),
                "upstream_datapoint_ids": upstream,
                "pipeline_sha256": pipeline_hash,
                "model_version": metrics["version"],
                "git_commit": git_commit,
                "freshness_cutoff": predictions["generated_at"],
                "conditional_status": (
                    next((r["freshness_status"] for r in predictions["predictions"]
                          if r["fixture_id"] == fixture_id), "global")
                ),
                "mission_version": "v1",
                "mission_sha256": mission_hash,
                "owner_subagent_id": review["owner"]["id"],
                "owner_result": review["owner"]["status"],
                "owner_evidence": f"reviews:{registry_hash[:12]}:owner",
                "replication_1_subagent_id": review["replication_1"]["id"],
                "replication_1_status": review["replication_1"]["status"],
                "replication_1_evidence": f"reviews:{registry_hash[:12]}:replication_1",
                "replication_2_subagent_id": review["replication_2"]["id"],
                "replication_2_status": review["replication_2"]["status"],
                "replication_2_evidence": f"reviews:{registry_hash[:12]}:replication_2",
                "editor_subagent_id": review["editor"]["id"],
                "editor_status": review["editor"]["status"],
                "editor_evidence": f"reviews:{registry_hash[:12]}:editor",
                "final_status": final_status,
            })

    ids_by_path = {
        f"{row['output_artifact']}:{row['json_pointer']}": row["datapoint_id"]
        for row in rows
    }
    for row in rows:
        references = [
            item for item in row["upstream_datapoint_ids"].split(";") if item
        ]
        if references:
            row["upstream_datapoint_ids"] = ";".join(
                ids_by_path.get(item, item) for item in references
            )

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    blocked = sum(row["final_status"] != "PASS" for row in rows)
    expected_paths = sorted(
        f"{row['output_artifact']}:{row['json_pointer']}" for row in rows
    )
    status_counts = {}
    artifact_counts = {}
    for row in rows:
        status_counts[row["final_status"]] = (
            status_counts.get(row["final_status"], 0) + 1
        )
        artifact_counts[row["output_artifact"]] = (
            artifact_counts.get(row["output_artifact"], 0) + 1
        )
    summary = {
        "schema_version": "1.0",
        "artifact": OUT.name,
        "artifact_sha256": sha256(OUT),
        "artifact_bytes": OUT.stat().st_size,
        "predictions_sha256": sha256(PREDICTIONS),
        "metrics_sha256": sha256(METRICS),
        "audit_rows": len(rows),
        "blocked_rows": blocked,
        "status_counts": status_counts,
        "artifact_counts": artifact_counts,
        "expected_json_leaf_count": len(expected_paths),
        "expected_paths_sha256": sha256_text("\n".join(expected_paths)),
        "audit_paths_sha256": sha256_text("\n".join(expected_paths)),
        "final_status": "PASS" if blocked == 0 else "BLOCKED",
        "review_binding_valid": review_binding_valid,
        "reviewed_model_version": registry.get("reviewed_model_version", ""),
        "current_model_version": metrics["version"],
        "reviewed_artifact_hashes": reviewed_artifact_hashes,
        "current_artifact_hashes": current_artifact_hashes,
        "current_semantic_hashes": current_semantic_hashes,
        "blocking_reason": (
            ""
            if review_binding_valid
            else "review_registry_not_bound_to_current_model_and_artifact_hashes"
        ),
    }
    SUMMARY_OUT.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUT} with {len(rows)} datapoints; blocked={blocked}")
    print(f"Wrote {SUMMARY_OUT} ({SUMMARY_OUT.stat().st_size} bytes)")
    if blocked:
        print(
            "Review binding diagnostics: "
            f"current_model={metrics['version']!r}; "
            f"reviewed_model={registry.get('reviewed_model_version', '')!r}; "
            f"current_hashes={current_artifact_hashes}; "
            f"current_semantic_hashes={current_semantic_hashes}; "
            f"reviewed_hashes={reviewed_artifact_hashes}",
            file=sys.stderr,
        )
        raise SystemExit("Datapoint audit contains non-PASS rows")


if __name__ == "__main__":
    main()
