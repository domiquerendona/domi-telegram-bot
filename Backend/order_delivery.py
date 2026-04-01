import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

from db import (
    assign_order_to_courier,
    cancel_order,
    get_platform_admin,
    create_offer_queue,
    delete_offer_queue,
    get_all_orders,
    get_active_orders_by_ally,
    get_routes_by_status,
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
    get_admin_special_orders_between,
    get_admin_special_orders_recent,
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
    get_ally_link_balance,
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
)
from datetime import datetime, timezone, timedelta
from db import (
    add_courier_rating,
    _coerce_datetime,
    _row_value,
    block_courier_for_ally,
    deactivate_courier,
    set_courier_arrived,
    set_route_courier_arrived,
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
    upsert_scheduled_job,
    cancel_scheduled_job,
    mark_job_executed,
    get_pending_scheduled_jobs,
    get_order_excluded_couriers,
    add_order_excluded_courier,
    reset_order_excluded_couriers,
    create_pending_fee_collection,
    resolve_pending_fee_collection,
    get_pending_fee_collection,
)
from services import apply_service_fee, check_service_fee_available, haversine_km, liquidate_route_additional_stops_fee, add_route_incentive, check_ally_active_subscription, get_fee_config, get_order_penalty_config, cancel_order_by_actor, cancel_route_by_actor, penalize_courier_for_delay_and_release, penalize_route_courier_for_delay_and_release, apply_special_order_commission, apply_special_order_creator_fees, check_special_commission_available


def _schedule_persistent_job(context, callback, when_seconds, name, job_data=None):
    """Programa un job y lo persiste en BD para recuperacion tras reinicio."""
    fire_at = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=when_seconds)).isoformat()
    try:
        upsert_scheduled_job(name, callback.__name__, fire_at, json.dumps(job_data or {}))
    except Exception as e:
        logger.warning("_schedule_persistent_job: no se pudo persistir job %s: %s", name, e)
    context.job_queue.run_once(callback, when=when_seconds, context=job_data or {}, name=name)


def _cancel_persistent_job(context, name):
    """Cancela un job del queue y lo marca cancelado en BD."""
    for job in context.job_queue.get_jobs_by_name(name):
        job.schedule_removal()
    try:
        cancel_scheduled_job(name)
    except Exception as e:
        logger.warning("_cancel_persistent_job: no se pudo cancelar job %s: %s", name, e)


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
    if arrived and pickup_conf:
        result["espera_recogida"] = (pickup_conf - arrived).total_seconds()
    if pickup_conf and delivered:
        result["entrega_cliente"] = (delivered - pickup_conf).total_seconds()
    if accepted and delivered:
        result["tiempo_total"] = (delivered - accepted).total_seconds()
    return result


def _get_route_durations(route, delivered_now=False):
    """
    Calcula duraciones por etapa de una ruta. Retorna dict con claves presentes segun datos disponibles:
      llegada_aliado:  courier_arrived_at - accepted_at
      tiempo_total:    delivered_at       - accepted_at
    delivered_now=True: usa datetime.now() como delivered_at.
    """
    from db import _row_value as _rv

    def _parse(val):
        if val is None:
            return None
        if hasattr(val, 'timetuple'):
            return val
        s = str(val).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                return datetime.strptime(s[:len(fmt)], fmt)
            except ValueError:
                continue
        return None

    result = {}
    accepted  = _parse(_rv(route, "accepted_at"))
    arrived   = _parse(_rv(route, "courier_arrived_at"))
    delivered = datetime.now(timezone.utc).replace(tzinfo=None) if delivered_now else _parse(_rv(route, "delivered_at"))

    if accepted and arrived:
        result["llegada_aliado"] = (arrived - accepted).total_seconds()
    if accepted and delivered:
        result["tiempo_total"] = (delivered - accepted).total_seconds()
    return result


OFFER_TIMEOUT_SECONDS = 30
OFFER_RETRY_SECONDS = 30
MAX_CYCLE_SECONDS = 600  # 10 minutos

ARRIVAL_INACTIVITY_SECONDS = 5 * 60    # 5 min: Rappi-style
ARRIVAL_WARN_SECONDS = 15 * 60         # 15 min: advertir al aliado
ARRIVAL_DEADLINE_SECONDS = 20 * 60     # 20 min: auto-liberar
ARRIVAL_RADIUS_KM = 0.15               # 150 metros
ARRIVAL_MOVEMENT_THRESHOLD_KM = 0.05   # 50 metros de movimiento mínimo hacia pickup
COMMISSION_CONFIRM_THRESHOLD = 5000    # Comisiones >= $5.000 requieren confirmación explícita del courier
OFFER_NO_RESPONSE_SECONDS = 300        # 5 min sin respuesta → sugerir incentivo
DELIVERY_REMINDER_SECONDS = 30 * 60   # 30 min en PICKED_UP → recordar al repartidor
DELIVERY_ADMIN_ALERT_SECONDS = 60 * 60  # 60 min en PICKED_UP → alertar al admin
DELIVERY_RADIUS_KM = 0.15              # 150 metros para validar entrega GPS
PICKUP_AUTOCONFIRM_SECONDS = 120        # 2 min → auto-confirmar llegada al pickup si aliado no responde

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


def _offer_reply_markup(order_id, special_commission=0):
    rows = [
        [
            InlineKeyboardButton("Aceptar", callback_data="order_accept_{}".format(order_id)),
            InlineKeyboardButton("Rechazar", callback_data="order_reject_{}".format(order_id)),
        ],
        [InlineKeyboardButton("Estoy ocupado", callback_data="order_busy_{}".format(order_id))],
    ]
    if special_commission and int(special_commission) > 0:
        rows.insert(0, [InlineKeyboardButton(
            "Ver detalle financiero del servicio",
            callback_data="order_fee_detail_{}".format(order_id),
        )])
    return InlineKeyboardMarkup(rows)



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
        _cancel_persistent_job(context, name)
    context.bot_data.get("arrival_manual_prompted", {}).pop(order_id, None)


def _cancel_delivery_reminder_jobs(context, order_id):
    """Cancela los jobs de recordatorio de entrega T+30 y alerta admin T+60."""
    for name in [
        "delivery_reminder_{}".format(order_id),
        "delivery_admin_alert_{}".format(order_id),
    ]:
        _cancel_persistent_job(context, name)


def _delivery_reminder_job(context):
    """T+30: recuerda al repartidor que tiene un pedido en curso sin finalizar."""
    mark_job_executed(context.job.name)
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
        logger.warning("No se pudo enviar recordatorio de entrega al repartidor (pedido %s): %s", order_id, e)


def _delivery_admin_alert_job(context):
    """T+60: notifica al admin del equipo que el pedido lleva mucho tiempo en curso."""
    mark_job_executed(context.job.name)
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
        logger.warning("No se pudo enviar alerta de entrega al admin (pedido %s): %s", order_id, e)


def _cancel_no_response_job(context, order_id):
    """Cancela el job de sugerencia de incentivo T+5 para un pedido."""
    _cancel_persistent_job(context, "offer_no_response_{}".format(order_id))


def _cancel_offer_retry_job(context, order_id):
    """Cancela el job de reintento cuando un pedido esta esperando couriers elegibles."""
    _cancel_persistent_job(context, "offer_retry_{}".format(order_id))


def _cancel_pickup_autoconfirm_job(context, order_id):
    """Cancela el job de auto-confirmacion de llegada al pickup (pedido)."""
    _cancel_persistent_job(context, "pickup_autoconfirm_{}".format(order_id))


def _cancel_route_pickup_autoconfirm_job(context, route_id):
    """Cancela el job de auto-confirmacion de llegada al pickup (ruta)."""
    _cancel_persistent_job(context, "route_pickup_autoconfirm_{}".format(route_id))


def _cancel_route_no_response_job(context, route_id):
    """Cancela el job de sugerencia de incentivo T+5 para una ruta."""
    _cancel_persistent_job(context, "route_no_response_{}".format(route_id))


def _cancel_route_offer_retry_job(context, route_id):
    """Cancela el job de reintento cuando una ruta esta esperando couriers elegibles."""
    _cancel_persistent_job(context, "route_offer_retry_{}".format(route_id))


def _cancel_order_expire_job(context, order_id):
    """Cancela el job de expiración automática T+10 para un pedido."""
    _cancel_persistent_job(context, "order_expire_{}".format(order_id))


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

    _schedule_persistent_job(
        context, _order_expire_job, remaining,
        "order_expire_{}".format(order_id), {"order_id": order_id},
    )


def _order_expire_job(context):
    """Job T+10: si el pedido sigue PUBLISHED, expira automáticamente."""
    mark_job_executed(context.job.name)
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return

    cycle_info = context.bot_data.get("offer_cycles", {}).get(order_id) or _build_cycle_info_for_expire(order)
    _expire_order(order_id, cycle_info, context)


def _schedule_offer_retry_job(context, order_id, delay_seconds=OFFER_RETRY_SECONDS):
    """Programa un reintento del ciclo cuando no hay couriers elegibles en este momento."""
    _cancel_offer_retry_job(context, order_id)
    _schedule_persistent_job(
        context,
        _offer_retry_job,
        delay_seconds,
        "offer_retry_{}".format(order_id),
        {"order_id": order_id},
    )


def _offer_retry_job(context):
    """Reintenta publicar o reactivar la siguiente oferta de un pedido PUBLISHED."""
    mark_job_executed(context.job.name)
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return

    if get_current_offer_for_order(order_id):
        return

    _send_next_offer(order_id, context)


def _activate_order_offer_dispatch(order_id, context, cycle_info, courier_ids):
    """Deja el pedido activo aunque temporalmente no haya couriers relanzables."""
    delete_offer_queue(order_id)
    if courier_ids:
        create_offer_queue(order_id, courier_ids)
        _cancel_offer_retry_job(context, order_id)
    else:
        logger.info(
            "publish_order_to_couriers: pedido %s activo sin couriers relanzables; reintentara en %ss",
            order_id,
            OFFER_RETRY_SECONDS,
        )
        _schedule_offer_retry_job(context, order_id)

    set_order_status(order_id, "PUBLISHED", "published_at")
    context.bot_data.setdefault("offer_cycles", {})[order_id] = cycle_info

    if courier_ids:
        _send_next_offer(order_id, context)


def _offer_no_response_job(context):
    """Job T+5: si el pedido sigue PUBLISHED, sugiere al creador que agregue incentivo."""
    mark_job_executed(context.job.name)
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
        logger.warning("Error obteniendo creador para pedido %s: %s", order_id, e)
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
        logger.warning("Error enviando sugerencia para pedido %s: %s", order_id, e)


def repost_order_to_couriers(order_id, context, excluded_courier_ids=None):
    """Re-oferta un pedido a todos los couriers activos (usado tras agregar incentivo).

    Limpia la cola existente, resetea los excluded_couriers y relanza el ciclo de ofertas.
    No verifica saldo del aliado/admin (ya fue verificado al crear el pedido).
    """
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return 0

    excluded_courier_ids = {int(cid) for cid in (excluded_courier_ids or []) if cid}

    # Limpiar cola existente, excluded_couriers en memoria y en BD
    clear_offer_queue(order_id)
    _cancel_offer_retry_job(context, order_id)
    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    try:
        reset_order_excluded_couriers(order_id)
        for courier_id in excluded_courier_ids:
            add_order_excluded_courier(order_id, courier_id)
    except Exception:
        pass

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


def _build_cancel_preview(status, created_at, charge_owner_type, has_courier):
    """Calcula el cargo esperado antes de confirmar una cancelacion."""
    cfg = get_order_penalty_config()
    preview = {
        "fee_total": 0,
        "courier_compensation": 0,
        "platform_share": 0,
        "code": "FREE",
        "grace_seconds_left": cfg["ally_cancel_grace_seconds"],
        "charged_owner_type": charge_owner_type or "",
    }

    if charge_owner_type not in ("ALLY", "ADMIN"):
        return preview

    if status == "ACCEPTED" and has_courier:
        preview.update(
            {
                "fee_total": cfg["ally_cancel_with_courier_total"],
                "courier_compensation": cfg["ally_cancel_with_courier_courier_share"],
                "platform_share": cfg["ally_cancel_with_courier_platform_share"],
                "code": "WITH_COURIER",
                "grace_seconds_left": 0,
            }
        )
        return preview

    created_dt = _coerce_datetime(created_at)
    elapsed_created = max(0, int((datetime.now(timezone.utc).replace(tzinfo=None) - created_dt).total_seconds()))
    preview["grace_seconds_left"] = max(0, cfg["ally_cancel_grace_seconds"] - elapsed_created)
    if elapsed_created > cfg["ally_cancel_grace_seconds"]:
        preview.update(
            {
                "fee_total": cfg["ally_cancel_after_grace_total"],
                "courier_compensation": 0,
                "platform_share": cfg["ally_cancel_after_grace_total"],
                "code": "AFTER_GRACE",
            }
        )
    return preview


def _build_order_cancel_preview(order):
    """Calcula el cargo esperado antes de confirmar cancelacion del pedido."""
    charge_owner_type = ""
    if _row_value(order, "ally_id"):
        charge_owner_type = "ALLY"
    elif _row_value(order, "creator_admin_id"):
        charge_owner_type = "ADMIN"
    return _build_cancel_preview(
        (_row_value(order, "status", 0) or "").strip().upper(),
        _row_value(order, "created_at"),
        charge_owner_type,
        bool(_row_value(order, "courier_id")),
    )


def _build_route_cancel_preview(route):
    """Calcula el cargo esperado antes de confirmar cancelacion de la ruta."""
    charge_owner_type = "ALLY" if _row_value(route, "ally_id") else ""
    return _build_cancel_preview(
        (_row_value(route, "status", 0) or "").strip().upper(),
        _row_value(route, "created_at"),
        charge_owner_type,
        bool(_row_value(route, "courier_id")),
    )


def _format_order_cancel_warning(order, actor_label="ally"):
    """Arma el texto de advertencia previo a cancelar un pedido."""
    preview = _build_order_cancel_preview(order)
    order_id = _row_value(order, "id")
    is_admin = actor_label == "admin"
    owner_type = preview.get("charged_owner_type") or ""

    if preview["fee_total"] <= 0:
        if is_admin and owner_type == "ADMIN":
            owner_line = "Cancelacion gratuita para el admin creador."
        elif is_admin:
            owner_line = "Cancelacion gratuita para el aliado."
        else:
            owner_line = "Cancelacion gratuita."
        grace_left = preview["grace_seconds_left"]
        return (
            "Vas a cancelar el pedido #{}.\n\n"
            "{}\n"
            "Aun estas dentro de los primeros 60 segundos.\n"
            "Te quedan {} segundos sin cargo."
        ).format(order_id, owner_line, max(0, grace_left))

    if is_admin and owner_type == "ADMIN" and preview["courier_compensation"] > 0:
        return (
            "Vas a cancelar el pedido #{}.\n\n"
            "Penalidad de ${:,} (${:,.0f} para el repartidor).\n"
            "Si confirmas, se descontaran ${:,} del saldo del admin creador del pedido.\n"
            "Distribucion:\n"
            "- Repartidor: ${:,}\n"
            "- Plataforma: ${:,}"
        ).format(
            order_id,
            preview["fee_total"],
            preview["courier_compensation"],
            preview["fee_total"],
            preview["courier_compensation"],
            preview["platform_share"],
        )

    if preview["courier_compensation"] > 0:
        charge_line = (
            "Si confirmas, se descontaran ${:,} del saldo del aliado dueño del servicio."
            if is_admin else
            "Si confirmas, se te descontaran ${:,} de tu saldo."
        ).format(preview["fee_total"])
        return (
            "Vas a cancelar el pedido #{}.\n\n"
            "Penalidad de ${:,} (${:,.0f} para el repartidor).\n"
            "{}\n"
            "Distribucion:\n"
            "- Repartidor: ${:,}\n"
            "- Plataforma: ${:,}"
        ).format(
            order_id,
            preview["fee_total"],
            preview["courier_compensation"],
            charge_line,
            preview["courier_compensation"],
            preview["platform_share"],
        )

    if is_admin and owner_type == "ADMIN":
        return (
            "Vas a cancelar el pedido #{}.\n\n"
            "Penalidad de ${:,}.\n"
            "Si confirmas, se descontaran ${:,} del saldo del admin creador del pedido.\n"
            "Ese valor ira a la Plataforma por cancelacion tardia."
        ).format(order_id, preview["fee_total"], preview["fee_total"])

    charge_line = (
        "Si confirmas, se descontaran ${:,} del saldo del aliado dueño del servicio."
        if is_admin else
        "Si confirmas, se te descontaran ${:,} de tu saldo."
    ).format(preview["fee_total"])
    return (
        "Vas a cancelar el pedido #{}.\n\n"
        "Penalidad de ${:,}.\n"
        "{}\n"
        "Ese valor ira a la Plataforma por cancelacion tardia."
    ).format(order_id, preview["fee_total"], charge_line)


def _build_order_cancel_result_text(order_id, actor_label, outcome):
    """Texto final despues de cancelar un pedido."""
    owner_type = outcome.get("charged_owner_type") or ""
    if outcome["fee_total"] <= 0:
        return "Pedido #{} cancelado. No se aplico ningun cargo.".format(order_id)

    if actor_label == "admin" and owner_type == "ADMIN":
        if outcome["penalty_applied"] and outcome["courier_compensation"] > 0:
            return (
                "Pedido #{} cancelado.\n"
                "Se desconto ${:,} al admin creador del pedido.\n"
                "Compensacion al repartidor: ${:,}.\n"
                "Plataforma: ${:,}."
            ).format(
                order_id,
                outcome["fee_total"],
                outcome["courier_compensation"],
                outcome["platform_share"],
            )
        if outcome["penalty_applied"]:
            return (
                "Pedido #{} cancelado.\n"
                "Se desconto ${:,} al admin creador del pedido.\n"
                "Ese valor fue registrado para la Plataforma."
            ).format(order_id, outcome["fee_total"])
        return (
            "Pedido #{} cancelado.\n"
            "Se intento cobrar ${:,} al admin creador del pedido, pero no fue posible.\n{}"
        ).format(
            order_id,
            outcome["fee_total"],
            outcome["penalty_message"] or "No se pudo aplicar el cargo automatico.",
        )

    if outcome["penalty_applied"]:
        if outcome["courier_compensation"] > 0:
            owner_line = (
                "Se desconto ${:,} al aliado dueño del servicio."
                if actor_label == "admin" else
                "Se descontaron ${:,} de tu saldo."
            ).format(outcome["fee_total"])
            return (
                "Pedido #{} cancelado.\n{}\n"
                "Compensacion al repartidor: ${:,}.\n"
                "Plataforma: ${:,}."
            ).format(
                order_id,
                owner_line,
                outcome["courier_compensation"],
                outcome["platform_share"],
            )

        owner_line = (
            "Se desconto ${:,} al aliado dueño del servicio."
            if actor_label == "admin" else
            "Se descontaron ${:,} de tu saldo."
        ).format(outcome["fee_total"])
        return (
            "Pedido #{} cancelado.\n{}\n"
            "Ese valor fue registrado para la Plataforma."
        ).format(order_id, owner_line)

    owner_line = (
        "Se intento cobrar ${:,} al aliado dueño del servicio, pero no fue posible."
        if actor_label == "admin" else
        "Se intento cobrar ${:,}, pero no fue posible."
    ).format(outcome["fee_total"])
    return (
        "Pedido #{} cancelado.\n{}\n{}"
    ).format(order_id, owner_line, outcome["penalty_message"] or "No se pudo aplicar el cargo automatico.")


