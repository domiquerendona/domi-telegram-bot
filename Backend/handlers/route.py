# =============================================================================
# handlers/route.py — Flujo de nueva ruta multi-parada
# Extraído de main.py
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
    PEDIDO_REQUIERE_BASE,
    PEDIDO_VALOR_BASE,
    RUTA_PICKUP_SELECTOR,
    RUTA_PICKUP_LISTA,
    RUTA_PICKUP_NUEVA_UBICACION,
    RUTA_PICKUP_NUEVA_DETALLES,
    RUTA_PICKUP_GUARDAR,
    RUTA_PARADA_SELECTOR,
    RUTA_PARADA_SEL_DIRECCION,
    RUTA_PARADA_NOMBRE,
    RUTA_PARADA_TELEFONO,
    RUTA_PARADA_UBICACION,
    RUTA_PARADA_DIRECCION,
    RUTA_MAS_PARADAS,
    RUTA_DISTANCIA_KM,
    RUTA_CONFIRMACION,
    RUTA_GUARDAR_CLIENTES,
    RUTA_PICKUP_NUEVA_CIUDAD,
    RUTA_PICKUP_NUEVA_BARRIO,
    RUTA_INCENTIVO_MONTO,
    RUTA_PARADA_BUSCAR,
    RUTA_PARADA_DEDUP,
    RUTA_GUARDAR_CUST_PARKING,
)
from handlers.order import (
    mostrar_pregunta_base,
    pedido_requiere_base_callback,
    pedido_valor_base_callback,
    pedido_valor_base_texto,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER,
    _OPTIONS_HINT,
    _fmt_pesos,
    build_offer_demand_badge_text,
    build_offer_suggestion_button_row,
    _geo_siguiente_o_gps,
    _handle_text_field_input,
    _maybe_cache_confirmed_geo,
    _mostrar_confirmacion_geocode,
    cancel_conversacion,
    cancel_por_texto,
    show_main_menu,
    show_flow_menu,
)
from services import (
    ensure_user,
    get_user_by_telegram_id,
    get_ally_by_user_id,
    get_ally_locations,
    get_ally_location_by_id,
    get_default_ally_location,
    create_ally_location,
    list_ally_customers,
    search_ally_customers,
    get_ally_customer_by_id,
    list_customer_addresses,
    get_customer_address_by_id,
    get_ally_customer_by_phone,
    create_ally_customer,
    find_matching_customer_address,
    upsert_customer_address_for_agenda,
    increment_ally_customer_usage, increment_customer_address_usage,
    has_valid_coords,
    resolve_location,
    extract_lat_lng_from_text,
    expand_short_url,
    calcular_precio_ruta,
    calcular_precio_ruta_inteligente,
    calcular_distancia_ruta_smart,
    optimizar_orden_paradas,
    create_route,
    create_route_destination,
    get_approved_admin_link_for_ally,
    get_ally_link_balance,
    add_route_incentive,
    set_address_parking_status,
    PARKING_FEE_AMOUNT,
    get_ally_parking_fee_enabled,
    build_offer_demand_preview,
    get_route_by_id,
)
from order_delivery import (
    publish_route_to_couriers,
    build_market_launch_status_text,
    build_courier_route_preview_text,
    build_route_creation_summary_text,
)


def _route_city_hint(context):
    """Extrae barrio+ciudad del aliado en sesion para mejorar geocoding de rutas."""
    ally = context.user_data.get("ally")
    if ally:
        parts = [p for p in [ally.get("barrio"), ally.get("city")] if p]
        if parts:
            return ", ".join(parts)
    return None


def _ruta_no_more_text(point_label: str):
    return (
        "No encontre mas opciones para {}.\n\n"
        "Envia otra ubicacion para continuar:\n"
        "- Un PIN de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Nombre del lugar o barrio con ciudad"
    ).format(point_label)


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
            if loc["lat"] == pickup_lat and loc["lng"] == pickup_lng:
                pickup_address = loc["address"] or ""
                pickup_location_id = loc["id"]
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


# ======================================================
# FLUJO NUEVA RUTA (multi-parada)
# ======================================================

def _ruta_limpiar_temp(context):
    """Limpia datos temporales de la parada actual."""
    for k in ["ruta_temp_name", "ruta_temp_phone", "ruta_temp_address",
              "ruta_temp_city", "ruta_temp_barrio", "ruta_temp_lat", "ruta_temp_lng",
              "ruta_temp_customer_id", "ruta_temp_parking_fee",
              "ruta_parada_geo_city", "ruta_parada_geo_barrio"]:
        context.user_data.pop(k, None)


def _ruta_mostrar_selector_pickup(update_or_query, context):
    """Muestra el selector de punto de recogida para la ruta."""
    ally_id = context.user_data.get("ruta_ally_id")
    keyboard = []
    if ally_id:
        locations = get_ally_locations(ally_id)
        default_loc = next((l for l in locations if l["is_default"]), None)
        if default_loc:
            label = (default_loc["label"] or "Base")[:20]
            address = (default_loc["address"] or "")[:30]
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
    context.user_data["ruta_pickup_location_id"] = location["id"]
    context.user_data["ruta_pickup_address"] = location["address"] or ""
    context.user_data["ruta_pickup_lat"] = location["lat"]
    context.user_data["ruta_pickup_lng"] = location["lng"]


