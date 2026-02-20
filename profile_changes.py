import os

from dotenv import load_dotenv
load_dotenv()

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, Filters

from services import extract_lat_lng_from_text
from db import (
    ensure_user,
    get_admin_by_user_id,
    get_courier_by_user_id,
    get_ally_by_user_id,
    get_admin_link_for_courier,
    get_admin_link_for_ally,
    get_default_ally_location,
    get_platform_admin,
    get_user_by_id,
    get_profile_change_request_by_id,
    create_profile_change_request,
    has_pending_profile_change_request,
    list_pending_profile_change_requests,
    mark_profile_change_request_approved,
    mark_profile_change_request_rejected,
    get_ally_by_id,
    get_connection,
    get_admin_by_team_code,
    upsert_admin_courier_link,
    upsert_admin_ally_link,
    deactivate_other_approved_admin_courier_links,
    deactivate_other_approved_admin_ally_links,
)


FAST_FIELDS = {"phone", "city", "barrio", "plate", "bike_type"}
VERIFIED_FIELDS = {
    "address",
    "residence_address",
    "residence_location",
    "business_name",
    "owner_name",
    "ally_default_location",
    "admin_team_code",
}

ADMIN_FIELDS = ["phone", "city", "barrio", "residence_address", "residence_location"]
COURIER_FIELDS = ["phone", "city", "barrio", "plate", "bike_type", "residence_address", "residence_location"]
ALLY_FIELDS = ["phone", "city", "barrio", "address", "business_name", "owner_name", "ally_default_location"]

# Migración de administración disponible para roles operativos
COURIER_FIELDS.append("admin_team_code")
ALLY_FIELDS.append("admin_team_code")

FIELD_LABELS = {
    "phone": "Telefono",
    "city": "Ciudad",
    "barrio": "Barrio",
    "plate": "Placa",
    "bike_type": "Tipo de moto",
    "address": "Direccion del negocio",
    "residence_address": "Direccion de residencia",
    "residence_location": "Ubicacion de residencia (GPS)",
    "business_name": "Nombre del negocio",
    "owner_name": "Nombre del propietario",
    "ally_default_location": "Ubicacion del negocio (GPS)",
    "admin_team_code": "Migracion de administracion",
}

(
    PC_SELECT_ROLE,
    PC_SELECT_FIELD,
    PC_NEW_VALUE,
    PC_CONFIRM,
) = range(600, 604)


_ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))


def _get_user_db_id(update):
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    return user_row["id"]


def _is_platform(update):
    return update.effective_user.id == _ADMIN_USER_ID


def _cancel_wrapper(update, context):
    from main import cancel_conversacion
    return cancel_conversacion(update, context)


def _cancel_text_wrapper(update, context):
    from main import cancel_por_texto
    return cancel_por_texto(update, context)


def _get_role_label(role):
    if role == "admin":
        return "Administrador"
    if role == "courier":
        return "Repartidor"
    if role == "ally":
        return "Aliado"
    return role


def _clear_pc_context(context):
    for k in [
        "pc_role",
        "pc_field",
        "pc_old_value",
        "pc_new_value",
        "pc_new_lat",
        "pc_new_lng",
        "pc_request_id",
    ]:
        if k in context.user_data:
            del context.user_data[k]


def _resolve_team_for_request(target_role, role_obj, target_role_id, field_name=None):
    if field_name == "admin_team_code":
        platform = get_platform_admin()
        if platform:
            return platform["id"], "PLATFORM"
        return None, "PLATFORM"

    if target_role == "admin":
        team_admin_id = role_obj["id"]
        team_code = role_obj["team_code"]
        return team_admin_id, team_code
    if target_role == "courier":
        link = get_admin_link_for_courier(target_role_id)
    else:
        link = get_admin_link_for_ally(target_role_id)
    if link:
        return link["admin_id"], link["team_code"]
    platform = get_platform_admin()
    if platform:
        return platform["id"], "PLATFORM"
    return None, "PLATFORM"


