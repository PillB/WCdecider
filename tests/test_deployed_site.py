#!/usr/bin/env python3
"""
Playwright validation against the deployed GitHub Pages site.

Set DEPLOY_URL (e.g. https://pabloillescas.github.io/WCdecider/)
Run: DEPLOY_URL=https://... python3 -m pytest tests/test_deployed_site.py -v
"""

from __future__ import annotations

import os
import re
from urllib.parse import urljoin

import pytest

DEPLOY_URL = os.environ.get("DEPLOY_URL", "").rstrip("/") + "/"

REQUIRED_EN = [
    "v4.1 prod",
    "wc_model_v4_replicable_pipeline.py",
    "68.6% win / 28.1% draw",
    "opener_draw_boost +0.07",
    "+69% HALT",
    "59.6%",
    "0.5956",
    "0.6039",
]

REQUIRED_ES = [
    "RESUMEN EJECUTIVO",
    "68,6% victoria / 28,1% empate",
    "HALT (+69% EV)",
    "Apostar conlleva riesgo real",
]

FORBIDDEN = [
    "(+12% SPEC), cleared",
    "Model (executed wc_model_v3.py)",
    "opener_draw_boost +0.055 (extra chance",
]


@pytest.fixture(scope="module")
def deploy_url() -> str:
    if not DEPLOY_URL or DEPLOY_URL == "/":
        pytest.skip("DEPLOY_URL not set — skip deployed-site tests")
    return DEPLOY_URL


@pytest.fixture(scope="module")
def browser_page(deploy_url: str):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(deploy_url, wait_until="networkidle", timeout=120_000)
        page.wait_for_timeout(500)
        yield page, deploy_url
        browser.close()


def _switch(page, lang: str) -> str:
    page.click("#btn-en" if lang == "en" else "#btn-es")
    page.wait_for_timeout(300)
    return page.evaluate("() => document.body.innerText")


class TestDeployedGitHubPages:
    def test_homepage_loads_200(self, browser_page):
        page, url = browser_page
        assert "WCdecider" in page.title() or "WCdecider" in page.content()

    def test_cdn_assets_render(self, browser_page):
        page, _ = browser_page
        # Tailwind + nav should produce styled layout (not raw unstyled HTML)
        nav = page.locator("nav")
        assert nav.count() > 0
        bg = page.evaluate("""() => {
          const nav = document.querySelector('nav');
          return nav ? getComputedStyle(nav).backgroundColor : '';
        }""")
        assert bg and bg != "rgba(0, 0, 0, 0)"

    def test_en_required_content(self, browser_page):
        page, _ = browser_page
        text = _switch(page, "en")
        missing = [m for m in REQUIRED_EN if m not in text]
        assert not missing, f"Missing on deployed EN site: {missing}"

    def test_en_forbidden_stale_absent(self, browser_page):
        page, _ = browser_page
        text = _switch(page, "en")
        found = [f for f in FORBIDDEN if f in text]
        assert not found, f"Stale content on deployed site: {found}"

    def test_es_toggle_and_content(self, browser_page):
        page, _ = browser_page
        text = _switch(page, "es")
        assert "lang-es" in page.evaluate("() => document.body.className")
        missing = [m for m in REQUIRED_ES if m not in text]
        assert not missing, f"Missing on deployed ES site: {missing}"

    def test_es_no_visible_en_spans(self, browser_page):
        page, _ = browser_page
        _switch(page, "es")
        visible_en = page.evaluate("""() => {
          let n = 0;
          document.querySelectorAll('.en').forEach(el => {
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            if (s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0) n++;
          });
          return n;
        }""")
        assert visible_en == 0

    def test_diagram_labels_toggle(self, browser_page):
        page, _ = browser_page
        _switch(page, "en")
        en_layer = page.text_content("#d-layer1")
        _switch(page, "es")
        es_layer = page.text_content("#d-layer1")
        assert en_layer != es_layer
        assert "CAPA 1" in (es_layer or "")

    def test_alternate_report_path(self, browser_page, deploy_url: str):
        page, base = browser_page
        alt = urljoin(base, "wc_june16_2026_report.html")
        resp = page.goto(alt, wait_until="networkidle", timeout=120_000)
        assert resp and resp.ok
        assert "v4.1 prod" in page.content()

    def test_responsible_gambling_block(self, browser_page):
        page, _ = browser_page
        _switch(page, "es")
        text = page.evaluate("() => document.body.innerText")
        assert "Jugadores Anónimos" in text