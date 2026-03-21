import os
import hashlib
import os
import time
import traceback
from datetime import datetime, timezone
from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import BadRequest
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

from services import (
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
    get_available_admin_teams,
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
    get_all_allies,
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
    get_all_couriers,
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
    get_active_order_for_courier,
    get_active_route_for_courier,
    get_pending_route_stops,
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
)
from order_delivery import publish_order_to_couriers, order_courier_callback, ally_active_orders, admin_orders_panel, admin_orders_callback, publish_route_to_couriers, handle_route_callback, handle_rating_callback, check_courier_arrival_at_pickup, repost_order_to_couriers
from db import (
    init_db,
    force_platform_admin,
    ensure_pricing_defaults,
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
    clientes_conv,
)
from handlers.recharges import (
    recargar_conv,
    configurar_pagos_conv,
    ingreso_conv,
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
)
from handlers.registration import (
    soy_aliado,
    ally_name,
    ally_owner,
    ally_document,
    ally_phone,
    ally_city,
    ally_barrio,
    ally_address,
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
    courier_residence_address,
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
    admin_nuevo_pedido_start, admin_pedido_pickup_callback,
    admin_pedido_nueva_dir_start, admin_pedido_pickup_text_handler,
    admin_pedido_geo_pickup_callback, admin_pedido_pickup_gps_handler,
    admin_pedido_save_pickup_callback, admin_pedido_cust_name_handler,
    admin_pedido_sel_cust_handler, admin_pedido_cust_selected,
    admin_pedido_addr_selected, admin_pedido_addr_nueva,
    admin_pedido_cust_phone_handler, admin_pedido_cust_addr_handler,
    admin_pedido_cust_gps_handler, admin_pedido_geo_callback,
    admin_pedido_tarifa_handler, admin_pedido_instruc_handler,
    admin_pedido_sin_instruc_callback, admin_pedido_inc_fijo_callback,
    admin_pedido_inc_otro_callback, admin_pedido_inc_monto_handler,
    admin_pedido_confirmar_callback, admin_pedido_cancelar_callback,
    construir_preview_oferta, get_preview_buttons, preview_callback,
    pedido_guardar_cliente_callback,
    _ally_bandeja_guardar_en_agenda, _pedido_pedir_valor_compra,
    pedido_valor_compra_handler, _ally_bandeja_precargar_pedido,
    _ally_bandeja_validar_entrada, _ally_bandeja_validar_ally_y_saldo,
    ally_bandeja_crear_pedido_entry, ally_bandeja_crear_y_guardar_entry,
    nuevo_pedido_conv, pedido_incentivo_conv, offer_suggest_inc_conv,
    admin_pedido_conv,
)

# ============================================================
# SEPARACIÓN DEV/PROD - Evitar conflicto getUpdates
# ============================================================

# Cargar .env SIEMPRE primero
load_dotenv()
ENV = os.getenv("ENV", "PROD").upper()

if ENV == "LOCAL":
    print(f"[ENV] Ambiente: {ENV} - .env cargado")
else:
    print(f"[ENV] Ambiente: {ENV} - usando variables de entorno del sistema (Railway/PROD)")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

# URL base del formulario público de pedidos del aliado.
# Configurar en Railway como variable de entorno FORM_BASE_URL.
# Ejemplo: https://form.domiquerendona.com
FORM_BASE_URL = os.getenv("FORM_BASE_URL", "").rstrip("/")


def _registration_reset_status_label(reset_state):
    if not reset_state:
        return "No autorizado"
    if reset_state.get("registration_reset_active"):
        return "Autorizado activo"
    if reset_state.get("registration_reset_consumed_at"):
        return "Consumido"
    return "No autorizado"


def _append_registration_reset_button(keyboard, role_prefix: str, role_id: int, role_status: str, reset_state):
    if role_status not in ("INACTIVE", "REJECTED"):
        return
    if reset_state and reset_state.get("registration_reset_active"):
        keyboard.append([InlineKeyboardButton("Revocar reinicio", callback_data="{}_reset_clear_{}".format(role_prefix, role_id))])
        return
    if reset_state and reset_state.get("registration_reset_consumed_at"):
        if role_prefix != "config_ally":
            return
    keyboard.append([InlineKeyboardButton("Autorizar reinicio", callback_data="{}_reset_enable_{}".format(role_prefix, role_id))])


def _notify_admin_local_welcome(context, admin_id: int, reactivated: bool = False):
    admin = get_admin_by_id(admin_id)
    if not admin:
        return
    user_row = get_user_by_id(admin["user_id"])
    if not user_row:
        return
    _send_role_welcome_message(
        context,
        "ADMIN_LOCAL",
        user_row["telegram_id"],
        profile=admin,
        reactivated=reactivated,
    )


def _render_platform_ally_detail(query, ally_id: int):
    ally = get_ally_by_id(ally_id)
    if not ally:
        query.edit_message_text("No se encontró el aliado.")
        return

    reset_state = get_ally_reset_state_by_id(ally_id)
    reset_status = _registration_reset_status_label(reset_state)
    admin_link = get_admin_link_for_ally(ally_id)
    default_loc = get_default_ally_location(ally_id)
    loc_lat = _row_value(default_loc, "lat") if default_loc else None
    loc_lng = _row_value(default_loc, "lng") if default_loc else None

    if loc_lat is not None and loc_lng is not None:
        loc_text = "{}, {}".format(loc_lat, loc_lng)
        maps_text = "Maps: https://www.google.com/maps?q={},{}\n".format(loc_lat, loc_lng)
    else:
        loc_text = "No disponible"
        maps_text = ""

    subsidio = int((_row_value(ally, "delivery_subsidy") or 0))
    min_purchase = _row_value(ally, "min_purchase_for_subsidy")
    if subsidio == 0:
        subsidio_label = "Subsidio domicilio: No configurado"
    elif min_purchase is not None:
        subsidio_label = (
            "Subsidio domicilio: ${:,} por pedido\n"
            "Modo: Condicional\n"
            "Compra minima: ${:,}"
        ).format(subsidio, min_purchase)
    else:
        subsidio_label = (
            "Subsidio domicilio: ${:,} por pedido\n"
            "Modo: Incondicional"
        ).format(subsidio)

    if admin_link:
        team_name = _row_value(admin_link, "team_name", "-")
        team_code = _row_value(admin_link, "team_code", "-")
        link_status = _row_value(admin_link, "link_status", "-")
        equipo_label = "{} ({}) - Vínculo: {}".format(team_name, team_code, link_status)
    else:
        equipo_label = "(sin equipo asignado)"

    texto = (
        "Detalle del aliado:\n\n"
        "ID: {id}\n"
        "Negocio: {business_name}\n"
        "Propietario: {owner_name}\n"
        "Teléfono: {phone}\n"
        "Dirección: {address}\n"
        "Ciudad: {city}\n"
        "Barrio: {barrio}\n"
        "Estado: {status}\n"
        "Equipo: {equipo}\n"
        "Reinicio de registro: {reset_status}\n"
        "{subsidio_label}\n"
        "Ubicación: {loc}\n"
        "{maps}"
    ).format(
        id=_row_value(ally, "id", "-"),
        business_name=_row_value(ally, "business_name", "-"),
        owner_name=_row_value(ally, "owner_name", "-"),
        phone=_row_value(ally, "phone", "-"),
        address=_row_value(ally, "address", "-"),
        city=_row_value(ally, "city", "-"),
        barrio=_row_value(ally, "barrio", "-"),
        status=_row_value(ally, "status", "-"),
        equipo=equipo_label,
        reset_status=reset_status,
        subsidio_label=subsidio_label,
        loc=loc_text,
        maps=maps_text,
    )

    status = _row_value(ally, "status")
    keyboard = []

    if status == "PENDING":
        keyboard.append([
            InlineKeyboardButton("✅ Aprobar", callback_data="config_ally_enable_{}".format(ally_id)),
            InlineKeyboardButton("❌ Rechazar", callback_data="config_ally_reject_{}".format(ally_id)),
        ])
    if status == "APPROVED":
        keyboard.append([InlineKeyboardButton("⛔ Desactivar", callback_data="config_ally_disable_{}".format(ally_id))])
    if status == "INACTIVE":
        keyboard.append([InlineKeyboardButton("✅ Activar", callback_data="config_ally_enable_{}".format(ally_id))])
        _append_registration_reset_button(keyboard, "config_ally", ally_id, status, reset_state)
    if status == "REJECTED":
        _append_registration_reset_button(keyboard, "config_ally", ally_id, status, reset_state)

    keyboard.append([InlineKeyboardButton(
        "Editar subsidio domicilio (${:,})".format(subsidio),
        callback_data="config_ally_subsidy_{}".format(ally_id)
    )])
    keyboard.append([InlineKeyboardButton(
        "Compra minima subsidio ({})".format(
            "${:,}".format(min_purchase) if min_purchase is not None else "sin condicion"
        ),
        callback_data="config_ally_minpurchase_{}".format(ally_id)
    )])
    keyboard.append([InlineKeyboardButton("Asignar/corregir equipo", callback_data="config_ally_assign_menu_{}".format(ally_id))])
    keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")])

    query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))




def _render_reference_candidates(query_or_update, offset: int = 0, edit: bool = False):
    rows = get_pending_reference_candidates(offset=offset, limit=10)

    if not rows:
        text = "No hay referencias pendientes por validar."
        keyboard = [[InlineKeyboardButton("Actualizar", callback_data="ref_list_0")]]
    else:
        text = "Referencias pendientes.\nToca una para revisar:"
        keyboard = []
        for row in rows:
            snippet = (row["raw_text"] or "")[:35]
            label = "#{} {} ({})".format(row["id"], snippet, row["seen_count"])
            keyboard.append([InlineKeyboardButton(label, callback_data="ref_view_{}".format(row["id"]))])

        nav = []
        if offset > 0:
            nav.append(InlineKeyboardButton("Anterior", callback_data="ref_list_{}".format(max(0, offset - 10))))
        if len(rows) == 10:
            nav.append(InlineKeyboardButton("Siguiente", callback_data="ref_list_{}".format(offset + 10)))
        if nav:
            keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("Actualizar", callback_data="ref_list_{}".format(offset))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    if edit:
        query_or_update.edit_message_text(text, reply_markup=reply_markup)
    else:
        query_or_update.message.reply_text(text, reply_markup=reply_markup)


def cmd_referencias(update, context):
    reviewer = _get_reference_reviewer(update.effective_user.id)
    if not reviewer["ok"]:
        update.message.reply_text(reviewer["message"])
        return
    _render_reference_candidates(update, offset=0, edit=False)


def reference_validation_callback(update, context):
    query = update.callback_query
    data = query.data
    reviewer = _get_reference_reviewer(query.from_user.id)
    if not reviewer["ok"]:
        query.answer(reviewer["message"], show_alert=True)
        return

    if data.startswith("ref_list_"):
        query.answer()
        try:
            offset = int(data.replace("ref_list_", ""))
        except Exception:
            offset = 0
        _render_reference_candidates(query, offset=max(0, offset), edit=True)
        return

    if data.startswith("ref_view_"):
        query.answer()
        try:
            candidate_id = int(data.replace("ref_view_", ""))
        except Exception:
            query.answer("Referencia invalida.", show_alert=True)
            return

        row = get_reference_candidate(candidate_id)
        if not row:
            query.edit_message_text(
                "Referencia no encontrada.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="ref_list_0")]])
            )
            return

        lat = row["suggested_lat"]
        lng = row["suggested_lng"]
        maps_line = ""
        if lat is not None and lng is not None:
            maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(lat, lng)
            try:
                context.bot.send_location(
                    chat_id=query.message.chat_id,
                    latitude=float(lat),
                    longitude=float(lng),
                )
            except Exception:
                pass

        text = (
            "Referencia #{}\n"
            "Texto: {}\n"
            "Normalizado: {}\n"
            "Veces vista: {}\n"
            "Fuente: {}\n"
            "Coords sugeridas: {}, {}\n"
            "{}"
            "Estado: {}"
        ).format(
            row["id"],
            row["raw_text"] or "-",
            row["normalized_text"] or "-",
            row["seen_count"] or 0,
            row["source"] or "-",
            lat if lat is not None else "-",
            lng if lng is not None else "-",
            maps_line,
            row["status"] or "-",
        )

        keyboard = [
            [
                InlineKeyboardButton("Aprobar", callback_data="ref_approve_{}".format(row["id"])),
                InlineKeyboardButton("Rechazar", callback_data="ref_reject_{}".format(row["id"])),
            ],
            [InlineKeyboardButton("Volver", callback_data="ref_list_0")],
        ]
        if lat is None or lng is None:
            keyboard.insert(1, [InlineKeyboardButton("Asignar ubicacion", callback_data="ref_setloc_{}".format(row["id"]))])
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("ref_setloc_"):
        query.answer()
        try:
            candidate_id = int(data.replace("ref_setloc_", ""))
        except Exception:
            query.answer("Referencia invalida.", show_alert=True)
            return

        row = get_reference_candidate(candidate_id)
        if not row:
            query.edit_message_text(
                "Referencia no encontrada.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="ref_list_0")]])
            )
            return

        context.user_data["ref_assign_candidate_id"] = candidate_id
        query.edit_message_text(
            "Envia un PIN de ubicacion de Telegram para esta referencia.\n\n"
            "Referencia: {}\n"
            "Luego te mostrare los botones para aprobar o rechazar.".format(row["raw_text"] or "-"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="ref_view_{}".format(candidate_id))]])
        )
        return

    if data.startswith("ref_approve_") or data.startswith("ref_reject_"):
        query.answer()
        approve = data.startswith("ref_approve_")
        prefix = "ref_approve_" if approve else "ref_reject_"
        try:
            candidate_id = int(data.replace(prefix, ""))
        except Exception:
            query.answer("Referencia invalida.", show_alert=True)
            return

        new_status = "APPROVED" if approve else "REJECTED"
        ok, msg = review_reference_candidate(
            candidate_id,
            new_status,
            reviewed_by_admin_id=reviewer["admin_id"],
            note="review_by_tg:{}".format(query.from_user.id),
        )
        keyboard = [[InlineKeyboardButton("Volver a pendientes", callback_data="ref_list_0")]]
        query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    query.answer("Opcion no reconocida.", show_alert=True)


