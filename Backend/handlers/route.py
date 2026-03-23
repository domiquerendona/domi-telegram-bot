# =============================================================================
# handlers/route.py — Flujo de nueva ruta multi-parada
# Extraído de main.py
# =============================================================================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from handlers.states import (
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
    RUTA_PARADA_CIUDAD,
    RUTA_PARADA_BARRIO,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER,
    _OPTIONS_HINT,
    _fmt_pesos,
    _geo_siguiente_o_gps,
    _handle_text_field_input,
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
    get_ally_customer_by_id,
    list_customer_addresses,
    get_customer_address_by_id,
    get_ally_customer_by_phone,
    create_ally_customer,
    create_customer_address,
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
)
from order_delivery import publish_route_to_couriers

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
    total_fee = precio_info["total_fee"]
    stop_fee = precio_info.get("tarifa_parada_adicional", 0)
    mensaje_ahorro = precio_info.get("mensaje_ahorro", "")
    context.user_data["ruta_precio"] = precio_info

    distancia_estimada = context.user_data.get("ruta_distancia_estimada", False)

    text = "RUTA DE ENTREGA\n"
    if fue_optimizado:
        text += "(Orden optimizado para menor distancia)\n"
    if distancia_estimada:
        text += "(Distancia aproximada — sin datos de carretera exactos)\n"
    text += "\nRecoge en: {}\n\n".format(pickup_address)
    for i, p in enumerate(paradas, 1):
        text += "Parada {}:\n  Cliente: {} - {}\n  Direccion: {}\n".format(
            i, p.get("name") or "Sin nombre", p.get("phone") or "", p.get("address") or "Sin direccion"
        )
    text += "\nDistancia total: {:.1f} km{}\n".format(
        total_km, " (aprox)" if distancia_estimada else ""
    )
    text += "Precio base (distancia): ${:,}\n".format(distance_fee)
    if additional_fee > 0:
        text += "Paradas adicionales ({} x ${:,}): ${:,}\n".format(len(paradas) - 1, stop_fee, additional_fee)
    text += "TOTAL: ${:,}".format(total_fee)
    if mensaje_ahorro:
        text += "\n{}".format(mensaje_ahorro)
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
                context.user_data["ruta_distancia_estimada"] = dist_result.get("estimada", False)
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
