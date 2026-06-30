# WCdecider manual odds update protocol

## Intake checklist

- Identify the new `manual_odds_YYYYMMDD_YYYYMMDD.csv`.
- Require matching `manual_odds_YYYYMMDD_YYYYMMDD.provenance.json`.
- Confirm provenance schema is `manual_wcdecider_odds_v1`.
- Confirm sidecar `output_csv`, row count, SHA-256, capture window, operator
  notes, and input method match the CSV.
- Confirm the active fixture CSV covers exactly the intended release dates.
- Treat missing elapsed results as pre-match unless verified from explicit
  sources.

## Regeneration order

Use the workflow in `.github/workflows/deploy.yml` as the source of truth:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B historical_odds_pipeline.py build-canonical
PYTHONDONTWRITEBYTECODE=1 python3 -B model_championship.py
PYTHONDONTWRITEBYTECODE=1 python3 -B promotion_pipeline.py
PYTHONDONTWRITEBYTECODE=1 python3 -B wc_june22_27_pipeline.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/merge_research_metrics.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_datapoint_audit.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_release_validation.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/generate_report.py
PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/build_site.py
```

If the active batch pipeline filename changes, discover it from the workflow,
README, and `AGENT_STATE.md`; do not guess.

## Local gates

Minimum gates for a normal manual-odds update:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/test_manual_odds_input_gui.py tests/test_june22_27_pipeline.py tests/test_build_site_safety.py -q --tb=short -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/test_report_playwright_compliance.py tests/test_translation_toggle.py -q --tb=short -p no:cacheprovider
```

Run the full suite when release validation, generated report logic, model
selection, stake simulation, or deployment behavior changes:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest tests/ -q --tb=short -p no:cacheprovider
```

Playwright tests may need permission to bind localhost.

## Deploy checklist

- Confirm `git status` contains only intended files.
- Stage explicitly; do not use broad staging in a mixed worktree.
- Commit with a release-focused message.
- Push to the branch and to `main` only after gates pass.
- Monitor the `Build, Test & Deploy GitHub Pages` workflow.
- Validate live deployed page with `scripts/wait_and_validate_deploy.py`.
