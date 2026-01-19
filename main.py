# -*- coding: utf-8 -*-

import os
import json
import zipfile
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

# ================== ENV ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN yok")
if not BASE_URL:
    raise RuntimeError("RENDER_EXTERNAL_URL yok")

DATA_DIR = "veriler"
TEMP_DIR = "temp"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ================== TELEGRAM APP ==================
tg_app = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 ZIP / 7Z / TXT gönder\n"
        "Dosya otomatik API olur"
    )

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    await update.message.reply_text("⏳ İşleniyor...")

    tg_file = await context.bot.get_file(doc.file_id)
    temp_path = os.path.join(TEMP_DIR, doc.file_name)
    await tg_file.download_to_drive(temp_path)

    api_id = f"api_{int(datetime.datetime.now().timestamp())}"
    sonuc = []

    def oku(dosya):
        try:
            with open(dosya, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        sonuc.append({
                            "veri": line,
                            "": ""
                        })
        except:
            pass

    if temp_path.endswith(".zip"):
        with zipfile.ZipFile(temp_path) as z:
            z.extractall(TEMP_DIR)
            for name in z.namelist():
                oku(os.path.join(TEMP_DIR, name))

    elif temp_path.endswith(".7z"):
        with py7zr.SevenZipFile(temp_path) as z:
            z.extractall(TEMP_DIR)
            for root, _, files in os.walk(TEMP_DIR):
                for f in files:
                    oku(os.path.join(root, f))
    else:
        oku(temp_path)

    with open(f"{DATA_DIR}/{api_id}.json", "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

    await update.message.reply_text(
        f"✅ API hazır\n\n{BASE_URL}/api/{api_id}"
    )

tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(MessageHandler(filters.Document.ALL, file_handler))

# ================== FLASK ==================
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot aktif"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), tg_app.bot)
    tg_app.update_queue.put_nowait(update)
    return "OK"

@app.route("/api/<api_id>")
def api(api_id):
    path = f"{DATA_DIR}/{api_id}.json"
    if not os.path.exists(path):
        return jsonify({"error": "yok"})
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))

# ================== MAIN ==================
if __name__ == "__main__":
    tg_app.bot.set_webhook(f"{BASE_URL}/webhook")
    app.run(host="0.0.0.0", port=PORT)
