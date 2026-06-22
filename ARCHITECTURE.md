# WCdecider Implemented Architecture

**Updated:** 2026-06-21

WCdecider is a flat, file-based Python pipeline producing a static GitHub Pages report. This document describes the implementation that exists now; future package ideas are not presented as current code.

The cross-cutting behavioral and validation contract is
`WCDECIDER_SYSTEM_DESIGN.md`; this architecture document remains the concise
implemented component map.

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
                         ├── subagent mission/review registry
                         ▼
          wc_june22_27_datapoint_audit.csv
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
- Tournament form and host adjustments are descriptive and zero in the current production probability path.
- A Poisson score grid is descriptive; totals, BTTS, and handicap recommendation policies are not validated in this release.
- Current odds are external CSV data with screenshot SHA-256 hashes.
- No neural model is silently loaded. No reported target is parsed from prose.
- There is no production ensemble/stack in this release. Future candidates must beat calibrated Elo under nested chronological evaluation.

## Website

`wc_june22_27_predictions.json` is the sole current-batch source for:

- 32 match cards
- probabilities
- recommendations and risk classes
- research notes and sources
- English/Spanish fixture text
- field-level audit status and conditional freshness

The HTML contains only batch-independent layout, glossary, workflow visualization, and rendering code. Dynamic content is escaped before insertion and JSON load failures are visible.

Every prediction/metrics JSON leaf is enumerated in the datapoint audit manifest with source/model/mission hashes and distinct owner, replication-1, replication-2, and editor identities. A non-PASS row blocks the site build.

## Validation and deployment

- Unit/integration tests verify schemas, formulas, datasets, hashes, full regeneration, and artifact counts.
- Playwright tests serve `site/` over HTTP and validate 32 unique cards, JSON parity, translations, requests, and responsive overflow.
- GitHub Actions generates the audit manifest, builds `site/`, then runs the full suite against the exact artifact before deployment.
- The generated HTML embeds the exact commit SHA; live validation rejects stale Pages content.
