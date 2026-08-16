"""NBA half-court geometry and hex-binned shot charts for Plotly.

Coordinates are in feet with the rim centre at the origin, matching
LOC_X/10, LOC_Y/10 from the stats.nba.com shot feed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import theme as T

X_MIN, X_MAX = -25.0, 25.0
Y_MIN, Y_MAX = -6.0, 40.0

LINE = dict(color=T.AXIS, width=1.4)


def _arc(cx, cy, r, a0, a1, n=90):
    a = np.linspace(np.radians(a0), np.radians(a1), n)
    return cx + r * np.cos(a), cy + r * np.sin(a)


def court_shapes() -> list[dict]:
    """Static court lines as Plotly shapes."""
    s = []

    def path(xs, ys):
        d = "M " + " L ".join(f"{x:.3f} {y:.3f}" for x, y in zip(xs, ys))
        s.append(dict(type="path", path=d, line=LINE, layer="above"))

    def line(x0, y0, x1, y1):
        s.append(dict(type="line", x0=x0, y0=y0, x1=x1, y1=y1, line=LINE, layer="above"))

    # Baseline and sidelines.
    line(-25, -5.25, 25, -5.25)
    line(-25, -5.25, -25, Y_MAX)
    line(25, -5.25, 25, Y_MAX)

    # Backboard and rim.
    line(-3, -4.0, 3, -4.0)
    s.append(dict(type="circle", x0=-0.75, y0=-0.75, x1=0.75, y1=0.75,
                  line=LINE, layer="above"))
    line(0, -4.0, 0, -0.75)

    # Paint: 16 ft wide, 19 ft from the baseline.
    s.append(dict(type="rect", x0=-8, y0=-5.25, x1=8, y1=13.75, line=LINE, layer="above"))

    # Free-throw circle (dashed on the far side, as painted).
    x, y = _arc(0, 13.75, 6, 0, 180)
    path(x, y)
    x, y = _arc(0, 13.75, 6, 180, 360)
    s.append(dict(type="path",
                  path="M " + " L ".join(f"{a:.3f} {b:.3f}" for a, b in zip(x, y)),
                  line=dict(color=T.AXIS, width=1.2, dash="dot"), layer="above"))

    # Restricted area.
    x, y = _arc(0, 0, 4, 0, 180)
    path(x, y)

    # Three-point line: corners to y = 8.75, then the 23.75 ft arc.
    line(-22, -5.25, -22, 8.75)
    line(22, -5.25, 22, 8.75)
    theta = np.degrees(np.arcsin(8.75 / 23.75))
    x, y = _arc(0, 0, 23.75, theta, 180 - theta)
    path(x, y)

    return s


def blank_court(height: int = 560) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        shapes=court_shapes(),
        height=height,
        paper_bgcolor=T.SURFACE,
        plot_bgcolor=T.SURFACE,
        margin=dict(l=4, r=4, t=40, b=4),
        font=dict(family=T.FONT, size=12, color=T.INK_2),
        hoverlabel=dict(bgcolor=T.SURFACE, bordercolor=T.AXIS,
                        font=dict(family=T.FONT, size=12, color=T.INK)),
        title=dict(text="", font=dict(size=15, color=T.INK)),
        showlegend=False,
    )
    fig.update_xaxes(range=[X_MIN, X_MAX], visible=False,
                     scaleanchor="y", scaleratio=1, constrain="domain")
    fig.update_yaxes(range=[Y_MIN, Y_MAX], visible=False, constrain="domain")
    return fig


# --------------------------------------------------------------------------
# hex binning
# --------------------------------------------------------------------------

def _hex_bin(x: np.ndarray, y: np.ndarray, size: float) -> tuple[np.ndarray, np.ndarray]:
    """Flat-top hex binning: point -> integer axial cell (q, r)."""
    q = (2.0 / 3.0 * x) / size
    r = (-1.0 / 3.0 * x + np.sqrt(3) / 3.0 * y) / size
    # cube rounding
    cx, cz = q, r
    cy = -cx - cz
    rx, ry, rz = np.round(cx), np.round(cy), np.round(cz)
    dx, dy, dz = np.abs(rx - cx), np.abs(ry - cy), np.abs(rz - cz)
    fix_x = (dx > dy) & (dx > dz)
    fix_z = ~fix_x & (dy > dz)
    rx = np.where(fix_x, -ry - rz, rx)
    rz = np.where(fix_z, -rx - ry, rz)
    return rx.astype(int), rz.astype(int)


def _hex_centre(q: np.ndarray, r: np.ndarray, size: float) -> tuple[np.ndarray, np.ndarray]:
    x = size * 1.5 * q
    y = size * (np.sqrt(3) / 2.0 * q + np.sqrt(3) * r)
    return x, y


def hex_shot_chart(shots: pd.DataFrame, league: pd.DataFrame, title: str = "",
                   size: float = 1.7, min_att: int = 4, height: int = 560,
                   plot_px: int = 520) -> go.Figure:
    """Goldsberry-style chart: hex area = volume, hex colour = points vs league.

    Colour is points per attempt in that cell minus the *league's* points per
    attempt in the same cell, so a player is compared against the same shot,
    not against the league average shot.
    """
    fig = blank_court(height)
    if shots.empty:
        return fig

    def binned(d: pd.DataFrame) -> pd.DataFrame:
        q, r = _hex_bin(d["loc_x"].to_numpy(), d["loc_y"].to_numpy(), size)
        g = pd.DataFrame({"q": q, "r": r, "pts": d["points"].to_numpy()})
        return g.groupby(["q", "r"], as_index=False).agg(att=("pts", "size"),
                                                         pps=("pts", "mean"))

    p = binned(shots)
    lg = binned(league).rename(columns={"att": "lg_att", "pps": "lg_pps"})
    m = p.merge(lg, on=["q", "r"], how="left")
    m = m[m["att"] >= min_att].copy()
    if m.empty:
        return fig
    m["lg_pps"] = m["lg_pps"].fillna(league["points"].mean())
    m["diff"] = m["pps"] - m["lg_pps"]

    cx, cy = _hex_centre(m["q"].to_numpy(), m["r"].to_numpy(), size)
    m["x"], m["y"] = cx, cy
    m = m[(m["x"].between(X_MIN, X_MAX)) & (m["y"].between(Y_MIN, Y_MAX))]

    # Marker diameter in px. Volume sets area, so radius scales with sqrt.
    px_per_ft = plot_px / (X_MAX - X_MIN)
    max_px = size * 2.0 * px_per_ft
    freq = m["att"] / m["att"].quantile(0.97)
    sizes = np.clip(np.sqrt(np.clip(freq, 0, 1)), 0.22, 1.0) * max_px

    # Clamp the colour range. A cell with four attempts can swing a full point
    # per shot, and letting that set the scale washes out every real signal.
    lim = float(np.clip(np.nanpercentile(np.abs(m["diff"]), 85), 0.25, 0.60))
    fig.add_trace(go.Scatter(
        x=m["x"], y=m["y"], mode="markers",
        marker=dict(
            symbol="hexagon2", size=sizes,
            color=m["diff"], colorscale=T.DIVERGING, cmin=-lim, cmax=lim,
            line=dict(width=0.6, color=T.SURFACE),
            colorbar=dict(
                title=dict(text="Pts per shot<br>vs league<br>(same spot)",
                           font=dict(size=11, color=T.INK_2)),
                thickness=10, len=0.55, x=1.0, tickfont=dict(size=10, color=T.MUTED),
                outlinewidth=0),
        ),
        customdata=np.stack([m["att"], m["pps"], m["lg_pps"], m["diff"]], axis=-1),
        hovertemplate=("%{customdata[0]:.0f} attempts<br>"
                       "%{customdata[1]:.2f} pts/shot<br>"
                       "league here %{customdata[2]:.2f}<br>"
                       "<b>%{customdata[3]:+.2f}</b><extra></extra>"),
    ))
    if title:
        fig.update_layout(title=dict(text=title))
    return fig
