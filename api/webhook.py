from flask import Flask, request
from telegram import Update
from telegram.ext import Application, ContextTypes
import sys
import os

# Добавляем родительскую директорию в путь для импорта bot.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bot import (
    command_new, command_see, handle_message, new_chat,
    SELECTING_ACTION, NEW_CHAT, CHATTING
)

app = Flask(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = '7920110758:AAGKs04L-L77Io1mNzG5SxJHvTpKgXSNW7s'
WEBHOOK_URL = 'https://gemini-system-test.vercel.app'  # Замените на ваш URL

# Инициализация бота
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Регистрация обработчиков
async def setup():
    # Инициализация приложения
    await application.initialize()
    
    # Установка вебхука
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    
    # Регистрация обработчиков команд и сообщений
    from telegram.ext import CommandHandler, MessageHandler, filters
    application.add_handler(CommandHandler("new", command_new))
    application.add_handler(CommandHandler("see", command_see))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# [api/webhook.py](api/webhook.py)
@app.route('/webhook', methods=['POST'])
async def webhook():
    """Обработчик вебхуков от Telegram."""
    # Проверяем, инициализировано ли приложение
    if not getattr(application, '_is_initialized', False):
        await application.initialize()        
    update = Update.de_json(request.get_json(), application.bot)
    await application.process_update(update)
    return "ok"

@app.route('/')
def home():
    """Простая проверка работоспособности."""
    return 'Bot is running'

# Запуск setup при старте
if __name__ == '__main__':
    import asyncio
    asyncio.run(setup())
    app.run(port=8000)
