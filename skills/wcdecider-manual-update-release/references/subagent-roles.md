# Required STORM and validator roles

Use distinct reviewer identities. Do not reuse one agent ID for multiple roles.

## Roles

- STORM moderator: reconciles role evidence, blockers, and release decision.
- Data lineage validator: checks fixture coverage, result evidence, manual odds
  provenance, row counts, normalized market keys, source hashes, and duplicate
  market groups.
- Clean-room replication reviewer: rebuilds from saved files and confirms
  deterministic outputs, zero production stakes, and expected artifact counts.
- ML/stat methodology reviewer: checks leakage, chronological validation,
  calibration, model promotion gates, and research-mode limits.
- Profitability/staking reviewer: checks closing-odds evidence, ROI/CLV claims,
  production bankroll status, educational simulation separation, and risk copy.
- Report/UI editor: checks JSON/DOM parity, bilingual text, mobile behavior,
  S/0 explanations, tooltip safety, and absence of stale fixtures.
- Deployment reliability reviewer: checks CI order, Pages artifact inputs,
  release-validation fetch path, and live validation readiness.

## PASS evidence must include

- Current artifact byte and/or semantic hashes relevant to the role.
- Exact command or inspection evidence.
- Explicit PASS/BLOCKED status.
- Any blocker root cause and required fix.

If a role disconnects, rerun that role. Do not mark release PASS with missing,
duplicated, or non-PASS roles.
