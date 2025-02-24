# api/telegram.py
import asyncio
from http.server import BaseHTTPRequestHandler
import json
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from bot import setup_webhook, TELEGRAM_BOT_TOKEN  # Импортируем только setup_webhook и токен

# Глобальная переменная для Application
app: Application = None
_setup_complete = False

class HttpRequestHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        global app, _setup_complete

        async def handle_post():
            global _setup_complete
            nonlocal self
            try:
                if app is None: # Создаем Application только при первом запросе
                    #Используем builder.build() и initialize/shutdown
                    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
                    await app.initialize()
                    # --- ConversationHandler ---
                    conv_handler = ConversationHandler(
                        entry_points=[
                            CommandHandler("start", self.start),
                            CommandHandler("new", self.command_new),
                            CommandHandler("see", self.command_see),
                        ],
                        states={
                            SELECTING_ACTION: [
                                CommandHandler("new", self.command_new),
                                CommandHandler("see", self.command_see),
                                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
                            ],
                            NEW_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.new_chat)],
                            CHATTING: [
                                CommandHandler("new", self.command_new),
                                CommandHandler("see", self.command_see),
                                MessageHandler(
                                    (filters.TEXT | filters.AUDIO | filters.PHOTO | filters.VOICE) & ~filters.COMMAND,
                                    self.handle_message,
                                ),
                            ],
                        },
                        fallbacks=[CommandHandler("cancel", self.cancel)],
                    )

                    app.add_handler(conv_handler)


                if not _setup_complete:
                    await setup_webhook(app)
                    _setup_complete = True

                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                update = Update.de_json(data, app.bot)
                await app.process_update(update)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')

            except Exception as e:
                print(f"Error in webhook handler: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Internal Server Error')

        asyncio.run(handle_post())

    def log_message(self, format, *args):
        # Переопределяем, чтобы избежать лишнего вывода в логи.
        return

    #----- Методы бота, адаптированные для использования внутри класса ------
    # Все методы, используемые в ConversationHandler, должны быть методами класса
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
      from bot import start
      await start(update, context)

    async def command_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
      from bot import command_new
      await command_new(update,context)

    async def command_see(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from bot import command_see
        await command_see(update, context)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from bot import handle_message
        await handle_message(update, context)

    async def new_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from bot import new_chat
        await new_chat(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from bot import cancel
        await cancel(update, context)

handler = HttpRequestHandler