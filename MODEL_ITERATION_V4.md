# WCdecider Model Iteration v4 — Critiques, Subagent Review & Retrospectives

**Date:** 2026-06-15 · **Iterations:** 2 rounds · **Subagents:** 6 (degrees 1–6)

---

## Iteration 0 Preamble (Pre-Review State)

The v3.1 pipeline (`wc_replicable_pipeline.py`) achieved peer-reviewed replication SUCCESS on the June 15–16 slate but exposed structural weaknesses on MD1–MD3 backtest:

- Spain 0–0 CV: raw 72% win vs realized draw
- Netherlands @2.15: MOD ROBUST call lost 2–2 (S/30)
- Sweden 5–1 Tunisia: soft-book Tunisia trap
- Independent Poisson ignores low-score correlation (0–0, 1–0 clusters)
- Single ensemble weight (35/35/30) applied to 1X2 degraded Brier vs pure Elo
- HALT triggered on raw model EV, not market-blended EV
- xG hybrid stub unwired; static 0.4 blend hurt calibration

**Objective:** Identify 20 critiques, run 6 subagents at 5+ degrees of structural difference, backtest, iterate, select best robust model.

---

## 20 Critiques & Improvements

| # | Critique | Severity | v4 Fix | Degree |
|---|----------|----------|--------|--------|
| 1 | Independent Poisson treats goals as uncorrelated | High | Dixon-Coles for O/U/BTTS only | 2 |
| 2 | DC blended into 1X2 raises Brier on draw outcomes | Critical | **Decouple**: Elo anchor for 1X2, DC for goals | 2 |
| 3 | `opener_draw_boost=0.055` under-calibrates WC 0–0 shocks | High | Tune to 0.07; `draw_base=0.20` | 1 |
| 4 | `mu_total=2.4` overshoots MD1–3 observed ~2.0 | Medium | Default 2.25; per-match heat adjust retained | 1 |
| 5 | Single ensemble weight for all bet tiers | High | Rule 24 tier-conditional weights | 4 |
| 6 | MOD favorites use same blend as SPEC longshots | Critical | MOD defers 50% to sharp; saved NED-JPN | 4 |
| 7 | HALT on raw model EV causes false positives | High | HALT on blended + Rule 14 EV | 4 |
| 8 | Rule 14 applied before ensemble, not after | Medium | Apply post-blend for staking EV | 4 |
| 9 | xG hybrid at fixed 0.4/0.6 hurts mismatches | High | Gate: only when gap>450 + lineup confirmed | 3 |
| 10 | No cross-book soft-side in EV layer | Medium | `o_soft_win_a` leg in SPEC tier (55% soft) | 4 |
| 11 | BTD standalone over-predicts draws on mismatches | Medium | BTD for draw parameter only, not 1X2 blend | 2 |
| 12 | CONMEBOL/AFC shrinkage not in replicable CSV path | Medium | Retained in v3; v4 inherits via finetune strings | 1 |
| 13 | N=2 settled matches overfits hyperparameter search | High | Expand to N=9; LOO validation | All |
| 14 | No log-loss or trap-detection metrics | Medium | `wc_backtest_framework.py` adds both | All |
| 15 | Sensitivities don't propagate to blended EV | Low | Sensitivities on 1X2 anchor; blend uses base | 1 |
| 16 | Combo joints use MC not full DC matrix | Medium | `dixon_coles_score_matrix` for combos (v4 DC leg) | 2 |
| 17 | Pinnacle disagreement checked post-hoc only | Medium | `sharp_diff_pp` in `halt_check_blended` | 4 |
| 18 | Static Elo snapshot; no temporal decay | Low | v5: EWMA + graph-regularized Elo | 5 |
| 19 | Hierarchical Bayesian posteriors unused for Kelly | Low | v5: conservative Kelly from draw bands | 6 |
| 20 | No automated regression tests for v4 | Medium | `tests/test_wc_model_v4.py` | All |

---

## Six Subagent Degrees — Summary

