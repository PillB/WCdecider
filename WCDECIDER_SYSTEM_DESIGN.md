# WCdecider Canonical System Design

Version: 2026-06-22

Status: mandatory design and validation contract

This document is the canonical technical design for WCdecider. Every future
data, model, recommendation, report, test, and deployment update must read this
file together with `AGENT_STATE.md`, `AGENT.md`, `PROJECT_UNDERSTANDING.md`,
`ARCHITECTURE.md`, `FUTURE_UPDATE_PROTOCOL.md`, and
`STORM_LOOP_ENGINEERING_PROTOCOL.md`.

`MODEL_PIPELINE_EXPLAINED.md` is the code-linked student walkthrough. It must
remain synchronized with this contract and the executable functions.

## 1. Product objective

WCdecider is a reproducible World Cup football forecasting and betting-market
analysis system. It:

1. ingests verified historical results, current fixtures, OSINT research, and
   screenshot-derived Betano/Betsson prices;
2. selects models using chronological validation;
3. generates match-result and score-derived market probabilities;
4. compares model probabilities with complete sourced markets;
5. produces up to four economically distinct sourced comparisons and a
   separate fail-closed `ACTIONABLE`/`ABSTAIN` decision;
6. publishes a bilingual JSON-driven report;
7. records every JSON leaf in a four-role audit manifest;
8. tests, deploys, and validates the exact GitHub Pages revision.

`BEST_AVAILABLE` means the highest-ranked sourced comparison under the
documented policy. It does not mean certain, safe, or historically profitable.

## 2. Mandatory operating cycle

Every phase follows:

1. **READ**
   - `AGENT_STATE.md`
   - this design document
   - relevant source, requirements, and validation files
2. **ACT**
   - perform only the active scoped task
   - preserve unrelated user files
   - fail closed on missing evidence
3. **WRITE & COMPRESS**
   - update `AGENT_STATE.md` immediately
   - record command evidence, defects, fixes, and next dependency

No checklist item is complete without:

1. implementation evidence;
2. an automated or independently reproducible validation;
3. a defined failure condition.

### Mandatory research and repair method

Every material phase must apply the two-layer method defined in
`STORM_LOOP_ENGINEERING_PROTOCOL.md`:

1. STORM structures multi-perspective, source-grounded research and evidence
   synthesis.
2. Loop engineering executes a bounded reproduce–measure–review–repair–test–
   retrospect cycle.

They are not synonyms. STORM does not replace statistical tests, and loop
engineering may not reuse the final holdout as an iterative optimization set.
Release review evidence must name the exact model version and prediction/
metrics hashes, or the release remains blocked.

## 3. Repository source-of-truth map

### Inputs

- `wc_2026_matches_june_22-27.csv`: canonical fixture IDs and kickoffs.
- `wc_2026_results_through_june23.csv`: verified elapsed tournament results.
- `wc_team_elo_baseline_june11.csv`: frozen pre-tournament ratings.
- `wc_backtest_historical_dataset.csv`: historical modeling data.
- `odds_june*.csv`: verbatim screenshot transcription.
- `Screenshots/IMG_*.PNG`: immutable price evidence.
- `research_june*.csv`: direct-URL OSINT notes.

### Pipeline

- `wc_june22_27_pipeline.py`: canonical deterministic data/model/output path.

### Generated artifacts

- `wc_dataset_a_world_cups.csv`
- `wc_dataset_b_supplementary.csv`
- `wc_june22_27_model_dataset.csv`
- `wc_odds_june_22-27.csv`
- `wc_research_june22_27.csv`
- `wc_screenshot_manifest_june22_27.csv`
- `wc_june22_27_model_metrics.json`
- `wc_june22_27_predictions.json`
- `wc_june22_27_provenance.txt`
- `wc_june22_27_datapoint_audit.csv`

### Report and deployment

- `scripts/generate_report.py`: current-batch JSON-driven Tailwind/JS report
  generator. Its card/rendering architecture is reusable, but current artifact
  filenames, dates, and title must be parameterized before calling it fully
  batch-independent.
- `index.html`: generated report source.
- `scripts/build_site.py`: fail-closed deployment bundle.
- `site/`: exact Pages artifact.
- `.github/workflows/deploy.yml`: pipeline → audit → report → site → tests →
  Pages artifact → deploy → live validation.

## 4. Data and provenance design

### Fixture identity

