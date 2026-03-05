import os
import json
import time
import firebase_admin
from firebase_admin import credentials, db
import telebot
from telebot.types import ChatPermissions
from flask import Flask, request, jsonify

# ─────────────────────────────────────────────────
# ENV VARIABLES (Set these in Vercel Dashboard)
# ─────────────────────────────────────────────────
BOT_TOKEN       = os.environ.get("BOT_TOKEN", "")
FIREBASE_CREDS  = os.environ.get("FIREBASE_CREDENTIALS", "{}")  # JSON string of service account
FIREBASE_DB_URL = "https://digit-product-default-rtdb.firebaseio.com"
ADMIN_IDS       = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
WEBHOOK_SECRET  = os.environ.get("WEBHOOK_SECRET", "mysecret123")  # optional security token

# ─────────────────────────────────────────────────
# FIREBASE INIT
# ─────────────────────────────────────────────────
if not firebase_admin._apps:
    try:
        cred_dict = json.loads(FIREBASE_CREDS)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
    except Exception as e:
        print(f"Firebase init error: {e}")

# ─────────────────────────────────────────────────
# BOT & FLASK INIT
# ─────────────────────────────────────────────────
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = Flask(__name__)

# ─────────────────────────────────────────────────
# FIREBASE HELPERS
# ─────────────────────────────────────────────────
def get_user(uid):
    try:
        return db.reference(f"/users/{uid}").get() or {}
    except:
        return {}

def update_user(uid, data):
    try:
        db.reference(f"/users/{uid}").update(data)
    except Exception as e:
        print(f"Firebase update error: {e}")

def get_settings():
    try:
        return db.reference("/settings").get() or {}
    except:
        return {}

def update_settings(data):
    try:
        db.reference("/settings").update(data)
    except Exception as e:
        print(f"Firebase settings error: {e}")

def is_bot_admin(uid):
    if uid in ADMIN_IDS:
        return True
    try:
        return db.reference(f"/admins/{uid}").get() is True
    except:
        return False

def is_premium(uid):
    try:
        return db.reference(f"/users/{uid}/is_premium").get() is True
    except:
        return False

def get_user_cooldown(uid):
    user = get_user(uid)
    if "cooldown" in user:
        return int(user["cooldown"])
    settings = get_settings()
    return int(settings.get("default_cooldown", 60))

def log_activity(uid, action, extra=""):
    try:
        log_ref = db.reference("/logs").push({
            "user_id": uid,
            "action": action,
            "extra": extra,
            "timestamp": int(time.time())
        })
    except:
        pass

def get_stats():
    try:
        users = db.reference("/users").get() or {}
        total = len(users)
        premium_count = sum(1 for u in users.values() if isinstance(u, dict) and u.get("is_premium"))
        settings = get_settings()
        return {
            "total_users": total,
            "premium_users": premium_count,
            "default_cooldown": settings.get("default_cooldown", 60),
            "bot_active": True
        }
    except:
        return {}

