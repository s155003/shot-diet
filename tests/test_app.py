"""Render every dashboard page headlessly and fail on any exception."""
from __future__ import annotations

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