def _format_route_cancel_warning(route, actor_label="ally"):
    """Arma el texto de advertencia previo a cancelar una ruta."""
    preview = _build_route_cancel_preview(route)
    route_id = _row_value(route, "id")

    if preview["fee_total"] <= 0:
        return (
            "Vas a cancelar la ruta #{}.\n\n"
            "Cancelacion gratuita.\n"
            "Aun estas dentro de los primeros 60 segundos.\n"
            "Te quedan {} segundos sin cargo."
        ).format(route_id, max(0, preview["grace_seconds_left"]))

    if preview["courier_compensation"] > 0:
        return (
            "Vas a cancelar la ruta #{}.\n\n"
            "Penalidad de ${:,} (${:,.0f} para el repartidor).\n"
            "Si confirmas, se te descontaran ${:,} de tu saldo.\n"
            "Distribucion:\n"
            "- Repartidor: ${:,}\n"
            "- Plataforma: ${:,}"
        ).format(
            route_id,
            preview["fee_total"],
            preview["courier_compensation"],
            preview["fee_total"],
            preview["courier_compensation"],
            preview["platform_share"],
        )

    return (
        "Vas a cancelar la ruta #{}.\n\n"
        "Penalidad de ${:,}.\n"
        "Si confirmas, se te descontaran ${:,} de tu saldo.\n"
        "Ese valor ira a la Plataforma por cancelacion tardia."
    ).format(route_id, preview["fee_total"], preview["fee_total"])


def _build_route_cancel_result_text(route_id, actor_label, outcome):
    """Texto final despues de cancelar una ruta."""
    if outcome["fee_total"] <= 0:
        return "Ruta #{} cancelada. No se aplico ningun cargo.".format(route_id)

    if outcome["penalty_applied"]:
        if outcome["courier_compensation"] > 0:
            return (
                "Ruta #{} cancelada.\n"
                "Se descontaron ${:,} de tu saldo.\n"
                "Compensacion al repartidor: ${:,}.\n"
                "Plataforma: ${:,}."
            ).format(
                route_id,
                outcome["fee_total"],
                outcome["courier_compensation"],
                outcome["platform_share"],
            )
        return (
            "Ruta #{} cancelada.\n"
            "Se descontaron ${:,} de tu saldo.\n"
            "Ese valor fue registrado para la Plataforma."
        ).format(route_id, outcome["fee_total"])

    return (
        "Ruta #{} cancelada.\n"
        "Se intento cobrar ${:,}, pero no fue posible.\n{}"
    ).format(
        route_id,
        outcome["fee_total"],
        outcome["penalty_message"] or "No se pudo aplicar el cargo automatico.",
    )


def _handle_repost_ally(update, context, order_id):
    """Aliado re-oferta un pedido PENDING o PUBLISHED desde sus pedidos activos."""
    query = update.callback_query
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.answer("Usuario no encontrado.", show_alert=True)
        return
    ally = get_ally_by_user_id(user["id"])
    if not ally:
        query.answer("Perfil de aliado no encontrado.", show_alert=True)
        return

    order = get_order_by_id(order_id)
    if not order or _row_value(order, "ally_id") != ally["id"]:
        query.answer("No tienes permiso para esta accion.", show_alert=True)
        return

    status = order["status"]
    if status not in ("PENDING", "PUBLISHED"):
        query.answer("Este pedido ya no puede re-ofertarse.", show_alert=True)
        return

    # Para PUBLISHED: cancelar jobs y cola existentes antes de republicar
    if status == "PUBLISHED":
        _cancel_no_response_job(context, order_id)
        _cancel_order_expire_job(context, order_id)
        _cancel_offer_retry_job(context, order_id)
        current = get_current_offer_for_order(order_id)
        if current:
            _cancel_offer_jobs(context, order_id, current["queue_id"])
        clear_offer_queue(order_id)
        context.bot_data.get("offer_cycles", {}).pop(order_id, None)
        context.bot_data.get("offer_messages", {}).pop(order_id, None)

    creator_admin_id = _row_value(order, "creator_admin_id")
    admin_id_override = int(creator_admin_id) if creator_admin_id else None

    count = publish_order_to_couriers(
        order_id=order_id,
        ally_id=ally["id"],
        context=context,
        admin_id_override=admin_id_override,
        skip_fee_check=True,
    )

    if count > 0:
        query.edit_message_text(
            "Pedido #{} re-ofertado. Se notifico a {} repartidor(es).".format(order_id, count)
        )
    else:
        query.answer(
            "Por ahora no hay repartidores disponibles. El pedido sigue activo y se reintentara automaticamente.",
            show_alert=True,
        )


def _route_no_response_job(context):
    """Job T+5: si la ruta sigue PUBLISHED, sugiere al aliado que agregue incentivo."""
    mark_job_executed(context.job.name)
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
        logger.warning("Error obteniendo creador para ruta %s: %s", route_id, e)
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
        logger.warning("Error enviando sugerencia para ruta %s: %s", route_id, e)


def _schedule_route_offer_retry_job(context, route_id, delay_seconds=None):
    """Programa un reintento del ciclo cuando no hay couriers elegibles para la ruta."""
    if delay_seconds is None:
        delay_seconds = ROUTE_OFFER_RETRY_SECONDS
    _cancel_route_offer_retry_job(context, route_id)
    _schedule_persistent_job(
        context,
        _route_offer_retry_job,
        delay_seconds,
        "route_offer_retry_{}".format(route_id),
        {"route_id": route_id},
    )


def _route_offer_retry_job(context):
    """Reintenta publicar o reactivar la siguiente oferta de una ruta PUBLISHED."""
    mark_job_executed(context.job.name)
    data = context.job.context or {}
    route_id = data.get("route_id")
    if not route_id:
        return

    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        return

    if get_current_route_offer(route_id):
        return

    _send_next_route_offer(route_id, context)


def _get_route_candidate_courier_ids(route_id, ally_id, admin_id, excluded_courier_ids=None):
    """Recalcula los couriers relanzables de una ruta con las reglas actuales."""
    route = get_route_by_id(route_id)
    if not route:
        return None, [], 0

    pickup_lat = route["pickup_lat"]
    pickup_lng = route["pickup_lng"]

    route_max_dist_km = None
    try:
        import math as _rmath
        route_destinations = get_route_destinations(route_id)
        for destination in route_destinations:
            d_lat = destination.get("dropoff_lat") if hasattr(destination, "get") else destination["dropoff_lat"]
            d_lng = destination.get("dropoff_lng") if hasattr(destination, "get") else destination["dropoff_lng"]
            if d_lat is not None and d_lng is not None and pickup_lat is not None and pickup_lng is not None:
                r_lat = _rmath.radians(d_lat - pickup_lat)
                r_lng = _rmath.radians(d_lng - pickup_lng)
                a_val = (_rmath.sin(r_lat / 2) ** 2
                         + _rmath.cos(_rmath.radians(pickup_lat)) * _rmath.cos(_rmath.radians(d_lat))
                         * _rmath.sin(r_lng / 2) ** 2)
                seg_km = 6371.0 * 2 * _rmath.atan2(_rmath.sqrt(a_val), _rmath.sqrt(1 - a_val))
                if route_max_dist_km is None or seg_km > route_max_dist_km:
                    route_max_dist_km = seg_km
    except Exception:
        route_max_dist_km = None

    excluded_courier_ids = {int(cid) for cid in (excluded_courier_ids or []) if cid}
    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=False,
        cash_required_amount=0,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        order_distance_km=route_max_dist_km,
    )

    courier_ids = []
    for courier in eligible:
        courier_id = courier["courier_id"]
        if courier_id in excluded_courier_ids:
            continue
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if not courier_admin_id:
            continue
        fee_ok, _ = check_service_fee_available("COURIER", courier_id, courier_admin_id)
        if fee_ok:
            courier_ids.append(courier_id)

    return route, courier_ids, len(eligible)


def _activate_route_offer_dispatch(route_id, context, cycle_info, courier_ids):
    """Deja la ruta activa aunque temporalmente no haya couriers relanzables."""
    delete_route_offer_queue(route_id)
    if courier_ids:
        create_route_offer_queue(route_id, courier_ids)
        _cancel_route_offer_retry_job(context, route_id)
    else:
        logger.info(
            "publish_route_to_couriers: ruta %s activa sin couriers relanzables; reintentara en %ss",
            route_id,
            ROUTE_OFFER_RETRY_SECONDS,
        )
        _schedule_route_offer_retry_job(context, route_id)

    update_route_status(route_id, "PUBLISHED", "published_at")
    context.bot_data.setdefault("route_offer_cycles", {})[route_id] = cycle_info

    if courier_ids:
        _send_next_route_offer(route_id, context)


def repost_route_to_couriers(route_id, context, excluded_courier_ids=None):
    """Re-oferta una ruta a todos los couriers con saldo (usado tras agregar incentivo).

    Limpia la cola existente y relanza el ciclo de ofertas.
    """
    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        return 0

    excluded_courier_ids = {int(cid) for cid in (excluded_courier_ids or []) if cid}
    delete_route_offer_queue(route_id)
    _cancel_route_offer_retry_job(context, route_id)
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
        excluded_courier_ids=excluded_courier_ids,
    )
    return count


def _handle_repost_ally_route(update, context, route_id):
    """Aliado re-oferta una ruta PUBLISHED desde sus pedidos activos."""
    query = update.callback_query
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.answer("Usuario no encontrado.", show_alert=True)
        return
    ally = get_ally_by_user_id(user["id"])
    if not ally:
        query.answer("Perfil de aliado no encontrado.", show_alert=True)
        return

    route = get_route_by_id(route_id)
    if not route or route.get("ally_id") != ally["id"]:
        query.answer("No tienes permiso para esta accion.", show_alert=True)
        return

    if route["status"] != "PUBLISHED":
        query.answer("Esta ruta ya no puede re-ofertarse.", show_alert=True)
        return

    # Cancelar job de sugerencia y limpiar cola existente
    _cancel_route_no_response_job(context, route_id)
    _cancel_route_offer_retry_job(context, route_id)
    delete_route_offer_queue(route_id)
    context.bot_data.get("route_offer_cycles", {}).pop(route_id, None)
    context.bot_data.get("route_offer_messages", {}).pop(route_id, None)

    admin_id_override = _row_value(route, "ally_admin_id_snapshot")
    if admin_id_override:
        admin_id_override = int(admin_id_override)

    count = publish_route_to_couriers(
        route_id=route_id,
        ally_id=ally["id"],
        context=context,
        admin_id_override=admin_id_override,
    )

    if count > 0:
        query.edit_message_text(
            "Ruta #{} re-ofertada. Se notifico a {} repartidor(es).".format(route_id, count)
        )
    else:
        query.answer(
            "Por ahora no hay repartidores disponibles. La ruta sigue activa y se reintentara automaticamente.",
            show_alert=True,
        )


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
        logger.warning("No se pudo notificar saldo insuficiente al aliado %s: %s", ally_id, e)


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
        logger.warning("No se pudo notificar saldo insuficiente al admin %s: %s", admin_id, e)


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
        logger.warning("No se pudo notificar saldo insuficiente al courier %s: %s", courier_id, e)


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
            logger.warning("Aliado sin admin aprobado, no se puede publicar pedido")
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
            logger.warning("Pedido %s sin oferta por saldo aliado/admin: %s", order_id, ally_code)
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

    # Leer campos especiales del pedido para pedidos de admin
    special_commission = int(order["special_commission"] or 0) if "special_commission" in order.keys() else 0
    team_only = int(order["team_only"] or 0) if "team_only" in order.keys() else 0

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
    eligible_count = len(eligible)

    # Filtro team_only: pedidos especiales que el admin quiere ofrecer solo a su equipo.
    if team_only and admin_id:
        eligible = [c for c in eligible if get_approved_admin_id_for_courier(c["courier_id"]) == admin_id]

    # Verificacion previa de saldo por courier usando el admin PROPIO de cada courier.
    # Siempre se verifica saldo para el fee estandar ($300).
    # Si hay comision especial: se verifica saldo para fee_estandar + comision (ambos se cobran al entregar).
    fee_cfg_pub = get_fee_config()
    filtered = []
    couriers_without_balance = []
    for c in eligible:
        courier_id = c["courier_id"]
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id is None:
            couriers_without_balance.append(courier_id)
            continue
        if special_commission > 0:
            ok, code = check_special_commission_available(
                courier_id, special_commission, fee_cfg_pub["fee_service_total"]
            )
        else:
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

    courier_ids = [c["courier_id"] for c in filtered]

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

    cycle_info = {
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
        "excluded_couriers": get_order_excluded_couriers(order_id),
        "order_distance_km": _order_distance_km,
    }

    if not courier_ids:
        logger.info(
            "publish_order_to_couriers: pedido %s sin couriers relanzables (eligible=%s filtered=%s team_only=%s)",
            order_id,
            eligible_count,
            len(filtered),
            int(bool(team_only)),
        )
        if ally_id is not None and eligible and not filtered:
            _notify_recharge_needed_to_ally(context, ally_id)

    _activate_order_offer_dispatch(order_id, context, cycle_info, courier_ids)

    # Programar sugerencia de incentivo si nadie acepta en T+5
    _cancel_no_response_job(context, order_id)
    _schedule_persistent_job(
        context, _offer_no_response_job, OFFER_NO_RESPONSE_SECONDS,
        "offer_no_response_{}".format(order_id), {"order_id": order_id},
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
        logger.info("_send_next_offer: pedido %s sin couriers pendientes; se intentara reiniciar el ciclo", order_id)
        _try_restart_cycle(order_id, context)
        return

    _cancel_offer_retry_job(context, order_id)
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
        courier_id=next_offer["courier_id"],
    )
    special_commission_offer = int(order["special_commission"] or 0) if "special_commission" in order.keys() else 0
    reply_markup = _offer_reply_markup(order_id, special_commission=special_commission_offer)

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
        logger.warning("No se pudo enviar oferta a courier %s: %s", next_offer["courier_id"], e)
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
        order = get_order_by_id(order_id)
        if not order or order["status"] != "PUBLISHED":
            logger.warning("_try_restart_cycle: pedido %s sin cycle_info y fuera de PUBLISHED", order_id)
            return
        cycle_info = _build_recovered_order_cycle_info(order)
        context.bot_data.setdefault("offer_cycles", {})[order_id] = cycle_info
        logger.warning("_try_restart_cycle: pedido %s sin cycle_info; reconstruido desde BD", order_id)

    import time
    elapsed = time.time() - cycle_info["started_at"]

    if elapsed >= MAX_CYCLE_SECONDS:
        logger.info(
            "_try_restart_cycle: pedido %s elapsed=%.0fs supera max=%ss; se expirara",
            order_id,
            elapsed,
            MAX_CYCLE_SECONDS,
        )
        _expire_order(order_id, cycle_info, context)
        return

    admin_id = cycle_info["admin_id"]
    ally_id = cycle_info["ally_id"]
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        logger.warning("_try_restart_cycle: pedido %s ya no esta en PUBLISHED al recalcular", order_id)
        return
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
        order_distance_km=cycle_info.get("order_distance_km"),
    )
    special_commission = int(order["special_commission"] or 0) if "special_commission" in order.keys() else 0
    fee_cfg_pub = get_fee_config() if special_commission > 0 else None
    courier_ids = []
    for courier in fresh:
        courier_id = courier["courier_id"]
        if courier_id in excluded:
            continue
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id is None:
            continue
        if special_commission > 0:
            ok, _ = check_special_commission_available(
                courier_id, special_commission, fee_cfg_pub["fee_service_total"]
            )
        else:
            ok, _ = check_service_fee_available(
                target_type="COURIER",
                target_id=courier_id,
                admin_id=courier_admin_id,
            )
        if ok:
            courier_ids.append(courier_id)
    logger.info(
        "_try_restart_cycle: pedido %s elapsed=%.0fs fresh=%s excluded=%s relanzables=%s",
        order_id,
        elapsed,
        len(fresh),
        len(excluded),
        len(courier_ids),
    )

    if not courier_ids:
        delete_offer_queue(order_id)
        logger.info(
            "_try_restart_cycle: pedido %s sigue activo sin couriers relanzables; reintentara en %ss",
            order_id,
            OFFER_RETRY_SECONDS,
        )
        _schedule_offer_retry_job(context, order_id)
        return

    delete_offer_queue(order_id)
    create_offer_queue(order_id, courier_ids)
    _send_next_offer(order_id, context)


def _expire_order(order_id, cycle_info, context):
    """Nadie acepto en 10 minutos. Cancela el pedido sin cobrar al aliado."""
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return
    logger.info("_expire_order: pedido %s en PUBLISHED sera cancelado sin cargo", order_id)

    _cancel_no_response_job(context, order_id)
    _cancel_order_expire_job(context, order_id)
    _cancel_offer_retry_job(context, order_id)
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
            logger.warning("No se pudo notificar expiracion al aliado: %s", e)
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
            logger.warning("No se pudo notificar expiración al admin creador: %s", e)


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
            if route["status"] == "PUBLISHED":
                keyboard = [
                    [InlineKeyboardButton(
                        "Re-ofrecer",
                        callback_data="ruta_repost_{}".format(route["id"]),
                    )],
                    [InlineKeyboardButton(
                        "Cancelar ruta",
                        callback_data="ruta_cancelar_aliado_{}".format(route["id"]),
                    )],
                ]
                update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            elif route["status"] == "ACCEPTED":
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
            if order["status"] in ("PENDING", "PUBLISHED"):
                keyboard = [
                    [InlineKeyboardButton(
                        "Aumentar incentivo",
                        callback_data="pedido_inc_menu_{}".format(order["id"]),
                    )],
                    [InlineKeyboardButton(
                        "Re-ofrecer",
                        callback_data="order_repost_{}".format(order["id"]),
                    )],
                    [InlineKeyboardButton(
                        "Cancelar pedido",
                        callback_data="order_cancel_{}".format(order["id"]),
                    )],
                ]
                update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            elif order["status"] == "ACCEPTED":
                keyboard = [
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


def _admin_history_period_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Hoy", callback_data="adminhist_periodo_hoy"),
            InlineKeyboardButton("Ayer", callback_data="adminhist_periodo_ayer"),
        ],
        [
            InlineKeyboardButton("Esta semana", callback_data="adminhist_periodo_semana"),
            InlineKeyboardButton("Este mes", callback_data="adminhist_periodo_mes"),
        ],
        [
            InlineKeyboardButton("Ultimos 15", callback_data="adminhist_periodo_recientes"),
        ],
    ])


