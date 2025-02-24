# bot.py
import os
import datetime
import logging
from telegram import Update, ReplyKeyboardMarkup, File
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    Application  # Application нужен для type hinting
)
import google.generativeai as genai
from dotenv import load_dotenv
import tempfile  # Добавлено

# Загружаем переменные окружения из .env файла (если он есть)
load_dotenv()

# Настройки (берем из переменных окружения)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверяем, что переменные окружения заданы
if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Не заданы переменные окружения TELEGRAM_BOT_TOKEN и/или GEMINI_API_KEY")

# Инициализация Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model_flash = genai.GenerativeModel('gemini-1.5-flash-8b')  # Модель Flash

# Состояния для ConversationHandler
SELECTING_ACTION, NEW_CHAT, CHATTING = range(3)

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Временная папка для логов
CHAT_LOGS_DIR = tempfile.mkdtemp(dir='/tmp')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое сообщение со списком команд."""
    logger.info(f"User {update.effective_user.id} started the bot")
    await update.message.reply_text(
        "Привет! Я ваш Gemini бот. Доступные команды:\n"
        "/new - Создать новый чат\n"
        "/see - Посмотреть контекст\n"
        "Отправьте любое сообщение для начала общения (текст, аудио, фото)"
    )
    return SELECTING_ACTION


async def command_see(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /see."""
    logger.info(f"User {update.effective_user.id} used /see command")
    return await view_context(update, context)


