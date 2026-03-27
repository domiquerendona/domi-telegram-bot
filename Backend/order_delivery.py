from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import (
    assign_order_to_courier,
    cancel_order,
    get_platform_admin,
    create_offer_queue,
    delete_offer_queue,
    get_all_orders,
    get_active_orders_by_ally,
    get_admin_by_id,
    get_ally_by_id,
    get_ally_by_user_id,
    get_ally_location_by_id,
    get_approved_admin_link_for_ally,
    get_approved_admin_link_for_courier,
    get_courier_by_id,
    get_courier_by_telegram_id,
    get_current_offer_for_order,
    get_default_ally_location,
    get_eligible_couriers_for_order,
    get_next_pending_offer,
    get_order_by_id,
    get_orders_by_ally,
    get_ally_orders_between,
    get_ally_routes_between,
    get_orders_by_admin_team,
    get_setting,
    get_user_by_telegram_id,
    get_user_by_id,
    mark_offer_as_offered,
    mark_offer_response,
    release_order_from_courier,
    get_order_pickup_confirmation,
    upsert_order_pickup_confirmation,
    review_order_pickup_confirmation,
    reset_offer_queue,
    clear_offer_queue,
    set_order_status,
    upsert_order_accounting_settlement,
    get_courier_link_balance,
    # Rutas multi-parada
    get_route_by_id,
    get_active_routes_by_ally,
    get_route_destinations,
    get_pending_route_stops,
    reorder_route_destinations,
    update_route_status,
    assign_route_to_courier,
    release_route_from_courier,
    deliver_route_stop,
    cancel_route,
    create_route_offer_queue,
    get_next_pending_route_offer,
    mark_route_offer_as_offered,
    mark_route_offer_response,
    get_current_route_offer,
    delete_route_offer_queue,
    reset_route_offer_queue,
)
from datetime import datetime, timezone, timedelta
from db import (
    add_courier_rating,
    block_courier_for_ally,
    deactivate_courier,
    set_courier_arrived,
    set_courier_accepted_location,
    get_active_order_for_courier,
    get_active_route_for_courier,
    get_courier_delivery_time_stats,
    get_approved_admin_id_for_courier,
    get_admin_by_telegram_id,
    create_order_support_request,
    get_pending_support_request,
    resolve_support_request,
    cancel_route_stop,
)
from services import apply_service_fee, check_service_fee_available, haversine_km, liquidate_route_additional_stops_fee, add_route_incentive, check_ally_active_subscription


def _format_duration(seconds):
    """Convierte segundos a texto legible: 'X min' o 'Xh Ymin'. Retorna 'N/D' si es None."""
    if seconds is None or seconds < 0:
        return "N/D"
    minutes = int(seconds) // 60
    if minutes < 60:
        return "{} min".format(minutes)
    hours = minutes // 60
    mins = minutes % 60
    return "{}h {}min".format(hours, mins)


def _get_order_durations(order, delivered_now=False):
    """
    Calcula duraciones de cada etapa del pedido.
    delivered_now=True: usa datetime.now(timezone.utc).replace(tzinfo=None) como delivered_at (recien marcado DELIVERED).
    Retorna dict con claves: llegada_aliado, entrega_cliente, tiempo_total (en segundos).
    Cada clave solo se incluye si ambos extremos del intervalo estan disponibles.
    """
    def _parse(val):
        if val is None:
            return None
        if hasattr(val, 'timetuple'):  # ya es objeto datetime (Postgres)
            return val
        s = str(val).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                return datetime.strptime(s[:len(fmt)], fmt)
            except ValueError:
                continue
        return None

    from db import _row_value as _rv
    accepted    = _parse(_rv(order, "accepted_at"))
    arrived     = _parse(_rv(order, "courier_arrived_at"))
    pickup_conf = _parse(_rv(order, "pickup_confirmed_at"))
    delivered   = datetime.now(timezone.utc).replace(tzinfo=None) if delivered_now else _parse(_rv(order, "delivered_at"))

    result = {}
    if accepted and arrived:
        result["llegada_aliado"] = (arrived - accepted).total_seconds()
    if pickup_conf and delivered:
        result["entrega_cliente"] = (delivered - pickup_conf).total_seconds()
    if accepted and delivered:
        result["tiempo_total"] = (delivered - accepted).total_seconds()
    return result


OFFER_TIMEOUT_SECONDS = 30
MAX_CYCLE_SECONDS = 600  # 10 minutos

ARRIVAL_INACTIVITY_SECONDS = 5 * 60    # 5 min: Rappi-style
ARRIVAL_WARN_SECONDS = 15 * 60         # 15 min: advertir al aliado
ARRIVAL_DEADLINE_SECONDS = 20 * 60     # 20 min: auto-liberar
ARRIVAL_RADIUS_KM = 0.1                # 100 metros
ARRIVAL_MOVEMENT_THRESHOLD_KM = 0.05   # 50 metros de movimiento mínimo hacia pickup
OFFER_NO_RESPONSE_SECONDS = 300        # 5 min sin respuesta → sugerir incentivo
DELIVERY_REMINDER_SECONDS = 30 * 60   # 30 min en PICKED_UP → recordar al repartidor
DELIVERY_ADMIN_ALERT_SECONDS = 60 * 60  # 60 min en PICKED_UP → alertar al admin
DELIVERY_RADIUS_KM = 0.1               # 100 metros para validar entrega GPS

GPS_INACTIVE_MSG = (
    "Tu ubicacion GPS no esta activa.\n\n"
    "Para continuar, activa tu ubicacion en vivo en Telegram:\n"
    "1. Abre el chat con el bot.\n"
    "2. Toca el clip (adjuntar).\n"
    "3. Selecciona \"Ubicacion\".\n"
    "4. Elige \"Compartir ubicacion en vivo\".\n\n"
    "Una vez activa tu ubicacion podras continuar con el servicio."
)


def _is_courier_gps_active(courier):
    """Retorna True si el courier tiene GPS activo con coordenadas validas."""
    active = int(_row_value(courier, "live_location_active", 0) or 0)
    lat = _row_value(courier, "live_lat")
    lng = _row_value(courier, "live_lng")
    return active == 1 and lat is not None and lng is not None


def _offer_reply_markup(order_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Aceptar", callback_data="order_accept_{}".format(order_id)),
            InlineKeyboardButton("Rechazar", callback_data="order_reject_{}".format(order_id)),
        ],
        [InlineKeyboardButton("Estoy ocupado", callback_data="order_busy_{}".format(order_id))],
    ])



def _cancel_offer_jobs(context, order_id, queue_id):
    timeout_jobs = context.job_queue.get_jobs_by_name(
        "offer_timeout_{}_{}".format(order_id, queue_id)
    )
    for job in timeout_jobs:
        job.schedule_removal()


def _cancel_arrival_jobs(context, order_id):
    """Cancela los 3 jobs de tracking de llegada y limpia prompts temporales del pedido."""
    for name in [
        "arr_inactive_{}".format(order_id),
        "arr_warn_{}".format(order_id),
        "arr_deadline_{}".format(order_id),
    ]:
        for job in context.job_queue.get_jobs_by_name(name):
            job.schedule_removal()
    context.bot_data.get("arrival_manual_prompted", {}).pop(order_id, None)


def _cancel_delivery_reminder_jobs(context, order_id):
    """Cancela los jobs de recordatorio de entrega T+30 y alerta admin T+60."""
    for name in [
        "delivery_reminder_{}".format(order_id),
        "delivery_admin_alert_{}".format(order_id),
    ]:
        for job in context.job_queue.get_jobs_by_name(name):
            job.schedule_removal()


def _delivery_reminder_job(context):
    """T+30: recuerda al repartidor que tiene un pedido en curso sin finalizar."""
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PICKED_UP":
        return
    courier = get_courier_by_id(order["courier_id"])
    if not courier:
        return
    courier_user = get_user_by_id(courier["user_id"])
    if not courier_user:
        return
    try:
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text="Recuerda finalizar el pedido en curso #{}. "
                 "Presiona \"Pedidos en curso\" cuando hayas entregado.".format(order_id),
        )
    except Exception as e:
        print("[WARN] No se pudo enviar recordatorio de entrega al repartidor (pedido {}): {}".format(order_id, e))


def _delivery_admin_alert_job(context):
    """T+60: notifica al admin del equipo que el pedido lleva mucho tiempo en curso."""
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PICKED_UP":
        return
    courier_id = order["courier_id"]
    admin_id = get_approved_admin_id_for_courier(courier_id)
    if not admin_id:
        return
    admin = get_admin_by_id(admin_id)
    if not admin:
        return
    admin_user = get_user_by_id(admin["user_id"])
    if not admin_user:
        return
    courier = get_courier_by_id(courier_id)
    courier_name = courier["full_name"] if courier else "Repartidor #{}".format(courier_id)
    try:
        context.bot.send_message(
            chat_id=admin_user["telegram_id"],
            text="El repartidor {} lleva mas de 60 minutos con el pedido en curso #{}. "
                 "Verifica que haya finalizado la entrega.".format(courier_name, order_id),
        )
    except Exception as e:
        print("[WARN] No se pudo enviar alerta de entrega al admin (pedido {}): {}".format(order_id, e))


def _cancel_no_response_job(context, order_id):
    """Cancela el job de sugerencia de incentivo T+5 para un pedido."""
    for job in context.job_queue.get_jobs_by_name("offer_no_response_{}".format(order_id)):
        job.schedule_removal()


def _cancel_route_no_response_job(context, route_id):
    """Cancela el job de sugerencia de incentivo T+5 para una ruta."""
    for job in context.job_queue.get_jobs_by_name("route_no_response_{}".format(route_id)):
        job.schedule_removal()


def _cancel_order_expire_job(context, order_id):
    """Cancela el job de expiración automática T+10 para un pedido."""
    for job in context.job_queue.get_jobs_by_name("order_expire_{}".format(order_id)):
        job.schedule_removal()


def _courier_is_within_pickup_radius(order, courier):
    """Retorna True si el courier esta dentro del radio valido para confirmar llegada."""
    pickup_lat, pickup_lng = _get_pickup_coords(order)
    if pickup_lat is None or pickup_lng is None:
        return False

    courier_lat = _row_value(courier, "live_lat") or _row_value(courier, "residence_lat")
    courier_lng = _row_value(courier, "live_lng") or _row_value(courier, "residence_lng")
    if courier_lat is None or courier_lng is None:
        return False

    dist_km = haversine_km(
        float(courier_lat),
        float(courier_lng),
        float(pickup_lat),
        float(pickup_lng),
    )
    return dist_km <= ARRIVAL_RADIUS_KM


def _notify_courier_arrival_detected(context, order, courier):
    """
    Notifica una sola vez por pedido que el GPS detecto cercania y que la llegada
    debe confirmarse manualmente desde el boton del courier.
    """
    courier_user = get_user_by_id(courier["user_id"]) if courier else None
    if not courier_user or not courier_user["telegram_id"]:
        return

    prompted = context.bot_data.setdefault("arrival_manual_prompted", {})
    if prompted.get(order["id"]):
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirmar llegada", callback_data="order_pickup_{}".format(order["id"]))],
        [InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order["id"]))],
    ])
    try:
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=(
                "Detectamos que estas cerca del punto de recogida del pedido #{}.\n\n"
                "Confirma tu llegada manualmente para avisarle al aliado."
            ).format(order["id"]),
            reply_markup=keyboard,
        )
        prompted[order["id"]] = True
    except Exception:
        pass


def _parse_dt(val):
    if val is None:
        return None
    if hasattr(val, "timetuple"):  # ya es objeto datetime (Postgres)
        return val
    s = str(val).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(s[:len(fmt)], fmt)
        except ValueError:
            continue
    return None


def _to_naive_utc(dt):
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        try:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            return dt.replace(tzinfo=None)
    return dt


def _build_cycle_info_for_expire(order):
    ally_id = order.get("ally_id") if hasattr(order, "get") else order["ally_id"]
    creator_admin_id = order.get("creator_admin_id") if hasattr(order, "get") else order["creator_admin_id"]

    admin_id = None
    if creator_admin_id:
        admin_id = int(creator_admin_id)
    elif ally_id is not None:
        try:
            admin_link = get_approved_admin_link_for_ally(int(ally_id))
            admin_id = admin_link["admin_id"] if admin_link else None
        except Exception:
            admin_id = None

    return {"ally_id": ally_id, "admin_id": admin_id}


def _schedule_order_expire_job(context, order_id):
    """
    Programa expiración automática del pedido a T+10 desde created_at.
    No debe extenderse por re-ofertas o reinicios del ciclo.
    """
    _cancel_order_expire_job(context, order_id)

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return

    created_at = _to_naive_utc(_parse_dt(order.get("created_at") if hasattr(order, "get") else order["created_at"]))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    elapsed = 0
    if created_at:
        try:
            elapsed = int(max(0, (now - created_at).total_seconds()))
        except Exception:
            elapsed = 0

    remaining = MAX_CYCLE_SECONDS - elapsed
    if remaining <= 0:
        cycle_info = context.bot_data.get("offer_cycles", {}).get(order_id) or _build_cycle_info_for_expire(order)
        _expire_order(order_id, cycle_info, context)
        return

    context.job_queue.run_once(
        _order_expire_job,
        remaining,
        context={"order_id": order_id},
        name="order_expire_{}".format(order_id),
    )


def _order_expire_job(context):
    """Job T+10: si el pedido sigue PUBLISHED, expira automáticamente."""
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return

    cycle_info = context.bot_data.get("offer_cycles", {}).get(order_id) or _build_cycle_info_for_expire(order)
    _expire_order(order_id, cycle_info, context)


def _offer_no_response_job(context):
    """Job T+5: si el pedido sigue PUBLISHED, sugiere al creador que agregue incentivo."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return

    # Obtener telegram_id del creador (aliado o admin)
    creator_chat_id = None
    try:
        creator_admin_id = order.get("creator_admin_id") if hasattr(order, "get") else order["creator_admin_id"]
        if creator_admin_id:
            admin = get_admin_by_id(int(creator_admin_id))
            if admin:
                user = get_user_by_id(admin["user_id"])
                if user:
                    creator_chat_id = int(user["telegram_id"])
        elif order["ally_id"]:
            ally = get_ally_by_id(int(order["ally_id"]))
            if ally:
                user = get_user_by_id(ally["user_id"])
                if user:
                    creator_chat_id = int(user["telegram_id"])
    except Exception as e:
        print("[T+5] Error obteniendo creador para pedido {}: {}".format(order_id, e))
        return

    if not creator_chat_id:
        return

    total_fee = int(order["total_fee"] or 0)
    incentive = int(order["additional_incentive"] or 0)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("+$1,500", callback_data="offer_inc_{}x1500".format(order_id)),
            InlineKeyboardButton("+$2,000", callback_data="offer_inc_{}x2000".format(order_id)),
            InlineKeyboardButton("+$3,000", callback_data="offer_inc_{}x3000".format(order_id)),
        ],
        [InlineKeyboardButton("Otro monto", callback_data="offer_inc_otro_{}".format(order_id))],
    ])

    msg = (
        "Pedido #{} lleva 5 minutos sin ser aceptado.\n\n"
        "Tarifa actual: ${:,}".format(order_id, total_fee)
    )
    if incentive > 0:
        msg += " (incluye incentivo de ${:,})".format(incentive)
    msg += (
        "\n\nEs posible que haya alta demanda. "
        "Los repartidores suelen preferir los pedidos mejor pagos.\n"
        "Agrega un incentivo para agilizar la toma:"
    )

    try:
        context.bot.send_message(
            chat_id=creator_chat_id,
            text=msg,
            reply_markup=keyboard,
        )
    except Exception as e:
        print("[T+5] Error enviando sugerencia para pedido {}: {}".format(order_id, e))


def repost_order_to_couriers(order_id, context):
    """Re-oferta un pedido a todos los couriers activos (usado tras agregar incentivo).

    Limpia la cola existente, resetea los excluded_couriers y relanza el ciclo de ofertas.
    No verifica saldo del aliado/admin (ya fue verificado al crear el pedido).
    """
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return 0

    # Limpiar cola existente y excluded_couriers en memoria
    clear_offer_queue(order_id)
    context.bot_data.get("offer_cycles", {}).pop(order_id, None)

    ally_id = order["ally_id"]
    creator_admin_id = order.get("creator_admin_id") if hasattr(order, "get") else order["creator_admin_id"]
    admin_id_override = None
    if creator_admin_id:
        admin_id_override = int(creator_admin_id)

    # Re-lanzar ciclo sin verificar saldo (skip_fee_check=True)
    count = publish_order_to_couriers(
        order_id=order_id,
        ally_id=ally_id,
        context=context,
        admin_id_override=admin_id_override,
        skip_fee_check=True,
    )
    return count


def _route_no_response_job(context):
    """Job T+5: si la ruta sigue PUBLISHED, sugiere al aliado que agregue incentivo."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    data = context.job.context or {}
    route_id = data.get("route_id")
    if not route_id:
        return

    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        return

    creator_chat_id = None
    try:
        ally_id = route["ally_id"]
        if ally_id:
            ally = get_ally_by_id(int(ally_id))
            if ally:
                user = get_user_by_id(ally["user_id"])
                if user:
                    creator_chat_id = int(user["telegram_id"])
    except Exception as e:
        print("[T+5 ruta] Error obteniendo creador para ruta {}: {}".format(route_id, e))
        return

    if not creator_chat_id:
        return

    total_fee = int(route["total_fee"] or 0)
    incentive = int(route["additional_incentive"] or 0)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("+$1,500", callback_data="ruta_inc_{}x1500".format(route_id)),
            InlineKeyboardButton("+$2,000", callback_data="ruta_inc_{}x2000".format(route_id)),
            InlineKeyboardButton("+$3,000", callback_data="ruta_inc_{}x3000".format(route_id)),
        ],
        [InlineKeyboardButton("Otro monto", callback_data="ruta_inc_otro_{}".format(route_id))],
    ])

    msg = (
        "Ruta #{} lleva 5 minutos sin ser aceptada.\n\n"
        "Tarifa actual al repartidor: ${:,}".format(route_id, total_fee)
    )
    if incentive > 0:
        msg += " (incluye incentivo de ${:,})".format(incentive)
    msg += (
        "\n\nEs posible que haya alta demanda. "
        "Agrega un incentivo para agilizar la toma:"
    )

    try:
        context.bot.send_message(
            chat_id=creator_chat_id,
            text=msg,
            reply_markup=keyboard,
        )
    except Exception as e:
        print("[T+5 ruta] Error enviando sugerencia para ruta {}: {}".format(route_id, e))


def repost_route_to_couriers(route_id, context):
    """Re-oferta una ruta a todos los couriers con saldo (usado tras agregar incentivo).

    Limpia la cola existente y relanza el ciclo de ofertas.
    """
    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        return 0

    delete_route_offer_queue(route_id)
    context.bot_data.get("route_offer_cycles", {}).pop(route_id, None)

    ally_id = route["ally_id"]
    admin_id_override = _row_value(route, "ally_admin_id_snapshot")
    if admin_id_override:
        admin_id_override = int(admin_id_override)

    count = publish_route_to_couriers(
        route_id=route_id,
        ally_id=ally_id,
        context=context,
        admin_id_override=admin_id_override,
    )
    return count


def _notify_recharge_needed_to_ally(context, ally_id):
    try:
        ally = get_ally_by_id(ally_id)
        if not ally:
            return
        user = get_user_by_id(ally["user_id"])
        if not user:
            return
        context.bot.send_message(
            chat_id=user["telegram_id"],
            text="No se puede ofrecer el servicio porque tu saldo es insuficiente. Recarga para continuar operando.",
        )
    except Exception as e:
        print("[WARN] No se pudo notificar saldo insuficiente al aliado {}: {}".format(ally_id, e))


def _notify_recharge_needed_to_admin(context, admin_id):
    try:
        admin = get_admin_by_id(admin_id)
        if not admin:
            return
        user = get_user_by_id(admin["user_id"])
        if not user:
            return
        context.bot.send_message(
            chat_id=user["telegram_id"],
            text="No se puede ofrecer servicio porque tu saldo de administrador es insuficiente. Recarga para seguir operando.",
        )
    except Exception as e:
        print("[WARN] No se pudo notificar saldo insuficiente al admin {}: {}".format(admin_id, e))


def _notify_recharge_needed_to_courier(context, courier_id):
    try:
        courier = get_courier_by_id(courier_id)
        if not courier:
            return
        user = get_user_by_id(courier["user_id"])
        if not user:
            return
        context.bot.send_message(
            chat_id=user["telegram_id"],
            text="No recibiste oferta porque tu saldo es insuficiente. Recarga para volver a operar.",
        )
    except Exception as e:
        print("[WARN] No se pudo notificar saldo insuficiente al courier {}: {}".format(courier_id, e))


