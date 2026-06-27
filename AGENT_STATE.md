# SYSTEM STATE: Promote June 27–29 manual odds batch to active report

## 🎯 Final Success Criteria
- `manual_odds_20260627_20260629.csv` is validated, provenance-corrected, and used as the active odds source for the June 27–29 batch.
- The pipeline regenerates deterministic model, odds, prediction, audit, report, and site artifacts for exactly the 10 active fixtures.
- Local pipeline, report, unit/integration/browser validations pass before deployment.
- GitHub Pages deploys the exact validated artifact and live JSON/DOM parity is checked.

## 🛑 Immutable Constraints & Guardrails
- Follow READ → ACT → WRITE & COMPRESS every phase/turn; `AGENT_STATE.md` remains in this exact schema.
- Do not discard user-owned dirty artifacts without explicit approval.
- Never fabricate results, odds, injuries, probabilities, sources, or audit success.
- Current odds must come from supplied manual CSV/provenance or explicit source evidence.
- If online elapsed results cannot be verified from authoritative sources, keep fixtures as future/pre-match or block the result update.
- Recommendation/staking language remains analysis-only; no football bet is certain.
- Deployment requires exact generated artifacts, passing local gates, and live validation.

## 🕒 Transactional Ledger (Chronological)
- 580 | Read `AGENT_STATE.md`, `WCDECIDER_SYSTEM_DESIGN.md`, `AGENT.md`, `STORM_LOOP_ENGINEERING_PROTOCOL.md`, pipeline/report/build files, and manual odds CSV/provenance | Found 497 manual odds rows across 10 fixtures; provenance sidecar incorrectly records 57 rows; pipeline/report still hard-code June 22–27/32 fixtures | Success
- 581 | Researched elapsed/schedule state and patched active inputs | Added `wc_2026_matches_june_27-29.csv`; appended verified June 25–26 results with source URLs; corrected manual odds provenance row count to 497; switched pipeline active fixtures to June 27–29 and cutoff/release to 2026-06-27T11:00:00-05:00 | Success
- 582 | Patched active-batch pipeline/report assumptions | Pipeline now accepts unique non-32 active fixture counts, skips stale screenshot odds outside active schedule, validates manual provenance row count, accepts expert `source_image` labels, falls back to low-confidence schedule research for missing current fixtures, and report loader checks JSON batch count dynamically | Success
- 583 | Ran clean-room-style validator feedback loop and repaired deterministic blockers | Added `wc_2026_results_through_june26.csv`, updated pipeline docs/source labels, preserved all 497 manual odds rows, normalized promo flags, split complete market groups by source snapshot, and reran pipeline successfully for 10 fixtures | Success
- 584 | Ran focused odds/model integrity checks | Confirmed 497/497 manual rows in normalized odds, manual CSV SHA matches every manual row, 10 predictions exist, every fixture has 4 ranked comparisons, coverage metric is 10, and no complete market group has duplicate selections | Success
- 585 | Completed validator loop and governance binding | Data validator passed; model, replication, and editor validators confirmed content readiness after final hashes; updated `governance/subagent_reviews_june22_27.json` to final byte and semantic hashes | Success
- 586 | Regenerated release artifacts | `scripts/generate_datapoint_audit.py` wrote 35,875 datapoints with blocked=0; regenerated `index.html`; `scripts/build_site.py` rebuilt the deployable `site/` bundle after summary hash checks | Success
- 587 | Ran local validation | Manual odds GUI/build/pipeline tests passed 54/54; Playwright report/translation tests passed 30/30 with local-server permission escalation; audit summary validates current JSON/metrics byte hashes | Success

## 🧠 Retrospective & Post-Mortem Notes
- External result evidence is mixed-source because official FIFA search results were not consistently accessible through search; each added score has a direct URL and retrieval timestamp.
- The new active batch uses existing JSON artifact filenames for low-risk report compatibility, while `batch.active_fixture_file` records the actual canonical fixture file.
- Manual odds provenance mismatch is repaired; the CSV/provenance pair is still the hashable source artifact for manual rows.
- Subagent validation correctly found a half-migrated release layer; regeneration and deployment must remain blocked until governance hashes, audit artifacts, root HTML, tests, and site bundle are synchronized to the current 10-fixture JSON.
- Current release is fail-closed: every fixture has four ranked comparisons and zero authorized recommendations/stakes because profitability promotion remains blocked.

## 📋 The Execution Pipeline
- [ ] Active Step: Commit and push the validated June 27–29 release artifacts.
- [ ] Next Step: Confirm GitHub CI/Pages deploy status.
- [ ] Future Milestone: Validate live GitHub Pages JSON/DOM parity against the local 10-fixture bundle.
