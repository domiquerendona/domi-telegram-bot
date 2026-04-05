# =============================================================================
# handlers/admin_panel.py — Panel de administración (Platform Admin + Local Admin)
# Extraído de main.py
# =============================================================================

import logging
logger = logging.getLogger(__name__)

import os
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from handlers.common import (
    _resolve_important_alert,
    _row_value,
    _schedule_important_alerts,
    _send_role_welcome_message,
    show_main_menu,
)
from services import (
    approve_role_registration,
    count_admin_couriers,
    count_admin_couriers_with_min_balance,
    create_admin_courier_link,
    deactivate_other_approved_admin_ally_links,
    es_admin_plataforma,
    get_active_orders_without_courier,
    get_admin_balance,
    get_admin_by_id,
    get_admin_by_telegram_id,
    get_admin_by_user_id,
    get_admin_link_for_ally,
    get_admin_reference_validator_permission,
    get_admin_reset_state_by_id,
    get_all_admins,
    PARKING_FEE_AMOUNT,
    set_address_parking_status,
    get_addresses_pending_parking_review,
    get_all_addresses_parking_review,
    get_ally_parking_fee_enabled,
    toggle_ally_parking_fee,
    get_ally_telegram_id_by_address_id,
    get_ally_telegram_id_by_ally_id,
    get_all_allies,
    get_all_couriers,
    get_all_local_admins,
    get_all_online_couriers,
    get_ally_approval_notification_chat_id,
    get_ally_by_id,
    get_ally_reset_state_by_id,
    get_courier_approval_notification_chat_id,
    get_courier_by_id,
    get_courier_reset_state_by_id,
    get_default_ally_location,
    get_local_admins_count,
    get_online_couriers_sorted_by_distance,
    get_order_by_id,
    get_pending_admins,
    get_pending_allies,
    get_pending_couriers,
    get_pending_couriers_by_admin,
    get_pending_reference_candidates,
    get_platform_admin,
    get_platform_admin_id,
    get_reference_candidate,
    get_totales_registros,
    get_user_by_id,
    get_user_by_telegram_id,
    get_user_db_id_from_update,
    list_ally_links_by_admin,
    list_pending_support_requests,
    list_approved_admin_teams,
    list_courier_links_by_admin,
    get_support_request_full,
    SUPPORT_TYPE_DELIVERY_PIN,
    SUPPORT_TYPE_ROUTE_STOP_PIN,
    SUPPORT_TYPE_PICKUP_PIN,
    SUPPORT_TYPE_ROUTE_PICKUP_PIN,
    platform_clear_admin_registration_reset,
    platform_clear_ally_registration_reset,
    platform_clear_courier_registration_reset,
    platform_enable_admin_registration_reset,
    platform_enable_ally_registration_reset,
    platform_enable_courier_registration_reset,
    review_reference_candidate,
    set_admin_reference_validator_permission,
    set_reference_candidate_coords,
    update_admin_status_by_id,
    update_ally_status_by_id,
    update_courier_status_by_id,
    upsert_admin_ally_link,
    user_has_platform_admin,
    _get_reference_reviewer,
)
from order_delivery import admin_orders_panel
from profile_changes import admin_change_requests_list
from handlers.config import tarifas_start
from handlers.registration import _create_or_reset_courier_from_context

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
SUPPORT_PAGE_SIZE = 6


def _support_type_label(support_type: str) -> str:
    labels = {
        SUPPORT_TYPE_DELIVERY_PIN: "Entrega pedido",
        SUPPORT_TYPE_PICKUP_PIN: "Pickup pedido",
        SUPPORT_TYPE_ROUTE_STOP_PIN: "Parada ruta",
        SUPPORT_TYPE_ROUTE_PICKUP_PIN: "Pickup ruta",
    }
    return labels.get(support_type, support_type or "Soporte")


def _support_created_label(created_at) -> str:
    if not created_at:
        return "-"
    if hasattr(created_at, "timetuple"):
        dt = created_at
    else:
        dt = None
        raw = str(created_at).strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                dt = datetime.strptime(raw[:len(fmt)], fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return raw

    now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    seconds = max(0, int((now_dt - dt).total_seconds()))
    if seconds < 60:
        age = "menos de 1 min"
    elif seconds < 3600:
        age = "{} min".format(seconds // 60)
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        age = "{}h {} min".format(hours, minutes) if minutes else "{}h".format(hours)
    return "{} ({})".format(dt.strftime("%Y-%m-%d %H:%M"), age)


def _support_owner_line(req) -> str:
    ally_id = _row_value(req, "order_ally_id", 0) or _row_value(req, "route_ally_id", 0)
    if ally_id:
        ally = get_ally_by_id(int(ally_id))
        if ally:
            return "Aliado responsable: {}".format(
                _row_value(ally, "business_name") or _row_value(ally, "owner_name") or "N/D"
            )
    creator_admin_id = _row_value(req, "order_creator_admin_id", 0)
    if creator_admin_id:
        admin = get_admin_by_id(int(creator_admin_id))
        if admin:
            return "Admin creador: {}".format(_row_value(admin, "full_name") or "N/D")
    return ""


def _support_target_lines(req):
    support_type = _row_value(req, "support_type")
    lines = []
    if support_type == SUPPORT_TYPE_DELIVERY_PIN:
        lines.append("Direccion de entrega: {}".format(_row_value(req, "delivery_address") or "N/D"))
        target_lat = _row_value(req, "dropoff_lat")
        target_lng = _row_value(req, "dropoff_lng")
    elif support_type == SUPPORT_TYPE_PICKUP_PIN:
        lines.append("Punto de recogida: {}".format(_row_value(req, "order_pickup_address") or "N/D"))
        target_lat = _row_value(req, "order_pickup_lat")
        target_lng = _row_value(req, "order_pickup_lng")
    elif support_type == SUPPORT_TYPE_ROUTE_STOP_PIN:
        lines.append(
            "Parada {}: {}".format(
                _row_value(req, "route_seq") or "-",
                _row_value(req, "route_customer_address") or "N/D",
            )
        )
        lines.append("Cliente: {}".format(_row_value(req, "route_customer_name") or "N/D"))
        target_lat = _row_value(req, "route_dropoff_lat")
        target_lng = _row_value(req, "route_dropoff_lng")
    else:
        lines.append("Punto de recogida: {}".format(_row_value(req, "route_pickup_address") or "N/D"))
        target_lat = _row_value(req, "route_pickup_lat")
        target_lng = _row_value(req, "route_pickup_lng")

    courier_lat = _row_value(req, "courier_lat")
    courier_lng = _row_value(req, "courier_lng")
    if target_lat is not None and target_lng is not None:
        lines.append("Pin objetivo: https://maps.google.com/?q={},{}".format(target_lat, target_lng))
    if courier_lat is not None and courier_lng is not None:
        lines.append("Courier en vivo: https://maps.google.com/?q={},{}".format(courier_lat, courier_lng))
    return lines


def _support_summary_label(req) -> str:
    support_type = _support_type_label(_row_value(req, "support_type"))
    courier_name = (_row_value(req, "courier_name") or "Repartidor").strip()
    if _row_value(req, "order_id", 0):
        order_id = int(_row_value(req, "order_id", 0))
        return "{} | Pedido #{} | {}".format(support_type, order_id, courier_name)
    route_id = int(_row_value(req, "route_id", 0) or 0)
    seq = _row_value(req, "route_seq", 0)
    if seq:
        return "{} | Ruta #{} parada {} | {}".format(support_type, route_id, seq, courier_name)
    return "{} | Ruta #{} | {}".format(support_type, route_id, courier_name)


def _support_action_rows(req):
    support_id = int(_row_value(req, "id", 0) or 0)
    order_id = int(_row_value(req, "order_id", 0) or 0)
    route_id = int(_row_value(req, "route_id", 0) or 0)
    route_seq = int(_row_value(req, "route_seq", 0) or 0)
    support_type = _row_value(req, "support_type")

    if support_type == SUPPORT_TYPE_DELIVERY_PIN:
        return [
            [InlineKeyboardButton("Finalizar servicio", callback_data="admin_pinissue_fin_{}".format(order_id))],
            [InlineKeyboardButton("Cancelar falla repartidor", callback_data="admin_pinissue_cancel_courier_{}".format(order_id))],
            [InlineKeyboardButton("Cancelar falla aliado", callback_data="admin_pinissue_cancel_ally_{}".format(order_id))],
        ]
    if support_type == SUPPORT_TYPE_PICKUP_PIN:
        return [
            [InlineKeyboardButton("Confirmar llegada", callback_data="admin_pickup_confirm_{}_{}".format(order_id, support_id))],
            [InlineKeyboardButton("Liberar pedido", callback_data="admin_pickup_release_{}_{}".format(order_id, support_id))],
        ]
    if support_type == SUPPORT_TYPE_ROUTE_STOP_PIN:
        suffix = "{}_{}".format(route_id, route_seq)
        return [
            [InlineKeyboardButton("Finalizar parada", callback_data="admin_ruta_pinissue_fin_{}".format(suffix))],
            [InlineKeyboardButton("Cancelar falla repartidor", callback_data="admin_ruta_pinissue_cancel_courier_{}".format(suffix))],
            [InlineKeyboardButton("Cancelar falla aliado", callback_data="admin_ruta_pinissue_cancel_ally_{}".format(suffix))],
        ]
    return [
        [InlineKeyboardButton("Confirmar llegada", callback_data="admin_ruta_pickup_confirm_{}_{}".format(route_id, support_id))],
        [InlineKeyboardButton("Liberar ruta", callback_data="admin_ruta_pickup_release_{}_{}".format(route_id, support_id))],
    ]


def _get_support_inbox_actor(telegram_id: int):
    admin = get_admin_by_telegram_id(telegram_id)
    is_platform = user_has_platform_admin(telegram_id)
    if not admin and not is_platform:
        return None, False
    return admin, is_platform


def _render_support_requests_list(query, offset: int = 0, edit: bool = False):
    admin, is_platform = _get_support_inbox_actor(query.from_user.id)
    if not admin and not is_platform:
        query.answer("No tienes permisos para ver esta bandeja.", show_alert=True)
        return

    admin_filter = None if is_platform else admin["id"]
    rows = list_pending_support_requests(admin_id=admin_filter, limit=SUPPORT_PAGE_SIZE + 1, offset=offset)
    has_next = len(rows) > SUPPORT_PAGE_SIZE
    rows = rows[:SUPPORT_PAGE_SIZE]

    scope_text = "todas las solicitudes" if is_platform else "las solicitudes de tu equipo"
    text = "Bandeja de soportes pendientes.\nRevisa {}.".format(scope_text)
    keyboard = []
    if rows:
        for req in rows:
            keyboard.append([
                InlineKeyboardButton(
                    _support_summary_label(req),
                    callback_data="admin_support_view_{}_{}".format(req["id"], offset),
                )
            ])
    else:
        text = "No hay soportes pendientes en este momento."

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("Anterior", callback_data="admin_support_list_{}".format(max(0, offset - SUPPORT_PAGE_SIZE))))
    if has_next:
        nav.append(InlineKeyboardButton("Siguiente", callback_data="admin_support_list_{}".format(offset + SUPPORT_PAGE_SIZE)))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("Actualizar", callback_data="admin_support_list_{}".format(offset))])

    markup = InlineKeyboardMarkup(keyboard)
    if edit:
        query.edit_message_text(text, reply_markup=markup)
    else:
        query.message.reply_text(text, reply_markup=markup)


def _render_support_request_detail(query, support_id: int, offset: int):
    admin, is_platform = _get_support_inbox_actor(query.from_user.id)
    if not admin and not is_platform:
        query.answer("No tienes permisos para ver esta solicitud.", show_alert=True)
        return

    req = get_support_request_full(support_id)
    if not req or _row_value(req, "status") != "PENDING":
        query.edit_message_text(
            "Esta solicitud ya no esta pendiente.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver a la bandeja", callback_data="admin_support_list_{}".format(offset))]
            ]),
        )
        return

    if not is_platform and admin["id"] != req["admin_id"]:
        query.edit_message_text("No tienes permiso para revisar esta solicitud.")
        return

    can_resolve = is_platform or (admin and admin["id"] == req["admin_id"])
    assigned_admin = _row_value(req, "admin_name") or "N/D"
    lines = [
        "{}".format(_support_type_label(_row_value(req, "support_type"))),
        "Solicitud #{}".format(_row_value(req, "id") or "-"),
        "Asignada a: {}".format(assigned_admin),
        "Creada: {}".format(_support_created_label(_row_value(req, "created_at"))),
        "",
        "Repartidor: {}".format(_row_value(req, "courier_name") or "N/D"),
        "Telefono: {}".format(_row_value(req, "courier_phone") or "N/D"),
    ]
    owner_line = _support_owner_line(req)
    if owner_line:
        lines.append(owner_line)
    lines.extend(_support_target_lines(req))

    keyboard = []
    if can_resolve:
        keyboard.extend(_support_action_rows(req))
    keyboard.append([InlineKeyboardButton("Volver a la bandeja", callback_data="admin_support_list_{}".format(offset))])
    query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


def _registration_reset_status_label(reset_state):
    if not reset_state:
        return "No autorizado"
    if reset_state.get("registration_reset_active"):
        return "Autorizado activo"
    if reset_state.get("registration_reset_consumed_at"):
        return "Consumido"
    return "No autorizado"


def _append_registration_reset_button(keyboard, role_prefix: str, role_id: int, role_status: str, reset_state):
    if role_status not in ("INACTIVE", "REJECTED"):
        return
    if reset_state and reset_state.get("registration_reset_active"):
        keyboard.append([InlineKeyboardButton("Revocar reinicio", callback_data="{}_reset_clear_{}".format(role_prefix, role_id))])
        return
    if reset_state and reset_state.get("registration_reset_consumed_at"):
        if role_prefix != "config_ally":
            return
    keyboard.append([InlineKeyboardButton("Autorizar reinicio", callback_data="{}_reset_enable_{}".format(role_prefix, role_id))])


