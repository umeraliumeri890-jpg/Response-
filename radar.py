# ============================================================
# MAIN DATA PROCESSING & DISPLAY (NO WHILE LOOP)
# ============================================================
try:
    r = requests.get(URL, params={"token": TOKEN, "records": 500}, timeout=10)
    if r.status_code == 200:
        raw_json = r.json().get("data", [])
        df = pd.DataFrame(raw_json)
        if not df.empty:
            threading.Thread(target=stream_to_google_sheet, args=(raw_json,), daemon=True).start()
            df['dt'] = pd.to_datetime(df['dt'])
            now   = datetime.now()
            df_5m = df[df['dt'] >= now - timedelta(minutes=5)]

            t1n, t1c = "NO DATA", 0
            t2n, t2c = "NO DATA", 0
            t3n, t3c = "NO DATA", 0
            if not df_5m.empty and 'cli' in df_5m.columns:
                tc = df_5m['cli'].value_counts().head(3)
                if len(tc) >= 1: t1n, t1c = tc.index[0], int(tc.iloc[0])
                if len(tc) >= 2: t2n, t2c = tc.index[1], int(tc.iloc[1])
                if len(tc) >= 3: t3n, t3c = tc.index[2], int(tc.iloc[2])

            tr = len(df)
            uc = df['cli'].nunique() if 'cli' in df.columns else 0
            un = df['num'].nunique() if 'num' in df.columns else 0
            df_tgt = df[df['cli'].str.contains(target_cli, case=False, na=False)].copy()

            with placeholder.container():
                st.markdown(f"""
                <div class="sr">
                    <div class="sb"><div class="sv">{tr}</div><div class="sl2">Total Records</div></div>
                    <div class="sb"><div class="sv">{t1c}</div><div class="sl2">Top CLI (5min)</div></div>
                    <div class="sb"><div class="sv">{uc}</div><div class="sl2">Unique CLIs</div></div>
                    <div class="sb"><div class="sv">{un}</div><div class="sl2">Unique Numbers</div></div>
                </div>
                <div class="lg">
                    <div class="rc r1"><div class="rwm">1</div>
                        <div class="rb">🏆 Top 1 — Last 5 Min</div>
                        <div class="rn">{t1n}</div><div class="rc_">⚡ {t1c} OTPs</div></div>
                    <div class="rc r2"><div class="rwm">2</div>
                        <div class="rb">🥈 Top 2 — Last 5 Min</div>
                        <div class="rn">{t2n}</div><div class="rc_">⚡ {t2c} OTPs</div></div>
                    <div class="rc r3"><div class="rwm">3</div>
                        <div class="rb">🥉 Top 3 — Last 5 Min</div>
                        <div class="rn">{t3n}</div><div class="rc_">⚡ {t3c} OTPs</div></div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f'<div class="sl">LIVE TARGET TRACKER — AGENT: {target_cli.upper()}</div>', unsafe_allow_html=True)
                if not df_tgt.empty:
                    md = df_tgt.head(25).copy()
                    md[['Team Member', 'Range']] = md['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                    md['Country'] = md['num'].apply(get_country)
                    md = md[['dt','cli','num','Country','message','Team Member','Range']].copy()
                    md.columns = ['Time','App','Number','Country','Message','Team Member','Range']
                    md['Time'] = pd.to_datetime(md['Time'])
                    md = md.sort_values('Time', ascending=False)
                    md['Time'] = md['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    st.dataframe(md.style.apply(highlight_team, axis=1),
                                 use_container_width=True, height=400, hide_index=True, column_config=col_cfg)
                else:
                    st.caption("▸ No packets for current target agent.")

                st.markdown('<div class="sl">GLOBAL LIVE NETWORK STREAM</div>', unsafe_allow_html=True)
                gd = df.head(msg_limit).copy()
                gd[['Team Member', 'Range']] = gd['num'].apply(lambda x: pd.Series(get_team_info(x, team_data)))
                gd['Country'] = gd['num'].apply(get_country)
                gd = gd[['dt','cli','num','Country','message','Team Member','Range']].copy()
                gd.columns = ['Time','App','Number','Country','Message','Team Member','Range']
                gd['Time'] = pd.to_datetime(gd['Time'])
                gd = gd.sort_values('Time', ascending=False)
                gd['Time'] = gd['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                st.dataframe(gd.style.apply(highlight_team, axis=1),
                             use_container_width=True, height=700, hide_index=True, column_config=col_cfg)

    sr = requests.get(GOOGLE_SCRIPT_URL, timeout=10)
    if sr.status_code == 200:
        sd = sr.json()
        if sd:
            sdf = pd.DataFrame(sd)
            if filter_cli: sdf = sdf[sdf['App'].astype(str).str.contains(filter_cli, case=False, na=False)]
            if filter_num: sdf = sdf[sdf['Number'].astype(str).str.contains(filter_num, na=False)]
            if filter_msg: sdf = sdf[sdf['Message'].astype(str).str.contains(filter_msg, case=False, na=False)]
            with history_placeholder.container():
                st.markdown(f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;'
                            f'color:#5a7aa0;margin-bottom:12px"><span style="color:#00aaff;font-weight:700">'
                            f'{len(sdf)}</span> permanent records</div>', unsafe_allow_html=True)
                if not sdf.empty:
                    try:
                        sdf['Time'] = pd.to_datetime(sdf['Time'])
                        sdf = sdf.sort_values('Time', ascending=False)
                        sdf['Time'] = sdf['Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
                    except: pass
                    sdf[['Team Member', 'Range']] = sdf['Number'].apply(
                        lambda x: pd.Series(get_team_info(x, team_data)))
                    st.dataframe(sdf.style.apply(highlight_team, axis=1),
                                 use_container_width=True, height=600, hide_index=True, column_config=col_cfg)

    # Infinite loop ki bajaye script ke end par sleep aur rerun karein
    time.sleep(15)
    st.rerun()

except Exception as e:
    time.sleep(5)
    st.rerun()
