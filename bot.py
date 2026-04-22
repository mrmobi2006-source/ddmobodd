import telebot
import base64
import json
import io

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "مرحباً يا بطل! 🚀\nأرسل لي ملف .dark وسأقوم بفك تشفيره وإرسال المحتوى كملف نصي (.txt) لتفادي حدود تليجرام.")

@bot.message_handler(content_types=['document'])
def handle_dark_file(message):
    # التحقق من أن الملف ينتهي بـ .dark (اختياري، يمكنك إزالته ليقبل أي ملف)
    if not message.document.file_name.lower().endswith('.dark'):
        bot.reply_to(message, "⚠️ يرجى إرسال ملف بصيغة .dark")
        return

    msg = bot.reply_to(message, "⏳ جاري قراءة وفك تشفير الملف...")
    
    try:
        # 1. تحميل الملف من تليجرام
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # 2. تحويل محتوى الملف إلى نص
        file_content = downloaded_file.decode('utf-8', errors='ignore').strip()
        
        # 3. تنظيف النص (إذا كان يحتوي على Darktunnel:// نزيلها)
        if "://" in file_content:
            base64_data = file_content.split("://", 1)[1]
        else:
            base64_data = file_content
            
        # 4. فك تشفير Base64
        decoded_bytes = base64.b64decode(base64_data)
        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
        
        # 5. محاولة ترتيب البيانات كـ JSON لتكون سهلة القراءة
        try:
            parsed_json = json.loads(decoded_str)
            final_text = json.dumps(parsed_json, indent=4, ensure_ascii=False)
        except json.JSONDecodeError:
            # إذا لم يكن JSON مرتباً، نعطيك النص كما هو
            final_text = decoded_str
            
        # 6. إنشاء ملف نصي وهمي في الذاكرة (بدون حفظه على مساحة الاستضافة)
        text_file = io.BytesIO(final_text.encode('utf-8'))
        text_file.name = f"Decrypted_{message.document.file_name}.txt"
        
        # 7. إرسال الملف إليك
        bot.send_document(message.chat.id, text_file, caption="✅ تم فك التشفير بنجاح! افتح الملف النصي لترى الإعدادات.")
        
        # حذف رسالة "جاري الانتظار" لتنظيف المحادثة
        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ أثناء فك التشفير:\n`{str(e)}`", 
                              chat_id=message.chat.id, 
                              message_id=msg.message_id,
                              parse_mode='Markdown')

print("Bot is ready and waiting for .dark files...")
bot.infinity_polling()