def publish_order_to_couriers(
    order_id,
    ally_id,
    context,
    admin_id_override=None,
    pickup_city=None,
    pickup_barrio=None,
    dropoff_city=None,
    dropoff_barrio=None,
    skip_fee_check=False,
):
    """
    Inicia el ciclo secuencial de ofertas para un pedido.
    1. Busca couriers elegibles (filtrados por veto, base, activación).
    2. Crea la cola de ofertas en BD.
    3. Envía la primera oferta.
    4. Programa timeout de 30s con JobQueue.

    skip_fee_check=True: omitir verificación de saldo (usado en re-oferta tras incentivo).
    ally_id=None: pedido especial creado por admin (no aplica fee de aliado).
    """
    admin_id = None
    if admin_id_override is not None:
        admin_id = int(admin_id_override)
    elif ally_id is not None:
        admin_link = get_approved_admin_link_for_ally(ally_id)
        if not admin_link:
            print("[WARN] Aliado sin admin aprobado, no se puede publicar pedido")
            return 0
        admin_id = admin_link["admin_id"]
    order = get_order_by_id(order_id)
    if not order:
        return 0

    # Verificacion previa de saldo del aliado y del admin antes de ofertar.
    # Omitida para pedidos de admin (no hay aliado) y en re-ofertas (ya fue verificado).
    if ally_id is not None and not skip_fee_check:
        ally_ok, ally_code = check_service_fee_available(
            target_type="ALLY",
            target_id=ally_id,
            admin_id=admin_id,
        )
        if not ally_ok:
            print("[WARN] Pedido {} sin oferta por saldo aliado/admin: {}".format(order_id, ally_code))
            _notify_recharge_needed_to_ally(context, ally_id)
            if ally_code == "ADMIN_SIN_SALDO":
                _notify_recharge_needed_to_admin(context, admin_id)
            return 0

    requires_cash = bool(order["requires_cash"])
    cash_amount = int(order["cash_required_amount"] or 0)

    # Obtener coordenadas del pickup para asignacion inteligente por cercania
    p_lat = order["pickup_lat"] if "pickup_lat" in order.keys() else None
    p_lng = order["pickup_lng"] if "pickup_lng" in order.keys() else None
    pickup_location_id = order["pickup_location_id"] if "pickup_location_id" in order.keys() else None
    pickup_loc_row = None
    # Solo buscar en ally_locations si hay ally_id (pedidos de aliado)
    if p_lat is None and pickup_location_id and ally_id is not None:
        loc = get_ally_location_by_id(pickup_location_id, ally_id)
        if loc:
            pickup_loc_row = loc
            p_lat = loc["lat"] if "lat" in loc.keys() else None
            p_lng = loc["lng"] if "lng" in loc.keys() else None

    # Calcular distancia pickup → dropoff para filtrar bicicletas en pedidos largos
    _order_distance_km = None
    d_lat = order["dropoff_lat"] if "dropoff_lat" in order.keys() else None
    d_lng = order["dropoff_lng"] if "dropoff_lng" in order.keys() else None
    if p_lat is not None and p_lng is not None and d_lat is not None and d_lng is not None:
        import math as _math
        _dlat = _math.radians(d_lat - p_lat)
        _dlng = _math.radians(d_lng - p_lng)
        _a = (_math.sin(_dlat / 2) ** 2
              + _math.cos(_math.radians(p_lat)) * _math.cos(_math.radians(d_lat))
              * _math.sin(_dlng / 2) ** 2)
        _order_distance_km = 6371.0 * 2 * _math.atan2(_math.sqrt(_a), _math.sqrt(1 - _a))

    # Red cooperativa: buscar en TODOS los couriers activos, sin filtro de equipo.
    # Cada courier opera bajo su propio admin; el fee se cobra a cada uno por separado.
    eligible = get_eligible_couriers_for_order(
        ally_id=ally_id,
        requires_cash=requires_cash,
        cash_required_amount=cash_amount,
        pickup_lat=p_lat,
        pickup_lng=p_lng,
        order_distance_km=_order_distance_km,
    )
    if not eligible:
        print("[WARN] No hay couriers elegibles para pedido {}".format(order_id))
        return 0

    # Verificacion previa de saldo por courier usando el admin PROPIO de cada courier.
    filtered = []
    couriers_without_balance = []
    for c in eligible:
        courier_id = c["courier_id"]
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id is None:
            couriers_without_balance.append(courier_id)
            continue
        ok, code = check_service_fee_available(
            target_type="COURIER",
            target_id=courier_id,
            admin_id=courier_admin_id,
        )
        if ok:
            filtered.append(c)
        else:
            couriers_without_balance.append(courier_id)

    for courier_id in couriers_without_balance:
        _notify_recharge_needed_to_courier(context, courier_id)

    if not filtered:
        print("[WARN] Pedido {} sin oferta: todos los couriers sin saldo operativo".format(order_id))
        if ally_id is not None:
            _notify_recharge_needed_to_ally(context, ally_id)
        return 0

    courier_ids = [c["courier_id"] for c in filtered]
    create_offer_queue(order_id, courier_ids)
    set_order_status(order_id, "PUBLISHED", "published_at")

    # Guardar datos del ciclo para re-consulta en reintentos
    if pickup_loc_row is None and pickup_location_id and ally_id is not None:
        try:
            pickup_loc_row = get_ally_location_by_id(pickup_location_id, ally_id)
        except Exception:
            pickup_loc_row = None

    if pickup_city is None or pickup_barrio is None:
        if pickup_loc_row:
            pickup_city = pickup_city if pickup_city is not None else pickup_loc_row["city"]
            pickup_barrio = pickup_barrio if pickup_barrio is not None else pickup_loc_row["barrio"]
        elif ally_id is not None:
            default_loc = get_default_ally_location(ally_id)
            if default_loc:
                pickup_city = pickup_city if pickup_city is not None else default_loc["city"]
                pickup_barrio = pickup_barrio if pickup_barrio is not None else default_loc["barrio"]

    if dropoff_city is None:
        dropoff_city = _row_value(order, "customer_city")
    if dropoff_barrio is None:
        dropoff_barrio = _row_value(order, "customer_barrio")

    context.bot_data.setdefault("offer_cycles", {})[order_id] = {
        "started_at": __import__("time").time(),
        "admin_id": admin_id,
        "ally_id": ally_id,
        "pickup_lat": p_lat,
        "pickup_lng": p_lng,
        "pickup_city": pickup_city,
        "pickup_barrio": pickup_barrio,
        "dropoff_city": dropoff_city,
        "dropoff_barrio": dropoff_barrio,
        "requires_cash": requires_cash,
        "cash_amount": cash_amount,
        "excluded_couriers": set(),
    }

    _send_next_offer(order_id, context)

    # Programar sugerencia de incentivo si nadie acepta en T+5
    _cancel_no_response_job(context, order_id)
    context.job_queue.run_once(
        _offer_no_response_job,
        OFFER_NO_RESPONSE_SECONDS,
        context={"order_id": order_id},
        name="offer_no_response_{}".format(order_id),
    )

    # Programar expiración automática T+10 (desde created_at)
    _schedule_order_expire_job(context, order_id)

    return len(courier_ids)


def _send_next_offer(order_id, context):
    """Envía la oferta al siguiente courier en la cola."""
    order = get_order_by_id(order_id)
    if not order or order["status"] not in ("PUBLISHED",):
        return

    next_offer = get_next_pending_offer(order_id)
    if not next_offer:
        # No quedan couriers en la cola, intentar reiniciar ciclo
        _try_restart_cycle(order_id, context)
        return

    mark_offer_as_offered(next_offer["queue_id"])

    pickup_lat, pickup_lng = _get_pickup_coords(order)

    # Calcular distancia y ETA del courier al punto de recogida
    courier_dist_km = None
    try:
        courier_data = get_courier_by_id(next_offer["courier_id"])
        if courier_data:
            c_lat = _row_value(courier_data, "live_lat") or _row_value(courier_data, "residence_lat")
            c_lng = _row_value(courier_data, "live_lng") or _row_value(courier_data, "residence_lng")
            if c_lat and c_lng and pickup_lat is not None and pickup_lng is not None:
                courier_dist_km = haversine_km(float(c_lat), float(c_lng),
                                               float(pickup_lat), float(pickup_lng))
    except Exception:
        pass

    cycle_info = context.bot_data.get("offer_cycles", {}).get(order_id, {}) or {}
    offer_text = "SERVICIO DISPONIBLE\n\n" + _build_offer_text(
        order,
        courier_dist_km=courier_dist_km,
        pickup_city_override=cycle_info.get("pickup_city"),
        pickup_barrio_override=cycle_info.get("pickup_barrio"),
        dropoff_city_override=cycle_info.get("dropoff_city"),
        dropoff_barrio_override=cycle_info.get("dropoff_barrio"),
    )
    reply_markup = _offer_reply_markup(order_id)

    try:
        msg = context.bot.send_message(
            chat_id=next_offer["telegram_id"],
            text=offer_text,
            reply_markup=reply_markup,
        )
        # Guardar message_id para poder editar al expirar
        context.bot_data.setdefault("offer_messages", {})[order_id] = {
            "chat_id": next_offer["telegram_id"],
            "message_id": msg.message_id,
        }
    except Exception as e:
        print("[WARN] No se pudo enviar oferta a courier {}: {}".format(next_offer["courier_id"], e))
        mark_offer_response(next_offer["queue_id"], "EXPIRED")
        _send_next_offer(order_id, context)
        return

    # Programar timeout de 30 segundos
    context.job_queue.run_once(
        _offer_timeout_job,
        OFFER_TIMEOUT_SECONDS,
        context={"order_id": order_id, "queue_id": next_offer["queue_id"]},
        name="offer_timeout_{}_{}".format(order_id, next_offer["queue_id"]),
    )



def _offer_timeout_job(context):
    """Job ejecutado cuando expira el timeout de 30s para un courier."""
    job_data = context.job.context
    order_id = job_data["order_id"]
    queue_id = job_data["queue_id"]

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return

    current = get_current_offer_for_order(order_id)
    if not current or current["queue_id"] != queue_id:
        return

    _cancel_offer_jobs(context, order_id, queue_id)
    mark_offer_response(queue_id, "EXPIRED")

    # Editar mensaje del courier para indicar que expiró
    msg_info = context.bot_data.get("offer_messages", {}).get(order_id)
    if msg_info:
        try:
            context.bot.edit_message_text(
                chat_id=msg_info["chat_id"],
                message_id=msg_info["message_id"],
                text="Oferta #{} expirada. No respondiste a tiempo.".format(order_id),
            )
        except Exception:
            pass

    _send_next_offer(order_id, context)


def _try_restart_cycle(order_id, context):
    """Reinicia el ciclo re-consultando couriers elegibles actuales dentro del radio.
    Captura repartidores que hayan entrado al radio desde el inicio del ciclo."""
    cycle_info = context.bot_data.get("offer_cycles", {}).get(order_id)
    if not cycle_info:
        return

    import time
    elapsed = time.time() - cycle_info["started_at"]

    if elapsed >= MAX_CYCLE_SECONDS:
        _expire_order(order_id, cycle_info, context)
        return

    admin_id = cycle_info["admin_id"]
    ally_id = cycle_info["ally_id"]
    p_lat = cycle_info.get("pickup_lat")
    p_lng = cycle_info.get("pickup_lng")
    requires_cash = cycle_info.get("requires_cash", False)
    cash_amount = cycle_info.get("cash_amount", 0)
    excluded = cycle_info.get("excluded_couriers", set())

    fresh = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=requires_cash,
        cash_required_amount=cash_amount,
        pickup_lat=p_lat,
        pickup_lng=p_lng,
    )
    courier_ids = [c["courier_id"] for c in fresh if c["courier_id"] not in excluded]

    if not courier_ids:
        _expire_order(order_id, cycle_info, context)
        return

    delete_offer_queue(order_id)
    create_offer_queue(order_id, courier_ids)
    _send_next_offer(order_id, context)


def _expire_order(order_id, cycle_info, context):
    """Nadie acepto en 10 minutos. Cancela el pedido sin cobrar al aliado."""
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return

    _cancel_no_response_job(context, order_id)
    _cancel_order_expire_job(context, order_id)
    current = get_current_offer_for_order(order_id)
    if current:
        _cancel_offer_jobs(context, order_id, current["queue_id"])

    cancel_order(order_id, "SYSTEM")
    delete_offer_queue(order_id)

    # Limpiar bot_data
    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    context.bot_data.get("offer_messages", {}).pop(order_id, None)

    ally_id = cycle_info["ally_id"]

    # Notificar sin cobro: si nadie toma el servicio, no se cobra al aliado
    if ally_id is not None:
        try:
            ally = get_ally_by_id(ally_id)
            if ally:
                ally_user = get_user_by_id(ally["user_id"])
                if ally_user and ally_user["telegram_id"]:
                    context.bot.send_message(
                        chat_id=ally_user["telegram_id"],
                        text=(
                            "El pedido #{} no fue tomado por ningun repartidor y fue cancelado automaticamente.\n"
                            "No se aplico ningun cargo."
                        ).format(order_id),
                    )
        except Exception as e:
            print("[WARN] No se pudo notificar expiracion al aliado: {}".format(e))
    else:
        # Notificar al admin creador (pedido especial)
        try:
            creator_admin_id = order.get("creator_admin_id") if hasattr(order, "get") else order["creator_admin_id"]
            if creator_admin_id:
                admin = get_admin_by_id(int(creator_admin_id))
                if admin:
                    user = get_user_by_id(admin["user_id"])
                    if user and user["telegram_id"]:
                        context.bot.send_message(
                            chat_id=user["telegram_id"],
                            text=(
                                "El pedido expiró sin repartidor asignado.\n"
                                "No se aplicó ningún cargo."
                            ),
                        )
        except Exception as e:
            print("[WARN] No se pudo notificar expiración al admin creador: {}".format(e))


_DIAS_ES = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
_MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _fmt_pesos_ally(amount):
    """Formatea entero COP como $X.XXX."""
    try:
        amount = int(amount or 0)
    except Exception:
        amount = 0
    return "${}".format("{:,}".format(amount).replace(",", "."))


def _fmt_date_es(date_key):
    """Convierte YYYY-MM-DD a 'Lun 24 mar'."""
    try:
        dt = datetime.strptime(date_key, "%Y-%m-%d")
        return "{} {} {}".format(_DIAS_ES[dt.weekday()], dt.day, _MESES_ES[dt.month - 1])
    except Exception:
        return date_key


