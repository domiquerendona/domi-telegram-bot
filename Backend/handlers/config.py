# =============================================================================
# handlers/config.py — ConversationHandlers de configuración de tarifas y subsidios
# Extraído de main.py (Fase 2b)
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
    ALERTAS_OFERTA_INPUT,
    CONFIG_ALLY_MIN_PURCHASE_VALOR,
    CONFIG_ALLY_SUBSIDY_VALOR,
    TARIFAS_VALOR,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER,
    cancel_conversacion,
    cancel_por_texto,
)
from services import (
    calc_buy_products_surcharge,
    calcular_precio_distancia,
    clear_offer_voice,
    es_admin_plataforma,
    get_admin_by_telegram_id,
    get_ally_by_id,
    get_buy_pricing_config,
    get_offer_alerts_config,
    get_pricing_config,
    save_offer_voice,
    save_pricing_setting,
    set_offer_reminder_seconds,
    set_offer_reminders_enabled,
    set_offer_voice_enabled,
    update_ally_delivery_subsidy,
    update_ally_min_purchase_for_subsidy,
    user_has_platform_admin,
)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _build_tarifas_texto(config, buy_config):
    """Construye el texto con los valores actuales de ambas tarifas."""
    return (
        "CONFIGURACION DE TARIFAS\n\n"
        "TARIFAS POR DISTANCIA:\n"
        f"1. Precio tramo 1 (0-{config['tier1_max_km']} km): ${config['precio_0_2km']:,}\n"
        f"2. Precio tramo 2 (>{config['tier1_max_km']}-{config['tier2_max_km']} km): ${config['precio_2_3km']:,}\n"
        f"3. Limite tramo 1 (km): {config['tier1_max_km']}\n"
        f"4. Limite tramo 2 / base km extra (km): {config['tier2_max_km']}\n"
        f"5. Precio km extra normal (<= {config['umbral_km_largo']} km): ${config['precio_km_extra_normal']:,}\n"
        f"6. Umbral km largo: {config['umbral_km_largo']} km\n"
        f"7. Precio km extra largo (>{config['umbral_km_largo']} km): ${config['precio_km_extra_largo']:,}\n"
        f"8. Ruta: parada adicional: ${config['tarifa_parada_adicional']:,}\n"
        "\nTARIFAS COMPRAS (recargo por productos):\n"
        f"9. Productos incluidos gratis: {buy_config['free_threshold']}\n"
        f"10. Recargo por producto adicional: ${buy_config['extra_fee']:,} c/u\n"
        f"   (Ej: {buy_config['free_threshold']+3} productos -> ${3*buy_config['extra_fee']:,} de recargo)\n"
    )


def _offer_alerts_status_text():
    cfg = get_offer_alerts_config()
    reminders_enabled = cfg["reminders_enabled"]
    reminder_seconds = cfg["reminder_seconds"]
    voice_enabled = cfg["voice_enabled"]
    voice_file_id = cfg["voice_file_id"]
    voice_state = "ACTIVA" if (voice_enabled == "1" and voice_file_id) else "INACTIVA"

    return (
        "CONFIG ALERTAS OFERTA\n\n"
        "Estado actual:\n"
        "- Recordatorios: {}\n"
        "- Segundos: {}\n"
        "- Voz: {}\n"
        "- Voice file_id: {}\n\n"
        "Comandos:\n"
        "- ver\n"
        "- recordatorios 1  (o 0)\n"
        "- segundos 8,16\n"
        "- voz 1  (o 0)\n"
        "- limpiar_voz\n\n"
        "Tambien puedes enviar una nota de voz o audio aqui.\n"
        "El bot guardara el file_id y activara voz automaticamente.\n\n"
        "Escribe /cancel para salir."
    ).format(
        "ACTIVOS" if reminders_enabled == "1" else "INACTIVOS",
        reminder_seconds or "8,16",
        voice_state,
        voice_file_id if voice_file_id else "(vacio)",
    )


# ---------------------------------------------------------------------------
# tarifas_conv handlers
# ---------------------------------------------------------------------------

