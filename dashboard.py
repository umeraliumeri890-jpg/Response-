"""Dashboard pages: KPIs, live monitor, search, exports, settings."""
from __future__ import annotations

import html
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st

try:
    from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode, JsCode

    HAS_AGGRID = True
except Exception:  # pragma: no cover
    HAS_AGGRID = False
    AgGrid = None  # type: ignore
    DataReturnMode = None  # type: ignore
    GridOptionsBuilder = None  # type: ignore
    GridUpdateMode = None  # type: ignore
    JsCode = None  # type: ignore

from api import load_live_data
from charts import (
    api_comparison,
    cli_bar,
    country_bar,
    country_map,
    country_pie,
    daily_trend,
    hourly_trend,
    live_timeline,
    otp_heatmap,
    team_performance,
)
from config import REFRESH_OPTIONS, THEMES, get_settings, theme_colors
from utils import (
    apply_search,
    compute_kpis,
    df_to_csv_bytes,
    df_to_excel_bytes,
    df_to_json_bytes,
    df_to_pdf_bytes,
    push_search_history,
    system_info,
    touch_activity,
)


def _fmt_delay(sec: float) -> str:
    if sec < 60:
        return f"{sec:.0f}s"
    if sec < 3600:
        return f"{sec/60:.1f}m"
    return f"{sec/3600:.1f}h"


