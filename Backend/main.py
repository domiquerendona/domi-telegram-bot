import logging
import os
import hashlib
import time
import traceback
from datetime import datetime, timezone
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import BadRequest
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
    PicklePersistence,
)

from services import (
    ADMIN_INVITE_START_PREFIX,
    ADMIN_INVITE_USER_DATA_KEY,
    audit_admin_invite_event,
    register_platform_income,
    build_order_pricing_breakdown,
    admin_puede_operar,
    calcular_precio_distancia,
    get_pricing_config,
    get_buy_pricing_config,
    calc_buy_products_surcharge,
    approve_role_registration,
    quote_order_by_addresses,
    quote_order_by_coords,
    quote_order_from_inputs,
    extract_lat_lng_from_text,
    expand_short_url,
    can_call_google_today,
    can_use_cotizador,
    extract_place_id_from_url,
    google_place_details,
    approve_recharge_request,
    reject_recharge_request,
    check_service_fee_available,
    resolve_location,
    resolve_location_next,
    has_valid_coords,
    get_smart_distance,
    _get_important_alert_config,
    es_admin_plataforma,
    _get_reference_reviewer,
    _get_missing_role_commands,
    get_user_by_id,
    resolve_admin_telegram_id,
    get_admin_registration_invites,
    resolve_admin_invite_from_start_arg,
    get_available_admin_teams,
    get_admin_invite_registrations,
    has_recent_invite_open,
    regenerate_admin_invite_by_role,
    # Alertas de oferta
    get_offer_alerts_config,
    save_offer_voice,
    set_offer_reminders_enabled,
    set_offer_reminder_seconds,
    set_offer_voice_enabled,
    clear_offer_voice,
    save_pricing_setting,
    # Candidatos de referencias
    get_pending_reference_candidates,
    get_reference_candidate,
    review_reference_candidate,
    set_reference_candidate_coords,
    # Funciones de acceso a datos (re-exportadas desde db vía services)
    ensure_user,
    get_user_db_id_from_update,
    get_user_by_telegram_id,
    get_admin_rejection_type_by_id,
    get_ally_rejection_type_by_id,
    get_courier_rejection_type_by_id,
    get_admin_reset_state_by_id,
    get_ally_reset_state_by_id,
    get_courier_reset_state_by_id,
    can_admin_reregister_via_platform_reset,
    can_ally_reregister_via_platform_reset,
    can_courier_reregister_via_platform_reset,
    platform_enable_admin_registration_reset,
    platform_enable_ally_registration_reset,
    platform_enable_courier_registration_reset,
    platform_clear_admin_registration_reset,
    platform_clear_ally_registration_reset,
    platform_clear_courier_registration_reset,
    reset_admin_registration_in_place_service,
    reset_ally_registration_in_place_service,
    reset_courier_registration_in_place_service,
    list_approved_admin_teams,
    list_courier_links_by_admin,
    list_ally_links_by_admin,
    get_platform_admin_id,
    upsert_admin_ally_link,
    create_admin_courier_link,
    deactivate_other_approved_admin_courier_links,
    deactivate_other_approved_admin_ally_links,
    get_local_admins_count,
    create_ally,
    get_ally_by_user_id,
    get_pending_allies,
    get_ally_by_id,
    update_ally_status,
    update_ally_status_by_id,
    update_ally,
    delete_ally,
    create_admin,
    get_admin_by_user_id,
    get_admin_by_telegram_id,
    user_has_platform_admin,
    get_all_admins,
    get_pending_admins,
    get_admin_by_id,
    get_admin_status_by_id,
    update_admin_status_by_id,
    count_admin_couriers,
    count_admin_couriers_with_min_balance,
    get_admin_by_team_code,
    update_admin_courier_status,
    upsert_admin_courier_link,
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
    create_admin_location,
    get_admin_locations,
    get_admin_location_by_id,
    get_default_admin_location,
    increment_admin_location_usage,
    create_courier,
    get_courier_by_user_id,
    get_courier_by_id,
    get_courier_by_telegram_id,
    set_courier_available_cash,
    can_courier_activate,
    deactivate_courier,
    update_courier_live_location,
    set_courier_availability,
    expire_stale_live_locations,
    get_pending_couriers,
    get_pending_couriers_by_admin,
    get_pending_allies_by_admin,
    get_all_local_admins,
    get_allies_by_admin_and_status,
    get_couriers_by_admin_and_status,
    update_courier_status,
    update_courier_status_by_id,
    get_courier_approval_notification_chat_id,
    get_ally_approval_notification_chat_id,
    parse_team_selection_callback,
    update_courier,
    delete_courier,
    get_admin_link_for_courier,
    get_admin_link_for_ally,
    get_courier_link_balance,
    create_order,
    set_order_status,
    assign_order_to_courier,
    get_order_by_id,
    get_orders_by_ally,
    get_orders_by_courier,
    get_courier_active_order_stage_line,
    get_active_order_for_courier,
    get_active_orders_for_courier,
    get_active_route_for_courier,
    get_pending_route_stops,
    get_route_destinations,
    ally_get_order_for_incentive,
    ally_increment_order_incentive,
    admin_get_order_for_incentive,
    admin_increment_order_incentive,
    courier_get_earnings_history,
    courier_get_earnings_by_date_key,
    get_totales_registros,
    add_courier_rating,
    get_active_terms_version,
    has_accepted_terms,
    save_terms_acceptance,
    save_terms_session_ack,
    create_ally_customer,
    update_ally_customer,
    archive_ally_customer,
    restore_ally_customer,
    get_ally_customer_by_id,
    get_ally_customer_by_phone,
    list_ally_customers,
    search_ally_customers,
    create_customer_address,
    update_customer_address,
    archive_customer_address,
    restore_customer_address,
    get_customer_address_by_id,
    list_customer_addresses,
    find_matching_customer_address,
    update_customer_address_coords,
    get_last_order_by_ally,
    get_recent_delivery_addresses_for_ally,
    get_link_cache,
    upsert_link_cache,
    get_approved_admin_link_for_courier,
    get_approved_admin_link_for_ally,
    get_all_approved_links_for_courier,
    get_all_approved_links_for_ally,
    get_admin_balance,
    get_sociedad_balance,
    get_platform_admin,
    ensure_platform_temp_coverage_for_ally,
    create_recharge_request,
    list_pending_recharges_for_admin,
    list_all_pending_recharges,
    get_admins_with_pending_count,
    list_recharge_ledger,
    get_recharge_request,
    get_admin_payment_info,
    update_admin_payment_info,
    update_recharge_proof,
    create_payment_method,
    get_payment_method_by_id,
    list_payment_methods,
    toggle_payment_method,
    deactivate_payment_method,
    get_admin_reference_validator_permission,
    set_admin_reference_validator_permission,
    # Rutas multi-parada
    calcular_precio_ruta,
    calcular_distancia_ruta,
    calcular_distancia_ruta_smart,
    create_route,
    create_route_destination,
    get_all_online_couriers,
    get_active_orders_without_courier,
    get_online_couriers_sorted_by_distance,
    block_courier_for_ally,
    unblock_courier_for_ally,
    get_blocked_courier_ids_for_ally,
    archive_admin_location,
    update_admin_location,
    create_admin_customer,
    update_admin_customer,
    archive_admin_customer,
    restore_admin_customer,
    get_admin_customer_by_id,
    get_admin_customer_by_phone,
    list_admin_customers,
    search_admin_customers,
    create_admin_customer_address,
    update_admin_customer_address,
    archive_admin_customer_address,
    restore_admin_customer_address,
    get_admin_customer_address_by_id,
    list_admin_customer_addresses,
    sync_all_courier_link_statuses,
    # Bandeja de solicitudes del aliado (enlace publico)
    get_or_create_ally_public_token,
    list_ally_form_requests_for_ally,
    get_ally_form_request_by_id,
    update_ally_form_request_status,
    mark_ally_form_request_converted,
    update_ally_delivery_subsidy,
    update_ally_min_purchase_for_subsidy,
    count_ally_form_requests_by_status,
    compute_ally_subsidy,
    expire_old_ally_subscriptions,
    get_all_pending_fee_collections,
    get_expiring_ally_subscriptions,
)
from order_delivery import publish_order_to_couriers, order_courier_callback, ally_active_orders, ally_orders_history_callback, admin_orders_panel, admin_orders_callback, publish_route_to_couriers, handle_route_callback, handle_rating_callback, check_courier_arrival_at_pickup, repost_order_to_couriers, recover_scheduled_jobs, recover_active_offer_dispatches, admin_special_orders_history_callback, _get_order_visible_pickup_line, _get_order_visible_dropoff_line, _get_route_visible_pickup_line, _get_route_stop_visible_line
from db import (
    init_db,
    force_platform_admin,
    ensure_pricing_defaults,
    ensure_platform_sociedad,
)
from profile_changes import (
    profile_change_conv,
    admin_change_requests_callback,
    admin_change_requests_list,
    chgreq_reject_reason_handler,
)
from handlers.states import *
from handlers.common import (
    _set_flow_step,
    _debug_admin_registration_state,
    _OPTIONS_HINT,
    CANCELAR_VOLVER_MENU_REGEX,
    CANCELAR_VOLVER_MENU_FILTER,
    _handle_phone_input,
    _handle_text_field_input,
    _clear_flow_data_from_state,
    _send_back_prompt,
    volver_paso_anterior,
    _row_value,
    _get_courier_toggle_button_label,
    _courier_main_button_label,
    get_main_menu_keyboard,
    get_flow_menu_keyboard,
    get_ally_menu_keyboard,
    get_repartidor_menu_keyboard,
    _get_chat_id,
    _get_user_roles,
    show_main_menu,
    show_flow_menu,
    cancel_conversacion,
    cancel_por_texto,
    _cotizar_resolver_ubicacion,
    _mostrar_confirmacion_geocode,
    _geo_siguiente_o_gps,
    _important_alert_job,
    _schedule_important_alerts,
    _resolve_important_alert,
    _build_role_welcome_message,
    _send_role_welcome_message,
)
from handlers.config import (
    tarifas_conv,
    config_alertas_oferta_conv,
    config_ally_subsidy_conv,
    config_ally_minpurchase_conv,
    config_subs_conv,
    tarifas_edit_callback,
)
from handlers.quotation import cotizar_conv
from handlers.location_agenda import (
    admin_dirs_conv,
    ally_locs_conv,
    _ally_locs_mostrar_lista,
    mis_ubicaciones_start,
)
from handlers.customer_agenda import (
    admin_clientes_conv,
    ally_clientes_conv,
    agenda_conv,
    plat_corregir_addr_conv,
)
from handlers.recharges import (
    recargar_conv,
    configurar_pagos_conv,
    ingreso_conv,
    recarga_directa_conv,
    cmd_saldo,
    cmd_recargar,
    cmd_recargas_pendientes,
    cmd_configurar_pagos,
    recharge_callback,
    recharge_proof_callback,
    plat_recargas_callback,
    local_recargas_pending_callback,
    admin_local_callback,
    ally_approval_callback,
    ally_suscripcion_conv,
    admin_movimientos_callback,
    admin_movimientos_periodo_callback,
    admin_mi_saldo_callback,
    sociedad_retiro_conv,
)
from handlers.registration import (
    soy_aliado,
    ally_name,
    ally_owner,
    ally_document,
    ally_phone,
    ally_city,
    ally_barrio,
    ally_ubicacion_handler,
    ally_ubicacion_location_handler,
    ally_geo_ubicacion_callback,
    ally_confirm,
    show_ally_team_selection,
    ally_team_callback,
    soy_repartidor,
    courier_fullname,
    courier_idnumber,
    courier_phone,
    courier_city,
    courier_barrio,
    courier_residence_location,
    courier_geo_ubicacion_callback,
    courier_plate,
    courier_biketype,
    courier_cedula_front,
    courier_cedula_back,
    courier_selfie,
    courier_confirm,
    show_courier_team_selection,
    courier_team_callback,
    admin_cedula_front,
    admin_cedula_back,
    admin_selfie,
    ally_conv,
    courier_conv,
    admin_conv,
)

