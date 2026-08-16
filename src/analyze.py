"""Decomposition, reliability analysis and the shot-diet optimiser."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import linprog

from config import (DEFAULT_TOTAL_MOVE, DEFAULT_ZONE_CAP, MIN_FGA,
                    MIN_ZONE_ATT_FOR_PRIOR, ZONE_ORDER)

ZONE_POINTS = {
    "Restricted Area": 2,
    "Paint (Non-RA)": 2,
    "Short Mid-Range (8-16 ft)": 2,
    "Long Mid-Range (16-24 ft)": 2,
    "Corner 3": 3,
    "Above the Break 3": 3,
}
assert set(ZONE_POINTS) == set(ZONE_ORDER)


# ==========================================================================
# 1. the decomposition
# ==========================================================================

def player_season_table(df: pd.DataFrame) -> pd.DataFrame:
    """Split each player-season's scoring rate into selection and making.

        PPS - league_PPS  =  (xPPS - league_PPS)  +  (PPS - xPPS)
                                  selection             making

    Selection is what the shot diet is worth in the hands of a league-average
    shooter. Making is what the shooter added on top of that diet.
    """
    league = df.groupby("SEASON", observed=True)["points"].mean().rename("league_pps")

    g = df.groupby(["SEASON", "PLAYER_ID", "PLAYER_NAME"], observed=True)
    out = g.agg(
        team=("team_abbrev", lambda s: s.mode().iat[0] if len(s.mode()) else s.iat[0]),
        n_teams=("team_abbrev", "nunique"),
        fga=("points", "size"),
        fgm=("SHOT_MADE_FLAG", "sum"),
        pts=("points", "sum"),
        fg3a=("is_three", "sum"),
        xpps=("xpps_full", "mean"),
        xpps_loc=("xpps_loc", "mean"),
    ).reset_index()

    out["pps"] = out["pts"] / out["fga"]
    out["fg_pct"] = out["fgm"] / out["fga"]
    out["fg3a_rate"] = out["fg3a"] / out["fga"]
    out = out.merge(league, on="SEASON")

    out["selection_pps"] = out["xpps"] - out["league_pps"]
    out["making_pps"] = out["pps"] - out["xpps"]
    out["total_pps"] = out["pps"] - out["league_pps"]

    # Points above what a league-average shooter on a league-average diet would
    # have scored on the same number of attempts.
    for k in ("selection", "making", "total"):
        out[f"{k}_pts"] = out[f"{k}_pps"] * out["fga"]
    # Per-100-shot versions travel better across roles.
    for k in ("selection", "making", "total"):
        out[f"{k}_p100"] = out[f"{k}_pps"] * 100

    return out.sort_values(["SEASON", "total_pts"], ascending=[True, False])


def team_season_table(df: pd.DataFrame) -> pd.DataFrame:
    league = df.groupby("SEASON", observed=True)["points"].mean().rename("league_pps")
    g = df.groupby(["SEASON", "team_abbrev"], observed=True)
    out = g.agg(
        fga=("points", "size"),
        pts=("points", "sum"),
        xpps=("xpps_full", "mean"),
        xpps_loc=("xpps_loc", "mean"),
        fg3a_rate=("is_three", "mean"),
    ).reset_index().merge(league, on="SEASON")
    out["pps"] = out["pts"] / out["fga"]
    out["selection_p100"] = (out["xpps"] - out["league_pps"]) * 100
    out["making_p100"] = (out["pps"] - out["xpps"]) * 100
    out["total_p100"] = (out["pps"] - out["league_pps"]) * 100
    return out.sort_values(["SEASON", "total_p100"], ascending=[True, False])


# ==========================================================================
# 2. empirical-Bayes zone rates
# ==========================================================================

def eb_beta_params(makes: np.ndarray, atts: np.ndarray) -> tuple[float, float]:
    """Method-of-moments beta-binomial prior for one zone-season.

    Returns (mu, k) where k is the prior strength in attempts. Observed spread
    in player make rates is part real talent and part binomial noise; only the
    excess over binomial noise is treated as talent.
    """
    atts = atts.astype(float)
    mu = makes.sum() / atts.sum()
    p = makes / atts
    w = atts / atts.sum()
    var_obs = float(np.sum(w * (p - mu) ** 2))
    var_bin = float(np.sum(w * mu * (1 - mu) / atts))
    var_true = var_obs - var_bin
    if var_true <= 1e-9:
        return mu, 1e6  # no detectable talent spread: shrink everyone to league
    k = mu * (1 - mu) / var_true - 1
    return mu, float(np.clip(k, 1.0, 1e6))


def player_zone_table(df: pd.DataFrame,
                      min_zone_att: int = MIN_ZONE_ATT_FOR_PRIOR) -> pd.DataFrame:
    """Per player-season-zone volume share and empirical-Bayes make rate."""
    d = df[df["zone"].isin(ZONE_ORDER)]
    g = d.groupby(["SEASON", "PLAYER_ID", "PLAYER_NAME", "zone"], observed=True)
    z = g.agg(att=("points", "size"), made=("SHOT_MADE_FLAG", "sum"),
              pts=("points", "sum"), xpps=("xpps_full", "mean")).reset_index()

    tot = z.groupby(["SEASON", "PLAYER_ID"], observed=True)["att"].transform("sum")
    z["share"] = z["att"] / tot
    z["player_fga"] = tot
    z["fg_pct"] = z["made"] / z["att"]

    # Fit one prior per zone-season on players with a usable sample.
    priors = {}
    for (season, zone), grp in z.groupby(["SEASON", "zone"], observed=True):
        s = grp[grp["att"] >= min_zone_att]
        if len(s) < 25:
            s = grp
        priors[(season, zone)] = eb_beta_params(s["made"].to_numpy(), s["att"].to_numpy())

    keys = list(zip(z["SEASON"].astype(str), z["zone"].astype(str)))
    z["league_fg_pct"] = [priors[k][0] for k in keys]
    z["prior_k"] = [priors[k][1] for k in keys]
    z["fg_pct_eb"] = (z["made"] + z["prior_k"] * z["league_fg_pct"]) / (z["att"] + z["prior_k"])

    z["pt_value"] = z["zone"].astype(str).map(ZONE_POINTS)
    z["ppa_raw"] = z["fg_pct"] * z["pt_value"]
    z["ppa_eb"] = z["fg_pct_eb"] * z["pt_value"]
    z["league_ppa"] = z["league_fg_pct"] * z["pt_value"]
    return z


def league_zone_table(z: pd.DataFrame) -> pd.DataFrame:
    g = z.groupby(["SEASON", "zone"], observed=True).agg(
        att=("att", "sum"), made=("made", "sum"),
        league_fg_pct=("league_fg_pct", "first"), prior_k=("prior_k", "first"),
    ).reset_index()
    tot = g.groupby("SEASON", observed=True)["att"].transform("sum")
    g["share"] = g["att"] / tot
    g["pt_value"] = g["zone"].astype(str).map(ZONE_POINTS)
    g["league_ppa"] = g["league_fg_pct"] * g["pt_value"]
    return g


# ==========================================================================
# 3. reliability: is this skill or is it noise?
# ==========================================================================

def _half_split(df: pd.DataFrame) -> pd.Series:
    """Alternate a player's games into two halves, ordered by date."""
    key = df[["SEASON", "PLAYER_ID", "GAME_DATE", "GAME_ID"]].drop_duplicates()
    key = key.sort_values(["SEASON", "PLAYER_ID", "GAME_DATE", "GAME_ID"])
    key["half"] = key.groupby(["SEASON", "PLAYER_ID"], observed=True).cumcount() % 2
    return df.merge(key, on=["SEASON", "PLAYER_ID", "GAME_DATE", "GAME_ID"], how="left")["half"]


