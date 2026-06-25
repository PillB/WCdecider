# WCdecider Project Understanding

All material updates must follow `STORM_LOOP_ENGINEERING_PROTOCOL.md`: STORM
for multi-perspective source-grounded research synthesis, and bounded loop
engineering for reproduce–measure–review–repair–test–retrospect execution.

**Last grounded:** 2026-06-23

**Active prediction batch:** FIFA World Cup matches from 2026-06-22 through 2026-06-27
**Repository:** flat, file-based Python + static HTML deployed to GitHub Pages

`WCDECIDER_SYSTEM_DESIGN.md` is the mandatory cross-cutting contract for data,
modeling, recommendations, bankroll simulation, UI behavior, governance, tests,
and deployment.

## Current Source-of-Truth Direction

The project is being consolidated around these canonical artifacts:

1. `wc_2026_matches_june_22-27.csv` — fixture identity and timezone-aware kickoff data.
2. `Screenshots/*.PNG` — immutable Betano/Betsson source evidence.
3. `wc_odds_june_22-27.csv` — normalized odds transcribed from screenshots; no live odds belong in Python.
4. Dataset A — historical World Cup/results/odds/features used for chronological training and backtesting.
5. Dataset B — supplementary training/validation data whose role must be explicit and leakage-safe.
6. `wc_june22_27_model_dataset.csv` plus provenance — current fixture features and direct source URLs.
7. A deterministic Python pipeline — data validation, feature engineering, model execution, calibration, ensemble, EV, and JSON export.
8. `wc_june22_27_predictions.json` — sole current-batch source for the website.
9. `index.html` — batch-independent Tailwind shell that renders one card per JSON fixture.
10. `site/` — generated deployment artifact; never the primary source.

## Implemented Repository Areas

- `.github/workflows/deploy.yml`: GitHub Pages test/build/deploy workflow.
- `Screenshots/`: betting-app screenshots. The current 216-image replacement set is user-owned input.
- `archived/`: old report snapshots, not current truth.
- `playwright validations/`: visual evidence from earlier deployments.
- `scripts/`: build, deploy, and deployed-site validation helpers.
- `tests/`: model, pipeline, translation, report, and deployment tests.
- `training/`: model weights, temporal/graph experiments, metrics, and review reports.
- Root `wc_*.py/csv/json/txt`: current and historical modeling artifacts.
- `index.html`: current report source.
- `site/`: generated GitHub Pages bundle.

## Current UI/Model Architecture Additions

- Research mode is a gated shadow view. It now publishes its own ranked
  sourced recommendations using the Dixon-Coles score grid against the same
  Betano/Betsson screenshot odds, but it remains non-production and cannot
  overwrite the production `recommendation` field or bankroll simulation.
- The report includes five risk-aversion lenses: exploratory, balanced,
  cautious, strict, and audit-only. These are transparent PASS/HALT review
  thresholds over the same sourced recommendations; they do not change saved
  model probabilities, source odds, or historical-profitability status. An
  underlying anomaly `HALT` cannot be overridden by any lens; `PASS` means only
  that the candidate cleared the declared diagnostic thresholds, not that the
  bet is robust or profitable.
- The browser loads `wc_june22_27_datapoint_audit_summary.json` for hash and
  leaf-path verification. The full audit CSV remains a reproducibility artifact
  and build gate, not a mobile startup dependency.
- Research mode swaps the production workflow diagram for a separate
  dashed-violet challenger diagram and swaps production proper-score panels for
  Dixon-Coles point estimates, paired-bootstrap intervals, chronological fold
  evidence, and the unchanged profitability limitation.
- The historical-odds subsystem builds a redistribution-safe public corpus of
  142,349 Football-Data closing-column rows over 8,908 events. Restricted Odds
  API samples stay under ignored `private_data/`; they are validation fixtures,
  not public dataset rows.

## Known Integrity Problems Being Removed

- Hard-coded current odds in Python.
- Silent fallback when optional neural-model weights are unavailable.
- “Replication” based on extracting target values from prose instead of recomputation.
- Multiple competing canonical datasets and stale fixtures such as England vs Bolivia.
- Dynamic JSON cards coexisting with duplicate static match cards.
- Incomplete bilingual dynamic fields and weak translation allowlists.
- CI that runs only part of the suite or accepts stale live content.
- `ARCHITECTURE.md` describing modules that do not exist.

## Model and Validation Principles

- Predictions are probabilities, not certainties.
- Current odds are compared only after base probabilities are generated.
- Training/model selection uses chronological folds and an untouched temporal holdout.
- Calibration is fitted inside training folds.
- Candidate models are compared with log loss, multiclass Brier/RPS, calibration, sharpness, closing-line value when available, simulated net return after vig, drawdown, and trap counts.
- Market-derived features are separated from pure team-strength features to prevent circular claims.
- All randomness uses recorded seeds; all serialized weights are required and hashed.

## Update Procedure

Every update follows:

1. Read `AGENT_STATE.md` and `WCDECIDER_SYSTEM_DESIGN.md`.
2. Inventory screenshots and fixtures.
3. Build canonical odds/data/provenance.
4. Update historical outcomes and retrain with temporal validation.
5. Freeze and execute the selected model.
6. Export JSON and render the site.
7. Run independent data/code/model/fixture audits twice.
8. Run all tests and red-team checks.
9. Build, publish, monitor CI, and validate the exact commit live.
10. Compress the verified status back into `AGENT_STATE.md`.

## Safety Rules

- Do not fabricate or infer cropped odds.
- Do not modify or discard unrelated dirty-worktree changes.
- Do not publish current-batch numbers outside the canonical JSON.
- Missing evidence or weights must fail closed.
- Confidence is capped at 70%; every recommendation states failure modes.
- Betting language remains analysis-only and includes responsible-gambling guidance.
