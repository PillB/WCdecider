# SYSTEM STATE: Replace blank-prone manual odds Tkinter UI with FastAPI web input

## 🎯 Final Success Criteria
- Running `python3 manual_odds_input_gui.py --start 2026-06-27 --end 2026-06-29` starts a local FastAPI web form instead of opening Tkinter, and falls forward to the next free localhost port if the preferred port is occupied.
- The web form supports Betsson/Betano manual odds entry for 1X2, totals, BTTS, Asian handicap, and double chance.
- The web route, CLI, and pure conversion functions all write the same `manual_wcdecider_odds_v1` raw CSV/provenance schema consumed by the model pipeline.
- Tests validate form rendering, route add/save/download behavior, manual CSV schema, and post-June-26 manual odds ingestion.

## 🛑 Immutable Constraints & Guardrails
- Follow READ → ACT → WRITE & COMPRESS every phase/turn; `AGENT_STATE.md` remains in this exact schema.
- Do not discard user-owned dirty artifacts without explicit approval.
- Do not commit large video/audio files; local temp media remains ignored.
- Manual odds are user observations, not screenshot OCR. They must be marked with manual source tokens and provenance.
- Manual odds ingestion must fail closed on missing/invalid provenance for applicable files, and must not require a `Screenshots/<source_image>` file.
- Keep the interactive odds-entry tool local-only by default: `127.0.0.1` host and explicit output CSV/provenance files.

## 🕒 Transactional Ledger (Chronological)
- 548 | Read state and inspected current raw/normalized odds schemas | Existing raw odds parts use fields `fixture_id`, `fixture_display`, `kickoff_local`, `app`, `market_original`, `market_id`, `selection_original`, `selection_id`, `line`, `odds`, `promo`, `source_image`, `capture_time`, `notes`; normalized pipeline later derives market family/completeness | Success
- 549 | Created `manual_odds_input_gui.py` | Standalone manual odds input script with configurable `--start`, `--end`, `--output`, `--append`; defaults to next three days; supports fixture/team/kickoff entry and Betsson/Betano odds for 1X2, totals, BTTS, Asian handicap, and double chance | Success
- 550 | Added headless script modes | `--simulate` writes deterministic sample odds/provenance without opening an interactive UI; `--self-test` validates raw schema, source token, complete 1X2 rows, and provenance JSON | Success
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
- 561 | Ran targeted ingestion validation | Manual-ingestion pipeline tests passed | Success
- 562 | Committed manual odds ingestion | Commit `6544668` added manual odds CSV ingestion | Success
- 563 | Cleaned generated artifacts and legacy locks | Commit `c9aaf2d` cleaned generated artifacts, legacy locks, and local scratch ignore state | Success
- 564 | Diagnosed blank Tkinter GUI | Tk object construction succeeded but macOS/Tk refresh hung in this environment; screenshot-based validation was unreliable | Blocked
- 565 | Hardened Tkinter layout as interim mitigation | Commit `57e2ff9` added explicit geometry, scrollable content, and headless layout diagnostics | Success
- 566 | Re-evaluated Tkinter retention | User correctly rejected keeping an inferior Tkinter path; Tkinter code became unnecessary surface area | Diverged
- 567 | Refactored interactive path to FastAPI-only | Removed `ManualOddsGui`, Tkinter imports, `--diagnose-gui`, GUI geometry constants, and Tk launch path; default CLI now runs local FastAPI on `127.0.0.1:8765` | Success
- 568 | Preserved shared data path | Added framework-free `rows_from_form_fields()` and `selection_display_name()` so FastAPI route, tests, and future UIs use the same row construction/validation before `write_rows()` | Success
- 569 | Added web form contract and renderer | Added `web_layout_spec()`, `--diagnose-web`, server-rendered responsive HTML, market-card filtering JavaScript, row table, save/download actions, and local health endpoint | Success
- 570 | Added FastAPI route layer | Added `/`, `/health`, `/add`, `/save`, `/clear`, and `/download`; route body parsing uses `parse_qs` and avoids multipart dependency | Success
- 571 | Fixed FastAPI annotation issue | `from __future__ import annotations` caused locally imported `Request` to resolve as a missing query parameter; moved `Request` to module scope with safe optional import | Success
- 572 | Added dependencies | Added `fastapi==0.115.6`, `uvicorn==0.32.1`, and `httpx==0.28.1` to `requirements-ci.txt`; installed locally for route validation | Success
- 573 | Added route-level tests | `tests/test_manual_odds_input_gui.py` now verifies web contract, HTML sections/market switching, form-field conversion, FastAPI `/add`, `/save`, `/download`, and `/health` | Success
- 574 | Ran validation | `pytest tests/test_manual_odds_input_gui.py` passed 7/7; manual-ingestion pipeline subset passed 3/3; `manual_odds_input_gui.py --self-test` passed; `manual_odds_input_gui.py --diagnose-web` printed expected contract; AST syntax check passed; `git diff --check` passed | Success
- 575 | Ran black-box server smoke | Sandbox blocked local bind; reran with approval and confirmed CLI FastAPI server starts and `/health` returns expected JSON | Success
- 576 | Diagnosed user port-bind failure | User command failed because `127.0.0.1:8765` was already occupied; current script printed the URL before Uvicorn attempted to bind and then exited on `Errno 48` | Success
- 577 | Implemented occupied-port fallback | Added `bind_available_server_socket()` to pre-bind the preferred port or next available port, then pass the bound socket to Uvicorn; printed URL now reflects the actual usable port | Success
- 578 | Added regression coverage | Added pure unit test with fake sockets proving fallback from 8765 to 8766 without needing real network bind permission | Success
- 579 | Ran validation | `pytest tests/test_manual_odds_input_gui.py` passed 8/8; `manual_odds_input_gui.py --self-test` passed; AST syntax check passed; `git diff --check` passed; approved black-box smoke occupied port 18000 and confirmed CLI served `/health` on 18001 | Success

## 🧠 Retrospective & Post-Mortem Notes
- Raw screenshot `selection_id` values are not consistently semantic (`croatia` vs `home`), so override matching uses normalized semantic selection (`A/D/B`, over/under, home/away) rather than raw selection IDs.
- Manual odds for June 26 and earlier are intentionally ignored before capture-time validation so stale/manual drafts for elapsed fixtures cannot break the pipeline.
- The manual CSV/provenance pair is the source evidence for manual odds; screenshots remain the source evidence for screenshot-derived odds.
- Tkinter is removed rather than retained because the failure mode was platform/window-server dependent and not worth supporting for a straightforward data-entry workflow.
- FastAPI route validation required explicit `httpx`; Starlette `TestClient` does not work without it.
- Route annotations must use a globally resolvable `Request` type because postponed annotations otherwise make FastAPI treat `request` as a required query parameter.
- Uvicorn should receive a pre-bound socket for this tool. That both fixes occupied default ports and avoids a race between "port available" checks and actual server bind.

## 📋 The Execution Pipeline
- [ ] Active Step: Stage and commit the occupied-port fallback fix.
- [ ] Next Step: Tell the user to rerun the same command and use the printed fallback URL if 8765 remains occupied.
- [ ] Future Milestone: Use the saved `manual_odds_YYYYMMDD_YYYYMMDD.csv` files for post-June-26 fixtures, rebuild model artifacts, validate report/site consistency, then deploy.
