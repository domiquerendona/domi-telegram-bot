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

from db import create_admin, get_admin_by_user_id  #administrador local

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
    get_all_allies,
    update_ally,
    delete_ally,
    # Direcciones de aliados
    create_ally_location,
    get_ally_locations,
    get_default_ally_location,
    set_default_ally_location,
    update_ally_location,
    delete_ally_location,
    # Repartidores
    create_courier,
    get_courier_by_user_id,
    get_courier_by_id,
    get_pending_couriers,      # ← NUEVO
    update_courier_status,     # ← NUEVO 
    get_all_couriers,
    update_courier,
    delete_courier,
    # Pedidos
    create_order,
    set_order_status,
    assign_order_to_courier,
    get_order_by_id,
    get_orders_by_ally,
    get_orders_by_courier,
    # HERRAMIENTAS ADMINISTRATIVAS NUEVAS
    get_totales_registros,
    # Calificaciones
    add_courier_rating,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))    # Administrador de Plataforma
COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

def es_admin(user_id: int) -> bool:
    """Devuelve True si el user_id es el administrador de plataforna."""
    return user_id == ADMIN_USER_ID

# Estados del registro de aliados
ALLY_NAME, ALLY_OWNER, ALLY_ADDRESS, ALLY_CITY, ALLY_BARRIO = range(5)

# Estados para registro de repartidores
COURIER_FULLNAME, COURIER_IDNUMBER, COURIER_PHONE, COURIER_CITY, COURIER_BARRIO, COURIER_PLATE, COURIER_BIKETYPE, COURIER_CONFIRM = range(5, 13)

