"""Freeze the banner in each pose so the rig can be inspected frame by frame.

Screenshotting a live timeline drifts, because the capture itself costs more
than the gap between phases. This forces each state class instead, which is
what actually needs checking: whether the skeleton holds together in every pose.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1])
URL = "http://localhost:8511"

# (state class, rig x, rig y)
POSES = [
    ("run", 210, 0),
    ("run", 520, 0),
    ("gather", 852, 8),
    ("rise", 890, -70),
    ("dunk", 890, -70),
    ("fall", 895, -34),
    ("land", 900, 0),
    (None, 900, 0),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 700})
        pg.goto(URL, wait_until="networkidle", timeout=90_000)
        pg.wait_for_selector("iframe", timeout=90_000)
        pg.wait_for_timeout(4000)

        frame = next((f for f in pg.frames
                      if f != pg.main_frame and f.query_selector("#banner")), None)
        if frame is None:
            raise SystemExit("banner iframe not found")
        el = pg.query_selector("iframe")

        for i, (state, x, y) in enumerate(POSES):
            frame.evaluate(
                """([state, x, y]) => {
                  const svg = document.getElementById('banner');
                  const rig = document.getElementById('rig');
                  ['run','gather','rise','dunk','fall','land']
                    .forEach(s => svg.classList.remove(s));
                  svg.classList.add('go');
                  if (state) svg.classList.add(state);
                  rig.style.transition = 'none';
                  rig.style.transform = `translate(${x}px,${y}px)`;
                }""", [state, x, y])
            pg.wait_for_timeout(700)
            name = f"{i}_{state or 'rest'}.png"
            el.screenshot(path=str(OUT / name))
            print(name)
        b.close()


if __name__ == "__main__":
    main()
