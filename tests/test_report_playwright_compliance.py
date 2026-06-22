"""Browser compliance tests for the generated June 22–27 site."""

from __future__ import annotations

import contextlib
import http.server
import json
import re
import socket
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


@contextlib.contextmanager
def serve(directory: Path):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *_args):
            pass

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def page():
    from playwright.sync_api import sync_playwright

    assert (SITE / "index.html").exists()
    with serve(SITE) as url, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        failed = []
        page.on("requestfailed", lambda request: failed.append(request.url))
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("#cards article")
        yield page, failed
        browser.close()


def test_exactly_32_unique_json_driven_cards(page):
    browser_page, _ = page
    ids = browser_page.locator("#cards article").evaluate_all(
        "els => els.map(e => e.dataset.fixtureId)"
    )
    assert len(ids) == 32
    assert len(set(ids)) == 32


def test_no_dynamic_resource_failures(page):
    _, failed = page
    assert failed == []


def test_rendered_recommendations_match_json(page):
    browser_page, _ = page
    payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    for item in payload["predictions"]:
        card = browser_page.locator(f'[data-fixture-id="{item["fixture_id"]}"]')
        assert card.count() == 1
        rec = item["recommendation"]
        assert rec is not None
        assert rec["decision_status"] == "BEST_AVAILABLE"
        text = card.inner_text()
        assert rec["selection_original"] in text
        displayed = re.search(r"Decision EV (-?\d+\.\d)%", text)
        assert displayed
        assert float(displayed.group(1)) == pytest.approx(rec["ev_pct"], abs=0.11)
        assert rec["strength"] in text
        assert f"risk grade {rec['risk_grade']}" in text


def test_forbidden_legacy_fixtures_are_absent(page):
    text = page[0].locator("body").inner_text()
    for stale in ("England vs Bolivia", "Canada vs Jamaica", "Germany vs Iran", "Switzerland vs Serbia"):
        assert stale not in text


def test_mobile_layout_has_no_horizontal_overflow(page):
    browser_page, _ = page
    browser_page.set_viewport_size({"width": 390, "height": 844})
    assert browser_page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1")


def test_metric_boxes_have_json_driven_newbie_hover_help(page):
    browser_page, _ = page
    payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    first = payload["predictions"][0]
    card = browser_page.locator(f'[data-fixture-id="{first["fixture_id"]}"]')
    assert card.locator(".tip").count() >= 10

    expected_goals_box = card.locator(
        '[data-json-pointer="/predictions/0/expected_goals/team_b"]'
    )
    help_button = expected_goals_box.locator(".tip")
    help_button.hover()
    popup = help_button.locator(":scope > span")
    assert popup.is_visible()
    assert first["metric_explanations"]["expected_goals_team_b"]["en"][
        "category_meaning"
    ] in popup.inner_text()
    assert first["metric_explanations"]["expected_goals_team_b"]["en"][
        "number_meaning"
    ] in popup.inner_text()
    assert first["metric_explanations"]["expected_goals_team_b"]["en"][
        "what_you_can_do"
    ] in popup.inner_text()
    browser_page.mouse.move(0, 0)
    help_button.focus()
    assert popup.is_visible()


def test_metric_tooltips_are_viewport_positioned_and_not_clipped(page):
    browser_page, _ = page
    browser_page.set_viewport_size({"width": 390, "height": 844})
    first_card = browser_page.locator("#cards article").first
    tips = first_card.locator(".tip")
    assert tips.count() >= 10
    for index in range(min(10, tips.count())):
        tip = tips.nth(index)
        tip.scroll_into_view_if_needed()
        tip.hover()
        popup = tip.locator(":scope > span")
        assert popup.is_visible()
        box = popup.bounding_box()
        assert box is not None
        assert box["x"] >= 7
        assert box["y"] >= 7
        assert box["x"] + box["width"] <= 383
        assert box["y"] + box["height"] <= 837
        assert popup.evaluate("el => getComputedStyle(el).position") == "fixed"
        assert int(popup.evaluate("el => getComputedStyle(el).zIndex")) >= 100
    browser_page.set_viewport_size({"width": 1440, "height": 1000})


def test_per_match_bankroll_steps_and_app_totals_match_json(page):
    browser_page, _ = page
    payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    plan_text = browser_page.locator("#bankroll-plan").inner_text()
    assert "Betano · S/100.00" in plan_text
    assert "Betsson · S/100.00" in plan_text
    assert "21 sourced match picks" in plan_text
    assert "11 sourced match picks" in plan_text

    for item in payload["predictions"]:
        card = browser_page.locator(f'[data-fixture-id="{item["fixture_id"]}"]')
        rec = item["recommendation"]
        budget = rec["budget_simulation"]
        text = card.inner_text()
        assert f"stake S/{budget['stake']:.2f} in {rec['app']}" in text
        details = card.locator("details").filter(
            has_text="S/100 app-budget simulation"
        )
        assert details.count() == 1
        details.locator("summary").click()
        assert f"S/{budget['gross_return_if_full_win']:.2f}" in details.inner_text()
        assert details.locator("ol.en li").count() == 6
        assert budget["steps"]["en"][-1] in details.inner_text()
