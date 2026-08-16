"""Expected-points-per-shot (xPPS) models and their out-of-fold predictions.

Two models are fit:

  xpps_loc   location, geometry, clock and venue only. "How good is this spot?"
  xpps_full  the above plus ACTION_TYPE. "How good is this look?"

ACTION_TYPE ("Cutting Dunk Shot", "Turnaround Fadeaway", "Driving Floating Jump
Shot", ...) describes how the attempt was manufactured, which is a property of
the offence, not of the shooter's touch. We therefore treat it as part of shot
*selection* and use xpps_full for the headline decomposition, keeping xpps_loc
as the purely geometric view.

Predictions used to grade players are always out-of-fold, and the folds are
grouped by PLAYER_ID. The model that judges a player has therefore never seen a
single one of that player's shots -- without this, a high-volume specialist
partly sets his own benchmark.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import SplineTransformer, StandardScaler
from sklearn.pipeline import make_pipeline

from config import RANDOM_STATE, REPORTS
from features import CATEGORICAL, FEATURES_FULL, FEATURES_LOC

N_FOLDS = 5


def _prep(df: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    X = df[feats].copy()
    for c in CATEGORICAL:
        if c in X.columns:
            X[c] = X[c].astype("category")
    return X


def new_model() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        loss="log_loss",
        max_iter=400,
        learning_rate=0.06,
        max_leaf_nodes=48,
        min_samples_leaf=120,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=25,
        categorical_features="from_dtype",
        random_state=RANDOM_STATE,
    )


def oof_predict(df: pd.DataFrame, feats: list[str], groups: pd.Series) -> np.ndarray:
    """Out-of-fold P(make), folds grouped so a player never trains on himself."""
    X, y = _prep(df, feats), df["SHOT_MADE_FLAG"].to_numpy()
    oof = np.zeros(len(df), dtype=float)
    cv = GroupKFold(n_splits=N_FOLDS)
    for k, (tr, te) in enumerate(cv.split(X, y, groups), 1):
        m = new_model().fit(X.iloc[tr], y[tr])
        oof[te] = m.predict_proba(X.iloc[te])[:, 1]
        print(f"    fold {k}/{N_FOLDS} done ({len(te):,} held out)")
    return oof


def fit_full(df: pd.DataFrame, feats: list[str]) -> HistGradientBoostingClassifier:
    """Refit on everything, for scoring hypothetical/new shots in the app."""
    return new_model().fit(_prep(df, feats), df["SHOT_MADE_FLAG"].to_numpy())


# --------------------------------------------------------------------------
# baselines and scoring
# --------------------------------------------------------------------------

def baseline_zone(df: pd.DataFrame, groups: pd.Series) -> np.ndarray:
    """Out-of-fold zone-average make rate: the 'shot chart' level of analysis."""
    oof = np.zeros(len(df))
    cv = GroupKFold(n_splits=N_FOLDS)
    key = df["zone"].astype(str) + "|" + df["SEASON"].astype(str)
    y = df["SHOT_MADE_FLAG"]
    for tr, te in cv.split(df, y, groups):
        rates = y.iloc[tr].groupby(key.iloc[tr], observed=True).mean()
        oof[te] = key.iloc[te].map(rates).fillna(y.iloc[tr].mean()).to_numpy()
    return oof


def baseline_distance(df: pd.DataFrame, groups: pd.Series) -> np.ndarray:
    """Out-of-fold spline logistic on distance + is_three: the textbook model."""
    oof = np.zeros(len(df))
    cv = GroupKFold(n_splits=N_FOLDS)
    X = df[["dist", "is_three"]].to_numpy()
    y = df["SHOT_MADE_FLAG"].to_numpy()
    pipe = make_pipeline(
        SplineTransformer(n_knots=8, degree=3),
        StandardScaler(),
        LogisticRegression(max_iter=2000),
    )
    for tr, te in cv.split(X, y, groups):
        oof[te] = pipe.fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    return oof


def score(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "log_loss": float(log_loss(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "auc": float(roc_auc_score(y, p)),
    }


def calibration_table(y: np.ndarray, p: np.ndarray, bins: int = 20) -> pd.DataFrame:
    """Equal-count bins: predicted vs observed make rate."""
    q = pd.qcut(p, bins, labels=False, duplicates="drop")
    out = pd.DataFrame({"pred": p, "obs": y, "bin": q}).groupby("bin").agg(
        n=("obs", "size"), pred=("pred", "mean"), obs=("obs", "mean")
    ).reset_index(drop=True)
    return out


def evaluate(df: pd.DataFrame, preds: dict[str, np.ndarray]) -> pd.DataFrame:
    y = df["SHOT_MADE_FLAG"].to_numpy()
    rows = []
    base = np.full(len(y), y.mean())
    rows.append({"model": "League mean make rate", **score(y, base)})
    for name, p in preds.items():
        rows.append({"model": name, **score(y, p)})
    out = pd.DataFrame(rows)
    ref = out.loc[0, "log_loss"]
    out["log_loss_gain_pct"] = (ref - out["log_loss"]) / ref * 100
    return out


def save_metrics(obj: dict, name: str) -> None:
    (REPORTS / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")
