#!/usr/bin/env python3
"""
UTS Hunters — headless OTP WhatsApp alert worker (no Streamlit / no browser).

Why this exists
---------------
Streamlit only executes app.py inside a live browser WebSocket session.
HTTP keep-alive pings (curl, UptimeRobot, GitHub Actions ping) do NOT run
process_otp_alerts(). This script is the real 24/7 engine.

Run locally:
  python alert_worker.py

Run via GitHub Actions every 5 minutes (see .github/workflows/otp_alert_worker.yml).
Credentials come from environment variables (same names as Streamlit secrets).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import phonenumbers
import requests
from phonenumbers import geocoder
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent
STATE_PATH = Path(os.environ.get("ALERT_STATE_PATH", str(ROOT / "data" / "alert_state.json")))
TEAM_FILE = ROOT / "Numbers_Export.csv"

DEFAULTS: dict[str, Any] = {
    "LAMIX_URL": "http://51.77.216.195/crapi/lamix/viewstats",
    "LAMIX_TOKEN": "",
    "PURPLE_URL": "http://137.74.1.203/crapi/reseller/mdr.php",
    "PURPLE_TOKEN": "",
    "API_TIMEOUT": "12",
    "API_RETRIES": "2",
    "LAMIX_RECORDS": "400",
    "PURPLE_RECORDS": "2000",
    "PURPLE_LOOKBACK_DAYS": "30",
    "WHATSAPP_ALERTS_ENABLED": "true",
    "WHATSAPP_THRESHOLD": "1",
    "WHATSAPP_WINDOW_MIN": "5",
    "WHATSAPP_COOLDOWN_MIN": "5",
    "WHATSAPP_PROVIDER": "greenapi",
    "WHATSAPP_WEBHOOK_URL": "",
    "CALLMEBOT_PHONE": "",
    "CALLMEBOT_APIKEY": "",
    "GREENAPI_ID_INSTANCE": "",
    "GREENAPI_API_TOKEN": "",
    "GREENAPI_API_URL": "https://api.green-api.com",
    "GREENAPI_GROUP_ID": "",
    "META_WA_TOKEN": "",
    "META_WA_PHONE_ID": "",
    "META_WA_TO": "",
    "TWILIO_SID": "",
    "TWILIO_TOKEN": "",
    "TWILIO_WA_FROM": "",
    "TWILIO_WA_TO": "",
}

_FLAGS: dict[str, str] = {
    "Malaysia": "🇲🇾",
    "Singapore": "🇸🇬",
    "Indonesia": "🇮🇩",
    "Pakistan": "🇵🇰",
    "India": "🇮🇳",
    "United Arab Emirates": "🇦🇪",
    "United Kingdom": "🇬🇧",
    "United States": "🇺🇸",
    "Russia": "🇷🇺",
    "Georgia": "🇬🇪",
    "Bangladesh": "🇧🇩",
    "Philippines": "🇵🇭",
    "Thailand": "🇹🇭",
    "Vietnam": "🇻🇳",
    "China": "🇨🇳",
    "Hong Kong": "🇭🇰",
    "Taiwan": "🇹🇼",
    "Japan": "🇯🇵",
    "South Korea": "🇰🇷",
    "Saudi Arabia": "🇸🇦",
    "Qatar": "🇶🇦",
    "Kuwait": "🇰🇼",
    "Oman": "🇴🇲",
    "Bahrain": "🇧🇭",
    "Turkey": "🇹🇷",
    "Egypt": "🇪🇬",
    "Nigeria": "🇳🇬",
    "South Africa": "🇿🇦",
    "Canada": "🇨🇦",
    "Australia": "🇦🇺",
    "Germany": "🇩🇪",
    "France": "🇫🇷",
    "Italy": "🇮🇹",
    "Spain": "🇪🇸",
    "Netherlands": "🇳🇱",
    "Brazil": "🇧🇷",
    "Mexico": "🇲🇽",
}


def env(key: str, default: str | None = None) -> str:
    if key in os.environ and str(os.environ.get(key, "")).strip() != "":
        return str(os.environ.get(key, "")).strip()
    # Also accept lowercase
    low = key.lower()
    if low in os.environ and str(os.environ.get(low, "")).strip() != "":
        return str(os.environ.get(low, "")).strip()
    if default is not None:
        return default
    return str(DEFAULTS.get(key, ""))


def env_bool(key: str, default: bool = True) -> bool:
    raw = env(key, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on", "y"}


def env_int(key: str, default: int) -> int:
    try:
        return int(float(env(key, str(default))))
    except Exception:
        return default


def log(msg: str, **extra: Any) -> None:
    payload = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "msg": msg, **extra}
    print(json.dumps(payload, default=str), flush=True)


def settings() -> dict[str, Any]:
    return {
        "lamix_url": env("LAMIX_URL"),
        "lamix_token": env("LAMIX_TOKEN"),
        "purple_url": env("PURPLE_URL"),
        "purple_token": env("PURPLE_TOKEN"),
        "api_timeout": env_int("API_TIMEOUT", 12),
        "api_retries": env_int("API_RETRIES", 2),
        "lamix_records": env_int("LAMIX_RECORDS", 400),
        "purple_records": env_int("PURPLE_RECORDS", 2000),
        "purple_lookback_days": env_int("PURPLE_LOOKBACK_DAYS", 30),
        "whatsapp_alerts_enabled": env_bool("WHATSAPP_ALERTS_ENABLED", True),
        "whatsapp_threshold": env_int("WHATSAPP_THRESHOLD", 1),
        "whatsapp_window_min": env_int("WHATSAPP_WINDOW_MIN", 5),
        "whatsapp_cooldown_min": env_int("WHATSAPP_COOLDOWN_MIN", 5),
        "whatsapp_provider": env("WHATSAPP_PROVIDER", "greenapi").lower(),
        "whatsapp_webhook_url": env("WHATSAPP_WEBHOOK_URL"),
        "callmebot_phone": env("CALLMEBOT_PHONE"),
        "callmebot_apikey": env("CALLMEBOT_APIKEY"),
        "greenapi_id_instance": env("GREENAPI_ID_INSTANCE"),
        "greenapi_api_token": env("GREENAPI_API_TOKEN"),
        "greenapi_api_url": env("GREENAPI_API_URL", "https://api.green-api.com"),
        "greenapi_group_id": env("GREENAPI_GROUP_ID"),
        "meta_wa_token": env("META_WA_TOKEN"),
        "meta_wa_phone_id": env("META_WA_PHONE_ID"),
        "meta_wa_to": env("META_WA_TO"),
        "twilio_sid": env("TWILIO_SID"),
        "twilio_token": env("TWILIO_TOKEN"),
        "twilio_wa_from": env("TWILIO_WA_FROM"),
        "twilio_wa_to": env("TWILIO_WA_TO"),
    }


def build_session(retries: int = 2) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=16)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "UTS-Hunters-AlertWorker/2.0", "Accept": "application/json"})
    return session


def normalize_item(item: dict[str, Any], panel: str) -> dict[str, Any] | None:
    dt_raw = item.get("dt") or item.get("datetime") or item.get("time") or item.get("date")
    num = item.get("num") or item.get("number") or item.get("phone") or item.get("msisdn")
    if num is None or dt_raw is None:
        return None
    cli = item.get("cli") or item.get("ident") or item.get("sender") or "UNKNOWN"
    message = item.get("message") or item.get("msg") or item.get("text") or ""
    return {
        "panel": panel,
        "dt_raw": dt_raw,
        "num": str(num).split(".")[0].strip(),
        "cli": str(cli).strip() or "UNKNOWN",
        "message": str(message),
    }


def fetch_lamix(session: requests.Session, cfg: dict[str, Any]) -> list[dict]:
    if not cfg["lamix_url"] or not cfg["lamix_token"]:
        log("lamix_skip", reason="missing url/token")
        return []
    r = session.get(
        cfg["lamix_url"],
        params={"token": cfg["lamix_token"], "records": cfg["lamix_records"]},
        timeout=cfg["api_timeout"],
    )
    if r.status_code != 200:
        log("lamix_fail", status=r.status_code, body=r.text[:200])
        return []
    payload = r.json()
    raw = payload.get("data", []) if isinstance(payload, dict) else payload
    rows = []
    for item in raw or []:
        if isinstance(item, dict):
            n = normalize_item(item, "LAMIX")
            if n:
                rows.append(n)
    log("lamix_ok", records=len(rows))
    return rows


def fetch_purple(session: requests.Session, cfg: dict[str, Any]) -> list[dict]:
    if not cfg["purple_url"] or not cfg["purple_token"]:
        log("purple_skip", reason="missing url/token")
        return []
    now = datetime.now()
    params = {
        "token": cfg["purple_token"],
        "fromdate": (now - timedelta(days=cfg["purple_lookback_days"])).strftime("%Y-%m-%d %H:%M:%S"),
        "todate": now.strftime("%Y-%m-%d %H:%M:%S"),
        "records": cfg["purple_records"],
        "searchnumber": "",
        "searchcli": "",
    }
    r = session.get(cfg["purple_url"], params=params, timeout=max(cfg["api_timeout"], 12))
    if r.status_code != 200:
        log("purple_fail", status=r.status_code, body=r.text[:200])
        return []
    payload = r.json()
    if isinstance(payload, dict):
        raw = payload.get("data", [])
    elif isinstance(payload, list):
        raw = payload
    else:
        raw = []
    rows = []
    for item in raw or []:
        if isinstance(item, dict):
            n = normalize_item(item, "PURPLE")
            if n:
                rows.append(n)
    log("purple_ok", records=len(rows))
    return rows


def merge_records(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["Panel", "CLI", "Number", "Message", "Country", "dt"])
    df = pd.DataFrame(rows)
    df["dt"] = pd.to_datetime(df["dt_raw"], errors="coerce")
    df = df.dropna(subset=["dt"])
    df["num"] = df["num"].astype(str).str.split(".").str[0].str.strip()
    df["cli"] = df["cli"].astype(str)
    df["message"] = df["message"].astype(str)
    df = df.drop_duplicates(subset=["dt", "num", "cli", "message", "panel"], keep="first")
    df = df.sort_values("dt", ascending=False).reset_index(drop=True)
    # Lightweight country (optional; failure → Unknown)
    countries = []
    for num in df["num"]:
        try:
            s = str(num).strip()
            if not s.startswith("+"):
                s = "+" + s
            parsed = phonenumbers.parse(s, None)
            name = geocoder.description_for_number(parsed, "en") or "Unknown"
            countries.append(name)
        except Exception:
            countries.append("Unknown")
    df["Country"] = countries
    return df.rename(columns={"panel": "Panel", "cli": "CLI", "num": "Number", "message": "Message"})


def load_state() -> dict[str, Any]:
    try:
        if STATE_PATH.exists():
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception as exc:
        log("state_load_error", error=str(exc))
    return {
        "cooldown_until": 0.0,
        "last_cli": "",
        "last_hash": "",
        "last_sent": 0.0,
        "history": [],
    }


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
    tmp.replace(STATE_PATH)


def unique_templates(messages: pd.Series, limit: int = 8) -> list[str]:
    import re

    otp_re = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
    out: list[str] = []
    seen: set[str] = set()
    for raw in messages.fillna("").astype(str).tolist():
        t = otp_re.sub("{OTP}", raw)
        t = re.sub(r"\s+", " ", t).strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t[:160])
        if len(out) >= limit:
            break
    return out


def top_countries(series: pd.Series, limit: int = 8) -> list[tuple[str, int]]:
    if series is None or series.empty:
        return []
    vc = series.fillna("Unknown").astype(str).value_counts()
    return [(str(k), int(v)) for k, v in vc.head(limit).items()]


def flag(country: str) -> str:
    return _FLAGS.get(country, "🌍")


def circled(n: int) -> str:
    base = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
    return base[n - 1] if 1 <= n <= 10 else f"({n})"


def build_alert_message(
    *,
    cli: str,
    panel: str,
    total: int,
    main_country: str,
    templates: list[str],
    countries: list[tuple[str, int]],
) -> str:
    time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "🚨 UTS HUNTERS · OTP ALERT",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"📱 CLI   : {cli}",
        f"🔌 Panel : {panel}",
        f"📊 Count : {total} OTP(s) / 5 min",
        f"🌍 Main  : {flag(main_country)} {main_country}",
        f"⏰ Time  : {time_str}",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "📝 Message Templates",
        "",
    ]
    if templates:
        for i, tmpl in enumerate(templates, 1):
            lines.append(f"{circled(i)} {tmpl}")
            lines.append("")
    else:
        lines.append("① (no message body)")
        lines.append("")
    lines.extend(["━━━━━━━━━━━━━━━━━━", "", "🌍 Top Countries", ""])
    if countries:
        for name, cnt in countries:
            lines.append(f"{flag(name)} {name} : {cnt}")
    else:
        lines.append("🌍 Unknown : 0")
    lines.extend(["", "━━━━━━━━━━━━━━━━━━", "", "Status:", "LIVE · background worker"])
    return "\n".join(lines)


def evaluate_cli_windows(df: pd.DataFrame, *, window_min: int, threshold: int) -> list[dict[str, Any]]:
    if df is None or df.empty or "CLI" not in df.columns or "dt" not in df.columns:
        return []
    work = df.copy()
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work = work.dropna(subset=["dt"])
    if work.empty:
        return []
    now = work["dt"].max()
    wall = datetime.now()
    anchor = max(now.to_pydatetime() if hasattr(now, "to_pydatetime") else now, wall - timedelta(minutes=1))
    start = anchor - timedelta(minutes=int(window_min))
    recent = work[work["dt"] >= start]
    if recent.empty:
        return []
    hits: list[dict[str, Any]] = []
    for cli, grp in recent.groupby(recent["CLI"].astype(str), sort=False):
        total = int(len(grp))
        if total < max(1, int(threshold)):
            continue
        panel = "MIXED"
        if "Panel" in grp.columns:
            try:
                panel = str(grp["Panel"].astype(str).value_counts().idxmax())
            except Exception:
                panel = "MIXED"
        countries = top_countries(grp["Country"] if "Country" in grp.columns else pd.Series(dtype=str))
        templates = unique_templates(grp["Message"] if "Message" in grp.columns else pd.Series(dtype=str))
        hits.append(
            {
                "cli": str(cli),
                "panel": panel,
                "total": total,
                "main_country": countries[0][0] if countries else "Unknown",
                "templates": templates,
                "countries": countries,
            }
        )
    hits.sort(key=lambda h: h["total"], reverse=True)
    return hits


def send_greenapi(message: str, cfg: dict[str, Any]) -> dict[str, Any]:
    instance = cfg["greenapi_id_instance"]
    token = cfg["greenapi_api_token"]
    api_url = (cfg["greenapi_api_url"] or "https://api.green-api.com").rstrip("/")
    chat_id = cfg["greenapi_group_id"]
    if not instance or not token or not chat_id:
        return {"ok": False, "provider": "greenapi", "detail": "missing GREENAPI secrets"}
    if chat_id.isdigit():
        chat_id = f"{chat_id}@g.us"
    if not (chat_id.endswith("@g.us") or chat_id.endswith("@c.us")):
        return {"ok": False, "provider": "greenapi", "detail": "bad GREENAPI_GROUP_ID"}
    url = f"{api_url}/waInstance{instance}/sendMessage/{token}"
    r = requests.post(
        url,
        json={"chatId": chat_id, "message": message[:20000], "linkPreview": False},
        timeout=30,
    )
    ok = 200 <= r.status_code < 300
    detail = f"HTTP {r.status_code}"
    try:
        body = r.json()
        detail = f"{detail} {body}"
        if ok and not body.get("idMessage") and body.get("message"):
            ok = False
    except Exception:
        detail = f"{detail} {r.text[:240]}"
    return {"ok": ok, "provider": "greenapi", "detail": detail[:400]}


def send_callmebot(message: str, cfg: dict[str, Any]) -> dict[str, Any]:
    phone = cfg["callmebot_phone"].lstrip("+")
    apikey = cfg["callmebot_apikey"]
    if not phone or not apikey:
        return {"ok": False, "provider": "callmebot", "detail": "missing secrets"}
    url = (
        f"https://api.callmebot.com/whatsapp.php?phone={quote(phone)}"
        f"&text={quote(message)}&apikey={quote(apikey)}"
    )
    r = requests.get(url, timeout=20)
    return {"ok": r.status_code == 200, "provider": "callmebot", "detail": f"HTTP {r.status_code} {r.text[:200]}"}


def send_webhook(message: str, cfg: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    url = cfg["whatsapp_webhook_url"]
    if not url:
        return {"ok": False, "provider": "webhook", "detail": "missing WHATSAPP_WEBHOOK_URL"}
    r = requests.post(url, json={"message": message, "meta": meta, "source": "alert_worker"}, timeout=20)
    return {"ok": 200 <= r.status_code < 300, "provider": "webhook", "detail": f"HTTP {r.status_code}"}


def send_alert(message: str, cfg: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    provider = (cfg["whatsapp_provider"] or "log").lower()
    if provider in ("", "log", "none", "dry_run"):
        log("wa_dry_run", cli=meta.get("cli"), total=meta.get("total"), preview=message[:120])
        return {"ok": True, "provider": "log", "detail": "logged only"}
    if provider == "greenapi":
        return send_greenapi(message, cfg)
    if provider == "callmebot":
        return send_callmebot(message, cfg)
    if provider == "webhook":
        return send_webhook(message, cfg, meta)
    return {"ok": False, "provider": provider, "detail": f"unsupported provider: {provider}"}


def run_once(force: bool = False) -> int:
    cfg = settings()
    if not cfg["whatsapp_alerts_enabled"] and not force:
        log("disabled", hint="Set WHATSAPP_ALERTS_ENABLED=true")
        return 0

    missing_api = []
    if not cfg["lamix_token"] and not cfg["purple_token"]:
        missing_api.append("LAMIX_TOKEN or PURPLE_TOKEN")
    if missing_api:
        log("config_error", missing=missing_api)
        return 2

    if cfg["whatsapp_provider"] == "greenapi":
        need = [k for k in ("greenapi_id_instance", "greenapi_api_token", "greenapi_group_id") if not cfg[k]]
        if need:
            log("config_error", missing=need)
            return 2

    state = load_state()
    now_ts = time.time()
    cooldown_until = float(state.get("cooldown_until", 0) or 0)
    if not force and now_ts < cooldown_until:
        log("cooldown_active", seconds_left=int(cooldown_until - now_ts), last_cli=state.get("last_cli"))
        return 0

    session = build_session(retries=cfg["api_retries"])
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = {
            pool.submit(fetch_lamix, session, cfg): "LAMIX",
            pool.submit(fetch_purple, session, cfg): "PURPLE",
        }
        for fut in as_completed(futs):
            try:
                rows.extend(fut.result())
            except Exception as exc:
                log("fetch_error", api=futs[fut], error=str(exc))

    df = merge_records(rows)
    log("merged", records=int(len(df)))
    if df.empty:
        log("no_data")
        return 0

    hits = evaluate_cli_windows(
        df,
        window_min=cfg["whatsapp_window_min"],
        threshold=cfg["whatsapp_threshold"],
    )
    if not hits:
        log("no_hits", window_min=cfg["whatsapp_window_min"], threshold=cfg["whatsapp_threshold"])
        return 0

    hit = hits[0]
    msg = build_alert_message(
        cli=hit["cli"],
        panel=hit["panel"],
        total=hit["total"],
        main_country=hit["main_country"],
        templates=hit["templates"],
        countries=hit["countries"],
    )
    msg_hash = hashlib.sha256(msg.encode("utf-8")).hexdigest()
    last_hash = str(state.get("last_hash") or "")
    last_sent = float(state.get("last_sent") or 0)
    if not force and msg_hash == last_hash and (now_ts - last_sent) < 30:
        log("duplicate_suppressed", cli=hit["cli"])
        return 0

    meta = {"cli": hit["cli"], "panel": hit["panel"], "total": hit["total"], "country": hit["main_country"]}
    result = send_alert(msg, cfg, meta)
    log("send_result", **result, **meta)

    # Arm cooldown only on successful send (or dry-run)
    if result.get("ok"):
        cd = max(60, int(cfg["whatsapp_cooldown_min"]) * 60)
        state["cooldown_until"] = now_ts + cd
        state["last_cli"] = hit["cli"]
        state["last_hash"] = msg_hash
        state["last_sent"] = now_ts
        hist = list(state.get("history") or [])
        hist.insert(
            0,
            {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "cli": hit["cli"],
                "total": hit["total"],
                "provider": result.get("provider"),
                "ok": True,
            },
        )
        state["history"] = hist[:30]
        save_state(state)
        log("alert_sent", cli=hit["cli"], total=hit["total"], cooldown_min=cfg["whatsapp_cooldown_min"])
        return 0

    log("alert_failed", detail=result.get("detail"))
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    force = "--force" in argv
    try:
        return run_once(force=force)
    except Exception:
        log("fatal", error=traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