def _ruta_iniciar_parada(update_or_query, context):
    """Muestra el selector de cliente para la proxima parada."""
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    ally_id = context.user_data.get("ruta_ally_id")
    all_clientes = list_ally_customers(ally_id, limit=50) if ally_id else []
    keyboard = [[InlineKeyboardButton("Cliente nuevo", callback_data="ruta_cliente_nuevo")]]
    for c in all_clientes[:10]:
        nombre = (c["name"] or "Sin nombre")[:25]
        phone = c["phone"] or ""
        keyboard.append([InlineKeyboardButton(
            "{} - {}".format(nombre, phone),
            callback_data="ruta_sel_cust_{}".format(c["id"])
        )])
    if all_clientes:
        keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="ruta_buscar_cliente")])
        if len(all_clientes) > 10:
            keyboard.append([InlineKeyboardButton(
                "Ver todos ({})".format(len(all_clientes)), callback_data="ruta_ver_todos"
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
        "customer_id": context.user_data.get("ruta_temp_customer_id"),
        "parking_fee": int(context.user_data.get("ruta_temp_parking_fee") or 0),
    }
    paradas = context.user_data.get("ruta_paradas", [])
    paradas.append(parada)
    context.user_data["ruta_paradas"] = paradas
    _ruta_limpiar_temp(context)


def _ruta_guardar_parada_y_cliente(context, msg_or_query):
    """Guarda la parada. Si es cliente nuevo, pregunta si guardarlo en agenda."""
    customer_id = context.user_data.get("ruta_temp_customer_id")
    name = context.user_data.get("ruta_temp_name") or ""
    phone = context.user_data.get("ruta_temp_phone") or ""
    address = context.user_data.get("ruta_temp_address") or ""
    city = context.user_data.get("ruta_temp_city") or ""
    barrio = context.user_data.get("ruta_temp_barrio") or ""
    lat = context.user_data.get("ruta_temp_lat")
    lng = context.user_data.get("ruta_temp_lng")

    _ruta_guardar_parada_actual(context)

    # Si es cliente nuevo (sin customer_id), preguntar si guardar en agenda
    if not customer_id and phone:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Si, guardar", callback_data="ruta_guardar_cust_si")],
            [InlineKeyboardButton("No", callback_data="ruta_guardar_cust_no")],
        ])
        text = "Deseas guardar a {} ({}) en tu agenda de clientes?".format(name, phone)
        if hasattr(msg_or_query, "edit_message_text"):
            msg_or_query.edit_message_text(text, reply_markup=keyboard)
        else:
            msg_or_query.message.reply_text(text, reply_markup=keyboard)
        return RUTA_GUARDAR_CLIENTES

    if customer_id and address:
        existing_address = find_matching_customer_address(
            customer_id,
            address,
            city=city,
            barrio=barrio,
        )
        if existing_address:
            if has_valid_coords(lat, lng) and not has_valid_coords(existing_address.get("lat"), existing_address.get("lng")):
                upsert_customer_address_for_agenda(
                    customer_id=customer_id,
                    label=existing_address.get("label") or barrio or city or "Principal",
                    address_text=address,
                    city=city,
                    barrio=barrio,
                    notes=existing_address.get("notes"),
                    lat=lat,
                    lng=lng,
                )
            return _ruta_mostrar_mas_paradas(msg_or_query, context)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Si, guardar", callback_data="ruta_guardar_cust_si")],
            [InlineKeyboardButton("No", callback_data="ruta_guardar_cust_no")],
        ])
        text = "Deseas guardar esta direccion para futuros pedidos de {}?".format(name or "este cliente")
        if hasattr(msg_or_query, "edit_message_text"):
            msg_or_query.edit_message_text(text, reply_markup=keyboard)
        else:
            msg_or_query.message.reply_text(text, reply_markup=keyboard)
        return RUTA_GUARDAR_CLIENTES

    return _ruta_mostrar_mas_paradas(msg_or_query, context)


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


def _ruta_incentivo_keyboard():
    """Botones de incentivo pre-confirmacion para ruta."""
    return [
        [
            InlineKeyboardButton("+1000", callback_data="ruta_inc_1000"),
            InlineKeyboardButton("+1500", callback_data="ruta_inc_1500"),
        ],
        [
            InlineKeyboardButton("+2000", callback_data="ruta_inc_2000"),
            InlineKeyboardButton("+3000", callback_data="ruta_inc_3000"),
        ],
        [InlineKeyboardButton("Otro monto", callback_data="ruta_inc_otro")],
    ]


def _ruta_continue_after_base(update_or_query, context, edit=False):
    """Retoma la ruta una vez se confirmo si requiere base."""
    paradas = context.user_data.get("ruta_paradas", [])
    pickup_lat = context.user_data.get("ruta_pickup_lat")
    pickup_lng = context.user_data.get("ruta_pickup_lng")
    tiene_gps = (
        pickup_lat is not None and pickup_lng is not None
        and all(p.get("lat") is not None and p.get("lng") is not None for p in paradas)
    )
    if tiene_gps:
        if edit and hasattr(update_or_query, "edit_message_text"):
            update_or_query.edit_message_text("Calculando distancia de la ruta...")
        elif hasattr(update_or_query, "message") and update_or_query.message:
            update_or_query.message.reply_text("Calculando distancia de la ruta...")
        dist_result = calcular_distancia_ruta_smart(pickup_lat, pickup_lng, paradas)
        if dist_result and dist_result["total_km"] > 0:
            context.user_data["ruta_distancia_km"] = dist_result["total_km"]
            context.user_data["ruta_distancia_estimada"] = dist_result.get("estimada", False)
            return _ruta_mostrar_confirmacion(update_or_query, context)
    if edit and hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(
            "DISTANCIA DE LA RUTA\n\n"
            "No tengo GPS de todas las paradas para calcular automaticamente.\n"
            "Ingresa la distancia total de la ruta en km.\n\nEjemplo: 10.5"
        )
    elif hasattr(update_or_query, "message") and update_or_query.message:
        update_or_query.message.reply_text(
            "DISTANCIA DE LA RUTA\n\n"
            "No tengo GPS de todas las paradas para calcular automaticamente.\n"
            "Ingresa la distancia total de la ruta en km.\n\nEjemplo: 10.5"
        )
    return RUTA_DISTANCIA_KM


