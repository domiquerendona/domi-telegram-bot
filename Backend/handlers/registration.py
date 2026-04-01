# =============================================================================
# handlers/registration.py — Handlers de registro de aliado, repartidor y admin
# Extraído de main.py (Fase 2f)
# =============================================================================

import logging
logger = logging.getLogger(__name__)

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from handlers.states import (
    ALLY_NAME, ALLY_OWNER, ALLY_DOCUMENT, ALLY_PHONE, ALLY_CITY, ALLY_BARRIO,
    ALLY_ADDRESS, ALLY_UBICACION, ALLY_CONFIRM, ALLY_TEAM,
    COURIER_FULLNAME, COURIER_IDNUMBER, COURIER_PHONE, COURIER_CITY, COURIER_BARRIO,
    COURIER_RESIDENCE_ADDRESS, COURIER_RESIDENCE_LOCATION, COURIER_VEHICLE_TYPE,
    COURIER_PLATE, COURIER_BIKETYPE, COURIER_CEDULA_FRONT, COURIER_CEDULA_BACK,
    COURIER_SELFIE, COURIER_CONFIRM, COURIER_TEAM,
    LOCAL_ADMIN_NAME, LOCAL_ADMIN_DOCUMENT, LOCAL_ADMIN_TEAMNAME,
    LOCAL_ADMIN_PHONE, LOCAL_ADMIN_CITY, LOCAL_ADMIN_BARRIO,
    LOCAL_ADMIN_RESIDENCE_ADDRESS, LOCAL_ADMIN_RESIDENCE_LOCATION,
    LOCAL_ADMIN_CEDULA_FRONT, LOCAL_ADMIN_CEDULA_BACK, LOCAL_ADMIN_SELFIE,
    LOCAL_ADMIN_CONFIRM,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER,
    _OPTIONS_HINT,
    _debug_admin_registration_state,
    _geo_siguiente_o_gps,
    _handle_phone_input,
    _handle_text_field_input,
    _mostrar_confirmacion_geocode,
    _schedule_important_alerts,
    _set_flow_step,
    cancel_conversacion,
    cancel_por_texto,
    volver_paso_anterior,
)
from services import (
    can_admin_reregister_via_platform_reset,
    can_ally_reregister_via_platform_reset,
    can_courier_reregister_via_platform_reset,
    create_admin,
    create_admin_courier_link,
    create_ally,
    create_ally_location,
    create_courier,
    ensure_user,
    extract_lat_lng_from_text,
    get_admin_by_id,
    get_admin_by_team_code,
    get_admin_by_user_id,
    get_admin_rejection_type_by_id,
    get_ally_by_user_id,
    get_ally_rejection_type_by_id,
    get_available_admin_teams,
    get_courier_by_user_id,
    get_courier_rejection_type_by_id,
    get_default_ally_location,
    get_user_by_id,
    get_user_by_telegram_id,
    get_user_db_id_from_update,
    has_valid_coords,
    parse_team_selection_callback,
    reset_admin_registration_in_place_service,
    reset_ally_registration_in_place_service,
    reset_courier_registration_in_place_service,
    resolve_location,
    update_ally_location,
    update_ally_location_coords,
    upsert_admin_ally_link,
)

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
PLATFORM_TEAM_CODE = "PLATFORM"


def _registration_invalid_location_text():
    return (
        "No pude detectar esa ubicacion.\n\n"
        "Prueba una de estas formas para continuar:\n"
        "- Envia un PIN de Telegram\n"
        "- Pega un link de Google Maps\n"
        "- Escribe coordenadas (ej: 4.81,-75.69)\n"
        "- Escribe una direccion con ciudad"
    )


def _registration_no_more_text():
    return (
        "No encontre mas opciones para esa ubicacion.\n\n"
        "Prueba una de estas formas para continuar:\n"
        "- Envia un PIN de Telegram\n"
        "- Pega un link de Google Maps\n"
        "- Escribe coordenadas (ej: 4.81,-75.69)\n"
        "- Escribe una direccion con ciudad"
    )


def _emit_registration_geo_confirmation(update, context, geo, texto, cb_si, cb_no, log_tag):
    logger.info(
        "[%s] status=pending source=%s lat=%s lng=%s",
        log_tag,
        geo.get("method"),
        geo.get("lat"),
        geo.get("lng"),
    )
    _mostrar_confirmacion_geocode(
        update.message,
        context,
        geo,
        texto,
        cb_si,
        cb_no,
        header_text="Confirma este punto exacto antes de continuar con tu registro.",
        question_text="Es esta la ubicacion correcta?",
    )


def _log_registration_location_saved(log_tag, source, lat, lng):
    logger.info("[%s] status=saved source=%s lat=%s lng=%s", log_tag, source, lat, lng)


# ----- REGISTRO DE ALIADO (flujo unificado) -----

