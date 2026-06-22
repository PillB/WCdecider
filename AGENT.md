# WCdecider Agent Protocol

Version: 2026-06-22

This file is the binding operating contract for every data, model, recommendation, report, and deployment update.

## 1. Non-negotiable principles

- Never fabricate results, odds, injuries, lineups, probabilities, sources, or audit success.
- Live odds must come from a supplied screenshot or another explicitly recorded source with timestamp and hash.
- Every external fact requires a direct URL, access time, and documented transformation.
- Model selection is chronological. The untouched holdout is not used for parameter or policy selection.
- A positive point-estimate EV is not automatically actionable.
- Football bets are never “surefire.” A price near 1.10 still has loss risk, model risk, void/settlement risk, and market-vig risk.
- Do not publish `STRONG`, `MODERATE`, or `SPECULATIVE` tiers unless a separate out-of-sample betting-policy validation supports them. The current safe classes are:
  - `PASS`: no actionable recommendation.
  - `HALT`: apparent edge is extreme or conflicts with the market and requires investigation; it is not a bet recommendation.
- Current match cards and all displayed numbers are generated from JSON, never hand-authored.
- Every published datapoint must have subagent audit ownership recorded in the datapoint audit manifest.
- The user makes all staking decisions. Analysis must contain uncertainty and responsible-gambling language.

## 2. Mandatory READ → ACT → WRITE cycle

For every phase:

1. Read `AGENT_STATE.md`.
2. Execute only the active sub-task.
3. Immediately update `AGENT_STATE.md` with the action, evidence, result, and next step.

No gate is complete without command output, artifact evidence, or an independent review result.

## 3. Mandatory subagent mission

Every subagent that creates or validates a published model datapoint receives this mission, scoped to its assigned fixtures/fields:

> Introspect and retrospect the model and completed-match backtests. Evaluate whether additional data, algorithms, calibration methods, ensembles, robustness checks, or profitability tests could materially improve the analysis. Use current, real, cited data only. Never claim a bet is certain; test any low-odds “near-certain” hypothesis against empirical frequency, calibration, vig, and downside. Execute the documented pipeline, reproduce assigned outputs from delivered files, identify discrepancies, and review the bilingual JSON-driven report for exact synchronization, clarity, UI/UX, and workflow-visualization correctness. Report PASS/FAIL, evidence, root cause, and required fixes.

Each fixture must have three independent audit roles:

1. Research/model auditor.
2. Code/data replication auditor.
3. Report/editor auditor.

One agent may cover multiple fields for one fixture, but the manifest must enumerate every published field and link it to the responsible audit results. Aggregate “looks good” approval is insufficient.

## 4. Datapoint audit manifest

The pipeline must generate `wc_datapoint_audit_<batch>.csv`. One row represents one published scalar or text field.

Required columns:

- `fixture_id`
- `json_path`
- `value_sha256`
- `source_artifact`
- `source_artifact_sha256`
- `model_version`
- `pipeline_sha256`
- `research_agent_id`
- `research_mission`
- `research_status`
- `replication_agent_id`
- `replication_status`
- `editor_agent_id`
- `editor_status`
- `reviewed_at`
- `notes`

Release gates:

1. The manifest covers every leaf field under every prediction record.
2. Every row has source/model hashes and non-empty role ownership.
3. All statuses are `PASS`; otherwise report generation or deployment fails.

## 5. Data intake and provenance

For each batch:

1. Define one canonical fixture CSV with stable IDs and timezone-aware kickoffs.
2. Hash and inventory every screenshot.
3. Transcribe visible values verbatim; never infer cropped values.
4. Normalize only documented market aliases.
5. Require at least one complete same-app A/D/B full-time market for any 1X2 comparison.
6. Verify elapsed results before incorporating them.
7. Maintain:
   - Dataset A: World Cup finals.
   - Dataset B: supplementary qualifiers/friendlies.
8. Save source URLs, retrieval timestamps, formulas, transformations, and artifact hashes in provenance.

## 6. Model research and backtesting

Every update must consider, test where feasible, and document rejection/acceptance of:

