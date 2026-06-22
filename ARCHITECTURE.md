# WCdecider Implemented Architecture

**Updated:** 2026-06-21

WCdecider is a flat, file-based Python pipeline producing a static GitHub Pages report. This document describes the implementation that exists now; future package ideas are not presented as current code.

## Data flow

```text
Screenshots + canonical fixtures + direct-URL OSINT
                         │
                         ▼
       date-owned odds/research CSV artifacts
                         │
historical data ─────────┼──── elapsed WC results
                         ▼
             wc_june22_27_pipeline.py
         ┌───────────────┼────────────────┐
         ▼               ▼                ▼
 Dataset A/B CSVs   model/odds CSVs   metrics/provenance
                         │
                         ▼
            wc_june22_27_predictions.json
                         │
                         ▼
             scripts/generate_report.py
                         │
                         ▼
                    index.html
                         │
                         ▼
               scripts/build_site.py
                         │
                         ▼
               site/ → GitHub Pages
```

## Sources and generated artifacts

- Sources: `Screenshots/`, canonical fixture/results/Elo/historical CSVs, date-owned odds and research CSVs, Python scripts.
- Generated model outputs: `wc_dataset_a_world_cups.csv`, `wc_dataset_b_supplementary.csv`, `wc_june22_27_model_dataset.csv`, `wc_odds_june_22-27.csv`, metrics, provenance, predictions JSON.
- Report source: generated root `index.html`.
- Deployment artifact: `site/`; the build fails if required artifacts are missing.

## Production model

- Historical inputs are explicitly split:
  - Dataset A: World Cup rows.
  - Dataset B: qualifiers and friendlies used as supplementary evidence.
- A three-way Elo conversion is selected using chronological evaluation windows.
- Current ratings are updated deterministically from the 40 World Cup results through June 21.
- Tournament form and host adjustments are bounded and recorded.
- A Poisson score grid supports totals, BTTS, and Asian handicap settlement.
- Current odds are external CSV data with screenshot SHA-256 hashes.
- No neural model is silently loaded. No reported target is parsed from prose.

## Website

`wc_june22_27_predictions.json` is the sole current-batch source for:

- 32 match cards
- probabilities
- recommendations and risk classes
- research notes and sources
- English/Spanish fixture text

The HTML contains only batch-independent layout, glossary, workflow visualization, and rendering code. Dynamic content is escaped before insertion and JSON load failures are visible.

## Validation and deployment

- Unit/integration tests verify schemas, formulas, datasets, hashes, full regeneration, and artifact counts.
- Playwright tests serve `site/` over HTTP and validate 32 unique cards, JSON parity, translations, requests, and responsive overflow.
- GitHub Actions runs the full suite before deployment.
- The generated HTML embeds the exact commit SHA; live validation rejects stale Pages content.
