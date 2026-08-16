"""Pull NBA shot-level data from stats.nba.com into data/raw/.

The ShotChartDetail endpoint silently truncates any response at 102,400 rows
(2^10 * 100). A full regular season is ~218,000 field goal attempts, so asking
for a whole season in one call returns roughly the first half of it -- through
mid-January -- with no error and no warning. Every downstream number would be
quietly wrong.

We therefore page by calendar month and assert that no single chunk lands near
the cap.
"""
from __future__ import annotations

import sys
import time

import pandas as pd
from nba_api.stats.endpoints import shotchartdetail

from config import RAW, SEASONS

ROW_CAP = 102_400
KEEP = [
    "GAME_ID", "GAME_EVENT_ID", "PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "TEAM_NAME",
    "PERIOD", "MINUTES_REMAINING", "SECONDS_REMAINING", "ACTION_TYPE", "SHOT_TYPE",
    "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA", "SHOT_ZONE_RANGE", "SHOT_DISTANCE",
    "LOC_X", "LOC_Y", "SHOT_MADE_FLAG", "GAME_DATE", "HTM", "VTM",
]


def month_windows(season: str) -> list[tuple[str, str]]:
    """(start, end) MM/DD/YYYY windows covering an NBA regular season."""
    y0 = int(season[:4])
    months = [(y0, m) for m in (9, 10, 11, 12)] + [(y0 + 1, m) for m in (1, 2, 3, 4, 5, 6)]
    out = []
    for y, m in months:
        start = pd.Timestamp(year=y, month=m, day=1)
        end = start + pd.offsets.MonthEnd(1)
        out.append((start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")))
    return out


def fetch_chunk(season: str, start: str, end: str, retries: int = 4) -> pd.DataFrame:
    for attempt in range(retries):
        try:
            resp = shotchartdetail.ShotChartDetail(
                team_id=0,
                player_id=0,
                season_nullable=season,
                season_type_all_star="Regular Season",
                context_measure_simple="FGA",
                date_from_nullable=start,
                date_to_nullable=end,
                timeout=90,
            )
            return resp.get_data_frames()[0]
        except Exception as exc:  # network flake / rate limit
            if attempt == retries - 1:
                raise
            wait = 3 * (attempt + 1)
            print(f"    retry {attempt + 1} after {type(exc).__name__}; sleeping {wait}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_season(season: str) -> pd.DataFrame:
    frames = []
    for start, end in month_windows(season):
        df = fetch_chunk(season, start, end)
        if len(df) >= ROW_CAP:
            raise RuntimeError(
                f"{season} {start}-{end} returned {len(df)} rows, at or above the "
                f"{ROW_CAP} API cap -- this window is truncated, use finer chunks."
            )
        if len(df):
            frames.append(df)
            print(f"    {start[:5]} -> {len(df):>6,} shots")
        time.sleep(0.7)
    if not frames:
        raise RuntimeError(f"no data returned for {season}")
    out = pd.concat(frames, ignore_index=True)
    # Month windows are disjoint, but a game straddling a boundary would be
    # double counted; dedupe on the natural key to be safe.
    out = out.drop_duplicates(subset=["GAME_ID", "GAME_EVENT_ID"]).reset_index(drop=True)
    return out[KEEP]


def main(seasons: list[str]) -> None:
    for season in seasons:
        path = RAW / f"shots_{season.replace('-', '_')}.parquet"
        if path.exists():
            print(f"{season}: cached ({len(pd.read_parquet(path)):,} shots)")
            continue
        print(f"{season}: fetching")
        df = fetch_season(season)
        df["SEASON"] = season
        df.to_parquet(path, index=False)
        print(f"{season}: {len(df):,} shots, {df.GAME_ID.nunique():,} games -> {path.name}")


if __name__ == "__main__":
    main(sys.argv[1:] or SEASONS)
