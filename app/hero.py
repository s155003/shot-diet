"""Landing hero: a half-court drawn from real shot data.

The one idea: a half-court that draws its own three-point line, then fills with
every shot of the season, sized by how often the league shoots from there and
coloured by what those shots are worth.

That is what keeps it off the banned list. Decorative animation reads as
generated; this is the product's own chart, so the striking element on the page
is real information rather than an effect.

Two things worth knowing before changing it:

* Colour is centred on **one point per attempt**, not on league average points
  per shot. League average is 1.09, dragged upward by the rim's enormous volume,
  so centring there paints almost the whole floor red and the picture stops
  meaning anything. One point per shot is a natural, explainable midpoint.
* Hex area scales with volume, capped at the 78th percentile. Uniform hexes were
  tried and produce a solid wall of colour that buries the court lines.
"""
from __future__ import annotations

import json

import streamlit as st

import theme as T
from data_access import PROCESSED

HEIGHT = 442


def _bins() -> str:
    path = PROCESSED / "hero_bins.json"
    if not path.exists():
        return json.dumps({"n_shots": 0, "bins": []})
    return path.read_text(encoding="utf-8")


_TEMPLATE = r"""
<style>
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:__PLANE__;
            font-family:__FONT__;-webkit-font-smoothing:antialiased}
  .hero{background:__SURFACE__;border:1px solid rgba(11,11,11,.12);border-radius:3px;
        display:grid;grid-template-columns:minmax(0,38%) minmax(0,62%);
        align-items:center;gap:22px;padding:20px 28px}
  .kick{font-size:.66rem;letter-spacing:.15em;text-transform:uppercase;
        color:__MUTED__;font-weight:620;margin:0 0 11px}
  /* The wordmark sits over a dashed rule in the ball colour, echoing the
     three-point line beside it, so the identity and the graphic are the same
     idea rather than two unrelated marks. */
  .wordmark{font-size:2.45rem;line-height:1;letter-spacing:-.035em;font-weight:720;
            color:__INK__;margin:0}
  .brandrule{height:0;border-top:3px dashed __BALL__;width:104px;margin:11px 0 13px}
  .tag{font-size:1.06rem;line-height:1.32;letter-spacing:-.012em;font-weight:640;
       color:__INK__;margin:0 0 11px;max-width:28ch}
  .sub{color:__INK2__;font-size:.92rem;line-height:1.56;max-width:48ch;margin:0}
  .sub b{color:__INK__;font-weight:640}
  .sub2{color:__MUTED__;font-size:.76rem;margin:14px 0 0;letter-spacing:.02em}
  .courtwrap{display:flex;flex-direction:column;gap:6px}
  .ccap{color:__MUTED__;font-size:.73rem;line-height:1.5;margin:0;max-width:60ch}
  .ccap b{font-weight:640}
  /* Fixed height, not auto: the iframe height is a constant, so a width-scaling
     SVG would either clip on a wide viewport or leave dead space on a narrow
     one. preserveAspectRatio letterboxes inside this box instead. */
  svg{display:block;width:100%;height:300px}

  .line{stroke:__AXIS__;stroke-width:1.5;fill:none}
  .paint{stroke:__GRID__;stroke-width:1.5;fill:none}
  .arc{stroke:__BALL__;stroke-width:3.4;fill:none;stroke-linecap:round;
       stroke-dasharray:12 9}
  .rim{stroke:__BALL__;stroke-width:3.6;stroke-linecap:round}
  .net{stroke:__AXIS__;stroke-width:1.2;fill:none}
  .hex{stroke:__SURFACE__;stroke-width:1}

  /* The mask rect is full width by default, so if this stylesheet never loads
     the arc stays visible rather than erased. Nothing animates from zero. */
  .wipe{transform-origin:center;animation:wipe 1s cubic-bezier(.2,.75,.3,1) .1s both}
  @keyframes wipe{from{transform:scaleX(.02)}to{transform:scaleX(1)}}
  .courtline{opacity:.4;animation:ink .5s ease-out both}
  @keyframes ink{to{opacity:1}}
  .hex{opacity:.22;animation:bloom .45s ease-out both}
  @keyframes bloom{from{opacity:.22;transform:scale(.5)}to{opacity:1;transform:scale(1)}}
  @media (prefers-reduced-motion:reduce){
    .wipe,.courtline,.hex{animation:none!important;opacity:1!important;
                          transform:none!important}
  }
</style>

<div class="hero">
  <div>
    <h1 class="wordmark">Shot Diet</h1>
    <div class="brandrule"></div>
    <p class="tag">Is he a good shooter, or does he just get good shots?</p>
    <p class="sub">Two players can score exactly the same while one takes layups
      and the other takes contested jumpers. A box score cannot tell them apart.
      <b>Type any NBA player's name</b> and Shot Diet splits his scoring in two:
      how good his shots were, and how well he made them. You get a shot chart,
      his shooting zone by zone, and what to change about his shot mix.</p>
    <p class="sub2">1,087,633 shots &middot; five seasons &middot; every player and team</p>
  </div>
  <div class="courtwrap">
    <div id="court"></div>
    <p class="ccap">Where the league shoots from, and what it gets back. Each
      hexagon is a patch of floor, sized by how often shots come from there.
      <b style="color:#1c5cab">Blue</b> returns more than a point per attempt,
      <b style="color:#a83232">red</b> less. The mid-range is the red band.</p>
  </div>
</div>

<script>
const DATA = __BINS__;
const NS = "http://www.w3.org/2000/svg";
const el = (n, a = {}) => { const e = document.createElementNS(NS, n);
  for (const k in a) e.setAttribute(k, a[k]); return e; };
const R3 = 23.75, CX = 22, CY = 8.75, CENTRE = 1.00, SPAN = 0.34;

function colour(pps) {
  let v = Math.max(-1, Math.min(1, (pps - CENTRE) / SPAN));
  const s = [[-1,[168,50,50]],[-.42,[206,124,124]],[0,[236,234,229]],
             [.42,[92,150,214]],[1,[16,66,129]]];
  for (let i = 0; i < s.length - 1; i++) {
    const [a, ca] = s[i], [b, cb] = s[i + 1];
    if (v <= b) { const t = (v - a) / (b - a);
      return "rgb(" + ca.map((c, j) => Math.round(c + (cb[j] - c) * t)).join(",") + ")"; }
  }
  return "rgb(16,66,129)";
}

(function build() {
  const w = 748, h = 430, ppf = 12.9, hoopY = 358;
  const X = f => w / 2 + f * ppf, Y = f => hoopY - f * ppf;
  const svg = el("svg", { viewBox: "0 0 " + w + " " + h });

  const g = el("g", { class: "courtline" });
  g.appendChild(el("line", { x1: X(-25), y1: Y(-5.25), x2: X(25), y2: Y(-5.25),
                             class: "line" }));
  g.appendChild(el("rect", { x: X(-8), y: Y(13.75), width: 16 * ppf,
                             height: 19 * ppf, class: "paint" }));
  const ft = [];
  for (let a = 0; a <= 180; a += 4) {
    const r = a * Math.PI / 180;
    ft.push(X(Math.cos(r) * 6).toFixed(1) + " " +
            Y(13.75 + Math.sin(r) * 6).toFixed(1));
  }
  g.appendChild(el("path", { d: "M " + ft.join(" L "), class: "paint" }));
  svg.appendChild(g);

  const ns = DATA.bins.map(b => b.n).sort((a, b) => a - b);
  const cap = ns[Math.floor(ns.length * 0.78)] || 1;
  const R = ppf * 1.55;
  const hexes = el("g");
  DATA.bins.slice().sort((a, b) => Math.hypot(a.x, a.y) - Math.hypot(b.x, b.y))
    .forEach((b, i) => {
      const k = Math.max(0.42, Math.min(1, Math.sqrt(b.n / cap)));
      const cx = X(b.x), cy = Y(b.y), r = R * k, pts = [];
      for (let a = 0; a < 6; a++) {
        const t = Math.PI / 180 * (60 * a);
        pts.push((cx + r * Math.cos(t)).toFixed(1) + "," +
                 (cy + r * Math.sin(t)).toFixed(1));
      }
      const p = el("polygon", { points: pts.join(" "), fill: colour(b.p),
                                class: "hex" });
      p.style.transformOrigin = cx.toFixed(1) + "px " + cy.toFixed(1) + "px";
      p.style.animationDelay = (0.42 + i * 0.0022) + "s";
      hexes.appendChild(p);
    });
  svg.appendChild(hexes);

  const th = Math.asin(CY / R3);
  const d = ["M " + X(-CX) + " " + Y(-5.25), "L " + X(-CX) + " " + Y(CY)];
  for (let a = Math.PI - th; a >= th; a -= 0.02)
    d.push("L " + X(Math.cos(a) * R3).toFixed(1) + " " +
                  Y(Math.sin(a) * R3).toFixed(1));
  d.push("L " + X(CX) + " " + Y(-5.25));
  const mask = el("mask", { id: "wipe" });
  mask.appendChild(el("rect", { x: 0, y: 0, width: w, height: h, fill: "#fff",
                                class: "wipe" }));
  svg.appendChild(mask);
  const wrap = el("g", { mask: "url(#wipe)" });
  wrap.appendChild(el("path", { d: d.join(" "), class: "arc" }));
  svg.appendChild(wrap);

  // hoop last, so the dense rim bins never bury it
  const hoop = el("g", { class: "courtline" });
  hoop.appendChild(el("line", { x1: X(-3), y1: Y(-4.1), x2: X(3), y2: Y(-4.1),
                                class: "line" }));
  hoop.appendChild(el("path", { class: "net",
    d: "M " + X(-0.75) + " " + Y(0) + " L " + X(-0.55) + " " + Y(-1.9) +
       " L " + X(0.55) + " " + Y(-1.9) + " L " + X(0.75) + " " + Y(0) }));
  hoop.appendChild(el("line", { x1: X(-0.75), y1: Y(0), x2: X(0.75), y2: Y(0),
                                class: "rim" }));
  svg.appendChild(hoop);

  document.getElementById("court").appendChild(svg);
})();
</script>
"""


def render(height: int = HEIGHT) -> None:
    """Draw the landing hero."""
    html = _TEMPLATE.replace("__BINS__", _bins())
    for key, val in (
        ("__SURFACE__", T.SURFACE), ("__PLANE__", T.PLANE), ("__INK__", T.INK),
        ("__INK2__", T.INK_2), ("__MUTED__", T.MUTED), ("__GRID__", T.GRID),
        ("__AXIS__", T.AXIS), ("__BALL__", T.SERIES[1]), ("__FONT__", T.FONT),
    ):
        html = html.replace(key, val)
    st.iframe(html, height=height)
