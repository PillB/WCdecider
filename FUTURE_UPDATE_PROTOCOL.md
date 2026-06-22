# Future Update Protocol

Version: 2.0 (2026-06-22)

This is the release checklist for every new WCdecider match batch. Replace `<batch>` with the active date range, and derive filenames from the canonical fixture file rather than hard-coding a previous release.

## Immutable rules

- Use only traceable source values. Never infer cropped odds or embed live prices in Python/HTML.
- Keep one canonical fixture CSV, one normalized odds CSV, one model dataset, one prediction JSON, one provenance file, and one screenshot manifest per batch.
- Use elapsed matches only after their final results are verified. Keep chronological selection and untouched holdout windows.
- The HTML report reads prediction JSON; current match cards and numbers are not hand-authored.
- No betting tier is actionable unless a separately validated betting-policy backtest supports it. Otherwise publish `PASS` or investigative `HALT`.
- A failed gate blocks release until the root cause is fixed and all affected gates are repeated.

## Phase 0 — Read state and define scope

- [ ] Read `AGENT_STATE.md`, `WCDECIDER_SYSTEM_DESIGN.md`, `PROJECT_UNDERSTANDING.md`, `ARCHITECTURE.md`, and this protocol.
- [ ] Create the canonical `<batch>_matches.csv` with stable fixture IDs and timezone-aware kickoffs.
- [ ] Record the source cutoff and separate elapsed matches from future matches.

Done tests:

1. Fixture IDs, teams, and kickoff timestamps are unique and non-empty.
2. The batch contains no already-completed fixture presented as a future prediction.
3. `AGENT_STATE.md` names the exact active task, next dependency, and immutable constraints.
4. The update is consistent with every applicable contract in `WCDECIDER_SYSTEM_DESIGN.md`.

## Phase 1 — Screenshot inventory and odds

- [ ] Hash every current screenshot and record filename, app, fixture, and review status.
- [ ] Transcribe only visible values into date-owned source CSVs.
- [ ] Normalize supported markets into one `<batch>_odds.csv`, preserving source image and source row.

Done tests:

1. Manifest row count equals the number of source screenshots and every hash matches its file.
2. Every published odd has a real source image and decimal price.
3. Every modeled fixture has at least one complete same-app A/D/B full-time market.

## Phase 2 — Dataset and provenance

- [ ] Verify elapsed results and update historical ratings chronologically.
- [ ] Build explicit Dataset A (World Cup finals) and Dataset B (supplementary qualifier/friendly data).
- [ ] Export the model dataset and provenance with formulas, source URLs, timestamps, transformations, and hashes.

Done tests:

1. Every externally sourced field has a direct source and retrieval timestamp.
2. Dataset A/B membership follows documented competition rules with no overlap.
3. A clean rebuild reproduces all dataset hashes and row counts.

## Phase 3 — Model selection and output generation

- [ ] Select model parameters only on chronological pre-holdout windows.
- [ ] Evaluate the untouched holdout and record Brier score, log loss, and calibration diagnostics.
- [ ] Generate probabilities, market comparison, stress values, `PASS`/`HALT`, and prediction JSON.

Done tests:

1. Each fixture has finite A/D/B probabilities summing to one within tolerance.
2. Selection rows and holdout rows are disjoint and ordered in time.
3. Re-running the pipeline produces byte-identical JSON and metrics.

## Phase 4 — Independent replication iteration 1

- [ ] Assign data replication, code replication, and model-audit agents.
- [ ] Assign every fixture to an independent row-level audit.
- [ ] Log each discrepancy, root cause, and exact fix in the validation record and state ledger.

Done tests:

1. Data agents reconstruct all canonical rows from delivered inputs and provenance.
2. Code agents rebuild every generated artifact without hidden inputs.
3. Model agents find no unaddressed critical/high issue; otherwise the phase fails.

## Phase 5 — Fixes and independent replication iteration 2

- [ ] Apply fixes without weakening fail-closed checks.
- [ ] Regenerate every affected artifact.
- [ ] Repeat data, code, model, and per-fixture audits.

Done tests:

1. Every iteration-one issue has a documented resolution and regression test.
2. All fixture agents match published JSON probabilities, odds, EV, stress, and class.
3. Final independent release audit reports no blocking issue.

## Phase 6 — JSON-driven bilingual report

Before report generation:

- [ ] Expand prediction and metrics JSON into canonical leaf paths.
- [ ] Assign distinct owner, replication-1, replication-2, and editor agents using the versioned mandatory mission.
- [ ] Generate the datapoint audit manifest and block on any missing/non-PASS row.

Governance done tests:

1. Manifest paths equal all prediction and metrics JSON leaves exactly.
2. Every row has source/model/mission hashes and four distinct passing agent IDs.
3. Conditional status and editor evidence are present for every fixture field.

- [ ] Generate one `bg-slate-900` card per canonical fixture from JSON.
- [ ] Translate every visible label, explanation, button, error, tooltip, and ELI5 instruction.
- [ ] Render data sources, model workflow, uncertainty, conditional status, and responsible-gambling text.

Done tests:

1. DOM fixture IDs equal canonical fixture IDs exactly—no missing, duplicate, or extra cards.
2. Displayed probabilities, odds, EV, and class match JSON within explicit display tolerance.
3. English/Spanish toggles, tooltips, filters, error states, and layouts pass browser tests.

## Phase 7 — Unit, integration, black-box, and adversarial tests

- [ ] Run schema, formulas, classification, determinism, hash, and corruption tests.
- [ ] Run end-to-end pipeline → report → site build tests.
- [ ] Run local HTTP Playwright and translation tests.

Done tests:

1. Missing odds, incomplete A/D/B, invalid probabilities, or bad provenance fail clearly.
2. The full local test suite has zero failures; external-only tests may skip only with an explicit reason.
3. A clean rebuild has no unstaged generated differences except expected commit metadata.

## Phase 8 — Documentation and release

- [ ] Update README, architecture, project understanding, validation record, and state ledger.
- [ ] Stage only reviewed in-scope files in a mixed worktree.
- [ ] Commit and push the release branch that triggers GitHub Actions/Pages.

Done tests:

1. Staged files contain no unrelated user changes or stale batch references in current-production paths.
2. The release commit contains all required inputs, generated artifacts, tests, and CI configuration.
3. The remote branch points to the exact local release commit.

## Phase 9 — CI and live validation

- [ ] Require GitHub Actions pipeline, tests, build, and deployment jobs to pass.
- [ ] Poll the live report for the exact commit marker.
- [ ] Run live JSON/DOM parity and bilingual browser checks.

Done tests:

1. All required GitHub checks pass for the release SHA.
2. Live commit marker and artifact hashes equal the release commit outputs.
3. Live fixture count, content, translations, and visual checks pass with no stale matches.

## Failure record template

For every failure record:

`Step ID | command/check | observed failure | root cause | fix | repeated gates | final status`
