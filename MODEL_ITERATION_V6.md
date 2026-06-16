# WCdecider Model Iteration v6 — Bayesian Search (6×5×2 Zoom)

**Date:** 2026-06-15 · **Subagents:** 30 (6 degrees × 5 version topologies) · **Harness:** `wc_bayesian_model_search.py`

---

## Iteration 5 Retrospective Preamble

v4.1 shipped with MOD 70/30 pre-stack. Remaining gap: no systematic Bayesian exploration of **workflow topology** across the six architectural alternatives. Iteration 6 runs Thompson-sampling zoom (5 seeds + 12 zoom per degree = 17 evals × 6 = **102 configs**) with composite objective:

\[
\text{score} = -\text{Brier} - 0.15 \cdot \text{traps} - 0.03 \cdot \text{shock\_brier} + 0.02 \cdot \text{spec\_signal}
\]

---

## Iteration 6 Preamble — Checklist

- [x] Build `wc_bayesian_model_search.py` with per-degree predictors + PARAM_BOUNDS
- [x] Define 5 seed topologies per degree (30 versions)
- [x] 2 zoom rounds × 6 Thompson samples per degree
- [x] Spawn 6 subagents (D1–D6) for deep analysis per alternative
- [x] Fix D4 trap eval to pass `mod_weights` into `eval_traps`
- [x] Save `wc_bayesian_search_results.json`
- [ ] Pinnacle validation before any production weight change (Rule 27)

---

## Cross-Degree Ranking (Best per Alternative)

| Rank | Degree | Best Config | Brier | Traps | Shock | Adopt? |
|------|--------|-------------|-------|-------|-------|--------|
| 1 | **D4** Tier topology | spec_soft60_zoom (MOD 38/45/17, SPEC 25/15/60) | **0.5967** | 0 | 1.217 | ⏳ Rule 27 block |
| 2 | **D2** DC + stack | global w≈0.47 | **0.5981** | 0 | 1.201 | ⏳ research only |
| 3 | **D3** xG surrogate | no_gate_w50 | 0.6155 | 0 | **1.066** | ⏳ v5 FBref |
| 4 | **D1** Variational | ob≈0.09, db≈0.21 | 0.6152 | 0 | 1.107 | ⏳ ob=0.08 compromise |
| 5 | **D6** Draw-band | band_pp=0.02 | 0.6155 | 0 | 1.103 | ✅ optional tweak |
| 6 | **D5** EWMA | wc_boost α≈0.14 | 0.6157 | 0 | 1.125 | ❌ no gain |

**Production unchanged:** `wc_model_v4_1_ensemble.py` — D2/D4 winners beat v4.1 on **prediction-level** Brier but sacrifice shock robustness or fail Rule 27.

---

## Degree 1 — Variational Elo+Poisson (5 Subagents)

### Seed topologies

| v | Label | ob | db | μ | Brier |
|---|-------|----|----|---|-------|
| v1 | prod | 0.07 | 0.20 | 2.25 | 0.6157 |
| v2 | wc_tune | **0.08** | 0.20 | 2.20 | 0.6154 |
| v3 | draw_heavy | 0.07 | 0.22 | 2.25 | 0.6160 |
| v4 | conservative | 0.06 | 0.18 | 2.30 | worst |
| v5 | timesplit | 0.055 | 0.18 | 2.20 | worst |

### Bayesian zoom winner
`ob=0.091, db=0.207` — Brier 0.6152, shock 1.107 (−0.017 vs prod on 6-match panel).

### Recommendation
**Partial adopt:** `opener_boost=0.08` (v2 compromise). Hold `draw_base=0.20`, `μ=2.25`. Do not jump to ob=0.09 without more Rule 21 opener samples (N=2).

---

## Degree 2 — Dixon-Coles + Stacking (5 Subagents)

### Seed topologies

| v | Topology | Brier | Shock | Notes |
|---|----------|-------|-------|-------|
| v2 | global50 | **0.5988** | 1.195 | Best seed |
| v5 | draw_shock ρ=-0.12 | 0.5999 | 1.188 | ρ inert without DC 1X2 |
| v1 | **v41 mod_only 70/30** | 0.6093 | **1.159** | Best shock among seeds |
| v4 | dc_blend | 0.6118 | 1.244 | Worst — do not ship |

### Bayesian zoom winner
`global stack w≈0.47` — Brier **0.5981** (Δ−0.0112 vs v41_prod).

### Recommendation
**Keep MOD-only 70/30.** Global stack wins Brier but worsens shock calibration. Research candidate: `D2-v2_global50` for closing-line calibration studies only.

---

## Degree 3 — xG Hybrid Surrogate (5 Subagents)

### Seed topologies

