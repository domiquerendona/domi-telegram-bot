import os
from datetime import datetime, timedelta

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

# ID del grupo de repartidores
COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))

# ID del grupo de restaurantes (ALIADOS)
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

# Estados de la conversación /nuevo_pedido
PEDIR_DIRECCION, PEDIR_VALOR_PEDIDO, PEDIR_FORMA_PAGO, PEDIR_ZONA, CONFIRMAR_PEDIDO = range(5)

# "Base de datos" simple en memoria
orders = {}          # order_id -> dict con datos del pedido
next_order_id = 1    # contador de pedidos

# Bloqueos de repartidores: courier_id -> datetime de fin de bloqueo
bloqueos = {}


# ------------- FUNCIONES AUXILIARES -------------

def esta_bloqueado(courier_id: int) -> bool:
    """Devuelve True si el repartidor sigue bloqueado, False si no."""
    if courier_id in bloqueos:
        if datetime.now() < bloqueos[courier_id]:
            return True
        # bloqueo expirado
        del bloqueos[courier_id]
    return False


def enviar_pedido_a_repartidores(order_id: int, context: CallbackContext) -> None:
    """Publica o republica un pedido en el grupo de repartidores."""
    order = orders.get(order_id)
    if not order:
        return

    if COURIER_CHAT_ID == 0:
        return

    texto = (
        f"🚨 *Nuevo domicilio disponible #{order_id}*\n\n"
        f"📍 Dirección: {order['direccion']}\n"
        f"💰 Valor productos: {order['valor']}\n"
        f"💳 Forma de pago: {order['forma_pago']}\n"
        f"📌 Zona: {order['zona']}\n\n"
        "El primero que toque el botón se queda con la carrera."
    )

    keyboard = [[InlineKeyboardButton("🛵 Tomar pedido", callback_data=f"tomar_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=COURIER_CHAT_ID,
        text=texto,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


# ------------- MANEJADORES DE COMANDOS -------------

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

    if RESTAURANT_CHAT_ID != 0 and chat.id != RESTAURANT_CHAT_ID:
        update.message.reply_text(
            "Este comando solo funciona en el *grupo de restaurantes*.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    order_id = next_order_id
    next_order_id += 1

    orders[order_id] = {
        "restaurante_chat_id": chat.id,              # grupo ALIADOS
        "restaurante_user_id": update.effective_user.id,  # usuario que crea el pedido
        "direccion": "",
        "valor": 0,
        "forma_pago": "",
        "zona": "",
        "courier_id": None,
        "estado": "pendiente",   # pendiente / tomado / en_tienda / esperando / con_pedido / entregado
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

    keyboard = [[
        InlineKeyboardButton("💵 Efectivo", callback_data="pago_efectivo"),
        InlineKeyboardButton("💳 Transferencia", callback_data="pago_transferencia"),
    ]]
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

    keyboard = [[
        InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_pedido"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_pedido"),
    ]]
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

    query.edit_message_text("✅ Pedido confirmado. Buscando domiciliario...")

    # Publicar el pedido en el grupo de repartidores
    enviar_pedido_a_repartidores(order_id, context)

    return ConversationHandler.END


def cancelar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if order_id in orders:
        del orders[order_id]

    query.edit_message_text("❌ Pedido cancelado.")
    return ConversationHandler.END


def cancelar_conversacion(update: Update, context: CallbackContext):
    update.message.reply_text("Conversación cancelada. Puedes empezar de nuevo con /nuevo_pedido.")
    return ConversationHandler.END


# ------------- MANEJADOR: TOMAR PEDIDO -------------

def tomar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data  # tomar_ID
    order_id = int(data.split("_")[1])
    order = orders.get(order_id)

    if not order:
        query.edit_message_text("Este pedido ya no está disponible.")
        return

    courier_id = update.effective_user.id

    # 1. Verificar bloqueo
    if esta_bloqueado(courier_id):
        desbloqueo = bloqueos[courier_id].strftime("%H:%M")
        query.answer(f"No puedes tomar pedidos hasta las {desbloqueo}.", show_alert=True)
        return

    # 2. Verificar si ya fue tomado
    if order["courier_id"] is not None:
        query.edit_message_text("⚠️ Otro repartidor ya tomó este pedido.")
        return

    # 3. Asignar pedido
    order["courier_id"] = courier_id
    order["hora_tomado"] = datetime.now()
    order["estado"] = "tomado"

    # Mensaje en el grupo de repartidores
    query.edit_message_text(
        "🛵 Pedido tomado por un repartidor.\n\n"
        "⏱ Recuerda: tiene máximo 15 minutos para llegar."
    )

    # 1) Mensaje privado al repartidor con toda la info (sin botones todavía)
    context.bot.send_message(
        chat_id=courier_id,
        text=(
            "✅ *Pedido asignado*\n\n"
            "Tienes máximo *15 minutos* para llegar al restaurante.\n\n"
            f"🧾 *Datos del pedido #{order_id}:*\n"
            f"📍 Dirección: {order['direccion']}\n"
            f"💰 Valor productos: {order['valor']}\n"
            f"💳 Pago: {order['forma_pago']}\n"
            f"📌 Zona: {order['zona']}\n\n"
            "Cuando llegues al aliado, él confirmará tu llegada y "
            "te enviaré un botón para marcar que *ya tienes el pedido*."
        ),
        parse_mode="Markdown",
    )

    # 2) Aviso al aliado SOLO EN PRIVADO con botón "Repartidor llegó"
    rest_user_id = order.get("restaurante_user_id")
    if rest_user_id:
        courier = update.effective_user
        nombre = courier.full_name
        user_link = f"@{courier.username}" if courier.username else ""
        texto_rest = (
            f"🛵 Tu pedido #{order_id} fue tomado por *{nombre}* {user_link}.\n\n"
            "Cuando el repartidor llegue a tu negocio, toca el botón de abajo:"
        )

        keyboard_rest = [[InlineKeyboardButton("✅ Repartidor llegó", callback_data=f"llego_{order_id}")]]
        reply_markup_rest = InlineKeyboardMarkup(keyboard_rest)

        context.bot.send_message(
            chat_id=rest_user_id,
            text=texto_rest,
            reply_markup=reply_markup_rest,
            parse_mode="Markdown",
        )

    # 3) Temporizador de 15 minutos
    context.job_queue.run_once(
        revisar_llegada,
        15 * 60,
        context={"order_id": order_id},
    )


# ------------- LLEGADA A LA TIENDA -------------

def confirmar_llegada_repartidor(update: Update, context: CallbackContext):
    """El aliado confirma que el repartidor llegó a la tienda (desde su privado)."""
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    order = orders.get(order_id)

    if not order:
        query.edit_message_text("Este pedido ya no está disponible.")
        return

    courier_id = order.get("courier_id")
    if not courier_id:
        query.edit_message_text("Aún no hay repartidor asignado para este pedido.")
        return

    # Cambiar estado para que revisar_llegada ya no lo trate como 'tomado'
    order["estado"] = "en_tienda"

    # Respuesta al aliado (en privado)
    query.edit_message_text(
        "✅ Marcaste que el repartidor *ya llegó* a tu negocio.",
        parse_mode="Markdown",
    )

    # Enviar al repartidor el botón "Ya tengo el pedido"
    keyboard = [[InlineKeyboardButton("✅ Ya tengo el pedido", callback_data=f"tengo_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=courier_id,
        text=(
            f"ℹ️ El aliado confirmó que ya llegaste para el pedido #{order_id}.\n\n"
            "Cuando el aliado te entregue el pedido, toca el botón de abajo:"
        ),
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


# ------------- FLUJO DEL REPARTIDOR: TENGO PEDIDO / ENTREGADO -------------

def tengo_pedido(update: Update, context: CallbackContext):
    """El repartidor confirma que el aliado ya le entregó el pedido."""
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    order = orders.get(order_id)
    courier_id = query.from_user.id

    if not order or order.get("courier_id") != courier_id:
        query.answer("No encuentro este pedido o ya no está asignado a ti.", show_alert=True)
        return

    # Cambiamos el estado
    order["estado"] = "con_pedido"

    # Mensaje al repartidor con nuevo botón
    keyboard = [[InlineKeyboardButton("📦 Pedido entregado", callback_data=f"entregado_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "👌 Marcaste que *ya tienes el pedido*.\n\n"
        "Cuando lo entregues al cliente, toca el botón de abajo:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


def pedido_entregado(update: Update, context: CallbackContext):
    """El repartidor marca que el pedido fue entregado al cliente."""
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    order = orders.get(order_id)
    courier_id = query.from_user.id

    if not order or order.get("courier_id") != courier_id:
        query.answer("No encuentro este pedido o ya no está asignado a ti.", show_alert=True)
        return

    order["estado"] = "entregado"

    # Confirmación al repartidor
    query.edit_message_text(
        "✅ Marcaste este pedido como *ENTREGADO*. ¡Gracias por tu servicio! 🛵",
        parse_mode="Markdown",
    )

    # Notificación al aliado SOLO EN PRIVADO
    rest_user_id = order.get("restaurante_user_id")
    if rest_user_id:
        courier = query.from_user
        nombre = courier.full_name
        user_link = f"@{courier.username}" if courier.username else ""
        context.bot.send_message(
            chat_id=rest_user_id,
            text=f"✅ Tu pedido #{order_id} fue marcado como *ENTREGADO* por {nombre} {user_link}.",
            parse_mode="Markdown",
        )

    # Si quisieras, aquí podrías borrar el pedido de la "BD":
    # del orders[order_id]


# ------------- REVISIÓN DE LLEGADA (15 MIN) -------------

def revisar_llegada(context: CallbackContext):
    data = context.job.context
    order_id = data["order_id"]
    order = orders.get(order_id)

    if not order:
        return

    # Si el pedido ya fue completado o el aliado ya confirmó llegada
    if order["estado"] != "tomado":
        return

    rest_user_id = order.get("restaurante_user_id")
    if not rest_user_id:
        return

    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Repartidor llegó", callback_data=f"llego_{order_id}")],
        [
            InlineKeyboardButton("🔄 Seguir esperando", callback_data=f"esperar_{order_id}"),
            InlineKeyboardButton("❌ Buscar otro repartidor", callback_data=f"cancelar_{order_id}"),
        ],
    ])

    context.bot.send_message(
        chat_id=rest_user_id,
        text=(
            "⚠️ Han pasado 15 minutos y el repartidor aún no reporta llegada.\n\n"
            "¿Qué deseas hacer?"
        ),
        reply_markup=botones,
    )


def seguir_esperando(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])

    if order_id in orders:
        orders[order_id]["estado"] = "esperando"

    query.edit_message_text("👌 Seguirás esperando al repartidor.")


def cancelar_repartidor(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    order = orders.get(order_id)

    if not order:
        query.edit_message_text("Este pedido ya no está disponible.")
        return

    courier_id = order.get("courier_id")

    # Suspender al repartidor 2 horas (si existe)
    if courier_id:
        bloqueos[courier_id] = datetime.now() + timedelta(hours=2)

        context.bot.send_message(
            chat_id=courier_id,
            text="⛔ Has sido suspendido 2 horas por incumplir el tiempo máximo de llegada.",
        )

    # Poner pedido nuevamente como pendiente
    order["courier_id"] = None
    order["estado"] = "pendiente"

    query.edit_message_text("❌ El repartidor fue rechazado. Buscando uno nuevo...")

    # Republicar el pedido en el grupo de repartidores
    enviar_pedido_a_repartidores(order_id, context)


# ------------- FUNCIÓN PRINCIPAL -------------

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # /start
    dp.add_handler(CommandHandler("start", start))

    # Flujo /nuevo_pedido
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("nuevo_pedido", nuevo_pedido)],
        states={
            PEDIR_DIRECCION: [
                MessageHandler(Filters.text & ~Filters.command, pedir_valor)
            ],
            PEDIR_VALOR_PEDIDO: [
                MessageHandler(Filters.text & ~Filters.command, pedir_forma_pago)
            ],
            PEDIR_FORMA_PAGO: [
                CallbackQueryHandler(recibir_forma_pago)
            ],
            PEDIR_ZONA: [
                MessageHandler(Filters.text & ~Filters.command, pedir_confirmacion)
            ],
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

    # Botón del aliado: "Repartidor llegó" (ahora en privado)
    dp.add_handler(CallbackQueryHandler(confirmar_llegada_repartidor, pattern=r"^llego_\d+$"))

    # Botones del repartidor en su chat privado
    dp.add_handler(CallbackQueryHandler(tengo_pedido, pattern=r"^tengo_\d+$"))
    dp.add_handler(CallbackQueryHandler(pedido_entregado, pattern=r"^entregado_\d+$"))

    # Opciones del aliado después de los 15 minutos (en privado)
    dp.add_handler(CallbackQueryHandler(seguir_esperando, pattern=r"^esperar_\d+$"))
    dp.add_handler(CallbackQueryHandler(cancelar_repartidor, pattern=r"^cancelar_\d+$"))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
