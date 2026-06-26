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
- R2.6: Rank one is a comparison only. It becomes `ACTIONABLE` only when every
  authorization gate passes; otherwise it is `ABSTAIN`.
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
- R2.14: Historical odds ingestion preserves immutable raw files and hashes,
  named bookmaker, source URL, retrieval time, market/line/selection contract,
  and evidence class. Published closing columns without quote times remain
  secondary evidence.
- R2.15: A timestamped fixed-odds snapshot is primary closing evidence only
  when complete, strictly before kickoff, and no more than 120 minutes before
  kickoff. Older snapshots remain pre-event observations.
- R2.16: Research mode may expose a selected tested gated shadow model, but it
  must be off by default, clearly labeled non-production, unable to mutate
  production recommendations or staking outputs, and must not imply that
  untested registered candidates were beaten.
- R2.17: Recommendation/model promotion requires cross-fitted outer OOF
  predictions, calibration fitted only on inner OOF predictions, a
  price-independent constrained stack, complete candidate/search ledgers,
  date-block uncertainty, family-wise multiplicity control, and confirmation
  on a newly sealed prospective cohort.
- R2.18: Empirical calibration is research-only below 300 OOF predictions, 75
  observations per outcome class, 40 date blocks, and four outer folds with at
  least 40 rows each. Identity calibration remains the production default
  unless calibrated probabilities are non-inferior on proper scores and
  reliability in sealed evidence.
- R2.19: A sealed prospective registry is immutable. Build and evaluation code
  verifies its prediction, protocol, model, data, policy, fixture-manifest, and
  source-commit hashes but never rewrites the sealed file.
- R2.20: Profitability promotion consumes a dedicated hash-bound eligible-bet
  ledger derived from the canonical closing-odds corpus. Aggregate public proxy
  coverage cannot authorize ROI, CLV, recommendations, or staking.
- R2.21: A user-controlled educational stake simulator may operate while
  production authorization is blocked, but it must remain a separate JSON
  object, label every amount hypothetical, evaluate only current-snapshot
  future fixtures, explicitly flag any forced-coverage HALT/negative-EV/
  negative-stress/below-fair row, preserve `recommendation=null` and authorized
  stake `S/0.00`, and never describe simulated arithmetic as validated profit.
- R2.22: Forward allocation uses S/100 independently per app, one sourced
  single per current match when that app has transcribed prices, a 20% absolute
  single cap with 15% balanced default, and an accumulator capped at 5% in the
  balanced profile. Missing app prices reserve the full S/100 and request data.

## R3 — Safety and classification

- R3.1: Every fixture has an explicit `ACTIONABLE` or `ABSTAIN` decision plus
  independent `PASS`/`HALT` anomaly diagnostics.
- R3.2: `BEST_AVAILABLE` is a comparative recommendation, not a guarantee; cards must show risk grade, stress case, source price, and profitability-validation status.
- R3.3: No “surefire,” “certain,” or “easy multiplier” claim is permitted.
- R3.4: A low-odds candidate must be rejected unless its conservative lower probability bound exceeds vig-adjusted break-even.
- R3.5: Conditional forecasts visibly require rerunning after intervening matches or material lineup/odds changes.
- R3.6: Confidence is capped at 70% and described as model evidence, not outcome certainty.
- R3.7: Publish up to four economically distinct sourced comparisons per
  fixture; disclose rather than fabricate any rank shortfall.
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
- R5.4: The report shows one rank-one comparison plus up
  to three sourced alternatives per fixture and clearly distinguishes every
  rank from validated profitability or certainty.
- R5.5: Cards show current/conditional freshness and audit status.
- R5.6: Report shows holdout metrics, sample size, baselines, and profitability limitations.
- R5.7: Workflow visualization represents only implemented/validated model components.
- R5.8: Tooltips and ELI5 text explain PASS, HALT, EV, stress, calibration, and uncertainty.
- R5.9: Cards display ranked alternatives with app, market, line, source price, fair threshold, decision/stress EV, utility, risk, source, and profitability status.
- R5.10: The mobile report shell must be safe before JSON loads: show a loading state, disable filters, prevent card rendering until the prediction/metrics/lightweight-audit-summary bundle verifies, and show a bilingual visible error plus diagnostics rather than crash or blank page on fetch/audit failure.
- R5.10a: The browser must not fetch or parse `wc_june22_27_datapoint_audit.csv`; it verifies `wc_june22_27_datapoint_audit_summary.json` hashes and leaf-path counts while the full CSV remains a build/reproducibility artifact.
- R5.11: The report footer displays last updated, model/report version, and exact build SHA marker.
- R5.12: The report includes a bilingual research-mode toggle when research-mode JSON is available; toggling reveals shadow-model probabilities/deltas, promotion-gate reasons, and shadow ranked recommendations without changing production recommendation fields.
- R5.13: The report includes 3–5 bilingual risk-aversion levels; changing the level updates visible PASS/HALT lens diagnostics but must not mutate saved probabilities, source odds, production rank one, or bankroll simulation.
- R5.14: Every risk lens enforces its published divergence, stressed-EV, risk-grade, and applicable fair-price thresholds; no lens may override an underlying anomaly `HALT`, and `PASS` must be described as a diagnostic rather than robustness or profitability.
- R5.15: HALT review compares identical sourced candidates across production and research models; aggregate or unpaired top-four counts cannot be described as model improvement.
- R5.16: The current page layout is a regression-tested user journey:
  hero summary and model evidence → performance/profitability visuals →
  filters/risk/budget controls → defensive loading shell → bankroll plan →
  top-two match summary table → exactly 32 match cards → footer
  freshness/version/build marker. The top summary must contain one row per
  fixture, link to the matching card anchor, preserve the production/research
  workflow toggle state, and keep all 32 cards rendered as `bg-slate-900`
  fixture cards.

## R6 — Pipeline and reproducibility

- R6.1: Pipeline contains no current hard-coded odds or prose-derived targets.
- R6.2: Rebuilds from the same inputs are byte-identical except explicit commit metadata.
- R6.3: CSV output uses LF line endings and deterministic ordering.
- R6.4: Provenance hashes match source and generated artifacts.
- R6.5: Missing inputs, invalid probabilities, incomplete markets, or failed audits stop execution clearly.
- R6.6: Python code contains docstrings, examples, formulas, and design rationale.

## R7 — CI and deployment

- R7.1: CI order is canonical historical odds → model championship →
  prediction pipeline → merged metrics → audit manifest → report → site build
  → full tests.
- R7.2: CI starts without relying on a pre-existing `site/`.
- R7.3: Browser tests run against the exact site artifact later uploaded.
- R7.4: Required dependency versions are bounded/pinned and Python is fixed by workflow.
- R7.5: GitHub Pages embeds the exact release SHA.
- R7.6: Live validation verifies SHA, artifact parity, 32 cards, bilingual toggle, footer freshness/version, mobile-safe JSON loading behavior, and no stale fixtures.
- R7.7: Live/mobile validation confirms no network request is made for the full audit CSV and that missing-artifact failures expose the diagnostics panel.

## Release gates

1. All source/data/model tests pass.
2. Two independent replication audits pass.
3. Final editor audit passes.
4. Datapoint manifest has complete leaf coverage and zero blocked rows.
5. Full local and GitHub Actions suites pass.
6. Exact live release SHA passes black-box validation.
