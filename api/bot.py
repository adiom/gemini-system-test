from http.server import BaseHTTPRequestHandler
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Replace with your actual bot token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! I'm your Telegram bot hosted on Vercel.")

async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello, {update.effective_user.first_name}!")

# Initialize bot application
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("hello", hello))

async def handle_update(request_body):
    """Process incoming webhook update"""
    try:
        update = Update.de_json(json.loads(request_body), application.bot)
        await application.process_update(update)
        return {"statusCode": 200, "body": "OK"}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}

def handler(event, context):
    """Vercel serverless function handler"""
    if event.get('body'):
        return handle_update(event['body'])
    return {"statusCode": 200, "body": "OK"}