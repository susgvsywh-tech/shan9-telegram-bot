import os
import random
import io
import urllib.request
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8816591363:AAH0n9RARDc6cDJwT13VD7wD_BtEC2vmTMk"

RANKS = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10}
CARD_SUITS = {'♠': 'S', '♥': 'H', '♦': 'D', '♣': 'C'}
ALL_CARDS = [(r, s) for r in RANKS.keys() for s in CARD_SUITS.keys()]

def download_card_images():
    if not os.path.exists("cards"):
        os.makedirs("cards")
    
    if not os.path.exists("cards/back.png"):
        try:
            urllib.request.urlretrieve("https://deckofcardsapi.com/static/img/back.png", "cards/back.png")
        except:
            pass

    api_ranks = {'A':'A', '2':'2', '3':'3', '4':'4', '5':'5', '6':'6', '7':'7', '8':'8', '9':'9', '10':'0', 'J':'J', 'Q':'Q', 'K':'K'}
    for r_code, r_api in api_ranks.items():
        for s_code, s_api in CARD_SUITS.items():
            filename = f"cards/{r_code}_{s_api}.png"
            if not os.path.exists(filename):
                url = f"https://deckofcardsapi.com/static/img/{r_api}{s_api}.png"
                try:
                    urllib.request.urlretrieve(url, filename)
                except:
                    pass

def generate_hand_image(hand, is_back=False):
    images = []
    
    if is_back:
        for _ in hand:
            if os.path.exists("cards/back.png"):
                img = Image.open("cards/back.png").convert("RGBA")
                img.thumbnail((160, 230))
                images.append(img)
    else:
        for rank, suit in hand:
            suit_code = CARD_SUITS[suit]
            filename = f"cards/{rank}_{suit_code}.png"
            if os.path.exists(filename):
                img = Image.open(filename).convert("RGBA")
                img.thumbnail((160, 230))
                images.append(img)

    if not images:
        return None

    card_w, card_h = images[0].size
    overlap = 30
    total_width = card_w + (len(images) - 1) * (card_w - overlap)

    combined_img = Image.new('RGBA', (total_width, card_h), (0, 0, 0, 0))
    x_offset = 0
    for img in images:
        combined_img.paste(img, (x_offset, 0), img)
        x_offset += card_w - overlap

    bio = io.BytesIO()
    bio.name = 'cards.png'
    combined_img.save(bio, 'PNG')
    bio.seek(0)
    return bio

class ShanGame:
    def __init__(self):
        self.players = {}
        self.is_open = True
        self.deck = ALL_CARDS.copy()
        random.shuffle(self.deck)

    def calculate_score(self, hand):
        total = sum(RANKS[card[0]] for card in hand)
        return total % 10

games = {}

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in games:
        await update.message.reply_text("Game already started! Click '🎮 Join Game' to play.")
        return

    games[chat_id] = ShanGame()
    keyboard = [[InlineKeyboardButton("🎮 Join Game", callback_data="join")]]
    
    await update.message.reply_text(
        "🎰 **Shan Koe Mee Game Table**\n\nClick '🎮 Join Game' to join. Type `/deal` when ready.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def deal_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games or not games[chat_id].players:
        await update.message.reply_text("No players found! Please type `/start_game` first.")
        return

    game = games[chat_id]
    game.is_open = False

    for user_id in game.players:
        game.players[user_id]["hand"] = [game.deck.pop(), game.deck.pop()]
        game.players[user_id]["status"] = "playing"

    # Auto Poki (8/9) Reveal
    for user_id, data in game.players.items():
        score = game.calculate_score(data["hand"])
        if score in [8, 9]:
            data["status"] = "stay"
            img_bytes = generate_hand_image(data["hand"], is_back=False)
            caption = f"🔥 **{data['name']} Poki {score}!**"
            if img_bytes:
                await context.bot.send_photo(chat_id=chat_id, photo=img_bytes, caption=caption, parse_mode="Markdown")

    keyboard = [
        [InlineKeyboardButton("👁️ View Cards", callback_data="view_hand")],
        [
            InlineKeyboardButton("🃏 Draw", callback_data="draw"),
            InlineKeyboardButton("🛑 Stay", callback_data="stay")
        ],
        [InlineKeyboardButton("📊 Show Results", callback_data="show_results")]
    ]

    back_img = generate_hand_image([('A', '♠'), ('A', '♠')], is_back=True)
    
    if back_img:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=back_img,
            caption="🎴 **Cards Dealt!**\n\nClick '👁️ View Cards' to check your hand privately.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user

    if chat_id not in games:
        await query.answer("No active game.", show_alert=True)
        return

    game = games[chat_id]

    if query.data == "join":
        if not game.is_open or user.id in game.players:
            await query.answer("Cannot join.", show_alert=True)
            return

        game.players[user.id] = {"name": user.first_name, "hand": [], "status": "joined"}
        await query.answer("Joined!")
        await query.message.edit_text(
            f"🎰 **Shan Koe Mee Game Table**\n\n**Players:**\n" + "\n".join([f"• 👤 {p['name']}" for p in game.players.values()]),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Join Game", callback_data="join")]])
        )

    elif query.data == "view_hand":
        if user.id not in game.players:
            return
        player = game.players[user.id]
        score = game.calculate_score(player["hand"])
        img_bytes = generate_hand_image(player["hand"], is_back=False)
        
        try:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=img_bytes,
                caption=f"📊 Score: {score} Points"
            )
            await query.answer("Sent cards to your DM!", show_alert=True)
        except Exception:
            await query.answer("Please start the bot in private DM first (/start).", show_alert=True)

    elif query.data == "draw":
        if user.id not in game.players:
            return
        player = game.players[user.id]
        if game.calculate_score(player["hand"]) in [8, 9] or len(player["hand"]) >= 3 or player["status"] == "stay":
            await query.answer("Cannot draw.", show_alert=True)
            return

        player["hand"].append(game.deck.pop())
        player["status"] = "stay"
        score = game.calculate_score(player["hand"])
        img_bytes = generate_hand_image(player["hand"], is_back=False)
        
        try:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=img_bytes,
                caption=f"🃏 Card Drawn.\n📊 Total Score: {score} Points"
            )
            await query.answer("Drawn!", show_alert=True)
        except Exception:
            await query.answer(f"Drawn! Score: {score}", show_alert=True)

    elif query.data == "stay":
        if user.id in game.players:
            game.players[user.id]["status"] = "stay"
            await query.answer("Stayed", show_alert=True)

    elif query.data == "show_results":
        await query.message.edit_text("🏆 **Game Results**", parse_mode="Markdown")
        
        for user_id, data in game.players.items():
            img_bytes = generate_hand_image(data["hand"], is_back=False)
            score = game.calculate_score(data["hand"])
            poki_str = f" 🔥 [ Poki {score} ]" if len(data["hand"]) == 2 and score in [8, 9] else ""
            caption = f"👤 **{data['name']}** ➡️ **{score} Points**{poki_str}"
            
            if img_bytes:
                await context.bot.send_photo(chat_id=chat_id, photo=img_bytes, caption=caption, parse_mode="Markdown")

        del games[chat_id]

def main():
    download_card_images()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("deal", deal_cards))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
        