# ─────────────────────────────────────────────────
# HELPER: Check if user is group admin/creator
# ─────────────────────────────────────────────────
def is_group_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# ─────────────────────────────────────────────────
# COMMAND: /start
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    update_user(uid, {
        "username": message.from_user.username or "",
        "name": message.from_user.first_name or "User",
        "joined": int(time.time())
    })

    if message.chat.type == "private":
        premium = is_premium(uid)
        cooldown = get_user_cooldown(uid)
        badge = "💎 Premium" if premium else "👤 Free"
        text = (
            f"🤖 *CooldownBot — Welcome!*\n\n"
            f"Haan! Main tera *Group Cooldown Manager* hoon.\n"
            f"Group mein har message ke baad main teri baat rokta hoon thodi der ke liye — "
            f"taaki sab fair rahe!\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Tera Account*\n"
            f"├ Plan: {badge}\n"
            f"├ Cooldown: *{cooldown} seconds*\n"
            f"└ Limit change: /setcooldown\n\n"
            f"📋 *Commands*\n"
            f"/setcooldown `<seconds>` — Apna cooldown set karo\n"
            f"/mystatus — Tera current status dekho\n"
            f"/help — Sab commands dekho\n\n"
            f"{'💎 *Premium Benefits:* 5s–3600s cooldown range!' if not premium else '💎 *Premium Active!* 5s–3600s range available.'}"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    else:
        bot.reply_to(message, "👋 Main active hoon is group mein! Private chat mein /start karo settings ke liye.")

# ─────────────────────────────────────────────────
# COMMAND: /help
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["help"])
def cmd_help(message):
    uid = message.from_user.id
    admin_section = ""
    if is_bot_admin(uid):
        admin_section = (
            "\n👑 *Admin Commands*\n"
            "/setglobalcooldown `<sec>` — Default cooldown change\n"
            "/addpremium `<user_id>` — Premium do kisi ko\n"
            "/removepremium `<user_id>` — Premium hatao\n"
            "/addadmin `<user_id>` — Admin banao\n"
            "/broadcast `<msg>` — Sab users ko message\n"
            "/stats — Bot ke stats dekho\n"
            "/banuser `<user_id>` — User ko ban karo\n"
            "/unbanuser `<user_id>` — Ban hatao\n"
        )

    text = (
        "📋 *CooldownBot — Help*\n\n"
        "👤 *User Commands*\n"
        "/start — Bot start karo\n"
        "/setcooldown `<seconds>` — Apna cooldown set karo\n"
        "  • Free: 30–300 sec\n"
        "  • Premium 💎: 5–3600 sec\n"
        "/mystatus — Current cooldown aur plan dekho\n"
        "/help — Ye message\n"
        + admin_section
    )
    bot.send_message(
        message.chat.id if message.chat.type == "private" else message.from_user.id,
        text, parse_mode="Markdown"
    )

# ─────────────────────────────────────────────────
# COMMAND: /setcooldown
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["setcooldown"])
def cmd_setcooldown(message):
    if message.chat.type != "private":
        bot.reply_to(message, "⚠️ Ye command sirf *private chat* mein use karo!", parse_mode="Markdown")
        return

    uid = message.from_user.id
    parts = message.text.strip().split()

    if len(parts) != 2 or not parts[1].isdigit():
        bot.send_message(
            message.chat.id,
            "❌ *Galat Format!*\n\nSahi use:\n`/setcooldown 45`\n\nExample: 45 seconds ke liye",
            parse_mode="Markdown"
        )
        return

    seconds = int(parts[1])
    premium = is_premium(uid) or is_bot_admin(uid)
    min_cd = 5 if premium else 30
    max_cd = 3600 if premium else 300

    if seconds < min_cd or seconds > max_cd:
        msg = (
            f"❌ *Range Error!*\n\n"
            f"Teri limit: *{min_cd}s – {max_cd}s*\n\n"
        )
        if not premium:
            msg += "💎 *Premium* lete ho toh 5s–3600s tak set kar sakte ho!"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        return

    update_user(uid, {
        "cooldown": seconds,
        "username": message.from_user.username or "",
        "name": message.from_user.first_name or "User"
    })
    log_activity(uid, "set_cooldown", str(seconds))

    bot.send_message(
        message.chat.id,
        f"✅ *Cooldown Set!*\n\n⏱ Ab tera cooldown: *{seconds} seconds*\n\nGroup mein har message ke baad {seconds} sec wait karna padega.",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────────
# COMMAND: /mystatus
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["mystatus"])
def cmd_mystatus(message):
    uid = message.from_user.id
    cooldown = get_user_cooldown(uid)
    premium = is_premium(uid)
    admin = is_bot_admin(uid)

    badge = "👑 Admin" if admin else ("💎 Premium" if premium else "👤 Free")
    range_text = "5s – 3600s" if (premium or admin) else "30s – 300s"

    text = (
        f"📊 *Tera Status*\n\n"
        f"├ Plan: *{badge}*\n"
        f"├ Cooldown: *{cooldown} seconds*\n"
        f"├ Allowed Range: {range_text}\n"
        f"└ ID: `{uid}`\n\n"
        f"Change karne ke liye: /setcooldown `<seconds>`"
    )

    target = message.chat.id if message.chat.type == "private" else uid
    try:
        bot.send_message(target, text, parse_mode="Markdown")
    except:
        bot.reply_to(message, text, parse_mode="Markdown")