- Stable fixture IDs are mandatory.
- Team aliases may normalize only unambiguous source labels.
- Truncated labels require fixture-context proof.
- No stale or extra fixture may enter the report.

### Screenshot prices

- Every price references a real filename and SHA-256.
- Cropped or unreadable prices are never inferred.
- Original app, market, selection, line, and text are preserved.
- Missing prices never become estimated sportsbook prices.

### Dataset split

- Dataset A: World Cup finals rows.
- Dataset B: supplementary qualifiers and friendlies.
- Elapsed 2026 matches replace stale historical copies.
- Data is sorted chronologically.
- The final 15% remains untouched for model evaluation.

### OSINT

- Every external fact needs a direct URL, access time, and confidence.
- Post-cutoff facts are excluded or explicitly marked unavailable.
- Research text is contextual evidence, not a hidden model target.

## 5. Market normalization and settlement

Supported families:

- full-time 1X2;
- total goals;
- BTTS;
- double chance;
- Asian handicap;
- explicitly normalized handicap-plus-total combinations.

Rules:

- Complete markets are grouped by fixture, app, market semantics, and line.
- 1X2 requires exact A/D/B coverage.
- Totals require Over/Under.
- BTTS requires Yes/No.
- Asian handicap requires opposing teams and lines.
- Quarter lines split the stake over adjacent half-lines.
- Combo probabilities come from exact joint score states, never multiplied
  marginal probabilities.
- Ambiguous result handicaps, boosts, corners, player markets, and unsupported
  pushed-leg combos fail closed.

## 6. Modeling framework

### Historical closing-odds evidence classes

- `timestamp_verified_bounded_close`: last complete named-bookmaker snapshot
  strictly before kickoff, with both provider snapshot and bookmaker update
  timestamps. Eligible for primary policy validation.
- `published_close_without_quote_timestamp`: provider-labeled close without a
  row-level quote time. Secondary robustness evidence only.
- `legacy_proxy_unknown_timestamp`: existing project value whose bookmaker and
  quote time cannot be reconstructed. Reconciliation only.

The Odds API historical snapshots are the preferred fixed-odds primary source;
Betfair historical exchange streams are the preferred independent benchmark
after access and redistribution rights are confirmed. Raw restricted-provider
payloads remain private; the public repository contains acquisition code,
schemas, hashes, coverage, and derived summaries.

`historical_odds_pipeline.py` enforces this separation. The current
redistribution-safe public corpus has 142,349 Football-Data closing-column rows
over 8,908 events with DST-aware kickoff conversion, cross-provider fixture
IDs, and split quarter-handicap settlement. Restricted Odds API samples remain
under ignored `private_data/` and are excluded from the downloadable corpus.
No row meets the frozen timestamp-verified 120-minute close gate, so
profitability remains unvalidated.

### Model-comparison visualization

The default report diagram uses solid green paths for production components.
Research mode replaces it with a distinct diagram using dashed violet paths
for challengers with zero production weight. Performance panels are generated
from metrics JSON and show proper scores, nested chronological folds,
paired-bootstrap differences, and confidence intervals. Profitability panels
show missing evidence instead of synthetic ROI, CLV, Sharpe, or profit curves.

### Nested model championship

`model_championship.py` compares uniform, market proxy, fixed Elo, nested-tuned
Elo, and nested Elo/market stacks on rolling-origin selection windows and one
untouched final holdout. Score-model Poisson and Dixon-Coles comparisons remain
in the canonical pipeline.

High-capacity TGNN and transformer candidates are registered but rejected from
fitting when the effective historical sample cannot support a credible
chronological comparison. Model complexity is never adopted to satisfy a rival
return claim.

Deep/graph research candidates remain in the championship registry rather than
in production. The current data can be viewed as a temporal graph of teams
connected by timestamped match edges, but that representation is not sufficient
evidence for a high-capacity temporal GNN. Promotion requires, at minimum:

- 2,000+ timestamped fixtures;
- roughly 30+ pre-event temporal edges per recurring team;
- strictly pre-kickoff node/edge features;
- nested walk-forward architecture and hyperparameter selection;
- final untouched holdout not used for model choice;
- calibration and proper-score superiority over simple baselines;
- timestamp-verified closing odds before any ROI/CLV claim;
- multiple-testing correction across searched architectures and policies.

### 1X2 structural model

- Ratings are updated sequentially using verified elapsed results.
- Neutral-site Elo uses K=60 and a goal-margin multiplier.
- A proper-score-tuned three-way conversion produces win/draw/loss
  probabilities. It must not be called empirically calibrated until reliability
  diagnostics are reported.
