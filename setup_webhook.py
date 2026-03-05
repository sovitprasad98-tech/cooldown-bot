"""
Run this ONCE after deploying to Vercel to set the webhook.
Usage: python setup_webhook.py
"""

import requests

BOT_TOKEN = input("Enter your Bot Token: ").strip()
VERCEL_URL = input("Enter your Vercel URL (e.g. https://your-app.vercel.app): ").strip()

WEBHOOK_URL = f"{VERCEL_URL}/api/webhook"

resp = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
    json={"url": WEBHOOK_URL, "allowed_updates": ["message", "callback_query"]}
)

data = resp.json()
if data.get("ok"):
    print(f"\n✅ Webhook set successfully!")
    print(f"   URL: {WEBHOOK_URL}")
else:
    print(f"\n❌ Failed: {data}")

# Verify
info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo").json()
print(f"\n📋 Webhook Info: {info.get('result', {})}")
