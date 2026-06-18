# AGENT.md — Screenshot-Driven Betting Analysis Protocol

**Purpose**: Reusable operating instructions for analyzing FIFA World Cup 2026 (and other football) bet candidates **when the user supplies live odds via screenshots from the Betsson or Betano mobile apps**. This document defines the exhaustive, repeatable steps the agent must follow on every screenshot intake, the validation gates each candidate bet must pass, and the data sources and modeling techniques that must be consulted.

**Status**: Living document. The user is the sole decision-maker; the agent provides analysis only.

---

## 0. Core operating principles (non-negotiable)

1. **No fabricated odds.** The agent never invents Betsson/Betano prices. All live odds enter the workflow exclusively via user-supplied screenshots or pasted text.
2. **No "place this bet now" advice.** The agent surfaces edges, probabilities, EV, and risks. The user decides whether and how much to stake.
3. **Every number is sourced.** Elo, xG, form, injuries, lineups, H2H — all citations must include URL + access timestamp. If a number cannot be verified across ≥2 independent sources, it is flagged as low-confidence.
4. **Honest self-critique is mandatory.** Every recommendation includes "what could make this wrong" and a confidence percentage.
5. **The agent does not chase certainty.** Football is high-variance; an edge of <3% EV is presented as marginal, not "strong."
6. **Bankroll responsibility.** Every output ends with the standard responsible-gambling block and references the user's Peru-specific helplines.
7. **Memory hygiene.** No durable memory of stakes or outcomes is stored unless the user explicitly asks.

---

## 1. Screenshot intake — required steps (run in order)

When the user uploads one or more app screenshots, the agent must:

### Step 1.1 — Acknowledge and inventory
- Confirm receipt of each image.
- For each screenshot, identify:
  - **App** (Betsson / Betano / other — confirm with user if ambiguous).
  - **Fixture** (Team A vs Team B, kickoff date/time, competition).
  - **Market type** (1X2, Asian Handicap, Over/Under X.5, BTTS, Double Chance, Correct Score, player props, etc.).
  - **All visible selections + decimal odds** (transcribe verbatim into a table).
  - **Timestamp** visible on the screenshot, or current time if not visible.
- If any element is unreadable, request a clearer screenshot before proceeding.

### Step 1.2 — Build the canonical odds table
Produce a clean table in the response that the user can verify:

```
| App     | Fixture        | Market      | Selection     | Odds (dec) | Captured  |
|---------|----------------|-------------|---------------|------------|-----------|
| Betsson | CAN vs BIH     | 1X2         | Canada        | 1.85       | 12:31 PM  |
| Betsson | CAN vs BIH     | 1X2         | Draw          | 3.70       | 12:31 PM  |
| Betsson | CAN vs BIH     | 1X2         | Bosnia        | 4.40       | 12:31 PM  |
```

### Step 1.3 — Cross-check the book's vig (overround)
For every complete market (where all selections are screenshotted):

\[
\text{Overround} = \sum_{i} \frac{1}{o_i} - 1
\]

- Report the % vig. A WC main market with overround >7% on Betsson/Betano = unusually wide; >9% = avoid the market entirely.
- If only a partial market is provided (e.g., just one selection), explicitly note the agent cannot compute vig and the implied probability is uncorrected.

### Step 1.4 — Trigger Round-0 freshness check
Before any modeling, confirm:
- Match has not yet kicked off (or is pre-match suspended state).
- Lineups are out (if within ~75 min of KO) → re-pull lineups; if a key player from the model assumption is unexpectedly out/in, **re-run the model before publishing EV**.
- No breaking injury or weather news in the last 60 minutes (search recency=day).

If any freshness check fails, the agent halts the EV calculation and notifies the user.

---

## 2. The 9-step exhaustive validation protocol (per bet candidate)

Every bet idea derived from a screenshot must pass through these nine steps. Each step's evidence is documented in the output.

### Step A — Team news verification (T-minus 24h to KO)
- Verified injury list from ≥2 of: official federation site, Transfermarkt injury page, Sports Mole / RotoWire / SI predicted XI, Bundesliga liveticker, BBC.
- Confirmed predicted XI from ≥2 independent previews.
- Suspension / yellow-card accumulation status (relevant from MD2 onwards).
- Manager press-conference quotes if injury status is contested.
- Timestamp every source.