def _get_old_value(target_role, field_name, role_obj, target_role_id):
    if field_name == "admin_team_code":
        if target_role == "courier":
            link = get_admin_link_for_courier(target_role_id)
        elif target_role == "ally":
            link = get_admin_link_for_ally(target_role_id)
        else:
            link = None
        if link and "team_code" in link.keys() and link["team_code"]:
            return link["team_code"]
        return "SIN_ADMIN"

    if field_name == "residence_location":
        lat = role_obj["residence_lat"] if "residence_lat" in role_obj.keys() else None
        lng = role_obj["residence_lng"] if "residence_lng" in role_obj.keys() else None
        if lat is not None and lng is not None:
            return "{}, {}".format(lat, lng)
        return "No disponible"
    if field_name == "ally_default_location":
        loc = get_default_ally_location(target_role_id)
        if loc and loc.get("lat") is not None and loc.get("lng") is not None:
            return "{}, {}".format(loc.get("lat"), loc.get("lng"))
        return "No disponible"
    if field_name in role_obj.keys():
        val = role_obj[field_name]
        return val if val not in (None, "") else "-"
    return "-"


def _show_field_options(query, role):
    if role == "admin":
        fields = ADMIN_FIELDS
    elif role == "courier":
        fields = COURIER_FIELDS
    else:
        fields = ALLY_FIELDS
    keyboard = []
    for f in fields:
        label = FIELD_LABELS.get(f, f)
        keyboard.append([InlineKeyboardButton(label, callback_data="perfil_change_field_{}".format(f))])
    query.edit_message_text(
        "Selecciona el campo que deseas actualizar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PC_SELECT_FIELD


def perfil_change_start(update, context):
    query = update.callback_query
    query.answer()
    user_db_id = _get_user_db_id(update)
    admin = get_admin_by_user_id(user_db_id)
    courier = get_courier_by_user_id(user_db_id)
    ally = get_ally_by_user_id(user_db_id)

    roles = []
    if admin:
        roles.append("admin")
    if courier:
        roles.append("courier")
    if ally:
        roles.append("ally")

    context.user_data["pc_admin"] = admin
    context.user_data["pc_courier"] = courier
    context.user_data["pc_ally"] = ally

    if len(roles) == 1:
        context.user_data["pc_role"] = roles[0]
        return _show_field_options(query, roles[0])

    keyboard = []
    if admin:
        keyboard.append([InlineKeyboardButton("Administrador", callback_data="perfil_change_role_admin")])
    if courier:
        keyboard.append([InlineKeyboardButton("Repartidor", callback_data="perfil_change_role_courier")])
    if ally:
        keyboard.append([InlineKeyboardButton("Aliado", callback_data="perfil_change_role_ally")])
    query.edit_message_text(
        "Selecciona el rol que deseas actualizar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PC_SELECT_ROLE


def pc_select_role(update, context):
    query = update.callback_query
    query.answer()
    data = query.data or ""
    if data == "perfil_change_role_admin":
        role = "admin"
    elif data == "perfil_change_role_courier":
        role = "courier"
    elif data == "perfil_change_role_ally":
        role = "ally"
    else:
        query.edit_message_text("Opcion no valida.")
        return ConversationHandler.END
    context.user_data["pc_role"] = role
    return _show_field_options(query, role)


def pc_select_field(update, context):
    query = update.callback_query
    query.answer()
    data = query.data or ""
    if not data.startswith("perfil_change_field_"):
        query.edit_message_text("Opcion no valida.")
        return ConversationHandler.END

    field_name = data.replace("perfil_change_field_", "")
    role = context.user_data.get("pc_role")
    user_db_id = _get_user_db_id(update)

    if role == "admin":
        role_obj = context.user_data.get("pc_admin")
        role_id = role_obj["id"]
    elif role == "courier":
        role_obj = context.user_data.get("pc_courier")
        role_id = role_obj["id"]
    else:
        role_obj = context.user_data.get("pc_ally")
        role_id = role_obj["id"]

    if has_pending_profile_change_request(user_db_id, role, role_id, field_name):
        query.edit_message_text("Ya tienes una solicitud pendiente para este campo. Espera a que sea revisada.")
        return ConversationHandler.END

    old_value = _get_old_value(role, field_name, role_obj, role_id)
    context.user_data["pc_field"] = field_name
    context.user_data["pc_old_value"] = old_value

    if field_name in ("residence_location", "ally_default_location"):
        query.edit_message_text("Envia tu ubicacion GPS (pin de Telegram) o pega un link de Google Maps.")
        return PC_NEW_VALUE
    if field_name == "admin_team_code":
        query.edit_message_text(
            "Escribe el codigo del equipo destino (ej: TEAM3 o PLATFORM).\n"
            "Solo se permite migrar a administradores con estado APPROVED."
        )
        return PC_NEW_VALUE

    query.edit_message_text(
        "Escribe el nuevo valor para {}.\n\nValor actual: {}".format(
            FIELD_LABELS.get(field_name, field_name),
            old_value
        )
    )
    return PC_NEW_VALUE


def pc_new_value(update, context):
    role = context.user_data.get("pc_role")
    field_name = context.user_data.get("pc_field")
    old_value = context.user_data.get("pc_old_value")

    new_value_display = ""
    if field_name in ("residence_location", "ally_default_location"):
        lat = None
        lng = None
        if update.message.location:
            lat = update.message.location.latitude
            lng = update.message.location.longitude
        else:
            text = (update.message.text or "").strip()
            coords = extract_lat_lng_from_text(text)
            if coords:
                lat, lng = coords
        if lat is None or lng is None:
            update.message.reply_text(
                "No pude detectar la ubicacion. Envia un pin de Telegram o pega un link de Google Maps."
            )
            return PC_NEW_VALUE
        context.user_data["pc_new_lat"] = lat
        context.user_data["pc_new_lng"] = lng
        new_value_display = "{}, {}".format(lat, lng)
        context.user_data["pc_new_value"] = (update.message.text or "").strip()
    elif field_name == "admin_team_code":
        team_code = (update.message.text or "").strip().upper()
        if not team_code:
            update.message.reply_text("Debes escribir un codigo de equipo valido.")
            return PC_NEW_VALUE
        admin_row = get_admin_by_team_code(team_code)
        if not admin_row:
            update.message.reply_text("No existe un administrador con ese codigo de equipo.")
            return PC_NEW_VALUE
        admin_status = admin_row["status"] if "status" in admin_row.keys() else admin_row[3]
        if admin_status != "APPROVED":
            update.message.reply_text(
                "Ese administrador no esta APPROVED. Debes elegir un equipo APPROVED."
            )
            return PC_NEW_VALUE
        context.user_data["pc_new_value"] = team_code
        new_value_display = team_code
    else:
        text = update.message.text.strip()
        context.user_data["pc_new_value"] = text
        new_value_display = text

    resumen = (
        "Resumen de tu solicitud:\n\n"
        "Rol: {rol}\n"
        "Campo: {campo}\n"
        "Valor actual: {old}\n"
        "Nuevo valor: {new}\n\n"
        "Escribe SI para confirmar o NO para cancelar."
    ).format(
        rol=_get_role_label(role),
        campo=FIELD_LABELS.get(field_name, field_name),
        old=old_value,
        new=new_value_display
    )
    update.message.reply_text(resumen)
    return PC_CONFIRM


def apply_profile_change_request(request_row):
    target_role = request_row["target_role"]
    target_role_id = request_row["target_role_id"]
    field_name = request_row["field_name"]
    new_value = request_row["new_value"]
    new_lat = request_row["new_lat"]
    new_lng = request_row["new_lng"]

    conn = get_connection()
    cur = conn.cursor()

    if target_role == "admin":
        if field_name == "phone":
            cur.execute("UPDATE admins SET phone = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "city":
            cur.execute("UPDATE admins SET city = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "barrio":
            cur.execute("UPDATE admins SET barrio = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "residence_address":
            cur.execute("UPDATE admins SET residence_address = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "residence_location":
            cur.execute(
                "UPDATE admins SET residence_lat = ?, residence_lng = ? WHERE id = ?",
                (new_lat, new_lng, target_role_id)
            )
    elif target_role == "courier":
        if field_name == "phone":
            cur.execute("UPDATE couriers SET phone = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "city":
            cur.execute("UPDATE couriers SET city = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "barrio":
            cur.execute("UPDATE couriers SET barrio = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "plate":
            cur.execute("UPDATE couriers SET plate = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "bike_type":
            cur.execute("UPDATE couriers SET bike_type = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "residence_address":
            cur.execute("UPDATE couriers SET residence_address = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "residence_location":
            cur.execute(
                "UPDATE couriers SET residence_lat = ?, residence_lng = ? WHERE id = ?",
                (new_lat, new_lng, target_role_id)
            )
        elif field_name == "admin_team_code":
            pass
    else:
        if field_name == "phone":
            cur.execute("UPDATE allies SET phone = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "city":
            cur.execute("UPDATE allies SET city = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "barrio":
            cur.execute("UPDATE allies SET barrio = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "address":
            cur.execute("UPDATE allies SET address = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "business_name":
            cur.execute("UPDATE allies SET business_name = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "owner_name":
            cur.execute("UPDATE allies SET owner_name = ? WHERE id = ?", (new_value, target_role_id))
        elif field_name == "ally_default_location":
            cur.execute("""
                UPDATE ally_locations
                SET lat = ?, lng = ?, address = ?
                WHERE ally_id = ? AND is_default = 1
            """, (new_lat, new_lng, new_value, target_role_id))
            if cur.rowcount == 0:
                ally = get_ally_by_id(target_role_id)
                city = ally["city"] if ally and ally["city"] else ""
                barrio = ally["barrio"] if ally and ally["barrio"] else ""
                cur.execute("""
                    INSERT INTO ally_locations (ally_id, label, address, city, barrio, is_default, lat, lng, created_at)
                    VALUES (?, 'Principal', ?, ?, ?, 1, ?, ?, datetime('now'))
                """, (target_role_id, new_value, city, barrio, new_lat, new_lng))
        elif field_name == "admin_team_code":
            pass

    conn.commit()
    conn.close()

    if field_name == "admin_team_code":
        team_code = (new_value or "").strip().upper()
        admin_row = get_admin_by_team_code(team_code)
        if not admin_row:
            raise ValueError("Admin destino no encontrado para team_code={}".format(team_code))
        admin_id = admin_row["id"] if "id" in admin_row.keys() else admin_row[0]
        admin_status = admin_row["status"] if "status" in admin_row.keys() else admin_row[3]
        if admin_status != "APPROVED":
            raise ValueError("Admin destino no esta APPROVED.")

        if target_role == "courier":
            upsert_admin_courier_link(admin_id, target_role_id, status="APPROVED", is_active=1)
            deactivate_other_approved_admin_courier_links(target_role_id, admin_id)
        elif target_role == "ally":
            upsert_admin_ally_link(admin_id, target_role_id, status="APPROVED")
            deactivate_other_approved_admin_ally_links(target_role_id, admin_id)


def pc_confirm(update, context):
    text = update.message.text.strip().upper()
    if text not in ("SI", "NO"):
        update.message.reply_text("Escribe SI para confirmar o NO para cancelar.")
        return PC_CONFIRM

    if text == "NO":
        update.message.reply_text("Solicitud cancelada.")
        _clear_pc_context(context)
        return ConversationHandler.END

    role = context.user_data.get("pc_role")
    field_name = context.user_data.get("pc_field")
    old_value = context.user_data.get("pc_old_value")
    new_value = context.user_data.get("pc_new_value") or ""
    new_lat = context.user_data.get("pc_new_lat")
    new_lng = context.user_data.get("pc_new_lng")

    user_db_id = _get_user_db_id(update)
    if role == "admin":
        role_obj = context.user_data.get("pc_admin")
        role_id = role_obj["id"]
    elif role == "courier":
        role_obj = context.user_data.get("pc_courier")
        role_id = role_obj["id"]
    else:
        role_obj = context.user_data.get("pc_ally")
        role_id = role_obj["id"]

    team_admin_id, team_code = _resolve_team_for_request(role, role_obj, role_id, field_name=field_name)
    req_id = create_profile_change_request(
        requester_user_id=user_db_id,
        target_role=role,
        target_role_id=role_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        new_lat=new_lat,
        new_lng=new_lng,
        team_admin_id=team_admin_id,
        team_code=team_code,
    )

    if field_name in FAST_FIELDS:
        req_row = get_profile_change_request_by_id(req_id)
        apply_profile_change_request(req_row)
        mark_profile_change_request_approved(req_id, user_db_id, None)
        update.message.reply_text("Cambio aplicado exitosamente.")
    else:
        update.message.reply_text("Solicitud creada. Un administrador la revisara pronto.")

    _clear_pc_context(context)
    return ConversationHandler.END


def _can_review(request_row, is_platform, admin_id):
    if is_platform:
        return True
    team_admin_id = request_row["team_admin_id"]
    team_code = request_row["team_code"]
    return team_admin_id == admin_id and (team_code is None or team_code != "PLATFORM")


def admin_change_requests_list(update, context):
    query = update.callback_query
    if query:
        query.answer()
    user_db_id = _get_user_db_id(update)
    es_plataforma = _is_platform(update)
    admin_local = get_admin_by_user_id(user_db_id)
    admin_id = admin_local["id"] if admin_local else None

    if not es_plataforma and not admin_local:
        if query:
            query.edit_message_text("No tienes permisos para ver solicitudes.")
        else:
            update.message.reply_text("No tienes permisos para ver solicitudes.")
        return

    pendientes = list_pending_profile_change_requests(es_plataforma, admin_id or 0)
    if not pendientes:
        if query:
            query.edit_message_text("No hay solicitudes pendientes.")
        else:
            update.message.reply_text("No hay solicitudes pendientes.")
        return

    keyboard = []
    for r in pendientes:
        label = "ID {} - {} - {}".format(r["id"], _get_role_label(r["target_role"]), FIELD_LABELS.get(r["field_name"], r["field_name"]))
        keyboard.append([InlineKeyboardButton(label, callback_data="chgreq_view_{}".format(r["id"]))])
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="admin_volver_panel")])
    text = "Solicitudes pendientes:\n\nToca una para ver detalle."
    if query:
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


def admin_change_requests_callback(update, context):
    query = update.callback_query
    data = query.data or ""
    query.answer()

    user_db_id = _get_user_db_id(update)
    es_plataforma = _is_platform(update)
    admin_local = get_admin_by_user_id(user_db_id)
    admin_id = admin_local["id"] if admin_local else None

    if data.startswith("chgreq_view_"):
        req_id = int(data.replace("chgreq_view_", ""))
        req = get_profile_change_request_by_id(req_id)
        if not req:
            query.edit_message_text("Solicitud no encontrada.")
            return
        if not _can_review(req, es_plataforma, admin_id):
            query.edit_message_text("No tienes permisos para revisar esta solicitud.")
            return
        maps_line = ""
        if req["new_lat"] is not None and req["new_lng"] is not None:
            maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(req["new_lat"], req["new_lng"])
        texto = (
            "Solicitud de cambio:\n\n"
            "ID: {id}\n"
            "Rol: {rol}\n"
            "Campo: {campo}\n"
            "Valor actual: {old}\n"
            "Nuevo valor: {new}\n"
            "{maps}"
            "Estado: {status}\n"
        ).format(
            id=req["id"],
            rol=_get_role_label(req["target_role"]),
            campo=FIELD_LABELS.get(req["field_name"], req["field_name"]),
            old=req["old_value"] if req["old_value"] else "-",
            new=req["new_value"] if req["new_value"] else "-",
            maps=maps_line,
            status=req["status"],
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data="chgreq_approve_{}".format(req["id"])),
                InlineKeyboardButton("❌ Rechazar", callback_data="chgreq_reject_{}".format(req["id"])),
            ],
            [InlineKeyboardButton("⬅️ Volver", callback_data="admin_change_requests")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("chgreq_approve_"):
        req_id = int(data.replace("chgreq_approve_", ""))
        req = get_profile_change_request_by_id(req_id)
        if not req:
            query.edit_message_text("Solicitud no encontrada.")
            return
        if not _can_review(req, es_plataforma, admin_id):
            query.edit_message_text("No tienes permisos para aprobar esta solicitud.")
            return
        apply_profile_change_request(req)
        mark_profile_change_request_approved(req_id, user_db_id, admin_id)
        requester = get_user_by_id(req["requester_user_id"])
        if requester:
            telegram_id = requester["telegram_id"]
            context.bot.send_message(
                chat_id=telegram_id,
                text="Tu solicitud de cambio de {} fue aprobada y aplicada.".format(
                    FIELD_LABELS.get(req["field_name"], req["field_name"])
                )
            )
        query.edit_message_text("Solicitud aprobada y aplicada.")
        return

    if data.startswith("chgreq_reject_"):
        req_id = int(data.replace("chgreq_reject_", ""))
        req = get_profile_change_request_by_id(req_id)
        if not req:
            query.edit_message_text("Solicitud no encontrada.")
            return
        if not _can_review(req, es_plataforma, admin_id):
            query.edit_message_text("No tienes permisos para rechazar esta solicitud.")
            return
        prompt = query.message.reply_text(
            "Escribe la razon de rechazo para esta solicitud.",
            reply_markup=ForceReply()
        )
        context.user_data["chgreq_rejecting"] = {
            "request_id": req_id,
            "reviewer_user_id": user_db_id,
            "reviewer_admin_id": admin_id,
            "prompt_message_id": prompt.message_id,
        }
        query.edit_message_text("Escribe la razon de rechazo para esta solicitud.")
        return


def chgreq_reject_reason_handler(update, context):
    pending = context.user_data.get("chgreq_rejecting")
    if not pending:
        return
    if not update.message.reply_to_message:
        return
    prompt_id = pending.get("prompt_message_id")
    if prompt_id and update.message.reply_to_message.message_id != prompt_id:
        return
    reason = update.message.text.strip()
    req_id = pending["request_id"]
    reviewer_user_id = pending["reviewer_user_id"]
    reviewer_admin_id = pending["reviewer_admin_id"]
    req = get_profile_change_request_by_id(req_id)
    if not req:
        update.message.reply_text("Solicitud no encontrada.")
        context.user_data.pop("chgreq_rejecting", None)
        return
    mark_profile_change_request_rejected(req_id, reviewer_user_id, reviewer_admin_id, reason)
    requester = get_user_by_id(req["requester_user_id"])
    if requester:
        telegram_id = requester["telegram_id"]
        context.bot.send_message(
            chat_id=telegram_id,
            text="Tu solicitud de cambio de {} fue rechazada.\nRazon: {}".format(
                FIELD_LABELS.get(req["field_name"], req["field_name"]),
                reason
            )
        )
    update.message.reply_text("Solicitud rechazada.")
    context.user_data.pop("chgreq_rejecting", None)


profile_change_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(perfil_change_start, pattern=r'^perfil_change_start$')],
    states={
        PC_SELECT_ROLE: [CallbackQueryHandler(pc_select_role, pattern=r"^perfil_change_role_")],
        PC_SELECT_FIELD: [CallbackQueryHandler(pc_select_field, pattern=r"^perfil_change_field_")],
        PC_NEW_VALUE: [
            MessageHandler(Filters.location, pc_new_value),
            MessageHandler(Filters.text & ~Filters.command, pc_new_value),
        ],
        PC_CONFIRM: [MessageHandler(Filters.text & ~Filters.command, pc_confirm)],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_wrapper),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), _cancel_text_wrapper),
    ],
    allow_reentry=True,
)
