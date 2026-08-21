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


def run(page: str | None) -> AppTest:
    """Open a tab. None is the landing page, which is what no selection means."""
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception, f"{page}: {[e.value for e in at.exception]}"
    if page is not None:
        at.segmented_control[0].set_value(page).run()
        assert not at.exception, f"{page}: {[e.value for e in at.exception]}"
    return at


def body(at: AppTest) -> str:
    return " ".join(str(m.value) for m in at.markdown)


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page: str) -> None:
    at = run(page)
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
    assert len(at.segmented_control[0].options) <= 4, at.segmented_control[0].options


def test_landing_is_the_court() -> None:
    """No tab selected is the landing page, and it is the court."""
    import hero

    at = run(None)
    assert at.markdown, "landing rendered nothing"
    # the landing is a single component, so the tools must not also render
    assert not at.dataframe, "landing rendered a table"
    assert 'class="stage"' in hero._TEMPLATE, "court is not the page"
    assert 'class="mast"' in hero._TEMPLATE, "masthead is not on the court"
    assert "Shot Diet" in hero._TEMPLATE, "hero lost the project name"
    assert "wordmark" in hero._TEMPLATE, "project name is not the hero element"
    assert "good shooter" in hero._TEMPLATE, "hero lost the plain-English pitch"
    assert "shot chart" in hero._TEMPLATE, "hero never says what you get"
    # The idea only lands with a concrete comparison, so the worked example is
    # part of the explanation rather than decoration.
    assert 'class="ex"' in hero._TEMPLATE, "hero lost the worked example"
    assert "better shooter" in hero._TEMPLATE, "example lost its punchline"
    assert "Both are true" in hero._TEMPLATE, "example lost the contradiction"
    # the counterfactual is the mechanism; without it the numbers come from nowhere
    assert "what would an average NBA player have scored" in hero._TEMPLATE, (
        "hero never explains how it knows what a shot was worth")
    ex = hero._example()
    assert set(ex) == {"a", "b"}, ex
    assert ex["a"]["scored"] > ex["b"]["scored"], "player A should score more"
    assert (ex["a"]["scored"] - ex["a"]["worth"]) < 0 < (
        ex["b"]["scored"] - ex["b"]["worth"]), "the contrast no longer holds"


def test_players_tab_is_the_tool_not_the_pitch() -> None:
    """The landing sells; the Players tab gets straight to work."""
    at = run("Players")
    assert '<h1 class="h1">' in body(at), "Players has no heading"
    assert 'class="stage"' not in body(at), "the landing court leaked into a tool"


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