def tarifas_start(update, context):
    """Comando /tarifas - Solo Admin Plataforma."""
    user = update.effective_user

    if not es_admin_plataforma(user.id):
        update.message.reply_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    config = get_pricing_config()
    buy_config = get_buy_pricing_config()
    mensaje = _build_tarifas_texto(config, buy_config)

    keyboard = [
        [InlineKeyboardButton("📏 Editar tarifas por distancia", callback_data="pricing_menu_distancia")],
        [InlineKeyboardButton("🛒 Editar tarifas compras", callback_data="pricing_menu_compras")],
        [InlineKeyboardButton("Salir", callback_data="pricing_exit")],
    ]

    update.effective_message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


def tarifas_edit_callback(update, context):
    """Callback para editar un valor de tarifa."""
    query = update.callback_query
    query.answer()

    if not es_admin_plataforma(query.from_user.id):
        query.edit_message_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    data = query.data

    if data == "pricing_exit":
        query.edit_message_text("Configuracion de tarifas cerrada.")
        return ConversationHandler.END

    if data == "pricing_volver":
        config = get_pricing_config()
        buy_config = get_buy_pricing_config()
        mensaje = _build_tarifas_texto(config, buy_config)
        keyboard = [
            [InlineKeyboardButton("📏 Editar tarifas por distancia", callback_data="pricing_menu_distancia")],
            [InlineKeyboardButton("🛒 Editar tarifas compras", callback_data="pricing_menu_compras")],
            [InlineKeyboardButton("Salir", callback_data="pricing_exit")],
        ]
        query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    if data == "pricing_menu_distancia":
        keyboard = [
            [InlineKeyboardButton("Cambiar precio tramo 1", callback_data="pricing_edit_precio_0_2km")],
            [InlineKeyboardButton("Cambiar precio tramo 2", callback_data="pricing_edit_precio_2_3km")],
            [InlineKeyboardButton("Cambiar limite tramo 1", callback_data="pricing_edit_tier1_max_km")],
            [InlineKeyboardButton("Cambiar limite tramo 2", callback_data="pricing_edit_tier2_max_km")],
            [InlineKeyboardButton("Cambiar km extra normal", callback_data="pricing_edit_precio_km_extra_normal")],
            [InlineKeyboardButton("Cambiar umbral km largo", callback_data="pricing_edit_umbral_km_largo")],
            [InlineKeyboardButton("Cambiar km extra largo", callback_data="pricing_edit_precio_km_extra_largo")],
            [InlineKeyboardButton("Cambiar parada adicional ruta", callback_data="pricing_edit_tarifa_parada_adicional")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="pricing_volver")],
        ]
        query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    if data == "pricing_menu_compras":
        buy_config = get_buy_pricing_config()
        keyboard = [
            [InlineKeyboardButton(
                f"Productos incluidos gratis (actual: {buy_config['free_threshold']})",
                callback_data="pricing_edit_buy_free_threshold"
            )],
            [InlineKeyboardButton(
                f"Recargo por producto adicional (actual: ${buy_config['extra_fee']:,})".replace(",", "."),
                callback_data="pricing_edit_buy_extra_fee"
            )],
            [InlineKeyboardButton("⬅️ Volver", callback_data="pricing_volver")],
        ]
        query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    if not data.startswith("pricing_edit_"):
        query.edit_message_text("Opcion no valida.")
        return ConversationHandler.END

    field = data.replace("pricing_edit_", "")
    context.user_data["pricing_field"] = field

    field_names = {
        "precio_0_2km": "Precio tramo 1",
        "precio_2_3km": "Precio tramo 2",
        "tier1_max_km": "Limite tramo 1 (km)",
        "tier2_max_km": "Limite tramo 2 / base km extra (km)",
        "precio_km_extra_normal": "Precio km extra normal",
        "umbral_km_largo": "Umbral km largo",
        "precio_km_extra_largo": "Precio km extra largo",
        "tarifa_parada_adicional": "Ruta: parada adicional",
        "buy_free_threshold": "Compras: productos incluidos gratis (default 2)",
        "buy_extra_fee": "Compras: recargo por producto adicional en $ (default 1000)",
    }

    field_name = field_names.get(field, field)

    query.edit_message_text(
        f"Editar: {field_name}\n\n"
        f"Envia el nuevo valor (numero).\n"
        f"O escribe /cancel para cancelar."
    )

    return TARIFAS_VALOR


