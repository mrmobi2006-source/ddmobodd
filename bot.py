import telebot
import base64
import json
import io
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# التوكن الخاص بك
TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"
bot = telebot.TeleBot(TOKEN)

def get_aes_key():
    """استخراج المفتاح السري باستخدام خوارزمية XOR 68"""
    encoded_str = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
    decoded_bytes = base64.b64decode(encoded_str)
    key_fragment = bytearray(decoded_bytes[4:20])
    return bytes([b ^ 68 for b in key_fragment])

AES_KEY = get_aes_key()

def decrypt_aes_data(encrypted_str):
    """فك تشفير AES/CBC/PKCS7"""
    try:
        raw_data = base64.b64decode(encrypted_str)
        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)
        return unpad(decrypted_padded, AES.block_size).decode('utf-8', errors='ignore')
    except:
        return None

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "مرحباً! أرسل ملف .dark الملقب بـ 'Locked' وسأقوم بفك الطبقات المشفرة بالكامل.")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    msg = bot.reply_to(message, "⏳ جاري فك التشفير العميق (AES + Base64)...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8', errors='ignore').strip()

        # 1. محاولة قراءة المحتوى كـ JSON
        try:
            data_json = json.loads(content)
            # التحقق إذا كان الملف "Locked" (يحتوي على encryptedLockedConfig)
            if "encryptedLockedConfig" in data_json:
                encrypted_val = data_json["encryptedLockedConfig"]
                decrypted_content = decrypt_aes_data(encrypted_val)
                if decrypted_content:
                    final_result = decrypted_content
                else:
                    final_result = "❌ فشل فك تشفير المحتوى الداخلي (AES)."
            else:
                final_result = json.dumps(data_json, indent=4, ensure_ascii=False)
        except json.JSONDecodeError:
            # 2. إذا لم يكن JSON، ربما هو Base64 مباشر (Darktunnel://)
            if "://" in content:
                content = content.split("://")[1]
            decoded_bytes = base64.b64decode(content)
            final_result = decoded_bytes.decode('utf-8', errors='ignore')

        # إرسال النتيجة كملف نصي
        output = io.BytesIO(final_result.encode('utf-8'))
        output.name = f"Final_Decrypted_{message.document.file_name}.txt"
        
        bot.send_document(message.chat.id, output, caption="✅ تم فك التشفير بالكامل بنجاح!")
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ: {str(e)}", chat_id=message.chat.id, message_id=msg.message_id)

bot.infinity_polling()