def _ruta_mostrar_confirmacion(update_or_query, context):
    """Muestra el resumen de la ruta con precio desglosado y orden optimizado."""
    paradas = context.user_data.get("ruta_paradas", [])
    pickup_address = context.user_data.get("ruta_pickup_address", "No definida")
    pickup_lat = context.user_data.get("ruta_pickup_lat")
    pickup_lng = context.user_data.get("ruta_pickup_lng")

    # Optimizar orden de paradas (TSP Haversine, sin costo de API)
    paradas_opt, distancia_opt, fue_optimizado = optimizar_orden_paradas(
        pickup_lat, pickup_lng, paradas
    )
    if fue_optimizado:
        context.user_data["ruta_paradas"] = paradas_opt
        paradas = paradas_opt

    # Usar distancia calculada en el flujo (smart/haversine) o la del TSP como fallback
    total_km = context.user_data.get("ruta_distancia_km") or distancia_opt or 0

    precio_info = calcular_precio_ruta_inteligente(
        total_km, paradas, pickup_lat=pickup_lat, pickup_lng=pickup_lng
    )
    distance_fee = precio_info["distance_fee"]
    additional_fee = precio_info["additional_stops_fee"]
    stop_fee = precio_info.get("tarifa_parada_adicional", 0)
    mensaje_ahorro = precio_info.get("mensaje_ahorro", "")
    # Sumar parking fees al total_fee antes de almacenar en user_data
    total_parking_fee = sum(int(p.get("parking_fee") or 0) for p in paradas)
    if total_parking_fee > 0:
        precio_info["total_fee"] += total_parking_fee
    total_fee = precio_info["total_fee"]
    context.user_data["ruta_precio"] = precio_info

    distancia_estimada = context.user_data.get("ruta_distancia_estimada", False)
    requires_cash = bool(context.user_data.get("ruta_requires_cash"))
    cash_required_amount = int(context.user_data.get("ruta_cash_required_amount") or 0)

    text = "RUTA DE ENTREGA\n"
    if fue_optimizado:
        text += "(Orden optimizado para menor distancia)\n"
    if distancia_estimada:
        text += "(Distancia aproximada — sin datos de carretera exactos)\n"
    text += "\nRecoge en: {}\n\n".format(pickup_address)
    for i, p in enumerate(paradas, 1):
        p_parking = int(p.get("parking_fee") or 0)
        parking_line = "  Parqueo dificil: +${:,}\n".format(p_parking) if p_parking > 0 else ""
        text += "Parada {}:\n  Cliente: {} - {}\n  Direccion: {}\n{}".format(
            i, p.get("name") or "Sin nombre", p.get("phone") or "", p.get("address") or "Sin direccion",
            parking_line
        )
    text += "\nDistancia total: {:.1f} km{}\n".format(
        total_km, " (aprox)" if distancia_estimada else ""
    )
    text += "Precio base (distancia): ${:,}\n".format(distance_fee)
    if additional_fee > 0:
        text += "Paradas adicionales ({} x ${:,}): ${:,}\n".format(len(paradas) - 1, stop_fee, additional_fee)
    if total_parking_fee > 0:
        text += "Puntos con parqueo dificil: +${:,}\n".format(total_parking_fee)
    text += "TOTAL: ${:,}".format(total_fee)
    if mensaje_ahorro:
        text += "\n{}".format(mensaje_ahorro)
    incentivo = int(context.user_data.get("ruta_incentivo", 0) or 0)
    if incentivo > 0:
        text += "\nIncentivo adicional: +${:,}".format(incentivo)
    if requires_cash and cash_required_amount > 0:
        text += "\nBase requerida: ${:,}".format(cash_required_amount)
    demand_preview = build_offer_demand_preview(
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        distance_km=total_km,
        ally_id=context.user_data.get("ruta_ally_id"),
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
    text += "\n\n{}".format(
        build_courier_route_preview_text(
            {
                "id": "preview",
                "pickup_address": pickup_address,
                "pickup_city": context.user_data.get("ruta_pickup_city") or "",
                "pickup_barrio": context.user_data.get("ruta_pickup_barrio") or "",
                "total_distance_km": total_km,
                "total_fee": total_fee,
                "additional_incentive": incentivo,
                "requires_cash": requires_cash,
                "cash_required_amount": cash_required_amount,
            },
            [
                {
                    "sequence": i,
                    "customer_address": p.get("address") or "",
                    "customer_city": p.get("city") or "",
                    "customer_barrio": p.get("barrio") or "",
                    "parking_fee": int(p.get("parking_fee") or 0),
                }
                for i, p in enumerate(paradas, 1)
            ],
        )
    )
    keyboard = _ruta_incentivo_keyboard()
    suggested_row = build_offer_suggestion_button_row(
        demand_preview,
        "ruta_inc_{amount}",
        allowed_amounts=(1000, 1500, 2000, 3000),
    )
    if suggested_row:
        keyboard.insert(0, suggested_row)
    keyboard += [
        [InlineKeyboardButton("Cambiar recogida", callback_data="ruta_edit_pickup")],
        [InlineKeyboardButton("Confirmar ruta", callback_data="ruta_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="ruta_cancelar")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(text, reply_markup=markup)
    else:
        update_or_query.message.reply_text(text, reply_markup=markup)
    return RUTA_CONFIRMACION


def ruta_edit_pickup_callback(update, context):
    """Desde el preview de ruta: volver a seleccionar punto de recogida."""
    query = update.callback_query
    query.answer()
    context.user_data["ruta_edit_from_preview"] = True
    return _ruta_mostrar_selector_pickup(query, context)


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
        if not default_loc or not default_loc["lat"]:
            query.edit_message_text("Tu ubicacion base no tiene GPS. Elige otra.")
            return _ruta_mostrar_selector_pickup(query, context)
        _ruta_guardar_pickup(context, default_loc)
        if context.user_data.pop("ruta_edit_from_preview", False):
            return _ruta_mostrar_confirmacion(query, context)
        return _ruta_iniciar_parada(query, context)
    if data == "ruta_pickup_lista":
        locations = get_ally_locations(ally_id)
        if not locations:
            query.edit_message_text("No tienes ubicaciones guardadas.")
            return _ruta_mostrar_selector_pickup(query, context)
        keyboard = []
        for loc in locations[:8]:
            label = (loc["label"] or "Sin nombre")[:20]
            address = (loc["address"] or "")[:25]
            sin_gps = " (sin GPS)" if not loc["lat"] else ""
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
        if not location or not location["lat"]:
            query.edit_message_text("Esa ubicacion no tiene GPS. Elige otra.")
            return RUTA_PICKUP_LISTA
        _ruta_guardar_pickup(context, location)
        if context.user_data.pop("ruta_edit_from_preview", False):
            return _ruta_mostrar_confirmacion(query, context)
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
        context.user_data["ruta_pickup_location_id"] = None
        context.user_data.pop("ruta_pickup_geo_formatted", None)
        _mostrar_confirmacion_geocode(
            update.message,
            context,
            {"lat": coords[0], "lng": coords[1]},
            text,
            "ruta_pickup_geo_si",
            "ruta_pickup_geo_no",
            header_text="Confirma el punto exacto de recogida antes de continuar.",
            question_text="Es esta la ubicacion de recogida correcta?",
        )
        return RUTA_PICKUP_NUEVA_UBICACION
    _hint = _route_city_hint(context)
    geo = resolve_location(text, city_hint=_hint)
    if geo and geo.get("lat") is not None and geo.get("lng") is not None:
        context.user_data["pending_geo_city_hint"] = _hint
        context.user_data["ruta_pickup_location_id"] = None
        _mostrar_confirmacion_geocode(
            update.message,
            context,
            geo,
            text,
            "ruta_pickup_geo_si", "ruta_pickup_geo_no",
            header_text="Confirma el punto exacto de recogida antes de continuar.",
            question_text="Es esta la ubicacion de recogida correcta?",
            formatted_storage_key="ruta_pickup_geo_formatted",
        )
        return RUTA_PICKUP_NUEVA_UBICACION
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
        _maybe_cache_confirmed_geo(context)
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        formatted = context.user_data.pop("ruta_pickup_geo_formatted", "")
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return RUTA_PICKUP_NUEVA_UBICACION
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
        query,
        context,
        "ruta_pickup_geo_si",
        "ruta_pickup_geo_no",
        RUTA_PICKUP_NUEVA_UBICACION,
        header_text="Confirma el punto exacto de recogida antes de continuar.",
        question_text="Es esta la ubicacion de recogida correcta?",
        no_more_text=_ruta_no_more_text("la recogida"),
        formatted_storage_key="ruta_pickup_geo_formatted",
    )


def ruta_pickup_nueva_ubicacion_location_handler(update, context):
    loc = update.message.location
    context.user_data["ruta_pickup_location_id"] = None
    context.user_data.pop("ruta_pickup_geo_formatted", None)
    _mostrar_confirmacion_geocode(
        update.message,
        context,
        {
            "lat": loc.latitude,
            "lng": loc.longitude,
            "formatted_address": "Ubicacion enviada desde Telegram.",
        },
        "",
        "ruta_pickup_geo_si",
        "ruta_pickup_geo_no",
        header_text="Confirma el punto exacto de recogida antes de continuar.",
        question_text="Es esta la ubicacion de recogida correcta?",
    )
    return RUTA_PICKUP_NUEVA_UBICACION


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
    if context.user_data.pop("ruta_edit_from_preview", False):
        return _ruta_mostrar_confirmacion(query, context)
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
    if data == "ruta_buscar_cliente":
        query.edit_message_text(
            "Escribe el nombre o telefono del cliente.\nEscribe '.' para ver todos:"
        )
        return RUTA_PARADA_BUSCAR
    if data == "ruta_ver_todos":
        all_clientes = list_ally_customers(ally_id, limit=50) if ally_id else []
        sorted_clientes = sorted(all_clientes, key=lambda c: (c["name"] or "").lower())
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        kb = [[InlineKeyboardButton("Cliente nuevo", callback_data="ruta_cliente_nuevo")]]
        for c in sorted_clientes:
            nombre = (c["name"] or "Sin nombre")[:25]
            phone = c["phone"] or ""
            kb.append([InlineKeyboardButton(
                "{} - {}".format(nombre, phone),
                callback_data="ruta_sel_cust_{}".format(c["id"])
            )])
        kb.append([InlineKeyboardButton("Buscar cliente", callback_data="ruta_buscar_cliente")])
        query.edit_message_text(
            "PARADA {} - TODOS LOS CLIENTES ({})\n\nSelecciona el cliente:".format(n, len(sorted_clientes)),
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return RUTA_PARADA_SELECTOR
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
        context.user_data["ruta_temp_name"] = customer["name"] or ""
        context.user_data["ruta_temp_phone"] = customer["phone"] or ""
        addresses = list_customer_addresses(cust_id)
        activas = [a for a in addresses if a["status"] == "ACTIVE"]
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        if not activas:
            query.edit_message_text(
                "PARADA {} - {}\n\nNo tiene direcciones guardadas.\n\n"
                "Escribe la direccion de entrega, o envia un PIN de Telegram, "
                "link de Google Maps o coordenadas.".format(
                    n, customer["name"] or "Cliente"
                )
            )
            return RUTA_PARADA_UBICACION
        keyboard = []
        for addr in activas[:6]:
            parking_status = addr["parking_status"] if "parking_status" in addr.keys() else "NOT_ASKED"
            parking_tag = " [P]" if parking_status in ("ALLY_YES", "ADMIN_YES") else ""
            label = (addr["label"] or addr["address_text"] or "Direccion")[:28] + parking_tag
            keyboard.append([InlineKeyboardButton(label, callback_data="ruta_sel_addr_{}".format(addr["id"]))])
        keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="ruta_addr_nueva")])
        query.edit_message_text(
            "PARADA {} - {}\n\nSelecciona la direccion de entrega:".format(n, customer["name"] or "Cliente"),
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
        query.edit_message_text(
            "PARADA {}\n\nEscribe la direccion de entrega, o envia un PIN de Telegram, "
            "link de Google Maps o coordenadas.".format(n)
        )
        return RUTA_PARADA_UBICACION
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
        if not has_valid_coords(addr["lat"], addr["lng"]):
            query.edit_message_text(
                "Esta direccion guardada no tiene ubicacion confirmada.\n\n"
                "Envia ahora la ubicacion GPS de la parada."
            )
            return RUTA_PARADA_UBICACION
        context.user_data["ruta_temp_address"] = addr["address_text"] or ""
        context.user_data["ruta_temp_city"] = addr["city"] or ""
        context.user_data["ruta_temp_barrio"] = addr["barrio"] or ""
        context.user_data["ruta_temp_lat"] = addr["lat"]
        context.user_data["ruta_temp_lng"] = addr["lng"]
        ally_id_ctx = context.user_data.get("ruta_ally_id")
        parking_enabled_ctx = get_ally_parking_fee_enabled(ally_id_ctx) if ally_id_ctx else False
        if parking_enabled_ctx:
            try:
                parking_status = addr["parking_status"]
            except (KeyError, IndexError):
                parking_status = "NOT_ASKED"
            context.user_data["ruta_temp_parking_fee"] = PARKING_FEE_AMOUNT if parking_status in ("ALLY_YES", "ADMIN_YES") else 0
        else:
            context.user_data["ruta_temp_parking_fee"] = 0
        try:
            increment_customer_address_usage(addr_id, cust_id)
            increment_ally_customer_usage(cust_id)
        except Exception:
            pass
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
    ally_id = context.user_data.get("ruta_ally_id")
    # Dedup: verificar si ya existe un cliente con este telefono
    existing = get_ally_customer_by_phone(ally_id, digits) if ally_id else None
    if existing:
        context.user_data["ruta_dedup_found"] = {"id": existing["id"], "name": existing["name"] or ""}
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Si, usar este cliente", callback_data="ruta_dedup_si")],
            [InlineKeyboardButton("No, es otro cliente", callback_data="ruta_dedup_no")],
        ])
        update.message.reply_text(
            "Este numero ya esta en tu agenda: {}\n\n"
            "Usar este cliente para la parada?".format(existing.get("name") or digits),
            reply_markup=keyboard,
        )
        return RUTA_PARADA_DEDUP
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
        context.user_data.pop("ruta_parada_geo_formatted", None)
        _mostrar_confirmacion_geocode(
            update.message,
            context,
            {"lat": coords[0], "lng": coords[1]},
            text,
            "ruta_parada_geo_si",
            "ruta_parada_geo_no",
            header_text="Confirma el punto exacto de la parada antes de continuar.",
            question_text="Es esta la ubicacion de entrega correcta?",
        )
        return RUTA_PARADA_UBICACION
    _hint = _route_city_hint(context)
    geo = resolve_location(text, city_hint=_hint)
    if geo and geo.get("lat") is not None and geo.get("lng") is not None:
        context.user_data["pending_geo_city_hint"] = _hint
        context.user_data["ruta_parada_geo_city"] = geo.get("city") or ""
        context.user_data["ruta_parada_geo_barrio"] = geo.get("barrio") or ""
        _mostrar_confirmacion_geocode(
            update.message,
            context,
            geo,
            text,
            "ruta_parada_geo_si", "ruta_parada_geo_no",
            header_text="Confirma el punto exacto de la parada antes de continuar.",
            question_text="Es esta la ubicacion de entrega correcta?",
            formatted_storage_key="ruta_parada_geo_formatted",
        )
        return RUTA_PARADA_UBICACION
    update.message.reply_text(
        "No pude encontrar esa ubicacion.\n\n"
        "Intenta con:\n"
        "- Un PIN de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Nombre del lugar o barrio con ciudad"
    )
    return RUTA_PARADA_UBICACION


