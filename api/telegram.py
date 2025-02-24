# api/telegram.py
import asyncio
from telegram import Update
from telegram.ext import Application, ContextTypes
from bot import main, setup_webhook
from http.server import BaseHTTPRequestHandler  # Импортируем BaseHTTPRequestHandler
import json

# Создаем экземпляр Application (вызываем main)
app: Application = main()
_setup_complete = False # Флаг для однократного вызова setup_webhook


class TelegramWebhookHandler(BaseHTTPRequestHandler):
    """Обработчик для Vercel Serverless Function."""

    def do_POST(self):
        """Обрабатывает POST-запросы от Telegram."""
        global _setup_complete
        try:
            # Устанавливаем вебхук при первом запуске (и при каждом деплое)
            if not _setup_complete:
                asyncio.run(setup_webhook(app)) # Используем asyncio.run, т.к. это синхронная функция
                _setup_complete = True

            # Обрабатываем входящий запрос от Telegram
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))  # Декодируем в UTF-8
            update = Update.de_json(data, app.bot)

            # Запускаем обработку обновления в асинхронном цикле
            asyncio.run(app.process_update(update))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK") # Обязательно возвращаем 200 OK

        except Exception as e:
            print(f"Error in webhook handler: {e}")  # Логируем ошибки
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")
    def log_message(self, format, *args):
        # Переопределяем, чтобы избежать лишнего вывода в логи.
        return

# Vercel entry point
handler = TelegramWebhookHandler