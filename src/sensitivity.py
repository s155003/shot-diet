"""Robustness checks for the headline null: does knowing the player help?

Checks three ways the null could be an artefact:
  1. the 5% move budget is so tight that every variant makes the same move
  2. the EB and league prescriptions are simply identical vectors
  3. the backtest falls back to league rates so often it cannot see the player
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import analyze as A
from config import PROCESSED, RAW, REPORTS
from features import FEATURES_FULL, build
from model import oof_predict


def load_scored() -> pd.DataFrame:
    """Feature table with out-of-fold xPPS, reusing the pipeline's cache."""
    df = build()
    cache = RAW / "oof_predictions.parquet"
    if cache.exists():
        pred = pd.read_parquet(cache)
        df = df.merge(pred, on=["GAME_ID", "GAME_EVENT_ID"], how="left")
        if df["xpps_full"].notna().all():
            return df
        df = df.drop(columns=["xpps_loc", "xpps_full"], errors="ignore")
    pv = 2 + df["is_three"]
    df["xpps_full"] = oof_predict(df, FEATURES_FULL, df["PLAYER_ID"]) * pv
    df["xpps_loc"] = df["xpps_full"]  # unused by these checks
    return df


def main() -> None:
    df = load_scored()
    ps = A.player_season_table(df)
    z = A.player_zone_table(df)
    lz = A.league_zone_table(z)

    rows, diffs = [], []
    for move in (0.03, 0.05, 0.10, 0.20):
        details = {}
        for mode in ("eb", "league", "raw"):
            _, d = A.build_prescriptions(z, ps, lz, total_move=move,
                                         zone_cap=max(move, 0.05), values_mode=mode)
            details[mode] = d
        bt = A.backtest_prescriptions(details, z)
        s = A.backtest_summary(bt)
        s["move_budget"] = move
        rows.append(s)

        # How far apart are the EB and league prescriptions themselves?
        a = details["eb"][["PLAYER_ID", "SEASON", "zone", "new_share"]]
        b = details["league"][["PLAYER_ID", "SEASON", "zone", "new_share"]]
        m = a.merge(b, on=["PLAYER_ID", "SEASON", "zone"], suffixes=("_eb", "_lg"))
        per = m.groupby(["PLAYER_ID", "SEASON"]).apply(
            lambda g: np.abs(g["new_share_eb"] - g["new_share_lg"]).sum() / 2,
            include_groups=False)
        diffs.append({"move_budget": move,
                      "median_prescription_gap_pct": float(per.median() * 100),
                      "pct_identical": float((per < 1e-6).mean() * 100),
                      "p90_gap_pct": float(per.quantile(0.9) * 100)})

    out = pd.concat(rows, ignore_index=True)
    gaps = pd.DataFrame(diffs)
    out.to_parquet(PROCESSED / "sensitivity_backtest.parquet", index=False)
    gaps.to_parquet(PROCESSED / "sensitivity_gaps.parquet", index=False)

    key = out[out["comparison"].isin(["EB vs. league-average advice", "EB vs. unshrunk"])]
    print("\n=== does knowing the player help, by move budget ===")
    print(key[["move_budget", "comparison", "mean_p100", "ci_low", "ci_high",
               "pct_positive"]].to_string(index=False))
    print("\n=== how different are the EB and league prescriptions ===")
    print(gaps.to_string(index=False))

    # 3. fallback rate: how often does the backtest have to use league rates?
    nxt = z[["SEASON", "PLAYER_ID", "zone", "att"]].copy()
    elig = ps.loc[ps["fga"] >= 200, ["SEASON", "PLAYER_ID"]]
    nxt = nxt.merge(elig, on=["SEASON", "PLAYER_ID"])
    print("\n=== backtest zone-sample coverage ===")
    print(f"player-season-zones with >=10 attempts: "
          f"{(nxt['att'] >= 10).mean() * 100:.1f}% "
          f"(share of attempts covered: "
          f"{nxt.loc[nxt['att'] >= 10, 'att'].sum() / nxt['att'].sum() * 100:.1f}%)")

    REPORTS.joinpath("sensitivity.txt").write_text(
        key.to_string(index=False) + "\n\n" + gaps.to_string(index=False),
        encoding="utf-8")


if __name__ == "__main__":
    main()
