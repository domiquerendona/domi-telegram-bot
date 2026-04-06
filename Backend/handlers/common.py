import logging
logger = logging.getLogger(__name__)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Filters, ConversationHandler

from services import (
    get_user_db_id_from_update,
    get_ally_by_user_id,
    get_courier_by_user_id,
    get_admin_by_user_id,
    es_admin_plataforma,
    _get_missing_role_commands,
    resolve_location,
    resolve_location_next,
    _get_important_alert_config,
    get_active_terms_version,
    has_accepted_terms,
    save_terms_acceptance,
    save_terms_session_ack,
)

from handlers.states import (
    FLOW_PREVIOUS_STATE,
    FLOW_STATE_ORDER,
    FLOW_STATE_KEYS,
    ALLY_NAME,
    ALLY_OWNER,
    ALLY_DOCUMENT,
    ALLY_PHONE,
    ALLY_CITY,
    ALLY_BARRIO,
    ALLY_UBICACION,
    ALLY_CONFIRM,
    ALLY_TEAM,
    COURIER_FULLNAME,
    COURIER_IDNUMBER,
    COURIER_PHONE,
    COURIER_CITY,
    COURIER_BARRIO,
    COURIER_RESIDENCE_LOCATION,
    COURIER_PLATE,
    COURIER_BIKETYPE,
    COURIER_CEDULA_FRONT,
    COURIER_CEDULA_BACK,
    COURIER_SELFIE,
    COURIER_CONFIRM,
    COURIER_TEAM,
    LOCAL_ADMIN_NAME,
    LOCAL_ADMIN_DOCUMENT,
    LOCAL_ADMIN_TEAMNAME,
    LOCAL_ADMIN_PHONE,
    LOCAL_ADMIN_CITY,
    LOCAL_ADMIN_BARRIO,
    LOCAL_ADMIN_RESIDENCE_LOCATION,
    LOCAL_ADMIN_CEDULA_FRONT,
    LOCAL_ADMIN_CEDULA_BACK,
    LOCAL_ADMIN_SELFIE,
    LOCAL_ADMIN_CONFIRM,
)


def _set_flow_step(context, flow, step):
    context.user_data["_back_flow"] = flow
    context.user_data["_back_step"] = step


def _debug_admin_registration_state(context, step, **extra):
    data = context.user_data or {}
    snapshot = {
        "admin_name": bool((data.get("admin_name") or "").strip()),
        "admin_document": bool((data.get("admin_document") or "").strip()),
        "admin_team_name": bool((data.get("admin_team_name") or "").strip()),
        "phone": bool((data.get("phone") or "").strip()),
        "admin_city": bool((data.get("admin_city") or "").strip()),
        "admin_barrio": bool((data.get("admin_barrio") or "").strip()),
        "admin_residence_address": bool((data.get("admin_residence_address") or "").strip()),
        "admin_residence_lat": data.get("admin_residence_lat") is not None,
        "admin_residence_lng": data.get("admin_residence_lng") is not None,
        "admin_cedula_front_file_id": bool(data.get("admin_cedula_front_file_id")),
        "admin_cedula_back_file_id": bool(data.get("admin_cedula_back_file_id")),
        "admin_selfie_file_id": bool(data.get("admin_selfie_file_id")),
        "_back_step": data.get("_back_step"),
    }
    logger.debug("[admin_reg] step=%s snapshot=%s extra=%s", step, snapshot, extra)


_OPTIONS_HINT = (
    "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
)

