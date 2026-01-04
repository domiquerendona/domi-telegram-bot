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

from db import get_local_admins_count

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

    # Admins
    create_admin,
    get_admin_by_user_id,
    get_all_admins,
    get_pending_admins,
    get_admin_by_id,
    update_admin_status_by_id,
    count_admin_couriers,
    count_admin_couriers_with_min_balance,

    # Direcciones aliados
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
    get_pending_couriers,
    update_courier_status,
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

    # Herramientas administrativas
    get_totales_registros,

    # Calificaciones
    add_courier_rating,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))  # Administrador de Plataforma

COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))


def es_admin(user_id: int) -> bool:
    """Devuelve True si el user_id es el administrador de plataforma."""
    return user_id == ADMIN_USER_ID


# =========================
# Estados del registro de aliados
# =========================
ALLY_NAME, ALLY_OWNER, ALLY_ADDRESS, ALLY_CITY, ALLY_PHONE, ALLY_BARRIO = range(6)


# =========================
# Estados para registro de repartidores
# =========================
(
    COURIER_FULLNAME,
    COURIER_IDNUMBER,
    COURIER_PHONE,
    COURIER_CITY,
    COURIER_BARRIO,
    COURIER_PLATE,
    COURIER_BIKETYPE,
    COURIER_CONFIRM,
    COURIER_TEAMCODE,
) = range(5, 14)


# =========================
# Estados para registro de administrador local
# =========================
(
    LOCAL_ADMIN_NAME,
    LOCAL_ADMIN_DOCUMENT,
    LOCAL_ADMIN_TEAMNAME,
    LOCAL_ADMIN_PHONE,
    LOCAL_ADMIN_CITY,
    LOCAL_ADMIN_BARRIO,
    LOCAL_ADMIN_ACCEPT,
) = range(300, 307)


# =========================
# Estados para crear un pedido
# =========================
PEDIDO_NOMBRE, PEDIDO_TELEFONO, PEDIDO_DIRECCION = range(14, 17)

def get_user_db_id_from_update(update):
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    return user_row["id"]                                                         

def start(update, context):
    """Comando /start y /menu: bienvenida con estado del usuario."""
    user_tg = update.effective_user

    # Crear/asegurar user en users y tomar users.id (interno)
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    # Perfiles
    ally = get_ally_by_user_id(user_db_id)
    courier = get_courier_by_user_id(user_db_id)

    # Admin local por users.id (interno)
    admin_local = None
    try:
        admin_local = get_admin_by_user_id(user_db_id)
    except Exception:
        admin_local = None

    es_admin_plataforma = (user_tg.id == ADMIN_USER_ID)

    estado_lineas = []
    siguientes_pasos = []

    # Admin Plataforma
    if es_admin_plataforma:
        estado_lineas.append("• Administrador de Plataforma: ACTIVO.")
        siguientes_pasos.append("• Usa /admin para abrir el Panel de Plataforma.")

    # Admin Local
    if admin_local:
        if isinstance(admin_local, dict):
            admin_status = admin_local.get("status", "PENDING")
            team_name = admin_local.get("team_name") or "-"
        else:
            # id, user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number, team_code
            admin_status = admin_local[6]
            team_name = admin_local[8] or "-"

        estado_lineas.append(f"• Administrador Local: equipo {team_name} (estado: {admin_status}).")

        if admin_status == "PENDING":
            siguientes_pasos.append("• Tu registro de administrador está pendiente de aprobación.")
        elif admin_status == "APPROVED":
            siguientes_pasos.append(
                "• Tu administrador fue APROBADO, pero no podrás operar hasta cumplir requisitos (10 repartidores con saldo mínimo)."
            )
            siguientes_pasos.append("• Usa /mi_admin para ver requisitos y tu estado operativo.")
        elif admin_status == "INACTIVE":
            siguientes_pasos.append("• Tu cuenta de administrador está INACTIVA. Contacta al Administrador de Plataforma.")
        elif admin_status == "REJECTED":
            siguientes_pasos.append("• Tu registro de administrador fue RECHAZADO. Contacta al Administrador de Plataforma.")

    # Aliado
    if ally:
        estado_lineas.append(f"• Aliado: {ally['business_name']} (estado: {ally['status']}).")
        if ally["status"] == "APPROVED":
            siguientes_pasos.append("• Puedes crear pedidos con /nuevo_pedido.")
        else:
            siguientes_pasos.append("• Tu negocio aún no está aprobado. Cuando esté APPROVED podrás usar /nuevo_pedido.")

    # Repartidor
    if courier:
        codigo = courier["code"] if courier["code"] else "sin código"
        estado_lineas.append(f"• Repartidor código interno: {codigo} (estado: {courier['status']}).")
        if courier["status"] == "APPROVED":
            siguientes_pasos.append("• Pronto podrás activarte y recibir ofertas (ONLINE) desde tu panel de repartidor.")
        else:
            siguientes_pasos.append("• Tu registro de repartidor aún está pendiente de aprobación.")

    # Si no tiene ningún perfil
    if not estado_lineas:
        estado_text = "Aún no estás registrado como aliado, repartidor ni administrador."
        siguientes_pasos = [
            "• Si tienes un negocio: usa /soy_aliado",
            "• Si eres repartidor: usa /soy_repartidor",
            "• Si vas a liderar un equipo: usa /soy_administrador",
        ]
    else:
        estado_text = "\n".join(estado_lineas)

    siguientes_text = "\n".join(siguientes_pasos) if siguientes_pasos else "• Usa los comandos principales para continuar."

    comandos = [
        "• /soy_aliado  - Registrar tu negocio aliado",
        "• /soy_repartidor  - Registrarte como repartidor",
        "• /soy_administrador  - Registrarte como administrador",
    ]

    if ally and ally.get("status") == "APPROVED":
        comandos.append("• /nuevo_pedido  - Crear nuevo pedido (aliados aprobados)")

    if admin_local:
        comandos.append("• /mi_admin  - Ver tu panel de administrador local")
    if es_admin_plataforma:
        comandos.append("• /admin  - Panel de administración de plataforma")

    comandos.append("• /menu  - Volver a ver este menú")

    mensaje = (
        "🐢 Bienvenido a Domiquerendona 🐢\n\n"
        "Sistema para conectar negocios aliados con repartidores de confianza.\n\n"
        "Tu estado actual:\n"
        f"{estado_text}\n\n"
        "Siguiente paso recomendado:\n"
        f"{siguientes_text}\n\n"
        "Comandos principales:\n"
        + "\n".join(comandos)
        + "\n"
    )

    update.message.reply_text(mensaje)


def menu(update, context):
    """Alias de /start para mostrar el menú principal."""
    return start(update, context)


def cancel(update, context):
    """Permite cancelar cualquier proceso y limpiar datos temporales."""
    context.user_data.clear()
    update.message.reply_text("Operación cancelada.\n\nPuedes usar /menu o /start para volver al inicio.")


def cmd_id(update, context):
    """Muestra el user_id de Telegram del usuario."""
    user = update.effective_user
    update.message.reply_text(f"Tu user_id es: {user.id}")
def pedido_nombre_cliente(update, context):
    context.user_data["customer_name"] = update.message.text.strip()
    update.message.reply_text("Ahora escribe el número de teléfono del cliente.")
    return PEDIDO_TELEFONO


def pedido_telefono_cliente(update, context):
    context.user_data["customer_phone"] = update.message.text.strip()
    update.message.reply_text("Ahora escribe la dirección de entrega del cliente.")
    return PEDIDO_DIRECCION


def pedido_direccion_cliente(update, context):
    context.user_data["customer_address"] = update.message.text.strip()

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
    context.user_data.clear()
    return ConversationHandler.END


# ----- REGISTRO DE ALIADO -----

def soy_aliado(update, context):
    user = update.effective_user
    ensure_user(user.id, user.username)
    update.message.reply_text(
        "👨‍🍳 Registro de aliado\n\n"
        "Escribe el nombre del negocio:"
    )
    return ALLY_NAME