def _ally_period_range(period):
    """Retorna (start_s, end_s, label) para el periodo dado (hoy/ayer/semana/mes)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "hoy":
        start, end, label = today, today + timedelta(days=1), "Hoy"
    elif period == "ayer":
        start, end, label = today - timedelta(days=1), today, "Ayer"
    elif period == "semana":
        start = today - timedelta(days=today.weekday())
        end = today + timedelta(days=1)
        label = "Esta semana"
    elif period == "mes":
        start = today.replace(day=1)
        end = today + timedelta(days=1)
        label = "Este mes"
    else:
        return None, None, "Periodo desconocido"
    return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"), label


def _ally_history_period_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Hoy", callback_data="allyhist_periodo_hoy"),
            InlineKeyboardButton("Ayer", callback_data="allyhist_periodo_ayer"),
        ],
        [
            InlineKeyboardButton("Esta semana", callback_data="allyhist_periodo_semana"),
            InlineKeyboardButton("Este mes", callback_data="allyhist_periodo_mes"),
        ],
    ])


def _ally_history_flat_text(orders, routes, label):
    """Genera un bloque de texto con todos los pedidos/rutas del periodo (para Hoy/Ayer)."""
    delivered_orders = [o for o in orders if _row_value(o, "status", "") == "DELIVERED"]
    cancelled_orders = [o for o in orders if _row_value(o, "status", "") == "CANCELLED"]
    delivered_routes = [r for r in routes if r["status"] == "DELIVERED"]
    cancelled_routes = [r for r in routes if r["status"] == "CANCELLED"]

    total = len(orders) + len(routes)
    total_delivered = len(delivered_orders) + len(delivered_routes)
    total_cancelled = len(cancelled_orders) + len(cancelled_routes)
    total_pesos = sum(int(_row_value(o, "total_fee", 0) or 0) for o in delivered_orders)
    total_pesos += sum(int(r["total_fee"] or 0) for r in delivered_routes)

    STATUS_LABELS = {"DELIVERED": "Entregado", "CANCELLED": "Cancelado"}
    lines = [
        "Historial — {} ({} pedidos)".format(label, total),
        "Entregados: {} | Cancelados: {}".format(total_delivered, total_cancelled),
        "Total domicilios entregados: {}".format(_fmt_pesos_ally(total_pesos)),
        "",
    ]

    all_items = []
    for o in orders:
        created = str(_row_value(o, "created_at", "") or "")
        hour = created[11:16] if len(created) >= 16 else "--:--"
        status = _row_value(o, "status", "") or ""
        fee = int(_row_value(o, "total_fee", 0) or 0)
        name = _row_value(o, "customer_name", "N/A") or "N/A"
        all_items.append((created, "#{} {} — {} — {} — {}".format(
            _row_value(o, "id", "?"),
            hour,
            name,
            _fmt_pesos_ally(fee),
            STATUS_LABELS.get(status, status),
        )))
    for r in routes:
        created = str(r["created_at"] or "")
        hour = created[11:16] if len(created) >= 16 else "--:--"
        status = r["status"] or ""
        fee = int(r["total_fee"] or 0)
        all_items.append((created, "Ruta #{} {} — {} — {}".format(
            r["id"], hour, _fmt_pesos_ally(fee), STATUS_LABELS.get(status, status),
        )))

    all_items.sort(key=lambda x: x[0], reverse=True)
    for _, line in all_items:
        lines.append(line)

    return "\n".join(lines)


def _ally_history_grouped_text(orders, routes, label):
    """
    Genera texto agrupado por dia para Esta semana / Este mes.
    Retorna (text, lista_de_date_keys_en_orden_desc).
    """
    days = {}
    for o in orders:
        created = str(_row_value(o, "created_at", "") or "")
        dk = created[:10] if len(created) >= 10 else "-"
        d = days.setdefault(dk, {"total": 0, "delivered": 0, "cancelled": 0, "pesos": 0})
        d["total"] += 1
        if _row_value(o, "status", "") == "DELIVERED":
            d["delivered"] += 1
            d["pesos"] += int(_row_value(o, "total_fee", 0) or 0)
        else:
            d["cancelled"] += 1
    for r in routes:
        created = str(r["created_at"] or "")
        dk = created[:10] if len(created) >= 10 else "-"
        d = days.setdefault(dk, {"total": 0, "delivered": 0, "cancelled": 0, "pesos": 0})
        d["total"] += 1
        if r["status"] == "DELIVERED":
            d["delivered"] += 1
            d["pesos"] += int(r["total_fee"] or 0)
        else:
            d["cancelled"] += 1

    grand_total = sum(d["total"] for d in days.values())
    grand_delivered = sum(d["delivered"] for d in days.values())
    grand_cancelled = sum(d["cancelled"] for d in days.values())
    grand_pesos = sum(d["pesos"] for d in days.values())

    lines = [
        "Historial — {} ({} pedidos)".format(label, grand_total),
        "Entregados: {} | Cancelados: {}".format(grand_delivered, grand_cancelled),
        "Total domicilios entregados: {}".format(_fmt_pesos_ally(grand_pesos)),
        "",
        "Toca un dia para ver el detalle:",
    ]
    sorted_keys = sorted(days.keys(), reverse=True)
    for dk in sorted_keys:
        d = days[dk]
        lines.append("{} — {} pedidos — {}".format(
            _fmt_date_es(dk), d["total"], _fmt_pesos_ally(d["pesos"])
        ))

    return "\n".join(lines), sorted_keys


def ally_active_orders(update, context):
    """Muestra pedidos activos del aliado y selector de periodo para historial."""
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        update.message.reply_text("No se encontro tu usuario.")
        return

    ally = get_ally_by_user_id(user["id"])
    if not ally:
        update.message.reply_text("No tienes perfil de aliado.")
        return

    active_orders = get_active_orders_by_ally(ally["id"])
    active_routes = get_active_routes_by_ally(ally["id"])

    STATUS_LABELS = {
        "PENDING": "Pendiente",
        "PUBLISHED": "Buscando repartidor",
        "ACCEPTED": "Repartidor asignado",
        "PICKED_UP": "En camino al cliente",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }

    if active_routes:
        update.message.reply_text("Rutas activas:")
        for route in active_routes:
            n_stops = len(get_route_destinations(route["id"]))
            status_label = STATUS_LABELS.get(route["status"], route["status"] or "")
            text = "Ruta #{}\nEstado: {}\nParadas: {}".format(
                route["id"], status_label, n_stops
            )
            if route["status"] in ("PUBLISHED", "ACCEPTED"):
                keyboard = [[InlineKeyboardButton(
                    "Cancelar ruta",
                    callback_data="ruta_cancelar_aliado_{}".format(route["id"]),
                )]]
                update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                update.message.reply_text(text)

    if active_orders:
        update.message.reply_text("Pedidos activos:")
        for order in active_orders:
            status_label = STATUS_LABELS.get(order["status"], order["status"])
            text = "Pedido #{}\nEstado: {}\nCliente: {}\nDireccion: {}".format(
                order["id"],
                status_label,
                order["customer_name"] or "N/A",
                order["customer_address"] or "N/A",
            )
            if order["status"] in ("PENDING", "PUBLISHED", "ACCEPTED"):
                keyboard = [
                    [InlineKeyboardButton(
                        "Aumentar incentivo",
                        callback_data="pedido_inc_menu_{}".format(order["id"]),
                    )],
                    [InlineKeyboardButton(
                        "Cancelar pedido",
                        callback_data="order_cancel_{}".format(order["id"]),
                    )],
                ]
                update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                update.message.reply_text(text)
    elif not active_routes:
        update.message.reply_text("No tienes pedidos activos en este momento.")

    # Selector de periodo para historial
    update.message.reply_text(
        "Historial de pedidos\nSelecciona un periodo:",
        reply_markup=_ally_history_period_keyboard(),
    )


def ally_orders_history_callback(update, context):
    """Callback para navegacion del historial de pedidos del aliado por periodo.
    Patrones: allyhist_periodo_{period} | allyhist_dia_{YYYYMMDD}_{period}
    """
    query = update.callback_query
    query.answer()
    data = query.data or ""
    telegram_id = update.effective_user.id

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.edit_message_text("No se encontro tu usuario.")
        return
    ally = get_ally_by_user_id(user["id"])
    if not ally:
        query.edit_message_text("No tienes perfil de aliado.")
        return

    if data.startswith("allyhist_periodo_"):
        period = data[len("allyhist_periodo_"):]
        _ally_show_period(query, ally["id"], period)
        return

    if data.startswith("allyhist_dia_"):
        # allyhist_dia_{YYYYMMDD}_{parent_period}
        rest = data[len("allyhist_dia_"):]
        parts = rest.split("_", 1)
        compact = parts[0]
        parent = parts[1] if len(parts) > 1 else "semana"
        if len(compact) == 8 and compact.isdigit():
            date_key = "{}-{}-{}".format(compact[:4], compact[4:6], compact[6:8])
            _ally_show_day(query, ally["id"], date_key, parent)
        else:
            query.edit_message_text("Fecha invalida.", reply_markup=_ally_history_period_keyboard())
        return

    query.edit_message_text(
        "Historial de pedidos\nSelecciona un periodo:",
        reply_markup=_ally_history_period_keyboard(),
    )


def _ally_show_period(query, ally_id, period):
    """Muestra resumen del historial para el periodo solicitado."""
    start_s, end_s, label = _ally_period_range(period)
    if not start_s:
        query.edit_message_text("Periodo invalido.", reply_markup=_ally_history_period_keyboard())
        return

    orders = get_ally_orders_between(ally_id, start_s, end_s)
    routes = get_ally_routes_between(ally_id, start_s, end_s)

    if not orders and not routes:
        query.edit_message_text(
            "Historial — {}\nNo hay pedidos en este periodo.".format(label),
            reply_markup=_ally_history_period_keyboard(),
        )
        return

    if period in ("hoy", "ayer"):
        text = _ally_history_flat_text(orders, routes, label)
        query.edit_message_text(text, reply_markup=_ally_history_period_keyboard())
    else:
        text, sorted_keys = _ally_history_grouped_text(orders, routes, label)
        day_buttons = []
        for dk in sorted_keys:
            compact = dk.replace("-", "")
            day_buttons.append([InlineKeyboardButton(
                _fmt_date_es(dk),
                callback_data="allyhist_dia_{}_{}".format(compact, period),
            )])
        full_kb = InlineKeyboardMarkup(day_buttons + _ally_history_period_keyboard().inline_keyboard)
        query.edit_message_text(text, reply_markup=full_kb)


def _ally_show_day(query, ally_id, date_key, parent_period):
    """Muestra detalle de un dia especifico del historial del aliado."""
    try:
        dt = datetime.strptime(date_key, "%Y-%m-%d")
    except ValueError:
        query.edit_message_text("Fecha invalida.", reply_markup=_ally_history_period_keyboard())
        return

    start_s = dt.strftime("%Y-%m-%d 00:00:00")
    end_s = (dt + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    orders = get_ally_orders_between(ally_id, start_s, end_s)
    routes = get_ally_routes_between(ally_id, start_s, end_s)

    text = _ally_history_flat_text(orders, routes, _fmt_date_es(date_key))
    back_label = "Volver a semana" if parent_period == "semana" else "Volver a mes"
    full_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(back_label, callback_data="allyhist_periodo_{}".format(parent_period))]]
        + _ally_history_period_keyboard().inline_keyboard
    )
    query.edit_message_text(text, reply_markup=full_kb)


def admin_orders_panel(update, context, admin_id, is_platform=False):
    """
    Muestra submenú de pedidos para admin.
    Llamado desde admin_menu_callback (platform) o mi_admin callbacks (local).
    """
    query = update.callback_query
    query.answer()

    keyboard = [
        [InlineKeyboardButton("Pedidos activos", callback_data="admpedidos_list_ACTIVE_{}".format(admin_id))],
        [InlineKeyboardButton("Pedidos entregados", callback_data="admpedidos_list_DELIVERED_{}".format(admin_id))],
        [InlineKeyboardButton("Pedidos cancelados", callback_data="admpedidos_list_CANCELLED_{}".format(admin_id))],
        [InlineKeyboardButton("Todos los pedidos", callback_data="admpedidos_list_ALL_{}".format(admin_id))],
        [InlineKeyboardButton("Estadisticas de entrega", callback_data="admpedidos_stats_{}".format(admin_id))],
    ]

    query.edit_message_text(
        "Panel de Pedidos\nSelecciona una categoria:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def admin_orders_callback(update, context):
    """
    Maneja callbacks del panel de pedidos admin.
    Patterns:
      admpedidos_list_{filter}_{admin_id}
      admpedidos_detail_{order_id}_{admin_id}
      admpedidos_cancel_{order_id}_{admin_id}
    """
    query = update.callback_query
    data = query.data or ""
    query.answer()

    if data.startswith("admpedidos_list_"):
        return _admin_orders_list(update, context, data)
    if data.startswith("admpedidos_detail_"):
        return _admin_order_detail(update, context, data)
    if data.startswith("admpedidos_cancel_"):
        return _admin_order_cancel(update, context, data)
    if data.startswith("admpedidos_statsdetail_"):
        return _admin_courier_delivery_stats(update, context, data)
    if data.startswith("admpedidos_stats_"):
        return _admin_delivery_stats_panel(update, context, data)
    return None


def _admin_orders_list(update, context, data):
    """Muestra lista de pedidos filtrados."""
    query = update.callback_query
    # Parse: admpedidos_list_{filter}_{admin_id}
    parts = data.replace("admpedidos_list_", "").rsplit("_", 1)
    if len(parts) != 2:
        query.edit_message_text("Error: formato de datos invalido.")
        return

    status_filter = parts[0]
    try:
        admin_id = int(parts[1])
    except ValueError:
        query.edit_message_text("Error: ID de admin invalido.")
        return

    platform_admin = get_platform_admin()
    is_platform = platform_admin and platform_admin["id"] == admin_id

    if status_filter == "ALL":
        db_filter = None
    else:
        db_filter = status_filter

    if is_platform:
        orders = get_all_orders(status_filter=db_filter, limit=20)
    else:
        orders = get_orders_by_admin_team(admin_id, status_filter=db_filter, limit=20)

    if not orders:
        query.edit_message_text(
            "No hay pedidos en esta categoria.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver", callback_data="admpedidos_list_ACTIVE_{}".format(admin_id))],
            ]),
        )
        return

    STATUS_LABELS = {
        "PENDING": "Pendiente",
        "PUBLISHED": "Buscando repartidor",
        "ACCEPTED": "Repartidor asignado",
        "PICKED_UP": "En camino",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }

    FILTER_LABELS = {
        "ACTIVE": "Activos",
        "DELIVERED": "Entregados",
        "CANCELLED": "Cancelados",
        "ALL": "Todos",
    }

    text = "Pedidos - {}\n\n".format(FILTER_LABELS.get(status_filter, status_filter))

    keyboard = []
    for order in orders:
        label = "#{} | {} | {}".format(
            order["id"],
            STATUS_LABELS.get(order["status"], order["status"]),
            order["customer_name"] or "N/A",
        )
        keyboard.append([InlineKeyboardButton(
            label,
            callback_data="admpedidos_detail_{}_{}".format(order["id"], admin_id),
        )])

    keyboard.append([InlineKeyboardButton(
        "Volver al panel de pedidos",
        callback_data="admin_pedidos" if is_platform else "admin_pedidos_local_{}".format(admin_id),
    )])

    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


def _admin_order_detail(update, context, data):
    """Muestra detalle de un pedido con opción de cancelar."""
    query = update.callback_query
    # Parse: admpedidos_detail_{order_id}_{admin_id}
    parts = data.replace("admpedidos_detail_", "").rsplit("_", 1)
    if len(parts) != 2:
        query.edit_message_text("Error de formato.")
        return

    try:
        order_id = int(parts[0])
        admin_id = int(parts[1])
    except ValueError:
        query.edit_message_text("Error de formato.")
        return

    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    STATUS_LABELS = {
        "PENDING": "Pendiente",
        "PUBLISHED": "Buscando repartidor",
        "ACCEPTED": "Repartidor asignado",
        "PICKED_UP": "En camino al cliente",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }

    ally = get_ally_by_id(order["ally_id"])
    ally_name = ally["full_name"] if ally else "N/A"

    courier_name = "Sin asignar"
    if order["courier_id"]:
        courier = get_courier_by_id(order["courier_id"])
        if courier:
            courier_name = courier["full_name"] or "Repartidor"

    ally_admin_snapshot_id = order["ally_admin_id_snapshot"] if "ally_admin_id_snapshot" in order.keys() else None
    courier_admin_snapshot_id = order["courier_admin_id_snapshot"] if "courier_admin_id_snapshot" in order.keys() else None

    ally_admin_snapshot_name = ""
    if ally_admin_snapshot_id:
        ally_admin_row = get_admin_by_id(int(ally_admin_snapshot_id))
        if ally_admin_row and ally_admin_row["full_name"]:
            ally_admin_snapshot_name = ally_admin_row["full_name"]

    courier_admin_snapshot_name = ""
    if courier_admin_snapshot_id:
        courier_admin_row = get_admin_by_id(int(courier_admin_snapshot_id))
        if courier_admin_row and courier_admin_row["full_name"]:
            courier_admin_snapshot_name = courier_admin_row["full_name"]

    ally_admin_snapshot_label = str(ally_admin_snapshot_id) if ally_admin_snapshot_id else "N/A"
    if ally_admin_snapshot_name:
        ally_admin_snapshot_label = "{} ({})".format(ally_admin_snapshot_label, ally_admin_snapshot_name)

    courier_admin_snapshot_label = str(courier_admin_snapshot_id) if courier_admin_snapshot_id else "N/A"
    if courier_admin_snapshot_name:
        courier_admin_snapshot_label = "{} ({})".format(courier_admin_snapshot_label, courier_admin_snapshot_name)

    canceled_by = order["canceled_by"] if "canceled_by" in order.keys() and order["canceled_by"] else "N/A"

    durations = _get_order_durations(order)
    dur_lines = []
    if "llegada_aliado" in durations:
        dur_lines.append("  Llegada al aliado: {}".format(_format_duration(durations["llegada_aliado"])))
    if "entrega_cliente" in durations:
        dur_lines.append("  Entrega al cliente: {}".format(_format_duration(durations["entrega_cliente"])))
    if "tiempo_total" in durations:
        dur_lines.append("  Tiempo total: {}".format(_format_duration(durations["tiempo_total"])))
    dur_block = ("Tiempos del pedido:\n" + "\n".join(dur_lines) + "\n\n") if dur_lines else ""

    text = (
        "Pedido #{}\n\n"
        "Estado: {}\n"
        "Aliado: {}\n"
        "Repartidor: {}\n"
        "Cliente: {}\n"
        "Telefono: {}\n"
        "Direccion: {}\n"
        "Distancia: {:.1f} km\n"
        "Tarifa courier: ${:,}\n\n"
        "Trazabilidad:\n"
        "Admin aliado (snapshot): {}\n"
        "Admin repartidor (snapshot): {}\n\n"
        "Timestamps:\n"
        "Creado: {}\n"
        "Publicado: {}\n"
        "Aceptado: {}\n"
        "Recogida confirmada: {}\n"
        "Entregado: {}\n"
        "Cancelado: {}\n"
        "Cancelado por: {}\n"
    ).format(
        order["id"],
        STATUS_LABELS.get(order["status"], order["status"]),
        ally_name,
        courier_name,
        order["customer_name"] or "N/A",
        order["customer_phone"] or "N/A",
        order["customer_address"] or "N/A",
        order["distance_km"] or 0,
        int(order["total_fee"] or 0),
        ally_admin_snapshot_label,
        courier_admin_snapshot_label,
        order["created_at"] or "N/A",
        order["published_at"] if "published_at" in order.keys() and order["published_at"] else "N/A",
        order["accepted_at"] if "accepted_at" in order.keys() and order["accepted_at"] else "N/A",
        order["pickup_confirmed_at"] if "pickup_confirmed_at" in order.keys() and order["pickup_confirmed_at"] else "N/A",
        order["delivered_at"] if "delivered_at" in order.keys() and order["delivered_at"] else "N/A",
        order["canceled_at"] if "canceled_at" in order.keys() and order["canceled_at"] else "N/A",
        canceled_by,
    )

    if order["instructions"]:
        text += "Instrucciones: {}\n".format(order["instructions"])

    # Campos de compra y subsidio (persistidos en Fase 3 — solo si existen)
    compra_lines = []
    try:
        purchase_amount = order["purchase_amount"]
        if purchase_amount is not None:
            compra_lines.append("Valor de compra: ${:,}".format(int(purchase_amount)))
        delivery_subsidy_applied = int(order["delivery_subsidy_applied"] or 0)
        if delivery_subsidy_applied > 0:
            compra_lines.append("Subsidio aplicado: -${:,}".format(delivery_subsidy_applied))
        elif purchase_amount is not None:
            compra_lines.append("Subsidio aplicado: No")
        customer_delivery_fee = order["customer_delivery_fee"]
        if customer_delivery_fee is not None:
            compra_lines.append("Domicilio al cliente: ${:,}".format(int(customer_delivery_fee)))
    except (KeyError, IndexError):
        pass
    if compra_lines:
        text += "\n" + "\n".join(compra_lines) + "\n"

    keyboard = []
    if order["status"] not in ("DELIVERED", "CANCELLED"):
        keyboard.append([InlineKeyboardButton(
            "Cancelar pedido",
            callback_data="admpedidos_cancel_{}_{}".format(order_id, admin_id),
        )])
    keyboard.append([InlineKeyboardButton(
        "Volver a la lista",
        callback_data="admpedidos_list_ACTIVE_{}".format(admin_id),
    )])

    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


def _admin_order_cancel(update, context, data):
    """Admin cancela un pedido desde el panel."""
    query = update.callback_query
    # Parse: admpedidos_cancel_{order_id}_{admin_id}
    parts = data.replace("admpedidos_cancel_", "").rsplit("_", 1)
    if len(parts) != 2:
        query.edit_message_text("Error de formato.")
        return

    try:
        order_id = int(parts[0])
        admin_id = int(parts[1])
    except ValueError:
        query.edit_message_text("Error de formato.")
        return

    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    if order["status"] in ("DELIVERED", "CANCELLED"):
        query.edit_message_text("Este pedido ya esta {} y no se puede cancelar.".format(
            "entregado" if order["status"] == "DELIVERED" else "cancelado"
        ))
        return

    had_courier = order["courier_id"]
    was_published = order["status"] == "PUBLISHED"

    _cancel_no_response_job(context, order_id)
    _cancel_order_expire_job(context, order_id)
    if was_published:
        current = get_current_offer_for_order(order_id)
        if current:
            jobs = context.job_queue.get_jobs_by_name(
                "offer_timeout_{}_{}".format(order_id, current["queue_id"])
            )
            for job in jobs:
                job.schedule_removal()

    _cancel_delivery_reminder_jobs(context, order_id)
    cancel_order(order_id, "ADMIN")
    delete_offer_queue(order_id)

    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    context.bot_data.get("offer_messages", {}).pop(order_id, None)

    try:
        ally = get_ally_by_id(order["ally_id"])
        if ally:
            ally_user = get_user_by_id(ally["user_id"])
            if ally_user and ally_user["telegram_id"]:
                context.bot.send_message(
                    chat_id=ally_user["telegram_id"],
                    text="Tu pedido #{} fue cancelado por el administrador.".format(order_id),
                )
    except Exception as e:
        print("[WARN] No se pudo notificar cancelacion al aliado: {}".format(e))

    if had_courier:
        _notify_courier_order_cancelled(context, order)

    keyboard = [[InlineKeyboardButton(
        "Volver a pedidos activos",
        callback_data="admpedidos_list_ACTIVE_{}".format(admin_id),
    )]]
    query.edit_message_text(
        "Pedido #{} cancelado exitosamente.".format(order_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def order_courier_callback(update, context):
    """
    Maneja botones de ofertas y ciclo de vida de pedidos.
    Patterns:
    - ^order_(accept|reject|busy|pickup|delivered|delivered_confirm|delivered_cancel|release|release_reason|release_confirm|release_abort|cancel)_\\d+$
    - ^order_pickupconfirm_(approve|reject)_\\d+$
    """
    query = update.callback_query
    data = query.data or ""
    query.answer()

    if data.startswith("order_pickupconfirm_approve_"):
        order_id = int(data.replace("order_pickupconfirm_approve_", ""))
        return _handle_pickup_confirmation_by_ally(update, context, order_id, approve=True)
    if data.startswith("order_pickupconfirm_reject_"):
        order_id = int(data.replace("order_pickupconfirm_reject_", ""))
        return _handle_pickup_confirmation_by_ally(update, context, order_id, approve=False)

    if data.startswith("order_find_another_"):
        order_id = int(data.replace("order_find_another_", ""))
        return _handle_find_another_courier(update, context, order_id)
    if data.startswith("order_wait_courier_"):
        order_id = int(data.replace("order_wait_courier_", ""))
        return _handle_wait_courier(update, context, order_id)
    if data.startswith("order_call_courier_"):
        order_id = int(data.replace("order_call_courier_", ""))
        return _handle_call_courier(update, context, order_id)
    if data.startswith("order_accept_"):
        order_id = int(data.replace("order_accept_", ""))
        return _handle_accept(update, context, order_id)
    if data.startswith("order_reject_"):
        order_id = int(data.replace("order_reject_", ""))
        return _handle_reject(update, context, order_id)
    if data.startswith("order_busy_"):
        order_id = int(data.replace("order_busy_", ""))
        return _handle_busy(update, context, order_id)
    if data.startswith("order_pickup_"):
        order_id = int(data.replace("order_pickup_", ""))
        return _handle_pickup(update, context, order_id)
    if data.startswith("order_delivered_confirm_"):
        order_id = int(data.replace("order_delivered_confirm_", ""))
        return _handle_delivered_confirm(update, context, order_id)
    if data.startswith("order_delivered_cancel_"):
        order_id = int(data.replace("order_delivered_cancel_", ""))
        query.edit_message_text("Ok. El pedido #{} sigue en curso.".format(order_id))
        return
    if data.startswith("order_delivered_"):
        order_id = int(data.replace("order_delivered_", ""))
        return _handle_delivered(update, context, order_id)
    if data.startswith("order_release_abort_"):
        order_id = int(data.replace("order_release_abort_", ""))
        query.edit_message_text("Ok. El pedido #{} sigue en curso.".format(order_id))
        return
    if data.startswith("order_release_reason_"):
        # order_release_reason_{order_id}_{reason}
        parts = data.split("_")
        if len(parts) < 5:
            query.edit_message_text("No se pudo procesar la razon de liberacion.")
            return
        order_id = int(parts[3])
        reason_code = parts[4]
        return _handle_release_reason_selected(update, context, order_id, reason_code)
    if data.startswith("order_release_confirm_"):
        # order_release_confirm_{order_id}_{reason}
        parts = data.split("_")
        if len(parts) < 5:
            query.edit_message_text("No se pudo confirmar la liberacion.")
            return
        order_id = int(parts[3])
        reason_code = parts[4]
        return _handle_release(update, context, order_id, reason_code=reason_code)
    if data.startswith("order_release_"):
        # order_release_{order_id}
        parts = data.split("_")
        if len(parts) < 3:
            query.edit_message_text("No se pudo procesar la liberacion.")
            return
        order_id = int(parts[2])
        return _handle_release_reason_menu(update, context, order_id)
    if data.startswith("order_cancel_"):
        order_id = int(data.replace("order_cancel_", ""))
        return _handle_cancel_ally(update, context, order_id)
    if data.startswith("order_confirm_pickup_"):
        order_id = int(data.replace("order_confirm_pickup_", ""))
        return _handle_confirm_pickup(update, context, order_id)
    if data.startswith("order_pinissue_"):
        order_id = int(data.replace("order_pinissue_", ""))
        return _handle_pin_issue_report(update, context, order_id)
    if data.startswith("admin_pinissue_fin_"):
        order_id = int(data.replace("admin_pinissue_fin_", ""))
        return _handle_admin_pinissue_action(update, context, order_id, "fin")
    if data.startswith("admin_pinissue_cancel_courier_"):
        order_id = int(data.replace("admin_pinissue_cancel_courier_", ""))
        return _handle_admin_pinissue_action(update, context, order_id, "cancel_courier")
    if data.startswith("admin_pinissue_cancel_ally_"):
        order_id = int(data.replace("admin_pinissue_cancel_ally_", ""))
        return _handle_admin_pinissue_action(update, context, order_id, "cancel_ally")
    return None


def _handle_release_reason_menu(update, context, order_id):
    """Muestra razones válidas antes de permitir que el courier libere el pedido."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    if order["status"] != "ACCEPTED":
        query.edit_message_text("Este pedido no se puede liberar en su estado actual.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != order["courier_id"]:
        query.edit_message_text("No tienes permiso para liberar este pedido.")
        return

    arrived_at = _row_value(order, "courier_arrived_at")
    arrived_line = ""
    if arrived_at:
        arrived_line = (
            "\n\nIMPORTANTE: Ya reportaste tu llegada al punto de recogida. "
            "Liberar en este punto solo se permite por motivos serios."
        )

    reason_labels = {
        "falla_mecanica": "Falla mecanica / accidente con el vehiculo",
        "emergencia": "Emergencia personal / seguridad",
        "aliado_no_entrega": "El aliado no entrega el pedido",
        "pedido_incorrecto": "Pedido incorrecto / no coincide",
        "sin_productos": "No hay productos disponibles",
        "otro_admin": "Otro (debe revisarlo el admin)",
    }

    lines = [
        "Vas a liberar el pedido #{}.".format(order_id),
        "",
        "Liberar un pedido sin motivo valido es una falta grave. "
        "Liberar para evitar la comision puede terminar en suspension o expulsion.",
        "Selecciona un motivo:",
    ]
    text = "\n".join(lines) + arrived_line

    kb = []
    for code, label in reason_labels.items():
        kb.append([InlineKeyboardButton(label, callback_data="order_release_reason_{}_{}".format(order_id, code))])
    kb.append([InlineKeyboardButton("Cancelar", callback_data="order_release_abort_{}".format(order_id))])

    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))


def _handle_release_reason_selected(update, context, order_id, reason_code):
    """Pide confirmación final antes de liberar el pedido."""
    query = update.callback_query
    reason_labels = {
        "falla_mecanica": "Falla mecanica / accidente con el vehiculo",
        "emergencia": "Emergencia personal / seguridad",
        "aliado_no_entrega": "El aliado no entrega el pedido",
        "pedido_incorrecto": "Pedido incorrecto / no coincide",
        "sin_productos": "No hay productos disponibles",
        "otro_admin": "Otro (debe revisarlo el admin)",
    }
    reason_label = reason_labels.get(reason_code, reason_code or "No especificado")

    keyboard = [[
        InlineKeyboardButton(
            "Confirmar liberacion",
            callback_data="order_release_confirm_{}_{}".format(order_id, reason_code),
        ),
        InlineKeyboardButton(
            "Cancelar",
            callback_data="order_release_abort_{}".format(order_id),
        ),
    ]]
    query.edit_message_text(
        "Confirmas que vas a liberar el pedido #{}?\n\nMotivo: {}\n\n"
        "Esta accion se revisa por el admin. Si es injustificada, puede haber sancion.".format(
            order_id,
            reason_label,
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------------------------------------------------------------------
# Timers de llegada (post-aceptación)
# ---------------------------------------------------------------------------

def _release_order_by_timeout(order_id, courier_id, context, reason="timeout"):
    """
    Libera un pedido ACCEPTED por inactividad o deadline, excluye al courier
    y reinicia el ciclo de ofertas. Usado por T+5, T+20 y cuando el aliado
    solicita otro repartidor.
    """
    import time as _time
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        return

    _cancel_arrival_jobs(context, order_id)
    release_order_from_courier(order_id)

    cycle = context.bot_data.get("offer_cycles", {}).get(order_id, {})
    excluded = set(cycle.get("excluded_couriers", set()))
    excluded.add(courier_id)

    # Notificar al courier
    try:
        c = get_courier_by_id(courier_id)
        if c:
            cu = get_user_by_id(c["user_id"])
            if cu:
                context.bot.send_message(
                    chat_id=cu["telegram_id"],
                    text="El pedido #{} fue liberado automaticamente ({}).".format(order_id, reason),
                )
    except Exception:
        pass

    # Notificar al aliado
    try:
        ally = get_ally_by_id(order["ally_id"])
        if ally:
            au = get_user_by_id(ally["user_id"])
            if au:
                context.bot.send_message(
                    chat_id=au["telegram_id"],
                    text=(
                        "El repartidor fue liberado del pedido #{} por {}. "
                        "Buscando otro repartidor..."
                    ).format(order_id, reason),
                )
    except Exception:
        pass

    # Reiniciar ciclo excluyendo al courier liberado
    ally_id = order["ally_id"]
    admin_link = get_approved_admin_link_for_ally(ally_id)
    admin_id = admin_link["admin_id"] if admin_link else cycle.get("admin_id")
    if not admin_id:
        return

    p_lat = cycle.get("pickup_lat")
    p_lng = cycle.get("pickup_lng")
    if p_lat is None or p_lng is None:
        p_lat, p_lng = _get_pickup_coords(order)

    requires_cash = bool(order["requires_cash"])
    cash_amount = int(order["cash_required_amount"] or 0)

    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id, ally_id=ally_id,
        requires_cash=requires_cash, cash_required_amount=cash_amount,
        pickup_lat=p_lat, pickup_lng=p_lng,
    )
    eligible = [c for c in eligible if c["courier_id"] not in excluded]

    if eligible:
        courier_ids = [c["courier_id"] for c in eligible]
        delete_offer_queue(order_id)
        create_offer_queue(order_id, courier_ids)
        context.bot_data.setdefault("offer_cycles", {})[order_id] = {
            "started_at": _time.time(),
            "admin_id": admin_id, "ally_id": ally_id,
            "pickup_lat": p_lat, "pickup_lng": p_lng,
            "pickup_city": cycle.get("pickup_city") if cycle else None,
            "pickup_barrio": cycle.get("pickup_barrio") if cycle else None,
            "dropoff_city": cycle.get("dropoff_city") if cycle else None,
            "dropoff_barrio": cycle.get("dropoff_barrio") if cycle else None,
            "requires_cash": requires_cash, "cash_amount": cash_amount,
            "excluded_couriers": excluded,
        }
        _send_next_offer(order_id, context)
    else:
        try:
            ally = get_ally_by_id(ally_id)
            if ally:
                au = get_user_by_id(ally["user_id"])
                if au:
                    context.bot.send_message(
                        chat_id=au["telegram_id"],
                        text="No hay mas repartidores disponibles para el pedido #{}.".format(order_id),
                    )
        except Exception:
            pass


def _arrival_inactivity_job(context):
    """T+5: algoritmo direccional Rappi-style.

    - Ya llego (<=100m): cancela jobs, no hace nada.
    - Avanzando bien (>=20% mas cerca): no hace nada.
    - Sin progreso o poco movimiento: avisa al courier.
    - Alejandose del pickup (>15% mas lejos que al aceptar): libera inmediatamente.
    """
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        return
    if order["courier_arrived_at"]:
        return

    pickup_lat, pickup_lng = _get_pickup_coords(order)
    accepted_lat = order["courier_accepted_lat"]
    accepted_lng = order["courier_accepted_lng"]

    if not all([pickup_lat, pickup_lng, accepted_lat, accepted_lng]):
        return  # Sin datos suficientes

    courier = get_courier_by_id(order["courier_id"])
    if not courier:
        return

    current_lat = float(_row_value(courier, "live_lat") or accepted_lat)
    current_lng = float(_row_value(courier, "live_lng") or accepted_lng)

    dist_accepted = haversine_km(float(accepted_lat), float(accepted_lng),
                                 float(pickup_lat), float(pickup_lng))
    dist_now = haversine_km(current_lat, current_lng,
                            float(pickup_lat), float(pickup_lng))

    # Ya llego
    if dist_now <= ARRIVAL_RADIUS_KM:
        _cancel_arrival_jobs(context, order_id)
        return

    courier_user = get_user_by_id(courier["user_id"]) if courier else None
    courier_tg_id = courier_user["telegram_id"] if courier_user else None

    # Se esta alejando del pickup (>15% mas lejos)
    if dist_accepted > 0.05 and dist_now > dist_accepted * 1.15:
        if courier_tg_id:
            try:
                context.bot.send_message(
                    chat_id=courier_tg_id,
                    text=(
                        "Pedido #{}: detectamos que te estas alejando del punto de recogida.\n"
                        "Si no puedes atender este servicio, libera el pedido para que otro repartidor lo tome."
                    ).format(order_id),
                )
            except Exception:
                pass
        _release_order_by_timeout(order_id, order["courier_id"], context,
                                  reason="T+5 alejandose del punto de recogida")
        return

    # Avanzando bien (>=20% mas cerca que al aceptar)
    if dist_accepted > 0.05 and dist_now < dist_accepted * 0.80:
        return  # Buen progreso, no hacer nada

    # Sin progreso suficiente: avisar (no liberar — T+20 hara la liberacion si es necesario)
    if courier_tg_id:
        try:
            context.bot.send_message(
                chat_id=courier_tg_id,
                text=(
                    "Pedido #{}: llevamos 5 minutos y no hemos detectado avance hacia el punto de recogida.\n"
                    "Asegurate de estar en camino. Si no puedes llegar, libera el pedido."
                ).format(order_id),
            )
        except Exception:
            pass


def _arrival_warn_ally_job(context):
    """T+15: notifica al aliado que el courier no ha llegado y le da opciones."""
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        return
    if order["courier_arrived_at"]:
        return

    courier = get_courier_by_id(order["courier_id"])
    courier_name = courier["full_name"] if courier else "El repartidor"
    courier_user = get_user_by_id(courier["user_id"]) if courier else None
    courier_tg_id = courier_user["telegram_id"] if courier_user else None

    # Notificar al aliado
    try:
        ally = get_ally_by_id(order["ally_id"])
        if ally:
            au = get_user_by_id(ally["user_id"])
            if au:
                keyboard = [
                    [InlineKeyboardButton(
                        "Buscar otro repartidor",
                        callback_data="order_find_another_{}".format(order_id),
                    )],
                    [InlineKeyboardButton(
                        "Seguir esperando",
                        callback_data="order_wait_courier_{}".format(order_id),
                    )],
                ]
                if courier:
                    keyboard.insert(1, [InlineKeyboardButton(
                        "Llamar al repartidor",
                        callback_data="order_call_courier_{}".format(order_id),
                    )])
                context.bot.send_message(
                    chat_id=au["telegram_id"],
                    text=(
                        "Han pasado 15 minutos y {} no ha reportado su llegada "
                        "al punto de recogida del pedido #{}.\n\nQue deseas hacer?"
                    ).format(courier_name, order_id),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
    except Exception as e:
        print("[WARN] _arrival_warn_ally_job: {}".format(e))

    # Notificar al courier con botones de respuesta
    if courier_tg_id:
        try:
            courier_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "Sigo en camino",
                    callback_data="order_arrival_enroute_{}".format(order_id)
                )],
                [InlineKeyboardButton(
                    "No puedo llegar — liberar pedido",
                    callback_data="order_arrival_release_{}".format(order_id)
                )],
            ])
            context.bot.send_message(
                chat_id=courier_tg_id,
                text=(
                    "Pedido #{}: llevas 15 minutos sin confirmar llegada al punto de recogida.\n"
                    "El aliado fue notificado. El pedido se liberara automaticamente en 5 minutos.\n\n"
                    "Que esta pasando?"
                ).format(order_id),
                reply_markup=courier_keyboard,
            )
        except Exception:
            pass


