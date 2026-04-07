# =============================================================================
# handlers/quotation.py — cotizar_conv (cotizador de envíos)
# Extraído de main.py (Fase 2d)
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
    COTIZAR_DISTANCIA,
    COTIZAR_ENTREGA,
    COTIZAR_MODO,
    COTIZAR_RECOGIDA,
    COTIZAR_RECOGIDA_SELECTOR,
    COTIZAR_RESULTADO,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER,
    _cotizar_resolver_ubicacion,
    _geo_siguiente_o_gps,
    _maybe_cache_confirmed_geo,
    _mostrar_confirmacion_geocode,
    cancel_conversacion,
    cancel_por_texto,
)
from services import (
    calcular_precio_distancia,
    can_use_cotizador,
    get_ally_by_id,
    get_ally_by_user_id,
    get_ally_location_by_id,
    get_ally_locations,
    get_default_ally_location,
    get_pricing_config,
    get_smart_distance,
    get_user_db_id_from_update,
)


def _cotizar_city_hint(context):
    """Retorna barrio+ciudad del aliado en sesion para mejorar geocoding del cotizador."""
    ally_id = context.user_data.get("cotizar_ally_id")
    if ally_id:
        try:
            ally = get_ally_by_id(ally_id)
            if ally:
                parts = [p for p in [ally.get("barrio"), ally.get("city")] if p]
                if parts:
                    return ", ".join(parts)
        except Exception:
            pass
    return None


def _cotizar_prompt_entrega():
    return (
        "Ahora enviame el punto de ENTREGA.\n"
        "Puedes enviar:\n"
        "- Un PIN de ubicacion de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Una direccion de texto"
    )


def _cotizar_no_more_text(point_label: str):
    return (
        "No encontre mas opciones para {}.\n\n"
        "Envia otra ubicacion para continuar:\n"
        "- Un PIN de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Una direccion con ciudad"
    ).format(point_label)


