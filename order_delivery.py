from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import (
    assign_order_to_courier,
    cancel_order,
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
    set_order_status,
)


OFFER_TIMEOUT_SECONDS = 30
MAX_CYCLE_SECONDS = 420  # 7 minutos


def _offer_reply_markup(order_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Aceptar", callback_data="order_accept_{}".format(order_id)),
            InlineKeyboardButton("Rechazar", callback_data="order_reject_{}".format(order_id)),
        ],
        [InlineKeyboardButton("Estoy ocupado", callback_data="order_busy_{}".format(order_id))],
    ])


def _get_offer_alert_config():
    reminders_enabled = str(get_setting("offer_reminders_enabled", "1") or "1").strip() == "1"
    reminder_seconds_raw = str(get_setting("offer_reminder_seconds", "8,16") or "8,16")
    voice_enabled = str(get_setting("offer_voice_enabled", "0") or "0").strip() == "1"
    voice_file_id = (get_setting("offer_voice_file_id", "") or "").strip()

    reminder_seconds = []
    for chunk in reminder_seconds_raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            sec = int(chunk)
            if 0 < sec < OFFER_TIMEOUT_SECONDS:
                reminder_seconds.append(sec)
        except Exception:
            continue
    if not reminder_seconds:
        reminder_seconds = [8, 16]

    return {
        "reminders_enabled": reminders_enabled,
        "reminder_seconds": reminder_seconds,
        "voice_enabled": voice_enabled and bool(voice_file_id),
        "voice_file_id": voice_file_id,
    }


def _cancel_offer_jobs(context, order_id, queue_id):
    timeout_jobs = context.job_queue.get_jobs_by_name(
        "offer_timeout_{}_{}".format(order_id, queue_id)
    )
    for job in timeout_jobs:
        job.schedule_removal()

    reminder_prefix = "offer_reminder_{}_{}_".format(order_id, queue_id)
    for idx in range(1, 6):
        jobs = context.job_queue.get_jobs_by_name(reminder_prefix + str(idx))
        for job in jobs:
            job.schedule_removal()


def _offer_reminder_job(context):
    data = context.job.context or {}
    order_id = data.get("order_id")
    queue_id = data.get("queue_id")
    chat_id = data.get("telegram_id")
    reminder_idx = data.get("reminder_idx", 1)

    if not order_id or not queue_id or not chat_id:
        return

    order = get_order_by_id(order_id)
    if not order or order["status"] != "PUBLISHED":
        return

    current = get_current_offer_for_order(order_id)
    if not current or current["queue_id"] != queue_id:
        return

    config = _get_offer_alert_config()

    if config["voice_enabled"]:
        try:
            context.bot.send_voice(
                chat_id=chat_id,
                voice=config["voice_file_id"],
            )
        except Exception:
            pass

    try:
        context.bot.send_message(
            chat_id=chat_id,
            text="Servicio disponible #{}. Responde ahora para no perderlo.".format(order_id),
            reply_markup=_offer_reply_markup(order_id),
        )
    except Exception as e:
        print("[WARN] No se pudo enviar recordatorio de oferta {} (intento {}): {}".format(
            order_id, reminder_idx, e
        ))


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


