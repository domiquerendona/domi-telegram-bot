# =============================================================================
# handlers/order.py — Flujos de pedidos (nuevo_pedido_conv, admin_pedido_conv, incentivos)
# Extraído de main.py (Fase 2e)
# =============================================================================

import logging
import re
logger = logging.getLogger(__name__)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler, CommandHandler, ConversationHandler,
    Filters, MessageHandler,
)
from handlers.states import (
    PEDIDO_SELECTOR_CLIENTE, PEDIDO_BUSCAR_CLIENTE, PEDIDO_SELECCIONAR_DIRECCION,
    PEDIDO_INSTRUCCIONES_EXTRA, PEDIDO_TIPO_SERVICIO, PEDIDO_NOMBRE,
    PEDIDO_TELEFONO, PEDIDO_UBICACION, PEDIDO_DIRECCION,
    PEDIDO_PICKUP_SELECTOR, PEDIDO_PICKUP_LISTA, PEDIDO_PICKUP_NUEVA_UBICACION,
    PEDIDO_PICKUP_NUEVA_DETALLES, PEDIDO_PICKUP_GUARDAR,
    PEDIDO_REQUIERE_BASE, PEDIDO_VALOR_BASE, PEDIDO_CONFIRMACION,
    PEDIDO_GUARDAR_CLIENTE, PEDIDO_COMPRAS_CANTIDAD, PEDIDO_INCENTIVO_MONTO,
    PEDIDO_PICKUP_NUEVA_CIUDAD, PEDIDO_PICKUP_NUEVA_BARRIO, PEDIDO_VALOR_COMPRA,
    OFFER_SUGGEST_INC_MONTO,
    ROUTE_SUGGEST_INC_MONTO,
    ADMIN_PEDIDO_PICKUP, ADMIN_PEDIDO_CUST_NAME, ADMIN_PEDIDO_CUST_PHONE,
    ADMIN_PEDIDO_CUST_ADDR, ADMIN_PEDIDO_TARIFA, ADMIN_PEDIDO_INSTRUC, ADMIN_PEDIDO_INC_MONTO,
    ADMIN_PEDIDO_COMISION,
    ADMIN_PEDIDO_TEMPLATE_NAME, ADMIN_PEDIDO_USE_TEMPLATE,
    ADMIN_PEDIDO_SEL_CUST, ADMIN_PEDIDO_SEL_CUST_ADDR, ADMIN_PEDIDO_SAVE_PICKUP,
    ADMIN_PEDIDO_PICKUP_DETALLE, ADMIN_PEDIDO_CUST_ADDR_DETALLE,
    PEDIDO_DEDUP_CONFIRM, PEDIDO_GUARDAR_DIR_EXISTENTE,
    ADMIN_PEDIDO_SEL_CUST_BUSCAR, ADMIN_PEDIDO_CUST_DEDUP, ADMIN_PEDIDO_GUARDAR_CUST,
    PEDIDO_PARADA_EXTRA_NOMBRE, PEDIDO_PARADA_EXTRA_TELEFONO, PEDIDO_PARADA_EXTRA_DIRECCION,
    PEDIDO_GUARDAR_DIR_PARKING, PEDIDO_GUARDAR_CUST_PARKING, ADMIN_PEDIDO_GUARDAR_PARKING,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER, _OPTIONS_HINT,
    _handle_text_field_input, _geo_siguiente_o_gps, _maybe_cache_confirmed_geo,
    _mostrar_confirmacion_geocode,
    cancel_conversacion, cancel_por_texto, ensure_terms,
    show_main_menu, show_flow_menu, _fmt_pesos, build_offer_demand_badge_text,
    build_offer_suggestion_button_row,
)
from order_delivery import (
    publish_order_to_couriers,
    repost_order_to_couriers,
    repost_route_to_couriers,
    publish_route_to_couriers,
    build_market_launch_status_text,
    build_courier_order_preview_text,
    build_order_price_summary_text,
    build_order_creation_summary_text,
    build_route_creation_summary_text,
)
from services import (
    ensure_user, get_user_by_telegram_id, get_ally_by_user_id,
    get_approved_admin_link_for_ally, get_admin_link_for_ally,
    get_platform_admin, check_service_fee_available,
    ensure_platform_temp_coverage_for_ally, user_has_platform_admin,
    get_admin_by_id, get_user_by_id,
    list_ally_customers, search_ally_customers, get_ally_customer_by_id,
    get_ally_customer_by_phone, create_ally_customer, create_customer_address,
    list_customer_addresses, get_customer_address_by_id,
    find_matching_customer_address, update_customer_address_coords,
    get_last_order_by_ally, get_recent_delivery_addresses_for_ally,
    get_default_ally_location, get_ally_locations, get_ally_location_by_id,
    update_ally_location_coords, create_ally_location,
    get_buy_pricing_config, quote_order_from_inputs, build_order_pricing_breakdown,
    has_valid_coords, get_link_cache, expand_short_url,
    extract_lat_lng_from_text, upsert_link_cache, extract_place_id_from_url,
    can_call_google_today, google_place_details,
    create_order, get_order_by_id, increment_pickup_usage,
    ally_get_order_for_incentive, ally_increment_order_incentive,
    admin_increment_order_incentive,
    add_route_incentive, get_route_by_id,
    create_route, create_route_destination,
    calcular_precio_ruta_inteligente, optimizar_orden_paradas,
    get_ally_link_balance,
    get_admin_by_telegram_id, get_admin_locations, get_admin_location_by_id,
    create_admin_location, increment_admin_location_usage, update_admin_location,
    list_admin_customers, search_admin_customers, get_admin_customer_by_id,
    get_admin_customer_address_by_id, list_admin_customer_addresses,
    get_admin_customer_by_phone, create_admin_customer, create_admin_customer_address,
    update_admin_customer_address, find_matching_admin_customer_address,
    upsert_customer_address_for_agenda, upsert_admin_customer_address_for_agenda,
    increment_ally_customer_usage, increment_customer_address_usage,
    increment_admin_customer_usage, increment_admin_customer_address_usage,
    get_ally_form_request_by_id, update_ally_form_request_status,
    mark_ally_form_request_converted,
    get_ally_by_id, compute_ally_subsidy, PARKING_FEE_AMOUNT, set_address_parking_status,
    get_ally_parking_fee_enabled,
    get_active_terms_version, save_terms_acceptance,
    resolve_location, resolve_location_next, save_confirmed_geocoding,
    get_fee_config, build_offer_demand_preview,
    save_order_template, list_order_templates, get_order_template_by_id,
    increment_order_template_usage, delete_order_template,
    get_admin_balance, get_sociedad_balance,
    resolve_owned_admin_actor, increment_setting_counter,
)


PEDIDO_BASE_PRESET_AMOUNTS = (20000, 50000, 100000, 200000)
PEDIDO_BASE_CALLBACK_PATTERN = (
    r"^pedido_base_(" + "|".join(str(amount) for amount in PEDIDO_BASE_PRESET_AMOUNTS) + r"|otro)$"
)
PICKUP_PREVIEW_CONFIRM_CALLBACK = "pickup_preview_confirm"
PICKUP_PREVIEW_CHANGE_CALLBACK = "pickup_preview_change"
PICKUP_PREVIEW_CALLBACK_PATTERN = r"^pickup_preview_(confirm|change)$"


def _append_success_followup(success_text, followup_text):
    """Concatena un seguimiento corto sin perder el resumen principal del servicio."""
    if not followup_text:
        return success_text
    return "{}\n\n{}".format(success_text, followup_text)


def _order_city_hint(context):
    """Extrae barrio+ciudad del aliado o admin en sesion para mejorar geocoding."""
    ally = context.user_data.get("ally")
    if ally:
        parts = [p for p in [ally.get("barrio"), ally.get("city")] if p]
        if parts:
            return ", ".join(parts)
    # Para flujos de admin: admin_id disponible pero sin row completo en user_data
    # No intentamos BD aqui para mantener el helper rapido y sin IO
    return None


def _pedido_is_system_address(text):
    """Detecta direcciones no legibles para humanos: GPS, coords, links o placeholders."""
    cleaned = " ".join(str(text or "").strip().split())
    if not cleaned:
        return True
    lowered = cleaned.lower()
    if lowered in {
        "ubicacion enviada desde telegram",
        "ubicacion enviada desde telegram.",
        "ubicacion pendiente de detallar",
        "direccion pendiente de detallar",
        "sin direccion",
    }:
        return True
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return True
    if re.match(r"^gps\s*\(\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\)$", cleaned, re.IGNORECASE):
        return True
    if re.match(r"^-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?$", cleaned):
        return True
    return False


def _pedido_visible_address_text(text, fallback="Ubicacion pendiente de detallar"):
    """Normaliza el texto mostrado al admin para no exponer coords crudas como direccion."""
    cleaned = " ".join(str(text or "").strip().split())
    if _pedido_is_system_address(cleaned):
        return fallback
    return cleaned


def _pedido_pickup_option_text(location):
    """Construye el texto visible de un pickup guardado evitando GPS/coords crudas."""
    label = _pedido_visible_address_text(location.get("label"), fallback="")
    if label:
        return label[:60]
    return _pedido_visible_address_text(
        location.get("address"),
        fallback="Ubicacion pendiente de detallar",
    )[:60]


def _pedido_customer_address_button_text(address):
    """Construye el boton visible de una direccion de cliente sin mostrar coords crudas."""
    raw_label = " ".join(str(address.get("label") or "").strip().split())
    label = raw_label if raw_label and not _pedido_is_system_address(raw_label) else "Sin etiqueta"
    visible_address = _pedido_visible_address_text(
        address.get("address_text"),
        fallback="Ubicacion pendiente de detallar",
    )
    parking_status = address.get("parking_status", "NOT_ASKED")
    parking_tag = " [P]" if parking_status in ("ALLY_YES", "ADMIN_YES") else ""
    return "{}{}: {}".format(label[:30], parking_tag, visible_address[:25])


def _pedido_reply_text(target, text, reply_markup=None):
    """Envia texto a query o mensaje sin duplicar ramificaciones del flujo."""
    if hasattr(target, "edit_message_text"):
        target.edit_message_text(text, reply_markup=reply_markup)
    elif hasattr(target, "reply_text"):
        target.reply_text(text, reply_markup=reply_markup)
    elif hasattr(target, "message") and target.message:
        target.message.reply_text(text, reply_markup=reply_markup)


