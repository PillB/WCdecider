# WCdecider Release Requirements

Version: 2026-06-22

This document defines testable production requirements. `AGENT.md` defines behavior; `FUTURE_UPDATE_PROTOCOL.md` defines execution order.

## R1 — Sources and fixtures

- R1.1: Canonical fixtures have stable IDs and timezone-aware kickoffs.
- R1.2: Every external fact has a direct URL, access time, and transformation note.
- R1.3: Every screenshot is inventoried with SHA-256, app, fixture, and review status.
- R1.4: Every published odd references a real screenshot and visible decimal price.
- R1.5: Any incomplete required same-app A/D/B market blocks that fixture.

## R2 — Dataset and model

- R2.1: Dataset A contains World Cup finals; Dataset B contains supplementary qualifiers/friendlies.
- R2.2: Elapsed results are verified and incorporated chronologically with Elo K=60.
- R2.3: Parameter/model selection uses only pre-holdout chronological windows.
- R2.4: Final holdout remains untouched until evaluation.
- R2.5: Report Brier, log loss, sample sizes, calibration parameters, and simple baselines.
- R2.6: Rank one is the single backward-compatible `BEST_AVAILABLE`
  recommendation; up to three additional economically distinct sourced
  alternatives may be published from settlement-validated 1X2, totals, BTTS,
  double-chance, Asian-handicap, or supported combo markets.
- R2.7: Score-model outputs may drive rankings, but profitability remains explicitly unvalidated without historical executable prices.
- R2.8: No production ensemble/stack may be claimed unless weights are selected out-of-fold and beat simpler baselines on untouched data.
- R2.9: No profitability, ROI, CLV, or staking tier may be claimed without timestamped historical odds and untouched policy evaluation after vig and selection effects.
- R2.10: Historical prices must carry an evidence class. Only complete named-bookmaker quotes with source and update timestamps strictly before kickoff are primary-validation eligible.
- R2.11: Model championships use nested rolling-origin selection and an untouched final holdout; ROI cannot select the champion.
- R2.12: High-capacity graph/neural candidates require adequate effective sample size and must beat simple baselines securely before production use.
- R2.13: Temporal GNN, graph-mixer, dynamic graph attention, and sequence-transformer candidates require a published promotion gate before production use: at least 2,000 timestamped fixtures, enough repeated temporal edges per team, strictly pre-event features, nested walk-forward selection, untouched holdout superiority, calibration evidence, and closing-line validation before profitability claims.

## R3 — Safety and classification

- R3.1: Every fixture has one `BEST_AVAILABLE` decision plus a `PASS` or investigative `HALT` diagnostic.
- R3.2: `BEST_AVAILABLE` is a comparative recommendation, not a guarantee; cards must show risk grade, stress case, source price, and profitability-validation status.
- R3.3: No “surefire,” “certain,” or “easy multiplier” claim is permitted.
- R3.4: A low-odds candidate must be rejected unless its conservative lower probability bound exceeds vig-adjusted break-even.
- R3.5: Conditional forecasts visibly require rerunning after intervening matches or material lineup/odds changes.
- R3.6: Confidence is capped at 70% and described as model evidence, not outcome certainty.
- R3.7: Publish up to four economically distinct sourced recommendations per fixture. Preserve rank one as `BEST_AVAILABLE`; disclose rather than fabricate any rank shortfall.
- R3.8: Equivalent market/selection/line events across screenshots or apps cannot occupy multiple top-four ranks.

## R4 — Datapoint subagent governance

- R4.1: Every prediction and metrics JSON leaf appears in `wc_june22_27_datapoint_audit.csv`.
- R4.2: Every manifest row records value/source/model/mission hashes and freshness status.
- R4.3: Every row has distinct owner, replication-1, replication-2, and editor subagent IDs.
- R4.4: Every role receives `governance/subagent_mission_v1.md`.
- R4.5: Every role status is `PASS`; any missing/non-PASS result blocks report build and deployment.
- R4.6: Review evidence identifies commands/artifacts checked and discrepancies found.

## R5 — Report

- R5.1: Exactly one JSON-driven `bg-slate-900` card exists per canonical fixture.
- R5.2: All visible application text, errors, diagrams, filters, and explanations switch English/Spanish.
- R5.3: Displayed values match JSON within explicit display tolerance.
- R5.4: The report shows one rank-one `BEST_AVAILABLE` recommendation plus up
  to three sourced alternatives per fixture and clearly distinguishes every
  rank from validated profitability or certainty.
- R5.5: Cards show current/conditional freshness and audit status.
- R5.6: Report shows holdout metrics, sample size, baselines, and profitability limitations.
- R5.7: Workflow visualization represents only implemented/validated model components.
- R5.8: Tooltips and ELI5 text explain PASS, HALT, EV, stress, calibration, and uncertainty.
- R5.9: Cards display ranked alternatives with app, market, line, source price, fair threshold, decision/stress EV, utility, risk, source, and profitability status.
- R5.10: The mobile report shell must be safe before JSON loads: show a loading state, disable filters, prevent card rendering until the prediction/metrics/audit bundle verifies, and show a bilingual visible error rather than crash or blank page on fetch/audit failure.
- R5.11: The report footer displays last updated, model/report version, and exact build SHA marker.

## R6 — Pipeline and reproducibility

- R6.1: Pipeline contains no current hard-coded odds or prose-derived targets.
- R6.2: Rebuilds from the same inputs are byte-identical except explicit commit metadata.
- R6.3: CSV output uses LF line endings and deterministic ordering.
- R6.4: Provenance hashes match source and generated artifacts.
- R6.5: Missing inputs, invalid probabilities, incomplete markets, or failed audits stop execution clearly.
- R6.6: Python code contains docstrings, examples, formulas, and design rationale.

## R7 — CI and deployment

- R7.1: CI order is pipeline → report → audit manifest → site build → full tests.
- R7.2: CI starts without relying on a pre-existing `site/`.
- R7.3: Browser tests run against the exact site artifact later uploaded.
- R7.4: Required dependency versions are bounded/pinned and Python is fixed by workflow.
- R7.5: GitHub Pages embeds the exact release SHA.
- R7.6: Live validation verifies SHA, artifact parity, 32 cards, bilingual toggle, footer freshness/version, mobile-safe JSON loading behavior, and no stale fixtures.

## Release gates

1. All source/data/model tests pass.
2. Two independent replication audits pass.
3. Final editor audit passes.
4. Datapoint manifest has complete leaf coverage and zero blocked rows.
5. Full local and GitHub Actions suites pass.
6. Exact live release SHA passes black-box validation.