def reference_assign_location_handler(update, context):
    """
    Recibe un PIN de Telegram para completar coordenadas de una referencia candidata.
    """
    candidate_id = context.user_data.get("ref_assign_candidate_id")
    if not candidate_id:
        return

    reviewer = _get_reference_reviewer(update.effective_user.id)
    if not reviewer["ok"]:
        update.message.reply_text(reviewer["message"])
        context.user_data.pop("ref_assign_candidate_id", None)
        return

    if not update.message or not update.message.location:
        update.message.reply_text("Envia un PIN de ubicacion de Telegram para continuar.")
        return

    row = get_reference_candidate(candidate_id)
    if not row:
        update.message.reply_text("Referencia no encontrada. Usa /referencias nuevamente.")
        context.user_data.pop("ref_assign_candidate_id", None)
        return

    lat = update.message.location.latitude
    lng = update.message.location.longitude
    ok = set_reference_candidate_coords(candidate_id, lat, lng)
    context.user_data.pop("ref_assign_candidate_id", None)

    if not ok:
        update.message.reply_text("No se pudo guardar la ubicacion. Intenta de nuevo con /referencias.")
        return

    keyboard = [
        [
            InlineKeyboardButton("Aprobar", callback_data="ref_approve_{}".format(candidate_id)),
            InlineKeyboardButton("Rechazar", callback_data="ref_reject_{}".format(candidate_id)),
        ],
        [InlineKeyboardButton("Ver referencia", callback_data="ref_view_{}".format(candidate_id))],
        [InlineKeyboardButton("Volver a pendientes", callback_data="ref_list_0")],
    ]
    update.message.reply_text(
        "Ubicacion guardada para la referencia.\n"
        "Ahora puedes aprobarla o rechazarla.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


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
                siguientes_pasos.append("• Tu registro de administrador fue RECHAZADO. Contacta al Administrador de Plataforma.")
        else:
            # Administrador Local normal: mostrar requisitos
            if admin_status == "PENDING":
                siguientes_pasos.append("• Tu registro de administrador está pendiente de aprobación.")
            elif admin_status == "APPROVED":
                siguientes_pasos.append(
                    "• Tu administrador fue APROBADO, pero no podrás operar hasta cumplir requisitos (5 aliados y 10 repartidores con saldo mínimo, más saldo master suficiente)."
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

    # Construir menú agrupado por rol
    missing_cmds = _get_missing_role_commands(ally, courier, admin_local, es_admin_plataforma_flag)
    comandos = []

    comandos.append("General:")
    comandos.append("• /mi_perfil  - Ver tu perfil consolidado")

    if ally and ally.get("status") == "APPROVED" and "/soy_aliado" not in missing_cmds:
        comandos.append("")
        comandos.append("🍕 Aliado:")
        comandos.append("• Toca [Mi aliado] en el menu para ver todas las opciones:")
        comandos.append("  Nuevo pedido, Mis pedidos, Clientes, Agenda,")
        comandos.append("  Cotizar envio, Recargar, Mi saldo")
    elif ally:
        ally_status = ally.get("status", "PENDING")
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
    elif admin_local:
        admin_status = admin_local["status"]
        if admin_status == "INACTIVE" and "/soy_admin" in missing_cmds:
            comandos.append("• /soy_admin  - Volver a registrarte como administrador")
        else:
            comandos.append("• /mi_admin  - Ver tu panel de administrador local")
        if admin_status == "APPROVED":
            comandos.append("• /recargas_pendientes  - Ver solicitudes de recarga")
            comandos.append("• /configurar_pagos  - Configurar datos de pago")
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
    active_order = get_active_order_for_courier(courier["id"])
    active_route = get_active_route_for_courier(courier["id"])
    has_active_service = (active_order and active_order["status"] in ("ACCEPTED", "PICKED_UP")) or (active_route and active_route["status"] == "ACCEPTED")

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

    if active_order and active_order["status"] in ("ACCEPTED", "PICKED_UP"):
        status_labels = {"ACCEPTED": "asignado", "PICKED_UP": "en camino al cliente"}
        label = status_labels.get(active_order["status"], active_order["status"])
        update.message.reply_text(
            "Tienes un pedido en curso (#{}  {}).\n"
            "Presiona \"Pedidos en curso\" para finalizarlo.".format(
                active_order["id"], label
            )
        )
    update.message.reply_text(msg, reply_markup=reply_markup)


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

    active_order = get_active_order_for_courier(courier["id"])
    active_route = get_active_route_for_courier(courier["id"])

    if not active_order and not active_route:
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

    update.message.reply_text("Pedidos en curso:")

    if active_order:
        order_id = _row_value(active_order, "id", "-")
        st = order_status_labels.get(
            _row_value(active_order, "status"),
            _row_value(active_order, "status", "-"),
        )
        order_status = _row_value(active_order, "status")
        pickup_address = _row_value(active_order, "pickup_address") or "No disponible"
        customer_city = _row_value(active_order, "customer_city") or ""
        customer_barrio = _row_value(active_order, "customer_barrio") or ""
        destino_area = "{}, {}".format(customer_barrio, customer_city).strip(", ") or "No disponible"
        total_fee = int((_row_value(active_order, "total_fee") or 0) or 0)

        msg = (
            "Pedido #{}\n"
            "Estado: {}\n"
            "Recoge en: {}\n"
            "Destino: {}\n"
            "Tarifa: ${:,}"
        ).format(order_id, st, pickup_address, destino_area, total_fee)

        kb = []
        if order_status == "ACCEPTED":
            kb.append([
                InlineKeyboardButton(
                    "Confirmar llegada",
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
        update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

    if active_route:
        route_id = _row_value(active_route, "id", "-")
        st = route_status_labels.get(
            _row_value(active_route, "status"),
            _row_value(active_route, "status", "-"),
        )
        route_status = _row_value(active_route, "status")
        pickup_address = _row_value(active_route, "pickup_address") or "No disponible"
        total_fee = int((_row_value(active_route, "total_fee") or 0) or 0)

        pending_stops = get_pending_route_stops(int(route_id)) if route_id != "-" else []
        next_seq = None
        if pending_stops:
            try:
                next_seq = min(int(s["sequence"]) for s in pending_stops if s.get("sequence") is not None)
            except Exception:
                next_seq = None

        msg = (
            "Ruta #{}\n"
            "Estado: {}\n"
            "Recoge en: {}\n"
            "Pago: ${:,}"
        ).format(route_id, st, pickup_address, total_fee)

        kb = []
        if next_seq is not None:
            kb.append([
                InlineKeyboardButton(
                    "Entregar siguiente parada",
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




def nueva_ruta_desde_cotizador(update, context):
    """Entry point de nueva_ruta_conv cuando el aliado elige 'Varias entregas' desde el cotizador."""
    query = update.callback_query
    query.answer()
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        query.edit_message_text("No estas registrado. Usa /start primero.")
        return ConversationHandler.END
    ally = get_ally_by_user_id(db_user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("Tu registro de aliado no esta activo.")
        return ConversationHandler.END
    pickup_lat = context.user_data.pop("prefill_ruta_pickup_lat", None)
    pickup_lng = context.user_data.pop("prefill_ruta_pickup_lng", None)
    # Buscar la ubicacion guardada que coincida con las coords del cotizador
    pickup_address = ""
    pickup_location_id = None
    if pickup_lat and pickup_lng:
        locations = get_ally_locations(ally["id"])
        for loc in locations:
            if loc.get("lat") == pickup_lat and loc.get("lng") == pickup_lng:
                pickup_address = loc.get("address") or ""
                pickup_location_id = loc.get("id")
                break
    context.user_data.clear()
    context.user_data["ruta_ally_id"] = ally["id"]
    context.user_data["ruta_ally"] = ally
    context.user_data["ruta_paradas"] = []
    context.user_data["ruta_pickup_lat"] = pickup_lat
    context.user_data["ruta_pickup_lng"] = pickup_lng
    context.user_data["ruta_pickup_address"] = pickup_address
    context.user_data["ruta_pickup_location_id"] = pickup_location_id
    return _ruta_iniciar_parada(query, context)


def _fmt_pesos(amount: int) -> str:
    try:
        amount = int(amount or 0)
    except Exception:
        amount = 0
    return f"${amount:,}".replace(",", ".")


def _courier_earnings_group_by_date(rows: list) -> list:
    totals = {}
    for r in rows or []:
        date_key = (r.get("date_key") or "").strip()
        if not date_key:
            continue
        d = totals.setdefault(date_key, {"orders": 0, "gross": 0, "fee": 0, "net": 0})
        d["orders"] += 1
        d["gross"] += int(r.get("gross_amount") or 0)
        d["fee"] += int(r.get("platform_fee") or 0)
        d["net"] += int(r.get("net_amount") or 0)
    # Orden desc por fecha (YYYY-MM-DD)
    result = []
    for k in sorted(totals.keys(), reverse=True):
        row = totals[k]
        result.append({
            "date_key": k,
            "orders": row["orders"],
            "gross": row["gross"],
            "fee": row["fee"],
            "net": row["net"],
        })
    return result


def _courier_earnings_buttons(daily: list):
    keyboard = []
    for d in daily:
        date_key = d["date_key"]
        compact = date_key.replace("-", "")
        label = "{} ({} pedidos)".format(date_key, d["orders"])
        keyboard.append([InlineKeyboardButton(label, callback_data="courier_earn_{}".format(compact))])
    keyboard.append([InlineKeyboardButton("Actualizar", callback_data="courier_earn_refresh")])
    return InlineKeyboardMarkup(keyboard)


def courier_earnings_start(update, context):
    """Muestra resumen de ganancias del repartidor por día (según liquidaciones contables)."""
    telegram_id = update.effective_user.id
    ok, courier, rows, msg = courier_get_earnings_history(telegram_id, days=7)
    if not ok:
        update.message.reply_text(msg)
        return

    daily = _courier_earnings_group_by_date(rows)
    if not daily:
        update.message.reply_text("No hay ganancias registradas en los últimos 7 días.")
        return

    total_orders = sum(d["orders"] for d in daily)
    total_gross = sum(d["gross"] for d in daily)
    total_fee = sum(d["fee"] for d in daily)
    total_net = sum(d["net"] for d in daily)

    text = (
        "MIS GANANCIAS (ULTIMOS 7 DIAS)\n\n"
        "Pedidos entregados: {}\n"
        "Bruto: {}\n"
        "Fee plataforma cobrado: {}\n"
        "Neto estimado: {}\n\n"
        "Selecciona un día para ver el detalle:"
    ).format(total_orders, _fmt_pesos(total_gross), _fmt_pesos(total_fee), _fmt_pesos(total_net))

    update.message.reply_text(text, reply_markup=_courier_earnings_buttons(daily))


def courier_earnings_callback(update, context):
    """Callback para ver resumen/detalle de ganancias del repartidor."""
    query = update.callback_query
    query.answer()
    data = query.data or ""
    telegram_id = update.effective_user.id

    if data == "courier_earn_refresh" or data == "courier_earn_back":
        ok, courier, rows, msg = courier_get_earnings_history(telegram_id, days=7)
        if not ok:
            query.edit_message_text(msg)
            return
        daily = _courier_earnings_group_by_date(rows)
        if not daily:
            query.edit_message_text("No hay ganancias registradas en los últimos 7 días.")
            return
        total_orders = sum(d["orders"] for d in daily)
        total_gross = sum(d["gross"] for d in daily)
        total_fee = sum(d["fee"] for d in daily)
        total_net = sum(d["net"] for d in daily)
        text = (
            "MIS GANANCIAS (ULTIMOS 7 DIAS)\n\n"
            "Pedidos entregados: {}\n"
            "Bruto: {}\n"
            "Fee plataforma cobrado: {}\n"
            "Neto estimado: {}\n\n"
            "Selecciona un día para ver el detalle:"
        ).format(total_orders, _fmt_pesos(total_gross), _fmt_pesos(total_fee), _fmt_pesos(total_net))
        query.edit_message_text(text, reply_markup=_courier_earnings_buttons(daily))
        return

    if not data.startswith("courier_earn_"):
        query.edit_message_text("Accion invalida.")
        return

    compact = data[len("courier_earn_"):]
    if not compact.isdigit() or len(compact) != 8:
        query.edit_message_text("Fecha invalida.")
        return

    date_key = "{}-{}-{}".format(compact[0:4], compact[4:6], compact[6:8])
    ok, courier, rows, msg = courier_get_earnings_by_date_key(telegram_id, date_key)
    if not ok:
        query.edit_message_text(msg)
        return

    if not rows:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="courier_earn_back")]])
        query.edit_message_text("No hay registros para {}.".format(date_key), reply_markup=keyboard)
        return

    gross = sum(int(r.get("gross_amount") or 0) for r in rows)
    fee = sum(int(r.get("platform_fee") or 0) for r in rows)
    net = sum(int(r.get("net_amount") or 0) for r in rows)

    lines = [
        "DETALLE DE GANANCIAS",
        "",
        "Fecha: {}".format(date_key),
        "Pedidos: {}".format(len(rows)),
        "Bruto: {}".format(_fmt_pesos(gross)),
        "Fee plataforma cobrado: {}".format(_fmt_pesos(fee)),
        "Neto estimado: {}".format(_fmt_pesos(net)),
        "",
        "Pedidos:",
    ]
    for r in rows[:25]:
        order_id = r.get("order_id")
        hour_key = r.get("hour_key") or "--:--"
        lines.append(
            "#{} {} | Bruto {} | Fee {} | Neto {}".format(
                order_id,
                hour_key,
                _fmt_pesos(int(r.get("gross_amount") or 0)),
                _fmt_pesos(int(r.get("platform_fee") or 0)),
                _fmt_pesos(int(r.get("net_amount") or 0)),
            )
        )
    if len(rows) > 25:
        lines.append("... y {} mas.".format(len(rows) - 25))

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="courier_earn_back")]])
    query.edit_message_text("\n".join(lines), reply_markup=keyboard)


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
        ally_id = ally["id"]
        business_name = ally["business_name"]
        owner_name = ally["owner_name"]
        address = ally["address"]
        city = ally["city"]
        barrio = ally["barrio"]
        phone = ally["phone"]
        status = ally["status"]

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
    es_admin_plataforma_flag = es_admin_plataforma(telegram_id)

    admin_id = None

    if not es_admin_plataforma_flag:
        try:
            user_db_id = get_user_db_id_from_update(update)
            admin = get_admin_by_user_id(user_db_id)

        except Exception:
            admin = None

        if not admin:
            message.reply_text("No tienes permisos para ver repartidores pendientes.")
            return

        admin_id = admin["id"]
        if not admin_id:
            message.reply_text("No se pudo validar tu rol de administrador.")
            return

    # Obtener pendientes según rol
    try:
        if es_admin_plataforma_flag:
            # Combinar: nuevos registros (couriers.status=PENDING) + solicitudes de union (admin_couriers.status=PENDING)
            nuevos = list(get_pending_couriers())
            join_requests = list(get_pending_couriers_by_admin(admin_id))
            seen_ids = set()
            pendientes = []
            for c in nuevos + join_requests:
                cid = c.get("courier_id") or c.get("id")
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    pendientes.append(c)
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
        courier_id = c.get("courier_id") or c.get("id")
        full_name = c.get("full_name", "")
        phone = c.get("phone", "")
        city = c.get("city", "")
        barrio = c.get("barrio", "")

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

        if es_admin_plataforma_flag:
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

        # Enviar fotos de verificación de identidad si están disponibles
        courier_full = get_courier_by_id(courier_id)
        if courier_full:
            cedula_front = courier_full.get("cedula_front_file_id") if isinstance(courier_full, dict) else None
            cedula_back = courier_full.get("cedula_back_file_id") if isinstance(courier_full, dict) else None
            selfie = courier_full.get("selfie_file_id") if isinstance(courier_full, dict) else None
            if cedula_front or cedula_back or selfie:
                try:
                    if cedula_front:
                        context.bot.send_photo(chat_id=message.chat_id, photo=cedula_front, caption="Cédula frente")
                    if cedula_back:
                        context.bot.send_photo(chat_id=message.chat_id, photo=cedula_back, caption="Cédula reverso")
                    if selfie:
                        context.bot.send_photo(chat_id=message.chat_id, photo=selfie, caption="Selfie")
                except Exception as e:
                    print(f"[WARN] No se pudieron enviar fotos del repartidor {courier_id}: {e}")

        
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

    if update.message.location:
        lat = update.message.location.latitude
        lng = update.message.location.longitude
    else:
        text = (update.message.text or "").strip()
        coords = extract_lat_lng_from_text(text)
        if coords:
            lat, lng = coords
        else:
            # Geocoding: intentar como direccion escrita
            geo = resolve_location(text)
            if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
                _mostrar_confirmacion_geocode(
                    update.message, context,
                    geo, text,
                    "admin_geo_si", "admin_geo_no",
                )
                return LOCAL_ADMIN_RESIDENCE_LOCATION

    if lat is None or lng is None:
        _debug_admin_registration_state(context, "admin_residence_location_missing_coords")
        update.message.reply_text(
            "No pude detectar la ubicacion. Envia un pin de Telegram o pega un link de Google Maps."
        )
        return LOCAL_ADMIN_RESIDENCE_LOCATION

    context.user_data["admin_residence_lat"] = lat
    context.user_data["admin_residence_lng"] = lng
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
        _debug_admin_registration_state(context, "admin_geo_confirm_saved")
        query.edit_message_text(
            "Ubicacion confirmada.\n\n"
            "Para verificar tu identidad, necesitamos fotos de tu documento.\n\n"
            "Envia una foto del FRENTE de tu cedula:" + _OPTIONS_HINT
        )
        _set_flow_step(context, "admin", LOCAL_ADMIN_CEDULA_FRONT)
        return LOCAL_ADMIN_CEDULA_FRONT
    else:  # admin_geo_no
        return _geo_siguiente_o_gps(query, context, "admin_geo_si", "admin_geo_no", LOCAL_ADMIN_RESIDENCE_LOCATION)


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
        print("[ERROR] admin_confirm:", e)
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
        print("[WARN] No se pudo notificar al admin plataforma:", e)

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
    
        
def admin_menu(update, context):
    """Panel de Administración de Plataforma."""
    user = update.effective_user
    user_db_id = get_user_db_id_from_update(update)

    # Solo el Admin de Plataforma aprobado puede usar este comando
    if not user_has_platform_admin(user.id):
        update.message.reply_text("Acceso restringido: tu Admin de Plataforma no esta APPROVED.")
        return

    texto = (
        "Panel de Administración de Plataforma.\n"
        "¿Qué deseas revisar?"
    )

    keyboard = [
        [InlineKeyboardButton("👥 Gestión de usuarios", callback_data="admin_gestion_usuarios")],
        [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos")],
        [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
        [InlineKeyboardButton("💰 Saldos de todos", callback_data="admin_saldos")],
        [InlineKeyboardButton("Referencias locales", callback_data="admin_ref_candidates")],
        [InlineKeyboardButton("📊 Finanzas", callback_data="admin_finanzas")],
        [InlineKeyboardButton("💳 Recargas", callback_data="plat_rec_menu")],
        [InlineKeyboardButton("📍 Repartidores online", callback_data="config_couriers_online")],
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

    if data == "admin_change_requests":
        return admin_change_requests_list(update, context)

    if data.startswith("admin_pedidos_local_"):
        try:
            admin_id = int(data.replace("admin_pedidos_local_", ""))
        except ValueError:
            query.answer("Error de formato.", show_alert=True)
            return
        return admin_orders_panel(update, context, admin_id, is_platform=False)

    # Gestión de usuarios (solo Admin Plataforma)
    if data == "admin_gestion_usuarios":
        if not user_has_platform_admin(user_id):
            query.answer("Solo el Administrador de Plataforma puede usar este menú.", show_alert=True)
            return
        query.answer()
        keyboard = [
            [InlineKeyboardButton("👤 Aliados pendientes", callback_data="admin_aliados_pendientes")],
            [InlineKeyboardButton("🚚 Repartidores pendientes", callback_data="admin_repartidores_pendientes")],
            [InlineKeyboardButton("🧑‍💼 Gestionar administradores", callback_data="admin_administradores")],
            [InlineKeyboardButton("Ver totales de registros", callback_data="config_totales")],
            [InlineKeyboardButton("Gestionar aliados", callback_data="config_gestion_aliados")],
            [InlineKeyboardButton("Gestionar repartidores", callback_data="config_gestion_repartidores")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Gestión de usuarios. ¿Qué deseas hacer?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Configuraciones (Admin Plataforma ve todo; Admin local ve solo Configurar pagos)
    if data == "admin_config":
        query.answer()
        is_platform = user_has_platform_admin(user_id)
        keyboard = []
        if is_platform:
            keyboard.append([InlineKeyboardButton("💰 Tarifas", callback_data="config_tarifas")])
        keyboard.append([InlineKeyboardButton("💳 Configurar pagos", callback_data="config_pagos")])
        if is_platform:
            keyboard.append([InlineKeyboardButton("Solicitudes de cambio", callback_data="config_change_requests")])
        if is_platform:
            keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_volver_panel")])
        else:
            keyboard.append([InlineKeyboardButton("Cerrar", callback_data="config_cerrar")])
        query.edit_message_text(
            "Configuraciones. ¿Qué deseas ajustar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Solo el Admin de Plataforma aprobado puede usar estos botones
    if not user_has_platform_admin(user_id):
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

    if data == "admin_ref_candidates":
        query.answer()
        _render_reference_candidates(query, offset=0, edit=True)
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

    # Submenú admins: listar administradores registrados
    if data == "admin_admins_registrados":
        query.answer()
        try:
            admins = get_all_admins()

            if not admins:
                query.edit_message_text(
                    "No hay administradores registrados en este momento.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")]
                    ])
                )
                return

            keyboard = []
            for a in admins:
                adm_id = a['id']
                full_name = a['full_name']
                team_name = a['team_name'] or "-"
                status = a['status']
                keyboard.append([InlineKeyboardButton(
                    "ID {} - {} | {} ({})".format(adm_id, full_name, team_name, status),
                    callback_data="admin_ver_admin_{}".format(adm_id)
                )])

            keyboard.append([InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")])
            query.edit_message_text(
                "Administradores registrados:\n\nToca un admin para ver detalles.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print("[ERROR] admin_admins_registrados:", e)
            query.edit_message_text(
                "Error al cargar administradores. Revisa los logs.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")]
                ])
            )
        return

    # Ver detalle de un admin
    if data.startswith("admin_ver_admin_"):
        query.answer()
        adm_id = int(data.replace("admin_ver_admin_", ""))
        admin_obj = get_admin_by_id(adm_id)

        if not admin_obj:
            query.edit_message_text(
                "Admin no encontrado.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver a la lista", callback_data="admin_admins_registrados")]
                ])
            )
            return

        # Datos del admin objetivo
        adm_full_name = admin_obj.get("full_name") or "-"
        adm_phone = admin_obj.get("phone") or "-"
        adm_city = admin_obj.get("city") or "-"
        adm_barrio = admin_obj.get("barrio") or "-"
        adm_team_name = admin_obj.get("team_name") or "-"
        adm_document = admin_obj.get("document_number") or "-"
        adm_team_code = admin_obj.get("team_code") or "-"
        adm_status = admin_obj.get("status") or "-"

        # Tipo de admin
        tipo_admin = "PLATAFORMA" if adm_team_code == "PLATFORM" else "ADMIN LOCAL"

        # Contadores
        num_couriers = count_admin_couriers(adm_id)
        num_couriers_balance = count_admin_couriers_with_min_balance(adm_id, 5000)
        perm = get_admin_reference_validator_permission(adm_id)
        perm_status = perm["status"] if perm else "INACTIVE"
        reset_state = get_admin_reset_state_by_id(adm_id)
        reset_status = _registration_reset_status_label(reset_state)

        residence_address = admin_obj.get("residence_address")
        residence_lat = admin_obj.get("residence_lat")
        residence_lng = admin_obj.get("residence_lng")
        if residence_lat is not None and residence_lng is not None:
            residence_location = "{}, {}".format(residence_lat, residence_lng)
            maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(residence_lat, residence_lng)
        else:
            residence_location = "No disponible"
            maps_line = ""

        texto = (
            "ADMIN ID: {}\n"
            "Nombre: {}\n"
            "Equipo: {}\n"
            "Team code: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Telefono: {}\n"
            "Documento: {}\n"
            "Estado: {}\n"
            "Tipo: {}\n"
            "Dirección residencia: {}\n"
            "Ubicación residencia: {}\n"
            "{}\n"
            "\n"
            "CONTADORES:\n"
            "Mensajeros vinculados: {}\n"
            "Mensajeros con saldo >= 5000: {}\n"
            "Reinicio de registro: {}"
        ).format(
            adm_id, adm_full_name, adm_team_name, adm_team_code,
            adm_city, adm_barrio, adm_phone, adm_document, adm_status, tipo_admin,
            residence_address or "No registrada",
            residence_location,
            maps_line,
            num_couriers, num_couriers_balance, reset_status
        )
        texto += "\nPermiso validar referencias: {}".format(perm_status)

        keyboard = []

        # Verificar si el usuario actual es Admin Plataforma
        es_plataforma = user_has_platform_admin(query.from_user.id)

        # Solo Admin Plataforma puede cambiar status
        # Y no puede modificar a otro admin PLATFORM (proteger)
        if es_plataforma and adm_team_code != "PLATFORM":
            if adm_status == "PENDING":
                keyboard.append([
                    InlineKeyboardButton("✅ Aprobar", callback_data="admin_set_status_{}_APPROVED".format(adm_id)),
                    InlineKeyboardButton("❌ Rechazar", callback_data="admin_set_status_{}_REJECTED".format(adm_id)),
                ])
            if adm_status == "APPROVED":
                keyboard.append([InlineKeyboardButton("⛔ Desactivar", callback_data="admin_set_status_{}_INACTIVE".format(adm_id))])
                if perm_status == "APPROVED":
                    keyboard.append([InlineKeyboardButton("Quitar permiso validar referencias", callback_data="admin_refperm_{}_INACTIVE".format(adm_id))])
                else:
                    keyboard.append([InlineKeyboardButton("Dar permiso validar referencias", callback_data="admin_refperm_{}_APPROVED".format(adm_id))])
            if adm_status == "INACTIVE":
                keyboard.append([InlineKeyboardButton("✅ Activar", callback_data="admin_set_status_{}_APPROVED".format(adm_id))])
                _append_registration_reset_button(keyboard, "admin", adm_id, adm_status, reset_state)
            # REJECTED: sin botones de accion (estado terminal)

        keyboard.append([InlineKeyboardButton("⬅️ Volver a la lista", callback_data="admin_admins_registrados")])
        keyboard.append([InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Cambiar status de un admin (solo Admin Plataforma)
    if data.startswith("admin_refperm_"):
        payload = data.replace("admin_refperm_", "")
        parts = payload.rsplit("_", 1)
        if len(parts) != 2:
            query.answer("Formato invalido", show_alert=True)
            return

        try:
            adm_id = int(parts[0])
        except Exception:
            query.answer("Admin invalido", show_alert=True)
            return

        new_status = parts[1]
        if new_status not in ("APPROVED", "INACTIVE"):
            query.answer("Estado no valido", show_alert=True)
            return

        target = get_admin_by_id(adm_id)
        if not target:
            query.answer("Admin no encontrado", show_alert=True)
            return
        if target["team_code"] == "PLATFORM":
            query.answer("No aplica para Admin Plataforma", show_alert=True)
            return
        if new_status == "APPROVED" and target["status"] != "APPROVED":
            query.answer("Solo admins locales APPROVED pueden recibir este permiso.", show_alert=True)
            return

        actor_user = get_user_by_telegram_id(query.from_user.id)
        actor_admin = get_admin_by_user_id(actor_user["id"]) if actor_user else None
        if not actor_admin:
            query.answer("No se encontro tu perfil admin.", show_alert=True)
            return

        set_admin_reference_validator_permission(
            adm_id,
            new_status,
            granted_by_admin_id=actor_admin["id"],
        )
        action_text = "otorgado" if new_status == "APPROVED" else "revocado"
        query.edit_message_text(
            "Permiso de validacion de referencias {} para admin {}.".format(action_text, adm_id),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver al admin", callback_data="admin_ver_admin_{}".format(adm_id))],
                [InlineKeyboardButton("Volver al panel", callback_data="admin_volver_panel")],
            ])
        )
        return

    if data.startswith("admin_set_status_"):
        # Formato: admin_set_status_{id}_{STATUS}
        parts = data.replace("admin_set_status_", "").rsplit("_", 1)
        if len(parts) != 2:
            query.answer("Formato invalido")
            return

        adm_id = int(parts[0])
        nuevo_status = parts[1]

        # Validar que sea un status permitido
        if nuevo_status not in ("APPROVED", "INACTIVE", "REJECTED"):
            query.answer("Status no valido")
            return

        # Verificar permisos: el usuario actual debe ser Admin Plataforma aprobado
        es_plataforma = user_has_platform_admin(query.from_user.id)

        if not es_plataforma:
            query.answer("Sin permisos para esta accion")
            return

        # Verificar que el admin objetivo no sea PLATFORM (proteger)
        admin_obj = get_admin_by_id(adm_id)
        if not admin_obj:
            query.answer("Admin no encontrado")
            return

        if admin_obj.get("team_code") == "PLATFORM":
            query.answer("No puedes modificar a un admin de plataforma")
            return

        # Aplicar cambio
        was_reactivated = bool(admin_obj.get("status") in ("INACTIVE", "REJECTED"))
        update_admin_status_by_id(adm_id, nuevo_status, changed_by=f"tg:{update.effective_user.id}")
        if nuevo_status == "APPROVED":
            try:
                _notify_admin_local_welcome(context, adm_id, reactivated=was_reactivated)
            except Exception as e:
                print("[WARN] No se pudo notificar onboarding de admin local:", e)
        query.answer("Estado actualizado a {}".format(nuevo_status))

        # Recargar el detalle
        admin_obj = get_admin_by_id(adm_id)
        adm_full_name = admin_obj.get("full_name") or "-"
        adm_phone = admin_obj.get("phone") or "-"
        adm_city = admin_obj.get("city") or "-"
        adm_barrio = admin_obj.get("barrio") or "-"
        adm_team_name = admin_obj.get("team_name") or "-"
        adm_document = admin_obj.get("document_number") or "-"
        adm_team_code = admin_obj.get("team_code") or "-"
        adm_status = admin_obj.get("status") or "-"

        tipo_admin = "PLATAFORMA" if adm_team_code == "PLATFORM" else "ADMIN LOCAL"
        num_couriers = count_admin_couriers(adm_id)
        num_couriers_balance = count_admin_couriers_with_min_balance(adm_id, 5000)
        perm = get_admin_reference_validator_permission(adm_id)
        perm_status = perm["status"] if perm else "INACTIVE"
        reset_state = get_admin_reset_state_by_id(adm_id)
        reset_status = _registration_reset_status_label(reset_state)

        texto = (
            "ADMIN ID: {}\n"
            "Nombre: {}\n"
            "Equipo: {}\n"
            "Team code: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Telefono: {}\n"
            "Documento: {}\n"
            "Estado: {}\n"
            "Tipo: {}\n\n"
            "CONTADORES:\n"
            "Mensajeros vinculados: {}\n"
            "Mensajeros con saldo >= 5000: {}\n\n"
            "Reinicio de registro: {}\n"
            "Estado actualizado a {}"
        ).format(
            adm_id, adm_full_name, adm_team_name, adm_team_code,
            adm_city, adm_barrio, adm_phone, adm_document, adm_status, tipo_admin,
            num_couriers, num_couriers_balance, reset_status, nuevo_status
        )
        texto += "\nPermiso validar referencias: {}".format(perm_status)

        keyboard = []
        # El admin objetivo no es PLATFORM, mostrar botones segun nuevo status
        if adm_status == "PENDING":
            keyboard.append([
                InlineKeyboardButton("✅ Aprobar", callback_data="admin_set_status_{}_APPROVED".format(adm_id)),
                InlineKeyboardButton("❌ Rechazar", callback_data="admin_set_status_{}_REJECTED".format(adm_id)),
            ])
        if adm_status == "APPROVED":
            keyboard.append([InlineKeyboardButton("⛔ Desactivar", callback_data="admin_set_status_{}_INACTIVE".format(adm_id))])
            if perm_status == "APPROVED":
                keyboard.append([InlineKeyboardButton("Quitar permiso validar referencias", callback_data="admin_refperm_{}_INACTIVE".format(adm_id))])
            else:
                keyboard.append([InlineKeyboardButton("Dar permiso validar referencias", callback_data="admin_refperm_{}_APPROVED".format(adm_id))])
        if adm_status == "INACTIVE":
            keyboard.append([InlineKeyboardButton("✅ Activar", callback_data="admin_set_status_{}_APPROVED".format(adm_id))])
            _append_registration_reset_button(keyboard, "admin", adm_id, adm_status, reset_state)
        # REJECTED: sin botones de accion (estado terminal)
        keyboard.append([InlineKeyboardButton("⬅️ Volver a la lista", callback_data="admin_admins_registrados")])
        keyboard.append([InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("admin_reset_"):
        payload = data.replace("admin_reset_", "")
        parts = payload.rsplit("_", 1)
        if len(parts) != 2:
            query.answer("Formato invalido", show_alert=True)
            return
        action = parts[0]
        try:
            adm_id = int(parts[1])
        except Exception:
            query.answer("Admin invalido", show_alert=True)
            return

        admin_obj = get_admin_by_id(adm_id)
        if not admin_obj:
            query.answer("Admin no encontrado", show_alert=True)
            return
        if admin_obj.get("team_code") == "PLATFORM":
            query.answer("No aplica para Admin Plataforma", show_alert=True)
            return

        reset_state = get_admin_reset_state_by_id(adm_id)
        if action == "enable":
            if admin_obj.get("status") != "INACTIVE":
                query.answer("Primero debe estar INACTIVE para autorizar reinicio.", show_alert=True)
                return
            if reset_state and reset_state.get("registration_reset_active"):
                query.answer("Este reinicio ya está autorizado.", show_alert=True)
                return
            try:
                platform_enable_admin_registration_reset(query.from_user.id, adm_id, note="Autorizado por plataforma")
            except PermissionError as e:
                query.answer(str(e), show_alert=True)
                return
            except ValueError as e:
                query.answer(str(e), show_alert=True)
                return
            query.edit_message_text(
                "Reinicio de registro autorizado correctamente.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Volver al admin", callback_data="admin_ver_admin_{}".format(adm_id))],
                    [InlineKeyboardButton("Volver al panel", callback_data="admin_volver_panel")],
                ])
            )
            return

        if action == "clear":
            if not reset_state or not reset_state.get("registration_reset_active"):
                if reset_state and reset_state.get("registration_reset_consumed_at"):
                    query.answer("Este reinicio ya fue consumido.", show_alert=True)
                else:
                    query.answer("No hay un reinicio activo para revocar.", show_alert=True)
                return
            try:
                platform_clear_admin_registration_reset(query.from_user.id, adm_id)
            except PermissionError as e:
                query.answer(str(e), show_alert=True)
                return
            except ValueError as e:
                query.answer(str(e), show_alert=True)
                return
            query.edit_message_text(
                "Reinicio de registro revocado correctamente.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Volver al admin", callback_data="admin_ver_admin_{}".format(adm_id))],
                    [InlineKeyboardButton("Volver al panel", callback_data="admin_volver_panel")],
                ])
            )
            return

        query.answer("Acción no reconocida", show_alert=True)
        return

    # Volver al panel (reconstruye el teclado sin llamar admin_menu, para evitar update.message)
    if data == "admin_volver_panel":
        query.answer()

        texto = (
            "Panel de Administración de Plataforma.\n"
            "¿Qué deseas revisar?"
        )
        keyboard = [
            [InlineKeyboardButton("👥 Gestión de usuarios", callback_data="admin_gestion_usuarios")],
            [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos")],
            [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
            [InlineKeyboardButton("💰 Saldos de todos", callback_data="admin_saldos")],
            [InlineKeyboardButton("Referencias locales", callback_data="admin_ref_candidates")],
            [InlineKeyboardButton("📊 Finanzas", callback_data="admin_finanzas")],
            [InlineKeyboardButton("💳 Recargas", callback_data="plat_rec_menu")],
        ]

        query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos (submenu principal)
    if data == "admin_saldos":
        query.answer()
        keyboard = [
            [InlineKeyboardButton("🚚 Repartidores", callback_data="admin_saldos_couriers")],
            [InlineKeyboardButton("👤 Aliados", callback_data="admin_saldos_allies")],
            [InlineKeyboardButton("🧑‍💼 Admins", callback_data="admin_saldos_admins_0")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Saldos de todos.\n¿Qué deseas revisar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: equipos (repartidores)
    if data == "admin_saldos_couriers":
        query.answer()
        teams = list_approved_admin_teams(include_platform=True)
        if not teams:
            query.edit_message_text(
                "No hay equipos aprobados disponibles.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")]
                ])
            )
            return

        keyboard = []
        for t in teams:
            admin_id = t["id"]
            team_name = t["team_name"] or "-"
            team_code = t["team_code"] or "-"
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(admin_id, team_name, team_code),
                callback_data="admin_saldos_team_couriers_{}_0".format(admin_id)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")])
        query.edit_message_text(
            "Equipos aprobados (Repartidores).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: equipos (aliados)
    if data == "admin_saldos_allies":
        query.answer()
        teams = list_approved_admin_teams(include_platform=True)
        if not teams:
            query.edit_message_text(
                "No hay equipos aprobados disponibles.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")]
                ])
            )
            return

        keyboard = []
        for t in teams:
            admin_id = t["id"]
            team_name = t["team_name"] or "-"
            team_code = t["team_code"] or "-"
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(admin_id, team_name, team_code),
                callback_data="admin_saldos_team_allies_{}_0".format(admin_id)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")])
        query.edit_message_text(
            "Equipos aprobados (Aliados).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: lista de admins con paginación
    if data.startswith("admin_saldos_admins_"):
        query.answer()
        try:
            offset = int(data.replace("admin_saldos_admins_", ""))
        except Exception:
            offset = 0
        teams = list_approved_admin_teams(include_platform=True)
        page = teams[offset:offset + 20]
        if not page:
            query.edit_message_text(
                "No hay administradores aprobados disponibles.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")]
                ])
            )
            return

        keyboard = []
        for t in page:
            admin_id = t["id"]
            team_name = t["team_name"] or "-"
            team_code = t["team_code"] or "-"
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(admin_id, team_name, team_code),
                callback_data="admin_saldos_member_admin_{}_{}".format(admin_id, offset)
            )])

        if offset > 0:
            keyboard.append([InlineKeyboardButton(
                "⬅️ Anterior", callback_data="admin_saldos_admins_{}".format(offset - 20)
            )])
        if len(page) == 20 and (offset + 20) < len(teams):
            keyboard.append([InlineKeyboardButton(
                "➡️ Siguiente", callback_data="admin_saldos_admins_{}".format(offset + 20)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")])

        query.edit_message_text(
            "Administradores aprobados (Saldos).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: lista de repartidores por admin con paginación
    if data.startswith("admin_saldos_team_couriers_"):
        query.answer()
        parts = data.replace("admin_saldos_team_couriers_", "").split("_")
        admin_id = int(parts[0]) if parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        links = list_courier_links_by_admin(admin_id, limit=20, offset=offset)

        if not links:
            query.edit_message_text(
                "No hay repartidores vinculados a este admin.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_couriers")]
                ])
            )
            return

        keyboard = []
        for idx, r in enumerate(links):
            courier_id = r["courier_id"]
            courier_name = r["full_name"] or "-"
            balance = r["balance"] or 0
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} | saldo {}".format(courier_id, courier_name, balance),
                callback_data="admin_saldos_member_courier_{}_{}_{}".format(admin_id, offset, idx)
            )])

        if offset > 0:
            keyboard.append([InlineKeyboardButton(
                "⬅️ Anterior", callback_data="admin_saldos_team_couriers_{}_{}".format(admin_id, offset - 20)
            )])
        if len(links) == 20:
            keyboard.append([InlineKeyboardButton(
                "➡️ Siguiente", callback_data="admin_saldos_team_couriers_{}_{}".format(admin_id, offset + 20)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_couriers")])

        query.edit_message_text(
            "Repartidores vinculados (admin ID {}).".format(admin_id),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: lista de aliados por admin con paginación
    if data.startswith("admin_saldos_team_allies_"):
        query.answer()
        parts = data.replace("admin_saldos_team_allies_", "").split("_")
        admin_id = int(parts[0]) if parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        links = list_ally_links_by_admin(admin_id, limit=20, offset=offset)

        if not links:
            query.edit_message_text(
                "No hay aliados vinculados a este admin.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_allies")]
                ])
            )
            return

        keyboard = []
        for idx, r in enumerate(links):
            ally_id = r["ally_id"]
            business_name = r["business_name"] or "-"
            balance = r["balance"] or 0
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} | saldo {}".format(ally_id, business_name, balance),
                callback_data="admin_saldos_member_ally_{}_{}_{}".format(admin_id, offset, idx)
            )])

        if offset > 0:
            keyboard.append([InlineKeyboardButton(
                "⬅️ Anterior", callback_data="admin_saldos_team_allies_{}_{}".format(admin_id, offset - 20)
            )])
        if len(links) == 20:
            keyboard.append([InlineKeyboardButton(
                "➡️ Siguiente", callback_data="admin_saldos_team_allies_{}_{}".format(admin_id, offset + 20)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_allies")])

        query.edit_message_text(
            "Aliados vinculados (admin ID {}).".format(admin_id),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: detalle repartidor
    if data.startswith("admin_saldos_member_courier_"):
        query.answer()
        parts = data.replace("admin_saldos_member_courier_", "").split("_")
        admin_id = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        idx = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else -1
        links = list_courier_links_by_admin(admin_id, limit=20, offset=offset)
        if idx < 0 or idx >= len(links):
            query.edit_message_text(
                "No se pudo cargar el detalle del repartidor.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_couriers_{}_{}".format(admin_id, offset))]
                ])
            )
            return

        r = links[idx]
        courier_id = r["courier_id"]
        courier_name = r["full_name"] or "-"
        phone = r["phone"] or "-"
        city = r["city"] or "-"
        barrio = r["barrio"] or "-"
        balance = r["balance"] or 0
        texto = (
            "Repartidor ID: {}\n"
            "Nombre: {}\n"
            "Telefono: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Saldo por vínculo: {}"
        ).format(courier_id, courier_name, phone, city, barrio, balance)
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_couriers_{}_{}".format(admin_id, offset))],
            [InlineKeyboardButton("⬅️ Volver a equipos", callback_data="admin_saldos_couriers")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Saldos de todos: detalle aliado
    if data.startswith("admin_saldos_member_ally_"):
        query.answer()
        parts = data.replace("admin_saldos_member_ally_", "").split("_")
        admin_id = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        idx = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else -1
        links = list_ally_links_by_admin(admin_id, limit=20, offset=offset)
        if idx < 0 or idx >= len(links):
            query.edit_message_text(
                "No se pudo cargar el detalle del aliado.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_allies_{}_{}".format(admin_id, offset))]
                ])
            )
            return

        r = links[idx]
        ally_id = r["ally_id"]
        business_name = r["business_name"] or "-"
        owner_name = r["owner_name"] or "-"
        phone = r["phone"] or "-"
        city = r["city"] or "-"
        barrio = r["barrio"] or "-"
        balance = r["balance"] or 0
        texto = (
            "Aliado ID: {}\n"
            "Negocio: {}\n"
            "Propietario: {}\n"
            "Telefono: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Saldo por vínculo: {}"
        ).format(ally_id, business_name, owner_name, phone, city, barrio, balance)
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_allies_{}_{}".format(admin_id, offset))],
            [InlineKeyboardButton("⬅️ Volver a equipos", callback_data="admin_saldos_allies")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Saldos de todos: detalle admin
    if data.startswith("admin_saldos_member_admin_"):
        query.answer()
        parts = data.replace("admin_saldos_member_admin_", "").split("_")
        admin_id = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        admin_obj = get_admin_by_id(admin_id)
        if not admin_obj:
            query.edit_message_text(
                "Admin no encontrado.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_admins_{}".format(offset))]
                ])
            )
            return

        adm_full_name = admin_obj.get("full_name") or "-"
        adm_team_name = admin_obj.get("team_name") or "-"
        adm_team_code = admin_obj.get("team_code") or "-"
        adm_status = admin_obj.get("status") or "-"
        balance = get_admin_balance(admin_id)
        texto = (
            "ADMIN ID: {}\n"
            "Nombre: {}\n"
            "Equipo: {}\n"
            "Team code: {}\n"
            "Estado: {}\n"
            "Saldo actual: {}"
        ).format(admin_id, adm_full_name, adm_team_name, adm_team_code, adm_status, balance)
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_admins_{}".format(offset))],
            [InlineKeyboardButton("⬅️ Volver a Saldos", callback_data="admin_saldos")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Botones aún no implementados (placeholders)
    if data == "admin_pedidos":
        user_db_id = get_user_db_id_from_update(update)
        admin = get_admin_by_user_id(user_db_id)
        if admin:
            admin_id = admin["id"]
            return admin_orders_panel(update, context, admin_id, is_platform=True)
        query.answer("No se encontro tu perfil de admin.", show_alert=True)
        return


    if data == "admin_finanzas":
        query.answer()
        admin = get_admin_by_user_id(get_user_db_id_from_update(update))
        if not admin:
            query.edit_message_text("No se encontro tu perfil de administrador.")
            return
        balance = get_admin_balance(admin["id"])
        keyboard = [
            [InlineKeyboardButton("Registrar ingreso externo", callback_data="ingreso_iniciar")],
            [InlineKeyboardButton("Volver al Panel", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Finanzas de Plataforma.\n\n"
            "Saldo disponible: ${:,}\n\n"
            "Registra cada pago recibido (efectivo, Nequi, transferencia) "
            "antes de aprobar recargas.".format(balance),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
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

        update_admin_status_by_id(admin_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")

        try:
            _notify_admin_local_welcome(context, admin_id, reactivated=False)
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

        update_admin_status_by_id(admin_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")

        query.edit_message_text(
            "❌ Administrador rechazado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver", callback_data="admin_admins_pendientes")]
            ])
        )
        return

    # Por si llega algo raro
    query.answer("Opción no reconocida.", show_alert=True)


def volver_menu_global(update, context):
    """Handler global para 'Cancelar' o 'Volver al menu' fuera de conversaciones."""
    try:
        context.user_data.clear()
    except Exception:
        pass
    show_main_menu(update, context, "Menu principal. Selecciona una opcion:")


# ----- COTIZADOR INTERNO -----

def courier_pick_admin_callback(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    user_db_id = context.user_data.get("courier_registration_user_id")

    # Opción legacy: no elegir admin -> asignar por defecto a Plataforma
    if data == "courier_pick_admin_none":
        if not user_db_id:
            query.edit_message_text(
                "No encontré tus datos recientes para vincularte a un equipo.\n"
                "Intenta /soy_repartidor de nuevo."
            )
            context.user_data.clear()
            return

        platform_admin = get_platform_admin()
        if not platform_admin:
            query.edit_message_text(
                "No existe equipo de Plataforma para vincularte.\n"
                "Contacta al administrador."
            )
            context.user_data.clear()
            return

        try:
            platform_admin_id = platform_admin["id"]
            courier_data = _create_or_reset_courier_from_context(context, user_db_id)
            courier_id = courier_data["courier_id"]
            create_admin_courier_link(platform_admin_id, courier_id)
        except Exception as e:
            print("[ERROR] create_admin_courier_link PLATFORM:", e)
            query.edit_message_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
            context.user_data.clear()
            return

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
                    "Equipo elegido: PLATAFORMA (PLATFORM)\n\n"
                    "Usa /admin para revisarlo."
                ).format(
                    courier_data["full_name"],
                    courier_data["id_number"],
                    courier_data["phone"],
                    courier_data["city"],
                    courier_data["barrio"],
                    courier_data["plate"],
                    courier_data["bike_type"],
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
            print("[WARN] No se pudo notificar al admin plataforma:", e)

        query.edit_message_text(
            "Perfecto. Quedaste vinculado al equipo de Plataforma.\n"
            "Tu vínculo quedó en estado PENDING hasta aprobación."
        )
        context.user_data.clear()
        return

    # Validación básica del callback
    if not data.startswith("courier_pick_admin_"):
        query.edit_message_text("Opción no reconocida.")
        return

    if not user_db_id:
        query.edit_message_text(
            "No encontré tus datos recientes para vincularte a un equipo.\n"
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
        courier_data = _create_or_reset_courier_from_context(context, user_db_id)
        courier_id = courier_data["courier_id"]
        create_admin_courier_link(admin_id, courier_id)
    except Exception as e:
        print("[ERROR] create_admin_courier_link:", e)
        query.edit_message_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
        context.user_data.clear()
        return

    # Notificar a plataforma y al admin local (sin depender de get_user_by_id)
    admin_telegram_id = None
    admin_team_name = "Equipo"
    admin_team_code = ""
    try:
        admin = get_admin_by_id(admin_id)

        # Heurística:
        # - si admin[1] parece un Telegram ID (muy grande), lo usamos como chat_id
        # - si no, NO rompemos el flujo (solo omitimos notificación)
        admin_user_field = admin.get("user_id") if isinstance(admin, dict) else admin["user_id"]

        if admin_user_field is not None:
            try:
                admin_user_field_int = int(admin_user_field)
                if admin_user_field_int > 100000000:  # típico telegram_id
                    admin_telegram_id = admin_user_field_int
            except Exception:
                admin_telegram_id = None
        if isinstance(admin, dict):
            admin_team_name = admin.get("team_name") or admin_team_name
            admin_team_code = admin.get("team_code") or admin_team_code

    except Exception as e:
        print("[WARN] No se pudo leer admin para notificación:", e)

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
                admin_team_name,
                f"({admin_team_code})" if admin_team_code else "",
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
        print("[WARN] No se pudo notificar al admin plataforma:", e)

    if admin_telegram_id:
        try:
            context.bot.send_message(
                chat_id=admin_telegram_id,
                text=(
                    "Nueva solicitud de repartidor para tu equipo.\n\n"
                    f"Repartidor ID: {courier_id}\n\n"
                    "Entra a /mi_admin para revisar pendientes."
                )
            )
            _schedule_important_alerts(
                context,
                alert_key="team_courier_pending_{}_{}".format(admin_id, courier_id),
                chat_id=admin_telegram_id,
                reminder_text=(
                    "Recordatorio importante:\n"
                    "Tienes un repartidor pendiente de aprobar en tu equipo.\n"
                    "Revisa /mi_admin."
                ),
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
        admin_id = admin["id"]
        full_name = admin["full_name"]
        city = admin["city"]

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

    residence_address = admin.get("residence_address")
    residence_lat = admin.get("residence_lat")
    residence_lng = admin.get("residence_lng")
    if residence_lat is not None and residence_lng is not None:
        residence_location = "{}, {}".format(residence_lat, residence_lng)
        maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(residence_lat, residence_lng)
    else:
        residence_location = "No disponible"
        maps_line = ""

    texto = (
        "Administrador pendiente:\n\n"
        f"ID: {admin['id']}\n"
        f"Nombre: {admin['full_name']}\n"
        f"Teléfono: {admin['phone']}\n"
        f"Ciudad: {admin['city']}\n"
        f"Barrio: {admin['barrio']}\n"
        f"Equipo: {admin['team_name'] or '-'}\n"
        f"Documento: {admin['document_number'] or '-'}\n"
        f"Estado: {admin['status']}\n"
        "Residencia: {}\n"
        "Ubicación residencia: {}\n"
        "{}"
    ).format(
        residence_address or "No registrada",
        residence_location,
        maps_line
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Aprobar", callback_data=f"admin_aprobar_{admin_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"admin_rechazar_{admin_id}")
        ],
        [InlineKeyboardButton("⬅ Volver", callback_data="admin_admins_pendientes")]
    ]

    query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

    # Enviar fotos de verificación de identidad si están disponibles
    cedula_front = admin.get("cedula_front_file_id")
    cedula_back = admin.get("cedula_back_file_id")
    selfie = admin.get("selfie_file_id")
    if cedula_front or cedula_back or selfie:
        try:
            if cedula_front:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_front, caption="Cédula frente")
            if cedula_back:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_back, caption="Cédula reverso")
            if selfie:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=selfie, caption="Selfie")
        except Exception as e:
            print(f"[WARN] No se pudieron enviar fotos del admin {admin_id}: {e}")

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
        admin_actual = get_admin_by_id(admin_id)
        was_reactivated = bool(admin_actual and admin_actual.get("status") in ("INACTIVE", "REJECTED"))
        try:
            update_admin_status_by_id(admin_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            print("[ERROR] update_admin_status_by_id APPROVED:", e)
            query.edit_message_text("Error aprobando administrador. Revisa logs.")
            return

        try:
            _notify_admin_local_welcome(context, admin_id, reactivated=was_reactivated)
        except Exception as e:
            print("[WARN] No se pudo notificar onboarding de admin local:", e)

        _resolve_important_alert(context, "admin_registration_{}".format(admin_id))
        query.edit_message_text("✅ Administrador aprobado (APPROVED).")
        return

    if accion == "rechazar":
        try:
            update_admin_status_by_id(admin_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            print("[ERROR] update_admin_status_by_id REJECTED:", e)
            query.edit_message_text("Error rechazando administrador. Revisa logs.")
            return

        _resolve_important_alert(context, "admin_registration_{}".format(admin_id))
        query.edit_message_text("❌ Administrador rechazado (REJECTED).")
        return

    query.answer("Acción no reconocida.", show_alert=True)


def pendientes(update, context):
    """Menú rápido para ver registros pendientes."""
    user_db_id = get_user_db_id_from_update(update)

    telegram_id = update.effective_user.id
    es_admin_plataforma_flag = es_admin_plataforma(telegram_id)

    if not es_admin_plataforma_flag:
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



def ally_bandeja_solicitudes(update, context):
    """Entry point del boton 'Mis solicitudes' en el menu del aliado."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally:
        update.message.reply_text("No tienes un perfil de aliado activo.")
        return
    _ally_bandeja_mostrar_lista(update, context, ally["id"], edit=False)


_ALLY_ENLACE_STATUS_LABEL = {
    "PENDING_REVIEW":   "Pendiente",
    "PENDING_LOCATION": "Sin ubicacion",
    "SAVED_CONTACT":    "Guardada",
    "CONVERTED_ORDER":  "Convertida",
    "DISMISSED":        "Ignorada",
}

_ALLY_ENLACE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Actualizar", callback_data="alyenlace_refresh")],
    [InlineKeyboardButton("Ver solicitudes", callback_data="alybandeja_pendientes")],
    [InlineKeyboardButton("Ver procesadas", callback_data="alybandeja_procesadas")],
])


def _ally_mi_enlace_build(ally_id):
    """Construye (mensaje, teclado) frescos para la vista 'Mi enlace de pedidos'.
    Lee todos los datos directamente de BD. Retorna (str, InlineKeyboardMarkup)."""
    ally = get_ally_by_id(ally_id)
    if not ally:
        return "No se encontro el perfil de aliado.", _ALLY_ENLACE_KEYBOARD

    token = get_or_create_ally_public_token(ally_id)
    subsidio = int(ally["delivery_subsidy"] or 0)
    try:
        min_purchase = ally["min_purchase_for_subsidy"]
    except (KeyError, IndexError):
        min_purchase = None

    if subsidio > 0 and min_purchase is not None:
        subsidio_info = (
            "Subsidio condicional: ${:,} por pedido\n"
            "Aplica solo en pedidos con compra desde ${:,}.\n"
            "Si la compra no alcanza ese valor, el cliente paga el domicilio completo."
        ).format(subsidio, min_purchase)
    elif subsidio > 0:
        subsidio_info = (
            "Subsidio fijo: ${:,} por pedido\n"
            "Aplica en todos tus pedidos sin condicion."
        ).format(subsidio)
    else:
        subsidio_info = (
            "Sin subsidio configurado. "
            "Tus clientes pagan el valor completo del domicilio."
        )

    conteos = count_ally_form_requests_by_status(ally_id)
    pendientes = conteos.get("PENDING_REVIEW", 0) + conteos.get("PENDING_LOCATION", 0)
    guardadas = conteos.get("SAVED_CONTACT", 0)
    convertidas = conteos.get("CONVERTED_ORDER", 0)
    ignoradas = conteos.get("DISMISSED", 0)
    total_solicitudes = sum(conteos.values())
    if total_solicitudes > 0:
        uso_enlace = "Uso del enlace: {} recibidas — {} convertidas".format(
            total_solicitudes, convertidas
        )
        if pendientes > 0:
            uso_enlace += " — {} pendientes por revisar".format(pendientes)
    else:
        uso_enlace = "Uso del enlace: Aun no hay solicitudes."
    actividad = (
        "Actividad de tu enlace:\n"
        "- Pendientes: {}\n"
        "- Guardadas en agenda: {}\n"
        "- Convertidas en pedido: {}\n"
        "- Ignoradas: {}"
    ).format(pendientes, guardadas, convertidas, ignoradas)

    recientes = list_ally_form_requests_for_ally(ally_id, status=None, limit=5)
    if recientes:
        lineas = []
        for r in recientes:
            etiqueta = _ALLY_ENLACE_STATUS_LABEL.get(r["status"], r["status"])
            nombre = (r["customer_name"] or "").split()[0] if r["customer_name"] else "?"
            if r["status"] == "CONVERTED_ORDER" and r.get("order_id"):
                detalle = "pedido #{}".format(r["order_id"])
            elif r.get("delivery_barrio"):
                detalle = r["delivery_barrio"]
            elif r.get("delivery_address"):
                palabras = (r["delivery_address"] or "").split()
                detalle = " ".join(palabras[:4]) if palabras else "sin direccion"
            else:
                detalle = "sin ubicacion"
            lineas.append("- {}: {} — {}".format(etiqueta, nombre, detalle))
        movimientos = "Ultimos movimientos:\n" + "\n".join(lineas)
    else:
        movimientos = "Ultimos movimientos:\nAun no hay solicitudes registradas."

    if FORM_BASE_URL:
        url = "{}/form/{}".format(FORM_BASE_URL, token)
        mensaje = (
            "Tu enlace de pedidos:\n"
            "{}\n"
            "{}\n\n"
            "{}\n\n"
            "{}\n\n"
            "{}\n\n"
            "Tus clientes pueden registrar sus datos, cotizar el domicilio "
            "y enviarte la solicitud directamente. "
            "En proximos pedidos solo necesitaran su numero de telefono."
            "\n\nTextos para compartir:\n\n"
            "Corto:\n"
            "\"Hola, aqui puedes hacerme tu pedido: {}\"\n\n"
            "Explicativo:\n"
            "\"Hola. Puedes enviarme tu pedido por este enlace: {}. "
            "Ahi puedes registrar tus datos y cotizar el domicilio.\"\n\n"
            "Cliente nuevo:\n"
            "\"Hola. Ahora puedes hacerme tu pedido por este enlace: {}. "
            "La primera vez llenas tus datos; despues sera mas rapido.\""
        ).format(url, uso_enlace, subsidio_info, actividad, movimientos, url, url, url)
    else:
        mensaje = (
            "Token de tu enlace: {}\n"
            "{}\n\n"
            "{}\n\n"
            "{}\n\n"
            "{}\n\n"
            "La URL publica del formulario aun no esta configurada. "
            "Pide al administrador que configure FORM_BASE_URL en el sistema."
        ).format(token, uso_enlace, subsidio_info, actividad, movimientos)

    return mensaje, _ALLY_ENLACE_KEYBOARD


def ally_mi_enlace(update, context):
    """Muestra el enlace de pedidos publico del aliado."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally:
        update.message.reply_text("No tienes un perfil de aliado activo.")
        return
    if ally["status"] != "APPROVED":
        update.message.reply_text(
            "Tu perfil de aliado aun no esta aprobado. "
            "El enlace estara disponible cuando tu cuenta este activa."
        )
        return
    mensaje, markup = _ally_mi_enlace_build(ally["id"])
    update.message.reply_text(mensaje, reply_markup=markup)


def ally_enlace_refresh_callback(update, context):
    """Refresca la vista 'Mi enlace de pedidos' con datos nuevos de BD."""
    query = update.callback_query
    query.answer()
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally:
        query.edit_message_text("No tienes un perfil de aliado activo.")
        return
    if ally["status"] != "APPROVED":
        query.edit_message_text(
            "Tu perfil de aliado aun no esta aprobado. "
            "El enlace estara disponible cuando tu cuenta este activa."
        )
        return
    mensaje, markup = _ally_mi_enlace_build(ally["id"])
    query.edit_message_text(mensaje, reply_markup=markup)


def _ally_bandeja_mostrar_lista(update, context, ally_id, edit=False):
    """Muestra la lista de solicitudes pendientes (PENDING_REVIEW o PENDING_LOCATION) del aliado."""
    solicitudes = list_ally_form_requests_for_ally(
        ally_id, status=["PENDING_REVIEW", "PENDING_LOCATION"], limit=15
    )
    if not solicitudes:
        text = "No tienes solicitudes pendientes."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ver procesadas", callback_data="alybandeja_procesadas")],
            [InlineKeyboardButton("Cerrar", callback_data="alybandeja_cerrar")],
        ])
        if edit and update.callback_query:
            update.callback_query.edit_message_text(text, reply_markup=keyboard)
        else:
            update.effective_message.reply_text(text, reply_markup=keyboard)
        return

    # PENDING_LOCATION primero (requieren ubicacion — mas urgentes), luego PENDING_REVIEW
    solicitudes = sorted(solicitudes, key=lambda s: 0 if s["status"] == "PENDING_LOCATION" else 1)

    sin_ubicacion = sum(1 for s in solicitudes if s["status"] == "PENDING_LOCATION")
    pendientes_rev = sum(1 for s in solicitudes if s["status"] == "PENDING_REVIEW")
    resumen_partes = []
    if sin_ubicacion:
        resumen_partes.append("{} sin ubicacion".format(sin_ubicacion))
    if pendientes_rev:
        resumen_partes.append("{} pendientes".format(pendientes_rev))
    resumen = " | ".join(resumen_partes)

    lines = ["Solicitudes pendientes ({}):  {}\n".format(len(solicitudes), resumen)]
    buttons = []
    for s in solicitudes:
        nombre = s["customer_name"] or "Sin nombre"
        telefono = s["customer_phone"] or ""
        direccion = s["delivery_address"] or "Sin direccion"
        etiqueta = _BANDEJA_STATUS_LABELS.get(s["status"], s["status"])
        lines.append("[{}] {} - {} | {}".format(etiqueta, nombre, telefono, direccion))
        buttons.append([InlineKeyboardButton(
            "{}: {}".format(etiqueta, nombre),
            callback_data="alybandeja_ver_{}".format(s["id"])
        )])
    buttons.append([InlineKeyboardButton("Ver procesadas", callback_data="alybandeja_procesadas")])
    buttons.append([InlineKeyboardButton("Cerrar", callback_data="alybandeja_cerrar")])

    text = "\n".join(lines)
    keyboard = InlineKeyboardMarkup(buttons)
    if edit and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, reply_markup=keyboard)


