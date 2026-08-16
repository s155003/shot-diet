"""Shot Diet - separating shot selection from shot making in the NBA."""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

import data_access as D  # noqa: F401  (also puts src/ on the path)
import charts as C
import court
import ui
from analyze import ZONE_POINTS, optimise_diet
from config import ZONE_ORDER

st.set_page_config(page_title="Shot Diet", page_icon="🏀", layout="wide",
                   initial_sidebar_state="expanded")
ui.boot()

SUM = D.summary()
SEASONS = D.seasons()
LATEST = SEASONS[0]
PS = D.table("player_season")


def roster(season: str, min_fga: int = 100) -> list[str]:
    d = PS[(PS["SEASON"] == season) & (PS["fga"] >= min_fga)]
    return sorted(d["PLAYER_NAME"].unique())


def signed(v: float, fmt: str = "+.1f") -> str:
    return format(v, fmt)


def fold(s: str) -> str:
    """Lowercase and strip diacritics, so `jokic` finds `Jokić`."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s.lower())
                   if not unicodedata.combining(ch))


def player_search(names: list[str], key: str, season: str,
                  hint: str = "") -> str | None:
    """Type-to-search with a result list. Returns a name once one is chosen.

    A plain selectbox filters on the exact label, so a reader typing `jokic`
    gets no results for `Nikola Jokić`. Folding both sides fixes that, and the
    result list is closer to how a reference site behaves anyway.
    """
    sel_key, q_key = f"{key}_sel", f"{key}_q"
    chosen = st.session_state.get(sel_key)
    if chosen and chosen not in names:
        chosen = st.session_state[sel_key] = None

    if chosen:
        c1, c2 = st.columns([6, 1])
        c1.markdown(f'<p class="cap" style="margin:6px 0 0">Showing '
                    f'<b style="color:{"#0b0b0b"}">{chosen}</b>, {season}</p>',
                    unsafe_allow_html=True)
        if c2.button("Clear", key=f"{key}_clear"):
            st.session_state[sel_key] = None
            st.session_state[q_key] = ""
            st.rerun()
        return chosen

    q = st.text_input("Search", key=q_key, placeholder="Type a name, e.g. jokic",
                      label_visibility="visible")
    if not q or len(q.strip()) < 2:
        ui.empty(hint or f"Start typing a player's name. Nothing loads until you "
                         f"pick one.<br><br><span style='font-size:.8rem'>"
                         f"{len(names):,} players in {season}.</span>")
        return None

    fq = fold(q.strip())
    hits = [nm for nm in names if fq in fold(nm)]
    if not hits:
        ui.empty(f"No player matching <b>{q}</b> in {season}.")
        return None
    if len(hits) == 1:
        st.session_state[sel_key] = hits[0]
        st.rerun()

    ui.caption(f"{len(hits)} matches", top=10)
    for i, nm in enumerate(hits[:12]):
        r = PS[(PS["SEASON"] == season) & (PS["PLAYER_NAME"] == nm)].iloc[0]
        c = st.columns([3, 1, 1, 1, 1])
        if c[0].button(nm, key=f"{key}_hit{i}", width="stretch"):
            st.session_state[sel_key] = nm
            st.rerun()
        c[1].markdown(f'<p class="cap">{r["team"]}</p>', unsafe_allow_html=True)
        c[2].markdown(f'<p class="cap">{r["fga"]:,.0f} FGA</p>',
                      unsafe_allow_html=True)
        c[3].markdown(f'<p class="cap">{r["pps"]:.3f} pts/shot</p>',
                      unsafe_allow_html=True)
        c[4].markdown(f'<p class="cap">{r["total_pts"]:+.0f} added</p>',
                      unsafe_allow_html=True)
    if len(hits) > 12:
        ui.caption(f"…and {len(hits) - 12} more. Narrow the search.")
    return None


PAGES = ["Search", "Leaders", "Teams", "Shot-diet optimiser", "Findings", "Method"]
with st.sidebar:
    st.markdown(
        '<p class="kicker" style="margin-bottom:2px">Shot Diet</p>'
        '<p class="cap" style="margin:0 0 16px">NBA shot selection vs. shot making'
        '</p>', unsafe_allow_html=True)
    page = st.radio("Section", PAGES, label_visibility="collapsed")
    ui.rule(16)
    st.markdown(
        f'<p class="cap">{SUM.get("n_shots", 0):,} shots · {SEASONS[-1]} to '
        f'{SEASONS[0]}<br>Regular season, stats.nba.com.</p>',
        unsafe_allow_html=True)


# ==========================================================================
# Search: a player page, and nothing at all until one is chosen
# ==========================================================================
if page == "Search":
    ui.kicker("Player search")
    ui.title("Look up a player")
    ui.note("Scoring split into the shots a player got and how well he made them. "
            "Every figure is per 100 shots, against the league average that season.")

    c = st.columns([1, 3.4])
    season = c[0].selectbox("Season", SEASONS, index=0)
    names = roster(season)
    with c[1]:
        who = player_search(names, "search", season)
    if who is None:
        st.stop()

    d = PS[(PS["SEASON"] == season) & (PS["PLAYER_NAME"] == who)]
    row = d.iloc[0]

    ui.rule(18)
    st.markdown(f'<h1 class="h1">{who}</h1>', unsafe_allow_html=True)
    ui.caption(f"{row['team']} · {season} · regular season", top=0)

    ui.statline([
        ("Attempts", f"{row['fga']:,.0f}"),
        ("FG%", f"{row['fg_pct']:.1%}"),
        ("Pts / shot", f"{row['pps']:.3f}"),
        ("Expected", f"{row['xpps']:.3f}"),
        ("Selection /100", signed(row["selection_p100"])),
        ("Making /100", signed(row["making_p100"])),
        ("Points added", signed(row["total_pts"], "+.0f")),
    ])
    ui.caption(
        "Selection is what his shot diet is worth in league-average hands. Making "
        "is what he added on top. The two sum to points added.", top=0)

    left, right = st.columns([1, 1.22], gap="large")
    with left:
        if season == LATEST:
            shots = D.table("shots_latest")
            ui.figure(court.hex_shot_chart(shots[shots["PLAYER_NAME"] == who], shots),
                      "Hexagon area is volume; colour is points per shot against the "
                      "league from that same spot.")
        else:
            ui.empty(f"Shot charts are built for {LATEST} only, to keep the "
                     "repository small. Re-run src/run_pipeline.py for others.")
    with right:
        z = D.table("player_zone")
        zz = z[(z["SEASON"] == season) & (z["PLAYER_NAME"] == who)].copy()
        zz["zone"] = pd.Categorical(zz["zone"], ZONE_ORDER, ordered=True)
        out = zz.sort_values("zone")[["zone", "att", "share", "fg_pct", "fg_pct_eb",
                                      "league_fg_pct", "ppa_eb", "league_ppa"]]
        out.columns = ["Zone", "Att", "Share", "FG%", "FG% adj", "Lg FG%",
                       "Pts/att adj", "Lg pts/att"]
        ui.section("By zone")
        ui.table(out, {"Share": "{:.1%}", "FG%": "{:.1%}", "FG% adj": "{:.1%}",
                       "Lg FG%": "{:.1%}", "Pts/att adj": "{:.2f}",
                       "Lg pts/att": "{:.2f}", "Att": "{:.0f}"})
        ui.caption("Adjusted rates are shrunk toward the league in proportion to "
                   "sample size, so a hot stretch is not read as a skill.")

        hist = PS[PS["PLAYER_NAME"] == who].sort_values("SEASON")
        if len(hist) > 1:
            ui.section("By season")
            ui.figure(C.player_history(hist))

    with ui.reveal("Where he ranks"):
        pool = PS[(PS["SEASON"] == season) & (PS["fga"] >= 200)].copy()
        if row["fga"] >= 200:
            r = []
            for lbl, col, asc in (("Shot selection", "selection_p100", False),
                                  ("Shot making", "making_p100", False),
                                  ("Points added", "total_pts", False),
                                  ("Points per shot", "pps", False)):
                rank = int(pool[col].rank(ascending=asc, method="min")
                           [pool["PLAYER_NAME"] == who].iloc[0])
                r.append({"Measure": lbl, "Rank": f"{rank} of {len(pool):,}",
                          "Value": f"{row[col]:+.2f}" if "p100" in col or
                          col == "total_pts" else f"{row[col]:.3f}"})
            ui.table(pd.DataFrame(r))
            ui.caption(f"Among {len(pool):,} players with 200 or more attempts in "
                       f"{season}.")
        else:
            ui.caption("Ranks are shown for players with 200 or more attempts.")


# ==========================================================================
# Leaders
# ==========================================================================
elif page == "Leaders":
    ui.kicker("Leaders")
    ui.title("Sort the league")

    c = st.columns([1, 1.1, 1.6, 1])
    season = c[0].selectbox("Season", SEASONS, index=0)
    min_fga = c[1].slider("Min attempts", 100, 1200, 300, step=50)
    metric = c[2].selectbox("Sort by", ["Points added", "Shot selection",
                                        "Shot making", "Points per shot",
                                        "Attempts"])
    order = c[3].selectbox("Order", ["High to low", "Low to high"])

    col = {"Points added": "total_pts", "Shot selection": "selection_p100",
           "Shot making": "making_p100", "Points per shot": "pps",
           "Attempts": "fga"}[metric]
    d = PS[(PS["SEASON"] == season) & (PS["fga"] >= min_fga)].copy()
    d = d.sort_values(col, ascending=(order == "Low to high"))
    d.insert(0, "#", range(1, len(d) + 1))

    tbl = d[["#", "PLAYER_NAME", "team", "fga", "fg_pct", "pps", "xpps",
             "selection_p100", "making_p100", "total_pts"]]
    tbl.columns = ["#", "Player", "Tm", "FGA", "FG%", "Pts/shot", "Expected",
                   "Selection /100", "Making /100", "Points added"]
    ui.table(tbl, {"FG%": "{:.1%}", "Pts/shot": "{:.3f}", "Expected": "{:.3f}",
                   "Selection /100": "{:+.1f}", "Making /100": "{:+.1f}",
                   "Points added": "{:+.0f}", "FGA": "{:.0f}"}, height=560)
    ui.caption(f"{len(d):,} players, {season}, minimum {min_fga} attempts. "
               "Click any column header to re-sort.")

    with ui.reveal("Show as a chart"):
        ui.figure(C.selection_vs_making(d.head(400)),
                  "Horizontal is what the diet is worth; vertical is what the "
                  "shooter added.")


# ==========================================================================
# Teams
# ==========================================================================
elif page == "Teams":
    ts = D.table("team_season")
    ui.kicker("Teams")
    ui.title("Thirty offences")

    c = st.columns([1, 1.6, 3])
    season = c[0].selectbox("Season", SEASONS, index=0)
    d = ts[ts["SEASON"] == season]
    team = c[1].selectbox("Team", sorted(d["team_abbrev"].unique()), index=None,
                          placeholder="All teams")

    if team:
        r = d[d["team_abbrev"] == team].iloc[0]
        ui.rule(16)
        st.markdown(f'<h1 class="h1">{team}</h1>', unsafe_allow_html=True)
        ui.caption(f"{season} · regular season", top=0)
        ui.statline([
            ("Attempts", f"{r['fga']:,.0f}"),
            ("Pts / shot", f"{r['pps']:.3f}"),
            ("3PA rate", f"{r['fg3a_rate']:.1%}"),
            ("Selection /100", signed(r["selection_p100"], "+.2f")),
            ("Making /100", signed(r["making_p100"], "+.2f")),
            ("Total /100", signed(r["total_p100"], "+.2f")),
        ])
        roster_t = PS[(PS["SEASON"] == season) & (PS["team"] == team) &
                      (PS["fga"] >= 100)].sort_values("total_pts", ascending=False)
        ui.section("Players")
        rt = roster_t[["PLAYER_NAME", "fga", "pps", "selection_p100",
                       "making_p100", "total_pts"]]
        rt.columns = ["Player", "FGA", "Pts/shot", "Selection /100",
                      "Making /100", "Points added"]
        ui.table(rt, {"FGA": "{:.0f}", "Pts/shot": "{:.3f}",
                      "Selection /100": "{:+.1f}", "Making /100": "{:+.1f}",
                      "Points added": "{:+.0f}"})
    else:
        ui.figure(C.team_scatter(d),
                  "Right is better shot selection; up is better shot making.")
        tbl = d.sort_values("total_p100", ascending=False)[
            ["team_abbrev", "fga", "pps", "fg3a_rate", "selection_p100",
             "making_p100", "total_p100"]]
        tbl.columns = ["Tm", "FGA", "Pts/shot", "3PA rate", "Selection /100",
                       "Making /100", "Total /100"]
        ui.table(tbl, {"FGA": "{:.0f}", "Pts/shot": "{:.3f}", "3PA rate": "{:.1%}",
                       "Selection /100": "{:+.2f}", "Making /100": "{:+.2f}",
                       "Total /100": "{:+.2f}"}, height=420)

    with ui.reveal("League shot diet by zone"):
        lz = D.table("league_zone")
        l = lz[lz["SEASON"] == season].copy()
        l["zone"] = pd.Categorical(l["zone"], ZONE_ORDER, ordered=True)
        l = l.sort_values("zone")[["zone", "att", "share", "league_fg_pct",
                                   "league_ppa"]]
        l.columns = ["Zone", "Attempts", "Share of shots", "FG%", "Pts per attempt"]
        ui.table(l, {"Attempts": "{:,.0f}", "Share of shots": "{:.1%}",
                     "FG%": "{:.1%}", "Pts per attempt": "{:.3f}"})


# ==========================================================================
# Optimiser
# ==========================================================================
elif page == "Shot-diet optimiser":
    z, lz = D.table("player_zone"), D.table("league_zone")

    ui.kicker("Prescriptive tool")
    ui.title("Reallocate a shot diet")
    ui.note("A linear program that moves a capped share of a player's attempts "
            "between zones to maximise expected points.")

    c = st.columns([1, 1, 1, 2.2])
    season = c[0].selectbox("Season", SEASONS, index=0)
    move = c[1].slider("Attempts movable", 1, 25, 5, step=1, format="%d%%") / 100
    zone_cap = c[2].slider("Cap per zone", 1, 25, 5, step=1, format="%d%%") / 100
    names = roster(season, 200)
    with c[3]:
        who = player_search(
            names, "opt", season,
            hint=f"Search a player to generate a prescription.<br><br>"
                 f"<span style='font-size:.8rem'>{len(names):,} qualify in "
                 f"{season} with 200 or more attempts.</span>")
    if who is None:
        st.stop()

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

    det = pd.DataFrame({
        "zone": ZONE_ORDER, "att": att, "share": shares, "new_share": new_shares,
        "delta": new_shares - shares, "ppa_eb": values,
        "league_ppa": pri["league_ppa"].to_numpy(float)})
    moves = det[det["delta"].abs() > 1e-6].sort_values("delta", ascending=False)

    ui.rule(16)
    st.markdown(f'<h1 class="h1">{who}</h1>', unsafe_allow_html=True)
    ui.caption(f"{season} · {fga:,.0f} attempts", top=0)
    ui.statline([
        ("Expected now", f"{cur_pps:.3f}"),
        ("Optimised", f"{new_pps:.3f}"),
        ("Gain /100", signed((new_pps - cur_pps) * 100, "+.2f")),
        ("Season points", signed((new_pps - cur_pps) * fga, "+.0f")),
        ("Shots moved", f"{moves['delta'].clip(lower=0).sum() * fga:,.0f}"),
    ])

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        ui.figure(C.zone_prescription(det, ZONE_ORDER))
    with right:
        ui.section("Prescription")
        if moves.empty:
            ui.note("Already optimal under these constraints.")
        else:
            m = moves[["zone", "delta", "ppa_eb", "league_ppa"]].copy()
            m["shots"] = m["delta"] * fga
            m["delta"] = m["delta"] * 100
            m.columns = ["Zone", "Change", "His pts/att", "Lg pts/att", "Shots"]
            ui.table(m[["Zone", "Change", "Shots", "His pts/att", "Lg pts/att"]],
                     {"Change": "{:+.1f}%", "Shots": "{:+,.0f}",
                      "His pts/att": "{:.3f}", "Lg pts/att": "{:.3f}"})
        ui.caption(
            "Out of sample this personalised prescription is no better than the "
            "same move computed from league-average zone values alone. See "
            "Findings.")

    with ui.reveal("Full zone table"):
        t = det.copy()
        t["delta"] = t["delta"] * 100
        t = t[["zone", "att", "share", "new_share", "delta", "ppa_eb", "league_ppa"]]
        t.columns = ["Zone", "Attempts", "Current", "Prescribed", "Change",
                     "His pts/att", "Lg pts/att"]
        ui.table(t, {"Attempts": "{:.0f}", "Current": "{:.1%}",
                     "Prescribed": "{:.1%}", "Change": "{:+.1f}%",
                     "His pts/att": "{:.3f}", "Lg pts/att": "{:.3f}"})

    with ui.reveal("Biggest available gains this season"):
        summ = D.table("prescription_summary")
        s = summ[summ["SEASON"] == season].nlargest(25, "gain_pts_season")[
            ["PLAYER_NAME", "fga", "current_pps_model", "optimised_pps",
             "gain_p100", "gain_pts_season"]]
        s.columns = ["Player", "FGA", "Expected", "Optimised", "Gain /100",
                     "Season points"]
        ui.table(s, {"FGA": "{:.0f}", "Expected": "{:.3f}", "Optimised": "{:.3f}",
                     "Gain /100": "{:+.2f}", "Season points": "{:+.0f}"}, height=400)
        ui.caption("At the default 5% move budget.")


# ==========================================================================
# Findings
# ==========================================================================
elif page == "Findings":
    stab = SUM.get("stabilization_attempts_50pct", {})
    sh, yoy = D.table("split_half"), D.table("yoy")
    spread = D.table("spread")
    bts = D.table("backtest_summary")

    ui.kicker("Findings")
    ui.title("What the data says")
    ui.note("Three results, each with the evidence behind it.")

    ui.rule(18)
    ui.section("1. Shot selection is knowable almost at once. Shot making is not.")
    ui.statline([
        ("Selection · 50% reliable at", f"{stab.get('selection', 0):.0f} shots"),
        ("Making · 50% reliable at", f"{stab.get('making', 0):.0f} shots"),
        ("Selection · year to year", f"r = {yoy.set_index('metric').loc['selection', 'yoy_r']:.2f}"),
        ("Making · year to year", f"r = {yoy.set_index('metric').loc['making', 'yoy_r']:.2f}"),
    ])
    ui.figure(C.stabilization_curve(D.table("stabilization_curve"), stab),
              "Reliability measured inside attempt bins, fitted to r = n / (n + k).")

    with ui.reveal("Reliability detail"):
        r = sh.merge(yoy, on="metric")
        r["metric"] = r["metric"].map({"selection": "Shot selection",
                                       "making": "Shot making"})
        r = r[["metric", "split_half_r", "spearman_brown_r", "yoy_r",
               "n_player_seasons", "n_pairs"]]
        r.columns = ["", "Split-half r", "Spearman-Brown", "Season to season",
                     "Player-seasons", "Season pairs"]
        ui.table(r, {"Split-half r": "{:.3f}", "Spearman-Brown": "{:.3f}",
                     "Season to season": "{:.3f}", "Player-seasons": "{:,.0f}",
                     "Season pairs": "{:,.0f}"})
        ui.figure(C.reliability_bars(sh, yoy))

    ui.rule(26)
    ui.section("2. Most of the repeatable difference between players is which "
               "shots they take.")
    sp = spread.copy()
    sp["component"] = sp["component"].map({"selection": "Shot selection",
                                           "making": "Shot making"})
    sp = sp[["component", "observed_sd_p100", "repeatable_sd_p100",
             "noise_sd_p100", "share_of_repeatable_spread"]]
    sp.columns = ["", "Spread across players (SD)", "Repeatable", "Noise",
                  "Share of repeatable spread"]
    ui.table(sp, {"Spread across players (SD)": "{:.2f}", "Repeatable": "{:.2f}",
                  "Noise": "{:.2f}", "Share of repeatable spread": "{:.1%}"})
    ui.caption(
        f"The two components correlate {SUM.get('corr_selection_making', 0):+.2f} "
        "across players: easier diets tend to go to the weaker shot-makers.")

    ui.rule(26)
    ui.section("3. Personalising shot-diet advice is worth nothing.")
    ui.note("Each season's prescription is graded against the following season, so "
            "every variant is judged on the same future.")
    ui.figure(C.backtest_dots(bts),
              "95% bootstrap confidence intervals. Grey means the interval "
              "contains zero.")
    b2 = bts.copy()
    b2.columns = ["Comparison", "Mean pts/100", "CI low", "CI high",
                  "% of players positive", "n"]
    ui.table(b2, {"Mean pts/100": "{:+.3f}", "CI low": "{:+.3f}",
                  "CI high": "{:+.3f}", "% of players positive": "{:.1f}",
                  "n": "{:,.0f}"})
    ui.caption(
        "Generic league-average advice matches the personalised version exactly. "
        "Shrinking a player's rates still beats trusting them, and the gap widens "
        "as the optimiser is allowed to move more volume.")

    with ui.reveal("Robustness of the null"):
        try:
            sens, gaps = D.table("sensitivity_backtest"), D.table("sensitivity_gaps")
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
            ui.caption("The null holds from a 3% to a 20% budget, and the two "
                       "prescriptions genuinely differ for about half the league.")
        except Exception:
            ui.caption("Run `python src/sensitivity.py` to generate these.")


# ==========================================================================
# Method
# ==========================================================================
else:
    ui.kicker("Method")
    ui.title("How the split is built")

    st.code("PPS − league PPS  =  (xPPS − league PPS)  +  (PPS − xPPS)\n"
            "                          shot selection        shot making",
            language=None)
    ui.note("A gradient-boosted model estimates what a league-average shooter would "
            "score on each attempt, from shot geometry, clock state, venue, season "
            "and play type. The two terms sum to a player's efficiency above league "
            "average with nothing left over.")

    ui.rule(20)
    ui.section("Model")
    m = D.table("model_metrics").copy()
    m.columns = ["Model", "Log loss", "Brier", "AUC", "Gain vs base rate (%)"]
    ui.table(m, {"Log loss": "{:.4f}", "Brier": "{:.4f}", "AUC": "{:.3f}",
                 "Gain vs base rate (%)": "{:.2f}"})

    a, b = st.columns([1, 1], gap="large")
    with a:
        ui.figure(C.calibration_plot(D.table("calibration")),
                  "Predicted against observed make rate, twenty equal-count bins.")
    with b:
        cal = SUM.get("calibration", {})
        ui.section("Guards")
        st.markdown(f"""
