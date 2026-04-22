import telebot
import base64
import json
import io
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"
bot = telebot.TeleBot(TOKEN)

def get_aes_key():
    # المفتاح القياسي المستخرج من تحليل الكود
    encoded_str = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
    decoded_bytes = base64.b64decode(encoded_str)
    key_fragment = bytearray(decoded_bytes[4:20])
    return bytes([b ^ 68 for b in key_fragment])

AES_KEY = get_aes_key()

def try_decrypt_all_modes(encrypted_base64):
    """تجربة فك التشفير بعدة وضعيات (IV مختلف)"""
    try:
        raw_data = base64.b64decode(encrypted_base64)
    except:
        return "❌ خطأ في ترميز Base64"

    results = []

    # المحاولة 1: أول 16 بايت هي الـ IV (الوضع القياسي)
    try:
        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        dec = unpad(cipher.decrypt(ciphertext), AES.block_size)
        results.append(dec.decode('utf-8', errors='ignore'))
    except: pass

    # المحاولة 2: IV صفري (تستخدمه بعض النسخ المعدلة)
    try:
        zero_iv = bytes([0]*16)
        cipher = AES.new(AES_KEY, AES.MODE_CBC, zero_iv)
        dec = unpad(cipher.decrypt(raw_data), AES.block_size)
        results.append(dec.decode('utf-8', errors='ignore'))
    except: pass

    # المحاولة 3: فك تشفير مباشر بدون إزالة الحشو (لحالات البيانات غير المنظمة)
    try:
        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        results.append(cipher.decrypt(ciphertext).decode('utf-8', errors='ignore'))
    except: pass

    if results:
        # إرجاع أنجح محاولة (التي تحتوي على كلمات دلالية)
        for res in results:
            if "vless" in res.lower() or "host" in res.lower() or "{" in res:
                return res
        return results[0]
    
    return "❌ فشلت جميع محاولات فك تشفير AES بالرغم من استخدام المفتاح الصحيح."

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    msg = bot.reply_to(message, "🔍 جاري الفحص العميق للملف الموصد...")
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8', errors='ignore').strip()

        data_json = json.loads(content)
        final_output = ""

        if "encryptedLockedConfig" in data_json:
            encrypted_val = data_json["encryptedLockedConfig"]
            decrypted_res = try_decrypt_all_modes(encrypted_val)
            
            # تجميع البيانات النهائية
            final_output = f"--- معلومات الملف ---\n"
            final_output += f"الاسم: {data_json.get('name')}\n"
            final_output += f"النوع: {data_json.get('type')}\n"
            final_output += f"----------------------\n\n"
            final_output += f"--- المحتوى المفكوك ---\n"
            final_output += decrypted_res
        else:
            final_output = json.dumps(data_json, indent=4, ensure_ascii=False)

        # إرسال النتيجة
        output_file = io.BytesIO(final_output.encode('utf-8'))
        output_file.name = "Decrypted_Result.txt"
        bot.send_document(message.chat.id, output_file, caption="✅ إليك النتيجة النهائية بعد الفحص العميق.")
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ تقني: {str(e)}", chat_id=message.chat.id, message_id=msg.message_id)

bot.infinity_polling()