_BANDEJA_STATUS_LABELS = {
    "PENDING_REVIEW": "Pendiente",
    "PENDING_LOCATION": "Sin ubicacion",
    "SAVED_CONTACT": "Guardada en agenda",
    "DISMISSED": "Ignorada",
    "CONVERTED_ORDER": "Convertida en pedido",
}


def _ally_bandeja_mostrar_procesadas(update, context, ally_id, edit=False):
    """Muestra solicitudes ya procesadas: SAVED_CONTACT, DISMISSED, CONVERTED_ORDER."""
    solicitudes = list_ally_form_requests_for_ally(
        ally_id, status=["SAVED_CONTACT", "DISMISSED", "CONVERTED_ORDER"], limit=20
    )
    if not solicitudes:
        text = "No hay solicitudes procesadas aun."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ver pendientes", callback_data="alybandeja_pendientes")],
            [InlineKeyboardButton("Cerrar", callback_data="alybandeja_cerrar")],
        ])
        if edit and update.callback_query:
            update.callback_query.edit_message_text(text, reply_markup=keyboard)
        else:
            update.effective_message.reply_text(text, reply_markup=keyboard)
        return

    lines = ["Solicitudes procesadas ({}):\n".format(len(solicitudes))]
    buttons = []
    for s in solicitudes:
        nombre = s["customer_name"] or "Sin nombre"
        estado = _BANDEJA_STATUS_LABELS.get(s["status"], s["status"])
        label = "{} [{}]".format(nombre, estado)
        buttons.append([InlineKeyboardButton(
            label,
            callback_data="alybandeja_verp_{}".format(s["id"])
        )])
        lines.append("{} | {} | {}".format(
            nombre,
            s["customer_phone"] or "",
            estado,
        ))

    buttons.append([InlineKeyboardButton("Ver pendientes", callback_data="alybandeja_pendientes")])
    buttons.append([InlineKeyboardButton("Cerrar", callback_data="alybandeja_cerrar")])

    text = "\n".join(lines)
    keyboard = InlineKeyboardMarkup(buttons)
    if edit and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        update.effective_message.reply_text(text, reply_markup=keyboard)


