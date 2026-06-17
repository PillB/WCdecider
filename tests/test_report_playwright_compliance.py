#!/usr/bin/env python3
"""
Playwright compliance audit for the latest report (wc_june17_21_full_report.html). Older versions are in archived/.

Validates user-facing content against:
  - wc_model_production_results.csv (v4.1 locked numbers)
  - EN/ES bilingual toggle requirements
  - AGENT.md report protocol (no stale v3-as-primary, HALT for AUT draw, etc.)

Run: python3 -m pytest tests/test_report_playwright_compliance.py -v
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
REPORT = ROOT / "index.html"  # latest version in root; previous reports moved to archived/
PRODUCTION_CSV = ROOT / "wc_model_production_results.csv"

LOCKED_BACKTEST = {
    "market_brier": "0.5956",
    "v4_1_stack_brier": "0.6039",
    "v4_elo_brier": "0.6157",
    "traps": "0/125",
}

# Stale primary-model strings that must NOT appear as live recommendations
FORBIDDEN_EN = [
    "(+12% SPEC), cleared",
    "Austria vs Jordan (pDraw 23.2%, +12% EV",
    "AUT Draw @5.05 (+12% base",
    "Model (executed wc_model_v3.py)",
    "Executed Model (wc_replicable_pipeline.py + documented base)",
    "opener_draw_boost +0.055 (extra chance",
    "62.0% win / 27.1% draw</span>",  # as primary finetune headline without v4.1 label
]

# Required v4.1 production markers (EN visible text)
REQUIRED_EN = [
    "v4.1 prod",
    "wc_model_v4_replicable_pipeline.py",
    "wc_model_v4_1_ensemble.py",
    "opener_draw_boost +0.07",
    "68.6% win / 28.1% draw",
    "0.5956",
    "0.6039",
    "0.6157",
    "0/125",
    "+69% HALT",
    "+69.0% EV",
    "HALT (+69% EV)",
    "59.6%",
    "34%",
    "EV −9.4%",
    "EV −41.7%",
    "EV −10.6%",
    "MOD 70/30",
    "Rule 24",
]

# Note: section headers use CSS uppercase — innerText shows ALL CAPS for those nodes
REQUIRED_ES = [
    "RESUMEN EJECUTIVO",
    "Marco Analítico y Visualización del Flujo de Modelado",
    "Replicación peer-review PASS",
    "Ganador producción",
    "opener_draw_boost +0,07",
    "68,6% victoria / 28,1% empate",
    "HALT (+69% EV)",
    "+69,0% EV",
    "mezcla MOD 70/30",
    "Regla 24",
    "Apostar conlleva riesgo real",
]

# Historical v3.1 references allowed only in labeled context
ALLOWED_V3_CONTEXT = [
    "v3.1 historical",
    "v3.1 documented",
    "histórico v3.1",
    "documentada v3.1",
    "wc_replicable_pipeline.py",  # legacy path note in replication block
    "wc_model_v3.py (bradley_terry",  # BTD stub reference
]


def load_june_production() -> list[dict]:
    rows = []
    with PRODUCTION_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("dataset") == "june_slate":
                rows.append(row)
    assert len(rows) == 6, f"Expected 6 june_slate rows, got {len(rows)}"
    return rows


def pct(val: float | str, decimals: int = 1) -> str:
    v = float(val) * 100
    return f"{v:.{decimals}f}"


@pytest.fixture(scope="module")
def june_rows():
    return load_june_production()


@pytest.fixture(scope="module")
def browser_page():
    from playwright.sync_api import sync_playwright

    if not REPORT.exists():
        pytest.skip(f"Report not found: {REPORT}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(REPORT.as_uri(), wait_until="networkidle")
        page.wait_for_timeout(400)
        yield page
        browser.close()


def _switch(page, lang: str) -> str:
    page.click("#btn-en" if lang == "en" else "#btn-es")
    page.wait_for_timeout(250)
    return page.evaluate("() => document.body.innerText")


def _visible_en_count(page) -> int:
    return page.evaluate("""() => {
      let n = 0;
      document.querySelectorAll('.en').forEach(el => {
        const s = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        if (s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0) n++;
      });
      return n;
    }""")


def _visible_es_count(page) -> int:
    return page.evaluate("""() => {
      let n = 0;
      document.querySelectorAll('.es').forEach(el => {
        const s = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        if (s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0) n++;
      });
      return n;
    }""")


class TestReportPlaywrightCompliance:
    def test_report_file_exists(self):
        assert REPORT.exists()

    def test_en_mode_body_class_and_required_content(self, browser_page):
        text = _switch(browser_page, "en")
        cls = browser_page.evaluate("() => document.body.className")
        assert "lang-en" in cls
        missing = [m for m in REQUIRED_EN if m not in text]
        assert not missing, f"Missing required EN markers: {missing}"

    def test_en_mode_forbidden_stale_content_absent(self, browser_page):
        text = _switch(browser_page, "en")
        found = [f for f in FORBIDDEN_EN if f in text]
        assert not found, f"Stale/forbidden EN content still visible: {found}"

    def test_es_mode_body_class_and_required_content(self, browser_page):
        text = _switch(browser_page, "es")
        cls = browser_page.evaluate("() => document.body.className")
        title = browser_page.title()
        assert "lang-es" in cls
        assert "Copa 2026" in title or "Análisis" in title
        missing = [m for m in REQUIRED_ES if m not in text]
        assert not missing, f"Missing required ES markers: {missing}"

    def test_es_mode_no_visible_en_spans(self, browser_page):
        _switch(browser_page, "es")
        visible_en = _visible_en_count(browser_page)
        assert visible_en == 0, f".en elements still visible in ES mode: {visible_en}"

    def test_es_mode_has_visible_translations(self, browser_page):
        _switch(browser_page, "es")
        visible_es = _visible_es_count(browser_page)
        assert visible_es > 50, f"Expected many visible .es elements, got {visible_es}"

    def test_toggle_switches_diagram_labels(self, browser_page):
        _switch(browser_page, "en")
        layer_en = browser_page.text_content("#d-layer1")
        _switch(browser_page, "es")
        layer_es = browser_page.text_content("#d-layer1")
        assert layer_en and layer_es
        assert layer_en != layer_es
        assert "CAPA 1" in layer_es

    def test_june_v41_numbers_in_report_en(self, browser_page, june_rows):
        text = _switch(browser_page, "en")

        # Map production CSV → substrings that must appear in report
        expectations = {
            "Spain vs Cape Verde": [pct(june_rows[0]["p_model_a"]), pct(june_rows[0]["p_model_d"])],
            "France vs Senegal": [pct(june_rows[2]["p_blend_a"], 1)],
            "Austria vs Jordan": [pct(june_rows[5]["p_model_d"], 1), "+69"],
        }
        for match, subs in expectations.items():
            for sub in subs:
                assert sub in text, f"{match}: expected '{sub}' in EN report text"

    def test_austria_halt_not_spec_recommendation_en(self, browser_page):
        text = _switch(browser_page, "en")
        # Surefire table row should show HALT not bare SPEC for AUT draw
        assert "AUT Draw @5.05" in text
        assert "HALT (MOD)" in text or "HALT (+69% EV)" in text
        assert "AUT Draw @5.05 (+12%" not in text

    def test_responsible_gambling_block_both_languages(self, browser_page):
        en = _switch(browser_page, "en")
        assert "Línea 0800-1-3232" in en
        assert "Jugadores Anónimos" in en
        es = _switch(browser_page, "es")
        assert "Apostar conlleva riesgo real" in es
        assert "Jugadores Anónimos Perú" in es

    def test_replication_package_visible(self, browser_page):
        text = _switch(browser_page, "en")
        for artifact in [
            "wc_2026_model_dataset.csv",
            "wc_backtest_historical_dataset.csv",
            "wc_model_production_results.csv",
            "Peer Review PASS",
        ]:
            assert artifact in text, f"Missing replication artifact reference: {artifact}"

    def test_backtest_locked_metrics_visible(self, browser_page):
        text = _switch(browser_page, "en")
        for k, v in LOCKED_BACKTEST.items():
            assert v in text, f"Missing locked backtest metric {k}={v}"

    def test_v3_references_only_in_allowed_context(self, browser_page):
        text = _switch(browser_page, "en")
        # wc_model_v3 may appear only for BTD stub — not as primary executed model
        assert "Model (executed wc_model_v3.py)" not in text
        if "wc_model_v3.py" in text:
            assert "bradley_terry" in text or "Stub" in text or "stub" in text

    def test_no_orphan_english_in_es_mode(self, browser_page):
        """Spot-check common English phrases that should be translated in ES mode."""
        text = _switch(browser_page, "es")
        orphan_patterns = [
            r"\bEXECUTIVE SUMMARY\b",
            r"\bExecutive Summary\b",
            r"\bBacktest Insights\b",
            r"\bSurefire / Near-1\.0\b",
            r"\bAnalytical Framework\b",
            r"\bFinal Classifications\b",
        ]
        hits = [p for p in orphan_patterns if re.search(p, text)]
        assert not hits, f"English section headers still in ES body: {hits}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])