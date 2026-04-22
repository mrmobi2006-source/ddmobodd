import base64
import json
import logging
from Crypto.Cipher import AES
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات لمراقبة البوت من لوحة تحكم ريلواي
logging.basicConfig(level=logging.INFO)

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"

def fix_padding(data):
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)
    return data

def decrypt_logic(link):
    try:
        raw_b64 = link.replace("darktunnel://", "").strip()
        outer_data = json.loads(base64.b64decode(fix_padding(raw_b64)))
        encrypted_config = outer_data.get("encryptedLockedConfig", "")
        
        # المفتاح المستخرج (XOR 68)
        ref = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
        key_raw = base64.b64decode(ref)
        aes_key = bytes([b ^ 68 for b in key_raw[4:20]])

        encrypted_config = encrypted_config.replace('-', '+').replace('_', '/')
        full_bytes = base64.b64decode(fix_padding(encrypted_config))
        
        iv = full_bytes[:16]
        ciphertext = full_bytes[16:]
        
        # معالجة طول البيانات (Trimming)
        remainder = len(ciphertext) % 16
        if remainder != 0:
            ciphertext = ciphertext[:-remainder]

        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)
        
        # تنظيف يدوي للبايتات الزائدة
        result = decrypted.strip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')
        return result.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "darktunnel://" in text:
        res = decrypt_logic(text)
        await update.message.reply_text(f"✅ تم الفك:\n\n`{res}`", parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.run_polling()