def tarifas_set_valor(update, context):
    """Captura y guarda el nuevo valor."""
    user = update.effective_user

    if not es_admin_plataforma(user.id):
        update.message.reply_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    texto = (update.message.text or "").strip().replace(",", ".")
    field = context.user_data.get("pricing_field")

    if not field:
        update.message.reply_text("Error: no se pudo identificar el campo a editar.")
        return ConversationHandler.END

    try:
        float(texto)
    except ValueError:
        update.message.reply_text("Valor invalido. Debe ser un numero. Intenta de nuevo o usa /cancel.")
        return TARIFAS_VALOR

    try:
        save_pricing_setting(field, texto)
    except ValueError as e:
        update.message.reply_text(
            f"Valor rechazado: {e}\n\nIntenta de nuevo o usa /cancel."
        )
        return TARIFAS_VALOR

    config = get_pricing_config()
    buy_config = get_buy_pricing_config()

    test_14 = calcular_precio_distancia(1.4)
    test_16 = calcular_precio_distancia(1.6)
    test_26 = calcular_precio_distancia(2.6)
    test_111 = calcular_precio_distancia(11.1)
    free_th = buy_config.get("free_threshold", 2)
    test_buy_3 = calc_buy_products_surcharge(free_th, buy_config)
    test_buy_8 = calc_buy_products_surcharge(free_th + 3, buy_config)
    test_buy_15 = calc_buy_products_surcharge(free_th + 8, buy_config)

    mensaje = (
        "Guardado.\n\n"
        "TARIFAS DISTANCIA:\n"
        f"- Precio tramo 1 (0-{config['tier1_max_km']} km): ${config['precio_0_2km']:,}\n"
        f"- Precio tramo 2 (>{config['tier1_max_km']}-{config['tier2_max_km']} km): ${config['precio_2_3km']:,}\n"
        f"- Limite tramo 1: {config['tier1_max_km']} km\n"
        f"- Limite tramo 2 / base km extra: {config['tier2_max_km']} km\n"
        f"- Precio km extra normal: ${config['precio_km_extra_normal']:,}\n"
        f"- Umbral largo: {config['umbral_km_largo']} km\n"
        f"- Precio km extra largo: ${config['precio_km_extra_largo']:,}\n\n"
        f"RUTAS:\n"
        f"- Parada adicional: ${config['tarifa_parada_adicional']:,}\n\n"
        f"TARIFAS COMPRAS:\n"
        f"- Productos gratis: {buy_config['free_threshold']}\n"
        f"- Recargo adicional: ${buy_config['extra_fee']:,} c/u\n\n"
        f"Prueba rapida distancia:\n"
        f"1.4 km -> ${test_14:,}\n"
        f"1.6 km -> ${test_16:,}\n"
        f"2.6 km -> ${test_26:,}\n"
        f"11.1 km -> ${test_111:,}\n\n"
        f"Prueba rapida compras:\n"
        f"{buy_config['free_threshold']} productos -> ${test_buy_3:,}\n"
        f"{buy_config['free_threshold']+3} productos -> ${test_buy_8:,}\n"
        f"{buy_config['free_threshold']+8} productos -> ${test_buy_15:,}"
    )

    update.message.reply_text(mensaje)
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# config_alertas_oferta_conv handlers
# ---------------------------------------------------------------------------

def config_alertas_oferta_start(update, context):
    user = update.effective_user
    if not es_admin_plataforma(user.id):
        update.message.reply_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END
    update.message.reply_text(_offer_alerts_status_text())
    return ALERTAS_OFERTA_INPUT


