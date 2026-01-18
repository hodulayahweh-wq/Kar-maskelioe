import os
import json
import pandas as pd
from flask import Flask, request, jsonify, send_file
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import threading

app = Flask(__name__)

# --- AYARLAR ---
TELEGRAM_BOT_TOKEN = "7127783002:AAHsB7KxujS-YnLJzxntfThAVR2d9fv0TpE"
BASE_URL = "https://ganstar.onrender.com"
DATA_DIR = "veriler"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- VERİ DÜZENLEME ---
def veriyi_temiz_kaydet(df, api_ismi):
    json_yolu = os.path.join(DATA_DIR, f"{api_ismi}.json")
    liste_verisi = df.to_dict(orient='records')
    
    # Verileri alt alta, boşluklu ve en okunaklı şekilde kaydet
    with open(json_yolu, 'w', encoding='utf-8') as f:
        json.dump(liste_verisi, f, indent=4, ensure_ascii=False)
    return json_yolu

# --- TELEGRAM BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif! Dosya gönder, API anında hazır olsun. (Key Gerekmez)")

async def dosya_yonetimi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    api_ismi = doc.file_name.split('.')[0].replace(" ", "_").lower()
    
    await update.message.reply_text("⚡ Veriler işleniyor ve sunucuya yükleniyor...")
    
    telegram_file = await context.bot.get_file(doc.file_id)
    temp_path = f"temp_{doc.file_name}"
    await telegram_file.download_to_drive(temp_path)

    try:
        # Hızlı okuma
        if temp_path.endswith('.csv'):
            df = pd.read_csv(temp_path, low_memory=False)
        else:
            df = pd.read_csv(temp_path, sep=None, engine='python')

        veriyi_temiz_kaydet(df, api_ismi)
        
        api_link = f"{BASE_URL}/api/v1/search/{api_ismi}"
        
        msg = (f"✅ **API Yayında!**\n\n"
               f"🔗 **Link:** `{api_link}`\n"
               f"🔓 **Erişim:** Herkese Açık (Key Yok)\n\n"
               f"Sorgu için: `{api_link}?ara=aranacak_kelime`")
        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {str(e)}")
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

# --- AÇIK API SERVİSİ ---
@app.route('/api/v1/search/<api_ismi>', methods=['GET'])
def search_api(api_ismi):
    json_yolu = os.path.join(DATA_DIR, f"{api_ismi}.json")
    
    if not os.path.exists(json_yolu):
        return jsonify({"hata": "Veri bulunamadı."}), 404

    with open(json_yolu, 'r', encoding='utf-8') as f:
        veriler = json.load(f)

    sorgu = request.args.get('ara')
    if sorgu:
        # Hızlı filtreleme
        sonuclar = [v for v in veriler if sorgu.lower() in str(v.values()).lower()]
    else:
        sonuclar = veriler

    # Veri çoksa (50+ kayıt) .txt dosyası olarak düzenli şekilde gönder
    if len(sonuclar) > 50:
        temp_result = f"sonuc_{api_ismi}.txt"
        with open(temp_result, "w", encoding="utf-8") as f:
            for s in sonuclar:
                # Her verinin altına boşluk ekleyerek kaydeder
                f.write(json.dumps(s, indent=4, ensure_ascii=False) + "\n\n")
        return send_file(temp_result, as_attachment=True)

    return jsonify(sonuclar)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, dosya_yonetimi))
    application.run_polling()
