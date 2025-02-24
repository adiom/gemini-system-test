# bot.py
import os
import datetime
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
)
import google.generativeai as genai
from dotenv import load_dotenv
import tempfile

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Missing environment variables: TELEGRAM_BOT_TOKEN and/or GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model_flash = genai.GenerativeModel('gemini-1.5-flash-8b')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

CHAT_LOGS_DIR = tempfile.mkdtemp(dir='/tmp')  # Create temp dir once

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initial bot greeting and command explanation."""
    logger.info(f"User {update.effective_user.id} started the bot.")
    await update.message.reply_text(
        "Hi! I'm your Gemini bot.\n"
        "/new - Start a new chat (and save/send the previous log)\n"
        "/see - View a summary of the current chat context"
    )

async def command_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /new command: sends previous log (if any) and prompts for system prompt."""
    logger.info(f"User {update.effective_user.id} requested a new chat.")
    await _send_previous_log(update, context)
    await update.message.reply_text("Enter the system prompt for the new chat (bot's role and tasks):")

async def _send_previous_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Helper function to send the chat log, if it exists."""
    chat_log_file = context.user_data.get('chat_log_file')
    if chat_log_file and os.path.exists(chat_log_file):
        try:
            with open(chat_log_file, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(chat_log_file),
                    caption="Previous chat log"
                )
            logger.info(f"Sent previous chat log to user {update.effective_user.id}")
        except Exception as e:
            logger.error(f"Error sending chat log: {e}")


async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Creates a new chat, sets the system prompt, and stores the log file path."""
    chat_id = update.effective_chat.id
    account_name = update.effective_user.username or str(update.effective_user.id)
    system_prompt = update.message.text
    logger.info(f"User {update.effective_user.id} set system prompt: {system_prompt}")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    chat_log_file = os.path.join(CHAT_LOGS_DIR, f"{account_name}-{chat_id}-{timestamp}.txt")

    with open(chat_log_file, "w", encoding="utf-8") as f:
        f.write(f"System Prompt: {system_prompt}\n\n")

    context.user_data['chat_log_file'] = chat_log_file
    await update.message.reply_text("New chat created! Send your messages.")



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes text messages, interacts with Gemini, and logs the conversation."""
    chat_log_file = context.user_data.get('chat_log_file')

    if not chat_log_file:
        await update.message.reply_text("Start a new chat with /new first.")
        return

    user_input = update.message.text
    logger.info(f"User {update.effective_user.id} sent message: {user_input}")

    with open(chat_log_file, "a", encoding="utf-8") as f:
        f.write(f"User: {user_input}\n")

    with open(chat_log_file, "r", encoding="utf-8") as f:
        chat_history = f.read()

    prompt_for_gemini = chat_history + "\nBot: "

    try:
        logger.info(f"Sending request to Gemini API for user {update.effective_user.id}")
        response = model_flash.generate_content(prompt_for_gemini)
        bot_reply = response.text

        with open(chat_log_file, "a", encoding="utf-8") as f:
            f.write(f"Bot: {bot_reply}\n")

        await _split_and_send_message(update, bot_reply)

    except Exception as e:
        logger.error(f"Error with Gemini API: {e}")
        await update.message.reply_text(f"Sorry, an error occurred: {e}")



async def _split_and_send_message(update: Update, text: str, max_length: int = 4096):
    """Splits long messages into chunks for Telegram's message limit."""
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        await update.message.reply_text(chunk)

async def command_see(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows a summary of the chat context and the full log."""
    chat_log_file = context.user_data.get('chat_log_file')

    if not chat_log_file or not os.path.exists(chat_log_file):
        await update.message.reply_text("No chat context found. Start a new chat with /new.")
        return

    with open(chat_log_file, "r", encoding="utf-8") as f:
        context_text = f.read()

    try:
        response = model_flash.generate_content(
            f"Summarize the topic of this conversation:\n\n{context_text}"
        )
        context_summary = response.text
    except Exception as e:
        logger.error(f"Error getting context summary from Gemini: {e}")
        context_summary = "Could not retrieve context summary."

    full_message = f"Chat Context Summary:\n\n{context_summary}\n\nFull Log:\n\n{context_text}"
    await _split_and_send_message(update, full_message)


async def setup_webhook(app):
    """Sets up the webhook on Vercel."""
    VERCEL_URL = os.getenv("VERCEL_URL")
    if not VERCEL_URL:
        raise ValueError("VERCEL_URL environment variable not set!")
    webhook_url = f"{VERCEL_URL}/api/telegram"
    await app.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")