def publish_order_to_couriers(order_id, ally_id, context, admin_id_override=None):
    """
    Inicia el ciclo secuencial de ofertas para un pedido.
    1. Busca couriers elegibles (filtrados por veto, base, activación).
    2. Crea la cola de ofertas en BD.
    3. Envía la primera oferta.
    4. Programa timeout de 30s con JobQueue.
    """
    admin_id = None
    if admin_id_override is not None:
        admin_id = int(admin_id_override)
    else:
        admin_link = get_approved_admin_link_for_ally(ally_id)
        if not admin_link:
            print("[WARN] Aliado sin admin aprobado, no se puede publicar pedido")
            return 0
        admin_id = admin_link["admin_id"]
    order = get_order_by_id(order_id)
    if not order:
        return 0

    from services import check_service_fee_available

    # Verificacion previa de saldo del aliado y del admin antes de ofertar.
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
    if p_lat is None and pickup_location_id:
        loc = get_ally_location_by_id(pickup_location_id, ally_id)
        if loc:
            p_lat = loc["lat"] if "lat" in loc.keys() else None
            p_lng = loc["lng"] if "lng" in loc.keys() else None

    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=requires_cash,
        cash_required_amount=cash_amount,
        pickup_lat=p_lat,
        pickup_lng=p_lng,
    )
    if not eligible:
        print("[WARN] No hay couriers elegibles para pedido {}".format(order_id))
        return 0

    # Verificacion previa de saldo por courier y admin antes de ofertar.
    filtered = []
    admin_without_balance = False
    couriers_without_balance = []
    for c in eligible:
        courier_id = c["courier_id"]
        ok, code = check_service_fee_available(
            target_type="COURIER",
            target_id=courier_id,
            admin_id=admin_id,
        )
        if ok:
            filtered.append(c)
        else:
            if code == "ADMIN_SIN_SALDO":
                admin_without_balance = True
            else:
                couriers_without_balance.append(courier_id)

    if admin_without_balance:
        print("[WARN] Pedido {} sin oferta por saldo admin insuficiente".format(order_id))
        _notify_recharge_needed_to_admin(context, admin_id)
        _notify_recharge_needed_to_ally(context, ally_id)
        return 0

    for courier_id in couriers_without_balance:
        _notify_recharge_needed_to_courier(context, courier_id)

    if not filtered:
        print("[WARN] Pedido {} sin oferta: todos los couriers sin saldo operativo".format(order_id))
        _notify_recharge_needed_to_ally(context, ally_id)
        return 0

    courier_ids = [c["courier_id"] for c in filtered]
    create_offer_queue(order_id, courier_ids)
    set_order_status(order_id, "PUBLISHED", "published_at")

    # Guardar timestamp de inicio del ciclo
    context.bot_data.setdefault("offer_cycles", {})[order_id] = {
        "started_at": __import__("time").time(),
        "admin_id": admin_id,
        "ally_id": ally_id,
    }

    _send_next_offer(order_id, context)
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

    offer_text = "SERVICIO DISPONIBLE\n\n" + _build_offer_text(order)
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

    config = _get_offer_alert_config()
    if config["reminders_enabled"]:
        reminder_idx = 1
        for sec in config["reminder_seconds"]:
            context.job_queue.run_once(
                _offer_reminder_job,
                sec,
                context={
                    "order_id": order_id,
                    "queue_id": next_offer["queue_id"],
                    "telegram_id": next_offer["telegram_id"],
                    "reminder_idx": reminder_idx,
                },
                name="offer_reminder_{}_{}_{}".format(order_id, next_offer["queue_id"], reminder_idx),
            )
            reminder_idx += 1


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
    """Reinicia el ciclo si no se superan los 7 minutos. Si se superan, cancela."""
    cycle_info = context.bot_data.get("offer_cycles", {}).get(order_id)
    if not cycle_info:
        return

    import time
    elapsed = time.time() - cycle_info["started_at"]

    if elapsed >= MAX_CYCLE_SECONDS:
        _expire_order(order_id, cycle_info, context)
        return

    reset_offer_queue(order_id)
    _send_next_offer(order_id, context)


def _expire_order(order_id, cycle_info, context):
    """Nadie acepto en 7 minutos. Cobra $300 al aliado y cancela."""
    cancel_order(order_id, "SYSTEM")
    delete_offer_queue(order_id)

    # Limpiar bot_data
    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    context.bot_data.get("offer_messages", {}).pop(order_id, None)

    ally_id = cycle_info["ally_id"]
    admin_id = cycle_info["admin_id"]

    # Cobrar $300 al aliado como comisión por gestión
    try:
        from services import apply_service_fee
        fee_ok, fee_msg = apply_service_fee(
            target_type="ALLY",
            target_id=ally_id,
            admin_id=admin_id,
            ref_type="ORDER",
            ref_id=order_id,
        )
        if not fee_ok:
            print("[WARN] No se pudo cobrar fee de expiración al aliado: {}".format(fee_msg))
    except Exception as e:
        print("[WARN] Error al cobrar fee de expiración: {}".format(e))

    # Notificar al aliado
    try:
        ally = get_ally_by_id(ally_id)
        if ally:
            ally_user = get_user_by_id(ally["user_id"])
            if ally_user and ally_user.get("telegram_id"):
                context.bot.send_message(
                    chat_id=ally_user["telegram_id"],
                    text=(
                        "Tu pedido #{} fue cancelado porque ningun repartidor "
                        "lo acepto en 7 minutos.\n\n"
                        "Se descontaron $300 de tu saldo como comision por la gestion."
                    ).format(order_id),
                )
    except Exception as e:
        print("[WARN] No se pudo notificar expiración al aliado: {}".format(e))


