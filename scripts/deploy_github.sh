#!/usr/bin/env bash
# One-shot: create repo (if needed), push main, wait for Pages, Playwright validate.
# 
# Per AGENT.md Automated Update Protocol: This is the deploy + live validation step.
# Run after build and full local tests (including playwright compliance for correct layout of *all* matches).
# Must succeed with 0 failures in test_deployed_site.py (all matches implemented, bilingual, no 404s, toggle works).
# See AGENT.md for the complete automatic process: new screenshots → research/CSV → core model retrain/pipeline rerun → website sections increment + recs update → tests → this script → live validate.
set -euo pipefail
cd "$(dirname "$0")/.."

OWNER="${GITHUB_OWNER:-PillB}"
REPO="${GITHUB_REPO:-WCdecider}"
DEPLOY_URL="https://${OWNER}.github.io/${REPO}/"

if ! command -v gh >/dev/null 2>&1; then
  echo "Install GitHub CLI: brew install gh && gh auth login"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Run: gh auth login"
  exit 1
fi

echo "[1/5] Ensure GitHub repo ${OWNER}/${REPO}"
if ! gh repo view "${OWNER}/${REPO}" >/dev/null 2>&1; then
  gh repo create "${REPO}" --public --source=. --remote=origin --push
else
  git remote add origin "https://github.com/${OWNER}/${REPO}.git" 2>/dev/null || \
    git remote set-url origin "https://github.com/${OWNER}/${REPO}.git"
  git push -u origin main
fi

echo "[2/5] Enable GitHub Pages (GitHub Actions source)"
if ! gh api "repos/${OWNER}/${REPO}/pages" >/dev/null 2>&1; then
  gh api --method POST "repos/${OWNER}/${REPO}/pages" --input - <<< '{"build_type":"workflow"}'
else
  gh api -X PUT "repos/${OWNER}/${REPO}/pages" -f build_type=workflow 2>/dev/null || true
fi

echo "[3/5] Wait for deploy workflow"
gh run watch --exit-status || true

echo "[4/5] Wait for live site + Playwright validate"
export DEPLOY_URL
python3 scripts/wait_and_validate_deploy.py

echo "[5/5] Done — ${DEPLOY_URL}"