def ruta_parada_geo_callback(update, context):
    """Confirmacion de geocoding para la ubicacion de una parada de la ruta."""
    query = update.callback_query
    query.answer()
    if query.data == "ruta_parada_geo_si":
        _maybe_cache_confirmed_geo(context)
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        formatted = context.user_data.pop("ruta_parada_geo_formatted", "")
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return RUTA_PARADA_UBICACION
        context.user_data["ruta_temp_lat"] = lat
        context.user_data["ruta_temp_lng"] = lng
        context.user_data["ruta_temp_city"] = context.user_data.pop("ruta_parada_geo_city", "")
        context.user_data["ruta_temp_barrio"] = context.user_data.pop("ruta_parada_geo_barrio", "")
        if formatted:
            context.user_data["ruta_temp_address"] = formatted
            return _ruta_guardar_parada_y_cliente(context, query)
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text("PARADA {}\n\nEscribe la descripcion de la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    return _geo_siguiente_o_gps(
        query,
        context,
        "ruta_parada_geo_si",
        "ruta_parada_geo_no",
        RUTA_PARADA_UBICACION,
        header_text="Confirma el punto exacto de la parada antes de continuar.",
        question_text="Es esta la ubicacion de entrega correcta?",
        no_more_text=_ruta_no_more_text("la parada"),
        formatted_storage_key="ruta_parada_geo_formatted",
    )


