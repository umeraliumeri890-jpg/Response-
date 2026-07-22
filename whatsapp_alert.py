```python
"""
SMART WHATSAPP OTP ALERT ENGINE
================================
Monitors the already-merged live dataframe (no extra API calls).

Trigger (per CLI):
  - rolling 5-minute window
  - >= threshold OTPs (default 50)
  - one alert, then cooldown (default 5 minutes)

Message templates:
  - strip OTP digits (4–8) → ******
  - unique templates only

Delivery is isolated in send_whatsapp_alert() so Meta / Twilio /
CallMeBot / webhook can be plugged later without touching the engine.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
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

from config import get_settings
from utils import log_event

# ---------------------------------------------------------------------------
# Persistent state file
# ---------------------------------------------------------------------------
ALERT_STATE_FILE = "alert_state.json"

def _load_alert_state() -> dict[str, Any]:
    """Load persistent alert state from JSON file."""
    default_state = {
        "last_hash": "",
        "last_sent": 0,
        "cooldowns": {}
    }
    if os.path.exists(ALERT_STATE_FILE):
        try:
            with open(ALERT_STATE_FILE, "r") as f:
                data = json.load(f)
                # Ensure all keys exist
                for key in default_state:
                    if key not in data:
                        data[key] = default_state[key]
                return data
        except Exception:
            return default_state
    return default_state

def _save_alert_state(state: dict[str, Any]) -> None:
    """Save persistent alert state to JSON file."""
    try:
        with open(ALERT_STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass

# Global alert state
_alert_state = _load_alert_state()

# ---------------------------------------------------------------------------
# Global lock for thread-safe alert processing
# ---------------------------------------------------------------------------
_ALERT_PROCESS_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Tunables (overridable via secrets / session)
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLD = 50
DEFAULT_WINDOW_MIN = 5
DEFAULT_COOLDOWN_MIN = 5
MAX_TEMPLATES = 8
MAX_COUNTRIES = 8
MAX_ALERTS_PER_TICK = 5  # safety: never spam more than N CLIs per refresh

# OTP digit runs 4–8 long (word-ish boundaries; keep Arabic/Unicode text intact)
_OTP_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")
# HTML entities sometimes appear in messages
_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|\w+);")
_WS_RE = re.compile(r"\s+")

# Country → flag (fallback 🌍)
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
    """Replace OTP digit groups with ****** and collapse whitespace."""
    if message is None:
        return ""
    text = str(message)
    # Decode common HTML entities so "<#>" becomes readable-ish
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
    # ①–⑳ then fallback
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
        "🚨 HIGH OTP TRAFFIC ALERT",
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

    lines.extend(
        [
            "━━━━━━━━━━━━━━━━━━",
            "",
            "🌍 Top Countries",
            "",
        ]
    )
    if countries:
        for name, cnt in countries:
            lines.append(f"{_flag(name)} {name} : {cnt}")
    else:
        lines.append("🌍 Unknown : 0")

    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━",
            "",
            "Status:",
            "LIVE",
        ]
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Delivery (isolated — swap provider without touching engine)
# ---------------------------------------------------------------------------
def send_whatsapp_alert(message: str, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Send (or stage) a WhatsApp alert.

    Providers (secret WHATSAPP_PROVIDER):
      - log        : only log + session history (default, always safe)
      - callmebot  : free personal WA via api.callmebot.com
      - webhook    : POST JSON to WHATSAPP_WEBHOOK_URL (Make/n8n/etc.)
      - meta       : Meta WhatsApp Cloud API (future-ready)
      - twilio     : Twilio WhatsApp (future-ready)

    Returns {ok, provider, detail}
    """
    settings = get_settings()
    provider = str(settings.get("whatsapp_provider") or "log").strip().lower()
    meta = meta or {}

    # Always keep a short in-session history for the Settings/debug panel
    hist = st.session_state.setdefault("wa_alert_history", [])
    hist.insert(
        0,
        {
            "ts": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
            "provider": provider,
            "cli": meta.get("cli"),
            "total": meta.get("total"),
            "preview": message[:180],
        },
    )
    st.session_state["wa_alert_history"] = hist[:30]

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
    """
    Free personal WhatsApp (not a group):
      https://www.callmebot.com/blog/free-api-whatsapp-messages/
    Secrets:
      CALLMEBOT_PHONE = 92300...
      CALLMEBOT_APIKEY = ...
    """
    phone = str(settings.get("callmebot_phone") or "").strip().lstrip("+")
    apikey = str(settings.get("callmebot_apikey") or "").strip()
    if not phone or not apikey:
        return {"ok": False, "provider": "callmebot", "detail": "CALLMEBOT_PHONE / CALLMEBOT_APIKEY missing"}
    url = (
        "https://api.callmebot.com/whatsapp.php"
        f"?phone={quote(phone)}&text={quote(message)}&apikey={quote(apikey)}"
    )
    r = requests.get(url, timeout=20)
    ok = r.status_code == 200
    return {"ok": ok, "provider": "callmebot", "detail": f"HTTP {r.status_code} {r.text[:200]}"}


def _send_greenapi(message: str, settings: dict[str, Any]) -> dict[str, Any]:
    """
    GREEN-API — send from YOUR personal WhatsApp into a GROUP.

    Console: https://console.green-api.com/
    Docs:    POST {apiUrl}/waInstance{idInstance}/sendMessage/{apiTokenInstance}

    Secrets:
      GREENAPI_ID_INSTANCE   = 1101xxxxxxxx
      GREENAPI_API_TOKEN     = xxxxxxxx...
      GREENAPI_API_URL       = https://api.green-api.com   (or your instance host)
      GREENAPI_GROUP_ID      = 1203630xxxxxxxxx@g.us

    How to get group id:
      1) Link phone via QR in Green-API console
      2) Send any message in the target group from that phone
      3) Console → journals / lastIncomingMessages OR getChats
      4) Copy chatId ending with @g.us
    """
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

    # Accept bare group ids and normalize
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
        # Green-API success usually returns idMessage
        if ok and not body.get("idMessage") and body.get("message"):
            ok = False
    except Exception:
        detail = f"{detail} {r.text[:240]}"
    return {"ok": ok, "provider": "greenapi", "detail": detail[:400]}


def _send_webhook(message: str, settings: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """
    Generic webhook — point to Make.com / n8n / Zapier free tier that posts into a WA group bot.
    Secret: WHATSAPP_WEBHOOK_URL
    """
    url = str(settings.get("whatsapp_webhook_url") or "").strip()
    if not url:
        return {"ok": False, "provider": "webhook", "detail": "WHATSAPP_WEBHOOK_URL missing"}
    payload = {"text": message, "message": message, **meta}
    r = requests.post(url, json=payload, timeout=20)
    ok = 200 <= r.status_code < 300
    return {"ok": ok, "provider": "webhook", "detail": f"HTTP {r.status_code}"}


def _send_meta(message: str, settings: dict[str, Any]) -> dict[str, Any]:
    """Meta WhatsApp Cloud API (user must have opted-in recipient)."""
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
    frm = str(settings.get("twilio_wa_from") or "").strip()  # whatsapp:+1415...
    to = str(settings.get("twilio_wa_to") or "").strip()
    if not sid or not token or not frm or not to:
        return {"ok": False, "provider": "twilio", "detail": "Twilio WA secrets missing"}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = {"From": frm, "To": to, "Body": message[:1600]}
    r = requests.post(url, data=data, auth=(sid, token), timeout=20)
    ok = 200 <= r.status_code < 300
    return {"ok": ok, "provider": "twilio", "detail": f"HTTP {r.status_code} {r.text[:200]}"}


def send_whatsapp_alert_async(message: str, meta: dict[str, Any] | None = None) -> None:
    """Fire-and-forget so UI never blocks on network."""
    def _run() -> None:
        try:
            send_whatsapp_alert(message, meta=meta)
        except Exception as exc:  # pragma: no cover
            log_event("wa_alert_async_error", str(exc))

    threading.Thread(target=_run, name="wa-alert", daemon=True).start()


# ---------------------------------------------------------------------------
# Cooldown state (persistent + session)
# ---------------------------------------------------------------------------
def _cooldown_map() -> dict[str, float]:
    # Merge persistent cooldowns with session cooldowns
    persistent = _alert_state.get("cooldowns", {})
    session_cooldowns = st.session_state.setdefault("wa_cli_cooldown_until", {})
    # Session overrides persistent (for current run)
    merged = {**persistent, **session_cooldowns}
    return merged


def _is_cooling(cli: str, now_ts: float) -> bool:
    cooldowns = _cooldown_map()
    until = float(cooldowns.get(cli, 0) or 0)
    return now_ts < until


def _arm_cooldown(cli: str, seconds: float, now_ts: float) -> None:
    expiry = now_ts + seconds
    # Update session
    st.session_state.setdefault("wa_cli_cooldown_until", {})[cli] = expiry
    # Update persistent
    _alert_state.setdefault("cooldowns", {})[cli] = expiry
    _save_alert_state(_alert_state)


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------
def _alert_config() -> dict[str, Any]:
    settings = get_settings()
    # session overrides (Settings page) win over secrets defaults
    return {
        "enabled": bool(st.session_state.get("wa_alerts_enabled", settings.get("whatsapp_alerts_enabled", True))),
        "threshold": int(st.session_state.get("wa_threshold", settings.get("whatsapp_threshold", DEFAULT_THRESHOLD))),
        "window_min": int(st.session_state.get("wa_window_min", settings.get("whatsapp_window_min", DEFAULT_WINDOW_MIN))),
        "cooldown_min": int(
            st.session_state.get("wa_cooldown_min", settings.get("whatsapp_cooldown_min", DEFAULT_COOLDOWN_MIN))
        ),
    }


def evaluate_cli_windows(df: pd.DataFrame, *, window_min: int, threshold: int) -> list[dict[str, Any]]:
    """
    Pure function: find CLIs over threshold in the last window_min minutes.
    Uses the existing merged dataframe only.
    """
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
    # Prefer wall clock if data is live; still clamp window to max(dt)
    wall = datetime.now()
    anchor = max(now.to_pydatetime() if hasattr(now, "to_pydatetime") else now, wall - timedelta(minutes=1))
    start = anchor - timedelta(minutes=int(window_min))
    recent = work[work["dt"] >= start]
    if recent.empty:
        return []

    hits: list[dict[str, Any]] = []
    for cli, grp in recent.groupby(recent["CLI"].astype(str), sort=False):
        total = int(len(grp))
        if total < int(threshold):
            continue
        # Dominant panel
        panel = "MIXED"
        if "Panel" in grp.columns:
            try:
                panel = str(grp["Panel"].astype(str).value_counts().idxmax())
            except Exception:
                panel = "MIXED"
        countries = top_countries(grp["Country"] if "Country" in grp.columns else pd.Series(dtype=str))
        main_country = countries[0][0] if countries else "Unknown"
        templates = unique_templates(grp["Message"] if "Message" in grp.columns else pd.Series(dtype=str))
        hits.append(
            {
                "cli": str(cli),
                "panel": panel,
                "total": total,
                "main_country": main_country,
                "templates": templates,
                "countries": countries,
                "window_start": start,
                "window_end": anchor,
            }
        )

    # Loudest first
    hits.sort(key=lambda h: h["total"], reverse=True)
    return hits


def process_otp_alerts(df: pd.DataFrame, *, force: bool = False) -> list[dict[str, Any]]:
    """
    Run one evaluation tick against the live merged frame.
    Safe to call every Streamlit rerun / autorefresh.
    Returns list of alerts fired this tick.
    """
    # Use global lock to prevent concurrent processing
    if not _ALERT_PROCESS_LOCK.acquire(blocking=False):
        # Another thread is already processing alerts
        return []

    try:
        cfg = _alert_config()
        if not cfg["enabled"] and not force:
            return []

        # Throttle full scans to ~ once per 10s even if UI reruns faster
        now_ts = time.time()
        last = float(st.session_state.get("wa_last_scan_ts", 0) or 0)
        if not force and (now_ts - last) < 10:
            return []
        st.session_state["wa_last_scan_ts"] = now_ts

        try:
            hits = evaluate_cli_windows(df, window_min=cfg["window_min"], threshold=cfg["threshold"])
        except Exception as exc:
            log_event("wa_eval_error", str(exc))
            return []

        fired: list[dict[str, Any]] = []

        for hit in hits[:MAX_ALERTS_PER_TICK]:
            cli = hit["cli"]
            total = hit["total"]

            # Determine cooldown based on OTP count
            if total >= 50:
                cooldown_sec = 300  # 5 minutes
            else:
                cooldown_sec = 600  # 10 minutes

            if _is_cooling(cli, now_ts):
                continue

            msg = build_alert_message(
                cli=cli,
                panel=hit["panel"],
                total=hit["total"],
                main_country=hit["main_country"],
                templates=hit["templates"],
                countries=hit["countries"],
            )

            # Compute message hash for duplicate detection
            msg_hash = hashlib.sha256(msg.encode("utf-8")).hexdigest()

            # Check for duplicate message (same hash within 30 seconds)
            last_hash = _alert_state.get("last_hash", "")
            last_sent = _alert_state.get("last_sent", 0)

            if msg_hash == last_hash and (now_ts - last_sent) < 30:
                # Skip duplicate
                log_event("wa_alert_skipped", "duplicate message", cli=cli, hash=msg_hash[:8])
                continue

            meta = {"cli": cli, "panel": hit["panel"], "total": hit["total"], "country": hit["main_country"]}

            # Arm cooldown BEFORE send to avoid double-fire on overlapping threads
            _arm_cooldown(cli, cooldown_sec, now_ts)

            # Update persistent state for duplicate detection
            _alert_state["last_hash"] = msg_hash
            _alert_state["last_sent"] = now_ts
            _save_alert_state(_alert_state)

            # Send alert
            send_whatsapp_alert_async(msg, meta=meta)

            fired.append({**meta, "message": msg})
            log_event("wa_alert_triggered", "high traffic", **meta)

            # Toast for operator (non-blocking UX)
            try:
                st.toast(f"🚨 WA alert armed · {cli} · {hit['total']} OTPs / {cfg['window_min']}m", icon="📱")
            except Exception:
                pass

        if fired:
            st.session_state["wa_last_fired"] = fired
        return fired

    finally:
        _ALERT_PROCESS_LOCK.release()


def _greenapi_base(settings: dict[str, Any] | None = None) -> tuple[str, str, str] | dict[str, Any]:
    """Return (api_url, instance, token) or error dict."""
    settings = settings or get_settings()
    instance = str(settings.get("greenapi_id_instance") or "").strip()
    token = str(settings.get("greenapi_api_token") or "").strip()
    api_url = str(settings.get("greenapi_api_url") or "https://api.green-api.com").strip().rstrip("/")
    if not instance or not token:
        return {
            "ok": False,
            "detail": "GREENAPI_ID_INSTANCE / GREENAPI_API_TOKEN missing in secrets",
            "groups": [],
        }
    return api_url, instance, token


def list_greenapi_groups(count: int = 200) -> dict[str, Any]:
    """
    Discover WhatsApp GROUP chat IDs from the linked Green-API instance.

    Tries:
      1) getChats  → type == group / id endswith @g.us
      2) lastOutgoingMessages + lastIncomingMessages → chatId @g.us

    IMPORTANT: Green-API only sees chats that had activity AFTER the phone was linked.
    If empty: open WhatsApp on the linked phone → open target group → send any message
    (e.g. "test") → wait 10–20s → run this again.
    """
    base = _greenapi_base()
    if isinstance(base, dict):
        return base
    api_url, instance, token = base
    found: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    # 1) getChats
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

    # 2) journals (often fill faster right after you send a group msg)
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
                # some payloads nest group info
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
        "Green-API purane silent groups nahi dikhata jab tak unme linked number se activity na ho."
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
    """Quick health: instance authorized?"""
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
    """Build a dry-run message for Settings UI."""
    if df is None or df.empty or not cli:
        return None
    cfg = _alert_config()
    sub = df[df["CLI"].astype(str).str.contains(str(cli), case=False, na=False)] if "CLI" in df.columns else df
    hits = evaluate_cli_windows(sub, window_min=cfg["window_min"], threshold=1)
    if not hits:
        # still show template sample from whatever rows exist
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
```
