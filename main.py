import os
from telegram.ext import Updater, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")

def start(update, context):
    update.message.reply_text("Hola Felipe, soy tu bot funcionando en Railway 🚀")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    updater.start_polling()
    updater.idle()

if _name_ == "_main_":
    main()
    main()