# ─────────────────────────────────────────────────
# ADMIN: /stats
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    if not is_bot_admin(message.from_user.id):
        return
    s = get_stats()
    settings = get_settings()
    text = (
        f"📊 *Bot Statistics*\n\n"
        f"👥 Total Users: *{s.get('total_users', 0)}*\n"
        f"💎 Premium Users: *{s.get('premium_users', 0)}*\n"
        f"⏱ Default Cooldown: *{settings.get('default_cooldown', 60)}s*\n"
        f"🤖 Bot Status: *Active ✅*"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

# ─────────────────────────────────────────────────
# ADMIN: /setglobalcooldown
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["setglobalcooldown"])
def cmd_set_global_cooldown(message):
    if not is_bot_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.reply_to(message, "Use: `/setglobalcooldown <seconds>`", parse_mode="Markdown")
        return
    seconds = int(parts[1])
    update_settings({"default_cooldown": seconds})
    log_activity(message.from_user.id, "set_global_cooldown", str(seconds))
    bot.reply_to(message, f"✅ Global cooldown set: *{seconds}s*", parse_mode="Markdown")

# ─────────────────────────────────────────────────
# ADMIN: /addpremium /removepremium
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["addpremium"])
def cmd_add_premium(message):
    if not is_bot_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "Use: `/addpremium <user_id>`", parse_mode="Markdown")
        return
    target_id = parts[1]
    update_user(target_id, {"is_premium": True})
    log_activity(message.from_user.id, "add_premium", target_id)
    bot.reply_to(message, f"✅ User `{target_id}` ko *Premium* diya gaya! 💎", parse_mode="Markdown")
    try:
        bot.send_message(int(target_id),
            "🎉 *Congratulations!*\n\nTumhe *Premium* plan mila hai!\n\n💎 Ab 5s–3600s cooldown set kar sakte ho.",
            parse_mode="Markdown")
    except:
        pass

@bot.message_handler(commands=["removepremium"])
def cmd_remove_premium(message):
    if not is_bot_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "Use: `/removepremium <user_id>`", parse_mode="Markdown")
        return
    target_id = parts[1]
    update_user(target_id, {"is_premium": False})
    log_activity(message.from_user.id, "remove_premium", target_id)
    bot.reply_to(message, f"✅ User `{target_id}` ka Premium remove kiya gaya.", parse_mode="Markdown")

# ─────────────────────────────────────────────────
# ADMIN: /addadmin
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["addadmin"])
def cmd_add_admin(message):
    if not is_bot_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "Use: `/addadmin <user_id>`", parse_mode="Markdown")
        return
    target_id = parts[1]
    try:
        db.reference(f"/admins/{target_id}").set(True)
        bot.reply_to(message, f"✅ User `{target_id}` ko *Admin* banaya gaya! 👑", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ─────────────────────────────────────────────────
# ADMIN: /banuser /unbanuser
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["banuser"])
def cmd_ban_user(message):
    if not is_bot_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "Use: `/banuser <user_id>`", parse_mode="Markdown")
        return
    target_id = parts[1]
    update_user(target_id, {"is_banned": True})
    log_activity(message.from_user.id, "ban_user", target_id)
    bot.reply_to(message, f"🚫 User `{target_id}` ko ban kiya gaya.", parse_mode="Markdown")

@bot.message_handler(commands=["unbanuser"])
def cmd_unban_user(message):
    if not is_bot_admin(message.from_user.id):
        return
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "Use: `/unbanuser <user_id>`", parse_mode="Markdown")
        return
    target_id = parts[1]
    update_user(target_id, {"is_banned": False})
    log_activity(message.from_user.id, "unban_user", target_id)
    bot.reply_to(message, f"✅ User `{target_id}` ka ban hata diya gaya.", parse_mode="Markdown")