def _metrics_by(df: pd.DataFrame, extra_keys: list[str]) -> pd.DataFrame:
    league = df.groupby("SEASON", observed=True)["points"].mean().rename("league_pps")
    g = df.groupby(["SEASON", "PLAYER_ID"] + extra_keys, observed=True)
    out = g.agg(fga=("points", "size"), pts=("points", "sum"),
                xpps=("xpps_full", "mean")).reset_index().merge(league, on="SEASON")
    out["pps"] = out["pts"] / out["fga"]
    out["selection"] = out["xpps"] - out["league_pps"]
    out["making"] = out["pps"] - out["xpps"]
    return out


def split_half_reliability(df: pd.DataFrame, min_att: int = 100) -> pd.DataFrame:
    """Odd/even-game split-half correlation, Spearman-Brown corrected."""
    d = df.copy()
    d["half"] = _half_split(d)
    m = _metrics_by(d, ["half"])
    wide = m.pivot_table(index=["SEASON", "PLAYER_ID"], columns="half", observed=True,
                         values=["selection", "making", "fga"])
    wide = wide.dropna()
    ok = (wide[("fga", 0)] >= min_att) & (wide[("fga", 1)] >= min_att)
    wide = wide[ok]
    rows = []
    for metric in ("selection", "making"):
        r = float(np.corrcoef(wide[(metric, 0)], wide[(metric, 1)])[0, 1])
        rows.append({
            "metric": metric,
            "split_half_r": r,
            "spearman_brown_r": 2 * r / (1 + r),
            "n_player_seasons": int(len(wide)),
            "min_attempts_per_half": min_att,
        })
    return pd.DataFrame(rows)


