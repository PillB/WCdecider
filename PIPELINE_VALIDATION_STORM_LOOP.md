# Production and Research Pipeline Validation Record

Date: 2026-06-24

Canonical method: `STORM_LOOP_ENGINEERING_PROTOCOL.md`. This file is the
release-specific application and evidence record.

## Method

Stanford STORM was used for perspective discovery and evidence synthesis:

1. statistics/model methodology;
2. clean-room replication;
3. data lineage/leakage;
4. editor/student reproducibility.

Loop engineering was used for execution:

```text
invariant → reproduce → adversarial review → patch → focused tests
→ regenerate artifacts → full regression → release gate
```

The final holdout was not used to tune fixes. Fixes addressed evaluation
mechanics, lineage, terminology, and circular quote evaluation.

## Iteration 1 findings and fixes

| Finding | Root cause | Fix | Validation |
|---|---|---|---|
| Same matchday split across tuning windows | row-count boundaries | whole-date tuning and benchmark boundaries | regression tests |
| Bootstrap ignored competition weights | row-level unweighted mean | weighted paired date-block bootstrap | deterministic interval tests |
| Market benchmark compared with itself | benchmark winner reused as challenger | best non-market challenger compared with market | non-zero comparison test |
| “Calibrated” overstated evidence | proper-score tuning mislabeled | `proper_score_tuned_not_empirically_calibrated` terminology | docs/artifact checks |
| Circular EV | quote-derived probability blended into forecast evaluating that quote | independent structural forecast; market probability diagnostic only | probability/EV reconstruction tests |
| Research gates existed only in prose | constants not evaluated | actual fixture/team edge counts and booleans exported | benchmark tests |
| Results/research/odds cutoff not executable | trusted filenames and partial timestamps | timezone-aware cutoff and pre-kickoff rejection | cutoff regression test |
| June 27 capture times lacked dates | time-only source transcription | frozen file-level capture-date metadata, explicitly exported | cutoff regression test |
| Historical-odds audit used legacy locator | stale artifact mapping | canonical coverage/CSV/manifest mapping | regenerated audit |
| Research audit kept only first URL | lossy bundle mapping | preserve complete reviewed URL bundle | regenerated audit |
| Documentation contradicted CI/model roles | stale commands and terminology | canonical command, Poisson role, benchmark/deployment, independent EV updated | editor search and browser tests |
| Source bundle required `.git` | unconditional `git rev-parse` | `SOURCE_BUNDLE_SHA` fallback with visible unversioned marker | code inspection; release tests |

## Current v5 statistical evidence

- Production 1X2: proper-score-tuned Elo, development-only.
- Expanded markets: tuned Elo independent-Poisson score grid.
- Research shadow: Dixon-Coles low-score correction, zero production weight.
- Benchmark winner: de-vigged market proxy.
- Development comparison block: 29 priced rows after whole-date split. It is
  not a confirmatory holdout because prior iterations used its feedback.
- Best price-independent challenger: tuned Elo.
- Weighted date-block bootstrap:
  - 13 blocks;
  - challenger minus market log loss: approximately `-0.00139`;
  - 95% interval approximately `[-0.20554, 0.21607]`;
  - secure improvement: false.
- Historical profitability: blocked because zero rows satisfy the
  timestamp-grade closing-price gate.

## Test evidence

- Focused model/lineage/artifact suite: 44 passed.
- Full sandbox run: 89 passed, 1 skipped; browser tests could not bind
  `127.0.0.1` under sandbox permissions.
- Browser/mobile/bilingual rerun with localhost permission: 20 passed.
- The sandbox-only failures were environment permission errors, not assertion
  failures.

## V5 release status

- Model version: `june22_27_v5_fail_closed_development_only`.
- All executable recommendations are null.
- All ranked rows are audit comparisons marked `ABSTAIN`.
- All stakes are zero and S/100 per app remains unallocated.
- Prior v4 review approval is revoked.
- The field-level audit remains BLOCKED pending new hash-bound reviews and
  confirmatory evidence.

## Honest unresolved release gates

1. A new sealed prospective holdout is required; the existing development
   comparison block cannot support confirmatory calibration claims.
2. Zero historical odds rows satisfy the timestamp-grade closing-price gate,
   so ROI, CLV, staking, and profitability claims remain prohibited.
3. Date-matched authoritative historical rating snapshots are unavailable.
   Supplementary history now starts from neutral 1500 and remains an interim
   development feature regime.
4. GitHub CLI authentication is invalid. `gh auth login -h github.com` is
   required before any later reviewed safety release can be published.
5. Field-specific OSINT citations are still bundled per fixture. The audit now
   preserves the full bundle instead of falsely selecting one URL, but future
   data acquisition should store one citation record per claim category.

No deployment should claim completion until these gates are cleared.

## Revoked v4 review record

The former v4 hash-bound PASS evidence is retained only as historical context.
Independent validators revoked it after finding data-integrity and
authorization defects. It must not be used to approve v5 or any deployment.