def _admin_history_flat_text(orders, label):
    """Texto plano de pedidos especiales del admin para Hoy/Ayer."""
    delivered = [o for o in orders if _row_value(o, "status", "") == "DELIVERED"]
    cancelled = [o for o in orders if _row_value(o, "status", "") == "CANCELLED"]

    total_fee = sum(int(_row_value(o, "total_fee", 0) or 0) for o in delivered)
    total_commission = sum(
        int(_row_value(o, "special_commission", 0) or 0) for o in delivered
    )

    STATUS_LABELS = {"DELIVERED": "Entregado", "CANCELLED": "Cancelado"}
    lines = [
        "Mis pedidos especiales — {} ({} pedidos)".format(label, len(orders)),
        "Entregados: {} | Cancelados: {}".format(len(delivered), len(cancelled)),
        "Total tarifas cobradas: {}".format(_fmt_pesos_ally(total_fee)),
    ]
    if total_commission > 0:
        lines.append("Total comisiones: {}".format(_fmt_pesos_ally(total_commission)))
    lines.append("")

    items = []
    for o in orders:
        created = str(_row_value(o, "created_at", "") or "")
        hour = created[11:16] if len(created) >= 16 else "--:--"
        status = _row_value(o, "status", "") or ""
        fee = int(_row_value(o, "total_fee", 0) or 0)
        commission = int(_row_value(o, "special_commission", 0) or 0)
        name = _row_value(o, "customer_name", "N/A") or "N/A"
        commission_str = " (+comision ${:,})".format(commission) if commission > 0 else ""
        items.append((created, "#{} {} — {} — {}{}  [{}]".format(
            _row_value(o, "id", "?"), hour, name,
            _fmt_pesos_ally(fee), commission_str,
            STATUS_LABELS.get(status, status),
        )))
    items.sort(key=lambda x: x[0], reverse=True)
    for _, line in items:
        lines.append(line)

    return "\n".join(lines)