def year_over_year(ps: pd.DataFrame, min_fga: int = MIN_FGA) -> pd.DataFrame:
    """Correlate each metric with itself in the player's next season."""
    d = ps[ps["fga"] >= min_fga][
        ["SEASON", "PLAYER_ID", "PLAYER_NAME", "fga",
         "selection_p100", "making_p100", "total_p100"]].copy()
    d["yr"] = d["SEASON"].str[:4].astype(int)
    nxt = d.copy()
    nxt["yr"] = nxt["yr"] - 1
    pair = d.merge(nxt, on=["PLAYER_ID", "yr"], suffixes=("_t", "_t1"))
    rows = []
    for metric in ("selection_p100", "making_p100", "total_p100"):
        a, b = pair[f"{metric}_t"], pair[f"{metric}_t1"]
        rows.append({
            "metric": metric.replace("_p100", ""),
            "yoy_r": float(np.corrcoef(a, b)[0, 1]),
            "r_squared": float(np.corrcoef(a, b)[0, 1] ** 2),
            "n_pairs": int(len(pair)),
        })
    return pd.DataFrame(rows), pair


def spread_decomposition(ps: pd.DataFrame, sh: pd.DataFrame,
                         min_fga: int = MIN_FGA) -> pd.DataFrame:
    """How much of each component's spread across players is real?

    Observed variance = true variance + measurement noise, and reliability is
    the share that is true. So the repeatable spread is the observed spread
    scaled by sqrt(reliability). A component can look decisive in a season's
    leaderboard and still carry very little of it into the next season.
    """
    d = ps[ps["fga"] >= min_fga]
    rel = sh.set_index("metric")["spearman_brown_r"]
    rows = []
    for metric in ("selection", "making"):
        x = d[f"{metric}_p100"]
        r = float(np.clip(rel.loc[metric], 0, 1))
        sd = float(x.std())
        rows.append({
            "component": metric,
            "observed_sd_p100": sd,
            "reliability": r,
            "repeatable_sd_p100": sd * np.sqrt(r),
            "noise_sd_p100": sd * np.sqrt(1 - r),
            "corr_with_total": float(np.corrcoef(x, d["total_p100"])[0, 1]),
        })
    out = pd.DataFrame(rows)
    out["share_of_repeatable_spread"] = (
        out["repeatable_sd_p100"] ** 2 / (out["repeatable_sd_p100"] ** 2).sum())
    out.attrs["corr_selection_making"] = float(
        np.corrcoef(d["selection_p100"], d["making_p100"])[0, 1])
    return out