def _notify_admin_local_welcome(context, admin_id: int, reactivated: bool = False):
    admin = get_admin_by_id(admin_id)
    if not admin:
        return
    user_row = get_user_by_id(admin["user_id"])
    if not user_row:
        return
    _send_role_welcome_message(
        context,
        "ADMIN_LOCAL",
        user_row["telegram_id"],
        profile=admin,
        reactivated=reactivated,
    )


def _render_platform_ally_detail(query, ally_id: int):
    ally = get_ally_by_id(ally_id)
    if not ally:
        query.edit_message_text("No se encontró el aliado.")
        return

    reset_state = get_ally_reset_state_by_id(ally_id)
    reset_status = _registration_reset_status_label(reset_state)
    admin_link = get_admin_link_for_ally(ally_id)
    default_loc = get_default_ally_location(ally_id)
    loc_lat = _row_value(default_loc, "lat") if default_loc else None
    loc_lng = _row_value(default_loc, "lng") if default_loc else None

    if loc_lat is not None and loc_lng is not None:
        loc_text = "{}, {}".format(loc_lat, loc_lng)
        maps_text = "Maps: https://www.google.com/maps?q={},{}\n".format(loc_lat, loc_lng)
    else:
        loc_text = "No disponible"
        maps_text = ""

    subsidio = int((_row_value(ally, "delivery_subsidy") or 0))
    min_purchase = _row_value(ally, "min_purchase_for_subsidy")
    if subsidio == 0:
        subsidio_label = "Subsidio domicilio: No configurado"
    elif min_purchase is not None:
        subsidio_label = (
            "Subsidio domicilio: ${:,} por pedido\n"
            "Modo: Condicional\n"
            "Compra minima: ${:,}"
        ).format(subsidio, min_purchase)
    else:
        subsidio_label = (
            "Subsidio domicilio: ${:,} por pedido\n"
            "Modo: Incondicional"
        ).format(subsidio)

    if admin_link:
        team_name = _row_value(admin_link, "team_name", "-")
        team_code = _row_value(admin_link, "team_code", "-")
        link_status = _row_value(admin_link, "link_status", "-")
        equipo_label = "{} ({}) - Vínculo: {}".format(team_name, team_code, link_status)
    else:
        equipo_label = "(sin equipo asignado)"

    parking_enabled = get_ally_parking_fee_enabled(ally_id)
    parking_label = "Cobro parqueo dificil: {}".format("ACTIVO" if parking_enabled else "INACTIVO")

    texto = (
        "Detalle del aliado:\n\n"
        "ID: {id}\n"
        "Negocio: {business_name}\n"
        "Propietario: {owner_name}\n"
        "Teléfono: {phone}\n"
        "Dirección: {address}\n"
        "Ciudad: {city}\n"
        "Barrio: {barrio}\n"
        "Estado: {status}\n"
        "Equipo: {equipo}\n"
        "Reinicio de registro: {reset_status}\n"
        "{subsidio_label}\n"
        "{parking_label}\n"
        "Ubicación: {loc}\n"
        "{maps}"
    ).format(
        id=_row_value(ally, "id", "-"),
        business_name=_row_value(ally, "business_name", "-"),
        owner_name=_row_value(ally, "owner_name", "-"),
        phone=_row_value(ally, "phone", "-"),
        address=_row_value(ally, "address", "-"),
        city=_row_value(ally, "city", "-"),
        barrio=_row_value(ally, "barrio", "-"),
        status=_row_value(ally, "status", "-"),
        equipo=equipo_label,
        reset_status=reset_status,
        subsidio_label=subsidio_label,
        parking_label=parking_label,
        loc=loc_text,
        maps=maps_text,
    )

    status = _row_value(ally, "status")
    keyboard = []

    if status == "PENDING":
        keyboard.append([
            InlineKeyboardButton("✅ Aprobar", callback_data="config_ally_enable_{}".format(ally_id)),
            InlineKeyboardButton("❌ Rechazar", callback_data="config_ally_reject_{}".format(ally_id)),
        ])
    if status == "APPROVED":
        keyboard.append([InlineKeyboardButton("⛔ Desactivar", callback_data="config_ally_disable_{}".format(ally_id))])
    if status == "INACTIVE":
        keyboard.append([InlineKeyboardButton("✅ Activar", callback_data="config_ally_enable_{}".format(ally_id))])
        _append_registration_reset_button(keyboard, "config_ally", ally_id, status, reset_state)
    if status == "REJECTED":
        _append_registration_reset_button(keyboard, "config_ally", ally_id, status, reset_state)

    keyboard.append([InlineKeyboardButton(
        "Editar subsidio domicilio (${:,})".format(subsidio),
        callback_data="config_ally_subsidy_{}".format(ally_id)
    )])
    keyboard.append([InlineKeyboardButton(
        "Compra minima subsidio ({})".format(
            "${:,}".format(min_purchase) if min_purchase is not None else "sin condicion"
        ),
        callback_data="config_ally_minpurchase_{}".format(ally_id)
    )])
    keyboard.append([InlineKeyboardButton(
        "{} Cobro parqueo dificil".format("Desactivar" if parking_enabled else "Activar"),
        callback_data="config_ally_parking_toggle_{}".format(ally_id)
    )])
    keyboard.append([InlineKeyboardButton("Asignar/corregir equipo", callback_data="config_ally_assign_menu_{}".format(ally_id))])
    keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")])

    query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))




def _render_reference_candidates(query_or_update, offset: int = 0, edit: bool = False):
    rows = get_pending_reference_candidates(offset=offset, limit=10)

    if not rows:
        text = "No hay referencias pendientes por validar."
        keyboard = [[InlineKeyboardButton("Actualizar", callback_data="ref_list_0")]]
    else:
        text = "Referencias pendientes.\nToca una para revisar:"
        keyboard = []
        for row in rows:
            snippet = (row["raw_text"] or "")[:35]
            label = "#{} {} ({})".format(row["id"], snippet, row["seen_count"])
            keyboard.append([InlineKeyboardButton(label, callback_data="ref_view_{}".format(row["id"]))])

        nav = []
        if offset > 0:
            nav.append(InlineKeyboardButton("Anterior", callback_data="ref_list_{}".format(max(0, offset - 10))))
        if len(rows) == 10:
            nav.append(InlineKeyboardButton("Siguiente", callback_data="ref_list_{}".format(offset + 10)))
        if nav:
            keyboard.append(nav)
        keyboard.append([InlineKeyboardButton("Actualizar", callback_data="ref_list_{}".format(offset))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    if edit:
        query_or_update.edit_message_text(text, reply_markup=reply_markup)
    else:
        query_or_update.message.reply_text(text, reply_markup=reply_markup)


def cmd_referencias(update, context):
    reviewer = _get_reference_reviewer(update.effective_user.id)
    if not reviewer["ok"]:
        update.message.reply_text(reviewer["message"])
        return
    _render_reference_candidates(update, offset=0, edit=False)


def reference_validation_callback(update, context):
    query = update.callback_query
    data = query.data
    reviewer = _get_reference_reviewer(query.from_user.id)
    if not reviewer["ok"]:
        query.answer(reviewer["message"], show_alert=True)
        return

    if data.startswith("ref_list_"):
        query.answer()
        try:
            offset = int(data.replace("ref_list_", ""))
        except Exception:
            offset = 0
        _render_reference_candidates(query, offset=max(0, offset), edit=True)
        return

    if data.startswith("ref_view_"):
        query.answer()
        try:
            candidate_id = int(data.replace("ref_view_", ""))
        except Exception:
            query.answer("Referencia invalida.", show_alert=True)
            return

        row = get_reference_candidate(candidate_id)
        if not row:
            query.edit_message_text(
                "Referencia no encontrada.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="ref_list_0")]])
            )
            return

        lat = row["suggested_lat"]
        lng = row["suggested_lng"]
        maps_line = ""
        if lat is not None and lng is not None:
            maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(lat, lng)
            try:
                context.bot.send_location(
                    chat_id=query.message.chat_id,
                    latitude=float(lat),
                    longitude=float(lng),
                )
            except Exception:
                pass

        text = (
            "Referencia #{}\n"
            "Texto: {}\n"
            "Normalizado: {}\n"
            "Veces vista: {}\n"
            "Fuente: {}\n"
            "Coords sugeridas: {}, {}\n"
            "{}"
            "Estado: {}"
        ).format(
            row["id"],
            row["raw_text"] or "-",
            row["normalized_text"] or "-",
            row["seen_count"] or 0,
            row["source"] or "-",
            lat if lat is not None else "-",
            lng if lng is not None else "-",
            maps_line,
            row["status"] or "-",
        )

        keyboard = [
            [
                InlineKeyboardButton("Aprobar", callback_data="ref_approve_{}".format(row["id"])),
                InlineKeyboardButton("Rechazar", callback_data="ref_reject_{}".format(row["id"])),
            ],
            [InlineKeyboardButton("Volver", callback_data="ref_list_0")],
        ]
        if lat is None or lng is None:
            keyboard.insert(1, [InlineKeyboardButton("Asignar ubicacion", callback_data="ref_setloc_{}".format(row["id"]))])
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("ref_setloc_"):
        query.answer()
        try:
            candidate_id = int(data.replace("ref_setloc_", ""))
        except Exception:
            query.answer("Referencia invalida.", show_alert=True)
            return

        row = get_reference_candidate(candidate_id)
        if not row:
            query.edit_message_text(
                "Referencia no encontrada.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="ref_list_0")]])
            )
            return

        context.user_data["ref_assign_candidate_id"] = candidate_id
        query.edit_message_text(
            "Envia un PIN de ubicacion de Telegram para esta referencia.\n\n"
            "Referencia: {}\n"
            "Luego te mostrare los botones para aprobar o rechazar.".format(row["raw_text"] or "-"),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="ref_view_{}".format(candidate_id))]])
        )
        return

    if data.startswith("ref_approve_") or data.startswith("ref_reject_"):
        query.answer()
        approve = data.startswith("ref_approve_")
        prefix = "ref_approve_" if approve else "ref_reject_"
        try:
            candidate_id = int(data.replace(prefix, ""))
        except Exception:
            query.answer("Referencia invalida.", show_alert=True)
            return

        new_status = "APPROVED" if approve else "REJECTED"
        ok, msg = review_reference_candidate(
            candidate_id,
            new_status,
            reviewed_by_admin_id=reviewer["admin_id"],
            note="review_by_tg:{}".format(query.from_user.id),
        )
        keyboard = [[InlineKeyboardButton("Volver a pendientes", callback_data="ref_list_0")]]
        query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    query.answer("Opcion no reconocida.", show_alert=True)


def reference_assign_location_handler(update, context):
    """
    Recibe un PIN de Telegram para completar coordenadas de una referencia candidata.
    """
    candidate_id = context.user_data.get("ref_assign_candidate_id")
    if not candidate_id:
        return

    reviewer = _get_reference_reviewer(update.effective_user.id)
    if not reviewer["ok"]:
        update.message.reply_text(reviewer["message"])
        context.user_data.pop("ref_assign_candidate_id", None)
        return

    if not update.message or not update.message.location:
        update.message.reply_text("Envia un PIN de ubicacion de Telegram para continuar.")
        return

    row = get_reference_candidate(candidate_id)
    if not row:
        update.message.reply_text("Referencia no encontrada. Usa /referencias nuevamente.")
        context.user_data.pop("ref_assign_candidate_id", None)
        return

    lat = update.message.location.latitude
    lng = update.message.location.longitude
    ok = set_reference_candidate_coords(candidate_id, lat, lng)
    context.user_data.pop("ref_assign_candidate_id", None)

    if not ok:
        update.message.reply_text("No se pudo guardar la ubicacion. Intenta de nuevo con /referencias.")
        return

    keyboard = [
        [
            InlineKeyboardButton("Aprobar", callback_data="ref_approve_{}".format(candidate_id)),
            InlineKeyboardButton("Rechazar", callback_data="ref_reject_{}".format(candidate_id)),
        ],
        [InlineKeyboardButton("Ver referencia", callback_data="ref_view_{}".format(candidate_id))],
        [InlineKeyboardButton("Volver a pendientes", callback_data="ref_list_0")],
    ]
    update.message.reply_text(
        "Ubicacion guardada para la referencia.\n"
        "Ahora puedes aprobarla o rechazarla.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def aliados_pendientes(update, context):
    """Lista aliados PENDING solo para el Administrador de Plataforma."""
    message = update.effective_message
    telegram_id = update.effective_user.id

    if telegram_id != ADMIN_USER_ID:
        message.reply_text("Este comando es solo para el Administrador de Plataforma.")
        return

    try:
        allies = get_pending_allies()
    except Exception as e:
        logger.error("get_pending_allies(): %s", e)
        message.reply_text("⚠️ Error interno al consultar aliados pendientes.")
        return

    if not allies:
        message.reply_text("No hay aliados pendientes por aprobar.")
        return

    for ally in allies:
        ally_id = ally["id"]
        business_name = ally["business_name"]
        owner_name = ally["owner_name"]
        address = ally["address"]
        city = ally["city"]
        barrio = ally["barrio"]
        phone = ally["phone"]
        status = ally["status"]

        texto = (
            "Aliado pendiente:\n"
            "------------------------\n"
            f"ID interno: {ally_id}\n"
            f"Negocio: {business_name}\n"
            f"Dueño: {owner_name}\n"
            f"Teléfono: {phone}\n"
            f"Dirección: {address}, {barrio}, {city}\n"
            f"Estado: {status}\n"
        )

        keyboard = [[
            InlineKeyboardButton("✅ Aprobar", callback_data=f"ally_approve_{ally_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"ally_reject_{ally_id}"),
        ]]

        message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))