def _arrival_deadline_job(context):
    """T+20: libera automáticamente el pedido si el courier no llegó."""
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        return
    if order["courier_arrived_at"]:
        return
    _release_order_by_timeout(order_id, order["courier_id"], context,
                               reason="timeout de llegada (20 min)")


def _handle_courier_arrival_button(update, context, order_id):
    """Courier presiona 'Confirmar llegada'. Valida GPS <= 100m del pickup."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        query.answer("Este pedido ya no esta activo.")
        return

    courier = get_courier_by_telegram_id(update.effective_user.id)
    if not courier:
        return

    live_lat = _row_value(courier, "live_lat")
    live_lng = _row_value(courier, "live_lng")
    live_active = _row_value(courier, "live_location_active")

    if not live_active or not live_lat or not live_lng:
        query.answer()
        query.message.reply_text(
            "Tu GPS no esta activo. Activa tu ubicacion en vivo en Telegram para confirmar tu llegada."
        )
        return

    pickup_lat, pickup_lng = _get_pickup_coords(order)
    if pickup_lat and pickup_lng:
        dist_km = haversine_km(float(live_lat), float(live_lng),
                               float(pickup_lat), float(pickup_lng))
        if dist_km > ARRIVAL_RADIUS_KM:
            query.answer()
            query.message.reply_text(
                "Segun tu ubicacion estas a {:.0f} metros del punto de recogida.\n"
                "Dirigete al lugar e intenta confirmar cuando estes mas cerca.".format(dist_km * 1000)
            )
            return

    _cancel_arrival_jobs(context, order_id)
    set_courier_arrived(order_id)
    courier_name = courier["full_name"] or "Repartidor"
    _notify_ally_courier_arrived(context, order, courier_name)
    query.edit_message_text(
        "Llegada confirmada. El aliado debe confirmar antes de entregarte los datos del cliente."
    )


def _handle_courier_arrival_enroute(update, context, order_id):
    """Courier responde 'Sigo en camino' al T+15."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        query.answer()
        return
    query.edit_message_text(
        "Confirmado. Sigue hacia el punto de recogida y presiona 'Confirmar llegada' cuando estes alli."
    )
    # Notificar al aliado
    try:
        if order["ally_id"]:
            ally = get_ally_by_id(order["ally_id"])
            if ally:
                au = get_user_by_id(ally["user_id"])
                if au:
                    context.bot.send_message(
                        chat_id=au["telegram_id"],
                        text="El repartidor confirma que sigue en camino al pedido #{}.".format(order_id),
                    )
    except Exception:
        pass


def _handle_courier_arrival_release(update, context, order_id):
    """Courier responde 'No puedo llegar' al T+15."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        query.answer()
        return
    query.edit_message_text("Pedido #{} liberado. Gracias por avisar.".format(order_id))
    _cancel_arrival_jobs(context, order_id)
    _release_order_by_timeout(order_id, order["courier_id"], context,
                              reason="courier confirmo que no puede llegar (T+15)")


def check_courier_arrival_at_pickup(courier_id, lat, lng, context):
    """
    Verifica si el courier está a <=100m del pickup de su pedido activo (ACCEPTED).
    Si es así, solo habilita la confirmación manual de llegada del courier.
    Llamada desde courier_live_location_handler en main.py en cada actualización.
    """
    order = get_active_order_for_courier(courier_id)
    if not order:
        return
    arrived_at = order["courier_arrived_at"] if "courier_arrived_at" in order.keys() else None
    if arrived_at:
        return  # Ya estaba marcado

    pickup_lat, pickup_lng = _get_pickup_coords(order)
    if not pickup_lat or not pickup_lng:
        return

    # Auto-deteccion removida: el courier confirma manualmente con boton GPS-validado.
    pass


# ---------------------------------------------------------------------------

def _handle_accept(update, context, order_id):
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    if order["status"] != "PUBLISHED":
        query.edit_message_text("Esta oferta ya no esta disponible.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        query.edit_message_text("No se encontro tu perfil de repartidor.")
        return

    # Verificar que este courier tiene la oferta activa
    current = get_current_offer_for_order(order_id)
    if not current or current["courier_id"] != courier["id"]:
        query.edit_message_text("Esta oferta ya no esta disponible para ti.")
        return

    active_order = get_active_order_for_courier(courier["id"])
    if active_order and active_order["id"] != order_id:
        query.edit_message_text(
            "No puedes aceptar un nuevo pedido porque ya tienes un pedido en curso (#{}).".format(
                active_order["id"]
            )
        )
        return

    active_route = get_active_route_for_courier(courier["id"])
    if active_route:
        query.edit_message_text(
            "No puedes aceptar un nuevo pedido porque ya tienes una ruta en curso (#{}).".format(
                active_route["id"]
            )
        )
        return

    # Cancelar jobs de timeout y sugerencia de incentivo
    _cancel_offer_jobs(context, order_id, current["queue_id"])
    _cancel_no_response_job(context, order_id)
    _cancel_order_expire_job(context, order_id)

    # Marcar oferta como aceptada
    mark_offer_response(current["queue_id"], "ACCEPTED")

    # Asignar courier al pedido y guardar snapshot de admin del courier
    courier_id = courier["id"]
    courier_admin_link = get_approved_admin_link_for_courier(courier_id)
    courier_admin_id_snapshot = courier_admin_link["admin_id"] if courier_admin_link else None
    assign_order_to_courier(order_id, courier_id, courier_admin_id_snapshot)
    courier_name = courier["full_name"] or "Repartidor"

    pickup_lat, pickup_lng = _get_pickup_coords(order)
    keyboard = []
    keyboard.extend(_build_navigation_rows(pickup_lat, pickup_lng))
    keyboard.append([InlineKeyboardButton(
        "Confirmar llegada al punto de recogida",
        callback_data="order_arrived_pickup_{}".format(order_id)
    )])
    keyboard.append([InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order_id))])

    customer_city = _row_value(order, "customer_city") or ""
    customer_barrio = _row_value(order, "customer_barrio") or ""
    destino_area = "{}, {}".format(customer_barrio, customer_city).strip(", ") or "No disponible"

    query.edit_message_text(
        "Pedido #{} aceptado.\n\n"
        "Recoge en: {}\n"
        "Destino: {}\n"
        "Tarifa: ${:,}\n\n"
        "Dirigete al punto de recogida. Tienes 15 minutos.\n"
        "Cuando estes alli, presiona 'Confirmar llegada al punto de recogida'.\n"
        "Si no puedes llegar, presiona 'Liberar pedido'.".format(
            order_id,
            _get_pickup_address(order),
            destino_area,
            int(order["total_fee"] or 0),
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    if pickup_lat is not None and pickup_lng is not None:
        try:
            context.bot.send_location(
                chat_id=query.message.chat_id,
                latitude=float(pickup_lat),
                longitude=float(pickup_lng),
            )
        except Exception:
            pass

    # Guardar posición del courier al aceptar (base para detección de inactividad T+5)
    try:
        c_data = get_courier_by_id(courier_id)
        if c_data:
            c_lat = _row_value(c_data, "live_lat") or _row_value(c_data, "residence_lat")
            c_lng = _row_value(c_data, "live_lng") or _row_value(c_data, "residence_lng")
            if c_lat and c_lng:
                set_courier_accepted_location(order_id, float(c_lat), float(c_lng))
    except Exception:
        pass

    # Programar 3 timers de llegada
    context.job_queue.run_once(
        _arrival_inactivity_job,
        ARRIVAL_INACTIVITY_SECONDS,
        context={"order_id": order_id},
        name="arr_inactive_{}".format(order_id),
    )
    context.job_queue.run_once(
        _arrival_warn_ally_job,
        ARRIVAL_WARN_SECONDS,
        context={"order_id": order_id},
        name="arr_warn_{}".format(order_id),
    )
    context.job_queue.run_once(
        _arrival_deadline_job,
        ARRIVAL_DEADLINE_SECONDS,
        context={"order_id": order_id},
        name="arr_deadline_{}".format(order_id),
    )

    # Limpiar bot_data del ciclo de ofertas
    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    context.bot_data.get("offer_messages", {}).pop(order_id, None)

    _notify_ally_order_accepted(context, order, courier_name)


def _handle_reject(update, context, order_id):
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        query.edit_message_text("Esta oferta ya no esta disponible.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        query.edit_message_text("Oferta #{} rechazada.".format(order_id))
        return

    current = get_current_offer_for_order(order_id)
    if not current or current["courier_id"] != courier["id"]:
        query.edit_message_text("Esta oferta ya no esta disponible para ti.")
        return

    # Cancelar el job de timeout
    _cancel_offer_jobs(context, order_id, current["queue_id"])

    mark_offer_response(current["queue_id"], "REJECTED")
    query.edit_message_text("Oferta #{} rechazada.".format(order_id))

    # Enviar al siguiente courier
    _send_next_offer(order_id, context)


def _handle_busy(update, context, order_id):
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        query.edit_message_text("Esta oferta ya no esta disponible.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        query.edit_message_text("Oferta #{} marcada como ocupado.".format(order_id))
        return

    current = get_current_offer_for_order(order_id)
    if not current or current["courier_id"] != courier["id"]:
        query.edit_message_text("Esta oferta ya no esta disponible para ti.")
        return

    _cancel_offer_jobs(context, order_id, current["queue_id"])

    # Se registra como REJECTED para mantener el flujo actual de cola y reinicio.
    mark_offer_response(current["queue_id"], "REJECTED")
    query.edit_message_text("Oferta #{} marcada como ocupado. Se asignara a otro repartidor.".format(order_id))
    _send_next_offer(order_id, context)


def _handle_find_another_courier(update, context, order_id):
    """Aliado solicita buscar otro repartidor cuando el courier no llega."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        query.edit_message_text("Este pedido ya no esta disponible para esta accion.")
        return
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    ally = get_ally_by_user_id(user["id"]) if user else None
    if not ally or ally["id"] != order["ally_id"]:
        query.answer("No tienes permiso para esta accion.")
        return
    query.edit_message_text("Buscando otro repartidor para el pedido #{}...".format(order_id))
    _release_order_by_timeout(order_id, order["courier_id"], context,
                              reason="solicitado por el aliado")


def _handle_call_courier(update, context, order_id):
    """Aliado solicita el teléfono del repartidor para poder llamarlo."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    courier_id = _row_value(order, "courier_id") if order else None
    if not order or order["status"] != "ACCEPTED" or not courier_id:
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Este pedido ya no esta disponible para esta accion.",
        )
        return

    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    ally = get_ally_by_user_id(user["id"]) if user else None
    if not ally or ally["id"] != order["ally_id"]:
        query.answer("No tienes permiso para esta accion.")
        return

    courier = get_courier_by_id(courier_id)
    courier_phone = _row_value(courier, "phone") if courier else None
    if not courier_phone:
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Telefono del repartidor no disponible para el pedido #{}.".format(order_id),
        )
        return

    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Telefono del repartidor para el pedido #{}: {}".format(order_id, courier_phone),
    )


def _handle_wait_courier(update, context, order_id):
    """Aliado decide seguir esperando al courier."""
    query = update.callback_query
    query.edit_message_text(
        "De acuerdo, seguimos esperando al repartidor para el pedido #{}.".format(order_id)
    )


def _handle_release(update, context, order_id, reason_code=None):
    """Courier libera un pedido aceptado. Vuelve a PUBLISHED y re-inicia ofertas."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    if order["status"] != "ACCEPTED":
        query.edit_message_text("Este pedido no se puede liberar en su estado actual.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != order["courier_id"]:
        query.edit_message_text("No tienes permiso para liberar este pedido.")
        return

    reason_labels = {
        "falla_mecanica": "Falla mecanica / accidente con el vehiculo",
        "emergencia": "Emergencia personal / seguridad",
        "aliado_no_entrega": "El aliado no entrega el pedido",
        "pedido_incorrecto": "Pedido incorrecto / no coincide",
        "sin_productos": "No hay productos disponibles",
        "otro_admin": "Otro (debe revisarlo el admin)",
    }
    reason_label = reason_labels.get(reason_code, reason_code or "No especificado")

    arrived_at = _row_value(order, "courier_arrived_at")
    arrived_flag = "SI" if arrived_at else "NO"

    _cancel_arrival_jobs(context, order_id)
    release_order_from_courier(order_id)
    query.edit_message_text(
        "Pedido #{} liberado.\n"
        "Motivo: {}\n\n"
        "Este pedido sera ofrecido a otros repartidores.".format(order_id, reason_label)
    )

    _notify_ally_order_released(context, order, reason_label=reason_label)
    _notify_admin_order_released(context, order, courier, reason_label=reason_label, arrived_flag=arrived_flag)

    # Re-iniciar ciclo de ofertas
    ally_id = order["ally_id"]
    admin_link = get_approved_admin_link_for_ally(ally_id)
    if admin_link:
        admin_id = admin_link["admin_id"]
    else:
        courier_admin_link = get_approved_admin_link_for_courier(courier["id"])
        admin_id = courier_admin_link["admin_id"] if courier_admin_link else None

    if not admin_id:
        print("[WARN] No se pudo reofertar pedido {}: sin admin operativo".format(order_id))
        return

    # Preservar couriers excluidos del ciclo anterior y agregar el que libero el pedido
    prev_cycle = context.bot_data.get("offer_cycles", {}).get(order_id, {})
    excluded = set(prev_cycle.get("excluded_couriers", set()))
    excluded.add(courier["id"])

    # Recuperar coordenadas de recogida del ciclo anterior
    p_lat = prev_cycle.get("pickup_lat")
    p_lng = prev_cycle.get("pickup_lng")

    requires_cash = bool(order["requires_cash"])
    cash_amount = int(order["cash_required_amount"] or 0)

    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=requires_cash,
        cash_required_amount=cash_amount,
        pickup_lat=p_lat,
        pickup_lng=p_lng,
    )
    # Excluir al courier que libero y a cualquier otro excluido previamente
    eligible = [c for c in eligible if c["courier_id"] not in excluded]

    if eligible:
        import time
        courier_ids = [c["courier_id"] for c in eligible]
        delete_offer_queue(order_id)
        create_offer_queue(order_id, courier_ids)

        context.bot_data.setdefault("offer_cycles", {})[order_id] = {
            "started_at": time.time(),
            "admin_id": admin_id,
            "ally_id": ally_id,
            "pickup_lat": p_lat,
            "pickup_lng": p_lng,
            "pickup_city": prev_cycle.get("pickup_city"),
            "pickup_barrio": prev_cycle.get("pickup_barrio"),
            "dropoff_city": prev_cycle.get("dropoff_city"),
            "dropoff_barrio": prev_cycle.get("dropoff_barrio"),
            "requires_cash": requires_cash,
            "cash_amount": cash_amount,
            "excluded_couriers": excluded,
        }
        _send_next_offer(order_id, context)
        _schedule_order_expire_job(context, order_id)


def _handle_cancel_ally(update, context, order_id):
    """Aliado cancela un pedido."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    if order["status"] not in ("PENDING", "PUBLISHED", "ACCEPTED"):
        query.edit_message_text(
            "No se puede cancelar el pedido #{} en estado actual.".format(order_id)
        )
        return

    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    ally = get_ally_by_user_id(user["id"]) if user else None
    if not ally or ally["id"] != order["ally_id"]:
        query.edit_message_text("No tienes permiso para cancelar este pedido.")
        return

    had_courier = order["status"] == "ACCEPTED" and order["courier_id"]
    was_published = order["status"] == "PUBLISHED"

    # Cancelar jobs de arrival si estaba en estado ACCEPTED
    _cancel_arrival_jobs(context, order_id)
    _cancel_delivery_reminder_jobs(context, order_id)

    # Cancelar jobs de timeout y sugerencia si estaba en ciclo de ofertas
    _cancel_no_response_job(context, order_id)
    _cancel_order_expire_job(context, order_id)
    if was_published:
        current = get_current_offer_for_order(order_id)
        if current:
            jobs = context.job_queue.get_jobs_by_name(
                "offer_timeout_{}_{}".format(order_id, current["queue_id"])
            )
            for job in jobs:
                job.schedule_removal()

    cancel_order(order_id, "ALLY")
    delete_offer_queue(order_id)

    # Limpiar bot_data
    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    context.bot_data.get("offer_messages", {}).pop(order_id, None)

    query.edit_message_text("Pedido cancelado. No se aplico ningun cargo.")

    if had_courier:
        _notify_courier_order_cancelled(context, order)


def _handle_cancel_ally_route(update, context, route_id):
    """Aliado cancela una ruta. Mismo comportamiento que cancelar un pedido individual."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route:
        query.edit_message_text("Ruta no encontrada.")
        return

    if route["status"] not in ("PUBLISHED", "ACCEPTED"):
        query.edit_message_text(
            "No se puede cancelar la ruta #{} en su estado actual.".format(route_id)
        )
        return

    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    ally = get_ally_by_user_id(user["id"]) if user else None
    if not ally or ally["id"] != route["ally_id"]:
        query.edit_message_text("No tienes permiso para cancelar esta ruta.")
        return

    had_courier = route["status"] == "ACCEPTED" and route["courier_id"]
    was_published = route["status"] == "PUBLISHED"

    # Cancelar jobs de oferta y sugerencia T+5
    _cancel_route_no_response_job(context, route_id)
    if was_published:
        current = get_current_route_offer(route_id)
        if current:
            _cancel_route_offer_jobs(context, route_id, current["queue_id"])
            mark_route_offer_response(current["queue_id"], "CANCELLED")

    cancel_route(route_id, "ALLY")
    delete_route_offer_queue(route_id)

    # Limpiar bot_data de oferta
    context.bot_data.get("route_offer_cycles", {}).pop(route_id, None)
    context.bot_data.get("route_offer_messages", {}).pop(route_id, None)

    query.edit_message_text("Ruta cancelada. No se aplico ningun cargo.")

    if had_courier:
        try:
            courier = get_courier_by_id(route["courier_id"])
            if courier:
                courier_user = get_user_by_id(courier["user_id"])
                if courier_user and courier_user["telegram_id"]:
                    context.bot.send_message(
                        chat_id=courier_user["telegram_id"],
                        text="La ruta #{} fue cancelada por el aliado.".format(route_id),
                    )
        except Exception as e:
            print("[WARN] No se pudo notificar cancelacion de ruta al courier: {}".format(e))


