"""Lamix + Purple SMS API client with pooling, retries, failover & merge."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_settings
from utils import enrich_dataframe, load_team_dataframe, log_event


@dataclass
class ApiHealth:
    name: str
    ok: bool = False
    latency_ms: float = 0.0
    last_sync: str = "—"
    records: int = 0
    error: str = ""
    status: str = "DOWN"


@dataclass
class FetchResult:
    df: pd.DataFrame
    health: dict[str, ApiHealth] = field(default_factory=dict)


def _build_session(retries: int = 2, backoff: float = 0.4) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=16)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "UTS-Hunters-Enterprise/2.0", "Accept": "application/json"})
    return session


@st.cache_resource(show_spinner=False)
def get_http_session() -> requests.Session:
    settings = get_settings()
    return _build_session(retries=int(settings["api_retries"]))


def _normalize_item(item: dict[str, Any], panel: str) -> dict[str, Any] | None:
    dt_raw = item.get("dt") or item.get("datetime") or item.get("time") or item.get("date")
    num = item.get("num") or item.get("number") or item.get("phone") or item.get("msisdn")
    if num is None or dt_raw is None:
        return None
    cli = item.get("cli") or item.get("ident") or item.get("sender") or "UNKNOWN"
    message = item.get("message") or item.get("msg") or item.get("text") or item.get("content") or ""
    return {
        "panel": panel,
        "dt_raw": dt_raw,
        "num": str(num).split(".")[0].strip(),
        "cli": str(cli).strip() or "UNKNOWN",
        "message": str(message),
    }


def fetch_lamix(session: requests.Session | None = None) -> tuple[list[dict], ApiHealth]:
    settings = get_settings()
    health = ApiHealth(name="LAMIX")
    sess = session or get_http_session()
    url = settings["lamix_url"]
    token = settings["lamix_token"]
    if not url or not token:
        health.error = "Missing LAMIX_URL / LAMIX_TOKEN"
        health.status = "MISCONFIG"
        return [], health

    t0 = time.perf_counter()
    try:
        # New Lamix REST API: GET /api/v1/messages
        # Auth: Authorization: Bearer <token>  (query ?token= also works)
        # Params: limit (1-1000, default 10). Response: { "records": [...], "count": N }
        limit = max(1, min(int(settings["lamix_records"]), 1000))
        r = sess.get(
            url,
            params={"limit": limit},
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings["api_timeout"],
        )
        health.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        health.last_sync = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        if r.status_code != 200:
            try:
                err_body = r.json()
                err_code = err_body.get("error") if isinstance(err_body, dict) else None
            except Exception:
                err_code = None
            health.error = f"HTTP {r.status_code}" + (f" ({err_code})" if err_code else "")
            health.status = "DOWN"
            log_event("api_fail", health.error, api="LAMIX")
            return [], health
        payload = r.json()
        if isinstance(payload, dict):
            raw = payload.get("records") or payload.get("data") or []
        else:
            raw = payload
        rows: list[dict] = []
        for item in raw or []:
            if isinstance(item, dict):
                n = _normalize_item(item, "LAMIX")
                if n:
                    rows.append(n)
        health.ok = True
        health.records = len(rows)
        health.status = "UP"
        return rows, health
    except Exception as exc:
        health.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        health.error = str(exc)
        health.status = "DOWN"
        health.last_sync = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        log_event("api_fail", str(exc), api="LAMIX")
        return [], health


def fetch_purple(session: requests.Session | None = None) -> tuple[list[dict], ApiHealth]:
    settings = get_settings()
    health = ApiHealth(name="PURPLE")
    sess = session or get_http_session()
    url = settings["purple_url"]
    token = settings["purple_token"]
    if not url or not token:
        health.error = "Missing PURPLE_URL / PURPLE_TOKEN"
        health.status = "MISCONFIG"
        return [], health

    now = datetime.now()
    params = {
        "token": token,
        "fromdate": (now - timedelta(days=settings["purple_lookback_days"])).strftime("%Y-%m-%d %H:%M:%S"),
        "todate": now.strftime("%Y-%m-%d %H:%M:%S"),
        "records": settings["purple_records"],
        "searchnumber": "",
        "searchcli": "",
    }
    t0 = time.perf_counter()
    try:
        r = sess.get(url, params=params, timeout=max(settings["api_timeout"], 12))
        health.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        health.last_sync = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        if r.status_code != 200:
            health.error = f"HTTP {r.status_code}"
            health.status = "DOWN"
            log_event("api_fail", health.error, api="PURPLE")
            return [], health
        payload = r.json()
        if isinstance(payload, dict):
            raw = payload.get("data", [])
        elif isinstance(payload, list):
            raw = payload
        else:
            raw = []
        rows: list[dict] = []
        for item in raw or []:
            if isinstance(item, dict):
                n = _normalize_item(item, "PURPLE")
                if n:
                    rows.append(n)
        health.ok = True
        health.records = len(rows)
        health.status = "UP"
        return rows, health
    except Exception as exc:
        health.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        health.error = str(exc)
        health.status = "DOWN"
        health.last_sync = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        log_event("api_fail", str(exc), api="PURPLE")
        return [], health


def merge_records(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["panel", "num", "cli", "message", "dt", "dt_raw"])
    df = pd.DataFrame(rows)
    df["dt"] = pd.to_datetime(df["dt_raw"], errors="coerce")
    df = df.dropna(subset=["dt"])
    # Automatic duplicate removal
    df["num"] = df["num"].astype(str).str.split(".").str[0].str.strip()
    df["cli"] = df["cli"].astype(str)
    df["message"] = df["message"].astype(str)
    df = df.drop_duplicates(subset=["dt", "num", "cli", "message", "panel"], keep="first")
    df = df.sort_values("dt", ascending=False).reset_index(drop=True)
    return df


def fetch_all_parallel() -> FetchResult:
    """ThreadPoolExecutor dual fetch with failover (continue if one dies)."""
    session = get_http_session()
    health: dict[str, ApiHealth] = {}
    combined: list[dict] = []

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {
            pool.submit(fetch_lamix, session): "LAMIX",
            pool.submit(fetch_purple, session): "PURPLE",
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                rows, h = fut.result()
            except Exception as exc:
                rows, h = [], ApiHealth(name=name, error=str(exc), status="DOWN")
            health[name] = h
            combined.extend(rows)

    df = merge_records(combined)
    return FetchResult(df=df, health=health)


@st.cache_data(show_spinner=False, ttl=5)
def cached_live_frame(_bust: int = 0) -> tuple[pd.DataFrame, dict]:
    """
    Cached merge of both APIs.
    `_bust` lets callers force refresh by changing an integer key.
    Returns (enriched_df, health_dict_serializable)
    """
    result = fetch_all_parallel()
    team = load_team_dataframe()
    enriched = enrich_dataframe(result.df, team_data=team)
    health = {
        k: {
            "name": v.name,
            "ok": v.ok,
            "latency_ms": v.latency_ms,
            "last_sync": v.last_sync,
            "records": v.records,
            "error": v.error,
            "status": v.status,
        }
        for k, v in result.health.items()
    }
    return enriched, health


def bust_cache() -> int:
    n = int(st.session_state.get("cache_bust", 0)) + 1
    st.session_state["cache_bust"] = n
    cached_live_frame.clear()
    return n


def load_live_data(force: bool = False) -> tuple[pd.DataFrame, dict]:
    if force:
        bust_cache()
    key = int(st.session_state.get("cache_bust", 0))
    try:
        return cached_live_frame(key)
    except Exception as exc:
        log_event("load_live_error", str(exc))
        st.session_state["last_api_error"] = str(exc)
        return pd.DataFrame(), {}
