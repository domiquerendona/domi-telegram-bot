import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)

# ------------- CONFIGURACIÓN BÁSICA -------------

TOKEN = os.getenv("BOT_TOKEN")

# ID del grupo de repartidores (Repartidores DOMIQUERENDONA)
COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))

# ID del grupo de restaurantes (ALIADOS ...)
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

# Estados para la conversación
PEDIR_DIRECCION, PEDIR_VALOR_PEDIDO, PEDIR_FORMA_PAGO, PEDIR_ZONA, CONFIRMAR_PEDIDO = range(5)

# "Base de datos" simple en memoria
orders = {}
next_order_id = 1


# ------------- MANEJADORES -------------

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if chat_id == RESTAURANT_CHAT_ID:
        texto = (
            "Hola, soy tu bot de domicilios 🚀\n\n"
            "Comando principal para *restaurantes*:\n"
            "/nuevo_pedido – crear un nuevo domicilio."
        )
    elif chat_id == COURIER_CHAT_ID:
        texto = (
            "Hola domiciliarios 🛵\n\n"
            "Aquí aparecerán los pedidos nuevos.\n"
            "Cuando veas uno, toca *Tomar pedido* para asignártelo."
        )
    else:
        texto = (
            "Hola, soy el bot de domicilios 🚀\n\n"
            "▫ En el grupo de *restaurantes* se usa /nuevo_pedido.\n"
            "▫ En el grupo de *repartidores* publico los pedidos para que los tomen."
        )

    update.message.reply_text(texto, parse_mode="Markdown")
    return ConversationHandler.END


