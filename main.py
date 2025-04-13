import os
import subprocess
import asyncio
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, CallbackContext, CallbackQueryHandler
)

TOKEN = "7702849773:AAGCjm804HsmISojzBamKUtGjOzVODhDKAw"
ADMIN_ID = 7435809888

TEMP_FILE = "test.py"
PROCESS = None
BLOCKED_USERS = set()
USER_MESSAGES = {}
MISUSE_USERS = {}

REQUIRED_LIBS = ['apscheduler', 'requests', 'flask']

async def install_missing_libs():
    missing = []
    for lib in REQUIRED_LIBS:
        try:
            __import__(lib)
        except ImportError:
            missing.append(lib)
    if missing:
        subprocess.call(['pip', 'install'] + missing)

def get_start_text(name: str, is_admin=False):
    text = f"""/start
استضافة بايثون | py:
مرحباً، {name}! 👋✨

📄 من فضلك، أرسل ملف (.py) الذي ترغب في تشغيله.
"""
    buttons = [
        [InlineKeyboardButton("📤 رفع ملف", callback_data="upload")],
        [InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/T6GIO")]
    ]
    if is_admin:
        buttons.insert(0, [InlineKeyboardButton("👥 عرض المستخدمين", callback_data="show_users")])
    return text, InlineKeyboardMarkup(buttons)

def get_admin_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ قياس سرعة البوت", callback_data="ping")]
    ])

async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or "مستخدم"

    if user_id in BLOCKED_USERS:
        await update.message.reply_text("❌ تم حظرك من استخدام البوت.")
        return

    if user_id not in USER_MESSAGES:
        msg = f"👤 مستخدم جديد\nالاسم: {user_name}\nالمعرف: @{update.effective_user.username or 'None'}\nالآيدي: {user_id}"
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)

    USER_MESSAGES[user_id] = update.message.text or "/start"
    is_admin = user_id == ADMIN_ID
    text, markup = get_start_text(user_name, is_admin)
    await update.message.reply_text(text, reply_markup=markup)

async def admin(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ الأمر مخصص للأدمن فقط.")
        return
    await update.message.reply_text("لوحة التحكم:", reply_markup=get_admin_buttons())

async def admin_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ هذا الزر مخصص للأدمن فقط.")
        return
    if query.data == "ping":
        start_time = time.time()
        sent_msg = await query.message.reply_text("⏳ جاري القياس ...")
        end_time = time.time()
        latency = round((end_time - start_time) * 1000)
        await sent_msg.edit_text(f"⚡ السرعة: {latency}ms")

async def extra_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "upload":
        await query.message.reply_text("📥 أرسل ملف بايثون المراد رفعه!")
    elif query.data == "show_users":
        if user_id != ADMIN_ID:
            await query.message.reply_text("❌ هذا الخيار للأدمن فقط.")
            return
        users_list = "\n".join([f"- {uid}" for uid in USER_MESSAGES])
        await query.message.reply_text(f"👥 المستخدمون:\n{users_list or 'لا يوجد مستخدمون بعد.'}")

async def block(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للأدمن فقط.")
        return
    if not context.args:
        await update.message.reply_text("❗ استخدم الأمر:\n/block USER_ID")
        return
    uid = int(context.args[0])
    BLOCKED_USERS.add(uid)
    await update.message.reply_text(f"✅ تم حظر المستخدم {uid}")
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"🚫 تم حظر المستخدم يدويًا:\nID: {uid}")

async def unblock(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للأدمن فقط.")
        return
    if not context.args:
        await update.message.reply_text("❗ استخدم الأمر:\n/unblock USER_ID")
        return
    uid = int(context.args[0])
    if uid in BLOCKED_USERS:
        BLOCKED_USERS.remove(uid)
        await update.message.reply_text(f"♻️ تم فك الحظر عن المستخدم {uid}")
    else:
        await update.message.reply_text("هذا المستخدم غير محظور.")

async def handle_file(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id in BLOCKED_USERS:
        await update.message.reply_text("❌ تم حظرك من استخدام البوت.")
        return

    if USER_MESSAGES.get(user_id) == "file_sent":
        MISUSE_USERS[user_id] = MISUSE_USERS.get(user_id, 0) + 1
        if MISUSE_USERS[user_id] >= 3:
            BLOCKED_USERS.add(user_id)
            await update.message.reply_text("❌ تم حظرك لتكرار الإرسال.")
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"🚫 تم حظر المستخدم لتكرار الإرسال:\nID: {user_id}")
            return
    USER_MESSAGES[user_id] = "file_sent"

    file = update.message.document
    if not file.file_name.endswith('.py'):
        await update.message.reply_text("❌ الملف المرسل ليس بامتداد .py")
        return

    new_file = await file.get_file()
    await new_file.download_to_drive(TEMP_FILE)

    await update.message.reply_text("📦 المكتبات المطلوبة:\n" + "\n".join(REQUIRED_LIBS))
    await install_missing_libs()
    await asyncio.sleep(2)

    await update.message.reply_text("✅ تم تثبيت المكتبات.\n🚀 جارٍ التشغيل ...", reply_markup=get_buttons(running=True))
    await run_file(update)

async def run_file(update: Update):
    global PROCESS
    if PROCESS:
        await update.message.reply_text("⚠️ البوت يعمل بالفعل.")
        return
    PROCESS = subprocess.Popen(["python", TEMP_FILE])

async def stop_bot(update: Update, context: CallbackContext):
    global PROCESS
    if PROCESS:
        PROCESS.terminate()
        PROCESS = None
        await update.callback_query.message.reply_text("✅ تم إيقاف البوت.", reply_markup=get_buttons(running=False))
    else:
        await update.callback_query.message.reply_text("❌ لا يوجد بوت يعمل حالياً.")

def get_buttons(running=False):
    if running:
        return InlineKeyboardMarkup([[InlineKeyboardButton("✅ إيقاف البوت", callback_data="stop")]])
    else:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🚀 تشغيل البوت", callback_data="run")]])

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data in ["upload", "show_users"]:
        await extra_buttons(update, context)
        return

    if query.from_user.id != ADMIN_ID:
        await query.message.reply_text("❌ هذا الزر مخصص للأدمن فقط.")
        return

    if query.data == "stop":
        await stop_bot(update, context)
    elif query.data == "run":
        await query.message.reply_text("🚀 جارٍ تشغيل البوت ...", reply_markup=get_buttons(running=True))
        await run_file(update)
    elif query.data == "ping":
        await admin_buttons(update, context)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("block", block))
    app.add_handler(CommandHandler("unblock", unblock))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("BOT STARTED")
    app.run_polling()
