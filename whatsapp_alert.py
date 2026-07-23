"""
SMART WHATSAPP OTP ALERT ENGINE
================================
Monitors the already-merged live dataframe (no extra API calls).

Trigger (per CLI):
  - rolling 5-minute window
  - ANY OTP activity (threshold default 1)
  - ONLY TOP 1 CLI
  - GLOBAL COOLDOWN: only 1 alert every 5 minutes
  - FILE-BASED cooldown (shared across sessions + workers)

IMPORTANT
---------
Streamlit only runs this module while a real browser WebSocket session is open.
HTTP keep-alive pings do NOT execute process_otp_alerts().
For 24/7 alerts use alert_worker.py via GitHub Actions (otp_alert_worker.yml).
"""
from __future__ import annotations

import hashlib
import html
import re
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

from config import ALERT_STATE_FILE, DATA_DIR, get_settings
from utils import log_event

# ---------------------------------------------------------------------------
# Global lock for thread-safe alert processing
# ---------------------------------------------------------------------------
_ALERT_PROCESS_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLD = 1  # ANY OTP
DEFAULT_WINDOW_MIN = 5
DEFAULT_COOLDOWN_MIN = 5
MAX_TEMPLATES = 8
MAX_COUNTRIES = 8
MAX_ALERTS_PER_TICK = 5

# OTP digit runs 4–8 long
_OTP_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|\w+);")
_WS_RE = re.compile(r"\s+")