_ORDER_STATUS_LABELS_ALLY = {
    "PENDING": "Pendiente",
    "PUBLISHED": "Buscando repartidor",
    "ACCEPTED": "Repartidor asignado",
    "PICKED_UP": "En camino al cliente",
    "DELIVERED": "Entregado",
    "CANCELLED": "Cancelado",
}


def _ally_bandeja_mostrar_pedido(query, ally_id, order_id):
    """
    Muestra el detalle de un pedido desde la bandeja del aliado.
    Valida que el pedido pertenezca al aliado. Solo lectura.
    """
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text(
            "El pedido #{} no fue encontrado.".format(order_id),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver a procesadas", callback_data="alybandeja_volver_procesadas")]
            ])
        )
        return

    if order["ally_id"] != ally_id:
        query.edit_message_text(
            "Este pedido no pertenece a tu cuenta.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver a procesadas", callback_data="alybandeja_volver_procesadas")]
            ])
        )
        return

    status_label = _ORDER_STATUS_LABELS_ALLY.get(order["status"], order["status"])

    courier_name = "Sin asignar"
    if order["courier_id"]:
        courier_row = get_courier_by_id(order["courier_id"])
        if courier_row and courier_row["full_name"]:
            courier_name = courier_row["full_name"]

    lines = [
        "Pedido #{}".format(order["id"]),
        "Estado: {}".format(status_label),
        "Cliente: {}".format(order["customer_name"] or "N/A"),
        "Telefono: {}".format(order["customer_phone"] or "N/A"),
        "Direccion: {}".format(order["customer_address"] or "N/A"),
        "Repartidor: {}".format(courier_name),
        "Tarifa courier: ${:,}".format(int(order["total_fee"] or 0)),
    ]
    try:
        purchase_amount = order["purchase_amount"]
        if purchase_amount is not None:
            lines.append("Valor de compra: ${:,}".format(int(purchase_amount)))
        delivery_subsidy_applied = int(order["delivery_subsidy_applied"] or 0)
        if delivery_subsidy_applied > 0:
            lines.append("Subsidio aplicado: -${:,}".format(delivery_subsidy_applied))
        elif purchase_amount is not None:
            # Hubo monto de compra confirmado pero el subsidio no aplico
            lines.append("Subsidio aplicado: No")
        customer_delivery_fee = order["customer_delivery_fee"]
        if customer_delivery_fee is not None:
            lines.append("Domicilio al cliente: ${:,}".format(int(customer_delivery_fee)))
    except (KeyError, IndexError):
        pass
    if order["instructions"]:
        lines.append("Instrucciones: {}".format(order["instructions"]))

    query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Volver a procesadas", callback_data="alybandeja_volver_procesadas")]
        ])
    )