- Hyperparameters are selected on chronological pre-holdout windows.

### Score model

Production:

- tuned independent Poisson score grid, goals 0–10, renormalized;
- base total-goal mean selected from `{2.25, 2.50, 2.75, 3.00}`;
- team allocation selected from `{0.30, 0.35, 0.40}`;
- Elo gap scale selected from `{350, 420, 500}`;
- match-specific total intensity:

  `match_mu = base_mu + gap_intensity * abs(Elo gap) / 400`

  with `gap_intensity` selected from `{0, .15, .30, .45}` and bounded total
  intensity.

Shadow:

- Dixon-Coles low-score correction.
- It remains shadow-only unless paired holdout uncertainty shows a secure gain.

### Rejected complexity

TGNN, GraphMixer-like, and tabular MLP research implementations remain excluded
from production because prior chronological experiments did not establish
secure superiority over proper-score-tuned simple/market benchmarks.
Complexity is adopted only when it beats a simpler baseline on untouched data
with reliability evidence.

Registered research-track families include CatBoost/LightGBM tabular models,
hierarchical dynamic Poisson, Dixon-Coles, Temporal Graph Networks, TGAT-style
dynamic graph attention, GraphMixer/DyGFormer-style efficient temporal graph
models, and sequence transformers. They are documented for student learning and
future data expansion, not claimed as current production winners.

### Research-mode toggle

The report may expose a user-controlled research-mode toggle. This mode is a
shadow/sensitivity view, not a production override.

Current implementation:

- selected gated candidate: Dixon-Coles low-score correction;
- reason: it is the selected tested low-parameter football-specific shadow
  candidate because it adds low-parameter score dependence without violating
  the small-sample gate; untested registered families are not claimed inferior;
- blocked candidates: temporal GNN, TGAT-style, GraphMixer/DyGFormer, and
  sequence transformers remain registry-only until the data gate is met;
- production recommendations, stake simulation, and top-four ranking remain
  unchanged when the toggle is enabled;
- research mode publishes its own top-four sourced recommendation ranking, but
  each item is labeled shadow/sensitivity analysis and must never replace the
  production `recommendation` field until promotion gates pass;
- every research-mode field must be present in prediction JSON and audit
  manifest coverage;
- UI text must state `research_gated_not_production` and explain why promotion
  failed.

### Required metrics

- multiclass Brier;
- log loss;
- score negative log likelihood;
- Over 2.5 Brier;
- BTTS Brier;
- simple prevalence/uniform baselines;
- paired bootstrap confidence intervals;
- sample sizes and chronological split;
- regime-shift limitations.

## 7. Probability and price design

The score grid produces:

- totals 0.5–5.5;
- BTTS Yes/No;
- double chance;
- total-goal buckets;
- top correct scores;
- Asian handicap lines;
- supported joint combinations.

Fair decimal price:

- ordinary event: `1 / probability`;
- push-capable event: `1 + p_loss / p_win`.

Displayed common-market probabilities and screenshot-priced evaluation must use
the same probability engine.

## 8. Recommendation policy

Every fixture receives up to four economically distinct sourced
comparisons. Rank one is not an executable recommendation unless all
actionability gates pass.

### Decision probability

- Structural forecast probabilities remain independent of the quote being
  evaluated.
- De-vigged source-market probabilities are retained separately as
  disagreement and risk diagnostics.
- Any future probability stack requires out-of-sample weight selection and
  untouched superiority before deployment.

### Ranking utility

The ranking uses:

- minimum of base and stressed decision EV;
- model-market disagreement penalty;
- market-family validation penalty;
- strong HALT penalty.

If any non-HALT choice exists, HALT choices cannot win rank one. If all choices
are HALT, the least-penalized uncertainty-adjusted candidate is visibly labeled
as an investigative fallback.

Equivalent events from different screenshots/apps are deduplicated for the
top-four idea list after retaining the strongest sourced instance. If fewer
than four distinct complete events exist, the output reports the source
shortfall instead of inventing a fourth choice. Lower ranks may retain visible
`HALT` diagnostics after all non-HALT choices.

### Required recommendation fields

- app and source screenshot;
- market, selection, and line;
- source odds and model fair threshold;
- model and decision probability;
- base and stressed EV;
- utility and risk grade;
- PASS/HALT diagnostic;
- profitability-validation status;
- failure and freshness notes.

