# =============================================================================
# handlers/recharges.py — Sistema de recargas, pagos e ingreso externo
# Extraído de main.py (Fase 2g)
# =============================================================================

import logging
logger = logging.getLogger(__name__)

import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)

from handlers.states import (
    ALLY_SUBS_CONFIRMAR,
    INGRESO_METODO,
    INGRESO_MONTO,
    INGRESO_NOTA,
    PAGO_BANCO,
    PAGO_INSTRUCCIONES,
    PAGO_MENU,
    PAGO_TELEFONO,
    PAGO_TITULAR,
    RECARGAR_ADMIN,
    RECARGAR_COMPROBANTE,
    RECARGAR_MONTO,
    RECARGAR_ROL,
    RECARGA_DIR_TIPO,
    RECARGA_DIR_MONTO,
    RECARGA_DIR_NOTA,
    SOCIEDAD_RETIRO_MONTO,
)
from handlers.common import (
    CANCELAR_VOLVER_MENU_FILTER,
    _build_role_welcome_message,
    _resolve_important_alert,
    _schedule_important_alerts,
    _send_role_welcome_message,
    cancel_conversacion,
    cancel_por_texto,
)
from services import (
    admin_puede_operar,
    approve_recharge_request,
    get_admin_balance_breakdown,
    get_admin_ledger_movements,
    get_admin_saldo_hoy,
    get_platform_sociedad,
    get_platform_sociedad_id,
    transfer_sociedad_to_platform,
    get_sociedad_balance,
    get_sociedad_saldo_hoy,
    approve_role_registration,
    count_admin_couriers,
    count_admin_couriers_with_min_balance,
    create_payment_method,
    create_recharge_request,
    deactivate_payment_method,
    ensure_user,
    es_admin_plataforma,
    get_admin_balance,
    get_admin_by_id,
    get_admin_by_telegram_id,
    get_admin_by_user_id,
    get_admin_link_for_ally,
    get_admin_link_for_courier,
    get_admin_payment_info,
    get_admin_status_by_id,
    get_admins_with_pending_count,
    get_all_approved_links_for_ally,
    get_all_approved_links_for_courier,
    get_ally_approval_notification_chat_id,
    get_ally_by_id,
    get_ally_by_user_id,
    get_allies_by_admin_and_status,
    get_approved_admin_link_for_ally,
    get_approved_admin_link_for_courier,
    get_courier_approval_notification_chat_id,
    get_courier_by_id,
    get_courier_by_user_id,
    get_couriers_by_admin_and_status,
    get_payment_method_by_id,
    get_pending_allies_by_admin,
    get_pending_couriers_by_admin,
    get_platform_admin,
    get_recharge_request,
    get_user_by_id,
    get_user_db_id_from_update,
    list_all_pending_recharges,
    list_payment_methods,
    list_pending_recharges_for_admin,
    list_recharge_ledger,
    register_platform_income,
    reject_recharge_request,
    toggle_payment_method,
    update_admin_courier_status,
    update_ally_status,
    upsert_admin_ally_link,
    update_recharge_proof,
    user_has_platform_admin,
    direct_recharge_by_platform,
    get_all_active_couriers,
    get_all_active_allies,
    get_all_local_admins_approved,
)

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

def cmd_saldo(update, context):
    """
    Comando /saldo - Muestra el saldo de TODOS los vínculos del usuario.
    Courier/Ally: un balance por cada admin con vínculo APPROVED.
    Admin: balance master del admin.
    """
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    mensaje = "💰 TUS SALDOS\n"
    mensaje += "(Los saldos de Repartidor/Aliado son por vínculo, no globales)\n\n"
    tiene_algo = False
    es_plataforma = False

    admin = get_admin_by_user_id(user_db_id)
    if admin:
        admin_id = admin["id"]
        balance = get_admin_balance(admin_id)
        team_name = admin["team_name"]
        team_code = admin["team_code"]
        admin_label = "Plataforma" if team_code == "PLATFORM" else (team_name or "sin nombre")
        if team_code:
            admin_label = "{} [{}]".format(admin_label, team_code)
        mensaje += "🔧 Admin ({}):\n".format(admin_label)
        mensaje += "   Saldo master: ${:,}\n".format(balance)
        if team_code == "PLATFORM":
            es_plataforma = True
            bd = get_admin_balance_breakdown(admin_id)
            mes = bd["mes_inicio"]
            mensaje += "\n   Desglose del mes ({}):\n".format(mes)
            if bd["fees_mes"]:
                mensaje += "   Fees equipo:             +${:,}\n".format(bd["fees_mes"])
            if bd["sociedad_advance_mes"]:
                mensaje += "   Retiros de Sociedad:     +${:,}\n".format(bd["sociedad_advance_mes"])
            if not any([bd["fees_mes"], bd["sociedad_advance_mes"]]):
                mensaje += "   (sin movimientos este mes)\n"
            mensaje += "   Fees equipo acumulados: ${:,}\n".format(bd["fees_total"])
            # Cuenta de la Sociedad (separada)
            sociedad = get_platform_sociedad()
            if sociedad:
                soc_id = sociedad["id"]
                soc_balance = sociedad["balance"] if sociedad["balance"] else 0
                soc_bd = get_admin_balance_breakdown(soc_id)
                mensaje += "\n💼 Sociedad Domiquerendona:\n"
                mensaje += "   Saldo sociedad: ${:,}\n".format(soc_balance)
                mensaje += "\n   Desglose del mes ({}):\n".format(mes)
                if soc_bd["ingresos_mes"]:
                    mensaje += "   Ingresos externos:   +${:,}\n".format(soc_bd["ingresos_mes"])
                if soc_bd["fees_mes"]:
                    mensaje += "   Fees plataforma:     +${:,}\n".format(soc_bd["fees_mes"])
                if soc_bd["subs_mes"]:
                    mensaje += "   Suscripciones:       +${:,}\n".format(soc_bd["subs_mes"])
                if soc_bd["recargas_mes"]:
                    mensaje += "   Recargas aprobadas:  -${:,}\n".format(soc_bd["recargas_mes"])
                if soc_bd["sociedad_advance_salida_mes"]:
                    mensaje += "   Retiros al personal: -${:,}\n".format(soc_bd["sociedad_advance_salida_mes"])
                if not any([soc_bd["ingresos_mes"], soc_bd["fees_mes"], soc_bd["subs_mes"],
                            soc_bd["recargas_mes"], soc_bd["sociedad_advance_salida_mes"]]):
                    mensaje += "   (sin movimientos este mes)\n"
                mensaje += "   Fees plataforma acumulados: ${:,}\n".format(soc_bd["fees_total"])
        mensaje += "\n"
        tiene_algo = True

    courier = get_courier_by_user_id(user_db_id)
    if courier:
        courier_id = courier["id"]
        links = get_all_approved_links_for_courier(courier_id)
        current_link = get_approved_admin_link_for_courier(courier_id)
        if links:
            mensaje += "🚴 Repartidor:\n"
            last_move_by_link = {l["link_id"]: l["last_movement_at"] for l in links}
            current_link_id = None
            if current_link:
                team_name = current_link["team_name"] or "-"
                team_code = current_link["team_code"] or ""
                balance = current_link["balance"] if current_link["balance"] else 0
                label = "Plataforma" if team_code == "PLATFORM" else team_name
                if team_code:
                    label = "{} [{}]".format(label, team_code)
                current_link_id = current_link["link_id"]
                last_move = last_move_by_link.get(current_link_id) or "-"
                mensaje += "   Mi admin actual: {} : ${:,} | Último movimiento: {}\n".format(label, balance, last_move)

            others = [l for l in links if not current_link_id or l["link_id"] != current_link_id]
            if others:
                mensaje += "   Otros vínculos APPROVED:\n"
                for link in others:
                    team_name = link["team_name"] or "-"
                    team_code = link["team_code"] or ""
                    balance = link["balance"] if link["balance"] else 0
                    label = "Plataforma" if team_code == "PLATFORM" else team_name
                    if team_code:
                        label = "{} [{}]".format(label, team_code)
                    last_move = link["last_movement_at"] or "-"
                    mensaje += "   - {} : ${:,} | Último movimiento: {}\n".format(label, balance, last_move)
            mensaje += "\n"
            tiene_algo = True
        else:
            mensaje += "🚴 Repartidor:\n"
            mensaje += "   Sin vinculo aprobado con admin.\n"
            mensaje += "   Usa /recargar para solicitar recarga.\n\n"
            tiene_algo = True

    ally = get_ally_by_user_id(user_db_id)
    if ally:
        ally_id = ally["id"]
        links = get_all_approved_links_for_ally(ally_id)
        current_link = get_approved_admin_link_for_ally(ally_id)
        if links:
            mensaje += "🍕 Aliado:\n"
            last_move_by_link = {l["link_id"]: l["last_movement_at"] for l in links}
            current_link_id = None
            if current_link:
                team_name = current_link["team_name"] or "-"
                team_code = current_link["team_code"] or ""
                balance = current_link["balance"] if current_link["balance"] else 0
                label = "Plataforma" if team_code == "PLATFORM" else team_name
                if team_code:
                    label = "{} [{}]".format(label, team_code)
                current_link_id = current_link["link_id"]
                last_move = last_move_by_link.get(current_link_id) or "-"
                mensaje += "   Mi admin actual: {} : ${:,} | Último movimiento: {}\n".format(label, balance, last_move)

            others = [l for l in links if not current_link_id or l["link_id"] != current_link_id]
            if others:
                mensaje += "   Otros vínculos APPROVED:\n"
                for link in others:
                    team_name = link["team_name"] or "-"
                    team_code = link["team_code"] or ""
                    balance = link["balance"] if link["balance"] else 0
                    label = "Plataforma" if team_code == "PLATFORM" else team_name
                    if team_code:
                        label = "{} [{}]".format(label, team_code)
                    last_move = link["last_movement_at"] or "-"
                    mensaje += "   - {} : ${:,} | Último movimiento: {}\n".format(label, balance, last_move)
            mensaje += "\n"
            tiene_algo = True
        else:
            mensaje += "🍕 Aliado:\n"
            mensaje += "   Sin vinculo aprobado con admin.\n"
            mensaje += "   Usa /recargar para solicitar recarga.\n\n"
            tiene_algo = True

    if not tiene_algo:
        mensaje = "No tienes roles registrados.\nUsa /soy_repartidor o /soy_aliado para registrarte."

    if es_plataforma:
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ver movimientos", callback_data="admin_movimientos")]
        ])
        update.message.reply_text(mensaje, reply_markup=markup)
    else:
        update.message.reply_text(mensaje)




