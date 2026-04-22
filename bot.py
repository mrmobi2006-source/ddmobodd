import base64
import json
import io
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# تفعيل سجل الأخطاء ليظهر في الشاشة عندك
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"

def derive_aes_key():
    reference = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
    decoded = base64.b64decode(reference)
    key_bytes = bytearray(decoded[4:20])
    return bytes([b ^ 68 for b in key_bytes])

AES_KEY = derive_aes_key()

def robust_b64decode(b64_string):
    clean_b64 = b64_string.strip().replace('-', '+').replace('_', '/').replace('\n', '').replace('\r', '')
    padding_needed = len(clean_b64) % 4
    if padding_needed:
        clean_b64 += '=' * (4 - padding_needed)
    return base64.b64decode(clean_b64)

def decrypt_payload(encrypted_data_b64):
    try:
        raw_data = robust_b64decode(encrypted_data_b64)
        remainder = len(raw_data) % 16
        if remainder != 0:
            raw_data = raw_data[:-remainder]
        
        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        
        try:
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        except:
            decrypted = cipher.decrypt(ciphertext).strip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')
            
        return decrypted.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Error: {str(e)}"

async def process_config(content):
    print(f"--- جاري معالجة بيانات بطول: {len(content)} حرف ---")
    try:
        # إذا كان الرابط يبدأ بـ البروتوكول
        if "darktunnel://" in content:
            content = content.split("darktunnel://")[1].split()[0] # نأخذ الرابط فقط
        
        # فك الغلاف
        raw_bytes = robust_b64decode(content)
        decoded_text = raw_bytes.decode('utf-8', errors='ignore')
        
        if '"encryptedLockedConfig"' in decoded_text:
            data = json.loads(decoded_text)
            return decrypt_payload(data["encryptedLockedConfig"])
        
        # إذا لم يكن JSON جرب الفك المباشر
        return decrypt_payload(content)
    except Exception as e:
        return f"فشل في التحليل: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل الكود وسأقوم بفكه.")

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # الحصول على النص سواء كان رسالة عادية أو تعليق على ملف
    text = update.message.text or update.message.caption
    
    # إذا أرسل ملفاً
    if update.message.document:
        print("استلمت ملفاً...")
        file = await context.bot.get_file(update.message.document.file_id)
        buffer = io.BytesIO()
        await file.download_to_memory(buffer)
        text = buffer.getvalue().decode('utf-8', errors='ignore')

    if not text:
        return

    print("جاري المحاولة...")
    result = await process_config(text)
    
    # تقسيم الرسالة إذا كانت طويلة جداً (تلجرام لا يقبل أكثر من 4096 حرف)
    if len(result) > 4000:
        for i in range(0, len(result), 4000):
            await update.message.reply_text(f"`{result[i:i+4000]}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"✅ النتيجة:\n\n`{result}`", parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    # هذا الهاندلر سيستقبل كل شيء (نص، ملفات، صور مع تعليق)
    app.add_handler(MessageHandler(filters.ALL, handle_all))
    
    print("البوت يعمل... جرب الإرسال الآن وراقب شاشة الكالي (Terminal)")
    app.run_polling()
