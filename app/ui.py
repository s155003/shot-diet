"""Interface layer: type scale, Streamlit chrome overrides, page furniture.

This is a reference tool, not an article. Nothing renders until the reader asks
for it, prose is limited to what a label cannot say on its own, and the tables
are the point rather than an appendix to it. Figures are set at reading size in
dense rows instead of in hero tiles.
"""
from __future__ import annotations

from contextlib import contextmanager

import pandas as pd
import streamlit as st

import theme as T


def boot() -> None:
    """Inject the stylesheet. Call once, immediately after set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# furniture
# --------------------------------------------------------------------------

def kicker(text: str) -> None:
    st.markdown(f'<p class="kicker">{text}</p>', unsafe_allow_html=True)


def title(text: str, sub: str = "") -> None:
    st.markdown(f'<h1 class="h1">{text}</h1>', unsafe_allow_html=True)
    if sub:
        note(sub)


def section(text: str) -> None:
    st.markdown(f'<h2 class="h2">{text}</h2>', unsafe_allow_html=True)


def note(text: str) -> None:
    """One line of clarification. Not a paragraph."""
    st.markdown(f'<p class="note">{text}</p>', unsafe_allow_html=True)


def caption(text: str, top: int = 6) -> None:
    st.markdown(f'<p class="cap" style="margin-top:{top}px">{text}</p>',
                unsafe_allow_html=True)


def rule(space: int = 22) -> None:
    st.markdown(f'<hr class="hr" style="margin:{space}px 0">',
                unsafe_allow_html=True)


def statline(pairs: list[tuple[str, str]]) -> None:
    """A dense label/value strip. The summary row on a reference page."""
    cells = "".join(
        f'<div class="sl-cell"><span class="sl-k">{k}</span>'
        f'<span class="sl-v">{v}</span></div>' for k, v in pairs)
    st.markdown(f'<div class="statline">{cells}</div>', unsafe_allow_html=True)


def empty(text: str) -> None:
    """Placeholder shown before the reader has searched for anything."""
    st.markdown(f'<div class="empty">{text}</div>', unsafe_allow_html=True)


@contextmanager
def reveal(label: str):
    with st.expander(label, expanded=False):
        yield


def figure(fig, cap: str = "", **kwargs) -> None:
    st.plotly_chart(fig, width="stretch", **kwargs)
    if cap:
        caption(cap)


def table(df: pd.DataFrame, fmt: dict | None = None, height: int | None = None) -> None:
    st.dataframe(df.style.format(fmt or {}), width="stretch", hide_index=True,
                 **({"height": height} if height else {}))


_CSS = f"""
<style>
  /* ---------- Streamlit chrome ---------- */
  [data-testid="stHeader"], [data-testid="stToolbar"] {{
      background: transparent; height: 0; visibility: hidden; }}
  #MainMenu, footer, [data-testid="stDecoration"] {{ display: none; }}
  [data-testid="stMain"] {{ background: {T.PLANE}; }}
  .block-container {{ padding-top: 2.1rem; padding-bottom: 4rem;
                      max-width: 1280px; }}

  /* ---------- type ---------- */
  html, body, [class*="css"], .stMarkdown {{
      font-family: {T.FONT}; -webkit-font-smoothing: antialiased; }}

  .kicker {{ color: {T.MUTED}; font-size: 0.68rem; font-weight: 620;
             letter-spacing: 0.15em; text-transform: uppercase; margin: 0 0 8px; }}
  .h1, h1 {{ color: {T.INK}; font-size: 1.62rem !important; font-weight: 660;
             letter-spacing: -0.018em; line-height: 1.2; margin: 0 0 6px; }}
  .h2, h2 {{ color: {T.INK}; font-size: 1.04rem !important; font-weight: 640;
             letter-spacing: -0.008em; margin: 0 0 8px; }}
  h3 {{ color: {T.INK}; font-size: 0.95rem !important; font-weight: 640; }}
  .note {{ color: {T.INK_2}; font-size: 0.90rem; line-height: 1.5;
           max-width: 88ch; margin: 0 0 4px; }}
  .cap {{ color: {T.MUTED}; font-size: 0.78rem; line-height: 1.5;
          max-width: 92ch; margin: 6px 0 0; }}
  .hr {{ border: none; border-top: 1px solid {T.GRID}; }}

  /* ---------- summary strip ---------- */
  .statline {{ display: flex; flex-wrap: wrap; gap: 0;
               border: 1px solid {T.GRID}; border-radius: 2px;
               background: {T.SURFACE}; margin: 2px 0 14px; }}
  .sl-cell {{ padding: 9px 18px; border-right: 1px solid {T.GRID};
              display: flex; flex-direction: column; gap: 2px; min-width: 96px; }}
  .sl-cell:last-child {{ border-right: none; }}
  .sl-k {{ color: {T.MUTED}; font-size: 0.66rem; font-weight: 620;
           letter-spacing: 0.09em; text-transform: uppercase; }}
  .sl-v {{ color: {T.INK}; font-size: 1.02rem; font-weight: 640;
           font-variant-numeric: tabular-nums; }}

  .empty {{ border: 1px dashed {T.GRID}; border-radius: 2px; background: {T.SURFACE};
            padding: 30px 22px; color: {T.MUTED}; font-size: 0.88rem;
            line-height: 1.6; }}

  /* ---------- sidebar as a nav ----------
     The radio dot sits three divs deep inside the option label, so
     `label > div:first-child` misses it and hits the hidden input wrapper.
     `data-selected` is a sturdier active hook than :has(input:checked). */
  [data-testid="stSidebar"] {{ background: {T.SURFACE};
      border-right: 1px solid {T.GRID}; }}
  [data-testid="stSidebar"] .block-container {{ padding-top: 2rem; }}
  [data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; }}
  [data-testid="stRadioOption"] {{ padding: 6px 12px; border-radius: 2px;
      margin: 0; transition: background .12s; cursor: pointer; }}
  [data-testid="stRadioOption"]:hover {{ background: {T.PLANE}; }}
  [data-testid="stRadioOption"] > div > div > div:first-child {{ display: none; }}
  [data-testid="stRadioOption"] p {{ font-size: 0.9rem; color: {T.INK_2}; }}
  [data-testid="stRadioOption"][data-selected="true"] {{
      background: {T.PLANE}; box-shadow: inset 2px 0 0 {T.SERIES[0]}; }}
  [data-testid="stRadioOption"][data-selected="true"] p {{
      color: {T.INK}; font-weight: 640; }}

  /* ---------- controls ---------- */
  [data-testid="stWidgetLabel"] p {{
      font-size: 0.68rem !important; font-weight: 620; color: {T.MUTED};
      letter-spacing: 0.09em; text-transform: uppercase; }}
  /* This Streamlit build renders widgets through react-aria, not BaseWeb, so
     `[data-baseweb="select"]`, `[data-baseweb="tag"]` and `[role="slider"]`
     match nothing. The combobox shell is the role="group" inside stSelectbox;
     the slider thumb takes its colour from theme.primaryColor in
     .streamlit/config.toml, so it needs no rule here. */
  [data-testid="stSelectbox"] [role="group"] {{
      border-color: {T.GRID} !important; border-radius: 2px !important;
      background: {T.SURFACE} !important; }}
  [data-testid="stSelectbox"] input {{ font-size: 0.92rem; }}
  [data-testid="stSliderThumbValue"] {{
      color: {T.INK_2} !important; font-size: 0.76rem; font-weight: 620; }}
  [data-testid="stBaseButton-secondary"] {{
      border: 1px solid {T.GRID}; border-radius: 2px; background: {T.SURFACE};
      color: {T.INK_2}; font-size: 0.84rem; padding: 3px 12px; }}
  [data-testid="stBaseButton-secondary"]:hover {{
      border-color: {T.SERIES[0]}; color: {T.SERIES[0]}; }}

  /* ---------- disclosure ---------- */
  [data-testid="stExpander"] {{ border: none !important; }}
  [data-testid="stExpander"] details {{ border: none; border-top: 1px solid {T.GRID};
      border-radius: 0; background: transparent; }}
  [data-testid="stExpander"] summary {{ padding: 10px 0 !important; }}
  [data-testid="stExpander"] summary p {{
      font-size: 0.74rem !important; font-weight: 620; color: {T.MUTED};
      letter-spacing: 0.09em; text-transform: uppercase; }}
  [data-testid="stExpander"] summary:hover p {{ color: {T.SERIES[0]}; }}

  /* ---------- tables: the point of the page ---------- */
  [data-testid="stDataFrame"] {{ font-size: 0.85rem; }}
  [data-testid="stDataFrame"] * {{ font-variant-numeric: tabular-nums; }}

  hr {{ border-color: {T.GRID}; }}
  a {{ color: {T.SERIES[0]}; }}
</style>
"""
