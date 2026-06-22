# June 22–27 Model Research and Selection

## Objective

Select the strongest reproducible model components for one best-available recommendation per fixture without promoting complexity that does not beat simpler chronological baselines.

## Prior project candidates re-executed

The saved 222-match backtest was run without downloading or changing the historical dataset.

| Candidate | Weighted 1X2 Brier | Log loss | Decision |
|---|---:|---:|---|
| De-vigged market implied | 0.5956 | 0.9928 | Required anchor where complete prices exist |
| v4.1 model/market stack | 0.6039 | 1.0098 | Retained as evidence for market shrinkage |
| Dixon-Coles 35% ensemble | 0.6109 | 1.0245 | Rejected for 1X2 production |
| v4 Elo | 0.6157 | 1.0286 | Structural probability component |
| v3.1 Elo | 0.6175 | 1.0307 | Rejected |

The historical totals comparison was tied at 0.2458 Brier for Dixon-Coles and independent Poisson. Dixon-Coles therefore remains a shadow model rather than receiving production weight.

## Neural and temporal graph candidates re-executed

| Candidate | Chronological test Brier | Decision |
|---|---:|---|
| GraphMixer-like d4 | 0.67301 | Reject |
| GraphMixer-like d8 | 0.67325 | Reject |
| TemporalGraphNN d8 full graph | 0.67464 | Reject |
| TemporalGraphNN d4 temporal | 0.67473 | Reject |
| Tabular MLP | 0.67455 | Reject |

These implementations use deterministic graph/temporal featurizers with a trained classifier head. They do not beat the simpler Elo or market-based baselines and are not production graph neural networks trained end-to-end. They remain research artifacts only.

## Current score-model improvement

The current pipeline added a chronologically selected Elo-gap intensity term:

`match_total_mu = base_mu + gap_intensity * abs(Elo gap) / 400`

The selected parameters are:

- base total goals: 2.50
- team allocation: 0.35
- Elo gap scale: 350
- gap intensity: 0.15

Untouched 38-match holdout:

| Metric | Previous fixed-intensity model | Current match-specific model |
|---|---:|---:|
| Score NLL | 3.06619 | 3.04925 |
| Over 2.5 Brier | 0.25423 | 0.25039 |
| BTTS Brier | 0.25629 | 0.25295 |

Current fixture total intensity now varies instead of remaining fixed at 2.50.

## Current recommendation stack

- 1X2 decision probability starts from a 50/50 structural-model/de-vigged-market stack because the market and prior v4.1 stack outperform raw Elo historically.
- Expanded market families start at 35% model / 65% de-vigged market because they lack family-specific historical price backtests.
- Model weight shrinks further as model-market divergence rises.
- HALT candidates cannot win the utility ranking while any non-HALT candidate exists.
- If every candidate is HALT, the mandatory recommendation is the highest de-vigged market-probability outcome, not the largest disputed model edge.
- Final ranking uses stressed expected profit minus model-market disagreement and market-family uncertainty penalties.

## Primary research reviewed

- Dixon and Coles, *Modelling Association Football Scores and Inefficiencies in the Football Betting Market* (1997).
- Rossi et al., [Temporal Graph Networks for Deep Learning on Dynamic Graphs](https://arxiv.org/abs/2006.10637).
- Cong et al., [Do We Really Need Complicated Model Architectures for Temporal Networks?](https://arxiv.org/abs/2302.11636).
- Xenopoulos and Silva, [Graph Neural Networks to Predict Sports Outcomes](https://arxiv.org/abs/2207.14124).
- Yeung et al., [Evaluating Soccer Match Prediction Models: A Deep Learning Approach and Feature Optimization for Gradient-Boosted Trees](https://arxiv.org/abs/2309.14807).
- Bunker, Yeung, and Fujii, [Machine Learning for Soccer Match Result Prediction](https://arxiv.org/abs/2403.07669).
- Ren and Susnjak, [Predicting Football Match Outcomes with Explainable Machine Learning and the Kelly Index](https://arxiv.org/abs/2211.15734).

The literature supports boosted trees with football-specific ratings on sufficiently rich tabular datasets and temporal/graph models when genuine interaction data exists. This repository currently has 253 team-level historical rows, not player-event or tracking graphs. Promoting a deep or graph model solely because it is more complex would not be evidence-based.

## Phase retrospective

The score-intensity change improved all three untouched score-market metrics, and market shrinkage is supported by the historical 1X2 backtest. The recommendation policy now satisfies the one-pick-per-match requirement, but historical profitability remains unvalidated for expanded families. Fresh owner, replication, statistics, per-fixture, and editor audits remain mandatory before publication.
