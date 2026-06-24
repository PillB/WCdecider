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


@pytest.fixture()
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


def test_mobile_page_uses_audit_summary_not_large_csv():
    from playwright.sync_api import sync_playwright

    with serve(SITE) as url, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
        )
        requested = []
        page.on("request", lambda request: requested.append(request.url))
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector("#cards article", timeout=15000)
        assert any(url.endswith("wc_june22_27_datapoint_audit_summary.json") for url in requested)
        assert not any(url.endswith("wc_june22_27_datapoint_audit.csv") for url in requested)
        assert page.locator("#cards article").count() == 32
        browser.close()


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


def test_top_ranked_recommendations_match_json_and_disclose_shortfalls(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    for item in payload["predictions"]:
        card = browser_page.locator(
            f'[data-fixture-id="{item["fixture_id"]}"]'
        )
        ranked = card.locator("[data-recommendation-rank]")
        assert ranked.count() == item["top_recommendations_available"]
        assert 1 <= ranked.count() <= 4
        for index, recommendation in enumerate(
            item["top_recommendations"], start=1
        ):
            rendered = card.locator(
                f'[data-recommendation-rank="{index}"]'
            ).inner_text()
            assert recommendation["selection_original"] in rendered
            assert f'{recommendation["odds"]:.2f}' in rendered
        if item["top_recommendations_available"] < 4:
            assert "was not invented" in card.inner_text()


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


def test_mobile_shell_survives_delayed_json_without_crashing():
    from playwright.sync_api import sync_playwright

    with serve(SITE) as url, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
        )
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        def slow_predictions(route):
            page.wait_for_timeout(500)
            route.continue_()

        page.route("**/wc_june22_27_predictions.json", slow_predictions)
        page.goto(url, wait_until="domcontentloaded")
        assert page.locator("#loading-shell").is_visible()
        assert page.locator("#date-filter").is_disabled()
        assert page.locator("#strength-filter").is_disabled()
        assert page_errors == []
        page.wait_for_selector("#cards article", timeout=15000)
        assert page.locator("#loading-shell").is_hidden()
        assert page.locator("#date-filter").is_enabled()
        assert page.locator("#strength-filter").is_enabled()
        assert page.locator("#cards article").count() == 32
        assert page_errors == []
        browser.close()


