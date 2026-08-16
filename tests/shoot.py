"""Screenshot each dashboard page for visual inspection."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
URL = "http://localhost:8511"
PAGES = ["The finding", "Players", "Shot-diet optimiser", "Teams",
         "Method & validation"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        # Streamlit scrolls inside its own container, so full_page capture only
        # sees the viewport; make the viewport tall instead.
        pg = b.new_page(viewport={"width": 1560, "height": 2600},
                        device_scale_factor=1)
        pg.goto(URL, wait_until="networkidle", timeout=90_000)
        pg.wait_for_selector("h1", timeout=90_000)
        pg.wait_for_timeout(4000)

        for i, name in enumerate(PAGES):
            if i:
                pg.get_by_test_id("stSidebar").get_by_text(name, exact=True).click()
                pg.wait_for_timeout(5000)
            pg.wait_for_timeout(1500)
            path = OUT / f"{i}_{name.split()[0].lower().strip('&')}.png"
            pg.screenshot(path=str(path), full_page=True)
            print(f"{path.name}: {path.stat().st_size:,} bytes")
        b.close()


if __name__ == "__main__":
    main()