def _admin_pedido_render_preview(target, context):
    """Vuelve al preview del pedido especial cuando se edita desde el resumen."""
    context.user_data.pop("admin_ped_edit_from_preview", None)
    text, markup = _admin_ped_preview_text(context.user_data)
    _pedido_reply_text(target, text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def _admin_pedido_render_pickup_save_prompt(target, context):
    """Pregunta si la nueva direccion humana de recogida debe guardarse en Mis Dirs."""
    keyboard = [[
        InlineKeyboardButton("Si, guardar", callback_data="admin_pedido_save_pickup_si"),
        InlineKeyboardButton("No, continuar", callback_data="admin_pedido_save_pickup_no"),
    ]]
    _pedido_reply_text(
        target,
        "Punto de recogida: {}\n\nGuardar esta direccion en Mis Dirs para futuros pedidos?".format(
            context.user_data.get("admin_ped_pickup_addr", "")
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_SAVE_PICKUP


def _admin_pedido_prompt_pickup_detail(target, context):
    """Pide la direccion visible final de recogida despues de confirmar el punto GPS."""
    pending = context.user_data.get("admin_ped_geo_pickup_pending") or {}
    if pending.get("location_id"):
        text = (
            "Esta direccion guardada estaba solo con coordenadas.\n\n"
            "Escribe la direccion visible correcta de recogida.\n"
            "No envíes GPS, links ni coordenadas."
        )
    else:
        text = (
            "Punto de recogida confirmado.\n\n"
            "Ahora escribe la direccion visible exacta de recogida para este pedido.\n"
            "No envíes GPS, links ni coordenadas."
        )
    _pedido_reply_text(target, text)
    return ADMIN_PEDIDO_PICKUP_DETALLE


def _admin_pedido_prompt_delivery_detail(target, context):
    """Pide la direccion visible final de entrega despues de confirmar el punto GPS."""
    pending = context.user_data.get("admin_ped_geo_cust_pending") or {}
    if pending.get("address_id"):
        text = (
            "Esta direccion guardada estaba solo con coordenadas.\n\n"
            "Escribe la direccion visible correcta de entrega.\n"
            "No envíes GPS, links ni coordenadas."
        )
    else:
        text = (
            "Punto de entrega confirmado.\n\n"
            "Ahora escribe la direccion visible exacta de entrega para este pedido.\n"
            "No envíes GPS, links ni coordenadas."
        )
    _pedido_reply_text(target, text)
    return ADMIN_PEDIDO_CUST_ADDR_DETALLE


def _pedido_human_label(label, fallback_text):
    """Conserva etiquetas humanas existentes y repara solo las que quedaron de sistema."""
    cleaned_label = " ".join(str(label or "").strip().split())
    if not cleaned_label or _pedido_is_system_address(cleaned_label):
        return fallback_text[:80]
    return cleaned_label[:80]


def _pedido_requires_human_detail(pending):
    """Pide detalle humano extra solo cuando la entrada original no era una direccion legible."""
    source = str((pending or {}).get("source") or "").lower()
    if source in {
        "gps",
        "telegram_pin",
        "saved_location",
        "saved_address",
        "coords",
        "regex",
        "link",
        "cache",
        "places",
        "places_api",
    }:
        return True
    original_text = " ".join(str((pending or {}).get("original_text") or "").strip().split())
    if original_text and _pedido_is_system_address(original_text):
        return True
    return False


def _pedido_merge_instruction_text(base_text, extra_text):
    """Une nota base + texto adicional sin crear saltos vacios ni duplicar ramas."""
    base = " ".join(str(base_text or "").strip().split())
    extra = " ".join(str(extra_text or "").strip().split())
    if base and extra:
        return "{}\n{}".format(base, extra)
    return extra or base


def _pedido_prompt_notes_or_continue(update_or_query, context, edit):
    """Muestra nota de direccion si existe; si no, continua con pickup o preview."""
    nota_direccion = context.user_data.get("nota_direccion", "")
    if nota_direccion:
        keyboard = [
            [InlineKeyboardButton("Si", callback_data="pedido_instr_si")],
            [InlineKeyboardButton("No", callback_data="pedido_instr_no")],
        ]
        _pedido_reply_text(
            update_or_query,
            "Nota para el repartidor:\n{}\n\n"
            "Deseas agregar instrucciones adicionales para este pedido?".format(
                nota_direccion
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return PEDIDO_INSTRUCCIONES_EXTRA
    if context.user_data.pop("pedido_edit_from_preview", False):
        return mostrar_resumen_confirmacion(update_or_query, context, edit=edit)
    return mostrar_selector_pickup(update_or_query, context, edit=edit)


def _pedido_start_pickup_fix(target, context, location):
    """Pide texto humano cuando un pickup guardado existe pero solo muestra GPS/coords."""
    context.user_data["pedido_pending_pickup_fix"] = {
        "location_id": location.get("id"),
        "city": location.get("city") or "",
        "barrio": location.get("barrio") or "",
        "phone": location.get("phone"),
        "lat": location.get("lat"),
        "lng": location.get("lng"),
    }
    _pedido_reply_text(
        target,
        "Esta direccion guardada estaba solo con coordenadas.\n\n"
        "Escribe la direccion visible correcta de recogida.\n"
        "No envies GPS, links ni coordenadas.",
    )
    return PEDIDO_PICKUP_NUEVA_DETALLES


def _pedido_base_keyboard():
    """Construye el teclado de montos fijos para base requerida."""
    keyboard = []
    current_row = []
    for amount in PEDIDO_BASE_PRESET_AMOUNTS:
        current_row.append(
            InlineKeyboardButton(_fmt_pesos(amount), callback_data=f"pedido_base_{amount}")
        )
        if len(current_row) == 2:
            keyboard.append(current_row)
            current_row = []
    if current_row:
        keyboard.append(current_row)
    keyboard.append([InlineKeyboardButton("Otro valor", callback_data="pedido_base_otro")])
    return InlineKeyboardMarkup(keyboard)


def _pedido_base_flow_kind(context):
    """Detecta que flujo esta usando el sub-paso compartido de base requerida."""
    if context.user_data.get("admin_ped_admin_id"):
        return "admin_pedido"
    if context.user_data.get("ruta_ally_id"):
        return "ruta"
    return "pedido"


def _pedido_base_storage_keys(context):
    """Retorna las claves de user_data segun el flujo activo."""
    flow_kind = _pedido_base_flow_kind(context)
    if flow_kind == "admin_pedido":
        return "admin_ped_requires_cash", "admin_ped_cash_required_amount"
    if flow_kind == "ruta":
        return "ruta_requires_cash", "ruta_cash_required_amount"
    return "requires_cash", "cash_required_amount"


def _pedido_set_base_requirement(context, requires_cash, cash_amount):
    """Guarda la decision de base requerida en las claves del flujo activo."""
    requires_key, amount_key = _pedido_base_storage_keys(context)
    context.user_data[requires_key] = bool(requires_cash)
    context.user_data[amount_key] = int(cash_amount or 0)


def _pedido_payment_method_from_base(requires_cash, cash_amount):
    """Mapea base requerida a un payment_method compatible con la oferta actual."""
    if requires_cash and int(cash_amount or 0) > 0:
        return "CASH_CONFIRMED"
    return "UNCONFIRMED"


def _pedido_continue_after_base(query_or_update, context, edit=False):
    """Retoma el flujo correcto despues de confirmar la base requerida."""
    flow_kind = _pedido_base_flow_kind(context)
    if flow_kind == "admin_pedido":
        return _admin_pedido_calcular_preview(query_or_update, context, edit=edit)
    if flow_kind == "ruta":
        route_continue = globals().get("_ruta_continue_after_base")
        if route_continue is None:
            # Lazy import para evitar dependencia circular: route.py reutiliza estos callbacks.
            from handlers.route import _ruta_continue_after_base as route_continue
        return route_continue(query_or_update, context, edit=edit)
    return calcular_cotizacion_y_confirmar(query_or_update, context, edit=edit)


def nuevo_pedido_desde_cotizador(update, context):
    """Entry point de nuevo_pedido_conv cuando el aliado confirma pedido desde el cotizador."""
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

    if not ensure_terms(update, context, user.id, role="ALLY"):
        return ConversationHandler.END

    # Transferir prefill del cotizador a claves del flujo de pedido
    context.user_data["ally_id"] = ally["id"]
    context.user_data["active_ally_id"] = ally["id"]
    context.user_data["ally"] = ally
    context.user_data["pickup_lat"] = context.user_data.pop("prefill_pickup_lat", None)
    context.user_data["pickup_lng"] = context.user_data.pop("prefill_pickup_lng", None)
    context.user_data["dropoff_lat"] = context.user_data.pop("prefill_dropoff_lat", None)
    context.user_data["dropoff_lng"] = context.user_data.pop("prefill_dropoff_lng", None)
    context.user_data["cotizador_prefill_dropoff"] = True

    if query.data == "cotizar_cust_recurrente":
        all_customers = list_ally_customers(ally["id"], limit=50)
        if not all_customers:
            query.edit_message_text("No tienes clientes guardados.\n\nEscribe el nombre del cliente:")
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE
        recent = all_customers[:10]
        keyboard = []
        for c in recent:
            keyboard.append([InlineKeyboardButton(
                f"{c['name']} - {c['phone']}",
                callback_data=f"pedido_sel_cust_{c['id']}"
            )])
        keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="pedido_buscar_cliente")])
        if len(all_customers) > 10:
            keyboard.append([InlineKeyboardButton(
                f"Ver todos ({len(all_customers)})", callback_data="pedido_ver_todos"
            )])
        keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])
        query.edit_message_text(
            "CLIENTES RECURRENTES\n\nSelecciona un cliente:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return PEDIDO_SELECTOR_CLIENTE

    # cotizar_cust_nuevo
    query.edit_message_text("Escribe el nombre del cliente:")
    context.user_data["is_new_customer"] = True
    return PEDIDO_NOMBRE


def _build_nuevo_pedido_keyboard(ally_id):
    keyboard = [
        [InlineKeyboardButton("Cliente recurrente", callback_data="pedido_cliente_recurrente")],
        [InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")],
    ]
    last_order = get_last_order_by_ally(ally_id)
    if last_order:
        keyboard.append([InlineKeyboardButton("Repetir ultimo pedido", callback_data="pedido_repetir_ultimo")])
    keyboard.append([InlineKeyboardButton("Varias entregas (ruta)", callback_data="pedido_a_ruta")])
    return keyboard


def nuevo_pedido(update, context):
    user = update.effective_user
    message = update.effective_message
    try:
        logger.debug(
            "[nuevo_pedido] entry user_id=%s chat_id=%s text=%r",
            getattr(user, 'id', None),
            getattr(getattr(message, 'chat', None), 'id', None),
            getattr(message, 'text', None),
        )

        ensure_user(user.id, user.username)
        db_user = get_user_by_telegram_id(user.id)
        logger.debug("[nuevo_pedido] db_user_found=%s user_id=%s", bool(db_user), getattr(user, 'id', None))

        if not db_user:
            if message:
                message.reply_text("Aun no estas registrado en el sistema. Usa /start primero.")
            return ConversationHandler.END

        ally = get_ally_by_user_id(db_user["id"])
        logger.debug("[nuevo_pedido] ally_found=%s ally_status=%s", bool(ally), ally['status'] if ally else None)
        if not ally:
            if message:
                message.reply_text(
                    "Aun no estas registrado como aliado.\n"
                    "Si tienes un negocio, registrate con /soy_aliado."
                )
            return ConversationHandler.END

        if ally["status"] != "APPROVED":
            if message:
                message.reply_text(
                    "Tu registro como aliado todavia no ha sido aprobado por el administrador.\n"
                    "Cuando tu estado sea APPROVED podras crear pedidos con /nuevo_pedido."
                )
            return ConversationHandler.END


        # Verificar saldo ANTES de iniciar el flujo para no perder tiempo
        _admin_link_early = get_approved_admin_link_for_ally(ally["id"])
        _admin_id_early = _admin_link_early["admin_id"] if _admin_link_early else None
        if not _admin_id_early:
            _platform_admin_early = get_platform_admin()
            _admin_id_early = _platform_admin_early["id"] if _platform_admin_early else None
        if _admin_id_early:
            _fee_ok, _fee_code = check_service_fee_available(
                target_type="ALLY",
                target_id=ally["id"],
                admin_id=_admin_id_early,
            )
            if not _fee_ok:
                if message:
                    if _fee_code == "ADMIN_SIN_SALDO":
                        message.reply_text(
                            "Tu administrador no tiene saldo suficiente para operar. Contacta a tu admin o recarga con plataforma."
                        )
                    else:
                        message.reply_text(
                            "No tienes saldo suficiente para crear un pedido. Recarga para continuar."
                        )
                return ConversationHandler.END
        if not ensure_terms(update, context, user.id, role="ALLY"):
            logger.debug("[nuevo_pedido] blocked_by_terms=True")
            return ConversationHandler.END

        context.user_data.clear()
        context.user_data["ally_id"] = ally["id"]
        context.user_data["active_ally_id"] = ally["id"]
        context.user_data["ally"] = ally

        show_flow_menu(update, context, "Iniciando nuevo pedido...")

        if message:
            message.reply_text(
                "CREAR NUEVO PEDIDO\n\n"
                "Selecciona una opcion:",
                reply_markup=InlineKeyboardMarkup(_build_nuevo_pedido_keyboard(ally["id"]))
            )
        return PEDIDO_SELECTOR_CLIENTE
    except Exception as e:
        logger.exception("[nuevo_pedido] %s: %s", type(e).__name__, e)
        if message:
            message.reply_text("Se produjo un error al iniciar el pedido. Intenta /nuevo_pedido.")
        return ConversationHandler.END

def pedido_selector_cliente_callback(update, context):
    """Maneja la seleccion de tipo de cliente en /nuevo_pedido."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally_id = context.user_data.get("active_ally_id")
    if not ally_id:
        query.edit_message_text("No hay un aliado activo. Regresa al menu e inicia el pedido nuevamente.")
        return ConversationHandler.END

    if data == "pedido_cliente_recurrente":
        # Mostrar lista de clientes recurrentes
        all_customers = list_ally_customers(ally_id, limit=50)
        if not all_customers:
            query.edit_message_text(
                "No tienes clientes guardados.\n\n"
                "Escribe el nombre del cliente para crear el pedido:"
            )
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE

        recent = all_customers[:10]
        keyboard = []
        for c in recent:
            btn_text = f"{c['name']} - {c['phone']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_cust_{c['id']}")])

        keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="pedido_buscar_cliente")])
        if len(all_customers) > 10:
            keyboard.append([InlineKeyboardButton(
                f"Ver todos ({len(all_customers)})", callback_data="pedido_ver_todos"
            )])
        keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "CLIENTES RECURRENTES\n\n"
            "Selecciona un cliente:",
            reply_markup=reply_markup
        )
        return PEDIDO_SELECTOR_CLIENTE

    elif data == "pedido_ver_todos":
        all_customers = list_ally_customers(ally_id, limit=50)
        sorted_customers = sorted(all_customers, key=lambda c: (c["name"] or "").lower())
        keyboard = []
        for c in sorted_customers:
            btn_text = f"{c['name']} - {c['phone']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_cust_{c['id']}")])
        keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="pedido_buscar_cliente")])
        keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])
        query.edit_message_text(
            f"TODOS LOS CLIENTES ({len(sorted_customers)})\n\n"
            "Selecciona un cliente:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return PEDIDO_SELECTOR_CLIENTE

    elif data == "pedido_cliente_nuevo":
        # Limpiar datos residuales de flujos anteriores para evitar reusar ubicacion/cliente
        for _k in ("customer_id", "customer_address", "customer_address_id",
                   "dropoff_lat", "dropoff_lng", "customer_city", "customer_barrio",
                   "customer_name", "customer_phone"):
            context.user_data.pop(_k, None)
        query.edit_message_text("Escribe el nombre del cliente:")
        context.user_data["is_new_customer"] = True
        return PEDIDO_NOMBRE

    elif data == "pedido_repetir_ultimo":
        last_order = get_last_order_by_ally(ally_id)
        if last_order:
            context.user_data["customer_name"] = last_order["customer_name"]
            context.user_data["customer_phone"] = last_order["customer_phone"]
            context.user_data["customer_address"] = last_order["customer_address"]
            context.user_data["customer_city"] = last_order["customer_city"] or ""
            context.user_data["customer_barrio"] = last_order["customer_barrio"] or ""
            context.user_data["dropoff_lat"] = last_order["dropoff_lat"]
            context.user_data["dropoff_lng"] = last_order["dropoff_lng"]
            context.user_data["is_new_customer"] = False
            has_dropoff = has_valid_coords(
                context.user_data["dropoff_lat"],
                context.user_data["dropoff_lng"],
            )
            logger.info(
                "[pedido_repetir_ultimo] ally_id=%s order_id=%s has_dropoff=%s",
                ally_id,
                last_order["id"],
                has_dropoff,
            )

            if not has_dropoff:
                query.edit_message_text(
                    "Ese ultimo pedido no tiene ubicacion confirmada en la entrega.\n\n"
                    "Envia la ubicacion valida para continuar."
                )
                return PEDIDO_UBICACION

            # Ir al selector de pickup
            return mostrar_selector_pickup(query, context, edit=True)
        else:
            query.edit_message_text("No hay pedidos anteriores. Escribe el nombre del cliente:")
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE

    elif data == "pedido_buscar_cliente":
        query.edit_message_text(
            "Escribe el nombre o telefono del cliente a buscar.\n"
            "Escribe '.' para ver todos:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver", callback_data="pedido_cliente_recurrente")]
            ])
        )
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
            btn_text = _pedido_customer_address_button_text(addr)
            keyboard.append([InlineKeyboardButton(btn_text, callback_data="pedido_sel_addr_{}".format(addr["id"]))])

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
    ally_id = context.user_data.get("active_ally_id")

    if not ally_id:
        update.message.reply_text("No hay un aliado activo. Regresa al menu e inicia el pedido nuevamente.")
        return ConversationHandler.END

    if not query_text:
        update.message.reply_text("Escribe al menos un caracter para buscar.")
        return PEDIDO_BUSCAR_CLIENTE
    if len(query_text) > 60:
        update.message.reply_text("El texto es muy largo. Intenta con menos caracteres.")
        return PEDIDO_BUSCAR_CLIENTE

    results = search_ally_customers(ally_id, query_text, limit=10)
    if not results:
        recientes = list_ally_customers(ally_id, limit=5)
        if recientes:
            keyboard = []
            for c in recientes:
                btn_text = f"{c['name']} - {c['phone']}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_cust_{c['id']}")])
            keyboard.append([InlineKeyboardButton("Buscar de nuevo", callback_data="pedido_buscar_cliente")])
            keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])
            update.message.reply_text(
                f"No encontre clientes con '{query_text}'.\n\n"
                "Tus clientes recientes:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return PEDIDO_SELECTOR_CLIENTE
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

    keyboard.append([InlineKeyboardButton("Buscar de nuevo", callback_data="pedido_buscar_cliente")])
    keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    truncado = " (mostrando 10)" if len(results) >= 10 else ""
    update.message.reply_text(
        f"Resultados para '{query_text}'{truncado}:\n\nSelecciona un cliente:",
        reply_markup=reply_markup
    )
    return PEDIDO_SELECTOR_CLIENTE


def pedido_seleccionar_direccion_callback(update, context):
    """Maneja la seleccion de direccion del cliente."""
    query = update.callback_query
    query.answer()
    data = query.data
    if data != "pedido_nueva_dir":
        context.user_data.pop("pedido_pending_address_fix", None)

    if data == "pedido_nueva_dir":
        context.user_data["pedido_parking_fee"] = 0
        query.edit_message_text(
            "Escribe la nueva direccion de entrega (nombre del lugar o calle),\n"
            "o envia un pin de ubicacion de Telegram."
        )
        return PEDIDO_UBICACION

    elif data == "guardar_dir_cliente_si":
        # Guardar la direccion del cliente
        customer_id = context.user_data.get("customer_id")
        address_text = context.user_data.get("customer_address", "")
        lat = context.user_data.get("dropoff_lat")
        lng = context.user_data.get("dropoff_lng")
        if address_text and not has_valid_coords(lat, lng):
            query.edit_message_text(
                "Esta direccion no tiene ubicacion confirmada.\n\n"
                "Envia un PIN de Telegram o un enlace valido para guardarla y usarla en pedidos."
            )
            return PEDIDO_UBICACION
        if customer_id and address_text:
            save_result = upsert_customer_address_for_agenda(
                customer_id=customer_id,
                label=address_text[:30],
                address_text=address_text,
                city=context.user_data.get("customer_city", ""),
                barrio=context.user_data.get("customer_barrio", ""),
                lat=lat,
                lng=lng,
            )
            ally_id_ctx = context.user_data.get("ally_id")
            parking_enabled = get_ally_parking_fee_enabled(ally_id_ctx) if ally_id_ctx else False
            if save_result["action"] == "created" and parking_enabled:
                address_id = save_result["address_id"]
                context.user_data["pedido_parking_address_id"] = address_id
                keyboard = [
                    [InlineKeyboardButton("Si, hay dificultad para parquear", callback_data="pedido_dir_parking_si")],
                    [InlineKeyboardButton("No / No lo se", callback_data="pedido_dir_parking_no")],
                ]
                query.edit_message_text(
                    "Direccion guardada.\n\n"
                    "En ese punto de entrega hay dificultad para parquear moto o bicicleta?\n"
                    "(zona restringida, riesgo de comparendo o sin lugar seguro para dejar el vehiculo)",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return PEDIDO_GUARDAR_DIR_PARKING
            if save_result["action"] == "coords_updated":
                query.edit_message_text("La direccion ya existia y se completo su geolocalizacion. Continuamos.")
            elif save_result["action"] == "existing":
                query.edit_message_text("La direccion ya estaba guardada. Continuamos.")
            else:
                query.edit_message_text("Direccion guardada. Continuamos.")
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
            query.edit_message_text(
                "Direccion no encontrada. Escribe la direccion de entrega (nombre del lugar o calle),\n"
                "o envia un pin de ubicacion de Telegram."
            )
            return PEDIDO_UBICACION

        context.user_data["customer_address_id"] = address_id
        context.user_data["customer_address"] = address["address_text"]
        context.user_data["customer_city"] = address["city"] or ""
        context.user_data["customer_barrio"] = address["barrio"] or ""
        context.user_data["dropoff_lat"] = address["lat"]
        context.user_data["dropoff_lng"] = address["lng"]
        try:
            increment_customer_address_usage(address_id, customer_id)
            increment_ally_customer_usage(customer_id)
        except Exception:
            pass

        ally_id_ctx = context.user_data.get("ally_id")
        parking_enabled_ctx = get_ally_parking_fee_enabled(ally_id_ctx) if ally_id_ctx else False
        parking_status = "NOT_ASKED"
        if parking_enabled_ctx:
            try:
                parking_status = address["parking_status"]
            except (KeyError, IndexError):
                parking_status = "NOT_ASKED"
            context.user_data["pedido_parking_fee"] = PARKING_FEE_AMOUNT if parking_status in ("ALLY_YES", "ADMIN_YES") else 0
        else:
            context.user_data["pedido_parking_fee"] = 0

        if not has_valid_coords(address["lat"], address["lng"]):
            query.edit_message_text(
                "Esta direccion guardada no tiene ubicacion confirmada.\n\n"
                "Corrigela en tu agenda o envia una ubicacion nueva para continuar."
            )
            return PEDIDO_UBICACION

        if _pedido_is_system_address(address["address_text"]):
            context.user_data["pedido_pending_address_fix"] = {
                "address_id": address_id,
                "customer_id": customer_id,
                "label": address.get("label") or "",
                "city": address["city"] or "",
                "barrio": address["barrio"] or "",
                "notes": address["notes"] or "",
                "parking_status": parking_status,
                "lat": address["lat"],
                "lng": address["lng"],
            }
            query.edit_message_text(
                "Esta direccion guardada estaba solo con coordenadas.\n\n"
                "Escribe la direccion visible correcta de entrega.\n"
                "No envies GPS, links ni coordenadas."
            )
            return PEDIDO_DIRECCION

        # Guardar nota de la direccion si existe
        nota_direccion = address["notes"] or ""
        context.user_data["nota_direccion"] = nota_direccion

        return _pedido_prompt_notes_or_continue(query, context, edit=True)

    return PEDIDO_SELECCIONAR_DIRECCION


def pedido_instrucciones_callback(update, context):
    """Maneja la respuesta sobre instrucciones adicionales."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pedido_instr_si":
        query.edit_message_text(
            "Escribe las instrucciones adicionales para el repartidor:"
        )
        return PEDIDO_INSTRUCCIONES_EXTRA

    elif data == "pedido_instr_no":
        # Usar solo la nota de la direccion como instrucciones finales
        nota_direccion = context.user_data.get("nota_direccion", "")
        context.user_data["instructions"] = _pedido_merge_instruction_text(
            nota_direccion,
            "",
        )
        if context.user_data.pop("pedido_edit_from_preview", False):
            return mostrar_resumen_confirmacion(query, context, edit=True)
        return mostrar_selector_pickup(query, context, edit=True)

    return PEDIDO_INSTRUCCIONES_EXTRA


def pedido_instrucciones_text(update, context):
    """Captura las instrucciones adicionales escritas por el aliado."""
    texto_adicional = update.message.text.strip()
    nota_direccion = context.user_data.get("nota_direccion", "")
    context.user_data["instructions"] = _pedido_merge_instruction_text(
        nota_direccion,
        texto_adicional,
    )

    if context.user_data.pop("pedido_edit_from_preview", False):
        return mostrar_resumen_confirmacion_msg(update, context)
    return mostrar_selector_pickup(update, context, edit=False)


def get_tipo_servicio_keyboard():
    """Retorna InlineKeyboardMarkup con opciones de tipo de servicio."""
    keyboard = [
        [InlineKeyboardButton("Entrega", callback_data="pedido_tipo_entrega")],
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
        "pedido_tipo_entrega": "Entrega",
        # Compatibilidad con mensajes viejos en chats ya abiertos
        "pedido_tipo_entrega_rapida": "Entrega",
        "pedido_tipo_domicilio": "Entrega",
        "pedido_tipo_mensajeria": "Entrega",
        "pedido_tipo_recogida": "Recogida en tienda",
        "pedido_tipo_compras": "Compras",
    }

    if data not in tipos_map:
        query.edit_message_text("Opcion no valida. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END

    context.user_data["service_type"] = tipos_map[data]

    # Si es Compras, pedir lista de productos
    if data == "pedido_tipo_compras":
        buy_config = get_buy_pricing_config()
        free_th = buy_config.get("free_threshold", 2)
        extra_fee = buy_config.get("extra_fee", 1000)
        extra_fee_fmt = f"${extra_fee:,}".replace(",", ".")
        query.edit_message_text(
            "🛒 COMPRAS\n\n"
            "Escribe la lista de productos con sus cantidades.\n\n"
            "Ejemplo:\n"
            "3 platanos, 2 bolsas de leche, 1 jabon\n\n"
            f"Los primeros {free_th} productos no tienen recargo.\n"
            f"Cada producto adicional: +{extra_fee_fmt}"
        )
        return PEDIDO_COMPRAS_CANTIDAD

    # Si viene de cliente recurrente pero faltan campos, rehidratar desde BD
    customer_id = context.user_data.get("customer_id")
    ally_id = context.user_data.get("active_ally_id")
    if customer_id and ally_id:
        if not context.user_data.get("customer_name") or not context.user_data.get("customer_phone"):
            customer = get_ally_customer_by_id(customer_id, ally_id)
            if customer:
                if not context.user_data.get("customer_name"):
                    context.user_data["customer_name"] = customer["name"] or ""
                if not context.user_data.get("customer_phone"):
                    context.user_data["customer_phone"] = customer["phone"] or ""

    # Verificar si ya tenemos todos los datos del cliente
    has_name = context.user_data.get("customer_name")
    has_phone = context.user_data.get("customer_phone")
    has_address = context.user_data.get("customer_address")

    if has_name and has_phone and has_address:
        # Ya tenemos datos del cliente, preguntar por base requerida
        return mostrar_pregunta_base(query, context, edit=True)
    else:
        # Si ya se selecciono un cliente recurrente, nunca re-pedir el nombre por defecto
        if customer_id:
            if not has_address:
                query.edit_message_text(
                    f"Tipo de servicio: {tipos_map[data]}\n\n"
                    "Falta la direccion de entrega.\n"
                    "Escribe la direccion de entrega:"
                )
                return PEDIDO_DIRECCION
            if not has_name:
                query.edit_message_text(
                    f"Tipo de servicio: {tipos_map[data]}\n\n"
                    "Falta el nombre del cliente.\n"
                    "Escribe el nombre del cliente:"
                )
                return PEDIDO_NOMBRE
            if not has_phone:
                query.edit_message_text(
                    f"Tipo de servicio: {tipos_map[data]}\n\n"
                    "Falta el telefono del cliente.\n"
                    "Escribe el numero de telefono del cliente:"
                )
                return PEDIDO_TELEFONO

        # Cliente nuevo: pedir nombre
        query.edit_message_text(
            f"Tipo de servicio: {tipos_map[data]}\n\n"
            "Ahora escribe el nombre del cliente:"
        )
        return PEDIDO_NOMBRE


def _parsear_lista_productos(texto):
    """Parsea una lista de productos con cantidades.

    Acepta separadores: coma, punto y coma, salto de linea.
    Acepta formatos por item:
      - "3 platanos"   (cantidad al inicio)
      - "platanos 3"   (cantidad al final)
      - "platanos x3"  (cantidad al final con prefijo x)
      - "platanos"     (sin cantidad → cuenta como 1)

    Returns:
        (items, total) donde items = [(qty, nombre), ...], total = suma de cantidades
        Si la lista esta vacia, retorna ([], 0).
    """
    import re
    items = []
    total = 0
    partes = re.split(r'[,;\n]+', texto)
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        # Cantidad al inicio: "3 platanos"
        m = re.match(r'^(\d+)\s+(.+)$', parte)
        if m:
            qty = int(m.group(1))
            name = m.group(2).strip()
            if not name:
                continue
            items.append((qty, name))
            total += qty
            continue
        # Cantidad al final con x opcional: "platanos x3" o "platanos 3"
        m = re.match(r'^(.+?)\s+[xX]?(\d+)$', parte)
        if m:
            name = m.group(1).strip()
            if not name:
                continue
            qty = int(m.group(2))
            items.append((qty, name))
            total += qty
            continue
        # Sin cantidad explicita → 1 unidad
        items.append((1, parte))
        total += 1
    return items, total


def pedido_compras_cantidad_handler(update, context):
    """Captura y parsea la lista de productos para Compras."""
    texto = update.message.text.strip()

    items, total = _parsear_lista_productos(texto)

    if not items or total <= 0:
        update.message.reply_text(
            "No pude leer la lista. Escribe la cantidad y el nombre de cada producto.\n\n"
            "Ejemplo:\n"
            "3 platanos, 2 bolsas de leche, 1 jabon"
        )
        return PEDIDO_COMPRAS_CANTIDAD

    if total > 50:
        update.message.reply_text(
            f"El total de unidades ({total}) supera el maximo de 50.\n"
            "Ajusta la lista e intentalo de nuevo:"
        )
        return PEDIDO_COMPRAS_CANTIDAD

    context.user_data["buy_products_list"] = texto
    context.user_data["buy_products_count"] = total

    # Continuar con el flujo normal
    has_name = context.user_data.get("customer_name")
    has_phone = context.user_data.get("customer_phone")
    has_address = context.user_data.get("customer_address")

    if has_name and has_phone and has_address:
        return mostrar_pregunta_base(update, context, edit=False)
    else:
        update.message.reply_text(
            f"Lista registrada ({total} unidad(es) en total).\n\n"
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
        _pedido_set_base_requirement(context, False, 0)
        return _pedido_continue_after_base(query, context, edit=True)

    elif data == "pedido_base_si":
        _pedido_set_base_requirement(context, True, 0)
        reply_markup = _pedido_base_keyboard()
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

    if data == "pedido_base_otro":
        query.edit_message_text(
            "Escribe el valor de la base (solo numeros):"
        )
        return PEDIDO_VALOR_BASE

    if data.startswith("pedido_base_"):
        raw_amount = data[len("pedido_base_"):]
        try:
            amount = int(raw_amount)
        except ValueError:
            return PEDIDO_VALOR_BASE
        if amount in PEDIDO_BASE_PRESET_AMOUNTS:
            _pedido_set_base_requirement(context, True, amount)
            return _pedido_continue_after_base(query, context, edit=True)

    return PEDIDO_VALOR_BASE


def pedido_valor_base_texto(update, context):
    """Maneja el valor de base ingresado por texto."""
    texto = update.message.text.strip().replace(".", "").replace(",", "")
    try:
        valor = int(texto)
        if valor <= 0:
            raise ValueError("Valor debe ser mayor a 0")
        _pedido_set_base_requirement(context, True, valor)
        return _pedido_continue_after_base(update, context, edit=False)
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
    """
    Calcula distancia con estrategia economica en 3 capas y muestra resumen.
    Capa 1: Cache de distancias previas (gratis)
    Capa 2: Haversine local (gratis, siempre disponible)
    Capa 3: Google API (solo si hay cuota)
    """
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
            pickup_text = default_location["address"]
            pickup_city = default_location["city"] or ""
            pickup_lat = default_location["lat"]
            pickup_lng = default_location["lng"]

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

    cotizacion = quote_order_from_inputs(
        pickup_text=pickup_text,
        dropoff_text=customer_address,
        pickup_city=pickup_city,
        dropoff_city=customer_city,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        dropoff_lat=dropoff_lat,
        dropoff_lng=dropoff_lng,
    )

    # Verificar si fallo
    if not cotizacion.get("success"):
        return mostrar_error_cotizacion(
            query_or_update, context,
            "No se pudo calcular la distancia automaticamente.\n\n"
            "Verifica que la API este activa y vuelve a intentar.",
            edit=edit
        )

    # Guardar datos de cotizacion
    context.user_data["quote_distance_km"] = cotizacion["distance_km"]
    pricing = build_order_pricing_breakdown(
        distance_km=cotizacion["distance_km"],
        service_type=context.user_data.get("service_type", ""),
        buy_products_count=context.user_data.get("buy_products_count", 0),
        additional_incentive=context.user_data.get("pedido_incentivo", 0),
    )
    context.user_data["quote_distance_fee"] = pricing["distance_fee"]
    context.user_data["buy_surcharge"] = pricing["buy_surcharge"]
    context.user_data["quote_price"] = pricing["subtotal_fee"]
    context.user_data["quote_source"] = cotizacion.get("quote_source", "text")
    context.user_data["distance_source"] = cotizacion.get("distance_source", "")

    # Mostrar resumen con botones de confirmacion
    keyboard = _pedido_confirmacion_keyboard(context)
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    # Agregar nota sobre precision y fuente de distancia
    dist_source = cotizacion.get("distance_source", "")
    if "google" in dist_source:
        resumen += "\n(Distancia por ruta - Google Maps)"
    elif "haversine" in dist_source:
        resumen += "\n(Distancia estimada - calculo local)"
    elif "cache" in dist_source:
        resumen += "\n(Distancia desde cache)"
    elif context.user_data.get("quote_source") == "coords":
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
    raw = update.message.text.strip()
    digits = "".join(filter(str.isdigit, raw))
    if len(digits) < 7:
        update.message.reply_text("Ingresa un numero de telefono valido (minimo 7 digitos).")
        return PEDIDO_TELEFONO
    context.user_data["customer_phone"] = digits
    # Dedup: si es cliente nuevo, verificar si ya existe en agenda
    if context.user_data.get("is_new_customer"):
        ally_id = context.user_data.get("active_ally_id") or context.user_data.get("ally_id")
        existing = get_ally_customer_by_phone(ally_id, digits) if ally_id else None
        if existing:
            context.user_data["dedup_found_customer_id"] = existing["id"]
            context.user_data["dedup_found_name"] = existing["name"] or ""
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Si, usar este cliente", callback_data="pedido_dedup_si")],
                [InlineKeyboardButton("No, es otro cliente", callback_data="pedido_dedup_no")],
            ])
            update.message.reply_text(
                "Este numero ya esta en tu agenda: {}\n\n"
                "Usar este cliente para el pedido?".format(existing["name"] or digits),
                reply_markup=keyboard,
            )
            return PEDIDO_DEDUP_CONFIRM
    # Si viene del cotizador, la ubicacion ya esta capturada
    if context.user_data.get("cotizador_prefill_dropoff"):
        update.message.reply_text(
            "Ubicacion guardada de la cotizacion.\n\n"
            "Escribe los detalles de la direccion del cliente:\n"
            "barrio, conjunto, torre, apto, referencias."
        )
        return PEDIDO_DIRECCION

    # Solo reutilizar datos de ubicacion si es cliente recurrente (no cliente nuevo)
    if not context.user_data.get("is_new_customer"):
        customer_id = context.user_data.get("customer_id")
        customer_address = context.user_data.get("customer_address")
        dropoff_lat = context.user_data.get("dropoff_lat")
        dropoff_lng = context.user_data.get("dropoff_lng")
        if customer_id and customer_address and (dropoff_lat is None or dropoff_lng is None):
            address_id = context.user_data.get("customer_address_id")
            if address_id:
                addr = get_customer_address_by_id(address_id, customer_id)
                if addr:
                    context.user_data["dropoff_lat"] = addr["lat"]
                    context.user_data["dropoff_lng"] = addr["lng"]
                    dropoff_lat = context.user_data.get("dropoff_lat")
                    dropoff_lng = context.user_data.get("dropoff_lng")

        if customer_id and customer_address and dropoff_lat is not None and dropoff_lng is not None:
            update.message.reply_text("Datos del cliente guardados. Continuamos con el pedido.")
            return mostrar_selector_pickup(update, context, edit=False)

    # Preguntar por ubicación (obligatoria)
    # Sugerir ultimas direcciones de entrega usadas por este aliado
    ally_id = context.user_data.get("active_ally_id")
    recientes = []
    if ally_id:
        try:
            recientes = get_recent_delivery_addresses_for_ally(ally_id, limit=5)
        except Exception:
            recientes = []
    if recientes:
        keyboard = []
        for row in recientes:
            addr_text = row[0] if isinstance(row, (list, tuple)) else row.get("customer_address", "")
            if addr_text:
                label = _pedido_visible_address_text(addr_text)[:40]
                if len(_pedido_visible_address_text(addr_text)) > 40:
                    label += "..."
                keyboard.append([InlineKeyboardButton(label, callback_data="pedido_nueva_dir")])
        # El boton lleva a PEDIDO_UBICACION sin prefill; el texto de la row se muestra como sugerencia visual
        # Mejor: guardamos las rows en user_data y usamos callbacks indexados
        context.user_data["_recientes_dirs"] = [
            {"address": row[0] if isinstance(row, (list, tuple)) else row.get("customer_address", ""),
             "city": row[1] if isinstance(row, (list, tuple)) else row.get("customer_city", ""),
             "barrio": row[2] if isinstance(row, (list, tuple)) else row.get("customer_barrio", ""),
             "lat": row[3] if isinstance(row, (list, tuple)) else row.get("dropoff_lat"),
             "lng": row[4] if isinstance(row, (list, tuple)) else row.get("dropoff_lng")}
            for row in recientes
        ]
        keyboard = []
        for i, row in enumerate(context.user_data["_recientes_dirs"]):
            addr_text = _pedido_visible_address_text(row["address"] or "")
            if addr_text:
                label = addr_text[:40] + ("..." if len(addr_text) > 40 else "")
                keyboard.append([InlineKeyboardButton(label, callback_data="pedido_reciente_dir_{}".format(i))])
        keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="pedido_nueva_dir")])
        update.message.reply_text(
            "Selecciona una direccion reciente o elige nueva:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return PEDIDO_UBICACION
    update.message.reply_text(
        "UBICACION (obligatoria)\n\n"
        "Envia la ubicacion (PIN de Telegram), "
        "pega el enlace (Google Maps/WhatsApp) "
        "o escribe coordenadas (lat,lng).\n\n"
        "No se puede continuar sin una ubicacion valida."
    )
    return PEDIDO_UBICACION


def _pedido_clear_pending_location_confirmation(context, clear_geo=False):
    keys = [
        "pedido_pending_location_source",
        "pedido_pending_location_link",
        "pedido_pending_location_expanded_link",
        "pedido_pending_location_provider",
        "pedido_pending_location_place_id",
        "pedido_pending_location_formatted_address",
        "pedido_pending_location_should_cache",
        "pedido_pending_prefill_address",
        "pedido_pending_customer_city",
        "pedido_pending_customer_barrio",
    ]
    if clear_geo:
        keys.extend([
            "pending_geo_lat",
            "pending_geo_lng",
            "pending_geo_text",
            "pending_geo_seen",
        ])
    for key in keys:
        context.user_data.pop(key, None)


def _pedido_solicitar_confirmacion_ubicacion(
    message,
    context,
    lat,
    lng,
    source,
    original_text="",
    formatted_address="",
    city="",
    barrio="",
    raw_link=None,
    expanded_link=None,
    provider=None,
    place_id=None,
    should_cache=False,
):
    _pedido_clear_pending_location_confirmation(context, clear_geo=False)
    context.user_data["pedido_pending_location_source"] = source
    context.user_data["pedido_pending_location_should_cache"] = bool(should_cache)
    logger.info(
        "[pedido_location_confirm] status=pending source=%s lat=%s lng=%s",
        source,
        lat,
        lng,
    )
    if raw_link:
        context.user_data["pedido_pending_location_link"] = raw_link
    if expanded_link:
        context.user_data["pedido_pending_location_expanded_link"] = expanded_link
    if provider:
        context.user_data["pedido_pending_location_provider"] = provider
    if place_id:
        context.user_data["pedido_pending_location_place_id"] = place_id
    if formatted_address:
        context.user_data["pedido_pending_location_formatted_address"] = formatted_address
    context.user_data["pedido_pending_customer_city"] = city or ""
    context.user_data["pedido_pending_customer_barrio"] = barrio or ""
    _mostrar_confirmacion_geocode(
        message,
        context,
        {
            "lat": lat,
            "lng": lng,
            "formatted_address": formatted_address,
            "place_id": place_id,
        },
        original_text,
        "pedido_geo_si",
        "pedido_geo_no",
        header_text="Confirma este punto exacto antes de continuar.",
        question_text="Es esta la ubicacion correcta?",
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
        return _pedido_solicitar_confirmacion_ubicacion(
            update.message,
            context,
            cached["lat"],
            cached["lng"],
            source="cache",
            original_text=texto,
            formatted_address=cached.get("formatted_address", ""),
            raw_link=raw_link,
            expanded_link=cached.get("expanded_link"),
            provider=cached.get("provider"),
            place_id=cached.get("place_id"),
        )

    # 2) Intentar expandir link corto si aplica
    expanded = expand_short_url(raw_link) or raw_link

    # 3) Extraer coordenadas del texto/URL con regex
    coords = extract_lat_lng_from_text(expanded)
    if coords:
        return _pedido_solicitar_confirmacion_ubicacion(
            update.message,
            context,
            coords[0],
            coords[1],
            source="regex",
            original_text=texto,
            raw_link=raw_link,
            expanded_link=expanded,
            provider="regex",
            should_cache=True,
        )

    # 4) Fallback: Google Places API SOLO si hay place_id en URL
    place_id = extract_place_id_from_url(expanded)
    if place_id and can_call_google_today():
        google_result = google_place_details(place_id)
        if google_result and google_result.get("lat") and google_result.get("lng"):
            return _pedido_solicitar_confirmacion_ubicacion(
                update.message,
                context,
                google_result["lat"],
                google_result["lng"],
                source="places",
                original_text=texto,
                formatted_address=google_result.get("formatted_address", ""),
                raw_link=raw_link,
                expanded_link=expanded,
                provider=google_result.get("provider"),
                place_id=google_result.get("place_id"),
                should_cache=True,
            )

    # 5) Geocoding: si el texto no es URL, intentar como direccion escrita
    if "http" not in texto:
        _hint = _order_city_hint(context)
        geo = resolve_location(texto, city_hint=_hint)
        if geo and geo.get("lat") is not None and geo.get("lng") is not None:
            context.user_data["pending_geo_city_hint"] = _hint
            source = "geocode" if geo.get("method") in ("geocode", "geocode_cache") else "resolved_text"
            return _pedido_solicitar_confirmacion_ubicacion(
                update.message,
                context,
                geo["lat"],
                geo["lng"],
                source=source,
                original_text=texto,
                formatted_address=geo.get("formatted_address", ""),
                city=geo.get("city", ""),
                barrio=geo.get("barrio", ""),
                place_id=geo.get("place_id"),
            )

    # 6) No se pudo resolver: la ubicacion es obligatoria
    es_link_corto_google = "maps.app.goo.gl" in raw_link or "goo.gl/maps" in raw_link

    if es_link_corto_google:
        keyboard = [[InlineKeyboardButton(
            "📋 Copiar mensaje para enviar al cliente",
            callback_data="ubicacion_copiar_msg_cliente"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "⚠️ Ese enlace no incluye coordenadas exactas.\n\n"
            "👉 Pídele al cliente una de estas opciones:\n"
            "• En WhatsApp: 📎 → Ubicación → Enviar ubicación actual\n"
            "• En Google Maps: tocar el punto azul → Compartir → copiar el link largo\n\n"
            "Cuando la tengas, envíala en este chat para continuar.",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            "No pude extraer coordenadas de ese texto.\n\n"
            "Envia una ubicacion valida para continuar.\n"
            "Tip: comparte PIN de Telegram, link de Maps con coordenadas o lat,lng."
        )
    return PEDIDO_UBICACION


def pedido_ubicacion_location_handler(update, context):
    """Maneja ubicacion nativa de Telegram (PIN) enviada por el usuario."""
    message = update.message
    if not message or not message.location:
        return PEDIDO_UBICACION

    loc = message.location
    return _pedido_solicitar_confirmacion_ubicacion(
        message,
        context,
        loc.latitude,
        loc.longitude,
        source="telegram_pin",
        formatted_address="Ubicacion enviada desde Telegram.",
    )


def pedido_geo_ubicacion_callback(update, context):
    """Maneja confirmacion de geocoding en el flujo de pedido."""
    query = update.callback_query
    query.answer()

    if query.data == "pedido_geo_si":
        _maybe_cache_confirmed_geo(context)
        source = context.user_data.pop("pedido_pending_location_source", "")
        raw_link = context.user_data.pop("pedido_pending_location_link", None)
        expanded_link = context.user_data.pop("pedido_pending_location_expanded_link", None)
        provider = context.user_data.pop("pedido_pending_location_provider", None)
        place_id = context.user_data.pop("pedido_pending_location_place_id", None)
        formatted_address = context.user_data.pop("pedido_pending_location_formatted_address", "")
        should_cache = bool(context.user_data.pop("pedido_pending_location_should_cache", False))
        pending_prefill_address = context.user_data.pop("pedido_pending_prefill_address", None)
        pending_customer_city = context.user_data.pop("pedido_pending_customer_city", "")
        pending_customer_barrio = context.user_data.pop("pedido_pending_customer_barrio", "")
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        original_text = context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        confirmed_recent_address = ""
        if lat is None or lng is None:
            _pedido_clear_pending_location_confirmation(context, clear_geo=True)
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return PEDIDO_UBICACION
        if source == "geocode":
            save_confirmed_geocoding(original_text, lat, lng)
        if raw_link:
            context.user_data["customer_location_link"] = raw_link
            if should_cache:
                upsert_link_cache(
                    raw_link,
                    expanded_link or raw_link,
                    lat,
                    lng,
                    formatted_address,
                    provider,
                    place_id,
                )
        context.user_data["customer_city"] = pending_customer_city or ""
        context.user_data["customer_barrio"] = pending_customer_barrio or ""
        if source == "recent_address":
            confirmed_recent_address = (pending_prefill_address or "").strip()
            if confirmed_recent_address:
                context.user_data["customer_address"] = confirmed_recent_address
        logger.info(
            "[pedido_location_confirm] status=confirmed source=%s lat=%s lng=%s",
            source,
            lat,
            lng,
        )
        context.user_data["dropoff_lat"] = lat
        context.user_data["dropoff_lng"] = lng
        if source == "recent_address" and confirmed_recent_address:
            if _pedido_is_system_address(confirmed_recent_address):
                logger.info(
                    "[address_rule_v2026_04_08] flow=ally_delivery action=prompt_detail source=recent_address"
                )
                query.edit_message_text(
                    "Esa direccion reciente estaba guardada solo con coordenadas.\n\n"
                    "Ahora escribe la direccion visible real del cliente.\n"
                    "No envies GPS, links ni coordenadas."
                )
                return PEDIDO_DIRECCION
            if context.user_data.pop("pedido_edit_from_preview", False):
                query.edit_message_text(
                    "Ubicacion confirmada.\n\n"
                    "Se usara esta direccion:\n{}".format(confirmed_recent_address)
                )
                return mostrar_resumen_confirmacion(query, context, edit=False)
            query.edit_message_text(
                "Ubicacion confirmada.\n\n"
                "Se reutilizara esta direccion:\n{}\n\n"
                "Continuamos con el punto de recogida.".format(confirmed_recent_address)
            )
            return mostrar_selector_pickup(query, context, edit=False)
        if not _pedido_requires_human_detail(
            {"source": source, "original_text": original_text}
        ):
            logger.info(
                "[address_rule_v2026_04_08] flow=ally_delivery action=reuse_human_text source=%s",
                source,
            )
            confirmed_address = _pedido_visible_address_text(
                original_text or formatted_address,
                fallback=formatted_address or "Direccion confirmada",
            )
            context.user_data["customer_address"] = confirmed_address
            if context.user_data.pop("pedido_edit_from_preview", False):
                query.edit_message_text(
                    "Ubicacion confirmada.\n\n"
                    "Se usara esta direccion:\n{}".format(confirmed_address)
                )
                return mostrar_resumen_confirmacion(query, context, edit=False)
            query.edit_message_text(
                "Ubicacion confirmada.\n\n"
                "Se usara esta direccion:\n{}\n\n"
                "Continuamos con el punto de recogida.".format(confirmed_address)
            )
            return mostrar_selector_pickup(query, context, edit=False)
        query.edit_message_text(
            "Ubicacion confirmada.\n\n"
            "Ahora escribe los detalles de la direccion:\n"
            "barrio, conjunto, torre, apto, referencias."
        )
        return PEDIDO_DIRECCION
    else:  # pedido_geo_no
        source = context.user_data.get("pedido_pending_location_source", "")
        if source == "geocode":
            result = _geo_siguiente_o_gps(query, context, "pedido_geo_si", "pedido_geo_no", PEDIDO_UBICACION)
            if "pending_geo_lat" not in context.user_data or "pending_geo_lng" not in context.user_data:
                _pedido_clear_pending_location_confirmation(context, clear_geo=False)
                logger.info("[pedido_location_confirm] status=rejected source=%s", source)
            return result
        _pedido_clear_pending_location_confirmation(context, clear_geo=True)
        logger.info("[pedido_location_confirm] status=rejected source=%s", source)
        query.edit_message_text(
            "Ubicacion descartada.\n\n"
            "Envia otra ubicacion para continuar.\n"
            "El flujo solo sigue cuando confirmes el punto exacto."
        )
        return PEDIDO_UBICACION


def pedido_reciente_dir_callback(update, context):
    """Selecciona una de las direcciones recientes del aliado para el pedido."""
    query = update.callback_query
    query.answer()
    idx_str = query.data.replace("pedido_reciente_dir_", "")
    try:
        idx = int(idx_str)
    except ValueError:
        query.edit_message_text("Error al seleccionar direccion. Escribe la direccion manualmente.")
        return PEDIDO_UBICACION
    recientes = context.user_data.get("_recientes_dirs", [])
    if idx < 0 or idx >= len(recientes):
        query.edit_message_text("Direccion no encontrada. Escribe la direccion manualmente.")
        return PEDIDO_UBICACION
    row = recientes[idx]
    if not has_valid_coords(row.get("lat"), row.get("lng")):
        context.user_data.pop("_recientes_dirs", None)
        query.edit_message_text(
            "Esa direccion antigua no tiene ubicacion confirmada.\n\n"
            "Envia una ubicacion nueva para continuar."
        )
        return PEDIDO_UBICACION
    context.user_data["pedido_pending_prefill_address"] = row["address"]
    context.user_data["pedido_pending_customer_city"] = row.get("city", "")
    context.user_data["pedido_pending_customer_barrio"] = row.get("barrio", "")
    context.user_data.pop("_recientes_dirs", None)
    query.edit_message_text(
        "Direccion seleccionada.\n\n"
        "Revisa el punto exacto y confirmalo para reutilizar esa misma direccion."
    )
    return _pedido_solicitar_confirmacion_ubicacion(
        query.message,
        context,
        row.get("lat"),
        row.get("lng"),
        source="recent_address",
        formatted_address=row["address"],
    )


def pedido_nueva_dir_en_ubicacion_callback(update, context):
    """Descarta sugerencias recientes y muestra el prompt de nueva ubicacion."""
    query = update.callback_query
    query.answer()
    context.user_data.pop("_recientes_dirs", None)
    query.edit_message_text(
        "UBICACION (obligatoria)\n\n"
        "Envia la ubicacion (PIN de Telegram), "
        "pega el enlace (Google Maps/WhatsApp) "
        "o escribe coordenadas (lat,lng).\n\n"
        "No se puede continuar sin una ubicacion valida."
    )
    return PEDIDO_UBICACION


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
    detail = " ".join(update.message.text.strip().split())
    if _pedido_is_system_address(detail):
        update.message.reply_text(
            "Escribe la direccion visible en texto humano.\n"
            "No envies GPS, links ni coordenadas."
        )
        return PEDIDO_DIRECCION

    pending_fix = context.user_data.get("pedido_pending_address_fix") or {}
    if pending_fix:
        lat = pending_fix.get("lat")
        lng = pending_fix.get("lng")
        if not has_valid_coords(lat, lng):
            context.user_data.pop("pedido_pending_address_fix", None)
            update.message.reply_text(
                "Se perdio la ubicacion confirmada.\n"
                "Envia una ubicacion nueva para continuar."
            )
            return PEDIDO_UBICACION
        customer_id = pending_fix.get("customer_id")
        address_id = pending_fix.get("address_id")
        label = _pedido_human_label(pending_fix.get("label"), detail)
        updated = update_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=label,
            address_text=detail,
            city=pending_fix.get("city", ""),
            barrio=pending_fix.get("barrio", ""),
            notes=pending_fix.get("notes"),
            lat=lat,
            lng=lng,
        )
        if not updated:
            update.message.reply_text(
                "No se pudo actualizar la direccion guardada. Intenta de nuevo."
            )
            return PEDIDO_DIRECCION
        context.user_data["customer_address_id"] = address_id
        context.user_data["customer_address"] = detail
        context.user_data["customer_city"] = pending_fix.get("city", "")
        context.user_data["customer_barrio"] = pending_fix.get("barrio", "")
        context.user_data["dropoff_lat"] = lat
        context.user_data["dropoff_lng"] = lng
        context.user_data["nota_direccion"] = pending_fix.get("notes") or ""
        parking_status = pending_fix.get("parking_status", "NOT_ASKED")
        context.user_data["pedido_parking_fee"] = (
            PARKING_FEE_AMOUNT if parking_status in ("ALLY_YES", "ADMIN_YES") else 0
        )
        try:
            increment_customer_address_usage(address_id, customer_id)
            increment_ally_customer_usage(customer_id)
        except Exception:
            pass
        logger.info(
            "[address_rule_v2026_04_08] flow=ally_delivery action=repair_saved_address address_id=%s",
            address_id,
        )
        context.user_data.pop("pedido_pending_address_fix", None)
        update.message.reply_text("Direccion actualizada. Continuamos con el pedido.")
        return _pedido_prompt_notes_or_continue(update, context, edit=False)

    context.user_data["customer_address"] = detail

    if context.user_data.pop("pedido_edit_from_preview", False):
        return mostrar_resumen_confirmacion_msg(update, context)

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
    ally = context.user_data.get("ally")
    ally_id = ally["id"] if ally else None

    keyboard = []
    if ally_id:
        locations = get_ally_locations(ally_id)
        default_loc = next((l for l in locations if l["is_default"]), None)

        if default_loc:
            label = _pedido_visible_address_text(default_loc["label"], fallback="Base")[:20]
            address = _pedido_pickup_option_text(default_loc)[:35]
            sin_gps = " (sin GPS)" if default_loc["lat"] is None else ""
            keyboard.append([InlineKeyboardButton(
                "Usar base: {} - {}{}".format(label, address, sin_gps),
                callback_data="pickup_select_base"
            )])

        otros = [l for l in locations if not l["is_default"]]
        if otros or (locations and not default_loc):
            n = len(locations)
            keyboard.append([InlineKeyboardButton(
                "Elegir otra ({})".format(n),
                callback_data="pickup_select_lista"
            )])

    keyboard.append([InlineKeyboardButton("Agregar nueva direccion", callback_data="pickup_select_nueva")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    texto = "PUNTO DE RECOGIDA\n\nDonde se recoge el pedido?"

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
    context.user_data.pop("pedido_pending_pickup_fix", None)

    ally = context.user_data.get("ally")
    if not ally:
        query.edit_message_text("Error: no se encontro informacion del aliado. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END

    ally_id = ally["id"]
    if data != "pickup_select_fixbasecoords":
        context.user_data.pop("pickup_fix_default_loc_id", None)

    if data == "pickup_select_base":
        # Usar direccion base del aliado
        default_loc = get_default_ally_location(ally_id)
        if not default_loc:
            query.edit_message_text(
                "No tienes una direccion base configurada.\n"
                "Puedes agregar una nueva o contactar soporte."
            )
            return mostrar_selector_pickup(query, context, edit=False)

        default_lat = default_loc["lat"]
        default_lng = default_loc["lng"]
        if default_lat is None or default_lng is None:
            keyboard = [
                [InlineKeyboardButton("Enviar PIN ahora", callback_data="pickup_select_fixbasecoords")],
                [InlineKeyboardButton("Elegir otra recogida", callback_data="pickup_select_lista")],
                [InlineKeyboardButton("Nueva direccion", callback_data="pickup_select_nueva")],
            ]
            query.edit_message_text(
                "Tu direccion principal no tiene coordenadas.\n"
                "Para continuar, debes enviar un PIN de ubicacion de recogida.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return PEDIDO_PICKUP_SELECTOR

        # Guardar pickup en user_data
        if _pedido_is_system_address(default_loc.get("address")):
            logger.info(
                "[address_rule_v2026_04_08] flow=ally_pickup action=prompt_repair_saved_pickup location_id=%s",
                default_loc.get("id"),
            )
            return _pedido_start_pickup_fix(query, context, default_loc)
        context.user_data["pickup_location"] = default_loc
        context.user_data["pickup_label"] = _pedido_visible_address_text(
            default_loc["label"],
            fallback="Base",
        )
        context.user_data["pickup_address"] = default_loc["address"] or ""
        context.user_data["pickup_city"] = default_loc["city"] or ""
        context.user_data["pickup_barrio"] = default_loc["barrio"] or ""
        context.user_data["pickup_lat"] = default_loc["lat"]
        context.user_data["pickup_lng"] = default_loc["lng"]

        # Continuar al siguiente paso
        return continuar_despues_pickup(query, context, edit=True)

    elif data == "pickup_select_lista":
        # Mostrar lista de direcciones guardadas
        return mostrar_lista_pickups(query, context)

    elif data == "pickup_select_nueva":
        # Pedir nueva direccion
        query.edit_message_text(
            "NUEVA DIRECCION DE RECOGIDA\n\n"
            "Envia la ubicacion (PIN de Telegram), "
            "pega el enlace (Google Maps/WhatsApp) "
            "o escribe coordenadas (lat,lng).\n\n"
            "La ubicacion es obligatoria para continuar."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    elif data == "pickup_select_fixbasecoords":
        default_loc = get_default_ally_location(ally_id)
        if not default_loc:
            query.edit_message_text(
                "No se encontro tu direccion principal.\n"
                "Elige otra direccion de recogida."
            )
            return mostrar_selector_pickup(query, context, edit=False)

        context.user_data["pickup_fix_default_loc_id"] = default_loc["id"]
        query.edit_message_text(
            "Envia un PIN de ubicacion de Telegram, link de Google Maps o coordenadas (lat,lng)\n"
            "para actualizar la direccion principal y continuar."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    else:
        query.edit_message_text("Opcion no valida. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END


# =============================================================
# PANEL DE GESTIÓN DE UBICACIONES DEL ALIADO ("Mis ubicaciones")
# =============================================================

def construir_etiqueta_pickup(loc):
    """Construye etiqueta para un pickup con info de uso."""
    label = loc["label"] or (loc["address"] or "Sin nombre")[:25]
    tags = []

    if loc["is_default"]:
        tags.append("BASE")
    if loc["is_frequent"]:
        tags.append("FRECUENTE")
    elif (loc["use_count"] or 0) > 0:
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

    # Botones directos sin submenú — un clic usa la dirección
    keyboard = []
    for loc in locations[:8]:
        label = _pedido_visible_address_text(loc["label"], fallback="Sin nombre")[:20]
        address = _pedido_visible_address_text(
            loc["address"],
            fallback="Ubicacion pendiente de detallar",
        )[:28]
        tags = []
        if loc["is_default"]:
            tags.append("BASE")
        if loc["is_frequent"]:
            tags.append("FRECUENTE")
        elif (loc["use_count"] or 0) > 0:
            tags.append("x{}".format(loc["use_count"]))
        tag_str = " [{}]".format(", ".join(tags)) if tags else ""
        sin_gps = " (sin GPS)" if loc["lat"] is None else ""
        keyboard.append([InlineKeyboardButton(
            "{}: {}{}{}".format(label, address, tag_str, sin_gps),
            callback_data="pickup_list_usar_{}".format(loc["id"])
        )])

    keyboard.append([InlineKeyboardButton("Agregar nueva", callback_data="pickup_list_nueva")])
    keyboard.append([InlineKeyboardButton("Volver", callback_data="pickup_list_volver")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        "ELEGIR PUNTO DE RECOGIDA\n\n"
        "Selecciona una de tus direcciones:",
        reply_markup=reply_markup
    )
    return PEDIDO_PICKUP_LISTA


def pedido_pickup_lista_callback(update, context):
    """Maneja la seleccion de una direccion de la lista."""
    query = update.callback_query
    query.answer()
    data = query.data
    context.user_data.pop("pedido_pending_pickup_fix", None)

    if data == "pickup_list_volver":
        return mostrar_selector_pickup(query, context, edit=True)

    if data == "pickup_list_nueva":
        query.edit_message_text(
            "NUEVA DIRECCION DE RECOGIDA\n\n"
            "Envia la ubicacion (PIN de Telegram), "
            "pega el enlace (Google Maps/WhatsApp) "
            "o escribe coordenadas (lat,lng).\n\n"
            "La ubicacion es obligatoria para continuar."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

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

        if location["lat"] is None or location["lng"] is None:
            query.answer("Esta direccion no tiene GPS. Selecciona otra o agrega una nueva.", show_alert=True)
            return mostrar_lista_pickups(query, context)

        if _pedido_is_system_address(location.get("address")):
            logger.info(
                "[address_rule_v2026_04_08] flow=ally_pickup action=prompt_repair_saved_pickup location_id=%s",
                location.get("id"),
            )
            return _pedido_start_pickup_fix(query, context, location)

        context.user_data["pickup_location"] = location
        context.user_data["pickup_label"] = _pedido_visible_address_text(
            location["label"],
            fallback="Recogida",
        )
        context.user_data["pickup_address"] = location["address"] or ""
        context.user_data["pickup_city"] = location["city"] or ""
        context.user_data["pickup_barrio"] = location["barrio"] or ""
        context.user_data["pickup_lat"] = location["lat"]
        context.user_data["pickup_lng"] = location["lng"]

        return continuar_despues_pickup(query, context, edit=True)

    query.edit_message_text("Opcion no valida.")
    return ConversationHandler.END


def pedido_pickup_nueva_ubicacion_handler(update, context):
    """Maneja la captura de ubicacion para nueva direccion de recogida."""
    text = update.message.text.strip()
    fixing_default = bool(context.user_data.get("pickup_fix_default_loc_id"))
    context.user_data.pop("pedido_pending_pickup_resolution", None)

    if text.lower() == "omitir":
        update.message.reply_text(
            "No puedes omitir la ubicacion.\n"
            "Envia un PIN, link de Google Maps o coordenadas (lat,lng)."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    # Mismo pipeline de resolucion usado en cotizacion
    _hint = _order_city_hint(context)
    loc = resolve_location(text, city_hint=_hint)
    if loc and loc.get("lat") is not None and loc.get("lng") is not None:
        if loc.get("method") == "geocode" and loc.get("formatted_address"):
            context.user_data["pending_geo_city_hint"] = _hint
            context.user_data["pedido_pending_pickup_resolution"] = {
                "source": loc.get("method") or "geocode",
                "original_text": text,
                "city": loc.get("city", ""),
                "barrio": loc.get("barrio", ""),
            }
            _mostrar_confirmacion_geocode(
                update.message, context,
                loc, text,
                "pickup_geo_si", "pickup_geo_no",
            )
            return PEDIDO_PICKUP_NUEVA_UBICACION

        lat, lng = loc["lat"], loc["lng"]
        if fixing_default:
            ally = context.user_data.get("ally")
            location_id = context.user_data.get("pickup_fix_default_loc_id")
            if not ally or not location_id:
                update.message.reply_text("No se pudo actualizar la direccion principal. Intenta /nuevo_pedido de nuevo.")
                return ConversationHandler.END

            update_ally_location_coords(location_id, lat, lng)
            context.user_data.pop("pickup_fix_default_loc_id", None)

            default_loc = get_default_ally_location(ally["id"])
            if not default_loc:
                update.message.reply_text("No se pudo cargar la direccion principal actualizada.")
                return ConversationHandler.END

            context.user_data["pickup_location"] = default_loc
            context.user_data["pickup_label"] = default_loc.get("label") or "Base"
            context.user_data["pickup_address"] = default_loc.get("address", "")
            context.user_data["pickup_city"] = default_loc.get("city", "")
            context.user_data["pickup_barrio"] = default_loc.get("barrio", "")
            context.user_data["pickup_lat"] = default_loc.get("lat")
            context.user_data["pickup_lng"] = default_loc.get("lng")

            update.message.reply_text("Ubicacion principal actualizada. Continuamos con el pedido.")
            return continuar_despues_pickup(update, context, edit=False)

        context.user_data["new_pickup_lat"] = lat
        context.user_data["new_pickup_lng"] = lng
        update.message.reply_text(
            f"Ubicacion capturada: {lat}, {lng}\n\n"
            "Ahora escribe los detalles de la direccion de recogida:\n"
            "direccion, barrio, referencias..."
        )
        return PEDIDO_PICKUP_NUEVA_DETALLES

    # No se pudo extraer - detectar si es link corto de Google
    es_link_corto_google = "maps.app.goo.gl" in text or "goo.gl/maps" in text

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
            "Cuando la tengas, enviala aqui para continuar.",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            "No se pudo extraer ubicacion valida.\n"
            "Envia un PIN, link de Google Maps o coordenadas (lat,lng)."
        )

    return PEDIDO_PICKUP_NUEVA_UBICACION


def pedido_pickup_geo_callback(update, context):
    """Maneja confirmacion de geocoding para nueva direccion de pickup en pedido."""
    query = update.callback_query
    query.answer()

    if query.data == "pickup_geo_si":
        _maybe_cache_confirmed_geo(context)
        resolution = context.user_data.pop("pedido_pending_pickup_resolution", {})
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Intenta /nuevo_pedido de nuevo.")
            return PEDIDO_PICKUP_NUEVA_UBICACION

        fixing_default = bool(context.user_data.get("pickup_fix_default_loc_id"))
        if fixing_default:
            ally = context.user_data.get("ally")
            location_id = context.user_data.get("pickup_fix_default_loc_id")
            if not ally or not location_id:
                query.edit_message_text("No se pudo actualizar la direccion principal. Intenta /nuevo_pedido de nuevo.")
                return ConversationHandler.END

            update_ally_location_coords(location_id, lat, lng)
            context.user_data.pop("pickup_fix_default_loc_id", None)

            default_loc = get_default_ally_location(ally["id"])
            if not default_loc:
                query.edit_message_text("No se pudo cargar la direccion principal actualizada.")
                return ConversationHandler.END

            context.user_data["pickup_location"] = default_loc
            context.user_data["pickup_label"] = default_loc.get("label") or "Base"
            context.user_data["pickup_address"] = default_loc.get("address", "")
            context.user_data["pickup_city"] = default_loc.get("city", "")
            context.user_data["pickup_lat"] = default_loc.get("lat")
            context.user_data["pickup_lng"] = default_loc.get("lng")

            query.edit_message_text("Ubicacion principal actualizada. Continuamos con el pedido.")
            return continuar_despues_pickup(query, context, edit=False)

        context.user_data["new_pickup_lat"] = lat
        context.user_data["new_pickup_lng"] = lng
        if not _pedido_requires_human_detail(
            {
                "source": resolution.get("source"),
                "original_text": resolution.get("original_text"),
            }
        ):
            logger.info(
                "[address_rule_v2026_04_08] flow=ally_pickup action=reuse_human_text source=%s",
                resolution.get("source"),
            )
            context.user_data["new_pickup_address"] = _pedido_visible_address_text(
                resolution.get("original_text"),
                fallback="Direccion confirmada",
            )
            if resolution.get("city"):
                context.user_data["new_pickup_city"] = resolution.get("city", "")
            if resolution.get("barrio"):
                context.user_data["new_pickup_barrio"] = resolution.get("barrio", "")
            suggested_city = resolution.get("city") or context.user_data.get("new_pickup_city") or "Pereira"
            query.edit_message_text(
                "Ubicacion confirmada.\n\n"
                "Se usara esta direccion de recogida:\n{}\n\n"
                "Ciudad de la recogida (ej: {}).".format(
                    context.user_data["new_pickup_address"],
                    suggested_city,
                )
            )
            return PEDIDO_PICKUP_NUEVA_CIUDAD
        query.edit_message_text(
            f"Ubicacion capturada: {lat}, {lng}\n\n"
            "Ahora escribe la direccion de recogida (sin ciudad ni barrio):"
        )
        return PEDIDO_PICKUP_NUEVA_DETALLES

    return _geo_siguiente_o_gps(query, context, "pickup_geo_si", "pickup_geo_no", PEDIDO_PICKUP_NUEVA_UBICACION)


def pedido_pickup_nueva_ubicacion_location_handler(update, context):
    """Maneja ubicacion nativa de Telegram (PIN) para nueva direccion de recogida en pedido."""
    loc = update.message.location
    fixing_default = bool(context.user_data.get("pickup_fix_default_loc_id"))
    context.user_data.pop("pedido_pending_pickup_resolution", None)

    if fixing_default:
        ally = context.user_data.get("ally")
        location_id = context.user_data.get("pickup_fix_default_loc_id")
        if not ally or not location_id:
            update.message.reply_text("No se pudo actualizar la direccion principal. Intenta /nuevo_pedido de nuevo.")
            return ConversationHandler.END

        update_ally_location_coords(location_id, loc.latitude, loc.longitude)
        context.user_data.pop("pickup_fix_default_loc_id", None)

        default_loc = get_default_ally_location(ally["id"])
        if not default_loc:
            update.message.reply_text("No se pudo cargar la direccion principal actualizada.")
            return ConversationHandler.END

        context.user_data["pickup_location"] = default_loc
        context.user_data["pickup_label"] = default_loc.get("label") or "Base"
        context.user_data["pickup_address"] = default_loc.get("address", "")
        context.user_data["pickup_city"] = default_loc.get("city", "")
        context.user_data["pickup_barrio"] = default_loc.get("barrio", "")
        context.user_data["pickup_lat"] = default_loc.get("lat")
        context.user_data["pickup_lng"] = default_loc.get("lng")

        update.message.reply_text("Ubicacion principal actualizada. Continuamos con el pedido.")
        return continuar_despues_pickup(update, context, edit=False)

    context.user_data["new_pickup_lat"] = loc.latitude
    context.user_data["new_pickup_lng"] = loc.longitude
    update.message.reply_text(
        f"Ubicacion capturada: {loc.latitude}, {loc.longitude}\n\n"
        "Ahora escribe la direccion de recogida (sin ciudad ni barrio):"
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
    text = " ".join(update.message.text.strip().split())
    if not text:
        update.message.reply_text("Por favor escribe la direccion de recogida:")
        return PEDIDO_PICKUP_NUEVA_DETALLES
    if _pedido_is_system_address(text):
        update.message.reply_text(
            "Escribe la direccion visible en texto humano.\n"
            "No envies GPS, links ni coordenadas."
        )
        return PEDIDO_PICKUP_NUEVA_DETALLES

    context.user_data["new_pickup_address"] = text
    pending_fix = context.user_data.get("pedido_pending_pickup_fix") or {}
    if pending_fix:
        lat = pending_fix.get("lat")
        lng = pending_fix.get("lng")
        if not has_valid_coords(lat, lng):
            context.user_data.pop("pedido_pending_pickup_fix", None)
            update.message.reply_text(
                "Se perdio la ubicacion confirmada.\n"
                "Envia una ubicacion nueva para continuar."
            )
            return PEDIDO_PICKUP_NUEVA_UBICACION
        context.user_data["new_pickup_lat"] = lat
        context.user_data["new_pickup_lng"] = lng
        if pending_fix.get("city"):
            context.user_data["new_pickup_city"] = pending_fix.get("city", "")
        if pending_fix.get("barrio"):
            context.user_data["new_pickup_barrio"] = pending_fix.get("barrio", "")
        if pending_fix.get("city") and pending_fix.get("barrio"):
            update_ally_location(
                pending_fix["location_id"],
                text,
                pending_fix.get("city", ""),
                pending_fix.get("barrio", ""),
                pending_fix.get("phone"),
            )
            context.user_data["pickup_label"] = "Recogida"
            context.user_data["pickup_address"] = text
            context.user_data["pickup_city"] = pending_fix.get("city", "")
            context.user_data["pickup_barrio"] = pending_fix.get("barrio", "")
            context.user_data["pickup_lat"] = lat
            context.user_data["pickup_lng"] = lng
            logger.info(
                "[address_rule_v2026_04_08] flow=ally_pickup action=repair_saved_pickup location_id=%s",
                pending_fix["location_id"],
            )
            context.user_data.pop("pedido_pending_pickup_fix", None)
            update.message.reply_text("Direccion corregida. Continuamos con el pedido.")
            return continuar_despues_pickup(update, context, edit=False)

    # Sugerir ciudad basada en la base del aliado (pero se pregunta siempre)
    ally = context.user_data.get("ally")
    default_city = "Pereira"
    if ally and not context.user_data.get("new_pickup_city"):
        default_loc = get_default_ally_location(ally["id"])
        if default_loc and default_loc["city"]:
            default_city = default_loc["city"]
    elif context.user_data.get("new_pickup_city"):
        default_city = context.user_data.get("new_pickup_city")

    update.message.reply_text(
        "Ciudad de la recogida (ej: {}).".format(default_city)
    )
    return PEDIDO_PICKUP_NUEVA_CIUDAD


def pedido_pickup_nueva_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la recogida:",
        "new_pickup_city",
        PEDIDO_PICKUP_NUEVA_CIUDAD,
        PEDIDO_PICKUP_NUEVA_BARRIO,
        flow=None,
        next_prompt="Barrio o sector de la recogida:",
        options_hint="",
        set_back_step=False,
    )


def pedido_pickup_nueva_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la recogida:",
        "new_pickup_barrio",
        PEDIDO_PICKUP_NUEVA_BARRIO,
        PEDIDO_PICKUP_GUARDAR,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == PEDIDO_PICKUP_NUEVA_BARRIO:
        return ok_state
    barrio = context.user_data.get("new_pickup_barrio", "")

    # Guardar pickup temporal
    context.user_data["pickup_label"] = "Nueva"
    context.user_data["pickup_address"] = context.user_data.get("new_pickup_address", "")
    context.user_data["pickup_city"] = context.user_data.get("new_pickup_city", "")
    context.user_data["pickup_barrio"] = barrio
    context.user_data["pickup_lat"] = context.user_data.get("new_pickup_lat")
    context.user_data["pickup_lng"] = context.user_data.get("new_pickup_lng")

    pending_fix = context.user_data.get("pedido_pending_pickup_fix") or {}
    if pending_fix:
        update_ally_location(
            pending_fix["location_id"],
            context.user_data.get("new_pickup_address", ""),
            context.user_data.get("new_pickup_city", ""),
            barrio,
            pending_fix.get("phone"),
        )
        logger.info(
            "[address_rule_v2026_04_08] flow=ally_pickup action=repair_saved_pickup location_id=%s",
            pending_fix["location_id"],
        )
        context.user_data.pop("pedido_pending_pickup_fix", None)
        update.message.reply_text("Direccion corregida. Continuamos con el pedido.")
        return continuar_despues_pickup(update, context, edit=False)

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
            barrio=context.user_data.get("new_pickup_barrio", ""),
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


def _pickup_preview_chat_id(query_or_update):
    if hasattr(query_or_update, "message") and query_or_update.message:
        return query_or_update.message.chat_id
    return getattr(query_or_update, "chat_id", None)


def _clear_pickup_preview_location(context, chat_id):
    message_id = context.user_data.pop("pickup_preview_location_message_id", None)
    if not message_id or not chat_id:
        return
    try:
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def mostrar_preview_pickup(query_or_update, context, edit=False):
    """Muestra un preview del pickup seleccionado antes de continuar el flujo."""
    pickup_label = context.user_data.get("pickup_label") or "Recogida"
    pickup_address = context.user_data.get("pickup_address") or "No disponible"
    pickup_city = context.user_data.get("pickup_city", "")
    pickup_barrio = context.user_data.get("pickup_barrio", "")
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")
    pickup_area = "{}, {}".format(pickup_barrio, pickup_city).strip(", ") or "No disponible"

    keyboard = []
    if has_valid_coords(pickup_lat, pickup_lng):
        gmaps_url = "https://www.google.com/maps?q={},{}".format(pickup_lat, pickup_lng)
        keyboard.append([InlineKeyboardButton("Abrir en Google Maps", url=gmaps_url)])
    keyboard.append([InlineKeyboardButton("Confirmar recogida", callback_data=PICKUP_PREVIEW_CONFIRM_CALLBACK)])
    keyboard.append([InlineKeyboardButton("Cambiar pickup", callback_data=PICKUP_PREVIEW_CHANGE_CALLBACK)])

    text = (
        "PREVIEW DEL PUNTO DE RECOGIDA\n\n"
        "Punto: {}\n"
        "Direccion: {}\n"
        "Zona: {}\n\n"
        "Te envio el pin de esta recogida en el siguiente mensaje para que la revises antes de continuar.\n\n"
        "Confirmas que este es el punto de recogida?"
    ).format(pickup_label, pickup_address, pickup_area)

    reply_markup = InlineKeyboardMarkup(keyboard)
    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(text, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(text, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(text, reply_markup=reply_markup)

    chat_id = _pickup_preview_chat_id(query_or_update)
    _clear_pickup_preview_location(context, chat_id)
    if chat_id and has_valid_coords(pickup_lat, pickup_lng):
        try:
            msg = context.bot.send_location(
                chat_id=chat_id,
                latitude=float(pickup_lat),
                longitude=float(pickup_lng),
            )
            context.user_data["pickup_preview_location_message_id"] = msg.message_id
        except Exception:
            context.user_data.pop("pickup_preview_location_message_id", None)

    logger.info(
        "pickup_preview_shown ally_id=%s chat_id=%s pickup_label=%s",
        context.user_data.get("ally_id"),
        chat_id,
        pickup_label,
    )
    return PEDIDO_PICKUP_SELECTOR


def _continuar_flujo_despues_pickup_confirmado(query, context, edit=True):
    """Continua el flujo una vez el aliado confirma el pickup seleccionado."""
    # Si veníamos de editar desde el preview, volver al preview directamente
    if context.user_data.pop("pedido_edit_from_preview", False):
        return mostrar_resumen_confirmacion(query, context, edit=edit)

    # Verificar si ya tenemos tipo de servicio
    if not context.user_data.get("service_type"):
        return mostrar_selector_tipo_servicio(query, context, edit=edit)

    # Ya tenemos tipo, preguntar por base
    return mostrar_pregunta_base(query, context, edit=edit)


def continuar_despues_pickup(query, context, edit=True):
    """Muestra preview del pickup y espera confirmacion del aliado."""
    if not context.user_data.get("pickup_address"):
        return _continuar_flujo_despues_pickup_confirmado(query, context, edit=edit)
    return mostrar_preview_pickup(query, context, edit=edit)


def pedido_pickup_preview_callback(update, context):
    """Maneja la confirmacion o cambio del pickup previsualizado."""
    query = update.callback_query
    query.answer()
    data = query.data

    _clear_pickup_preview_location(context, _pickup_preview_chat_id(query))

    if data == PICKUP_PREVIEW_CONFIRM_CALLBACK:
        logger.info(
            "pickup_preview_confirmed ally_id=%s chat_id=%s",
            context.user_data.get("ally_id"),
            _pickup_preview_chat_id(query),
        )
        return _continuar_flujo_despues_pickup_confirmado(query, context, edit=True)

    if data == PICKUP_PREVIEW_CHANGE_CALLBACK:
        logger.info(
            "pickup_preview_change_requested ally_id=%s chat_id=%s",
            context.user_data.get("ally_id"),
            _pickup_preview_chat_id(query),
        )
        return mostrar_selector_pickup(query, context, edit=True)

    query.edit_message_text("Opcion no valida.")
    return ConversationHandler.END


def _pedido_incentivo_keyboard(prefix: str = "pedido_inc_", order_id: int = None):
    """
    Botones de incentivo (pre y post oferta).
    - Pre: callback_data=pedido_inc_1000 / pedido_inc_otro
    - Post: callback_data=pedido_inc_{order_id}x{monto} / pedido_inc_otro_{order_id}
    """
    if order_id is None:
        return [
            [
                InlineKeyboardButton("+1500", callback_data=f"{prefix}1500"),
                InlineKeyboardButton("+2000", callback_data=f"{prefix}2000"),
                InlineKeyboardButton("+3000", callback_data=f"{prefix}3000"),
            ],
            [InlineKeyboardButton("Otro monto", callback_data=f"{prefix}otro")],
        ]

    return [
        [
            InlineKeyboardButton("+1000", callback_data=f"{prefix}{order_id}x1000"),
            InlineKeyboardButton("+1500", callback_data=f"{prefix}{order_id}x1500"),
        ],
        [
            InlineKeyboardButton("+2000", callback_data=f"{prefix}{order_id}x2000"),
            InlineKeyboardButton("+3000", callback_data=f"{prefix}{order_id}x3000"),
        ],
        [InlineKeyboardButton("Otro monto", callback_data=f"{prefix}otro_{order_id}")],
    ]


def _pedido_confirmacion_keyboard(context):
    """Teclado de confirmacion: incentivos + agregar parada + confirmar + cancelar."""
    paradas_extra = context.user_data.get("pedido_paradas_extra", [])
    n_extras = len(paradas_extra)
    confirmar_label = "Confirmar ruta ({} paradas)".format(n_extras + 1) if n_extras else "Confirmar pedido"
    rows = _pedido_incentivo_keyboard()
    if paradas_extra:
        demand_preview = build_offer_demand_preview(
            pickup_lat=context.user_data.get("pickup_lat"),
            pickup_lng=context.user_data.get("pickup_lng"),
            distance_km=context.user_data.get("ruta_distancia_desde_pedido", 0),
            ally_id=context.user_data.get("ally_id"),
            requires_cash=context.user_data.get("requires_cash", False),
            cash_required_amount=context.user_data.get("cash_required_amount", 0),
            current_incentive=int(context.user_data.get("pedido_incentivo", 0) or 0),
        )
    else:
        demand_preview = build_offer_demand_preview(
            pickup_lat=context.user_data.get("pickup_lat"),
            pickup_lng=context.user_data.get("pickup_lng"),
            distance_km=context.user_data.get("quote_distance_km", 0),
            ally_id=context.user_data.get("ally_id"),
            requires_cash=context.user_data.get("requires_cash", False),
            cash_required_amount=context.user_data.get("cash_required_amount", 0),
            current_incentive=int(context.user_data.get("pedido_incentivo", 0) or 0),
        )
    suggested_row = build_offer_suggestion_button_row(
        demand_preview,
        "pedido_inc_{amount}",
        allowed_amounts=(1000, 1500, 2000, 3000),
    )
    if suggested_row:
        rows.insert(0, suggested_row)
    rows.append([InlineKeyboardButton("+ Agregar otra entrega", callback_data="pedido_agregar_parada")])
    rows.append([
        InlineKeyboardButton("Cambiar recogida", callback_data="pedido_edit_pickup"),
        InlineKeyboardButton("Cambiar instrucciones", callback_data="pedido_edit_instruc"),
    ])
    rows.append([InlineKeyboardButton("Cambiar direccion entrega", callback_data="pedido_edit_dir")])
    rows.append([InlineKeyboardButton(confirmar_label, callback_data="pedido_confirmar")])
    rows.append([InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")])
    return rows


def _haversine_km_inline(lat1, lng1, lat2, lng2):
    """Calcula distancia Haversine en km entre dos puntos."""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _construir_resumen_ruta_desde_pedido(context):
    """Construye el resumen de ruta cuando hay paradas extra en un pedido."""
    pickup_label = context.user_data.get("pickup_label", "")
    pickup_address = context.user_data.get("pickup_address", "")
    if pickup_label and pickup_address:
        recogida = "{}: {}".format(pickup_label, pickup_address)
    elif pickup_address:
        recogida = pickup_address
    else:
        recogida = "-"

    primera = {
        "name": context.user_data.get("customer_name", "-"),
        "phone": context.user_data.get("customer_phone", "-"),
        "address": context.user_data.get("customer_address", "-"),
        "city": context.user_data.get("customer_city", ""),
        "barrio": context.user_data.get("customer_barrio", ""),
        "lat": context.user_data.get("dropoff_lat"),
        "lng": context.user_data.get("dropoff_lng"),
    }
    paradas_extra = context.user_data.get("pedido_paradas_extra", [])
    all_paradas = [primera] + paradas_extra

    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")

    # Distancia total: primer tramo ya calculado + tramos extra por Haversine
    total_km = float(context.user_data.get("quote_distance_km") or 0)
    for i in range(1, len(all_paradas)):
        prev = all_paradas[i - 1]
        curr = all_paradas[i]
        if has_valid_coords(prev.get("lat"), prev.get("lng")) and has_valid_coords(curr.get("lat"), curr.get("lng")):
            total_km += _haversine_km_inline(prev["lat"], prev["lng"], curr["lat"], curr["lng"])

    paradas_opt, _, fue_optimizado = optimizar_orden_paradas(pickup_lat, pickup_lng, all_paradas)
    if fue_optimizado:
        all_paradas = paradas_opt
        context.user_data["pedido_paradas_extra"] = all_paradas[1:]

    precio_info = calcular_precio_ruta_inteligente(total_km, all_paradas, pickup_lat=pickup_lat, pickup_lng=pickup_lng)
    context.user_data["ruta_precio_desde_pedido"] = precio_info
    context.user_data["ruta_paradas_desde_pedido"] = all_paradas
    context.user_data["ruta_distancia_desde_pedido"] = total_km

    distance_fee = precio_info["distance_fee"]
    additional_fee = precio_info["additional_stops_fee"]
    total_fee = precio_info["total_fee"]
    stop_fee = precio_info.get("tarifa_parada_adicional", 0)
    mensaje_ahorro = precio_info.get("mensaje_ahorro", "")
    incentivo = int(context.user_data.get("pedido_incentivo", 0) or 0)
    requires_cash = bool(context.user_data.get("requires_cash"))
    cash_required_amount = int(context.user_data.get("cash_required_amount") or 0)

    text = "RUTA DE ENTREGA\n"
    if fue_optimizado:
        text += "(Orden optimizado para menor distancia)\n"
    text += "\nRecoge en: {}\n\n".format(recogida)
    for i, p in enumerate(all_paradas, 1):
        text += "Parada {}:\n  Cliente: {} - {}\n  Direccion: {}\n".format(
            i, p.get("name") or "-", p.get("phone") or "", p.get("address") or "-"
        )
    text += "\nDistancia total: {:.1f} km\n".format(total_km)
    text += "Precio base (distancia): ${:,}\n".format(distance_fee)
    if additional_fee > 0:
        text += "Paradas adicionales ({} x ${:,}): ${:,}\n".format(len(all_paradas) - 1, stop_fee, additional_fee)
    total_con_incentivo = total_fee + incentivo
    text += "TOTAL: ${:,}".format(total_con_incentivo)
    if mensaje_ahorro:
        text += "\n{}".format(mensaje_ahorro)
    if incentivo > 0:
        text += "\nIncentivo adicional: +${:,}".format(incentivo)
    if requires_cash and cash_required_amount > 0:
        text += "\nBase requerida: ${:,}".format(cash_required_amount)
    demand_preview = build_offer_demand_preview(
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        distance_km=total_km,
        ally_id=context.user_data.get("ally_id"),
        requires_cash=requires_cash,
        cash_required_amount=cash_required_amount,
        current_incentive=incentivo,
    )
    demand_block = build_offer_demand_badge_text(demand_preview)
    if demand_block:
        text += "\n\n{}".format(demand_block)
    text += (
        "\n\nSi agregas incentivo, es mas probable que te tomen rapido.\n\n"
        "Confirmas esta ruta?"
    )
    return text


def construir_resumen_pedido(context):
    """Construye el texto del resumen del pedido. Si hay paradas extra, devuelve resumen de ruta."""
    if context.user_data.get("pedido_paradas_extra"):
        return _construir_resumen_ruta_desde_pedido(context)
    tipo_servicio = context.user_data.get("service_type", "-")
    nombre = context.user_data.get("customer_name", "-")
    telefono = context.user_data.get("customer_phone", "-")
    direccion = context.user_data.get("customer_address", "-")
    pickup_label = context.user_data.get("pickup_label", "")
    pickup_address = context.user_data.get("pickup_address", "")
    distancia = context.user_data.get("quote_distance_km", 0)
    subtotal_servicio = int(context.user_data.get("quote_price", 0) or 0)
    tarifa_distancia = int(context.user_data.get("quote_distance_fee", subtotal_servicio) or 0)
    incentivo = int(context.user_data.get("pedido_incentivo", 0) or 0)
    pedido_parking_fee = int(context.user_data.get("pedido_parking_fee") or 0)
    total = subtotal_servicio + incentivo + pedido_parking_fee
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

    # Si es Compras, mostrar lista y desglose de precio
    if tipo_servicio == "Compras":
        buy_list = context.user_data.get("buy_products_list", "")
        if buy_list:
            resumen += f"Lista de productos:\n{buy_list}\n"
        if buy_products > 0:
            resumen += "Tarifa distancia: " + _fmt_pesos(tarifa_distancia) + "\n"
            resumen += f"Total unidades: {buy_products}\n"
            if buy_surcharge > 0:
                resumen += "Recargo productos: " + _fmt_pesos(buy_surcharge) + "\n"

    resumen += "Subtotal del servicio: " + _fmt_pesos(subtotal_servicio) + "\n"
    if incentivo > 0:
        resumen += "Incentivo adicional: " + _fmt_pesos(incentivo) + "\n"
    if pedido_parking_fee > 0:
        resumen += "Punto con parqueo dificil: +" + _fmt_pesos(pedido_parking_fee) + "\n"
    resumen += "Total a pagar: " + _fmt_pesos(total) + "\n"

    if requires_cash and cash_amount > 0:
        resumen += "Base requerida: " + _fmt_pesos(cash_amount) + "\n"

    purchase_amount = context.user_data.get("pedido_purchase_amount")
    if purchase_amount is not None:
        resumen += "Valor de compra: " + _fmt_pesos(purchase_amount) + "\n"

    # Calcular subsidio efectivo al cliente y cachear en user_data para create_order
    ally_id_ctx = context.user_data.get("ally_id")
    subsidio_efectivo_cache = 0
    customer_delivery_fee_cache = None
    if ally_id_ctx and subtotal_servicio > 0:
        try:
            ally_row = get_ally_by_id(ally_id_ctx)
            if ally_row:
                delivery_subsidy = int(ally_row["delivery_subsidy"] or 0)
                try:
                    min_purchase_sub = ally_row["min_purchase_for_subsidy"]
                except (KeyError, IndexError):
                    min_purchase_sub = None
                subsidio_efectivo_cache = compute_ally_subsidy(delivery_subsidy, min_purchase_sub, purchase_amount)
                customer_delivery_fee_cache = max(subtotal_servicio - subsidio_efectivo_cache, 0)
        except Exception as _e:
            logger.warning("construir_resumen_pedido: error calculando subsidio ally=%s err=%s", 
                ally_id_ctx, _e)
    # Persistir en user_data para que pedido_confirmacion_callback los pase a create_order
    context.user_data["pedido_subsidio_efectivo"] = subsidio_efectivo_cache
    context.user_data["pedido_customer_delivery_fee"] = customer_delivery_fee_cache
    if subsidio_efectivo_cache > 0 and customer_delivery_fee_cache is not None:
        resumen += "Subsidio domicilio: -" + _fmt_pesos(subsidio_efectivo_cache) + "\n"
        resumen += "Domicilio al cliente: " + _fmt_pesos(customer_delivery_fee_cache) + "\n"

    demand_preview = build_offer_demand_preview(
        pickup_lat=context.user_data.get("pickup_lat"),
        pickup_lng=context.user_data.get("pickup_lng"),
        distance_km=distancia,
        ally_id=ally_id_ctx,
        requires_cash=requires_cash,
        cash_required_amount=cash_amount,
        current_incentive=incentivo,
    )
    demand_block = build_offer_demand_badge_text(demand_preview)
    if demand_block:
        resumen += "\n" + demand_block + "\n"

    # Aviso de precio estimado cuando se uso Haversine (sin red vial real)
    dist_source = context.user_data.get("distance_source", "")
    if "haversine" in dist_source:
        resumen += (
            "\nAVISO: precio estimado. No se pudo calcular la distancia por carretera "
            "en este momento. El precio real puede ser mayor si la ruta tiene curvas o desvios. "
            "Considera agregar un incentivo.\n"
        )

    resumen += (
        "\nSi agregas incentivo, es mas probable que te tomen rapido.\n\n"
        "Deseas agregar un incentivo antes de confirmar? (Tambien puedes hacerlo despues de publicar)\n\n"
        "Confirmas este pedido?"
    )
    return resumen


def mostrar_resumen_confirmacion(query, context, edit=True):
    """Muestra resumen del pedido con botones de confirmacion (para CallbackQuery)."""
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")
    if pickup_lat is None or pickup_lng is None:
        return mostrar_selector_pickup(query, context, edit=True)

    keyboard = _pedido_confirmacion_keyboard(context)
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    if edit:
        query.edit_message_text(resumen, reply_markup=reply_markup)
    else:
        query.message.reply_text(resumen, reply_markup=reply_markup)

    return PEDIDO_CONFIRMACION


def mostrar_resumen_confirmacion_msg(update, context):
    """Muestra resumen del pedido con botones de confirmacion (para Message)."""
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")
    if pickup_lat is None or pickup_lng is None:
        return mostrar_selector_pickup(update, context, edit=False)

    keyboard = _pedido_confirmacion_keyboard(context)
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    update.message.reply_text(resumen, reply_markup=reply_markup)
    return PEDIDO_CONFIRMACION


def pedido_confirmacion(update, context):
    """Fallback: redirige a botones si el usuario escribe texto."""
    # Mostrar resumen con botones
    return mostrar_resumen_confirmacion_msg(update, context)


# ---- Editar campos desde el preview (nuevo_pedido_conv) ----

def pedido_edit_instruc_callback(update, context):
    """Desde el preview: volver a pedir instrucciones al repartidor."""
    query = update.callback_query
    query.answer()
    context.user_data["pedido_edit_from_preview"] = True
    query.edit_message_text(
        "Escribe las instrucciones para el repartidor "
        "(o escribe 'ninguna' para dejar en blanco):"
    )
    return PEDIDO_INSTRUCCIONES_EXTRA


def pedido_edit_dir_callback(update, context):
    """Desde el preview: volver a pedir la direccion de entrega."""
    query = update.callback_query
    query.answer()
    context.user_data["pedido_edit_from_preview"] = True
    query.edit_message_text(
        "Escribe la nueva direccion de entrega, comparte ubicacion GPS "
        "o pega un link de Google Maps:"
    )
    return PEDIDO_UBICACION


def pedido_edit_pickup_callback(update, context):
    """Desde el preview: volver a seleccionar punto de recogida."""
    query = update.callback_query
    query.answer()
    context.user_data["pedido_edit_from_preview"] = True
    return mostrar_selector_pickup(query, context, edit=True)


def pedido_incentivo_fixed_callback(update, context):
    """Agrega incentivo (botones +1000/+1500/+2000/+3000) antes de confirmar pedido."""
    query = update.callback_query
    query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) != 3:
        return PEDIDO_CONFIRMACION
    if parts[0] != "pedido" or parts[1] != "inc":
        return PEDIDO_CONFIRMACION
    try:
        delta = int(parts[2])
    except Exception:
        return PEDIDO_CONFIRMACION
    if delta <= 0:
        return PEDIDO_CONFIRMACION

    current = int(context.user_data.get("pedido_incentivo", 0) or 0)
    context.user_data["pedido_incentivo"] = current + delta
    return mostrar_resumen_confirmacion(query, context, edit=True)


def pedido_incentivo_otro_start(update, context):
    """Pide al aliado ingresar un incentivo adicional por texto (antes de confirmar)."""
    query = update.callback_query
    query.answer()
    context.user_data.pop("pedido_incentivo_edit_order_id", None)
    query.edit_message_text(
        "Escribe el incentivo adicional en pesos (solo numeros).\n"
        "Ejemplo: 2500\n\n"
        "Escribe 'cancelar' para volver al menu."
    )
    return PEDIDO_INCENTIVO_MONTO


def pedido_incentivo_monto_handler(update, context):
    """Recibe incentivo adicional por texto antes de confirmar."""
    text = (update.message.text or "").strip()
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return PEDIDO_INCENTIVO_MONTO
    try:
        delta = int(digits)
    except Exception:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return PEDIDO_INCENTIVO_MONTO
    if delta <= 0:
        update.message.reply_text("El incentivo debe ser mayor a 0.")
        return PEDIDO_INCENTIVO_MONTO
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto.")
        return PEDIDO_INCENTIVO_MONTO

    current = int(context.user_data.get("pedido_incentivo", 0) or 0)
    context.user_data["pedido_incentivo"] = current + delta
    return mostrar_resumen_confirmacion_msg(update, context)


def _pedido_incentivo_menu_text(order):
    order_id = int(order["id"])
    incentive = int(order["additional_incentive"] or 0)
    total_fee = int(order["total_fee"] or 0)
    return (
        "INCENTIVO DEL PEDIDO\n\n"
        "Pedido: #{}\n"
        "Incentivo actual: {}\n"
        "Pago total: {}\n\n"
        "Sugerencia: En horas de alta demanda los repartidores toman primero los servicios mejor pagos. "
        "Si agregas incentivo, es mas probable que te tomen rapido."
    ).format(order_id, _fmt_pesos(incentive), _fmt_pesos(total_fee))


def _get_refreshed_order_after_incentive_update(order_id):
    """
    Recarga el pedido despues de aumentar incentivo para que notificaciones y UI
    salgan siempre del estado ya persistido en BD.
    """
    return get_order_by_id(int(order_id))


def pedido_incentivo_menu_callback(update, context):
    """Muestra menú para aumentar incentivo de un pedido ya creado."""
    query = update.callback_query
    query.answer()
    parts = query.data.split("_")
    if len(parts) != 4:
        query.edit_message_text("Accion invalida.")
        return
    try:
        order_id = int(parts[3])
    except Exception:
        query.edit_message_text("Accion invalida.")
        return

    telegram_id = update.effective_user.id
    ok, order, msg = ally_get_order_for_incentive(telegram_id, order_id)
    if not ok:
        query.edit_message_text(msg)
        return

    keyboard = _pedido_incentivo_keyboard(order_id=order_id)
    query.edit_message_text(_pedido_incentivo_menu_text(order), reply_markup=InlineKeyboardMarkup(keyboard))


def pedido_incentivo_existing_fixed_callback(update, context):
    """Agrega incentivo (botones +1000/+1500/+2000/+3000) a pedido existente."""
    query = update.callback_query
    query.answer()
    if not query.data.startswith("pedido_inc_"):
        query.edit_message_text("Accion invalida.")
        return
    payload = query.data[len("pedido_inc_"):]
    if "x" not in payload:
        query.edit_message_text("Accion invalida.")
        return
    chunks = payload.split("x", 1)
    try:
        order_id = int(chunks[0])
        delta = int(chunks[1])
    except Exception:
        query.edit_message_text("Accion invalida.")
        return

    telegram_id = update.effective_user.id
    ok, order, courier_telegram_id, msg = ally_increment_order_incentive(telegram_id, order_id, delta)
    if not ok:
        query.edit_message_text(msg)
        return

    # Usar siempre el pedido recargado para evitar textos con totals parciales.
    refreshed_order = _get_refreshed_order_after_incentive_update(order_id) or order

    # Notificar al aliado
    try:
        incentive = int(refreshed_order["additional_incentive"] or 0)
        total_fee = int(refreshed_order["total_fee"] or 0)
        context.bot.send_message(
            chat_id=telegram_id,
            text=(
                "Incentivo agregado al pedido #{}:\n"
                "Incentivo adicional: +{}\n"
                "Total incentivos: {}\n"
                "Nuevo pago total: {}"
            ).format(order_id, _fmt_pesos(delta), _fmt_pesos(incentive), _fmt_pesos(total_fee)),
        )
    except Exception:
        pass

    # Si el pedido sigue en oferta (PUBLISHED), re-ofertar para que los couriers vean el nuevo pago.
    try:
        repost_order_to_couriers(order_id, context)
    except Exception:
        pass

    if courier_telegram_id:
        try:
            incentive = int(refreshed_order["additional_incentive"] or 0)
            total_fee = int(refreshed_order["total_fee"] or 0)
            context.bot.send_message(
                chat_id=courier_telegram_id,
                text=(
                    "Actualizacion de pedido #{}:\n"
                    "El aliado aumento el incentivo.\n"
                    "Incentivo adicional: {}\n"
                    "Pago total: {}"
                ).format(order_id, _fmt_pesos(incentive), _fmt_pesos(total_fee)),
            )
        except Exception:
            pass

    keyboard = _pedido_incentivo_keyboard(order_id=order_id)
    query.edit_message_text(_pedido_incentivo_menu_text(refreshed_order), reply_markup=InlineKeyboardMarkup(keyboard))


def pedido_incentivo_existing_otro_start(update, context):
    """Inicia captura de 'Otro monto' para un pedido existente."""
    query = update.callback_query
    query.answer()
    parts = query.data.split("_")
    if len(parts) != 4:
        query.edit_message_text("Accion invalida.")
        return ConversationHandler.END
    try:
        order_id = int(parts[3])
    except Exception:
        query.edit_message_text("Accion invalida.")
        return ConversationHandler.END

    context.user_data["pedido_incentivo_edit_order_id"] = order_id
    query.edit_message_text(
        "Escribe el incentivo adicional en pesos (solo numeros).\n"
        "Ejemplo: 2500\n\n"
        "Escribe 'cancelar' para salir."
    )
    return PEDIDO_INCENTIVO_MONTO


def pedido_incentivo_existing_monto_handler(update, context):
    """Recibe incentivo adicional por texto para un pedido existente."""
    order_id = context.user_data.get("pedido_incentivo_edit_order_id")
    if not order_id:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return PEDIDO_INCENTIVO_MONTO

    try:
        delta = int(digits)
    except Exception:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return PEDIDO_INCENTIVO_MONTO

    if delta <= 0:
        update.message.reply_text("El incentivo debe ser mayor a 0.")
        return PEDIDO_INCENTIVO_MONTO
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto.")
        return PEDIDO_INCENTIVO_MONTO

    telegram_id = update.effective_user.id
    ok, order, courier_telegram_id, msg = ally_increment_order_incentive(telegram_id, int(order_id), int(delta))
    if not ok:
        update.message.reply_text(msg)
        context.user_data.pop("pedido_incentivo_edit_order_id", None)
        return ConversationHandler.END

    context.user_data.pop("pedido_incentivo_edit_order_id", None)
    refreshed_order = _get_refreshed_order_after_incentive_update(order_id) or order

    # Notificar al aliado
    try:
        incentive = int(refreshed_order["additional_incentive"] or 0)
        total_fee = int(refreshed_order["total_fee"] or 0)
        context.bot.send_message(
            chat_id=telegram_id,
            text=(
                "Incentivo agregado al pedido #{}:\n"
                "Incentivo adicional: +{}\n"
                "Total incentivos: {}\n"
                "Nuevo pago total: {}"
            ).format(int(order_id), _fmt_pesos(delta), _fmt_pesos(incentive), _fmt_pesos(total_fee)),
        )
    except Exception:
        pass

    # Si el pedido sigue en oferta (PUBLISHED), re-ofertar para que los couriers vean el nuevo pago.
    try:
        repost_order_to_couriers(int(order_id), context)
    except Exception:
        pass

    if courier_telegram_id:
        try:
            incentive = int(refreshed_order["additional_incentive"] or 0)
            total_fee = int(refreshed_order["total_fee"] or 0)
            context.bot.send_message(
                chat_id=courier_telegram_id,
                text=(
                    "Actualizacion de pedido #{}:\n"
                    "El aliado aumento el incentivo.\n"
                    "Incentivo adicional: {}\n"
                    "Pago total: {}"
                ).format(int(order_id), _fmt_pesos(incentive), _fmt_pesos(total_fee)),
            )
        except Exception:
            pass

    keyboard = _pedido_incentivo_keyboard(order_id=int(order_id))
    update.message.reply_text(_pedido_incentivo_menu_text(refreshed_order), reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


# ── Sugerencia de incentivo T+5 (aplica a todos los pedidos: aliados y admin) ──

def offer_suggest_inc_fixed_callback(update, context):
    """Botones +1500/+2000/+3000 de la sugerencia T+5."""
    query = update.callback_query
    query.answer()
    data = query.data  # offer_inc_{order_id}x{delta}
    try:
        parts = data.replace("offer_inc_", "").split("x")
        order_id = int(parts[0])
        delta = int(parts[1])
    except Exception:
        query.edit_message_text("Error al procesar el incentivo.")
        return

    telegram_id = update.effective_user.id
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    # Determinar si el creador es aliado o admin
    creator_admin_id = order.get("creator_admin_id") if hasattr(order, "get") else order["creator_admin_id"]
    if creator_admin_id:
        ok, updated, courier_tid, msg = admin_increment_order_incentive(telegram_id, order_id, delta)
    else:
        ok, updated, courier_tid, msg = ally_increment_order_incentive(telegram_id, order_id, delta)

    if not ok:
        query.edit_message_text(msg)
        return

    refreshed_order = _get_refreshed_order_after_incentive_update(order_id) or updated

    # Re-ofertar a todos los couriers y re-programar T+5
    repost_count = repost_order_to_couriers(order_id, context)

    total_fee = int(refreshed_order["total_fee"] or 0)
    incentive = int(refreshed_order["additional_incentive"] or 0)
    
    # Notificar al creador (aliado o admin)
    context.bot.send_message(
        chat_id=telegram_id,
        text=(
            "Incentivo agregado al pedido #{}:\n"
            "Incentivo adicional: +{}\n"
            "Total incentivos: {}\n"
            "Nuevo pago total: {}\n\n"
            "Re-ofertando a {} repartidores activos."
        ).format(order_id, _fmt_pesos(delta), _fmt_pesos(incentive), _fmt_pesos(total_fee), repost_count),
    )

    query.edit_message_text(
        "Incentivo agregado: +${:,}\n"
        "Incentivo acumulado: ${:,}\n"
        "Tarifa total del pedido: ${:,}\n"
        "Re-ofertando a {} repartidores activos.".format(
            delta, incentive, total_fee, repost_count
        )
    )


def offer_suggest_inc_otro_start(update, context):
    """Boton 'Otro monto' de la sugerencia T+5."""
    query = update.callback_query
    query.answer()
    data = query.data  # offer_inc_otro_{order_id}
    try:
        order_id = int(data.replace("offer_inc_otro_", ""))
    except Exception:
        query.edit_message_text("Error al procesar la solicitud.")
        return ConversationHandler.END

    order = get_order_by_id(order_id)
    if not order or order["status"] not in ("PENDING", "PUBLISHED"):
        query.edit_message_text("Este pedido ya no permite agregar incentivo.")
        return ConversationHandler.END

    context.user_data["offer_suggest_edit_order_id"] = order_id
    query.edit_message_text("Ingresa el monto del incentivo que deseas agregar (en pesos COP, solo numeros):")
    return OFFER_SUGGEST_INC_MONTO


def offer_suggest_inc_monto_handler(update, context):
    """Recibe monto libre de incentivo de la sugerencia T+5."""
    order_id = context.user_data.get("offer_suggest_edit_order_id")
    if not order_id:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return OFFER_SUGGEST_INC_MONTO

    try:
        delta = int(digits)
    except Exception:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return OFFER_SUGGEST_INC_MONTO

    if delta <= 0:
        update.message.reply_text("El incentivo debe ser mayor a 0.")
        return OFFER_SUGGEST_INC_MONTO
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto (maximo $200,000).")
        return OFFER_SUGGEST_INC_MONTO

    telegram_id = update.effective_user.id
    order = get_order_by_id(order_id)
    creator_admin_id = order.get("creator_admin_id") if (order and hasattr(order, "get")) else (order["creator_admin_id"] if order else None)

    if creator_admin_id:
        ok, updated, courier_tid, msg = admin_increment_order_incentive(telegram_id, int(order_id), delta)
    else:
        ok, updated, courier_tid, msg = ally_increment_order_incentive(telegram_id, int(order_id), delta)

    context.user_data.pop("offer_suggest_edit_order_id", None)

    if not ok:
        update.message.reply_text(msg)
        return ConversationHandler.END

    refreshed_order = _get_refreshed_order_after_incentive_update(order_id) or updated
    repost_count = repost_order_to_couriers(int(order_id), context)
    total_fee = int(refreshed_order["total_fee"] or 0)
    incentive = int(refreshed_order["additional_incentive"] or 0)
    
    # Notificar al creador (aliado o admin)
    context.bot.send_message(
        chat_id=telegram_id,
        text=(
            "Incentivo agregado al pedido #{}:\n"
            "Incentivo adicional: +{}\n"
            "Total incentivos: {}\n"
            "Nuevo pago total: {}\n\n"
            "Re-ofertando a {} repartidores activos."
        ).format(order_id, _fmt_pesos(delta), _fmt_pesos(incentive), _fmt_pesos(total_fee), repost_count),
    )
    
    update.message.reply_text(
        "Incentivo agregado: +${:,}\n"
        "Incentivo acumulado: ${:,}\n"
        "Tarifa total del pedido: ${:,}\n"
        "Re-ofertando a {} repartidores activos.".format(
            delta, incentive, total_fee, repost_count
        )
    )
    return ConversationHandler.END


# ── Sugerencia de incentivo T+5 para RUTAS ──

def route_suggest_inc_fixed_callback(update, context):
    """Botones +1500/+2000/+3000 de la sugerencia T+5 para rutas."""
    query = update.callback_query
    query.answer()
    data = query.data  # ruta_inc_{route_id}x{delta}
    try:
        parts = data.replace("ruta_inc_", "").split("x")
        route_id = int(parts[0])
        delta = int(parts[1])
    except Exception:
        query.edit_message_text("Error al procesar el incentivo.")
        return

    route = get_route_by_id(route_id)
    if not route or route["status"] not in ("PUBLISHED",):
        query.edit_message_text("Esta ruta ya no permite agregar incentivo.")
        return

    if delta <= 0 or delta > 200000:
        query.edit_message_text("Monto de incentivo no valido.")
        return

    add_route_incentive(route_id, delta)
    repost_count = repost_route_to_couriers(route_id, context)

    route = get_route_by_id(route_id)
    total_fee = int(route["total_fee"] or 0) if route else 0
    incentive = int(route["additional_incentive"] or 0) if route else delta

    # Notificar al creador
    try:
        telegram_id = update.effective_user.id
        context.bot.send_message(
            chat_id=telegram_id,
            text=(
                "Incentivo agregado a la ruta #{}:\n"
                "Incentivo adicional: +{}\n"
                "Total incentivos: {}\n"
                "Nuevo pago total: {}\n\n"
                "Re-ofertando a {} repartidores activos."
            ).format(route_id, _fmt_pesos(delta), _fmt_pesos(incentive), _fmt_pesos(total_fee), repost_count),
        )
    except Exception as e:
        logger.warning("Error al notificar al creador de la ruta: %s", e)

    query.edit_message_text(
        "Incentivo agregado: +${:,}\n"
        "Incentivo acumulado: ${:,}\n"
        "Tarifa total de la ruta: ${:,}\n"
        "Re-ofertando a {} repartidores activos.".format(
            delta, incentive, total_fee, repost_count
        )
    )


def route_suggest_inc_otro_start(update, context):
    """Boton 'Otro monto' de la sugerencia T+5 para rutas."""
    query = update.callback_query
    query.answer()
    data = query.data  # ruta_inc_otro_{route_id}
    try:
        route_id = int(data.replace("ruta_inc_otro_", ""))
    except Exception:
        query.edit_message_text("Error al procesar la solicitud.")
        return ConversationHandler.END

    route = get_route_by_id(route_id)
    if not route or route["status"] not in ("PUBLISHED",):
        query.edit_message_text("Esta ruta ya no permite agregar incentivo.")
        return ConversationHandler.END

    context.user_data["route_suggest_edit_route_id"] = route_id
    query.edit_message_text("Ingresa el monto del incentivo que deseas agregar (en pesos COP, solo numeros):")
    return ROUTE_SUGGEST_INC_MONTO


def route_suggest_inc_monto_handler(update, context):
    """Recibe monto libre de incentivo de la sugerencia T+5 para rutas."""
    route_id = context.user_data.get("route_suggest_edit_route_id")
    if not route_id:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return ROUTE_SUGGEST_INC_MONTO

    try:
        delta = int(digits)
    except Exception:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return ROUTE_SUGGEST_INC_MONTO

    if delta <= 0:
        update.message.reply_text("El incentivo debe ser mayor a 0.")
        return ROUTE_SUGGEST_INC_MONTO
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto (maximo $200,000).")
        return ROUTE_SUGGEST_INC_MONTO

    add_route_incentive(int(route_id), delta)
    repost_count = repost_route_to_couriers(int(route_id), context)

    context.user_data.pop("route_suggest_edit_route_id", None)

    route = get_route_by_id(route_id)
    total_fee = int(route["total_fee"] or 0) if route else 0
    incentive = int(route["additional_incentive"] or 0) if route else delta
    
    # Notificar al creador
    try:
        telegram_id = update.effective_user.id
        context.bot.send_message(
            chat_id=telegram_id,
            text=(
                "Incentivo agregado a la ruta #{}:\n"
                "Incentivo adicional: +{}\n"
                "Total incentivos: {}\n"
                "Nuevo pago total: {}\n\n"
                "Re-ofertando a {} repartidores activos."
            ).format(route_id, _fmt_pesos(delta), _fmt_pesos(incentive), _fmt_pesos(total_fee), repost_count),
        )
    except Exception as e:
        logger.warning("Error al notificar al creador de la ruta: %s", e)

    update.message.reply_text(
        "Incentivo agregado: +${:,}\n"
        "Incentivo acumulado: ${:,}\n"
        "Tarifa total de la ruta: ${:,}\n"
        "Re-ofertando a {} repartidores activos.".format(
            delta, incentive, total_fee, repost_count
        )
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────
# PEDIDO ESPECIAL ADMIN
# ─────────────────────────────────────────────────────────────────────────
def _admin_ped_courier_preview_block(ctx):
    """Bloque espejo del mensaje real que recibira el courier antes de aceptar."""
    requires_cash = bool(ctx.get("admin_ped_requires_cash"))
    cash_required_amount = int(ctx.get("admin_ped_cash_required_amount") or 0)
    draft_order = {
        "id": ctx.get("admin_ped_order_id") or "preview",
        "distance_km": float(ctx.get("admin_ped_distance_km") or 0),
        "total_fee": int(ctx.get("admin_ped_tarifa") or 0) + int(ctx.get("admin_ped_incentivo") or 0),
        "additional_incentive": int(ctx.get("admin_ped_incentivo") or 0),
        "payment_method": _pedido_payment_method_from_base(requires_cash, cash_required_amount),
        "requires_cash": requires_cash,
        "cash_required_amount": cash_required_amount,
        "instructions": ctx.get("admin_ped_instruc") or "",
        "parking_fee": int(ctx.get("admin_ped_parking_fee") or 0),
        "special_commission": int(ctx.get("admin_ped_comision") or 0),
        "pickup_address": ctx.get("admin_ped_pickup_addr") or "",
        "customer_address": ctx.get("admin_ped_cust_addr") or "",
    }
    return build_courier_order_preview_text(
        draft_order,
        pickup_city_override=ctx.get("admin_ped_pickup_city"),
        pickup_barrio_override=ctx.get("admin_ped_pickup_barrio"),
        dropoff_city_override=ctx.get("admin_ped_dropoff_city"),
        dropoff_barrio_override=ctx.get("admin_ped_dropoff_barrio"),
    )


def _admin_ped_preview_text(ctx):
    """Construye texto y teclado del preview del pedido especial del admin."""
    tarifa = int(ctx.get("admin_ped_tarifa") or 0)
    incentivo = int(ctx.get("admin_ped_incentivo") or 0)
    parking_fee = int(ctx.get("admin_ped_parking_fee") or 0)
    requires_cash = bool(ctx.get("admin_ped_requires_cash"))
    cash_required_amount = int(ctx.get("admin_ped_cash_required_amount") or 0)
    comision = int(ctx.get("admin_ped_comision") or 0)
    team_only = int(ctx.get("admin_ped_team_only") or 0)
    total = tarifa + incentivo
    distancia_km = float(ctx.get("admin_ped_distance_km") or 0)
    instruc = ctx.get("admin_ped_instruc") or "Ninguna"
    quote_source = ctx.get("admin_ped_quote_source") or "text"
    source_label = "Ruta estimada"
    if quote_source == "coords":
        source_label = "Ruta por coordenadas"
    elif "cache" in quote_source:
        source_label = "Ruta desde cache"
    elif "fallback" in quote_source:
        source_label = "Ruta estimada local"
    visibilidad_label = "Solo mi equipo" if team_only else "Todos los equipos"
    visibilidad_btn = "Cambiara: Todos los equipos" if team_only else "Cambiara: Solo mi equipo"
    # Calcular lo que el admin pagara a plataforma al entregar
    fee_cfg_prev = get_fee_config()
    platform_share = fee_cfg_prev["fee_platform_share"]
    tech_dev_pct = fee_cfg_prev["fee_special_order_tech_dev_pct"]
    admin_fee_plat = platform_share
    admin_fee_tech = round(tarifa * tech_dev_pct / 100) if (comision > 0 and tech_dev_pct > 0 and tarifa > 0) else 0
    admin_fee_total = admin_fee_plat + admin_fee_tech
    if admin_fee_tech > 0:
        admin_fee_line = "Tus fees al entregar: -${:,} (plataforma ${:,} + desarrollo {}% ${:,})".format(
            admin_fee_total, admin_fee_plat, tech_dev_pct, admin_fee_tech)
    else:
        admin_fee_line = "Tus fees al entregar: -${:,} (fee de plataforma)".format(admin_fee_plat)

    # Aviso de saldo bajo si el balance post-fee quedaria por debajo del minimo operativo
    saldo_bajo_warning = ""
    try:
        admin_id_prev = ctx.get("admin_ped_admin_id")
        if admin_id_prev:
            current_balance = get_admin_balance(int(admin_id_prev))
            balance_post_fee = current_balance - admin_fee_total
            if balance_post_fee < MIN_ADMIN_OPERATING_BALANCE:
                saldo_bajo_warning = (
                    "\n\nAVISO: tras cobrar los fees de este pedido tu saldo quedara en ${:,}, "
                    "por debajo del minimo operativo (${:,}). "
                    "Recarga tu cuenta pronto para poder seguir creando pedidos especiales.".format(
                        balance_post_fee, MIN_ADMIN_OPERATING_BALANCE)
                )
    except Exception:
        pass

    demand_preview = build_offer_demand_preview(
        pickup_lat=ctx.get("admin_ped_pickup_lat"),
        pickup_lng=ctx.get("admin_ped_pickup_lng"),
        distance_km=distancia_km,
        admin_id=ctx.get("admin_ped_admin_id"),
        team_only=bool(team_only),
        requires_cash=requires_cash,
        cash_required_amount=cash_required_amount,
        current_incentive=incentivo,
    )
    demand_block = build_offer_demand_badge_text(demand_preview)

    text = (
        "Resumen del pedido especial:\n\n"
        "Recogida: {}\n"
        "Cliente: {} / {}\n"
        "Entrega: {}\n"
        "Distancia: {:.1f} km ({})\n"
        "Tarifa al repartidor: ${:,}\n"
        "{}"
        "{}"
        "{}"
        "Comision al repartidor: {}\n"
        "{}\n"
        "Visibilidad: {}\n"
        "Instrucciones: {}\n\n"
        "Total oferta al courier: ${:,}"
        "{}"
        "{}"
        "\n\nPara cambiar las instrucciones escribe el nuevo texto en el chat."
        "\n\n{}"
    ).format(
        ctx.get("admin_ped_pickup_addr", ""),
        ctx.get("admin_ped_cust_name", ""),
        ctx.get("admin_ped_cust_phone", ""),
        ctx.get("admin_ped_cust_addr", ""),
        distancia_km,
        source_label,
        tarifa,
        "Incentivo: +${:,}\n".format(incentivo) if incentivo else "",
        "Punto con parqueo dificil: +${:,}\n".format(parking_fee) if parking_fee else "",
        "Base requerida: ${:,}\n".format(cash_required_amount) if requires_cash and cash_required_amount > 0 else "",
        "${:,}".format(comision) if comision > 0 else "Fee estandar al repartidor ($300)",
        admin_fee_line,
        visibilidad_label,
        instruc,
        total,
        "\n\n{}".format(demand_block) if demand_block else "",
        saldo_bajo_warning,
        _admin_ped_courier_preview_block(ctx),
    )
    keyboard = [
        [InlineKeyboardButton("Confirmar y publicar", callback_data="admin_pedido_confirmar")],
    ]
    suggested_row = build_offer_suggestion_button_row(
        demand_preview,
        "admin_pedido_inc_{amount}",
        allowed_amounts=(1000, 1500, 2000, 3000),
    )
    if suggested_row:
        keyboard.append(suggested_row)
    keyboard.extend([
        [
            InlineKeyboardButton("+$1,000", callback_data="admin_pedido_inc_1000"),
            InlineKeyboardButton("+$1,500", callback_data="admin_pedido_inc_1500"),
        ],
        [
            InlineKeyboardButton("+$2,000", callback_data="admin_pedido_inc_2000"),
            InlineKeyboardButton("+$3,000", callback_data="admin_pedido_inc_3000"),
        ],
        [InlineKeyboardButton("Otro incentivo", callback_data="admin_pedido_inc_otro")],
        [InlineKeyboardButton(visibilidad_btn, callback_data="admin_pedido_team_toggle")],
        [InlineKeyboardButton("Guardar como plantilla", callback_data="admin_pedido_guardar_plantilla")],
        [
            InlineKeyboardButton("Cambiar recogida", callback_data="admin_pedido_edit_pickup"),
            InlineKeyboardButton("Cambiar tarifa", callback_data="admin_pedido_edit_tarifa"),
        ],
        [InlineKeyboardButton("Cambiar cliente / entrega", callback_data="admin_pedido_edit_cust")],
        [InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")],
    ])
    return text, InlineKeyboardMarkup(keyboard)


def _admin_pedido_calcular_preview(update_or_query, context, edit=False):
    """Calcula la distancia del pedido especial admin y pide la tarifa manual al admin."""
    pickup_addr = context.user_data.get("admin_ped_pickup_addr", "")
    pickup_city = context.user_data.get("admin_ped_pickup_city", "")
    pickup_lat = context.user_data.get("admin_ped_pickup_lat")
    pickup_lng = context.user_data.get("admin_ped_pickup_lng")
    dropoff_addr = context.user_data.get("admin_ped_cust_addr", "")
    dropoff_city = context.user_data.get("admin_ped_dropoff_city", "")
    dropoff_lat = context.user_data.get("admin_ped_dropoff_lat")
    dropoff_lng = context.user_data.get("admin_ped_dropoff_lng")

    cotizacion = quote_order_from_inputs(
        pickup_text=pickup_addr,
        dropoff_text=dropoff_addr,
        pickup_city=pickup_city,
        dropoff_city=dropoff_city,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        dropoff_lat=dropoff_lat,
        dropoff_lng=dropoff_lng,
    )
    context.user_data.setdefault("admin_ped_incentivo", 0)
    context.user_data.setdefault("admin_ped_comision", 0)
    context.user_data.setdefault("admin_ped_team_only", 0)
    context.user_data["admin_ped_distance_km"] = cotizacion["distance_km"]
    context.user_data["admin_ped_quote_source"] = cotizacion.get("quote_source", "text")
    # Si veníamos de editar cliente/entrega desde el preview, volver al preview directamente
    if context.user_data.pop("admin_ped_edit_from_preview", False):
        text, markup = _admin_ped_preview_text(context.user_data)
        if hasattr(update_or_query, "message") and update_or_query.message:
            update_or_query.message.reply_text(text, reply_markup=markup)
        else:
            update_or_query.edit_message_text(text, reply_markup=markup)
        return ADMIN_PEDIDO_INSTRUC
    source_label = "Ruta estimada"
    if cotizacion.get("quote_source") == "coords":
        source_label = "Ruta por coordenadas"
    elif "cache" in str(cotizacion.get("quote_source", "")):
        source_label = "Ruta desde cache"
    elif "fallback" in str(cotizacion.get("quote_source", "")):
        source_label = "Ruta estimada local"
    text = (
        "Distancia calculada: {:.1f} km ({})\n\n"
        "Cual es la tarifa que le pagaras al repartidor?\n"
        "Ingresa el monto en pesos (ej: 15000):"
    ).format(cotizacion["distance_km"], source_label)
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")],
    ])
    if edit and hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(text, reply_markup=markup)
    elif hasattr(update_or_query, "message") and update_or_query.message:
        update_or_query.message.reply_text(text, reply_markup=markup)
    else:
        update_or_query.edit_message_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_TARIFA


def _admin_pedido_pedir_comision(update_or_query, context):
    """Muestra la tarifa ingresada y pide la comision que cobrara al courier."""
    tarifa = int(context.user_data.get("admin_ped_tarifa") or 0)
    fee_cfg = get_fee_config()
    min_comision = fee_cfg["fee_platform_share"]
    text = (
        "Tarifa al repartidor: ${:,}\n\n"
        "Comision al repartidor:\n"
        "Es el monto que se le descontara al courier de su saldo operativo "
        "al entregar este pedido (va al admin creador mas la cuota de plataforma).\n\n"
        "Minimo si cobras: ${:,} (cuota de plataforma).\n"
        "Escribe el monto o toca 'Sin comision':"
    ).format(tarifa, min_comision)
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Sin comision (fee estandar)", callback_data="admin_pedido_sin_comision")],
        [InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")],
    ])
    if hasattr(update_or_query, "message") and update_or_query.message:
        update_or_query.message.reply_text(text, reply_markup=markup)
    else:
        update_or_query.edit_message_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_COMISION


def _admin_pedido_pedir_instruc(update_or_query, context):
    """Muestra resumen de tarifa/comision/visibilidad y pide instrucciones al admin."""
    tarifa = int(context.user_data.get("admin_ped_tarifa") or 0)
    comision = int(context.user_data.get("admin_ped_comision") or 0)
    team_only = int(context.user_data.get("admin_ped_team_only") or 0)
    addr_notes = (context.user_data.get("admin_ped_addr_notes") or "").strip()
    fee_cfg = get_fee_config()
    fee_estandar = fee_cfg["fee_service_total"]
    if comision > 0:
        comision_str = "Comision al repartidor: ${:,}".format(comision)
    else:
        comision_str = "Comision: fee estandar (${:,})".format(fee_estandar)
    visibilidad_label = "Solo mi equipo" if team_only else "Todos los equipos"
    text = (
        "Tarifa al repartidor: ${:,}\n"
        "{}\n"
        "Visibilidad: {}\n\n"
    ).format(tarifa, comision_str, visibilidad_label)
    if addr_notes:
        text += (
            "Nota guardada de la direccion:\n{}\n\n"
            "Escribe instrucciones adicionales para el courier "
            "o toca 'Usar solo nota guardada'."
        ).format(addr_notes)
    else:
        text += (
            "Escribe instrucciones adicionales para el courier "
            "o toca 'Sin instrucciones'."
        )
    visibilidad_btn = "Visibilidad: Solo mi equipo" if team_only else "Visibilidad: Todos los equipos"
    sin_instruc_label = "Usar solo nota guardada" if addr_notes else "Sin instrucciones"
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(sin_instruc_label, callback_data="admin_pedido_sin_instruc")],
        [InlineKeyboardButton(visibilidad_btn, callback_data="admin_pedido_team_toggle")],
        [InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")],
    ])
    if hasattr(update_or_query, "message") and update_or_query.message:
        update_or_query.message.reply_text(text, reply_markup=markup)
    else:
        update_or_query.edit_message_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


MIN_ADMIN_OPERATING_BALANCE = 2000  # Saldo minimo para crear pedidos especiales


def _admin_pedido_mostrar_selector_cliente(query_or_update, context, edit=True):
    """Muestra selector de cliente del admin equivalente al flujo del aliado.

    Si hay clientes guardados: lista + Buscar + Cliente nuevo.
    Si no hay clientes: va directo al campo de nombre, sin boton intermedio.
    """
    admin_id = context.user_data.get("admin_ped_admin_id")
    all_customers = list_admin_customers(admin_id, limit=50, include_inactive=False) if admin_id else []

    if not all_customers:
        context.user_data["admin_ped_is_new_customer"] = True
        text = "Escribe el nombre del cliente:"
        if edit and hasattr(query_or_update, "edit_message_text"):
            query_or_update.edit_message_text(text)
        else:
            query_or_update.message.reply_text(text)
        return ADMIN_PEDIDO_CUST_NAME

    keyboard = []
    for c in all_customers[:8]:
        btn_text = "{} - {}".format(c["name"], c["phone"])
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_pedido_sel_{}".format(c["id"]))])
    keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="admin_pedido_buscar_cust")])
    if len(all_customers) > 8:
        keyboard.append([InlineKeyboardButton(
            "Ver todos ({})".format(len(all_customers)), callback_data="admin_pedido_ver_todos"
        )])
    keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="admin_pedido_cliente_nuevo")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])

    markup = InlineKeyboardMarkup(keyboard)
    text = "Selecciona el cliente:"
    if edit and hasattr(query_or_update, "edit_message_text"):
        query_or_update.edit_message_text(text, reply_markup=markup)
    else:
        query_or_update.message.reply_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_SEL_CUST


def _resolve_admin_for_special_order(telegram_id, selected_admin_id=None):
    """Resuelve el admin actor del pedido especial usando ownership explicito y compatibilidad legacy."""
    return resolve_owned_admin_actor(
        telegram_id,
        selected_admin_id=selected_admin_id,
        prefer_platform=True,
        legacy_counter_key="admin_special_order_legacy_callback_count",
        invalid_counter_key="admin_special_order_invalid_selected_count",
    )


def admin_nuevo_pedido_start(update, context):
    """Entrada al flujo de pedido especial del admin. Verifica saldo minimo y muestra puntos de recogida."""
    query = update.callback_query
    query.answer()
    telegram_id = update.effective_user.id
    data = query.data or ""
    match = re.fullmatch(r"admin_nuevo_pedido(?:_(\d+))?", data)
    selected_admin_id = int(match.group(1)) if match and match.group(1) else None
    admin = _resolve_admin_for_special_order(telegram_id, selected_admin_id=selected_admin_id)
    if selected_admin_id is not None and not admin:
        logger.warning(
            "[admin_special_order_actor_v2026_04_09] invalid_selected_admin telegram_id=%s selected_admin_id=%s",
            telegram_id,
            selected_admin_id,
        )
        query.edit_message_text(
            "No se pudo validar el administrador de este pedido especial.\n\n"
            "Vuelve a abrir Mi admin y entra de nuevo desde el boton actualizado."
        )
        return ConversationHandler.END
    if not admin or (admin["status"] or "").upper() != "APPROVED":
        query.edit_message_text("Solo los administradores aprobados pueden crear pedidos especiales.")
        return ConversationHandler.END
    logger.info(
        "[admin_special_order_actor_v2026_04_09] telegram_id=%s admin_id=%s team_code=%s",
        telegram_id,
        admin["id"],
        admin.get("team_code"),
    )
    admin_balance = get_admin_balance(admin["id"])
    if admin_balance < MIN_ADMIN_OPERATING_BALANCE:
        increment_setting_counter("admin_special_order_low_balance_blocked_count")
        is_platform_admin = (admin.get("team_code") or "").upper() == "PLATFORM"
        sociedad_balance = get_sociedad_balance() if is_platform_admin else 0
        text = (
            "Saldo insuficiente para crear un pedido especial.\n\n"
            "Tu saldo personal actual: ${:,}\n"
            "Saldo minimo requerido: ${:,}\n"
        ).format(admin_balance, MIN_ADMIN_OPERATING_BALANCE)
        reply_markup = None
        if is_platform_admin:
            text += (
                "Saldo Sociedad disponible: ${:,}\n\n"
                "Los pedidos especiales usan tu saldo personal. "
                "La Sociedad no se descuenta automaticamente.\n"
            ).format(sociedad_balance)
            if sociedad_balance > 0:
                text += "\nPuedes retirar fondos de Sociedad a tu saldo y volver a intentarlo."
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Retirar de Sociedad a mi saldo", callback_data="admin_sociedad_retiro_{}".format(admin["id"]))],
                ])
            else:
                text += "\nLa Sociedad tampoco tiene saldo disponible para transferirte en este momento."
        else:
            text += "\nRecarga tu saldo para poder crear pedidos especiales."
        query.edit_message_text(text, reply_markup=reply_markup)
        return ConversationHandler.END
    admin_id = admin["id"]
    # Limpiar datos anteriores del flujo
    for key in list(context.user_data.keys()):
        if key.startswith("admin_ped_"):
            del context.user_data[key]
    context.user_data["admin_ped_admin_id"] = admin_id
    show_flow_menu(update, context, "Iniciando pedido especial...")
    locations = get_admin_locations(admin_id)
    keyboard = []
    # Mostrar boton de plantillas si el admin tiene alguna
    templates = list_order_templates(admin_id)
    if templates:
        keyboard.append([InlineKeyboardButton(
            "Usar plantilla ({} guardadas)".format(len(templates)),
            callback_data="admin_pedido_usar_plantilla",
        )])
    for loc in locations:
        label = _pedido_pickup_option_text(loc)
        keyboard.append([InlineKeyboardButton(label, callback_data="admin_pedido_pickup_{}".format(loc["id"]))])
    keyboard.append([InlineKeyboardButton("Nueva direccion de recogida", callback_data="admin_pedido_nueva_dir")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])
    query.edit_message_text(
        "Pedido especial — Punto de recogida\n\nSelecciona el punto de recogida:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_PICKUP


def admin_pedido_pickup_callback(update, context):
    """Selecciona ubicacion de recogida existente y avanza a nombre del cliente."""
    query = update.callback_query
    query.answer()
    loc_id = int(query.data.split("_")[-1])
    admin_id = context.user_data.get("admin_ped_admin_id")
    loc = get_admin_location_by_id(loc_id, admin_id)
    if not loc:
        query.edit_message_text("Ubicacion no encontrada. Intenta de nuevo.")
        return ADMIN_PEDIDO_PICKUP
    if not has_valid_coords(loc.get("lat"), loc.get("lng")):
        query.edit_message_text(
            "Esta direccion guardada no tiene ubicacion confirmada.\n\n"
            "Selecciona otra o crea una nueva con GPS."
        )
        return ADMIN_PEDIDO_PICKUP
    if _pedido_is_system_address(loc.get("address")):
        context.user_data["admin_ped_geo_pickup_pending"] = {
            "address": loc.get("address", ""),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "city": loc.get("city", ""),
            "barrio": loc.get("barrio", ""),
            "location_id": loc_id,
            "label": loc.get("label", ""),
            "phone": loc.get("phone"),
            "source": "saved_location",
        }
        return _admin_pedido_prompt_pickup_detail(query, context)
    context.user_data["admin_ped_pickup_id"] = loc_id
    context.user_data["admin_ped_pickup_addr"] = loc["address"]
    context.user_data["admin_ped_pickup_lat"] = loc.get("lat")
    context.user_data["admin_ped_pickup_lng"] = loc.get("lng")
    context.user_data["admin_ped_pickup_city"] = loc.get("city", "")
    context.user_data["admin_ped_pickup_barrio"] = loc.get("barrio", "")
    # Si venimos de editar desde el preview y ya hay datos del cliente, volver al preview
    if context.user_data.get("admin_ped_edit_from_preview"):
        return _admin_pedido_render_preview(query, context)
    return _admin_pedido_mostrar_selector_cliente(query, context, edit=True)


def admin_pedido_nueva_dir_start(update, context):
    """Pide al admin que escriba la nueva direccion de recogida."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "Escribe la direccion del punto de recogida (o envia tu ubicacion GPS):"
    )
    return ADMIN_PEDIDO_PICKUP


def admin_pedido_pickup_text_handler(update, context):
    """Geocodifica el texto ingresado como nueva direccion de recogida."""
    texto = update.message.text.strip()
    _hint = _order_city_hint(context)
    geo = resolve_location(texto, city_hint=_hint)
    if not geo or geo.get("lat") is None or geo.get("lng") is None:
        update.message.reply_text(
            "No pude encontrar esa direccion. Intentalo de nuevo o envia tu ubicacion GPS."
        )
        return ADMIN_PEDIDO_PICKUP
    context.user_data["pending_geo_city_hint"] = _hint
    resolved_address = (
        geo.get("formatted_address")
        or geo.get("address")
        or geo.get("label")
        or texto
    )
    context.user_data["admin_ped_geo_pickup_pending"] = {
        "address": resolved_address,
        "lat": geo.get("lat"),
        "lng": geo.get("lng"),
        "city": geo.get("city", ""),
        "barrio": geo.get("barrio", ""),
        "original_text": texto,
        "source": geo.get("method") or "geocode",
        "place_id": geo.get("place_id"),
    }
    _mostrar_confirmacion_geocode(
        update.message,
        context,
        {
            "lat": geo["lat"],
            "lng": geo["lng"],
            "formatted_address": resolved_address,
            "place_id": geo.get("place_id"),
        },
        texto,
        "admin_pedido_geo_pickup_si",
        "admin_pedido_geo_pickup_no",
        header_text="Confirma este punto exacto antes de continuar.",
        question_text="Es esta la ubicacion de recogida correcta?",
    )
    return ADMIN_PEDIDO_PICKUP


def admin_pedido_pickup_gps_handler(update, context):
    """Solicita confirmacion del GPS enviado como nueva direccion de recogida."""
    location = update.message.location
    lat, lng = location.latitude, location.longitude
    logger.info(
        "[admin_pedido_pickup_confirm] status=pending source=gps lat=%s lng=%s",
        lat,
        lng,
    )
    context.user_data["admin_ped_geo_pickup_pending"] = {
        "address": "GPS ({:.5f}, {:.5f})".format(lat, lng),
        "lat": lat,
        "lng": lng,
        "city": "",
        "barrio": "",
        "original_text": "",
        "source": "gps",
        "place_id": None,
    }
    _mostrar_confirmacion_geocode(
        update.message,
        context,
        {"lat": lat, "lng": lng, "formatted_address": "Ubicacion enviada desde Telegram."},
        "",
        "admin_pedido_geo_pickup_si",
        "admin_pedido_geo_pickup_no",
        header_text="Confirma este punto exacto antes de continuar.",
        question_text="Es esta la ubicacion de recogida correcta?",
    )
    return ADMIN_PEDIDO_PICKUP


def admin_pedido_geo_pickup_callback(update, context):
    """Confirma o rechaza geocodificacion del punto de recogida."""
    query = update.callback_query
    query.answer()
    pending = context.user_data.get("admin_ped_geo_pickup_pending", {})
    if query.data == "admin_pedido_geo_pickup_si":
        _maybe_cache_confirmed_geo(context)
        logger.info(
            "[admin_pedido_pickup_confirm] status=confirmed source=%s lat=%s lng=%s",
            pending.get("source", "geocode"),
            pending.get("lat"),
            pending.get("lng"),
        )
        context.user_data.pop("pending_geo_lat", None)
        context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        context.user_data.pop("pending_geo_city_hint", None)
        if _pedido_requires_human_detail(pending):
            logger.info(
                "[address_rule_v2026_04_08] flow=admin_pickup action=prompt_detail source=%s",
                pending.get("source"),
            )
            return _admin_pedido_prompt_pickup_detail(query, context)
        logger.info(
            "[address_rule_v2026_04_08] flow=admin_pickup action=reuse_human_text source=%s",
            pending.get("source"),
        )
        pickup_addr = _pedido_visible_address_text(
            pending.get("original_text") or pending.get("address"),
            fallback=pending.get("address") or "",
        )
        context.user_data["admin_ped_pickup_id"] = None
        context.user_data["admin_ped_pickup_addr"] = pickup_addr
        context.user_data["admin_ped_pickup_lat"] = pending.get("lat")
        context.user_data["admin_ped_pickup_lng"] = pending.get("lng")
        context.user_data["admin_ped_pickup_city"] = pending.get("city", "")
        context.user_data["admin_ped_pickup_barrio"] = pending.get("barrio", "")
        context.user_data.pop("admin_ped_geo_pickup_pending", None)
        if context.user_data.get("admin_ped_edit_from_preview"):
            return _admin_pedido_render_preview(query, context)
        return _admin_pedido_render_pickup_save_prompt(query, context)
    else:
        if pending.get("source") == "gps":
            context.user_data.pop("admin_ped_geo_pickup_pending", None)
            context.user_data.pop("pending_geo_lat", None)
            context.user_data.pop("pending_geo_lng", None)
            context.user_data.pop("pending_geo_text", None)
            context.user_data.pop("pending_geo_seen", None)
            context.user_data.pop("pending_geo_city_hint", None)
            query.edit_message_text(
                "Ubicacion descartada.\n\n"
                "Envia otra ubicacion para continuar.\n"
                "El flujo solo sigue cuando confirmes el punto exacto."
            )
            return ADMIN_PEDIDO_PICKUP
        original = pending.get("original_text", "")
        seen = list(context.user_data.get("pending_geo_seen", []))
        if not seen:
            current_pid = pending.get("place_id")
            if not current_pid and pending.get("lat") is not None and pending.get("lng") is not None:
                current_pid = "{},{}".format(pending["lat"], pending["lng"])
            if current_pid:
                seen = [current_pid]
        next_geo = resolve_location_next(original, seen, city_hint=_order_city_hint(context)) if original else None
        if next_geo and next_geo.get("lat") is not None and next_geo.get("lng") is not None:
            next_pid = next_geo.get("place_id") or "{},{}".format(next_geo["lat"], next_geo["lng"])
            if next_pid not in seen:
                seen.append(next_pid)
            resolved_address = (
                next_geo.get("formatted_address")
                or next_geo.get("address")
                or next_geo.get("label")
                or original
            )
            context.user_data["admin_ped_geo_pickup_pending"] = {
                "address": resolved_address,
                "lat": next_geo["lat"],
                "lng": next_geo["lng"],
                "city": next_geo.get("city", ""),
                "barrio": next_geo.get("barrio", ""),
                "original_text": original,
                "source": "geocode",
                "place_id": next_geo.get("place_id"),
            }
            query.edit_message_text("Buscando otra opcion...")
            _mostrar_confirmacion_geocode(
                query.message,
                context,
                {
                    "lat": next_geo["lat"],
                    "lng": next_geo["lng"],
                    "formatted_address": resolved_address,
                    "place_id": next_geo.get("place_id"),
                },
                original,
                "admin_pedido_geo_pickup_si",
                "admin_pedido_geo_pickup_no",
                header_text="Confirma este punto exacto antes de continuar.",
                question_text="Es esta la ubicacion de recogida correcta?",
            )
            context.user_data["pending_geo_seen"] = seen
            return ADMIN_PEDIDO_PICKUP
        else:
            context.user_data.pop("pending_geo_lat", None)
            context.user_data.pop("pending_geo_lng", None)
            context.user_data.pop("pending_geo_text", None)
            context.user_data.pop("pending_geo_seen", None)
            context.user_data.pop("pending_geo_city_hint", None)
            query.edit_message_text(
                "No encontre mas resultados. Escribe la direccion nuevamente o envia GPS:"
            )
            context.user_data.pop("admin_ped_geo_pickup_pending", None)
            return ADMIN_PEDIDO_PICKUP


def admin_pedido_pickup_detalle_handler(update, context):
    """Captura la direccion humana final de recogida tras confirmar el punto GPS."""
    detail = " ".join(update.message.text.strip().split())
    pending = context.user_data.get("admin_ped_geo_pickup_pending") or {}
    lat = pending.get("lat")
    lng = pending.get("lng")
    if _pedido_is_system_address(detail):
        update.message.reply_text(
            "Escribe la direccion visible en texto humano.\n"
            "No envíes GPS, links ni coordenadas."
        )
        return ADMIN_PEDIDO_PICKUP_DETALLE
    if not has_valid_coords(lat, lng):
        context.user_data.pop("admin_ped_geo_pickup_pending", None)
        update.message.reply_text("Se perdio la ubicacion. Envia de nuevo el punto de recogida.")
        return ADMIN_PEDIDO_PICKUP

    context.user_data["admin_ped_pickup_addr"] = detail
    context.user_data["admin_ped_pickup_lat"] = lat
    context.user_data["admin_ped_pickup_lng"] = lng
    context.user_data["admin_ped_pickup_city"] = pending.get("city", "")
    context.user_data["admin_ped_pickup_barrio"] = pending.get("barrio", "")

    location_id = pending.get("location_id")
    if location_id:
        admin_id = context.user_data.get("admin_ped_admin_id")
        label = _pedido_human_label(pending.get("label"), detail)
        try:
            updated = update_admin_location(
                location_id=location_id,
                admin_id=admin_id,
                label=label,
                address=detail,
                city=pending.get("city", ""),
                barrio=pending.get("barrio", ""),
                phone=pending.get("phone"),
                lat=lat,
                lng=lng,
            )
        except Exception as e:
            update.message.reply_text("No se pudo actualizar la direccion guardada: {}".format(e))
            return ADMIN_PEDIDO_PICKUP_DETALLE
        if not updated:
            update.message.reply_text("No se pudo actualizar la direccion guardada. Intenta de nuevo.")
            return ADMIN_PEDIDO_PICKUP_DETALLE
        context.user_data["admin_ped_pickup_id"] = location_id
    else:
        context.user_data["admin_ped_pickup_id"] = None

    context.user_data.pop("admin_ped_geo_pickup_pending", None)

    if context.user_data.get("admin_ped_edit_from_preview"):
        return _admin_pedido_render_preview(update.message, context)
    if location_id:
        return _admin_pedido_mostrar_selector_cliente(update, context, edit=False)
    return _admin_pedido_render_pickup_save_prompt(update.message, context)


def admin_pedido_save_pickup_callback(update, context):
    """Guarda (o no) la nueva direccion de recogida en admin_locations y avanza al nombre del cliente."""
    query = update.callback_query
    query.answer()
    admin_id = context.user_data.get("admin_ped_admin_id")
    if query.data == "admin_pedido_save_pickup_si" and admin_id:
        addr = context.user_data.get("admin_ped_pickup_addr", "")
        lat = context.user_data.get("admin_ped_pickup_lat")
        lng = context.user_data.get("admin_ped_pickup_lng")
        city = context.user_data.get("admin_ped_pickup_city", "")
        barrio = context.user_data.get("admin_ped_pickup_barrio", "")
        try:
            loc_id = create_admin_location(
                admin_id, addr[:80], addr, city, barrio, lat=lat, lng=lng
            )
            context.user_data["admin_ped_pickup_id"] = loc_id
        except Exception as e:
            logger.warning("admin_pedido_save_pickup_callback: %s", e)
    return _admin_pedido_mostrar_selector_cliente(query, context, edit=True)


def admin_pedido_cust_name_handler(update, context):
    """Captura nombre del cliente."""
    nombre = update.message.text.strip()
    if not nombre:
        update.message.reply_text("El nombre no puede estar vacio.")
        return ADMIN_PEDIDO_CUST_NAME
    context.user_data["admin_ped_cust_name"] = nombre
    update.message.reply_text("Telefono del cliente (minimo 7 digitos):" + _OPTIONS_HINT)
    return ADMIN_PEDIDO_CUST_PHONE


def admin_pedido_sel_cust_handler(update, context):
    """Muestra lista de clientes del admin para seleccionar en el pedido."""
    query = update.callback_query
    query.answer()
    admin_id = context.user_data.get("admin_ped_admin_id")
    if not admin_id:
        query.edit_message_text("Sesion expirada. Cancela y vuelve a crear el pedido.")
        return ConversationHandler.END

    customers = list_admin_customers(admin_id, limit=15, include_inactive=False)
    if not customers:
        keyboard = [[InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")]]
        query.edit_message_text(
            "No tienes clientes guardados en tu agenda.\n\n"
            "Escribe el nombre del cliente directamente:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_PEDIDO_CUST_NAME

    keyboard = []
    for c in customers:
        btn_text = "{} - {}".format(c["name"], c["phone"])
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_pedido_sel_{}".format(c["id"]))])
    keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="admin_pedido_buscar_cust")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])

    query.edit_message_text(
        "Selecciona el cliente de tu agenda:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_PEDIDO_SEL_CUST


def admin_pedido_cust_selected(update, context):
    """Cliente seleccionado de la agenda. Muestra sus direcciones guardadas."""
    query = update.callback_query
    query.answer()
    customer_id = int(query.data.replace("acust_pedido_sel_", ""))
    admin_id = context.user_data.get("admin_ped_admin_id")

    customer = get_admin_customer_by_id(customer_id, admin_id)
    if not customer:
        query.edit_message_text("Cliente no encontrado.")
        return ADMIN_PEDIDO_SEL_CUST

    context.user_data["admin_ped_cust_name"] = customer["name"]
    context.user_data["admin_ped_cust_phone"] = customer["phone"]
    context.user_data["admin_ped_selected_cust_id"] = customer_id  # marca que viene de agenda

    addresses = list_admin_customer_addresses(customer_id)
    keyboard = []
    for addr in addresses:
        btn_text = _pedido_customer_address_button_text(addr)
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_pedido_addr_{}".format(addr["id"]))])
    keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="acust_pedido_addr_nueva")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])

    query.edit_message_text(
        "Cliente: {} ({})\n\nSelecciona la direccion de entrega:".format(
            customer["name"], customer["phone"]
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_PEDIDO_SEL_CUST_ADDR


def admin_pedido_addr_selected(update, context):
    """Direccion seleccionada de la agenda. Calcula tarifa automaticamente."""
    query = update.callback_query
    query.answer()
    address_id = int(query.data.replace("acust_pedido_addr_", ""))
    admin_id = context.user_data.get("admin_ped_admin_id")
    cust_name = context.user_data.get("admin_ped_cust_name", "")

    # Buscar la direccion por customer_id no es requerido aqui, solo necesitamos el id
    # Necesitamos buscar por address_id sin restriccion de customer (es del admin)
    # Usamos get_admin_customer_address_by_id con customer_id=None
    address = get_admin_customer_address_by_id(address_id, customer_id=None)
    if not address:
        query.edit_message_text("Direccion no encontrada. Intenta nuevamente.")
        return ADMIN_PEDIDO_SEL_CUST_ADDR

    if not has_valid_coords(address["lat"], address["lng"]):
        query.edit_message_text(
            "Esta direccion guardada no tiene ubicacion confirmada.\n\n"
            "Corrigela en la agenda o envia una direccion nueva con GPS."
        )
        return ADMIN_PEDIDO_CUST_ADDR

    try:
        parking_status = address["parking_status"]
    except (KeyError, IndexError):
        parking_status = "NOT_ASKED"

    if _pedido_is_system_address(address["address_text"]):
        context.user_data["admin_ped_geo_cust_pending"] = {
            "address": address["address_text"] or "",
            "lat": address["lat"],
            "lng": address["lng"],
            "city": address["city"] or "",
            "barrio": address["barrio"] or "",
            "address_id": address["id"],
            "customer_id": address["customer_id"],
            "label": address["label"] or "",
            "notes": address["notes"],
            "parking_status": parking_status,
            "source": "saved_address",
        }
        return _admin_pedido_prompt_delivery_detail(query, context)

    context.user_data["admin_ped_addr_notes"] = address["notes"] or ""
    context.user_data["admin_ped_cust_addr"] = address["address_text"]
    context.user_data["admin_ped_dropoff_lat"] = address["lat"]
    context.user_data["admin_ped_dropoff_lng"] = address["lng"]
    context.user_data["admin_ped_dropoff_city"] = address["city"] or ""
    context.user_data["admin_ped_dropoff_barrio"] = address["barrio"] or ""
    context.user_data["admin_ped_parking_fee"] = PARKING_FEE_AMOUNT if parking_status in ("ALLY_YES", "ADMIN_YES") else 0
    cust_id_for_inc = context.user_data.get("admin_ped_selected_cust_id")
    if cust_id_for_inc:
        try:
            increment_admin_customer_address_usage(address_id, cust_id_for_inc)
            increment_admin_customer_usage(cust_id_for_inc)
        except Exception:
            pass

    logger.info(
        "[requires_cash_unified_v2026_04_09] flow=admin_special action=ask_base source=saved_address address_id=%s",
        address_id,
    )
    return mostrar_pregunta_base(query, context, edit=True)


def admin_pedido_addr_nueva(update, context):
    """Admin eligio ingresar nueva direccion manualmente."""
    query = update.callback_query
    query.answer()
    context.user_data["admin_ped_addr_notes"] = ""
    query.edit_message_text("Direccion de entrega del cliente (escribe o envia GPS):")
    return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_cust_phone_handler(update, context):
    """Captura telefono del cliente."""
    phone = update.message.text.strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 7:
        update.message.reply_text("Telefono invalido. Ingresa minimo 7 digitos.")
        return ADMIN_PEDIDO_CUST_PHONE
    context.user_data["admin_ped_cust_phone"] = digits
    admin_id = context.user_data.get("admin_ped_admin_id")
    # Dedup: verificar si ya existe en la agenda del admin
    existing = get_admin_customer_by_phone(admin_id, digits) if admin_id else None
    if existing:
        context.user_data["admin_ped_dedup_cust_id"] = existing["id"]
        context.user_data["admin_ped_dedup_name"] = existing["name"] or ""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Si, usar este cliente", callback_data="admin_ped_dedup_si")],
            [InlineKeyboardButton("No, es otro cliente", callback_data="admin_ped_dedup_no")],
            [InlineKeyboardButton("Cancelar pedido", callback_data="admin_pedido_cancelar")],
        ])
        update.message.reply_text(
            "Este numero ya esta en tu agenda: {}\n\n"
            "Usar este cliente para el pedido?".format(existing["name"] or digits),
            reply_markup=keyboard,
        )
        return ADMIN_PEDIDO_CUST_DEDUP
    update.message.reply_text("Direccion de entrega del cliente (escribe o envia GPS):" + _OPTIONS_HINT)
    return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_cust_addr_handler(update, context):
    """Geocodifica la direccion de entrega del cliente."""
    texto = update.message.text.strip()
    context.user_data["admin_ped_addr_notes"] = ""
    _hint = _order_city_hint(context)
    geo = resolve_location(texto, city_hint=_hint)
    if not geo or geo.get("lat") is None or geo.get("lng") is None:
        update.message.reply_text(
            "No pude encontrar esa direccion. Intentalo de nuevo o envia GPS."
        )
        return ADMIN_PEDIDO_CUST_ADDR
    resolved_address = (
        geo.get("formatted_address")
        or geo.get("address")
        or geo.get("label")
        or texto
    )
    logger.info(
        "[admin_pedido_location_confirm] status=pending source=geocode lat=%s lng=%s",
        geo["lat"],
        geo["lng"],
    )
    context.user_data["pending_geo_city_hint"] = _hint
    context.user_data["admin_ped_geo_cust_pending"] = {
        "address": resolved_address,
        "lat": geo["lat"],
        "lng": geo["lng"],
        "city": geo.get("city", ""),
        "barrio": geo.get("barrio", ""),
        "original_text": texto,
        "source": geo.get("method") or "geocode",
        "place_id": geo.get("place_id"),
    }
    _mostrar_confirmacion_geocode(
        update.message,
        context,
        {
            "lat": geo["lat"],
            "lng": geo["lng"],
            "formatted_address": resolved_address,
            "place_id": geo.get("place_id"),
        },
        texto,
        "admin_pedido_geo_si",
        "admin_pedido_geo_no",
        header_text="Confirma este punto exacto antes de continuar.",
        question_text="Es esta la ubicacion de entrega correcta?",
    )
    return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_cust_gps_handler(update, context):
    """Solicita confirmacion del GPS enviado como direccion de entrega."""
    location = update.message.location
    context.user_data["admin_ped_addr_notes"] = ""
    lat, lng = location.latitude, location.longitude
    logger.info(
        "[admin_pedido_location_confirm] status=pending source=gps lat=%s lng=%s",
        lat,
        lng,
    )
    context.user_data["admin_ped_geo_cust_pending"] = {
        "address": "GPS ({:.5f}, {:.5f})".format(lat, lng),
        "lat": lat,
        "lng": lng,
        "city": "",
        "barrio": "",
        "original_text": "",
        "source": "gps",
        "place_id": None,
    }
    _mostrar_confirmacion_geocode(
        update.message,
        context,
        {"lat": lat, "lng": lng, "formatted_address": "Ubicacion enviada desde Telegram."},
        "",
        "admin_pedido_geo_si",
        "admin_pedido_geo_no",
        header_text="Confirma este punto exacto antes de continuar.",
        question_text="Es esta la ubicacion de entrega correcta?",
    )
    return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_geo_callback(update, context):
    """Confirma o rechaza geocodificacion de la direccion de entrega del cliente."""
    query = update.callback_query
    query.answer()
    pending = context.user_data.get("admin_ped_geo_cust_pending", {})
    if query.data == "admin_pedido_geo_si":
        _maybe_cache_confirmed_geo(context)
        logger.info(
            "[admin_pedido_location_confirm] status=confirmed source=%s lat=%s lng=%s",
            pending.get("source", "geocode"),
            pending.get("lat"),
            pending.get("lng"),
        )
        context.user_data.pop("pending_geo_lat", None)
        context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        context.user_data.pop("pending_geo_city_hint", None)
        if _pedido_requires_human_detail(pending):
            logger.info(
                "[address_rule_v2026_04_08] flow=admin_delivery action=prompt_detail source=%s",
                pending.get("source"),
            )
            return _admin_pedido_prompt_delivery_detail(query, context)
        logger.info(
            "[address_rule_v2026_04_08] flow=admin_delivery action=reuse_human_text source=%s",
            pending.get("source"),
        )
        context.user_data["admin_ped_cust_addr"] = _pedido_visible_address_text(
            pending.get("original_text") or pending.get("address"),
            fallback=pending.get("address") or "",
        )
        context.user_data["admin_ped_addr_notes"] = ""
        context.user_data["admin_ped_dropoff_lat"] = pending.get("lat")
        context.user_data["admin_ped_dropoff_lng"] = pending.get("lng")
        context.user_data["admin_ped_dropoff_city"] = pending.get("city", "")
        context.user_data["admin_ped_dropoff_barrio"] = pending.get("barrio", "")
        context.user_data["admin_ped_parking_fee"] = 0
        context.user_data.pop("admin_ped_geo_cust_pending", None)
        logger.info(
            "[requires_cash_unified_v2026_04_09] flow=admin_special action=ask_base source=%s",
            pending.get("source", "geocode"),
        )
        return mostrar_pregunta_base(query, context, edit=True)
    else:
        if pending.get("source") == "gps":
            context.user_data.pop("admin_ped_geo_cust_pending", None)
            context.user_data.pop("pending_geo_lat", None)
            context.user_data.pop("pending_geo_lng", None)
            context.user_data.pop("pending_geo_text", None)
            context.user_data.pop("pending_geo_seen", None)
            context.user_data.pop("pending_geo_city_hint", None)
            logger.info("[admin_pedido_location_confirm] status=rejected source=gps")
            query.edit_message_text(
                "Ubicacion descartada.\n\n"
                "Envia otra ubicacion para continuar.\n"
                "El flujo solo sigue cuando confirmes el punto exacto."
            )
            return ADMIN_PEDIDO_CUST_ADDR
        original = pending.get("original_text", "")
        seen = list(context.user_data.get("pending_geo_seen", []))
        if not seen:
            current_pid = pending.get("place_id")
            if not current_pid and pending.get("lat") is not None and pending.get("lng") is not None:
                current_pid = "{},{}".format(pending["lat"], pending["lng"])
            if current_pid:
                seen = [current_pid]
        next_geo = resolve_location_next(original, seen, city_hint=_order_city_hint(context)) if original else None
        if next_geo and next_geo.get("lat") is not None and next_geo.get("lng") is not None:
            next_pid = next_geo.get("place_id") or "{},{}".format(next_geo["lat"], next_geo["lng"])
            if next_pid not in seen:
                seen.append(next_pid)
            resolved_address = (
                next_geo.get("formatted_address")
                or next_geo.get("address")
                or next_geo.get("label")
                or original
            )
            context.user_data["admin_ped_geo_cust_pending"] = {
                "address": resolved_address,
                "lat": next_geo["lat"],
                "lng": next_geo["lng"],
                "city": next_geo.get("city", ""),
                "barrio": next_geo.get("barrio", ""),
                "original_text": original,
                "source": "geocode",
                "place_id": next_geo.get("place_id"),
            }
            query.edit_message_text("Buscando otra opcion...")
            _mostrar_confirmacion_geocode(
                query.message,
                context,
                {
                    "lat": next_geo["lat"],
                    "lng": next_geo["lng"],
                    "formatted_address": resolved_address,
                    "place_id": next_geo.get("place_id"),
                },
                original,
                "admin_pedido_geo_si",
                "admin_pedido_geo_no",
                header_text="Confirma este punto exacto antes de continuar.",
                question_text="Es esta la ubicacion de entrega correcta?",
            )
            context.user_data["pending_geo_seen"] = seen
            return ADMIN_PEDIDO_CUST_ADDR
        else:
            context.user_data.pop("pending_geo_lat", None)
            context.user_data.pop("pending_geo_lng", None)
            context.user_data.pop("pending_geo_text", None)
            context.user_data.pop("pending_geo_seen", None)
            context.user_data.pop("pending_geo_city_hint", None)
            query.edit_message_text(
                "No encontre mas resultados. Escribe la direccion nuevamente o envia GPS:"
            )
            context.user_data.pop("admin_ped_geo_cust_pending", None)
            return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_cust_addr_detalle_handler(update, context):
    """Captura la direccion humana final de entrega tras confirmar el punto GPS."""
    detail = " ".join(update.message.text.strip().split())
    pending = context.user_data.get("admin_ped_geo_cust_pending") or {}
    lat = pending.get("lat")
    lng = pending.get("lng")
    if _pedido_is_system_address(detail):
        update.message.reply_text(
            "Escribe la direccion visible en texto humano.\n"
            "No envíes GPS, links ni coordenadas."
        )
        return ADMIN_PEDIDO_CUST_ADDR_DETALLE
    if not has_valid_coords(lat, lng):
        context.user_data.pop("admin_ped_geo_cust_pending", None)
        update.message.reply_text("Se perdio la ubicacion. Envia de nuevo la entrega.")
        return ADMIN_PEDIDO_CUST_ADDR

    context.user_data["admin_ped_cust_addr"] = detail
    context.user_data["admin_ped_addr_notes"] = pending.get("notes") or ""
    context.user_data["admin_ped_dropoff_lat"] = lat
    context.user_data["admin_ped_dropoff_lng"] = lng
    context.user_data["admin_ped_dropoff_city"] = pending.get("city", "")
    context.user_data["admin_ped_dropoff_barrio"] = pending.get("barrio", "")
    parking_status = pending.get("parking_status", "NOT_ASKED")
    context.user_data["admin_ped_parking_fee"] = (
        PARKING_FEE_AMOUNT if parking_status in ("ALLY_YES", "ADMIN_YES") else 0
    )

    address_id = pending.get("address_id")
    customer_id = pending.get("customer_id")
    if address_id and customer_id:
        label = _pedido_human_label(pending.get("label"), detail)
        try:
            updated = update_admin_customer_address(
                address_id=address_id,
                customer_id=customer_id,
                label=label,
                address_text=detail,
                city=pending.get("city", ""),
                barrio=pending.get("barrio", ""),
                notes=pending.get("notes"),
                lat=lat,
                lng=lng,
            )
        except Exception as e:
            update.message.reply_text("No se pudo actualizar la direccion guardada: {}".format(e))
            return ADMIN_PEDIDO_CUST_ADDR_DETALLE
        if not updated:
            update.message.reply_text("No se pudo actualizar la direccion guardada. Intenta de nuevo.")
            return ADMIN_PEDIDO_CUST_ADDR_DETALLE
        try:
            increment_admin_customer_address_usage(address_id, customer_id)
            increment_admin_customer_usage(customer_id)
        except Exception:
            pass

    context.user_data.pop("admin_ped_geo_cust_pending", None)
    logger.info(
        "[requires_cash_unified_v2026_04_09] flow=admin_special action=ask_base source=manual_detail"
    )
    return mostrar_pregunta_base(update, context, edit=False)


def admin_pedido_tarifa_handler(update, context):
    """Captura la tarifa manual ingresada por el admin y pide la comision."""
    texto = update.message.text.strip().replace(",", "").replace(".", "").replace("$", "")
    if not texto.isdigit() or int(texto) < 1000:
        update.message.reply_text("Ingresa una tarifa valida en pesos (minimo $1,000).")
        return ADMIN_PEDIDO_TARIFA
    tarifa = int(texto)
    if tarifa > 500000:
        update.message.reply_text("La tarifa es demasiado alta (maximo $500,000).")
        return ADMIN_PEDIDO_TARIFA
    context.user_data["admin_ped_tarifa"] = tarifa
    context.user_data["admin_ped_base_fee"] = tarifa
    context.user_data["admin_ped_buy_surcharge"] = 0
    if context.user_data.pop("admin_ped_edit_from_preview", False):
        text, markup = _admin_ped_preview_text(context.user_data)
        update.message.reply_text(text, reply_markup=markup)
        return ADMIN_PEDIDO_INSTRUC
    return _admin_pedido_pedir_comision(update, context)


def admin_pedido_comision_handler(update, context):
    """Captura el monto de comision y pide instrucciones."""
    texto = update.message.text.strip().replace(",", "").replace(".", "").replace("$", "")
    if not texto.isdigit() or int(texto) < 0:
        update.message.reply_text("Ingresa un monto valido o toca 'Sin comision'.")
        return ADMIN_PEDIDO_COMISION
    comision = int(texto)
    if comision > 0:
        fee_cfg = get_fee_config()
        min_comision = fee_cfg["fee_platform_share"]
        if comision < min_comision:
            update.message.reply_text(
                "La comision minima es ${:,} (cuota de plataforma). "
                "Ingresa ese monto o mas, o toca 'Sin comision'.".format(min_comision)
            )
            return ADMIN_PEDIDO_COMISION
    if comision > 200000:
        update.message.reply_text("La comision es demasiado alta (maximo $200,000).")
        return ADMIN_PEDIDO_COMISION
    context.user_data["admin_ped_comision"] = comision
    return _admin_pedido_pedir_instruc(update, context)


def admin_pedido_sin_comision_callback(update, context):
    """Admin elige no cobrar comision especial (usa fee estandar)."""
    query = update.callback_query
    query.answer()
    context.user_data["admin_ped_comision"] = 0
    return _admin_pedido_pedir_instruc(query, context)


def admin_pedido_team_toggle_callback(update, context):
    """Alterna visibilidad: todos los equipos / solo mi equipo."""
    query = update.callback_query
    query.answer()
    actual = int(context.user_data.get("admin_ped_team_only") or 0)
    context.user_data["admin_ped_team_only"] = 0 if actual else 1
    # Mantener instrucciones si ya las habia y mostrar preview actualizado
    if context.user_data.get("admin_ped_instruc") is not None:
        text, markup = _admin_ped_preview_text(context.user_data)
        query.edit_message_text(text, reply_markup=markup)
        return ADMIN_PEDIDO_INSTRUC
    return _admin_pedido_pedir_instruc(query, context)


def admin_pedido_instruc_handler(update, context):
    """Guarda instrucciones y muestra preview del pedido."""
    context.user_data["admin_ped_instruc"] = _pedido_merge_instruction_text(
        context.user_data.get("admin_ped_addr_notes", ""),
        update.message.text.strip(),
    )
    text, markup = _admin_ped_preview_text(context.user_data)
    update.message.reply_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_sin_instruc_callback(update, context):
    """Sin instrucciones: guarda vacio y muestra preview."""
    query = update.callback_query
    query.answer()
    context.user_data["admin_ped_instruc"] = _pedido_merge_instruction_text(
        context.user_data.get("admin_ped_addr_notes", ""),
        "",
    )
    text, markup = _admin_ped_preview_text(context.user_data)
    query.edit_message_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_inc_fijo_callback(update, context):
    """Agrega incentivo fijo al preview del pedido especial admin."""
    query = update.callback_query
    query.answer()
    delta = int(query.data.split("_")[-1])
    actual = int(context.user_data.get("admin_ped_incentivo") or 0)
    context.user_data["admin_ped_incentivo"] = actual + delta
    text, markup = _admin_ped_preview_text(context.user_data)
    query.edit_message_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_inc_otro_callback(update, context):
    """Solicita monto libre de incentivo."""
    query = update.callback_query
    query.answer()
    query.edit_message_text("Escribe el monto del incentivo adicional (en pesos):")
    return ADMIN_PEDIDO_INC_MONTO


def admin_pedido_inc_monto_handler(update, context):
    """Captura monto libre de incentivo y regresa al preview."""
    texto = update.message.text.strip().replace(",", "").replace(".", "")
    if not texto.isdigit() or int(texto) <= 0:
        update.message.reply_text("Ingresa un monto valido mayor que 0.")
        return ADMIN_PEDIDO_INC_MONTO
    delta = int(texto)
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto (maximo $200,000).")
        return ADMIN_PEDIDO_INC_MONTO
    actual = int(context.user_data.get("admin_ped_incentivo") or 0)
    context.user_data["admin_ped_incentivo"] = actual + delta
    text, markup = _admin_ped_preview_text(context.user_data)
    update.message.reply_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_confirmar_callback(update, context):
    """Crea y publica el pedido especial del admin."""
    query = update.callback_query
    query.answer()
    admin_id = context.user_data.get("admin_ped_admin_id")
    if not admin_id:
        query.edit_message_text("Sesion expirada. Usa 'Nuevo pedido especial' de nuevo.")
        return ConversationHandler.END
    tarifa = int(context.user_data.get("admin_ped_tarifa") or 0)
    incentivo = int(context.user_data.get("admin_ped_incentivo") or 0)
    parking_fee = int(context.user_data.get("admin_ped_parking_fee") or 0)
    comision = int(context.user_data.get("admin_ped_comision") or 0)
    team_only = int(context.user_data.get("admin_ped_team_only") or 0)
    total_fee = tarifa + incentivo + parking_fee
    pickup_location_id = context.user_data.get("admin_ped_pickup_id")
    pickup_addr = context.user_data.get("admin_ped_pickup_addr", "")
    pickup_lat = context.user_data.get("admin_ped_pickup_lat")
    pickup_lng = context.user_data.get("admin_ped_pickup_lng")
    pickup_city = context.user_data.get("admin_ped_pickup_city", "")
    pickup_barrio = context.user_data.get("admin_ped_pickup_barrio", "")
    cust_name = context.user_data.get("admin_ped_cust_name", "")
    cust_phone = context.user_data.get("admin_ped_cust_phone", "")
    cust_addr = context.user_data.get("admin_ped_cust_addr", "")
    dropoff_lat = context.user_data.get("admin_ped_dropoff_lat")
    dropoff_lng = context.user_data.get("admin_ped_dropoff_lng")
    dropoff_city = context.user_data.get("admin_ped_dropoff_city", "")
    dropoff_barrio = context.user_data.get("admin_ped_dropoff_barrio", "")
    distance_km = float(context.user_data.get("admin_ped_distance_km") or 0)
    quote_source = context.user_data.get("admin_ped_quote_source", "admin")
    instruc = context.user_data.get("admin_ped_instruc", "")
    requires_cash = bool(context.user_data.get("admin_ped_requires_cash"))
    cash_required_amount = int(context.user_data.get("admin_ped_cash_required_amount") or 0)
    if not has_valid_coords(pickup_lat, pickup_lng) or not has_valid_coords(dropoff_lat, dropoff_lng):
        query.edit_message_text(
            "El pedido requiere ubicacion confirmada en recogida y entrega antes de crearse."
        )
        return ADMIN_PEDIDO_CUST_ADDR
    try:
        order_id = create_order(
            ally_id=None,
            creator_admin_id=admin_id,
            customer_name=cust_name,
            customer_phone=cust_phone,
            customer_address=cust_addr,
            customer_city=dropoff_city,
            customer_barrio=dropoff_barrio,
            pickup_location_id=pickup_location_id,
            pay_at_store_required=False,
            pay_at_store_amount=0,
            base_fee=tarifa,
            distance_km=distance_km,
            buy_surcharge=0,
            rain_extra=0,
            high_demand_extra=0,
            night_extra=0,
            additional_incentive=incentivo,
            total_fee=total_fee,
            instructions=instruc,
            requires_cash=requires_cash,
            cash_required_amount=cash_required_amount,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            quote_source=quote_source,
            ally_admin_id_snapshot=admin_id,
            payment_method=_pedido_payment_method_from_base(requires_cash, cash_required_amount),
            parking_fee=parking_fee,
            special_commission=comision,
            team_only=team_only,
        )
    except Exception as e:
        logger.error("admin_pedido_confirmar_callback create_order: %s", e)
        query.edit_message_text("Error al crear el pedido. Intenta de nuevo.")
        return ConversationHandler.END
    if pickup_location_id:
        increment_admin_location_usage(pickup_location_id, admin_id)
    published_count = 0
    try:
        published_count = publish_order_to_couriers(
            order_id,
            None,
            context,
            admin_id_override=admin_id,
            pickup_city=pickup_city,
            pickup_barrio=pickup_barrio,
            dropoff_city=dropoff_city,
            dropoff_barrio=dropoff_barrio,
            skip_fee_check=True,
        )
    except Exception as e:
        logger.warning("admin_pedido_confirmar_callback publish: %s", e)
    price_block = build_order_price_summary_text(
        get_order_by_id(order_id),
        label="Valor del servicio",
    )
    comision_line = (
        "Comision especial al courier: ${:,}".format(comision)
        if comision > 0
        else "Comision especial al courier: fee estandar"
    )
    visibilidad_str = "Solo equipo propio" if team_only else "Todos los equipos"
    success_title = "Pedido especial publicado." if published_count >= 0 else "Pedido especial creado."
    success_lines = [
        success_title,
        "ID: #{}".format(order_id),
        price_block or "Valor del servicio: ${:,}".format(total_fee),
        comision_line,
        "Visibilidad: {}".format(visibilidad_str),
        build_market_launch_status_text(published_count),
    ]
    success_msg = "\n".join(line for line in success_lines if line)
    # Ofrecer guardar cliente/direccion cuando aplique y completar GPS si la direccion ya existia.
    cust_name = context.user_data.get("admin_ped_cust_name", "")
    cust_phone = context.user_data.get("admin_ped_cust_phone", "")
    if cust_phone and has_valid_coords(dropoff_lat, dropoff_lng):
        existing_customer_id = context.user_data.get("admin_ped_selected_cust_id")
        existing_customer_name = cust_name
        if existing_customer_id:
            selected_customer = get_admin_customer_by_id(existing_customer_id, admin_id)
            if selected_customer:
                existing_customer_name = selected_customer["name"] or existing_customer_name
        else:
            existing = get_admin_customer_by_phone(admin_id, cust_phone)
            if existing:
                existing_customer_id = existing["id"]
                existing_customer_name = existing["name"] or existing_customer_name

        if existing_customer_id:
            existing_addr = find_matching_admin_customer_address(
                existing_customer_id,
                cust_addr,
                city=dropoff_city,
                barrio=dropoff_barrio,
            )
            if existing_addr:
                save_result = upsert_admin_customer_address_for_agenda(
                    customer_id=existing_customer_id,
                    label=existing_addr.get("label") or dropoff_barrio or dropoff_city or "Principal",
                    address_text=cust_addr,
                    city=dropoff_city,
                    barrio=dropoff_barrio,
                    notes=existing_addr.get("notes"),
                    lat=dropoff_lat,
                    lng=dropoff_lng,
                )
                if save_result["action"] == "coords_updated":
                    success_msg += "\n\nLa direccion ya existia en tu agenda y se completo su geolocalizacion."
            else:
                context.user_data["admin_ped_guardar_existing_id"] = existing_customer_id
                query.edit_message_text(
                    success_msg + "\n\n"
                    "Este cliente ya esta en tu agenda ({}).\n"
                    "Deseas agregar esta direccion a su perfil?".format(existing_customer_name or cust_name),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Si, agregar", callback_data="admin_ped_guardar_dir_si")],
                        [InlineKeyboardButton("No", callback_data="admin_ped_guardar_dir_no")],
                        [InlineKeyboardButton("Cancelar pedido", callback_data="admin_pedido_cancelar")],
                    ]),
                )
                return ADMIN_PEDIDO_GUARDAR_CUST
        else:
            query.edit_message_text(
                success_msg + "\n\nDeseas guardar a {} en tu agenda?".format(cust_name),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Si, guardar", callback_data="admin_ped_guardar_cust_si")],
                    [InlineKeyboardButton("No", callback_data="admin_ped_guardar_cust_no")],
                    [InlineKeyboardButton("Cancelar pedido", callback_data="admin_pedido_cancelar")],
                ]),
            )
            return ADMIN_PEDIDO_GUARDAR_CUST
    query.edit_message_text(success_msg)
    for key in list(context.user_data.keys()):
        if key.startswith("admin_ped_"):
            del context.user_data[key]
    return ConversationHandler.END


def admin_pedido_guardar_plantilla_callback(update, context):
    """Admin toca 'Guardar como plantilla' en el preview del pedido especial."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "Ingresa un nombre corto para esta plantilla\n"
        "(ej: 'Pollo Express', 'Farmacia Centro'):"
    )
    return ADMIN_PEDIDO_TEMPLATE_NAME


def admin_pedido_template_name_handler(update, context):
    """Recibe el nombre de la plantilla y la guarda."""
    nombre = update.message.text.strip()
    if not nombre:
        update.message.reply_text("El nombre no puede estar vacio. Intenta de nuevo:")
        return ADMIN_PEDIDO_TEMPLATE_NAME

    admin_id = context.user_data.get("admin_ped_admin_id")
    if not admin_id:
        update.message.reply_text("Error: sesion expirada. Vuelve al menu.")
        return ConversationHandler.END

    # Recolectar datos del pedido actual
    pickup_location_id = context.user_data.get("admin_ped_pickup_id")
    pickup_addr = context.user_data.get("admin_ped_pickup_addr", "")
    pickup_city = context.user_data.get("admin_ped_pickup_city", "")
    pickup_barrio = context.user_data.get("admin_ped_pickup_barrio", "")
    pickup_lat = context.user_data.get("admin_ped_pickup_lat")
    pickup_lng = context.user_data.get("admin_ped_pickup_lng")
    tarifa = int(context.user_data.get("admin_ped_tarifa", 0) or 0)
    comision = int(context.user_data.get("admin_ped_comision", 0) or 0)
    team_only = int(context.user_data.get("admin_ped_team_only", 0) or 0)
    instruc = context.user_data.get("admin_ped_instruc", "")

    try:
        save_order_template(
            admin_id=int(admin_id),
            name=nombre,
            pickup_location_id=pickup_location_id,
            pickup_addr=pickup_addr,
            pickup_city=pickup_city,
            pickup_barrio=pickup_barrio,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            tarifa=tarifa,
            comision=comision,
            team_only=team_only,
            instruc=instruc or "",
        )
        update.message.reply_text(
            'Plantilla "{}" guardada.\n'
            'La encontraras en "Usar plantilla" la proxima vez que crees un pedido especial.'.format(nombre)
        )
    except Exception as e:
        logger.error("admin_pedido_template_name_handler: %s", e)
        update.message.reply_text("Error al guardar la plantilla. Intenta de nuevo.")

    # Mostrar el preview de nuevo para que pueda confirmar
    from handlers.order import _admin_pedido_calcular_preview
    _admin_pedido_calcular_preview(update, context, edit=False)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_usar_plantilla_callback(update, context):
    """Admin toca 'Usar plantilla' al inicio del flujo — muestra lista de plantillas."""
    query = update.callback_query
    query.answer()

    telegram_id = update.effective_user.id
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin:
        query.edit_message_text("No tienes perfil de administrador.")
        return ConversationHandler.END

    templates = list_order_templates(admin["id"])
    if not templates:
        query.edit_message_text(
            "No tienes plantillas guardadas.\n"
            "Crea un pedido especial y guarda la configuracion como plantilla."
        )
        return ConversationHandler.END

    keyboard = []
    for t in templates[:10]:
        tid = t["id"] if hasattr(t, "__getitem__") else t[0]
        tname = t["name"] if hasattr(t, "__getitem__") else t[2]
        use_count = t["use_count"] if hasattr(t, "__getitem__") else t[13]
        tarifa = t["tarifa"] if hasattr(t, "__getitem__") else t[9]
        label = "{} — ${:,}{}".format(tname, tarifa, " ({}x)".format(use_count) if use_count else "")
        keyboard.append([
            InlineKeyboardButton(label, callback_data="admin_ped_tmpl_{}".format(tid)),
            InlineKeyboardButton("Eliminar", callback_data="admin_ped_tmpl_del_{}".format(tid)),
        ])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])

    context.user_data["admin_ped_admin_id"] = admin["id"]
    query.edit_message_text(
        "Selecciona una plantilla para pre-llenar el pedido:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_USE_TEMPLATE


def admin_mis_plantillas_callback(update, context):
    """Admin accede a 'Mis plantillas' desde el menu principal — lista con opcion de eliminar."""
    query = update.callback_query
    query.answer()

    telegram_id = update.effective_user.id
    data = query.data or ""
    match = re.fullmatch(r"admin_mis_plantillas(?:_(\d+))?", data)
    selected_admin_id = int(match.group(1)) if match and match.group(1) else None
    admin = resolve_owned_admin_actor(
        telegram_id,
        selected_admin_id=selected_admin_id,
        prefer_platform=False,
        legacy_counter_key="admin_templates_legacy_callback_count",
        invalid_counter_key="admin_templates_invalid_selected_count",
    )
    if selected_admin_id is not None and not admin:
        query.edit_message_text(
            "No se pudo validar este panel de plantillas.\n\n"
            "Vuelve a abrir Mi admin y entra de nuevo desde el boton actualizado."
        )
        return
    if not admin:
        query.edit_message_text("No tienes perfil de administrador.")
        return

    admin_id = admin["id"]
    templates = list_order_templates(admin["id"])
    if not templates:
        query.edit_message_text(
            "No tienes plantillas guardadas.\n\n"
            "Las plantillas se crean al finalizar un pedido especial — "
            'el bot te preguntara si deseas guardar la configuracion como plantilla.'
        )
        return

    keyboard = []
    for t in templates[:10]:
        tid = t["id"] if hasattr(t, "__getitem__") else t[0]
        tname = t["name"] if hasattr(t, "__getitem__") else t[2]
        use_count = t["use_count"] if hasattr(t, "__getitem__") else t[13]
        tarifa = t["tarifa"] if hasattr(t, "__getitem__") else t[9]
        label = "{} — ${:,}{}".format(tname, tarifa, " ({}x)".format(use_count) if use_count else "")
        keyboard.append([
            InlineKeyboardButton(label, callback_data="admin_ped_tmpl_info_{}_{}".format(tid, admin_id)),
            InlineKeyboardButton("Eliminar", callback_data="admin_ped_tmpl_menu_del_{}_{}".format(tid, admin_id)),
        ])

    query.edit_message_text(
        "Mis plantillas ({} guardadas):\n\n"
        "Toca el nombre para ver el detalle, o Eliminar para borrarla.".format(len(templates)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def admin_ped_tmpl_info_callback(update, context):
    """Muestra el detalle de una plantilla desde el menu Mis plantillas."""
    query = update.callback_query
    query.answer()

    match = re.fullmatch(r"admin_ped_tmpl_info_(\d+)(?:_(\d+))?", query.data or "")
    if not match:
        query.answer("Callback invalido.", show_alert=True)
        return
    template_id = int(match.group(1))
    selected_admin_id = int(match.group(2)) if match.group(2) else None
    telegram_id = update.effective_user.id
    admin = resolve_owned_admin_actor(
        telegram_id,
        selected_admin_id=selected_admin_id,
        prefer_platform=False,
        legacy_counter_key="admin_templates_info_legacy_callback_count",
        invalid_counter_key="admin_templates_info_invalid_selected_count",
    )
    if selected_admin_id is not None and not admin:
        query.edit_message_text(
            "No se pudo validar esta plantilla.\n\n"
            "Vuelve a abrir Mis plantillas desde el menu actualizado."
        )
        return
    if not admin:
        query.answer("Error.", show_alert=True)
        return

    admin_id = admin["id"]
    t = get_order_template_by_id(template_id, admin["id"])
    if not t:
        query.edit_message_text("Plantilla no encontrada.")
        return

    tname = t["name"] if hasattr(t, "__getitem__") else t[2]
    pickup_addr = t["pickup_addr"] if hasattr(t, "__getitem__") else t[4]
    tarifa = t["tarifa"] if hasattr(t, "__getitem__") else t[9]
    comision = t["comision"] if hasattr(t, "__getitem__") else t[10]
    team_only = t["team_only"] if hasattr(t, "__getitem__") else t[11]
    instruc = t["instruc"] if hasattr(t, "__getitem__") else t[12]
    use_count = t["use_count"] if hasattr(t, "__getitem__") else t[13]

    lines = [
        "Plantilla: {}".format(tname),
        "Pickup: {}".format(pickup_addr or "no definido"),
        "Valor configurado: ${:,}".format(tarifa or 0),
    ]
    if comision:
        lines.append("Comision al courier: ${:,}".format(comision))
    lines.append("Visibilidad: {}".format("Solo mi equipo" if team_only else "Todos los couriers"))
    if instruc:
        lines.append("Instrucciones: {}".format(instruc))
    lines.append("Usos: {}".format(use_count or 0))

    query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Eliminar", callback_data="admin_ped_tmpl_menu_del_{}_{}".format(template_id, admin_id)),
            InlineKeyboardButton("Volver", callback_data="admin_mis_plantillas_{}".format(admin_id)),
        ]]),
    )


def admin_ped_tmpl_menu_del_callback(update, context):
    """Elimina una plantilla desde el menu Mis plantillas y recarga la lista."""
    query = update.callback_query
    query.answer()

    match = re.fullmatch(r"admin_ped_tmpl_menu_del_(\d+)(?:_(\d+))?", query.data or "")
    if not match:
        query.answer("Callback invalido.", show_alert=True)
        return
    template_id = int(match.group(1))
    selected_admin_id = int(match.group(2)) if match.group(2) else None
    telegram_id = update.effective_user.id
    admin = resolve_owned_admin_actor(
        telegram_id,
        selected_admin_id=selected_admin_id,
        prefer_platform=False,
        legacy_counter_key="admin_templates_del_legacy_callback_count",
        invalid_counter_key="admin_templates_del_invalid_selected_count",
    )
    if selected_admin_id is not None and not admin:
        query.edit_message_text(
            "No se pudo validar esta plantilla.\n\n"
            "Vuelve a abrir Mis plantillas desde el menu actualizado."
        )
        return
    if not admin:
        query.answer("Error.", show_alert=True)
        return

    admin_id = admin["id"]
    delete_order_template(template_id, admin["id"])

    templates = list_order_templates(admin["id"])
    if not templates:
        query.edit_message_text("Plantilla eliminada. No tienes mas plantillas guardadas.")
        return

    keyboard = []
    for t in templates[:10]:
        tid = t["id"] if hasattr(t, "__getitem__") else t[0]
        tname = t["name"] if hasattr(t, "__getitem__") else t[2]
        use_count = t["use_count"] if hasattr(t, "__getitem__") else t[13]
        tarifa = t["tarifa"] if hasattr(t, "__getitem__") else t[9]
        label = "{} — ${:,}{}".format(tname, tarifa, " ({}x)".format(use_count) if use_count else "")
        keyboard.append([
            InlineKeyboardButton(label, callback_data="admin_ped_tmpl_info_{}_{}".format(tid, admin_id)),
            InlineKeyboardButton("Eliminar", callback_data="admin_ped_tmpl_menu_del_{}_{}".format(tid, admin_id)),
        ])

    query.edit_message_text(
        "Plantilla eliminada. Plantillas restantes ({}):\n\n"
        "Toca el nombre para ver el detalle, o Eliminar para borrarla.".format(len(templates)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def admin_pedido_tmpl_del_callback(update, context):
    """Admin elimina una plantilla desde la lista de seleccion."""
    query = update.callback_query
    query.answer()

    data = query.data or ""
    template_id = int(data.replace("admin_ped_tmpl_del_", ""))
    telegram_id = update.effective_user.id
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin:
        query.answer("Error: perfil no encontrado.", show_alert=True)
        return ADMIN_PEDIDO_USE_TEMPLATE

    delete_order_template(template_id, admin["id"])

    # Recargar la lista actualizada
    templates = list_order_templates(admin["id"])
    if not templates:
        query.edit_message_text("Plantilla eliminada. No tienes mas plantillas guardadas.")
        return ConversationHandler.END

    keyboard = []
    for t in templates[:10]:
        tid = t["id"] if hasattr(t, "__getitem__") else t[0]
        tname = t["name"] if hasattr(t, "__getitem__") else t[2]
        use_count = t["use_count"] if hasattr(t, "__getitem__") else t[13]
        tarifa = t["tarifa"] if hasattr(t, "__getitem__") else t[9]
        label = "{} — ${:,}{}".format(tname, tarifa, " ({}x)".format(use_count) if use_count else "")
        keyboard.append([
            InlineKeyboardButton(label, callback_data="admin_ped_tmpl_{}".format(tid)),
            InlineKeyboardButton("Eliminar", callback_data="admin_ped_tmpl_del_{}".format(tid)),
        ])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])
    query.edit_message_text(
        "Plantilla eliminada. Selecciona otra o cancela:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_USE_TEMPLATE


def admin_pedido_tmpl_sel_callback(update, context):
    """Admin selecciona una plantilla — pre-llena user_data y va al paso de cliente."""
    query = update.callback_query
    query.answer()

    data = query.data or ""
    template_id = int(data.replace("admin_ped_tmpl_", ""))
    admin_id = context.user_data.get("admin_ped_admin_id")
    if not admin_id:
        query.edit_message_text("Error: sesion expirada.")
        return ConversationHandler.END

    template = get_order_template_by_id(template_id, int(admin_id))
    if not template:
        query.edit_message_text("Plantilla no encontrada.")
        return ConversationHandler.END

    # Pre-llenar user_data con los datos de la plantilla
    t = template
    context.user_data["admin_ped_pickup_id"] = t["pickup_location_id"] if hasattr(t, "__getitem__") else t[3]
    context.user_data["admin_ped_pickup_addr"] = t["pickup_addr"] if hasattr(t, "__getitem__") else t[4]
    context.user_data["admin_ped_pickup_city"] = t["pickup_city"] if hasattr(t, "__getitem__") else t[5]
    context.user_data["admin_ped_pickup_barrio"] = t["pickup_barrio"] if hasattr(t, "__getitem__") else t[6]
    context.user_data["admin_ped_pickup_lat"] = t["pickup_lat"] if hasattr(t, "__getitem__") else t[7]
    context.user_data["admin_ped_pickup_lng"] = t["pickup_lng"] if hasattr(t, "__getitem__") else t[8]
    context.user_data["admin_ped_tarifa"] = t["tarifa"] if hasattr(t, "__getitem__") else t[9]
    context.user_data["admin_ped_comision"] = t["comision"] if hasattr(t, "__getitem__") else t[10]
    context.user_data["admin_ped_team_only"] = t["team_only"] if hasattr(t, "__getitem__") else t[11]
    context.user_data["admin_ped_instruc"] = t["instruc"] if hasattr(t, "__getitem__") else t[12]
    tname = t["name"] if hasattr(t, "__getitem__") else t[2]

    increment_order_template_usage(template_id, int(admin_id))

    pickup_addr = context.user_data["admin_ped_pickup_addr"] or "no definido"
    query.edit_message_text(
        'Plantilla "{}" cargada.\n'
        "Pickup: {}\n"
        "Valor configurado: ${:,}\n\n"
        "Ahora ingresa el nombre del cliente:".format(
            tname,
            pickup_addr,
            context.user_data["admin_ped_tarifa"],
        )
    )
    return ADMIN_PEDIDO_CUST_NAME


def admin_pedido_ver_todos_callback(update, context):
    """Admin toca 'Ver todos' en el selector de clientes del pedido especial."""
    query = update.callback_query
    query.answer()
    admin_id = context.user_data.get("admin_ped_admin_id")
    all_customers = list_admin_customers(admin_id, limit=50, include_inactive=False) if admin_id else []
    sorted_customers = sorted(all_customers, key=lambda c: (c["name"] or "").lower())
    keyboard = []
    for c in sorted_customers:
        btn_text = "{} - {}".format(c["name"], c["phone"])
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_pedido_sel_{}".format(c["id"]))])
    keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="admin_pedido_buscar_cust")])
    keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="admin_pedido_cliente_nuevo")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])
    query.edit_message_text(
        "TODOS LOS CLIENTES ({})\n\nSelecciona el cliente:".format(len(sorted_customers)),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_PEDIDO_SEL_CUST


def admin_pedido_buscar_cust_start(update, context):
    """Admin toca 'Buscar cliente' en la lista de su agenda durante pedido especial."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "Escribe el nombre o telefono del cliente.\nEscribe '.' para ver todos:"
    )
    return ADMIN_PEDIDO_SEL_CUST_BUSCAR


def admin_pedido_buscar_cust_handler(update, context):
    """Busca clientes del admin por nombre o telefono durante pedido especial."""
    texto = update.message.text.strip()
    admin_id = context.user_data.get("admin_ped_admin_id")

    if not texto:
        update.message.reply_text("Escribe al menos un caracter para buscar.")
        return ADMIN_PEDIDO_SEL_CUST_BUSCAR
    if len(texto) > 60:
        update.message.reply_text("El texto es muy largo. Intenta con menos caracteres.")
        return ADMIN_PEDIDO_SEL_CUST_BUSCAR

    activos = search_admin_customers(admin_id, texto) if admin_id else []
    if not activos:
        recientes = list_admin_customers(admin_id, limit=5, include_inactive=False) if admin_id else []
        if recientes:
            keyboard = []
            for c in recientes:
                btn_text = "{} - {}".format(c["name"], c["phone"])
                keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_pedido_sel_{}".format(c["id"]))])
            keyboard.append([InlineKeyboardButton("Buscar de nuevo", callback_data="admin_pedido_buscar_cust")])
            keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="admin_pedido_cliente_nuevo")])
            keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])
            update.message.reply_text(
                "No encontre clientes con '{}'.\n\nTus clientes recientes:".format(texto),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ADMIN_PEDIDO_SEL_CUST
        update.message.reply_text(
            "No se encontro ningun cliente con '{}'.\n\nEscribe el nombre del cliente:".format(texto)
        )
        return ADMIN_PEDIDO_CUST_NAME
    mostrados = activos[:10]
    encabezado = "Resultados para '{}'{}:\n\nSelecciona el cliente:".format(
        texto, " (mostrando 10)" if len(activos) >= 10 else ""
    )
    keyboard = []
    for c in mostrados:
        btn_text = "{} - {}".format(c["name"], c["phone"])
        keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_pedido_sel_{}".format(c["id"]))])
    keyboard.append([InlineKeyboardButton("Buscar de nuevo", callback_data="admin_pedido_buscar_cust")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])
    update.message.reply_text(encabezado, reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_PEDIDO_SEL_CUST


def admin_pedido_cust_dedup_callback(update, context):
    """Confirma si usar cliente existente encontrado por telefono en admin_pedido."""
    query = update.callback_query
    query.answer()
    if query.data == "admin_ped_dedup_si":
        cust_id = context.user_data.pop("admin_ped_dedup_cust_id", None)
        name = context.user_data.pop("admin_ped_dedup_name", "")
        context.user_data["admin_ped_cust_name"] = name
        context.user_data["admin_ped_selected_cust_id"] = cust_id
        addrs = list_admin_customer_addresses(cust_id) if cust_id else []
        activas = [a for a in addrs if a["status"] == "ACTIVE"]
        if activas:
            keyboard = []
            for a in activas[:8]:
                btn_text = _pedido_customer_address_button_text(a)
                keyboard.append([InlineKeyboardButton(btn_text, callback_data="acust_pedido_addr_{}".format(a["id"]))])
            keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="acust_pedido_addr_nueva")])
            query.edit_message_text(
                "Cliente: {}\n\nSelecciona la direccion de entrega:".format(name),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ADMIN_PEDIDO_SEL_CUST_ADDR
        query.edit_message_text(
            "Cliente: {}\n\nEscribe la direccion de entrega o envia GPS:".format(name)
        )
        return ADMIN_PEDIDO_CUST_ADDR
    else:
        context.user_data.pop("admin_ped_dedup_cust_id", None)
        context.user_data.pop("admin_ped_dedup_name", None)
        query.edit_message_text("Escribe la direccion de entrega del cliente:")
        return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_guardar_cust_callback(update, context):
    """Maneja la decision de guardar cliente/direccion tras crear pedido admin."""
    query = update.callback_query
    query.answer()
    admin_id = context.user_data.get("admin_ped_admin_id")
    cust_name = context.user_data.get("admin_ped_cust_name", "")
    cust_phone = context.user_data.get("admin_ped_cust_phone", "")
    addr = context.user_data.get("admin_ped_cust_addr", "")
    city = context.user_data.get("admin_ped_dropoff_city", "")
    barrio = context.user_data.get("admin_ped_dropoff_barrio", "")
    lat = context.user_data.get("admin_ped_dropoff_lat")
    lng = context.user_data.get("admin_ped_dropoff_lng")
    label = barrio or city or "Principal"
    data = query.data
    parking_address_id = None
    saved_message = "Guardado."
    if data == "admin_ped_guardar_cust_si":
        try:
            new_id = create_admin_customer(admin_id, cust_name, cust_phone)
            parking_address_id = create_admin_customer_address(new_id, label, addr, city=city, barrio=barrio, lat=lat, lng=lng)
        except Exception as e:
            query.edit_message_text("No se pudo guardar el cliente: {}".format(e))
            for key in list(context.user_data.keys()):
                if key.startswith("admin_ped_"):
                    del context.user_data[key]
            return ConversationHandler.END
    elif data == "admin_ped_guardar_dir_si":
        existing_id = context.user_data.get("admin_ped_guardar_existing_id")
        try:
            save_result = upsert_admin_customer_address_for_agenda(
                customer_id=existing_id,
                label=label,
                address_text=addr,
                city=city,
                barrio=barrio,
                lat=lat,
                lng=lng,
            )
            if save_result["action"] == "created":
                parking_address_id = save_result["address_id"]
            elif save_result["action"] == "coords_updated":
                saved_message = "La direccion ya existia y se completo su geolocalizacion."
            else:
                saved_message = "La direccion ya estaba guardada en la agenda."
        except Exception as e:
            query.edit_message_text("No se pudo agregar la direccion: {}".format(e))
            for key in list(context.user_data.keys()):
                if key.startswith("admin_ped_"):
                    del context.user_data[key]
            return ConversationHandler.END
    else:
        query.edit_message_text("OK, no se guardo.")
        for key in list(context.user_data.keys()):
            if key.startswith("admin_ped_"):
                del context.user_data[key]
        return ConversationHandler.END

    if parking_address_id is None:
        query.edit_message_text(saved_message)
        for key in list(context.user_data.keys()):
            if key.startswith("admin_ped_"):
                del context.user_data[key]
        show_main_menu(update, context)
        return ConversationHandler.END

    context.user_data["admin_ped_parking_address_id"] = parking_address_id
    keyboard = [
        [InlineKeyboardButton("Si, hay dificultad para parquear", callback_data="admin_ped_guardar_parking_si")],
        [InlineKeyboardButton("No / No lo se", callback_data="admin_ped_guardar_parking_no")],
        [InlineKeyboardButton("Omitir", callback_data="admin_ped_guardar_parking_no")],
    ]
    query.edit_message_text(
        "{}\n\n"
        "En ese punto de entrega hay dificultad para parquear moto o bicicleta?\n"
        "(zona restringida, riesgo de comparendo o sin lugar seguro para dejar el vehiculo)".format(saved_message),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_GUARDAR_PARKING


def pedido_guardar_dir_parking_callback(update, context):
    """Respuesta de parqueo al guardar nueva direccion para cliente existente mid-pedido."""
    query = update.callback_query
    query.answer()
    address_id = context.user_data.pop("pedido_parking_address_id", None)
    if address_id:
        if query.data == "pedido_dir_parking_si":
            set_address_parking_status(address_id, "ALLY_YES")
        else:
            set_address_parking_status(address_id, "PENDING_REVIEW")
    return mostrar_selector_pickup(query, context, edit=False)


def pedido_guardar_cust_parking_callback(update, context):
    """Respuesta de parqueo al guardar cliente nuevo tras crear pedido."""
    query = update.callback_query
    query.answer()
    address_id = context.user_data.pop("pedido_guardar_parking_address_id", None)
    customer_name = context.user_data.get("customer_name", "")
    success_text = context.user_data.get("pedido_success_text", "Pedido creado exitosamente.")
    if address_id:
        if query.data == "pedido_guardar_cust_parking_si":
            set_address_parking_status(address_id, "ALLY_YES")
        else:
            set_address_parking_status(address_id, "PENDING_REVIEW")
    context.user_data.clear()
    show_main_menu(
        update,
        context,
        _append_success_followup(
            success_text,
            "Cliente '{}' guardado para futuros pedidos.".format(customer_name),
        ),
    )
    return ConversationHandler.END


def admin_pedido_guardar_parking_callback(update, context):
    """Respuesta de parqueo al guardar cliente tras pedido especial del admin."""
    query = update.callback_query
    query.answer()
    address_id = context.user_data.pop("admin_ped_parking_address_id", None)
    if address_id:
        if query.data == "admin_ped_guardar_parking_si":
            set_address_parking_status(address_id, "ALLY_YES", table="admin_customer_addresses")
        else:
            set_address_parking_status(address_id, "PENDING_REVIEW", table="admin_customer_addresses")
    for key in list(context.user_data.keys()):
        if key.startswith("admin_ped_"):
            del context.user_data[key]
    show_main_menu(update, context)
    return ConversationHandler.END


def admin_pedido_cancelar_callback(update, context):
    """Cancela el flujo de pedido especial del admin."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith("admin_ped_"):
            del context.user_data[key]
    query.edit_message_text("Pedido cancelado.")
    return ConversationHandler.END


# ---- Editar campos desde el preview (admin_pedido_conv) ----

def admin_pedido_edit_pickup_callback(update, context):
    """Desde el preview admin: volver a seleccionar punto de recogida."""
    query = update.callback_query
    query.answer()
    context.user_data["admin_ped_edit_from_preview"] = True
    admin_id = context.user_data.get("admin_ped_admin_id")
    locations = get_admin_locations(admin_id)
    keyboard = []
    for loc in locations:
        label = _pedido_pickup_option_text(loc)
        keyboard.append([InlineKeyboardButton(
            label, callback_data="admin_pedido_pickup_{}".format(loc["id"])
        )])
    keyboard.append([InlineKeyboardButton("Nueva direccion de recogida", callback_data="admin_pedido_nueva_dir")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])
    query.edit_message_text(
        "Selecciona el nuevo punto de recogida:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_PICKUP


def admin_pedido_edit_cust_callback(update, context):
    """Desde el preview admin: volver a seleccionar o ingresar cliente."""
    query = update.callback_query
    query.answer()
    context.user_data["admin_ped_edit_from_preview"] = True
    return _admin_pedido_mostrar_selector_cliente(query, context, edit=True)


def admin_pedido_cliente_nuevo_callback(update, context):
    """Admin elige 'Cliente nuevo' desde el selector de clientes."""
    query = update.callback_query
    query.answer()
    context.user_data["admin_ped_is_new_customer"] = True
    query.edit_message_text("Escribe el nombre del cliente:")
    return ADMIN_PEDIDO_CUST_NAME


def admin_pedido_edit_tarifa_callback(update, context):
    """Desde el preview admin: volver a ingresar tarifa al repartidor."""
    query = update.callback_query
    query.answer()
    context.user_data["admin_ped_edit_from_preview"] = True
    query.edit_message_text("Escribe la nueva tarifa al repartidor (en pesos):")
    return ADMIN_PEDIDO_TARIFA


# =============================================================================
# Handlers para agregar paradas extra a un pedido (conversion a ruta en preview)
# =============================================================================

def pedido_agregar_parada_callback(update, context):
    """Inicia captura de una parada adicional desde la pantalla de confirmacion."""
    query = update.callback_query
    query.answer()
    paradas_extra = context.user_data.get("pedido_paradas_extra", [])
    n = len(paradas_extra) + 2  # parada 1 es la original; nueva seria la n
    query.edit_message_text(
        "Parada {}:\n\nEscribe el nombre del cliente:".format(n)
    )
    return PEDIDO_PARADA_EXTRA_NOMBRE


def pedido_extra_nombre_handler(update, context):
    """Captura el nombre del cliente de la parada extra."""
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text("El nombre no puede estar vacio. Escribe el nombre del cliente:")
        return PEDIDO_PARADA_EXTRA_NOMBRE
    context.user_data["pedido_extra_temp_name"] = texto
    update.message.reply_text("Escribe el telefono del cliente:")
    return PEDIDO_PARADA_EXTRA_TELEFONO


def pedido_extra_telefono_handler(update, context):
    """Captura el telefono del cliente de la parada extra."""
    texto = update.message.text.strip()
    digits = "".join(c for c in texto if c.isdigit())
    if len(digits) < 7:
        update.message.reply_text("Ingresa un telefono valido (minimo 7 digitos):")
        return PEDIDO_PARADA_EXTRA_TELEFONO
    context.user_data["pedido_extra_temp_phone"] = texto
    update.message.reply_text(
        "Escribe la direccion de entrega para esta parada:\n(Puedes enviar la ubicacion GPS o escribir la direccion)"
    )
    return PEDIDO_PARADA_EXTRA_DIRECCION


def pedido_extra_direccion_handler(update, context):
    """Captura la direccion de la parada extra por texto con geocoding."""
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text("Escribe la direccion de entrega:")
        return PEDIDO_PARADA_EXTRA_DIRECCION
    _hint = _order_city_hint(context)
    geo = resolve_location(texto, city_hint=_hint)
    if geo and has_valid_coords(geo.get("lat"), geo.get("lng")):
        context.user_data["pending_geo_city_hint"] = _hint
        context.user_data["pedido_extra_geo_pending"] = {
            "lat": geo["lat"],
            "lng": geo["lng"],
            "address": geo.get("address", texto),
            "city": geo.get("city", ""),
            "barrio": geo.get("barrio", ""),
            "original_text": texto,
        }
        _mostrar_confirmacion_geocode(
            update.message, context,
            geo, texto,
            "pedido_extra_geo_si", "pedido_extra_geo_no",
        )
        return PEDIDO_PARADA_EXTRA_DIRECCION
    # Sin resultado: pedir GPS
    update.message.reply_text(
        "No encontre esa direccion.\n\nEnvia la ubicacion GPS de la parada o escribe la direccion de otra forma."
    )
    return PEDIDO_PARADA_EXTRA_DIRECCION


def pedido_extra_gps_handler(update, context):
    """Captura GPS de la parada extra."""
    location = update.message.location
    context.user_data["pedido_extra_temp_lat"] = location.latitude
    context.user_data["pedido_extra_temp_lng"] = location.longitude
    context.user_data["pedido_extra_temp_address"] = context.user_data.get("pedido_extra_temp_address", "")
    context.user_data["pedido_extra_temp_city"] = ""
    context.user_data["pedido_extra_temp_barrio"] = ""
    return _pedido_extra_guardar_y_mostrar(update, context)


def pedido_extra_geo_callback(update, context):
    """Confirma o rechaza geocoding de la parada extra."""
    query = update.callback_query
    query.answer()
    if query.data == "pedido_extra_geo_si":
        pending = context.user_data.pop("pedido_extra_geo_pending", {})
        context.user_data["pedido_extra_temp_lat"] = pending.get("lat")
        context.user_data["pedido_extra_temp_lng"] = pending.get("lng")
        context.user_data["pedido_extra_temp_address"] = pending.get("address", "")
        context.user_data["pedido_extra_temp_city"] = pending.get("city", "")
        context.user_data["pedido_extra_temp_barrio"] = pending.get("barrio", "")
        return _pedido_extra_guardar_y_mostrar(query, context)
    else:  # pedido_extra_geo_no
        return _geo_siguiente_o_gps(query, context, "pedido_extra_geo_si", "pedido_extra_geo_no", PEDIDO_PARADA_EXTRA_DIRECCION)


def _pedido_extra_guardar_y_mostrar(update_or_query, context):
    """Guarda la parada temporal en pedido_paradas_extra y vuelve al resumen del pedido."""
    parada = {
        "name": context.user_data.pop("pedido_extra_temp_name", ""),
        "phone": context.user_data.pop("pedido_extra_temp_phone", ""),
        "address": context.user_data.pop("pedido_extra_temp_address", ""),
        "city": context.user_data.pop("pedido_extra_temp_city", ""),
        "barrio": context.user_data.pop("pedido_extra_temp_barrio", ""),
        "lat": context.user_data.pop("pedido_extra_temp_lat", None),
        "lng": context.user_data.pop("pedido_extra_temp_lng", None),
    }
    context.user_data.pop("pedido_extra_geo_pending", None)
    paradas_extra = context.user_data.get("pedido_paradas_extra", [])
    paradas_extra.append(parada)
    context.user_data["pedido_paradas_extra"] = paradas_extra

    resumen = construir_resumen_pedido(context)
    keyboard = _pedido_confirmacion_keyboard(context)
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(resumen, reply_markup=markup)
    else:
        update_or_query.message.reply_text(resumen, reply_markup=markup)
    return PEDIDO_CONFIRMACION


def _pedido_confirmar_como_ruta(query, context):
    """Crea y publica una ruta cuando el aliado convirtio su pedido agregando paradas extra."""
    ally_id = context.user_data.get("ally_id")
    if not ally_id:
        query.edit_message_text("Error: sesion expirada. Usa /nuevo_pedido de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    # Reutilizar datos calculados en _construir_resumen_ruta_desde_pedido
    all_paradas = context.user_data.get("ruta_paradas_desde_pedido")
    precio_info = context.user_data.get("ruta_precio_desde_pedido")
    total_km = context.user_data.get("ruta_distancia_desde_pedido", 0)

    # Si por alguna razon no se calcularon aun (ej. preview no fue actualizado), calcular ahora
    if not all_paradas or not precio_info:
        _construir_resumen_ruta_desde_pedido(context)
        all_paradas = context.user_data.get("ruta_paradas_desde_pedido", [])
        precio_info = context.user_data.get("ruta_precio_desde_pedido", {})
        total_km = context.user_data.get("ruta_distancia_desde_pedido", 0)

    if not all_paradas or len(all_paradas) < 2:
        query.edit_message_text("Error: datos de ruta incompletos. Intenta de nuevo.")
        context.user_data.clear()
        show_main_menu(query, context)
        return ConversationHandler.END

    # Verificar que todas las paradas tienen coordenadas
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")
    if not has_valid_coords(pickup_lat, pickup_lng):
        query.edit_message_text("La recogida requiere ubicacion confirmada.")
        return PEDIDO_CONFIRMACION
    for p in all_paradas:
        if not has_valid_coords(p.get("lat"), p.get("lng")):
            query.edit_message_text(
                "La parada '{}' no tiene ubicacion confirmada. Intenta agregar la direccion de nuevo.".format(
                    p.get("address", "sin nombre"))
            )
            return PEDIDO_CONFIRMACION

    link = get_approved_admin_link_for_ally(ally_id)
    admin_id_snapshot = link["admin_id"] if link else None

    # Validar saldo para fee de ruta: $300 base + $200 por parada adicional
    n_paradas = len(all_paradas)
    fee_total_aliado = 300 + 200 * (n_paradas - 1)
    if admin_id_snapshot:
        saldo = get_ally_link_balance(ally_id, admin_id_snapshot)
        if saldo < fee_total_aliado:
            query.edit_message_text(
                "Saldo insuficiente para crear la ruta.\n"
                "Necesitas: ${:,}\nTu saldo actual: ${:,}\n\n"
                "Solicita una recarga a tu administrador.".format(fee_total_aliado, saldo)
            )
            context.user_data.clear()
            show_main_menu(query, context)
            return ConversationHandler.END

    pickup_location = context.user_data.get("pickup_location")
    pickup_location_id = pickup_location["id"] if pickup_location else None
    if not pickup_location_id:
        default_loc = get_default_ally_location(ally_id)
        pickup_location_id = default_loc["id"] if default_loc else None
    pickup_address = context.user_data.get("pickup_address", "")

    base_instructions = context.user_data.get("instructions", "")
    incentivo = int(context.user_data.get("pedido_incentivo", 0) or 0)
    requires_cash = bool(context.user_data.get("requires_cash"))
    cash_required_amount = int(context.user_data.get("cash_required_amount") or 0)

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
            instructions=base_instructions or None,
            ally_admin_id_snapshot=admin_id_snapshot,
            requires_cash=requires_cash,
            cash_required_amount=cash_required_amount,
        )
    except Exception as e:
        query.edit_message_text("Error al crear la ruta: {}".format(str(e)))
        context.user_data.pop("pedido_processed", None)
        return PEDIDO_CONFIRMACION

    for i, parada in enumerate(all_paradas, 1):
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

    if incentivo > 0:
        add_route_incentive(route_id, incentivo)

    if pickup_location_id:
        try:
            increment_pickup_usage(pickup_location_id, ally_id)
        except Exception:
            pass

    count = publish_route_to_couriers(route_id, ally_id, context, admin_id_override=admin_id_snapshot)
    route_row = get_route_by_id(route_id)
    msg = build_route_creation_summary_text(route_row, build_market_launch_status_text(count))

    query.edit_message_text(msg)
    context.user_data.clear()
    show_main_menu(query, context)
    return ConversationHandler.END



def _resolve_ally_admin_id(ally_id, chat_id, context, from_user_id):
    """Resuelve el admin_id para publicar el pedido de un aliado.

    Retorna (admin_id, True) en exito.
    Retorna (None, False) en error (el mensaje de error ya fue enviado al aliado).
    """
    admin_link = get_approved_admin_link_for_ally(ally_id)
    if admin_link:
        return admin_link["admin_id"], True

    latest_admin_link = get_admin_link_for_ally(ally_id)
    latest_link_status = (latest_admin_link["link_status"] or "").upper() if latest_admin_link else ""

    if latest_admin_link and latest_link_status in ("PENDING", "REJECTED", "INACTIVE"):
        ok_cov, cov_msg, migrated_couriers = ensure_platform_temp_coverage_for_ally(ally_id)
        if ok_cov:
            platform_admin = get_platform_admin()
            admin_id = platform_admin["id"] if platform_admin else None
            logger.info(
                "Cobertura temporal plataforma aplicada para ally_id=%s couriers_migrados=%s",
                ally_id, migrated_couriers,
            )
            context.bot.send_message(
                chat_id=chat_id,
                text=(
                    "Tu administracion local aun no esta aprobada. "
                    "Activamos cobertura temporal con Plataforma para que puedas operar.\n"
                    "Te recomendamos solicitar migracion a un admin APPROVED desde \'Solicitar cambio\'."
                ),
            )
            return admin_id, True
        context.bot.send_message(
            chat_id=chat_id,
            text="No se pudo activar cobertura temporal: {}".format(cov_msg),
        )
        return None, False

    if user_has_platform_admin(from_user_id):
        platform_admin = get_platform_admin()
        if platform_admin:
            logger.info("Platform bypass aplicado: aliado sin link APPROVED, pedido con admin plataforma.")
            return platform_admin["id"], True
        context.bot.send_message(
            chat_id=chat_id,
            text=(
                "No se encontro Admin Plataforma activo para continuar.\n"
                "Contacta soporte de plataforma."
            ),
        )
        return None, False

    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "No tienes un administrador APPROVED vinculado.\n"
            "No se puede crear ni publicar el pedido hasta tener un vinculo aprobado."
        ),
    )
    return None, False


