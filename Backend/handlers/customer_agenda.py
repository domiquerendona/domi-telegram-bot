# =============================================================================
# handlers/customer_agenda.py — Agenda de clientes (Fase 2e)
# Extraido de main.py
# Contiene: clientes_conv, agenda_conv, admin_clientes_conv, ally_clientes_conv
# =============================================================================

import logging
logger = logging.getLogger(__name__)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from handlers.states import (
    ADMIN_CUST_BUSCAR,
    ADMIN_CUST_DIR_BARRIO,
    ADMIN_CUST_DIR_CIUDAD,
    ADMIN_CUST_DIR_CORREGIR,
    ADMIN_CUST_DIR_EDITAR_LABEL,
    ADMIN_CUST_DIR_EDITAR_NOTA,
    ADMIN_CUST_DIR_EDITAR_TEXT,
    ADMIN_CUST_DIR_NUEVA_LABEL,
    ADMIN_CUST_DIR_NUEVA_TEXT,
    ADMIN_CUST_EDITAR_NOMBRE,
    ADMIN_CUST_EDITAR_NOTAS,
    ADMIN_CUST_EDITAR_TELEFONO,
    ADMIN_CUST_MENU,
    ADMIN_CUST_NUEVO_DIR_LABEL,
    ADMIN_CUST_NUEVO_DIR_TEXT,
    ADMIN_CUST_NUEVO_NOMBRE,
    ADMIN_CUST_NUEVO_NOTAS,
    ADMIN_CUST_NUEVO_TELEFONO,
    ADMIN_CUST_VER,
    ALLY_CUST_BUSCAR,
    ALLY_CUST_DIR_BARRIO,
    ALLY_CUST_DIR_CIUDAD,
    ALLY_CUST_DIR_CORREGIR,
    ALLY_CUST_PARKING,
    ADMIN_CUST_PARKING,
    ALLY_CUST_DIR_EDITAR_LABEL,
    ALLY_CUST_DIR_EDITAR_NOTA,
    ALLY_CUST_DIR_EDITAR_TEXT,
    ALLY_CUST_DIR_NUEVA_LABEL,
    ALLY_CUST_DIR_NUEVA_TEXT,
    ALLY_CUST_EDITAR_NOMBRE,
    ALLY_CUST_EDITAR_NOTAS,
    ALLY_CUST_EDITAR_TEL,
    ALLY_CUST_MENU,
    ALLY_CUST_NUEVO_DIR_LABEL,
    ALLY_CUST_NUEVO_DIR_TEXT,
    ALLY_CUST_NUEVO_NOMBRE,
    ALLY_CUST_NUEVO_NOTAS,
    ALLY_CUST_NUEVO_TEL,
    ALLY_CUST_VER,
    CLIENTES_BUSCAR,
    CLIENTES_DIR_BARRIO,
    CLIENTES_DIR_CIUDAD,
    CLIENTES_DIR_CORREGIR_COORDS,
    CLIENTES_DIR_EDITAR_LABEL,
    CLIENTES_DIR_EDITAR_NOTA,
    CLIENTES_DIR_EDITAR_TEXT,
    CLIENTES_DIR_NUEVA_LABEL,
    CLIENTES_DIR_NUEVA_TEXT,
    CLIENTES_EDITAR_NOMBRE,
    CLIENTES_EDITAR_NOTAS,
    CLIENTES_EDITAR_TELEFONO,
    CLIENTES_MENU,
    CLIENTES_NUEVO_DIRECCION_LABEL,
    CLIENTES_NUEVO_DIRECCION_TEXT,
    CLIENTES_NUEVO_NOMBRE,
    CLIENTES_NUEVO_NOTAS,
    CLIENTES_NUEVO_TELEFONO,
    CLIENTES_VER_CLIENTE,
    DIRECCIONES_MENU,
    DIRECCIONES_PICKUPS,
    DIRECCIONES_PICKUP_GUARDAR,
    DIRECCIONES_PICKUP_NUEVA_BARRIO,
    DIRECCIONES_PICKUP_NUEVA_CIUDAD,
    DIRECCIONES_PICKUP_NUEVA_DETALLES,
    DIRECCIONES_PICKUP_NUEVA_UBICACION,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER,
    _geo_siguiente_o_gps,
    _handle_text_field_input,
    _mostrar_confirmacion_geocode,
    cancel_conversacion,
    cancel_por_texto,
)
from services import (
    archive_admin_customer,
    archive_admin_customer_address,
    archive_ally_customer,
    archive_customer_address,
    create_admin_customer,
    create_admin_customer_address,
    create_ally_customer,
    create_ally_location,
    create_customer_address,
    delete_ally_location,
    PARKING_FEE_AMOUNT,
    set_address_parking_status,
    get_ally_parking_fee_enabled,
    ensure_user,
    find_matching_customer_address,
    get_admin_by_telegram_id,
    get_admin_customer_address_by_id,
    get_admin_customer_by_id,
    get_ally_by_user_id,
    get_ally_customer_by_id,
    get_ally_location_by_id,
    get_ally_locations,
    get_customer_address_by_id,
    get_default_ally_location,
    get_user_by_telegram_id,
    get_user_db_id_from_update,
    has_valid_coords,
    list_admin_customer_addresses,
    list_admin_customers,
    list_ally_customers,
    list_customer_addresses,
    resolve_location,
    restore_admin_customer,
    restore_ally_customer,
    search_admin_customers,
    search_ally_customers,
    set_default_ally_location,
    update_admin_customer,
    update_admin_customer_address,
    update_ally_customer,
    update_customer_address,
    update_customer_address_coords,
)


def _agenda_geo_no_more_text():
    return (
        "No encontre mas opciones para esa direccion.\n\n"
        "Envia otra ubicacion para continuar:\n"
        "- Un PIN de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Una direccion con ciudad"
    )


