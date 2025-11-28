import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

from db import (
    init_db,
    ensure_user,
    get_user_by_telegram_id,
    get_setting,
    set_setting,
    # Aliados
    create_ally,
    get_ally_by_user_id,
    get_pending_allies,
    get_ally_by_id,
    update_ally_status,
    # Direcciones de aliados
    create_ally_location,
    get_ally_locations,
    set_default_ally_location,
    update_ally_location,
    delete_ally_location,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

# Estados del registro de aliados
ALLY_NAME, ALLY_OWNER, ALLY_ADDRESS, ALLY_CITY, ALLY_BARRIO = range(5)

# Estados para registro de repartidores
COURIER_FULLNAME, COURIER_IDNUMBER, COURIER_PHONE, COURIER_CITY, COURIER_BARRIO, COURIER_PLATE, COURIER_BIKETYPE, COURIER_CONFIRM = range(5, 13)

# Estados para crear un pedido
PEDIDO_NOMBRE, PEDIDO_TELEFONO, PEDIDO_DIRECCION = range(13, 16)

def start(update, context):
    """Comando /start y /menu: mensaje de bienvenida simple con estado del usuario."""
    user_tg = update.effective_user

    # Aseguramos que el usuario exista en la tabla users
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    # Revisamos si ya es aliado y/o repartidor
    ally = get_ally_by_user_id(user_db_id)
    courier = get_courier_by_user_id(user_db_id)

    estado_lineas = []
    if ally:
        estado_lineas.append(
            f"• Aliado: {ally['business_name']} (estado: {ally['status']})."
        )
    if courier:
        codigo = courier["code"] if courier["code"] else "sin código"
        estado_lineas.append(
            f"• Repartidor código interno: {codigo} (estado: {courier['status']})."
        )

    if not estado_lineas:
        estado_text = "Aún no estás registrado como aliado ni como repartidor."
    else:
        estado_text = "\n".join(estado_lineas)

    mensaje = (
        "🐢 Bienvenido a Domiquerendona 🐢\n\n"
        "Sistema para conectar negocios aliados con repartidores de confianza.\n\n"
        "Tu estado actual:\n"
        f"{estado_text}\n\n"
        "Comandos principales:\n"
        "• /soy_aliado  - Registrar tu negocio aliado\n"
        "• /soy_repartidor  - Registrarte como repartidor\n"
        "• /nuevo_pedido  - Crear nuevo pedido (aliados aprobados)\n"
        "• /menu  - Volver a ver este menú\n"
    )

    update.message.reply_text(mensaje)

def menu(update, context):
    """Alias de /start para mostrar el menú principal."""
    return start(update, context)

def cancel(update, context):
    """Permite cancelar cualquier proceso y limpiar datos temporales."""
    context.user_data.clear()
    update.message.reply_text(
        "Operación cancelada.\n\nPuedes usar /menu o /start para volver al inicio."
    )

def cmd_id(update, context):
    """Muestra el user_id de Telegram del usuario."""
    user = update.effective_user
    update.message.reply_text(f"Tu user_id es: {user.id}")

def pedido_telefono_cliente(update, context):
    # Guardar teléfono del cliente
    context.user_data["customer_phone"] = update.message.text.strip()

    # Pedir ahora la dirección de entrega
    update.message.reply_text("Ahora escribe la dirección de entrega del cliente.")
    return PEDIDO_DIRECCION
    
def pedido_direccion_cliente(update, context):
    # Guardar dirección del cliente
    context.user_data["customer_address"] = update.message.text.strip()

    # Recuperar datos para mostrarlos al final
    nombre = context.user_data.get("customer_name", "")
    telefono = context.user_data.get("customer_phone", "")
    direccion = context.user_data.get("customer_address", "")

    texto = (
        "Por ahora /nuevo_pedido está en construcción.\n"
        "Hemos guardado estos datos del cliente:\n"
        f"- Nombre: {nombre}\n"
        f"- Teléfono: {telefono}\n"
        f"- Dirección: {direccion}"
    )

    update.message.reply_text(texto)
    return ConversationHandler.END
    
# ----- REGISTRO DE ALIADO -----

def soy_aliado(update, context):
    user = update.effective_user
    ensure_user(user.id, user.username)
    print(f"[DEBUG] soy_aliado llamado por user_id={user.id}")
    update.message.reply_text(
        "👨‍🍳 Registro de aliado\n\n"
        "Escribe el nombre del negocio:"
    )
    return ALLY_NAME


def ally_name(update, context):
    texto = update.message.text.strip()
    print(f"[DEBUG] ally_name, texto recibido = {texto!r}")
    if not texto:
        update.message.reply_text("El nombre del negocio no puede estar vacío. Escríbelo de nuevo:")
        return ALLY_NAME

    context.user_data["business_name"] = texto
    update.message.reply_text("Escribe el nombre del dueño o administrador:")
    return ALLY_OWNER


def ally_owner(update, context):
    texto = update.message.text.strip()
    print(f"[DEBUG] ally_owner, texto recibido = {texto!r}")
    if not texto:
        update.message.reply_text("El nombre del dueño no puede estar vacío. Escríbelo de nuevo:")
        return ALLY_OWNER

    context.user_data["owner_name"] = texto
    update.message.reply_text("Escribe la dirección del negocio:")
    return ALLY_ADDRESS


def ally_address(update, context):
    texto = update.message.text.strip()
    print(f"[DEBUG] ally_address, texto recibido = {texto!r}")
    context.user_data["address"] = texto
    update.message.reply_text("Escribe la ciudad del negocio:")
    return ALLY_CITY

def ally_city(update, context):
    """Guarda la ciudad y pide el teléfono de contacto del negocio."""
    texto = update.message.text.strip()
    user_id = update.effective_user.id

    if not texto:
        update.message.reply_text("La ciudad del negocio no puede estar vacía. Escríbela de nuevo:")
        return ALLY_CITY

    city = texto

    # 🔹 Guardar la ciudad en user_data
    context.user_data["city"] = city
    print(f"[DEBUG] ally_city: user_id={user_id}, city={city!r}")

    update.message.reply_text("Escribe el teléfono de contacto del negocio:")
    # Pasamos al estado donde pedimos teléfono/barrio
    return ALLY_BARRIO

def ally_barrio(update, context):
    """
    Este estado se usa dos veces:
    1) Primero para guardar el teléfono del negocio.
    2) Luego para guardar el barrio y crear el aliado en la BD.
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # 1) Si aún NO hemos guardado el teléfono, este mensaje es el teléfono
    if "ally_phone" not in context.user_data:
        phone = text
        context.user_data["ally_phone"] = phone
        print(f"[DEBUG] ally_barrio (teléfono): user_id={user_id}, phone={phone}")

        update.message.reply_text("Escribe el barrio o sector del negocio:")
        # Seguimos en el mismo estado ALLY_BARRIO, pero ahora esperando el barrio
        return ALLY_BARRIO

    # 2) Si ya hay teléfono guardado, ahora este mensaje es el barrio
    barrio = text
    context.user_data["ally_barrio"] = barrio
    print(f"[DEBUG] ally_barrio (barrio): user_id={user_id}, barrio={barrio}")

    # Recuperar todos los datos del aliado
    business_name = context.user_data.get("business_name")
    owner_name = context.user_data.get("owner_name")
    address = context.user_data.get("address")
    city = context.user_data.get("city")
    barrio = context.user_data.get("ally_barrio")
    phone = context.user_data.get("ally_phone")

    print(
        f"[DEBUG] Datos para create_ally: user_id={user_id}, "
        f"business_name={business_name}, owner_name={owner_name}, "
        f"address={address}, city={city}, barrio={barrio}, phone={phone}"
    )

    try:
        # Crear aliado en la tabla allies (incluyendo teléfono)
        ally_id = create_ally(
            user_id=user_id,
            business_name=business_name,
            owner_name=owner_name,
            address=address,
            city=city,
            barrio=barrio,
            phone=phone,
        )
        print(f"[DEBUG] Aliado creado en la BD con id={ally_id}")

        # Crear dirección principal en ally_locations
        create_ally_location(
            ally_id=ally_id,
            label="Principal",
            address=address,
            city=city,
            barrio=barrio,
            phone=None,  # si luego quieres, aquí también puedes usar phone
            is_default=True,
        )
        print("[DEBUG] Dirección principal creada")

    except Exception as e:
        print(f"[ERROR] Error al crear aliado o su dirección: {e}")
        update.message.reply_text(
            f"⚠️ Error técnico al guardar tu registro de aliado:\n{e}"
        )
        return ConversationHandler.END

    # Confirmar al usuario (SIN parse_mode)
    update.message.reply_text(
        "✅ Aliado registrado exitosamente!\n\n"
        f"🏪 Negocio: {business_name}\n"
        f"👤 Dueño: {owner_name}\n"
        f"📞 Teléfono: {phone}\n"
        f"📍 Dirección: {address}, {barrio}, {city}\n"
        "Tu estado es 'PENDING'."
    )

    # Limpiar datos temporales
    context.user_data.clear()
    return ConversationHandler.END

def soy_repartidor(update, context):
    user = update.effective_user
    ensure_user(user.id, user.username)
    update.message.reply_text(
        "🛵 Registro de repartidor\n\n"
        "Escribe tu nombre completo:"
    )
    return COURIER_FULLNAME

def courier_fullname(update, context):
    context.user_data["full_name"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe tu número de identificación:"
    )
    return COURIER_IDNUMBER

def courier_idnumber(update, context):
    context.user_data["id_number"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe tu número de celular:"
    )
    return COURIER_PHONE

def courier_phone(update, context):
    context.user_data["phone"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe la ciudad donde trabajas:"
    )
    return COURIER_CITY

def courier_city(update, context):
    context.user_data["city"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el barrio o sector principal donde trabajas:"
    )
    return COURIER_BARRIO

def courier_barrio(update, context):
    context.user_data["barrio"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe la placa de tu moto (o escribe 'ninguna' si no tienes):"
    )
    return COURIER_PLATE

def courier_plate(update, context):
    context.user_data["plate"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el tipo de moto (Ejemplo: Bóxer 100, FZ, scooter, bicicleta, etc.):"
    )
    return COURIER_BIKETYPE
    
def courier_biketype(update, context):
    # Guardar tipo de moto
    context.user_data["bike_type"] = update.message.text.strip()

    # Sacar los datos de forma segura (usando get por si falta alguno)
    full_name = context.user_data.get("full_name", "")
    id_number = context.user_data.get("id_number", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    plate = context.user_data.get("plate", "")
    bike_type = context.user_data.get("bike_type", "")

    resumen = (
        "Verifica tus datos de repartidor:\n\n"
        f"Nombre: {full_name}\n"
        f"Cédula: {id_number}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Placa: {plate}\n"
        f"Tipo de moto: {bike_type}\n\n"
        "Si todo está bien escribe: SI\n"
        "Si quieres corregir, cancela y vuelve a usar /soy_repartidor"
    )

    update.message.reply_text(resumen)
    return COURIER_CONFIRM

def courier_confirm(update, context):
    confirm_text = update.message.text.strip().upper()
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)

    # Si el usuario no escribe SI, cancelamos
    if confirm_text not in ("SI", "SÍ", "SI.", "SÍ."):
        update.message.reply_text(
            "Registro cancelado.\n\n"
            "Si deseas intentarlo de nuevo, usa /soy_repartidor."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Tomar los datos de forma segura
    full_name = context.user_data.get("full_name", "")
    id_number = context.user_data.get("id_number", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    plate = context.user_data.get("plate", "")
    bike_type = context.user_data.get("bike_type", "")

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

    mensaje_final = (
        "Repartidor registrado exitosamente.\n\n"
        f"Nombre: {full_name}\n"
        f"Cédula: {id_number}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Placa: {plate}\n"
        f"Tipo de moto: {bike_type}\n"
        f"Código interno: {code}\n\n"
        "Tu estado es: PENDING. El administrador deberá aprobarte "
        "antes de que puedas tomar pedidos."
    )

    update.message.reply_text(mensaje_final)
    context.user_data.clear()
    return ConversationHandler.END
    
def nuevo_pedido(update, context):
    user = update.effective_user

    # Asegurar usuario en BD
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)

    if not db_user:
        update.message.reply_text(
            "Aún no estás registrado en el sistema. Usa /start primero."
        )
        return ConversationHandler.END

    # Verificar si es aliado
    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text(
            "Aún no estás registrado como aliado.\n"
            "Si tienes un negocio, regístrate con /soy_aliado."
        )
        return ConversationHandler.END

    # Verificar estado del aliado
    if ally["status"] != "APPROVED":
        update.message.reply_text(
            "Tu registro como aliado todavía no ha sido aprobado por el administrador.\n"
            "Cuando tu estado sea APPROVED podrás crear pedidos con /nuevo_pedido."
        )
        return ConversationHandler.END

    # Si todo está bien, empezar conversación del pedido
    update.message.reply_text(
        "Crear nuevo pedido.\n\n"
        "Perfecto, empecemos.\n"
        "Primero escribe el nombre del cliente."
    )
    return PEDIDO_NOMBRE

def pedido_nombre_cliente(update, context):
    # Guardar nombre del cliente
    context.user_data["customer_name"] = update.message.text.strip()

    # Pedir teléfono
    update.message.reply_text("Ahora escribe el número de teléfono del cliente.")
    return PEDIDO_TELEFONO

def pedido_telefono_cliente(update, context):
    # Guardar teléfono del cliente
    context.user_data["customer_phone"] = update.message.text.strip()

    # Pedir ahora la dirección
    update.message.reply_text("Ahora escribe la dirección de entrega del cliente.")
    return PEDIDO_DIRECCION
    
def pedido_direccion_cliente(update, context):
    # Guardar dirección del cliente
    context.user_data["customer_address"] = update.message.text.strip()

    # Recuperar datos para mostrarlos al final
    nombre = context.user_data.get("customer_name", "")
    telefono = context.user_data.get("customer_phone", "")
    direccion = context.user_data.get("customer_address", "")

    texto = (
        "Por ahora /nuevo_pedido está en construcción.\n"
        "Hemos guardado estos datos del cliente:\n"
        f"- Nombre: {nombre}\n"
        f"- Teléfono: {telefono}\n"
        f"- Dirección: {direccion}"
    )

    update.message.reply_text(texto)
    return ConversationHandler.END

    # Buscar el usuario en la BD
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        update.message.reply_text(
            "Aún no estás registrado en el sistema. Usa /start primero."
        )
        return

    # Verificar si es aliado
    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text(
            "Aún no estás registrado como aliado.\n\n"
            "Si tienes un negocio, regístrate con /soy_aliado."
        )
        return

    # Verificar estado del aliado
    if ally["status"] != "APPROVED":
        update.message.reply_text(
            "Tu registro como aliado todavía no ha sido aprobado por el administrador.\n\n"
            "Cuando tu estado sea APPROVED podrás crear pedidos con /nuevo_pedido."
        )
        return

    # Si todo está bien
        update.message.reply_text(
    "✅ Perfecto, eres un aliado APROBADO.\n"
    "Desde ahora puedes usar /nuevo_pedido para crear pedidos."
    )
    
def pedido_nombre_cliente(update, context):
    context.user_data["customer_name"] = update.message.text.strip()
    update.message.reply_text("Ahora escribe el número de teléfono del cliente.")
    return PEDIDO_TELEFONO
    
def pedido_telefono_cliente(update, context):
    # Guardamos el teléfono del cliente
    context.user_data["customer_phone"] = update.message.text.strip()

    # Mensaje de cierre temporal
    update.message.reply_text(
        "Por ahora /nuevo_pedido está en construcción.\n"
        "Hemos guardado el nombre y el teléfono del cliente."
    )
    
def aliados_pendientes(update, context):
    """Lista aliados PENDING solo para el administrador."""
    user_id = update.effective_user.id
    print(f"user_id que envía el comando: {user_id}")
    print(f"ADMIN_USER_ID configurado: {ADMIN_USER_ID}")

    # Solo el admin puede usar este comando
    if user_id != ADMIN_USER_ID:
        update.message.reply_text("Este comando es solo para el administrador.")
        return

    # Intentar leer aliados pendientes de la BD
    try:
        allies = get_pending_allies()
    except Exception as e:
        print(f"[ERROR] en get_pending_allies(): {e}")
        update.message.reply_text("⚠️ Error interno al consultar aliados pendientes.")
        return

    if not allies:
        update.message.reply_text("No hay aliados pendientes por aprobar.")
        return

    # Enviar un mensaje por cada aliado pendiente, con botones
    for ally in allies:
        ally_id, business_name, owner_name, address, city, barrio, phone, status = ally

        texto = (
            "Aliados pendientes:\n"
            "-----------------------------\n"
            f"ID interno: {ally_id}\n"
            f"Negocio: {business_name}\n"
            f"Dueño: {owner_name}\n"
            f"Teléfono: {phone}\n"
            f"Dirección: {address}, {barrio}, {city}\n"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Aprobar",  callback_data=f"ally_approve_{ally_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"ally_reject_{ally_id}"),
            ]
        ]

        update.message.reply_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

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

# Conversación para /nuevo_pedido
nuevo_pedido_conv = ConversationHandler(
    entry_points=[CommandHandler("nuevo_pedido", nuevo_pedido)],
    states={
        PEDIDO_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command, pedido_nombre_cliente)
        ],
        PEDIDO_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command, pedido_telefono_cliente)
        ],
        PEDIDO_DIRECCION: [
            MessageHandler(Filters.text & ~Filters.command, pedido_direccion_cliente)
        ],
    },
    fallbacks=[],
)

def botones_aliados(update, context):
    """Maneja los botones de aprobar o rechazar aliados."""
    query = update.callback_query
    query.answer()

    data = query.data  # Ej: "aprobar_3" o "rechazar_5"

    if data.startswith("aprobar_"):
        ally_id = int(data.split("_")[1])
        update_ally_status(ally_id, "APPROVED")
        query.edit_message_text("✅ Aliado aprobado exitosamente.")
        return

    if data.startswith("rechazar_"):
        ally_id = int(data.split("_")[1])
        update_ally_status(ally_id, "REJECTED")
        query.edit_message_text("❌ Aliado rechazado.")
        return

    # Si llega algo inesperado
    query.edit_message_text("Comando no reconocido.")
    
def show_id(update, context):
    """Muestra el ID de Telegram del usuario que envía el comando."""
    user_id = update.effective_user.id
    update.message.reply_text(f"Tu ID de usuario es: {user_id}")
    
from telegram.ext import ConversationHandler 

def ally_approval_callback(update, context):
    """Maneja los botones de aprobar / rechazar aliados."""
    query = update.callback_query
    data = query.data            # Ej: "ally_approve_3" o "ally_reject_5"
    user_id = query.from_user.id

    # Solo el administrador puede usar estos botones
    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador puede usar estos botones.", show_alert=True)
        return

    # Separar la data del botón
    # ally_approve_3  -> ["ally", "approve", "3"]
    partes = data.split("_")
    if len(partes) != 3:
        query.answer("Datos de botón no válidos.")
        return

    _, accion, ally_id_str = partes

    # Convertir ID del aliado a entero
    try:
        ally_id = int(ally_id_str)
    except ValueError:
        query.answer("ID de aliado no válido.")
        return

    # Definir estado según el botón
    if accion == "approve":
        nuevo_estado = "APPROVED"
        texto_estado = "aprobado"
    elif accion == "reject":
        nuevo_estado = "REJECTED"
        texto_estado = "rechazado"
    else:
        query.answer("Acción no reconocida.")
        return

    # Actualizar en la BD
    try:
        update_ally_status(ally_id, nuevo_estado)
    except Exception as e:
        print(f"[ERROR] ally_approval_callback: {e}")
        query.answer(f"Error al actualizar el estado del aliado:\n{e}", show_alert=True)
        return

    # Confirmar al admin y editar el mensaje del botón
    query.answer(f"Aliado {texto_estado}.")
    query.edit_message_text(f"Aliado {ally_id} ha sido {texto_estado.upper()}.")

def main():
    # Inicializar base de datos
    init_db()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Comandos básicos
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))

    # Comandos administrativos
    dp.add_handler(CommandHandler("id", cmd_id))
    dp.add_handler(CommandHandler("aliados_pendientes", aliados_pendientes))
    dp.add_handler(CommandHandler("cancel", cancel))


    # Conversaciones completas
    dp.add_handler(CallbackQueryHandler(ally_approval_callback, pattern="^ally_"))
    dp.add_handler(ally_conv)            # /soy_aliado
    dp.add_handler(courier_conv)         # /soy_repartidor
    dp.add_handler(nuevo_pedido_conv)    # /nuevo_pedido

    # Iniciar el bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()

# trigger deploy

