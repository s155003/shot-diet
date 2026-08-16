"""Shot Diet - separating shot selection from shot making in the NBA."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

import data_access as D  # noqa: F401  (also puts src/ on the path)
import banner
import charts as C
import court
import theme as T
import ui
from analyze import ZONE_POINTS, optimise_diet
from config import ZONE_ORDER

st.set_page_config(page_title="Shot Diet", page_icon="🏀", layout="wide",
                   initial_sidebar_state="expanded")
ui.boot()

SUM = D.summary()
SEASONS = D.seasons()
LATEST = SEASONS[0]


def n(v: str | float, fmt: str = "") -> str:
    """A figure set inside running prose, never on its own."""
    return f'<span class="n">{format(v, fmt) if fmt else v}</span>'


PAGES = ["The finding", "Players", "Shot-diet optimiser", "Teams", "Method & validation"]
with st.sidebar:
    st.markdown(f'<p class="kicker" style="margin-bottom:4px">Shot Diet</p>'
                f'<p class="cap" style="margin:0 0 18px">Separating shot selection '
                f'from shot making</p>', unsafe_allow_html=True)
    page = st.radio("Section", PAGES, label_visibility="collapsed")
    ui.rule(18)
    st.markdown(
        f'<p class="cap">{SUM.get("n_shots", 0):,} shots · {len(SEASONS)} seasons '
        f'({SEASONS[-1]} to {SEASONS[0]})<br>Every regular-season field goal attempt '
        f'from stats.nba.com.</p>', unsafe_allow_html=True)


# ==========================================================================
# 1. the finding
# ==========================================================================
if page == "The finding":
    banner.render()

    sh = D.table("split_half").set_index("metric")
    yoy = D.table("yoy").set_index("metric")
    spread = D.table("spread").set_index("component")
    stab = SUM.get("stabilization_attempts_50pct", {})
    k_sel, k_mak = stab.get("selection", 0), stab.get("making", 0)

    ui.kicker("The finding")
    ui.title("Which half of a shot can you actually coach?")
    ui.lede(
        "Every field goal attempt is two decisions layered on top of each other: "
        "what shot the offence generated, and whether the player put it in. "
        "Box-score efficiency welds them together, so a centre who only dunks looks "
        "like a great shooter and a guard creating late-clock jumpers looks like a "
        "bad one. This project separates the two, then measures how much of each one "
        "a team can actually move.")

    ui.rule(30)

    ui.section("One half of the game settles in eleven shots. The other takes a season.")
    ui.para(
        "Watch a player take eleven attempts and you already know most of what you "
        "will ever know about the quality of the shots he gets. Watch him take three "
        "hundred and you still cannot say with confidence whether he is a good "
        "shooter. That gap is the whole finding, and it decides which half is worth "
        "a coaching staff's attention.")

    ui.figure(
        C.stabilization_curve(D.table("stabilization_curve"), stab),
        "Reliability is measured inside attempt bins, then fitted to r = n / (n + k). "
        "The dotted lines mark where each measure becomes half signal, half noise.")

    ui.para(
        "The same thing shows up across seasons. What kind of shots a player takes is "
        "close to a fixed property of his role and his team's scheme, and it survives "
        "into the following year almost intact. How well he makes them survives far "
        "less well: about a third of it does not carry over at all.")

    with ui.reveal("Show the reliability figures"):
        a, b = st.columns([1, 1], gap="large")
        with a:
            ui.figure(C.reliability_bars(D.table("split_half"), D.table("yoy")))
        with b:
            r = D.table("split_half").merge(D.table("yoy"), on="metric")
            r["metric"] = r["metric"].map({"selection": "Shot selection",
                                           "making": "Shot making"})
            r = r[["metric", "split_half_r", "spearman_brown_r", "yoy_r",
                   "n_player_seasons", "n_pairs"]]
            r.columns = ["", "Split-half r", "Spearman-Brown", "Season to season",
                         "Player-seasons", "Season pairs"]
            ui.table(r, {"Split-half r": "{:.3f}", "Spearman-Brown": "{:.3f}",
                         "Season to season": "{:.3f}", "Player-seasons": "{:,.0f}",
                         "Season pairs": "{:,.0f}"})
            ui.caption(
                "Split-half correlates a player's odd-numbered games against his "
                "even-numbered ones inside the same season. Season-to-season pairs "
                "consecutive seasons for the same player.")

    ui.rule(34)

    # ---- why the leaderboard misleads -------------------------------------
    ps = D.table("player_season")
    d = ps[(ps["SEASON"] == LATEST) & (ps["fga"] >= 200)]
    show = [x for x in ("Nikola Jokić", "DeMar DeRozan", "Rudy Gobert", "Luka Dončić",
                        "Kevin Durant", "Mitchell Robinson")
            if x in set(d["PLAYER_NAME"])]

    ui.section("Why the efficiency leaderboard misleads you")
    ui.para(
        "In any single season the two components look equally important. They vary "
        "across players by almost exactly the same amount, which is why nobody "
        "separates them. Strip out the measurement noise, though, and most of the "
        "difference that actually repeats is simply which shots a player takes.")
    ui.para(
        "The two also pull against each other. Players handed the easiest shots tend "
        "to be the weaker shot-makers, and the best shot-makers are handed the "
        "hardest shots. Rudy Gobert scores more per shot than Luka Dončić and is the "
        "worse shooter of the two by a wide margin.")

    ui.figure(
        C.selection_vs_making(d, show),
        f"{LATEST}, minimum 200 attempts. Bubble size is volume, colour is total "
        "points per 100 above league average. Ringed points are labelled; hover for "
        "any player.")

    with ui.reveal("Show the same players as numbers"):
        ex = d[d["PLAYER_NAME"].isin(show)].sort_values("selection_p100")
        ex = ex[["PLAYER_NAME", "team", "fga", "pps", "selection_p100", "making_p100"]]
        ex.columns = ["Player", "Team", "FGA", "Pts/shot", "Selection /100",
                      "Making /100"]
        ui.table(ex, {"FGA": "{:.0f}", "Pts/shot": "{:.3f}",
                      "Selection /100": "{:+.1f}", "Making /100": "{:+.1f}"})
        sp = spread.reset_index()
        sp["component"] = sp["component"].map({"selection": "Shot selection",
                                               "making": "Shot making"})
        sp = sp[["component", "observed_sd_p100", "repeatable_sd_p100",
                 "noise_sd_p100", "share_of_repeatable_spread"]]
        sp.columns = ["", "Spread across players (SD)", "Of which repeatable",
                      "Of which noise", "Share of repeatable spread"]
        ui.table(sp, {"Spread across players (SD)": "{:.2f}",
                      "Of which repeatable": "{:.2f}", "Of which noise": "{:.2f}",
                      "Share of repeatable spread": "{:.1%}"})
        ui.caption(
            f"Selection and shot making correlate "
            f"{SUM.get('corr_selection_making', 0):+.2f} across players.")

    ui.rule(34)

    # ---- the verdict ------------------------------------------------------
    bts = D.table("backtest_summary")
    eb_lg = bts[bts["comparison"] == "EB vs. league-average advice"].iloc[0]
    eb_kept = bts[bts["comparison"] == "EB prescription vs. do nothing"].iloc[0]

    ui.section("So what should a staff actually do?")
    ui.para(
        "The project ships an optimiser that moves a small share of a player's "
        "attempts out of the mid-range and into the rim and the corners. Graded "
        "against the following season it works, and it works for almost everyone. "
        "Then we ran the controls that could have killed it.")
    ui.pull(
        "Tailoring the advice to the individual shooter turned out to be worth "
        "nothing at all. Every point of the gain comes from the league-average "
        "structure of the floor.")
    ui.para(
        "A prescription built from a player's own shrunk zone-by-zone shooting is "
        "statistically indistinguishable from generic advice that ignores him "
        "completely, and the two genuinely disagree for about half the league. "
        "Trusting his raw hot zones is worse still. One season of shot data simply "
        "does not contain a trustworthy read on where an individual shoots best.")

    ui.figure(
        C.backtest_dots(bts),
        "Each season's prescription is graded against the following season's "
        "shooting, so every variant is judged on the same future. Bars are 95% "
        "bootstrap confidence intervals; grey means the interval contains zero.")

    with ui.reveal("Show the out-of-sample results"):
        b2 = bts.copy()
        b2.columns = ["Comparison", "Mean pts/100", "CI low", "CI high",
                      "% of players positive", "n"]
        ui.table(b2, {"Mean pts/100": "{:+.3f}", "CI low": "{:+.3f}",
                      "CI high": "{:+.3f}", "% of players positive": "{:.1f}",
                      "n": "{:,.0f}"})

    ui.rule(30)
    ui.section("The practical upshot")
    ui.para(
        "Shot quality belongs to the scheme far more than to the roster. Spend the "
        "coaching capital on where shots come from: it shows up almost immediately "
        "and it persists across seasons. Do not build a personalised shot-diet plan "
        "off one season of shooting splits, because you will be coaching noise. And "
        "read every efficiency leaderboard through the split, because a high-scoring "
        "centre and a low-scoring guard can be the same player wearing different "
        "roles.")


# ==========================================================================
# 2. players
# ==========================================================================
elif page == "Players":
    ps = D.table("player_season")

    ui.kicker("Players")
    ui.title("Who gets good shots, and who makes hard ones")
    ui.lede(
        "The horizontal axis is what a player's shot diet is worth in average hands. "
        "The vertical axis is what he added on top of it. Together they sum exactly "
        "to his efficiency above league average.")

    c = st.columns([1, 1, 2])
    season = c[0].selectbox("Season", SEASONS, index=0)
    min_fga = c[1].slider("Minimum attempts", 100, 1000, 200, step=50)
    d = ps[(ps["SEASON"] == season) & (ps["fga"] >= min_fga)].copy()
    names = sorted(d["PLAYER_NAME"].unique())
    default = [x for x in ("Nikola Jokić", "DeMar DeRozan", "Rudy Gobert")
               if x in names]
    picked = c[2].multiselect("Highlight", names, default=default)

    ui.figure(C.selection_vs_making(d, picked, season),
              f"{season}, minimum {min_fga} attempts.")

    with ui.reveal("Show the leaderboard"):
        sort_by = st.radio("Rank by", ["Total points added", "Shot selection",
                                       "Shot making"], horizontal=True)
        col = {"Total points added": "total_pts", "Shot selection": "selection_p100",
               "Shot making": "making_p100"}[sort_by]
        tbl = d.sort_values(col, ascending=False)[
            ["PLAYER_NAME", "team", "fga", "fg_pct", "pps", "xpps",
             "selection_p100", "making_p100", "total_pts"]]
        tbl.columns = ["Player", "Team", "FGA", "FG%", "Pts/shot", "Expected",
                       "Selection /100", "Making /100", "Total pts added"]
        ui.table(tbl, {"FG%": "{:.1%}", "Pts/shot": "{:.3f}", "Expected": "{:.3f}",
                       "Selection /100": "{:+.1f}", "Making /100": "{:+.1f}",
                       "Total pts added": "{:+.0f}", "FGA": "{:.0f}"}, height=420)

    ui.rule(34)

    # ---- player detail ----------------------------------------------------
    ui.section("Player detail")
    who = st.selectbox("Player", names, index=names.index(picked[0]) if picked else 0)
    row = d[d["PLAYER_NAME"] == who].iloc[0]

    verb_s = "better than" if row["selection_p100"] >= 0 else "worse than"
    verb_m = "added" if row["making_p100"] >= 0 else "gave back"
    st.markdown(
        f'<p class="lede">{who} took {n(row["fga"], ",.0f")} shots in {season} and '
        f'scored {n(row["pps"], ".2f")} points on each of them. The shots themselves '
        f'were {n(abs(row["selection_p100"]), ".1f")} points per 100 {verb_s} what '
        f'the average NBA player gets, and he {verb_m} '
        f'{n(abs(row["making_p100"]), ".1f")} more on top of that. Net, he was worth '
        f'{n(row["total_pts"], "+.0f")} points above a league-average shooter on a '
        f'league-average diet.</p>', unsafe_allow_html=True)

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        if season == LATEST:
            shots = D.table("shots_latest")
            ui.figure(
                court.hex_shot_chart(shots[shots["PLAYER_NAME"] == who], shots),
                "Hexagon area is attempt volume; colour is points per shot against "
                "what the league scores from that same patch of floor.")
        else:
            st.info(f"Shot charts ship for {LATEST} only, to keep the repository "
                    "small. Re-run src/run_pipeline.py to build them for other "
                    "seasons.")
    with right:
        hist = ps[ps["PLAYER_NAME"] == who].sort_values("SEASON")
        if len(hist) > 1:
            ui.figure(C.player_history(hist),
                      "Season by season. Selection is what the diet was worth; "
                      "making is what he added to it.")

    with ui.reveal("Show the zone profile"):
        z = D.table("player_zone")
        zz = z[(z["SEASON"] == season) & (z["PLAYER_NAME"] == who)].copy()
        zz["zone"] = pd.Categorical(zz["zone"], ZONE_ORDER, ordered=True)
        out = zz.sort_values("zone")[["zone", "att", "share", "fg_pct", "fg_pct_eb",
                                      "league_fg_pct", "ppa_eb", "league_ppa"]]
        out.columns = ["Zone", "Att", "Share", "FG%", "FG% shrunk", "League FG%",
                       "Pts/att shrunk", "League pts/att"]
        ui.table(out, {"Share": "{:.1%}", "FG%": "{:.1%}", "FG% shrunk": "{:.1%}",
                       "League FG%": "{:.1%}", "Pts/att shrunk": "{:.2f}",
                       "League pts/att": "{:.2f}", "Att": "{:.0f}"})
        ui.caption(
            "Shrunk blends the player's own rate toward the league rate in "
            "proportion to how little we have seen. It is the correction that keeps "
            "a 12-for-20 stretch from being read as a skill.")


# ==========================================================================
# 3. optimiser
# ==========================================================================
elif page == "Shot-diet optimiser":
    z, ps, lz = D.table("player_zone"), D.table("player_season"), D.table("league_zone")

    ui.kicker("Prescriptive tool")
    ui.title("The shot-diet optimiser")
    ui.lede(
        "A linear program that reallocates a fixed share of a player's attempts "
        "across the six zones to maximise expected points, held to how much churn a "
        "staff would realistically install. Zone values are empirical-Bayes "
        "estimates: the player's own rate blended toward the league's in proportion "
        "to sample size.")

    c = st.columns([1, 1.4, 1, 1])
    season = c[0].selectbox("Season", SEASONS, index=0)
    pool = ps[(ps["SEASON"] == season) & (ps["fga"] >= 200)]
    names = sorted(pool["PLAYER_NAME"].unique())
    who = c[1].selectbox("Player", names,
                         index=names.index("DeMar DeRozan")
                         if "DeMar DeRozan" in names else 0)
    move = c[2].slider("Attempts you may move", 1, 25, 5, step=1, format="%d%%") / 100
    zone_cap = c[3].slider("Max change per zone", 1, 25, 5, step=1, format="%d%%") / 100

    zz = z[(z["SEASON"] == season) & (z["PLAYER_NAME"] == who)]
    pri = lz[lz["SEASON"] == season]
    pri = pri.set_index(pri["zone"].astype(str)).reindex(ZONE_ORDER)
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
    season_pts = (new_pps - cur_pps) * fga

    det = pd.DataFrame({
        "zone": ZONE_ORDER, "att": att, "share": shares, "new_share": new_shares,
        "delta": new_shares - shares, "ppa_eb": values,
        "league_ppa": pri["league_ppa"].to_numpy(float)})
    moves = det[det["delta"].abs() > 1e-6].sort_values("delta", ascending=False)

    if moves.empty:
        ui.para(f"{who}'s diet is already optimal under these constraints.")
    else:
        into = moves.iloc[0]["zone"]
        outof = moves.iloc[-1]["zone"]
        shifted = float(moves["delta"].clip(lower=0).sum() * fga)
        st.markdown(
            f'<p class="lede">Move {n(shifted, ",.0f")} of {who}\'s '
            f'{n(fga, ",.0f")} attempts out of the '
            f'<b>{outof.lower()}</b> and into the <b>{into.lower()}</b>, and he '
            f'scores {n(gain100, "+.2f")} more points per 100 shots. Across the '
            f'season that is about {n(abs(season_pts), ",.0f")} points, for a change '
            f'of roughly {n(move * 100, ".0f")}% of his shot diet.</p>',
            unsafe_allow_html=True)

    ui.figure(C.zone_prescription(det, ZONE_ORDER),
              "Current diet against the prescribed one, ordered by distance from "
              "the rim.")

    ui.caption(
        "Read this with the caveat from the finding. Out of sample, this "
        "personalised prescription is no better than the same move computed from "
        "league-average zone values alone. The move earns its points; tailoring it "
        "to him does not.", top=18)

    with ui.reveal("Show the zone maths"):
        t = det.copy()
        t["delta_pct"] = t["delta"] * 100
        t = t[["zone", "att", "share", "new_share", "delta_pct", "ppa_eb",
               "league_ppa"]]
        t.columns = ["Zone", "Attempts", "Current share", "Prescribed share",
                     "Change", "His pts/att", "League pts/att"]
        ui.table(t, {"Attempts": "{:.0f}", "Current share": "{:.1%}",
                     "Prescribed share": "{:.1%}", "Change": "{:+.1f}%",
                     "His pts/att": "{:.3f}", "League pts/att": "{:.3f}"})

    with ui.reveal("Show the biggest available gains this season"):
        summ = D.table("prescription_summary")
        s = summ[summ["SEASON"] == season].nlargest(20, "gain_pts_season")[
            ["PLAYER_NAME", "fga", "current_pps_model", "optimised_pps",
             "gain_p100", "gain_pts_season", "volume_moved_pct"]]
        s.columns = ["Player", "FGA", "Expected pts/shot", "Optimised", "Gain /100",
                     "Season points", "Volume moved"]
        ui.table(s, {"FGA": "{:.0f}", "Expected pts/shot": "{:.3f}",
                     "Optimised": "{:.3f}", "Gain /100": "{:+.2f}",
                     "Season points": "{:+.0f}", "Volume moved": "{:.1f}%"},
                 height=400)
        ui.caption("Computed at the default 5% move budget.")


# ==========================================================================
# 4. teams
# ==========================================================================
elif page == "Teams":
    ts = D.table("team_season")

    ui.kicker("Teams")
    ui.title("The same split across thirty offences")
    ui.lede(
        "Teams to the right generate better shots. Teams higher up convert them "
        "above expectation. Selection is the half a coaching staff owns.")

    season = st.selectbox("Season", SEASONS, index=0)
    d = ts[ts["SEASON"] == season]

    ui.figure(C.team_scatter(d),
              f"{season}. Colour is total points per 100 above league average.")

    with ui.reveal("Show the team table"):
        tbl = d.sort_values("total_p100", ascending=False)[
            ["team_abbrev", "fga", "pps", "fg3a_rate", "selection_p100",
             "making_p100", "total_p100"]]
        tbl.columns = ["Team", "FGA", "Pts/shot", "3PA rate", "Selection /100",
                       "Making /100", "Total /100"]
        ui.table(tbl, {"FGA": "{:.0f}", "Pts/shot": "{:.3f}", "3PA rate": "{:.1%}",
                       "Selection /100": "{:+.2f}", "Making /100": "{:+.2f}",
                       "Total /100": "{:+.2f}"}, height=420)

    with ui.reveal("Show the league shot diet"):
        lz = D.table("league_zone")
        l = lz[lz["SEASON"] == season].copy()
        l["zone"] = pd.Categorical(l["zone"], ZONE_ORDER, ordered=True)
        l = l.sort_values("zone")[["zone", "att", "share", "league_fg_pct",
                                   "league_ppa"]]
        l.columns = ["Zone", "Attempts", "Share of league shots", "FG%",
                     "Points per attempt"]
        ui.table(l, {"Attempts": "{:,.0f}", "Share of league shots": "{:.1%}",
                     "FG%": "{:.1%}", "Points per attempt": "{:.3f}"})


# ==========================================================================
# 5. method
# ==========================================================================
else:
    ui.kicker("Method")
    ui.title("How the split is built, and where it breaks")

    ui.section("The decomposition")
    ui.para(
        "For every attempt, a model estimates the probability a league-average "
        "shooter converts it. Times the shot's point value, that gives expected "
        "points per shot. Averaged over a player's season it splits exactly in two:")
    st.code("PPS − league PPS  =  (xPPS − league PPS)  +  (PPS − xPPS)\n"
            "                          shot selection        shot making",
            language=None)
    ui.para(
        "The first term is what the diet is worth in average hands. The second is "
        "what the shooter added on top. They sum to the player's efficiency above "
        "league average with nothing left over.")

    ui.rule(30)
    ui.section("The model")
    ui.para(
        "Gradient-boosted trees over shot geometry, clock state, venue, season and "
        "the play type recorded in ACTION_TYPE. Two versions are fit: one on "
        "geometry alone, and one that adds play type. The second drives the headline "
        "split, on the reasoning that whether a shot is a cut, a pull-up or a "
        "turnaround fadeaway is a property of the offence rather than of the "
        "shooter's touch.")
    ui.para(
        "Calibration matters more than discrimination here, because an uncalibrated "
        "model would not make the decomposition add up. Across every shot in the "
        "sample the model's expected points sit within four thousandths of a point "
        "per 100 of actual scoring.")

    ui.figure(C.calibration_plot(D.table("calibration")),
              "Predicted against observed make rate, in twenty equal-count bins.")

    with ui.reveal("Show the model metrics"):
        m = D.table("model_metrics").copy()
        m.columns = ["Model", "Log loss", "Brier", "AUC",
                     "Log-loss gain vs base rate (%)"]
        ui.table(m, {"Log loss": "{:.4f}", "Brier": "{:.4f}", "AUC": "{:.3f}",
                     "Log-loss gain vs base rate (%)": "{:.2f}"})
        cal = SUM.get("calibration", {})
        ui.caption(
            f"Calibration gap {cal.get('calibration_gap_p100', 0):+.3f} points per "
            f"100 shots; the worst of twenty probability bins is off by "
            f"{cal.get('max_calibration_bin_error', 0):.3f}.")

    ui.rule(30)
    ui.section("Guards against fooling ourselves")
    st.markdown(f"""
