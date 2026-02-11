from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import (
    assign_order_to_courier,
    get_ally_by_id,
    get_ally_location_by_id,
    get_approved_admin_link_for_ally,
    get_courier_by_telegram_id,
    get_default_ally_location,
    get_eligible_couriers_for_order,
    get_order_by_id,
    get_user_by_id,
    set_order_status,
)


def publish_order_to_couriers(order_id, ally_id, context):
    """
    Busca couriers elegibles del equipo del aliado y les envia la oferta.
    Llamada desde main.py despues de crear el pedido.
    """
    admin_link = get_approved_admin_link_for_ally(ally_id)
    if not admin_link:
        print("[WARN] Aliado sin admin aprobado, no se puede publicar pedido")
        return 0

    admin_id = admin_link["admin_id"]
    order = get_order_by_id(order_id)
    if not order:
        return 0

    eligible_couriers = get_eligible_couriers_for_order(admin_id)
    if not eligible_couriers:
        print("[WARN] No se encontraron couriers elegibles para el pedido {}".format(order_id))
        return 0

    offer_text = _build_offer_text(order)
    reply_markup = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Aceptar", callback_data="order_accept_{}".format(order_id)),
            InlineKeyboardButton("Rechazar", callback_data="order_reject_{}".format(order_id)),
        ]
    ])

    sent_count = 0
    for courier in eligible_couriers:
        try:
            if not courier.get("telegram_id"):
                continue

            context.bot.send_message(
                chat_id=courier["telegram_id"],
                text=offer_text,
                reply_markup=reply_markup,
            )
            sent_count += 1
        except Exception as e:
            print("[WARN] No se pudo enviar oferta a courier {}: {}".format(courier["courier_id"], e))

    if sent_count > 0:
        set_order_status(order_id, "PUBLISHED", "published_at")

    return sent_count


def order_courier_callback(update, context):
    """
    Maneja botones de ofertas para couriers.
    Pattern: ^order_(accept|reject)_\\d+$
    """
    query = update.callback_query
    data = query.data or ""
    query.answer()

    if data.startswith("order_accept_"):
        order_id = int(data.replace("order_accept_", ""))
        return _handle_accept(update, context, order_id)
    if data.startswith("order_reject_"):
        order_id = int(data.replace("order_reject_", ""))
        return _handle_reject(update, context, order_id)
    return None


def _handle_accept(update, context, order_id):
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    if order["status"] != "PUBLISHED":
        query.edit_message_text("Esta oferta ya fue tomada por otro repartidor.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        query.edit_message_text("No se encontro tu perfil de repartidor.")
        return

    if courier["status"] != "APPROVED":
        query.edit_message_text("Tu perfil de repartidor no esta activo.")
        return

    admin_link = get_approved_admin_link_for_ally(order["ally_id"])
    if not admin_link:
        query.edit_message_text("Esta oferta ya no esta disponible.")
        return

    admin_id = admin_link["admin_id"]
    eligible_ids = _get_eligible_courier_ids(admin_id)
    courier_id = courier["id"]
    if courier_id not in eligible_ids:
        query.edit_message_text("No estas habilitado para aceptar esta oferta.")
        return

    assign_order_to_courier(order_id, courier_id)
    courier_name = courier["full_name"] or "Repartidor"

    query.edit_message_text(
        "Pedido #{} aceptado.\n\n"
        "Recoge en: {}\n"
        "Entrega en: {}\n"
        "Cliente: {}\n"
        "Telefono cliente: {}\n\n"
        "Dirigete al punto de recogida.".format(
            order_id,
            _get_pickup_address(order),
            order["customer_address"] or "No disponible",
            order["customer_name"] or "No disponible",
            order["customer_phone"] or "No disponible",
        )
    )

    _notify_ally_order_accepted(context, order, courier_name)
    _notify_other_couriers_taken(context, order_id, admin_id, courier_id)


def _handle_reject(update, context, order_id):
    query = update.callback_query
    query.edit_message_text("Oferta #{} rechazada.".format(order_id))


def _build_offer_text(order):
    """Construye el texto de oferta para el courier."""
    pickup_address = _get_pickup_address(order)
    distance_km = order["distance_km"] or 0
    total_fee = int(order["total_fee"] or 0)

    text = (
        "OFERTA DISPONIBLE\n\n"
        "Pedido: #{}\n"
        "Recoge en: {}\n"
        "Entrega en: {}\n"
        "Distancia: {:.1f} km\n"
        "Pago: ${:,}\n"
    ).format(
        order["id"],
        pickup_address,
        order["customer_address"] or "No disponible",
        distance_km,
        total_fee,
    )

    cash_amount = order["cash_required_amount"] or 0
    if order["requires_cash"] and cash_amount > 0:
        text += "Base requerida: ${:,}\n".format(int(cash_amount))
        text += "\nADVERTENCIA: Si no tienes base suficiente, NO tomes este servicio.\n"

    instructions = order["instructions"] or ""
    if instructions.strip():
        text += "\nInstrucciones: {}\n".format(instructions.strip())

    return text


def _get_pickup_address(order):
    """Obtiene direccion de recogida usando pickup_location_id o default del aliado."""
    pickup_location_id = order["pickup_location_id"]
    ally_id = order["ally_id"]

    if pickup_location_id and ally_id:
        location = get_ally_location_by_id(pickup_location_id, ally_id)
        if location:
            return location.get("address") or "No disponible"

    default_loc = get_default_ally_location(ally_id)
    if default_loc:
        return default_loc.get("address", "No disponible")
    return "No disponible"


def _get_eligible_courier_ids(admin_id):
    eligible = get_eligible_couriers_for_order(admin_id)
    return {courier["courier_id"] for courier in eligible}


def _notify_ally_order_accepted(context, order, courier_name):
    try:
        ally = get_ally_by_id(order["ally_id"])
        if not ally:
            return

        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user.get("telegram_id"):
            return

        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "Tu pedido #{} fue aceptado por el repartidor {}.\n"
                "El repartidor se dirige al punto de recogida."
            ).format(order["id"], courier_name),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar al aliado: {}".format(e))


def _notify_other_couriers_taken(context, order_id, admin_id, accepted_courier_id):
    eligible = get_eligible_couriers_for_order(admin_id)
    for courier in eligible:
        if courier["courier_id"] == accepted_courier_id:
            continue
        try:
            if not courier.get("telegram_id"):
                continue

            context.bot.send_message(
                chat_id=courier["telegram_id"],
                text="La oferta #{} ya fue tomada por otro repartidor.".format(order_id),
            )
        except Exception as e:
            print("[WARN] No se pudo notificar cierre de oferta a courier {}: {}".format(courier["courier_id"], e))
