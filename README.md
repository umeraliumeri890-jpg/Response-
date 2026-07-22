# ⚡ UTS HUNTERS ENTERPRISE

Enterprise-grade **Streamlit** SOC dashboard that pulls live OTP logs from multiple SMS APIs, merges them, enriches with team + country intelligence, and presents a premium cyber operations UI.

| Target | Value |
|--------|--------|
| Platform | GitHub · Streamlit Community Cloud |
| Runtime | Python **3.12** |
| Entry point | `app.py` |
| Version | 2.0.0 |

---

## Features

- **Activation-code auth** via Google Apps Script registry (`check_code`, `generate_codes`, `deactivate_code`, `list_codes`)
- **Server-side device fingerprint** (User-Agent + Accept-Language + Accept-Encoding → SHA256)
- **Admin panel** restricted to operator `Umer Ali`
- **Dual API ingest** — Lamix + Purple with `ThreadPoolExecutor`, failover, retries, connection pooling
- **Merge engine** — normalized columns, newest-first sort, automatic dedupe
- **Auto refresh** via `streamlit-autorefresh` (5 / 10 / 15 / 30 / 60s / OFF) — **no** `time.sleep` loops
- **CSV team lookup** (`Numbers_Export.csv`) with ignored members `UTS_Umer1`, `UTS_Khadija`
- **Country geolocation** with `phonenumbers` + cached lookups
- **KPI cards**, animated Top-3 CLI glass cards, API health panel
- **Plotly analytics** — timeline, pie/bar, heatmap, hourly/daily trends, API compare, team performance, geo map
- **Sidebar navigation** (option-menu) — Dashboard, Live Monitor, Analytics, Countries, CLI, Search, Exports, Settings, Admin
- **Advanced search** — CLI / country / number / message / date / API / member + regex / contains / starts / ends
- **AgGrid tables** — sort, filter, freeze, pagination, dark theme
- **Exports** — CSV, Excel, PDF, JSON (current filter or full data)
- **Toasts** — API down, new OTP, high traffic
- **Themes** — Cyber · Dark · Blue · Purple · Light
- **Secrets-only config** — nothing sensitive hard-coded
- **Daily rotating logs** under `logs/`
- Optional **GitHub Actions** syntax/import check

---

## Project structure

```
UTS-HUNTERS/
├── app.py                 # Streamlit entry
├── api.py                 # Lamix + Purple clients, merge, cache
├── auth.py                # Activation + device lock + session
├── dashboard.py           # Pages, KPIs, AgGrid, exports UI
├── analytics.py           # Aggregations
├── admin.py               # Admin-only code registry UI
├── charts.py              # Plotly charts
├── utils.py               # Fingerprint, team CSV, country, export helpers
├── config.py              # Settings + themes
├── styles.css             # External cyber SOC CSS (no inline stylesheet)
├── requirements.txt
├── README.md
├── Numbers_Export.csv     # Sample team map (replace with yours)
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── .github/workflows/
│   └── streamlit-check.yml
├── assets/
│   ├── logo.png
│   └── background.png
├── logs/
└── data/
```

---

## Quick start (local)

### 1. Clone / unzip

```bash
cd UTS-HUNTERS
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml`:

```toml
LAMIX_URL = "http://51.77.216.195/crapi/lamix/viewstats"
LAMIX_TOKEN = "YOUR_LAMIX_TOKEN"

PURPLE_URL = "http://137.74.1.203/crapi/reseller/mdr.php"
PURPLE_TOKEN = "YOUR_PURPLE_TOKEN"

REGISTRY_URL = "https://script.google.com/macros/s/YOUR_DEPLOYMENT_ID/exec"
ADMIN_KEY = "YOUR_ADMIN_KEY"
```

> ⚠️ Never commit `secrets.toml`. It is git-ignored.

### 3. Team CSV

Place your export at project root as `Numbers_Export.csv`:

| Phone Number | Status | Range |
|--------------|--------|-------|
| 923001112233 | Allocated: Ahmed Khan | PK-Mobile-A |
| 447700900123 | Allocated: John Smith | UK-Mobile |

Rows whose member name is `UTS_Umer1` or `UTS_Khadija` are ignored.

### 4. Run

```bash
streamlit run app.py
```

Open the local URL, enter an activation code from your registry.

---

## Streamlit Community Cloud