def soy_aliado(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    # Validación anti-duplicados
    existing = get_ally_by_user_id(user_db_id)
    if existing:
        status = existing["status"]
        ally_id = existing["id"]

        rejection_type = get_ally_rejection_type_by_id(ally_id)

        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de aliado en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de aliado aprobado (APPROVED). Si necesitas cambios, contacta al administrador."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status in ("INACTIVE", "REJECTED") and not can_ally_reregister_via_platform_reset(ally_id):
            update.message.reply_text(
                f"Tu registro de aliado esta {status}.\n"
                "Solo el Administrador de Plataforma puede autorizar un reinicio del registro.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status not in ("INACTIVE", "REJECTED"):
            update.message.reply_text(
                f"No puedes iniciar un nuevo registro con estado {status}.\n"
                "Solo el Administrador de Plataforma puede autorizar un reinicio del registro.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

    update.message.reply_text(
        "Registro de aliado\n\n"
        "Escribe el nombre del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    _set_flow_step(context, "ally", ALLY_NAME)
    return ALLY_NAME


def ally_name(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "El nombre del negocio no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_NAME

    context.user_data["business_name"] = texto
    update.message.reply_text(
        "Escribe el nombre del dueño o administrador:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "ally", ALLY_OWNER)
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
        "Escribe el número de cédula del dueño o representante:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "ally", ALLY_DOCUMENT)
    return ALLY_DOCUMENT


def ally_document(update, context):
    doc = update.message.text.strip()
    if len(doc) < 5:
        update.message.reply_text(
            "El número de documento parece muy corto. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_DOCUMENT

    context.user_data["ally_document"] = doc
    update.message.reply_text(
        "Escribe el teléfono de contacto del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "ally", ALLY_PHONE)
    return ALLY_PHONE


def ally_phone(update, context):
    from handlers.common import _handle_phone_input
    return _handle_phone_input(update, context,
        storage_key="ally_phone",
        current_state=ALLY_PHONE,
        next_state=ALLY_CITY,
        flow="ally",
        next_prompt="Escribe la ciudad del negocio:")


def ally_city(update, context):
    from handlers.common import _handle_text_field_input
    return _handle_text_field_input(update, context,
        error_msg="La ciudad del negocio no puede estar vacía. Escríbela de nuevo:",
        storage_key="city",
        current_state=ALLY_CITY,
        next_state=ALLY_BARRIO,
        flow="ally",
        next_prompt="Escribe el barrio del negocio:")


def ally_barrio(update, context):
    from handlers.common import _handle_text_field_input
    return _handle_text_field_input(update, context,
        error_msg="El barrio no puede estar vacío. Escríbelo de nuevo:",
        storage_key="barrio",
        current_state=ALLY_BARRIO,
        next_state=ALLY_ADDRESS,
        flow="ally",
        next_prompt="Escribe la dirección del negocio:")


def ally_address(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "La dirección no puede estar vacía. Escríbela de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_ADDRESS

    context.user_data["address"] = texto
    update.message.reply_text(
        "Envía la ubicación GPS (pin de Telegram) o pega un link de Google Maps."
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "ally", ALLY_UBICACION)
    return ALLY_UBICACION


def ally_ubicacion_handler(update, context):
    """Maneja texto de ubicación del aliado (link o coords)."""
    texto = update.message.text.strip()
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        db_user = ensure_user(user.id, user.username)
    context.user_data["ally_registration_user_id"] = db_user["id"]

    coords = extract_lat_lng_from_text(texto)
    if coords:
        context.user_data["ally_lat"] = coords[0]
        context.user_data["ally_lng"] = coords[1]
        _log_registration_location_saved(
            "ally_registration_location",
            "text_coords_or_link",
            coords[0],
            coords[1],
        )
        update.message.reply_text("Ubicacion guardada.")
        return show_ally_team_selection(update, context, from_callback=False)

    # Geocoding: intentar como direccion escrita
    geo = resolve_location(texto)
    if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
        _emit_registration_geo_confirmation(
            update,
            context,
            geo,
            texto,
            "ally_geo_si",
            "ally_geo_no",
            "ally_registration_location",
        )
        return ALLY_UBICACION

    update.message.reply_text(_registration_invalid_location_text())
    return ALLY_UBICACION


def ally_ubicacion_location_handler(update, context):
    """Maneja ubicación nativa de Telegram (PIN) para registro de aliado."""
    loc = update.message.location
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        db_user = ensure_user(user.id, user.username)
    context.user_data["ally_registration_user_id"] = db_user["id"]
    context.user_data["ally_lat"] = loc.latitude
    context.user_data["ally_lng"] = loc.longitude
    _log_registration_location_saved(
        "ally_registration_location",
        "telegram_pin",
        loc.latitude,
        loc.longitude,
    )
    update.message.reply_text("Ubicacion guardada.")
    return show_ally_team_selection(update, context, from_callback=False)


def ally_geo_ubicacion_callback(update, context):
    """Maneja confirmacion de geocoding en el registro de aliado."""
    query = update.callback_query
    query.answer()
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        db_user = ensure_user(user.id, user.username)
    context.user_data["ally_registration_user_id"] = db_user["id"]

    if query.data == "ally_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return ALLY_UBICACION
        context.user_data["ally_lat"] = lat
        context.user_data["ally_lng"] = lng
        logger.info(
            "[ally_registration_location] status=confirmed source=geocode lat=%s lng=%s",
            lat,
            lng,
        )
        query.edit_message_text("Ubicacion confirmada.")
        return show_ally_team_selection(update, context, from_callback=True)
    else:  # ally_geo_no
        logger.info("[ally_registration_location] status=rejected source=geocode")
        return _geo_siguiente_o_gps(
            query,
            context,
            "ally_geo_si",
            "ally_geo_no",
            ALLY_UBICACION,
            header_text="Confirma este punto exacto antes de continuar con tu registro.",
            question_text="Es esta la ubicacion correcta?",
            no_more_text=_registration_no_more_text(),
        )


def _show_ally_confirm(update, context):
    """Muestra resumen de datos del aliado y pide confirmación."""
    business_name = context.user_data.get("business_name", "")
    owner_name = context.user_data.get("owner_name", "")
    ally_document = context.user_data.get("ally_document", "")
    phone = context.user_data.get("ally_phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    address = context.user_data.get("address", "")
    ally_lat = context.user_data.get("ally_lat")
    ally_lng = context.user_data.get("ally_lng")
    if ally_lat is not None and ally_lng is not None:
        ubicacion = f"{ally_lat}, {ally_lng}"
    else:
        ubicacion = "No disponible"
    selected_team_name = context.user_data.get("ally_selected_team_name", "No seleccionado")
    selected_team_code = context.user_data.get("ally_selected_team_code")
    equipo = (
        f"{selected_team_name} ({selected_team_code})"
        if selected_team_code else
        selected_team_name
    )

    resumen = (
        "Verifica tus datos de aliado:\n\n"
        f"Negocio: {business_name}\n"
        f"Dueño: {owner_name}\n"
        f"Cédula: {ally_document}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Dirección: {address}\n"
        f"Equipo: {equipo}\n"
        f"Ubicación: {ubicacion}\n\n"
        "Si todo está bien escribe: SI\n"
        "Si quieres corregir, escribe 'volver' o usa /cancel y vuelve a /soy_aliado"
    )
    message = update.message or (update.callback_query.message if update.callback_query else None)
    if message:
        message.reply_text(resumen)
    _set_flow_step(context, "ally", ALLY_CONFIRM)
    return ALLY_CONFIRM


def _create_or_reset_ally_from_context(context, user_db_id: int):
    business_name = context.user_data.get("business_name", "").strip()
    owner_name = context.user_data.get("owner_name", "").strip()
    ally_document = context.user_data.get("ally_document", "").strip()
    address = context.user_data.get("address", "").strip()
    city = context.user_data.get("city", "").strip()
    phone = context.user_data.get("ally_phone", "").strip()
    barrio = context.user_data.get("barrio", "").strip()
    ally_lat = context.user_data.get("ally_lat")
    ally_lng = context.user_data.get("ally_lng")

    if not has_valid_coords(ally_lat, ally_lng):
        raise ValueError("La direccion principal del aliado requiere ubicacion confirmada.")

    previous_ally = get_ally_by_user_id(user_db_id)
    if previous_ally and can_ally_reregister_via_platform_reset(previous_ally["id"]):
        ally = reset_ally_registration_in_place_service(
            ally_id=previous_ally["id"],
            business_name=business_name,
            owner_name=owner_name,
            address=address,
            city=city,
            barrio=barrio,
            phone=phone,
            document_number=ally_document,
        )
        ally_id = ally["id"]
    else:
        ally_id = create_ally(
            user_id=user_db_id,
            business_name=business_name,
            owner_name=owner_name,
            address=address,
            city=city,
            barrio=barrio,
            phone=phone,
            document_number=ally_document,
        )

    default_location = get_default_ally_location(ally_id)
    if default_location:
        update_ally_location(
            default_location["id"],
            address=address,
            city=city,
            barrio=barrio,
            phone=None,
        )
        update_ally_location_coords(default_location["id"], ally_lat, ally_lng)
    else:
        create_ally_location(
            ally_id=ally_id,
            label="Principal",
            address=address,
            city=city,
            barrio=barrio,
            phone=None,
            is_default=True,
            lat=ally_lat,
            lng=ally_lng,
        )

    return {
        "ally_id": ally_id,
        "business_name": business_name,
        "owner_name": owner_name,
        "ally_document": ally_document,
        "phone": phone,
        "city": city,
        "barrio": barrio,
    }


def ally_confirm(update, context):
    """Confirma datos y guarda el registro del aliado en BD."""
    confirm_text = update.message.text.strip().upper()

    if confirm_text not in ("SI", "SÍ", "SI.", "SÍ."):
        update.message.reply_text(
            "Registro cancelado.\n\n"
            "Si deseas intentarlo de nuevo, usa /soy_aliado."
        )
        context.user_data.clear()
        return ConversationHandler.END

    user_db_id = context.user_data.get("ally_registration_user_id")
    selected_admin_id = context.user_data.get("ally_selected_admin_id")
    selected_team_name = context.user_data.get("ally_selected_team_name")
    selected_team_code = context.user_data.get("ally_selected_team_code")

    if not user_db_id or not selected_team_name:
        update.message.reply_text(
            "Primero debes elegir un equipo para continuar.\n\n"
            "Usa /soy_aliado para iniciar de nuevo."
        )
        context.user_data.clear()
        return ConversationHandler.END

    ally_lat = context.user_data.get("ally_lat")
    ally_lng = context.user_data.get("ally_lng")

    if not has_valid_coords(ally_lat, ally_lng):
        update.message.reply_text(
            "La direccion principal del aliado requiere ubicacion confirmada.\n\n"
            "Envia un PIN de Telegram o un enlace valido para continuar."
        )
        _set_flow_step(context, "ally", ALLY_UBICACION)
        return ALLY_UBICACION

    try:
        ally_data = _create_or_reset_ally_from_context(context, user_db_id)
        ally_id = ally_data["ally_id"]
        upsert_admin_ally_link(selected_admin_id, ally_id, status="PENDING")
    except Exception as e:
        logger.error("ally_confirm: no se pudo crear el registro: %s", e)
        update.message.reply_text("Error técnico al guardar tu solicitud. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END

    admin_telegram_id = context.user_data.get("ally_selected_admin_telegram_id")
    if not admin_telegram_id and selected_admin_id:
        try:
            admin_row = get_admin_by_id(selected_admin_id)
            admin_user = get_user_by_id(admin_row["user_id"]) if admin_row and admin_row.get("user_id") else None
            admin_telegram_id = admin_user["telegram_id"] if admin_user else None
        except Exception as e:
            logger.warning("No se pudo resolver telegram_id del admin local %s: %s", selected_admin_id, e)

    try:
        context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                "Nuevo registro de ALIADO pendiente:\n\n"
                f"Negocio: {ally_data['business_name']}\n"
                f"Dueño: {ally_data['owner_name']}\n"
                f"Cédula: {ally_data['ally_document']}\n"
                f"Teléfono: {ally_data['phone']}\n"
                f"Ciudad: {ally_data['city']}\n"
                f"Barrio: {ally_data['barrio']}\n"
                f"Equipo elegido: {selected_team_name}"
                f"{f' ({selected_team_code})' if selected_team_code else ''}\n\n"
                "Usa /aliados_pendientes o /admin para revisarlo."
            )
        )
        _schedule_important_alerts(
            context,
            alert_key="ally_registration_{}".format(ally_id),
            chat_id=ADMIN_USER_ID,
            reminder_text=(
                "Recordatorio importante:\n"
                "El registro de aliado #{} sigue pendiente.\n"
                "Revisa /aliados_pendientes o /admin."
            ).format(ally_id),
        )
    except Exception as e:
        logger.warning("No se pudo notificar al admin plataforma: %s", e)

    try:
        if admin_telegram_id and selected_team_code != PLATFORM_TEAM_CODE:
            context.bot.send_message(
                chat_id=admin_telegram_id,
                text=(
                    "Nueva solicitud de aliado para tu equipo.\n\n"
                    "Negocio: {}\n"
                    "Equipo: {} ({})\n\n"
                    "Entra a /mi_admin para aprobar o rechazar."
                ).format(ally_data["business_name"], selected_team_name, selected_team_code)
            )
            _schedule_important_alerts(
                context,
                alert_key="team_ally_pending_{}_{}".format(selected_admin_id, ally_id),
                chat_id=admin_telegram_id,
                reminder_text=(
                    "Recordatorio importante:\n"
                    "Tienes un aliado pendiente de aprobar en tu equipo.\n"
                    "Revisa /mi_admin."
                ),
            )
    except Exception as e:
        logger.warning("No se pudo notificar al admin local sobre aliado: %s", e)

    update.message.reply_text(
        "Listo. Tu solicitud fue enviada.\n"
        f"Equipo elegido: {selected_team_name}{f' ({selected_team_code})' if selected_team_code else ''}\n"
        "Quedas en estado PENDING hasta aprobación."
    )
    context.user_data.clear()
    return ConversationHandler.END


def show_ally_team_selection(update_or_query, context, from_callback=False):
    """
    Muestra lista de equipos (admins disponibles) y opción Ninguno.
    Si elige Ninguno, se asigna al Admin de Plataforma (TEAM_CODE de plataforma).
    """
    message = update_or_query.message or (update_or_query.callback_query.message if update_or_query.callback_query else None)
    if not context.user_data.get("ally_registration_user_id"):
        if message:
            message.reply_text("Error técnico: no encuentro tus datos del registro. Intenta /soy_aliado de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    teams = get_available_admin_teams()
    keyboard = []

    # Botones por equipo disponible
    if teams:
        for row in teams:
            admin_id = row["id"]
            team_name = row["team_name"]
            team_code = row["team_code"]
            label = f"{team_name} ({team_code})"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"ally_team_{team_code}")])

    # Opción Ninguno (default plataforma)
    keyboard.append([InlineKeyboardButton("Ninguno (Admin de Plataforma)", callback_data="ally_team_NONE")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = (
        "A que equipo (Administrador) quieres pertenecer?\n"
        "Si eliges Ninguno, quedas por defecto con el Admin de Plataforma y recargas con el."
    )

    if message:
        message.reply_text(texto, reply_markup=reply_markup)

    return ALLY_TEAM


def ally_team_callback(update, context):
    query = update.callback_query
    data = (query.data or "").strip()
    logger.debug("ally_team_callback recibió data=%s", data)
    query.answer()

    selected = parse_team_selection_callback(data, "ally_team")
    if selected is None:
        return ALLY_TEAM

    user_db_id = context.user_data.get("ally_registration_user_id")
    if not user_db_id:
        query.edit_message_text("Error técnico: no encuentro tus datos del registro. Intenta /soy_aliado de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    if selected.upper() == "NONE":
        platform_admin = get_admin_by_team_code(PLATFORM_TEAM_CODE)
        if not platform_admin:
            query.edit_message_text(
                "En este momento no existe el equipo del Admin de Plataforma (TEAM_CODE: PLATFORM).\n"
                "Crea/asegura ese admin en la tabla admins con team_code='PLATFORM' y status='APPROVED', luego intenta de nuevo."
            )
            context.user_data.clear()
            return ConversationHandler.END

        context.user_data["ally_selected_admin_id"] = platform_admin["id"]
        context.user_data["ally_selected_admin_telegram_id"] = platform_admin["telegram_id"]
        context.user_data["ally_selected_team_name"] = "PLATAFORMA"
        context.user_data["ally_selected_team_code"] = PLATFORM_TEAM_CODE
        query.edit_message_text("Equipo seleccionado: PLATAFORMA (PLATFORM).")
        return _show_ally_confirm(update, context)

    # 2) Si selecciona un TEAM_CODE real
    admin_row = get_admin_by_team_code(selected)
    if not admin_row:
        query.edit_message_text(
            "Ese TEAM_CODE no existe o no está disponible.\n"
            "Vuelve a intentar /soy_aliado."
        )
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data["ally_selected_admin_id"] = admin_row["id"]
    context.user_data["ally_selected_admin_telegram_id"] = admin_row["telegram_id"]
    context.user_data["ally_selected_team_name"] = admin_row["team_name"]
    context.user_data["ally_selected_team_code"] = admin_row["team_code"]
    query.edit_message_text(
        "Equipo seleccionado:\n"
        f"{admin_row['team_name']} ({admin_row['team_code']})"
    )
    return _show_ally_confirm(update, context)


# ----- REGISTRO DE REPARTIDOR (flujo unificado) -----

def soy_repartidor(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    existing = get_courier_by_user_id(user_db_id)
    if existing:
        status = existing["status"]
        courier_id = existing["id"]

        rejection_type = get_courier_rejection_type_by_id(courier_id)

        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de repartidor en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de repartidor aprobado (APPROVED). Si necesitas cambios, contacta al administrador."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status == "INACTIVE" and not can_courier_reregister_via_platform_reset(courier_id):
            update.message.reply_text(
                "Tu registro de repartidor esta INACTIVE.\n"
                "Solo el Administrador de Plataforma puede autorizar un reinicio del registro.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status != "INACTIVE":
            update.message.reply_text(
                f"No puedes iniciar un nuevo registro con estado {status}.\n"
                "Solo el Administrador de Plataforma puede autorizar un reinicio del registro.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

    update.message.reply_text(
        "Registro de repartidor\n\n"
        "Escribe tu nombre completo:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    _set_flow_step(context, "courier", COURIER_FULLNAME)
    return COURIER_FULLNAME


def courier_fullname(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "El nombre no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return COURIER_FULLNAME
    context.user_data["full_name"] = texto
    update.message.reply_text(
        "Escribe tu número de identificación:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_IDNUMBER)
    return COURIER_IDNUMBER


def courier_idnumber(update, context):
    doc = update.message.text.strip()
    if len(doc) < 5:
        update.message.reply_text(
            "El número de documento parece muy corto. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return COURIER_IDNUMBER
    context.user_data["id_number"] = doc
    update.message.reply_text(
        "Escribe tu número de celular:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_PHONE)
    return COURIER_PHONE


def courier_phone(update, context):
    from handlers.common import _handle_phone_input
    return _handle_phone_input(update, context,
        storage_key="phone",
        current_state=COURIER_PHONE,
        next_state=COURIER_CITY,
        flow="courier",
        next_prompt="Escribe la ciudad donde trabajas:")


def courier_city(update, context):
    from handlers.common import _handle_text_field_input
    return _handle_text_field_input(update, context,
        error_msg="La ciudad no puede estar vacía. Escríbela de nuevo:",
        storage_key="city",
        current_state=COURIER_CITY,
        next_state=COURIER_BARRIO,
        flow="courier",
        next_prompt="Escribe el barrio o sector principal donde trabajas:")


def courier_barrio(update, context):
    from handlers.common import _handle_text_field_input
    return _handle_text_field_input(update, context,
        error_msg="El barrio no puede estar vacío. Escríbelo de nuevo:",
        storage_key="barrio",
        current_state=COURIER_BARRIO,
        next_state=COURIER_RESIDENCE_ADDRESS,
        flow="courier",
        next_prompt="Escribe tu dirección de residencia:")


def courier_residence_address(update, context):
    address = update.message.text.strip()
    if not address:
        update.message.reply_text(
            "La dirección no puede estar vacía. Escríbela de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return COURIER_RESIDENCE_ADDRESS
    context.user_data["residence_address"] = address
    update.message.reply_text(
        "Envía tu ubicación GPS (pin de Telegram) o pega un link de Google Maps."
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_RESIDENCE_LOCATION)
    return COURIER_RESIDENCE_LOCATION


def courier_residence_location(update, context):
    lat = None
    lng = None
    source = None
    if update.message.location:
        lat = update.message.location.latitude
        lng = update.message.location.longitude
        source = "telegram_pin"
    else:
        text = (update.message.text or "").strip()
        coords = extract_lat_lng_from_text(text)
        if coords:
            lat, lng = coords
            source = "text_coords_or_link"
        else:
            # Geocoding: intentar como direccion escrita
            geo = resolve_location(text)
            if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
                _emit_registration_geo_confirmation(
                    update,
                    context,
                    geo,
                    text,
                    "courier_geo_si",
                    "courier_geo_no",
                    "courier_registration_location",
                )
                return COURIER_RESIDENCE_LOCATION

    if lat is None or lng is None:
        update.message.reply_text(_registration_invalid_location_text())
        return COURIER_RESIDENCE_LOCATION

    context.user_data["residence_lat"] = lat
    context.user_data["residence_lng"] = lng
    _log_registration_location_saved("courier_registration_location", source, lat, lng)
    return _ask_courier_vehicle_type(update.message, context)


def courier_geo_ubicacion_callback(update, context):
    """Maneja confirmacion de geocoding en el registro de repartidor."""
    query = update.callback_query
    query.answer()

    if query.data == "courier_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return COURIER_RESIDENCE_LOCATION
        context.user_data["residence_lat"] = lat
        context.user_data["residence_lng"] = lng
        logger.info(
            "[courier_registration_location] status=confirmed source=geocode lat=%s lng=%s",
            lat,
            lng,
        )
        query.edit_message_text("Ubicacion confirmada.")
        return _ask_courier_vehicle_type(query.message, context)
    else:  # courier_geo_no
        logger.info("[courier_registration_location] status=rejected source=geocode")
        return _geo_siguiente_o_gps(
            query,
            context,
            "courier_geo_si",
            "courier_geo_no",
            COURIER_RESIDENCE_LOCATION,
            header_text="Confirma este punto exacto antes de continuar con tu registro.",
            question_text="Es esta la ubicacion correcta?",
            no_more_text=_registration_no_more_text(),
        )


def _ask_courier_vehicle_type(message, context):
    """Muestra botones para seleccionar el tipo de vehículo del repartidor."""
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Moto / Scooter", callback_data="courier_vehiculo_moto"),
            InlineKeyboardButton("Bicicleta", callback_data="courier_vehiculo_bici"),
        ]
    ])
    message.reply_text(
        "Ubicacion guardada.\n\n"
        "Selecciona tu tipo de vehiculo:",
        reply_markup=keyboard,
    )
    _set_flow_step(context, "courier", COURIER_VEHICLE_TYPE)
    return COURIER_VEHICLE_TYPE


def courier_vehicle_type_callback(update, context):
    """Maneja la seleccion de tipo de vehiculo (Moto o Bicicleta)."""
    query = update.callback_query
    query.answer()

    if query.data == "courier_vehiculo_moto":
        context.user_data["vehicle_type"] = "MOTO"
        query.edit_message_text(
            "Vehiculo: Moto / Scooter.\n\n"
            "Escribe la placa de tu moto (o escribe 'ninguna' si no tienes):"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        _set_flow_step(context, "courier", COURIER_PLATE)
        return COURIER_PLATE
    else:  # courier_vehiculo_bici
        context.user_data["vehicle_type"] = "BICICLETA"
        context.user_data["plate"] = ""
        context.user_data["bike_type"] = ""
        query.edit_message_text(
            "Vehiculo: Bicicleta.\n\n"
            "Perfecto. Ahora necesitamos verificar tu identidad.\n\n"
            "Envia una foto del FRENTE de tu cedula de ciudadania:"
            + _OPTIONS_HINT
        )
        _set_flow_step(context, "courier", COURIER_CEDULA_FRONT)
        return COURIER_CEDULA_FRONT


def courier_plate(update, context):
    context.user_data["plate"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el tipo de moto (Ejemplo: Bóxer 100, FZ, scooter, bicicleta, etc.):"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_BIKETYPE)
    return COURIER_BIKETYPE


def courier_biketype(update, context):
    context.user_data["bike_type"] = update.message.text.strip()
    update.message.reply_text(
        "Perfecto. Ahora necesitamos verificar tu identidad.\n\n"
        "Envía una foto del FRENTE de tu cédula de ciudadanía:"
        + _OPTIONS_HINT
    )
    _set_flow_step(context, "courier", COURIER_CEDULA_FRONT)
    return COURIER_CEDULA_FRONT


def courier_cedula_front(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una foto (imagen) del frente de tu cédula." + _OPTIONS_HINT
        )
        return COURIER_CEDULA_FRONT
    context.user_data["cedula_front_file_id"] = update.message.photo[-1].file_id
    update.message.reply_text(
        "Foto del frente recibida.\n\n"
        "Ahora envía una foto del REVERSO de tu cédula:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "courier", COURIER_CEDULA_BACK)
    return COURIER_CEDULA_BACK


def courier_cedula_back(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una foto (imagen) del reverso de tu cédula." + _OPTIONS_HINT
        )
        return COURIER_CEDULA_BACK
    context.user_data["cedula_back_file_id"] = update.message.photo[-1].file_id
    update.message.reply_text(
        "Foto del reverso recibida.\n\n"
        "Por último, envía una SELFIE (foto de tu cara) tomada en este momento:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "courier", COURIER_SELFIE)
    return COURIER_SELFIE


def courier_selfie(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una selfie (foto de tu cara)." + _OPTIONS_HINT
        )
        return COURIER_SELFIE
    context.user_data["selfie_file_id"] = update.message.photo[-1].file_id
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        db_user = ensure_user(user.id, user.username)
    context.user_data["courier_registration_user_id"] = db_user["id"]

    return show_courier_team_selection(update, context)


def _show_courier_confirm(update, context):
    full_name = context.user_data.get("full_name", "")
    id_number = context.user_data.get("id_number", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    vehicle_type = context.user_data.get("vehicle_type", "MOTO")
    plate = context.user_data.get("plate", "")
    bike_type = context.user_data.get("bike_type", "")
    residence_address = context.user_data.get("residence_address", "") or "No registrada"
    residence_lat = context.user_data.get("residence_lat")
    residence_lng = context.user_data.get("residence_lng")
    selected_team_name = context.user_data.get("courier_selected_team_name", "No seleccionado")
    selected_team_code = context.user_data.get("courier_selected_team_code")
    if residence_lat is not None and residence_lng is not None:
        residence_location = "{}, {}".format(residence_lat, residence_lng)
    else:
        residence_location = "No disponible"
    team_label = (
        f"{selected_team_name} ({selected_team_code})"
        if selected_team_code else
        selected_team_name
    )

    vehiculo_label = "Moto / Scooter" if vehicle_type == "MOTO" else "Bicicleta"
    detalles_vehiculo = ""
    if vehicle_type == "MOTO":
        detalles_vehiculo = f"Placa: {plate}\nTipo de moto: {bike_type}\n"

    resumen = (
        "Fotos recibidas. Verifica tus datos de repartidor:\n\n"
        f"Nombre: {full_name}\n"
        f"Cédula: {id_number}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Dirección residencia: {residence_address}\n"
        f"Ubicación residencia: {residence_location}\n"
        f"Vehículo: {vehiculo_label}\n"
        + detalles_vehiculo +
        f"Equipo: {team_label}\n\n"
        "Si todo está bien escribe: SI\n"
        "Si quieres corregir, escribe 'volver' o usa /cancel y vuelve a /soy_repartidor"
    )
    message = update.message or (update.callback_query.message if update.callback_query else None)
    if message:
        message.reply_text(resumen)
    _set_flow_step(context, "courier", COURIER_CONFIRM)
    return COURIER_CONFIRM


# ----- REGISTRO DE ADMINISTRADOR LOCAL (foto handlers) -----

def admin_cedula_front(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una foto (imagen) del frente de tu cédula." + _OPTIONS_HINT
        )
        return LOCAL_ADMIN_CEDULA_FRONT
    context.user_data["admin_cedula_front_file_id"] = update.message.photo[-1].file_id
    _debug_admin_registration_state(context, "admin_cedula_front_saved")
    update.message.reply_text(
        "Foto del frente recibida.\n\n"
        "Ahora envía una foto del REVERSO de tu cédula:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_CEDULA_BACK)
    return LOCAL_ADMIN_CEDULA_BACK


def admin_cedula_back(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una foto (imagen) del reverso de tu cédula." + _OPTIONS_HINT
        )
        return LOCAL_ADMIN_CEDULA_BACK
    context.user_data["admin_cedula_back_file_id"] = update.message.photo[-1].file_id
    _debug_admin_registration_state(context, "admin_cedula_back_saved")
    update.message.reply_text(
        "Foto del reverso recibida.\n\n"
        "Por último, envía una SELFIE (foto de tu cara) tomada en este momento:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_SELFIE)
    return LOCAL_ADMIN_SELFIE


def admin_selfie(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una selfie (foto de tu cara)." + _OPTIONS_HINT
        )
        return LOCAL_ADMIN_SELFIE
    context.user_data["admin_selfie_file_id"] = update.message.photo[-1].file_id
    _debug_admin_registration_state(context, "admin_selfie_saved")

    full_name = context.user_data.get("admin_name", "")
    document_number = context.user_data.get("admin_document", "")
    team_name = context.user_data.get("admin_team_name", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("admin_city", "")
    barrio = context.user_data.get("admin_barrio", "")
    residence_address = context.user_data.get("admin_residence_address", "")
    lat = context.user_data.get("admin_residence_lat")
    lng = context.user_data.get("admin_residence_lng")

    resumen = (
        "Fotos recibidas. Verifica tus datos de Administrador Local:\n\n"
        "Nombre: {}\n"
        "Cédula: {}\n"
        "Equipo: {}\n"
        "Teléfono: {}\n"
        "Ciudad: {}\n"
        "Barrio: {}\n"
        "Dirección: {}\n"
        "Ubicación: {}, {}\n\n"
        "Condiciones para Administrador Local:\n"
        "1) Para operar necesitas al menos 5 aliados con saldo >= 5000.\n"
        "2) También necesitas al menos 10 repartidores con saldo >= 5000.\n"
        "3) Tu saldo master debe mantenerse en >= 60000.\n\n"
        "Si todo está correcto, escribe ACEPTAR para finalizar.\n"
        "Si quieres corregir, escribe 'volver' o usa /cancel."
    ).format(full_name, document_number, team_name, phone, city, barrio, residence_address, lat, lng)
    update.message.reply_text(resumen)
    _set_flow_step(context, "admin", LOCAL_ADMIN_CONFIRM)
    return LOCAL_ADMIN_CONFIRM


def _create_or_reset_courier_from_context(context, user_db_id: int):
    full_name = context.user_data.get("full_name", "")
    id_number = context.user_data.get("id_number", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    vehicle_type = context.user_data.get("vehicle_type", "MOTO")
    plate = context.user_data.get("plate", "")
    bike_type = context.user_data.get("bike_type", "")
    residence_address = context.user_data.get("residence_address", "")
    residence_lat = context.user_data.get("residence_lat")
    residence_lng = context.user_data.get("residence_lng")
    cedula_front_file_id = context.user_data.get("cedula_front_file_id")
    cedula_back_file_id = context.user_data.get("cedula_back_file_id")
    selfie_file_id = context.user_data.get("selfie_file_id")
    code = f"R-{user_db_id:04d}"

    previous_courier = get_courier_by_user_id(user_db_id)
    if previous_courier and can_courier_reregister_via_platform_reset(previous_courier["id"]):
        courier = reset_courier_registration_in_place_service(
            courier_id=previous_courier["id"],
            full_name=full_name,
            id_number=id_number,
            phone=phone,
            city=city,
            barrio=barrio,
            vehicle_type=vehicle_type,
            plate=plate,
            bike_type=bike_type,
            code=code,
            residence_address=residence_address,
            residence_lat=residence_lat,
            residence_lng=residence_lng,
            cedula_front_file_id=cedula_front_file_id,
            cedula_back_file_id=cedula_back_file_id,
            selfie_file_id=selfie_file_id,
        )
    else:
        create_courier(
            user_id=user_db_id,
            full_name=full_name,
            id_number=id_number,
            phone=phone,
            city=city,
            barrio=barrio,
            vehicle_type=vehicle_type,
            plate=plate,
            bike_type=bike_type,
            code=code,
            residence_address=residence_address,
            residence_lat=residence_lat,
            residence_lng=residence_lng,
            cedula_front_file_id=cedula_front_file_id,
            cedula_back_file_id=cedula_back_file_id,
            selfie_file_id=selfie_file_id,
        )
        courier = get_courier_by_user_id(user_db_id)

    if not courier:
        raise ValueError("No se pudo obtener el perfil de repartidor despues de guardar.")

    return {
        "courier": courier,
        "courier_id": courier["id"],
        "full_name": full_name,
        "id_number": id_number,
        "phone": phone,
        "city": city,
        "barrio": barrio,
        "plate": plate,
        "bike_type": bike_type,
        "code": code,
    }


def courier_confirm(update, context):
    confirm_text = update.message.text.strip().upper()

    if confirm_text not in ("SI", "SÍ", "SI.", "SÍ."):
        update.message.reply_text(
            "Registro cancelado.\n\n"
            "Si deseas intentarlo de nuevo, usa /soy_repartidor."
        )
        context.user_data.clear()
        return ConversationHandler.END

    user_db_id = context.user_data.get("courier_registration_user_id")
    selected_admin_id = context.user_data.get("courier_selected_admin_id")
    selected_team_name = context.user_data.get("courier_selected_team_name")
    selected_team_code = context.user_data.get("courier_selected_team_code")

    if not user_db_id or not selected_team_name:
        update.message.reply_text(
            "Primero debes elegir un equipo para continuar.\n\n"
            "Usa /soy_repartidor para iniciar de nuevo."
        )
        context.user_data.clear()
        return ConversationHandler.END

    try:
        courier_data = _create_or_reset_courier_from_context(context, user_db_id)
        courier_id = courier_data["courier_id"]
        create_admin_courier_link(selected_admin_id, courier_id)
    except Exception as e:
        logger.error("courier_confirm: no se pudo crear el registro: %s", e)
        update.message.reply_text("Error técnico al guardar tu solicitud. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END

    admin_telegram_id = context.user_data.get("courier_selected_admin_telegram_id")
    if not admin_telegram_id and selected_admin_id:
        try:
            admin_row = get_admin_by_id(selected_admin_id)
            admin_user = get_user_by_id(admin_row["user_id"]) if admin_row and admin_row.get("user_id") else None
            admin_telegram_id = admin_user["telegram_id"] if admin_user else None
        except Exception as e:
            logger.warning("No se pudo resolver telegram_id del admin local %s: %s", selected_admin_id, e)

    try:
        context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                "Nuevo registro de REPARTIDOR pendiente:\n\n"
                "Nombre: {}\n"
                "Cedula: {}\n"
                "Telefono: {}\n"
                "Ciudad: {}\n"
                "Barrio: {}\n"
                "Placa: {}\n"
                "Tipo de moto: {}\n"
                "Equipo elegido: {} {}\n\n"
                "Usa /admin para revisarlo."
            ).format(
                courier_data["full_name"],
                courier_data["id_number"],
                courier_data["phone"],
                courier_data["city"],
                courier_data["barrio"],
                courier_data["plate"],
                courier_data["bike_type"],
                selected_team_name,
                f"({selected_team_code})" if selected_team_code else "",
            )
        )
        _schedule_important_alerts(
            context,
            alert_key="courier_registration_{}".format(courier_id),
            chat_id=ADMIN_USER_ID,
            reminder_text=(
                "Recordatorio importante:\n"
                "El registro de repartidor #{} sigue pendiente.\n"
                "Revisa /repartidores_pendientes o /admin."
            ).format(courier_id),
        )
    except Exception as e:
        logger.warning("No se pudo notificar al admin plataforma: %s", e)

    try:
        if admin_telegram_id and selected_team_code != PLATFORM_TEAM_CODE:
            context.bot.send_message(
                chat_id=admin_telegram_id,
                text=(
                    "Nueva solicitud de repartidor para tu equipo.\n\n"
                    f"Repartidor ID: {courier_id}\n"
                    f"Equipo: {selected_team_name}\n"
                    f"Código: {selected_team_code}\n\n"
                    "Entra a /mi_admin para aprobar o rechazar."
                )
            )
            _schedule_important_alerts(
                context,
                alert_key="team_courier_pending_{}_{}".format(selected_admin_id, courier_id),
                chat_id=admin_telegram_id,
                reminder_text=(
                    "Recordatorio importante:\n"
                    "Tienes un repartidor pendiente de aprobar en tu equipo.\n"
                    "Revisa /mi_admin."
                ),
            )
    except Exception as e:
        logger.warning("No se pudo notificar al admin local: %s", e)

    update.message.reply_text(
        "Listo. Tu solicitud fue enviada.\n"
        f"Equipo elegido: {selected_team_name}{f' ({selected_team_code})' if selected_team_code else ''}\n"
        "Quedas en estado PENDING hasta aprobación."
    )
    context.user_data.clear()
    return ConversationHandler.END


def show_courier_team_selection(update, context):
    """Muestra lista de equipos (admins) con botones para el repartidor."""
    if not context.user_data.get("courier_registration_user_id"):
        update.message.reply_text("Error técnico: no encuentro tus datos del registro. Intenta /soy_repartidor de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    teams = get_available_admin_teams()
    keyboard = []

    if teams:
        for row in teams:
            admin_id = row["id"]
            team_name = row["team_name"]
            team_code = row["team_code"]
            label = f"{team_name} ({team_code})"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"courier_team_{team_code}")])

    keyboard.append([InlineKeyboardButton("Ninguno (Admin de Plataforma)", callback_data="courier_team_NONE")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "¿A qué equipo (Administrador) quieres pertenecer?\n"
        "Si eliges Ninguno, quedas por defecto con el Admin de Plataforma.",
        reply_markup=reply_markup
    )

    return COURIER_TEAM


def courier_team_callback(update, context):
    """Maneja la selección de equipo del repartidor (botones)."""
    query = update.callback_query
    data = (query.data or "").strip()
    query.answer()

    selected = parse_team_selection_callback(data, "courier_team")
    if selected is None:
        return COURIER_TEAM

    user_db_id = context.user_data.get("courier_registration_user_id")
    if not user_db_id:
        query.edit_message_text("Error técnico: no encuentro tus datos del registro. Intenta /soy_repartidor de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    if selected.upper() == "NONE":
        platform_admin = get_admin_by_team_code(PLATFORM_TEAM_CODE)
        if not platform_admin:
            query.edit_message_text(
                "En este momento no existe el equipo del Admin de Plataforma (TEAM_CODE: PLATFORM).\n"
                "Contacta al administrador."
            )
            context.user_data.clear()
            return ConversationHandler.END

        context.user_data["courier_selected_admin_id"] = platform_admin["id"]
        context.user_data["courier_selected_admin_telegram_id"] = platform_admin["telegram_id"]
        context.user_data["courier_selected_team_name"] = "PLATAFORMA"
        context.user_data["courier_selected_team_code"] = PLATFORM_TEAM_CODE
        query.edit_message_text("Equipo seleccionado: PLATAFORMA (PLATFORM).")
        return _show_courier_confirm(update, context)

    admin_row = get_admin_by_team_code(selected)
    if not admin_row:
        query.edit_message_text(
            "Ese código de equipo no existe o no está disponible.\n"
            "Vuelve a intentar /soy_repartidor."
        )
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data["courier_selected_admin_id"] = admin_row["id"]
    context.user_data["courier_selected_admin_telegram_id"] = admin_row["telegram_id"]
    context.user_data["courier_selected_team_name"] = admin_row["team_name"]
    context.user_data["courier_selected_team_code"] = admin_row["team_code"]
    query.edit_message_text(
        "Equipo seleccionado:\n"
        f"{admin_row['team_name']} ({admin_row['team_code']})"
    )
    return _show_courier_confirm(update, context)


# =============================================================================
# ConversationHandler definitions
# =============================================================================

ally_conv = ConversationHandler(
    entry_points=[CommandHandler("soy_aliado", soy_aliado)],
    states={
        ALLY_NAME: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_name)],
        ALLY_OWNER: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_owner)],
        ALLY_DOCUMENT: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_document)],
        ALLY_PHONE: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_phone)],
        ALLY_CITY: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_city)],
        ALLY_BARRIO: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_barrio)],
        ALLY_ADDRESS: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_address)],
        ALLY_UBICACION: [
            CallbackQueryHandler(ally_geo_ubicacion_callback, pattern=r"^ally_geo_"),
            MessageHandler(Filters.location, ally_ubicacion_location_handler),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_ubicacion_handler),
        ],
        ALLY_CONFIRM: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ally_confirm)],
        ALLY_TEAM: [CallbackQueryHandler(ally_team_callback, pattern=r"^ally_team(?::|_)")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="ally_conv",
    persistent=True,
)

courier_conv = ConversationHandler(
    entry_points=[CommandHandler("soy_repartidor", soy_repartidor)],
    states={
        COURIER_FULLNAME: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_fullname)
        ],
        COURIER_IDNUMBER: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_idnumber)
        ],
        COURIER_PHONE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_phone)
        ],
        COURIER_CITY: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_city)
        ],
        COURIER_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_barrio)
        ],
        COURIER_RESIDENCE_ADDRESS: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_residence_address)
        ],
        COURIER_RESIDENCE_LOCATION: [
            CallbackQueryHandler(courier_geo_ubicacion_callback, pattern=r"^courier_geo_"),
            MessageHandler(Filters.location, courier_residence_location),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_residence_location),
        ],
        COURIER_VEHICLE_TYPE: [
            CallbackQueryHandler(courier_vehicle_type_callback, pattern=r"^courier_vehiculo_"),
        ],
        COURIER_PLATE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_plate)
        ],
        COURIER_BIKETYPE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_biketype)
        ],
        COURIER_CEDULA_FRONT: [
            MessageHandler(Filters.photo, courier_cedula_front),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_cedula_front),
        ],
        COURIER_CEDULA_BACK: [
            MessageHandler(Filters.photo, courier_cedula_back),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_cedula_back),
        ],
        COURIER_SELFIE: [
            MessageHandler(Filters.photo, courier_selfie),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_selfie),
        ],
        COURIER_CONFIRM: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, courier_confirm)
        ],
        COURIER_TEAM: [
            CallbackQueryHandler(courier_team_callback, pattern=r"^courier_team(?::|_)")
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="courier_conv",
    persistent=True,
)