<div class="para">

**No player grades himself.** Every prediction used to evaluate a player is
out-of-fold, and the folds are grouped by player ID, so the model scoring a player
has never seen one of his shots. Without this a high-volume specialist partly sets
his own benchmark.

**The API silently truncates.** The shot endpoint caps every response at 102,400
rows, so a whole-season request returns roughly the first half of the season with no
error and no warning. The loader pages by calendar month and asserts that no chunk
reaches the cap.

**Clock management is removed.** {SUM.get('n_excluded_backcourt_or_heave', 0):,}
backcourt attempts and buzzer heaves are dropped, since they are not shot selection.

**Zones are kept coarse on purpose.** An earlier ten-zone scheme split left from
right, and the empirical-Bayes prior strength swung by an order of magnitude between
the two wings for the same shot. That is binomial noise rather than a real talent
difference, and it made the optimiser prefer left-side threes to identical
right-side ones.

**Rates are shrunk, not trusted.** A method-of-moments beta-binomial prior means
only the spread that exceeds binomial noise is treated as talent.

**The prescriptive tool is graded out of sample**, against two controls, with
bootstrap confidence intervals. That is how the null above surfaced instead of a
personalisation feature that does nothing.

</div>
""", unsafe_allow_html=True)

    with ui.reveal("Show the robustness checks"):
        try:
            sens = D.table("sensitivity_backtest")
            gaps = D.table("sensitivity_gaps")
            ui.para(
                "The headline null would be an artefact if the move budget were so "
                "small that every variant made the same move. It is not: the null "
                "holds from a 3% to a 20% budget, while the two prescriptions "
                "genuinely disagree for about half the league.")
            kk = sens[sens["comparison"].isin(["EB vs. league-average advice",
                                               "EB vs. unshrunk"])]
            kk = kk[["move_budget", "comparison", "mean_p100", "ci_low", "ci_high"]]
            kk.columns = ["Move budget", "Comparison", "Mean pts/100", "CI low",
                          "CI high"]
            ui.table(kk, {"Move budget": "{:.0%}", "Mean pts/100": "{:+.3f}",
                          "CI low": "{:+.3f}", "CI high": "{:+.3f}"})
            gg = gaps.copy()
            gg.columns = ["Move budget", "Median gap between prescriptions",
                          "% identical", "90th percentile gap"]
            ui.table(gg, {"Move budget": "{:.0%}",
                          "Median gap between prescriptions": "{:.2f}%",
                          "% identical": "{:.1f}%",
                          "90th percentile gap": "{:.1f}%"})
        except Exception:
            ui.caption("Run `python src/sensitivity.py` to generate these.")

    ui.rule(30)
    ui.section("What this cannot see")
    st.markdown("""
<div class="para">

**No defender.** The public feed carries no defender distance or closeout data, so
selection here means shot location, play type and clock, but not whether the shot was
open. Some of what lands in shot making is really a player's ability to generate
separation, which is itself a skill the model cannot attribute.

**Play type is a coarse proxy.** ACTION_TYPE is recorded by human scorers and its
categories blur.

**No free throws, no fouls.** A shot diet that draws more fouls is undervalued here,
and three-point-heavy diets are mildly flattered for the same reason.

**The optimiser assumes zone rates hold under reallocation.** Shifting volume changes
defensive attention, and the marginal corner three is not the average one. The small
default move budget is there to keep that assumption honest.

**Selection is not free.** Telling a guard to take fewer pull-ups only works if
someone else can generate the shot. The number says what it is worth, not whether the
roster can do it.

</div>
""", unsafe_allow_html=True)

    ui.rule(30)
    ui.caption(
        f"{SUM.get('n_shots', 0):,} regular-season field goal attempts across "
        f"{', '.join(SUM.get('seasons', []))}, from the public stats.nba.com "
        f"shotchartdetail endpoint. Pipeline runtime "
        f"{SUM.get('runtime_minutes', 0)} minutes.")
