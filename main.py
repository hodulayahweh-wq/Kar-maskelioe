import os
import json
import re
import threading

from flask import Flask, request, jsonify, Response

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ======================
# AYARLAR – ENVIRONMENT YOK
# ======================
DATA_DIR = "data"
PORT = int(os.environ.get("PORT", 10000))  # Render otomatik verir – DOKUNMA!

BOT_TOKEN = "7127783002:AAHYAQfkVgEXOzMSz5L99wqa_NsmOm8Q5rU"  # ←←← KENDİ BOT TOKEN'INI BURAYA KOY

ADMIN_ID = 8258235296
CHANNEL = "@lordsystemv3"

os.makedirs(DATA_DIR, exist_ok=True)

# ======================
# FLASK – Render health check + port için ZORUNLU
# ======================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot aktif – LORD FREE", 200

@app.route("/health")
def health():
    return "OK", 200

# ======================
# API SEARCH (eski mantık korunmuş)
# ======================
def normalize(v):
    if not v:
        return ""
    return re.sub(r"\s+", "", str(v)).upper()

@app.route("/api/search/<name>")
def search(name):
    path = os.path.join(DATA_DIR, f"{name}.json")
    if not os.path.isfile(path):
        return {"error": "Dosya yok"}, 404

    if not request.args:
        return {"error": "Parametre yok"}, 400

    key, value = next(iter(request.args.items()))

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    value = normalize(value)
    results = [
        r for r in data
        if key in r and normalize(r.get(key, "")) == value
    ]

    if not results:
        return {"error": "Bulunamadı"}, 404

    if len(results) == 1:
        return jsonify(results[0])

    txt = ""
    for i, r in enumerate(results, 1):
        txt += f"--- KAYIT {i} ---\n"
        for k, v in r.items():
            txt += f"{k}: {v}\n"
        txt += "\n"
    return Response(txt, mimetype="text/plain")

# ======================
# BOT HANDLER'LAR
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid == ADMIN_ID:
        kb = [["📤 Dosya Yükle"], ["📄 Dosyalar"]]
        await update.message.reply_text(
            "👑 ADMIN PANEL",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
        )
        return

    try:
        member = await context.bot.get_chat_member(CHANNEL, uid)
        if member.status in ("member", "administrator", "creator"):
            await update.message.reply_text("✅ Hoş geldin!")
        else:
            await update.message.reply_text(f"❌ {CHANNEL} kanalına katıl!")
    except Exception:
        await update.message.reply_text(f"❌ {CHANNEL} kanalına katıl!")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    doc = update.message.document
    if not doc:
        await update.message.reply_text("Dosya gönder lütfen.")
        return

    file = await doc.get_file()
    raw_bytes = await file.download_as_bytearray()
    text = raw_bytes.decode("utf-8", errors="ignore")

    try:
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError
    except Exception:
        data = [{"value": l.strip()} for l in text.splitlines() if l.strip()]

    name = os.path.splitext(doc.file_name or "veri")[0].lower()
    safe = "".join(c for c in name if c.isalnum() or c in "-_")

    path = os.path.join(DATA_DIR, f"{safe}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    await update.message.reply_text(f"✅ Yüklendi: /{safe}\nÖrnek: /api/search/{safe}?key=deger")

# ======================
# BOT BAŞLATMA
# ======================
def run_bot():
    if not BOT_TOKEN or len(BOT_TOKEN.strip()) < 30:
        print("HATA: BOT_TOKEN kodda tanımlı değil veya hatalı!")
        return

    print("Bot polling başlıyor...")

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"Bot hatası: {context.error}")

    application.add_error_handler(error_handler)

    application.run_polling(
        poll_interval=1.0,
        timeout=20,
        drop_pending_updates=True,          # restart sonrası eski update'leri at
        bootstrap_retries=-1,               # bağlantı sorunu olursa sonsuz retry
        allowed_updates=Update.ALL_TYPES
    )

# ======================
# ANA ÇALIŞTIRMA
# ======================
if __name__ == "__main__":
    # Bot ayrı thread'de
    threading.Thread(target=run_bot, daemon=True).start()

    # Flask ana thread'de (Render dinlesin)
    print(f"Flask başlatılıyor – PORT: {PORT}")
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        use_reloader=False
    )
