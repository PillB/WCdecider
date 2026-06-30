---
name: wcdecider-manual-update-release
description: Safely update WCdecider from newly entered manual Betano/Betsson odds CSVs and provenance sidecars. Use when a task mentions manual_odds_*.csv, manual odds input, updated match betting markets, rebuilding the WCdecider report/site, validating predictions/metrics/audits, avoiding hallucinated data, or deploying a new WCdecider release.
---

# WCdecider Manual Update Release

## Core rule

Treat the release as fail-closed. Never invent odds, results, injuries, news,
sources, probabilities, hashes, reviewer evidence, or deployment status. If a
required artifact or source is missing, block and report the exact dependency.

## Required workflow

1. Read `AGENT_STATE.md`, then read the current project docs only as needed:
   `AGENT.md`, `WCDECIDER_SYSTEM_DESIGN.md`, `PROJECT_UNDERSTANDING.md`,
   `FUTURE_UPDATE_PROTOCOL.md`, and `STORM_LOOP_ENGINEERING_PROTOCOL.md`.
2. Inspect the active manual odds CSV and matching `.provenance.json`.
   Validate schema, row count, source hash, capture timestamps, fixture
   coverage, app labels, market IDs, canonical selections, lines, promo flags,
   and source images before trusting any row.
3. Regenerate only from sourced artifacts. Prefer the current CI order from
   `.github/workflows/deploy.yml`; do not hand-edit generated JSON/HTML except
   to fix source generators and rerun them.
4. Validate with distinct STORM roles: data lineage, clean-room replication,
   ML/stat methodology, profitability/staking, report/UI editor, deployment
   reliability, and moderator. A non-PASS role blocks release.
5. Generate datapoint audit and role-level release validation. `blocked_rows`
   must be zero. Prediction/metrics JSON should be reviewed by semantic hash
   when platform byte drift is expected; prompt packs and static review inputs
   remain byte-bound.
6. Run local gates before deploy:
   - focused pipeline/build tests;
   - Playwright/report tests with localhost permission when needed;
   - full suite when the change touches release logic, generated artifacts, or
     UI behavior.
7. Deploy only after local gates pass, then monitor GitHub Actions and validate
   the live GitHub Pages JSON/DOM parity. Record final status in `AGENT_STATE.md`.

## Use bundled resources

- Read `references/update-protocol.md` for the exact command sequence and
  promotion/deploy checklist.
- Read `references/validation-guardrails.md` before changing odds, predictions,
  recommendations, staking, audit hashes, or user-facing betting copy.
- Read `references/subagent-roles.md` when creating or evaluating review agents.
- Run `scripts/release_preflight.py --repo <repo>` before committing.
- Run `scripts/print_artifact_hashes.py --repo <repo>` when rebinding review
  registries or diagnosing CI drift.

## Release language constraints

Use “audit comparison”, “source row”, “hypothetical simulation”, and
“authorized stake S/0” unless the profitability promotion gate explicitly
passes. Avoid “surefire”, “guaranteed profit”, “go place this bet”, and
imperative app-navigation copy.
