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

async def handler(event, context):  # event - это весь HTTP-запрос
    """Handles incoming requests from the Telegram webhook."""

    # Инициализируем приложение Telegram
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    await app.initialize()

    # Обработчик диалогов
    CHAT = 1
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
        fallbacks=[],
    )
    app.add_handler(conv_handler)

    # Настройка вебхука (только при первом запуске)
    if not app.updater:
        await setup_webhook(app)
        app.updater = True  # Флаг, что вебхук настроен

    try:
        # Разбираем тело запроса (оно в event['body'])
        data = json.loads(event['body'])
        update = Update.de_json(data, app.bot)
        await app.process_update(update)

        # Возвращаем стандартный ответ для serverless-функций
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/plain'
            },
            'body': 'OK'
        }

    except Exception as e:
        print(f"Error in webhook handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'text/plain'
            },
            'body': 'Internal Server Error'
        }