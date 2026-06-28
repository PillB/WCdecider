"""Browser compliance tests for the generated active-batch site."""

from __future__ import annotations

import contextlib
import http.server
import json
import os
import re
import socket
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = Path(os.environ.get("WCDECIDER_SITE_DIR", ROOT / "site"))


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


def test_exactly_batch_count_unique_json_driven_cards(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    ids = browser_page.locator("#cards article").evaluate_all(
        "els => els.map(e => e.dataset.fixtureId)"
    )
    assert len(ids) == payload["batch"]["fixture_count"]
    assert len(set(ids)) == payload["batch"]["fixture_count"]


def test_elapsed_cards_show_verified_results_and_future_cards_do_not(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    elapsed = [
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "elapsed_result_verified"
    ]
    future = [
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "future"
    ]
    assert len(elapsed) == 0
    assert len(future) == payload["batch"]["fixture_count"]
    for row in elapsed:
        text = browser_page.locator(
            f'[data-fixture-id="{row["fixture_id"]}"]'
        ).inner_text()
        assert f'Final result: {row["verified_result"]["score"]}' in text
        assert "Archived pre-match forecast" in text
    for row in future:
        text = browser_page.locator(
            f'[data-fixture-id="{row["fixture_id"]}"]'
        ).inner_text()
        assert "Final result:" not in text


def test_every_future_card_has_best_watchlist_and_eli5_zero_stake_flow(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    future = [
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "future"
    ]
    assert len(future) == payload["batch"]["fixture_count"]
    for row in future:
        rank_one = row["rank_one_comparison"]
        assert rank_one is not None
        assert len(rank_one["steps"]["en"]) in {1, 6}
        assert rank_one["budget_simulation"]["stake"] == 0.0
        card = browser_page.locator(
            f'[data-fixture-id="{row["fixture_id"]}"]'
        )
        text = card.inner_text()
        if row["freshness_status"].startswith("conditional_"):
            assert "Best available watchlist" not in text
            assert "STOP: do not use the saved sportsbook steps or price" in text
            assert "Top ranked sourced comparisons" not in text
            assert card.locator("[data-recommendation-rank]").count() == 0
        else:
            assert "Best available watchlist" in text
            assert "ELI5: check this exact watchlist" in text
        assert "System stake: S/0.00" in text


def test_elapsed_cards_hide_betting_controls(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    elapsed = [
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "elapsed_result_verified"
    ]
    assert len(elapsed) == 0
    for row in elapsed:
        card = browser_page.locator(
            f'[data-fixture-id="{row["fixture_id"]}"]'
        )
        text = card.inner_text()
        assert "Archived forecast review" in text
        assert "System stake: S/0.00" in text
        assert "Top ranked sourced comparisons" not in text
        assert "Ranked screenshot market comparisons" not in text
        assert "Research, risks and ELI5" not in text
        assert card.locator("[data-recommendation-rank]").count() == 0


def test_workflow_counts_are_json_driven(page):
    browser_page, _ = page
    metrics = json.loads(
        (SITE / "wc_june22_27_model_metrics.json").read_text(encoding="utf-8")
    )
    historical = metrics["dataset_a_rows"] + metrics["dataset_b_rows"]
    assert browser_page.locator("#production-history-count").text_content() == (
        f"{historical} rows"
    )
    assert browser_page.locator("#elapsed-results-count").text_content() == (
        f'{metrics["elapsed_wc2026_rows"]} results'
    )


def test_current_page_layout_contract_and_user_journey(page):
    browser_page, _ = page
    required_sections = [
        "#summary",
        "#model-evidence",
        "#performance-viz",
        "#profitability-viz",
        "#date-filter",
        "#strength-filter",
        "#risk-profile",
        "#simulation-budget",
        "#loading-shell",
        "#bankroll-plan",
        "#top-summary",
        "#cards",
        "footer",
    ]
    for selector in required_sections:
        assert browser_page.locator(selector).count() >= 1, selector

    ordered_selectors = [
        "#summary",
        "#model-evidence",
        "#performance-viz",
        "#profitability-viz",
        "#date-filter",
        "#loading-shell",
        "#bankroll-plan",
        "#top-summary",
        "#cards",
        "footer",
    ]
    dom_order = browser_page.evaluate(
        """selectors => selectors.map(selector =>
            Array.from(document.querySelectorAll('*')).indexOf(
                document.querySelector(selector)
            )
        )""",
        ordered_selectors,
    )
    assert dom_order == sorted(dom_order)
    assert all(index >= 0 for index in dom_order)

    assert browser_page.locator("#production-workflow").is_visible()
    assert browser_page.locator("#research-workflow").is_hidden()
    assert browser_page.locator("#bankroll-plan article").count() >= 3
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    assert browser_page.locator("#top-summary tbody tr").count() == payload["batch"]["fixture_count"]
    assert browser_page.locator("#cards article.bg-slate-900").count() == payload["batch"]["fixture_count"]

    first_summary_link = browser_page.locator("#top-summary tbody a[href^='#match-']").first
    target = first_summary_link.get_attribute("href")
    assert target
    assert browser_page.locator(target).count() == 1
    first_summary_link.click()
    assert browser_page.evaluate("location.hash") == target

    footer = browser_page.locator("footer").inner_text()
    assert "last updated" in footer
    assert "Version" in footer
    assert browser_page.locator('meta[name="wcdecider-build"]').get_attribute("content")


def test_top_summary_table_links_top_two_and_allocations(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    rows = browser_page.locator("#top-summary tbody tr")
    assert rows.count() == payload["batch"]["fixture_count"]

    first_current = next(
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "future"
        and row["freshness_status"] == "current_snapshot"
    )
    summary_row = browser_page.locator(
        f'[data-top-summary-row="{first_current["fixture_id"]}"]'
    )
    assert summary_row.count() == 1
    assert first_current["ranked_comparisons"][0]["display"]["selection"]["en"] in (
        summary_row.inner_text()
    )
    assert first_current["ranked_comparisons"][1]["display"]["selection"]["en"] in (
        summary_row.inner_text()
    )
    balanced_stake = first_current["rank_one_comparison"]["stake_simulation"][
        "Betsson"
    ]["balanced"]["stake"]
    assert f"S/{balanced_stake:.2f}" in summary_row.inner_text()
    assert summary_row.locator('a[href="#match-' + first_current["fixture_id"] + '"]').count() >= 1
    assert browser_page.locator(f'#match-{first_current["fixture_id"]}').count() == 1

    browser_page.locator("#simulation-budget").fill("200")
    assert f"S/{balanced_stake * 2:.2f}" in summary_row.inner_text()
    summary_row.locator('a[href="#match-' + first_current["fixture_id"] + '"]').first.click()
    assert browser_page.evaluate("location.hash") == f"#match-{first_current['fixture_id']}"


def test_blocked_app_empty_profiles_do_not_break_stake_simulator(page):
    browser_page, failed = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    assert payload["educational_stake_simulation"]["apps"]["Betano"]["profiles"]
    assert browser_page.locator("#status").inner_text() == "Verified JSON loaded"
    plan_text = browser_page.locator("#bankroll-plan").inner_text()
    assert "Authorized stake" in plan_text
    assert "interactive S/100.00 simulation" in plan_text
    assert failed == []


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
        assert any(url.endswith("release_validation_june22_27.json") for url in requested)
        assert not any(url.endswith("wc_june22_27_datapoint_audit.csv") for url in requested)
        payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
        assert page.locator("#cards article").count() == payload["batch"]["fixture_count"]
        browser.close()


def test_rendered_recommendations_match_json(page):
    browser_page, _ = page
    payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    for item in payload["predictions"]:
        card = browser_page.locator(f'[data-fixture-id="{item["fixture_id"]}"]')
        assert card.count() == 1
        assert item["recommendation"] is None
        rec = item["rank_one_comparison"]
        assert rec["decision_status"] == "ABSTAIN"
        assert rec["budget_simulation"]["stake"] == 0.0
        text = card.inner_text()
        current = (
            item["fixture_lifecycle_status"] == "future"
            and item["freshness_status"] == "current_snapshot"
        )
        if not current:
            assert "Decision EV" not in text
            continue
        assert rec["display"]["selection"]["en"] in text
        displayed = re.search(r"Decision EV (-?\d+\.\d)%", text)
        assert displayed
        assert float(displayed.group(1)) == pytest.approx(rec["ev_pct"], abs=0.11)
        assert rec["strength"] in text
        assert f"risk grade {rec['risk_grade']}" in text
        assert "Best available watchlist" in text


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
        current = (
            item["fixture_lifecycle_status"] == "future"
            and item["freshness_status"] == "current_snapshot"
        )
        if not current:
            assert ranked.count() == 0
            continue
        assert ranked.count() == item["ranked_comparisons_available"]
        assert 1 <= ranked.count() <= 4
        for index, recommendation in enumerate(
            item["ranked_comparisons"], start=1
        ):
            rendered = card.locator(
                f'[data-recommendation-rank="{index}"]'
            ).inner_text()
            assert recommendation["display"]["selection"]["en"] in rendered
            assert f'{recommendation["odds"]:.2f}' in rendered
        if item["ranked_comparisons_available"] < 4:
            assert "was not manufactured" in card.inner_text()


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
    prediction_index, first = next(
        (index, row)
        for index, row in enumerate(payload["predictions"])
        if row["fixture_lifecycle_status"] == "future"
        and row["freshness_status"] == "current_snapshot"
    )
    card = browser_page.locator(f'[data-fixture-id="{first["fixture_id"]}"]')
    assert card.locator(".tip").count() >= 10

    expected_goals_box = card.locator(
        f'[data-json-pointer="/predictions/{prediction_index}/expected_goals/team_b"]'
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
    payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    first_card = browser_page.locator(
        f'[data-fixture-id="{payload["predictions"][0]["fixture_id"]}"]'
    )
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


def test_mobile_tooltips_open_by_tap_scroll_and_close_with_escape(page):
    browser_page, _ = page
    browser_page.set_viewport_size({"width": 390, "height": 844})
    cards = browser_page.locator("#cards article")
    payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    assert cards.count() == payload["batch"]["fixture_count"]
    checked = 0
    for index in range(cards.count()):
        tips = cards.nth(index).locator(".tip")
        if tips.count() == 0:
            continue
        tip = tips.first
        tip.scroll_into_view_if_needed()
        tip.click()
        popup = tip.locator(":scope > span")
        assert popup.is_visible()
        assert popup.evaluate("el => getComputedStyle(el).overflowY") == "auto"
        box = popup.bounding_box()
        assert box is not None
        assert box["x"] >= 7
        assert box["y"] >= 7
        assert box["x"] + box["width"] <= 383
        assert box["y"] + box["height"] <= 837
        browser_page.keyboard.press("Escape")
        assert not popup.is_visible()
        checked += 1
    assert checked > 0


def test_interactive_stake_simulation_scales_and_preserves_authorization(page):
    browser_page, _ = page
    payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
    plan_text = browser_page.locator("#bankroll-plan").inner_text()
    assert "interactive S/100.00 simulation" in plan_text
    assert "Authorized stake" in plan_text
    assert "S/0.00" in plan_text
    balanced = payload["educational_stake_simulation"]["apps"]["Betsson"][
        "profiles"
    ]["balanced"]
    assert f"S/{balanced['singles_deployed']:.2f}" in plan_text
    assert f"S/{balanced['cash_reserved']:.2f}" in plan_text
    assert "The simulator is available even though the production authorization remains zero." in plan_text
    assert "All three legs must win" in plan_text

    for item in payload["predictions"]:
        card = browser_page.locator(f'[data-fixture-id="{item["fixture_id"]}"]')
        assert item["recommendation"] is None
        rec = item["rank_one_comparison"]
        budget = rec["budget_simulation"]
        assert budget["stake"] == 0.0
        text = card.inner_text()
        assert f"System stake: S/{budget['stake']:.2f}" in text
        details = card.locator("details").filter(
            has_text="Fail-closed allocation"
        )
        assert details.count() == 0
        if (
            item["fixture_lifecycle_status"] == "future"
            and item["freshness_status"] == "current_snapshot"
        ):
            simulated = rec["stake_simulation"]["Betsson"]["balanced"]["stake"]
            assert f"S/{simulated:.2f}" in text
            assert simulated >= 0
            assert "Comparison only" in text
        else:
            assert card.locator(
                f'[data-simulation-stake="{item["fixture_id"]}"]'
            ).count() == 0

    browser_page.locator("#simulation-budget").fill("200")
    first = next(
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "future"
        and row["freshness_status"] == "current_snapshot"
    )
    expected = (
        first["rank_one_comparison"]["stake_simulation"]["Betsson"]["balanced"][
            "stake"
        ] * 2
    )
    assert browser_page.locator(
        f'[data-simulation-stake="{first["fixture_id"]}"]'
    ).inner_text() == f"S/{expected:.2f}"
    browser_page.locator("#risk-profile").select_option("strict")
    strict_expected = (
        first["rank_one_comparison"]["stake_simulation"]["Betsson"]["strict"][
            "stake"
        ] * 2
    )
    assert browser_page.locator(
        f'[data-simulation-stake="{first["fixture_id"]}"]'
    ).inner_text() == f"S/{strict_expected:.2f}"


def test_complementary_betting_panel_discloses_dutching_math_and_risk(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    first = next(
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "future"
        and row["freshness_status"] == "current_snapshot"
    )
    card = browser_page.locator(f'[data-fixture-id="{first["fixture_id"]}"]')
    text = card.inner_text()
    assert "Complementary / dutching check" in text
    analysis = first["complementary_bet_analysis"]
    if analysis["full_cover_arbitrage_available"]:
        assert "Full-cover arbitrage found" in text
        assert "before app limits, stale-price risk" in text
    else:
        assert "No guaranteed full-cover arbitrage" in text
        assert "leaves one result uncovered" in text
        assert "loss S/10.00" in text
    assert "Two-outcome hedges can still lose" in text
    browser_page.locator("#lang").click()
    spanish = card.inner_text()
    assert "Chequeo complementario / dutching" in spanish
    assert "resultado no cubierto" in spanish


def test_double_discount_gate_is_visible_and_non_authorizing(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    first = next(
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "future"
        and row["freshness_status"] == "current_snapshot"
    )
    card = browser_page.locator(f'[data-fixture-id="{first["fixture_id"]}"]')
    text = card.inner_text()
    assert "Double-discount gate" in text
    assert "not proof of profit" in text
    gate = first["ranked_comparisons"][0]["margin_of_safety"]
    assert f"{gate['observed_market_probability'] * 100:.1f}%" in text
    assert f"{gate['required_market_probability_max'] * 100:.1f}%" in text
    browser_page.locator("#lang").click()
    spanish = card.inner_text()
    assert "Puerta doble descuento" in spanish
    assert "no prueba de beneficio" in spanish


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
        payload = json.loads((SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8"))
        assert page.locator("#cards article").count() == payload["batch"]["fixture_count"]
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
    first = next(
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "future"
        and row["freshness_status"] == "current_snapshot"
    )
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
    assert research_ranked.count() == first["research_mode"]["ranked_comparisons_available"]
    assert first["research_mode"]["ranked_comparisons"][0]["display"]["selection"]["en"] in text
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
    for fold in metrics.get("model_championship", {}).get("nested_outer_championship", {}).get("folds", []):
        assert f"{fold['metrics']['market_devigged_proxy']['log_loss']:.3f}" in performance
    odds = metrics.get("historical_closing_odds", {"events": 0, "primary_validation_events": 0})
    assert str(odds["events"]) in profitability
    assert str(odds["primary_validation_events"]) in profitability
    assert "ROI / CLV: not estimable yet" in profitability
    browser_page.locator("#lang").click()
    spanish = browser_page.locator("#performance-viz").inner_text()
    assert "Brier Más de 2,5" in spanish
    assert "Brier ambos marcan" in spanish
    if metrics.get("model_championship", {}).get("nested_outer_championship", {}).get("folds"):
        assert "Pliegue 1" in spanish
    assert "Over 2.5 Brier" not in spanish
    assert "Fold 1" not in spanish


def test_risk_aversion_lens_switches_profile_panels(page):
    browser_page, _ = page
    payload = json.loads(
        (SITE / "wc_june22_27_predictions.json").read_text(encoding="utf-8")
    )
    first = next(
        row for row in payload["predictions"]
        if row["fixture_lifecycle_status"] == "future"
        and row["freshness_status"] == "current_snapshot"
    )
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
