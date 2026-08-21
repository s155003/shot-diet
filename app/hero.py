"""Landing hero: what the product is, in the order a stranger needs it.

Structure is problem, method, evidence, consequence. Earlier versions stated the
concept ("scoring split into shot quality and shot making") and readers did not
follow, because a concept gives no reason to believe the two halves can come
apart. Two changes fixed that:

* **Say how it knows.** The page states the counterfactual outright: for every
  shot, what would an average NBA player have scored on that exact shot?
  Without that sentence "his shots were worth 1.45" is a number from nowhere,
  and that was the single largest gap in comprehension.
* **Show it happening.** Gobert outscores Doncic and is the worse shooter. Until
  a reader watches four real numbers do that, the idea sounds like wordplay.

The court is the product's own chart rather than decoration, which is the
written exception to the no-decorative-animation rule in DESIGN.md section 6.2.
Colour is centred on one point per attempt, not league average points per shot:
league average is 1.09, dragged upward by the rim's volume, so centring there
paints nearly the whole floor red and the picture stops meaning anything. Hex
area scales with volume, capped at the 78th percentile; uniform hexes were tried
and produce a solid wall that buries the court lines.
"""
from __future__ import annotations

import json
import unicodedata

import pandas as pd
import streamlit as st

import theme as T
from data_access import PROCESSED

HEIGHT = 646

# The pair the pitch rests on. Gobert scores more per shot and is the worse
# shooter, which is the whole idea in one row.
PAIR = ("Rudy Gobert", "Luka Doncic")


