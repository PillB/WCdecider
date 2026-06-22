# June 22–27 Validation Record

## Scope

- 32 World Cup fixtures from June 22 through June 27, 2026.
- 216 source screenshots across Betano and Betsson.
- 40 elapsed World Cup results through June 21.
- Explicit Dataset A/B split and chronological calibration.

## Validation attempts and fixes

1. **Repository audit**
   - Found hard-coded odds, prose-derived targets, optional silent TGNN fallback, duplicate static/dynamic cards, stale fixtures, and partial CI.
   - Replaced the production path with external screenshot odds, deterministic pipeline execution, JSON-only current cards, and full CI.

2. **Screenshot extraction**
   - Date-owned workers transcribed odds and source filenames.
   - June 24 app labels were systematically wrong; direct visual review corrected orange images to Betano and dark images to Betsson.
   - Two exhaustive workers stalled on unsupported exotic markets. The critical fallback was narrowed to independently verified standard 1X2 screens; no cropped prices were inferred.

3. **Pipeline execution**
   - First run failed closed on the app-truncated label `Congo Democra...`.
   - Added the unambiguous normalized alias and reran successfully.

4. **Recommendation classification**
   - A negative-EV selection was initially HALT because divergence was checked before the minimum-EV gate.
   - Reordered classification so EV below +1.5% is always PASS.

5. **Browser parity**
   - Initial Playwright run found Python and JavaScript half-way rounding differed by 0.1 percentage point.
   - Numeric parity now uses an explicit 0.11pp display tolerance while the underlying JSON number remains exact.

## Verified local results

- Canonical fixtures: 32 unique.
- Merged screenshot odds: 756 rows.
- Model rows: 32.
- Dataset A: 132 World Cup finals rows.
- Dataset B: 121 supplementary qualifier/friendly rows.
- Focused pipeline suite: 9 passed.
- Browser/translation suite: 7 passed.
- Final full suite: **60 passed, 1 skipped** in 192.60 seconds.
- The skip is the live Pages check, which requires `DEPLOY_URL` after deployment.

## Independent audit iteration 1

- Data/code audits failed the first iteration on incomplete all-image inventory, pre-fix Dataset A/B semantics, post-cutoff research claims, insufficient provenance formulas, nondeterministic timestamps, and implicit skipping of unsupported markets.
- Model audit rejected STRONG claims because result handicaps were mis-settled, score-grid markets were unvalidated, there was no untouched holdout, current form was double-counted, and selection mining was too broad.
- Fixes:
  - Added a complete 216-image SHA-256 manifest.
  - Sanitized post-cutoff research into a canonical file.
  - Limited recommendations to complete standard full-time 1X2.
  - Corrected Dataset A/B, added an untouched holdout, de-vigged divergence, removed form double-counting, and removed STRONG from this release.
  - Added deterministic timestamps and generated-artifact hashes.

## Independent audit iteration 2

- Data replication passed after generated provenance hashes were isolated from temporary test outputs.
- Code replication passed deterministic regeneration, artifact hashes, site parity, and the exact per-app A/D/B market gate.
- Model audit found no remaining critical implementation defect after the release adopted an abstention-only policy.
- Per-fixture agents independently rebuilt and checked all 32 rows. Every row matched the published JSON; sampled screenshot hashes matched the source images.
- Final independent release audit result: **PASS — no blocking issues**.

## Remaining external gate

- GitHub Actions and exact-commit live validation must run after the release commit is pushed.

## Current release policy

Independent model review established that the probability model’s untouched holdout does not validate a profitable betting-policy tier. Therefore:

- Standard full-time 1X2 comparisons are published.
- Ordinary candidates are `PASS`, even when point-estimate EV is positive.
- Extreme disagreement or EV is `HALT` and shown for additional investigation.
- No `STRONG`, `MODERATE`, or `SPECULATIVE` recommendation is published.
- June 24–27 rows are conditional snapshots and require rerunning after intervening matches.
