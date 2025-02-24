import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Replace with your actual bot token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! I'm your Telegram bot hosted on Vercel.")

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello, {update.effective_user.first_name}!")

async def webhook(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Create an application instance
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("hello", hello))

    # Process the update
    await application.process_update(update)

    return "OK"

# For local testing
if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("hello", hello))
    application.run_polling()