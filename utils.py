"""Shared helpers: logging, fingerprint, team lookup, country, export, filters."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd
import phonenumbers
import streamlit as st
from phonenumbers import geocoder

from config import IGNORE_TEAM_MEMBERS, LOG_DIR, ROOT, get_settings


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def setup_logger(name: str = "uts_hunters") -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    fh = TimedRotatingFileHandler(
        LOG_DIR / "app.log", when="midnight", backupCount=14, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


log = setup_logger()


def log_event(kind: str, message: str, **extra: Any) -> None:
    payload = {"kind": kind, "message": message, **extra}
    log.info(json.dumps(payload, default=str))


# ---------------------------------------------------------------------------
# Device fingerprint
# ---------------------------------------------------------------------------
def get_server_side_fp() -> str:
    """SHA256 fingerprint from User-Agent + Accept-Language + Accept-Encoding."""
    try:
        headers = st.context.headers
        ua = headers.get("User-Agent", "unknown")
        lang = headers.get("Accept-Language", "")
        enc = headers.get("Accept-Encoding", "")
        raw = f"{ua}|{lang}|{enc}"
        return "FP" + hashlib.sha256(raw.encode()).hexdigest()[:20].upper()
    except Exception:
        try:
            import streamlit.web.server.websocket_headers as wh  # type: ignore

            headers = wh._get_websocket_headers()  # noqa: SLF001
            ua = (headers or {}).get("User-Agent", "unknown")
            raw = f"{ua}"
            return "FP" + hashlib.sha256(raw.encode()).hexdigest()[:20].upper()
        except Exception:
            return "FP_FALLBACK"


# ---------------------------------------------------------------------------
# Country lookup (cached)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=86_400)
def get_country_cached(num_str: str) -> str:
    try:
        s = str(num_str).strip()
        if not s:
            return "Unknown"
        if not s.startswith("+"):
            s = "+" + s
        parsed = phonenumbers.parse(s, None)
        name = geocoder.description_for_number(parsed, "en")
        return name or "Unknown"
    except Exception:
        return "Unknown"


@lru_cache(maxsize=50_000)
def get_country_lru(num_str: str) -> str:
    return get_country_cached(num_str)


# ---------------------------------------------------------------------------
# Team CSV lookup
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=300)
def load_team_dataframe(path: str | None = None) -> dict[str, dict[str, str]]:
    settings = get_settings()
    file_path = Path(path or settings["team_file"])
    candidates = [file_path, ROOT / "Numbers_Export.csv", Path("Numbers_Export.csv")]
    for fp in candidates:
        try:
            if not fp.exists():
                continue
            df = pd.read_csv(fp, low_memory=False)
            cols = {c.lower().strip(): c for c in df.columns}
            phone_col = cols.get("phone number") or cols.get("number") or list(df.columns)[0]
            status_col = cols.get("status")
            range_col = cols.get("range")
            out: dict[str, dict[str, str]] = {}
            for _, row in df.iterrows():
                phone = str(row[phone_col]).split(".")[0].strip()
                if not phone or phone.lower() == "nan":
                    continue
                status = str(row[status_col]).strip() if status_col else ""
                member = status.replace("Allocated: ", "").replace("allocated: ", "").strip()
                rng = str(row[range_col]).strip() if range_col else ""
                if member in IGNORE_TEAM_MEMBERS:
                    continue
                out[phone] = {"MemberName": member, "Range": rng}
            return out
        except Exception as exc:
            log_event("team_csv_error", str(exc), path=str(fp))
    return {}


def enrich_dataframe(df: pd.DataFrame, team_data: dict | None = None, limit: int | None = None) -> pd.DataFrame:
    """Add Country / Team Member / Range / display Time columns."""
    if df is None or df.empty:
        return pd.DataFrame(
            columns=["Time", "Panel", "CLI", "Number", "Country", "Message", "Team Member", "Range", "dt"]
        )

    work = df.copy()
    if limit:
        work = work.head(int(limit))

    if "num" not in work.columns and "number" in work.columns:
        work["num"] = work["number"]
    if "cli" not in work.columns:
        work["cli"] = "UNKNOWN"
    if "message" not in work.columns:
        work["message"] = ""
    if "panel" not in work.columns:
        work["panel"] = "UNKNOWN"

    work["num_clean"] = work["num"].astype(str).str.split(".").str[0].str.strip()

    team_data = team_data if team_data is not None else load_team_dataframe()
    members, ranges, countries = [], [], []
    for num in work["num_clean"]:
        countries.append(get_country_cached(num))
        info = team_data.get(num)
        if info:
            members.append(info.get("MemberName", ""))
            ranges.append(info.get("Range", ""))
        else:
            members.append("")
            ranges.append("")

    work["Team Member"] = members
    work["Range"] = ranges
    work["Country"] = countries

    if "dt" in work.columns:
        work["Time"] = pd.to_datetime(work["dt"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        work["Time"] = ""

    out = work.rename(columns={"panel": "Panel", "cli": "CLI", "num": "Number", "message": "Message"})
    cols = ["Time", "Panel", "CLI", "Number", "Country", "Message", "Team Member", "Range"]
    if "dt" in out.columns:
        cols.append("dt")
    for c in cols:
        if c not in out.columns:
            out[c] = ""
    return out[cols]


# ---------------------------------------------------------------------------
# Filtering / search
# ---------------------------------------------------------------------------
def apply_search(
    df: pd.DataFrame,
    *,
    cli: str = "",
    country: str = "",
    number: str = "",
    message: str = "",
    api: str = "All",
    member: str = "",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    mode: str = "Contains",
    use_regex: bool = False,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    out = df.copy()

    def _match(series: pd.Series, q: str) -> pd.Series:
        if not q:
            return pd.Series([True] * len(series), index=series.index)
        s = series.astype(str)
        if use_regex:
            try:
                return s.str.contains(q, case=False, na=False, regex=True)
            except re.error:
                return s.str.contains(re.escape(q), case=False, na=False, regex=True)
        q_low = q.lower()
        s_low = s.str.lower()
        if mode == "Starts with":
            return s_low.str.startswith(q_low)
        if mode == "Ends with":
            return s_low.str.endswith(q_low)
        return s_low.str.contains(q_low, na=False, regex=False)

    if "CLI" in out.columns:
        out = out[_match(out["CLI"], cli)]
    if "Country" in out.columns and country and country != "All":
        out = out[out["Country"] == country]
    if "Number" in out.columns:
        out = out[_match(out["Number"], number)]
    if "Message" in out.columns:
        out = out[_match(out["Message"], message)]
    if api and api != "All" and "Panel" in out.columns:
        out = out[out["Panel"].astype(str).str.upper() == api.upper()]
    if member and member != "All" and "Team Member" in out.columns:
        out = out[out["Team Member"] == member]

    if "dt" in out.columns:
        dts = pd.to_datetime(out["dt"], errors="coerce")
        if date_from is not None:
            out = out[dts >= pd.Timestamp(date_from)]
        if date_to is not None:
            end = pd.Timestamp(date_to) + pd.Timedelta(days=1)
            out = out[dts < end]

    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------
def compute_kpis(df: pd.DataFrame, tz: str = "UTC") -> dict[str, Any]:
    empty = {
        "total_otp": 0,
        "today_otp": 0,
        "min5_otp": 0,
        "unique_numbers": 0,
        "unique_cli": 0,
        "countries": 0,
        "matched": 0,
        "avg_delay_sec": 0.0,
        "top_cli": [],
        "lamix_count": 0,
        "purple_count": 0,
    }
    if df is None or df.empty:
        return empty

    now = datetime.now(ZoneInfo(tz)).replace(tzinfo=None) if tz else datetime.now()
    work = df.copy()
    if "dt" not in work.columns:
        return empty
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work = work.dropna(subset=["dt"])

    today = now.date()
    min5 = now - timedelta(minutes=5)

    matched = 0
    if "Team Member" in work.columns:
        matched = int((work["Team Member"].astype(str).str.strip() != "").sum())

    delays = (now - work["dt"]).dt.total_seconds()
    avg_delay = float(delays.clip(lower=0).mean()) if len(delays) else 0.0

    top_cli = []
    if "CLI" in work.columns:
        recent = work[work["dt"] >= min5]
        if not recent.empty:
            vc = recent["CLI"].value_counts().head(3)
            top_cli = [{"name": str(i), "count": int(c)} for i, c in vc.items()]

    return {
        "total_otp": int(len(work)),
        "today_otp": int((work["dt"].dt.date == today).sum()),
        "min5_otp": int((work["dt"] >= min5).sum()),
        "unique_numbers": int(work["Number"].nunique()) if "Number" in work.columns else 0,
        "unique_cli": int(work["CLI"].nunique()) if "CLI" in work.columns else 0,
        "countries": int(work["Country"].nunique()) if "Country" in work.columns else 0,
        "matched": matched,
        "avg_delay_sec": round(avg_delay, 1),
        "top_cli": top_cli,
        "lamix_count": int((work["Panel"].astype(str).str.upper() == "LAMIX").sum()) if "Panel" in work.columns else 0,
        "purple_count": int((work["Panel"].astype(str).str.upper() == "PURPLE").sum()) if "Panel" in work.columns else 0,
    }


def trend_arrow(current: float, previous: float) -> str:
    if previous <= 0:
        return "→"
    if current > previous * 1.05:
        return "↑"
    if current < previous * 0.95:
        return "↓"
    return "→"


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="OTP")
    return buf.getvalue()


def df_to_json_bytes(df: pd.DataFrame) -> bytes:
    return df.to_json(orient="records", date_format="iso", force_ascii=False).encode("utf-8")


def df_to_pdf_bytes(df: pd.DataFrame, title: str = "UTS Hunters Export") -> bytes:
    """Lightweight PDF export via reportlab if available, else plain text PDF-ish fallback."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
        styles = getSampleStyleSheet()
        story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
        show = df.head(200).fillna("").astype(str)
        data = [list(show.columns)] + show.values.tolist()
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B1224")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#00D4FF")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#1a3a70")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#081224")),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.whitesmoke),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#081224"), colors.HexColor("#0B1224")]),
                ]
            )
        )
        story.append(table)
        doc.build(story)
        return buf.getvalue()
    except Exception as exc:
        log_event("pdf_export_fallback", str(exc))
        # Minimal valid-ish PDF with text dump
        content = title + "\n\n" + df.head(100).to_string(index=False)
        # plain bytes labeled as .txt content inside pdf container is messy; return text bytes
        return content.encode("utf-8")


