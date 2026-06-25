# WCdecider Production and Research Model Pipelines

## Purpose and evidence boundary

This document explains the executable modeling path in
`wc_june22_27_pipeline.py` and `model_championship.py`. It is an implementation
guide, not a claim that any recommendation is safe, certain, or historically
profitable.

The current evidence supports reproducible probabilities, a production Elo
plus independent-Poisson score model, a zero-production-weight Dixon-Coles
challenger, exact settlement of supported markets, and chronological model
comparison with proper scores. It does not support a validated ROI, CLV,
Sharpe, or profit claim; a "surefire" bet; or promotion of a temporal graph
neural network, transformer, or other high-capacity model.

The historical closing-odds corpus has zero rows satisfying the frozen
timestamp-grade closing-price gate. Model probabilities can be evaluated, but
betting-policy profitability cannot yet be evaluated honestly.

## Reproduce the pipelines

Use Python 3.11 from the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ci.txt
playwright install chromium

PYTHONDONTWRITEBYTECODE=1 python3 -B historical_odds_pipeline.py build-canonical
PYTHONDONTWRITEBYTECODE=1 python3 -B wc_june22_27_pipeline.py
PYTHONDONTWRITEBYTECODE=1 python3 -B model_championship.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/merge_research_metrics.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_datapoint_audit.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_report.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/build_site.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/ -q
```

The scripts fail closed for missing files, malformed schemas, unmapped
fixtures, unsupported prices, or absent provenance. Random comparisons use the
frozen seed `42`. In a source bundle without `.git`, set
`SOURCE_BUNDLE_SHA=<exported-commit>` before `build_site.py`; otherwise the
footer is explicitly marked `LOCAL_SOURCE_BUNDLE_UNVERSIONED`.

## Production pipeline

### P1. Read and validate source files

Code: `read_csv`, `write_csv`, `sha256`, and `freshness_status`.

Inputs are historical results and ratings, verified 2026 results, a frozen Elo
baseline, canonical fixtures, screenshot-derived Betano/Betsson prices, and
direct-URL research notes. Explicit files prevent hidden API state and
hard-coded target probabilities.

Done conditions:

1. Every required file exists with unique headers.
2. Every screenshot has a SHA-256 hash.
3. Every odds and research row maps to exactly one canonical fixture.

### P2. Construct chronological historical rows

Code: `load_historical`, `HistoricalRow`, and `current_team_state`.

The pipeline excludes stale embedded 2026 rows, then replays verified 2026
results from the frozen baseline in date order. Each match stores its pre-match
rating before `update_elo` runs. This prevents post-match rating leakage and
duplicate results.

Done conditions:

1. Rows are date-sorted.
2. Rating updates occur only after the current row is created.
3. Canonical 2026 rows replace rather than duplicate stale rows.

### P3. Update neutral-site Elo ratings

Code: `expected_score`, `goal_margin_multiplier`, and `update_elo`.

```text
expected_a = 1 / (1 + 10 ** ((elo_b - elo_a) / divisor))
delta = K * goal_margin_multiplier * (actual_a - expected_a)
```

The current replay uses `K=60`, no automatic home advantage, and a bounded
goal-margin multiplier. Elo is a low-variance strength summary suitable for a
small sample.

Done conditions:

1. Rating gains and losses are equal and opposite.
2. Draws use an actual score of `0.5`.
3. Larger margins increase update magnitude without changing direction.

### P4. Calibrate three-way 1X2 probabilities

Code: `three_way_elo`, `temporal_folds`, `calibrate_elo`, `brier`, and
`log_loss`.

Elo first produces a two-outcome strength expectation. A bounded draw
probability is added as a function of matchup closeness. Divisor, draw base,
and draw slope are selected on chronological pre-holdout windows. The final
15% is evaluated once.

Current result:

- divisor `450`;
- draw base `0.22`;
- draw slope `0.12`;
- The exact selection/development-comparison counts are generated in
  `model_championship_results.json`; the comparison block is development-only,
  not an untouched confirmatory holdout.
- holdout Brier about `0.57347`;
- holdout log loss about `0.93759`.

Log loss and multiclass Brier are proper scoring rules, unlike accuracy, and
penalize unjustified confidence.

Done conditions:

1. The final holdout is excluded from hyperparameter selection.
2. Folds remain chronological.
3. Probabilities are positive and sum to one.

### P5. Select the production score model

Code: `expected_lambdas`, `score_model_metrics`, `score_model_row_losses`, and
`calibrate_score_model`.

The pipeline searches the expected total-goal level, Elo-to-goal allocation,
gap scale, and mismatch intensity on chronological selection windows. Candidate
score grids are evaluated by exact-score negative log likelihood, Over 2.5
Brier, and BTTS Brier. The selected model is evaluated on a date-blocked
development comparison set; a new sealed prospective holdout is still required.

Current production configuration:

- tuned Elo independent Poisson;
- total-goal base `2.5`;
- allocation `0.35`;
- Elo gap scale `350`;
- gap intensity `0.30`.

Done conditions:

1. Selection and holdout separate before search.
2. Exact-score likelihood is measured at the observed score.
3. Over 2.5 and BTTS are compared with selection-rate baselines.

### P6. Create fixture expected goals

Code: `expected_lambdas` and the production section of `build`.

```text
match_mu = clip(base_mu + gap_intensity * abs(Elo gap) / 400, 1.5, 4.5)
team_a_share = 0.5 + allocation * tanh(Elo gap / gap_scale)
lambda_a = match_mu * team_a_share
lambda_b = match_mu * (1 - team_a_share)
```

This separates expected pace from the allocation of goals. For example,
`lambda_a = 0.51` means an average of 0.51 goals across repeated scenarios; it
does not mean a 51% chance of scoring.

Done conditions:

1. Both lambdas remain positive.
2. Their sum equals the bounded match total.
3. A larger Elo advantage increases that team's goal share.

### P7. Build the independent-Poisson score grid

Code: `poisson_pmf` and `score_matrix`.

The model enumerates scores 0–10 for each team, multiplies the independent
Poisson probabilities, and renormalizes the finite 121-cell grid.

Done conditions:

1. Cells sum to one after normalization.
2. No probability is negative.
3. Grid-implied home/draw/away sums to one.

### P8. Derive common football markets

Code: `event_probability`, `asian_probability`, `fair_decimal`,
`common_market_probabilities`, and `result_probabilities_from_matrix`.

The same score grid generates 1X2, totals, BTTS, double chance, total-goal
buckets, correct scores, and Asian handicaps. This avoids contradictory
probabilities from unrelated models.

Done conditions:

1. Complementary no-push markets sum to one.
2. Asian push probability is explicit.
3. Fair prices include push probability where applicable.

### P9. Normalize and gate screenshot markets

Code: `normalize_market_schema`, `mark_complete_markets`,
`load_and_merge_odds`, and `screenshot_manifest`.

Each row receives a canonical family, settlement rule, selection, line,
fixture, app, and source hash. Only structurally complete groups are eligible
for EV calculations. Ambiguous rows remain provenance evidence but are not
guessed.

Done conditions:

1. 1X2 requires home/draw/away.
2. Totals and BTTS require both sides.
3. Asian handicap requires opposing selections.

### P10. Settle contracts by exact score enumeration

Code: `settle_line`, `split_quarter_line`, `settle_asian_handicap`, and
`probability_and_ev`.

For every score, the code calculates win, push, partial win, partial loss, or
loss and sums probability-weighted returns. A quarter line such as `-0.75`
splits equally into `-0.5` and `-1.0`.

Done conditions:

1. Win, push, and loss equivalents sum to one.
2. Quarter-line examples are unit tested.
3. Unsupported contracts return no evaluation rather than a fabricated value.

### P11. Combine model and market information conservatively

Code: `evaluate_sourced_markets`.

For each complete sourced selection the pipeline computes model EV, adverse
stress EV, and model-market divergence. The structural model probability and
the market-implied probability remain separate. The quoted price never enters
the probability used to evaluate that same quote.

Done conditions:

1. Decision probability equals the independent structural forecast.
2. Market probability is used only for disagreement/risk diagnostics.
3. Decision win/push/loss sums to one.

### P12. Diagnose anomalous edges

Code: `classify`.

`HALT` is assigned when model-market divergence exceeds 15 percentage points
or raw EV exceeds 25%; otherwise the diagnostic is `PASS`. Large apparent
edges often indicate stale prices, transcription mistakes, settlement
mismatches, missing information, or model failure. `PASS` only means the
anomaly gate did not fire.

Done conditions:

1. `PASS` is never described as safe, certain, robust, or profitable.
2. Risk profiles cannot override an underlying HALT.
3. Research/production HALT comparisons use the same sourced candidate.

### P13. Rank up to four distinct recommendations

Code: `recommendation_utility`, `recommendation_equivalence_key`,
`rank_distinct_recommendations`, and `public_recommendation`.

```text
utility =
  minimum(decision EV, stressed decision EV)
  - disagreement penalty
  - market-family penalty
  - HALT penalty
