"""Cached loaders for the processed tables."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    path = PROCESSED / f"{name}.parquet"
    if not path.exists():
        st.error(f"Missing `data/processed/{name}.parquet`. "
                 "Run `python src/fetch.py && python src/run_pipeline.py` first.")
        st.stop()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def summary() -> dict:
    path = REPORTS / "summary.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


@st.cache_data(show_spinner=False)
def seasons() -> list[str]:
    return sorted(table("player_season")["SEASON"].unique(), reverse=True)
