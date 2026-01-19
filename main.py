# -*- coding: utf-8 -*-

import os
import json
import zipfile
import shutil
import datetime
import py7zr

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ================== AYARLAR ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN yok")

BASE_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

DATA_DIR = "veriler"
TEMP_DIR = "temp"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ================== TELEGRAM ==================
app_tg = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 ZIP / 7Z / TXT gönder.\n"
        "Dosya API'ye çevrilecektir."
    )

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    await update.message.reply_text("⏳ İşleniyor...")

    file = await context.bot.get_file(doc.file_id)
    path = os.path.join(TEMP_DIR, doc.file_name)
    await file.download_to_drive(path)

    api_id = f"api_{int(datetime.datetime.now().timestamp())}"
    out = []

    def oku(dosya):
        with open(dosya, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append({"veri": line, " ": ""})

    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            z.extractall(TEMP_DIR)
            for n in z.namelist():
                oku(os.path.join(TEMP_DIR, n))

    elif path.endswith(".7z"):
        with py7zr.SevenZipFile(path) as z:
            z.extractall(TEMP_DIR)
            for r, _, f in os.walk(TEMP_DIR):
                for x in f:
                    oku(os.path.join(r, x))
    else:
        oku(path)

    with open(f"{DATA_DIR}/{api_id}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    await update.message.reply_text(
        f"✅ API HAZIR\n\n{BASE_URL}/api/{api_id}"
    )

app_tg.add_handler(CommandHandler("start", start))
app_tg.add_handler(MessageHandler(filters.Document.ALL, file_handler))

# ================== FLASK ==================
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
async def webhook():
    await app_tg.update_queue.put(
        Update.de_json(request.get_json(force=True), app_tg.bot)
    )
    return "OK"

@app.route("/api/<api_id>")
def api(api_id):
    p = f"{DATA_DIR}/{api_id}.json"
    if not os.path.exists(p):
        return jsonify({"error": "yok"})
    with open(p, encoding="utf-8") as f:
        return jsonify(json.load(f))

# ================== MAIN ==================
if __name__ == "__main__":
    app_tg.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"{BASE_URL}/webhook"
    )
    app.run(host="0.0.0.0", port=PORT)