def ruta_parada_ubicacion_location_handler(update, context):
    loc = update.message.location
    context.user_data.pop("ruta_parada_geo_formatted", None)
    _mostrar_confirmacion_geocode(
        update.message,
        context,
        {
            "lat": loc.latitude,
            "lng": loc.longitude,
            "formatted_address": "Ubicacion enviada desde Telegram.",
        },
        "",
        "ruta_parada_geo_si",
        "ruta_parada_geo_no",
        header_text="Confirma el punto exacto de la parada antes de continuar.",
        question_text="Es esta la ubicacion de entrega correcta?",
    )
    return RUTA_PARADA_UBICACION


def ruta_parada_direccion_handler(update, context):
    address = update.message.text.strip()
    if not address:
        update.message.reply_text("Escribe la direccion de entrega.")
        return RUTA_PARADA_DIRECCION
    context.user_data["ruta_temp_address"] = address
    return _ruta_guardar_parada_y_cliente(context, update)



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
        logger.info(
            "[requires_cash_unified_v2026_04_09] flow=route action=ask_base stops=%s",
            len(paradas),
        )
        return mostrar_pregunta_base(query, context, edit=True)
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


def ruta_inc_fijo_callback(update, context):
    """Agrega incentivo fijo (+1000/+1500/+2000/+3000) antes de confirmar ruta."""
    query = update.callback_query
    query.answer()
    data = query.data  # "ruta_inc_1500" etc
    parts = data.split("_")
    try:
        delta = int(parts[-1])
    except Exception:
        return RUTA_CONFIRMACION
    if delta <= 0:
        return RUTA_CONFIRMACION
    current = int(context.user_data.get("ruta_incentivo", 0) or 0)
    context.user_data["ruta_incentivo"] = current + delta
    return _ruta_mostrar_confirmacion(query, context)


