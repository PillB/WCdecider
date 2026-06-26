# SYSTEM STATE: Add research-only double-discount gate and media-ignore protection

## 🎯 Final Success Criteria
- Tweet-derived ideas are integrated only where defensible: feature/model diversification and confidence filters remain research guidance; double-discount is implemented as a non-authorizing margin-of-safety flag.
- The report shows observed market probability, required double-discount threshold, pass/fail status, and bilingual non-authorization language.
- Large local video/audio files under repo `tmp/` are ignored and not staged.
- Pipeline, governance-audit, and browser regression tests pass with updated JSON/report artifacts.

## 🛑 Immutable Constraints & Guardrails
- Follow READ → ACT → WRITE & COMPRESS every phase/turn; `AGENT_STATE.md` remains in this exact schema.
- Do not modify or stage unrelated user-owned files unless explicitly requested. Existing historical/proxy artifacts and untracked local files remain protected.
- Do not copy marketing claims such as “pure math,” “money printer,” or guaranteed win rates into production logic.
- A double-discount gate is research-only and cannot authorize a wager; production authorization remains blocked with `recommendation=null` and `S/0.00` authorized stake.
- Video/audio files in local temp folders must not be committed. If a provided video is unavailable locally, record that limitation rather than inventing lecture content.

## 🕒 Transactional Ledger (Chronological)
- 534 | Read state, inspected worktree, searched temp locations for the Stanford video/audio | No `.mp4`, `.mov`, `.m4v`, `.webm`, `.mkv`, `.mp3`, `.m4a`, or `.wav` file was found in repo `tmp/`, `/tmp`, `/private/tmp`, or the macOS temp directory during scan; only `tmp/AGENT.md` exists locally | Blocked for video analysis
- 535 | Analyzed provided tweet content | Accepted defensible ideas: feature subsampling/ensemble diversity, probability thresholds as filters, margin-of-safety entry, log-return/Sharpe/path-risk evaluation; rejected unsafe claims and fixed win-rate/guarantee rhetoric | Success
- 536 | Added repo temp media ignore rules | `.gitignore` now ignores large media/audio extensions under `tmp/` without ignoring `tmp/AGENT.md` or staging any video | Success
- 537 | Implemented research-only double-discount gate | `public_recommendation` now emits `margin_of_safety` with method, observed market probability, required max probability `0.5 * model decision probability`, pass/fail, `entry_authorized=false`, and bilingual explanation | Success
- 538 | Updated report UI | Ranked comparison tiles show the double-discount gate, observed vs required probabilities, pass/fail status, and bilingual non-authorization text | Success
- 539 | Updated requirements | Added R2.24/R2.25 for research-only double-discount, log returns, drawdown, Sharpe/risk metrics, MAE/MFE-style diagnostics, and win-rate non-sufficiency; added R5.18 for UI disclosure | Success
- 540 | Added tests | Pipeline test validates all ranked comparisons include deterministic non-authorizing double-discount metadata; browser test validates visible English/Spanish double-discount safety text | Success
- 541 | Regenerated canonical artifacts | Ran prediction pipeline, merged research metrics, regenerated report, regenerated datapoint audit, and rebuilt site; audit manifest contains 70,634 datapoints and zero blocked rows | Success
- 542 | Browser validation | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/test_report_playwright_compliance.py -q --tb=short -p no:cacheprovider` passed 28/28 in 90.62s under local-server browser permissions | Success
- 543 | Pipeline/governance validation | `PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/test_june22_27_pipeline.py -q --tb=short -p no:cacheprovider` passed 38/38 in 193.06s | Success
- 544 | Final artifact sanity check | 32 predictions, 108 ranked comparisons, 7 double-discount pass flags, and 0 blocked audit rows | Success
- 545 | Created and amended local implementation commit | Staged only `.gitignore`, governance binding, report/pipeline/tests/requirements, and regenerated June 22–27 artifacts; excluded unrelated historical/proxy files, local untracked files, and repo `tmp/`; local branch is ahead of origin with one implementation commit | Success
- 546 | Pushed implementation branch | `git push origin codex/june23-safety-model-update` succeeded, updating remote branch from `7f016aa` to `b70dfb7`; GitHub warned `wc_june22_27_datapoint_audit.csv` is 76.11 MB and recommends Git LFS | Success
- 547 | Retried draft PR creation | GitHub connector returned `403 Resource not accessible by integration`; draft PR creation remains blocked by integration/auth permissions, but the branch is published | Blocked

## 🧠 Retrospective & Post-Mortem Notes
- The tweet’s “70% confidence” and “80% win rate” framing is not a valid standalone betting promotion rule. The implemented version treats confidence/discount as a review flag subordinate to source freshness, settlement, profitability validation, and audit gates.
- The “Double Discount” rule maps cleanly to football odds as `market_implied_probability <= 0.5 * model_decision_probability`, but this can still be wrong if the model is miscalibrated or the price is stale.
- The Stanford video could not be analyzed because no video/audio file was found in the scanned temp paths. If the file is provided at a concrete path, analyze it before making additional lecture-derived changes.
- Browser tests require permission to bind a local `127.0.0.1` server; sandbox-only runs fail with `PermissionError: [Errno 1] Operation not permitted`.

## 📋 The Execution Pipeline
- [ ] Active Step: Commit and push this state-only publish ledger update.
- [ ] Next Step: After GitHub auth/integration permissions are repaired, open a draft PR from `codex/june23-safety-model-update` to `main`.
- [ ] Future Milestone: If the Stanford lecture file path is supplied, transcribe/analyze the audio and convert only validated insights into gated requirements/tests.
