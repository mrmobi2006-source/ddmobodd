#!/usr/bin/env python3
"""
=====================================
  DarkTunnel Decryptor — Telegram Bot
  يفك تشفير ملفات .dark ويعيد ملف .txt
=====================================

المتطلبات:
    pip install python-telegram-bot pycryptodome

التشغيل:
    python dark_decryptor_bot.py
"""

import os
import re
import json
import base64
import logging
import tempfile
import traceback

from telegram import Update, Document
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ─────────────────────────────────────────────
#  ⚙️  الإعدادات — عدّل هذا القسم فقط
# ─────────────────────────────────────────────

BOT_TOKEN = "8690128803:AAHyf-UhR-lf2HS02hG02zXyEa2_65VLe1k"          # <── ضع توكن البوت هنا (لا تشاركه مع أحد)

# ─── اشتقاق المفتاح الحقيقي ───
# النص المرجعي → Base64 decode → slice [4:20] → XOR كل بايت مع 0x44
_KEY_REF_B64 = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
_key_ref_bytes = base64.b64decode(_KEY_REF_B64)
DERIVED_KEY: bytes = bytes(b ^ 0x44 for b in _key_ref_bytes[4:20])

# قائمة المفاتيح للتجربة (المشتق أولاً)
AES_KEYS: list[bytes] = [DERIVED_KEY]

# ─────────────────────────────────────────────
#  📋  تهيئة السجل
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
#  🔓  منطق فك التشفير
# ══════════════════════════════════════════════

def fix_base64_padding(s: str) -> str:
    """يُصلح ترميز Base64 URL-safe ويضيف padding ناقصاً."""
    s = s.replace("-", "+").replace("_", "/")
    pad = len(s) % 4
    if pad:
        s += "=" * (4 - pad)
    return s


def try_decrypt(ciphertext: bytes, iv: bytes, key: bytes) -> bytes | None:
    """يحاول فك التشفير بمفتاح محدد، ويُعيد None عند الفشل."""
    try:
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        raw = cipher.decrypt(ciphertext)
        return unpad(raw, AES.block_size)
    except Exception:
        return None


def decrypt_payload(b64_payload: str) -> tuple[str, str]:
    """
    يفك ترميز Base64 ثم يفك تشفير AES-CBC.
    يُعيد (plaintext, method_used).
    يرفع ValueError إذا فشلت كل المحاولات.
    """
    raw = base64.b64decode(fix_base64_padding(b64_payload))

    # — المحاولة 1: IV من أول 16 بايت —
    if len(raw) > 16:
        iv, ciphertext = raw[:16], raw[16:]
        for key in AES_KEYS:
            plain = try_decrypt(ciphertext, iv, key)
            if plain:
                return plain.decode("utf-8", errors="replace"), f"AES-CBC | IV=first 16 bytes | key={key!r}"

    # — المحاولة 2: IV صفري (Zero IV) —
    zero_iv = b"\x00" * 16
    for key in AES_KEYS:
        plain = try_decrypt(raw, zero_iv, key)
        if plain:
            return plain.decode("utf-8", errors="replace"), f"AES-CBC | IV=Zero | key={key!r}"

    raise ValueError("فشل فك التشفير — لم ينجح أي مفتاح أو IV.")


def parse_dark_content(content: str) -> dict:
    """
    يقبل:
      • URI: darktunnel://[Base64]
      • JSON خام
      • نص Base64 مباشر
    يُعيد قاموساً بالحقول المستخرجة.
    """
    result = {}

    content = content.strip()

    # ─── حالة 1: URI ───
    uri_match = re.match(r"(?i)darktunnel://(.+)", content)
    if uri_match:
        b64 = uri_match.group(1)
        decoded_bytes = base64.b64decode(fix_base64_padding(b64))
        inner = json.loads(decoded_bytes.decode("utf-8"))
        result.update({
            "source": "DarkTunnel URI",
            "type": inner.get("type", "N/A"),
            "name": inner.get("name", "N/A"),
        })
        enc = inner.get("encryptedLockedConfig", "")
        if enc:
            plain, method = decrypt_payload(enc)
            result["decrypted_config"] = plain
            result["method"] = method
        else:
            result["decrypted_config"] = json.dumps(inner, ensure_ascii=False, indent=2)
            result["method"] = "لا يوجد حقل مشفر — تم استخراج JSON مباشرة"
        return result

    # ─── حالة 2: JSON خام ───
    try:
        obj = json.loads(content)
        result.update({
            "source": "JSON مباشر",
            "type": obj.get("type", "N/A"),
            "name": obj.get("name", "N/A"),
        })
        enc = obj.get("encryptedLockedConfig", "")
        if enc:
            plain, method = decrypt_payload(enc)
            result["decrypted_config"] = plain
            result["method"] = method
        else:
            result["decrypted_config"] = json.dumps(obj, ensure_ascii=False, indent=2)
            result["method"] = "لا يوجد حقل مشفر"
        return result
    except json.JSONDecodeError:
        pass

    # ─── حالة 3: Base64 خام ───
    plain, method = decrypt_payload(content)
    result.update({
        "source": "Base64 خام",
        "type": "N/A",
        "name": "N/A",
        "decrypted_config": plain,
        "method": method,
    })
    return result


