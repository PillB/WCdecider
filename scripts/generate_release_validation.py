#!/usr/bin/env python3
"""Generate the role-level release validation record.

This gate complements the field-level datapoint audit. The datapoint audit
answers "is every published value reviewed?" This record answers "did the
research-agent team validate the exact release artifact, including model
methodology, profitability limits, report interpretation, and deployment
readiness?"

Example:
    python3 scripts/generate_release_validation.py
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from generate_datapoint_audit import semantic_json_sha256

ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS = ROOT / "wc_june22_27_predictions.json"
METRICS = ROOT / "wc_june22_27_model_metrics.json"
AUDIT_SUMMARY = ROOT / "wc_june22_27_datapoint_audit_summary.json"
PROMPT_PACK = ROOT / "governance" / "research_agent_prompt_pack_v1.md"
REVIEWS = ROOT / "governance" / "release_validation_reviews_june22_27.json"
OUT = ROOT / "governance" / "release_validation_june22_27.json"

REQUIRED_ROLES = (
    "storm_moderator",
    "data_lineage",
    "ml_methodology",
    "profitability_staking",
    "clean_room_replication",
    "report_ui_editor",
    "deployment_reliability",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    for path in (PREDICTIONS, METRICS, AUDIT_SUMMARY, PROMPT_PACK, REVIEWS):
        if not path.exists():
            raise FileNotFoundError(f"Required release-validation input missing: {path}")

    predictions = load_json(PREDICTIONS)
    metrics = load_json(METRICS)
    audit_summary = load_json(AUDIT_SUMMARY)
    review_registry = load_json(REVIEWS)

    current_artifact_hashes = {
        PREDICTIONS.name: sha256(PREDICTIONS),
        METRICS.name: sha256(METRICS),
        AUDIT_SUMMARY.name: sha256(AUDIT_SUMMARY),
        PROMPT_PACK.name: sha256(PROMPT_PACK),
    }
    current_semantic_hashes = {
        PREDICTIONS.name: semantic_json_sha256(predictions),
        METRICS.name: semantic_json_sha256(metrics),
    }
    reviewed_artifact_hashes = review_registry.get("reviewed_artifact_hashes", {})
    reviewed_semantic_hashes = review_registry.get("reviewed_semantic_hashes", {})
    roles = review_registry.get("roles", {})

    missing_roles = [role for role in REQUIRED_ROLES if role not in roles]
    non_pass_roles = [
        role for role in REQUIRED_ROLES
        if role in roles and roles[role].get("status") != "PASS"
    ]
    role_ids = [
        roles[role].get("agent_id", "")
        for role in REQUIRED_ROLES
        if role in roles
    ]
    duplicate_role_ids = sorted({
        agent_id for agent_id in role_ids
        if agent_id and role_ids.count(agent_id) > 1
    })
    # The field-level audit validates prediction/metrics semantic hashes, not
    # raw bytes, because platform BLAS/Python differences can change JSON byte
    # representation without changing reviewed values. Keep byte binding for
    # the prompt pack only; prediction/metrics exactness is enforced by
    # ``semantic_binding_valid`` and the audit summary below.
    prebound_artifact_hashes = {
        PROMPT_PACK.name: current_artifact_hashes[PROMPT_PACK.name],
    }
    artifact_binding_valid = all(
        reviewed_artifact_hashes.get(key) == value
        for key, value in prebound_artifact_hashes.items()
    )
    semantic_binding_valid = reviewed_semantic_hashes == current_semantic_hashes
    audit_summary_valid = (
        audit_summary.get("final_status") == "PASS"
        and audit_summary.get("blocked_rows") == 0
        and audit_summary.get("predictions_sha256") == current_artifact_hashes[PREDICTIONS.name]
        and audit_summary.get("metrics_sha256") == current_artifact_hashes[METRICS.name]
    )
    profitability_fail_closed = (
        metrics.get("evaluation_governance", {}).get("recommendation_release_status") == "blocked"
        and metrics.get("evaluation_governance", {}).get("bankroll_release_status")
        == "prohibited_zero_allocation"
        and sum(1 for row in predictions.get("predictions", []) if row.get("recommendation")) == 0
    )
    fixture_count_valid = (
        predictions.get("batch", {}).get("fixture_count")
        == len(predictions.get("predictions", []))
    )

    blockers = []
    if missing_roles:
        blockers.append(f"missing_roles:{','.join(missing_roles)}")
    if non_pass_roles:
        blockers.append(f"non_pass_roles:{','.join(non_pass_roles)}")
    if duplicate_role_ids:
        blockers.append(f"duplicate_role_ids:{','.join(duplicate_role_ids)}")
    if not artifact_binding_valid:
        blockers.append("review_registry_artifact_hash_mismatch")
    if not semantic_binding_valid:
        blockers.append("review_registry_semantic_hash_mismatch")
    if not audit_summary_valid:
        blockers.append("audit_summary_not_bound_to_current_json")
    if not profitability_fail_closed:
        blockers.append("profitability_or_staking_gate_not_fail_closed")
    if not fixture_count_valid:
        blockers.append("prediction_count_mismatch")

    record = {
        "schema_version": "1.0",
        "batch_id": (
            f"{predictions.get('batch', {}).get('start', 'unknown')}_"
            f"{predictions.get('batch', {}).get('end', 'unknown')}"
        ),
        "generated_at": predictions.get("generated_at", ""),
        "git_commit": os.environ.get(
            "GITHUB_SHA",
            review_registry.get("git_commit", "LOCAL_UNCOMMITTED"),
        ),
        "model_version": metrics.get("version", ""),
        "prompt_pack": {
            "path": str(PROMPT_PACK.relative_to(ROOT)),
            "sha256": current_artifact_hashes[PROMPT_PACK.name],
        },
        "review_registry": {
            "path": str(REVIEWS.relative_to(ROOT)),
            "sha256": sha256(REVIEWS),
        },
        "current_artifact_hashes": current_artifact_hashes,
        "current_semantic_hashes": current_semantic_hashes,
        "reviewed_artifact_hashes": reviewed_artifact_hashes,
        "reviewed_semantic_hashes": reviewed_semantic_hashes,
        "roles": {role: roles.get(role, {}) for role in REQUIRED_ROLES},
        "release_checks": {
            "artifact_binding_valid": artifact_binding_valid,
            "artifact_binding_scope": sorted(prebound_artifact_hashes),
            "semantic_binding_valid": semantic_binding_valid,
            "audit_summary_valid": audit_summary_valid,
            "profitability_fail_closed": profitability_fail_closed,
            "fixture_count_valid": fixture_count_valid,
            "duplicate_role_ids": duplicate_role_ids,
        },
        "blockers": blockers,
        "final_status": "PASS" if not blockers else "BLOCKED",
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes); status={record['final_status']}")
    if blockers:
        raise SystemExit(f"Release validation blocked: {blockers}")


if __name__ == "__main__":
    main()
