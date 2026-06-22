# WCdecider

Reproducible FIFA World Cup 2026 probability and betting-market analysis. The current production batch covers **June 22–27, 2026**: 32 fixtures and 216 Betano/Betsson screenshots.

Live report: https://pillb.github.io/WCdecider/

## Reproduce the current batch

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B wc_june22_27_pipeline.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_datapoint_audit.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_report.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/build_site.py
python3 -m http.server 8765 --directory site
```

Open http://127.0.0.1:8765/.

The pipeline requires:

- `wc_2026_matches_june_22-27.csv`
- `wc_2026_results_through_june21.csv`
- `wc_team_elo_baseline_june11.csv`
- `wc_backtest_historical_dataset.csv`
- `odds_june22_23.csv`, `odds_june24.csv`, `odds_june25_26.csv`, `odds_june27.csv`
- `research_june22_23.csv`, `research_june24_25.csv`, `research_june26_27.csv`
- The referenced files under `Screenshots/`

It generates the canonical model dataset, merged odds, Dataset A/B splits, model metrics, provenance, prediction JSON, and a leaf-field subagent audit manifest.

Current limitations:

- The production model is calibrated Elo 1X2; Poisson outputs are descriptive.
- The 38-match untouched holdout shows forecast signal, not validated profitability.
- Historical closing odds are incomplete, so ROI, CLV, staking tiers, and “safe” low-odds bets are not supported.
- The release contains zero actionable bets. `PASS` means abstain; `HALT` means investigate an implausible/model-market disagreement.
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

See [PROJECT_UNDERSTANDING.md](PROJECT_UNDERSTANDING.md) for the implemented architecture and source-of-truth map.