def cmd_recargar(update, context):
    """
    Comando /recargar - Inicia el flujo de solicitud de recarga.
    Determina el rol y muestra opciones de admin.
    """
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    courier = get_courier_by_user_id(user_db_id)
    ally = get_ally_by_user_id(user_db_id)
    admin = get_admin_by_user_id(user_db_id)

    # Determinar si es admin local (no plataforma)
    admin_local = None
    if admin:
        admin_id = admin["id"]
        admin_full = get_admin_by_id(admin_id)
        if admin_full:
            tc = admin_full["team_code"]
            if tc and tc != "PLATFORM":
                admin_local = admin_full

    roles = []
    if courier:
        roles.append(("COURIER", courier["id"], courier["full_name"] or "Repartidor"))
    if ally:
        roles.append(("ALLY", ally["id"], ally["business_name"] or "Aliado"))
    if admin_local:
        a_id = admin_local["id"]
        a_name = admin_local["team_name"]
        roles.append(("ADMIN", a_id, a_name or "Admin Local"))

    if not roles:
        update.message.reply_text(
            "Para solicitar recargas debes ser Repartidor, Aliado o Administrador Local.\n"
            "Usa /soy_repartidor, /soy_aliado o /soy_admin para registrarte."
        )
        return ConversationHandler.END

    if len(roles) == 1:
        # Solo un rol: ir directo a monto
        context.user_data["recargar_target_type"] = roles[0][0]
        context.user_data["recargar_target_id"] = roles[0][1]
        context.user_data["recargar_target_name"] = roles[0][2]
        update.message.reply_text(
            "Escribe el monto que deseas recargar (solo numeros).\n"
            "Ejemplo: 10000"
        )
        return RECARGAR_MONTO
    else:
        # Múltiples roles: preguntar como qué rol quiere recargar
        keyboard = []
        for role_type, role_id, role_name in roles:
            label_map = {"COURIER": "Repartidor", "ALLY": "Aliado", "ADMIN": "Admin Local"}
            keyboard.append([InlineKeyboardButton(
                "{}: {}".format(label_map.get(role_type, role_type), role_name),
                callback_data="recargar_role_{}_{}".format(role_type, role_id),
            )])
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="recargar_cancel")])
        update.message.reply_text(
            "Tienes multiples roles. Como cual deseas recargar?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return RECARGAR_ROL


def recargar_rol_callback(update, context):
    """Callback para seleccionar el rol con el que se quiere recargar."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "recargar_cancel":
        query.edit_message_text("Solicitud de recarga cancelada.")
        return ConversationHandler.END

    if not data.startswith("recargar_role_"):
        return RECARGAR_ROL

    # Parse: recargar_role_{TYPE}_{ID}
    parts = data.replace("recargar_role_", "").split("_", 1)
    if len(parts) != 2:
        query.edit_message_text("Error de formato.")
        return ConversationHandler.END

    role_type = parts[0]
    try:
        role_id = int(parts[1])
    except ValueError:
        query.edit_message_text("Error de formato.")
        return ConversationHandler.END

    if role_type == "COURIER":
        courier = get_courier_by_user_id(get_user_db_id_from_update(update))
        role_name = courier["full_name"] if courier else "Repartidor"
    elif role_type == "ALLY":
        ally = get_ally_by_user_id(get_user_db_id_from_update(update))
        role_name = ally["business_name"] if ally else "Aliado"
    elif role_type == "ADMIN":
        admin_full = get_admin_by_id(role_id)
        role_name = admin_full["team_name"] if admin_full else "Admin Local"
    else:
        query.edit_message_text("Rol no reconocido.")
        return ConversationHandler.END

    context.user_data["recargar_target_type"] = role_type
    context.user_data["recargar_target_id"] = role_id
    context.user_data["recargar_target_name"] = role_name

    query.edit_message_text(
        "Recargando como: {} ({})\n\n"
        "Escribe el monto que deseas recargar (solo numeros).\n"
        "Ejemplo: 10000".format(
            {"COURIER": "Repartidor", "ALLY": "Aliado", "ADMIN": "Admin Local"}.get(role_type, role_type),
            role_name,
        )
    )
    return RECARGAR_MONTO


def recargar_monto(update, context):
    """Recibe el monto de la recarga."""
    texto = update.message.text.strip().replace(".", "").replace(",", "")

    try:
        monto = int(texto)
    except ValueError:
        update.message.reply_text("Por favor ingresa solo numeros. Ejemplo: 10000")
        return RECARGAR_MONTO

    if monto < 1000:
        update.message.reply_text("El monto minimo es $1,000.")
        return RECARGAR_MONTO

    if monto > 1000000:
        update.message.reply_text("El monto maximo es $1,000,000.")
        return RECARGAR_MONTO

    context.user_data["recargar_monto"] = monto

    target_type = context.user_data["recargar_target_type"]
    target_id = context.user_data["recargar_target_id"]

    # Admin local: siempre recarga con plataforma
    if target_type == "ADMIN":
        platform = get_platform_admin()
        if not platform:
            update.message.reply_text("No hay administrador de plataforma configurado.")
            return ConversationHandler.END
        platform_id = platform["id"]
        context.user_data["recargar_admin_id"] = platform_id

        # Mostrar datos de pago de plataforma directamente
        payment_info = get_admin_payment_info(platform_id)
        if payment_info:
            info_text = "Datos de pago de Plataforma:\n\n"
            if payment_info["bank_name"]:
                info_text += "Banco: {}\n".format(payment_info["bank_name"])
            if payment_info["account_type"]:
                info_text += "Tipo: {}\n".format(payment_info["account_type"])
            if payment_info["account_number"]:
                info_text += "Cuenta: {}\n".format(payment_info["account_number"])
            if payment_info["nequi_number"]:
                info_text += "Nequi: {}\n".format(payment_info["nequi_number"])
            if payment_info["daviplata_number"]:
                info_text += "Daviplata: {}\n".format(payment_info["daviplata_number"])
            info_text += "\nMonto a pagar: ${:,}\n\n".format(monto)
            info_text += "Realiza el pago y envia el comprobante (foto)."
        else:
            info_text = (
                "Monto: ${:,}\n\n"
                "Contacta a Plataforma para obtener los datos de pago.\n"
                "Envia el comprobante (foto) cuando hayas pagado."
            ).format(monto)

        update.message.reply_text(info_text)
        return RECARGAR_COMPROBANTE

    # Courier/Ally: mostrar opciones de admin con vínculo APPROVED vigente
    if target_type == "COURIER":
        link = get_approved_admin_link_for_courier(target_id)
        approved_links = get_all_approved_links_for_courier(target_id)
    else:
        link = get_approved_admin_link_for_ally(target_id)
        approved_links = get_all_approved_links_for_ally(target_id)
    approved_admin_ids = {row["admin_id"] for row in approved_links} if approved_links else set()

    buttons = []

    if link and link["admin_id"] in approved_admin_ids:
        admin_id = link["admin_id"]
        team_name = link["team_name"] or "Mi admin"
        buttons.append([InlineKeyboardButton(
            f"Mi admin: {team_name}",
            callback_data=f"recargar_admin_{admin_id}"
        )])
        context.user_data["recargar_mi_admin_id"] = admin_id

    platform = get_platform_admin()
    if platform:
        platform_id = platform["id"]
        platform_name = platform["team_name"] or platform["full_name"] or "Plataforma"
        # Plataforma siempre disponible como fallback, excepto si ya aparece como "Mi admin"
        if not link or link["admin_id"] != platform_id:
            buttons.append([InlineKeyboardButton(
                f"Plataforma: {platform_name}",
                callback_data=f"recargar_admin_{platform_id}"
            )])

    if not buttons:
        update.message.reply_text(
            "No hay admins disponibles para procesar recargas.\n"
            "Contacta al soporte."
        )
        return ConversationHandler.END

    buttons.append([InlineKeyboardButton("Cancelar", callback_data="recargar_cancel")])

    update.message.reply_text(
        f"Monto: ${monto:,}\n\n"
        f"Selecciona a quien solicitar la recarga:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return RECARGAR_ADMIN


def recargar_admin_callback(update, context):
    """Callback para seleccionar admin y mostrar datos de pago."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "recargar_cancel":
        query.edit_message_text("Solicitud de recarga cancelada.")
        return ConversationHandler.END

    if not data.startswith("recargar_admin_"):
        return RECARGAR_ADMIN

    admin_id = int(data.replace("recargar_admin_", ""))

    target_type = context.user_data.get("recargar_target_type")
    target_id = context.user_data.get("recargar_target_id")
    if not target_type or not target_id:
        query.edit_message_text("Error: datos incompletos. Usa /recargar nuevamente.")
        return ConversationHandler.END

    if target_type == "COURIER":
        approved_links = get_all_approved_links_for_courier(target_id)
        allowed_admin_ids = {row["admin_id"] for row in approved_links}
    elif target_type == "ALLY":
        approved_links = get_all_approved_links_for_ally(target_id)
        allowed_admin_ids = {row["admin_id"] for row in approved_links}
    elif target_type == "ADMIN":
        platform_admin = get_platform_admin()
        platform_admin_id = platform_admin["id"] if platform_admin else None
        allowed_admin_ids = {platform_admin_id} if platform_admin_id else set()
    else:
        allowed_admin_ids = set()

    # Plataforma siempre habilitada como fallback para COURIER/ALLY
    if target_type in ("COURIER", "ALLY"):
        platform_admin = get_platform_admin()
        if platform_admin:
            allowed_admin_ids.add(platform_admin["id"])

    if admin_id not in allowed_admin_ids:
        query.edit_message_text("Seleccion invalida. Usa /recargar nuevamente.")
        return ConversationHandler.END

    # Si el admin seleccionado no es plataforma, verificar que este APPROVED
    platform_admin = get_platform_admin()
    platform_admin_id = platform_admin["id"] if platform_admin else None
    if admin_id != platform_admin_id:
        admin_status = get_admin_status_by_id(admin_id)
        if admin_status == "PENDING":
            query.edit_message_text(
                "Este administrador aun no ha cumplido con los requisitos para aprobar recargas. "
                "Por favor recarga con Plataforma para que puedas trabajar."
            )
            return ConversationHandler.END

    context.user_data["recargar_admin_id"] = admin_id

    monto = context.user_data.get("recargar_monto")

    # Obtener cuentas de pago activas del admin
    methods = list_payment_methods(admin_id, only_active=True)
    admin_row = get_admin_by_id(admin_id)
    admin_name = admin_row["full_name"] if admin_row else "Admin"

    if methods:
        pago_texto = f"Datos para el pago:\n\n"
        pago_texto += f"Monto a transferir: ${monto:,}\n\n"
        pago_texto += "Cuentas disponibles:\n\n"

        for m in methods:
            pago_texto += f"{m['method_name']}: {m['account_number']}\n"
            pago_texto += f"   Titular: {m['account_holder']}\n"
            if m["instructions"]:
                pago_texto += f"   {m['instructions']}\n"
            pago_texto += "\n"

        pago_texto += "Realiza la transferencia y envia una FOTO del comprobante."
    else:
        pago_texto = (
            f"Monto a transferir: ${monto:,}\n\n"
            f"Contacta a {admin_name} para obtener los datos de pago.\n\n"
            "Una vez realices el pago, envia una FOTO del comprobante."
        )

    query.edit_message_text(pago_texto)

    return RECARGAR_COMPROBANTE


def recargar_comprobante(update, context):
    """Recibe la foto del comprobante y crea la solicitud."""
    if not update.message.photo:
        update.message.reply_text("Por favor envia una FOTO del comprobante de pago.")
        return RECARGAR_COMPROBANTE

    # Obtener el file_id de la foto (mejor calidad)
    photo = update.message.photo[-1]
    proof_file_id = photo.file_id

    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    target_type = context.user_data.get("recargar_target_type")
    target_id = context.user_data.get("recargar_target_id")
    monto = context.user_data.get("recargar_monto")
    target_name = context.user_data.get("recargar_target_name", "")
    admin_id = context.user_data.get("recargar_admin_id")

    if not target_type or not target_id or not monto or not admin_id:
        update.message.reply_text("Error: datos incompletos. Usa /recargar nuevamente.")
        return ConversationHandler.END

    request_id = create_recharge_request(
        target_type=target_type,
        target_id=target_id,
        admin_id=admin_id,
        amount=monto,
        requested_by_user_id=user_db_id,
        proof_file_id=proof_file_id
    )
    if not request_id:
        update.message.reply_text(
            "Ya existe una recarga pendiente con este comprobante. "
            "Espera a que sea aprobada o rechazada antes de enviar otra."
        )
        return ConversationHandler.END

    update.message.reply_text(
        f"Solicitud de recarga enviada.\n\n"
        f"ID: #{request_id}\n"
        f"Monto: ${monto:,}\n"
        f"Estado: PENDIENTE\n\n"
        f"El admin verificara tu comprobante y procesara la recarga."
    )

    # Notificar al admin con la foto
    try:
        admin_row = get_admin_by_id(admin_id)
        if admin_row:
            admin_user_id = admin_row["user_id"]
            admin_user = get_user_by_id(admin_user_id)
            if admin_user:
                admin_telegram_id = admin_user["telegram_id"]
                tipo_label = "Repartidor" if target_type == "COURIER" else "Aliado"

                notif_text = (
                    f"Nueva solicitud de recarga #{request_id}\n\n"
                    f"De: {target_name} ({tipo_label})\n"
                    f"Monto: ${monto:,}\n\n"
                    f"Comprobante adjunto:"
                )

                buttons = [
                    [
                        InlineKeyboardButton("Aprobar", callback_data=f"recharge_approve_{request_id}"),
                        InlineKeyboardButton("Rechazar", callback_data=f"recharge_reject_{request_id}")
                    ]
                ]

                # Enviar foto con caption y botones
                context.bot.send_photo(
                    chat_id=admin_telegram_id,
                    photo=proof_file_id,
                    caption=notif_text,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                _schedule_important_alerts(
                    context,
                    alert_key="recharge_request_{}".format(request_id),
                    chat_id=admin_telegram_id,
                    reminder_text=(
                        "Recordatorio importante:\n"
                        "La solicitud de recarga #{} sigue pendiente.\n"
                        "Revisala en /recargas_pendientes o con los botones."
                    ).format(request_id),
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
    except Exception as e:
        logger.warning("No se pudo notificar al admin: %s", e)

    context.user_data.pop("recargar_target_type", None)
    context.user_data.pop("recargar_target_id", None)
    context.user_data.pop("recargar_monto", None)
    context.user_data.pop("recargar_target_name", None)
    context.user_data.pop("recargar_mi_admin_id", None)
    context.user_data.pop("recargar_admin_id", None)

    return ConversationHandler.END


def recargar_comprobante_texto(update, context):
    """Evita silencio cuando el flujo espera foto y el usuario envia texto."""
    texto = (update.message.text or "").strip().lower()
    if texto == "cancelar":
        context.user_data.clear()
        update.message.reply_text("Recarga cancelada.")
        return ConversationHandler.END
    update.message.reply_text(
        "Aun falta el comprobante.\n"
        "Envia una FOTO del comprobante o escribe Cancelar."
    )
    return RECARGAR_COMPROBANTE


def cmd_recargas_pendientes(update, context):
    """
    Comando /recargas_pendientes - Lista las solicitudes PENDING para el admin.
    Solo para admins.
    """
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    admin = get_admin_by_user_id(user_db_id)
    if not admin:
        update.message.reply_text("Este comando es solo para administradores.")
        return

    admin_id = admin["id"]
    admin_status = admin["status"]

    if admin_status != "APPROVED":
        update.message.reply_text("Tu cuenta de admin no esta aprobada.")
        return

    pendientes = list_pending_recharges_for_admin(admin_id)

    if not pendientes:
        update.message.reply_text("No tienes solicitudes de recarga pendientes.")
        return

    for req in pendientes:
        req_id = req["id"]
        target_type = req["target_type"]
        target_id = req["target_id"]
        amount = req["amount"]
        method = req["method"] or "-"
        note = req["note"] or "-"
        created_at = req["created_at"] or "-"
        target_name = req["target_name"] or "Desconocido"
        proof_file_id = req["proof_file_id"]

        tipo_label = "Repartidor" if target_type == "COURIER" else "Aliado"

        texto = (
            f"Solicitud #{req_id}\n"
            f"De: {target_name} ({tipo_label})\n"
            f"Monto: ${amount:,}\n"
            f"Metodo: {method}\n"
            f"Fecha: {created_at}\n"
        )

        buttons = [
            [
                InlineKeyboardButton("Aprobar", callback_data=f"recharge_approve_{req_id}"),
                InlineKeyboardButton("Rechazar", callback_data=f"recharge_reject_{req_id}")
            ],
            [
                InlineKeyboardButton("Ver comprobante", callback_data=f"recharge_proof_{req_id}")
            ],
        ]

        update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(buttons))


def _get_owned_recharge_request_or_error(request_id: int, actor_admin_id: int, actor_telegram_id: int):
    """
    Capa reusable de ownership para callbacks de recarga.
    Retorna: (req_dict | None, error_msg | None)
    """
    req = get_recharge_request(request_id)
    if not req:
        return None, "Solicitud no encontrada."

    if req["admin_id"] == actor_admin_id:
        return req, None

    if user_has_platform_admin(actor_telegram_id):
        return req, None

    return None, "Esta solicitud no te corresponde."


def recharge_proof_callback(update, context):
    """
    Callback para ver comprobante.
    Patron: ^recharge_proof_\\d+$
    """
    query = update.callback_query
    data = query.data

    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    admin = get_admin_by_user_id(user_db_id)
    if not admin:
        query.answer("No autorizado.", show_alert=True)
        return

    admin_id = admin["id"]
    admin_status = admin["status"]
    if admin_status != "APPROVED":
        query.answer("No autorizado.", show_alert=True)
        return

    if not data.startswith("recharge_proof_"):
        return

    request_id = int(data.replace("recharge_proof_", ""))
    req, ownership_error = _get_owned_recharge_request_or_error(request_id, admin_id, user_tg.id)
    if ownership_error:
        query.answer(ownership_error, show_alert=True)
        return

    proof_file_id = req["proof_file_id"]
    if not proof_file_id:
        query.answer("Sin comprobante.", show_alert=True)
        return

    try:
        context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=proof_file_id,
            caption=f"Comprobante de solicitud #{request_id}"
        )
        query.answer("Comprobante enviado.")
    except Exception as e:
        logger.warning("No se pudo enviar comprobante: %s", e)
        query.answer("No se pudo enviar el comprobante.", show_alert=True)


def recharge_callback(update, context):
    """
    Callback para aprobar/rechazar solicitudes de recarga.
    Patron: ^recharge_(approve|reject)_\\d+$
    """
    query = update.callback_query
    data = query.data

    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    admin = get_admin_by_user_id(user_db_id)
    if not admin:
        query.answer("No autorizado.", show_alert=True)
        return

    admin_id = admin["id"]
    admin_status = admin["status"]
    if admin_status != "APPROVED":
        query.answer("No autorizado.", show_alert=True)
        return

    if data.startswith("recharge_approve_"):
        request_id = int(data.replace("recharge_approve_", ""))
        _req, ownership_error = _get_owned_recharge_request_or_error(request_id, admin_id, user_tg.id)
        if ownership_error:
            query.answer(ownership_error, show_alert=True)
            return

        success, msg = approve_recharge_request(request_id, admin_id)

        if success:
            # Notificar al solicitante (ally/courier/admin) su nuevo saldo
            try:
                req_user_id = _req["requested_by_user_id"] if _req else None
                req_user = get_user_by_id(req_user_id) if req_user_id else None
                req_chat_id = req_user["telegram_id"] if req_user else None

                new_balance = None
                if _req and _req["target_type"] == "COURIER":
                    link = get_approved_admin_link_for_courier(_req["target_id"])
                    if link:
                        new_balance = link["balance"]
                elif _req and _req["target_type"] == "ALLY":
                    link = get_approved_admin_link_for_ally(_req["target_id"])
                    if link:
                        new_balance = link["balance"]
                elif _req and _req["target_type"] == "ADMIN":
                    new_balance = get_admin_balance(_req["target_id"])

                if req_chat_id and (new_balance is not None):
                    context.bot.send_message(
                        chat_id=req_chat_id,
                        text="Tu recarga #{} fue exitosa. Tu nuevo saldo es: ${:,}.".format(request_id, int(new_balance)),
                    )
                elif req_chat_id:
                    context.bot.send_message(
                        chat_id=req_chat_id,
                        text="Tu recarga #{} fue exitosa.".format(request_id),
                    )
            except Exception as e:
                logger.warning("No se pudo notificar al solicitante de la recarga #%s: %s", request_id, e)

            _resolve_important_alert(context, "recharge_request_{}".format(request_id))
            query.answer("Recarga aprobada.")
            suffix = f"\n\nAPROBADA por admin #{admin_id}"
            if query.message.text:
                query.edit_message_text(query.message.text + suffix)
            elif query.message.caption:
                query.edit_message_caption(query.message.caption + suffix)
            else:
                query.edit_message_text("Solicitud procesada." + suffix)
        else:
            query.answer(msg, show_alert=True)

    elif data.startswith("recharge_reject_"):
        request_id = int(data.replace("recharge_reject_", ""))
        _req, ownership_error = _get_owned_recharge_request_or_error(request_id, admin_id, user_tg.id)
        if ownership_error:
            query.answer(ownership_error, show_alert=True)
            return

        success, msg = reject_recharge_request(request_id, admin_id)

        if success:
            # Notificar al solicitante (ally/courier/admin) sobre el rechazo
            try:
                req_user_id = _req["requested_by_user_id"] if _req else None
                req_user = get_user_by_id(req_user_id) if req_user_id else None
                req_chat_id = req_user["telegram_id"] if req_user else None
                if req_chat_id:
                    context.bot.send_message(
                        chat_id=req_chat_id,
                        text=(
                            "Tu recarga #{} fue rechazada. "
                            "Comunicate con el administrador al que solicitaste tu recarga."
                        ).format(request_id),
                    )
            except Exception as e:
                logger.warning("No se pudo notificar rechazo al solicitante de la recarga #%s: %s", request_id, e)

            _resolve_important_alert(context, "recharge_request_{}".format(request_id))
            query.answer("Solicitud rechazada.")
            suffix = f"\n\nRECHAZADA por admin #{admin_id}"
            if query.message.text:
                query.edit_message_text(query.message.text + suffix)
            elif query.message.caption:
                query.edit_message_caption(query.message.caption + suffix)
            else:
                query.edit_message_text("Solicitud procesada." + suffix)
        else:
            query.answer(msg, show_alert=True)


# ============================================================
# PANEL DE RECARGAS — ADMIN DE PLATAFORMA (plat_rec_*)
# ============================================================

def plat_recargas_callback(update, context):
    """Panel de recargas para el Admin de Plataforma. Prefijo: plat_rec_"""
    query = update.callback_query
    query.answer()
    data = query.data
    user_id = update.effective_user.id

    if not user_has_platform_admin(user_id):
        query.answer("Solo el Admin de Plataforma puede usar este panel.", show_alert=True)
        return

    back_btn = InlineKeyboardButton("⬅ Volver", callback_data="plat_rec_menu")

    # ---- Menú principal ----
    if data == "plat_rec_menu":
        keyboard = [
            [InlineKeyboardButton("📋 Pendientes de todos los admins", callback_data="plat_rec_pending")],
            [InlineKeyboardButton("📊 Historial contable", callback_data="plat_rec_history")],
            [InlineKeyboardButton("⚠️ Alertas de admins locales", callback_data="plat_rec_alerts")],
            [InlineKeyboardButton("💳 Recarga directa a usuario", callback_data="plat_rdir_inicio")],
            [InlineKeyboardButton("⬅ Volver al panel", callback_data="admin_volver_panel")],
        ]
        query.edit_message_text(
            "Panel de Recargas\n\nSelecciona una vista:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ---- Todas las solicitudes PENDING agrupadas por admin ----
    if data == "plat_rec_pending":
        pendientes = list_all_pending_recharges(limit=50)
        if not pendientes:
            query.edit_message_text(
                "No hay solicitudes de recarga pendientes en el sistema.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
            return

        by_admin = {}
        for req in pendientes:
            aid = req["admin_id"]
            if aid not in by_admin:
                by_admin[aid] = {"admin_name": req["admin_name"], "count": 0, "total": 0}
            by_admin[aid]["count"] += 1
            by_admin[aid]["total"] += req["amount"]

        tipo_label = {"COURIER": "Repartidor", "ALLY": "Aliado", "ADMIN": "Admin"}
        lines = ["Solicitudes PENDIENTES ({} en total):\n".format(len(pendientes))]
        for req in pendientes:
            lines.append("#{} | {} | {} | ${:,}".format(
                req["id"],
                req["admin_name"],
                req["target_name"] or "-",
                req["amount"],
            ))

        lines.append("\nPor admin:")
        keyboard = []
        for aid, info in by_admin.items():
            lines.append("  {}: {} solicitud(es) — ${:,}".format(
                info["admin_name"], info["count"], info["total"]
            ))
            keyboard.append([InlineKeyboardButton(
                "🔔 Notificar a {}".format(info["admin_name"]),
                callback_data="plat_rec_notify_{}".format(aid)
            )])
        keyboard.append([back_btn])

        texto = "\n".join(lines)
        if len(texto) > 4000:
            texto = texto[:3950] + "\n...(truncado)"
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # ---- Historial contable (ledger RECHARGE) ----
    if data == "plat_rec_history":
        entries = list_recharge_ledger(limit=20)
        if not entries:
            query.edit_message_text(
                "No hay movimientos de recarga registrados aun.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
            return

        dest_label = {"COURIER": "Repartidor", "ALLY": "Aliado", "ADMIN": "Admin", "PLATFORM": "Plataforma"}
        lines = ["Historial de recargas (ultimas 20):\n"]
        for e in entries:
            fecha = (e["created_at"] or "")[:10]
            origen = e["from_name"] or e["from_type"] or "-"
            destino = e["to_name"] or e["to_type"] or "-"
            tipo = dest_label.get(e["to_type"], e["to_type"])
            lines.append("{} | {} -> {} ({}) | ${:,}".format(
                fecha, origen, destino, tipo, e["amount"]
            ))

        texto = "\n".join(lines)
        if len(texto) > 4000:
            texto = texto[:3950] + "\n...(truncado)"
        query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup([[back_btn]])
        )
        return

    # ---- Alertas: admins con pendientes o saldo bajo ----
    if data == "plat_rec_alerts":
        admins_data = get_admins_with_pending_count()
        alertas = [a for a in admins_data if a["pending_count"] > 0 or (a["balance"] or 0) < 60000]

        if not alertas:
            query.edit_message_text(
                "No hay alertas: todos los admins tienen saldo suficiente y sin pendientes.",
                reply_markup=InlineKeyboardMarkup([[back_btn]])
            )
            return

        lines = ["Alertas de admins locales:\n"]
        keyboard = []
        for a in alertas:
            balance = a["balance"] or 0
            pending = a["pending_count"]
            flags = []
            if pending > 0:
                flags.append("{} pendiente(s)".format(pending))
            if balance < 60000:
                flags.append("saldo bajo ${:,}".format(balance))
            lines.append("{}: {}".format(a["admin_name"], " | ".join(flags)))
            keyboard.append([InlineKeyboardButton(
                "🔔 Notificar a {}".format(a["admin_name"]),
                callback_data="plat_rec_notify_{}".format(a["admin_id"])
            )])
        keyboard.append([back_btn])

        query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ---- Notificar admin local ----
    if data.startswith("plat_rec_notify_"):
        admin_id = int(data.replace("plat_rec_notify_", ""))
        admins_data = get_admins_with_pending_count()
        target = next((a for a in admins_data if a["admin_id"] == admin_id), None)
        if not target:
            query.answer("Admin no encontrado.", show_alert=True)
            return

        telegram_id = target["telegram_id"]
        pending = target["pending_count"]
        balance = target["balance"] or 0
        admin_name = target["admin_name"]

        partes = ["Recordatorio de Plataforma:"]
        if pending > 0:
            partes.append(
                "Tienes {} solicitud(es) de recarga PENDIENTE(S) sin procesar.\n"
                "Revisalas con /recargas_pendientes".format(pending)
            )
        if balance < 60000:
            partes.append(
                "Tu saldo actual es ${:,}. Recarga tu cuenta para poder atender "
                "a tu equipo sin interrupciones.".format(balance)
            )

        try:
            context.bot.send_message(chat_id=telegram_id, text="\n\n".join(partes))
            query.answer("Notificacion enviada a {}.".format(admin_name))
        except Exception as e:
            logger.warning("plat_rec_notify admin_id=%s: %s", admin_id, e)
            query.answer("No se pudo enviar la notificacion.", show_alert=True)
        return


# ---- Recargas pendientes inline para admin local (local_recargas_pending_) ----

def local_recargas_pending_callback(update, context):
    """Muestra las recargas pendientes del admin local desde su panel /mi_admin."""
    query = update.callback_query
    query.answer()
    data = query.data

    if not data.startswith("local_recargas_pending_"):
        return

    admin_id = int(data.split("_")[-1])

    # Verificar que el solicitante es el propio admin
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    admin = get_admin_by_user_id(user_row["id"])
    if not admin or admin["id"] != admin_id:
        query.answer("No autorizado.", show_alert=True)
        return

    pendientes = list_pending_recharges_for_admin(admin_id)
    if not pendientes:
        query.edit_message_text(
            "No tienes solicitudes de recarga pendientes.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅ Volver", callback_data=f"local_my_team_{admin_id}")
            ]])
        )
        return

    for req in pendientes:
        req_id = req["id"]
        tipo = "Repartidor" if req["target_type"] == "COURIER" else "Aliado"
        texto = (
            "Solicitud #{}\n"
            "De: {} ({})\n"
            "Monto: ${:,}\n"
            "Metodo: {}\n"
            "Fecha: {}"
        ).format(
            req_id,
            req["target_name"] or "-",
            tipo,
            req["amount"],
            req["method"] or "-",
            (req["created_at"] or "-")[:16],
        )
        buttons = [
            [
                InlineKeyboardButton("Aprobar", callback_data=f"recharge_approve_{req_id}"),
                InlineKeyboardButton("Rechazar", callback_data=f"recharge_reject_{req_id}"),
            ],
            [InlineKeyboardButton("Ver comprobante", callback_data=f"recharge_proof_{req_id}")],
        ]
        query.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(buttons))

    query.edit_message_text(
        "Tienes {} solicitud(es) pendiente(s). Revisalas arriba.".format(len(pendientes))
    )


