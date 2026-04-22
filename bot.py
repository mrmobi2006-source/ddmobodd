import telebot
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# التوكن الخاص بك
TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"
bot = telebot.TeleBot(TOKEN)

def get_aes_key():
    """خوارزمية استخراج المفتاح السري التي قمنا بتحليلها"""
    encoded_str = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
    decoded_bytes = base64.b64decode(encoded_str)
    # أخذ 16 بايت من الموقع 4
    key_fragment = bytearray(decoded_bytes[4:20])
    # عملية XOR مع الرقم 68
    final_key = bytes([b ^ 68 for b in key_fragment])
    return final_key

# استدعاء المفتاح مرة واحدة عند تشغيل البوت
AES_KEY = get_aes_key()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "مرحباً بك يا بطل في بوت فك التشفير! 🚀\n\n"
        "قم بإرسال ملف الإعدادات المشفر (مثلاً ملف .dark أو أي ملف يستعمل نفس الخوارزمية) "
        "وسأقوم باستخراج سيرفرات VLESS والبيانات منه فوراً."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    msg = bot.reply_to(message, "⏳ جاري تحليل وفك تشفير الملف...")
    try:
        # تحميل الملف من التليجرام
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # بحسب تحليلنا لكود الجافا (السطر 188)، أول 16 بايت هي الـ IV
        iv = downloaded_file[:16]
        # باقي الملف هو النص المشفر
        ciphertext = downloaded_file[16:]

        # عملية فك التشفير AES/CBC
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)
        
        # إزالة الحشو (Padding) وتحويل الناتج إلى نص
        decrypted_data = unpad(decrypted_padded, AES.block_size).decode('utf-8', errors='ignore')

        # التحقق من حجم النص (تليجرام لا يسمح برسائل أطول من 4096 حرف)
        if len(decrypted_data) > 4000:
            with open("decrypted_servers.txt", "w", encoding="utf-8") as f:
                f.write(decrypted_data)
            with open("decrypted_servers.txt", "rb") as f:
                bot.send_document(message.chat.id, f, caption="✅ تم فك التشفير! (تم إرساله كملف لأن المحتوى طويل جداً)")
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            bot.edit_message_text(f"✅ **تم فك التشفير بنجاح:**\n\n`{decrypted_data}`", 
                                  chat_id=message.chat.id, 
                                  message_id=msg.message_id, 
                                  parse_mode='Markdown')

    except ValueError:
        bot.edit_message_text("❌ خطأ: لم أتمكن من إزالة الحشو (Padding). قد يكون الملف غير مدعوم أو المفتاح غير مطابق لهذه النسخة.", 
                              chat_id=message.chat.id, 
                              message_id=msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ غير متوقع:\n`{str(e)}`", 
                              chat_id=message.chat.id, 
                              message_id=msg.message_id, 
                              parse_mode='Markdown')

print("Bot is running...")
# تشغيل البوت بشكل مستمر
bot.infinity_polling()
