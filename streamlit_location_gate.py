"""
streamlit_location_gate.py
--------------------------
Production-ready location capture for Streamlit Community Cloud.

Why browser GPS fails on share.streamlit.io
-------------------------------------------
Streamlit Cloud embeds your app in a cross-origin iframe. Modern browsers
enforce Permissions-Policy: geolocation is NOT allowed unless the parent
iframe has allow="geolocation". Streamlit Cloud does not set that attribute,
and you cannot change it from inside the app. Nested component iframes
(streamlit-js-eval, streamlit-geolocation, components.html) inherit the same
block. No pure client-side HTML/JS workaround can override this browser rule.

What this module does instead
-----------------------------
1. Reads the visitor's real client IP from reverse-proxy headers
   (X-Forwarded-For / X-Real-IP / CF-Connecting-IP / st.context).
2. Resolves approximate lat/lon via free HTTPS IP-geolocation APIs
   (ipapi.co → ipinfo.io → freeipapi.com), with graceful failover.
3. Stores results in:
       st.session_state["latitude"]
       st.session_state["longitude"]
   plus metadata (ip, city, country, source, accuracy note).
4. Renders a themed "GPS Location Required" gate that never dead-ends:
   auto-resolve → retry → optional manual lat/lon override.

Accuracy note: IP geolocation is city/region level (typically 5–50+ km),
not true GPS. That is the best you can guarantee inside Streamlit Cloud.

Usage (drop-in, call once near the top of app.py after set_page_config):

    from streamlit_location_gate import require_location
    require_location()   # st.stop()s until lat/lon are in session_state

Or integrate the functions into your existing file (see INTEGRATION below).
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any, Optional

import requests
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
IP_LOOKUP_TIMEOUT = 6  # seconds per provider
# Optional API tokens via st.secrets (leave empty for free anonymous tiers)
# st.secrets["IPAPI_TOKEN"]  / st.secrets["IPINFO_TOKEN"]


# ---------------------------------------------------------------------------
# Client IP resolution
# ---------------------------------------------------------------------------
def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value.strip())
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
    except ValueError:
        return False


def _first_public_ip(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    # X-Forwarded-For may be: client, proxy1, proxy2
    for part in re.split(r"[,\s]+", raw.strip()):
        part = part.strip()
        # strip port if present (e.g. 1.2.3.4:1234)
        if part.count(":") == 1 and "." in part:
            part = part.split(":", 1)[0]
        if part.startswith("[") and "]" in part:
            part = part[1 : part.index("]")]
        if _is_public_ip(part):
            return part
    return None


def get_client_ip() -> Optional[str]:
    """Best-effort public client IP behind Streamlit Cloud / proxies."""
    headers = {}
    try:
        headers = dict(st.context.headers)
    except Exception:
        try:
            import streamlit.web.server.websocket_headers as wh

            headers = dict(wh.get_websocket_headers() or {})
        except Exception:
            headers = {}

    # Normalize header keys (Tornado / ASGI casing varies)
    lower = {str(k).lower(): v for k, v in headers.items()}

    for key in (
        "x-forwarded-for",
        "x-real-ip",
        "cf-connecting-ip",
        "true-client-ip",
        "x-client-ip",
        "fly-client-ip",
        "fastly-client-ip",
    ):
        found = _first_public_ip(lower.get(key))
        if found:
            return found

    # Streamlit 1.45+ (often None on Community Cloud behind proxy)
    try:
        ip = getattr(st.context, "ip_address", None)
        if ip and _is_public_ip(str(ip)):
            return str(ip)
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# IP → lat/lon providers (HTTPS, free tiers)
# ---------------------------------------------------------------------------
def _lookup_ipapi_co(ip: Optional[str]) -> Optional[dict[str, Any]]:
    token = ""
    try:
        token = st.secrets.get("IPAPI_TOKEN", "")  # type: ignore[attr-defined]
    except Exception:
        token = ""
    if ip:
        url = f"https://ipapi.co/{ip}/json/"
    else:
        # Without client IP this returns the *server* IP — only last resort
        url = "https://ipapi.co/json/"
    headers = {"User-Agent": "streamlit-location-gate/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=IP_LOOKUP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data.get("reason") or data.get("error"))
    lat, lon = data.get("latitude"), data.get("longitude")
    if lat is None or lon is None:
        return None
    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "ip": data.get("ip") or ip,
        "city": data.get("city"),
        "region": data.get("region"),
        "country": data.get("country_name") or data.get("country"),
        "source": "ipapi.co",
        "accuracy": "ip_city",
    }


def _lookup_ipinfo(ip: Optional[str]) -> Optional[dict[str, Any]]:
    token = ""
    try:
        token = st.secrets.get("IPINFO_TOKEN", "")  # type: ignore[attr-defined]
    except Exception:
        token = ""
    base = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
    if token:
        base += f"?token={token}"
    r = requests.get(base, headers={"User-Agent": "streamlit-location-gate/1.0"}, timeout=IP_LOOKUP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    loc = data.get("loc")  # "lat,lon"
    if not loc or "," not in loc:
        return None
    lat_s, lon_s = loc.split(",", 1)
    return {
        "latitude": float(lat_s),
        "longitude": float(lon_s),
        "ip": data.get("ip") or ip,
        "city": data.get("city"),
        "region": data.get("region"),
        "country": data.get("country"),
        "source": "ipinfo.io",
        "accuracy": "ip_city",
    }


def _lookup_freeipapi(ip: Optional[str]) -> Optional[dict[str, Any]]:
    # https://freeipapi.com — free, HTTPS, no key for light use
    url = f"https://freeipapi.com/api/json/{ip}" if ip else "https://freeipapi.com/api/json"
    r = requests.get(url, headers={"User-Agent": "streamlit-location-gate/1.0"}, timeout=IP_LOOKUP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    lat, lon = data.get("latitude"), data.get("longitude")
    if lat is None or lon is None:
        return None
    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "ip": data.get("ipAddress") or ip,
        "city": data.get("cityName"),
        "region": data.get("regionName"),
        "country": data.get("countryName"),
        "source": "freeipapi.com",
        "accuracy": "ip_city",
    }


def resolve_ip_location(ip: Optional[str] = None) -> dict[str, Any]:
    """
    Resolve lat/lon for a client IP using multiple free providers.
    Returns a dict with latitude/longitude or raises RuntimeError.
    """
    if ip is None:
        ip = get_client_ip()

    errors: list[str] = []
    for name, fn in (
        ("ipapi.co", _lookup_ipapi_co),
        ("ipinfo.io", _lookup_ipinfo),
        ("freeipapi.com", _lookup_freeipapi),
    ):
        try:
            result = fn(ip)
            if result and result.get("latitude") is not None:
                return result
            errors.append(f"{name}: empty coords")
        except Exception as exc:  # noqa: BLE001 — collect and continue
            errors.append(f"{name}: {exc}")

    raise RuntimeError("All IP geolocation providers failed: " + " | ".join(errors))


def store_location(
    latitude: float,
    longitude: float,
    *,
    ip: Optional[str] = None,
    city: Optional[str] = None,
    region: Optional[str] = None,
    country: Optional[str] = None,
    source: str = "manual",
    accuracy: str = "manual",
) -> None:
    """Write required session_state keys used by the rest of the app."""
    st.session_state["latitude"] = float(latitude)
    st.session_state["longitude"] = float(longitude)
    st.session_state["location_ip"] = ip
    st.session_state["location_city"] = city
    st.session_state["location_region"] = region
    st.session_state["location_country"] = country
    st.session_state["location_source"] = source
    st.session_state["location_accuracy"] = accuracy
    st.session_state["location_ready"] = True


def location_is_ready() -> bool:
    return (
        st.session_state.get("location_ready") is True
        and st.session_state.get("latitude") is not None
        and st.session_state.get("longitude") is not None
    )


# ---------------------------------------------------------------------------
# Optional: browser GPS attempt (works on direct hosts, NOT Streamlit Cloud)
# ---------------------------------------------------------------------------
def _render_browser_gps_probe() -> None:
    """
    Best-effort browser GPS via components.html.
    On Streamlit Cloud this will almost always hit Permissions-Policy and
    post {error: ...}. Kept as an optional path for self-hosted deploys
    where the top-level page can allow geolocation.
    """
    # postMessage to parent is unreliable across Streamlit component iframes;
    # we use query-param style via streamlit's component value protocol is not
    # available in raw components.html. So this is informational only unless
    # you host outside Cloud. Primary path remains IP geolocation.
    components.html(
        """
        <div id="gps-status" style="font-family:monospace;font-size:11px;color:#5a7aa0;padding:4px 0;">
          Probing browser GPS (optional)…
        </div>
        <script>
        (function () {
          const el = document.getElementById('gps-status');
          if (!navigator.geolocation) {
            el.textContent = 'Browser GPS API unavailable in this context.';
            return;
          }
          try {
            navigator.geolocation.getCurrentPosition(
              function (pos) {
                el.textContent = 'Browser GPS OK: ' +
                  pos.coords.latitude.toFixed(5) + ', ' +
                  pos.coords.longitude.toFixed(5) +
                  ' (Cloud iframe usually blocks this — use IP path)';
              },
              function (err) {
                el.textContent = 'Browser GPS blocked: ' + (err && err.message ? err.message : err);
              },
              { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
            );
          } catch (e) {
            el.textContent = 'Browser GPS exception: ' + e;
          }
        })();
        </script>
        """,
        height=28,
    )


# ---------------------------------------------------------------------------
# UI gate (matches UTS HUNTERS dark theme)
# ---------------------------------------------------------------------------
_GATE_CSS = """
<style>
.loc-card{
  background:var(--card,#0a1a35);border:1px solid var(--b2,#1a3a70);
  border-radius:6px;padding:40px 36px;box-shadow:0 20px 60px rgba(0,0,0,.5);
  max-width:520px;margin:0 auto;
}
.loc-icon{font-size:42px;text-align:center;margin-bottom:12px}
.loc-title{
  font-family:Inter,sans-serif;font-size:22px;font-weight:900;color:#fff;
  text-align:center;margin-bottom:6px
}
.loc-sub{
  font-family:'JetBrains Mono',monospace;font-size:10px;color:#304560;
  letter-spacing:2px;text-transform:uppercase;text-align:center;margin-bottom:22px
}
.loc-msg{
  font-family:'JetBrains Mono',monospace;font-size:11px;color:#5a7aa0;
  line-height:1.7;text-align:center;margin-bottom:18px
}
.loc-ok{
  background:rgba(0,230,118,.08);border:1px solid rgba(0,230,118,.3);
  border-radius:3px;padding:10px 14px;font-family:'JetBrains Mono',monospace;
  font-size:11px;color:#00e676;margin-top:12px;text-align:center
}
.loc-err{
  background:rgba(255,61,113,.08);border:1px solid rgba(255,61,113,.3);
  border-radius:3px;padding:10px 14px;font-family:'JetBrains Mono',monospace;
  font-size:11px;color:#ff3d71;margin-top:12px;text-align:center
}
.loc-meta{
  margin-top:16px;font-family:'JetBrains Mono',monospace;font-size:9px;
  color:#1a3a70;text-align:center;line-height:1.9
}
</style>
"""


def require_location(
    *,
    auto_resolve: bool = True,
    allow_manual: bool = True,
    show_browser_probe: bool = False,
    heading: str = "GPS Location Required",
) -> None:
    """
    Block the app until latitude/longitude are stored in session_state.
    Call this before your activation / auth screen.
    """
    if location_is_ready():
        return

    st.markdown(_GATE_CSS, unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="hdr" style="text-align:center;padding:32px 20px 8px">
          <div class="badge" style="display:inline-block;border:1px solid #0066bb;
            border-radius:2px;padding:4px 18px;font-family:'JetBrains Mono',monospace;
            font-size:10px;font-weight:600;color:#00aaff;letter-spacing:6px;
            text-transform:uppercase;margin-bottom:12px">UTS SYSTEMS</div>
          <div style="font-size:40px;font-weight:900;color:#fff;letter-spacing:-1px">
            ⚡ LOCATION <span style="color:#00aaff">CHECK</span>
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#5a7aa0;
            letter-spacing:4px;text-transform:uppercase;margin:10px 0 20px">{heading}</div>
          <div style="height:1px;background:linear-gradient(90deg,transparent,#0066bb,transparent);
            margin:0 auto 20px;max-width:600px"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown('<div class="loc-card">', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="loc-icon">📡</div>
            <div class="loc-title">{heading}</div>
            <div class="loc-sub">Secure session bootstrap</div>
            <div class="loc-msg">
              Browser GPS is blocked inside Streamlit Cloud iframes
              (Permissions-Policy). We capture approximate coordinates from
              your network IP so you can continue to activation.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if show_browser_probe:
            _render_browser_gps_probe()

        # ---- Auto resolve on first visit ----
        if auto_resolve and not st.session_state.get("_loc_attempted"):
            st.session_state["_loc_attempted"] = True
            with st.spinner("Resolving secure network location…"):
                try:
                    result = resolve_ip_location()
                    store_location(
                        result["latitude"],
                        result["longitude"],
                        ip=result.get("ip"),
                        city=result.get("city"),
                        region=result.get("region"),
                        country=result.get("country"),
                        source=result.get("source", "ip"),
                        accuracy=result.get("accuracy", "ip_city"),
                    )
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.session_state["_loc_last_error"] = str(exc)

        err = st.session_state.get("_loc_last_error")
        if err:
            st.markdown(
                f'<div class="loc-err">⚠ Auto-locate failed — {err}</div>',
                unsafe_allow_html=True,
            )

        c_a, c_b = st.columns(2)
        with c_a:
            if st.button("▶  DETECT LOCATION", use_container_width=True, key="loc_retry"):
                st.session_state["_loc_attempted"] = True
                with st.spinner("Resolving…"):
                    try:
                        result = resolve_ip_location()
                        store_location(
                            result["latitude"],
                            result["longitude"],
                            ip=result.get("ip"),
                            city=result.get("city"),
                            region=result.get("region"),
                            country=result.get("country"),
                            source=result.get("source", "ip"),
                            accuracy=result.get("accuracy", "ip_city"),
                        )
                        st.session_state.pop("_loc_last_error", None)
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.session_state["_loc_last_error"] = str(exc)
                        st.rerun()
        with c_b:
            show_manual = st.session_state.get("_show_manual_loc", False)
            if st.button(
                "✎  MANUAL ENTRY" if allow_manual else "—",
                use_container_width=True,
                key="loc_manual_toggle",
                disabled=not allow_manual,
            ):
                st.session_state["_show_manual_loc"] = not show_manual
                st.rerun()

        if allow_manual and st.session_state.get("_show_manual_loc"):
            st.markdown(
                '<div class="loc-sub" style="margin-top:18px">Manual coordinates</div>',
                unsafe_allow_html=True,
            )
            m1, m2 = st.columns(2)
            with m1:
                man_lat = st.number_input(
                    "Latitude",
                    min_value=-90.0,
                    max_value=90.0,
                    value=0.0,
                    format="%.6f",
                    key="man_lat",
                )
            with m2:
                man_lon = st.number_input(
                    "Longitude",
                    min_value=-180.0,
                    max_value=180.0,
                    value=0.0,
                    format="%.6f",
                    key="man_lon",
                )
            if st.button("✓  USE THESE COORDINATES", use_container_width=True, key="loc_manual_apply"):
                if man_lat == 0.0 and man_lon == 0.0:
                    st.markdown(
                        '<div class="loc-err">Enter non-zero coordinates (0,0 is not accepted).</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    store_location(man_lat, man_lon, source="manual", accuracy="manual")
                    st.rerun()

        client_ip = get_client_ip() or "undetected"
        st.markdown(
            f"""
            <div class="loc-meta">
              Client IP hint: {client_ip}<br>
              Method: IP geolocation (city-level) · Fallback: manual entry<br>
              True GPS requires host allow="geolocation" (not available on Streamlit Cloud)
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# ---------------------------------------------------------------------------
# INTEGRATION snippet for your existing app.py
# ---------------------------------------------------------------------------
INTEGRATION_SNIPPET = r'''
# ---- place AFTER st.set_page_config + CSS, BEFORE auth flow ----
from streamlit_location_gate import require_location, location_is_ready

require_location(auto_resolve=True, allow_manual=True, show_browser_probe=False)

# From here on, these are always set:
#   st.session_state["latitude"]
#   st.session_state["longitude"]
# Optional metadata:
#   st.session_state["location_ip"]
#   st.session_state["location_city"]
#   st.session_state["location_country"]
#   st.session_state["location_source"]   # e.g. "ipapi.co" | "manual"
'''