def _check_ally_fee_for_order(ally_id, admin_id, chat_id, context):
    """Verifica saldo antes de crear pedido. Retorna True si puede proceder.

    Si retorna False el mensaje de error ya fue enviado al aliado.
    """
    fee_ok, fee_code = check_service_fee_available(
        target_type="ALLY",
        target_id=ally_id,
        admin_id=admin_id,
    )
    if fee_ok:
        return True

    if fee_code == "ADMIN_SIN_SALDO":
        context.bot.send_message(
            chat_id=chat_id,
            text=(
                "Tu administrador no tiene saldo suficiente para operar. "
                "Contacta a tu administrador o recarga directamente con plataforma."
            ),
        )
        try:
            admin_row = get_admin_by_id(admin_id)
            if admin_row:
                admin_user = get_user_by_id(admin_row["user_id"])
                if admin_user:
                    context.bot.send_message(
                        chat_id=admin_user["telegram_id"],
                        text=(
                            "Tu equipo no puede operar porque no tienes saldo. "
                            "Recarga con plataforma para que tu equipo siga generando ganancias."
                        ),
                    )
        except Exception as e:
            logger.warning("No se pudo notificar al admin: %s", e)
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text="No tienes saldo suficiente para este servicio. Recarga para continuar.",
        )
    return False