def nuevo_pedido(update: Update, context: CallbackContext):
    """Inicia la creación de un pedido (solo en grupo de restaurantes)."""
    global next_order_id

    chat = update.effective_chat

    # Si tenemos configurado RESTAURANT_CHAT_ID y este chat no coincide, no seguimos
    if RESTAURANT_CHAT_ID != 0 and chat.id != RESTAURANT_CHAT_ID:
        update.message.reply_text(
            "Este comando solo funciona en el *grupo de restaurantes*.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    order_id = next_order_id
    next_order_id += 1

    orders[order_id] = {
        "restaurante_chat_id": chat.id,
        "restaurante_user_id": update.effective_user.id,
        "direccion": "",
        "valor": 0,
        "forma_pago": "",
        "zona": "",
        "courier_user_id": None,
    }

    context.user_data["order_id"] = order_id

    update.message.reply_text(
        "📍 Envíame la *dirección del cliente*:",
        parse_mode="Markdown",
    )
    return PEDIR_DIRECCION


def pedir_valor(update: Update, context: CallbackContext):
    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        update.message.reply_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    orders[order_id]["direccion"] = update.message.text.strip()

    update.message.reply_text(
        "💰 ¿Cuál es el *valor de los productos*? (solo números)",
        parse_mode="Markdown",
    )
    return PEDIR_VALOR_PEDIDO


def pedir_forma_pago(update: Update, context: CallbackContext):
    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        update.message.reply_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    texto = update.message.text.strip()

    try:
        valor = int(texto)
    except ValueError:
        update.message.reply_text(
            "Por favor envíame *solo números* para el valor de los productos.",
            parse_mode="Markdown",
        )
        return PEDIR_VALOR_PEDIDO

    orders[order_id]["valor"] = valor

    keyboard = [
        [
            InlineKeyboardButton("💵 Efectivo", callback_data="pago_efectivo"),
            InlineKeyboardButton("💳 Transferencia", callback_data="pago_transferencia"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Selecciona la *forma de pago*:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return PEDIR_FORMA_PAGO


def recibir_forma_pago(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        query.edit_message_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    data = query.data  # pago_efectivo o pago_transferencia
    forma = "efectivo" if data == "pago_efectivo" else "transferencia"

    orders[order_id]["forma_pago"] = forma

    query.edit_message_text(
        f"✅ Forma de pago: *{forma.capitalize()}*\n\n"
        "Ahora escribe la *zona/barrio*:",
        parse_mode="Markdown",
    )
    return PEDIR_ZONA


def pedir_confirmacion(update: Update, context: CallbackContext):
    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        update.message.reply_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    orders[order_id]["zona"] = update.message.text.strip()
    order = orders[order_id]

    resumen = (
        f"🧾 *Resumen del pedido #{order_id}:*\n"
        f"📍 Dirección: {order['direccion']}\n"
        f"💰 Valor productos: {order['valor']}\n"
        f"💳 Forma de pago: {order['forma_pago']}\n"
        f"📌 Zona: {order['zona']}\n\n"
        "¿Confirmas este pedido?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_pedido"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_pedido"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(resumen, reply_markup=reply_markup, parse_mode="Markdown")
    return CONFIRMAR_PEDIDO


def confirmar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        query.edit_message_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    order = orders[order_id]

    # Aviso en el grupo de restaurantes
    query.edit_message_text("✅ Pedido confirmado. Buscando domiciliario...")

    # Publicar en el grupo de repartidores
    if COURIER_CHAT_ID != 0:
        texto_couriers = (
            f"🚨 *Nuevo domicilio disponible #{order_id}*\n\n"
            f"📍 Dirección: {order['direccion']}\n"
            f"💰 Valor productos: {order['valor']}\n"
            f"💳 Forma de pago: {order['forma_pago']}\n"
            f"📌 Zona: {order['zona']}\n\n"
            "El primero que toque el botón se queda con la carrera."
        )

        keyboard = [
            [InlineKeyboardButton("🛵 Tomar pedido", callback_data=f"tomar_{order_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=COURIER_CHAT_ID,
            text=texto_couriers,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    return ConversationHandler.END


def cancelar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if order_id in orders:
        del orders[order_id]

    query.edit_message_text("❌ Pedido cancelado.")
    return ConversationHandler.END


def tomar_pedido(update: Update, context: CallbackContext):
    """Un domiciliario pulsa 'Tomar pedido' en el grupo de repartidores."""
    query = update.callback_query
    query.answer()

    data = query.data  # tomar_X
    try:
        order_id = int(data.split("_")[1])
    except (IndexError, ValueError):
        query.edit_message_text("Error al leer el pedido.")
        return

    order = orders.get(order_id)
    if not order:
        query.edit_message_text("⚠️ Este pedido ya no está disponible.")
        return

    if order.get("courier_user_id"):
        query.edit_message_text("⚠️ Otro domiciliario ya tomó este pedido.")
        return

    courier = query.from_user
    courier_id = courier.id

    order["courier_user_id"] = courier_id
    order["courier_name"] = courier.full_name
    order["courier_username"] = courier.username

    # Editar mensaje en el grupo de repartidores
    query.edit_message_text(f"✅ Pedido #{order_id} tomado por {courier.full_name}.")

    # Mensaje privado al domiciliario
    texto_courier = (
        f"✅ *Pedido asignado #{order_id}*\n\n"
        f"📍 Dirección: {order['direccion']}\n"
        f"💰 Valor productos: {order['valor']}\n"
        f"💳 Forma de pago: {order['forma_pago']}\n"
        f"📌 Zona: {order['zona']}\n\n"
        "Comunícate con el restaurante para cualquier detalle adicional."
    )

    context.bot.send_message(
        chat_id=courier_id,
        text=texto_courier,
        parse_mode="Markdown",
    )

    # Aviso al restaurante
    rest_chat_id = order.get("restaurante_chat_id")
    if rest_chat_id:
        nombre = courier.full_name
        user_link = f"@{courier.username}" if courier.username else ""
        texto_rest = f"🛵 Tu pedido #{order_id} fue tomado por *{nombre}* {user_link}"

        context.bot.send_message(
            chat_id=rest_chat_id,
            text=texto_rest,
            parse_mode="Markdown",
        )


def cancelar_conversacion(update: Update, context: CallbackContext):
    update.message.reply_text("Conversación cancelada. Puedes empezar de nuevo con /nuevo_pedido.")
    return ConversationHandler.END


# ------------- FUNCIÓN PRINCIPAL -------------

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # /start
    dp.add_handler(CommandHandler("start", start))

    # Flujo /nuevo_pedido (solo lo controlamos dentro de la función)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("nuevo_pedido", nuevo_pedido)],
        states={
            PEDIR_DIRECCION: [MessageHandler(Filters.text & ~Filters.command, pedir_valor)],
            PEDIR_VALOR_PEDIDO: [MessageHandler(Filters.text & ~Filters.command, pedir_forma_pago)],
            PEDIR_FORMA_PAGO: [CallbackQueryHandler(recibir_forma_pago)],
            PEDIR_ZONA: [MessageHandler(Filters.text & ~Filters.command, pedir_confirmacion)],
            CONFIRMAR_PEDIDO: [
                CallbackQueryHandler(confirmar_pedido, pattern="^confirmar_pedido$"),
                CallbackQueryHandler(cancelar_pedido, pattern="^cancelar_pedido$"),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)],
        allow_reentry=True,
    )

    dp.add_handler(conv_handler)

    # Cuando un domiciliario pulsa "Tomar pedido"
    dp.add_handler(CallbackQueryHandler(tomar_pedido, pattern=r"^tomar_\d+$"))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