from handlers.order import (
    nuevo_pedido_desde_cotizador, nuevo_pedido, nuevo_pedido_tras_terms,
    pedido_selector_cliente_callback, pedido_buscar_cliente,
    pedido_seleccionar_direccion_callback, pedido_instrucciones_callback,
    pedido_instrucciones_text, get_tipo_servicio_keyboard,
    mostrar_selector_tipo_servicio, pedido_tipo_servicio_callback,
    _parsear_lista_productos, pedido_compras_cantidad_handler,
    pedido_ubicacion_handler, pedido_ubicacion_location_handler,
    pedido_geo_ubicacion_callback, pedido_reciente_dir_callback,
    pedido_nueva_dir_en_ubicacion_callback, pedido_ubicacion_copiar_msg_callback,
    pedido_direccion_cliente, mostrar_selector_pickup, pedido_pickup_callback,
    mostrar_lista_pickups, pedido_pickup_lista_callback,
    pedido_pickup_nueva_ubicacion_handler, pedido_pickup_nueva_ubicacion_location_handler,
    pedido_pickup_nueva_detalles_handler, pedido_pickup_nueva_ciudad_handler,
    pedido_pickup_nueva_barrio_handler, pickup_nueva_copiar_msg_callback,
    pedido_pickup_geo_callback, pedido_pickup_guardar_callback,
    pedido_nombre_cliente, pedido_telefono_cliente,
    mostrar_pregunta_base, pedido_requiere_base_callback,
    pedido_valor_base_callback, pedido_valor_base_texto,
    mostrar_error_cotizacion, calcular_cotizacion_y_confirmar,
    pedido_retry_quote_callback, pedido_tipo_servicio,
    construir_resumen_pedido, mostrar_resumen_confirmacion,
    mostrar_resumen_confirmacion_msg, pedido_confirmacion,
    pedido_confirmacion_callback, _pedido_incentivo_keyboard,
    pedido_incentivo_fixed_callback, pedido_incentivo_otro_start,
    pedido_incentivo_monto_handler, pedido_incentivo_existing_otro_start,
    pedido_incentivo_existing_monto_handler,
    offer_suggest_inc_fixed_callback, offer_suggest_inc_otro_start,
    offer_suggest_inc_monto_handler,
    route_suggest_inc_fixed_callback,
    admin_nuevo_pedido_start, admin_pedido_pickup_callback,
    admin_pedido_nueva_dir_start, admin_pedido_pickup_text_handler,
    admin_pedido_geo_pickup_callback, admin_pedido_pickup_gps_handler,
    admin_pedido_save_pickup_callback, admin_pedido_cust_name_handler,
    admin_pedido_sel_cust_handler, admin_pedido_cust_selected,
    admin_pedido_addr_selected, admin_pedido_addr_nueva,
    admin_pedido_cust_phone_handler, admin_pedido_cust_addr_handler,
    admin_pedido_cust_gps_handler, admin_pedido_geo_callback,
    admin_pedido_instruc_handler,
    admin_pedido_sin_instruc_callback, admin_pedido_inc_fijo_callback,
    admin_pedido_inc_otro_callback, admin_pedido_inc_monto_handler,
    admin_pedido_confirmar_callback, admin_pedido_cancelar_callback,
    construir_preview_oferta, get_preview_buttons, preview_callback,
    pedido_guardar_cliente_callback,
    _ally_bandeja_guardar_en_agenda, _pedido_pedir_valor_compra,
    pedido_valor_compra_handler, _ally_bandeja_precargar_pedido,
    _ally_bandeja_validar_entrada, _ally_bandeja_validar_ally_y_saldo,
    ally_bandeja_crear_pedido_entry, ally_bandeja_crear_y_guardar_entry,
    pedido_incentivo_menu_callback, pedido_incentivo_existing_fixed_callback,
    nuevo_pedido_conv, pedido_incentivo_conv, offer_suggest_inc_conv,
    route_suggest_inc_conv,
    admin_pedido_conv,
    admin_mis_plantillas_callback,
    admin_ped_tmpl_info_callback,
    admin_ped_tmpl_menu_del_callback, MIN_ADMIN_OPERATING_BALANCE,
)
from handlers.route import (
    nueva_ruta_desde_cotizador,
    nueva_ruta_desde_menu,
    nueva_ruta_start,
    nueva_ruta_conv,
)
from handlers.admin_panel import (
    _registration_reset_status_label,
    _append_registration_reset_button,
    _notify_admin_local_welcome,
    _render_platform_ally_detail,
    _render_reference_candidates,
    cmd_referencias,
    reference_validation_callback,
    reference_assign_location_handler,
    aliados_pendientes,
    repartidores_pendientes,
    admin_menu,
    admin_menu_callback,
    volver_menu_global,
    courier_pick_admin_callback,
    admins_pendientes,
    admin_ver_pendiente,
    admin_aprobar_rechazar_callback,
    pendientes,
    admin_config_callback,
    admin_parking_review,
    admin_parking_review_callback,
    rechazar_conv,
)
from handlers.courier_panel import (
    courier_earnings_start,
    courier_earnings_callback,
)
from handlers.ally_bandeja import (
    ally_bandeja_solicitudes,
    _ALLY_ENLACE_STATUS_LABEL,
    _ally_mi_enlace_build,
    ally_mi_enlace,
    ally_enlace_refresh_callback,
    _ally_bandeja_mostrar_lista,
    _ally_bandeja_mostrar_procesadas,
    _ally_bandeja_mostrar_pedido,
    ally_bandeja_callback,
)

# ============================================================
# SEPARACIÓN DEV/PROD - Evitar conflicto getUpdates
# ============================================================

# Cargar .env SIEMPRE primero
load_dotenv()
ENV = os.getenv("ENV", "PROD").upper()

