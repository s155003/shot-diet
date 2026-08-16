"""Render every dashboard page headlessly and fail on any exception."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app" / "streamlit_app.py")
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "src")]

PAGES = ["The finding", "Players", "Shot-diet optimiser", "Teams",
         "Method & validation"]


def run(page: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception, f"{page}: {[e.value for e in at.exception]}"
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, f"{page}: {[e.value for e in at.exception]}"
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page: str) -> None:
    at = run(page)
    # Headings are custom editorial markup rather than st.title, so check the
    # page actually produced prose.
    body = " ".join(str(m.value) for m in at.markdown)
    assert "ed-h1" in body, f"{page} rendered no heading"
    assert len(body) > 400, f"{page} rendered almost nothing"


def _prose(at: AppTest) -> str:
    return " ".join(str(m.value) for m in at.markdown)


def test_optimiser_responds_to_budget() -> None:
    """Moving the budget slider must change the prescription."""
    at = run("Shot-diet optimiser")
    before = _prose(at)
    at.slider[0].set_value(20).run()
    assert not at.exception, [e.value for e in at.exception]
    assert _prose(at) != before, "budget slider did not change the result"


def test_numbers_stay_behind_disclosure() -> None:
    """The landing page argues in prose; exact figures live in expanders."""
    at = run("The finding")
    labels = [str(e.label) for e in at.expander]
    assert labels, "no progressive disclosure on the landing page"
    assert all(lbl.lower().startswith("show") for lbl in labels), labels
    # Stat tiles were the thing that shouted; there should be none left.
    assert not at.metric, f"{len(at.metric)} bare stat tiles still on the page"


def test_player_page_switches_player() -> None:
    at = run("Players")
    at.selectbox[1].select_index(3).run()
    assert not at.exception, [e.value for e in at.exception]


JOINTS = ["thighL", "thighR", "shinL", "shinR",
          "upperL", "upperR", "foreL", "foreR", "trunk"]
POSES = ["GATHER", "RISE", "DUNK", "FALL", "LAND", "REST"]


def test_banner_markup_is_complete() -> None:
    import banner

    html = banner._TEMPLATE

    # Every joint needs an explicit view-box pivot. The CSS default pivots on
    # each group's bounding box, which is nowhere near the joint, and the
    # figure comes apart the moment anything rotates. Selectors are grouped
    # (`#shinL, #shinR { ... }`), so collect whatever each pivot rule targets.
    pivoted: set[str] = set()
    for sel in re.findall(r"([^{}]+)\{[^{}]*transform-origin:[^{}]*\}", html):
        pivoted.update(re.findall(r"#(\w+)", sel))

    for joint in JOINTS:
        assert joint in pivoted, f"{joint} has no explicit pivot"
        assert f'id="{joint}"' in html, f"{joint} not in the markup"

    # A transform attribute on an element that also gets a CSS transform is
    # discarded wholesale, so anything that moves keeps its offset elsewhere.
    for moving in ('<g id="rig" transform=', '<g id="defender" transform='):
        assert moving not in html, f"{moving!r} would be overridden by CSS"


def test_banner_is_a_pure_function_of_progress() -> None:
    """Scrubbing only works if every pose is keyed off t, with no wall clock."""
    import banner

    html = banner._TEMPLATE
    assert "function frame(t)" in html, "no frame(t) entry point to scrub"
    for pose in POSES:
        assert re.search(rf"var {pose}\s*=\s*\{{", html), f"{pose} pose missing"
        for joint in JOINTS:
            assert f"{joint}:" in html.split(f"var {pose}")[1][:400], \
                f"{pose} does not set {joint}"

    # Scroll has to drive it, and there must be a fallback when the parent
    # document is unreachable.
    assert "addEventListener('scroll'" in html, "nothing listens for scroll"
    assert "window.parent.document" in html, "never reads the parent scroller"
    assert "loopStart" in html, "no fallback when the parent is unreadable"
    assert "prefers-reduced-motion" in html, "no reduced-motion path"


def test_banner_renders_without_placeholders(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr("streamlit.components.v1.html",
                        lambda h, **kw: captured.update(html=h, kw=kw))
    import banner

    banner.render()
    left = re.findall(r"__[A-Z0-9_]+__", captured["html"])
    assert not left, f"unsubstituted palette placeholders: {sorted(set(left))}"
    assert "#fcfcfb" in captured["html"], "palette was never substituted in"
    assert captured["kw"]["height"] == banner.HEIGHT