# Regex y filtro compartido para todos los botones de navegación del menú.
# Nota: cualquier texto que coincida NO será consumido como input en estados de conversación.
# Al llegar al fallback de una conversación, cancela la conversación limpiamente.
CANCELAR_VOLVER_MENU_REGEX = (
    r'(?i)^\s*[\W_]*\s*('
    # Cancelación explícita
    r'cancelar|volver al men[uú]|men[uú]'
    # Saldos
    r'|mi saldo repartidor|mi saldo aliado'
    # Menú principal
    r'|mi aliado|mi repartidor(?:\s*[·\u00b7]\s*(?:online|offline))?|mi admin|admin plataforma'
    r'|mi perfil|ayuda|actualizar men[uú]'
    # Submenú aliado (no entry-points de conversación)
    r'|mis pedidos|mis repartidores|mis solicitudes'
    r'|mi enlace de pedidos|mi suscripci[oó]n'
    # Submenú repartidor
    r'|activar repartidor|desactivarme|actualizar'
    r'|pedidos en curso|mis pedidos repartidor|mis ganancias'
    r'|recargar repartidor'
    r')\s*$'
)
CANCELAR_VOLVER_MENU_FILTER = Filters.regex(CANCELAR_VOLVER_MENU_REGEX)


def _handle_phone_input(update, context, storage_key, current_state, next_state, flow, next_prompt):
    """Helper para validar y almacenar teléfono en flujos de registro."""
    phone = (update.message.text or "").strip()
    digits = "".join([c for c in phone if c.isdigit()])
    if len(digits) < 7:
        update.message.reply_text(
            "Ese teléfono no parece válido. Escríbelo de nuevo, por favor." + _OPTIONS_HINT
        )
        return current_state
    context.user_data[storage_key] = phone
    update.message.reply_text(next_prompt + _OPTIONS_HINT)
    _set_flow_step(context, flow, next_state)
    return next_state


def _handle_text_field_input(
    update,
    context,
    error_msg,
    storage_key,
    current_state,
    next_state,
    flow,
    next_prompt,
    options_hint=_OPTIONS_HINT,
    set_back_step=True,
):
    """Helper para validar y almacenar campos de texto simple."""
    texto = (update.message.text or "").strip()
    if not texto:
        update.message.reply_text(error_msg + (options_hint or ""))
        return current_state
    context.user_data[storage_key] = texto
    if next_prompt is not None:
        update.message.reply_text(next_prompt + (options_hint or ""))
    if set_back_step:
        _set_flow_step(context, flow, next_state)
    return next_state


def _clear_flow_data_from_state(context, flow, target_state):
    states = FLOW_STATE_ORDER.get(flow, [])
    if target_state not in states:
        return
    start_idx = states.index(target_state)
    for state in states[start_idx:]:
        for key in FLOW_STATE_KEYS.get(flow, {}).get(state, []):
            context.user_data.pop(key, None)


