# requirements.md — Data, Tools & Validation Gates for AGENT.md

**Companion document to AGENT.md.** This file enumerates every dependency the screenshot-driven betting analysis workflow needs, the validation gates each candidate bet must clear before being graded "Strong," and the failure conditions that force a halt.

---

## 1. Functional requirements (what the agent must always be able to do)

### R1 — Screenshot intake
| ID | Requirement | Must / Should |
|----|-------------|---------------|
| R1.1 | Parse decimal odds from a screenshot to ±0.01 accuracy | MUST |
| R1.2 | Identify the app (Betsson vs Betano vs other) from UI cues, or confirm with user | MUST |
| R1.3 | Extract market label, selection labels, and the visible timestamp | MUST |
| R1.4 | Detect "boosted odds" or promo markers | SHOULD |
| R1.5 | Flag screenshots older than 4 hours as stale | MUST |
| R1.6 | Reject blurry / unreadable images with a re-upload request | MUST |

### R2 — Data acquisition
| ID | Requirement | Must / Should |
|----|-------------|---------------|
| R2.1 | Fetch current Elo from international-football.net within 48h of analysis | MUST |
| R2.2 | Retrieve injury list from ≥2 independent sources per team | MUST |
| R2.3 | Retrieve predicted lineups from ≥2 independent sources | MUST |
| R2.4 | Cross-reference fixture date/time/venue from ≥2 schedule sources | MUST |
| R2.5 | Pull recent form (last 6 competitive matches) per team with opposition strength | MUST |
| R2.6 | Pull H2H last 10 meetings | SHOULD |
| R2.7 | Pull referee statistics when known | SHOULD |
| R2.8 | Pull weather forecast for outdoor venues | SHOULD |
| R2.9 | Pull starting-XI xG per-90 from club fixtures (FBref) when international xG is unreliable | SHOULD |

### R3 — Modeling
| ID | Requirement | Must / Should |
|----|-------------|---------------|
| R3.1 | Execute the Elo + form + home model in actual code | MUST |
| R3.2 | Run sensitivity test in three scenarios (aggressive / base / conservative) | MUST |
| R3.3 | Produce 1X2, Over/Under 2.5, BTTS fair odds per match | MUST |
| R3.4 | Produce match-specific markets when requested (correct score, Asian Handicap, team totals) | SHOULD |
| R3.5 | Compute EV against user's live odds (not estimated odds) | MUST |
| R3.6 | Compute book overround for every complete market | MUST |
| R3.7 | Detect and report any genuine cross-book arbitrage with stake-split math | MUST |
| R3.8 | Run expanded historical backtest (≥200 matches: prior WCs + friendlies/WCQ + current MD) before material calibration changes | MUST |
| R3.9 | Use walk-forward Elo (K=20) for chronological friendly/WCQ backtest rows — no look-ahead | MUST |
| R3.10 | Report weighted Brier stratified by competition + market-implied devigged baseline | MUST |
| R3.11 | Production v4 stack: `wc_model_v4_ensemble.py` (1X2 anchor + DC O/U + Rule 24 tier EV) | MUST |

### R4 — Reporting & transparency
| ID | Requirement | Must / Should |
|----|-------------|---------------|
| R4.1 | Show all model formulas in KaTeX | MUST |
| R4.2 | Cite every external fact with URL + timestamp | MUST |
| R4.3 | Include "what could make this wrong" for every recommendation | MUST |
| R4.4 | Cap confidence at 70% | MUST |
| R4.5 | Append the standardized responsible-gambling block | MUST |
| R4.6 | Never include a "place this bet now" directive | MUST |

---

## 2. Data sources — authoritative list

### 2.1 Tier-1 (primary, always consulted)

| Source | Use | URL pattern |
|--------|-----|-------------|
| **international-football.net** | Current Elo ratings, dated | `/elo-ratings-table?year=YYYY&month=MM&day=DD` |
| **eloratings.net** | Latest match results, secondary Elo | `/latest` and `/{team}` |
| **FBref** (StatsBomb data) | xG, xGA, set-pieces, advanced metrics | `fbref.com/en/squads/...` and national-team pages |
| **Transfermarkt** | Injuries, suspensions, market values, squad list | `/sperrenundverletzungen/verein/{id}` |
| **FotMob** | Squad health, lineups, in-app injury status | `/teams/{id}/squad` |
| **FIFA.com** | Official squads, suspensions, competition data | `fifa.com/fifaplus/en/tournaments/...` |
| **Federation official sites** | Late-breaking team news | varies (e.g., ussoccer.com, canadasoccer.com) |

### 2.2 Tier-2 (lineup / preview triangulation)