No recommendation may claim certainty or validated profitability without a
timestamped untouched historical price backtest.

### Risk-aversion lenses

The report exposes five profile levels: exploratory, balanced, cautious,
strict, and audit-only. These profiles reclassify the displayed sourced
recommendations by transparent thresholds on model-market disagreement,
stressed EV, risk grade, and fair-price gate.

Rules:

- profiles are UI/decision lenses, not model retraining;
- they do not mutate probabilities, source odds, rank-one production
  recommendation, or bankroll allocation;
- stricter profiles may mark more rows as `HALT` and must explain the specific
  failed threshold;
- exploratory profiles may surface more candidates for review but must retain
  the unvalidated-profitability warning;
- no profile may convert an underlying anomaly `HALT` into `PASS`;
- a lens `PASS` is a threshold diagnostic only, not evidence of model
  robustness, accuracy improvement, or betting profitability;
- the HALT loop compares identical sourced candidates under production and
  shadow models. A shadow reclassification is a sensitivity-review lead, not a
  resolved HALT or evidence that the shadow model is better.

## 9. Fail-closed bankroll simulation

The bankroll planner is educational and allocates only to `ACTIONABLE` rows.

### Scope

- Maximum budget: S/100 in Betano and S/100 in Betsson.
- A fixture is assigned only to the app containing its sourced selected price.
- App coverage is derived from the current rank-one sourced comparison and is
  not a fixed release constant.
- The system never invents the same price in the other app.

### Allocation

- Every `ACTIONABLE` fixture may receive a S/1 base stake.
- Remaining budget is weighted toward positive stressed EV and lower risk.
- Risk-grade bonus is monotonic: A > B > C > D.
- Maximum stake is S/10 per match.
- Stakes round to S/0.10.
- Unallocated budget is allowed and expected when gates fail.
- `ABSTAIN` always has stake zero.

### Per-match simulation fields

- simulated stake;
- percentage of app budget;
- screenshot price;
- model fair-price threshold;
- price-gate status;
- full-win gross return and profit illustration;
- six bilingual navigation/check steps only for `ACTIONABLE` rows;
- abstention and unvalidated-profitability warning.

If the current price is below the fair threshold, the website must state that a
disciplined process pauses and preserves the unallocated budget.

## 10. JSON-driven newbie explanations

Every compact metric box must read its explanation from prediction JSON.

Required metric keys:

- team A win;
- draw;
- team B win;
- expected goals team A;
- expected goals team B;
- Over 2.5;
- Under 2.5;
- BTTS Yes;
- BTTS No;
- home -0.5 Asian handicap.

Every EN/ES explanation contains:

1. `title`;
2. `category_meaning`;
3. `number_meaning`;
4. `what_you_can_do`.

Expected goals must be described as an average goal count, not a percentage or
exact score. Explanation fields are output-only and cannot change the model.

## 11. Tooltip and responsive UI design

- Help triggers work with mouse hover and keyboard focus.
- Tooltip content is escaped JSON text.
- Popups use viewport-fixed positioning, not card-relative positioning.
- Horizontal placement is clamped to the viewport.
- Popups choose above/below placement based on available space.
- Maximum height is viewport-bounded and scrollable.
- Z-index must exceed sticky navigation and match-card content.
- Tooltips must not be clipped by `overflow` on cards or grid containers.
- Mobile tests verify all tested popup rectangles remain inside the viewport.

## 12. Bilingual report contract

- Exactly one JSON-driven `bg-slate-900` card per canonical fixture.
- All visible text switches English/Spanish.
- Per-card content includes probabilities, expected goals, market summaries,
  recommendation, bankroll simulation, sources, risks, freshness, and ELI5.
- Betano and Betsson steps identify the exact fixture, market, selection, line,
  price check, stake, and slip verification.
- Dynamic load or audit failures are visible and block cards.
- The workflow diagram represents only implemented components.
- The report shell must render safely before JSON arrives: filters remain
  disabled, a bilingual loading skeleton is visible, no card rendering occurs,
  and late/failed/mobile fetches produce a visible error instead of a blank
  page or JavaScript exception.
- The footer must show last updated, model/report version, and exact build SHA
  marker after verified JSON loads, so users can verify freshness on mobile.
- Card rendering should degrade gracefully for future optional field drift while
  the audit gate still blocks missing or tampered prediction/metrics leaves.