```

Non-HALT rows rank first. Economically identical contracts are deduplicated by
their score-state settlement vectors. Rank one is `BEST_AVAILABLE`. If every
candidate is HALT, the highest de-vigged market-probability fallback is still
published but visibly remains investigative.

Done conditions:

1. Equivalent contracts cannot occupy multiple ranks.
2. Rank one exists whenever a supported complete market exists.
3. Every rank carries price, fair price, stress EV, risk, and the
   unvalidated-profitability warning.

### P14. Apply risk-aversion lenses

Code: `RISK_AVERSION_PROFILES`, `risk_lens_for_recommendation`, and
`risk_profile_summary`.

The five lenses are exploratory, balanced, cautious, strict, and audit only.
They expose threshold-based views without changing probabilities, odds,
production rank one, or bankroll allocation.

Done conditions:

1. Stricter thresholds are nested.
2. No profile promotes an underlying HALT.
3. The UI states the exact threshold that passed or failed.

### P15. Produce an educational bankroll simulation

Code: `allocate_app_budget`, `attach_bankroll_simulation`, and
`app_navigation_steps`.

The S/100-per-app example assigns a small base amount for required fixture
coverage, weights the remainder toward lower-risk positive stressed EV, caps a
single selection at 10%, and rounds to S/0.10. It is a usability simulation,
not a validated Kelly policy.

Done conditions:

1. Stakes sum exactly to S/100 per app.
2. No example stake exceeds the cap.
3. The report says staking utility and profitability are unvalidated.

### P16. Export auditable artifacts

Code: `build`, `main`, and the report-generation scripts.

The pipeline exports model datasets, normalized odds, predictions JSON, metrics
JSON, provenance, screenshot manifest, research data, and report/site assets.

Done conditions:

1. Generated JSON drives match cards and diagrams.
2. Root and site artifacts have matching hashes.
3. Unit, integration, browser, bilingual, mobile, and live-site checks pass
   before release.

## Research pipeline

### R1. Register candidate families before fitting

Code: `model_championship.py`, `registered_variants`, and
`capacity_rejections`.

The registry includes simple baselines, Elo, market proxy, Elo-market stacks,
score models, tabular boosting research, Bayesian model averaging research,
temporal graph models, and sequence transformers. Registration prevents the
report from implying that every fashionable architecture was credibly trained.

### R2. Run a nested chronological benchmark

Code: `rolling_windows`, `tune_elo`, `tune_stack`, and
`nested_outer_benchmark`.

Inner rolling-origin windows choose Elo and stack parameters. Independent outer
chronological windows evaluate those choices. Same-date matchdays remain on one
side of each outer boundary. The benchmark winner is chosen by outer mean log
loss, then Brier; the final holdout is evaluation-only. This result is evidence,
not an automatic deployment instruction.

The current outer-fold benchmark winner is `market_devigged_proxy`.

### R3. Fit the feasible football-specific challenger

Code: `dixon_coles_score_matrix` and the shadow section of
`calibrate_score_model`.

Dixon-Coles modifies the independent-Poisson cells for `0-0`, `0-1`, `1-0`,
and `1-1`, then renormalizes. The selected shadow parameter is `rho = -0.15`.
This adds one football-specific dependence parameter and is more defensible on
a few hundred matches than a large neural architecture.

### R4. Compare production and challenger on identical rows

Code: `score_model_row_losses` and `paired_bootstrap_mean_difference`.

For each holdout match, weighted challenger loss minus weighted production loss
is stored inside its calendar-date block. Whole date blocks are resampled 2,000
times. Dixon-Coles has slightly better point estimates for score NLL and BTTS,
but both 95% intervals cross zero, so the improvement is not statistically
secure.

Current limitation: date blocking preserves within-matchday dependence but
does not fully model repeated-team and competition dependence. With more data,
add team/competition cluster and longer moving-block sensitivity intervals.

### R5. Generate research-specific probabilities and recommendations

Code: `research_mode_payload`, the research branch of `build`, and
`evaluate_sourced_markets`.

The Dixon-Coles grid produces separate research probabilities, stress grids,
top-four sourced recommendations, and production deltas. Production
recommendations and bankroll fields remain unchanged.

Done conditions:

1. Research lineage points to research probabilities and `rho`.
2. Research mode cannot overwrite production fields.
3. HALT comparisons pair identical sourced candidates.

### R6. Enforce zero production weight and promotion gates

Code: `research_mode_payload`, `deep_learning_research`, and requirements
R2.12–R2.14.

No research model enters production without enough timestamped fixtures and
repeated temporal edges, strictly pre-event features, nested walk-forward
selection, untouched-holdout superiority, calibration evidence, multiplicity
control, and timestamp-verified closing-price ROI/CLV evaluation.

The current project prescreen requires at least 2,000 timestamped fixtures and
roughly 30 temporal edges per team. These are conservative project gates, not
universal constants.

### R7. Build cross-fitted calibration and stacking promotion evidence

Code: `promotion_pipeline.py`,
`RECOMMENDATION_STACKING_PROMOTION_PLAN.md`, and
`governance/prospective_holdout_registry.json`.

For each expanding outer fold, the promotion pipeline generates genuine inner
OOF Elo and independent-Poisson predictions. Scalar temperature parameters and
a non-negative convex stack weight are selected only from those inner OOF
predictions. The selected base configurations are then refit on the complete
outer-training prefix and evaluated once on the outer block.

The pooled OOF artifact reports log loss, multiclass and classwise Brier,
top-label and classwise ECE, calibration-in-the-large, class counts, fold
lineage, date-block bootstrap intervals, and Holm-adjusted comparisons.
Market-price inputs are excluded from this production-candidate track.

Current result: 124 OOF rows are sufficient only for exploratory scalar
temperature research. Raw tuned Elo has the best pooled OOF log loss. Both
temperature-scaled bases have worse point estimates with confidence intervals
that cross zero; the selected stack collapses to calibrated Poisson and is
worse than raw tuned Elo. Some temperature choices hit the search boundary and
production sample gates fail. The stack therefore receives zero production
weight and cannot authorize recommendations.

## Validation design

| Risk | Control | Current status |
|---|---|---|
| Temporal leakage | expanding/rolling-origin splits | implemented |
| Same-matchday leakage | keep same-date blocks together | implemented |
| Hyperparameter bias | nested inner selection and outer evaluation | 1X2 benchmark |
| Final test reuse | new sealed prospective temporal holdout | not yet available; release remains blocked |
| Probability quality | log loss and Brier | implemented |
| Comparison noise | paired row differences and confidence interval | implemented |
| Dependent matches | block/cluster sensitivity intervals | future improvement |
| Many model variants | registry, nested search, Holm gate before promotion | implemented for the current price-independent promotion track; broader families remain gated |
| Calibration drift | pooled cross-fitted reliability/ECE plus future sealed monitoring | development diagnostics implemented; prospective confirmation blocked |
| Policy overfit | frozen policy on executable historical closes | blocked: zero eligible closes |
| Distribution shift | competition/time subgroup and recency stress | partly implemented |
| Reproducibility | files, hashes, seeds, clean-room reruns | implemented |

## STORM plus loop engineering

The Stanford STORM pattern is used to organize research, not replace
statistical validation:

1. **Perspective discovery:** methodology, replication, lineage, and
   editor/student agents.
2. **Source-grounded investigation:** each perspective traces claims to code,
   artifacts, tests, and primary references.
3. **Outline synthesis:** independent findings become the stage-by-stage
   structure and validation matrix.
4. **Document generation:** explanations are written only after the evidence
   structure is fixed.

The bounded loop-engineering cycle is:

```text
define invariant
→ reproduce
→ adversarial sub-agent review
→ classify finding
→ patch code/document/test
→ rerun focused tests
→ rerun full suite
→ repeat until release gates pass
```

This loop must not repeatedly optimize against the final holdout. A failed
promotion returns to selection/outer-fold research and requires new future
holdout data or an explicitly exploratory label.

## Primary references

- Dixon and Coles (1997), *Modelling Association Football Scores and
  Inefficiencies in the Football Betting Market*.
- Bergmeir, Hyndman, and Koo (2018), time-series cross-validation:
  https://doi.org/10.1016/j.csda.2017.11.003
- Hyndman and Athanasopoulos, time-series cross-validation:
  https://otexts.com/fpp3/tscv.html
- Gneiting and Raftery (2007), strictly proper scoring rules:
  https://doi.org/10.1198/016214506000001437
- Guo et al. (2017), probability calibration:
  https://proceedings.mlr.press/v70/guo17a.html
- Nadeau and Bengio (2003), uncertainty after model comparison:
  https://doi.org/10.1023/A:1024068626366
- Demšar (2006), statistical model comparisons:
  https://www.jmlr.org/papers/v7/demsar06a.html
- Shao et al. (2024), Stanford STORM:
  https://arxiv.org/abs/2402.14207
- Stanford OVAL STORM implementation:
  https://github.com/stanford-oval/storm

## Universal done conditions

No stage is complete until all three conditions hold:

1. **Implementation:** behavior exists in executable code or a generated
   artifact.
2. **Evidence:** a deterministic test, hash comparison, or statistical result
   validates it.
3. **Communication:** report and documentation describe the same behavior and
   disclose its limits.
