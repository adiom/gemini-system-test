# api/telegram.py
import asyncio
from http.server import BaseHTTPRequestHandler
import json
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from bot import setup_webhook, TELEGRAM_BOT_TOKEN, start, command_new, command_see, handle_message, new_chat, cancel #Импортируем все методы

class HttpRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = None  # Инициализируем self.app в конструкторе
        self._setup_complete = False

    def do_POST(self):

        async def handle_post():
            nonlocal self
            try:
                if self.app is None:
                    self.app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
                    await self.app.initialize()
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
                    self.app.add_handler(conv_handler)

                if not self._setup_complete:
                    await setup_webhook(self.app)
                    self._setup_complete = True

                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                update = Update.de_json(data, self.app.bot)
                await self.app.process_update(update)

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
        return

    #----- Методы бота, адаптированные для использования внутри класса ------
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await start(update, context)

    async def command_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await command_new(update, context)

    async def command_see(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await command_see(update, context)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await handle_message(update, context)

    async def new_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await new_chat(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await cancel(update, context)

handler = HttpRequestHandler