"""Debug: what happens when we hit the city_search page?"""
import time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_context().new_page()
    page.on("console", lambda m: print(f"  console.{m.type}: {m.text}"))
    page.on("pageerror", lambda e: print(f"  pageerror: {e}"))
    page.on("requestfailed", lambda r: print(f"  REQ FAILED: {r.url}  →  {r.failure}"))
    page.on("response", lambda r: print(f"  ← {r.status} {r.url}") if "nominatim" in r.url or "locations" in r.url else None)

    page.goto(f"{BASE}/city_search.html", wait_until="networkidle")
    page.fill("#city", "Варна")
    page.fill("#km", "30")
    page.click("#searchBtn")
    time.sleep(15)
    err = page.text_content("#errorBox")
    err_visible = page.locator("#errorBox").is_visible()
    res_visible = page.locator("#resultsSection").is_visible()
    print(f"\nerrorBox visible={err_visible}  text={err!r}")
    print(f"resultsSection visible={res_visible}")
    browser.close()
