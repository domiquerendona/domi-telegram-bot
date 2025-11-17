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

# ---------------- CONFIGURACIÓN BÁSICA ----------------

TOKEN = os.getenv("BOT_TOKEN")  # Ya lo tienes en Railway

# ID del grupo donde están los domiciliarios
# Luego lo reemplazas por el real y lo guardas en Railway como variable COURIER_CHAT_ID
COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))

# Estados de la conversación para crear pedido
PEDIR_DIRECCION, PEDIR_VALOR_PEDIDO, PEDIR_FORMA_PAGO, PEDIR_ZONA, CONFIRMAR_PEDIDO = range(5)

# "Base de datos" simple en memoria por ahora
orders = {}
next_order_id = 1

# ---------------- MANEJADORES BÁSICOS ----------------

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hola Felipe, soy tu bot funcionando en Railway 🚀\n\n"
        "Comando principal:\n"
        "/nuevo_pedido – crear un nuevo domicilio."
    )

    return ConversationHandler.END


def nuevo_pedido(update: Update, context: CallbackContext):
    global next_order_id

    order_id = next_order_id
    next_order_id += 1

    # Creamos el esqueleto del pedido
    orders[order_id] = {
        "restaurante_id": update.effective_chat.id,   # grupo donde se crea el pedido
        "creador_id": update.effective_user.id,       # persona que escribió /nuevo_pedido
        "direccion": "",
        "valor": 0,
        "forma_pago": "",
        "zona": "",
        "courier_id": None,
        "estado": "pendiente",                        # 🔹 NUEVO
    }

    context.user_data["order_id"] = order_id

    update.message.reply_text("📍 Envíame la dirección del cliente:", parse_mode="Markdown")
    return PEDIR_DIRECCION

def pedir_valor(update: Update, context: CallbackContext):
    order_id = context.user_data["order_id"]
    orders[order_id]["direccion"] = update.message.text

    update.message.reply_text("💰 ¿Cuál es el valor del pedido (solo números)?", parse_mode="Markdown")
    return PEDIR_VALOR_PEDIDO