def _handle_pickup(update, context, order_id):
    """Confirma manualmente la llegada del courier una vez el GPS detecta cercania al pickup."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    if order["status"] != "ACCEPTED":
        query.edit_message_text("Este pedido no esta en estado de recogida.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != order["courier_id"]:
        query.edit_message_text("No tienes permiso para confirmar este pedido.")
        return

    if _row_value(order, "courier_arrived_at"):
        query.edit_message_text(
            "Ya confirmaste tu llegada al punto de recogida del pedido #{}.\n\n"
            "Espera la confirmacion del aliado o libera el pedido si surge un problema.".format(order_id),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order_id))]]
            ),
        )
        return

    courier = get_courier_by_id(courier["id"]) or courier
    if not _courier_is_within_pickup_radius(order, courier):
        pickup_lat, pickup_lng = _get_pickup_coords(order)
        keyboard = []
        keyboard.extend(_build_navigation_rows(pickup_lat, pickup_lng))
        keyboard.append([InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order_id))])
        query.edit_message_text(
            "Aun no podemos confirmar tu llegada al pedido #{}.\n\n"
            "Acercate mas al punto de recogida y vuelve a presionar \"Confirmar llegada\" cuando estes alli."
            .format(order_id),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    set_courier_arrived(order_id)
    _cancel_arrival_jobs(context, order_id)
    courier_name = courier["full_name"] or "Repartidor"

    # Pedido de admin (sin aliado): auto-confirmar y revelar datos directamente
    if not order["ally_id"]:
        query.edit_message_text("Pedido #{} - Llegada confirmada.".format(order_id))
        _notify_courier_pickup_approved(context, order)
        return

    upsert_order_pickup_confirmation(order_id, courier["id"], order["ally_id"], "PENDING")
    _notify_ally_courier_arrived(context, order, courier_name)

    keyboard = [[InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order_id))]]
    query.edit_message_text(
        "Pedido #{} - Llegada confirmada.\n\n"
        "Avisamos al aliado para que confirme tu llegada al punto de recogida.\n"
        "Cuando confirme, te enviaremos la ruta al punto de entrega.".format(order_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return


def _handle_pickup_confirmation_by_ally(update, context, order_id, approve):
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    ally = get_ally_by_user_id(user["id"]) if user else None
    if not ally or ally["id"] != order["ally_id"]:
        query.edit_message_text("No tienes permiso para confirmar esta recogida.")
        return

    confirmation = get_order_pickup_confirmation(order_id)
    if not confirmation:
        query.edit_message_text("No hay solicitud de recogida pendiente para este pedido.")
        return
    if confirmation["status"] != "PENDING":
        query.edit_message_text("Esta solicitud ya fue revisada.")
        return

    new_status = "APPROVED" if approve else "REJECTED"
    if not review_order_pickup_confirmation(order_id, new_status, ally["id"]):
        query.edit_message_text("No se pudo actualizar la confirmacion. Intenta de nuevo.")
        return

    if approve:
        query.edit_message_text("Llegada confirmada. Esperando que el repartidor confirme la recogida del pedido.")
        _notify_courier_awaiting_pickup_confirm(context, order)
    else:
        query.edit_message_text("Recogida rechazada. El repartidor fue notificado.")
        _notify_courier_pickup_rejected(context, order)
    return


def _handle_delivered(update, context, order_id):
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    _cancel_arrival_jobs(context, order_id)
    _cancel_delivery_reminder_jobs(context, order_id)

    if order["status"] != "PICKED_UP":
        query.edit_message_text("Este pedido no esta en estado de entrega.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != order["courier_id"]:
        query.edit_message_text("No tienes permiso para marcar este pedido.")
        return

    courier_id = courier["id"]
    ally_id = order["ally_id"]

    # Red cooperativa: fee del aliado → su propio admin; fee del courier → su propio admin.
    ally_admin_link = get_approved_admin_link_for_ally(ally_id)
    ally_admin_id = ally_admin_link["admin_id"] if ally_admin_link else None

    # Usar snapshot guardado en _handle_accept; fallback al admin actual del courier
    courier_admin_id = order["courier_admin_id_snapshot"] if "courier_admin_id_snapshot" in order.keys() else None
    if courier_admin_id is None:
        courier_admin_link = get_approved_admin_link_for_courier(courier_id)
        courier_admin_id = courier_admin_link["admin_id"] if courier_admin_link else None

    fee_ally_ok = False
    fee_courier_ok = False

    if ally_admin_id and not check_ally_active_subscription(ally_id):
        ally_ok, ally_msg = apply_service_fee(
            target_type="ALLY",
            target_id=ally_id,
            admin_id=ally_admin_id,
            ref_type="ORDER",
            ref_id=order_id,
            total_fee=order["total_fee"],
        )
        if ally_ok:
            fee_ally_ok = True
        else:
            print("[WARN] No se pudo cobrar fee al aliado: {}".format(ally_msg))
    elif ally_admin_id:
        fee_ally_ok = True  # suscripcion activa — sin cobro

    if courier_admin_id:
        courier_ok, courier_msg = apply_service_fee(
            target_type="COURIER",
            target_id=courier_id,
            admin_id=courier_admin_id,
            ref_type="ORDER",
            ref_id=order_id,
        )
        if courier_ok:
            fee_courier_ok = True
            # Notificar al courier si su saldo quedo insuficiente para el proximo servicio
            try:
                new_balance = get_courier_link_balance(courier_id, courier_admin_id)
                if new_balance < 300:
                    deactivate_courier(courier_id)
                    try:
                        courier_row = get_courier_by_id(courier_id)
                        if courier_row:
                            user = get_user_by_id(courier_row["user_id"])
                            if user and user["telegram_id"]:
                                context.bot.send_message(
                                    chat_id=user["telegram_id"],
                                    text=(
                                        "Has sido desactivado automaticamente.\n\n"
                                        "Tu saldo operativo quedo en ${:,} tras el cobro del servicio "
                                        "y necesitas al menos $300 para seguir recibiendo pedidos.\n\n"
                                        "Solicita una recarga a tu administrador y vuelve a activarte.".format(new_balance)
                                    ),
                                )
                    except Exception:
                        pass
            except Exception as e:
                print("[WARN] No se pudo verificar saldo post-fee del courier {}: {}".format(courier_id, e))
        else:
            if courier_msg == "ADMIN_SIN_SALDO":
                try:
                    admin_row = get_admin_by_id(courier_admin_id)
                    if admin_row:
                        admin_user = get_user_by_id(admin_row["user_id"])
                        if admin_user and admin_user["telegram_id"]:
                            context.bot.send_message(
                                chat_id=admin_user["telegram_id"],
                                text=(
                                    "Tu equipo no puede operar porque no tienes saldo. "
                                    "Recarga con plataforma para que tu equipo siga generando ganancias."
                                ),
                            )
                except Exception as e:
                    print("[WARN] No se pudo notificar al admin: {}".format(e))
            print("[WARN] No se pudo cobrar fee al courier: {}".format(courier_msg))

    try:
        ally_fee_charged = 300 if fee_ally_ok else 0
        courier_fee_charged = 300 if fee_courier_ok else 0
        creator_admin_id = order["creator_admin_id"] if "creator_admin_id" in order.keys() else None
        settlement_admin_id = creator_admin_id or ally_admin_id or courier_admin_id
        settlement_note = (
            "Fees cobrados OK"
            if (fee_ally_ok and fee_courier_ok)
            else "Cobro parcial o pendiente de fees al entregar"
        )
        upsert_order_accounting_settlement(
            order_id=order_id,
            admin_id=settlement_admin_id,
            ally_id=ally_id,
            courier_id=courier_id,
            order_total_fee=int(order["total_fee"] or 0),
            ally_fee_expected=300,
            ally_fee_charged=ally_fee_charged,
            courier_fee_expected=300,
            courier_fee_charged=courier_fee_charged,
            note=settlement_note,
            delivered_at=None,
        )
    except Exception as e:
        print("[WARN] No se pudo registrar liquidacion contable de pedido {}: {}".format(order_id, e))

    set_order_status(order_id, "DELIVERED", "delivered_at")
    delete_offer_queue(order_id)

    durations = _get_order_durations(order, delivered_now=True)

    time_lines = []
    if "llegada_aliado" in durations:
        time_lines.append("  Llegada al aliado: {}".format(_format_duration(durations["llegada_aliado"])))
    if "entrega_cliente" in durations:
        time_lines.append("  Entrega al cliente: {}".format(_format_duration(durations["entrega_cliente"])))
    if "tiempo_total" in durations:
        time_lines.append("  Tiempo total: {}".format(_format_duration(durations["tiempo_total"])))

    time_block = ("\n\nTiempos del servicio:\n" + "\n".join(time_lines)) if time_lines else ""


    if fee_courier_ok:
        courier_msg = (
            "Pedido #{} entregado exitosamente.{}\n\n"
            "Se descontaron $300 de tu saldo por este servicio."
        ).format(order_id, time_block)
    else:
        courier_msg = "Pedido #{} entregado exitosamente.{}".format(order_id, time_block)

    query.edit_message_text(courier_msg)

    _notify_ally_delivered(context, order, durations)


def _build_offer_text(
    order,
    courier_dist_km=None,
    pickup_city_override=None,
    pickup_barrio_override=None,
    dropoff_city_override=None,
    dropoff_barrio_override=None,
):
    """Construye el texto de oferta para el courier."""
    pickup_city, pickup_barrio = _get_pickup_area(order)
    if pickup_city_override is not None:
        pickup_city = pickup_city_override
    if pickup_barrio_override is not None:
        pickup_barrio = pickup_barrio_override

    dropoff_city, dropoff_barrio = _get_dropoff_area(order)
    if dropoff_city_override is not None:
        dropoff_city = dropoff_city_override
    if dropoff_barrio_override is not None:
        dropoff_barrio = dropoff_barrio_override

    distance_km = order["distance_km"] or 0
    total_fee = int(order["total_fee"] or 0)
    additional_incentive = int(order["additional_incentive"] or 0)

    text = (
        "OFERTA DISPONIBLE\n\n"
        "Pedido: #{}\n"
        "Recoges en el barrio o sector {} de la ciudad de {}\n"
        "Entrega en el barrio o sector {} de la ciudad de {}\n"
        "Distancia de entrega: {:.1f} km\n"
        "Pago total: ${:,}\n"
    ).format(
        order["id"],
        (pickup_barrio or "No disponible"),
        (pickup_city or "No disponible"),
        (dropoff_barrio or "No disponible"),
        (dropoff_city or "No disponible"),
        distance_km,
        total_fee,
    )

    if courier_dist_km is not None:
        eta_min = max(1, round(courier_dist_km / 25 * 60))
        text += "Tu distancia al punto de recogida: {:.1f} km (~{} min)\n".format(
            courier_dist_km, eta_min
        )

    if additional_incentive > 0:
        base_fee = max(0, total_fee - additional_incentive)
        text += "Pago base: ${:,}\n".format(int(base_fee))
        text += "Incentivo adicional: ${:,}\n".format(int(additional_incentive))

    cash_amount = order["cash_required_amount"] or 0
    payment_method = order["payment_method"] or "UNCONFIRMED"

    if payment_method == "CASH_CONFIRMED":
        text += "Pago: efectivo confirmado\n"
        if cash_amount > 0:
            text += "Base requerida: ${:,}\n".format(int(cash_amount))
            text += "\nADVERTENCIA: Si no tienes base suficiente, NO tomes este servicio.\n"
    elif payment_method == "TRANSFER_CONFIRMED":
        text += "Pago: transferencia confirmada\n"
    else:
        text += "Pago: no confirmado (no debes adelantar dinero)\n"

    instructions = order["instructions"] or ""
    if instructions.strip():
        text += "\nInstrucciones: {}\n".format(instructions.strip())

    text += "\nAviso: una vez aceptado tienes 15 min para llegar al punto de recogida.\n"

    parking_fee = int(order["parking_fee"] or 0) if "parking_fee" in order.keys() else 0
    if parking_fee > 0:
        text += (
            "\nATENCION: El punto de entrega tiene dificultad para parquear moto o bicicleta. "
            "Se incluyen ${:,} para que cubras el parqueo o cualquier imprevisto con tu vehiculo. "
            "No dejes tu moto o bici en lugar prohibido — comparendos o inmovilizaciones "
            "son tu responsabilidad.\n".format(parking_fee)
        )

    return text


def _get_pickup_address(order):
    """Obtiene direccion de recogida usando pickup_location_id o default del aliado."""
    pickup_location_id = _row_value(order, "pickup_location_id")
    ally_id = _row_value(order, "ally_id")

    if pickup_location_id and ally_id:
        location = get_ally_location_by_id(pickup_location_id, ally_id)
        if location:
            return _row_value(location, "address", "No disponible") or "No disponible"

    default_loc = get_default_ally_location(ally_id)
    if default_loc:
        return _row_value(default_loc, "address", "No disponible")
    return "No disponible"


def _row_value(row, key, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        return default


def _get_pickup_coords(order):
    lat = _row_value(order, "pickup_lat")
    lng = _row_value(order, "pickup_lng")
    if lat is not None and lng is not None:
        return lat, lng

    pickup_location_id = _row_value(order, "pickup_location_id")
    ally_id = _row_value(order, "ally_id")
    if pickup_location_id and ally_id:
        location = get_ally_location_by_id(pickup_location_id, ally_id)
        if location:
            lat = _row_value(location, "lat")
            lng = _row_value(location, "lng")
            if lat is not None and lng is not None:
                return lat, lng

    default_loc = get_default_ally_location(ally_id)
    if default_loc:
        lat = _row_value(default_loc, "lat")
        lng = _row_value(default_loc, "lng")
        if lat is not None and lng is not None:
            return lat, lng
    return None, None


def _get_pickup_area(order):
    pickup_location_id = _row_value(order, "pickup_location_id")
    ally_id = _row_value(order, "ally_id")

    if pickup_location_id and ally_id:
        location = get_ally_location_by_id(pickup_location_id, ally_id)
        if location:
            return _row_value(location, "city"), _row_value(location, "barrio")

    default_loc = get_default_ally_location(ally_id) if ally_id else None
    if default_loc:
        return _row_value(default_loc, "city"), _row_value(default_loc, "barrio")

    return None, None


def _get_dropoff_area(order):
    return _row_value(order, "customer_city"), _row_value(order, "customer_barrio")


def _get_dropoff_coords(order):
    lat = _row_value(order, "dropoff_lat")
    lng = _row_value(order, "dropoff_lng")
    if lat is None or lng is None:
        return None, None
    return lat, lng


def _build_navigation_rows(lat, lng):
    if lat is None or lng is None:
        return []
    destination = "{},{}".format(float(lat), float(lng))
    gmaps_url = "https://www.google.com/maps/dir/?api=1&destination={}&travelmode=driving".format(destination)
    waze_url = "https://waze.com/ul?ll={}&navigate=yes".format(destination)
    return [
        [InlineKeyboardButton("Abrir en Google Maps", url=gmaps_url)],
        [InlineKeyboardButton("Abrir en Waze", url=waze_url)],
    ]


def _notify_ally_order_accepted(context, order, courier_name):
    try:
        ally = get_ally_by_id(order["ally_id"])
        if not ally:
            return

        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user["telegram_id"]:
            return

        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "Tu pedido #{} fue aceptado por el repartidor {}.\n"
                "El repartidor se dirige al punto de recogida."
            ).format(order["id"], courier_name),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Llamar al repartidor",
                    callback_data="order_call_courier_{}".format(order["id"]),
                )
            ]]),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar al aliado: {}".format(e))


def _notify_ally_courier_arrived(context, order, courier_name):
    """Notifica al aliado que el courier confirmo manualmente su llegada al pickup."""
    try:
        ally = get_ally_by_id(order["ally_id"])
        if not ally:
            return
        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user["telegram_id"]:
            return
        order_id = order["id"]
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Confirmar llegada",
                    callback_data="order_pickupconfirm_approve_{}".format(order_id),
                ),
                InlineKeyboardButton(
                    "No ha llegado",
                    callback_data="order_pickupconfirm_reject_{}".format(order_id),
                ),
            ]
        ])
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "El repartidor {} confirmo su llegada al punto de recogida (pedido #{}).\n\n"
                "Confirma su llegada para que reciba los datos del cliente y proceda a entregar."
            ).format(courier_name, order_id),
            reply_markup=keyboard,
        )
    except Exception as e:
        print("[WARN] _notify_ally_courier_arrived: {}".format(e))


def _notify_courier_awaiting_pickup_confirm(context, order):
    """Notifica al courier que el aliado confirmo su llegada y debe confirmar que recogió el pedido."""
    try:
        if not order["courier_id"]:
            return
        courier = get_courier_by_id(order["courier_id"])
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=(
                "El aliado confirmo tu llegada al punto de recogida - Pedido #{}\n\n"
                "Confirma que ya recogiste el pedido para continuar."
            ).format(order["id"]),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Confirmar recogida",
                    callback_data="order_confirm_pickup_{}".format(order["id"])
                )
            ]]),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar confirmacion pendiente al courier: {}".format(e))


def _handle_confirm_pickup(update, context, order_id):
    """Courier confirma que recogió el pedido. Transiciona a PICKED_UP y revela datos del cliente."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return
    if order["status"] != "ACCEPTED":
        query.edit_message_text("Este pedido ya no requiere confirmacion de recogida.")
        return
    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != order["courier_id"]:
        query.edit_message_text("No tienes permiso para confirmar este pedido.")
        return
    set_order_status(order_id, "PICKED_UP", "pickup_confirmed_at")
    query.edit_message_text("Recogida confirmada. A continuacion encontraras los datos de entrega.")
    _notify_courier_pickup_approved(context, get_order_by_id(order_id))
    context.job_queue.run_once(
        _delivery_reminder_job,
        DELIVERY_REMINDER_SECONDS,
        context={"order_id": order_id},
        name="delivery_reminder_{}".format(order_id),
    )
    context.job_queue.run_once(
        _delivery_admin_alert_job,
        DELIVERY_ADMIN_ALERT_SECONDS,
        context={"order_id": order_id},
        name="delivery_admin_alert_{}".format(order_id),
    )


def _notify_courier_pickup_approved(context, order):
    """Envia al courier los datos de entrega tras confirmar la recogida."""
    try:
        if not order["courier_id"]:
            return
        courier = get_courier_by_id(order["courier_id"])
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return

        dropoff_lat, dropoff_lng = _get_dropoff_coords(order)
        keyboard = []
        keyboard.extend(_build_navigation_rows(dropoff_lat, dropoff_lng))
        keyboard.append([InlineKeyboardButton("Finalizar servicio", callback_data="order_delivered_confirm_{}".format(order["id"]))])
        parking_fee = int(order["parking_fee"] or 0) if "parking_fee" in order.keys() else 0
        parking_aviso = ""
        if parking_fee > 0:
            parking_aviso = (
                "\n\nRECUERDA: Este punto tiene dificultad de parqueo (${:,} incluidos). "
                "Asegurate de dejar tu vehiculo en un lugar seguro y legal antes de entregar.".format(parking_fee)
            )
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=(
                "Datos de entrega - Pedido #{}\n\n"
                "Entrega en: {}\n"
                "Cliente: {}\n"
                "Telefono: {}{}\n\n"
                "Dirigete al punto de entrega. Solo podras finalizar el servicio cuando estes "
                "a menos de 100 metros del lugar de entrega."
            ).format(
                order["id"],
                order["customer_address"] or "No disponible",
                order["customer_name"] or "No disponible",
                order["customer_phone"] or "No disponible",
                parking_aviso,
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        if dropoff_lat is not None and dropoff_lng is not None:
            context.bot.send_location(
                chat_id=courier_user["telegram_id"],
                latitude=float(dropoff_lat),
                longitude=float(dropoff_lng),
            )
    except Exception as e:
        print("[WARN] No se pudo notificar confirmacion de recogida al courier: {}".format(e))


def _notify_courier_pickup_rejected(context, order):
    """Notifica al courier que el aliado rechazo la confirmacion de recogida."""
    try:
        if not order["courier_id"]:
            return
        courier = get_courier_by_id(order["courier_id"])
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return

        keyboard = [
            [InlineKeyboardButton("Solicitar confirmacion nuevamente", callback_data="order_pickup_{}".format(order["id"]))],
            [InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order["id"]))],
        ]
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=(
                "El aliado rechazo la confirmacion de llegada del pedido #{}.\n"
                "Verifica en el punto de recogida y vuelve a confirmar tu llegada."
            ).format(order["id"]),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar rechazo de recogida al courier: {}".format(e))


def _notify_ally_delivered(context, order, durations=None):
    """Notifica al aliado que el pedido fue entregado y solicita calificacion del servicio."""
    try:
        ally = get_ally_by_id(order["ally_id"])
        if not ally:
            return
        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user["telegram_id"]:
            return

        courier = get_courier_by_id(order["courier_id"]) if order["courier_id"] else None
        courier_name = (courier["full_name"] if courier else None) or "el repartidor"
        order_id = order["id"]

        time_lines = []
        if durations:
            if "llegada_aliado" in durations:
                time_lines.append("  Llegada del repartidor: {}".format(_format_duration(durations["llegada_aliado"])))
            if "entrega_cliente" in durations:
                time_lines.append("  Tiempo de entrega: {}".format(_format_duration(durations["entrega_cliente"])))
        time_block = ("\n\nTiempos del servicio:\n" + "\n".join(time_lines)) if time_lines else ""


        keyboard = [[
            InlineKeyboardButton("1", callback_data="rating_star_{}_1".format(order_id)),
            InlineKeyboardButton("2", callback_data="rating_star_{}_2".format(order_id)),
            InlineKeyboardButton("3", callback_data="rating_star_{}_3".format(order_id)),
            InlineKeyboardButton("4", callback_data="rating_star_{}_4".format(order_id)),
            InlineKeyboardButton("5", callback_data="rating_star_{}_5".format(order_id)),
        ]]
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "Pedido #{} entregado exitosamente por {}.{}\n\n"
                "Como calificarias el servicio?\n"
                "1 = Muy malo  |  5 = Excelente"
            ).format(order_id, courier_name, time_block),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar entrega al aliado: {}".format(e))

