"""Render every page headlessly and fail on any exception."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app" / "streamlit_app.py")
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "src")]

PAGES = ["Search", "Leaders", "Teams", "Shot-diet optimiser", "Findings", "Method"]
SEARCH_FIRST = ["Search", "Shot-diet optimiser"]


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
    assert not at.dataframe, f"{page} rendered {len(at.dataframe)} tables unprompted"


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
    at = run("Search")
    at = pick(at, "jokic")
    assert "Jokić" in body(at), "accent-folded search did not reach the player"
    assert 'class="statline"' in body(at), "no summary strip after choosing a player"
    assert at.dataframe, "no zone table after choosing a player"


def test_search_reports_no_match() -> None:
    at = run("Search")
    at.text_input[0].set_value("zzzznotaplayer").run()
    assert not at.exception, [e.value for e in at.exception]
    assert "No player matching" in body(at)


def test_optimiser_responds_to_budget() -> None:
    at = run("Shot-diet optimiser")
    at = pick(at, "jokic")
    before = body(at)
    at.slider[0].set_value(20).run()
    assert not at.exception, [e.value for e in at.exception]
    assert body(at) != before, "budget slider did not change the result"


def test_leaders_sorts() -> None:
    at = run("Leaders")
    assert at.dataframe, "leaders table missing"
    sort_by = next(s for s in at.selectbox if s.label == "Sort by")
    top_before = at.dataframe[0].value.iloc[0]["Player"]
    sort_by.set_value("Shot making").run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.dataframe[0].value.iloc[0]["Player"] != top_before, \
        "changing the sort did not reorder the table"


def test_no_bare_stat_tiles_anywhere() -> None:
    """Figures belong in strips and tables, not in Streamlit metric widgets."""
    for page in PAGES:
        at = run(page)
        assert not at.metric, f"{page} has {len(at.metric)} bare stat tiles"
