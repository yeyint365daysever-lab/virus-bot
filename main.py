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
# GAME STATE & ASSETS
# ---------------------------------------------------------
STICKERS = {
    "organ_red": "CAACAgIAAxkBAA...",
    "organ_blue": "CAACAgIAAxkBAA...",
    "organ_green": "CAACAgIAAxkBAA...",
    "organ_yellow": "CAACAgIAAxkBAA...",
    "virus_red": "CAACAgIAAxkBAA...",
    "virus_blue": "CAACAgIAAxkBAA...",
    "virus_green": "CAACAgIAAxkBAA...",
    "virus_yellow": "CAACAgIAAxkBAA...",
    "medicine_red": "CAACAgIAAxkBAA...",
    "medicine_blue": "CAACAgIAAxkBAA...",
    "medicine_green": "CAACAgIAAxkBAA...",
    "medicine_yellow": "CAACAgIAAxkBAA..."
}

game_state = {
    "active": False,
    "players": [],
    "usernames": {},
    "hands": {},
    "boards": {},
    "deck": [],
    "current_turn_index": 0
}

COLORS = ["red", "blue", "green", "yellow"]

def create_deck():
    deck = []
    for color in COLORS:
        deck.extend([("organ", color)] * 5)
        deck.extend([("virus", color)] * 4)
        deck.extend([("medicine", color)] * 4)
    random.shuffle(deck)
    return deck

def init_player_board():
    return {color: {"medicine": 0, "virus": 0, "has_organ": False} for color in COLORS}

# ---------------------------------------------------------
# BOT HANDLERS
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Join Game", callback_data="join_game")],
        [InlineKeyboardButton("🚀 Start Match", callback_data="start_match")]
    ]
    await update.message.reply_text(
        "🦠 **Welcome to Virus!** 💊\n\n"
        "Assemble 4 healthy organs of different colors to win!\n"
        "Click **Join Game** to enter, then **Start Match**.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_Mode="Markdown"
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
                f"✅ {name} joined!\nPlayers: {len(game_state['players'])}\n\nClick Start Match when ready.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Join Game", callback_data="join_game")],
                    [InlineKeyboardButton("🚀 Start Match", callback_data="start_match")]
                ])
            )
        else:
            await query.answer("You're already in!", show_alert=True)

    elif data == "start_match":
        if len(game_state["players"]) < 1:
            await query.answer("Need at least 1 player!", show_alert=True)
            return
        
        game_state["active"] = True
        game_state["deck"] = create_deck()
        game_state["boards"] = {pid: init_player_board() for pid in game_state["players"]}
        game_state["hands"] = {pid: [game_state["deck"].pop() for _ in range(3)] for pid in game_state["players"]}
        game_state["current_turn_index"] = 0

        await query.edit_message_text("🎲 **Match Started!** Check your private messages or chat for your turn.")
        await prompt_turn(context, game_state["players"][0])

async def prompt_turn(context: ContextTypes.DEFAULT_TYPE, player_id: int):
    hand = game_state["hands"][player_id]
    name = game_state["usernames"][player_id]
    
    keyboard = []
    for idx, card in enumerate(hand):
        card_text = f"{card[0].capitalize()} ({card[1].capitalize()})"
        keyboard.append([InlineKeyboardButton(f"Play: {card_text}", callback_data=f"play_{idx}")])
    
    keyboard.append([InlineKeyboardButton("🔄 Discard & Pass", callback_data="pass_turn")])

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
    for color, info in board.items():
        state_str = "Empty"
        if info["has_organ"]:
            if info["medicine"] == 2:
                state_str = "🛡️ Immunized"
            elif info["medicine"] == 1:
                state_str = "💊 Vaccinated"
            elif info["virus"] > 0:
                state_str = f"🦠 Infected ({info['virus']})"
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

        board = game_state["boards"][user_id]
        if card_type == "organ":
            if not board[color]["has_organ"]:
                board[color]["has_organ"] = True
                await query.message.reply_text(f"Played a {color} organ!")
            else:
                await query.message.reply_text("Organ slot already filled! Card discarded.")
        elif card_type == "medicine":
            if board[color]["has_organ"] and board[color]["virus"] == 0:
                board[color]["medicine"] += 1
                await query.message.reply_text(f"Applied medicine to {color} organ!")
            else:
                await query.message.reply_text("Cannot place medicine here.")
        elif card_type == "virus":
            board[color]["virus"] += 1
            await query.message.reply_text(f"Placed virus on {color} organ!")

        if game_state["deck"]:
            hand.append(game_state["deck"].pop())

        # Check win condition
        completed = sum(1 for info in board.values() if info["has_organ"] and info["virus"] == 0)
        if completed >= 4:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"🏆 **{game_state['usernames'][user_id]} wins the game!** 🎉",
                parse_mode="Markdown"
            )
            game_state["active"] = False
            return

        advance_turn()
        await prompt_turn(context, game_state["players"][game_state["current_turn_index"]])

    elif data == "pass_turn":
        await query.message.reply_text("Passed turn.")
        game_state["hands"][user_id] = [game_state["deck"].pop() for _ in range(3) if game_state["deck"]]
        advance_turn()
        await prompt_turn(context, game_state["players"][game_state["current_turn_index"]])

def advance_turn():
    game_state["current_turn_index"] = (game_state["current_turn_index"] + 1) % len(game_state["players"])

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    # Start Flask web server in background thread so Render's port checker is satisfied
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Build and run Telegram bot on the main thread
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(join_game|start_match)$"))
    application.add_handler(CallbackQueryHandler(game_action_handler, pattern="^(play_|pass_turn)"))

    print("Bot polling started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