# ============================================================
# CONFIGURAR DATOS DE PAGO (ADMINS)
# ============================================================

def cmd_configurar_pagos(update, context):
    """
    Comando /configurar_pagos - Muestra menu de gestion de cuentas de pago.
    """
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    admin = get_admin_by_user_id(user_db_id)
    if not admin:
        update.message.reply_text("Este comando es solo para administradores.")
        return ConversationHandler.END

    admin_id = admin["id"]
    context.user_data["pago_admin_id"] = admin_id

    return mostrar_menu_pagos(update, context, admin_id, es_mensaje=True)


def cmd_configurar_pagos_callback(update, context):
    """Entry point del ConversationHandler de pagos desde el boton config_pagos."""
    query = update.callback_query
    query.answer()
    user_tg = query.from_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]
    admin = get_admin_by_user_id(user_db_id)
    if not admin:
        query.edit_message_text("Este menu es solo para administradores.")
        return ConversationHandler.END
    admin_id = admin["id"]
    context.user_data["pago_admin_id"] = admin_id
    return mostrar_menu_pagos(update, context, admin_id, es_mensaje=False)


def mostrar_menu_pagos(update, context, admin_id, es_mensaje=False):
    """Muestra el menu de cuentas de pago."""
    methods = list_payment_methods(admin_id, only_active=False)

    texto = "Tus cuentas de pago:\n\n"

    if methods:
        for m in methods:
            estado = "ON" if m["is_active"] == 1 else "OFF"
            texto += f"{'🟢' if m['is_active'] == 1 else '🔴'} {m['method_name']} - {m['account_number']} ({estado})\n"
        texto += "\n"
    else:
        texto += "(No tienes cuentas configuradas)\n\n"

    texto += "Selecciona una opcion:"

    buttons = [
        [InlineKeyboardButton("Agregar cuenta", callback_data="pagos_agregar")],
    ]

    if methods:
        buttons.append([InlineKeyboardButton("Gestionar cuentas", callback_data="pagos_gestionar")])

    buttons.append([InlineKeyboardButton("Cerrar", callback_data="pagos_cerrar")])

    if es_mensaje:
        update.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        update.callback_query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))

    return PAGO_MENU