def config_alertas_oferta_input(update, context):
    user = update.effective_user
    if not es_admin_plataforma(user.id):
        update.message.reply_text("No autorizado.")
        return ConversationHandler.END

    msg = update.message
    if not msg:
        return ALERTAS_OFERTA_INPUT

    if msg.voice or msg.audio:
        file_id = msg.voice.file_id if msg.voice else msg.audio.file_id
        save_offer_voice(file_id)
        update.message.reply_text(
            "Voice file_id guardado y voz activada.\n\n" + _offer_alerts_status_text()
        )
        return ALERTAS_OFERTA_INPUT

    text = (msg.text or "").strip()
    text_lower = text.lower()

    if text_lower in ("ver", "estado"):
        update.message.reply_text(_offer_alerts_status_text())
        return ALERTAS_OFERTA_INPUT

    if text_lower.startswith("recordatorios "):
        value = text_lower.replace("recordatorios ", "").strip()
        if value not in ("0", "1", "on", "off"):
            update.message.reply_text("Valor invalido. Usa: recordatorios 1 o recordatorios 0")
            return ALERTAS_OFERTA_INPUT
        set_offer_reminders_enabled(value in ("1", "on"))
        update.message.reply_text("Recordatorios actualizados.\n\n" + _offer_alerts_status_text())
        return ALERTAS_OFERTA_INPUT

    if text_lower.startswith("segundos "):
        raw = text_lower.replace("segundos ", "").strip()
        chunks = [c.strip() for c in raw.split(",") if c.strip()]
        seconds = []
        for c in chunks:
            if not c.isdigit():
                update.message.reply_text("Formato invalido. Ejemplo: segundos 8,16")
                return ALERTAS_OFERTA_INPUT
            n = int(c)
            if n <= 0 or n >= 30:
                update.message.reply_text("Cada segundo debe estar entre 1 y 29.")
                return ALERTAS_OFERTA_INPUT
            if n not in seconds:
                seconds.append(n)
        if not seconds:
            update.message.reply_text("Debes enviar al menos un segundo. Ejemplo: segundos 8,16")
            return ALERTAS_OFERTA_INPUT
        set_offer_reminder_seconds(seconds)
        update.message.reply_text("Segundos actualizados.\n\n" + _offer_alerts_status_text())
        return ALERTAS_OFERTA_INPUT

    if text_lower.startswith("voz "):
        value = text_lower.replace("voz ", "").strip()
        if value not in ("0", "1", "on", "off"):
            update.message.reply_text("Valor invalido. Usa: voz 1 o voz 0")
            return ALERTAS_OFERTA_INPUT
        enable = value in ("1", "on")
        if enable:
            cfg = get_offer_alerts_config()
            if not cfg["voice_file_id"]:
                update.message.reply_text(
                    "No hay voice_file_id guardado.\n"
                    "Envia una nota de voz o audio primero."
                )
                return ALERTAS_OFERTA_INPUT
        set_offer_voice_enabled(enable)
        update.message.reply_text("Voz actualizada.\n\n" + _offer_alerts_status_text())
        return ALERTAS_OFERTA_INPUT

    if text_lower == "limpiar_voz":
        clear_offer_voice()
        update.message.reply_text("Voice file_id limpiado y voz desactivada.\n\n" + _offer_alerts_status_text())
        return ALERTAS_OFERTA_INPUT

    update.message.reply_text(
        "Comando no reconocido.\n"
        "Usa: ver, recordatorios 1/0, segundos 8,16, voz 1/0, limpiar_voz"
    )
    return ALERTAS_OFERTA_INPUT


# ---------------------------------------------------------------------------
# config_ally_subsidy_conv handlers
# ---------------------------------------------------------------------------

def config_ally_subsidy_start(update, context):
    """Entry point del ConversationHandler para editar el subsidio de domicilio de un aliado."""
    query = update.callback_query
    query.answer()
    if not user_has_platform_admin(query.from_user.id):
        query.answer("Solo el Administrador de Plataforma puede editar el subsidio.", show_alert=True)
        return ConversationHandler.END
    ally_id = int(query.data.split("_")[-1])
    ally = get_ally_by_id(ally_id)
    if not ally:
        query.edit_message_text("No se encontro el aliado.")
        return ConversationHandler.END
    subsidio_actual = int(ally["delivery_subsidy"] or 0)
    context.user_data["config_subsidy_ally_id"] = ally_id
    query.edit_message_text(
        "Aliado: {}\n\nSubsidio actual: ${:,}\n\n"
        "Envia el nuevo valor del subsidio (numero entero en COP, 0 para sin subsidio).\n"
        "Usa /cancel para cancelar.".format(ally["business_name"], subsidio_actual)
    )
    return CONFIG_ALLY_SUBSIDY_VALOR


