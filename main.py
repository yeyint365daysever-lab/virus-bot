import os
import random
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Keep-alive web server for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Virus! Bot is active!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# ---------------------------------------------------------
# STICKER FILE IDs & GAME ASSETS MAPPING
# ---------------------------------------------------------
# Replace these placeholder file_ids with your actual custom sticker file_ids
STICKERS = {
    # Organs
    "organ_red": "CAACAgIAAxkBAA...",
    "organ_blue": "CAACAgIAAxkBAA...",
    "organ_green": "CAACAgIAAxkBAA...",
    "organ_yellow": "CAACAgIAAxkBAA...",
    # Viruses
    "virus_red": "CAACAgIAAxkBAA...",
    "virus_blue": "CAACAgIAAxkBAA...",
    "virus_green": "CAACAgIAAxkBAA...",
    "virus_yellow": "CAACAgIAAxkBAA...",
    "virus_wild": "CAACAgIAAxkBAA...",
    # Medicines
    "med_red": "CAACAgIAAxkBAA...",
    "med_blue": "CAACAgIAAxkBAA...",
    "med_green": "CAACAgIAAxkBAA...",
    "med_yellow": "CAACAgIAAxkBAA...",
    "med_wild": "CAACAgIAAxkBAA...",
    # Treatments
    "treatment_transplant": "CAACAgIAAxkBAA...",
    "treatment_thief": "CAACAgIAAxkBAA...",
    "treatment_contagion": "CAACAgIAAxkBAA...",
    "treatment_latex": "CAACAgIAAxkBAA...",
    "treatment_error": "CAACAgIAAxkBAA..."
}

# ---------------------------------------------------------
# GAME STATE STORAGE (Simple in-memory for single match)
# ---------------------------------------------------------
game_state = {
    "active": False,
    "players": [],          # List of user IDs
    "usernames": {},        # user_id -> display name
    "hands": {},            # user_id -> list of cards
    "boards": {},           # user_id -> dict of organs {"red": {"status": "healthy/vaccinated/infected/destroyed", "cards": []}}
    "deck": [],
    "discard": [],
    "current_turn_index": 0
}

COLORS = ["red", "blue", "green", "yellow"]

def create_deck():
    deck = []
    # Add Organs (1 of each color per player roughly, or standard distribution)
    for color in COLORS:
        deck.extend([("organ", color)] * 5)
        deck.extend([("virus", color)] * 4)
        deck.extend([("medicine", color)] * 4)
    # Wild cards
    deck.extend([("virus", "wild")] * 2)
    deck.extend([("medicine", "wild")] * 2)
    # Treatments
    deck.extend([("treatment", "transplant")] * 2)
    deck.extend([("treatment", "thief")] * 2)
    deck.extend([("treatment", "latex")] * 2)
    random.shuffle(deck)
    return deck

def init_player_board():
    return {
        color: {"status": "empty", "medicine": 0, "virus": 0, "has_organ": False} 
        for color in COLORS
    }

# ---------------------------------------------------------
# HANDLERS
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Join Game", callback_data="join_game")],
        [InlineKeyboardButton("🚀 Start Match", callback_data="start_match")]
    ]
    await update.message.reply_text(
        "🦠 **Welcome to Virus!** 💊\n\n"
        "Assemble 4 healthy organs of different colors (Red, Blue, Green, Yellow) to win!\n"
        "Click **Join Game** to enter, and **Start Match** when everyone is ready.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    name = query.from_user.first_name

    data = query.data

    if data == "join_game":
        if game_state["active"]:
            await query.edit_message_text("Game is already running!")
            return
        if user_id not in game_state["players"]:
            game_state["players"].append(user_id)
            game_state["usernames"][user_id] = name
            await query.edit_message_text(
                f"✅ {name} joined the game!\nPlayers joined: {len(game_state['players'])}\n\nClick Start Match when ready.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Join Game", callback_data="join_game")],
                    [InlineKeyboardButton("🚀 Start Match", callback_data="start_match")]
                ])
            )
        else:
            await query.answer("You are already in the game!", show_alert=True)

    elif data == "start_match":
        if len(game_state["players"]) < 1: # Allow solo testing or multiplayer
            await query.answer("Need at least 1 player to start!", show_alert=True)
            return
        
        # Initialize Game
        game_state["active"] = True
        game_state["deck"] = create_deck()
        game_state["discard"] = []
        game_state["boards"] = {pid: init_player_board() for pid in game_state["players"]}
        game_state["hands"] = {pid: [game_state["deck"].pop() for _ in range(3)] for pid in game_state["players"]}
        game_state["current_turn_index"] = 0

        await query.edit_message_text("🎲 **Game Started!** Checking initial hands...")
        await prompt_turn(context, game_state["players"][0])