async def command_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /new."""
    logger.info(f"User {update.effective_user.id} used /new command")

    # Отправляем текущий лог, если он есть
    chat_log_file = context.user_data.get('chat_log_file')
    if chat_log_file and os.path.exists(chat_log_file):
        try:
            with open(chat_log_file, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(chat_log_file),
                    caption="Лог предыдущего чата"
                )
            logger.info(f"Previous chat log sent to user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error sending chat log: {e}")

    await update.message.reply_text("Введите system prompt для нового чата (описание роли и задач бота):")
    return NEW_CHAT


async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора действия."""
    user_choice = update.message.text
    logger.info(f"User {update.effective_user.id} chose action: {user_choice}")

    if user_choice == "Создать новый чат":
        # Прощальное сообщение перед созданием нового чата
        await update.message.reply_text("Завершаю текущий чат и начинаем новый!")
        await update.message.reply_text("Введите system prompt для нового чата (описание роли и задач бота):")
        return NEW_CHAT
    elif user_choice == "Посмотреть контекст":
        await view_context(update, context)  # Вызываем view_context напрямую
        reply_keyboard = [["Посмотреть контекст", "Создать новый чат"]]  # Предлагаем выбор действий снова
        await update.message.reply_text(
            "Выберите следующее действие:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return SELECTING_ACTION  # Возвращаемся к выбору действия
    else:
        reply_keyboard = [["Посмотреть контекст", "Создать новый чат"]]
        await update.message.reply_text(
            "Не понял ваш выбор. Пожалуйста, выберите действие из кнопок:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return SELECTING_ACTION


async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание нового чата с system prompt."""
    chat_id = update.effective_chat.id
    account_name = update.effective_user.username or str(
        update.effective_user.id)  # Имя пользователя Telegram или ID
    system_prompt = update.message.text
    logger.info(f"User {update.effective_user.id} set system prompt: {system_prompt}")

    # Создаем уникальное имя файла
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    chat_log_file = os.path.join(CHAT_LOGS_DIR, f"{account_name}-{chat_id}-{timestamp}.txt")

    # Записываем system prompt в файл
    with open(chat_log_file, "w", encoding="utf-8") as f:
        f.write(f"System Prompt: {system_prompt}\n\n")

    # Сохраняем путь к файлу в контексте пользователя и устанавливаем состояние CHATTING
    context.user_data['chat_log_file'] = chat_log_file
    await update.message.reply_text("Новый чат создан! Теперь вы можете отправлять сообщения.")
    return CHATTING  # Переходим в состояние CHATTING, чтобы обрабатывать сообщения


async def transcribe_audio_gemini_api(audio_file: File) -> str or None:
    """Транскрибирует аудиофайл, используя Gemini API."""
    logger.info("Starting audio transcription using Gemini API")
    try:
        audio_data = await audio_file.download_as_bytes()

        # Попытка отправить аудио данные в Gemini как бинарные данные
        contents = [{
            "parts": [{"text": "Преобразуй это аудио в текст:"},
                      {"mime_type": "audio/ogg", "data": audio_data}]  # mime_type - нужно уточнить
        }]

        response = model_flash.generate_content(contents=contents)  # Отправляем запрос с аудио данными

        if response.text:
            transcribed_text = response.text
            logger.info("Audio transcription successful using Gemini API")
            return transcribed_text
        else:
            logger.warning("Gemini API returned empty response for audio transcription.")
            return None

    except Exception as e:
        logger.error(f"Error during audio transcription using Gemini API: {e}")
        return None


async def split_and_send_message(update: Update, text: str, max_length: int = 4096):
    """Разделяет длинное сообщение на части и отправляет их последовательно."""
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        await update.message.reply_text(chunk)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений с учетом контекста."""
    chat_id = update.effective_chat.id
    chat_log_file = context.user_data.get('chat_log_file')

    if not chat_log_file:
        await update.message.reply_text("Сначала создайте новый чат, используя команду /new")
        return SELECTING_ACTION

    user_input = None
    message_type = "текст"

    if update.message.text:
        user_input = update.message.text
        message_type = "текст"
    # Временно отключаем обработку аудио
    elif update.message.voice:
      message_type = "голосовое сообщение"
      await update.message.reply_text("Извините, обработка голосовых сообщений временно отключена.")
      return CHATTING
    elif update.message.audio:
      message_type = "аудио файл"
      await update.message.reply_text("Извините, обработка аудиофайлов временно отключена.")
      return CHATTING
    elif update.message.photo:
        user_input = "Фотография"  # Обработка фото
        message_type = "фото"
    else:
        await update.message.reply_text("Поддерживаются только текст, аудио и фото.")
        return CHATTING

    if user_input is None:  # Если не удалось получить user_input
        return CHATTING

    logger.info(f"User {update.effective_user.id} sent message ({message_type}): {user_input}")

    # Логируем сообщение пользователя
    with open(chat_log_file, "a", encoding="utf-8") as f:
        f.write(f"User ({message_type}): {user_input}\n")

    # Загружаем историю чата
    with open(chat_log_file, "r", encoding="utf-8") as f:
        chat_history = f.read()

    prompt_for_gemini = chat_history + f"\nUser ({message_type}): {user_input}\nBot: "

    try:
        logger.info(f"Sending request to Gemini API with context for user {update.effective_user.id}")
        response = model_flash.generate_content(prompt_for_gemini)
        logger.info(f"Gemini API response received for user {update.effective_user.id}")
        bot_reply = response.text

        with open(chat_log_file, "a", encoding="utf-8") as f:
            f.write(f"Bot: {bot_reply}\n")

        await split_and_send_message(update, bot_reply)

    except Exception as e:
        logger.error(f"Ошибка при обращении к Gemini API: {e}")
        await update.message.reply_text(f"Извините, произошла ошибка: {e}")

    return CHATTING


async def view_context(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает контекст текущего чата."""
    chat_id = update.effective_chat.id
    chat_log_file = context.user_data.get('chat_log_file')

    if not chat_log_file or not os.path.exists(chat_log_file):
        await update.message.reply_text("Контекст пуст или чат не создан. Сначала создайте новый чат.")
        return SELECTING_ACTION  # Возвращаемся в меню

    with open(chat_log_file, "r", encoding="utf-8") as f:
        context_text = f.read()

    try:
        response = model_flash.generate_content(
            f"Кратко опиши тему текущего диалога, основываясь на следующем контексте:\n\n{context_text}")
        context_summary = response.text
    except Exception as e:
        logger.error(f"Ошибка при запросе summary контекста к Gemini API: {e}")
        context_summary = "Не удалось получить описание контекста."

    full_message = f"Краткое описание контекста чата:\n\n{context_summary}\n\nПолный контекст:\n\n{context_text}"
    await split_and_send_message(update, full_message)
    return SELECTING_ACTION


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего действия."""
    logger.info(f"User {update.effective_user.id} cancelled action")
    await update.message.reply_text("Действие отменено.")
    return SELECTING_ACTION


async def setup_webhook(app: Application):  # Аннотация типов
    """Настройка webhook."""
    WEBHOOK_URL = f"{os.getenv('VERCEL_URL')}/api/telegram"  # Используем переменную VERCEL_URL
    await app.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"Webhook set to: {WEBHOOK_URL}")