<div class="note">

**Out-of-fold, grouped by player.** The model scoring a player has never seen one
of his shots, so a high-volume specialist cannot set his own benchmark.

**The API truncates silently.** `shotchartdetail` caps responses at 102,400 rows,
returning about half a season with no error. The loader pages by month and asserts
no chunk reaches the cap.

**Clock management removed.** {SUM.get('n_excluded_backcourt_or_heave', 0):,}
backcourt attempts and buzzer heaves dropped.

**Six zones, not ten.** A left/right split made the empirical-Bayes prior swing by
an order of magnitude between wings for the same shot — binomial noise, not talent.

**Rates shrunk, not trusted.** Method-of-moments beta-binomial prior.

**Calibration gap {cal.get('calibration_gap_p100', 0):+.3f}** points per 100 shots
across every attempt in the sample.

</div>
""", unsafe_allow_html=True)

    ui.rule(20)
    ui.section("Limits")
    st.markdown("""
<div class="note">

**No defender.** The public feed has no defender distance, so selection means
location, play type and clock — not whether the shot was open. Some of what lands in
shot making is really the ability to create separation.

**Play type is a coarse, human-scored proxy.**

**No free throws or fouls**, so foul-drawing diets are undervalued.

**The optimiser assumes zone rates hold under reallocation.** The marginal corner
three is not the average one, which is why the default move budget is small.

**Selection is not free.** Fewer pull-ups only works if someone else can create the
shot.

</div>
""", unsafe_allow_html=True)

    ui.rule(20)
    ui.caption(
        f"{SUM.get('n_shots', 0):,} regular-season field goal attempts, "
        f"{', '.join(SUM.get('seasons', []))}, from the public stats.nba.com "
        f"shotchartdetail endpoint. Pipeline runtime "
        f"{SUM.get('runtime_minutes', 0)} minutes.")