def pagos_callback(update, context):
    """Callback para el menu de pagos."""
    query = update.callback_query
    query.answer()
    data = query.data

    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    admin = get_admin_by_user_id(user_db_id)
    if not admin:
        query.edit_message_text("No autorizado.")
        return ConversationHandler.END

    admin_id = admin["id"]
    context.user_data["pago_admin_id"] = admin_id

    if data == "pagos_cerrar":
        query.edit_message_text("Menu de pagos cerrado.")
        return ConversationHandler.END

    if data == "pagos_agregar":
        query.edit_message_text(
            "Agregar nueva cuenta de pago.\n\n"
            "Escribe el nombre del BANCO o BILLETERA:\n"
            "(Ejemplo: Nequi, Daviplata, Bancolombia, etc.)"
        )
        return PAGO_BANCO

    if data == "pagos_gestionar":
        methods = list_payment_methods(admin_id, only_active=False)

        if not methods:
            query.edit_message_text("No tienes cuentas para gestionar.")
            return PAGO_MENU

        texto = "Tus cuentas de pago:\n\nToca una para activar/desactivar:\n"

        buttons = []
        for m in methods:
            estado = "ON" if m["is_active"] == 1 else "OFF"
            emoji = "🟢" if m["is_active"] == 1 else "🔴"
            buttons.append([InlineKeyboardButton(
                f"{emoji} {m['method_name']} - {m['account_number']} ({estado})",
                callback_data=f"pagos_ver_{m['id']}"
            )])

        buttons.append([InlineKeyboardButton("Volver", callback_data="pagos_volver")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
        return PAGO_MENU

    if data == "pagos_volver":
        return mostrar_menu_pagos(update, context, admin_id, es_mensaje=False)

    if data.startswith("pagos_ver_"):
        method_id = int(data.replace("pagos_ver_", ""))
        method = get_payment_method_by_id(method_id)

        if not method:
            query.edit_message_text("Cuenta no encontrada.")
            return

        estado = "ACTIVA" if method["is_active"] == 1 else "INACTIVA"
        emoji = "🟢" if method["is_active"] == 1 else "🔴"

        texto = (
            f"{emoji} Cuenta {estado}\n\n"
            f"Banco/Billetera: {method['method_name']}\n"
            f"Numero: {method['account_number']}\n"
            f"Titular: {method['account_holder']}\n"
            f"Instrucciones: {method['instructions'] or '-'}\n"
        )

        buttons = []
        if method["is_active"] == 1:
            buttons.append([InlineKeyboardButton("Desactivar", callback_data=f"pagos_toggle_{method_id}_0")])
        else:
            buttons.append([InlineKeyboardButton("Activar", callback_data=f"pagos_toggle_{method_id}_1")])

        buttons.append([InlineKeyboardButton("Desactivar", callback_data=f"pagos_delete_{method_id}")])
        buttons.append([InlineKeyboardButton("Volver", callback_data="pagos_gestionar")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
        return PAGO_MENU

    if data.startswith("pagos_toggle_"):
        parts = data.replace("pagos_toggle_", "").split("_")
        method_id = int(parts[0])
        new_status = int(parts[1])

        toggle_payment_method(method_id, new_status)

        estado = "activada" if new_status == 1 else "desactivada"
        query.answer(f"Cuenta {estado}.")

        # Volver a mostrar la cuenta
        method = get_payment_method_by_id(method_id)
        if method:
            estado = "ACTIVA" if method["is_active"] == 1 else "INACTIVA"
            emoji = "🟢" if method["is_active"] == 1 else "🔴"

            texto = (
                f"{emoji} Cuenta {estado}\n\n"
                f"Banco/Billetera: {method['method_name']}\n"
                f"Numero: {method['account_number']}\n"
                f"Titular: {method['account_holder']}\n"
                f"Instrucciones: {method['instructions'] or '-'}\n"
            )

            buttons = []
            if method["is_active"] == 1:
                buttons.append([InlineKeyboardButton("Desactivar", callback_data=f"pagos_toggle_{method_id}_0")])
            else:
                buttons.append([InlineKeyboardButton("Activar", callback_data=f"pagos_toggle_{method_id}_1")])

            buttons.append([InlineKeyboardButton("Desactivar", callback_data=f"pagos_delete_{method_id}")])
            buttons.append([InlineKeyboardButton("Volver", callback_data="pagos_gestionar")])

            query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
        return PAGO_MENU

    if data.startswith("pagos_delete_"):
        method_id = int(data.replace("pagos_delete_", ""))
        deactivate_payment_method(method_id)
        query.answer("Cuenta desactivada.")

        # Volver a gestionar
        methods = list_payment_methods(admin_id, only_active=False)

        if not methods:
            return mostrar_menu_pagos(update, context, admin_id, es_mensaje=False)

        texto = "Tus cuentas de pago:\n\nToca una para activar/desactivar:\n"

        buttons = []
        for m in methods:
            estado = "ON" if m["is_active"] == 1 else "OFF"
            emoji = "🟢" if m["is_active"] == 1 else "🔴"
            buttons.append([InlineKeyboardButton(
                f"{emoji} {m['method_name']} - {m['account_number']} ({estado})",
                callback_data=f"pagos_ver_{m['id']}"
            )])

        buttons.append([InlineKeyboardButton("Volver", callback_data="pagos_volver")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(buttons))
        return PAGO_MENU

    return PAGO_MENU


def pago_banco(update, context):
    """Recibe el banco/billetera."""
    texto = update.message.text.strip()
    context.user_data["pago_banco"] = texto

    update.message.reply_text(
        "Escribe el NUMERO de cuenta o celular:"
    )
    return PAGO_TELEFONO


def pago_telefono(update, context):
    """Recibe el numero de telefono/cuenta."""
    texto = update.message.text.strip()
    context.user_data["pago_telefono"] = texto

    update.message.reply_text(
        "Escribe el NOMBRE DEL TITULAR de la cuenta:\n"
        "(Como aparece en la cuenta)"
    )
    return PAGO_TITULAR


def pago_titular(update, context):
    """Recibe el titular de la cuenta."""
    texto = update.message.text.strip()
    context.user_data["pago_titular"] = texto

    update.message.reply_text(
        "Escribe INSTRUCCIONES adicionales para el pago (opcional):\n"
        "(Ejemplo: 'Enviar a llave Nequi', 'Notificar por WhatsApp', etc.)\n\n"
        "Si no tienes instrucciones, escribe: ninguna"
    )
    return PAGO_INSTRUCCIONES


def pago_instrucciones(update, context):
    """Recibe las instrucciones y guarda la cuenta."""
    texto = update.message.text.strip()

    if texto.lower() in ["ninguna", "ninguno", "no", "na", "n/a", "-"]:
        instrucciones = None
    else:
        instrucciones = texto

    admin_id = context.user_data.get("pago_admin_id")

    method_id = create_payment_method(
        admin_id=admin_id,
        method_name=context.user_data.get("pago_banco"),
        account_number=context.user_data.get("pago_telefono"),
        account_holder=context.user_data.get("pago_titular"),
        instructions=instrucciones
    )

    resumen = (
        "Cuenta de pago agregada:\n\n"
        f"Banco/Billetera: {context.user_data.get('pago_banco')}\n"
        f"Numero: {context.user_data.get('pago_telefono')}\n"
        f"Titular: {context.user_data.get('pago_titular')}\n"
        f"Instrucciones: {instrucciones or '-'}\n\n"
        "Estado: ACTIVA\n\n"
        "Usa /configurar_pagos para gestionar tus cuentas."
    )

    update.message.reply_text(resumen)

    context.user_data.pop("pago_admin_id", None)
    context.user_data.pop("pago_telefono", None)
    context.user_data.pop("pago_banco", None)
    context.user_data.pop("pago_titular", None)

    return ConversationHandler.END


def admin_local_callback(update, context):
    query = update.callback_query
    if not query:
        return
    data = query.data
    query.answer()

    user_db_id = get_user_db_id_from_update(update)

    admin = get_admin_by_user_id(user_db_id)
    if not admin:
        query.edit_message_text("No autorizado.")
        return

    admin_id = admin["id"]

    # Seguridad extra SOLO para callbacks que terminan en admin_id
    if data.startswith(("local_check_", "local_status_", "local_couriers_pending_")):
        try:
            target_admin_id = int(data.split("_")[-1])
            if target_admin_id != admin_id:
                query.edit_message_text("No autorizado.")
                return
        except Exception:
            query.edit_message_text("No autorizado.")
            return

    if data.startswith("local_check_"):
        admin_full = get_admin_by_id(admin_id)
        status = admin_full["status"] or "-"
        team_code = admin_full["team_code"] or "-"

        # Administrador de Plataforma: siempre operativo
        if team_code == "PLATFORM":
            keyboard = [
                [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            ]
            try:
                query.edit_message_text(
                    "Panel Administrador Local\n\n"
                    "Como Administrador de Plataforma, tu operación está habilitada.\n"
                    "Selecciona una opción:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    query.answer("Sin cambios.")
                    return
                raise
            return

        # FASE 1: Mostrar requisitos como información, NO como bloqueo
        ok, msg, stats = admin_puede_operar(admin_id)

        total_couriers = stats.get("total_couriers", 0)
        couriers_ok = stats.get("couriers_ok", 0)
        total_allies = stats.get("total_allies", 0)
        allies_ok = stats.get("allies_ok", 0)
        admin_bal = stats.get("admin_balance", 0)

        estado_msg = (
            "📊 Estado del equipo:\n"
            "• Aliados vinculados: {} (con saldo >= $5,000: {})\n"
            "• Repartidores vinculados: {} (con saldo >= $5,000: {})\n"
            "• Tu saldo master: ${:,}\n\n"
            "Requisitos para operar:\n"
            "• 5 aliados con saldo >= $5,000: {}\n"
            "• 10 repartidores con saldo >= $5,000: {}\n"
            "• Saldo master >= $60,000: {}\n\n"
        ).format(
            total_allies, allies_ok,
            total_couriers, couriers_ok,
            admin_bal,
            "OK" if allies_ok >= 5 else "Faltan {}".format(5 - allies_ok),
            "OK" if couriers_ok >= 10 else "Faltan {}".format(10 - couriers_ok),
            "OK" if admin_bal >= 60000 else "Faltan ${:,}".format(60000 - admin_bal),
        )
        keyboard = [
            [InlineKeyboardButton("⏳ Repartidores pendientes", callback_data=f"local_couriers_pending_{admin_id}")],
            [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            [InlineKeyboardButton("🔄 Verificar de nuevo", callback_data=f"local_check_{admin_id}")],
        ]
        try:
            query.edit_message_text(
                "Panel Administrador Local\n\n"
                f"Estado: {status}\n\n"
                + estado_msg +
                "Panel habilitado. Selecciona una opción:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except BadRequest as e:
            if "Message is not modified" in str(e):
                query.answer("Sin cambios.")
                return
            raise
        return

    if data.startswith("local_status_"):
        admin_full = get_admin_by_id(admin_id)
        status = admin_full["status"] or "-"
        team_code = admin_full["team_code"] or "-"

        # Administrador de Plataforma: mensaje especial
        if team_code == "PLATFORM":
            total = count_admin_couriers(admin_id)
            texto = (
                "Estado de tu cuenta (Admin Plataforma):\n\n"
                f"Estado: {status}\n"
                f"Repartidores vinculados: {total}\n\n"
                "Como Administrador de Plataforma, tu operación está habilitada."
            )
            keyboard = []
            query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)
            return

        # Administrador Local normal: mostrar requisitos
        total = count_admin_couriers(admin_id)
        okb = count_admin_couriers_with_min_balance(admin_id, 5000)

        texto = (
            "Estado de tu cuenta (Admin Local):\n\n"
            f"Estado: {status}\n"
            f"Repartidores vinculados: {total}\n"
            f"Con saldo >= 5000: {okb}\n\n"
            "Recuerda: Aprobado no siempre significa operativo; el sistema valida requisitos en tiempo real."
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("local_couriers_pending_"):
        try:
            pendientes = get_pending_couriers_by_admin(admin_id)
        except Exception as e:
            logger.error("get_pending_couriers_by_admin: %s", e)
            query.edit_message_text("Error consultando pendientes de tu equipo.")
            return

        if not pendientes:
            query.edit_message_text(
                "No tienes repartidores pendientes por aprobar en tu equipo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data=f"local_check_{admin_id}")]
                ])
            )
            return

        keyboard = []
        for c in pendientes:
            courier_id = c["courier_id"]
            full_name = c["full_name"] or ""
            keyboard.append([
                InlineKeyboardButton(
                    f"ID {courier_id} - {full_name}",
                    callback_data=f"local_courier_view_{courier_id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data=f"local_check_{admin_id}")])

        query.edit_message_text(
            "Repartidores pendientes (tu equipo). Toca uno para ver detalle:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("local_courier_view_"):
        courier_id = int(data.split("_")[-1])

        courier = get_courier_by_id(courier_id)
        if not courier:
            query.edit_message_text("No se encontró el repartidor.")
            return

        residence_address = courier["residence_address"]
        residence_lat = courier["residence_lat"]
        residence_lng = courier["residence_lng"]
        if residence_lat is not None and residence_lng is not None:
            residence_location = "{}, {}".format(residence_lat, residence_lng)
            maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(residence_lat, residence_lng)
        else:
            residence_location = "No disponible"
            maps_line = ""

        texto = (
            "REPARTIDOR (pendiente de tu equipo)\n\n"
            f"ID: {courier['id']}\n"
            f"Nombre: {courier['full_name']}\n"
            f"Documento: {courier['id_number']}\n"
            f"Teléfono: {courier['phone']}\n"
            f"Ciudad: {courier['city']}\n"
            f"Barrio: {courier['barrio']}\n"
            "Dirección residencia: {}\n"
            "Ubicación residencia: {}\n"
            "{}"
            f"Placa: {courier['plate'] or '-'}\n"
            f"Moto: {courier['bike_type'] or '-'}\n"
        ).format(
            residence_address or "No registrada",
            residence_location,
            maps_line,
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"local_courier_approve_{courier_id}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"local_courier_reject_{courier_id}")
            ],
            [InlineKeyboardButton("⛔ Bloquear", callback_data=f"local_courier_block_{courier_id}")],
            [InlineKeyboardButton("⬅ Volver", callback_data=f"local_couriers_pending_{admin_id}")]
        ]

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))

        cedula_front = courier["cedula_front_file_id"]
        cedula_back = courier["cedula_back_file_id"]
        selfie = courier["selfie_file_id"]
        if cedula_front or cedula_back or selfie:
            try:
                if cedula_front:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_front, caption="Cédula frente")
                if cedula_back:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_back, caption="Cédula reverso")
                if selfie:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=selfie, caption="Selfie")
            except Exception as e:
                logger.warning("No se pudieron enviar fotos del repartidor %s: %s", courier_id, e)

        return

    # Bloquear acciones de aprobar/rechazar/bloquear si Admin Local no esta APPROVED
    if data.startswith(("local_courier_approve_", "local_courier_reject_", "local_courier_block_")):
        admin_full = get_admin_by_id(admin_id)
        admin_status = admin_full["status"] if admin_full else None
        if admin_status != "APPROVED":
            query.answer("Acceso restringido: tu Admin Local no esta APPROVED.", show_alert=True)
            return

    if data.startswith("local_courier_approve_"):
        courier_id = int(data.split("_")[-1])
        result = approve_role_registration(update.effective_user.id, "COURIER", courier_id)
        if not result.get("ok"):
            query.edit_message_text(result.get("message") or "Error aprobando repartidor.")
            return

        try:
            courier_telegram_id = get_courier_approval_notification_chat_id(courier_id)
            if courier_telegram_id:
                _send_role_welcome_message(
                    context,
                    "COURIER",
                    courier_telegram_id,
                    profile=result.get("profile"),
                    bonus_granted=bool(result.get("bonus_granted")),
                )
        except Exception as e:
            logger.warning("Error notificando repartidor (local approve): %s", e)

        _resolve_important_alert(context, "team_courier_pending_{}_{}".format(admin_id, courier_id))
        query.edit_message_text(
            "✅ Repartidor aprobado en tu equipo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_courier_reject_confirm_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            logger.error("update_admin_courier_status REJECTED: %s", e)
            query.edit_message_text("Error rechazando repartidor. Revisa logs.")
            return

        _resolve_important_alert(context, "team_courier_pending_{}_{}".format(admin_id, courier_id))

        try:
            courier_tg = get_courier_approval_notification_chat_id(courier_id)
            if courier_tg:
                context.bot.send_message(
                    chat_id=courier_tg,
                    text=(
                        "Tu solicitud de ingreso al equipo fue RECHAZADA.\n\n"
                        "Si crees que es un error, contacta directamente al administrador."
                    ),
                )
        except Exception as _e:
            logger.warning("local_courier_reject_confirm notify: %s", _e)

        query.edit_message_text(
            "Repartidor rechazado para tu equipo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_courier_reject_cancel_"):
        courier_id = int(data.split("_")[-1])
        query.edit_message_text(
            "Rechazo cancelado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_courier_reject_"):
        courier_id = int(data.split("_")[-1])
        courier = get_courier_by_id(courier_id)
        nombre = courier["full_name"] if courier else "ID {}".format(courier_id)
        query.edit_message_text(
            "Vas a rechazar a {} de tu equipo.\n\n"
            "Esta accion rechaza su solicitud de ingreso. "
            "El repartidor no podra operar en tu equipo.\n\n"
            "Confirmas el rechazo?".format(nombre),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Si, rechazar", callback_data=f"local_courier_reject_confirm_{courier_id}"),
                    InlineKeyboardButton("Cancelar", callback_data=f"local_courier_reject_cancel_{courier_id}"),
                ]
            ])
        )
        return

    if data.startswith("local_courier_block_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "INACTIVE", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            logger.error("update_admin_courier_status INACTIVE: %s", e)
            query.edit_message_text("Error bloqueando repartidor. Revisa logs.")
            return

        _resolve_important_alert(context, "team_courier_pending_{}_{}".format(admin_id, courier_id))
        query.edit_message_text(
            "⛔ Repartidor bloqueado en tu equipo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    # ---- ALIADOS PENDIENTES ----

    if data.startswith("local_allies_pending_"):
        try:
            pendientes = get_pending_allies_by_admin(admin_id)
        except Exception as e:
            logger.error("get_pending_allies_by_admin: %s", e)
            query.edit_message_text("Error consultando aliados pendientes de tu equipo.")
            return

        if not pendientes:
            query.edit_message_text(
                "No tienes aliados pendientes por aprobar en tu equipo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data=f"local_check_{admin_id}")]
                ])
            )
            return

        keyboard = []
        for a in pendientes:
            ally_id_row = a["ally_id"]
            bname = a["business_name"] or ""
            keyboard.append([InlineKeyboardButton(
                f"ID {ally_id_row} - {bname}",
                callback_data=f"local_ally_view_{ally_id_row}"
            )])
        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data=f"local_check_{admin_id}")])
        query.edit_message_text(
            "Aliados pendientes (tu equipo). Toca uno para ver detalle:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("local_ally_view_"):
        ally_id_val = int(data.split("_")[-1])
        ally = get_ally_by_id(ally_id_val)
        if not ally:
            query.edit_message_text("No se encontró el aliado.")
            return

        texto = (
            "ALIADO (pendiente de tu equipo)\n\n"
            "ID: {}\n"
            "Negocio: {}\n"
            "Propietario: {}\n"
            "Telefono: {}\n"
            "Ciudad: {}\n"
            "Barrio: {}\n"
            "Direccion: {}\n"
        ).format(
            ally["id"],
            ally["business_name"] or "-",
            ally["owner_name"] or "-",
            ally["phone"] or "-",
            ally["city"] or "-",
            ally["barrio"] or "-",
            ally["address"] or "-",
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"local_ally_approve_{ally_id_val}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"local_ally_reject_{ally_id_val}"),
            ],
            [InlineKeyboardButton("⬅ Volver", callback_data=f"local_allies_pending_{admin_id}")]
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        cedula_front = ally["cedula_front_file_id"]
        cedula_back = ally["cedula_back_file_id"]
        selfie = ally["selfie_file_id"]
        if cedula_front or cedula_back or selfie:
            try:
                if cedula_front:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_front, caption="Cédula frente")
                if cedula_back:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_back, caption="Cédula reverso")
                if selfie:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=selfie, caption="Selfie")
            except Exception as e:
                logger.warning("No se pudieron enviar fotos del aliado %s: %s", ally_id_val, e)
        return

    if data.startswith("local_ally_approve_") or data.startswith("local_ally_reject_"):
        ally_id_val = int(data.split("_")[-1])
        admin_full = get_admin_by_id(admin_id)
        admin_status = admin_full["status"] if admin_full else None
        if admin_status != "APPROVED":
            query.edit_message_text("Tu cuenta de administrador no está APPROVED. No puedes aprobar/rechazar aliados.")
            return

        if data.startswith("local_ally_approve_"):
            result = approve_role_registration(update.effective_user.id, "ALLY", ally_id_val)
            if not result.get("ok"):
                query.edit_message_text(result.get("message") or "Error aprobando aliado.")
                return

            try:
                ally_telegram_id = get_ally_approval_notification_chat_id(ally_id_val)
                if ally_telegram_id:
                    _send_role_welcome_message(
                        context,
                        "ALLY",
                        ally_telegram_id,
                        profile=result.get("profile"),
                        bonus_granted=bool(result.get("bonus_granted")),
                    )
            except Exception as e:
                logger.warning("Error notificando aliado (local approve): %s", e)

            _resolve_important_alert(context, "team_ally_pending_{}_{}".format(admin_id, ally_id_val))
            query.edit_message_text(
                "✅ Aliado aprobado en tu equipo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_allies_pending_{admin_id}")]
                ])
            )
        else:
            try:
                upsert_admin_ally_link(admin_id, ally_id_val, "REJECTED")
            except Exception as e:
                logger.error("local_ally_reject: %s", e)
                query.edit_message_text("Error rechazando aliado. Revisa logs.")
                return
            _resolve_important_alert(context, "team_ally_pending_{}_{}".format(admin_id, ally_id_val))
            query.edit_message_text(
                "❌ Aliado rechazado para tu equipo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_allies_pending_{admin_id}")]
                ])
            )
        return

    # ---- MI EQUIPO ----

    if data.startswith("local_my_team_"):
        keyboard = [
            [InlineKeyboardButton("🚚 Mis repartidores", callback_data=f"local_team_couriers_{admin_id}")],
            [InlineKeyboardButton("🏪 Mis aliados", callback_data=f"local_team_allies_{admin_id}")],
            [InlineKeyboardButton("⬅ Volver", callback_data=f"local_check_{admin_id}")],
        ]
        query.edit_message_text("Mi equipo. Selecciona:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("local_team_couriers_"):
        approved = get_couriers_by_admin_and_status(admin_id, "APPROVED")
        inactive = get_couriers_by_admin_and_status(admin_id, "INACTIVE")
        members = list(approved) + list(inactive)
        if not members:
            query.edit_message_text(
                "No tienes repartidores en tu equipo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data=f"local_my_team_{admin_id}")]
                ])
            )
            return
        keyboard = []
        for c in members:
            cid = c["courier_id"]
            cname = c["full_name"] or ""
            cstatus = c["status"]
            keyboard.append([InlineKeyboardButton(
                f"{cname} [{cstatus}]",
                callback_data=f"local_team_courier_view_{cid}"
            )])
        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data=f"local_my_team_{admin_id}")])
        query.edit_message_text(
            "Mis repartidores. Toca uno para gestionar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("local_team_allies_"):
        approved = get_allies_by_admin_and_status(admin_id, "APPROVED")
        inactive = get_allies_by_admin_and_status(admin_id, "INACTIVE")
        members = list(approved) + list(inactive)
        if not members:
            query.edit_message_text(
                "No tienes aliados en tu equipo.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅ Volver", callback_data=f"local_my_team_{admin_id}")]
                ])
            )
            return
        keyboard = []
        for a in members:
            aid = a["ally_id"]
            aname = a["business_name"] or ""
            astatus = a["status"]
            keyboard.append([InlineKeyboardButton(
                f"{aname} [{astatus}]",
                callback_data=f"local_team_ally_view_{aid}"
            )])
        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data=f"local_my_team_{admin_id}")])
        query.edit_message_text(
            "Mis aliados. Toca uno para gestionar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("local_team_courier_view_"):
        courier_id = int(data.split("_")[-1])
        courier = get_courier_by_id(courier_id)
        if not courier:
            query.edit_message_text("No se encontró el repartidor.")
            return
        link = get_admin_link_for_courier(courier_id)
        link_status = link["link_status"] if link else "?"
        link_balance = link["balance"] if link else 0
        texto = (
            "Repartidor de tu equipo\n\n"
            "Nombre: {}\n"
            "Telefono: {}\n"
            "Estado en equipo: {}\n"
            "Saldo: ${:,}\n"
            "Placa: {}\n"
            "Moto: {}\n"
        ).format(
            courier["full_name"] or "-",
            courier["phone"] or "-",
            link_status,
            link_balance,
            courier["plate"] or "-",
            courier["bike_type"] or "-",
        )
        if link_status == "APPROVED":
            action_btn = InlineKeyboardButton("⏸ Inactivar", callback_data=f"local_courier_inactivate_{courier_id}")
        elif link_status == "INACTIVE":
            action_btn = InlineKeyboardButton("▶ Activar", callback_data=f"local_courier_activate_{courier_id}")
        else:
            action_btn = None
        keyboard = []
        if action_btn:
            keyboard.append([action_btn])
        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data=f"local_team_couriers_{admin_id}")])
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("local_team_ally_view_"):
        ally_id_val = int(data.split("_")[-1])
        ally = get_ally_by_id(ally_id_val)
        if not ally:
            query.edit_message_text("No se encontró el aliado.")
            return
        link = get_admin_link_for_ally(ally_id_val)
        link_status = link["link_status"] if link else "?"
        link_balance = link["balance"] if link else 0
        texto = (
            "Aliado de tu equipo\n\n"
            "Negocio: {}\n"
            "Propietario: {}\n"
            "Telefono: {}\n"
            "Estado en equipo: {}\n"
            "Saldo: ${:,}\n"
        ).format(
            ally["business_name"] or "-",
            ally["owner_name"] or "-",
            ally["phone"] or "-",
            link_status,
            link_balance,
        )
        if link_status == "APPROVED":
            action_btn = InlineKeyboardButton("⏸ Inactivar", callback_data=f"local_ally_inactivate_{ally_id_val}")
        elif link_status == "INACTIVE":
            action_btn = InlineKeyboardButton("▶ Activar", callback_data=f"local_ally_activate_{ally_id_val}")
        else:
            action_btn = None
        keyboard = []
        if action_btn:
            keyboard.append([action_btn])
        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data=f"local_team_allies_{admin_id}")])
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("local_courier_activate_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            logger.error("local_courier_activate: %s", e)
            query.edit_message_text("Error activando repartidor.")
            return
        query.edit_message_text(
            "✅ Repartidor activado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a mi equipo", callback_data=f"local_team_couriers_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_courier_inactivate_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "INACTIVE", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            logger.error("local_courier_inactivate: %s", e)
            query.edit_message_text("Error inactivando repartidor.")
            return
        query.edit_message_text(
            "⏸ Repartidor inactivado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a mi equipo", callback_data=f"local_team_couriers_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_ally_activate_"):
        ally_id_val = int(data.split("_")[-1])
        try:
            upsert_admin_ally_link(admin_id, ally_id_val, "APPROVED")
        except Exception as e:
            logger.error("local_ally_activate: %s", e)
            query.edit_message_text("Error activando aliado.")
            return
        query.edit_message_text(
            "✅ Aliado activado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a mi equipo", callback_data=f"local_team_allies_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_ally_inactivate_"):
        ally_id_val = int(data.split("_")[-1])
        try:
            upsert_admin_ally_link(admin_id, ally_id_val, "INACTIVE")
        except Exception as e:
            logger.error("local_ally_inactivate: %s", e)
            query.edit_message_text("Error inactivando aliado.")
            return
        query.edit_message_text(
            "⏸ Aliado inactivado.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a mi equipo", callback_data=f"local_team_allies_{admin_id}")]
            ])
        )
        return

    query.edit_message_text("Opción no reconocida.")

