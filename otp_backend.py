from flask import Flask, request, jsonify
import random
import time
import requests
import os

app = Flask(__name__)

BOT_TOKEN = "8841448958:AAEoN3vQURJMKcFcijtGpmQqfATDR60YSoE"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# OTP saqlash: {phone: {code, expires, chat_id}}
otp_store = {}

# Foydalanuvchilar: {phone: chat_id} — oldindan ro'yxatdan o'tgan
user_store = {}

def send_telegram_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text})
    return resp.json()

@app.route('/register', methods=['POST'])
def register():
    """Foydalanuvchi telefonini chat_id bilan bog'lash"""
    data = request.json
    phone = data.get('phone')
    chat_id = data.get('chat_id')
    if not phone or not chat_id:
        return jsonify({"success": False, "error": "phone va chat_id kerak"}), 400
    user_store[phone] = chat_id
    return jsonify({"success": True})

@app.route('/send-otp', methods=['POST'])
def send_otp():
    """OTP yuborish"""
    data = request.json
    phone = data.get('phone')
    if not phone:
        return jsonify({"success": False, "error": "phone kerak"}), 400
    
    chat_id = user_store.get(phone)
    if not chat_id:
        return jsonify({"success": False, "error": "Bu raqam ro'yxatdan o'tmagan. Avval botga /start yozing va raqamingizni kiriting."}), 404
    
    code = str(random.randint(100000, 999999))
    otp_store[phone] = {
        "code": code,
        "expires": time.time() + 300  # 5 daqiqa
    }
    
    msg = f"🦷 DentalCare\n\nSizning tasdiqlash kodingiz:\n\n*{code}*\n\nKod 5 daqiqa amal qiladi."
    result = send_telegram_message(chat_id, msg)
    
    if result.get('ok'):
        return jsonify({"success": True, "message": "Telegram ga kod yuborildi"})
    else:
        return jsonify({"success": False, "error": "Telegram xato: " + str(result)}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """OTP tasdiqlash"""
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    
    if not phone or not code:
        return jsonify({"success": False, "error": "phone va code kerak"}), 400
    
    stored = otp_store.get(phone)
    if not stored:
        return jsonify({"success": False, "error": "Kod topilmadi. Qayta so'rang"}), 404
    
    if time.time() > stored['expires']:
        del otp_store[phone]
        return jsonify({"success": False, "error": "Kod muddati o'tdi"}), 400
    
    if stored['code'] != code:
        return jsonify({"success": False, "error": "Kod noto'g'ri"}), 400
    
    del otp_store[phone]
    return jsonify({"success": True, "message": "Tasdiqlandi!"})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook — foydalanuvchi raqamini olish"""
    data = request.json
    if 'message' not in data:
        return jsonify({"ok": True})
    
    msg = data['message']
    chat_id = msg['chat']['id']
    text = msg.get('text', '')
    
    if text == '/start':
        send_telegram_message(chat_id, 
            "👋 Salom! DentalCare botiga xush kelibsiz!\n\n"
            "Telefon raqamingizni kiriting (masalan: +998901234567)\n"
            "Shundan keyin ilovaga kirishingiz mumkin bo'ladi.")
    elif text.startswith('+998') or text.startswith('998'):
        phone = text if text.startswith('+') else '+' + text
        user_store[phone] = chat_id
        send_telegram_message(chat_id,
            f"✅ {phone} raqami muvaffaqiyatli bog'landi!\n\n"
            "Endi DentalCare ilovasida bu raqam bilan kirishingiz mumkin.")
    
    return jsonify({"ok": True})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
