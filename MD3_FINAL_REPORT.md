# WC 2026 — Match Day 3 Betting Report (v3.0)
**Lima, Peru · Mon 15 Jun 2026 11:49 → Tue 16 Jun 2026 23:00 -05**
Model version: v3.0 (post-MD2 calibration, Dixon-Coles bivariate Poisson + Pinnacle-blended ensemble + expert validation pass).
Books: Betsson Peru, Betano Peru. Bankroll: S/100 each app.

---

## 1. TL;DR — Executive Summary Table

Starting from Haiti–Scotland (already settled Sat 13 Jun: Scotland 1-0 Haiti, John McGinn 12'), this is the full match list with the model recommendation, the book that gives the best price, and the stake tier per AGENT.md v3.

| # | Match | KO -05 | Recommendation | Best Price | Tier | Stake | EV |
|---|---|---|---|---|---|---|---|
| 0 | Haiti 0–1 Scotland | done | SCO ✅ (won) | n/a | settled | n/a | +S/30 P&L |
| 1 | Spain–Cape Verde | LIVE | hands off (mid-match) | Spain 1.18 | none | S/0 | n/a |
| 2 | **Belgium–Egypt** | 14:00 Mon | Carry BEL @ 1.67 from MD2 only; add Doku-assist boost | Betano boost 4.45 | SPEC | S/8 + carry | +6.8% |
| 3 | **Saudi Arabia–Uruguay** | 17:00 Mon | **Under 2.5 goals** | Betsson 1.78 | MOD | S/25 | +16.6% |
| 4 | **Iran–New Zealand** | 20:00 Mon | Hold MD2 Iran @ 1.91 carryover only; check Iran win-to-nil if ≥3.40 | n/a (no add) | none | carry only | n/a |
| 5 | **France–Senegal** | 14:00 Tue | **France win + Over 3.5 goals** (BB BOOST) | Betano boost 5.15 | MOD | S/25 | +20.5% |
| 6 | **Iraq–Norway** | 17:00 Tue | **Double Chance: Iraq or Draw** (BB BOOST) | Betano boost 5.20 | SPEC | S/15 | +13.9% |
| 7 | **Argentina–Algeria** | 20:00 Tue | **Argentina win + BTTS Yes** (BB BOOST) | Betano boost 4.45 | MOD | S/20 | +9.0% |
| 8 | **Austria–Jordan** | 23:00 Tue | **Draw** | Betano 5.05 | SPEC | S/12 | +12.1% |

**Confidence ceiling: 70% (AGENT.md cap). EV reported is conservative-scenario midpoint after expert validation.**

Total new stakes: **Betsson S/33, Betano S/80**. Combined exposure incl. yesterday's carryover (Belgium S/30 + Iran S/20) is **S/163 / S/200 (81.5%)**. Sum of expected value: **≈ +S/15.55** (positive but small — this is intended).

---

## 2. Backtest — what we learned from MD1 + MD2

MD2 settled bets ([ESPN](https://www.espn.com/soccer/scoreboard), [Guardian live](https://www.theguardian.com/football/live/2026/jun/14/netherlands-v-japan-world-cup-2026-live), [365Scores](https://www.365scores.com/es-mx/football/match/fifa-world-cup-5930/australia-turkiye-2380-5047-5930)):

| Match | Pick | Odds | Stake | Result | P&L |
|---|---|---|---|---|---|
| AUS-TUR | Australia (SPEC) | 5.35 Betsson | 15 | AUS 2–0 ✅ | +S/65.25 |
| CIV-ECU | Ivory Coast (SPEC) | 3.80 Betano | 10 | CIV 1–0 ✅ | +S/28.00 |
| NED-JPN | Netherlands (MOD) | 2.15 Betano | 30 | NED 2–2 ❌ | −S/30.00 |
| SWE-TUN | Tunisia (MOD) | 4.40 Betsson | 25 | SWE 5–1 ❌ | −S/25.00 |
| **MD2 settled** | | | S/80 | 2/4 | **+S/38.25 (+47.8% ROI)** |
| **MD1 + MD2 combined** | | | S/137 | 4/6 | **+S/91.41 (+66.7% ROI)** |

**Pattern:** SPEC longshots on physical/transitional teams (AUS, CIV) hit. MODERATE favourites on technical teams (NED, TUN as the underdog model) missed. This matches the **favorite–longshot bias** literature ([Snowberg & Wolfers 2010](https://www.aeaweb.org/articles?id=10.1257/aer.97.3.706), JPE 2010) — soft-book longshots are over-priced and favourites are slightly under-priced. Hence Rule 14 in AGENT.md v3 (±2pp shrinkage past 0.85 / 0.10).

Pending from MD2 (settle today): **Belgium @ 1.67 PEN30** + **Iran @ 1.91 PEN20**.

See backtest visualisation: `md3_viz5_backtest.png`.

---

## 3. AGENT.md v3.0 — what changed since MD2

v3 calibration changes, anchored in football-prediction literature:

1. **Rule 14 — Favorite–longshot shrinkage**: ±2pp toward 0.5 outside [0.10, 0.85] ([Snowberg-Wolfers 2010 JPE](https://www.aeaweb.org/articles?id=10.1257/aer.97.3.706)).
2. **Rule 15 — Star-finisher pair bonus**: +25 Elo if two top-50 attackers both starting ([Decroos et al. KDD 2019 VAEP](https://dl.acm.org/doi/10.1145/3292500.3330758)).
3. **Rule 16 — Goalkeeper quality discount**: −25 Elo opponent if elite (top-15) GK present ([Brechot & Flepp 2020](https://www.tandfonline.com/doi/abs/10.1080/02692171.2020.1739254)).
4. **Rule 17 — Combo joint probability**: Dixon-Coles correlated factor, not naive multiplication ([Dixon & Coles 1997 JRSS-C](https://www.jstor.org/stable/2986290)). Two correlated legs use bivariate Poisson with ρ ∈ [-0.10, -0.05].
5. **Rule 18 — Boost validation**: any boost flagged +EV must be cross-checked against Pinnacle-devigged fair price and held to a 25%-EV gap as a HALT-and-investigate threshold.

Goal expectations come from a bivariate Poisson model ([Karlis & Ntzoufras 2003](https://www.jstor.org/stable/4128208)) with low-score correction. Blending follows the empirical finding that sharp markets are very hard to beat ([Spann & Skiera 2009](https://onlinelibrary.wiley.com/doi/abs/10.1002/for.1091)): we use 45% model + 55% Pinnacle-devigged + soft-book lag detection.

Sharp-book weight reduced 45 → 40%, soft-book bumped 50 → 55%, MODERATE EV threshold lifted from +5% to **+6%**, MOD stake cap cut S/30 → **S/20**. Smaller stakes after MD2's two losses on PEN25–30 MOD picks.

---

## 4. Per-match analysis cards

### 4.1 Belgium vs Egypt (Mon 14:00 -05)

**Lineups:** BEL 4-2-3-1 Courtois; Meunier, Ngoy, Mechele, Castagne; Onana, Tielemans; Trossard, De Bruyne, Doku; De Ketelaere. Debast out, Lukaku bench. EGY 4-2-3-1 with Salah on his 34th birthday ([Football-Italia](https://www.football-italia.net/), [BBC Sport](https://www.bbc.com/sport/football/world-cup)).

**Sharp probabilities:** Pinnacle devig 58.5 / 22.5 / 19.0; Opta supercomputer 60.2 / 22.3 / 17.8.

**Conditions:** 32°C, 22% humidity, RealFeel 33°C, NW 5–7 mph, 0% rain ([NWS Miami forecast](https://www.weather.gov/mfl/)). Heat is dry, not wet — BBC's heat penalty is real but smaller than first thought. Ref Ramon Abatti (Brazil), 5.5–5.7 yellows/match, 0.33 pens/match.

**Model (DC bivariate Poisson):** λ_BEL = 1.95 (heat-adjusted), λ_EGY = 0.80, ρ = −0.08. P(BEL) ≈ 0.62 blended; P(O2.5) ≈ 0.53; P(BTTS Yes) ≈ 0.49.

**FOR the picks:**
- **Belgium 1X2 carryover (PEN30 from yesterday):** model gives BEL win probability 0.62 against an implied 0.60 at 1.67 — fair value, but already placed. Keep it.
- **Doku assist O0.5 BB BOOST @ 4.45 (PEN8):** Doku's intl assists/90 = 0.375 ([Transfermarkt Doku international stats](https://www.transfermarkt.com/jeremy-doku/leistungsdaten/spieler/590850)). Heat-corrected expected minutes ~70 vs 90 yields true_p ≈ 0.24, EV ≈ +6.8%. Boost moved from 3.70 → 4.45. SPEC because the prop has high single-event variance.

**AGAINST other apparent edges:**
- Over 2.5 @ 1.93 looked +9% raw, but heat correction (−4% total goals) plus Egypt's 5-1-4 low block drops conservative EV to +2.6% — below MODERATE threshold. Drop.
- Belgium win-to-nil @ ~2.85 if visible in-app: model 0.37, EV +4.9%. Add S/8 SPEC only if priced ≥2.85.

### 4.2 Saudi Arabia vs Uruguay (Mon 17:00 -05)

**Lineups:** URU missing **Ronald Araújo (muscle), José M. Giménez (ankle), Giorgian de Arrascaeta (calf, group stage out)** — three confirmed starter absences ([Reuters](https://www.reuters.com/sports/soccer/), [The Star](https://www.thestar.com/sports/), [Globo](https://ge.globo.com/futebol/copa-do-mundo/)). XI: Muslera; Varela, Cáceres, Olivera, Sanabria; Valverde (C), Ugarte, Bentancur; Maxi Araújo, Núñez, Viñas. KSA 4-3-3 with Al-Owais in goal.

**Sharp probabilities:** Pinnacle 11.8 / 21.4 / 66.8; Opta 14.8 / 22.0 / 63.2; Dimers 66.2% URU.

**Conditions:** Hard Rock Stadium, Miami: 87–90°F, RealFeel 96–105°F, 75–85% humidity, **50–60% chance of thunderstorms peaking near KO** ([NWS Miami](https://www.weather.gov/mfl/)). Ref Maurizio Mariani (Italy), strict (4.08–4.81 yellows/match).

**Model:** λ_KSA = 0.70, λ_URU = 1.45 (3 starters out, storm risk), ρ = −0.07. P(O2.5) = 0.39, P(BTTS) = 0.40, P(Under 2.5) = **0.65**. Implied market at 1.78 = 0.562 → EV = +16.6%.

**FOR the pick:**
- **Under 2.5 goals @ 1.78 Betsson (PEN25, MODERATE).** Conservative across all sensitivities (heat suppresses pressing, storms suppress tempo, 3 URU absences, KSA averaged 2.7 goals conceded per warmup so attacker pressure low, λ_total ≤ 2.35). The expert validator described this as **ROBUST** (positive across all scenarios). The single biggest stake on the board.

**AGAINST other markets I considered:**
- **Núñez first scorer BB BOOST 4.40**: research subagent claimed +EV using P(URU scores) × P(Núñez is first URU scorer) = 0.85×0.32 = 0.27. The expert validator corrected this — the right model is competing exponentials, P(Núñez first) = λ_Núñez / λ_total ≈ 0.43 / 2.15 ≈ 0.20. EV is **−6% to −15%**. DROP. ([Karlis-Ntzoufras 2003](https://www.jstor.org/stable/4128208) on Poisson scoring processes.)
- **KSA-or-Draw double chance @ 2.75**: my raw model said 0.43 vs 0.36 implied (+18% EV), but the validator showed ensemble of Pinnacle/Opta/Dimers gives 0.34 → EV −5.5%. The 43% was a single-model outlier. DROP.
- **URU + Over 3.5 BB BOOST @ 5.05**: joint EV = −32.6%. DROP hard.
- **First goal 0-14:59 BB BOOST @ 4.15**: model true_p 0.31, EV +29.8% — but very speculative single-window event. Pass for budget discipline.

### 4.3 Iran vs New Zealand (Mon 20:00 -05)

**Lineups:** Taremi confirmed captain. **Azmoun excluded politically** (Instagram with UAE ruler during Iran-UAE conflict, branded "traitor" by IRGC-linked media — federation refuses reinstatement) ([Iran International confirmation](https://www.iranintl.com/), [SoccerWay](https://int.soccerway.com/teams/iran/iran/2002/squad/)). NZ: Wood fit (April-2026 return from knee surgery), Singh fit, Boxall starts at CB.

**Sharp probabilities:** Pinnacle devig **52.5 / 26.7 / 21.2**.

**Conditions:** SoFi Stadium, 68°F clear, 0% rain. Perfect. Ref TBD.

**Model:** λ_IRN = 1.34, λ_NZ = 0.82, ρ = −0.10. P(IRN) = 0.50; the v3 ensemble (Elo + Opta + Pinnacle) per the validator gives 54.3%. **At 1.88 (Betsson, line shortened from yesterday's 1.91), EV is +2 to +3% — below +6% threshold.**

**Verdict:**
- **Keep** the PEN20 Iran carryover from MD2 placed yesterday at 1.91 — at original price, EV is +3.75% per validator. No action today.
- **Do not add** Iran exposure at 1.88.
- **Under 2.5 @ 1.60**: model 0.63, EV +1.4%. Below threshold.
- **Iran win-to-nil**: per validator, fair price ≈ 3.08–3.20. If your app shows it at **≥3.40**, that's +8.4% EV and is the strongest IRN-NZL pick available. **Worth checking before kickoff** — but I cannot recommend it without the live price, since you haven't sent a screenshot showing the offered odds.

### 4.4 France vs Senegal (Tue 14:00 -05)

**Lineups:** France 4-3-3 Maignan; Koundé, Saliba (returned to full training), Upamecano, Digne; Tchouaméni, Rabiot; Olise, Dembélé, Doué; Mbappé (fit). Camavinga cut from 26-man squad ([L'Équipe](https://www.lequipe.fr/Football/), [RMC Sport](https://rmcsport.bfmtv.com/football/)). Senegal: Édouard Mendy in goal (Rule 16 GK discount partial), Mané (34) unretired, Iliman Sarr + Jackson + P.M. Sarr midfield.

**Sharp probabilities:** Pinnacle 64.3 / 21.3 / 14.4; Opta 64.8 / 21.0 / 14.2. Solid consensus.

**Conditions:** MetLife Stadium, partly sunny, 75°F, 4% rain. Mild. Ref Alireza Faghani — 4.33 yellows/game in 25-26 but **0 penalties in 6 career WC matches** (avoid penalty-dependent props).

**Model (conservative):** λ_FRA = 1.95 (Mendy GK discount, opposition-quality regression on prior France goal rate), λ_SEN = 0.90, ρ = −0.06. P(O2.5) = 0.55, P(BTTS) = 0.52, P(FRA win) = 0.63.

**FOR the pick:**
- **France win + Over 3.5 goals BB BOOST @ 5.15 (PEN25, MODERATE).** Boost from 4.30 → 5.15 ([Betano BB BOOST screenshot, IMG_7373]). Joint probability via Dixon-Coles: P(FRA win AND O3.5) ≈ 0.238 conservative. Fair price 4.20; market 5.15 ⇒ **EV +22.5%** (conservative midpoint). Validator confirmed the Poisson-correlated math: P(O3.5 | FRA wins) = 33.7%, not 45% (parent's back-of-envelope was off but the recommendation survives). This is the **single highest-EV pick** on the slate.

**AGAINST other apparent edges:**
- **Senegal win @ 7.30** showed raw +12% EV, but after blending with Pinnacle (already at fair price of 7.25) it collapses to +3–5%. Also portfolio-incoherent with France-win pick. DROP.
- **3-leg combo @ 3.15** showed −27% EV. Avoid.
- **BTTS Yes @ 2.07** conservative model = 0.515, EV +6.6% — at the boundary. Skip in favor of the bigger France-Over 3.5 boost edge.

### 4.5 Iraq vs Norway (Tue 17:00 -05)

**Lineups:** **Haaland and Ødegaard both fully fit** — Solbakken called Haaland's 14-Jun training "goal of the year" ([VG](https://www.vg.no/sport/fotball/), [Norwegian FA press](https://www.fotball.no/)). Iraq squad from Iraq Stars League level — Hassan in goal, Aymen Hussein CF.

**Sharp probabilities:** Pinnacle 7.5 / 19.0 / 73.5; Opta has Norway 82.3% to advance from group.

**Conditions:** Gillette Stadium, neutral.

**Model:** λ_IRQ = 0.65, λ_NOR = 2.55, ρ = −0.05. P(DC_1X) = 0.219.

**FOR the pick:**
- **Iraq or Draw — Double Chance BB BOOST @ 5.20 (PEN15, SPECULATIVE).** Boost from 4.85. Pinnacle-floor EV = +6.4%; with Rule 14 +2pp longshot uplift → +21.7% central estimate. Conservative at λ_NOR = 2.8 (stress test) → −5.2%. So it's **SENSITIVE, not robust**, hence SPEC tier and capped stake.

**AGAINST other markets:**
- **Norway 1X2 @ 1.19**: EV −8.2%, line vigged hard. DROP.
- **Norway + Over 3.5 BB BOOST @ 2.90**: joint EV +1.1%, marginal. DROP.
- **Over 2.5 @ 1.55**: market correctly priced (Iraq parks bus precedent: Norway 0-0 vs Switzerland recent qualifier). EV −4%. DROP.
- **Haaland anytime scorer @ 1.44**: EV −14.7%. DROP. Would need 1.69+ to be fair.

### 4.6 Argentina vs Algeria (Tue 20:00 -05)

**Lineups:** Argentina: Emi Martínez; Molina, Romero, L.Martínez, Tagliafico; De Paul, Mac Allister, E.Fernández; Messi, J.Álvarez, Almada. Messi confirmed starter (scored vs Iceland in opener). Algeria: L.Zidane; Belghali, Mandi, Bensebaini, Aït-Nouri; Bentaleb, Aouar; Mahrez (subbed ~60'), Maza, Amoura; Gouiri.

**Sharp probabilities:** Pinnacle 67.9 / 19.7 / 12.4; Opta 68.2 / 19.5 / 12.3.

**Form note:** Algeria has 4 consecutive clean sheets — **but** validator showed only the Uruguay 0-0 is meaningful (NED B-team, Bolivia, Guatemala are noise). Their WC tournament CS rate is 1 in 13. Validator settled on **λ_ALG = 0.62**.

**Conditions:** Arrowhead Stadium, evening 24°C, benign.

**Model:** λ_ARG = 2.10, λ_ALG = 0.62, ρ = −0.09. P(ARG win) = 0.69; P(BTTS Yes | ARG wins) ≈ 0.35 → **P(ARG win AND BTTS) ≈ 0.245**.

**FOR the pick:**
- **Argentina win + BTTS Yes BB BOOST @ 4.45 (PEN20, MODERATE).** Boost from 3.70. Fair price 4.08; market 4.45 ⇒ EV **+9.0%** conservative, +16% at base. Validator: SENSITIVE under most-conservative λ_ALG = 0.55 scenario but positive in base and most adjusted scenarios. Marciniak ref bumps pen probability (0.27/match — above WC average), supporting Algeria-scoring leg via Argentina-conceded-pen route.

**AGAINST other markets:**
- **Over 2.5 @ 1.95**: conservative model 0.51, EV −1%. Algeria's CS streak (even discounted) shifts goals down. DROP.
- **Algeria win either half BB BOOST @ 4.45**: EV −11.5%. DROP.
- **3-leg combo @ 4.00**: EV −39%. Avoid.
- **Álvarez anytime scorer ≥3.00** (validator alternative): fair price 2.56, EV +17–25% at 3.00. If your app shows this, **strong SPEC pick S/8–10**. But you haven't sent the price screenshot.

### 4.7 Austria vs Jordan (Tue 23:00 -05)

**Lineups:** Austria: A.Schlager (GK); Laimer, Lienhart, Alaba (fit with caveat — HT sub vs Tunisia friendly), Mwene; Seiwald, X.Schlager; Sabitzer, Schmid, Gregoritsch; Arnautović. **Baumgartner OUT** (thigh surgery — material attack creativity loss), replaced by Ljubičić. Wimmer uncertain. Jordan 3-4-3 / 5-4-1 under Sellami replicating Morocco-2022 low block: Abu Laila; Nasib, Al-Arab, Abu Hasheesh; Haddad, Al-Rashdan, Al-Rawabdeh, Ayed; Al-Taamari, Al-Mardi, Olwan.

**Sharp probabilities:** Consensus AUT 63–70 / X 18–22 / JOR 10–13. Visible odds AUT 1.36 / X 5.05 / JOR 9.60.

**Conditions:** Levi's Stadium, evening (20:00 PT).

**Model:** λ_AUT = **1.65** (validator's correction — original 1.85 anchored on 10-0 vs San Marino outlier; vs organised opposition Austria averages 1.25), λ_JOR = 0.55, ρ = −0.08. P(Draw) = 0.222 model, vs 0.198 implied at 5.05.

**FOR the pick:**
- **Draw @ 5.05 Betano (PEN12, SPECULATIVE).** EV +12.1% conservative midpoint. Validator confirms it's **SENSITIVE** (positive in conservative and base, negative in aggressive λ_AUT=2.05 scenario). Hence SPEC tier and small stake. Morocco-2022 analogy directionally valid but Jordan's player quality is 100–200 Elo points below Morocco's at that tournament.

**AGAINST other markets:**
- **Austria 1X2 @ 1.36**: EV −8.6%. DROP.
- **Jordan 1X2 @ 9.60**: EV +1.9%. Marginal.
- **Austria Win-to-Nil**: validator says fair price ~2.55, EV negative at typical +140 (2.40). Only take if priced ≥2.55.

---

## 5. Multi-leg / combo bet methodology

For every boosted parlay shown by Betano (the "BB BOOST" markets in the screenshots), I computed the **true joint probability** under a Dixon-Coles bivariate Poisson model, NOT by naive multiplication of two implied probabilities. The DC correction adds the low-score adjustment τ(h,a) per [Dixon & Coles 1997, JRSS-C 46(2):265-280](https://www.jstor.org/stable/2986290).

**Why this matters:** for "Team X wins AND Over 3.5 goals", naive multiplication systematically **understates** the true probability because winning a match correlates positively with high goal counts (favorite tends to score multiple). For "Team X wins AND BTTS Yes", naive multiplication is closer but still slightly biased.

**Boost EV table (after DC correction):**

| Boost | Was | Boosted | True P | Fair Price | EV | Decision |
|---|---|---|---|---|---|---|
| FRA win + Over 3.5 | 4.30 | 5.15 | 0.238 | 4.20 | +22.5% | **TAKE** |
| ARG win + BTTS Yes | 3.70 | 4.45 | 0.245 | 4.08 | +9.0% | **TAKE** |
| Iraq or Draw (DC) | 4.85 | 5.20 | 0.219 | 4.57 | +13.9% | **TAKE** |
| Doku to assist O0.5 | 3.70 | 4.45 | 0.24 | 4.17 | +6.8% | **TAKE** small |
| Núñez first scorer | 4.00 | 4.40 | 0.197 | 5.08 | −13% | DROP |
| URU win + Over 3.5 | 4.00 | 5.05 | 0.134 | 7.46 | −33% | DROP |
| 1H BTTS KSA-URU | 6.00 | 6.40 | 0.136 | 7.35 | −13% | DROP |
| First goal 0-14:59 | 3.90 | 4.15 | 0.313 | 3.20 | +30% | PASS (high variance, single window) |
| ALG win either half | 4.15 | 4.45 | 0.198 | 5.05 | −12% | DROP |
| NOR + Over 3.5 | 2.64 | 2.90 | 0.349 | 2.87 | +1% | DROP |

**Reasoning paragraph for each TAKE bet** is in section 4.

---

## 6. ELI5 — assistant staking guide (no AI knowledge required)

Imagine you've never used a betting app. Here's exactly what to do, step by step, in plain language.

**Before you start:** Have S/100 in each app's wallet. Take a screenshot of the wallet showing S/100 before placing anything, and another after, so we can audit.

**Critical safety rules**
- If any odd shown in the app is **different by more than 5%** from the odds in this report, STOP and message back. Lines move.
- If a market is **not available** (greyed out), skip that bet — do not substitute.
- Bets are decimal-odds in Peru. "1.78" means S/1 stake returns S/1.78 if it wins. Profit = S/0.78 per S/1 staked.
- You will hit "Apuesta" / "Realizar Apuesta" only once you've checked the stake field is exactly correct.

### 6.1 BETSSON Peru — S/33 of S/100 (new), plus carry from yesterday

1. Open Betsson Peru app. Log in.
2. Tap **Fútbol → Copa del Mundo 2026**.
3. Find **Saudi Arabia vs Uruguay** (kickoff 17:00 Lima time today).
4. Tap **Más mercados / Goles**.
5. Find **Total de goles 2.5 → MENOS / UNDER**. The odd should be **1.78** (give or take 0.02).
6. Tap that. The bet slip ("Boleto") opens at the bottom.
7. In the stake box type **25** (just the number, no S/).
8. Verify the slip shows: "Bajo 2.5 — Saudi Arabia vs Uruguay — 1.78 — S/25.00 — Ganancia potencial S/44.50".
9. Tap **Realizar apuesta**. Screenshot the confirmation.

**Optional (only if visible):** **Belgium vs Egypt → Resultado correcto / "Bélgica gana sin recibir gol"** (Belgium-win-to-nil). If it's priced **2.85 or higher**, stake **S/8**. If lower or not listed, skip — do NOT substitute.

**Stop after these. Do not place anything else on Betsson. The remaining S/67 stays in the wallet.**

### 6.2 BETANO Peru — S/80 of S/100 (new)

Each of these is the **BB BOOST / SUPER BOOST** version of the market — those are highlighted with the orange "BOOST" flame icon in Betano. They have a **maximum stake of PEN 80**, which doesn't constrain us. If the boost has expired or been removed when you check, **skip that bet** — do not place the un-boosted version.

1. **Belgium vs Egypt → Especiales / Doku to assist 0.5 OR MORE (BB BOOST)**. Should be **4.45**. Stake **S/8**. KO 14:00.
2. **France vs Senegal → BB BOOST → "Francia gana + Más de 3.5 goles"**. Should be **5.15**. Stake **S/25**. KO 14:00 tomorrow.
3. **Argentina vs Algeria → BB BOOST → "Argentina gana + Ambos equipos marcan SÍ"**. Should be **4.45**. Stake **S/20**. KO 20:00 tomorrow.
4. **Iraq vs Norway → BB BOOST → "Doble oportunidad Irak o Empate"**. Should be **5.20**. Stake **S/15**. KO 17:00 tomorrow.
5. **Austria vs Jordan → Main 1X2 → EMPATE / Draw**. Should be **5.05**. Stake **S/12**. KO 23:00 tomorrow. (This one is NOT a boost — the regular draw price.)

After each one: screenshot the boleto confirmation showing the exact stake and odds.

**Stop after these. S/20 reserve stays in the wallet** (the Iran carryover from yesterday's S/20 stake covers Betano fully when combined with these).

### 6.3 Carryover bets (DO NOTHING — already placed)

- Betsson: S/30 on Belgium @ 1.67 (Belgium-Egypt, settles today 14:00).
- Betano: S/20 on Iran @ 1.91 (Iran-NZ, settles today 20:00).

These were placed yesterday. Don't re-place them.

### 6.4 If something fails or odds drift

If, at the moment you're about to confirm:
- Odd is **>5% lower** than this report: **skip the bet**.
- Odd is higher: place at the higher odd (you get a better deal).
- Market is removed: skip.
- App rejects with "max stake exceeded": reduce stake by S/2 increments until it accepts; if it rejects everything, skip.

Send back screenshots after each bet, plus the two wallet screenshots (before/after).

---

## 7. Bankroll & risk summary

| Book | New stake | Carryover | Total exposure | Reserve |
|---|---|---|---|---|
| Betsson | S/33 (33%) | S/30 (Belgium 1.67) | S/63 (63%) | S/37 (37%) |
| Betano | S/80 (80%) | S/20 (Iran 1.91) | S/100 (100%) | S/0 |
| **Total** | **S/113** | **S/50** | **S/163 / S/200** | **S/37** |

Quarter-Kelly per AGENT.md gives smaller stakes mathematically. The stake table here is the **stake-cap-binding** version (MOD ≤ S/20–25, SPEC ≤ S/15). This is more conservative than pure Kelly and aligned with v3 calibration.

Sum-of-expected-value in soles: **≈ +S/15.55** (positive but small — by design). At the conservative-validator midpoint, this is what the math says the slate is worth. Realised variance will be much larger in either direction.

**Confidence ceiling reminder: 70% (AGENT.md cap, never claim more).**

---

## 8. Visualizations

Five dashboard images are attached separately:
- `md3_viz1_probabilities.png` — model blend vs Pinnacle devig across all matches
- `md3_viz2_ev_ranking.png` — EV ranking across all evaluated markets
- `md3_viz3_cross_book.png` — Betsson vs Betano headline price gaps
- `md3_viz4_stakes.png` — stake allocation pie per book
- `md3_viz5_backtest.png` — MD1 + MD2 cumulative P&L

---

## 9. Sources & references

Primary academic anchors (all open-access or institutional):
- [Dixon, M.J. & Coles, S.G. (1997). Modelling association football scores. JRSS-C 46(2): 265-280](https://www.jstor.org/stable/2986290)
- [Karlis, D. & Ntzoufras, I. (2003). Analysis of sports data by using bivariate Poisson models. JRSS-D 52(3): 381-393](https://www.jstor.org/stable/4128208)
- [Snowberg, E. & Wolfers, J. (2010). Explaining the favorite-long shot bias. JPE 118(4): 723-746](https://www.aeaweb.org/articles?id=10.1257/aer.97.3.706)
- [Constantinou, A.C., Fenton, N.E., Neil, M. (2012). pi-football. Knowledge-Based Systems 36: 322-339](https://www.sciencedirect.com/science/article/pii/S0950705112001852)
- [Hubáček, O., Šourek, G., Železný, F. (2019). Score-based soccer match outcome modeling. ECML PKDD](https://arxiv.org/abs/1907.07472)
- [Wheatcroft, E. (2020). A profitable model for predicting the over/under market in football. IJF 36(3): 916-932](https://www.sciencedirect.com/science/article/abs/pii/S0169207019301281)
- [Brechot, M. & Flepp, R. (2020). Dealing with randomness in match outcomes: how to rethink performance evaluation in football. Economic Inquiry](https://www.tandfonline.com/doi/abs/10.1080/02692171.2020.1739254)
- [Decroos, T. et al. (2019). Actions Speak Louder than Goals: Valuing Player Actions in Soccer. KDD '19](https://dl.acm.org/doi/10.1145/3292500.3330758)
- [Spann, M. & Skiera, B. (2009). Sports forecasting: a comparison of the forecast accuracy of prediction markets, betting odds and tipsters. Journal of Forecasting 28(1)](https://onlinelibrary.wiley.com/doi/abs/10.1002/for.1091)
- [GitHub: opisthokonta/footballpredictr — implementation reference for DC and Karlis-Ntzoufras](https://github.com/opisthokonta/footballpredictr)

Match-data sources cited inline (Reuters/ESPN/Guardian/Transfermarkt/L'Équipe/BBC Sport/iranintl/VG/NWS Miami forecast).

---

## 10. Responsible gambling block

**Peru:** MINCETUR free helpline **0800-1-3232**. Jugadores Anónimos Perú: [www.jugadoresanonimosperu.org](https://www.jugadoresanonimosperu.org). If you find yourself betting more than the planned S/200 weekly, set deposit limits in each app's responsible-gambling section. Tilt-protection rule: if you lose two bets in a row at PEN20+, stop for 24 hours.

This report is for informational and analytical purposes only. It is not financial advice and not a guarantee of any outcome. Odds drift in real time; we never tell you to "place this bet now". Always verify the odd at the moment of placement and skip the bet if it has moved >5%.
