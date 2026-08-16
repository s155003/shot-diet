"""Freeze the banner at fixed progress values so each pose can be inspected.

The animation is a pure function of t, so it can be scrubbed straight to any
frame. Screenshotting a live timeline drifts, because the capture costs more
than the gap between phases.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1])
URL = "http://localhost:8511"
TS = [0.00, 0.18, 0.36, 0.50, 0.56, 0.66, 0.75, 0.80, 0.84, 0.90, 0.96, 1.00]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 900})
        pg.goto(URL, wait_until="networkidle", timeout=90_000)
        pg.wait_for_selector("iframe", timeout=90_000)
        pg.wait_for_timeout(5000)

        fr = next((f for f in pg.frames
                   if f != pg.main_frame and f.query_selector("#banner")), None)
        if fr is None:
            raise SystemExit("banner iframe not found")
        el = pg.query_selector("iframe")

        for t in TS:
            fr.evaluate("(t) => window.__scrub(t)", t)
            pg.wait_for_timeout(160)
            name = f"t{int(t * 100):03d}.png"
            el.screenshot(path=str(OUT / name))
            print(name)
        b.close()


if __name__ == "__main__":
    main()
