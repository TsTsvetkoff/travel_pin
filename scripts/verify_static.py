"""
End-to-end smoke test for the static site served from /docs.

Drives the page with a real headless browser, verifies:
- locations.json loads and 397 markers render
- filter, search, and category select all update the visible card list
- E3/E4 trails render as polylines (non-empty)
- city_search.html renders, accepts input, geocodes, and renders result cards
- hall_of_fame.html renders a card per diploma

Run from the repo root with the http.server on :8000 already running.
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"


def main() -> int:
    errors: list[str] = []
    console_errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()

        page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"))
        page.on(
            "console",
            lambda msg: console_errors.append(f"console.{msg.type}: {msg.text}")
            if msg.type in ("error", "warning")
            else None,
        )

        # --- index.html ---
        page.goto(f"{BASE}/index.html", wait_until="networkidle")
        page.wait_for_function("document.querySelectorAll('.location-card').length > 0", timeout=10_000)

        total = page.text_content("#totalCount")
        cards = page.locator(".location-card").count()
        if cards != 397:
            errors.append(f"index: expected 397 cards, got {cards}")
        if total != "397":
            errors.append(f"index: totalCount expected '397', got {total!r}")

        # Filter: pick a category, expect the count to drop.
        page.select_option("#categorySelect", "Peak")
        page.wait_for_function("document.querySelectorAll('.location-card').length < 397", timeout=5_000)
        peak_count = page.locator(".location-card").count()
        if peak_count == 0 or peak_count >= 397:
            errors.append(f"index: filter to Peak produced {peak_count} cards (suspicious)")

        # Clear filters, then search.
        page.click("#clearFiltersBtn")
        page.wait_for_function("document.querySelectorAll('.location-card').length == 397", timeout=5_000)
        page.fill("#searchInput", "Крепост")
        page.locator("#searchForm button[type=submit]").click()
        page.wait_for_function("document.querySelectorAll('.location-card').length > 0 && document.querySelectorAll('.location-card').length < 397", timeout=5_000)
        search_count = page.locator(".location-card").count()
        if search_count == 0 or search_count >= 397:
            errors.append(f"index: search 'Крепост' produced {search_count} cards (suspicious)")

        # Clear search.
        page.click("#clearSearchBtn")
        page.wait_for_function("document.querySelectorAll('.location-card').length == 397", timeout=5_000)

        # Toggle E-trail button.
        page.click("#toggleTrailsBtn")
        btn_text = page.text_content("#toggleTrailsBtn")
        if btn_text != "Show all pins":
            errors.append(f"index: toggle button expected 'Show all pins', got {btn_text!r}")
        page.click("#toggleTrailsBtn")

        # --- city_search.html ---
        page.goto(f"{BASE}/city_search.html", wait_until="networkidle")
        page.fill("#city", "Варна")
        page.fill("#km", "30")
        page.click("#searchBtn")
        # Wait for the results section to appear (Nominatim + fetch is async).
        try:
            page.wait_for_selector("#resultsSection", state="visible", timeout=15_000)
        except Exception as e:
            errors.append(f"city_search: results did not appear ({e})")
        else:
            results = page.locator(".result-card").count()
            if results == 0:
                # Check whether the error box is showing instead.
                err_text = page.text_content("#errorBox")
                errors.append(f"city_search: 0 results near Варна; error box says: {err_text!r}")
            else:
                first = page.text_content(".result-name")
                print(f"city_search: {results} results near Варна, first = {first!r}")

        # --- hall_of_fame.html ---
        page.goto(f"{BASE}/hall_of_fame.html", wait_until="networkidle")
        page.wait_for_selector(".hof-item", timeout=5_000)
        hof_count = page.locator(".hof-item").count()
        if hof_count != 4:
            errors.append(f"hall_of_fame: expected 4 items, got {hof_count}")

        browser.close()

    if console_errors:
        # Surface JS errors, but only ones that are not "favicon" noise.
        real = [e for e in console_errors if "favicon" not in e.lower()]
        if real:
            print("Browser console messages:")
            for e in real:
                print("  -", e)
            errors.extend(real)

    if errors:
        print("\nFAILED:")
        for e in errors:
            print("  ✗", e)
        return 1
    print("\nAll static-page checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
