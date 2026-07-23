# 24/7 WhatsApp OTP Alerts — Fix Guide

## Root cause (why pings failed)

Streamlit **only runs Python** (`app.py` → `process_otp_alerts()`) inside a **live browser WebSocket session**.

| Action | Wakes container? | Runs `process_otp_alerts()`? |
|--------|------------------|------------------------------|
| You open the app in Chrome | Yes | **Yes** |
| GitHub Actions `curl` ping | Sometimes | **No** |
| UptimeRobot HTTP check | Sometimes | **No** |
| Auto-refresh (15s) | Only while tab open | Yes (tab must stay open) |

So keep-alive workflows can never fix background alerts on Streamlit Community Cloud. The dashboard UI and the alert engine must be separated.

## The fix

A **headless worker** runs on GitHub Actions every 5 minutes:

1. Fetches Lamix + Purple OTP data directly
2. Evaluates the same 5-minute TOP-1 CLI window
3. Sends WhatsApp via Green-API
4. Stores cooldown in `data/alert_state.json` (cached between runs)

Files:

- `alert_worker.py` — headless engine (no Streamlit)
- `.github/workflows/otp_alert_worker.yml` — schedule every 5 min
- `whatsapp_alert.py` — still used when a human has the dashboard open (file-based cooldown)
- `config.py` — env-first secrets (works in Actions + Streamlit)
- `auth.py` — `AUTH_DISABLED=true` auto-login for the dashboard

## Deploy steps

### 1. Push code to GitHub

```bash
git add alert_worker.py requirements-worker.txt ALERTS_24x7.md \
  config.py auth.py whatsapp_alert.py \
  data/alert_state.json \
  .github/workflows/otp_alert_worker.yml \
  .github/workflows/keep_alive.yml
git commit -m "fix: 24/7 OTP WhatsApp alerts via headless GitHub worker"
git push origin main
```

Streamlit Cloud will redeploy the dashboard automatically.

### 2. Add GitHub repository secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**

Required:

| Secret | Example |
|--------|---------|
| `LAMIX_TOKEN` | your lamix token |
| `PURPLE_TOKEN` | your purple token |
| `GREENAPI_ID_INSTANCE` | `1101xxxxxxxx` |
| `GREENAPI_API_TOKEN` | green-api token |
| `GREENAPI_GROUP_ID` | `1203630...@g.us` |
| `WHATSAPP_PROVIDER` | `greenapi` |
| `WHATSAPP_ALERTS_ENABLED` | `true` |

Recommended:

| Secret | Value |
|--------|-------|
| `LAMIX_URL` | `http://51.77.216.195/crapi/lamix/viewstats` |
| `PURPLE_URL` | `http://137.74.1.203/crapi/reseller/mdr.php` |
| `GREENAPI_API_URL` | `https://api.green-api.com` |
| `WHATSAPP_THRESHOLD` | `1` |
| `WHATSAPP_WINDOW_MIN` | `5` |
| `WHATSAPP_COOLDOWN_MIN` | `5` |
| `LAMIX_RECORDS` | `400` |
| `PURPLE_RECORDS` | `2000` |
| `PURPLE_LOOKBACK_DAYS` | `30` |

Optional dashboard keep-alive:

| Secret | Value |
|--------|-------|
| `STREAMLIT_APP_URL` | `https://leveluts.streamlit.app/` |

> Use the **same values** you already put in Streamlit Cloud secrets.

### 3. Enable Actions + first manual run

1. Repo → **Actions** → enable workflows if prompted  
2. Open **OTP WhatsApp Alert Worker**  
3. **Run workflow** → set `force = true` once  
4. Confirm WhatsApp receives the alert  
5. Leave schedule on (`*/5 * * * *`)

### 4. Streamlit Cloud secrets (dashboard only)

Keep your existing secrets. Add if missing:

```toml
AUTH_DISABLED = true
WHATSAPP_ALERTS_ENABLED = true
WHATSAPP_THRESHOLD = 1
WHATSAPP_WINDOW_MIN = 5
WHATSAPP_COOLDOWN_MIN = 5
WHATSAPP_PROVIDER = "greenapi"
GREENAPI_ID_INSTANCE = "..."
GREENAPI_API_TOKEN = "..."
GREENAPI_GROUP_ID = "...@g.us"
```

## Verify

```text
Browser CLOSED
→ wait up to ~5–10 min (Actions schedule + OTP window)
→ WhatsApp group gets alert           ✅

Actions → OTP WhatsApp Alert Worker → latest run logs
→ {"msg": "alert_sent", "cli": "..."}  ✅
or {"msg": "no_hits"} if no recent OTP ✅
or {"msg": "cooldown_active"}          ✅
```

## Local test

```bash
export LAMIX_TOKEN=...
export PURPLE_TOKEN=...
export WHATSAPP_PROVIDER=greenapi
export GREENAPI_ID_INSTANCE=...
export GREENAPI_API_TOKEN=...
export GREENAPI_GROUP_ID=...@g.us
python alert_worker.py --force
```

## Cost

| Piece | Cost |
|-------|------|
| GitHub Actions (public repo / free minutes) | Free tier |
| Streamlit Community Cloud | Free |
| Green-API developer | Free tier (check limits) |

## Double alerts (dashboard open)

Streamlit auto `process_otp_alerts()` is **disabled** in `app.py`.
Only GitHub Actions worker sends production alerts.
Settings → Send TEST still works (manual).
Keep the dashboard toggle **OFF**.

## Why only ONE WhatsApp then silence?

Two separate things:

### A) Cooldown (by design)
After `alert_sent`, worker waits `WHATSAPP_COOLDOWN_MIN` (default **5 minutes**).
Next runs log `cooldown_active` and send **nothing**. This prevents spam.
After cooldown ends, a **new** OTP window can alert again.

### B) GitHub schedule not firing (common on free tier)
If Actions list only shows **Manually run** / `workflow_dispatch` and never
**scheduled** / `schedule`, GitHub cron has not started (or is delayed hours).

**Fix — free external cron (recommended backup):**

1. GitHub → Settings → Developer settings → Personal access tokens →
   Fine-grained token (or classic `repo` + `workflow` scope)
2. Create token with access to this repo + Actions read/write
3. Go to https://cron-job.org (free) → Create cronjob:
   - URL: `https://api.github.com/repos/umeraliumeri890-jpg/Response-/dispatches`
   - Schedule: every 5 minutes
   - Request method: **POST**
   - Headers:
     - `Accept: application/vnd.github+json`
     - `Authorization: Bearer YOUR_GITHUB_TOKEN`
     - `X-GitHub-Api-Version: 2022-11-28`
   - Body (JSON):
     ```json
     {"event_type":"otp_alert_tick"}
     ```
4. Save. Actions should show runs with event **`repository_dispatch`** every ~5 min.

Workflow already listens for `repository_dispatch` type `otp_alert_tick`.

## What NOT to expect

- Pinging the Streamlit URL will **never** reliably fire alerts.
- Leaving a phone browser tab open is fragile (sleep, network).
- Streamlit free tier has **no always-on background thread** for your script.
- GitHub `schedule` is **UTC** and often delayed 5–60+ min on free / new repos.
- Look for Event = **`schedule`** or **`repository_dispatch`** (not only manual).
- Green checkmark ≠ WhatsApp every time (`no_hits` / `cooldown_active` are success).

The headless worker is the correct architecture.
