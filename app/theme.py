"""Chart palette and shared Plotly styling.

The app commits to a single light surface, so every colour below is validated
against #fcfcfb. Categorical slots are used in fixed order and never cycled.
"""
from __future__ import annotations

SURFACE = "#fcfcfb"
PLANE = "#f9f9f7"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# Categorical slots 1-3 (validated all-pairs, light: worst CVD dE 9.2).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SELECTION = SERIES[0]   # blue  - shot selection
MAKING = SERIES[1]      # orange - shot making

# Diverging: blue (above average) <-> red (below average), neutral grey middle.
DIV_POS = "#2a78d6"
DIV_NEG = "#d03b3b"
DIV_MID = "#f0efec"
DIVERGING = [[0.0, "#8f1f1f"], [0.25, DIV_NEG], [0.5, DIV_MID],
             [0.75, DIV_POS], [1.0, "#104281"]]

# Sequential blue, 100 -> 700.
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

GOOD = "#0ca30c"
CRITICAL = "#d03b3b"

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def style(fig, height: int = 420, showlegend: bool = True, ytitle: str = "",
          xtitle: str = ""):
    """Apply the recessive-chrome house style to a Plotly figure."""
    fig.update_layout(
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=13, color=INK_2),
        margin=dict(l=8, r=8, t=36, b=8),
        showlegend=showlegend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(color=INK_2)),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=AXIS,
                        font=dict(family=FONT, size=12, color=INK)),
        # An empty text is required: a title dict carrying only a font makes
        # Plotly render the string "undefined" in the corner of the chart.
        title=dict(text="", font=dict(size=15, color=INK)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=AXIS,
                     ticks="outside", tickcolor=AXIS, tickfont=dict(color=MUTED),
                     title=dict(text=xtitle, font=dict(color=INK_2)))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=AXIS,
                     tickfont=dict(color=MUTED),
                     title=dict(text=ytitle, font=dict(color=INK_2)))
    return fig
