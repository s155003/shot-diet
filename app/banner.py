"""Scroll-driven drive-and-dunk hero for the landing page.

Everything on screen is a pure function of one number, `t`, the progress of the
move from 0 to 1. That is what makes the animation scrubbable: scrolling maps
the page position straight onto `t`, so the player runs, gathers, rises and
dunks under the reader's thumb rather than on a timer of its own. Net ripple,
rim flex, ball spin, shadow and motion ghosts are all functions of `t` too, so
they stay correct when scrubbed backwards.

The figures are original silhouettes, not NBA footage or any real player's
likeness. The hoop is a side elevation of the same geometry the shot charts use
and the caption numbers come out of data/processed/.

Rigging notes, both of which tore the figure apart before they were fixed:

  * Joints are rotated by writing `transform` on each group from JavaScript.
    Pivots are set with `transform-box: view-box` and an explicit
    `transform-origin`; the CSS default pivots on each group's bounding box,
    which is nowhere near the joint.
  * A CSS transform replaces an element's `transform` attribute rather than
    composing with it, so anything that moves keeps its static offset on a
    separate outer group.
"""
from __future__ import annotations

import streamlit.components.v1 as components

import theme as T

HEIGHT = 445

# Skeleton, authored standing with the feet on the floor (y = 212):
# shoulders 120, elbows 152, hands 182, hips 158, knees 188, ankles 212.
_TEMPLATE = r"""
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: __PLANE__;
               font-family: __FONT__; }
  .wrap { background: __SURFACE__; border: 1px solid rgba(11,11,11,0.12);
          border-radius: 3px; overflow: hidden; position: relative; }

  .hero { padding: 20px 26px 4px; }
  .hero h1 { margin: 0 0 8px; color: __INK__; font-size: 1.62rem;
             font-weight: 680; letter-spacing: -0.015em; line-height: 1.22; }
  .hero p  { margin: 0; color: __INK2__; font-size: 1.0rem; line-height: 1.55;
             max-width: 74ch; }
  .hero .hi { color: __BLUE__; font-weight: 650; }
  .hero .hi2 { color: __ORANGE__; font-weight: 650; }

  .stage { display: block; width: 100%; height: 236px; }

  .cap { padding: 6px 26px 14px; display: flex; gap: 26px;
         align-items: baseline; flex-wrap: wrap; }
  .cap b { color: __INK__; font-size: 0.9rem; font-weight: 650; }
  .cap span { color: __MUTED__; font-size: 0.82rem; }

  .hint { margin-left: auto; flex: 0 0 auto; color: __MUTED__; white-space: nowrap;
          font-size: 0.72rem; letter-spacing: 0.06em; text-transform: uppercase;
          display: flex; align-items: center; gap: 7px; }
  .hint .chev { display: inline-block; width: 7px; height: 7px;
                border-right: 1.6px solid __MUTED__;
                border-bottom: 1.6px solid __MUTED__;
                transform: rotate(45deg); animation: nudge 1.5s ease-in-out infinite; }
  @keyframes nudge { 0%,100% { transform: rotate(45deg) translate(0,0); }
                     50%     { transform: rotate(45deg) translate(2.5px,2.5px); } }
  .hint.done { opacity: 0; transition: opacity .4s; }

  .floor { stroke: __AXIS__; stroke-width: 1.6; }
  .mark  { stroke: __GRID__; stroke-width: 1.6; stroke-dasharray: 4 5; }
  .lbl   { fill: __MUTED__; font-size: 12px; }
  .limb  { stroke: __INK__; stroke-linecap: round; fill: none; }
  /* Far-side limbs are a solid shadow tone, not transparency: over a light
     surface a 40% black reads as a detached grey figure standing behind. */
  .far .limb { stroke: #54524e; }
  .far circle { fill: #54524e; }
  .kit   { fill: __BLUE__; }
  .dfnd  { stroke: __MUTED__; stroke-linecap: round; fill: none; }
  .dfndf { fill: __MUTED__; }
  .dot   { fill: __BLUE__; opacity: .26; }

  .j { transform-box: view-box; }
  #thighL,#thighR { transform-origin: 0px 158px; }
  #shinL, #shinR  { transform-origin: 0px 188px; }
  #upperL,#upperR { transform-origin: 0px 120px; }
  #foreL, #foreR  { transform-origin: 0px 152px; }
  #trunk          { transform-origin: 0px 158px; }
  #dArmL,#dArmR   { transform-origin: 0px 120px; }
  #rim            { transform-origin: 968px 96px; }

  @media (prefers-reduced-motion: reduce) { .hint { display: none; } }
</style>

<div class="wrap">
  <div class="hero">
    <h1>Two players score the same. One is a better shooter.<br>
        The other just takes easier shots.</h1>
    <p>Shot Diet reads a million NBA shots and separates
       <span class="hi">the shot you got</span> from
       <span class="hi2">whether you made it</span>, so a team can see which one
       is actually costing them points, and fix it.</p>
  </div>

  <svg class="stage" id="banner" viewBox="0 0 1180 250"
       preserveAspectRatio="xMidYMid meet" role="img"
       aria-label="A silhouette drives from the three-point line, rises over a
                   defender and dunks. The animation advances as the page
                   scrolls. The restricted area supplies 28.4 percent of NBA
                   shots and returns 1.34 points per attempt, more than any
                   other zone on the floor.">

    <line class="floor" x1="0" y1="212" x2="1180" y2="212"/>
    <line class="mark" x1="196" y1="76" x2="196" y2="212"/>
    <text class="lbl" x="206" y="90">three-point line</text>
    <line class="mark" x1="782" y1="150" x2="782" y2="212"/>
    <text class="lbl" x="664" y="166">restricted area</text>

    <g id="dots"></g>

    <!-- hoop, side elevation: the backboard is edge-on -->
    <rect fill="__INK__" opacity=".22" x="1044" y="26" width="5" height="186"/>
    <rect fill="__INK__" opacity=".22" x="972" y="30" width="74" height="5"/>
    <rect fill="__AXIS__" x="966" y="26" width="6" height="82"/>
    <rect id="rim" class="j" fill="__ORANGE__" x="922" y="94"
          width="46" height="4.5" rx="2"/>
    <path id="net"  fill="none" stroke="__AXIS__" stroke-width="1.5"/>
    <path id="net2" fill="none" stroke="__AXIS__" stroke-width="1.1" opacity=".65"/>

    <ellipse id="shadow" cx="0" cy="212" rx="26" ry="4.5" fill="__INK__" opacity=".12"/>

    <!-- defender: static x on the outer group, motion on the inner one -->
    <g transform="translate(874,0)">
      <g id="defender">
        <path class="dfnd" stroke-width="11" d="M -7 158 L -9 212"/>
        <path class="dfnd" stroke-width="11" d="M  7 158 L  9 212"/>
        <path class="dfndf" d="M -15 118 h 30 l -4 42 h -22 z"/>
        <ellipse class="dfndf" cx="0" cy="103" rx="12" ry="13.5"/>
        <path id="dArmL" class="dfnd j" stroke-width="9" d="M -13 120 L -17 178"/>
        <path id="dArmR" class="dfnd j" stroke-width="9" d="M  13 120 L  17 178"/>
      </g>
    </g>

    <g id="ghosts"></g>

    <g id="rig">
      <!-- far side first, dimmed, so it reads as depth -->
      <g class="far">
        <g id="thighL" class="j">
          <path class="limb" stroke-width="13" d="M -8 158 L -8 188"/>
          <g id="shinL" class="j">
            <path class="limb" stroke-width="10" d="M -8 188 L -8 208"/>
            <path class="limb" stroke-width="7" d="M -8 208 L -17 209"/>
          </g>
        </g>
        <g id="upperL" class="j">
          <path class="limb" stroke-width="10" d="M -14 120 L -14 152"/>
          <g id="foreL" class="j">
            <path class="limb" stroke-width="8" d="M -14 152 L -14 180"/>
            <circle fill="__INK__" cx="-14" cy="182" r="5.5"/>
          </g>
        </g>
      </g>

      <g id="trunk" class="j">
        <path class="kit" d="M -15.5 117 h 31 l -4.5 43 h -22 z"/>
        <path class="limb" stroke-width="15" d="M 0 148 L 0 158"/>
        <path class="limb" stroke-width="9"  d="M 0 110 L 0 118"/>
        <ellipse fill="__INK__" cx="0" cy="101" rx="12" ry="13.5"/>
      </g>

      <g id="thighR" class="j">
        <path class="limb" stroke-width="14" d="M 8 158 L 8 188"/>
        <g id="shinR" class="j">
          <path class="limb" stroke-width="11" d="M 8 188 L 8 208"/>
          <path class="limb" stroke-width="7.5" d="M 8 208 L -2 209"/>
        </g>
      </g>
      <g id="upperR" class="j">
        <path class="limb" stroke-width="11" d="M 14 120 L 14 152"/>
        <g id="foreR" class="j">
          <path class="limb" stroke-width="8.5" d="M 14 152 L 14 180"/>
          <circle fill="__INK__" cx="14" cy="182" r="6"/>
        </g>
      </g>
    </g>


    <g id="ball">
      <circle fill="__ORANGE__" cx="0" cy="0" r="12"/>
      <g id="seams" stroke="rgba(255,255,255,.8)" stroke-width="1.2" fill="none">
        <path d="M -12 0 h 24 M 0 -12 v 24
                 M -9 -8 a 14 14 0 0 0 0 16
                 M  9 -8 a 14 14 0 0 1 0 16"/>
      </g>
    </g>
  </svg>

  <div class="cap">
    <b>Right here is the best shot in basketball.</b>
    <span>28.4% of every NBA shot, paying 1.34 points each. A long two pays 0.83.</span>
    <div class="hint" id="hint"><span>scroll to play</span><i class="chev"></i></div>
  </div>
</div>

<script>
(function () {
  var svg = document.getElementById('banner');
  var rig = document.getElementById('rig');
  var hint = document.getElementById('hint');

  var el = {};
  ['thighL','shinL','thighR','shinR','upperL','foreL','upperR','foreR','trunk',
   'dArmL','dArmR','rim','defender','ball','seams','shadow','net','net2',
   'ghosts','dots'].forEach(function (k) { el[k] = document.getElementById(k); });

  // ---- geometry -----------------------------------------------------------
  var START_X = 200, TAKEOFF_X = 838, APEX_X = 890, LAND_X = 902, JUMP_Y = -72;
  var FLOOR = 212, RIM_X = 945, RIM_Y = 96;

  // ---- helpers ------------------------------------------------------------
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function lerp(a, b, u) { return a + (b - a) * u; }
  function smooth(u) { u = clamp(u, 0, 1); return u * u * (3 - 2 * u); }
  // progress of t inside [a,b], eased
  function seg(t, a, b) { return smooth((t - a) / (b - a)); }

  // ---- poses: joint angles in degrees, positive is clockwise --------------
  var GATHER = {thighL:-40, shinL:62, thighR:26, shinR:-48, upperL:-58, foreL:-40,
                upperR:-34, foreR:-46, trunk:-15};
  var RISE   = {thighL:72, shinL:-74, thighR:-32, shinR:-54, upperL:-52, foreL:-34,
                upperR:154, foreR:8, trunk:-5};
  var DUNK   = {thighL:64, shinL:-70, thighR:-30, shinR:-52, upperL:-50, foreL:-32,
                upperR:42, foreR:0, trunk:3};
  var FALL   = {thighL:30, shinL:-34, thighR:-24, shinR:-16, upperL:-64, foreL:-24,
                upperR:84, foreR:-30, trunk:-2};
  var LAND   = {thighL:-24, shinL:38, thighR:18, shinR:-30, upperL:-44, foreL:-34,
                upperR:38, foreR:-30, trunk:-10};
  var REST   = {thighL:-4, shinL:4, thighR:4, shinR:-4, upperL:-8, foreL:-6,
                upperR:8, foreR:-6, trunk:-2};
  var KEYS = Object.keys(REST);

  function blend(a, b, u) {
    var o = {};
    for (var i = 0; i < KEYS.length; i++) o[KEYS[i]] = lerp(a[KEYS[i]], b[KEYS[i]], u);
    return o;
  }

  // Run cycle: counter-rotating limbs driven off one phase angle, with the
  // shin trailing the thigh so the leg folds through the swing.
  function runPose(ph) {
    var s = Math.sin(ph), c = Math.cos(ph);
    return {
      thighL: 38 * s,
      shinL: -34 + 30 * Math.sin(ph - 1.15),
      thighR: -38 * s,
      shinR: -34 + 30 * Math.sin(ph - 1.15 + Math.PI),
      upperL: -36 * s, foreL: -38 + 14 * c,
      upperR: 36 * s,  foreR: -40 - 14 * c,
      trunk: -9
    };
  }

  // ---- the whole scene as a function of t --------------------------------
  var P = { run: 0.50, gather: 0.58, rise: 0.75, dunk: 0.81, fall: 0.92 };

  function frame(t) {
    t = clamp(t, 0, 1);
    var pose, x, y, ballPos, spin = t * 1500;

    if (t < P.run) {
      var u = t / P.run;
      var ph = u * Math.PI * 2 * 5.2;             // strides across the drive
      pose = runPose(ph);
      x = lerp(START_X, TAKEOFF_X, smooth(u));
      y = Math.abs(Math.sin(ph)) * -3.5;           // slight bob
      // dribble: ball falls to the floor and returns, twice per stride
      var b = Math.abs(Math.cos(ph));
      ballPos = [x + 26, lerp(FLOOR - 12, 174, b)];
    } else if (t < P.gather) {
      var u2 = seg(t, P.run, P.gather);
      pose = blend(runPose(Math.PI * 2 * 5.2), GATHER, u2);
      x = lerp(TAKEOFF_X, TAKEOFF_X + 16, u2);
      y = lerp(0, 9, u2);
      ballPos = [lerp(x + 26, x + 10, u2), lerp(174, 150, u2)];
    } else if (t < P.rise) {
      var u3 = seg(t, P.gather, P.rise);
      pose = blend(GATHER, RISE, u3);
      x = lerp(TAKEOFF_X + 16, APEX_X, u3);
      y = lerp(9, JUMP_Y, u3);
      // ball rides up with the cocked hand
      ballPos = [lerp(x + 10, x + 45, u3), lerp(150 + y * 0.2, y + 66, u3)];
    } else if (t < P.dunk) {
      var u4 = seg(t, P.rise, P.dunk);
      pose = blend(RISE, DUNK, u4);
      x = APEX_X; y = JUMP_Y;
      ballPos = [lerp(x + 45, RIM_X, u4), lerp(y + 66, RIM_Y - 2, u4)];
    } else if (t < P.fall) {
      var u5 = seg(t, P.dunk, P.fall);
      pose = blend(DUNK, FALL, u5);
      x = lerp(APEX_X, LAND_X, u5);
      y = lerp(JUMP_Y, 0, u5 * u5);                // gravity: accelerating drop
      ballPos = [lerp(RIM_X, RIM_X + 4, u5), lerp(RIM_Y - 2, FLOOR - 12, u5 * u5)];
    } else {
      var u6 = seg(t, P.fall, 1);
      pose = blend(FALL, u6 < 0.55 ? LAND : LAND, u6);
      pose = blend(pose, REST, clamp((u6 - 0.55) / 0.45, 0, 1));
      x = LAND_X; y = 0;
      // ball bounces once and settles
      var bt = u6 / 1.0;
      var bounce = Math.abs(Math.sin(bt * Math.PI * 1.6)) * (1 - bt) * 46;
      ballPos = [RIM_X + 4 + bt * 26, FLOOR - 12 - bounce];
    }

    // write joints
    for (var i = 0; i < KEYS.length; i++) {
      var k = KEYS[i];
      if (el[k]) el[k].style.transform = 'rotate(' + pose[k].toFixed(2) + 'deg)';
    }
    rig.style.transform = 'translate(' + x.toFixed(1) + 'px,' + y.toFixed(1) + 'px)';

    // ball
    el.ball.style.transform =
      'translate(' + ballPos[0].toFixed(1) + 'px,' + ballPos[1].toFixed(1) + 'px)';
    el.seams.style.transform = 'rotate(' + spin.toFixed(1) + 'deg)';

    // shadow: shrinks and fades as the player rises
    var lift = clamp(-y / -JUMP_Y, 0, 1);
    el.shadow.setAttribute('cx', x.toFixed(1));
    el.shadow.setAttribute('rx', (26 - 12 * lift).toFixed(1));
    el.shadow.setAttribute('opacity', (0.13 - 0.085 * lift).toFixed(3));

    // defender contests late and lands short
    var dLift = t < P.gather ? 0
              : t < P.dunk ? smooth((t - P.gather) / (P.dunk - P.gather))
              : 1 - smooth((t - P.dunk) / (1 - P.dunk));
    el.defender.style.transform = 'translateY(' + (-30 * dLift).toFixed(1) + 'px)';
    el.dArmL.style.transform = 'rotate(' + (-6 - 160 * dLift).toFixed(1) + 'deg)';
    el.dArmR.style.transform = 'rotate(' + (6 + 164 * dLift).toFixed(1) + 'deg)';

    // rim flex and net ripple, both peaking just after contact
    var hit = clamp((t - P.dunk) / 0.14, 0, 1);
    var shock = t < P.dunk ? 0 : Math.sin(hit * Math.PI) * (1 - hit * 0.35);
    el.rim.style.transform = 'rotate(' + (9 * shock).toFixed(2) + 'deg)';
    drawNet(shock);

    drawGhosts(t, x, y);
  }

  // Exposed so the pose inspector in tests/ can scrub to an exact frame.
  window.__scrub = function (t) { mode = 'manual'; frame(t); };

  // net hangs from the rim; `s` deforms it on contact
  function drawNet(s) {
    var L = 924, R = 966, top = 98, len = 34 + 12 * s, sq = 1 - 0.28 * s;
    var cx = (L + R) / 2;
    var bl = cx - (cx - L) * sq * 0.62, br = cx + (R - cx) * sq * 0.62;
    el.net.setAttribute('d',
      'M ' + L + ' ' + top + ' Q ' + (L + 2) + ' ' + (top + len * 0.6) + ' '
        + bl + ' ' + (top + len) + ' L ' + br + ' ' + (top + len)
        + ' Q ' + (R - 2) + ' ' + (top + len * 0.6) + ' ' + R + ' ' + top);
    var m = [];
    for (var i = 1; i <= 3; i++) {
      var f = i / 4;
      var x0 = L + (R - L) * f, x1 = bl + (br - bl) * f;
      m.push('M ' + x0 + ' ' + top + ' Q ' + lerp(x0, x1, .5) + ' '
             + (top + len * 0.55) + ' ' + x1 + ' ' + (top + len));
    }
    el.net2.setAttribute('d', m.join(' '));
  }

  // three fading copies of the rig, lagging in time, only while airborne
  var GH = 3;
  (function buildGhosts() {
    for (var i = 0; i < GH; i++) {
      var u = document.createElementNS('http://www.w3.org/2000/svg', 'use');
      u.setAttributeNS('http://www.w3.org/1999/xlink', 'href', '#rig');
      u.setAttribute('opacity', '0');
      el.ghosts.appendChild(u);
    }
  })();

  function drawGhosts(t, x, y) {
    var air = t > P.gather && t < P.fall ? 1 : 0;
    for (var i = 0; i < GH; i++) {
      var g = el.ghosts.childNodes[i];
      if (!air) { g.setAttribute('opacity', '0'); continue; }
      var back = (i + 1) * 0.022;
      var tt = clamp(t - back, 0, 1);
      var gx = lerp(TAKEOFF_X + 16, APEX_X, smooth((tt - P.gather) / (P.rise - P.gather)));
      var gy = lerp(9, JUMP_Y, smooth((tt - P.gather) / (P.rise - P.gather)));
      if (tt > P.rise) { gx = x; gy = y; }
      g.setAttribute('transform', 'translate(' + (gx - x) + ',' + (gy - y) + ')');
      g.setAttribute('opacity', (0.13 - i * 0.035).toFixed(3));
    }
  }

  // restricted-area attempt cloud, dense at the rim
  (function seed() {
    var f = document.createDocumentFragment();
    for (var i = 0; i < 42; i++) {
      var k = Math.pow(Math.random(), 0.6);
      var c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('class', 'dot');
      c.setAttribute('cx', (RIM_X - k * 168 - Math.random() * 12).toFixed(1));
      c.setAttribute('cy', (201 - Math.random() * 15).toFixed(1));
      c.setAttribute('r', (2.6 + Math.random() * 3.2).toFixed(1));
      f.appendChild(c);
    }
    el.dots.appendChild(f);
  })();

  // ---- drive it ----------------------------------------------------------
  var reduce = window.matchMedia &&
               window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { frame(P.dunk + 0.005); return; }

  // The component runs in a srcdoc iframe, which is same-origin with the app,
  // so the parent's scroll position is readable. If a browser or a future
  // Streamlit sandbox blocks it, fall back to a timed loop.
  function scroller() {
    try {
      var d = window.parent.document;
      var m = d.querySelector('[data-testid="stMain"]') ||
              d.querySelector('section.main') ||
              d.scrollingElement;
      if (!m) return null;
      void m.scrollTop;
      return m;
    } catch (e) { return null; }
  }

  // Short enough that the whole move plays while the banner is still on
  // screen; the hero is ~430px tall, so a longer scrub would finish the dunk
  // after the reader had already scrolled past it.
  var SCRUB = 420;
  var host = scroller();
  var mode = 'intro';
  frame(0);

  // Intro plays the move once so it is visible before anyone scrolls, then
  // rewinds to the start. Without the rewind the banner rests on the landed
  // pose and the first scroll snaps the player backwards to mid-stride.
  var t0 = null, INTRO = 3000, HOLD = 620, REWIND = 520;
  function intro(ts) {
    if (mode !== 'intro') return;
    if (t0 === null) t0 = ts;
    var e = ts - t0;
    if (e < INTRO) { frame(e / INTRO); }
    else if (e < INTRO + HOLD) { frame(1); }
    else if (e < INTRO + HOLD + REWIND) {
      frame(1 - smooth((e - INTRO - HOLD) / REWIND));
    } else {
      frame(0);
      mode = host ? 'scroll' : 'loop';
      if (!host) loopStart();
      return;
    }
    requestAnimationFrame(intro);
  }
  requestAnimationFrame(intro);

  if (host) {
    var pending = false;
    var onScroll = function () {
      if (pending) return;
      pending = true;
      requestAnimationFrame(function () {
        pending = false;
        var top = host === document.scrollingElement || !host.scrollTop && host.scrollY
          ? (host.scrollY || 0) : host.scrollTop;
        if (top > 4) {
          mode = 'scroll';
          hint.classList.add('done');
        }
        if (mode === 'scroll') frame(clamp(top / SCRUB, 0, 1));
      });
    };
    host.addEventListener('scroll', onScroll, { passive: true });
    try { window.parent.addEventListener('scroll', onScroll, { passive: true }); } catch (e) {}
  }

  function loopStart() {
    var s = null;
    (function step(ts) {
      if (s === null) s = ts;
      var p = ((ts - s) % 5200) / 3200;
      frame(clamp(p, 0, 1));
      requestAnimationFrame(step);
    })(performance.now());
  }
})();
</script>
"""


def render(height: int = HEIGHT) -> None:
    """Draw the scroll-driven hero."""
    html = _TEMPLATE
    for key, val in (
        ("__SURFACE__", T.SURFACE), ("__PLANE__", T.PLANE), ("__INK__", T.INK),
        ("__INK2__", T.INK_2), ("__MUTED__", T.MUTED), ("__GRID__", T.GRID),
        ("__AXIS__", T.AXIS), ("__BLUE__", T.SERIES[0]), ("__ORANGE__", T.SERIES[1]),
        ("__FONT__", T.FONT),
    ):
        html = html.replace(key, val)
    components.html(html, height=height, scrolling=False)
