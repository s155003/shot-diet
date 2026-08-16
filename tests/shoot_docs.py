"""Capture the README screenshots at a readable aspect ratio."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
URL = "http://localhost:8511"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 980},
                        device_scale_factor=1)
        pg.goto(URL, wait_until="networkidle", timeout=90_000)
        pg.wait_for_selector("h1", timeout=90_000)
        pg.wait_for_timeout(3500)

        def nav(label: str) -> None:
            pg.get_by_test_id("stSidebar").get_by_text(label, exact=True).click()
            pg.wait_for_timeout(4500)

        def shot(name: str, scroll: int = 0) -> None:
            if scroll:
                pg.mouse.wheel(0, scroll)
                pg.wait_for_timeout(1800)
            p = OUT / f"{name}.png"
            pg.screenshot(path=str(p))
            print(f"{p.name}: {p.stat().st_size / 1024:,.0f} KB")

        # empty search state: the tool before anyone has asked it anything
        shot("search-empty")

        # type-to-search, then take the accent-folded hit
        pg.get_by_test_id("stMain").get_by_test_id("stTextInput").locator(
            "input").fill("jokic")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(5000)
        shot("player")
        shot("prescription", scroll=1500)

        nav("Leaders")
        shot("leaders")

        nav("Findings")
        shot("findings")

        b.close()


if __name__ == "__main__":
    main()
