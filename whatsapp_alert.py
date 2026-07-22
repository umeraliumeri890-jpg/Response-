def process_otp_alerts(df: pd.DataFrame, *, force: bool = False) -> list[dict[str, Any]]:
    """
    Run one evaluation tick against the live merged frame.
    Sends alerts EVERY 5 MINUTES for TOP 1 CLI with OTP activity.
    """
    if not _ALERT_PROCESS_LOCK.acquire(blocking=False):
        return []

    try:
        cfg = _alert_config()
        if not cfg["enabled"] and not force:
            return []

        now_ts = time.time()
        last = float(st.session_state.get("wa_last_scan_ts", 0) or 0)
        if not force and (now_ts - last) < 10:
            return []
        st.session_state["wa_last_scan_ts"] = now_ts

        try:
            hits = evaluate_cli_windows(df, window_min=cfg["window_min"], threshold=1)
        except Exception as exc:
            log_event("wa_eval_error", str(exc))
            return []

        fired: list[dict[str, Any]] = []

        # ONLY TOP 1 CLI - highest OTP count
        top_hits = hits[:1]  # Sirf pehla (top 1)

        for hit in top_hits:
            cli = hit["cli"]
            total = hit["total"]

            cooldown_sec = 300  # 5 minutes fixed

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

            msg_hash = hashlib.sha256(msg.encode("utf-8")).hexdigest()
            last_hash = _alert_state.get("last_hash", "")
            last_sent = _alert_state.get("last_sent", 0)

            if msg_hash == last_hash and (now_ts - last_sent) < 30:
                log_event("wa_alert_skipped", "duplicate message", cli=cli, hash=msg_hash[:8])
                continue

            meta = {"cli": cli, "panel": hit["panel"], "total": hit["total"], "country": hit["main_country"]}

            _arm_cooldown(cli, cooldown_sec, now_ts)
            _alert_state["last_hash"] = msg_hash
            _alert_state["last_sent"] = now_ts
            _save_alert_state(_alert_state)

            send_whatsapp_alert_async(msg, meta=meta)

            fired.append({**meta, "message": msg})
            log_event("wa_alert_triggered", "OTP traffic", **meta)

            try:
                st.toast(f"🚨 WA alert · {cli} · {hit['total']} OTPs (TOP 1)", icon="📱")
            except Exception:
                pass

        if fired:
            st.session_state["wa_last_fired"] = fired
        return fired

    finally:
        _ALERT_PROCESS_LOCK.release()