def stabilization_point(df: pd.DataFrame, metric: str, min_att: int = 40) -> dict:
    """Attempts needed before a metric is half signal, half noise.

    Split-half r is computed inside attempt bins, Spearman-Brown corrected to
    full-sample reliability, then r = n / (n + k) is fitted. k is the attempt
    count at which reliability reaches 0.5.
    """
    d = df.copy()
    d["half"] = _half_split(d)
    m = _metrics_by(d, ["half"])
    wide = m.pivot_table(index=["SEASON", "PLAYER_ID"], columns="half", observed=True,
                         values=[metric, "fga"]).dropna()
    wide = wide[(wide[("fga", 0)] >= min_att) & (wide[("fga", 1)] >= min_att)]
    n_half = wide[("fga", 0)] + wide[("fga", 1)]

    edges = np.quantile(n_half, np.linspace(0, 1, 7))
    pts = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = wide[(n_half >= lo) & (n_half <= hi)]
        if len(sel) < 40:
            continue
        r = float(np.corrcoef(sel[(metric, 0)], sel[(metric, 1)])[0, 1])
        r_full = 2 * r / (1 + r) if r > -0.99 else np.nan
        mean_n = float(((sel[("fga", 0)] + sel[("fga", 1)]) / 1).mean())
        pts.append({"mean_attempts": mean_n, "reliability": r_full, "n": len(sel)})

    curve = pd.DataFrame(pts).dropna()
    # Fit r = n/(n+k) by least squares on k.
    n_arr, r_arr = curve["mean_attempts"].to_numpy(), curve["reliability"].to_numpy()
    ks = np.linspace(1, 20000, 40000)
    sse = ((n_arr[None, :] / (n_arr[None, :] + ks[:, None])) - r_arr[None, :]) ** 2
    k_hat = float(ks[sse.sum(axis=1).argmin()])
    return {"metric": metric, "k_50pct_reliable_attempts": k_hat, "curve": curve}


# ==========================================================================
# 4. the prescriptive tool
# ==========================================================================

def optimise_diet(shares: np.ndarray, values: np.ndarray,
                  total_move: float = DEFAULT_TOTAL_MOVE,
                  zone_cap: float = DEFAULT_ZONE_CAP) -> np.ndarray:
    """Reallocate volume across zones to maximise expected points.

    Written as an LP over the *moves* rather than the shares, so that total
    churn can be budgeted directly:

        s = s0 + up - down,   up, down >= 0
        sum(up) = sum(down)                 shares still sum to one
        sum(up) <= total_move               only this much of the diet moves
        up_i, down_i <= zone_cap            and no single zone swings wildly

    Budgeting total movement is the constraint that matters. Capping only
    per-zone movement looks conservative but is not: with six zones a +/-5pp
    per-zone cap silently permits reshuffling 15% of a player's attempts. The
    point of this tool is a change a coach would actually install, so the ask
    is "move 5% of your shots", not "become a different player".
    """
    n = len(shares)
    up_hi = np.minimum(zone_cap, 1.0 - shares)
    down_hi = np.minimum(zone_cap, shares)  # cannot give away shots you never took

    c = np.concatenate([-values, values])           # maximise v.(s0 + up - down)
    A_eq = np.concatenate([np.ones(n), -np.ones(n)])[None, :]
    A_ub = np.concatenate([np.ones(n), np.zeros(n)])[None, :]
    bounds = list(zip(np.zeros(n), up_hi)) + list(zip(np.zeros(n), down_hi))

    res = linprog(c=c, A_eq=A_eq, b_eq=[0.0], A_ub=A_ub, b_ub=[total_move],
                  bounds=bounds, method="highs")
    if not res.success:
        return shares.copy()
    return shares + res.x[:n] - res.x[n:]


