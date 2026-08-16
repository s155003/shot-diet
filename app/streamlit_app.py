"""Shot Diet - separating shot selection from shot making in the NBA."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

import data_access as D  # noqa: F401  (also puts src/ on the path)
import charts as C
import court
import theme as T
from analyze import ZONE_POINTS, optimise_diet
from config import ZONE_ORDER

st.set_page_config(page_title="Shot Diet", page_icon="🏀", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown(f"""
<style>
  .stApp {{ background: {T.PLANE}; }}
  html, body, [class*="css"] {{ font-family: {T.FONT}; }}
  h1, h2, h3 {{ color: {T.INK}; letter-spacing: -0.01em; }}
  .lede {{ color: {T.INK_2}; font-size: 1.05rem; line-height: 1.6; max-width: 70ch; }}
  .kpi {{ background: {T.SURFACE}; border: 1px solid rgba(11,11,11,0.10);
          border-radius: 10px; padding: 16px 18px; height: 100%; }}
  .kpi .label {{ color: {T.MUTED}; font-size: 0.78rem; text-transform: uppercase;
                 letter-spacing: 0.06em; }}
  .kpi .value {{ color: {T.INK}; font-size: 2.0rem; font-weight: 650;
                 line-height: 1.15; margin: 4px 0 2px; }}
  .kpi .foot {{ color: {T.INK_2}; font-size: 0.85rem; line-height: 1.45; }}
  .callout {{ background: {T.SURFACE}; border-left: 3px solid {T.SERIES[0]};
              border-radius: 6px; padding: 14px 18px; color: {T.INK_2};
              font-size: 0.97rem; line-height: 1.6; }}
  .note {{ color: {T.MUTED}; font-size: 0.84rem; line-height: 1.5; }}
  [data-testid="stMetricValue"] {{ font-size: 1.6rem; }}