def _send_back_prompt(update, flow, state):
    prompts = {
        "ally": {
            ALLY_NAME: "Registro de aliado\n\nEscribe el nombre del negocio:",
            ALLY_OWNER: "Escribe el nombre del dueño o administrador:",
            ALLY_DOCUMENT: "Escribe el número de cédula del dueño o representante:",
            ALLY_PHONE: "Escribe el teléfono de contacto del negocio:",
            ALLY_CITY: "Escribe la ciudad del negocio:",
            ALLY_BARRIO: "Escribe el barrio del negocio:",
            ALLY_UBICACION: (
                "Ubicacion del negocio\n\n"
                "Escribe la direccion exacta (ej: Cra 15 #23-45, Barrio Cuba) "
                "o envia un pin de Telegram."
            ),
            ALLY_CONFIRM: "Escribe SI para confirmar tu registro.",
        },
        "courier": {
            COURIER_FULLNAME: "Registro de repartidor\n\nEscribe tu nombre completo:",
            COURIER_IDNUMBER: "Escribe tu número de identificación:",
            COURIER_PHONE: "Escribe tu número de celular:",
            COURIER_CITY: "Escribe la ciudad donde trabajas:",
            COURIER_BARRIO: "Escribe el barrio o sector principal donde trabajas:",
            COURIER_RESIDENCE_LOCATION: (
                "Direccion de residencia\n\n"
                "Por seguridad registramos donde vives. "
                "Solo el equipo administrativo tiene acceso a este dato.\n\n"
                "Escribe tu direccion completa (ej: Cra 15 #23-45, Barrio Cuba) "
                "o envia un pin de Telegram."
            ),
            COURIER_PLATE: "Escribe la placa de tu moto (o 'ninguna'):",
            COURIER_BIKETYPE: "Escribe el tipo de moto:",
            COURIER_CEDULA_FRONT: "Envía una foto del frente de tu cédula:",
            COURIER_CEDULA_BACK: "Envía una foto del reverso de tu cédula:",
            COURIER_SELFIE: "Envía una foto de tu cara (selfie):",
            COURIER_CONFIRM: "Escribe SI para confirmar tu registro.",
        },
        "admin": {
            LOCAL_ADMIN_NAME: "Registro de Administrador Local.\nEscribe tu nombre completo:",
            LOCAL_ADMIN_DOCUMENT: "Escribe tu número de documento:",
            LOCAL_ADMIN_TEAMNAME: "Escribe el nombre de tu administración (equipo):",
            LOCAL_ADMIN_PHONE: "Escribe tu número de teléfono:",
            LOCAL_ADMIN_CITY: "¿En qué ciudad vas a operar como Administrador Local?",
            LOCAL_ADMIN_BARRIO: "Escribe tu barrio o zona base de operación:",
            LOCAL_ADMIN_RESIDENCE_LOCATION: (
                "Direccion de residencia\n\n"
                "Por seguridad registramos donde vives. "
                "Solo el equipo administrativo tiene acceso a este dato.\n\n"
                "Escribe tu direccion completa (ej: Cra 15 #23-45, Barrio Cuba) "
                "o envia un pin de Telegram."
            ),
            LOCAL_ADMIN_CEDULA_FRONT: "Envía una foto del frente de tu cédula:",
            LOCAL_ADMIN_CEDULA_BACK: "Envía una foto del reverso de tu cédula:",
            LOCAL_ADMIN_SELFIE: "Envía una foto de tu cara (selfie):",
            LOCAL_ADMIN_CONFIRM: "Escribe ACEPTAR para finalizar o volver para corregir.",
        },
    }
    msg = prompts.get(flow, {}).get(state)
    if msg:
        update.message.reply_text(msg)
    else:
        update.message.reply_text("Escribe el dato solicitado o usa /cancel para salir.")


def volver_paso_anterior(update, context):
    flow = context.user_data.get("_back_flow")
    current_state = context.user_data.get("_back_step")
    if not flow or current_state is None:
        update.message.reply_text("No hay un paso anterior disponible en este flujo.")
        return ConversationHandler.END

    previous_state = FLOW_PREVIOUS_STATE.get(flow, {}).get(current_state)
    if previous_state is None:
        update.message.reply_text("Ya estás en el primer paso. Escribe el dato o usa /cancel.")
        return current_state

    # En TEAM ya existe registro persistido; permitir volver sería riesgoso.
    if flow == "courier" and current_state == COURIER_TEAM:
        update.message.reply_text(
            "Aquí no se permite volver atrás porque el registro ya se guardó.\n"
            "Selecciona un equipo para terminar."
        )
        return current_state

    if flow == "ally" and current_state == ALLY_TEAM:
        update.message.reply_text(
            "Aquí no se permite volver atrás porque el registro ya se guardó.\n"
            "Selecciona un equipo para terminar."
        )
        return current_state

    _clear_flow_data_from_state(context, flow, previous_state)
    _set_flow_step(context, flow, previous_state)
    _send_back_prompt(update, flow, previous_state)
    return previous_state


# ---------- HELPERS DE LECTURA DE FILAS ----------

def _row_value(row, key, default=None):
    """Lee un campo desde dict/sqlite3.Row de forma segura."""
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        return default


