import os
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters
)

# Importar funciones de base de datos
from db import (
    init_db,
    ensure_user,
    get_user_by_telegram_id,
    create_ally,
    get_ally_by_user_id
    create_courier,
    get_courier_by_user_id,
)

TOKEN = os.getenv("BOT_TOKEN")

# Estados del registro de aliados
ALLY_NAME, ALLY_OWNER, ALLY_ADDRESS, ALLY_CITY, ALLY_BARRIO = range(5)

# Estados para registro de repartidores
(
    COURIER_FULLNAME,
    COURIER_IDNUMBER,
    COURIER_PHONE,
    COURIER_CITY,
    COURIER_BARRIO,
    COURIER_PLATE,
    COURIER_BIKETYPE,
    COURIER_CONFIRM,
) = range(8)

def start(update, context):
    update.message.reply_text("🐢 Domiquerendona está en construcción, pero ya estoy viva.")

def soy_aliado(update, context):
    user = update.effective_user
    # Crear usuario en BD si no existe
    ensure_user(user.id, user.username)

    update.message.reply_text(
        "🧑‍🍳 *Registro de aliado*\n\n"
        "Escribe el *nombre del negocio*:",
        parse_mode="Markdown",
    )
    return ALLY_NAME

def ally_name(update, context):
    context.user_data["business_name"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el *nombre del dueño o administrador*:",
        parse_mode="Markdown",
    )
    return ALLY_OWNER

def ally_owner(update, context):
    context.user_data["owner_name"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe la *dirección del negocio*:",
        parse_mode="Markdown",
    )
    return ALLY_ADDRESS

def ally_address(update, context):
    context.user_data["address"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe la *ciudad del negocio*:",
        parse_mode="Markdown",
    )
    return ALLY_CITY

def ally_city(update, context):
    context.user_data["city"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el *barrio o sector del negocio*:",
        parse_mode="Markdown",
    )
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
        f"✅ *Aliado registrado exitosamente*\n\n"
        f"🏪 Negocio: {business_name}\n"
        f"👤 Dueño: {owner_name}\n"
        f"📍 Dirección: {address}, {barrio}, {city}\n\n"
        "Tu estado es: *PENDING*",
        parse_mode="Markdown",
    )
    
  context.user_data.clear()
    return ConversationHandler.END

def soy_repartidor(update, context):
    user = update.effective_user
    ensure_user(user.id, user.username)

    update.message.reply_text(
        "🛵 *Registro de repartidor*\n\n"
        "Escribe tu *nombre completo*:",
        parse_mode="Markdown",
    )
    return COURIER_FULLNAME

def courier_fullname(update, context):
    context.user_data["full_name"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe tu *número de identificación*:",
        parse_mode="Markdown",
    )
    return COURIER_IDNUMBER
    
def courier_idnumber(update, context):
    context.user_data["id_number"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe tu *número de celular*:",
        parse_mode="Markdown",
    )
    return COURIER_PHONE
    
def courier_phone(update, context):
    context.user_data["phone"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe la *ciudad donde trabajas*:",
        parse_mode="Markdown",
    )
    return COURIER_CITY
    
def courier_city(update, context):
    context.user_data["city"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el *barrio o sector principal donde trabajas*:",
        parse_mode="Markdown",
    )
    return COURIER_BARRIO
    
def courier_barrio(update, context):
    context.user_data["barrio"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe la *placa de tu moto* (o escribe 'ninguna' si no tienes):",
        parse_mode="Markdown",
    )
    return COURIER_PLATE

def courier_plate(update, context):
    context.user_data["plate"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el *tipo de moto* (Ejemplo: Bóxer 100, FZ, scooter, bicicleta, etc.):",
        parse_mode="Markdown",
    )
    return COURIER_BIKETYPE
    
def courier_biketype(update, context):
    context.user_data["bike_type"] = update.message.text.strip()

    # Sacar los datos para mostrarlos en un resumen
    full_name = context.user_data["full_name"]
    id_number = context.user_data["id_number"]
    phone = context.user_data["phone"]
    city = context.user_data["city"]
    barrio = context.user_data["barrio"]
    plate = context.user_data["plate"]
    bike_type = context.user_data["bike_type"]

    resumen = (
        "✅ *Verifica tus datos de repartidor:*\n\n"
        f"👤 Nombre: {full_name}\n"
        f"🆔 Cédula: {id_number}\n"
        f"📱 Teléfono: {phone}\n"
        f"🏙 Ciudad: {city}\n"
        f"📍 Barrio: {barrio}\n"
        f"🛵 Placa: {plate}\n"
        f"💺 Tipo de moto: {bike_type}\n\n"
        "Si todo está bien escribe: *SI*\n"
        "Si quieres corregir, cancela y vuelve a usar /soy_repartidor"
    )

    update.message.reply_text(resumen, parse_mode="Markdown")
    return COURIER_CONFIRM

def courier_confirm(update, context):
    confirm_text = update.message.text.strip().upper()
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)

    if confirm_text not in ("SI", "SÍ", "SI.", "SÍ."):
        update.message.reply_text(
            "❌ Registro cancelado.\n\n"
            "Si deseas intentarlo de nuevo, usa /soy_repartidor."
        )
        context.user_data.clear()
        return ConversationHandler.END

    full_name = context.user_data["full_name"]
    id_number = context.user_data["id_number"]
    phone = context.user_data["phone"]
    city = context.user_data["city"]
    barrio = context.user_data["barrio"]
    plate = context.user_data["plate"]
    bike_type = context.user_data["bike_type"]

    # Código interno simple basado en id de usuario
    code = f"R-{db_user['id']:04d}"

    create_courier(
        user_id=db_user["id"],
        full_name=full_name,
        id_number=id_number,
        phone=phone,
        city=city,
        barrio=barrio,
        plate=plate,
        bike_type=bike_type,
        code=code,
    )

    update.message.reply_text(
        "✅ *Repartidor registrado exitosamente*\n\n"
        f"👤 Nombre: {full_name}\n"
        f"🆔 Cédula: {id_number}\n"
        f"📱 Teléfono: {phone}\n"
        f"🏙 Ciudad: {city}\n"
        f"📍 Barrio: {barrio}\n"
        f"🛵 Placa: {plate}\n"
        f"💺 Tipo de moto: {bike_type}\n"
        f"🔐 Código interno: *{code}*\n\n"
        "Tu estado es: *PENDING*.\n"
        "El administrador deberá aprobarte antes de que puedas tomar pedidos.",
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

courier_conv = ConversationHandler(
    entry_points=[CommandHandler("soy_repartidor", soy_repartidor)],
    states={
        COURIER_FULLNAME: [
            MessageHandler(Filters.text & ~Filters.command, courier_fullname)
        ],
        COURIER_IDNUMBER: [
            MessageHandler(Filters.text & ~Filters.command, courier_idnumber)
        ],
        COURIER_PHONE: [
            MessageHandler(Filters.text & ~Filters.command, courier_phone)
        ],
        COURIER_CITY: [
            MessageHandler(Filters.text & ~Filters.command, courier_city)
        ],
        COURIER_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command, courier_barrio)
        ],
        COURIER_PLATE: [
            MessageHandler(Filters.text & ~Filters.command, courier_plate)
        ],
        COURIER_BIKETYPE: [
            MessageHandler(Filters.text & ~Filters.command, courier_biketype)
        ],
        COURIER_CONFIRM: [
            MessageHandler(Filters.text & ~Filters.command, courier_confirm)
        ],
    },
    fallbacks=[],
)

def main():
    # Inicializar base de datos
    init_db()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(ally_conv)
    dp.add_handler(courier_conv)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