# ─────────────────────────────────────────────────
# ADMIN: /broadcast
# ─────────────────────────────────────────────────
@bot.message_handler(commands=["broadcast"])
def cmd_broadcast(message):
    if not is_bot_admin(message.from_user.id):
        return
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        bot.reply_to(message, "Use: `/broadcast <message>`", parse_mode="Markdown")
        return
    msg_text = parts[1]
    try:
        users = db.reference("/users").get() or {}
        sent, failed = 0, 0
        for uid in users:
            try:
                bot.send_message(int(uid), f"📢 *Broadcast:*\n\n{msg_text}", parse_mode="Markdown")
                sent += 1
                time.sleep(0.05)
            except:
                failed += 1
        bot.reply_to(message, f"✅ Broadcast done!\n✉️ Sent: {sent}\n❌ Failed: {failed}")
        log_activity(message.from_user.id, "broadcast", msg_text[:50])
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# ─────────────────────────────────────────────────
# GROUP MESSAGE HANDLER — CORE LOGIC
# ─────────────────────────────────────────────────
@bot.message_handler(
    func=lambda msg: msg.chat.type in ["group", "supergroup"],
    content_types=["text", "photo", "video", "audio", "voice", "sticker", "document", "animation"]
)
def group_handler(message):
    uid = message.from_user.id
    chat_id = message.chat.id

    # Skip commands
    if message.text and message.text.startswith("/"):
        return

    # Skip group admins & creator
    if is_group_admin(chat_id, uid):
        return

    # Skip bot admins
    if is_bot_admin(uid):
        return

    # Skip banned users (just block, no restrict)
    user_data = get_user(uid)
    if user_data.get("is_banned"):
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass
        return

    # Get this user's cooldown
    cooldown = get_user_cooldown(uid)

    # Save user info + last message time
    update_user(uid, {
        "username": message.from_user.username or "",
        "name": message.from_user.first_name or "User",
        "last_message": int(time.time()),
        "last_group": str(chat_id)
    })

    # Restrict user using Telegram's until_date — auto unrestrict after cooldown
    until_date = int(time.time()) + cooldown

    try:
        bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=uid,
            until_date=until_date,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
        )

        name = message.from_user.first_name or "User"
        username = f"@{message.from_user.username}" if message.from_user.username else name

        warn_text = (
            f"⏳ {username} — *{cooldown} seconds* baad phir message kar sakte ho!"
        )
        warn_msg = bot.send_message(chat_id, warn_text, parse_mode="Markdown")
        log_activity(uid, "cooldown_applied", str(cooldown))

    except telebot.apihelper.ApiTelegramException as e:
        error_text = str(e)
        if "not enough rights" in error_text or "CHAT_ADMIN_REQUIRED" in error_text:
            # Bot doesn't have admin rights
            bot.send_message(
                chat_id,
                "⚠️ *Mujhe Admin rights chahiye!*\n\nPlease mujhe group admin banao taaki main cooldown enforce kar sakoon.",
                parse_mode="Markdown"
            )
        else:
            print(f"Restrict error: {e}")
    except Exception as e:
        print(f"Group handler error: {e}")

# ─────────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────────
@app.route("/api/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        try:
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            print(f"Webhook processing error: {e}")
        return "", 200
    return "", 403

@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Admin panel API — returns bot stats"""
    secret = request.headers.get("X-Admin-Secret", "")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_stats())

@app.route("/api/users", methods=["GET"])
def api_users():
    """Admin panel API — returns all users"""
    secret = request.headers.get("X-Admin-Secret", "")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        users = db.reference("/users").get() or {}
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    """Admin panel API — get/update settings"""
    secret = request.headers.get("X-Admin-Secret", "")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    if request.method == "GET":
        return jsonify(get_settings())
    if request.method == "POST":
        data = request.get_json()
        update_settings(data)
        return jsonify({"success": True})

@app.route("/api/user/update", methods=["POST"])
def api_user_update():
    """Admin panel API — update user"""
    secret = request.headers.get("X-Admin-Secret", "")
    if secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    uid = data.get("user_id")
    update = data.get("update", {})
    if not uid:
        return jsonify({"error": "user_id required"}), 400
    update_user(uid, update)
    return jsonify({"success": True})

@app.route("/", methods=["GET"])
def index():
    return "🤖 CooldownBot is Running!", 200

# ─────────────────────────────────────────────────
# VERCEL ENTRY POINT
# ─────────────────────────────────────────────────
# Vercel will use 'app' as the WSGI handler