logging.basicConfig(
    level=logging.DEBUG if ENV == "LOCAL" else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

if ENV == "LOCAL":
    logger.info("Ambiente: %s - .env cargado", ENV)
else:
    logger.info("Ambiente: %s - usando variables de entorno del sistema (Railway/PROD)", ENV)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

# URL base del formulario público de pedidos del aliado.
# Configurar en Railway como variable de entorno FORM_BASE_URL.
# Ejemplo: https://form.domiquerendona.com
FORM_BASE_URL = os.getenv("FORM_BASE_URL", "").rstrip("/")

# URL pública del panel web Angular.
# Railway: https://angular-production-44c8.up.railway.app  → muestra botón inline
# Local:   http://localhost:4200                            → muestra texto con el link
# Telegram solo acepta https:// en botones inline.
WEB_PANEL_URL = os.getenv("WEB_PANEL_URL", "").strip().rstrip("/")
WEB_PANEL_URL_IS_HTTPS = WEB_PANEL_URL.startswith("https://")

PLATFORM_TEAM_CODE = "PLATFORM"


def _build_bot_deep_link(context, payload: str) -> str:
    username = (os.getenv("BOT_USERNAME", "") or "").strip().lstrip("@")
    if not username:
        username = (getattr(context.bot, "username", "") or "").strip().lstrip("@")
    return "https://t.me/{}?start={}".format(username, payload) if username and payload else ""


def start(update, context):
    """Comando /start y /menu: bienvenida con estado del usuario."""
    user_tg = update.effective_user
    start_arg = (context.args[0] if getattr(context, "args", None) else "").strip()

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
        logger.exception("Error en get_admin_by_user_id en /start")
        admin_local = None

    invite_info = resolve_admin_invite_from_start_arg(start_arg) if start_arg else None
    invite_warning = ""
    if start_arg.startswith(ADMIN_INVITE_START_PREFIX):
        if invite_info:
            context.user_data[ADMIN_INVITE_USER_DATA_KEY] = invite_info["token"]
            audit_admin_invite_event(
                invite_info["token"],
                telegram_id=user_tg.id,
                user_id=user_db_id,
                outcome="START_OPENED",
                note="Deep link de invitacion abierto en /start.",
            )
            logger.info(
                "[admin_invite_start] telegram_id=%s admin_id=%s role_scope=%s team_code=%s",
                user_tg.id,
                invite_info["admin_id"],
                invite_info["role_scope"],
                invite_info["team_code"],
            )
            # Notificar al admin local (no al admin de plataforma) que alguien abrio su enlace.
            # Solo una vez por telegram_id cada 24h para evitar spam si la persona abre varias veces.
            admin_tg_id = invite_info.get("admin_telegram_id")
            if admin_tg_id and int(admin_tg_id) != int(ADMIN_USER_ID):
                already_notified = has_recent_invite_open(
                    invite_info["admin_id"], user_tg.id, hours=24
                )
                if not already_notified:
                    role_scope = invite_info.get("role_scope", "")
                    rol_texto = (
                        "aliado o repartidor" if role_scope == "BOTH"
                        else "aliado" if role_scope == "ALLY"
                        else "repartidor"
                    )
                    try:
                        context.bot.send_message(
                            chat_id=admin_tg_id,
                            text=(
                                "Alguien abrio tu enlace de invitacion ({}).\n"
                                "Si completa el registro lo veras en /aliados_pendientes o /repartidores_pendientes.\n"
                                "Usa /mis_invitados para ver el historial."
                            ).format(rol_texto),
                        )
                    except Exception:
                        pass
            # Tokens BOTH muestran pantalla de seleccion de rol
            if invite_info.get("role_scope") == "BOTH":
                update.message.reply_text(
                    f"Bienvenido al equipo {invite_info['team_name']}!\n\n"
                    "Que vas a registrar?",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Soy aliado (negocio)", callback_data="invite_role_ally")],
                        [InlineKeyboardButton("Soy repartidor", callback_data="invite_role_courier")],
                    ])
                )
                return
        else:
            context.user_data.pop(ADMIN_INVITE_USER_DATA_KEY, None)
            logger.info(
                "[admin_invite_start_invalid] telegram_id=%s start_arg=%s",
                user_tg.id,
                start_arg,
            )
            invite_warning = (
                "Invitacion detectada:\n"
                "- Ese enlace ya no esta disponible. Pide al administrador un enlace nuevo.\n\n"
            )

    es_admin_plataforma_flag = es_admin_plataforma(user_tg.id)

    estado_lineas = []
    siguientes_pasos = []

    # Admin Plataforma
    if es_admin_plataforma_flag:
        estado_lineas.append("• Administrador de Plataforma: ACTIVO.")
        siguientes_pasos.append("• Usa /admin para abrir el Panel de Plataforma.")

    # Admin Local
    if admin_local:
        admin_status = admin_local.get("status", "PENDING") if isinstance(admin_local, dict) else admin_local["status"]
        admin_status = admin_status or "PENDING"
        team_name = (admin_local.get("team_name") if isinstance(admin_local, dict) else admin_local["team_name"]) or "-"
        team_code = (admin_local.get("team_code") if isinstance(admin_local, dict) else admin_local["team_code"]) or "-"

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
                motivo_adm = admin_local.get("rejection_reason") if isinstance(admin_local, dict) else (admin_local["rejection_reason"] if admin_local["rejection_reason"] else None)
                if motivo_adm:
                    siguientes_pasos.append(
                        "• Tu registro de administrador fue RECHAZADO.\n"
                        "  Motivo: {}\n"
                        "  Contacta al Administrador de Plataforma si tienes preguntas.".format(motivo_adm)
                    )
                else:
                    siguientes_pasos.append("• Tu registro de administrador fue RECHAZADO. Contacta al Administrador de Plataforma.")
        else:
            # Administrador Local normal: mostrar requisitos
            if admin_status == "PENDING":
                siguientes_pasos.append("• Tu registro de administrador esta pendiente de aprobacion.")
            elif admin_status == "APPROVED":
                siguientes_pasos.append(
                    "• Tu administrador fue APROBADO, pero no podras operar hasta cumplir requisitos (5 aliados y 10 repartidores con saldo minimo, mas saldo master suficiente)."
                )
                siguientes_pasos.append("• Usa /mi_admin para ver requisitos y tu estado operativo.")
            elif admin_status == "INACTIVE":
                siguientes_pasos.append("• Tu cuenta de administrador esta INACTIVA. Contacta al Administrador de Plataforma.")
            elif admin_status == "REJECTED":
                motivo_adm = admin_local.get("rejection_reason") if isinstance(admin_local, dict) else (admin_local["rejection_reason"] if admin_local["rejection_reason"] else None)
                if motivo_adm:
                    siguientes_pasos.append(
                        "• Tu registro de administrador fue RECHAZADO.\n"
                        "  Motivo: {}\n"
                        "  Contacta al Administrador de Plataforma si tienes preguntas.".format(motivo_adm)
                    )
                else:
                    siguientes_pasos.append("• Tu registro de administrador fue RECHAZADO. Contacta al Administrador de Plataforma.")

    # Aliado
    if ally:
        estado_lineas.append(f"• Aliado: {ally['business_name']} (estado: {ally['status']}).")
        if ally["status"] == "APPROVED":
            siguientes_pasos.append("• Puedes crear pedidos con /nuevo_pedido.")
        elif ally["status"] == "REJECTED":
            motivo_ally = ally["rejection_reason"] if ally["rejection_reason"] else None
            if motivo_ally:
                siguientes_pasos.append(
                    "• Tu registro de aliado fue RECHAZADO.\n"
                    "  Motivo: {}\n"
                    "  Contacta al administrador si tienes preguntas.".format(motivo_ally)
                )
            else:
                siguientes_pasos.append("• Tu registro de aliado fue RECHAZADO. Contacta al Administrador de Plataforma.")
        elif ally["status"] == "INACTIVE":
            siguientes_pasos.append("• Tu negocio esta INACTIVO. Contacta al administrador.")
        else:
            siguientes_pasos.append("• Tu negocio aun no esta aprobado. Cuando este APPROVED podras usar /nuevo_pedido.")

    # Repartidor
    if courier:
        codigo = courier["code"] if courier["code"] else "sin codigo"
        estado_lineas.append(f"• Repartidor codigo interno: {codigo} (estado: {courier['status']}).")
        if courier["status"] == "APPROVED":
            siguientes_pasos.append("• Pronto podras activarte y recibir ofertas (ONLINE) desde tu panel de repartidor.")
        elif courier["status"] == "REJECTED":
            motivo_courier = courier["rejection_reason"] if courier["rejection_reason"] else None
            if motivo_courier:
                siguientes_pasos.append(
                    "• Tu registro de repartidor fue RECHAZADO.\n"
                    "  Motivo: {}\n"
                    "  Contacta al administrador si tienes preguntas.".format(motivo_courier)
                )
            else:
                siguientes_pasos.append("• Tu registro de repartidor fue RECHAZADO. Contacta al Administrador de Plataforma.")
        elif courier["status"] == "INACTIVE":
            siguientes_pasos.append("• Tu cuenta de repartidor esta INACTIVA. Contacta al administrador.")
        else:
            siguientes_pasos.append("• Tu registro de repartidor aun esta pendiente de aprobacion.")

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
    invite_text = invite_warning
    if invite_info:
        team_label = "{} ({})".format(invite_info["team_name"], invite_info["team_code"])
        role_label = "aliado" if invite_info["role_scope"] == "ALLY" else "repartidor"
        if invite_info["role_scope"] == "ALLY":
            if ally and ally["status"] in ("PENDING", "APPROVED"):
                invite_action = "- Ya tienes un perfil de aliado existente. El enlace no cambia tu equipo automaticamente."
            else:
                invite_action = "- Usa /soy_aliado para continuar tu registro directo con ese equipo."
        else:
            if courier and courier["status"] in ("PENDING", "APPROVED"):
                invite_action = "- Ya tienes un perfil de repartidor existente. El enlace no cambia tu equipo automaticamente."
            else:
                invite_action = "- Usa /soy_repartidor para continuar tu registro directo con ese equipo."
        invite_text = (
            "Invitacion detectada:\n"
            f"- Equipo: {team_label}\n"
            f"- Registro directo para: {role_label}\n"
            f"{invite_action}\n\n"
        )

    # Construir menú agrupado por rol
    missing_cmds = _get_missing_role_commands(ally, courier, admin_local, es_admin_plataforma_flag)
    comandos = []

    comandos.append("General:")
    comandos.append("• /mi_perfil  - Ver tu perfil consolidado")

    if ally and ally["status"] == "APPROVED" and "/soy_aliado" not in missing_cmds:
        comandos.append("")
        comandos.append("🍕 Aliado:")
        comandos.append("• Toca [Mi aliado] en el menu para ver todas las opciones:")
        comandos.append("  Nuevo pedido, Mis pedidos, Clientes, Agenda,")
        comandos.append("  Cotizar envio, Recargar, Mi saldo")
    elif ally:
        ally_status = ally["status"] or "PENDING"
        comandos.append("")
        comandos.append("Aliado:")
        comandos.append(f"• Tu perfil de aliado está {ally_status}.")
        comandos.append("  Cuando esté APPROVED verás la sección [Mi aliado] en el menu.")
    else:
        comandos.append("")
        comandos.append("Aliado:")
        comandos.append("• /soy_aliado  - Registrarte como aliado")

    if courier and "/soy_repartidor" not in missing_cmds:
        comandos.append("")
        comandos.append("🚴 Repartidor:")
        if courier["status"] == "APPROVED":
            comandos.append("• Toca [Mi repartidor] en el menu para ver todas las opciones:")
            comandos.append("  Activar/Pausar, Mis pedidos, Recargar, Mi saldo")
        else:
            comandos.append("• Tu perfil de repartidor no está APPROVED todavía.")
            comandos.append("  Cuando esté APPROVED verás la sección [Mi repartidor] en el menu.")
    else:
        comandos.append("")
        comandos.append("Repartidor:")
        comandos.append("• /soy_repartidor  - Registrarte como repartidor")

    comandos.append("")
    comandos.append("Administrador:")
    if es_admin_plataforma_flag:
        comandos.append("• /admin  - Panel de administración de plataforma")
        comandos.append("• /tarifas  - Configurar tarifas")
        comandos.append("• /recargas_pendientes  - Ver solicitudes de recarga")
        comandos.append("• /configurar_pagos  - Configurar datos de pago")
        comandos.append("• /ver_enlaces_admin  - Ver enlaces directos de registro")
        comandos.append("• /regenerar_enlaces_admin  - Invalidar y crear enlaces nuevos")
        comandos.append("• /mis_invitados  - Ver registros creados via enlace de invitacion")
    elif admin_local:
        admin_status = admin_local["status"]
        if admin_status == "INACTIVE" and "/soy_admin" in missing_cmds:
            comandos.append("• /soy_admin  - Volver a registrarte como administrador")
        else:
            comandos.append("• /mi_admin  - Ver tu panel de administrador local")
        if admin_status == "APPROVED":
            comandos.append("• /recargas_pendientes  - Ver solicitudes de recarga")
            comandos.append("• /configurar_pagos  - Configurar datos de pago")
            comandos.append("• /ver_enlaces_admin  - Ver enlaces directos de registro")
            comandos.append("• /regenerar_enlaces_admin  - Invalidar y crear enlaces nuevos")
            comandos.append("• /mis_invitados  - Ver registros creados via enlace de invitacion")
    else:
        if "/soy_admin" in missing_cmds:
            comandos.append("• /soy_admin  - Registrarte como administrador")
        else:
            comandos.append("• No tienes opciones de administrador disponibles.")

    mensaje = (
        "🐢 Bienvenido a Domiquerendona 🐢\n\n"
        "Sistema para conectar negocios aliados con repartidores de confianza.\n\n"
        "Tu estado actual:\n"
        f"{estado_text}\n\n"
        "Siguiente paso recomendado:\n"
        f"{siguientes_text}\n\n"
        f"{invite_text}"
        "Menú por secciones:\n"
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
        # Mostrar menú principal con botones de secciones
        reply_markup = get_main_menu_keyboard(missing_cmds, courier, ally, admin_local, es_admin_plataforma_flag)
        update.message.reply_text(mensaje, reply_markup=reply_markup)


def menu(update, context):
    """Alias de /start para mostrar el menú principal."""
    return start(update, context)


def stale_callback_handler(update, context):
    """Catch-all para callbacks huerfanos (bot reiniciado, sesion expirada).
    Se registra al final de todos los handlers para capturar cualquier callback
    que ningun otro handler haya procesado."""
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id if query.message else None
    callback_data = query.data or ""
    silent_order_flow_prefixes = (
        "pedido_",
        "pickup_",
        "preview_",
        "ubicacion_",
        "guardar_dir_cliente_",
    )
    if chat_id:
        if not callback_data.startswith(silent_order_flow_prefixes):
            context.bot.send_message(
                chat_id=chat_id,
                text="Esta accion ya no esta disponible (el bot se reinicio). Usa el menu para continuar."
            )
        show_main_menu(update, context)


def mi_aliado(update, context):
    """Muestra el submenu de gestion de aliado."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally:
        update.message.reply_text("No tienes perfil de aliado. Usa /soy_aliado para registrarte.")
        return
    status = ally["status"]
    business_name = ally["business_name"]
    if status != "APPROVED":
        if status == "PENDING":
            update.message.reply_text(
                "Tu registro de aliado está PENDING.\n\n"
                "Aún no puedes usar el panel de aliado hasta que sea aprobado por plataforma."
            )
        elif status == "INACTIVE":
            update.message.reply_text(
                "Tu perfil de aliado está INACTIVE.\n\n"
                "Si ya tienes autorización para nuevo registro, usa /soy_aliado."
            )
        else:
            update.message.reply_text(
                f"Tu perfil de aliado está {status}.\n\n"
                "Cuando esté APPROVED verás el panel de aliado."
            )
        return
    msg = (
        "🍕 GESTION DE ALIADO\n\n"
        f"Negocio: {business_name}\n"
        f"Estado: {status}\n\n"
        "Selecciona una opcion:"
    )
    reply_markup = get_ally_menu_keyboard()
    update.message.reply_text(msg, reply_markup=reply_markup)


def _ally_couriers_build_panel(ally_id):
    """Construye texto e InlineKeyboardMarkup del panel de repartidores para un aliado.
    Muestra secciones ACTIVOS y BLOQUEADOS separadas.
    Retorna (text, markup) donde markup puede ser None si no hay botones."""
    admin_link = get_approved_admin_link_for_ally(ally_id)
    if not admin_link:
        return "No tienes un administrador aprobado asignado.", None

    admin_id = admin_link["admin_id"]
    couriers = list_courier_links_by_admin(admin_id)
    if not couriers:
        return "Tu equipo no tiene repartidores activos.", None

    blocked_ids = get_blocked_courier_ids_for_ally(ally_id)
    activos = []
    bloqueados = []
    for c in couriers:
        cid = c["courier_id"] if isinstance(c, dict) else c[1]
        name = (c["full_name"] if isinstance(c, dict) else c[2]) or "Sin nombre"
        if cid in blocked_ids:
            bloqueados.append((cid, name))
        else:
            activos.append((cid, name))

    lines = ["Repartidores de tu equipo:\n"]
    keyboard = []

    if activos:
        lines.append("ACTIVOS ({})".format(len(activos)))
        for cid, name in activos:
            lines.append("  {}".format(name))
            keyboard.append([InlineKeyboardButton(
                "Bloquear: {}".format(name),
                callback_data="ally_block_block_{}".format(cid),
            )])

    if bloqueados:
        if activos:
            lines.append("")
        lines.append("BLOQUEADOS ({})".format(len(bloqueados)))
        for cid, name in bloqueados:
            lines.append("  {} (bloqueado)".format(name))
            keyboard.append([InlineKeyboardButton(
                "Desbloquear: {}".format(name),
                callback_data="ally_block_unblock_{}".format(cid),
            )])

    if not activos and not bloqueados:
        return "Tu equipo no tiene repartidores.", None

    markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    return chr(10).join(lines), markup


def ally_couriers_panel(update, context):
    """Muestra repartidores del equipo con secciones ACTIVOS y BLOQUEADOS."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally or ally["status"] != "APPROVED":
        update.message.reply_text("Solo aliados aprobados pueden gestionar repartidores.")
        return

    text, markup = _ally_couriers_build_panel(ally["id"])
    update.message.reply_text(text, reply_markup=markup)


def ally_block_callback(update, context):
    """Maneja bloqueo/desbloqueo de repartidor por aliado y actualiza el panel."""
    query = update.callback_query
    query.answer()
    data = query.data

    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.edit_message_text("Usuario no encontrado.")
        return

    ally = get_ally_by_user_id(user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("Solo aliados aprobados pueden gestionar repartidores.")
        return

    ally_id = ally["id"]
    if data.startswith("ally_block_block_"):
        courier_id = int(data.split("_")[-1])
        block_courier_for_ally(ally_id, courier_id)
    elif data.startswith("ally_block_unblock_"):
        courier_id = int(data.split("_")[-1])
        unblock_courier_for_ally(ally_id, courier_id)
    else:
        return

    # Regenerar panel actualizado en el mismo mensaje
    text, markup = _ally_couriers_build_panel(ally_id)
    try:
        query.edit_message_text(text, reply_markup=markup)
    except Exception:
        pass


def mi_repartidor(update, context):
    """Muestra el submenu de gestion de repartidor."""
    user_db_id = get_user_db_id_from_update(update)
    courier = get_courier_by_user_id(user_db_id)
    if not courier:
        update.message.reply_text("No tienes perfil de repartidor. Usa /soy_repartidor para registrarte.")
        return
    status = _row_value(courier, "status", "PENDING")
    full_name = _row_value(courier, "full_name", "-")
    is_active = _row_value(courier, "is_active", 0)
    available_cash = int(_row_value(courier, "available_cash", 0) or 0)
    if is_active and status == "APPROVED":
        avail_status = _row_value(courier, "availability_status", "INACTIVE")
        live_active = int(_row_value(courier, "live_location_active", 0) or 0) == 1
        if avail_status == "APPROVED" and live_active:
            disp = "ONLINE"
        elif avail_status == "APPROVED":
            disp = "PAUSADO"
        else:
            disp = "OFFLINE"
    else:
        disp = "OFFLINE"
    disp_line = f"Disponibilidad: {disp}"
    if disp == "ONLINE":
        disp_line += f" (base ${available_cash:,})"
    msg = (
        "🚴 GESTION DE REPARTIDOR\n\n"
        f"Nombre: {full_name}\n"
        f"Estado: {status}\n"
        f"{disp_line}\n\n"
        "Selecciona una opcion:"
    )
    reply_markup = get_repartidor_menu_keyboard(courier)
    active_orders = get_active_orders_for_courier(courier["id"])
    active_route = get_active_route_for_courier(courier["id"])
    has_active_service = bool(active_orders) or (active_route and active_route["status"] == "ACCEPTED")

    if has_active_service:
        gps_active = (
            int(_row_value(courier, "live_location_active", 0) or 0) == 1
            and _row_value(courier, "live_lat") is not None
        )
        if not gps_active:
            update.message.reply_text(
                "Tu ubicacion GPS no esta activa y tienes un servicio en curso.\n\n"
                "Debes activar tu ubicacion en vivo para poder usar tus funciones de repartidor:\n"
                "1. Abre el chat con el bot.\n"
                "2. Toca el clip (adjuntar).\n"
                "3. Selecciona \"Ubicacion\".\n"
                "4. Elige \"Compartir ubicacion en vivo\"."
            )

    if active_orders:
        status_labels = {"ACCEPTED": "asignado", "PICKED_UP": "en camino al cliente"}
        if len(active_orders) == 1:
            ao = active_orders[0]
            label = status_labels.get(_row_value(ao, "status"), _row_value(ao, "status"))
            update.message.reply_text(
                "Tienes un pedido en curso (#{}  {}).\n"
                "Presiona \"Pedidos en curso\" para gestionarlo.".format(
                    _row_value(ao, "id"), label
                )
            )
        else:
            lines = []
            for ao in active_orders:
                label = status_labels.get(_row_value(ao, "status"), _row_value(ao, "status"))
                lines.append("#{} — {}".format(_row_value(ao, "id"), label))
            update.message.reply_text(
                "Tienes {} pedidos activos:\n{}\n\n"
                "Presiona \"Pedidos en curso\" para gestionarlos.".format(
                    len(active_orders), "\n".join(lines)
                )
            )
    update.message.reply_text(msg, reply_markup=reply_markup)
    if WEB_PANEL_URL and WEB_PANEL_URL_IS_HTTPS:
        update.message.reply_text(
            "Tambien puedes ver tus ganancias y perfil en el panel web:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🌐 Mi panel web", url=WEB_PANEL_URL + "/courier")
            ]])
        )
    elif WEB_PANEL_URL:
        update.message.reply_text(
            "Tambien puedes ver tus ganancias y perfil en el panel web:\n"
            + WEB_PANEL_URL + "/courier"
        )