def ally_name(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text("El nombre del negocio no puede estar vacío. Escríbelo de nuevo:")
        return ALLY_NAME

    context.user_data.clear()
    context.user_data["business_name"] = texto
    update.message.reply_text("Escribe el nombre del dueño o administrador:")
    return ALLY_OWNER


def ally_owner(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text("El nombre del dueño no puede estar vacío. Escríbelo de nuevo:")
        return ALLY_OWNER

    context.user_data["owner_name"] = texto
    update.message.reply_text("Escribe la dirección del negocio:")
    return ALLY_ADDRESS


def ally_address(update, context):
    texto = update.message.text.strip()
    context.user_data["address"] = texto
    update.message.reply_text("Escribe la ciudad del negocio:")
    return ALLY_CITY


def ally_city(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text("La ciudad del negocio no puede estar vacía. Escríbela de nuevo:")
        return ALLY_CITY

    context.user_data["city"] = texto
    update.message.reply_text("Escribe el teléfono de contacto del negocio:")
    return ALLY_PHONE


def ally_phone(update, context):
    phone = (update.message.text or "").strip()

    # Validación mínima: que tenga al menos 7 dígitos
    digits = "".join([c for c in phone if c.isdigit()])
    if len(digits) < 7:
        update.message.reply_text("Ese teléfono no parece válido. Escríbelo de nuevo, por favor.")
        return ALLY_PHONE

    # Guardamos en el contexto con el mismo término que acordamos: ally_phone
    context.user_data["ally_phone"] = phone

    # Siguiente paso
    update.message.reply_text("Escribe el barrio del negocio:")
    return ALLY_BARRIO


def ally_barrio(update, context):
    """
    ALLY_BARRIO se usa 2 veces:
    1) Primer mensaje: teléfono
    2) Segundo mensaje: barrio -> crea aliado
    """
    user_tg_id = user.id
    text = update.message.text.strip()

    # 1) teléfono
    if "ally_phone" not in context.user_data:
        if not text:
            update.message.reply_text("El teléfono no puede estar vacío. Escríbelo de nuevo:")
            return ALLY_BARRIO
        context.user_data["ally_phone"] = text
        update.message.reply_text("Escribe el barrio o sector del negocio:")
        return ALLY_BARRIO

    # 2) barrio
    barrio = text
    if not barrio:
        update.message.reply_text("El barrio no puede estar vacío. Escríbelo de nuevo:")
        return ALLY_BARRIO

    business_name = context.user_data.get("business_name", "").strip()
    owner_name = context.user_data.get("owner_name", "").strip()
    address = context.user_data.get("address", "").strip()
    city = context.user_data.get("city", "").strip()
    phone = context.user_data.get("ally_phone", "").strip()

    try:
        ally_id = create_ally(
            user_id=user_tg_id,
            business_name=business_name,
            owner_name=owner_name,
            address=address,
            city=city,
            barrio=barrio,
            phone=phone,
        )

        create_ally_location(
            ally_id=ally_id,
            label="Principal",
            address=address,
            city=city,
            barrio=barrio,
            phone=None,
            is_default=True,
        )

        # Notificar al Admin de Plataforma
        try:
            context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=(
                    "Nuevo registro de ALIADO pendiente:\n\n"
                    f"Negocio: {business_name}\n"
                    f"Dueño: {owner_name}\n"
                    f"Teléfono: {phone}\n"
                    f"Ciudad: {city}\n"
                    f"Barrio: {barrio}\n\n"
                    "Usa /aliados_pendientes o /admin para revisarlo."
                )
            )
        except Exception as e:
            print("[WARN] No se pudo notificar al admin plataforma:", e)

        update.message.reply_text(
            "Aliado registrado exitosamente.\n\n"
            f"Negocio: {business_name}\n"
            f"Dueño: {owner_name}\n"
            f"Teléfono: {phone}\n"
            f"Dirección: {address}, {barrio}, {city}\n"
            "Tu estado es PENDING."
        )

    except Exception as e:
        print(f"[ERROR] Error al crear aliado: {e}")
        update.message.reply_text("Error técnico al guardar tu registro. Intenta más tarde.")

    context.user_data.clear()
    return ConversationHandler.END


# ----- REGISTRO DE REPARTIDOR -----

def soy_repartidor(update, context):
    user = update.effective_user
    ensure_user(user.id, user.username)
    context.user_data.clear()
    update.message.reply_text(
        "🛵 Registro de repartidor\n\n"
        "Escribe tu nombre completo:"
    )
    return COURIER_FULLNAME


def courier_fullname(update, context):
    context.user_data["full_name"] = update.message.text.strip()
    update.message.reply_text("Escribe tu número de identificación:")
    return COURIER_IDNUMBER


def courier_idnumber(update, context):
    context.user_data["id_number"] = update.message.text.strip()
    update.message.reply_text("Escribe tu número de celular:")
    return COURIER_PHONE


def courier_phone(update, context):
    context.user_data["phone"] = update.message.text.strip()
    update.message.reply_text("Escribe la ciudad donde trabajas:")
    return COURIER_CITY


def courier_city(update, context):
    context.user_data["city"] = update.message.text.strip()
    update.message.reply_text("Escribe el barrio o sector principal donde trabajas:")
    return COURIER_BARRIO


def courier_barrio(update, context):
    context.user_data["barrio"] = update.message.text.strip()
    update.message.reply_text("Escribe la placa de tu moto (o escribe 'ninguna' si no tienes):")
    return COURIER_PLATE


def courier_plate(update, context):
    context.user_data["plate"] = update.message.text.strip()
    update.message.reply_text("Escribe el tipo de moto (Ejemplo: Bóxer 100, FZ, scooter, bicicleta, etc.):")
    return COURIER_BIKETYPE


def courier_biketype(update, context):
    context.user_data["bike_type"] = update.message.text.strip()

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
        "Si quieres corregir, usa /cancel y vuelve a /soy_repartidor"
    )

    update.message.reply_text(resumen)
    return COURIER_CONFIRM


def courier_confirm(update, context):
    confirm_text = update.message.text.strip().upper()
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)

    if confirm_text not in ("SI", "SÍ", "SI.", "SÍ."):
        update.message.reply_text(
            "Registro cancelado.\n\n"
            "Si deseas intentarlo de nuevo, usa /soy_repartidor."
        )
        context.user_data.clear()
        return ConversationHandler.END

    full_name = context.user_data.get("full_name", "")
    id_number = context.user_data.get("id_number", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    plate = context.user_data.get("plate", "")
    bike_type = context.user_data.get("bike_type", "")

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

    courier = get_courier_by_user_id(db_user["id"])
    if not courier:
        update.message.reply_text(
            "Se registró tu usuario, pero ocurrió un error obteniendo tu perfil de repartidor.\n"
            "Intenta de nuevo."
        )
        context.user_data.clear()
        return ConversationHandler.END

    courier_id = courier["id"] if isinstance(courier, dict) else courier[0]
    context.user_data["new_courier_id"] = courier_id

    update.message.reply_text(
        "Repartidor registrado exitosamente.\n\n"
        f"Nombre: {full_name}\n"
        f"Cédula: {id_number}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Placa: {plate}\n"
        f"Tipo de moto: {bike_type}\n"
        f"Código interno: {code}\n\n"
        "Tu estado es: PENDING.\n\n"
        "Ahora, si deseas unirte a un Administrador Local, escribe el CÓDIGO DE EQUIPO (ej: TEAM1).\n"
        "Si no tienes código, escribe: NO"
    )
    return COURIER_TEAMCODE


def courier_teamcode(update, context):
    text = update.message.text.strip().upper()

    courier_id = context.user_data.get("new_courier_id")
    if not courier_id:
        update.message.reply_text("Error: no se encontró tu registro reciente. Intenta /soy_repartidor de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    if text in ("NO", "N", "NO.", "N."):
        update.message.reply_text(
            "Perfecto. Quedas registrado.\n\n"
            "Cuando tengas un código de equipo, podrás solicitar unirte más adelante."
        )
        context.user_data.clear()
        return ConversationHandler.END

    team_code = text

    admin = get_admin_by_team_code(team_code)
    if not admin:
        update.message.reply_text(
            "No encontré un Administrador Local con ese código.\n\n"
            "Verifica el código e inténtalo de nuevo.\n"
            "O escribe NO para finalizar."
        )
        return COURIER_TEAMCODE

    admin_id = admin[0]

    # IMPORTANTE: aquí admin[1] debe ser el TELEGRAM_ID real del admin.
    # Si tu get_admin_by_team_code devuelve user_id interno, esto fallará.
    admin_telegram_id = admin[1]

    admin_name = admin[2]
    admin_status = admin[3]
    admin_team = admin[4]
    admin_team_code = admin[5]

    try:
        create_admin_courier_link(admin_id, courier_id)
    except Exception as e:
        print("[ERROR] create_admin_courier_link:", e)
        update.message.reply_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END

    try:
        context.bot.send_message(
            chat_id=admin_telegram_id,
            text=(
                "📥 Nueva solicitud de repartidor para tu equipo.\n\n"
                f"Repartidor ID: {courier_id}\n"
                f"Equipo: {admin_team}\n"
                f"Código: {admin_team_code}\n\n"
                "Entra a /mi_admin para aprobar o rechazar."
            )
        )
    except Exception as e:
        print("[WARN] No se pudo notificar al admin local:", e)

    update.message.reply_text(
        "Listo. Tu solicitud para unirte al equipo fue enviada.\n\n"
        "Quedas PENDIENTE de aprobación por el Administrador Local."
    )

    context.user_data.clear()
    return ConversationHandler.END

def nuevo_pedido(update, context):
    user = update.effective_user

    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)

    if not db_user:
        update.message.reply_text("Aún no estás registrado en el sistema. Usa /start primero.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text(
            "Aún no estás registrado como aliado.\n"
            "Si tienes un negocio, regístrate con /soy_aliado."
        )
        return ConversationHandler.END

    if ally["status"] != "APPROVED":
        update.message.reply_text(
            "Tu registro como aliado todavía no ha sido aprobado por el administrador.\n"
            "Cuando tu estado sea APPROVED podrás crear pedidos con /nuevo_pedido."
        )
        return ConversationHandler.END

    # Si tienes ensure_terms implementado y quieres exigirlo, déjalo.
    # Si NO lo tienes, comenta estas 2 líneas.
    if not ensure_terms(update, context, user.id, role="ALLY"):
        return ConversationHandler.END

    context.user_data.clear()
    update.message.reply_text(
        "Crear nuevo pedido.\n\n"
        "Perfecto, empecemos.\n"
        "Primero escribe el nombre del cliente."
    )
    return PEDIDO_NOMBRE


def pedido_nombre_cliente(update, context):
    context.user_data["customer_name"] = update.message.text.strip()
    update.message.reply_text("Ahora escribe el número de teléfono del cliente.")
    return PEDIDO_TELEFONO


def pedido_telefono_cliente(update, context):
    context.user_data["customer_phone"] = update.message.text.strip()
    update.message.reply_text("Ahora escribe la dirección de entrega del cliente.")
    return PEDIDO_DIRECCION


def pedido_direccion_cliente(update, context):
    context.user_data["customer_address"] = update.message.text.strip()

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
    context.user_data.clear()
    return ConversationHandler.END

    
def aliados_pendientes(update, context):
    """Lista aliados PENDING solo para el Administrador de Plataforma."""
    message = update.effective_message
    user_db_id = get_user_db_id_from_update(update)
    if user_id != ADMIN_USER_ID:
        message.reply_text("Este comando es solo para el Administrador de Plataforma.")
        return

    try:
        allies = get_pending_allies()
    except Exception as e:
        print(f"[ERROR] get_pending_allies(): {e}")
        message.reply_text("⚠️ Error interno al consultar aliados pendientes.")
        return

    if not allies:
        message.reply_text("No hay aliados pendientes por aprobar.")
        return

    for ally in allies:
        ally_id, business_name, owner_name, address, city, barrio, phone, status = ally

        texto = (
            "Aliado pendiente:\n"
            "------------------------\n"
            f"ID interno: {ally_id}\n"
            f"Negocio: {business_name}\n"
            f"Dueño: {owner_name}\n"
            f"Teléfono: {phone}\n"
            f"Dirección: {address}, {barrio}, {city}\n"
            f"Estado: {status}\n"
        )

        keyboard = [[
            InlineKeyboardButton("✅ Aprobar", callback_data=f"ally_approve_{ally_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"ally_reject_{ally_id}"),
        ]]

        message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

def repartidores_pendientes(update, context):
    message = update.effective_message
    user_db_id = get_user_db_id_from_update(update)

    # Permisos: admin de plataforma o admin local
    es_admin_plataforma = (user_id == ADMIN_USER_ID)
    admin_id = None

    if not es_admin_plataforma:
        try:
            user_db_id = get_user_db_id_from_update(update)
            admin = get_admin_by_user_id(user_db_id)

        except Exception:
            admin = None

        if not admin:
            message.reply_text("No tienes permisos para ver repartidores pendientes.")
            return

        admin_id = admin["id"] if isinstance(admin, dict) else admin[0]
        if not admin_id:
            message.reply_text("No se pudo validar tu rol de administrador.")
            return

    # Obtener pendientes según rol
    try:
        if es_admin_plataforma:
            pendientes = get_pending_couriers()  # global (tabla couriers)
        else:
            pendientes = get_pending_couriers_by_admin(admin_id)  # por equipo (tabla admin_couriers)
    except Exception as e:
        print(f"[ERROR] repartidores_pendientes: {e}")
        message.reply_text("Error consultando repartidores pendientes. Revisa logs del servidor.")
        return

    if not pendientes:
        message.reply_text("No hay repartidores pendientes por aprobar.")
        return

    for c in pendientes:
        # Ideal: que ambas funciones de DB devuelvan (courier_id, full_name, phone, city, barrio)
        if isinstance(c, dict):
            courier_id = c.get("courier_id") or c.get("id")
            full_name = c.get("full_name", "")
            phone = c.get("phone", "")
            city = c.get("city", "")
            barrio = c.get("barrio", "")
        else:
            courier_id = c[0]
            full_name = c[1] if len(c) > 1 else ""
            phone = c[2] if len(c) > 2 else ""
            city = c[3] if len(c) > 3 else ""
            barrio = c[4] if len(c) > 4 else ""

        if not courier_id:
            continue

        texto = (
            "REPARTIDOR PENDIENTE\n"
            f"ID: {courier_id}\n"
            f"Nombre: {full_name}\n"
            f"Teléfono: {phone}\n"
            f"Ciudad: {city}\n"
            f"Barrio: {barrio}"
        )

        if es_admin_plataforma:
            keyboard = [[
                InlineKeyboardButton("✅ Aprobar", callback_data=f"courier_approve_{courier_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"courier_reject_{courier_id}")
            ]]
        else:
            keyboard = [[
                InlineKeyboardButton("✅ Aprobar", callback_data=f"local_courier_approve_{courier_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"local_courier_reject_{courier_id}")
            ], [
                InlineKeyboardButton("⛔ Bloquear", callback_data=f"local_courier_block_{courier_id}")
            ]]

        message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

        
def soy_admin(update, context):
    # ID interno users.id (NO telegram_id)
    user_db_id = get_user_db_id_from_update(update)

    context.user_data.clear()

    existing = get_admin_by_user_id(user_db_id)
    if existing:
        team_name = existing[8] if len(existing) > 8 and existing[8] else existing[2]
        doc = existing[9] if len(existing) > 9 and existing[9] else "No registrado"

        update.message.reply_text(
            "Ya tienes un registro como Administrador Local.\n"
            f"Nombre: {existing[2]}\n"
            f"Documento: {doc}\n"
            f"Administración: {team_name}\n"
            f"Teléfono: {existing[3]}\n"
            f"Ciudad: {existing[4]}\n"
            f"Barrio: {existing[5]}\n"
            f"Estado: {existing[6]}\n\n"
            "Si deseas actualizar tus datos, escribe SI.\n"
            "Si no, escribe NO."
        )
        context.user_data["admin_update_prompt"] = True
        return LOCAL_ADMIN_NAME

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

    update.message.reply_text(
        "Escribe tu número de documento (CC o equivalente).\n"
        "Este dato se usa solo para control interno de la plataforma."
    )
    return LOCAL_ADMIN_DOCUMENT


def admin_document(update, context):
    doc = update.message.text.strip()

    if len(doc) < 5:
        update.message.reply_text("El número de documento parece muy corto. Escríbelo de nuevo:")
        return LOCAL_ADMIN_DOCUMENT

    context.user_data["admin_document"] = doc

    update.message.reply_text(
        "Ahora escribe el nombre de tu administración (nombre del equipo).\n"
        "Ejemplo: Mensajeros Pereira Centro"
    )
    return LOCAL_ADMIN_TEAMNAME

    
def admin_teamname(update, context):
    team_name = update.message.text.strip()

    if len(team_name) < 3:
        update.message.reply_text("El nombre de la administración debe tener al menos 3 caracteres. Escríbelo de nuevo:")
        return LOCAL_ADMIN_TEAMNAME

    context.user_data["admin_team_name"] = team_name
    update.message.reply_text("Escribe tu número de teléfono:")
    return LOCAL_ADMIN_PHONE
    

def admin_phone(update, context):
    phone = update.message.text.strip()

    if len(phone) < 7:
        update.message.reply_text("El teléfono parece inválido. Escríbelo de nuevo:")
        return LOCAL_ADMIN_PHONE

    context.user_data["phone"] = phone
    update.message.reply_text("¿En qué ciudad vas a operar como Administrador Local?")
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
    user_db_id = get_user_db_id_from_update(update)

    if answer != "ACEPTAR":
        update.message.reply_text("Registro cancelado. Si deseas intentarlo de nuevo usa /soy_admin.")
        context.user_data.clear()
        return ConversationHandler.END
        
    full_name = (context.user_data.get("admin_name") or "").strip()
    document_number = (context.user_data.get("admin_document") or "").strip()
    team_name = (context.user_data.get("admin_team_name") or "").strip()
    phone = (context.user_data.get("phone") or "").strip()
    city = (context.user_data.get("admin_city") or "").strip()
    barrio = (context.user_data.get("admin_barrio") or "").strip()

    admin_id, team_code = create_admin(user_id, full_name, phone, city, barrio, team_name, document_number)

   
    update.message.reply_text(
        "Registro de Administrador Local recibido.\n"
        "Estado: PENDING\n\n"
        f"Tu CÓDIGO DE EQUIPO es: {team_code}\n"
        "Compártelo con los repartidores que quieras vincular a tu equipo.\n\n"
        "Recuerda: para ser aprobado debes registrar 10 repartidores con recarga mínima de 5000 cada uno."
    )

    context.user_data.clear()
    return ConversationHandler.END
    
        
def admin_menu(update, context):
    """Panel de Administración de Plataforma."""
    user = update.effective_user
    user_db_id = get_user_db_id_from_update(update)

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
        [InlineKeyboardButton("🧑‍💼 Gestionar administradores", callback_data="admin_administradores")],
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
        aliados_pendientes(update, context)
        return

    # Botón: Repartidores pendientes (Plataforma)
    if data == "admin_repartidores_pendientes":
        query.answer()
        repartidores_pendientes(update, context)
        return

    # Botón: Gestionar administradores (submenú)
    if data == "admin_administradores":
        query.answer()
        keyboard = [
            [InlineKeyboardButton("📋 Administradores registrados", callback_data="admin_admins_registrados")],
            [InlineKeyboardButton("⏳ Administradores pendientes", callback_data="admin_admins_pendientes")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Gestión de administradores.\n¿Qué deseas hacer?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Submenú admins: pendientes
    if data == "admin_admins_pendientes":
        query.answer()
        try:
            admins_pendientes(update, context)
        except Exception as e:
            print("[ERROR] admins_pendientes:", e)
            query.edit_message_text(
                "Error mostrando administradores pendientes. Revisa logs.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")]
                ])
            )
        return

    # Submenú admins: registrados (placeholder por ahora)
    if data == "admin_admins_registrados":
        query.answer()
        query.edit_message_text(
            "Administradores registrados: (pendiente de implementar)\n\n"
            "⬅️ Usa el botón 'Volver al Panel' para regresar.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")]
            ])
        )
        return

    # Volver al panel (reconstruye el teclado sin llamar admin_menu, para evitar update.message)
    if data == "admin_volver_panel":
        query.answer()

        texto = (
            "Panel de Administración de Plataforma.\n"
            "¿Qué deseas revisar?"
        )
        keyboard = [
            [InlineKeyboardButton("👤 Aliados pendientes", callback_data="admin_aliados_pendientes")],
            [InlineKeyboardButton("🚚 Repartidores pendientes", callback_data="admin_repartidores_pendientes")],
            [InlineKeyboardButton("🧑‍💼 Gestionar administradores", callback_data="admin_administradores")],
            [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos")],
            [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
            [InlineKeyboardButton("💰 Tarifas", callback_data="admin_tarifas")],
            [InlineKeyboardButton("📊 Finanzas", callback_data="admin_finanzas")],
        ]

        query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Botones aún no implementados (placeholders)
    if data == "admin_pedidos":
        query.answer("La sección de pedidos de la Plataforma aún no está implementada.")
        return

    if data == "admin_config":
        query.answer()
        keyboard = [
            [InlineKeyboardButton("Ver totales de registros", callback_data="config_totales")],
            [InlineKeyboardButton("Gestionar aliados", callback_data="config_gestion_aliados")],
            [InlineKeyboardButton("Gestionar repartidores", callback_data="config_gestion_repartidores")],
            [InlineKeyboardButton("Gestionar administradores", callback_data="config_gestion_administradores")],
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

    # Ver admin pendiente (detalle)
    if data.startswith("admin_ver_pendiente_"):
        query.answer()
        admin_ver_pendiente(update, context)
        return

    # Aprobar admin local
    if data.startswith("admin_aprobar_"):
        query.answer()
        admin_id = int(data.split("_")[-1])

        update_admin_status_by_id(admin_id, "APPROVED")

        # Notificar al administrador aprobado (pero aclarando que NO puede operar aún)
        try:
            admin = get_admin_by_id(admin_id)
            admin_user_db_id = admin[1]  # users.id interno

            u = get_user_by_id(admin_user_db_id)  # debe existir en db.py
            if u:
                admin_telegram_id = u["telegram_id"]

                msg = (
                    "✅ Tu cuenta de Administrador Local ha sido APROBADA.\n\n"
                    "IMPORTANTE: La aprobación no significa que ya puedas operar.\n"
                    "Para operar debes cumplir los requisitos.\n\n"
                    "Requisitos para operar:\n"
                    "1) Tener mínimo 10 repartidores vinculados a tu equipo.\n"
                    "2) Cada uno debe estar APROBADO y con saldo por vínculo >= 5000.\n"
                    "3) Mantener tu cuenta activa y cumplir las reglas de la plataforma.\n\n"
                    "Cuando intentes usar funciones operativas, el sistema validará estos requisitos."
                )
                context.bot.send_message(chat_id=admin_telegram_id, text=msg)

        except Exception as e:
            print("[WARN] No se pudo notificar al admin aprobado:", e)

        query.edit_message_text(
            "✅ Administrador aprobado correctamente.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver", callback_data="admin_admins_pendientes")]
            ])
        )
        return

    # Rechazar admin local
    if data.startswith("admin_rechazar_"):
        query.answer()
        admin_id = int(data.split("_")[-1])

        update_admin_status_by_id(admin_id, "REJECTED")

        query.edit_message_text(
            "❌ Administrador rechazado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver", callback_data="admin_admins_pendientes")]
            ])
        )
        return

    # Por si llega algo raro
    query.answer("Opción no reconocida.", show_alert=True)


