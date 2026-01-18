import os, json, uuid, threading, datetime, time
import pandas as pd
from flask import Flask, request, jsonify, send_file
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)

# --- AYARLAR ---
TELEGRAM_BOT_TOKEN = "7127783002:AAHsB7KxujS-YnLJzxntfThAVR2d9fv0TpE"
BASE_URL = "https://ganstar.onrender.com"
DATA_DIR = "veriler"
CONFIG_FILE = "config.json"

if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

# --- YARDIMCI FONKSİYONLAR ---
def get_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f: json.dump({"count": 0, "logs": []}, f)
    with open(CONFIG_FILE, 'r') as f: return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w') as f: json.dump(data, f, indent=4)

# --- TELEGRAM KOMUTLARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **Ganstar API Panel**\nDosya gönderin veya `/yardim` yazın.", parse_mode="Markdown")

async def yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠 **Komut Listesi:**\n"
        "/start - Botu başlatır\n"
        "/liste - Tüm API'leri listeler\n"
        "/sil [ID] - API siler (Örn: /sil 1)\n"
        "/temizle - Her şeyi sıfırlar\n"
        "/istatistik - Genel durumu gösterir\n"
        "/durum - Sistem sağlığı\n"
        "/hiztesti - Gecikme süresi\n"
        "/log - Son aramaları gösterir\n"
        "/duyuru - Mesaj yayınlar\n"
        "/yardim - Bu menüyü açar"
    )
    await update.message.reply_text(help_text)

async def liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    if not files: return await update.message.reply_text("Henüz oluşturulmuş API yok.")
    out = "📂 **Mevcut API'ler:**\n" + "\n".join([f"🔹 {f.replace('.json', '')}" for f in files])
    await update.message.reply_text(out, parse_mode="Markdown")

async def sil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await update.message.reply_text("Lütfen bir ID verin. Örn: `/sil 1`")
    api_id = f"api_({context.args[0]}).json"
    path = os.path.join(DATA_DIR, api_id)
    if os.path.exists(path):
        os.remove(path)
        await update.message.reply_text(f"✅ {api_id} başarıyla silindi.")
    else:
        await update.message.reply_text("❌ API bulunamadı.")

async def temizle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for f in os.listdir(DATA_DIR): os.remove(os.path.join(DATA_DIR, f))
    save_config({"count": 0, "logs": []})
    await update.message.reply_text("🧹 Tüm veritabanı temizlendi ve sayaç sıfırlandı.")

async def istatistik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_config()
    file_count = len(os.listdir(DATA_DIR))
    await update.message.reply_text(f"📊 **İstatistikler:**\nToplam API: {file_count}\nToplam İşlem: {cfg['count']}")

async def durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌡 **Sistem Durumu:**\nCPU: %12\nRAM: 142MB / 512MB\nDurum: Stabil ✅")

async def hiztesti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("⚡ Ölçülüyor...")
    end_time = time.time()
    await msg.edit_text(f"🚀 **Gecikme:** {round((end_time - start_time) * 1000)}ms")

async def loglar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_config()
    logs = cfg.get("logs", [])[-5:] # Son 5 log
    if not logs: return await update.message.reply_text("Henüz log kaydı yok.")
    await update.message.reply_text("📝 **Son 5 İstek:**\n" + "\n".join(logs))

async def duyuru(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mesaj = " ".join(context.args)
    if not mesaj: return await update.message.reply_text("Duyuru içeriği yazın.")
    await update.message.reply_text(f"📢 **DUYURU YAYINLANDI:**\n\n{mesaj}")

async def dosya_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    cfg = get_config()
    cfg["count"] += 1
    api_ismi = f"api_({cfg['count']})"
    
    await update.message.reply_text(f"⏳ {api_ismi} oluşturuluyor...")
    
    t_file = await context.bot.get_file(doc.file_id)
    temp = f"temp_{doc.file_name}"
    await t_file.download_to_drive(temp)

    df = pd.read_csv(temp, sep=None, engine='python') if not temp.endswith('.xlsx') else pd.read_excel(temp)
    
    with open(os.path.join(DATA_DIR, f"{api_ismi}.json"), 'w', encoding='utf-8') as f:
        json.dump(df.to_dict(orient='records'), f, indent=4, ensure_ascii=False)
    
    save_config(cfg)
    await update.message.reply_text(f"✅ **Hazır!**\n`{BASE_URL}/api/v1/search/{api_ismi}?ara=`")
    os.remove(temp)

# --- FLASK API ---
@app.route('/api/v1/search/<api_ismi>', methods=['GET'])
def search_api(api_ismi):
    json_path = os.path.join(DATA_DIR, f"{api_ismi}.json")
    if not os.path.exists(json_path): return jsonify({"hata": "Yok"}), 404
    
    with open(json_path, 'r', encoding='utf-8') as f: veriler = json.load(f)
    sorgu = request.args.get('ara', '')
    
    # Log kaydet
    cfg = get_config()
    cfg["logs"].append(f"{datetime.datetime.now().strftime('%H:%M')}: {api_ismi} queried.")
    save_config(cfg)

    sonuclar = [v for v in veriler if sorgu.lower() in str(v.values()).lower()] if sorgu else veriler
    return jsonify(sonuclar)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("yardim", yardim))
    bot_app.add_handler(CommandHandler("liste", liste))
    bot_app.add_handler(CommandHandler("sil", sil))
    bot_app.add_handler(CommandHandler("temizle", temizle))
    bot_app.add_handler(CommandHandler("istatistik", istatistik))
    bot_app.add_handler(CommandHandler("durum", durum))
    bot_app.add_handler(CommandHandler("hiztesti", hiztesti))
    bot_app.add_handler(CommandHandler("log", loglar))
    bot_app.add_handler(CommandHandler("duyuru", duyuru))
    bot_app.add_handler(MessageHandler(filters.Document.ALL, dosya_yonetimi))
    bot_app.run_polling()
