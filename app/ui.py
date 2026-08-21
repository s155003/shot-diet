"""Interface layer: type scale, Streamlit chrome overrides, page furniture.

This is a reference tool, not an article. Nothing renders until the reader asks
for it, prose is limited to what a label cannot say on its own, and the tables
are the point rather than an appendix to it. Figures are set at reading size in
dense rows instead of in hero tiles.
"""
from __future__ import annotations

import html
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


def legend(items: list[tuple[str, str]]) -> None:
    """A one-line glossary. Cheaper than a paragraph explaining the columns."""
    cells = "".join(f'<div class="lg-item"><span class="lg-k">{k}</span>'
                    f'<span class="lg-v">{v}</span></div>' for k, v in items)
    st.markdown(f'<div class="legend">{cells}</div>', unsafe_allow_html=True)


def playerhead(name: str, meta: str) -> None:
    """The name bar at the top of a subject's sheet."""
    st.markdown(f'<div class="phead"><h1 class="h1">{name}</h1>'
                f'<p class="cap">{meta}</p></div>', unsafe_allow_html=True)


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


def statsheet(df: pd.DataFrame, fmt: dict | None = None,
              left: tuple[str, ...] = (), signed_cols: tuple[str, ...] = (),
              height: int | None = None) -> None:
    """A box-score table: dark header, zebra rows, figures right-aligned.

    Rendered as real HTML rather than through st.dataframe, whose grid draws to
    a canvas and ignores almost all styling. The trade is column-header sorting,
    which the explicit sort controls already cover.
    """
    fmt = fmt or {}
    cols = list(df.columns)
    head = "".join(
        f'<th class="{"l" if c in left else ""}">{html.escape(str(c))}</th>'
        for c in cols)

    rows = []
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            try:
                txt = format(v, fmt[c].strip("{:}")) if c in fmt else str(v)
            except (ValueError, TypeError):
                txt = "" if pd.isna(v) else str(v)
            cls = "l" if c in left else ""
            if c in signed_cols and isinstance(v, (int, float)) and not pd.isna(v):
                cls += " pos" if v > 0 else (" neg" if v < 0 else "")
            cells.append(f'<td class="{cls.strip()}">{html.escape(txt)}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")

    style = f' style="max-height:{height}px"' if height else ""
    st.markdown(
        f'<div class="ss-wrap"{style}><table class="ss">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody>"
        f"</table></div>", unsafe_allow_html=True)


_CSS = f"""
<style>
  /* ---------- Streamlit chrome ---------- */
  [data-testid="stHeader"], [data-testid="stToolbar"] {{
      background: transparent; height: 0; visibility: hidden; }}
  #MainMenu, footer, [data-testid="stDecoration"] {{ display: none; }}
  [data-testid="stMain"] {{ background: {T.PLANE}; }}
  .block-container {{ padding-top: 1.5rem; padding-bottom: 4rem;
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
            padding: 26px 22px; color: {T.MUTED}; font-size: 0.88rem;
            line-height: 1.6; }}

  .legend {{ display: flex; flex-wrap: wrap; gap: 0 26px; margin: 10px 0 4px; }}
  .lg-item {{ display: flex; align-items: baseline; gap: 7px; }}
  .lg-k {{ color: {T.INK}; font-size: 0.66rem; font-weight: 680;
           letter-spacing: 0.09em; text-transform: uppercase; }}
  .lg-v {{ color: {T.MUTED}; font-size: 0.82rem; }}

  .phead {{ border-left: 3px solid {T.SERIES[0]}; padding-left: 12px;
            margin: 0 0 10px; }}
  .phead .h1 {{ margin-bottom: 2px; }}
  .phead .cap {{ margin-top: 0; }}

  /* ---------- masthead ---------- */
  [data-testid="stSidebar"] {{ display: none; }}
  .brand {{ color: {T.INK}; font-size: 1.02rem; font-weight: 720;
            letter-spacing: -.02em; margin: 6px 0 0; }}
  .barmeta {{ color: {T.MUTED}; font-size: 0.72rem; text-align: right;
              margin: 11px 0 0; }}
  .barrule {{ border-top: 1px solid {T.GRID}; margin: 6px 0 20px; }}

  /* Segmented control restyled as tabs. Streamlit renders it as
     [data-testid="stButtonGroup"] containing a role="radiogroup" of
     button[data-variant="segmented_control"]; there is no stSegmentedControl
     test id, and the active one is marked with aria-checked, not aria-pressed. */
  [data-testid="stButtonGroup"] label {{ display: none; }}
  [data-testid="stButtonGroup"] [role="radiogroup"] {{
      gap: 4px; border: none; background: transparent; }}
  button[data-variant="segmented_control"] {{
      background: transparent !important; border: none !important;
      border-radius: 0 !important; box-shadow: none !important;
      padding: 6px 15px !important; min-height: 0 !important;
      border-bottom: 2px solid transparent !important;
      transition: color .12s, border-color .12s; }}
  button[data-variant="segmented_control"] p {{
      font-size: 0.9rem !important; font-weight: 560 !important;
      color: {T.MUTED} !important; }}
  button[data-variant="segmented_control"]:hover p {{ color: {T.INK} !important; }}
  button[data-variant="segmented_control"][aria-checked="true"] {{
      border-bottom: 2px solid {T.SERIES[0]} !important; }}
  button[data-variant="segmented_control"][aria-checked="true"] p {{
      color: {T.INK} !important; font-weight: 700 !important; }}

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

  /* box-score sheet */
  .ss-wrap {{ overflow: auto; border: 1px solid {T.GRID}; border-radius: 2px;
              background: {T.SURFACE}; margin: 2px 0 2px; }}
  .ss {{ width: 100%; border-collapse: collapse; font-size: 0.84rem;
         font-variant-numeric: tabular-nums; }}
  .ss thead th {{ position: sticky; top: 0; z-index: 2;
                  background: {T.INK}; color: #fff;
                  font-size: 0.64rem; font-weight: 680; letter-spacing: 0.08em;
                  text-transform: uppercase; white-space: nowrap;
                  padding: 8px 11px; text-align: right; }}
  .ss thead th.l {{ text-align: left; }}
  .ss tbody td {{ padding: 6px 11px; text-align: right; color: {T.INK};
                  border-bottom: 1px solid {T.GRID}; white-space: nowrap; }}
  .ss tbody td.l {{ text-align: left; font-weight: 560; }}
  .ss tbody tr:nth-child(even) {{ background: {T.PLANE}; }}
  .ss tbody tr:hover {{ background: #eef3fb; }}
  .ss tbody tr:last-child td {{ border-bottom: none; }}
  .ss .pos {{ color: #1c5cab; font-weight: 620; }}
  .ss .neg {{ color: #a83232; font-weight: 620; }}

  hr {{ border-color: {T.GRID}; }}
  a {{ color: {T.SERIES[0]}; }}
</style>
"""
