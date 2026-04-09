# =============================================================================
# handlers/location_agenda.py — admin_dirs_conv + ally_locs_conv
# Extraído de main.py (Fase 2d)
# =============================================================================

import logging
import re

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
    ADMIN_DIRS_MENU,
    ADMIN_DIRS_NUEVA_LABEL,
    ADMIN_DIRS_NUEVA_TEL,
    ADMIN_DIRS_NUEVA_TEXT,
    ADMIN_DIRS_VER,
    ALLY_LOCS_ADD_BARRIO,
    ALLY_LOCS_ADD_CITY,
    ALLY_LOCS_ADD_COORDS,
    ALLY_LOCS_ADD_LABEL,
    ALLY_LOCS_MENU,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER,
    _cotizar_resolver_ubicacion,
    _handle_text_field_input,
    cancel_conversacion,
    cancel_por_texto,
)
from services import (
    archive_admin_location,
    create_admin_location,
    create_ally_location,
    delete_ally_location,
    delete_distance_cache_for_coord,
    ensure_user,
    get_admin_by_telegram_id,
    get_admin_by_user_id,
    get_admin_location_by_id,
    get_admin_locations,
    get_ally_by_user_id,
    get_ally_location_by_id,
    get_ally_locations,
    get_user_by_telegram_id,
    get_user_db_id_from_update,
    resolve_location,
    set_default_ally_location,
    update_admin_location,
    update_ally_location,
    update_ally_location_coords,
    is_system_address_text,
    visible_address_label,
    visible_address_text,
    resolve_owned_admin_actor,
)


def _loc_repair_tag(address_text):
    return " [revisar]" if is_system_address_text(address_text) else ""

def _loc_admin_city_hint(update):
    """Retorna barrio+ciudad del admin para mejorar geocoding de sus ubicaciones."""
    try:
        admin = get_admin_by_telegram_id(update.effective_user.id)
        if admin:
            parts = [p for p in [admin.get("barrio"), admin.get("city")] if p]
            if parts:
                return ", ".join(parts)
    except Exception:
        pass
    return None


def _ally_locs_mostrar_lista(query_or_update, ally_id, edit=False, aviso=None):
    """Muestra el panel de ubicaciones del aliado con botones de gestión."""
    locations = get_ally_locations(ally_id)

    keyboard = []
    if locations:
        for loc in locations:
            label = visible_address_label(loc["label"], loc["address"], fallback="Sin nombre")[:25]
            tags = []
            if loc["is_default"]:
                tags.append("BASE")
            if loc["is_frequent"]:
                tags.append("FRECUENTE")
            tag_str = " [{}]".format(", ".join(tags)) if tags else ""
            sin_gps = " (sin GPS)" if loc["lat"] is None else ""
            keyboard.append([InlineKeyboardButton(
                "{}{}{}{}".format(label, tag_str, _loc_repair_tag(loc["address"]), sin_gps),
                callback_data="ally_locs_ver_{}".format(loc["id"])
            )])
        keyboard.append([InlineKeyboardButton("+ Agregar nueva", callback_data="ally_locs_add")])
        texto_base = "MIS UBICACIONES DE RECOGIDA\n\nSelecciona una para ver opciones:"
    else:
        keyboard.append([InlineKeyboardButton("+ Agregar primera ubicacion", callback_data="ally_locs_add")])
        texto_base = "MIS UBICACIONES DE RECOGIDA\n\nAun no tienes ubicaciones guardadas."

    if aviso:
        texto = "{}\n\n{}".format(aviso, texto_base)
    else:
        texto = texto_base

    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(texto, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)

    return ALLY_LOCS_MENU