def format_output(info: dict) -> str:
    """يُنسّق النتيجة كنص مرتب للحفظ في .txt"""
    sep = "═" * 50
    return f"""{sep}
  DarkTunnel Decryptor — النتيجة
{sep}

المصدر     : {info.get('source', 'N/A')}
النوع (type): {info.get('type', 'N/A')}
الاسم (name): {info.get('name', 'N/A')}
الطريقة    : {info.get('method', 'N/A')}

{sep}
  ✅ الإعدادات بعد فك التشفير
{sep}

{info.get('decrypted_config', '')}

{sep}
"""


# ══════════════════════════════════════════════
#  🤖  معالجات الأوامر والرسائل
# ══════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *مرحباً في DarkTunnel Decryptor Bot*\n\n"
        "📎 أرسل لي ملف بصيغة `.dark` وسأفك تشفيره وأعيد لك ملف `.txt` بالإعدادات المستخرجة.\n\n"
        "يمكنك أيضاً إرسال:\n"
        "• رابط `darktunnel://...`\n"
        "• JSON مباشر يحتوي على `encryptedLockedConfig`",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *طريقة الاستخدام:*\n\n"
        "1️⃣ أرسل ملف `.dark` كمرفق\n"
        "2️⃣ أو أرسل محتوى الملف كنص\n\n"
        "*الصيغ المدعومة:*\n"
        "• `darktunnel://[Base64]`\n"
        "• JSON يحتوي على `encryptedLockedConfig`\n"
        "• Base64 خام\n\n"
        "⚙️ البوت يجرب تلقائياً عدة مفاتيح و IV للوصول إلى البيانات.",
        parse_mode="Markdown",
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يعالج الملفات المُرسَلة."""
    doc: Document = update.message.document
    fname = doc.file_name or "unknown"

    if not (fname.endswith(".dark") or fname.endswith(".txt") or fname.endswith(".json")):
        await update.message.reply_text(
            f"⚠️ الملف `{fname}` غير مدعوم مباشرة، لكن سأحاول معالجته كنص...",
            parse_mode="Markdown",
        )

    await update.message.reply_text("⏳ جاري فك التشفير...")

    try:
        tg_file = await doc.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dark") as tmp:
            await tg_file.download_to_drive(tmp.name)
            tmp_path = tmp.name

        with open(tmp_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()

        info = parse_dark_content(content)
        output_text = format_output(info)

        # حفظ النتيجة في ملف مؤقت وإرساله
        out_name = fname.replace(".dark", "") + "_decrypted.txt"
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".txt", mode="w", encoding="utf-8"
        ) as out_tmp:
            out_tmp.write(output_text)
            out_tmp_path = out_tmp.name

        await update.message.reply_document(
            document=open(out_tmp_path, "rb"),
            filename=out_name,
            caption=f"✅ *تم فك التشفير بنجاح!*\n📄 النوع: `{info.get('type','N/A')}` | الاسم: `{info.get('name','N/A')}`",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            f"❌ *خطأ أثناء المعالجة:*\n`{e}`\n\n"
            "تأكد أن الملف بالصيغة الصحيحة أو جرب إرسال محتوى الملف كنص.",
            parse_mode="Markdown",
        )
    finally:
        for p in [tmp_path, out_tmp_path]:
            try:
                os.unlink(p)
            except Exception:
                pass


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """يعالج النص المُرسَل مباشرة."""
    content = update.message.text.strip()

    if content.startswith("/"):
        return  # تجاهل الأوامر غير المعرَّفة

    await update.message.reply_text("⏳ جاري فك التشفير...")

    try:
        info = parse_dark_content(content)
        output_text = format_output(info)

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".txt", mode="w", encoding="utf-8"
        ) as out_tmp:
            out_tmp.write(output_text)
            out_tmp_path = out_tmp.name

        await update.message.reply_document(
            document=open(out_tmp_path, "rb"),
            filename="decrypted_config.txt",
            caption=f"✅ *تم فك التشفير!*\nالنوع: `{info.get('type','N/A')}` | الاسم: `{info.get('name','N/A')}`",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            f"❌ *خطأ:* `{e}`",
            parse_mode="Markdown",
        )
    finally:
        try:
            os.unlink(out_tmp_path)
        except Exception:
            pass


# ══════════════════════════════════════════════
#  🚀  نقطة الدخول
# ══════════════════════════════════════════════

def main() -> None:
    token = os.environ.get("BOT_TOKEN", BOT_TOKEN)
    if token == "YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "❌ لم يتم تعيين BOT_TOKEN!\n"
            "• عدّل المتغير BOT_TOKEN في الكود، أو\n"
            "• شغّل البوت بـ: BOT_TOKEN=xxxx python dark_decryptor_bot.py"
        )

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🤖 البوت يعمل الآن... اضغط Ctrl+C للإيقاف.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