def courier_orders_history(update, context):
    """Muestra pedidos del repartidor (activos e historial reciente)."""
    user_db_id = get_user_db_id_from_update(update)
    courier = get_courier_by_user_id(user_db_id)
    if not courier:
        update.message.reply_text("No tienes perfil de repartidor.")
        return

    orders = get_orders_by_courier(courier["id"], limit=20)
    if not orders:
        update.message.reply_text("No tienes pedidos registrados.")
        return

    status_labels = {
        "PENDING": "Pendiente",
        "PUBLISHED": "Buscando repartidor",
        "ACCEPTED": "Asignado",
        "PICKED_UP": "En camino",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }

    active_orders = [o for o in orders if _row_value(o, "status") not in ("DELIVERED", "CANCELLED")]
    history_orders = [o for o in orders if _row_value(o, "status") in ("DELIVERED", "CANCELLED")]

    if active_orders:
        update.message.reply_text("Tus pedidos activos:")
        for order in active_orders:
            status = status_labels.get(_row_value(order, "status"), _row_value(order, "status", "-"))
            msg = (
                "Pedido #{}\n"
                "Estado: {}\n"
                "Cliente: {}\n"
                "Dirección: {}"
            ).format(
                _row_value(order, "id", "-"),
                status,
                _row_value(order, "customer_name", "N/A") or "N/A",
                _row_value(order, "customer_address", "N/A") or "N/A",
            )
            update.message.reply_text(msg)
    else:
        update.message.reply_text("No tienes pedidos activos.")

    if history_orders:
        update.message.reply_text("Tu historial reciente:")
        for order in history_orders[:10]:
            status = status_labels.get(_row_value(order, "status"), _row_value(order, "status", "-"))
            event_at = "-"
            if _row_value(order, "status") == "DELIVERED":
                event_at = _row_value(order, "delivered_at", "-") or "-"
            elif _row_value(order, "status") == "CANCELLED":
                event_at = _row_value(order, "canceled_at", "-") or "-"

            msg = (
                "Pedido #{}\n"
                "Estado: {}\n"
                "Fecha: {}\n"
                "Cliente: {}\n"
                "Dirección: {}"
            ).format(
                _row_value(order, "id", "-"),
                status,
                event_at,
                _row_value(order, "customer_name", "N/A") or "N/A",
                _row_value(order, "customer_address", "N/A") or "N/A",
            )
            update.message.reply_text(msg)


def courier_pedidos_en_curso(update, context):
    """Muestra el estado de los trabajos activos asignados al repartidor."""
    user_db_id = get_user_db_id_from_update(update)
    courier = get_courier_by_user_id(user_db_id)
    if not courier:
        update.message.reply_text("No tienes perfil de repartidor.")
        return

    active_orders = get_active_orders_for_courier(courier["id"])
    active_route = get_active_route_for_courier(courier["id"])

    if not active_orders and not active_route:
        update.message.reply_text("No tienes pedidos en curso.")
        return

    order_status_labels = {
        "ACCEPTED": "Asignado",
        "PICKED_UP": "En camino",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }
    route_status_labels = {
        "ACCEPTED": "En curso",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }

    total_activos = len(active_orders) + (1 if active_route else 0)
    if total_activos > 1:
        update.message.reply_text(
            "Tienes {} servicios activos:".format(total_activos)
        )
    else:
        update.message.reply_text("Pedidos en curso:")

    for idx, active_order in enumerate(active_orders):
        order_id = _row_value(active_order, "id", "-")
        st = order_status_labels.get(
            _row_value(active_order, "status"),
            _row_value(active_order, "status", "-"),
        )
        order_status = _row_value(active_order, "status")
        order_stage_line = get_courier_active_order_stage_line(active_order)
        pickup_address = _get_order_visible_pickup_line(active_order) or "Ubicacion pendiente de detallar"
        destino_area = _get_order_visible_dropoff_line(active_order) or "Ubicacion pendiente de detallar"
        total_fee = int((_row_value(active_order, "total_fee") or 0) or 0)

        header = "[{}/{}] ".format(idx + 1, len(active_orders)) if len(active_orders) > 1 else ""
        msg = (
            "{}Pedido #{}\n"
            "Estado: {}\n"
            "Recoge en: {}\n"
            "Destino: {}\n"
            "Tarifa: ${:,}"
        ).format(header, order_id, st, pickup_address, destino_area, total_fee)

        kb = []
        if order_status == "ACCEPTED":
            if order_stage_line:
                msg += "\n{}".format(order_stage_line)
            kb.append([
                InlineKeyboardButton(
                    "Confirmar llegada al pickup",
                    callback_data="order_pickup_{}".format(order_id),
                ),
            ])
            kb.append([
                InlineKeyboardButton(
                    "Liberar pedido",
                    callback_data="order_release_{}".format(order_id),
                ),
            ])
        elif order_status == "PICKED_UP":
            kb.append([
                InlineKeyboardButton(
                    "Finalizar pedido",
                    callback_data="order_delivered_confirm_{}".format(order_id),
                ),
            ])
            dropoff_lat = _row_value(active_order, "dropoff_lat")
            dropoff_lng = _row_value(active_order, "dropoff_lng")
            customer_name = _row_value(active_order, "customer_name") or "Sin nombre"
            customer_phone = _row_value(active_order, "customer_phone") or "Sin telefono"
            customer_address = _get_order_visible_dropoff_line(active_order) or "Sin direccion legible"
            msg += (
                "\n\nENTREGA:\n"
                "Cliente: {}\n"
                "Telefono: {}\n"
                "Direccion: {}"
            ).format(customer_name, customer_phone, customer_address)
            if dropoff_lat and dropoff_lng:
                dest = "{},{}".format(float(dropoff_lat), float(dropoff_lng))
                kb.append([InlineKeyboardButton(
                    "Abrir en Google Maps",
                    url="https://www.google.com/maps/dir/?api=1&destination={}&travelmode=driving".format(dest)
                )])
                kb.append([InlineKeyboardButton(
                    "Abrir en Waze",
                    url="https://waze.com/ul?ll={}&navigate=yes".format(dest)
                )])
        update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

    if active_route:
        route_id = _row_value(active_route, "id", "-")
        st = route_status_labels.get(
            _row_value(active_route, "status"),
            _row_value(active_route, "status", "-"),
        )
        route_status = _row_value(active_route, "status")
        pickup_address = _get_route_visible_pickup_line(active_route) or "Ubicacion pendiente de detallar"
        total_fee = int((_row_value(active_route, "total_fee") or 0) or 0)

        pending_stops = get_pending_route_stops(int(route_id)) if route_id != "-" else []
        next_seq = None
        next_stop = None
        if pending_stops:
            try:
                next_stop = min(pending_stops, key=lambda s: int(s["sequence"]) if s["sequence"] is not None else 9999)
                next_seq = int(next_stop["sequence"]) if next_stop else None
            except Exception:
                next_seq = None

        total_stops = len(get_route_destinations(int(route_id))) if route_id != "-" else 0
        completed_stops = total_stops - len(pending_stops)

        msg = (
            "Ruta #{}\n"
            "Estado: {}\n"
            "Recoge en: {}\n"
            "Pago: ${:,}\n"
            "Paradas: {}/{} completadas"
        ).format(route_id, st, pickup_address, total_fee, completed_stops, total_stops)

        if next_stop:
            stop_name = _row_value(next_stop, "customer_name") or "Sin nombre"
            stop_phone = _row_value(next_stop, "customer_phone") or "Sin telefono"
            stop_addr = _get_route_stop_visible_line(next_stop) or "Ubicacion pendiente de detallar"
            msg += (
                "\n\nSIGUIENTE PARADA (#{}):\n"
                "Cliente: {}\n"
                "Telefono: {}\n"
                "Direccion: {}"
            ).format(next_seq, stop_name, stop_phone, stop_addr)

        if len(pending_stops) > 1:
            msg += "\n\nPROXIMAS PARADAS:"
            for s in pending_stops[1:]:
                s_seq = _row_value(s, "sequence", "?")
                s_addr = _get_route_stop_visible_line(s) or "Ubicacion pendiente de detallar"
                msg += "\n{}. {}".format(s_seq, s_addr)

        kb = []
        if next_stop:
            drop_lat = _row_value(next_stop, "dropoff_lat")
            drop_lng = _row_value(next_stop, "dropoff_lng")
            if drop_lat and drop_lng:
                dest = "{},{}".format(float(drop_lat), float(drop_lng))
                kb.append([InlineKeyboardButton(
                    "Google Maps - Parada {}".format(next_seq),
                    url="https://www.google.com/maps/dir/?api=1&destination={}&travelmode=driving".format(dest)
                )])
                kb.append([InlineKeyboardButton(
                    "Waze - Parada {}".format(next_seq),
                    url="https://waze.com/ul?ll={}&navigate=yes".format(dest)
                )])
            kb.append([
                InlineKeyboardButton(
                    "Confirmar entrega parada {}".format(next_seq),
                    callback_data="ruta_entregar_{}_{}".format(route_id, next_seq),
                )
            ])
        if route_status == "ACCEPTED":
            kb.append([
                InlineKeyboardButton(
                    "Liberar ruta",
                    callback_data="ruta_liberar_{}".format(route_id),
                )
            ])
        update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb) if kb else None)

def cmd_id(update, context):
    """Muestra el user_id de Telegram del usuario."""
    user = update.effective_user
    update.message.reply_text(f"Tu user_id es: {user.id}")


def menu_button_handler(update, context):
    """Maneja los botones del menú principal y submenús (ReplyKeyboard)."""
    text = update.message.text.strip()

    # --- Botones del menú principal ---
    if text == "Mi aliado":
        return mi_aliado(update, context)
    elif text.startswith("Mi repartidor"):
        return mi_repartidor(update, context)
    elif text == "Mi admin":
        return mi_admin(update, context)
    elif text == "Admin plataforma":
        return admin_menu(update, context)
    elif text == "Mi perfil":
        return mi_perfil(update, context)
    elif text == "Ayuda":
        ally, courier, admin_local = _get_user_roles(update)
        missing_cmds = _get_missing_role_commands(ally, courier, admin_local)
        msg = (
            "AYUDA\n\n"
            "Secciones del menu:\n"
            "• Mi aliado - Gestion de tu negocio (pedidos, clientes, agenda, cotizar, recargar, saldo)\n"
            "• Mi repartidor - Gestion de repartidor (activar/pausar, pedidos, recargar, saldo)\n\n"
            "• Mi admin - Panel de administrador local (equipo, pendientes, recargas, configuraciones)\n\n"
            "• Admin plataforma - Panel de administracion de plataforma\n\n"
            "Comandos disponibles:\n"
            "/nuevo_pedido - Crear un nuevo pedido\n"
            "/clientes - Gestionar clientes\n"
            "/cotizar - Cotizar envio por distancia\n"
            "/recargar - Solicitar recarga\n"
            "/saldo - Ver tu saldo\n"
            "/mi_perfil - Ver tu perfil\n"
            "/mi_admin - Panel de administrador\n"
            "/cancel - Cancelar proceso actual\n"
            "/menu - Ver menu principal"
        )
        if missing_cmds:
            msg += "\n\nREGISTRO:\n"
            if "/soy_aliado" in missing_cmds:
                msg += "/soy_aliado - Registrar mi negocio\n"
            if "/soy_repartidor" in missing_cmds:
                msg += "/soy_repartidor - Registrarme como repartidor\n"
            if "/soy_admin" in missing_cmds:
                msg += "/soy_admin - Registrarme como administrador"
        ayuda_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("Solicitar unirme a un equipo", callback_data="solequipo_start")
        ]])
        update.message.reply_text(msg, reply_markup=ayuda_markup)
        return
    elif text == "Menu":
        return start(update, context)
    elif text == "Actualizar menu":
        return show_main_menu(update, context, "Menu actualizado. Selecciona una opcion:")

    # --- Botones del submenú Aliado ---
    elif text == "Mis pedidos":
        return ally_active_orders(update, context)
    elif text == "Mis repartidores":
        return ally_couriers_panel(update, context)
    elif text == "Mi saldo aliado":
        return cmd_saldo(update, context)
    elif text == "Mis solicitudes":
        return ally_bandeja_solicitudes(update, context)
    elif text == "Mi enlace de pedidos":
        return ally_mi_enlace(update, context)
    elif text == "Mi suscripcion":
        update.message.reply_text(
            "Cargando tu suscripcion...",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Ver mi suscripcion", callback_data="ally_mi_suscripcion")
            ]])
        )
        return

    # --- Botones del submenú Repartidor ---
    elif text == "Activar repartidor":
        return courier_activate_from_message(update, context)
    elif text == "Desactivarme":
        return courier_deactivate_from_message(update, context)
    elif text == "Actualizar":
        return mi_repartidor(update, context)
    elif text == "Pedidos en curso":
        return courier_pedidos_en_curso(update, context)
    elif text == "Mis pedidos repartidor":
        return courier_orders_history(update, context)
    elif text == "Mis ganancias":
        return courier_earnings_start(update, context)
    elif text == "Mi saldo repartidor":
        return cmd_saldo(update, context)

    # --- Botón compartido ---
    elif text == "Volver al menu":
        return show_main_menu(update, context, "Menu principal. Selecciona una opcion:")