def cotizar_start(update, context):
    telegram_id = update.effective_user.id
    ok, msg = can_use_cotizador(telegram_id)
    if not ok:
        update.effective_message.reply_text(msg)
        return ConversationHandler.END

    context.user_data.pop("cotizar_pickup", None)
    context.user_data.pop("cotizar_dropoff", None)
    context.user_data.pop("cotizar_ally_id", None)
    keyboard = [
        [InlineKeyboardButton("Por distancia (km)", callback_data="cotizar_modo_km")],
        [InlineKeyboardButton("Por ubicaciones", callback_data="cotizar_modo_ubi")],
    ]
    update.effective_message.reply_text(
        "COTIZADOR\n\n"
        "Como quieres cotizar?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COTIZAR_MODO


def cotizar_modo_callback(update, context):
    query = update.callback_query
    query.answer()
    modo = query.data

    if modo == "cotizar_modo_km":
        query.edit_message_text(
            "COTIZADOR POR DISTANCIA\n\n"
            "Enviame la distancia en km (ej: 5.9)."
        )
        return COTIZAR_DISTANCIA

    elif modo == "cotizar_modo_ubi":
        # Si el usuario es un aliado con ubicaciones guardadas, mostrar selector
        user_db_id = get_user_db_id_from_update(update)
        ally = get_ally_by_user_id(user_db_id) if user_db_id else None
        if ally and ally.get("status") == "APPROVED":
            locations = get_ally_locations(ally["id"])
            if locations:
                context.user_data["cotizar_ally_id"] = ally["id"]
                return _cotizar_mostrar_selector(query, context, locations)
        # Sin ubicaciones guardadas: flujo manual
        query.edit_message_text(
            "COTIZADOR POR UBICACIONES\n\n"
            "Enviame el punto de RECOGIDA.\n"
            "Puedes enviar:\n"
            "- Un PIN de ubicacion de Telegram\n"
            "- Un link de Google Maps\n"
            "- Coordenadas (ej: 4.81,-75.69)\n"
            "- Una direccion de texto"
        )
        return COTIZAR_RECOGIDA

    return ConversationHandler.END


def _cotizar_mostrar_selector(query, context, locations):
    """Muestra el selector de punto de recogida del aliado en el cotizador."""
    keyboard = []
    default_loc = next((l for l in locations if l.get("is_default")), None)
    if default_loc:
        label = (default_loc.get("label") or "Base")[:20]
        address = (default_loc.get("address") or "")[:35]
        sin_gps = " (sin GPS)" if default_loc.get("lat") is None else ""
        keyboard.append([InlineKeyboardButton(
            "Usar mi ubicacion base: {} - {}{}".format(label, address, sin_gps),
            callback_data="cotizar_pickup_base"
        )])
    if len(locations) > 1 or not default_loc:
        keyboard.append([InlineKeyboardButton(
            "Elegir de mis ubicaciones ({})".format(len(locations)),
            callback_data="cotizar_pickup_lista"
        )])
    keyboard.append([InlineKeyboardButton(
        "Ingresar otra ubicacion",
        callback_data="cotizar_pickup_manual"
    )])
    query.edit_message_text(
        "COTIZADOR - PUNTO DE RECOGIDA\n\n"
        "Desde donde se recoge el envio?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COTIZAR_RECOGIDA_SELECTOR


def _cotizar_mostrar_lista(query, ally_id, titulo="MIS UBICACIONES"):
    """Muestra la lista de ubicaciones guardadas del aliado en el cotizador."""
    locations = get_ally_locations(ally_id)
    if not locations:
        query.edit_message_text("No tienes ubicaciones guardadas. Usa /cotizar de nuevo.")
        return ConversationHandler.END
    keyboard = []
    for loc in locations[:8]:
        loc_id = loc["id"]
        label = (loc.get("label") or "Sin nombre")[:20]
        address = (loc.get("address") or "")[:28]
        tags = []
        if loc.get("is_default"):
            tags.append("BASE")
        if loc.get("is_frequent"):
            tags.append("FRECUENTE")
        tag_str = " [{}]".format(", ".join(tags)) if tags else ""
        sin_gps = " (sin GPS)" if loc.get("lat") is None else ""
        keyboard.append([InlineKeyboardButton(
            "{}: {}{}{}".format(label, address, tag_str, sin_gps),
            callback_data="cotizar_pickup_usar_{}".format(loc_id)
        )])
    keyboard.append([InlineKeyboardButton("Ingresar otra ubicacion", callback_data="cotizar_pickup_manual")])
    keyboard.append([InlineKeyboardButton("Volver", callback_data="cotizar_pickup_volver")])
    query.edit_message_text(
        "COTIZADOR - {}\n\n"
        "Selecciona el punto de recogida:".format(titulo),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COTIZAR_RECOGIDA_SELECTOR


def cotizar_pickup_callback(update, context):
    """Maneja la seleccion de punto de recogida del aliado en el cotizador."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("cotizar_ally_id")

    if data == "cotizar_pickup_base":
        if not ally_id:
            query.edit_message_text("Error: intenta /cotizar de nuevo.")
            return ConversationHandler.END
        default_loc = get_default_ally_location(ally_id)
        if not default_loc or default_loc.get("lat") is None:
            return _cotizar_mostrar_lista(query, ally_id, "BASE SIN GPS - ELIGE OTRA")
        context.user_data["cotizar_pickup"] = {
            "lat": default_loc["lat"],
            "lng": default_loc["lng"],
            "method": "saved",
        }
        query.edit_message_text(
            "Recogida: {} - {}\n\n"
            "Ahora enviame el punto de ENTREGA.\n"
            "Puedes enviar un PIN de ubicacion, un link de Google Maps "
            "o coordenadas (ej: 4.81,-75.69).".format(
                default_loc.get("label") or "Base",
                default_loc.get("address") or ""
            )
        )
        return COTIZAR_ENTREGA

    elif data == "cotizar_pickup_lista":
        if not ally_id:
            query.edit_message_text("Error: intenta /cotizar de nuevo.")
            return ConversationHandler.END
        return _cotizar_mostrar_lista(query, ally_id)

    elif data == "cotizar_pickup_manual":
        query.edit_message_text(
            "COTIZADOR POR UBICACIONES\n\n"
            "Enviame el punto de RECOGIDA.\n"
            "Puedes enviar:\n"
            "- Un PIN de ubicacion de Telegram\n"
            "- Un link de Google Maps\n"
            "- Coordenadas (ej: 4.81,-75.69)\n"
            "- Una direccion de texto"
        )
        return COTIZAR_RECOGIDA

    elif data == "cotizar_pickup_volver":
        if not ally_id:
            query.edit_message_text("Error: intenta /cotizar de nuevo.")
            return ConversationHandler.END
        locations = get_ally_locations(ally_id)
        return _cotizar_mostrar_selector(query, context, locations)

    elif data.startswith("cotizar_pickup_usar_"):
        try:
            loc_id = int(data.split("cotizar_pickup_usar_")[1])
        except (ValueError, IndexError):
            query.edit_message_text("Error: intenta /cotizar de nuevo.")
            return ConversationHandler.END
        loc = get_ally_location_by_id(loc_id, ally_id)
        if not loc or loc.get("lat") is None:
            return _cotizar_mostrar_lista(query, ally_id, "SIN GPS - ELIGE OTRA")
        context.user_data["cotizar_pickup"] = {
            "lat": loc["lat"],
            "lng": loc["lng"],
            "method": "saved",
        }
        query.edit_message_text(
            "Recogida: {} - {}\n\n"
            "Ahora enviame el punto de ENTREGA.\n"
            "Puedes enviar un PIN de ubicacion, un link de Google Maps "
            "o coordenadas (ej: 4.81,-75.69).".format(
                loc.get("label") or "Ubicacion",
                loc.get("address") or ""
            )
        )
        return COTIZAR_ENTREGA

    return COTIZAR_RECOGIDA_SELECTOR


def cotizar_distancia(update, context):
    texto = (update.message.text or "").strip().replace(",", ".")
    try:
        distancia = float(texto)
    except ValueError:
        update.message.reply_text("Valor invalido. Escribe la distancia en km (ej: 5.9).")
        return COTIZAR_DISTANCIA

    if distancia <= 0:
        update.message.reply_text("La distancia debe ser mayor a 0. Ej: 3.1")
        return COTIZAR_DISTANCIA

    config = get_pricing_config()
    precio = calcular_precio_distancia(distancia, config)

    update.message.reply_text(
        f"COTIZACION\n\n"
        f"Distancia: {distancia:.1f} km\n"
        f"Precio: ${precio:,}".replace(",", ".")
    )
    return ConversationHandler.END


def cotizar_recogida(update, context):
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
        return COTIZAR_RECOGIDA

    if loc.get("lat") is not None and loc.get("lng") is not None:
        original_text = update.message.text.strip() if update.message and update.message.text else ""
        context.user_data["pending_geo_city_hint"] = _cotizar_city_hint(context)
        _mostrar_confirmacion_geocode(
            update.message,
            context,
            loc,
            original_text,
            "cotizar_recogida_geo_si", "cotizar_recogida_geo_no",
            header_text="Confirma el punto exacto de recogida antes de continuar.",
            question_text="Es esta la ubicacion de recogida correcta?",
        )
        return COTIZAR_RECOGIDA

    update.message.reply_text("No pude confirmar ese punto. Envia otra ubicacion para la recogida.")
    return COTIZAR_RECOGIDA


def cotizar_recogida_location(update, context):
    """Handler para PIN de Telegram en recogida."""
    return cotizar_recogida(update, context)


def cotizar_recogida_geo_callback(update, context):
    """Maneja confirmacion de geocoding en recogida del cotizador."""
    query = update.callback_query
    query.answer()

    if query.data == "cotizar_recogida_geo_si":
        _maybe_cache_confirmed_geo(context)
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Intenta /cotizar de nuevo.")
            return COTIZAR_RECOGIDA
        context.user_data["cotizar_pickup"] = {"lat": lat, "lng": lng, "method": "confirmed"}
        query.edit_message_text(
            "Recogida confirmada.\n\n{}".format(_cotizar_prompt_entrega())
        )
        return COTIZAR_ENTREGA
    else:  # cotizar_recogida_geo_no
        return _geo_siguiente_o_gps(
            query,
            context,
            "cotizar_recogida_geo_si",
            "cotizar_recogida_geo_no",
            COTIZAR_RECOGIDA,
            header_text="Confirma el punto exacto de recogida antes de continuar.",
            question_text="Es esta la ubicacion de recogida correcta?",
            no_more_text=_cotizar_no_more_text("la recogida"),
        )


def cotizar_entrega(update, context):
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
        return COTIZAR_ENTREGA

    if loc.get("lat") is not None and loc.get("lng") is not None:
        original_text = update.message.text.strip() if update.message and update.message.text else ""
        context.user_data["pending_geo_city_hint"] = _cotizar_city_hint(context)
        _mostrar_confirmacion_geocode(
            update.message,
            context,
            loc,
            original_text,
            "cotizar_entrega_geo_si", "cotizar_entrega_geo_no",
            header_text="Confirma el punto exacto de entrega antes de cotizar.",
            question_text="Es esta la ubicacion de entrega correcta?",
        )
        return COTIZAR_ENTREGA

    update.message.reply_text("No pude confirmar ese punto. Envia otra ubicacion para la entrega.")
    return COTIZAR_ENTREGA


def cotizar_entrega_location(update, context):
    """Handler para PIN de Telegram en entrega."""
    return cotizar_entrega(update, context)


def cotizar_entrega_geo_callback(update, context):
    """Maneja confirmacion de geocoding en entrega del cotizador."""
    query = update.callback_query
    query.answer()

    if query.data == "cotizar_entrega_geo_si":
        _maybe_cache_confirmed_geo(context)
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Intenta /cotizar de nuevo.")
            return ConversationHandler.END
        pickup = context.user_data.get("cotizar_pickup")
        if not pickup:
            query.edit_message_text("Error: no se encontro recogida. Usa /cotizar de nuevo.")
            return ConversationHandler.END

        result = get_smart_distance(pickup["lat"], pickup["lng"], lat, lng)
        distance_km = result["distance_km"]
        config = get_pricing_config()
        precio = calcular_precio_distancia(distance_km, config)

        source = result["source"]
        if "google" in source:
            nota_fuente = "Distancia por ruta (Google Maps)"
        elif "haversine" in source:
            nota_fuente = "Distancia estimada (calculo local)"
        else:
            nota_fuente = f"Distancia desde cache ({source})"

        context.user_data["cotizar_result_pickup_lat"] = pickup["lat"]
        context.user_data["cotizar_result_pickup_lng"] = pickup["lng"]
        context.user_data["cotizar_result_dropoff_lat"] = lat
        context.user_data["cotizar_result_dropoff_lng"] = lng
        keyboard = [
            [InlineKeyboardButton("Crear pedido con esta ruta", callback_data="cotizar_crear_pedido")],
            [InlineKeyboardButton("Varias entregas (ruta)", callback_data="cotizar_crear_ruta")],
            [InlineKeyboardButton("Solo consulta", callback_data="cotizar_cerrar")],
        ]
        query.edit_message_text(
            f"COTIZACION\n\n"
            f"Distancia: {distance_km:.1f} km\n"
            f"Precio: ${precio:,}\n\n".replace(",", ".")
            + f"{nota_fuente}\n\n"
            + "Deseas crear el pedido?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        context.user_data.pop("cotizar_pickup", None)
        context.user_data.pop("cotizar_ally_id", None)
        return COTIZAR_RESULTADO
    else:  # cotizar_entrega_geo_no
        return _geo_siguiente_o_gps(
            query,
            context,
            "cotizar_entrega_geo_si",
            "cotizar_entrega_geo_no",
            COTIZAR_ENTREGA,
            header_text="Confirma el punto exacto de entrega antes de cotizar.",
            question_text="Es esta la ubicacion de entrega correcta?",
            no_more_text=_cotizar_no_more_text("la entrega"),
        )


def cotizar_resultado_callback(update, context):
    """Maneja la decision del aliado tras ver el precio de cotizacion."""
    query = update.callback_query
    query.answer()

    if query.data == "cotizar_cerrar":
        context.user_data.pop("cotizar_result_pickup_lat", None)
        context.user_data.pop("cotizar_result_pickup_lng", None)
        context.user_data.pop("cotizar_result_dropoff_lat", None)
        context.user_data.pop("cotizar_result_dropoff_lng", None)
        context.user_data.pop("cotizar_pickup", None)
        context.user_data.pop("cotizar_ally_id", None)
        try:
            query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        query.message.reply_text("Cotizacion completada.")
        return ConversationHandler.END

    if query.data == "cotizar_crear_ruta":
        pickup_lat = context.user_data.pop("cotizar_result_pickup_lat", None)
        pickup_lng = context.user_data.pop("cotizar_result_pickup_lng", None)
        context.user_data.pop("cotizar_result_dropoff_lat", None)
        context.user_data.pop("cotizar_result_dropoff_lng", None)
        context.user_data.pop("cotizar_pickup", None)
        context.user_data.pop("cotizar_ally_id", None)
        context.user_data["prefill_ruta_pickup_lat"] = pickup_lat
        context.user_data["prefill_ruta_pickup_lng"] = pickup_lng
        query.edit_message_text("Ruta de multiples paradas.")
        keyboard = [[
            InlineKeyboardButton("Cliente recurrente", callback_data="cotizar_ruta_cust_recurrente"),
            InlineKeyboardButton("Cliente nuevo", callback_data="cotizar_ruta_cust_nuevo"),
        ]]
        query.message.reply_text(
            "Primera parada - Tipo de cliente:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ConversationHandler.END

    # cotizar_crear_pedido
    pickup_lat = context.user_data.pop("cotizar_result_pickup_lat", None)
    pickup_lng = context.user_data.pop("cotizar_result_pickup_lng", None)
    dropoff_lat = context.user_data.pop("cotizar_result_dropoff_lat", None)
    dropoff_lng = context.user_data.pop("cotizar_result_dropoff_lng", None)
    context.user_data.pop("cotizar_pickup", None)
    context.user_data.pop("cotizar_ally_id", None)

    context.user_data["prefill_pickup_lat"] = pickup_lat
    context.user_data["prefill_pickup_lng"] = pickup_lng
    context.user_data["prefill_dropoff_lat"] = dropoff_lat
    context.user_data["prefill_dropoff_lng"] = dropoff_lng

    query.edit_message_text("Perfecto. Ahora selecciona el tipo de cliente:")
    keyboard = [[
        InlineKeyboardButton("Cliente recurrente", callback_data="cotizar_cust_recurrente"),
        InlineKeyboardButton("Cliente nuevo", callback_data="cotizar_cust_nuevo"),
    ]]
    query.message.reply_text(
        "Tipo de cliente:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END



cotizar_conv = ConversationHandler(
    entry_points=[
        CommandHandler("cotizar", cotizar_start),
        MessageHandler(Filters.regex(r'^Cotizar envio$'), cotizar_start),
    ],
    states={
        COTIZAR_MODO: [
            CallbackQueryHandler(cotizar_modo_callback, pattern=r"^cotizar_modo_"),
        ],
        COTIZAR_RECOGIDA_SELECTOR: [
            CallbackQueryHandler(cotizar_pickup_callback, pattern=r"^cotizar_pickup_"),
        ],
        COTIZAR_DISTANCIA: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, cotizar_distancia),
        ],
        COTIZAR_RECOGIDA: [
            CallbackQueryHandler(cotizar_recogida_geo_callback, pattern=r"^cotizar_recogida_geo_"),
            MessageHandler(Filters.location, cotizar_recogida_location),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, cotizar_recogida),
        ],
        COTIZAR_ENTREGA: [
            CallbackQueryHandler(cotizar_entrega_geo_callback, pattern=r"^cotizar_entrega_geo_"),
            MessageHandler(Filters.location, cotizar_entrega_location),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, cotizar_entrega),
        ],
        COTIZAR_RESULTADO: [
            CallbackQueryHandler(cotizar_resultado_callback, pattern=r"^cotizar_(crear_pedido|crear_ruta|cerrar)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    name="cotizar_conv",
    persistent=True,
)


