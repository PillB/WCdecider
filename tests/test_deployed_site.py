"""Live GitHub Pages validation for the exact June 22–27 artifact."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(not os.environ.get("DEPLOY_URL"), reason="DEPLOY_URL is set after Pages deploy")
def test_live_site_matches_expected_commit_and_json():
    from playwright.sync_api import sync_playwright

    url = os.environ["DEPLOY_URL"].rstrip("/") + "/"
    expected_sha = os.environ.get("GITHUB_SHA")
    local = json.loads((ROOT / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        failures = []
        page.on("requestfailed", lambda request: failures.append(request.url))
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("#cards article")
        assert page.locator("#cards article").count() == 32
        assert len(set(page.locator("#cards article").evaluate_all("els => els.map(e => e.dataset.fixtureId)"))) == 32
        assert failures == []
        if expected_sha:
            assert page.locator('meta[name="wcdecider-build"]').get_attribute("content") == expected_sha
        remote = page.evaluate("fetch('wc_june22_27_predictions.json').then(r => r.json())")
        assert remote["model"]["pipeline_sha256"] == local["model"]["pipeline_sha256"]
        page.locator("#lang").click()
        assert "lang-es" in page.locator("body").get_attribute("class")
        browser.close()