</style>
""", unsafe_allow_html=True)


def kpi(label: str, value: str, foot: str = "") -> str:
    return (f'<div class="kpi"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="foot">{foot}</div></div>')


SUM = D.summary()
SEASONS = D.seasons()
LATEST = SEASONS[0]

PAGES = ["The finding", "Players", "Shot-diet optimiser", "Teams", "Method & validation"]
with st.sidebar:
    st.markdown("### 🏀 Shot Diet")
    st.caption("Separating shot selection from shot making")
    page = st.radio("Section", PAGES, label_visibility="collapsed")
    st.divider()
    st.caption(
        f"**{SUM.get('n_shots', 0):,}** shots · **{len(SEASONS)}** seasons "
        f"({SEASONS[-1]} to {SEASONS[0]}) · every regular-season field goal "
        "attempt from stats.nba.com.")


# ==========================================================================
# 1. the finding
# ==========================================================================
if page == "The finding":
    st.title("Coach the diet, not the shooter")
    st.markdown(
        '<p class="lede">Every field goal attempt is two decisions layered on top '
        'of each other: <b>what shot the offence generated</b>, and <b>whether the '
        'player put it in</b>. Box-score efficiency welds them together, so a centre '
        'who only dunks looks like a great shooter and a guard creating late-clock '
        'jumpers looks like a bad one. This project separates them, then asks which '
        'half a team can actually act on.</p>', unsafe_allow_html=True)

    sh = D.table("split_half").set_index("metric")
    yoy = D.table("yoy").set_index("metric")
    spread = D.table("spread").set_index("component")
    stab = SUM.get("stabilization_attempts_50pct", {})

    st.write("")
    c = st.columns(4)
    c[0].markdown(kpi("Selection stabilises at", f"{stab.get('selection', 0):.0f} shots",
                      "Reliability reaches 0.5 almost immediately."), unsafe_allow_html=True)
    c[1].markdown(kpi("Making stabilises at", f"{stab.get('making', 0):.0f} shots",
                      "About four months of a starter's season."), unsafe_allow_html=True)
    c[2].markdown(kpi("Selection, year to year", f"r = {yoy.loc['selection', 'yoy_r']:.2f}",
                      "Nearly a fixed property of role and scheme."), unsafe_allow_html=True)
    c[3].markdown(kpi("Making, year to year", f"r = {yoy.loc['making', 'yoy_r']:.2f}",
                      "Real, but a third of it does not carry over."),
                  unsafe_allow_html=True)

    st.write("")
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("One half repeats. The other partly evaporates.")
        st.plotly_chart(C.reliability_bars(D.table("split_half"), D.table("yoy")),
                        use_container_width=True)
        st.markdown(
            f'<p class="note">Split-half correlates a player\'s odd-numbered games '
            f'against his even-numbered ones within the same season (Spearman-Brown '
            f'corrected, n = {int(sh.loc["selection", "n_player_seasons"]):,} '
            f'player-seasons). Season-to-season pairs consecutive seasons for the same '
            f'player (n = {int(yoy.loc["selection", "n_pairs"]):,}).</p>',
            unsafe_allow_html=True)
    with right:
        st.subheader("How many shots before you can trust the number?")
        st.plotly_chart(
            C.stabilization_curve(D.table("stabilization_curve"), stab),
            use_container_width=True)
        st.markdown(
            '<p class="note">Reliability measured inside attempt bins, then fitted to '
            'r = n / (n + k). Selection is knowable from a handful of possessions; '
            'shot making needs most of a season before half the spread is signal.</p>',
            unsafe_allow_html=True)

    st.divider()
    st.subheader("Why the leaderboard misleads you")
    a, b = st.columns([1.05, 1], gap="large")
    with a:
        sel_sd = spread.loc["selection", "observed_sd_p100"]
        mak_sd = spread.loc["making", "observed_sd_p100"]
        sel_rep = spread.loc["selection", "repeatable_sd_p100"]
        mak_rep = spread.loc["making", "repeatable_sd_p100"]
        corr = SUM.get("corr_selection_making", 0)
        st.markdown(
            f'<div class="callout">In any single season the two components look '
            f'equally important — selection varies across players with a standard '
            f'deviation of <b>{sel_sd:.1f}</b> points per 100 shots, making by '
            f'<b>{mak_sd:.1f}</b>. Strip out the measurement noise and the picture '
            f'changes: <b>{sel_rep:.1f}</b> of the selection spread is real against '
            f'only <b>{mak_rep:.1f}</b> of the making spread. Roughly '
            f'<b>{spread.loc["selection", "share_of_repeatable_spread"] * 100:.0f}%</b> '
            f'of the genuinely repeatable difference between players is which shots '
            f'they take.<br><br>The two also pull against each other '
            f'(r = <b>{corr:+.2f}</b>). Players handed the easiest shots tend to be '
            f'the weaker shot-makers, and the best shot-makers are handed the hardest '
            f'ones — which is exactly why raw points-per-shot flatters the first group '
            f'and punishes the second.</div>', unsafe_allow_html=True)
        ps = D.table("player_season")
        d = ps[(ps["SEASON"] == LATEST) & (ps["fga"] >= 200)]
        show = ["Nikola Jokić", "DeMar DeRozan", "Rudy Gobert", "Luka Dončić",
                "Kevin Durant", "Mitchell Robinson"]
        show = [n for n in show if n in set(d["PLAYER_NAME"])]

        ex = d[d["PLAYER_NAME"].isin(show)].sort_values("selection_p100")
        ex = ex[["PLAYER_NAME", "team", "fga", "pps", "selection_p100",
                 "making_p100"]].copy()
        ex.columns = ["Player", "Team", "FGA", "Pts/shot", "Selection /100",
                      "Making /100"]
        st.markdown(f"**Same league, opposite jobs — {LATEST}**")
        st.dataframe(
            ex.style.format({"FGA": "{:.0f}", "Pts/shot": "{:.3f}",
                             "Selection /100": "{:+.1f}", "Making /100": "{:+.1f}"})
              .background_gradient(subset=["Selection /100"], cmap="RdBu",
                                   vmin=-40, vmax=40)
              .background_gradient(subset=["Making /100"], cmap="RdBu",
                                   vmin=-25, vmax=25),
            use_container_width=True, hide_index=True)
    with b:
        st.plotly_chart(C.selection_vs_making(d, show), use_container_width=True)
        st.markdown(f'<p class="note">{LATEST}, minimum 200 attempts. Bubble size is '
                    'volume; colour is total points per 100 above league average. '
                    'Ringed points are labelled.</p>',
                    unsafe_allow_html=True)

    st.divider()
    st.subheader("So what should a staff actually do?")
    bts = D.table("backtest_summary")
    g1, g2 = st.columns([1, 1], gap="large")
    with g1:
        st.plotly_chart(C.backtest_dots(bts), use_container_width=True)
        st.markdown('<p class="note">Each season\'s prescription is graded against '
                    'the <i>following</i> season\'s shooting. Bars are 95% bootstrap '
                    'confidence intervals; grey means the interval contains zero.</p>',
                    unsafe_allow_html=True)
    with g2:
        eb_v_lg = bts[bts["comparison"] == "EB vs. league-average advice"].iloc[0]
        eb_v_raw = bts[bts["comparison"] == "EB vs. unshrunk"].iloc[0]
        eb_v_kept = bts[bts["comparison"] == "EB prescription vs. do nothing"].iloc[0]
        st.markdown(
            f'<div class="callout">Moving <b>5% of a player\'s attempts</b> out of the '
            f'mid-range and into the rim and corners is worth '
            f'<b>{eb_v_kept["mean_p100"]:+.2f}</b> points per 100 shots the following '
            f'season, and it works for '
            f'<b>{eb_v_kept["pct_positive"]:.1f}%</b> of players.<br><br>'
            f'But tailoring that advice to the individual shooter is worth '
            f'<b>nothing</b>. A prescription built from a player\'s own '
            f'shrunk zone-by-zone shooting beats generic league-average advice by '
            f'<b>{eb_v_lg["mean_p100"]:+.2f}</b> points per 100 '
            f'(95% CI {eb_v_lg["ci_low"]:+.2f} to {eb_v_lg["ci_high"]:+.2f}) — '
            f'indistinguishable from zero, and the two prescriptions genuinely differ '
            f'for about half the league.<br><br>'
            f'Trusting a player\'s raw hot zones is actively worse '
            f'(<b>{eb_v_raw["mean_p100"]:+.2f}</b> points per 100 for the shrunk version '
            f'over the unshrunk one). One season of shot data simply does not contain '
            f'a trustworthy read on where an individual shoots best.</div>',
            unsafe_allow_html=True)
        st.markdown(
            '<p class="note" style="margin-top:14px"><b>The practical upshot.</b> '
            'Shot quality is a scheme problem, not a personnel problem. Spend the '
            'coaching capital on where shots come from — it shows up in eleven '
            'attempts and it persists across seasons. Do not build a personalised '
            'shot-diet plan off one season of shooting splits; you will be coaching '
            'noise.</p>', unsafe_allow_html=True)


# ==========================================================================
# 2. players
# ==========================================================================
elif page == "Players":
    st.title("Players")
    ps = D.table("player_season")

    c = st.columns([1, 1, 2])
    season = c[0].selectbox("Season", SEASONS, index=0)
    min_fga = c[1].slider("Minimum attempts", 100, 1000, 200, step=50)
    d = ps[(ps["SEASON"] == season) & (ps["fga"] >= min_fga)].copy()

    names = sorted(d["PLAYER_NAME"].unique())
    default = [n for n in ("Nikola Jokić", "DeMar DeRozan", "Rudy Gobert") if n in names]
    picked = c[2].multiselect("Highlight players", names, default=default)

    st.plotly_chart(C.selection_vs_making(d, picked, season), use_container_width=True)

    st.subheader("Leaderboard")
    sort_by = st.radio("Rank by", ["Total points added", "Shot selection",
                                   "Shot making"], horizontal=True)
    col = {"Total points added": "total_pts", "Shot selection": "selection_p100",
           "Shot making": "making_p100"}[sort_by]
    tbl = d.sort_values(col, ascending=False)[
        ["PLAYER_NAME", "team", "fga", "fg_pct", "pps", "xpps",
         "selection_p100", "making_p100", "total_pts"]].copy()
    tbl.columns = ["Player", "Team", "FGA", "FG%", "Pts/shot", "Expected pts/shot",
                   "Selection /100", "Making /100", "Total pts added"]
    st.dataframe(
        tbl.style.format({"FG%": "{:.1%}", "Pts/shot": "{:.3f}",
                          "Expected pts/shot": "{:.3f}", "Selection /100": "{:+.1f}",
                          "Making /100": "{:+.1f}", "Total pts added": "{:+.0f}",
                          "FGA": "{:.0f}"})
           .background_gradient(subset=["Selection /100"], cmap="RdBu", vmin=-30, vmax=30)
           .background_gradient(subset=["Making /100"], cmap="RdBu", vmin=-25, vmax=25),
        use_container_width=True, height=420, hide_index=True)

    st.divider()
    st.subheader("Player detail")
    who = st.selectbox("Player", names,
                       index=names.index(picked[0]) if picked else 0)
    row = d[d["PLAYER_NAME"] == who].iloc[0]

    m = st.columns(5)
    m[0].metric("Attempts", f"{row['fga']:,.0f}")
    m[1].metric("Points per shot", f"{row['pps']:.3f}",
                f"{(row['pps'] - row['league_pps']) * 100:+.1f} vs league /100")
    # Units live in the label rather than the delta slot: Streamlit renders a
    # delta as an arrow, and an arrow beside a negative selection number reads
    # as a direction of travel it does not have.
    m[2].metric("Shot selection /100", f"{row['selection_p100']:+.1f}")
    m[3].metric("Shot making /100", f"{row['making_p100']:+.1f}")
    m[4].metric("Total points added", f"{row['total_pts']:+.0f}")

    left, right = st.columns([1.1, 1], gap="large")
    with left:
        if season == LATEST:
            shots = D.table("shots_latest")
            his = shots[shots["PLAYER_NAME"] == who]
            st.plotly_chart(
                court.hex_shot_chart(his, shots, title=f"{who} — {season}"),
                use_container_width=True)
            st.markdown('<p class="note">Hexagon area is attempt volume; colour is '
                        'points per shot against what the league scores from that same '
                        'patch of floor.</p>', unsafe_allow_html=True)
        else:
            st.info(f"Shot charts ship for {LATEST} only, to keep the repository small. "
                    "Re-run `src/run_pipeline.py` to build them for other seasons.")
    with right:
        z = D.table("player_zone")
        zz = z[(z["SEASON"] == season) & (z["PLAYER_NAME"] == who)].copy()
        zz["zone"] = pd.Categorical(zz["zone"], ZONE_ORDER, ordered=True)
        zz = zz.sort_values("zone")
        out = zz[["zone", "att", "share", "fg_pct", "fg_pct_eb", "league_fg_pct",
                  "ppa_eb", "league_ppa"]].copy()
        out.columns = ["Zone", "Att", "Share", "FG%", "FG% (shrunk)", "League FG%",
                       "Pts/att (shrunk)", "League pts/att"]
        st.markdown("**Zone profile**")
        st.dataframe(out.style.format({"Share": "{:.1%}", "FG%": "{:.1%}",
                                       "FG% (shrunk)": "{:.1%}", "League FG%": "{:.1%}",
                                       "Pts/att (shrunk)": "{:.2f}",
                                       "League pts/att": "{:.2f}", "Att": "{:.0f}"}),
                     use_container_width=True, hide_index=True, height=250)
        st.markdown('<p class="note">"Shrunk" blends the player\'s own rate toward the '
                    'league rate in proportion to how little we have seen — the '
                    'correction that keeps a 12-for-20 stretch from being read as a '
                    'skill.</p>', unsafe_allow_html=True)

        hist = ps[ps["PLAYER_NAME"] == who].sort_values("SEASON")
        if len(hist) > 1:
            st.markdown("**Season by season**")
            h = hist[["SEASON", "fga", "pps", "selection_p100", "making_p100"]].copy()
            h.columns = ["Season", "FGA", "Pts/shot", "Selection /100", "Making /100"]
            st.dataframe(h.style.format({"Pts/shot": "{:.3f}", "FGA": "{:.0f}",
                                         "Selection /100": "{:+.1f}",
                                         "Making /100": "{:+.1f}"}),
                         use_container_width=True, hide_index=True)


# ==========================================================================
# 3. optimiser
# ==========================================================================
elif page == "Shot-diet optimiser":
    st.title("Shot-diet optimiser")
    st.markdown(
        '<p class="lede">A linear program that reallocates a fixed share of a '
        'player\'s attempts across the six zones to maximise expected points, '
        'subject to how much churn a staff would realistically install. '
        'Zone values are empirical-Bayes estimates: the player\'s own rate blended '
        'toward the league\'s in proportion to sample size.</p>',
        unsafe_allow_html=True)

    z, ps, lz = D.table("player_zone"), D.table("player_season"), D.table("league_zone")

    c = st.columns([1, 1.4, 1, 1])
    season = c[0].selectbox("Season", SEASONS, index=0)
    pool = ps[(ps["SEASON"] == season) & (ps["fga"] >= 200)]
    names = sorted(pool["PLAYER_NAME"].unique())
    who = c[1].selectbox("Player", names,
                         index=names.index("DeMar DeRozan")
                         if "DeMar DeRozan" in names else 0)
    move = c[2].slider("Share of attempts you may move", 1, 25, 5, step=1,
                       format="%d%%") / 100
    zone_cap = c[3].slider("Max change in any one zone", 1, 25, 5, step=1,
                           format="%d%%") / 100

    zz = z[(z["SEASON"] == season) & (z["PLAYER_NAME"] == who)]
    pri = lz[lz["SEASON"] == season].set_index(lz[lz["SEASON"] == season]["zone"]
                                               .astype(str)).reindex(ZONE_ORDER)
    g = zz.set_index(zz["zone"].astype(str)).reindex(ZONE_ORDER)

    att = g["att"].fillna(0.0).to_numpy(float)
    made = g["made"].fillna(0.0).to_numpy(float)
    league_pct = pri["league_fg_pct"].to_numpy(float)
    k = pri["prior_k"].to_numpy(float)
    pt_val = np.array([ZONE_POINTS[zone] for zone in ZONE_ORDER], float)

    shares = att / att.sum()
    eb = (made + k * league_pct) / (att + k)
    values = eb * pt_val
    new_shares = optimise_diet(shares, values, move, zone_cap)

    cur_pps, new_pps = float(shares @ values), float(new_shares @ values)
    fga = float(att.sum())
    gain100 = (new_pps - cur_pps) * 100

    m = st.columns(4)
    m[0].metric("Attempts", f"{fga:,.0f}")
    m[1].metric("Expected pts/shot now", f"{cur_pps:.3f}")
    m[2].metric("After reallocation", f"{new_pps:.3f}", f"{gain100:+.2f} per 100")
    m[3].metric("Points gained over the season",
                f"{(new_pps - cur_pps) * fga:+.0f}")
    if fga < 400:
        st.caption("Low volume — treat the season-points figure with care.")

    det = pd.DataFrame({
        "zone": ZONE_ORDER, "att": att, "share": shares, "new_share": new_shares,
        "delta": new_shares - shares, "ppa_eb": values, "league_ppa":
        pri["league_ppa"].to_numpy(float)})

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.plotly_chart(C.zone_prescription(det, ZONE_ORDER),
                        use_container_width=True)
    with right:
        st.markdown("**The prescription**")
        moves = det[det["delta"].abs() > 1e-6].sort_values("delta", ascending=False)
        if moves.empty:
            st.success("This diet is already optimal under the current constraints.")
        else:
            for _, r in moves.iterrows():
                arrow = "▲" if r["delta"] > 0 else "▼"
                colr = T.GOOD if r["delta"] > 0 else T.CRITICAL
                st.markdown(
                    f'<div style="padding:7px 0;border-bottom:1px solid {T.GRID}">'
                    f'<span style="color:{colr};font-weight:700">{arrow}</span> '
                    f'<b style="color:{T.INK}">{r["zone"]}</b><br>'
                    f'<span class="note">{abs(r["delta"]) * 100:.1f}% of attempts '
                    f'({abs(r["delta"]) * fga:.0f} shots) · worth '
                    f'{r["ppa_eb"]:.2f} pts/att to him, '
                    f'{r["league_ppa"]:.2f} league-wide</span></div>',
                    unsafe_allow_html=True)

        st.markdown(
            f'<p class="note" style="margin-top:16px"><b>Read this with the caveat '
            f'from the finding.</b> Out of sample, this personalised prescription is '
            f'no better than the same move computed from league-average zone values '
            f'alone. The gain is real; the personalisation is not.</p>',
            unsafe_allow_html=True)

    st.divider()
    st.subheader("Biggest available gains this season")
    summ = D.table("prescription_summary")
    s = summ[summ["SEASON"] == season].nlargest(20, "gain_pts_season")[
        ["PLAYER_NAME", "fga", "current_pps_model", "optimised_pps",
         "gain_p100", "gain_pts_season", "volume_moved_pct"]].copy()
    s.columns = ["Player", "FGA", "Expected pts/shot", "Optimised", "Gain /100",
                 "Season points", "Volume moved"]
    st.dataframe(s.style.format({"FGA": "{:.0f}", "Expected pts/shot": "{:.3f}",
                                 "Optimised": "{:.3f}", "Gain /100": "{:+.2f}",
                                 "Season points": "{:+.0f}", "Volume moved": "{:.1f}%"}),
                 use_container_width=True, hide_index=True, height=400)
    st.markdown('<p class="note">Computed at the default 5% move budget.</p>',
                unsafe_allow_html=True)


# ==========================================================================
# 4. teams
# ==========================================================================
elif page == "Teams":
    st.title("Teams")
    st.markdown('<p class="lede">The same split applied to all thirty offences. '
                'Selection is the part a coaching staff owns.</p>',
                unsafe_allow_html=True)
    ts = D.table("team_season")
    season = st.selectbox("Season", SEASONS, index=0)
    d = ts[ts["SEASON"] == season]

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.plotly_chart(C.team_scatter(d), use_container_width=True)
    with right:
        tbl = d.sort_values("total_p100", ascending=False)[
            ["team_abbrev", "fga", "pps", "fg3a_rate", "selection_p100",
             "making_p100", "total_p100"]].copy()
        tbl.columns = ["Team", "FGA", "Pts/shot", "3PA rate", "Selection /100",
                       "Making /100", "Total /100"]
        st.dataframe(
            tbl.style.format({"FGA": "{:.0f}", "Pts/shot": "{:.3f}",
                              "3PA rate": "{:.1%}", "Selection /100": "{:+.2f}",
                              "Making /100": "{:+.2f}", "Total /100": "{:+.2f}"})
               .background_gradient(subset=["Selection /100"], cmap="RdBu",
                                    vmin=-7, vmax=7)
               .background_gradient(subset=["Making /100"], cmap="RdBu",
                                    vmin=-7, vmax=7),
            use_container_width=True, hide_index=True, height=560)

    st.subheader("League shot diet")
    lz = D.table("league_zone")
    l = lz[lz["SEASON"] == season].copy()
    l["zone"] = pd.Categorical(l["zone"], ZONE_ORDER, ordered=True)
    l = l.sort_values("zone")[["zone", "att", "share", "league_fg_pct", "league_ppa"]]
    l.columns = ["Zone", "Attempts", "Share of league shots", "FG%", "Points per attempt"]
    st.dataframe(l.style.format({"Attempts": "{:,.0f}", "Share of league shots": "{:.1%}",
                                 "FG%": "{:.1%}", "Points per attempt": "{:.3f}"}),
                 use_container_width=True, hide_index=True)


# ==========================================================================
# 5. method
# ==========================================================================
else:
    st.title("Method & validation")

    st.subheader("The decomposition")
    st.markdown(
        '<div class="callout">For every attempt, a model estimates the probability a '
        '<i>league-average</i> shooter converts it, which times the shot\'s point value '
        'gives expected points per shot (xPPS). Averaged over a player\'s season:'
        '<br><br><code>PPS − league PPS  =  (xPPS − league PPS)  +  (PPS − xPPS)</code>'
        '<br><br>The first term is <b>shot selection</b> — what the diet is worth in '
        'average hands. The second is <b>shot making</b> — what the shooter added on '
        'top. They sum exactly to the player\'s efficiency above league average.</div>',
        unsafe_allow_html=True)

    st.subheader("Model")
    st.markdown(
        '<p class="lede">Gradient-boosted trees over shot geometry (x, y, distance, '
        'angle off-centre), clock state (period, seconds left), venue, season, and '
        'the play type recorded in <code>ACTION_TYPE</code>. Two versions are fit: '
        '<b>xPPS-loc</b> uses geometry only; <b>xPPS-full</b> adds play type and is '
        'used for the headline split, on the reasoning that whether a shot is a cut, '
        'a pull-up or a turnaround fadeaway is a property of the offence rather than '
        'of the shooter\'s touch.</p>', unsafe_allow_html=True)

    m = D.table("model_metrics").copy()
    m.columns = ["Model", "Log loss", "Brier", "AUC", "Log-loss gain vs base rate (%)"]
    st.dataframe(m.style.format({"Log loss": "{:.4f}", "Brier": "{:.4f}", "AUC": "{:.3f}",
                                 "Log-loss gain vs base rate (%)": "{:.2f}"}),
                 use_container_width=True, hide_index=True)

    a, b = st.columns([1, 1], gap="large")
    with a:
        st.plotly_chart(C.calibration_plot(D.table("calibration")),
                        use_container_width=True)
        cal = SUM.get("calibration", {})
        st.markdown(
            f'<p class="note">Calibration matters more than discrimination here: an '
            f'uncalibrated model would not make the decomposition add up. Across all '
            f'{SUM.get("n_shots", 0):,} shots the model\'s expected points sit '
            f'<b>{cal.get("calibration_gap_p100", 0):+.3f}</b> points per 100 from '
            f'actual scoring, and the worst of twenty probability bins is off by '
            f'{cal.get("max_calibration_bin_error", 0):.3f}.</p>',
            unsafe_allow_html=True)
    with b:
        st.markdown("**Guards against fooling ourselves**")
        st.markdown(
            f"""