LOCAL_ADMIN_NAME, LOCAL_ADMIN_PHONE, LOCAL_ADMIN_CITY, LOCAL_ADMIN_BARRIO, LOCAL_ADMIN_ACCEPT = range(300, 305)

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
    1) Para guardar el teléfono del negocio.
    2) Luego para guardar el barrio y crear el aliado en la BD.
    """
    from telegram.ext import ConversationHandler

    user_id = update.effective_user.id
    text = update.message.text.strip()

    # 1) PRIMER MENSAJE → teléfono
    if "ally_phone" not in context.user_data:
        phone = text
        context.user_data["ally_phone"] = phone
        print(f"[DEBUG] ally_barrio (teléfono): user_id={user_id}, phone={phone}")

        update.message.reply_text("Escribe el barrio o sector del negocio:")
        return ALLY_BARRIO

    # 2) SEGUNDO MENSAJE → barrio
    barrio = text
    context.user_data["ally_barrio"] = barrio
    print(f"[DEBUG] ally_barrio (barrio): user_id={user_id}, barrio={barrio}")

    # Recuperar datos
    business_name = context.user_data.get("business_name")
    owner_name = context.user_data.get("owner_name")
    address = context.user_data.get("address")
    city = context.user_data.get("city")
    phone = context.user_data.get("ally_phone")

    print(
        f"[DEBUG] Datos para create_ally: user_id={user_id}, business_name={business_name}, "
        f"owner_name={owner_name}, address={address}, city={city}, barrio={barrio}, phone={phone}"
    )

    try:
        # --- Crear aliado ---
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

        # --- Crear dirección principal ---
        create_ally_location(
            ally_id=ally_id,
            label="Principal",
            address=address,
            city=city,
            barrio=barrio,
            phone=None,
            is_default=True,
        )
        print("[DEBUG] Dirección principal creada")

       # --- Notificar al Administrador de Plataforma ---
try:
    context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=(
            "Nuevo registro de ALIADO pendiente en la Plataforma:\n\n"
            f"Negocio: {business_name}\n"
            f"Dueño: {owner_name}\n"
            f"Teléfono: {phone}\n"
            f"Ciudad: {city}\n"
            f"Barrio: {barrio}\n\n"
            "Usa /aliados_pendientes o el Panel de Plataforma (/admin) para revisarlo."
        )
    )
except Exception as e:
    print("Error enviando notificación al Administrador de Plataforma:", e)

        # --- Confirmación al usuario ---
        update.message.reply_text(
            "Aliado registrado exitosamente!\n\n"
            f"Negocio: {business_name}\n"
            f"Dueño: {owner_name}\n"
            f"Teléfono: {phone}\n"
            f"Dirección: {address}, {barrio}, {city}\n"
            "Tu estado es PENDING."
        )

        # Limpiar datos
        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        print(f"[ERROR] Error al crear aliado o su dirección: {e}")
        update.message.reply_text(
            "Error técnico al guardar tu registro. Intenta más tarde."
        )
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
    
# Notificar al Administrador de Plataforma sobre nuevo aliado pendiente
try:
    context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=(
            "Nuevo registro de ALIADO pendiente en la Plataforma:\n\n"
            "Negocio: {}\n"
            "Propietario: {}\n"
            "Teléfono: {}\n"
            "Ciudad: {}\n"
            "Barrio: {}\n\n"
            "Usa /aliados_pendientes o el Panel de Plataforma (/admin) para revisarlo."
        ).format(
            business_name,  # usa las mismas variables que ya usas al crear el aliado
            owner_name,
            ally_phone,
            city,
            barrio,
        )
    )
except Exception as e:
    print("Error enviando notificación al Administrador de Plataforma:", e)

  
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
    """Lista aliados PENDING solo para el Administrador de Plataforma."""
    message = update.effective_message
    user_id = update.effective_user.id
    print(f"[DEBUG] user_id que envía el comando: {user_id}")
    print(f"[DEBUG] ADMIN_USER_ID (Administrador de Plataforma) configurado: {ADMIN_USER_ID}")

    # Solo el Administrador de Plataforma puede usar este comando
    if user_id != ADMIN_USER_ID:
        message.reply_text("Este comando es solo para el Administrador de Plataforma.")
        return

    # Intentar leer aliados pendientes de la BD
    try:
        allies = get_pending_allies()
    except Exception as e:
        print(f"[ERROR] en get_pending_allies(): {e}")
        message.reply_text("⚠️ Error interno al consultar aliados pendientes.")
        return

    if not allies:
        message.reply_text("No hay aliados pendientes por aprobar.")
        return

    # Enviar un mensaje por cada aliado pendiente, con botones
    for ally in allies:
        ally_id, business_name, owner_name, address, city, barrio, phone, status = ally

        texto = (
            "Aliados pendientes:\n"
            "------------------------\n"
            f"ID interno: {ally_id}\n"
            f"Negocio: {business_name}\n"
            f"Dueño: {owner_name}\n"
            f"Teléfono: {phone}\n"
            f"Dirección: {address}, {barrio}, {city}\n"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"ally_approve_{ally_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"ally_reject_{ally_id}"),
            ]
        ]

        message.reply_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

def aliados_pendientes(update, context):
    """Lista aliados PENDING solo para el Administrador de Plataforma."""
    message = update.effective_message
    user_id = update.effective_user.id
    print(f"[DEBUG] user_id que envía el comando: {user_id}")
    print(f"[DEBUG] ADMIN_USER_ID (Administrador de Plataforma) configurado: {ADMIN_USER_ID}")

    # Solo el Administrador de Plataforma puede usar este comando
    if user_id != ADMIN_USER_ID:
        message.reply_text("Este comando es solo para el Administrador de Plataforma.")
        return

    if not couriers:
        message.reply_text("No hay repartidores pendientes por aprobar.")
        return

    # Enviar un mensaje por cada repartidor pendiente, con botones
    for row in couriers:
        (
            courier_id,
            user_id_db,
            full_name,
            id_number,
            phone,
            city,
            barrio,
            plate,
            bike_type,
            code,
            status,
        ) = row

        texto = (
            "Repartidores pendientes:\n"
            "------------------------\n"
            f"ID interno: {courier_id}\n"
            f"Nombre: {full_name}\n"
            f"Cédula: {id_number}\n"
            f"Teléfono: {phone}\n"
            f"Ciudad: {city}\n"
            f"Barrio: {barrio}\n"
            f"Placa: {plate}\n"
            f"Tipo de moto: {bike_type}\n"
            f"Código interno: {code}\n"
            f"Estado: {status}\n"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    f"Aprobar {courier_id}",
                    callback_data=f"courier_approve_{courier_id}",
                ),
                InlineKeyboardButton(
                    f"Rechazar {courier_id}",
                    callback_data=f"courier_reject_{courier_id}",
                ),
            ]
        ]

        message.reply_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        
def soy_admin(update, context):
    user_id = update.effective_user.id

    # Limpieza del contexto
    context.user_data.clear()

# Si ya existe como Administrador Local, muéstralo (opcional pero recomendado)
existing = get_admin_by_user_id(user_id)
if existing:
    # existing: (id, user_id, full_name, phone, city, barrio, status, created_at)
    update.message.reply_text(
        "Ya tienes un registro como Administrador Local.\n"
        f"Nombre: {existing[2]}\n"
        f"Teléfono: {existing[3]}\n"
        f"Ciudad: {existing[4]}\n"
        f"Barrio: {existing[5]}\n"
        f"Estado: {existing[6]}\n\n"
        "Si deseas actualizar tus datos, escribe SI.\n"
        "Si no, escribe NO."
    )
    context.user_data["admin_update_prompt"] = True
    return LOCAL_ADMIN_NAME  # reutilizamos LOCAL_ADMIN_NAME para capturar SI/NO

update.message.reply_text("Registro de Administrador Local.\nEscribe tu nombre completo:")
return LOCAL_ADMIN_NAME


def admin_name(update, context):
    text = update.message.text.strip()

    # Si veníamos del prompt de actualización
    if context.user_data.get("admin_update_prompt"):
        answer = text.upper()
        context.user_data.pop("admin_update_prompt", None)
        if answer == "SI":
            update.message.reply_text("Perfecto. Escribe tu nombre completo:")
            return LOCAL_ADMIN_NAME
        update.message.reply_text("Entendido. No se modificó tu registro.")
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data["admin_name"] = text
    update.message.reply_text("Escribe tu número de teléfono:")
    return LOCAL_ADMIN_PHONE


def admin_phone(update, context):
    context.user_data["admin_phone"] = update.message.text.strip()
    update.message.reply_text("¿En qué ciudad vas a operar? (Ej: Pereira, Dosquebradas):")
    return LOCAL_ADMIN_CITY


def admin_city(update, context):
    context.user_data["admin_city"] = update.message.text.strip()
    update.message.reply_text("Escribe tu barrio o zona base de operación:")
    return LOCAL_ADMIN_BARRIO


def admin_barrio(update, context):
    context.user_data["admin_barrio"] = update.message.text.strip()

    msg = (
        "Condiciones para Administrador Local:\n"
        "1) Para ser aprobado debes registrar al menos 10 repartidores.\n"
        "2) Cada repartidor debe tener recarga mínima de 5000.\n"
        "3) Si tu administrador local no tiene saldo activo con la plataforma, su operación queda suspendida.\n\n"
        "Escribe ACEPTAR para finalizar el registro o /cancel para salir."
    )
    update.message.reply_text(msg)
    return LOCAL_ADMIN_ACCEPT


def admin_accept(update, context):
    answer = update.message.text.strip().upper()
    user_id = update.effective_user.id

    if answer != "ACEPTAR":
        update.message.reply_text("Registro cancelado. Si deseas intentarlo de nuevo usa /soy_admin.")
        context.user_data.clear()
        return ConversationHandler.END

    full_name = context.user_data.get("admin_name", "")
    phone = context.user_data.get("admin_phone", "")
    city = context.user_data.get("admin_city", "")
    barrio = context.user_data.get("admin_barrio", "")

    create_admin(user_id, full_name, phone, city, barrio)

    update.message.reply_text(
        "Registro de Administrador Local recibido.\n"
        "Estado: PENDING\n\n"
        "Recuerda: para ser aprobado debes registrar 10 repartidores con recarga mínima de 5000 cada uno."
    )

    context.user_data.clear()
    return ConversationHandler.END
        
def admin_menu(update, context):
    """Panel de Administración de Plataforma."""
    user = update.effective_user
    user_id = user.id

    # Solo el Administrador de Plataforma puede usar este comando
    if user_id != ADMIN_USER_ID:
        update.message.reply_text("Este comando es solo para el Administrador de Plataforma.")
        return

    texto = (
        "Panel de Administración de Plataforma.\n"
        "¿Qué deseas revisar?"
    )

    keyboard = [
        [InlineKeyboardButton("👤 Aliados pendientes", callback_data="admin_aliados_pendientes")],
        [InlineKeyboardButton("🚚 Repartidores pendientes", callback_data="admin_repartidores_pendientes")],
        [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos")],
        [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
        [InlineKeyboardButton("💰 Tarifas", callback_data="admin_tarifas")],
        [InlineKeyboardButton("📊 Finanzas", callback_data="admin_finanzas")],
    ]

    update.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    
def admin_menu_callback(update, context):
    """Maneja los botones del Panel de Administración de Plataforma."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    # Solo el Administrador de Plataforma puede usar estos botones
    if user_id != ADMIN_USER_ID:
        query.answer("Solo el Administrador de Plataforma puede usar este menú.", show_alert=True)
        return