| Source | Use |
|--------|-----|
| Sports Mole | Predicted XI, injury suspension lists |
| RotoWire | Lineup notes + tactical analysis |
| Sports Illustrated | Pre-match preview + predicted XI |
| ESPN Soccer | Match preview, kickoff info, broadcast |
| BBC Sport | UK perspective + reliable injury news |
| Bundesliga liveticker (where applicable) | Real-time updates close to KO |
| The Athletic / NYT | Tactical deep-dives |

### 2.3 Tier-3 (market sanity checks — never live Betsson/Betano)

| Source | Use |
|--------|-----|
| sports-king.com | Public Bet365 / sharp prices, often dated |
| VegasInsider | US sportsbook consensus lines |
| ESPN BET / FanDuel / DraftKings published articles | Tier-1 US sharp prices |
| Betfair Exchange (public preview articles only) | Sharpest public-market signal where covered |
| WhoScored prediction model | Algorithmic baseline |
| Opta Analyst | Stats Perform supercomputer probabilities |

### 2.4 Tier-4 (qualitative / context)

| Source | Use |
|--------|-----|
| Local-language media | Late team news in Spanish / Portuguese / Bosnian, etc. |
| Beat reporters on X / Bluesky | Pressers, last-minute changes |
| YouTube official channels (federations) | Press conferences |
| Weather Underground / accuweather | Match-day weather |

**Rule**: Tier-1 must always be consulted. Tier-2 must contribute ≥2 sources per team. Tier-3 is for market sanity. Tier-4 is supplementary; never the sole basis for a claim.

---

## 3. Validation gates (each bet must pass to be graded)

A bet candidate is **graded** only after clearing all applicable gates. Failure of any gate downgrades the bet automatically.

### Gate G1 — Data freshness
- ✅ Lineup data ≤ 24h old (≤ 90 min if pre-KO lineups have been announced).
- ✅ Injury data ≤ 24h old.
- ✅ Odds screenshot ≤ 4h old.
- ✅ Match has not started.

**Failure** → halt analysis, request fresh inputs.

### Gate G2 — Source diversity
- ✅ ≥2 independent sources confirm key team news.
- ✅ Elo + xG (or proxy) both consulted.
- ✅ At least one Tier-3 sanity-check on market consensus.

**Failure** → flag as low-confidence; cap grade at Speculative.

### Gate G3 — Model robustness
- ✅ Model runs in code (not narrated).
- ✅ Sensitivity test produces three valid scenarios.
- ✅ EV in base scenario ≥ +1.5%.

**Failure** → grade Pass.

### Gate G4 — EV magnitude vs vig
- ✅ EV exceeds book overround on that market by at least 1 percentage point.
  - Example: Betsson 1X2 with 6% vig → EV must be ≥ +7% for "Strong."
- ✅ For "Strong": EV ≥ +6% in base AND positive in all 3 sensitivity scenarios.

**Failure** → downgrade by one tier.

### Gate G5 — No critical data gap
Critical gaps include:
- Key player status genuinely unknown (e.g., late fitness test).
- Conflicting source reports unresolved.
- Referee unconfirmed for a referee-driven market.
- Weather unconfirmed for an outdoor extreme-condition venue.

**Failure** → cap grade at Moderate; if multiple critical gaps, cap at Speculative.

### Gate G6 — Variance / liquidity
- ✅ Bet is not a long-tail correct-score / accumulator with >5 legs unless explicitly requested.
- ✅ Player props capped at "Strong: Moderate" max regardless of model EV.

**Failure** → downgrade.

### Gate G7 — Self-critique sufficiency
- ✅ At least 3 plausible "what could make this wrong" scenarios listed.
- ✅ One single point of model failure explicitly identified.
- ✅ Confidence % not above 70%.

**Failure** → revise output before publishing.

### Gate G8 — User-action safety
- ✅ Output never instructs the user to place a bet.
- ✅ Stake suggestions framed as ranges, capped, and tied to user-supplied bankroll if provided.
- ✅ Responsible-gambling block appended.

**Failure** → block publication; rewrite.

---

## 4. Tool requirements

