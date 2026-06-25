# Recommendation and Stacking Promotion Plan

Status: active, fail-closed
Method: `STORM_LOOP_ENGINEERING_PROTOCOL.md`

## Objective and evidence boundary

The objective is to determine whether an empirically calibrated,
price-independent model or constrained stack may replace the current
development model and eventually authorize executable recommendations.

This plan does **not** authorize bets. Promotion requires both forecast-quality
evidence and a separate timestamp-qualified profitability evaluation. The
existing development comparison set has informed prior work and is not a
sealed confirmatory holdout.

## Phase 1 — Freeze the promotion protocol

- [x] Define candidate families, chronology, metrics, multiplicity control, and
  stop conditions before evaluating a new prospective cohort.
- [x] Separate price-independent production candidates from market-aware
  benchmarks.
- [x] Preserve `ABSTAIN`, null recommendations, and zero stakes until all gates
  pass.

Done tests:

1. A machine-readable result lists every searched candidate and weight.
2. No candidate using the evaluated quote can authorize a bet on that quote.
3. The recommendation authorization result is false whenever any required gate
   is unavailable or false.

Retrospective: the prior championship selected configurations chronologically,
but it did not export pooled OOF predictions, empirical reliability metrics, or
multiplicity-adjusted promotion decisions.

## Phase 2 — Generate leakage-safe OOF predictions

- [ ] Produce expanding-window outer-fold predictions for fixed Elo, tuned Elo,
  tuned independent Poisson, calibrated variants, and a constrained
  price-independent stack.
- [ ] Select all parameters, temperatures, and stack weights using only data
  preceding each outer test fold.
- [ ] Export row-level fixture date, outcome, weight, fold, probabilities, and
  model lineage.

Done tests:

1. Every OOF row has `train_end < fixture_date`.
2. No fixture date appears in both train and test within a fold.
3. Repeated runs produce byte-identical OOF CSV and result JSON.

## Phase 3 — Empirical calibration championship

- [ ] Compare identity and multiclass temperature scaling using inner
  chronological validation only.
- [ ] Report weighted log loss, multiclass Brier, top-label ECE, classwise ECE,
  confidence-bin counts, and sample size.
- [ ] Reject calibration when effective sample or bin coverage is inadequate or
  when proper scores deteriorate beyond the registered tolerance.

Done tests:

1. Probabilities are finite, strictly positive, and sum to one.
2. Temperature is selected without access to the outer test fold.
3. Promotion requires non-inferior proper scores and improved or non-inferior
   reliability on pooled OOF predictions.

## Phase 4 — Constrained stacking and multiplicity control

- [ ] Search a deterministic simplex grid over calibrated Elo and independent
  Poisson probabilities.
- [ ] Keep market-only and Elo/market stacks as research benchmarks, never as
  price-independent recommendation probabilities.
- [ ] Compare identical OOF observations with date-block bootstrap intervals and
  Holm correction across searched challengers.

Done tests:

1. Stack weights are non-negative and sum to one.
2. The selected stack beats each included base model in registered outer-fold
   evidence before it can pass the model gate.
3. Family-wise adjusted significance, fold consistency, and reliability gates
   all pass; otherwise the stack remains shadow-only.

## Phase 5 — Seal prospective cohorts

- [ ] Record immutable prediction hash, source commit, model version, fixture
  IDs, cutoff, kickoff bounds, and protocol hash before outcomes are known.
- [ ] Write a separate exact-hash lock artifact; evaluation verifies the lock
  and never rewrites either sealed file.
- [ ] Mark post-hoc or previously inspected cohorts as non-confirmatory.
- [ ] Evaluate a cohort only after all outcomes and required source snapshots
  are frozen.

Done tests:

1. Registry mutation after sealing changes the registry hash and fails the
   integrity test.
2. Every confirmatory fixture kickoff is strictly after the seal timestamp.
3. No evaluated cohort was used to choose its own model, calibration, stack, or
   recommendation policy.

## Phase 6 — Profitability and CLV authorization

- [ ] Join only named-bookmaker, complete, timestamped, strictly pre-kickoff
  prices satisfying the closing-window contract.
- [ ] Evaluate a frozen selection and staking policy after vig, pushes,
  commissions, and market-specific settlement.
- [ ] Report turnover, ROI, CLV, drawdown, concentration, block-bootstrap
  uncertainty, and multiplicity-adjusted policy comparisons.

Done tests:

1. At least 500 eligible bets across at least 250 fixtures are available.
2. Prespecified lower confidence bounds for both ROI and CLV are positive.
3. Drawdown, concentration, source coverage, and independent replication gates
   pass.

## Phase 7 — Recommendation promotion

- [ ] Require forecast, calibration, prospective, profitability, governance,
  report-parity, CI, and live black-box gates simultaneously.
- [ ] Generate recommendations from saved model outputs and eligible source
  prices only.
- [ ] Keep one best-available analysis per match while distinguishing
  non-executable fair-price watchlists from executable recommendations.

Done tests:

1. `recommendation_authorized` is true only when every named gate is true.
2. JSON, HTML, and bankroll outputs agree exactly and no unauthorized stake is
   positive.
3. Four exact-hash independent reviews, local tests, CI, deployment, and live
   validation pass.

## Current release decision

The current release remains `ABSTAIN` with zero stakes. Forecast promotion is
blocked by the absence of a newly sealed confirmatory holdout and sufficient
empirical calibration evidence. Profitability promotion is independently
blocked because zero historical rows satisfy the timestamp-qualified closing
price contract.
