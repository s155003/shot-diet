"""Animated drive-and-dunk banner for the landing page.

The figures are original silhouettes, not NBA footage or any real player's
likeness. The scene is a side elevation of the same hoop the shot charts use,
the dot cloud is drawn from the restricted-area attempt distribution, and the
caption numbers come out of data/processed/, so the banner demonstrates the
dataset rather than decorating the page.

Rigging notes, because SVG limb animation has two easy traps:

  * Every joint group is authored with its pivot written out explicitly as
    `transform-box: view-box; transform-origin: <jx>px <jy>px`. The default
    `fill-box` pivots on each group's own bounding box, which is nowhere near
    the joint, and the figure comes apart the moment anything rotates.
  * The rig is positioned only through CSS `transform`. A `transform` attribute
    on the same element is overridden wholesale by the CSS one rather than
    combined with it, so mixing the two silently loses the base offset.

Motion is sequenced in JavaScript by toggling state classes rather than through
one long keyframe track, which keeps each pose independently tunable. It replays
when scrolled back into view and collapses to a static finished pose under
prefers-reduced-motion.
"""
from __future__ import annotations

import streamlit.components.v1 as components

import theme as T

HEIGHT = 300

# Skeleton, authored standing with the feet on the floor line (y = 212).
# Shoulders 120, hips 158, knees 186, ankles 212.
_TEMPLATE = r"""
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: __PLANE__; }
  .wrap { font-family: __FONT__; background: __SURFACE__;
          border: 1px solid rgba(11,11,11,0.12); border-radius: 3px;
          overflow: hidden; position: relative; }
  /* Fixed height, not auto: the iframe height is a constant, so letting the
     SVG scale with width would overflow and clip on a wide viewport.
     preserveAspectRatio="meet" letterboxes inside this box instead. */
  .stage { display: block; width: 100%; height: 224px; }
  .cap { padding: 11px 18px 13px; border-top: 1px solid __GRID__; }
  .cap b { color: __INK__; font-size: 0.95rem; font-weight: 650; }
  .cap span { color: __MUTED__; font-size: 0.82rem; line-height: 1.5; }
  .replay { position: absolute; top: 10px; right: 12px; background: __SURFACE__;
            color: __MUTED__; border: 1px solid __GRID__; border-radius: 3px;
            font-family: inherit; font-size: 0.7rem; letter-spacing: 0.05em;
            text-transform: uppercase; padding: 5px 10px; cursor: pointer; }
  .replay:hover { color: __INK2__; border-color: __AXIS__; }

  .floor { stroke: __AXIS__; stroke-width: 1.6; }
  .arc   { stroke: __GRID__; stroke-width: 1.6; stroke-dasharray: 4 5; }
  .lbl   { fill: __MUTED__; font-size: 12px; font-family: __FONT__; }
  .skin  { fill: __INK__; }
  .kit   { fill: __BLUE__; }
  .dfnd  { fill: __MUTED__; }
  .ballc { fill: __ORANGE__; }
  .seam  { stroke: rgba(255,255,255,.75); stroke-width: 1.1; fill: none; }

  .dot { fill: __BLUE__; opacity: 0; }
  .banner.go .dot { animation: pop .45s ease-out forwards; }
  @keyframes pop { from { opacity:0 } to { opacity:.28 } }

  /* ---- joints: pivot written out in view-box units ---- */
  .j { transform-box: view-box; }
  #thighL { transform-origin: -8px  158px; }
  #thighR { transform-origin:  8px  158px; }
  #shinL  { transform-origin: -8px  186px; }
  #shinR  { transform-origin:  8px  186px; }
  #upperL { transform-origin: -14px 120px; }
  #upperR { transform-origin:  14px 120px; }
  #foreL  { transform-origin: -14px 152px; }
  #foreR  { transform-origin:  14px 152px; }
  #trunk  { transform-origin:  0px  158px; }
  #dArmL  { transform-origin: -13px 120px; }
  #dArmR  { transform-origin:  13px 120px; }

  /* ================= run cycle ================= */
  .banner.run #thighL { animation: thA .44s linear infinite; }
  .banner.run #thighR { animation: thB .44s linear infinite; }
  .banner.run #shinL  { animation: shA .44s linear infinite; }
  .banner.run #shinR  { animation: shB .44s linear infinite; }
  .banner.run #upperL { animation: arA .44s linear infinite; }
  .banner.run #upperR { animation: arB .44s linear infinite; }
  .banner.run #foreL  { animation: fbend .44s linear infinite; }
  .banner.run #foreR  { animation: fbend .44s linear infinite; }
  .banner.run #trunk  { animation: lean .44s linear infinite; }

  @keyframes thA { 0%{transform:rotate(38deg)} 50%{transform:rotate(-34deg)} 100%{transform:rotate(38deg)} }
  @keyframes thB { 0%{transform:rotate(-34deg)} 50%{transform:rotate(38deg)} 100%{transform:rotate(-34deg)} }
  @keyframes shA { 0%{transform:rotate(-8deg)} 25%{transform:rotate(-64deg)} 50%{transform:rotate(-4deg)} 75%{transform:rotate(-22deg)} 100%{transform:rotate(-8deg)} }
  @keyframes shB { 0%{transform:rotate(-4deg)} 25%{transform:rotate(-22deg)} 50%{transform:rotate(-8deg)} 75%{transform:rotate(-64deg)} 100%{transform:rotate(-4deg)} }
  @keyframes arA { 0%{transform:rotate(-38deg)} 50%{transform:rotate(30deg)} 100%{transform:rotate(-38deg)} }
  @keyframes arB { 0%{transform:rotate(30deg)} 50%{transform:rotate(-38deg)} 100%{transform:rotate(30deg)} }
  @keyframes fbend { 0%{transform:rotate(-28deg)} 50%{transform:rotate(-46deg)} 100%{transform:rotate(-28deg)} }
  @keyframes lean { 0%{transform:rotate(-7deg) translateY(0)} 50%{transform:rotate(-7deg) translateY(2.5px)} 100%{transform:rotate(-7deg) translateY(0)} }

  .banner.run #ball { animation: dribble .44s cubic-bezier(.35,0,.7,1) infinite; }
  @keyframes dribble { 0%{transform:translate(0,0)} 50%{transform:translate(10px,20px)} 100%{transform:translate(0,0)} }

  /* ================= gather ================= */
  .banner.gather #thighL { transform: rotate(-40deg); }
  .banner.gather #thighR { transform: rotate(26deg); }
  .banner.gather #shinL  { transform: rotate(62deg); }
  .banner.gather #shinR  { transform: rotate(-48deg); }
  .banner.gather #upperL { transform: rotate(-58deg); }
  .banner.gather #upperR { transform: rotate(-34deg); }
  .banner.gather #foreL  { transform: rotate(-40deg); }
  .banner.gather #foreR  { transform: rotate(-46deg); }
  .banner.gather #trunk  { transform: rotate(-14deg) translateY(7px); }
  .banner.gather #ball   { transform: translate(-2px,-26px); }

  /* ================= rise: knees tucked, right arm cocked overhead =========
     A thigh hanging straight down needs roughly +70deg to bring the knee up to
     horizontal; small angles just swing the leg forward and read as a stumble. */
  .banner.rise #thighL, .banner.dunk #thighL { transform: rotate(72deg); }
  .banner.rise #thighR, .banner.dunk #thighR { transform: rotate(-32deg); }
  .banner.rise #shinL,  .banner.dunk #shinL  { transform: rotate(-74deg); }
  .banner.rise #shinR,  .banner.dunk #shinR  { transform: rotate(-54deg); }
  .banner.rise #upperL, .banner.dunk #upperL { transform: rotate(-52deg); }
  .banner.rise #foreL,  .banner.dunk #foreL  { transform: rotate(-34deg); }
  .banner.rise #trunk,  .banner.dunk #trunk  { transform: rotate(-4deg); }
  .banner.rise #upperR { transform: rotate(154deg); }
  .banner.rise #foreR  { transform: rotate(8deg); }
  .banner.rise #ball   { transform: translate(15px,-124px); }

  /* ================= dunk: arm snaps down to the rim =======================
     42deg puts the extended arm's hand exactly on the rim centre from the apex
     position; see the geometry note in the module docstring. */
  .banner.dunk #upperR { transform: rotate(42deg); }
  .banner.dunk #foreR  { transform: rotate(0deg); }
  .banner.dunk #ball   { transform: translate(26px,-24px); }

  /* ================= fall ================= */
  .banner.fall #upperR { transform: rotate(84deg); }
  .banner.fall #foreR  { transform: rotate(-30deg); }
  .banner.fall #upperL { transform: rotate(-64deg); }
  .banner.fall #foreL  { transform: rotate(-24deg); }
  .banner.fall #thighL { transform: rotate(30deg); }
  .banner.fall #thighR { transform: rotate(-24deg); }
  .banner.fall #shinL  { transform: rotate(-34deg); }
  .banner.fall #shinR  { transform: rotate(-16deg); }
  .banner.fall #ball   { transform: translate(30px,26px); }

  /* ================= land ================= */
  .banner.land #thighL { transform: rotate(-24deg); }
  .banner.land #thighR { transform: rotate(18deg); }
  .banner.land #shinL  { transform: rotate(38deg); }
  .banner.land #shinR  { transform: rotate(-30deg); }
  .banner.land #upperL { transform: rotate(-44deg); }
  .banner.land #upperR { transform: rotate(38deg); }
  .banner.land #foreL  { transform: rotate(-34deg); }
  .banner.land #foreR  { transform: rotate(-30deg); }
  .banner.land #trunk  { transform: rotate(-9deg) translateY(8px); }
  .banner.land #ball   { transform: translate(34px,22px); }

  .banner.gather .j, .banner.rise .j, .banner.fall .j, .banner.land .j
      { transition: transform .17s ease-out; }
  .banner.dunk .j { transition: transform .11s cubic-bezier(.5,0,.75,0); }
  .banner.gather #ball, .banner.rise #ball { transition: transform .3s ease-out; }
  .banner.dunk #ball { transition: transform .11s cubic-bezier(.5,0,.85,0); }
  .banner.fall #ball { transition: transform .36s cubic-bezier(.4,0,.9,.6); }
  .banner.land #ball { transition: transform .3s ease-out; }

  /* ---- defender contests late and short ---- */
  #defender { transition: transform .42s cubic-bezier(.3,.7,.4,1); }
  .banner.rise #defender, .banner.dunk #defender { transform: translateY(-26px); }
  .banner.rise #dArmL, .banner.dunk #dArmL { transform: rotate(-166deg); }
  .banner.rise #dArmR, .banner.dunk #dArmR { transform: rotate(170deg); }
  .banner.fall #dArmL, .banner.land #dArmL { transform: rotate(-150deg); }
  .banner.fall #dArmR, .banner.land #dArmR { transform: rotate(140deg); }
  #dArmL, #dArmR { transition: transform .34s ease-out; }

  #rim { transform-box: view-box; transform-origin: 968px 96px; }
  .banner.dunk #rim, .banner.fall #rim { animation: rimflex .6s ease-out 1; }
  @keyframes rimflex { 0%{transform:rotate(0)} 28%{transform:rotate(8deg)} 100%{transform:rotate(0)} }

  #net { transform-box: view-box; transform-origin: 945px 98px; }
  .banner.dunk #net, .banner.fall #net { animation: ripple .65s ease-out 1; }
  @keyframes ripple { 0%{transform:scaleY(1)} 26%{transform:scaleY(1.5) skewX(10deg)}
                      60%{transform:scaleY(1.15) skewX(-6deg)} 100%{transform:scaleY(1)} }

  #scuff { opacity: 0; }
  .banner.land #scuff { animation: scuff .55s ease-out 1; }
  @keyframes scuff { 0%{opacity:.45; transform:scaleX(.3)} 100%{opacity:0; transform:scaleX(1.7)} }

  @media (prefers-reduced-motion: reduce) {
    .banner *, .banner { animation: none !important; transition: none !important; }
  }
</style>

<div class="wrap">
  <button class="replay" id="replay" type="button">Replay</button>
  <svg class="stage banner" id="banner" viewBox="0 0 1180 250"
       preserveAspectRatio="xMidYMid meet" role="img"
       aria-label="An animated silhouette drives from the three-point line, rises
                   over a defender and dunks. The restricted area supplies 28.4
                   percent of NBA shots and returns 1.34 points per attempt, more
                   than any other zone.">

    <line class="floor" x1="0" y1="212" x2="1180" y2="212"/>
    <line class="arc" x1="196" y1="76" x2="196" y2="212"/>
    <text class="lbl" x="206" y="90">three-point line</text>
    <line class="arc" x1="782" y1="150" x2="782" y2="212"/>
    <text class="lbl" x="676" y="166">restricted area</text>

    <g id="dots"></g>

    <!-- hoop in side elevation: the backboard is edge-on, so it is a plane at
         x=968 with the rim reaching left from it. No shooter's square, which
         only exists in a front view. -->
    <rect class="skin" x="1044" y="26" width="5" height="186" opacity=".3"/>
    <rect class="skin" x="972" y="30"  width="74" height="5" opacity=".3"/>
    <rect x="966" y="26" width="6" height="82" fill="__AXIS__"/>
    <rect id="rim" class="ballc" x="922" y="94" width="46" height="4" rx="2"/>
    <path id="net" d="M 924 98 L 931 132 L 959 132 L 966 98"
          fill="none" stroke="__AXIS__" stroke-width="1.5"/>
    <path d="M 933 98 L 938 132 M 945 98 L 945 132 M 957 98 L 952 132"
          fill="none" stroke="__AXIS__" stroke-width="1.1" opacity=".7"/>

    <ellipse id="scuff" cx="900" cy="210" rx="26" ry="4" fill="__MUTED__"/>

    <!-- Defender. The static x offset lives on an outer group: a CSS transform
         on the same element would replace the transform attribute outright and
         throw the figure back to x=0. -->
    <g transform="translate(858,0)">
      <g id="defender">
        <rect class="dfnd" x="-13" y="158" width="11" height="54" rx="5"/>
        <rect class="dfnd" x="2"   y="158" width="11" height="54" rx="5"/>
        <path class="dfnd" d="M -15 118 h 30 l -3 42 h -24 z"/>
        <ellipse class="dfnd" cx="0" cy="104" rx="13" ry="14"/>
        <rect class="dfnd j" id="dArmL" x="-25" y="120" width="9" height="58" rx="4"/>
        <rect class="dfnd j" id="dArmR" x="16"  y="120" width="9" height="58" rx="4"/>
      </g>
    </g>

    <!-- Attacker. Far-side limbs are drawn before the trunk and dimmed; the
         near arm is the one that dunks, so it stays in front and at full ink. -->
    <g id="rig">
      <g id="thighL" class="j">
        <rect class="skin" x="-14" y="158" width="11" height="30" rx="5" opacity=".68"/>
        <g id="shinL" class="j">
          <rect class="skin" x="-13" y="186" width="10" height="28" rx="5" opacity=".68"/>
          <rect class="skin" x="-19" y="206" width="20" height="7" rx="3" opacity=".68"/>
        </g>
      </g>
      <g id="upperL" class="j">
        <rect class="skin" x="-19" y="120" width="9" height="34" rx="4" opacity=".68"/>
        <g id="foreL" class="j">
          <rect class="skin" x="-19" y="152" width="8" height="30" rx="4" opacity=".68"/>
          <circle class="skin" cx="-14" cy="184" r="6" opacity=".68"/>
        </g>
      </g>

      <g id="trunk" class="j">
        <path class="kit" d="M -16 118 h 32 l -4 42 h -24 z"/>
        <rect class="skin" x="-13" y="146" width="26" height="15" rx="2"/>
        <ellipse class="skin" cx="0" cy="103" rx="13" ry="14"/>
      </g>

      <g id="thighR" class="j">
        <rect class="skin" x="3" y="158" width="12" height="30" rx="6"/>
        <g id="shinR" class="j">
          <rect class="skin" x="4" y="186" width="10" height="28" rx="5"/>
          <rect class="skin" x="2" y="206" width="20" height="7" rx="3"/>
        </g>
      </g>
      <g id="upperR" class="j">
        <rect class="skin" x="10" y="120" width="9" height="34" rx="4"/>
        <g id="foreR" class="j">
          <rect class="skin" x="10" y="152" width="8" height="30" rx="4"/>
          <circle class="skin" cx="14" cy="184" r="6"/>
        </g>
      </g>

      <g id="ball">
        <circle class="ballc" cx="30" cy="190" r="12"/>
        <path class="seam" d="M 18 190 h 24 M 30 178 v 24
                              M 21 182 a 14 14 0 0 0 0 16
                              M 39 182 a 14 14 0 0 1 0 16"/>
      </g>
    </g>
  </svg>

  <div class="cap">
    <b>28.4% of NBA shots come from the restricted area, and they return 1.34 points each.</b><br>
    <span>The long mid-range returns 0.83. That gap, not shooting talent, is where
          the points are. Five seasons, 1,087,633 attempts.</span>
  </div>
</div>

<script>
(function () {
  var svg  = document.getElementById('banner');
  var rig  = document.getElementById('rig');
  var dots = document.getElementById('dots');
  var btn  = document.getElementById('replay');
  var timers = [];

  // APEX_X is set so the extended dunk arm lands on the rim centre (945):
  // shoulder sits 14 right of the rig origin, the 62-long arm at 42deg reaches
  // a further 41.5, so 890 + 14 + 41.5 = 945.5.
  var START_X = 210, TAKEOFF_X = 838, APEX_X = 890, LAND_X = 900, JUMP_Y = -70;

  // Restricted-area attempt cloud: dense at the rim, thinning outward, the
  // shape the real distribution has in data/processed/player_zone.parquet.
  (function seed() {
    for (var i = 0; i < 40; i++) {
      var t = Math.pow(Math.random(), 0.6);
      var x = 945 - t * 165 - Math.random() * 14;
      var y = 200 - Math.random() * 16;
      var c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('class', 'dot');
      c.setAttribute('cx', x.toFixed(1));
      c.setAttribute('cy', y.toFixed(1));
      c.setAttribute('r', (2.6 + Math.random() * 3.2).toFixed(1));
      c.style.animationDelay = (0.3 + i * 0.02) + 's';
      dots.appendChild(c);
    }
  })();

  var STATES = ['run', 'gather', 'rise', 'dunk', 'fall', 'land'];
  function only(cls) {
    STATES.forEach(function (s) { svg.classList.remove(s); });
    if (cls) svg.classList.add(cls);
  }
  function at(ms, fn) { timers.push(setTimeout(fn, ms)); }
  function move(x, y, dur, ease) {
    rig.style.transition = 'transform ' + dur + 's ' + ease;
    rig.style.transform = 'translate(' + x + 'px,' + y + 'px)';
  }

  function reset() {
    timers.forEach(clearTimeout); timers = [];
    svg.classList.remove('go');
    only(null);
    rig.style.transition = 'none';
    rig.style.transform = 'translate(' + START_X + 'px,0px)';
    void svg.getBoundingClientRect();
  }

  function play() {
    reset();
    svg.classList.add('go');
    at(60,   function () { only('run');    move(TAKEOFF_X, 0, 1.9, 'cubic-bezier(.30,.03,.55,1)'); });
    at(1990, function () { only('gather'); move(TAKEOFF_X + 14, 8, .17, 'ease-out'); });
    at(2170, function () { only('rise');   move(APEX_X, JUMP_Y, .46, 'cubic-bezier(.16,.72,.34,1)'); });
    at(2640, function () { only('dunk'); });
    at(2800, function () { only('fall');   move(LAND_X, 0, .40, 'cubic-bezier(.55,.06,.85,.5)'); });
    at(3210, function () { only('land'); });
    at(3780, function () { only(null); });
  }

  var reduce = window.matchMedia &&
               window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) {
    svg.classList.add('go', 'dunk');
    rig.style.transform = 'translate(' + APEX_X + 'px,' + JUMP_Y + 'px)';
    btn.style.display = 'none';
  } else {
    btn.addEventListener('click', play);
    if ('IntersectionObserver' in window) {
      var armed = true;
      new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (e.isIntersecting && armed) { armed = false; play(); }
          else if (!e.isIntersecting) { armed = true; }
        });
      }, { threshold: 0.3 }).observe(svg);
    } else { play(); }
  }
})();
</script>
"""


def render(height: int = HEIGHT) -> None:
    """Draw the animated banner."""
    html = _TEMPLATE
    for key, val in (
        ("__SURFACE__", T.SURFACE), ("__PLANE__", T.PLANE), ("__INK__", T.INK),
        ("__INK2__", T.INK_2), ("__MUTED__", T.MUTED), ("__GRID__", T.GRID),
        ("__AXIS__", T.AXIS), ("__BLUE__", T.SERIES[0]), ("__ORANGE__", T.SERIES[1]),
        ("__FONT__", T.FONT),
    ):
        html = html.replace(key, val)
    components.html(html, height=height, scrolling=False)