# Country flags
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
    "Angola": "🇦🇴",
    "Palestine": "🇵🇸",
    "Saudi Arabia": "🇸🇦",
    "Bangladesh": "🇧🇩",
    "Philippines": "🇵🇭",
    "Thailand": "🇹🇭",
    "Vietnam": "🇻🇳",
    "Nigeria": "🇳🇬",
    "Turkey": "🇹🇷",
    "Germany": "🇩🇪",
    "France": "🇫🇷",
    "Canada": "🇨🇦",
    "Australia": "🇦🇺",
}


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------
def normalize_template(message: str) -> str:
    if message is None:
        return ""
    text = str(message)
    try:
        text = html.unescape(text)
    except Exception:
        pass
    text = _ENTITY_RE.sub(" ", text)
    text = _OTP_RE.sub("******", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def unique_templates(messages: pd.Series, limit: int = MAX_TEMPLATES) -> list[str]:
    seen: OrderedDict[str, None] = OrderedDict()
    for raw in messages.fillna("").astype(str):
        tmpl = normalize_template(raw)
        if not tmpl:
            continue
        if tmpl not in seen:
            seen[tmpl] = None
        if len(seen) >= limit:
            break
    return list(seen.keys())


def top_countries(series: pd.Series, limit: int = MAX_COUNTRIES) -> list[tuple[str, int]]:
    if series is None or series.empty:
        return []
    vc = series.fillna("Unknown").astype(str).value_counts().head(limit)
    return [(str(k), int(v)) for k, v in vc.items()]


def _flag(country: str) -> str:
    return _FLAGS.get(country, "🌍")


def _circled(n: int) -> str:
    if 1 <= n <= 20:
        return chr(0x2460 + n - 1)
    return f"{n}."


# ---------------------------------------------------------------------------
# Message builder
# ---------------------------------------------------------------------------
def build_alert_message(
    *,
    cli: str,
    panel: str,
    total: int,
    main_country: str,
    templates: list[str],
    countries: list[tuple[str, int]],
    when: datetime | None = None,
) -> str:
    ts = when or datetime.now()
    time_str = ts.strftime("%I:%M %p").lstrip("0")

    lines = [
        "🚨 OTP TRAFFIC ALERT",
        "",
        f"⚠ CLI : {cli}",
        f"📡 Panel : {panel}",
        f"🌍 Main Country : {main_country or 'Unknown'}",
        f"📊 Total OTP : {total}",
        f"⏰ Time : {time_str}",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "📝 Message Templates",
        "",
    ]
    if templates:
        for i, tmpl in enumerate(templates, 1):
            lines.append(f"{_circled(i)} {tmpl}")
            lines.append("")
    else:
        lines.append("① (no message body)")
        lines.append("")

    lines.extend([
        "━━━━━━━━━━━━━━━━━━",
        "",
        "🌍 Top Countries",
        "",
    ])
    if countries:
        for name, cnt in countries:
            lines.append(f"{_flag(name)} {name} : {cnt}")
    else:
        lines.append("🌍 Unknown : 0")

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "Status:",
        "LIVE",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------
def send_whatsapp_alert(message: str, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    provider = str(settings.get("whatsapp_provider") or "log").strip().lower()
    meta = meta or {}

    try:
        hist = st.session_state.setdefault("wa_alert_history", [])
        hist.insert(0, {
            "ts": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
            "provider": provider,
            "cli": meta.get("cli"),
            "total": meta.get("total"),
            "preview": message[:180],
        })
        st.session_state["wa_alert_history"] = hist[:30]
    except Exception:
        pass

    try:
        if provider in ("", "log", "none", "dry_run"):
            log_event("wa_alert_log", "dry-run alert", cli=meta.get("cli"), total=meta.get("total"))
            return {"ok": True, "provider": "log", "detail": "logged only"}

        if provider == "callmebot":
            return _send_callmebot(message, settings)
        if provider == "greenapi":
            return _send_greenapi(message, settings)
        if provider == "webhook":
            return _send_webhook(message, settings, meta)
        if provider == "meta":
            return _send_meta(message, settings)
        if provider == "twilio":
            return _send_twilio(message, settings)

        log_event("wa_alert_unknown_provider", provider)
        return {"ok": False, "provider": provider, "detail": f"unknown provider: {provider}"}
    except Exception as exc:
        log_event("wa_alert_send_error", str(exc), provider=provider)
        return {"ok": False, "provider": provider, "detail": str(exc)}


def _send_callmebot(message: str, settings: dict[str, Any]) -> dict[str, Any]:
    phone = str(settings.get("callmebot_phone") or "").strip().lstrip("+")
    apikey = str(settings.get("callmebot_apikey") or "").strip()
    if not phone or not apikey:
        return {"ok": False, "provider": "callmebot", "detail": "CALLMEBOT_PHONE / CALLMEBOT_APIKEY missing"}
    url = f"https://api.callmebot.com/whatsapp.php?phone={quote(phone)}&text={quote(message)}&apikey={quote(apikey)}"
    r = requests.get(url, timeout=20)
    ok = r.status_code == 200
    return {"ok": ok, "provider": "callmebot", "detail": f"HTTP {r.status_code} {r.text[:200]}"}


def _send_greenapi(message: str, settings: dict[str, Any]) -> dict[str, Any]:
    instance = str(settings.get("greenapi_id_instance") or "").strip()
    token = str(settings.get("greenapi_api_token") or "").strip()
    api_url = str(settings.get("greenapi_api_url") or "https://api.green-api.com").strip().rstrip("/")
    chat_id = str(settings.get("greenapi_group_id") or "").strip()

    if not instance or not token or not chat_id:
        return {
            "ok": False,
            "provider": "greenapi",
            "detail": "GREENAPI_ID_INSTANCE / GREENAPI_API_TOKEN / GREENAPI_GROUP_ID missing",
        }

    if chat_id.isdigit():
        chat_id = f"{chat_id}@g.us"
    if not (chat_id.endswith("@g.us") or chat_id.endswith("@c.us")):
        return {
            "ok": False,
            "provider": "greenapi",
            "detail": "GREENAPI_GROUP_ID must look like 1203630...@g.us",
        }

    url = f"{api_url}/waInstance{instance}/sendMessage/{token}"
    payload = {
        "chatId": chat_id,
        "message": message[:20000],
        "linkPreview": False,
    }
    r = requests.post(url, json=payload, timeout=30)
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


def _send_webhook(message: str, settings: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    url = str(settings.get("whatsapp_webhook_url") or "").strip()
    if not url:
        return {"ok": False, "provider": "webhook", "detail": "WHATSAPP_WEBHOOK_URL missing"}
    payload = {"text": message, "message": message, **meta}
    r = requests.post(url, json=payload, timeout=20)
    ok = 200 <= r.status_code < 300
    return {"ok": ok, "provider": "webhook", "detail": f"HTTP {r.status_code}"}


def _send_meta(message: str, settings: dict[str, Any]) -> dict[str, Any]:
    token = str(settings.get("meta_wa_token") or "").strip()
    phone_id = str(settings.get("meta_wa_phone_id") or "").strip()
    to = str(settings.get("meta_wa_to") or "").strip()
    if not token or not phone_id or not to:
        return {
            "ok": False,
            "provider": "meta",
            "detail": "META_WA_TOKEN / META_WA_PHONE_ID / META_WA_TO missing",
        }
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "messaging_product": "whatsapp",
        "to": to.lstrip("+"),
        "type": "text",
        "text": {"preview_url": False, "body": message[:4096]},
    }
    r = requests.post(url, headers=headers, json=body, timeout=20)
    ok = 200 <= r.status_code < 300
    return {"ok": ok, "provider": "meta", "detail": f"HTTP {r.status_code} {r.text[:200]}"}


def _send_twilio(message: str, settings: dict[str, Any]) -> dict[str, Any]:
    sid = str(settings.get("twilio_sid") or "").strip()
    token = str(settings.get("twilio_token") or "").strip()
    frm = str(settings.get("twilio_wa_from") or "").strip()
    to = str(settings.get("twilio_wa_to") or "").strip()
    if not sid or not token or not frm or not to:
        return {"ok": False, "provider": "twilio", "detail": "Twilio WA secrets missing"}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = {"From": frm, "To": to, "Body": message[:1600]}
    r = requests.post(url, data=data, auth=(sid, token), timeout=20)
    ok = 200 <= r.status_code < 300
    return {"ok": ok, "provider": "twilio", "detail": f"HTTP {r.status_code} {r.text[:200]}"}


def send_whatsapp_alert_async(message: str, meta: dict[str, Any] | None = None) -> None:
    def _run() -> None:
        try:
            send_whatsapp_alert(message, meta=meta)
        except Exception as exc:
            log_event("wa_alert_async_error", str(exc))
    threading.Thread(target=_run, name="wa-alert", daemon=True).start()


# ---------------------------------------------------------------------------
# GLOBAL COOLDOWN - FILE BASED (survives browser close / multi-session)
# ---------------------------------------------------------------------------
def _state_path():
    try:
        return ALERT_STATE_FILE
    except Exception:
        from pathlib import Path
        return Path(__file__).resolve().parent / "data" / "alert_state.json"


def _load_file_state() -> dict[str, Any]:
    path = _state_path()
    try:
        if path.exists():
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception as exc:
        log_event("wa_state_load_error", str(exc))
    return {
        "cooldown_until": 0.0,
        "last_cli": "",
        "last_hash": "",
        "last_sent": 0.0,
        "history": [],
    }


def _save_file_state(state: dict[str, Any]) -> None:
    path = _state_path()
    try:
        import json
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        log_event("wa_state_save_error", str(exc))


def _get_cooldown_state() -> dict[str, Any]:
    """Prefer session mirror for UI, but always backed by disk."""
    file_state = _load_file_state()
    try:
        sess = st.session_state.get("wa_global_cooldown")
        if isinstance(sess, dict):
            # Merge: take the more restrictive (later) cooldown
            fu = float(file_state.get("cooldown_until", 0) or 0)
            su = float(sess.get("cooldown_until", 0) or 0)
            if su > fu:
                file_state = {**file_state, **sess}
        st.session_state["wa_global_cooldown"] = file_state
    except Exception:
        pass
    return file_state


def _is_global_cooling(now_ts: float) -> bool:
    state = _get_cooldown_state()
    until = float(state.get("cooldown_until", 0) or 0)
    return now_ts < until


def _arm_global_cooldown(seconds: float, now_ts: float, cli: str, msg_hash: str) -> None:
    state = _get_cooldown_state()
    state["cooldown_until"] = now_ts + seconds
    state["last_cli"] = cli
    state["last_hash"] = msg_hash
    state["last_sent"] = now_ts
    try:
        st.session_state["wa_global_cooldown"] = state
    except Exception:
        pass
    _save_file_state(state)


def _alert_config() -> dict[str, Any]:
    settings = get_settings()
    enabled = settings.get("whatsapp_alerts_enabled", True)
    try:
        enabled = bool(st.session_state.get("wa_alerts_enabled", enabled))
    except Exception:
        enabled = bool(enabled)
    return {
        "enabled": enabled,
        "threshold": int(settings.get("whatsapp_threshold", 1) or 1),
        "window_min": int(settings.get("whatsapp_window_min", 5) or 5),
        "cooldown_min": int(settings.get("whatsapp_cooldown_min", 5) or 5),
    }


def evaluate_cli_windows(df: pd.DataFrame, *, window_min: int, threshold: int) -> list[dict[str, Any]]:
    if df is None or df.empty or "CLI" not in df.columns:
        return []
    if "dt" not in df.columns:
        return []

    work = df.copy()
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work = work.dropna(subset=["dt"])
    if work.empty:
        return []

    now = work["dt"].max()
    if pd.isna(now):
        return []
    wall = datetime.now()
    anchor = max(now.to_pydatetime() if hasattr(now, "to_pydatetime") else now, wall - timedelta(minutes=1))
    start = anchor - timedelta(minutes=int(window_min))
    recent = work[work["dt"] >= start]
    if recent.empty:
        return []

    hits: list[dict[str, Any]] = []
    for cli, grp in recent.groupby(recent["CLI"].astype(str), sort=False):
        total = int(len(grp))
        if total < 1:
            continue
        panel = "MIXED"
        if "Panel" in grp.columns:
            try:
                panel = str(grp["Panel"].astype(str).value_counts().idxmax())
            except Exception:
                panel = "MIXED"
        countries = top_countries(grp["Country"] if "Country" in grp.columns else pd.Series(dtype=str))
        main_country = countries[0][0] if countries else "Unknown"
        templates = unique_templates(grp["Message"] if "Message" in grp.columns else pd.Series(dtype=str))
        hits.append({
            "cli": str(cli),
            "panel": panel,
            "total": total,
            "main_country": main_country,
            "templates": templates,
            "countries": countries,
            "window_start": start,
            "window_end": anchor,
        })

    hits.sort(key=lambda h: h["total"], reverse=True)
    return hits


def process_otp_alerts(df: pd.DataFrame, *, force: bool = False) -> list[dict[str, Any]]:
    """Run inside a live Streamlit session only.

    For browser-closed / 24x7 delivery use alert_worker.py (GitHub Actions).
    """
    if not _ALERT_PROCESS_LOCK.acquire(blocking=False):
        return []

    try:
        cfg = _alert_config()
        if not cfg["enabled"] and not force:
            return []

        now_ts = time.time()
        try:
            last = float(st.session_state.get("wa_last_scan_ts", 0) or 0)
        except Exception:
            last = 0.0
        if not force and (now_ts - last) < 10:
            return []
        try:
            st.session_state["wa_last_scan_ts"] = now_ts
        except Exception:
            pass

        if _is_global_cooling(now_ts):
            return []

        try:
            hits = evaluate_cli_windows(
                df,
                window_min=int(cfg["window_min"]),
                threshold=int(cfg["threshold"]),
            )
        except Exception as exc:
            log_event("wa_eval_error", str(exc))
            return []

        fired: list[dict[str, Any]] = []
        top_hits = hits[:1]
        cooldown_sec = max(60, int(cfg["cooldown_min"]) * 60)

        for hit in top_hits:
            cli = hit["cli"]

            msg = build_alert_message(
                cli=cli,
                panel=hit["panel"],
                total=hit["total"],
                main_country=hit["main_country"],
                templates=hit["templates"],
                countries=hit["countries"],
            )

            msg_hash = hashlib.sha256(msg.encode("utf-8")).hexdigest()
            state = _get_cooldown_state()
            last_hash = state.get("last_hash", "")
            last_sent = float(state.get("last_sent", 0) or 0)

            if msg_hash == last_hash and (now_ts - last_sent) < 30:
                continue

            meta = {"cli": cli, "panel": hit["panel"], "total": hit["total"], "country": hit["main_country"]}

            # Arm cooldown before send to prevent double-fire on fast reruns
            _arm_global_cooldown(cooldown_sec, now_ts, cli, msg_hash)
            send_whatsapp_alert_async(msg, meta=meta)

            fired.append({**meta, "message": msg})
            log_event("wa_alert_triggered", "OTP traffic", **meta)

            try:
                st.toast(
                    f"🚨 WA alert · {cli} · {hit['total']} OTPs | Next in {cfg['cooldown_min']}min",
                    icon="📱",
                )
            except Exception:
                pass

        if fired:
            try:
                st.session_state["wa_last_fired"] = fired
            except Exception:
                pass
        return fired

    finally:
        _ALERT_PROCESS_LOCK.release()


# ---------------------------------------------------------------------------
# GREEN-API Helper Functions
# ---------------------------------------------------------------------------
def _greenapi_base(settings: dict[str, Any] | None = None) -> tuple[str, str, str] | dict[str, Any]:
    settings = settings or get_settings()
    instance = str(settings.get("greenapi_id_instance") or "").strip()
    token = str(settings.get("greenapi_api_token") or "").strip()
    api_url = str(settings.get("greenapi_api_url") or "https://api.green-api.com").strip().rstrip("/")
    if not instance or not token:
        return {
            "ok": False,
            "detail": "GREENAPI_ID_INSTANCE / GREENAPI_API_TOKEN missing",
            "groups": [],
        }
    return api_url, instance, token


def list_greenapi_groups(count: int = 200) -> dict[str, Any]:
    base = _greenapi_base()
    if isinstance(base, dict):
        return base
    api_url, instance, token = base
    found: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    try:
        url = f"{api_url}/waInstance{instance}/getChats/{token}"
        r = requests.get(url, params={"count": int(count)}, timeout=30)
        if 200 <= r.status_code < 300:
            data = r.json() if r.text else []
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    cid = str(item.get("id") or item.get("chatId") or "")
                    ctype = str(item.get("type") or "").lower()
                    name = str(item.get("name") or "")
                    if cid.endswith("@g.us") or ctype == "group":
                        if cid.isdigit():
                            cid = f"{cid}@g.us"
                        if cid:
                            found[cid] = {
                                "chatId": cid,
                                "name": name or cid,
                                "type": ctype or "group",
                                "source": "getChats",
                            }
            elif isinstance(data, dict) and data.get("message"):
                errors.append(f"getChats: {data.get('message')}")
        else:
            errors.append(f"getChats HTTP {r.status_code}: {r.text[:180]}")
    except Exception as exc:
        errors.append(f"getChats error: {exc}")

    for journal in ("lastOutgoingMessages", "lastIncomingMessages"):
        try:
            url = f"{api_url}/waInstance{instance}/{journal}/{token}"
            r = requests.get(url, params={"minutes": 1440}, timeout=30)
            if not (200 <= r.status_code < 300):
                errors.append(f"{journal} HTTP {r.status_code}")
                continue
            data = r.json() if r.text else []
            if not isinstance(data, list):
                continue
            for item in data:
                if not isinstance(item, dict):
                    continue
                cid = str(item.get("chatId") or "")
                if not cid.endswith("@g.us"):
                    continue
                name = ""
                for key in ("chatName", "senderName", "name"):
                    if item.get(key):
                        name = str(item.get(key))
                        break
                prev = found.get(cid)
                found[cid] = {
                    "chatId": cid,
                    "name": (prev or {}).get("name") or name or cid,
                    "type": "group",
                    "source": (prev or {}).get("source", "") + f"+{journal}",
                }
        except Exception as exc:
            errors.append(f"{journal} error: {exc}")

    groups = sorted(found.values(), key=lambda g: (g.get("name") or g["chatId"]).lower())
    tip = (
        "Phone se target group OPEN karke koi message bhejo (e.g. 'id test'), "
        "10–20 sec wait, phir dubara Fetch dabao. "
        "Green-API purane silent groups nahi dikhata."
    )
    return {
        "ok": True,
        "groups": groups,
        "count": len(groups),
        "errors": errors,
        "tip": tip if not groups else "",
        "detail": f"Found {len(groups)} group(s)",
    }


def check_greenapi_state() -> dict[str, Any]:
    base = _greenapi_base()
    if isinstance(base, dict):
        return base
    api_url, instance, token = base
    try:
        url = f"{api_url}/waInstance{instance}/getStateInstance/{token}"
        r = requests.get(url, timeout=20)
        body = {}
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:200]}
        state = str(body.get("stateInstance") or body.get("state") or "")
        return {
            "ok": 200 <= r.status_code < 300,
            "state": state or "unknown",
            "detail": body,
            "authorized": state.lower() in {"authorized", "online", "connected"},
        }
    except Exception as exc:
        return {"ok": False, "state": "error", "detail": str(exc), "authorized": False}


def preview_alert_for_cli(df: pd.DataFrame, cli: str) -> str | None:
    if df is None or df.empty or not cli:
        return None
    sub = df[df["CLI"].astype(str).str.contains(str(cli), case=False, na=False)] if "CLI" in df.columns else df
    hits = evaluate_cli_windows(sub, window_min=5, threshold=1)
    if not hits:
        if sub.empty:
            return None
        templates = unique_templates(sub["Message"] if "Message" in sub.columns else pd.Series(dtype=str))
        countries = top_countries(sub["Country"] if "Country" in sub.columns else pd.Series(dtype=str))
        panel = "MIXED"
        if "Panel" in sub.columns and not sub.empty:
            try:
                panel = str(sub["Panel"].astype(str).value_counts().idxmax())
            except Exception:
                pass
        return build_alert_message(
            cli=cli,
            panel=panel,
            total=len(sub),
            main_country=countries[0][0] if countries else "Unknown",
            templates=templates,
            countries=countries,
        )
    h = hits[0]
    return build_alert_message(
        cli=h["cli"],
        panel=h["panel"],
        total=h["total"],
        main_country=h["main_country"],
        templates=h["templates"],
        countries=h["countries"],
    )
