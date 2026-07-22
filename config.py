"""UTS Hunters Enterprise — central configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent
TEAM_FILE = ROOT / "Numbers_Export.csv"
LOG_DIR = ROOT / "logs"
ASSETS_DIR = ROOT / "assets"
DATA_DIR = ROOT / "data"

APP_NAME = "UTS HUNTERS ENTERPRISE"
APP_VERSION = "2.0.0"
ADMIN_OPERATOR = "Umer Ali"

# Defaults used only when secrets are missing (local dev / demo).
_DEFAULTS: dict[str, Any] = {
    "LAMIX_URL": "http://51.77.216.195/crapi/lamix/viewstats",
    "LAMIX_TOKEN": "",
    "PURPLE_URL": "http://137.74.1.203/crapi/reseller/mdr.php",
    "PURPLE_TOKEN": "",
    "REGISTRY_URL": "",
    "ADMIN_KEY": "",
    "SESSION_TIMEOUT_MIN": 60,
    "API_TIMEOUT": 12,
    "API_RETRIES": 2,
    "LAMIX_RECORDS": 400,
    "PURPLE_RECORDS": 2000,
    "PURPLE_LOOKBACK_DAYS": 30,
    # WhatsApp alert engine (optional)
    "WHATSAPP_ALERTS_ENABLED": True,
    "WHATSAPP_THRESHOLD": 50,
    "WHATSAPP_WINDOW_MIN": 5,
    "WHATSAPP_COOLDOWN_MIN": 5,
    "WHATSAPP_PROVIDER": "log",  # log | callmebot | webhook | meta | twilio
    "WHATSAPP_WEBHOOK_URL": "",
    "CALLMEBOT_PHONE": "",
    "CALLMEBOT_APIKEY": "",
    "META_WA_TOKEN": "",
    "META_WA_PHONE_ID": "",
    "META_WA_TO": "",
    "TWILIO_SID": "",
    "TWILIO_TOKEN": "",
    "TWILIO_WA_FROM": "",
    "TWILIO_WA_TO": "",
}

IGNORE_TEAM_MEMBERS = {"UTS_Umer1", "UTS_Khadija"}

REFRESH_OPTIONS = {
    "OFF": 0,
    "5 sec": 5,
    "10 sec": 10,
    "15 sec": 15,
    "30 sec": 30,
    "60 sec": 60,
}

THEMES = {
    "Cyber": {
        "accent": "#00D4FF",
        "accent2": "#6D5DFC",
        "bg": "#030712",
        "bg2": "#081224",
        "card": "#0B1224",
        "text": "#E8F4FF",
        "muted": "#5A7AA0",
        "success": "#00E676",
        "danger": "#FF3D71",
        "gold": "#F0B429",
        "silver": "#A8B4C8",
        "bronze": "#CD7F32",
    },
    "Dark": {
        "accent": "#38BDF8",
        "accent2": "#818CF8",
        "bg": "#0A0A0B",
        "bg2": "#111827",
        "card": "#1F2937",
        "text": "#F3F4F6",
        "muted": "#9CA3AF",
        "success": "#34D399",
        "danger": "#F87171",
        "gold": "#FBBF24",
        "silver": "#D1D5DB",
        "bronze": "#D97706",
    },
    "Blue": {
        "accent": "#3B82F6",
        "accent2": "#06B6D4",
        "bg": "#020617",
        "bg2": "#0C1A3A",
        "card": "#122447",
        "text": "#DBEAFE",
        "muted": "#64748B",
        "success": "#22C55E",
        "danger": "#EF4444",
        "gold": "#EAB308",
        "silver": "#94A3B8",
        "bronze": "#B45309",
    },
    "Purple": {
        "accent": "#A78BFA",
        "accent2": "#F472B6",
        "bg": "#0B0618",
        "bg2": "#1A0B2E",
        "card": "#24153F",
        "text": "#F3E8FF",
        "muted": "#A78BFA",
        "success": "#4ADE80",
        "danger": "#FB7185",
        "gold": "#FCD34D",
        "silver": "#C4B5FD",
        "bronze": "#C084FC",
    },
    "Light": {
        "accent": "#0284C7",
        "accent2": "#7C3AED",
        "bg": "#F8FAFC",
        "bg2": "#FFFFFF",
        "card": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#64748B",
        "success": "#059669",
        "danger": "#DC2626",
        "gold": "#D97706",
        "silver": "#64748B",
        "bronze": "#B45309",
    },
}

SIDEBAR_PAGES = [
    ("Dashboard", "radar"),
    ("Live Monitor", "activity"),
    ("Analytics", "bar-chart-2"),
    ("Countries", "globe-2"),
    ("CLI Analysis", "cpu"),
    ("Search", "search"),
    ("Exports", "download"),
    ("Settings", "settings"),
    ("Admin", "shield"),
]

COLUMN_MAP = {
    "Time": "Time",
    "Panel": "Panel",
    "App": "CLI",
    "Number": "Number",
    "Country": "Country",
    "Message": "Message",
    "Team Member": "Team Member",
    "Range": "Range",
}


def _secret(key: str, default: Any = None) -> Any:
    try:
        if key in st.secrets:
            return st.secrets[key]
        # nested [api] style
        for section in ("api", "auth", "app"):
            try:
                sec = st.secrets[section]
                if key in sec:
                    return sec[key]
                # case variants
                low = key.lower()
                if low in sec:
                    return sec[low]
            except Exception:
                continue
    except Exception:
        pass
    if default is not None:
        return default
    return _DEFAULTS.get(key, "")


def get_settings() -> dict[str, Any]:
    """Resolve runtime settings from secrets with safe defaults."""
    return {
        "lamix_url": str(_secret("LAMIX_URL", _DEFAULTS["LAMIX_URL"])),
        "lamix_token": str(_secret("LAMIX_TOKEN", _DEFAULTS["LAMIX_TOKEN"])),
        "purple_url": str(_secret("PURPLE_URL", _DEFAULTS["PURPLE_URL"])),
        "purple_token": str(_secret("PURPLE_TOKEN", _DEFAULTS["PURPLE_TOKEN"])),
        "registry_url": str(_secret("REGISTRY_URL", _DEFAULTS["REGISTRY_URL"])),
        "admin_key": str(_secret("ADMIN_KEY", _DEFAULTS["ADMIN_KEY"])),
        "session_timeout_min": int(_secret("SESSION_TIMEOUT_MIN", _DEFAULTS["SESSION_TIMEOUT_MIN"])),
        "api_timeout": int(_secret("API_TIMEOUT", _DEFAULTS["API_TIMEOUT"])),
        "api_retries": int(_secret("API_RETRIES", _DEFAULTS["API_RETRIES"])),
        "lamix_records": int(_secret("LAMIX_RECORDS", _DEFAULTS["LAMIX_RECORDS"])),
        "purple_records": int(_secret("PURPLE_RECORDS", _DEFAULTS["PURPLE_RECORDS"])),
        "purple_lookback_days": int(_secret("PURPLE_LOOKBACK_DAYS", _DEFAULTS["PURPLE_LOOKBACK_DAYS"])),
        "team_file": str(_secret("TEAM_FILE", str(TEAM_FILE))),
        # WhatsApp OTP alert engine
        "whatsapp_alerts_enabled": bool(_secret("WHATSAPP_ALERTS_ENABLED", _DEFAULTS["WHATSAPP_ALERTS_ENABLED"])),
        "whatsapp_threshold": int(_secret("WHATSAPP_THRESHOLD", _DEFAULTS["WHATSAPP_THRESHOLD"])),
        "whatsapp_window_min": int(_secret("WHATSAPP_WINDOW_MIN", _DEFAULTS["WHATSAPP_WINDOW_MIN"])),
        "whatsapp_cooldown_min": int(_secret("WHATSAPP_COOLDOWN_MIN", _DEFAULTS["WHATSAPP_COOLDOWN_MIN"])),
        "whatsapp_provider": str(_secret("WHATSAPP_PROVIDER", _DEFAULTS["WHATSAPP_PROVIDER"])),
        "whatsapp_webhook_url": str(_secret("WHATSAPP_WEBHOOK_URL", _DEFAULTS["WHATSAPP_WEBHOOK_URL"])),
        "callmebot_phone": str(_secret("CALLMEBOT_PHONE", _DEFAULTS["CALLMEBOT_PHONE"])),
        "callmebot_apikey": str(_secret("CALLMEBOT_APIKEY", _DEFAULTS["CALLMEBOT_APIKEY"])),
        "meta_wa_token": str(_secret("META_WA_TOKEN", _DEFAULTS["META_WA_TOKEN"])),
        "meta_wa_phone_id": str(_secret("META_WA_PHONE_ID", _DEFAULTS["META_WA_PHONE_ID"])),
        "meta_wa_to": str(_secret("META_WA_TO", _DEFAULTS["META_WA_TO"])),
        "twilio_sid": str(_secret("TWILIO_SID", _DEFAULTS["TWILIO_SID"])),
        "twilio_token": str(_secret("TWILIO_TOKEN", _DEFAULTS["TWILIO_TOKEN"])),
        "twilio_wa_from": str(_secret("TWILIO_WA_FROM", _DEFAULTS["TWILIO_WA_FROM"])),
        "twilio_wa_to": str(_secret("TWILIO_WA_TO", _DEFAULTS["TWILIO_WA_TO"])),
    }


def theme_colors(name: str | None = None) -> dict[str, str]:
    key = name or st.session_state.get("theme", "Cyber")
    return THEMES.get(key, THEMES["Cyber"])
