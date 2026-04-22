import telebot
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"
bot = telebot.TeleBot(TOKEN)

def get_aes_key():
    # النص المرجعي من ملف الجافا
    encoded_str = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
    decoded_bytes = base64.b64decode(encoded_str)
    # التطبيق يأخذ 16 بايت تبدأ من الموقع 4 (index 4 to 20)
    key_fragment = bytearray(decoded_bytes[4:20])
    # عملية الـ XOR مع الرقم 68 (0x44) كما في الكود
    return bytes([b ^ 68 for b in key_fragment])

AES_KEY = get_aes_key()

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    msg = bot.reply_to(message, "🔍 محاولة فك التشفير بطرق متعددة...")
    try:
        file_info = bot.get_file(message.document.file_id)
        data = bot.download_file(file_info.file_path)

        # محاولة 1: افتراض أن أول 16 بايت هي IV
        iv = data[:16]
        ciphertext = data[16:]
        
        # إذا فشل التشفير العادي، سنجرب IV صفري (شائع في بعض تطبيقات التشفير)
        possible_ivs = [iv, bytes([0]*16)]
        
        decrypted_text = None
        
        for trial_iv in possible_ivs:
            try:
                cipher = AES.new(AES_KEY, AES.MODE_CBC, trial_iv)
                raw_decrypted = cipher.decrypt(ciphertext if trial_iv == iv else data)
                
                # محاولة إزالة الحشو PKCS7
                try:
                    decrypted_text = unpad(raw_decrypted, AES.block_size).decode('utf-8', errors='ignore')
                    break 
                except:
                    # إذا فشل الحشو، ربما البيانات لا تحتاج إزالة حشو
                    decrypted_text = raw_decrypted.decode('utf-8', errors='ignore')
                    if "vless" in decrypted_text.lower() or "vmess" in decrypted_text.lower():
                        break
            except:
                continue

        if decrypted_text and len(decrypted_text.strip()) > 5:
            bot.edit_message_text(f"✅ **تم استخراج البيانات:**\n\n`{decrypted_text[:1000]}`", 
                                  chat_id=message.chat.id, 
                                  message_id=msg.message_id, 
                                  parse_mode='Markdown')
        else:
            raise ValueError("لم نتمكن من العثور على نص مفهوم")

    except Exception as e:
        bot.edit_message_text(f"❌ لا يزال هناك تعارض في المفتاح أو بنية الملف.\nتأكد أن الملف هو الملف الناتج عن عملية التشفير في السطر 188 (ملف .tmp أو .dex).", 
                              chat_id=message.chat.id, 
                               message_id=msg.message_id)

bot.infinity_polling()