def _create_and_publish_order(ally_id, admin_id, context):
    """Crea el pedido en BD y lo publica a couriers.

    Retorna (order_id, published_count, pricing, pickup_text).
    Lanza Exception en caso de error de BD.
    """
    pickup_location = context.user_data.get("pickup_location")
    pickup_text = context.user_data.get("pickup_address", "")
    if pickup_location:
        pickup_location_id = pickup_location["id"]
    else:
        default_location = get_default_ally_location(ally_id)
        pickup_location_id = default_location["id"] if default_location else None
        if not pickup_text and default_location:
            pickup_text = default_location["address"] or "No definida"
    if not pickup_text:
        pickup_text = "No definida"

    customer_name = context.user_data.get("customer_name", "")
    customer_phone = context.user_data.get("customer_phone", "")
    customer_address = context.user_data.get("customer_address", "")
    customer_city = context.user_data.get("customer_city", "")
    customer_barrio = context.user_data.get("customer_barrio", "")
    service_type = context.user_data.get("service_type", "")
    distance_km = context.user_data.get("quote_distance_km", 0.0)
    requires_cash = context.user_data.get("requires_cash", False)
    cash_required_amount = context.user_data.get("cash_required_amount", 0)
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")
    dropoff_lat = context.user_data.get("dropoff_lat")
    dropoff_lng = context.user_data.get("dropoff_lng")
    quote_source = context.user_data.get("quote_source", "text")

    base_instructions = context.user_data.get("instructions", "")
    buy_products_list = context.user_data.get("buy_products_list", "")
    if service_type == "Compras" and buy_products_list:
        instructions_final = "[Lista Compras: {}]".format(buy_products_list)
        if base_instructions:
            instructions_final += "\n{}".format(base_instructions)
    else:
        instructions_final = base_instructions

    pedido_incentivo = int(context.user_data.get("pedido_incentivo", 0) or 0)
    if pedido_incentivo < 0:
        pedido_incentivo = 0
    pricing = build_order_pricing_breakdown(
        distance_km=distance_km,
        service_type=service_type,
        buy_products_count=context.user_data.get("buy_products_count", 0),
        additional_incentive=pedido_incentivo,
    )
    parking_fee_val = int(context.user_data.get("pedido_parking_fee") or 0)

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
        base_fee=pricing["base_fee"],
        distance_km=pricing["distance_km"],
        buy_surcharge=pricing["buy_surcharge"],
        rain_extra=0,
        high_demand_extra=0,
        night_extra=0,
        additional_incentive=pricing["additional_incentive"],
        total_fee=pricing["total_fee"] + parking_fee_val,
        instructions=instructions_final,
        requires_cash=requires_cash,
        cash_required_amount=cash_required_amount,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        dropoff_lat=dropoff_lat,
        dropoff_lng=dropoff_lng,
        quote_source=quote_source,
        ally_admin_id_snapshot=admin_id,
        purchase_amount=context.user_data.get("pedido_purchase_amount"),
        delivery_subsidy_applied=int(context.user_data.get("pedido_subsidio_efectivo") or 0),
        customer_delivery_fee=context.user_data.get("pedido_customer_delivery_fee"),
        payment_method=_pedido_payment_method_from_base(requires_cash, cash_required_amount),
        parking_fee=parking_fee_val,
    )
    context.user_data["order_id"] = order_id

    published_count = 0
    try:
        published_count = publish_order_to_couriers(
            order_id,
            ally_id,
            context,
            admin_id_override=admin_id,
            pickup_city=context.user_data.get("pickup_city"),
            pickup_barrio=context.user_data.get("pickup_barrio"),
            dropoff_city=context.user_data.get("customer_city"),
            dropoff_barrio=context.user_data.get("customer_barrio"),
        )
    except Exception as e:
        logger.warning("Error al publicar pedido a couriers: %s", e)

    if pickup_location_id:
        increment_pickup_usage(pickup_location_id, ally_id)

    return order_id, published_count, pricing, pickup_text


