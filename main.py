import os
import logging
import random
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

app = Flask('')
@app.route('/')
def home():
    return "Virus Card Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# Full Sticker Database from your list
CARDS = {
    "red_organ": "AAMCBAADGQEDnYqtasQ5i373B8Ykcj6sXV31dD6hGgADJiQAAi7mGFI7Z885vQYEXgEAB20AAz0E",
    "green_organ": "AAMCBAADGQEDnYqbasQ5YLE4wRDssCR3Rs7l0Ojzrw0AAoQgAALGpxlScxmhRIeaqioBAAdtAAM9BA",
    "red_virus": "AAMCBAADGQEDnYq1asQ5pnJjjL7mbSUFbqMbUTNTdicAAnMdAAJbYRhSIX91MrMN-IgBAAdtAAM9BA",
    "red_medicine": "AAMCBAADGQEDnYqxasQ5mZXIIHCp3j0eH9celDLcMbEAAm8gAALD-RlSjGTPYyWfvioBAAdtAAM9BA"
}

# Game State Variables
game_in_progress = False
players = []  # List of player usernames/IDs
player_hands = {} # {user_id: [card1, card2, card3]}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to **Virus!** 🦠\n\n"
        "Commands:\n"
        "/join - Join the game lobby\n"
        "/startgame - Start the match once everyone has joined!"
    )

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_in_progress
    if game_in_progress:
        await update.message.reply_text("A game is already running! Wait for it to finish.")
        return

    user = update.effective_user
    user_name = user.first_name

    if user.id not in players:
        players.append(user.id)
        await update.message.reply_text(f"✅ {user_name} has joined the game! Total players: {len(players)}")
    else:
        await update.message.reply_text(f"You're already in the lobby, {user_name}!")

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_in_progress
    if len(players) < 2:
        await update.message.reply_text("⚠️ You need at least 2 players to start a game! Type /join first.")
        return

    game_in_progress = True
    await update.message.reply_text(
        f"🎮 **The Virus! game has officially started with {len(players)} players!**\n"
        "Let the infection begin..."
    )

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("No BOT_TOKEN found in environment variables!")

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('join', join_game))
    application.add_handler(CommandHandler('startgame', start_game))

    print("Bot polling started...")
    application.run_polling()

if __name__ == '__main__':
    t = Thread(target=run_web)
    t.start()
    main()