def highlight_team_rows(row: pd.Series) -> list[str]:
    if str(row.get("Team Member", "")).strip():
        return [
            "background-color:rgba(0,212,255,.10);color:#00D4FF;font-weight:600;border-left:3px solid #00D4FF"
        ] * len(row)
    return [""] * len(row)


def inject_css(path: Path | str | None = None) -> None:
    css_path = Path(path or ROOT / "styles.css")
    try:
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception as exc:
        log_event("css_load_error", str(exc))


def touch_activity() -> None:
    st.session_state["last_activity"] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def session_expired(timeout_min: int) -> bool:
    raw = st.session_state.get("last_activity")
    if not raw:
        return False
    try:
        last = datetime.fromisoformat(raw)
        return datetime.now(timezone.utc).replace(tzinfo=None) - last > timedelta(minutes=int(timeout_min))
    except Exception:
        return False


def push_search_history(item: dict[str, Any], limit: int = 12) -> None:
    hist: list = st.session_state.setdefault("search_history", [])
    hist.insert(0, item)
    st.session_state["search_history"] = hist[:limit]


def system_info() -> dict[str, Any]:
    import platform
    import sys

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "streamlit": getattr(st, "__version__", "unknown"),
        "app_root": str(ROOT),
        "time_utc": datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
    }
