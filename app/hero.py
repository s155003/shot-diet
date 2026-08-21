"""The landing page: a half court, with the product written on it.

The court is not an illustration beside the copy, it is the page. The wordmark
and the pitch sit in the backcourt, the empty floor beyond the arc where no
shots are taken, so the type never fights the data. Below the arc the same
hexagons carry the finding: blue at the rim and in the corners, red through the
mid-range.

Structure of the copy is problem, method, evidence, consequence. Earlier drafts
stated the concept and readers did not follow, because a concept gives no reason
to believe the two halves can come apart. Two things fixed that and must
survive any rewrite:

* **Say how it knows.** For every shot, what would an average NBA player have
  scored on that exact shot? Without that sentence "his shots were worth 1.45"
  is a number from nowhere, and that was the largest gap in comprehension.
* **Show it happening.** Gobert outscores Doncic and is the worse shooter.

Colour is centred on one point per attempt, not on league average points per
shot: league average is 1.09, dragged upward by the rim's volume, so centring
there paints nearly the whole floor red and the picture stops meaning anything.
Hex area scales with volume, capped at the 78th percentile; uniform hexes were
tried and produce a solid wall that buries the court lines.

This is the written exception to the no-decorative-animation rule, recorded in
DESIGN.md section 6.2. The court is the product's own chart, so the striking
element on the page is information. Strip the data out and it becomes
decoration and has to go.
"""
from __future__ import annotations

import json
import unicodedata

import pandas as pd
import streamlit as st

import theme as T
from data_access import PROCESSED

