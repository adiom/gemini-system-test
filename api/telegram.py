# api/telegram.py
import asyncio
from telegram import Update
from telegram.ext import Application, ContextTypes
from bot import main, setup_webhook

# Создаем экземпляр Application (вызываем main)
app: Application = main()
_setup_complete = False # Флаг, чтобы setup_webhook выполнился только один раз

async def telegram_webhook_handler(req, res):
    """Обработчик для Vercel Serverless Function."""
    global _setup_complete
    try:
        # Устанавливаем вебхук при первом запуске (и при каждом деплое)
        if not _setup_complete:
          await setup_webhook(app)
          _setup_complete = True

        # Обрабатываем входящий запрос от Telegram
        data = await req.json()  # Асинхронно читаем тело запроса
        update = Update.de_json(data, app.bot)
        await app.process_update(update)

        return res.status(200).send("OK")  # Обязательно возвращаем 200 OK

    except Exception as e:
        print(f"Error in webhook handler: {e}")  # Используйте print для логов в Vercel
        return res.status(500).send("Internal Server Error")

# Создаем асинхронную обертку для обработчика
async def handler(req, res):
  await telegram_webhook_handler(req, res)