def ally_active_orders(update, context):
    """Muestra pedidos activos e historial reciente del aliado."""
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
    all_orders = get_orders_by_ally(ally["id"], limit=20)
    history_orders = [o for o in all_orders if o["status"] in ("DELIVERED", "CANCELLED")]

    if not active_orders and not history_orders:
        update.message.reply_text("No tienes pedidos registrados.")
        return

    STATUS_LABELS = {
        "PENDING": "Pendiente",
        "PUBLISHED": "Buscando repartidor",
        "ACCEPTED": "Repartidor asignado",
        "PICKED_UP": "En camino al cliente",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }

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
                keyboard = [[InlineKeyboardButton(
                    "Cancelar pedido",
                    callback_data="order_cancel_{}".format(order["id"]),
                )]]
                update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                update.message.reply_text(text)
    else:
        update.message.reply_text("No tienes pedidos activos.")

    if history_orders:
        update.message.reply_text("Historial reciente (entregados/cancelados):")
        for order in history_orders[:10]:
            status_label = STATUS_LABELS.get(order["status"], order["status"])

            courier_name = "Sin asignar"
            courier_id = order["courier_id"] if "courier_id" in order.keys() else None
            if courier_id:
                courier_row = get_courier_by_id(courier_id)
                if courier_row and courier_row["full_name"]:
                    courier_name = courier_row["full_name"]

            ally_admin_snapshot_id = order["ally_admin_id_snapshot"] if "ally_admin_id_snapshot" in order.keys() else None
            courier_admin_snapshot_id = order["courier_admin_id_snapshot"] if "courier_admin_id_snapshot" in order.keys() else None

            ally_admin_label = str(ally_admin_snapshot_id) if ally_admin_snapshot_id else "N/A"
            if ally_admin_snapshot_id:
                admin_row = get_admin_by_id(int(ally_admin_snapshot_id))
                if admin_row and admin_row["full_name"]:
                    ally_admin_label = "{} ({})".format(ally_admin_label, admin_row["full_name"])

            courier_admin_label = str(courier_admin_snapshot_id) if courier_admin_snapshot_id else "N/A"
            if courier_admin_snapshot_id:
                admin_row = get_admin_by_id(int(courier_admin_snapshot_id))
                if admin_row and admin_row["full_name"]:
                    courier_admin_label = "{} ({})".format(courier_admin_label, admin_row["full_name"])

            event_at = "N/A"
            if order["status"] == "DELIVERED" and "delivered_at" in order.keys() and order["delivered_at"]:
                event_at = order["delivered_at"]
            elif order["status"] == "CANCELLED" and "canceled_at" in order.keys() and order["canceled_at"]:
                event_at = order["canceled_at"]
            canceled_by = order["canceled_by"] if "canceled_by" in order.keys() and order["canceled_by"] else "N/A"

            text = (
                "Pedido #{}\n"
                "Estado: {}\n"
                "Fecha: {}\n"
                "Cliente: {}\n"
                "Repartidor: {}\n"
                "Admin aliado (snapshot): {}\n"
                "Admin repartidor (snapshot): {}\n"
                "Cancelado por: {}"
            ).format(
                order["id"],
                status_label,
                event_at,
                order["customer_name"] or "N/A",
                courier_name,
                ally_admin_label,
                courier_admin_label,
                canceled_by,
            )
            update.message.reply_text(text)


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

    from db import get_platform_admin
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

    text = (
        "Pedido #{}\n\n"
        "Estado: {}\n"
        "Aliado: {}\n"
        "Repartidor: {}\n"
        "Cliente: {}\n"
        "Telefono: {}\n"
        "Direccion: {}\n"
        "Distancia: {:.1f} km\n"
        "Tarifa: ${:,}\n\n"
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

    if was_published:
        current = get_current_offer_for_order(order_id)
        if current:
            jobs = context.job_queue.get_jobs_by_name(
                "offer_timeout_{}_{}".format(order_id, current["queue_id"])
            )
            for job in jobs:
                job.schedule_removal()

    cancel_order(order_id, "ADMIN")
    delete_offer_queue(order_id)

    context.bot_data.get("offer_cycles", {}).pop(order_id, None)
    context.bot_data.get("offer_messages", {}).pop(order_id, None)

    try:
        ally = get_ally_by_id(order["ally_id"])
        if ally:
            ally_user = get_user_by_id(ally["user_id"])
            if ally_user and ally_user.get("telegram_id"):
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
    - ^order_(accept|reject|busy|pickup|delivered|release|cancel)_\\d+$
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
    if data.startswith("order_delivered_"):
        order_id = int(data.replace("order_delivered_", ""))
        return _handle_delivered(update, context, order_id)
    if data.startswith("order_release_"):
        order_id = int(data.replace("order_release_", ""))
        return _handle_release(update, context, order_id)
    if data.startswith("order_cancel_"):
        order_id = int(data.replace("order_cancel_", ""))
        return _handle_cancel_ally(update, context, order_id)
    return None


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

    # Cancelar el job de timeout
    _cancel_offer_jobs(context, order_id, current["queue_id"])

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
    keyboard.append([InlineKeyboardButton("Confirmar recogida", callback_data="order_pickup_{}".format(order_id))])
    keyboard.append([InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order_id))])

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


