"""Editorial layer: type system, Streamlit chrome overrides, page furniture.

Two rules drive everything here.

Numbers are not decoration. A figure belongs inside a sentence or inside a
chart, where it carries context. Bare stat tiles make a reader parse four
unrelated quantities before they know what the page is about, so the landing
page states its argument in words and keeps the precise values one click away
behind `reveal()`.

Chrome recedes. Hairline rules instead of boxes, one accent colour, a single
prose measure, and Streamlit's stock header, slider bubbles and heat-mapped
tables all toned down or removed.
"""
from __future__ import annotations

from contextlib import contextmanager

import pandas as pd
import streamlit as st

import theme as T

MEASURE = "68ch"          # prose line length
_TYPE_SCALE = {"h1": "2.05rem", "h2": "1.30rem", "h3": "1.02rem"}


def boot() -> None:
    """Inject the stylesheet. Call once, immediately after set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# page furniture
# --------------------------------------------------------------------------

def kicker(text: str) -> None:
    st.markdown(f'<p class="kicker">{text}</p>', unsafe_allow_html=True)


def title(text: str, sub: str = "") -> None:
    st.markdown(f'<h1 class="ed-h1">{text}</h1>', unsafe_allow_html=True)
    if sub:
        lede(sub)


def lede(text: str) -> None:
    st.markdown(f'<p class="lede">{text}</p>', unsafe_allow_html=True)


def para(text: str) -> None:
    st.markdown(f'<p class="para">{text}</p>', unsafe_allow_html=True)


def section(text: str, sub: str = "") -> None:
    st.markdown(f'<h2 class="ed-h2">{text}</h2>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<p class="para">{sub}</p>', unsafe_allow_html=True)


def rule(space: int = 26) -> None:
    st.markdown(f'<hr class="ed-rule" style="margin:{space}px 0">',
                unsafe_allow_html=True)


def caption(text: str, top: int = 6) -> None:
    st.markdown(f'<p class="cap" style="margin-top:{top}px">{text}</p>',
                unsafe_allow_html=True)


def pull(text: str) -> None:
    """A quiet emphasis block. Used sparingly, for the one claim that matters."""
    st.markdown(f'<p class="pull">{text}</p>', unsafe_allow_html=True)


@contextmanager
def reveal(label: str = "Show the numbers"):
    """Progressive disclosure: exact figures stay collapsed until asked for."""
    with st.expander(label, expanded=False):
        yield


def figure(fig, cap: str = "", **kwargs) -> None:
    st.plotly_chart(fig, width="stretch", **kwargs)
    if cap:
        caption(cap)


def table(df: pd.DataFrame, fmt: dict | None = None, height: int | None = None) -> None:
    """A plain table. No heat maps: the colour was fighting the charts."""
    styled = df.style.format(fmt or {})
    st.dataframe(styled, width="stretch", hide_index=True,
                 **({"height": height} if height else {}))


_CSS = f"""
<style>
  /* ---------- Streamlit chrome ---------- */
  [data-testid="stHeader"], [data-testid="stToolbar"] {{
      background: transparent; height: 0; visibility: hidden; }}
  #MainMenu, footer, [data-testid="stDecoration"] {{ display: none; }}
  [data-testid="stMain"] {{ background: {T.PLANE}; }}
  .block-container {{ padding-top: 2.4rem; padding-bottom: 5rem;
                      max-width: 1180px; }}

  /* ---------- type ---------- */
  html, body, [class*="css"], .stMarkdown {{
      font-family: {T.FONT};
      -webkit-font-smoothing: antialiased; }}

  .kicker {{ color: {T.MUTED}; font-size: 0.70rem; font-weight: 620;
             letter-spacing: 0.14em; text-transform: uppercase;
             margin: 0 0 10px; }}

  .ed-h1, h1 {{ color: {T.INK}; font-size: {_TYPE_SCALE['h1']} !important;
                font-weight: 660; letter-spacing: -0.021em; line-height: 1.16;
                margin: 0 0 14px; max-width: 30ch; }}

  .ed-h2, h2 {{ color: {T.INK}; font-size: {_TYPE_SCALE['h2']} !important;
                font-weight: 640; letter-spacing: -0.012em; line-height: 1.3;
                margin: 0 0 10px; }}
  h3 {{ color: {T.INK}; font-size: {_TYPE_SCALE['h3']} !important;
        font-weight: 640; letter-spacing: -0.004em; }}

  .lede {{ color: {T.INK_2}; font-size: 1.06rem; line-height: 1.62;
           max-width: {MEASURE}; margin: 0 0 6px; }}
  .para {{ color: {T.INK_2}; font-size: 0.97rem; line-height: 1.7;
           max-width: {MEASURE}; margin: 0 0 12px; }}
  .cap  {{ color: {T.MUTED}; font-size: 0.80rem; line-height: 1.55;
           max-width: 76ch; margin: 6px 0 0; }}

  .pull {{ color: {T.INK}; font-size: 1.10rem; line-height: 1.55;
           font-weight: 560; letter-spacing: -0.006em;
           max-width: 60ch; margin: 18px 0;
           padding-left: 16px; border-left: 2px solid {T.AXIS}; }}

  /* a figure inside prose: same weight as the text around it */
  .n {{ font-weight: 640; color: {T.INK}; font-variant-numeric: tabular-nums; }}

  .ed-rule {{ border: none; border-top: 1px solid {T.GRID}; }}

  /* ---------- sidebar as a nav ----------
     Streamlit nests the radio dot three divs deep inside the option label
     (label > div > div > div:first-child); the label's own first child is the
     visually-hidden input wrapper, so `label > div:first-child` misses it.
     `data-selected` on the label is a cleaner active hook than :has(). */
  [data-testid="stSidebar"] {{ background: {T.SURFACE};
      border-right: 1px solid {T.GRID}; }}
  [data-testid="stSidebar"] .block-container {{ padding-top: 2.2rem; }}
  [data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; }}
  [data-testid="stRadioOption"] {{
      padding: 7px 12px; border-radius: 2px; margin: 0;
      transition: background .12s; cursor: pointer; }}
  [data-testid="stRadioOption"]:hover {{ background: {T.PLANE}; }}
  [data-testid="stRadioOption"] > div > div > div:first-child {{ display: none; }}
  [data-testid="stRadioOption"] p {{
      font-size: 0.92rem; color: {T.INK_2}; }}
  [data-testid="stRadioOption"][data-selected="true"] {{
      background: {T.PLANE}; box-shadow: inset 2px 0 0 {T.SERIES[0]}; }}
  [data-testid="stRadioOption"][data-selected="true"] p {{
      color: {T.INK}; font-weight: 640; }}

  /* ---------- controls ---------- */
  [data-testid="stWidgetLabel"] p {{
      font-size: 0.74rem !important; font-weight: 600; color: {T.MUTED};
      letter-spacing: 0.07em; text-transform: uppercase; }}
  [data-baseweb="select"] > div {{
      border-color: {T.GRID} !important; border-radius: 2px !important;
      background: {T.SURFACE} !important; font-size: 0.92rem; }}
  [data-testid="stSlider"] [data-testid="stThumbValue"] {{
      color: {T.INK_2}; font-size: 0.78rem; font-weight: 600; }}
  [data-baseweb="slider"] [role="slider"] {{ background: {T.SERIES[0]}; }}
  /* Multiselect pills ship as saturated blue chips, which outshout the chart
     they are filtering. Neutral chip, coloured only by a leading rule. */
  [data-baseweb="tag"] {{
      background: {T.PLANE} !important; color: {T.INK} !important;
      border: 1px solid {T.GRID} !important;
      border-left: 2px solid {T.SERIES[0]} !important;
      border-radius: 2px !important; font-size: 0.84rem !important; }}
  [data-baseweb="tag"] span, [data-baseweb="tag"] svg {{
      color: {T.INK_2} !important; fill: {T.INK_2} !important; }}

  /* ---------- progressive disclosure ---------- */
  [data-testid="stExpander"] {{ border: none !important; }}
  [data-testid="stExpander"] details {{
      border: none; border-top: 1px solid {T.GRID};
      border-radius: 0; background: transparent; }}
  [data-testid="stExpander"] summary {{
      padding: 11px 0 !important; }}
  [data-testid="stExpander"] summary p {{
      font-size: 0.76rem !important; font-weight: 620; color: {T.MUTED};
      letter-spacing: 0.09em; text-transform: uppercase; }}
  [data-testid="stExpander"] summary:hover p {{ color: {T.SERIES[0]}; }}
  [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
      padding-top: 2px; }}

  /* ---------- tables ---------- */
  [data-testid="stDataFrame"] {{ font-size: 0.86rem; }}
  [data-testid="stDataFrame"] * {{ font-variant-numeric: tabular-nums; }}

  /* ---------- misc ---------- */
  [data-testid="stElementContainer"]:has(> iframe) {{ margin-bottom: 4px; }}
  hr {{ border-color: {T.GRID}; }}
  a {{ color: {T.SERIES[0]}; }}
</style>
"""
