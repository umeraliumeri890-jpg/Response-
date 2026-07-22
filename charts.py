"""Plotly-only chart builders for UTS Hunters."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import theme_colors


def _layout(fig: go.Figure, title: str = "") -> go.Figure:
    t = theme_colors()
    fig.update_layout(
        title=dict(text=title, font=dict(color=t["text"], size=16, family="Orbitron, Inter, sans-serif")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text"], family="Inter, sans-serif"),
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=t["muted"])),
        xaxis=dict(gridcolor="rgba(0,212,255,0.08)", zeroline=False, color=t["muted"]),
        yaxis=dict(gridcolor="rgba(0,212,255,0.08)", zeroline=False, color=t["muted"]),
        colorway=[t["accent"], t["accent2"], t["gold"], t["success"], t["danger"], t["silver"]],
        hovermode="closest",
    )
    return fig


def live_timeline(df: pd.DataFrame) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "dt" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No timeline data", showarrow=False, font=dict(color=t["muted"]))
        return _layout(fig, "Live Timeline — OTP / minute")

    work = df.copy()
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work = work.dropna(subset=["dt"])
    work["minute"] = work["dt"].dt.floor("min")
    series = work.groupby("minute").size().reset_index(name="otp")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=series["minute"],
            y=series["otp"],
            mode="lines+markers",
            line=dict(color=t["accent"], width=2, shape="spline"),
            marker=dict(size=5, color=t["accent2"]),
            fill="tozeroy",
            fillcolor="rgba(0,212,255,0.12)",
            name="OTP/min",
        )
    )
    return _layout(fig, "Live Timeline — OTP / minute")


def country_pie(df: pd.DataFrame) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "Country" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No country data", showarrow=False)
        return _layout(fig, "Country Share")
    vc = df["Country"].fillna("Unknown").value_counts().head(12).reset_index()
    vc.columns = ["Country", "count"]
    fig = px.pie(vc, names="Country", values="count", hole=0.55)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return _layout(fig, "Country Distribution")


def country_bar(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "Country" not in df.columns:
        fig = go.Figure()
        return _layout(fig, f"Top {top_n} Countries")
    vc = df["Country"].fillna("Unknown").value_counts().head(top_n).sort_values()
    fig = go.Figure(
        go.Bar(
            x=vc.values,
            y=vc.index,
            orientation="h",
            marker=dict(color=vc.values, colorscale=[[0, t["accent2"]], [1, t["accent"]]]),
        )
    )
    return _layout(fig, f"Top {top_n} Countries")


def cli_bar(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "CLI" not in df.columns:
        fig = go.Figure()
        return _layout(fig, "Top CLI")
    vc = df["CLI"].fillna("UNKNOWN").value_counts().head(top_n).sort_values()
    fig = go.Figure(
        go.Bar(
            x=vc.values,
            y=vc.index.astype(str),
            orientation="h",
            marker=dict(color=t["accent2"]),
            name="CLI",
        )
    )
    return _layout(fig, f"Top {top_n} CLI")


def otp_heatmap(df: pd.DataFrame) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "dt" not in df.columns:
        fig = go.Figure()
        return _layout(fig, "OTP Heatmap — Hour × Day")
    work = df.copy()
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work = work.dropna(subset=["dt"])
    work["hour"] = work["dt"].dt.hour
    work["day"] = work["dt"].dt.day_name()
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = (
        work.groupby(["day", "hour"]).size().reset_index(name="count")
        .pivot(index="day", columns="hour", values="count")
        .reindex(day_order)
        .fillna(0)
    )
    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns),
            y=list(pivot.index),
            colorscale=[[0, t["bg2"]], [0.5, t["accent2"]], [1, t["accent"]]],
            hoverongaps=False,
        )
    )
    return _layout(fig, "OTP Heatmap — Hours vs Days")


def hourly_trend(df: pd.DataFrame) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "dt" not in df.columns:
        fig = go.Figure()
        return _layout(fig, "Hourly Trend")
    work = df.copy()
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work["hour"] = work["dt"].dt.hour
    vc = work.groupby("hour").size().reindex(range(24), fill_value=0)
    fig = go.Figure(
        go.Bar(x=vc.index, y=vc.values, marker=dict(color=t["accent"]), name="OTP")
    )
    fig.update_xaxes(title="Hour")
    return _layout(fig, "Hourly Trend")


def daily_trend(df: pd.DataFrame) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "dt" not in df.columns:
        fig = go.Figure()
        return _layout(fig, "Daily Trend")
    work = df.copy()
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work["day"] = work["dt"].dt.date
    vc = work.groupby("day").size().reset_index(name="otp")
    fig = go.Figure(
        go.Scatter(
            x=vc["day"],
            y=vc["otp"],
            mode="lines+markers",
            line=dict(color=t["accent2"], width=3),
            fill="tozeroy",
            fillcolor="rgba(109,93,252,0.15)",
        )
    )
    return _layout(fig, "Daily Trend")


def api_comparison(df: pd.DataFrame) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "Panel" not in df.columns:
        fig = go.Figure()
        return _layout(fig, "API Comparison — Lamix vs Purple")
    work = df.copy()
    work["dt"] = pd.to_datetime(work.get("dt"), errors="coerce")
    work = work.dropna(subset=["dt"])
    work["hour"] = work["dt"].dt.floor("h")
    grp = work.groupby(["hour", "Panel"]).size().reset_index(name="otp")
    fig = px.line(grp, x="hour", y="otp", color="Panel", markers=True)
    return _layout(fig, "API Comparison — Lamix vs Purple")


def team_performance(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "Team Member" not in df.columns:
        fig = go.Figure()
        return _layout(fig, "Team Performance")
    work = df[df["Team Member"].astype(str).str.strip() != ""]
    if work.empty:
        fig = go.Figure()
        fig.add_annotation(text="No matched team members", showarrow=False, font=dict(color=t["muted"]))
        return _layout(fig, "Team Performance")
    vc = work["Team Member"].value_counts().head(top_n).sort_values()
    fig = go.Figure(
        go.Bar(
            x=vc.values,
            y=vc.index.astype(str),
            orientation="h",
            marker=dict(color=t["gold"]),
        )
    )
    return _layout(fig, "Team Performance")


def country_map(df: pd.DataFrame) -> go.Figure:
    t = theme_colors()
    if df is None or df.empty or "Country" not in df.columns:
        fig = go.Figure()
        return _layout(fig, "Country Distribution Map")

    # Map free-text geocoder names to ISO-ish labels plotly understands reasonably
    vc = df["Country"].fillna("Unknown").value_counts().reset_index()
    vc.columns = ["Country", "count"]
    fig = px.scatter_geo(
        vc,
        locations="Country",
        locationmode="country names",
        size="count",
        hover_name="Country",
        size_max=40,
        color="count",
        color_continuous_scale=[[0, t["accent2"]], [1, t["accent"]]],
    )
    fig.update_geos(
        bgcolor="rgba(0,0,0,0)",
        showland=True,
        landcolor="rgba(11,18,36,0.9)",
        showocean=True,
        oceancolor="rgba(3,7,18,0.95)",
        showcountries=True,
        countrycolor="rgba(0,212,255,0.25)",
        showframe=False,
    )
    fig.update_layout(coloraxis_showscale=False)
    return _layout(fig, "Country Distribution Map")


def empty_fig(title: str = "") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text="No data", showarrow=False)
    return _layout(fig, title)
