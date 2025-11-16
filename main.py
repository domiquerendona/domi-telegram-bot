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

# -------------------------
# CONFIGURACIÓN BÁSICA
# -------------------------

TOKEN = os.getenv("BOT_TOKEN")  # Ya lo tienes en Railway
# ID del grupo donde están los domiciliarios.
# Lo configuraremos luego con /chatid + variable en Railway
COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))

# Estados de la conversación para crear pedido
(
    PEDIR_DIRECCION,
    PEDIR_VALOR_PEDIDO,
    PEDIR_FORMA_PAGO,
    PEDIR_ZONA,
    CONFIRMAR_PEDIDO,
) = range(5)

# "Base de datos" en memoria por ahora
orders = {}
next_order_id = 1


# -------------------------
# HANDLERS BÁSICOS
# -------------------------

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Hola Felipe, soy tu bot funcionando en Railway 🚀\n\n"
        "Comandos disponibles:\n"
        "/start - Mostrar este mensaje\n"
        "/nuevo_pedido - Crear un nuevo domicilio\n"
        "/chatid - Ver el ID de este chat (útil para el grupo de domiciliarios)"
    )


def chatid(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    update.message.reply_text(f"El ID de este chat es: {chat_id}", parse_mode="Markdown")


# -------------------------
# FLUJO: NUEVO PEDIDO
# -------------------------

def nuevo_pedido(update: Update, context: CallbackContext):
    update.message.reply_text("Vamos a crear un nuevo domicilio 👇\n\n"
                              "1️⃣ Envíame la dirección completa del cliente.",
                              parse_mode="Markdown")
    return PEDIR_DIRECCION


def pedir_valor_pedido(update: Update, context: CallbackContext):
    context.user_data["direccion"] = update.message.text.strip()
    update.message.reply_text(
        "2️⃣ ¿Cuánto vale el pedido (productos), en pesos?\n"
        "Solo escribe el número, sin puntos ni comas. Ej: 25000",
        parse_mode="Markdown",
    )
    return PEDIR_VALOR_PEDIDO


def pedir_forma_pago(update: Update, context: CallbackContext):
    texto = update.message.text.strip()
    if not texto.isdigit():
        update.message.reply_text("Por favor envía solo números. Ej: 25000")
        return PEDIR_VALOR_PEDIDO

    context.user_data["valor_pedido"] = int(texto)

    keyboard = [
        [
            InlineKeyboardButton("💵 Efectivo", callback_data="pago_efectivo"),
            InlineKeyboardButton("💳 Ya pagado", callback_data="pago_pagado"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "3️⃣ ¿Cómo va a pagar el cliente?", reply_markup=reply_markup
    )
    return PEDIR_FORMA_PAGO


def procesar_forma_pago(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "pago_efectivo":
        context.user_data["forma_pago"] = "Efectivo"
    else:
        context.user_data["forma_pago"] = "Ya pagado"

    keyboard = [
        [
            InlineKeyboardButton("Zona cercana", callback_data="zona_cercana"),
            InlineKeyboardButton("Zona media", callback_data="zona_media"),
        ],
        [
            InlineKeyboardButton("Zona lejana", callback_data="zona_lejana"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "4️⃣ Elige la zona del domicilio (luego podemos hacer esto automático):",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return PEDIR_ZONA


def procesar_zona(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    zona = query.data
    if zona == "zona_cercana":
        context.user_data["zona"] = "Cercana"
        context.user_data["valor_domicilio"] = 4000
    elif zona == "zona_media":
        context.user_data["zona"] = "Media"
        context.user_data["valor_domicilio"] = 5000
    else:
        context.user_data["zona"] = "Lejana"
        context.user_data["valor_domicilio"] = 6000

    direccion = context.user_data["direccion"]
    valor_pedido = context.user_data["valor_pedido"]
    forma_pago = context.user_data["forma_pago"]
    valor_dom = context.user_data["valor_domicilio"]

    texto_resumen = (
        "🧾 Resumen del pedido:\n\n"
        f"📍 Dirección: {direccion}\n"
        f"💰 Valor pedido: ${valor_pedido}\n"
        f"🪙 Forma de pago: {forma_pago}\n"
        f"🚴 Valor domicilio: ${valor_dom}\n\n"
        "¿Confirmas este domicilio?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_pedido"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_pedido"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        texto_resumen, reply_markup=reply_markup, parse_mode="Markdown"
    )
    return CONFIRMAR_PEDIDO


def confirmar_pedido(update: Update, context: CallbackContext):
    global next_order_id, orders
    query = update.callback_query
    query.answer()

    if query.data == "cancelar_pedido":
        query.edit_message_text("❌ Pedido cancelado.")
        return ConversationHandler.END

    # Crear pedido
    order_id = next_order_id
    next_order_id += 1

    orders[order_id] = {
        "id": order_id,
        "restaurant_chat_id": query.message.chat.id,
        "direccion": context.user_data["direccion"],
        "valor_pedido": context.user_data["valor_pedido"],
        "forma_pago": context.user_data["forma_pago"],
        "zona": context.user_data["zona"],
        "valor_domicilio": context.user_data["valor_domicilio"],
        "courier_id": None,
    }

    query.edit_message_text(f"✅ Pedido #{order_id} creado y enviado a los domiciliarios.")

    # Enviar al grupo de domiciliarios
    if COURIER_CHAT_ID != 0:
        order = orders[order_id]
        texto = (
            f"🚨 Nuevo domicilio #{order_id}\n\n"
            f"📍 Dirección: {order['direccion']}\n"
            f"💰 Valor pedido: ${order['valor_pedido']}\n"
            f"🪙 Pago: {order['forma_pago']}\n"
            f"📦 Zona: {order['zona']}\n"
            f"🚴 Valor domicilio: ${order['valor_domicilio']}\n\n"
            "El primero que tome la carrera se la queda."
        )
        keyboard = [
            [InlineKeyboardButton("🚴 Tomar pedido", callback_data=f"take_{order_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=COURIER_CHAT_ID,
            text=texto,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    else:
        context.bot.send_message(
            chat_id=query.message.chat.id,
            text="⚠️ Aún no hay configurado un grupo de domiciliarios. "
                 "Configura COURIER_CHAT_ID en Railway.",
        )

    # Limpiar datos temporales
    context.user_data.clear()
    return ConversationHandler.END


# -------------------------
# CUANDO UN DOMICILIARIO TOMA EL PEDIDO
# -------------------------

def tomar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data  # ejemplo: "take_3"
    try:
        order_id = int(data.split("_")[1])
    except (IndexError, ValueError):
        query.edit_message_text("Error al leer el ID del pedido.")
        return

    order = orders.get(order_id)
    if not order:
        query.edit_message_text("Este pedido ya no existe o fue eliminado.")
        return

    if order["courier_id"] is not None:
        query.answer("Este pedido ya fue tomado por otro domiciliario.", show_alert=True)
        return

    courier = query.from_user
    order["courier_id"] = courier.id

    # Editar mensaje en el grupo
    nuevo_texto = (
        f"✅ Pedido #{order_id} tomado\n\n"
        f"📍 Dirección: {order['direccion']}\n"
        f"💰 Valor pedido: ${order['valor_pedido']}\n"
        f"🪙 Pago: {order['forma_pago']}\n"
        f"📦 Zona: {order['zona']}\n"
        f"🚴 Valor domicilio: ${order['valor_domicilio']}\n\n"
        f"Asignado a: @{courier.username or courier.full_name}"
    )

    query.edit_message_text(nuevo_texto, parse_mode="Markdown")

    # Avisar al restaurante
    restaurant_chat_id = order["restaurant_chat_id"]
    context.bot.send_message(
        chat_id=restaurant_chat_id,
        text=(
            f"🚴 Tu pedido #{order_id} fue tomado por "
            f"@{courier.username or courier.full_name}."
        ),
    )


# -------------------------
# FUNCIÓN PRINCIPAL
# -------------------------

def main():
    if not TOKEN:
        print("ERROR: BOT_TOKEN no está configurado")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # /start y /chatid
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("chatid", chatid))

    # Conversación para /nuevo_pedido
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("nuevo_pedido", nuevo_pedido)],
        states={
            PEDIR_DIRECCION: [MessageHandler(Filters.text & ~Filters.command, pedir_valor_pedido)],
            PEDIR_VALOR_PEDIDO: [MessageHandler(Filters.text & ~Filters.command, pedir_forma_pago)],
            PEDIR_FORMA_PAGO: [CallbackQueryHandler(procesar_forma_pago, pattern="^pago_")],
            PEDIR_ZONA: [CallbackQueryHandler(procesar_zona, pattern="^zona_")],
            CONFIRMAR_PEDIDO: [CallbackQueryHandler(confirmar_pedido, pattern="^(confirmar_pedido|cancelar_pedido)$")],
        },
        fallbacks=[CommandHandler("cancelar", lambda u, c: ConversationHandler.END)],
    )
    dp.add_handler(conv_handler)

    # Handler para cuando un domiciliario toma un pedido
    dp.add_handler(CallbackQueryHandler(tomar_pedido, pattern=r"^take_\d+$"))

    updater.start_polling()
    updater.idle()


if _name_ == "_main_":
    main()