def handle_rating_callback(update, context):
    """Maneja la calificacion del servicio por parte del aliado tras la entrega."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("rating_star_"):
        parts = data.split("_")
        order_id = int(parts[2])
        stars = int(parts[3])

        order = get_order_by_id(order_id)
        if not order or not order["courier_id"]:
            query.edit_message_text("Pedido no encontrado.")
            return

        courier_id = order["courier_id"]
        try:
            add_courier_rating(order_id, courier_id, stars)
        except Exception as e:
            print("[WARN] No se pudo registrar calificacion orden {}: {}".format(order_id, e))

        if stars >= 4:
            query.edit_message_text(
                "Gracias por tu calificacion ({}/5). "
                "Seguiremos mejorando el servicio.".format(stars)
            )
            return

        # Calificacion baja: ofrecer bloquear al courier
        courier = get_courier_by_id(courier_id)
        courier_name = (courier["full_name"] if courier else None) or "este repartidor"
        keyboard = [[
            InlineKeyboardButton(
                "Si, bloquear",
                callback_data="rating_block_{}_{}".format(courier_id, order_id),
            ),
            InlineKeyboardButton(
                "No, gracias",
                callback_data="rating_skip_{}".format(order_id),
            ),
        ]]
        query.edit_message_text(
            "Calificacion guardada ({}/5).\n\n"
            "Deseas bloquear a {} para que tus pedidos no le lleguen?".format(
                stars, courier_name
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("rating_block_"):
        # rating_block_{courier_id}_{order_id}
        parts = data.split("_")
        courier_id = int(parts[2])

        telegram_id = update.effective_user.id
        user = get_user_by_telegram_id(telegram_id)
        if not user:
            query.edit_message_text("Usuario no encontrado.")
            return

        ally = get_ally_by_user_id(user["id"])
        if not ally:
            query.edit_message_text("Solo aliados pueden bloquear repartidores.")
            return

        try:
            block_courier_for_ally(ally["id"], courier_id)
        except Exception as e:
            print("[WARN] No se pudo bloquear courier {}: {}".format(courier_id, e))

        courier = get_courier_by_id(courier_id)
        courier_name = (courier["full_name"] if courier else None) or "el repartidor"
        query.edit_message_text(
            "{} fue bloqueado. No recibira mas tus ofertas.\n"
            "Puedes desbloquearlo en cualquier momento desde Mis repartidores.".format(courier_name)
        )

    elif data.startswith("rating_skip_"):
        query.edit_message_text(
            "Gracias por tu calificacion. Seguiremos mejorando el servicio."
        )


def _notify_courier_order_cancelled(context, order):
    """Notifica al courier que el aliado cancelo el pedido."""
    try:
        if not order["courier_id"]:
            return
        courier = get_courier_by_id(order["courier_id"])
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text="El pedido #{} fue cancelado por el aliado.".format(order["id"]),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar cancelacion al courier: {}".format(e))


def _notify_ally_order_released(context, order, reason_label=None):
    """Notifica al aliado que el courier libero el pedido."""
    try:
        ally = get_ally_by_id(order["ally_id"])
        if not ally:
            return
        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user["telegram_id"]:
            return
        reason_line = ""
        if reason_label:
            reason_line = "\nMotivo: {}".format(reason_label)
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "El repartidor libero tu pedido #{}.{}\n"
                "Estamos buscando otro repartidor."
            ).format(order["id"], reason_line),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar liberacion al aliado: {}".format(e))


def _notify_admin_order_released(context, order, courier, reason_label, arrived_flag):
    """Notifica al admin del equipo (si existe) cuando un courier libera un pedido."""
    try:
        admin_id = _row_value(order, "courier_admin_id_snapshot")
        if not admin_id:
            courier_admin_link = get_approved_admin_link_for_courier(courier["id"])
            admin_id = courier_admin_link["admin_id"] if courier_admin_link else None
        if not admin_id:
            return
        admin = get_admin_by_id(admin_id)
        if not admin:
            return
        admin_user = get_user_by_id(admin["user_id"])
        if not admin_user or not admin_user["telegram_id"]:
            return
        courier_name = (courier["full_name"] or "").strip() or "Repartidor"
        context.bot.send_message(
            chat_id=admin_user["telegram_id"],
            text=(
                "ALERTA: liberacion de pedido\n\n"
                "Pedido: #{}\n"
                "Courier: {}\n"
                "Llego al pickup: {}\n"
                "Motivo: {}\n\n"
                "Accion: revisar si es justificado. Liberar para evitar comision es falta grave."
            ).format(
                order["id"],
                courier_name,
                arrived_flag,
                reason_label,
            ),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar liberacion al admin: {}".format(e))


# ===== FLUJO DE RUTAS MULTI-PARADA =====

ROUTE_OFFER_TIMEOUT_SECONDS = 30
ROUTE_MAX_CYCLE_SECONDS = 420  # 7 minutos


def _route_offer_reply_markup(route_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Aceptar", callback_data="ruta_aceptar_{}".format(route_id)),
            InlineKeyboardButton("Rechazar", callback_data="ruta_rechazar_{}".format(route_id)),
        ],
        [InlineKeyboardButton("Estoy ocupado", callback_data="ruta_ocupado_{}".format(route_id))],
    ])


def _build_route_offer_text(route, destinations):
    """Construye el texto de oferta de ruta para el courier."""
    total_km = float(route["total_distance_km"] or 0)
    total_fee = int(route["total_fee"] or 0)
    additional_incentive = int(route["additional_incentive"] or 0)

    # Barrio/ciudad de recogida
    pickup_city = route["pickup_city"] or ""
    pickup_barrio = route["pickup_barrio"] or ""
    if not pickup_city and not pickup_barrio:
        pickup_area = route["pickup_address"] or "No disponible"
    elif pickup_barrio and pickup_city:
        pickup_area = "{}, {}".format(pickup_barrio, pickup_city)
    else:
        pickup_area = pickup_barrio or pickup_city

    text = "RUTA DISPONIBLE\n\nRuta #{}\nRecogida: {}\n\n".format(route["id"], pickup_area)
    text += "{} paradas:\n".format(len(destinations))

    for dest in destinations:
        barrio = dest["customer_barrio"] or ""
        city = dest["customer_city"] or ""
        if barrio and city:
            area = "{}, {}".format(barrio, city)
        elif barrio or city:
            area = barrio or city
        else:
            area = dest["customer_address"] or "Sin direccion"
        text += "  Parada {}: {}\n".format(dest["sequence"], area)

    text += "\nDistancia total: {:.1f} km\n".format(total_km)

    if additional_incentive > 0:
        base_fee = max(0, total_fee - additional_incentive)
        text += "Pago base: ${:,}\n".format(base_fee)
        text += "Incentivo adicional: ${:,}\n".format(additional_incentive)
        text += "Pago total: ${:,}\n".format(total_fee)
    else:
        text += "Pago: ${:,}\n".format(total_fee)

    text += "\nAviso: una vez aceptada tienes 15 min para llegar a la recogida.\n"

    return text


def _cancel_route_offer_jobs(context, route_id, queue_id):
    timeout_jobs = context.job_queue.get_jobs_by_name(
        "route_offer_timeout_{}_{}".format(route_id, queue_id)
    )
    for job in timeout_jobs:
        job.schedule_removal()


def _route_offer_timeout_job(context):
    """Job ejecutado cuando expira el timeout de oferta de ruta."""
    job_data = context.job.context
    route_id = job_data["route_id"]
    queue_id = job_data["queue_id"]

    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        return

    current = get_current_route_offer(route_id)
    if not current or current["queue_id"] != queue_id:
        return

    _cancel_route_offer_jobs(context, route_id, queue_id)
    mark_route_offer_response(queue_id, "EXPIRED")

    msg_info = context.bot_data.get("route_offer_messages", {}).get(route_id)
    if msg_info:
        try:
            context.bot.edit_message_text(
                chat_id=msg_info["chat_id"],
                message_id=msg_info["message_id"],
                text="Ruta #{} expirada. No respondiste a tiempo.".format(route_id),
            )
        except Exception:
            pass

    _send_next_route_offer(route_id, context)


def _try_restart_route_cycle(route_id, context):
    cycle_info = context.bot_data.get("route_offer_cycles", {}).get(route_id)
    if not cycle_info:
        return

    import time
    elapsed = time.time() - cycle_info["started_at"]

    if elapsed >= ROUTE_MAX_CYCLE_SECONDS:
        _expire_route(route_id, cycle_info, context)
        return

    reset_route_offer_queue(route_id)
    _send_next_route_offer(route_id, context)


def _expire_route(route_id, cycle_info, context):
    """Nadie acepto la ruta en 7 minutos. Cancela la ruta."""
    _cancel_route_no_response_job(context, route_id)
    cancel_route(route_id, "SYSTEM")
    delete_route_offer_queue(route_id)

    context.bot_data.get("route_offer_cycles", {}).pop(route_id, None)
    context.bot_data.get("route_offer_messages", {}).pop(route_id, None)

    ally_id = cycle_info.get("ally_id")
    try:
        ally = get_ally_by_id(ally_id)
        if ally:
            ally_user = get_user_by_id(ally["user_id"])
            if ally_user and ally_user["telegram_id"]:
                context.bot.send_message(
                    chat_id=ally_user["telegram_id"],
                    text=(
                        "Tu ruta #{} fue cancelada porque ningun repartidor "
                        "la acepto en 7 minutos."
                    ).format(route_id),
                )
    except Exception as e:
        print("[WARN] No se pudo notificar expiracion de ruta al aliado: {}".format(e))


def _send_next_route_offer(route_id, context):
    """Envia la oferta de ruta al siguiente courier en la cola."""
    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        return

    next_offer = get_next_pending_route_offer(route_id)
    if not next_offer:
        _try_restart_route_cycle(route_id, context)
        return

    mark_route_offer_as_offered(next_offer["queue_id"])

    destinations = get_route_destinations(route_id)
    offer_text = "SERVICIO DISPONIBLE\n\n" + _build_route_offer_text(route, destinations)
    reply_markup = _route_offer_reply_markup(route_id)

    try:
        msg = context.bot.send_message(
            chat_id=next_offer["telegram_id"],
            text=offer_text,
            reply_markup=reply_markup,
        )
        context.bot_data.setdefault("route_offer_messages", {})[route_id] = {
            "chat_id": next_offer["telegram_id"],
            "message_id": msg.message_id,
        }
    except Exception as e:
        print("[WARN] No se pudo enviar oferta de ruta a courier {}: {}".format(next_offer["courier_id"], e))
        mark_route_offer_response(next_offer["queue_id"], "EXPIRED")
        _send_next_route_offer(route_id, context)
        return

    context.job_queue.run_once(
        _route_offer_timeout_job,
        ROUTE_OFFER_TIMEOUT_SECONDS,
        context={"route_id": route_id, "queue_id": next_offer["queue_id"]},
        name="route_offer_timeout_{}_{}".format(route_id, next_offer["queue_id"]),
    )


def publish_route_to_couriers(route_id, ally_id, context, admin_id_override=None):
    """Publica una ruta a la cola de couriers. Retorna cantidad de couriers en cola."""
    if admin_id_override:
        admin_id = admin_id_override
    else:
        link = get_approved_admin_link_for_ally(ally_id)
        if not link:
            return 0
        admin_id = link["admin_id"]

    route = get_route_by_id(route_id)
    if not route:
        return 0

    pickup_lat = route["pickup_lat"]
    pickup_lng = route["pickup_lng"]

    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=False,
        cash_required_amount=0,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
    )

    if not eligible:
        return 0

    # Filtrar couriers sin saldo suficiente para el fee de servicio ($300)
    # El sistema no ofrece el servicio a couriers que no puedan pagarlo al finalizar
    couriers_con_saldo = []
    for c in eligible:
        c_id = c["courier_id"]
        c_admin_id = get_approved_admin_id_for_courier(c_id)
        if not c_admin_id:
            continue
        fee_ok, _ = check_service_fee_available("COURIER", c_id, c_admin_id)
        if fee_ok:
            couriers_con_saldo.append(c_id)

    if not couriers_con_saldo:
        return 0

    courier_ids = couriers_con_saldo
    create_route_offer_queue(route_id, courier_ids)
    update_route_status(route_id, "PUBLISHED", "published_at")

    import time
    context.bot_data.setdefault("route_offer_cycles", {})[route_id] = {
        "started_at": time.time(),
        "admin_id": admin_id,
        "ally_id": ally_id,
    }

    _send_next_route_offer(route_id, context)

    # Programar sugerencia de incentivo T+5 si nadie acepta la ruta
    _cancel_route_no_response_job(context, route_id)
    context.job_queue.run_once(
        _route_no_response_job,
        OFFER_NO_RESPONSE_SECONDS,
        context={"route_id": route_id},
        name="route_no_response_{}".format(route_id),
    )

    return len(courier_ids)


def _send_route_stop_to_courier(context, chat_id, route, stop):
    """Envia los detalles de una parada al courier."""
    route_id = route["id"]
    seq = stop["sequence"]
    lat = stop["dropoff_lat"]
    lng = stop["dropoff_lng"]
    total_stops = len(get_route_destinations(route_id))

    keyboard = []
    keyboard.extend(_build_navigation_rows(lat, lng))
    keyboard.append([
        InlineKeyboardButton(
            "Confirmar entrega parada {}".format(seq),
            callback_data="ruta_entregar_{}_{}".format(route_id, seq)
        )
    ])
    keyboard.append([InlineKeyboardButton("Liberar ruta", callback_data="ruta_liberar_{}".format(route_id))])

    stop_instructions = stop["instructions"] or ""
    instr_line = "Instrucciones: {}\n".format(stop_instructions.strip()) if stop_instructions.strip() else ""

    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "Parada {} de {}:\n\n"
            "Cliente: {}\n"
            "Telefono: {}\n"
            "Direccion: {}\n"
            "{}"
            "\nDirigete a la parada y confirma la entrega cuando termines."
        ).format(
            seq,
            total_stops,
            stop["customer_name"] or "Sin nombre",
            stop["customer_phone"] or "Sin telefono",
            stop["customer_address"] or "Sin direccion",
            instr_line,
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    if lat is not None and lng is not None:
        try:
            context.bot.send_location(chat_id=chat_id, latitude=float(lat), longitude=float(lng))
        except Exception:
            pass


def _handle_route_accept(update, context, route_id):
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route:
        query.edit_message_text("Ruta no encontrada.")
        return

    if route["status"] != "PUBLISHED":
        query.edit_message_text("Esta oferta ya no esta disponible.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        query.edit_message_text("No se encontro tu perfil de repartidor.")
        return

    current = get_current_route_offer(route_id)
    if not current or current["courier_id"] != courier["id"]:
        query.edit_message_text("Esta oferta ya no esta disponible para ti.")
        return

    active_order = get_active_order_for_courier(courier["id"])
    if active_order:
        query.edit_message_text(
            "No puedes aceptar una nueva ruta porque ya tienes un pedido en curso (#{}).".format(
                active_order["id"]
            )
        )
        return

    active_route = get_active_route_for_courier(courier["id"])
    if active_route and active_route["id"] != route_id:
        query.edit_message_text(
            "No puedes aceptar una nueva ruta porque ya tienes una ruta en curso (#{}).".format(
                active_route["id"]
            )
        )
        return

    # Re-verificar saldo antes de asignar (puede haber cambiado desde la publicación)
    courier_id = courier["id"]
    courier_admin_link = get_approved_admin_link_for_courier(courier_id)
    courier_admin_id_snapshot = courier_admin_link["admin_id"] if courier_admin_link else None
    if courier_admin_id_snapshot:
        fee_ok, _ = check_service_fee_available("COURIER", courier_id, courier_admin_id_snapshot)
        if not fee_ok:
            query.edit_message_text(
                "No puedes aceptar esta ruta porque no tienes saldo suficiente.\n"
                "Solicita una recarga a tu administrador."
            )
            return

    _cancel_route_offer_jobs(context, route_id, current["queue_id"])
    _cancel_route_no_response_job(context, route_id)
    mark_route_offer_response(current["queue_id"], "ACCEPTED")
    assign_route_to_courier(route_id, courier_id, courier_admin_id_snapshot)

    context.bot_data.get("route_offer_cycles", {}).pop(route_id, None)
    context.bot_data.get("route_offer_messages", {}).pop(route_id, None)

    route = get_route_by_id(route_id)
    destinations = get_route_destinations(route_id)

    # Guardar posicion del courier al aceptar (base para T+5 de llegada)
    try:
        c_data = get_courier_by_id(courier_id)
        if c_data:
            c_lat = _row_value(c_data, "live_lat") or _row_value(c_data, "residence_lat")
            c_lng = _row_value(c_data, "live_lng") or _row_value(c_data, "residence_lng")
            if c_lat and c_lng:
                context.bot_data.setdefault("route_accepted_pos", {})[route_id] = {
                    "lat": float(c_lat), "lng": float(c_lng)
                }
    except Exception:
        pass

    # Programar timers de llegada al pickup (igual que pedidos)
    context.job_queue.run_once(
        _route_arrival_inactivity_job,
        ARRIVAL_INACTIVITY_SECONDS,
        context={"route_id": route_id, "courier_id": courier_id},
        name="ruta_arr_inactive_{}".format(route_id),
    )
    context.job_queue.run_once(
        _route_arrival_warn_job,
        ARRIVAL_WARN_SECONDS,
        context={"route_id": route_id, "courier_id": courier_id},
        name="ruta_arr_warn_{}".format(route_id),
    )
    context.job_queue.run_once(
        _route_arrival_deadline_job,
        ARRIVAL_DEADLINE_SECONDS,
        context={"route_id": route_id, "courier_id": courier_id},
        name="ruta_arr_deadline_{}".format(route_id),
    )

    _notify_ally_route_accepted(context, route, courier["full_name"] or "Repartidor")

    # Mostrar pantalla de reordenamiento antes de salir a recoger
    _show_route_reorder(query, context, route_id, destinations)


def _show_route_reorder(msg_or_query, context, route_id, destinations):
    """Muestra la lista de paradas con botones para reordenar."""
    text = "Ruta #{} aceptada.\n\nOrden actual de paradas:\n".format(route_id)
    for d in destinations:
        barrio = d["customer_barrio"] or d["customer_address"] or "Sin info"
        text += "  {}. {}\n".format(d["sequence"], barrio)
    text += "\nPuedes cambiar el orden segun tu conveniencia o confirmar el orden actual."

    keyboard = []
    for i, d in enumerate(destinations):
        row = []
        if i > 0:
            row.append(InlineKeyboardButton(
                "↑ Parada {}".format(d["sequence"]),
                callback_data="ruta_orden_up_{}_{}".format(route_id, d["id"])
            ))
        if i < len(destinations) - 1:
            row.append(InlineKeyboardButton(
                "↓ Parada {}".format(d["sequence"]),
                callback_data="ruta_orden_dn_{}_{}".format(route_id, d["id"])
            ))
        if row:
            keyboard.append(row)
    keyboard.append([InlineKeyboardButton(
        "Confirmar orden e ir a recoger",
        callback_data="ruta_orden_ok_{}".format(route_id)
    )])

    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(msg_or_query, "edit_message_text"):
        msg_or_query.edit_message_text(text, reply_markup=markup)
    else:
        msg_or_query.message.reply_text(text, reply_markup=markup)


def _handle_route_reorder(update, context, data):
    """Maneja botones ↑/↓ y confirmacion de orden de paradas."""
    query = update.callback_query

    if data.startswith("ruta_orden_ok_"):
        route_id = int(data.replace("ruta_orden_ok_", ""))
        _show_route_pickup_navigation(query, context, route_id)
        return

    if data.startswith("ruta_orden_up_") or data.startswith("ruta_orden_dn_"):
        up = data.startswith("ruta_orden_up_")
        parts = data.replace("ruta_orden_up_", "").replace("ruta_orden_dn_", "").split("_")
        try:
            route_id = int(parts[0])
            dest_id = int(parts[1])
        except (ValueError, IndexError):
            return
        destinations = get_route_destinations(route_id)
        ids = [d["id"] for d in destinations]
        try:
            idx = ids.index(dest_id)
        except ValueError:
            return
        swap = idx - 1 if up else idx + 1
        if 0 <= swap < len(ids):
            ids[idx], ids[swap] = ids[swap], ids[idx]
            reorder_route_destinations(route_id, ids)
        destinations = get_route_destinations(route_id)
        _show_route_reorder(query, context, route_id, destinations)


def _show_route_pickup_navigation(msg_or_query, context, route_id):
    """Muestra navegacion al punto de recogida con boton 'Confirmar recogida'."""
    route = get_route_by_id(route_id)
    if not route:
        return
    pickup_address = route["pickup_address"] or "No disponible"
    pickup_lat = route["pickup_lat"]
    pickup_lng = route["pickup_lng"]

    keyboard = list(_build_navigation_rows(pickup_lat, pickup_lng))
    keyboard.append([InlineKeyboardButton(
        "Confirmar llegada al punto de recogida",
        callback_data="ruta_pickup_confirm_{}".format(route_id)
    )])
    keyboard.append([InlineKeyboardButton(
        "Liberar ruta", callback_data="ruta_liberar_{}".format(route_id)
    )])

    text = (
        "Ve a recoger los productos.\n\n"
        "Recogida: {}\n\n"
        "Tienes 15 minutos para llegar. Cuando estes alli, presiona 'Confirmar llegada'.\n"
        "Si no puedes llegar, presiona 'Liberar ruta'."
    ).format(pickup_address)

    if hasattr(msg_or_query, "edit_message_text"):
        msg_or_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        msg_or_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    if pickup_lat is not None and pickup_lng is not None:
        try:
            chat_id = (msg_or_query.message.chat_id
                       if hasattr(msg_or_query, "message") else msg_or_query.chat_id)
            context.bot.send_location(chat_id=chat_id,
                                      latitude=float(pickup_lat),
                                      longitude=float(pickup_lng))
        except Exception:
            pass


def _cancel_route_arrival_jobs(context, route_id):
    for suffix in ("inactive", "warn", "deadline"):
        for job in context.job_queue.get_jobs_by_name("ruta_arr_{}_{}".format(suffix, route_id)):
            job.schedule_removal()


def _handle_route_pickup_confirm(update, context, route_id):
    """Courier confirma llegada al punto de recogida. Valida GPS <= 100m."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta ya no esta activa.")
        return

    courier = get_courier_by_telegram_id(update.effective_user.id)
    if not courier:
        return

    pickup_lat = route["pickup_lat"]
    pickup_lng = route["pickup_lng"]

    if pickup_lat and pickup_lng:
        live_lat = _row_value(courier, "live_lat")
        live_lng = _row_value(courier, "live_lng")
        live_active = _row_value(courier, "live_location_active")

        if not live_active or not live_lat or not live_lng:
            query.answer()
            query.message.reply_text(
                "Tu GPS no esta activo. Activa tu ubicacion en vivo en Telegram para confirmar tu llegada."
            )
            return

        dist_km = haversine_km(float(live_lat), float(live_lng),
                               float(pickup_lat), float(pickup_lng))
        if dist_km > ARRIVAL_RADIUS_KM:
            query.answer()
            query.message.reply_text(
                "Segun tu ubicacion estas a {:.0f} metros del punto de recogida.\n"
                "Dirigete al lugar e intenta confirmar cuando estes mas cerca.".format(dist_km * 1000)
            )
            return

    _cancel_route_arrival_jobs(context, route_id)
    context.bot_data.get("route_accepted_pos", {}).pop(route_id, None)

    courier_name = courier["full_name"] or "El repartidor"
    query.edit_message_text(
        "Llegada confirmada. Esperando que el aliado confirme para recibir los detalles de la primera parada."
    )
    _notify_ally_route_courier_arrived(context, route, courier_name)


def _notify_ally_route_courier_arrived(context, route, courier_name):
    """Notifica al aliado que el courier llego al pickup de la ruta, con botones de confirmacion."""
    try:
        ally_id = route["ally_id"]
        if not ally_id:
            return
        ally = get_ally_by_id(ally_id)
        if not ally:
            return
        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user["telegram_id"]:
            return
        route_id = route["id"]
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Confirmar llegada",
                    callback_data="ruta_pickupconfirm_approve_{}".format(route_id),
                ),
                InlineKeyboardButton(
                    "No ha llegado",
                    callback_data="ruta_pickupconfirm_reject_{}".format(route_id),
                ),
            ]
        ])
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "{} confirmo su llegada al punto de recogida de la ruta #{}.\n\n"
                "Confirma su llegada para que reciba los detalles de la primera parada."
            ).format(courier_name, route_id),
            reply_markup=keyboard,
        )
    except Exception as e:
        print("[WARN] _notify_ally_route_courier_arrived: {}".format(e))


