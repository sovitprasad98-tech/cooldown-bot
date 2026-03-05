# 🤖 CooldownBot — Setup Guide

## Project Structure
```
cooldown-bot/
├── api/
│   └── webhook.py       ← Main bot + Flask server
├── admin_panel.html     ← Open in browser (no server needed)
├── requirements.txt
├── vercel.json
├── setup_webhook.py     ← Run once after deploy
└── README.md
```

---

## Step 1 — Firebase Service Account Setup

> **Important:** Bot ke liye Firebase Admin SDK chahiye — ye Web Config se alag hai!

1. [Firebase Console](https://console.firebase.google.com) → Apna project open karo
2. **Project Settings** → **Service Accounts** tab
3. **"Generate new private key"** button dabao
4. JSON file download hogi — uska content copy karo

---

## Step 2 — GitHub pe Upload Karo

```bash
git init
git add .
git commit -m "Initial CooldownBot"
git remote add origin https://github.com/YOUR_USERNAME/cooldown-bot.git
git push -u origin main
```

---

## Step 3 — Vercel Deploy

1. [vercel.com](https://vercel.com) pe jao → Import GitHub repo
2. **Environment Variables** add karo:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | BotFather se mila token |
| `FIREBASE_CREDENTIALS` | Firebase service account JSON (poora JSON paste karo) |
| `ADMIN_IDS` | Tera Telegram user ID (e.g. `123456789`) |
| `WEBHOOK_SECRET` | Koi bhi secret string (e.g. `mysecret123`) |

3. **Deploy** karo

---

## Step 4 — Webhook Set Karo

Deploy ke baad:

```bash
python setup_webhook.py
```

Ya directly browser mein:
```
https://api.telegram.org/botYOUR_TOKEN/setWebhook?url=https://YOUR-APP.vercel.app/api/webhook
```

---

## Step 5 — Bot ko Group Admin Banao

Ye **ZARURI** hai! Bina admin rights ke bot restrict nahi kar sakta:
1. Apne Telegram group mein jao
2. Bot ko **Admin** banao
3. Permissions: **Restrict Members** ✅ (minimum required)

---

## Step 6 — Admin Panel Use Karo

`admin_panel.html` seedha browser mein open karo — koi hosting ki zarurat nahi!

**Login fields:**
- Firebase DB URL: `https://digit-product-default-rtdb.firebaseio.com`
- Admin Secret: Jo `WEBHOOK_SECRET` tune set kiya
- Firebase API Key: Already filled hai

---

## Commands

### User Commands
| Command | Description |
|---|---|
| `/start` | Bot se milna, status dekho |
| `/setcooldown <sec>` | Apna cooldown set karo (private chat mein) |
| `/mystatus` | Current plan aur cooldown |
| `/help` | Sab commands |

### Admin Commands
| Command | Description |
|---|---|
| `/stats` | Bot statistics |
| `/setglobalcooldown <sec>` | Default cooldown change |
| `/addpremium <user_id>` | Premium do |
| `/removepremium <user_id>` | Premium hatao |
| `/addadmin <user_id>` | Admin banao |
| `/banuser <user_id>` | Ban karo |
| `/unbanuser <user_id>` | Unban karo |
| `/broadcast <msg>` | Sab users ko message |

---

## Cooldown Limits

| Plan | Min | Max |
|---|---|---|
| 👤 Free | 30s | 300s |
| 💎 Premium | 5s | 3600s |
| 👑 Admin | No limit | No limit |

---

## How It Works (Technical)

1. User group mein message bhejta hai
2. Bot `restrictChatMember` call karta hai Telegram API pe
3. `until_date = now + cooldown_seconds` set hota hai
4. **Telegram khud** user ko restrict karta hai — koi bypass nahi!
5. Timer khatam hone pe Telegram automatically unrestrict kar deta hai
6. Bot ko koi background job run nahi karna padta (serverless friendly ✅)

---

## Firebase Structure

```
digit-product-default-rtdb/
├── users/
│   └── {user_id}/
│       ├── name: "Sovit"
│       ├── username: "SovitX"
│       ├── cooldown: 60
│       ├── is_premium: false
│       ├── is_banned: false
│       └── last_message: 1709123456
├── settings/
│   ├── default_cooldown: 60
│   ├── free_min: 30
│   ├── free_max: 300
│   ├── premium_min: 5
│   ├── premium_max: 3600
│   ├── bot_active: true
│   └── admin_bypass: true
├── admins/
│   └── {user_id}: true
└── logs/
    └── {auto_id}/
        ├── user_id: "123456"
        ├── action: "set_cooldown"
        ├── extra: "45"
        └── timestamp: 1709123456
```
