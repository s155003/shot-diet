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
    assert at.title, f"{page} rendered no title"


def test_optimiser_responds_to_budget() -> None:
    """Moving the budget slider must change the prescription."""
    at = run("Shot-diet optimiser")
    small = at.metric[2].value
    at.slider[0].set_value(20).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.metric[2].value != small, "budget slider did not change the result"


def test_player_page_switches_player() -> None:
    at = run("Players")
    at.selectbox[1].select_index(3).run()
    assert not at.exception, [e.value for e in at.exception]


PHASES = ["run", "gather", "rise", "dunk", "fall", "land"]


def test_banner_markup_is_complete() -> None:
    """Every phase the sequencer toggles must have poses defined for it."""
    import banner

    html = banner._TEMPLATE
    for key, val in (("__SURFACE__", "#fcfcfb"), ("__INK__", "#0b0b0b")):
        assert key in html, f"{key} placeholder missing from the template"

    for phase in PHASES:
        assert f".banner.{phase} " in html, f"no CSS poses for the {phase!r} phase"
        assert f"only('{phase}')" in html, f"sequencer never enters {phase!r}"

    # Each joint the poses drive needs an explicit view-box pivot; the CSS
    # default pivots on the bounding box and tears the figure apart.
    for joint in ("thighL", "thighR", "shinL", "shinR",
                  "upperL", "upperR", "foreL", "foreR", "trunk"):
        assert re.search(rf"#{joint}\s*\{{\s*transform-origin:", html), \
            f"{joint} has no explicit pivot"
        assert f'id="{joint}"' in html, f"{joint} not in the markup"

    # A transform attribute on an element that also gets a CSS transform is
    # silently discarded, so the moving groups must not carry one.
    for moving in ('<g id="rig" transform=', '<g id="defender" transform='):
        assert moving not in html, f"{moving!r} would be overridden by CSS"


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