def ally_bandeja_callback(update, context):
    """Maneja todos los callbacks alybandeja_* para la bandeja del aliado."""
    query = update.callback_query
    query.answer()
    data = query.data

    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally:
        query.edit_message_text("No tienes un perfil de aliado activo.")
        return

    ally_id = ally["id"]

    if data == "alybandeja_cerrar":
        query.edit_message_text("Bandeja cerrada.")
        return

    if data == "alybandeja_volver" or data == "alybandeja_pendientes":
        _ally_bandeja_mostrar_lista(update, context, ally_id, edit=True)
        return

    if data == "alybandeja_procesadas":
        _ally_bandeja_mostrar_procesadas(update, context, ally_id, edit=True)
        return

    if data == "alybandeja_volver_procesadas":
        _ally_bandeja_mostrar_procesadas(update, context, ally_id, edit=True)
        return

    if data.startswith("alybandeja_ver_"):
        request_id = int(data.split("_")[-1])
        solicitud = get_ally_form_request_by_id(request_id, ally_id)
        if not solicitud:
            query.edit_message_text("Solicitud no encontrada.")
            return

        nombre = solicitud["customer_name"] or "Sin nombre"
        telefono = solicitud["customer_phone"] or "No indicado"
        direccion = solicitud["delivery_address"] or "No indicada"
        ciudad = solicitud["delivery_city"] or ""
        barrio = solicitud["delivery_barrio"] or ""
        notas = solicitud["notes"] or ""

        estado_actual = solicitud.get("status", "")
        estado_label = _BANDEJA_STATUS_LABELS.get(estado_actual, estado_actual)
        _ACCION_SUGERIDA = {
            "PENDING_LOCATION": "confirmar ubicacion con el cliente.",
            "PENDING_REVIEW": "revisar la solicitud y decidir.",
        }
        accion = _ACCION_SUGERIDA.get(estado_actual)

        lines = [
            "Solicitud #{}".format(solicitud["id"]),
            "Estado: {}".format(estado_label),
        ]
        if accion:
            lines.append("Accion sugerida: {}".format(accion))
        lines += [
            "",
            "Cliente: {}".format(nombre),
            "Telefono: {}".format(telefono),
            "Direccion: {}{}{}".format(
                direccion,
                " - " + barrio if barrio else "",
                ", " + ciudad if ciudad else "",
            ),
        ]
        if notas:
            lines.append("Notas: {}".format(notas))
        purchase_amt = solicitud.get("purchase_amount_declared")
        if purchase_amt is not None:
            lines.append("Valor compra declarado: ${}".format("{:,}".format(int(purchase_amt))))

        # Mostrar desglose economico si hay cotizacion
        quoted = solicitud["quoted_price"]
        subsidio = solicitud["subsidio_aliado"]
        incentivo = solicitud["incentivo_cliente"]
        total = solicitud["total_cliente"]
        if quoted is not None:
            lines.append("")
            lines.append("Cotizacion domicilio: ${}".format("{:,}".format(int(quoted))))
            if subsidio:
                lines.append("  Subsidio aliado: -${}".format("{:,}".format(int(subsidio))))
                base = max(int(quoted) - int(subsidio), 0)
                lines.append("  Base cliente: ${}".format("{:,}".format(base)))
            if incentivo:
                lines.append("  Incentivo adicional: +${}".format("{:,}".format(int(incentivo))))
            if total is not None:
                lines.append("  Total cliente: ${}".format("{:,}".format(int(total))))

        # Mostrar order_id si existe (solicitud ya convertida)
        if solicitud.get("order_id"):
            lines.append("")
            lines.append("Convertida en pedido #{}".format(solicitud["order_id"]))

        buttons = [
            [InlineKeyboardButton(
                "Crear pedido",
                callback_data="alybandeja_crear_{}".format(solicitud["id"])
            )],
            [InlineKeyboardButton(
                "Crear y guardar",
                callback_data="alybandeja_crearyguardar_{}".format(solicitud["id"])
            )],
            [InlineKeyboardButton(
                "Guardar en agenda",
                callback_data="alybandeja_guardar_{}".format(solicitud["id"])
            )],
            [InlineKeyboardButton(
                "Ignorar",
                callback_data="alybandeja_ignorar_{}".format(solicitud["id"])
            )],
            [InlineKeyboardButton("Volver", callback_data="alybandeja_volver")],
        ]
        query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("alybandeja_verp_"):
        request_id = int(data.split("_")[-1])
        solicitud = get_ally_form_request_by_id(request_id, ally_id)
        if not solicitud:
            query.edit_message_text("Solicitud no encontrada.")
            return

        nombre = solicitud["customer_name"] or "Sin nombre"
        telefono = solicitud["customer_phone"] or "No indicado"
        direccion = solicitud["delivery_address"] or "No indicada"
        ciudad = solicitud["delivery_city"] or ""
        barrio = solicitud["delivery_barrio"] or ""
        notas_p = solicitud["notes"] or ""
        estado_label = _BANDEJA_STATUS_LABELS.get(solicitud["status"], solicitud["status"])

        lines_p = [
            "Solicitud #{}".format(solicitud["id"]),
            "Estado: {}".format(estado_label),
            "Cliente: {}".format(nombre),
            "Telefono: {}".format(telefono),
            "Direccion: {}{}{}".format(
                direccion,
                " - " + barrio if barrio else "",
                ", " + ciudad if ciudad else "",
            ),
        ]
        if notas_p:
            lines_p.append("Notas: {}".format(notas_p))
        purchase_amt_p = solicitud.get("purchase_amount_declared")
        if purchase_amt_p is not None:
            lines_p.append("Valor compra declarado: ${}".format("{:,}".format(int(purchase_amt_p))))

        quoted_p = solicitud["quoted_price"]
        subsidio_p = solicitud["subsidio_aliado"]
        incentivo_p = solicitud["incentivo_cliente"]
        total_p = solicitud["total_cliente"]
        if quoted_p is not None:
            lines_p.append("")
            lines_p.append("Cotizacion domicilio: ${}".format("{:,}".format(int(quoted_p))))
            if subsidio_p:
                lines_p.append("  Subsidio aliado: -${}".format("{:,}".format(int(subsidio_p))))
                base_p = max(int(quoted_p) - int(subsidio_p), 0)
                lines_p.append("  Base cliente: ${}".format("{:,}".format(base_p)))
            if incentivo_p:
                lines_p.append("  Incentivo adicional: +${}".format("{:,}".format(int(incentivo_p))))
            if total_p is not None:
                lines_p.append("  Total cliente: ${}".format("{:,}".format(int(total_p))))

        order_id_p = solicitud.get("order_id")
        if order_id_p:
            lines_p.append("")
            lines_p.append("Convertida en pedido #{}".format(order_id_p))

        back_buttons = []
        if order_id_p:
            back_buttons.append([InlineKeyboardButton(
                "Ver pedido #{}".format(order_id_p),
                callback_data="alybandeja_verpedido_{}".format(order_id_p)
            )])
        back_buttons.append([InlineKeyboardButton("Volver a procesadas", callback_data="alybandeja_volver_procesadas")])

        query.edit_message_text(
            "\n".join(lines_p),
            reply_markup=InlineKeyboardMarkup(back_buttons)
        )
        return

    if data.startswith("alybandeja_verpedido_"):
        try:
            order_id_req = int(data.split("_")[-1])
        except (ValueError, IndexError):
            query.edit_message_text("Referencia de pedido no valida.")
            return
        _ally_bandeja_mostrar_pedido(query, ally_id, order_id_req)
        return

    if data.startswith("alybandeja_guardar_"):
        request_id = int(data.split("_")[-1])
        solicitud = get_ally_form_request_by_id(request_id, ally_id)
        if not solicitud:
            query.edit_message_text("Solicitud no encontrada.")
            return
        if solicitud["status"] not in ("PENDING_REVIEW", "PENDING_LOCATION"):
            query.edit_message_text(
                "Esta solicitud ya fue procesada anteriormente.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
            )
            return

        msg_cliente, msg_dir = _ally_bandeja_guardar_en_agenda(ally_id, solicitud)
        update_ally_form_request_status(request_id, ally_id, "SAVED_CONTACT")
        query.edit_message_text(
            "{}{}\n\nPuedes ver el cliente en tu agenda.".format(msg_cliente, msg_dir),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
        )
        return

    if data.startswith("alybandeja_ignorar_"):
        request_id = int(data.split("_")[-1])
        solicitud = get_ally_form_request_by_id(request_id, ally_id)
        if not solicitud:
            query.edit_message_text("Solicitud no encontrada.")
            return
        if solicitud["status"] not in ("PENDING_REVIEW", "PENDING_LOCATION"):
            query.edit_message_text(
                "Esta solicitud ya fue procesada y no puede ignorarse.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
            )
            return
        update_ally_form_request_status(request_id, ally_id, "DISMISSED")
        query.edit_message_text(
            "Solicitud ignorada.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
        )
        return