def _handle_route_pickupconfirm_by_ally(update, context, route_id, approve):
    """Aliado confirma o rechaza la llegada del courier al pickup de la ruta."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta ya no esta activa.")
        return

    courier_id = _row_value(route, "courier_id")
    courier_user = None
    if courier_id:
        courier = get_courier_by_id(courier_id)
        if courier:
            courier_user = get_user_by_id(courier["user_id"])

    if approve:
        query.edit_message_text("Llegada confirmada. El repartidor recibira los detalles de la primera parada.")
        if not courier_user:
            return
        destinations = get_route_destinations(route_id)
        pending = [d for d in destinations if d["status"] == "PENDING"]
        if not pending:
            context.bot.send_message(
                chat_id=courier_user["telegram_id"],
                text="El aliado confirmo tu llegada. No hay paradas pendientes en esta ruta.",
            )
            return
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text="El aliado confirmo tu llegada. Aqui van los detalles de la primera parada:",
        )
        _send_route_stop_to_courier(context, courier_user["telegram_id"], route, pending[0])
    else:
        query.edit_message_text("Ok. El repartidor sera notificado.")
        if not courier_user:
            return
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=(
                "El aliado indica que aun no has llegado al punto de recogida de la ruta #{}.\n"
                "Dirigete al lugar y confirma tu llegada cuando estes alli."
            ).format(route_id),
        )


def _route_arrival_inactivity_job(context):
    """T+5 ruta: algoritmo direccional — misma logica que pedidos."""
    data = context.job.context or {}
    route_id = data.get("route_id")
    courier_id = data.get("courier_id")
    if not route_id:
        return
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        return

    pickup_lat = route["pickup_lat"]
    pickup_lng = route["pickup_lng"]
    accepted_pos = context.bot_data.get("route_accepted_pos", {}).get(route_id, {})
    accepted_lat = accepted_pos.get("lat")
    accepted_lng = accepted_pos.get("lng")

    if not all([pickup_lat, pickup_lng, accepted_lat, accepted_lng]):
        return

    courier = get_courier_by_id(courier_id) if courier_id else None
    if not courier:
        return

    current_lat = float(_row_value(courier, "live_lat") or accepted_lat)
    current_lng = float(_row_value(courier, "live_lng") or accepted_lng)

    dist_accepted = haversine_km(float(accepted_lat), float(accepted_lng),
                                 float(pickup_lat), float(pickup_lng))
    dist_now = haversine_km(current_lat, current_lng, float(pickup_lat), float(pickup_lng))

    if dist_now <= ARRIVAL_RADIUS_KM:
        _cancel_route_arrival_jobs(context, route_id)
        return

    courier_user = get_user_by_id(courier["user_id"]) if courier else None
    courier_tg_id = courier_user["telegram_id"] if courier_user else None

    if dist_accepted > 0.05 and dist_now > dist_accepted * 1.15:
        if courier_tg_id:
            try:
                context.bot.send_message(
                    chat_id=courier_tg_id,
                    text=(
                        "Ruta #{}: detectamos que te estas alejando del punto de recogida.\n"
                        "Si no puedes atender esta ruta, liberala para que otro repartidor la tome."
                    ).format(route_id),
                )
            except Exception:
                pass
        _release_route_by_timeout(route_id, courier_id, context)
        return

    if dist_accepted > 0.05 and dist_now < dist_accepted * 0.80:
        return  # Buen progreso

    if courier_tg_id:
        try:
            context.bot.send_message(
                chat_id=courier_tg_id,
                text=(
                    "Ruta #{}: llevamos 5 minutos y no hemos detectado avance hacia el punto de recogida.\n"
                    "Asegurate de estar en camino. Si no puedes llegar, libera la ruta."
                ).format(route_id),
            )
        except Exception:
            pass


def _route_arrival_warn_job(context):
    """T+15 ruta: avisa al aliado y pregunta al courier."""
    data = context.job.context or {}
    route_id = data.get("route_id")
    courier_id = data.get("courier_id")
    if not route_id:
        return
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        return

    courier = get_courier_by_id(courier_id) if courier_id else None
    courier_name = courier["full_name"] if courier else "El repartidor"
    courier_user = get_user_by_id(courier["user_id"]) if courier else None
    courier_tg_id = courier_user["telegram_id"] if courier_user else None

    try:
        ally_id = route["ally_id"]
        if ally_id:
            ally = get_ally_by_id(ally_id)
            if ally:
                au = get_user_by_id(ally["user_id"])
                if au:
                    context.bot.send_message(
                        chat_id=au["telegram_id"],
                        text=(
                            "Han pasado 15 minutos y {} no ha confirmado su llegada "
                            "al punto de recogida de la ruta #{}.".format(courier_name, route_id)
                        ),
                    )
    except Exception:
        pass

    if courier_tg_id:
        try:
            courier_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "Sigo en camino",
                    callback_data="ruta_arrival_enroute_{}".format(route_id)
                )],
                [InlineKeyboardButton(
                    "No puedo llegar — liberar ruta",
                    callback_data="ruta_arrival_release_{}".format(route_id)
                )],
            ])
            context.bot.send_message(
                chat_id=courier_tg_id,
                text=(
                    "Ruta #{}: llevas 15 minutos sin confirmar llegada al punto de recogida.\n"
                    "La ruta se liberara automaticamente en 5 minutos.\n\nQue esta pasando?"
                ).format(route_id),
                reply_markup=courier_keyboard,
            )
        except Exception:
            pass


def _route_arrival_deadline_job(context):
    """T+20 ruta: libera la ruta si el courier no llego."""
    data = context.job.context or {}
    route_id = data.get("route_id")
    courier_id = data.get("courier_id")
    if not route_id:
        return
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        return
    _release_route_by_timeout(route_id, courier_id, context)


def _release_route_by_timeout(route_id, courier_id, context):
    """Libera una ruta por timeout o inactividad y re-oferta."""
    _cancel_route_arrival_jobs(context, route_id)
    context.bot_data.get("route_accepted_pos", {}).pop(route_id, None)
    try:
        update_route_status(route_id, "PUBLISHED")
        route = get_route_by_id(route_id)
        if route:
            ally_id = route["ally_id"]
            publish_route_to_couriers(route_id, ally_id, context)
    except Exception as e:
        print("[WARN] _release_route_by_timeout: {}".format(e))


def _handle_route_arrival_enroute(update, context, route_id):
    """Courier responde 'Sigo en camino' al T+15 de ruta."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.answer()
        return
    query.edit_message_text(
        "Confirmado. Sigue hacia el punto de recogida y presiona 'Confirmar llegada' cuando estes alli."
    )
    try:
        ally_id = route["ally_id"]
        if ally_id:
            ally = get_ally_by_id(ally_id)
            if ally:
                au = get_user_by_id(ally["user_id"])
                if au:
                    context.bot.send_message(
                        chat_id=au["telegram_id"],
                        text="El repartidor confirma que sigue en camino a la ruta #{}.".format(route_id),
                    )
    except Exception:
        pass


def _handle_route_arrival_release(update, context, route_id):
    """Courier responde 'No puedo llegar' al T+15 de ruta."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.answer()
        return
    query.edit_message_text("Ruta #{} liberada. Gracias por avisar.".format(route_id))
    _cancel_route_arrival_jobs(context, route_id)
    courier = get_courier_by_telegram_id(update.effective_user.id)
    courier_id = courier["id"] if courier else None
    _release_route_by_timeout(route_id, courier_id, context)


def _handle_route_reject(update, context, route_id):
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        query.edit_message_text("Esta oferta ya no esta disponible.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        query.edit_message_text("Oferta de ruta #{} rechazada.".format(route_id))
        return

    current = get_current_route_offer(route_id)
    if not current or current["courier_id"] != courier["id"]:
        query.edit_message_text("Esta oferta ya no esta disponible para ti.")
        return

    _cancel_route_offer_jobs(context, route_id, current["queue_id"])
    mark_route_offer_response(current["queue_id"], "REJECTED")
    query.edit_message_text("Oferta de ruta #{} rechazada.".format(route_id))
    _send_next_route_offer(route_id, context)


def _handle_route_busy(update, context, route_id):
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        query.edit_message_text("Esta oferta ya no esta disponible.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        query.edit_message_text("Oferta de ruta #{} rechazada.".format(route_id))
        return

    current = get_current_route_offer(route_id)
    if not current or current["courier_id"] != courier["id"]:
        query.edit_message_text("Esta oferta ya no esta disponible para ti.")
        return

    _cancel_route_offer_jobs(context, route_id, current["queue_id"])
    mark_route_offer_response(current["queue_id"], "BUSY")
    query.edit_message_text("Registrado. Te saltamos esta ruta.")
    _send_next_route_offer(route_id, context)


def _handle_route_deliver_stop(update, context, route_id, seq):
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route:
        query.edit_message_text("Ruta no encontrada.")
        return

    if route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta ya no esta en curso.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != route["courier_id"]:
        query.edit_message_text("Solo el repartidor asignado puede confirmar entregas.")
        return

    # Validar GPS activo
    if not _is_courier_gps_active(courier):
        query.edit_message_text(GPS_INACTIVE_MSG)
        return

    # Obtener coordenadas de la parada
    stops = get_route_destinations(route_id)
    stop = next((s for s in stops if s["sequence"] == seq), None)
    if not stop:
        query.edit_message_text("Parada no encontrada.")
        return

    stop_lat = _row_value(stop, "dropoff_lat")
    stop_lng = _row_value(stop, "dropoff_lng")
    courier_lat = float(_row_value(courier, "live_lat") or 0)
    courier_lng = float(_row_value(courier, "live_lng") or 0)

    if stop_lat is not None and stop_lng is not None:
        dist = haversine_km(courier_lat, courier_lng, float(stop_lat), float(stop_lng))
        if dist > DELIVERY_RADIUS_KM:
            query.edit_message_text(
                "No puedes finalizar esta parada porque no estas cerca del punto de entrega.\n"
                "Distancia actual: {:.0f} metros. Debes estar a menos de 100 metros.\n\n"
                "Si ya estas en el lugar pero el pin esta mal ubicado, usa el boton de ayuda.".format(dist * 1000),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "Estoy aqui pero el pin esta mal",
                        callback_data="ruta_pinissue_{}_{}".format(route_id, seq)
                    )
                ]]),
            )
            return

    deliver_route_stop(route_id, seq)
    query.edit_message_text("Parada {} confirmada como entregada.".format(seq))

    pending = get_pending_route_stops(route_id)
    if pending:
        next_stop = pending[0]
        _send_route_stop_to_courier(context, query.message.chat_id, route, next_stop)
    else:
        update_route_status(route_id, "DELIVERED", "delivered_at")
        # Fee base al aliado: $300 (igual que pedido individual — $200 admin + $100 plataforma)
        ally_id = route["ally_id"]
        ally_admin_id = _row_value(route, "ally_admin_id_snapshot")
        if not ally_admin_id:
            ally_link = get_approved_admin_link_for_ally(ally_id) if ally_id else None
            ally_admin_id = ally_link["admin_id"] if ally_link else None
        if ally_id and ally_admin_id and not check_ally_active_subscription(ally_id):
            ally_ok, ally_msg = apply_service_fee(
                target_type="ALLY", target_id=ally_id,
                admin_id=ally_admin_id, ref_type="ROUTE", ref_id=route_id,
                total_fee=route["total_fee"],
            )
            if not ally_ok:
                print("[WARN] No se pudo cobrar fee base al aliado en ruta {}: {}".format(route_id, ally_msg))
        # Fee base al repartidor: $300 (igual que pedido individual — $200 admin + $100 plataforma)
        courier_id_route = route["courier_id"]
        courier_admin_id_route = _row_value(route, "courier_admin_id_snapshot")
        if not courier_admin_id_route and courier_id_route:
            courier_admin_id_route = get_approved_admin_id_for_courier(courier_id_route)
        if courier_id_route and courier_admin_id_route:
            courier_ok, courier_msg = apply_service_fee(
                target_type="COURIER", target_id=courier_id_route,
                admin_id=courier_admin_id_route, ref_type="ROUTE", ref_id=route_id,
            )
            if not courier_ok:
                print("[WARN] No se pudo cobrar fee base al repartidor en ruta {}: {}".format(route_id, courier_msg))
        # Fee adicional por paradas extra: $200 c/u (split 50/50 admin/plataforma)
        ok, msg = liquidate_route_additional_stops_fee(route_id)
        if not ok and "no tiene additional_stops_fee" not in msg and "ya tenia liquidado" not in msg and "incidencias/cancelaciones" not in msg:
            print("[WARN] No se pudo liquidar additional_stops_fee de ruta {}: {}".format(route_id, msg))
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Ruta #{} completada. Todas las paradas fueron entregadas.".format(route_id),
        )
        _notify_ally_route_delivered(context, route)


def _notify_ally_route_accepted(context, route, courier_name):
    try:
        ally = get_ally_by_id(route["ally_id"])
        if not ally:
            return
        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user["telegram_id"]:
            return
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text="Tu ruta #{} fue aceptada por {}. Tiene {} paradas de entrega.".format(
                route["id"],
                courier_name,
                len(get_route_destinations(route["id"])),
            ),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar aceptacion de ruta al aliado: {}".format(e))


def _notify_ally_route_delivered(context, route):
    try:
        ally = get_ally_by_id(route["ally_id"])
        if not ally:
            return
        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user["telegram_id"]:
            return
        route_id = route["id"]
        # Calcular desglose de fees cobrados
        stops = get_route_destinations(route_id)
        n_delivered = sum(1 for s in stops if str(s["status"] or "") == "DELIVERED")
        n_cancelled = len(stops) - n_delivered
        fee_base = 300
        # $200 por parada adicional = tarifa de SERVICIO cobrada al saldo del aliado.
        # NO confundir con tarifa_parada_adicional ($4.000) que es el pago al courier,
        # acordado fuera de la plataforma y nunca descontado de saldos internos.
        FEE_PARADA_SERVICIO = 200
        fee_adicional = max(0, (n_delivered - 1)) * FEE_PARADA_SERVICIO
        fee_total = fee_base + fee_adicional
        lines = [
            "Ruta #{} completada.".format(route_id),
            "",
            "Cobros aplicados a tu saldo:",
            "  Servicio base:        -${}".format(format(fee_base, ",")),
        ]
        if fee_adicional > 0:
            lines.append("  Paradas adicionales:  -${}  ({} x ${})".format(
                format(fee_adicional, ","), n_delivered - 1, format(FEE_PARADA_SERVICIO, ",")
            ))
        lines.append("  Total descontado:     -${}".format(format(fee_total, ",")))
        if n_cancelled > 0:
            lines.append("")
            lines.append("{} parada(s) no se entregaron.".format(n_cancelled))
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text="\n".join(lines),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar entrega de ruta al aliado: {}".format(e))


def handle_route_callback(update, context):
    """
    Dispatcher de callbacks ruta_aceptar_*, ruta_rechazar_*, ruta_ocupado_*, ruta_entregar_*,
    ruta_liberar_* (flujo responsable con motivo).
    Registrar en main.py como CallbackQueryHandler con pattern r'^ruta_(aceptar|rechazar|ocupado|entregar|liberar|liberar_motivo|liberar_confirmar|liberar_abort)_'.
    """
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("ruta_aceptar_"):
        route_id = int(data.replace("ruta_aceptar_", ""))
        return _handle_route_accept(update, context, route_id)

    if data.startswith("ruta_rechazar_"):
        route_id = int(data.replace("ruta_rechazar_", ""))
        return _handle_route_reject(update, context, route_id)

    if data.startswith("order_arrived_pickup_"):
        order_id = int(data.replace("order_arrived_pickup_", ""))
        return _handle_courier_arrival_button(update, context, order_id)

    if data.startswith("order_arrival_enroute_"):
        order_id = int(data.replace("order_arrival_enroute_", ""))
        return _handle_courier_arrival_enroute(update, context, order_id)

    if data.startswith("order_arrival_release_"):
        order_id = int(data.replace("order_arrival_release_", ""))
        return _handle_courier_arrival_release(update, context, order_id)

    if data.startswith("ruta_arrival_enroute_"):
        route_id = int(data.replace("ruta_arrival_enroute_", ""))
        return _handle_route_arrival_enroute(update, context, route_id)

    if data.startswith("ruta_arrival_release_"):
        route_id = int(data.replace("ruta_arrival_release_", ""))
        return _handle_route_arrival_release(update, context, route_id)

    if data.startswith("ruta_orden_"):
        return _handle_route_reorder(update, context, data)

    if data.startswith("ruta_pickup_confirm_"):
        route_id = int(data.replace("ruta_pickup_confirm_", ""))
        return _handle_route_pickup_confirm(update, context, route_id)

    if data.startswith("ruta_pickupconfirm_approve_"):
        route_id = int(data.replace("ruta_pickupconfirm_approve_", ""))
        return _handle_route_pickupconfirm_by_ally(update, context, route_id, approve=True)

    if data.startswith("ruta_pickupconfirm_reject_"):
        route_id = int(data.replace("ruta_pickupconfirm_reject_", ""))
        return _handle_route_pickupconfirm_by_ally(update, context, route_id, approve=False)

    if data.startswith("ruta_ocupado_"):
        route_id = int(data.replace("ruta_ocupado_", ""))
        return _handle_route_busy(update, context, route_id)

    if data.startswith("ruta_entregar_"):
        parts = data.replace("ruta_entregar_", "").split("_")
        if len(parts) == 2:
            try:
                route_id = int(parts[0])
                seq = int(parts[1])
                return _handle_route_deliver_stop(update, context, route_id, seq)
            except ValueError:
                pass

    if data.startswith("ruta_liberar_abort_"):
        route_id = int(data.replace("ruta_liberar_abort_", ""))
        query.edit_message_text("Ok. La ruta #{} sigue en curso.".format(route_id))
        return

    if data.startswith("ruta_liberar_motivo_"):
        # ruta_liberar_motivo_{route_id}_{reason}
        parts = data.split("_")
        if len(parts) < 5:
            query.edit_message_text("No se pudo procesar el motivo de liberacion.")
            return
        route_id = int(parts[3])
        reason_code = parts[4]
        return _handle_route_release_reason_selected(update, context, route_id, reason_code)

    if data.startswith("ruta_liberar_confirmar_"):
        # ruta_liberar_confirmar_{route_id}_{reason}
        parts = data.split("_")
        if len(parts) < 5:
            query.edit_message_text("No se pudo confirmar la liberacion.")
            return
        route_id = int(parts[3])
        reason_code = parts[4]
        return _handle_route_release_confirm(update, context, route_id, reason_code)

    if data.startswith("ruta_liberar_"):
        route_id = int(data.replace("ruta_liberar_", ""))
        return _handle_route_release_menu(update, context, route_id)

    if data.startswith("ruta_pinissue_"):
        parts = data.replace("ruta_pinissue_", "").split("_")
        if len(parts) == 2:
            try:
                route_id = int(parts[0])
                seq = int(parts[1])
                return _handle_route_pin_issue(update, context, route_id, seq)
            except ValueError:
                pass

    if data.startswith("admin_ruta_pinissue_fin_"):
        parts = data.replace("admin_ruta_pinissue_fin_", "").split("_")
        if len(parts) == 2:
            return _handle_admin_route_pinissue_action(update, context, int(parts[0]), int(parts[1]), "fin")

    if data.startswith("admin_ruta_pinissue_cancel_courier_"):
        parts = data.replace("admin_ruta_pinissue_cancel_courier_", "").split("_")
        if len(parts) == 2:
            return _handle_admin_route_pinissue_action(update, context, int(parts[0]), int(parts[1]), "cancel_courier")

    if data.startswith("admin_ruta_pinissue_cancel_ally_"):
        parts = data.replace("admin_ruta_pinissue_cancel_ally_", "").split("_")
        if len(parts) == 2:
            return _handle_admin_route_pinissue_action(update, context, int(parts[0]), int(parts[1]), "cancel_ally")

    if data.startswith("ruta_cancelar_aliado_"):
        route_id = int(data.replace("ruta_cancelar_aliado_", ""))
        return _handle_cancel_ally_route(update, context, route_id)

    return None


def _handle_route_release_menu(update, context, route_id):
    """Muestra razones antes de permitir que el courier libere una ruta aceptada."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route:
        query.edit_message_text("Ruta no encontrada.")
        return

    if route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta no se puede liberar en su estado actual.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != route["courier_id"]:
        query.edit_message_text("No tienes permiso para liberar esta ruta.")
        return

    # Bloquear liberación si ya entrego alguna parada (ya recogió el producto)
    stops = get_route_destinations(route_id)
    n_delivered = sum(1 for s in stops if str(s["status"] or "") == "DELIVERED")
    if n_delivered > 0:
        query.edit_message_text(
            "Ya entregaste {} parada(s). No puedes liberar la ruta una vez que recogiste los productos.\n\n"
            "Si tienes un problema, contacta a tu administrador.".format(n_delivered)
        )
        return

    reason_labels = {
        "falla_mecanica": "Falla mecanica / accidente con el vehiculo",
        "emergencia": "Emergencia personal / seguridad",
        "no_puedo_continuar": "No puedo continuar la ruta",
        "pedido_incorrecto": "Datos incorrectos / ruta inconsistente",
        "otro_admin": "Otro (debe revisarlo el admin)",
    }

    text = (
        "Vas a liberar la ruta #{}.\n\n"
        "Liberar una ruta sin motivo valido es una falta grave.\n"
        "Solo el aliado puede cancelar el servicio; esto solo libera y re-oferta la ruta.\n\n"
        "Selecciona un motivo:"
    ).format(route_id)

    kb = []
    for code, label in reason_labels.items():
        kb.append([InlineKeyboardButton(label, callback_data="ruta_liberar_motivo_{}_{}".format(route_id, code))])
    kb.append([InlineKeyboardButton("Cancelar", callback_data="ruta_liberar_abort_{}".format(route_id))])
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))


