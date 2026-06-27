# WCdecider

Reproducible FIFA World Cup 2026 probability and betting-market analysis. The current production batch covers **June 22–27, 2026**: 32 fixtures and 216 Betano/Betsson screenshots.

The code-linked production/research walkthrough and validation design are in
[`MODEL_PIPELINE_EXPLAINED.md`](MODEL_PIPELINE_EXPLAINED.md).
The mandatory research and improvement process is defined in
[`STORM_LOOP_ENGINEERING_PROTOCOL.md`](STORM_LOOP_ENGINEERING_PROTOCOL.md).

Live report: https://pillb.github.io/WCdecider/

## Reproduce the current batch

Use Python 3.11. For a clean environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ci.txt
playwright install chromium
```

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B historical_odds_pipeline.py build-canonical
PYTHONDONTWRITEBYTECODE=1 python3 -B model_championship.py
PYTHONDONTWRITEBYTECODE=1 python3 -B wc_june22_27_pipeline.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/merge_research_metrics.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_datapoint_audit.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_report.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/build_site.py
python3 -m http.server 8765 --directory site
```

Acquire and rebuild the evidence-graded historical odds corpus:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B historical_odds_pipeline.py acquire-football-data
PYTHONDONTWRITEBYTECODE=1 python3 -B historical_odds_pipeline.py acquire-the-odds-api-samples
PYTHONDONTWRITEBYTECODE=1 python3 -B historical_odds_pipeline.py build-canonical
```

Open http://127.0.0.1:8765/.

The pipeline requires:

- `wc_2026_matches_june_22-27.csv`
- `wc_2026_results_through_june24.csv`
- `wc_team_elo_baseline_june11.csv`
- `wc_backtest_historical_dataset.csv`
- `odds_june22_23.csv`, `odds_june24.csv`, `odds_june25_26.csv`, `odds_june27.csv`
- `research_june22_23.csv`, `research_june24_25.csv`, `research_june26_27.csv`
- The referenced files under `Screenshots/`

It generates the canonical model dataset, merged odds, Dataset A/B splits, model metrics, provenance, prediction JSON, and a leaf-field subagent audit manifest.

Historical-market and championship artifacts:

- `historical_odds_pipeline.py` segregates timestamp-verified closes from
  timestampless and unknown-timestamp proxies. Authenticated raw provider data
  remains private when redistribution is restricted.
- `historical_odds_coverage.json` currently records 217 legacy proxy events,
  651 selections, and zero primary-validation-eligible rows.
- `model_championship.py` performs nested rolling-origin Elo/market comparisons;
  its small holdout advantage is statistically insecure.
- `HISTORICAL_ODDS_MODEL_CHAMPIONSHIP_PLAN.md` defines the completion and
  profitability-promotion gates.
- Each fixture publishes up to four economically distinct sourced alternatives;
  20 source-limited fixtures currently have only three and disclose the missing
  fourth rank.

Current limitations:

- The production 1X2 model is proper-score-tuned Elo. The Poisson score grid is
  production-critical for totals, BTTS, handicaps, and ranked comparisons, but
  betting-policy profitability is unvalidated.
- The 38-match untouched holdout shows forecast signal, not validated profitability.
- The redistribution-safe public corpus has 142,349 evidence-graded closing
  rows across 8,908 events. A separate ignored private validation fixture has
  1,311 timestamped pre-event rows from 38 events, all outside the frozen
  120-minute closing window. ROI, CLV, staking tiers, and “safe” low-odds bets
  remain unsupported.
- Ranked recommendations are relative sourced comparisons, not evidence of
  profitability. `HALT` identifies material model-market disagreement.
- June 24–27 forecasts are conditional and must be rerun after intervening results and material lineup/odds changes.

## Tests

```bash
pip install -r requirements-ci.txt
playwright install chromium
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/ -q --tb=short
```

Browser tests run the built site through a local HTTP server so dynamic JSON loading is genuinely exercised.

## Adding new matches

Follow [FUTURE_UPDATE_PROTOCOL.md](FUTURE_UPDATE_PROTOCOL.md). At minimum:

1. Preserve screenshot source evidence and transcribe exact odds with image hashes.
2. Add timezone-aware canonical fixtures and direct-URL research provenance.
3. Add elapsed results to Dataset A and rerun chronological model selection.
4. Generate JSON; never hard-code current prices or report numbers in HTML/Python.
5. Assign owner, two replicators, and editor to every published leaf through the audit manifest.
6. Run two independent replication iterations and the full test matrix.
7. Build, push, require green GitHub Actions, and validate the exact commit live.

Read [WCDECIDER_SYSTEM_DESIGN.md](WCDECIDER_SYSTEM_DESIGN.md) first for the
canonical data, modeling, recommendation, bankroll, UI, audit, test, and
deployment contracts. See [PROJECT_UNDERSTANDING.md](PROJECT_UNDERSTANDING.md)
for the implemented source-of-truth map.
