import os
import json
import uuid
import pandas as pd
import asyncio
from flask import Flask, request, jsonify, send_file
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import threading

# --- AYARLAR ---
TELEGRAM_BOT_TOKEN = "7127783002:AAHsB7KxujS-YnLJzxntfThAVR2d9fv0TpE"
MASTER_KEY = "lord2026"
RENDER_URL = "https://ganstar.onrender.com"
DB_FILE = "api_database.json"

app = Flask(__name__)

# Veritabanı kontrolü
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w') as f: json.dump({}, f)

def db_oku():
    with open(DB_FILE, 'r') as f: return json.load(f)

def db_yaz(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

# --- TELEGRAM BOT MANTIĞI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Merhaba! Ben API Botu. Dosya gönder, sana özel API oluşturayım. \n\nMaster Key: {MASTER_KEY}")

async def dosya_al(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    file_name = doc.file_name
    
    # Dosyayı indir
    temp_path = f"temp_{file_name}"
    await file.download_to_drive(temp_path)
    
    # Token oluştur ve işle
    api_token = str(uuid.uuid4())[:8]
    json_path = f"data_{api_token}.json"
    
    try:
        if file_name.endswith('.csv'):
            df = pd.read_csv(temp_path)
        else:
            df = pd.read_csv(temp_path, sep=None, engine='python')
        
        veriler = df.to_dict(orient='records')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(veriler, f, indent=4, ensure_ascii=False)
        
        db = db_oku()
        db[api_token] = json_path
        db_yaz(db)
        
        msg = (f"✅ API Oluşturuldu!\n\n"
               f"🔑 Token: `{api_token}`\n"
               f"🔗 API Link: {RENDER_URL}/get-data\n"
               f"❓ Sorgu: `{RENDER_URL}/get-data?token={api_token}&ara=kelime`\n\n"
               f"Veriyi çekmek için bu tokeni kullanın.")
        await update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        await update.message.reply_text(f"Hata oluştu: {e}")
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

# --- FLASK API MANTIĞI (Veri Çekme) ---

@app.route('/get-data', methods=['GET'])
def veri_cek():
    token = request.args.get('token') or request.headers.get("Authorization")
    sorgu = request.args.get('ara')

    db = db_oku()
    if token not in db:
        return jsonify({"hata": "Gecersiz Token"}), 401

    with open(db[token], 'r', encoding='utf-8') as f:
        veriler = json.load(f)

    if sorgu:
        sonuclar = [v for v in veriler if sorgu.lower() in str(v.values()).lower()]
    else:
        sonuclar = veriler

    if len(sonuclar) > 30:
        t_file = f"result_{token}.txt"
        with open(t_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(sonuclar, indent=4, ensure_ascii=False))
        return send_file(t_file, as_attachment=True)

    return jsonify(sonuclar)

# --- ÇALIŞTIRMA ---

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Flask'ı ayrı bir işlemde başlat
    threading.Thread(target=run_flask).start()
    
    # Telegram Botu başlat
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, dosya_al))
    
    print("Bot ve API başlatıldı...")
    application.run_polling()