def saludo_menu_handler(update, context):
    """Muestra menu principal cuando el usuario saluda fuera de comandos."""
    show_main_menu(update, context, "Hola. Te muestro el menu principal:")

# Conversación para gestión de ubicaciones del aliado ("Mis ubicaciones")
def mi_admin(update, context):
    user_db_id = get_user_db_id_from_update(update)

    # Validar que sea admin local registrado
    admin = None
    admin = get_admin_by_user_id(user_db_id)
 
    if not admin:
        update.message.reply_text("No tienes perfil de Administrador Local registrado.")
        return

    admin_id = admin["id"]

    # Traer detalle completo (incluye team_code)
    admin_full = get_admin_by_id(admin_id)
    if not admin_full:
        update.message.reply_text("No se pudo cargar tu perfil de administrador. Revisa BD.")
        return

    status = admin_full["status"] or "-"
    team_name = admin_full["team_name"] or "-"
    team_code = admin_full["team_code"] or "-"

    header = (
        "Panel Administrador Local\n\n"
        f"Estado: {status}\n"
        f"Equipo: {team_name}\n"
        f"Código de equipo: {team_code}\n"
        "Usa /ver_enlaces_admin para ver tus enlaces directos de registro.\n"
        "Usa /regenerar_enlaces_admin para invalidar los actuales y crear otros.\n"
        "Tu código de equipo sigue disponible como respaldo.\n\n"
    )

    # Administrador de Plataforma: siempre operativo
    if team_code == "PLATFORM":
        keyboard = [
            [InlineKeyboardButton("⏳ Repartidores pendientes", callback_data=f"local_couriers_pending_{admin_id}")],
            [InlineKeyboardButton("⏳ Aliados pendientes", callback_data=f"local_allies_pending_{admin_id}")],
            [InlineKeyboardButton("👥 Mi equipo", callback_data=f"local_my_team_{admin_id}")],
            [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos_local_{}".format(admin_id))],
            [InlineKeyboardButton("📋 Nuevo pedido especial", callback_data="admin_nuevo_pedido_{}".format(admin_id))],
            [InlineKeyboardButton("📜 Mis pedidos especiales", callback_data="adminhist_periodo_hoy_{}".format(admin_id))],
            [InlineKeyboardButton("👤 Mis clientes", callback_data="admin_mis_clientes_{}".format(admin_id))],
            [InlineKeyboardButton("📍 Mis direcciones", callback_data="admin_mis_dirs_{}".format(admin_id))],
            [InlineKeyboardButton("🗂 Mis plantillas", callback_data="admin_mis_plantillas_{}".format(admin_id))],
            [InlineKeyboardButton("💳 Recargas pendientes", callback_data=f"local_recargas_pending_{admin_id}")],
            [InlineKeyboardButton("💰 Mi saldo", callback_data="admin_mi_saldo_{}".format(admin_id)), InlineKeyboardButton("📊 Mis movimientos", callback_data="admin_movimientos_{}".format(admin_id))],
            [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            [InlineKeyboardButton("Soportes pendientes", callback_data="admin_support_open")],
            [InlineKeyboardButton("📝 Solicitudes de cambio", callback_data="admin_change_requests")],
            [InlineKeyboardButton("🅿️ Puntos difícil parqueo", callback_data="parking_review_list")],
        ]
        saldo_alerta = ""
        saldo_sociedad = get_sociedad_balance()
        if admin_full["balance"] < MIN_ADMIN_OPERATING_BALANCE and saldo_sociedad > 0:
            saldo_alerta = (
                "\nATENCION: Tu saldo personal esta por debajo de ${:,}, "
                "pero Sociedad tiene fondos disponibles.\n"
                "Si vas a crear un pedido especial, primero retira saldo desde Sociedad.\n"
            ).format(MIN_ADMIN_OPERATING_BALANCE)
            keyboard.insert(9, [InlineKeyboardButton("Retirar de Sociedad a mi saldo", callback_data="admin_sociedad_retiro_{}".format(admin_id))])
        if WEB_PANEL_URL and WEB_PANEL_URL_IS_HTTPS:
            keyboard.append([InlineKeyboardButton("🌐 Abrir panel web", url=WEB_PANEL_URL)])
        update.message.reply_text(
            header +
            "Como Administrador de Plataforma, tu operación está habilitada.\n"
            + saldo_alerta +
            "Selecciona una opción:"
            + ("\n\nPanel web: " + WEB_PANEL_URL if WEB_PANEL_URL and not WEB_PANEL_URL_IS_HTTPS else ""),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # FASE 1: Mostrar estado del equipo como información, NO como bloqueo
    ok, msg, stats = admin_puede_operar(admin_id)

    # Construir mensaje de estado
    total_couriers = stats.get("total_couriers", 0)
    couriers_ok = stats.get("couriers_ok", 0)
    total_allies = stats.get("total_allies", 0)
    allies_ok = stats.get("allies_ok", 0)
    admin_bal = stats.get("admin_balance", 0)

    estado_msg = (
        "📊 Estado del equipo:\n"
        "• Aliados vinculados: {} (con saldo >= $5,000: {})\n"
        "• Repartidores vinculados: {} (con saldo >= $5,000: {})\n"
        "• Tu saldo master: ${:,}\n\n"
        "Requisitos para operar:\n"
        "• 5 aliados con saldo >= $5,000: {}\n"
        "• 10 repartidores con saldo >= $5,000: {}\n"
        "• Saldo master >= $60,000: {}\n\n"
    ).format(
        total_allies, allies_ok,
        total_couriers, couriers_ok,
        admin_bal,
        "OK" if allies_ok >= 5 else "Faltan {}".format(5 - allies_ok),
        "OK" if couriers_ok >= 10 else "Faltan {}".format(10 - couriers_ok),
        "OK" if admin_bal >= 60000 else "Faltan ${:,}".format(60000 - admin_bal),
    )
    # En FASE 1: panel siempre habilitado
    keyboard = [
        [InlineKeyboardButton("⏳ Repartidores pendientes", callback_data=f"local_couriers_pending_{admin_id}")],
        [InlineKeyboardButton("⏳ Aliados pendientes", callback_data=f"local_allies_pending_{admin_id}")],
        [InlineKeyboardButton("👥 Mi equipo", callback_data=f"local_my_team_{admin_id}")],
        [InlineKeyboardButton("📦 Pedidos de mi equipo", callback_data="admin_pedidos_local_{}".format(admin_id))],
        [InlineKeyboardButton("📋 Nuevo pedido especial", callback_data="admin_nuevo_pedido_{}".format(admin_id))],
        [InlineKeyboardButton("📜 Mis pedidos especiales", callback_data="adminhist_periodo_hoy_{}".format(admin_id))],
        [InlineKeyboardButton("👤 Mis clientes", callback_data="admin_mis_clientes_{}".format(admin_id))],
        [InlineKeyboardButton("📍 Mis direcciones", callback_data="admin_mis_dirs_{}".format(admin_id))],
        [InlineKeyboardButton("🗂 Mis plantillas", callback_data="admin_mis_plantillas_{}".format(admin_id))],
        [InlineKeyboardButton("💳 Recargas pendientes", callback_data=f"local_recargas_pending_{admin_id}")],
        [InlineKeyboardButton("💰 Mi saldo", callback_data="admin_mi_saldo_{}".format(admin_id)), InlineKeyboardButton("📊 Mis movimientos", callback_data="admin_movimientos_{}".format(admin_id))],
        [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
        [InlineKeyboardButton("🔍 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
        [InlineKeyboardButton("Soportes pendientes", callback_data="admin_support_open")],
        [InlineKeyboardButton("📝 Solicitudes de cambio", callback_data="admin_change_requests")],
        [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
        [InlineKeyboardButton("🅿️ Puntos difícil parqueo", callback_data="parking_review_list")],
    ]
    if WEB_PANEL_URL and WEB_PANEL_URL_IS_HTTPS:
        keyboard.append([InlineKeyboardButton("🌐 Abrir panel web", url=WEB_PANEL_URL)])
    update.message.reply_text(
        header + estado_msg +
        "Panel de administración habilitado.\n"
        "Selecciona una opción:"
        + ("\n\nPanel web: " + WEB_PANEL_URL if WEB_PANEL_URL and not WEB_PANEL_URL_IS_HTTPS else ""),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def _send_admin_registration_links(update, context, regenerate: bool = False, alias_used: bool = False):
    result = get_admin_registration_invites(update.effective_user.id, regenerate=regenerate)
    if not result.get("ok"):
        update.message.reply_text(result.get("message") or "No se pudieron generar tus enlaces.")
        return

    ally_url = _build_bot_deep_link(context, f"{ADMIN_INVITE_START_PREFIX}{result['ally_token']}")
    courier_url = _build_bot_deep_link(context, f"{ADMIN_INVITE_START_PREFIX}{result['courier_token']}")
    both_url = _build_bot_deep_link(context, f"{ADMIN_INVITE_START_PREFIX}{result['both_token']}")

    if not ally_url or not courier_url or not both_url:
        update.message.reply_text(
            "No pude construir la URL pública del bot en este momento.\n"
            "Intenta de nuevo más tarde."
        )
        return

    mode = result.get("mode")
    if regenerate:
        intro = (
            "Regeneré nuevos enlaces directos de registro.\n"
            "Los enlaces anteriores quedaron invalidados.\n\n"
        )
    elif mode == "created":
        intro = "Creé nuevos enlaces directos de registro porque no había enlaces activos.\n\n"
    else:
        intro = "Estos son tus enlaces directos de registro activos.\n\n"

    alias_note = ""
    if alias_used and not regenerate:
        alias_note = (
            "Este comando ahora muestra tus enlaces activos.\n"
            "Si quieres invalidarlos y crear otros, usa /regenerar_enlaces_admin.\n\n"
        )

    update.message.reply_text(
        intro
        + alias_note
        + f"Equipo: {result['team_name']} ({result['team_code']})\n\n"
        + f"Enlace combinado (vence: {result['both_expires_text']}):\n"
        + f"{both_url}\n\n"
        + f"Enlace solo para aliados (vence: {result['ally_expires_text']}):\n"
        + f"{ally_url}\n\n"
        + f"Enlace solo para repartidores (vence: {result['courier_expires_text']}):\n"
        + f"{courier_url}\n\n"
        + f"Vigencia configurada: {result['hours_valid']} horas.\n"
        + "El enlace combinado pregunta el rol al abrirlo."
    )


def ver_enlaces_admin(update, context):
    _send_admin_registration_links(update, context, regenerate=False)


def regenerar_enlaces_admin(update, context):
    """Muestra botones para elegir qué enlace(s) regenerar."""
    admin = get_admin_by_telegram_id(update.effective_user.id)
    if not admin or admin["status"] != "APPROVED":
        update.message.reply_text("Este comando es solo para administradores aprobados.")
        return
    update.message.reply_text(
        "Que enlace quieres regenerar?\n"
        "El enlace anterior de ese tipo quedara invalidado.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Enlace combinado (aliados + repartidores)", callback_data="regen_invite_BOTH")],
            [InlineKeyboardButton("Solo aliados", callback_data="regen_invite_ALLY")],
            [InlineKeyboardButton("Solo repartidores", callback_data="regen_invite_COURIER")],
            [InlineKeyboardButton("Los tres a la vez", callback_data="regen_invite_ALL")],
        ])
    )


def generar_enlaces_admin(update, context):
    _send_admin_registration_links(update, context, regenerate=False, alias_used=True)


def mis_invitados(update, context):
    """Muestra los registros y stats de conversion de los enlaces de invitacion del admin."""
    admin = get_admin_by_telegram_id(update.effective_user.id)
    if not admin or admin["status"] != "APPROVED":
        update.message.reply_text("Este comando es solo para administradores aprobados.")
        return
    rows, total_opens = get_admin_invite_registrations(admin["id"])
    total_reg = len(rows)
    conversion = f"{total_reg}/{total_opens}" if total_opens else str(total_reg)
    pct = f" ({round(total_reg * 100 / total_opens)}%)" if total_opens else ""
    STATUS_LABELS = {
        "PENDING": "Pendiente",
        "APPROVED": "Aprobado",
        "INACTIVE": "Inactivo",
        "REJECTED": "Rechazado",
    }
    lineas = [
        "Registros via enlace de invitacion:",
        f"Abrieron el enlace: {total_opens}",
        f"Completaron registro: {conversion}{pct}\n",
    ]
    if not rows:
        lineas.append("Nadie ha completado el registro aun.")
    else:
        for row in rows:
            outcome = (_row_value(row, "outcome", 0) or "").upper()
            created_at = str(_row_value(row, "created_at", 3) or "")[:10]
            if outcome == "ALLY_PENDING_CREATED":
                nombre = _row_value(row, "ally_name", 4) or "—"
                status = _row_value(row, "ally_status", 5) or "PENDING"
                rol = "Aliado"
            else:
                nombre = _row_value(row, "courier_name", 6) or "—"
                status = _row_value(row, "courier_status", 7) or "PENDING"
                rol = "Repartidor"
            estado = STATUS_LABELS.get(status, status)
            lineas.append(f"• {nombre} ({rol}) — {estado} — {created_at}")
    update.message.reply_text("\n".join(lineas))


def regen_invite_callback(update, context):
    """Ejecuta la regeneracion del tipo de enlace elegido por el admin."""
    query = update.callback_query
    query.answer()
    data = (query.data or "").strip()
    role_key = data.replace("regen_invite_", "")

    roles_map = {
        "ALLY": ["ALLY"],
        "COURIER": ["COURIER"],
        "BOTH": ["BOTH"],
        "ALL": ["ALLY", "COURIER", "BOTH"],
    }
    roles = roles_map.get(role_key)
    if not roles:
        query.edit_message_text("Opcion no reconocida.")
        return

    result = regenerate_admin_invite_by_role(update.effective_user.id, roles)
    if not result.get("ok"):
        query.edit_message_text(result.get("message") or "Error al regenerar el enlace.")
        return

    lineas = [
        f"Enlace(s) regenerados para equipo {result['team_name']} ({result['team_code']}).\n"
        "Los anteriores quedaron invalidados.\n"
    ]
    prefix = ADMIN_INVITE_START_PREFIX

    def make_url(token):
        return _build_bot_deep_link(context, f"{prefix}{token}")

    if "both_token" in result:
        lineas.append(
            f"Enlace combinado (vence: {result['both_expires_text']}):\n{make_url(result['both_token'])}"
        )
    if "ally_token" in result:
        lineas.append(
            f"Enlace aliados (vence: {result['ally_expires_text']}):\n{make_url(result['ally_token'])}"
        )
    if "courier_token" in result:
        lineas.append(
            f"Enlace repartidores (vence: {result['courier_expires_text']}):\n{make_url(result['courier_token'])}"
        )
    query.edit_message_text("\n\n".join(lineas))




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
        admin_balance = get_admin_balance(admin_id)
        if team_code == "PLATFORM":
            saldo_sociedad = get_sociedad_balance()
            mensaje += f"   Saldo personal (ganancias): ${admin_balance:,}\n"
            mensaje += f"   Saldo Sociedad (fondos operativos): ${saldo_sociedad:,}\n\n"
        else:
            mensaje += f"   Saldo personal: ${admin_balance:,}\n\n"

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
        ally_links = get_all_approved_links_for_ally(ally_id)
        if ally_links:
            for alink in ally_links:
                alink_team = alink["team_name"] or "-"
                alink_code = alink["team_code"] or ""
                alink_balance = alink["balance"] if alink["balance"] else 0
                if alink_code == "PLATFORM":
                    alink_label = "Plataforma"
                else:
                    alink_label = alink_team
                mensaje += f"   Saldo ({alink_label}): ${alink_balance:,}\n"
            mensaje += "\n"

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
        courier_links = get_all_approved_links_for_courier(courier_id)
        if courier_links:
            for clink in courier_links:
                clink_team = clink["team_name"] or "-"
                clink_code = clink["team_code"] or ""
                clink_balance = clink["balance"] if clink["balance"] else 0
                if clink_code == "PLATFORM":
                    clink_label = "Plataforma"
                else:
                    clink_label = clink_team
                mensaje += f"   Saldo ({clink_label}): ${clink_balance:,}\n"
            mensaje += "\n"

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

        # Mostrar estado de disponibilidad (live location)
        courier_is_active = courier["is_active"] if "is_active" in courier.keys() else 0
        if courier_is_active and courier_status == "APPROVED":
            avail_status = _row_value(courier, "availability_status", "INACTIVE")
            live_active = int(_row_value(courier, "live_location_active", 0) or 0) == 1
            if avail_status == "APPROVED" and live_active:
                avail = "ONLINE"
            elif avail_status == "APPROVED":
                avail = "PAUSADO"
            else:
                avail = "OFFLINE"
            mensaje += f"   Disponibilidad: {avail}\n"
            if avail == "ONLINE":
                avail_cash = int(_row_value(courier, "available_cash", 0) or 0)
                mensaje += f"   (Compartiendo ubicacion en vivo)\n"
                mensaje += f"   Base declarada: ${avail_cash:,}\n"
            elif avail == "PAUSADO":
                mensaje += "   (Ubicacion en vivo detenida - comparte para volver a ONLINE)\n"
            else:
                mensaje += "   (Comparte tu ubicacion en vivo para estar ONLINE)\n"

    mensaje += "\n"

    # ===== ACCIONES RÁPIDAS =====
    mensaje += "⚡ ACCIONES RÁPIDAS\n\n"
    mensaje += "• /menu - Ver menú principal\n"

    if admin:
        mensaje += "• /mi_admin - Panel de administrador\n"

    if ally and status == "APPROVED":
        mensaje += "• /nuevo_pedido - Crear pedido\n"

    if admin or ally or courier:
        keyboard = [[InlineKeyboardButton("Solicitar cambio", callback_data="perfil_change_start")]]
        if courier:
            courier_buttons = []
            courier_is_active = courier["is_active"] if "is_active" in courier.keys() else 0
            if courier_is_active:
                courier_buttons.append([InlineKeyboardButton(
                    "Desactivarme",
                    callback_data="courier_deactivate",
                )])
            else:
                courier_buttons.append([InlineKeyboardButton(
                    "Activarme (declarar base)",
                    callback_data="courier_activate",
                )])
            keyboard.extend(courier_buttons)
        update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text(mensaje)


def pendientes_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    telegram_id = update.effective_user.id
    es_admin_plataforma_flag = es_admin_plataforma(telegram_id)

    if not es_admin_plataforma_flag:
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
    """Aprobacion global de repartidores (solo Admin Plataforma). Rechazo va por rechazar_conv."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    # La aprobacion por Admin Local va por admin_local_callback con local_courier_approve.
    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador de plataforma puede usar estos botones.", show_alert=True)
        return

    partes = data.split("_")  # courier_approve_3
    if len(partes) != 3 or partes[0] != "courier" or partes[1] != "approve":
        query.answer("Datos de boton no validos.", show_alert=True)
        return

    try:
        courier_id = int(partes[2])
    except ValueError:
        query.answer("ID de repartidor no valido.", show_alert=True)
        return

    result = approve_role_registration(update.effective_user.id, "COURIER", courier_id)
    if not result.get("ok"):
        query.answer(result.get("message") or "No se pudo aprobar el repartidor.", show_alert=True)
        return

    _resolve_important_alert(context, "courier_registration_{}".format(courier_id))

    courier = result.get("profile")
    if not courier:
        query.edit_message_text("No se encontro el repartidor despues de actualizar.")
        return

    full_name = courier["full_name"]

    try:
        msg = _build_role_welcome_message("COURIER", profile=courier, bonus_granted=bool(result.get("bonus_granted")), reactivated=False)
        u = get_user_by_id(courier["user_id"])
        context.bot.send_message(chat_id=u["telegram_id"], text=msg)
    except Exception as e:
        logger.warning("Error notificando repartidor: %s", e)

    query.edit_message_text("El repartidor '{}' ha sido APROBADO.".format(full_name))
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
            logger.warning("[terms] save_terms_session_ack: %s", e)
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


def terms_callback(update, context):
    query = update.callback_query
    data = query.data
    telegram_id = query.from_user.id
    query.answer()
    logger.debug(
        "[terms][callback] data=%r telegram_id=%s message_id=%s",
        data, telegram_id, getattr(query.message, 'message_id', None),
    )

    if data.startswith("terms_accept_"):
        role = data.split("_", 2)[-1]
        tv = get_active_terms_version(role)
        logger.debug("[terms][callback] accept role=%s tv_found=%s", role, bool(tv))
        if not tv:
            query.edit_message_text("Términos no configurados. Contacta soporte.")
            return

        version, url, sha256 = tv
        save_terms_acceptance(telegram_id, role, version, sha256, query.message.message_id)
        logger.debug("[terms][callback] acceptance_saved role=%s version=%r", role, version)
        if role == "ALLY":
            query.edit_message_text("Aceptación registrada. Ya puedes continuar con Nuevo pedido.")
            logger.debug("[terms][callback] awaiting_manual_nuevo_pedido")
            return
        query.edit_message_text("Aceptación registrada. Ya puedes continuar.")
        return

    if data.startswith("terms_decline_"):
        logger.debug("[terms][callback] decline")
        query.edit_message_text(
            "No puedes usar la plataforma sin aceptar los Términos y Condiciones.\n"
            "Si cambias de decisión, vuelve a intentar y acepta los términos."
        )
        return

    query.answer("Opción no reconocida.", show_alert=True)


def courier_live_location_handler(update, context):
    """
    Maneja ubicaciones en vivo compartidas por repartidores.
    - Live location nueva: courier pasa a ONLINE y se guarda lat/lng.
    - Live location update (edited_message): se actualiza lat/lng.
    - Ubicacion estatica (pin): se ignora para este flujo.
    """
    # Determinar si es mensaje nuevo o editado
    message = update.edited_message or update.message
    if not message or not message.location:
        return

    location = message.location
    lat = location.latitude
    lng = location.longitude

    # Detectar si es live location (tiene live_period)
    # Los pines estaticos se ignoran — pueden venir de flujos de conversacion
    live_period = getattr(location, 'live_period', None)
    if not live_period and not update.edited_message:
        return

    telegram_id = update.effective_user.id

    # Solo procesar si es repartidor aprobado
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        return
    if courier["status"] != "APPROVED":
        return
    if not int(_row_value(courier, "is_active", 0) or 0):
        now_ts = time.time()
        last_sent = context.user_data.get("deact_reminder_ts", 0)
        if now_ts - last_sent >= 300:
            try:
                context.bot.send_message(
                    chat_id=telegram_id,
                    text="Estas desactivado y sigues compartiendo tu ubicacion.\n"
                         "Deten el envio de ubicacion en vivo desde tu chat.\n"
                         "Si quieres activarte, presiona Activarme en tu menu."
                )
                context.user_data["deact_reminder_ts"] = now_ts
            except Exception:
                pass
        return

    # Es live location (nueva o update) -> actualizar y marcar ONLINE
    if update.message and live_period:
        update_courier_live_location(courier["id"], lat, lng, live_period_seconds=live_period)
    else:
        update_courier_live_location(courier["id"], lat, lng)

    # Verificar llegada al punto de recogida si tiene pedido activo
    try:
        check_courier_arrival_at_pickup(courier["id"], lat, lng, context)
    except Exception as e:
        logger.warning("check_courier_arrival_at_pickup: %s", e)

    # Solo notificar la primera vez (cuando pasa a ONLINE visible)
    was_online = (
        _row_value(courier, "availability_status") == "APPROVED"
        and int(_row_value(courier, "live_location_active", 0) or 0) == 1
    )
    if not was_online and update.message and live_period:
        try:
            context.bot.send_message(
                chat_id=telegram_id,
                text="Tu ubicacion en vivo esta activa. Estas ONLINE y recibiras ofertas cercanas."
            )
        except Exception:
            pass


def courier_live_location_expired_check(context):
    """
    Job periodico: revisa couriers ONLINE cuya sesion de ubicacion en vivo
    ya expiro y los desactiva completamente (requieren re-activacion con base).
    """
    expired_ids = expire_stale_live_locations(stale_timeout_seconds=900)
    for cid in expired_ids:
        try:
            courier = get_courier_by_id(cid)
            if courier:
                # Evitar notificacion "antigua" si el courier ya volvio a ONLINE
                if (
                    _row_value(courier, "availability_status") == "APPROVED"
                    and int(_row_value(courier, "live_location_active", 0) or 0) == 1
                ):
                    continue
                user = get_user_by_id(courier["user_id"])
                if user:
                    tg_id = user["telegram_id"]
                    context.bot.send_message(
                        chat_id=tg_id,
                        text="Tu ubicacion en vivo expiro. Quedaste OFFLINE.\n"
                             "Para volver a recibir pedidos, ve a tu menu y presiona Activarme."
                    )
        except Exception as e:
            logger.warning("No se pudo notificar expiracion a courier %s: %s", cid, e)


def _courier_activate_common(update, context, reply_func):
    """Inicia flujo de activacion del courier: pide declarar base."""
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        reply_func("No se encontro tu usuario.")
        return

    courier = get_courier_by_user_id(user["id"])
    if not courier or courier["status"] != "APPROVED":
        reply_func("No tienes perfil de repartidor activo.")
        return

    # Verificar que tiene equipo activo y saldo suficiente para activarse
    admin_link = get_approved_admin_link_for_courier(courier["id"])
    admin_id = _row_value(admin_link, "admin_id")
    if not admin_id:
        admins = get_all_local_admins()
        if not admins:
            reply_func(
                "No tienes equipo activo asignado. Contacta al soporte."
            )
            return
        keyboard = [
            [InlineKeyboardButton(
                f"{_row_value(a, 'full_name')} - {_row_value(a, 'city')}",
                callback_data=f"solequipo_courier_sel_{_row_value(a, 'id')}"
            )]
            for a in admins
        ]
        update.effective_message.reply_text(
            "No tienes equipo activo asignado.\n\n"
            "Selecciona un administrador para solicitar unirte a su equipo:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    saldo = int(_row_value(admin_link, "balance", 0) or 0)
    if saldo < 300:
        reply_func(
            "No puedes activarte porque tu saldo es insuficiente.\n\n"
            "Saldo actual: ${:,}\n"
            "Minimo requerido: $300\n\n"
            "Solicita una recarga a tu administrador para poder conectarte.".format(saldo)
        )
        return

    reply_func(
        "Para activarte, indica cuanta base (dinero en efectivo) tienes disponible.\n\n"
        "Escribe el monto en pesos (solo numeros, ej: 50000):"
    )
    context.user_data["courier_activating"] = True
    context.user_data["courier_id_activating"] = courier["id"]


def _courier_deactivate_common(update, context, reply_func):
    """Desactiva al courier."""
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        reply_func("No se encontro tu usuario.")
        return

    courier = get_courier_by_user_id(user["id"])
    if not courier:
        reply_func("No se encontro tu perfil.")
        return

    deactivate_courier(courier["id"])
    context.user_data.pop("deact_reminder_ts", None)
    courier_updated = get_courier_by_user_id(user["id"])
    updated_keyboard = get_repartidor_menu_keyboard(courier_updated)
    update.effective_message.reply_text(
        "Te has desactivado. No recibiras ofertas de pedidos.\n\n"
        "Deten el envio de ubicacion en vivo desde tu chat para "
        "dejar de compartir tu posicion y ahorrar bateria.",
        reply_markup=updated_keyboard
    )


def courier_activate_from_message(update, context):
    """Activa flujo desde boton del teclado principal."""
    return _courier_activate_common(update, context, update.message.reply_text)


def courier_deactivate_from_message(update, context):
    """Desactiva desde boton del teclado principal."""
    return _courier_deactivate_common(update, context, update.message.reply_text)


def courier_activate_callback(update, context):
    """Inicia flujo de activacion del courier desde callback."""
    query = update.callback_query
    query.answer()
    return _courier_activate_common(update, context, query.edit_message_text)


def courier_deactivate_callback(update, context):
    """Desactiva al courier desde callback."""
    query = update.callback_query
    query.answer()
    return _courier_deactivate_common(update, context, query.edit_message_text)


def courier_base_amount_handler(update, context):
    """Recibe el monto de base declarado por el courier al activarse."""
    if not context.user_data.get("courier_activating"):
        return

    text = update.message.text.strip()
    try:
        amount = int(text.replace(".", "").replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        update.message.reply_text("Por favor escribe solo numeros. Ej: 50000")
        return

    if amount < 0:
        update.message.reply_text("El monto debe ser positivo.")
        return

    courier_id = context.user_data.get("courier_id_activating")
    if not courier_id:
        update.message.reply_text("Error: sesion expirada. Ve a Mi perfil e intenta de nuevo.")
        context.user_data.pop("courier_activating", None)
        context.user_data.pop("courier_id_activating", None)
        return

    ok, msg = can_courier_activate(courier_id)
    if not ok:
        update.message.reply_text(msg)
        context.user_data.pop("courier_activating", None)
        context.user_data.pop("courier_id_activating", None)
        return

    set_courier_available_cash(courier_id, amount)

    context.user_data.pop("courier_activating", None)
    context.user_data.pop("courier_id_activating", None)

    update.message.reply_text(
        "Base registrada: ${:,}\n\n"
        "Aun no estas ONLINE.\n"
        "Comparte tu ubicacion en vivo para activarte "
        "y comenzar a recibir pedidos.".format(amount)
    )


def global_error_handler(update, context):
    """Registra errores no capturados para diagnostico en Railway."""
    try:
        if update and getattr(update, "effective_user", None):
            logger.error(
                "Excepcion no capturada user_id=%s chat_id=%s",
                update.effective_user.id,
                getattr(getattr(update, 'effective_chat', None), 'id', None),
            )
        else:
            logger.error("Excepcion no capturada (sin update)")
        if update and getattr(update, "effective_message", None):
            logger.error("text=%r", getattr(update.effective_message, 'text', None))
    except Exception as meta_err:
        logger.error("meta_log_failed=%s", meta_err)
    logger.error(traceback.format_exc())


def solequipo_start_callback(update, context):
    """Muestra lista de admins para solicitar union a un equipo (desde Ayuda)."""
    query = update.callback_query
    query.answer()
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.edit_message_text("No se encontro tu usuario.")
        return

    courier = get_courier_by_user_id(user["id"])
    ally = get_ally_by_user_id(user["id"])

    if courier and courier["status"] == "APPROVED":
        prefix = "solequipo_courier_sel_"
        role_text = "repartidor"
    elif ally and ally["status"] == "APPROVED":
        prefix = "solequipo_ally_sel_"
        role_text = "aliado"
    else:
        query.edit_message_text(
            "Esta opcion solo esta disponible para repartidores y aliados aprobados."
        )
        return

    admins = get_all_local_admins()
    if not admins:
        query.edit_message_text("No hay administradores disponibles en este momento.")
        return

    keyboard = [
        [InlineKeyboardButton(
            f"{_row_value(a, 'full_name')} - {_row_value(a, 'city')}",
            callback_data=f"{prefix}{_row_value(a, 'id')}"
        )]
        for a in admins
    ]
    query.edit_message_text(
        f"Como {role_text}, selecciona el administrador al que deseas unirte:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def solequipo_courier_sel_callback(update, context):
    """Courier confirma solicitud de union a un admin."""
    query = update.callback_query
    query.answer()
    target_admin_id = int(query.data.replace("solequipo_courier_sel_", ""))

    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.edit_message_text("No se encontro tu usuario.")
        return

    courier = get_courier_by_user_id(user["id"])
    if not courier or courier["status"] != "APPROVED":
        query.edit_message_text("No tienes perfil de repartidor activo.")
        return

    upsert_admin_courier_link(target_admin_id, courier["id"], "PENDING")

    admin = get_admin_by_id(target_admin_id)
    if admin:
        admin_user = get_user_by_id(_row_value(admin, "user_id"))
        if admin_user:
            try:
                context.bot.send_message(
                    chat_id=_row_value(admin_user, "telegram_id"),
                    text=(
                        f"El repartidor {courier['full_name']} ha solicitado unirse a tu equipo.\n"
                        "Revisa tus repartidores pendientes para aprobarlo."
                    )
                )
            except Exception:
                pass

    query.edit_message_text(
        "Solicitud enviada. El administrador recibira tu peticion y podra aprobarte "
        "desde su panel de repartidores pendientes."
    )


def solequipo_ally_sel_callback(update, context):
    """Ally confirma solicitud de union a un admin."""
    query = update.callback_query
    query.answer()
    target_admin_id = int(query.data.replace("solequipo_ally_sel_", ""))

    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.edit_message_text("No se encontro tu usuario.")
        return

    ally = get_ally_by_user_id(user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("No tienes perfil de aliado activo.")
        return

    upsert_admin_ally_link(target_admin_id, ally["id"], "PENDING")

    admin = get_admin_by_id(target_admin_id)
    if admin:
        admin_user = get_user_by_id(_row_value(admin, "user_id"))
        if admin_user:
            try:
                context.bot.send_message(
                    chat_id=_row_value(admin_user, "telegram_id"),
                    text=(
                        f"El aliado {ally['business_name']} ha solicitado unirse a tu equipo.\n"
                        "Revisa tus aliados pendientes para aprobarlo."
                    )
                )
            except Exception:
                pass

    query.edit_message_text(
        "Solicitud enviada. El administrador recibira tu peticion y podra aprobarte "
        "desde su panel de aliados pendientes."
    )


def _recover_pending_fee_collections(bot):
    """Al arrancar, reenvía al admin el botón de reintento por cada cobro de fee pendiente."""
    try:
        pending = get_all_pending_fee_collections()
        for rec in pending:
            try:
                rec = dict(rec) if not isinstance(rec, dict) else rec
                order_id = rec.get("order_id") or (rec[1] if len(rec) > 1 else None)
                creator_admin_id = rec.get("creator_admin_id") or (rec[2] if len(rec) > 2 else None)
                if not order_id or not creator_admin_id:
                    continue
                # Verificar que el pedido sigue en DELIVERED antes de reenviar
                order = get_order_by_id(int(order_id))
                if not order:
                    continue
                order_status = order["status"] if isinstance(order, dict) else order[3]
                if order_status != "DELIVERED":
                    # El pedido fue cancelado o aún no fue entregado; ignorar
                    continue
                admin = get_admin_by_id(int(creator_admin_id))
                if not admin:
                    continue
                user = get_user_by_id(admin["user_id"] if isinstance(admin, dict) else admin[1])
                if not user:
                    continue
                telegram_id = user["telegram_id"] if isinstance(user, dict) else user[2]
                if not telegram_id:
                    continue
                from telegram import InlineKeyboardMarkup, InlineKeyboardButton
                bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        "Cobro pendiente — pedido #{}\n\n"
                        "Hay un fee de plataforma que no pudo cobrarse mientras el bot estuvo reiniciado.\n"
                        "Recarga tu saldo si es necesario y usa el boton para completar el cobro."
                    ).format(order_id),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "Reintentar cobro de fees",
                            callback_data="admin_retry_creator_fees_{}".format(order_id),
                        )
                    ]]),
                )
            except Exception as e:
                logger.warning("_recover_pending_fee_collections: error en registro %s: %s", rec, e)
    except Exception as e:
        logger.warning("_recover_pending_fee_collections: %s", e)


def _notify_expiring_subscriptions_job(context):
    """Job diario: notifica a aliados cuya suscripcion vence en los proximos 3 dias."""
    try:
        expiring = get_expiring_ally_subscriptions(days=3)
        for s in expiring:
            try:
                ally_tg_id = s["ally_telegram_id"]
                if not ally_tg_id:
                    continue
                expires_str = str(s["expires_at"])[:10]
                context.bot.send_message(
                    chat_id=ally_tg_id,
                    text=(
                        "Recordatorio de suscripcion\n\n"
                        "Tu suscripcion vence el {}.\n"
                        "Renovarla desde el menu 'Mi suscripcion' te permite seguir "
                        "disfrutando del servicio sin cobro por cada domicilio.".format(expires_str)
                    ),
                )
            except Exception:
                pass
    except Exception as e:
        logger.warning("_notify_expiring_subscriptions_job: %s", e)


def main():
    # Modo sleep: el servicio Railway sigue vivo pero el bot no arranca.
    # Activar: poner PAUSE_BOT_DEV=true en las variables de entorno del servicio DEV en Railway.
    # Desactivar: eliminar la variable o ponerla en "false".
    if os.getenv("PAUSE_BOT_DEV", "").lower() in ("1", "true", "yes"):
        logger.warning("PAUSE_BOT_DEV activo. Bot en modo sleep. Elimina o pon 'false' en PAUSE_BOT_DEV para reactivar.")
        while True:
            time.sleep(60)

    init_db()
    force_platform_admin(ADMIN_USER_ID)
    ensure_platform_sociedad()
    ensure_pricing_defaults()
    sync_all_courier_link_statuses()
    expire_old_ally_subscriptions()

    if not BOT_TOKEN:
        raise RuntimeError("Falta BOT_TOKEN en variables de entorno.")

    # Log seguro: fingerprint del token para verificar separación DEV/PROD
    token_hash = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:8]
    token_suffix = BOT_TOKEN[-6:] if len(BOT_TOKEN) >= 6 else "***"
    logger.info("TOKEN fingerprint: hash=%s suffix=...%s", token_hash, token_suffix)
    logger.info("Ambiente: %s", ENV)

    persistence_path = os.getenv("PERSISTENCE_PATH", "bot_persistence.pkl")
    persistence = PicklePersistence(filename=persistence_path)
    logger.info("Persistencia: %s", persistence_path)

    updater = Updater(BOT_TOKEN, use_context=True, persistence=persistence)
    dp = updater.dispatcher
    dp.add_error_handler(global_error_handler)

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
    dp.add_handler(CommandHandler("referencias", cmd_referencias))
    # comandos de los administradores
    dp.add_handler(CommandHandler("mi_admin", mi_admin))
    dp.add_handler(CommandHandler("ver_enlaces_admin", ver_enlaces_admin))
    dp.add_handler(CommandHandler("regenerar_enlaces_admin", regenerar_enlaces_admin))
    dp.add_handler(CommandHandler("generar_enlaces_admin", generar_enlaces_admin))
    dp.add_handler(CallbackQueryHandler(regen_invite_callback, pattern="^regen_invite_(ALLY|COURIER|BOTH|ALL)$"))
    dp.add_handler(CommandHandler("mis_invitados", mis_invitados))
    dp.add_handler(CommandHandler("mi_perfil", mi_perfil))

    # Sistema de recargas
    dp.add_handler(CommandHandler("saldo", cmd_saldo))
    dp.add_handler(CommandHandler("recargas_pendientes", cmd_recargas_pendientes))
    dp.add_handler(CallbackQueryHandler(recharge_proof_callback, pattern=r"^recharge_proof_\d+$"))
    dp.add_handler(CallbackQueryHandler(recharge_callback, pattern=r"^recharge_(approve|reject)_\d+$"))
    dp.add_handler(CallbackQueryHandler(plat_recargas_callback, pattern=r"^plat_rec_"))
    dp.add_handler(CallbackQueryHandler(local_recargas_pending_callback, pattern=r"^local_recargas_pending_\d+$"))
    dp.add_handler(CallbackQueryHandler(
        admin_local_callback,
        pattern=r"^local_"
    ))

    # -------------------------
    # Callbacks (ordenados por especificidad)
    # -------------------------

    # Menú de pendientes (botones menu_*)
    dp.add_handler(CallbackQueryHandler(pendientes_callback, pattern=r"^menu_"))

    # Configuraciones (botones config_*)
    dp.add_handler(config_ally_subsidy_conv)      # debe ir ANTES del handler general config_*
    dp.add_handler(config_ally_minpurchase_conv)  # debe ir ANTES del handler general config_*
    dp.add_handler(config_subs_conv)              # configurar precio de suscripcion de aliado
    dp.add_handler(ally_suscripcion_conv)         # aliado ve y renueva su suscripcion
    dp.add_handler(sociedad_retiro_conv)          # Admin Plataforma retira de Sociedad a saldo personal
    dp.add_handler(CallbackQueryHandler(admin_movimientos_callback, pattern=r"^admin_movimientos(?:_\d+)?$"))
    dp.add_handler(CallbackQueryHandler(admin_movimientos_periodo_callback, pattern=r"^admin_movimientos(?:_soc)?_(hoy|semana|mes|todo)(?:_\d+)?$"))
    dp.add_handler(CallbackQueryHandler(admin_mi_saldo_callback, pattern=r"^admin_mi_saldo(?:_\d+)?$"))
    dp.add_handler(CallbackQueryHandler(admin_config_callback, pattern=r"^config_(?!pagos$)"))
    dp.add_handler(CallbackQueryHandler(reference_validation_callback, pattern=r"^ref_"))

    # Aprobación Aliados (botones ally_approve_ID); rechazo va por rechazar_conv
    dp.add_handler(CallbackQueryHandler(ally_approval_callback, pattern=r"^ally_approve_\d+$"))

    # Aprobación Repartidores (botones courier_approve_ID); rechazo va por rechazar_conv
    dp.add_handler(CallbackQueryHandler(courier_approval_callback, pattern=r"^courier_approve_\d+$"))

    # -------------------------
    # Panel admin plataforma (botones admin_*)
    # -------------------------

    # 1) Admins pendientes (handlers específicos)
    dp.add_handler(CallbackQueryHandler(admins_pendientes, pattern=r"^admin_admins_pendientes$"))
    dp.add_handler(CallbackQueryHandler(admin_ver_pendiente, pattern=r"^admin_ver_pendiente_\d+$"))
    dp.add_handler(CallbackQueryHandler(admin_aprobar_rechazar_callback, pattern=r"^admin_aprobar_\d+$"))  # rechazo va por rechazar_conv
    dp.add_handler(
        CallbackQueryHandler(
            order_courier_callback,
            pattern=(
                r"^order_((accept|reject|busy|pickup|delivered|delivered_confirm|delivered_cancel|"
                r"release|release_reason|release_confirm|release_abort|cancel|find_another|"
                r"wait_courier|call_courier|confirm_pickup|pinissue)_\d+(?:_.+)?|"
                r"(cancel_confirm|cancel_abort|find_another_confirm|find_another_abort)_\d+)$"
            ),
        )
    )
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_pickupconfirm_(approve|reject)_\d+$"))
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^admin_pinissue_(fin|cancel_courier|cancel_ally)_\d+$"))
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_repost_\d+$"))  # aliado re-oferta pedido
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_pickup_pinissue_\d+$"))  # pin recogida pedido
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^admin_pickup_(confirm|release)_\d+_\d+$"))  # admin resuelve pin recogida pedido
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^admin_retry_creator_fees_\d+$"))  # reintento cobro fees admin creador
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_fee_detail_\d+$"))  # detalle financiero oferta comision especial
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_commission_confirm_\d+$"))  # courier confirma comision alta
    dp.add_handler(CallbackQueryHandler(pedido_incentivo_menu_callback, pattern=r"^pedido_inc_menu_\d+$"))
    dp.add_handler(CallbackQueryHandler(pedido_incentivo_existing_fixed_callback, pattern=r"^pedido_inc_\d+x(1000|1500|2000|3000)$"))
    dp.add_handler(CallbackQueryHandler(offer_suggest_inc_fixed_callback, pattern=r"^offer_inc_\d+x(1500|2000|3000)$"))
    dp.add_handler(CallbackQueryHandler(route_suggest_inc_fixed_callback, pattern=r"^ruta_inc_\d+x(1500|2000|3000)$"))
    dp.add_handler(CallbackQueryHandler(courier_earnings_callback, pattern=r"^courier_earn_"))
    dp.add_handler(CallbackQueryHandler(courier_activate_callback, pattern=r"^courier_activate$"))
    dp.add_handler(CallbackQueryHandler(courier_deactivate_callback, pattern=r"^courier_deactivate$"))
    dp.add_handler(CallbackQueryHandler(admin_change_requests_callback, pattern=r"^chgreq_"))
    dp.add_handler(CallbackQueryHandler(ally_orders_history_callback, pattern=r"^allyhist_"))
    dp.add_handler(CallbackQueryHandler(admin_special_orders_history_callback, pattern=r"^adminhist_"))
    dp.add_handler(CallbackQueryHandler(admin_orders_callback, pattern=r"^admpedidos_"))
    dp.add_handler(CallbackQueryHandler(solequipo_start_callback, pattern=r"^solequipo_start$"))
    dp.add_handler(CallbackQueryHandler(solequipo_courier_sel_callback, pattern=r"^solequipo_courier_sel_\d+$"))
    dp.add_handler(CallbackQueryHandler(solequipo_ally_sel_callback, pattern=r"^solequipo_ally_sel_\d+$"))

    # -------------------------
    # Conversaciones completas
    # -------------------------
    dp.add_handler(ally_conv)          # /soy_aliado
    dp.add_handler(courier_conv)       # /soy_repartidor
    dp.add_handler(nueva_ruta_conv)    # Nueva ruta (multi-parada)
    dp.add_handler(nuevo_pedido_conv)  # /nuevo_pedido
    dp.add_handler(pedido_incentivo_conv)  # Incentivo adicional post-creacion (aliado)
    dp.add_handler(offer_suggest_inc_conv)  # Incentivo desde sugerencia T+5 (pedido)
    dp.add_handler(route_suggest_inc_conv)  # Incentivo desde sugerencia T+5 (ruta)
    dp.add_handler(ally_clientes_conv)     # Agenda de clientes del Aliado (entry: Mis clientes)
    dp.add_handler(CallbackQueryHandler(ally_bandeja_callback, pattern=r"^alybandeja_"))  # Bandeja solicitudes
    dp.add_handler(CallbackQueryHandler(ally_enlace_refresh_callback, pattern=r"^alyenlace_refresh$"))  # Refrescar Mi enlace
    # Estos tres deben ir ANTES del handler global ^admin_ para que sus entry points no sean interceptados
    dp.add_handler(plat_corregir_addr_conv)  # Corrección coords aliados, solo Admin Plataforma (entry: plat_corr_inicio)
    dp.add_handler(admin_clientes_conv)    # Agenda de clientes del Admin (entry: admin_mis_clientes)
    dp.add_handler(admin_dirs_conv)        # Gestion ubicaciones de recogida del Admin (entry: admin_mis_dirs)
    dp.add_handler(admin_pedido_conv)      # Pedido especial del Admin (entry: admin_nuevo_pedido)
    dp.add_handler(CallbackQueryHandler(admin_mis_plantillas_callback, pattern=r"^admin_mis_plantillas(?:_\d+)?$"))
    dp.add_handler(CallbackQueryHandler(admin_ped_tmpl_info_callback, pattern=r"^admin_ped_tmpl_info_\d+(?:_\d+)?$"))
    dp.add_handler(CallbackQueryHandler(admin_ped_tmpl_menu_del_callback, pattern=r"^admin_ped_tmpl_menu_del_\d+(?:_\d+)?$"))

    # Parqueadero: revision de direcciones (admin local y plataforma)
    dp.add_handler(CallbackQueryHandler(
        lambda u, c: admin_parking_review(u, c, show_all=False),
        pattern=r"^parking_review_list$"
    ))
    dp.add_handler(CallbackQueryHandler(
        admin_parking_review_callback,
        pattern=r"^parking_(rev_yes_\d+|rev_no_\d+|ver_todas|noop_\d+)$"
    ))

    dp.add_handler(rechazar_conv)  # debe ir ANTES de admin_menu_callback
    dp.add_handler(CallbackQueryHandler(admin_menu_callback, pattern=r"^admin_(?!geo_|pedido_|ruta_pinissue_|ruta_pickup_)"))

    # Configuracion de tarifas (botones pricing_*)
    dp.add_handler(CallbackQueryHandler(tarifas_edit_callback, pattern=r"^pricing_"))

    # -------------------------
    # Live location handler para repartidores (ONLINE/PAUSADO)
    # -------------------------
    # Mensajes nuevos con ubicacion (incluye live location inicial)
    dp.add_handler(MessageHandler(Filters.location, courier_live_location_handler), group=2)
    # Mensajes editados (actualizaciones de live location en tiempo real)
    dp.add_handler(MessageHandler(
        Filters.location,
        courier_live_location_handler,
        edited_updates=True,
        message_updates=False,
    ), group=3)

    # Job periodico: expirar live locations cada 60 segundos
    updater.job_queue.run_repeating(
        courier_live_location_expired_check,
        interval=60,
        first=60,
        name="expire_live_locations",
    )
    dp.add_handler(CallbackQueryHandler(handle_route_callback, pattern=r"^ruta_(aceptar|rechazar|ocupado|entregar|liberar|liberar_motivo|liberar_confirmar|liberar_abort|pinissue|cancelar_aliado|find_another|wait_courier|repost|orden|pickup_confirm|pickupconfirm|arrival_enroute|arrival_release)_"))  # callbacks de rutas
    dp.add_handler(CallbackQueryHandler(handle_route_callback, pattern=r"^admin_ruta_pinissue_(fin|cancel_courier|cancel_ally)_"))
    dp.add_handler(CallbackQueryHandler(handle_route_callback, pattern=r"^order_(arrived_pickup|arrival_enroute|arrival_release)_\d+$"))  # llegada al pickup (pedidos normales)
    dp.add_handler(CallbackQueryHandler(handle_route_callback, pattern=r"^ruta_pickup_pinissue_\d+$"))  # pin recogida ruta
    dp.add_handler(CallbackQueryHandler(handle_route_callback, pattern=r"^admin_ruta_pickup_(confirm|release)_\d+_\d+$"))  # admin resuelve pin recogida ruta
    dp.add_handler(CallbackQueryHandler(preview_callback, pattern=r"^preview_"))  # preview oferta
    dp.add_handler(CallbackQueryHandler(ally_block_callback, pattern=r"^ally_block_(block|unblock)_\d+$"))  # bloqueo couriers por aliado
    dp.add_handler(CallbackQueryHandler(handle_rating_callback, pattern=r"^rating_(star|block|skip)_"))  # calificacion post-entrega
    dp.add_handler(agenda_conv)        # /agenda (Agenda del aliado)
    dp.add_handler(ally_locs_conv)     # Mis ubicaciones (aliado)
    dp.add_handler(cotizar_conv)       # /cotizar
    dp.add_handler(tarifas_conv)       # /tarifas (Admin Plataforma)
    dp.add_handler(config_alertas_oferta_conv)  # /config_alertas_oferta (Admin Plataforma)
    dp.add_handler(CallbackQueryHandler(terms_callback, pattern=r"^terms_"))  # /ternimos y condiciones

    # ConversationHandlers de recargas/pagos/ingreso (definidos en handlers.recharges)
    dp.add_handler(recargar_conv)
    dp.add_handler(profile_change_conv)
    dp.add_handler(configurar_pagos_conv)
    dp.add_handler(ingreso_conv)
    dp.add_handler(recarga_directa_conv)

    # -------------------------
    # Registro de Administradores Locales
    # -------------------------
    dp.add_handler(admin_conv)
    dp.add_handler(MessageHandler(Filters.reply & Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, chgreq_reject_reason_handler))

    dp.add_handler(MessageHandler(
        Filters.text & Filters.regex(r'^\d[\d.,\$]*$') & ~Filters.command,
        courier_base_amount_handler,
    ), group=1)
    dp.add_handler(MessageHandler(Filters.location, reference_assign_location_handler), group=1)

    # -------------------------
    # Handler para botones del menú principal (ReplyKeyboard)
    # -------------------------
    dp.add_handler(MessageHandler(
        Filters.regex(r'^(Mi aliado|Mi repartidor.*|Mi admin|Admin plataforma|Mi perfil|Ayuda|Menu|Actualizar menu|Mis pedidos|Mis repartidores|Mi saldo aliado|Mis solicitudes|Activar repartidor|Desactivarme|Actualizar|Pedidos en curso|Mis pedidos repartidor|Mis ganancias|Mi saldo repartidor|Volver al menu)$'),
        menu_button_handler
    ))

    # Handler de saludo para onboarding (sin comandos)
    dp.add_handler(MessageHandler(
        Filters.regex(r'(?i)^\s*(hola|buenas|buenos dias|buen dia|hello|hi)\s*$') & ~Filters.command,
        saludo_menu_handler
    ))

    # Handler global para "Cancelar" y "Volver al menu" (fuera de conversaciones)
    dp.add_handler(MessageHandler(
        Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'),
        volver_menu_global
    ))

    # Catch-all para callbacks huerfanos (bot reiniciado, sesion expirada)
    dp.add_handler(CallbackQueryHandler(stale_callback_handler))

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
            logger.warning("No se pudo notificar al admin: %s", e)
    else:
        logger.info("ADMIN_USER_ID=0, se omite notificacion de arranque.")

    # Recuperar jobs persistidos tras reinicio
    recover_scheduled_jobs(updater.job_queue)

    # Job diario: notificar suscripciones proximas a vencer (cada 24 h, primer disparo en 1 h)
    updater.job_queue.run_repeating(
        _notify_expiring_subscriptions_job,
        interval=86400,
        first=3600,
        name="notify_expiring_subscriptions",
    )

    # Rehidratar ofertas activas que pudieron quedar a mitad del ciclo por reinicio
    recover_active_offer_dispatches(updater)

    # Reenviar notificaciones de cobros de fees pendientes (sobreviven reinicios)
    _recover_pending_fee_collections(updater.bot)

    # Iniciar el bot
    updater.start_polling(drop_pending_updates=True)
    logger.info("Polling iniciado. Bot activo.")
    updater.idle()


if __name__ == "__main__":
    main()





