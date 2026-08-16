"""Run the whole Shot Diet pipeline: features -> models -> tables -> reports."""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

import analyze as A
import model as M
from config import MIN_FGA, PROCESSED, RAW, REPORTS, SEASONS
from features import FEATURES_FULL, FEATURES_LOC, build


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> None:
    t0 = time.time()

    log("building feature table")
    df = build()
    n_excl = df.attrs.get("n_excluded", 0)
    log(f"  {len(df):,} shots across {len(SEASONS)} seasons "
        f"({n_excl:,} backcourt/heave attempts excluded)")

    groups = df["PLAYER_ID"]

    log("out-of-fold xPPS (location only)")
    p_loc = M.oof_predict(df, FEATURES_LOC, groups)
    log("out-of-fold xPPS (location + action type)")
    p_full = M.oof_predict(df, FEATURES_FULL, groups)

    log("baselines")
    p_zone = M.baseline_zone(df, groups)
    p_dist = M.baseline_distance(df, groups)

    pt_val = 2 + df["is_three"].to_numpy()
    df["xpps_loc"] = p_loc * pt_val
    df["xpps_full"] = p_full * pt_val

    # Cache the out-of-fold predictions so the robustness checks can reuse them
    # instead of refitting ten folds of gradient boosting.
    df[["GAME_ID", "GAME_EVENT_ID", "xpps_loc", "xpps_full"]].to_parquet(
        RAW / "oof_predictions.parquet", index=False)

    log("scoring models")
    metrics = M.evaluate(df, {
        "Distance spline logistic (baseline)": p_dist,
        "Zone average make rate (baseline)": p_zone,
        "xPPS-loc (gradient boosting, geometry)": p_loc,
        "xPPS-full (gradient boosting, + action type)": p_full,
    })
    print(metrics.to_string(index=False))
    metrics.to_parquet(PROCESSED / "model_metrics.parquet", index=False)

    calib = M.calibration_table(df["SHOT_MADE_FLAG"].to_numpy(), p_full)
    calib.to_parquet(PROCESSED / "calibration.parquet", index=False)

    # A calibrated model must reproduce league scoring rate; if it does not,
    # the selection/making split does not add up.
    chk = {
        "league_actual_pps": float(df["points"].mean()),
        "league_model_xpps": float(df["xpps_full"].mean()),
        "calibration_gap_p100": float((df["xpps_full"].mean() - df["points"].mean()) * 100),
        "max_calibration_bin_error": float((calib["pred"] - calib["obs"]).abs().max()),
    }
    log(f"  calibration gap: {chk['calibration_gap_p100']:.3f} pts per 100 shots")

    log("player and team decomposition")
    ps = A.player_season_table(df)
    ts = A.team_season_table(df)
    ps.to_parquet(PROCESSED / "player_season.parquet", index=False)
    ts.to_parquet(PROCESSED / "team_season.parquet", index=False)

    log("empirical-Bayes zone rates")
    z = A.player_zone_table(df)
    lz = A.league_zone_table(z)
    z.to_parquet(PROCESSED / "player_zone.parquet", index=False)
    lz.to_parquet(PROCESSED / "league_zone.parquet", index=False)

    log("reliability")
    sh = A.split_half_reliability(df)
    yoy, pairs = A.year_over_year(ps)
    sh.to_parquet(PROCESSED / "split_half.parquet", index=False)
    yoy.to_parquet(PROCESSED / "yoy.parquet", index=False)
    pairs.to_parquet(PROCESSED / "yoy_pairs.parquet", index=False)
    print(sh.to_string(index=False))
    print(yoy.to_string(index=False))

    spread = A.spread_decomposition(ps, sh)
    corr_sm = spread.attrs["corr_selection_making"]
    spread.to_parquet(PROCESSED / "spread.parquet", index=False)
    print(spread.to_string(index=False))
    log(f"  corr(selection, making) across players = {corr_sm:+.3f}")

    stab = {}
    curves = []
    for metric in ("selection", "making"):
        r = A.stabilization_point(df, metric)
        stab[metric] = r["k_50pct_reliable_attempts"]
        c = r["curve"]
        c["metric"] = metric
        curves.append(c)
        log(f"  {metric}: 50% reliable at {r['k_50pct_reliable_attempts']:.0f} attempts")
    pd.concat(curves).to_parquet(PROCESSED / "stabilization_curve.parquet", index=False)

    log("shot-diet optimiser (+ league-only and unshrunk controls)")
    details = {}
    for mode in ("eb", "league", "raw"):
        s, d = A.build_prescriptions(z, ps, lz, values_mode=mode)
        details[mode] = d
        if mode == "eb":
            summ, det = s, d
    summ.to_parquet(PROCESSED / "prescription_summary.parquet", index=False)
    det.to_parquet(PROCESSED / "prescription_detail.parquet", index=False)
    log(f"  {len(summ):,} player-seasons optimised, "
        f"median gain {summ['gain_p100'].median():.2f} pts/100, "
        f"median volume moved {summ['volume_moved_pct'].median():.1f}%")

    log("backtesting prescriptions out of sample")
    bt = A.backtest_prescriptions(details, z)
    bts = A.backtest_summary(bt)
    bt.to_parquet(PROCESSED / "backtest.parquet", index=False)
    bts.to_parquet(PROCESSED / "backtest_summary.parquet", index=False)
    if len(bts):
        print(bts.to_string(index=False))

    log("saving shot sample for the court charts")
    latest = SEASONS[-1]
    cols = ["SEASON", "PLAYER_ID", "PLAYER_NAME", "team_abbrev", "loc_x", "loc_y",
            "dist", "zone", "is_three", "SHOT_MADE_FLAG", "points",
            "xpps_full", "xpps_loc"]
    samp = df.loc[df["SEASON"] == latest, cols].copy()
    samp["loc_x"] = samp["loc_x"].astype("float32")
    samp["loc_y"] = samp["loc_y"].astype("float32")
    samp["dist"] = samp["dist"].astype("float32")
    samp["xpps_full"] = samp["xpps_full"].astype("float32")
    samp["xpps_loc"] = samp["xpps_loc"].astype("float32")
    samp["SHOT_MADE_FLAG"] = samp["SHOT_MADE_FLAG"].astype("int8")
    samp["points"] = samp["points"].astype("int8")
    samp["is_three"] = samp["is_three"].astype("int8")
    samp.to_parquet(PROCESSED / "shots_latest.parquet", index=False, compression="zstd")

    summary = {
        "seasons": SEASONS,
        "n_shots": int(len(df)),
        "n_excluded_backcourt_or_heave": int(n_excl),
        "n_players": int(df["PLAYER_ID"].nunique()),
        "min_fga_for_leaderboards": MIN_FGA,
        "calibration": chk,
        "model_metrics": metrics.to_dict("records"),
        "split_half": sh.to_dict("records"),
        "year_over_year": yoy.to_dict("records"),
        "spread": spread.to_dict("records"),
        "corr_selection_making": corr_sm,
        "stabilization_attempts_50pct": stab,
        "prescription": {
            "n_player_seasons": int(len(summ)),
            "median_gain_p100": float(summ["gain_p100"].median()),
            "mean_gain_p100": float(summ["gain_p100"].mean()),
        },
        "backtest": bts.to_dict("records"),
        "runtime_minutes": round((time.time() - t0) / 60, 1),
    }
    (REPORTS / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"done in {summary['runtime_minutes']} min -> reports/summary.json")


if __name__ == "__main__":
    main()
