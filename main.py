import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Set up logging so you can see errors in Render logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. Create a tiny web server (Flask) so Render's free tier stays awake
app = Flask('')

@app.route('/')
def home():
    return "Virus Card Bot is alive and running!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# 2. Your Telegram Card Stickers Database
CARDS = {
    "red_virus": "AAMCBAADGQEDnYq1asQ5pnJjjL7mbSUFbqMbUTNTdicAAnMdAAJbYRhSIX91MrMN-IgBAAdtAAM9BA",
    "red_organ": "AAMCBAADGQEDnYqtasQ5i373B8Ykcj6sXV31dD6hGgADJiQAAi7mGFI7Z885vQYEXgEAB20AAz0E"
}

# Telegram Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Welcome to the Virus! Game Bot on Render.")

async def test_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_sticker(
        chat_id=update.effective_chat.id,
        sticker=CARDS["red_virus"]
    )

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("No BOT_TOKEN found in environment variables!")

    # Build the Telegram bot
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('testcard', test_card))

    print("Bot polling started...")
    application.run_polling()

if __name__ == '__main__':
    # Start the web server in the background
    t = Thread(target=run_web)
    t.start()
    # Start the Telegram bot
    main()
