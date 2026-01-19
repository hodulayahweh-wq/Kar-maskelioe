# -*- coding: utf-8 -*-

import os
import json
import zipfile
import shutil
import threading
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

# ================= AYARLAR =================
BOT_TOKEN = "8210876778:AAEYapHGjNEx1ysqLR4nYr2ilXZ4m7tOsOs"
BASE_URL = "https://ganstar.onrender.com"

DATA_DIR = "veriler"
TEMP_DIR = "temp"
LOG_FILE = "logs.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# ================= FLASK =================
app = Flask(__name__)

def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_log(data):
    logs = load_logs()
    logs.append(data)
    logs = logs[-100:]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

@app.route("/api/v1/search/<api_id>")
def search_api(api_id):
    path = os.path.join(DATA_DIR, f"{api_id}.json")
    if not os.path.exists(path):
        return jsonify({"error": "API bulunamadı"}), 404

    query = request.args.get("ara", "").lower()

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    save_log({
        "api": api_id,
        "query": query,
        "ip": request.remote_addr,
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    if query:
        data = [x for x in data if query in json.dumps(x, ensure_ascii=False).lower()]

    return jsonify(data)

@app.route("/api/v1/logs")
def api_logs():
    return jsonify(load_logs())

def run_flask():
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        threaded=True
    )

# ================= DOSYA İŞLEME =================
def extract_archive(path, out):
    if path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            z.extractall(out)

    elif path.endswith(".7z"):
        with py7zr.SevenZipFile(path, mode="r") as z:
            z.extractall(out)

def read_all_files(folder):
    results = []
    for root, _, files in os.walk(folder):
        for name in files:
            full = os.path.join(root, name)
            try:
                with open(full, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            results.append({
                                "veri": line,
                                " ": ""
                            })
            except:
                pass
    return results

# ================= TELEGRAM =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 ZIP veya 7Z dosya gönder.\n"
        "İçindeki tüm veriler API olarak açılır."
    )

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    api_id = f"api_{int(datetime.datetime.now().timestamp())}"

    await update.message.reply_text("⏳ Dosya işleniyor...")

    tg_file = await context.bot.get_file(doc.file_id)
    archive_path = os.path.join(TEMP_DIR, doc.file_name)
    await tg_file.download_to_drive(archive_path)

    extract_path = os.path.join(TEMP_DIR, api_id)
    os.makedirs(extract_path, exist_ok=True)

    extract_archive(archive_path, extract_path)
    data = read_all_files(extract_path)

    with open(os.path.join(DATA_DIR, f"{api_id}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    shutil.rmtree(extract_path)
    os.remove(archive_path)

    await update.message.reply_text(
        "✅ API OLUŞTURULDU\n\n"
        f"{BASE_URL}/api/v1/search/{api_id}?ara="
    )

# ================= MAIN =================
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()

    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.Document.ALL, file_handler))

    bot.run_polling()