def config_ally_subsidy_valor(update, context):
    """Captura y guarda el nuevo subsidio de domicilio del aliado."""
    texto = (update.message.text or "").strip().replace(".", "").replace(",", "")
    ally_id = context.user_data.get("config_subsidy_ally_id")
    if not ally_id:
        update.message.reply_text("Error: sesion perdida. Vuelve al menu de configuracion.")
        return ConversationHandler.END
    try:
        nuevo_subsidio = int(texto)
        if nuevo_subsidio < 0:
            raise ValueError("negativo")
    except ValueError:
        update.message.reply_text(
            "Valor invalido. Debe ser un numero entero mayor o igual a 0. Intenta de nuevo o usa /cancel."
        )
        return CONFIG_ALLY_SUBSIDY_VALOR
    update_ally_delivery_subsidy(ally_id, nuevo_subsidio)
    context.user_data.pop("config_subsidy_ally_id", None)
    ally = get_ally_by_id(ally_id)
    business_name = ally["business_name"] if ally else "ID {}".format(ally_id)
    update.message.reply_text(
        "Subsidio de domicilio actualizado.\n\n"
        "Aliado: {}\nNuevo subsidio: ${:,}".format(business_name, nuevo_subsidio)
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# config_ally_minpurchase_conv handlers
# ---------------------------------------------------------------------------

def config_ally_minpurchase_start(update, context):
    """Inicia el flujo para editar la compra mínima requerida para aplicar el subsidio."""
    query = update.callback_query
    query.answer()
    telegram_id = query.from_user.id
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin or admin.get("role") != "PLATFORM_ADMIN":
        query.answer("Solo el Administrador de Plataforma puede editar esto.", show_alert=True)
        return ConversationHandler.END
    ally_id = int(query.data.split("_")[-1])
    ally = get_ally_by_id(ally_id)
    if not ally:
        query.edit_message_text("No se encontro el aliado.")
        return ConversationHandler.END
    try:
        min_actual = ally["min_purchase_for_subsidy"]
    except (KeyError, IndexError):
        min_actual = None
    subsidio = int(ally["delivery_subsidy"] or 0)
    context.user_data["config_minpurchase_ally_id"] = ally_id
    if subsidio == 0:
        query.edit_message_text(
            "Este aliado no tiene subsidio configurado ($0). "
            "Configura primero el subsidio antes de definir la compra minima.\n\n"
            "Usa /cancel para cancelar."
        )
        return ConversationHandler.END
    if min_actual is not None:
        actual_txt = "Compra minima actual: ${:,}".format(min_actual)
        instruccion = (
            "Envia el nuevo valor minimo de compra (entero en COP), "
            "0 para quitar la condicion (subsidio incondicional), "
            "o /cancel para cancelar."
        )
    else:
        actual_txt = "Sin compra minima configurada (subsidio incondicional)."
        instruccion = (
            "Envia el valor minimo de compra requerido para aplicar el subsidio "
            "(entero en COP, mayor a 0), o /cancel para cancelar."
        )
    query.edit_message_text(
        "Aliado: {}\nSubsidio: ${:,}\n{}\n\n{}".format(
            ally["business_name"], subsidio, actual_txt, instruccion
        )
    )
    return CONFIG_ALLY_MIN_PURCHASE_VALOR


def config_ally_minpurchase_valor(update, context):
    """Captura y guarda la compra mínima para activar el subsidio del aliado."""
    texto = (update.message.text or "").strip().replace(".", "").replace(",", "")
    ally_id = context.user_data.get("config_minpurchase_ally_id")
    if not ally_id:
        update.message.reply_text("Error: sesion perdida. Vuelve al menu de configuracion.")
        return ConversationHandler.END
    try:
        valor = int(texto)
        if valor < 0:
            raise ValueError("negativo")
    except ValueError:
        update.message.reply_text(
            "Valor invalido. Debe ser un numero entero >= 0 (0 = subsidio incondicional). Intenta de nuevo o usa /cancel."
        )
        return CONFIG_ALLY_MIN_PURCHASE_VALOR
    nuevo_min = valor if valor > 0 else None
    update_ally_min_purchase_for_subsidy(ally_id, nuevo_min)
    context.user_data.pop("config_minpurchase_ally_id", None)
    ally = get_ally_by_id(ally_id)
    business_name = ally["business_name"] if ally else "ID {}".format(ally_id)
    if nuevo_min is not None:
        resultado = "Compra minima para subsidio: ${:,}".format(nuevo_min)
    else:
        resultado = "Subsidio ahora es incondicional (sin compra minima)."
    update.message.reply_text(
        "Configuracion actualizada.\n\nAliado: {}\n{}".format(business_name, resultado)
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# ConversationHandlers
# ---------------------------------------------------------------------------

tarifas_conv = ConversationHandler(
    entry_points=[CommandHandler("tarifas", tarifas_start)],
    states={
        TARIFAS_VALOR: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, tarifas_set_valor)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
)

config_alertas_oferta_conv = ConversationHandler(
    entry_points=[CommandHandler("config_alertas_oferta", config_alertas_oferta_start)],
    states={
        ALERTAS_OFERTA_INPUT: [
            MessageHandler((Filters.text | Filters.voice | Filters.audio) & ~Filters.command, config_alertas_oferta_input),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
)

config_ally_minpurchase_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(config_ally_minpurchase_start, pattern=r"^config_ally_minpurchase_\d+$")],
    states={
        CONFIG_ALLY_MIN_PURCHASE_VALOR: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, config_ally_minpurchase_valor)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
)

config_ally_subsidy_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(config_ally_subsidy_start, pattern=r"^config_ally_subsidy_\d+$")],
    states={
        CONFIG_ALLY_SUBSIDY_VALOR: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, config_ally_subsidy_valor)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
)

