# api/telegram.py
import os
import json
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
from bot import (
    setup_webhook,
    TELEGRAM_BOT_TOKEN,
    start,
    command_new,
    command_see,
    handle_message,
    new_chat,
)

logger = logging.getLogger(__name__)

async def telegram_webhook(request):
    """Handles incoming requests from the Telegram webhook."""
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    await app.initialize()
    # Conversation handler setup (moved here for clarity)
    CHAT = 1 # Only need 1 "state"
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("new", command_new),
            CommandHandler("see", command_see),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        ],
        states={
          CHAT: [
              CommandHandler("new", command_new),
              CommandHandler("see", command_see),
              MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
          ]
        },
        fallbacks=[],  # No need for a cancel command, /new handles ending a chat
    )
    app.add_handler(conv_handler)

    # Webhook setup (only do this once)
    if not app.updater:  # Check if updater exists (first run)
        await setup_webhook(app)
        app.updater = True  # Dummy updater to mark as initialized


    try:
        data = json.loads(request)
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return "OK"  # Return a simple 200 OK response
    except Exception as e:
        print(f"Error in webhook handler: {e}")
        return "Internal Server Error", 500


async def handler(event, context):
    """AWS Lambda handler function (adapted for Vercel)."""
    return await telegram_webhook(event['body'])