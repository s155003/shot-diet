"""Shot Diet - separating shot selection from shot making in the NBA."""
from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
import streamlit as st

import data_access as D  # noqa: F401  (also puts src/ on the path)
import charts as C
import court
import hero
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


def fold(s: str) -> str:
    """Lowercase and strip diacritics, so `jokic` finds `Jokić`."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s.lower())
                   if not unicodedata.combining(ch))


def player_search(names: list[str], key: str, season: str) -> str | None:
    """Type-to-search with a result list. Returns a name once one is chosen.

    A plain selectbox filters on the exact label, so a reader typing `jokic`
    gets nothing for `Nikola Jokić`. Folding both sides fixes that, and a result
    list is closer to how a reference site behaves anyway.
    """
    sel_key, q_key = f"{key}_sel", f"{key}_q"
    chosen = st.session_state.get(sel_key)
    if chosen and chosen not in names:
        chosen = st.session_state[sel_key] = None

    if chosen:
        c1, c2 = st.columns([6, 1])
        c1.markdown(f'<p class="cap" style="margin:8px 0 0">Showing '
                    f'<b style="color:#0b0b0b">{chosen}</b>, {season}</p>',
                    unsafe_allow_html=True)
        if c2.button("Clear", key=f"{key}_clear"):
            st.session_state[sel_key] = None
            st.session_state[q_key] = ""
            st.rerun()
        return chosen

    q = st.text_input("Search players", key=q_key,
                      placeholder="Type a name, e.g. jokic")
    if not q or len(q.strip()) < 2:
        ui.empty(f"Search any of the {len(names):,} players in {season}. "
                 "Nothing loads until you pick one.")
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
        for col, txt in zip(c[1:], (r["team"], f"{r['fga']:,.0f} FGA",
                                    f"{r['pps']:.3f} pts/shot",
                                    f"{r['total_pts']:+.0f} added")):
            col.markdown(f'<p class="cap">{txt}</p>', unsafe_allow_html=True)
    if len(hits) > 12:
        ui.caption(f"…and {len(hits) - 12} more. Narrow the search.")
    return None


PAGES = ["Players", "Leaders", "Teams", "Findings"]

# Masthead: wordmark on the left, tabs across the top. A sidebar spends a fifth
# of the width on four links and makes the tool feel like a dashboard rather
# than a site you navigate.
bar = st.columns([1.05, 3.4, 1.5], gap="small")
with bar[0]:
    st.markdown('<p class="brand">Shot Diet</p>', unsafe_allow_html=True)
with bar[1]:
    # No selection is the landing page, which keeps the tab bar at four tools
    # rather than spending one of them on "Home".
    page = st.segmented_control("Section", PAGES, default=None,
                                label_visibility="collapsed")
with bar[2]:
    st.markdown(
        f'<p class="barmeta">{SUM.get("n_shots", 0):,} shots · {SEASONS[-1]} '
        f'to {SEASONS[0]}</p>', unsafe_allow_html=True)
st.markdown('<div class="barrule"></div>', unsafe_allow_html=True)


# ==========================================================================
# Players: the landing page. Search, then one player's sheet.
# ==========================================================================
if page is None:
    hero.render()
    st.stop()


if page == "Players":
    ui.kicker("Players")
    ui.title("Look up any NBA player")
    ui.legend([
        ("Selection", "how good the shots he took were"),
        ("Making", "how well he made them, against what an average NBA "
                   "player would"),
        ("Both", "points per 100 shots, versus the league that season"),
    ])

    c = st.columns([1, 3.4])
    season = c[0].selectbox("Season", SEASONS, index=0)
    names = roster(season)
    with c[1]:
        who = player_search(names, "search", season)
    if who is None:
        st.stop()

    row = PS[(PS["SEASON"] == season) & (PS["PLAYER_NAME"] == who)].iloc[0]

    ui.rule(16)
    ui.playerhead(who, f"{row['team']} · {season} · regular season")
    ui.statline([
        ("Attempts", f"{row['fga']:,.0f}"),
        ("FG%", f"{row['fg_pct']:.1%}"),
        ("Pts / shot", f"{row['pps']:.3f}"),
        ("Expected", f"{row['xpps']:.3f}"),
        ("Selection /100", f"{row['selection_p100']:+.1f}"),
        ("Making /100", f"{row['making_p100']:+.1f}"),
        ("Points added", f"{row['total_pts']:+.0f}"),
    ])

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        if season == LATEST:
            shots = D.table("shots_latest")
            ui.figure(court.hex_shot_chart(shots[shots["PLAYER_NAME"] == who], shots),
                      "Hexagon area is volume; colour is points per shot against the "
                      "league from that same spot.")
        else:
            ui.empty(f"Shot charts are built for {LATEST} only, to keep the "
                     "repository small.")
    with right:
        ui.section("By zone")
        z = D.table("player_zone")
        zz = z[(z["SEASON"] == season) & (z["PLAYER_NAME"] == who)].copy()
        zz["zone"] = pd.Categorical(zz["zone"], ZONE_ORDER, ordered=True)
        out = zz.sort_values("zone")[["zone", "att", "share", "fg_pct", "fg_pct_eb",
                                      "league_fg_pct", "ppa_eb", "league_ppa"]]
        out.columns = ["Zone", "Att", "Share", "FG%", "FG% adj", "Lg FG%",
                       "Pts/att", "Lg pts/att"]
        ui.statsheet(out, {"Share": "{:.1%}", "FG%": "{:.1%}", "FG% adj": "{:.1%}",
                           "Lg FG%": "{:.1%}", "Pts/att": "{:.2f}",
                           "Lg pts/att": "{:.2f}", "Att": "{:.0f}"}, left=("Zone",))
        ui.caption("Adjusted rates are shrunk toward the league in proportion to "
                   "sample size, so a hot stretch is not read as a skill.")

        hist = PS[PS["PLAYER_NAME"] == who].sort_values("SEASON")
        if len(hist) > 1:
            ui.section("By season")
            ui.figure(C.player_history(hist))

    # ---- prescription, on the player's own page ---------------------------
    ui.rule(24)
    ui.section("Shot-diet prescription")
    if row["fga"] < 200:
        ui.note("Prescriptions are generated for players with 200 or more attempts.")
    else:
        lz = D.table("league_zone")
        cc = st.columns([1, 1, 3])
        move = cc[0].slider("Attempts movable", 1, 25, 5, step=1,
                            format="%d%%") / 100
        zone_cap = cc[1].slider("Cap per zone", 1, 25, 5, step=1,
                                format="%d%%") / 100

        pri = lz[lz["SEASON"] == season]
        pri = pri.set_index(pri["zone"].astype(str)).reindex(ZONE_ORDER)
        g = zz.set_index(zz["zone"].astype(str)).reindex(ZONE_ORDER)
        att = g["att"].fillna(0.0).to_numpy(float)
        made = g["made"].fillna(0.0).to_numpy(float)
        league_pct = pri["league_fg_pct"].to_numpy(float)
        k = pri["prior_k"].to_numpy(float)
        pt_val = np.array([ZONE_POINTS[zn] for zn in ZONE_ORDER], float)

        shares = att / att.sum()
        eb = (made + k * league_pct) / (att + k)
        values = eb * pt_val
        new_shares = optimise_diet(shares, values, move, zone_cap)
        cur_pps, new_pps = float(shares @ values), float(new_shares @ values)
        fga = float(att.sum())

        det = pd.DataFrame({
            "zone": ZONE_ORDER, "att": att, "share": shares,
            "new_share": new_shares, "delta": new_shares - shares,
            "ppa_eb": values, "league_ppa": pri["league_ppa"].to_numpy(float)})
        moves = det[det["delta"].abs() > 1e-6].sort_values("delta", ascending=False)

        ui.statline([
            ("Expected now", f"{cur_pps:.3f}"),
            ("Optimised", f"{new_pps:.3f}"),
            ("Gain /100", f"{(new_pps - cur_pps) * 100:+.2f}"),
            ("Season points", f"{(new_pps - cur_pps) * fga:+.0f}"),
            ("Shots moved", f"{moves['delta'].clip(lower=0).sum() * fga:,.0f}"),
        ])

        pl, pr = st.columns([1.15, 1], gap="large")
        with pl:
            ui.figure(C.zone_prescription(det, ZONE_ORDER))
        with pr:
            if moves.empty:
                ui.note("Already optimal under these constraints.")
            else:
                m = moves[["zone", "delta", "ppa_eb", "league_ppa"]].copy()
                m["shots"] = m["delta"] * fga
                m["delta"] = m["delta"] * 100
                m = m[["zone", "delta", "shots", "ppa_eb", "league_ppa"]]
                m.columns = ["Zone", "Change", "Shots", "His pts/att", "Lg pts/att"]
                ui.statsheet(m, {"Change": "{:+.1f}", "Shots": "{:+,.0f}",
                                 "His pts/att": "{:.3f}", "Lg pts/att": "{:.3f}"},
                             left=("Zone",), signed_cols=("Change", "Shots"))
            ui.caption(
                "Out of sample this personalised prescription is no better than the "
                "same move computed from league-average zone values alone. See "
                "Findings.")

    with ui.reveal("Where he ranks"):
        pool = PS[(PS["SEASON"] == season) & (PS["fga"] >= 200)]
        if row["fga"] >= 200:
            r = []
            for lbl, col in (("Shot selection", "selection_p100"),
                             ("Shot making", "making_p100"),
                             ("Points added", "total_pts"),
                             ("Points per shot", "pps")):
                rank = int(pool[col].rank(ascending=False, method="min")
                           [pool["PLAYER_NAME"] == who].iloc[0])
                r.append({"Measure": lbl, "Rank": f"{rank} of {len(pool):,}",
                          "Value": f"{row[col]:+.2f}" if col != "pps"
                          else f"{row[col]:.3f}"})
            ui.statsheet(pd.DataFrame(r), left=("Measure", "Rank"))
            ui.caption(f"Among {len(pool):,} players with 200 or more attempts.")
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
    tbl.columns = ["#", "Player", "Tm", "FGA", "FG%", "Pts/shot", "Exp",
                   "Selection", "Making", "Pts added"]
    ui.statsheet(tbl, {"FG%": "{:.1%}", "Pts/shot": "{:.3f}", "Exp": "{:.3f}",
                       "Selection": "{:+.1f}", "Making": "{:+.1f}",
                       "Pts added": "{:+.0f}", "FGA": "{:.0f}"},
                 left=("Player", "Tm"),
                 signed_cols=("Selection", "Making", "Pts added"), height=560)
    ui.caption(f"{len(d):,} players · {season} · minimum {min_fga} attempts. "
               "Selection and making are per 100 shots against the league.")

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
        ui.rule(14)
        ui.playerhead(team, f"{season} · regular season")
        ui.statline([
            ("Attempts", f"{r['fga']:,.0f}"),
            ("Pts / shot", f"{r['pps']:.3f}"),
            ("3PA rate", f"{r['fg3a_rate']:.1%}"),
            ("Selection /100", f"{r['selection_p100']:+.2f}"),
            ("Making /100", f"{r['making_p100']:+.2f}"),
            ("Total /100", f"{r['total_p100']:+.2f}"),
        ])
        ui.section("Players")
        rt = PS[(PS["SEASON"] == season) & (PS["team"] == team) &
                (PS["fga"] >= 100)].sort_values("total_pts", ascending=False)
        rt = rt[["PLAYER_NAME", "fga", "pps", "selection_p100", "making_p100",
                 "total_pts"]]
        rt.columns = ["Player", "FGA", "Pts/shot", "Selection", "Making",
                      "Pts added"]
        ui.statsheet(rt, {"FGA": "{:.0f}", "Pts/shot": "{:.3f}",
                          "Selection": "{:+.1f}", "Making": "{:+.1f}",
                          "Pts added": "{:+.0f}"}, left=("Player",),
                     signed_cols=("Selection", "Making", "Pts added"))
    else:
        ui.figure(C.team_scatter(d),
                  "Right is better shot selection; up is better shot making.")
        tbl = d.sort_values("total_p100", ascending=False)[
            ["team_abbrev", "fga", "pps", "fg3a_rate", "selection_p100",
             "making_p100", "total_p100"]]
        tbl.columns = ["Tm", "FGA", "Pts/shot", "3PA rate", "Selection",
                       "Making", "Total"]
        ui.statsheet(tbl, {"FGA": "{:.0f}", "Pts/shot": "{:.3f}",
                           "3PA rate": "{:.1%}", "Selection": "{:+.2f}",
                           "Making": "{:+.2f}", "Total": "{:+.2f}"},
                     left=("Tm",), signed_cols=("Selection", "Making", "Total"),
                     height=440)

    with ui.reveal("League shot diet by zone"):
        lz = D.table("league_zone")
        l = lz[lz["SEASON"] == season].copy()
        l["zone"] = pd.Categorical(l["zone"], ZONE_ORDER, ordered=True)
        l = l.sort_values("zone")[["zone", "att", "share", "league_fg_pct",
                                   "league_ppa"]]
        l.columns = ["Zone", "Attempts", "Share", "FG%", "Pts per attempt"]
        ui.statsheet(l, {"Attempts": "{:,.0f}", "Share": "{:.1%}",
                         "FG%": "{:.1%}", "Pts per attempt": "{:.3f}"},
                     left=("Zone",))


# ==========================================================================
# Findings (research + method in one place)
# ==========================================================================
else:
    stab = SUM.get("stabilization_attempts_50pct", {})
    sh, yoy = D.table("split_half"), D.table("yoy")
    bts = D.table("backtest_summary")

    ui.kicker("Findings")
    ui.title("What the data says")
    ui.note("Three results, the evidence behind each, and how the split is built.")

    ui.rule(16)
    ui.section("1. Shot selection is knowable almost at once. Shot making is not.")
    ui.statline([
        ("Selection · 50% reliable at", f"{stab.get('selection', 0):.0f} shots"),
        ("Making · 50% reliable at", f"{stab.get('making', 0):.0f} shots"),
        ("Selection · year to year",
         f"r = {yoy.set_index('metric').loc['selection', 'yoy_r']:.2f}"),
        ("Making · year to year",
         f"r = {yoy.set_index('metric').loc['making', 'yoy_r']:.2f}"),
    ])
    ui.figure(C.stabilization_curve(D.table("stabilization_curve"), stab),
              "Reliability measured inside attempt bins, fitted to r = n / (n + k).")

    with ui.reveal("Reliability detail"):
        r = sh.merge(yoy, on="metric")
        r["metric"] = r["metric"].map({"selection": "Shot selection",
                                       "making": "Shot making"})
        r = r[["metric", "split_half_r", "spearman_brown_r", "yoy_r",
               "n_player_seasons", "n_pairs"]]
        r.columns = ["Component", "Split-half r", "Spearman-Brown",
                     "Season to season", "Player-seasons", "Season pairs"]
        ui.statsheet(r, {"Split-half r": "{:.3f}", "Spearman-Brown": "{:.3f}",
                         "Season to season": "{:.3f}",
                         "Player-seasons": "{:,.0f}", "Season pairs": "{:,.0f}"},
                     left=("Component",))
        ui.figure(C.reliability_bars(sh, yoy))

    ui.rule(24)
    ui.section("2. Most of the repeatable difference between players is which "
               "shots they take.")
    sp = D.table("spread").copy()
    sp["component"] = sp["component"].map({"selection": "Shot selection",
                                           "making": "Shot making"})
    sp = sp[["component", "observed_sd_p100", "repeatable_sd_p100",
             "noise_sd_p100", "share_of_repeatable_spread"]]
    sp.columns = ["Component", "Spread (SD)", "Repeatable", "Noise",
                  "Share of repeatable"]
    ui.statsheet(sp, {"Spread (SD)": "{:.2f}", "Repeatable": "{:.2f}",
                      "Noise": "{:.2f}", "Share of repeatable": "{:.1%}"},
                 left=("Component",))
    ui.caption(
        f"The two correlate {SUM.get('corr_selection_making', 0):+.2f} across "
        "players: easier diets tend to go to the weaker shot-makers.")

    ui.rule(24)
    ui.section("3. Personalising shot-diet advice is worth nothing.")
    ui.note("Each season's prescription is graded against the following season, so "
            "every variant is judged on the same future.")
    ui.figure(C.backtest_dots(bts),
              "95% bootstrap confidence intervals. Grey means the interval "
              "contains zero.")
    b2 = bts.copy()
    b2.columns = ["Comparison", "Mean pts/100", "CI low", "CI high",
                  "% positive", "n"]
    ui.statsheet(b2, {"Mean pts/100": "{:+.3f}", "CI low": "{:+.3f}",
                      "CI high": "{:+.3f}", "% positive": "{:.1f}",
                      "n": "{:,.0f}"}, left=("Comparison",),
                 signed_cols=("Mean pts/100",))
    ui.caption(
        "Generic league-average advice matches the personalised version exactly. "
        "Shrinking a player's rates still beats trusting them.")

    with ui.reveal("Robustness of the null"):
        try:
            sens, gaps = D.table("sensitivity_backtest"), D.table("sensitivity_gaps")
            kk = sens[sens["comparison"].isin(["EB vs. league-average advice",
                                               "EB vs. unshrunk"])]
            kk = kk[["move_budget", "comparison", "mean_p100", "ci_low", "ci_high"]]
            kk.columns = ["Move budget", "Comparison", "Mean pts/100", "CI low",
                          "CI high"]
            ui.statsheet(kk, {"Move budget": "{:.0%}", "Mean pts/100": "{:+.3f}",
                              "CI low": "{:+.3f}", "CI high": "{:+.3f}"},
                         left=("Comparison",), signed_cols=("Mean pts/100",))
            ui.caption("The null holds from a 3% to a 20% budget, and the two "
                       "prescriptions genuinely differ for about half the league.")
        except Exception:
            ui.caption("Run `python src/sensitivity.py` to generate these.")

    ui.rule(24)
    ui.section("How the split is built")
    st.code("PPS − league PPS  =  (xPPS − league PPS)  +  (PPS − xPPS)\n"
            "                          shot selection        shot making",
            language=None)
    ui.note("A gradient-boosted model estimates what a league-average shooter "
            "would score on each attempt, from shot geometry, clock state, venue, "
            "season and play type. The two terms sum to a player's efficiency "
            "above league average with nothing left over.")

    with ui.reveal("Model metrics and calibration"):
        m = D.table("model_metrics").copy()
        m.columns = ["Model", "Log loss", "Brier", "AUC", "Gain vs base (%)"]
        ui.statsheet(m, {"Log loss": "{:.4f}", "Brier": "{:.4f}", "AUC": "{:.3f}",
                         "Gain vs base (%)": "{:.2f}"}, left=("Model",))
        ui.figure(C.calibration_plot(D.table("calibration")),
                  "Predicted against observed make rate, twenty equal-count bins.")

    with ui.reveal("Guards against fooling ourselves"):
        cal = SUM.get("calibration", {})
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
an order of magnitude between wings for the same shot. That is binomial noise
rather than a real talent difference.

**Rates shrunk, not trusted.** Method-of-moments beta-binomial prior.

**Calibration gap {cal.get('calibration_gap_p100', 0):+.3f}** points per 100 shots
across every attempt in the sample.

</div>
""", unsafe_allow_html=True)

    with ui.reveal("What this cannot see"):
        st.markdown("""
<div class="note">

**No defender.** The public feed has no defender distance, so selection means
location, play type and clock, but not whether the shot was open. Some of what lands in
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
        f"shotchartdetail endpoint.")
