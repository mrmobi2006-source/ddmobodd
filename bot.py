import base64
import json
import io
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"

def derive_aes_key():
    """المفتاح السري المستخرج من الجافا"""
    reference = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
    decoded = base64.b64decode(reference)
    key_bytes = bytearray(decoded[4:20])
    return bytes([b ^ 68 for b in key_bytes])

AES_KEY = derive_aes_key()

def robust_b64decode(b64_string):
    """
    السر الأول للبوتات الاحترافية: 
    تنظيف النص وإصلاح الحشو لضمان عدم تلف البيانات (مضاعفات الـ 16)
    """
    # تحويل URL-Safe إلى Base64 قياسي
    clean_b64 = b64_string.replace('-', '+').replace('_', '/')
    # إضافة الحشو الناقص (Padding)
    padding_needed = len(clean_b64) % 4
    if padding_needed:
        clean_b64 += '=' * (4 - padding_needed)
    
    return base64.b64decode(clean_b64)

def decrypt_payload(encrypted_data_b64):
    """السر الثاني: فك التشفير مع التعامل مع الأخطاء ديناميكياً"""
    try:
        # فك تشفير Base64 الآمن
        raw_data = robust_b64decode(encrypted_data_b64)
        
        # التأكد من سلامة البلوكات (يجب أن يكون من مضاعفات 16)
        if len(raw_data) % 16 != 0:
            return "❌ البيانات تالفة أو ليست بتشفير AES قياسي."

        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8', errors='ignore')
        
    except Exception as e:
        return f"❌ خطأ تقني في فك AES: {str(e)}"

async def process_config(content):
    try:
        if content.startswith("darktunnel://"):
            content = content.replace("darktunnel://", "")
        
        # فك غلاف الرابط الخارجي بشكل آمن
        raw_json_bytes = robust_b64decode(content)
        data = json.loads(raw_json_bytes.decode('utf-8', errors='ignore'))
        
        if "encryptedLockedConfig" in data:
            inner_decrypted = decrypt_payload(data["encryptedLockedConfig"])
            return f"✅ **تم كسر القفل الداخلي!**\n\n`{inner_decrypted}`"
        else:
            return f"✅ **إعدادات بدون قفل:**\n`{json.dumps(data, indent=2, ensure_ascii=False)}`"
            
    except json.JSONDecodeError:
        # إذا لم يكن الغلاف الخارجي JSON، فربما هو الملف المشفر مباشرة!
        inner_decrypted = decrypt_payload(content)
        if "❌" not in inner_decrypted:
            return f"✅ **تم فك تشفير الملف الخام!**\n\n`{inner_decrypted}`"
        return "❌ فشل تحليل البيانات كـ JSON أو كملف خام."
    except Exception as e:
        return f"❌ خطأ عام: {str(e)}"

# --- إعدادات البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل لي الرابط أو الملف وسأحطمه لك 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ جاري الكسر...")
    result = await process_config(update.message.text)
    await msg.edit_text(result, parse_mode='Markdown')

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ جاري تحميل وفك الملف...")
    file = await context.bot.get_file(update.message.document.file_id)
    buffer = io.BytesIO()
    await file.download_to_memory(buffer)
    content = buffer.getvalue().decode('utf-8', errors='ignore')
    
    result = await process_config(content)
    await msg.edit_text(result, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    print("البوت الاحترافي يعمل الآن...")
    app.run_polling()