# Botón: Aliados pendientes (Plataforma)
if data == "admin_aliados_pendientes":
    query.answer()
    # Reutilizamos la función existente
    aliados_pendientes(update, context)
    return

# Botón: Repartidores pendientes (Plataforma)
if data == "admin_repartidores_pendientes":
    query.answer()
    # Reutilizamos la función existente
    repartidores_pendientes(update, context)
    return

# Botones aún no implementados (placeholders)
if data == "admin_pedidos":
    query.answer("La sección de pedidos de la Plataforma aún no está implementada.")
    return

if data == "admin_config":
    keyboard = [
        [InlineKeyboardButton("Ver totales de registros", callback_data="config_totales")],
        [InlineKeyboardButton("Gestionar aliados", callback_data="config_gestion_aliados")],
        [InlineKeyboardButton("Gestionar repartidores", callback_data="config_gestion_repartidores")],
    ]

    query.edit_message_text(
        "Configuraciones de administración. ¿Qué deseas hacer?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return

    if data == "admin_tarifas":
        query.answer("La sección de tarifas aún no está implementada.")
        return

    if data == "admin_finanzas":
        query.answer("La sección de finanzas aún no está implementada.")
        return

    # Por si llega algo raro
    query.answer("Opción no reconocida.", show_alert=True)

def pendientes(update, context):
    """Menú rápido para ver registros pendientes."""
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        update.message.reply_text("Solo el administrador de plataforna puede usar este comando.")
        return

    keyboard = [
        [
            InlineKeyboardButton("🟦 Aliados pendientes", callback_data="menu_aliados_pendientes"),
            InlineKeyboardButton("🟧 Repartidores pendientes", callback_data="menu_repartidores_pendientes")
        ]
    ]

    update.message.reply_text(
        "Seleccione qué desea revisar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
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

    # Solo el administrador de plataforma puede usar estos botones
    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador de plataforma puede usar estos botones.", show_alert=True)
        return

    if not data.startswith("ally_"):
        query.answer("Comando no reconocido.", show_alert=True)
        return

    partes = data.split("_")    # ["ally", "approve", "3"]
    if len(partes) != 3:
        query.answer("Datos de botón no válidos.", show_alert=True)
        return

    _, accion, ally_id_str = partes

    # Convertir ID del aliado a entero
    try:
        ally_id = int(ally_id_str)
    except ValueError:
        query.answer("ID de aliado no válido.", show_alert=True)
        return

    # -------------------------------------------------------------
    # APROBAR ALIADO
    # -------------------------------------------------------------
    if accion == "approve":
        nuevo_estado = "APPROVED"

        # Actualizar en la BD
        try:
            update_ally_status(ally_id, nuevo_estado)
        except Exception as e:
            print(f"[ERROR] ally_approval_callback (approve): {e}")
            query.answer(f"Error al actualizar el estado del aliado:\n{e}", show_alert=True)
            return

        # Obtener datos del aliado
        ally = get_ally_by_id(ally_id)
        if not ally:
            query.edit_message_text("No se encontró el aliado después de actualizar.")
            return

        # id, user_id, business_name, owner_name, phone, address, city, barrio, status
        ally_user_id = ally[1]
        business_name = ally[2]

        # Notificar al aliado
        try:
            context.bot.send_message(
                chat_id=ally_user_id,
                text=(
                    "Tu registro como aliado '{}' ha sido APROBADO.\n"
                    "Ya puedes usar el bot para crear pedidos."
                ).format(business_name)
            )
        except Exception as e:
            print("Error notificando aliado aprobado:", e)

        # Confirmar al administrador de plataforma
        query.edit_message_text("El aliado '{}' ha sido APROBADO.".format(business_name))
        return

    # -------------------------------------------------------------
    # RECHAZAR ALIADO
    # -------------------------------------------------------------
    elif accion == "reject":
        nuevo_estado = "REJECTED"

        # Actualizar en la BD
        try:
            update_ally_status(ally_id, nuevo_estado)
        except Exception as e:
            print(f"[ERROR] ally_approval_callback (reject): {e}")
            query.answer(f"Error al actualizar el estado del aliado:\n{e}", show_alert=True)
            return

        ally = get_ally_by_id(ally_id)
        if not ally:
            query.edit_message_text("No se encontró el aliado después de actualizar.")
            return

        ally_user_id = ally[1]
        business_name = ally[2]

        # Notificar al aliado
        try:
            context.bot.send_message(
                chat_id=ally_user_id,
                text=(
                    "Tu registro como aliado '{}' ha sido RECHAZADO.\n"
                    "Si crees que es un error, comunícate con el administrador."
                ).format(business_name)
            )
        except Exception as e:
            print("Error notificando aliado rechazado:", e)

        # Confirmar al admin
        query.edit_message_text("El aliado '{}' ha sido RECHAZADO.".format(business_name))
        return

    # -------------------------------------------------------------
    # ACCIÓN NO RECONOCIDA
    # -------------------------------------------------------------
    else:
        query.answer("Acción no reconocida.", show_alert=True)
        return
        
def pendientes_callback(update, context):
    query = update.callback_query
    data = query.data

    if data == "menu_aliados_pendientes":
        query.answer()
        aliados_pendientes(update, context)
        return

    if data == "menu_repartidores_pendientes":
        query.answer()
        repartidores_pendientes(update, context)
        return

    query.answer("Opción no reconocida.", show_alert=True)
    
def courier_approval_callback(update, context):
    """Maneja los botones de aprobar / rechazar repartidores."""
    query = update.callback_query
    data = query.data  # Ej: "courier_approve_3" o "courier_reject_5"
    user_id = query.from_user.id

    # Solo el administrador de plataforna puede usar estos botones
    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador de plataforma puede usar estos botones.", show_alert=True)
        return

    if not data.startswith("courier_"):
        query.answer("Comando no reconocido.", show_alert=True)
        return

    partes = data.split("_")  # ["courier", "approve", "3"]
    if len(partes) != 3:
        query.answer("Datos de botón no válidos.", show_alert=True)
        return

    _, accion, courier_id_str = partes

    try:
        courier_id = int(courier_id_str)
    except ValueError:
        query.answer("ID de repartidor no válido.", show_alert=True)
        return

    # -------------------------------------------------------------
    # APROBAR REPARTIDOR
    # -------------------------------------------------------------
    if accion == "approve":
        nuevo_estado = "APPROVED"

        # Actualizar en la BD
        try:
            update_courier_status(courier_id, nuevo_estado)
        except Exception as e:
            print(f"[ERROR] courier_approval_callback (approve): {e}")
            query.answer(f"Error al actualizar el estado del repartidor:\n{e}", show_alert=True)
            return

        # Obtener datos del repartidor
        courier = get_courier_by_id(courier_id)
        if not courier:
            query.edit_message_text("No se encontró el repartidor después de actualizar.")
            return

        # id, user_id, full_name, id_number, phone, city, barrio, plate, bike_type, code, status
        courier_user_id = courier[1]
        full_name = courier[2]

        # Notificar al repartidor
        try:
            context.bot.send_message(
                chat_id=courier_user_id,
                text="Tu registro como repartidor ha sido APROBADO. Bienvenido, {}.".format(full_name)
            )
        except Exception as e:
            print("Error notificando repartidor aprobado:", e)

        # Confirmar al admin
        query.edit_message_text("El repartidor '{}' ha sido APROBADO.".format(full_name))
        return

    # -------------------------------------------------------------
    # RECHAZAR REPARTIDOR
    # -------------------------------------------------------------
    elif accion == "reject":
        nuevo_estado = "REJECTED"

        # Actualizar en la BD
        try:
            update_courier_status(courier_id, nuevo_estado)
        except Exception as e:
            print(f"[ERROR] courier_approval_callback (reject): {e}")
            query.answer(f"Error al actualizar el estado del repartidor:\n{e}", show_alert=True)
            return

        courier = get_courier_by_id(courier_id)
        if not courier:
            query.edit_message_text("No se encontró el repartidor después de actualizar.")
            return

        courier_user_id = courier[1]
        full_name = courier[2]

        # Notificar al repartidor
        try:
            context.bot.send_message(
                chat_id=courier_user_id,
                text=(
                    "Tu registro como repartidor ha sido RECHAZADO, {}.\n"
                    "Si crees que es un error, comunícate con el administrador."
                ).format(full_name)
            )
        except Exception as e:
            print("Error notificando repartidor rechazado:", e)

        # Confirmar al admin
        query.edit_message_text("El repartidor '{}' ha sido RECHAZADO.".format(full_name))
        return

    # -------------------------------------------------------------
    # ACCIÓN NO RECONOCIDA
    # -------------------------------------------------------------
    else:
        query.answer("Acción no reconocida.", show_alert=True)
        return

def admin_configuraciones(update, context):
    user_id = update.effective_user.id

    if not es_admin(user_id):
        return

    keyboard = [
        [InlineKeyboardButton("Ver totales de registros", callback_data="config_totales")],
        [InlineKeyboardButton("Gestionar aliados", callback_data="config_gestion_aliados")],
        [InlineKeyboardButton("Gestionar repartidores", callback_data="config_gestion_repartidores")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Configuraciones de administración. ¿Qué deseas hacer?",
        reply_markup=reply_markup
    )
    
def admin_config_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    # Verificación de administrador
    if not es_admin(user_id):
        query.answer("No tienes permisos para esto.")
        return

    # 1) Ver totales de registros
    if data == "config_totales":
        total_allies, total_couriers = get_totales_registros()
        texto = (
            "Resumen de registros:\n\n"
            "Aliados registrados: {}\n"
            "Repartidores registrados: {}"
        ).format(total_allies, total_couriers)

        query.edit_message_text(texto)
        return

    # 2) Gestionar aliados (listar)
    if data == "config_gestion_aliados":
        allies = get_all_allies()

        if not allies:
            query.edit_message_text("No hay aliados registrados en este momento.")
            return

        keyboard = []
        for ally in allies:
            # Según get_all_allies:
            # id, user_id, business_name, owner_name, phone, address, city, barrio, status
            ally_id = ally[0]
            business_name = ally[2]
            status = ally[8]

            button_text = "ID {} - {} ({})".format(ally_id, business_name, status)
            callback_data = "config_ver_ally_{}".format(ally_id)
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        keyboard.append([InlineKeyboardButton("Cerrar", callback_data="config_cerrar")])

        query.edit_message_text(
            "Aliados registrados. Toca uno para ver detalle.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 2.1) Ver detalle de aliado
    if data.startswith("config_ver_ally_"):
        ally_id = int(data.split("_")[-1])
        ally = get_ally_by_id(ally_id)

        if not ally:
            query.edit_message_text("No se encontró el aliado.")
            return

        # Mismos índices que arriba:
        # id, user_id, business_name, owner_name, phone, address, city, barrio, status
        texto = (
            "Detalle del aliado:\n\n"
            "ID: {id}\n"
            "Negocio: {business_name}\n"
            "Propietario: {owner_name}\n"
            "Teléfono: {phone}\n"
            "Dirección: {address}\n"
            "Ciudad: {city}\n"
            "Barrio: {barrio}\n"
            "Estado: {status}"
        ).format(
            id=ally[0],
            business_name=ally[2],
            owner_name=ally[3],
            phone=ally[4],
            address=ally[5],
            city=ally[6],
            barrio=ally[7],
            status=ally[8],
        )

        keyboard = [
            [InlineKeyboardButton("❌ Eliminar aliado", callback_data="config_confirm_delete_ally_{}".format(ally_id))],
            [InlineKeyboardButton("⬅ Volver a la lista", callback_data="config_gestion_aliados")],
        ]

        query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 2.2) Confirmar borrado de aliado
    if data.startswith("config_confirm_delete_ally_"):
        ally_id = int(data.split("_")[-1])
        delete_ally(ally_id)
        query.edit_message_text("El aliado {} ha sido eliminado.".format(ally_id))
        return

    # 3) Gestionar repartidores (listar)
    if data == "config_gestion_repartidores":
        couriers = get_all_couriers()

        if not couriers:
            query.edit_message_text("No hay repartidores registrados en este momento.")
            return

        keyboard = []
        for courier in couriers:
            # Según get_all_couriers:
            # id, user_id, full_name, id_number, phone, city, barrio, plate, bike_type, code, status
            courier_id = courier[0]
            full_name = courier[2]
            status = courier[10]

            button_text = "ID {} - {} ({})".format(courier_id, full_name, status)
            callback_data = "config_ver_courier_{}".format(courier_id)
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        keyboard.append([InlineKeyboardButton("Cerrar", callback_data="config_cerrar")])

        query.edit_message_text(
            "Repartidores registrados. Toca uno para ver detalle.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 3.1) Ver detalle de repartidor
    if data.startswith("config_ver_courier_"):
        courier_id = int(data.split("_")[-1])
        courier = get_courier_by_id(courier_id)

        if not courier:
            query.edit_message_text("No se encontró el repartidor.")
            return

        texto = (
            "Detalle del repartidor:\n\n"
            "ID: {id}\n"
            "Nombre: {full_name}\n"
            "Documento: {id_number}\n"
            "Teléfono: {phone}\n"
            "Ciudad: {city}\n"
            "Barrio: {barrio}\n"
            "Placa: {plate}\n"
            "Tipo de moto: {bike_type}\n"
            "Estado: {status}"
        ).format(
            id=courier[0],
            full_name=courier[2],
            id_number=courier[3],
            phone=courier[4],
            city=courier[5],
            barrio=courier[6],
            plate=courier[7],
            bike_type=courier[8],
            status=courier[10],
        )

        keyboard = [
            [InlineKeyboardButton("❌ Eliminar repartidor", callback_data="config_confirm_delete_courier_{}".format(courier_id))],
            [InlineKeyboardButton("⬅ Volver a la lista", callback_data="config_gestion_repartidores")],
        ]

        query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # 3.2) Confirmar borrado de repartidor
    if data.startswith("config_confirm_delete_courier_"):
        courier_id = int(data.split("_")[-1])
        delete_courier(courier_id)
        query.edit_message_text("El repartidor {} ha sido eliminado.".format(courier_id))
        return

    # 4) Cerrar menú de configuraciones
    if data == "config_cerrar":
        query.edit_message_text("Menú de configuraciones cerrado.")
        return

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

# Callbacks del menú de configuraciones de la Plataforma
dp.add_handler(CallbackQueryHandler(admin_config_callback, pattern="^config_"))

# Conversaciones completas
dp.add_handler(ally_conv)          # /soy_aliado
dp.add_handler(courier_conv)       # /soy_repartidor
dp.add_handler(nuevo_pedido_conv)  # /nuevo_pedido
dp.add_handler(CommandHandler("repartidores_pendientes", repartidores_pendientes))
dp.add_handler(CommandHandler("pendientes", pendientes))

# Callbacks de aprobación (Plataforma)
dp.add_handler(CallbackQueryHandler(ally_approval_callback, pattern="^ally_"))
dp.add_handler(CallbackQueryHandler(ally_approval_callback, pattern="^ally_"))
dp.add_handler(CallbackQueryHandler(courier_approval_callback, pattern="^courier_"))
dp.add_handler(CallbackQueryHandler(pendientes_callback, pattern="menu_"))

# Callbacks del Panel de Administración de Plataforma
dp.add_handler(CallbackQueryHandler(ally_approval_callback, pattern="ally_"))
dp.add_handler(CallbackQueryHandler(courier_approval_callback, pattern="courier_"))
dp.add_handler(CallbackQueryHandler(admin_menu_callback, pattern="admin_"))  # Plataforma

# Comandos administrativos de Plataforma
dp.add_handler(CommandHandler("id", cmd_id))
dp.add_handler(CommandHandler("aliados_pendientes", aliados_pendientes))
dp.add_handler(CommandHandler("repartidores_pendientes", repartidores_pendientes))
dp.add_handler(CommandHandler("cancel", cancel))
dp.add_handler(CommandHandler("admin", admin_menu))  # Panel de Plataforma

# Registro de Administradores Locales
admin_conv = ConversationHandler(
    entry_points=[CommandHandler("soy_admin", soy_admin)],
    states={
        LOCAL_ADMIN_NAME: [MessageHandler(Filters.text & ~Filters.command, admin_name)],
        LOCAL_ADMIN_PHONE: [MessageHandler(Filters.text & ~Filters.command, admin_phone)],
        LOCAL_ADMIN_CITY: [MessageHandler(Filters.text & ~Filters.command, admin_city)],
        LOCAL_ADMIN_BARRIO: [MessageHandler(Filters.text & ~Filters.command, admin_barrio)],
        LOCAL_ADMIN_ACCEPT: [MessageHandler(Filters.text & ~Filters.command, admin_accept)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conversacion)],
)

dp.add_handler(admin_conv)


    # Iniciar el bot
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()

# trigger deploy