def _handle_post_order_ui(query, update, context, order_id, ally_id, published_count, pricing, pickup_text):
    """UI post-creacion: preview, oferta guardar cliente/direccion, menu de exito.

    Retorna el estado de ConversationHandler correspondiente.
    """
    service_type = context.user_data.get("service_type", "")
    requires_cash = context.user_data.get("requires_cash", False)
    cash_required_amount = context.user_data.get("cash_required_amount", 0)
    customer_address = context.user_data.get("customer_address", "")
    customer_city = context.user_data.get("customer_city", "")
    customer_barrio = context.user_data.get("customer_barrio", "")
    customer_phone = context.user_data.get("customer_phone", "")
    customer_id_ctx = context.user_data.get("customer_id")
    is_new_customer = context.user_data.get("is_new_customer", False)
    dropoff_lat = context.user_data.get("dropoff_lat")
    dropoff_lng = context.user_data.get("dropoff_lng")

    order_preview_row = get_order_by_id(order_id)
    preview = construir_preview_oferta(
        order_preview_row,
        service_type=service_type,
        pickup_city=context.user_data.get("pickup_city"),
        pickup_barrio=context.user_data.get("pickup_barrio"),
        dropoff_city=customer_city,
        dropoff_barrio=customer_barrio,
    )
    market_status_text = build_market_launch_status_text(published_count)
    success_text = build_order_creation_summary_text(order_preview_row, market_status_text)
    context.user_data["pedido_success_text"] = success_text

    try:
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Si quieres, puedes agregar o aumentar el incentivo cuando quieras.\nPedido: #{}".format(order_id),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Aumentar incentivo", callback_data="pedido_inc_menu_{}".format(order_id))]]
            ),
        )
    except Exception:
        pass

    existing_customer = get_ally_customer_by_phone(ally_id, customer_phone) if customer_phone else None
    should_offer_save_customer = bool((is_new_customer or not customer_id_ctx) and not existing_customer)

    if should_offer_save_customer:
        query.edit_message_text(
            _append_success_followup(success_text, "Quieres guardar este cliente para futuros pedidos?"),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Si, guardar cliente", callback_data="pedido_guardar_si")],
                [InlineKeyboardButton("No, solo este pedido", callback_data="pedido_guardar_no")],
            ]),
        )
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text=preview,
            reply_markup=get_preview_buttons(),
        )
        return PEDIDO_GUARDAR_CLIENTE

    addr_already_saved = False
    if existing_customer and has_valid_coords(dropoff_lat, dropoff_lng):
        addr_match = find_matching_customer_address(
            existing_customer["id"], customer_address, customer_city, customer_barrio
        )
        addr_already_saved = bool(addr_match)
        if not addr_already_saved:
            context.user_data["guardar_dir_existing_cust_id"] = existing_customer["id"]

    if existing_customer and has_valid_coords(dropoff_lat, dropoff_lng) and not addr_already_saved:
        save_prompt = "Deseas agregar esta direccion a la agenda de {}?".format(
            existing_customer["name"] or "este cliente"
        )
        query.edit_message_text(
            _append_success_followup(success_text, save_prompt),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Si, agregar", callback_data="pedido_guardar_dir_si")],
                [InlineKeyboardButton("No", callback_data="pedido_guardar_dir_no")],
            ]),
        )
        return PEDIDO_GUARDAR_DIR_EXISTENTE

    try:
        query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    context.user_data.clear()
    show_main_menu(
        update, context,
        success_text,
    )
    return ConversationHandler.END