def ally_approval_callback(update, context):
    """Maneja el boton de aprobar aliados (solo Admin Plataforma). Rechazo va por rechazar_conv."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador de plataforma puede usar estos botones.", show_alert=True)
        return

    partes = data.split("_")  # ally_approve_3
    if len(partes) != 3 or partes[0] != "ally" or partes[1] != "approve":
        query.answer("Datos de boton no validos.", show_alert=True)
        return

    try:
        ally_id = int(partes[2])
    except ValueError:
        query.answer("ID de aliado no valido.", show_alert=True)
        return

    result = approve_role_registration(update.effective_user.id, "ALLY", ally_id)
    if not result.get("ok"):
        query.answer(result.get("message") or "No se pudo aprobar el aliado.", show_alert=True)
        return

    _resolve_important_alert(context, "ally_registration_{}".format(ally_id))

    ally = result.get("profile")
    if not ally:
        query.edit_message_text("No se encontro el aliado despues de actualizar.")
        return

    business_name = ally["business_name"]

    try:
        msg = _build_role_welcome_message("ALLY", profile=ally, bonus_granted=bool(result.get("bonus_granted")), reactivated=False)
        u = get_user_by_id(ally["user_id"])
        context.bot.send_message(chat_id=u["telegram_id"], text=msg)
    except Exception as e:
        logger.warning("Error notificando aliado: %s", e)

    query.answer()
    query.edit_message_text("El aliado '{}' ha sido APROBADO.".format(business_name))


# ============================================================
# REGISTRAR INGRESO EXTERNO (Admin Plataforma)
# ============================================================

def ingreso_iniciar_callback(update, context):
    """Punto de entrada al flujo de registro de ingreso externo."""
    query = update.callback_query
    query.answer()
    if not user_has_platform_admin(query.from_user.id):
        query.edit_message_text("Acceso restringido al Administrador de Plataforma.")
        return ConversationHandler.END
    query.edit_message_text(
        "Registrar ingreso externo a la Sociedad.\n\n"
        "Este dinero se acredita al fondo de la Sociedad Domiquerendona,\n"
        "no a tu saldo personal.\n\n"
        "Escribe el monto recibido (solo numeros).\n"
        "Ejemplo: 50000\n\n"
        "Escribe Cancelar para salir."
    )
    return INGRESO_MONTO


def ingreso_monto_handler(update, context):
    """Captura y valida el monto."""
    texto = (update.message.text or "").strip()
    if texto.lower() == "cancelar":
        context.user_data.pop("ingreso_monto", None)
        update.message.reply_text("Registro de ingreso cancelado.")
        return ConversationHandler.END
    try:
        monto = int(texto.replace(",", "").replace(".", "").replace(" ", ""))
    except ValueError:
        update.message.reply_text("Monto invalido. Escribe solo numeros. Ejemplo: 50000")
        return INGRESO_MONTO
    if monto < 1000:
        update.message.reply_text("El monto minimo es $1,000.")
        return INGRESO_MONTO
    if monto > 50000000:
        update.message.reply_text("El monto maximo por registro es $50,000,000.")
        return INGRESO_MONTO
    context.user_data["ingreso_monto"] = monto
    keyboard = [
        [InlineKeyboardButton("Efectivo", callback_data="ingreso_metodo_Efectivo")],
        [InlineKeyboardButton("Nequi", callback_data="ingreso_metodo_Nequi")],
        [InlineKeyboardButton("Transferencia bancaria", callback_data="ingreso_metodo_Transferencia")],
        [InlineKeyboardButton("Cancelar", callback_data="ingreso_cancelar")],
    ]
    update.message.reply_text(
        "Monto: ${:,}\n\nSelecciona el metodo de pago recibido:".format(monto),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return INGRESO_METODO


def ingreso_metodo_callback(update, context):
    """Captura el metodo y pide una nota opcional."""
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "ingreso_cancelar":
        context.user_data.pop("ingreso_monto", None)
        query.edit_message_text("Registro de ingreso cancelado.")
        return ConversationHandler.END
    if not data.startswith("ingreso_metodo_"):
        return INGRESO_METODO
    metodo = data.replace("ingreso_metodo_", "")
    context.user_data["ingreso_metodo"] = metodo
    monto = context.user_data.get("ingreso_monto", 0)
    query.edit_message_text(
        "Monto: ${:,}\n"
        "Metodo: {}\n\n"
        "Escribe una nota o referencia (quien pago, numero de transaccion, etc.).\n"
        "O escribe 'sin nota' para omitirla.".format(monto, metodo)
    )
    return INGRESO_NOTA


def ingreso_nota_handler(update, context):
    """Registra el ingreso y confirma al admin."""
    user_tg = update.effective_user
    nota_texto = (update.message.text or "").strip()
    if nota_texto.lower() == "cancelar":
        context.user_data.pop("ingreso_monto", None)
        context.user_data.pop("ingreso_metodo", None)
        update.message.reply_text("Registro de ingreso cancelado.")
        return ConversationHandler.END
    nota = None if nota_texto.lower() == "sin nota" else nota_texto
    monto = context.user_data.get("ingreso_monto")
    metodo = context.user_data.get("ingreso_metodo")
    if not monto or not metodo:
        update.message.reply_text("Error en el flujo. Vuelve a intentarlo desde el panel.")
        return ConversationHandler.END
    admin = get_admin_by_telegram_id(user_tg.id)
    if not admin:
        update.message.reply_text("No se encontro tu perfil de administrador.")
        return ConversationHandler.END
    admin_id = admin["id"]
    try:
        register_platform_income(admin_id=admin_id, amount=monto, method=metodo, note=nota)
    except Exception as e:
        logger.error("register_platform_income: %s", e)
        update.message.reply_text("Error al registrar el ingreso. Revisa los logs.")
        return ConversationHandler.END
    context.user_data.pop("ingreso_monto", None)
    context.user_data.pop("ingreso_metodo", None)
    nuevo_balance_sociedad = get_sociedad_balance()
    update.message.reply_text(
        "Ingreso registrado correctamente en la Sociedad.\n\n"
        "Monto: ${:,}\n"
        "Metodo: {}\n"
        "{}Nuevo saldo Sociedad: ${:,}".format(
            monto,
            metodo,
            "Nota: {}\n".format(nota) if nota else "",
            nuevo_balance_sociedad,
        )
    )
    return ConversationHandler.END



# =============================================================================
# ConversationHandlers (no referencian menu, se definen aquí)
# =============================================================================

recargar_conv = ConversationHandler(
    entry_points=[
        CommandHandler("recargar", cmd_recargar),
        MessageHandler(Filters.regex(r'^(Recargar|Recargar repartidor)$'), cmd_recargar),
    ],
    states={
        RECARGAR_ROL: [CallbackQueryHandler(recargar_rol_callback)],
        RECARGAR_MONTO: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, recargar_monto)],
        RECARGAR_ADMIN: [CallbackQueryHandler(recargar_admin_callback, pattern=r"^recargar_")],
        RECARGAR_COMPROBANTE: [
            MessageHandler(Filters.photo, recargar_comprobante),
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, recargar_comprobante_texto),
        ],
    },
    fallbacks=[
        CommandHandler("recargar", cmd_recargar),
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="recargar_conv",
    persistent=True,
)

configurar_pagos_conv = ConversationHandler(
    entry_points=[
        CommandHandler("configurar_pagos", cmd_configurar_pagos),
        CallbackQueryHandler(cmd_configurar_pagos_callback, pattern=r"^config_pagos$"),
    ],
    states={
        PAGO_MENU: [CallbackQueryHandler(pagos_callback, pattern=r"^pagos_")],
        PAGO_TELEFONO: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pago_telefono)],
        PAGO_BANCO: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pago_banco)],
        PAGO_TITULAR: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pago_titular)],
        PAGO_INSTRUCCIONES: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, pago_instrucciones)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    name="configurar_pagos_conv",
    persistent=True,
)

ingreso_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(ingreso_iniciar_callback, pattern=r"^ingreso_iniciar$"),
    ],
    states={
        INGRESO_MONTO: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ingreso_monto_handler)],
        INGRESO_METODO: [CallbackQueryHandler(ingreso_metodo_callback, pattern=r"^ingreso_")],
        INGRESO_NOTA: [MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, ingreso_nota_handler)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="ingreso_conv",
    persistent=True,
)


# =============================================================================
# RECARGA DIRECTA POR ADMIN DE PLATAFORMA (recarga_directa_conv)
# Entry: callback plat_rdir_inicio
# Prefijo callbacks: plat_rdir_   |  Prefijo user_data: recdir_
# Solo accesible para Admin de Plataforma.
# Flujo: tipo de usuario → seleccionar usuario → monto → nota → confirmar
# =============================================================================

_RECDIR_TIPO_LABEL = {"COURIER": "Repartidor", "ALLY": "Aliado", "ADMIN": "Admin Local"}


def _recdir_cancelar(update_or_query, context):
    """Limpia user_data del flujo y termina la conversacion."""
    for k in ("recdir_tipo", "recdir_target_id", "recdir_target_name", "recdir_monto", "recdir_nota"):
        context.user_data.pop(k, None)
    if hasattr(update_or_query, "message") and update_or_query.message:
        update_or_query.message.reply_text("Recarga directa cancelada.")
    elif hasattr(update_or_query, "edit_message_text"):
        try:
            update_or_query.edit_message_text("Recarga directa cancelada.")
        except Exception:
            pass
    return ConversationHandler.END


def recarga_directa_inicio(update, context):
    """Entry point del flujo de recarga directa. Verifica que sea Admin Plataforma."""
    query = update.callback_query
    query.answer()

    if not user_has_platform_admin(update.effective_user.id):
        query.edit_message_text("Solo el Admin de Plataforma puede hacer recargas directas.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("Repartidor", callback_data="plat_rdir_tipo_COURIER")],
        [InlineKeyboardButton("Aliado", callback_data="plat_rdir_tipo_ALLY")],
        [InlineKeyboardButton("Admin Local", callback_data="plat_rdir_tipo_ADMIN")],
        [InlineKeyboardButton("Cancelar", callback_data="plat_rdir_cancel")],
    ]
    query.edit_message_text(
        "Recarga directa\n\n"
        "Selecciona el tipo de usuario a recargar:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return RECARGA_DIR_TIPO


def recarga_directa_tipo_callback(update, context):
    """Recibe el tipo seleccionado y muestra la lista de usuarios correspondiente."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "plat_rdir_cancel":
        return _recdir_cancelar(query, context)

    if not data.startswith("plat_rdir_tipo_"):
        return RECARGA_DIR_TIPO

    tipo = data.replace("plat_rdir_tipo_", "")
    if tipo not in ("COURIER", "ALLY", "ADMIN"):
        query.edit_message_text("Tipo no reconocido.")
        return ConversationHandler.END

    context.user_data["recdir_tipo"] = tipo
    label = _RECDIR_TIPO_LABEL.get(tipo, tipo)

    if tipo == "COURIER":
        usuarios = get_all_active_couriers()
        if not usuarios:
            query.edit_message_text(
                "No hay repartidores APPROVED en el sistema.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="plat_rdir_cancel")]]),
            )
            return RECARGA_DIR_TIPO
        keyboard = []
        for u in usuarios:
            nombre = u["full_name"] or "Sin nombre"
            saldo = u["balance"] if u["balance"] is not None else 0
            team = u["link_team_name"] or "Sin equipo"
            keyboard.append([InlineKeyboardButton(
                "{} | ${:,} | {}".format(nombre, saldo, team),
                callback_data="plat_rdir_usr_{}".format(u["courier_id"]),
            )])
    elif tipo == "ALLY":
        usuarios = get_all_active_allies()
        if not usuarios:
            query.edit_message_text(
                "No hay aliados APPROVED en el sistema.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="plat_rdir_cancel")]]),
            )
            return RECARGA_DIR_TIPO
        keyboard = []
        for u in usuarios:
            nombre = u["business_name"] or u["owner_name"] or "Sin nombre"
            saldo = u["balance"] if u["balance"] is not None else 0
            team = u["link_team_name"] or "Sin equipo"
            keyboard.append([InlineKeyboardButton(
                "{} | ${:,} | {}".format(nombre, saldo, team),
                callback_data="plat_rdir_usr_{}".format(u["ally_id"]),
            )])
    else:  # ADMIN
        usuarios = get_all_local_admins_approved()
        if not usuarios:
            query.edit_message_text(
                "No hay admins locales APPROVED en el sistema.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancelar", callback_data="plat_rdir_cancel")]]),
            )
            return RECARGA_DIR_TIPO
        keyboard = []
        for u in usuarios:
            nombre = u["team_name"] or u["full_name"] or "Sin nombre"
            saldo = u["balance"] if u["balance"] is not None else 0
            code = u["team_code"] or ""
            label_btn = "{} [{}] | ${:,}".format(nombre, code, saldo) if code else "{} | ${:,}".format(nombre, saldo)
            keyboard.append([InlineKeyboardButton(
                label_btn,
                callback_data="plat_rdir_usr_{}".format(u["admin_id"]),
            )])

    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="plat_rdir_cancel")])
    query.edit_message_text(
        "Selecciona el {} a recargar:".format(_RECDIR_TIPO_LABEL.get(tipo, tipo)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return RECARGA_DIR_TIPO


def recarga_directa_usuario_callback(update, context):
    """Recibe el usuario seleccionado y solicita el monto."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "plat_rdir_cancel":
        return _recdir_cancelar(query, context)

    if not data.startswith("plat_rdir_usr_"):
        return RECARGA_DIR_TIPO

    try:
        target_id = int(data.replace("plat_rdir_usr_", ""))
    except ValueError:
        query.edit_message_text("Error de formato.")
        return ConversationHandler.END

    tipo = context.user_data.get("recdir_tipo")
    if tipo == "COURIER":
        usuarios = get_all_active_couriers()
        match = next((u for u in usuarios if u["courier_id"] == target_id), None)
        target_name = match["full_name"] if match else "Repartidor #{}".format(target_id)
    elif tipo == "ALLY":
        usuarios = get_all_active_allies()
        match = next((u for u in usuarios if u["ally_id"] == target_id), None)
        target_name = (match["business_name"] or match["owner_name"]) if match else "Aliado #{}".format(target_id)
    else:
        usuarios = get_all_local_admins_approved()
        match = next((u for u in usuarios if u["admin_id"] == target_id), None)
        target_name = (match["team_name"] or match["full_name"]) if match else "Admin #{}".format(target_id)

    context.user_data["recdir_target_id"] = target_id
    context.user_data["recdir_target_name"] = target_name

    query.edit_message_text(
        "Recarga directa a: {} ({})\n\n"
        "Escribe el monto a recargar (solo numeros, minimo $1,000).\n"
        "Ejemplo: 50000".format(target_name, _RECDIR_TIPO_LABEL.get(tipo, tipo))
    )
    return RECARGA_DIR_MONTO


def recarga_directa_monto_handler(update, context):
    """Recibe el monto y solicita una nota opcional."""
    texto = update.message.text.strip().replace(".", "").replace(",", "")
    try:
        monto = int(texto)
    except ValueError:
        update.message.reply_text("Por favor ingresa solo numeros. Ejemplo: 50000")
        return RECARGA_DIR_MONTO

    if monto < 1000:
        update.message.reply_text("El monto minimo es $1,000.")
        return RECARGA_DIR_MONTO

    if monto > 5000000:
        update.message.reply_text("El monto maximo por recarga directa es $5,000,000.")
        return RECARGA_DIR_MONTO

    context.user_data["recdir_monto"] = monto

    tipo = context.user_data.get("recdir_tipo", "")
    nombre = context.user_data.get("recdir_target_name", "")

    keyboard = [[InlineKeyboardButton("Sin nota — Confirmar recarga", callback_data="plat_rdir_sin_nota")],
                [InlineKeyboardButton("Cancelar", callback_data="plat_rdir_cancel")]]
    update.message.reply_text(
        "Monto: ${:,}\n"
        "Destino: {} ({})\n\n"
        "Escribe una nota descriptiva (motivo, referencia, etc.)\n"
        "o usa el boton para confirmar sin nota.".format(
            monto, nombre, _RECDIR_TIPO_LABEL.get(tipo, tipo)
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return RECARGA_DIR_NOTA


def recarga_directa_nota_handler(update, context):
    """Recibe la nota de texto y muestra la confirmacion final."""
    nota = update.message.text.strip()
    if nota.lower() == "cancelar":
        return _recdir_cancelar(update, context)

    context.user_data["recdir_nota"] = nota
    return _recdir_mostrar_confirmacion(update.message.reply_text, context)


def recarga_directa_confirmar_callback(update, context):
    """Callback: sin nota o confirmar recarga."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "plat_rdir_cancel":
        return _recdir_cancelar(query, context)

    if data == "plat_rdir_sin_nota":
        context.user_data["recdir_nota"] = None
        return _recdir_mostrar_confirmacion(query.edit_message_text, context)

    if data == "plat_rdir_confirmar":
        return _recdir_ejecutar(query, context)

    return RECARGA_DIR_NOTA


def _recdir_mostrar_confirmacion(send_fn, context):
    """Muestra el resumen de la recarga directa para confirmacion final."""
    tipo = context.user_data.get("recdir_tipo", "")
    nombre = context.user_data.get("recdir_target_name", "")
    monto = context.user_data.get("recdir_monto", 0)
    nota = context.user_data.get("recdir_nota")

    resumen = (
        "CONFIRMAR RECARGA DIRECTA\n\n"
        "Tipo: {}\n"
        "Destino: {}\n"
        "Monto: ${:,}\n"
        "{}Nota: {}\n\n"
        "El saldo saldra de la Sociedad.\n"
        "Esta accion no se puede deshacer."
    ).format(
        _RECDIR_TIPO_LABEL.get(tipo, tipo),
        nombre,
        monto,
        "",
        nota if nota else "(sin nota)",
    )

    keyboard = [
        [InlineKeyboardButton("Confirmar recarga", callback_data="plat_rdir_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="plat_rdir_cancel")],
    ]
    send_fn(resumen, reply_markup=InlineKeyboardMarkup(keyboard))
    return RECARGA_DIR_NOTA


def _recdir_ejecutar(query, context):
    """Ejecuta la recarga directa y notifica al destinatario."""
    user_tg = query.from_user
    admin = get_admin_by_telegram_id(user_tg.id)
    if not admin:
        query.edit_message_text("Error: no se encontro tu perfil de administrador.")
        return ConversationHandler.END

    platform_admin_id = admin["id"]
    user_row = ensure_user(user_tg.id, user_tg.username)
    platform_user_id = user_row["id"]

    tipo = context.user_data.get("recdir_tipo")
    target_id = context.user_data.get("recdir_target_id")
    monto = context.user_data.get("recdir_monto")
    nota = context.user_data.get("recdir_nota")
    nombre = context.user_data.get("recdir_target_name", "")

    if not all([tipo, target_id, monto]):
        query.edit_message_text("Error: datos incompletos. Usa el flujo nuevamente.")
        return ConversationHandler.END

    success, msg = direct_recharge_by_platform(
        target_type=tipo,
        target_id=target_id,
        platform_admin_id=platform_admin_id,
        platform_user_id=platform_user_id,
        amount=monto,
        note=nota,
    )

    for k in ("recdir_tipo", "recdir_target_id", "recdir_target_name", "recdir_monto", "recdir_nota"):
        context.user_data.pop(k, None)

    if not success:
        query.edit_message_text("Error al ejecutar la recarga: {}".format(msg))
        return ConversationHandler.END

    # Notificar al destinatario en Telegram
    telegram_id_destino = None
    nuevo_saldo = None
    try:
        if tipo == "COURIER":
            courier = get_courier_by_id(target_id)
            if courier:
                user_dest = get_user_by_id(courier["user_id"])
                if user_dest:
                    telegram_id_destino = user_dest["telegram_id"]
            link = get_approved_admin_link_for_courier(target_id)
            nuevo_saldo = link["balance"] if link else None
        elif tipo == "ALLY":
            ally = get_ally_by_id(target_id)
            if ally:
                user_dest = get_user_by_id(ally["user_id"])
                if user_dest:
                    telegram_id_destino = user_dest["telegram_id"]
            link = get_approved_admin_link_for_ally(target_id)
            nuevo_saldo = link["balance"] if link else None
        elif tipo == "ADMIN":
            admin_dest = get_admin_by_id(target_id)
            if admin_dest:
                user_dest = get_user_by_id(admin_dest["user_id"])
                if user_dest:
                    telegram_id_destino = user_dest["telegram_id"]
            nuevo_saldo = get_admin_balance(target_id)
    except Exception as e:
        logger.warning("recarga_directa: no se pudo obtener telegram_id del destinatario: %s", e)

    if telegram_id_destino:
        try:
            msg_destino = "Tu saldo fue recargado por Plataforma.\n\nMonto: ${:,}".format(monto)
            if nuevo_saldo is not None:
                msg_destino += "\nNuevo saldo: ${:,}".format(int(nuevo_saldo))
            if nota:
                msg_destino += "\nNota: {}".format(nota)
            query.bot.send_message(chat_id=telegram_id_destino, text=msg_destino)
        except Exception as e:
            logger.warning("recarga_directa: no se pudo notificar al destinatario: %s", e)

    confirmacion = (
        "Recarga directa ejecutada.\n\n"
        "Destino: {} ({})\n"
        "Monto: ${:,}\n"
        "{}Nuevo saldo: {}"
    ).format(
        nombre,
        _RECDIR_TIPO_LABEL.get(tipo, tipo),
        monto,
        "Nota: {}\n".format(nota) if nota else "",
        "${:,}".format(int(nuevo_saldo)) if nuevo_saldo is not None else "N/D",
    )
    query.edit_message_text(confirmacion)
    return ConversationHandler.END


recarga_directa_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(recarga_directa_inicio, pattern=r"^plat_rdir_inicio$"),
    ],
    states={
        RECARGA_DIR_TIPO: [
            CallbackQueryHandler(recarga_directa_usuario_callback, pattern=r"^plat_rdir_usr_\d+$"),
            CallbackQueryHandler(recarga_directa_tipo_callback, pattern=r"^plat_rdir_(tipo_|cancel)"),
        ],
        RECARGA_DIR_MONTO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, recarga_directa_monto_handler),
        ],
        RECARGA_DIR_NOTA: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, recarga_directa_nota_handler),
            CallbackQueryHandler(recarga_directa_confirmar_callback, pattern=r"^plat_rdir_(sin_nota|confirmar|cancel)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="recarga_directa_conv",
    persistent=True,
)


# ---------------------------------------------------------------------------
# admin_mi_saldo — Vista de saldo en tiempo real para cualquier admin
# Entry: callback admin_mi_saldo
# Muestra: saldo actual, resumen HOY (ingresos/egresos), alerta si saldo bajo
# ---------------------------------------------------------------------------

MIN_ADMIN_OPERATING_BALANCE_DISPLAY = 2000  # Umbral para alerta visual de saldo bajo


def admin_mi_saldo_callback(update, context):
    """Muestra el saldo actual del admin con resumen de movimientos de hoy."""
    query = update.callback_query
    query.answer()
    telegram_id = update.effective_user.id
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin:
        query.edit_message_text("No se encontro tu perfil de administrador.")
        return

    admin_id = admin["id"]
    is_platform = admin.get("team_code") == "PLATFORM"
    datos = get_admin_saldo_hoy(admin_id)
    balance = datos["balance"]
    alerta = balance < MIN_ADMIN_OPERATING_BALANCE_DISPLAY

    if alerta:
        estado_icon = "SALDO BAJO"
        alerta_line = "\nATENCION: Tu saldo personal esta bajo del minimo (${:,}).\n".format(
            MIN_ADMIN_OPERATING_BALANCE_DISPLAY)
    else:
        estado_icon = "OK"
        alerta_line = ""

    # Construir resumen personal de hoy
    hoy_lines = []
    if datos["fees_estandar_hoy"]:
        hoy_lines.append("  Fees estandar recibidos:   +${:,}".format(datos["fees_estandar_hoy"]))
    if datos["comisiones_hoy"]:
        hoy_lines.append("  Comisiones especiales:     +${:,}".format(datos["comisiones_hoy"]))
    if datos["subs_hoy"]:
        hoy_lines.append("  Suscripciones:             +${:,}".format(datos["subs_hoy"]))
    if datos.get("sociedad_advance_hoy"):
        hoy_lines.append("  Retiro de Sociedad:        +${:,}".format(datos["sociedad_advance_hoy"]))
    if datos["plat_fee_pagado_hoy"]:
        hoy_lines.append("  Fee plataforma pagado:     -${:,}".format(datos["plat_fee_pagado_hoy"]))
    if datos["tech_fee_pagado_hoy"]:
        hoy_lines.append("  Desarrollo tecnologico:    -${:,}".format(datos["tech_fee_pagado_hoy"]))
    if not is_platform and datos["recargas_salientes_hoy"]:
        hoy_lines.append("  Recargas aprobadas:        -${:,}".format(datos["recargas_salientes_hoy"]))

    if hoy_lines:
        resumen_hoy = "\nMovimientos personales de hoy ({}):\n".format(datos["fecha"]) + "\n".join(hoy_lines)
        neto = datos["total_ingresos_hoy"] - datos["total_egresos_hoy"]
        signo = "+" if neto >= 0 else ""
        resumen_hoy += "\n  Neto del dia:              {}${:,}".format(signo, neto)
    else:
        resumen_hoy = "\nMovimientos personales de hoy ({}): sin movimientos.".format(datos["fecha"])

    team_name = admin.get("team_name") or "Admin"

    if is_platform:
        # Para Admin Plataforma: mostrar saldo personal + saldo Sociedad
        sociedad_id = get_platform_sociedad_id()
        soc = get_sociedad_saldo_hoy(sociedad_id) if sociedad_id else None
        soc_balance = soc["balance"] if soc else 0

        soc_lines = []
        if soc:
            if soc["ingresos_hoy"]:
                soc_lines.append("  Ingresos externos:         +${:,}".format(soc["ingresos_hoy"]))
            if soc["plat_fees_hoy"]:
                soc_lines.append("  Fees de plataforma:        +${:,}".format(soc["plat_fees_hoy"]))
            if soc["subs_hoy"]:
                soc_lines.append("  Suscripciones (plataforma):+${:,}".format(soc["subs_hoy"]))
            if soc["recargas_hoy"]:
                soc_lines.append("  Recargas aprobadas:        -${:,}".format(soc["recargas_hoy"]))
            if soc["retiros_hoy"]:
                soc_lines.append("  Retiros a tu saldo:        -${:,}".format(soc["retiros_hoy"]))

        if soc_lines:
            resumen_soc = "\nMovimientos Sociedad de hoy ({}):\n".format(datos["fecha"]) + "\n".join(soc_lines)
            neto_soc = soc["total_ingresos_hoy"] - soc["total_egresos_hoy"]
            signo_soc = "+" if neto_soc >= 0 else ""
            resumen_soc += "\n  Neto del dia:              {}${:,}".format(signo_soc, neto_soc)
        else:
            resumen_soc = "\nMovimientos Sociedad de hoy ({}): sin movimientos.".format(datos["fecha"])

        texto = (
            "Mis saldos — {}\n\n"
            "Saldo personal (ganancias equipo): ${:,} [{}]{}{}\n"
            "Saldo Sociedad (fondos operativos): ${:,}{}"
        ).format(
            team_name,
            balance, estado_icon, alerta_line, resumen_hoy,
            soc_balance, resumen_soc,
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Retirar de Sociedad a mi saldo", callback_data="admin_sociedad_retiro")],
            [InlineKeyboardButton("Ver mis movimientos personales", callback_data="admin_movimientos")],
        ])
    else:
        texto = (
            "Mi saldo — {}\n\n"
            "Saldo actual: ${:,} [{}]{}{}"
        ).format(
            team_name, balance, estado_icon, alerta_line, resumen_hoy,
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ver historial de movimientos", callback_data="admin_movimientos")],
        ])

    query.edit_message_text(texto, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# Flujo "Retirar de Sociedad a mi saldo personal" (Admin Plataforma)
# Entry: callback admin_sociedad_retiro
# ---------------------------------------------------------------------------

def sociedad_retiro_iniciar_callback(update, context):
    """Punto de entrada: Admin Plataforma retira fondos de Sociedad a su saldo personal."""
    query = update.callback_query
    query.answer()
    if not user_has_platform_admin(query.from_user.id):
        query.edit_message_text("Acceso restringido al Administrador de Plataforma.")
        return ConversationHandler.END
    soc_balance = get_sociedad_balance()
    if soc_balance <= 0:
        query.edit_message_text(
            "La Sociedad no tiene saldo disponible para retirar.\n\n"
            "Saldo Sociedad: ${:,}".format(soc_balance)
        )
        return ConversationHandler.END
    query.edit_message_text(
        "Retirar fondos de la Sociedad a tu saldo personal.\n\n"
        "Saldo disponible en Sociedad: ${:,}\n\n"
        "Escribe el monto a retirar (solo numeros).\n"
        "Escribe Cancelar para salir.".format(soc_balance)
    )
    return SOCIEDAD_RETIRO_MONTO


def sociedad_retiro_monto_handler(update, context):
    """Captura el monto, confirma y ejecuta la transferencia Sociedad → personal."""
    texto = (update.message.text or "").strip()
    if texto.lower() == "cancelar":
        update.message.reply_text("Retiro cancelado.")
        return ConversationHandler.END
    try:
        monto = int(texto.replace(",", "").replace(".", "").replace(" ", ""))
    except ValueError:
        update.message.reply_text("Monto invalido. Escribe solo numeros. Ejemplo: 50000")
        return SOCIEDAD_RETIRO_MONTO
    if monto < 1000:
        update.message.reply_text("El monto minimo es $1,000.")
        return SOCIEDAD_RETIRO_MONTO
    if monto > 500000000:
        update.message.reply_text("El monto maximo por retiro es $500,000,000.")
        return SOCIEDAD_RETIRO_MONTO

    admin = get_admin_by_telegram_id(update.effective_user.id)
    if not admin:
        update.message.reply_text("No se encontro tu perfil de administrador.")
        return ConversationHandler.END
    admin_id = admin["id"]
    try:
        transfer_sociedad_to_platform(platform_admin_id=admin_id, amount=monto)
    except ValueError as e:
        update.message.reply_text("No se pudo realizar el retiro: {}".format(e))
        return ConversationHandler.END
    except Exception as e:
        logger.error("sociedad_retiro: %s", e)
        update.message.reply_text("Error al procesar el retiro. Revisa los logs.")
        return ConversationHandler.END

    nuevo_personal = get_admin_balance(admin_id)
    nuevo_soc = get_sociedad_balance()
    update.message.reply_text(
        "Retiro realizado correctamente.\n\n"
        "Monto retirado:       ${:,}\n"
        "Tu saldo personal:    ${:,}\n"
        "Saldo Sociedad:       ${:,}".format(monto, nuevo_personal, nuevo_soc)
    )
    return ConversationHandler.END


sociedad_retiro_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(sociedad_retiro_iniciar_callback, pattern=r"^admin_sociedad_retiro$"),
    ],
    states={
        SOCIEDAD_RETIRO_MONTO: [
            MessageHandler(Filters.text & ~Filters.command & ~CANCELAR_VOLVER_MENU_FILTER, sociedad_retiro_monto_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="sociedad_retiro_conv",
    persistent=True,
)


# admin_movimientos — Historial de movimientos del saldo master (PLATFORM)
# Entry: callback admin_movimientos
# Periodo: admin_movimientos_hoy / semana / mes / todo
# ---------------------------------------------------------------------------

_KIND_LABELS = {
    "INCOME": "Ingreso externo",
    "FEE_INCOME": "Fee cobrado",
    "PLATFORM_FEE": "Fee plataforma",
    "RECHARGE": "Recarga aprobada",
    "SUBSCRIPTION_PLATFORM_SHARE": "Suscripcion (plataforma)",
    "SUBSCRIPTION_ADMIN_SHARE": "Suscripcion (admin)",
    "SPECIAL_ORDER_COMMISSION": "Comision pedido especial",
    "SPECIAL_ORDER_PLATFORM_FEE": "Fee plataforma pedido especial",
    "TECH_DEV_FEE": "Desarrollo tecnologico (2%)",
    "SOCIEDAD_ADVANCE": "Retiro de Sociedad a saldo personal",
}

def _movimientos_keyboard(is_platform=False):
    rows = [
        [
            InlineKeyboardButton("Hoy", callback_data="admin_movimientos_hoy"),
            InlineKeyboardButton("Semana", callback_data="admin_movimientos_semana"),
        ],
        [
            InlineKeyboardButton("Este mes", callback_data="admin_movimientos_mes"),
            InlineKeyboardButton("Todo", callback_data="admin_movimientos_todo"),
        ],
    ]
    if is_platform:
        rows.append([
            InlineKeyboardButton("Sociedad — Hoy", callback_data="admin_movimientos_soc_hoy"),
            InlineKeyboardButton("Sociedad — Semana", callback_data="admin_movimientos_soc_semana"),
        ])
        rows.append([
            InlineKeyboardButton("Sociedad — Este mes", callback_data="admin_movimientos_soc_mes"),
            InlineKeyboardButton("Sociedad — Todo", callback_data="admin_movimientos_soc_todo"),
        ])
    return InlineKeyboardMarkup(rows)


def admin_movimientos_callback(update, context):
    """Muestra selector de periodo para ver movimientos del saldo master."""
    query = update.callback_query
    query.answer()
    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    admin = get_admin_by_user_id(user_row["id"])
    is_platform = (admin and (admin.get("team_code") or "").upper() == "PLATFORM")
    query.edit_message_text(
        "Movimientos del saldo master — selecciona un periodo:",
        reply_markup=_movimientos_keyboard(is_platform=is_platform),
    )


def admin_movimientos_periodo_callback(update, context):
    """Muestra movimientos del ledger para el periodo elegido (cuenta personal o sociedad)."""
    from datetime import datetime, timezone, timedelta
    query = update.callback_query
    query.answer()

    user_tg = update.effective_user
    user_row = ensure_user(user_tg.id, user_tg.username)
    admin = get_admin_by_user_id(user_row["id"])
    if not admin:
        query.answer("No tienes perfil de administrador.", show_alert=True)
        return

    # Determinar si es cuenta personal o sociedad
    data = query.data  # admin_movimientos_hoy / admin_movimientos_soc_mes / etc.
    parts = data.split("_")  # ['admin', 'movimientos', 'soc', 'mes'] o ['admin', 'movimientos', 'mes']
    es_sociedad = "soc" in parts
    periodo = parts[-1]  # hoy, semana, mes, todo

    if es_sociedad:
        target_id = get_platform_sociedad_id()
        cuenta_label = "Sociedad"
    else:
        target_id = admin["id"]
        cuenta_label = "Cuenta personal"

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if periodo == "hoy":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        periodo_label = "Hoy"
    elif periodo == "semana":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        periodo_label = "Esta semana"
    elif periodo == "mes":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        periodo_label = "Este mes"
    else:
        start = None
        periodo_label = "Todo el historial"

    start_s = start.strftime("%Y-%m-%d %H:%M:%S") if start else None
    movimientos = get_admin_ledger_movements(target_id, start_s=start_s, limit=30, is_sociedad=es_sociedad)

    label = "{} — {}".format(cuenta_label, periodo_label)
    if not movimientos:
        texto = "Sin movimientos para: " + label
    else:
        lineas = ["Movimientos — {}\n".format(label)]
        for m in movimientos:
            kind_label = _KIND_LABELS.get(m["kind"], m["kind"])
            signo = "+" if m["direction"] == "IN" else "-"
            fecha = m["created_at"][:10] if m["created_at"] else ""
            nota = m["note"] or ""
            nota_corta = "  " + nota[:28] if nota else ""
            lineas.append("{} {} ${:,}  {}{}".format(signo, kind_label, m["amount"], fecha, nota_corta))
        texto = "\n".join(lineas)
        if len(movimientos) == 30:
            texto += "\n(mostrando ultimos 30)"

    is_platform = (admin and (admin.get("team_code") or "").upper() == "PLATFORM")
    query.edit_message_text(texto, reply_markup=_movimientos_keyboard(is_platform=is_platform))


# ---------------------------------------------------------------------------
# ally_suscripcion_conv — Aliado ve estado y renueva su suscripcion
# Entry: callback ally_mi_suscripcion
# ---------------------------------------------------------------------------

from services import (
    get_ally_by_telegram_id,
    get_approved_admin_link_for_ally,
    get_subscription_summary_for_ally,
    pay_ally_subscription,
)


def ally_suscripcion_start(update, context):
    query = update.callback_query
    query.answer()
    telegram_id = update.effective_user.id
    ally = get_ally_by_telegram_id(telegram_id)
    if not ally:
        query.edit_message_text("No tienes perfil de aliado.")
        return ConversationHandler.END

    ally_id = ally["id"]
    link = get_approved_admin_link_for_ally(ally_id)
    if not link:
        query.edit_message_text("No tienes un administrador asignado.")
        return ConversationHandler.END

    admin_id = link["admin_id"]
    context.user_data["subs_ally_id"] = ally_id
    context.user_data["subs_admin_id"] = admin_id

    info = get_subscription_summary_for_ally(ally_id, admin_id)

    if info["has_subscription"]:
        days = info["days_left"]
        days_txt = "{} dias".format(days) if days is not None else "activa"
        text = (
            "MI SUSCRIPCION\n\n"
            "Estado: ACTIVA\n"
            "Tiempo restante: {}\n"
            "Precio: ${:,}/mes\n\n"
            "Con suscripcion activa no se te cobran fees por pedido entregado.\n\n"
            "Puedes renovar antes de que expire para no perder continuidad.".format(
                days_txt, info["price"] or 0
            )
        )
    else:
        if info["price"]:
            text = (
                "MI SUSCRIPCION\n\n"
                "Estado: SIN SUSCRIPCION ACTIVA\n"
                "Precio configurado: ${:,}/mes\n"
                "Tu saldo actual: ${:,}\n\n"
                "Sin suscripcion se te cobra ${} por cada pedido entregado.\n\n"
                "Con suscripcion: sin cobros por pedido durante 30 dias.".format(
                    info["price"], info["balance"], "fee normal"
                )
            )
        else:
            query.edit_message_text(
                "MI SUSCRIPCION\n\n"
                "Tu administrador aun no ha configurado el precio de suscripcion. "
                "Contactalo para solicitarlo."
            )
            return ConversationHandler.END

    buttons = []
    if info["can_renew"]:
        buttons.append([InlineKeyboardButton(
            "Renovar por ${:,}".format(info["price"]), callback_data="ally_subs_renovar"
        )])
    else:
        if info["price"] and not info["has_subscription"]:
            buttons.append([InlineKeyboardButton(
                "Saldo insuficiente (necesitas ${:,})".format(info["price"]), callback_data="ally_subs_noop"
            )])

    markup = InlineKeyboardMarkup(buttons) if buttons else None
    query.edit_message_text(text, reply_markup=markup)
    return ALLY_SUBS_CONFIRMAR


def ally_subs_renovar_callback(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "ally_subs_noop":
        query.edit_message_text("Recarga tu saldo para poder renovar la suscripcion.")
        return ConversationHandler.END

    ally_id = context.user_data.get("subs_ally_id")
    admin_id = context.user_data.get("subs_admin_id")
    if not ally_id or not admin_id:
        query.edit_message_text("Error: sesion expirada. Intenta de nuevo.")
        return ConversationHandler.END

    ok, msg = pay_ally_subscription(ally_id, admin_id)
    query.edit_message_text(msg)
    return ConversationHandler.END


ally_suscripcion_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(ally_suscripcion_start, pattern=r"^ally_mi_suscripcion$")],
    states={
        ALLY_SUBS_CONFIRMAR: [
            CallbackQueryHandler(ally_subs_renovar_callback, pattern=r"^ally_subs_(renovar|noop)$")
        ]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(CANCELAR_VOLVER_MENU_FILTER, cancel_por_texto),
    ],
    allow_reentry=True,
    name="ally_suscripcion_conv",
    persistent=True,
)
