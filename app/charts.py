"""Chart builders shared across the dashboard pages."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import theme as T


def reliability_bars(sh: pd.DataFrame, yoy: pd.DataFrame) -> go.Figure:
    """Two reliability measures for the two components, as grouped bars."""
    order = ["selection", "making"]
    label = {"selection": "Shot selection", "making": "Shot making"}
    sh_v = sh.set_index("metric")["spearman_brown_r"]
    yoy_v = yoy.set_index("metric")["yoy_r"]

    fig = go.Figure()
    for name, vals, color in (
        ("Within season (split-half)", [sh_v[m] for m in order], T.SERIES[0]),
        ("Season to season", [yoy_v[m] for m in order], T.SERIES[1]),
    ):
        fig.add_trace(go.Bar(
            x=[label[m] for m in order], y=vals, name=name,
            marker=dict(color=color, line=dict(width=2, color=T.SURFACE)),
            text=[f"{v:.2f}" for v in vals], textposition="outside",
            textfont=dict(color=T.INK_2, size=13),
            hovertemplate="%{x}<br>" + name + ": r = %{y:.3f}<extra></extra>",
        ))
    fig.update_layout(barmode="group", bargap=0.45, bargroupgap=0.08,
                      yaxis=dict(range=[0, 1.12], tickformat=".1f"))
    return T.style(fig, height=380, ytitle="Correlation with itself (r)")


def stabilization_curve(curve: pd.DataFrame, ks: dict) -> go.Figure:
    """Measured reliability by sample size, with the fitted r = n/(n+k) curve."""
    fig = go.Figure()
    colors = {"selection": T.SERIES[0], "making": T.SERIES[1]}
    label = {"selection": "Shot selection", "making": "Shot making"}
    grid = np.linspace(5, 1400, 300)

    for metric in ("selection", "making"):
        c = curve[curve["metric"] == metric]
        k = ks[metric]
        fig.add_trace(go.Scatter(
            x=grid, y=grid / (grid + k), mode="lines", name=label[metric],
            line=dict(color=colors[metric], width=2),
            hovertemplate=label[metric] + "<br>%{x:.0f} attempts<br>"
                          "reliability %{y:.2f}<extra></extra>"))
        fig.add_trace(go.Scatter(
            x=c["mean_attempts"], y=c["reliability"], mode="markers",
            name=label[metric] + " (measured)", showlegend=False,
            marker=dict(color=colors[metric], size=9,
                        line=dict(width=2, color=T.SURFACE)),
            hovertemplate="measured: %{x:.0f} attempts, r = %{y:.2f}<extra></extra>"))
        fig.add_vline(x=k, line=dict(color=colors[metric], width=1, dash="dot"))
        fig.add_annotation(x=k, y=0.5, text=f"<b>{k:.0f}</b> attempts",
                           showarrow=False, yshift=16, xshift=6, xanchor="left",
                           font=dict(color=colors[metric], size=12))

    fig.add_hline(y=0.5, line=dict(color=T.AXIS, width=1))
    fig.add_annotation(x=1400, y=0.5, text="half signal, half noise", showarrow=False,
                       yshift=-12, xanchor="right", font=dict(color=T.MUTED, size=11))
    fig.update_layout(yaxis=dict(range=[0, 1.02]))
    return T.style(fig, height=400, xtitle="Field goal attempts",
                   ytitle="Reliability")


def selection_vs_making(ps: pd.DataFrame, highlight: list[str] | None = None,
                        season: str = "") -> go.Figure:
    """The quadrant chart: who gets good shots vs who makes hard ones."""
    d = ps.copy()
    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color=T.AXIS, width=1))
    fig.add_hline(y=0, line=dict(color=T.AXIS, width=1))

    fig.add_trace(go.Scatter(
        x=d["selection_p100"], y=d["making_p100"], mode="markers",
        name="Players",
        marker=dict(size=np.clip(d["fga"] / 90, 6, 22), color=d["total_p100"],
                    colorscale=T.DIVERGING, cmin=-25, cmax=25,
                    line=dict(width=1, color=T.SURFACE), opacity=0.9,
                    colorbar=dict(title=dict(text="Total pts<br>per 100",
                                             font=dict(size=11, color=T.INK_2)),
                                  thickness=10, len=0.5, tickfont=dict(size=10,
                                                                       color=T.MUTED),
                                  outlinewidth=0)),
        customdata=np.stack([d["PLAYER_NAME"], d["team"], d["fga"], d["pps"]], axis=-1),
        hovertemplate=("<b>%{customdata[0]}</b> (%{customdata[1]})<br>"
                       "%{customdata[2]:.0f} FGA, %{customdata[3]:.2f} pts/shot<br>"
                       "selection %{x:+.1f} · making %{y:+.1f}<extra></extra>"),
    ))

    if highlight:
        h = d[d["PLAYER_NAME"].isin(highlight)]
        # Push each label away from the busy centre so names clear their markers.
        mid = d["selection_p100"].median()
        pos = ["middle left" if v > mid else "middle right"
               for v in h["selection_p100"]]
        fig.add_trace(go.Scatter(
            x=h["selection_p100"], y=h["making_p100"], mode="markers+text",
            text=[f"{n}  " if p == "middle left" else f"  {n}"
                  for n, p in zip(h["PLAYER_NAME"], pos)],
            textposition=pos, showlegend=False,
            textfont=dict(color=T.INK, size=11),
            marker=dict(size=13, color="rgba(0,0,0,0)",
                        line=dict(width=2, color=T.INK)),
            hoverinfo="skip"))
        pad = (d["selection_p100"].max() - d["selection_p100"].min()) * 0.16
        fig.update_xaxes(range=[d["selection_p100"].min() - pad,
                                d["selection_p100"].max() + pad])

    # Paper coordinates run 0-1, so the corners are (0.02, 0.98), not (-1, 1).
    for x, y, txt in ((0.985, 0.985, "Easy shots,<br>makes them"),
                      (0.015, 0.985, "Hard shots,<br>makes them"),
                      (0.985, 0.015, "Easy shots,<br>misses them"),
                      (0.015, 0.015, "Hard shots,<br>misses them")):
        right = x > 0.5
        fig.add_annotation(x=x, y=y, xref="paper", yref="paper",
                           xanchor="right" if right else "left",
                           yanchor="top" if y > 0.5 else "bottom",
                           text=txt, showarrow=False,
                           font=dict(color=T.MUTED, size=11),
                           align="right" if right else "left")

    return T.style(fig, height=520, showlegend=False,
                   xtitle="Shot selection (points per 100 from the diet)",
                   ytitle="Shot making (points per 100 above expectation)")


def zone_prescription(det: pd.DataFrame, zone_order: list[str]) -> go.Figure:
    """Current vs prescribed share of attempts, by zone.

    Ordered by distance from the rim rather than by volume, so the chart reads
    the way a coach describes a shot diet.
    """
    d = det.set_index("zone").reindex(zone_order[::-1]).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=d["zone"], x=d["share"] * 100, orientation="h", name="Current diet",
        marker=dict(color=T.SERIES[0], line=dict(width=2, color=T.SURFACE)),
        hovertemplate="%{y}<br>current: %{x:.1f}% of attempts<extra></extra>"))
    fig.add_trace(go.Bar(
        y=d["zone"], x=d["new_share"] * 100, orientation="h", name="Prescribed diet",
        marker=dict(color=T.SERIES[1], line=dict(width=2, color=T.SURFACE)),
        hovertemplate="%{y}<br>prescribed: %{x:.1f}% of attempts<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
    fig.update_yaxes(showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=T.GRID)
    return T.style(fig, height=380, xtitle="Share of the player's attempts (%)")


def backtest_dots(bts: pd.DataFrame) -> go.Figure:
    """Paired out-of-sample comparisons with bootstrap CIs."""
    d = bts.iloc[::-1].reset_index(drop=True)
    decisive = (d["ci_low"] > 0) | (d["ci_high"] < 0)
    colors = [T.SERIES[0] if s else T.MUTED for s in decisive]

    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color=T.AXIS, width=1.5))
    for i, r in d.iterrows():
        fig.add_shape(type="line", x0=r["ci_low"], x1=r["ci_high"], y0=i, y1=i,
                      line=dict(color=colors[i], width=2))
    fig.add_trace(go.Scatter(
        x=d["mean_p100"], y=list(range(len(d))), mode="markers",
        marker=dict(size=13, color=colors, line=dict(width=2, color=T.SURFACE)),
        customdata=np.stack([d["ci_low"], d["ci_high"], d["pct_positive"]], axis=-1),
        hovertemplate=("%{y}<br><b>%{x:+.2f}</b> pts per 100<br>"
                       "95%% CI %{customdata[0]:+.2f} to %{customdata[1]:+.2f}<br>"
                       "positive for %{customdata[2]:.0f}%% of players<extra></extra>"),
        showlegend=False))
    fig.update_yaxes(tickmode="array", tickvals=list(range(len(d))),
                     ticktext=d["comparison"], showgrid=False,
                     tickfont=dict(color=T.INK_2, size=12))
    fig.update_xaxes(showgrid=True, gridcolor=T.GRID)
    fig = T.style(fig, height=320, showlegend=False,
                  xtitle="Points per 100 shots gained next season")
    # The category labels are long; give them room rather than truncating.
    fig.update_layout(margin=dict(l=8, r=24, t=20, b=44),
                      yaxis=dict(range=[-0.6, len(d) - 0.4]))
    return fig


def calibration_plot(cal: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect calibration",
                             line=dict(color=T.AXIS, width=1.5, dash="dash"),
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=cal["pred"], y=cal["obs"], mode="markers", name="xPPS-full model",
        marker=dict(size=10, color=T.SERIES[0], line=dict(width=2, color=T.SURFACE)),
        customdata=cal["n"],
        hovertemplate=("predicted %{x:.3f}<br>observed %{y:.3f}<br>"
                       "%{customdata:,.0f} shots<extra></extra>")))
    lo = float(min(cal["pred"].min(), cal["obs"].min())) - 0.03
    hi = float(max(cal["pred"].max(), cal["obs"].max())) + 0.03
    fig.update_xaxes(range=[lo, hi], showgrid=True, gridcolor=T.GRID)
    fig.update_yaxes(range=[lo, hi])
    return T.style(fig, height=380, xtitle="Predicted make probability",
                   ytitle="Observed make rate")


def team_scatter(ts: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color=T.AXIS, width=1))
    fig.add_hline(y=0, line=dict(color=T.AXIS, width=1))
    fig.add_trace(go.Scatter(
        x=ts["selection_p100"], y=ts["making_p100"], mode="markers+text",
        text=ts["team_abbrev"], textposition="middle center",
        textfont=dict(color=T.SURFACE, size=9, family=T.FONT),
        marker=dict(size=26, color=ts["total_p100"], colorscale=T.DIVERGING,
                    cmin=-7, cmax=7, line=dict(width=2, color=T.SURFACE),
                    colorbar=dict(title=dict(text="Total pts<br>per 100",
                                             font=dict(size=11, color=T.INK_2)),
                                  thickness=10, len=0.5,
                                  tickfont=dict(size=10, color=T.MUTED), outlinewidth=0)),
        customdata=np.stack([ts["pps"], ts["fg3a_rate"] * 100], axis=-1),
        hovertemplate=("<b>%{text}</b><br>%{customdata[0]:.3f} pts/shot<br>"
                       "%{customdata[1]:.0f}%% of shots are threes<br>"
                       "selection %{x:+.2f} · making %{y:+.2f}<extra></extra>"),
        showlegend=False))
    # Pad both axes so bubbles at the extremes are not clipped by the frame.
    for col, upd in (("selection_p100", fig.update_xaxes),
                     ("making_p100", fig.update_yaxes)):
        lo, hi = float(ts[col].min()), float(ts[col].max())
        pad = (hi - lo) * 0.12
        upd(range=[lo - pad, hi + pad])
    return T.style(fig, height=560, showlegend=False,
                   xtitle="Shot selection (points per 100 from the diet)",
                   ytitle="Shot making (points per 100 above expectation)")
