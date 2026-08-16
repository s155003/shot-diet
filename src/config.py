"""Shared paths and constants for the Shot Diet pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"

for _d in (RAW, PROCESSED, REPORTS):
    _d.mkdir(parents=True, exist_ok=True)

# Five most recent complete regular seasons. 2019-20 / 2020-21 are excluded
# on purpose: the bubble and the 72-game season distort both shot selection
# and rest patterns enough to contaminate year-over-year stability estimates.
SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]

# Minimum attempts for a player-season to enter the leaderboards / stability
# sample. 200 FGA is roughly a rotation player who played most of a season.
MIN_FGA = 200

# Court zones we optimise over: the six buckets NBA staffs already talk in.
#
# Splitting these further by left/right was tried and abandoned. Per-side
# samples are small enough that the empirical-Bayes prior strength swung from
# k=199 on one wing to k=2018 on the other for the same shot -- an artefact of
# binomial noise, not a real talent difference -- which made the optimiser
# recommend left-side threes over identical right-side threes. Left/right
# shooting splits are almost entirely noise at single-season volume.
ZONE_ORDER = [
    "Restricted Area",
    "Paint (Non-RA)",
    "Short Mid-Range (8-16 ft)",
    "Long Mid-Range (16-24 ft)",
    "Corner 3",
    "Above the Break 3",
]

# Minimum attempts a player needs in a zone-season to help fit that zone's
# empirical-Bayes prior. Low-volume tails make the moment estimator unstable.
MIN_ZONE_ATT_FOR_PRIOR = 25

# Shot-diet optimiser defaults: move at most 5% of a player's total attempts,
# and at most 5 percentage points of share in or out of any single zone.
DEFAULT_TOTAL_MOVE = 0.05
DEFAULT_ZONE_CAP = 0.05

RANDOM_STATE = 17
