# Expanded Markets Execution Plan

Objective: extend the June 22–27 release with reproducible total-goals, BTTS, Asian-handicap, number-of-goals, and screenshot-supported combo analysis, and publish exactly one best-available risk-ranked recommendation per fixture without fabricating missing prices or describing a model pick as certain.

## Recommendation-policy amendment — one pick per fixture

- [ ] Audit prior v4/v4.1/v6 Elo, market stack, Dixon-Coles, Bayesian, EWMA, TGNN, GraphMixer, tabular MLP, and ensemble experiments.
- [ ] Research primary literature for score models, calibrated boosted trees, temporal graphs, stacking, and sports outcome prediction.
- [ ] Select model components only through chronological pre-holdout evaluation and untouched-holdout diagnostics.
- [ ] Fix any probability-engine disagreement between displayed common markets and priced-market evaluation.
- [ ] Produce exactly one recommendation for every fixture:
  - executable comparison when a complete screenshot price exists;
  - otherwise a model-side recommendation with a minimum acceptable price/fair-price threshold and `price_unavailable` status.
- [ ] Rank by uncertainty-adjusted utility, not raw EV alone, and publish failure scenarios and risk grade.

Done tests:

1. Exactly 32 unique fixtures each contain exactly one recommendation and no fixture is marked “no action.”
2. Every executable recommendation references a real source image/hash; every unpriced recommendation has no claimed sportsbook EV and clearly states its minimum acceptable price.
3. The chosen production components beat or tie simpler baselines on pre-declared chronological metrics, or are rejected and documented.

## Phase 0 — Scope, evidence, and design

- [ ] Inventory every source market by fixture, app, selection, line, and screenshot hash.
- [ ] Separate “probability available” from “real price available” and “betting policy validated.”
- [ ] Define market-specific outputs, settlement, metrics, uncertainty, and report language.
- [ ] Assign ML methodology, statistical validation, data/provenance, replication, and editor subagents.

Done tests:

1. All 756 odds rows map to one documented market family or an explicit unsupported reason.
2. Fixture/app coverage matrix identifies complete and partial markets with no inferred prices.
3. Every planned report field has a source/model path and a subagent audit owner.

Deliverables:

- Coverage matrix and unsupported-market register.
- This checklist and updated state ledger.
- Market model/test specification.

## Phase 1 — Canonical market dataset and settlement

- [ ] Normalize totals, BTTS, Asian handicap, number-of-goals, double chance, result handicap, and combo selections.
- [ ] Preserve original labels, decimal odds, app, line, screenshot filename, and SHA-256.
- [ ] Implement exact settlement for integer, half, and quarter Asian lines and supported combo conjunctions.
- [ ] Reject ambiguous result handicaps, boosts, player props, and cropped selections unless independently resolved.

Done tests:

1. Every supported normalized row round-trips to the original source row and valid screenshot hash.
2. Exhaustive score-grid unit tests match hand-calculated win/push/half-win/half-loss outcomes.
3. Incomplete or ambiguous markets fail closed and never receive EV/recommendation output.

Deliverables:

- Expanded normalized market CSV.
- Market schema/provenance documentation.
- Settlement unit-test suite.

## Phase 2 — Market probability models and backtesting

- [ ] Establish simple baselines: empirical total-goal distribution and independent Poisson.
- [ ] Test team attack/defense partial pooling, Dixon-Coles/bivariate correction, recency/competition weighting, and calibrated alternatives where sample size permits.
- [ ] Use nested chronological selection and untouched outer holdout.
- [ ] Evaluate totals, BTTS, handicap outcomes, and combo joint probabilities separately.
- [ ] Quantify calibration and uncertainty; do not infer profitability without historical executable prices.

Done tests:

1. Accepted models beat or tie the simplest baseline on untouched proper scoring metrics without leakage.
2. Reliability/calibration diagnostics and bootstrap uncertainty are recorded by market family.
3. Any market family failing sample-size, calibration, or settlement gates is marked descriptive-only.

Deliverables:

- Market-model metrics JSON and documented model card.
- Reproducible backtest outputs.
- Accepted/rejected model comparison table.

