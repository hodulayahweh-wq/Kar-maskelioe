import os, json, zipfile, shutil, threading, datetime
import py7zr, rarfile
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ================== AYARLAR ==================
TOKEN = "7127783002:AAHKKKCRHPj-O6aNEX-8s3PBLMI3EgS9ri8"
BASE_URL = "https://ganstar.onrender.com"
DATA_DIR = "veriler"
TMP_DIR = "temp"
LOG_FILE = "logs.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

# ================== FLASK ==================
app = Flask(__name__)

def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    return json.load(open(LOG_FILE))

def save_log(entry):
    logs = load_logs()
    logs.append(entry)
    json.dump(logs[-100:], open(LOG_FILE, "w"), indent=2)

@app.route("/api/v1/search/<api>", methods=["GET"])
def api_search(api):
    path = f"{DATA_DIR}/{api}.json"
    if not os.path.exists(path):
        return jsonify({"error": "API bulunamadı"}), 404

    query = request.args.get("ara", "").lower()
    data = json.load(open(path, encoding="utf-8"))

    save_log({
        "api": api,
        "query": query,
        "ip": request.remote_addr,
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    })

    if query:
        data = [i for i in data if query in json.dumps(i, ensure_ascii=False).lower()]

    return jsonify(data)

@app.route("/api/v1/logs")
def api_logs():
    return jsonify(load_logs())

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), threaded=True)

# ================== DOSYA OKUMA ==================
def read_all_files(folder):
    output = []
    for root, _, files in os.walk(folder):
        for f in files:
            p = os.path.join(root, f)
            try:
                with open(p, encoding="utf-8", errors="ignore") as file:
                    for line in file:
                        line = line.strip()
                        if line:
                            output.append({
                                "veri": line,
                                " ": ""   # boşluklu kayıt
                            })
            except:
                pass
    return output

def extract_archive(path, out):
    if path.endswith(".zip"):
        zipfile.ZipFile(path).extractall(out)
    elif path.endswith(".7z"):
        with py7zr.SevenZipFile(path).extractall(out)
    elif path.endswith(".rar"):
        rarfile.RarFile(path).extractall(out)

# ================== TELEGRAM ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 ZIP / 7Z dosya gönder.\nAPI otomatik oluşur.")

async def dosya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    api_id = f"api_{int(datetime.datetime.now().timestamp())}"

    await update.message.reply_text("⏳ Dosya açılıyor...")

    f = await context.bot.get_file(doc.file_id)
    archive = f"{TMP_DIR}/{doc.file_name}"
    await f.download_to_drive(archive)

    extract_dir = f"{TMP_DIR}/{api_id}"
    os.makedirs(extract_dir, exist_ok=True)

    extract_archive(archive, extract_dir)
    data = read_all_files(extract_dir)

    json.dump(
        data,
        open(f"{DATA_DIR}/{api_id}.json", "w", encoding="utf-8"),
        indent=2,
        ensure_ascii=False
    )

    shutil.rmtree(extract_dir)
    os.remove(archive)

    await update.message.reply_text(
        f"✅ API hazır!\n\n"
        f"{BASE_URL}/api/v1/search/{api_id}?ara="
    )

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()

    app_bot = Application.builder().token(TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.Document.ALL, dosya))
    app_bot.run_polling()