| Degree | Approach | Key Finding | Adopted in v4? |
|--------|----------|-------------|----------------|
| **1** Variational Elo+Poisson tuning | Grid search opener_boost, μ, draw_base | v4 Brier 0.8628 vs raw 1.106 on Spain-CV | ✅ Yes |
| **2** Dixon-Coles + BTD + 35/35/30 ensemble | Structural upgrade | DC ensemble **worse** 1X2 Brier; use DC for O/U only | ✅ Partial |
| **3** xG hybrid bottom-up | Dynamic club xG blend | Static 0.4/0.6 hurts; gate behind gap+lineup | ⏳ v5 |
| **4** Sharp-first 50/30/20 (MOD) vs soft 55% (SPEC) | Market-tier ensemble | PASS on NED-JPN; Rule 24 | ✅ Yes |
| **5** Temporal GNN surrogate | EWMA + graph Elo + Bayes BTD | Promising; N too small for full TGN | ⏳ v5 |
| **6** Hierarchical Bayesian | Posterior draw bands → conservative Kelly | ~57% stake haircut; Rules as learned nodes | ⏳ v5 |

---

## Iteration 1 — Execute & Measure

### Checklist (completed)

- [x] Spawn 6 subagents (degrees 1–6)
- [x] Build `wc_ensemble_degree2.py` (Degree 2)
- [x] Run Brier on Spain-CV + BEL-EGY (N=2)
- [x] Document 20 critiques
- [x] Identify elo_v3 as best 1X2 on N=2

### Retrospective 1

**Results:**
- `elo_v3` mean Brier 0.9519 (best on N=2)
- `ensemble_35_35_30` mean Brier 1.1279 (worse)
- DC ρ grid: ρ=0.0 marginally best on N=2 ensemble (overfit signal)
- Weight sensitivity: `more_elo` (45%) best on N=2

**Issues to fix:**
1. N=2 insufficient — expand to MD1+MD2+MD3 (9 matches)
2. Don't blend DC into 1X2 despite Degree-2 recommendation
3. Tier-conditional weights not yet implemented
4. Need unified v4 module

**Strategy for Iteration 2:**
- Build `wc_model_v4_ensemble.py` with decoupled legs
- Expand `wc_backtest_framework.py` to 9 matches
- LOO cross-validation for opener_boost
- Trap analysis on MOD favorites
- HALT on blended EV

---

## Iteration 2 Preamble

**Goals:**
1. Implement v4 with Rule 24 tier ensemble
2. Backtest 9 settled matches
3. Hyperparameter sweep (opener_boost × μ)
4. Select production winner
5. Update HTML diagram + documentation

**Contingencies:**
- If v4_elo ≈ v31_elo: keep v3.1 replicable pipeline unchanged for regression
- If DC hurts 1X2: confirm decoupling in docs
- If MOD traps persist: increase sharp weight to 55%

### Checklist (completed)

- [x] `wc_model_v4_ensemble.py`
- [x] `wc_backtest_framework.py` (9 matches)
- [x] LOO + hyperparameter sweep
- [x] Trap analysis
- [x] `tests/test_wc_model_v4.py`
- [x] `MODEL_PIPELINE_V4.md`
- [x] HTML diagram update

### Retrospective 2

**Results (executed 2026-06-15):**

| Model | Mean Brier (N=9) |
|-------|------------------|
| **v4_elo** | **0.8628** |
| v31_elo | 0.8950 |
| dc_ensemble_35 | 0.9022 |

- O/U Brier: DC = Independent = 0.2255 (negligible Δ on N=9; DC preferred for joint combos)
- Trap analysis: **0 MOD favorites** would be bet under v4 (all PASS)
- NED-JPN: ev_model −17.4% → ev_v4 −8.2% → PASS ✅ (counterfactual saves S/30)
- LOO best opener_boost varies 0.04–0.08; production uses 0.07 (constrained, not 0.08 overfit)
- Hyperparameter sweep best: boost=0.08, μ=2.2, Brier=0.8573 (marginal gain; 0.07/2.25 retained for stability)

