import os
import hashlib

from dotenv import load_dotenv
load_dotenv()


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

from services import (
    admin_puede_operar,
    calcular_precio_distancia,
    get_pricing_config,
    get_buy_pricing_config,
    calc_buy_products_surcharge,
    quote_order,
    quote_order_by_addresses,
    quote_order_by_coords,
    extract_lat_lng_from_text,
    expand_short_url,
    can_call_google_today,
    extract_place_id_from_url,
    google_place_details,
)
from db import (
    init_db,
    force_platform_admin,
    ensure_pricing_defaults,
    ensure_user,
    get_user_by_telegram_id,
    get_user_by_id,
    get_admin_rejection_type_by_id,
    get_ally_rejection_type_by_id,
    get_courier_rejection_type_by_id,
    get_setting,
    set_setting,
    get_available_admin_teams,
    get_platform_admin_id,
    upsert_admin_ally_link,
    create_admin_courier_link,
    get_local_admins_count,

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
    get_admin_by_telegram_id,
    get_all_admins,
    get_pending_admins,
    get_admin_by_id,
    update_admin_status_by_id,
    count_admin_couriers,
    count_admin_couriers_with_min_balance,
    get_admin_by_team_code,
    update_admin_courier_status,

    # Direcciones aliados
    create_ally_location,
    get_ally_locations,
    get_ally_location_by_id,
    get_default_ally_location,
    set_default_ally_location,
    update_ally_location,
    update_ally_location_coords,
    delete_ally_location,
    increment_pickup_usage,
    set_frequent_pickup,

    # Repartidores
    create_courier,
    get_courier_by_user_id,
    get_courier_by_id,
    get_pending_couriers,
    update_courier_status,
    get_all_couriers,
    update_courier,
    delete_courier,
    get_admin_link_for_courier,
    get_admin_link_for_ally,

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

    # Términos y condiciones
    get_active_terms_version,
    has_accepted_terms,
    save_terms_acceptance,
    save_terms_session_ack,

    # Clientes recurrentes de aliados
    create_ally_customer,
    update_ally_customer,
    archive_ally_customer,
    restore_ally_customer,
    get_ally_customer_by_id,
    list_ally_customers,
    search_ally_customers,
    create_customer_address,
    update_customer_address,
    archive_customer_address,
    restore_customer_address,
    get_customer_address_by_id,
    list_customer_addresses,
    get_last_order_by_ally,

    # Cache de links de ubicación
    get_link_cache,
    upsert_link_cache,
)

# ============================================================
# SEPARACIÓN DEV/PROD - Evitar conflicto getUpdates
# ============================================================
ENV = os.getenv("ENV", "PROD").upper()

# Solo cargar .env en LOCAL (DEV), NUNCA en PROD
if ENV == "LOCAL":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print(f"[ENV] Ambiente: {ENV} - .env cargado")
    except ImportError:
        print(f"[ENV] Ambiente: {ENV} - python-dotenv no instalado, usando variables de sistema")
else:
    print(f"[ENV] Ambiente: {ENV} - usando variables de entorno del sistema (Railway/PROD)")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))  # Administrador de Plataforma

COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

# Constante para equipo de plataforma
PLATFORM_TEAM_CODE = "PLATFORM"


def es_admin(user_id: int) -> bool:
    """Devuelve True si el user_id es el administrador de plataforma."""
    return user_id == ADMIN_USER_ID


def es_admin_plataforma(telegram_id: int) -> bool:
    """
    Valida si el usuario es Administrador de Plataforma.
    Verifica que exista en admins con team_code='PLATFORM' y status='APPROVED'.
    """
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin:
        return False

    # Soportar dict o sqlite3.Row
    if isinstance(admin, dict):
        team_code = admin.get("team_code")
        status = admin.get("status")
    else:
        # sqlite3.Row
        team_code = admin["team_code"] if "team_code" in admin.keys() else None
        status = admin["status"] if "status" in admin.keys() else None

    return team_code == "PLATFORM" and status == "APPROVED"


# =========================
# Estados del registro de aliados
# =========================
ALLY_NAME, ALLY_OWNER, ALLY_ADDRESS, ALLY_CITY, ALLY_PHONE, ALLY_BARRIO, ALLY_UBICACION, ALLY_TEAM = range(8)


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
# Estados para crear un pedido (modificado para cliente recurrente)
# =========================
(
    PEDIDO_SELECTOR_CLIENTE,      # Selector cliente recurrente/nuevo
    PEDIDO_BUSCAR_CLIENTE,        # Buscar cliente por nombre/telefono
    PEDIDO_SELECCIONAR_DIRECCION, # Seleccionar direccion del cliente
    PEDIDO_TIPO_SERVICIO,
    PEDIDO_NOMBRE,
    PEDIDO_TELEFONO,
    PEDIDO_UBICACION,             # Capturar ubicacion (link/coords) opcional
    PEDIDO_DIRECCION,
    PEDIDO_PICKUP_SELECTOR,       # Selector de punto de recogida
    PEDIDO_PICKUP_LISTA,          # Lista de pickups guardados
    PEDIDO_PICKUP_NUEVA_UBICACION,# Capturar coords de nueva direccion
    PEDIDO_PICKUP_NUEVA_DETALLES, # Capturar detalles de nueva direccion
    PEDIDO_PICKUP_GUARDAR,        # Preguntar si guardar nueva direccion
    PEDIDO_REQUIERE_BASE,         # Preguntar si requiere base
    PEDIDO_VALOR_BASE,            # Capturar valor de base
    PEDIDO_CONFIRMACION,
    PEDIDO_GUARDAR_CLIENTE,       # Preguntar si guardar cliente nuevo
    PEDIDO_COMPRAS_CANTIDAD,      # Capturar cantidad de productos
) = range(14, 32)


# =========================
# Estados para /clientes (agenda de clientes recurrentes)
# =========================
(
    CLIENTES_MENU,
    CLIENTES_NUEVO_NOMBRE,
    CLIENTES_NUEVO_TELEFONO,
    CLIENTES_NUEVO_NOTAS,
    CLIENTES_NUEVO_DIRECCION_LABEL,
    CLIENTES_NUEVO_DIRECCION_TEXT,
    CLIENTES_BUSCAR,
    CLIENTES_VER_CLIENTE,
    CLIENTES_EDITAR_NOMBRE,
    CLIENTES_EDITAR_TELEFONO,
    CLIENTES_EDITAR_NOTAS,
    CLIENTES_DIR_NUEVA_LABEL,
    CLIENTES_DIR_NUEVA_TEXT,
    CLIENTES_DIR_EDITAR_LABEL,
    CLIENTES_DIR_EDITAR_TEXT,
) = range(400, 415)


# =========================
# Estados para cotizador interno
# =========================
COTIZAR_DISTANCIA = 901


