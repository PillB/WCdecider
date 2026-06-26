# SYSTEM STATE: Prefer manual odds CSVs over screenshots after June 26

## 🎯 Final Success Criteria
- Root-level `manual_odds_*.csv` files created by the manual GUI are automatically discovered by the June 22–27 model pipeline.
- Manual odds require matching `.provenance.json` sidecars, use manual source tokens, and hash the CSV/provenance pair instead of any screenshot.
- For fixtures after 2026-06-26, manual odds replace matching screenshot rows by normalized fixture/app/market/selection/line key and append unmatched supported rows.
- Screenshot-derived odds remain authoritative for June 26 and earlier unless a future request changes that boundary.
- Focused pipeline and GUI regression tests pass without relying on repo-local generated manual odds files.

## 🛑 Immutable Constraints & Guardrails
- Follow READ → ACT → WRITE & COMPRESS every phase/turn; `AGENT_STATE.md` remains in this exact schema.
- Do not stage or modify unrelated user-owned historical/proxy/local artifacts.
- Do not commit large video/audio files; local temp media remains ignored.
- Manual odds are user observations, not screenshot OCR. They must be marked with manual source tokens and provenance.
- Manual odds ingestion must fail closed on missing/invalid provenance for applicable files, and must not require a `Screenshots/<source_image>` file.
- Current production staking gates remain separate from this ingestion change.

## 🕒 Transactional Ledger (Chronological)
- 548 | Read state and inspected current raw/normalized odds schemas | Existing raw odds parts use fields `fixture_id`, `fixture_display`, `kickoff_local`, `app`, `market_original`, `market_id`, `selection_original`, `selection_id`, `line`, `odds`, `promo`, `source_image`, `capture_time`, `notes`; normalized pipeline later derives market family/completeness | Success
- 549 | Created `manual_odds_input_gui.py` | Standalone stdlib Tkinter GUI with configurable `--start`, `--end`, `--output`, `--append`; defaults to next three days; supports fixture/team/kickoff entry and Betsson/Betano odds for 1X2, totals, BTTS, Asian handicap, and double chance | Success
- 550 | Added headless script modes | `--simulate` writes deterministic sample odds/provenance without opening GUI; `--self-test` validates raw schema, source token, complete 1X2 rows, and provenance JSON | Success
- 551 | Added validation/export logic | Fatal validation catches unsupported apps/markets, invalid decimal odds, missing required lines, duplicate rows, and no rows; warnings flag incomplete or missing 1X2 fixture/app groups | Success
- 552 | Added `tests/test_manual_odds_input_gui.py` | Pytest covers simulated raw schema/provenance, manual source tokens, complete 1X2 triplet, bad odds rejection, and partial 1X2 warning | Success
- 553 | Ran script validation | `PYTHONDONTWRITEBYTECODE=1 python3 -B manual_odds_input_gui.py --self-test` passed | Success
- 554 | Implemented manual odds discovery and provenance validation | Pipeline discovers root-level `manual_odds_*.csv`, requires schema `manual_wcdecider_odds_v1`, requires matching raw fields, and includes manual CSV/provenance files in input hashes | Success
- 555 | Implemented manual odds source handling | Manual rows get `source_kind=manual_user_input`, `source_file=<manual_csv>`, and `source_sha256` from combined CSV/provenance hash; screenshot rows keep screenshot hashes | Success
- 556 | Implemented post-June-26 preference logic | Manual rows for fixtures after 2026-06-26 replace screenshot rows by normalized semantic row key; June 26 and earlier manual rows are ignored before capture-time validation | Success
- 557 | Preserved screenshot manifest semantics | Screenshot inventory counts only screenshot rows, so manual source tokens do not pollute screenshot coverage reporting | Success
- 558 | Updated provenance documentation emitted by pipeline | Provenance now documents manual override files, normalized replacement key, source_kind/source_file, and manual source hashing semantics | Success
- 559 | Added pipeline regression tests | Tests cover manual replacement after June 26, no override for June 26 or earlier, missing provenance fail-closed behavior, and screenshot/manual source assertions | Success
- 560 | Fixed failed prefilter edge case | Initial implementation validated old-fixture manual capture times before ignoring them; changed manual ingestion to ignore June 26-and-earlier rows before timestamp validation | Success
- 561 | Ran targeted ingestion validation | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest` for the four new/updated ingestion tests passed 4/4 | Success
- 562 | Ran full focused validation | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/test_manual_odds_input_gui.py tests/test_june22_27_pipeline.py -q --tb=short -p no:cacheprovider` passed 43/43 in 206.23s | Success
- 563 | Inspected final worktree | Relevant modified files are `wc_june22_27_pipeline.py`, `tests/test_june22_27_pipeline.py`, `manual_odds_input_gui.py`, `tests/test_manual_odds_input_gui.py`, and `AGENT_STATE.md`; unrelated dirty artifacts remain untouched | Success
- 564 | Re-read state and analyzed dirty files before commit | Relevant scoped files are the manual odds GUI, its tests, pipeline ingestion changes, pipeline tests, and `AGENT_STATE.md`; unrelated dirty/generated/local files remain excluded | Success
- 565 | Re-ran focused validation before staging | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/test_manual_odds_input_gui.py` plus four manual-ingestion pipeline tests passed 6/6 | Success
- 566 | Staged scoped files only | Staged `AGENT_STATE.md`, `manual_odds_input_gui.py`, `tests/test_manual_odds_input_gui.py`, `tests/test_june22_27_pipeline.py`, and `wc_june22_27_pipeline.py` | Success
- 567 | Created local commit | Commit `6e64461` with message `Add manual odds CSV ingestion`; excluded unrelated dirty/generated/local artifacts | Success
- 568 | Checked post-commit status | Only previously excluded dirty files remain outside the commit | Success

## 🧠 Retrospective & Post-Mortem Notes
- Raw screenshot `selection_id` values are not consistently semantic (`croatia` vs GUI `home`), so override matching uses the normalized semantic selection (`A/D/B`, over/under, home/away) rather than raw selection IDs.
- Manual odds for June 26 and earlier are intentionally ignored before capture-time validation so stale/manual drafts for elapsed fixtures cannot break the pipeline.
- The manual CSV/provenance pair is the source evidence for manual odds; screenshots remain the source evidence for screenshot-derived odds.
- The focused test suite is slow because it includes broad pipeline validation; it passed after the prefilter fix.
- Existing unrelated dirty files are still present and should be reviewed separately before any commit/publish operation.
- Dirty files intentionally excluded from this commit: `historical_odds_provenance.txt`, `historical_odds_proxy.csv`, `wc_june22_27_datapoint_audit.csv`, `wc_june22_27_datapoint_audit_summary.json`, `wc_model_production_results.csv`, `CAN_QAT_card_replicated.html`, `VALIDATION_ITERATION_JUNE17_21.md`, `wc_screenshots_inventory_clean.csv`, and repo `tmp/`.

## 📋 The Execution Pipeline
- [ ] Active Step: Report commit result and remaining excluded dirty files.
- [ ] Next Step: If requested, push branch or separately review/clean the excluded generated/local artifacts.
- [ ] Future Milestone: Run a real `manual_odds_YYYYMMDD_YYYYMMDD.csv` export for post-June-26 fixtures, rebuild model artifacts, validate report/site consistency, then deploy.