def _admin_history_grouped_text(orders, label):
    """Texto agrupado por dia para semana/mes. Retorna (text, sorted_day_keys)."""
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

    grand_total = sum(d["total"] for d in days.values())
    grand_delivered = sum(d["delivered"] for d in days.values())
    grand_cancelled = sum(d["cancelled"] for d in days.values())
    grand_pesos = sum(d["pesos"] for d in days.values())

    lines = [
        "Mis pedidos especiales — {} ({} pedidos)".format(label, grand_total),
        "Entregados: {} | Cancelados: {}".format(grand_delivered, grand_cancelled),
        "Total tarifas: {}".format(_fmt_pesos_ally(grand_pesos)),
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


def _admin_show_special_recent(query, admin_id):
    """Muestra los ultimos 15 pedidos especiales del admin (todos los estados)."""
    orders = get_admin_special_orders_recent(admin_id, limit=15)
    if not orders:
        query.edit_message_text(
            "Mis pedidos especiales — Ultimos 15\nNo tienes pedidos especiales aun.",
            reply_markup=_admin_history_period_keyboard(),
        )
        return
    STATUS_LABELS = {
        "PUBLISHED": "Publicado",
        "ACCEPTED": "Aceptado",
        "PICKED_UP": "Recogido",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
        "EXPIRED": "Expirado",
    }
    lines = ["Mis pedidos especiales — Ultimos {} ({} pedidos)".format(15, len(orders)), ""]
    action_rows = []
    for o in orders:
        created = str(_row_value(o, "created_at", "") or "")
        day = created[:10] if len(created) >= 10 else "?"
        hour = created[11:16] if len(created) >= 16 else "--:--"
        status = _row_value(o, "status", "") or ""
        fee = int(_row_value(o, "total_fee", 0) or 0)
        name = _row_value(o, "customer_name", "N/A") or "N/A"
        commission = int(_row_value(o, "special_commission", 0) or 0)
        commission_str = " +com${:,}".format(commission) if commission > 0 else ""
        status_label = STATUS_LABELS.get(status, status)
        if status in ("PUBLISHED", "ACCEPTED", "PICKED_UP"):
            action_rows.append([InlineKeyboardButton(
                "Ver pedido #{}".format(_row_value(o, "id", "?")),
                callback_data="admpedidos_detail_{}_{}".format(_row_value(o, "id", "?"), admin_id),
            )])
        lines.append("#{} {} {} — {} — {}{}  [{}]".format(
            _row_value(o, "id", "?"), day, hour, name,
            _fmt_pesos_ally(fee), commission_str, status_label,
        ))
    full_kb = InlineKeyboardMarkup(action_rows + _admin_history_period_keyboard().inline_keyboard)
    query.edit_message_text("\n".join(lines), reply_markup=full_kb)


def admin_special_orders_history_callback(update, context):
    """Callback historial de pedidos especiales del admin.
    Patrones: adminhist_periodo_{period} | adminhist_dia_{YYYYMMDD}_{period} | adminhist_periodo_recientes
    """
    query = update.callback_query
    query.answer()
    data = query.data or ""
    telegram_id = update.effective_user.id

    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.edit_message_text("No se encontro tu usuario.")
        return
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin:
        query.edit_message_text("No tienes perfil de administrador.")
        return

    if data == "adminhist_periodo_recientes":
        _admin_show_special_recent(query, admin["id"])
        return

    if data.startswith("adminhist_periodo_"):
        period = data[len("adminhist_periodo_"):]
        _admin_show_special_period(query, admin["id"], period)
        return

    if data.startswith("adminhist_dia_"):
        rest = data[len("adminhist_dia_"):]
        parts = rest.split("_", 1)
        compact = parts[0]
        parent = parts[1] if len(parts) > 1 else "semana"
        if len(compact) == 8 and compact.isdigit():
            date_key = "{}-{}-{}".format(compact[:4], compact[4:6], compact[6:8])
            _admin_show_special_day(query, admin["id"], date_key, parent)
        else:
            query.edit_message_text("Fecha invalida.", reply_markup=_admin_history_period_keyboard())
        return

    query.edit_message_text(
        "Mis pedidos especiales\nSelecciona un periodo:",
        reply_markup=_admin_history_period_keyboard(),
    )


def _admin_show_special_period(query, admin_id, period):
    start_s, end_s, label = _ally_period_range(period)
    if not start_s:
        query.edit_message_text("Periodo invalido.", reply_markup=_admin_history_period_keyboard())
        return

    orders = get_admin_special_orders_between(admin_id, start_s, end_s)
    if not orders:
        query.edit_message_text(
            "Mis pedidos especiales — {}\nNo hay pedidos en este periodo.".format(label),
            reply_markup=_admin_history_period_keyboard(),
        )
        return

    if period in ("hoy", "ayer"):
        text = _admin_history_flat_text(orders, label)
        query.edit_message_text(text, reply_markup=_admin_history_period_keyboard())
    else:
        text, sorted_keys = _admin_history_grouped_text(orders, label)
        day_buttons = []
        for dk in sorted_keys:
            compact = dk.replace("-", "")
            day_buttons.append([InlineKeyboardButton(
                _fmt_date_es(dk),
                callback_data="adminhist_dia_{}_{}".format(compact, period),
            )])
        full_kb = InlineKeyboardMarkup(day_buttons + _admin_history_period_keyboard().inline_keyboard)
        query.edit_message_text(text, reply_markup=full_kb)


def _admin_show_special_day(query, admin_id, date_key, parent_period):
    try:
        dt = datetime.strptime(date_key, "%Y-%m-%d")
    except ValueError:
        query.edit_message_text("Fecha invalida.", reply_markup=_admin_history_period_keyboard())
        return
    start_s = dt.strftime("%Y-%m-%d 00:00:00")
    end_s = (dt + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    orders = get_admin_special_orders_between(admin_id, start_s, end_s)
    text = _admin_history_flat_text(orders, _fmt_date_es(date_key))
    back_label = "Volver a semana" if parent_period == "semana" else "Volver a mes"
    full_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(back_label, callback_data="adminhist_periodo_{}".format(parent_period))]]
        + _admin_history_period_keyboard().inline_keyboard
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
      admpedidos_cancel_confirm_{order_id}_{admin_id}
      admpedidos_cancel_abort_{order_id}_{admin_id}
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

    ally = get_ally_by_id(order["ally_id"]) if order["ally_id"] else None
    creator_admin_id = order["creator_admin_id"] if "creator_admin_id" in order.keys() else None
    creator_admin = get_admin_by_id(int(creator_admin_id)) if creator_admin_id else None
    ally_name = ally["full_name"] if ally else ("Pedido especial de admin" if creator_admin_id else "N/A")

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
        dur_lines.append("  Llegada al pickup: {}".format(_format_duration(durations["llegada_aliado"])))
    if "espera_recogida" in durations:
        dur_lines.append("  Espera en recogida: {}".format(_format_duration(durations["espera_recogida"])))
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

    if creator_admin:
        creator_label = creator_admin["full_name"] or "Admin #{}".format(creator_admin_id)
        text = text.replace(
            "Repartidor:",
            "Admin creador: {}\nRepartidor:".format(creator_label),
            1,
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
    payload = data.replace("admpedidos_cancel_", "")
    action = "warn"
    if payload.startswith("confirm_"):
        action = "confirm"
        payload = payload.replace("confirm_", "", 1)
    elif payload.startswith("abort_"):
        action = "abort"
        payload = payload.replace("abort_", "", 1)

    parts = payload.rsplit("_", 1)
    if len(parts) != 2:
        query.edit_message_text("Error de formato.")
        return

    try:
        order_id = int(parts[0])
        admin_id = int(parts[1])
    except ValueError:
        query.edit_message_text("Error de formato.")
        return

    if action == "abort":
        return _admin_order_detail(update, context, "admpedidos_detail_{}_{}".format(order_id, admin_id))

    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    if order["status"] in ("DELIVERED", "CANCELLED"):
        query.edit_message_text("Este pedido ya esta {} y no se puede cancelar.".format(
            "entregado" if order["status"] == "DELIVERED" else "cancelado"
        ))
        return

    if action == "warn":
        keyboard = [[
            InlineKeyboardButton(
                "✅ Confirmar",
                callback_data="admpedidos_cancel_confirm_{}_{}".format(order_id, admin_id),
            ),
            InlineKeyboardButton(
                "❌ Volver",
                callback_data="admpedidos_cancel_abort_{}_{}".format(order_id, admin_id),
            ),
        ]]
        query.edit_message_text(
            _format_order_cancel_warning(order, actor_label="admin"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    had_courier = order["courier_id"]
    was_published = order["status"] == "PUBLISHED"
    current_offer = get_current_offer_for_order(order_id) if was_published else None

    outcome = cancel_order_by_actor(
        order_id,
        "ADMIN",
        actor_admin_id=admin_id,
    )
    if not outcome["ok"]:
        query.edit_message_text(outcome["message"])
        return

    _cancel_arrival_jobs(context, order_id)
    _cancel_no_response_job(context, order_id)
    _cancel_order_expire_job(context, order_id)
    if current_offer:
        jobs = context.job_queue.get_jobs_by_name(
            "offer_timeout_{}_{}".format(order_id, current_offer["queue_id"])
        )
        for job in jobs:
            job.schedule_removal()

    _cancel_delivery_reminder_jobs(context, order_id)
    delete_offer_queue(order_id)

    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    context.bot_data.get("offer_messages", {}).pop(order_id, None)

    try:
        ally = get_ally_by_id(order["ally_id"])
        if ally:
            ally_user = get_user_by_id(ally["user_id"])
            if ally_user and ally_user["telegram_id"]:
                ally_text = "Tu pedido #{} fue cancelado por el administrador.".format(order_id)
                if outcome["fee_total"] > 0 and outcome["penalty_applied"]:
                    ally_text += "\nSe desconto ${:,} de tu saldo por esta cancelacion.".format(outcome["fee_total"])
                elif outcome["fee_total"] > 0:
                    ally_text += "\nNo se pudo aplicar el cargo automatico: {}.".format(
                        outcome["penalty_message"] or "saldo o vinculo no disponible"
                    )
                context.bot.send_message(
                    chat_id=ally_user["telegram_id"],
                    text=ally_text,
                )
    except Exception as e:
        logger.warning("No se pudo notificar cancelacion al aliado: %s", e)

    if had_courier:
        _notify_courier_order_cancelled(
            context,
            order,
            actor_label="administrador",
            compensation_amount=outcome["courier_compensation"],
            compensation_applied=outcome["penalty_applied"],
        )

    keyboard = [[InlineKeyboardButton(
        "Volver a pedidos activos",
        callback_data="admpedidos_list_ACTIVE_{}".format(admin_id),
    )]]
    query.edit_message_text(
        _build_order_cancel_result_text(order_id, "admin", outcome),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def order_courier_callback(update, context):
    """
    Maneja botones de ofertas y ciclo de vida de pedidos.
    Patterns:
    - ^order_(accept|reject|busy|pickup|delivered|delivered_confirm|delivered_cancel|release|release_reason|release_confirm|release_abort|cancel)_\\d+$
    - ^order_(cancel_confirm|cancel_abort|find_another_confirm|find_another_abort)_\\d+$
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

    if data.startswith("order_find_another_confirm_"):
        order_id = int(data.replace("order_find_another_confirm_", ""))
        return _handle_find_another_courier(update, context, order_id, confirm=True)
    if data.startswith("order_find_another_abort_"):
        order_id = int(data.replace("order_find_another_abort_", ""))
        return _handle_find_another_abort(update, context, order_id)
    if data.startswith("order_find_another_"):
        order_id = int(data.replace("order_find_another_", ""))
        return _handle_find_another_courier(update, context, order_id)
    if data.startswith("order_wait_courier_"):
        order_id = int(data.replace("order_wait_courier_", ""))
        return _handle_wait_courier(update, context, order_id)
    if data.startswith("order_call_courier_"):
        order_id = int(data.replace("order_call_courier_", ""))
        return _handle_call_courier(update, context, order_id)
    if data.startswith("order_fee_detail_"):
        order_id = int(data.replace("order_fee_detail_", ""))
        return _handle_offer_fee_detail(update, context, order_id)
    if data.startswith("admin_retry_creator_fees_"):
        order_id = int(data.replace("admin_retry_creator_fees_", ""))
        return _handle_admin_retry_creator_fees(update, context, order_id)
    if data.startswith("order_commission_confirm_"):
        order_id = int(data.replace("order_commission_confirm_", ""))
        return _handle_accept(update, context, order_id, commission_confirmed=True)
    if data.startswith("order_accept_"):
        order_id = int(data.replace("order_accept_", ""))
        return _handle_accept(update, context, order_id)
    if data.startswith("order_reject_"):
        order_id = int(data.replace("order_reject_", ""))
        return _handle_reject(update, context, order_id)
    if data.startswith("order_busy_"):
        order_id = int(data.replace("order_busy_", ""))
        return _handle_busy(update, context, order_id)
    # IMPORTANTE: order_pickup_pinissue_ debe ir antes que order_pickup_ (prefijo mas especifico primero)
    if data.startswith("order_pickup_pinissue_"):
        order_id = int(data.replace("order_pickup_pinissue_", ""))
        return _handle_order_pickup_pinissue(update, context, order_id)
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
        parts = data.replace("order_release_reason_", "", 1).split("_", 1)
        if len(parts) < 2:
            query.edit_message_text("No se pudo procesar la razon de liberacion.")
            return
        order_id = int(parts[0])
        reason_code = parts[1]
        return _handle_release_reason_selected(update, context, order_id, reason_code)
    if data.startswith("order_release_confirm_"):
        # order_release_confirm_{order_id}_{reason}
        parts = data.replace("order_release_confirm_", "", 1).split("_", 1)
        if len(parts) < 2:
            query.edit_message_text("No se pudo confirmar la liberacion.")
            return
        order_id = int(parts[0])
        reason_code = parts[1]
        return _handle_release(update, context, order_id, reason_code=reason_code)
    if data.startswith("order_release_"):
        # order_release_{order_id}
        parts = data.split("_")
        if len(parts) < 3:
            query.edit_message_text("No se pudo procesar la liberacion.")
            return
        order_id = int(parts[2])
        return _handle_release_reason_menu(update, context, order_id)
    if data.startswith("order_cancel_confirm_"):
        order_id = int(data.replace("order_cancel_confirm_", ""))
        return _handle_cancel_ally(update, context, order_id, confirm=True)
    if data.startswith("order_cancel_abort_"):
        order_id = int(data.replace("order_cancel_abort_", ""))
        return _handle_cancel_ally_abort(update, context, order_id)
    if data.startswith("order_cancel_"):
        order_id = int(data.replace("order_cancel_", ""))
        return _handle_cancel_ally(update, context, order_id)
    if data.startswith("order_repost_"):
        order_id = int(data.replace("order_repost_", ""))
        return _handle_repost_ally(update, context, order_id)
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
    if data.startswith("admin_pickup_confirm_"):
        parts = data.replace("admin_pickup_confirm_", "").split("_")
        if len(parts) == 2:
            return _handle_admin_pickup_pinissue_action(update, context, int(parts[0]), int(parts[1]), "confirm")
    if data.startswith("admin_pickup_release_"):
        parts = data.replace("admin_pickup_release_", "").split("_")
        if len(parts) == 2:
            return _handle_admin_pickup_pinissue_action(update, context, int(parts[0]), int(parts[1]), "release")
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
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        return

    _cancel_arrival_jobs(context, order_id)
    release_order_from_courier(order_id)

    cycle = context.bot_data.get("offer_cycles", {}).get(order_id, {})
    excluded = set(cycle.get("excluded_couriers", set()))
    excluded.add(courier_id)
    try:
        add_order_excluded_courier(order_id, courier_id)
    except Exception:
        pass

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

    repost_count = repost_order_to_couriers(order_id, context, excluded_courier_ids=excluded)
    if repost_count <= 0:
        try:
            ally = get_ally_by_id(order["ally_id"])
            if ally:
                au = get_user_by_id(ally["user_id"])
                if au:
                    context.bot.send_message(
                        chat_id=au["telegram_id"],
                        text=(
                            "No hay otro repartidor disponible para el pedido #{} por ahora. "
                            "El pedido sigue activo y se reintentara automaticamente."
                        ).format(order_id),
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
    mark_job_executed(context.job.name)
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
    mark_job_executed(context.job.name)
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
                        "al punto de recogida del pedido #{}.\n\n"
                        "Si eliges buscar otro repartidor, se intentara aplicar la penalidad de demora.\n\n"
                        "Que deseas hacer?"
                    ).format(courier_name, order_id),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
    except Exception as e:
        logger.warning("_arrival_warn_ally_job: %s", e)

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
    mark_job_executed(context.job.name)
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
    """Courier presiona 'Confirmar llegada'. Valida GPS <= 150m del pickup."""
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
                "Dirigete al lugar e intenta confirmar cuando estes mas cerca.\n\n"
                "Si ya estas en el lugar pero el pin de recogida esta mal ubicado, usa el boton de ayuda.".format(dist_km * 1000),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "Estoy aqui pero el pin de recogida esta mal",
                        callback_data="order_pickup_pinissue_{}".format(order_id)
                    )
                ]]),
            )
            return

    _cancel_arrival_jobs(context, order_id)
    set_courier_arrived(order_id)
    courier_name = courier["full_name"] or "Repartidor"

    # Pedido de admin (sin aliado): auto-confirmar directamente
    if not order["ally_id"]:
        query.edit_message_text("Pedido #{} - Llegada confirmada.".format(order_id))
        _notify_courier_pickup_approved(context, order)
        return

    upsert_order_pickup_confirmation(order_id, courier["id"], order["ally_id"], "PENDING")
    _notify_ally_courier_arrived(context, order, courier_name)
    context.job_queue.run_once(
        _pickup_autoconfirm_job,
        PICKUP_AUTOCONFIRM_SECONDS,
        context={"order_id": order_id},
        name="pickup_autoconfirm_{}".format(order_id),
    )
    query.edit_message_text(
        "Llegada confirmada. Avisamos al aliado — se confirmara automaticamente en 2 minutos si no hay novedad."
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


def _handle_offer_fee_detail(update, context, order_id):
    """Muestra el desglose financiero completo de una oferta con comision especial.
    No cuenta como aceptacion — el courier puede volver y aceptar o rechazar normalmente.
    """
    query = update.callback_query
    query.answer()
    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        query.answer("Este servicio ya no esta disponible.", show_alert=True)
        return

    special_commission = int(order["special_commission"] or 0) if "special_commission" in order.keys() else 0
    total_fee_val = int(order["total_fee"] or 0) if order.get("total_fee") else 0
    fee_cfg = get_fee_config()
    fee_std = fee_cfg["fee_service_total"]
    fee_admin = fee_cfg["fee_admin_share"]
    fee_plat = fee_cfg["fee_platform_share"]

    total_descuento = fee_std + special_commission
    ganancia_neta = total_fee_val - total_descuento if total_fee_val > 0 else None

    texto = (
        "Detalle financiero del servicio #{}\n\n"
        "Cobras al cliente: ${:,}\n\n"
        "Descuentos de tu saldo al entregar:\n"
        "  Fee estandar:       -${:,}\n"
        "    Admin (${:,}) + Plataforma (${:,})\n"
        "  Comision del admin: -${:,}\n"
        "  Total descuentos:   -${:,}\n"
        "{}"
        "\nEsta informacion es solo de consulta. Usa los botones de abajo para aceptar o rechazar."
    ).format(
        order_id,
        total_fee_val,
        fee_std, fee_admin, fee_plat,
        special_commission,
        total_descuento,
        "\nGanancia neta estimada: ${:,}\n".format(ganancia_neta) if ganancia_neta is not None else "",
    )

    # Mantener los mismos botones de accion
    reply_markup = _offer_reply_markup(order_id, special_commission=special_commission)
    query.edit_message_text(texto, reply_markup=reply_markup)


# ---------------------------------------------------------------------------

def _handle_accept(update, context, order_id, commission_confirmed=False):
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

    # Confirmacion explícita para comisiones altas
    special_commission = int(order["special_commission"] or 0) if order["special_commission"] else 0
    if special_commission >= COMMISSION_CONFIRM_THRESHOLD and not commission_confirmed:
        fee_cfg_ac = get_fee_config()
        fee_std_ac = fee_cfg_ac["fee_service_total"]
        total_descuento = fee_std_ac + special_commission
        ganancia_neta = int(order["total_fee"] or 0) - total_descuento
        confirm_text = (
            "Confirmacion requerida — comision alta\n\n"
            "Este pedido tiene una comision especial de ${:,}.\n\n"
            "Al entregar se descontara de tu saldo:\n"
            "  Fee estandar: -${:,}\n"
            "  Comision del admin: -${:,}\n"
            "  Total descuento: -${:,}\n\n"
            "Tarifa que cobras al cliente: ${:,}\n"
            "Ganancia neta: ${:,}\n\n"
            "Confirmas que aceptas estos terminos?"
        ).format(
            special_commission, fee_std_ac,
            special_commission,
            total_descuento,
            int(order["total_fee"] or 0), ganancia_neta,
        )
        query.edit_message_text(
            confirm_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Si, acepto el pedido", callback_data="order_commission_confirm_{}".format(order_id))],
                [InlineKeyboardButton("No, rechazar", callback_data="order_reject_{}".format(order_id))],
            ]),
        )
        query.answer()
        return

    query.answer()
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
    _schedule_persistent_job(
        context, _arrival_inactivity_job, ARRIVAL_INACTIVITY_SECONDS,
        "arr_inactive_{}".format(order_id), {"order_id": order_id},
    )
    _schedule_persistent_job(
        context, _arrival_warn_ally_job, ARRIVAL_WARN_SECONDS,
        "arr_warn_{}".format(order_id), {"order_id": order_id},
    )
    _schedule_persistent_job(
        context, _arrival_deadline_job, ARRIVAL_DEADLINE_SECONDS,
        "arr_deadline_{}".format(order_id), {"order_id": order_id},
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


def _handle_cancel_ally_abort(update, context, order_id):
    """Cancela la advertencia y deja el pedido activo."""
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("Cancelar pedido", callback_data="order_cancel_{}".format(order_id))]]
    query.edit_message_text(
        "Cancelacion anulada. El pedido #{} sigue activo.".format(order_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def _handle_find_another_abort(update, context, order_id):
    """Cancela la advertencia de quitar el pedido al courier."""
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("Buscar otro repartidor", callback_data="order_find_another_{}".format(order_id))]]
    query.edit_message_text(
        "Seguimos esperando al repartidor del pedido #{}.".format(order_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def _handle_find_another_courier(update, context, order_id, confirm=False):
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
    if not confirm:
        cfg = get_order_penalty_config()
        keyboard = [[
            InlineKeyboardButton(
                "Confirmar cambio",
                callback_data="order_find_another_confirm_{}".format(order_id),
            ),
            InlineKeyboardButton(
                "Seguir esperando",
                callback_data="order_find_another_abort_{}".format(order_id),
            ),
        ]]
        query.edit_message_text(
            (
                "Vas a quitarle el pedido #{} al repartidor actual.\n\n"
                "Si confirmas, se intentara aplicar una penalidad de ${:,} al repartidor.\n"
                "Distribucion:\n"
                "- Aliado: ${:,}\n"
                "- Plataforma: ${:,}\n\n"
                "Luego el pedido se re-ofrecera automaticamente a otros repartidores."
            ).format(
                order_id,
                cfg["courier_delay_penalty_total"],
                cfg["courier_delay_penalty_ally_share"],
                cfg["courier_delay_penalty_platform_share"],
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    outcome = penalize_courier_for_delay_and_release(
        order_id,
        reason="ALLY_DELAY_RELEASE_CONFIRMED",
    )
    if not outcome["ok"]:
        query.edit_message_text(outcome["message"])
        return

    _cancel_arrival_jobs(context, order_id)
    courier_id = outcome["courier_id"]
    excluded_ids = {courier_id} if courier_id else set()
    repost_count = repost_order_to_couriers(order_id, context, excluded_courier_ids=excluded_ids)

    if courier_id:
        try:
            courier = get_courier_by_id(courier_id)
            courier_user = get_user_by_id(courier["user_id"]) if courier else None
            if courier_user and courier_user["telegram_id"]:
                courier_text = (
                    "El pedido #{} te fue retirado por demora en la llegada al pickup."
                    .format(order_id)
                )
                if outcome["penalty_applied"]:
                    courier_text += (
                        "\nSe descontaron ${:,} de tu saldo: ${:,} para el aliado y ${:,} para la Plataforma."
                        .format(
                            outcome["penalty_total"],
                            outcome["ally_compensation"],
                            outcome["platform_share"],
                        )
                    )
                else:
                    courier_text += "\nNo se pudo aplicar la penalidad automatica: {}.".format(
                        outcome["penalty_message"] or "saldo o vinculo no disponible"
                    )
                context.bot.send_message(chat_id=courier_user["telegram_id"], text=courier_text)
        except Exception as e:
            logger.warning("No se pudo notificar penalidad de demora al courier: %s", e)

    result_lines = ["Pedido #{} liberado del repartidor actual.".format(order_id)]
    if outcome["penalty_applied"]:
        result_lines.append(
            "Se descontaron ${:,} al repartidor: ${:,} para tu saldo y ${:,} para la Plataforma.".format(
                outcome["penalty_total"],
                outcome["ally_compensation"],
                outcome["platform_share"],
            )
        )
    else:
        result_lines.append(
            "No se pudo aplicar la penalidad automatica: {}.".format(
                outcome["penalty_message"] or "saldo o vinculo no disponible"
            )
        )
    if repost_count > 0:
        result_lines.append("El pedido ya fue re-ofrecido a otros repartidores.")
    else:
        result_lines.append(
            "El pedido sigue activo; por ahora no hay otro repartidor disponible y se reintentara automaticamente."
        )
    query.edit_message_text("\n".join(result_lines))


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

    # Preservar couriers excluidos del ciclo anterior y agregar el que libero el pedido
    prev_cycle = context.bot_data.get("offer_cycles", {}).get(order_id, {})
    excluded = set(prev_cycle.get("excluded_couriers", set()))
    excluded.add(courier["id"])
    try:
        add_order_excluded_courier(order_id, courier["id"])
    except Exception:
        pass

    repost_count = repost_order_to_couriers(order_id, context, excluded_courier_ids=excluded)
    if repost_count <= 0:
        try:
            ally_row = get_ally_by_id(order["ally_id"])
            ally_user = get_user_by_id(ally_row["user_id"]) if ally_row else None
            if ally_user and ally_user["telegram_id"]:
                context.bot.send_message(
                    chat_id=ally_user["telegram_id"],
                    text=(
                        "Por ahora no hay otro repartidor disponible para el pedido #{}. "
                        "El pedido sigue activo y se reintentara automaticamente."
                    ).format(order_id),
                )
        except Exception:
            pass


def _handle_cancel_ally(update, context, order_id, confirm=False):
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

    if not confirm:
        keyboard = [[
            InlineKeyboardButton(
                "✅ Confirmar",
                callback_data="order_cancel_confirm_{}".format(order_id),
            ),
            InlineKeyboardButton(
                "❌ Volver",
                callback_data="order_cancel_abort_{}".format(order_id),
            ),
        ]]
        query.edit_message_text(
            _format_order_cancel_warning(order, actor_label="ally"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    had_courier = order["status"] == "ACCEPTED" and order["courier_id"]
    was_published = order["status"] == "PUBLISHED"
    current_offer = get_current_offer_for_order(order_id) if was_published else None

    outcome = cancel_order_by_actor(
        order_id,
        "ALLY",
    )
    if not outcome["ok"]:
        query.edit_message_text(outcome["message"])
        return

    _cancel_arrival_jobs(context, order_id)
    _cancel_delivery_reminder_jobs(context, order_id)
    _cancel_no_response_job(context, order_id)
    _cancel_order_expire_job(context, order_id)
    if current_offer:
        jobs = context.job_queue.get_jobs_by_name(
            "offer_timeout_{}_{}".format(order_id, current_offer["queue_id"])
        )
        for job in jobs:
            job.schedule_removal()

    delete_offer_queue(order_id)
    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    context.bot_data.get("offer_messages", {}).pop(order_id, None)

    query.edit_message_text(_build_order_cancel_result_text(order_id, "ally", outcome))

    if had_courier:
        _notify_courier_order_cancelled(
            context,
            order,
            actor_label="aliado",
            compensation_amount=outcome["courier_compensation"],
            compensation_applied=outcome["penalty_applied"],
        )


def _handle_cancel_ally_route_abort(update, context, route_id):
    """Cancela la advertencia y deja la ruta activa."""
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("Cancelar ruta", callback_data="ruta_cancelar_aliado_{}".format(route_id))]]
    query.edit_message_text(
        "Cancelacion anulada. La ruta #{} sigue activa.".format(route_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def _notify_courier_route_cancelled(context, route, compensation_amount=0, compensation_applied=False):
    """Notifica al repartidor que la ruta fue cancelada por el aliado."""
    try:
        courier_id = _row_value(route, "courier_id")
        if not courier_id:
            return
        courier = get_courier_by_id(courier_id)
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return

        text = "La ruta #{} fue cancelada por el aliado.".format(_row_value(route, "id"))
        if compensation_applied and compensation_amount:
            text += "\nRecibiste una compensacion de ${:,} en tu saldo por esta cancelacion.".format(
                int(compensation_amount)
            )
        elif compensation_amount:
            text += "\nNo fue posible acreditar la compensacion automatica de ${:,}.".format(int(compensation_amount))

        context.bot.send_message(chat_id=courier_user["telegram_id"], text=text)
    except Exception as e:
        logger.warning("No se pudo notificar cancelacion de ruta al courier: %s", e)


def _handle_cancel_ally_route(update, context, route_id, confirm=False):
    """Aliado cancela una ruta usando el mismo esquema de advertencia y cobro del pedido."""
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

    if not confirm:
        keyboard = [[
            InlineKeyboardButton(
                "✅ Confirmar",
                callback_data="ruta_cancelar_aliado_confirm_{}".format(route_id),
            ),
            InlineKeyboardButton(
                "❌ Volver",
                callback_data="ruta_cancelar_aliado_abort_{}".format(route_id),
            ),
        ]]
        query.edit_message_text(
            _format_route_cancel_warning(route, actor_label="ally"),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    had_courier = route["status"] == "ACCEPTED" and route["courier_id"]
    was_published = route["status"] == "PUBLISHED"
    current = get_current_route_offer(route_id) if was_published else None

    outcome = cancel_route_by_actor(route_id, "ALLY")
    if not outcome["ok"]:
        query.edit_message_text(outcome["message"])
        return

    _cancel_route_arrival_jobs(context, route_id)
    _cancel_route_no_response_job(context, route_id)
    if current:
        _cancel_route_offer_jobs(context, route_id, current["queue_id"])
        mark_route_offer_response(current["queue_id"], "CANCELLED")

    delete_route_offer_queue(route_id)
    context.bot_data.get("route_offer_cycles", {}).pop(route_id, None)
    context.bot_data.get("route_offer_messages", {}).pop(route_id, None)
    context.bot_data.get("route_accepted_pos", {}).pop(route_id, None)

    query.edit_message_text(_build_route_cancel_result_text(route_id, "ally", outcome))

    if had_courier:
        _notify_courier_route_cancelled(
            context,
            route,
            compensation_amount=outcome["courier_compensation"],
            compensation_applied=outcome["penalty_applied"],
        )


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
        keyboard.append([InlineKeyboardButton(
            "Estoy aqui pero el pin de recogida esta mal",
            callback_data="order_pickup_pinissue_{}".format(order_id)
        )])
        keyboard.append([InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order_id))])
        query.edit_message_text(
            "Aun no podemos confirmar tu llegada al pedido #{}.\n\n"
            "Acercate mas al punto de recogida y vuelve a presionar \"Confirmar llegada\" cuando estes alli.\n\n"
            "Si ya estas en el lugar pero el pin de recogida esta mal, usa el boton de ayuda."
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
    context.job_queue.run_once(
        _pickup_autoconfirm_job,
        PICKUP_AUTOCONFIRM_SECONDS,
        context={"order_id": order_id},
        name="pickup_autoconfirm_{}".format(order_id),
    )

    keyboard = [[InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order_id))]]
    query.edit_message_text(
        "Pedido #{} - Llegada confirmada.\n\n"
        "Avisamos al aliado — se confirmara automaticamente en 2 minutos si no hay novedad.".format(order_id),
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

    _cancel_pickup_autoconfirm_job(context, order_id)

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


def _apply_delivery_fees(context, order, courier_id):
    """Aplica todos los fees de un pedido entregado y retorna el resultado.

    Usado por _handle_delivered (entrega manual) y _do_deliver_order (resolucion admin).

    Retorna dict con:
      ally_admin_id, courier_admin_id,
      fee_ally_ok (bool), fee_courier_ok (bool),
      fee_cobrado_courier (int, total descontado del courier).
    """
    order_id = order["id"]
    ally_id = order["ally_id"]
    special_commission = int(order["special_commission"] or 0) if "special_commission" in order.keys() else 0
    creator_admin_id = order["creator_admin_id"] if "creator_admin_id" in order.keys() else None

    # Red cooperativa: fee del aliado → su propio admin; fee del courier → su propio admin.
    ally_admin_link = get_approved_admin_link_for_ally(ally_id) if ally_id else None
    ally_admin_id = ally_admin_link["admin_id"] if ally_admin_link else None

    courier_admin_id = order["courier_admin_id_snapshot"] if "courier_admin_id_snapshot" in order.keys() else None
    if courier_admin_id is None:
        courier_admin_link = get_approved_admin_link_for_courier(courier_id)
        courier_admin_id = courier_admin_link["admin_id"] if courier_admin_link else None

    fee_ally_ok = False
    fee_courier_ok = False
    fee_cobrado_courier = None

    if ally_admin_id and not check_ally_active_subscription(ally_id):
        ally_ok, ally_msg = apply_service_fee(
            target_type="ALLY", target_id=ally_id, admin_id=ally_admin_id,
            ref_type="ORDER", ref_id=order_id, total_fee=order["total_fee"],
        )
        if ally_ok:
            fee_ally_ok = True
        else:
            logger.warning("No se pudo cobrar fee al aliado: %s", ally_msg)
    elif ally_admin_id:
        fee_ally_ok = True  # suscripcion activa — sin cobro

    if courier_admin_id:
        courier_ok, courier_msg_raw = apply_service_fee(
            target_type="COURIER", target_id=courier_id, admin_id=courier_admin_id,
            ref_type="ORDER", ref_id=order_id,
        )
        fee_cobrado_courier = get_fee_config()["fee_service_total"] if courier_ok else 0

        if courier_ok and ally_id is None and special_commission > 0 and creator_admin_id:
            comm_ok, comm_msg = apply_special_order_commission(
                order_id, courier_id, special_commission, int(creator_admin_id)
            )
            if comm_ok:
                fee_cobrado_courier = (fee_cobrado_courier or 0) + special_commission
            else:
                logger.warning("No se pudo cobrar comision especial al courier %s: %s", courier_id, comm_msg)

        if ally_id is None and creator_admin_id:
            try:
                apply_special_order_creator_fees(
                    order_id, int(creator_admin_id),
                    int(order["total_fee"] or 0),
                    has_commission=(special_commission > 0),
                )
            except Exception as e:
                logger.warning("No se pudo cobrar fees de plataforma al admin creador %s: %s", creator_admin_id, e)
                _notify_admin_creator_fee_failed(
                    context, order_id, int(creator_admin_id),
                    int(order["total_fee"] or 0),
                    has_commission=(special_commission > 0),
                )

        if courier_ok:
            fee_courier_ok = True
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
                                        "y necesitas al menos ${:,} para seguir recibiendo pedidos.\n\n"
                                        "Solicita una recarga a tu administrador y vuelve a activarte.".format(
                                            new_balance, 300)
                                    ),
                                )
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("No se pudo verificar saldo post-fee del courier %s: %s", courier_id, e)
        else:
            logger.warning("No se pudo cobrar fee al courier: %s", courier_msg_raw)

    return {
        "ally_admin_id": ally_admin_id,
        "courier_admin_id": courier_admin_id,
        "fee_ally_ok": fee_ally_ok,
        "fee_courier_ok": fee_courier_ok,
        "fee_cobrado_courier": fee_cobrado_courier,
    }


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

    fees = _apply_delivery_fees(context, order, courier_id)
    ally_admin_id = fees["ally_admin_id"]
    courier_admin_id = fees["courier_admin_id"]
    fee_ally_ok = fees["fee_ally_ok"]
    fee_courier_ok = fees["fee_courier_ok"]
    fee_cobrado_courier = fees["fee_cobrado_courier"]
    creator_admin_id = order["creator_admin_id"] if "creator_admin_id" in order.keys() else None

    try:
        ally_fee_charged = 300 if fee_ally_ok else 0
        courier_fee_charged = (fee_cobrado_courier or 0) if fee_courier_ok else 0
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
        logger.warning("No se pudo registrar liquidacion contable de pedido %s: %s", order_id, e)

    set_order_status(order_id, "DELIVERED", "delivered_at")
    delete_offer_queue(order_id)

    durations = _get_order_durations(order, delivered_now=True)

    time_lines = []
    if "llegada_aliado" in durations:
        time_lines.append("  Llegada al pickup: {}".format(_format_duration(durations["llegada_aliado"])))
    if "espera_recogida" in durations:
        time_lines.append("  Espera en recogida: {}".format(_format_duration(durations["espera_recogida"])))
    if "entrega_cliente" in durations:
        time_lines.append("  Entrega al cliente: {}".format(_format_duration(durations["entrega_cliente"])))
    if "tiempo_total" in durations:
        time_lines.append("  Tiempo total: {}".format(_format_duration(durations["tiempo_total"])))

    time_block = ("\n\nTiempos del servicio:\n" + "\n".join(time_lines)) if time_lines else ""


    if fee_courier_ok:
        if fee_cobrado_courier is None:
            fee_cfg = get_fee_config()
            fee_cobrado_courier = fee_cfg["fee_service_total"]
        balance_courier = None
        if courier_admin_id:
            try:
                balance_courier = get_courier_link_balance(courier_id, courier_admin_id)
            except Exception:
                pass
        saldo_str = "\nSaldo actual: ${:,}".format(balance_courier) if balance_courier is not None else ""
        courier_msg = (
            "Pedido #{} entregado exitosamente.{}\n\n"
            "Se descontaron ${:,} de tu saldo por este servicio.{}"
        ).format(order_id, time_block, fee_cobrado_courier, saldo_str)
    else:
        courier_msg = "Pedido #{} entregado exitosamente.{}".format(order_id, time_block)

    query.edit_message_text(courier_msg)

    _notify_ally_delivered(context, order, durations)

    # Pedidos especiales de admin (ally_id=None): notificar al admin creador
    if creator_admin_id and not order["ally_id"]:
        _notify_admin_order_delivered(context, order, durations, int(creator_admin_id))


def _build_offer_text(
    order,
    courier_dist_km=None,
    pickup_city_override=None,
    pickup_barrio_override=None,
    dropoff_city_override=None,
    dropoff_barrio_override=None,
    courier_id=None,
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

    special_commission = int(order["special_commission"] or 0) if "special_commission" in order.keys() else 0
    fee_cfg_offer = get_fee_config()
    fee_std = fee_cfg_offer["fee_service_total"]
    total_fee_val = int(order["total_fee"] or 0) if order.get("total_fee") else 0
    if special_commission > 0:
        total_descuento = fee_std + special_commission
        ganancia_neta = total_fee_val - total_descuento
        text += (
            "\nDESCUENTOS AL ACEPTAR:"
            "\n  Fee estandar: -${:,} (admin ${:,} + plataforma ${:,})".format(
                fee_std, fee_cfg_offer["fee_admin_share"], fee_cfg_offer["fee_platform_share"])
            + "\n  Comision del admin: -${:,}".format(special_commission)
            + "\n  Total descuentos: -${:,}".format(total_descuento)
        )
        if total_fee_val > 0:
            text += "\n  Ganancia neta: ${:,}".format(ganancia_neta)
        text += "\n"
    else:
        text += (
            "\nFee de servicio: -${:,} (se descuenta de tu saldo al entregar)\n".format(fee_std)
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
        logger.warning("No se pudo notificar al aliado: %s", e)


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
                    "Confirmar ya",
                    callback_data="order_pickupconfirm_approve_{}".format(order_id),
                ),
                InlineKeyboardButton(
                    "Hay un problema",
                    callback_data="order_pickupconfirm_reject_{}".format(order_id),
                ),
            ]
        ])
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "El repartidor {} confirmo su llegada al punto de recogida (pedido #{}).\n\n"
                "Se confirmara automaticamente en 2 minutos si no hay novedad."
            ).format(courier_name, order_id),
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.warning("_notify_ally_courier_arrived: %s", e)


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
        logger.warning("No se pudo notificar confirmacion pendiente al courier: %s", e)


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
    _schedule_persistent_job(
        context, _delivery_reminder_job, DELIVERY_REMINDER_SECONDS,
        "delivery_reminder_{}".format(order_id), {"order_id": order_id},
    )
    _schedule_persistent_job(
        context, _delivery_admin_alert_job, DELIVERY_ADMIN_ALERT_SECONDS,
        "delivery_admin_alert_{}".format(order_id), {"order_id": order_id},
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
                "a menos de 150 metros del lugar de entrega."
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
        logger.warning("No se pudo notificar confirmacion de recogida al courier: %s", e)


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
        logger.warning("No se pudo notificar rechazo de recogida al courier: %s", e)


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
                time_lines.append("  Llegada al pickup: {}".format(_format_duration(durations["llegada_aliado"])))
            if "espera_recogida" in durations:
                time_lines.append("  Espera en recogida: {}".format(_format_duration(durations["espera_recogida"])))
            if "entrega_cliente" in durations:
                time_lines.append("  Tiempo de entrega: {}".format(_format_duration(durations["entrega_cliente"])))
            if "tiempo_total" in durations:
                time_lines.append("  Tiempo total: {}".format(_format_duration(durations["tiempo_total"])))
        time_block = ("\n\nTiempos del servicio:\n" + "\n".join(time_lines)) if time_lines else ""

        # Desglose de fee cobrado al aliado
        fee_block = ""
        try:
            ally_id = order["ally_id"]
            if ally_id and not check_ally_active_subscription(ally_id):
                ally_admin_link = get_approved_admin_link_for_ally(ally_id)
                if ally_admin_link:
                    fee_cfg = get_fee_config()
                    fee_servicio = fee_cfg["fee_service_total"]
                    commission_pct = fee_cfg.get("fee_ally_commission_pct", 0)
                    total_fee_val = int(order["total_fee"] or 0) if order.get("total_fee") else 0
                    commission_amt = round(total_fee_val * commission_pct / 100) if commission_pct and total_fee_val else 0
                    fee_total_cobrado = fee_servicio + commission_amt
                    ally_balance = get_ally_link_balance(ally_id, ally_admin_link["admin_id"])
                    if commission_amt > 0:
                        fee_block = (
                            "\n\nCobros aplicados:"
                            "\n  Servicio: -${:,}"
                            "\n  Comision ({}%): -${:,}"
                            "\n  Total: -${:,}"
                            "\nSaldo actual: ${:,}"
                        ).format(fee_servicio, commission_pct, commission_amt, fee_total_cobrado, ally_balance)
                    else:
                        fee_block = "\n\nCobro aplicado: -${:,}\nSaldo actual: ${:,}".format(fee_servicio, ally_balance)
        except Exception:
            pass

        parking_fee = int(order["parking_fee"] or 0) if "parking_fee" in order.keys() else 0
        total_fee_order = int(order["total_fee"] or 0) if order.get("total_fee") else 0
        parking_block = (
            "\n\nTarifa al repartidor: ${:,} (incluye ${:,} por parqueo dificil)".format(total_fee_order, parking_fee)
        ) if parking_fee > 0 else ""

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
                "Pedido #{} entregado exitosamente por {}.{}{}{}\n\n"
                "Como calificarias el servicio?\n"
                "1 = Muy malo  |  5 = Excelente"
            ).format(order_id, courier_name, time_block, fee_block, parking_block),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        logger.warning("No se pudo notificar entrega al aliado: %s", e)


def _notify_admin_order_delivered(context, order, durations, creator_admin_id):
    """
    Notifica al admin creador de un pedido especial (ally_id=None) que fue entregado.
    Equivalente a _notify_ally_delivered pero dirigido al admin creador.
    """
    try:
        admin = get_admin_by_id(creator_admin_id)
        if not admin:
            return
        admin_user = get_user_by_id(admin["user_id"])
        if not admin_user or not admin_user["telegram_id"]:
            return

        courier = get_courier_by_id(order["courier_id"]) if order["courier_id"] else None
        courier_name = (courier["full_name"] if courier else None) or "el repartidor"
        order_id = order["id"]

        time_lines = []
        if durations:
            if "llegada_aliado" in durations:
                time_lines.append("  Llegada al pickup: {}".format(_format_duration(durations["llegada_aliado"])))
            if "espera_recogida" in durations:
                time_lines.append("  Espera en recogida: {}".format(_format_duration(durations["espera_recogida"])))
            if "entrega_cliente" in durations:
                time_lines.append("  Tiempo de entrega: {}".format(_format_duration(durations["entrega_cliente"])))
            if "tiempo_total" in durations:
                time_lines.append("  Tiempo total: {}".format(_format_duration(durations["tiempo_total"])))
        time_block = ("\n\nTiempos del servicio:\n" + "\n".join(time_lines)) if time_lines else ""

        # Desglose de fees: lo que el admin recibio y lo que pago a plataforma
        fee_block = ""
        try:
            fee_cfg_n = get_fee_config()
            fee_std = fee_cfg_n["fee_service_total"]
            platform_share = fee_cfg_n["fee_platform_share"]
            tech_dev_pct = fee_cfg_n["fee_special_order_tech_dev_pct"]
            special_commission = int(order["special_commission"] or 0) if "special_commission" in order.keys() else 0
            total_fee_val = int(order["total_fee"] or 0) if order.get("total_fee") else 0

            lines = ["\n\nResumen financiero:"]
            # Cobros al courier
            lines.append("  Fee estandar al repartidor: -${:,}".format(fee_std))
            if special_commission > 0:
                lines.append("  Comision recibida del repartidor: +${:,}".format(special_commission))
            # Fees pagados por el admin a plataforma
            lines.append("  Fee plataforma pagado: -${:,}".format(platform_share))
            if special_commission > 0 and tech_dev_pct > 0 and total_fee_val > 0:
                tech_fee = round(total_fee_val * tech_dev_pct / 100)
                lines.append("  Desarrollo tecnologico ({}%): -${:,}".format(tech_dev_pct, tech_fee))
                ganancia_neta = special_commission - platform_share - tech_fee
                lines.append("  Ganancia neta de la comision: ${:,}".format(ganancia_neta))
            else:
                lines.append("  (Sin comision especial en este pedido)")
            fee_block = "\n".join(lines)

            # Saldo del courier post-cobro
            if order["courier_id"]:
                courier_admin_id_fee = _row_value(order, "courier_admin_id_snapshot")
                if not courier_admin_id_fee:
                    courier_admin_id_fee = get_approved_admin_id_for_courier(order["courier_id"])
                if courier_admin_id_fee:
                    courier_balance = get_courier_link_balance(order["courier_id"], courier_admin_id_fee)
                    fee_block += "\n\nSaldo repartidor: ${:,}".format(courier_balance)
        except Exception:
            pass

        parking_fee = int(order["parking_fee"] or 0) if "parking_fee" in order.keys() else 0
        total_fee_order = int(order["total_fee"] or 0) if order.get("total_fee") else 0
        parking_block = (
            "\n\nTarifa al repartidor: ${:,} (incluye ${:,} por parqueo dificil)".format(total_fee_order, parking_fee)
        ) if parking_fee > 0 else ""

        context.bot.send_message(
            chat_id=admin_user["telegram_id"],
            text=(
                "Pedido #{} entregado por {}.{}{}{}"
            ).format(order_id, courier_name, time_block, fee_block, parking_block),
        )
    except Exception as e:
        logger.warning("No se pudo notificar entrega de pedido especial al admin %s: %s", creator_admin_id, e)


def _notify_admin_creator_fee_failed(context, order_id, creator_admin_id, total_fee, has_commission):
    """
    Notifica al admin creador que no se pudieron cobrar los fees de plataforma
    por saldo insuficiente. Persiste el cobro pendiente en BD e incluye boton de reintento.
    """
    try:
        # Persistir en BD para sobrevivir reinicios
        create_pending_fee_collection(order_id, creator_admin_id, total_fee, has_commission)
    except Exception as e:
        logger.warning("No se pudo persistir pending_fee_collection orden %s: %s", order_id, e)
    try:
        from services import get_fee_config
        fee_cfg = get_fee_config()
        platform_share = fee_cfg["fee_platform_share"]
        tech_dev_pct = fee_cfg["fee_special_order_tech_dev_pct"]
        tech_dev_fee = round(total_fee * tech_dev_pct / 100) if has_commission else 0
        total_fees = platform_share + tech_dev_fee

        admin = get_admin_by_id(creator_admin_id)
        if not admin:
            return
        admin_user = get_user_by_id(admin["user_id"])
        if not admin_user or not admin_user["telegram_id"]:
            return

        lines = [
            "Atencion: no se pudieron cobrar los fees de plataforma del pedido #{}.".format(order_id),
            "",
            "Fees pendientes:",
            "  Fee plataforma: ${:,}".format(platform_share),
        ]
        if has_commission and tech_dev_fee > 0:
            lines.append("  Desarrollo tecnologico ({}%): ${:,}".format(tech_dev_pct, tech_dev_fee))
        lines += [
            "  Total: ${:,}".format(total_fees),
            "",
            "Tu saldo actual es insuficiente para cubrir estos fees.",
            "Recarga tu cuenta y usa el boton para reintentar el cobro.",
        ]

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "Reintentar cobro de fees",
                callback_data="admin_retry_creator_fees_{}".format(order_id),
            )
        ]])
        context.bot.send_message(
            chat_id=admin_user["telegram_id"],
            text="\n".join(lines),
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.warning("No se pudo notificar fee fallido al admin creador %s: %s", creator_admin_id, e)


def _handle_admin_retry_creator_fees(update, context, order_id):
    """
    Admin reintenta el cobro de fees de plataforma de un pedido especial entregado.
    """
    query = update.callback_query
    query.answer()

    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido #{} no encontrado.".format(order_id))
        return

    ally_id = order.get("ally_id") if hasattr(order, "get") else order["ally_id"]
    creator_admin_id = order.get("creator_admin_id") if hasattr(order, "get") else order["creator_admin_id"]
    special_commission = int(order["special_commission"] or 0) if order["special_commission"] else 0

    if ally_id is not None or not creator_admin_id:
        query.edit_message_text("Este pedido no es un pedido especial de admin.")
        return

    try:
        apply_special_order_creator_fees(
            order_id, int(creator_admin_id),
            int(order["total_fee"] or 0),
            has_commission=(special_commission > 0),
        )
        # Marcar como resuelto en BD
        try:
            resolve_pending_fee_collection(order_id)
        except Exception:
            pass
        query.edit_message_text(
            "Fees de plataforma del pedido #{} cobrados exitosamente.".format(order_id)
        )
    except Exception as e:
        query.edit_message_text(
            "No se pudo cobrar aun. Saldo insuficiente.\n\nError: {}\n\nIntenta de nuevo mas tarde.".format(str(e)),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "Reintentar cobro de fees",
                    callback_data="admin_retry_creator_fees_{}".format(order_id),
                )
            ]]),
        )


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
            logger.warning("No se pudo registrar calificacion orden %s: %s", order_id, e)

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
            logger.warning("No se pudo bloquear courier %s: %s", courier_id, e)

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


def _notify_courier_order_cancelled(context, order, actor_label="aliado", compensation_amount=0, compensation_applied=False):
    """Notifica al courier que el pedido fue cancelado y si hubo compensacion."""
    try:
        if not order["courier_id"]:
            return
        courier = get_courier_by_id(order["courier_id"])
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return
        text = "El pedido #{} fue cancelado por el {}.".format(order["id"], actor_label)
        if compensation_amount > 0:
            if compensation_applied:
                text += "\nRecibiste una compensacion de ${:,} en tu saldo por esta cancelacion.".format(compensation_amount)
            else:
                text += "\nSe intento acreditar una compensacion de ${:,}, pero no fue posible automaticamente.".format(compensation_amount)
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=text,
        )
    except Exception as e:
        logger.warning("No se pudo notificar cancelacion al courier: %s", e)


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
        logger.warning("No se pudo notificar liberacion al aliado: %s", e)


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
        logger.warning("No se pudo notificar liberacion al admin: %s", e)


# ===== FLUJO DE RUTAS MULTI-PARADA =====

ROUTE_OFFER_TIMEOUT_SECONDS = 30
ROUTE_OFFER_RETRY_SECONDS = 30
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

    # Barrio/ciudad de recogida (columnas opcionales — fallback a pickup_address)
    pickup_city = route.get("pickup_city") or ""
    pickup_barrio = route.get("pickup_barrio") or ""
    if not pickup_city and not pickup_barrio:
        pickup_area = route["pickup_address"] or "No disponible"
    elif pickup_barrio and pickup_city:
        pickup_area = "{}, {}".format(pickup_barrio, pickup_city)
    else:
        pickup_area = pickup_barrio or pickup_city

    text = "RUTA DISPONIBLE\n\nRuta #{}\nRecogida: {}\n\n".format(route["id"], pickup_area)
    text += "{} paradas:\n".format(len(destinations))

    paradas_parking = []
    for dest in destinations:
        barrio = dest["customer_barrio"] or ""
        city = dest["customer_city"] or ""
        if barrio and city:
            area = "{}, {}".format(barrio, city)
        elif barrio or city:
            area = barrio or city
        else:
            area = dest["customer_address"] or "Sin direccion"
        dest_parking = int(dest["parking_fee"] or 0) if "parking_fee" in dest.keys() else 0
        parking_flag = " [parqueo dificil]" if dest_parking > 0 else ""
        text += "  Parada {}: {}{}\n".format(dest["sequence"], area, parking_flag)
        if dest_parking > 0:
            paradas_parking.append((dest["sequence"], dest_parking))

    text += "\nDistancia total: {:.1f} km\n".format(total_km)

    if additional_incentive > 0:
        base_fee = max(0, total_fee - additional_incentive)
        text += "Pago base: ${:,}\n".format(base_fee)
        text += "Incentivo adicional: ${:,}\n".format(additional_incentive)
        text += "Pago total: ${:,}\n".format(total_fee)
    else:
        text += "Pago: ${:,}\n".format(total_fee)

    if paradas_parking:
        total_parking = sum(p for _, p in paradas_parking)
        text += (
            "\nATENCION: {} parada(s) de esta ruta tienen dificultad para parquear moto o bicicleta "
            "(zona restringida, riesgo de comparendo o sin lugar seguro). "
            "Se incluyen ${:,} en total para cubrir el parqueo o cualquier imprevisto. "
            "Comparendos o inmovilizaciones son tu responsabilidad.\n"
        ).format(len(paradas_parking), total_parking)

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
        route = get_route_by_id(route_id)
        if not route or route["status"] != "PUBLISHED":
            logger.warning("_try_restart_route_cycle: ruta %s sin cycle_info y fuera de PUBLISHED", route_id)
            return
        cycle_info = _build_recovered_route_cycle_info(route)
        context.bot_data.setdefault("route_offer_cycles", {})[route_id] = cycle_info
        logger.warning("_try_restart_route_cycle: ruta %s sin cycle_info; reconstruida desde BD", route_id)

    import time
    elapsed = time.time() - cycle_info["started_at"]
    logger.info("_try_restart_route_cycle: ruta %s elapsed=%.0fs", route_id, elapsed)

    if elapsed >= ROUTE_MAX_CYCLE_SECONDS:
        logger.info(
            "_try_restart_route_cycle: ruta %s elapsed=%.0fs supera max=%ss; se expirara",
            route_id,
            elapsed,
            ROUTE_MAX_CYCLE_SECONDS,
        )
        _expire_route(route_id, cycle_info, context)
        return

    admin_id = cycle_info.get("admin_id")
    ally_id = cycle_info.get("ally_id")
    excluded = cycle_info.get("excluded_couriers", set())
    route, courier_ids, eligible_count = _get_route_candidate_courier_ids(
        route_id,
        ally_id,
        admin_id,
        excluded_courier_ids=excluded,
    )
    if not route or route["status"] != "PUBLISHED":
        logger.warning("_try_restart_route_cycle: ruta %s ya no esta en PUBLISHED al recalcular", route_id)
        return

    logger.info(
        "_try_restart_route_cycle: ruta %s elapsed=%.0fs eligible=%s excluded=%s relanzables=%s",
        route_id,
        elapsed,
        eligible_count,
        len(excluded),
        len(courier_ids),
    )

    if not courier_ids:
        delete_route_offer_queue(route_id)
        logger.info(
            "_try_restart_route_cycle: ruta %s sigue activa sin couriers relanzables; reintentara en %ss",
            route_id,
            ROUTE_OFFER_RETRY_SECONDS,
        )
        _schedule_route_offer_retry_job(context, route_id)
        return

    delete_route_offer_queue(route_id)
    create_route_offer_queue(route_id, courier_ids)
    _cancel_route_offer_retry_job(context, route_id)
    _send_next_route_offer(route_id, context)


def _expire_route(route_id, cycle_info, context):
    """Nadie acepto la ruta en 7 minutos. Cancela la ruta."""
    logger.info("_expire_route: ruta %s en PUBLISHED sera cancelada sin cargo", route_id)
    _cancel_route_no_response_job(context, route_id)
    _cancel_route_offer_retry_job(context, route_id)
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
                        "la acepto en 7 minutos.\n"
                        "No se aplico ningun cargo."
                    ).format(route_id),
                )
    except Exception as e:
        logger.warning("No se pudo notificar expiracion de ruta al aliado: %s", e)


def _send_next_route_offer(route_id, context):
    """Envia la oferta de ruta al siguiente courier en la cola."""
    route = get_route_by_id(route_id)
    if not route or route["status"] != "PUBLISHED":
        return

    next_offer = get_next_pending_route_offer(route_id)
    if not next_offer:
        logger.info("_send_next_route_offer: ruta %s sin couriers pendientes; se intentara reiniciar el ciclo", route_id)
        _try_restart_route_cycle(route_id, context)
        return

    _cancel_route_offer_retry_job(context, route_id)
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
        logger.warning("No se pudo enviar oferta de ruta a courier %s: %s", next_offer["courier_id"], e)
        mark_route_offer_response(next_offer["queue_id"], "EXPIRED")
        _send_next_route_offer(route_id, context)
        return

    context.job_queue.run_once(
        _route_offer_timeout_job,
        ROUTE_OFFER_TIMEOUT_SECONDS,
        context={"route_id": route_id, "queue_id": next_offer["queue_id"]},
        name="route_offer_timeout_{}_{}".format(route_id, next_offer["queue_id"]),
    )


def publish_route_to_couriers(route_id, ally_id, context, admin_id_override=None, excluded_courier_ids=None):
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

    # Calcular distancia máxima pickup→parada para filtrar bicicletas >3 km
    _route_max_dist_km = None
    try:
        import math as _rmath
        _rdests = get_route_destinations(route_id)
        for _d in _rdests:
            _dlat = _d.get("dropoff_lat") if hasattr(_d, "get") else _d["dropoff_lat"]
            _dlng = _d.get("dropoff_lng") if hasattr(_d, "get") else _d["dropoff_lng"]
            if _dlat is not None and _dlng is not None and pickup_lat is not None and pickup_lng is not None:
                _rlat = _rmath.radians(_dlat - pickup_lat)
                _rlng = _rmath.radians(_dlng - pickup_lng)
                _a = (_rmath.sin(_rlat / 2) ** 2
                      + _rmath.cos(_rmath.radians(pickup_lat)) * _rmath.cos(_rmath.radians(_dlat))
                      * _rmath.sin(_rlng / 2) ** 2)
                _seg_km = 6371.0 * 2 * _rmath.atan2(_rmath.sqrt(_a), _rmath.sqrt(1 - _a))
                if _route_max_dist_km is None or _seg_km > _route_max_dist_km:
                    _route_max_dist_km = _seg_km
    except Exception:
        pass

    excluded_courier_ids = {int(cid) for cid in (excluded_courier_ids or []) if cid}

    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=False,
        cash_required_amount=0,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        order_distance_km=_route_max_dist_km,
    )

    # Filtrar couriers sin saldo suficiente para el fee de servicio ($300)
    # El sistema no ofrece el servicio a couriers que no puedan pagarlo al finalizar
    couriers_con_saldo = []
    for c in eligible:
        c_id = c["courier_id"]
        if c_id in excluded_courier_ids:
            continue
        c_admin_id = get_approved_admin_id_for_courier(c_id)
        if not c_admin_id:
            continue
        fee_ok, _ = check_service_fee_available("COURIER", c_id, c_admin_id)
        if fee_ok:
            couriers_con_saldo.append(c_id)

    courier_ids = couriers_con_saldo

    import time
    cycle_info = {
        "started_at": time.time(),
        "admin_id": admin_id,
        "ally_id": ally_id,
        "excluded_couriers": excluded_courier_ids,
    }

    if not courier_ids:
        logger.info(
            "publish_route_to_couriers: ruta %s sin couriers relanzables (eligible=%s excluded=%s)",
            route_id,
            len(eligible),
            len(excluded_courier_ids),
        )

    _activate_route_offer_dispatch(route_id, context, cycle_info, courier_ids)

    # Programar sugerencia de incentivo T+5 si nadie acepta la ruta
    _cancel_route_no_response_job(context, route_id)
    _schedule_persistent_job(
        context, _route_no_response_job, OFFER_NO_RESPONSE_SECONDS,
        "route_no_response_{}".format(route_id), {"route_id": route_id},
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

    stop_instructions = stop.get("instructions") or ""
    instr_line = "Instrucciones: {}\n".format(stop_instructions.strip()) if stop_instructions.strip() else ""
    stop_parking_fee = int(stop["parking_fee"] or 0) if "parking_fee" in stop.keys() else 0
    parking_aviso = (
        "\nRECUERDA: Esta parada tiene dificultad de parqueo (${:,} incluidos). "
        "Asegurate de dejar tu vehiculo en un lugar seguro y legal antes de entregar.".format(stop_parking_fee)
    ) if stop_parking_fee > 0 else ""

    context.bot.send_message(
        chat_id=chat_id,
        text=(
            "Parada {} de {}:\n\n"
            "Cliente: {}\n"
            "Telefono: {}\n"
            "Direccion: {}\n"
            "{}"
            "\nDirigete a la parada y confirma la entrega cuando termines."
            "{}"
        ).format(
            seq,
            total_stops,
            stop["customer_name"] or "Sin nombre",
            stop["customer_phone"] or "Sin telefono",
            stop["customer_address"] or "Sin direccion",
            instr_line,
            parking_aviso,
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
    _schedule_persistent_job(
        context, _route_arrival_inactivity_job, ARRIVAL_INACTIVITY_SECONDS,
        "ruta_arr_inactive_{}".format(route_id), {"route_id": route_id, "courier_id": courier_id},
    )
    _schedule_persistent_job(
        context, _route_arrival_warn_job, ARRIVAL_WARN_SECONDS,
        "ruta_arr_warn_{}".format(route_id), {"route_id": route_id, "courier_id": courier_id},
    )
    _schedule_persistent_job(
        context, _route_arrival_deadline_job, ARRIVAL_DEADLINE_SECONDS,
        "ruta_arr_deadline_{}".format(route_id), {"route_id": route_id, "courier_id": courier_id},
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


def _pickup_autoconfirm_job(context):
    """Job T+2: auto-confirma la llegada al pickup si el aliado no respondio."""
    data = context.job.context or {}
    order_id = data.get("order_id")
    if not order_id:
        return
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        return
    # Si ya fue respondida manualmente, no hacer nada
    confirmation = get_order_pickup_confirmation(order_id)
    if confirmation and confirmation["status"] != "PENDING":
        return
    # Marcar como aprobada en BD si existe el registro
    if confirmation:
        review_order_pickup_confirmation(order_id, "APPROVED", 0)
    # Notificar al courier
    _notify_courier_awaiting_pickup_confirm(context, order)
    # Notificar al aliado que se auto-confirmo
    try:
        ally = get_ally_by_id(order["ally_id"])
        if ally:
            ally_user = get_user_by_id(ally["user_id"])
            if ally_user and ally_user["telegram_id"]:
                context.bot.send_message(
                    chat_id=ally_user["telegram_id"],
                    text="Llegada del repartidor al pedido #{} confirmada automaticamente.".format(order_id),
                )
    except Exception as e:
        logger.warning("No se pudo notificar auto-confirmacion al aliado (pedido %s): %s", order_id, e)


def _route_pickup_autoconfirm_job(context):
    """Job T+2: auto-confirma la llegada al pickup de la ruta si el aliado no respondio."""
    data = context.job.context or {}
    route_id = data.get("route_id")
    if not route_id:
        return
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        return
    courier_id = _row_value(route, "courier_id")
    courier = get_courier_by_id(courier_id) if courier_id else None
    if not courier:
        return
    courier_user = get_user_by_id(courier["user_id"])
    if not courier_user or not courier_user["telegram_id"]:
        return
    # Replicar rama "approve" de _handle_route_pickupconfirm_by_ally
    destinations = get_route_destinations(route_id)
    pending = [d for d in destinations if d["status"] == "PENDING"]
    if not pending:
        try:
            context.bot.send_message(
                chat_id=courier_user["telegram_id"],
                text="Llegada confirmada automaticamente. No hay paradas pendientes en la ruta #{}.".format(route_id),
            )
        except Exception:
            pass
        return
    try:
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text="Llegada confirmada automaticamente. Aqui van los detalles de la primera parada:",
        )
        _send_route_stop_to_courier(context, courier_user["telegram_id"], route, pending[0])
    except Exception as e:
        logger.warning("No se pudo enviar parada al courier en auto-confirm ruta %s: %s", route_id, e)
    # Notificar al aliado
    try:
        ally_id = route["ally_id"]
        if ally_id:
            ally = get_ally_by_id(ally_id)
            if ally:
                ally_user = get_user_by_id(ally["user_id"])
                if ally_user and ally_user["telegram_id"]:
                    context.bot.send_message(
                        chat_id=ally_user["telegram_id"],
                        text="Llegada del repartidor a la ruta #{} confirmada automaticamente.".format(route_id),
                    )
    except Exception as e:
        logger.warning("No se pudo notificar auto-confirmacion al aliado (ruta %s): %s", route_id, e)


def _cancel_route_arrival_jobs(context, route_id):
    for suffix in ("inactive", "warn", "deadline"):
        _cancel_persistent_job(context, "ruta_arr_{}_{}".format(suffix, route_id))


def _handle_route_pickup_confirm(update, context, route_id):
    """Courier confirma llegada al punto de recogida. Valida GPS <= 150m."""
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
                "Dirigete al lugar e intenta confirmar cuando estes mas cerca.\n\n"
                "Si ya estas en el lugar pero el pin de recogida esta mal ubicado, usa el boton de ayuda.".format(dist_km * 1000),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "Estoy aqui pero el pin de recogida esta mal",
                        callback_data="ruta_pickup_pinissue_{}".format(route_id)
                    )
                ]]),
            )
            return

    _cancel_route_arrival_jobs(context, route_id)
    context.bot_data.get("route_accepted_pos", {}).pop(route_id, None)
    set_route_courier_arrived(route_id)

    courier_name = courier["full_name"] or "El repartidor"
    _notify_ally_route_courier_arrived(context, route, courier_name)
    context.job_queue.run_once(
        _route_pickup_autoconfirm_job,
        PICKUP_AUTOCONFIRM_SECONDS,
        context={"route_id": route_id},
        name="route_pickup_autoconfirm_{}".format(route_id),
    )
    query.edit_message_text(
        "Llegada confirmada. Avisamos al aliado — se confirmara automaticamente en 2 minutos si no hay novedad."
    )


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
                    "Confirmar ya",
                    callback_data="ruta_pickupconfirm_approve_{}".format(route_id),
                ),
                InlineKeyboardButton(
                    "Hay un problema",
                    callback_data="ruta_pickupconfirm_reject_{}".format(route_id),
                ),
            ]
        ])
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "{} confirmo su llegada al punto de recogida de la ruta #{}.\n\n"
                "Se confirmara automaticamente en 2 minutos si no hay novedad."
            ).format(courier_name, route_id),
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.warning("_notify_ally_route_courier_arrived: %s", e)


def _handle_route_pickupconfirm_by_ally(update, context, route_id, approve):
    """Aliado confirma o rechaza la llegada del courier al pickup de la ruta."""
    query = update.callback_query
    _cancel_route_pickup_autoconfirm_job(context, route_id)
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
    mark_job_executed(context.job.name)
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
    mark_job_executed(context.job.name)
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
                    keyboard = [
                        [InlineKeyboardButton(
                            "Buscar otro repartidor",
                            callback_data="ruta_find_another_{}".format(route_id),
                        )],
                        [InlineKeyboardButton(
                            "Seguir esperando",
                            callback_data="ruta_wait_courier_{}".format(route_id),
                        )],
                    ]
                    context.bot.send_message(
                        chat_id=au["telegram_id"],
                        text=(
                            "Han pasado 15 minutos y {} no ha confirmado su llegada "
                            "al punto de recogida de la ruta #{}.\n\n"
                            "Si eliges buscar otro repartidor, se intentara aplicar la penalidad de demora.\n\n"
                            "Que deseas hacer?".format(courier_name, route_id)
                        ),
                        reply_markup=InlineKeyboardMarkup(keyboard),
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
    mark_job_executed(context.job.name)
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
    repost_count = 0
    try:
        release_route_from_courier(route_id)
        excluded_ids = {int(courier_id)} if courier_id else None
        repost_count = repost_route_to_couriers(route_id, context, excluded_courier_ids=excluded_ids)
    except Exception as e:
        logger.warning("_release_route_by_timeout: %s", e)
    # Notificar al courier (equivalente a _release_order_by_timeout)
    try:
        c = get_courier_by_id(courier_id)
        if c:
            cu = get_user_by_id(c["user_id"])
            if cu:
                context.bot.send_message(
                    chat_id=cu["telegram_id"],
                    text="La ruta #{} fue liberada automaticamente por inactividad y sera ofrecida a otro repartidor.".format(route_id),
                )
    except Exception:
        pass
    # Notificar al aliado (equivalente a _release_order_by_timeout)
    try:
        route_for_ally = get_route_by_id(route_id)
        if route_for_ally:
            ally = get_ally_by_id(route_for_ally["ally_id"]) if route_for_ally["ally_id"] else None
            if ally:
                au = get_user_by_id(ally["user_id"])
                if au:
                    context.bot.send_message(
                        chat_id=au["telegram_id"],
                        text=(
                            "El repartidor fue liberado de la ruta #{} por inactividad. "
                            "{}"
                        ).format(
                            route_id,
                            (
                                "Buscando otro repartidor..."
                                if repost_count > 0
                                else "Por ahora no hay otro repartidor disponible, pero la ruta sigue activa y se reintentara automaticamente."
                            ),
                        ),
                    )
    except Exception:
        pass


def _handle_wait_route_courier(update, context, route_id):
    """Aliado decide seguir esperando al repartidor de la ruta."""
    query = update.callback_query
    query.edit_message_text("Seguimos esperando al repartidor de la ruta #{}.".format(route_id))


def _handle_find_another_route_abort(update, context, route_id):
    """Cancela la advertencia de quitar la ruta al courier."""
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("Buscar otro repartidor", callback_data="ruta_find_another_{}".format(route_id))]]
    query.edit_message_text(
        "Seguimos esperando al repartidor de la ruta #{}.".format(route_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def _handle_find_another_route_courier(update, context, route_id, confirm=False):
    """Aliado solicita buscar otro repartidor cuando el courier no llega a la ruta."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta ya no esta disponible para esta accion.")
        return
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    ally = get_ally_by_user_id(user["id"]) if user else None
    if not ally or ally["id"] != route["ally_id"]:
        query.answer("No tienes permiso para esta accion.")
        return

    if not confirm:
        cfg = get_order_penalty_config()
        keyboard = [[
            InlineKeyboardButton(
                "Confirmar cambio",
                callback_data="ruta_find_another_confirm_{}".format(route_id),
            ),
            InlineKeyboardButton(
                "Seguir esperando",
                callback_data="ruta_find_another_abort_{}".format(route_id),
            ),
        ]]
        query.edit_message_text(
            (
                "Vas a quitarle la ruta #{} al repartidor actual.\n\n"
                "Si confirmas, se intentara aplicar una penalidad de ${:,} al repartidor.\n"
                "Distribucion:\n"
                "- Aliado: ${:,}\n"
                "- Plataforma: ${:,}\n\n"
                "Luego la ruta se re-ofrecera automaticamente a otros repartidores."
            ).format(
                route_id,
                cfg["courier_delay_penalty_total"],
                cfg["courier_delay_penalty_ally_share"],
                cfg["courier_delay_penalty_platform_share"],
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    outcome = penalize_route_courier_for_delay_and_release(
        route_id,
        reason="ALLY_DELAY_RELEASE_CONFIRMED",
    )
    if not outcome["ok"]:
        query.edit_message_text(outcome["message"])
        return

    _cancel_route_arrival_jobs(context, route_id)
    context.bot_data.get("route_accepted_pos", {}).pop(route_id, None)
    courier_id = outcome["courier_id"]
    excluded_ids = {courier_id} if courier_id else set()
    repost_count = repost_route_to_couriers(route_id, context, excluded_courier_ids=excluded_ids)

    if courier_id:
        try:
            courier = get_courier_by_id(courier_id)
            courier_user = get_user_by_id(courier["user_id"]) if courier else None
            if courier_user and courier_user["telegram_id"]:
                courier_text = (
                    "La ruta #{} te fue retirada por demora en la llegada al pickup."
                    .format(route_id)
                )
                if outcome["penalty_applied"]:
                    courier_text += (
                        "\nSe descontaron ${:,} de tu saldo: ${:,} para el aliado y ${:,} para la Plataforma."
                        .format(
                            outcome["penalty_total"],
                            outcome["ally_compensation"],
                            outcome["platform_share"],
                        )
                    )
                else:
                    courier_text += "\nNo se pudo aplicar la penalidad automatica: {}.".format(
                        outcome["penalty_message"] or "motivo no disponible"
                    )
                context.bot.send_message(chat_id=courier_user["telegram_id"], text=courier_text)
        except Exception as e:
            logger.warning("No se pudo notificar penalidad de ruta al courier: %s", e)

    query.edit_message_text(
        (
            "La ruta #{} fue liberada del repartidor actual.\n"
            "{}\n"
            "Compensacion al aliado: ${:,}.\n"
            "Plataforma: ${:,}."
        ).format(
            route_id,
            "Penalidad aplicada." if outcome["penalty_applied"] else (
                outcome["penalty_message"] or "No se pudo aplicar la penalidad automaticamente."
            ),
            outcome["ally_compensation"] if outcome["penalty_applied"] else 0,
            outcome["platform_share"] if outcome["penalty_applied"] else 0,
        )
    )

    if repost_count <= 0:
        try:
            route_fresh = get_route_by_id(route_id)
            ally_row = get_ally_by_id(route_fresh["ally_id"]) if route_fresh and route_fresh["ally_id"] else None
            ally_user = get_user_by_id(ally_row["user_id"]) if ally_row else None
            if ally_user and ally_user["telegram_id"]:
                context.bot.send_message(
                    chat_id=ally_user["telegram_id"],
                    text=(
                        "Por ahora no hay otro repartidor disponible para la ruta #{}. "
                        "La ruta sigue activa y se reintentara automaticamente."
                    ).format(route_id),
                )
        except Exception:
            pass


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
                "Distancia actual: {:.0f} metros. Debes estar a menos de 150 metros.\n\n"
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
                logger.warning("No se pudo cobrar fee base al aliado en ruta %s: %s", route_id, ally_msg)
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
                logger.warning("No se pudo cobrar fee base al repartidor en ruta %s: %s", route_id, courier_msg)
        # Fee adicional por paradas extra: $200 c/u (split 50/50 admin/plataforma)
        ok, msg = liquidate_route_additional_stops_fee(route_id)
        if not ok and "no tiene additional_stops_fee" not in msg and "ya tenia liquidado" not in msg and "incidencias/cancelaciones" not in msg:
            logger.warning("No se pudo liquidar additional_stops_fee de ruta %s: %s", route_id, msg)
        route_dur = _get_route_durations(route, delivered_now=True)
        time_lines_c = []
        if "llegada_aliado" in route_dur:
            time_lines_c.append("  Llegada al pickup: {}".format(_format_duration(route_dur["llegada_aliado"])))
        if "tiempo_total" in route_dur:
            time_lines_c.append("  Tiempo total: {}".format(_format_duration(route_dur["tiempo_total"])))
        time_str = ("\n\nTiempos del servicio:\n" + "\n".join(time_lines_c)) if time_lines_c else ""
        context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Ruta #{} completada. Todas las paradas fueron entregadas.{}".format(route_id, time_str),
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
        logger.warning("No se pudo notificar aceptacion de ruta al aliado: %s", e)


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

        # Tiempos de la ruta
        try:
            route_dur = _get_route_durations(route, delivered_now=True)
            if route_dur:
                lines.append("")
                lines.append("Tiempos del servicio:")
                if "llegada_aliado" in route_dur:
                    lines.append("  Llegada al pickup: {}".format(_format_duration(route_dur["llegada_aliado"])))
                if "tiempo_total" in route_dur:
                    lines.append("  Tiempo total: {}".format(_format_duration(route_dur["tiempo_total"])))
        except Exception:
            pass

        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text="\n".join(lines),
        )
    except Exception as e:
        logger.warning("No se pudo notificar entrega de ruta al aliado: %s", e)


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

    if data.startswith("ruta_find_another_confirm_"):
        route_id = int(data.replace("ruta_find_another_confirm_", ""))
        return _handle_find_another_route_courier(update, context, route_id, confirm=True)

    if data.startswith("ruta_find_another_abort_"):
        route_id = int(data.replace("ruta_find_another_abort_", ""))
        return _handle_find_another_route_abort(update, context, route_id)

    if data.startswith("ruta_find_another_"):
        route_id = int(data.replace("ruta_find_another_", ""))
        return _handle_find_another_route_courier(update, context, route_id)

    if data.startswith("ruta_wait_courier_"):
        route_id = int(data.replace("ruta_wait_courier_", ""))
        return _handle_wait_route_courier(update, context, route_id)

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
        parts = data.replace("ruta_liberar_motivo_", "", 1).split("_", 1)
        if len(parts) < 2:
            query.edit_message_text("No se pudo procesar el motivo de liberacion.")
            return
        route_id = int(parts[0])
        reason_code = parts[1]
        return _handle_route_release_reason_selected(update, context, route_id, reason_code)

    if data.startswith("ruta_liberar_confirmar_"):
        # ruta_liberar_confirmar_{route_id}_{reason}
        parts = data.replace("ruta_liberar_confirmar_", "", 1).split("_", 1)
        if len(parts) < 2:
            query.edit_message_text("No se pudo confirmar la liberacion.")
            return
        route_id = int(parts[0])
        reason_code = parts[1]
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

    if data.startswith("ruta_cancelar_aliado_confirm_"):
        route_id = int(data.replace("ruta_cancelar_aliado_confirm_", ""))
        return _handle_cancel_ally_route(update, context, route_id, confirm=True)
    if data.startswith("ruta_cancelar_aliado_abort_"):
        route_id = int(data.replace("ruta_cancelar_aliado_abort_", ""))
        return _handle_cancel_ally_route_abort(update, context, route_id)
    if data.startswith("ruta_cancelar_aliado_"):
        route_id = int(data.replace("ruta_cancelar_aliado_", ""))
        return _handle_cancel_ally_route(update, context, route_id)
    if data.startswith("ruta_repost_"):
        route_id = int(data.replace("ruta_repost_", ""))
        return _handle_repost_ally_route(update, context, route_id)

    # pickup pin issue — ruta (punto de recogida)
    if data.startswith("ruta_pickup_pinissue_"):
        route_id = int(data.replace("ruta_pickup_pinissue_", ""))
        return _handle_route_pickup_pinissue(update, context, route_id)
    if data.startswith("admin_ruta_pickup_confirm_"):
        parts = data.replace("admin_ruta_pickup_confirm_", "").split("_")
        if len(parts) == 2:
            return _handle_admin_route_pickup_pinissue_action(update, context, int(parts[0]), int(parts[1]), "confirm")
    if data.startswith("admin_ruta_pickup_release_"):
        parts = data.replace("admin_ruta_pickup_release_", "").split("_")
        if len(parts) == 2:
            return _handle_admin_route_pickup_pinissue_action(update, context, int(parts[0]), int(parts[1]), "release")

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
            logger.warning("No se pudo cobrar fee al courier por liberacion de ruta %s: %s", route_id, fee_msg)

    delete_route_offer_queue(route_id)
    release_route_from_courier(route_id)

    fee_cfg_lib = get_fee_config()
    fee_lib = fee_cfg_lib["fee_service_total"]
    balance_lib = None
    if fee_ok and courier_admin_id_release:
        try:
            balance_lib = get_courier_link_balance(courier["id"], courier_admin_id_release)
        except Exception:
            pass
    saldo_lib = "\nSaldo actual: ${:,}".format(balance_lib) if balance_lib is not None else ""
    fee_line = "Se cobro la tarifa de servicio (${:,}) por la liberacion.".format(fee_lib) if fee_ok else "No se pudo cobrar la tarifa de servicio."
    query.edit_message_text(
        "Ruta #{} liberada.\nMotivo: {}\n\n{}{}\nSera ofrecida a otros repartidores.".format(
            route_id,
            reason_label,
            fee_line,
            saldo_lib,
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

    # Calcular distancia máxima pickup→parada para filtrar bicicletas >3 km
    _rrel_max_dist_km = None
    try:
        import math as _rrelmath
        _rreldests = get_route_destinations(route_id)
        for _d in _rreldests:
            _dlat = _d.get("dropoff_lat") if hasattr(_d, "get") else _d["dropoff_lat"]
            _dlng = _d.get("dropoff_lng") if hasattr(_d, "get") else _d["dropoff_lng"]
            if _dlat is not None and _dlng is not None and pickup_lat is not None and pickup_lng is not None:
                _rlat = _rrelmath.radians(_dlat - pickup_lat)
                _rlng = _rrelmath.radians(_dlng - pickup_lng)
                _a = (_rrelmath.sin(_rlat / 2) ** 2
                      + _rrelmath.cos(_rrelmath.radians(pickup_lat)) * _rrelmath.cos(_rrelmath.radians(_dlat))
                      * _rrelmath.sin(_rlng / 2) ** 2)
                _seg_km = 6371.0 * 2 * _rrelmath.atan2(_rrelmath.sqrt(_a), _rrelmath.sqrt(1 - _a))
                if _rrel_max_dist_km is None or _seg_km > _rrel_max_dist_km:
                    _rrel_max_dist_km = _seg_km
    except Exception:
        pass

    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=False,
        cash_required_amount=0,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        order_distance_km=_rrel_max_dist_km,
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
                "Distancia actual: {:.0f} metros. Debes estar a menos de 150 metros.\n\n"
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
        logger.warning("No se pudo notificar pin issue al admin (pedido %s): %s", order["id"], e)


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

    _apply_delivery_fees(context, order, courier_id)

    set_order_status(order_id, "DELIVERED", "delivered_at")
    delete_offer_queue(order_id)

    # Notificar al aliado (o admin creador en pedidos especiales) con tiempos
    try:
        fresh_order = get_order_by_id(order_id)
        if fresh_order:
            durations = _get_order_durations(fresh_order)
            if ally_id:
                _notify_ally_delivered(context, fresh_order, durations)
            else:
                creator_admin_id = fresh_order["creator_admin_id"] if "creator_admin_id" in fresh_order.keys() else None
                if creator_admin_id:
                    _notify_admin_order_delivered(context, fresh_order, durations, int(creator_admin_id))
    except Exception as e:
        logger.warning("No se pudo notificar entrega en _do_deliver_order pedido %s: %s", order_id, e)


def _notify_courier_support_resolved(context, courier_id, order_id, resolution):
    """Notifica al courier el resultado de la intervencion del admin."""
    try:
        courier = get_courier_by_id(courier_id)
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return

        fee_cfg = get_fee_config()
        fee = fee_cfg["fee_service_total"]
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        balance_actual = None
        if courier_admin_id:
            try:
                balance_actual = get_courier_link_balance(courier_id, courier_admin_id)
            except Exception:
                pass

        desglose = "\n\nComision cobrada: ${:,}\n".format(fee)
        if balance_actual is not None:
            desglose += "Saldo actual: ${:,}".format(balance_actual)

        # Calcular tiempos del servicio (solo para "fin" — pedido entregado)
        time_block = ""
        if resolution == "fin":
            try:
                fresh_order = get_order_by_id(order_id)
                if fresh_order:
                    durations = _get_order_durations(fresh_order)
                    time_lines = []
                    if "llegada_aliado" in durations:
                        time_lines.append("  Llegada al pickup: {}".format(_format_duration(durations["llegada_aliado"])))
                    if "espera_recogida" in durations:
                        time_lines.append("  Espera en recogida: {}".format(_format_duration(durations["espera_recogida"])))
                    if "entrega_cliente" in durations:
                        time_lines.append("  Entrega al cliente: {}".format(_format_duration(durations["entrega_cliente"])))
                    if "tiempo_total" in durations:
                        time_lines.append("  Tiempo total: {}".format(_format_duration(durations["tiempo_total"])))
                    if time_lines:
                        time_block = "\n\nTiempos del servicio:\n" + "\n".join(time_lines)
            except Exception as e:
                logger.warning("No se pudieron calcular tiempos para courier %s pedido %s: %s", courier_id, order_id, e)

        messages = {
            "fin": (
                "Tu administrador finalizo el servicio #{} en tu nombre. "
                "Los cargos normales fueron aplicados.{}{}".format(order_id, time_block, desglose)
            ),
            "cancel_courier": (
                "El pedido #{} fue cancelado por tu administrador. "
                "La falla fue atribuida a ti. Se cobro la comision.\n"
                "Debes devolver el producto al punto de recogida.{}".format(order_id, desglose)
            ),
            "cancel_ally": (
                "El pedido #{} fue cancelado por tu administrador. "
                "La falla fue atribuida al aliado. Se cobro comision a ambas partes.\n"
                "Debes devolver el producto al punto de recogida.{}".format(order_id, desglose)
            ),
        }
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=messages.get(resolution, "El pedido #{} fue resuelto por tu administrador.".format(order_id)),
        )
    except Exception as e:
        logger.warning("No se pudo notificar resolucion al courier %s: %s", courier_id, e)


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
        logger.warning("No se pudo notificar pin issue de ruta al admin: %s", e)


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
                        logger.warning("No se pudo cobrar fee al aliado (cancel_ally) en ruta %s: %s", route_id, pi_ally_msg)
        # Siempre fee al courier en cancel_courier; en cancel_ally también
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        if courier_admin_id:
            pi_courier_ok, pi_courier_msg = apply_service_fee(
                target_type="COURIER", target_id=courier_id,
                admin_id=courier_admin_id,
                ref_type="ROUTE", ref_id=route_id,
            )
            if not pi_courier_ok:
                logger.warning("No se pudo cobrar fee al repartidor (pin issue) en ruta %s: %s", route_id, pi_courier_msg)

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
                logger.warning("No se pudo cobrar fee base al aliado en ruta %s: %s", route_id, ally_msg_r)
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
                logger.warning("No se pudo cobrar fee base al repartidor en ruta %s: %s", route_id, courier_msg_r)
        # Fee adicional por paradas extra: $200 c/u (split 50/50 admin/plataforma)
        ok, msg = liquidate_route_additional_stops_fee(route_id)
        if not ok and "no tiene additional_stops_fee" not in msg and "ya tenia liquidado" not in msg and "incidencias/cancelaciones" not in msg:
            logger.warning("No se pudo liquidar additional_stops_fee de ruta %s: %s", route_id, msg)
        _notify_ally_route_delivered(context, route)
        # Notificar al courier: ruta completada + tiempos + devoluciones si aplica
        try:
            courier = get_courier_by_id(courier_id)
            courier_user = get_user_by_id(courier["user_id"]) if courier else None
            if courier_user and courier_user["telegram_id"]:
                route_dur = _get_route_durations(route, delivered_now=True)
                time_lines_c = []
                if "llegada_aliado" in route_dur:
                    time_lines_c.append("  Llegada al pickup: {}".format(_format_duration(route_dur["llegada_aliado"])))
                if "tiempo_total" in route_dur:
                    time_lines_c.append("  Tiempo total: {}".format(_format_duration(route_dur["tiempo_total"])))
                time_str = ("\n\nTiempos del servicio:\n" + "\n".join(time_lines_c)) if time_lines_c else ""
                cancelled = [s for s in get_route_destinations(route_id)
                             if str(s["status"] or "").startswith("CANCELLED")]
                if cancelled:
                    names = [s["customer_name"] or "Parada {}".format(s["sequence"]) for s in cancelled]
                    msg = (
                        "Ruta #{} completada.{}\n\n"
                        "Tienes {} parada(s) cancelada(s) que requieren devolucion:\n"
                        "{}\n\n"
                        "Dirgete al punto de recogida para devolver los productos."
                    ).format(route_id, time_str, len(cancelled), "\n".join("- " + n for n in names))
                else:
                    msg = "Ruta #{} completada.{}".format(route_id, time_str)
                context.bot.send_message(chat_id=courier_user["telegram_id"], text=msg)
        except Exception as e:
            logger.warning("No se pudo notificar completion al courier en ruta %s: %s", route_id, e)


def _notify_courier_route_stop_resolved(context, courier_id, route_id, seq, resolution):
    """Notifica al courier el resultado de la intervencion del admin en una parada."""
    try:
        courier = get_courier_by_id(courier_id)
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user["telegram_id"]:
            return

        fee_cfg = get_fee_config()
        fee = fee_cfg["fee_service_total"]
        courier_admin_id = get_approved_admin_id_for_courier(courier_id)
        balance_actual = None
        if courier_admin_id:
            try:
                balance_actual = get_courier_link_balance(courier_id, courier_admin_id)
            except Exception:
                pass

        desglose = "\n\nComision cobrada: ${:,}\n".format(fee)
        if balance_actual is not None:
            desglose += "Saldo actual: ${:,}".format(balance_actual)

        messages = {
            "fin": "Tu administrador finalizo la parada {} de la ruta #{}.{}".format(seq, route_id, desglose),
            "cancel_courier": (
                "La parada {} de la ruta #{} fue cancelada. Falla atribuida a ti. "
                "Continua con las demas paradas.{}".format(seq, route_id, desglose)
            ),
            "cancel_ally": (
                "La parada {} de la ruta #{} fue cancelada. Falla atribuida al aliado. "
                "Continua con las demas paradas.{}".format(seq, route_id, desglose)
            ),
        }
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=messages.get(resolution, "Parada {} resuelta por tu administrador.".format(seq)),
        )
    except Exception as e:
        logger.warning("No se pudo notificar resolucion de parada al courier %s: %s", courier_id, e)


# ---------------------------------------------------------------------------
# Flujo pin mal ubicado — punto de RECOGIDA (pedidos normales y admin)
# ---------------------------------------------------------------------------

def _handle_order_pickup_pinissue(update, context, order_id):
    """Courier reporta que el pin de recogida esta mal (estado ACCEPTED). Notifica al admin."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        query.edit_message_text("Este pedido no esta disponible para esta accion.")
        return
    courier = get_courier_by_telegram_id(update.effective_user.id)
    if not courier or courier["id"] != order["courier_id"]:
        query.edit_message_text("No tienes permiso para esta accion.")
        return

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
        "Solicitud enviada. Tu administrador fue notificado y podra confirmar tu llegada o liberar el pedido.\n"
        "Permanece en el lugar hasta recibir respuesta."
    )
    _notify_admin_pickup_pinissue(context, order, courier, admin_id, support_id)


def _notify_admin_pickup_pinissue(context, order, courier, admin_id, support_id):
    """Envia al admin la alerta de pin de recogida mal ubicado con opciones de accion."""
    try:
        admin = get_admin_by_id(admin_id)
        if not admin:
            return
        admin_user = get_user_by_id(admin["user_id"])
        if not admin_user or not admin_user["telegram_id"]:
            return

        pickup_lat, pickup_lng = _get_pickup_coords(order)
        courier_lat = _row_value(courier, "live_lat")
        courier_lng = _row_value(courier, "live_lng")

        maps_pickup = ""
        if pickup_lat is not None and pickup_lng is not None:
            maps_pickup = "https://maps.google.com/?q={},{}".format(pickup_lat, pickup_lng)
        maps_courier = ""
        if courier_lat is not None and courier_lng is not None:
            maps_courier = "https://maps.google.com/?q={},{}".format(courier_lat, courier_lng)

        courier_user = get_user_by_id(courier["user_id"])
        courier_tg = ""
        if courier_user and courier_user["telegram_id"]:
            courier_tg = "tg://user?id={}".format(courier_user["telegram_id"])

        lines = [
            "AYUDA - Pin de recogida - Pedido #{}".format(order["id"]),
            "",
            "Repartidor: {}".format(_row_value(courier, "full_name") or "N/D"),
            "Telefono: {}".format(_row_value(courier, "phone") or "N/D"),
            "Punto de recogida: {}".format(order["pickup_address"] or "N/D"),
        ]
        if maps_pickup:
            lines.append("Pin de recogida: {}".format(maps_pickup))
        if maps_courier:
            lines.append("Ubicacion actual del repartidor: {}".format(maps_courier))

        keyboard = [
            [InlineKeyboardButton(
                "Confirmar llegada del repartidor",
                callback_data="admin_pickup_confirm_{}_{}".format(order["id"], support_id)
            )],
            [InlineKeyboardButton(
                "Liberar pedido",
                callback_data="admin_pickup_release_{}_{}".format(order["id"], support_id)
            )],
        ]
        if courier_tg:
            keyboard.append([InlineKeyboardButton("Chatear con el repartidor", url=courier_tg)])

        context.bot.send_message(
            chat_id=admin_user["telegram_id"],
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        logger.warning("No se pudo notificar pickup pin issue al admin (pedido %s): %s", order["id"], e)


def _handle_admin_pickup_pinissue_action(update, context, order_id, support_id, action):
    """Admin confirma llegada del courier o libera el pedido (pin de recogida mal ubicado)."""
    query = update.callback_query
    order = get_order_by_id(order_id)
    if not order or order["status"] != "ACCEPTED":
        query.edit_message_text("Este pedido ya no esta activo.")
        return

    support = get_pending_support_request(order_id=order_id)
    if not support or support["id"] != support_id:
        query.edit_message_text("Esta solicitud ya fue resuelta.")
        return

    admin = get_admin_by_telegram_id(update.effective_user.id)
    if not admin or admin["id"] != support["admin_id"]:
        query.edit_message_text("No tienes permiso para resolver esta solicitud.")
        return

    resolution = "CONFIRMED_ARRIVAL" if action == "confirm" else "RELEASED"
    ok = resolve_support_request(support["id"], resolution, admin["id"])
    if not ok:
        query.edit_message_text("Esta solicitud ya fue resuelta.")
        return

    courier_id = support["courier_id"]
    courier = get_courier_by_id(courier_id)

    if action == "confirm":
        _cancel_arrival_jobs(context, order_id)
        set_courier_arrived(order_id)
        query.edit_message_text("Llegada confirmada para pedido #{}.".format(order_id))
        if not order["ally_id"]:
            _notify_courier_pickup_approved(context, order)
        else:
            courier_name = courier["full_name"] if courier else "El repartidor"
            upsert_order_pickup_confirmation(order_id, courier_id, order["ally_id"], "PENDING")
            _notify_ally_courier_arrived(context, order, courier_name)
            context.job_queue.run_once(
                _pickup_autoconfirm_job,
                PICKUP_AUTOCONFIRM_SECONDS,
                context={"order_id": order_id},
                name="pickup_autoconfirm_{}".format(order_id),
            )
        try:
            if courier:
                cu = get_user_by_id(courier["user_id"])
                if cu and cu["telegram_id"]:
                    context.bot.send_message(
                        chat_id=cu["telegram_id"],
                        text="Tu administrador confirmo tu llegada al punto de recogida del pedido #{}.".format(order_id)
                    )
        except Exception:
            pass
    else:
        query.edit_message_text("Pedido #{} liberado para re-oferta.".format(order_id))
        _release_order_by_timeout(order_id, courier_id, context,
                                   reason="pin de recogida incorrecto — liberado por admin")


# ---------------------------------------------------------------------------
# Flujo pin mal ubicado — punto de RECOGIDA (rutas)
# ---------------------------------------------------------------------------

def _handle_route_pickup_pinissue(update, context, route_id):
    """Courier reporta que el pin de recogida de la ruta esta mal (estado ACCEPTED). Notifica al admin."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta ya no esta activa.")
        return
    courier = get_courier_by_telegram_id(update.effective_user.id)
    if not courier or courier["id"] != route["courier_id"]:
        query.edit_message_text("No tienes permiso para esta accion.")
        return

    # route_seq=0 representa el pickup (secuencias de paradas empiezan en 1)
    existing = get_pending_support_request(route_id=route_id, route_seq=0)
    if existing:
        query.edit_message_text(
            "Ya enviaste una solicitud de ayuda para esta ruta.\n"
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
        route_id=route_id,
        route_seq=0,
    )
    query.edit_message_text(
        "Solicitud enviada. Tu administrador fue notificado y podra confirmar tu llegada o liberar la ruta.\n"
        "Permanece en el lugar hasta recibir respuesta."
    )
    _notify_admin_route_pickup_pinissue(context, route, courier, admin_id, support_id)


def _notify_admin_route_pickup_pinissue(context, route, courier, admin_id, support_id):
    """Envia al admin la alerta de pin de recogida de ruta mal ubicado con opciones de accion."""
    try:
        admin = get_admin_by_id(admin_id)
        if not admin:
            return
        admin_user = get_user_by_id(admin["user_id"])
        if not admin_user or not admin_user["telegram_id"]:
            return

        pickup_lat = route["pickup_lat"]
        pickup_lng = route["pickup_lng"]
        courier_lat = _row_value(courier, "live_lat")
        courier_lng = _row_value(courier, "live_lng")

        maps_pickup = ""
        if pickup_lat is not None and pickup_lng is not None:
            maps_pickup = "https://maps.google.com/?q={},{}".format(pickup_lat, pickup_lng)
        maps_courier = ""
        if courier_lat is not None and courier_lng is not None:
            maps_courier = "https://maps.google.com/?q={},{}".format(courier_lat, courier_lng)

        courier_user = get_user_by_id(courier["user_id"])
        courier_tg = ""
        if courier_user and courier_user["telegram_id"]:
            courier_tg = "tg://user?id={}".format(courier_user["telegram_id"])

        lines = [
            "AYUDA - Pin de recogida - Ruta #{}".format(route["id"]),
            "",
            "Repartidor: {}".format(_row_value(courier, "full_name") or "N/D"),
            "Telefono: {}".format(_row_value(courier, "phone") or "N/D"),
            "Punto de recogida: {}".format(route["pickup_address"] or "N/D"),
        ]
        if maps_pickup:
            lines.append("Pin de recogida: {}".format(maps_pickup))
        if maps_courier:
            lines.append("Ubicacion actual del repartidor: {}".format(maps_courier))

        keyboard = [
            [InlineKeyboardButton(
                "Confirmar llegada del repartidor",
                callback_data="admin_ruta_pickup_confirm_{}_{}".format(route["id"], support_id)
            )],
            [InlineKeyboardButton(
                "Liberar ruta",
                callback_data="admin_ruta_pickup_release_{}_{}".format(route["id"], support_id)
            )],
        ]
        if courier_tg:
            keyboard.append([InlineKeyboardButton("Chatear con el repartidor", url=courier_tg)])

        context.bot.send_message(
            chat_id=admin_user["telegram_id"],
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        logger.warning("No se pudo notificar pickup pin issue al admin (ruta %s): %s", route["id"], e)


def _handle_admin_route_pickup_pinissue_action(update, context, route_id, support_id, action):
    """Admin confirma llegada del courier o libera la ruta (pin de recogida mal ubicado)."""
    query = update.callback_query
    route = get_route_by_id(route_id)
    if not route or route["status"] != "ACCEPTED":
        query.edit_message_text("Esta ruta ya no esta activa.")
        return

    support = get_pending_support_request(route_id=route_id, route_seq=0)
    if not support or support["id"] != support_id:
        query.edit_message_text("Esta solicitud ya fue resuelta.")
        return

    admin = get_admin_by_telegram_id(update.effective_user.id)
    if not admin or admin["id"] != support["admin_id"]:
        query.edit_message_text("No tienes permiso para resolver esta solicitud.")
        return

    resolution = "CONFIRMED_ARRIVAL" if action == "confirm" else "RELEASED"
    ok = resolve_support_request(support["id"], resolution, admin["id"])
    if not ok:
        query.edit_message_text("Esta solicitud ya fue resuelta.")
        return

    courier_id = support["courier_id"]
    courier = get_courier_by_id(courier_id)

    if action == "confirm":
        _cancel_route_arrival_jobs(context, route_id)
        context.bot_data.get("route_accepted_pos", {}).pop(route_id, None)
        query.edit_message_text("Llegada confirmada para ruta #{}.".format(route_id))
        courier_name = courier["full_name"] if courier else "El repartidor"
        _notify_ally_route_courier_arrived(context, route, courier_name)
        context.job_queue.run_once(
            _route_pickup_autoconfirm_job,
            PICKUP_AUTOCONFIRM_SECONDS,
            context={"route_id": route_id},
            name="route_pickup_autoconfirm_{}".format(route_id),
        )
        try:
            if courier:
                cu = get_user_by_id(courier["user_id"])
                if cu and cu["telegram_id"]:
                    context.bot.send_message(
                        chat_id=cu["telegram_id"],
                        text="Tu administrador confirmo tu llegada al punto de recogida de la ruta #{}.".format(route_id)
                    )
        except Exception:
            pass
    else:
        query.edit_message_text("Ruta #{} liberada para re-oferta.".format(route_id))
        _release_route_by_timeout(route_id, courier_id, context,
                                   reason="pin de recogida incorrecto — liberado por admin")


# ---------------------------------------------------------------------------
# Job recovery after restart
# ---------------------------------------------------------------------------

JOB_REGISTRY = {
    "_order_expire_job": _order_expire_job,
    "_offer_no_response_job": _offer_no_response_job,
    "_offer_retry_job": _offer_retry_job,
    "_arrival_inactivity_job": _arrival_inactivity_job,
    "_arrival_warn_ally_job": _arrival_warn_ally_job,
    "_arrival_deadline_job": _arrival_deadline_job,
    "_delivery_reminder_job": _delivery_reminder_job,
    "_delivery_admin_alert_job": _delivery_admin_alert_job,
    "_route_no_response_job": _route_no_response_job,
    "_route_offer_retry_job": _route_offer_retry_job,
    "_route_arrival_inactivity_job": _route_arrival_inactivity_job,
    "_route_arrival_warn_job": _route_arrival_warn_job,
    "_route_arrival_deadline_job": _route_arrival_deadline_job,
}


def recover_scheduled_jobs(job_queue):
    """Al arrancar, reprograma en memoria los jobs persistidos que no fueron ejecutados.

    Llama a esta funcion justo despues de crear el Updater y antes de start_polling().
    Los jobs cuyo fire_at ya paso se disparan inmediatamente (when=0).
    """
    from datetime import datetime, timezone
    try:
        pending = get_pending_scheduled_jobs()
    except Exception as e:
        logger.warning("recover_scheduled_jobs: no se pudo leer scheduled_jobs: %s", e)
        return

    recovered = 0
    skipped = 0
    for row in pending:
        job_name = row["job_name"]
        callback_name = row["callback_name"]
        fire_at_str = row["fire_at"]
        job_data_json = row["job_data"] or "{}"

        callback = JOB_REGISTRY.get(callback_name)
        if callback is None:
            logger.warning("recover_scheduled_jobs: callback desconocido %s (job %s) - omitido", callback_name, job_name)
            skipped += 1
            continue

        try:
            job_data = json.loads(job_data_json)
        except Exception:
            job_data = {}

        try:
            fire_at = datetime.fromisoformat(fire_at_str)
        except Exception:
            fire_at = datetime.now(timezone.utc).replace(tzinfo=None)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        delay = max(0, (fire_at - now).total_seconds())

        try:
            job_queue.run_once(callback, when=delay, context=job_data, name=job_name)
            recovered += 1
            logger.info("recover_scheduled_jobs: reprogramado %s en %.0fs", job_name, delay)
        except Exception as e:
            logger.warning("recover_scheduled_jobs: error al reprogramar %s: %s", job_name, e)
            skipped += 1

    logger.info("recover_scheduled_jobs: %d jobs recuperados, %d omitidos", recovered, skipped)


def _restore_cycle_started_at(record):
    import time

    started_at = time.time()
    started_raw = _row_value(record, "published_at") or _row_value(record, "created_at")
    started_dt = _to_naive_utc(_parse_dt(started_raw))
    if started_dt is None:
        return started_at

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        elapsed = max(0, (now - started_dt).total_seconds())
    except Exception:
        return started_at
    return started_at - elapsed


def _remaining_timeout_seconds(offered_at_raw, timeout_seconds):
    offered_at = _to_naive_utc(_parse_dt(offered_at_raw))
    if offered_at is None:
        return timeout_seconds

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        elapsed = max(0, (now - offered_at).total_seconds())
    except Exception:
        return timeout_seconds
    return max(0, timeout_seconds - elapsed)


def _build_recovered_order_cycle_info(order):
    cycle_info = _build_cycle_info_for_expire(order)
    cycle_info.update(
        {
            "started_at": _restore_cycle_started_at(order),
            "pickup_lat": _row_value(order, "pickup_lat"),
            "pickup_lng": _row_value(order, "pickup_lng"),
            "pickup_city": _row_value(order, "pickup_city"),
            "pickup_barrio": _row_value(order, "pickup_barrio"),
            "dropoff_city": _row_value(order, "customer_city"),
            "dropoff_barrio": _row_value(order, "customer_barrio"),
            "requires_cash": bool(_row_value(order, "requires_cash", False)),
            "cash_amount": int(_row_value(order, "cash_required_amount", 0) or 0),
            "excluded_couriers": get_order_excluded_couriers(_row_value(order, "id")),
            "order_distance_km": _row_value(order, "distance_km"),
        }
    )
    return cycle_info


def _build_recovered_route_cycle_info(route):
    ally_id = _row_value(route, "ally_id")
    admin_id = _row_value(route, "ally_admin_id_snapshot")
    if admin_id is None and ally_id is not None:
        try:
            admin_link = get_approved_admin_link_for_ally(int(ally_id))
            admin_id = admin_link["admin_id"] if admin_link else None
        except Exception:
            admin_id = None

    return {
        "started_at": _restore_cycle_started_at(route),
        "admin_id": admin_id,
        "ally_id": ally_id,
        "excluded_couriers": set(),
    }


def recover_active_offer_dispatches(updater):
    """Rehidrata ofertas activas tras reinicio para que pedidos y rutas no queden huerfanos."""
    from types import SimpleNamespace

    runtime = SimpleNamespace(
        bot=updater.bot,
        job_queue=updater.job_queue,
        bot_data=updater.dispatcher.bot_data,
    )

    recovered_orders = 0
    rescheduled_order_timeouts = 0
    for order in get_all_orders(status_filter="ACTIVE", limit=500):
        if _row_value(order, "status") != "PUBLISHED":
            continue

        order_id = int(_row_value(order, "id"))
        runtime.bot_data.setdefault("offer_cycles", {}).setdefault(
            order_id, _build_recovered_order_cycle_info(order)
        )

        current = get_current_offer_for_order(order_id)
        if current:
            job_name = "offer_timeout_{}_{}".format(order_id, current["queue_id"])
            for job in runtime.job_queue.get_jobs_by_name(job_name):
                job.schedule_removal()
            runtime.job_queue.run_once(
                _offer_timeout_job,
                when=_remaining_timeout_seconds(current.get("offered_at"), OFFER_TIMEOUT_SECONDS),
                context={"order_id": order_id, "queue_id": current["queue_id"]},
                name=job_name,
            )
            rescheduled_order_timeouts += 1
            continue

        _send_next_offer(order_id, runtime)
        recovered_orders += 1

    recovered_routes = 0
    rescheduled_route_timeouts = 0
    for route in get_routes_by_status("PUBLISHED", limit=500):
        route_id = int(_row_value(route, "id"))
        runtime.bot_data.setdefault("route_offer_cycles", {}).setdefault(
            route_id, _build_recovered_route_cycle_info(route)
        )

        current = get_current_route_offer(route_id)
        if current:
            job_name = "route_offer_timeout_{}_{}".format(route_id, current["queue_id"])
            for job in runtime.job_queue.get_jobs_by_name(job_name):
                job.schedule_removal()
            runtime.job_queue.run_once(
                _route_offer_timeout_job,
                when=_remaining_timeout_seconds(current.get("offered_at"), ROUTE_OFFER_TIMEOUT_SECONDS),
                context={"route_id": route_id, "queue_id": current["queue_id"]},
                name=job_name,
            )
            rescheduled_route_timeouts += 1
            continue

        _send_next_route_offer(route_id, runtime)
        recovered_routes += 1

    logger.info(
        "recover_active_offer_dispatches: pedidos_reactivados=%s, timeouts_pedidos=%s, rutas_reactivadas=%s, timeouts_rutas=%s",
        recovered_orders,
        rescheduled_order_timeouts,
        recovered_routes,
        rescheduled_route_timeouts,
    )
