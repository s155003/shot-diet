"""Turn raw shot events into the modelling table."""
from __future__ import annotations

import numpy as np
import pandas as pd
from nba_api.stats.static import teams as static_teams

from config import RAW, SEASONS

# Rare ACTION_TYPE values are collapsed so the model does not carve out a leaf
# for a shot type that happens forty times a decade.
MIN_ACTION_COUNT = 400

FEATURES_LOC = ["loc_x", "loc_y", "dist", "abs_x", "angle", "is_three",
                "period_c", "secs_left", "is_home", "SEASON"]
FEATURES_FULL = FEATURES_LOC + ["action"]
CATEGORICAL = ["SEASON", "action"]


def load_raw(seasons: list[str] | None = None) -> pd.DataFrame:
    seasons = seasons or SEASONS
    frames = []
    for s in seasons:
        path = RAW / f"shots_{s.replace('-', '_')}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing -- run src/fetch.py first")
        frames.append(pd.read_parquet(path))
    return pd.concat(frames, ignore_index=True)


def label_zone(basic: pd.Series, rng: pd.Series) -> pd.Series:
    """Collapse NBA's zone/range pair into the six zones we optimise over."""
    zone = basic.astype(str).replace({
        "In The Paint (Non-RA)": "Paint (Non-RA)",
        "Left Corner 3": "Corner 3",
        "Right Corner 3": "Corner 3",
    })
    mid = basic.eq("Mid-Range")
    zone = zone.mask(mid & rng.eq("8-16 ft."), "Short Mid-Range (8-16 ft)")
    zone = zone.mask(mid & rng.eq("16-24 ft."), "Long Mid-Range (16-24 ft)")
    return zone


def build(seasons: list[str] | None = None) -> pd.DataFrame:
    df = load_raw(seasons)

    tricode = {t["id"]: t["abbreviation"] for t in static_teams.get_teams()}
    df["team_abbrev"] = df["TEAM_ID"].map(tricode)
    df["is_home"] = df["team_abbrev"].eq(df["HTM"]).astype(int)

    df["is_three"] = df["SHOT_TYPE"].str.startswith("3").astype(int)
    df["points"] = df["SHOT_MADE_FLAG"] * (2 + df["is_three"])
    df["secs_left"] = df["MINUTES_REMAINING"] * 60 + df["SECONDS_REMAINING"]
    df["period_c"] = df["PERIOD"].clip(upper=5)

    # Geometry. LOC_X/LOC_Y are in tenths of a foot, origin at the basket.
    x, y = df["LOC_X"].astype(float) / 10.0, df["LOC_Y"].astype(float) / 10.0
    df["loc_x"], df["loc_y"] = x, y
    df["dist"] = np.hypot(x, y)
    df["abs_x"] = x.abs()
    # Absolute angle off the straight-on line to the rim, in degrees. Made
    # symmetric because a corner three is a corner three from either side.
    df["angle"] = np.degrees(np.arctan2(df["abs_x"], np.maximum(y, 0.01)))

    df["zone"] = label_zone(df["SHOT_ZONE_BASIC"], df["SHOT_ZONE_RANGE"])

    # --- exclusions -------------------------------------------------------
    # Backcourt attempts and end-of-period heaves are not shot-selection
    # decisions, they are clock management. Leaving them in punishes whichever
    # guard happens to be holding the ball at the buzzer.
    df["is_heave"] = ((df["secs_left"] <= 3) & (df["dist"] >= 30)).astype(int)
    n_before = len(df)
    df = df.loc[df["SHOT_ZONE_BASIC"].ne("Backcourt") & df["is_heave"].eq(0)]
    df = df.reset_index(drop=True)
    df.attrs["n_excluded"] = n_before - len(df)

    counts = df["ACTION_TYPE"].value_counts()
    common = counts[counts >= MIN_ACTION_COUNT].index
    df["action"] = df["ACTION_TYPE"].where(df["ACTION_TYPE"].isin(common), "Other")

    for c in ("action", "zone", "SEASON"):
        df[c] = df[c].astype("category")

    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], format="%Y%m%d")
    return df
