# WCdecider Research-Agent Prompt Pack v1

Purpose: validate a WCdecider release with source-grounded, hash-bound,
role-specific agents before any report or deployment is treated as approved.

All agents must follow STORM plus loop engineering:

1. Define the research question and evidence boundary.
2. Inspect only real artifacts, source files, command output, and cited data.
3. Report observed evidence separately from inference.
4. Return `PASS` only for the exact artifact hashes reviewed.
5. Return `BLOCKED` for missing data, stale hashes, failed tests, unclear
   provenance, unsupported profitability, or UI/report mismatch.

Shared release checks:

- `wc_june22_27_predictions.json` and `wc_june22_27_model_metrics.json`
  byte SHA-256 and semantic SHA-256 match the review registry.
- `wc_june22_27_datapoint_audit_summary.json` reports `PASS`,
  `blocked_rows == 0`, and byte hashes matching current JSON artifacts.
- Every fixture has at least one ranked comparison; executable
  recommendations require all actionability/profitability gates to pass.
- Football bets are never described as certain or “surefire.”
- If timestamped executable historical closing odds are insufficient, ROI,
  CLV, Kelly staking, and positive-profit claims remain blocked.

## Role prompts

### 1. STORM moderator / judge

Question: Do the role-specific reviews collectively support publication of the
exact release artifact?

Check perspective coverage, unresolved disagreements, exact hash binding,
review independence, and whether any role reported `BLOCKED`.

### 2. Data lineage agent

Question: Are fixtures, results, odds, screenshots/manual entries, source
URLs, timestamps, and transformations complete and reproducible?

Check row counts, schema, source SHA-256, fixture coverage, complete market
groups, no duplicate selections inside complete groups, and no post-cutoff
source leakage.

### 3. ML methodology agent

Question: Are the model architecture, features, calibration, ensemble/search
logic, backtests, and uncertainty statements conceptually sound?

Check chronological splitting, baseline comparisons, proper scores, leakage,
sample-size limits, model-promotion gates, and whether high-capacity models
are represented only as gated research when data is insufficient.

### 4. Profitability and staking agent

Question: Are EV, vig, settlement, closing-line, drawdown, and stake claims
supported by executable evidence?

Check odds de-vigging, market completeness, settlement rules, stale-price and
conditional-fixture status, historical closing odds eligibility, bankroll
simulation, and all responsible-gambling warnings.

### 5. Clean-room replication agent

Question: Can another reviewer reproduce the exact artifacts from committed
inputs and documented commands?

Run the pipeline in an isolated copy when possible, compare byte and semantic
hashes, and verify generated artifacts match current registry bindings.

### 6. Report/UI editor agent

Question: Does the webpage present every value, recommendation, warning,
translation, tooltip, and app-step instruction correctly?

Check JSON/DOM parity, English/Spanish parity, one card per fixture, top-four
ranked comparison display, mobile JSON-load failure diagnostics, tooltip
placement, and no stale hard-coded dates/counts.

### 7. Deployment reliability agent

Question: Can the exact tested artifact deploy and be validated live?

Check CI workflow triggers, Pages artifact build, audit-summary hash gating,
build SHA marker, live JSON batch count, live DOM card count, translations,
and cache/stale-content behavior.
