# Validation and hallucination guardrails

## Data truth

- Do not create odds, screenshots, results, injuries, lineups, weather, or news
  from memory.
- Every manual odds row must preserve `source_kind=manual_user_input`,
  `source_file`, `source_sha256`, capture time derivation, source image label,
  and normalized market key.
- Results added after kickoff require explicit source URLs and retrieval
  timestamps. If verification is unavailable, keep fixtures pre-match.
- Do not infer bookmaker prices from fair odds or model probabilities.

## Hashes and generated artifacts

- Treat generated files as outputs of source code and data. Fix generators and
  rerun rather than hand-editing generated JSON/HTML.
- Field datapoint audit is authoritative for JSON leaf coverage.
- `blocked_rows > 0` blocks release.
- Prefer semantic hashes for prediction/metrics JSON when CI/local platform
  byte drift is possible.
- Byte-bind prompt packs, static manual sources, and fixed review inputs.

## Recommendations and staking

- Production `recommendation` stays `null` and production stake stays `0.0`
  unless the published profitability promotion gate passes.
- Educational stake simulation must be labeled hypothetical and separate from
  production authorization.
- A displayed gross amount includes stake and is not profit.
- S/0 exclusions should be explained in plain language.
- Avoid “surefire”, “near certain”, “guaranteed profit”, “place this bet”, and
  imperative app-navigation instructions unless a future authorized release
  explicitly changes the policy.

## UI/report safety

- Every visible number must come from JSON, metrics, audit summary, or explicit
  source files.
- The report must load small audit summaries on mobile; never require the
  browser to download the large datapoint CSV.
- Bilingual English/Spanish text must remain synchronized.
- Hover/tap explanations must not be clipped on mobile.
