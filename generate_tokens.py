import secrets
import json
from datetime import datetime, timedelta

# ================================
# YAHAN APNE USERS LIKHO
# ================================
users = [
    "Bilal",
    "Kamran",
    "Asad",
    # Jitne chahiye
]

EXPIRY_DAYS = 30
YOUR_APP_URL = "https://YOUR-APP.streamlit.app"  # Apna URL yahan
# ================================

tokens = {}
print("\n" + "="*65)
print("   TOKENS GENERATED — Har bande ko SIRF uska link bhejo")
print("="*65)

for user in users:
    token = secrets.token_urlsafe(20)
    tokens[token] = {
        "name": user,
        "expires": (datetime.now() + timedelta(days=EXPIRY_DAYS)).strftime("%Y-%m-%d"),
        "locked_ip": None,
        "active": True
    }
    print(f"\n  👤 {user}")
    print(f"  🔗 {YOUR_APP_URL}/?token={token}")

with open("tokens.json", "w") as f:
    json.dump(tokens, f, indent=2)

print("\n" + "="*65)
print("  ✅ tokens.json updated!")
print("="*65 + "\n")
