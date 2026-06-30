#!/usr/bin/env python3
"""Print WCdecider release artifact byte and semantic hashes.

This helper is read-only. It is intended for diagnosing review-registry drift
and CI/local platform differences.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_JSON = (
    "wc_june22_27_predictions.json",
    "wc_june22_27_model_metrics.json",
    "wc_june22_27_datapoint_audit_summary.json",
    "governance/release_validation_june22_27.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, list):
        return [normalize_floats(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_floats(value[key]) for key in sorted(value)}
    return value


def semantic_json_sha256(value: Any) -> str:
    payload = json.dumps(
        normalize_floats(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def project_semantic_hash(root: Path, value: Any) -> str:
    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        sys.path.insert(0, str(scripts_dir))
        try:
            from generate_datapoint_audit import semantic_json_sha256 as project_hash

            return project_hash(value)
        except Exception:
            pass
        finally:
            try:
                sys.path.remove(str(scripts_dir))
            except ValueError:
                pass
    return semantic_json_sha256(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="WCdecider repo root")
    parser.add_argument("paths", nargs="*", help="Artifact paths relative to repo")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    for rel in args.paths or DEFAULT_JSON:
        path = root / rel
        if not path.exists():
            print(f"{rel}\tMISSING")
            continue
        print(f"{rel}\tbytes\t{sha256(path)}")
        if path.suffix == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
            print(f"{rel}\tsemantic\t{project_semantic_hash(root, value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
