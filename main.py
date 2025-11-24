import os
from telegram.ext import Updater, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")

def start(update, context):
    from telegram.ext import ConversationHandler, MessageHandler, Filters

ALLY_NAME, ALLY_OWNER, ALLY_ADDRESS, ALLY_CITY, ALLY_BARRIO = range(5)

from db import (
    ensure_user,
    get_user_by_telegram_id,
    create_ally,
    get_ally_by_user_id
)


def soy_aliado(update, context):
    user = update.effective_user
    ensure_user(user.id, user.username)

    update.message.reply_text(
        "🧑‍🍳 Registro de aliado\n\n"
        "Escribe el nombre del negocio:",
        parse_mode="Markdown",
    )
    return ALLY_NAME


def ally_name(update, context):
    context.user_data["business_name"] = update.message.text.strip()
    update.message.reply_text("Escribe el nombre del dueño o administrador:", parse_mode="Markdown")
    return ALLY_OWNER


def ally_owner(update, context):
    context.user_data["owner_name"] = update.message.text.strip()
    update.message.reply_text("Escribe la dirección del negocio:", parse_mode="Markdown")
    return ALLY_ADDRESS


def ally_address(update, context):
    context.user_data["address"] = update.message.text.strip()
    update.message.reply_text("Escribe la ciudad del negocio:", parse_mode="Markdown")
    return ALLY_CITY


def ally_city(update, context):
    context.user_data["city"] = update.message.text.strip()
    update.message.reply_text("Escribe el barrio o sector del negocio:", parse_mode="Markdown")
    return ALLY_BARRIO


def ally_barrio(update, context):
    barrio = update.message.text.strip()
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)

    business_name = context.user_data["business_name"]
    owner_name = context.user_data["owner_name"]
    address = context.user_data["address"]
    city = context.user_data["city"]

    create_ally(
        user_id=db_user["id"],
        business_name=business_name,
        owner_name=owner_name,
        address=address,
        city=city,
        barrio=barrio,
    )

    update.message.reply_text(
        f"✅ Aliado registrado exitosamente\n\n"
        f"🏪 Negocio: {business_name}\n"
        f"👤 Dueño: {owner_name}\n"
        f"📍 Dirección: {address}, {barrio}, {city}\n\n"
        "Tu estado es: PENDING\n"
        "(en el futuro lo aprobarás desde el panel de admin)",
        parse_mode="Markdown",
    )

    context.user_data.clear()
    return ConversationHandler.END


ally_conv = ConversationHandler(
    entry_points=[CommandHandler("soy_aliado", soy_aliado)],
    states={
        ALLY_NAME: [MessageHandler(Filters.text & ~Filters.command, ally_name)],
        ALLY_OWNER: [MessageHandler(Filters.text & ~Filters.command, ally_owner)],
        ALLY_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, ally_address)],
        ALLY_CITY: [MessageHandler(Filters.text & ~Filters.command, ally_city)],
        ALLY_BARRIO: [MessageHandler(Filters.text & ~Filters.command, ally_barrio)],
    },
    fallbacks=[],
)
    update.message.reply_text("🐢 Domiquerendona está en construcción, pero ya estoy viva.")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