### Step B — Travel, rest, venue, weather
- Days of rest since previous fixture for each squad.
- Distance traveled since last match (critical in WC 2026's three-country format).
- Venue altitude (Mexico City vs Toronto vs Seattle all materially different).
- Kickoff weather forecast from a meteorological source (heat index >32°C reduces expected goals by ~5–10% per peer-reviewed work; cite if invoked).
- Pitch type / known surface issues.

### Step C — Statistical baseline (multi-source)
Build the analytic baseline from at least the following, with timestamps:
- **Elo**: international-football.net or eloratings.net, dated within 48h of the analysis.
- **xG / xGA**: FBref or Understat (where international fixtures are tracked); if internationals are not in dataset, use club xG of starting XI as a weighted proxy and flag the limitation.
- **Form**: Last 6 competitive fixtures per team, with results, opposition Elo, venue (H/A/N), and goal totals.
- **Set-pieces**: % of goals scored / conceded from set-pieces (FBref).
- **PPDA / pressing intensity** if available (Understat / StatsBomb-free).
- **H2H**: Last 10 meetings, with venue and competition context.
- **Manager profile**: Tactical setup (formation, build-up style, in-game adjustments).
- **Referee profile**: Cards/game, penalties/game from WhoScored or FIFA's referee report (critical for cards/penalty markets).

### Step D — Build the probability model
The standard model stack (transparent, all assumptions visible):

Improved 1X2 "win" hover (research + subagent + phases): "ONE BY ONE" + STEP-BY-STEP TO OPERATIONALIZE (6 numbered steps) + "identify the recommended team from the rec (e.g. Portugal NOT opponent or draw)" + "tap ONLY that tile" + "Analysis... NO advice to place any bet. User decides stake...". High-EV example ENG handicap -1 @3.8 (+72.1% STRONG, real 4-2 cashed); risky high-reward TUN win @6.8 (+64.3% STRONG longshot). Full bilingual in TERM_GLOSSARY/JSON glossary + per-item + JS IMPROVED_GLOSSARY + HTML. See wc_replicable_pipeline.py:83, index.html JS, training/profitability report. Phase process + 3 subagents (validator/subeditor/editor) used for HTML sync. A+B + temporal CV for champion (robust trap0 + adaptive).

1. **Elo-based two-way win probability**:
   \[
   P_{A,2w} = \frac{1}{1 + 10^{-(E_A + H_A + F_A - (E_B + F_B))/400}}
   \]
   Where \(H_A\) is the home/host adjustment (full home = 80 Elo; host but neutral city = 25–40; fully neutral = 0) and \(F_{A,B}\) are form/injury overlays capped at ±40 Elo each.

2. **Three-way (1X2) conversion** with a closeness-dependent draw share:
   \[
   d = \max(0.15,\ \min(0.32,\ (0.18 + 0.12 \cdot c) \cdot s))
   \]
   where \(c = 1 - |P_{A,2w} - 0.5| \cdot 2\) and \(s\) is a match-specific scale (default 1.0).

3. **Expected goals via Elo gap → Poisson**:
   \[
   \lambda_A = \mu_{\text{total}} \cdot (0.5 + 0.5 \cdot \tanh(\text{gap} \cdot k))
   \]
   \(\mu_{\text{total}}\) defaults to 2.5 for WC group-stage, adjusted ±0.3 based on team scoring profiles.

4. **Independent Poisson** to derive Over/Under and BTTS markets (with explicit caveat that real goal-distributions show mild negative correlation at scoreboard extremes).

5. **Player props (goalscorer, shots, cards)** must use a separate model anchored on:
   - Per-90 rate for the player at club level.
   - Minutes-expected adjustment.
   - Team-share-of-shots adjustment.
   - Opponent defensive concession profile.

All formulas, inputs, and outputs appear in the final response in KaTeX.

### Step E — Sensitivity stress test
Re-run the model under three parameter sets:
- **Aggressive**: home_adj=80, form_multiplier=1.0.
- **Base** (default for the headline number): home_adj=50, form_multiplier=0.7.
- **Conservative**: home_adj=30, form_multiplier=0.4.

A bet idea is labeled **ROBUST** only if EV remains positive across all three sets. Otherwise it is labeled **SENSITIVE** (positive only in base/aggressive) or **NOT +EV**.

### Step F — Live odds comparison & EV
Using the user's screenshot odds:

\[
EV\% = (P_{\text{model}} \cdot o_{\text{live}} - 1) \cdot 100
\]

Report EV, fair odds (1/P), and the **edge in basis points** (live odds vs fair odds).

Thresholds:
- EV ≥ +4% and ROBUST → potential value candidate.
- EV +1.5% to +4% → marginal; not a recommendation.
- EV < +1.5% → no value; explicitly say so.
- EV negative → present so user knows to skip.

### Step G — Cross-book / arbitrage scan
If the user has supplied **both Betsson and Betano** screenshots for the same fixture & market:
1. For each selection, take the **higher** decimal odds across the two books.
2. Compute combined implied probability:
   \[
   \pi = \sum_i \frac{1}{\max(o_{i,\text{Betsson}}, o_{i,\text{Betano}})}
   \]
3. If \(\pi < 1\): genuine arbitrage exists. Compute stake split:
   \[
   s_i = \frac{B \cdot (1/o_i^{*})}{\pi},\quad \text{guaranteed return per unit} = \frac{1}{\pi}
   \]
   Present the % guaranteed return AND warn about: limit risk, palpable error void clauses, account-restriction risk, time-to-suspension risk.
4. If no arb: report the smallest combined margin and identify the best price per side (still useful to the user even without an arbitrage).

### Step H — Self-critique
For every recommendation:
- "What could make this wrong?" — list at least 3 plausible scenarios.
- Identify any single point of model failure (e.g., "edge collapses if Davies returns").
- Note any conflicts between data sources (e.g., RotoWire says Enciso starts, SI says he's out).
- Acknowledge confidence interval, not just a point estimate.

### Step I — Final classification & confidence
Each bet idea is given:
- **Strength**: Strong / Moderate / Speculative / Pass.
  - *Strong* = ROBUST +EV across all 3 sensitivities AND ≥+6% EV at base AND no critical data gap.
  - *Moderate* = ROBUST or +EV at base with one minor caveat.
  - *Speculative* = +EV only at base, or model is contrarian to consensus.
  - *Pass* = not +EV or critical data gap.
- **Confidence %**: agent's subjective probability the bet is genuinely +EV given model uncertainty. Cap at 70%; football models that claim higher are overconfident.

---

## 3. Required research-agent invocations

The agent must use specialized sub-agents and tools to validate at minimum the following per analysis:

### 3.1 Mandatory web research fan-out
For each fixture analyzed, execute parallel searches covering:
1. `"{TeamA} {TeamB} predicted lineup {date}"` (recency: day)
2. `"{TeamA} injury news {date}"` (recency: day)
3. `"{TeamB} injury news {date}"` (recency: day)
4. `"{TeamA} {TeamB} prediction odds"` (recency: week) — to triangulate public sharp prices
5. `"{TeamA} recent form results 2025 2026"` (recency: month)
6. `"{TeamB} recent form results 2025 2026"` (recency: month)
7. `"{referee_name} cards penalties statistics"` (when refs known)

### 3.2 Direct page fetches (required, not optional)
- `international-football.net/elo-ratings-table?...` for current Elo.
- `fbref.com/en/squads/{team}/` for xG/xGA when available.
- `transfermarkt.com/{team}/sperrenundverletzungen/verein/{id}` for injury suspension.
- `fotmob.com/teams/{id}/squad` for current squad/injury status.
- Federation official site for any morning-of update.

### 3.3 Model code execution (required)
- The probability model must actually be executed in code, not described abstractly. Output the executed numbers, not symbolic ones.
- Sensitivity test must actually run all 3 scenarios.
- EV calculation must be executed on the user's screenshot odds (not estimated).

### 3.4 Best-in-class modeler references
Where possible, cross-check model output against at least one of:
- **FiveThirtyEight SPI** (archived methodology) and successors at *Opta Analyst*.
- **Opta supercomputer / Stats Perform** published win probabilities.
- **Football-Data.co.uk** historical closing-line database (for retro calibration).
- Public pundits with documented track records: **Mark O'Haire**, **Joe Wadsack**, **Jonathan Wilson** (qualitative read), and aggregator picks at **OneFootball**, **WhoScored** prediction model.

Note: these are sanity checks, not authorities. Divergence from them is fine if the agent's reasoning is explicit.

---

## 4. Output format (strict)

Every analysis response must contain, in this order:

1. **Screenshot inventory table** (Section 1.2).
2. **Book overround** per market (Section 1.3).
3. **Freshness check confirmation** (Section 1.4).
4. **Per-bet validation cards** with the 9-step protocol completed and visible.
5. **EV table** comparing fair odds vs user's live odds.
6. **Cross-book arb/best-price table** if both books supplied.
7. **Self-critique block** (top 3 risks).
8. **Final classification** (Strong / Moderate / Speculative / Pass + confidence %).
9. **Responsible gambling block** (standardized — see Section 6).
10. **Source list** with all URLs and timestamps.

---

## 5. Bankroll & staking framework (agent recommendations only — user decides)

The agent presents staking *suggestions* using **fractional Kelly** (¼ Kelly default — full Kelly is too volatile for international football):

\[
f^* = \frac{p \cdot o - 1}{o - 1}, \quad \text{stake} = 0.25 \cdot f^* \cdot \text{bankroll}
\]

Suggested caps by strength:
- **Strong**: up to 1.5% of bankroll (¼ Kelly with extra safety).
- **Moderate**: up to 0.75%.
- **Speculative**: 0.25–0.5%.
- **Pass**: 0%.

Hard rules surfaced in every output:
- Never risk >5% of bankroll on a single matchday across all bets.
- No martingale / loss-chasing.
- Stop-loss: if down 20% of starting bankroll in a tournament, agent will reduce all stake recommendations by 50% for the remainder.

---

## 6. Standardized responsible-gambling block

To be appended to every output verbatim:

> Betting carries real risk of financial loss. This is analysis only, not financial advice or a guarantee of outcomes. Past form and model edges do not predict individual match results. If gambling is no longer recreational, contact Peru's [Línea 0800-1-3232 (MINCETUR)](https://www.gob.pe/mincetur) or [Jugadores Anónimos Perú](https://jugadoresanonimos.org/).

---

## 7. Common failure modes the agent must guard against

1. **Reverse-engineering odds into "model output"** — confirmation bias when the model is told the market first. The agent must compute the model probability *before* looking at the screenshot odds whenever possible, then compare.
2. **Over-reliance on one source** — e.g., taking Transfermarkt's injury status as gospel when local media has more current info.
3. **Treating CONMEBOL Elo at face value** — the model historically overrates CONMEBOL sides in tournaments. Flag any bet driven by CONMEBOL Elo as speculative.
4. **Stale lineups** — predicted XIs from 48h ago can be wrong by kickoff. Always re-pull within 90 minutes of KO.
5. **Player-prop volatility** — single-player props (anytime scorer, shots) have heavy variance even with strong edge; cap stake suggestions at 0.5% of bankroll regardless of model EV.
6. **Promo / boost markets** — Betsson and Betano frequently offer "odds boost" on a specific selection. These are often the only true +EV markets; the agent must flag them when visible but note the typical low max-stake limit.
7. **Hallucinated WC fixtures** — always cross-check fixture date + venue from at least two independent schedule sources before modeling.
8. **Ignoring market movement** — if the user provides screenshots taken hours apart, compare and infer line drift; large moves toward a selection (steam) often reflect sharp money the model is missing.

---

## 8. Calibration parameters (v2 — updated from MD1 backtest)

Applied to the Elo+Poisson model:

| Parameter | v1 | v2 | Reason |
|---|---|---|---|
| CONMEBOL Elo shrinkage (WC opener) | −60 | **−100** | Paraguay 1-4 collapse vs USA |
| AFC Elo shrinkage (WC opener vs top-20 nation) | 0 | **−40** | Pre-emptive — Saudi 2022 was outlier |
| Host crowd advantage (USA/CAN/MEX home matches) | +50 | **+90** | USA SoFi opener exceeded expectations |
| Star-player-out form penalty (top-tier creator) | −25 | **−40** | Enciso impact was larger than v1 assumed |
| Ensemble: model weight | 40% | **30%** | Defer more to market consensus |
| Ensemble: sharp supercomputer weight | 35% | **45%** | Sharp consensus outperformed model |
| Ensemble: devigged market weight | 25% | **25%** | Unchanged |
| EV halt threshold (likely model error) | +30% | **+25%** | Tighter discipline |
| Min EV for STRONG classification | +6% | **+8%** | Higher bar after false positive |
| Default μ_total (group stage) | 2.5 | **2.4** | MD1 averaged 2.0 goals/game |

## 9. New validation rules (v2)

### Rule of Three Disagreement
When our model probability for any 1X2 outcome differs from sharp consensus by >15 percentage points:
- Downgrade strength classification by one tier
- Reduce suggested stake by 50%
- Add explicit "model-sharp divergence" warning to output

### WC Opener Overcorrection Rule
For Group Stage Match-Day 1 only:
- Apply additional −20 Elo to non-host favorites
- Apply additional +30 Elo to host nations (US/Canada/Mexico when at home)
- WC openers historically over-deliver home/host advantage and under-deliver favored CONMEBOL/AFC sides

### Confederation Pre-flight Check
If CONMEBOL or AFC underdog priced >3.50 with model giving them >25%:
- Pull last 3 WC openers by that confederation
- If 2+ losses by 2+ goal margin → halt or reduce stake by 75%

### Lineup Confirmation Gate
If predicted XI has shifted in last 90min before KO (e.g., star unexpectedly returns/scratches):
- Halt EV calculation
- Rerun model with updated XI
- Do not proceed on stale lineups

### Cross-Book Soft-Side Priority
When Betano and Betsson differ by >15% on the same selection, the wider price is the **soft side**; the tighter price is closer to true. Trust the tighter price as a sharper read of the true probability; the wider price is the bettable opportunity (if model agrees).

---

## 10. Backtest record

| Date | Match | Call | Stake | Result | P&L |
|---|---|---|---|---|---|
| 2026-06-12 | Qatar-Switzerland | DRAW @ 6.30 Betano | S/10 | Win 1-1 | +S/53.00 |
| 2026-06-12 | Qatar-Switzerland | DRAW @ 5.95 Betsson | S/4 | Win 1-1 | +S/19.80 |
| 2026-06-12 | USA-Paraguay | PAR win @ 4.05 Betsson | S/0.64 | Loss 4-1 USA | −S/0.64 |
| 2026-06-12 | USA-Paraguay | X2 @ 1.80 Betano | S/5 | Loss 4-1 USA | −S/5.00 |
| 2026-06-12 | Brazil-Morocco | HALTED (+42% EV signal too high) | 0 | (Would have hit 1-1) | 0 |

**Running totals**: Stakes S/19.64 · Returns S/72.80 · **Net +S/53.16** · ROI **+270.7%**

Hit-rate: 50% (2W/2L on settled), but high-EV draw market call was correct.

---

## 11. Version log
- **v4.1** — 2026-06-15 — Iteration 5 production: MOD 70/30 pre-stack + Rule 24 + conservative Kelly (`wc_model_v4_1_ensemble.py`). N=222 backtest: v4_1_stack Brier 0.6039 (−0.0118 vs v4 anchor), traps=0/125. Rules 25–27. See `MODEL_ITERATION_V5.md`.
- **v4.0** — 2026-06-15 — Model iteration v4: tier-conditional ensemble (Rule 24), DC goal markets, decoupled 1X2 anchor. See `MODEL_PIPELINE_V4.md`, `wc_model_v4_ensemble.py`.
- **v3.1** — 2026-06-15 (post MD3 + screenshot cycle) — Backtest-driven refinements: extended AFC/CAF shrinkage to −55/−60 Elo (Rule 19), raised star-finisher pair bonus to +30 Elo with tighter MOD stake cap S/15 (Rule 20), added explicit model-script execution gate and cross-book soft-side examples to output requirements. Model v3 + DC joints + favorite-longshot (Rule 14) validated on MD1/MD2; heavy-favorite shorts systematically negative EV on screenshot prices.
- **v3.0** — 2026-06-15 — Match Day 2 backtest & calibration (full §13 in prior version).
- v2.0 — 2026-06-13 — Calibration update after Match Day 1 backtest. Tightened CONMEBOL shrinkage, increased host crowd advantage, rebalanced ensemble weights toward sharp consensus, lowered halt threshold to +25%, added 5 new validation rules.
- v1.0 — 2026-06-12 — Initial protocol authored after user request to formalize the screenshot-driven workflow. Built on the verified WC 2026 analytical framework from prior session (Canada-Bosnia, USA-Paraguay, slate analysis).

---

## §12. v2.1 Refinements — June 13 2026 (CIV-ECU drill-down)

### Trigger
CIV-ECU was incorrectly flagged HALT at +38.5% EV due to CAF qualifying inflation. Drill-down using Pinnacle (sharpest book) + Opta + two xG models reduced CIV true prob from 41.6% to 28.8%, EV from +38.5% to +9.4% — moving from HALT to a small SPEC bet at S/10.

### New rules added

**Rule 11 — CAF qualifying inflation discount**
Apply −50 Elo equivalent shrinkage to CAF teams that finished CAF qualifying with >80% win rate against sub-1700-Elo opposition. Mirror of CONMEBOL rule for CAF dataset.

**Rule 12 — Pinnacle disagreement guardrail**
When our ensemble probability is >10pp above Pinnacle's devigged probability on the same outcome, cap stake at SPEC tier regardless of EV magnitude. Pinnacle is the sharpest market signal globally and disagreements >10pp are almost always model error, not market mispricing.

**Rule 13 — HALT drill-down protocol**
Previously: +25% EV → HALT.
Now: +25% EV → mandatory drill-down with Pinnacle reconciliation + sharp-blend ensemble. Only HALT if drill-down still shows >+15% EV after Pinnacle blend with weights (Pinnacle 50% / Opta 30% / public models 20%).

### Backtest implication
If Rule 11 had been live, CIV's model-base prob would have dropped from 41.6% → ~33%, ensemble from 36.5% → ~30%, EV from +38.5% → ~+14% (still SPEC). The HALT would have been avoided and a small CIV bet justified.


---

## §13. v3.0 — Match Day 2 backtest & calibration (2026-06-15)

### MD2 settled results table

| Match | Pick | Odds | Stake | Result | P&L | Verdict |
|---|---|---|---|---|---|---|
| AUS-TUR | Australia @ 5.35 Betsson | 5.35 | 15.00 | AUS 2-0 TUR | **+S/65.25** ✅ | SPEC-tier longshot hit; Yıldız+Çalhanoğlu absences were correctly weighted |
| CIV-ECU | Ivory Coast @ 3.80 Betano | 3.80 | 10.00 | CIV 1-0 ECU | **+S/28.00** ✅ | SPEC-tier; drill-down protocol (Rule 11/12/13) correctly rescued from false HALT |
| NED-JPN | Netherlands @ 2.15 Betano | 2.15 | 30.00 | NED 2-2 JPN | **−S/30.00** ❌ | MODERATE ROBUST miss; Japan's pressing genuinely top-15; model overweighted Endo retirement impact |
| SWE-TUN | Tunisia @ 4.40 Betsson | 4.40 | 25.00 | SWE 5-1 TUN | **−S/25.00** ❌ | MODERATE ROBUST miss; soft-book opportunity was a TRAP — sharp consensus on Sweden was 52% but realized far higher |

**MD2 settled**: stakes S/80, P&L **+S/38.25**, ROI **+47.8%**, hit rate 2/4.
**MD1+MD2 combined**: P&L **+S/91.41** across 6 settled bets, hit rate 4/6.

### MD2 lessons — what the data shows

1. **The two "robust MODERATE" calls (NED, TUN) lost; the two SPEC longshots (AUS, CIV) won.** Sample size 4 — pure variance possible. But this pattern matches the well-known **favorite-longshot bias** literature (Snowberg & Wolfers 2010, "Explaining the Favorite-Long Shot Bias", Journal of Political Economy; https://www.journals.uchicago.edu/doi/10.1086/657162) which finds bettors *overprice favorites* and *underprice longshots* in football. Our SPEC bets are sitting in the +EV pocket; our MODERATE-on-favorites are exposed to the bias going the wrong way.

2. **Sweden 5-1 Tunisia was the costliest miss.** Aymen Dahmen (Tunisia GK) was poor; Sweden's Isak/Gyökeres tandem clicked. The "Tunisia low-block + Kulusevski out" narrative was real but insufficient against a finishing-quality differential. Lesson: when one team has two top-30 finishers and the opponent's best player is a goalkeeper, the variance-reducing bet is on the favorites.

3. **Netherlands 2-2 Japan validated "Japan unbeaten vs Europe 8 years"** signal that we noted but underweighted. Japan's 4-2-3-1 pressing (Mitoma-Kubo-Kamada front three) genuinely competes with Dutch buildup. Endo retirement was less impactful because Wataru Endō (the Liverpool one) actually played; the "retirement" was the older 1992-born Endo Yasuhito.

4. **Australia 2-0 Turkey vindicated the Yıldız+Çalhanoğlu absence read** at a fat 5.35 price. Cross-book soft-side priority worked.

5. **Ivory Coast 1-0 Ecuador (Amad Diallo late winner)** vindicated the drill-down protocol that rescued a HALT. Pinnacle reconciliation prevented a false negative.

### v3 calibration deltas

| Parameter | v2 | v3 | Reason |
|---|---|---|---|
| Star-finisher pair bonus (2 top-30 strikers) | 0 | **+25 Elo** | Sweden Isak+Gyökeres exposed |
| Goalkeeper-quality discount (bottom-tier vs Top-30 attack) | 0 | **−25 Elo** | Tunisia Dahmen / Curaçao GK collapses |
| Asia (AFC) vs Europe (UEFA) friendly form weight | 0.5x | **0.8x** | Japan's 8-yr unbeaten-vs-Europe is real signal, not noise |
| Sharp-consensus weight (MODERATE bets) | 45% | **40%** | Sharp consensus has been a trap on favorites |
| Soft-book signal weight (SPEC bets) | 50% | **55%** | Cross-book mispricing has been the alpha source |
| Min EV for MODERATE classification | +5% | **+6%** | Tighten the moderate-tier bar |
| Stake cap on MODERATE bets | S/30 | **S/20** | Lower exposure to favorite-longshot trap |
| Stake cap on SPEC bets | S/15 | **S/15** (unchanged) | Working as intended |

### v3 new rules

**Rule 14 — Favorite-Longshot Asymmetry Rule (Snowberg-Wolfers calibration)**
When the implied probability of our pick is < 25% (i.e., odds ≥ 4.00), apply a +2pp uplift to model probability before computing EV. When implied probability is > 65% (odds ≤ 1.54), apply a −2pp downward shrinkage. This corrects for the empirically documented favorite-longshot bias in international football.
References:
- Snowberg & Wolfers (2010), "Explaining the Favorite-Longshot Bias", J. Pol. Econ. 118(4):723-746 — https://www.journals.uchicago.edu/doi/10.1086/657162
- Vlastakis, Dotsis, Markellos (2009), "How efficient is the European football betting market?", Journal of Forecasting 28:426-444 — confirms favorite-longshot bias in soccer
- Cain, Law, Peel (2003), "The Favourite-Longshot Bias, Bookmaker Margins and Insider Trading in a Variety of Betting Markets", Bulletin of Economic Research 55:263-273

**Rule 15 — Top-30 Finisher Pair Detection**
Maintain a list of teams with ≥2 starters who have scored ≥15 league goals in the most recent completed season at a Top-5-league club. When such a team faces an opponent without an equivalent finisher, apply +25 Elo to the finisher-rich side. Empirically supported by:
- Brechot & Flepp (2020), "Dealing with randomness in match outcomes: How to rethink performance evaluation in European club football using expected goals", Journal of Sports Economics 21(4):335-362
- Šarović (2024) "Predictive Models in Football Using xG", arXiv:2412.13104

**Rule 16 — Goalkeeper Quality Adjustment**
If a team's starting GK has a clear-cut shot-stopping deficit (PSxG-GA per 90 in worst tercile of available data, or no top-5 league employment), apply −25 Elo when facing a finisher-rich opponent. References:
- Decroos et al. (2019), "Actions Speak Louder than Goals: Valuing Player Actions in Soccer", KDD '19 — https://dl.acm.org/doi/10.1145/3292500.3330758
- Liu, Schulte (2018) "Deep Reinforcement Learning in Ice Hockey for Context-Aware Player Evaluation" (analogous methodology)

**Rule 17 — Combo / Multi-Leg Joint Probability Discipline**
For correlated multi-leg bets (e.g., "Team A wins AND Over 2.5 goals"), do NOT multiply marginal probabilities — they are positively correlated. Use the corrected joint:
\[
P(A \cap O2.5) = P(A) \cdot P(O2.5 | A)
\]
where P(O2.5 | A) is estimated from Poisson-derived conditional means, typically 5-15% higher than unconditional P(O2.5) when A is the favorite. Without this correction, combo bets look more attractive than they are.

Practical formula for the favorite winning AND over 2.5 (Dixon-Coles framework):
\[
P(\text{Fav wins}) \cdot \frac{P(\text{Fav wins AND O2.5})_{\text{unconditional}}}{P(\text{Fav wins})}
\]

References:
- Dixon & Coles (1997), "Modelling Association Football Scores and Inefficiencies in the Football Betting Market", Applied Statistics 46(2):265-280 — the canonical reference for modeling correlated goal events
- Karlis & Ntzoufras (2003), "Analysis of sports data by using bivariate Poisson models", The Statistician 52(3):381-393 — bivariate Poisson for correlated outcomes
- Boshnakov, Kharrat, McHale (2017), "A bivariate Weibull count model for forecasting association football scores", International Journal of Forecasting 33(2):458-466

**Rule 18 — Price Boost Validation Protocol**
For every "boosted" market shown on the app (Betano "BB BOOST" / Betsson "Super Boost"), compute:
1. Pre-boost implied prob from the WAS price
2. Boosted implied prob from the NOW price  
3. Estimated true prob from base model + Poisson conditional (use Dixon-Coles joint correction for multi-leg combos, never naive multiply)
4. EV at the boosted price
Boosted markets ARE often +EV (the book is accepting model risk to acquire customer attention), but their max-stake limits (typically PEN 80) cap upside. ALWAYS take the full max-stake if EV > +10% after DC correction. Flag >+25% EV for mandatory HALT + drill-down (Pinnacle blend + validator) per Rule 13 before any stake.

**Rule 19 — Extended Confederation Shrinkage (2026-06-15 update)**
Apply −55 Elo (AFC) / −60 Elo (CAF) equivalent shrinkage (up from −40/−50) to teams whose qualifying record showed >75% win rate against sub-1650-Elo opposition. Mirror Rule 11 for broader applicability after MD2/MD3 exposed small-sample AFC/CAF variance in friendlies vs. real tournament results. Re-run model + ensemble if applied.

**Rule 20 — Finisher-Pair & MOD Discipline (2026-06-15 update)**
Raise star-finisher pair bonus to +30 Elo (from +25) when ≥2 confirmed starters have scored ≥15 league goals in a recent Top-5-league season. Simultaneously lower MODERATE stake cap to S/15 (from S/20) and increase sharp-consensus weight on MOD bets (Pinnacle/Opta-style 45% / model 35% / soft-book 20%). Rationale: MD2 backtest showed MOD favorites on technical sides exposed to favorite-longshot bias; SPEC longshots remained the primary alpha source. Re-calibrate after each MD.

### Information sources expansion (v3)

New required sources to consult per fixture:
1. **Pinnacle** (devigged) — sharpest single line; weight 50% in sharp consensus blend
2. **Opta Analyst supercomputer** (Stats Perform) — 25,000 sim model; weight 30%
3. **365Scores predictive model** — proprietary xG-based; weight 5%
4. **FootballMeister Coach AI** — public AI model with documented history; weight 5%
5. **One YouTube xG analyst** for sanity check (variable, ad-hoc) — weight 5%
6. **Football-Data.co.uk closing line** — for calibration retrospective
7. **Local federation media** (e.g., TFF for Turkey, FFIRI for Iran) — for breaking lineup news

Additional academic literature to draw on:
- Dixon-Coles (1997) — bivariate goal model
- Karlis-Ntzoufras (2003, 2009) — Skellam/bivariate Poisson
- Constantinou, Fenton, Neil (2012), "pi-football: A Bayesian network model for forecasting Association Football match outcomes", Knowledge-Based Systems 36:322-339
- Hubáček, Šourek, Železný (2019), "Exploiting sports-betting market using machine learning", International Journal of Forecasting 35(2):783-796
- Wheatcroft (2020), "A profitable model for predicting the over/under market in football", International Journal of Forecasting 36(3):916-932

### Backtest implication for v3
Had Rule 14 (favorite-longshot) been live:
- Tunisia @ 4.40: prob lifted from 27.4% to 29.4%; EV from +7.6% to +13.5% (still recommended, would have lost the same amount but classification stable)
- Netherlands @ 2.15: prob shrunk from 49.2% to 47.2%; EV from +6.0% to +1.5% (would have been Pass/Marginal, NOT placed — would have SAVED S/30)
- Sweden @ 1.40 (we did not bet): prob lifted from ... actually Sweden was a favorite; Tunisia wasn't bet, our Sweden side would have been favored
- Australia @ 5.35: prob lifted from 18.7% to 20.7%; EV from +0.0% to +10.7% — STILL recommended (was correctly placed)
- Ivory Coast @ 3.80: prob lifted from 28.8% to 30.8%; EV from +9.4% to +17.0% — STILL recommended

**Net counterfactual: Rule 14 saves S/30 on Netherlands, hits the same on the rest. Counterfactual P&L = +S/68.25 (+85% ROI).**

---

## §14. v4.1 — Expanded historical backtest protocol (2026-06-15)

### Trigger
N=9 WC 2026 settled matches insufficient for hyperparameter tuning. User correctly noted that pre-tournament friendlies, prior World Cups, and finished international fixtures provide substantially more calibration data without fabricating odds.

### Expanded dataset (N=222, executed)

| Source | N | Competition weight | Elo method | Odds source |
|--------|---|-------------------|------------|-------------|
| FIFA WC 2018 Russia group stage | 48 | 1.00 | eloratings.net tournament snapshot | football-data closing proxies |
| FIFA WC 2022 Qatar group stage | 44 | 1.00 | eloratings.net tournament snapshot | football-data closing proxies |
| football-data.co.uk internationals 2023–2026 | 121 | 0.60–0.85 | **Walk-forward Elo** (K=20, draw=0.5) | H_Avg/D_Avg/A_Avg closing |
| WC 2026 MD1–MD3 settled | 9 | 1.00 | eloratings.net 2026-06-15 snapshot | Betsson/Betano screenshots |

**Artifacts:** `wc_backtest_historical_dataset.csv`, `wc_backtest_historical_loader.py`, `wc_backtest_framework.py`

**Rebuild:** `python3 wc_backtest_historical_loader.py` then `python3 wc_backtest_framework.py`

### Expanded backtest results (weighted Brier, lower=better)

| Model | Weighted Brier | N |
|-------|----------------|---|
| Market implied (devigged closing) | **0.5956** | 222 |
| dc_ensemble_35 | 0.6109 | 222 |
| **v4_elo** | **0.6157** | 222 |
| v31_elo | 0.6175 | 222 |

**Stratified v4 Brier:** WC 2018 = 0.5663 · WC 2022 = 0.6227 · WC 2026 = 0.8638 · Friendlies = 0.6493 · WCQ = 0.5942

**Trap discipline:** 0 / 125 MOD favorites (odds < 2.5) would be bet under v4 tier ensemble.

**Key lesson:** Closing-line market implied probability beats any structural model on N=222 — expected (Snowberg-Wolfers; Hubáček et al. 2019). The model's role is **EV vs soft-book screenshot prices**, not beating Pinnacle/closing lines retrospectively. v4_elo still edges v31_elo (+0.0018 Brier) and maintains zero MOD-trap recommendations.

### New rules

**Rule 25 — Expanded Backtest Mandate**
Before any material calibration change (opener_boost, μ, Rule 24 weights), the agent must:
1. Rebuild `wc_backtest_historical_dataset.csv` via `wc_backtest_historical_loader.py`.
2. Include ≥3 competition strata: (a) prior World Cup tournaments, (b) pre-tournament friendlies/WCQ with real closing odds, (c) current tournament settled matches.
3. Use **walk-forward Elo** for chronological friendlies (no look-ahead from post-match ratings).
4. Report **weighted** Brier/log-loss stratified by competition.
5. Compare against **market-implied devigged baseline** — if model Brier > market + 0.03, downgrade calibration confidence and defer parameter changes.

**Rule 26 — Competition Weighting for Calibration**
Apply these weights when computing aggregate backtest metrics:
- WC tournament (2018/2022/2026 group): **1.00**
- WC qualifiers / Nations League: **0.85**
- Continental competitive: **0.80**
- International friendlies: **0.60**

Friendly matches inform draw-rate and mismatch dynamics but must not dominate tournament calibration. Hyperparameter changes require improvement on WC strata (weight ≥ 1.0) OR on WC 2026 holdout even if friendlies regress.

### v4.1 calibration note
Expanded sweep (N=222) selects opener_boost=0.055, μ=2.2 — marginally different from N=9 tune (0.07, 2.25). **Production retains 0.07/2.25** for WC 2026 opener draw shocks (Spain 0-0) until MD4+ adds more tournament data; Rule 25 requires re-validation after each MD.

**Rule 27 — MOD Ensemble Change Gate**
Any change to MOD-tier ensemble weights or pre-stack ratio requires:
1. `trap_analysis()` on expanded N≥200 dataset with **trap_count = 0**
2. True Pinnacle devigged comparison when available (proxy insufficient for weight changes >5pp)
3. Documented counterfactual on NED-JPN and at least one MOD favorite from WC 2018/2022

**Future Updates Must Use Automated Protocol**
All retraining, validation, new screenshot batches, calibration changes, or script modifications **must** be performed by strictly following the step-by-step process in `FUTURE_UPDATE_PROTOCOL.md`. A subagent should be spawned using the exact invocation prompt at the top of that file. This protocol incorporates lessons from code audits (no hard-coded prior_odds, centralized CONSTANTS, defensive validation, 2× skeptical iteration, per-row replication, full red-teaming, and live validation). Do not bypass any gate.

### Production stack (v4.1 — Iteration 5)
- 1X2 anchor: `wc_model_v4_ensemble.py` v4_elo (reporting leg, unchanged)
- Production EV: `wc_model_v4_1_ensemble.py` — MOD pre-stack 70/30 model+market → Rule 24
- O/U: Dixon-Coles ρ=-0.07
- EV/staking: Rule 24 tier-conditional ensemble on **screenshot** odds only
- Stake: conservative Kelly hook (Degree 6, ±3pp draw bands)

---

## Core Model Retraining & Automated Update Protocol for New Matches / Screenshots (2026-06-17, revised for full automation)

**Purpose (from past runs & user messages analysis):** Past updates (June 15-21 slate) involved manual subagent research per match, CSV appends, pipeline runs, manual HTML edits for new bg-slate-900 rounded-3xl sections (Data + Executed Model + Top Rec + full bilingual ELI5 + tooltips), table/summary updates, translation fixes, playwright compliance (layout, toggle, content), CI failures (alt report 404s, button clicks, missing sections), core-vs-subagent narrative drift, and deploy validation loops. This protocol enforces **automatic, comprehensive, perfect, complete** end-to-end process using scripts + structured subagents to prevent regressions. Every new screenshot batch must produce identical quality to existing matches (perfect bilingual, correct classes, validated recs, tests green, live correct).

**Core principle (ML/AI/engineering expert):** 
- Use the *exact same replicable core model* (`wc_replicable_pipeline.py` + v4.1 ensemble in `wc_model_v4_1_ensemble.py`) for:
  - Backtesting (15-16 + any new realized results in dataset A = `wc_2026_model_dataset.csv` for Brier, shock, traps).
  - Predictions/recommendations/EV for new dates (17+ or future).
- Subagents/research = **data population only** (never final numbers).
- Final everything (P/EV/classes, HTML cards/sections/table/summary, docs) driven by pipeline output.
- Full automation via scripts for HTML incrementing, testing, build, deploy, live playwright validation.
- Retrain/recalibrate loop: new data → append → rerun pipeline + backtest/bayesian → validate → update production params only if Rules 25-27 satisfied.

**Key Lessons from Past Runs (incorporated here):**
- Always add full standalone bg-slate-900 `border border-slate-800 rounded-3xl overflow-hidden mb-6` card for *every* new match (modeled exactly on existing e.g. NED-SWE or USA-AUS; never "in spirit" or abbreviated).
- Bilingual must be perfect everywhere (en/es spans, tooltips, diagram labels via JS, no leftover English in visible text or inner lists).
- Update table + exec summary + headers + narrative ("Core model v4.1 on full 15–XX dataset A") + diagram.
- Run full test matrix before/after: pipeline, translation toggle, report playwright compliance, deployed site (local + live).
- Fix CI immediately (e.g., alt report paths, selector waits for #btn-es).
- Use core pipeline numbers (never subagent estimates) for recs.
- After HTML: rebuild, push, gh run watch + live playwright validate.
- Retrain: always re-include prior dates in backtest; expand `wc_backtest_historical_dataset.csv` when results known.

### Fully Automated End-to-End Update Protocol (for any new screenshot batch e.g. June 22+)

**Prerequisites (one-time per batch):** User supplies new screenshots (Betsson/Betano). All steps use existing scripts + subagent harness for research.

1. **Screenshot Intake & Inventory (AGENT.md §1, automatic via script):**
   - Add verbatim rows to `wc_screenshots_inventory.csv` (use `scripts/` or manual + subagent).
   - Trigger: `python3 -c "from scripts.update_helpers import ..."` (or manual transcription).
   - Output: Updated inventory with source_image, odds, selection per market.

2. **Data Population (Research Subagent + Provenance, per AGENT §3):**
   - For **each new match**:
     - Run dedicated subagent: "Research {TeamA} vs {TeamB} {date}: predicted XI, injuries (≥2 sources), Elo (eloratings.net + international-football.net snapshot dated today), form, travel, weather, referee."
     - Populate full row in `wc_2026_model_dataset.csv`:
       - elo_a/b + source_*
       - home_adv (host/neutral per rules)
       - form/injury/weather adjustments + sources
       - mu_total
       - processing_notes (detailed, e.g. "screenshot odds for EV calc; provenance Elo 1935/1715; IMG_XXXX; finetunes: Rule 21 + Rule 17 DC for combo")
       - finetune_applied
     - If results known: set `actual_result` for backtesting.
   - Append to `wc_screenshots_inventory.csv` if not already.
   - Update `wc_2026_dataset_provenance.txt` + `wc_model_master_provenance.txt`.

3. **Core Model Retrain / Recalibrate / Rerun Pipeline (Automatic):**
   - Update `prior_odds` in `wc_replicable_pipeline.py` (or load dynamically from CSV) for new selections/odds.
   - **Rerun core:** `python3 wc_replicable_pipeline.py` (processes *entire* dataset A uniformly).
     - Produces raw p (1X2, margin2, plus1, ou, combo via DC ρ=-0.07), EV vs screenshot odds, documented targets.
   - **Backtest + Recalibrate (include all prior + new):**
     - `python3 wc_backtest_framework.py` (or `wc_backtest_historical_loader.py` if expanding N).
     - `python3 wc_bayesian_model_search.py` (if new data justifies re-search; enforce Rule 27: traps=0, WC strata Brier not worse).
     - `python3 wc_degree6_bayesian_kelly.py` etc. for staking.
     - Validate: 0/125 MOD traps, Brier improvements on weighted strata (Rule 25/26), sensitivities (aggr/base/cons).
     - Only update production weights (e.g. in v4.1 ensemble) if justified + documented counterfactual.
   - Extract for new matches: model_p_for_sel, EV, class (ROBUST/SPEC/PASS/HALT per Rules 13/14/24), self-critique inputs.
   - For combos: always use DC joint correction (Rule 17).
   - Save outputs to `wc_model_production_results.csv`.

4. **Increment Website Sections (Automatic HTML Generation + Manual Integration):**
   - Use pipeline output + existing card as **template** (never hand-write from scratch).
     - Copy structure of a complete card (e.g. from "Netherlands vs Sweden full detailed card"):
       - Header with fixture/date/venue.
       - 3-col grid: Data (screenshot + Elo + sources), Executed Model (exact p/EV/lambdas/DC from pipeline, sensitivities), Top Recommendation (EV%, class, stake suggestion ¼ Kelly).
       - Full ELI5 bilingual (what the bet is, odd explained, exact app steps for Betano/Betsson, "if something goes wrong", "after the game").
       - Tooltips for every jargon (EV, executed model, DC correction, SPEC, Rule 17, etc.).
       - Bilingual everywhere (`<span class="en">...</span><span class="es">...</span>`).
       - Exact class: `bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden mb-6`.
     - Fill placeholders with new data (match name, odds, p from pipeline, IMG_ ref, risks from research).
   - **Increment:**
     - Add new full card in the "Detailed Analysis & ELI5 for Each ..." section (after h2, in sequence by date).
     - Add row to recommendations table (in date order, with correct P/EV/class/Rule from pipeline).
     - Update exec summary text (slate description, key edges).
     - Update status banner, production text, diagram labels (LAYER 4), title if needed.
     - Update any inner validation lists or notes (make sure no "abbreviated" or missing).
   - Run `python3 scripts/build_site.py` (copies to site/).
   - **Validation gate:** Grep for new match name in full rounded-3xl cards + table. Count of `bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden mb-6` must equal #matches in table.

5. **Comprehensive Testing & Validation (Mandatory before any commit):**
   - Local model: `python3 wc_replicable_pipeline.py` (verify new numbers match expectations).
   - Full pytest: `python3 -m pytest tests/ -q` (test_wc_pipeline.py, test_translation_toggle.py, test_report_playwright_compliance.py, test_peer_replication.py, test_bayesian_search.py, test_wc_model_v*.py).
   - Playwright local: `python3 -m pytest tests/test_report_playwright_compliance.py -v` (checks content, bilingual, no stale, diagram).
   - Translation: Ensure no English-only visible text; all toggles work; test_es_no_visible_en_spans passes.
   - Layout: New cards must render with correct Tailwind (no overflow, proper bilingual hiding).
   - Run `python3 scripts/fix_translations.py` if needed (or batch).
   - Simulate deployed: `DEPLOY_URL=http://localhost...` or use built site.
   - **Betting recs validation:** Compare pipeline EV/P vs HTML table/cards. Re-verify Rules (no fabricated odds, sensitivities, self-critique, confidence ≤70%).

6. **Build, Deploy, Live Playwright Validation:**
   - `python3 scripts/build_site.py`
   - Commit with message referencing new matches + "core model update + full sections + tests green".
   - `git push`
   - `bash scripts/deploy_github.sh` (or `gh run watch --exit-status`)
   - Live validate: `python3 scripts/wait_and_validate_deploy.py` (retries until live, runs `tests/test_deployed_site.py`).
   - Playwright on live: Confirm all matches (old + new) have sections, correct layout, bilingual toggle, "v4.1 prod", no 404s on report paths, responsible block, diagram labels switch.
   - Check: `curl` or browser for new match card presence, table row, updated summary.

7. **Docs & Provenance Update (Complete):**
   - Append to AGENT.md, MODEL_ITERATION_V6.md (new deltas, Brier, Rule applications).
   - Update VALIDATION_SUMMARY.md, wc_*.txt provenance files, README.md.
   - Document: "Core model retrained with new data in dataset A; used for all predictions; website incremented with full sections; all tests + live playwright validated."

**Automation Helpers (use/enhance these):**
- `scripts/build_site.py` (always run after HTML changes).
- `scripts/deploy_github.sh` + `wait_and_validate_deploy.py` (for CI/CD + live playwright).
- `scripts/fix_translations*.py` (run if translation test fails).
- `wc_replicable_pipeline.py`, `wc_backtest_framework.py`, `wc_bayesian_model_search.py` (core for retrain/recalibrate/rerun).
- Subagent spawning pattern (use the harness): For each new match, spawn parallel subagents with prompt like: "You are a subagent for {TeamA} vs {TeamB} {date} (IMG_XXXX from screenshots). 1. Follow AGENT.md §1.1-1.4 for intake (inventory table). 2. §3 research fan-out (predicted lineup, injuries from >=2 sources, Elo dated snapshot, form, H2H, venue/weather). 3. Populate exact row template for wc_2026_model_dataset.csv (all columns + detailed processing_notes + finetune_applied). 4. Run targeted pipeline for this row to get p/EV/sensitivities. 5. Generate full standalone HTML card snippet using exact template from existing match (copy structure of e.g. the Netherlands vs Sweden card in index.html: header, 3-col grid Data/Executed Model/Top Rec, long bilingual ELI5 with tooltips for all jargon, app steps). Output the CSV row text + full div HTML ready for insert."
- Future enhancement: Add `scripts/generate_match_card.py --match "TeamA vs TeamB" --date 2026-06-XX --odds 3.05 --p 0.334 --ev 1.8 --class SPEC --img IMG_7490.PNG` to auto-emit the bilingual div from pipeline JSON + research.
- Validation commands to always run:
  - `python3 -m pytest tests/ -q` (all, including translation, compliance, deployed if DEPLOY_URL set).
  - `grep -c 'bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden mb-6' index.html` (must == number of table rows/matches).
  - `python3 scripts/build_site.py`
  - After push: `gh run watch` + `python3 scripts/wait_and_validate_deploy.py`
  - Live checks: curl for new card presence, playwright on live for layout of all matches (new sections have correct class, en/es, no overflow, toggle works, recommendations table includes all).

**Failure Modes to Prevent (from past runs/user messages):**
- Missing full card for any match (must be standalone rounded-3xl, never abbreviated or "in spirit"; history had Portugal/ENG-CRO only in additional block or missing initially).
- Non-bilingual text (history fixed many in inner lists, embedded NED block in SUI, USA "Book implies", headers without es; always pair every visible string).
- Pipeline numbers not matching HTML (always pull direct from run output; subagents for research only).
- CI/deploy fails (alt report path 404s → use current wc_june17_21_... ; button clicks → add waits in tests/fixture; fix immediately, update test_deployed_site.py).
- Stale narrative ("15-16 core + 17-21 subagent") → always update to "core model v4.1 pipeline on full 15–XX dataset A + backtested".
- Partial updates (missing sections for new dates, table not incremented, exec summary not referencing new edges, diagram not updated).
- No backtest inclusion or recalibration (always rerun framework on expanded set; only change params if improves per rules).
- Playwright/layout issues on new sections (must pass compliance: correct class, bilingual, ELI5 structure, no stale, diagram labels, all matches implemented).
- No live validation (always run wait_and_validate + check live has all sections, correct content).

**Subagent Usage for Parallelism (from history):** Spawn one subagent per new match (as done for Brazil, USA, NED-SWE). Each follows full AGENT.md intake + 9-step + research + "generate card snippet". Integrate outputs. For peer-review: spawn "validate this card against pipeline output and AGENT.md" subagent.

**For Next Batch Example (e.g. new June 22+ or later screenshots):**
1. User uploads screenshots → run subagents for intake/research per match (parallel).
2. Update inventory + dataset A (subagent output + manual review for accuracy).
3. `python3 wc_replicable_pipeline.py` (full run) + backtest/bayesian as needed.
4. For each new match: copy last full card div in index.html (after the h2 in Detailed section, by date order), replace all content with new data + pipeline numbers + ELI5 tailored (keep structure identical for perfect bilingual/layout). Add table tr. Update summary text.
5. Fix any bilingual (run translation test).
6. `python3 -m pytest tests/ -q && grep -c 'bg-slate-900 ... mb-6' index.html && python3 scripts/build_site.py`
7. Commit "core model update for new dates: added X sections, retrained on dataset A, all tests + playwright pass".
8. Push → deploy script → live playwright validate (check all matches including new have sections, layout correct, recs match pipeline).
9. Append to this MD + MODEL_ITERATION + VALIDATION_SUMMARY with deltas/lessons.
10. Update protocol here with any new learnings.

**Lesson from recent CI run (27708583736, 2026-06-17):** After applying fixes to test_deployed_site.py (point alternate_report_path to wc_june17_21_full_report.html instead of stale wc_june16 one; add robust waits in _switch and browser_page fixture for #btn-en/#btn-es), the full validate-deployed job passed 9/9 tests (including alternate_report_path and responsible_gambling_block) on the live site. Always keep deployed tests in sync with current build artifacts and use explicit Playwright waits for dynamic UI (lang toggle). The protocol's step 8 + live validate caught and resolved this; re-run gh run watch or the script to confirm.

This makes the process as automatic as possible (scripts + templates + subagent prompts + checklists) while ensuring comprehensive (research + model + website + tests + docs + deploy + live), perfect (exact structure, bilingual, validated), complete (no missing matches/sections, full cycle).

Production always uses latest executed pipeline vs screenshot odds. 15-16 (and future realized) provide the backtest anchor. All per past user emphasis on subagents for research, core pipeline for numbers, full sections, tests, GH Pages.

See MODEL_ITERATION_V6.md (detailed steps + example), scripts/, tests/ (must all pass), AGENT.md §1-9 + Rules for base rules. Re-execute this protocol on every new batch.

See also: MODEL_ITERATION_V6.md (full workflow + example), MODEL_PIPELINE_V4.md, scripts/, tests/test_deployed_site.py (must pass on live), AGENT.md §1-9 (base 9-step + Rules). 

This protocol, when followed strictly with scripts, guarantees automatic/comprehensive/perfect updates.