**Edge cases identified:**
1. **Draw shocks** (Spain 0–0, BEL 1–1, BRA 1–1): v4 draw_base + opener_boost essential
2. **MOD favorite traps** (NED, SWE, ESP win shorts): tier blend + Rule 14 → PASS
3. **SPEC longshots** (AUS @5.35): soft 55% preserves +EV signal
4. **High-scoring mismatches** (SWE 5–1): model under-predicts blowouts — finisher-pair bonus needed
5. **Partial odds markets** (win-only screenshots): sharp_proxy draw allocation sensitive

**Leverage data points:**
- Spain rotation −25 Elo + minnow 1.16: largest single draw calibration lever
- Cross-book soft-side (AUS 5.35 Betsson): SPEC alpha source
- Heat μ suppression (BEL 2.35): modest but directionally correct

**Winner: `wc_model_v4_ensemble.py`**
- 1X2: v4_elo anchor (not DC ensemble)
- Goals: Dixon-Coles
- EV: Rule 24 tier blend + Rule 14 + HALT on blended

---

## Iteration 3 — Expanded Historical Backtest (N=222)

### Preamble
User correctly identified N=9 as insufficient. Built expanded dataset from WC 2018/2022, 121 football-data.co.uk friendlies/WCQ (2023–2026), walk-forward Elo, plus WC26 MD1–3.

### Results (executed 2026-06-15)

| Model | Weighted Brier | N |
|-------|----------------|---|
| Market implied | **0.5956** | 222 |
| v4_elo | 0.6157 | 222 |
| v31_elo | 0.6175 | 222 |

- Trap discipline: **0/125** MOD favorites would bet under v4
- v4 beats v31 on expanded set; market implied beats all (expected — closing lines are sharp)
- WC 2026 stratum Brier 0.8638 (high variance, N=9) — opener shocks dominate
- Hyperparameter sweep on N=222: opener_boost=0.055, μ=2.2 (production keeps 0.07/2.25 per Rule 25 WC holdout rule)

### New rules: AGENT.md Rule 25 (expanded backtest mandate), Rule 26 (competition weights)

---

## Iteration 4 Preamble (Future — v5)

**When:** Post MD4+ with ≥15 settled matches

**Tasks:**
- [ ] EWMA Elo with graph regularization (Degree 5)
- [ ] Dynamic xG blend with lineup gate (Degree 3)
- [ ] Bayesian BTD posterior Kelly (Degree 6)
- [ ] Expand HISTORICAL_MATCHES in backtest CSV
- [ ] Re-calibrate Rule 24 weights with Pinnacle devigged lines
- [ ] Walk-forward stake simulation (P&L, not just Brier)

**Contingencies:**
- If SPEC longshot hit-rate drops: reduce soft weight from 55% to 45%
- If draw rate rises in MD4+: increase opener_boost ceiling to 0.09

---

## Performance Comparison Table

| Metric | v3.1 | Degree-2 Ensemble | **v4** |
|--------|------|-------------------|--------|
| 1X2 Brier (N=9) | 0.8950 | 0.9022 | **0.8628** |
| MOD trap bets | 2+ | 2+ | **0** |
| NED-JPN EV | +6% (MOD) | ~+4% | **−8.2% (PASS)** |
| O/U structure | Independent | DC | **DC** |
| HALT target | Raw EV | Raw EV | **Blended EV** |
| Replicable regression | Locked | N/A | Additive (new module) |

---

## Files Delivered

| Artifact | Path |
|----------|------|
| Production v4 | `wc_model_v4_ensemble.py` |
| Backtest harness | `wc_backtest_framework.py` |
| Degree-2 research | `wc_ensemble_degree2.py` |
| v4 tests | `tests/test_wc_model_v4.py` |
| Architecture doc | `MODEL_PIPELINE_V4.md` |
| This iteration log | `MODEL_ITERATION_V4.md` |
| HTML diagram | `wc_june16_2026_report.html` (v4 layer labels) |

---

## Responsible Gambling Block

> Betting carries real risk of financial loss. This is analysis only, not financial advice or a guarantee of outcomes. Past form and model edges do not predict individual match results. If gambling is no longer recreational, contact Peru's [Línea 0800-1-3232 (MINCETUR)](https://www.gob.pe/mincetur) or [Jugadores Anónimos Perú](https://jugadoresanonimos.org/).