- **No player grades himself.** Every prediction used to evaluate a player is
  out-of-fold, and the folds are grouped by player ID — the model scoring a
  player has never seen one of his shots. Without this, a high-volume specialist
  partly sets his own benchmark.
- **Clock-management shots removed.** {SUM.get('n_excluded_backcourt_or_heave', 0):,}
  backcourt attempts and buzzer heaves are dropped; they are not shot selection.
- **Zones kept coarse on purpose.** An earlier ten-zone scheme split left from
  right, and the empirical-Bayes prior strength swung from k = 199 on one wing to
  k = 2018 on the other for the same shot — binomial noise, not a real talent
  difference. Six zones keep every bucket well sampled.
- **Rates are shrunk, not trusted.** Player zone rates are blended toward the
  league by a method-of-moments beta-binomial prior, so only the spread that
  exceeds binomial noise is treated as talent.
- **The prescriptive tool is graded out of sample** against the following
  season, with two controls, below.
            """)

    st.divider()
    st.subheader("Out-of-sample test of the optimiser")
    st.plotly_chart(C.backtest_dots(D.table("backtest_summary")),
                    use_container_width=True)
    bt = D.table("backtest_summary").copy()
    bt.columns = ["Comparison", "Mean pts/100", "CI low", "CI high",
                  "% of players positive", "n"]
    st.dataframe(bt.style.format({"Mean pts/100": "{:+.3f}", "CI low": "{:+.3f}",
                                  "CI high": "{:+.3f}",
                                  "% of players positive": "{:.1f}", "n": "{:,.0f}"}),
                 use_container_width=True, hide_index=True)
    st.markdown(
        '<p class="note">Each season\'s prescription is scored on the player\'s '
        '<i>next</i> season observed zone rates, so all four variants are graded on the '
        'same future. 95% CIs from 2,000 bootstrap resamples over players.</p>',
        unsafe_allow_html=True)

    try:
        sens = D.table("sensitivity_backtest")
        gaps = D.table("sensitivity_gaps")
        with st.expander("Robustness: is the null just a tight constraint?"):
            st.markdown(
                "The headline null — personalising the prescription adds nothing — "
                "would be an artefact if the move budget were so small that every "
                "variant made the same move. It is not. The null holds from a 3% to a "
                "20% budget, while the empirical-Bayes and league-average "
                "prescriptions genuinely disagree for about half the league.")
            k = sens[sens["comparison"].isin(["EB vs. league-average advice",
                                              "EB vs. unshrunk"])].copy()
            k = k[["move_budget", "comparison", "mean_p100", "ci_low", "ci_high"]]
            k.columns = ["Move budget", "Comparison", "Mean pts/100", "CI low", "CI high"]
            st.dataframe(k.style.format({"Move budget": "{:.0%}", "Mean pts/100": "{:+.3f}",
                                         "CI low": "{:+.3f}", "CI high": "{:+.3f}"}),
                         use_container_width=True, hide_index=True)
            g = gaps.copy()
            g.columns = ["Move budget", "Median gap between the two prescriptions (%)",
                         "% identical", "90th percentile gap (%)"]
            st.dataframe(g.style.format({"Move budget": "{:.0%}",
                                         "Median gap between the two prescriptions (%)": "{:.2f}",
                                         "% identical": "{:.1f}",
                                         "90th percentile gap (%)": "{:.1f}"}),
                         use_container_width=True, hide_index=True)
    except Exception:
        pass

    st.divider()
    st.subheader("What this cannot see")
    st.markdown("""