def pedido_confirmacion_callback(update, context):
    """Maneja la confirmacion/cancelacion del pedido por botones."""
    query = update.callback_query
    query.answer()
    data = query.data

    if context.user_data.get("pedido_processed"):
        query.edit_message_text("Este pedido ya fue procesado.")
        return ConversationHandler.END

    if data == "pedido_confirmar":
        context.user_data["pedido_processed"] = True

        if context.user_data.get("pedido_paradas_extra"):
            return _pedido_confirmar_como_ruta(query, context)

        ally_id = context.user_data.get("ally_id")
        if not ally_id:
            query.edit_message_text("Error: sesion expirada. Usa /nuevo_pedido de nuevo.")
            context.user_data.clear()
            return ConversationHandler.END
        chat_id = query.message.chat_id

        admin_id, ok = _resolve_ally_admin_id(ally_id, chat_id, context, query.from_user.id)
        if not ok:
            context.user_data.clear()
            return ConversationHandler.END

        if not _check_ally_fee_for_order(ally_id, admin_id, chat_id, context):
            context.user_data.clear()
            return ConversationHandler.END

        if not has_valid_coords(context.user_data.get("pickup_lat"), context.user_data.get("pickup_lng")) or \
           not has_valid_coords(context.user_data.get("dropoff_lat"), context.user_data.get("dropoff_lng")):
            context.user_data.pop("pedido_processed", None)
            query.edit_message_text(
                "El pedido requiere ubicacion confirmada en recogida y entrega.\n\n"
                "Envia la ubicacion valida antes de confirmar."
            )
            return PEDIDO_UBICACION

        try:
            order_id, published_count, pricing, pickup_text = _create_and_publish_order(
                ally_id, admin_id, context
            )
        except Exception as e:
            query.edit_message_text(
                "Error al crear el pedido: {}\n\nPor favor intenta nuevamente mas tarde.".format(e)
            )
            context.user_data.clear()
            show_main_menu(update, context)
            return ConversationHandler.END

        _form_req_id = context.user_data.get("bandeja_form_request_id")
        if _form_req_id:
            try:
                mark_ally_form_request_converted(_form_req_id, ally_id, order_id)
            except Exception as e:
                logger.warning("mark_ally_form_request_converted failed: req=%s order=%s err=%s",
                               _form_req_id, order_id, e)

        return _handle_post_order_ui(
            query, update, context, order_id, ally_id, published_count, pricing, pickup_text
        )

    elif data == "pedido_cancelar":
        query.edit_message_text("Pedido cancelado.")
        context.user_data.clear()
        show_main_menu(update, context)
        return ConversationHandler.END

    return PEDIDO_CONFIRMACION

