import random
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8816591363:AAFQ_IxBbliDcPFrNfA16Lrd3bzuumTH2Qc"
WEB_APP_URL = "https://susgvsywh-tech.github.io/shan9-telegram-bot/"

RANKS = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10}
SUITS = ['♠', '♥', '♦', '♣']
ALL_CARDS = [(r, s) for r in RANKS.keys() for s in SUITS]

class ShanGame:
    def __init__(self):
        self.deck = ALL_CARDS.copy()
        random.shuffle(self.deck)

    def draw_hand(self):
        hand = [self.deck.pop() for _ in range(3)]
        score = sum(RANKS[card[0]] for card in hand) % 10
        return hand, score

games = {}

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    games[chat_id] = ShanGame()
    
    keyboard = [[InlineKeyboardButton("🎴 Play Shan Koe Mee (Random)", web_app=WebAppInfo(url=WEB_APP_URL))]]
    await update.message.reply_text(
        "🎲 **ကံတရားသာလျှင် အဆုံးအဖြတ်ပေးမည်!**\n\nClick below to draw your fate:", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if chat_id not in games:
        games[chat_id] = ShanGame()

    data = json.loads(update.effective_message.web_app_data.data)
    action = data.get("action")

    if action == "draw":
        hand, score = games[chat_id].draw_hand()
        cards_str = " ".join([f"{c[0]}{c[1]}" for c in hand])
        await update.message.reply_text(f"👤 {user.first_name} ရဲ့ လက်ထဲမှာ:\n🎴 **{cards_str}**\n\n🎯 **ရမှတ် - {score}**")
    
    elif action == "stay":
        await update.message.reply_text(f"🏁 {user.first_name} ဂိမ်းရပ်နားလိုက်ပါပြီ။")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    print("Bot is running with Pure Luck Mode...")
    app.run_polling()

if __name__ == "__main__":
    main()
    
