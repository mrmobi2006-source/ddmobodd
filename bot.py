import base64
import json
from Crypto.Cipher import AES

TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"

def final_attempt_decrypt(encrypted_link):
    try:
        # 1. استخراج الـ B64 من الرابط
        raw_b64 = encrypted_link.split("://")[1]
        outer_data = json.loads(base64.b64decode(raw_b64 + "==="))
        inner_payload = outer_data.get("encryptedLockedConfig", "")
        
        # 2. تحضير البيانات لفك التشفير (بناءً على تحليل Ca)
        raw_inner = base64.b64decode(inner_payload.replace('-', '+').replace('_', '/') + "===")
        iv = raw_inner[:16]
        ciphertext = raw_inner[16:]
        ciphertext = ciphertext[:(len(ciphertext) // 16) * 16]

        # 3. المفاتيح المحتملة (السر الأخير)
        # بما أن الكود يستخدم Gomobile، المفتاح غالباً ما يكون مشتقاً من اسم الحزمة أو توقيع ثابت
        potential_keys = [
            b'\x32\x43\xf6\xa8\x88\x5a\x30\x8d\x31\x31\x98\xa2\xe0\x37\x07\x34', # مفتاح Go القياسي
            b'0123456789abcdef', # مفتاح الاختبار
            bytes([b ^ 68 for b in b'ZXCHn3veSKESmIQG']) # مفتاح XOR المستخرج
        ]

        for key in potential_keys:
            cipher = AES.new(key, AES.MODE_CBC, iv)
            dec = cipher.decrypt(ciphertext)
            res = "".join([chr(b) for b in dec if 32 <= b <= 126]) # تنظيف النص
            
            if any(k in res.lower() for k in ["vless", "vmess", "uuid", "path"]):
                return res
        
        return "🔒 التشفير محمي داخل مكتبة Go الناتجة عن كلاس Ca. أحتاج ملف .so للاستخراج الدقيق."
    except Exception as e:
        return f"❌ خطأ في الهيكل: {str(e)}"

# (أكمل إعدادات البوت لإرسال النتيجة للمستخدم عبر التليجرام)
