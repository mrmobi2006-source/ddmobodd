import telebot
import base64
import json

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"
bot = telebot.TeleBot(TOKEN)

def decode_darktunnel(link):
    try:
        # إزالة البروتوكول إذا وجد
        if "://" in link:
            base64_data = link.split("://")[1]
        else:
            base64_data = link
            
        # فك ترميز Base64
        decoded_bytes = base64.b64decode(base64_data)
        decoded_str = decoded_bytes.decode('utf-8')
        
        # تحويل النص إلى JSON
        config = json.loads(decoded_str)
        return config
    except Exception as e:
        return f"Error: {str(e)}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "أرسل رابط Darktunnel:// أو نص الـ Base64 وسأقوم باستخراج السيرفر لك فوراً! 🚀")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    input_text = message.text.strip()
    
    if input_text.lower().startswith("darktunnel://") or len(input_text) > 50:
        msg = bot.reply_to(message, "⏳ جاري تحليل الرابط واستخراج البيانات...")
        result = decode_darktunnel(input_text)
        
        if isinstance(result, dict):
            # تنسيق البيانات المستخرجة بشكل جميل
            v2ray = result.get("vlessTunnelConfig", {}).get("v2rayConfig", {})
            inject = result.get("vlessTunnelConfig", {}).get("injectConfig", {})
            
            output = (
                f"✅ **تم فك التكوين بنجاح**\n\n"
                f"👤 **الاسم:** `{result.get('name')}`\n"
                f"Type: `{result.get('type')}`\n\n"
                f"🌐 **Server/Host:** `{v2ray.get('host')}`\n"
                f"🔑 **UUID:** `{v2ray.get('uuid')}`\n"
                f"Path: `{v2ray.get('wsPath')}`\n"
                f"SNI: `{v2ray.get('serverNameIndication')}`\n\n"
                f"📡 **Proxy Host:** `{inject.get('proxyHost')}`\n"
                f"📝 **Payload:**\n`{inject.get('payload')}`"
            )
            bot.edit_message_text(output, message.chat.id, msg.message_id, parse_mode='Markdown')
        else:
            bot.edit_message_text(f"❌ فشل في تحليل الرابط. تأكد من صحة التنسيق.", message.chat.id, msg.message_id)

bot.infinity_polling()