- **No defender.** The public feed carries no defender distance or closeout data,
  so "selection" here means shot location, play type and clock — not whether the
  shot was open. Some of what lands in *making* is really a player's ability to
  generate separation, which is itself a skill the model cannot attribute.
- **Play type is a coarse proxy.** `ACTION_TYPE` is recorded by human scorers and
  its categories blur (a "Driving Floating Jump Shot" covers a lot of ground).
- **No free throws, no fouls.** A shot diet that draws more fouls is undervalued
  here; three-point-heavy diets are mildly flattered for the same reason.
- **The optimiser assumes zone rates hold under reallocation.** Shifting volume
  changes defensive attention; the marginal corner three is not the average one.
  The 5% default move budget is deliberately small to keep that assumption honest.
- **Selection is not free.** Telling a guard to take fewer pull-ups only works if
  someone else can generate the shot. The number says what it is worth, not
  whether the roster can do it.
    """)

    st.subheader("Data")
    st.markdown(
        f'<p class="note">{SUM.get("n_shots", 0):,} regular-season field goal attempts '
        f'across {", ".join(SUM.get("seasons", []))}, pulled from the public '
        f'stats.nba.com <code>shotchartdetail</code> endpoint. That endpoint silently '
        f'truncates any response at 102,400 rows, so a whole-season request returns '
        f'roughly the first half of the season with no error; the loader pages by '
        f'calendar month and asserts no chunk reaches the cap. '
        f'Pipeline runtime {SUM.get("runtime_minutes", 0)} minutes.</p>',
        unsafe_allow_html=True)