def cancel_conversacion(update, context):
    # Cierra cualquier conversación activa y limpia datos temporales
    try:
        context.user_data.clear()
    except Exception:
        pass

    # Responder según sea mensaje o callback (si lo usas en botones)
    if getattr(update, "callback_query", None):
        q = update.callback_query
        q.answer()
        q.edit_message_text("Proceso cancelado. Puedes iniciar de nuevo cuando quieras.")
    else:
        update.message.reply_text("Proceso cancelado. Puedes iniciar de nuevo cuando quieras.")

    return ConversationHandler.END

def courier_pick_admin_callback(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    # courier_id que acabamos de crear (guardado en courier_confirm)
    courier_id = context.user_data.get("new_courier_id")

    # Opción: no elegir admin
    if data == "courier_pick_admin_none":
        query.edit_message_text("Perfecto. Quedaste registrado sin equipo por ahora.")
        context.user_data.clear()
        return

    # Validación básica del callback
    if not data.startswith("courier_pick_admin_"):
        query.edit_message_text("Opción no reconocida.")
        return

    if not courier_id:
        query.edit_message_text(
            "No encontré tu registro reciente para vincular a un equipo.\n"
            "Intenta /soy_repartidor de nuevo."
        )
        context.user_data.clear()
        return

    # Extraer admin_id
    try:
        admin_id = int(data.split("_")[-1])
    except Exception:
        query.edit_message_text("Error leyendo la opción seleccionada. Intenta de nuevo.")
        return

    # Crear vínculo PENDING en admin_couriers
    try:
        create_admin_courier_link(admin_id, courier_id)
    except Exception as e:
        print("[ERROR] create_admin_courier_link:", e)
        query.edit_message_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
        context.user_data.clear()
        return

    # Notificar al admin local (sin depender de get_user_by_id)
    admin_telegram_id = None
    try:
        admin = get_admin_by_id(admin_id)

        # Heurística:
        # - si admin[1] parece un Telegram ID (muy grande), lo usamos como chat_id
        # - si no, NO rompemos el flujo (solo omitimos notificación)
        admin_user_field = None
        if isinstance(admin, dict):
            admin_user_field = admin.get("user_id")
        else:
            admin_user_field = admin[1] if len(admin) > 1 else None

        if admin_user_field is not None:
            try:
                admin_user_field_int = int(admin_user_field)
                if admin_user_field_int > 100000000:  # típico telegram_id
                    admin_telegram_id = admin_user_field_int
            except Exception:
                admin_telegram_id = None

    except Exception as e:
        print("[WARN] No se pudo leer admin para notificación:", e)

    if admin_telegram_id:
        try:
            context.bot.send_message(
                chat_id=admin_telegram_id,
                text=(
                    "📥 Nueva solicitud de repartidor para tu equipo.\n\n"
                    f"Repartidor ID: {courier_id}\n\n"
                    "Entra a /mi_admin para revisar pendientes."
                )
            )
        except Exception as e:
            print("[WARN] No se pudo notificar al admin local:", e)

    query.edit_message_text(
        "Listo. Tu solicitud fue enviada. Quedas PENDIENTE de aprobación."
    )
    context.user_data.clear()


def admins_pendientes(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    # Seguridad: solo Admin de Plataforma
    if user_id != ADMIN_USER_ID:
        query.answer("No tienes permisos para esto.", show_alert=True)
        return

    # Responder el callback para evitar “cargando…”
    query.answer()

    try:
        admins = get_pending_admins()
    except Exception as e:
        print("[ERROR] get_pending_admins:", e)
        query.edit_message_text(
            "Error consultando administradores pendientes. Revisa logs.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver al Panel", callback_data="admin_volver_panel")]
            ])
        )
        return

    if not admins:
        query.edit_message_text(
            "No hay administradores pendientes en este momento.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver al Panel", callback_data="admin_volver_panel")]
            ])
        )
        return

    keyboard = []
    for admin in admins:
        admin_id = admin[0]
        full_name = admin[2]
        city = admin[4]

        keyboard.append([
            InlineKeyboardButton(
                "ID {} - {} ({})".format(admin_id, full_name, city),
                callback_data="admin_ver_pendiente_{}".format(admin_id)
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅ Volver al Panel", callback_data="admin_volver_panel")])

    query.edit_message_text(
        "Administradores pendientes de aprobación:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    

def admin_ver_pendiente(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != ADMIN_USER_ID:
        query.answer("No tienes permisos.", show_alert=True)
        return

    admin_id = int(query.data.split("_")[-1])
    admin = get_admin_by_id(admin_id)

    if not admin:
        query.edit_message_text("Administrador no encontrado.")
        return

    # id, user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number
    texto = (
        "Administrador pendiente:\n\n"
        f"ID: {admin[0]}\n"
        f"Nombre: {admin[2]}\n"
        f"Teléfono: {admin[3]}\n"
        f"Ciudad: {admin[4]}\n"
        f"Barrio: {admin[5]}\n"
        f"Equipo: {admin[8] or '-'}\n"
        f"Documento: {admin[9] or '-'}\n"
        f"Estado: {admin[6]}"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Aprobar", callback_data=f"admin_aprobar_{admin_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"admin_rechazar_{admin_id}")
        ],
        [InlineKeyboardButton("⬅ Volver", callback_data="admin_admins_pendientes")]
    ]

    query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

def admin_aprobar_rechazar_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    # Solo Admin de Plataforma
    if user_id != ADMIN_USER_ID:
        query.answer("No tienes permisos.", show_alert=True)
        return

    partes = data.split("_")  # admin_aprobar_12
    if len(partes) != 3:
        query.answer("Datos inválidos.", show_alert=True)
        return

    _, accion, admin_id_str = partes

    try:
        admin_id = int(admin_id_str)
    except ValueError:
        query.answer("ID inválido.", show_alert=True)
        return

    if accion == "aprobar":
        try:
            update_admin_status_by_id(admin_id, "APPROVED")
        except Exception as e:
            print("[ERROR] update_admin_status_by_id APPROVED:", e)
            query.edit_message_text("Error aprobando administrador. Revisa logs.")
            return

        query.edit_message_text("✅ Administrador aprobado (APPROVED).")
        return

    if accion == "rechazar":
        try:
            update_admin_status_by_id(admin_id, "REJECTED")
        except Exception as e:
            print("[ERROR] update_admin_status_by_id REJECTED:", e)
            query.edit_message_text("Error rechazando administrador. Revisa logs.")
            return

        query.edit_message_text("❌ Administrador rechazado (REJECTED).")
        return

    query.answer("Acción no reconocida.", show_alert=True)


def pendientes(update, context):
    """Menú rápido para ver registros pendientes."""
    user_db_id = get_user_db_id_from_update(update)

    es_admin_plataforma = (user_id == ADMIN_USER_ID)

    if not es_admin_plataforma:
        try:
            user_db_id = get_user_db_id_from_update(update)
            admin = get_admin_by_user_id(user_db_id)

        except Exception:
            admin = None

        if not admin:
            update.message.reply_text("No tienes permisos para usar este comando.")
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
        ALLY_PHONE: [MessageHandler(Filters.text & ~Filters.command, ally_phone)],
        ALLY_BARRIO: [MessageHandler(Filters.text & ~Filters.command, ally_barrio)],
    },
    fallbacks=[CommandHandler("cancel", cancel_conversacion)],
    allow_reentry=True,
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
    fallbacks=[CommandHandler("cancel", cancel_conversacion)],
    allow_reentry=True,
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
    fallbacks=[CommandHandler("cancel", cancel_conversacion)],
    allow_reentry=True,
)
def admin_puede_operar(admin_id):
    """
    Aprobación != operación.
    Operación solo si cumple requisitos en tiempo real.
    Retorna (True, None) o (False, mensaje).
    """
    admin = get_admin_by_id(admin_id)
    if not admin:
        return (False, "No se pudo validar tu cuenta de administrador.")

    status = admin[6]  # status en admins

    if status != "APPROVED":
        return (False, f"Tu cuenta no está habilitada. Estado actual: {status}")

    total = count_admin_couriers(admin_id)
    ok = count_admin_couriers_with_min_balance(admin_id, 5000)

    if total < 10 or ok < 10:
        msg = (
            "Aún no puedes operar como Administrador Local.\n\n"
            "Requisitos para operar:\n"
            "1) 10 repartidores vinculados a tu equipo\n"
            "2) Los 10 deben estar APROBADOS\n"
            "3) Cada uno con saldo por vínculo >= 5000\n\n"
            f"Tu estado actual:\n"
            f"- Vinculados: {total}\n"
            f"- Con saldo >= 5000: {ok}\n\n"
            "Acción: completa vínculos y recargas. Cuando cumplas, el sistema te habilita automáticamente."
        )
        return (False, msg)

    return (True, None)
           

def mi_admin(update, context):
    user_db_id = get_user_db_id_from_update(update)

    # Validar que sea admin local registrado
    admin = None
    try:
        user_db_id = get_user_db_id_from_update(update)
        admin = get_admin_by_user_id(user_db_id)
  # puede devolver dict o tupla
    except Exception:
        admin = None

    if not admin:
        update.message.reply_text("No tienes perfil de Administrador Local registrado.")
        return

    # Soportar dict/tupla
    admin_id = admin["id"] if isinstance(admin, dict) else admin[0]

    # Traer detalle completo (incluye team_code)
    admin_full = get_admin_by_id(admin_id)
    if not admin_full:
        update.message.reply_text("No se pudo cargar tu perfil de administrador. Revisa BD.")
        return

    status = admin_full[6]
    team_name = admin_full[8] or "-"
    team_code = "-"
    if isinstance(admin_full, dict):
        team_code = admin_full.get("team_code") or "-"
    else:
        team_code = admin_full[10] if len(admin_full) > 10 and admin_full[10] else "-"

    # Validación operativa en tiempo real
    ok, msg = admin_puede_operar(admin_id)

    header = (
        "Panel Administrador Local\n\n"
        f"Estado: {status}\n"
        f"Equipo: {team_name}\n"
        f"Código de equipo: {team_code}\n"
        "Compártelo a tus repartidores para que soliciten unirse a tu equipo.\n\n"
    )

    if not ok:
        keyboard = [
            [InlineKeyboardButton("🔄 Verificar de nuevo", callback_data=f"local_check_{admin_id}")],
        ]
        update.message.reply_text(
            header + msg,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Si ya puede operar (menú mínimo por ahora)
    keyboard = [
        [InlineKeyboardButton("⏳ Repartidores pendientes (mi equipo)", callback_data=f"local_couriers_pending_{admin_id}")],
        [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
        [InlineKeyboardButton("🔄 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
    ]

    update.message.reply_text(
        header +
        "Ya cumples requisitos para operar.\n"
        "Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def admin_local_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    # Validar que sea admin local
    admin = None
    try:
        user_db_id = get_user_db_id_from_update(update)
        admin = get_admin_by_user_id(user_db_id)

    except Exception:
        admin = None

    if not admin:
        query.edit_message_text("No autorizado.")
        return

    admin_id = admin["id"] if isinstance(admin, dict) else admin[0]

    # Seguridad extra SOLO para callbacks que terminan en admin_id
    if data.startswith(("local_check_", "local_status_", "local_couriers_pending_")):
        try:
            target_admin_id = int(data.split("_")[-1])
            if target_admin_id != admin_id:
                query.edit_message_text("No autorizado.")
                return
        except Exception:
            query.edit_message_text("No autorizado.")
            return

    if data.startswith("local_check_"):
        ok, msg = admin_puede_operar(admin_id)
        admin_full = get_admin_by_id(admin_id)
        status = admin_full[6]

        if not ok:
            keyboard = [
                [InlineKeyboardButton("🔄 Verificar de nuevo", callback_data=f"local_check_{admin_id}")],
            ]
            query.edit_message_text(
                "Panel Administrador Local\n\n"
                f"Estado: {status}\n\n"
                + msg,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        keyboard = [
            [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            [InlineKeyboardButton("🔄 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
        ]
        query.edit_message_text(
            "Panel Administrador Local\n\n"
            "Ya cumples requisitos para operar.\n"
            "Selecciona una opción:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("local_status_"):
        admin_full = get_admin_by_id(admin_id)
        status = admin_full[6]
        total = count_admin_couriers(admin_id)
        okb = count_admin_couriers_with_min_balance(admin_id, 5000)

        texto = (
            "Estado de tu cuenta (Admin Local):\n\n"
            f"Estado: {status}\n"
            f"Repartidores vinculados: {total}\n"
            f"Con saldo >= 5000: {okb}\n\n"
            "Recuerda: Aprobado no siempre significa operativo; el sistema valida requisitos en tiempo real."
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("local_couriers_pending_"):
        try:
            pendientes = get_pending_couriers_by_admin(admin_id)  # db.py
        except Exception as e:
            print("[ERROR] get_pending_couriers_by_admin:", e)
            query.edit_message_text("Error consultando pendientes de tu equipo.")
            return

        if not pendientes:
            query.edit_message_text(
                "No tienes repartidores pendientes por aprobar en tu equipo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data=f"local_check_{admin_id}")]
                ])
            )
            return

        keyboard = []
        for c in pendientes:
            courier_id = c[0]
            full_name = c[1] if len(c) > 1 else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"ID {courier_id} - {full_name}",
                    callback_data=f"local_courier_view_{courier_id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data=f"local_check_{admin_id}")])

        query.edit_message_text(
            "Repartidores pendientes (tu equipo). Toca uno para ver detalle:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("local_courier_view_"):
        courier_id = int(data.split("_")[-1])

        courier = get_courier_by_id(courier_id)
        if not courier:
            query.edit_message_text("No se encontró el repartidor.")
            return

        texto = (
            "REPARTIDOR (pendiente de tu equipo)\n\n"
            f"ID: {courier[0]}\n"
            f"Nombre: {courier[2]}\n"
            f"Documento: {courier[3]}\n"
            f"Teléfono: {courier[4]}\n"
            f"Ciudad: {courier[5]}\n"
            f"Barrio: {courier[6]}\n"
            f"Placa: {courier[7] or '-'}\n"
            f"Moto: {courier[8] or '-'}\n"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"local_courier_approve_{courier_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"local_courier_reject_{courier_id}")
            ],
            [InlineKeyboardButton("⛔ Bloquear", callback_data=f"local_courier_block_{courier_id}")],
            [InlineKeyboardButton("⬅ Volver", callback_data=f"local_couriers_pending_{admin_id}")]
        ]

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("local_courier_approve_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "APPROVED")
        except Exception as e:
            print("[ERROR] update_admin_courier_status APPROVED:", e)
            query.edit_message_text("Error aprobando repartidor. Revisa logs.")
            return

        query.edit_message_text(
            "✅ Repartidor aprobado en tu equipo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_courier_reject_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "REJECTED")
        except Exception as e:
            print("[ERROR] update_admin_courier_status REJECTED:", e)
            query.edit_message_text("Error rechazando repartidor. Revisa logs.")
            return

        query.edit_message_text(
            "❌ Repartidor rechazado para tu equipo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_courier_block_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "BLOCKED")
        except Exception as e:
            print("[ERROR] update_admin_courier_status BLOCKED:", e)
            query.edit_message_text("Error bloqueando repartidor. Revisa logs.")
            return

        query.edit_message_text(
            "⛔ Repartidor bloqueado en tu equipo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    query.edit_message_text("Opción no reconocida.")
    
def ally_approval_callback(update, context):
    """Maneja los botones de aprobar / rechazar aliados (solo Admin Plataforma)."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador de plataforma puede usar estos botones.", show_alert=True)
        return

    partes = data.split("_")  # ally_approve_3
    if len(partes) != 3 or partes[0] != "ally":
        query.answer("Datos de botón no válidos.", show_alert=True)
        return

    accion = partes[1]
    try:
        ally_id = int(partes[2])
    except ValueError:
        query.answer("ID de aliado no válido.", show_alert=True)
        return

    if accion not in ("approve", "reject"):
        query.answer("Acción no reconocida.", show_alert=True)
        return

    nuevo_estado = "APPROVED" if accion == "approve" else "REJECTED"

    try:
        update_ally_status(ally_id, nuevo_estado)
    except Exception as e:
        print(f"[ERROR] ally_approval_callback: {e}")
        query.answer("Error actualizando el aliado. Revisa logs.", show_alert=True)
        return

    ally = get_ally_by_id(ally_id)
    if not ally:
        query.edit_message_text("No se encontró el aliado después de actualizar.")
        return

    # Estructura esperada: id, user_id(telegram_id), business_name, owner_name, phone, address, city, barrio, status
    ally_user_id = ally[1]       # EN TU DISEÑO ACTUAL ESTO ES telegram_id (porque create_ally usa user_id=telegram_id)
    business_name = ally[2]

    # Notificar al aliado (si falla, no rompemos el flujo)
    try:
        u = get_user_by_id(ally_user_id)  # debe existir en db.py
        ally_telegram_id = u["telegram_id"] if isinstance(u, dict) else u[1]

        context.bot.send_message(
            chat_id=ally_telegram_id,
            text=(
                "Tu registro como aliado '{}' ha sido {}.\n"
                "{}"
            ).format(
                business_name,
                "APROBADO" if accion == "approve" else "RECHAZADO",
                "Ya puedes usar el bot para crear pedidos." if accion == "approve"
                else "Si crees que es un error, comunícate con el administrador."
            )
        )
    except Exception as e:
        print("Error notificando aliado:", e)


    if nuevo_estado == "APPROVED":
        query.edit_message_text("✅ El aliado '{}' ha sido APROBADO.".format(business_name))
    else:
        query.edit_message_text("❌ El aliado '{}' ha sido RECHAZADO.".format(business_name))


def pendientes_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    es_admin_plataforma = (user_id == ADMIN_USER_ID)

    if not es_admin_plataforma:
        try:
            user_db_id = get_user_db_id_from_update(update)
            admin = get_admin_by_user_id(user_db_id)

        except Exception:
            admin = None
        if not admin:
            query.answer("No tienes permisos.", show_alert=True)
            return

    if data == "menu_aliados_pendientes":
        aliados_pendientes(update, context)
        return

    if data == "menu_repartidores_pendientes":
        repartidores_pendientes(update, context)
        return

    query.answer("Opción no reconocida.", show_alert=True)


def courier_approval_callback(update, context):
    """Aprobación / rechazo global de repartidores (solo Admin Plataforma)."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    # En tu main(), este handler ^courier_(approve|reject)_\d+$ está pensado para ADMIN PLATAFORMA.
    # La aprobación por Admin Local va por admin_local_callback con local_courier_approve/reject/block.
    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador de plataforma puede usar estos botones.", show_alert=True)
        return

    partes = data.split("_")  # courier_approve_3
    if len(partes) != 3 or partes[0] != "courier":
        query.answer("Datos de botón no válidos.", show_alert=True)
        return

    accion = partes[1]
    try:
        courier_id = int(partes[2])
    except ValueError:
        query.answer("ID de repartidor no válido.", show_alert=True)
        return

    if accion not in ("approve", "reject"):
        query.answer("Acción no reconocida.", show_alert=True)
        return

    nuevo_estado = "APPROVED" if accion == "approve" else "REJECTED"

    # Actualizar estado global del courier
    try:
        update_courier_status(courier_id, nuevo_estado)
    except Exception as e:
        print(f"[ERROR] update_courier_status: {e}")
        query.answer("Error actualizando repartidor. Revisa logs.", show_alert=True)
        return

    courier = get_courier_by_id(courier_id)
    if not courier:
        query.edit_message_text("No se encontró el repartidor después de actualizar.")
        return

    # courier esperado: id, user_id(users.id), full_name, id_number, phone, city, barrio, plate, bike_type, code, status
    courier_user_db_id = courier[1]   # users.id
    full_name = courier[2]

    # Notificar al repartidor si existe get_user_by_id (recomendado).
    # Si no existe, solo omitimos notificación sin romper.
    try:
        u = get_user_by_id(courier_user_id)  # debe existir en db.py
        courier_telegram_id = u["telegram_id"] if isinstance(u, dict) else u[1]

        if accion == "approve":
            msg = "Tu registro como repartidor ha sido APROBADO. Bienvenido, {}.".format(full_name)
        else:
            msg = (
                "Tu registro como repartidor ha sido RECHAZADO, {}.\n"
                "Si crees que es un error, comunícate con el administrador."
            ).format(full_name)

        context.bot.send_message(chat_id=courier_telegram_id, text=msg)
    except Exception as e:
        print("Error notificando repartidor:", e)

    if nuevo_estado == "APPROVED":
        query.edit_message_text("✅ El repartidor '{}' ha sido APROBADO.".format(full_name))
    else:
        query.edit_message_text("❌ El repartidor '{}' ha sido RECHAZADO.".format(full_name))


def admin_configuraciones(update, context):
    user_db_id = get_user_db_id_from_update(update)
    if not es_admin(user_id):
        return

    keyboard = [
        [InlineKeyboardButton("Ver totales de registros", callback_data="config_totales")],
        [InlineKeyboardButton("Gestionar aliados", callback_data="config_gestion_aliados")],
        [InlineKeyboardButton("Gestionar repartidores", callback_data="config_gestion_repartidores")],
        [InlineKeyboardButton("Gestionar administradores", callback_data="config_gestion_administradores")],
        [InlineKeyboardButton("Cerrar", callback_data="config_cerrar")],
    ]
    update.message.reply_text(
        "Configuraciones de administración. ¿Qué deseas hacer?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def admin_config_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    if not es_admin(user_id):
        query.answer("No tienes permisos para esto.", show_alert=True)
        return

    if data == "config_totales":
        total_allies, total_couriers = get_totales_registros()
        total_admins = get_local_admins_count()

        texto = (
            "Resumen de registros:\n\n"
            "Aliados registrados: {}\n"
            "Repartidores registrados: {}\n"
            "Administradores locales registrados: {}"
        ).format(total_allies, total_couriers, total_admins)

        query.edit_message_text(texto)
        return


    if data == "config_gestion_aliados":
        allies = get_all_allies()
        if not allies:
            query.edit_message_text("No hay aliados registrados en este momento.")
            return

        keyboard = []
        for ally in allies:
            ally_id = ally[0]
            business_name = ally[2]
            status = ally[8]
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(ally_id, business_name, status),
                callback_data="config_ver_ally_{}".format(ally_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_cerrar")])
        query.edit_message_text(
            "Aliados registrados. Toca uno para ver detalle.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("config_ver_ally_"):
        ally_id = int(data.split("_")[-1])
        ally = get_ally_by_id(ally_id)
        if not ally:
            query.edit_message_text("No se encontró el aliado.")
            return

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
            [InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("config_confirm_delete_ally_"):
        ally_id = int(data.split("_")[-1])
        delete_ally(ally_id)
        query.edit_message_text("El aliado {} ha sido eliminado.".format(ally_id))
        return

    if data == "config_gestion_repartidores":
        couriers = get_all_couriers()
        if not couriers:
            query.edit_message_text("No hay repartidores registrados en este momento.")
            return

        keyboard = []
        for courier in couriers:
            courier_id = courier[0]
            full_name = courier[2]
            status = courier[10]
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(courier_id, full_name, status),
                callback_data="config_ver_courier_{}".format(courier_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_cerrar")])
        query.edit_message_text(
            "Repartidores registrados. Toca uno para ver detalle.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

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
            [InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("config_confirm_delete_courier_"):
        courier_id = int(data.split("_")[-1])
        delete_courier(courier_id)
        query.edit_message_text("El repartidor {} ha sido eliminado.".format(courier_id))
        return

    if data == "config_gestion_administradores":
        admins = get_all_admins()
        if not admins:
            query.edit_message_text("No hay administradores registrados en este momento.")
            return

        keyboard = []
        for a in admins:
            admin_id = a[0]
            full_name = a[2]
            team_name = a[8] or "-"
            status = a[6]
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} | {} ({})".format(admin_id, full_name, team_name, status),
                callback_data="config_ver_admin_{}".format(admin_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_cerrar")])
        query.edit_message_text(
            "Administradores registrados. Toca uno para ver detalle.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("config_ver_admin_"):
        admin_id = int(data.split("_")[-1])
        admin = get_admin_by_id(admin_id)
        if not admin:
            query.edit_message_text("No se encontró el administrador.")
            return

        status = admin[6]
        total_couriers = count_admin_couriers(admin_id)
        couriers_ok_balance = count_admin_couriers_with_min_balance(admin_id, 5000)

        texto = (
            "Detalle del administrador:\n\n"
            "ID: {id}\n"
            "Nombre: {full_name}\n"
            "Teléfono: {phone}\n"
            "Ciudad: {city}\n"
            "Barrio: {barrio}\n"
            "Equipo: {team}\n"
            "Documento: {doc}\n"
            "Estado: {status}\n\n"
            "Regla de aprobación:\n"
            "- Repartidores vinculados: {total}\n"
            "- Con saldo >= 5000: {ok}\n"
            "Requisito: 10 y 10"
        ).format(
            id=admin[0],
            full_name=admin[2],
            phone=admin[3],
            city=admin[4],
            barrio=admin[5],
            team=admin[8] or "-",
            doc=admin[9] or "-",
            status=status,
            total=total_couriers,
            ok=couriers_ok_balance,
        )

        keyboard = []
        if status == "PENDING":
            keyboard.append([
                InlineKeyboardButton("✅ Aprobar", callback_data="config_admin_approve_{}".format(admin_id)),
                InlineKeyboardButton("❌ Rechazar", callback_data="config_admin_reject_{}".format(admin_id)),
            ])
        if status == "APPROVED":
            keyboard.append([InlineKeyboardButton("⛔ Desactivar", callback_data="config_admin_disable_{}".format(admin_id))])
        if status == "INACTIVE":
            keyboard.append([InlineKeyboardButton("✅ Activar", callback_data="config_admin_enable_{}".format(admin_id))])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_administradores")])
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("config_admin_approve_"):
        admin_id = int(data.split("_")[-1])
        update_admin_status_by_id(admin_id, "APPROVED")
        query.edit_message_text(
            "Administrador aprobado (APPROVED).\n\n"
            "Nota: la operación se habilita automáticamente cuando cumpla requisitos (10 repartidores y saldo >= 5000)."
        )
        return

    if data.startswith("config_admin_reject_"):
        admin_id = int(data.split("_")[-1])
        update_admin_status_by_id(admin_id, "REJECTED")
        query.edit_message_text("Administrador rechazado (REJECTED).")
        return

    if data.startswith("config_admin_disable_"):
        admin_id = int(data.split("_")[-1])
        update_admin_status_by_id(admin_id, "INACTIVE")
        query.edit_message_text("Administrador desactivado (INACTIVE).")
        return

    if data.startswith("config_admin_enable_"):
        admin_id = int(data.split("_")[-1])
        update_admin_status_by_id(admin_id, "APPROVED")
        query.edit_message_text("Administrador activado (APPROVED).")
        return

    if data == "config_cerrar":
        query.edit_message_text("Menú de configuraciones cerrado.")
        return

    query.answer("Opción no reconocida.", show_alert=True)


def ensure_terms(update, context, telegram_id: int, role: str) -> bool:
    tv = get_active_terms_version(role)
    if not tv:
        context.bot.send_message(
            chat_id=telegram_id,
            text="Términos no configurados para este rol. Contacta al soporte de la plataforma."
        )
        return False

    version, url, sha256 = tv

    if has_accepted_terms(telegram_id, role, version, sha256):
        try:
            save_terms_session_ack(telegram_id, role, version)
        except Exception as e:
            print("[WARN] save_terms_session_ack:", e)
        return True

    text = (
        "Antes de continuar debes aceptar los Términos y Condiciones de Domiquerendona.\n\n"
        "Rol: {}\n"
        "Versión: {}\n\n"
        "Lee el documento y confirma tu aceptación para continuar."
    ).format(role, version)

    keyboard = [
        [InlineKeyboardButton("Leer términos", url=url)],
        [
            InlineKeyboardButton("Acepto", callback_data="terms_accept_{}".format(role)),
            InlineKeyboardButton("No acepto", callback_data="terms_decline_{}".format(role)),
        ],
    ]

    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        context.bot.send_message(chat_id=telegram_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    return False


def terms_callback(update, context):
    query = update.callback_query
    data = query.data
    telegram_id = query.from_user.id
    query.answer()

    if data.startswith("terms_accept_"):
        role = data.split("_", 2)[-1]
        tv = get_active_terms_version(role)
        if not tv:
            query.edit_message_text("Términos no configurados. Contacta soporte.")
            return

        version, url, sha256 = tv
        save_terms_acceptance(telegram_id, role, version, sha256, query.message.message_id)
        query.edit_message_text("Aceptación registrada. Ya puedes continuar.")
        return

    if data.startswith("terms_decline_"):
        query.edit_message_text(
            "No puedes usar la plataforma sin aceptar los Términos y Condiciones.\n"
            "Si cambias de decisión, vuelve a intentar y acepta los términos."
        )
        return

    query.answer("Opción no reconocida.", show_alert=True)


def main():
    # Inicializar base de datos
    init_db()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    print("[BOOT] Iniciando polling...")

    # -------------------------
    # Comandos básicos
    # -------------------------
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("cancel", cancel_conversacion))

    # -------------------------
    # Comandos administrativos (Plataforma y/o Admin Local según tu validación interna)
    # -------------------------
    dp.add_handler(CommandHandler("id", cmd_id))
    dp.add_handler(CommandHandler("pendientes", pendientes))
    dp.add_handler(CommandHandler("aliados_pendientes", aliados_pendientes))
    dp.add_handler(CommandHandler("repartidores_pendientes", repartidores_pendientes))
    dp.add_handler(CallbackQueryHandler(courier_pick_admin_callback, pattern=r"^courier_pick_admin_"))

    # Panel de Plataforma
    dp.add_handler(CommandHandler("admin", admin_menu))
    # comandos de los administradores
    dp.add_handler(CommandHandler("mi_admin", mi_admin))
    dp.add_handler(CallbackQueryHandler(
        admin_local_callback,
        pattern=r"^local_(check|status|couriers_pending|courier_view|courier_approve|courier_reject|courier_block)_\d+$"
    ))

    # -------------------------
    # Callbacks (ordenados por especificidad)
    # -------------------------

    # Menú de pendientes (botones menu_*)
    dp.add_handler(CallbackQueryHandler(pendientes_callback, pattern=r"^menu_"))

    # Configuraciones (botones config_*)
    dp.add_handler(CallbackQueryHandler(admin_config_callback, pattern=r"^config_"))

    # Aprobación / rechazo Aliados (botones ally_approve_ID / ally_reject_ID o similar)
    # Ajusta el patrón si tu callback_data exacto difiere
    dp.add_handler(CallbackQueryHandler(ally_approval_callback, pattern=r"^ally_(approve|reject)_\d+$"))

    # Aprobación / rechazo Repartidores (botones courier_approve_ID / courier_reject_ID)
    dp.add_handler(CallbackQueryHandler(courier_approval_callback, pattern=r"^courier_(approve|reject)_\d+$"))

    # -------------------------
    # Panel admin plataforma (botones admin_*)
    # -------------------------

    # 1) Admins pendientes (handlers específicos)
    dp.add_handler(CallbackQueryHandler(admins_pendientes, pattern=r"^admin_admins_pendientes$"))
    dp.add_handler(CallbackQueryHandler(admin_ver_pendiente, pattern=r"^admin_ver_pendiente_\d+$"))
    dp.add_handler(CallbackQueryHandler(admin_aprobar_rechazar_callback, pattern=r"^admin_(aprobar|rechazar)_\d+$"))
    dp.add_handler(CallbackQueryHandler(admin_menu_callback, pattern=r"^admin_"))


    # -------------------------
    # Conversaciones completas
    # -------------------------
    dp.add_handler(ally_conv)          # /soy_aliado
    dp.add_handler(courier_conv)       # /soy_repartidor
    dp.add_handler(nuevo_pedido_conv)  # /nuevo_pedido
    dp.add_handler(CallbackQueryHandler(terms_callback, pattern=r"^terms_"))  # /ternimos y condiciones


    # -------------------------
    # Registro de Administradores Locales
    # -------------------------
    admin_conv = ConversationHandler(
        entry_points=[
            CommandHandler("soy_admin", soy_admin),
            CommandHandler("soy_administrador", soy_admin),
        ],

        states={
            LOCAL_ADMIN_NAME: [MessageHandler(Filters.text & ~Filters.command, admin_name)],
            LOCAL_ADMIN_DOCUMENT: [MessageHandler(Filters.text & ~Filters.command, admin_document)],
            LOCAL_ADMIN_TEAMNAME: [MessageHandler(Filters.text & ~Filters.command, admin_teamname)],
            LOCAL_ADMIN_PHONE: [MessageHandler(Filters.text & ~Filters.command, admin_phone)],
            LOCAL_ADMIN_CITY: [MessageHandler(Filters.text & ~Filters.command, admin_city)],
            LOCAL_ADMIN_BARRIO: [MessageHandler(Filters.text & ~Filters.command, admin_barrio)],
            LOCAL_ADMIN_ACCEPT: [MessageHandler(Filters.text & ~Filters.command, admin_accept)],
        },
       fallbacks=[CommandHandler("cancel", cancel_conversacion)],
    )
    dp.add_handler(admin_conv)
    
    # -------------------------
    # Notificación de arranque al Administrador de Plataforma
    # -------------------------
    try:
        updater.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text="Bot iniciado correctamente."
        )
    except Exception as e:
        print("Error enviando notificación al Administrador de Plataforma:", e)

    # Iniciar el bot
    updater.start_polling()
    print("[BOOT] Polling iniciado. Bot activo.")
    updater.idle()


if __name__ == "__main__":
    main()
