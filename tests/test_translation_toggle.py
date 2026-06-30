"""Static and browser tests for complete EN/ES report behavior."""

from __future__ import annotations

from pathlib import Path

from test_report_playwright_compliance import serve

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


def test_static_report_contains_bilingual_contract():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'class="en"' in html
    assert 'class="es"' in html
    assert "6 active fixtures. One auditable pipeline." in html
    assert "6 partidos activos. Un pipeline auditable." in html
    assert "lang-es .en" in html


def test_toggle_changes_visible_language():
    from playwright.sync_api import sync_playwright

    with serve(SITE) as url, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("#cards article")
        assert "lang-en" in page.locator("body").get_attribute("class")
        assert page.locator("text=6 active fixtures. One auditable pipeline.").is_visible()
        page.locator("#lang").click()
        assert "lang-es" in page.locator("body").get_attribute("class")
        assert page.locator("text=6 partidos activos. Un pipeline auditable.").is_visible()
        assert page.locator(".en:visible").count() == 0
        browser.close()