def pedir_forma_pago(update: Update, context: CallbackContext):
    order_id = context.user_data["order_id"]

    try:
        valor = int(update.message.text)
    except ValueError:
        update.message.reply_text("Por favor envíame solo números para el valor del pedido.")
        return PEDIR_VALOR_PEDIDO

    orders[order_id]["valor"] = valor

    keyboard = [
        [
            InlineKeyboardButton("💵 Efectivo", callback_data="efectivo"),
            InlineKeyboardButton("💳 Transferencia", callback_data="transferencia"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text("Selecciona la forma de pago:", reply_markup=reply_markup, parse_mode="Markdown")
    return PEDIR_FORMA_PAGO


def recibir_forma_pago(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = context.user_data["order_id"]
    orders[order_id]["forma_pago"] = query.data

    query.edit_message_text("✅ Forma de pago registrada.\n\nAhora dime la zona/barrio:", parse_mode="Markdown")
    return PEDIR_ZONA


def pedir_confirmacion(update: Update, context: CallbackContext):
    order_id = context.user_data["order_id"]
    orders[order_id]["zona"] = update.message.text

    order = orders[order_id]

    resumen = (
        f"🧾 Resumen del pedido #{order_id}:\n"
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
    order_id = context.user_data["order_id"]
    order = orders[order_id]

    # Aviso al restaurante
    query.edit_message_text("✅ Pedido confirmado. Buscando domiciliario...")

    # Mensaje al grupo de domiciliarios
    if COURIER_CHAT_ID != 0:
        texto_couriers = (
            f"🚨 Nuevo domicilio disponible #{order_id}\n\n"
            f"📍 Dirección: {order['direccion']}\n"
            f"💰 Valor productos: {order['valor']}\n"
            f"💳 Forma de pago: {order['forma_pago']}\n"
            f"📌 Zona: {order['zona']}\n\n"
            "El primero que acepte se queda con la carrera."
        )

        keyboard = [
            [InlineKeyboardButton("🛵 Tomar pedido", callback_data=f"tomar_{order_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.bot.send_message(
            chat_id=COURIER_CHAT_ID,
            text=texto_couriers,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    return ConversationHandler.END


def cancelar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("❌ Pedido cancelado.")
    return ConversationHandler.END


def tomar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data  # ejemplo: "tomar_3"
    order_id = int(data.split("_")[1])

    order = orders.get(order_id)
    if not order:
        query.edit_message_text("⚠️ Este pedido ya no está disponible.")
        return

    if order["courier_id"] is not None:
        query.edit_message_text("⚠️ Otro domiciliario ya tomó este pedido.")
        return

    courier_id = update.effective_user.id
    courier_name = update.effective_user.full_name
    courier_username = update.effective_user.username

    order["courier_id"] = courier_id
    order["estado"] = "asignado"

    # Editamos mensaje en el grupo de repartidores
    query.edit_message_text("✅ Pedido tomado por un domiciliario.")

    # 🛵 Mensaje al domiciliario (privado) con botón "Marcar como entregado"
    texto_courier = (
        f"✅ Pedido asignado #{order_id}\n\n"
        f"📍 Dirección: {order['direccion']}\n"
        f"💰 Valor productos: {order['valor']}\n"
        f"💳 Forma de pago: {order['forma_pago']}\n"
        f"📌 Zona: {order['zona']}\n\n"
        "Cuando entregues el pedido, marca como entregado 👇"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Marcar como entregado", callback_data=f"entregado_{order_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.bot.send_message(
        chat_id=courier_id,
        text=texto_courier,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
def tomar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data  # ejemplo: "tomar_3"
    order_id = int(data.split("_")[1])

    order = orders.get(order_id)
    if not order:
        query.edit_message_text("⚠️ Este pedido ya no está disponible.")
        return

    if order["courier_id"] is not None:
        query.edit_message_text("⚠️ Otro domiciliario ya tomó este pedido.")
        return

    courier_id = update.effective_user.id
    courier_name = update.effective_user.full_name
    courier_username = update.effective_user.username

    order["courier_id"] = courier_id
    order["estado"] = "asignado"

    # Editamos mensaje en el grupo de repartidores
    query.edit_message_text("✅ Pedido tomado por un domiciliario.")

    # 🛵 Mensaje al domiciliario (privado) con botón "Marcar como entregado"
    texto_courier = (
        f"✅ Pedido asignado #{order_id}\n\n"
        f"📍 Dirección: {order['direccion']}\n"
        f"💰 Valor productos: {order['valor']}\n"
        f"💳 Forma de pago: {order['forma_pago']}\n"
        f"📌 Zona: {order['zona']}\n\n"
        "Cuando entregues el pedido, marca como entregado 👇"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Marcar como entregado", callback_data=f"entregado_{order_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.bot.send_message(
        chat_id=courier_id,
        text=texto_courier,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    # Mensaje al grupo del restaurante
    texto_restaurante = (
        f"✅ El pedido #{order_id} ya fue tomado.\n\n"
        f"🛵 Repartidor: {courier_name}"
    )
    if courier_username:
        texto_restaurante += f" (@{courier_username})"

    query.bot.send_message(
        chat_id=order["restaurante_id"],
        text=texto_restaurante,
        parse_mode="Markdown",
    )

    # Mensaje privado a la persona que creó el pedido
    creador_id = order.get("creador_id")
    if creador_id:
        query.bot.send_message(
            chat_id=creador_id,
            text=texto_restaurante,
            parse_mode="Markdown",
        )
    # Mensaje al grupo del restaurante
    texto_restaurante = (
        f"✅ El pedido #{order_id} ya fue tomado.\n\n"
        f"🛵 Repartidor: {courier_name}"
    )
    if courier_username:
        texto_restaurante += f" (@{courier_username})"

    query.bot.send_message(
        chat_id=order["restaurante_id"],
        text=texto_restaurante,
        parse_mode="Markdown",
    )

    # Mensaje privado a la persona que creó el pedido
    creador_id = order.get("creador_id")
    if creador_id:
        query.bot.send_message(
            chat_id=creador_id,
            text=texto_restaurante,
            parse_mode="Markdown",
        )


def cancelar_conversacion(update: Update, context: CallbackContext):
    update.message.reply_text("Conversación cancelada.")
    return ConversationHandler.END


def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Comando /start
    dp.add_handler(CommandHandler("start", start))

    # Flujo para /nuevo_pedido
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
    )

    dp.add_handler(conv_handler)

    # Handler para cuando un domiciliario presiona "Tomar pedido"
    dp.add_handler(CallbackQueryHandler(tomar_pedido, pattern=r"^tomar_\d+$"))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Comandos simples
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("id", cmd_id))

    # Flujo del pedido
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
    )

    dp.add_handler(conv_handler)

    # Handler para tomar pedidos
    dp.add_handler(CallbackQueryHandler(tomar_pedido, pattern=r"^tomar_\d+$"))

    updater.start_polling()
    updater.idle()
if __name__ == "__main__":
    main()