def construir_preview_oferta(
    order,
    service_type="",
    pickup_city=None,
    pickup_barrio=None,
    dropoff_city=None,
    dropoff_barrio=None,
):
    """Construye un preview espejo del bloque real que recibe el courier."""
    if not order:
        return "No pude reconstruir el preview exacto del courier."

    summary_lines = []
    if service_type:
        summary_lines.append("Servicio: {}".format(service_type))

    preview_text = build_courier_order_preview_text(
        order,
        pickup_city_override=pickup_city,
        pickup_barrio_override=pickup_barrio,
        dropoff_city_override=dropoff_city,
        dropoff_barrio_override=dropoff_barrio,
    )
    if summary_lines:
        return "{}\n\n{}".format("\n".join(summary_lines), preview_text)
    return preview_text


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
    success_text = context.user_data.get("pedido_success_text", "Pedido creado exitosamente.")

    if data == "pedido_guardar_si":
        ally_id = context.user_data.get("active_ally_id")
        customer_name = context.user_data.get("customer_name", "")
        customer_phone = context.user_data.get("customer_phone", "")
        customer_address = context.user_data.get("customer_address", "")
        if customer_address and not has_valid_coords(
            context.user_data.get("dropoff_lat"),
            context.user_data.get("dropoff_lng"),
        ):
            context.user_data.clear()
            show_main_menu(
                update,
                context,
                "Pedido creado exitosamente.\nLa direccion no se guardo porque no tenia ubicacion confirmada.",
            )
            return ConversationHandler.END

        try:
            # Crear cliente si no existe uno activo por telefono.
            existing_customer = get_ally_customer_by_phone(ally_id, customer_phone)
            if existing_customer:
                customer_id = existing_customer["id"]
            else:
                customer_id = create_ally_customer(ally_id, customer_name, customer_phone)
            # Crear direccion
            address_id = create_customer_address(
                customer_id,
                "Principal",
                customer_address,
                city=context.user_data.get("customer_city", ""),
                barrio=context.user_data.get("customer_barrio", ""),
                lat=context.user_data.get("dropoff_lat"),
                lng=context.user_data.get("dropoff_lng"),
            )
            ally_id_ctx = context.user_data.get("ally_id")
            parking_enabled_save = get_ally_parking_fee_enabled(ally_id_ctx) if ally_id_ctx else False
            if parking_enabled_save:
                context.user_data["pedido_guardar_parking_address_id"] = address_id
                keyboard = [
                    [InlineKeyboardButton("Si, hay dificultad para parquear", callback_data="pedido_guardar_cust_parking_si")],
                    [InlineKeyboardButton("No / No lo se", callback_data="pedido_guardar_cust_parking_no")],
                ]
                query.edit_message_text(
                    _append_success_followup(
                        success_text,
                        "Cliente '{}' guardado.\n\n"
                        "En ese punto de entrega hay dificultad para parquear moto o bicicleta?\n"
                        "(zona restringida, riesgo de comparendo o sin lugar seguro para dejar el vehiculo)".format(
                            customer_name
                        ),
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return PEDIDO_GUARDAR_CUST_PARKING
            else:
                context.user_data.clear()
                show_main_menu(
                    update,
                    context,
                    _append_success_followup(
                        success_text,
                        "Cliente '{}' guardado para futuros pedidos.".format(customer_name),
                    ),
                )
                return ConversationHandler.END
        except Exception as e:
            context.user_data.clear()
            show_main_menu(
                update,
                context,
                _append_success_followup(success_text, "Error al guardar cliente: {}".format(str(e))),
            )
            return ConversationHandler.END

    elif data == "pedido_guardar_no":
        context.user_data.clear()
        show_main_menu(update, context, success_text)
        return ConversationHandler.END

    return PEDIDO_GUARDAR_CLIENTE


def pedido_dedup_confirm_callback(update, context):
    """Confirma si usar cliente existente encontrado por telefono al crear pedido."""
    query = update.callback_query
    query.answer()
    if query.data == "pedido_dedup_si":
        cust_id = context.user_data.pop("dedup_found_customer_id", None)
        name = context.user_data.pop("dedup_found_name", "")
        phone = context.user_data.get("customer_phone", "")
        context.user_data["customer_id"] = cust_id
        context.user_data["customer_name"] = name
        context.user_data["customer_phone"] = phone
        context.user_data["is_new_customer"] = False
        addrs = list_customer_addresses(cust_id) if cust_id else []
        activas = [a for a in addrs if a["status"] == "ACTIVE"]
        if activas:
            keyboard = []
            for a in activas[:8]:
                text_btn = _pedido_customer_address_button_text(a)
                keyboard.append([InlineKeyboardButton(text_btn, callback_data="pedido_sel_addr_{}".format(a["id"]))])
            keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="pedido_nueva_dir")])
            query.edit_message_text(
                "Cliente: {}\n\nSelecciona la direccion de entrega:".format(name),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return PEDIDO_SELECCIONAR_DIRECCION
        query.edit_message_text(
            "Cliente: {}\n\nEscribe la direccion de entrega o envia un PIN de ubicacion:".format(name)
        )
        return PEDIDO_UBICACION
    else:
        context.user_data.pop("dedup_found_customer_id", None)
        context.user_data.pop("dedup_found_name", None)
        query.edit_message_text("Escribe la direccion de entrega del cliente:")
        return PEDIDO_UBICACION


def pedido_guardar_dir_existente_callback(update, context):
    """Ofrece agregar nueva direccion a cliente ya existente tras crear pedido."""
    query = update.callback_query
    query.answer()
    success_text = context.user_data.get("pedido_success_text", "Pedido creado exitosamente.")
    if query.data == "pedido_guardar_dir_si":
        cust_id = context.user_data.get("guardar_dir_existing_cust_id")
        address = context.user_data.get("customer_address", "")
        city = context.user_data.get("customer_city", "")
        barrio = context.user_data.get("customer_barrio", "")
        lat = context.user_data.get("dropoff_lat")
        lng = context.user_data.get("dropoff_lng")
        label = barrio or city or "Nueva direccion"
        try:
            save_result = upsert_customer_address_for_agenda(
                customer_id=cust_id,
                label=label,
                address_text=address,
                city=city,
                barrio=barrio,
                lat=lat,
                lng=lng,
            )
            if save_result["action"] == "created":
                query.edit_message_text(
                    _append_success_followup(success_text, "Direccion guardada en la agenda del cliente.")
                )
            elif save_result["action"] == "coords_updated":
                query.edit_message_text(
                    _append_success_followup(
                        success_text,
                        "La direccion ya existia y se completo su geolocalizacion.",
                    )
                )
            else:
                query.edit_message_text(
                    _append_success_followup(
                        success_text,
                        "La direccion ya estaba guardada en la agenda del cliente.",
                    )
                )
        except Exception as e:
            query.edit_message_text(
                _append_success_followup(success_text, "No se pudo guardar la direccion: {}".format(e))
            )
    else:
        query.edit_message_text(_append_success_followup(success_text, "OK, no se guardo la direccion."))
    context.user_data.clear()
    show_main_menu(update, context)
    return ConversationHandler.END


def _ally_bandeja_guardar_en_agenda(ally_id, solicitud):
    """
    Guarda cliente y dirección desde solicitud de bandeja con anti-duplicado.
    Retorna (msg_cliente, msg_dir).
    """
    phone = (solicitud["customer_phone"] or "").strip()
    nombre = (solicitud["customer_name"] or "").strip()
    lat = solicitud["lat"]
    lng = solicitud["lng"]
    direccion = (solicitud["delivery_address"] or "").strip()
    city = (solicitud["delivery_city"] or "").strip() or None
    barrio = (solicitud["delivery_barrio"] or "").strip() or None
    tiene_coords = has_valid_coords(lat, lng)

    cliente_existente = get_ally_customer_by_phone(ally_id, phone) if phone else None
    if cliente_existente:
        customer_id = cliente_existente["id"]
        msg_cliente = "Cliente ya existia en agenda."
    else:
        customer_id = create_ally_customer(ally_id, nombre, phone, notes=None)
        msg_cliente = "Cliente nuevo guardado en agenda."

    msg_dir = ""
    if direccion:
        existente = find_matching_customer_address(customer_id, direccion, city=city, barrio=barrio)
        if existente is None:
            create_customer_address(
                customer_id=customer_id,
                label=None,
                address_text=direccion,
                city=city,
                barrio=barrio,
                notes=None,
                lat=lat if tiene_coords else None,
                lng=lng if tiene_coords else None,
                require_coords=False,
            )
            msg_dir = " Direccion nueva guardada{}.".format(" con coordenadas" if tiene_coords else "")
        else:
            addr_id = existente["id"]
            if tiene_coords and not has_valid_coords(existente["lat"], existente["lng"]):
                update_customer_address_coords(addr_id, customer_id, lat, lng)
                msg_dir = " Direccion ya existia; coordenadas completadas."
            else:
                msg_dir = " Direccion ya existia en agenda."

    return msg_cliente, msg_dir


def _pedido_pedir_valor_compra(query_or_update, context, edit=False):
    """
    Pregunta al aliado el valor de compra antes de continuar con el flujo de pedido.
    Se usa cuando la solicitud de bandeja trae purchase_amount_declared.
    Retorna el estado PEDIDO_VALOR_COMPRA.
    """
    suggested = context.user_data.get("pedido_purchase_amount_suggested")
    if suggested is not None:
        msg = (
            "Valor de compra declarado por el cliente: ${:,}\n\n"
            "Envia el valor correcto de la compra en pesos, o 0 si no aplica:"
        ).format(int(suggested))
    else:
        msg = "Envia el valor de la compra en pesos, o 0 si no aplica:"
    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(msg)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(msg)
    else:
        query_or_update.edit_message_text(msg)
    return PEDIDO_VALOR_COMPRA


def pedido_valor_compra_handler(update, context):
    """
    Maneja la respuesta del aliado al valor de compra.
    Acepta: entero >= 0 (en pesos), o vacío/0 para None.
    Luego continúa al flujo normal de pedido.
    """
    text = update.message.text.strip() if update.message.text else ""
    if not text or text == "0":
        context.user_data["pedido_purchase_amount"] = None
    else:
        try:
            val = int(text.replace(",", "").replace(".", "").replace("$", ""))
            if val < 0:
                update.message.reply_text(
                    "El valor no puede ser negativo. Envia el monto en pesos o 0 si no aplica:"
                )
                return PEDIDO_VALOR_COMPRA
            context.user_data["pedido_purchase_amount"] = val
        except ValueError:
            update.message.reply_text(
                "Valor invalido. Envia solo numeros (ej: 50000) o 0 si no aplica:"
            )
            return PEDIDO_VALOR_COMPRA
    if context.user_data.get("customer_address"):
        return mostrar_pregunta_base(update, context, edit=False)
    else:
        update.message.reply_text(
            "Para crear el pedido, indica la direccion de entrega.\n\n"
            "Envia la ubicacion (pin de Telegram) o escribe la direccion:"
        )
        return PEDIDO_UBICACION


def _ally_bandeja_precargar_pedido(context, ally, solicitud, request_id):
    """
    Limpia context.user_data y precarga los datos de la solicitud para el flujo
    de pedido. Pre-carga también el pickup default del aliado.
    """
    context.user_data.clear()
    context.user_data["ally_id"] = ally["id"]
    context.user_data["active_ally_id"] = ally["id"]
    context.user_data["ally"] = ally
    context.user_data["service_type"] = "Entrega"
    context.user_data["is_new_customer"] = True
    context.user_data["bandeja_form_request_id"] = request_id
    context.user_data["customer_name"] = (solicitud["customer_name"] or "").strip()
    context.user_data["customer_phone"] = (solicitud["customer_phone"] or "").strip()
    context.user_data["customer_address"] = (solicitud["delivery_address"] or "").strip()
    context.user_data["customer_city"] = (solicitud["delivery_city"] or "").strip()
    context.user_data["customer_barrio"] = (solicitud["delivery_barrio"] or "").strip()
    if solicitud["notes"]:
        context.user_data["instructions"] = solicitud["notes"].strip()
    if solicitud["purchase_amount_declared"] is not None:
        context.user_data["pedido_purchase_amount_suggested"] = solicitud["purchase_amount_declared"]
    if has_valid_coords(solicitud["lat"], solicitud["lng"]):
        context.user_data["dropoff_lat"] = solicitud["lat"]
        context.user_data["dropoff_lng"] = solicitud["lng"]
    # Pre-cargar pickup default para que aparezca en resumen
    default_loc = get_default_ally_location(ally["id"])
    if default_loc:
        context.user_data["pickup_address"] = default_loc["address"] or ""
        context.user_data["pickup_city"] = default_loc["city"] or ""
        context.user_data["pickup_barrio"] = default_loc["barrio"] or ""
        context.user_data["pickup_lat"] = default_loc["lat"]
        context.user_data["pickup_lng"] = default_loc["lng"]
        if default_loc["id"]:
            context.user_data["pickup_location_id"] = default_loc["id"]


def _ally_bandeja_validar_entrada(query, ally_id, request_id):
    """
    Valida solicitud (ownership + estado procesable).
    Retorna la solicitud si es válida, None si no (y ya editó el mensaje).
    """
    solicitud = get_ally_form_request_by_id(request_id, ally_id)
    if not solicitud:
        query.edit_message_text("Solicitud no encontrada.")
        return None
    if solicitud["status"] not in ("PENDING_REVIEW", "PENDING_LOCATION"):
        query.edit_message_text(
            "Esta solicitud ya fue procesada anteriormente.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
        )
        return None
    return solicitud


def _ally_bandeja_validar_ally_y_saldo(query, update, context):
    """
    Valida que el usuario sea aliado activo con saldo suficiente y términos aceptados.
    Retorna el objeto ally si todo está bien, None si falló (y ya editó el mensaje).
    """
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        query.edit_message_text("No estas registrado. Usa /start primero.")
        return None
    ally = get_ally_by_user_id(db_user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("Tu cuenta de aliado no esta activa.")
        return None
    _admin_link = get_approved_admin_link_for_ally(ally["id"])
    _admin_id = _admin_link["admin_id"] if _admin_link else None
    if not _admin_id:
        _plat = get_platform_admin()
        _admin_id = _plat["id"] if _plat else None
    if _admin_id:
        _fee_ok, _fee_code = check_service_fee_available(
            target_type="ALLY", target_id=ally["id"], admin_id=_admin_id,
        )
        if not _fee_ok:
            if _fee_code == "ADMIN_SIN_SALDO":
                query.edit_message_text("Tu administrador no tiene saldo suficiente para operar.")
            else:
                query.edit_message_text("No tienes saldo suficiente. Recarga para continuar.")
            return None
    if not ensure_terms(update, context, user.id, role="ALLY"):
        return None
    return ally


def ally_bandeja_crear_pedido_entry(update, context):
    """
    Entry point de nuevo_pedido_conv desde la bandeja: precarga datos y entra al flujo.
    Callback: alybandeja_crear_{request_id}
    """
    query = update.callback_query
    query.answer()
    request_id = int(query.data.split("_")[-1])

    ally = _ally_bandeja_validar_ally_y_saldo(query, update, context)
    if not ally:
        return ConversationHandler.END

    solicitud = _ally_bandeja_validar_entrada(query, ally["id"], request_id)
    if not solicitud:
        return ConversationHandler.END

    _ally_bandeja_precargar_pedido(context, ally, solicitud, request_id)

    if context.user_data.get("pedido_purchase_amount_suggested") is not None:
        return _pedido_pedir_valor_compra(query, context, edit=True)

    if context.user_data.get("customer_address"):
        return mostrar_pregunta_base(query, context, edit=True)
    else:
        query.edit_message_text(
            "Para crear el pedido, indica la direccion de entrega.\n\n"
            "Envia la ubicacion (pin de Telegram) o escribe la direccion:"
        )
        return PEDIDO_UBICACION


def ally_bandeja_crear_y_guardar_entry(update, context):
    """
    Entry point de nuevo_pedido_conv desde la bandeja: guarda en agenda y luego crea pedido.
    Callback: alybandeja_crearyguardar_{request_id}
    """
    query = update.callback_query
    query.answer()
    request_id = int(query.data.split("_")[-1])

    ally = _ally_bandeja_validar_ally_y_saldo(query, update, context)
    if not ally:
        return ConversationHandler.END

    solicitud = _ally_bandeja_validar_entrada(query, ally["id"], request_id)
    if not solicitud:
        return ConversationHandler.END

    # 1. Guardar en agenda (anti-duplicado) antes de limpiar user_data
    msg_cliente, msg_dir = _ally_bandeja_guardar_en_agenda(ally["id"], solicitud)
    update_ally_form_request_status(request_id, ally["id"], "SAVED_CONTACT")

    # 2. Notificar resultado del guardado
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Guardado: {}{}\n\nAhora creando el pedido...".format(msg_cliente, msg_dir),
    )

    # 3. Precargar user_data y entrar al flujo de pedido
    _ally_bandeja_precargar_pedido(context, ally, solicitud, request_id)

    if context.user_data.get("pedido_purchase_amount_suggested") is not None:
        return _pedido_pedir_valor_compra(query, context, edit=True)

    if context.user_data.get("customer_address"):
        return mostrar_pregunta_base(query, context, edit=True)
    else:
        query.edit_message_text(
            "Para crear el pedido, indica la direccion de entrega.\n\n"
            "Envia la ubicacion (pin de Telegram) o escribe la direccion:"
        )
        return PEDIDO_UBICACION


def nuevo_pedido_tras_terms(update, context):
    """Continua el flujo de nuevo_pedido tras aceptar terminos y condiciones."""
    query = update.callback_query
    query.answer()
    telegram_id = query.from_user.id

    tv = get_active_terms_version("ALLY")
    if not tv:
        query.edit_message_text("Terminos no configurados. Contacta soporte.")
        return ConversationHandler.END

    version, url, sha256 = tv
    save_terms_acceptance(telegram_id, "ALLY", version, sha256, query.message.message_id)

    db_user = get_user_by_telegram_id(telegram_id)
    if not db_user:
        query.edit_message_text("Error: usuario no encontrado. Usa /nuevo_pedido.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("No se pudo continuar. Usa Nuevo pedido.")
        return ConversationHandler.END

    query.edit_message_text("Aceptacion registrada. Iniciando nuevo pedido...")
    context.user_data.clear()
    context.user_data["ally_id"] = ally["id"]
    context.user_data["active_ally_id"] = ally["id"]
    context.user_data["ally"] = ally

    update.effective_message.reply_text(
        "CREAR NUEVO PEDIDO\n\nSelecciona una opcion:",
        reply_markup=InlineKeyboardMarkup(_build_nuevo_pedido_keyboard(ally["id"]))
    )
    return PEDIDO_SELECTOR_CLIENTE


# Conversacion para /nuevo_pedido (con selector de cliente recurrente)
nuevo_pedido_conv = ConversationHandler(
    entry_points=[
        CommandHandler("nuevo_pedido", nuevo_pedido),
        MessageHandler(Filters.regex(r'^Nuevo pedido$'), nuevo_pedido),
        CallbackQueryHandler(nuevo_pedido_desde_cotizador, pattern=r"^cotizar_cust_(nuevo|recurrente)$"),
        CallbackQueryHandler(nuevo_pedido_tras_terms, pattern=r"^terms_accept_ALLY$"),
        CallbackQueryHandler(ally_bandeja_crear_pedido_entry, pattern=r"^alybandeja_crear_\d+$"),
        CallbackQueryHandler(ally_bandeja_crear_y_guardar_entry, pattern=r"^alybandeja_crearyguardar_\d+$"),
    ],
    states={
        PEDIDO_SELECTOR_CLIENTE: [
            CallbackQueryHandler(pedido_selector_cliente_callback, pattern=r"^pedido_(cliente_recurrente|cliente_nuevo|repetir_ultimo|buscar_cliente|ver_todos|sel_cust_\d+)$")
        ],
        PEDIDO_BUSCAR_CLIENTE: [
            CallbackQueryHandler(pedido_selector_cliente_callback, pattern=r"^pedido_cliente_recurrente$"),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_buscar_cliente)
        ],
        PEDIDO_SELECCIONAR_DIRECCION: [
            CallbackQueryHandler(pedido_seleccionar_direccion_callback, pattern=r"^(pedido_(nueva_dir|sel_addr_\d+)|guardar_dir_cliente_(si|no))$")
        ],
        PEDIDO_INSTRUCCIONES_EXTRA: [
            CallbackQueryHandler(pedido_instrucciones_callback, pattern=r"^pedido_instr_"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_instrucciones_text)
        ],
        PEDIDO_TIPO_SERVICIO: [
            CallbackQueryHandler(pedido_tipo_servicio_callback, pattern=r"^pedido_tipo_"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_tipo_servicio)
        ],
        PEDIDO_COMPRAS_CANTIDAD: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_compras_cantidad_handler)
        ],
        PEDIDO_NOMBRE: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_nombre_cliente)
        ],
        PEDIDO_TELEFONO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_telefono_cliente)
        ],
        PEDIDO_UBICACION: [
            CallbackQueryHandler(pedido_ubicacion_copiar_msg_callback, pattern=r"^ubicacion_copiar_msg_cliente$"),
            CallbackQueryHandler(pedido_reciente_dir_callback, pattern=r"^pedido_reciente_dir_\d+$"),
            CallbackQueryHandler(pedido_nueva_dir_en_ubicacion_callback, pattern=r"^pedido_nueva_dir$"),
            CallbackQueryHandler(pedido_geo_ubicacion_callback, pattern=r"^pedido_geo_"),
            MessageHandler(Filters.location, pedido_ubicacion_location_handler),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_ubicacion_handler)
        ],
        PEDIDO_DIRECCION: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_direccion_cliente)
        ],
        PEDIDO_PICKUP_SELECTOR: [
            CallbackQueryHandler(pedido_pickup_callback, pattern=r"^pickup_select_"),
            CallbackQueryHandler(pedido_pickup_preview_callback, pattern=PICKUP_PREVIEW_CALLBACK_PATTERN),
        ],
        PEDIDO_PICKUP_LISTA: [
            CallbackQueryHandler(pedido_pickup_lista_callback, pattern=r"^pickup_list_")
        ],
        PEDIDO_PICKUP_NUEVA_UBICACION: [
            CallbackQueryHandler(pickup_nueva_copiar_msg_callback, pattern=r"^pickup_copiar_msg_cliente$"),
            CallbackQueryHandler(pedido_pickup_geo_callback, pattern=r"^pickup_geo_"),
            MessageHandler(Filters.location, pedido_pickup_nueva_ubicacion_location_handler),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_pickup_nueva_ubicacion_handler)
        ],
        PEDIDO_PICKUP_NUEVA_DETALLES: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_pickup_nueva_detalles_handler)
        ],
        PEDIDO_PICKUP_NUEVA_CIUDAD: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_pickup_nueva_ciudad_handler),
        ],
        PEDIDO_PICKUP_NUEVA_BARRIO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_pickup_nueva_barrio_handler),
        ],
        PEDIDO_PICKUP_GUARDAR: [
            CallbackQueryHandler(pedido_pickup_guardar_callback, pattern=r"^pickup_guardar_")
        ],
        PEDIDO_VALOR_COMPRA: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_valor_compra_handler),
        ],
        PEDIDO_REQUIERE_BASE: [
            CallbackQueryHandler(pedido_requiere_base_callback, pattern=r"^pedido_base_(si|no)$")
        ],
        PEDIDO_VALOR_BASE: [
            CallbackQueryHandler(pedido_valor_base_callback, pattern=PEDIDO_BASE_CALLBACK_PATTERN),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_valor_base_texto)
        ],
        PEDIDO_CONFIRMACION: [
            CallbackQueryHandler(pedido_edit_instruc_callback, pattern=r"^pedido_edit_instruc$"),
            CallbackQueryHandler(pedido_edit_dir_callback, pattern=r"^pedido_edit_dir$"),
            CallbackQueryHandler(pedido_edit_pickup_callback, pattern=r"^pedido_edit_pickup$"),
            CallbackQueryHandler(pedido_retry_quote_callback, pattern=r"^pedido_retry_quote$"),
            CallbackQueryHandler(pedido_incentivo_fixed_callback, pattern=r"^pedido_inc_(1000|1500|2000|3000)$"),
            CallbackQueryHandler(pedido_incentivo_otro_start, pattern=r"^pedido_inc_otro$"),
            CallbackQueryHandler(pedido_agregar_parada_callback, pattern=r"^pedido_agregar_parada$"),
            CallbackQueryHandler(pedido_confirmacion_callback, pattern=r"^pedido_(confirmar|cancelar)$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_confirmacion)
        ],
        PEDIDO_INCENTIVO_MONTO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_incentivo_monto_handler),
        ],
        PEDIDO_GUARDAR_CLIENTE: [
            CallbackQueryHandler(pedido_guardar_cliente_callback, pattern=r"^pedido_guardar_")
        ],
        PEDIDO_DEDUP_CONFIRM: [
            CallbackQueryHandler(pedido_dedup_confirm_callback, pattern=r"^pedido_dedup_(si|no)$"),
        ],
        PEDIDO_GUARDAR_DIR_EXISTENTE: [
            CallbackQueryHandler(pedido_guardar_dir_existente_callback, pattern=r"^pedido_guardar_dir_(si|no)$"),
        ],
        PEDIDO_PARADA_EXTRA_NOMBRE: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_extra_nombre_handler),
        ],
        PEDIDO_PARADA_EXTRA_TELEFONO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_extra_telefono_handler),
        ],
        PEDIDO_PARADA_EXTRA_DIRECCION: [
            CallbackQueryHandler(pedido_extra_geo_callback, pattern=r"^pedido_extra_geo_(si|no)$"),
            MessageHandler(Filters.location, pedido_extra_gps_handler),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_extra_direccion_handler),
        ],
        PEDIDO_GUARDAR_DIR_PARKING: [
            CallbackQueryHandler(pedido_guardar_dir_parking_callback, pattern=r"^pedido_dir_parking_(si|no)$"),
        ],
        PEDIDO_GUARDAR_CUST_PARKING: [
            CallbackQueryHandler(pedido_guardar_cust_parking_callback, pattern=r"^pedido_guardar_cust_parking_(si|no)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="nuevo_pedido_conv",
    persistent=True,
)


pedido_incentivo_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pedido_incentivo_existing_otro_start, pattern=r"^pedido_inc_otro_\d+$"),
    ],
    states={
        PEDIDO_INCENTIVO_MONTO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_incentivo_existing_monto_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="pedido_incentivo_conv",
    persistent=True,
)

