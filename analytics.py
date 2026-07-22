"""Analytics helpers — aggregations used across pages."""
from __future__ import annotations

from typing import Any

import pandas as pd


def cli_summary(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    if df is None or df.empty or "CLI" not in df.columns:
        return pd.DataFrame(columns=["CLI", "OTP", "Numbers", "Countries"])
    g = (
        df.groupby("CLI", dropna=False)
        .agg(
            OTP=("CLI", "size"),
            Numbers=("Number", "nunique") if "Number" in df.columns else ("CLI", "size"),
            Countries=("Country", "nunique") if "Country" in df.columns else ("CLI", "size"),
        )
        .sort_values("OTP", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return g


def country_summary(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    if df is None or df.empty or "Country" not in df.columns:
        return pd.DataFrame(columns=["Country", "OTP", "CLI", "Numbers"])
    g = (
        df.groupby("Country", dropna=False)
        .agg(
            OTP=("Country", "size"),
            CLI=("CLI", "nunique") if "CLI" in df.columns else ("Country", "size"),
            Numbers=("Number", "nunique") if "Number" in df.columns else ("Country", "size"),
        )
        .sort_values("OTP", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return g


def team_summary(df: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    if df is None or df.empty or "Team Member" not in df.columns:
        return pd.DataFrame(columns=["Team Member", "OTP", "Numbers", "CLI"])
    work = df[df["Team Member"].astype(str).str.strip() != ""].copy()
    if work.empty:
        return pd.DataFrame(columns=["Team Member", "OTP", "Numbers", "CLI"])
    g = (
        work.groupby("Team Member", dropna=False)
        .agg(
            OTP=("Team Member", "size"),
            Numbers=("Number", "nunique") if "Number" in work.columns else ("Team Member", "size"),
            CLI=("CLI", "nunique") if "CLI" in work.columns else ("Team Member", "size"),
        )
        .sort_values("OTP", ascending=False)
        .head(top_n)
        .reset_index()
    )
    return g


def api_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df is None or df.empty or "Panel" not in df.columns:
        return {"LAMIX": 0, "PURPLE": 0}
    vc = df["Panel"].astype(str).str.upper().value_counts().to_dict()
    return {"LAMIX": int(vc.get("LAMIX", 0)), "PURPLE": int(vc.get("PURPLE", 0))}


def rolling_minute_counts(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "dt" not in df.columns:
        return pd.DataFrame(columns=["minute", "otp"])
    work = df.copy()
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work = work.dropna(subset=["dt"])
    work["minute"] = work["dt"].dt.floor("min")
    return work.groupby("minute").size().reset_index(name="otp")
