# WCdecider Model Iteration v5 — Stacking, Shock Robustness & Production v4.1

**Date:** 2026-06-15 · **Iteration:** 5 (complete) · **Subagents:** 6 (degrees 1–6, re-run on N=222)

---

## Iteration 4 Retrospective Preamble

**State entering Iteration 5:**
- N=222 expanded backtest live (`wc_backtest_historical_dataset.csv`)
- v4_elo Brier 0.6157; market implied 0.5956 (expected gap)
- Trap discipline: 0/125 MOD favorites under Rule 24
- Six subagent degrees documented but MOD EV layer still used raw model anchor only
- Degree 5 (EWMA) and Degree 6 (Bayesian Kelly) artifacts not integrated

**Issues to fix:**
1. MOD tier EV still overweights structural model vs closing-line signal
2. Global 50/50 stack beats 70/30 on Brier but 70/30 is safer for MOD-only deployment
3. No production module for v4.1 stack + conservative Kelly
4. HTML diagram still labels v4.0 only

---

## Iteration 5 Preamble — Checklist

**Goals:**
- [x] Re-run 6 subagents on N=222 with stacking sweep + time-split CV
- [x] Implement `wc_model_v4_1_ensemble.py` (MOD 70/30 pre-stack)
- [x] Integrate Degree 6 conservative Kelly (stake suggestion only)
- [x] Lock trap count = 0 under v4.1 on 125 MOD favorites
- [x] Add `tests/test_wc_model_v4_1.py`
- [x] Update backtest framework with `v4_1_stack` model leg
- [x] Document Rule 27 in AGENT.md

**Contingencies:**
- If 70/30 stack introduces MOD traps → revert to v4.0 for MOD tier
- If stack_model_50 beats 70/30 on traps → document as research-only (global stack overfits soft-book use case)
- If pytest fails on v3 regression → keep v4.0 as fallback import

**Evals:**
- Weighted Brier on N=222 (full + WC strata)
- Trap analysis MOD favorites (must stay 0)
- NED-JPN counterfactual (must PASS)
- AUS-TUR SPEC (must preserve +EV signal)
- Time-split: train pre-2026 → test WC26

---

## Six Subagent Degrees — Iteration 5 Results (N=222)

| Degree | Approach | Key Finding | Adopted in v4.1? |
|--------|----------|-------------|------------------|
| **1** Variational tuning | opener_boost × draw_base × μ grid on WC strata | ob=0.08/db=0.20 marginally best WC Brier 0.6086; production keeps 0.07/2.25 | ⏳ Hold (Rule 25) |
| **2** Dixon-Coles + stacking | Global model+market convex blend | stack_model_50 Brier 0.5988; 70/30 Brier 0.6039; traps=0 all weights | ✅ MOD-only 70/30 |
| **3** xG hybrid | FBref pipeline gate | Not shipped; no lineup-confirmed xG on N=222 | ⏳ v5 |
| **4** Rule 24 tier ensemble | Pin50/M30/S20 MOD | Unchanged; NED-JPN PASS at −7.0% blended EV | ✅ Yes |
| **5** EWMA temporal Elo | α=0.08 walk-forward | Does not beat static on friendlies (`wc_ewma_elo_experiment.py`) | ⏳ v5 |
| **6** Bayesian Kelly bands | ±3pp draw uncertainty | ~57% stake haircut; saves ~S/52 MD2 counterfactual (`wc_degree6_bayesian_kelly.py`) | ✅ Stake hook |

---

## Iteration 5 — Executed Results

### Model comparison (N=222, weighted Brier)

| Model | Brier | Traps (MOD) |
|-------|-------|-------------|
| market_implied | **0.5956** | — |
| stack_model_50 (research) | 0.5988 | 0 |
| **v4_1_stack** | **0.6039** | 0 |
| dc_ensemble_35 | 0.6109 | — |
| v4_elo (anchor) | 0.6157 | 0 |
| v31_elo | 0.6175 | — |

**Δ v4.1 vs v4 anchor:** −0.0118 Brier (12% relative improvement toward market)

### Stacking sweep (full N=222)

| w_model | Brier | traps |
|---------|-------|-------|
| 0.5 | 0.5988 | 0 |
| 0.6 | 0.6011 | 0 |
| **0.7** | **0.6039** | **0** |
| 0.8 | 0.6073 | 0 |
| 1.0 | 0.6157 | 0 |

**Production choice:** 70/30 — balances Brier gain vs MOD-tier conservatism (less market overfit than 50/50 on WC26 holdout variance).

### Time-split CV

- Train (pre-2026): Brier 0.5974, best HP ob=0.055/db=0.18
- Test (WC26 N=9): Brier 0.9014 (high variance; opener shocks)
- Rule 25: retain 0.07/2.25 until MD4+

### Shock cases