def _agenda_emit_geo_confirmation(update, context, loc, texto, cb_si, cb_no, formatted_key, log_tag):
    logger.info(
        "[%s] status=pending lat=%s lng=%s",
        log_tag,
        loc.get("lat"),
        loc.get("lng"),
    )
    _mostrar_confirmacion_geocode(
        update.message,
        context,
        loc,
        texto,
        cb_si,
        cb_no,
        header_text="Confirma este punto exacto antes de guardar la direccion.",
        question_text="Es esta la ubicacion correcta?",
        formatted_storage_key=formatted_key,
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
    context.user_data["active_ally_id"] = ally["id"]

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
    ally_id = context.user_data.get("active_ally_id")

    if not ally_id:
        query.edit_message_text("No hay un aliado activo. Regresa al menu e inicia el pedido nuevamente.")
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
    ally_id = context.user_data.get("active_ally_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if not customer:
        query.edit_message_text("Cliente no encontrado.")
        return CLIENTES_MENU

    context.user_data["current_customer_id"] = customer_id

    addresses = list_customer_addresses(customer_id)
    addr_text = ""
    if addresses:
        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            parking_status = addr["parking_status"] if "parking_status" in addr.keys() else "NOT_ASKED"
            parking_tag = " [parqueo dificil]" if parking_status in ("ALLY_YES", "ADMIN_YES") else ""
            addr_text += "- {}{}: {}...\n".format(label, parking_tag, addr["address_text"][:35])
    else:
        addr_text = "Sin direcciones guardadas\n"

    nota_interna = customer["notes"] or "Sin notas"

    keyboard = [
        [InlineKeyboardButton("Direcciones", callback_data="cust_dirs")],
        [InlineKeyboardButton("Editar", callback_data="cust_editar")],
        [InlineKeyboardButton("Archivar", callback_data="cust_archivar")],
        [InlineKeyboardButton("Volver", callback_data="cust_volver_menu")],
    ]

    query.edit_message_text(
        f"Cliente: {customer['name']}\n"
        f"Telefono: {customer['phone']}\n\n"
        f"Nota interna:\n{nota_interna}\n\n"
        f"Direcciones guardadas:\n{addr_text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CLIENTES_VER_CLIENTE


def clientes_ver_cliente_callback(update, context):
    """Maneja callbacks de la vista de cliente."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("active_ally_id")
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
        nota_entrega = address["notes"] or "Sin nota"
        lat = address["lat"]
        lng = address["lng"]

        if lat is not None and lng is not None:
            try:
                context.bot.send_location(
                    chat_id=query.message.chat_id,
                    latitude=float(lat),
                    longitude=float(lng),
                )
            except Exception:
                pass
            coords_text = "Coordenadas: {:.5f}, {:.5f}".format(float(lat), float(lng))
            btn_coords = "Corregir coordenadas"
        else:
            coords_text = "Sin coordenadas"
            btn_coords = "Agregar coordenadas"

        keyboard = [
            [InlineKeyboardButton("Editar", callback_data="cust_dir_editar")],
            [InlineKeyboardButton("Editar nota entrega", callback_data="cust_dir_edit_nota")],
            [InlineKeyboardButton(btn_coords, callback_data="cust_dir_corregir_coords")],
            [InlineKeyboardButton("Archivar", callback_data="cust_dir_archivar")],
            [InlineKeyboardButton("Volver", callback_data="cust_dirs")],
        ]

        query.edit_message_text(
            f"{label}\n"
            f"{address['address_text']}\n\n"
            f"Nota para entrega:\n{nota_entrega}\n\n"
            f"{coords_text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_VER_CLIENTE

    elif data == "cust_dir_corregir_coords":
        query.edit_message_text(
            "Corregir / agregar coordenadas\n\n"
            "Envia un pin de ubicacion de Telegram, un link de Google Maps, "
            "o escribe las coordenadas (ej: 4.81,-75.69).\n\n"
            "Escribe 'cancelar' para volver."
        )
        context.user_data["clientes_geo_mode"] = "corregir_coords"
        return CLIENTES_DIR_CORREGIR_COORDS

    elif data == "cust_dir_editar":
        query.edit_message_text("Escribe la nueva etiqueta (Casa, Trabajo, Otro):")
        return CLIENTES_DIR_EDITAR_LABEL

    elif data == "cust_dir_edit_nota":
        query.edit_message_text(
            "Escribe la nota para entrega.\n"
            "Esta nota sera visible para el repartidor.\n\n"
            "Escribe 'ninguna' para borrar la nota:"
        )
        return CLIENTES_DIR_EDITAR_NOTA

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
    update.message.reply_text("Escribe la direccion de entrega del cliente:")
    return CLIENTES_NUEVO_DIRECCION_TEXT


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


def _clientes_resolver_direccion_para_agenda(update, context, texto, cb_si, cb_no, estado):
    """Aplica el mismo pipeline de cotizar para resolver una direccion en agenda."""
    loc = resolve_location(texto)
    if not loc or loc.get("lat") is None or loc.get("lng") is None:
        update.message.reply_text(
            "No pude encontrar esa ubicacion.\n\n"
            "Intenta con:\n"
            "- Un PIN de Telegram\n"
            "- Un link de Google Maps\n"
            "- Coordenadas (ej: 4.81,-75.69)\n"
            "- Direccion con ciudad (ej: Barrio Leningrado, Pereira)"
        )
        return None

    if loc.get("method") == "geocode" and loc.get("formatted_address"):
        _agenda_emit_geo_confirmation(
            update,
            context,
            loc,
            texto,
            cb_si,
            cb_no,
            "clientes_geo_formatted",
            "clientes_location_confirm",
        )
        return estado

    return loc


def _clientes_guardar_nuevo(msg_or_query, context, address_text, lat, lng):
    """Crea cliente + direccion 'Principal' directamente. Limpia claves temporales."""
    ally_id = context.user_data.get("active_ally_id")
    name = context.user_data.get("new_customer_name")
    phone = context.user_data.get("new_customer_phone")
    try:
        customer_id = create_ally_customer(ally_id, name, phone, None)
        create_customer_address(customer_id, "Principal", address_text, city="", barrio="", lat=lat, lng=lng)
        keyboard = [[InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")]]
        text = "Cliente '{}' guardado.\n\nTelefono: {}\nDireccion: {}".format(name, phone, address_text)
        if hasattr(msg_or_query, 'reply_text'):
            msg_or_query.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            msg_or_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        err_text = "Error al guardar cliente: {}".format(str(e))
        if hasattr(msg_or_query, 'reply_text'):
            msg_or_query.reply_text(err_text)
        else:
            msg_or_query.edit_message_text(err_text)
    for key in [
        "new_customer_name", "new_customer_phone",
        "clientes_geo_mode", "clientes_geo_address_input", "clientes_geo_formatted",
        "clientes_pending_mode", "clientes_pending_address_text",
        "clientes_pending_lat", "clientes_pending_lng",
        "clientes_pending_city", "clientes_pending_barrio", "clientes_pending_notes",
    ]:
        context.user_data.pop(key, None)
    return CLIENTES_MENU


def clientes_nuevo_direccion_text(update, context):
    """Recibe direccion y guarda el nuevo cliente."""
    address_text = update.message.text.strip()

    resolved = _clientes_resolver_direccion_para_agenda(
        update, context, address_text, "cust_geo_si", "cust_geo_no", CLIENTES_NUEVO_DIRECCION_TEXT
    )
    if resolved is None:
        return CLIENTES_NUEVO_DIRECCION_TEXT
    if isinstance(resolved, int):
        context.user_data["clientes_geo_mode"] = "nuevo_cliente"
        context.user_data["clientes_geo_address_input"] = address_text
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    address_to_save = resolved.get("formatted_address") or address_text
    return _clientes_guardar_nuevo(update.message, context, address_to_save, lat, lng)


def clientes_buscar(update, context):
    """Busca clientes por nombre o telefono."""
    query_text = update.message.text.strip()
    ally_id = context.user_data.get("active_ally_id")

    results = search_ally_customers(ally_id, query_text, limit=10)
    if not results:
        keyboard = [
            [InlineKeyboardButton("Agregar nuevo cliente", callback_data="cust_nuevo")],
            [InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")],
        ]
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
    ally_id = context.user_data.get("active_ally_id")
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
    ally_id = context.user_data.get("active_ally_id")
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
    ally_id = context.user_data.get("active_ally_id")
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

    resolved = _clientes_resolver_direccion_para_agenda(
        update, context, address_text, "cust_geo_si", "cust_geo_no", CLIENTES_DIR_NUEVA_TEXT
    )
    if resolved is None:
        return CLIENTES_DIR_NUEVA_TEXT
    if isinstance(resolved, int):
        context.user_data["clientes_geo_mode"] = "dir_nueva"
        context.user_data["clientes_geo_address_input"] = address_text
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    address_to_save = resolved.get("formatted_address") or address_text
    context.user_data["clientes_pending_mode"] = "dir_nueva"
    context.user_data["clientes_pending_address_text"] = address_to_save
    context.user_data["clientes_pending_lat"] = lat
    context.user_data["clientes_pending_lng"] = lng
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return CLIENTES_DIR_CIUDAD


def clientes_geo_callback(update, context):
    """Confirma/rechaza geocoding de direccion en agenda de clientes."""
    query = update.callback_query
    query.answer()

    mode = context.user_data.get("clientes_geo_mode")
    if not mode:
        query.edit_message_text("Sesion de geocodificacion expirada. Escribe la direccion nuevamente.")
        return CLIENTES_MENU

    if query.data == "cust_geo_si":
        formatted = context.user_data.pop("clientes_geo_formatted", "")
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Escribe la ubicacion nuevamente.")
            return CLIENTES_NUEVO_DIRECCION_TEXT if mode == "nuevo_cliente" else CLIENTES_DIR_NUEVA_TEXT
        logger.info(
            "[clientes_location_confirm] status=confirmed mode=%s lat=%s lng=%s",
            mode,
            lat,
            lng,
        )

        if mode == "corregir_coords":
            context.user_data.pop("clientes_geo_mode", None)
            customer_id = context.user_data.get("current_customer_id")
            address_id = context.user_data.get("current_address_id")
            address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
            if not address:
                query.edit_message_text("Error: direccion no encontrada.")
                return clientes_mostrar_menu(update, context, edit_message=True)
            try:
                update_customer_address(
                    address_id=address_id,
                    customer_id=customer_id,
                    label=address["label"],
                    address_text=address["address_text"],
                    city=address["city"] or "",
                    barrio=address["barrio"] or "",
                    notes=address["notes"],
                    lat=lat,
                    lng=lng,
                )
                query.edit_message_text(
                    "Coordenadas actualizadas.\n"
                    "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
                )
            except Exception as e:
                query.edit_message_text("Error al actualizar: {}".format(str(e)))
            return clientes_mostrar_menu(update, context, edit_message=False)

        address_to_save = (formatted or context.user_data.get("clientes_geo_address_input", "")).strip()
        if mode == "nuevo_cliente":
            context.user_data.pop("clientes_geo_mode", None)
            context.user_data.pop("clientes_geo_address_input", None)
            return _clientes_guardar_nuevo(query, context, address_to_save, lat, lng)

        context.user_data["clientes_pending_mode"] = mode
        context.user_data["clientes_pending_address_text"] = address_to_save
        context.user_data["clientes_pending_lat"] = lat
        context.user_data["clientes_pending_lng"] = lng
        query.edit_message_text("Escribe la ciudad de la direccion:")
        return CLIENTES_DIR_CIUDAD

    estado = CLIENTES_NUEVO_DIRECCION_TEXT if mode == "nuevo_cliente" else CLIENTES_DIR_NUEVA_TEXT
    logger.info("[clientes_location_confirm] status=rejected mode=%s", mode)
    return _geo_siguiente_o_gps(
        query,
        context,
        "cust_geo_si",
        "cust_geo_no",
        estado,
        header_text="Confirma este punto exacto antes de guardar la direccion.",
        question_text="Es esta la ubicacion correcta?",
        no_more_text=_agenda_geo_no_more_text(),
        formatted_storage_key="clientes_geo_formatted",
    )


def clientes_dir_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la direccion:",
        "clientes_pending_city",
        CLIENTES_DIR_CIUDAD,
        CLIENTES_DIR_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector de la direccion:",
        options_hint="",
        set_back_step=False,
    )


def clientes_dir_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la direccion:",
        "clientes_pending_barrio",
        CLIENTES_DIR_BARRIO,
        CLIENTES_MENU,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == CLIENTES_DIR_BARRIO:
        return ok_state
    barrio = context.user_data.get("clientes_pending_barrio", "")

    mode = context.user_data.get("clientes_pending_mode")
    address_text = context.user_data.get("clientes_pending_address_text", "")
    lat = context.user_data.get("clientes_pending_lat")
    lng = context.user_data.get("clientes_pending_lng")
    city = context.user_data.get("clientes_pending_city", "")
    notes = context.user_data.get("clientes_pending_notes")

    if mode == "nuevo_cliente":
        ally_id = context.user_data.get("active_ally_id")
        name = context.user_data.get("new_customer_name")
        phone = context.user_data.get("new_customer_phone")
        customer_notes = context.user_data.get("new_customer_notes")
        label = context.user_data.get("new_address_label")
        try:
            customer_id = create_ally_customer(ally_id, name, phone, customer_notes)
            create_customer_address(customer_id, label, address_text, city=city, barrio=barrio, lat=lat, lng=lng)
            keyboard = [[InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")]]
            update.message.reply_text(
                "Cliente '{}' creado exitosamente.\n\n"
                "Telefono: {}\n"
                "Direccion ({}): {}".format(name, phone, label, address_text),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            update.message.reply_text("Error al crear cliente: {}".format(str(e)))

        for key in [
            "new_customer_name",
            "new_customer_phone",
            "new_customer_notes",
            "new_address_label",
            "clientes_geo_mode",
            "clientes_geo_address_input",
            "clientes_pending_mode",
            "clientes_pending_address_text",
            "clientes_pending_lat",
            "clientes_pending_lng",
            "clientes_pending_city",
            "clientes_pending_barrio",
            "clientes_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return CLIENTES_MENU

    if mode == "dir_nueva":
        customer_id = context.user_data.get("current_customer_id")
        label = context.user_data.get("new_address_label")
        try:
            create_customer_address(customer_id, label, address_text, city=city, barrio=barrio, lat=lat, lng=lng)
            update.message.reply_text("Direccion agregada: {} - {}".format(label, address_text))
        except Exception as e:
            update.message.reply_text("Error: {}".format(str(e)))

        for key in [
            "new_address_label",
            "clientes_geo_mode",
            "clientes_geo_address_input",
            "clientes_pending_mode",
            "clientes_pending_address_text",
            "clientes_pending_lat",
            "clientes_pending_lng",
            "clientes_pending_city",
            "clientes_pending_barrio",
            "clientes_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    if mode == "dir_editar":
        customer_id = context.user_data.get("current_customer_id")
        address_id = context.user_data.get("current_address_id")
        label = context.user_data.get("edit_address_label")
        try:
            update_customer_address(
                address_id=address_id,
                customer_id=customer_id,
                label=label,
                address_text=address_text,
                city=city,
                barrio=barrio,
                notes=notes,
                lat=lat,
                lng=lng,
            )
            update.message.reply_text("Direccion actualizada.")
        except Exception as e:
            update.message.reply_text("Error: {}".format(str(e)))

        for key in [
            "edit_address_label",
            "current_address_id",
            "clientes_pending_mode",
            "clientes_pending_address_text",
            "clientes_pending_lat",
            "clientes_pending_lng",
            "clientes_pending_city",
            "clientes_pending_barrio",
            "clientes_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    update.message.reply_text("Error: sesion expirada. Intenta de nuevo desde el menu.")
    for key in [
        "clientes_pending_mode",
        "clientes_pending_address_text",
        "clientes_pending_lat",
        "clientes_pending_lng",
        "clientes_pending_city",
        "clientes_pending_barrio",
        "clientes_pending_notes",
    ]:
        context.user_data.pop(key, None)
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

    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("edit_address_label", None)
        context.user_data.pop("current_address_id", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    resolved = _clientes_resolver_direccion_para_agenda(
        update, context, address_text, "cust_geo_si", "cust_geo_no", CLIENTES_DIR_EDITAR_TEXT
    )
    if resolved is None:
        return CLIENTES_DIR_EDITAR_TEXT
    if isinstance(resolved, int):
        context.user_data["clientes_geo_mode"] = "dir_editar"
        context.user_data["clientes_geo_address_input"] = address_text
        return resolved

    context.user_data["clientes_pending_mode"] = "dir_editar"
    context.user_data["clientes_pending_address_text"] = resolved.get("formatted_address") or address_text
    context.user_data["clientes_pending_lat"] = resolved.get("lat")
    context.user_data["clientes_pending_lng"] = resolved.get("lng")
    context.user_data["clientes_pending_notes"] = address.get("notes")
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return CLIENTES_DIR_CIUDAD


def clientes_dir_editar_nota(update, context):
    """Actualiza la nota para entrega de una direccion."""
    nota_text = update.message.text.strip()
    customer_id = context.user_data.get("current_customer_id")
    address_id = context.user_data.get("current_address_id")

    # Obtener la direccion actual para preservar los otros campos
    address = get_customer_address_by_id(address_id, customer_id)
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        return clientes_mostrar_menu(update, context, edit_message=False)

    # Si escribe "ninguna", borrar la nota
    nueva_nota = None if nota_text.lower() == "ninguna" else nota_text

    try:
        update_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"],
            barrio=address["barrio"],
            notes=nueva_nota,
            lat=address["lat"],
            lng=address["lng"]
        )
        if nueva_nota:
            update.message.reply_text("Nota para entrega actualizada.")
        else:
            update.message.reply_text("Nota para entrega eliminada.")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

    context.user_data.pop("current_address_id", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_dir_corregir_coords_handler(update, context):
    """Recibe texto/link para corregir o agregar coordenadas de una direccion de cliente."""
    text = update.message.text.strip()
    if text.lower() == "cancelar":
        context.user_data.pop("clientes_geo_mode", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    customer_id = context.user_data.get("current_customer_id")
    address_id = context.user_data.get("current_address_id")
    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("clientes_geo_mode", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    context.user_data["clientes_geo_mode"] = "corregir_coords"
    context.user_data["clientes_geo_address_input"] = text

    resolved = _clientes_resolver_direccion_para_agenda(
        update, context, text, "cust_geo_si", "cust_geo_no", CLIENTES_DIR_CORREGIR_COORDS
    )
    if resolved is None:
        return CLIENTES_DIR_CORREGIR_COORDS
    if isinstance(resolved, int):
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    if lat is None or lng is None:
        update.message.reply_text("No se pudo obtener coordenadas. Intenta de nuevo o escribe 'cancelar'.")
        return CLIENTES_DIR_CORREGIR_COORDS

    try:
        update_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"] or "",
            barrio=address["barrio"] or "",
            notes=address["notes"],
            lat=lat,
            lng=lng,
        )
        update.message.reply_text(
            "Coordenadas actualizadas.\n"
            "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
        )
    except Exception as e:
        update.message.reply_text("Error al actualizar: {}".format(str(e)))

    context.user_data.pop("clientes_geo_mode", None)
    context.user_data.pop("clientes_geo_address_input", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_dir_corregir_coords_location_handler(update, context):
    """Recibe pin GPS de Telegram para corregir o agregar coordenadas de una direccion."""
    loc = update.message.location
    lat = loc.latitude
    lng = loc.longitude
    customer_id = context.user_data.get("current_customer_id")
    address_id = context.user_data.get("current_address_id")
    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("clientes_geo_mode", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    try:
        update_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"] or "",
            barrio=address["barrio"] or "",
            notes=address["notes"],
            lat=lat,
            lng=lng,
        )
        update.message.reply_text(
            "Coordenadas actualizadas.\n"
            "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
        )
    except Exception as e:
        update.message.reply_text("Error al actualizar: {}".format(str(e)))

    context.user_data.pop("clientes_geo_mode", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


# =========================
# Agenda de clientes del Admin (admin_clientes_conv)
# Prefijo callbacks: acust_
# Prefijo user_data: acust_
# =========================

def admin_clientes_cmd(update, context):
    """Entry point de la agenda de clientes del admin. Verifica que sea admin APPROVED."""
    query = update.callback_query
    query.answer()
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)

    if not db_user:
        query.edit_message_text("Aun no estas registrado. Usa /start primero.")
        return ConversationHandler.END

    admin = get_admin_by_telegram_id(user.id)
    if not admin:
        query.edit_message_text("Este menu es solo para administradores.")
        return ConversationHandler.END

    if admin["status"] != "APPROVED":
        query.edit_message_text("Tu registro como administrador aun no ha sido aprobado.")
        return ConversationHandler.END

    for key in list(context.user_data.keys()):
        if key.startswith("acust_"):
            del context.user_data[key]
    context.user_data["acust_admin_id"] = admin["id"]

    return _admin_clientes_mostrar_menu(update, context, edit_message=True)


def _admin_clientes_mostrar_menu(update, context, edit_message=False):
    """Muestra el menu principal de la agenda de clientes del admin."""
    keyboard = [
        [InlineKeyboardButton("Nuevo cliente", callback_data="acust_nuevo")],
        [InlineKeyboardButton("Buscar cliente", callback_data="acust_buscar")],
        [InlineKeyboardButton("Mis clientes", callback_data="acust_lista")],
        [InlineKeyboardButton("Clientes archivados", callback_data="acust_archivados")],
        [InlineKeyboardButton("Cerrar", callback_data="acust_cerrar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "AGENDA DE CLIENTES\n\nSelecciona una opcion:"

    if edit_message and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update.effective_message.reply_text(text, reply_markup=reply_markup)

    return ADMIN_CUST_MENU


def admin_clientes_menu_callback(update, context):
    """Maneja los callbacks del menu de clientes del admin."""
    query = update.callback_query
    query.answer()
    data = query.data
    admin_id = context.user_data.get("acust_admin_id")

    if not admin_id:
        query.edit_message_text("Sesion expirada. Vuelve al menu e inicia de nuevo.")
        return ConversationHandler.END

    if data == "acust_nuevo":
        query.edit_message_text("NUEVO CLIENTE\n\nEscribe el nombre del cliente:")
        return ADMIN_CUST_NUEVO_NOMBRE

    elif data == "acust_buscar":
        query.edit_message_text("BUSCAR CLIENTE\n\nEscribe el nombre o telefono a buscar:")
        return ADMIN_CUST_BUSCAR

    elif data == "acust_lista":
        customers = list_admin_customers(admin_id, limit=10, include_inactive=False)
        if not customers:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="acust_volver_menu")]]
            query.edit_message_text(
                "No tienes clientes guardados.\n\n"
                "Usa 'Nuevo cliente' para agregar uno.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ADMIN_CUST_MENU

        keyboard = []
        for c in customers:
            btn_text = "{} - {}".format(c["name"], c["phone"])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_ver_{}".format(c["id"]))])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="acust_volver_menu")])

        query.edit_message_text(
            "MIS CLIENTES\n\nSelecciona un cliente para ver detalles:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CUST_MENU

    elif data == "acust_archivados":
        customers = list_admin_customers(admin_id, limit=20, include_inactive=True)
        archived = [c for c in customers if c["status"] == "INACTIVE"]

        if not archived:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="acust_volver_menu")]]
            query.edit_message_text(
                "No tienes clientes archivados.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ADMIN_CUST_MENU

        keyboard = []
        for c in archived:
            btn_text = "{} - {}".format(c["name"], c["phone"])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_restaurar_{}".format(c["id"]))])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="acust_volver_menu")])

        query.edit_message_text(
            "CLIENTES ARCHIVADOS\n\nSelecciona uno para restaurar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CUST_MENU

    elif data == "acust_volver_menu":
        return _admin_clientes_mostrar_menu(update, context, edit_message=True)

    elif data == "acust_cerrar":
        query.edit_message_text("Agenda de clientes cerrada.")
        for key in list(context.user_data.keys()):
            if key.startswith("acust_"):
                del context.user_data[key]
        return ConversationHandler.END

    elif data.startswith("acust_ver_"):
        customer_id = int(data.replace("acust_ver_", ""))
        return _admin_clientes_ver_cliente(query, context, customer_id)

    elif data.startswith("acust_restaurar_"):
        customer_id = int(data.replace("acust_restaurar_", ""))
        if restore_admin_customer(customer_id, admin_id):
            query.edit_message_text("Cliente restaurado exitosamente.")
        else:
            query.edit_message_text("No se pudo restaurar el cliente.")
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    return ADMIN_CUST_MENU


def _admin_clientes_ver_cliente(query, context, customer_id):
    """Muestra detalles de un cliente del admin y sus opciones."""
    admin_id = context.user_data.get("acust_admin_id")
    customer = get_admin_customer_by_id(customer_id, admin_id)

    if not customer:
        query.edit_message_text("Cliente no encontrado.")
        return ADMIN_CUST_MENU

    context.user_data["acust_current_customer_id"] = customer_id

    addresses = list_admin_customer_addresses(customer_id)
    addr_text = ""
    if addresses:
        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            parking_status = addr["parking_status"] if "parking_status" in addr.keys() else "NOT_ASKED"
            parking_tag = " [parqueo dificil]" if parking_status in ("ALLY_YES", "ADMIN_YES") else ""
            addr_text += "- {}{}: {}...\n".format(label, parking_tag, addr["address_text"][:35])
    else:
        addr_text = "Sin direcciones guardadas\n"

    nota_interna = customer["notes"] or "Sin notas"

    keyboard = [
        [InlineKeyboardButton("Direcciones", callback_data="acust_dirs")],
        [InlineKeyboardButton("Editar", callback_data="acust_editar")],
        [InlineKeyboardButton("Archivar", callback_data="acust_archivar")],
        [InlineKeyboardButton("Volver", callback_data="acust_volver_menu")],
    ]

    query.edit_message_text(
        "Cliente: {}\n"
        "Telefono: {}\n\n"
        "Nota interna:\n{}\n\n"
        "Direcciones guardadas:\n{}".format(
            customer["name"], customer["phone"], nota_interna, addr_text
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_CUST_VER


def admin_clientes_ver_callback(update, context):
    """Maneja callbacks de la vista de cliente del admin."""
    query = update.callback_query
    query.answer()
    data = query.data
    admin_id = context.user_data.get("acust_admin_id")
    customer_id = context.user_data.get("acust_current_customer_id")

    if data == "acust_dirs":
        addresses = list_admin_customer_addresses(customer_id)
        keyboard = []

        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            btn_text = "{}: {}...".format(label, addr["address_text"][:25])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_dir_ver_{}".format(addr["id"]))])

        keyboard.append([InlineKeyboardButton("Agregar direccion", callback_data="acust_dir_nueva")])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="acust_ver_{}".format(customer_id))])

        query.edit_message_text(
            "DIRECCIONES DEL CLIENTE\n\nSelecciona una para editar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CUST_VER

    elif data == "acust_editar":
        keyboard = [
            [InlineKeyboardButton("Editar nombre", callback_data="acust_edit_nombre")],
            [InlineKeyboardButton("Editar telefono", callback_data="acust_edit_telefono")],
            [InlineKeyboardButton("Editar notas", callback_data="acust_edit_notas")],
            [InlineKeyboardButton("Volver", callback_data="acust_ver_{}".format(customer_id))],
        ]
        query.edit_message_text(
            "Que deseas editar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CUST_VER

    elif data == "acust_edit_nombre":
        query.edit_message_text("Escribe el nuevo nombre del cliente:")
        return ADMIN_CUST_EDITAR_NOMBRE

    elif data == "acust_edit_telefono":
        query.edit_message_text("Escribe el nuevo telefono del cliente:")
        return ADMIN_CUST_EDITAR_TELEFONO

    elif data == "acust_edit_notas":
        query.edit_message_text("Escribe las nuevas notas del cliente (o 'ninguna' para borrar):")
        return ADMIN_CUST_EDITAR_NOTAS

    elif data == "acust_archivar":
        if archive_admin_customer(customer_id, admin_id):
            query.edit_message_text("Cliente archivado exitosamente.")
        else:
            query.edit_message_text("No se pudo archivar el cliente.")
        context.user_data.pop("acust_current_customer_id", None)
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    elif data == "acust_dir_nueva":
        query.edit_message_text("NUEVA DIRECCION\n\nEscribe la etiqueta (Casa, Trabajo, Otro):")
        return ADMIN_CUST_DIR_NUEVA_LABEL

    elif data.startswith("acust_dir_ver_"):
        address_id = int(data.replace("acust_dir_ver_", ""))
        address = get_admin_customer_address_by_id(address_id, customer_id)
        if not address:
            query.edit_message_text("Direccion no encontrada.")
            return ADMIN_CUST_VER

        context.user_data["acust_current_address_id"] = address_id
        label = address["label"] or "Sin etiqueta"
        nota_entrega = address["notes"] or "Sin nota"
        lat = address["lat"]
        lng = address["lng"]

        if lat is not None and lng is not None:
            try:
                context.bot.send_location(
                    chat_id=query.message.chat_id,
                    latitude=float(lat),
                    longitude=float(lng),
                )
            except Exception:
                pass
            coords_text = "Coordenadas: {:.5f}, {:.5f}".format(float(lat), float(lng))
            btn_coords = "Corregir coordenadas"
        else:
            coords_text = "Sin coordenadas"
            btn_coords = "Agregar coordenadas"

        keyboard = [
            [InlineKeyboardButton("Editar", callback_data="acust_dir_editar")],
            [InlineKeyboardButton("Editar nota entrega", callback_data="acust_dir_edit_nota")],
            [InlineKeyboardButton(btn_coords, callback_data="acust_dir_corregir_coords")],
            [InlineKeyboardButton("Archivar", callback_data="acust_dir_archivar")],
            [InlineKeyboardButton("Volver", callback_data="acust_dirs")],
        ]

        query.edit_message_text(
            "{}\n"
            "{}\n\n"
            "Nota para entrega:\n{}\n\n"
            "{}".format(label, address["address_text"], nota_entrega, coords_text),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CUST_VER

    elif data == "acust_dir_corregir_coords":
        query.edit_message_text(
            "Corregir / agregar coordenadas\n\n"
            "Envia un pin de ubicacion de Telegram, un link de Google Maps, "
            "o escribe las coordenadas (ej: 4.81,-75.69).\n\n"
            "Escribe 'cancelar' para volver."
        )
        context.user_data["acust_geo_mode"] = "corregir_coords"
        return ADMIN_CUST_DIR_CORREGIR

    elif data == "acust_dir_editar":
        query.edit_message_text("Escribe la nueva etiqueta (Casa, Trabajo, Otro):")
        return ADMIN_CUST_DIR_EDITAR_LABEL

    elif data == "acust_dir_edit_nota":
        query.edit_message_text(
            "Escribe la nota para entrega.\n"
            "Esta nota sera visible para el repartidor.\n\n"
            "Escribe 'ninguna' para borrar la nota:"
        )
        return ADMIN_CUST_DIR_EDITAR_NOTA

    elif data == "acust_dir_archivar":
        address_id = context.user_data.get("acust_current_address_id")
        if archive_admin_customer_address(address_id, customer_id):
            query.edit_message_text("Direccion archivada.")
        else:
            query.edit_message_text("No se pudo archivar la direccion.")
        context.user_data.pop("acust_current_address_id", None)
        return _admin_clientes_ver_cliente(query, context, customer_id)

    elif data.startswith("acust_ver_"):
        cid = int(data.replace("acust_ver_", ""))
        return _admin_clientes_ver_cliente(query, context, cid)

    elif data == "acust_volver_menu":
        context.user_data.pop("acust_current_customer_id", None)
        return _admin_clientes_mostrar_menu(update, context, edit_message=True)

    return ADMIN_CUST_VER


def _admin_clientes_guardar_nuevo(msg_or_query, context, address_text, lat, lng):
    """Crea cliente + direccion 'Principal' directamente. Luego pregunta sobre parqueo."""
    admin_id = context.user_data.get("acust_admin_id")
    name = context.user_data.get("acust_new_customer_name")
    phone = context.user_data.get("acust_new_customer_phone")
    try:
        customer_id = create_admin_customer(admin_id, name, phone, None)
        address_id = create_admin_customer_address(customer_id, "Principal", address_text, city="", barrio="", lat=lat, lng=lng)
        context.user_data["acust_parking_address_id"] = address_id
        keyboard = [
            [InlineKeyboardButton("Si, hay dificultad para parquear", callback_data="acust_parking_si")],
            [InlineKeyboardButton("No / No lo se", callback_data="acust_parking_no")],
        ]
        text = (
            "Cliente '{}' guardado.\n\nTelefono: {}\nDireccion: {}\n\n"
            "En ese punto de entrega hay dificultad para parquear moto o bicicleta?\n"
            "(zona restringida, riesgo de comparendo o sin lugar seguro para dejar el vehiculo)"
        ).format(name, phone, address_text)
        if hasattr(msg_or_query, 'reply_text'):
            msg_or_query.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            msg_or_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        err_text = "Error al guardar cliente: {}".format(str(e))
        if hasattr(msg_or_query, 'reply_text'):
            msg_or_query.reply_text(err_text)
        else:
            msg_or_query.edit_message_text(err_text)
        for key in [
            "acust_new_customer_name", "acust_new_customer_phone",
            "acust_geo_mode", "acust_geo_address_input", "acust_geo_formatted",
            "acust_pending_mode", "acust_pending_address_text",
            "acust_pending_lat", "acust_pending_lng",
            "acust_pending_city", "acust_pending_barrio", "acust_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return ADMIN_CUST_MENU
    for key in [
        "acust_new_customer_name", "acust_new_customer_phone",
        "acust_geo_mode", "acust_geo_address_input", "acust_geo_formatted",
        "acust_pending_mode", "acust_pending_address_text",
        "acust_pending_lat", "acust_pending_lng",
        "acust_pending_city", "acust_pending_barrio", "acust_pending_notes",
    ]:
        context.user_data.pop(key, None)
    return ADMIN_CUST_PARKING


def admin_clientes_nuevo_nombre(update, context):
    """Recibe nombre del nuevo cliente del admin."""
    context.user_data["acust_new_customer_name"] = update.message.text.strip()
    update.message.reply_text("Escribe el telefono del cliente:")
    return ADMIN_CUST_NUEVO_TELEFONO


def admin_clientes_nuevo_telefono(update, context):
    """Recibe telefono del nuevo cliente del admin."""
    context.user_data["acust_new_customer_phone"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion de entrega del cliente:")
    return ADMIN_CUST_NUEVO_DIR_TEXT


def admin_clientes_nuevo_notas(update, context):
    """Recibe notas del nuevo cliente del admin."""
    notas = update.message.text.strip()
    if notas.lower() == "ninguna":
        notas = None
    context.user_data["acust_new_customer_notes"] = notas
    update.message.reply_text("Escribe la etiqueta de la direccion (Casa, Trabajo, Otro):")
    return ADMIN_CUST_NUEVO_DIR_LABEL


def admin_clientes_nuevo_dir_label(update, context):
    """Recibe etiqueta de direccion del nuevo cliente del admin."""
    context.user_data["acust_new_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return ADMIN_CUST_NUEVO_DIR_TEXT


def _admin_clientes_resolver_dir(update, context, texto, cb_si, cb_no, estado):
    """Aplica el pipeline de geocoding para resolver una direccion en la agenda del admin."""
    loc = resolve_location(texto)
    if not loc or loc.get("lat") is None or loc.get("lng") is None:
        update.message.reply_text(
            "No pude encontrar esa ubicacion.\n\n"
            "Intenta con:\n"
            "- Un PIN de Telegram\n"
            "- Un link de Google Maps\n"
            "- Coordenadas (ej: 4.81,-75.69)\n"
            "- Direccion con ciudad (ej: Barrio Leningrado, Pereira)"
        )
        return None

    if loc.get("method") == "geocode" and loc.get("formatted_address"):
        _agenda_emit_geo_confirmation(
            update,
            context,
            loc,
            texto,
            cb_si,
            cb_no,
            "acust_geo_formatted",
            "admin_clientes_location_confirm",
        )
        return estado

    return loc


def admin_clientes_nuevo_dir_text(update, context):
    """Recibe direccion y prepara creacion del nuevo cliente del admin."""
    address_text = update.message.text.strip()

    resolved = _admin_clientes_resolver_dir(
        update, context, address_text, "acust_geo_si", "acust_geo_no", ADMIN_CUST_NUEVO_DIR_TEXT
    )
    if resolved is None:
        return ADMIN_CUST_NUEVO_DIR_TEXT
    if isinstance(resolved, int):
        context.user_data["acust_geo_mode"] = "nuevo_cliente"
        context.user_data["acust_geo_address_input"] = address_text
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    address_to_save = resolved.get("formatted_address") or address_text
    return _admin_clientes_guardar_nuevo(update.message, context, address_to_save, lat, lng)


def admin_clientes_buscar(update, context):
    """Busca clientes del admin por nombre o telefono."""
    query_text = update.message.text.strip()
    admin_id = context.user_data.get("acust_admin_id")

    results = search_admin_customers(admin_id, query_text, limit=10)
    if not results:
        keyboard = [
            [InlineKeyboardButton("Agregar nuevo cliente", callback_data="acust_nuevo")],
            [InlineKeyboardButton("Volver al menu", callback_data="acust_volver_menu")],
        ]
        update.message.reply_text(
            "No se encontraron clientes con '{}'.".format(query_text),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CUST_MENU

    keyboard = []
    for c in results:
        btn_text = "{} - {}".format(c["name"], c["phone"])
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_ver_{}".format(c["id"]))])
    keyboard.append([InlineKeyboardButton("Volver al menu", callback_data="acust_volver_menu")])

    update.message.reply_text(
        "Resultados para '{}':".format(query_text),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_CUST_MENU


def admin_clientes_editar_nombre(update, context):
    """Actualiza el nombre del cliente del admin."""
    nuevo_nombre = update.message.text.strip()
    admin_id = context.user_data.get("acust_admin_id")
    customer_id = context.user_data.get("acust_current_customer_id")
    customer = get_admin_customer_by_id(customer_id, admin_id)

    if customer:
        update_admin_customer(customer_id, admin_id, nuevo_nombre, customer["phone"], customer["notes"])
        update.message.reply_text("Nombre actualizado a: {}".format(nuevo_nombre))
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return _admin_clientes_mostrar_menu(update, context, edit_message=False)


def admin_clientes_editar_telefono(update, context):
    """Actualiza el telefono del cliente del admin."""
    nuevo_telefono = update.message.text.strip()
    admin_id = context.user_data.get("acust_admin_id")
    customer_id = context.user_data.get("acust_current_customer_id")
    customer = get_admin_customer_by_id(customer_id, admin_id)

    if customer:
        update_admin_customer(customer_id, admin_id, customer["name"], nuevo_telefono, customer["notes"])
        update.message.reply_text("Telefono actualizado a: {}".format(nuevo_telefono))
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return _admin_clientes_mostrar_menu(update, context, edit_message=False)


def admin_clientes_editar_notas(update, context):
    """Actualiza las notas del cliente del admin."""
    nuevas_notas = update.message.text.strip()
    if nuevas_notas.lower() == "ninguna":
        nuevas_notas = None
    admin_id = context.user_data.get("acust_admin_id")
    customer_id = context.user_data.get("acust_current_customer_id")
    customer = get_admin_customer_by_id(customer_id, admin_id)

    if customer:
        update_admin_customer(customer_id, admin_id, customer["name"], customer["phone"], nuevas_notas)
        update.message.reply_text("Notas actualizadas.")
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return _admin_clientes_mostrar_menu(update, context, edit_message=False)


def admin_clientes_dir_nueva_label(update, context):
    """Recibe etiqueta de nueva direccion para cliente del admin."""
    context.user_data["acust_new_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return ADMIN_CUST_DIR_NUEVA_TEXT


def admin_clientes_dir_nueva_text(update, context):
    """Crea nueva direccion para cliente del admin."""
    address_text = update.message.text.strip()

    resolved = _admin_clientes_resolver_dir(
        update, context, address_text, "acust_geo_si", "acust_geo_no", ADMIN_CUST_DIR_NUEVA_TEXT
    )
    if resolved is None:
        return ADMIN_CUST_DIR_NUEVA_TEXT
    if isinstance(resolved, int):
        context.user_data["acust_geo_mode"] = "dir_nueva"
        context.user_data["acust_geo_address_input"] = address_text
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    address_to_save = resolved.get("formatted_address") or address_text
    context.user_data["acust_pending_mode"] = "dir_nueva"
    context.user_data["acust_pending_address_text"] = address_to_save
    context.user_data["acust_pending_lat"] = lat
    context.user_data["acust_pending_lng"] = lng
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return ADMIN_CUST_DIR_CIUDAD


def admin_clientes_geo_callback(update, context):
    """Confirma/rechaza geocoding de direccion en agenda de clientes del admin."""
    query = update.callback_query
    query.answer()

    mode = context.user_data.get("acust_geo_mode")
    if not mode:
        query.edit_message_text("Sesion de geocodificacion expirada. Escribe la direccion nuevamente.")
        return ADMIN_CUST_MENU

    if query.data == "acust_geo_si":
        formatted = context.user_data.pop("acust_geo_formatted", "")
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Escribe la ubicacion nuevamente.")
            return ADMIN_CUST_NUEVO_DIR_TEXT if mode == "nuevo_cliente" else ADMIN_CUST_DIR_NUEVA_TEXT
        logger.info(
            "[admin_clientes_location_confirm] status=confirmed mode=%s lat=%s lng=%s",
            mode,
            lat,
            lng,
        )

        if mode == "corregir_coords":
            context.user_data.pop("acust_geo_mode", None)
            customer_id = context.user_data.get("acust_current_customer_id")
            address_id = context.user_data.get("acust_current_address_id")
            address = get_admin_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
            if not address:
                query.edit_message_text("Error: direccion no encontrada.")
                return _admin_clientes_mostrar_menu(update, context, edit_message=True)
            try:
                update_admin_customer_address(
                    address_id=address_id,
                    customer_id=customer_id,
                    label=address["label"],
                    address_text=address["address_text"],
                    city=address["city"] or "",
                    barrio=address["barrio"] or "",
                    notes=address["notes"],
                    lat=lat,
                    lng=lng,
                )
                query.edit_message_text(
                    "Coordenadas actualizadas.\n"
                    "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
                )
            except Exception as e:
                query.edit_message_text("Error al actualizar: {}".format(str(e)))
            return _admin_clientes_mostrar_menu(update, context, edit_message=False)

        address_to_save = (formatted or context.user_data.get("acust_geo_address_input", "")).strip()
        if mode == "nuevo_cliente":
            context.user_data.pop("acust_geo_mode", None)
            context.user_data.pop("acust_geo_address_input", None)
            return _admin_clientes_guardar_nuevo(query, context, address_to_save, lat, lng)

        context.user_data["acust_pending_mode"] = mode
        context.user_data["acust_pending_address_text"] = address_to_save
        context.user_data["acust_pending_lat"] = lat
        context.user_data["acust_pending_lng"] = lng
        query.edit_message_text("Escribe la ciudad de la direccion:")
        return ADMIN_CUST_DIR_CIUDAD

    estado = ADMIN_CUST_NUEVO_DIR_TEXT if mode == "nuevo_cliente" else ADMIN_CUST_DIR_NUEVA_TEXT
    logger.info("[admin_clientes_location_confirm] status=rejected mode=%s", mode)
    return _geo_siguiente_o_gps(
        query,
        context,
        "acust_geo_si",
        "acust_geo_no",
        estado,
        header_text="Confirma este punto exacto antes de guardar la direccion.",
        question_text="Es esta la ubicacion correcta?",
        no_more_text=_agenda_geo_no_more_text(),
        formatted_storage_key="acust_geo_formatted",
    )


def admin_clientes_dir_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la direccion:",
        "acust_pending_city",
        ADMIN_CUST_DIR_CIUDAD,
        ADMIN_CUST_DIR_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector de la direccion:",
        options_hint="",
        set_back_step=False,
    )


def admin_clientes_dir_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la direccion:",
        "acust_pending_barrio",
        ADMIN_CUST_DIR_BARRIO,
        ADMIN_CUST_MENU,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == ADMIN_CUST_DIR_BARRIO:
        return ok_state
    barrio = context.user_data.get("acust_pending_barrio", "")

    mode = context.user_data.get("acust_pending_mode")
    address_text = context.user_data.get("acust_pending_address_text", "")
    lat = context.user_data.get("acust_pending_lat")
    lng = context.user_data.get("acust_pending_lng")
    city = context.user_data.get("acust_pending_city", "")
    notes = context.user_data.get("acust_pending_notes")

    if mode == "nuevo_cliente":
        admin_id = context.user_data.get("acust_admin_id")
        name = context.user_data.get("acust_new_customer_name")
        phone = context.user_data.get("acust_new_customer_phone")
        customer_notes = context.user_data.get("acust_new_customer_notes")
        label = context.user_data.get("acust_new_address_label")
        try:
            customer_id = create_admin_customer(admin_id, name, phone, customer_notes)
            address_id = create_admin_customer_address(customer_id, label, address_text, city=city, barrio=barrio, lat=lat, lng=lng)
            context.user_data["acust_parking_address_id"] = address_id
            keyboard = [
                [InlineKeyboardButton("Si, hay dificultad para parquear", callback_data="acust_parking_si")],
                [InlineKeyboardButton("No / No lo se", callback_data="acust_parking_no")],
            ]
            update.message.reply_text(
                "Cliente '{}' creado exitosamente.\n\nTelefono: {}\nDireccion ({}): {}\n\n"
                "En ese punto de entrega hay dificultad para parquear moto o bicicleta?\n"
                "(zona restringida, riesgo de comparendo o sin lugar seguro para dejar el vehiculo)".format(
                    name, phone, label, address_text
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            update.message.reply_text("Error al crear cliente: {}".format(str(e)))
            for key in [
                "acust_new_customer_name", "acust_new_customer_phone", "acust_new_customer_notes",
                "acust_new_address_label", "acust_geo_mode", "acust_geo_address_input",
                "acust_pending_mode", "acust_pending_address_text", "acust_pending_lat",
                "acust_pending_lng", "acust_pending_city", "acust_pending_barrio", "acust_pending_notes",
            ]:
                context.user_data.pop(key, None)
            return ADMIN_CUST_MENU

        for key in [
            "acust_new_customer_name", "acust_new_customer_phone", "acust_new_customer_notes",
            "acust_new_address_label", "acust_geo_mode", "acust_geo_address_input",
            "acust_pending_mode", "acust_pending_address_text", "acust_pending_lat",
            "acust_pending_lng", "acust_pending_city", "acust_pending_barrio", "acust_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return ADMIN_CUST_PARKING

    if mode == "dir_nueva":
        customer_id = context.user_data.get("acust_current_customer_id")
        label = context.user_data.get("acust_new_address_label")
        try:
            create_admin_customer_address(customer_id, label, address_text, city=city, barrio=barrio, lat=lat, lng=lng)
            update.message.reply_text("Direccion agregada: {} - {}".format(label, address_text))
        except Exception as e:
            update.message.reply_text("Error: {}".format(str(e)))

        for key in [
            "acust_new_address_label", "acust_geo_mode", "acust_geo_address_input",
            "acust_pending_mode", "acust_pending_address_text", "acust_pending_lat",
            "acust_pending_lng", "acust_pending_city", "acust_pending_barrio", "acust_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    if mode == "dir_editar":
        customer_id = context.user_data.get("acust_current_customer_id")
        address_id = context.user_data.get("acust_current_address_id")
        label = context.user_data.get("acust_edit_address_label")
        try:
            update_admin_customer_address(
                address_id=address_id,
                customer_id=customer_id,
                label=label,
                address_text=address_text,
                city=city,
                barrio=barrio,
                notes=notes,
                lat=lat,
                lng=lng,
            )
            update.message.reply_text("Direccion actualizada.")
        except Exception as e:
            update.message.reply_text("Error: {}".format(str(e)))

        for key in [
            "acust_edit_address_label", "acust_current_address_id",
            "acust_pending_mode", "acust_pending_address_text", "acust_pending_lat",
            "acust_pending_lng", "acust_pending_city", "acust_pending_barrio", "acust_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    update.message.reply_text("Error: sesion expirada. Intenta de nuevo desde el menu.")
    for key in [
        "acust_pending_mode", "acust_pending_address_text", "acust_pending_lat",
        "acust_pending_lng", "acust_pending_city", "acust_pending_barrio", "acust_pending_notes",
    ]:
        context.user_data.pop(key, None)
    return _admin_clientes_mostrar_menu(update, context, edit_message=False)


def admin_clientes_dir_editar_label(update, context):
    """Recibe nueva etiqueta para editar direccion del admin."""
    context.user_data["acust_edit_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la nueva direccion completa:")
    return ADMIN_CUST_DIR_EDITAR_TEXT


def admin_clientes_dir_editar_text(update, context):
    """Actualiza direccion existente del admin."""
    address_text = update.message.text.strip()
    customer_id = context.user_data.get("acust_current_customer_id")
    address_id = context.user_data.get("acust_current_address_id")

    address = get_admin_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("acust_edit_address_label", None)
        context.user_data.pop("acust_current_address_id", None)
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    resolved = _admin_clientes_resolver_dir(
        update, context, address_text, "acust_geo_si", "acust_geo_no", ADMIN_CUST_DIR_EDITAR_TEXT
    )
    if resolved is None:
        return ADMIN_CUST_DIR_EDITAR_TEXT
    if isinstance(resolved, int):
        context.user_data["acust_geo_mode"] = "dir_editar"
        context.user_data["acust_geo_address_input"] = address_text
        return resolved

    context.user_data["acust_pending_mode"] = "dir_editar"
    context.user_data["acust_pending_address_text"] = resolved.get("formatted_address") or address_text
    context.user_data["acust_pending_lat"] = resolved.get("lat")
    context.user_data["acust_pending_lng"] = resolved.get("lng")
    context.user_data["acust_pending_notes"] = address.get("notes") if hasattr(address, "get") else address["notes"]
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return ADMIN_CUST_DIR_CIUDAD


def admin_clientes_dir_editar_nota(update, context):
    """Actualiza la nota para entrega de una direccion del admin."""
    nota_text = update.message.text.strip()
    customer_id = context.user_data.get("acust_current_customer_id")
    address_id = context.user_data.get("acust_current_address_id")

    address = get_admin_customer_address_by_id(address_id, customer_id)
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    nueva_nota = None if nota_text.lower() == "ninguna" else nota_text

    try:
        update_admin_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"],
            barrio=address["barrio"],
            notes=nueva_nota,
            lat=address["lat"],
            lng=address["lng"]
        )
        if nueva_nota:
            update.message.reply_text("Nota para entrega actualizada.")
        else:
            update.message.reply_text("Nota para entrega eliminada.")
    except Exception as e:
        update.message.reply_text("Error: {}".format(str(e)))

    context.user_data.pop("acust_current_address_id", None)
    return _admin_clientes_mostrar_menu(update, context, edit_message=False)


def admin_clientes_dir_corregir_handler(update, context):
    """Recibe texto/link para corregir coordenadas de una direccion del cliente del admin."""
    text = update.message.text.strip()
    if text.lower() == "cancelar":
        context.user_data.pop("acust_geo_mode", None)
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    customer_id = context.user_data.get("acust_current_customer_id")
    address_id = context.user_data.get("acust_current_address_id")
    address = get_admin_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("acust_geo_mode", None)
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    context.user_data["acust_geo_mode"] = "corregir_coords"
    context.user_data["acust_geo_address_input"] = text

    resolved = _admin_clientes_resolver_dir(
        update, context, text, "acust_geo_si", "acust_geo_no", ADMIN_CUST_DIR_CORREGIR
    )
    if resolved is None:
        return ADMIN_CUST_DIR_CORREGIR
    if isinstance(resolved, int):
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    if lat is None or lng is None:
        update.message.reply_text("No se pudo obtener coordenadas. Intenta de nuevo o escribe 'cancelar'.")
        return ADMIN_CUST_DIR_CORREGIR

    try:
        update_admin_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"] or "",
            barrio=address["barrio"] or "",
            notes=address["notes"],
            lat=lat,
            lng=lng,
        )
        update.message.reply_text(
            "Coordenadas actualizadas.\n"
            "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
        )
    except Exception as e:
        update.message.reply_text("Error al actualizar: {}".format(str(e)))

    context.user_data.pop("acust_geo_mode", None)
    context.user_data.pop("acust_geo_address_input", None)
    return _admin_clientes_mostrar_menu(update, context, edit_message=False)


def admin_clientes_dir_corregir_location_handler(update, context):
    """Recibe pin GPS para corregir coordenadas de una direccion del cliente del admin."""
    loc = update.message.location
    lat = loc.latitude
    lng = loc.longitude
    customer_id = context.user_data.get("acust_current_customer_id")
    address_id = context.user_data.get("acust_current_address_id")
    address = get_admin_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("acust_geo_mode", None)
        return _admin_clientes_mostrar_menu(update, context, edit_message=False)

    try:
        update_admin_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"] or "",
            barrio=address["barrio"] or "",
            notes=address["notes"],
            lat=lat,
            lng=lng,
        )
        update.message.reply_text(
            "Coordenadas actualizadas.\n"
            "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
        )
    except Exception as e:
        update.message.reply_text("Error al actualizar: {}".format(str(e)))

    context.user_data.pop("acust_geo_mode", None)
    return _admin_clientes_mostrar_menu(update, context, edit_message=False)

# =========================
# Agenda de clientes del Aliado (ally_clientes_conv)
# Prefijo callbacks: allycust_
# Prefijo user_data: allycust_
# =========================

def ally_clientes_cmd(update, context):
    """Entry point de la agenda de clientes del aliado."""
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        update.message.reply_text("Aun no estas registrado. Usa /start primero.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text("Este menu es solo para aliados.")
        return ConversationHandler.END

    if ally["status"] != "APPROVED":
        update.message.reply_text("Tu registro como aliado aun no ha sido aprobado.")
        return ConversationHandler.END

    for key in list(context.user_data.keys()):
        if key.startswith("allycust_"):
            del context.user_data[key]
    context.user_data["allycust_ally_id"] = ally["id"]

    return _ally_clientes_mostrar_menu(update, context, edit_message=False)


def _ally_clientes_mostrar_menu(update, context, edit_message=False):
    """Muestra el menu principal de la agenda de clientes del aliado."""
    keyboard = [
        [InlineKeyboardButton("Nuevo cliente", callback_data="allycust_nuevo")],
        [InlineKeyboardButton("Buscar cliente", callback_data="allycust_buscar")],
        [InlineKeyboardButton("Mis clientes", callback_data="allycust_lista")],
        [InlineKeyboardButton("Clientes archivados", callback_data="allycust_archivados")],
        [InlineKeyboardButton("Cerrar", callback_data="allycust_cerrar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "AGENDA DE CLIENTES\n\nSelecciona una opcion:"

    if edit_message and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update.effective_message.reply_text(text, reply_markup=reply_markup)

    return ALLY_CUST_MENU


def ally_clientes_menu_callback(update, context):
    """Maneja los callbacks del menu de clientes del aliado."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("allycust_ally_id")

    if not ally_id:
        query.edit_message_text("Sesion expirada. Vuelve al menu e inicia de nuevo.")
        return ConversationHandler.END

    if data == "allycust_nuevo":
        query.edit_message_text("NUEVO CLIENTE\n\nEscribe el nombre del cliente:")
        return ALLY_CUST_NUEVO_NOMBRE

    elif data == "allycust_buscar":
        query.edit_message_text("BUSCAR CLIENTE\n\nEscribe el nombre o telefono a buscar:")
        return ALLY_CUST_BUSCAR

    elif data == "allycust_lista":
        customers = list_ally_customers(ally_id, limit=10, include_inactive=False)
        if not customers:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="allycust_volver_menu")]]
            query.edit_message_text(
                "No tienes clientes guardados.\n\n"
                "Usa 'Nuevo cliente' para agregar uno.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ALLY_CUST_MENU

        keyboard = []
        for c in customers:
            btn_text = "{} - {}".format(c["name"], c["phone"])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="allycust_ver_{}".format(c["id"]))])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="allycust_volver_menu")])
        query.edit_message_text(
            "MIS CLIENTES\n\nSelecciona un cliente para ver detalles:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ALLY_CUST_MENU

    elif data == "allycust_archivados":
        customers = list_ally_customers(ally_id, limit=20, include_inactive=True)
        archived = [c for c in customers if c["status"] == "INACTIVE"]
        if not archived:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="allycust_volver_menu")]]
            query.edit_message_text("No tienes clientes archivados.", reply_markup=InlineKeyboardMarkup(keyboard))
            return ALLY_CUST_MENU

        keyboard = []
        for c in archived:
            btn_text = "{} - {}".format(c["name"], c["phone"])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="allycust_restaurar_{}".format(c["id"]))])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="allycust_volver_menu")])
        query.edit_message_text(
            "CLIENTES ARCHIVADOS\n\nSelecciona uno para restaurar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ALLY_CUST_MENU

    elif data == "allycust_volver_menu":
        return _ally_clientes_mostrar_menu(update, context, edit_message=True)

    elif data == "allycust_cerrar":
        query.edit_message_text("Agenda de clientes cerrada.")
        for key in list(context.user_data.keys()):
            if key.startswith("allycust_"):
                del context.user_data[key]
        return ConversationHandler.END

    elif data.startswith("allycust_ver_"):
        customer_id = int(data.replace("allycust_ver_", ""))
        return _ally_clientes_ver_cliente(query, context, customer_id)

    elif data.startswith("allycust_restaurar_"):
        customer_id = int(data.replace("allycust_restaurar_", ""))
        if restore_ally_customer(customer_id, ally_id):
            query.edit_message_text("Cliente restaurado exitosamente.")
        else:
            query.edit_message_text("No se pudo restaurar el cliente.")
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    return ALLY_CUST_MENU


def _ally_clientes_ver_cliente(query, context, customer_id):
    """Muestra detalles de un cliente del aliado y sus opciones."""
    ally_id = context.user_data.get("allycust_ally_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if not customer:
        query.edit_message_text("Cliente no encontrado.")
        return ALLY_CUST_MENU

    context.user_data["allycust_current_customer_id"] = customer_id

    addresses = list_customer_addresses(customer_id)
    addr_text = ""
    if addresses:
        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            parking_status = addr["parking_status"] if "parking_status" in addr.keys() else "NOT_ASKED"
            parking_tag = " [parqueo dificil]" if parking_status in ("ALLY_YES", "ADMIN_YES") else ""
            addr_text += "- {}{}: {}...\n".format(label, parking_tag, addr["address_text"][:35])
    else:
        addr_text = "Sin direcciones guardadas\n"

    nota_interna = customer["notes"] or "Sin notas"

    keyboard = [
        [InlineKeyboardButton("Direcciones", callback_data="allycust_dirs")],
        [InlineKeyboardButton("Editar", callback_data="allycust_editar")],
        [InlineKeyboardButton("Archivar", callback_data="allycust_archivar")],
        [InlineKeyboardButton("Volver", callback_data="allycust_volver_menu")],
    ]
    query.edit_message_text(
        "Cliente: {}\n"
        "Telefono: {}\n\n"
        "Nota interna:\n{}\n\n"
        "Direcciones guardadas:\n{}".format(customer["name"], customer["phone"], nota_interna, addr_text),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ALLY_CUST_VER


def ally_clientes_ver_callback(update, context):
    """Maneja callbacks de la vista de cliente del aliado."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("allycust_ally_id")
    customer_id = context.user_data.get("allycust_current_customer_id")

    if data == "allycust_dirs":
        addresses = list_customer_addresses(customer_id)
        keyboard = []
        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            btn_text = "{}: {}...".format(label, addr["address_text"][:25])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="allycust_dir_ver_{}".format(addr["id"]))])
        keyboard.append([InlineKeyboardButton("Agregar direccion", callback_data="allycust_dir_nueva")])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="allycust_ver_{}".format(customer_id))])
        query.edit_message_text(
            "DIRECCIONES DEL CLIENTE\n\nSelecciona una para editar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ALLY_CUST_VER

    elif data == "allycust_editar":
        keyboard = [
            [InlineKeyboardButton("Editar nombre", callback_data="allycust_edit_nombre")],
            [InlineKeyboardButton("Editar telefono", callback_data="allycust_edit_telefono")],
            [InlineKeyboardButton("Editar notas", callback_data="allycust_edit_notas")],
            [InlineKeyboardButton("Volver", callback_data="allycust_ver_{}".format(customer_id))],
        ]
        query.edit_message_text("Que deseas editar?", reply_markup=InlineKeyboardMarkup(keyboard))
        return ALLY_CUST_VER

    elif data == "allycust_edit_nombre":
        query.edit_message_text("Escribe el nuevo nombre del cliente:")
        return ALLY_CUST_EDITAR_NOMBRE

    elif data == "allycust_edit_telefono":
        query.edit_message_text("Escribe el nuevo telefono del cliente:")
        return ALLY_CUST_EDITAR_TEL

    elif data == "allycust_edit_notas":
        query.edit_message_text("Escribe las nuevas notas del cliente (o 'ninguna' para borrar):")
        return ALLY_CUST_EDITAR_NOTAS

    elif data == "allycust_archivar":
        if archive_ally_customer(customer_id, ally_id):
            query.edit_message_text("Cliente archivado exitosamente.")
        else:
            query.edit_message_text("No se pudo archivar el cliente.")
        context.user_data.pop("allycust_current_customer_id", None)
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    elif data == "allycust_dir_nueva":
        query.edit_message_text("NUEVA DIRECCION\n\nEscribe la etiqueta (Casa, Trabajo, Otro):")
        return ALLY_CUST_DIR_NUEVA_LABEL

    elif data.startswith("allycust_dir_ver_"):
        address_id = int(data.replace("allycust_dir_ver_", ""))
        address = get_customer_address_by_id(address_id, customer_id)
        if not address:
            query.edit_message_text("Direccion no encontrada.")
            return ALLY_CUST_VER

        context.user_data["allycust_current_address_id"] = address_id
        label = address["label"] or "Sin etiqueta"
        nota_entrega = address["notes"] or "Sin nota"
        lat = address["lat"]
        lng = address["lng"]

        if lat is not None and lng is not None:
            try:
                context.bot.send_location(chat_id=query.message.chat_id, latitude=float(lat), longitude=float(lng))
            except Exception:
                pass
            coords_text = "Coordenadas: {:.5f}, {:.5f}".format(float(lat), float(lng))
            btn_coords = "Corregir coordenadas"
        else:
            coords_text = "Sin coordenadas"
            btn_coords = "Agregar coordenadas"

        keyboard = [
            [InlineKeyboardButton("Editar", callback_data="allycust_dir_editar")],
            [InlineKeyboardButton("Editar nota entrega", callback_data="allycust_dir_edit_nota")],
            [InlineKeyboardButton(btn_coords, callback_data="allycust_dir_corregir_coords")],
            [InlineKeyboardButton("Archivar", callback_data="allycust_dir_archivar")],
            [InlineKeyboardButton("Volver", callback_data="allycust_dirs")],
        ]
        query.edit_message_text(
            "{}\n{}\n\nNota para entrega:\n{}\n\n{}".format(label, address["address_text"], nota_entrega, coords_text),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ALLY_CUST_VER

    elif data == "allycust_dir_corregir_coords":
        query.edit_message_text(
            "Corregir / agregar coordenadas\n\n"
            "Envia un pin de ubicacion de Telegram, un link de Google Maps, "
            "o escribe las coordenadas (ej: 4.81,-75.69).\n\n"
            "Escribe 'cancelar' para volver."
        )
        context.user_data["allycust_geo_mode"] = "corregir_coords"
        return ALLY_CUST_DIR_CORREGIR

    elif data == "allycust_dir_editar":
        query.edit_message_text("Escribe la nueva etiqueta (Casa, Trabajo, Otro):")
        return ALLY_CUST_DIR_EDITAR_LABEL

    elif data == "allycust_dir_edit_nota":
        query.edit_message_text(
            "Escribe la nota para entrega.\n"
            "Esta nota sera visible para el repartidor.\n\n"
            "Escribe 'ninguna' para borrar la nota:"
        )
        return ALLY_CUST_DIR_EDITAR_NOTA

    elif data == "allycust_dir_archivar":
        address_id = context.user_data.get("allycust_current_address_id")
        if archive_customer_address(address_id, customer_id):
            query.edit_message_text("Direccion archivada.")
        else:
            query.edit_message_text("No se pudo archivar la direccion.")
        context.user_data.pop("allycust_current_address_id", None)
        return _ally_clientes_ver_cliente(query, context, customer_id)

    elif data.startswith("allycust_ver_"):
        cid = int(data.replace("allycust_ver_", ""))
        return _ally_clientes_ver_cliente(query, context, cid)

    elif data == "allycust_volver_menu":
        context.user_data.pop("allycust_current_customer_id", None)
        return _ally_clientes_mostrar_menu(update, context, edit_message=True)

    return ALLY_CUST_VER


def _ally_clientes_guardar_nuevo(msg_or_query, context, address_text, lat, lng):
    """Crea cliente + direccion 'Principal' directamente. Luego pregunta sobre parqueadero."""
    ally_id = context.user_data.get("allycust_ally_id")
    name = context.user_data.get("allycust_new_customer_name")
    phone = context.user_data.get("allycust_new_customer_phone")
    try:
        customer_id = create_ally_customer(ally_id, name, phone, None)
        address_id = create_customer_address(customer_id, "Principal", address_text, city="", barrio="", lat=lat, lng=lng)
        parking_enabled = get_ally_parking_fee_enabled(ally_id) if ally_id else False
        if parking_enabled:
            context.user_data["allycust_parking_address_id"] = address_id
            keyboard = [
                [InlineKeyboardButton("Si, hay dificultad para parquear", callback_data="allycust_parking_si")],
                [InlineKeyboardButton("No / No lo se", callback_data="allycust_parking_no")],
            ]
            text = (
                "Cliente '{}' guardado.\n\n"
                "Telefono: {}\n"
                "Direccion: {}\n\n"
                "En ese punto de entrega hay dificultad para parquear moto o bicicleta?\n"
                "(zona restringida, riesgo de comparendo o sin lugar seguro para dejar el vehiculo)"
            ).format(name, phone, address_text)
            if hasattr(msg_or_query, 'reply_text'):
                msg_or_query.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                msg_or_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            text = "Cliente '{}' guardado.\n\nTelefono: {}\nDireccion: {}".format(name, phone, address_text)
            if hasattr(msg_or_query, 'reply_text'):
                msg_or_query.reply_text(text)
            else:
                msg_or_query.edit_message_text(text)
    except Exception as e:
        err_text = "Error al guardar cliente: {}".format(str(e))
        if hasattr(msg_or_query, 'reply_text'):
            msg_or_query.reply_text(err_text)
        else:
            msg_or_query.edit_message_text(err_text)
        for key in [
            "allycust_new_customer_name", "allycust_new_customer_phone",
            "allycust_geo_mode", "allycust_geo_address_input", "allycust_geo_formatted",
            "allycust_pending_mode", "allycust_pending_address_text",
            "allycust_pending_lat", "allycust_pending_lng",
            "allycust_pending_city", "allycust_pending_barrio", "allycust_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return ALLY_CUST_MENU
    for key in [
        "allycust_new_customer_name", "allycust_new_customer_phone",
        "allycust_geo_mode", "allycust_geo_address_input", "allycust_geo_formatted",
        "allycust_pending_mode", "allycust_pending_address_text",
        "allycust_pending_lat", "allycust_pending_lng",
        "allycust_pending_city", "allycust_pending_barrio", "allycust_pending_notes",
    ]:
        context.user_data.pop(key, None)
    if parking_enabled:
        return ALLY_CUST_PARKING
    return ALLY_CUST_MENU


def ally_clientes_nuevo_nombre(update, context):
    context.user_data["allycust_new_customer_name"] = update.message.text.strip()
    update.message.reply_text("Escribe el telefono del cliente:")
    return ALLY_CUST_NUEVO_TEL


def ally_clientes_nuevo_telefono(update, context):
    context.user_data["allycust_new_customer_phone"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion de entrega del cliente:")
    return ALLY_CUST_NUEVO_DIR_TEXT


def ally_clientes_nuevo_notas(update, context):
    notas = update.message.text.strip()
    if notas.lower() == "ninguna":
        notas = None
    context.user_data["allycust_new_customer_notes"] = notas
    update.message.reply_text("Escribe la etiqueta de la direccion (Casa, Trabajo, Otro):")
    return ALLY_CUST_NUEVO_DIR_LABEL


def ally_clientes_nuevo_dir_label(update, context):
    context.user_data["allycust_new_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return ALLY_CUST_NUEVO_DIR_TEXT


def _ally_clientes_resolver_dir(update, context, texto, cb_si, cb_no, estado):
    """Aplica el pipeline de geocoding para resolver una direccion en la agenda del aliado."""
    loc = resolve_location(texto)
    if not loc or loc.get("lat") is None or loc.get("lng") is None:
        update.message.reply_text(
            "No pude encontrar esa ubicacion.\n\n"
            "Intenta con:\n"
            "- Un PIN de Telegram\n"
            "- Un link de Google Maps\n"
            "- Coordenadas (ej: 4.81,-75.69)\n"
            "- Direccion con ciudad (ej: Barrio Leningrado, Pereira)"
        )
        return None

    if loc.get("method") == "geocode" and loc.get("formatted_address"):
        _agenda_emit_geo_confirmation(
            update,
            context,
            loc,
            texto,
            cb_si,
            cb_no,
            "allycust_geo_formatted",
            "ally_clientes_location_confirm",
        )
        return estado

    return loc


def ally_clientes_nuevo_dir_text(update, context):
    address_text = update.message.text.strip()
    resolved = _ally_clientes_resolver_dir(
        update, context, address_text, "allycust_geo_si", "allycust_geo_no", ALLY_CUST_NUEVO_DIR_TEXT
    )
    if resolved is None:
        return ALLY_CUST_NUEVO_DIR_TEXT
    if isinstance(resolved, int):
        context.user_data["allycust_geo_mode"] = "nuevo_cliente"
        context.user_data["allycust_geo_address_input"] = address_text
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    address_to_save = resolved.get("formatted_address") or address_text
    return _ally_clientes_guardar_nuevo(update.message, context, address_to_save, lat, lng)


def ally_clientes_buscar(update, context):
    query_text = update.message.text.strip()
    ally_id = context.user_data.get("allycust_ally_id")
    results = search_ally_customers(ally_id, query_text, limit=10)
    if not results:
        keyboard = [
            [InlineKeyboardButton("Agregar nuevo cliente", callback_data="allycust_nuevo")],
            [InlineKeyboardButton("Volver al menu", callback_data="allycust_volver_menu")],
        ]
        update.message.reply_text(
            "No se encontraron clientes con '{}'.".format(query_text),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ALLY_CUST_MENU

    keyboard = []
    for c in results:
        btn_text = "{} - {}".format(c["name"], c["phone"])
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="allycust_ver_{}".format(c["id"]))])
    keyboard.append([InlineKeyboardButton("Volver al menu", callback_data="allycust_volver_menu")])
    update.message.reply_text(
        "Resultados para '{}':".format(query_text),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ALLY_CUST_MENU


def ally_clientes_editar_nombre(update, context):
    nuevo_nombre = update.message.text.strip()
    ally_id = context.user_data.get("allycust_ally_id")
    customer_id = context.user_data.get("allycust_current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)
    if customer:
        update_ally_customer(customer_id, ally_id, nuevo_nombre, customer["phone"], customer["notes"])
        update.message.reply_text("Nombre actualizado a: {}".format(nuevo_nombre))
    else:
        update.message.reply_text("Error: cliente no encontrado.")
    return _ally_clientes_mostrar_menu(update, context, edit_message=False)


def ally_clientes_editar_telefono(update, context):
    nuevo_telefono = update.message.text.strip()
    ally_id = context.user_data.get("allycust_ally_id")
    customer_id = context.user_data.get("allycust_current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)
    if customer:
        update_ally_customer(customer_id, ally_id, customer["name"], nuevo_telefono, customer["notes"])
        update.message.reply_text("Telefono actualizado a: {}".format(nuevo_telefono))
    else:
        update.message.reply_text("Error: cliente no encontrado.")
    return _ally_clientes_mostrar_menu(update, context, edit_message=False)


def ally_clientes_editar_notas(update, context):
    nuevas_notas = update.message.text.strip()
    if nuevas_notas.lower() == "ninguna":
        nuevas_notas = None
    ally_id = context.user_data.get("allycust_ally_id")
    customer_id = context.user_data.get("allycust_current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)
    if customer:
        update_ally_customer(customer_id, ally_id, customer["name"], customer["phone"], nuevas_notas)
        update.message.reply_text("Notas actualizadas.")
    else:
        update.message.reply_text("Error: cliente no encontrado.")
    return _ally_clientes_mostrar_menu(update, context, edit_message=False)


def ally_clientes_dir_nueva_label(update, context):
    context.user_data["allycust_new_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return ALLY_CUST_DIR_NUEVA_TEXT


def ally_clientes_dir_nueva_text(update, context):
    address_text = update.message.text.strip()
    resolved = _ally_clientes_resolver_dir(
        update, context, address_text, "allycust_geo_si", "allycust_geo_no", ALLY_CUST_DIR_NUEVA_TEXT
    )
    if resolved is None:
        return ALLY_CUST_DIR_NUEVA_TEXT
    if isinstance(resolved, int):
        context.user_data["allycust_geo_mode"] = "dir_nueva"
        context.user_data["allycust_geo_address_input"] = address_text
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    address_to_save = resolved.get("formatted_address") or address_text
    context.user_data["allycust_pending_mode"] = "dir_nueva"
    context.user_data["allycust_pending_address_text"] = address_to_save
    context.user_data["allycust_pending_lat"] = lat
    context.user_data["allycust_pending_lng"] = lng
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return ALLY_CUST_DIR_CIUDAD


def ally_clientes_geo_callback(update, context):
    """Confirma/rechaza geocoding de direccion en agenda de clientes del aliado."""
    query = update.callback_query
    query.answer()

    mode = context.user_data.get("allycust_geo_mode")
    if not mode:
        query.edit_message_text("Sesion de geocodificacion expirada. Escribe la direccion nuevamente.")
        return ALLY_CUST_MENU

    if query.data == "allycust_geo_si":
        formatted = context.user_data.pop("allycust_geo_formatted", "")
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Escribe la ubicacion nuevamente.")
            return ALLY_CUST_NUEVO_DIR_TEXT if mode == "nuevo_cliente" else ALLY_CUST_DIR_NUEVA_TEXT
        logger.info(
            "[ally_clientes_location_confirm] status=confirmed mode=%s lat=%s lng=%s",
            mode,
            lat,
            lng,
        )

        if mode == "corregir_coords":
            context.user_data.pop("allycust_geo_mode", None)
            customer_id = context.user_data.get("allycust_current_customer_id")
            address_id = context.user_data.get("allycust_current_address_id")
            address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
            if not address:
                query.edit_message_text("Error: direccion no encontrada.")
                return _ally_clientes_mostrar_menu(update, context, edit_message=True)
            try:
                update_customer_address(
                    address_id=address_id, customer_id=customer_id,
                    label=address["label"], address_text=address["address_text"],
                    city=address["city"] or "", barrio=address["barrio"] or "",
                    notes=address["notes"], lat=lat, lng=lng,
                )
                query.edit_message_text(
                    "Coordenadas actualizadas.\nLat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
                )
            except Exception as e:
                query.edit_message_text("Error al actualizar: {}".format(str(e)))
            return _ally_clientes_mostrar_menu(update, context, edit_message=False)

        address_to_save = (formatted or context.user_data.get("allycust_geo_address_input", "")).strip()
        if mode == "nuevo_cliente":
            context.user_data.pop("allycust_geo_mode", None)
            context.user_data.pop("allycust_geo_address_input", None)
            return _ally_clientes_guardar_nuevo(query, context, address_to_save, lat, lng)

        context.user_data["allycust_pending_mode"] = mode
        context.user_data["allycust_pending_address_text"] = address_to_save
        context.user_data["allycust_pending_lat"] = lat
        context.user_data["allycust_pending_lng"] = lng
        query.edit_message_text("Escribe la ciudad de la direccion:")
        return ALLY_CUST_DIR_CIUDAD

    estado = ALLY_CUST_NUEVO_DIR_TEXT if mode == "nuevo_cliente" else ALLY_CUST_DIR_NUEVA_TEXT
    logger.info("[ally_clientes_location_confirm] status=rejected mode=%s", mode)
    return _geo_siguiente_o_gps(
        query,
        context,
        "allycust_geo_si",
        "allycust_geo_no",
        estado,
        header_text="Confirma este punto exacto antes de guardar la direccion.",
        question_text="Es esta la ubicacion correcta?",
        no_more_text=_agenda_geo_no_more_text(),
        formatted_storage_key="allycust_geo_formatted",
    )


def ally_clientes_dir_ciudad_handler(update, context):
    return _handle_text_field_input(
        update, context,
        "Por favor escribe la ciudad de la direccion:",
        "allycust_pending_city",
        ALLY_CUST_DIR_CIUDAD, ALLY_CUST_DIR_BARRIO,
        flow=None, next_prompt="Escribe el barrio o sector de la direccion:",
        options_hint="", set_back_step=False,
    )


def ally_clientes_dir_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update, context,
        "Por favor escribe el barrio o sector de la direccion:",
        "allycust_pending_barrio",
        ALLY_CUST_DIR_BARRIO, ALLY_CUST_MENU,
        flow=None, next_prompt=None, options_hint="", set_back_step=False,
    )
    if ok_state == ALLY_CUST_DIR_BARRIO:
        return ok_state

    barrio = context.user_data.get("allycust_pending_barrio", "")
    mode = context.user_data.get("allycust_pending_mode")
    address_text = context.user_data.get("allycust_pending_address_text", "")
    lat = context.user_data.get("allycust_pending_lat")
    lng = context.user_data.get("allycust_pending_lng")
    city = context.user_data.get("allycust_pending_city", "")
    notes = context.user_data.get("allycust_pending_notes")

    _ALLYCUST_PENDING_KEYS = [
        "allycust_geo_mode", "allycust_geo_address_input", "allycust_geo_formatted",
        "allycust_pending_mode", "allycust_pending_address_text", "allycust_pending_lat",
        "allycust_pending_lng", "allycust_pending_city", "allycust_pending_barrio", "allycust_pending_notes",
    ]

    if mode == "nuevo_cliente":
        ally_id = context.user_data.get("allycust_ally_id")
        name = context.user_data.get("allycust_new_customer_name")
        phone = context.user_data.get("allycust_new_customer_phone")
        customer_notes = context.user_data.get("allycust_new_customer_notes")
        label = context.user_data.get("allycust_new_address_label")
        try:
            customer_id = create_ally_customer(ally_id, name, phone, customer_notes)
            address_id = create_customer_address(customer_id, label, address_text, city=city, barrio=barrio, lat=lat, lng=lng)
            parking_enabled = get_ally_parking_fee_enabled(ally_id) if ally_id else False
            if parking_enabled:
                context.user_data["allycust_parking_address_id"] = address_id
                keyboard = [
                    [InlineKeyboardButton("Si, hay dificultad para parquear", callback_data="allycust_parking_si")],
                    [InlineKeyboardButton("No / No lo se", callback_data="allycust_parking_no")],
                ]
                update.message.reply_text(
                    "Cliente '{}' creado exitosamente.\n\nTelefono: {}\nDireccion ({}): {}\n\n"
                    "En ese punto de entrega hay dificultad para parquear moto o bicicleta?\n"
                    "(zona restringida, riesgo de comparendo o sin lugar seguro para dejar el vehiculo)".format(
                        name, phone, label, address_text
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                update.message.reply_text(
                    "Cliente '{}' creado exitosamente.\n\nTelefono: {}\nDireccion ({}): {}".format(
                        name, phone, label, address_text
                    )
                )
        except Exception as e:
            update.message.reply_text("Error al crear cliente: {}".format(str(e)))
            for key in _ALLYCUST_PENDING_KEYS + ["allycust_new_customer_name", "allycust_new_customer_phone",
                                                  "allycust_new_customer_notes", "allycust_new_address_label"]:
                context.user_data.pop(key, None)
            return ALLY_CUST_MENU
        for key in _ALLYCUST_PENDING_KEYS + ["allycust_new_customer_name", "allycust_new_customer_phone",
                                              "allycust_new_customer_notes", "allycust_new_address_label"]:
            context.user_data.pop(key, None)
        if ally_id and get_ally_parking_fee_enabled(ally_id):
            return ALLY_CUST_PARKING
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    if mode == "dir_nueva":
        customer_id = context.user_data.get("allycust_current_customer_id")
        label = context.user_data.get("allycust_new_address_label")
        try:
            create_customer_address(customer_id, label, address_text, city=city, barrio=barrio, lat=lat, lng=lng)
            update.message.reply_text("Direccion agregada: {} - {}".format(label, address_text))
        except Exception as e:
            update.message.reply_text("Error: {}".format(str(e)))
        for key in _ALLYCUST_PENDING_KEYS + ["allycust_new_address_label"]:
            context.user_data.pop(key, None)
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    if mode == "dir_editar":
        customer_id = context.user_data.get("allycust_current_customer_id")
        address_id = context.user_data.get("allycust_current_address_id")
        label = context.user_data.get("allycust_edit_address_label")
        try:
            update_customer_address(
                address_id=address_id, customer_id=customer_id,
                label=label, address_text=address_text,
                city=city, barrio=barrio, notes=notes, lat=lat, lng=lng,
            )
            update.message.reply_text("Direccion actualizada.")
        except Exception as e:
            update.message.reply_text("Error: {}".format(str(e)))
        for key in _ALLYCUST_PENDING_KEYS + ["allycust_edit_address_label", "allycust_current_address_id"]:
            context.user_data.pop(key, None)
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    update.message.reply_text("Error: sesion expirada. Intenta de nuevo desde el menu.")
    for key in _ALLYCUST_PENDING_KEYS:
        context.user_data.pop(key, None)
    return _ally_clientes_mostrar_menu(update, context, edit_message=False)


def ally_clientes_dir_editar_label(update, context):
    context.user_data["allycust_edit_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la nueva direccion completa:")
    return ALLY_CUST_DIR_EDITAR_TEXT


def ally_clientes_dir_editar_text(update, context):
    address_text = update.message.text.strip()
    customer_id = context.user_data.get("allycust_current_customer_id")
    address_id = context.user_data.get("allycust_current_address_id")
    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("allycust_edit_address_label", None)
        context.user_data.pop("allycust_current_address_id", None)
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    resolved = _ally_clientes_resolver_dir(
        update, context, address_text, "allycust_geo_si", "allycust_geo_no", ALLY_CUST_DIR_EDITAR_TEXT
    )
    if resolved is None:
        return ALLY_CUST_DIR_EDITAR_TEXT
    if isinstance(resolved, int):
        context.user_data["allycust_geo_mode"] = "dir_editar"
        context.user_data["allycust_geo_address_input"] = address_text
        return resolved

    context.user_data["allycust_pending_mode"] = "dir_editar"
    context.user_data["allycust_pending_address_text"] = resolved.get("formatted_address") or address_text
    context.user_data["allycust_pending_lat"] = resolved.get("lat")
    context.user_data["allycust_pending_lng"] = resolved.get("lng")
    context.user_data["allycust_pending_notes"] = address["notes"]
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return ALLY_CUST_DIR_CIUDAD


def ally_clientes_dir_editar_nota(update, context):
    nota_text = update.message.text.strip()
    customer_id = context.user_data.get("allycust_current_customer_id")
    address_id = context.user_data.get("allycust_current_address_id")
    address = get_customer_address_by_id(address_id, customer_id)
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    nueva_nota = None if nota_text.lower() == "ninguna" else nota_text
    try:
        update_customer_address(
            address_id=address_id, customer_id=customer_id,
            label=address["label"], address_text=address["address_text"],
            city=address["city"], barrio=address["barrio"],
            notes=nueva_nota, lat=address["lat"], lng=address["lng"],
        )
        update.message.reply_text("Nota para entrega actualizada." if nueva_nota else "Nota para entrega eliminada.")
    except Exception as e:
        update.message.reply_text("Error: {}".format(str(e)))

    context.user_data.pop("allycust_current_address_id", None)
    return _ally_clientes_mostrar_menu(update, context, edit_message=False)


def ally_clientes_dir_corregir_handler(update, context):
    text = update.message.text.strip()
    if text.lower() == "cancelar":
        context.user_data.pop("allycust_geo_mode", None)
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    customer_id = context.user_data.get("allycust_current_customer_id")
    address_id = context.user_data.get("allycust_current_address_id")
    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("allycust_geo_mode", None)
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    context.user_data["allycust_geo_mode"] = "corregir_coords"
    context.user_data["allycust_geo_address_input"] = text

    resolved = _ally_clientes_resolver_dir(
        update, context, text, "allycust_geo_si", "allycust_geo_no", ALLY_CUST_DIR_CORREGIR
    )
    if resolved is None:
        return ALLY_CUST_DIR_CORREGIR
    if isinstance(resolved, int):
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    if lat is None or lng is None:
        update.message.reply_text("No se pudo obtener coordenadas. Intenta de nuevo o escribe 'cancelar'.")
        return ALLY_CUST_DIR_CORREGIR

    try:
        update_customer_address(
            address_id=address_id, customer_id=customer_id,
            label=address["label"], address_text=address["address_text"],
            city=address["city"] or "", barrio=address["barrio"] or "",
            notes=address["notes"], lat=lat, lng=lng,
        )
        update.message.reply_text(
            "Coordenadas actualizadas.\nLat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
        )
    except Exception as e:
        update.message.reply_text("Error al actualizar: {}".format(str(e)))

    context.user_data.pop("allycust_geo_mode", None)
    context.user_data.pop("allycust_geo_address_input", None)
    return _ally_clientes_mostrar_menu(update, context, edit_message=False)


def ally_clientes_dir_corregir_location_handler(update, context):
    loc = update.message.location
    lat = loc.latitude
    lng = loc.longitude
    customer_id = context.user_data.get("allycust_current_customer_id")
    address_id = context.user_data.get("allycust_current_address_id")
    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("allycust_geo_mode", None)
        return _ally_clientes_mostrar_menu(update, context, edit_message=False)

    try:
        update_customer_address(
            address_id=address_id, customer_id=customer_id,
            label=address["label"], address_text=address["address_text"],
            city=address["city"] or "", barrio=address["barrio"] or "",
            notes=address["notes"], lat=lat, lng=lng,
        )
        update.message.reply_text(
            "Coordenadas actualizadas.\nLat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
        )
    except Exception as e:
        update.message.reply_text("Error al actualizar: {}".format(str(e)))

    context.user_data.pop("allycust_geo_mode", None)
    return _ally_clientes_mostrar_menu(update, context, edit_message=False)

def agenda_cmd(update, context):
    """Comando /agenda: panel principal del aliado."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)

    if not ally:
        update.message.reply_text(
            "No tienes perfil de aliado registrado.\n"
            "Usa /soy_aliado para registrarte."
        )
        return ConversationHandler.END

    status = ally["status"]
    if status != "APPROVED":
        update.message.reply_text(
            "Tu cuenta de aliado no esta aprobada.\n"
            "Cuando tu estado sea APPROVED podras usar esta funcion."
        )
        return ConversationHandler.END

    context.user_data.clear()
    ally_id = ally["id"]
    context.user_data["active_ally_id"] = ally_id
    context.user_data["ally_locs_ally_id"] = ally_id
    context.user_data["ally"] = {"id": ally_id}

    return agenda_mostrar_menu(update, context)


def agenda_mostrar_menu(update, context, edit_message=False):
    """Muestra menu principal de la agenda del aliado."""
    keyboard = [
        [InlineKeyboardButton("Clientes", callback_data="agenda_clientes")],
        [InlineKeyboardButton("Direcciones de recogida", callback_data="agenda_pickups")],
        [InlineKeyboardButton("Cerrar", callback_data="agenda_cerrar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "Agenda del aliado\n\n"
        "Desde aqui puedes administrar tus clientes y direcciones "
        "guardadas para agilizar tus pedidos."
    )

    if edit_message and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text, reply_markup=reply_markup)

    return DIRECCIONES_MENU


def agenda_menu_callback(update, context):
    """Maneja callbacks del menu principal de la agenda."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "agenda_pickups":
        return agenda_pickups_mostrar(query, context)

    elif data == "agenda_clientes":
        return clientes_mostrar_menu(update, context, edit_message=True)

    elif data == "agenda_cerrar":
        query.edit_message_text("Agenda cerrada.")
        return ConversationHandler.END

    elif data == "agenda_volver":
        return agenda_mostrar_menu(update, context, edit_message=True)

    return DIRECCIONES_MENU


def agenda_pickups_mostrar(query, context):
    """Muestra lista de direcciones de recogida del aliado con botones por ubicacion."""
    ally_id = context.user_data.get("active_ally_id")
    if not ally_id:
        query.edit_message_text("Error: no hay aliado activo.")
        return ConversationHandler.END

    locations = get_ally_locations(ally_id)
    keyboard = []

    if locations:
        for loc in locations[:10]:
            label = (loc["label"] or "Sin nombre")[:25]
            tags = []
            if loc["is_default"]:
                tags.append("BASE")
            tag_str = " [{}]".format(", ".join(tags)) if tags else ""
            keyboard.append([InlineKeyboardButton(
                "{}{}".format(label, tag_str),
                callback_data="agenda_pickup_ver_{}".format(loc["id"])
            )])
        keyboard.append([InlineKeyboardButton("+ Agregar nueva", callback_data="agenda_pickups_nueva")])
        texto = "PUNTOS DE RECOGIDA\n\nSelecciona uno para ver opciones o agregar nuevo:"
    else:
        keyboard.append([InlineKeyboardButton("+ Agregar primera ubicacion", callback_data="agenda_pickups_nueva")])
        texto = "PUNTOS DE RECOGIDA\n\nAun no tienes ubicaciones de recogida guardadas."

    keyboard.append([InlineKeyboardButton("Volver", callback_data="agenda_volver")])
    query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return DIRECCIONES_PICKUPS


def agenda_pickups_callback(update, context):
    """Maneja callbacks de la lista de recogidas."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally_id = context.user_data.get("active_ally_id")
    if not ally_id:
        query.edit_message_text("Error: no hay aliado activo.")
        return ConversationHandler.END

    if data == "agenda_volver":
        return agenda_mostrar_menu(update, context, edit_message=True)

    elif data == "agenda_pickup_lista" or data == "agenda_pickup_del_cancel":
        return agenda_pickups_mostrar(query, context)

    elif data == "agenda_pickups_nueva":
        query.edit_message_text(
            "Nueva ubicacion de recogida\n\n"
            "Envia la ubicacion (PIN de Telegram), "
            "pega el enlace (Google Maps/WhatsApp) "
            "o escribe coordenadas (lat,lng).\n\n"
            "La ubicacion es obligatoria para continuar."
        )
        return DIRECCIONES_PICKUP_NUEVA_UBICACION

    elif data.startswith("agenda_pickup_ver_"):
        try:
            loc_id = int(data.split("agenda_pickup_ver_")[1])
        except (ValueError, IndexError):
            return agenda_pickups_mostrar(query, context)
        loc = get_ally_location_by_id(loc_id, ally_id)
        if not loc:
            return agenda_pickups_mostrar(query, context)
        label = loc["label"] or "Sin nombre"
        address = loc["address"] or "-"
        gps = "{}, {}".format(round(loc["lat"], 5), round(loc["lng"], 5)) if loc["lat"] else "Sin GPS"
        is_base = bool(loc["is_default"])
        detalle = "{}\n\nDireccion: {}\nGPS: {}".format(label, address, gps)
        keyboard = []
        if not is_base:
            keyboard.append([InlineKeyboardButton(
                "Marcar como base",
                callback_data="agenda_pickup_base_{}".format(loc_id)
            )])
        keyboard.append([InlineKeyboardButton(
            "Eliminar",
            callback_data="agenda_pickup_del_{}".format(loc_id)
        )])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="agenda_pickup_lista")])
        query.edit_message_text(detalle, reply_markup=InlineKeyboardMarkup(keyboard))
        return DIRECCIONES_PICKUPS

    elif data.startswith("agenda_pickup_base_"):
        try:
            loc_id = int(data.split("agenda_pickup_base_")[1])
        except (ValueError, IndexError):
            return agenda_pickups_mostrar(query, context)
        set_default_ally_location(loc_id, ally_id)
        return agenda_pickups_mostrar(query, context)

    elif data.startswith("agenda_pickup_del_confirm_"):
        try:
            loc_id = int(data.split("agenda_pickup_del_confirm_")[1])
        except (ValueError, IndexError):
            return agenda_pickups_mostrar(query, context)
        delete_ally_location(loc_id, ally_id)
        return agenda_pickups_mostrar(query, context)

    elif data.startswith("agenda_pickup_del_"):
        try:
            loc_id = int(data.split("agenda_pickup_del_")[1])
        except (ValueError, IndexError):
            return agenda_pickups_mostrar(query, context)
        loc = get_ally_location_by_id(loc_id, ally_id)
        label = (loc["label"] or "esta ubicacion") if loc else "esta ubicacion"
        keyboard = [
            [InlineKeyboardButton(
                "Confirmar eliminacion",
                callback_data="agenda_pickup_del_confirm_{}".format(loc_id)
            )],
            [InlineKeyboardButton("Cancelar", callback_data="agenda_pickup_del_cancel")],
        ]
        query.edit_message_text(
            "Eliminar '{}'?\n\nEsta accion no se puede deshacer.".format(label),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DIRECCIONES_PICKUPS

    return DIRECCIONES_PICKUPS


def direcciones_pickup_nueva_ubicacion(update, context):
    """Captura ubicacion (link o coords) para nueva recogida."""
    text = update.message.text.strip()

    if text.lower() == "omitir":
        update.message.reply_text(
            "No puedes omitir la ubicacion.\n"
            "Envia un PIN, link de Google Maps o coordenadas (lat,lng)."
        )
        return DIRECCIONES_PICKUP_NUEVA_UBICACION

    # Intentar extraer coordenadas de link de Google Maps
    lat, lng = None, None
    import re
    # Patron para Google Maps: @lat,lng o ?q=lat,lng o /lat,lng
    patterns = [
        r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',
        r'\?q=(-?\d+\.?\d*),(-?\d+\.?\d*)',
        r'/(-?\d+\.?\d*),(-?\d+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
                break
            except ValueError:
                continue

    # Si no es link, intentar como coords directas
    if lat is None and ',' in text:
        try:
            parts = text.split(',')
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
        except (ValueError, IndexError):
            pass

    if lat is not None and lng is not None:
        context.user_data["new_pickup_lat"] = lat
        context.user_data["new_pickup_lng"] = lng
        update.message.reply_text(
            f"Coordenadas capturadas: {lat:.6f}, {lng:.6f}\n\n"
            "Escribe la direccion de recogida (texto):"
        )
        return DIRECCIONES_PICKUP_NUEVA_DETALLES
    else:
        update.message.reply_text(
            "No se detectaron coordenadas validas.\n"
            "Envia un PIN, link de Google Maps o coordenadas (lat,lng)."
        )
        return DIRECCIONES_PICKUP_NUEVA_UBICACION


def direcciones_pickup_nueva_ubicacion_location_handler(update, context):
    """Maneja ubicacion nativa de Telegram (PIN) para nueva recogida en /agenda."""
    loc = update.message.location
    context.user_data["new_pickup_lat"] = loc.latitude
    context.user_data["new_pickup_lng"] = loc.longitude
    update.message.reply_text(
        f"Coordenadas capturadas: {loc.latitude:.6f}, {loc.longitude:.6f}\n\n"
        "Escribe la direccion de recogida (texto):"
    )
    return DIRECCIONES_PICKUP_NUEVA_DETALLES


def direcciones_pickup_nueva_detalles(update, context):
    """Captura direccion en texto y pregunta si guardar."""
    text = update.message.text.strip()
    if not text:
        update.message.reply_text("Por favor escribe la direccion de recogida:")
        return DIRECCIONES_PICKUP_NUEVA_DETALLES

    context.user_data["new_pickup_address"] = text

    # Sugerir ciudad basada en la base del aliado (pero se pregunta siempre)
    ally_id = context.user_data.get("active_ally_id")
    default_city = "Pereira"
    if ally_id:
        default_loc = get_default_ally_location(ally_id)
        if default_loc and default_loc["city"]:
            default_city = default_loc["city"]
    update.message.reply_text("Ciudad de la recogida (ej: {}).".format(default_city))
    return DIRECCIONES_PICKUP_NUEVA_CIUDAD


def direcciones_pickup_nueva_ciudad(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la recogida:",
        "new_pickup_city",
        DIRECCIONES_PICKUP_NUEVA_CIUDAD,
        DIRECCIONES_PICKUP_NUEVA_BARRIO,
        flow=None,
        next_prompt="Barrio o sector de la recogida:",
        options_hint="",
        set_back_step=False,
    )


def direcciones_pickup_nueva_barrio(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la recogida:",
        "new_pickup_barrio",
        DIRECCIONES_PICKUP_NUEVA_BARRIO,
        DIRECCIONES_PICKUP_GUARDAR,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == DIRECCIONES_PICKUP_NUEVA_BARRIO:
        return ok_state
    barrio = context.user_data.get("new_pickup_barrio", "")
    address = context.user_data.get("new_pickup_address", "")
    city = context.user_data.get("new_pickup_city", "")

    keyboard = [
        [InlineKeyboardButton("Si, guardar", callback_data="dir_pickup_guardar_si")],
        [InlineKeyboardButton("Cancelar", callback_data="dir_pickup_guardar_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Direccion: {}\nCiudad: {}\nBarrio o sector: {}\n\nDeseas guardar esta direccion?".format(address, city, barrio),
        reply_markup=reply_markup
    )
    return DIRECCIONES_PICKUP_GUARDAR


def direcciones_pickup_guardar_callback(update, context):
    """Guarda o cancela la nueva direccion de recogida."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "dir_pickup_guardar_si":
        ally_id = context.user_data.get("active_ally_id")
        if not ally_id:
            query.edit_message_text("Error: no hay aliado activo.")
            return ConversationHandler.END

        address = context.user_data.get("new_pickup_address", "")
        city = context.user_data.get("new_pickup_city", "Pereira")
        lat = context.user_data.get("new_pickup_lat")
        lng = context.user_data.get("new_pickup_lng")

        new_loc_id = create_ally_location(
            ally_id=ally_id,
            label=address[:30],
            address=address,
            city=city,
            barrio=context.user_data.get("new_pickup_barrio", ""),
            phone="",
            is_default=False,
            lat=lat,
            lng=lng,
        )

        if new_loc_id:
            query.edit_message_text("Direccion guardada correctamente.")
        else:
            query.edit_message_text("Error al guardar la direccion.")

        # Limpiar datos temporales
        context.user_data.pop("new_pickup_address", None)
        context.user_data.pop("new_pickup_city", None)
        context.user_data.pop("new_pickup_barrio", None)
        context.user_data.pop("new_pickup_lat", None)
        context.user_data.pop("new_pickup_lng", None)

        # Volver a mostrar lista de pickups
        return agenda_pickups_mostrar(query, context)

    else:
        query.edit_message_text("Operacion cancelada.")
        return agenda_mostrar_menu(update, context, edit_message=True)


# ConversationHandler para /agenda
agenda_conv = ConversationHandler(
    entry_points=[
        CommandHandler("agenda", agenda_cmd),
        MessageHandler(Filters.regex(r'^Agenda$'), agenda_cmd),
    ],
    states={
        DIRECCIONES_MENU: [
            CallbackQueryHandler(agenda_menu_callback, pattern=r"^agenda_(pickups|clientes|cerrar|volver)$"),
        ],
        DIRECCIONES_PICKUPS: [
            CallbackQueryHandler(
                agenda_pickups_callback,
                pattern=r"^agenda_(volver|pickups_nueva|pickup_lista|pickup_del_cancel|pickup_ver_\d+|pickup_base_\d+|pickup_del_confirm_\d+|pickup_del_\d+)$"
            )
        ],
        DIRECCIONES_PICKUP_NUEVA_UBICACION: [
            MessageHandler(Filters.location, direcciones_pickup_nueva_ubicacion_location_handler),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, direcciones_pickup_nueva_ubicacion)
        ],
        DIRECCIONES_PICKUP_NUEVA_DETALLES: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, direcciones_pickup_nueva_detalles)
        ],
        DIRECCIONES_PICKUP_NUEVA_CIUDAD: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, direcciones_pickup_nueva_ciudad)
        ],
        DIRECCIONES_PICKUP_NUEVA_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, direcciones_pickup_nueva_barrio)
        ],
        DIRECCIONES_PICKUP_GUARDAR: [
            CallbackQueryHandler(direcciones_pickup_guardar_callback, pattern=r"^dir_pickup_guardar_")
        ],
        CLIENTES_MENU: [
            CallbackQueryHandler(clientes_menu_callback, pattern=r"^cust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_\d+|restaurar_\d+)$")
        ],
        CLIENTES_NUEVO_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_nuevo_nombre)
        ],
        CLIENTES_NUEVO_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_nuevo_telefono)
        ],
        CLIENTES_NUEVO_DIRECCION_TEXT: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_nuevo_direccion_text)
        ],
        CLIENTES_BUSCAR: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_buscar)
        ],
        CLIENTES_VER_CLIENTE: [
            CallbackQueryHandler(clientes_ver_cliente_callback, pattern=r"^cust_(dirs|editar|edit_nombre|edit_telefono|edit_notas|archivar|dir_nueva|dir_ver_\d+|dir_editar|dir_edit_nota|dir_archivar|dir_corregir_coords|ver_\d+|volver_menu)$")
        ],
        CLIENTES_EDITAR_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_editar_nombre)
        ],
        CLIENTES_EDITAR_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_editar_telefono)
        ],
        CLIENTES_EDITAR_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_editar_notas)
        ],
        CLIENTES_DIR_NUEVA_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_nueva_label)
        ],
        CLIENTES_DIR_NUEVA_TEXT: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_nueva_text)
        ],
        CLIENTES_DIR_EDITAR_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_editar_label)
        ],
        CLIENTES_DIR_EDITAR_TEXT: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_editar_text)
        ],
        CLIENTES_DIR_CIUDAD: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_ciudad_handler)
        ],
        CLIENTES_DIR_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_barrio_handler)
        ],
        CLIENTES_DIR_EDITAR_NOTA: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_editar_nota)
        ],
        CLIENTES_DIR_CORREGIR_COORDS: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.location, clientes_dir_corregir_coords_location_handler),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_corregir_coords_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="agenda_conv",
    persistent=True,
)

# ConversationHandler para /clientes — entrada unificada, redirige a ally_clientes_conv via ally_clientes_cmd
clientes_conv = ConversationHandler(
    entry_points=[
        CommandHandler("clientes", clientes_cmd),
        MessageHandler(Filters.regex(r'^Clientes$'), clientes_cmd),
    ],
    states={
        CLIENTES_MENU: [
            CallbackQueryHandler(clientes_menu_callback, pattern=r"^cust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_\d+|restaurar_\d+)$")
        ],
        CLIENTES_NUEVO_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_nuevo_nombre)
        ],
        CLIENTES_NUEVO_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_nuevo_telefono)
        ],
        CLIENTES_NUEVO_DIRECCION_TEXT: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_nuevo_direccion_text)
        ],
        CLIENTES_BUSCAR: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_buscar)
        ],
        CLIENTES_VER_CLIENTE: [
            CallbackQueryHandler(clientes_ver_cliente_callback, pattern=r"^cust_(dirs|editar|edit_nombre|edit_telefono|edit_notas|archivar|dir_nueva|dir_ver_\d+|dir_editar|dir_edit_nota|dir_archivar|dir_corregir_coords|ver_\d+|volver_menu)$")
        ],
        CLIENTES_EDITAR_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_editar_nombre)
        ],
        CLIENTES_EDITAR_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_editar_telefono)
        ],
        CLIENTES_EDITAR_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_editar_notas)
        ],
        CLIENTES_DIR_NUEVA_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_nueva_label)
        ],
        CLIENTES_DIR_NUEVA_TEXT: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_nueva_text)
        ],
        CLIENTES_DIR_EDITAR_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_editar_label)
        ],
        CLIENTES_DIR_EDITAR_TEXT: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_editar_text)
        ],
        CLIENTES_DIR_EDITAR_NOTA: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_editar_nota)
        ],
        CLIENTES_DIR_CORREGIR_COORDS: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.location, clientes_dir_corregir_coords_location_handler),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, clientes_dir_corregir_coords_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="clientes_conv",
    persistent=True,
)
def admin_clientes_parking_callback(update, context):
    """Maneja la respuesta del admin sobre dificultad de parqueo al crear cliente en agenda."""
    query = update.callback_query
    query.answer()
    address_id = context.user_data.pop("acust_parking_address_id", None)
    if not address_id:
        query.edit_message_text("Error: no se pudo identificar la direccion. Intenta de nuevo.")
        return ADMIN_CUST_MENU
    if query.data == "acust_parking_si":
        set_address_parking_status(address_id, "ALLY_YES", table="admin_customer_addresses")
        query.edit_message_text(
            "Registrado. Se agregaran ${:,} al domicilio para ayudar al repartidor "
            "con el parqueo en ese punto.\n\n"
            "Tu administrador puede verificar y corregir el dato.".format(PARKING_FEE_AMOUNT)
        )
    else:
        set_address_parking_status(address_id, "PENDING_REVIEW", table="admin_customer_addresses")
        query.edit_message_text(
            "Entendido. El administrador revisara si hay dificultad de parqueo en esa "
            "direccion. Por ahora no se agrega ningun cobro adicional."
        )
    return ADMIN_CUST_MENU


admin_clientes_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(admin_clientes_cmd, pattern=r"^admin_mis_clientes$"),
    ],
    states={
        ADMIN_CUST_MENU: [
            CallbackQueryHandler(admin_clientes_menu_callback, pattern=r"^acust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_\d+|restaurar_\d+)$")
        ],
        ADMIN_CUST_NUEVO_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_nuevo_nombre)
        ],
        ADMIN_CUST_NUEVO_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_nuevo_telefono)
        ],
        ADMIN_CUST_NUEVO_DIR_TEXT: [
            CallbackQueryHandler(admin_clientes_geo_callback, pattern=r"^acust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_nuevo_dir_text)
        ],
        ADMIN_CUST_BUSCAR: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_buscar)
        ],
        ADMIN_CUST_VER: [
            CallbackQueryHandler(admin_clientes_ver_callback, pattern=r"^acust_(dirs|editar|edit_nombre|edit_telefono|edit_notas|archivar|dir_nueva|dir_ver_\d+|dir_editar|dir_edit_nota|dir_archivar|dir_corregir_coords|ver_\d+|volver_menu)$")
        ],
        ADMIN_CUST_EDITAR_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_editar_nombre)
        ],
        ADMIN_CUST_EDITAR_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_editar_telefono)
        ],
        ADMIN_CUST_EDITAR_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_editar_notas)
        ],
        ADMIN_CUST_DIR_NUEVA_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_dir_nueva_label)
        ],
        ADMIN_CUST_DIR_NUEVA_TEXT: [
            CallbackQueryHandler(admin_clientes_geo_callback, pattern=r"^acust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_dir_nueva_text)
        ],
        ADMIN_CUST_DIR_EDITAR_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_dir_editar_label)
        ],
        ADMIN_CUST_DIR_EDITAR_TEXT: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_dir_editar_text)
        ],
        ADMIN_CUST_DIR_EDITAR_NOTA: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_dir_editar_nota)
        ],
        ADMIN_CUST_DIR_CIUDAD: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_dir_ciudad_handler)
        ],
        ADMIN_CUST_DIR_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_dir_barrio_handler)
        ],
        ADMIN_CUST_DIR_CORREGIR: [
            CallbackQueryHandler(admin_clientes_geo_callback, pattern=r"^acust_geo_(si|no)$"),
            MessageHandler(Filters.location, admin_clientes_dir_corregir_location_handler),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_clientes_dir_corregir_handler),
        ],
        ADMIN_CUST_PARKING: [
            CallbackQueryHandler(admin_clientes_parking_callback, pattern=r"^acust_parking_(si|no)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="admin_clientes_conv",
    persistent=True,
)
def ally_clientes_parking_callback(update, context):
    """Maneja la respuesta del aliado sobre parqueadero al crear cliente.

    Si dice SI: marca ALLY_YES (tarifa $1.200 activa, admin verifica).
    Si dice NO: marca PENDING_REVIEW (admin debe confirmar).
    En ningun caso se expone PII del cliente — solo se actualiza el campo geografico.
    """
    query = update.callback_query
    query.answer()
    address_id = context.user_data.pop("allycust_parking_address_id", None)

    if not address_id:
        query.edit_message_text("Error: no se pudo identificar la direccion. Intenta de nuevo.")
        return ALLY_CUST_MENU

    if query.data == "allycust_parking_si":
        set_address_parking_status(address_id, "ALLY_YES")
        query.edit_message_text(
            "Registrado. Se agregaran ${:,} al domicilio para ayudar al repartidor "
            "con el parqueo en ese punto.\n\n"
            "Tu administrador verificara el dato para confirmarlo.".format(PARKING_FEE_AMOUNT)
        )
    else:
        set_address_parking_status(address_id, "PENDING_REVIEW")
        query.edit_message_text(
            "Entendido. Tu administrador revisara si hay dificultad de parqueo en esa "
            "direccion. Por ahora no se agrega ningun cobro adicional."
        )

    return ALLY_CUST_MENU


ally_clientes_conv = ConversationHandler(
    entry_points=[
        MessageHandler(Filters.regex(r'^Mis clientes$'), ally_clientes_cmd),
        MessageHandler(Filters.regex(r'^Clientes$'), ally_clientes_cmd),
        CommandHandler("clientes", ally_clientes_cmd),
    ],
    states={
        ALLY_CUST_MENU: [
            CallbackQueryHandler(ally_clientes_menu_callback, pattern=r"^allycust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_\d+|restaurar_\d+)$")
        ],
        ALLY_CUST_NUEVO_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_nuevo_nombre)
        ],
        ALLY_CUST_NUEVO_TEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_nuevo_telefono)
        ],
        ALLY_CUST_NUEVO_DIR_TEXT: [
            CallbackQueryHandler(ally_clientes_geo_callback, pattern=r"^allycust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_nuevo_dir_text)
        ],
        ALLY_CUST_BUSCAR: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_buscar)
        ],
        ALLY_CUST_VER: [
            CallbackQueryHandler(ally_clientes_ver_callback, pattern=r"^allycust_(dirs|editar|edit_nombre|edit_telefono|edit_notas|archivar|dir_nueva|dir_ver_\d+|dir_editar|dir_edit_nota|dir_archivar|dir_corregir_coords|ver_\d+|volver_menu)$")
        ],
        ALLY_CUST_EDITAR_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_editar_nombre)
        ],
        ALLY_CUST_EDITAR_TEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_editar_telefono)
        ],
        ALLY_CUST_EDITAR_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_editar_notas)
        ],
        ALLY_CUST_DIR_NUEVA_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_dir_nueva_label)
        ],
        ALLY_CUST_DIR_NUEVA_TEXT: [
            CallbackQueryHandler(ally_clientes_geo_callback, pattern=r"^allycust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_dir_nueva_text)
        ],
        ALLY_CUST_DIR_EDITAR_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_dir_editar_label)
        ],
        ALLY_CUST_DIR_EDITAR_TEXT: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_dir_editar_text)
        ],
        ALLY_CUST_DIR_EDITAR_NOTA: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_dir_editar_nota)
        ],
        ALLY_CUST_DIR_CIUDAD: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_dir_ciudad_handler)
        ],
        ALLY_CUST_DIR_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_dir_barrio_handler)
        ],
        ALLY_CUST_DIR_CORREGIR: [
            CallbackQueryHandler(ally_clientes_geo_callback, pattern=r"^allycust_geo_(si|no)$"),
            MessageHandler(Filters.location, ally_clientes_dir_corregir_location_handler),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_clientes_dir_corregir_handler),
        ],
        ALLY_CUST_PARKING: [
            CallbackQueryHandler(ally_clientes_parking_callback, pattern=r"^allycust_parking_(si|no)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="ally_clientes_conv",
    persistent=True,
)