# =============================================================================
# Admin registration handlers
# =============================================================================

        
def soy_admin(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    existing = get_admin_by_user_id(user_db_id)
    if existing:
        status = existing["status"]
        admin_id = existing["id"]

        rejection_type = get_admin_rejection_type_by_id(admin_id)

        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de administrador en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de administrador aprobado (APPROVED). Si necesitas cambios, contacta al administrador de plataforma."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador de plataforma.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status == "INACTIVE" and not can_admin_reregister_via_platform_reset(admin_id):
            update.message.reply_text(
                "Tu registro de administrador esta INACTIVE.\n"
                "Solo el Administrador de Plataforma puede autorizar un reinicio del registro.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status != "INACTIVE":
            update.message.reply_text(
                f"No puedes iniciar un nuevo registro con estado {status}.\n"
                "Solo el Administrador de Plataforma puede autorizar un reinicio del registro.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        team_name = existing["team_name"] or existing["full_name"]
        doc = existing["document_number"] or "No registrado"
        full_name = existing["full_name"]
        phone = existing["phone"]
        city = existing["city"]
        barrio = existing["barrio"]

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
        _set_flow_step(context, "admin", LOCAL_ADMIN_NAME)
        return LOCAL_ADMIN_NAME

    update.message.reply_text(
        "Registro de Administrador Local.\n\n"
        "Escribe tu nombre completo:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_NAME)
    return LOCAL_ADMIN_NAME


def admin_name(update, context):
    text = update.message.text.strip()

    if context.user_data.get("admin_update_prompt"):
        answer = text.upper()
        context.user_data.pop("admin_update_prompt", None)
        if answer == "SI":
            update.message.reply_text(
                "Perfecto. Escribe tu nombre completo:"
                "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
            )
            _set_flow_step(context, "admin", LOCAL_ADMIN_NAME)
            return LOCAL_ADMIN_NAME
        update.message.reply_text("Entendido. No se modificó tu registro.")
        context.user_data.clear()
        return ConversationHandler.END

    if not text:
        update.message.reply_text(
            "El nombre no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return LOCAL_ADMIN_NAME

    context.user_data["admin_name"] = text
    _debug_admin_registration_state(context, "admin_name_saved")
    update.message.reply_text(
        "Escribe tu número de documento (CC o equivalente):"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_DOCUMENT)
    return LOCAL_ADMIN_DOCUMENT


def admin_document(update, context):
    doc = update.message.text.strip()
    if len(doc) < 5:
        update.message.reply_text(
            "El número de documento parece muy corto. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return LOCAL_ADMIN_DOCUMENT

    context.user_data["admin_document"] = doc
    _debug_admin_registration_state(context, "admin_document_saved")
    update.message.reply_text(
        "Escribe el nombre de tu administración (nombre del equipo).\n"
        "Ejemplo: Mensajeros Pereira Centro"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_TEAMNAME)
    return LOCAL_ADMIN_TEAMNAME


def admin_teamname(update, context):
    team_name = update.message.text.strip()
    if len(team_name) < 3:
        update.message.reply_text(
            "El nombre de la administración debe tener al menos 3 caracteres. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return LOCAL_ADMIN_TEAMNAME

    context.user_data["admin_team_name"] = team_name
    _debug_admin_registration_state(context, "admin_teamname_saved")
    update.message.reply_text(
        "Escribe tu número de teléfono:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_PHONE)
    return LOCAL_ADMIN_PHONE


def admin_phone(update, context):
    next_state = _handle_phone_input(update, context,
        storage_key="phone",
        current_state=LOCAL_ADMIN_PHONE,
        next_state=LOCAL_ADMIN_CITY,
        flow="admin",
        next_prompt="¿En qué ciudad vas a operar como Administrador Local?")
    if next_state == LOCAL_ADMIN_CITY:
        _debug_admin_registration_state(context, "admin_phone_saved")
    return next_state


def admin_city(update, context):
    next_state = _handle_text_field_input(update, context,
        error_msg="La ciudad no puede estar vacía. Escríbela de nuevo:",
        storage_key="admin_city",
        current_state=LOCAL_ADMIN_CITY,
        next_state=LOCAL_ADMIN_BARRIO,
        flow="admin",
        next_prompt="Escribe tu barrio o zona base de operación:")
    if next_state == LOCAL_ADMIN_BARRIO:
        _debug_admin_registration_state(context, "admin_city_saved")
    return next_state


def admin_barrio(update, context):
    next_state = _handle_text_field_input(update, context,
        error_msg="El barrio no puede estar vacío. Escríbelo de nuevo:",
        storage_key="admin_barrio",
        current_state=LOCAL_ADMIN_BARRIO,
        next_state=LOCAL_ADMIN_RESIDENCE_ADDRESS,
        flow="admin",
        next_prompt="Escribe tu dirección de residencia (texto exacto). Ej: Calle 10 # 20-30, apto 301")
    if next_state == LOCAL_ADMIN_RESIDENCE_ADDRESS:
        _debug_admin_registration_state(context, "admin_barrio_saved")
    return next_state


def admin_residence_address(update, context):
    address = update.message.text.strip()
    if len(address) < 6:
        update.message.reply_text(
            "La dirección debe tener al menos 6 caracteres. Escríbela de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return LOCAL_ADMIN_RESIDENCE_ADDRESS
    context.user_data["admin_residence_address"] = address
    _debug_admin_registration_state(context, "admin_residence_address_saved")
    update.message.reply_text(
        "Envía tu ubicación GPS (pin de Telegram) o pega un link de Google Maps."
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_RESIDENCE_LOCATION)
    return LOCAL_ADMIN_RESIDENCE_LOCATION


def admin_residence_location(update, context):
    lat = None
    lng = None
    source = None

    if update.message.location:
        lat = update.message.location.latitude
        lng = update.message.location.longitude
        source = "telegram_pin"
    else:
        text = (update.message.text or "").strip()
        coords = extract_lat_lng_from_text(text)
        if coords:
            lat, lng = coords
            source = "text_coords_or_link"
        else:
            # Geocoding: intentar como direccion escrita
            geo = resolve_location(text)
            if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
                _emit_registration_geo_confirmation(
                    update,
                    context,
                    geo,
                    text,
                    "admin_geo_si",
                    "admin_geo_no",
                    "admin_registration_location",
                )
                return LOCAL_ADMIN_RESIDENCE_LOCATION

    if lat is None or lng is None:
        _debug_admin_registration_state(context, "admin_residence_location_missing_coords")
        update.message.reply_text(_registration_invalid_location_text())
        return LOCAL_ADMIN_RESIDENCE_LOCATION

    context.user_data["admin_residence_lat"] = lat
    context.user_data["admin_residence_lng"] = lng
    _log_registration_location_saved("admin_registration_location", source, lat, lng)
    _debug_admin_registration_state(context, "admin_residence_location_saved")
    update.message.reply_text(
        "Ubicacion guardada.\n\n"
        "Para verificar tu identidad, necesitamos fotos de tu documento.\n\n"
        "Envia una foto del FRENTE de tu cedula:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_CEDULA_FRONT)
    return LOCAL_ADMIN_CEDULA_FRONT


def admin_geo_ubicacion_callback(update, context):
    """Maneja confirmacion de geocoding en el registro de admin local."""
    query = update.callback_query
    query.answer()

    if query.data == "admin_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            _debug_admin_registration_state(context, "admin_geo_confirm_missing_pending")
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return LOCAL_ADMIN_RESIDENCE_LOCATION
        context.user_data["admin_residence_lat"] = lat
        context.user_data["admin_residence_lng"] = lng
        logger.info(
            "[admin_registration_location] status=confirmed source=geocode lat=%s lng=%s",
            lat,
            lng,
        )
        _debug_admin_registration_state(context, "admin_geo_confirm_saved")
        query.edit_message_text(
            "Ubicacion confirmada.\n\n"
            "Para verificar tu identidad, necesitamos fotos de tu documento.\n\n"
            "Envia una foto del FRENTE de tu cedula:" + _OPTIONS_HINT
        )
        _set_flow_step(context, "admin", LOCAL_ADMIN_CEDULA_FRONT)
        return LOCAL_ADMIN_CEDULA_FRONT
    else:  # admin_geo_no
        logger.info("[admin_registration_location] status=rejected source=geocode")
        return _geo_siguiente_o_gps(
            query,
            context,
            "admin_geo_si",
            "admin_geo_no",
            LOCAL_ADMIN_RESIDENCE_LOCATION,
            header_text="Confirma este punto exacto antes de continuar con tu registro.",
            question_text="Es esta la ubicacion correcta?",
            no_more_text=_registration_no_more_text(),
        )


def admin_confirm(update, context):
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
    residence_address = (context.user_data.get("admin_residence_address") or "").strip()
    residence_lat = context.user_data.get("admin_residence_lat")
    residence_lng = context.user_data.get("admin_residence_lng")
    cedula_front_file_id = context.user_data.get("admin_cedula_front_file_id")
    cedula_back_file_id = context.user_data.get("admin_cedula_back_file_id")
    selfie_file_id = context.user_data.get("admin_selfie_file_id")
    _debug_admin_registration_state(context, "admin_confirm_before_create", answer=answer)

    try:
        previous_admin = get_admin_by_user_id(user_db_id)
        if previous_admin and can_admin_reregister_via_platform_reset(previous_admin["id"]):
            admin = reset_admin_registration_in_place_service(
                admin_id=previous_admin["id"],
                full_name=full_name,
                phone=phone,
                city=city,
                barrio=barrio,
                team_name=team_name,
                document_number=document_number,
                residence_address=residence_address,
                residence_lat=residence_lat,
                residence_lng=residence_lng,
                cedula_front_file_id=cedula_front_file_id,
                cedula_back_file_id=cedula_back_file_id,
                selfie_file_id=selfie_file_id,
            )
            admin_id = admin["id"]
            team_code = admin["team_code"]
        else:
            admin_id, team_code = create_admin(
                user_db_id,
                full_name,
                phone,
                city,
                barrio,
                team_name,
                document_number,
                residence_address,
                residence_lat,
                residence_lng,
                cedula_front_file_id,
                cedula_back_file_id,
                selfie_file_id,
            )
    except ValueError as e:
        _debug_admin_registration_state(context, "admin_confirm_value_error", error=str(e))
        update.message.reply_text(str(e))
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error("admin_confirm: %s", e)
        _debug_admin_registration_state(context, "admin_confirm_exception", error=str(e))
        update.message.reply_text("Error técnico al finalizar tu registro. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END
    _debug_admin_registration_state(context, "admin_confirm_success", admin_id=admin_id)

    try:
        context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                "Nuevo registro de ADMINISTRADOR LOCAL pendiente:\n\n"
                "Nombre: {}\n"
                "Documento: {}\n"
                "Equipo: {}\n"
                "Codigo de equipo: {}\n"
                "Telefono: {}\n"
                "Ciudad: {}\n"
                "Barrio: {}\n\n"
                "Usa /admin para revisarlo."
            ).format(full_name, document_number, team_name, team_code, phone, city, barrio)
        )
        _schedule_important_alerts(
            context,
            alert_key="admin_registration_{}".format(admin_id),
            chat_id=ADMIN_USER_ID,
            reminder_text=(
                "Recordatorio importante:\n"
                "El registro de administrador local #{} sigue pendiente.\n"
                "Revisa /admin."
            ).format(admin_id),
        )
    except Exception as e:
        logger.warning("No se pudo notificar al admin plataforma: %s", e)

    update.message.reply_text(
        "Registro de Administrador Local recibido.\n"
        "Estado: PENDING\n\n"
        f"Dirección residencia: {residence_address}\n"
        f"Coordenadas: {residence_lat}, {residence_lng}\n\n"
        f"Tu CÓDIGO DE EQUIPO es: {team_code}\n"
        "Compártelo con los repartidores que quieras vincular a tu equipo.\n\n"
        "Recuerda: para operar necesitas 5 aliados con saldo >= 5000, 10 repartidores con saldo >= 5000 y saldo master >= 60000."
    )

    context.user_data.clear()
    return ConversationHandler.END
    


admin_conv = ConversationHandler(
    entry_points=[
        CommandHandler("soy_admin", soy_admin),
        CommandHandler("soy_administrador", soy_admin),
    ],

    states={
        LOCAL_ADMIN_NAME: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_name)],
        LOCAL_ADMIN_DOCUMENT: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_document)],
        LOCAL_ADMIN_TEAMNAME: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_teamname)],
        LOCAL_ADMIN_PHONE: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_phone)],
        LOCAL_ADMIN_CITY: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_city)],
        LOCAL_ADMIN_BARRIO: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_barrio)],
        LOCAL_ADMIN_RESIDENCE_ADDRESS: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_residence_address)],
        LOCAL_ADMIN_RESIDENCE_LOCATION: [
            CallbackQueryHandler(admin_geo_ubicacion_callback, pattern=r"^admin_geo_"),
            MessageHandler(Filters.location, admin_residence_location),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_residence_location),
        ],
        LOCAL_ADMIN_CEDULA_FRONT: [
            MessageHandler(Filters.photo, admin_cedula_front),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_cedula_front),
        ],
        LOCAL_ADMIN_CEDULA_BACK: [
            MessageHandler(Filters.photo, admin_cedula_back),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_cedula_back),
        ],
        LOCAL_ADMIN_SELFIE: [
            MessageHandler(Filters.photo, admin_selfie),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_selfie),
        ],
        LOCAL_ADMIN_CONFIRM: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_confirm)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    name="admin_conv",
    persistent=True,
)