def _example() -> dict:
    """Read the worked example live, so it cannot drift from the data."""
    ps = pd.read_parquet(PROCESSED / "player_season.parquet")
    latest = sorted(ps["SEASON"].astype(str).unique())[-1]   # SEASON is an
    d = ps[ps["SEASON"].astype(str) == latest]               # unordered category
    plain = d["PLAYER_NAME"].map(
        lambda s: "".join(c for c in unicodedata.normalize("NFKD", s)
                          if not unicodedata.combining(c)))
    out = {}
    for key, want in zip(("a", "b"), PAIR):
        row = d[plain == want]
        if row.empty:
            return {}
        r = row.iloc[0]
        out[key] = {"name": r["PLAYER_NAME"], "worth": float(r["xpps"]),
                    "scored": float(r["pps"]), "fga": int(r["fga"])}
    return out


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
  .hero{background:__SURFACE__;border:1px solid rgba(11,11,11,.12);
        border-radius:3px;padding:22px 28px 20px}

  /* The wordmark sits over a dashed rule in the ball colour, echoing the
     three-point line below it, so the identity and the graphic are one idea. */
  .wordmark{font-size:2.3rem;line-height:1;letter-spacing:-.035em;font-weight:720;
            color:__INK__;margin:0}
  .brandrule{height:0;border-top:3px dashed __BALL__;width:98px;margin:10px 0 12px}
  .tag{font-size:1.02rem;line-height:1.3;letter-spacing:-.01em;font-weight:640;
       color:__INK__;margin:0 0 14px;max-width:60ch}

  .step{display:flex;gap:11px;align-items:flex-start;margin:0 0 9px;max-width:82ch}
  .num{flex:0 0 auto;width:17px;height:17px;border-radius:2px;margin-top:2px;
       background:__INK__;color:#fff;font-size:.63rem;font-weight:700;
       display:flex;align-items:center;justify-content:center}
  .step p{margin:0;color:__INK2__;font-size:.91rem;line-height:1.5}
  .step b{color:__INK__;font-weight:640}

  .cols{display:grid;grid-template-columns:minmax(0,49%) minmax(0,51%);
        gap:22px;align-items:start;margin-top:14px}

  .ex{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;
      font-size:.83rem}
  .ex thead th{color:__MUTED__;font-size:.57rem;font-weight:660;line-height:1.25;
               letter-spacing:.06em;text-transform:uppercase;text-align:right;
               padding:0 8px 5px;border-bottom:1px solid __GRID__;white-space:nowrap}
  .ex th.l,.ex td.l{text-align:left}
  .ex td{padding:7px 8px;text-align:right;color:__INK__;white-space:nowrap}
  .ex td.l:first-child{font-weight:640}
  .ex tbody tr+tr td{border-top:1px solid __GRID__}
  .pos{color:#1c5cab;font-weight:660}
  .neg{color:#a83232;font-weight:660}
  .verdict{margin:11px 0 0;color:__INK__;font-size:.89rem;line-height:1.5;
           font-weight:600}
  .why{margin:11px 0 0;color:__INK2__;font-size:.83rem;line-height:1.5;
       padding-left:11px;border-left:2px solid __GRID__}
  .doit{margin-top:15px;padding-top:13px;border-top:1px solid __GRID__}

  svg{display:block;width:100%;height:232px}
  .ccap{color:__MUTED__;font-size:.72rem;line-height:1.45;margin:5px 0 0}
  .ccap b{font-weight:640}

  .line{stroke:__AXIS__;stroke-width:1.5;fill:none}
  .paint{stroke:__GRID__;stroke-width:1.5;fill:none}
  .arc{stroke:__BALL__;stroke-width:3.2;fill:none;stroke-linecap:round;
       stroke-dasharray:11 8}
  .rim{stroke:__BALL__;stroke-width:3.4;stroke-linecap:round}
  .net{stroke:__AXIS__;stroke-width:1.2;fill:none}
  .hex{stroke:__SURFACE__;stroke-width:1}

  /* The mask rect is full width by default, so a stylesheet that never loads
     leaves the court visible rather than erased. Nothing starts at zero. */
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
  <h1 class="wordmark">Shot Diet</h1>
  <div class="brandrule"></div>
  <p class="tag">Is he a good shooter, or does he just get good shots?</p>

  <div class="step"><span class="num">1</span><p>
    <b>The problem.</b> Some players get handed layups. Others have to create
    contested jumpers. A box score counts both the same, so it cannot tell a
    good shooter apart from a player in a good situation.</p></div>

  <div class="step"><span class="num">2</span><p>
    <b>How we test it.</b> For each of 1,087,633 shots we ask one question:
    <b>what would an average NBA player have scored on this exact shot?</b>
    Same spot on the floor, same type of play, same moment in the game. Then we
    compare that to what the player actually scored.</p></div>

  <div class="cols">
    <div>
      <table class="ex">
        <thead><tr><th class="l">Last season</th>
          <th>An average NBA<br>player would score</th>
          <th>He actually<br>scored</th><th class="l"></th></tr></thead>
        <tbody>
          <tr><td class="l">__A_NAME__</td><td>__A_WORTH__</td>
              <td>__A_SCORED__</td><td class="l neg">__A_DIFF__ worse</td></tr>
          <tr><td class="l">__B_NAME__</td><td>__B_WORTH__</td>
              <td>__B_SCORED__</td><td class="l pos">__B_DIFF__ better</td></tr>
        </tbody>
      </table>
      <p class="verdict">__A_FIRST__ scores more per shot. __B_FIRST__ is the
        better shooter. Both are true at the same time.</p>
      <p class="why"><b>Why it matters.</b> Which shots a player gets is
        something a coach can change. How well he shoots them mostly is not.
        This tells a team which half of the problem is worth working on.</p>
    </div>

    <div>
      <div id="court"></div>
      <p class="ccap">Every shot the league took last season, by where it came
        from. Each hexagon is a patch of floor, bigger where more shots are
        taken. <b style="color:#1c5cab">Blue</b> pays more than a point per
        shot, <b style="color:#a83232">red</b> pays less. Dunks pay. The
        mid-range, that red band, does not.</p>
    </div>
  </div>

  <div class="step doit"><span class="num">3</span><p>
    <b>What you get.</b> Type any player's name below for his own split, his
    shot chart, his shooting zone by zone, and which shots he should trade for
    which.</p></div>
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
    ex = _example()
    if ex:
        for k, tag in (("a", "A"), ("b", "B")):
            p = ex[k]
            html = (html
                    .replace("__%s_NAME__" % tag, p["name"])
                    .replace("__%s_FIRST__" % tag, p["name"].split()[0])
                    .replace("__%s_WORTH__" % tag, "%.2f" % p["worth"])
                    .replace("__%s_SCORED__" % tag, "%.2f" % p["scored"])
                    .replace("__%s_DIFF__" % tag,
                             "%.2f" % abs(p["scored"] - p["worth"])))
    for key, val in (
        ("__SURFACE__", T.SURFACE), ("__PLANE__", T.PLANE), ("__INK__", T.INK),
        ("__INK2__", T.INK_2), ("__MUTED__", T.MUTED), ("__GRID__", T.GRID),
        ("__AXIS__", T.AXIS), ("__BALL__", T.SERIES[1]), ("__FONT__", T.FONT),
    ):
        html = html.replace(key, val)
    st.iframe(html, height=height)