HEIGHT = 1400

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

  /* The court is the stage; the masthead is positioned inside it, in the
     backcourt, where the data never reaches. */
  .stage{position:relative;background:__SURFACE__;
         border:1px solid rgba(11,11,11,.12);border-radius:3px;overflow:hidden}
  .stage svg{display:block;width:100%;height:auto}

  .mast{position:absolute;left:0;right:0;top:4.2%;text-align:center;
        padding:0 24px;pointer-events:none}
  .wordmark{font-size:clamp(2.4rem,5.2vw,4rem);line-height:.96;
            letter-spacing:-.042em;font-weight:730;color:__INK__;margin:0}
  .brandrule{height:0;border-top:3px dashed __BALL__;width:132px;
             margin:14px auto 15px}
  .tag{font-size:clamp(.95rem,1.5vw,1.22rem);line-height:1.32;font-weight:620;
       letter-spacing:-.012em;color:__INK__;margin:0 auto;max-width:34ch}
  .said{margin:13px auto 0;max-width:52ch;color:__INK2__;
        font-size:clamp(.8rem,1.05vw,.95rem);line-height:1.5}

  .courtcap{margin:0 0 18px;color:__MUTED__;font-size:.82rem;line-height:1.5;
            max-width:86ch}
  .courtcap b{font-weight:660}

  /* the explanation, under the court */
  .below{padding:26px 30px 24px}
  .step{display:flex;gap:12px;align-items:flex-start;margin:0 0 11px;max-width:88ch}
  .num{flex:0 0 auto;width:18px;height:18px;border-radius:2px;margin-top:2px;
       background:__INK__;color:#fff;font-size:.64rem;font-weight:700;
       display:flex;align-items:center;justify-content:center}
  .step p{margin:0;color:__INK2__;font-size:.93rem;line-height:1.52}
  .step b{color:__INK__;font-weight:640}

  .cols{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);
        gap:26px;align-items:start;margin-top:6px}
  .ex{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;
      font-size:.85rem}
  .ex thead th{color:__MUTED__;font-size:.58rem;font-weight:660;line-height:1.25;
               letter-spacing:.06em;text-transform:uppercase;text-align:right;
               padding:0 8px 5px;border-bottom:1px solid __GRID__;white-space:nowrap}
  .ex th.l,.ex td.l{text-align:left}
  .ex td{padding:8px;text-align:right;color:__INK__;white-space:nowrap}
  .ex td.l:first-child{font-weight:640}
  .ex tbody tr+tr td{border-top:1px solid __GRID__}
  .pos{color:#1c5cab;font-weight:660}
  .neg{color:#a83232;font-weight:660}
  .verdict{margin:12px 0 0;color:__INK__;font-size:.92rem;line-height:1.5;
           font-weight:620}
  .why{margin:0;color:__INK2__;font-size:.87rem;line-height:1.55;
       padding-left:13px;border-left:2px solid __GRID__}

  .line{stroke:__AXIS__;stroke-width:1.7;fill:none}
  .paint{stroke:__GRID__;stroke-width:1.7;fill:none}
  .arc{stroke:__BALL__;stroke-width:4;fill:none;stroke-linecap:round;
       stroke-dasharray:14 10}
  .rim{stroke:__BALL__;stroke-width:4.2;stroke-linecap:round}
  .net{stroke:__AXIS__;stroke-width:1.4;fill:none}
  .hex{stroke:__SURFACE__;stroke-width:1.1}

  /* The mask rect is full width by default, so a stylesheet that never loads
     leaves the court visible rather than erased. Nothing starts at zero. */
  .wipe{transform-origin:center;animation:wipe 1.05s cubic-bezier(.2,.75,.3,1) .12s both}
  @keyframes wipe{from{transform:scaleX(.02)}to{transform:scaleX(1)}}
  .courtline{opacity:.4;animation:ink .55s ease-out both}
  @keyframes ink{to{opacity:1}}
  .hex{opacity:.22;animation:bloom .45s ease-out both}
  @keyframes bloom{from{opacity:.22;transform:scale(.5)}to{opacity:1;transform:scale(1)}}
  @media (prefers-reduced-motion:reduce){
    .wipe,.courtline,.hex{animation:none!important;opacity:1!important;
                          transform:none!important}
  }
</style>

<div class="stage">
  <div id="court"></div>
  <div class="mast">
    <h1 class="wordmark">Shot Diet</h1>
    <div class="brandrule"></div>
    <p class="tag">Is he a good shooter, or does he just get good shots?</p>
  </div>
</div>

<div class="below">
  <p class="courtcap">Every shot the NBA took last season, laid on the floor it
    came from. Each hexagon is a patch of court, bigger where more shots are
    taken. <b style="color:#1c5cab">Blue</b> pays more than a point a shot,
    <b style="color:#a83232">red</b> pays less. Dunks pay. The mid-range, that
    red band, does not.</p>

  <div class="step"><span class="num">1</span><p>
    <b>The problem.</b> Some players get handed layups. Others have to create
    contested jumpers. A box score counts both the same, so it cannot tell a
    good shooter apart from a player in a good situation.</p></div>

  <div class="step"><span class="num">2</span><p>
    <b>How we test it.</b> For each of 1,087,633 shots we ask one question:
    <b>what would an average NBA player have scored on this exact shot?</b>
    Same spot on the floor, same type of play, same moment in the game. Then we
    compare that with what the player actually scored.</p></div>

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
    </div>
    <div>
      <p class="why"><b>Why it matters.</b> Which shots a player gets is
        something a coach can change. How well he shoots them mostly is not, so
        the split tells a team which half of the problem is worth working on.
        <br><br><b>What you get.</b> Open <b>Players</b> above for any player's
        own split, his shot chart, his shooting zone by zone, and which shots he
        should trade for which. <b>Leaders</b> ranks the league,
        <b>Teams</b> does the same for all thirty, and <b>Findings</b> shows
        the evidence behind it.</p>
    </div>
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
  // The frame extends well above the arc on purpose. Above-the-break threes
  // reach about 27 feet, so the empty floor only starts past that, and the
  // masthead needs a band with no hexagons in it at all.
  const w = 1160, h = 940, ppf = 18.6, hoopY = 828;
  const X = f => w / 2 + f * ppf, Y = f => hoopY - f * ppf;
  const svg = el("svg", { viewBox: "0 0 " + w + " " + h });

  const g = el("g", { class: "courtline" });
  g.appendChild(el("line", { x1: X(-25), y1: Y(-5.25), x2: X(25), y2: Y(-5.25),
                             class: "line" }));
  g.appendChild(el("line", { x1: X(-25), y1: Y(-5.25), x2: X(-25), y2: 0,
                             class: "line" }));
  g.appendChild(el("line", { x1: X(25), y1: Y(-5.25), x2: X(25), y2: 0,
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
      p.style.animationDelay = (0.45 + i * 0.0024) + "s";
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
    d: "M " + X(-0.75) + " " + Y(0) + " L " + X(-0.55) + " " + Y(-2.1) +
       " L " + X(0.55) + " " + Y(-2.1) + " L " + X(0.75) + " " + Y(0) }));
  hoop.appendChild(el("line", { x1: X(-0.75), y1: Y(0), x2: X(0.75), y2: Y(0),
                                class: "rim" }));
  svg.appendChild(hoop);

  document.getElementById("court").appendChild(svg);
})();
</script>
"""


def render(height: int = HEIGHT) -> None:
    """Draw the landing page."""
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