- Elo/logistic three-way baselines.
- Market-implied de-vigged probabilities.
- Multinomial logistic or calibrated tree baselines when sample size supports them.
- Poisson/Dixon-Coles score models for descriptive score distributions.
- Hierarchical or partial-pooling team-strength models.
- Calibration methods: Platt, isotonic, beta/Dirichlet calibration where data suffices.
- Ensembles/stacking selected on chronological validation only.
- Recency decay, competition weighting, travel/rest/venue/weather features.
- Closing-line comparison and policy-level profitability with realistic vig.
- Robustness to missing lineups, stale odds, parameter perturbation, and regime shift.

Rules:

- Complexity must beat a simpler baseline on untouched data and calibration, not only training fit.
- Hyperparameters and ensemble weights are selected before the final holdout.
- Report Brier score, log loss, calibration, sample size, and confidence intervals.
- Do not use a market family for recommendations until its settlement and policy are independently validated.

## 7. “Near-certain” and low-odds analysis

For any proposed short-priced bet:

1. Convert odds to implied probability and remove vig using the complete market.
2. Compare model probability with empirical calibrated frequency and uncertainty bounds.
3. Stress injuries, rotation, red cards, penalties, weather, and stale-price scenarios.
4. Evaluate expected loss severity and bankroll drawdown, not only expected profit.
5. Reject “easy multiplier” language unless a genuine cross-book arbitrage is verified from simultaneous executable prices.

If no candidate survives these checks, say so directly. Rank safer and riskier comparisons only as analysis; do not imply certainty.

## 8. Pipeline and deliverables

The delivered pipeline must:

1. Load canonical inputs.
2. Validate schemas, hashes, fixture coverage, and freshness status.
3. Build Dataset A/B.
4. select parameters on chronological pre-holdout windows.
5. Evaluate untouched holdout metrics.
6. Update ratings using verified elapsed results.
7. Generate probabilities and supported market comparisons.
8. Apply conservative `PASS`/`HALT` policy.
9. Export model dataset, normalized odds, metrics, predictions, provenance, research, screenshot manifest, and datapoint audit manifest.
10. Produce deterministic outputs from the same inputs.

Python code requires docstrings, examples, explicit formulas, comments explaining design choices, and fail-closed errors.

## 9. Report contract

The report must:

- Use Tailwind/CSS/JS and load all current fixture cards from prediction JSON.
- Contain exactly one `bg-slate-900` card per canonical fixture.
- Switch all visible content between English and Spanish.
- Include novice tooltips and ELI5 app-navigation steps.
- Show sources, cutoff, uncertainty, conditional/stale status, and responsible-gambling language.
- Show a workflow visualization of:
  - source acquisition and hashing;
  - Dataset A/B;
  - chronological selection and holdout;
  - model candidates and accepted weights;
  - calibration and robustness gates;
  - market comparison;
  - `PASS`/`HALT`;
  - JSON/report/audit/deployment.
- Never display an ensemble weight, model, feature, recommendation, or profitability claim not present in validated artifacts.

## 10. Independent validation loop

Run two iterations:

1. Data replication.
2. Code replication from clean inputs.
3. Model/statistical audit.
4. One row-level audit for every fixture.
5. Datapoint manifest completeness audit.
6. Element-by-element bilingual report/editor audit.

For every failure record the exact issue, root cause, fix, regression test, and repeated gates.

## 11. Tests and deployment

Required local/CI order:

1. Run pipeline.
2. Generate report.
3. Build `site/`.
4. Run full unit/integration/black-box/browser suite.
5. Upload exact site artifact.
6. Deploy Pages.
7. Verify the live exact commit marker, JSON/DOM parity, translations, and artifact hashes.

The live validation test is the only test allowed to skip before deployment, and only because no deployment URL/SHA exists yet.

## 12. Required files

- `AGENT_STATE.md`
- `PROJECT_UNDERSTANDING.md`
- `FUTURE_UPDATE_PROTOCOL.md`
- `ARCHITECTURE.md`
- canonical fixtures/results/odds/research CSVs
- Dataset A/B and model dataset CSVs
- prediction and metrics JSON
- screenshot and datapoint audit manifests
- provenance text
- complete Python pipeline
- JSON-driven bilingual report
- validation record
- tests and GitHub Actions workflow

Future updates follow `FUTURE_UPDATE_PROTOCOL.md` without bypassing a gate.
