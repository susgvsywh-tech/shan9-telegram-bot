import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8816591363:AAH0n9RARDc6cDJwT13VD7wD_BtEC2vmTMk"

RANKS = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10}

CARD_EMOJIS = {
    # Spades
    ('A', '♠'): '🂡', ('2', '♠'): '🂢', ('3', '♠'): '🂣', ('4', '♠'): '🂤', ('5', '♠'): '🂥', 
    ('6', '♠'): '🂦', ('7', '♠'): '🂧', ('8', '♠'): '🂨', ('9', '♠'): '🂩', ('10', '♠'): '🂪', 
    ('J', '♠'): '🂫', ('Q', '♠'): '🂭', ('K', '♠'): '🂮',
    # Hearts
    ('A', '♥'): '🂱', ('2', '♥'): '🂲', ('3', '♥'): '🂳', ('4', '♥'): '🂴', ('5', '♥'): '🂵', 
    ('6', '♥'): '🂶', ('7', '♥'): '🂷', ('8', '♥'): '🂸', ('9', '♥'): '🂹', ('10', '♥'): '🂺', 
    ('J', '♥'): '🂻', ('Q', '♥'): '🂽', ('K', '♥'): '🂾',
    # Diamonds
    ('A', '♦'): '🃁', ('2', '♦'): '🃂', ('3', '♦'): '🃃', ('4', '♦'): '🃄', ('5', '♦'): '🃅', 
    ('6', '♦'): '🃆', ('7', '♦'): '🃇', ('8', '♦'): '🃈', ('9', '♦'): '🃉', ('10', '♦'): '🃊', 
    ('J', '♦'): '🃋', ('Q', '♦'): '🃍', ('K', '♦'): '🃎',
    # Clubs
    ('A', '♣'): '🃑', ('2', '♣'): '🃒', ('3', '♣'): '🃓', ('4', '♣'): '🃔', ('5', '♣'): '🃕', 
    ('6', '♣'): '🃖', ('7', '♣'): '🃗', ('8', '♣'): '🃘', ('9', '♣'): '🃙', ('10', '♣'): '🃚', 
    ('J', '♣'): '🃛', ('Q', '♣'): '🃝', ('K', '♣'): '🃞'
}

def render_card(card):
    emoji = CARD_EMOJIS.get(card, '')
    return f"{emoji} {card[0]}{card[1]}"

class ShanGame:
    def __init__(self):
        self.players = {}
        self.is_open = True
        self.deck = list(CARD_EMOJIS.keys())
        random.shuffle(self.deck)

    def calculate_score(self, hand):
        total = sum(RANKS[card[0]] for card in hand)
        return total % 10

games = {}

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in games:
        await update.message.reply_text("⚠️ Game already in progress! Click 'Join' to play.")
        return

    games[chat_id] = ShanGame()
    keyboard = [[InlineKeyboardButton("🎮 Join Game", callback_data="join")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎰 **Shan Koe Mee Game Started!**\n\nClick 'Join Game' to enter.\nType `/deal` when all players are ready.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def deal_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games or not games[chat_id].players:
        await update.message.reply_text("⚠️ No players yet. Type `/start_game` first.")
        return

    game = games[chat_id]
    game.is_open = False

    for user_id in game.players:
        game.players[user_id]["hand"] = [game.deck.pop(), game.deck.pop()]

    keyboard = [
        [
            InlineKeyboardButton("🃏 Draw", callback_data="draw"),
            InlineKeyboardButton("🛑 Stay", callback_data="stay")
        ],
        [InlineKeyboardButton("📊 Show Results", callback_data="show_results")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = "🎴 **Cards Dealt!**\n\n"
    for user_id, data in game.players.items():
        score = game.calculate_score(data["hand"])
        if len(data["hand"]) == 2 and score in [8, 9]:
            c1, c2 = render_card(data["hand"][0]), render_card(data["hand"][1])
            msg += f"🔥 **{data['name']}**: [{c1}] [{c2}] ➡️ **Poki {score}!**\n"
        else:
            msg += f"👤 **{data['name']}**: 2 Cards (Choose Draw or Stay)\n"

    await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user

    if chat_id not in games:
        await query.answer("No active game.", show_alert=True)
        return

    game = games[chat_id]

    if query.data == "join":
        if not game.is_open:
            await query.answer("Game already started!", show_alert=True)
            return
        if user.id in game.players:
            await query.answer("You have already joined.", show_alert=True)
            return

        game.players[user.id] = {"name": user.first_name, "hand": []}
        await query.answer("Joined the game!")
        await query.message.edit_text(
            f"🎰 **Shan Koe Mee Game Started!**\n\n**Players:**\n" + 
            "\n".join([f"- {p['name']}" for p in game.players.values()]),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Join Game", callback_data="join")]])
        )

    elif query.data == "draw":
        if user.id not in game.players:
            await query.answer("You are not in this game.", show_alert=True)
            return
        
        player = game.players[user.id]
        if len(player["hand"]) >= 3:
            await query.answer("Max 3 cards reached!", show_alert=True)
            return

        card = game.deck.pop()
        player["hand"].append(card)
        score = game.calculate_score(player["hand"])
        await query.answer(f"Card drawn: {render_card(card)} | Total score: {score}", show_alert=True)

    elif query.data == "stay":
        if user.id not in game.players:
            await query.answer("You are not in this game.", show_alert=True)
            return
        await query.answer("You choose to Stay.", show_alert=True)

    elif query.data == "show_results":
        result_text = "🏆 **Game Results** 🏆\n\n"
        for user_id, data in game.players.items():
            hand_str = " ".join([f"[{render_card(c)}]" for c in data["hand"]])
            score = game.calculate_score(data["hand"])
            card_count = len(data["hand"])
            
            poki_str = ""
            if card_count == 2 and score in [8, 9]:
                poki_str = f" 🔥 (Poki {score})"

            result_text += f"👤 **{data['name']}**: {hand_str} ➡️ **{score} Pts**{poki_str}\n"

        del games[chat_id]
        await query.message.edit_text(result_text, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("deal", deal_cards))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
        