async def prompt_turn(context: ContextTypes.DEFAULT_TYPE, player_id: int):
    hand = game_state["hands"][player_id]
    name = game_state["usernames"][player_id]
    
    keyboard = []
    for idx, card in enumerate(hand):
        card_text = f"{card[0].capitalize()} ({card[1].capitalize()})"
        keyboard.append([InlineKeyboardButton(f"Play: {card_text}", callback_data=f"play_{idx}")])
    
    keyboard.append([InlineKeyboardButton("🔄 Discard & Pass", callback_data="pass_turn")])

    # Send status update to chat
    board_summary = get_board_summary_text(player_id)
    msg = f"👤 **Turn: {name}**\n\n{board_summary}\n\n**Your Hand:**"
    
    await context.bot.send_message(
        chat_id=player_id,
        text=msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def get_board_summary_text(player_id):
    board = game_state["boards"][player_id]
    text = "🏥 **Your Body Board:**\n"
    for color, status_info in board.items():
        state_str = "Empty"
        if status_info["has_organ"]:
            if status_info["medicine"] == 2:
                state_str = "🛡️ Immunized"
            elif status_info["medicine"] == 1:
                state_str = "💊 Vaccinated"
            elif status_info["virus"] > 0:
                state_str = f"🦠 Infected ({status_info['virus']})"
            else:
                state_str = "❤️ Healthy Organ"
        text += f"- {color.capitalize()}: {state_str}\n"
    return text

async def game_action_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    current_player = game_state["players"][game_state["current_turn_index"]]
    if user_id != current_player:
        await query.answer("It's not your turn!", show_alert=True)
        return

    hand = game_state["hands"][user_id]

    if data.startswith("play_"):
        card_idx = int(data.split("_")[1])
        card = hand.pop(card_idx)
        card_type, color = card

        # Handle Card Logic
        board = game_state["boards"][user_id]
        if card_type == "organ":
            if not board[color]["has_organ"]:
                board[color]["has_organ"] = True
                await query.message.reply_text(f"Played a {color} organ!")
            else:
                await query.message.reply_text("You already have that organ! Card discarded.")
        elif card_type == "medicine":
            if board[color]["has_organ"] and board[color]["virus"] == 0:
                board[color]["medicine"] += 1
                await query.message.reply_text(f"Applied medicine to your {color} organ!")
            else:
                await query.message.reply_text("Cannot place medicine here. Card wasted/discarded.")
        elif card_type == "virus":
            # For simplicity in initial play, target self or check win conditions
            board[color]["virus"] += 1
            await query.message.reply_text(f"Infected a {color} organ!")

        # Draw replacement card if deck has cards
        if game_state["deck"]:
            hand.append(game_state["deck"].pop())

        # Check Win Condition (4 healthy/vaccinated/immunized organs)
        won = check_win_condition(user_id)
        if won:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"🏆 **{game_state['usernames'][user_id]} has won the game by completing their body!** 🎉",
                parse_mode="Markdown"
            )
            game_state["active"] = False
            return

        # Advance Turn
        advance_turn()
        next_player = game_state["players"][game_state["current_turn_index"]]
        await prompt_turn(context, next_player)

    elif data == "pass_turn":
        await query.message.reply_text("Passed turn and discarded hand cards.")
        game_state["hands"][user_id] = [game_state["deck"].pop() for _ in range(3) if game_state["deck"]]
        advance_turn()
        next_player = game_state["players"][game_state["current_turn_index"]]
        await prompt_turn(context, next_player)

def check_win_condition(player_id):
    board = game_state["boards"][player_id]
    completed = 0
    for color, info in board.items():
        if info["has_organ"] and info["virus"] == 0:
            completed += 1
    return completed >= 4

def advance_turn():
    game_state["current_turn_index"] = (game_state["current_turn_index"] + 1) % len(game_state["players"])

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(join_game|start_match)$"))
    application.add_handler(CallbackQueryHandler(game_action_handler, pattern="^(play_|pass_turn)"))

    Thread(target=run_flask).daemon = True
    Thread(target=run_flask).start()

    print("Bot polling started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
