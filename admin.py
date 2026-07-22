"""Admin panel — activation code management (Umer Ali only)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from auth import deactivate_code, generate_codes, is_admin, list_codes
from utils import log_event


def render_admin() -> None:
    if not is_admin():
        st.warning("Admin panel is restricted to operator **Umer Ali**.")
        st.stop()

    st.markdown('<div class="sl">ADMIN CONTROL CENTER</div>', unsafe_allow_html=True)
    st.caption("Registry actions: generate_codes · list_codes · deactivate_code · device unlock")

    # Generate
    st.markdown('<div class="ac glass"><div class="at">⚡ Generate Activation Codes</div>', unsafe_allow_html=True)
    g1, g2, g3 = st.columns([1, 1, 2])
    with g1:
        gen_count = st.number_input("How many?", min_value=1, max_value=50, value=5, key="gen_count")
    with g2:
        gen_prefix = st.text_input("Prefix", value="UTS", key="gen_prefix")
    with g3:
        st.write("")
        st.write("")
        if st.button("⚡ GENERATE", key="gen_btn", use_container_width=True):
            with st.spinner("Generating codes via registry..."):
                res = generate_codes(int(gen_count), gen_prefix.strip() or "UTS")
            if res.get("success"):
                codes = res.get("codes") or []
                st.success(f"✅ {len(codes)} codes generated")
                st.code("\n".join(codes), language=None)
                log_event("admin_generate", f"{len(codes)} codes", prefix=gen_prefix)
                st.session_state["codes_list"] = None
            else:
                st.error(f"❌ {res.get('msg', 'Unknown error')}")
    st.markdown("</div>", unsafe_allow_html=True)

    # List
    st.markdown('<div class="sl">ALL CODES</div>', unsafe_allow_html=True)
    b1, b2 = st.columns([1, 3])
    with b1:
        if st.button("📋 LOAD / REFRESH", key="load_codes", use_container_width=True):
            with st.spinner("Loading registry..."):
                res = list_codes()
            if res.get("success"):
                st.session_state["codes_list"] = res.get("codes", [])
                log_event("admin_list", f"{len(st.session_state['codes_list'])} codes")
            else:
                st.error(res.get("msg", "Failed to load codes"))

    codes_list = st.session_state.get("codes_list") or []
    if codes_list:
        cdf = pd.DataFrame(codes_list)

        def _style_status(v):
            if v == "ACTIVE":
                return "color:#00E676;font-weight:700"
            if v == "DEACTIVATED":
                return "color:#FF3D71;font-weight:700"
            return "color:#F0B429;font-weight:700"

        try:
            styled = cdf.style.map(_style_status, subset=["status"]) if "status" in cdf.columns else cdf
        except Exception:
            styled = cdf
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            column_config={
                "code": st.column_config.TextColumn("ACTIVATION CODE", width="large"),
                "operator": st.column_config.TextColumn("OPERATOR", width="medium"),
                "status": st.column_config.TextColumn("STATUS", width="small"),
                "created": st.column_config.TextColumn("CREATED", width="medium"),
                "activated_at": st.column_config.TextColumn("LOCKED AT", width="medium"),
                "last_seen": st.column_config.TextColumn("LAST SEEN", width="medium"),
                "fp": st.column_config.TextColumn("DEVICE FP", width="medium"),
            },
        )
    else:
        st.info("Click **LOAD / REFRESH** to pull codes from the registry.")

    # Deactivate
    st.markdown('<div class="ac glass"><div class="at">🔐 Deactivate / Reset Device Lock</div>', unsafe_allow_html=True)
    d1, d2 = st.columns([2, 1])
    with d1:
        deact = st.text_input("Code to deactivate", placeholder="UTS-XXXXXXXXXXXX", key="deact_in")
    with d2:
        st.write("")
        st.write("")
        if st.button("🚫 DEACTIVATE", key="deact_btn", use_container_width=True):
            if not deact.strip():
                st.warning("Enter a code.")
            else:
                with st.spinner("Deactivating..."):
                    res = deactivate_code(deact.strip().upper())
                if res.get("success"):
                    st.success("✅ Deactivated — device lock removed.")
                    log_event("admin_deactivate", deact.strip().upper())
                    st.session_state["codes_list"] = None
                    st.rerun()
                else:
                    st.error(f"❌ {res.get('msg', 'Failed')}")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Admin notes"):
        st.markdown(
            """
            - Only operator name **Umer Ali** (from registry `check_code`) can open this panel.
            - Codes are device-locked using server-side fingerprint (UA + language + encoding).
            - Keep `ADMIN_KEY` and `REGISTRY_URL` in Streamlit secrets — never commit them.
            """
        )