### 4.1 Required tools (in workspace)
- **Web search** with recency filter (`day`, `week`, `month`).
- **URL fetcher** with LLM extraction.
- **Code execution** (Python with numpy/scipy). Production analysis: `wc_model_v4_ensemble.py` (v4 tier ensemble + DC O/U + Rule 24). Legacy/replicable: `wc_replicable_pipeline.py`. Expanded backtest: `wc_backtest_historical_loader.py` → `wc_backtest_framework.py`. Do not narrate numbers — output executed results only. Re-run on material lineup/injury/odds update within 90 min of KO.
- **Expanded backtest dataset** `wc_backtest_historical_dataset.csv` (N≥200: WC 2018/2022 + friendlies 2023–2026 + WC26 MD). Rebuild before calibration changes per Rule 25.
- **File system** for caching Elo tables and team profiles between calls.
- **Image-aware vision** to read screenshots (handled by the agent's native multimodal capability).

### 4.2 Optional tools (use when available)
- Subagents for parallel research (one per team news lookup).
- Memory store for user's stated bankroll and preferences.
- Scheduled jobs to refresh Elo/lineup pages on matchdays.

### 4.3 Tools explicitly NOT to use
- ❌ Browser automation to log into or scrape Betsson / Betano apps.
- ❌ Any third-party "tipster" API that aggregates picks (introduces bias).
- ❌ Live-odds APIs without explicit user consent and licensing.

---

## 5. Performance / quality SLAs

| Metric | Target |
|--------|--------|
| End-to-end analysis time per match (with fresh screenshots) | ≤ 5 minutes |
| Number of distinct citations per match | ≥ 8 |
| Number of data sources consulted per match | ≥ 6 |
| Number of model scenarios run per bet | 3 (mandatory) |
| Max confidence % allowed | 70 |
| Max bankroll % suggested per single bet | 1.5 |
| Max bankroll % suggested per matchday | 5.0 |

---

## 6. Failure & halt conditions

The agent **must halt** and notify the user (rather than guess) when:

1. The match has already kicked off.
2. Screenshot odds are unreadable or contradict the labeled market.
3. Source contradiction on a critical input cannot be resolved within 2 search rounds.
4. The model produces an EV > +30% — this is almost always a model error, not a genuine edge.
5. The user's screenshots span two different fixtures or markets but are presented as one — request clarification.
6. The user requests a stake on a match that is not in the verified WC 2026 fixture list or known competition schedule.
7. The agent cannot verify the Elo or injury data from any source (all primary sources down) — flag explicitly.

---

## 7. Localization & regulatory notes (Peru-specific)

The user operates in Lima, Peru.
- Online sports betting is regulated by **MINCETUR** under **Ley 31806** (in force since 2024).
- Betsson and Betano are both authorized operators in Peru.
- The agent treats the user as the licensed bettor and decision-maker.
- Helpline references: **Línea 0800-1-3232** (MINCETUR support), **Jugadores Anónimos Perú**.

---

## 8. Definitions

- **Decimal odds (o)**: European-format odds; payout per 1 unit staked including stake.
- **Implied probability**: 1/o.
- **Vig / overround**: Sum of implied probabilities across a market, minus 1.
- **Fair odds**: 1 / P_model.
- **EV%**: (P_model × o_live − 1) × 100.
- **Kelly fraction**: (p·o − 1) / (o − 1); fractional Kelly = k × Kelly (k=0.25 default).
- **ROBUST edge**: +EV in all three sensitivity scenarios.
- **Sharp price**: A price from a low-margin, high-limit book (Pinnacle, Betfair Exchange, sharp Asian books) used as a market reference.

---

## 9. Change control

- This file is version-controlled in workspace.
- The user is the only party who can request material changes to validation thresholds, source list, or grading rules.
- The agent may propose updates after each tournament round based on observed model accuracy, but must not change them unilaterally during a live tournament.

---

## 10. Acknowledged limitations

The agent acknowledges:
- No access to Pinnacle or Betfair Exchange live odds API.
- No access to Betsson or Betano live odds (screenshot-only).
- Internationals have small sample sizes; xG models for national teams have wider error bars than club football.
- WC 2026 is the first 48-team, 3-host-country tournament — there is no historical base rate for travel/altitude/heat effects at this scale; assumptions are best-effort.
- Models do not see in-game tactical adjustments, injuries during warmups, or red cards.

The user is the final decision-maker on every wager.

---

## 11. Version log
- **v1.3** — 2026-06-15 — Expanded backtest mandate (R3.8–R3.11, Rule 25/26). N=222 dataset: WC 2018/2022 group stages + football-data.co.uk internationals 2023–2026 (walk-forward Elo) + WC26 MD1–3. Weighted Brier stratification + market-implied baseline required before calibration changes. Production model = `wc_model_v4_ensemble.py`.
- v1.2 — 2026-06-15 (post "proceed" + backtest cycle) — Added Rules 21-23 references (WC opener/minnow finetunes, BT + xG-hybrid ensemble, HTML report/viz mandate with Tailwind). Updated code execution reqs for finetune flags + alt legs. Expanded Tier-3 sources for xG (FBref) and BT ratings. Added explicit HTML validation + interactive viz requirements while preserving AGENT §4 core.
- v1.1 — 2026-06-15 — Added mandatory model-script execution (wc_model_v3.py or successor) for all numerical outputs. Added Rule 19/20 references from AGENT v3.1 backtest cycle. Updated data sources with eloratings.net 2026-06-15 snapshot and DC joint literature.
- v1.0 — 2026-06-12 — Initial requirements authored alongside AGENT.md v1.0.
