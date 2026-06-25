# Specialist STORM Model Review

Status: independent AI/ML QA/model-validation verdict is FAIL-CLOSED; prior
release approval revoked.

Reviewed artifacts:

- model version: `june22_27_best_available_v4_independent_ev`;
- predictions SHA-256:
  `c38f08849a489935b9e946758db001b2cc0bee5dd0a7724cc5d9731901780976`;
- metrics SHA-256:
  `c5668b96fcf723620fc8fef1ffe15a6981ad5352267b8b4e06bc6b1e16ca0aa1`.

## STORM perspectives

1. senior ML methodology;
2. deep-learning architecture;
3. temporal GNN/graph modeling;
4. football forecasting and betting modeling;
5. independent AI/ML QA and model validation.

## Cross-perspective consensus

- Neural and temporal-graph models have not earned production weight.
- The immediate bottleneck is data integrity, feature availability, sealed
  evaluation, and recommendation-policy validation—not model capacity.
- Current graph methods are experimental deterministic featurizers rather than
  validated end-to-end temporal GNNs.
- Graph-derived rolling features can be tested now in regularized tabular and
  dynamic-Poisson baselines.
- Historical profitability remains unvalidated because zero rows meet the
  timestamp-grade closing-price gate.
- A prospective forecast/quote ledger and a genuinely sealed future holdout
  have higher expected information gain than another architecture search.

## Specialist-raised candidate release blockers

The independent validator must reproduce and rule on:

1. an alleged impossible duplicate Poland–Japan 2018 row;
2. heterogeneous historical Elo construction;
3. prior development feedback using the nominal final holdout;
4. forced recommendations with negative EV, negative stress, HALT, stale data,
   or below-fair prices;
5. positive bankroll allocation to such recommendations;
6. ambiguous handicap-plus-total push settlement;
7. stale/conditional fixtures receiving executable-looking recommendations;
8. unsupported “TGNN”/GraphMixer naming and evaluation claims in historical
   research artifacts.

## Architecture research classification

- Dynamic ratings and graph-derived tabular features: research now.
- Hierarchical dynamic/bivariate Poisson: highest-priority model challenger
  after data repair.
- Neural Poisson/intensity model: first defensible neural shadow candidate only
  after larger clean score history.
- Tabular MLP/team embeddings: deferred until at least thousands of clean
  fixtures and substantially denser team histories.
- Sequence models/TGN/TGAT/GraphMixer: research-gated.
- Transformer/DyGFormer/player heterogeneous graph: rejected under current
  data.

## Proposed promotion evidence

Any complex model must:

1. use availability-timestamped pre-event features;
2. use date-block nested walk-forward selection;
3. preserve a new sealed holdout;
4. beat market and strongest non-neural baselines in log loss and Brier;
5. show a paired block-bootstrap confidence interval below zero;
6. show reliability slope/intercept and classwise reliability;
7. survive multiplicity correction and ablations;
8. show stable gains across degree, era, competition, and favorite/underdog
   strata;
9. use timestamp-eligible executable odds before profitability claims.

No production change is approved by this document. The independent AI/ML QA
validator owns the final severity and release-gate decision.

## Independent governance verdict

Two independent validators confirmed release blockers:

- materially corrupt/incomplete 2018 and 2022 World Cup fixture history;
- nominal holdout contaminated by repeated development feedback;
- forced negative-EV, negative-stress, HALT, stale, and below-fair
  recommendations with positive stakes;
- invalid Asian grouping that combines signed quarter-line markets;
- unsupported future combo push semantics;
- heterogeneous/non-replayable Elo regimes;
- no confirmatory calibration or profitability evidence.

Required release state:

- release: `BLOCKED`;
- recommendation policy: not approved;
- bankroll output: prohibited;
- combo markets: disabled pending contract validation;
- graph/deep models: research only;
- probability model: development-only pending clean data and a new sealed
  prospective holdout.

## Repair iteration v5

New development-only artifacts:

- model version: `june22_27_v5_fail_closed_development_only`;
- predictions SHA-256:
  `315c720c4c2a3379de6decc48d216a1c9c3338e28ab55851eb7f164b20559f66`;
- metrics SHA-256:
  `b4b9f5834f3c7bd4d2f569b16a40c68923d7a24d8b59a77ad5bbf120efd19065`;
- historical dataset SHA-256:
  `a16de28a55d29065509a3250dbad25aadfaa60519666f0b55293938c2f0ca072`.

Implemented:

- repaired 2018/2022 48-fixture group contracts with pair/appearance gates;
- tournament Elo replayed sequentially from documented start snapshots;
- signed Asian home-line market identity and exact reciprocal-pair completeness;
- combo markets disabled pending app-specific settlement contracts;
- elapsed/conditional lifecycle gates;
- all 32 decisions set to `ABSTAIN`;
- Betano and Betsson stake totals set to S/0 with full budgets unallocated;
- nominal holdout reclassified as development-only, not confirmatory;
- prior governance approval remains revoked.

Focused data/model/governance tests: 50 passed. Independent validator re-audit
is pending; this repair does not restore release approval.
