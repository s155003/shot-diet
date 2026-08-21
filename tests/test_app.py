"""Render every page headlessly and fail on any exception."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app" / "streamlit_app.py")
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "src")]

PAGES = ["Players", "Leaders", "Teams", "Findings"]
SEARCH_FIRST = ["Players"]


def run(page: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception, f"{page}: {[e.value for e in at.exception]}"
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, f"{page}: {[e.value for e in at.exception]}"
    return at


def body(at: AppTest) -> str:
    return " ".join(str(m.value) for m in at.markdown)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page: str) -> None:
    at = run(page)
    if page == "Players":
        # The landing masthead lives inside the hero iframe, so the page's own
        # markdown carries the glossary rather than an h1.
        assert 'class="legend"' in body(at), "Players rendered no masthead"
    else:
        assert '<h1 class="h1">' in body(at), f"{page} rendered no heading"


@pytest.mark.parametrize("page", SEARCH_FIRST)
def test_nothing_loads_before_a_search(page: str) -> None:
    """The whole point of the rebuild: no player's data until one is picked.

    AppTest exposes no accessor for plotly charts, so absence of any table plus
    the placeholder is what stands in for "nothing has loaded yet".
    """
    at = run(page)
    txt = body(at)
    assert 'class="empty"' in txt, f"{page} shows data before anything is searched"
    assert 'class="statline"' not in txt, f"{page} shows a summary unprompted"
    assert "<table" not in txt, f"{page} rendered a table unprompted"


def pick(at: AppTest, name: str) -> AppTest:
    """Drive the type-to-search the way a reader would."""
    if at.text_input:
        at.text_input[0].set_value(name).run()
        assert not at.exception, [e.value for e in at.exception]
    if 'class="statline"' not in body(at):   # several matches: click the first
        hits = [b for b in at.button if b.label != "Clear"]
        assert hits, f"no results for {name!r}"
        hits[0].click().run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def test_search_finds_a_player_despite_accents() -> None:
    """Typing `jokic` has to find `Nikola Jokić`, or the search is useless."""
    at = run("Players")
    at = pick(at, "jokic")
    assert "Jokić" in body(at), "accent-folded search did not reach the player"
    assert 'class="statline"' in body(at), "no summary strip after choosing a player"
    assert "<table" in body(at), "no zone table after choosing a player"


def test_search_reports_no_match() -> None:
    at = run("Players")
    at.text_input[0].set_value("zzzznotaplayer").run()
    assert not at.exception, [e.value for e in at.exception]
    assert "No player matching" in body(at)


def test_optimiser_responds_to_budget() -> None:
    at = run("Players")
    at = pick(at, "jokic")
    before = body(at)
    at.slider[0].set_value(20).run()
    assert not at.exception, [e.value for e in at.exception]
    assert body(at) != before, "budget slider did not change the result"


def test_leaders_sorts() -> None:
    at = run("Leaders")
    assert "<table" in body(at), "leaders table missing"
    before = body(at)
    next(s for s in at.selectbox if s.label == "Sort by").set_value(
        "Shot making").run()
    assert not at.exception, [e.value for e in at.exception]
    assert body(at) != before, "changing the sort did not reorder the table"


def test_nav_stays_small() -> None:
    """Four sections. Every extra one is a decision the reader has to make."""
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert len(at.sidebar.radio[0].options) <= 4, at.sidebar.radio[0].options


def test_landing_explains_itself() -> None:
    """The landing page has to say what the product is before it asks for input."""
    import hero

    at = run("Players")
    assert 'class="legend"' in body(at), "no column glossary on the landing page"
    assert "good shooter" in hero._TEMPLATE, "hero lost the plain-English pitch"
    assert "splits his scoring in two" in hero._TEMPLATE, "hero never says what it does"


def test_hero_stands_down_once_a_player_is_chosen() -> None:
    at = run("Players")
    at = pick(at, "jokic")
    assert '<h1 class="h1">' in body(at), "no page heading once the hero steps aside"


def test_hero_data_is_real_and_inlined() -> None:
    """The hero is the product's own chart, not decoration, so it needs data."""
    import json

    import hero

    data = json.loads(hero._bins())
    assert data["n_shots"] > 100_000, data["n_shots"]
    assert len(data["bins"]) > 100, len(data["bins"])
    pps = [b["p"] for b in data["bins"]]
    assert min(pps) < 0.9 < max(pps), (min(pps), max(pps))
    # nothing may animate from invisible
    assert "from{opacity:.22" in hero._TEMPLATE
    assert "prefers-reduced-motion" in hero._TEMPLATE


def test_no_bare_stat_tiles_anywhere() -> None:
    """Figures belong in strips and tables, not in Streamlit metric widgets."""
    for page in PAGES:
        at = run(page)
        assert not at.metric, f"{page} has {len(at.metric)} bare stat tiles"