def ruta_inc_otro_start(update, context):
    """Pide al aliado ingresar un incentivo adicional por texto (antes de confirmar ruta)."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "Escribe el incentivo adicional en pesos (solo numeros).\n"
        "Ejemplo: 2500\n\n"
        "Escribe 'cancelar' para volver al menu."
    )
    return RUTA_INCENTIVO_MONTO


def ruta_inc_monto_handler(update, context):
    """Recibe incentivo adicional por texto antes de confirmar ruta."""
    text = (update.message.text or "").strip()
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return RUTA_INCENTIVO_MONTO
    try:
        delta = int(digits)
    except Exception:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return RUTA_INCENTIVO_MONTO
    if delta <= 0:
        update.message.reply_text("El monto debe ser mayor a 0.")
        return RUTA_INCENTIVO_MONTO
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto.")
        return RUTA_INCENTIVO_MONTO
    current = int(context.user_data.get("ruta_incentivo", 0) or 0)
    context.user_data["ruta_incentivo"] = current + delta
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
    requires_cash = bool(context.user_data.get("ruta_requires_cash"))
    cash_required_amount = int(context.user_data.get("ruta_cash_required_amount") or 0)
    if not has_valid_coords(pickup_lat, pickup_lng) or any(
        not has_valid_coords(parada.get("lat"), parada.get("lng")) for parada in paradas
    ):
        query.edit_message_text(
            "La ruta requiere GPS confirmado en recogida y en todas las paradas antes de crearse."
        )
        return RUTA_CONFIRMACION
    link = get_approved_admin_link_for_ally(ally_id)
    admin_id_snapshot = link["admin_id"] if link else None
    # Validar saldo suficiente para el fee completo de la ruta:
    # $300 base (mismo que pedido individual) + $200 por cada parada adicional
    n_paradas = len(paradas)
    fee_total_aliado = 300 + 200 * (n_paradas - 1)
    if admin_id_snapshot:
        saldo_aliado = get_ally_link_balance(ally_id, admin_id_snapshot)
        if saldo_aliado < fee_total_aliado:
            query.edit_message_text(
                "Saldo insuficiente para crear la ruta.\n"
                "Necesitas: ${:,}\n"
                "Tu saldo actual: ${:,}\n\n"
                "Solicita una recarga a tu administrador.".format(fee_total_aliado, saldo_aliado)
            )
            context.user_data.clear()
            show_main_menu(update, context)
            return ConversationHandler.END
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
            requires_cash=requires_cash,
            cash_required_amount=cash_required_amount,
        )
    except Exception as e:
        query.edit_message_text("Error al crear la ruta: {}".format(str(e)))
        return RUTA_CONFIRMACION
    if not route_id:
        query.edit_message_text("Error al crear la ruta. Intenta de nuevo.")
        show_main_menu(update, context)
        return ConversationHandler.END
    try:
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
                parking_fee=int(parada.get("parking_fee") or 0),
            )
        incentivo = int(context.user_data.get("ruta_incentivo", 0) or 0)
        if incentivo > 0:
            add_route_incentive(route_id, incentivo)
        count = publish_route_to_couriers(route_id, ally_id, context, admin_id_override=admin_id_snapshot)
    except Exception as e:
        logger.error("Error publicando ruta %s: %s", route_id, e, exc_info=True)
        query.edit_message_text(
            "Error al publicar la ruta. Intenta de nuevo desde 'Nueva ruta'."
        )
        context.user_data.clear()
        show_main_menu(update, context)
        return ConversationHandler.END
    route_row = get_route_by_id(route_id)
    base_msg = build_route_creation_summary_text(route_row, build_market_launch_status_text(count))
    query.edit_message_text(base_msg)
    context.user_data.clear()
    show_main_menu(update, context)
    return ConversationHandler.END


def ruta_guardar_cust_callback(update, context):
    """Preguntado por parada: guardar o no el cliente nuevo en la agenda."""
    query = update.callback_query
    query.answer()
    ally_id = context.user_data.get("ruta_ally_id")
    # Los datos del cliente aun estan en ruta_paradas[-1] (ya guardado como parada)
    paradas = context.user_data.get("ruta_paradas", [])
    ultima = paradas[-1] if paradas else {}

    if query.data == "ruta_guardar_cust_si" and ally_id:
        name = ultima.get("name") or ""
        phone = ultima.get("phone") or ""
        address = ultima.get("address") or ""
        city = ultima.get("city") or ""
        barrio = ultima.get("barrio") or ""
        lat = ultima.get("lat")
        lng = ultima.get("lng")
        customer_id = ultima.get("customer_id")
        try:
            address_id = None
            message_text = ""
            if customer_id:
                if address:
                    save_result = upsert_customer_address_for_agenda(
                        customer_id=customer_id,
                        label=barrio or city or "Nueva direccion",
                        address_text=address,
                        city=city,
                        barrio=barrio,
                        lat=lat,
                        lng=lng,
                    )
                    if save_result["action"] == "created":
                        address_id = save_result["address_id"]
                        message_text = "Direccion guardada para {}.".format(name or "este cliente")
                    elif save_result["action"] == "coords_updated":
                        message_text = "La direccion ya existia y se completo su geolocalizacion."
                    else:
                        message_text = "La direccion ya estaba guardada en la agenda."
            else:
                existing = get_ally_customer_by_phone(ally_id, phone)
                if existing:
                    customer_id = existing["id"]
                else:
                    customer_id = create_ally_customer(ally_id, name, phone)
                if address:
                    save_result = upsert_customer_address_for_agenda(
                        customer_id=customer_id,
                        label="Principal",
                        address_text=address,
                        city=city,
                        barrio=barrio,
                        lat=lat,
                        lng=lng,
                    )
                    if save_result["action"] == "created":
                        address_id = save_result["address_id"]
                        message_text = "Cliente {} guardado en tu agenda.".format(name)
                    elif save_result["action"] == "coords_updated":
                        message_text = "Cliente {} guardado. La direccion ya existia y se completo su geolocalizacion.".format(name)
                    else:
                        message_text = "Cliente {} guardado. La direccion ya estaba en la agenda.".format(name)
            parking_enabled_ruta = get_ally_parking_fee_enabled(ally_id) if ally_id else False
            if address_id and parking_enabled_ruta:
                context.user_data["ruta_parking_address_id"] = address_id
                keyboard = [
                    [InlineKeyboardButton("Si, hay dificultad para parquear", callback_data="ruta_guardar_cust_parking_si")],
                    [InlineKeyboardButton("No / No lo se", callback_data="ruta_guardar_cust_parking_no")],
                ]
                query.edit_message_text(
                    "{}\n\n"
                    "En ese punto de entrega hay dificultad para parquear moto o bicicleta?\n"
                    "(zona restringida, riesgo de comparendo o sin lugar seguro para dejar el vehiculo)".format(
                        message_text or "Guardado correctamente."
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return RUTA_GUARDAR_CUST_PARKING
            else:
                query.edit_message_text(message_text or "Guardado correctamente.")
        except Exception as e:
            logger.warning("Error guardando cliente de ruta: %s", e)
            query.edit_message_text("No se pudo guardar la informacion en agenda.")
    else:
        if (ultima.get("customer_id") or 0) > 0:
            query.edit_message_text("OK, no se guardo la direccion.")
        else:
            query.edit_message_text("OK, no se guardo el cliente.")

    return _ruta_mostrar_mas_paradas(query, context)


def ruta_guardar_cust_parking_callback(update, context):
    """Respuesta de parqueo al guardar cliente de parada de ruta."""
    query = update.callback_query
    query.answer()
    address_id = context.user_data.pop("ruta_parking_address_id", None)
    if address_id:
        if query.data == "ruta_guardar_cust_parking_si":
            set_address_parking_status(address_id, "ALLY_YES")
        else:
            set_address_parking_status(address_id, "PENDING_REVIEW")
    return _ruta_mostrar_mas_paradas(query, context)


def ruta_parada_buscar_handler(update, context):
    """Busca clientes por nombre o telefono en el flujo de nueva ruta."""
    texto = update.message.text.strip()
    ally_id = context.user_data.get("ruta_ally_id")
    if not ally_id or not texto:
        update.message.reply_text("Escribe un nombre o telefono para buscar.")
        return RUTA_PARADA_BUSCAR
    if len(texto) > 60:
        update.message.reply_text("El texto es muy largo. Intenta con menos caracteres.")
        return RUTA_PARADA_BUSCAR
    activos = search_ally_customers(ally_id, texto) if ally_id else []
    if not activos:
        recientes = list_ally_customers(ally_id, limit=5) if ally_id else []
        if recientes:
            keyboard = []
            keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="ruta_cliente_nuevo")])
            for c in recientes:
                nombre = (c["name"] or "Sin nombre")[:25]
                phone = c["phone"] or ""
                keyboard.append([InlineKeyboardButton(
                    "{} - {}".format(nombre, phone),
                    callback_data="ruta_sel_cust_{}".format(c["id"])
                )])
            keyboard.append([InlineKeyboardButton("Buscar de nuevo", callback_data="ruta_buscar_cliente")])
            update.message.reply_text(
                "No encontre clientes con '{}'.\n\nTus clientes recientes:".format(texto),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return RUTA_PARADA_SELECTOR
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        update.message.reply_text(
            "No se encontro ningun cliente con '{}'.\n\n"
            "Escribe el nombre del cliente para la parada {}:".format(texto, n)
        )
        return RUTA_PARADA_NOMBRE
    mostrados = activos[:10]
    encabezado = "Resultados para '{}'{}:\n\nSelecciona el cliente:".format(
        texto, " (mostrando 10)" if len(activos) >= 10 else ""
    )
    keyboard = []
    for c in mostrados:
        nombre = (c["name"] or "Sin nombre")[:25]
        phone = c["phone"] or ""
        keyboard.append([InlineKeyboardButton(
            "{} - {}".format(nombre, phone),
            callback_data="ruta_sel_cust_{}".format(c["id"])
        )])
    keyboard.append([InlineKeyboardButton("Buscar de nuevo", callback_data="ruta_buscar_cliente")])
    keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="ruta_cliente_nuevo")])
    update.message.reply_text(encabezado, reply_markup=InlineKeyboardMarkup(keyboard))
    return RUTA_PARADA_SELECTOR


def ruta_parada_dedup_callback(update, context):
    """Confirma si usar cliente existente encontrado por telefono en ruta."""
    query = update.callback_query
    query.answer()
    if query.data == "ruta_dedup_si":
        found = context.user_data.pop("ruta_dedup_found", {})
        cust_id = found.get("id")
        name = found.get("name") or ""
        phone = context.user_data.get("ruta_temp_phone", "")
        context.user_data["ruta_temp_customer_id"] = cust_id
        context.user_data["ruta_temp_name"] = name
        # Mostrar direcciones del cliente
        addrs = list_customer_addresses(cust_id) if cust_id else []
        activos = [a for a in addrs if a["status"] == "ACTIVE"]
        if activos:
            paradas = context.user_data.get("ruta_paradas", [])
            n = len(paradas) + 1
            keyboard = []
            for a in activos[:8]:
                parking_status = a["parking_status"] if "parking_status" in a.keys() else "NOT_ASKED"
                parking_tag = " [P]" if parking_status in ("ALLY_YES", "ADMIN_YES") else ""
                label = (a["label"] or a["address_text"] or "Direccion")[:28] + parking_tag
                keyboard.append([InlineKeyboardButton(label, callback_data="ruta_sel_addr_{}".format(a["id"]))])
            keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="ruta_addr_nueva")])
            query.edit_message_text(
                "PARADA {} - {}\n\nSelecciona la direccion de entrega:".format(n, name),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return RUTA_PARADA_SEL_DIRECCION
        # Sin direcciones guardadas — pedir GPS
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text(
            "PARADA {} - {}\n\nEnvia la ubicacion GPS (PIN de Telegram, link o lat,lng).".format(n, name)
        )
        return RUTA_PARADA_UBICACION
    else:
        # No es este cliente — continuar como nuevo con el telefono ya guardado
        context.user_data.pop("ruta_dedup_found", None)
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text(
            "PARADA {}\n\nEscribe el nombre del cliente:".format(n)
        )
        # Limpiar nombre temporal para que lo ingrese de nuevo
        context.user_data.pop("ruta_temp_name", None)
        return RUTA_PARADA_NOMBRE


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
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_pickup_nueva_ubicacion_handler),
        ],
        RUTA_PICKUP_NUEVA_DETALLES: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_pickup_nueva_detalles_handler),
        ],
        RUTA_PICKUP_NUEVA_CIUDAD: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_pickup_nueva_ciudad_handler),
        ],
        RUTA_PICKUP_NUEVA_BARRIO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_pickup_nueva_barrio_handler),
        ],
        RUTA_PICKUP_GUARDAR: [
            CallbackQueryHandler(ruta_pickup_guardar_callback, pattern=r"^ruta_pickup_guardar_(si|no)$"),
        ],
        RUTA_PARADA_SELECTOR: [
            CallbackQueryHandler(ruta_parada_selector_callback, pattern=r"^ruta_(cliente_nuevo|sel_cust_\d+|buscar_cliente|ver_todos)$"),
        ],
        RUTA_PARADA_SEL_DIRECCION: [
            CallbackQueryHandler(ruta_parada_sel_direccion_callback, pattern=r"^ruta_(sel_addr_\d+|addr_nueva)$"),
        ],
        RUTA_PARADA_NOMBRE: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_nombre_handler),
        ],
        RUTA_PARADA_TELEFONO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_telefono_handler),
        ],
        RUTA_PARADA_UBICACION: [
            CallbackQueryHandler(ruta_parada_geo_callback, pattern=r"^ruta_parada_geo_(si|no)$"),
            MessageHandler(Filters.location, ruta_parada_ubicacion_location_handler),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_ubicacion_handler),
        ],
        RUTA_PARADA_DIRECCION: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_direccion_handler),
        ],
        RUTA_MAS_PARADAS: [
            CallbackQueryHandler(ruta_mas_paradas_callback, pattern=r"^ruta_mas_(si|no)$"),
        ],
        PEDIDO_REQUIERE_BASE: [
            CallbackQueryHandler(pedido_requiere_base_callback, pattern=r"^pedido_base_(si|no)$"),
        ],
        PEDIDO_VALOR_BASE: [
            CallbackQueryHandler(pedido_valor_base_callback, pattern=r"^pedido_base_(20000|50000|100000|200000|otro)$"),
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pedido_valor_base_texto),
        ],
        RUTA_DISTANCIA_KM: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_distancia_km_handler),
        ],
        RUTA_CONFIRMACION: [
            CallbackQueryHandler(ruta_edit_pickup_callback, pattern=r"^ruta_edit_pickup$"),
            CallbackQueryHandler(ruta_inc_fijo_callback, pattern=r"^ruta_inc_(1000|1500|2000|3000)$"),
            CallbackQueryHandler(ruta_inc_otro_start, pattern=r"^ruta_inc_otro$"),
            CallbackQueryHandler(ruta_confirmacion_callback, pattern=r"^ruta_(confirmar|cancelar)$"),
        ],
        RUTA_INCENTIVO_MONTO: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_inc_monto_handler),
        ],
        RUTA_GUARDAR_CLIENTES: [
            CallbackQueryHandler(ruta_guardar_cust_callback, pattern=r"^ruta_guardar_cust_(si|no)$"),
        ],
        RUTA_PARADA_BUSCAR: [
            MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ruta_parada_buscar_handler),
        ],
        RUTA_PARADA_DEDUP: [
            CallbackQueryHandler(ruta_parada_dedup_callback, pattern=r"^ruta_dedup_(si|no)$"),
        ],
        RUTA_GUARDAR_CUST_PARKING: [
            CallbackQueryHandler(ruta_guardar_cust_parking_callback, pattern=r"^ruta_guardar_cust_parking_(si|no)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="nueva_ruta_conv",
    persistent=True,
)
