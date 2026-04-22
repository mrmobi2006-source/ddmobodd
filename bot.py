import base64
import json
import logging
import re
from Crypto.Cipher import AES

# إعداد المكتبة الخاصة بالتليجرام
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات (Logs) لمتابعة البوت من ريلواي
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

# --- بيانات البوت الخاصة بك ---
TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"

def clean_b64(data):
    """تنظيف النص وإصلاح الحشو (Padding)"""
    data = data.strip().replace('-', '+').replace('_', '/').replace('\n', '').replace('\r', '')
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    return data

def decrypt_darktunnel(link):
    try:
        # 1. استخراج الجزء المشفر من الرابط
        if "darktunnel://" in link:
            link = link.split("darktunnel://")[1].strip()
        
        # 2. فك الغلاف الخارجي (JSON)
        outer_bytes = base64.b64decode(clean_b64(link))
        outer_json = json.loads(outer_bytes.decode('utf-8', errors='ignore'))
        encrypted_config = outer_json.get("encryptedLockedConfig", "")

        if not encrypted_config:
            return "❌ الرابط لا يحتوي على تشفير داخلي (Locked Config)."

        # 3. إعداد المفاتيح المحتملة (المفتاح المستخرج XOR 68)
        # هذا هو الجزء الذي استخرجناه من الجافا
        ref = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
        key_bytes = bytearray(base64.b64decode(ref))
        # المفتاح الأول: XOR 68 على البايتات من 4 إلى 20
        key1 = bytes([b ^ 68 for b in key_bytes[4:20]])
        
        # مفاتيح احتياطية في حال كان هناك تحديث
        possible_keys = [key1, b'1234567890123456', b'darktunnel_key_v']

        # 4. فك تشفير المحتوى (AES-CBC)
        raw_data = base64.b64decode(clean_b64(encrypted_config))
        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        
        # مواءمة الطول مع بلوكات 16 بايت (Trimming)
        remainder = len(ciphertext) % 16
        if remainder != 0:
            ciphertext = ciphertext[:-remainder]

        for k in possible_keys:
            try:
                cipher = AES.new(k, AES.MODE_CBC, iv)
                decrypted = cipher.decrypt(ciphertext)
                
                # تنظيف البايتات الزائدة يدويًا (Manual Unpadding)
                # نبحث عن الكلمات المفتاحية في النتيجة (مثل vless, host, uuid)
                result = decrypted.decode('utf-8', errors='ignore')
                if re.search(r'(vless|vmess|trojan|host|uuid|path)', result, re.IGNORECASE):
                    # تنظيف الرموز غير النصية في البداية والنهاية
                    clean_res = re.sub(r'[^\x20-\x7E]', '', result).strip()
                    return clean_res
            except:
                continue
                
        return "❌ لم يتم العثور على المفتاح الصحيح. ربما تم تحديث مكتبة Go."

    except Exception as e:
        return f"❌ خطأ تقني: {str(e)}"

# --- دوال التعامل مع التليجرام ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك! أرسل لي رابط DarkTunnel وسأقوم بمحاولة كسر التشفير فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return
    
    # إشعار المستخدم بالبدء
    status_msg = await update.message.reply_text("⏳ جاري محاولة الفك...")
    
    result = decrypt_darktunnel(text)
    
    # الرد بالنتيجة
    await status_msg.edit_text(f"🔍 النتيجة:\n\n`{result}`", parse_mode='Markdown')

if __name__ == '__main__':
    # بناء البوت
    app = ApplicationBuilder().token(TOKEN).build()
    
    # إضافة الأوامر والمستقبلات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logging.info("البوت يعمل الآن على ريلواي...")
    app.run_polling()
