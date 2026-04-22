import base64
import json
import io
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"

def derive_aes_key():
    reference = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
    decoded = base64.b64decode(reference)
    key_bytes = bytearray(decoded[4:20])
    return bytes([b ^ 68 for b in key_bytes])

AES_KEY = derive_aes_key()

def robust_b64decode(b64_string):
    # تنظيف شامل للنص من أي فراغات أو رموز غريبة قد تأتي من النسخ واللصق
    clean_b64 = b64_string.strip().replace('-', '+').replace('_', '/').replace('\n', '').replace('\r', '')
    padding_needed = len(clean_b64) % 4
    if padding_needed:
        clean_b64 += '=' * (4 - padding_needed)
    return base64.b64decode(clean_b64)

def decrypt_payload(encrypted_data_b64):
    try:
        raw_data = robust_b64decode(encrypted_data_b64)
        
        # --- السر الاحترافي: إصلاح طول البيانات تلقائياً ---
        # إذا كانت البيانات ليست من مضاعفات 16، نقوم بقص الزيادة (Junk Bytes)
        remainder = len(raw_data) % 16
        if remainder != 0:
            raw_data = raw_data[:-remainder] # قص البايتات العائدة للحماية
        
        if len(raw_data) < 32: # 16 للـ IV و 16 كحد أدنى للبيانات
            return "❌ النص قصير جداً ليكون مشفراً."

        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        # استخدام try داخلي لفك الحشو (Padding) لأن المطور قد يستخدم Zero Padding
        try:
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        except:
            # إذا فشل unpad العادي، نجرب الفك الخام وننظف يدوياً
            decrypted = cipher.decrypt(ciphertext).strip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f')
            
        return decrypted.decode('utf-8', errors='ignore')
        
    except Exception as e:
        return f"❌ خطأ AES: {str(e)}"

async def process_config(content):
    try:
        # البحث عن بداية ونهاية الـ JSON داخل النص (في حال وجود كلام قبله أو بعده)
        if "darktunnel://" in content:
            content = content.split("darktunnel://")[1].strip()
        
        raw_bytes = robust_b64decode(content)
        decoded_text = raw_bytes.decode('utf-8', errors='ignore')
        
        # محاولة فك كـ JSON
        try:
            data = json.loads(decoded_text)
            if "encryptedLockedConfig" in data:
                inner = decrypt_payload(data["encryptedLockedConfig"])
                return f"✅ **تم كسر القفل بنجاح:**\n\n`{inner}`"
            return f"📝 **بيانات مفتوحة:**\n`{json.dumps(data, indent=2)}`"
        except:
            # إذا لم يكن JSON، ربما هو النص المشفر مباشرة
            inner = decrypt_payload(content)
            if inner and not inner.startswith("❌"):
                return f"🔓 **فك تشفير مباشر:**\n\n`{inner}`"
            return "❌ تعذر فهم بنية البيانات (ليست JSON وليست AES صالحة)."

    except Exception as e:
        return f"❌ خطأ عام: {str(e)}"

# --- إعدادات البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل أي شيء وسأحاول تحطيمه! 🛠️")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = await process_config(update.message.text)
    await update.message.reply_text(result, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("البوت (النسخة النهائية) يعمل الآن...")
    app.run_polling()