def build_prescriptions(z: pd.DataFrame, ps: pd.DataFrame, lz: pd.DataFrame,
                        total_move: float = DEFAULT_TOTAL_MOVE,
                        zone_cap: float = DEFAULT_ZONE_CAP,
                        min_fga: int = MIN_FGA,
                        values_mode: str = "eb") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per player-season: optimal reallocation and its expected value.

    values_mode selects what the optimiser believes about the player:
      "eb"      empirical-Bayes blend of his own zone rates and the league's
      "raw"     his observed zone rates, unshrunk (the noise-chasing control)
      "league"  league zone rates only, ignoring the player (the generic control)
    """
    elig = ps.loc[ps["fga"] >= min_fga, ["SEASON", "PLAYER_ID"]]
    d = z.merge(elig, on=["SEASON", "PLAYER_ID"])

    # Season -> zone -> (league make rate, prior strength). Zones a player never
    # shot from still need a prior, so the optimiser can suggest opening up a
    # corner three he is not currently taking at all.
    prior = {
        s: g.set_index(g["zone"].astype(str))[["league_fg_pct", "prior_k"]]
        for s, g in lz.groupby("SEASON", observed=True)
    }
    pt_val = np.array([ZONE_POINTS[zz] for zz in ZONE_ORDER], dtype=float)

    detail, summary = [], []
    for (season, pid, name), grp in d.groupby(
            ["SEASON", "PLAYER_ID", "PLAYER_NAME"], observed=True):
        g = grp.set_index(grp["zone"].astype(str)).reindex(ZONE_ORDER)
        pri = prior[season].reindex(ZONE_ORDER)

        att = g["att"].fillna(0.0).to_numpy(dtype=float)
        made = g["made"].fillna(0.0).to_numpy(dtype=float)
        league_pct = pri["league_fg_pct"].to_numpy(dtype=float)
        k = pri["prior_k"].to_numpy(dtype=float)

        shares = att / att.sum()
        eb = (made + k * league_pct) / (att + k)
        if values_mode == "eb":
            rates = eb
        elif values_mode == "raw":
            # Unshrunk, with the league rate standing in only where the player
            # has essentially no sample at all.
            with np.errstate(invalid="ignore", divide="ignore"):
                rates = np.where(att >= 5, made / np.where(att > 0, att, 1), league_pct)
        elif values_mode == "league":
            rates = league_pct
        else:
            raise ValueError(f"unknown values_mode {values_mode!r}")
        values = rates * pt_val

        new_shares = optimise_diet(shares, values, total_move, zone_cap)
        cur_pps, new_pps = float(shares @ values), float(new_shares @ values)
        fga = float(att.sum())

        summary.append({
            "SEASON": season, "PLAYER_ID": pid, "PLAYER_NAME": name, "fga": fga,
            "current_pps_model": cur_pps, "optimised_pps": new_pps,
            "gain_p100": (new_pps - cur_pps) * 100,
            "gain_pts_season": (new_pps - cur_pps) * fga,
            "volume_moved_pct": float(np.abs(new_shares - shares).sum() / 2 * 100),
        })
        for i, zz in enumerate(ZONE_ORDER):
            detail.append({
                "SEASON": season, "PLAYER_ID": pid, "PLAYER_NAME": name, "zone": zz,
                "att": att[i], "share": shares[i], "new_share": new_shares[i],
                "delta_share": new_shares[i] - shares[i],
                "delta_att_per100": (new_shares[i] - shares[i]) * 100,
                "ppa_used": values[i], "fg_pct_eb": eb[i],
                "ppa_eb": eb[i] * pt_val[i], "league_fg_pct": league_pct[i],
                "fg_pct_raw": (made[i] / att[i]) if att[i] > 0 else np.nan,
            })
    return pd.DataFrame(summary), pd.DataFrame(detail)


def backtest_prescriptions(details: dict[str, pd.DataFrame], z: pd.DataFrame,
                           min_next_fga: int = MIN_FGA) -> pd.DataFrame:
    """Score each season-t prescription against season t+1 shooting.

    Every variant is graded on the *same* next-season observed zone rates, so
    the comparison isolates what each one believed:

      kept        the player's own season-t diet          (do nothing)
      league      move toward league-average zone value   (generic advice)
      raw         move toward his unshrunk hot zones      (noise-chasing)
      eb          move toward his shrunk zone edge        (the tool)

    "eb beats kept" mostly re-proves that the mid-range is bad, which nobody
    needs a model for. The tests that matter are eb vs league -- does knowing
    *this* player help at all -- and eb vs raw -- does shrinking his rates beat
    trusting them.
    """
    nxt = z[["SEASON", "PLAYER_ID", "zone", "att", "made", "pt_value"]].copy()
    nxt["yr"] = nxt["SEASON"].str[:4].astype(int) - 1
    nxt["zone"] = nxt["zone"].astype(str)

    base = details["eb"].copy()
    base["yr"] = base["SEASON"].str[:4].astype(int)
    base = base[["PLAYER_ID", "PLAYER_NAME", "yr", "zone", "share"]]
    for name, det in details.items():
        d = det.copy()
        d["yr"] = d["SEASON"].str[:4].astype(int)
        base = base.merge(
            d[["PLAYER_ID", "yr", "zone", "new_share"]].rename(
                columns={"new_share": f"share_{name}"}),
            on=["PLAYER_ID", "yr", "zone"], how="left")

    m = base.merge(nxt, on=["PLAYER_ID", "yr", "zone"], how="left")
    if m.empty:
        return pd.DataFrame()
    m["att"] = m["att"].fillna(0.0)
    m["made"] = m["made"].fillna(0.0)
    m["pt_value"] = m["zone"].map(ZONE_POINTS)

    # Next-season league value per zone, used where the player has too little
    # sample for his own rate to mean anything.
    lg = m.groupby(["yr", "zone"], as_index=False).agg(
        made_sum=("made", "sum"), att_sum=("att", "sum"))
    lg["league_ppa_t1"] = (lg["made_sum"] / lg["att_sum"].clip(lower=1)) * \
        lg["zone"].map(ZONE_POINTS)
    m = m.merge(lg[["yr", "zone", "league_ppa_t1"]], on=["yr", "zone"], how="left")

    own = np.where(m["att"] >= 10, m["made"] / m["att"].clip(lower=1) * m["pt_value"], np.nan)
    m["obs_ppa_t1"] = pd.Series(own, index=m.index).fillna(m["league_ppa_t1"])

    tot_next = m.groupby(["PLAYER_ID", "yr"])["att"].transform("sum")
    m["share_actual_t1"] = np.where(tot_next > 0, m["att"] / tot_next.clip(lower=1), 0.0)

    variants = {"kept": "share", "actual_t1": "share_actual_t1",
                **{k: f"share_{k}" for k in details}}
    for name, col in variants.items():
        m[f"pps_{name}"] = m[col].fillna(0.0) * m["obs_ppa_t1"]

    agg = {"next_fga": ("att", "sum")}
    agg |= {f"pps_{n}": (f"pps_{n}", "sum") for n in variants}
    out = m.groupby(["PLAYER_ID", "PLAYER_NAME", "yr"], as_index=False).agg(**agg)
    out = out[out["next_fga"] >= min_next_fga].copy()

    for n in details:
        out[f"gain_{n}_vs_kept_p100"] = (out[f"pps_{n}"] - out["pps_kept"]) * 100
    out["eb_vs_league_p100"] = (out["pps_eb"] - out["pps_league"]) * 100
    out["eb_vs_raw_p100"] = (out["pps_eb"] - out["pps_raw"]) * 100
    return out


def backtest_summary(bt: pd.DataFrame) -> pd.DataFrame:
    """Paired comparisons with a bootstrap CI on the mean difference."""
    if bt.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(17)
    tests = [
        ("EB prescription vs. do nothing", "gain_eb_vs_kept_p100"),
        ("League-average advice vs. do nothing", "gain_league_vs_kept_p100"),
        ("Unshrunk (noise-chasing) vs. do nothing", "gain_raw_vs_kept_p100"),
        ("EB vs. league-average advice", "eb_vs_league_p100"),
        ("EB vs. unshrunk", "eb_vs_raw_p100"),
    ]
    rows = []
    for label, col in tests:
        x = bt[col].to_numpy()
        boots = rng.choice(x, size=(2000, len(x)), replace=True).mean(axis=1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append({
            "comparison": label, "mean_p100": float(x.mean()),
            "ci_low": float(lo), "ci_high": float(hi),
            "pct_positive": float((x > 0).mean() * 100), "n": int(len(x)),
        })
    return pd.DataFrame(rows)
