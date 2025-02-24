import asyncio
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes

# Импортируем функции и переменные из основного файла бота (bot.py)
from bot import main, setup_webhook, TELEGRAM_BOT_TOKEN  # Убедитесь, что TELEGRAM_BOT_TOKEN тоже импортирован


# Настройка логирования (можно скопировать из bot.py, если там настроено иначе)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# Создаем экземпляр Application (вызываем main из bot.py)
# Важно: делаем это *вне* функции-обработчика, чтобы Application
# создавался только один раз при инициализации Serverless Function.
app: Application = main()


async def telegram_webhook_handler(req, res):
    """Обработчик для Vercel Serverless Function (Webhook)."""
    try:
        # Устанавливаем вебхук при первом запуске (и при каждом деплое)
        # Проверяем, был ли bot уже установлен (чтобы не вызывать set_webhook повторно)
        if not app.bot:  # app.bot становится доступен после setup_webhook
            await setup_webhook(app)
            logger.info("Webhook setup completed in Vercel function.") # Логируем успешную установку

        # Обрабатываем входящий запрос от Telegram
        data = await req.json()  # Получаем данные запроса как JSON
        update = Update.de_json(data, app.bot)  # Преобразуем JSON в объект Update
        await app.process_update(update)  # Обрабатываем обновление (вызываем handlers)

        return res.status(200).send("OK")  # Обязательно возвращаем 200 OK

    except Exception as e:
        logger.exception(f"Error in webhook handler: {e}") # Исп. logger.exception для полной трассировки
        return res.status(500).send("Internal Server Error")