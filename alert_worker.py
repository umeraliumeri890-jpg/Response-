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
import re
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
    "WHATSAPP_WINDOW_MIN": "3",
    "WHATSAPP_COOLDOWN_MIN": "1",
    "WHATSAPP_MAX_ALERTS_PER_RUN": "1",
    "WHATSAPP_TOP_N": "3",
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
        "whatsapp_window_min": env_int("WHATSAPP_WINDOW_MIN", 3),
        "whatsapp_cooldown_min": env_int("WHATSAPP_COOLDOWN_MIN", 1),
        "whatsapp_max_alerts_per_run": env_int("WHATSAPP_MAX_ALERTS_PER_RUN", 1),
        "whatsapp_top_n": env_int("WHATSAPP_TOP_N", 3),
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



# ---------------------------------------------------------------------------
# App / site intelligence (CLI + SMS body → brand + Google/Play links)
# ---------------------------------------------------------------------------
_APP_CATALOG: list[dict[str, str]] = [
    # key words matched against CLI + message (case-insensitive)
    {"name": "Bumble", "keys": "bumble", "web": "https://bumble.com", "play": "https://play.google.com/store/apps/details?id=com.bumble.app", "ios": "https://apps.apple.com/app/bumble-dating-friends-bizz/id930441707", "google": "https://www.google.com/search?q=Bumble+app"},
    {"name": "Cobee by Pluxee", "keys": "cobee,pluxee", "web": "https://www.pluxee.com", "play": "https://play.google.com/store/search?q=Cobee%20Pluxee&c=apps", "ios": "https://www.google.com/search?q=Cobee+by+Pluxee+app", "google": "https://www.google.com/search?q=Cobee+by+Pluxee"},
    {"name": "Talabat", "keys": "talabat", "web": "https://www.talabat.com", "play": "https://play.google.com/store/search?q=talabat&c=apps", "ios": "https://www.google.com/search?q=Talabat+app", "google": "https://www.google.com/search?q=Talabat+app"},
    {"name": "Rakuten", "keys": "rakuten", "web": "https://www.rakuten.com", "play": "https://play.google.com/store/search?q=rakuten&c=apps", "ios": "https://www.google.com/search?q=Rakuten+app", "google": "https://www.google.com/search?q=Rakuten+app"},
    {"name": "Tinder", "keys": "tinder", "web": "https://tinder.com", "play": "https://play.google.com/store/apps/details?id=com.tinder", "ios": "https://apps.apple.com/app/tinder-dating-app-meet-people/id547702041", "google": "https://www.google.com/search?q=Tinder+app"},
    {"name": "Hinge", "keys": "hinge", "web": "https://hinge.co", "play": "https://play.google.com/store/apps/details?id=co.hinge.app", "ios": "https://apps.apple.com/app/hinge-dating-app-matches/id595287172", "google": "https://www.google.com/search?q=Hinge+app"},
    {"name": "WhatsApp", "keys": "whatsapp,wa code,whats app", "web": "https://www.whatsapp.com", "play": "https://play.google.com/store/apps/details?id=com.whatsapp", "ios": "https://apps.apple.com/app/whatsapp-messenger/id310633997", "google": "https://www.google.com/search?q=WhatsApp"},
    {"name": "Telegram", "keys": "telegram", "web": "https://telegram.org", "play": "https://play.google.com/store/apps/details?id=org.telegram.messenger", "ios": "https://apps.apple.com/app/telegram-messenger/id686449807", "google": "https://www.google.com/search?q=Telegram+app"},
    {"name": "Facebook", "keys": "facebook,fb-," , "web": "https://www.facebook.com", "play": "https://play.google.com/store/apps/details?id=com.facebook.katana", "ios": "https://apps.apple.com/app/facebook/id284882215", "google": "https://www.google.com/search?q=Facebook+app"},
    {"name": "Instagram", "keys": "instagram,ig ", "web": "https://www.instagram.com", "play": "https://play.google.com/store/apps/details?id=com.instagram.android", "ios": "https://apps.apple.com/app/instagram/id389801252", "google": "https://www.google.com/search?q=Instagram+app"},
    {"name": "TikTok", "keys": "tiktok,tik tok,musically", "web": "https://www.tiktok.com", "play": "https://play.google.com/store/apps/details?id=com.zhiliaoapp.musically", "ios": "https://apps.apple.com/app/tiktok/id835599320", "google": "https://www.google.com/search?q=TikTok+app"},
    {"name": "Snapchat", "keys": "snapchat,snap ", "web": "https://www.snapchat.com", "play": "https://play.google.com/store/apps/details?id=com.snapchat.android", "ios": "https://apps.apple.com/app/snapchat/id447188370", "google": "https://www.google.com/search?q=Snapchat+app"},
    {"name": "Google", "keys": "google,g- ,g-id,g id", "web": "https://accounts.google.com", "play": "https://play.google.com/store/apps/details?id=com.google.android.gms", "ios": "https://apps.apple.com/app/google/id284815942", "google": "https://www.google.com/search?q=Google+account"},
    {"name": "Microsoft", "keys": "microsoft,msft,outlook", "web": "https://www.microsoft.com", "play": "https://play.google.com/store/apps/details?id=com.microsoft.office.outlook", "ios": "https://apps.apple.com/app/microsoft-outlook/id951937596", "google": "https://www.google.com/search?q=Microsoft+account"},
    {"name": "Apple", "keys": "apple,icloud,apple id", "web": "https://appleid.apple.com", "play": "https://www.apple.com/app-store/", "ios": "https://apps.apple.com", "google": "https://www.google.com/search?q=Apple+ID"},
    {"name": "Amazon", "keys": "amazon,aws ", "web": "https://www.amazon.com", "play": "https://play.google.com/store/apps/details?id=com.amazon.mShop.android.shopping", "ios": "https://apps.apple.com/app/amazon-shopping/id297606951", "google": "https://www.google.com/search?q=Amazon+app"},
    {"name": "PayPal", "keys": "paypal", "web": "https://www.paypal.com", "play": "https://play.google.com/store/apps/details?id=com.paypal.android.p2pmobile", "ios": "https://apps.apple.com/app/paypal-mobile-cash/id283646709", "google": "https://www.google.com/search?q=PayPal+app"},
    {"name": "Uber", "keys": "uber", "web": "https://www.uber.com", "play": "https://play.google.com/store/apps/details?id=com.ubercab", "ios": "https://apps.apple.com/app/uber-request-a-ride/id368677368", "google": "https://www.google.com/search?q=Uber+app"},
    {"name": "Grab", "keys": "grab", "web": "https://www.grab.com", "play": "https://play.google.com/store/apps/details?id=com.grabtaxi.passenger", "ios": "https://apps.apple.com/app/grab-taxi-food-delivery/id647268330", "google": "https://www.google.com/search?q=Grab+app"},
    {"name": "Foodpanda", "keys": "foodpanda,panda", "web": "https://www.foodpanda.com", "play": "https://play.google.com/store/apps/details?id=com.global.foodpanda.android", "ios": "https://apps.apple.com/app/foodpanda-food-delivery/id758103884", "google": "https://www.google.com/search?q=Foodpanda+app"},
    {"name": "Shopee", "keys": "shopee", "web": "https://shopee.com", "play": "https://play.google.com/store/apps/details?id=com.shopee.my", "ios": "https://apps.apple.com/app/shopee/id959841443", "google": "https://www.google.com/search?q=Shopee+app"},
    {"name": "Lazada", "keys": "lazada", "web": "https://www.lazada.com", "play": "https://play.google.com/store/apps/details?id=com.lazada.android", "ios": "https://apps.apple.com/app/lazada-online-shopping-app/id785385147", "google": "https://www.google.com/search?q=Lazada+app"},
    {"name": "Tokopedia", "keys": "tokopedia,tokped", "web": "https://www.tokopedia.com", "play": "https://play.google.com/store/apps/details?id=com.tokopedia.tkpd", "ios": "https://apps.apple.com/app/tokopedia/id1001394201", "google": "https://www.google.com/search?q=Tokopedia+app"},
    {"name": "Daraz", "keys": "daraz", "web": "https://www.daraz.pk", "play": "https://play.google.com/store/apps/details?id=com.daraz.android", "ios": "https://apps.apple.com/app/daraz-online-shopping-app/id980023904", "google": "https://www.google.com/search?q=Daraz+app"},
    {"name": "Careem", "keys": "careem", "web": "https://www.careem.com", "play": "https://play.google.com/store/apps/details?id=com.careem.acma", "ios": "https://apps.apple.com/app/careem/id592978487", "google": "https://www.google.com/search?q=Careem+app"},
    {"name": "BYJU'S", "keys": "byju,byjus", "web": "https://byjus.com", "play": "https://play.google.com/store/apps/details?id=com.byjus.thelearningapp", "ios": "https://apps.apple.com/app/byjus-the-learning-app/id1136776297", "google": "https://www.google.com/search?q=BYJU%27S+app"},
    {"name": "Netflix", "keys": "netflix", "web": "https://www.netflix.com", "play": "https://play.google.com/store/apps/details?id=com.netflix.mediaclient", "ios": "https://apps.apple.com/app/netflix/id363590051", "google": "https://www.google.com/search?q=Netflix+app"},
    {"name": "Discord", "keys": "discord", "web": "https://discord.com", "play": "https://play.google.com/store/apps/details?id=com.discord", "ios": "https://apps.apple.com/app/discord-talk-chat-hang-out/id985746746", "google": "https://www.google.com/search?q=Discord+app"},
    {"name": "Twitter / X", "keys": "twitter, x.com,twtr", "web": "https://x.com", "play": "https://play.google.com/store/apps/details?id=com.twitter.android", "ios": "https://apps.apple.com/app/x/id333903271", "google": "https://www.google.com/search?q=X+Twitter+app"},
    {"name": "LinkedIn", "keys": "linkedin", "web": "https://www.linkedin.com", "play": "https://play.google.com/store/apps/details?id=com.linkedin.android", "ios": "https://apps.apple.com/app/linkedin/id288429040", "google": "https://www.google.com/search?q=LinkedIn+app"},
    {"name": "Coinbase", "keys": "coinbase", "web": "https://www.coinbase.com", "play": "https://play.google.com/store/apps/details?id=com.coinbase.android", "ios": "https://apps.apple.com/app/coinbase-buy-bitcoin-ether/id886427730", "google": "https://www.google.com/search?q=Coinbase+app"},
    {"name": "Binance", "keys": "binance", "web": "https://www.binance.com", "play": "https://play.google.com/store/apps/details?id=com.binance.dev", "ios": "https://apps.apple.com/app/binance-buy-bitcoin-crypto/id1436799971", "google": "https://www.google.com/search?q=Binance+app"},
    {"name": "Cash App", "keys": "cash app,cashapp,square cash", "web": "https://cash.app", "play": "https://play.google.com/store/apps/details?id=com.squareup.cash", "ios": "https://apps.apple.com/app/cash-app/id711923939", "google": "https://www.google.com/search?q=Cash+App"},
    {"name": "Venmo", "keys": "venmo", "web": "https://venmo.com", "play": "https://play.google.com/store/apps/details?id=com.venmo", "ios": "https://apps.apple.com/app/venmo/id351727428", "google": "https://www.google.com/search?q=Venmo+app"},
    {"name": "Stripe", "keys": "stripe", "web": "https://stripe.com", "play": "https://play.google.com/store/search?q=stripe&c=apps", "ios": "https://www.google.com/search?q=Stripe", "google": "https://www.google.com/search?q=Stripe"},
    {"name": "Shopify", "keys": "shopify", "web": "https://www.shopify.com", "play": "https://play.google.com/store/apps/details?id=com.shopify.mobile", "ios": "https://apps.apple.com/app/shopify-ecommerce-business/id371294472", "google": "https://www.google.com/search?q=Shopify+app"},
    {"name": "MYOB", "keys": "myob", "web": "https://www.myob.com", "play": "https://play.google.com/store/search?q=MYOB&c=apps", "ios": "https://www.google.com/search?q=MYOB+app", "google": "https://www.google.com/search?q=MYOB+app"},
    {"name": "Xero", "keys": "xero", "web": "https://www.xero.com", "play": "https://play.google.com/store/apps/details?id=com.xero.touch", "ios": "https://apps.apple.com/app/xero-accounting/id468420032", "google": "https://www.google.com/search?q=Xero+app"},
    {"name": "Wise", "keys": "wise.com,transferwise, wise ", "web": "https://wise.com", "play": "https://play.google.com/store/apps/details?id=com.transferwise.android", "ios": "https://apps.apple.com/app/wise/id612261027", "google": "https://www.google.com/search?q=Wise+app"},
    {"name": "Revolut", "keys": "revolut", "web": "https://www.revolut.com", "play": "https://play.google.com/store/apps/details?id=com.revolut.revolut", "ios": "https://apps.apple.com/app/revolut/id932493382", "google": "https://www.google.com/search?q=Revolut+app"},
    {"name": "N26", "keys": "n26", "web": "https://n26.com", "play": "https://play.google.com/store/apps/details?id=de.number26.android", "ios": "https://apps.apple.com/app/n26-mobile-banking/id956347094", "google": "https://www.google.com/search?q=N26+app"},
    {"name": "OkCupid", "keys": "okcupid,ok cupid", "web": "https://www.okcupid.com", "play": "https://play.google.com/store/apps/details?id=com.okcupid.okcupid", "ios": "https://apps.apple.com/app/okcupid-online-dating-app/id338701294", "google": "https://www.google.com/search?q=OkCupid+app"},
    {"name": "Plenty of Fish", "keys": "pof,plenty of fish", "web": "https://www.pof.com", "play": "https://play.google.com/store/apps/details?id=com.pof.android", "ios": "https://apps.apple.com/app/plenty-of-fish-dating-app/id312860541", "google": "https://www.google.com/search?q=Plenty+of+Fish+app"},
    {"name": "Viber", "keys": "viber", "web": "https://www.viber.com", "play": "https://play.google.com/store/apps/details?id=com.viber.voip", "ios": "https://apps.apple.com/app/viber-messenger/id382617920", "google": "https://www.google.com/search?q=Viber+app"},
    {"name": "Signal", "keys": "signal", "web": "https://signal.org", "play": "https://play.google.com/store/apps/details?id=org.thoughtcrime.securesms", "ios": "https://apps.apple.com/app/signal-private-messenger/id874139669", "google": "https://www.google.com/search?q=Signal+app"},
    {"name": "Twilio", "keys": "twilio", "web": "https://www.twilio.com", "play": "https://www.google.com/search?q=Twilio", "ios": "https://www.google.com/search?q=Twilio", "google": "https://www.google.com/search?q=Twilio"},
    {"name": "Authy", "keys": "authy", "web": "https://authy.com", "play": "https://play.google.com/store/apps/details?id=com.authy.authy", "ios": "https://apps.apple.com/app/twilio-authy/id494168017", "google": "https://www.google.com/search?q=Authy+app"},
]