# ---------------------------------------------------------------------------
# config_subs_conv — Admin configura precio de suscripcion para un aliado
# Entry: callback config_subs_{ally_id}
# ---------------------------------------------------------------------------

from handlers.states import CONFIG_SUBS_PRECIO
from services import (
    get_setting,
    set_ally_subscription_price,
    get_ally_subscription_price,
    get_ally_link_balance,
)


def config_subs_start(update, context):
    query = update.callback_query
    query.answer()
    data = query.data  # config_subs_{ally_id}
    ally_id = int(data.split("_")[-1])
    context.user_data["subs_ally_id"] = ally_id

    platform_share = int(get_setting("subscription_platform_share") or 20000)
    current = get_ally_subscription_price(
        context.user_data.get("admin_db_id") or 0, ally_id
    )
    current_txt = "${:,}".format(current) if current else "No configurado"

    query.edit_message_text(
        "CONFIGURAR SUSCRIPCION MENSUAL\n\n"
        "Aliado id: {}\n"
        "Precio actual: {}\n"
        "Piso de plataforma: ${:,}\n\n"
        "El aliado pagara el precio que configures. De ese total, ${:,} "
        "van a plataforma y el resto es tu ganancia mensual por este aliado.\n\n"
        "Ingresa el nuevo precio mensual (en pesos, solo numeros):\n"
        "Minimo: ${:,}".format(ally_id, current_txt, platform_share, platform_share, platform_share + 1),
    )
    return CONFIG_SUBS_PRECIO


def config_subs_precio(update, context):
    text = update.message.text.strip().replace(".", "").replace(",", "").replace("$", "")
    if not text.isdigit():
        update.message.reply_text("Ingresa solo numeros. Ejemplo: 80000")
        return CONFIG_SUBS_PRECIO

    price = int(text)
    platform_share = int(get_setting("subscription_platform_share") or 20000)
    if price <= platform_share:
        update.message.reply_text(
            "El precio debe ser mayor a ${:,} (piso de plataforma). Intenta de nuevo.".format(platform_share)
        )
        return CONFIG_SUBS_PRECIO

    admin_id = context.user_data.get("admin_db_id") or 0
    ally_id = context.user_data.get("subs_ally_id")
    admin_share = price - platform_share

    set_ally_subscription_price(admin_id, ally_id, price)

    update.message.reply_text(
        "Precio configurado: ${:,}/mes\n"
        "Tu ganancia: ${:,}/mes\n"
        "Plataforma: ${:,}/mes\n\n"
        "El aliado podra renovar su suscripcion desde su menu.".format(
            price, admin_share, platform_share
        )
    )
    return ConversationHandler.END


config_subs_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(config_subs_start, pattern=r"^config_subs_\d+$")],
    states={
        CONFIG_SUBS_PRECIO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, config_subs_precio)
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
)