def _handle_release(update, context, order_id):
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

    release_order_from_courier(order_id)
    query.edit_message_text("Pedido #{} liberado. Sera ofrecido a otros repartidores.".format(order_id))

    _notify_ally_order_released(context, order)

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

    requires_cash = bool(order["requires_cash"])
    cash_amount = int(order["cash_required_amount"] or 0)

    eligible = get_eligible_couriers_for_order(
        admin_id=admin_id,
        ally_id=ally_id,
        requires_cash=requires_cash,
        cash_required_amount=cash_amount,
    )
    if eligible:
        import time
        courier_ids = [c["courier_id"] for c in eligible]
        delete_offer_queue(order_id)
        create_offer_queue(order_id, courier_ids)

        context.bot_data.setdefault("offer_cycles", {})[order_id] = {
            "started_at": time.time(),
            "admin_id": admin_id,
            "ally_id": ally_id,
        }
        _send_next_offer(order_id, context)


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

    # Cancelar jobs de timeout si estaba en ciclo de ofertas
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

    query.edit_message_text("Pedido #{} cancelado exitosamente.".format(order_id))

    if had_courier:
        _notify_courier_order_cancelled(context, order)


def _handle_pickup(update, context, order_id):
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

    upsert_order_pickup_confirmation(order_id, courier["id"], order["ally_id"], "PENDING")
    courier_name = courier["full_name"] or "Repartidor"
    _notify_ally_pickup(context, order, courier_name)

    keyboard = [[InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order_id))]]
    query.edit_message_text(
        "Pedido #{} - Solicitud enviada.\n\n"
        "El aliado debe confirmar la entrega del pedido en recogida.\n"
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
        set_order_status(order_id, "PICKED_UP", "pickup_confirmed_at")
        query.edit_message_text("Recogida confirmada. El repartidor fue notificado para continuar a entrega.")
        _notify_courier_pickup_approved(context, order)
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
    admin_link = get_approved_admin_link_for_ally(ally_id)
    if admin_link:
        admin_id = admin_link["admin_id"]
    else:
        courier_admin_link = get_approved_admin_link_for_courier(courier_id)
        admin_id = courier_admin_link["admin_id"] if courier_admin_link else None

    fee_ally_ok = False
    fee_courier_ok = False

    if admin_id:
        from services import apply_service_fee

        ally_ok, ally_msg = apply_service_fee(
            target_type="ALLY",
            target_id=ally_id,
            admin_id=admin_id,
            ref_type="ORDER",
            ref_id=order_id,
        )
        if ally_ok:
            fee_ally_ok = True
        else:
            print("[WARN] No se pudo cobrar fee al aliado: {}".format(ally_msg))

        courier_ok, courier_msg = apply_service_fee(
            target_type="COURIER",
            target_id=courier_id,
            admin_id=admin_id,
            ref_type="ORDER",
            ref_id=order_id,
        )
        if courier_ok:
            fee_courier_ok = True
        else:
            if courier_msg == "ADMIN_SIN_SALDO":
                try:
                    admin_row = get_admin_by_id(admin_id)
                    if admin_row:
                        admin_user = get_user_by_id(admin_row["user_id"])
                        if admin_user and admin_user.get("telegram_id"):
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

    set_order_status(order_id, "DELIVERED", "delivered_at")
    delete_offer_queue(order_id)

    if fee_ally_ok and fee_courier_ok:
        query.edit_message_text(
            "Pedido #{} entregado exitosamente.\n\n"
            "Se descontaron $300 de tu saldo por este servicio.".format(order_id)
        )
    elif fee_courier_ok:
        query.edit_message_text(
            "Pedido #{} entregado exitosamente.\n\n"
            "Se descontaron $300 de tu saldo por este servicio.".format(order_id)
        )
    else:
        query.edit_message_text("Pedido #{} entregado exitosamente.".format(order_id))

    _notify_ally_delivered(context, order)


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


def _notify_ally_pickup(context, order, courier_name):
    """Solicita confirmacion al aliado antes de habilitar la entrega al repartidor."""
    try:
        ally = get_ally_by_id(order["ally_id"])
        if not ally:
            return False
        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user.get("telegram_id"):
            return False
        keyboard = [
            [InlineKeyboardButton("Confirmar entrega al repartidor", callback_data="order_pickupconfirm_approve_{}".format(order["id"]))],
            [InlineKeyboardButton("Reportar problema", callback_data="order_pickupconfirm_reject_{}".format(order["id"]))],
        ]
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text=(
                "Seguridad de recogida - Pedido #{}\n\n"
                "El repartidor {} indica que recibio el pedido.\n"
                "Confirma para habilitar la ruta de entrega."
            ).format(order["id"], courier_name),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return True
    except Exception as e:
        print("[WARN] No se pudo notificar pickup al aliado: {}".format(e))
        return False


def _notify_courier_pickup_approved(context, order):
    """Envia al courier la entrega cuando el aliado confirma la recogida."""
    try:
        if not order["courier_id"]:
            return
        courier = get_courier_by_id(order["courier_id"])
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user.get("telegram_id"):
            return

        dropoff_lat, dropoff_lng = _get_dropoff_coords(order)
        keyboard = []
        keyboard.extend(_build_navigation_rows(dropoff_lat, dropoff_lng))
        keyboard.append([InlineKeyboardButton("Marcar como entregado", callback_data="order_delivered_{}".format(order["id"]))])
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=(
                "Recogida confirmada por el aliado - Pedido #{}\n\n"
                "Entrega en: {}\n"
                "Cliente: {}\n"
                "Telefono cliente: {}\n\n"
                "Dirigete al punto de entrega."
            ).format(
                order["id"],
                order["customer_address"] or "No disponible",
                order["customer_name"] or "No disponible",
                order["customer_phone"] or "No disponible",
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
        if not courier_user or not courier_user.get("telegram_id"):
            return

        keyboard = [
            [InlineKeyboardButton("Solicitar confirmacion nuevamente", callback_data="order_pickup_{}".format(order["id"]))],
            [InlineKeyboardButton("Liberar pedido", callback_data="order_release_{}".format(order["id"]))],
        ]
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text=(
                "El aliado rechazo la confirmacion de recogida del pedido #{}.\n"
                "Verifica en el punto de recogida y vuelve a solicitar confirmacion."
            ).format(order["id"]),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar rechazo de recogida al courier: {}".format(e))


def _notify_ally_delivered(context, order):
    """Notifica al aliado que el pedido fue entregado."""
    try:
        ally = get_ally_by_id(order["ally_id"])
        if not ally:
            return
        ally_user = get_user_by_id(ally["user_id"])
        if not ally_user or not ally_user.get("telegram_id"):
            return
        context.bot.send_message(
            chat_id=ally_user["telegram_id"],
            text="Tu pedido #{} fue entregado exitosamente.".format(order["id"]),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar entrega al aliado: {}".format(e))


def _notify_courier_order_cancelled(context, order):
    """Notifica al courier que el aliado cancelo el pedido."""
    try:
        if not order["courier_id"]:
            return
        courier = get_courier_by_id(order["courier_id"])
        if not courier:
            return
        courier_user = get_user_by_id(courier["user_id"])
        if not courier_user or not courier_user.get("telegram_id"):
            return
        context.bot.send_message(
            chat_id=courier_user["telegram_id"],
            text="El pedido #{} fue cancelado por el aliado.".format(order["id"]),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar cancelacion al courier: {}".format(e))


def _notify_ally_order_released(context, order):
    """Notifica al aliado que el courier libero el pedido."""
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
                "El repartidor libero tu pedido #{}. "
                "Estamos buscando otro repartidor."
            ).format(order["id"]),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar liberacion al aliado: {}".format(e))