def test_footer_last_updated_version_and_build_marker(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    footer = browser_page.locator("footer").inner_text()
    assert payload["generated_at"] in footer
    assert payload["model"]["version"] in footer
    build = browser_page.locator('meta[name="wcdecider-build"]').get_attribute("content")
    assert build
    assert build[:12] in footer


def test_research_mode_toggle_reveals_gated_shadow_model(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    first = payload["predictions"][0]
    toggle = browser_page.locator("#research-toggle")
    assert toggle.is_enabled()
    assert toggle.get_attribute("aria-pressed") == "false"
    assert browser_page.locator(".research-panel").first.is_hidden()
    assert browser_page.locator("#production-workflow").is_visible()
    assert browser_page.locator("#research-workflow").is_hidden()
    assert browser_page.locator(".production-performance").first.is_visible()
    assert browser_page.locator(".research-performance").first.is_hidden()
    toggle.click()
    assert toggle.get_attribute("aria-pressed") == "true"
    panel = browser_page.locator(
        f'[data-fixture-id="{first["fixture_id"]}"] .research-panel'
    )
    assert panel.is_visible()
    assert browser_page.locator("#production-workflow").is_hidden()
    assert browser_page.locator("#research-workflow").is_visible()
    assert browser_page.locator(".production-performance").first.is_hidden()
    assert browser_page.locator(".research-performance").first.is_visible()
    text = panel.inner_text()
    assert first["research_mode"]["selected_candidate"] in text
    assert "not production" in text
    assert f'{first["research_mode"]["probabilities"]["team_a_win"] * 100:.1f}%' in text
    research_ranked = panel.locator("[data-research-recommendation-rank]")
    assert research_ranked.count() == first["research_mode"]["top_recommendations_available"]
    assert first["research_mode"]["top_recommendations"][0]["selection_original"] in text
    research_workflow = browser_page.locator("#research-workflow")
    assert research_workflow.locator(".research-path").count() == 1
    assert "CI crosses zero" in research_workflow.text_content()
    toggle.click()
    assert browser_page.locator(".research-panel").first.is_hidden()


def test_performance_and_profitability_visuals_match_metrics(page):
    browser_page, _ = page
    metrics = json.loads(
        (SITE / "wc_june22_27_model_metrics.json").read_text(encoding="utf-8")
    )
    performance = browser_page.locator("#performance-viz").inner_text()
    profitability = browser_page.locator("#profitability-viz").inner_text()
    production = metrics["score_market_calibration"]["production_holdout"]
    assert f"{production['score_nll']:.4f}" in performance
    assert f"{production['over_2_5_brier']:.4f}" in performance
    assert f"{production['btts_brier']:.4f}" in performance
    for fold in metrics["model_championship"]["nested_outer_championship"]["folds"]:
        assert f"{fold['metrics']['market_devigged_proxy']['log_loss']:.3f}" in performance
    assert str(metrics["historical_closing_odds"]["events"]) in profitability
    assert str(metrics["historical_closing_odds"]["primary_validation_events"]) in profitability
    assert "ROI / CLV: not estimable yet" in profitability
    browser_page.locator("#lang").click()
    spanish = browser_page.locator("#performance-viz").inner_text()
    assert "Brier Más de 2,5" in spanish
    assert "Brier ambos marcan" in spanish
    assert "Pliegue 1" in spanish
    assert "Over 2.5 Brier" not in spanish
    assert "Fold 1" not in spanish


def test_risk_aversion_lens_switches_profile_panels(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    first = payload["predictions"][0]
    card = browser_page.locator(f'[data-fixture-id="{first["fixture_id"]}"]')
    selector = browser_page.locator("#risk-profile")
    rank_one = card.locator('[data-recommendation-rank="1"]')
    assert selector.is_enabled()
    assert card.locator('[data-risk-profile-panel="balanced"]').first.is_visible()
    assert rank_one.locator('[data-risk-lens-profile="balanced"]').is_visible()
    selector.select_option("audit_only")
    assert card.locator('[data-risk-profile-panel="balanced"]').first.is_hidden()
    assert card.locator('[data-risk-profile-panel="audit_only"]').first.is_visible()
    assert rank_one.locator('[data-risk-lens-profile="audit_only"]').is_visible()
    text = card.locator('[data-risk-profile-panel="audit_only"]').first.inner_text()
    expected = first["risk_profile_summary"]["audit_only"]
    assert f"{expected['pass_count']} PASS" in text
    assert f"{expected['halt_count']} HALT" in text
    assert selector.locator('option[value="audit_only"]').inner_text() == "Audit only"
    browser_page.locator("#lang").click()
    assert selector.locator('option[value="audit_only"]').inner_text() == "Solo auditoría"
    spanish_card_text = card.inner_text()
    assert "Ambos marcan: sí" in spanish_card_text
    assert "BTTS Yes / Sí" not in spanish_card_text


def test_report_has_no_stale_hardcoded_audit_count(page):
    browser_page, _ = page
    content = browser_page.content()
    assert "31,319 PASS fields" not in content
    assert "31.319 campos PASS" not in content
    assert "Ambos marcan: no" in content
    assert "Agente de usuario:" in content
    assert "Combinación de marcadores" in content
    assert "Poisson producción + DC investigación" in content
    assert "JSON + auditoría" in content


def test_mobile_missing_predictions_json_fails_visible_not_blank():
    from playwright.sync_api import sync_playwright

    with serve(SITE) as url, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
        )
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.route(
            "**/wc_june22_27_predictions.json",
            lambda route: route.fulfill(status=404, body="missing"),
        )
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("#error:not(.hidden)", timeout=10000)
        assert "Report data failed to load" in page.locator("#error").inner_text()
        assert page.locator("#diagnostics").is_visible()
        assert "wc_june22_27_predictions.json" in page.locator("#diagnostics").inner_text()
        assert page.locator("#cards article").count() == 0
        assert page.locator("#date-filter").is_disabled()
        assert page.locator("#strength-filter").is_disabled()
        assert page_errors == []
        browser.close()


def test_tampered_json_value_fails_closed_without_mobile_crash():
    from playwright.sync_api import sync_playwright

    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    payload["predictions"][0].setdefault("research", {}).setdefault(
        "source_urls", []
    )
    payload["predictions"][0]["research"]["source_urls"] = ["not a valid url"]

    with serve(SITE) as url, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.route(
            "**/wc_june22_27_predictions.json",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(payload),
            ),
        )
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector("#error:not(.hidden)", timeout=15000)
        assert "Report data failed to load" in page.locator("#error").inner_text()
        assert page.locator("#diagnostics").is_visible()
        assert page.locator("#cards article").count() == 0
        assert page_errors == []
        browser.close()
