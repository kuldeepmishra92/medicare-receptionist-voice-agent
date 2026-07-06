"""
Keep-Alive Ping Script — Prevents Hugging Face Spaces from going to sleep
Run standalone or as a service: python keep_alive.py
"""
import time
import requests
import os

# Set target URL (Defaults to local Docker port 7860 or your HF Space URL)
TARGET_URL = os.getenv("HF_SPACE_URL") or os.getenv("SPACE_HOST") or "http://localhost:7860/health"
if not TARGET_URL.startswith("http"):
    TARGET_URL = f"https://{TARGET_URL}/health"

PING_INTERVAL_SECONDS = 300  # Ping every 5 minutes

print(f"🚀 Keep-Alive Ping Service initialized.")
print(f"🎯 Target URL: {TARGET_URL}")
print(f"⏱️ Interval: Every {PING_INTERVAL_SECONDS} seconds (5 minutes)\n")

while True:
    try:
        response = requests.get(TARGET_URL, timeout=15)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] 🟢 Ping Success | Status: {response.status_code} | Target: {TARGET_URL}")
    except Exception as err:
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] ⚠️ Ping Exception: {err}")

    time.sleep(PING_INTERVAL_SECONDS)