def mis_ubicaciones_start(update, context):
    """Muestra el panel de gestión de ubicaciones del aliado."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally or ally["status"] != "APPROVED":
        update.message.reply_text(
            "No tienes un perfil de aliado activo. Contacta al administrador."
        )
        return ConversationHandler.END
    context.user_data["ally_locs_ally_id"] = ally["id"]
    return _ally_locs_mostrar_lista(update, ally["id"], edit=False)


def ally_locs_menu_callback(update, context):
    """Maneja todas las acciones del panel de ubicaciones del aliado."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ally_locs_ally_id")

    if not ally_id:
        query.edit_message_text("Sesion expirada. Regresa al menu e intenta de nuevo.")
        return ConversationHandler.END

    if data == "ally_locs_lista" or data == "ally_locs_del_cancel":
        return _ally_locs_mostrar_lista(query, ally_id, edit=True)

    if data.startswith("ally_locs_ver_"):
        try:
            loc_id = int(data.split("ally_locs_ver_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)

        loc = get_ally_location_by_id(loc_id, ally_id)
        if not loc:
            return _ally_locs_mostrar_lista(query, ally_id, edit=True, aviso="Ubicacion no encontrada.")

        label = visible_address_label(loc["label"], loc["address"], fallback="Sin nombre")
        address = visible_address_text(loc["address"], fallback="Direccion pendiente de corregir")
        gps = "{}, {}".format(round(loc["lat"], 5), round(loc["lng"], 5)) if loc["lat"] else "Sin GPS"
        usos = loc["use_count"] or 0
        is_base = bool(loc["is_default"])
        repair_note = ""
        if is_system_address_text(loc["address"]):
            repair_note = "\n\nATENCION: esta ubicacion necesita texto humano. Si no la corriges al reutilizarla en un pedido, volvera a pedir detalle."

        detalle = (
            "UBICACION: {}\n\n"
            "Direccion: {}\n"
            "GPS: {}\n"
            "Usos en pedidos: {}{}"
        ).format(label, address, gps, usos, repair_note)

        keyboard = []
        if not is_base:
            keyboard.append([InlineKeyboardButton(
                "Marcar como base",
                callback_data="ally_locs_base_{}".format(loc_id)
            )])
        if is_system_address_text(loc["address"]):
            keyboard.append([InlineKeyboardButton(
                "Corregir ahora",
                callback_data="ally_locs_fix_{}".format(loc_id)
            )])
        keyboard.append([InlineKeyboardButton(
            "Eliminar",
            callback_data="ally_locs_del_{}".format(loc_id)
        )])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="ally_locs_lista")])

        query.edit_message_text(detalle, reply_markup=InlineKeyboardMarkup(keyboard))
        return ALLY_LOCS_MENU

    if data.startswith("ally_locs_base_"):
        try:
            loc_id = int(data.split("ally_locs_base_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)
        set_default_ally_location(loc_id, ally_id)
        return _ally_locs_mostrar_lista(query, ally_id, edit=True, aviso="Base actualizada.")

    if data.startswith("ally_locs_fix_"):
        try:
            loc_id = int(data.split("ally_locs_fix_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)
        loc = get_ally_location_by_id(loc_id, ally_id)
        if not loc:
            return _ally_locs_mostrar_lista(query, ally_id, edit=True, aviso="Ubicacion no encontrada.")
        context.user_data["ally_locs_editing_id"] = loc_id
        logger.info("[address_fix_agenda_v2026_04_09] flow=ally_locs action=start location_id=%s", loc_id)
        query.edit_message_text(
            "CORREGIR UBICACION\n\n"
            "Envia la ubicacion corregida del punto de recogida:\n"
            "- Comparte tu ubicacion (PIN de Telegram)\n"
            "- Pega un link de Google Maps\n"
            "- Escribe coordenadas (ej: 4.81,-75.69)"
        )
        return ALLY_LOCS_ADD_COORDS

    if data.startswith("ally_locs_del_confirm_"):
        try:
            loc_id = int(data.split("ally_locs_del_confirm_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)
        delete_ally_location(loc_id, ally_id)
        return _ally_locs_mostrar_lista(query, ally_id, edit=True, aviso="Ubicacion eliminada.")

    if data.startswith("ally_locs_del_"):
        try:
            loc_id = int(data.split("ally_locs_del_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)
        loc = get_ally_location_by_id(loc_id, ally_id)
        label = loc["label"] or "esta ubicacion" if loc else "esta ubicacion"
        keyboard = [
            [InlineKeyboardButton(
                "Confirmar eliminacion",
                callback_data="ally_locs_del_confirm_{}".format(loc_id)
            )],
            [InlineKeyboardButton("Cancelar", callback_data="ally_locs_del_cancel")],
        ]
        query.edit_message_text(
            "Eliminar '{}'?\n\nEsta accion no se puede deshacer.".format(label),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ALLY_LOCS_MENU

    if data == "ally_locs_add":
        context.user_data.pop("ally_locs_editing_id", None)
        query.edit_message_text(
            "AGREGAR UBICACION\n\n"
            "Envia la ubicacion del punto de recogida:\n"
            "- Comparte tu ubicacion (PIN de Telegram)\n"
            "- Pega un link de Google Maps\n"
            "- Escribe coordenadas (ej: 4.81,-75.69)"
        )
        return ALLY_LOCS_ADD_COORDS

    return ALLY_LOCS_MENU


def ally_locs_add_coords(update, context):
    """Captura la ubicacion (texto/link/coords) de la nueva direccion del aliado."""
    loc = _cotizar_resolver_ubicacion(update, context)
    if not loc:
        update.message.reply_text(
            "No pude encontrar esa ubicacion.\n\n"
            "Intenta con:\n"
            "- Un PIN de Telegram\n"
            "- Un link de Google Maps\n"
            "- Coordenadas (ej: 4.81,-75.69)\n"
            "- Direccion con ciudad (ej: Barrio Leningrado, Pereira)"
        )
        return ALLY_LOCS_ADD_COORDS

    context.user_data["ally_locs_new_lat"] = loc["lat"]
    context.user_data["ally_locs_new_lng"] = loc["lng"]
    dir_encontrada = ""
    if loc.get("method") == "geocode" and loc.get("formatted_address"):
        dir_encontrada = f"Ubicacion encontrada: {loc['formatted_address']}\n\n"
    update.message.reply_text(
        f"{dir_encontrada}Dale un nombre a este punto de recogida:\n"
        "(ej: Tienda centro, Bodega norte, Casa)"
    )
    return ALLY_LOCS_ADD_LABEL


def ally_locs_add_coords_location(update, context):
    """Handler para PIN nativo de Telegram al agregar ubicacion del aliado."""
    return ally_locs_add_coords(update, context)


def ally_locs_add_label(update, context):
    """Guarda la nueva ubicacion del aliado con la etiqueta ingresada."""
    texto = (update.message.text or "").strip()
    if not texto:
        update.message.reply_text("El nombre no puede estar vacio. Escribe un nombre para la ubicacion:")
        return ALLY_LOCS_ADD_LABEL

    ally_id = context.user_data.get("ally_locs_ally_id")
    lat = context.user_data.get("ally_locs_new_lat")
    lng = context.user_data.get("ally_locs_new_lng")

    if not ally_id or lat is None:
        update.message.reply_text("Error: datos perdidos. Regresa al menu de ubicaciones.")
        return ConversationHandler.END

    label = texto[:40]
    context.user_data["ally_locs_new_label"] = label
    update.message.reply_text("Escribe la ciudad del punto de recogida:")
    return ALLY_LOCS_ADD_CITY


def ally_locs_add_city(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad del punto de recogida:",
        "ally_locs_new_city",
        ALLY_LOCS_ADD_CITY,
        ALLY_LOCS_ADD_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector del punto de recogida:",
        options_hint="",
        set_back_step=False,
    )


def ally_locs_add_barrio(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector del punto de recogida:",
        "ally_locs_new_barrio",
        ALLY_LOCS_ADD_BARRIO,
        ALLY_LOCS_MENU,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == ALLY_LOCS_ADD_BARRIO:
        return ok_state
    barrio = context.user_data.get("ally_locs_new_barrio", "")

    ally_id = context.user_data.get("ally_locs_ally_id")
    lat = context.user_data.get("ally_locs_new_lat")
    lng = context.user_data.get("ally_locs_new_lng")
    label = context.user_data.get("ally_locs_new_label", "")
    city = context.user_data.get("ally_locs_new_city", "")

    if not ally_id or lat is None:
        update.message.reply_text("Error: datos perdidos. Regresa al menu de ubicaciones.")
        return ConversationHandler.END

    editing_id = context.user_data.pop("ally_locs_editing_id", None)
    if editing_id:
        update_ally_location(
            editing_id,
            address=label,
            city=city,
            barrio=barrio,
            phone=None,
        )
        update_ally_location_coords(editing_id, lat, lng)
        logger.info("[address_fix_agenda_v2026_04_09] flow=ally_locs action=save location_id=%s", editing_id)
        for key in [
            "ally_locs_new_lat",
            "ally_locs_new_lng",
            "ally_locs_new_label",
            "ally_locs_new_city",
            "ally_locs_new_barrio",
        ]:
            context.user_data.pop(key, None)
        update.message.reply_text("Ubicacion corregida correctamente.")
        return _ally_locs_mostrar_lista(update, ally_id, edit=False)

    new_loc_id = create_ally_location(
        ally_id=ally_id,
        label=label,
        address=label,
        city=city,
        barrio=barrio,
        lat=lat,
        lng=lng,
    )

    for key in [
        "ally_locs_new_lat",
        "ally_locs_new_lng",
        "ally_locs_new_label",
        "ally_locs_new_city",
        "ally_locs_new_barrio",
    ]:
        context.user_data.pop(key, None)

    keyboard = [
        [InlineKeyboardButton("Si, usar como base", callback_data="ally_locs_base_{}".format(new_loc_id))],
        [InlineKeyboardButton("No, solo guardarla", callback_data="ally_locs_lista")],
    ]
    update.message.reply_text(
        "Ubicacion '{}' guardada.\n\n"
        "Usar como direccion base (la que aparece primero al crear pedidos)?".format(label),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ALLY_LOCS_MENU


# =============================================================
# FIN PANEL GESTIÓN DE UBICACIONES
# =============================================================


def admin_dirs_cmd(update, context):
    """Entry point de gestion de ubicaciones de recogida del admin."""
    query = update.callback_query
    query.answer()
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)

    if not db_user:
        query.edit_message_text("Aun no estas registrado. Usa /start primero.")
        return ConversationHandler.END

    data = query.data or ""
    match = re.fullmatch(r"admin_mis_dirs(?:_(\d+))?", data)
    selected_admin_id = int(match.group(1)) if match and match.group(1) else None
    admin = resolve_owned_admin_actor(
        user.id,
        selected_admin_id=selected_admin_id,
        prefer_platform=False,
        legacy_counter_key="admin_dirs_legacy_callback_count",
        invalid_counter_key="admin_dirs_invalid_selected_count",
    )
    if selected_admin_id is not None and not admin:
        query.edit_message_text(
            "No se pudo validar este panel de direcciones.\n\n"
            "Vuelve a abrir Mi admin y entra de nuevo desde el boton actualizado."
        )
        return ConversationHandler.END
    if not admin:
        query.edit_message_text("Este menu es solo para administradores.")
        return ConversationHandler.END

    if admin["status"] != "APPROVED":
        query.edit_message_text("Tu registro como administrador aun no ha sido aprobado.")
        return ConversationHandler.END

    for key in list(context.user_data.keys()):
        if key.startswith("adirs_"):
            del context.user_data[key]
    context.user_data["adirs_admin_id"] = admin["id"]

    return _admin_dirs_mostrar_menu(update, context, edit_message=True)


def _admin_dirs_mostrar_menu(update, context, edit_message=False):
    """Muestra la lista de ubicaciones de recogida del admin."""
    admin_id = context.user_data.get("adirs_admin_id")
    locations = get_admin_locations(admin_id)

    keyboard = []
    if locations:
        for loc in locations:
            label = visible_address_label(loc["label"], loc["address"], fallback="Sin etiqueta")
            visible_address = visible_address_text(loc["address"], fallback="Direccion pendiente de corregir")
            btn_text = "{}{}: {}".format(label, _loc_repair_tag(loc["address"]), visible_address[:25])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="adirs_ver_{}".format(loc["id"]))])

    keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="adirs_nueva")])
    keyboard.append([InlineKeyboardButton("Cerrar", callback_data="adirs_cerrar")])

    text = "MIS DIRECCIONES DE RECOGIDA\n\nSelecciona una para editar o agrega una nueva:"
    if not locations:
        text = "MIS DIRECCIONES DE RECOGIDA\n\nNo tienes direcciones guardadas.\nAgrega tu primera ubicacion de recogida:"

    if edit_message and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    return ADMIN_DIRS_MENU


def admin_dirs_menu_callback(update, context):
    """Maneja los callbacks del menu de ubicaciones del admin."""
    query = update.callback_query
    query.answer()
    data = query.data
    admin_id = context.user_data.get("adirs_admin_id")

    if not admin_id:
        query.edit_message_text("Sesion expirada. Vuelve al menu e inicia de nuevo.")
        return ConversationHandler.END

    if data == "adirs_nueva":
        query.edit_message_text("NUEVA UBICACION\n\nEscribe el nombre del lugar (ej: Tienda Principal, Casa):")
        return ADMIN_DIRS_NUEVA_LABEL

    elif data == "adirs_volver_menu":
        return _admin_dirs_mostrar_menu(update, context, edit_message=True)

    elif data == "adirs_cerrar":
        query.edit_message_text("Mis direcciones cerrado.")
        for key in list(context.user_data.keys()):
            if key.startswith("adirs_"):
                del context.user_data[key]
        return ConversationHandler.END

    elif data.startswith("adirs_ver_"):
        loc_id = int(data.replace("adirs_ver_", ""))
        return _admin_dirs_ver_ubicacion(query, context, loc_id, admin_id)

    elif data.startswith("adirs_archivar_"):
        loc_id = int(data.replace("adirs_archivar_", ""))
        if archive_admin_location(loc_id, admin_id):
            query.edit_message_text("Ubicacion archivada.")
        else:
            query.edit_message_text("No se pudo archivar la ubicacion.")
        return _admin_dirs_mostrar_menu(update, context, edit_message=False)

    elif data.startswith("adirs_editar_"):
        loc_id = int(data.replace("adirs_editar_", ""))
        context.user_data["adirs_editing_id"] = loc_id
        query.edit_message_text("EDITAR UBICACION\n\nEscribe el nuevo nombre del lugar:")
        return ADMIN_DIRS_NUEVA_LABEL

    return ADMIN_DIRS_MENU


def _admin_dirs_ver_ubicacion(query, context, loc_id, admin_id):
    """Muestra detalles de una ubicacion de recogida del admin."""
    from services import get_admin_location_by_id
    loc = get_admin_location_by_id(loc_id, admin_id)
    if not loc:
        query.edit_message_text("Ubicacion no encontrada.")
        return ADMIN_DIRS_MENU

    context.user_data["adirs_current_id"] = loc_id
    label = visible_address_label(loc["label"], loc["address"], fallback="Sin etiqueta")
    phone_text = loc["phone"] or "Sin telefono"
    lat = loc["lat"]
    lng = loc["lng"]
    coords_text = "Coordenadas: {:.5f}, {:.5f}".format(float(lat), float(lng)) if lat and lng else "Sin coordenadas"
    visible_address = visible_address_text(loc["address"], fallback="Direccion pendiente de corregir")
    repair_note = ""
    if is_system_address_text(loc["address"]):
        repair_note = "\n\nATENCION: esta direccion necesita correccion humana. Usa 'Editar' para dejarla legible."

    if lat and lng:
        try:
            context.bot.send_location(
                chat_id=query.message.chat_id,
                latitude=float(lat),
                longitude=float(lng),
            )
        except Exception:
            pass

    edit_label = "Corregir ahora" if is_system_address_text(loc["address"]) else "Editar"
    keyboard = [
        [InlineKeyboardButton(edit_label, callback_data="adirs_editar_{}".format(loc_id))],
        [InlineKeyboardButton("Archivar", callback_data="adirs_archivar_{}".format(loc_id))],
        [InlineKeyboardButton("Volver", callback_data="adirs_volver_menu")],
    ]

    query.edit_message_text(
        "{}\n{}\n\nTelefono: {}\n{}{}".format(label, visible_address, phone_text, coords_text, repair_note),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_DIRS_VER


def admin_dirs_nueva_label_handler(update, context):
    """Recibe label de nueva ubicacion (o editando existente)."""
    context.user_data["adirs_new_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return ADMIN_DIRS_NUEVA_TEXT


def admin_dirs_nueva_text_handler(update, context):
    """Recibe direccion de nueva ubicacion (o editando). Geocodifica."""
    address_text = update.message.text.strip()
    admin_id = context.user_data.get("adirs_admin_id")
    label = context.user_data.get("adirs_new_label", "")
    editing_id = context.user_data.get("adirs_editing_id")

    if editing_id and "adirs_old_lat" not in context.user_data:
        try:
            old_loc = get_admin_location_by_id(editing_id, admin_id)
            if old_loc:
                context.user_data["adirs_old_lat"] = old_loc.get("lat")
                context.user_data["adirs_old_lng"] = old_loc.get("lng")
        except Exception:
            pass

    loc = resolve_location(address_text, city_hint=_loc_admin_city_hint(update))
    if not loc or loc.get("lat") is None or loc.get("lng") is None:
        update.message.reply_text(
            "No pude encontrar esa ubicacion.\n\n"
            "Intenta con coordenadas (ej: 4.81,-75.69) o un link de Google Maps."
        )
        return ADMIN_DIRS_NUEVA_TEXT

    lat = loc.get("lat")
    lng = loc.get("lng")
    address_to_save = loc.get("formatted_address") or address_text
    city = loc.get("city") or ""
    barrio = loc.get("barrio") or ""

    context.user_data["adirs_pending_address"] = address_to_save
    context.user_data["adirs_pending_lat"] = lat
    context.user_data["adirs_pending_lng"] = lng
    context.user_data["adirs_pending_city"] = city
    context.user_data["adirs_pending_barrio"] = barrio

    update.message.reply_text(
        "Escribe el telefono del punto de recogida (o 'ninguno' si no hay):"
    )
    return ADMIN_DIRS_NUEVA_TEL


def admin_dirs_nueva_tel_handler(update, context):
    """Recibe telefono y guarda la ubicacion de recogida."""
    tel_text = update.message.text.strip()
    phone = None if tel_text.lower() == "ninguno" else tel_text
    admin_id = context.user_data.get("adirs_admin_id")
    label = context.user_data.get("adirs_new_label", "")
    address = context.user_data.get("adirs_pending_address", "")
    city = context.user_data.get("adirs_pending_city", "")
    barrio = context.user_data.get("adirs_pending_barrio", "")
    lat = context.user_data.get("adirs_pending_lat")
    lng = context.user_data.get("adirs_pending_lng")
    editing_id = context.user_data.pop("adirs_editing_id", None)
    old_lat = context.user_data.pop("adirs_old_lat", None)
    old_lng = context.user_data.pop("adirs_old_lng", None)

    try:
        if editing_id:
            if old_lat is not None and old_lng is not None:
                try:
                    delete_distance_cache_for_coord("{},{}".format(round(float(old_lat), 5), round(float(old_lng), 5)))
                except Exception:
                    pass
            update_admin_location(editing_id, admin_id, label, address, city, barrio, phone=phone, lat=lat, lng=lng)
            update.message.reply_text("Ubicacion actualizada: {}".format(label))
        else:
            create_admin_location(admin_id, label, address, city, barrio, phone=phone, lat=lat, lng=lng)
            update.message.reply_text("Ubicacion guardada: {}".format(label))
    except Exception as e:
        update.message.reply_text("Error al guardar: {}".format(str(e)))

    for key in ["adirs_new_label", "adirs_pending_address", "adirs_pending_lat",
                "adirs_pending_lng", "adirs_pending_city", "adirs_pending_barrio"]:
        context.user_data.pop(key, None)

    return _admin_dirs_mostrar_menu(update, context, edit_message=False)


# =========================
# Panel "Agenda del aliado" (/agenda)
# =========================

admin_dirs_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(admin_dirs_cmd, pattern=r"^admin_mis_dirs(?:_\d+)?$"),
    ],
    states={
        ADMIN_DIRS_MENU: [
            CallbackQueryHandler(admin_dirs_menu_callback, pattern=r"^adirs_(nueva|volver_menu|cerrar|ver_\d+|archivar_\d+|editar_\d+)$")
        ],
        ADMIN_DIRS_NUEVA_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_dirs_nueva_label_handler)
        ],
        ADMIN_DIRS_NUEVA_TEXT: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_dirs_nueva_text_handler)
        ],
        ADMIN_DIRS_NUEVA_TEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_dirs_nueva_tel_handler)
        ],
        ADMIN_DIRS_VER: [
            CallbackQueryHandler(admin_dirs_menu_callback, pattern=r"^adirs_(editar_\d+|archivar_\d+|volver_menu)$")
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="admin_dirs_conv",
    persistent=True,
)

# Conversación para "Otro monto" de la sugerencia T+5 (aplica a aliados y admins)

ally_locs_conv = ConversationHandler(
    entry_points=[
        MessageHandler(Filters.regex(r'^Mis ubicaciones$'), mis_ubicaciones_start),
    ],
    states={
        ALLY_LOCS_MENU: [
            CallbackQueryHandler(ally_locs_menu_callback, pattern=r"^ally_locs_"),
        ],
        ALLY_LOCS_ADD_COORDS: [
            MessageHandler(Filters.location, ally_locs_add_coords_location),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_locs_add_coords),
        ],
        ALLY_LOCS_ADD_LABEL: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_locs_add_label),
        ],
        ALLY_LOCS_ADD_CITY: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_locs_add_city),
        ],
        ALLY_LOCS_ADD_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_locs_add_barrio),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(
            Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'),
            cancel_por_texto
        ),
    ],
    allow_reentry=True,
    name="ally_locs_conv",
    persistent=True,
)


# Conversación para /cotizar
