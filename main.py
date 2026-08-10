import os
import random
import io
import urllib.request
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8816591363:AAFQ_IxBbliDcPFrNfA16Lrd3bzuumTH2Qc"

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
    try:
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
    except Exception as e:
        print(f"Image generation error: {e}")
        return None

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
        await update.message.reply_text("Game already started! Click '🎮 Join Game' or use `/kill` to reset.")
        return

    games[chat_id] = ShanGame()
    keyboard = [[InlineKeyboardButton("🎮 Join Game", callback_data="join")]]
    
    await update.message.reply_text(
        "🎰 **Shan Koe Mee Game Table**\n\nClick '🎮 Join Game' to join. Type `/deal` when ready.\nType `/kill` to stop/reset the game.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def kill_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in games:
        del games[chat_id]
        await update.message.reply_text("🛑 **Game session killed and reset successfully!** You can now type `/start_game` to start a new game.")
    else:
        await update.message.reply_text("No active game session to kill.")

async def deal_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in games:
        await update.message.reply_text("No active game! Please type `/start_game` first.")
        return

    game = games[chat_id]
    if not game.players:
        await update.message.reply_text("No players joined yet! Click '🎮 Join Game' first.")
        return

    game.is_open = False

    for user_id in game.players:
        game.players[user_id]["hand"] = [game.deck.pop(), game.deck.pop()]
        game.players[user_id]["status"] = "playing"

    # Poki Reveal (8/9)
    for user_id, data in game.players.items():
        score = game.calculate_score(data["hand"])
        if score in [8, 9]:
            data["status"] = "stay"
            img_bytes = generate_hand_image(data["hand"], is_back=False)
            caption = f"🔥 **{data['name']} Poki {score}!**"
            if img_bytes:
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=img_bytes, caption=caption, parse_mode="Markdown")
                except:
                    await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
            else:
                cards_str = " ".join([f"{r}{s}" for r, s in data['hand']])
                await context.bot.send_message(chat_id=chat_id, text=f"🔥 **{data['name']} Poki {score}!** [{cards_str}]", parse_mode="Markdown")

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
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=back_img,
                caption="🎴 **Cards Dealt!**\n\nClick '👁️ View Cards' to check your hand privately.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🎴 **Cards Dealt!**\n\nClick '👁️ View Cards' to check your hand privately.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎴 **Cards Dealt!**\n\nClick '👁️ View Cards' to check your hand privately.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user

    if chat_id not in games:
        await query.answer("No active game session.", show_alert=True)
        return

    game = games[chat_id]

    if query.data == "join":
        if not game.is_open or user.id in game.players:
            await query.answer("Already joined or game closed.", show_alert=True)
            return

        game.players[user.id] = {"name": user.first_name, "hand": [], "status": "joined"}
        await query.answer("Joined!")
        await query.message.edit_text(
            f"🎰 **Shan Koe Mee Game Table**\n\n**Players Joined:**\n" + "\n".join([f"• 👤 {p['name']}" for p in game.players.values()]),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Join Game", callback_data="join")]])
        )

    elif query.data == "view_hand":
        if user.id not in game.players:
            await query.answer("You are not in this game.", show_alert=True)
            return
        player = game.players[user.id]
        score = game.calculate_score(player["hand"])
        img_bytes = generate_hand_image(player["hand"], is_back=False)
        cards_str = " ".join([f"{r}{s}" for r, s in player['hand']])
        
        try:
            if img_bytes:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=img_bytes,
                    caption=f"📊 Your Hand: {cards_str}\n📊 Score: {score} Points"
                )
            else:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"📊 Your Hand: {cards_str}\n📊 Score: {score} Points"
                )
            await query.answer("Sent cards to your DM!", show_alert=True)
        except Exception:
            await query.answer("Please start the bot in private DM first (/start).", show_alert=True)

    elif query.data == "draw":
        if user.id not in game.players:
            await query.answer("You are not in this game.", show_alert=True)
            return
        player = game.players[user.id]
        if game.calculate_score(player["hand"]) in [8, 9] or len(player["hand"]) >= 3 or player["status"] == "stay":
            await query.answer("Cannot draw more cards.", show_alert=True)
            return

        player["hand"].append(game.deck.pop())
        player["status"] = "stay"
        score = game.calculate_score(player["hand"])
        img_bytes = generate_hand_image(player["hand"], is_back=False)
        cards_str = " ".join([f"{r}{s}" for r, s in player['hand']])
        
        try:
            if img_bytes:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=img_bytes,
                    caption=f"🃏 Card Drawn.\n📊 Hand: {cards_str}\n📊 Total Score: {score} Points"
                )
            else:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"🃏 Card Drawn.\n📊 Hand: {cards_str}\n📊 Total Score: {score} Points"
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
            cards_str = " ".join([f"{r}{s}" for r, s in data['hand']])
            poki_str = f" 🔥 [ Poki {score} ]" if len(data["hand"]) == 2 and score in [8, 9] else ""
            caption = f"👤 **{data['name']}** ➡️ **{score} Points** ({cards_str}){poki_str}"
            
            if img_bytes:
                try:
                    await context.bot.send_photo(chat_id=chat_id, photo=img_bytes, caption=caption, parse_mode="Markdown")
                except:
                    await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")
            else:
                await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")

        if chat_id in games:
            del games[chat_id]

def main():
    download_card_images()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("kill", kill_game))
    app.add_handler(CommandHandler("reset", kill_game))
    app.add_handler(CommandHandler("deal", deal_cards))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
        
