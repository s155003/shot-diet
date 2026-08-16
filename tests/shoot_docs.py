"""Capture the README screenshots at a readable aspect ratio."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
URL = "http://localhost:8511"

# (sidebar label, output name, extra scroll in px)
SHOTS = [
    ("The finding", "finding", 0),
    ("Shot-diet optimiser", "optimiser", 0),
    ("Players", "player-detail", 1750),
    ("Method & validation", "validation", 1250),
]


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 950},
                        device_scale_factor=1)
        pg.goto(URL, wait_until="networkidle", timeout=90_000)
        pg.wait_for_selector("h1", timeout=90_000)
        pg.wait_for_timeout(4000)

        for i, (label, name, scroll) in enumerate(SHOTS):
            if i:
                pg.get_by_test_id("stSidebar").get_by_text(label, exact=True).click()
                pg.wait_for_timeout(5500)
            if scroll:
                pg.mouse.wheel(0, scroll)
                pg.wait_for_timeout(2500)
            path = OUT / f"{name}.png"
            pg.screenshot(path=str(path))
            print(f"{path.name}: {path.stat().st_size / 1024:,.0f} KB")
        b.close()


if __name__ == "__main__":
    main()
