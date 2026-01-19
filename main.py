# -*- coding: utf-8 -*-

import os
import json
import zipfile
import datetime
import threading
import py7zr

from flask import Flask, jsonify
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

PORT = int(os.environ.get("PORT", 10000))

DATA_DIR = "veriler"
TEMP_DIR = "temp"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ================== TELEGRAM BOT ==================
application = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 ZIP / 7Z / TXT gönder.\n"
        "İçerik JSON API’ye çevrilir."
    )

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    await update.message.reply_text("⏳ Dosya işleniyor...")

    tg_file = await context.bot.get_file(doc.file_id)
    file_path = os.path.join(TEMP_DIR, doc.file_name)
    await tg_file.download_to_drive(file_path)

    api_id = f"api_{int(datetime.datetime.now().timestamp())}"
    result = []

    def oku(dosya):
        try:
            with open(dosya, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        result.append({
                            "veri": line,
                            "": ""
                        })
        except:
            pass

    if file_path.endswith(".zip"):
        with zipfile.ZipFile(file_path) as z:
            z.extractall(TEMP_DIR)
            for name in z.namelist():
                oku(os.path.join(TEMP_DIR, name))

    elif file_path.endswith(".7z"):
        with py7zr.SevenZipFile(file_path, mode="r") as z:
            z.extractall(TEMP_DIR)
            for root, _, files in os.walk(TEMP_DIR):
                for f in files:
                    oku(os.path.join(root, f))
    else:
        oku(file_path)

    out_path = os.path.join(DATA_DIR, f"{api_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    await update.message.reply_text(
        f"✅ API OLUŞTURULDU\n\n"
        f"/api/{api_id}"
    )

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Document.ALL, file_handler))

# ================== FLASK API ==================
app = Flask(__name__)

@app.route("/api/<api_id>")
def api(api_id):
    path = os.path.join(DATA_DIR, f"{api_id}.json")
    if not os.path.exists(path):
        return jsonify({"error": "bulunamadı"})
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    application.run_polling()