def render_header(operator: str, is_admin: bool, health: dict) -> None:
    up = sum(1 for h in health.values() if h.get("ok"))
    total = max(len(health), 1)
    live = "LIVE" if up else "DEGRADED"
    color = "#00E676" if up == total and total else ("#F0B429" if up else "#FF3D71")
    st.markdown(
        f"""
        <div class="hdr">
          <div class="badge">UTS SYSTEMS · ENTERPRISE</div>
          <div class="title">⚡ UTS <span>HUNTERS</span> ⚡</div>
          <div class="sub">> Cyber SOC · Multi-API OTP Intelligence</div>
          <div class="divider"></div>
        </div>
        <div class="opbar glass">
          <div class="oi"><span class="pd" style="background:{color};box-shadow:0 0 8px {color}"></span><span style="color:{color}">{live}</span></div>
          <div class="od">|</div>
          <div class="oi">OPERATOR: <span>{operator.upper()}</span></div>
          <div class="od">|</div>
          <div class="oi">SESSION: <span>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span></div>
          <div class="od">|</div>
          <div class="oi">APIs: <span>{up}/{total}</span></div>
          {"<div class='od'>|</div><div class='oi'><span style='color:#F0B429'>👑 ADMIN</span></div>" if is_admin else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_cards(kpis: dict[str, Any], health: dict) -> None:
    api_status = "UP" if any(h.get("ok") for h in health.values()) else "DOWN"
    cards = [
        ("Total OTP", f"{kpis['total_otp']:,}", "📦"),
        ("Today OTP", f"{kpis['today_otp']:,}", "📅"),
        ("5 Min OTP", f"{kpis['min5_otp']:,}", "⚡"),
        ("Unique Numbers", f"{kpis['unique_numbers']:,}", "🔢"),
        ("Unique CLI", f"{kpis['unique_cli']:,}", "📡"),
        ("API Status", api_status, "💚" if api_status == "UP" else "💔"),
        ("Avg Delay", _fmt_delay(kpis["avg_delay_sec"]), "⏱️"),
        ("Countries", f"{kpis['countries']:,}", "🌍"),
        ("Matched", f"{kpis['matched']:,}", "🎯"),
    ]
    cols = st.columns(3)
    for i, (label, value, icon) in enumerate(cards):
        with cols[i % 3]:
            st.markdown(
                f'<div class="kpi glass"><div class="kpi-icon">{icon}</div>'
                f'<div class="kpi-val">{value}</div><div class="kpi-label">{label}</div></div>',
                unsafe_allow_html=True,
            )


def live_cli_cards(top_cli: list[dict]) -> None:
    """Render top-3 CLI cards. Use single-line HTML (no indented markdown code fences)."""
    slots = (top_cli + [{"name": "—", "count": 0}] * 3)[:3]
    ranks = ["r1", "r2", "r3"]
    medals = ["🥇 Top 1 — Last 5 Min", "🥈 Top 2 — Last 5 Min", "🥉 Top 3 — Last 5 Min"]
    cols = st.columns(3)
    for i, item in enumerate(slots):
        name = html.escape(str(item.get("name", "—")))
        count = int(item.get("count", 0) or 0)
        # Keep HTML on one line — Streamlit treats indented multi-line blocks as code
        card = (
            f'<div class="rc {ranks[i]} glass">'
            f'<div class="rwm">{i + 1}</div>'
            f'<div class="rb">{medals[i]}</div>'
            f'<div class="rn">{name}</div>'
            f'<div class="rc_">⚡ {count} OTPs</div>'
            f"</div>"
        )
        with cols[i]:
            st.markdown(card, unsafe_allow_html=True)


def api_health_cards(health: dict) -> None:
    if not health:
        st.info("No API health data yet.")
        return
    cols = st.columns(len(health))
    for i, (name, h) in enumerate(health.items()):
        status = h.get("status", "DOWN")
        color = "#00E676" if h.get("ok") else "#FF3D71"
        err = html.escape(str(h.get("error") or "None"))
        sync = html.escape(str(h.get("last_sync", "—")))
        with cols[i]:
            st.markdown(
                f'<div class="health glass">'
                f'<div class="health-name">{html.escape(str(name))}</div>'
                f'<div class="health-status" style="color:{color}">{html.escape(str(status))}</div>'
                f'<div class="health-row"><span>Latency</span><b>{h.get("latency_ms", 0)} ms</b></div>'
                f'<div class="health-row"><span>Records</span><b>{h.get("records", 0)}</b></div>'
                f'<div class="health-row"><span>Last Sync</span><b>{sync}</b></div>'
                f'<div class="health-row"><span>Errors</span><b>{err}</b></div>'
                f"</div>",
                unsafe_allow_html=True,
            )


def aggrid_table(df: pd.DataFrame, height: int = 420, key: str = "grid") -> pd.DataFrame:
    if df is None or df.empty:
        st.caption("No rows to display.")
        return df
    show = df.drop(columns=["dt"], errors="ignore").copy()

    if not HAS_AGGRID:
        st.dataframe(show, use_container_width=True, height=height, hide_index=True)
        return show

    gb = GridOptionsBuilder.from_dataframe(show)
    gb.configure_default_column(
        filterable=True,
        sortable=True,
        resizable=True,
        editable=False,
        groupable=False,
    )
    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=int(st.session_state.get("page_size", 50)),
    )
    gb.configure_side_bar()
    gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    if "Time" in show.columns:
        gb.configure_column("Time", pinned="left")
    if "Team Member" in show.columns:
        gb.configure_column(
            "Team Member",
            cellStyle=JsCode(
                """
                function(params) {
                  if (params.value && params.value.toString().trim() !== '') {
                    return {'color': '#00D4FF', 'fontWeight': '700', 'borderLeft': '3px solid #00D4FF'};
                  }
                  return {};
                }
                """
            ),
        )
    grid_options = gb.build()
    t = theme_colors()
    custom_css = {
        ".ag-root-wrapper": {
            "background-color": t["card"],
            "border": f"1px solid {t['accent']}33",
            "border-radius": "8px",
        },
        ".ag-header": {"background-color": t["bg2"], "color": t["accent"]},
        ".ag-row": {"background-color": t["card"], "color": t["text"]},
        ".ag-row-odd": {"background-color": t["bg2"]},
    }
    resp = AgGrid(
        show,
        gridOptions=grid_options,
        height=height,
        theme="streamlit",
        update_mode=GridUpdateMode.NO_UPDATE,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
        custom_css=custom_css,
        key=key,
        reload_data=False,
    )
    try:
        return pd.DataFrame(resp["data"])
    except Exception:
        return show


def _notify_events(df: pd.DataFrame, health: dict) -> None:
    """Toast notifications for API down / high traffic / new OTPs."""
    if not st.session_state.get("notifications_enabled", True):
        return
    for name, h in (health or {}).items():
        flag = f"notified_down_{name}"
        if not h.get("ok") and not st.session_state.get(flag):
            st.toast(f"⚠ API DOWN: {name} — {h.get('error') or 'unreachable'}", icon="🔴")
            st.session_state[flag] = True
        if h.get("ok"):
            st.session_state[flag] = False

    kpis = compute_kpis(df, tz=st.session_state.get("timezone", "UTC"))
    if kpis["min5_otp"] >= int(st.session_state.get("high_traffic_threshold", 80)):
        last = st.session_state.get("last_high_traffic_toast", 0)
        now_ts = datetime.now(timezone.utc).replace(tzinfo=None).timestamp()
        if now_ts - last > 60:
            st.toast(f"🔥 High traffic: {kpis['min5_otp']} OTPs in 5 min", icon="⚡")
            st.session_state["last_high_traffic_toast"] = now_ts

    prev = int(st.session_state.get("prev_total_otp", 0))
    if kpis["total_otp"] > prev > 0:
        st.toast(f"✨ +{kpis['total_otp'] - prev} new OTP records", icon="📨")
    st.session_state["prev_total_otp"] = kpis["total_otp"]


def page_dashboard(df: pd.DataFrame, health: dict) -> None:
    st.markdown('<div class="sl">COMMAND OVERVIEW</div>', unsafe_allow_html=True)
    kpis = compute_kpis(df, tz=st.session_state.get("timezone", "UTC"))
    kpi_cards(kpis, health)
    st.markdown('<div class="sl">LIVE CLI LEADERS</div>', unsafe_allow_html=True)
    live_cli_cards(kpis.get("top_cli") or [])
    st.markdown('<div class="sl">API HEALTH</div>', unsafe_allow_html=True)
    api_health_cards(health)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(live_timeline(df), use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.plotly_chart(api_comparison(df), use_container_width=True, config={"displayModeBar": False})
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(country_pie(df), use_container_width=True, config={"displayModeBar": False})
    with c4:
        st.plotly_chart(cli_bar(df), use_container_width=True, config={"displayModeBar": False})


def page_live_monitor(df: pd.DataFrame) -> None:
    st.markdown('<div class="sl">LIVE MONITOR</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        target = st.text_input("🎯 Target CLI", value=st.session_state.get("target_cli", "MYOB"), key="target_cli")
    with c2:
        limit = st.number_input("Stream buffer", min_value=25, max_value=5000, value=int(st.session_state.get("stream_buffer", 500)), step=25)
        st.session_state["stream_buffer"] = int(limit)
    with c3:
        only_matched = st.toggle("Matched only", value=False)

    kpis = compute_kpis(df)
    live_cli_cards(kpis.get("top_cli") or [])

    work = df.copy()
    if target.strip() and "CLI" in work.columns:
        tgt = work[work["CLI"].astype(str).str.contains(target.strip(), case=False, na=False)]
    else:
        tgt = work.iloc[0:0]

    st.markdown(f'<div class="sl">TARGET TRACKER — {target.upper() or "ALL"}</div>', unsafe_allow_html=True)
    aggrid_table(tgt.head(80), height=280, key="tgt_grid")

    stream = work.head(int(limit))
    if only_matched and "Team Member" in stream.columns:
        stream = stream[stream["Team Member"].astype(str).str.strip() != ""]
    st.markdown('<div class="sl">GLOBAL LIVE STREAM</div>', unsafe_allow_html=True)
    aggrid_table(stream, height=520, key="live_grid")


def page_analytics(df: pd.DataFrame) -> None:
    st.markdown('<div class="sl">ANALYTICS SUITE</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        st.plotly_chart(live_timeline(df), use_container_width=True)
        st.plotly_chart(hourly_trend(df), use_container_width=True)
        st.plotly_chart(otp_heatmap(df), use_container_width=True)
    with b:
        st.plotly_chart(daily_trend(df), use_container_width=True)
        st.plotly_chart(api_comparison(df), use_container_width=True)
        st.plotly_chart(team_performance(df), use_container_width=True)


def page_countries(df: pd.DataFrame) -> None:
    st.markdown('<div class="sl">COUNTRY INTELLIGENCE</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(country_pie(df), use_container_width=True)
        st.plotly_chart(country_bar(df), use_container_width=True)
    with c2:
        st.plotly_chart(country_map(df), use_container_width=True)
        if df is not None and not df.empty and "Country" in df.columns:
            vc = df["Country"].value_counts().rename_axis("Country").reset_index(name="OTP")
            aggrid_table(vc, height=360, key="country_table")


def page_cli(df: pd.DataFrame) -> None:
    st.markdown('<div class="sl">CLI ANALYSIS</div>', unsafe_allow_html=True)
    st.plotly_chart(cli_bar(df, top_n=25), use_container_width=True)
    if df is not None and not df.empty and "CLI" in df.columns:
        vc = df["CLI"].value_counts().rename_axis("CLI").reset_index(name="OTP")
        if "Panel" in df.columns:
            pivot = pd.crosstab(df["CLI"], df["Panel"])
            vc = vc.merge(pivot, left_on="CLI", right_index=True, how="left")
        aggrid_table(vc.head(200), height=480, key="cli_table")


def page_search(df: pd.DataFrame) -> None:
    st.markdown('<div class="sl">ADVANCED SEARCH</div>', unsafe_allow_html=True)
    countries = ["All"]
    members = ["All"]
    if df is not None and not df.empty:
        if "Country" in df.columns:
            countries += sorted([c for c in df["Country"].dropna().unique().tolist() if c])
        if "Team Member" in df.columns:
            members += sorted([m for m in df["Team Member"].dropna().unique().tolist() if str(m).strip()])

    favs = st.session_state.setdefault("favorite_filters", [])
    if favs:
        pick = st.selectbox("⭐ Favorite filters", ["—"] + [f["label"] for f in favs])
        if pick != "—":
            fav = next(f for f in favs if f["label"] == pick)
            for k, v in fav["values"].items():
                st.session_state[k] = v

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        cli = st.text_input("CLI", key="s_cli")
        number = st.text_input("Number", key="s_number")
    with c2:
        country = st.selectbox("Country", countries, key="s_country")
        member = st.selectbox("Team Member", members, key="s_member")
    with c3:
        message = st.text_input("Message", key="s_message")
        api = st.selectbox("API", ["All", "LAMIX", "PURPLE"], key="s_api")
    with c4:
        mode = st.selectbox("Match mode", ["Contains", "Starts with", "Ends with"], key="s_mode")
        use_regex = st.toggle("Regex", value=False, key="s_regex")

    d1, d2, d3 = st.columns([1, 1, 1])
    with d1:
        date_from = st.date_input("From", value=None, key="s_from")
    with d2:
        date_to = st.date_input("To", value=None, key="s_to")
    with d3:
        st.write("")
        st.write("")
        run = st.button("🔍 Search", use_container_width=True)
        save_fav = st.button("⭐ Save filter", use_container_width=True)

    if save_fav:
        label = f"{cli or '*'}|{country}|{api}|{mode}"
        favs.insert(
            0,
            {
                "label": label,
                "values": {
                    "s_cli": cli,
                    "s_number": number,
                    "s_country": country,
                    "s_member": member,
                    "s_message": message,
                    "s_api": api,
                    "s_mode": mode,
                    "s_regex": use_regex,
                },
            },
        )
        st.session_state["favorite_filters"] = favs[:15]
        st.success("Filter saved.")

    filtered = apply_search(
        df,
        cli=cli,
        country=country,
        number=number,
        message=message,
        api=api,
        member=member,
        date_from=datetime.combine(date_from, datetime.min.time()) if isinstance(date_from, date) else None,
        date_to=datetime.combine(date_to, datetime.min.time()) if isinstance(date_to, date) else None,
        mode=mode,
        use_regex=use_regex,
    )
    if run:
        push_search_history(
            {
                "ts": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                "cli": cli,
                "country": country,
                "api": api,
                "hits": len(filtered),
            }
        )
    st.caption(f"Results: **{0 if filtered is None else len(filtered)}**")
    aggrid_table(filtered if filtered is not None else df, height=520, key="search_grid")
    st.session_state["last_filtered"] = filtered

    hist = st.session_state.get("search_history") or []
    if hist:
        with st.expander("Search history"):
            st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)


def page_exports(df: pd.DataFrame) -> None:
    st.markdown('<div class="sl">EXPORT CENTER</div>', unsafe_allow_html=True)
    scope = st.radio("Scope", ["Current Filter", "Full Data"], horizontal=True)
    data = st.session_state.get("last_filtered") if scope == "Current Filter" else df
    if data is None or (isinstance(data, pd.DataFrame) and data.empty):
        data = df
    if data is None:
        data = pd.DataFrame()
    export_df = data.drop(columns=["dt"], errors="ignore") if isinstance(data, pd.DataFrame) else pd.DataFrame()
    st.write(f"Rows ready: **{len(export_df)}**")

    c1, c2, c3, c4 = st.columns(4)
    ts = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%Y%m%d_%H%M%S")
    with c1:
        st.download_button("⬇ CSV", data=df_to_csv_bytes(export_df), file_name=f"uts_otp_{ts}.csv", mime="text/csv", use_container_width=True)
    with c2:
        st.download_button("⬇ Excel", data=df_to_excel_bytes(export_df), file_name=f"uts_otp_{ts}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c3:
        st.download_button("⬇ JSON", data=df_to_json_bytes(export_df), file_name=f"uts_otp_{ts}.json", mime="application/json", use_container_width=True)
    with c4:
        pdf = df_to_pdf_bytes(export_df)
        mime = "application/pdf" if pdf[:4] == b"%PDF" else "text/plain"
        ext = "pdf" if mime.endswith("pdf") else "txt"
        st.download_button("⬇ PDF", data=pdf, file_name=f"uts_otp_{ts}.{ext}", mime=mime, use_container_width=True)

    st.dataframe(export_df.head(100), use_container_width=True, hide_index=True)


def page_settings() -> None:
    st.markdown('<div class="sl">SETTINGS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        theme = st.selectbox("Theme", list(THEMES.keys()), index=list(THEMES.keys()).index(st.session_state.get("theme", "Cyber")))
        st.session_state["theme"] = theme
        refresh = st.selectbox(
            "Auto refresh",
            list(REFRESH_OPTIONS.keys()),
            index=list(REFRESH_OPTIONS.keys()).index(st.session_state.get("refresh_label", "15 sec")),
        )
        st.session_state["refresh_label"] = refresh
        st.session_state["refresh_sec"] = REFRESH_OPTIONS[refresh]
        st.session_state["timezone"] = st.selectbox(
            "Timezone",
            ["UTC", "America/Los_Angeles", "America/New_York", "Europe/London", "Asia/Karachi", "Asia/Dubai", "Asia/Kolkata"],
            index=0 if st.session_state.get("timezone", "UTC") == "UTC" else None,
        )
    with c2:
        st.session_state["page_size"] = st.number_input("Table page size", 10, 500, int(st.session_state.get("page_size", 50)), 10)
        st.session_state["notifications_enabled"] = st.toggle("Toast notifications", value=st.session_state.get("notifications_enabled", True))
        st.session_state["desktop_notify"] = st.toggle("Desktop notification hint", value=st.session_state.get("desktop_notify", False))
        st.session_state["high_traffic_threshold"] = st.number_input("High traffic threshold (5m)", 10, 5000, int(st.session_state.get("high_traffic_threshold", 80)), 10)
        if st.button("Force API refresh", use_container_width=True):
            load_live_data(force=True)
            st.success("Cache cleared — next load is fresh.")
            st.rerun()

    st.markdown('<div class="sl">SYSTEM INFORMATION</div>', unsafe_allow_html=True)
    info = system_info()
    st.json(info)

    if st.session_state.get("desktop_notify"):
        st.markdown(
            """
            <script>
            if (window.Notification && Notification.permission !== 'granted') {
              Notification.requestPermission();
            }
            </script>
            """,
            unsafe_allow_html=True,
        )

    st.caption("Keyboard: use sidebar to jump pages · R to rerun (Streamlit) · settings persist in session.")


def error_boundary(exc: Exception) -> None:
    st.markdown('<div class="error-box glass">', unsafe_allow_html=True)
    st.error("Something went wrong while loading the dashboard.")
    st.exception(exc)
    if st.button("🔄 Retry", key="err_retry"):
        load_live_data(force=True)
        touch_activity()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