# ---------- TECLADOS DE MENÚ ----------

def _get_courier_toggle_button_label(courier):
    """Retorna el texto del boton de estado para repartidor APPROVED."""
    if not courier or _row_value(courier, "status") != "APPROVED":
        return None
    courier_is_active = _row_value(courier, "is_active", 0)
    if courier_is_active:
        return "Desactivarme"
    return "Activar repartidor"


def _courier_main_button_label(courier):
    """Retorna el label del boton Mi repartidor con estado inline."""
    if not courier or _row_value(courier, "status") != "APPROVED":
        return None
    is_active = int(_row_value(courier, "is_active", 0) or 0)
    avail_status = _row_value(courier, "availability_status", "INACTIVE")
    live_active = int(_row_value(courier, "live_location_active", 0) or 0)
    if is_active and avail_status == "APPROVED" and live_active:
        return "Mi repartidor · ONLINE"
    return "Mi repartidor · OFFLINE"


def get_main_menu_keyboard(missing_cmds, courier=None, ally=None, admin_local=None, is_platform_admin: bool = False):
    """Retorna el teclado principal para usuarios fuera de flujos."""
    keyboard = []
    role_row = []
    if ally and ally["status"] == "APPROVED" and "/soy_aliado" not in missing_cmds:
        role_row.append('Mi aliado')
    courier_btn = _courier_main_button_label(courier)
    if courier_btn and "/soy_repartidor" not in missing_cmds:
        role_row.append(courier_btn)
    if admin_local and "/soy_admin" not in missing_cmds:
        role_row.append('Mi admin')
    if is_platform_admin:
        role_row.append('Admin plataforma')
    if role_row:
        keyboard.append(role_row)
    keyboard.append(['Mi perfil', 'Ayuda'])
    keyboard.append(['Menu', 'Actualizar menu'])
    if missing_cmds:
        if len(missing_cmds) == 1:
            register_rows = [missing_cmds]
        elif len(missing_cmds) == 2:
            register_rows = [missing_cmds]
        else:
            register_rows = [missing_cmds[:2], missing_cmds[2:]]
        keyboard = register_rows + keyboard
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_flow_menu_keyboard():
    """Retorna el teclado reducido para usuarios dentro de flujos."""
    keyboard = [
        ['Cancelar', 'Volver al menu']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_ally_menu_keyboard():
    """Retorna el teclado de seccion Aliado."""
    keyboard = [
        ['Nuevo pedido', 'Nueva ruta'],
        ['Mis pedidos', 'Agenda'],
        ['Cotizar envio', 'Recargar'],
        ['Mis repartidores', 'Mi saldo aliado'],
        ['Mis clientes', 'Mis solicitudes'],
        ['Mi enlace de pedidos', 'Mi suscripcion'],
        ['Volver al menu'],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_repartidor_menu_keyboard(courier):
    """Retorna el teclado de seccion Repartidor."""
    courier_toggle = _get_courier_toggle_button_label(courier)
    keyboard = []
    if courier_toggle:
        keyboard.append([courier_toggle])
    keyboard.append(['Pedidos en curso', 'Actualizar'])
    keyboard.append(['Mis pedidos repartidor', 'Mis ganancias'])
    keyboard.append(['Recargar repartidor', 'Mi saldo repartidor'])
    keyboard.append(['Volver al menu'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------- HELPERS DE MENÚ ----------

def _get_chat_id(update):
    """Extrae chat_id de forma robusta desde update."""
    if getattr(update, "callback_query", None) and update.callback_query.message:
        return update.callback_query.message.chat_id
    if getattr(update, "message", None):
        return update.message.chat_id
    return None


def _get_user_roles(update):
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    courier = get_courier_by_user_id(user_db_id)
    admin_local = None
    try:
        admin_local = get_admin_by_user_id(user_db_id)
    except Exception as e:
        logger.warning("ERROR get_admin_by_user_id en menu: %s", e)
        admin_local = None
    return ally, courier, admin_local


def show_main_menu(update, context, text="Menu principal. Selecciona una opcion:"):
    """Muestra el menú principal completo."""
    ally, courier, admin_local = _get_user_roles(update)
    es_admin_plataforma_flag = es_admin_plataforma(update.effective_user.id)
    missing_cmds = _get_missing_role_commands(ally, courier, admin_local, es_admin_plataforma_flag)
    reply_markup = get_main_menu_keyboard(missing_cmds, courier, ally, admin_local, es_admin_plataforma_flag)
    chat_id = _get_chat_id(update)
    if chat_id:
        context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def show_flow_menu(update, context, text):
    """Muestra el menú reducido para flujos activos."""
    reply_markup = get_flow_menu_keyboard()
    chat_id = _get_chat_id(update)
    if chat_id and text:
        context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


# ---------- CANCEL HANDLERS (usados en fallbacks de ConversationHandler) ----------

def cancel_conversacion(update, context):
    """Cierra cualquier conversación activa y muestra menú principal."""
    try:
        context.user_data.clear()
    except Exception:
        pass
    if getattr(update, "callback_query", None):
        q = update.callback_query
        q.answer()
        q.edit_message_text("Proceso cancelado.")
    else:
        update.message.reply_text("Proceso cancelado.")
    show_main_menu(update, context, "Menu principal. Selecciona una opcion:")
    return ConversationHandler.END


def cancel_por_texto(update, context):
    """Handler para cuando el usuario escribe 'Cancelar' o 'Volver al menu'."""
    return cancel_conversacion(update, context)


# ---------- RESOLVER UBICACIÓN (compartido entre ally_locs, cotizador, pedido) ----------

def _cotizar_resolver_ubicacion(update, context):
    """Resuelve ubicacion desde texto o PIN de Telegram. Retorna dict o None."""
    if update.message.location:
        loc = update.message.location
        return {"lat": loc.latitude, "lng": loc.longitude, "method": "gps"}
    texto = (update.message.text or "").strip()
    if not texto:
        return None
    return resolve_location(texto)


def _mostrar_confirmacion_geocode(
    message,
    context,
    geo,
    original_text,
    cb_si,
    cb_no,
    header_text=None,
    question_text="Es correcta?",
    seen_ids=None,
    formatted_storage_key=None,
):
    """Muestra una ubicacion candidata con pin, link de Maps y botones de confirmacion.
    geo: dict con lat, lng, formatted_address/address/label y place_id.
    original_text: texto original del usuario (para carga perezosa del siguiente candidato)."""
    lat = geo["lat"]
    lng = geo["lng"]
    formatted_address = (
        geo.get("formatted_address")
        or geo.get("address")
        or geo.get("label")
        or ""
    )
    _pid = geo.get("place_id") or f"{lat},{lng}"
    if formatted_storage_key:
        if formatted_address:
            context.user_data[formatted_storage_key] = formatted_address
        else:
            context.user_data.pop(formatted_storage_key, None)
    context.user_data["pending_geo_lat"] = lat
    context.user_data["pending_geo_lng"] = lng
    context.user_data["pending_geo_text"] = original_text
    context.user_data["pending_geo_seen"] = list(seen_ids) if seen_ids is not None else [_pid]
    # city_hint: si ya hay uno guardado de la llamada inicial, lo conservamos.
    # El caller puede haber guardado "pending_geo_city_hint" antes de llamar a _mostrar_confirmacion_geocode.
    message.reply_location(latitude=lat, longitude=lng)
    maps_link = f"https://maps.google.com/?q={lat},{lng}"
    keyboard = [[
        InlineKeyboardButton("Si, usar esta ubicacion", callback_data=cb_si),
        InlineKeyboardButton("No, esta no es", callback_data=cb_no),
    ]]
    text_parts = [header_text or "Encontre esta ubicacion:"]
    if formatted_address:
        text_parts.append(formatted_address)
    text_parts.append(f"Ver en mapa: {maps_link}")
    text_parts.append(question_text)
    message.reply_text("\n\n".join(text_parts), reply_markup=InlineKeyboardMarkup(keyboard))


def _geo_siguiente_o_gps(
    query,
    context,
    cb_si,
    cb_no,
    estado,
    header_text="Otra opcion:",
    question_text="Es correcta?",
    no_more_text=None,
    formatted_storage_key=None,
):
    """Busca el siguiente candidato de geocoding (carga perezosa) o pide GPS si no hay mas."""
    original_text = context.user_data.get("pending_geo_text", "")
    seen = context.user_data.get("pending_geo_seen", [])
    city_hint = context.user_data.get("pending_geo_city_hint")
    next_geo = resolve_location_next(original_text, seen, city_hint=city_hint) if original_text else None
    if next_geo:
        _pid = next_geo.get("place_id") or f"{next_geo['lat']},{next_geo['lng']}"
        seen.append(_pid)
        query.edit_message_text("Buscando otra opcion...")
        _mostrar_confirmacion_geocode(
            query.message,
            context,
            next_geo,
            original_text,
            cb_si,
            cb_no,
            header_text=header_text,
            question_text=question_text,
            seen_ids=seen,
            formatted_storage_key=formatted_storage_key,
        )
    else:
        context.user_data.pop("pending_geo_lat", None)
        context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        context.user_data.pop("pending_geo_city_hint", None)
        if formatted_storage_key:
            context.user_data.pop(formatted_storage_key, None)
        query.edit_message_text(
            no_more_text
            or (
                "No encontre mas opciones.\n\n"
                "Prueba una de estas formas para continuar:\n"
                "- Envia un PIN de ubicacion de Telegram\n"
                "- Pega un link de Google Maps con coordenadas\n"
                "- Escribe coordenadas directas (ej: 4.81,-75.69)\n"
                "- Escribe una direccion con ciudad"
            )
        )
    return estado


def _important_alert_job(context):
    data = context.job.context or {}
    alert_key = data.get("alert_key")
    if not alert_key:
        return
    if not context.bot_data.get("important_alert_open:{}".format(alert_key), False):
        return
    chat_id = data.get("chat_id")
    text = data.get("text")
    if not chat_id or not text:
        return
    reply_markup = data.get("reply_markup")
    try:
        context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    except Exception as e:
        logger.warning("No se pudo enviar recordatorio importante %s: %s", alert_key, e)


def _schedule_important_alerts(context, alert_key, chat_id, reminder_text, reply_markup=None):
    config = _get_important_alert_config()
    if not config["enabled"]:
        return
    context.bot_data["important_alert_open:{}".format(alert_key)] = True
    for idx, sec in enumerate(config["seconds"], start=1):
        context.job_queue.run_once(
            _important_alert_job,
            when=sec,
            context={
                "alert_key": alert_key,
                "chat_id": chat_id,
                "text": reminder_text,
                "reply_markup": reply_markup,
            },
            name="important_alert_{}_{}".format(alert_key, idx),
        )


def _resolve_important_alert(context, alert_key):
    context.bot_data["important_alert_open:{}".format(alert_key)] = False
    config = _get_important_alert_config()
    for idx in range(1, len(config["seconds"]) + 1):
        jobs = context.job_queue.get_jobs_by_name("important_alert_{}_{}".format(alert_key, idx))
        for job in jobs:
            try:
                job.schedule_removal()
            except Exception:
                pass


def _build_role_welcome_message(role: str, profile=None, bonus_granted: bool = False, reactivated: bool = False) -> str:
    role = (role or "").strip().upper()
    team_name = "-"
    if isinstance(profile, dict):
        team_name = profile.get("team_name") or "-"

    if role == "ADMIN_LOCAL":
        opening = (
            "Bienvenido a Domiquerendona. Tu cuenta de Administrador Local fue reactivada.\n\n"
            if reactivated else
            "Bienvenido a Domiquerendona. Tu cuenta de Administrador Local fue aprobada.\n\n"
        )
        return (
            opening
            + "Primeros pasos para operar:\n"
            + "1. Usa /mi_admin para revisar tu panel, estado operativo y pendientes.\n"
            + "2. Usa /configurar_pagos para dejar tus datos de pago al dia.\n"
            + "3. Usa /recargas_pendientes para gestionar solicitudes cuando ya estes operando.\n"
            + "4. Tu equipo actual es '{}'. Antes de operar debes cumplir los requisitos: 5 aliados con saldo >= 5000, 10 repartidores con saldo >= 5000 y saldo master >= 60000.\n\n".format(team_name)
            + "Usa /menu para ver todas tus opciones."
        )

    if role == "ALLY":
        opening = (
            "Bienvenido a Domiquerendona. Tu negocio fue reactivado.\n\n"
            if reactivated else
            "Bienvenido a Domiquerendona. Tu negocio fue aprobado.\n\n"
        )
        bonus_line = ""
        if bonus_granted:
            bonus_line = "Recibiste $5.000 de saldo de bienvenida para crear tu primer pedido.\n\n"
        return (
            opening
            + bonus_line
            + "Primeros pasos para operar:\n"
            + "1. Usa /menu y entra a [Mi aliado].\n"
            + "2. Crea tu primer pedido con /nuevo_pedido.\n"
            + "3. Usa /agenda para guardar clientes y direcciones frecuentes.\n"
            + "4. Usa /recargar cuando necesites saldo adicional.\n\n"
            + "Usa /menu para ver todas tus opciones."
        )

    if role == "COURIER":
        opening = (
            "Bienvenido a Domiquerendona. Tu perfil de repartidor fue reactivado.\n\n"
            if reactivated else
            "Bienvenido a Domiquerendona. Tu registro de repartidor fue aprobado.\n\n"
        )
        bonus_line = ""
        if bonus_granted:
            bonus_line = "Recibiste $5.000 de saldo de bienvenida para empezar a recibir pedidos.\n\n"
        return (
            opening
            + bonus_line
            + "Primeros pasos para operar:\n"
            + "1. Usa /menu y entra a [Mi repartidor].\n"
            + "2. Activa tu panel y comparte tu ubicacion en vivo cuando vayas a recibir ofertas.\n"
            + "3. Revisa tus pedidos y tu saldo desde ese mismo menu.\n"
            + "4. Usa /recargar cuando necesites saldo adicional.\n\n"
            + "Usa /menu para ver todas tus opciones."
        )

    return "Bienvenido a Domiquerendona.\n\nUsa /menu para ver tus opciones."


def _send_role_welcome_message(context, role: str, chat_id: int, profile=None, bonus_granted: bool = False, reactivated: bool = False):
    if not chat_id:
        return
    context.bot.send_message(
        chat_id=chat_id,
        text=_build_role_welcome_message(
            role,
            profile=profile,
            bonus_granted=bonus_granted,
            reactivated=reactivated,
        ),
    )


# ---------- UTILIDADES MONETARIAS ----------

def _fmt_pesos(amount: int) -> str:
    try:
        amount = int(amount or 0)
    except Exception:
        amount = 0
    return f"${amount:,}".replace(",", ".")


def build_offer_demand_badge_text(preview: dict) -> str:
    """Renderiza un bloque compacto de semaforo de demanda para previews."""
    if not preview:
        return ""

    signal_label = preview.get("signal_label") or "NO DISPONIBLE"
    eligible_count = int(preview.get("eligible_count") or 0)
    nearest_km = preview.get("nearest_km")
    suggested_incentive = int(preview.get("suggested_incentive") or 0)
    extra_suggested = int(preview.get("extra_incentive_suggested") or 0)
    current_incentive = int(preview.get("current_incentive") or 0)
    reason = (preview.get("reason") or "").strip()

    lines = [
        "Semaforo de demanda actual: {}".format(signal_label),
        "Repartidores elegibles cerca ahora: {}".format(eligible_count),
    ]
    if nearest_km is not None:
        lines[-1] += " (mas cercano ~{:.1f} km)".format(float(nearest_km))
    if reason:
        lines.append(reason)

    if suggested_incentive <= 0:
        lines.append("Incentivo sugerido ahora: opcional.")
    else:
        lines.append("Sugerencia opcional para acelerar: {}".format(_fmt_pesos(suggested_incentive)))
        if extra_suggested > 0:
            lines.append("Si quieres moverlo mas rapido, agrega al menos {} mas.".format(_fmt_pesos(extra_suggested)))
        elif current_incentive > 0:
            lines.append("Tu incentivo actual ya cubre esta sugerencia.")

    return "\n".join(lines)


# ---------- TÉRMINOS Y CONDICIONES ----------

def build_offer_suggestion_button_row(preview: dict, callback_template: str, allowed_amounts=None):
    """Construye una fila discreta de sugerencia cuando falta incentivo para la demanda actual."""
    if not preview or not callback_template:
        return None

    signal_code = (preview.get("signal_code") or "").strip().upper()
    extra_suggested = int(preview.get("extra_incentive_suggested") or 0)
    if signal_code not in ("MEDIUM", "HIGH") or extra_suggested <= 0:
        return None

    allowed = set(int(v) for v in (allowed_amounts or []))
    if allowed and extra_suggested not in allowed:
        return None

    return [
        InlineKeyboardButton(
            "Aplicar sugerencia ({})".format(_fmt_pesos(extra_suggested)),
            callback_data=callback_template.format(amount=extra_suggested),
        )
    ]


def ensure_terms(update, context, telegram_id: int, role: str) -> bool:
    logger.debug(
        "[terms][ensure] role=%s telegram_id=%s via_callback=%s",
        role, telegram_id, bool(getattr(update, 'callback_query', None)),
    )
    tv = get_active_terms_version(role)
    if not tv:
        logger.debug("[terms][ensure] no_terms_config role=%s", role)
        context.bot.send_message(
            chat_id=telegram_id,
            text="Términos no configurados para este rol. Contacta al soporte de la plataforma."
        )
        return False

    version, url, sha256 = tv
    logger.debug("[terms][ensure] version=%r url=%r", version, url)

    accepted = has_accepted_terms(telegram_id, role, version, sha256)
    logger.debug("[terms][ensure] already_accepted=%s", accepted)
    if accepted:
        try:
            save_terms_session_ack(telegram_id, role, version)
        except Exception as e:
            logger.warning("save_terms_session_ack: %s", e)
        return True

    text = (
        "Antes de continuar debes aceptar los Términos y Condiciones de Domiquerendona.\n\n"
        "Rol: {}\n"
        "Versión: {}\n\n"
        "Lee el documento y confirma tu aceptación para continuar."
    ).format(role, version)

    valid_terms_url = isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))
    keyboard = []
    if valid_terms_url:
        keyboard.append([InlineKeyboardButton("Leer términos", url=url)])
    else:
        logger.warning("[terms] URL invalida para role=%s, version=%s: %r", role, version, url)
    keyboard.append(
        [
            InlineKeyboardButton("Acepto", callback_data="terms_accept_{}".format(role)),
            InlineKeyboardButton("No acepto", callback_data="terms_decline_{}".format(role)),
        ]
    )

    if update.callback_query:
        logger.debug("[terms][ensure] prompt_sent_via=callback_edit")
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        logger.debug("[terms][ensure] prompt_sent_via=send_message")
        context.bot.send_message(chat_id=telegram_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    return False
