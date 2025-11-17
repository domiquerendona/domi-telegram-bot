import os
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
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

TOKEN = os.getenv("BOT_TOKEN")  # Tu token del bot (lo tienes en Railway)
COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))  # Grupo de repartidores

# Estados de la conversación para crear pedido
PEDIR_DIRECCION, PEDIR_VALOR_PEDIDO, PEDIR_FORMA_PAGO, PEDIR_ZONA, CONFIRMAR_PEDIDO = range(5)

# “Base de datos” en memoria
orders = {}
next_order_id = 1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------- COMANDOS BÁSICOS ----------------

def start(update: Update, context: CallbackContext):
    """
    Mensaje de bienvenida.
    Agregamos un teclado con el botón /nuevo_pedido para no tener que escribirlo.
    """
    teclado = ReplyKeyboardMarkup(
        [[KeyboardButton("/nuevo_pedido")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    update.message.reply_text(
        "Hola, soy tu bot de domicilios 🚀\n\n"
        "Comando principal:\n"
        "🛒 /nuevo_pedido – crear un nuevo domicilio.",
        reply_markup=teclado,
    )

    return ConversationHandler.END


def cmd_id(update: Update, context: CallbackContext):
    """
    Muestra el ID del chat donde se ejecuta el comando.
    Útil para configurar nuevos grupos en Railway.
    """
    chat = update.effective_chat
    update.message.reply_text(f"El ID de este chat es: {chat.id}")


# ---------------- FLUJO DE NUEVO PEDIDO ----------------

def nuevo_pedido(update: Update, context: CallbackContext):
    """
    Inicia la creación de un pedido desde el grupo de restaurantes.
    """
    global next_order_id

    order_id = next_order_id
    next_order_id += 1

    # Guardamos el pedido con el chat del restaurante que lo crea
    orders[order_id] = {
        "restaurante_id": update.effective_chat.id,
        "direccion": "",
        "valor": 0,
        "forma_pago": "",
        "zona": "",
        "courier_id": None,
        "courier_nombre": None,
    }

    context.user_data["order_id"] = order_id

    update.message.reply_text("📍 Envíame la *dirección del cliente*:", parse_mode="Markdown")
    return PEDIR_DIRECCION


def pedir_valor(update: Update, context: CallbackContext):
    """
    Guarda la dirección y pide el valor del pedido.
    """
    order_id = context.user_data.get("order_id")
    if order_id is None:
        update.message.reply_text("Hubo un error interno. Escribe /nuevo_pedido otra vez.")
        return ConversationHandler.END

    orders[order_id]["direccion"] = update.message.text

    update.message.reply_text("💰 ¿Cuál es el *valor de los productos*? (solo números)", parse_mode="Markdown")
    return PEDIR_VALOR_PEDIDO


def pedir_forma_pago(update: Update, context: CallbackContext):
    """
    Guarda el valor del pedido y pregunta la forma de pago.
    """
    order_id = context.user_data.get("order_id")
    if order_id is None:
        update.message.reply_text("Hubo un error interno. Escribe /nuevo_pedido otra vez.")
        return ConversationHandler.END

    try:
        valor = int(update.message.text)
    except ValueError:
        update.message.reply_text("Por favor envíame *solo números* para el valor del pedido.", parse_mode="Markdown")
        return PEDIR_VALOR_PEDIDO

    orders[order_id]["valor"] = valor

    keyboard = [
        [
            InlineKeyboardButton("💵 Efectivo", callback_data="efectivo"),
            InlineKeyboardButton("💳 Transferencia", callback_data="transferencia"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text("Selecciona la *forma de pago*:", reply_markup=reply_markup, parse_mode="Markdown")
    return PEDIR_FORMA_PAGO


def recibir_forma_pago(update: Update, context: CallbackContext):
    """
    Recibe la forma de pago desde el botón y pide la zona/barrio.
    """
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if order_id is None:
        query.edit_message_text("Hubo un error interno. Escribe /nuevo_pedido otra vez.")
        return ConversationHandler.END

    orders[order_id]["forma_pago"] = query.data

    query.edit_message_text("✅ Forma de pago registrada.\n\nAhora dime la *zona/barrio*:", parse_mode="Markdown")
    return PEDIR_ZONA


def pedir_confirmacion(update: Update, context: CallbackContext):
    """
    Guarda la zona y muestra resumen para confirmar o cancelar.
    """
    order_id = context.user_data.get("order_id")
    if order_id is None:
        update.message.reply_text("Hubo un error interno. Escribe /nuevo_pedido otra vez.")
        return ConversationHandler.END

    orders[order_id]["zona"] = update.message.text
    order = orders[order_id]

    resumen = (
        f"🧾 *Resumen del pedido #{order_id}:*\n\n"
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
    """
    Cuando el restaurante confirma, se envía el aviso al grupo de repartidores.
    """
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if order_id is None:
        query.edit_message_text("Hubo un error interno. Escribe /nuevo_pedido otra vez.")
        return ConversationHandler.END

    order = orders[order_id]

    # Aviso al restaurante
    query.edit_message_text("✅ Pedido confirmado. Buscando domiciliario...")

    # Mensaje al grupo de domiciliarios
    if COURIER_CHAT_ID != 0:
        texto_couriers = (
            f"🚨 *Nuevo domicilio disponible* #{order_id}\n\n"
            f"📍 Dirección: {order['direccion']}\n"
            f"💰 Valor productos: {order['valor']}\n"
            f"💳 Forma de pago: {order['forma_pago']}\n"
            f"📌 Zona: {order['zona']}\n\n"
            "El primero que acepte se queda con la carrera. 🛵"
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
    """
    El restaurante cancela antes de enviarlo a los repartidores.
    """
    query = update.callback_query
    query.answer()
    query.edit_message_text("❌ Pedido cancelado.")
    return ConversationHandler.END


def tomar_pedido(update: Update, context: CallbackContext):
    """
    Un domiciliario pulsa el botón "Tomar pedido".
    """
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
    courier_nombre = update.effective_user.first_name

    order["courier_id"] = courier_id
    order["courier_nombre"] = courier_nombre

    # Editamos mensaje en el grupo de repartidores
    query.edit_message_text(f"✅ Pedido #{order_id} tomado por: *{courier_nombre}*.", parse_mode="Markdown")

    # Enviamos detalles al domiciliario por privado
    texto_courier = (
        f"✅ *Pedido asignado* #{order_id}\n\n"
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

    # Avisamos al restaurante (grupo donde se creó el pedido)
    restaurante_id = order["restaurante_id"]
    try:
        context.bot.send_message(
            chat_id=restaurante_id,
            text=f"🛵 El domiciliario *{courier_nombre}* tomó el pedido #{order_id}.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Error enviando mensaje al restaurante: {e}")


def cancelar_conversacion(update: Update, context: CallbackContext):
    """
    Permite cortar el flujo con /cancelar.
    """
    update.message.reply_text("❌ Conversación cancelada.")
    return ConversationHandler.END


# ---------------- MAIN ----------------

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Comandos simples
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("id", cmd_id))

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