def _clean_brand_token(raw: str) -> str:
    s = re.sub(r"[^A-Za-z0-9+.\- ]+", " ", str(raw or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def detect_app_brand(*, cli: str, templates: list[str] | None = None, messages: list[str] | None = None) -> dict[str, str]:
    """Detect app/site from CLI name first, then SMS body/templates."""
    import re as _re

    blob_parts = [str(cli or "")]
    for t in templates or []:
        blob_parts.append(str(t))
    for m in messages or []:
        blob_parts.append(str(m))
    blob = " ".join(blob_parts).lower()
    cli_l = str(cli or "").lower()

    # 1) Catalog exact/keyword hits (prefer CLI match)
    best = None
    best_score = 0
    for item in _APP_CATALOG:
        keys = [k.strip().lower() for k in item["keys"].split(",") if k.strip()]
        score = 0
        for k in keys:
            if k and k in cli_l:
                score = max(score, 100 + len(k))
            elif k and k in blob:
                score = max(score, 40 + len(k))
        if score > best_score:
            best_score = score
            best = item
    if best and best_score >= 40:
        return {
            "name": best["name"],
            "source": "catalog",
            "web": best.get("web", ""),
            "play": best.get("play", ""),
            "ios": best.get("ios", ""),
            "google": best.get("google", ""),
        }

    # 2) Domain in message body
    domain_re = _re.compile(r"\b([a-z0-9][a-z0-9\-]{1,30}\.(?:com|net|org|io|co|app|me|my|pk|sg|id|in|ae))\b", _re.I)
    for part in blob_parts:
        m = domain_re.search(str(part))
        if m:
            dom = m.group(1).lower()
            root = dom.split(".")[0]
            if root not in {"www", "http", "https", "bit", "tinyurl", "t"}:
                q = quote(root)
                return {
                    "name": root.upper() if len(root) <= 4 else root.title(),
                    "source": "domain",
                    "web": f"https://{dom}",
                    "play": f"https://play.google.com/store/search?q={q}&c=apps",
                    "ios": f"https://www.google.com/search?q={q}+ios+app",
                    "google": f"https://www.google.com/search?q={q}+app",
                }

    # 3) Fallback: use cleaned CLI as brand query
    token = _clean_brand_token(cli)
    # strip common OTP noise words from CLI
    noise = {"sms", "otp", "code", "verify", "verification", "auth", "alert", "msg", "info", "service"}
    parts = [p for p in token.split() if p.lower() not in noise]
    token = " ".join(parts) if parts else token
    if not token or token.lower() in {"unknown", "n/a", "none", "null"}:
        return {
            "name": "Unknown",
            "source": "none",
            "web": "",
            "play": "https://play.google.com/store/apps",
            "ios": "",
            "google": "https://www.google.com/search?q=OTP+app",
        }
    q = quote(token)
    return {
        "name": token.upper() if len(token) <= 5 else token.title(),
        "source": "cli",
        "web": f"https://www.google.com/search?q={q}+official+site",
        "play": f"https://play.google.com/store/search?q={q}&c=apps",
        "ios": f"https://www.google.com/search?q={q}+app+store",
        "google": f"https://www.google.com/search?q={q}+app",
    }


def format_app_links_block(app: dict[str, str]) -> list[str]:
    name = app.get("name") or "Unknown"
    lines = [
        "━━━━━━━━━━━━━━━━━━",
        "",
        "🔎 App / Site Intel",
        "",
        f"🏷 Name  : {name}",
    ]
    if app.get("google"):
        lines.append(f"🔍 Google: {app['google']}")
    if app.get("play"):
        lines.append(f"▶ Play  : {app['play']}")
    if app.get("ios"):
        lines.append(f" iOS   : {app['ios']}")
    if app.get("web"):
        lines.append(f"🌐 Web   : {app['web']}")
    lines.append("")
    return lines



def build_alert_message(
    *,
    cli: str,
    panel: str,
    total: int,
    main_country: str,
    templates: list[str],
    countries: list[tuple[str, int]],
    app: dict[str, str] | None = None,
) -> str:
    time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    app = app or detect_app_brand(cli=cli, templates=templates)
    lines = [
        "🚨 UTS HUNTERS · OTP ALERT",
        "",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"📱 CLI   : {cli}",
        f"🏷 App   : {app.get('name') or 'Unknown'}",
        f"🔌 Panel : {panel}",
        f"📊 Count : {total} OTP(s) (recent window)",
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


def _bar(count: int, total: int, width: int = 16) -> str:
    total = max(1, int(total or 1))
    count = max(0, int(count or 0))
    filled = int(round((count / total) * width))
    filled = max(0, min(width, filled))
    return ("█" * filled) + ("░" * (width - filled))


def _rank_badge(idx: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(int(idx), "🔹")


def _rank_label(idx: int) -> str:
    return {1: "DOMINANT", 2: "ACTIVE", 3: "STABLE"}.get(int(idx), "LIVE")


def _wrap_quote(text: str, width: int = 42) -> list[str]:
    raw = " ".join(str(text or "").split())
    if not raw:
        return ['  "(no message body)"']
    words = raw.split(" ")
    rows: list[str] = []
    cur = ""
    for w in words:
        trial = w if not cur else f"{cur} {w}"
        if len(trial) <= width:
            cur = trial
        else:
            if cur:
                rows.append(cur)
            cur = w
    if cur:
        rows.append(cur)
    out: list[str] = []
    for i, row in enumerate(rows):
        if i == 0 and len(rows) == 1:
            out.append(f'  "{row}"')
        elif i == 0:
            out.append(f'  "{row}')
        elif i == len(rows) - 1:
            out.append(f"  {row}\"")
        else:
            out.append(f"  {row}")
    return out


def build_top_n_alert_message(hits: list[dict[str, Any]], *, top_n: int = 3) -> str:
    """Premium UTS Hunters WhatsApp layout — TOP N, no links."""
    top_n = max(1, min(10, int(top_n or 3)))
    selected = list(hits[:top_n])
    grand_total = sum(int(h.get("total") or 0) for h in selected)

    lines: list[str] = [
        "◤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◥",
        "                 UTS HUNTERS",
        "                  OTP ALERT",
        "            LIVE INTELLIGENCE FEED",
        "◣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◢",
        "",
        "                  ⚡ STATUS: ACTIVE",
        "              ⏱ WINDOW: 1-MIN REFRESH",
        f"          📊 TOTAL OTPs HARVESTED: {grand_total}",
        "",
        "┌───────────────────────────────────────────┐",
        f"│          🏆 TOP {len(selected)} GLOBAL RANKINGS         │",
        "└───────────────────────────────────────────┘",
        "",
    ]

    for idx, hit in enumerate(selected, 1):
        cli = str(hit.get("cli") or "UNKNOWN")
        templates = [str(t) for t in (hit.get("templates") or []) if str(t).strip()]
        app = detect_app_brand(cli=cli, templates=templates)
        app_name = str(app.get("name") or cli)
        countries = hit.get("countries") or []
        total = int(hit.get("total") or 0)
        panel = str(hit.get("panel") or "MIXED").upper()
        if idx == 1 and panel not in {"", "MIXED"}:
            panel_txt = f"{panel} (HIGH-PRIORITY)"
        else:
            panel_txt = panel
        main_country = str(hit.get("main_country") or (countries[0][0] if countries else "Unknown"))
        main_flag = flag(main_country)
        main_share = 0
        if countries and total > 0:
            try:
                main_share = int(round((int(countries[0][1]) / total) * 100))
            except Exception:
                main_share = 0

        if idx == 1:
            lines.extend(
                [
                    f"  {_rank_badge(idx)} RANK #{idx} · {_rank_label(idx)}",
                    "  ──────────────────────────────────────────",
                    f"  📱  CLIENT     : {cli}",
                    f"  🏷  APP        : {app_name}",
                    f"  🔌  PANEL      : {panel_txt}",
                    f"  📈  VOLUME     : {total} OTPs",
                    f"  🌍  PRIMARY    : {main_flag} {main_country.upper()}"
                    + (f" ({main_share}%)" if main_share else ""),
                    "",
                    "  📝  MESSAGE TEMPLATE",
                    "  ──────────────────────────────────────────",
                ]
            )
            if templates:
                lines.extend(_wrap_quote(templates[0]))
            else:
                lines.append('  "(no message body)"')
            lines.append("")
            if countries:
                lines.extend(
                    [
                        "  ──────────────────────────────────────────",
                        "  ⚠️  REGIONAL TRAFFIC",
                        "  ──────────────────────────────────────────",
                    ]
                )
                for name, cnt in countries[:5]:
                    nm = str(name)
                    c = int(cnt)
                    lines.append(f"  {flag(nm)} {nm:<14} {_bar(c, total)}  {c}")
            lines.append("")
        else:
            lines.extend(
                [
                    "┌───────────────────────────────────────────┐",
                    f"│              RANK #{idx} · {_rank_label(idx):<7}             │",
                    "├───────────────────────────────────────────┤",
                    f"│  📱  CLIENT     : {cli:<22}│",
                    f"│  🏷  APP        : {app_name[:22]:<22}│",
                    f"│  🔌  PANEL      : {panel_txt[:22]:<22}│",
                    f"│  📈  VOLUME     : {str(total) + ' OTPs':<22}│",
                    f"│  🌍  PRIMARY    : {(main_flag + ' ' + main_country.upper())[:22]:<22}│",
                    "│                                           │",
                    f"│  📝  TEMPLATES ({len(templates)} DETECTED)              │",
                    "│  ──────────────────────────────────────── │",
                ]
            )
            if templates:
                for t_i, tmpl in enumerate(templates[:4], 1):
                    t = str(tmpl).replace("\n", " ")
                    if len(t) > 36:
                        t = t[:33] + "..."
                    lines.append(f"│  {t_i}. {t:<37}│")
            else:
                lines.append("│  1. (no message body)                     │")
            lines.append("│                                           │")
            if countries:
                lines.extend(
                    [
                        "│  🌍  GEO-SPLIT                           │",
                        "│  ──────────────────────────────────────── │",
                    ]
                )
                for name, cnt in countries[:4]:
                    nm = str(name)
                    c = int(cnt)
                    row = f"{flag(nm)} {nm:<12} {_bar(c, total, 14)}  {c}"
                    if len(row) > 41:
                        row = row[:41]
                    lines.append(f"│  {row:<41}│")
            lines.append("└───────────────────────────────────────────┘")
            lines.append("")

    lines.extend(
        [
            "◤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◥",
            "            UTS-HQ · LIVE MONITOR",
            "       © 2026 UTS HUNTERS · ALL RIGHTS",
            "◣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◢",
            "",
            "              ═══════════════════",
            "              POWERED BY UMER ALI",
            "              ═══════════════════",
        ]
    )
    return "\n".join(lines)


def evaluate_cli_windows(df: pd.DataFrame, *, window_min: int, threshold: int) -> list[dict[str, Any]]:
    if df is None or df.empty or "CLI" not in df.columns or "dt" not in df.columns:
        return []
    work = df.copy()
    work["dt"] = pd.to_datetime(work["dt"], errors="coerce")
    work = work.dropna(subset=["dt"])
    if work.empty:
        return []
    # Anchor to wall clock so late/skewed API timestamps still fall in lookback
    wall = datetime.now()
    data_max = work["dt"].max()
    data_max_py = data_max.to_pydatetime() if hasattr(data_max, "to_pydatetime") else data_max
    # Prefer wall clock; if API clocks are ahead, still include them via max()
    anchor = max(wall, data_max_py)
    start = anchor - timedelta(minutes=int(window_min))
    recent = work[work["dt"] >= start]
    if recent.empty:
        # Fallback: last N minutes relative to newest API row (handles bad wall/API skew)
        start2 = data_max_py - timedelta(minutes=int(window_min))
        recent = work[work["dt"] >= start2]
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
        newest = grp["dt"].max()
        newest_s = newest.isoformat() if hasattr(newest, "isoformat") else str(newest)
        hits.append(
            {
                "cli": str(cli),
                "panel": panel,
                "total": total,
                "main_country": countries[0][0] if countries else "Unknown",
                "templates": templates,
                "countries": countries,
                "newest_dt": newest_s,
                "window_end": anchor.isoformat() if hasattr(anchor, "isoformat") else str(anchor),
            }
        )
    hits.sort(key=lambda h: (h["total"], h.get("newest_dt", "")), reverse=True)
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
    """Fetch OTPs and alert on NEW activity.

    Upgrades:
    - Sending cadence default 1 minute (global gate)
    - One WhatsApp message with TOP 3 apps/CLIs
    - Window default 3 min (fits 1-min cron ticks)
    - Fingerprint skip if same window already alerted
    """
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
    # Per-CLI cooldown map: {cli: cooldown_until_ts}
    cli_cd: dict[str, float] = {}
    raw_cd = state.get("cli_cooldowns") or state.get("cooldowns") or {}
    if isinstance(raw_cd, dict):
        for k, v in raw_cd.items():
            try:
                cli_cd[str(k)] = float(v)
            except Exception:
                continue
    # Seen fingerprint per CLI: last newest dt iso we already alerted
    seen: dict[str, str] = {}
    raw_seen = state.get("cli_seen") or {}
    if isinstance(raw_seen, dict):
        for k, v in raw_seen.items():
            seen[str(k)] = str(v)

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

    # Use wall-clock anchored window (not only max-dt) so late API lag still catches OTPs
    hits = evaluate_cli_windows(
        df,
        window_min=cfg["whatsapp_window_min"],
        threshold=cfg["whatsapp_threshold"],
    )
    if not hits:
        log("no_hits", window_min=cfg["whatsapp_window_min"], threshold=cfg["whatsapp_threshold"])
        return 0

    top_n = max(1, min(10, int(cfg.get("whatsapp_top_n") or 3)))
    # Sending cadence: default 1 minute between WhatsApp messages
    cd_sec = max(45, int(float(cfg["whatsapp_cooldown_min"]) * 60))

    # Global send gate (1 message / cooldown), independent of per-CLI details
    global_until = float(state.get("global_cooldown_until") or state.get("cooldown_until") or 0)
    if not force and now_ts < global_until:
        left = int(global_until - now_ts)
        log(
            "global_cooldown",
            seconds_left=left,
            hint="Sending time gate — next WhatsApp after cooldown",
        )
        return 0

    # Enrich hits with app names + filter unchanged fingerprints
    ready: list[dict[str, Any]] = []
    skipped_cd = 0
    skipped_seen = 0
    for hit in hits:
        cli = str(hit["cli"])
        until = float(cli_cd.get(cli, 0) or 0)
        if not force and now_ts < until:
            skipped_cd += 1
            continue
        newest = hit.get("newest_dt") or hit.get("window_end") or ""
        newest_s = newest.isoformat() if hasattr(newest, "isoformat") else str(newest)
        fp = f"{newest_s}|{hit['total']}|{hit.get('panel','')}"
        if not force and seen.get(cli) == fp:
            skipped_seen += 1
            continue
        app = detect_app_brand(cli=cli, templates=hit.get("templates") or [])
        hit = {**hit, "app": app, "fp": fp}
        ready.append(hit)

    if not ready:
        log(
            "no_new_hits",
            skipped_cooldown=skipped_cd,
            skipped_same_window=skipped_seen,
            raw_hits=len(hits),
        )
        return 0

    selected = ready[:top_n]
    msg = build_top_n_alert_message(selected, top_n=top_n)
    meta = {
        "cli": ",".join(str(h["cli"]) for h in selected),
        "apps": ",".join(str((h.get("app") or {}).get("name") or h["cli"]) for h in selected),
        "total": sum(int(h.get("total") or 0) for h in selected),
        "top_n": len(selected),
    }
    result = send_alert(msg, cfg, meta)
    log("send_result", **{k: result.get(k) for k in ("ok", "provider", "detail")}, **meta)

    if result.get("ok"):
        # Arm global 1-min sending gate
        state["global_cooldown_until"] = now_ts + cd_sec
        state["cooldown_until"] = now_ts + cd_sec
        state["last_sent"] = now_ts
        state["last_cli"] = meta["cli"]
        for h in selected:
            cli = str(h["cli"])
            cli_cd[cli] = now_ts + cd_sec
            seen[cli] = str(h.get("fp") or "")
        hist = list(state.get("history") or [])
        hist.insert(
            0,
            {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "cli": meta["cli"],
                "apps": meta["apps"],
                "total": meta["total"],
                "top_n": len(selected),
                "provider": result.get("provider"),
                "ok": True,
            },
        )
        state["history"] = hist[:50]
        state["cli_cooldowns"] = {k: v for k, v in cli_cd.items() if float(v) > now_ts - 3600}
        state["cli_seen"] = dict(list(seen.items())[-200:])
        save_state(state)
        log(
            "alert_sent",
            apps=meta["apps"],
            total=meta["total"],
            top_n=len(selected),
            cooldown_min=cfg["whatsapp_cooldown_min"],
        )
        log(
            "run_summary",
            sent=1,
            top_n=len(selected),
            skipped_cooldown=skipped_cd,
            skipped_same_window=skipped_seen,
            hits=len(hits),
            window_min=cfg["whatsapp_window_min"],
            cooldown_min=cfg["whatsapp_cooldown_min"],
        )
        return 0

    log("alert_failed", detail=result.get("detail"))
    log(
        "run_summary",
        sent=0,
        failed=1,
        skipped_cooldown=skipped_cd,
        skipped_same_window=skipped_seen,
        hits=len(hits),
    )
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
