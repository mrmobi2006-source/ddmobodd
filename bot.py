import base64
import json
from Crypto.Cipher import AES

def universal_decrypt(payload):
    # قائمة بالمفاتيح المحتملة (المستخرجة من تحليل تطبيقات مشابهة)
    possible_keys = [
        # المفتاح الذي استخرجناه (ربما يحتاج تعديل)
        bytes([b ^ 68 for b in base64.b64decode("ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU=")[4:20]]),
        # مفاتيح افتراضية يستخدمها مطورو Go-V2Ray
        b"1234567890123456", 
        b"darktunnel_key_v",
        b"v2ray_secret_key"
    ]

    payload = payload.replace('-', '+').replace('_', '/')
    try:
        raw_data = base64.b64decode(payload + '=' * (-len(payload) % 4))
        iv = raw_data[:16]
        ciphertext = raw_data[16:]
        
        # قص الزوائد لتناسب AES
        ciphertext = ciphertext[:(len(ciphertext) // 16) * 16]

        for key in possible_keys:
            try:
                cipher = AES.new(key, AES.MODE_CBC, iv)
                dec = cipher.decrypt(ciphertext)
                # إذا وجدنا أي كلمة تدل على V2Ray مثل "vless" أو "host"
                if b"vless" in dec.lower() or b"host" in dec.lower() or b"uuid" in dec.lower():
                    return dec.decode('utf-8', errors='ignore').strip()
            except:
                continue
        return "❌ لم ينجح أي مفتاح محتمل."
    except Exception as e:
        return f"❌ خطأ في البنية: {str(e)}"

# انسخ الرابط الحقيقي الذي نجح مع البوتات الأخرى وضعه هنا للتجربة
link = "ضع_الرابط_هنا"
if "darktunnel://" in link:
    inner_b64 = json.loads(base64.b64decode(link.split("://")[1])).get("encryptedLockedConfig")
    print(universal_decrypt(inner_b64))