- Mobile browsers must not fetch or parse the full field-level audit CSV. The
  full CSV remains the reproducibility artifact and build-time gate; the report
  loads only `wc_june22_27_datapoint_audit_summary.json`, verifies the
  prediction/metrics hashes and canonical leaf-path hash, and exposes a visible
  diagnostic panel with artifact URL, HTTP status, byte counts, build SHA, audit
  hash, network state, and user agent on any startup failure.
- Research mode, when available, must be off by default and enabled only by an
  explicit toggle. It may reveal shadow probabilities and deltas, but it cannot
  alter production recommendation fields or claim validated profitability.

## 13. Datapoint governance

Every prediction and metrics JSON leaf appears once in
`wc_june22_27_datapoint_audit.csv`.

Each row records:

- canonical value and hash;
- source artifact and hash;
- pipeline/model/mission hash;
- source URL/timestamp where applicable;
- freshness and conditional status;
- four distinct reviewer identities:
  - owner/model;
  - replication 1;
  - replication 2/statistics;
  - editor/UIUX.

All roles must provide release-specific PASS evidence. A stale review from a
previous leaf count is invalid. Any PENDING or FAIL status blocks site build.
The manifest stores compact, hash-bound references to the canonical reviewer
registry instead of repeating the same long evidence prose in every row. Full
evidence remains in `governance/subagent_reviews_june22_27.json`; this
normalization preserves traceability and keeps the artifact within GitHub's
single-file limit.

The browser independently computes the exact prediction/metrics JSON leaf-path
set and compares its SHA-256 against the lightweight audit summary before
displaying audit PASS. It must not download the full audit CSV in the UI path,
because that file can be tens of megabytes and can crash mobile Safari/WebKit
before an error handler can render.

## 14. Test design

### Unit tests

- formulas, probabilities, fair prices;
- quarter-line settlement;
- combo settlement;
- schema and completeness;
- allocation sums, stake caps, and return arithmetic;
- explanation schema and exact displayed-value references.

### Integration tests

- pipeline → artifacts;
- artifacts → audit manifest;
- audit → report;
- report → exact site bundle;
- deterministic rebuild and hashes.

### Browser/black-box tests

- 32 unique cards;
- JSON/DOM recommendation parity;
- English/Spanish toggle;
- no request failures or stale fixtures;
- mobile overflow;
- metric tooltip hover and keyboard focus;
- tooltip viewport bounds and fixed positioning;
- delayed mobile JSON load with no page errors;
- missing/tampered JSON fail-closed with visible error and no cards;
- mobile startup requests the audit summary JSON and never the full audit CSV;
- diagnostics panel appears on missing/tampered artifacts and includes the
  failing artifact path;
- footer last-updated, version, and build marker;
- allocated and unallocated app totals;
- per-match stake, return, and six-step flow parity.

### Release test

The full local and CI suite must pass. The live-only check may skip before
deployment only because an exact deployed SHA does not yet exist.

## 15. Deployment design

1. run pipeline;
2. generate zero-blocked audit manifest;
3. generate report;
4. build exact `site/`;
5. run full tests against that site;
6. upload one Pages artifact;
7. deploy that artifact;
8. validate the exact SHA live with Playwright;
9. independently verify live JSON, audit count/hash, and core UI contract.

Only reviewed in-scope files are staged. Unrelated dirty-worktree files remain
untouched.

## 16. Mandatory phase retrospectives

After every phase record:

- what passed;
- what failed;
- root cause;
- exact fix;
- regression test;
- remaining limitation;
- next phase strategy.

Current known limitations:

- historical expanded-market executable prices are absent;
- profitability and staking utility remain unvalidated out of sample;
- the 38-match score holdout is small and shifted;
- later fixtures require reruns after intervening results and current lineups;
- screenshot prices are snapshots and must be rechecked.

## 17. Future-change acceptance checklist

A future update is done only when:

1. canonical source coverage and hashes pass;
2. chronological model and market-specific metrics pass;
3. every fixture has an explicit `ACTIONABLE` or `ABSTAIN` status and
   every additional rank is settlement-distinct or an explicit source
   shortfall is published;
4. app prices and bankroll simulations use only sourced app data;
5. all JSON fields have fresh four-role audit PASS evidence;
6. all visible fields are bilingual and JSON-driven;
7. tooltips are unclipped on desktop and mobile;
8. unit, integration, black-box, browser, and deterministic tests pass;
9. GitHub Actions deploys the exact tested artifact;
10. the exact live SHA and artifact parity pass.