def repartidores_pendientes(update, context):
    message = update.effective_message
    user_db_id = get_user_db_id_from_update(update)

    # Permisos: admin de plataforma o admin local
    telegram_id = update.effective_user.id
    es_admin_plataforma_flag = es_admin_plataforma(telegram_id)

    admin_id = None

    if not es_admin_plataforma_flag:
        try:
            user_db_id = get_user_db_id_from_update(update)
            admin = get_admin_by_user_id(user_db_id)

        except Exception:
            admin = None

        if not admin:
            message.reply_text("No tienes permisos para ver repartidores pendientes.")
            return

        admin_id = admin["id"]
        if not admin_id:
            message.reply_text("No se pudo validar tu rol de administrador.")
            return

    # Obtener pendientes según rol
    try:
        if es_admin_plataforma_flag:
            # Combinar: nuevos registros (couriers.status=PENDING) + solicitudes de union (admin_couriers.status=PENDING)
            nuevos = list(get_pending_couriers())
            join_requests = list(get_pending_couriers_by_admin(admin_id))
            seen_ids = set()
            pendientes = []
            for c in nuevos + join_requests:
                try:
                    cid = c["courier_id"]
                except (IndexError, KeyError):
                    cid = None
                if not cid:
                    try:
                        cid = c["id"]
                    except (IndexError, KeyError):
                        cid = None
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    pendientes.append(c)
        else:
            pendientes = get_pending_couriers_by_admin(admin_id)  # por equipo (tabla admin_couriers)
    except Exception as e:
        logger.error("repartidores_pendientes: %s", e)
        message.reply_text("Error consultando repartidores pendientes. Revisa logs del servidor.")
        return

    if not pendientes:
        message.reply_text("No hay repartidores pendientes por aprobar.")
        return

    for c in pendientes:
        # Ideal: que ambas funciones de DB devuelvan (courier_id, full_name, phone, city, barrio)
        try:
            courier_id = c["courier_id"]
        except (IndexError, KeyError):
            courier_id = None
        if not courier_id:
            try:
                courier_id = c["id"]
            except (IndexError, KeyError):
                courier_id = None
        full_name = c["full_name"] or ""
        phone = c["phone"] or ""
        city = c["city"] or ""
        barrio = c["barrio"] or ""

        if not courier_id:
            continue

        texto = (
            "REPARTIDOR PENDIENTE\n"
            f"ID: {courier_id}\n"
            f"Nombre: {full_name}\n"
            f"Teléfono: {phone}\n"
            f"Ciudad: {city}\n"
            f"Barrio: {barrio}"
        )

        if es_admin_plataforma_flag:
            keyboard = [[
                InlineKeyboardButton("✅ Aprobar", callback_data=f"courier_approve_{courier_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"courier_reject_{courier_id}")
            ]]
        else:
            keyboard = [[
                InlineKeyboardButton("✅ Aprobar", callback_data=f"local_courier_approve_{courier_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"local_courier_reject_{courier_id}")
            ], [
                InlineKeyboardButton("⛔ Bloquear", callback_data=f"local_courier_block_{courier_id}")
            ]]

        message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

        # Enviar fotos de verificación de identidad si están disponibles
        courier_full = get_courier_by_id(courier_id)
        if courier_full:
            cedula_front = courier_full.get("cedula_front_file_id") if isinstance(courier_full, dict) else None
            cedula_back = courier_full.get("cedula_back_file_id") if isinstance(courier_full, dict) else None
            selfie = courier_full.get("selfie_file_id") if isinstance(courier_full, dict) else None
            if cedula_front or cedula_back or selfie:
                try:
                    if cedula_front:
                        context.bot.send_photo(chat_id=message.chat_id, photo=cedula_front, caption="Cédula frente")
                    if cedula_back:
                        context.bot.send_photo(chat_id=message.chat_id, photo=cedula_back, caption="Cédula reverso")
                    if selfie:
                        context.bot.send_photo(chat_id=message.chat_id, photo=selfie, caption="Selfie")
                except Exception as e:
                    logger.warning("No se pudieron enviar fotos del repartidor %s: %s", courier_id, e)

        
def admin_menu(update, context):
    """Panel de Administración de Plataforma."""
    user = update.effective_user
    user_db_id = get_user_db_id_from_update(update)

    # Solo el Admin de Plataforma aprobado puede usar este comando
    if not user_has_platform_admin(user.id):
        update.message.reply_text("Acceso restringido: tu Admin de Plataforma no esta APPROVED.")
        return

    texto = (
        "Panel de Administración de Plataforma.\n"
        "¿Qué deseas revisar?"
    )

    keyboard = [
        [InlineKeyboardButton("👥 Gestión de usuarios", callback_data="admin_gestion_usuarios")],
        [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos")],
        [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
        [InlineKeyboardButton("💰 Saldos de todos", callback_data="admin_saldos")],
        [InlineKeyboardButton("Soportes pendientes", callback_data="admin_support_open")],
        [InlineKeyboardButton("Referencias locales", callback_data="admin_ref_candidates")],
        [InlineKeyboardButton("📊 Finanzas", callback_data="admin_finanzas")],
        [InlineKeyboardButton("💳 Recargas", callback_data="plat_rec_menu")],
        [InlineKeyboardButton("📍 Repartidores online", callback_data="config_couriers_online")],
    ]

    update.message.reply_text(
        texto,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def admin_menu_callback(update, context):
    """Maneja los botones del Panel de Administración de Plataforma."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "admin_change_requests":
        return admin_change_requests_list(update, context)

    if data.startswith("admin_pedidos_local_"):
        try:
            admin_id = int(data.replace("admin_pedidos_local_", ""))
        except ValueError:
            query.answer("Error de formato.", show_alert=True)
            return
        return admin_orders_panel(update, context, admin_id, is_platform=False)

    if data == "admin_support_open":
        query.answer()
        _render_support_requests_list(query, offset=0, edit=False)
        return

    if data.startswith("admin_support_list_"):
        query.answer()
        try:
            offset = int(data.replace("admin_support_list_", ""))
        except ValueError:
            query.answer("Error de formato.", show_alert=True)
            return
        _render_support_requests_list(query, offset=max(0, offset), edit=True)
        return

    if data.startswith("admin_support_view_"):
        query.answer()
        parts = data.replace("admin_support_view_", "").split("_")
        if len(parts) != 2:
            query.answer("Error de formato.", show_alert=True)
            return
        try:
            support_id = int(parts[0])
            offset = int(parts[1])
        except ValueError:
            query.answer("Error de formato.", show_alert=True)
            return
        _render_support_request_detail(query, support_id, max(0, offset))
        return

    # Gestión de usuarios (solo Admin Plataforma)
    if data == "admin_gestion_usuarios":
        if not user_has_platform_admin(user_id):
            query.answer("Solo el Administrador de Plataforma puede usar este menú.", show_alert=True)
            return
        query.answer()
        keyboard = [
            [InlineKeyboardButton("👤 Aliados pendientes", callback_data="admin_aliados_pendientes")],
            [InlineKeyboardButton("🚚 Repartidores pendientes", callback_data="admin_repartidores_pendientes")],
            [InlineKeyboardButton("🧑‍💼 Gestionar administradores", callback_data="admin_administradores")],
            [InlineKeyboardButton("Ver totales de registros", callback_data="config_totales")],
            [InlineKeyboardButton("Gestionar aliados", callback_data="config_gestion_aliados")],
            [InlineKeyboardButton("Gestionar repartidores", callback_data="config_gestion_repartidores")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Gestión de usuarios. ¿Qué deseas hacer?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Configuraciones (Admin Plataforma ve todo; Admin local ve solo Configurar pagos)
    if data == "admin_config":
        query.answer()
        is_platform = user_has_platform_admin(user_id)
        keyboard = []
        if is_platform:
            keyboard.append([InlineKeyboardButton("💰 Tarifas", callback_data="config_tarifas")])
        keyboard.append([InlineKeyboardButton("💳 Configurar pagos", callback_data="config_pagos")])
        if is_platform:
            keyboard.append([InlineKeyboardButton("Solicitudes de cambio", callback_data="config_change_requests")])
        if is_platform:
            keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_volver_panel")])
        else:
            keyboard.append([InlineKeyboardButton("Cerrar", callback_data="config_cerrar")])
        query.edit_message_text(
            "Configuraciones. ¿Qué deseas ajustar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Solo el Admin de Plataforma aprobado puede usar estos botones
    if not user_has_platform_admin(user_id):
        query.answer("Solo el Administrador de Plataforma puede usar este menú.", show_alert=True)
        return

    # Botón: Aliados pendientes (Plataforma)
    if data == "admin_aliados_pendientes":
        query.answer()
        aliados_pendientes(update, context)
        return

    # Botón: Repartidores pendientes (Plataforma)
    if data == "admin_repartidores_pendientes":
        query.answer()
        repartidores_pendientes(update, context)
        return

    if data == "admin_ref_candidates":
        query.answer()
        _render_reference_candidates(query, offset=0, edit=True)
        return

    # Botón: Gestionar administradores (submenú)
    if data == "admin_administradores":
        query.answer()
        keyboard = [
            [InlineKeyboardButton("📋 Administradores registrados", callback_data="admin_admins_registrados")],
            [InlineKeyboardButton("⏳ Administradores pendientes", callback_data="admin_admins_pendientes")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Gestión de administradores.\n¿Qué deseas hacer?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Submenú admins: pendientes
    if data == "admin_admins_pendientes":
        query.answer()
        try:
            admins_pendientes(update, context)
        except Exception as e:
            logger.error("admins_pendientes: %s", e)
            query.edit_message_text(
                "Error mostrando administradores pendientes. Revisa logs.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")]
                ])
            )
        return

    # Submenú admins: listar administradores registrados
    if data == "admin_admins_registrados":
        query.answer()
        try:
            admins = get_all_admins()

            if not admins:
                query.edit_message_text(
                    "No hay administradores registrados en este momento.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")]
                    ])
                )
                return

            keyboard = []
            for a in admins:
                adm_id = a['id']
                full_name = a['full_name']
                team_name = a['team_name'] or "-"
                status = a['status']
                keyboard.append([InlineKeyboardButton(
                    "ID {} - {} | {} ({})".format(adm_id, full_name, team_name, status),
                    callback_data="admin_ver_admin_{}".format(adm_id)
                )])

            keyboard.append([InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")])
            query.edit_message_text(
                "Administradores registrados:\n\nToca un admin para ver detalles.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error("admin_admins_registrados: %s", e)
            query.edit_message_text(
                "Error al cargar administradores. Revisa los logs.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")]
                ])
            )
        return

    # Ver detalle de un admin
    if data.startswith("admin_ver_admin_"):
        query.answer()
        adm_id = int(data.replace("admin_ver_admin_", ""))
        admin_obj = get_admin_by_id(adm_id)

        if not admin_obj:
            query.edit_message_text(
                "Admin no encontrado.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver a la lista", callback_data="admin_admins_registrados")]
                ])
            )
            return

        # Datos del admin objetivo
        adm_full_name = admin_obj["full_name"] or "-"
        adm_phone = admin_obj["phone"] or "-"
        adm_city = admin_obj["city"] or "-"
        adm_barrio = admin_obj["barrio"] or "-"
        adm_team_name = admin_obj["team_name"] or "-"
        adm_document = admin_obj["document_number"] or "-"
        adm_team_code = admin_obj["team_code"] or "-"
        adm_status = admin_obj["status"] or "-"

        # Tipo de admin
        tipo_admin = "PLATAFORMA" if adm_team_code == "PLATFORM" else "ADMIN LOCAL"

        # Contadores
        num_couriers = count_admin_couriers(adm_id)
        num_couriers_balance = count_admin_couriers_with_min_balance(adm_id, 5000)
        perm = get_admin_reference_validator_permission(adm_id)
        perm_status = perm["status"] if perm else "INACTIVE"
        reset_state = get_admin_reset_state_by_id(adm_id)
        reset_status = _registration_reset_status_label(reset_state)

        residence_address = admin_obj["residence_address"]
        residence_lat = admin_obj["residence_lat"]
        residence_lng = admin_obj["residence_lng"]
        if residence_lat is not None and residence_lng is not None:
            residence_location = "{}, {}".format(residence_lat, residence_lng)
            maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(residence_lat, residence_lng)
        else:
            residence_location = "No disponible"
            maps_line = ""

        texto = (
            "ADMIN ID: {}\n"
            "Nombre: {}\n"
            "Equipo: {}\n"
            "Team code: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Telefono: {}\n"
            "Documento: {}\n"
            "Estado: {}\n"
            "Tipo: {}\n"
            "Dirección residencia: {}\n"
            "Ubicación residencia: {}\n"
            "{}\n"
            "\n"
            "CONTADORES:\n"
            "Mensajeros vinculados: {}\n"
            "Mensajeros con saldo >= 5000: {}\n"
            "Reinicio de registro: {}"
        ).format(
            adm_id, adm_full_name, adm_team_name, adm_team_code,
            adm_city, adm_barrio, adm_phone, adm_document, adm_status, tipo_admin,
            residence_address or "No registrada",
            residence_location,
            maps_line,
            num_couriers, num_couriers_balance, reset_status
        )
        texto += "\nPermiso validar referencias: {}".format(perm_status)

        keyboard = []

        # Verificar si el usuario actual es Admin Plataforma
        es_plataforma = user_has_platform_admin(query.from_user.id)

        # Solo Admin Plataforma puede cambiar status
        # Y no puede modificar a otro admin PLATFORM (proteger)
        if es_plataforma and adm_team_code != "PLATFORM":
            if adm_status == "PENDING":
                keyboard.append([
                    InlineKeyboardButton("✅ Aprobar", callback_data="admin_set_status_{}_APPROVED".format(adm_id)),
                    InlineKeyboardButton("❌ Rechazar", callback_data="admin_set_status_{}_REJECTED".format(adm_id)),
                ])
            if adm_status == "APPROVED":
                keyboard.append([InlineKeyboardButton("⛔ Desactivar", callback_data="admin_set_status_{}_INACTIVE".format(adm_id))])
                if perm_status == "APPROVED":
                    keyboard.append([InlineKeyboardButton("Quitar permiso validar referencias", callback_data="admin_refperm_{}_INACTIVE".format(adm_id))])
                else:
                    keyboard.append([InlineKeyboardButton("Dar permiso validar referencias", callback_data="admin_refperm_{}_APPROVED".format(adm_id))])
            if adm_status == "INACTIVE":
                keyboard.append([InlineKeyboardButton("✅ Activar", callback_data="admin_set_status_{}_APPROVED".format(adm_id))])
                _append_registration_reset_button(keyboard, "admin", adm_id, adm_status, reset_state)
            # REJECTED: sin botones de accion (estado terminal)

        keyboard.append([InlineKeyboardButton("⬅️ Volver a la lista", callback_data="admin_admins_registrados")])
        keyboard.append([InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Cambiar status de un admin (solo Admin Plataforma)
    if data.startswith("admin_refperm_"):
        payload = data.replace("admin_refperm_", "")
        parts = payload.rsplit("_", 1)
        if len(parts) != 2:
            query.answer("Formato invalido", show_alert=True)
            return

        try:
            adm_id = int(parts[0])
        except Exception:
            query.answer("Admin invalido", show_alert=True)
            return

        new_status = parts[1]
        if new_status not in ("APPROVED", "INACTIVE"):
            query.answer("Estado no valido", show_alert=True)
            return

        target = get_admin_by_id(adm_id)
        if not target:
            query.answer("Admin no encontrado", show_alert=True)
            return
        if target["team_code"] == "PLATFORM":
            query.answer("No aplica para Admin Plataforma", show_alert=True)
            return
        if new_status == "APPROVED" and target["status"] != "APPROVED":
            query.answer("Solo admins locales APPROVED pueden recibir este permiso.", show_alert=True)
            return

        actor_user = get_user_by_telegram_id(query.from_user.id)
        actor_admin = get_admin_by_user_id(actor_user["id"]) if actor_user else None
        if not actor_admin:
            query.answer("No se encontro tu perfil admin.", show_alert=True)
            return

        set_admin_reference_validator_permission(
            adm_id,
            new_status,
            granted_by_admin_id=actor_admin["id"],
        )
        action_text = "otorgado" if new_status == "APPROVED" else "revocado"
        query.edit_message_text(
            "Permiso de validacion de referencias {} para admin {}.".format(action_text, adm_id),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver al admin", callback_data="admin_ver_admin_{}".format(adm_id))],
                [InlineKeyboardButton("Volver al panel", callback_data="admin_volver_panel")],
            ])
        )
        return

    if data.startswith("admin_set_status_"):
        # Formato: admin_set_status_{id}_{STATUS}
        parts = data.replace("admin_set_status_", "").rsplit("_", 1)
        if len(parts) != 2:
            query.answer("Formato invalido")
            return

        adm_id = int(parts[0])
        nuevo_status = parts[1]

        # Validar que sea un status permitido
        if nuevo_status not in ("APPROVED", "INACTIVE", "REJECTED"):
            query.answer("Status no valido")
            return

        # Verificar permisos: el usuario actual debe ser Admin Plataforma aprobado
        es_plataforma = user_has_platform_admin(query.from_user.id)

        if not es_plataforma:
            query.answer("Sin permisos para esta accion")
            return

        # Verificar que el admin objetivo no sea PLATFORM (proteger)
        admin_obj = get_admin_by_id(adm_id)
        if not admin_obj:
            query.answer("Admin no encontrado")
            return

        if admin_obj["team_code"] == "PLATFORM":
            query.answer("No puedes modificar a un admin de plataforma")
            return

        # Aplicar cambio
        was_reactivated = bool(admin_obj["status"] in ("INACTIVE", "REJECTED"))
        update_admin_status_by_id(adm_id, nuevo_status, changed_by=f"tg:{update.effective_user.id}")
        if nuevo_status == "APPROVED":
            try:
                _notify_admin_local_welcome(context, adm_id, reactivated=was_reactivated)
            except Exception as e:
                logger.warning("No se pudo notificar onboarding de admin local: %s", e)
        query.answer("Estado actualizado a {}".format(nuevo_status))

        # Recargar el detalle
        admin_obj = get_admin_by_id(adm_id)
        adm_full_name = admin_obj["full_name"] or "-"
        adm_phone = admin_obj["phone"] or "-"
        adm_city = admin_obj["city"] or "-"
        adm_barrio = admin_obj["barrio"] or "-"
        adm_team_name = admin_obj["team_name"] or "-"
        adm_document = admin_obj["document_number"] or "-"
        adm_team_code = admin_obj["team_code"] or "-"
        adm_status = admin_obj["status"] or "-"

        tipo_admin = "PLATAFORMA" if adm_team_code == "PLATFORM" else "ADMIN LOCAL"
        num_couriers = count_admin_couriers(adm_id)
        num_couriers_balance = count_admin_couriers_with_min_balance(adm_id, 5000)
        perm = get_admin_reference_validator_permission(adm_id)
        perm_status = perm["status"] if perm else "INACTIVE"
        reset_state = get_admin_reset_state_by_id(adm_id)
        reset_status = _registration_reset_status_label(reset_state)

        texto = (
            "ADMIN ID: {}\n"
            "Nombre: {}\n"
            "Equipo: {}\n"
            "Team code: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Telefono: {}\n"
            "Documento: {}\n"
            "Estado: {}\n"
            "Tipo: {}\n\n"
            "CONTADORES:\n"
            "Mensajeros vinculados: {}\n"
            "Mensajeros con saldo >= 5000: {}\n\n"
            "Reinicio de registro: {}\n"
            "Estado actualizado a {}"
        ).format(
            adm_id, adm_full_name, adm_team_name, adm_team_code,
            adm_city, adm_barrio, adm_phone, adm_document, adm_status, tipo_admin,
            num_couriers, num_couriers_balance, reset_status, nuevo_status
        )
        texto += "\nPermiso validar referencias: {}".format(perm_status)

        keyboard = []
        # El admin objetivo no es PLATFORM, mostrar botones segun nuevo status
        if adm_status == "PENDING":
            keyboard.append([
                InlineKeyboardButton("✅ Aprobar", callback_data="admin_set_status_{}_APPROVED".format(adm_id)),
                InlineKeyboardButton("❌ Rechazar", callback_data="admin_set_status_{}_REJECTED".format(adm_id)),
            ])
        if adm_status == "APPROVED":
            keyboard.append([InlineKeyboardButton("⛔ Desactivar", callback_data="admin_set_status_{}_INACTIVE".format(adm_id))])
            if perm_status == "APPROVED":
                keyboard.append([InlineKeyboardButton("Quitar permiso validar referencias", callback_data="admin_refperm_{}_INACTIVE".format(adm_id))])
            else:
                keyboard.append([InlineKeyboardButton("Dar permiso validar referencias", callback_data="admin_refperm_{}_APPROVED".format(adm_id))])
        if adm_status == "INACTIVE":
            keyboard.append([InlineKeyboardButton("✅ Activar", callback_data="admin_set_status_{}_APPROVED".format(adm_id))])
            _append_registration_reset_button(keyboard, "admin", adm_id, adm_status, reset_state)
        # REJECTED: sin botones de accion (estado terminal)
        keyboard.append([InlineKeyboardButton("⬅️ Volver a la lista", callback_data="admin_admins_registrados")])
        keyboard.append([InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("admin_reset_"):
        payload = data.replace("admin_reset_", "")
        parts = payload.rsplit("_", 1)
        if len(parts) != 2:
            query.answer("Formato invalido", show_alert=True)
            return
        action = parts[0]
        try:
            adm_id = int(parts[1])
        except Exception:
            query.answer("Admin invalido", show_alert=True)
            return

        admin_obj = get_admin_by_id(adm_id)
        if not admin_obj:
            query.answer("Admin no encontrado", show_alert=True)
            return
        if admin_obj["team_code"] == "PLATFORM":
            query.answer("No aplica para Admin Plataforma", show_alert=True)
            return

        reset_state = get_admin_reset_state_by_id(adm_id)
        if action == "enable":
            if admin_obj["status"] != "INACTIVE":
                query.answer("Primero debe estar INACTIVE para autorizar reinicio.", show_alert=True)
                return
            if reset_state and reset_state.get("registration_reset_active"):
                query.answer("Este reinicio ya está autorizado.", show_alert=True)
                return
            try:
                platform_enable_admin_registration_reset(query.from_user.id, adm_id, note="Autorizado por plataforma")
            except PermissionError as e:
                query.answer(str(e), show_alert=True)
                return
            except ValueError as e:
                query.answer(str(e), show_alert=True)
                return
            query.edit_message_text(
                "Reinicio de registro autorizado correctamente.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Volver al admin", callback_data="admin_ver_admin_{}".format(adm_id))],
                    [InlineKeyboardButton("Volver al panel", callback_data="admin_volver_panel")],
                ])
            )
            return

        if action == "clear":
            if not reset_state or not reset_state.get("registration_reset_active"):
                if reset_state and reset_state.get("registration_reset_consumed_at"):
                    query.answer("Este reinicio ya fue consumido.", show_alert=True)
                else:
                    query.answer("No hay un reinicio activo para revocar.", show_alert=True)
                return
            try:
                platform_clear_admin_registration_reset(query.from_user.id, adm_id)
            except PermissionError as e:
                query.answer(str(e), show_alert=True)
                return
            except ValueError as e:
                query.answer(str(e), show_alert=True)
                return
            query.edit_message_text(
                "Reinicio de registro revocado correctamente.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Volver al admin", callback_data="admin_ver_admin_{}".format(adm_id))],
                    [InlineKeyboardButton("Volver al panel", callback_data="admin_volver_panel")],
                ])
            )
            return

        query.answer("Acción no reconocida", show_alert=True)
        return

    # Volver al panel (reconstruye el teclado sin llamar admin_menu, para evitar update.message)
    if data == "admin_volver_panel":
        query.answer()

        texto = (
            "Panel de Administración de Plataforma.\n"
            "¿Qué deseas revisar?"
        )
        keyboard = [
            [InlineKeyboardButton("👥 Gestión de usuarios", callback_data="admin_gestion_usuarios")],
            [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos")],
            [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
            [InlineKeyboardButton("💰 Saldos de todos", callback_data="admin_saldos")],
            [InlineKeyboardButton("Referencias locales", callback_data="admin_ref_candidates")],
            [InlineKeyboardButton("📊 Finanzas", callback_data="admin_finanzas")],
            [InlineKeyboardButton("💳 Recargas", callback_data="plat_rec_menu")],
        ]

        query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos (submenu principal)
    if data == "admin_saldos":
        query.answer()
        keyboard = [
            [InlineKeyboardButton("🚚 Repartidores", callback_data="admin_saldos_couriers")],
            [InlineKeyboardButton("👤 Aliados", callback_data="admin_saldos_allies")],
            [InlineKeyboardButton("🧑‍💼 Admins", callback_data="admin_saldos_admins_0")],
            [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Saldos de todos.\n¿Qué deseas revisar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: equipos (repartidores)
    if data == "admin_saldos_couriers":
        query.answer()
        teams = list_approved_admin_teams(include_platform=True)
        if not teams:
            query.edit_message_text(
                "No hay equipos aprobados disponibles.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")]
                ])
            )
            return

        keyboard = []
        for t in teams:
            admin_id = t["id"]
            team_name = t["team_name"] or "-"
            team_code = t["team_code"] or "-"
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(admin_id, team_name, team_code),
                callback_data="admin_saldos_team_couriers_{}_0".format(admin_id)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")])
        query.edit_message_text(
            "Equipos aprobados (Repartidores).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: equipos (aliados)
    if data == "admin_saldos_allies":
        query.answer()
        teams = list_approved_admin_teams(include_platform=True)
        if not teams:
            query.edit_message_text(
                "No hay equipos aprobados disponibles.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")]
                ])
            )
            return

        keyboard = []
        for t in teams:
            admin_id = t["id"]
            team_name = t["team_name"] or "-"
            team_code = t["team_code"] or "-"
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(admin_id, team_name, team_code),
                callback_data="admin_saldos_team_allies_{}_0".format(admin_id)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")])
        query.edit_message_text(
            "Equipos aprobados (Aliados).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: lista de admins con paginación
    if data.startswith("admin_saldos_admins_"):
        query.answer()
        try:
            offset = int(data.replace("admin_saldos_admins_", ""))
        except Exception:
            offset = 0
        teams = list_approved_admin_teams(include_platform=True)
        page = teams[offset:offset + 20]
        if not page:
            query.edit_message_text(
                "No hay administradores aprobados disponibles.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")]
                ])
            )
            return

        keyboard = []
        for t in page:
            admin_id = t["id"]
            team_name = t["team_name"] or "-"
            team_code = t["team_code"] or "-"
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(admin_id, team_name, team_code),
                callback_data="admin_saldos_member_admin_{}_{}".format(admin_id, offset)
            )])

        if offset > 0:
            keyboard.append([InlineKeyboardButton(
                "⬅️ Anterior", callback_data="admin_saldos_admins_{}".format(offset - 20)
            )])
        if len(page) == 20 and (offset + 20) < len(teams):
            keyboard.append([InlineKeyboardButton(
                "➡️ Siguiente", callback_data="admin_saldos_admins_{}".format(offset + 20)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos")])

        query.edit_message_text(
            "Administradores aprobados (Saldos).",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: lista de repartidores por admin con paginación
    if data.startswith("admin_saldos_team_couriers_"):
        query.answer()
        parts = data.replace("admin_saldos_team_couriers_", "").split("_")
        admin_id = int(parts[0]) if parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        links = list_courier_links_by_admin(admin_id, limit=20, offset=offset)

        if not links:
            query.edit_message_text(
                "No hay repartidores vinculados a este admin.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_couriers")]
                ])
            )
            return

        keyboard = []
        for idx, r in enumerate(links):
            courier_id = r["courier_id"]
            courier_name = r["full_name"] or "-"
            balance = r["balance"] or 0
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} | saldo {}".format(courier_id, courier_name, balance),
                callback_data="admin_saldos_member_courier_{}_{}_{}".format(admin_id, offset, idx)
            )])

        if offset > 0:
            keyboard.append([InlineKeyboardButton(
                "⬅️ Anterior", callback_data="admin_saldos_team_couriers_{}_{}".format(admin_id, offset - 20)
            )])
        if len(links) == 20:
            keyboard.append([InlineKeyboardButton(
                "➡️ Siguiente", callback_data="admin_saldos_team_couriers_{}_{}".format(admin_id, offset + 20)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_couriers")])

        query.edit_message_text(
            "Repartidores vinculados (admin ID {}).".format(admin_id),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: lista de aliados por admin con paginación
    if data.startswith("admin_saldos_team_allies_"):
        query.answer()
        parts = data.replace("admin_saldos_team_allies_", "").split("_")
        admin_id = int(parts[0]) if parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        links = list_ally_links_by_admin(admin_id, limit=20, offset=offset)

        if not links:
            query.edit_message_text(
                "No hay aliados vinculados a este admin.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_allies")]
                ])
            )
            return

        keyboard = []
        for idx, r in enumerate(links):
            ally_id = r["ally_id"]
            business_name = r["business_name"] or "-"
            balance = r["balance"] or 0
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} | saldo {}".format(ally_id, business_name, balance),
                callback_data="admin_saldos_member_ally_{}_{}_{}".format(admin_id, offset, idx)
            )])

        if offset > 0:
            keyboard.append([InlineKeyboardButton(
                "⬅️ Anterior", callback_data="admin_saldos_team_allies_{}_{}".format(admin_id, offset - 20)
            )])
        if len(links) == 20:
            keyboard.append([InlineKeyboardButton(
                "➡️ Siguiente", callback_data="admin_saldos_team_allies_{}_{}".format(admin_id, offset + 20)
            )])
        keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_allies")])

        query.edit_message_text(
            "Aliados vinculados (admin ID {}).".format(admin_id),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Saldos de todos: detalle repartidor
    if data.startswith("admin_saldos_member_courier_"):
        query.answer()
        parts = data.replace("admin_saldos_member_courier_", "").split("_")
        admin_id = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        idx = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else -1
        links = list_courier_links_by_admin(admin_id, limit=20, offset=offset)
        if idx < 0 or idx >= len(links):
            query.edit_message_text(
                "No se pudo cargar el detalle del repartidor.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_couriers_{}_{}".format(admin_id, offset))]
                ])
            )
            return

        r = links[idx]
        courier_id = r["courier_id"]
        courier_name = r["full_name"] or "-"
        phone = r["phone"] or "-"
        city = r["city"] or "-"
        barrio = r["barrio"] or "-"
        balance = r["balance"] or 0
        texto = (
            "Repartidor ID: {}\n"
            "Nombre: {}\n"
            "Telefono: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Saldo por vínculo: {}"
        ).format(courier_id, courier_name, phone, city, barrio, balance)
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_couriers_{}_{}".format(admin_id, offset))],
            [InlineKeyboardButton("⬅️ Volver a equipos", callback_data="admin_saldos_couriers")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Saldos de todos: detalle aliado
    if data.startswith("admin_saldos_member_ally_"):
        query.answer()
        parts = data.replace("admin_saldos_member_ally_", "").split("_")
        admin_id = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        idx = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else -1
        links = list_ally_links_by_admin(admin_id, limit=20, offset=offset)
        if idx < 0 or idx >= len(links):
            query.edit_message_text(
                "No se pudo cargar el detalle del aliado.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_allies_{}_{}".format(admin_id, offset))]
                ])
            )
            return

        r = links[idx]
        ally_id = r["ally_id"]
        business_name = r["business_name"] or "-"
        owner_name = r["owner_name"] or "-"
        phone = r["phone"] or "-"
        city = r["city"] or "-"
        barrio = r["barrio"] or "-"
        balance = r["balance"] or 0
        parking_enabled = get_ally_parking_fee_enabled(ally_id)
        texto = (
            "Aliado ID: {}\n"
            "Negocio: {}\n"
            "Propietario: {}\n"
            "Telefono: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Saldo por vínculo: {}\n"
            "Cobro parqueo dificil: {}"
        ).format(ally_id, business_name, owner_name, phone, city, barrio, balance,
                 "ACTIVO" if parking_enabled else "INACTIVO")
        keyboard = [
            [InlineKeyboardButton(
                "{} Cobro parqueo dificil".format("Desactivar" if parking_enabled else "Activar"),
                callback_data="admin_local_parking_toggle_{}_{}_{}_{}" .format(ally_id, admin_id, offset, idx)
            )],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_allies_{}_{}".format(admin_id, offset))],
            [InlineKeyboardButton("⬅️ Volver a equipos", callback_data="admin_saldos_allies")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Saldos de todos: detalle admin
    if data.startswith("admin_saldos_member_admin_"):
        query.answer()
        parts = data.replace("admin_saldos_member_admin_", "").split("_")
        admin_id = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
        offset = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        admin_obj = get_admin_by_id(admin_id)
        if not admin_obj:
            query.edit_message_text(
                "Admin no encontrado.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_admins_{}".format(offset))]
                ])
            )
            return

        adm_full_name = admin_obj["full_name"] or "-"
        adm_team_name = admin_obj["team_name"] or "-"
        adm_team_code = admin_obj["team_code"] or "-"
        adm_status = admin_obj["status"] or "-"
        balance = get_admin_balance(admin_id)
        texto = (
            "ADMIN ID: {}\n"
            "Nombre: {}\n"
            "Equipo: {}\n"
            "Team code: {}\n"
            "Estado: {}\n"
            "Saldo actual: {}"
        ).format(admin_id, adm_full_name, adm_team_name, adm_team_code, adm_status, balance)
        keyboard = [
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_admins_{}".format(offset))],
            [InlineKeyboardButton("⬅️ Volver a Saldos", callback_data="admin_saldos")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Botones aún no implementados (placeholders)
    if data == "admin_pedidos":
        user_db_id = get_user_db_id_from_update(update)
        admin = get_admin_by_user_id(user_db_id)
        if admin:
            admin_id = admin["id"]
            return admin_orders_panel(update, context, admin_id, is_platform=True)
        query.answer("No se encontro tu perfil de admin.", show_alert=True)
        return


    if data == "admin_finanzas":
        query.answer()
        admin = get_admin_by_user_id(get_user_db_id_from_update(update))
        if not admin:
            query.edit_message_text("No se encontro tu perfil de administrador.")
            return
        balance = get_admin_balance(admin["id"])
        keyboard = [
            [InlineKeyboardButton("Registrar ingreso externo", callback_data="ingreso_iniciar")],
            [InlineKeyboardButton("Volver al Panel", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Finanzas de Plataforma.\n\n"
            "Saldo disponible: ${:,}\n\n"
            "Registra cada pago recibido (efectivo, Nequi, transferencia) "
            "antes de aprobar recargas.".format(balance),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Ver admin pendiente (detalle)
    if data.startswith("admin_ver_pendiente_"):
        query.answer()
        admin_ver_pendiente(update, context)
        return

    # Aprobar admin local
    if data.startswith("admin_aprobar_"):
        query.answer()
        admin_id = int(data.split("_")[-1])

        update_admin_status_by_id(admin_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")

        try:
            _notify_admin_local_welcome(context, admin_id, reactivated=False)
        except Exception as e:
            logger.warning("No se pudo notificar al admin aprobado: %s", e)

        query.edit_message_text(
            "✅ Administrador aprobado correctamente.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver", callback_data="admin_admins_pendientes")]
            ])
        )
        return

    # Rechazar admin local
    if data.startswith("admin_rechazar_"):
        query.answer()
        admin_id = int(data.split("_")[-1])

        update_admin_status_by_id(admin_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")

        query.edit_message_text(
            "❌ Administrador rechazado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver", callback_data="admin_admins_pendientes")]
            ])
        )
        return

    # Por si llega algo raro
    query.answer("Opción no reconocida.", show_alert=True)


def volver_menu_global(update, context):
    """Handler global para 'Cancelar' o 'Volver al menu' fuera de conversaciones."""
    try:
        context.user_data.clear()
    except Exception:
        pass
    show_main_menu(update, context, "Menu principal. Selecciona una opcion:")


# ----- COTIZADOR INTERNO -----

def courier_pick_admin_callback(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    user_db_id = context.user_data.get("courier_registration_user_id")

    # Opción legacy: no elegir admin -> asignar por defecto a Plataforma
    if data == "courier_pick_admin_none":
        if not user_db_id:
            query.edit_message_text(
                "No encontré tus datos recientes para vincularte a un equipo.\n"
                "Intenta /soy_repartidor de nuevo."
            )
            context.user_data.clear()
            return

        platform_admin = get_platform_admin()
        if not platform_admin:
            query.edit_message_text(
                "No existe equipo de Plataforma para vincularte.\n"
                "Contacta al administrador."
            )
            context.user_data.clear()
            return

        try:
            platform_admin_id = platform_admin["id"]
            courier_data = _create_or_reset_courier_from_context(context, user_db_id)
            courier_id = courier_data["courier_id"]
            create_admin_courier_link(platform_admin_id, courier_id)
        except Exception as e:
            logger.error("create_admin_courier_link PLATFORM: %s", e)
            query.edit_message_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
            context.user_data.clear()
            return

        try:
            context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=(
                    "Nuevo registro de REPARTIDOR pendiente:\n\n"
                    "Nombre: {}\n"
                    "Cedula: {}\n"
                    "Telefono: {}\n"
                    "Ciudad: {}\n"
                    "Barrio: {}\n"
                    "Placa: {}\n"
                    "Tipo de moto: {}\n"
                    "Equipo elegido: PLATAFORMA (PLATFORM)\n\n"
                    "Usa /admin para revisarlo."
                ).format(
                    courier_data["full_name"],
                    courier_data["id_number"],
                    courier_data["phone"],
                    courier_data["city"],
                    courier_data["barrio"],
                    courier_data["plate"],
                    courier_data["bike_type"],
                )
            )
            _schedule_important_alerts(
                context,
                alert_key="courier_registration_{}".format(courier_id),
                chat_id=ADMIN_USER_ID,
                reminder_text=(
                    "Recordatorio importante:\n"
                    "El registro de repartidor #{} sigue pendiente.\n"
                    "Revisa /repartidores_pendientes o /admin."
                ).format(courier_id),
            )
        except Exception as e:
            logger.warning("No se pudo notificar al admin plataforma: %s", e)

        query.edit_message_text(
            "Perfecto. Quedaste vinculado al equipo de Plataforma.\n"
            "Tu vínculo quedó en estado PENDING hasta aprobación."
        )
        context.user_data.clear()
        return

    # Validación básica del callback
    if not data.startswith("courier_pick_admin_"):
        query.edit_message_text("Opción no reconocida.")
        return

    if not user_db_id:
        query.edit_message_text(
            "No encontré tus datos recientes para vincularte a un equipo.\n"
            "Intenta /soy_repartidor de nuevo."
        )
        context.user_data.clear()
        return

    # Extraer admin_id
    try:
        admin_id = int(data.split("_")[-1])
    except Exception:
        query.edit_message_text("Error leyendo la opción seleccionada. Intenta de nuevo.")
        return

    # Crear vínculo PENDING en admin_couriers
    try:
        courier_data = _create_or_reset_courier_from_context(context, user_db_id)
        courier_id = courier_data["courier_id"]
        create_admin_courier_link(admin_id, courier_id)
    except Exception as e:
        logger.error("create_admin_courier_link: %s", e)
        query.edit_message_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
        context.user_data.clear()
        return

    # Notificar a plataforma y al admin local (sin depender de get_user_by_id)
    admin_telegram_id = None
    admin_team_name = "Equipo"
    admin_team_code = ""
    try:
        admin = get_admin_by_id(admin_id)

        # Heurística:
        # - si admin[1] parece un Telegram ID (muy grande), lo usamos como chat_id
        # - si no, NO rompemos el flujo (solo omitimos notificación)
        admin_user_field = admin.get("user_id") if isinstance(admin, dict) else admin["user_id"]

        if admin_user_field is not None:
            try:
                admin_user_field_int = int(admin_user_field)
                if admin_user_field_int > 100000000:  # típico telegram_id
                    admin_telegram_id = admin_user_field_int
            except Exception:
                admin_telegram_id = None
        if isinstance(admin, dict):
            admin_team_name = admin.get("team_name") or admin_team_name
            admin_team_code = admin.get("team_code") or admin_team_code

    except Exception as e:
        logger.warning("No se pudo leer admin para notificación: %s", e)

    try:
        context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                "Nuevo registro de REPARTIDOR pendiente:\n\n"
                "Nombre: {}\n"
                "Cedula: {}\n"
                "Telefono: {}\n"
                "Ciudad: {}\n"
                "Barrio: {}\n"
                "Placa: {}\n"
                "Tipo de moto: {}\n"
                "Equipo elegido: {} {}\n\n"
                "Usa /admin para revisarlo."
            ).format(
                courier_data["full_name"],
                courier_data["id_number"],
                courier_data["phone"],
                courier_data["city"],
                courier_data["barrio"],
                courier_data["plate"],
                courier_data["bike_type"],
                admin_team_name,
                f"({admin_team_code})" if admin_team_code else "",
            )
        )
        _schedule_important_alerts(
            context,
            alert_key="courier_registration_{}".format(courier_id),
            chat_id=ADMIN_USER_ID,
            reminder_text=(
                "Recordatorio importante:\n"
                "El registro de repartidor #{} sigue pendiente.\n"
                "Revisa /repartidores_pendientes o /admin."
            ).format(courier_id),
        )
    except Exception as e:
        logger.warning("No se pudo notificar al admin plataforma: %s", e)

    if admin_telegram_id:
        try:
            context.bot.send_message(
                chat_id=admin_telegram_id,
                text=(
                    "Nueva solicitud de repartidor para tu equipo.\n\n"
                    f"Repartidor ID: {courier_id}\n\n"
                    "Entra a /mi_admin para revisar pendientes."
                )
            )
            _schedule_important_alerts(
                context,
                alert_key="team_courier_pending_{}_{}".format(admin_id, courier_id),
                chat_id=admin_telegram_id,
                reminder_text=(
                    "Recordatorio importante:\n"
                    "Tienes un repartidor pendiente de aprobar en tu equipo.\n"
                    "Revisa /mi_admin."
                ),
            )
        except Exception as e:
            logger.warning("No se pudo notificar al admin local: %s", e)

    query.edit_message_text(
        "Listo. Tu solicitud fue enviada. Quedas PENDIENTE de aprobación."
    )
    context.user_data.clear()


def admins_pendientes(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    # Seguridad: solo Admin de Plataforma
    if user_id != ADMIN_USER_ID:
        query.answer("No tienes permisos para esto.", show_alert=True)
        return

    # Responder el callback para evitar “cargando…”
    query.answer()

    try:
        admins = get_pending_admins()
    except Exception as e:
        logger.error("get_pending_admins: %s", e)
        query.edit_message_text(
            "Error consultando administradores pendientes. Revisa logs.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver al Panel", callback_data="admin_volver_panel")]
            ])
        )
        return

    if not admins:
        query.edit_message_text(
            "No hay administradores pendientes en este momento.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver al Panel", callback_data="admin_volver_panel")]
            ])
        )
        return

    keyboard = []
    for admin in admins:
        admin_id = admin["id"]
        full_name = admin["full_name"]
        city = admin["city"]

        keyboard.append([
            InlineKeyboardButton(
                "ID {} - {} ({})".format(admin_id, full_name, city),
                callback_data="admin_ver_pendiente_{}".format(admin_id)
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅ Volver al Panel", callback_data="admin_volver_panel")])

    query.edit_message_text(
        "Administradores pendientes de aprobación:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    

def admin_ver_pendiente(update, context):
    query = update.callback_query
    user_id = query.from_user.id

    if user_id != ADMIN_USER_ID:
        query.answer("No tienes permisos.", show_alert=True)
        return

    admin_id = int(query.data.split("_")[-1])
    admin = get_admin_by_id(admin_id)

    if not admin:
        query.edit_message_text("Administrador no encontrado.")
        return

    residence_address = admin["residence_address"]
    residence_lat = admin["residence_lat"]
    residence_lng = admin["residence_lng"]
    if residence_lat is not None and residence_lng is not None:
        residence_location = "{}, {}".format(residence_lat, residence_lng)
        maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(residence_lat, residence_lng)
    else:
        residence_location = "No disponible"
        maps_line = ""

    texto = (
        "Administrador pendiente:\n\n"
        f"ID: {admin['id']}\n"
        f"Nombre: {admin['full_name']}\n"
        f"Teléfono: {admin['phone']}\n"
        f"Ciudad: {admin['city']}\n"
        f"Barrio: {admin['barrio']}\n"
        f"Equipo: {admin['team_name'] or '-'}\n"
        f"Documento: {admin['document_number'] or '-'}\n"
        f"Estado: {admin['status']}\n"
        "Residencia: {}\n"
        "Ubicación residencia: {}\n"
        "{}"
    ).format(
        residence_address or "No registrada",
        residence_location,
        maps_line
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Aprobar", callback_data=f"admin_aprobar_{admin_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"admin_rechazar_{admin_id}")
        ],
        [InlineKeyboardButton("⬅ Volver", callback_data="admin_admins_pendientes")]
    ]

    query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

    # Enviar fotos de verificación de identidad si están disponibles
    cedula_front = admin["cedula_front_file_id"]
    cedula_back = admin["cedula_back_file_id"]
    selfie = admin["selfie_file_id"]
    if cedula_front or cedula_back or selfie:
        try:
            if cedula_front:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_front, caption="Cédula frente")
            if cedula_back:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_back, caption="Cédula reverso")
            if selfie:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=selfie, caption="Selfie")
        except Exception as e:
            logger.warning("No se pudieron enviar fotos del admin %s: %s", admin_id, e)

def admin_aprobar_rechazar_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    # Solo Admin de Plataforma
    if user_id != ADMIN_USER_ID:
        query.answer("No tienes permisos.", show_alert=True)
        return

    partes = data.split("_")  # admin_aprobar_12
    if len(partes) != 3:
        query.answer("Datos inválidos.", show_alert=True)
        return

    _, accion, admin_id_str = partes

    try:
        admin_id = int(admin_id_str)
    except ValueError:
        query.answer("ID inválido.", show_alert=True)
        return

    if accion == "aprobar":
        admin_actual = get_admin_by_id(admin_id)
        was_reactivated = bool(admin_actual and admin_actual["status"] in ("INACTIVE", "REJECTED"))
        try:
            update_admin_status_by_id(admin_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            logger.error("update_admin_status_by_id APPROVED: %s", e)
            query.edit_message_text("Error aprobando administrador. Revisa logs.")
            return

        try:
            _notify_admin_local_welcome(context, admin_id, reactivated=was_reactivated)
        except Exception as e:
            logger.warning("No se pudo notificar onboarding de admin local: %s", e)

        _resolve_important_alert(context, "admin_registration_{}".format(admin_id))
        query.edit_message_text("✅ Administrador aprobado (APPROVED).")
        return

    if accion == "rechazar":
        try:
            update_admin_status_by_id(admin_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            logger.error("update_admin_status_by_id REJECTED: %s", e)
            query.edit_message_text("Error rechazando administrador. Revisa logs.")
            return

        _resolve_important_alert(context, "admin_registration_{}".format(admin_id))
        query.edit_message_text("❌ Administrador rechazado (REJECTED).")
        return

    query.answer("Acción no reconocida.", show_alert=True)


def pendientes(update, context):
    """Menú rápido para ver registros pendientes."""
    user_db_id = get_user_db_id_from_update(update)

    telegram_id = update.effective_user.id
    es_admin_plataforma_flag = es_admin_plataforma(telegram_id)

    if not es_admin_plataforma_flag:
        try:
            user_db_id = get_user_db_id_from_update(update)
            admin = get_admin_by_user_id(user_db_id)

        except Exception:
            admin = None

        if not admin:
            update.message.reply_text("No tienes permisos para usar este comando.")
            return

    keyboard = [
        [
            InlineKeyboardButton("🟦 Aliados pendientes", callback_data="menu_aliados_pendientes"),
            InlineKeyboardButton("🟧 Repartidores pendientes", callback_data="menu_repartidores_pendientes")
        ]
    ]

    update.message.reply_text(
        "Seleccione que desea revisar:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )





def admin_config_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    if not user_has_platform_admin(user_id):
        query.answer("Solo el Administrador de Plataforma puede usar este menu.", show_alert=True)
        return

    # Tarifas (solo Admin Plataforma)
    if data == "config_tarifas":
        tarifas_start(update, context)
        return

    # Solicitudes de cambio (solo Admin Plataforma)
    if data == "config_change_requests":
        return admin_change_requests_list(update, context)

    if data == "config_totales":
        total_allies, total_couriers = get_totales_registros()
        total_admins = get_local_admins_count()

        texto = (
            "Resumen de registros:\n\n"
            "Aliados registrados: {}\n"
            "Repartidores registrados: {}\n"
            "Administradores locales registrados: {}"
        ).format(total_allies, total_couriers, total_admins)

        query.edit_message_text(texto)
        return


    if data == "config_gestion_aliados":
        allies = get_all_allies()
        if not allies:
            query.edit_message_text("No hay aliados registrados en este momento.")
            return

        keyboard = []
        for ally in allies:
            ally_id = ally["id"]
            business_name = ally["business_name"]
            status = ally["status"]
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(ally_id, business_name, status),
                callback_data="config_ver_ally_{}".format(ally_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_cerrar")])
        query.edit_message_text(
            "Aliados registrados. Toca uno para ver detalle.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("config_ver_ally_"):
        try:
            ally_id = int(data.split("_")[-1])
            _render_platform_ally_detail(query, ally_id)
        except Exception as e:
            logger.error("config_ver_ally_%s: %s", data, e)
            query.answer("No pude abrir el detalle del aliado.", show_alert=True)
        return

    if data.startswith("admin_local_parking_toggle_"):
        # Formato: admin_local_parking_toggle_{ally_id}_{admin_id}_{offset}_{idx}
        try:
            parts = data.replace("admin_local_parking_toggle_", "").split("_")
            ally_id = int(parts[0])
            link_admin_id = int(parts[1])
            offset = int(parts[2])
            idx = int(parts[3])
        except (ValueError, IndexError):
            query.answer("Error de formato.", show_alert=True)
            return
        query.answer()
        currently_enabled = get_ally_parking_fee_enabled(ally_id)
        new_enabled = not currently_enabled
        toggle_ally_parking_fee(ally_id, link_admin_id, new_enabled)
        new_state = "ACTIVO" if new_enabled else "INACTIVO"
        query.answer("Cobro parqueo dificil: {}".format(new_state), show_alert=True)
        try:
            ally_tg_id = get_ally_telegram_id_by_ally_id(ally_id)
            if ally_tg_id:
                if new_enabled:
                    toggle_msg = (
                        "Tu administrador ha habilitado el cobro adicional por parqueo dificil.\n\n"
                        "Las direcciones de tus clientes marcadas con dificultad de parqueo generaran "
                        "un cargo de ${:,} adicional en cada pedido a esos puntos, "
                        "para ayudar al repartidor con el parqueo o cualquier imprevisto.".format(PARKING_FEE_AMOUNT)
                    )
                else:
                    toggle_msg = (
                        "Tu administrador ha desactivado el cobro adicional por parqueo dificil.\n\n"
                        "Ya no se aplicara el cargo adicional por parqueo en tus pedidos."
                    )
                context.bot.send_message(chat_id=ally_tg_id, text=toggle_msg)
        except Exception as _e:
            logger.warning("admin_local_parking_toggle_: no se pudo notificar al aliado %s: %s", ally_id, _e)
        # Re-renderizar: simular callback admin_saldos_member_ally_{admin_id}_{offset}_{idx}
        links = list_ally_links_by_admin(link_admin_id, limit=20, offset=offset)
        if idx < 0 or idx >= len(links):
            query.edit_message_text("Error al recargar el detalle.")
            return
        r = links[idx]
        ally_id_r = r["ally_id"]
        business_name = r["business_name"] or "-"
        owner_name = r["owner_name"] or "-"
        phone_r = r["phone"] or "-"
        city_r = r["city"] or "-"
        barrio_r = r["barrio"] or "-"
        balance_r = r["balance"] or 0
        parking_enabled_new = get_ally_parking_fee_enabled(ally_id_r)
        texto = (
            "Aliado ID: {}\n"
            "Negocio: {}\n"
            "Propietario: {}\n"
            "Telefono: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Saldo por vínculo: {}\n"
            "Cobro parqueo dificil: {}"
        ).format(ally_id_r, business_name, owner_name, phone_r, city_r, barrio_r, balance_r,
                 "ACTIVO" if parking_enabled_new else "INACTIVO")
        keyboard = [
            [InlineKeyboardButton(
                "{} Cobro parqueo dificil".format("Desactivar" if parking_enabled_new else "Activar"),
                callback_data="admin_local_parking_toggle_{}_{}_{}_{}" .format(ally_id_r, link_admin_id, offset, idx)
            )],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_saldos_team_allies_{}_{}".format(link_admin_id, offset))],
            [InlineKeyboardButton("⬅️ Volver a equipos", callback_data="admin_saldos_allies")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("config_ally_parking_toggle_"):
        try:
            ally_id = int(data.split("_")[-1])
        except (ValueError, IndexError):
            query.answer("Error de formato.", show_alert=True)
            return
        currently_enabled = get_ally_parking_fee_enabled(ally_id)
        new_enabled = not currently_enabled
        # admin_id=None: actualiza el vinculo APPROVED del aliado sin importar qué admin lo gestione
        toggle_ally_parking_fee(ally_id, None, new_enabled)
        new_state = "ACTIVO" if new_enabled else "INACTIVO"
        query.answer("Cobro parqueo dificil: {}".format(new_state), show_alert=True)
        try:
            ally_tg_id = get_ally_telegram_id_by_ally_id(ally_id)
            if ally_tg_id:
                if new_enabled:
                    toggle_msg = (
                        "Tu administrador ha habilitado el cobro adicional por parqueo dificil.\n\n"
                        "Las direcciones de tus clientes marcadas con dificultad de parqueo generaran "
                        "un cargo de ${:,} adicional en cada pedido a esos puntos, "
                        "para ayudar al repartidor con el parqueo o cualquier imprevisto.".format(PARKING_FEE_AMOUNT)
                    )
                else:
                    toggle_msg = (
                        "Tu administrador ha desactivado el cobro adicional por parqueo dificil.\n\n"
                        "Ya no se aplicara el cargo adicional por parqueo en tus pedidos."
                    )
                context.bot.send_message(chat_id=ally_tg_id, text=toggle_msg)
        except Exception as _e:
            logger.warning("config_ally_parking_toggle_: no se pudo notificar al aliado %s: %s", ally_id, _e)
        _render_platform_ally_detail(query, ally_id)
        return

    if data.startswith("config_ally_assign_menu_"):
        ally_id = int(data.split("_")[-1])
        ally = get_ally_by_id(ally_id)
        if not ally:
            query.edit_message_text("No se encontró el aliado.")
            return

        keyboard = []
        admins = get_all_local_admins()
        for admin_row in admins:
            admin_id = _row_value(admin_row, "id")
            team_name = _row_value(admin_row, "team_name", "-")
            team_code = _row_value(admin_row, "team_code", "-")
            keyboard.append([InlineKeyboardButton(
                "{} ({})".format(team_name, team_code),
                callback_data="config_ally_assign_pick_{}_{}".format(ally_id, admin_id)
            )])

        platform_admin = get_platform_admin()
        if platform_admin:
            keyboard.append([InlineKeyboardButton(
                "Plataforma (PLATFORM)",
                callback_data="config_ally_assign_platform_{}".format(ally_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver al aliado", callback_data="config_ver_ally_{}".format(ally_id))])
        query.edit_message_text(
            "Selecciona el equipo que debe quedar vinculado a este aliado:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("config_ally_assign_platform_") or data.startswith("config_ally_assign_pick_"):
        if data.startswith("config_ally_assign_platform_"):
            ally_id = int(data.replace("config_ally_assign_platform_", ""))
            platform_admin = get_platform_admin()
            if not platform_admin:
                query.edit_message_text("No existe un admin de plataforma disponible.")
                return
            target_admin_id = _row_value(platform_admin, "id")
            target_team_name = _row_value(platform_admin, "team_name", "Plataforma")
            target_team_code = _row_value(platform_admin, "team_code", "PLATFORM")
        else:
            parts = data.split("_")
            if len(parts) != 6:
                query.answer("Formato inválido.", show_alert=True)
                return
            ally_id = int(parts[4])
            target_admin_id = int(parts[5])
            admin_row = get_admin_by_id(target_admin_id)
            if not admin_row:
                query.edit_message_text("No se encontró el admin destino.")
                return
            target_team_name = _row_value(admin_row, "team_name", _row_value(admin_row, "full_name", "-"))
            target_team_code = _row_value(admin_row, "team_code", "-")

        ally = get_ally_by_id(ally_id)
        if not ally:
            query.edit_message_text("No se encontró el aliado.")
            return

        ally_status = (_row_value(ally, "status", "") or "").upper()
        if ally_status == "APPROVED":
            link_status = "APPROVED"
        elif ally_status == "PENDING":
            link_status = "PENDING"
        else:
            link_status = "INACTIVE"

        try:
            upsert_admin_ally_link(target_admin_id, ally_id, link_status)
            if link_status == "APPROVED":
                deactivate_other_approved_admin_ally_links(ally_id, target_admin_id)
        except Exception as e:
            logger.error("config_ally_assign_team ally_id=%s: %s", ally_id, e)
            query.edit_message_text("No se pudo actualizar el equipo del aliado.")
            return

        query.edit_message_text(
            "Equipo actualizado.\n\n"
            "Aliado ID: {}\n"
            "Nuevo equipo: {} ({})\n"
            "Estado del vínculo: {}\n\n"
            "Puedes volver al detalle para revisar el resultado.".format(
                ally_id,
                target_team_name,
                target_team_code,
                link_status,
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver al aliado", callback_data="config_ver_ally_{}".format(ally_id))],
                [InlineKeyboardButton("Volver a aliados", callback_data="config_gestion_aliados")],
            ])
        )
        return

        keyboard = []
        for courier in couriers:
            courier_id = courier["id"]
            full_name = courier["full_name"]
            status = courier["status"]
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(courier_id, full_name, status),
                callback_data="config_ver_courier_{}".format(courier_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_cerrar")])
        query.edit_message_text(
            "Repartidores registrados. Toca uno para ver detalle.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("config_ver_courier_"):
        courier_id = int(data.split("_")[-1])
        courier = get_courier_by_id(courier_id)
        if not courier:
            query.edit_message_text("No se encontró el repartidor.")
            return
        reset_state = get_courier_reset_state_by_id(courier_id)
        reset_status = _registration_reset_status_label(reset_state)

        rejection_reason = _row_value(courier, "rejection_reason", default=None)
        rejected_at = _row_value(courier, "rejected_at", default=None)
        rechazo_lineas = ""
        if rejection_reason:
            rechazo_lineas += "\nMotivo de rechazo: {}".format(rejection_reason)
        if rejected_at:
            fecha_str = str(rejected_at)[:10] if rejected_at else ""
            rechazo_lineas += "\nFecha de rechazo: {}".format(fecha_str)

        texto = (
            "Detalle del repartidor:\n\n"
            "ID: {id}\n"
            "Nombre: {full_name}\n"
            "Documento: {id_number}\n"
            "Teléfono: {phone}\n"
            "Ciudad: {city}\n"
            "Barrio: {barrio}\n"
            "Placa: {plate}\n"
            "Tipo de moto: {bike_type}\n"
            "Estado: {status}{rechazo_lineas}\n"
            "Reinicio de registro: {reset_status}"
        ).format(
            id=courier["id"],
            full_name=courier["full_name"],
            id_number=courier["id_number"],
            phone=courier["phone"],
            city=courier["city"],
            barrio=courier["barrio"],
            plate=courier["plate"],
            bike_type=courier["bike_type"],
            status=courier["status"],
            rechazo_lineas=rechazo_lineas,
            reset_status=reset_status,
        )

        status = courier["status"]
        keyboard = []

        if status == "PENDING":
            keyboard.append([
                InlineKeyboardButton("✅ Aprobar", callback_data="config_courier_enable_{}".format(courier_id)),
                InlineKeyboardButton("❌ Rechazar", callback_data="config_courier_reject_{}".format(courier_id)),
            ])
        if status == "APPROVED":
            keyboard.append([InlineKeyboardButton("⛔ Desactivar", callback_data="config_courier_disable_{}".format(courier_id))])
        if status == "INACTIVE":
            keyboard.append([InlineKeyboardButton("✅ Activar", callback_data="config_courier_enable_{}".format(courier_id))])
            _append_registration_reset_button(keyboard, "config_courier", courier_id, status, reset_state)
        if status == "REJECTED":
            _append_registration_reset_button(keyboard, "config_courier", courier_id, status, reset_state)

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")])
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "config_couriers_online":
        # Muestra todos los repartidores ONLINE en este momento (cualquier equipo)
        if not user_has_platform_admin(user_id):
            query.answer("Solo el Administrador de Plataforma puede ver esto.", show_alert=True)
            return
        query.answer()
        online = get_all_online_couriers()
        if not online:
            query.edit_message_text(
                "No hay repartidores con ubicacion en vivo activa en este momento.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Buscar cercanos a pedido", callback_data="config_couriers_cerca_pedido")],
                    [InlineKeyboardButton("⬅ Volver", callback_data="admin_volver_panel")],
                ])
            )
            return

        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        lineas = ["Repartidores online ahora ({}):\n".format(len(online))]
        keyboard = []
        for c in online:
            nombre = c["full_name"]
            ciudad = c["admin_city"] or "?"
            updated = c["live_location_updated_at"]
            if updated:
                try:
                    if isinstance(updated, str):
                        ts = datetime.datetime.fromisoformat(updated.replace("Z", ""))
                    else:
                        ts = updated
                    minutos = int((now - ts).total_seconds() / 60)
                    hace = "hace {} min".format(minutos) if minutos < 60 else "hace {}h".format(minutos // 60)
                except Exception:
                    hace = "?"
            else:
                hace = "?"
            lineas.append("{} | {} | {}".format(nombre, ciudad, hace))
            tg_id = c["telegram_id"]
            keyboard.append([InlineKeyboardButton(
                "Contactar: {}".format(nombre),
                url="tg://user?id={}".format(tg_id)
            )])

        keyboard.append([InlineKeyboardButton("Buscar cercanos a pedido", callback_data="config_couriers_cerca_pedido")])
        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="admin_volver_panel")])
        query.edit_message_text(
            "\n".join(lineas),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "config_couriers_cerca_pedido":
        # Muestra pedidos activos sin courier para que el admin elija uno
        if not user_has_platform_admin(user_id):
            query.answer("Solo el Administrador de Plataforma puede ver esto.", show_alert=True)
            return
        query.answer()
        pedidos = get_active_orders_without_courier(limit=15)
        if not pedidos:
            query.edit_message_text(
                "No hay pedidos activos sin repartidor asignado en este momento.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data="config_couriers_online")],
                ])
            )
            return

        keyboard = []
        for p in pedidos:
            orden_id = p["id"]
            ally = p["ally_name"] or "Aliado"
            direccion = (p["pickup_address"] or "")[:30]
            estado = p["status"]
            keyboard.append([InlineKeyboardButton(
                "#{} {} — {} ({})".format(orden_id, ally, direccion, estado),
                callback_data="config_cercanos_pedido_{}".format(orden_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_couriers_online")])
        query.edit_message_text(
            "Pedidos sin repartidor. Selecciona uno para ver quienes estan mas cerca:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("config_cercanos_pedido_"):
        # Muestra repartidores ONLINE ordenados por distancia al pickup del pedido
        if not user_has_platform_admin(user_id):
            query.answer("Solo el Administrador de Plataforma puede ver esto.", show_alert=True)
            return
        query.answer()
        try:
            order_id = int(data.split("_")[-1])
        except ValueError:
            query.answer("Error de formato.", show_alert=True)
            return
        order = get_order_by_id(order_id)
        if not order:
            query.edit_message_text("Pedido no encontrado.")
            return

        pickup_lat = order["pickup_lat"]
        pickup_lng = order["pickup_lng"]
        if not pickup_lat or not pickup_lng:
            query.edit_message_text(
                "Este pedido no tiene coordenadas de recogida registradas.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data="config_couriers_cerca_pedido")],
                ])
            )
            return

        cercanos = get_online_couriers_sorted_by_distance(float(pickup_lat), float(pickup_lng))
        if not cercanos:
            query.edit_message_text(
                "No hay repartidores online en este momento para comparar.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data="config_couriers_cerca_pedido")],
                ])
            )
            return

        lineas = ["Repartidores mas cercanos al pedido #{}:\n".format(order_id)]
        keyboard = []
        for c in cercanos[:10]:
            nombre = c["full_name"]
            dist = c["distancia_km"]
            ciudad = c["admin_city"] or "?"
            if dist >= 9000:
                dist_label = "sin GPS"
            else:
                dist_label = "{} km".format(dist)
            lineas.append("{} — {} | {}".format(nombre, dist_label, ciudad))
            tg_id = c["telegram_id"]
            keyboard.append([InlineKeyboardButton(
                "Contactar: {} ({})".format(nombre, dist_label),
                url="tg://user?id={}".format(tg_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_couriers_cerca_pedido")])
        query.edit_message_text(
            "\n".join(lineas),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == "config_gestion_repartidores":
        couriers = get_all_couriers()
        if not couriers:
            query.edit_message_text(
                "No hay repartidores registrados en este momento.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data="config_cerrar")]
                ])
            )
            return

        keyboard = []
        for courier in couriers:
            courier_id = courier["id"]
            full_name = courier["full_name"]
            status = courier["status"]
            keyboard.append([InlineKeyboardButton(
                "ID {} - {} ({})".format(courier_id, full_name, status),
                callback_data="config_ver_courier_{}".format(courier_id)
            )])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_cerrar")])
        query.edit_message_text(
            "Repartidores registrados. Toca uno para ver detalle.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("config_ally_disable_"):
        ally_id = int(data.split("_")[-1])
        update_ally_status_by_id(ally_id, "INACTIVE", changed_by=f"tg:{update.effective_user.id}")
        try:
            link = get_admin_link_for_ally(ally_id)
            if link:
                upsert_admin_ally_link(link["admin_id"], ally_id, "INACTIVE")
        except Exception as e:
            logger.error("config_ally_disable_ upsert link: %s", e)
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")]]
        query.edit_message_text("Aliado desactivado (INACTIVE).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_ally_enable_"):
        ally_id = int(data.split("_")[-1])
        ally_before = get_ally_by_id(ally_id)
        if ally_before and ally_before["status"] == "PENDING":
            result = approve_role_registration(update.effective_user.id, "ALLY", ally_id)
            if not result.get("ok"):
                query.answer(result.get("message") or "No se pudo aprobar el aliado.", show_alert=True)
                return
            try:
                ally = result.get("profile") or get_ally_by_id(ally_id)
                ally_telegram_id = get_ally_approval_notification_chat_id(ally_id)
                _send_role_welcome_message(
                    context,
                    "ALLY",
                    ally_telegram_id,
                    profile=ally,
                    bonus_granted=bool(result.get("bonus_granted")),
                    reactivated=False,
                )
            except Exception as e:
                logger.warning("No se pudo enviar onboarding al aliado %s: %s", ally_id, e)
            kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")]]
            query.edit_message_text("Aliado aprobado (APPROVED).", reply_markup=InlineKeyboardMarkup(kb))
            return
        was_reactivated = bool(ally_before and ally_before["status"] in ("INACTIVE", "REJECTED"))
        update_ally_status_by_id(ally_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
        try:
            link = get_admin_link_for_ally(ally_id)
            keep_admin_id = link["admin_id"] if link else get_platform_admin_id()
            upsert_admin_ally_link(keep_admin_id, ally_id, "APPROVED")
        except Exception as e:
            logger.error("config_ally_enable_ upsert link: %s", e)
        try:
            ally = get_ally_by_id(ally_id)
            ally_telegram_id = get_ally_approval_notification_chat_id(ally_id)
            _send_role_welcome_message(context, "ALLY", ally_telegram_id, profile=ally, reactivated=was_reactivated)
        except Exception as e:
            logger.warning("No se pudo enviar onboarding al aliado %s: %s", ally_id, e)
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")]]
        query.edit_message_text("Aliado activado (APPROVED).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_ally_reject_"):
        ally_id = int(data.split("_")[-1])
        update_ally_status_by_id(ally_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")]]
        query.edit_message_text("Aliado rechazado (REJECTED).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_ally_reset_"):
        payload = data.replace("config_ally_reset_", "")
        parts = payload.rsplit("_", 1)
        if len(parts) != 2:
            query.answer("Formato invalido", show_alert=True)
            return
        action = parts[0]
        try:
            ally_id = int(parts[1])
        except Exception:
            query.answer("Aliado invalido", show_alert=True)
            return

        ally = get_ally_by_id(ally_id)
        if not ally:
            query.answer("Aliado no encontrado.", show_alert=True)
            return
        reset_state = get_ally_reset_state_by_id(ally_id)

        if action == "enable":
            if ally["status"] not in ("INACTIVE", "REJECTED"):
                query.answer("Primero debe estar INACTIVE o REJECTED para autorizar reinicio.", show_alert=True)
                return
            if reset_state and reset_state.get("registration_reset_active"):
                query.answer("Este reinicio ya está autorizado.", show_alert=True)
                return
            try:
                platform_enable_ally_registration_reset(query.from_user.id, ally_id, note="Autorizado por plataforma")
            except PermissionError as e:
                query.answer(str(e), show_alert=True)
                return
            except ValueError as e:
                query.answer(str(e), show_alert=True)
                return
            query.edit_message_text(
                "Reinicio de registro autorizado correctamente.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Volver al aliado", callback_data="config_ver_ally_{}".format(ally_id))],
                    [InlineKeyboardButton("Volver", callback_data="config_gestion_aliados")],
                ])
            )
            return

        if action == "clear":
            if not reset_state or not reset_state.get("registration_reset_active"):
                if reset_state and reset_state.get("registration_reset_consumed_at"):
                    query.answer("Este reinicio ya fue consumido.", show_alert=True)
                else:
                    query.answer("No hay un reinicio activo para revocar.", show_alert=True)
                return
            try:
                platform_clear_ally_registration_reset(query.from_user.id, ally_id)
            except PermissionError as e:
                query.answer(str(e), show_alert=True)
                return
            except ValueError as e:
                query.answer(str(e), show_alert=True)
                return
            query.edit_message_text(
                "Reinicio de registro revocado correctamente.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Volver al aliado", callback_data="config_ver_ally_{}".format(ally_id))],
                    [InlineKeyboardButton("Volver", callback_data="config_gestion_aliados")],
                ])
            )
            return

        query.answer("Acción no reconocida.", show_alert=True)
        return

    if data.startswith("config_courier_disable_"):
        courier_id = int(data.split("_")[-1])
        update_courier_status_by_id(courier_id, "INACTIVE", changed_by=f"tg:{update.effective_user.id}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")]]
        query.edit_message_text("Repartidor desactivado (INACTIVE).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_courier_enable_"):
        courier_id = int(data.split("_")[-1])
        courier_before = get_courier_by_id(courier_id)
        if courier_before and courier_before.get("status") == "PENDING":
            result = approve_role_registration(update.effective_user.id, "COURIER", courier_id)
            if not result.get("ok"):
                query.answer(result.get("message") or "No se pudo aprobar el repartidor.", show_alert=True)
                return
            try:
                courier = result.get("profile") or get_courier_by_id(courier_id)
                courier_telegram_id = get_courier_approval_notification_chat_id(courier_id)
                _send_role_welcome_message(
                    context,
                    "COURIER",
                    courier_telegram_id,
                    profile=courier,
                    bonus_granted=bool(result.get("bonus_granted")),
                    reactivated=False,
                )
            except Exception as e:
                logger.warning("No se pudo enviar onboarding al repartidor %s: %s", courier_id, e)
            kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")]]
            query.edit_message_text("Repartidor aprobado (APPROVED).", reply_markup=InlineKeyboardMarkup(kb))
            return
        was_reactivated = bool(courier_before and courier_before.get("status") in ("INACTIVE", "REJECTED"))
        update_courier_status_by_id(courier_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
        try:
            courier = get_courier_by_id(courier_id)
            courier_telegram_id = get_courier_approval_notification_chat_id(courier_id)
            _send_role_welcome_message(context, "COURIER", courier_telegram_id, profile=courier, reactivated=was_reactivated)
        except Exception as e:
            logger.warning("No se pudo enviar onboarding al repartidor %s: %s", courier_id, e)
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")]]
        query.edit_message_text("Repartidor activado (APPROVED).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_courier_reject_"):
        courier_id = int(data.split("_")[-1])
        update_courier_status_by_id(courier_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")]]
        query.edit_message_text("Repartidor rechazado (REJECTED).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_courier_reset_"):
        payload = data.replace("config_courier_reset_", "")
        parts = payload.rsplit("_", 1)
        if len(parts) != 2:
            query.answer("Formato invalido", show_alert=True)
            return
        action = parts[0]
        try:
            courier_id = int(parts[1])
        except Exception:
            query.answer("Repartidor invalido", show_alert=True)
            return

        courier = get_courier_by_id(courier_id)
        if not courier:
            query.answer("Repartidor no encontrado.", show_alert=True)
            return
        reset_state = get_courier_reset_state_by_id(courier_id)

        if action == "enable":
            if courier["status"] != "INACTIVE":
                query.answer("Primero debe estar INACTIVE para autorizar reinicio.", show_alert=True)
                return
            if reset_state and reset_state.get("registration_reset_active"):
                query.answer("Este reinicio ya está autorizado.", show_alert=True)
                return
            try:
                platform_enable_courier_registration_reset(query.from_user.id, courier_id, note="Autorizado por plataforma")
            except PermissionError as e:
                query.answer(str(e), show_alert=True)
                return
            except ValueError as e:
                query.answer(str(e), show_alert=True)
                return
            query.edit_message_text(
                "Reinicio de registro autorizado correctamente.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Volver al repartidor", callback_data="config_ver_courier_{}".format(courier_id))],
                    [InlineKeyboardButton("Volver", callback_data="config_gestion_repartidores")],
                ])
            )
            return

        if action == "clear":
            if not reset_state or not reset_state.get("registration_reset_active"):
                if reset_state and reset_state.get("registration_reset_consumed_at"):
                    query.answer("Este reinicio ya fue consumido.", show_alert=True)
                else:
                    query.answer("No hay un reinicio activo para revocar.", show_alert=True)
                return
            try:
                platform_clear_courier_registration_reset(query.from_user.id, courier_id)
            except PermissionError as e:
                query.answer(str(e), show_alert=True)
                return
            except ValueError as e:
                query.answer(str(e), show_alert=True)
                return
            query.edit_message_text(
                "Reinicio de registro revocado correctamente.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Volver al repartidor", callback_data="config_ver_courier_{}".format(courier_id))],
                    [InlineKeyboardButton("Volver", callback_data="config_gestion_repartidores")],
                ])
            )
            return

        query.answer("Acción no reconocida.", show_alert=True)
        return

    if data == "config_cerrar":
        query.edit_message_text("Menú de configuraciones cerrado.")
        return

    query.answer("Opción no reconocida.", show_alert=True)


def _parking_status_label(status):
    """Etiqueta legible para el estado de dificultad de parqueo."""
    return {
        "NOT_ASKED": "Sin revisar",
        "ALLY_YES": "Aliado reporta dificultad (pendiente verificacion)",
        "PENDING_REVIEW": "Aliado no sabe (pendiente revision)",
        "ADMIN_YES": "Confirmado: punto con dificultad de parqueo",
        "ADMIN_NO": "Confirmado: sin dificultad de parqueo",
    }.get(status, status)


def admin_parking_review(update, context, show_all=False):
    """Muestra al admin la lista de direcciones pendientes de revision de parqueadero.

    PRIVACIDAD: solo muestra datos geograficos (direccion, ciudad, barrio) y nombre
    del aliado. Nunca expone nombre ni telefono del cliente.
    show_all=True: incluye tambien las ya revisadas (para correccion).
    """
    if update.callback_query:
        query = update.callback_query
        query.answer()
        user_id = query.from_user.id
        send_fn = query.edit_message_text
    else:
        user_id = update.effective_user.id
        send_fn = update.message.reply_text

    # Persistir la vista actual para que el callback pueda restaurarla después de cada acción
    context.user_data["parking_show_all"] = show_all

    admin = get_admin_by_user_id(get_user_db_id_from_update(update))
    if not admin:
        send_fn("No tienes un perfil de administrador activo.")
        return

    # Admin de plataforma (ADMIN_USER_ID) ve todos los aliados sin filtro de equipo.
    # Admin local solo ve los aliados de su equipo.
    admin_id = None if user_id == ADMIN_USER_ID else admin["id"]
    rows = get_all_addresses_parking_review(admin_id) if show_all else get_addresses_pending_parking_review(admin_id)

    if not rows:
        if show_all:
            msg = "No hay puntos con decision tomada ni pendientes de revision."
            keyboard = [[InlineKeyboardButton("Cerrar", callback_data="parking_close")]]
        else:
            msg = (
                "No hay puntos de entrega pendientes de revision de parqueo.\n\n"
                "Puedes ver los ya revisados para corregirlos si es necesario."
            )
            keyboard = [
                [InlineKeyboardButton("Ver todas (con revisadas)", callback_data="parking_ver_todas")],
                [InlineKeyboardButton("Cerrar", callback_data="parking_close")],
            ]
        send_fn(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    title = "PUNTOS CON DIFICULTAD DE PARQUEO" if not show_all else "TODOS LOS PUNTOS (parqueo)"

    # Pre-cargar el estado del toggle por aliado para no hacer N consultas en el loop
    ally_parking_cache = {}
    for row in rows:
        a_id = row["ally_id"] if "ally_id" in row.keys() else row[8]
        if a_id not in ally_parking_cache:
            ally_parking_cache[a_id] = get_ally_parking_fee_enabled(a_id)

    keyboard = []
    for i, row in enumerate(rows, 1):
        addr_id = row["id"] if "id" in row.keys() else row[0]
        address_text = row["address_text"] if "address_text" in row.keys() else row[1]
        city = row["city"] if "city" in row.keys() else row[2]
        barrio = row["barrio"] if "barrio" in row.keys() else row[3]
        status = row["parking_status"] if "parking_status" in row.keys() else row[4]
        ally_name = row["ally_name"] if "ally_name" in row.keys() else row[7]
        a_id = row["ally_id"] if "ally_id" in row.keys() else row[8]

        location_label = "{}, {}".format(barrio or "Sin barrio", city or "Sin ciudad")
        header = "{}. {} | {} | {}".format(i, ally_name, address_text[:30], location_label)
        estado_label = _parking_status_label(status)
        parking_toggle_on = ally_parking_cache.get(a_id, False)

        # Fila 1: encabezado del punto (no accionable, muestra info)
        keyboard.append([InlineKeyboardButton(
            header[:60],
            callback_data="parking_noop_{}".format(addr_id)
        )])
        # Fila 2: estado actual + aviso de toggle si está desactivado (una sola fila)
        toggle_suffix = " | COBRO DESACTIVADO" if not parking_toggle_on else ""
        keyboard.append([InlineKeyboardButton(
            "Estado: {}{}".format(estado_label, toggle_suffix),
            callback_data="parking_noop_{}".format(addr_id)
        )])
        # Fila 3: botones de accion
        keyboard.append([
            InlineKeyboardButton("SI, dificultad", callback_data="parking_rev_yes_{}".format(addr_id)),
            InlineKeyboardButton("NO, sin problema", callback_data="parking_rev_no_{}".format(addr_id)),
        ])

    if not show_all:
        keyboard.append([InlineKeyboardButton("Ver todas (con revisadas)", callback_data="parking_ver_todas")])
    keyboard.append([InlineKeyboardButton("Cerrar", callback_data="parking_close")])

    text = "{}\n\nToca SI o NO en cada punto para confirmar o descartar la dificultad de parqueo.".format(title)
    if len(rows) == 30:
        text += "\n\n(Mostrando los 30 mas recientes)"

    send_fn(text, reply_markup=InlineKeyboardMarkup(keyboard))


def admin_parking_review_callback(update, context):
    """Procesa la decision del admin sobre parqueadero de una direccion."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "parking_close":
        query.edit_message_text("Panel de parqueo cerrado.")
        context.user_data.pop("parking_show_all", None)
        return

    if data == "parking_ver_todas":
        admin_parking_review(update, context, show_all=True)
        return

    if data.startswith("parking_rev_yes_") or data.startswith("parking_rev_no_"):
        try:
            address_id = int(data.split("_")[-1])
        except (ValueError, IndexError):
            query.answer("Error de formato.", show_alert=True)
            return

        admin = get_admin_by_user_id(get_user_db_id_from_update(update))
        if not admin:
            query.answer("No tienes perfil de administrador.", show_alert=True)
            return
        admin_id = admin["id"]

        if data.startswith("parking_rev_yes_"):
            set_address_parking_status(address_id, "ADMIN_YES", reviewed_by=admin_id)
            query.answer(
                "Confirmado: punto con dificultad de parqueo. Se aplicaran ${:,} en pedidos a esta direccion.".format(PARKING_FEE_AMOUNT),
                show_alert=True
            )
            ally_msg = (
                "Tu administrador reviso una de tus direcciones de entrega y confirmo "
                "que hay dificultad para parquear moto o bicicleta en ese punto.\n\n"
                "Se agregaran ${:,} al costo del domicilio en pedidos a esa direccion "
                "para ayudar al repartidor con el parqueo o cualquier imprevisto.".format(PARKING_FEE_AMOUNT)
            )
        else:
            set_address_parking_status(address_id, "ADMIN_NO", reviewed_by=admin_id)
            query.answer("Confirmado: sin dificultad de parqueo en este punto.", show_alert=True)
            ally_msg = (
                "Tu administrador reviso una de tus direcciones de entrega y confirmo "
                "que no hay dificultad especial para parquear en ese punto.\n\n"
                "No se aplicara cobro adicional de parqueo en pedidos a esa direccion."
            )

        try:
            ally_telegram_id = get_ally_telegram_id_by_address_id(address_id)
            if ally_telegram_id:
                context.bot.send_message(chat_id=ally_telegram_id, text=ally_msg)
        except Exception as _e:
            logger.warning("admin_parking_review_callback: no se pudo notificar al aliado: %s", _e)

        admin_parking_review(update, context, show_all=context.user_data.get("parking_show_all", False))


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