def _handle_route_release_reason_selected(update, context, route_id, reason_code):
    """Pide confirmación final antes de liberar la ruta."""
    query = update.callback_query
    reason_labels = {
        "falla_mecanica": "Falla mecanica / accidente con el vehiculo",
        "emergencia": "Emergencia personal / seguridad",
        "no_puedo_continuar": "No puedo continuar la ruta",
        "pedido_incorrecto": "Datos incorrectos / ruta inconsistente",
        "otro_admin": "Otro (debe revisarlo el admin)",
    }
    reason_label = reason_labels.get(reason_code, reason_code or "No especificado")
    keyboard = [[
        InlineKeyboardButton(
            "Confirmar liberacion",
            callback_data="ruta_liberar_confirmar_{}_{}".format(route_id, reason_code),
        ),
        InlineKeyboardButton(
            "Cancelar",
            callback_data="ruta_liberar_abort_{}".format(route_id),
        ),
    ]]
    query.edit_message_text(
        "Confirmas que vas a liberar la ruta #{}?\n\nMotivo: {}\n\n"
        "Esta accion se revisa por el admin. Si es injustificada, puede haber sancion.".format(
            route_id,
            reason_label,
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def _handle_route_release_confirm(update, context, route_id, reason_code):
    """Libera la ruta y la re-oferta a otros couriers, excluyendo al que la liberó."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route:
        query.edit_message_text("Ruta no encontrada.")
        return

    if route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta no se puede liberar en su estado actual.")
        return

    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != route["courier_id"]:
        query.edit_message_text("No tienes permiso para liberar esta ruta.")
        return

    reason_labels = {
        "falla_mecanica": "Falla mecanica / accidente con el vehiculo",
        "emergencia": "Emergencia personal / seguridad",
        "no_puedo_continuar": "No puedo continuar la ruta",
        "pedido_incorrecto": "Datos incorrectos / ruta inconsistente",
        "otro_admin": "Otro (debe revisarlo el admin)",
    }
    reason_label = reason_labels.get(reason_code, reason_code or "No especificado")

    ally_id = route["ally_id"]
    link = get_approved_admin_link_for_ally(ally_id) if ally_id else None
    admin_id = link["admin_id"] if link else None
    if not admin_id:
        courier_admin_link = get_approved_admin_link_for_courier(courier["id"])
        admin_id = courier_admin_link["admin_id"] if courier_admin_link else None

    # Cobrar $300 al courier por liberar la ruta (igual que cancelar un pedido)
    courier_admin_id_release = _row_value(route, "courier_admin_id_snapshot")
    if not courier_admin_id_release:
        courier_admin_id_release = get_approved_admin_id_for_courier(courier["id"])
    if courier_admin_id_release:
        fee_ok, fee_msg = apply_service_fee(
            target_type="COURIER", target_id=courier["id"],
            admin_id=courier_admin_id_release, ref_type="ROUTE", ref_id=route_id,
        )
        if not fee_ok:
            print("[WARN] No se pudo cobrar fee al courier por liberacion de ruta {}: {}".format(route_id, fee_msg))

    delete_route_offer_queue(route_id)
    release_route_from_courier(route_id)

    query.edit_message_text(
        "Ruta #{} liberada.\nMotivo: {}\n\nSe cobro la tarifa de servicio ($300) por la liberacion.\nSera ofrecida a otros repartidores.".format(
            route_id,
            reason_label,
        )
    )

    try:
        ally = get_ally_by_id(ally_id) if ally_id else None
        if ally:
            ally_user = get_user_by_id(ally["user_id"])
            if ally_user and ally_user["telegram_id"]:
                context.bot.send_message(
                    chat_id=ally_user["telegram_id"],
                    text=(
                        "El repartidor libero tu ruta #{}.\n"
                        "Motivo: {}\n"
                        "Estamos buscando otro repartidor."
                    ).format(route_id, reason_label),
                )
    except Exception:
        pass

    try:
        if admin_id:
            admin = get_admin_by_id(admin_id)
            if admin:
                admin_user = get_user_by_id(admin["user_id"])
                if admin_user and admin_user["telegram_id"]:
                    courier_name = (courier["full_name"] or "").strip() or "Repartidor"
                    context.bot.send_message(
                        chat_id=admin_user["telegram_id"],
                        text=(
                            "ALERTA: liberacion de ruta\n\n"
                            "Ruta: #{}\n"
                            "Courier: {}\n"
                            "Motivo: {}\n\n"
                            "Accion: revisar si es justificado."
                        ).format(route_id, courier_name, reason_label),
                    )
    except Exception:
        pass

    if not admin_id or not ally_id:
        return

    pickup_lat = route["pickup_lat"]
    pickup_lng = route["pickup_lng"]
    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=False,
        cash_required_amount=0,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
    )
    # Excluir al courier que liberó y a los sin saldo suficiente
    couriers_re_oferta = []
    for c in eligible:
        c_id = c["courier_id"]
        if c_id == courier["id"]:
            continue
        c_admin_id = get_approved_admin_id_for_courier(c_id)
        if not c_admin_id:
            continue
        fee_ok, _ = check_service_fee_available("COURIER", c_id, c_admin_id)
        if fee_ok:
            couriers_re_oferta.append(c_id)
    if not couriers_re_oferta:
        return

    courier_ids = couriers_re_oferta
    create_route_offer_queue(route_id, courier_ids)
    update_route_status(route_id, "PUBLISHED", "published_at")

    import time
    context.bot_data.setdefault("route_offer_cycles", {})[route_id] = {
        "started_at": time.time(),
        "admin_id": admin_id,
        "ally_id": ally_id,
        "excluded_couriers": {courier["id"]},
    }
    _send_next_route_offer(route_id, context)


# ---------------------------------------------------------------------------
# Validación GPS + finalización de pedido con check de distancia
# ---------------------------------------------------------------------------

def _handle_delivered_confirm(update, context, order_id):
    """Valida GPS y distancia antes de mostrar la confirmacion de entrega."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return
    if order["status"] != "PICKED_UP":
        query.edit_message_text("Este pedido no esta en estado de entrega.")
        return
    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != order["courier_id"]:
        query.edit_message_text("No tienes permiso para finalizar este pedido.")
        return

    # Bloquear si GPS inactivo
    if not _is_courier_gps_active(courier):
        query.edit_message_text(GPS_INACTIVE_MSG)
        return

    # Validar distancia al punto de entrega
    dropoff_lat = _row_value(order, "dropoff_lat")
    dropoff_lng = _row_value(order, "dropoff_lng")
    if dropoff_lat is not None and dropoff_lng is not None:
        courier_lat = float(_row_value(courier, "live_lat") or 0)
        courier_lng = float(_row_value(courier, "live_lng") or 0)
        dist = haversine_km(courier_lat, courier_lng, float(dropoff_lat), float(dropoff_lng))
        if dist > DELIVERY_RADIUS_KM:
            query.edit_message_text(
                "No puedes finalizar el servicio porque no estas cerca del punto de entrega.\n"
                "Distancia actual: {:.0f} metros. Debes estar a menos de 100 metros.\n\n"
                "Si ya estas en el lugar pero el pin esta mal ubicado, usa el boton de ayuda.".format(dist * 1000),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "Estoy aqui pero el pin esta mal",
                        callback_data="order_pinissue_{}".format(order_id)
                    )
                ]]),
            )
            return

    keyboard = [[
        InlineKeyboardButton("Si", callback_data="order_delivered_{}".format(order_id)),
        InlineKeyboardButton("No", callback_data="order_delivered_cancel_{}".format(order_id)),
    ]]
    query.edit_message_text(
        "Ya entregaste el pedido #{}?".format(order_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------------------------------------------------------------------------
# Flujo pin mal ubicado — pedido
# ---------------------------------------------------------------------------

def _handle_pin_issue_report(update, context, order_id):
    """Courier reporta que el pin de entrega esta mal. Notifica al admin del equipo."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PICKED_UP":
        query.edit_message_text("Este pedido no esta disponible para esta accion.")
        return
    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != order["courier_id"]:
        query.edit_message_text("No tienes permiso para esta accion.")
        return

    if not _is_courier_gps_active(courier):
        query.edit_message_text(GPS_INACTIVE_MSG)
        return

    # Evitar duplicados: si ya hay una solicitud pendiente, no crear otra
    existing = get_pending_support_request(order_id=order_id)
    if existing:
        query.edit_message_text(
            "Ya enviaste una solicitud de ayuda para este pedido.\n"
            "Tu administrador fue notificado y respondera pronto."
        )
        return

    admin_id = get_approved_admin_id_for_courier(courier["id"])
    if not admin_id:
        query.edit_message_text("No se encontro un administrador asignado para tu equipo.")
        return

    support_id = create_order_support_request(
        courier_id=courier["id"],
        admin_id=admin_id,
        order_id=order_id,
    )
    query.edit_message_text(
        "Solicitud enviada. Tu administrador fue notificado y podra ayudarte a finalizar el servicio.\n"
        "Permanece en el lugar hasta recibir respuesta."
    )
    _notify_admin_pin_issue(context, order, courier, admin_id, support_id)


def _notify_admin_pin_issue(context, order, courier, admin_id, support_id):
    """Envia al admin del equipo la alerta de pin mal ubicado con opciones de accion."""
    try:
        admin = get_admin_by_id(admin_id)
        if not admin:
            return
        admin_user = get_user_by_id(admin["user_id"])
        if not admin_user or not admin_user["telegram_id"]:
            return

        courier_lat = _row_value(courier, "live_lat")
        courier_lng = _row_value(courier, "live_lng")
        dropoff_lat = _row_value(order, "dropoff_lat")
        dropoff_lng = _row_value(order, "dropoff_lng")

        maps_courier = ""
        if courier_lat is not None and courier_lng is not None:
            maps_courier = "https://maps.google.com/?q={},{}".format(courier_lat, courier_lng)

        maps_delivery = ""
        if dropoff_lat is not None and dropoff_lng is not None:
            maps_delivery = "https://maps.google.com/?q={},{}".format(dropoff_lat, dropoff_lng)

        courier_user = get_user_by_id(courier["user_id"])
        courier_tg = ""
        if courier_user and courier_user["telegram_id"]:
            courier_tg = "tg://user?id={}".format(courier_user["telegram_id"])

        lines = [
            "Uno de tus repartidores necesita tu ayuda - Pedido #{}".format(order["id"]),
            "",
            "Repartidor: {}".format(_row_value(courier, "full_name") or "N/D"),
            "Telefono: {}".format(_row_value(courier, "phone") or "N/D"),
            "Direccion de entrega guardada: {}".format(order["customer_address"] or "N/D"),
            "Cliente: {}".format(order["customer_name"] or "N/D"),
        ]
        if maps_delivery:
            lines.append("Pin de entrega: {}".format(maps_delivery))
        if maps_courier:
            lines.append("Ubicacion actual del repartidor: {}".format(maps_courier))

        keyboard = [
            [InlineKeyboardButton(
                "Finalizar servicio",
                callback_data="admin_pinissue_fin_{}".format(order["id"])
            )],
            [InlineKeyboardButton(
                "Cancelar — falla del repartidor",
                callback_data="admin_pinissue_cancel_courier_{}".format(order["id"])
            )],
            [InlineKeyboardButton(
                "Cancelar — falla del aliado",
                callback_data="admin_pinissue_cancel_ally_{}".format(order["id"])
            )],
        ]
        if courier_tg:
            keyboard.append([InlineKeyboardButton(
                "Chatear con el repartidor",
                url=courier_tg
            )])

        context.bot.send_message(
            chat_id=admin_user["telegram_id"],
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar pin issue al admin (pedido {}): {}".format(order["id"], e))


def _handle_admin_pinissue_action(update, context, order_id, action):
    """Admin resuelve la solicitud de ayuda: finaliza o cancela con atribucion de falla."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return
    if order["status"] != "PICKED_UP":
        query.edit_message_text("Este pedido ya fue resuelto o no esta en estado de entrega.")
        return

    support = get_pending_support_request(order_id=order_id)
    if not support:
        query.edit_message_text("No hay solicitud de ayuda pendiente para este pedido.")
        return

    telegram_id = update.effective_user.id
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin or admin["id"] != support["admin_id"]:
        query.edit_message_text("No tienes permiso para resolver esta solicitud.")
        return

    if action == "fin":
        resolve_support_request(support["id"], "DELIVERED", admin["id"])
        _cancel_delivery_reminder_jobs(context, order_id)
        _do_deliver_order(context, order, support["courier_id"])
        query.edit_message_text(
            "Servicio #{} finalizado correctamente. "
            "Se aplicaron los cargos de comision normales.".format(order_id)
        )
        _notify_courier_support_resolved(context, support["courier_id"], order_id, "fin")

    elif action == "cancel_courier":
        resolve_support_request(support["id"], "CANCELLED_COURIER", admin["id"])
        _cancel_delivery_reminder_jobs(context, order_id)
        cancel_order(order_id, "ADMIN")
        # Courier paga $300, aliado no paga
        courier_admin_id = get_approved_admin_id_for_courier(support["courier_id"])
        if courier_admin_id:
            apply_service_fee(
                target_type="COURIER",
                target_id=support["courier_id"],
                admin_id=courier_admin_id,
                ref_type="ORDER",
                ref_id=order_id,
            )
        query.edit_message_text(
            "Pedido #{} cancelado. Falla atribuida al repartidor.\n"
            "Se cobro comision al repartidor. El aliado no fue cargado.".format(order_id)
        )
        _notify_courier_support_resolved(context, support["courier_id"], order_id, "cancel_courier")

    elif action == "cancel_ally":
        resolve_support_request(support["id"], "CANCELLED_ALLY", admin["id"])
        _cancel_delivery_reminder_jobs(context, order_id)
        cancel_order(order_id, "ADMIN")
        # Ambos pagan $300
        ally_id = order["ally_id"]
        if ally_id:
            ally_admin_link = get_approved_admin_link_for_ally(ally_id)
            if ally_admin_link:
                apply_service_fee(
                    target_type="ALLY",
                    target_id=ally_id,
                    admin_id=ally_admin_link["admin_id"],
                    ref_type="ORDER",
                    ref_id=order_id,
                )
        courier_admin_id = get_approved_admin_id_for_courier(support["courier_id"])
        if courier_admin_id:
            apply_service_fee(
                target_type="COURIER",
                target_id=support["courier_id"],
                admin_id=courier_admin_id,
                ref_type="ORDER",
                ref_id=order_id,
            )
        query.edit_message_text(
            "Pedido #{} cancelado. Falla atribuida al aliado.\n"
            "Se cobro comision al aliado y al repartidor.".format(order_id)
        )
        _notify_courier_support_resolved(context, support["courier_id"], order_id, "cancel_ally")


def _do_deliver_order(context, order, courier_id):
    """Aplica fees y marca el pedido como DELIVERED (usado en resolucion de admin)."""
    order_id = order["id"]
    ally_id = order["ally_id"]
    ally_admin_link = get_approved_admin_link_for_ally(ally_id) if ally_id else None
    ally_admin_id = ally_admin_link["admin_id"] if ally_admin_link else None
    courier_admin_id = order["courier_admin_id_snapshot"] if "courier_admin_id_snapshot" in order.keys() else None
    if courier_admin_id is None:
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)

    if ally_admin_id and not check_ally_active_subscription(ally_id):
        apply_service_fee(
            target_type="ALLY", target_id=ally_id, admin_id=ally_admin_id,
            ref_type="ORDER", ref_id=order_id,
            total_fee=order["total_fee"],
        )
    if courier_admin_id:
        apply_service_fee(
            target_type="COURIER", target_id=courier_id, admin_id=courier_admin_id,
            ref_type="ORDER", ref_id=order_id,
        )
    set_order_status(order_id, "DELIVERED", "delivered_at")
    delete_offer_queue(order_id)


def _notify_courier_support_resolved(context, courier_id, order_id, resolution):
    """Notifica al courier el resultado de la intervencion del admin."""
    try:
        courier = get_courier_by_id(courier_id)
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return
        messages = {
            "fin": (
                "Tu administrador finalizo el servicio #{} en tu nombre. "
                "Los cargos normales fueron aplicados.".format(order_id)
            ),
            "cancel_courier": (
                "El pedido #{} fue cancelado por tu administrador. "
                "La falla fue atribuida a ti. Se cobro la comision.\n"
                "Debes devolver el producto al punto de recogida.".format(order_id)
            ),
            "cancel_ally": (
                "El pedido #{} fue cancelado por tu administrador. "
                "La falla fue atribuida al aliado. Se cobro comision a ambas partes.\n"
                "Debes devolver el producto al punto de recogida.".format(order_id)
            ),
        }
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=messages.get(resolution, "El pedido #{} fue resuelto por tu administrador.".format(order_id)),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar resolucion al courier {}: {}".format(courier_id, e))


# ---------------------------------------------------------------------------
# Flujo pin mal ubicado — rutas multi-parada
# ---------------------------------------------------------------------------

def _handle_route_pin_issue(update, context, route_id, seq):
    """Courier reporta pin mal ubicado en una parada de ruta."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta ya no esta en curso.")
        return
    telegram_id = update.effective_user.id
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier or courier["id"] != route["courier_id"]:
        query.edit_message_text("No tienes permiso para esta accion.")
        return

    if not _is_courier_gps_active(courier):
        query.edit_message_text(GPS_INACTIVE_MSG)
        return

    existing = get_pending_support_request(route_id=route_id, route_seq=seq)
    if existing:
        query.edit_message_text(
            "Ya enviaste una solicitud de ayuda para esta parada.\n"
            "Tu administrador fue notificado y respondera pronto."
        )
        return

    admin_id = get_approved_admin_id_for_courier(courier["id"])
    if not admin_id:
        query.edit_message_text("No se encontro un administrador asignado para tu equipo.")
        return

    stops = get_route_destinations(route_id)
    stop = next((s for s in stops if s["sequence"] == seq), None)
    if not stop:
        query.edit_message_text("Parada no encontrada.")
        return

    support_id = create_order_support_request(
        courier_id=courier["id"],
        admin_id=admin_id,
        route_id=route_id,
        route_seq=seq,
    )
    query.edit_message_text(
        "Solicitud enviada. Tu administrador fue notificado.\n"
        "Permanece en el lugar hasta recibir respuesta. "
        "Despues continuaras con las demas paradas."
    )
    _notify_admin_route_pin_issue(context, route, stop, courier, admin_id, support_id)


def _notify_admin_route_pin_issue(context, route, stop, courier, admin_id, support_id):
    """Envia al admin del equipo la alerta de pin mal ubicado en parada de ruta."""
    try:
        admin = get_admin_by_id(admin_id)
        if not admin:
            return
        admin_user = get_user_by_id(admin["user_id"])
        if not admin_user or not admin_user["telegram_id"]:
            return

        courier_lat = _row_value(courier, "live_lat")
        courier_lng = _row_value(courier, "live_lng")
        stop_lat = _row_value(stop, "dropoff_lat")
        stop_lng = _row_value(stop, "dropoff_lng")
        seq = stop["sequence"]

        maps_courier = ""
        if courier_lat is not None and courier_lng is not None:
            maps_courier = "https://maps.google.com/?q={},{}".format(courier_lat, courier_lng)
        maps_stop = ""
        if stop_lat is not None and stop_lng is not None:
            maps_stop = "https://maps.google.com/?q={},{}".format(stop_lat, stop_lng)

        courier_user = get_user_by_id(courier["user_id"])
        courier_tg = ""
        if courier_user and courier_user["telegram_id"]:
            courier_tg = "tg://user?id={}".format(courier_user["telegram_id"])

        lines = [
            "Uno de tus repartidores necesita tu ayuda - Ruta #{} Parada {}".format(route["id"], seq),
            "",
            "Repartidor: {}".format(_row_value(courier, "full_name") or "N/D"),
            "Telefono: {}".format(_row_value(courier, "phone") or "N/D"),
            "Cliente: {}".format(stop["customer_name"] or "N/D"),
            "Direccion guardada: {}".format(stop["customer_address"] or "N/D"),
        ]
        if maps_stop:
            lines.append("Pin de entrega: {}".format(maps_stop))
        if maps_courier:
            lines.append("Ubicacion actual del repartidor: {}".format(maps_courier))

        route_seq_str = "{}_{}".format(route["id"], seq)
        keyboard = [
            [InlineKeyboardButton(
                "Finalizar esta parada",
                callback_data="admin_ruta_pinissue_fin_{}".format(route_seq_str)
            )],
            [InlineKeyboardButton(
                "Cancelar parada — falla del repartidor",
                callback_data="admin_ruta_pinissue_cancel_courier_{}".format(route_seq_str)
            )],
            [InlineKeyboardButton(
                "Cancelar parada — falla del aliado",
                callback_data="admin_ruta_pinissue_cancel_ally_{}".format(route_seq_str)
            )],
        ]
        if courier_tg:
            keyboard.append([InlineKeyboardButton(
                "Chatear con el repartidor",
                url=courier_tg
            )])

        context.bot.send_message(
            chat_id=admin_user["telegram_id"],
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar pin issue de ruta al admin: {}".format(e))


def _handle_admin_route_pinissue_action(update, context, route_id, seq, action):
    """Admin resuelve pin issue en parada de ruta."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta ya no esta en curso.")
        return

    support = get_pending_support_request(route_id=route_id, route_seq=seq)
    if not support:
        query.edit_message_text("No hay solicitud de ayuda pendiente para esta parada.")
        return

    telegram_id = update.effective_user.id
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin or admin["id"] != support["admin_id"]:
        query.edit_message_text("No tienes permiso para resolver esta solicitud.")
        return

    courier_id = support["courier_id"]

    if action == "fin":
        resolve_support_request(support["id"], "DELIVERED", admin["id"])
        deliver_route_stop(route_id, seq)
        query.edit_message_text("Parada {} de la ruta #{} finalizada.".format(seq, route_id))
        _notify_courier_route_stop_resolved(context, courier_id, route_id, seq, "fin")

    elif action in ("cancel_courier", "cancel_ally"):
        resolution = "CANCELLED_COURIER" if action == "cancel_courier" else "CANCELLED_ALLY"
        resolve_support_request(support["id"], resolution, admin["id"])
        cancel_route_stop(route_id, seq, resolution)

        # Aplicar fees segun culpable
        if action == "cancel_ally":
            # Fee al aliado de la ruta (penalidad por su falla)
            ally_id = route["ally_id"]
            if ally_id:
                ally_admin_link = get_approved_admin_link_for_ally(ally_id)
                if ally_admin_link:
                    pi_ally_ok, pi_ally_msg = apply_service_fee(
                        target_type="ALLY", target_id=ally_id,
                        admin_id=ally_admin_link["admin_id"],
                        ref_type="ROUTE", ref_id=route_id,
                    )
                    if not pi_ally_ok:
                        print("[WARN] No se pudo cobrar fee al aliado (cancel_ally) en ruta {}: {}".format(route_id, pi_ally_msg))
        # Siempre fee al courier en cancel_courier; en cancel_ally también
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id:
            pi_courier_ok, pi_courier_msg = apply_service_fee(
                target_type="COURIER", target_id=courier_id,
                admin_id=courier_admin_id,
                ref_type="ROUTE", ref_id=route_id,
            )
            if not pi_courier_ok:
                print("[WARN] No se pudo cobrar fee al repartidor (pin issue) en ruta {}: {}".format(route_id, pi_courier_msg))

        label = "falla del repartidor" if action == "cancel_courier" else "falla del aliado"
        query.edit_message_text(
            "Parada {} cancelada ({}).\n"
            "El repartidor continuara con las demas paradas.".format(seq, label)
        )
        _notify_courier_route_stop_resolved(context, courier_id, route_id, seq, action)

    # Verificar si quedan paradas pendientes para continuar la ruta
    pending = get_pending_route_stops(route_id)
    if pending:
        courier = get_courier_by_id(courier_id)
        if courier:
            courier_user = get_user_by_id(courier["user_id"])
            if courier_user and courier_user["telegram_id"]:
                next_stop = pending[0]
                _send_route_stop_to_courier(context, courier_user["telegram_id"], route, next_stop)
    else:
        # Todas las paradas resueltas (entregadas o canceladas)
        update_route_status(route_id, "DELIVERED", "delivered_at")
        # Fee base al aliado: $300 (igual que pedido individual — $200 admin + $100 plataforma)
        ally_id_route = route["ally_id"]
        ally_admin_id_route = _row_value(route, "ally_admin_id_snapshot")
        if not ally_admin_id_route:
            ally_link_r = get_approved_admin_link_for_ally(ally_id_route) if ally_id_route else None
            ally_admin_id_route = ally_link_r["admin_id"] if ally_link_r else None
        if ally_id_route and ally_admin_id_route and not check_ally_active_subscription(ally_id_route):
            ally_ok_r, ally_msg_r = apply_service_fee(
                target_type="ALLY", target_id=ally_id_route,
                admin_id=ally_admin_id_route, ref_type="ROUTE", ref_id=route_id,
                total_fee=route["total_fee"],
            )
            if not ally_ok_r:
                print("[WARN] No se pudo cobrar fee base al aliado en ruta {}: {}".format(route_id, ally_msg_r))
        # Fee base al repartidor: $300 (igual que pedido individual — $200 admin + $100 plataforma)
        courier_admin_id_r = _row_value(route, "courier_admin_id_snapshot")
        if not courier_admin_id_r and courier_id:
            courier_admin_id_r = get_approved_admin_id_for_courier(courier_id)
        if courier_id and courier_admin_id_r:
            courier_ok_r, courier_msg_r = apply_service_fee(
                target_type="COURIER", target_id=courier_id,
                admin_id=courier_admin_id_r, ref_type="ROUTE", ref_id=route_id,
            )
            if not courier_ok_r:
                print("[WARN] No se pudo cobrar fee base al repartidor en ruta {}: {}".format(route_id, courier_msg_r))
        # Fee adicional por paradas extra: $200 c/u (split 50/50 admin/plataforma)
        ok, msg = liquidate_route_additional_stops_fee(route_id)
        if not ok and "no tiene additional_stops_fee" not in msg and "ya tenia liquidado" not in msg and "incidencias/cancelaciones" not in msg:
            print("[WARN] No se pudo liquidar additional_stops_fee de ruta {}: {}".format(route_id, msg))
        _notify_ally_route_delivered(context, route)
        # Notificar al courier si hay devoluciones pendientes
        cancelled = [s for s in get_route_destinations(route_id)
                     if str(s["status"] or "").startswith("CANCELLED")]
        if cancelled:
            try:
                courier = get_courier_by_id(courier_id)
                courier_user = get_user_by_id(courier["user_id"]) if courier else None
                if courier_user and courier_user["telegram_id"]:
                    names = [s["customer_name"] or "Parada {}".format(s["sequence"]) for s in cancelled]
                    context.bot.send_message(
                        chat_id=courier_user["telegram_id"],
                        text=(
                            "Ruta #{} completada.\n\n"
                            "Tienes {} parada(s) cancelada(s) que requieren devolucion:\n"
                            "{}\n\n"
                            "Dirígete al punto de recogida para devolver los productos."
                        ).format(route_id, len(cancelled), "\n".join("- " + n for n in names)),
                    )
            except Exception as e:
                print("[WARN] No se pudo notificar devoluciones al courier: {}".format(e))


def _notify_courier_route_stop_resolved(context, courier_id, route_id, seq, resolution):
    """Notifica al courier el resultado de la intervencion del admin en una parada."""
    try:
        courier = get_courier_by_id(courier_id)
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return
        messages = {
            "fin": "Tu administrador finalizo la parada {} de la ruta #{}.".format(seq, route_id),
            "cancel_courier": (
                "La parada {} de la ruta #{} fue cancelada. Falla atribuida a ti. "
                "Continua con las demas paradas.".format(seq, route_id)
            ),
            "cancel_ally": (
                "La parada {} de la ruta #{} fue cancelada. Falla atribuida al aliado. "
                "Continua con las demas paradas.".format(seq, route_id)
            ),
        }
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=messages.get(resolution, "Parada {} resuelta por tu administrador.".format(seq)),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar resolucion de parada al courier {}: {}".format(courier_id, e))