## Phase 3 — Predictions, fair odds, EV, and conservative policy

- [ ] Generate per-fixture probabilities and fair odds for common total, BTTS, and handicap lines.
- [ ] Compute screenshot-price EV only where a real supported price exists.
- [ ] Generate supported combo probabilities from the joint score distribution, not multiplied marginal probabilities.
- [ ] Apply uncertainty stress tests, model-market disagreement checks, stale/conditional flags, and abstention-first classification.

Done tests:

1. Probabilities and fair odds are finite, internally consistent, and reconstructable from model outputs.
2. Every EV references an exact source price/hash; fixtures without prices explicitly show “price unavailable.”
3. No actionable tier appears unless an untouched historical-odds policy backtest validates it.

Deliverables:

- Expanded prediction JSON and model dataset columns.
- Market rankings by evidence/risk, explicitly non-actionable when policy is unvalidated.
- Updated leaf-field audit manifest.

## Phase 4 — Independent validation iterations

- [ ] ML methodology audit.
- [ ] Statistical/calibration audit.
- [ ] Data/provenance audit.
- [ ] Two independent clean-code/data replications.
- [ ] Per-fixture/field-family review with manifest linkage.

Done tests:

1. Iteration 1 issues have root causes, fixes, and regression tests.
2. Iteration 2 reproduces all expanded JSON/metrics leaves and source hashes.
3. Manifest contains distinct passing owner, two replicators, and editor for every published leaf.

Deliverables:

- Audit registry/evidence.
- Validation record with both iterations.
- Zero-blocked datapoint manifest.

## Phase 5 — Bilingual report and editor audit

- [ ] Add totals, BTTS, handicaps, number-of-goals, and supported combos to each match card.
- [ ] Clearly distinguish model probability, fair price, screenshot price, EV, uncertainty, and policy status.
- [ ] Extend workflow visualization with score model, calibration, settlement, joint-event combos, and audit gates.
- [ ] Translate all visible English/Spanish text and add novice tooltips.
- [ ] Run the required editor/UIUX subagent.

Done tests:

1. DOM values match expanded JSON and manifest pointers for every displayed field.
2. English/Spanish, filters, accessibility, responsive layout, and error states pass browser tests.
3. Editor reports no misleading recommendation language, stale field, missing match, or visualization mismatch.

Deliverables:

- Updated JSON-driven Tailwind report.
- Expanded workflow visualization.
- Editor PASS evidence.

## Phase 6 — Full testing and adversarial checks

- [ ] Run unit tests for formulas/settlement/calibration.
- [ ] Run integration tests for pipeline → manifest → report → site.
- [ ] Run corruption, missing-price, stale-data, incomplete-market, and extreme-input tests.
- [ ] Run local HTTP Playwright/translation/black-box parity tests.

Done tests:

1. Full local suite has zero failures; live-only test may skip before deployment.
2. Every adversarial input fails safely with an explicit diagnostic.
3. Clean deterministic rebuild produces no unexplained generated differences.

Deliverables:

- Test logs and validation summary.
- Corrected artifacts after all failures.

## Phase 7 — GitHub deployment and live validation

- [ ] Stage only in-scope changes and preserve unrelated user files.
- [ ] Push one reviewed commit to trigger the single-tested-artifact Pages workflow.
- [ ] Monitor the exact run with `gh run watch --exit-status`.
- [ ] Validate live SHA, JSON/DOM parity, manifest hash, translations, and expanded-market cards.

Done tests:

1. Build-test, deploy, and validate-deployed jobs all pass for the exact release SHA.
2. Live HTML commit/audit hashes match the release artifacts.
3. Live browser checks confirm all 32 cards and supported market sections with no stale/extra fixtures.

Deliverables:

- Release SHA, Actions run URL, and live URL.
- Final state/validation record.

## Overall success conditions

1. All 32 fixtures have reproducible common-market probabilities; EV is shown only for real sourced prices.
2. Market-specific validation and uncertainty are honest, leakage-safe, and independently reproduced.
3. The bilingual live report, audit manifest, CI, and exact deployment all pass.
