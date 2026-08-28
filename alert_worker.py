def fetch_lamix(session: requests.Session, cfg: dict[str, Any]) -> list[dict]:
    """Fetch messages from Lamix API v1."""
    if not cfg["lamix_url"] or not cfg["lamix_token"]:
        log("lamix_skip", reason="missing url/token")
        return []
    
    # ✅ New API: Use Bearer token in header
    headers = {
        "Authorization": f"Bearer {cfg['lamix_token']}",
        "Accept": "application/json",
    }
    
    # ✅ New API: Use `limit` instead of `records`
    params = {
        "limit": min(cfg.get("lamix_records", 500), 1000),
    }
    
    # Optional: Add date filter
    from_date = (datetime.now() - timedelta(days=cfg.get("purple_lookback_days", 30))).strftime("%Y-%m-%dT00:00:00Z")
    params["from"] = from_date
    
    try:
        r = session.get(
            cfg["lamix_url"],
            params=params,
            headers=headers,
            timeout=cfg["api_timeout"],
        )
        if r.status_code != 200:
            log("lamix_fail", status=r.status_code, body=r.text[:200])
            return []
            
        payload = r.json()
        
        # ✅ New API: Response has `records` array
        raw = payload.get("records", []) if isinstance(payload, dict) else payload
        
        # Handle nested records
        if isinstance(raw, dict) and "records" in raw:
            raw = raw.get("records", [])
            
        rows = []
        for item in raw or []:
            if isinstance(item, dict):
                n = normalize_item(item, "LAMIX")
                if n:
                    rows.append(n)
        log("lamix_ok", records=len(rows))
        return rows
    except Exception as exc:
        log("lamix_error", error=str(exc))
        return []
