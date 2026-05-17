import logging
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from config import TELEGRAM_TOKEN
from handlers.start import start_handler, handle_callback
from handlers.message import message_handler
from handlers.voice import voice_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("menu", start_handler))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("🚀 MegaLearnBot is running!")
    app.run_polling(drop_pending_updates=True)

async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import get_user
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    user = get_user(update.effective_user.id)
    text = (
        f"📊 *ההתקדמות שלך*\n\n"
        f"🔤 אנגלית — רמה {user['english_level']} | XP: {user['english_xp']}\n"
        f"🔢 מתמטיקה — רמה {user['math_level']} | XP: {user['math_xp']}\n"
        f"🔥 Streak: {user['streak']} ימים\n"
        f"✅ שיעורים שהושלמו: {user['lessons_done']}\n"
        f"⭐ ציון ממוצע: {user['avg_score']}%"
    )
    keyboard = [[InlineKeyboardButton("🏠 תפריט ראשי", callback_data="main_menu")]]
    await update.message.reply_text(text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database import reset_user
    reset_user(update.effective_user.id)
    await update.message.reply_text("♻️ הפרופיל שלך אופס. שלח /start כדי להתחיל מחדש.")

if __name__ == "__main__":
    main()