1. Push this repo to **GitHub** (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select the repo, branch, and main file: **`app.py`**.
4. Python version: **3.12**.
5. **Settings → Secrets** — paste the same TOML as `secrets.toml.example` (with real values).
6. Deploy.

### Secrets checklist (Cloud)

| Key | Required |
|-----|----------|
| `LAMIX_URL` | ✅ |
| `LAMIX_TOKEN` | ✅ |
| `PURPLE_URL` | ✅ |
| `PURPLE_TOKEN` | ✅ |
| `REGISTRY_URL` | ✅ |
| `ADMIN_KEY` | ✅ (admin actions) |

---

## GitHub

```bash
git init
git add .
git commit -m "Initial commit: UTS Hunters Enterprise"
git branch -M main
git remote add origin https://github.com/<you>/UTS-HUNTERS.git
git push -u origin main
```

Included workflow: `.github/workflows/streamlit-check.yml` compiles modules on push/PR.

---

## Authentication flow

1. User enters activation code.
2. App builds device fingerprint: `SHA256(User-Agent | Accept-Language | Accept-Encoding)`.
3. `POST` registry `check_code` with `{code, fp}`.
4. On success → session (`authenticated`, `operator_name`, `auth_code`).
5. Inactivity timeout (default 60 min) forces re-login.
6. Logout clears session keys.

**Admin:** if `operator_name == "Umer Ali"`, Admin page is unlocked.

---

## APIs

### Lamix

```
GET {LAMIX_URL}?token=...&records=400
```

Normalized fields: `datetime`, `number`, `cli`, `message` → panel `LAMIX`.

### Purple

```
GET {PURPLE_URL}?token=...&fromdate=...&todate=...&records=2000
```

Normalized fields → panel `PURPLE`.

### Merge

- Common columns · parse datetime · drop bad rows · dedupe · sort **descending**
- If one API fails, the other still feeds the dashboard (failover)

---

## Sidebar pages

| Page | Purpose |
|------|---------|
| Dashboard | KPIs, Top CLI, API health, overview charts |
| Live Monitor | Target CLI tracker + global AgGrid stream |
| Analytics | Full Plotly suite |
| Countries | Pie, bar, geo map |
| CLI Analysis | Rankings + breakdown |
| Search | Multi-filter + regex + favorites + history |
| Exports | CSV / Excel / PDF / JSON |
| Settings | Theme, refresh, timezone, page size, system info |
| Admin | Code generate / list / deactivate |

---

## Auto refresh

Sidebar control:

`5 sec · 10 sec · 15 sec · 30 sec · 60 sec · OFF`

Uses **`streamlit-autorefresh`** only — no blocking `time.sleep()` rerun loops.

---

## Performance notes

- `requests.Session()` + `HTTPAdapter` connection pool
- `urllib3.Retry` with backoff
- `ThreadPoolExecutor` dual fetch
- `@st.cache_resource` for HTTP session
- `@st.cache_data` for live frame (TTL) + country + team CSV
- Manual **Force refresh** busts cache

---

## Themes

Cyber (default) palette:

```
#00D4FF  #6D5DFC  #0B1224  #081224  #030712
```

Fonts: **Orbitron** + **Inter** (+ JetBrains Mono for mono UI). Glassmorphism + glow in `styles.css`.

---

## Logging

Daily rotating file: `logs/app.log`

Events: login success/deny, API failures, admin actions, page errors.

---

## Screenshots

After deploy, capture:

1. Login gate  
2. Dashboard KPIs + Top CLI  
3. Live Monitor AgGrid  
4. Analytics heatmap  
5. Admin code manager  

Drop images into `assets/` and link them here if desired.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Login always fails | Verify `REGISTRY_URL` + Apps Script deployment access |
| Empty tables | Check API tokens / network egress on Cloud |
| AgGrid missing | `pip install streamlit-aggrid` |
| PDF export is `.txt` | Ensure `reportlab` installed |
| Team members blank | Confirm CSV headers: `Phone Number`, `Status`, `Range` |
| Secrets warning banner | Fill all keys in Cloud secrets / local `secrets.toml` |

---

## Security

- No tokens in source code
- Device-locked activation codes
- Admin key only server-side via secrets
- `.gitignore` blocks `secrets.toml`, venvs, logs

---

## License

Private / internal — UTS Systems. All rights reserved.

---

**UTS HUNTERS ENTERPRISE** — multi-API OTP intelligence for operators.