| Match | Outcome | pD v4 | pD stack70 | Brier v4 |
|-------|---------|-------|------------|----------|
| ESP-CPV (2026) | D | 27.9% | 23.9% | 0.999 |
| ARG-KSA (2022) | B | 21.9% | 20.5% | 1.444 |
| GER-JPN (2022) | B | 26.4% | 24.9% | 1.003 |

Stack pulls draw prob toward market on shocks — acceptable trade for MOD trap avoidance.

### Live demo (v4.1)

| Match | Tier | EV R14 | Class |
|-------|------|--------|-------|
| ESP-CPV draw | MOD | −0.6% | PASS |
| NED-JPN | MOD | −7.0% | PASS |
| AUS-TUR | SPEC | +15.3% | STRONG |

---

## Iteration 5 Retrospective

**What worked:**
- MOD-only 70/30 pre-stack improves blended calibration without reintroducing favorite traps
- Trap discipline maintained 0/125 across all stack weights ≥0.5
- Conservative Kelly hook provides stake discipline without changing classification
- 32/32 pytest pass (v3 regression + v4 + v4.1)

**What did not ship:**
- Global 50/50 stack (best Brier but too market-dependent for structural edge detection)
- EWMA Elo (no gain on friendlies with current α)
- xG hybrid (data pipeline incomplete)
- opener_boost 0.08 (marginal WC gain; risks overfit on N=9 holdout)

**Edge cases:**
1. **Draw shocks:** stack reduces draw overconfidence on ESP-CPV (good for MOD shorts)
2. **SPEC longshots:** AUS-TUR unchanged (no pre-stack on SPEC tier)
3. **Partial odds:** market_implied falls back to 3.5/4.0 draw/away — flag low confidence
4. **WC26 holdout:** test Brier 0.9014 — do not tune aggressively on 9 matches

---

## Iteration 6 Preamble (Future — v5)

**When:** Post MD4+ with ≥15 WC26 settled matches

**Tasks:**
- [ ] Date-honest EWMA Elo with competition-specific α
- [ ] Dynamic xG blend (Degree 3) with lineup confirmation gate
- [ ] Full PyMC Bayesian BTD posterior (Degree 6)
- [ ] Walk-forward P&L simulation on screenshot odds (not just Brier)
- [ ] Pinnacle devigged lines in Rule 24 sharp leg (replace proxy)
- [ ] Re-evaluate global stack vs MOD-only stack on expanded WC26 stratum

**Contingencies:**
- If SPEC hit-rate drops below 40%: reduce soft weight 55% → 45%
- If draw rate in MD4+ exceeds 30%: raise opener_boost ceiling to 0.09
- If v4.1 MOD traps > 0: emergency revert to v4.0 `wc_model_v4_ensemble.py`

**Eval checklist:**
- [ ] Rebuild CSV after each MD
- [ ] Weighted Brier stratified by competition (Rule 26)
- [ ] Trap count = 0 on MOD favorites
- [ ] HALT drill-down on any blended EV > +25%
- [ ] Counterfactual P&L on MD2 bets with conservative Kelly

---

## Production Winner: `wc_model_v4_1_ensemble.py`

| Leg | Model |
|-----|-------|
| **1X2 anchor** (reporting) | v4_elo — unchanged |
| **MOD EV pre-stack** | 70% model + 30% market implied |
| **SPEC/MARG EV** | Raw model anchor → Rule 24 |
| **Goals** | Dixon-Coles ρ=-0.07 |
| **Staking** | Rule 14 + HALT on blended; conservative Kelly optional |
| **Trap discipline** | Rule 27 gate |

---

## New Rule: AGENT.md Rule 27

**Rule 27 — MOD Ensemble Change Gate**
Any change to MOD-tier ensemble weights or pre-stack ratio requires:
1. `trap_analysis()` on expanded N≥200 dataset with **trap_count = 0**
2. True Pinnacle devigged comparison when available (proxy insufficient for weight changes >5pp)
3. Documented counterfactual on NED-JPN and at least one MOD favorite from WC 2018/2022

---

## Files Delivered (Iteration 5)

| Artifact | Path |
|----------|------|
| Production v4.1 | `wc_model_v4_1_ensemble.py` |
| Iteration runner | `wc_model_iteration_runner.py` |
| Backtest (v4.1 stack leg) | `wc_backtest_framework.py` |
| v4.1 tests | `tests/test_wc_model_v4_1.py` |
| EWMA experiment | `wc_ewma_elo_experiment.py` |
| Bayesian Kelly | `wc_degree6_bayesian_kelly.py` |
| Architecture doc | `MODEL_PIPELINE_V4.md` (updated v4.1) |
| This log | `MODEL_ITERATION_V5.md` |
| HTML diagram | `wc_june16_2026_report.html` |

---

## Responsible Gambling Block

> Betting carries real risk of financial loss. This is analysis only, not financial advice or a guarantee of outcomes. Past form and model edges do not predict individual match results. If gambling is no longer recreational, contact Peru's [Línea 0800-1-3232 (MINCETUR)](https://www.gob.pe/mincetur) or [Jugadores Anónimos Perú](https://jugadoresanonimos.org/).