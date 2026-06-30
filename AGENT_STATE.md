# SYSTEM STATE: Update WCdecider From June 30–July 1 Manual Odds CSV

## 🎯 Final Success Criteria
- Validate `manual_odds_20260630_20260701.csv` and matching provenance before trusting any odds row.
- Regenerate model/recommendation/report/site artifacts from source data and generators, including June 30 and July 1 match betting market data from Betsson and Betano where present.
- Run required local validation gates, STORM-style role checks, release preflight, and deployment workflow validation.
- Publish the validated website update through the GitHub workflow and record deployment evidence without fabricating CI/live status.

## 🛑 Immutable Constraints & Guardrails
- Follow READ → ACT → WRITE & COMPRESS every phase/turn; `AGENT_STATE.md` remains in this exact schema.
- Use the repo local skill `skills/wcdecider-manual-update-release/` for this manual-odds update.
- Use GitHub publishing skill instructions for commit/push/deploy handling.
- Do not fabricate odds, results, injuries, sources, probabilities, hashes, validation evidence, CI status, or live deployment status.
- Do not discard user-owned dirty artifacts without explicit approval.
- Production betting recommendations and stakes remain fail-closed unless the published profitability promotion gate passes.
- Generated release artifacts must come from source/data regeneration, not hand-edited JSON/HTML.
- Datapoint audit `blocked_rows > 0` or missing/non-PASS role validation blocks release.

## 🕒 Transactional Ledger (Chronological)
- 611 | Read `AGENT_STATE.md`, local `wcdecider-manual-update-release` skill, required skill references, GitHub `yeet` skill, and CI workflow | Confirmed manual odds/provenance validation, generator-only artifact updates, fail-closed staking, role validation, local gates, and GitHub deployment requirements | Success
- 612 | Inspected repo status, project docs, CI workflow, current generator, tests, and `manual_odds_20260630_20260701.csv` | Found untracked CSV with 420 rows, SHA-256 `b6d09bca89e464b781a9870d4ba81779df354b3968bbac15997b82c39377aba1`, no matching provenance sidecar, 6 canonical fixtures plus 5 abbreviated duplicate fixture IDs, and current pipeline hardcoded to June 27–29 active fixtures/cutoff/provenance | Blocked
- 613 | Checked screenshot/source-image labels and manual odds tooling | CSV references `IMG_8055.jpg`–`IMG_8111.jpg`, but current `Screenshots/` only contains prior `IMG_7523.PNG`–`IMG_7745.PNG`; manual-user-input ingestion hashes the CSV/provenance pair rather than screenshot files, so sidecar must explicitly document unavailable image files/source labels before release | Success
- 614 | Added `manual_odds_20260630_20260701.provenance.json`, added `wc_2026_matches_june_30-july_01.csv`, retargeted active pipeline constants, made datapoint/release batch IDs dynamic, and updated site bundle fixture artifact | Sidecar row count/hash/fields match CSV; canonical fixture file has 6 unique June 30–July 1 fixtures; syntax check passed with `PYTHONPYCACHEPREFIX=/tmp/wcdecider_pycache python3 -m py_compile ...` | Success
- 615 | Ran retargeted generation and subagent-style validation | Initial data lineage/editor/clean-room reviews BLOCKED on kickoff mismatch, post-kickoff odds rows, stale June 27 cutoff copy, imperative app-copy, and stale site artifacts | Blocked
- 616 | Corrected canonical kickoffs to match manual CSV, added post-kickoff manual odds exclusion from normalized evaluation odds, converted app/navigation copy to audit-only wording, rebound governance hashes, regenerated pipeline/audit/release/report/site | Pipeline produced 6 predictions, 0 production recommendations, one elapsed-unverified fixture, 379 normalized pre-match odds rows from 420 raw rows, datapoint audit PASS with 20,133 rows and blocked_rows=0, release validation PASS, root/site JSON hashes match | Success
- 617 | Ran local release preflight and focused tests | `release_preflight.py --repo .` PASS; `pytest tests/test_manual_odds_input_gui.py tests/test_june22_27_pipeline.py tests/test_build_site_safety.py -q --tb=short -p no:cacheprovider` PASS with 55 tests | Success
- 618 | Ran browser/translation gates with localhost permission | Initial sandbox run blocked on localhost bind; escalated rerun passed after updating tests for `elapsed_requires_verified_result` audit-only cards; `pytest tests/test_report_playwright_compliance.py tests/test_translation_toggle.py -q --tb=short -p no:cacheprovider` PASS with 30 tests | Success
- 619 | Ran full local test suite with localhost permission | `pytest tests/ -q --tb=short -p no:cacheprovider` PASS with 144 passed and 14 skipped in 205.71s | Success

## 🧠 Retrospective & Post-Mortem Notes
- Missing provenance was fixed with a sidecar that records CSV hash, row count, source-image limitations, alias mappings, and post-kickoff exclusion policy.
- Correcting kickoff lineage surfaced valid post-kickoff odds leakage; normalized evaluation odds now exclude rows captured at/after kickoff while preserving the raw manual CSV archive.
- Ivory Coast vs Norway is no longer treated as a live/future actionable fixture because its canonical kickoff is before release time and no verified result source was added; it remains audit-only with production stake S/0.
- Browser tests needed lifecycle nuance: verified elapsed results hide betting controls, while elapsed-unverified rows can still render source-audit comparisons and S/0 simulation exclusion.
- The active pipeline is still filename-legacy in places (`wc_june22_27_*`) but the JSON batch metadata, fixture file, provenance, report copy, and site artifact now reflect June 30–July 1.

## 📋 The Execution Pipeline
- [ ] Active Step: Review final diff and commit intended artifacts.
- [ ] Next Step: Push through GitHub deployment path and monitor CI.
- [ ] Future Milestone: Validate GitHub Pages live status for the deployed commit.