# =========================

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
        CommandHandler("menu", menu),
        MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
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
        CommandHandler("menu", menu),
        MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)

# ======================================================
# FLUJO NUEVA RUTA (multi-parada)
# ======================================================

def _ruta_limpiar_temp(context):
    """Limpia datos temporales de la parada actual."""
    for k in ["ruta_temp_name", "ruta_temp_phone", "ruta_temp_address",
              "ruta_temp_city", "ruta_temp_barrio", "ruta_temp_lat", "ruta_temp_lng",
              "ruta_temp_customer_id"]:
        context.user_data.pop(k, None)


def _ruta_mostrar_selector_pickup(update_or_query, context):
    """Muestra el selector de punto de recogida para la ruta."""
    ally_id = context.user_data.get("ruta_ally_id")
    keyboard = []
    if ally_id:
        locations = get_ally_locations(ally_id)
        default_loc = next((l for l in locations if l.get("is_default")), None)
        if default_loc:
            label = (default_loc.get("label") or "Base")[:20]
            address = (default_loc.get("address") or "")[:30]
            keyboard.append([InlineKeyboardButton(
                "Usar base: {} - {}".format(label, address),
                callback_data="ruta_pickup_base"
            )])
        if locations:
            keyboard.append([InlineKeyboardButton(
                "Elegir otra ubicacion ({})".format(len(locations)),
                callback_data="ruta_pickup_lista"
            )])
    keyboard.append([InlineKeyboardButton("Nueva direccion de recogida", callback_data="ruta_pickup_nueva")])
    markup = InlineKeyboardMarkup(keyboard)
    text = "NUEVA RUTA\n\nSelecciona el punto de recogida:"
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(text, reply_markup=markup)
    else:
        update_or_query.message.reply_text(text, reply_markup=markup)
    return RUTA_PICKUP_SELECTOR


def _ruta_guardar_pickup(context, location):
    context.user_data["ruta_pickup_location_id"] = location.get("id")
    context.user_data["ruta_pickup_address"] = location.get("address", "")
    context.user_data["ruta_pickup_lat"] = location.get("lat")
    context.user_data["ruta_pickup_lng"] = location.get("lng")


def _ruta_iniciar_parada(update_or_query, context):
    """Muestra el selector de cliente para la proxima parada."""
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    ally_id = context.user_data.get("ruta_ally_id")
    clientes = list_ally_customers(ally_id) if ally_id else []
    activos = [c for c in clientes if c.get("status") == "ACTIVE"]
    keyboard = [[InlineKeyboardButton("Cliente nuevo", callback_data="ruta_cliente_nuevo")]]
    for c in activos[:8]:
        nombre = (c.get("name") or "Sin nombre")[:25]
        phone = c.get("phone") or ""
        keyboard.append([InlineKeyboardButton(
            "{} - {}".format(nombre, phone),
            callback_data="ruta_sel_cust_{}".format(c["id"])
        )])
    markup = InlineKeyboardMarkup(keyboard)
    text = "PARADA {} DE LA RUTA\n\nSelecciona el cliente:".format(n)
    _ruta_limpiar_temp(context)
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(text, reply_markup=markup)
    else:
        update_or_query.message.reply_text(text, reply_markup=markup)
    return RUTA_PARADA_SELECTOR


def _ruta_guardar_parada_actual(context):
    """Guarda los datos temporales de la parada en la lista ruta_paradas."""
    parada = {
        "name": context.user_data.get("ruta_temp_name") or "",
        "phone": context.user_data.get("ruta_temp_phone") or "",
        "address": context.user_data.get("ruta_temp_address") or "",
        "city": context.user_data.get("ruta_temp_city") or "",
        "barrio": context.user_data.get("ruta_temp_barrio") or "",
        "lat": context.user_data.get("ruta_temp_lat"),
        "lng": context.user_data.get("ruta_temp_lng"),
        "customer_id": context.user_data.get("ruta_temp_customer_id"),  # None si es cliente nuevo
    }
    paradas = context.user_data.get("ruta_paradas", [])
    paradas.append(parada)
    context.user_data["ruta_paradas"] = paradas
    _ruta_limpiar_temp(context)


def _ruta_mostrar_mas_paradas(update_or_query, context):
    """Muestra opcion de agregar mas paradas o continuar."""
    paradas = context.user_data.get("ruta_paradas", [])
    n_actual = len(paradas)
    resumen = "RUTA: {} parada(s) agregada(s)\n\n".format(n_actual)
    for i, p in enumerate(paradas, 1):
        resumen += "Parada {}: {} - {}\n".format(
            i, p.get("name") or "Sin nombre", p.get("address") or "Sin direccion"
        )
    if n_actual >= 5:
        resumen += "\nMaximo 5 paradas alcanzado."
        keyboard = [[InlineKeyboardButton("Continuar con {} paradas".format(n_actual), callback_data="ruta_mas_no")]]
    else:
        keyboard = [
            [InlineKeyboardButton("Agregar parada {}".format(n_actual + 1), callback_data="ruta_mas_si")],
            [InlineKeyboardButton("Listo, continuar con {} parada(s)".format(n_actual), callback_data="ruta_mas_no")],
        ]
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(resumen, reply_markup=markup)
    else:
        update_or_query.message.reply_text(resumen, reply_markup=markup)
    return RUTA_MAS_PARADAS


def _ruta_mostrar_confirmacion(update_or_query, context):
    """Muestra el resumen de la ruta con precio desglosado."""
    paradas = context.user_data.get("ruta_paradas", [])
    total_km = context.user_data.get("ruta_distancia_km", 0)
    pickup_address = context.user_data.get("ruta_pickup_address", "No definida")
    precio_info = calcular_precio_ruta(total_km, len(paradas))
    distance_fee = precio_info["distance_fee"]
    additional_fee = precio_info["additional_stops_fee"]
    total_fee = precio_info["total_fee"]
    stop_fee = precio_info.get("tarifa_parada_adicional", 0)
    context.user_data["ruta_precio"] = precio_info
    text = "RUTA DE ENTREGA\n\nRecoge en: {}\n\n".format(pickup_address)
    for i, p in enumerate(paradas, 1):
        text += "Parada {}:\n  Cliente: {} - {}\n  Direccion: {}\n".format(
            i, p.get("name") or "Sin nombre", p.get("phone") or "", p.get("address") or "Sin direccion"
        )
    text += "\nDistancia total: {:.1f} km\n".format(total_km)
    text += "Precio base (distancia): ${:,}\n".format(distance_fee)
    if additional_fee > 0:
        text += "Paradas adicionales ({} x ${:,}): ${:,}\n".format(len(paradas) - 1, stop_fee, additional_fee)
    text += "TOTAL: ${:,}".format(total_fee)
    keyboard = [
        [InlineKeyboardButton("Confirmar ruta", callback_data="ruta_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="ruta_cancelar")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(text, reply_markup=markup)
    else:
        update_or_query.message.reply_text(text, reply_markup=markup)
    return RUTA_CONFIRMACION


def nueva_ruta_desde_menu(update, context):
    """Entry point de nueva_ruta_conv desde boton 'Varias entregas (ruta)' en nuevo_pedido."""
    query = update.callback_query
    query.answer()
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        query.edit_message_text("No estas registrado. Usa /start primero.")
        return ConversationHandler.END
    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        query.edit_message_text("No tienes perfil de aliado.")
        return ConversationHandler.END
    if ally["status"] != "APPROVED":
        query.edit_message_text("Tu registro como aliado no ha sido aprobado aun.")
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data["ruta_ally_id"] = ally["id"]
    context.user_data["ruta_ally"] = ally
    context.user_data["ruta_paradas"] = []
    show_flow_menu(update, context, "Iniciando nueva ruta...")
    return _ruta_mostrar_selector_pickup(query, context)


def nueva_ruta_start(update, context):
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        update.message.reply_text("Aun no estas registrado. Usa /start primero.")
        return ConversationHandler.END
    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text("No tienes perfil de aliado.")
        return ConversationHandler.END
    if ally["status"] != "APPROVED":
        update.message.reply_text("Tu registro como aliado no ha sido aprobado aun.")
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data["ruta_ally_id"] = ally["id"]
    context.user_data["ruta_ally"] = ally
    context.user_data["ruta_paradas"] = []
    show_flow_menu(update, context, "Iniciando nueva ruta...")
    return _ruta_mostrar_selector_pickup(update, context)


def ruta_pickup_selector_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id")
    if data == "ruta_pickup_base":
        default_loc = get_default_ally_location(ally_id)
        if not default_loc or not default_loc.get("lat"):
            query.edit_message_text("Tu ubicacion base no tiene GPS. Elige otra.")
            return _ruta_mostrar_selector_pickup(query, context)
        _ruta_guardar_pickup(context, default_loc)
        return _ruta_iniciar_parada(query, context)
    if data == "ruta_pickup_lista":
        locations = get_ally_locations(ally_id)
        if not locations:
            query.edit_message_text("No tienes ubicaciones guardadas.")
            return _ruta_mostrar_selector_pickup(query, context)
        keyboard = []
        for loc in locations[:8]:
            label = (loc.get("label") or "Sin nombre")[:20]
            address = (loc.get("address") or "")[:25]
            sin_gps = " (sin GPS)" if not loc.get("lat") else ""
            keyboard.append([InlineKeyboardButton(
                "{}: {}{}".format(label, address, sin_gps),
                callback_data="ruta_pickup_usar_{}".format(loc["id"])
            )])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="ruta_pickup_volver_lista")])
        query.edit_message_text(
            "Selecciona el punto de recogida:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return RUTA_PICKUP_LISTA
    if data == "ruta_pickup_nueva":
        query.edit_message_text(
            "NUEVA DIRECCION DE RECOGIDA\n\n"
            "Envia un PIN de ubicacion de Telegram, link de Google Maps o coordenadas (lat,lng)."
        )
        return RUTA_PICKUP_NUEVA_UBICACION
    return RUTA_PICKUP_SELECTOR


def ruta_pickup_lista_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id")
    if data == "ruta_pickup_volver_lista":
        return _ruta_mostrar_selector_pickup(query, context)
    if data.startswith("ruta_pickup_usar_"):
        try:
            loc_id = int(data.replace("ruta_pickup_usar_", ""))
        except ValueError:
            return RUTA_PICKUP_LISTA
        location = get_ally_location_by_id(loc_id, ally_id)
        if not location or not location.get("lat"):
            query.edit_message_text("Esa ubicacion no tiene GPS. Elige otra.")
            return RUTA_PICKUP_LISTA
        _ruta_guardar_pickup(context, location)
        return _ruta_iniciar_parada(query, context)
    return RUTA_PICKUP_LISTA


def ruta_pickup_nueva_ubicacion_handler(update, context):
    text = update.message.text.strip() if update.message.text else ""
    raw = text
    if "http" in text:
        raw = next((t for t in text.split() if t.startswith("http")), text)
    expanded = expand_short_url(raw) or raw
    coords = extract_lat_lng_from_text(expanded)
    if coords:
        context.user_data["ruta_pickup_lat"] = coords[0]
        context.user_data["ruta_pickup_lng"] = coords[1]
        context.user_data["ruta_pickup_location_id"] = None
        update.message.reply_text(
            "Ubicacion recibida. Ahora escribe la descripcion de la direccion de recogida:"
        )
        return RUTA_PICKUP_NUEVA_DETALLES
    geo = resolve_location(text)
    if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
        context.user_data["ruta_pickup_location_id"] = None
        context.user_data["ruta_pickup_geo_formatted"] = geo.get("formatted_address", "")
        _mostrar_confirmacion_geocode(
            update.message, context, geo, text,
            "ruta_pickup_geo_si", "ruta_pickup_geo_no",
        )
        return RUTA_PICKUP_NUEVA_UBICACION
    if geo and geo.get("lat") is not None:
        context.user_data["ruta_pickup_lat"] = geo["lat"]
        context.user_data["ruta_pickup_lng"] = geo["lng"]
        context.user_data["ruta_pickup_location_id"] = None
        update.message.reply_text(
            "Ubicacion recibida. Ahora escribe la descripcion de la direccion de recogida:"
        )
        return RUTA_PICKUP_NUEVA_DETALLES
    update.message.reply_text(
        "No pude encontrar esa ubicacion.\n\n"
        "Intenta con:\n"
        "- Un PIN de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Nombre del lugar o barrio con ciudad"
    )
    return RUTA_PICKUP_NUEVA_UBICACION


def ruta_pickup_geo_callback(update, context):
    """Confirmacion de geocoding para el punto de recogida de la ruta."""
    query = update.callback_query
    query.answer()
    if query.data == "ruta_pickup_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        formatted = context.user_data.pop("ruta_pickup_geo_formatted", "")
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        context.user_data["ruta_pickup_lat"] = lat
        context.user_data["ruta_pickup_lng"] = lng
        if formatted:
            context.user_data["ruta_pickup_address"] = formatted
        query.edit_message_text(
            "Recogida confirmada.\n\nAhora escribe la descripcion de la direccion (o confirma la sugerida):"
        )
        if formatted:
            query.message.reply_text(formatted)
        return RUTA_PICKUP_NUEVA_DETALLES
    return _geo_siguiente_o_gps(
        query, context, "ruta_pickup_geo_si", "ruta_pickup_geo_no", RUTA_PICKUP_NUEVA_UBICACION
    )


def ruta_pickup_nueva_ubicacion_location_handler(update, context):
    loc = update.message.location
    context.user_data["ruta_pickup_lat"] = loc.latitude
    context.user_data["ruta_pickup_lng"] = loc.longitude
    context.user_data["ruta_pickup_location_id"] = None
    update.message.reply_text("Ubicacion recibida. Ahora escribe la descripcion de la direccion de recogida:")
    return RUTA_PICKUP_NUEVA_DETALLES


def ruta_pickup_nueva_detalles_handler(update, context):
    address = update.message.text.strip()
    if not address:
        update.message.reply_text("Escribe la descripcion de la direccion.")
        return RUTA_PICKUP_NUEVA_DETALLES
    context.user_data["ruta_pickup_address"] = address
    update.message.reply_text("Escribe la ciudad del punto de recogida:")
    return RUTA_PICKUP_NUEVA_CIUDAD


def ruta_pickup_nueva_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad del punto de recogida:",
        "ruta_pickup_city",
        RUTA_PICKUP_NUEVA_CIUDAD,
        RUTA_PICKUP_NUEVA_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector del punto de recogida:",
        options_hint="",
        set_back_step=False,
    )


