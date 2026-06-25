# STORM and Loop-Engineering Protocol

Status: mandatory for every material data, model, recommendation, report, or
deployment change.

This file defines how WCdecider uses Stanford STORM and loop engineering. The
methods solve different problems and must not be conflated.

## 1. Stanford STORM: research synthesis

WCdecider uses the STORM pattern—perspective discovery, source-grounded
questioning, outline synthesis, and grounded writing—to organize research and
review.

Required sequence:

1. **Define the research question and evidence boundary.**
   - State what decision the research may change.
   - State the cutoff, permitted sources, and claims that remain unvalidated.
2. **Discover distinct perspectives.**
   - At minimum: model/statistics, clean-room replication, data
     lineage/leakage, and report/editor/user experience.
   - Perspectives must ask different questions rather than duplicate one
     generic review.
3. **Run source-grounded investigations.**
   - Trace claims to primary literature, executable code, source data,
     generated artifacts, and tests.
   - Separate directly observed evidence from inference.
4. **Synthesize an evidence outline before writing conclusions.**
   - Group agreements, contradictions, defects, unknowns, and promotion gates.
   - Preserve dissent; do not average conflicting reviews into a false PASS.
5. **Write or update the implementation/documentation from the outline.**
   - Every material claim must link to code, an artifact, a test, or a cited
     source.
6. **Bind review evidence to the exact release.**
   - Record model version and exact prediction/metrics hashes.
   - A review of an earlier artifact set cannot approve a later release.

STORM is not:

- a substitute for statistical testing;
- permission to let agents vote a claim into truth;
- an excuse to cite secondary summaries when primary evidence is available;
- a reason to declare every registered model tested;
- a release approval unless the exact artifact hashes were reviewed.

## 2. Loop engineering: executable improvement

WCdecider uses a bounded, test-driven repair loop:

```text
specify invariant and stop condition
→ reproduce the current behavior
→ measure against a frozen evaluation
→ obtain adversarial review
→ classify the root cause
→ make the smallest evidence-supported change
→ run focused tests
→ regenerate dependent artifacts
→ run integration, black-box, and full regression tests
→ retrospect and either stop, iterate, or block
```

Every loop iteration must record:

- invariant or hypothesis;
- baseline command and result;
- defect and root cause;
- files and behavior changed;
- focused and regression test evidence;
- artifact hashes when outputs changed;
- retrospective;
- next condition or explicit blocker.

Stop only when:

1. implementation, evidence, and communication agree;
2. focused, integration, and black-box gates pass;
3. release-current independent reviews are hash-bound;
4. no unresolved material discrepancy remains;
5. deployment and live validation pass when publication is in scope.

Block rather than simulate success when credentials, source evidence, reviewer
capacity, or required data are unavailable.

## 3. Statistical safeguards inside the loop

- Never repeatedly tune against the final untouched holdout.
- A failed promotion returns to inner selection/outer evaluation and requires
  new future holdout evidence for a new confirmatory claim.
- Register searched variants and control multiplicity before promotion.
- Use chronological/date-block splits for time-dependent football data.
- Use proper scores and reliability evidence, not accuracy alone.
- Compare models on identical observations with dependence-aware uncertainty.
- Keep forecast probability independent from the quote used to calculate EV
  unless a stack has earned its weight out of sample.
- Never optimize or claim profitability without timestamp-eligible executable
  historical prices and a frozen policy evaluation.

## 4. Required phase template

Each material phase must use this template in its design or validation record:

```markdown
### Phase: <name>

Research question:
Evidence boundary:
STORM perspectives:
Invariant:
Baseline reproduction:
Finding/root cause:
Change:
Focused tests:
Integration/black-box tests:
Retrospective:
Release status: PASS / BLOCKED / DIVERGED
Next condition:
```

## 5. Canonical records

- Persistent operational state: `AGENT_STATE.md`
- Binding agent behavior: `AGENT.md`
- Technical contract: `WCDECIDER_SYSTEM_DESIGN.md`
- Pipeline explanation: `MODEL_PIPELINE_EXPLAINED.md`
- Per-release evidence: `PIPELINE_VALIDATION_STORM_LOOP.md`

The per-release record may change. This protocol remains the mandatory method
for future releases.
