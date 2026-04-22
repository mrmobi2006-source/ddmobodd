import base64
import json
import logging
import hashlib
import re
from Crypto.Cipher import AES
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"

def get_potential_keys():
    """توليد قائمة بكل المفاتيح المحتملة بناءً على تحليل ملفات الجافا والـ SO"""
    keys = []
    
    # 1. المفتاح المستخرج من الجافا (XOR 68)
    try:
        ref = base64.b64decode("ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU=")
        keys.append(bytes([b ^ 68 for b in ref[4:20]])) # 16-byte
        keys.append(bytes([b ^ 68 for b in ref[:32]]))  # 32-byte
    except:
        pass

    # 2. مفاتيح مشتقة من الكلمات التي وجدناها في ملف libgojni.so
    # التطبيقات غالباً تستخدم MD5 أو SHA256 للكلمات المفتاحية لتوليد المفتاح
    magic_words = [
        "darktunnel", "libdarktunnel", "v2ray.com/core", 
        "vless", "vmess", "libgojni", "darktunnel_key"
    ]
    for word in magic_words:
        keys.append(hashlib.md5(word.encode()).digest()) # يولد مفتاح 16 بايت
        keys.append(hashlib.sha256(word.encode()).digest()[:16]) # يولد مفتاح 16 بايت
        keys.append(hashlib.sha256(word.encode()).digest()) # يولد مفتاح 32 بايت

    # 3. مفاتيح Go القياسية الثابتة
    keys.extend([
        b'0123456789abcdef',
        b'0123456789abcdef0123456789abcdef',
        b'\x32\x43\xf6\xa8\x88\x5a\x30\x8d\x31\x31\x98\xa2\xe0\x37\x07\x34'
    ])
    return keys

def clean_b64(data):
    data = data.strip().replace('-', '+').replace('_', '/')
    pad = len(data) % 4
    return data + '=' * (4 - pad) if pad else data

def crack_darktunnel(link):
    try:
        if "darktunnel://" in link:
            link = link.split("darktunnel://")[1].strip()
        
        outer_json = json.loads(base64.b64decode(clean_b64(link)).decode('utf-8', errors='ignore'))
        enc_config = outer_json.get("encryptedLockedConfig", "")
        
        if not enc_config:
            return "❌ لا يوجد إعداد مشفر في هذا الرابط."

        raw_data = base64.b64decode(clean_b64(enc_config))
        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        ciphertext = ciphertext[:(len(ciphertext) // 16) * 16] # قص الزوائد

        possible_keys = get_potential_keys()
        
        # تجربة كل المفاتيح كـ "هاكر" حقيقي
        for key in possible_keys:
            try:
                cipher = AES.new(key, AES.MODE_CBC, iv)
                dec = cipher.decrypt(ciphertext)
                result = "".join([chr(b) for b in dec if 32 <= b <= 126]) # تنظيف فوري
                
                if "vless" in result.lower() or "vmess" in result.lower() or "uuid" in result.lower():
                    return f"🔓 **تم الاختراق بنجاح!**\n\n`{result.strip()}`"
            except:
                continue
                
        return "❌ لم يتطابق أي مفتاح من القاموس. (التشفير معقد جداً)"
    except Exception as e:
        return f"❌ فشل في تحليل الرابط: {str(e)}"

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return
    
    msg = await update.message.reply_text("⏳ جاري تحليل الرابط وكسر التشفير...")
    result = crack_darktunnel(text)
    await msg.edit_text(result, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    logging.info("🔥 محرك الاختراق يعمل الآن...")
    app.run_polling()