def ruta_pickup_nueva_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector del punto de recogida:",
        "ruta_pickup_barrio",
        RUTA_PICKUP_NUEVA_BARRIO,
        RUTA_PICKUP_GUARDAR,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == RUTA_PICKUP_NUEVA_BARRIO:
        return ok_state
    barrio = context.user_data.get("ruta_pickup_barrio", "")
    address = context.user_data.get("ruta_pickup_address", "")
    keyboard = [
        [InlineKeyboardButton("Si, guardar", callback_data="ruta_pickup_guardar_si")],
        [InlineKeyboardButton("No, solo para esta ruta", callback_data="ruta_pickup_guardar_no")],
    ]
    update.message.reply_text(
        "Deseas guardar '{}' como una de tus ubicaciones?".format(address[:50]),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return RUTA_PICKUP_GUARDAR


def ruta_pickup_guardar_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id")
    if data == "ruta_pickup_guardar_si":
        address = context.user_data.get("ruta_pickup_address", "")
        lat = context.user_data.get("ruta_pickup_lat")
        lng = context.user_data.get("ruta_pickup_lng")
        new_loc_id = create_ally_location(
            ally_id=ally_id,
            label=address[:30],
            address=address,
            city=context.user_data.get("ruta_pickup_city", ""),
            barrio=context.user_data.get("ruta_pickup_barrio", ""),
            phone="",
            is_default=False,
            lat=lat,
            lng=lng,
        )
        context.user_data["ruta_pickup_location_id"] = new_loc_id
        query.edit_message_text("Direccion guardada.")
    else:
        query.edit_message_text("OK, usaremos esta direccion solo para esta ruta.")
    return _ruta_iniciar_parada(query, context)


def ruta_parada_selector_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id")
    _ruta_limpiar_temp(context)
    if data == "ruta_cliente_nuevo":
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text("PARADA {} - CLIENTE NUEVO\n\nEscribe el nombre del cliente:".format(n))
        return RUTA_PARADA_NOMBRE
    if data.startswith("ruta_sel_cust_"):
        try:
            cust_id = int(data.replace("ruta_sel_cust_", ""))
        except ValueError:
            return RUTA_PARADA_SELECTOR
        customer = get_ally_customer_by_id(cust_id, ally_id)
        if not customer:
            query.edit_message_text("Cliente no encontrado.")
            return RUTA_PARADA_SELECTOR
        context.user_data["ruta_temp_customer_id"] = cust_id
        context.user_data["ruta_temp_name"] = customer.get("name") or ""
        context.user_data["ruta_temp_phone"] = customer.get("phone") or ""
        addresses = list_customer_addresses(cust_id)
        activas = [a for a in addresses if a.get("status") == "ACTIVE"]
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        if not activas:
            query.edit_message_text(
                "PARADA {} - {}\n\nNo tiene direcciones guardadas. Escribe la direccion de entrega:".format(
                    n, customer.get("name") or "Cliente"
                )
            )
            return RUTA_PARADA_DIRECCION
        keyboard = []
        for addr in activas[:6]:
            label = (addr.get("label") or addr.get("address_text") or "Direccion")[:30]
            keyboard.append([InlineKeyboardButton(label, callback_data="ruta_sel_addr_{}".format(addr["id"]))])
        keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="ruta_addr_nueva")])
        query.edit_message_text(
            "PARADA {} - {}\n\nSelecciona la direccion de entrega:".format(n, customer.get("name") or "Cliente"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return RUTA_PARADA_SEL_DIRECCION
    return RUTA_PARADA_SELECTOR


def ruta_parada_sel_direccion_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "ruta_addr_nueva":
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    if data.startswith("ruta_sel_addr_"):
        try:
            addr_id = int(data.replace("ruta_sel_addr_", ""))
        except ValueError:
            return RUTA_PARADA_SEL_DIRECCION
        cust_id = context.user_data.get("ruta_temp_customer_id")
        addr = get_customer_address_by_id(addr_id, cust_id) if cust_id else None
        if not addr:
            query.edit_message_text("Direccion no encontrada.")
            return RUTA_PARADA_SEL_DIRECCION
        if not has_valid_coords(addr.get("lat"), addr.get("lng")):
            query.edit_message_text(
                "Esta direccion guardada no tiene ubicacion confirmada.\n\n"
                "Envia ahora la ubicacion GPS de la parada."
            )
            return RUTA_PARADA_UBICACION
        context.user_data["ruta_temp_address"] = addr.get("address_text") or ""
        context.user_data["ruta_temp_city"] = addr.get("city") or ""
        context.user_data["ruta_temp_barrio"] = addr.get("barrio") or ""
        context.user_data["ruta_temp_lat"] = addr.get("lat")
        context.user_data["ruta_temp_lng"] = addr.get("lng")
        _ruta_guardar_parada_actual(context)
        return _ruta_mostrar_mas_paradas(query, context)
    return RUTA_PARADA_SEL_DIRECCION


def ruta_parada_nombre_handler(update, context):
    nombre = update.message.text.strip()
    if not nombre:
        update.message.reply_text("Escribe el nombre del cliente.")
        return RUTA_PARADA_NOMBRE
    context.user_data["ruta_temp_name"] = nombre
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    update.message.reply_text(
        "PARADA {} - {}\n\nEscribe el telefono del cliente (solo numeros):".format(n, nombre)
    )
    return RUTA_PARADA_TELEFONO


def ruta_parada_telefono_handler(update, context):
    texto = update.message.text.strip()
    digits = "".join(filter(str.isdigit, texto))
    if len(digits) < 7:
        update.message.reply_text("Ingresa un numero de telefono valido (minimo 7 digitos).")
        return RUTA_PARADA_TELEFONO
    context.user_data["ruta_temp_phone"] = digits
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    nombre = context.user_data.get("ruta_temp_name", "")
    update.message.reply_text(
        "PARADA {} - {}\n\n"
        "Envia la ubicacion GPS (PIN de Telegram, link o lat,lng).".format(n, nombre)
    )
    return RUTA_PARADA_UBICACION


def ruta_parada_ubicacion_handler(update, context):
    text = update.message.text.strip()
    if text.lower() == "omitir":
        update.message.reply_text(
            "No se puede omitir la ubicacion de una parada.\n\n"
            "Envia un PIN de Telegram, un link de Maps o coordenadas lat,lng."
        )
        return RUTA_PARADA_UBICACION
    raw = text
    if "http" in text:
        raw = next((t for t in text.split() if t.startswith("http")), text)
    expanded = expand_short_url(raw) or raw
    coords = extract_lat_lng_from_text(expanded)
    if coords:
        context.user_data["ruta_temp_lat"] = coords[0]
        context.user_data["ruta_temp_lng"] = coords[1]
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        update.message.reply_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    geo = resolve_location(text)
    if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
        context.user_data["ruta_parada_geo_formatted"] = geo.get("formatted_address", "")
        _mostrar_confirmacion_geocode(
            update.message, context, geo, text,
            "ruta_parada_geo_si", "ruta_parada_geo_no",
        )
        return RUTA_PARADA_UBICACION
    if geo and geo.get("lat") is not None:
        context.user_data["ruta_temp_lat"] = geo["lat"]
        context.user_data["ruta_temp_lng"] = geo["lng"]
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        update.message.reply_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    update.message.reply_text(
        "No pude encontrar esa ubicacion.\n\n"
        "Intenta con:\n"
        "- Un PIN de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Nombre del lugar o barrio con ciudad\n"
        "- O escribe 'omitir' para ingresar solo la direccion."
    )
    return RUTA_PARADA_UBICACION


def ruta_parada_geo_callback(update, context):
    """Confirmacion de geocoding para la ubicacion de una parada de la ruta."""
    query = update.callback_query
    query.answer()
    if query.data == "ruta_parada_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        formatted = context.user_data.pop("ruta_parada_geo_formatted", "")
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        context.user_data["ruta_temp_lat"] = lat
        context.user_data["ruta_temp_lng"] = lng
        if formatted:
            context.user_data["ruta_temp_address"] = formatted
            query.edit_message_text("Escribe la ciudad de la entrega:")
            return RUTA_PARADA_CIUDAD
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text("PARADA {}\n\nEscribe la descripcion de la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    return _geo_siguiente_o_gps(
        query, context, "ruta_parada_geo_si", "ruta_parada_geo_no", RUTA_PARADA_UBICACION
    )


def ruta_parada_ubicacion_location_handler(update, context):
    loc = update.message.location
    context.user_data["ruta_temp_lat"] = loc.latitude
    context.user_data["ruta_temp_lng"] = loc.longitude
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    update.message.reply_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
    return RUTA_PARADA_DIRECCION


def ruta_parada_direccion_handler(update, context):
    address = update.message.text.strip()
    if not address:
        update.message.reply_text("Escribe la direccion de entrega.")
        return RUTA_PARADA_DIRECCION
    context.user_data["ruta_temp_address"] = address
    update.message.reply_text("Escribe la ciudad de la entrega:")
    return RUTA_PARADA_CIUDAD


def ruta_parada_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la entrega:",
        "ruta_temp_city",
        RUTA_PARADA_CIUDAD,
        RUTA_PARADA_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector de la entrega:",
        options_hint="",
        set_back_step=False,
    )


def ruta_parada_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la entrega:",
        "ruta_temp_barrio",
        RUTA_PARADA_BARRIO,
        RUTA_MAS_PARADAS,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == RUTA_PARADA_BARRIO:
        return ok_state
    _ruta_guardar_parada_actual(context)
    return _ruta_mostrar_mas_paradas(update, context)


def ruta_mas_paradas_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "ruta_mas_si":
        return _ruta_iniciar_parada(query, context)
    if data == "ruta_mas_no":
        paradas = context.user_data.get("ruta_paradas", [])
        if len(paradas) < 2:
            query.edit_message_text("Debes agregar al menos 2 paradas para crear una ruta.")
            return _ruta_iniciar_parada(query, context)
        pickup_lat = context.user_data.get("ruta_pickup_lat")
        pickup_lng = context.user_data.get("ruta_pickup_lng")
        tiene_gps = (
            pickup_lat is not None and pickup_lng is not None
            and all(p.get("lat") is not None and p.get("lng") is not None for p in paradas)
        )
        if tiene_gps:
            query.edit_message_text("Calculando distancia de la ruta...")
            dist_result = calcular_distancia_ruta_smart(pickup_lat, pickup_lng, paradas)
            if dist_result and dist_result["total_km"] > 0:
                context.user_data["ruta_distancia_km"] = dist_result["total_km"]
                return _ruta_mostrar_confirmacion(query, context)
        query.edit_message_text(
            "DISTANCIA DE LA RUTA\n\n"
            "No tengo GPS de todas las paradas para calcular automaticamente.\n"
            "Ingresa la distancia total de la ruta en km.\n\nEjemplo: 10.5"
        )
        return RUTA_DISTANCIA_KM
    return RUTA_MAS_PARADAS


def ruta_distancia_km_handler(update, context):
    text = update.message.text.strip().replace(",", ".")
    try:
        km = float(text)
        if km <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("Ingresa un numero valido mayor a 0 (ej: 8 o 10.5).")
        return RUTA_DISTANCIA_KM
    context.user_data["ruta_distancia_km"] = round(km, 2)
    return _ruta_mostrar_confirmacion(update, context)


def ruta_confirmacion_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "ruta_cancelar":
        query.edit_message_text("Ruta cancelada.")
        context.user_data.clear()
        show_main_menu(update, context)
        return ConversationHandler.END
    if data != "ruta_confirmar":
        return RUTA_CONFIRMACION
    ally_id = context.user_data.get("ruta_ally_id")
    paradas = context.user_data.get("ruta_paradas", [])
    precio_info = context.user_data.get("ruta_precio", {})
    if not ally_id or len(paradas) < 2:
        query.edit_message_text("Error: datos incompletos. Empieza de nuevo con 'Nueva ruta'.")
        context.user_data.clear()
        show_main_menu(update, context)
        return ConversationHandler.END
    pickup_address = context.user_data.get("ruta_pickup_address", "")
    pickup_lat = context.user_data.get("ruta_pickup_lat")
    pickup_lng = context.user_data.get("ruta_pickup_lng")
    pickup_location_id = context.user_data.get("ruta_pickup_location_id")
    total_km = context.user_data.get("ruta_distancia_km", 0)
    if not has_valid_coords(pickup_lat, pickup_lng) or any(
        not has_valid_coords(parada.get("lat"), parada.get("lng")) for parada in paradas
    ):
        query.edit_message_text(
            "La ruta requiere GPS confirmado en recogida y en todas las paradas antes de crearse."
        )
        return RUTA_CONFIRMACION
    link = get_approved_admin_link_for_ally(ally_id)
    admin_id_snapshot = link["admin_id"] if link else None
    try:
        route_id = create_route(
            ally_id=ally_id,
            pickup_location_id=pickup_location_id,
            pickup_address=pickup_address,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            total_distance_km=total_km,
            distance_fee=precio_info.get("distance_fee", 0),
            additional_stops_fee=precio_info.get("additional_stops_fee", 0),
            total_fee=precio_info.get("total_fee", 0),
            instructions=None,
            ally_admin_id_snapshot=admin_id_snapshot,
        )
    except Exception as e:
        query.edit_message_text("Error al crear la ruta: {}".format(str(e)))
        return RUTA_CONFIRMACION
    if not route_id:
        query.edit_message_text("Error al crear la ruta. Intenta de nuevo.")
        show_main_menu(update, context)
        return ConversationHandler.END
    for i, parada in enumerate(paradas, 1):
        create_route_destination(
            route_id=route_id,
            sequence=i,
            customer_name=parada.get("name") or "",
            customer_phone=parada.get("phone") or "",
            customer_address=parada.get("address") or "",
            customer_city=parada.get("city") or "",
            customer_barrio=parada.get("barrio") or "",
            dropoff_lat=parada.get("lat"),
            dropoff_lng=parada.get("lng"),
        )
    count = publish_route_to_couriers(route_id, ally_id, context, admin_id_override=admin_id_snapshot)
    if count > 0:
        base_msg = "Ruta #{} creada exitosamente.\nPronto un repartidor sera asignado.".format(route_id)
    else:
        base_msg = "Ruta #{} creada. No hay repartidores disponibles en este momento.".format(route_id)
    query.edit_message_text(base_msg)

    # Verificar si hay clientes nuevos para ofrecer guardarlos
    nuevos = [p for p in paradas if not p.get("customer_id")]
    if nuevos:
        # Guardar referencia para el callback
        context.user_data["ruta_nuevos_clientes"] = nuevos
        context.user_data["ruta_ally_id_guardar"] = ally_id
        names_list = "\n".join("- {} ({})".format(p["name"], p["phone"]) for p in nuevos if p.get("name"))
        keyboard = [
            [InlineKeyboardButton("Si, guardar", callback_data="ruta_guardar_clientes_si")],
            [InlineKeyboardButton("No", callback_data="ruta_guardar_clientes_no")],
        ]
        query.message.reply_text(
            "Clientes nuevos en esta ruta:\n{}\n\nDeseas guardarlos para futuros pedidos?".format(names_list),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return RUTA_GUARDAR_CLIENTES

    context.user_data.clear()
    show_main_menu(update, context)
    return ConversationHandler.END


def ruta_guardar_clientes_callback(update, context):
    """Maneja la decision de guardar o no los clientes nuevos de la ruta."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id_guardar")
    nuevos = context.user_data.get("ruta_nuevos_clientes", [])

    if data == "ruta_guardar_clientes_si" and ally_id:
        saved = 0
        for p in nuevos:
            name = p.get("name") or ""
            phone = p.get("phone") or ""
            address = p.get("address") or ""
            if not phone:
                continue
            try:
                existing = get_ally_customer_by_phone(ally_id, phone)
                if existing:
                    customer_id = existing["id"]
                else:
                    customer_id = create_ally_customer(ally_id, name, phone)
                if address:
                    create_customer_address(
                        customer_id, "Principal", address,
                        city=p.get("city") or "",
                        barrio=p.get("barrio") or "",
                        lat=p.get("lat"), lng=p.get("lng"),
                    )
                saved += 1
            except Exception as e:
                print("[WARN] Error guardando cliente de ruta: {}".format(e))
        query.edit_message_text("Se guardaron {} cliente(s) nuevos.".format(saved))
    else:
        query.edit_message_text("Clientes no guardados.")

    context.user_data.clear()
    show_main_menu(update, context)
    return ConversationHandler.END


# Conversacion "Nueva ruta" (multi-parada)
nueva_ruta_conv = ConversationHandler(
    entry_points=[
        MessageHandler(Filters.regex(r'^Nueva ruta$'), nueva_ruta_start),
        CallbackQueryHandler(nueva_ruta_desde_cotizador, pattern=r"^cotizar_ruta_cust_(nuevo|recurrente)$"),
        CallbackQueryHandler(nueva_ruta_desde_menu, pattern=r"^pedido_a_ruta$"),
    ],
    states={
        RUTA_PICKUP_SELECTOR: [
            CallbackQueryHandler(ruta_pickup_selector_callback, pattern=r"^ruta_pickup_(base|lista|nueva)$"),
        ],
        RUTA_PICKUP_LISTA: [
            CallbackQueryHandler(ruta_pickup_lista_callback, pattern=r"^ruta_pickup_(usar_\d+|volver_lista)$"),
        ],
        RUTA_PICKUP_NUEVA_UBICACION: [
            CallbackQueryHandler(ruta_pickup_geo_callback, pattern=r"^ruta_pickup_geo_(si|no)$"),
            MessageHandler(Filters.location, ruta_pickup_nueva_ubicacion_location_handler),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_pickup_nueva_ubicacion_handler),
        ],
        RUTA_PICKUP_NUEVA_DETALLES: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_pickup_nueva_detalles_handler),
        ],
        RUTA_PICKUP_NUEVA_CIUDAD: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_pickup_nueva_ciudad_handler),
        ],
        RUTA_PICKUP_NUEVA_BARRIO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_pickup_nueva_barrio_handler),
        ],
        RUTA_PICKUP_GUARDAR: [
            CallbackQueryHandler(ruta_pickup_guardar_callback, pattern=r"^ruta_pickup_guardar_(si|no)$"),
        ],
        RUTA_PARADA_SELECTOR: [
            CallbackQueryHandler(ruta_parada_selector_callback, pattern=r"^ruta_(cliente_nuevo|sel_cust_\d+)$"),
        ],
        RUTA_PARADA_SEL_DIRECCION: [
            CallbackQueryHandler(ruta_parada_sel_direccion_callback, pattern=r"^ruta_(sel_addr_\d+|addr_nueva)$"),
        ],
        RUTA_PARADA_NOMBRE: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_nombre_handler),
        ],
        RUTA_PARADA_TELEFONO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_telefono_handler),
        ],
        RUTA_PARADA_UBICACION: [
            CallbackQueryHandler(ruta_parada_geo_callback, pattern=r"^ruta_parada_geo_(si|no)$"),
            MessageHandler(Filters.location, ruta_parada_ubicacion_location_handler),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_ubicacion_handler),
        ],
        RUTA_PARADA_DIRECCION: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_direccion_handler),
        ],
        RUTA_PARADA_CIUDAD: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_ciudad_handler),
        ],
        RUTA_PARADA_BARRIO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_barrio_handler),
        ],
        RUTA_MAS_PARADAS: [
            CallbackQueryHandler(ruta_mas_paradas_callback, pattern=r"^ruta_mas_(si|no)$"),
        ],
        RUTA_DISTANCIA_KM: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_distancia_km_handler),
        ],
        RUTA_CONFIRMACION: [
            CallbackQueryHandler(ruta_confirmacion_callback, pattern=r"^ruta_(confirmar|cancelar)$"),
        ],
        RUTA_GUARDAR_CLIENTES: [
            CallbackQueryHandler(ruta_guardar_clientes_callback, pattern=r"^ruta_guardar_clientes_(si|no)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)



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

    status = admin_full.get("status") or "-"
    team_name = admin_full.get("team_name") or "-"
    team_code = admin_full.get("team_code") or "-"

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
            [InlineKeyboardButton("⏳ Repartidores pendientes", callback_data=f"local_couriers_pending_{admin_id}")],
            [InlineKeyboardButton("⏳ Aliados pendientes", callback_data=f"local_allies_pending_{admin_id}")],
            [InlineKeyboardButton("👥 Mi equipo", callback_data=f"local_my_team_{admin_id}")],
            [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos_local_{}".format(admin_id))],
            [InlineKeyboardButton("📋 Nuevo pedido especial", callback_data="admin_nuevo_pedido")],
            [InlineKeyboardButton("👤 Mis clientes", callback_data="admin_mis_clientes")],
            [InlineKeyboardButton("📍 Mis direcciones", callback_data="admin_mis_dirs")],
            [InlineKeyboardButton("💳 Recargas pendientes", callback_data=f"local_recargas_pending_{admin_id}")],
            [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            [InlineKeyboardButton("📝 Solicitudes de cambio", callback_data="admin_change_requests")],
        ]
        update.message.reply_text(
            header +
            "Como Administrador de Plataforma, tu operación está habilitada.\n"
            "Selecciona una opción:",
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
        [InlineKeyboardButton("📋 Nuevo pedido especial", callback_data="admin_nuevo_pedido")],
        [InlineKeyboardButton("👤 Mis clientes", callback_data="admin_mis_clientes")],
        [InlineKeyboardButton("📍 Mis direcciones", callback_data="admin_mis_dirs")],
        [InlineKeyboardButton("💳 Recargas pendientes", callback_data=f"local_recargas_pending_{admin_id}")],
        [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
        [InlineKeyboardButton("🔍 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
        [InlineKeyboardButton("📝 Solicitudes de cambio", callback_data="admin_change_requests")],
        [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
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
        admin_balance = get_admin_balance(admin_id)
        mensaje += f"   Saldo master: ${admin_balance:,}\n\n"

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
    bonus_granted = False
    if nuevo_estado == "APPROVED":
        result = approve_role_registration(update.effective_user.id, "COURIER", courier_id)
        if not result.get("ok"):
            query.answer(result.get("message") or "No se pudo aprobar el repartidor.", show_alert=True)
            return
        bonus_granted = bool(result.get("bonus_granted"))
    else:
        try:
            update_courier_status(courier_id, nuevo_estado, changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            print(f"[ERROR] update_courier_status: {e}")
            query.answer("Error actualizando repartidor. Revisa logs.", show_alert=True)
            return
    _resolve_important_alert(context, "courier_registration_{}".format(courier_id))

    courier = result.get("profile") if nuevo_estado == "APPROVED" else get_courier_by_id(courier_id)
    if not courier:
        query.edit_message_text("No se encontró el repartidor después de actualizar.")
        return

    courier_user_db_id = courier["user_id"]
    full_name = courier["full_name"]

    # Notificar al repartidor si existe get_user_by_id (recomendado).
    # Si no existe, solo omitimos notificación sin romper.
    try:
        u = get_user_by_id(courier_user_db_id)
        courier_telegram_id = u["telegram_id"]

        if accion == "approve":
            msg = _build_role_welcome_message("COURIER", profile=courier, bonus_granted=bonus_granted, reactivated=False)
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
def ensure_terms(update, context, telegram_id: int, role: str) -> bool:
    print(
        f"[DEBUG][terms][ensure] role={role} telegram_id={telegram_id} via_callback={bool(getattr(update, 'callback_query', None))}",
        flush=True,
    )
    tv = get_active_terms_version(role)
    if not tv:
        print(f"[DEBUG][terms][ensure] no_terms_config role={role}", flush=True)
        context.bot.send_message(
            chat_id=telegram_id,
            text="Términos no configurados para este rol. Contacta al soporte de la plataforma."
        )
        return False

    version, url, sha256 = tv
    print(f"[DEBUG][terms][ensure] version={version!r} url={url!r}", flush=True)

    accepted = has_accepted_terms(telegram_id, role, version, sha256)
    print(f"[DEBUG][terms][ensure] already_accepted={accepted}", flush=True)
    if accepted:
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

    valid_terms_url = isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))
    keyboard = []
    if valid_terms_url:
        keyboard.append([InlineKeyboardButton("Leer términos", url=url)])
    else:
        print(f"[WARN][terms] URL invalida para role={role}, version={version}: {url!r}", flush=True)
    keyboard.append(
        [
            InlineKeyboardButton("Acepto", callback_data="terms_accept_{}".format(role)),
            InlineKeyboardButton("No acepto", callback_data="terms_decline_{}".format(role)),
        ]
    )

    if update.callback_query:
        print("[DEBUG][terms][ensure] prompt_sent_via=callback_edit", flush=True)
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        print("[DEBUG][terms][ensure] prompt_sent_via=send_message", flush=True)
        context.bot.send_message(chat_id=telegram_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    return False


def terms_callback(update, context):
    query = update.callback_query
    data = query.data
    telegram_id = query.from_user.id
    query.answer()
    print(
        f"[DEBUG][terms][callback] data={data!r} telegram_id={telegram_id} message_id={getattr(query.message, 'message_id', None)}",
        flush=True,
    )

    if data.startswith("terms_accept_"):
        role = data.split("_", 2)[-1]
        tv = get_active_terms_version(role)
        print(f"[DEBUG][terms][callback] accept role={role} tv_found={bool(tv)}", flush=True)
        if not tv:
            query.edit_message_text("Términos no configurados. Contacta soporte.")
            return

        version, url, sha256 = tv
        save_terms_acceptance(telegram_id, role, version, sha256, query.message.message_id)
        print(f"[DEBUG][terms][callback] acceptance_saved role={role} version={version!r}", flush=True)
        if role == "ALLY":
            query.edit_message_text("Aceptación registrada. Ya puedes continuar con Nuevo pedido.")
            print("[DEBUG][terms][callback] awaiting_manual_nuevo_pedido", flush=True)
            return
        query.edit_message_text("Aceptación registrada. Ya puedes continuar.")
        return

    if data.startswith("terms_decline_"):
        print("[DEBUG][terms][callback] decline", flush=True)
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

    telegram_id = update.effective_user.id

    # Solo procesar si es repartidor aprobado y activo
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

    location = message.location
    lat = location.latitude
    lng = location.longitude

    # Detectar si es live location (tiene live_period)
    live_period = getattr(location, 'live_period', None)

    if live_period or update.edited_message:
        # Es live location (nueva o update) -> actualizar y marcar ONLINE
        if update.message and live_period:
            update_courier_live_location(courier["id"], lat, lng, live_period_seconds=live_period)
        else:
            update_courier_live_location(courier["id"], lat, lng)

        # Verificar llegada al punto de recogida si tiene pedido activo
        try:
            check_courier_arrival_at_pickup(courier["id"], lat, lng, context)
        except Exception as e:
            print("[WARN] check_courier_arrival_at_pickup: {}".format(e))

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
    # Si es ubicacion estatica (pin sin live_period), no hacemos nada


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
            print(f"[WARN] No se pudo notificar expiracion a courier {cid}: {e}")


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
    print("[ERROR][telegram] Excepcion no capturada", flush=True)
    try:
        if update and getattr(update, "effective_user", None):
            print(
                f"[ERROR][telegram] user_id={update.effective_user.id} "
                f"chat_id={getattr(getattr(update, 'effective_chat', None), 'id', None)}",
                flush=True,
            )
        if update and getattr(update, "effective_message", None):
            print(
                f"[ERROR][telegram] text={getattr(update.effective_message, 'text', None)!r}",
                flush=True,
            )
    except Exception as meta_err:
        print(f"[ERROR][telegram] meta_log_failed={meta_err}", flush=True)
    print(traceback.format_exc(), flush=True)


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


def main():
    init_db()
    force_platform_admin(ADMIN_USER_ID)
    ensure_pricing_defaults()
    sync_all_courier_link_statuses()

    if not BOT_TOKEN:
        raise RuntimeError("Falta BOT_TOKEN en variables de entorno.")

    # Log seguro: fingerprint del token para verificar separación DEV/PROD
    token_hash = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:8]
    token_suffix = BOT_TOKEN[-6:] if len(BOT_TOKEN) >= 6 else "***"
    print(f"[BOT] TOKEN fingerprint: hash={token_hash} suffix=...{token_suffix}")
    print(f"[BOT] Ambiente: {ENV}")

    updater = Updater(BOT_TOKEN, use_context=True)
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
    dp.add_handler(CallbackQueryHandler(admin_config_callback, pattern=r"^config_(?!pagos$)"))
    dp.add_handler(CallbackQueryHandler(reference_validation_callback, pattern=r"^ref_"))

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
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_(accept|reject|busy|pickup|delivered|delivered_confirm|delivered_cancel|release|release_reason|release_confirm|release_abort|cancel|find_another|wait_courier|call_courier|confirm_pickup|pinissue)_\d+(?:_.+)?$"))
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_pickupconfirm_(approve|reject)_\d+$"))
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^admin_pinissue_(fin|cancel_courier|cancel_ally)_\d+$"))
    dp.add_handler(CallbackQueryHandler(pedido_incentivo_menu_callback, pattern=r"^pedido_inc_menu_\d+$"))
    dp.add_handler(CallbackQueryHandler(pedido_incentivo_existing_fixed_callback, pattern=r"^pedido_inc_\d+x(1000|1500|2000|3000)$"))
    dp.add_handler(CallbackQueryHandler(offer_suggest_inc_fixed_callback, pattern=r"^offer_inc_\d+x(1500|2000|3000)$"))
    dp.add_handler(CallbackQueryHandler(courier_earnings_callback, pattern=r"^courier_earn_"))
    dp.add_handler(CallbackQueryHandler(courier_activate_callback, pattern=r"^courier_activate$"))
    dp.add_handler(CallbackQueryHandler(courier_deactivate_callback, pattern=r"^courier_deactivate$"))
    dp.add_handler(CallbackQueryHandler(admin_change_requests_callback, pattern=r"^chgreq_"))
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
    dp.add_handler(offer_suggest_inc_conv)  # Incentivo desde sugerencia T+5 (aliado y admin)
    dp.add_handler(ally_clientes_conv)     # Agenda de clientes del Aliado (entry: Mis clientes)
    dp.add_handler(CallbackQueryHandler(ally_bandeja_callback, pattern=r"^alybandeja_"))  # Bandeja solicitudes
    dp.add_handler(CallbackQueryHandler(ally_enlace_refresh_callback, pattern=r"^alyenlace_refresh$"))  # Refrescar Mi enlace
    # Estos tres deben ir ANTES del handler global ^admin_ para que sus entry points no sean interceptados
    dp.add_handler(admin_clientes_conv)    # Agenda de clientes del Admin (entry: admin_mis_clientes)
    dp.add_handler(admin_dirs_conv)        # Gestion ubicaciones de recogida del Admin (entry: admin_mis_dirs)
    dp.add_handler(admin_pedido_conv)      # Pedido especial del Admin (entry: admin_nuevo_pedido)

    dp.add_handler(CallbackQueryHandler(admin_menu_callback, pattern=r"^admin_(?!geo_)"))

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
    dp.add_handler(CallbackQueryHandler(handle_route_callback, pattern=r"^ruta_(aceptar|rechazar|ocupado|entregar|liberar|liberar_motivo|liberar_confirmar|liberar_abort|pinissue)_"))  # callbacks de rutas al courier
    dp.add_handler(CallbackQueryHandler(handle_route_callback, pattern=r"^admin_ruta_pinissue_(fin|cancel_courier|cancel_ally)_"))
    dp.add_handler(CallbackQueryHandler(preview_callback, pattern=r"^preview_"))  # preview oferta
    dp.add_handler(CallbackQueryHandler(ally_block_callback, pattern=r"^ally_block_(block|unblock)_\d+$"))  # bloqueo couriers por aliado
    dp.add_handler(CallbackQueryHandler(handle_rating_callback, pattern=r"^rating_(star|block|skip)_"))  # calificacion post-entrega
    dp.add_handler(clientes_conv)      # /clientes (agenda de clientes)
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

    # -------------------------
    # Registro de Administradores Locales
    # -------------------------
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
            CommandHandler("menu", menu),
            MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú]|men[uú])\s*$'), cancel_por_texto),
        ],
    )
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





