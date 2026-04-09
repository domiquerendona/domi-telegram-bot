# =============================================================================
# handlers/ally_bandeja.py — Bandeja de solicitudes del aliado (enlace público)
# Extraído de main.py
# =============================================================================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import logging
logger = logging.getLogger(__name__)

from services import (
    count_ally_form_requests_by_status,
    create_order,
    get_ally_by_id,
    get_ally_by_user_id,
    get_ally_form_request_by_id,
    get_approved_admin_link_for_ally,
    get_courier_by_id,
    get_default_ally_location,
    get_or_create_ally_public_token,
    get_order_by_id,
    get_user_db_id_from_update,
    list_ally_form_requests_for_ally,
    mark_ally_form_request_converted,
    update_ally_form_request_status,
)
from handlers.order import _ally_bandeja_guardar_en_agenda
from order_delivery import (
    _get_order_durations,
    _format_duration,
    publish_order_to_couriers,
    build_courier_order_preview_text,
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

    # Bloque de tiempos (solo para pedidos entregados)
    if order["status"] == "DELIVERED":
        durations = _get_order_durations(order)
        dur_lines = []
        if "llegada_aliado" in durations:
            dur_lines.append("  Llegada al pickup: {}".format(_format_duration(durations["llegada_aliado"])))
        if "espera_recogida" in durations:
            dur_lines.append("  Espera en recogida: {}".format(_format_duration(durations["espera_recogida"])))
        if "entrega_cliente" in durations:
            dur_lines.append("  Tiempo de entrega: {}".format(_format_duration(durations["entrega_cliente"])))
        if "tiempo_total" in durations:
            dur_lines.append("  Tiempo total: {}".format(_format_duration(durations["tiempo_total"])))
        if dur_lines:
            lines.append("")
            lines.append("Tiempos del servicio:")
            lines.extend(dur_lines)

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

    # ---- Crear pedido desde solicitud (con o sin guardar en agenda) ----
    if data.startswith("alybandeja_crear_") or data.startswith("alybandeja_crearyguardar_"):
        guardar = data.startswith("alybandeja_crearyguardar_")
        request_id = int(data.split("_")[-1])
        solicitud = get_ally_form_request_by_id(request_id, ally_id)
        if not solicitud:
            query.edit_message_text("Solicitud no encontrada.")
            return
        if solicitud["status"] not in ("PENDING_REVIEW", "PENDING_LOCATION"):
            query.edit_message_text(
                "Esta solicitud ya fue procesada.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
            )
            return

        # Validar que tiene coordenadas de entrega
        lat = solicitud.get("lat")
        lng = solicitud.get("lng")
        if not lat or not lng:
            query.edit_message_text(
                "Esta solicitud no tiene ubicacion de entrega confirmada.\n\n"
                "Contacta al cliente para confirmar la direccion antes de crear el pedido.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
            )
            return

        # Validar punto de recogida del aliado
        pickup = get_default_ally_location(ally_id)
        if not pickup or not pickup.get("lat") or not pickup.get("lng"):
            query.edit_message_text(
                "No tienes una ubicacion de recogida configurada.\n\n"
                "Agrega una desde 'Mis ubicaciones' antes de crear pedidos.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
            )
            return

        total_fee = solicitud.get("quoted_price") or 0
        nombre = solicitud["customer_name"] or "Sin nombre"
        telefono = solicitud["customer_phone"] or ""
        direccion = solicitud["delivery_address"] or ""
        ciudad_entrega = solicitud.get("delivery_city") or ""
        barrio_entrega = solicitud.get("delivery_barrio") or ""
        incentivo = solicitud.get("incentivo_cliente") or 0

        preview_lines = [
            "Resumen del pedido a crear:\n",
            "Cliente: {} | {}".format(nombre, telefono),
            "Entrega: {}{}{}".format(
                direccion,
                " - " + barrio_entrega if barrio_entrega else "",
                ", " + ciudad_entrega if ciudad_entrega else "",
            ),
            "Pickup: {} ({})".format(pickup.get("label") or "Principal", pickup.get("address") or ""),
            "Tarifa al courier: ${:,}".format(int(total_fee)),
        ]
        if incentivo:
            preview_lines.append("Incentivo adicional: +${:,}".format(int(incentivo)))
        preview_lines.append("")
        preview_lines.append(
            build_courier_order_preview_text(
                {
                    "id": "preview",
                    "distance_km": float(solicitud.get("distance_km") or 0),
                    "total_fee": int(total_fee or 0),
                    "additional_incentive": int(incentivo or 0),
                    "payment_method": "UNCONFIRMED",
                    "cash_required_amount": 0,
                    "instructions": "",
                    "pickup_address": pickup.get("address") or "",
                    "customer_address": direccion,
                },
                pickup_city_override=pickup.get("city") or "",
                pickup_barrio_override=pickup.get("barrio") or "",
                dropoff_city_override=ciudad_entrega,
                dropoff_barrio_override=barrio_entrega,
            )
        )

        confirm_cb = "alybandeja_confirmargsave_{}".format(request_id) if guardar else "alybandeja_confirmar_{}".format(request_id)
        buttons = [
            [InlineKeyboardButton("Confirmar y publicar", callback_data=confirm_cb)],
            [InlineKeyboardButton("Cancelar", callback_data="alybandeja_ver_{}".format(request_id))],
        ]
        query.edit_message_text("\n".join(preview_lines), reply_markup=InlineKeyboardMarkup(buttons))
        return

    # ---- Confirmar creacion del pedido ----
    if data.startswith("alybandeja_confirmar_") or data.startswith("alybandeja_confirmargsave_"):
        guardar = data.startswith("alybandeja_confirmargsave_")
        request_id = int(data.split("_")[-1])
        solicitud = get_ally_form_request_by_id(request_id, ally_id)
        if not solicitud:
            query.edit_message_text("Solicitud no encontrada.")
            return

        lat = solicitud.get("lat")
        lng = solicitud.get("lng")
        pickup = get_default_ally_location(ally_id)
        if not lat or not lng or not pickup or not pickup.get("lat"):
            query.edit_message_text(
                "No se puede crear el pedido: faltan coordenadas.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
            )
            return

        admin_link = get_approved_admin_link_for_ally(ally_id)
        ally_row = get_ally_by_id(ally_id)
        total_fee = int(solicitud.get("quoted_price") or 0)
        incentivo = int(solicitud.get("incentivo_cliente") or 0)
        ciudad_entrega = solicitud.get("delivery_city") or ""
        barrio_entrega = solicitud.get("delivery_barrio") or ""
        ciudad_pickup = pickup.get("city") or ""
        barrio_pickup = pickup.get("barrio") or ""

        try:
            order_id = create_order(
                ally_id=ally_id,
                customer_name=solicitud["customer_name"],
                customer_phone=solicitud["customer_phone"],
                customer_address=solicitud.get("delivery_address") or "",
                customer_city=ciudad_entrega,
                customer_barrio=barrio_entrega,
                pickup_location_id=pickup.get("id"),
                total_fee=total_fee,
                additional_incentive=incentivo,
                pickup_lat=float(pickup["lat"]),
                pickup_lng=float(pickup["lng"]),
                dropoff_lat=float(lat),
                dropoff_lng=float(lng),
                ally_admin_id_snapshot=admin_link["admin_id"] if admin_link else None,
                quote_source="ALLY_FORM",
            )
        except Exception as e:
            logger.warning("alybandeja_confirmar create_order error: %s", e)
            query.edit_message_text(
                "No se pudo crear el pedido: {}".format(str(e)),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="alybandeja_volver")]])
            )
            return

        # Marcar solicitud como convertida
        try:
            mark_ally_form_request_converted(request_id, ally_id, order_id)
        except Exception:
            pass

        # Guardar en agenda si corresponde
        if guardar:
            try:
                _ally_bandeja_guardar_en_agenda(ally_id, solicitud)
            except Exception:
                pass

        # Publicar pedido a couriers
        published_count = 0
        try:
            published_count = publish_order_to_couriers(
                order_id, ally_id, context,
                pickup_city=ciudad_pickup,
                pickup_barrio=barrio_pickup,
                dropoff_city=ciudad_entrega,
                dropoff_barrio=barrio_entrega,
            )
        except Exception as e:
            logger.warning("alybandeja_confirmar publish error: %s", e)

        query.edit_message_text(
            (
                "Pedido #{} creado y publicado.\n\nBuscando repartidor..."
                if published_count >= 0 else
                "Pedido #{} creado.\n\nLa publicacion quedo bloqueada hasta corregir la direccion visible."
            ).format(order_id),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver a solicitudes", callback_data="alybandeja_volver")]])
        )
        return