| v | gate | weight | Brier | Shock |
|---|------|--------|-------|-------|
| v1 | 400 | 0.30 | **0.6152** | 1.112 |
| v4 | 0 (always) | 0.50 | 0.6155 | **1.066** |
| v5 | 9999 (off) | 0.0 | 0.6157 | 1.123 |

Only **3/222** matches pass gate=400 — gated configs ≈ form_only.

### Recommendation
**Defer to v5** with real FBref xG. Surrogate confirms upset-direction signal but ΔBrier < 0.001 vs anchor. Start v5 search at gate=400, w=0.30.

---

## Degree 4 — Tier Ensemble Topology (5 Subagents)

### Seed topologies (prediction-level blend)

| v | MOD weights | Brier | NED-JPN EV |
|---|-------------|-------|------------|
| v1 | **Pin50/M30/S20 (prod)** | 0.5967 | −7.0% PASS |
| v2 | sharp55 | 0.5968 | −6.6% (weakest) |
| v3 | model35 | 0.5967 | −7.5% |
| v4 | spec_soft60 | 0.5966 | — |
| v5 | unified40 | 0.5971 | −8.0% |

### Bayesian zoom winner
MOD 38/45/17 + SPEC 25/15/60 — Brier 0.5967, traps=0.

### Rule 27 block
MOD model +8pp shift without Pinnacle validation → **cannot adopt**.

### Recommendation
**Retain Pin50/M30/S20.** Fix applied: D4 now passes `mod_weights` to trap eval for future sweeps.

---

## Degree 5 — EWMA Temporal Elo (5 Subagents)

### Seed topologies

All five seeds: **Brier 0.6157** (identical to v4_elo). Only `comp_boost_wc=True` breaks ties on shock.

True EWMA experiment (`wc_ewma_elo_experiment.py`, N=121): EWMA does **not** beat static snapshot.

### Recommendation
**Do not ship.** v5 needs date-honest chronological EWMA wired into Elo pre-match fields, not form-blend surrogate.

---

## Degree 6 — Bayesian Draw-Band Kelly (5 Subagents)

### Seed topologies

| v | draw_band_pp | Brier | Shock | MD2 loss saved |
|---|--------------|-------|-------|----------------|
| v3 | **0.02** | 0.6155 | 1.103 | S/51.67 |
| v1 | 0.03 (prod) | 0.6160 | **1.094** | **S/51.92** |
| v5 | 0.00 | 0.6157 | 1.123 | — |

### Recommendation
**Optional:** `draw_band_pp=0.02` (search winner) or keep 0.03 (best shock). `kelly_haircut=0.57` validated. NED-JPN → stake_cons=S/0.

---

## Composite Production Topology (v4.2 candidate — not shipped)

Synthesis of per-degree winners **subject to Rule 27**:

```
Layer 1: Elo anchor — ob=0.08, db=0.20 (D1 v2 compromise)
Layer 2: Goals — Dixon-Coles ρ=-0.07 (unchanged)
Layer 3: MOD EV — 70/30 model+market pre-stack (D2 prod, not global47)
Layer 4: Rule 24 — Pin50/M30/S20 (D4 prod, not zoom winner)
Layer 5: Stake — draw_band=0.02–0.03, kelly_haircut=0.57 (D6)
Layer 6: xG — none until v5 FBref (D3 deferred)
Layer 7: EWMA — none until v5 chronological (D5 deferred)
```

**Expected lift:** ob 0.07→0.08 may improve shock Brier ~1–2% on 6-match panel; aggregate Brier Δ < 0.001.

---

## Iteration 7 Preamble (Next)

**Tasks:**
- [ ] Ship v4.2 with `opener_boost=0.08` only if MD4+ openers validate
- [ ] Wire true Pinnacle devigged into D4 trap eval
- [ ] FBref xG pipeline for D3 re-search
- [ ] Chronological EWMA in loader for D5
- [ ] Walk-forward P&L sim with conservative Kelly caps

**Evals:**
- Re-run `python3 wc_bayesian_model_search.py` after each MD
- Rule 27 gate on any weight change >5pp
- WC strata Brier must not regress >0.005

---

## Run Instructions

```bash
python3 wc_bayesian_model_search.py           # all 6 degrees
python3 wc_bayesian_model_search.py --degree 2  # single degree
python3 wc_degree6_bayesian_kelly.py          # Kelly counterfactual
python3 wc_ewma_elo_experiment.py             # true EWMA N=121
```

---

## Responsible Gambling Block

> Betting carries real risk of financial loss. This is analysis only, not financial advice or a guarantee of outcomes. Past form and model edges do not predict individual match results. If gambling is no longer recreational, contact Peru's [Línea 0800-1-3232 (MINCETUR)](https://www.gob.pe/mincetur) or [Jugadores Anónimos Perú](https://jugadoresanonimos.org/).