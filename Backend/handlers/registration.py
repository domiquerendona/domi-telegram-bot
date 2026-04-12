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
    ALLY_UBICACION, ALLY_CONFIRM, ALLY_TEAM,
    COURIER_FULLNAME, COURIER_IDNUMBER, COURIER_PHONE, COURIER_CITY, COURIER_BARRIO,
    COURIER_RESIDENCE_LOCATION, COURIER_VEHICLE_TYPE,
    COURIER_PLATE, COURIER_BIKETYPE, COURIER_CEDULA_FRONT, COURIER_CEDULA_BACK,
    COURIER_SELFIE, COURIER_CONFIRM, COURIER_TEAM,
    LOCAL_ADMIN_NAME, LOCAL_ADMIN_DOCUMENT, LOCAL_ADMIN_TEAMNAME,
    LOCAL_ADMIN_PHONE, LOCAL_ADMIN_CITY, LOCAL_ADMIN_BARRIO,
    LOCAL_ADMIN_RESIDENCE_LOCATION,
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
    _maybe_cache_confirmed_geo,
    _mostrar_confirmacion_geocode,
    _schedule_important_alerts,
    _set_flow_step,
    cancel_conversacion,
    cancel_por_texto,
    volver_paso_anterior,
    clear_registration_flow_data,
)
from services import (
    ADMIN_INVITE_USER_DATA_KEY,
    audit_admin_invite_event,
    audit_admin_invite_submission,
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
    resolve_admin_invite_from_token,
    resolve_location,
    update_ally_location,
    update_ally_location_coords,
    upsert_admin_ally_link,
)

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
PLATFORM_TEAM_CODE = "PLATFORM"


def _reg_city_hint(context, city_key="city", barrio_key="barrio"):
    """Retorna barrio+ciudad ya capturados en el flujo de registro para mejorar geocoding."""
    parts = [p for p in [context.user_data.get(barrio_key), context.user_data.get(city_key)] if p]
    return ", ".join(parts) if parts else None


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


def _emit_registration_geo_confirmation(update, context, geo, texto, cb_si, cb_no, log_tag, city_hint=None):
    logger.info(
        "[%s] status=pending source=%s lat=%s lng=%s",
        log_tag,
        geo.get("method"),
        geo.get("lat"),
        geo.get("lng"),
    )
    context.user_data["pending_geo_city_hint"] = city_hint
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


def _clear_invite_token(context):
    context.user_data.pop(ADMIN_INVITE_USER_DATA_KEY, None)


def _resolve_registration_invite(context, expected_role: str):
    raw_token = (context.user_data.get(ADMIN_INVITE_USER_DATA_KEY) or "").strip()
    if not raw_token:
        return None
    invite = resolve_admin_invite_from_token(raw_token, expected_role=expected_role)
    if not invite:
        _clear_invite_token(context)
        return None
    return invite


def _apply_invite_team_selection(context, prefix: str, invite: dict):
    context.user_data[f"{prefix}_selected_admin_id"] = invite["admin_id"]
    context.user_data[f"{prefix}_selected_admin_telegram_id"] = invite["admin_telegram_id"]
    context.user_data[f"{prefix}_selected_team_name"] = invite["team_name"]
    context.user_data[f"{prefix}_selected_team_code"] = invite["team_code"]


# ----- REGISTRO DE ALIADO (flujo unificado) -----

def soy_aliado(update, context):
    if update.callback_query:
        try:
            update.callback_query.answer()
            update.callback_query.delete_message()
        except Exception:
            pass
    user_db_id = get_user_db_id_from_update(update)
    clear_registration_flow_data(context)

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
        "Registro de aliado (7 pasos)\n\n"
        "Paso 1 de 7: Nombre del negocio\n\n"
        "Escribe el nombre comercial de tu negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    _set_flow_step(context, "ally", ALLY_NAME)
    return ALLY_NAME

# ... (el resto del archivo registration.py sin cambios) ...
