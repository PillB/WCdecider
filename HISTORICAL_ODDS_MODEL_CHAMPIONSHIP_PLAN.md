# Historical Odds and Model Championship Execution Plan

Version: 2026-06-22

Status: binding implementation checklist for the current upgrade

This plan extends `WCDECIDER_SYSTEM_DESIGN.md`. It does not authorize labeling
proxy, averaged, opening, post-kickoff, or model-implied prices as closing odds.
It also does not accept the reported rival return as evidence without an
independently reproducible bet ledger.

## Phase 0 — Freeze claims, scope, and evaluation

- [ ] Define genuine-close, bounded-close, proxy-close, snapshot, and current
  screenshot evidence classes.
- [ ] Freeze competitions, seasons, bookmakers, markets, kickoff source, close
  selection rule, and legal/publication boundary.
- [ ] Freeze the model-championship folds, metrics, candidate families, ranking
  policy, and untouched release gates before evaluating the final holdout.

Done conditions:

1. The schema cannot represent an inferred price as a genuine close.
2. Every source has an access, license, redistribution, and timestamp-semantics
   note.
3. The final holdout, champion metric, and profitability gates are serialized
   before final evaluation.

## Phase 1 — Immutable historical acquisition

- [ ] Implement authenticated The Odds API historical snapshot acquisition.
- [ ] Implement optional Betfair historical stream ingestion.
- [x] Implement Football-Data closing-column ingestion in a physically separate table.
- [x] Acquire official The Odds API public historical samples as a second provider.
- [ ] Save immutable raw payloads outside public deployment artifacts when
  redistribution is restricted.

Done conditions:

1. Every raw payload has URL/request metadata, retrieval time, and SHA-256.
2. Re-running normalization from the same raw files is deterministic.
3. Missing credentials fail with a clear blocked status and never generate
   synthetic odds.

Current public result: 25 Football-Data files produce 142,349 rows across 8,908
events. Football-Data rows are provider-published closing columns without row
quote timestamps. Two official The Odds API samples are retained only in
ignored private validation storage: 1,311 rows over 38 overlapping events,
timestamped at least 695 minutes before kickoff. Zero rows are primary
closing-line eligible under the frozen 120-minute gate.

## Phase 2 — Canonical closing-odds dataset

- [ ] Normalize fixture, bookmaker, market, period, selection, line, decimal
  price, source snapshot time, bookmaker update time, kickoff, and source class.
- [ ] Select the final complete strictly pre-kickoff market per bookmaker.
- [ ] Join verified final scores and settle 1X2, totals, BTTS, and Asian lines.
- [ ] Produce coverage summaries by competition, season, market, bookmaker, and
  evidence class.

Done conditions:

1. `quote_time < kickoff` and `bookmaker_update_time < kickoff` for every
   primary-validation row.
2. Complete-market and settlement invariants pass, including pushes and quarter
   lines.
3. Coverage numerator, denominator, exclusions, and missingness reasons reconcile.

## Phase 3 — Exhaustive but leakage-safe model championship

- [ ] Test simple baselines: prevalence, Elo, market-only, Poisson, Dixon-Coles.
- [ ] Test gradual variants: recency, competition weighting, dynamic home/host
  effects, calibration, score-intensity and draw adjustments.
- [ ] Test radical variants only when data supports them: hierarchical dynamic
  Poisson, regularized multinomial/tabular models, Bayesian model averaging,
  graph/temporal models, and stacking.
- [ ] Select hyperparameters and stack weights only inside nested rolling-origin
  folds.

Done conditions:

1. Every candidate emits fold-level predictions before seeing fold outcomes.
2. Champion selection uses proper scores and calibration, not retrospective ROI
   alone.
3. High-capacity candidates that lack adequate effective sample size or fail to
   beat simple baselines are explicitly rejected.

## Phase 4 — Profitability and rival-claim audit

- [ ] Evaluate frozen policies on a chronologically later untouched sample.
- [ ] Apply vig removal, realistic execution lag, commissions, liquidity,
  missing-market handling, stake caps, and correlated-exposure limits.
- [ ] Report turnover, net profit, ROI, hit rate, CLV, maximum drawdown, longest
  losing run, bootstrap confidence intervals, and probability of loss.
- [ ] Apply family-wise or false-discovery controls across policy/model searches.

Done conditions:

1. No selected policy uses the final holdout for thresholds or model choice.
2. A profitability claim requires positive lower confidence bounds after costs
   and multiplicity correction, adequate sample size, and acceptable drawdown.
3. A +500% expected-return claim is rejected unless the rival supplies complete
   executable prices, timestamps, stakes, settlement, and independent replication.

## Phase 5 — Top-four recommendation output

- [ ] Rank up to four distinct sourced candidates for every current fixture.
- [ ] Suppress same-event equivalents and duplicate screenshots of the same
  app/market/selection/line.
- [ ] Preserve the existing top-one recommendation for compatibility.
- [ ] Add rank, reason, uncertainty, price gate, source, and profitability status
  to JSON and bilingual report cards.

Done conditions:

1. Every fixture has four ranks when four genuinely distinct complete sourced
   candidates exist; otherwise the shortfall is explicit.
2. Rank order exactly follows the frozen uncertainty-adjusted utility and is
   deterministic.
3. Browser tests verify 32 cards, rank/JSON parity, bilingual text, mobile layout,
   keyboard help, and no tooltip clipping.

## Phase 6 — Independent validation

- [ ] Data/source replication.
- [ ] Code/model replication from delivered public inputs.
- [ ] Statistical and leakage audit.
- [ ] Per-fixture recommendation audit.
- [ ] Editor/newbie and accessibility audit.

Done conditions:

1. Two independent rebuilds agree on every public artifact and hash.
2. No unresolved critical/high source, leakage, settlement, or ranking issue remains.
3. Every published JSON leaf has current role-specific audit evidence.

## Phase 7 — Release and live validation

- [ ] Build on an isolated `codex/...` branch and stage only reviewed files.
- [ ] Run unit, integration, corruption, deterministic, browser, and black-box tests.
- [ ] Push, open a draft PR, pass CI/CD, deploy the exact tested artifact, and
  validate the live SHA.

Done conditions:

1. Local and CI suites have zero failures.
2. Live JSON/DOM values and artifact hashes match the release commit.
3. Profitability wording accurately reflects the primary historical dataset gate;
   unavailable credentials or failed gates remain visible limitations.