# =========================
# Estados para configuración de tarifas (Admin Plataforma)
# =========================
TARIFAS_VALOR = 902

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
    except Exception as e:
        print("ERROR get_admin_by_user_id en /start:", e)
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
            team_code = admin_local.get("team_code") or "-"
        else:
            # id, user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number, team_code
            admin_status = admin_local[6]
            team_name = admin_local[8] or "-"
            team_code = admin_local[10] if len(admin_local) > 10 and admin_local[10] else "-"

        estado_lineas.append(f"• Administrador Local: equipo {team_name} (estado: {admin_status}).")

        # Administrador de Plataforma: no mostrar requisitos
        if team_code == "PLATFORM":
            if admin_status == "APPROVED":
                siguientes_pasos.append("• Como Administrador de Plataforma, tu operación está habilitada.")
                siguientes_pasos.append("• Usa /mi_admin para acceder a tu panel.")
            elif admin_status == "PENDING":
                siguientes_pasos.append("• Tu registro de administrador está pendiente de aprobación.")
            elif admin_status == "INACTIVE":
                siguientes_pasos.append("• Tu cuenta de administrador está INACTIVA. Contacta al Administrador de Plataforma.")
            elif admin_status == "REJECTED":
                siguientes_pasos.append("• Tu registro de administrador fue RECHAZADO. Contacta al Administrador de Plataforma.")
        else:
            # Administrador Local normal: mostrar requisitos
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

    # Construir menú según roles del usuario
    comandos = []

    # Comandos principales (para todos)
    comandos.append("• /menu  - Ver este menú")
    comandos.append("• /mi_perfil  - Ver tu perfil consolidado")
    comandos.append("• /cotizar  - Cotizar por distancia")

    # Nuevo pedido y clientes (solo aliados aprobados)
    if ally and ally["status"] == "APPROVED":
        comandos.append("• /nuevo_pedido  - Crear nuevo pedido")
        comandos.append("• /clientes  - Agenda de clientes recurrentes")

    # Admin (segun tipo, evitar duplicados)
    if es_admin_plataforma:
        comandos.append("• /admin  - Panel de administración de plataforma")
        comandos.append("• /tarifas  - Configurar tarifas")
    elif admin_local:
        comandos.append("• /mi_admin  - Ver tu panel de administrador local")

    # Registro (solo si NO tiene ningún rol)
    if not (ally or courier or admin_local or es_admin_plataforma):
        comandos.append("")
        comandos.append("Registro:")
        comandos.append("• /soy_aliado  - Registrar tu negocio")
        comandos.append("• /soy_repartidor  - Registrarte como repartidor")
        comandos.append("• /soy_administrador  - Registrarte como administrador")

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

    # Mostrar ReplyKeyboard SOLO para usuarios nuevos (sin roles)
    if not estado_lineas and not context.user_data.get('keyboard_shown'):
        keyboard = [
            ['/soy_aliado', '/soy_repartidor'],
            ['/soy_admin', '/menu']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        context.user_data['keyboard_shown'] = True
        update.message.reply_text(mensaje, reply_markup=reply_markup)
    else:
        update.message.reply_text(mensaje)


def menu(update, context):
    """Alias de /start para mostrar el menú principal."""
    return start(update, context)


# ---------- MENÚS PERSISTENTES ----------

def get_main_menu_keyboard():
    """Retorna el teclado principal para usuarios fuera de flujos."""
    keyboard = [
        ['Nuevo pedido', 'Mis pedidos'],
        ['Mi perfil', 'Ayuda'],
        ['Menu']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_flow_menu_keyboard():
    """Retorna el teclado reducido para usuarios dentro de flujos."""
    keyboard = [
        ['Cancelar', 'Volver al menu']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def _get_chat_id(update):
    """Extrae chat_id de forma robusta desde update."""
    if getattr(update, "callback_query", None) and update.callback_query.message:
        return update.callback_query.message.chat_id
    if getattr(update, "message", None):
        return update.message.chat_id
    return None


def show_main_menu(update, context, text="Menu principal. Selecciona una opcion:"):
    """Muestra el menú principal completo."""
    reply_markup = get_main_menu_keyboard()
    chat_id = _get_chat_id(update)
    if chat_id:
        context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def show_flow_menu(update, context, text):
    """Muestra el menú reducido para flujos activos."""
    reply_markup = get_flow_menu_keyboard()
    chat_id = _get_chat_id(update)
    if chat_id and text:
        context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def cmd_id(update, context):
    """Muestra el user_id de Telegram del usuario."""
    user = update.effective_user
    update.message.reply_text(f"Tu user_id es: {user.id}")


def menu_button_handler(update, context):
    """Maneja los botones del menú principal (ReplyKeyboard)."""
    text = update.message.text.strip()

    if text == "Mis pedidos":
        update.message.reply_text("Funcion 'Mis pedidos' en desarrollo.")
        return
    elif text == "Mi perfil":
        return mi_perfil(update, context)
    elif text == "Ayuda":
        update.message.reply_text(
            "AYUDA\n\n"
            "Comandos disponibles:\n"
            "/nuevo_pedido - Crear un nuevo pedido\n"
            "/clientes - Gestionar clientes\n"
            "/cotizar - Cotizar envio por distancia\n"
            "/mi_perfil - Ver tu perfil\n"
            "/cancel - Cancelar proceso actual\n"
            "/menu - Ver menu principal"
        )
        return
    elif text == "Menu":
        return start(update, context)


# ----- REGISTRO DE ALIADO -----

def soy_aliado(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    # Validación anti-duplicados
    existing = get_ally_by_user_id(user_db_id)
    if existing:
        status = existing["status"] if isinstance(existing, dict) else existing[8]
        ally_id = existing["id"] if isinstance(existing, dict) else existing[0]

        # Obtener rejection_type usando función específica
        rejection_type = get_ally_rejection_type_by_id(ally_id)

        # Bloquear si PENDING o APPROVED
        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de aliado en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de aliado aprobado (APPROVED). Si necesitas cambios, contacta al administrador."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        # Bloquear si REJECTED + BLOCKED
        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        # Permitir si INACTIVE o REJECTED CORRECTABLE/NULL (continuar)

    update.message.reply_text(
        "Registro de aliado\n\n"
        "Escribe el nombre del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    return ALLY_NAME


def ally_name(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "El nombre del negocio no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_NAME

    context.user_data.clear()
    context.user_data["business_name"] = texto
    update.message.reply_text(
        "Escribe el nombre del dueño o administrador:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return ALLY_OWNER


def ally_owner(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "El nombre del dueño no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_OWNER

    context.user_data["owner_name"] = texto
    update.message.reply_text(
        "Escribe la dirección del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return ALLY_ADDRESS


def ally_address(update, context):
    texto = update.message.text.strip()
    context.user_data["address"] = texto
    update.message.reply_text(
        "Escribe la ciudad del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return ALLY_CITY


def ally_city(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "La ciudad del negocio no puede estar vacía. Escríbela de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_CITY

    context.user_data["city"] = texto
    update.message.reply_text(
        "Escribe el teléfono de contacto del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return ALLY_PHONE


def ally_phone(update, context):
    phone = (update.message.text or "").strip()

    # Validación mínima: que tenga al menos 7 dígitos
    digits = "".join([c for c in phone if c.isdigit()])
    if len(digits) < 7:
        update.message.reply_text(
            "Ese teléfono no parece válido. Escríbelo de nuevo, por favor."
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_PHONE

    # Guardamos en el contexto con el mismo término que acordamos: ally_phone
    context.user_data["ally_phone"] = phone

    # Siguiente paso
    update.message.reply_text(
        "Escribe el barrio del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return ALLY_BARRIO


def ally_barrio(update, context):
    text = (update.message.text or "").strip()
    if not text:
        update.message.reply_text(
            "El barrio no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_BARRIO

    context.user_data["barrio"] = text

    # Preguntar por ubicación (opcional)
    keyboard = [[InlineKeyboardButton("Omitir ubicacion", callback_data="ally_ubicacion_skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "UBICACION DEL NEGOCIO (opcional)\n\n"
        "Pega el enlace de ubicacion (WhatsApp/Google Maps) "
        "o coordenadas lat,lng.\n\n"
        "Si no tienes, toca Omitir.",
        reply_markup=reply_markup
    )
    return ALLY_UBICACION


def ally_ubicacion_handler(update, context):
    """Maneja texto de ubicación del aliado (link o coords)."""
    texto = update.message.text.strip()

    # Intentar extraer coordenadas
    coords = extract_lat_lng_from_text(texto)
    if coords:
        context.user_data["ally_lat"] = coords[0]
        context.user_data["ally_lng"] = coords[1]
        update.message.reply_text("Ubicacion guardada. Continuando registro...")
    else:
        update.message.reply_text(
            "No se pudo extraer la ubicacion del texto.\n"
            "Continuando sin ubicacion exacta..."
        )

    return finalizar_registro_ally(update, context)


def ally_ubicacion_skip_callback(update, context):
    """Omite la ubicación del aliado."""
    query = update.callback_query
    query.answer()
    query.edit_message_text("Continuando sin ubicacion exacta...")
    return finalizar_registro_ally(query, context, from_callback=True)


def finalizar_registro_ally(update_or_query, context, from_callback=False):
    """Finaliza el registro del aliado creando en BD."""
    if from_callback:
        user_tg = update_or_query.message.chat
        chat_id = update_or_query.message.chat_id
    else:
        user_tg = update_or_query.effective_user
        chat_id = update_or_query.message.chat_id

    user_row = get_user_by_telegram_id(user_tg.id if hasattr(user_tg, 'id') else chat_id)
    if not user_row:
        user_row = ensure_user(user_tg.id if hasattr(user_tg, 'id') else chat_id, None)
    user_db_id = user_row["id"]

    business_name = context.user_data.get("business_name", "").strip()
    owner_name = context.user_data.get("owner_name", "").strip()
    address = context.user_data.get("address", "").strip()
    city = context.user_data.get("city", "").strip()
    phone = context.user_data.get("ally_phone", "").strip()
    barrio = context.user_data.get("barrio", "").strip()
    ally_lat = context.user_data.get("ally_lat")
    ally_lng = context.user_data.get("ally_lng")

    try:
        ally_id = create_ally(
            user_id=user_db_id,
            business_name=business_name,
            owner_name=owner_name,
            address=address,
            city=city,
            barrio=barrio,
            phone=phone,
        )

        context.user_data["ally_id"] = ally_id

        location_id = create_ally_location(
            ally_id=ally_id,
            label="Principal",
            address=address,
            city=city,
            barrio=barrio,
            phone=None,
            is_default=True,
        )

        # Guardar coords si existen
        if ally_lat and ally_lng and location_id:
            update_ally_location_coords(location_id, ally_lat, ally_lng)

        # Notificación al Admin de Plataforma (opcional)
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

        return show_ally_team_selection(update_or_query, context, from_callback)

    except Exception as e:
        print(f"[ERROR] Error al crear aliado: {e}")
        if from_callback:
            context.bot.send_message(chat_id=chat_id, text="Error técnico al guardar tu registro. Intenta más tarde.")
        else:
            update_or_query.message.reply_text("Error técnico al guardar tu registro. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END


def show_ally_team_selection(update_or_query, context, from_callback=False):
    """
    Muestra lista de equipos (admins disponibles) y opción Ninguno.
    Si elige Ninguno, se asigna al Admin de Plataforma (TEAM_CODE de plataforma).
    """
    ally_id = context.user_data.get("ally_id")
    if not ally_id:
        if from_callback:
            context.bot.send_message(
                chat_id=update_or_query.message.chat_id,
                text="Error técnico: no encuentro el ID del aliado. Intenta /soy_aliado de nuevo."
            )
        else:
            update_or_query.message.reply_text("Error técnico: no encuentro el ID del aliado. Intenta /soy_aliado de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    teams = get_available_admin_teams()  # db.py
    keyboard = []

    # Botones por equipo disponible
    if teams:
        for row in teams:
            # row puede venir como sqlite3.Row o tupla
            admin_id = row[0]
            team_name = row[1]
            team_code = row[2]
            admin_status = row[3] if len(row) > 3 else 'APPROVED'

            # FASE 1: Mostrar estado si es PENDING
            label = f"{team_name} ({team_code})"
            if admin_status == 'PENDING':
                label += " [Pendiente]"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"ally_team:{team_code}")])

    # Opción Ninguno (default plataforma)
    keyboard.append([InlineKeyboardButton("Ninguno (Admin de Plataforma)", callback_data="ally_team:NONE")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = (
        "A que equipo (Administrador) quieres pertenecer?\n"
        "Si eliges Ninguno, quedas por defecto con el Admin de Plataforma y recargas con el."
    )

    if from_callback:
        context.bot.send_message(
            chat_id=update_or_query.message.chat_id,
            text=texto,
            reply_markup=reply_markup
        )
    else:
        update_or_query.message.reply_text(texto, reply_markup=reply_markup)

    return ALLY_TEAM


def ally_team_callback(update, context):
    query = update.callback_query
    data = (query.data or "").strip()
    print(f"[DEBUG] ally_team_callback recibió data={data}")
    query.answer()

    # Validación básica
    if not data.startswith("ally_team:"):
        return ALLY_TEAM

    ally_id = context.user_data.get("ally_id")
    if not ally_id:
        query.edit_message_text("Error técnico: no encuentro el ID del aliado. Intenta /soy_aliado de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    selected = data.split("ally_team:", 1)[1].strip()

    # 1) Si selecciona NONE → asignar a Admin de Plataforma
    if selected.upper() == "NONE":
        platform_admin = get_admin_by_team_code(PLATFORM_TEAM_CODE)
        if not platform_admin:
            query.edit_message_text(
                "En este momento no existe el equipo del Admin de Plataforma (TEAM_CODE: PLATFORM).\n"
                "Crea/asegura ese admin en la tabla admins con team_code='PLATFORM' y status='APPROVED', luego intenta de nuevo."
            )
            context.user_data.clear()
            return ConversationHandler.END

        platform_admin_id = platform_admin[0]

        try:
            upsert_admin_ally_link(platform_admin_id, ally_id, status="PENDING")
            print(f"[DEBUG] ally_team_callback: vínculo creado ally_id={ally_id}, admin_id={platform_admin_id}, team=PLATFORM")
        except Exception as e:
            print(f"[ERROR] ally_team_callback: upsert_admin_ally_link falló: {e}")
            query.edit_message_text(
                "Error técnico al vincular con el equipo. Intenta /soy_aliado de nuevo."
            )
            context.user_data.clear()
            return ConversationHandler.END

        query.edit_message_text(
            "Listo. Quedaste asignado por defecto al Admin de Plataforma.\n"
            "Tu vínculo quedó en estado PENDING hasta aprobación."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # 2) Si selecciona un TEAM_CODE real
    admin_row = get_admin_by_team_code(selected)
    if not admin_row:
        query.edit_message_text(
            "Ese TEAM_CODE no existe o no está disponible.\n"
            "Vuelve a intentar /soy_aliado."
        )
        context.user_data.clear()
        return ConversationHandler.END

    admin_id = admin_row[0]
    team_name = admin_row[4]  # según tu función: COALESCE(team_name, full_name) AS team_name
    team_code = admin_row[5]

    try:
        upsert_admin_ally_link(admin_id, ally_id, status="PENDING")
        print(f"[DEBUG] ally_team_callback: vínculo creado ally_id={ally_id}, admin_id={admin_id}, team={team_code}")
    except Exception as e:
        print(f"[ERROR] ally_team_callback: upsert_admin_ally_link falló: {e}")
        query.edit_message_text(
            "Error técnico al vincular con el equipo. Intenta /soy_aliado de nuevo."
        )
        context.user_data.clear()
        return ConversationHandler.END

    query.edit_message_text(
        "Listo. Elegiste el equipo:\n"
        f"{team_name} ({team_code})\n\n"
        "Tu vínculo quedó en estado PENDING hasta aprobación."
    )
    context.user_data.clear()
    return ConversationHandler.END



# ----- REGISTRO DE REPARTIDOR -----

def soy_repartidor(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    # Validación anti-duplicados
    existing = get_courier_by_user_id(user_db_id)
    if existing:
        status = existing["status"] if isinstance(existing, dict) else existing[11]
        courier_id = existing["id"] if isinstance(existing, dict) else existing[0]

        # Obtener rejection_type usando función específica
        rejection_type = get_courier_rejection_type_by_id(courier_id)

        # Bloquear si PENDING o APPROVED
        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de repartidor en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de repartidor aprobado (APPROVED). Si necesitas cambios, contacta al administrador."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        # Bloquear si REJECTED + BLOCKED
        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        # Permitir si INACTIVE o REJECTED CORRECTABLE/NULL (continuar)

    update.message.reply_text(
        "Registro de repartidor\n\n"
        "Escribe tu nombre completo:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    return COURIER_FULLNAME


def courier_fullname(update, context):
    context.user_data["full_name"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe tu número de identificación:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return COURIER_IDNUMBER


def courier_idnumber(update, context):
    context.user_data["id_number"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe tu número de celular:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return COURIER_PHONE


def courier_phone(update, context):
    context.user_data["phone"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe la ciudad donde trabajas:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return COURIER_CITY


def courier_city(update, context):
    context.user_data["city"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el barrio o sector principal donde trabajas:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return COURIER_BARRIO


def courier_barrio(update, context):
    context.user_data["barrio"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe la placa de tu moto (o escribe 'ninguna' si no tienes):"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    return COURIER_PLATE


def courier_plate(update, context):
    context.user_data["plate"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el tipo de moto (Ejemplo: Bóxer 100, FZ, scooter, bicicleta, etc.):"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
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
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
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

    if text in ("NO", "N", "NO.", "N.", "NINGUNO", ""):
        # FASE 1: Asignar a Admin de Plataforma por defecto
        platform_admin = get_admin_by_team_code(PLATFORM_TEAM_CODE)
        if not platform_admin:
            update.message.reply_text(
                "En este momento no existe el equipo del Admin de Plataforma (TEAM_CODE: PLATFORM).\n"
                "Crea/asegura ese admin en la tabla admins con team_code='PLATFORM', luego intenta de nuevo."
            )
            context.user_data.clear()
            return ConversationHandler.END

        platform_admin_id = platform_admin[0]

        try:
            create_admin_courier_link(platform_admin_id, courier_id)
            print(f"[DEBUG] courier_teamcode: vínculo creado courier_id={courier_id}, admin_id={platform_admin_id}, team=PLATFORM")
        except Exception as e:
            print(f"[ERROR] courier_teamcode: create_admin_courier_link falló: {e}")
            update.message.reply_text("Error técnico al vincular con el equipo. Intenta /soy_repartidor de nuevo.")
            context.user_data.clear()
            return ConversationHandler.END

        update.message.reply_text(
            "Perfecto. Quedas registrado en el equipo de PLATAFORMA.\n\n"
            "Cuando tengas un código TEAM, podrás pedir cambio más adelante."
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

    # get_admin_by_team_code retorna:
    # (admin_id, user_id, full_name, status, team_name, team_code, telegram_id)
    admin_id = admin[0]
    admin_user_db_id = admin[1]  # users.id (NO telegram_id)
    admin_name = admin[2]
    admin_status = admin[3]
    admin_team = admin[4]
    admin_team_code = admin[5]
    admin_telegram_id = admin[6]  # telegram_id REAL para notificaciones

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
        update.message.reply_text("Aun no estas registrado en el sistema. Usa /start primero.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text(
            "Aun no estas registrado como aliado.\n"
            "Si tienes un negocio, registrate con /soy_aliado."
        )
        return ConversationHandler.END

    if ally["status"] != "APPROVED":
        update.message.reply_text(
            "Tu registro como aliado todavia no ha sido aprobado por el administrador.\n"
            "Cuando tu estado sea APPROVED podras crear pedidos con /nuevo_pedido."
        )
        return ConversationHandler.END

    # Si tienes ensure_terms implementado y quieres exigirlo, dejalo.
    # Si NO lo tienes, comenta estas 2 lineas.
    if not ensure_terms(update, context, user.id, role="ALLY"):
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["ally_id"] = ally["id"]
    context.user_data["ally"] = ally

    # Mostrar menú reducido de flujo
    show_flow_menu(update, context, "Iniciando nuevo pedido...")

    # Mostrar selector de cliente recurrente/nuevo
    keyboard = [
        [InlineKeyboardButton("Cliente recurrente", callback_data="pedido_cliente_recurrente")],
        [InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")],
    ]

    # Verificar si hay ultimo pedido para ofrecer repetir
    last_order = get_last_order_by_ally(ally["id"])
    if last_order:
        keyboard.append([InlineKeyboardButton("Repetir ultimo pedido", callback_data="pedido_repetir_ultimo")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "CREAR NUEVO PEDIDO\n\n"
        "Selecciona una opcion:",
        reply_markup=reply_markup
    )
    return PEDIDO_SELECTOR_CLIENTE


def pedido_selector_cliente_callback(update, context):
    """Maneja la seleccion de tipo de cliente en /nuevo_pedido."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally_id = context.user_data.get("ally_id")
    if not ally_id:
        query.edit_message_text("Error: sesion expirada. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END

    if data == "pedido_cliente_recurrente":
        # Mostrar lista de clientes recurrentes
        customers = list_ally_customers(ally_id, limit=10)
        if not customers:
            query.edit_message_text(
                "No tienes clientes guardados.\n\n"
                "Escribe el nombre del cliente para crear el pedido:"
            )
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE

        keyboard = []
        for c in customers:
            btn_text = f"{c['name']} - {c['phone']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_cust_{c['id']}")])

        keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="pedido_buscar_cliente")])
        keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "CLIENTES RECURRENTES\n\n"
            "Selecciona un cliente:",
            reply_markup=reply_markup
        )
        return PEDIDO_SELECTOR_CLIENTE

    elif data == "pedido_cliente_nuevo":
        query.edit_message_text("Escribe el nombre del cliente:")
        context.user_data["is_new_customer"] = True
        return PEDIDO_NOMBRE

    elif data == "pedido_repetir_ultimo":
        ally_id = context.user_data.get("ally_id")
        last_order = get_last_order_by_ally(ally_id)
        if last_order:
            context.user_data["customer_name"] = last_order["customer_name"]
            context.user_data["customer_phone"] = last_order["customer_phone"]
            context.user_data["customer_address"] = last_order["customer_address"]
            context.user_data["is_new_customer"] = False

            # Ir al selector de pickup
            return mostrar_selector_pickup(query, context, edit=True)
        else:
            query.edit_message_text("No hay pedidos anteriores. Escribe el nombre del cliente:")
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE

    elif data == "pedido_buscar_cliente":
        query.edit_message_text("Escribe el nombre o telefono del cliente a buscar:")
        return PEDIDO_BUSCAR_CLIENTE

    elif data.startswith("pedido_sel_cust_"):
        # Selecciono un cliente recurrente
        customer_id = int(data.replace("pedido_sel_cust_", ""))
        customer = get_ally_customer_by_id(customer_id, ally_id)
        if not customer:
            query.edit_message_text("Cliente no encontrado. Escribe el nombre del cliente:")
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE

        context.user_data["customer_id"] = customer_id
        context.user_data["customer_name"] = customer["name"]
        context.user_data["customer_phone"] = customer["phone"]
        context.user_data["is_new_customer"] = False

        # Mostrar direcciones del cliente
        addresses = list_customer_addresses(customer_id)
        if not addresses:
            query.edit_message_text(
                f"Cliente: {customer['name']}\n"
                f"Telefono: {customer['phone']}\n\n"
                "Este cliente no tiene direcciones guardadas.\n"
                "Escribe la direccion de entrega:"
            )
            return PEDIDO_DIRECCION

        keyboard = []
        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            btn_text = f"{label}: {addr['address_text'][:30]}..."
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_addr_{addr['id']}")])

        keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="pedido_nueva_dir")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"Cliente: {customer['name']}\n"
            f"Telefono: {customer['phone']}\n\n"
            "Selecciona la direccion de entrega:",
            reply_markup=reply_markup
        )
        return PEDIDO_SELECCIONAR_DIRECCION

    return PEDIDO_SELECTOR_CLIENTE


def pedido_buscar_cliente(update, context):
    """Busca clientes por nombre o telefono."""
    query_text = update.message.text.strip()
    ally_id = context.user_data.get("ally_id")

    if not ally_id:
        update.message.reply_text("Error: sesion expirada. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END

    results = search_ally_customers(ally_id, query_text, limit=10)
    if not results:
        update.message.reply_text(
            f"No se encontraron clientes con '{query_text}'.\n\n"
            "Escribe el nombre del cliente para crear el pedido:"
        )
        context.user_data["is_new_customer"] = True
        return PEDIDO_NOMBRE

    keyboard = []
    for c in results:
        btn_text = f"{c['name']} - {c['phone']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_cust_{c['id']}")])

    keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"Resultados para '{query_text}':\n\n"
        "Selecciona un cliente:",
        reply_markup=reply_markup
    )
    return PEDIDO_SELECTOR_CLIENTE


def pedido_seleccionar_direccion_callback(update, context):
    """Maneja la seleccion de direccion del cliente."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pedido_nueva_dir":
        query.edit_message_text("Escribe la nueva direccion de entrega:")
        return PEDIDO_DIRECCION

    elif data == "guardar_dir_cliente_si":
        # Guardar la direccion del cliente
        customer_id = context.user_data.get("customer_id")
        address_text = context.user_data.get("customer_address", "")
        lat = context.user_data.get("dropoff_lat")
        lng = context.user_data.get("dropoff_lng")
        if customer_id and address_text:
            create_customer_address(
                customer_id=customer_id,
                label=address_text[:30],
                address_text=address_text,
                lat=lat,
                lng=lng
            )
            query.edit_message_text("Direccion guardada.")
        else:
            query.edit_message_text("OK, continuamos.")
        return mostrar_selector_pickup(query, context, edit=False)

    elif data == "guardar_dir_cliente_no":
        query.edit_message_text("OK, usaremos esta direccion solo esta vez.")
        return mostrar_selector_pickup(query, context, edit=False)

    elif data.startswith("pedido_sel_addr_"):
        address_id = int(data.replace("pedido_sel_addr_", ""))
        customer_id = context.user_data.get("customer_id")
        address = get_customer_address_by_id(address_id, customer_id)

        if not address:
            query.edit_message_text("Direccion no encontrada. Escribe la direccion de entrega:")
            return PEDIDO_DIRECCION

        context.user_data["customer_address"] = address["address_text"]
        context.user_data["customer_city"] = address["city"] or ""
        context.user_data["customer_barrio"] = address["barrio"] or ""
        context.user_data["dropoff_lat"] = address.get("lat")
        context.user_data["dropoff_lng"] = address.get("lng")

        # Mostrar selector de punto de recogida
        return mostrar_selector_pickup(query, context, edit=True)

    return PEDIDO_SELECCIONAR_DIRECCION


def get_tipo_servicio_keyboard():
    """Retorna InlineKeyboardMarkup con opciones de tipo de servicio."""
    keyboard = [
        [InlineKeyboardButton("Entrega rapida (30-45 min)", callback_data="pedido_tipo_entrega_rapida")],
        [InlineKeyboardButton("Domicilio", callback_data="pedido_tipo_domicilio")],
        [InlineKeyboardButton("Mensajeria", callback_data="pedido_tipo_mensajeria")],
        [InlineKeyboardButton("Recogida en tienda", callback_data="pedido_tipo_recogida")],
        [InlineKeyboardButton("🛒 Compras", callback_data="pedido_tipo_compras")],
    ]
    return InlineKeyboardMarkup(keyboard)


def mostrar_selector_tipo_servicio(query_or_update, context, edit=False, texto_intro=None):
    """Muestra selector de tipo de servicio con botones.

    Args:
        query_or_update: CallbackQuery o Update
        context: Context del bot
        edit: Si True, edita el mensaje existente
        texto_intro: Texto introductorio opcional (ej: info del cliente)
    """
    reply_markup = get_tipo_servicio_keyboard()

    if texto_intro:
        texto = f"{texto_intro}\n\nSelecciona el tipo de servicio:"
    else:
        texto = "TIPO DE SERVICIO\n\nSelecciona una opcion:"

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(texto, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)

    return PEDIDO_TIPO_SERVICIO


def pedido_tipo_servicio_callback(update, context):
    """Maneja la seleccion de tipo de servicio por boton."""
    query = update.callback_query
    query.answer()
    data = query.data

    # Mapeo de callbacks a texto legible
    tipos_map = {
        "pedido_tipo_entrega_rapida": "Entrega rapida (30-45 min)",
        "pedido_tipo_domicilio": "Domicilio",
        "pedido_tipo_mensajeria": "Mensajeria",
        "pedido_tipo_recogida": "Recogida en tienda",
        "pedido_tipo_compras": "Compras",
    }

    if data not in tipos_map:
        query.edit_message_text("Opcion no valida. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END

    context.user_data["service_type"] = tipos_map[data]

    # Si es Compras, pedir cantidad de productos
    if data == "pedido_tipo_compras":
        query.edit_message_text(
            "🛒 COMPRAS\n\n"
            "Cuantos productos son en total?\n\n"
            "(Cada 3 unidades de un producto = 1 producto.\n"
            "Unidades adicionales cuentan como producto extra)"
        )
        return PEDIDO_COMPRAS_CANTIDAD

    # Verificar si ya tenemos todos los datos del cliente
    has_name = context.user_data.get("customer_name")
    has_phone = context.user_data.get("customer_phone")
    has_address = context.user_data.get("customer_address")

    if has_name and has_phone and has_address:
        # Ya tenemos datos del cliente, preguntar por base requerida
        return mostrar_pregunta_base(query, context, edit=True)
    else:
        # Cliente nuevo: pedir nombre
        query.edit_message_text(
            f"Tipo de servicio: {tipos_map[data]}\n\n"
            "Ahora escribe el nombre del cliente:"
        )
        return PEDIDO_NOMBRE


def pedido_compras_cantidad_handler(update, context):
    """Captura la cantidad de productos para Compras."""
    texto = update.message.text.strip()

    try:
        cantidad = int(texto)
        if cantidad <= 0:
            update.message.reply_text(
                "Cantidad invalida. Escribe un numero mayor a 0:"
            )
            return PEDIDO_COMPRAS_CANTIDAD
        if cantidad > 50:
            update.message.reply_text(
                "Maximo 50 productos. Escribe una cantidad valida:"
            )
            return PEDIDO_COMPRAS_CANTIDAD
    except ValueError:
        update.message.reply_text(
            "Valor invalido. Escribe un numero entero:"
        )
        return PEDIDO_COMPRAS_CANTIDAD

    context.user_data["buy_products_count"] = cantidad

    # Continuar con el flujo normal
    has_name = context.user_data.get("customer_name")
    has_phone = context.user_data.get("customer_phone")
    has_address = context.user_data.get("customer_address")

    if has_name and has_phone and has_address:
        return mostrar_pregunta_base(update, context, edit=False)
    else:
        update.message.reply_text(
            f"Productos: {cantidad}\n\n"
            "Ahora escribe el nombre del cliente:"
        )
        return PEDIDO_NOMBRE


def mostrar_pregunta_base(query_or_update, context, edit=False):
    """Muestra pregunta de si requiere base."""
    keyboard = [
        [InlineKeyboardButton("Si, requiere base", callback_data="pedido_base_si")],
        [InlineKeyboardButton("No requiere base", callback_data="pedido_base_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    texto = (
        "BASE REQUERIDA\n\n"
        "El repartidor debe pagar/adelantar dinero al recoger el pedido?"
    )

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(texto, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)

    return PEDIDO_REQUIERE_BASE


def pedido_requiere_base_callback(update, context):
    """Maneja la respuesta de si requiere base."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pedido_base_no":
        context.user_data["requires_cash"] = False
        context.user_data["cash_required_amount"] = 0
        # Calcular cotizacion y mostrar confirmacion
        return calcular_cotizacion_y_confirmar(query, context, edit=True)

    elif data == "pedido_base_si":
        context.user_data["requires_cash"] = True
        # Mostrar opciones de monto
        keyboard = [
            [
                InlineKeyboardButton("$5.000", callback_data="pedido_base_5000"),
                InlineKeyboardButton("$10.000", callback_data="pedido_base_10000"),
            ],
            [
                InlineKeyboardButton("$20.000", callback_data="pedido_base_20000"),
                InlineKeyboardButton("$50.000", callback_data="pedido_base_50000"),
            ],
            [InlineKeyboardButton("Otro valor", callback_data="pedido_base_otro")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "VALOR DE BASE\n\n"
            "Cuanto debe adelantar el repartidor?",
            reply_markup=reply_markup
        )
        return PEDIDO_VALOR_BASE

    return PEDIDO_REQUIERE_BASE


def pedido_valor_base_callback(update, context):
    """Maneja la seleccion del valor de base."""
    query = update.callback_query
    query.answer()
    data = query.data

    valores_map = {
        "pedido_base_5000": 5000,
        "pedido_base_10000": 10000,
        "pedido_base_20000": 20000,
        "pedido_base_50000": 50000,
    }

    if data in valores_map:
        context.user_data["cash_required_amount"] = valores_map[data]
        return calcular_cotizacion_y_confirmar(query, context, edit=True)

    elif data == "pedido_base_otro":
        query.edit_message_text(
            "Escribe el valor de la base (solo numeros):"
        )
        return PEDIDO_VALOR_BASE

    return PEDIDO_VALOR_BASE


def pedido_valor_base_texto(update, context):
    """Maneja el valor de base ingresado por texto."""
    texto = update.message.text.strip().replace(".", "").replace(",", "")
    try:
        valor = int(texto)
        if valor <= 0:
            raise ValueError("Valor debe ser mayor a 0")
        context.user_data["cash_required_amount"] = valor
        return calcular_cotizacion_y_confirmar(update, context, edit=False)
    except ValueError:
        update.message.reply_text(
            "Valor invalido. Escribe solo numeros (ej: 15000):"
        )
        return PEDIDO_VALOR_BASE


def mostrar_error_cotizacion(query_or_update, context, mensaje, edit=False):
    """Muestra error de cotizacion con botones Reintentar/Cancelar."""
    keyboard = [
        [InlineKeyboardButton("Reintentar cotizacion", callback_data="pedido_retry_quote")],
        [InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(mensaje, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(mensaje, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(mensaje, reply_markup=reply_markup)

    return PEDIDO_CONFIRMACION


def calcular_cotizacion_y_confirmar(query_or_update, context, edit=False):
    """Calcula distancia via API (preferente por coords) y muestra resumen."""
    ally_id = context.user_data.get("ally_id")
    customer_address = context.user_data.get("customer_address", "")
    customer_city = context.user_data.get("customer_city", "")

    # Obtener coords del cliente (si se capturaron)
    dropoff_lat = context.user_data.get("dropoff_lat")
    dropoff_lng = context.user_data.get("dropoff_lng")

    # Usar pickup seleccionado por el usuario (del selector de pickup)
    pickup_text = context.user_data.get("pickup_address")
    pickup_city = context.user_data.get("pickup_city", "")
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")

    # Si no hay pickup en user_data, usar default del aliado (fallback)
    if not pickup_text and ally_id:
        default_location = get_default_ally_location(ally_id)
        if default_location:
            pickup_text = default_location.get("address")
            pickup_city = default_location.get("city") or ""
            pickup_lat = default_location.get("lat")
            pickup_lng = default_location.get("lng")

    if not pickup_text:
        return mostrar_error_cotizacion(
            query_or_update, context,
            "No tienes una direccion base configurada.\n\n"
            "Configura tu punto de recogida antes de crear pedidos.",
            edit=edit
        )

    # Guardar coords de pickup para el pedido
    context.user_data["pickup_lat"] = pickup_lat
    context.user_data["pickup_lng"] = pickup_lng

    # Intentar cotizar por coordenadas (más preciso)
    cotizacion = None
    if pickup_lat and pickup_lng and dropoff_lat and dropoff_lng:
        cotizacion = quote_order_by_coords(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)

    # Si no hay coords o falló, usar texto como fallback
    if not cotizacion or not cotizacion.get("success"):
        # Determinar ciudad efectiva
        effective_city = pickup_city or "Pereira"
        delivery_city = customer_city or effective_city

        # Construir direcciones completas
        origin = pickup_text
        if effective_city.lower() not in pickup_text.lower():
            origin = f"{pickup_text}, {effective_city}, Colombia"
        elif "colombia" not in pickup_text.lower():
            origin = f"{pickup_text}, Colombia"

        destination = customer_address
        if delivery_city.lower() not in customer_address.lower():
            destination = f"{customer_address}, {delivery_city}, Colombia"
        elif "colombia" not in customer_address.lower():
            destination = f"{customer_address}, Colombia"

        city_hint = f"{effective_city}, Colombia"
        cotizacion = quote_order_by_addresses(origin, destination, city_hint)

    # Verificar si la API fallo
    if not cotizacion["success"]:
        return mostrar_error_cotizacion(
            query_or_update, context,
            "No se pudo calcular la distancia automaticamente.\n\n"
            "Verifica que la API este activa y vuelve a intentar.",
            edit=edit
        )

    # Guardar datos de cotizacion
    context.user_data["quote_distance_km"] = cotizacion["distance_km"]
    base_price = cotizacion["price"]

    # Si es servicio de Compras, calcular recargo por productos
    buy_surcharge = 0
    if context.user_data.get("service_type") == "Compras":
        n_products = context.user_data.get("buy_products_count", 0)
        buy_surcharge = calc_buy_products_surcharge(n_products)
        context.user_data["buy_surcharge"] = buy_surcharge

    context.user_data["quote_price"] = base_price + buy_surcharge
    context.user_data["quote_source"] = cotizacion.get("quote_source", "text")

    # Mostrar resumen con botones de confirmacion
    keyboard = [
        [InlineKeyboardButton("Confirmar pedido", callback_data="pedido_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    # Agregar nota sobre precisión
    if context.user_data.get("quote_source") == "coords":
        resumen += "\n(Cotizacion precisa por ubicacion)"
    else:
        resumen += "\n(Cotizacion estimada por direccion)"

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(resumen, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(resumen, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(resumen, reply_markup=reply_markup)

    return PEDIDO_CONFIRMACION


def pedido_retry_quote_callback(update, context):
    """Reintenta calcular la cotizacion."""
    query = update.callback_query
    query.answer()
    return calcular_cotizacion_y_confirmar(query, context, edit=True)


def pedido_tipo_servicio(update, context):
    """Fallback: redirige a botones si el usuario escribe texto."""
    # Simplemente mostrar botones sin mensaje de error
    return mostrar_selector_tipo_servicio(update, context, edit=False)


def pedido_nombre_cliente(update, context):
    context.user_data["customer_name"] = update.message.text.strip()
    update.message.reply_text("Ahora escribe el numero de telefono del cliente.")
    return PEDIDO_TELEFONO


def pedido_telefono_cliente(update, context):
    context.user_data["customer_phone"] = update.message.text.strip()
    # Preguntar por ubicación (opcional)
    keyboard = [[InlineKeyboardButton("Omitir ubicacion", callback_data="pedido_ubicacion_skip")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "UBICACION (opcional)\n\n"
        "Pega el enlace de ubicacion del cliente (WhatsApp/Google Maps) "
        "o coordenadas lat,lng.\n\n"
        "Si no tienes, toca Omitir.",
        reply_markup=reply_markup
    )
    return PEDIDO_UBICACION


def pedido_ubicacion_handler(update, context):
    """Maneja texto de ubicación (link o coords) con cache + Google place_id only."""
    texto = update.message.text.strip()

    # Normalizar: tomar primer URL si hay varios tokens
    raw_link = texto
    if "http" in texto:
        raw_link = next((t for t in texto.split() if t.startswith("http")), texto)

    # 1) Consultar cache
    cached = get_link_cache(raw_link)
    if cached and cached.get("lat") is not None and cached.get("lng") is not None:
        context.user_data["dropoff_lat"] = cached["lat"]
        context.user_data["dropoff_lng"] = cached["lng"]
        context.user_data["customer_location_link"] = raw_link
        update.message.reply_text(
            "Ubicacion guardada (desde cache).\n\n"
            "Ahora escribe los detalles de la direccion:\n"
            "barrio, conjunto, torre, apto, referencias."
        )
        return PEDIDO_DIRECCION

    # 2) Intentar expandir link corto si aplica
    expanded = expand_short_url(raw_link) or raw_link

    # 3) Extraer coordenadas del texto/URL con regex
    coords = extract_lat_lng_from_text(expanded)
    if coords:
        context.user_data["dropoff_lat"] = coords[0]
        context.user_data["dropoff_lng"] = coords[1]
        context.user_data["customer_location_link"] = raw_link
        upsert_link_cache(raw_link, expanded, coords[0], coords[1], provider="regex")
        update.message.reply_text(
            "Ubicacion guardada.\n\n"
            "Ahora escribe los detalles de la direccion:\n"
            "barrio, conjunto, torre, apto, referencias."
        )
        return PEDIDO_DIRECCION

    # 4) Fallback: Google Places API SOLO si hay place_id en URL
    place_id = extract_place_id_from_url(expanded)
    if place_id and can_call_google_today():
        google_result = google_place_details(place_id)
        if google_result and google_result.get("lat") and google_result.get("lng"):
            context.user_data["dropoff_lat"] = google_result["lat"]
            context.user_data["dropoff_lng"] = google_result["lng"]
            context.user_data["customer_location_link"] = raw_link
            upsert_link_cache(
                raw_link, expanded,
                google_result["lat"], google_result["lng"],
                google_result.get("formatted_address"),
                google_result.get("provider"),
                google_result.get("place_id")
            )
            update.message.reply_text(
                "Ubicacion guardada (via Google).\n\n"
                "Ahora escribe los detalles de la direccion:\n"
                "barrio, conjunto, torre, apto, referencias."
            )
            return PEDIDO_DIRECCION

    # 5) No se pudo resolver
    # Detectar si es un link de maps.app.goo.gl para mensaje UX especial
    es_link_corto_google = "maps.app.goo.gl" in raw_link or "goo.gl/maps" in raw_link

    if es_link_corto_google:
        # UX especial para links de Google Maps sin coordenadas
        keyboard = [[InlineKeyboardButton(
            "📋 Copiar mensaje para enviar al cliente",
            callback_data="ubicacion_copiar_msg_cliente"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "⚠️ Ese enlace no incluye coordenadas exactas.\n\n"
            "👉 Para registrar la dirección rápido, pídele al cliente una de estas opciones (toma 5 segundos):\n"
            "• En WhatsApp: 📎 → Ubicación → Enviar ubicación actual\n"
            "• En Google Maps: tocar el punto azul → Compartir → copiar el link largo\n\n"
            "Mientras tanto, escribe los detalles de la dirección:\n"
            "barrio, conjunto, torre, apto, referencias.",
            reply_markup=reply_markup
        )
    else:
        # Mensaje genérico para otros casos
        update.message.reply_text(
            "No pude extraer coordenadas de ese texto.\n\n"
            "Escribe los detalles de la dirección:\n"
            "barrio, conjunto, torre, apto, referencias.\n\n"
            "(Tip: pega coordenadas lat,lng o pide ubicación por WhatsApp)"
        )
    return PEDIDO_DIRECCION


def pedido_ubicacion_skip_callback(update, context):
    """Omite la ubicación y pide solo dirección de texto."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "Escribe los detalles de la direccion:\n"
        "barrio, conjunto, torre, apto, referencias.\n\n"
        "(La cotizacion sera menos precisa sin ubicacion exacta)"
    )
    return PEDIDO_DIRECCION


def pedido_ubicacion_copiar_msg_callback(update, context):
    """Envía mensaje listo para copiar y enviar al cliente."""
    query = update.callback_query
    query.answer()
    # Enviar mensaje listo para copiar (texto plano)
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "📋 Copia y envía este mensaje al cliente:\n\n"
            "Hola 👋 ¿me puedes enviar tu ubicación por WhatsApp "
            "(📍Enviar ubicación actual) o un link largo de Google Maps? "
            "Es para registrar tu dirección rápido. Gracias 🙏"
        )
    )
    return PEDIDO_UBICACION


def pedido_direccion_cliente(update, context):
    context.user_data["customer_address"] = update.message.text.strip()

    # Si hay cliente existente (recurrente), preguntar si guardar direccion
    customer_id = context.user_data.get("customer_id")
    if customer_id and not context.user_data.get("is_new_customer"):
        keyboard = [
            [InlineKeyboardButton("Si, guardar", callback_data="guardar_dir_cliente_si")],
            [InlineKeyboardButton("No, solo usar esta vez", callback_data="guardar_dir_cliente_no")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Deseas guardar esta direccion para futuros pedidos?",
            reply_markup=reply_markup
        )
        return PEDIDO_SELECCIONAR_DIRECCION

    # Cliente nuevo o sin guardar - continuar al pickup
    return mostrar_selector_pickup(update, context, edit=False)


# ---------- PICKUP SELECTOR (PUNTO DE RECOGIDA) ----------

def mostrar_selector_pickup(query_or_update, context, edit=False):
    """Muestra selector de punto de recogida con botones.

    Args:
        query_or_update: CallbackQuery o Update
        context: Context del bot
        edit: Si True, edita el mensaje existente
    """
    keyboard = [
        [InlineKeyboardButton("Mi direccion base", callback_data="pickup_select_base")],
        [InlineKeyboardButton("Elegir otra", callback_data="pickup_select_lista")],
        [InlineKeyboardButton("Agregar nueva", callback_data="pickup_select_nueva")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = (
        "PUNTO DE RECOGIDA\n\n"
        "Donde se recoge el pedido?"
    )

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(texto, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)

    return PEDIDO_PICKUP_SELECTOR


def pedido_pickup_callback(update, context):
    """Maneja la seleccion del tipo de pickup."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally = context.user_data.get("ally")
    if not ally:
        query.edit_message_text("Error: no se encontro informacion del aliado. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END

    ally_id = ally["id"]

    if data == "pickup_select_base":
        # Usar direccion base del aliado
        default_loc = get_default_ally_location(ally_id)
        if not default_loc:
            query.edit_message_text(
                "No tienes una direccion base configurada.\n"
                "Puedes agregar una nueva o contactar soporte."
            )
            return mostrar_selector_pickup(query, context, edit=False)

        # Guardar pickup en user_data
        context.user_data["pickup_location"] = default_loc
        context.user_data["pickup_label"] = default_loc.get("label") or "Base"
        context.user_data["pickup_address"] = default_loc.get("address", "")
        context.user_data["pickup_city"] = default_loc.get("city", "")
        context.user_data["pickup_lat"] = default_loc.get("lat")
        context.user_data["pickup_lng"] = default_loc.get("lng")

        # Continuar al siguiente paso
        return continuar_despues_pickup(query, context, edit=True)

    elif data == "pickup_select_lista":
        # Mostrar lista de direcciones guardadas
        return mostrar_lista_pickups(query, context)

    elif data == "pickup_select_nueva":
        # Pedir nueva direccion
        query.edit_message_text(
            "NUEVA DIRECCION DE RECOGIDA\n\n"
            "Envia la ubicacion (link de Google Maps o WhatsApp) "
            "o coordenadas (lat,lng).\n\n"
            "Tambien puedes escribir 'omitir' para ingresar solo texto."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    else:
        query.edit_message_text("Opcion no valida. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END


def construir_etiqueta_pickup(loc):
    """Construye etiqueta para un pickup con info de uso."""
    label = loc.get("label") or loc.get("address", "Sin nombre")[:25]
    tags = []

    if loc.get("is_default"):
        tags.append("BASE")
    if loc.get("is_frequent"):
        tags.append("FRECUENTE")
    elif loc.get("use_count", 0) > 0:
        tags.append(f"x{loc['use_count']}")

    if tags:
        return f"{label} ({', '.join(tags)})"
    return label


def mostrar_lista_pickups(query, context):
    """Muestra lista de direcciones guardadas del aliado (max 8)."""
    ally = context.user_data.get("ally")
    if not ally:
        query.edit_message_text("Error: no se encontro informacion del aliado.")
        return ConversationHandler.END

    ally_id = ally["id"]
    locations = get_ally_locations(ally_id)  # Ya ordenadas por prioridad

    if not locations:
        query.edit_message_text(
            "No tienes direcciones guardadas.\n"
            "Agrega una nueva direccion."
        )
        return mostrar_selector_pickup(query, context, edit=False)

    # Construir botones con etiquetas (max 8)
    keyboard = []
    for loc in locations[:8]:
        btn_text = construir_etiqueta_pickup(loc)
        callback = f"pickup_list_loc_{loc['id']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])

    keyboard.append([InlineKeyboardButton("Agregar nueva", callback_data="pickup_list_nueva")])
    keyboard.append([InlineKeyboardButton("Volver", callback_data="pickup_list_volver")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        "ELEGIR PUNTO DE RECOGIDA\n\n"
        "Selecciona una de tus direcciones guardadas:",
        reply_markup=reply_markup
    )
    return PEDIDO_PICKUP_LISTA


def pedido_pickup_lista_callback(update, context):
    """Maneja la seleccion de una direccion de la lista."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pickup_list_volver":
        return mostrar_selector_pickup(query, context, edit=True)

    if data == "pickup_list_nueva":
        query.edit_message_text(
            "NUEVA DIRECCION DE RECOGIDA\n\n"
            "Envia la ubicacion (link de Google Maps o WhatsApp) "
            "o coordenadas (lat,lng).\n\n"
            "Tambien puedes escribir 'omitir' para ingresar solo texto."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    if data == "pickup_list_back":
        return mostrar_lista_pickups(query, context)

    # Manejar marcar/desmarcar frecuente
    if data.startswith("pickup_list_freq_"):
        parts = data.replace("pickup_list_freq_", "").split("_")
        if len(parts) == 2:
            loc_id = int(parts[0])
            new_freq = int(parts[1])
            ally = context.user_data.get("ally")
            if ally:
                set_frequent_pickup(loc_id, ally["id"], new_freq == 1)
                msg = "Marcada como frecuente" if new_freq == 1 else "Desmarcada como frecuente"
                query.answer(msg)
            return mostrar_lista_pickups(query, context)

    # Usar pickup seleccionado
    if data.startswith("pickup_list_usar_"):
        try:
            loc_id = int(data.replace("pickup_list_usar_", ""))
        except ValueError:
            query.edit_message_text("Error: ID invalido.")
            return ConversationHandler.END

        ally = context.user_data.get("ally")
        if not ally:
            query.edit_message_text("Error: no se encontro informacion del aliado.")
            return ConversationHandler.END

        location = get_ally_location_by_id(loc_id, ally["id"])
        if not location:
            query.edit_message_text("Error: direccion no encontrada.")
            return mostrar_selector_pickup(query, context, edit=False)

        # Guardar pickup en user_data
        context.user_data["pickup_location"] = location
        context.user_data["pickup_label"] = location.get("label") or "Recogida"
        context.user_data["pickup_address"] = location.get("address", "")
        context.user_data["pickup_city"] = location.get("city", "")
        context.user_data["pickup_lat"] = location.get("lat")
        context.user_data["pickup_lng"] = location.get("lng")

        return continuar_despues_pickup(query, context, edit=True)

    # Seleccionar pickup - mostrar submenú
    if data.startswith("pickup_list_loc_"):
        try:
            loc_id = int(data.replace("pickup_list_loc_", ""))
        except ValueError:
            query.edit_message_text("Error: ID invalido.")
            return ConversationHandler.END

        ally = context.user_data.get("ally")
        if not ally:
            query.edit_message_text("Error: no se encontro informacion del aliado.")
            return ConversationHandler.END

        location = get_ally_location_by_id(loc_id, ally["id"])
        if not location:
            query.edit_message_text("Error: direccion no encontrada.")
            return mostrar_lista_pickups(query, context)

        # Mostrar submenú para esta pickup
        label = construir_etiqueta_pickup(location)
        is_freq = location.get("is_frequent", 0)

        keyboard = [
            [InlineKeyboardButton("Usar para este pedido", callback_data=f"pickup_list_usar_{loc_id}")],
        ]

        if is_freq:
            keyboard.append([InlineKeyboardButton("Quitar de frecuentes", callback_data=f"pickup_list_freq_{loc_id}_0")])
        else:
            keyboard.append([InlineKeyboardButton("Marcar como frecuente", callback_data=f"pickup_list_freq_{loc_id}_1")])

        keyboard.append([InlineKeyboardButton("Volver a lista", callback_data="pickup_list_back")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"PICKUP SELECCIONADO\n\n"
            f"{label}\n"
            f"Direccion: {location.get('address', '-')}\n"
            f"Usos: {location.get('use_count', 0)}",
            reply_markup=reply_markup
        )
        return PEDIDO_PICKUP_LISTA

    query.edit_message_text("Opcion no valida.")
    return ConversationHandler.END


def pedido_pickup_nueva_ubicacion_handler(update, context):
    """Maneja la captura de ubicacion para nueva direccion de recogida."""
    from services import extract_lat_lng_from_text, expand_short_url

    text = update.message.text.strip()

    if text.lower() == "omitir":
        context.user_data["new_pickup_lat"] = None
        context.user_data["new_pickup_lng"] = None
        update.message.reply_text(
            "Sin ubicacion exacta.\n\n"
            "Ahora escribe los detalles de la direccion de recogida:\n"
            "direccion, barrio, referencias..."
        )
        return PEDIDO_PICKUP_NUEVA_DETALLES

    # Normalizar: tomar primer URL si hay varios tokens
    raw_link = text
    if "http" in text:
        raw_link = next((t for t in text.split() if t.startswith("http")), text)

    # Expandir link corto si aplica
    expanded = expand_short_url(raw_link) or raw_link

    coords = extract_lat_lng_from_text(expanded)
    if coords:
        lat, lng = coords
        context.user_data["new_pickup_lat"] = lat
        context.user_data["new_pickup_lng"] = lng
        update.message.reply_text(
            f"Ubicacion capturada: {lat}, {lng}\n\n"
            "Ahora escribe los detalles de la direccion de recogida:\n"
            "direccion, barrio, referencias..."
        )
        return PEDIDO_PICKUP_NUEVA_DETALLES

    # No se pudo extraer - detectar si es link corto de Google
    context.user_data["new_pickup_lat"] = None
    context.user_data["new_pickup_lng"] = None

    es_link_corto_google = "maps.app.goo.gl" in raw_link or "goo.gl/maps" in raw_link

    if es_link_corto_google:
        keyboard = [[InlineKeyboardButton(
            "📋 Copiar mensaje para enviar al cliente",
            callback_data="pickup_copiar_msg_cliente"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "⚠️ Ese enlace no incluye coordenadas exactas.\n\n"
            "👉 Pidele al cliente una de estas opciones:\n"
            "• En WhatsApp: 📎 → Ubicacion → Enviar ubicacion actual\n"
            "• En Google Maps: tocar el punto azul → Compartir → copiar el link largo\n\n"
            "Mientras tanto, escribe los detalles de la direccion de recogida:\n"
            "direccion, barrio, referencias...",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            "No se pudo extraer ubicacion del texto.\n\n"
            "Escribe los detalles de la direccion de recogida:\n"
            "direccion, barrio, referencias..."
        )

    return PEDIDO_PICKUP_NUEVA_DETALLES


def pickup_nueva_copiar_msg_callback(update, context):
    """Envia mensaje listo para copiar (flujo pickup nueva)."""
    query = update.callback_query
    query.answer()
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "📋 Copia y envia este mensaje al cliente:\n\n"
            "Hola 👋 ¿me puedes enviar tu ubicacion por WhatsApp "
            "(📍Enviar ubicacion actual) o un link largo de Google Maps? "
            "Es para registrar tu direccion rapido. Gracias 🙏"
        )
    )
    return PEDIDO_PICKUP_NUEVA_UBICACION


def pedido_pickup_nueva_detalles_handler(update, context):
    """Maneja la captura de detalles de nueva direccion de recogida."""
    text = update.message.text.strip()
    if not text:
        update.message.reply_text("Por favor escribe la direccion de recogida:")
        return PEDIDO_PICKUP_NUEVA_DETALLES

    context.user_data["new_pickup_address"] = text

    # Usar pickup temporal en user_data
    ally = context.user_data.get("ally")
    default_city = "Pereira"
    if ally:
        default_loc = get_default_ally_location(ally["id"])
        if default_loc and default_loc.get("city"):
            default_city = default_loc["city"]

    context.user_data["new_pickup_city"] = default_city

    # Guardar pickup temporal
    context.user_data["pickup_label"] = "Nueva"
    context.user_data["pickup_address"] = text
    context.user_data["pickup_city"] = default_city
    context.user_data["pickup_lat"] = context.user_data.get("new_pickup_lat")
    context.user_data["pickup_lng"] = context.user_data.get("new_pickup_lng")

    # Preguntar si quiere guardar la direccion
    keyboard = [
        [InlineKeyboardButton("Si, guardar", callback_data="pickup_guardar_si")],
        [InlineKeyboardButton("No, solo usar esta vez", callback_data="pickup_guardar_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Deseas guardar esta direccion para futuros pedidos?",
        reply_markup=reply_markup
    )
    return PEDIDO_PICKUP_GUARDAR


def pedido_pickup_guardar_callback(update, context):
    """Maneja la decision de guardar o no la nueva direccion."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally = context.user_data.get("ally")
    if not ally:
        query.edit_message_text("Error: no se encontro informacion del aliado.")
        return ConversationHandler.END

    if data == "pickup_guardar_si":
        # Guardar en BD
        new_loc_id = create_ally_location(
            ally_id=ally["id"],
            label=context.user_data.get("new_pickup_address", "")[:30],
            address=context.user_data.get("new_pickup_address", ""),
            city=context.user_data.get("new_pickup_city", "Pereira"),
            barrio="",
            phone="",
            is_default=False,
            lat=context.user_data.get("new_pickup_lat"),
            lng=context.user_data.get("new_pickup_lng"),
        )
        if new_loc_id:
            query.edit_message_text("Direccion guardada correctamente.")
        else:
            query.edit_message_text("No se pudo guardar, pero continuamos con el pedido.")

    else:
        query.edit_message_text("OK, usaremos esta direccion solo para este pedido.")

    # Continuar al siguiente paso
    return continuar_despues_pickup(query, context, edit=False)


def continuar_despues_pickup(query, context, edit=True):
    """Continua el flujo despues de seleccionar el pickup."""
    # Verificar si ya tenemos tipo de servicio
    if not context.user_data.get("service_type"):
        return mostrar_selector_tipo_servicio(query, context, edit=edit)

    # Ya tenemos tipo, preguntar por base
    return mostrar_pregunta_base(query, context, edit=edit)


def construir_resumen_pedido(context):
    """Construye el texto del resumen del pedido."""
    tipo_servicio = context.user_data.get("service_type", "-")
    nombre = context.user_data.get("customer_name", "-")
    telefono = context.user_data.get("customer_phone", "-")
    direccion = context.user_data.get("customer_address", "-")
    pickup_label = context.user_data.get("pickup_label", "")
    pickup_address = context.user_data.get("pickup_address", "")
    distancia = context.user_data.get("quote_distance_km", 0)
    precio = context.user_data.get("quote_price", 0)
    requires_cash = context.user_data.get("requires_cash", False)
    cash_amount = context.user_data.get("cash_required_amount", 0)
    buy_products = context.user_data.get("buy_products_count", 0)
    buy_surcharge = context.user_data.get("buy_surcharge", 0)

    # Mostrar recogida
    if pickup_label and pickup_address:
        recogida = f"{pickup_label}: {pickup_address}"
    elif pickup_address:
        recogida = pickup_address
    else:
        recogida = "-"

    resumen = (
        "RESUMEN DEL PEDIDO\n\n"
        f"Tipo: {tipo_servicio}\n"
        f"Cliente: {nombre}\n"
        f"Telefono: {telefono}\n"
        f"Recogida: {recogida}\n"
        f"Entrega: {direccion}\n"
        f"Distancia: {distancia:.1f} km\n"
    )

    # Si es Compras, mostrar desglose
    if tipo_servicio == "Compras" and buy_products > 0:
        tarifa_distancia = precio - buy_surcharge
        resumen += f"Tarifa distancia: ${tarifa_distancia:,}".replace(",", ".") + "\n"
        resumen += f"Productos: {buy_products}\n"
        resumen += f"Recargo productos: ${buy_surcharge:,}".replace(",", ".") + "\n"

    resumen += f"Valor del servicio: ${precio:,}".replace(",", ".") + "\n"

    if requires_cash and cash_amount > 0:
        resumen += f"Base requerida: ${cash_amount:,}".replace(",", ".") + "\n"

    resumen += "\nConfirmas este pedido?"
    return resumen


def mostrar_resumen_confirmacion(query, context, edit=True):
    """Muestra resumen del pedido con botones de confirmacion (para CallbackQuery)."""
    keyboard = [
        [InlineKeyboardButton("Confirmar pedido", callback_data="pedido_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    if edit:
        query.edit_message_text(resumen, reply_markup=reply_markup)
    else:
        query.message.reply_text(resumen, reply_markup=reply_markup)

    return PEDIDO_CONFIRMACION


def mostrar_resumen_confirmacion_msg(update, context):
    """Muestra resumen del pedido con botones de confirmacion (para Message)."""
    keyboard = [
        [InlineKeyboardButton("Confirmar pedido", callback_data="pedido_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    update.message.reply_text(resumen, reply_markup=reply_markup)
    return PEDIDO_CONFIRMACION


def pedido_confirmacion(update, context):
    """Fallback: redirige a botones si el usuario escribe texto."""
    # Mostrar resumen con botones
    return mostrar_resumen_confirmacion_msg(update, context)


def pedido_confirmacion_callback(update, context):
    """Maneja la confirmacion/cancelacion del pedido por botones."""
    query = update.callback_query
    query.answer()
    data = query.data

    # Anti doble-click: verificar si ya fue procesado
    if context.user_data.get("pedido_processed"):
        query.edit_message_text("Este pedido ya fue procesado.")
        return ConversationHandler.END

    if data == "pedido_confirmar":
        # Marcar como procesado ANTES de crear el pedido
        context.user_data["pedido_processed"] = True

        # Obtener datos del usuario y ally
        ally_id = context.user_data.get("ally_id")
        if not ally_id:
            query.edit_message_text("Error: sesion expirada. Usa /nuevo_pedido de nuevo.")
            context.user_data.clear()
            return ConversationHandler.END

        # Obtener pickup del selector (o default si no existe)
        pickup_location = context.user_data.get("pickup_location")
        pickup_text = context.user_data.get("pickup_address", "")
        if pickup_location:
            pickup_location_id = pickup_location.get("id")
        else:
            # Fallback: usar default si no se selecciono ninguno
            default_location = get_default_ally_location(ally_id)
            pickup_location_id = default_location["id"] if default_location else None
            if not pickup_text and default_location:
                pickup_text = default_location.get("address", "No definida")

        if not pickup_text:
            pickup_text = "No definida"

        # Obtener datos del pedido de context.user_data
        customer_name = context.user_data.get("customer_name", "")
        customer_phone = context.user_data.get("customer_phone", "")
        customer_address = context.user_data.get("customer_address", "")
        customer_city = context.user_data.get("customer_city", "")
        customer_barrio = context.user_data.get("customer_barrio", "")
        service_type = context.user_data.get("service_type", "")

        # Obtener datos de cotizacion
        distance_km = context.user_data.get("quote_distance_km", 0.0)
        quote_price = context.user_data.get("quote_price", 0)
        requires_cash = context.user_data.get("requires_cash", False)
        cash_required_amount = context.user_data.get("cash_required_amount", 0)

        # Obtener coords y quote_source
        pickup_lat = context.user_data.get("pickup_lat")
        pickup_lng = context.user_data.get("pickup_lng")
        dropoff_lat = context.user_data.get("dropoff_lat")
        dropoff_lng = context.user_data.get("dropoff_lng")
        quote_source = context.user_data.get("quote_source", "text")

        # Crear pedido en BD
        try:
            order_id = create_order(
                ally_id=ally_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_address=customer_address,
                customer_city=customer_city,
                customer_barrio=customer_barrio,
                pickup_location_id=pickup_location_id,
                pay_at_store_required=False,
                pay_at_store_amount=0,
                base_fee=0,
                distance_km=distance_km,
                rain_extra=0,
                high_demand_extra=0,
                night_extra=0,
                additional_incentive=0,
                total_fee=quote_price,
                instructions="",
                requires_cash=requires_cash,
                cash_required_amount=cash_required_amount,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
                quote_source=quote_source,
            )
            context.user_data["order_id"] = order_id

            # Incrementar contador de uso del pickup
            if pickup_location_id:
                increment_pickup_usage(pickup_location_id, ally_id)

            # Construir preview de oferta para repartidor
            preview = construir_preview_oferta(
                order_id, service_type, pickup_text, customer_address,
                distance_km, quote_price, requires_cash, cash_required_amount
            )

            # Si es cliente nuevo, preguntar si guardar
            is_new_customer = context.user_data.get("is_new_customer", False)
            if is_new_customer:
                keyboard = [
                    [InlineKeyboardButton("Si, guardar cliente", callback_data="pedido_guardar_si")],
                    [InlineKeyboardButton("No, solo este pedido", callback_data="pedido_guardar_no")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(
                    f"Pedido #{order_id} creado exitosamente.\n\n"
                    "Quieres guardar este cliente para futuros pedidos?",
                    reply_markup=reply_markup
                )
                # Enviar preview como mensaje separado
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=preview,
                    reply_markup=get_preview_buttons()
                )
                return PEDIDO_GUARDAR_CLIENTE
            else:
                # Cliente existente: éxito directo + menú
                context.user_data.clear()
                show_main_menu(update, context, f"Pedido #{order_id} creado exitosamente.\nPronto un repartidor sera asignado.")
                return ConversationHandler.END

        except Exception as e:
            query.edit_message_text(
                f"Error al crear el pedido: {str(e)}\n\n"
                "Por favor intenta nuevamente mas tarde."
            )
            context.user_data.clear()
            show_main_menu(update, context)
            return ConversationHandler.END

    elif data == "pedido_cancelar":
        query.edit_message_text("Pedido cancelado.")
        context.user_data.clear()
        show_main_menu(update, context)
        return ConversationHandler.END

    return PEDIDO_CONFIRMACION


def construir_preview_oferta(order_id, service_type, pickup_text, customer_address,
                              distance_km, price, requires_cash, cash_amount):
    """Construye el preview de la oferta que vera el repartidor."""
    preview = (
        "PREVIEW: ASI VERA EL REPARTIDOR LA OFERTA\n"
        "=" * 35 + "\n\n"
        "OFERTA DISPONIBLE\n\n"
        f"Servicio: {service_type}\n"
        f"Recoge en: {pickup_text}\n"
        f"Entrega en: {customer_address}\n"
        f"Distancia: {distance_km:.1f} km\n"
        f"Pago: ${price:,}".replace(",", ".") + "\n"
    )

    if requires_cash and cash_amount > 0:
        preview += f"Base requerida: ${cash_amount:,}".replace(",", ".") + "\n"
        preview += (
            "\nADVERTENCIA:\n"
            f"Si no tienes al menos ${cash_amount:,}".replace(",", ".") + " de base, "
            "NO tomes este servicio.\n"
            "Sin base, no se te entregara la orden."
        )

    return preview


def get_preview_buttons():
    """Retorna botones simulados del preview."""
    keyboard = [
        [
            InlineKeyboardButton("Aceptar (preview)", callback_data="preview_accept"),
            InlineKeyboardButton("Rechazar (preview)", callback_data="preview_reject"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def preview_callback(update, context):
    """Maneja clicks en botones del preview (solo informativo)."""
    query = update.callback_query
    query.answer("Vista previa: esto lo vera el repartidor.", show_alert=True)


def pedido_guardar_cliente_callback(update, context):
    """Maneja la decision de guardar o no el cliente nuevo."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pedido_guardar_si":
        ally_id = context.user_data.get("ally_id")
        customer_name = context.user_data.get("customer_name", "")
        customer_phone = context.user_data.get("customer_phone", "")
        customer_address = context.user_data.get("customer_address", "")

        try:
            # Crear cliente
            customer_id = create_ally_customer(ally_id, customer_name, customer_phone)
            # Crear direccion
            create_customer_address(
                customer_id,
                "Principal",
                customer_address,
                lat=context.user_data.get("dropoff_lat"),
                lng=context.user_data.get("dropoff_lng"),
            )
            context.user_data.clear()
            show_main_menu(update, context, f"Pedido creado exitosamente.\nCliente '{customer_name}' guardado para futuros pedidos.\nPronto un repartidor sera asignado.")
            return ConversationHandler.END
        except Exception as e:
            context.user_data.clear()
            show_main_menu(update, context, f"Pedido creado exitosamente.\nError al guardar cliente: {str(e)}\nPronto un repartidor sera asignado.")
            return ConversationHandler.END

    elif data == "pedido_guardar_no":
        context.user_data.clear()
        show_main_menu(update, context, "Pedido creado exitosamente.\nPronto un repartidor sera asignado.")
        return ConversationHandler.END

    return PEDIDO_GUARDAR_CLIENTE


def aliados_pendientes(update, context):
    """Lista aliados PENDING solo para el Administrador de Plataforma."""
    message = update.effective_message
    telegram_id = update.effective_user.id

    if telegram_id != ADMIN_USER_ID:
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
    telegram_id = update.effective_user.id
    es_admin_plataforma = (telegram_id == ADMIN_USER_ID)

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
        status = existing.get("status") if isinstance(existing, dict) else existing[7]
        admin_id = existing.get("id") if isinstance(existing, dict) else existing[0]

        # Obtener rejection_type usando función específica
        rejection_type = get_admin_rejection_type_by_id(admin_id)

        # Bloquear si PENDING o APPROVED
        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de administrador en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de administrador aprobado (APPROVED). Si necesitas cambios, contacta al administrador de plataforma."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        # Bloquear si REJECTED + BLOCKED
        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador de plataforma.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        # Permitir actualizar si INACTIVE o REJECTED CORRECTABLE/NULL
        team_name = existing.get("team_name") if isinstance(existing, dict) else (existing[9] if len(existing) > 9 and existing[9] else existing[3])
        doc = existing.get("document_number") if isinstance(existing, dict) else (existing[10] if len(existing) > 10 and existing[10] else "No registrado")
        full_name = existing.get("full_name") if isinstance(existing, dict) else existing[3]
        phone = existing.get("phone") if isinstance(existing, dict) else existing[4]
        city = existing.get("city") if isinstance(existing, dict) else existing[5]
        barrio = existing.get("barrio") if isinstance(existing, dict) else existing[6]

        update.message.reply_text(
            "Ya tienes un registro como Administrador Local.\n"
            f"Nombre: {full_name}\n"
            f"Documento: {doc}\n"
            f"Administración: {team_name}\n"
            f"Teléfono: {phone}\n"
            f"Ciudad: {city}\n"
            f"Barrio: {barrio}\n"
            f"Estado: {status}\n\n"
            "Si deseas actualizar tus datos, escribe SI.\n"
            "Si no, escribe NO.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data["admin_update_prompt"] = True
        return LOCAL_ADMIN_NAME

    update.message.reply_text(
        "Registro de Administrador Local.\nEscribe tu nombre completo:",
        reply_markup=ReplyKeyboardRemove()
    )
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
    
    try:
        admin_id, team_code = create_admin(
            user_db_id, full_name, phone, city, barrio, team_name, document_number
        )
    except ValueError as e:
        update.message.reply_text(str(e))
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        print("[ERROR] admin_accept:", e)
        update.message.reply_text("Error técnico al finalizar tu registro. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END

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
    if user.id != ADMIN_USER_ID:
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
    """Cierra cualquier conversación activa y muestra menú principal."""
    try:
        context.user_data.clear()
    except Exception:
        pass

    # Responder según sea mensaje o callback
    if getattr(update, "callback_query", None):
        q = update.callback_query
        q.answer()
        q.edit_message_text("Proceso cancelado.")
    else:
        update.message.reply_text("Proceso cancelado.")

    # Mostrar menú principal
    show_main_menu(update, context, "Menu principal. Selecciona una opcion:")
    return ConversationHandler.END


def cancel_por_texto(update, context):
    """Handler para cuando el usuario escribe 'Cancelar' o 'Volver al menu'."""
    return cancel_conversacion(update, context)


def volver_menu_global(update, context):
    """Handler global para 'Cancelar' o 'Volver al menu' fuera de conversaciones."""
    try:
        context.user_data.clear()
    except Exception:
        pass
    show_main_menu(update, context, "Menu principal. Selecciona una opcion:")


# ----- COTIZADOR INTERNO -----

def cotizar_start(update, context):
    update.message.reply_text(
        "COTIZADOR\n\n"
        "Enviame la distancia en km (ej: 5.9)."
    )
    return COTIZAR_DISTANCIA

def cotizar_distancia(update, context):
    texto = (update.message.text or "").strip().replace(",", ".")
    try:
        distancia = float(texto)
    except ValueError:
        update.message.reply_text("Valor invalido. Escribe la distancia en km (ej: 5.9).")
        return COTIZAR_DISTANCIA

    if distancia <= 0:
        update.message.reply_text("La distancia debe ser mayor a 0. Ej: 3.1")
        return COTIZAR_DISTANCIA

    precio = calcular_precio_distancia(distancia)

    update.message.reply_text(
        f"Distancia: {distancia:.1f} km\n"
        f"Precio: ${precio:,}".replace(",", ".")
    )
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

    telegram_id = update.effective_user.id
    es_admin_plataforma = (telegram_id == ADMIN_USER_ID)

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
        "Seleccione que desea revisar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# COMANDO /clientes - AGENDA DE CLIENTES RECURRENTES
# ============================================================

def clientes_cmd(update, context):
    """Comando /clientes - Solo para aliados aprobados."""
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)

    if not db_user:
        update.message.reply_text("Aun no estas registrado. Usa /start primero.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text(
            "Este comando es solo para aliados registrados.\n"
            "Si tienes un negocio, registrate con /soy_aliado."
        )
        return ConversationHandler.END

    if ally["status"] != "APPROVED":
        update.message.reply_text(
            "Tu registro como aliado aun no ha sido aprobado.\n"
            "Cuando tu estado sea APPROVED podras usar esta funcion."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["ally_id"] = ally["id"]

    return clientes_mostrar_menu(update, context)


def clientes_mostrar_menu(update, context, edit_message=False):
    """Muestra el menu principal de clientes."""
    keyboard = [
        [InlineKeyboardButton("Nuevo cliente", callback_data="cust_nuevo")],
        [InlineKeyboardButton("Buscar cliente", callback_data="cust_buscar")],
        [InlineKeyboardButton("Mis clientes", callback_data="cust_lista")],
        [InlineKeyboardButton("Clientes archivados", callback_data="cust_archivados")],
        [InlineKeyboardButton("Cerrar", callback_data="cust_cerrar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "AGENDA DE CLIENTES\n\nSelecciona una opcion:"

    if edit_message and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text, reply_markup=reply_markup)

    return CLIENTES_MENU


def clientes_menu_callback(update, context):
    """Maneja los callbacks del menu de clientes."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ally_id")

    if not ally_id:
        query.edit_message_text("Sesion expirada. Usa /clientes de nuevo.")
        return ConversationHandler.END

    if data == "cust_nuevo":
        query.edit_message_text("NUEVO CLIENTE\n\nEscribe el nombre del cliente:")
        return CLIENTES_NUEVO_NOMBRE

    elif data == "cust_buscar":
        query.edit_message_text("BUSCAR CLIENTE\n\nEscribe el nombre o telefono a buscar:")
        return CLIENTES_BUSCAR

    elif data == "cust_lista":
        customers = list_ally_customers(ally_id, limit=10, include_inactive=False)
        if not customers:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cust_volver_menu")]]
            query.edit_message_text(
                "No tienes clientes guardados.\n\n"
                "Usa 'Nuevo cliente' para agregar uno.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return CLIENTES_MENU

        keyboard = []
        for c in customers:
            btn_text = f"{c['name']} - {c['phone']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"cust_ver_{c['id']}")])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="cust_volver_menu")])

        query.edit_message_text(
            "MIS CLIENTES\n\nSelecciona un cliente para ver detalles:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_MENU

    elif data == "cust_archivados":
        customers = list_ally_customers(ally_id, limit=20, include_inactive=True)
        archived = [c for c in customers if c["status"] == "INACTIVE"]

        if not archived:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cust_volver_menu")]]
            query.edit_message_text(
                "No tienes clientes archivados.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return CLIENTES_MENU

        keyboard = []
        for c in archived:
            btn_text = f"{c['name']} - {c['phone']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"cust_restaurar_{c['id']}")])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="cust_volver_menu")])

        query.edit_message_text(
            "CLIENTES ARCHIVADOS\n\nSelecciona uno para restaurar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_MENU

    elif data == "cust_volver_menu":
        return clientes_mostrar_menu(update, context, edit_message=True)

    elif data == "cust_cerrar":
        query.edit_message_text("Agenda de clientes cerrada.")
        context.user_data.clear()
        return ConversationHandler.END

    elif data.startswith("cust_ver_"):
        customer_id = int(data.replace("cust_ver_", ""))
        return clientes_ver_cliente(query, context, customer_id)

    elif data.startswith("cust_restaurar_"):
        customer_id = int(data.replace("cust_restaurar_", ""))
        if restore_ally_customer(customer_id, ally_id):
            query.edit_message_text("Cliente restaurado exitosamente.")
        else:
            query.edit_message_text("No se pudo restaurar el cliente.")
        return clientes_mostrar_menu(update, context, edit_message=False)

    return CLIENTES_MENU


def clientes_ver_cliente(query, context, customer_id):
    """Muestra detalles de un cliente y sus opciones."""
    ally_id = context.user_data.get("ally_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if not customer:
        query.edit_message_text("Cliente no encontrado.")
        return CLIENTES_MENU

    context.user_data["current_customer_id"] = customer_id

    addresses = list_customer_addresses(customer_id)
    addr_text = ""
    if addresses:
        for i, addr in enumerate(addresses, 1):
            label = addr["label"] or "Sin etiqueta"
            addr_text += f"{i}. {label}: {addr['address_text']}\n"
    else:
        addr_text = "Sin direcciones guardadas\n"

    notas = customer["notes"] or "Sin notas"

    keyboard = [
        [InlineKeyboardButton("Direcciones", callback_data="cust_dirs")],
        [InlineKeyboardButton("Editar", callback_data="cust_editar")],
        [InlineKeyboardButton("Archivar", callback_data="cust_archivar")],
        [InlineKeyboardButton("Volver", callback_data="cust_volver_menu")],
    ]

    query.edit_message_text(
        f"CLIENTE: {customer['name']}\n"
        f"Telefono: {customer['phone']}\n"
        f"Notas: {notas}\n\n"
        f"DIRECCIONES:\n{addr_text}\n"
        "Selecciona una accion:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CLIENTES_VER_CLIENTE


def clientes_ver_cliente_callback(update, context):
    """Maneja callbacks de la vista de cliente."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ally_id")
    customer_id = context.user_data.get("current_customer_id")

    if data == "cust_dirs":
        addresses = list_customer_addresses(customer_id)
        keyboard = []

        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            btn_text = f"{label}: {addr['address_text'][:25]}..."
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"cust_dir_ver_{addr['id']}")])

        keyboard.append([InlineKeyboardButton("Agregar direccion", callback_data="cust_dir_nueva")])
        keyboard.append([InlineKeyboardButton("Volver", callback_data=f"cust_ver_{customer_id}")])

        query.edit_message_text(
            "DIRECCIONES DEL CLIENTE\n\nSelecciona una para editar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_VER_CLIENTE

    elif data == "cust_editar":
        keyboard = [
            [InlineKeyboardButton("Editar nombre", callback_data="cust_edit_nombre")],
            [InlineKeyboardButton("Editar telefono", callback_data="cust_edit_telefono")],
            [InlineKeyboardButton("Editar notas", callback_data="cust_edit_notas")],
            [InlineKeyboardButton("Volver", callback_data=f"cust_ver_{customer_id}")],
        ]
        query.edit_message_text(
            "Que deseas editar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_VER_CLIENTE

    elif data == "cust_edit_nombre":
        query.edit_message_text("Escribe el nuevo nombre del cliente:")
        return CLIENTES_EDITAR_NOMBRE

    elif data == "cust_edit_telefono":
        query.edit_message_text("Escribe el nuevo telefono del cliente:")
        return CLIENTES_EDITAR_TELEFONO

    elif data == "cust_edit_notas":
        query.edit_message_text("Escribe las nuevas notas del cliente (o 'ninguna' para borrar):")
        return CLIENTES_EDITAR_NOTAS

    elif data == "cust_archivar":
        if archive_ally_customer(customer_id, ally_id):
            query.edit_message_text("Cliente archivado exitosamente.")
        else:
            query.edit_message_text("No se pudo archivar el cliente.")
        context.user_data.pop("current_customer_id", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    elif data == "cust_dir_nueva":
        query.edit_message_text("NUEVA DIRECCION\n\nEscribe la etiqueta (Casa, Trabajo, Otro):")
        return CLIENTES_DIR_NUEVA_LABEL

    elif data.startswith("cust_dir_ver_"):
        address_id = int(data.replace("cust_dir_ver_", ""))
        address = get_customer_address_by_id(address_id, customer_id)
        if not address:
            query.edit_message_text("Direccion no encontrada.")
            return CLIENTES_VER_CLIENTE

        context.user_data["current_address_id"] = address_id
        label = address["label"] or "Sin etiqueta"

        keyboard = [
            [InlineKeyboardButton("Editar", callback_data="cust_dir_editar")],
            [InlineKeyboardButton("Archivar", callback_data="cust_dir_archivar")],
            [InlineKeyboardButton("Volver", callback_data="cust_dirs")],
        ]

        query.edit_message_text(
            f"DIRECCION: {label}\n\n"
            f"Direccion: {address['address_text']}\n"
            f"Ciudad: {address['city'] or 'N/A'}\n"
            f"Barrio: {address['barrio'] or 'N/A'}\n\n"
            "Selecciona una accion:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_VER_CLIENTE

    elif data == "cust_dir_editar":
        query.edit_message_text("Escribe la nueva etiqueta (Casa, Trabajo, Otro):")
        return CLIENTES_DIR_EDITAR_LABEL

    elif data == "cust_dir_archivar":
        address_id = context.user_data.get("current_address_id")
        if archive_customer_address(address_id, customer_id):
            query.edit_message_text("Direccion archivada.")
        else:
            query.edit_message_text("No se pudo archivar la direccion.")
        context.user_data.pop("current_address_id", None)
        return clientes_ver_cliente(query, context, customer_id)

    elif data.startswith("cust_ver_"):
        cid = int(data.replace("cust_ver_", ""))
        return clientes_ver_cliente(query, context, cid)

    elif data == "cust_volver_menu":
        context.user_data.pop("current_customer_id", None)
        return clientes_mostrar_menu(update, context, edit_message=True)

    return CLIENTES_VER_CLIENTE


def clientes_nuevo_nombre(update, context):
    """Recibe nombre del nuevo cliente."""
    context.user_data["new_customer_name"] = update.message.text.strip()
    update.message.reply_text("Escribe el telefono del cliente:")
    return CLIENTES_NUEVO_TELEFONO


def clientes_nuevo_telefono(update, context):
    """Recibe telefono del nuevo cliente."""
    context.user_data["new_customer_phone"] = update.message.text.strip()
    update.message.reply_text("Escribe notas del cliente (o 'ninguna' si no hay):")
    return CLIENTES_NUEVO_NOTAS


def clientes_nuevo_notas(update, context):
    """Recibe notas del nuevo cliente."""
    notas = update.message.text.strip()
    if notas.lower() == "ninguna":
        notas = None
    context.user_data["new_customer_notes"] = notas
    update.message.reply_text("Escribe la etiqueta de la direccion (Casa, Trabajo, Otro):")
    return CLIENTES_NUEVO_DIRECCION_LABEL


def clientes_nuevo_direccion_label(update, context):
    """Recibe etiqueta de direccion del nuevo cliente."""
    context.user_data["new_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return CLIENTES_NUEVO_DIRECCION_TEXT


def clientes_nuevo_direccion_text(update, context):
    """Recibe direccion y guarda el nuevo cliente."""
    address_text = update.message.text.strip()
    ally_id = context.user_data.get("ally_id")
    name = context.user_data.get("new_customer_name")
    phone = context.user_data.get("new_customer_phone")
    notes = context.user_data.get("new_customer_notes")
    label = context.user_data.get("new_address_label")

    try:
        customer_id = create_ally_customer(ally_id, name, phone, notes)
        create_customer_address(customer_id, label, address_text)

        keyboard = [[InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")]]
        update.message.reply_text(
            f"Cliente '{name}' creado exitosamente.\n\n"
            f"Telefono: {phone}\n"
            f"Direccion ({label}): {address_text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        update.message.reply_text(f"Error al crear cliente: {str(e)}")

    # Limpiar datos temporales
    for key in ["new_customer_name", "new_customer_phone", "new_customer_notes", "new_address_label"]:
        context.user_data.pop(key, None)

    return CLIENTES_MENU


def clientes_buscar(update, context):
    """Busca clientes por nombre o telefono."""
    query_text = update.message.text.strip()
    ally_id = context.user_data.get("ally_id")

    results = search_ally_customers(ally_id, query_text, limit=10)
    if not results:
        keyboard = [[InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")]]
        update.message.reply_text(
            f"No se encontraron clientes con '{query_text}'.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_MENU

    keyboard = []
    for c in results:
        btn_text = f"{c['name']} - {c['phone']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"cust_ver_{c['id']}")])
    keyboard.append([InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")])

    update.message.reply_text(
        f"Resultados para '{query_text}':",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CLIENTES_MENU


def clientes_editar_nombre(update, context):
    """Actualiza el nombre del cliente."""
    nuevo_nombre = update.message.text.strip()
    ally_id = context.user_data.get("ally_id")
    customer_id = context.user_data.get("current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if customer:
        update_ally_customer(customer_id, ally_id, nuevo_nombre, customer["phone"], customer["notes"])
        update.message.reply_text(f"Nombre actualizado a: {nuevo_nombre}")
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_editar_telefono(update, context):
    """Actualiza el telefono del cliente."""
    nuevo_telefono = update.message.text.strip()
    ally_id = context.user_data.get("ally_id")
    customer_id = context.user_data.get("current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if customer:
        update_ally_customer(customer_id, ally_id, customer["name"], nuevo_telefono, customer["notes"])
        update.message.reply_text(f"Telefono actualizado a: {nuevo_telefono}")
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_editar_notas(update, context):
    """Actualiza las notas del cliente."""
    nuevas_notas = update.message.text.strip()
    if nuevas_notas.lower() == "ninguna":
        nuevas_notas = None
    ally_id = context.user_data.get("ally_id")
    customer_id = context.user_data.get("current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if customer:
        update_ally_customer(customer_id, ally_id, customer["name"], customer["phone"], nuevas_notas)
        update.message.reply_text("Notas actualizadas.")
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_dir_nueva_label(update, context):
    """Recibe etiqueta de nueva direccion."""
    context.user_data["new_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return CLIENTES_DIR_NUEVA_TEXT


def clientes_dir_nueva_text(update, context):
    """Crea nueva direccion para cliente existente."""
    address_text = update.message.text.strip()
    customer_id = context.user_data.get("current_customer_id")
    label = context.user_data.get("new_address_label")

    try:
        create_customer_address(customer_id, label, address_text)
        update.message.reply_text(f"Direccion agregada: {label} - {address_text}")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

    context.user_data.pop("new_address_label", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_dir_editar_label(update, context):
    """Recibe nueva etiqueta para editar direccion."""
    context.user_data["edit_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la nueva direccion completa:")
    return CLIENTES_DIR_EDITAR_TEXT


def clientes_dir_editar_text(update, context):
    """Actualiza direccion existente."""
    address_text = update.message.text.strip()
    customer_id = context.user_data.get("current_customer_id")
    address_id = context.user_data.get("current_address_id")
    label = context.user_data.get("edit_address_label")

    try:
        update_customer_address(address_id, customer_id, label, address_text)
        update.message.reply_text("Direccion actualizada.")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

    context.user_data.pop("edit_address_label", None)
    context.user_data.pop("current_address_id", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


# ConversationHandler para /clientes
clientes_conv = ConversationHandler(
    entry_points=[CommandHandler("clientes", clientes_cmd)],
    states={
        CLIENTES_MENU: [
            CallbackQueryHandler(clientes_menu_callback, pattern=r"^cust_")
        ],
        CLIENTES_NUEVO_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_nombre)
        ],
        CLIENTES_NUEVO_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_telefono)
        ],
        CLIENTES_NUEVO_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_notas)
        ],
        CLIENTES_NUEVO_DIRECCION_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_direccion_label)
        ],
        CLIENTES_NUEVO_DIRECCION_TEXT: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_direccion_text)
        ],
        CLIENTES_BUSCAR: [
            MessageHandler(Filters.text & ~Filters.command, clientes_buscar)
        ],
        CLIENTES_VER_CLIENTE: [
            CallbackQueryHandler(clientes_ver_cliente_callback, pattern=r"^cust_")
        ],
        CLIENTES_EDITAR_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_nombre)
        ],
        CLIENTES_EDITAR_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_telefono)
        ],
        CLIENTES_EDITAR_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_notas)
        ],
        CLIENTES_DIR_NUEVA_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_nueva_label)
        ],
        CLIENTES_DIR_NUEVA_TEXT: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_nueva_text)
        ],
        CLIENTES_DIR_EDITAR_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_editar_label)
        ],
        CLIENTES_DIR_EDITAR_TEXT: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_editar_text)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'^(Cancelar|Volver al menu)$'), cancel_por_texto),
    ],
    allow_reentry=True,
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
        ALLY_UBICACION: [
            CallbackQueryHandler(ally_ubicacion_skip_callback, pattern=r"^ally_ubicacion_skip$"),
            MessageHandler(Filters.text & ~Filters.command, ally_ubicacion_handler)
        ],
        ALLY_TEAM: [CallbackQueryHandler(ally_team_callback, pattern=r"^ally_team:")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        CommandHandler("menu", menu),
        MessageHandler(Filters.regex(r'^(Cancelar|Volver al menu)$'), cancel_por_texto),
    ],
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
        COURIER_TEAMCODE: [
            MessageHandler(Filters.text & ~Filters.command, courier_teamcode)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        CommandHandler("menu", menu),
        MessageHandler(Filters.regex(r'^(Cancelar|Volver al menu)$'), cancel_por_texto),
    ],
    allow_reentry=True,
)

# Conversacion para /nuevo_pedido (con selector de cliente recurrente)
nuevo_pedido_conv = ConversationHandler(
    entry_points=[
        CommandHandler("nuevo_pedido", nuevo_pedido),
        MessageHandler(Filters.regex(r'^Nuevo pedido$'), nuevo_pedido),
    ],
    states={
        PEDIDO_SELECTOR_CLIENTE: [
            CallbackQueryHandler(pedido_selector_cliente_callback, pattern=r"^pedido_")
        ],
        PEDIDO_BUSCAR_CLIENTE: [
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_buscar_cliente)
        ],
        PEDIDO_SELECCIONAR_DIRECCION: [
            CallbackQueryHandler(pedido_seleccionar_direccion_callback, pattern=r"^pedido_")
        ],
        PEDIDO_TIPO_SERVICIO: [
            CallbackQueryHandler(pedido_tipo_servicio_callback, pattern=r"^pedido_tipo_"),
            MessageHandler(Filters.text & ~Filters.command, pedido_tipo_servicio)
        ],
        PEDIDO_COMPRAS_CANTIDAD: [
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_compras_cantidad_handler)
        ],
        PEDIDO_NOMBRE: [
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_nombre_cliente)
        ],
        PEDIDO_TELEFONO: [
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_telefono_cliente)
        ],
        PEDIDO_UBICACION: [
            CallbackQueryHandler(pedido_ubicacion_skip_callback, pattern=r"^pedido_ubicacion_skip$"),
            CallbackQueryHandler(pedido_ubicacion_copiar_msg_callback, pattern=r"^ubicacion_copiar_msg_cliente$"),
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_ubicacion_handler)
        ],
        PEDIDO_DIRECCION: [
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_direccion_cliente)
        ],
        PEDIDO_PICKUP_SELECTOR: [
            CallbackQueryHandler(pedido_pickup_callback, pattern=r"^pickup_select_")
        ],
        PEDIDO_PICKUP_LISTA: [
            CallbackQueryHandler(pedido_pickup_lista_callback, pattern=r"^pickup_list_")
        ],
        PEDIDO_PICKUP_NUEVA_UBICACION: [
            CallbackQueryHandler(pickup_nueva_copiar_msg_callback, pattern=r"^pickup_copiar_msg_cliente$"),
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_pickup_nueva_ubicacion_handler)
        ],
        PEDIDO_PICKUP_NUEVA_DETALLES: [
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_pickup_nueva_detalles_handler)
        ],
        PEDIDO_PICKUP_GUARDAR: [
            CallbackQueryHandler(pedido_pickup_guardar_callback, pattern=r"^pickup_guardar_")
        ],
        PEDIDO_REQUIERE_BASE: [
            CallbackQueryHandler(pedido_requiere_base_callback, pattern=r"^pedido_base_")
        ],
        PEDIDO_VALOR_BASE: [
            CallbackQueryHandler(pedido_valor_base_callback, pattern=r"^pedido_base_"),
            MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_valor_base_texto)
        ],
        PEDIDO_CONFIRMACION: [
            CallbackQueryHandler(pedido_retry_quote_callback, pattern=r"^pedido_retry_quote$"),
            CallbackQueryHandler(pedido_confirmacion_callback, pattern=r"^pedido_(confirmar|cancelar)$"),
            MessageHandler(Filters.text & ~Filters.command, pedido_confirmacion)
        ],
        PEDIDO_GUARDAR_CLIENTE: [
            CallbackQueryHandler(pedido_guardar_cliente_callback, pattern=r"^pedido_guardar_")
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'^\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)

# Conversación para /cotizar
cotizar_conv = ConversationHandler(
    entry_points=[CommandHandler("cotizar", cotizar_start)],
    states={
        COTIZAR_DISTANCIA: [MessageHandler(Filters.text & ~Filters.command, cotizar_distancia)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'^(Cancelar|Volver al menu)$'), cancel_por_texto),
    ],
)


# ----- CONFIGURACION DE TARIFAS (ADMIN PLATAFORMA) -----

def tarifas_start(update, context):
    """Comando /tarifas - Solo Admin Plataforma."""
    user = update.effective_user

    # Validar que es Admin de Plataforma
    if not es_admin_plataforma(user.id):
        update.message.reply_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    # Cargar configuracion actual
    config = get_pricing_config()
    buy_config = get_buy_pricing_config()

    # Mostrar valores actuales
    mensaje = (
        "CONFIGURACION DE TARIFAS\n\n"
        "TARIFAS POR DISTANCIA:\n"
        f"1. Precio 0-2 km: ${config['precio_0_2km']:,}\n"
        f"2. Precio 2-3 km: ${config['precio_2_3km']:,}\n"
        f"3. Base distancia (km): {config['base_distance_km']}\n"
        f"4. Precio km extra normal (<=10km): ${config['precio_km_extra_normal']:,}\n"
        f"5. Umbral km largo: {config['umbral_km_largo']} km\n"
        f"6. Precio km extra largo (>10km): ${config['precio_km_extra_largo']:,}\n"
        "\nTARIFAS COMPRAS (recargo por productos):\n"
        f"7. Productos 1-{buy_config['tier1_max']}: ${buy_config['tier1_fee']:,} c/u\n"
        f"8. Productos {buy_config['tier1_max']+1}-{buy_config['tier1_max']+buy_config['tier2_max']}: ${buy_config['tier2_fee']:,} c/u\n"
        f"9. Productos {buy_config['tier1_max']+buy_config['tier2_max']+1}+: ${buy_config['tier3_fee']:,} c/u\n"
    )

    # Botones para editar
    keyboard = [
        [InlineKeyboardButton("Cambiar 0-2 km", callback_data="pricing_edit_precio_0_2km")],
        [InlineKeyboardButton("Cambiar 2-3 km", callback_data="pricing_edit_precio_2_3km")],
        [InlineKeyboardButton("Cambiar base distancia", callback_data="pricing_edit_base_distance_km")],
        [InlineKeyboardButton("Cambiar km extra normal", callback_data="pricing_edit_precio_km_extra_normal")],
        [InlineKeyboardButton("Cambiar umbral largo", callback_data="pricing_edit_umbral_km_largo")],
        [InlineKeyboardButton("Cambiar km extra largo", callback_data="pricing_edit_precio_km_extra_largo")],
        [InlineKeyboardButton("Compras: max tier1", callback_data="pricing_edit_buy_tier1_max")],
        [InlineKeyboardButton("Compras: fee tier1", callback_data="pricing_edit_buy_tier1_fee")],
        [InlineKeyboardButton("Compras: max tier2", callback_data="pricing_edit_buy_tier2_max")],
        [InlineKeyboardButton("Compras: fee tier2", callback_data="pricing_edit_buy_tier2_fee")],
        [InlineKeyboardButton("Compras: fee tier3", callback_data="pricing_edit_buy_tier3_fee")],
        [InlineKeyboardButton("Salir", callback_data="pricing_exit")],
    ]

    update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


def tarifas_edit_callback(update, context):
    """Callback para editar un valor de tarifa."""
    query = update.callback_query
    query.answer()

    # Validar que es Admin de Plataforma
    if not es_admin_plataforma(query.from_user.id):
        query.edit_message_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    data = query.data

    if data == "pricing_exit":
        query.edit_message_text("Configuracion de tarifas cerrada.")
        return ConversationHandler.END

    # Extraer el campo a editar
    if not data.startswith("pricing_edit_"):
        query.edit_message_text("Opcion no valida.")
        return ConversationHandler.END

    field = data.replace("pricing_edit_", "")
    context.user_data["pricing_field"] = field

    # Mapeo de campos a nombres legibles
    field_names = {
        "precio_0_2km": "Precio 0-2 km",
        "precio_2_3km": "Precio 2-3 km",
        "base_distance_km": "Base distancia (km)",
        "precio_km_extra_normal": "Precio km extra normal",
        "umbral_km_largo": "Umbral km largo",
        "precio_km_extra_largo": "Precio km extra largo",
        "buy_tier1_max": "Compras: max productos tier1 (default 5)",
        "buy_tier1_fee": "Compras: recargo tier1 c/u (default 1000)",
        "buy_tier2_max": "Compras: max productos tier2 (default 5)",
        "buy_tier2_fee": "Compras: recargo tier2 c/u (default 700)",
        "buy_tier3_fee": "Compras: recargo tier3+ c/u (default 500)",
    }

    field_name = field_names.get(field, field)

    query.edit_message_text(
        f"Editar: {field_name}\n\n"
        f"Envia el nuevo valor (numero).\n"
        f"O escribe /cancel para cancelar."
    )

    return TARIFAS_VALOR


def tarifas_set_valor(update, context):
    """Captura y guarda el nuevo valor."""
    user = update.effective_user

    # Validar que es Admin de Plataforma
    if not es_admin_plataforma(user.id):
        update.message.reply_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    texto = (update.message.text or "").strip().replace(",", ".")
    field = context.user_data.get("pricing_field")

    if not field:
        update.message.reply_text("Error: no se pudo identificar el campo a editar.")
        return ConversationHandler.END

    # Validar valor numerico
    try:
        valor_float = float(texto)
    except ValueError:
        update.message.reply_text("Valor invalido. Debe ser un numero. Intenta de nuevo o usa /cancel.")
        return TARIFAS_VALOR

    # Guardar en BD - campos de compras usan prefijo 'buy_', distancia usa 'pricing_'
    if field.startswith("buy_"):
        setting_key = field
    else:
        setting_key = f"pricing_{field}"
    set_setting(setting_key, texto)

    # Recargar config y mostrar
    config = get_pricing_config()
    buy_config = get_buy_pricing_config()

    # Pruebas rapidas
    test_31 = calcular_precio_distancia(3.1)
    test_111 = calcular_precio_distancia(11.1)
    test_buy_3 = calc_buy_products_surcharge(3)
    test_buy_8 = calc_buy_products_surcharge(8)
    test_buy_15 = calc_buy_products_surcharge(15)

    mensaje = (
        "Guardado.\n\n"
        "TARIFAS DISTANCIA:\n"
        f"- Precio 0-2 km: ${config['precio_0_2km']:,}\n"
        f"- Precio 2-3 km: ${config['precio_2_3km']:,}\n"
        f"- Base distancia: {config['base_distance_km']} km\n"
        f"- Precio km extra normal: ${config['precio_km_extra_normal']:,}\n"
        f"- Umbral largo: {config['umbral_km_largo']} km\n"
        f"- Precio km extra largo: ${config['precio_km_extra_largo']:,}\n\n"
        f"TARIFAS COMPRAS:\n"
        f"- Tier1 (1-{buy_config['tier1_max']}): ${buy_config['tier1_fee']:,} c/u\n"
        f"- Tier2 ({buy_config['tier1_max']+1}-{buy_config['tier1_max']+buy_config['tier2_max']}): ${buy_config['tier2_fee']:,} c/u\n"
        f"- Tier3 ({buy_config['tier1_max']+buy_config['tier2_max']+1}+): ${buy_config['tier3_fee']:,} c/u\n\n"
        f"Prueba rapida distancia:\n"
        f"3.1 km -> ${test_31:,}\n"
        f"11.1 km -> ${test_111:,}\n\n"
        f"Prueba rapida compras:\n"
        f"3 productos -> ${test_buy_3:,}\n"
        f"8 productos -> ${test_buy_8:,}\n"
        f"15 productos -> ${test_buy_15:,}"
    )

    update.message.reply_text(mensaje)
    context.user_data.clear()
    return ConversationHandler.END


# Conversacion para /tarifas
tarifas_conv = ConversationHandler(
    entry_points=[CommandHandler("tarifas", tarifas_start)],
    states={
        TARIFAS_VALOR: [MessageHandler(Filters.text & ~Filters.command, tarifas_set_valor)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'^(Cancelar|Volver al menu)$'), cancel_por_texto),
    ],
)


def mi_admin(update, context):
    user_db_id = get_user_db_id_from_update(update)

    # Validar que sea admin local registrado
    admin = None
    admin = get_admin_by_user_id(user_db_id)
 
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

    header = (
        "Panel Administrador Local\n\n"
        f"Estado: {status}\n"
        f"Equipo: {team_name}\n"
        f"Código de equipo: {team_code}\n"
        "Compártelo a tus repartidores para que soliciten unirse a tu equipo.\n\n"
    )

    # Administrador de Plataforma: siempre operativo
    if team_code == "PLATFORM":
        keyboard = [
            [InlineKeyboardButton("⏳ Repartidores pendientes (mi equipo)", callback_data=f"local_couriers_pending_{admin_id}")],
            [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
        ]
        update.message.reply_text(
            header +
            "Como Administrador de Plataforma, tu operación está habilitada.\n"
            "Selecciona una opción:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # FASE 1: Mostrar estado del equipo como información, NO como bloqueo
    ok, msg, total, okb = admin_puede_operar(admin_id)

    # Construir mensaje de estado (sin bloquear)
    estado_msg = (
        f"📊 Estado del equipo:\n"
        f"• Repartidores vinculados: {total}\n"
        f"• Con saldo >= 5000: {okb}\n\n"
    )

    # En FASE 1: panel siempre habilitado
    keyboard = [
        [InlineKeyboardButton("⏳ Repartidores pendientes (mi equipo)", callback_data=f"local_couriers_pending_{admin_id}")],
        [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
        [InlineKeyboardButton("🔄 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
    ]

    update.message.reply_text(
        header + estado_msg +
        "Panel de administración habilitado.\n"
        "Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def mi_perfil(update, context):
    """
    Muestra perfil consolidado del usuario: roles, estados, equipos, fecha de registro.
    """
    def get_status_icon(status):
        """Retorna ícono según estado."""
        if status == "APPROVED":
            return "🟢 "
        if status == "PENDING":
            return "🟡 "
        if status in ("REJECTED", "INACTIVE"):
            return "🔴 "
        return ""

    telegram_id = update.effective_user.id
    user_db_id = get_user_db_id_from_update(update)

    # Obtener datos base del usuario (con created_at)
    user = get_user_by_id(user_db_id)
    if not user:
        update.message.reply_text("No se encontró tu usuario en la base de datos.")
        return

    # Acceso por nombre (sqlite3.Row)
    username = user["username"] if user["username"] else "-"
    fecha_registro = user["created_at"] if user["created_at"] else "(no disponible)"

    # Encabezado
    mensaje = "👤 MI PERFIL\n\n"
    mensaje += f"📱 Telegram ID: {telegram_id}\n"
    mensaje += f"👤 Usuario: {'@' + username if username != '-' else '(sin username)'}\n"
    mensaje += f"📅 Fecha de registro: {fecha_registro}\n\n"

    # ===== ROLES Y ESTADOS =====
    mensaje += "📋 ROLES Y ESTADO\n\n"

    # Admin
    admin = get_admin_by_user_id(user_db_id)
    if admin:
        admin_id = admin["id"]
        admin_full = get_admin_by_id(admin_id)

        # Acceso por nombre (sqlite3.Row) - sin índices mágicos
        full_name = admin_full["full_name"] if admin_full["full_name"] else "-"
        phone = admin_full["phone"] if admin_full["phone"] else "-"
        status = admin_full["status"] if admin_full["status"] else "PENDING"
        team_name = admin_full["team_name"] if admin_full["team_name"] else "-"
        team_code = admin_full["team_code"] if admin_full["team_code"] else "-"

        # Construir línea de equipo (agrupar nombre y código)
        if team_name != "-" and team_code != "-":
            equipo_admin = f"{team_name} ({team_code})"
        elif team_name != "-":
            equipo_admin = team_name
        elif team_code != "-":
            equipo_admin = team_code
        else:
            equipo_admin = "-"

        mensaje += f"🔧 Administrador Local\n"
        mensaje += f"   Nombre: {full_name}\n"
        mensaje += f"   Teléfono: {phone}\n"
        mensaje += f"   Estado: {get_status_icon(status)}{status}\n"
        mensaje += f"   Equipo: {equipo_admin}\n\n"

    # Aliado
    ally = get_ally_by_user_id(user_db_id)
    if ally:
        ally_id = ally["id"]

        # Acceso por nombre (sqlite3.Row) - sin índices mágicos
        business_name = ally["business_name"] if ally["business_name"] else "-"
        phone = ally["phone"] if ally["phone"] else "-"
        status = ally["status"] if ally["status"] else "PENDING"

        # Buscar equipo vinculado
        admin_link = get_admin_link_for_ally(ally_id)
        equipo_info = "(sin equipo)"
        if admin_link:
            # Acceso por nombre (sqlite3.Row) - sin índices mágicos
            team_name = admin_link["team_name"] if admin_link["team_name"] else "-"
            team_code = admin_link["team_code"] if admin_link["team_code"] else "-"
            link_status = admin_link["link_status"] if admin_link["link_status"] else "-"
            equipo_info = f"{team_name} ({team_code}) - Vínculo: {link_status}"

        mensaje += f"🍕 Aliado\n"
        mensaje += f"   Negocio: {business_name}\n"
        mensaje += f"   Teléfono: {phone}\n"
        mensaje += f"   Estado: {get_status_icon(status)}{status}\n"
        mensaje += f"   Equipo: {equipo_info}\n\n"

    # Repartidor
    courier = get_courier_by_user_id(user_db_id)
    if courier:
        courier_id = courier["id"]

        # Acceso por nombre (sqlite3.Row) - sin índices mágicos
        full_name = courier["full_name"] if courier["full_name"] else "-"
        code = courier["code"] if courier["code"] else "-"
        status = courier["status"] if courier["status"] else "PENDING"

        # Buscar equipo vinculado
        admin_link = get_admin_link_for_courier(courier_id)
        equipo_info = "(sin equipo)"
        if admin_link:
            # Acceso por nombre (sqlite3.Row) - sin índices mágicos
            team_name = admin_link["team_name"] if admin_link["team_name"] else "-"
            team_code = admin_link["team_code"] if admin_link["team_code"] else "-"
            link_status = admin_link["link_status"] if admin_link["link_status"] else "-"
            equipo_info = f"{team_name} ({team_code}) - Vínculo: {link_status}"

        mensaje += f"🚴 Repartidor\n"
        mensaje += f"   Nombre: {full_name}\n"
        mensaje += f"   Código interno: {code if code else 'sin asignar'}\n"
        mensaje += f"   Estado: {get_status_icon(status)}{status}\n"
        mensaje += f"   Equipo: {equipo_info}\n\n"

    # Si no tiene roles
    if not admin and not ally and not courier:
        mensaje += "   (Sin roles registrados)\n\n"

    # ===== ESTADO OPERATIVO =====
    mensaje += "📊 ESTADO OPERATIVO\n\n"

    # Pedidos
    if ally:
        ally_status = ally["status"] if ally["status"] else "PENDING"
        if ally_status == "APPROVED":
            mensaje += f"{get_status_icon(ally_status)}Pedidos: Habilitados\n"
        else:
            mensaje += f"{get_status_icon(ally_status)}Pedidos: No habilitados\n"
    else:
        mensaje += "❌ Pedidos: Requiere rol Aliado\n"

    # Admin
    if admin:
        admin_status = admin_full["status"] if admin_full["status"] else "PENDING"
        if admin_status == "APPROVED":
            mensaje += f"{get_status_icon(admin_status)}Admin: Aprobado\n"
        elif admin_status == "PENDING":
            mensaje += f"{get_status_icon(admin_status)}Admin: Pendiente de aprobación\n"
        else:
            mensaje += f"{get_status_icon(admin_status)}Admin: {admin_status}\n"

    # Repartidor
    if courier:
        courier_status = courier["status"] if courier["status"] else "PENDING"
        if courier_status == "APPROVED":
            mensaje += f"{get_status_icon(courier_status)}Repartidor: Activo\n"
        elif courier_status == "PENDING":
            mensaje += f"{get_status_icon(courier_status)}Repartidor: Pendiente\n"
        else:
            mensaje += f"{get_status_icon(courier_status)}Repartidor: No activo\n"

    mensaje += "\n"

    # ===== ACCIONES RÁPIDAS =====
    mensaje += "⚡ ACCIONES RÁPIDAS\n\n"
    mensaje += "• /menu - Ver menú principal\n"

    if admin:
        mensaje += "• /mi_admin - Panel de administrador\n"

    if ally and status == "APPROVED":
        mensaje += "• /nuevo_pedido - Crear pedido\n"

    update.message.reply_text(mensaje)


def admin_local_callback(update, context):
    query = update.callback_query
    if not query:
        return
    data = query.data
    query.answer()

    user_db_id = get_user_db_id_from_update(update)

    admin = get_admin_by_user_id(user_db_id)
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
        admin_full = get_admin_by_id(admin_id)
        status = admin_full[6]
        team_code = "-"
        if isinstance(admin_full, dict):
            team_code = admin_full.get("team_code") or "-"
        else:
            team_code = admin_full[10] if len(admin_full) > 10 and admin_full[10] else "-"

        # Administrador de Plataforma: siempre operativo
        if team_code == "PLATFORM":
            keyboard = [
                [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            ]
            query.edit_message_text(
                "Panel Administrador Local\n\n"
                "Como Administrador de Plataforma, tu operación está habilitada.\n"
                "Selecciona una opción:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # FASE 1: Mostrar requisitos como información, NO como bloqueo
        ok, msg, total, okb = admin_puede_operar(admin_id)

        estado_msg = (
            f"📊 Estado del equipo:\n"
            f"• Repartidores vinculados: {total}\n"
            f"• Con saldo >= 5000: {okb}\n\n"
        )

        keyboard = [
            [InlineKeyboardButton("⏳ Repartidores pendientes", callback_data=f"local_couriers_pending_{admin_id}")],
            [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            [InlineKeyboardButton("🔄 Verificar de nuevo", callback_data=f"local_check_{admin_id}")],
        ]
        query.edit_message_text(
            "Panel Administrador Local\n\n"
            f"Estado: {status}\n\n"
            + estado_msg +
            "Panel habilitado. Selecciona una opción:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("local_status_"):
        admin_full = get_admin_by_id(admin_id)
        status = admin_full[6]
        team_code = "-"
        if isinstance(admin_full, dict):
            team_code = admin_full.get("team_code") or "-"
        else:
            team_code = admin_full[10] if len(admin_full) > 10 and admin_full[10] else "-"

        # Administrador de Plataforma: mensaje especial
        if team_code == "PLATFORM":
            total = count_admin_couriers(admin_id)
            texto = (
                "Estado de tu cuenta (Admin Plataforma):\n\n"
                f"Estado: {status}\n"
                f"Repartidores vinculados: {total}\n\n"
                "Como Administrador de Plataforma, tu operación está habilitada."
            )
            keyboard = []
            query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)
            return

        # Administrador Local normal: mostrar requisitos
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
            update_admin_courier_status(admin_id, courier_id, "INACTIVE")
        except Exception as e:
            print("[ERROR] update_admin_courier_status INACTIVE:", e)
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

    telegram_id = update.effective_user.id
    es_admin_plataforma = (telegram_id == ADMIN_USER_ID)

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
    user_tg_id = update.effective_user.id

    # es_admin debe validar por telegram_id (consistente con callbacks)
    if not es_admin(user_tg_id):
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

        status = ally[8]
        keyboard = []

        if status == "APPROVED":
            keyboard.append([
                InlineKeyboardButton(
                    "⛔ Desactivar",
                    callback_data="config_ally_disable_{}".format(ally_id)
                )
            ])
        elif status == "INACTIVE":
            keyboard.append([
                InlineKeyboardButton(
                    "✅ Activar",
                    callback_data="config_ally_enable_{}".format(ally_id)
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
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

        # Estado actual del repartidor
        status = courier[10]

        keyboard = []

        # Solo mostramos la acción coherente según estado
        if status == "APPROVED":
            keyboard.append([
                InlineKeyboardButton(
                    "⛔ Desactivar repartidor",
                    callback_data="config_courier_disable_{}".format(courier_id)
                )
            ])
        elif status == "INACTIVE":
            keyboard.append([
                InlineKeyboardButton(
                    "✅ Activar repartidor",
                    callback_data="config_courier_enable_{}".format(courier_id)
                )
            ])

        # Siempre permitir volver
        keyboard.append([
            InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")
        ])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
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

    if data.startswith("config_courier_disable_"):
        courier_id = int(data.split("_")[-1])
        update_courier_status_by_id(courier_id, "INACTIVE")
        query.edit_message_text("Repartidor desactivado (INACTIVE).")
        return

    if data.startswith("config_courier_enable_"):
        courier_id = int(data.split("_")[-1])
        update_courier_status_by_id(courier_id, "APPROVED")
        query.edit_message_text("Repartidor activado (APPROVED).")
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
    init_db()
    force_platform_admin(ADMIN_USER_ID)
    ensure_pricing_defaults()

    if not BOT_TOKEN:
        raise RuntimeError("Falta BOT_TOKEN en variables de entorno.")

    # Log seguro: fingerprint del token para verificar separación DEV/PROD
    token_hash = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:8]
    token_suffix = BOT_TOKEN[-6:] if len(BOT_TOKEN) >= 6 else "***"
    print(f"[BOT] TOKEN fingerprint: hash={token_hash} suffix=...{token_suffix}")
    print(f"[BOT] Ambiente: {ENV}")

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

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
    dp.add_handler(CommandHandler("mi_perfil", mi_perfil))
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

    # Configuracion de tarifas (botones pricing_*)
    dp.add_handler(CallbackQueryHandler(tarifas_edit_callback, pattern=r"^pricing_"))


    # -------------------------
    # Conversaciones completas
    # -------------------------
    dp.add_handler(ally_conv)          # /soy_aliado
    dp.add_handler(courier_conv)       # /soy_repartidor
    dp.add_handler(nuevo_pedido_conv)  # /nuevo_pedido
    dp.add_handler(CallbackQueryHandler(preview_callback, pattern=r"^preview_"))  # preview oferta
    dp.add_handler(clientes_conv)      # /clientes (agenda de clientes)
    dp.add_handler(cotizar_conv)       # /cotizar
    dp.add_handler(tarifas_conv)       # /tarifas (Admin Plataforma)
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
        fallbacks=[
            CommandHandler("cancel", cancel_conversacion),
            MessageHandler(Filters.regex(r'^(Cancelar|Volver al menu)$'), cancel_por_texto),
        ],
    )
    dp.add_handler(admin_conv)

    # -------------------------
    # Handler para botones del menú principal (ReplyKeyboard)
    # -------------------------
    dp.add_handler(MessageHandler(
        Filters.regex(r'^(Mis pedidos|Mi perfil|Ayuda|Menu)$'),
        menu_button_handler
    ))

    # Handler global para "Cancelar" y "Volver al menu" (fuera de conversaciones)
    dp.add_handler(MessageHandler(
        Filters.regex(r'^(Cancelar|Volver al menu)$'),
        volver_menu_global
    ))

    # -------------------------
    # Notificación de arranque al Administrador de Plataforma (opcional)
    # -------------------------
    if ADMIN_USER_ID:
        try:
            updater.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text="Bot iniciado correctamente."
            )
        except Exception as e:
         print(f"[WARN] No se pudo notificar al admin: {e}")
    else:
        print("[INFO] ADMIN_USER_ID=0, se omite notificación.")


    # Iniciar el bot
    updater.start_polling(drop_pending_updates=True)
    print("[BOOT] Polling iniciado. Bot activo.")
    updater.idle()


if __name__ == "__main__":
    main()
