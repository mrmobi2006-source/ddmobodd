import base64
import json
import io
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات التقنية المستخرجة ---
TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"

def derive_aes_key():
    """اشتقاق المفتاح باستخدام خوارزمية XOR 68 التي استخرجناها من الجافا"""
    reference = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
    decoded = base64.b64decode(reference)
    # استخراج 16 بايت بدءاً من Index 4 وإجراء XOR مع 68
    key_bytes = bytearray(decoded[4:20])
    return bytes([b ^ 68 for b in key_bytes])

AES_KEY = derive_aes_key()

def decrypt_payload(encrypted_data_b64):
    """فك تشفير AES-CBC للبيانات الموصدة"""
    try:
        raw_data = base64.b64decode(encrypted_data_b64)
        iv = raw_data[:16]  # أول 16 بايت هي الـ IV
        ciphertext = raw_data[16:]
        
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"خطأ في فك التشفير: {str(e)}"

async def process_config(content):
    """تحليل نص الإعدادات وفكه سواء كان رابطاً أو ملف JSON"""
    try:
        # إذا كان رابطاً، نزيل البادئة ونفك الـ Base64 الخارجي
        if content.startswith("darktunnel://"):
            content = content.replace("darktunnel://", "")
        
        data = json.loads(base64.b64decode(content))
        
        # التحقق من وجود محتوى موصد (Locked)
        if "encryptedLockedConfig" in data:
            inner_decrypted = decrypt_payload(data["encryptedLockedConfig"])
            return f"✅ **تم كسر التشفير بنجاح!**\n\n**الإعدادات الداخلية:**\n`{inner_decrypted}`"
        else:
            return f"✅ **إعدادات مفتوحة:**\n`{json.dumps(data, indent=2, ensure_ascii=False)}`"
    except:
        return "❌ فشل تحليل البيانات. تأكد أن الرابط أو الملف صحيح."

# --- إدارة البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل لي رابط Darktunnel أو ملف .dark وسأقوم بتفكيكه لك فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await process_config(update.message.text)
    await update.message.reply_text(result, parse_mode='Markdown')

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.document.file_id)
    buffer = io.BytesIO()
    await file.download_to_memory(buffer)
    content = buffer.getvalue().decode('utf-8')
    
    result = await process_config(content)
    await update.message.reply_text(result, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("البوت يعمل الآن... في انتظار الملفات.")
    app.run_polling()
