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
    ALLY_ADDRESS,
    ALLY_UBICACION,
    ALLY_CONFIRM,
    ALLY_TEAM,
    COURIER_FULLNAME,
    COURIER_IDNUMBER,
    COURIER_PHONE,
    COURIER_CITY,
    COURIER_BARRIO,
    COURIER_RESIDENCE_ADDRESS,
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
    LOCAL_ADMIN_RESIDENCE_ADDRESS,
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
    print(f"[DEBUG][admin_reg] step={step} snapshot={snapshot} extra={extra}", flush=True)


_OPTIONS_HINT = (
    "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
)

# Regex y filtro compartido para "Cancelar" / "Volver al menu".
# Nota: se usa para evitar que ese texto sea consumido como input normal en estados con texto.
CANCELAR_VOLVER_MENU_REGEX = r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'
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
            ALLY_ADDRESS: "Escribe la dirección del negocio:",
            ALLY_UBICACION: (
                "Envía la ubicación GPS (pin de Telegram) o pega un link de Google Maps."
            ),
            ALLY_CONFIRM: "Escribe SI para confirmar tu registro.",
        },
        "courier": {
            COURIER_FULLNAME: "Registro de repartidor\n\nEscribe tu nombre completo:",
            COURIER_IDNUMBER: "Escribe tu número de identificación:",
            COURIER_PHONE: "Escribe tu número de celular:",
            COURIER_CITY: "Escribe la ciudad donde trabajas:",
            COURIER_BARRIO: "Escribe el barrio o sector principal donde trabajas:",
            COURIER_RESIDENCE_ADDRESS: "Escribe tu dirección de residencia:",
            COURIER_RESIDENCE_LOCATION: "Envía tu ubicación GPS (pin de Telegram) o pega un link de Google Maps.",
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
            LOCAL_ADMIN_RESIDENCE_ADDRESS: "Escribe tu dirección de residencia:",
            LOCAL_ADMIN_RESIDENCE_LOCATION: "Envía tu ubicación GPS (pin de Telegram) o pega un link de Google Maps.",
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
    if ally and ally.get("status") == "APPROVED" and "/soy_aliado" not in missing_cmds:
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
        ['Mi enlace de pedidos'],
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
        print("ERROR get_admin_by_user_id en menu:", e)
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


def _mostrar_confirmacion_geocode(message, context, geo, original_text, cb_si, cb_no):
    """Muestra el primer candidato de geocoding con pin, link de Maps y botones de confirmacion.
    geo: dict con lat, lng, formatted_address, place_id.
    original_text: texto original del usuario (para carga perezosa del siguiente candidato)."""
    lat = geo["lat"]
    lng = geo["lng"]
    formatted_address = geo.get("formatted_address", "")
    _pid = geo.get("place_id") or f"{lat},{lng}"
    context.user_data["pending_geo_lat"] = lat
    context.user_data["pending_geo_lng"] = lng
    context.user_data["pending_geo_text"] = original_text
    context.user_data["pending_geo_seen"] = [_pid]
    message.reply_location(latitude=lat, longitude=lng)
    maps_link = f"https://maps.google.com/?q={lat},{lng}"
    keyboard = [[
        InlineKeyboardButton("Si, usar esta ubicacion", callback_data=cb_si),
        InlineKeyboardButton("No, esta no es", callback_data=cb_no),
    ]]
    message.reply_text(
        f"Encontre esta ubicacion:\n\n{formatted_address}\n\n"
        f"Ver en mapa: {maps_link}\n\n"
        "Es correcta?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def _geo_siguiente_o_gps(query, context, cb_si, cb_no, estado):
    """Busca el siguiente candidato de geocoding (carga perezosa) o pide GPS si no hay mas."""
    original_text = context.user_data.get("pending_geo_text", "")
    seen = context.user_data.get("pending_geo_seen", [])
    next_geo = resolve_location_next(original_text, seen) if original_text else None
    if next_geo:
        _pid = next_geo.get("place_id") or f"{next_geo['lat']},{next_geo['lng']}"
        seen.append(_pid)
        context.user_data["pending_geo_seen"] = seen
        context.user_data["pending_geo_lat"] = next_geo["lat"]
        context.user_data["pending_geo_lng"] = next_geo["lng"]
        lat = next_geo["lat"]
        lng = next_geo["lng"]
        maps_link = f"https://maps.google.com/?q={lat},{lng}"
        keyboard = [[
            InlineKeyboardButton("Si, usar esta ubicacion", callback_data=cb_si),
            InlineKeyboardButton("No, esta no es", callback_data=cb_no),
        ]]
        query.edit_message_text("Buscando otra opcion...")
        query.message.reply_location(latitude=lat, longitude=lng)
        query.message.reply_text(
            f"Otra opcion:\n\n{next_geo.get('formatted_address', '')}\n\n"
            f"Ver en mapa: {maps_link}\n\nEs correcta?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        context.user_data.pop("pending_geo_lat", None)
        context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        query.edit_message_text(
            "No encontre mas opciones. Envia la ubicacion de otra forma:\n"
            "- Un PIN de ubicacion de Telegram\n"
            "- Un link de Google Maps con coordenadas\n"
            "- Coordenadas directas (ej: 4.81,-75.69)"
        )
    return estado
