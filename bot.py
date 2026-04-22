#!/usr/bin/env python3
"""
=====================================
  DarkTunnel Decryptor — Telegram Bot
=====================================
pip install python-telegram-bot pycryptodome
BOT_TOKEN=xxxx python dark_decryptor_bot.py
"""

import os, re, json, base64, logging, tempfile, traceback
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

_KEY_REF_B64 = "ZXCHn3veSKESmIQGY5dTv+Y5At4diIt6mZtYwgFH5dU="
_key_ref_bytes = base64.b64decode(_KEY_REF_B64)
DERIVED_KEY: bytes = bytes(b ^ 0x44 for b in _key_ref_bytes[4:20])

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_b64(s: str) -> str:
    s = s.replace("-", "+").replace("_", "/")
    pad = len(s) % 4
    if pad: s += "=" * (4 - pad)
    return s


def try_aes(ct: bytes, iv: bytes, key: bytes):
    try:
        return unpad(AES.new(key, AES.MODE_CBC, iv=iv).decrypt(ct), AES.block_size)
    except Exception:
        return None


def decrypt_payload(b64_payload: str) -> tuple[str, str]:
    raw = base64.b64decode(fix_b64(b64_payload))
    logger.info(f"decrypt | raw_len={len(raw)} | first16={raw[:16].hex()} | key={DERIVED_KEY.hex()}")

    zero_iv = b"\x00" * 16
    combos = []
    if len(raw) > 16:
        combos += [
            ("IV=first16 | CT=raw[16:]", raw[:16], raw[16:]),
            ("IV=zero    | CT=raw[16:]", zero_iv,  raw[16:]),
        ]
    combos.append(("IV=zero | CT=raw(full)", zero_iv, raw))

    for label, iv, ct in combos:
        result = try_aes(ct, iv, DERIVED_KEY)
        if result is not None:
            logger.info(f"SUCCESS: {label}")
            return result.decode("utf-8", errors="replace"), label

    diag = (
        f"حجم البيانات الخام : {len(raw)} بايت\n"
        f"أول 16 بايت (IV?)  : {raw[:16].hex()}\n"
        f"المفتاح المشتق     : {DERIVED_KEY.hex()}\n"
        f"المجموعات المُجرَّبة: {len(combos)} — جميعها فشلت"
    )
    raise ValueError(diag)


def parse_dark(content: str) -> dict:
    content = content.strip()

    m = re.match(r"(?i)darktunnel://(.+)", content)
    if m:
        inner = json.loads(base64.b64decode(fix_b64(m.group(1))).decode("utf-8"))
        enc = inner.get("encryptedLockedConfig", "")
        if enc:
            plain, method = decrypt_payload(enc)
        else:
            plain, method = json.dumps(inner, ensure_ascii=False, indent=2), "لا يوجد حقل مشفر"
        return {"source": "DarkTunnel URI", "type": inner.get("type","N/A"),
                "name": inner.get("name","N/A"), "method": method, "decrypted_config": plain}

    try:
        obj = json.loads(content)
        enc = obj.get("encryptedLockedConfig", "")
        if enc:
            plain, method = decrypt_payload(enc)
        else:
            plain, method = json.dumps(obj, ensure_ascii=False, indent=2), "لا حقل مشفر"
        return {"source": "JSON مباشر", "type": obj.get("type","N/A"),
                "name": obj.get("name","N/A"), "method": method, "decrypted_config": plain}
    except json.JSONDecodeError:
        pass

    plain, method = decrypt_payload(content)
    return {"source": "Base64 خام", "type": "N/A", "name": "N/A",
            "method": method, "decrypted_config": plain}


def build_output(info: dict) -> str:
    sep = "═" * 52
    return (
        f"{sep}\n  DarkTunnel Decryptor — النتيجة\n{sep}\n\n"
        f"المصدر      : {info['source']}\n"
        f"النوع (type): {info['type']}\n"
        f"الاسم (name): {info['name']}\n"
        f"الطريقة     : {info['method']}\n\n"
        f"{sep}\n  الإعدادات بعد فك التشفير\n{sep}\n\n"
        f"{info['decrypted_config']}\n\n{sep}\n"
    )


async def _process(update: Update, content: str, out_filename: str):
    out_tmp = None
    try:
        info = parse_dark(content)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as f:
            f.write(build_output(info))
            out_tmp = f.name
        await update.message.reply_document(
            document=open(out_tmp, "rb"), filename=out_filename,
            caption=f"✅ *تم!* النوع: `{info['type']}` | الاسم: `{info['name']}`",
            parse_mode="Markdown",
        )
    except ValueError as e:
        await update.message.reply_text(
            f"❌ *فشل فك التشفير*\n\n```\n{e}\n```\n\n"
            "💡 تحقق من صحة منطق اشتقاق المفتاح في `_KEY_REF_B64`.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(traceback.format_exc())
        await update.message.reply_text(f"❌ خطأ: `{e}`", parse_mode="Markdown")
    finally:
        if out_tmp:
            try: os.unlink(out_tmp)
            except: pass


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *DarkTunnel Decryptor Bot*\n\n"
        "📎 أرسل ملف `.dark` وسأعيد لك ملف `.txt` يحتوي الإعدادات المفكوكة.\n"
        "يُقبل أيضاً: رابط `darktunnel://...` أو JSON مباشر.", parse_mode="Markdown")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    fname = doc.file_name or "file.dark"
    await update.message.reply_text("⏳ جاري فك التشفير...")
    tmp = None
    try:
        tg_file = await doc.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dark") as t:
            await tg_file.download_to_drive(t.name)
            tmp = t.name
        with open(tmp, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
        await _process(update, content, fname.rsplit(".", 1)[0] + "_decrypted.txt")
    finally:
        if tmp:
            try: os.unlink(tmp)
            except: pass


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = update.message.text.strip()
    if content.startswith("/"): return
    await update.message.reply_text("⏳ جاري فك التشفير...")
    await _process(update, content, "decrypted_config.txt")


def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("عيّن BOT_TOKEN أولاً:\n  BOT_TOKEN=xxxx python dark_decryptor_bot.py")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("🤖 البوت يعمل — Ctrl+C للإيقاف")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