offer_suggest_inc_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(offer_suggest_inc_otro_start, pattern=r"^offer_inc_otro_\d+$"),
    ],
    states={
        OFFER_SUGGEST_INC_MONTO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, offer_suggest_inc_monto_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="offer_suggest_inc_conv",
    persistent=True,
)

route_suggest_inc_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(route_suggest_inc_otro_start, pattern=r"^ruta_inc_otro_\d+$"),
    ],
    states={
        ROUTE_SUGGEST_INC_MONTO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, route_suggest_inc_monto_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="route_suggest_inc_conv",
    persistent=True,
)

# Conversación para crear pedido especial del Admin Local/Plataforma
admin_pedido_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(admin_nuevo_pedido_start, pattern=r"^admin_nuevo_pedido(?:_\d+)?$"),
    ],
    states={
        ADMIN_PEDIDO_PICKUP: [
            CallbackQueryHandler(admin_pedido_usar_plantilla_callback, pattern=r"^admin_pedido_usar_plantilla$"),
            CallbackQueryHandler(admin_pedido_pickup_callback, pattern=r"^admin_pedido_pickup_\d+$"),
            CallbackQueryHandler(admin_pedido_nueva_dir_start, pattern=r"^admin_pedido_nueva_dir$"),
            CallbackQueryHandler(admin_pedido_geo_pickup_callback, pattern=r"^admin_pedido_geo_pickup_(si|no)$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
            MessageHandler(Filters.location, admin_pedido_pickup_gps_handler),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_pickup_text_handler),
        ],
        ADMIN_PEDIDO_PICKUP_DETALLE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_pickup_detalle_handler),
        ],
        ADMIN_PEDIDO_USE_TEMPLATE: [
            CallbackQueryHandler(admin_pedido_tmpl_del_callback, pattern=r"^admin_ped_tmpl_del_\d+$"),
            CallbackQueryHandler(admin_pedido_tmpl_sel_callback, pattern=r"^admin_ped_tmpl_\d+$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
        ],
        ADMIN_PEDIDO_SAVE_PICKUP: [
            CallbackQueryHandler(admin_pedido_save_pickup_callback, pattern=r"^admin_pedido_save_pickup_(si|no)$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
        ],
        ADMIN_PEDIDO_CUST_NAME: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_cust_name_handler),
        ],
        ADMIN_PEDIDO_SEL_CUST: [
            CallbackQueryHandler(admin_pedido_cust_selected, pattern=r"^acust_pedido_sel_\d+$"),
            CallbackQueryHandler(admin_pedido_buscar_cust_start, pattern=r"^admin_pedido_buscar_cust$"),
            CallbackQueryHandler(admin_pedido_ver_todos_callback, pattern=r"^admin_pedido_ver_todos$"),
            CallbackQueryHandler(admin_pedido_cliente_nuevo_callback, pattern=r"^admin_pedido_cliente_nuevo$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
        ],
        ADMIN_PEDIDO_SEL_CUST_ADDR: [
            CallbackQueryHandler(admin_pedido_addr_selected, pattern=r"^acust_pedido_addr_\d+$"),
            CallbackQueryHandler(admin_pedido_addr_nueva, pattern=r"^acust_pedido_addr_nueva$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
        ],
        ADMIN_PEDIDO_CUST_PHONE: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_cust_phone_handler),
        ],
        ADMIN_PEDIDO_CUST_ADDR: [
            CallbackQueryHandler(admin_pedido_geo_callback, pattern=r"^admin_pedido_geo_(si|no)$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
            MessageHandler(Filters.location, admin_pedido_cust_gps_handler),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_cust_addr_handler),
        ],
        ADMIN_PEDIDO_CUST_ADDR_DETALLE: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_cust_addr_detalle_handler),
        ],
        PEDIDO_REQUIERE_BASE: [
            CallbackQueryHandler(pedido_requiere_base_callback, pattern=r"^pedido_base_(si|no)$"),
        ],
        PEDIDO_VALOR_BASE: [
            CallbackQueryHandler(pedido_valor_base_callback, pattern=PEDIDO_BASE_CALLBACK_PATTERN),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_valor_base_texto),
        ],
        ADMIN_PEDIDO_TARIFA: [
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_tarifa_handler),
        ],
        ADMIN_PEDIDO_COMISION: [
            CallbackQueryHandler(admin_pedido_sin_comision_callback, pattern=r"^admin_pedido_sin_comision$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_comision_handler),
        ],
        ADMIN_PEDIDO_INSTRUC: [
            CallbackQueryHandler(admin_pedido_sin_instruc_callback, pattern=r"^admin_pedido_sin_instruc$"),
            CallbackQueryHandler(admin_pedido_inc_fijo_callback, pattern=r"^admin_pedido_inc_(1000|1500|2000|3000)$"),
            CallbackQueryHandler(admin_pedido_inc_otro_callback, pattern=r"^admin_pedido_inc_otro$"),
            CallbackQueryHandler(admin_pedido_team_toggle_callback, pattern=r"^admin_pedido_team_toggle$"),
            CallbackQueryHandler(admin_pedido_guardar_plantilla_callback, pattern=r"^admin_pedido_guardar_plantilla$"),
            CallbackQueryHandler(admin_pedido_edit_pickup_callback, pattern=r"^admin_pedido_edit_pickup$"),
            CallbackQueryHandler(admin_pedido_edit_cust_callback, pattern=r"^admin_pedido_edit_cust$"),
            CallbackQueryHandler(admin_pedido_edit_tarifa_callback, pattern=r"^admin_pedido_edit_tarifa$"),
            CallbackQueryHandler(admin_pedido_confirmar_callback, pattern=r"^admin_pedido_confirmar$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_instruc_handler),
        ],
        ADMIN_PEDIDO_TEMPLATE_NAME: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_template_name_handler),
        ],
        ADMIN_PEDIDO_INC_MONTO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_inc_monto_handler),
        ],
        ADMIN_PEDIDO_SEL_CUST_BUSCAR: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, admin_pedido_buscar_cust_handler),
        ],
        ADMIN_PEDIDO_CUST_DEDUP: [
            CallbackQueryHandler(admin_pedido_cust_dedup_callback, pattern=r"^admin_ped_dedup_(si|no)$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
        ],
        ADMIN_PEDIDO_GUARDAR_CUST: [
            CallbackQueryHandler(admin_pedido_guardar_cust_callback, pattern=r"^admin_ped_guardar_(cust|dir)_(si|no)$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
        ],
        ADMIN_PEDIDO_GUARDAR_PARKING: [
            CallbackQueryHandler(admin_pedido_guardar_parking_callback, pattern=r"^admin_ped_guardar_parking_(si|no)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="admin_pedido_conv",
    persistent=True,
)

