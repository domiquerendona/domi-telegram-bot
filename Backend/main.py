import os
import hashlib
import os
import time
import traceback
from dotenv import load_dotenv

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.error import BadRequest
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)

# Importa la clase principal de FastAPI
from fastapi import FastAPI

# Importa el router administrativo
# Router de endpoints administrativos
from web.api.admin import router as admin_router
# Router de endpoints de usuarios
from web.api.users import router as users_router
# Router de endpoints del dashboard
from web.api.dashboard import router as dashboard_router




# Se crea la instancia principal de la aplicación FastAPI
# Esta es la app que se ejecuta con Uvicorn
app = FastAPI()


# Se registran las rutas administrativas dentro de la aplicación
# Esto habilita endpoints como:
# POST /admin/users/{user_id}/approve

# Registra las rutas de administración
app.include_router(admin_router)
# Registra las rutas de usuarios
app.include_router(users_router)
# Registra las rutas del dashboard
app.include_router(dashboard_router)
from fastapi.responses import HTMLResponse

# Importa el middleware que permite manejar CORS en FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Lista de orígenes permitidos (frontend autorizado)
# En este caso, Angular corre en el puerto 4200 en desarrollo
origins = [
    "http://localhost:4200",
]

# Se agrega el middleware CORS a la aplicación
app.add_middleware(
    CORSMiddleware,

    # Orígenes que pueden hacer peticiones al backend
    allow_origins=origins,

    # Permite enviar cookies o credenciales (importante si usas JWT en cookies)
    allow_credentials=True,

    # Permite todos los métodos HTTP (GET, POST, PUT, DELETE, etc.)
    allow_methods=["*"],

    # Permite todos los headers en las solicitudes
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Domi App</title>
        </head>
        <body>
            <h1>Panel Web Domi 🚀</h1>
            <p>Backend funcionando correctamente.</p>
        </body>
    </html>
    """

from services import (
    register_platform_income,
    admin_puede_operar,
    calcular_precio_distancia,
    get_pricing_config,
    get_buy_pricing_config,
    calc_buy_products_surcharge,
    quote_order_by_addresses,
    quote_order_by_coords,
    extract_lat_lng_from_text,
    expand_short_url,
    can_call_google_today,
    extract_place_id_from_url,
    google_place_details,
    approve_recharge_request,
    reject_recharge_request,
    check_service_fee_available,
    resolve_location,
    resolve_location_next,
    get_smart_distance,
    _get_important_alert_config,
    es_admin_plataforma,
    _get_reference_reviewer,
    _get_missing_role_commands,
    get_user_by_id,
    get_available_admin_teams,
    # Alertas de oferta
    get_offer_alerts_config,
    save_offer_voice,
    set_offer_reminders_enabled,
    set_offer_reminder_seconds,
    set_offer_voice_enabled,
    clear_offer_voice,
    save_pricing_setting,
    # Candidatos de referencias
    get_pending_reference_candidates,
    get_reference_candidate,
    review_reference_candidate,
    set_reference_candidate_coords,
    # Funciones de acceso a datos (re-exportadas desde db vía services)
    ensure_user,
    get_user_db_id_from_update,
    get_user_by_telegram_id,
    get_admin_rejection_type_by_id,
    get_ally_rejection_type_by_id,
    get_courier_rejection_type_by_id,
    list_approved_admin_teams,
    list_courier_links_by_admin,
    list_ally_links_by_admin,
    get_platform_admin_id,
    upsert_admin_ally_link,
    create_admin_courier_link,
    deactivate_other_approved_admin_courier_links,
    deactivate_other_approved_admin_ally_links,
    get_local_admins_count,
    create_ally,
    get_ally_by_user_id,
    get_pending_allies,
    get_ally_by_id,
    update_ally_status,
    update_ally_status_by_id,
    get_all_allies,
    update_ally,
    delete_ally,
    create_admin,
    get_admin_by_user_id,
    get_admin_by_telegram_id,
    user_has_platform_admin,
    get_all_admins,
    get_pending_admins,
    get_admin_by_id,
    get_admin_status_by_id,
    update_admin_status_by_id,
    count_admin_couriers,
    count_admin_couriers_with_min_balance,
    get_admin_by_team_code,
    update_admin_courier_status,
    upsert_admin_courier_link,
    create_ally_location,
    get_ally_locations,
    get_ally_location_by_id,
    get_default_ally_location,
    set_default_ally_location,
    update_ally_location,
    update_ally_location_coords,
    delete_ally_location,
    increment_pickup_usage,
    set_frequent_pickup,
    create_admin_location,
    get_admin_locations,
    get_admin_location_by_id,
    get_default_admin_location,
    increment_admin_location_usage,
    create_courier,
    get_courier_by_user_id,
    get_courier_by_id,
    get_courier_by_telegram_id,
    set_courier_available_cash,
    can_courier_activate,
    deactivate_courier,
    update_courier_live_location,
    set_courier_availability,
    expire_stale_live_locations,
    get_pending_couriers,
    get_pending_couriers_by_admin,
    get_pending_allies_by_admin,
    get_allies_by_admin_and_status,
    get_couriers_by_admin_and_status,
    update_courier_status,
    update_courier_status_by_id,
    get_all_couriers,
    update_courier,
    delete_courier,
    get_admin_link_for_courier,
    get_admin_link_for_ally,
    get_courier_link_balance,
    create_order,
    set_order_status,
    assign_order_to_courier,
    get_order_by_id,
    get_orders_by_ally,
    get_orders_by_courier,
    get_active_order_for_courier,
    get_active_route_for_courier,
    get_pending_route_stops,
    ally_get_order_for_incentive,
    ally_increment_order_incentive,
    admin_get_order_for_incentive,
    admin_increment_order_incentive,
    courier_get_earnings_history,
    courier_get_earnings_by_date_key,
    get_totales_registros,
    add_courier_rating,
    get_active_terms_version,
    has_accepted_terms,
    save_terms_acceptance,
    save_terms_session_ack,
    create_ally_customer,
    update_ally_customer,
    archive_ally_customer,
    restore_ally_customer,
    get_ally_customer_by_id,
    get_ally_customer_by_phone,
    list_ally_customers,
    search_ally_customers,
    create_customer_address,
    update_customer_address,
    archive_customer_address,
    restore_customer_address,
    get_customer_address_by_id,
    list_customer_addresses,
    get_last_order_by_ally,
    get_link_cache,
    upsert_link_cache,
    get_approved_admin_link_for_courier,
    get_approved_admin_link_for_ally,
    get_all_approved_links_for_courier,
    get_all_approved_links_for_ally,
    get_admin_balance,
    get_platform_admin,
    ensure_platform_temp_coverage_for_ally,
    create_recharge_request,
    list_pending_recharges_for_admin,
    list_all_pending_recharges,
    get_admins_with_pending_count,
    list_recharge_ledger,
    get_recharge_request,
    get_admin_payment_info,
    update_admin_payment_info,
    update_recharge_proof,
    create_payment_method,
    get_payment_method_by_id,
    list_payment_methods,
    toggle_payment_method,
    deactivate_payment_method,
    get_admin_reference_validator_permission,
    set_admin_reference_validator_permission,
    # Rutas multi-parada
    calcular_precio_ruta,
    calcular_distancia_ruta,
    calcular_distancia_ruta_smart,
    create_route,
    create_route_destination,
    get_all_online_couriers,
    get_active_orders_without_courier,
    get_online_couriers_sorted_by_distance,
    block_courier_for_ally,
    unblock_courier_for_ally,
    get_blocked_courier_ids_for_ally,
)
from order_delivery import publish_order_to_couriers, order_courier_callback, ally_active_orders, admin_orders_panel, admin_orders_callback, publish_route_to_couriers, handle_route_callback, handle_rating_callback, check_courier_arrival_at_pickup, repost_order_to_couriers
from db import (
    init_db,
    force_platform_admin,
    ensure_pricing_defaults,
)
from profile_changes import (
    profile_change_conv,
    admin_change_requests_callback,
    admin_change_requests_list,
    chgreq_reject_reason_handler,
)

# ============================================================
# SEPARACIÓN DEV/PROD - Evitar conflicto getUpdates
# ============================================================

# Cargar .env SIEMPRE primero
load_dotenv()
ENV = os.getenv("ENV", "PROD").upper()

if ENV == "LOCAL":
    print(f"[ENV] Ambiente: {ENV} - .env cargado")
else:
    print(f"[ENV] Ambiente: {ENV} - usando variables de entorno del sistema (Railway/PROD)")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

def _important_alert_job(context):
    data = context.job.context or {}
    alert_key = data.get("alert_key")
    if not alert_key:
        return
    if not context.bot_data.get("important_alert_open:{}".format(alert_key), False):
        return
    chat_id = data.get("chat_id")
    text = data.get("text")
    if not chat_id or not text:
        return
    reply_markup = data.get("reply_markup")
    try:
        context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    except Exception as e:
        print("[WARN] No se pudo enviar recordatorio importante {}: {}".format(alert_key, e))


def _schedule_important_alerts(context, alert_key, chat_id, reminder_text, reply_markup=None):
    config = _get_important_alert_config()
    if not config["enabled"]:
        return
    context.bot_data["important_alert_open:{}".format(alert_key)] = True
    for idx, sec in enumerate(config["seconds"], start=1):
        context.job_queue.run_once(
            _important_alert_job,
            when=sec,
            context={
                "alert_key": alert_key,
                "chat_id": chat_id,
                "text": reminder_text,
                "reply_markup": reply_markup,
            },
            name="important_alert_{}_{}".format(alert_key, idx),
        )


def _resolve_important_alert(context, alert_key):
    context.bot_data["important_alert_open:{}".format(alert_key)] = False
    config = _get_important_alert_config()
    for idx in range(1, len(config["seconds"]) + 1):
        jobs = context.job_queue.get_jobs_by_name("important_alert_{}_{}".format(alert_key, idx))
        for job in jobs:
            try:
                job.schedule_removal()
            except Exception:
                pass




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


# =========================
# Estados del registro de aliados (flujo unificado)
# =========================
(
    ALLY_NAME,
    ALLY_OWNER,
    ALLY_DOCUMENT,
    ALLY_PHONE,
    ALLY_CITY,
    ALLY_BARRIO,
    ALLY_ADDRESS,
    ALLY_UBICACION,
    ALLY_CONFIRM,
    ALLY_TEAM,
) = range(10)


# =========================
# Estados para registro de repartidores (flujo unificado)
# =========================
(
    COURIER_FULLNAME,
    COURIER_IDNUMBER,
    COURIER_PHONE,
    COURIER_CITY,
    COURIER_BARRIO,
    COURIER_RESIDENCE_ADDRESS,
    COURIER_RESIDENCE_LOCATION,
    COURIER_PLATE,
    COURIER_BIKETYPE,
    COURIER_CEDULA_FRONT,
    COURIER_CEDULA_BACK,
    COURIER_SELFIE,
    COURIER_CONFIRM,
    COURIER_TEAM,
) = range(100, 114)


# =========================
# Estados para registro de administrador local (flujo unificado)
# =========================
(
    LOCAL_ADMIN_NAME,
    LOCAL_ADMIN_DOCUMENT,
    LOCAL_ADMIN_TEAMNAME,
    LOCAL_ADMIN_PHONE,
    LOCAL_ADMIN_CITY,
    LOCAL_ADMIN_BARRIO,
    LOCAL_ADMIN_RESIDENCE_ADDRESS,
    LOCAL_ADMIN_RESIDENCE_LOCATION,
    LOCAL_ADMIN_CEDULA_FRONT,
    LOCAL_ADMIN_CEDULA_BACK,
    LOCAL_ADMIN_SELFIE,
    LOCAL_ADMIN_CONFIRM,
) = range(300, 312)


FLOW_STATE_ORDER = {
    "ally": [
        ALLY_NAME, ALLY_OWNER, ALLY_DOCUMENT, ALLY_PHONE,
        ALLY_CITY, ALLY_BARRIO, ALLY_ADDRESS, ALLY_UBICACION, ALLY_CONFIRM,
    ],
    "courier": [
        COURIER_FULLNAME, COURIER_IDNUMBER, COURIER_PHONE,
        COURIER_CITY, COURIER_BARRIO, COURIER_RESIDENCE_ADDRESS,
        COURIER_RESIDENCE_LOCATION, COURIER_PLATE, COURIER_BIKETYPE,
        COURIER_CEDULA_FRONT, COURIER_CEDULA_BACK, COURIER_SELFIE,
        COURIER_CONFIRM,
    ],
    "admin": [
        LOCAL_ADMIN_NAME, LOCAL_ADMIN_DOCUMENT, LOCAL_ADMIN_TEAMNAME,
        LOCAL_ADMIN_PHONE, LOCAL_ADMIN_CITY, LOCAL_ADMIN_BARRIO,
        LOCAL_ADMIN_RESIDENCE_ADDRESS, LOCAL_ADMIN_RESIDENCE_LOCATION,
        LOCAL_ADMIN_CEDULA_FRONT, LOCAL_ADMIN_CEDULA_BACK, LOCAL_ADMIN_SELFIE,
        LOCAL_ADMIN_CONFIRM,
    ],
}

FLOW_STATE_KEYS = {
    "ally": {
        ALLY_NAME: ["business_name"],
        ALLY_OWNER: ["owner_name"],
        ALLY_DOCUMENT: ["ally_document"],
        ALLY_PHONE: ["ally_phone"],
        ALLY_CITY: ["city"],
        ALLY_BARRIO: ["barrio"],
        ALLY_ADDRESS: ["address"],
        ALLY_UBICACION: ["ally_lat", "ally_lng"],
        ALLY_CONFIRM: [],
    },
    "courier": {
        COURIER_FULLNAME: ["full_name"],
        COURIER_IDNUMBER: ["id_number"],
        COURIER_PHONE: ["phone"],
        COURIER_CITY: ["city"],
        COURIER_BARRIO: ["barrio"],
        COURIER_RESIDENCE_ADDRESS: ["residence_address"],
        COURIER_RESIDENCE_LOCATION: ["residence_lat", "residence_lng"],
        COURIER_PLATE: ["plate"],
        COURIER_BIKETYPE: ["bike_type"],
        COURIER_CEDULA_FRONT: ["cedula_front_file_id"],
        COURIER_CEDULA_BACK: ["cedula_back_file_id"],
        COURIER_SELFIE: ["selfie_file_id"],
        COURIER_CONFIRM: [],
    },
    "admin": {
        LOCAL_ADMIN_NAME: ["admin_name"],
        LOCAL_ADMIN_DOCUMENT: ["admin_document"],
        LOCAL_ADMIN_TEAMNAME: ["admin_team_name"],
        LOCAL_ADMIN_PHONE: ["phone"],
        LOCAL_ADMIN_CITY: ["admin_city"],
        LOCAL_ADMIN_BARRIO: ["admin_barrio"],
        LOCAL_ADMIN_RESIDENCE_ADDRESS: ["admin_residence_address"],
        LOCAL_ADMIN_RESIDENCE_LOCATION: ["admin_residence_lat", "admin_residence_lng"],
        LOCAL_ADMIN_CEDULA_FRONT: ["admin_cedula_front_file_id"],
        LOCAL_ADMIN_CEDULA_BACK: ["admin_cedula_back_file_id"],
        LOCAL_ADMIN_SELFIE: ["admin_selfie_file_id"],
        LOCAL_ADMIN_CONFIRM: [],
    },
}

FLOW_PREVIOUS_STATE = {}
for _flow, _states in FLOW_STATE_ORDER.items():
    FLOW_PREVIOUS_STATE[_flow] = {}
    for _idx, _state in enumerate(_states):
        FLOW_PREVIOUS_STATE[_flow][_state] = _states[_idx - 1] if _idx > 0 else None


def _set_flow_step(context, flow, step):
    context.user_data["_back_flow"] = flow
    context.user_data["_back_step"] = step


_OPTIONS_HINT = (
    "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
)


def _handle_phone_input(update, context, storage_key, current_state, next_state, flow, next_prompt):
    """Helper para validar y almacenar teléfono en flujos de registro."""
    phone = (update.message.text or "").strip()
    digits = "".join([c for c in phone if c.isdigit()])
    if len(digits) < 7:
        update.message.reply_text(
            "Ese teléfono no parece válido. Escríbelo de nuevo, por favor." + _OPTIONS_HINT
        )
        return current_state
    context.user_data[storage_key] = phone
    update.message.reply_text(next_prompt + _OPTIONS_HINT)
    _set_flow_step(context, flow, next_state)
    return next_state


def _handle_text_field_input(
    update,
    context,
    error_msg,
    storage_key,
    current_state,
    next_state,
    flow,
    next_prompt,
    options_hint=_OPTIONS_HINT,
    set_back_step=True,
):
    """Helper para validar y almacenar campos de texto simple."""
    texto = (update.message.text or "").strip()
    if not texto:
        update.message.reply_text(error_msg + (options_hint or ""))
        return current_state
    context.user_data[storage_key] = texto
    if next_prompt is not None:
        update.message.reply_text(next_prompt + (options_hint or ""))
    if set_back_step:
        _set_flow_step(context, flow, next_state)
    return next_state


def _clear_flow_data_from_state(context, flow, target_state):
    states = FLOW_STATE_ORDER.get(flow, [])
    if target_state not in states:
        return
    start_idx = states.index(target_state)
    for state in states[start_idx:]:
        for key in FLOW_STATE_KEYS.get(flow, {}).get(state, []):
            context.user_data.pop(key, None)


def _send_back_prompt(update, flow, state):
    prompts = {
        "ally": {
            ALLY_NAME: "Registro de aliado\n\nEscribe el nombre del negocio:",
            ALLY_OWNER: "Escribe el nombre del dueño o administrador:",
            ALLY_DOCUMENT: "Escribe el número de cédula del dueño o representante:",
            ALLY_PHONE: "Escribe el teléfono de contacto del negocio:",
            ALLY_CITY: "Escribe la ciudad del negocio:",
            ALLY_BARRIO: "Escribe el barrio del negocio:",
            ALLY_ADDRESS: "Escribe la dirección del negocio:",
            ALLY_UBICACION: (
                "Envía la ubicación GPS (pin de Telegram) o pega un link de Google Maps."
            ),
            ALLY_CONFIRM: "Escribe SI para confirmar tu registro.",
        },
        "courier": {
            COURIER_FULLNAME: "Registro de repartidor\n\nEscribe tu nombre completo:",
            COURIER_IDNUMBER: "Escribe tu número de identificación:",
            COURIER_PHONE: "Escribe tu número de celular:",
            COURIER_CITY: "Escribe la ciudad donde trabajas:",
            COURIER_BARRIO: "Escribe el barrio o sector principal donde trabajas:",
            COURIER_RESIDENCE_ADDRESS: "Escribe tu dirección de residencia:",
            COURIER_RESIDENCE_LOCATION: "Envía tu ubicación GPS (pin de Telegram) o pega un link de Google Maps.",
            COURIER_PLATE: "Escribe la placa de tu moto (o 'ninguna'):",
            COURIER_BIKETYPE: "Escribe el tipo de moto:",
            COURIER_CEDULA_FRONT: "Envía una foto del frente de tu cédula:",
            COURIER_CEDULA_BACK: "Envía una foto del reverso de tu cédula:",
            COURIER_SELFIE: "Envía una foto de tu cara (selfie):",
            COURIER_CONFIRM: "Escribe SI para confirmar tu registro.",
        },
        "admin": {
            LOCAL_ADMIN_NAME: "Registro de Administrador Local.\nEscribe tu nombre completo:",
            LOCAL_ADMIN_DOCUMENT: "Escribe tu número de documento:",
            LOCAL_ADMIN_TEAMNAME: "Escribe el nombre de tu administración (equipo):",
            LOCAL_ADMIN_PHONE: "Escribe tu número de teléfono:",
            LOCAL_ADMIN_CITY: "¿En qué ciudad vas a operar como Administrador Local?",
            LOCAL_ADMIN_BARRIO: "Escribe tu barrio o zona base de operación:",
            LOCAL_ADMIN_RESIDENCE_ADDRESS: "Escribe tu dirección de residencia:",
            LOCAL_ADMIN_RESIDENCE_LOCATION: "Envía tu ubicación GPS (pin de Telegram) o pega un link de Google Maps.",
            LOCAL_ADMIN_CEDULA_FRONT: "Envía una foto del frente de tu cédula:",
            LOCAL_ADMIN_CEDULA_BACK: "Envía una foto del reverso de tu cédula:",
            LOCAL_ADMIN_SELFIE: "Envía una foto de tu cara (selfie):",
            LOCAL_ADMIN_CONFIRM: "Escribe ACEPTAR para finalizar o volver para corregir.",
        },
    }
    msg = prompts.get(flow, {}).get(state)
    if msg:
        update.message.reply_text(msg)
    else:
        update.message.reply_text("Escribe el dato solicitado o usa /cancel para salir.")


def volver_paso_anterior(update, context):
    flow = context.user_data.get("_back_flow")
    current_state = context.user_data.get("_back_step")
    if not flow or current_state is None:
        update.message.reply_text("No hay un paso anterior disponible en este flujo.")
        return ConversationHandler.END

    previous_state = FLOW_PREVIOUS_STATE.get(flow, {}).get(current_state)
    if previous_state is None:
        update.message.reply_text("Ya estás en el primer paso. Escribe el dato o usa /cancel.")
        return current_state

    # En TEAM ya existe registro persistido; permitir volver sería riesgoso.
    if flow == "courier" and current_state == COURIER_TEAM:
        update.message.reply_text(
            "Aquí no se permite volver atrás porque el registro ya se guardó.\n"
            "Selecciona un equipo para terminar."
        )
        return current_state

    if flow == "ally" and current_state == ALLY_TEAM:
        update.message.reply_text(
            "Aquí no se permite volver atrás porque el registro ya se guardó.\n"
            "Selecciona un equipo para terminar."
        )
        return current_state

    _clear_flow_data_from_state(context, flow, previous_state)
    _set_flow_step(context, flow, previous_state)
    _send_back_prompt(update, flow, previous_state)
    return previous_state


# =========================
# Estados para crear un pedido (modificado para cliente recurrente)
# =========================
(
    PEDIDO_SELECTOR_CLIENTE,      # Selector cliente recurrente/nuevo
    PEDIDO_BUSCAR_CLIENTE,        # Buscar cliente por nombre/telefono
    PEDIDO_SELECCIONAR_DIRECCION, # Seleccionar direccion del cliente
    PEDIDO_INSTRUCCIONES_EXTRA,   # Preguntar si agregar instrucciones adicionales
    PEDIDO_TIPO_SERVICIO,
    PEDIDO_NOMBRE,
    PEDIDO_TELEFONO,
    PEDIDO_UBICACION,             # Capturar ubicacion (link/coords) opcional
    PEDIDO_DIRECCION,
    PEDIDO_PICKUP_SELECTOR,       # Selector de punto de recogida
    PEDIDO_PICKUP_LISTA,          # Lista de pickups guardados
    PEDIDO_PICKUP_NUEVA_UBICACION,# Capturar coords de nueva direccion
    PEDIDO_PICKUP_NUEVA_DETALLES, # Capturar detalles de nueva direccion
    PEDIDO_PICKUP_GUARDAR,        # Preguntar si guardar nueva direccion
    PEDIDO_REQUIERE_BASE,         # Preguntar si requiere base
    PEDIDO_VALOR_BASE,            # Capturar valor de base
    PEDIDO_CONFIRMACION,
    PEDIDO_GUARDAR_CLIENTE,       # Preguntar si guardar cliente nuevo
    PEDIDO_COMPRAS_CANTIDAD,      # Capturar lista de productos con cantidades
) = range(14, 33)

PEDIDO_INCENTIVO_MONTO = 900  # Capturar incentivo adicional (otro monto)
PEDIDO_PICKUP_NUEVA_CIUDAD = 880
PEDIDO_PICKUP_NUEVA_BARRIO = 881


# =========================
# Estados para crear una ruta multi-parada
# =========================
(
    RUTA_PICKUP_SELECTOR,        # 33 - Selector de punto de recogida
    RUTA_PICKUP_LISTA,           # 34 - Lista de pickups guardados
    RUTA_PICKUP_NUEVA_UBICACION, # 35 - Capturar coords nueva direccion de recogida
    RUTA_PICKUP_NUEVA_DETALLES,  # 36 - Detalles de nueva direccion
    RUTA_PICKUP_GUARDAR,         # 37 - Preguntar si guardar nueva direccion
    RUTA_PARADA_SELECTOR,        # 38 - Tipo de cliente (nuevo/recurrente) para parada actual
    RUTA_PARADA_SEL_DIRECCION,   # 39 - Seleccionar direccion de cliente recurrente
    RUTA_PARADA_NOMBRE,          # 40 - Nombre del cliente
    RUTA_PARADA_TELEFONO,        # 41 - Telefono del cliente
    RUTA_PARADA_UBICACION,       # 42 - GPS opcional de la parada
    RUTA_PARADA_DIRECCION,       # 43 - Direccion de entrega
    RUTA_MAS_PARADAS,            # 44 - Agregar mas paradas o finalizar
    RUTA_DISTANCIA_KM,           # 45 - Km totales (si no hay GPS suficiente)
    RUTA_CONFIRMACION,           # 46 - Confirmacion y creacion de la ruta
    RUTA_GUARDAR_CLIENTES,       # 47 - Guardar clientes nuevos de las paradas
) = range(33, 48)

RUTA_PICKUP_NUEVA_CIUDAD = 48
RUTA_PICKUP_NUEVA_BARRIO = 49
RUTA_PARADA_CIUDAD = 50
RUTA_PARADA_BARRIO = 51


# =========================
# Estados para /clientes (agenda de clientes recurrentes)
# =========================
(
    CLIENTES_MENU,
    CLIENTES_NUEVO_NOMBRE,
    CLIENTES_NUEVO_TELEFONO,
    CLIENTES_NUEVO_NOTAS,
    CLIENTES_NUEVO_DIRECCION_LABEL,
    CLIENTES_NUEVO_DIRECCION_TEXT,
    CLIENTES_BUSCAR,
    CLIENTES_VER_CLIENTE,
    CLIENTES_EDITAR_NOMBRE,
    CLIENTES_EDITAR_TELEFONO,
    CLIENTES_EDITAR_NOTAS,
    CLIENTES_DIR_NUEVA_LABEL,
    CLIENTES_DIR_NUEVA_TEXT,
    CLIENTES_DIR_EDITAR_LABEL,
    CLIENTES_DIR_EDITAR_TEXT,
    CLIENTES_DIR_EDITAR_NOTA,
) = range(400, 416)

CLIENTES_DIR_CIUDAD = 416
CLIENTES_DIR_BARRIO = 417
CLIENTES_DIR_CORREGIR_COORDS = 418
CLIENTES_DIR_CORREGIR_GEO = 419


# =========================
# Estados para /direcciones (panel Mis direcciones del aliado)
# =========================
(
    DIRECCIONES_MENU,
    DIRECCIONES_PICKUPS,
    DIRECCIONES_PICKUP_NUEVA_UBICACION,
    DIRECCIONES_PICKUP_NUEVA_DETALLES,
    DIRECCIONES_PICKUP_GUARDAR,
) = range(500, 505)

DIRECCIONES_PICKUP_NUEVA_CIUDAD = 505
DIRECCIONES_PICKUP_NUEVA_BARRIO = 506

# =========================
# Estados para cotizador interno
# =========================
COTIZAR_DISTANCIA = 901
COTIZAR_MODO = 903
COTIZAR_RECOGIDA = 904
COTIZAR_ENTREGA = 905
COTIZAR_RECOGIDA_SELECTOR = 906
COTIZAR_RESULTADO = 907


# =========================
# Estados para configuración de tarifas (Admin Plataforma)
# =========================
TARIFAS_VALOR = 902

# =========================
# Estados para sistema de recargas
# =========================
RECARGAR_MONTO = 950
RECARGAR_ADMIN = 951
RECARGAR_COMPROBANTE = 952
RECARGAR_ROL = 953

# =========================
# Estados para configurar datos de pago
# =========================
PAGO_TELEFONO = 960
PAGO_BANCO = 961
PAGO_TITULAR = 962
PAGO_INSTRUCCIONES = 963
PAGO_MENU = 964
ALERTAS_OFERTA_INPUT = 965

# Estados para el flujo de registro de ingreso externo (Admin Plataforma)
INGRESO_MONTO = 970
INGRESO_METODO = 971
INGRESO_NOTA = 972

OFFER_SUGGEST_INC_MONTO = 915  # Capturar monto libre en sugerencia T+5

# Estados para pedido especial del Admin Local
ADMIN_PEDIDO_PICKUP    = 908   # Seleccionar/crear dirección de recogida
ADMIN_PEDIDO_CUST_NAME = 909   # Nombre del cliente
ADMIN_PEDIDO_CUST_PHONE= 910   # Teléfono del cliente
ADMIN_PEDIDO_CUST_ADDR = 911   # Dirección de entrega (texto/GPS/geocoding)
ADMIN_PEDIDO_TARIFA    = 912   # Tarifa manualmente ingresada
ADMIN_PEDIDO_INSTRUC   = 913   # Instrucciones adicionales
ADMIN_PEDIDO_INC_MONTO = 916   # Incentivo adicional (monto libre pre-publicación)

# Estados para el panel de gestión de ubicaciones del aliado
ALLY_LOCS_MENU       = 920   # Panel principal (lista + operaciones vía callbacks)
ALLY_LOCS_ADD_COORDS = 921   # Agregar: esperando GPS / link / coords
ALLY_LOCS_ADD_LABEL  = 922   # Agregar: esperando etiqueta / nombre
ALLY_LOCS_ADD_CITY   = 923   # Agregar: esperando ciudad
ALLY_LOCS_ADD_BARRIO = 924   # Agregar: esperando barrio/sector

def start(update, context):
    """Comando /start y /menu: bienvenida con estado del usuario."""
    user_tg = update.effective_user

    # Crear/asegurar user en users y tomar users.id (interno)
    user_row = ensure_user(user_tg.id, user_tg.username)
    user_db_id = user_row["id"]

    # Perfiles
    ally = get_ally_by_user_id(user_db_id)
    courier = get_courier_by_user_id(user_db_id)

    # Admin local por users.id (interno)
    admin_local = None
    try:
        admin_local = get_admin_by_user_id(user_db_id)
    except Exception as e:
        print("ERROR get_admin_by_user_id en /start:", e)
        admin_local = None

    es_admin_plataforma_flag = es_admin_plataforma(user_tg.id)

    estado_lineas = []
    siguientes_pasos = []

    # Admin Plataforma
    if es_admin_plataforma_flag:
        estado_lineas.append("• Administrador de Plataforma: ACTIVO.")
        siguientes_pasos.append("• Usa /admin para abrir el Panel de Plataforma.")

    # Admin Local
    if admin_local:
        admin_status = admin_local.get("status", "PENDING") if isinstance(admin_local, dict) else admin_local["status"]
        admin_status = admin_status or "PENDING"
        team_name = (admin_local.get("team_name") if isinstance(admin_local, dict) else admin_local["team_name"]) or "-"
        team_code = (admin_local.get("team_code") if isinstance(admin_local, dict) else admin_local["team_code"]) or "-"

        estado_lineas.append(f"• Administrador Local: equipo {team_name} (estado: {admin_status}).")

        # Administrador de Plataforma: no mostrar requisitos
        if team_code == "PLATFORM":
            if admin_status == "APPROVED":
                siguientes_pasos.append("• Como Administrador de Plataforma, tu operación está habilitada.")
                siguientes_pasos.append("• Usa /mi_admin para acceder a tu panel.")
            elif admin_status == "PENDING":
                siguientes_pasos.append("• Tu registro de administrador está pendiente de aprobación.")
            elif admin_status == "INACTIVE":
                siguientes_pasos.append("• Tu cuenta de administrador está INACTIVA. Contacta al Administrador de Plataforma.")
            elif admin_status == "REJECTED":
                siguientes_pasos.append("• Tu registro de administrador fue RECHAZADO. Contacta al Administrador de Plataforma.")
        else:
            # Administrador Local normal: mostrar requisitos
            if admin_status == "PENDING":
                siguientes_pasos.append("• Tu registro de administrador está pendiente de aprobación.")
            elif admin_status == "APPROVED":
                siguientes_pasos.append(
                    "• Tu administrador fue APROBADO, pero no podrás operar hasta cumplir requisitos (10 repartidores con saldo mínimo)."
                )
                siguientes_pasos.append("• Usa /mi_admin para ver requisitos y tu estado operativo.")
            elif admin_status == "INACTIVE":
                siguientes_pasos.append("• Tu cuenta de administrador está INACTIVA. Contacta al Administrador de Plataforma.")
            elif admin_status == "REJECTED":
                siguientes_pasos.append("• Tu registro de administrador fue RECHAZADO. Contacta al Administrador de Plataforma.")

    # Aliado
    if ally:
        estado_lineas.append(f"• Aliado: {ally['business_name']} (estado: {ally['status']}).")
        if ally["status"] == "APPROVED":
            siguientes_pasos.append("• Puedes crear pedidos con /nuevo_pedido.")
        else:
            siguientes_pasos.append("• Tu negocio aún no está aprobado. Cuando esté APPROVED podrás usar /nuevo_pedido.")

    # Repartidor
    if courier:
        codigo = courier["code"] if courier["code"] else "sin código"
        estado_lineas.append(f"• Repartidor código interno: {codigo} (estado: {courier['status']}).")
        if courier["status"] == "APPROVED":
            siguientes_pasos.append("• Pronto podrás activarte y recibir ofertas (ONLINE) desde tu panel de repartidor.")
        else:
            siguientes_pasos.append("• Tu registro de repartidor aún está pendiente de aprobación.")

    # Si no tiene ningún perfil
    if not estado_lineas:
        estado_text = "Aún no estás registrado como aliado, repartidor ni administrador."
        siguientes_pasos = [
            "• Si tienes un negocio: usa /soy_aliado",
            "• Si eres repartidor: usa /soy_repartidor",
            "• Si vas a liderar un equipo: usa /soy_administrador",
        ]
    else:
        estado_text = "\n".join(estado_lineas)

    siguientes_text = "\n".join(siguientes_pasos) if siguientes_pasos else "• Usa los comandos principales para continuar."

    # Construir menú agrupado por rol
    missing_cmds = _get_missing_role_commands(ally, courier, admin_local, es_admin_plataforma_flag)
    comandos = []

    comandos.append("General:")
    comandos.append("• /mi_perfil  - Ver tu perfil consolidado")

    if ally:
        comandos.append("")
        comandos.append("🍕 Aliado:")
        comandos.append("• Toca [Mi aliado] en el menu para ver todas las opciones:")
        comandos.append("  Nuevo pedido, Mis pedidos, Clientes, Agenda,")
        comandos.append("  Cotizar envio, Recargar, Mi saldo")
    else:
        comandos.append("")
        comandos.append("Aliado:")
        comandos.append("• /soy_aliado  - Registrarte como aliado")

    if courier:
        comandos.append("")
        comandos.append("🚴 Repartidor:")
        if courier["status"] == "APPROVED":
            comandos.append("• Toca [Mi repartidor] en el menu para ver todas las opciones:")
            comandos.append("  Activar/Pausar, Mis pedidos, Recargar, Mi saldo")
        else:
            comandos.append("• Tu perfil de repartidor no está APPROVED todavía.")
            comandos.append("  Cuando esté APPROVED verás la sección [Mi repartidor] en el menu.")
    else:
        comandos.append("")
        comandos.append("Repartidor:")
        comandos.append("• /soy_repartidor  - Registrarte como repartidor")

    comandos.append("")
    comandos.append("Administrador:")
    if es_admin_plataforma_flag:
        comandos.append("• /admin  - Panel de administración de plataforma")
        comandos.append("• /tarifas  - Configurar tarifas")
        comandos.append("• /recargas_pendientes  - Ver solicitudes de recarga")
        comandos.append("• /configurar_pagos  - Configurar datos de pago")
    elif admin_local:
        comandos.append("• /mi_admin  - Ver tu panel de administrador local")
        admin_status = admin_local["status"]
        if admin_status == "APPROVED":
            comandos.append("• /recargas_pendientes  - Ver solicitudes de recarga")
            comandos.append("• /configurar_pagos  - Configurar datos de pago")
    else:
        if "/soy_admin" in missing_cmds:
            comandos.append("• /soy_admin  - Registrarte como administrador")
        else:
            comandos.append("• No tienes opciones de administrador disponibles.")

    mensaje = (
        "🐢 Bienvenido a Domiquerendona 🐢\n\n"
        "Sistema para conectar negocios aliados con repartidores de confianza.\n\n"
        "Tu estado actual:\n"
        f"{estado_text}\n\n"
        "Siguiente paso recomendado:\n"
        f"{siguientes_text}\n\n"
        "Menú por secciones:\n"
        + "\n".join(comandos)
        + "\n"
    )

    # Mostrar ReplyKeyboard SOLO para usuarios nuevos (sin roles)
    if not estado_lineas and not context.user_data.get('keyboard_shown'):
        keyboard = [
            ['/soy_aliado', '/soy_repartidor'],
            ['/soy_admin', '/menu']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        context.user_data['keyboard_shown'] = True
        update.message.reply_text(mensaje, reply_markup=reply_markup)
    else:
        # Mostrar menú principal con botones de secciones
        reply_markup = get_main_menu_keyboard(missing_cmds, courier, ally)
        update.message.reply_text(mensaje, reply_markup=reply_markup)


def menu(update, context):
    """Alias de /start para mostrar el menú principal."""
    return start(update, context)


# ---------- MENÚS PERSISTENTES ----------

def _row_value(row, key, default=None):
    """Lee un campo desde dict/sqlite3.Row de forma segura."""
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        return default


def _get_courier_toggle_button_label(courier):
    """Retorna el texto del boton de estado para repartidor APPROVED."""
    if not courier or _row_value(courier, "status") != "APPROVED":
        return None
    courier_is_active = _row_value(courier, "is_active", 0)
    if courier_is_active:
        return "Desactivarme"
    return "Activar repartidor"


def _courier_main_button_label(courier):
    """Retorna el label del boton Mi repartidor con estado inline."""
    if not courier or _row_value(courier, "status") != "APPROVED":
        return None
    is_active = int(_row_value(courier, "is_active", 0) or 0)
    avail_status = _row_value(courier, "availability_status", "INACTIVE")
    live_active = int(_row_value(courier, "live_location_active", 0) or 0)
    if is_active and avail_status == "APPROVED" and live_active:
        return "Mi repartidor · ONLINE"
    return "Mi repartidor · OFFLINE"


def get_main_menu_keyboard(missing_cmds, courier=None, ally=None):
    """Retorna el teclado principal para usuarios fuera de flujos."""
    keyboard = []
    # Fila de roles: mostrar botones de seccion segun roles del usuario
    role_row = []
    if ally:
        role_row.append('Mi aliado')
    courier_btn = _courier_main_button_label(courier)
    if courier_btn:
        role_row.append(courier_btn)
    if role_row:
        keyboard.append(role_row)
    keyboard.append(['Mi perfil', 'Ayuda'])
    keyboard.append(['Menu'])
    if missing_cmds:
        if len(missing_cmds) == 1:
            register_rows = [missing_cmds]
        elif len(missing_cmds) == 2:
            register_rows = [missing_cmds]
        else:
            register_rows = [missing_cmds[:2], missing_cmds[2:]]
        keyboard = register_rows + keyboard
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_flow_menu_keyboard():
    """Retorna el teclado reducido para usuarios dentro de flujos."""
    keyboard = [
        ['Cancelar', 'Volver al menu']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_ally_menu_keyboard():
    """Retorna el teclado de seccion Aliado."""
    keyboard = [
        ['Nuevo pedido', 'Nueva ruta'],
        ['Mis pedidos', 'Agenda'],
        ['Cotizar envio', 'Recargar'],
        ['Mis repartidores', 'Mi saldo aliado'],
        ['Volver al menu'],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_repartidor_menu_keyboard(courier):
    """Retorna el teclado de seccion Repartidor."""
    courier_toggle = _get_courier_toggle_button_label(courier)
    keyboard = []
    if courier_toggle:
        keyboard.append([courier_toggle])
    keyboard.append(['Pedidos en curso', 'Actualizar'])
    keyboard.append(['Mis pedidos repartidor', 'Mis ganancias'])
    keyboard.append(['Recargar repartidor', 'Mi saldo repartidor'])
    keyboard.append(['Volver al menu'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def mi_aliado(update, context):
    """Muestra el submenu de gestion de aliado."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally:
        update.message.reply_text("No tienes perfil de aliado. Usa /soy_aliado para registrarte.")
        return
    status = ally["status"]
    business_name = ally["business_name"]
    msg = (
        "🍕 GESTION DE ALIADO\n\n"
        f"Negocio: {business_name}\n"
        f"Estado: {status}\n\n"
        "Selecciona una opcion:"
    )
    reply_markup = get_ally_menu_keyboard()
    update.message.reply_text(msg, reply_markup=reply_markup)


def _ally_couriers_build_panel(ally_id):
    """Construye texto e InlineKeyboardMarkup del panel de repartidores para un aliado.
    Muestra secciones ACTIVOS y BLOQUEADOS separadas.
    Retorna (text, markup) donde markup puede ser None si no hay botones."""
    admin_link = get_approved_admin_link_for_ally(ally_id)
    if not admin_link:
        return "No tienes un administrador aprobado asignado.", None

    admin_id = admin_link["admin_id"]
    couriers = list_courier_links_by_admin(admin_id)
    if not couriers:
        return "Tu equipo no tiene repartidores activos.", None

    blocked_ids = get_blocked_courier_ids_for_ally(ally_id)
    activos = []
    bloqueados = []
    for c in couriers:
        cid = c["courier_id"] if isinstance(c, dict) else c[1]
        name = (c["full_name"] if isinstance(c, dict) else c[2]) or "Sin nombre"
        if cid in blocked_ids:
            bloqueados.append((cid, name))
        else:
            activos.append((cid, name))

    lines = ["Repartidores de tu equipo:\n"]
    keyboard = []

    if activos:
        lines.append("ACTIVOS ({})".format(len(activos)))
        for cid, name in activos:
            lines.append("  {}".format(name))
            keyboard.append([InlineKeyboardButton(
                "Bloquear: {}".format(name),
                callback_data="ally_block_block_{}".format(cid),
            )])

    if bloqueados:
        if activos:
            lines.append("")
        lines.append("BLOQUEADOS ({})".format(len(bloqueados)))
        for cid, name in bloqueados:
            lines.append("  {} (bloqueado)".format(name))
            keyboard.append([InlineKeyboardButton(
                "Desbloquear: {}".format(name),
                callback_data="ally_block_unblock_{}".format(cid),
            )])

    if not activos and not bloqueados:
        return "Tu equipo no tiene repartidores.", None

    markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    return chr(10).join(lines), markup


def ally_couriers_panel(update, context):
    """Muestra repartidores del equipo con secciones ACTIVOS y BLOQUEADOS."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally or ally["status"] != "APPROVED":
        update.message.reply_text("Solo aliados aprobados pueden gestionar repartidores.")
        return

    text, markup = _ally_couriers_build_panel(ally["id"])
    update.message.reply_text(text, reply_markup=markup)


def ally_block_callback(update, context):
    """Maneja bloqueo/desbloqueo de repartidor por aliado y actualiza el panel."""
    query = update.callback_query
    query.answer()
    data = query.data

    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        query.edit_message_text("Usuario no encontrado.")
        return

    ally = get_ally_by_user_id(user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("Solo aliados aprobados pueden gestionar repartidores.")
        return

    ally_id = ally["id"]
    if data.startswith("ally_block_block_"):
        courier_id = int(data.split("_")[-1])
        block_courier_for_ally(ally_id, courier_id)
    elif data.startswith("ally_block_unblock_"):
        courier_id = int(data.split("_")[-1])
        unblock_courier_for_ally(ally_id, courier_id)
    else:
        return

    # Regenerar panel actualizado en el mismo mensaje
    text, markup = _ally_couriers_build_panel(ally_id)
    try:
        query.edit_message_text(text, reply_markup=markup)
    except Exception:
        pass


def mi_repartidor(update, context):
    """Muestra el submenu de gestion de repartidor."""
    user_db_id = get_user_db_id_from_update(update)
    courier = get_courier_by_user_id(user_db_id)
    if not courier:
        update.message.reply_text("No tienes perfil de repartidor. Usa /soy_repartidor para registrarte.")
        return
    status = _row_value(courier, "status", "PENDING")
    full_name = _row_value(courier, "full_name", "-")
    is_active = _row_value(courier, "is_active", 0)
    available_cash = int(_row_value(courier, "available_cash", 0) or 0)
    if is_active and status == "APPROVED":
        avail_status = _row_value(courier, "availability_status", "INACTIVE")
        live_active = int(_row_value(courier, "live_location_active", 0) or 0) == 1
        if avail_status == "APPROVED" and live_active:
            disp = "ONLINE"
        elif avail_status == "APPROVED":
            disp = "PAUSADO"
        else:
            disp = "OFFLINE"
    else:
        disp = "OFFLINE"
    disp_line = f"Disponibilidad: {disp}"
    if disp == "ONLINE":
        disp_line += f" (base ${available_cash:,})"
    msg = (
        "🚴 GESTION DE REPARTIDOR\n\n"
        f"Nombre: {full_name}\n"
        f"Estado: {status}\n"
        f"{disp_line}\n\n"
        "Selecciona una opcion:"
    )
    reply_markup = get_repartidor_menu_keyboard(courier)
    update.message.reply_text(msg, reply_markup=reply_markup)


def courier_orders_history(update, context):
    """Muestra pedidos del repartidor (activos e historial reciente)."""
    user_db_id = get_user_db_id_from_update(update)
    courier = get_courier_by_user_id(user_db_id)
    if not courier:
        update.message.reply_text("No tienes perfil de repartidor.")
        return

    orders = get_orders_by_courier(courier["id"], limit=20)
    if not orders:
        update.message.reply_text("No tienes pedidos registrados.")
        return

    status_labels = {
        "PENDING": "Pendiente",
        "PUBLISHED": "Buscando repartidor",
        "ACCEPTED": "Asignado",
        "PICKED_UP": "En camino",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }

    active_orders = [o for o in orders if _row_value(o, "status") not in ("DELIVERED", "CANCELLED")]
    history_orders = [o for o in orders if _row_value(o, "status") in ("DELIVERED", "CANCELLED")]

    if active_orders:
        update.message.reply_text("Tus pedidos activos:")
        for order in active_orders:
            status = status_labels.get(_row_value(order, "status"), _row_value(order, "status", "-"))
            msg = (
                "Pedido #{}\n"
                "Estado: {}\n"
                "Cliente: {}\n"
                "Dirección: {}"
            ).format(
                _row_value(order, "id", "-"),
                status,
                _row_value(order, "customer_name", "N/A") or "N/A",
                _row_value(order, "customer_address", "N/A") or "N/A",
            )
            update.message.reply_text(msg)
    else:
        update.message.reply_text("No tienes pedidos activos.")

    if history_orders:
        update.message.reply_text("Tu historial reciente:")
        for order in history_orders[:10]:
            status = status_labels.get(_row_value(order, "status"), _row_value(order, "status", "-"))
            event_at = "-"
            if _row_value(order, "status") == "DELIVERED":
                event_at = _row_value(order, "delivered_at", "-") or "-"
            elif _row_value(order, "status") == "CANCELLED":
                event_at = _row_value(order, "canceled_at", "-") or "-"

            msg = (
                "Pedido #{}\n"
                "Estado: {}\n"
                "Fecha: {}\n"
                "Cliente: {}\n"
                "Dirección: {}"
            ).format(
                _row_value(order, "id", "-"),
                status,
                event_at,
                _row_value(order, "customer_name", "N/A") or "N/A",
                _row_value(order, "customer_address", "N/A") or "N/A",
            )
            update.message.reply_text(msg)


def courier_pedidos_en_curso(update, context):
    """Muestra el estado de los trabajos activos asignados al repartidor."""
    user_db_id = get_user_db_id_from_update(update)
    courier = get_courier_by_user_id(user_db_id)
    if not courier:
        update.message.reply_text("No tienes perfil de repartidor.")
        return

    active_order = get_active_order_for_courier(courier["id"])
    active_route = get_active_route_for_courier(courier["id"])

    if not active_order and not active_route:
        update.message.reply_text("No tienes pedidos en curso.")
        return

    order_status_labels = {
        "ACCEPTED": "Asignado",
        "PICKED_UP": "En camino",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }
    route_status_labels = {
        "ACCEPTED": "En curso",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
    }

    update.message.reply_text("Pedidos en curso:")

    if active_order:
        order_id = _row_value(active_order, "id", "-")
        st = order_status_labels.get(
            _row_value(active_order, "status"),
            _row_value(active_order, "status", "-"),
        )
        order_status = _row_value(active_order, "status")
        pickup_address = _row_value(active_order, "pickup_address") or "No disponible"
        customer_city = _row_value(active_order, "customer_city") or ""
        customer_barrio = _row_value(active_order, "customer_barrio") or ""
        destino_area = "{}, {}".format(customer_barrio, customer_city).strip(", ") or "No disponible"
        total_fee = int((_row_value(active_order, "total_fee") or 0) or 0)

        msg = (
            "Pedido #{}\n"
            "Estado: {}\n"
            "Recoge en: {}\n"
            "Destino: {}\n"
            "Tarifa: ${:,}"
        ).format(order_id, st, pickup_address, destino_area, total_fee)

        kb = []
        if order_status == "ACCEPTED":
            kb.append([
                InlineKeyboardButton(
                    "Solicitar confirmacion de recogida",
                    callback_data="order_pickup_{}".format(order_id),
                ),
            ])
            kb.append([
                InlineKeyboardButton(
                    "Liberar pedido",
                    callback_data="order_release_{}".format(order_id),
                ),
            ])
        elif order_status == "PICKED_UP":
            kb.append([
                InlineKeyboardButton(
                    "Finalizar pedido",
                    callback_data="order_delivered_confirm_{}".format(order_id),
                ),
            ])
        update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb))

    if active_route:
        route_id = _row_value(active_route, "id", "-")
        st = route_status_labels.get(
            _row_value(active_route, "status"),
            _row_value(active_route, "status", "-"),
        )
        route_status = _row_value(active_route, "status")
        pickup_address = _row_value(active_route, "pickup_address") or "No disponible"
        total_fee = int((_row_value(active_route, "total_fee") or 0) or 0)

        pending_stops = get_pending_route_stops(int(route_id)) if route_id != "-" else []
        next_seq = None
        if pending_stops:
            try:
                next_seq = min(int(s["sequence"]) for s in pending_stops if s.get("sequence") is not None)
            except Exception:
                next_seq = None

        msg = (
            "Ruta #{}\n"
            "Estado: {}\n"
            "Recoge en: {}\n"
            "Pago: ${:,}"
        ).format(route_id, st, pickup_address, total_fee)

        kb = []
        if next_seq is not None:
            kb.append([
                InlineKeyboardButton(
                    "Entregar siguiente parada",
                    callback_data="ruta_entregar_{}_{}".format(route_id, next_seq),
                )
            ])
        if route_status == "ACCEPTED":
            kb.append([
                InlineKeyboardButton(
                    "Liberar ruta",
                    callback_data="ruta_liberar_{}".format(route_id),
                )
            ])
        update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb) if kb else None)

    update.message.reply_text("No puedes aceptar nuevos pedidos o rutas hasta finalizar el actual.")


def _get_chat_id(update):
    """Extrae chat_id de forma robusta desde update."""
    if getattr(update, "callback_query", None) and update.callback_query.message:
        return update.callback_query.message.chat_id
    if getattr(update, "message", None):
        return update.message.chat_id
    return None


def _get_user_roles(update):
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    courier = get_courier_by_user_id(user_db_id)
    admin_local = None
    try:
        admin_local = get_admin_by_user_id(user_db_id)
    except Exception as e:
        print("ERROR get_admin_by_user_id en menu:", e)
        admin_local = None
    return ally, courier, admin_local


def show_main_menu(update, context, text="Menu principal. Selecciona una opcion:"):
    """Muestra el menú principal completo."""
    ally, courier, admin_local = _get_user_roles(update)
    es_admin_plataforma_flag = es_admin_plataforma(update.effective_user.id)
    missing_cmds = _get_missing_role_commands(ally, courier, admin_local, es_admin_plataforma_flag)
    reply_markup = get_main_menu_keyboard(missing_cmds, courier, ally)
    chat_id = _get_chat_id(update)
    if chat_id:
        context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def show_flow_menu(update, context, text):
    """Muestra el menú reducido para flujos activos."""
    reply_markup = get_flow_menu_keyboard()
    chat_id = _get_chat_id(update)
    if chat_id and text:
        context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)


def cmd_id(update, context):
    """Muestra el user_id de Telegram del usuario."""
    user = update.effective_user
    update.message.reply_text(f"Tu user_id es: {user.id}")


def menu_button_handler(update, context):
    """Maneja los botones del menú principal y submenús (ReplyKeyboard)."""
    text = update.message.text.strip()

    # --- Botones del menú principal ---
    if text == "Mi aliado":
        return mi_aliado(update, context)
    elif text.startswith("Mi repartidor"):
        return mi_repartidor(update, context)
    elif text == "Mi perfil":
        return mi_perfil(update, context)
    elif text == "Ayuda":
        ally, courier, admin_local = _get_user_roles(update)
        missing_cmds = _get_missing_role_commands(ally, courier, admin_local)
        msg = (
            "AYUDA\n\n"
            "Secciones del menu:\n"
            "• Mi aliado - Gestion de tu negocio (pedidos, clientes, agenda, cotizar, recargar, saldo)\n"
            "• Mi repartidor - Gestion de repartidor (activar/pausar, pedidos, recargar, saldo)\n\n"
            "Comandos disponibles:\n"
            "/nuevo_pedido - Crear un nuevo pedido\n"
            "/clientes - Gestionar clientes\n"
            "/cotizar - Cotizar envio por distancia\n"
            "/recargar - Solicitar recarga\n"
            "/saldo - Ver tu saldo\n"
            "/mi_perfil - Ver tu perfil\n"
            "/cancel - Cancelar proceso actual\n"
            "/menu - Ver menu principal"
        )
        if missing_cmds:
            msg += "\n\nREGISTRO:\n"
            if "/soy_aliado" in missing_cmds:
                msg += "/soy_aliado - Registrar mi negocio\n"
            if "/soy_repartidor" in missing_cmds:
                msg += "/soy_repartidor - Registrarme como repartidor\n"
            if "/soy_admin" in missing_cmds:
                msg += "/soy_admin - Registrarme como administrador"
        update.message.reply_text(msg)
        return
    elif text == "Menu":
        return start(update, context)

    # --- Botones del submenú Aliado ---
    elif text == "Mis pedidos":
        return ally_active_orders(update, context)
    elif text == "Mis repartidores":
        return ally_couriers_panel(update, context)
    elif text == "Mi saldo aliado":
        return cmd_saldo(update, context)

    # --- Botones del submenú Repartidor ---
    elif text == "Activar repartidor":
        return courier_activate_from_message(update, context)
    elif text == "Desactivarme":
        return courier_deactivate_from_message(update, context)
    elif text == "Actualizar":
        return mi_repartidor(update, context)
    elif text == "Pedidos en curso":
        return courier_pedidos_en_curso(update, context)
    elif text == "Mis pedidos repartidor":
        return courier_orders_history(update, context)
    elif text == "Mis ganancias":
        return courier_earnings_start(update, context)
    elif text == "Mi saldo repartidor":
        return cmd_saldo(update, context)

    # --- Botón compartido ---
    elif text == "Volver al menu":
        return show_main_menu(update, context, "Menu principal. Selecciona una opcion:")


def saludo_menu_handler(update, context):
    """Muestra menu principal cuando el usuario saluda fuera de comandos."""
    show_main_menu(update, context, "Hola. Te muestro el menu principal:")


# ----- REGISTRO DE ALIADO (flujo unificado) -----

def soy_aliado(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    # Validación anti-duplicados
    existing = get_ally_by_user_id(user_db_id)
    if existing:
        status = existing["status"]
        ally_id = existing["id"]

        rejection_type = get_ally_rejection_type_by_id(ally_id)

        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de aliado en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de aliado aprobado (APPROVED). Si necesitas cambios, contacta al administrador."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status != "INACTIVE":
            update.message.reply_text(
                f"No puedes iniciar un nuevo registro con estado {status}.\n"
                "Solo se permite nuevo registro cuando el registro previo esta en INACTIVE.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

    update.message.reply_text(
        "Registro de aliado\n\n"
        "Escribe el nombre del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    _set_flow_step(context, "ally", ALLY_NAME)
    return ALLY_NAME


def ally_name(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "El nombre del negocio no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_NAME

    context.user_data["business_name"] = texto
    update.message.reply_text(
        "Escribe el nombre del dueño o administrador:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "ally", ALLY_OWNER)
    return ALLY_OWNER


def ally_owner(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "El nombre del dueño no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_OWNER

    context.user_data["owner_name"] = texto
    update.message.reply_text(
        "Escribe el número de cédula del dueño o representante:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "ally", ALLY_DOCUMENT)
    return ALLY_DOCUMENT


def ally_document(update, context):
    doc = update.message.text.strip()
    if len(doc) < 5:
        update.message.reply_text(
            "El número de documento parece muy corto. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_DOCUMENT

    context.user_data["ally_document"] = doc
    update.message.reply_text(
        "Escribe el teléfono de contacto del negocio:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "ally", ALLY_PHONE)
    return ALLY_PHONE


def ally_phone(update, context):
    return _handle_phone_input(update, context,
        storage_key="ally_phone",
        current_state=ALLY_PHONE,
        next_state=ALLY_CITY,
        flow="ally",
        next_prompt="Escribe la ciudad del negocio:")


def ally_city(update, context):
    return _handle_text_field_input(update, context,
        error_msg="La ciudad del negocio no puede estar vacía. Escríbela de nuevo:",
        storage_key="city",
        current_state=ALLY_CITY,
        next_state=ALLY_BARRIO,
        flow="ally",
        next_prompt="Escribe el barrio del negocio:")


def ally_barrio(update, context):
    return _handle_text_field_input(update, context,
        error_msg="El barrio no puede estar vacío. Escríbelo de nuevo:",
        storage_key="barrio",
        current_state=ALLY_BARRIO,
        next_state=ALLY_ADDRESS,
        flow="ally",
        next_prompt="Escribe la dirección del negocio:")


def ally_address(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "La dirección no puede estar vacía. Escríbela de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return ALLY_ADDRESS

    context.user_data["address"] = texto
    update.message.reply_text(
        "Envía la ubicación GPS (pin de Telegram) o pega un link de Google Maps."
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "ally", ALLY_UBICACION)
    return ALLY_UBICACION


def ally_ubicacion_handler(update, context):
    """Maneja texto de ubicación del aliado (link o coords)."""
    texto = update.message.text.strip()

    coords = extract_lat_lng_from_text(texto)
    if coords:
        context.user_data["ally_lat"] = coords[0]
        context.user_data["ally_lng"] = coords[1]
        update.message.reply_text("Ubicacion guardada.")
        return _show_ally_confirm(update, context)

    # Geocoding: intentar como direccion escrita
    geo = resolve_location(texto)
    if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
        _mostrar_confirmacion_geocode(
            update.message, context,
            geo, texto,
            "ally_geo_si", "ally_geo_no",
        )
        return ALLY_UBICACION

    update.message.reply_text(
        "No se pudo extraer la ubicacion del texto.\n"
        "Envia un pin de Telegram o pega un link de Google Maps."
    )
    return ALLY_UBICACION


def ally_ubicacion_location_handler(update, context):
    """Maneja ubicación nativa de Telegram (PIN) para registro de aliado."""
    loc = update.message.location
    context.user_data["ally_lat"] = loc.latitude
    context.user_data["ally_lng"] = loc.longitude
    update.message.reply_text("Ubicacion guardada.")
    return _show_ally_confirm(update, context)


def ally_geo_ubicacion_callback(update, context):
    """Maneja confirmacion de geocoding en el registro de aliado."""
    query = update.callback_query
    query.answer()

    if query.data == "ally_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return ALLY_UBICACION
        context.user_data["ally_lat"] = lat
        context.user_data["ally_lng"] = lng
        query.edit_message_text("Ubicacion confirmada.")
        return _show_ally_confirm(update, context)
    else:  # ally_geo_no
        return _geo_siguiente_o_gps(query, context, "ally_geo_si", "ally_geo_no", ALLY_UBICACION)


def _show_ally_confirm(update, context):
    """Muestra resumen de datos del aliado y pide confirmación."""
    business_name = context.user_data.get("business_name", "")
    owner_name = context.user_data.get("owner_name", "")
    ally_document = context.user_data.get("ally_document", "")
    phone = context.user_data.get("ally_phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    address = context.user_data.get("address", "")
    ally_lat = context.user_data.get("ally_lat")
    ally_lng = context.user_data.get("ally_lng")
    if ally_lat is not None and ally_lng is not None:
        ubicacion = f"{ally_lat}, {ally_lng}"
    else:
        ubicacion = "No disponible"

    resumen = (
        "Verifica tus datos de aliado:\n\n"
        f"Negocio: {business_name}\n"
        f"Dueño: {owner_name}\n"
        f"Cédula: {ally_document}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Dirección: {address}\n"
        f"Ubicación: {ubicacion}\n\n"
        "Si todo está bien escribe: SI\n"
        "Si quieres corregir, escribe 'volver' o usa /cancel y vuelve a /soy_aliado"
    )
    update.message.reply_text(resumen)
    _set_flow_step(context, "ally", ALLY_CONFIRM)
    return ALLY_CONFIRM


def ally_confirm(update, context):
    """Confirma y guarda el registro del aliado en BD."""
    confirm_text = update.message.text.strip().upper()
    user = update.effective_user

    if confirm_text not in ("SI", "SÍ", "SI.", "SÍ."):
        update.message.reply_text(
            "Registro cancelado.\n\n"
            "Si deseas intentarlo de nuevo, usa /soy_aliado."
        )
        context.user_data.clear()
        return ConversationHandler.END

    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        db_user = ensure_user(user.id, user.username)
    user_db_id = db_user["id"]

    business_name = context.user_data.get("business_name", "").strip()
    owner_name = context.user_data.get("owner_name", "").strip()
    ally_document = context.user_data.get("ally_document", "").strip()
    address = context.user_data.get("address", "").strip()
    city = context.user_data.get("city", "").strip()
    phone = context.user_data.get("ally_phone", "").strip()
    barrio = context.user_data.get("barrio", "").strip()
    ally_lat = context.user_data.get("ally_lat")
    ally_lng = context.user_data.get("ally_lng")

    try:
        ally_id = create_ally(
            user_id=user_db_id,
            business_name=business_name,
            owner_name=owner_name,
            address=address,
            city=city,
            barrio=barrio,
            phone=phone,
            document_number=ally_document,
        )

        context.user_data["ally_id"] = ally_id

        location_id = create_ally_location(
            ally_id=ally_id,
            label="Principal",
            address=address,
            city=city,
            barrio=barrio,
            phone=None,
            is_default=True,
        )

        if ally_lat and ally_lng and location_id:
            update_ally_location_coords(location_id, ally_lat, ally_lng)

        try:
            context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=(
                    "Nuevo registro de ALIADO pendiente:\n\n"
                    f"Negocio: {business_name}\n"
                    f"Dueño: {owner_name}\n"
                    f"Cédula: {ally_document}\n"
                    f"Teléfono: {phone}\n"
                    f"Ciudad: {city}\n"
                    f"Barrio: {barrio}\n\n"
                    "Usa /aliados_pendientes o /admin para revisarlo."
                )
            )
            _schedule_important_alerts(
                context,
                alert_key="ally_registration_{}".format(ally_id),
                chat_id=ADMIN_USER_ID,
                reminder_text=(
                    "Recordatorio importante:\n"
                    "El registro de aliado #{} sigue pendiente.\n"
                    "Revisa /aliados_pendientes o /admin."
                ).format(ally_id),
            )
        except Exception as e:
            print("[WARN] No se pudo notificar al admin plataforma:", e)

        return show_ally_team_selection(update, context, from_callback=False)

    except ValueError as e:
        print(f"[ERROR] Error de validación al crear aliado: {e}")
        err = str(e)
        if "cédula ya está registrada con otro teléfono" in err or "cedula ya está registrada con otro teléfono" in err:
            update.message.reply_text(
                "No se pudo completar el registro: ese número de cédula ya está registrado con otro teléfono."
            )
        else:
            update.message.reply_text("No se pudo completar el registro con los datos enviados. Verifica e intenta de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        print(f"[ERROR] Error al crear aliado: {e}")
        update.message.reply_text("Error técnico al guardar tu registro. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END


def show_ally_team_selection(update_or_query, context, from_callback=False):
    """
    Muestra lista de equipos (admins disponibles) y opción Ninguno.
    Si elige Ninguno, se asigna al Admin de Plataforma (TEAM_CODE de plataforma).
    """
    ally_id = context.user_data.get("ally_id")
    if not ally_id:
        if from_callback:
            context.bot.send_message(
                chat_id=update_or_query.message.chat_id,
                text="Error técnico: no encuentro el ID del aliado. Intenta /soy_aliado de nuevo."
            )
        else:
            update_or_query.message.reply_text("Error técnico: no encuentro el ID del aliado. Intenta /soy_aliado de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    teams = get_available_admin_teams()
    keyboard = []

    # Botones por equipo disponible
    if teams:
        for row in teams:
            admin_id = row["id"]
            team_name = row["team_name"]
            team_code = row["team_code"]
            admin_status = row["status"]

            # FASE 1: Mostrar estado si es PENDING
            label = f"{team_name} ({team_code})"
            if admin_status == 'PENDING':
                label += " [Pendiente]"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"ally_team:{team_code}")])

    # Opción Ninguno (default plataforma)
    keyboard.append([InlineKeyboardButton("Ninguno (Admin de Plataforma)", callback_data="ally_team:NONE")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = (
        "A que equipo (Administrador) quieres pertenecer?\n"
        "Si eliges Ninguno, quedas por defecto con el Admin de Plataforma y recargas con el."
    )

    if from_callback:
        context.bot.send_message(
            chat_id=update_or_query.message.chat_id,
            text=texto,
            reply_markup=reply_markup
        )
    else:
        update_or_query.message.reply_text(texto, reply_markup=reply_markup)

    return ALLY_TEAM


def ally_team_callback(update, context):
    query = update.callback_query
    data = (query.data or "").strip()
    print(f"[DEBUG] ally_team_callback recibió data={data}")
    query.answer()

    # Validación básica
    if not data.startswith("ally_team:"):
        return ALLY_TEAM

    ally_id = context.user_data.get("ally_id")
    if not ally_id:
        query.edit_message_text("Error técnico: no encuentro el ID del aliado. Intenta /soy_aliado de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    selected = data.split("ally_team:", 1)[1].strip()

    # 1) Si selecciona NONE → asignar a Admin de Plataforma
    if selected.upper() == "NONE":
        platform_admin = get_admin_by_team_code(PLATFORM_TEAM_CODE)
        if not platform_admin:
            query.edit_message_text(
                "En este momento no existe el equipo del Admin de Plataforma (TEAM_CODE: PLATFORM).\n"
                "Crea/asegura ese admin en la tabla admins con team_code='PLATFORM' y status='APPROVED', luego intenta de nuevo."
            )
            context.user_data.clear()
            return ConversationHandler.END

        platform_admin_id = platform_admin["id"]

        try:
            upsert_admin_ally_link(platform_admin_id, ally_id, status="PENDING")
            print(f"[DEBUG] ally_team_callback: vínculo creado ally_id={ally_id}, admin_id={platform_admin_id}, team=PLATFORM")
        except Exception as e:
            print(f"[ERROR] ally_team_callback: upsert_admin_ally_link falló: {e}")
            query.edit_message_text(
                "Error técnico al vincular con el equipo. Intenta /soy_aliado de nuevo."
            )
            context.user_data.clear()
            return ConversationHandler.END

        query.edit_message_text(
            "Listo. Quedaste asignado por defecto al Admin de Plataforma.\n"
            "Tu vínculo quedó en estado PENDING hasta aprobación."
        )
        context.user_data.clear()
        return ConversationHandler.END

    # 2) Si selecciona un TEAM_CODE real
    admin_row = get_admin_by_team_code(selected)
    if not admin_row:
        query.edit_message_text(
            "Ese TEAM_CODE no existe o no está disponible.\n"
            "Vuelve a intentar /soy_aliado."
        )
        context.user_data.clear()
        return ConversationHandler.END

    admin_id = admin_row["id"]
    team_name = admin_row["team_name"]
    team_code = admin_row["team_code"]

    try:
        upsert_admin_ally_link(admin_id, ally_id, status="PENDING")
        print(f"[DEBUG] ally_team_callback: vínculo creado ally_id={ally_id}, admin_id={admin_id}, team={team_code}")
    except Exception as e:
        print(f"[ERROR] ally_team_callback: upsert_admin_ally_link falló: {e}")
        query.edit_message_text(
            "Error técnico al vincular con el equipo. Intenta /soy_aliado de nuevo."
        )
        context.user_data.clear()
        return ConversationHandler.END

    admin_telegram_id = admin_row.get("telegram_id")
    business_name = context.user_data.get("business_name", "Aliado")
    try:
        if admin_telegram_id:
            context.bot.send_message(
                chat_id=admin_telegram_id,
                text=(
                    "Nueva solicitud de aliado para tu equipo.\n\n"
                    "Negocio: {}\n"
                    "Equipo: {} ({})\n\n"
                    "Entra a /mi_admin para aprobar o rechazar."
                ).format(business_name, team_name, team_code)
            )
            _schedule_important_alerts(
                context,
                alert_key="team_ally_pending_{}_{}".format(admin_id, ally_id),
                chat_id=admin_telegram_id,
                reminder_text=(
                    "Recordatorio importante:\n"
                    "Tienes un aliado pendiente de aprobar en tu equipo.\n"
                    "Revisa /mi_admin."
                ),
            )
    except Exception as e:
        print("[WARN] No se pudo notificar al admin local sobre aliado:", e)

    query.edit_message_text(
        "Listo. Elegiste el equipo:\n"
        f"{team_name} ({team_code})\n\n"
        "Tu vínculo quedó en estado PENDING hasta aprobación."
    )
    context.user_data.clear()
    return ConversationHandler.END



# ----- REGISTRO DE REPARTIDOR (flujo unificado) -----

def soy_repartidor(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    existing = get_courier_by_user_id(user_db_id)
    if existing:
        status = existing["status"]
        courier_id = existing["id"]

        rejection_type = get_courier_rejection_type_by_id(courier_id)

        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de repartidor en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de repartidor aprobado (APPROVED). Si necesitas cambios, contacta al administrador."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status != "INACTIVE":
            update.message.reply_text(
                f"No puedes iniciar un nuevo registro con estado {status}.\n"
                "Solo se permite nuevo registro cuando el registro previo esta en INACTIVE.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

    update.message.reply_text(
        "Registro de repartidor\n\n"
        "Escribe tu nombre completo:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    _set_flow_step(context, "courier", COURIER_FULLNAME)
    return COURIER_FULLNAME


def courier_fullname(update, context):
    texto = update.message.text.strip()
    if not texto:
        update.message.reply_text(
            "El nombre no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return COURIER_FULLNAME
    context.user_data["full_name"] = texto
    update.message.reply_text(
        "Escribe tu número de identificación:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_IDNUMBER)
    return COURIER_IDNUMBER


def courier_idnumber(update, context):
    doc = update.message.text.strip()
    if len(doc) < 5:
        update.message.reply_text(
            "El número de documento parece muy corto. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return COURIER_IDNUMBER
    context.user_data["id_number"] = doc
    update.message.reply_text(
        "Escribe tu número de celular:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_PHONE)
    return COURIER_PHONE


def courier_phone(update, context):
    return _handle_phone_input(update, context,
        storage_key="phone",
        current_state=COURIER_PHONE,
        next_state=COURIER_CITY,
        flow="courier",
        next_prompt="Escribe la ciudad donde trabajas:")


def courier_city(update, context):
    return _handle_text_field_input(update, context,
        error_msg="La ciudad no puede estar vacía. Escríbela de nuevo:",
        storage_key="city",
        current_state=COURIER_CITY,
        next_state=COURIER_BARRIO,
        flow="courier",
        next_prompt="Escribe el barrio o sector principal donde trabajas:")


def courier_barrio(update, context):
    return _handle_text_field_input(update, context,
        error_msg="El barrio no puede estar vacío. Escríbelo de nuevo:",
        storage_key="barrio",
        current_state=COURIER_BARRIO,
        next_state=COURIER_RESIDENCE_ADDRESS,
        flow="courier",
        next_prompt="Escribe tu dirección de residencia:")


def courier_residence_address(update, context):
    address = update.message.text.strip()
    if not address:
        update.message.reply_text(
            "La dirección no puede estar vacía. Escríbela de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return COURIER_RESIDENCE_ADDRESS
    context.user_data["residence_address"] = address
    update.message.reply_text(
        "Envía tu ubicación GPS (pin de Telegram) o pega un link de Google Maps."
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_RESIDENCE_LOCATION)
    return COURIER_RESIDENCE_LOCATION


def courier_residence_location(update, context):
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
        else:
            # Geocoding: intentar como direccion escrita
            geo = resolve_location(text)
            if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
                _mostrar_confirmacion_geocode(
                    update.message, context,
                    geo, text,
                    "courier_geo_si", "courier_geo_no",
                )
                return COURIER_RESIDENCE_LOCATION

    if lat is None or lng is None:
        update.message.reply_text(
            "No pude detectar la ubicacion. Envia un pin de Telegram o pega un link de Google Maps."
        )
        return COURIER_RESIDENCE_LOCATION

    context.user_data["residence_lat"] = lat
    context.user_data["residence_lng"] = lng
    update.message.reply_text(
        "Ubicacion guardada.\n\n"
        "Escribe la placa de tu moto (o escribe 'ninguna' si no tienes):"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_PLATE)
    return COURIER_PLATE


def courier_geo_ubicacion_callback(update, context):
    """Maneja confirmacion de geocoding en el registro de repartidor."""
    query = update.callback_query
    query.answer()

    if query.data == "courier_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return COURIER_RESIDENCE_LOCATION
        context.user_data["residence_lat"] = lat
        context.user_data["residence_lng"] = lng
        query.edit_message_text(
            "Ubicacion confirmada.\n\n"
            "Escribe la placa de tu moto (o escribe 'ninguna' si no tienes):"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        _set_flow_step(context, "courier", COURIER_PLATE)
        return COURIER_PLATE
    else:  # courier_geo_no
        return _geo_siguiente_o_gps(query, context, "courier_geo_si", "courier_geo_no", COURIER_RESIDENCE_LOCATION)


def courier_plate(update, context):
    context.user_data["plate"] = update.message.text.strip()
    update.message.reply_text(
        "Escribe el tipo de moto (Ejemplo: Bóxer 100, FZ, scooter, bicicleta, etc.):"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_BIKETYPE)
    return COURIER_BIKETYPE


def courier_biketype(update, context):
    context.user_data["bike_type"] = update.message.text.strip()
    update.message.reply_text(
        "Perfecto. Ahora necesitamos verificar tu identidad.\n\n"
        "Envía una foto del FRENTE de tu cédula de ciudadanía:"
        + _OPTIONS_HINT
    )
    _set_flow_step(context, "courier", COURIER_CEDULA_FRONT)
    return COURIER_CEDULA_FRONT


def courier_cedula_front(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una foto (imagen) del frente de tu cédula." + _OPTIONS_HINT
        )
        return COURIER_CEDULA_FRONT
    context.user_data["cedula_front_file_id"] = update.message.photo[-1].file_id
    update.message.reply_text(
        "Foto del frente recibida.\n\n"
        "Ahora envía una foto del REVERSO de tu cédula:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "courier", COURIER_CEDULA_BACK)
    return COURIER_CEDULA_BACK


def courier_cedula_back(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una foto (imagen) del reverso de tu cédula." + _OPTIONS_HINT
        )
        return COURIER_CEDULA_BACK
    context.user_data["cedula_back_file_id"] = update.message.photo[-1].file_id
    update.message.reply_text(
        "Foto del reverso recibida.\n\n"
        "Por último, envía una SELFIE (foto de tu cara) tomada en este momento:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "courier", COURIER_SELFIE)
    return COURIER_SELFIE


def courier_selfie(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una selfie (foto de tu cara)." + _OPTIONS_HINT
        )
        return COURIER_SELFIE
    context.user_data["selfie_file_id"] = update.message.photo[-1].file_id

    full_name = context.user_data.get("full_name", "")
    id_number = context.user_data.get("id_number", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    plate = context.user_data.get("plate", "")
    bike_type = context.user_data.get("bike_type", "")
    residence_address = context.user_data.get("residence_address", "") or "No registrada"
    residence_lat = context.user_data.get("residence_lat")
    residence_lng = context.user_data.get("residence_lng")
    if residence_lat is not None and residence_lng is not None:
        residence_location = "{}, {}".format(residence_lat, residence_lng)
    else:
        residence_location = "No disponible"

    resumen = (
        "Fotos recibidas. Verifica tus datos de repartidor:\n\n"
        f"Nombre: {full_name}\n"
        f"Cédula: {id_number}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Dirección residencia: {residence_address}\n"
        f"Ubicación residencia: {residence_location}\n"
        f"Placa: {plate}\n"
        f"Tipo de moto: {bike_type}\n\n"
        "Si todo está bien escribe: SI\n"
        "Si quieres corregir, escribe 'volver' o usa /cancel y vuelve a /soy_repartidor"
    )
    update.message.reply_text(resumen)
    _set_flow_step(context, "courier", COURIER_CONFIRM)
    return COURIER_CONFIRM


def admin_cedula_front(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una foto (imagen) del frente de tu cédula." + _OPTIONS_HINT
        )
        return LOCAL_ADMIN_CEDULA_FRONT
    context.user_data["admin_cedula_front_file_id"] = update.message.photo[-1].file_id
    update.message.reply_text(
        "Foto del frente recibida.\n\n"
        "Ahora envía una foto del REVERSO de tu cédula:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_CEDULA_BACK)
    return LOCAL_ADMIN_CEDULA_BACK


def admin_cedula_back(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una foto (imagen) del reverso de tu cédula." + _OPTIONS_HINT
        )
        return LOCAL_ADMIN_CEDULA_BACK
    context.user_data["admin_cedula_back_file_id"] = update.message.photo[-1].file_id
    update.message.reply_text(
        "Foto del reverso recibida.\n\n"
        "Por último, envía una SELFIE (foto de tu cara) tomada en este momento:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_SELFIE)
    return LOCAL_ADMIN_SELFIE


def admin_selfie(update, context):
    if not update.message.photo:
        update.message.reply_text(
            "Por favor envía una selfie (foto de tu cara)." + _OPTIONS_HINT
        )
        return LOCAL_ADMIN_SELFIE
    context.user_data["admin_selfie_file_id"] = update.message.photo[-1].file_id

    full_name = context.user_data.get("admin_name", "")
    document_number = context.user_data.get("admin_document", "")
    team_name = context.user_data.get("admin_team_name", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("admin_city", "")
    barrio = context.user_data.get("admin_barrio", "")
    residence_address = context.user_data.get("admin_residence_address", "")
    lat = context.user_data.get("admin_residence_lat")
    lng = context.user_data.get("admin_residence_lng")

    resumen = (
        "Fotos recibidas. Verifica tus datos de Administrador Local:\n\n"
        "Nombre: {}\n"
        "Cédula: {}\n"
        "Equipo: {}\n"
        "Teléfono: {}\n"
        "Ciudad: {}\n"
        "Barrio: {}\n"
        "Dirección: {}\n"
        "Ubicación: {}, {}\n\n"
        "Condiciones para Administrador Local:\n"
        "1) Para ser aprobado debes registrar al menos 10 repartidores.\n"
        "2) Cada repartidor debe tener recarga mínima de 5000.\n"
        "3) Si tu administrador local no tiene saldo activo con la plataforma, su operación queda suspendida.\n\n"
        "Si todo está correcto, escribe ACEPTAR para finalizar.\n"
        "Si quieres corregir, escribe 'volver' o usa /cancel."
    ).format(full_name, document_number, team_name, phone, city, barrio, residence_address, lat, lng)
    update.message.reply_text(resumen)
    _set_flow_step(context, "admin", LOCAL_ADMIN_CONFIRM)
    return LOCAL_ADMIN_CONFIRM


def courier_confirm(update, context):
    confirm_text = update.message.text.strip().upper()
    user = update.effective_user
    db_user = get_user_by_telegram_id(user.id)

    if confirm_text not in ("SI", "SÍ", "SI.", "SÍ."):
        update.message.reply_text(
            "Registro cancelado.\n\n"
            "Si deseas intentarlo de nuevo, usa /soy_repartidor."
        )
        context.user_data.clear()
        return ConversationHandler.END

    full_name = context.user_data.get("full_name", "")
    id_number = context.user_data.get("id_number", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("city", "")
    barrio = context.user_data.get("barrio", "")
    plate = context.user_data.get("plate", "")
    bike_type = context.user_data.get("bike_type", "")
    residence_address = context.user_data.get("residence_address", "")
    residence_lat = context.user_data.get("residence_lat")
    residence_lng = context.user_data.get("residence_lng")
    cedula_front_file_id = context.user_data.get("cedula_front_file_id")
    cedula_back_file_id = context.user_data.get("cedula_back_file_id")
    selfie_file_id = context.user_data.get("selfie_file_id")

    code = f"R-{db_user['id']:04d}"

    try:
        create_courier(
            user_id=db_user["id"],
            full_name=full_name,
            id_number=id_number,
            phone=phone,
            city=city,
            barrio=barrio,
            plate=plate,
            bike_type=bike_type,
            code=code,
            residence_address=residence_address,
            residence_lat=residence_lat,
            residence_lng=residence_lng,
            cedula_front_file_id=cedula_front_file_id,
            cedula_back_file_id=cedula_back_file_id,
            selfie_file_id=selfie_file_id,
        )
    except ValueError as e:
        update.message.reply_text(
            "No se pudo completar el registro: {}\n\n"
            "Revisa tus datos y vuelve a intentarlo con /soy_repartidor.".format(e)
        )
        context.user_data.clear()
        return ConversationHandler.END

    courier = get_courier_by_user_id(db_user["id"])
    if not courier:
        update.message.reply_text(
            "Se registró tu usuario, pero ocurrió un error obteniendo tu perfil de repartidor.\n"
            "Intenta de nuevo."
        )
        context.user_data.clear()
        return ConversationHandler.END

    courier_id = courier["id"]

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
                "Tipo de moto: {}\n\n"
                "Usa /admin para revisarlo."
            ).format(full_name, id_number, phone, city, barrio, plate, bike_type)
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
        print("[WARN] No se pudo notificar al admin plataforma:", e)

    context.user_data["new_courier_id"] = courier_id

    update.message.reply_text(
        "Repartidor registrado exitosamente.\n\n"
        f"Nombre: {full_name}\n"
        f"Cédula: {id_number}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Placa: {plate}\n"
        f"Tipo de moto: {bike_type}\n"
        f"Código interno: {code}\n\n"
        "Tu estado es: PENDING."
    )

    return show_courier_team_selection(update, context)


def show_courier_team_selection(update, context):
    """Muestra lista de equipos (admins) con botones para el repartidor."""
    courier_id = context.user_data.get("new_courier_id")
    if not courier_id:
        update.message.reply_text("Error técnico: no encuentro el ID del repartidor. Intenta /soy_repartidor de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    teams = get_available_admin_teams()
    keyboard = []

    if teams:
        for row in teams:
            admin_id = row["id"]
            team_name = row["team_name"]
            team_code = row["team_code"]
            admin_status = row["status"]

            label = f"{team_name} ({team_code})"
            if admin_status == 'PENDING':
                label += " [Pendiente]"
            keyboard.append([InlineKeyboardButton(label, callback_data=f"courier_team:{team_code}")])

    keyboard.append([InlineKeyboardButton("Ninguno (Admin de Plataforma)", callback_data="courier_team:NONE")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "¿A qué equipo (Administrador) quieres pertenecer?\n"
        "Si eliges Ninguno, quedas por defecto con el Admin de Plataforma.",
        reply_markup=reply_markup
    )

    return COURIER_TEAM


def courier_team_callback(update, context):
    """Maneja la selección de equipo del repartidor (botones)."""
    query = update.callback_query
    data = (query.data or "").strip()
    query.answer()

    if not data.startswith("courier_team:"):
        return COURIER_TEAM

    courier_id = context.user_data.get("new_courier_id")
    if not courier_id:
        query.edit_message_text("Error técnico: no encuentro el ID del repartidor. Intenta /soy_repartidor de nuevo.")
        context.user_data.clear()
        return ConversationHandler.END

    selected = data.split("courier_team:", 1)[1].strip()

    if selected.upper() == "NONE":
        platform_admin = get_admin_by_team_code(PLATFORM_TEAM_CODE)
        if not platform_admin:
            query.edit_message_text(
                "En este momento no existe el equipo del Admin de Plataforma (TEAM_CODE: PLATFORM).\n"
                "Contacta al administrador."
            )
            context.user_data.clear()
            return ConversationHandler.END

        platform_admin_id = platform_admin["id"]

        try:
            create_admin_courier_link(platform_admin_id, courier_id)
        except Exception as e:
            print(f"[ERROR] courier_team_callback: create_admin_courier_link falló: {e}")
            query.edit_message_text("Error técnico al vincular con el equipo. Intenta /soy_repartidor de nuevo.")
            context.user_data.clear()
            return ConversationHandler.END

        query.edit_message_text(
            "Listo. Quedaste asignado por defecto al Admin de Plataforma.\n"
            "Tu vínculo quedó en estado PENDING hasta aprobación."
        )
        context.user_data.clear()
        return ConversationHandler.END

    admin_row = get_admin_by_team_code(selected)
    if not admin_row:
        query.edit_message_text(
            "Ese código de equipo no existe o no está disponible.\n"
            "Vuelve a intentar /soy_repartidor."
        )
        context.user_data.clear()
        return ConversationHandler.END

    admin_id = admin_row["id"]
    admin_team = admin_row["team_name"]
    admin_team_code = admin_row["team_code"]
    admin_telegram_id = admin_row["telegram_id"]

    try:
        create_admin_courier_link(admin_id, courier_id)
    except Exception as e:
        print("[ERROR] create_admin_courier_link:", e)
        query.edit_message_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END

    try:
        context.bot.send_message(
            chat_id=admin_telegram_id,
            text=(
                "Nueva solicitud de repartidor para tu equipo.\n\n"
                f"Repartidor ID: {courier_id}\n"
                f"Equipo: {admin_team}\n"
                f"Código: {admin_team_code}\n\n"
                "Entra a /mi_admin para aprobar o rechazar."
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
        print("[WARN] No se pudo notificar al admin local:", e)

    query.edit_message_text(
        "Listo. Elegiste el equipo:\n"
        f"{admin_team} ({admin_team_code})\n\n"
        "Tu vínculo quedó en estado PENDING hasta aprobación."
    )
    context.user_data.clear()
    return ConversationHandler.END

def nuevo_pedido_desde_cotizador(update, context):
    """Entry point de nuevo_pedido_conv cuando el aliado confirma pedido desde el cotizador."""
    query = update.callback_query
    query.answer()

    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        query.edit_message_text("No estas registrado. Usa /start primero.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("Tu registro de aliado no esta activo.")
        return ConversationHandler.END

    if not ensure_terms(update, context, user.id, role="ALLY"):
        return ConversationHandler.END

    # Transferir prefill del cotizador a claves del flujo de pedido
    context.user_data["ally_id"] = ally["id"]
    context.user_data["active_ally_id"] = ally["id"]
    context.user_data["ally"] = ally
    context.user_data["pickup_lat"] = context.user_data.pop("prefill_pickup_lat", None)
    context.user_data["pickup_lng"] = context.user_data.pop("prefill_pickup_lng", None)
    context.user_data["dropoff_lat"] = context.user_data.pop("prefill_dropoff_lat", None)
    context.user_data["dropoff_lng"] = context.user_data.pop("prefill_dropoff_lng", None)
    context.user_data["cotizador_prefill_dropoff"] = True

    if query.data == "cotizar_cust_recurrente":
        customers = list_ally_customers(ally["id"], limit=10)
        if not customers:
            query.edit_message_text("No tienes clientes guardados.\n\nEscribe el nombre del cliente:")
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE
        keyboard = []
        for c in customers:
            keyboard.append([InlineKeyboardButton(
                f"{c['name']} - {c['phone']}",
                callback_data=f"pedido_sel_cust_{c['id']}"
            )])
        keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="pedido_buscar_cliente")])
        keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])
        query.edit_message_text(
            "CLIENTES RECURRENTES\n\nSelecciona un cliente:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return PEDIDO_SELECTOR_CLIENTE

    # cotizar_cust_nuevo
    query.edit_message_text("Escribe el nombre del cliente:")
    context.user_data["is_new_customer"] = True
    return PEDIDO_NOMBRE


def nueva_ruta_desde_cotizador(update, context):
    """Entry point de nueva_ruta_conv cuando el aliado elige 'Varias entregas' desde el cotizador."""
    query = update.callback_query
    query.answer()
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        query.edit_message_text("No estas registrado. Usa /start primero.")
        return ConversationHandler.END
    ally = get_ally_by_user_id(db_user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("Tu registro de aliado no esta activo.")
        return ConversationHandler.END
    pickup_lat = context.user_data.pop("prefill_ruta_pickup_lat", None)
    pickup_lng = context.user_data.pop("prefill_ruta_pickup_lng", None)
    # Buscar la ubicacion guardada que coincida con las coords del cotizador
    pickup_address = ""
    pickup_location_id = None
    if pickup_lat and pickup_lng:
        locations = get_ally_locations(ally["id"])
        for loc in locations:
            if loc.get("lat") == pickup_lat and loc.get("lng") == pickup_lng:
                pickup_address = loc.get("address") or ""
                pickup_location_id = loc.get("id")
                break
    context.user_data.clear()
    context.user_data["ruta_ally_id"] = ally["id"]
    context.user_data["ruta_ally"] = ally
    context.user_data["ruta_paradas"] = []
    context.user_data["ruta_pickup_lat"] = pickup_lat
    context.user_data["ruta_pickup_lng"] = pickup_lng
    context.user_data["ruta_pickup_address"] = pickup_address
    context.user_data["ruta_pickup_location_id"] = pickup_location_id
    return _ruta_iniciar_parada(query, context)


def nuevo_pedido(update, context):
    user = update.effective_user
    message = update.effective_message
    try:
        print(
            f"[DEBUG][nuevo_pedido] entry user_id={getattr(user, 'id', None)} "
            f"chat_id={getattr(getattr(message, 'chat', None), 'id', None)} "
            f"text={getattr(message, 'text', None)!r}",
            flush=True,
        )

        ensure_user(user.id, user.username)
        db_user = get_user_by_telegram_id(user.id)
        print(
            f"[DEBUG][nuevo_pedido] db_user_found={bool(db_user)} user_id={getattr(user, 'id', None)}",
            flush=True,
        )

        if not db_user:
            if message:
                message.reply_text("Aun no estas registrado en el sistema. Usa /start primero.")
            return ConversationHandler.END

        ally = get_ally_by_user_id(db_user["id"])
        print(
            f"[DEBUG][nuevo_pedido] ally_found={bool(ally)} ally_status={ally.get('status') if ally else None}",
            flush=True,
        )
        if not ally:
            if message:
                message.reply_text(
                    "Aun no estas registrado como aliado.\n"
                    "Si tienes un negocio, registrate con /soy_aliado."
                )
            return ConversationHandler.END

        if ally["status"] != "APPROVED":
            if message:
                message.reply_text(
                    "Tu registro como aliado todavia no ha sido aprobado por el administrador.\n"
                    "Cuando tu estado sea APPROVED podras crear pedidos con /nuevo_pedido."
                )
            return ConversationHandler.END

        if not ensure_terms(update, context, user.id, role="ALLY"):
            print("[DEBUG][nuevo_pedido] blocked_by_terms=True", flush=True)
            return ConversationHandler.END

        context.user_data.clear()
        context.user_data["ally_id"] = ally["id"]
        context.user_data["active_ally_id"] = ally["id"]
        context.user_data["ally"] = ally

        show_flow_menu(update, context, "Iniciando nuevo pedido...")

        keyboard = [
            [InlineKeyboardButton("Cliente recurrente", callback_data="pedido_cliente_recurrente")],
            [InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")],
        ]

        last_order = get_last_order_by_ally(ally["id"])
        if last_order:
            keyboard.append([InlineKeyboardButton("Repetir ultimo pedido", callback_data="pedido_repetir_ultimo")])

        keyboard.append([InlineKeyboardButton("Varias entregas (ruta)", callback_data="pedido_a_ruta")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        if message:
            message.reply_text(
                "CREAR NUEVO PEDIDO\n\n"
                "Selecciona una opcion:",
                reply_markup=reply_markup
            )
        return PEDIDO_SELECTOR_CLIENTE
    except Exception as e:
        print(f"[ERROR][nuevo_pedido] {type(e).__name__}: {e}", flush=True)
        print(traceback.format_exc(), flush=True)
        if message:
            message.reply_text("Se produjo un error al iniciar el pedido. Intenta /nuevo_pedido.")
        return ConversationHandler.END


def pedido_selector_cliente_callback(update, context):
    """Maneja la seleccion de tipo de cliente en /nuevo_pedido."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally_id = context.user_data.get("active_ally_id")
    if not ally_id:
        query.edit_message_text("No hay un aliado activo. Regresa al menu e inicia el pedido nuevamente.")
        return ConversationHandler.END

    if data == "pedido_cliente_recurrente":
        # Mostrar lista de clientes recurrentes
        customers = list_ally_customers(ally_id, limit=10)
        if not customers:
            query.edit_message_text(
                "No tienes clientes guardados.\n\n"
                "Escribe el nombre del cliente para crear el pedido:"
            )
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE

        keyboard = []
        for c in customers:
            btn_text = f"{c['name']} - {c['phone']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_cust_{c['id']}")])

        keyboard.append([InlineKeyboardButton("Buscar cliente", callback_data="pedido_buscar_cliente")])
        keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "CLIENTES RECURRENTES\n\n"
            "Selecciona un cliente:",
            reply_markup=reply_markup
        )
        return PEDIDO_SELECTOR_CLIENTE

    elif data == "pedido_cliente_nuevo":
        # Limpiar datos residuales de flujos anteriores para evitar reusar ubicacion/cliente
        for _k in ("customer_id", "customer_address", "customer_address_id",
                   "dropoff_lat", "dropoff_lng", "customer_city", "customer_barrio",
                   "customer_name", "customer_phone"):
            context.user_data.pop(_k, None)
        query.edit_message_text("Escribe el nombre del cliente:")
        context.user_data["is_new_customer"] = True
        return PEDIDO_NOMBRE

    elif data == "pedido_repetir_ultimo":
        last_order = get_last_order_by_ally(ally_id)
        if last_order:
            context.user_data["customer_name"] = last_order["customer_name"]
            context.user_data["customer_phone"] = last_order["customer_phone"]
            context.user_data["customer_address"] = last_order["customer_address"]
            context.user_data["is_new_customer"] = False

            # Ir al selector de pickup
            return mostrar_selector_pickup(query, context, edit=True)
        else:
            query.edit_message_text("No hay pedidos anteriores. Escribe el nombre del cliente:")
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE

    elif data == "pedido_buscar_cliente":
        query.edit_message_text("Escribe el nombre o telefono del cliente a buscar:")
        return PEDIDO_BUSCAR_CLIENTE

    elif data.startswith("pedido_sel_cust_"):
        # Selecciono un cliente recurrente
        customer_id = int(data.replace("pedido_sel_cust_", ""))
        customer = get_ally_customer_by_id(customer_id, ally_id)
        if not customer:
            query.edit_message_text("Cliente no encontrado. Escribe el nombre del cliente:")
            context.user_data["is_new_customer"] = True
            return PEDIDO_NOMBRE

        context.user_data["customer_id"] = customer_id
        context.user_data["customer_name"] = customer["name"]
        context.user_data["customer_phone"] = customer["phone"]
        context.user_data["is_new_customer"] = False

        # Mostrar direcciones del cliente
        addresses = list_customer_addresses(customer_id)
        if not addresses:
            query.edit_message_text(
                f"Cliente: {customer['name']}\n"
                f"Telefono: {customer['phone']}\n\n"
                "Este cliente no tiene direcciones guardadas.\n"
                "Escribe la direccion de entrega:"
            )
            return PEDIDO_DIRECCION

        keyboard = []
        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            btn_text = f"{label}: {addr['address_text'][:30]}..."
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_addr_{addr['id']}")])

        keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="pedido_nueva_dir")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"Cliente: {customer['name']}\n"
            f"Telefono: {customer['phone']}\n\n"
            "Selecciona la direccion de entrega:",
            reply_markup=reply_markup
        )
        return PEDIDO_SELECCIONAR_DIRECCION

    return PEDIDO_SELECTOR_CLIENTE


def pedido_buscar_cliente(update, context):
    """Busca clientes por nombre o telefono."""
    query_text = update.message.text.strip()
    ally_id = context.user_data.get("active_ally_id")

    if not ally_id:
        update.message.reply_text("No hay un aliado activo. Regresa al menu e inicia el pedido nuevamente.")
        return ConversationHandler.END

    results = search_ally_customers(ally_id, query_text, limit=10)
    if not results:
        update.message.reply_text(
            f"No se encontraron clientes con '{query_text}'.\n\n"
            "Escribe el nombre del cliente para crear el pedido:"
        )
        context.user_data["is_new_customer"] = True
        return PEDIDO_NOMBRE

    keyboard = []
    for c in results:
        btn_text = f"{c['name']} - {c['phone']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"pedido_sel_cust_{c['id']}")])

    keyboard.append([InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"Resultados para '{query_text}':\n\n"
        "Selecciona un cliente:",
        reply_markup=reply_markup
    )
    return PEDIDO_SELECTOR_CLIENTE


def pedido_seleccionar_direccion_callback(update, context):
    """Maneja la seleccion de direccion del cliente."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pedido_nueva_dir":
        query.edit_message_text(
            "Escribe la nueva direccion de entrega (nombre del lugar o calle),\n"
            "o envia un pin de ubicacion de Telegram."
        )
        return PEDIDO_UBICACION

    elif data == "guardar_dir_cliente_si":
        # Guardar la direccion del cliente
        customer_id = context.user_data.get("customer_id")
        address_text = context.user_data.get("customer_address", "")
        lat = context.user_data.get("dropoff_lat")
        lng = context.user_data.get("dropoff_lng")
        if customer_id and address_text:
            create_customer_address(
                customer_id=customer_id,
                label=address_text[:30],
                address_text=address_text,
                city=context.user_data.get("customer_city", ""),
                barrio=context.user_data.get("customer_barrio", ""),
                lat=lat,
                lng=lng
            )
            query.edit_message_text("Direccion guardada.")
        else:
            query.edit_message_text("OK, continuamos.")
        return mostrar_selector_pickup(query, context, edit=False)

    elif data == "guardar_dir_cliente_no":
        query.edit_message_text("OK, usaremos esta direccion solo esta vez.")
        return mostrar_selector_pickup(query, context, edit=False)

    elif data.startswith("pedido_sel_addr_"):
        address_id = int(data.replace("pedido_sel_addr_", ""))
        customer_id = context.user_data.get("customer_id")
        address = get_customer_address_by_id(address_id, customer_id)

        if not address:
            query.edit_message_text(
                "Direccion no encontrada. Escribe la direccion de entrega (nombre del lugar o calle),\n"
                "o envia un pin de ubicacion de Telegram."
            )
            return PEDIDO_UBICACION

        context.user_data["customer_address_id"] = address_id
        context.user_data["customer_address"] = address["address_text"]
        context.user_data["customer_city"] = address["city"] or ""
        context.user_data["customer_barrio"] = address["barrio"] or ""
        context.user_data["dropoff_lat"] = address["lat"]
        context.user_data["dropoff_lng"] = address["lng"]

        # Guardar nota de la direccion si existe
        nota_direccion = address["notes"] or ""
        context.user_data["nota_direccion"] = nota_direccion

        # Si hay nota de direccion, mostrarla y preguntar si agregar instrucciones
        if nota_direccion:
            keyboard = [
                [InlineKeyboardButton("Si", callback_data="pedido_instr_si")],
                [InlineKeyboardButton("No", callback_data="pedido_instr_no")],
            ]
            query.edit_message_text(
                f"Nota para el repartidor:\n{nota_direccion}\n\n"
                "Deseas agregar instrucciones adicionales para este pedido?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return PEDIDO_INSTRUCCIONES_EXTRA

        # Sin nota, continuar al selector de pickup
        return mostrar_selector_pickup(query, context, edit=True)

    return PEDIDO_SELECCIONAR_DIRECCION


def pedido_instrucciones_callback(update, context):
    """Maneja la respuesta sobre instrucciones adicionales."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pedido_instr_si":
        query.edit_message_text(
            "Escribe las instrucciones adicionales para el repartidor:"
        )
        return PEDIDO_INSTRUCCIONES_EXTRA

    elif data == "pedido_instr_no":
        # Usar solo la nota de la direccion como instrucciones finales
        nota_direccion = context.user_data.get("nota_direccion", "")
        context.user_data["instructions"] = nota_direccion
        return mostrar_selector_pickup(query, context, edit=True)

    return PEDIDO_INSTRUCCIONES_EXTRA


def pedido_instrucciones_text(update, context):
    """Captura las instrucciones adicionales escritas por el aliado."""
    texto_adicional = update.message.text.strip()
    nota_direccion = context.user_data.get("nota_direccion", "")

    # Concatenar nota de direccion con instrucciones adicionales
    if nota_direccion and texto_adicional:
        context.user_data["instructions"] = f"{nota_direccion}\n{texto_adicional}"
    elif texto_adicional:
        context.user_data["instructions"] = texto_adicional
    else:
        context.user_data["instructions"] = nota_direccion

    return mostrar_selector_pickup(update, context, edit=False)


def get_tipo_servicio_keyboard():
    """Retorna InlineKeyboardMarkup con opciones de tipo de servicio."""
    keyboard = [
        [InlineKeyboardButton("Entrega", callback_data="pedido_tipo_entrega")],
        [InlineKeyboardButton("🛒 Compras", callback_data="pedido_tipo_compras")],
    ]
    return InlineKeyboardMarkup(keyboard)


def mostrar_selector_tipo_servicio(query_or_update, context, edit=False, texto_intro=None):
    """Muestra selector de tipo de servicio con botones.

    Args:
        query_or_update: CallbackQuery o Update
        context: Context del bot
        edit: Si True, edita el mensaje existente
        texto_intro: Texto introductorio opcional (ej: info del cliente)
    """
    reply_markup = get_tipo_servicio_keyboard()

    if texto_intro:
        texto = f"{texto_intro}\n\nSelecciona el tipo de servicio:"
    else:
        texto = "TIPO DE SERVICIO\n\nSelecciona una opcion:"

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(texto, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)

    return PEDIDO_TIPO_SERVICIO


def pedido_tipo_servicio_callback(update, context):
    """Maneja la seleccion de tipo de servicio por boton."""
    query = update.callback_query
    query.answer()
    data = query.data

    # Mapeo de callbacks a texto legible
    tipos_map = {
        "pedido_tipo_entrega": "Entrega",
        # Compatibilidad con mensajes viejos en chats ya abiertos
        "pedido_tipo_entrega_rapida": "Entrega",
        "pedido_tipo_domicilio": "Entrega",
        "pedido_tipo_mensajeria": "Entrega",
        "pedido_tipo_recogida": "Recogida en tienda",
        "pedido_tipo_compras": "Compras",
    }

    if data not in tipos_map:
        query.edit_message_text("Opcion no valida. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END

    context.user_data["service_type"] = tipos_map[data]

    # Si es Compras, pedir lista de productos
    if data == "pedido_tipo_compras":
        buy_config = get_buy_pricing_config()
        free_th = buy_config.get("free_threshold", 2)
        extra_fee = buy_config.get("extra_fee", 1000)
        extra_fee_fmt = f"${extra_fee:,}".replace(",", ".")
        query.edit_message_text(
            "🛒 COMPRAS\n\n"
            "Escribe la lista de productos con sus cantidades.\n\n"
            "Ejemplo:\n"
            "3 platanos, 2 bolsas de leche, 1 jabon\n\n"
            f"Los primeros {free_th} productos no tienen recargo.\n"
            f"Cada producto adicional: +{extra_fee_fmt}"
        )
        return PEDIDO_COMPRAS_CANTIDAD

    # Si viene de cliente recurrente pero faltan campos, rehidratar desde BD
    customer_id = context.user_data.get("customer_id")
    ally_id = context.user_data.get("active_ally_id")
    if customer_id and ally_id:
        if not context.user_data.get("customer_name") or not context.user_data.get("customer_phone"):
            customer = get_ally_customer_by_id(customer_id, ally_id)
            if customer:
                if not context.user_data.get("customer_name"):
                    context.user_data["customer_name"] = customer.get("name") or ""
                if not context.user_data.get("customer_phone"):
                    context.user_data["customer_phone"] = customer.get("phone") or ""

    # Verificar si ya tenemos todos los datos del cliente
    has_name = context.user_data.get("customer_name")
    has_phone = context.user_data.get("customer_phone")
    has_address = context.user_data.get("customer_address")

    if has_name and has_phone and has_address:
        # Ya tenemos datos del cliente, preguntar por base requerida
        return mostrar_pregunta_base(query, context, edit=True)
    else:
        # Si ya se selecciono un cliente recurrente, nunca re-pedir el nombre por defecto
        if customer_id:
            if not has_address:
                query.edit_message_text(
                    f"Tipo de servicio: {tipos_map[data]}\n\n"
                    "Falta la direccion de entrega.\n"
                    "Escribe la direccion de entrega:"
                )
                return PEDIDO_DIRECCION
            if not has_name:
                query.edit_message_text(
                    f"Tipo de servicio: {tipos_map[data]}\n\n"
                    "Falta el nombre del cliente.\n"
                    "Escribe el nombre del cliente:"
                )
                return PEDIDO_NOMBRE
            if not has_phone:
                query.edit_message_text(
                    f"Tipo de servicio: {tipos_map[data]}\n\n"
                    "Falta el telefono del cliente.\n"
                    "Escribe el numero de telefono del cliente:"
                )
                return PEDIDO_TELEFONO

        # Cliente nuevo: pedir nombre
        query.edit_message_text(
            f"Tipo de servicio: {tipos_map[data]}\n\n"
            "Ahora escribe el nombre del cliente:"
        )
        return PEDIDO_NOMBRE


def _parsear_lista_productos(texto):
    """Parsea una lista de productos con cantidades.

    Acepta separadores: coma, punto y coma, salto de linea.
    Acepta formatos por item:
      - "3 platanos"   (cantidad al inicio)
      - "platanos 3"   (cantidad al final)
      - "platanos x3"  (cantidad al final con prefijo x)
      - "platanos"     (sin cantidad → cuenta como 1)

    Returns:
        (items, total) donde items = [(qty, nombre), ...], total = suma de cantidades
        Si la lista esta vacia, retorna ([], 0).
    """
    import re
    items = []
    total = 0
    partes = re.split(r'[,;\n]+', texto)
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        # Cantidad al inicio: "3 platanos"
        m = re.match(r'^(\d+)\s+(.+)$', parte)
        if m:
            qty = int(m.group(1))
            name = m.group(2).strip()
            if not name:
                continue
            items.append((qty, name))
            total += qty
            continue
        # Cantidad al final con x opcional: "platanos x3" o "platanos 3"
        m = re.match(r'^(.+?)\s+[xX]?(\d+)$', parte)
        if m:
            name = m.group(1).strip()
            if not name:
                continue
            qty = int(m.group(2))
            items.append((qty, name))
            total += qty
            continue
        # Sin cantidad explicita → 1 unidad
        items.append((1, parte))
        total += 1
    return items, total


def pedido_compras_cantidad_handler(update, context):
    """Captura y parsea la lista de productos para Compras."""
    texto = update.message.text.strip()

    items, total = _parsear_lista_productos(texto)

    if not items or total <= 0:
        update.message.reply_text(
            "No pude leer la lista. Escribe la cantidad y el nombre de cada producto.\n\n"
            "Ejemplo:\n"
            "3 platanos, 2 bolsas de leche, 1 jabon"
        )
        return PEDIDO_COMPRAS_CANTIDAD

    if total > 50:
        update.message.reply_text(
            f"El total de unidades ({total}) supera el maximo de 50.\n"
            "Ajusta la lista e intentalo de nuevo:"
        )
        return PEDIDO_COMPRAS_CANTIDAD

    context.user_data["buy_products_list"] = texto
    context.user_data["buy_products_count"] = total

    # Continuar con el flujo normal
    has_name = context.user_data.get("customer_name")
    has_phone = context.user_data.get("customer_phone")
    has_address = context.user_data.get("customer_address")

    if has_name and has_phone and has_address:
        return mostrar_pregunta_base(update, context, edit=False)
    else:
        update.message.reply_text(
            f"Lista registrada ({total} unidad(es) en total).\n\n"
            "Ahora escribe el nombre del cliente:"
        )
        return PEDIDO_NOMBRE


def mostrar_pregunta_base(query_or_update, context, edit=False):
    """Muestra pregunta de si requiere base."""
    keyboard = [
        [InlineKeyboardButton("Si, requiere base", callback_data="pedido_base_si")],
        [InlineKeyboardButton("No requiere base", callback_data="pedido_base_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    texto = (
        "BASE REQUERIDA\n\n"
        "El repartidor debe pagar/adelantar dinero al recoger el pedido?"
    )

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(texto, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)

    return PEDIDO_REQUIERE_BASE


def pedido_requiere_base_callback(update, context):
    """Maneja la respuesta de si requiere base."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pedido_base_no":
        context.user_data["requires_cash"] = False
        context.user_data["cash_required_amount"] = 0
        # Calcular cotizacion y mostrar confirmacion
        return calcular_cotizacion_y_confirmar(query, context, edit=True)

    elif data == "pedido_base_si":
        context.user_data["requires_cash"] = True
        # Mostrar opciones de monto
        keyboard = [
            [
                InlineKeyboardButton("$5.000", callback_data="pedido_base_5000"),
                InlineKeyboardButton("$10.000", callback_data="pedido_base_10000"),
            ],
            [
                InlineKeyboardButton("$20.000", callback_data="pedido_base_20000"),
                InlineKeyboardButton("$50.000", callback_data="pedido_base_50000"),
            ],
            [InlineKeyboardButton("Otro valor", callback_data="pedido_base_otro")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            "VALOR DE BASE\n\n"
            "Cuanto debe adelantar el repartidor?",
            reply_markup=reply_markup
        )
        return PEDIDO_VALOR_BASE

    return PEDIDO_REQUIERE_BASE


def pedido_valor_base_callback(update, context):
    """Maneja la seleccion del valor de base."""
    query = update.callback_query
    query.answer()
    data = query.data

    valores_map = {
        "pedido_base_5000": 5000,
        "pedido_base_10000": 10000,
        "pedido_base_20000": 20000,
        "pedido_base_50000": 50000,
    }

    if data in valores_map:
        context.user_data["cash_required_amount"] = valores_map[data]
        return calcular_cotizacion_y_confirmar(query, context, edit=True)

    elif data == "pedido_base_otro":
        query.edit_message_text(
            "Escribe el valor de la base (solo numeros):"
        )
        return PEDIDO_VALOR_BASE

    return PEDIDO_VALOR_BASE


def pedido_valor_base_texto(update, context):
    """Maneja el valor de base ingresado por texto."""
    texto = update.message.text.strip().replace(".", "").replace(",", "")
    try:
        valor = int(texto)
        if valor <= 0:
            raise ValueError("Valor debe ser mayor a 0")
        context.user_data["cash_required_amount"] = valor
        return calcular_cotizacion_y_confirmar(update, context, edit=False)
    except ValueError:
        update.message.reply_text(
            "Valor invalido. Escribe solo numeros (ej: 15000):"
        )
        return PEDIDO_VALOR_BASE


def mostrar_error_cotizacion(query_or_update, context, mensaje, edit=False):
    """Muestra error de cotizacion con botones Reintentar/Cancelar."""
    keyboard = [
        [InlineKeyboardButton("Reintentar cotizacion", callback_data="pedido_retry_quote")],
        [InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(mensaje, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(mensaje, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(mensaje, reply_markup=reply_markup)

    return PEDIDO_CONFIRMACION


def calcular_cotizacion_y_confirmar(query_or_update, context, edit=False):
    """
    Calcula distancia con estrategia economica en 3 capas y muestra resumen.
    Capa 1: Cache de distancias previas (gratis)
    Capa 2: Haversine local (gratis, siempre disponible)
    Capa 3: Google API (solo si hay cuota)
    """
    ally_id = context.user_data.get("ally_id")
    customer_address = context.user_data.get("customer_address", "")
    customer_city = context.user_data.get("customer_city", "")

    # Obtener coords del cliente (si se capturaron)
    dropoff_lat = context.user_data.get("dropoff_lat")
    dropoff_lng = context.user_data.get("dropoff_lng")

    # Usar pickup seleccionado por el usuario (del selector de pickup)
    pickup_text = context.user_data.get("pickup_address")
    pickup_city = context.user_data.get("pickup_city", "")
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")

    # Si no hay pickup en user_data, usar default del aliado (fallback)
    if not pickup_text and ally_id:
        default_location = get_default_ally_location(ally_id)
        if default_location:
            pickup_text = default_location.get("address")
            pickup_city = default_location.get("city") or ""
            pickup_lat = default_location.get("lat")
            pickup_lng = default_location.get("lng")

    if not pickup_text:
        return mostrar_error_cotizacion(
            query_or_update, context,
            "No tienes una direccion base configurada.\n\n"
            "Configura tu punto de recogida antes de crear pedidos.",
            edit=edit
        )

    # Guardar coords de pickup para el pedido
    context.user_data["pickup_lat"] = pickup_lat
    context.user_data["pickup_lng"] = pickup_lng

    # Intentar cotizar por coordenadas (usa estrategia en 3 capas: cache -> haversine -> google)
    cotizacion = None
    if pickup_lat and pickup_lng and dropoff_lat and dropoff_lng:
        cotizacion = quote_order_by_coords(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)

    # Si no hay coords, usar texto como fallback (requiere Google API)
    if not cotizacion or not cotizacion.get("success"):
        # Determinar ciudad efectiva
        effective_city = pickup_city or "Pereira"
        delivery_city = customer_city or effective_city

        # Construir direcciones completas
        origin = pickup_text
        if effective_city.lower() not in pickup_text.lower():
            origin = f"{pickup_text}, {effective_city}, Colombia"
        elif "colombia" not in pickup_text.lower():
            origin = f"{pickup_text}, Colombia"

        destination = customer_address
        if delivery_city.lower() not in customer_address.lower():
            destination = f"{customer_address}, {delivery_city}, Colombia"
        elif "colombia" not in customer_address.lower():
            destination = f"{customer_address}, Colombia"

        city_hint = f"{effective_city}, Colombia"
        cotizacion = quote_order_by_addresses(origin, destination, city_hint)

    # Verificar si fallo
    if not cotizacion.get("success"):
        return mostrar_error_cotizacion(
            query_or_update, context,
            "No se pudo calcular la distancia automaticamente.\n\n"
            "Verifica que la API este activa y vuelve a intentar.",
            edit=edit
        )

    # Guardar datos de cotizacion
    context.user_data["quote_distance_km"] = cotizacion["distance_km"]
    base_price = cotizacion["price"]

    # Si es servicio de Compras, calcular recargo por productos
    buy_surcharge = 0
    if context.user_data.get("service_type") == "Compras":
        n_products = context.user_data.get("buy_products_count", 0)
        buy_surcharge = calc_buy_products_surcharge(n_products)
        context.user_data["buy_surcharge"] = buy_surcharge

    context.user_data["quote_price"] = base_price + buy_surcharge
    context.user_data["quote_source"] = cotizacion.get("quote_source", "text")
    context.user_data["distance_source"] = cotizacion.get("distance_source", "")

    # Mostrar resumen con botones de confirmacion
    keyboard = [
        [InlineKeyboardButton("Confirmar pedido", callback_data="pedido_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    # Agregar nota sobre precision y fuente de distancia
    dist_source = cotizacion.get("distance_source", "")
    if "google" in dist_source:
        resumen += "\n(Distancia por ruta - Google Maps)"
    elif "haversine" in dist_source:
        resumen += "\n(Distancia estimada - calculo local)"
    elif "cache" in dist_source:
        resumen += "\n(Distancia desde cache)"
    elif context.user_data.get("quote_source") == "coords":
        resumen += "\n(Cotizacion precisa por ubicacion)"
    else:
        resumen += "\n(Cotizacion estimada por direccion)"

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(resumen, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(resumen, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(resumen, reply_markup=reply_markup)

    return PEDIDO_CONFIRMACION


def pedido_retry_quote_callback(update, context):
    """Reintenta calcular la cotizacion."""
    query = update.callback_query
    query.answer()
    return calcular_cotizacion_y_confirmar(query, context, edit=True)


def pedido_tipo_servicio(update, context):
    """Fallback: redirige a botones si el usuario escribe texto."""
    # Simplemente mostrar botones sin mensaje de error
    return mostrar_selector_tipo_servicio(update, context, edit=False)


def pedido_nombre_cliente(update, context):
    context.user_data["customer_name"] = update.message.text.strip()
    update.message.reply_text("Ahora escribe el numero de telefono del cliente.")
    return PEDIDO_TELEFONO


def pedido_telefono_cliente(update, context):
    context.user_data["customer_phone"] = update.message.text.strip()
    # Si viene del cotizador, la ubicacion ya esta capturada
    if context.user_data.get("cotizador_prefill_dropoff"):
        update.message.reply_text(
            "Ubicacion guardada de la cotizacion.\n\n"
            "Escribe los detalles de la direccion del cliente:\n"
            "barrio, conjunto, torre, apto, referencias."
        )
        return PEDIDO_DIRECCION

    # Solo reutilizar datos de ubicacion si es cliente recurrente (no cliente nuevo)
    if not context.user_data.get("is_new_customer"):
        customer_id = context.user_data.get("customer_id")
        customer_address = context.user_data.get("customer_address")
        dropoff_lat = context.user_data.get("dropoff_lat")
        dropoff_lng = context.user_data.get("dropoff_lng")
        if customer_id and customer_address and (dropoff_lat is None or dropoff_lng is None):
            address_id = context.user_data.get("customer_address_id")
            if address_id:
                addr = get_customer_address_by_id(address_id, customer_id)
                if addr:
                    context.user_data["dropoff_lat"] = addr.get("lat")
                    context.user_data["dropoff_lng"] = addr.get("lng")
                    dropoff_lat = context.user_data.get("dropoff_lat")
                    dropoff_lng = context.user_data.get("dropoff_lng")

        if customer_id and customer_address and dropoff_lat is not None and dropoff_lng is not None:
            update.message.reply_text("Datos del cliente guardados. Continuamos con el pedido.")
            return mostrar_selector_pickup(update, context, edit=False)

    # Preguntar por ubicación (obligatoria)
    update.message.reply_text(
        "UBICACION (obligatoria)\n\n"
        "Envia la ubicacion (PIN de Telegram), "
        "pega el enlace (Google Maps/WhatsApp) "
        "o escribe coordenadas (lat,lng).\n\n"
        "No se puede continuar sin una ubicacion valida."
    )
    return PEDIDO_UBICACION


def _mostrar_confirmacion_geocode(message, context, geo, original_text, cb_si, cb_no):
    """Muestra el primer candidato de geocoding con pin, link de Maps y botones de confirmacion.
    geo: dict con lat, lng, formatted_address, place_id.
    original_text: texto original del usuario (para carga perezosa del siguiente candidato)."""
    lat = geo["lat"]
    lng = geo["lng"]
    formatted_address = geo.get("formatted_address", "")
    _pid = geo.get("place_id") or f"{lat},{lng}"
    context.user_data["pending_geo_lat"] = lat
    context.user_data["pending_geo_lng"] = lng
    context.user_data["pending_geo_text"] = original_text
    context.user_data["pending_geo_seen"] = [_pid]
    message.reply_location(latitude=lat, longitude=lng)
    maps_link = f"https://maps.google.com/?q={lat},{lng}"
    keyboard = [[
        InlineKeyboardButton("Si, usar esta ubicacion", callback_data=cb_si),
        InlineKeyboardButton("No, esta no es", callback_data=cb_no),
    ]]
    message.reply_text(
        f"Encontre esta ubicacion:\n\n{formatted_address}\n\n"
        f"Ver en mapa: {maps_link}\n\n"
        "Es correcta?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def _geo_siguiente_o_gps(query, context, cb_si, cb_no, estado):
    """Busca el siguiente candidato de geocoding (carga perezosa) o pide GPS si no hay mas."""
    original_text = context.user_data.get("pending_geo_text", "")
    seen = context.user_data.get("pending_geo_seen", [])
    next_geo = resolve_location_next(original_text, seen) if original_text else None
    if next_geo:
        _pid = next_geo.get("place_id") or f"{next_geo['lat']},{next_geo['lng']}"
        seen.append(_pid)
        context.user_data["pending_geo_seen"] = seen
        context.user_data["pending_geo_lat"] = next_geo["lat"]
        context.user_data["pending_geo_lng"] = next_geo["lng"]
        lat = next_geo["lat"]
        lng = next_geo["lng"]
        maps_link = f"https://maps.google.com/?q={lat},{lng}"
        keyboard = [[
            InlineKeyboardButton("Si, usar esta ubicacion", callback_data=cb_si),
            InlineKeyboardButton("No, esta no es", callback_data=cb_no),
        ]]
        query.edit_message_text("Buscando otra opcion...")
        query.message.reply_location(latitude=lat, longitude=lng)
        query.message.reply_text(
            f"Otra opcion:\n\n{next_geo.get('formatted_address', '')}\n\n"
            f"Ver en mapa: {maps_link}\n\nEs correcta?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        context.user_data.pop("pending_geo_lat", None)
        context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        query.edit_message_text(
            "No encontre mas opciones. Envia la ubicacion de otra forma:\n"
            "- Un PIN de ubicacion de Telegram\n"
            "- Un link de Google Maps con coordenadas\n"
            "- Coordenadas directas (ej: 4.81,-75.69)"
        )
    return estado


def pedido_ubicacion_handler(update, context):
    """Maneja texto de ubicación (link o coords) con cache + Google place_id only."""
    texto = update.message.text.strip()

    # Normalizar: tomar primer URL si hay varios tokens
    raw_link = texto
    if "http" in texto:
        raw_link = next((t for t in texto.split() if t.startswith("http")), texto)

    # 1) Consultar cache
    cached = get_link_cache(raw_link)
    if cached and cached.get("lat") is not None and cached.get("lng") is not None:
        context.user_data["dropoff_lat"] = cached["lat"]
        context.user_data["dropoff_lng"] = cached["lng"]
        context.user_data["customer_location_link"] = raw_link
        update.message.reply_text(
            "Ubicacion guardada (desde cache).\n\n"
            "Ahora escribe los detalles de la direccion:\n"
            "barrio, conjunto, torre, apto, referencias."
        )
        return PEDIDO_DIRECCION

    # 2) Intentar expandir link corto si aplica
    expanded = expand_short_url(raw_link) or raw_link

    # 3) Extraer coordenadas del texto/URL con regex
    coords = extract_lat_lng_from_text(expanded)
    if coords:
        context.user_data["dropoff_lat"] = coords[0]
        context.user_data["dropoff_lng"] = coords[1]
        context.user_data["customer_location_link"] = raw_link
        upsert_link_cache(raw_link, expanded, coords[0], coords[1], provider="regex")
        update.message.reply_text(
            "Ubicacion guardada.\n\n"
            "Ahora escribe los detalles de la direccion:\n"
            "barrio, conjunto, torre, apto, referencias."
        )
        return PEDIDO_DIRECCION

    # 4) Fallback: Google Places API SOLO si hay place_id en URL
    place_id = extract_place_id_from_url(expanded)
    if place_id and can_call_google_today():
        google_result = google_place_details(place_id)
        if google_result and google_result.get("lat") and google_result.get("lng"):
            context.user_data["dropoff_lat"] = google_result["lat"]
            context.user_data["dropoff_lng"] = google_result["lng"]
            context.user_data["customer_location_link"] = raw_link
            upsert_link_cache(
                raw_link, expanded,
                google_result["lat"], google_result["lng"],
                google_result.get("formatted_address"),
                google_result.get("provider"),
                google_result.get("place_id")
            )
            update.message.reply_text(
                "Ubicacion guardada (via Google).\n\n"
                "Ahora escribe los detalles de la direccion:\n"
                "barrio, conjunto, torre, apto, referencias."
            )
            return PEDIDO_DIRECCION

    # 5) Geocoding: si el texto no es URL, intentar como direccion escrita
    if "http" not in texto:
        geo = resolve_location(texto)
        if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
            _mostrar_confirmacion_geocode(
                update.message, context,
                geo, texto,
                "pedido_geo_si", "pedido_geo_no",
            )
            return PEDIDO_UBICACION

    # 6) No se pudo resolver: la ubicacion es obligatoria
    es_link_corto_google = "maps.app.goo.gl" in raw_link or "goo.gl/maps" in raw_link

    if es_link_corto_google:
        keyboard = [[InlineKeyboardButton(
            "📋 Copiar mensaje para enviar al cliente",
            callback_data="ubicacion_copiar_msg_cliente"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "⚠️ Ese enlace no incluye coordenadas exactas.\n\n"
            "👉 Pídele al cliente una de estas opciones:\n"
            "• En WhatsApp: 📎 → Ubicación → Enviar ubicación actual\n"
            "• En Google Maps: tocar el punto azul → Compartir → copiar el link largo\n\n"
            "Cuando la tengas, envíala en este chat para continuar.",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            "No pude extraer coordenadas de ese texto.\n\n"
            "Envia una ubicacion valida para continuar.\n"
            "Tip: comparte PIN de Telegram, link de Maps con coordenadas o lat,lng."
        )
    return PEDIDO_UBICACION


def pedido_ubicacion_location_handler(update, context):
    """Maneja ubicacion nativa de Telegram (PIN) enviada por el usuario."""
    message = update.message or update.edited_message
    if not message or not message.location:
        return PEDIDO_UBICACION

    loc = message.location
    context.user_data["dropoff_lat"] = loc.latitude
    context.user_data["dropoff_lng"] = loc.longitude
    message.reply_text(
        "Ubicacion guardada.\n\n"
        "Ahora escribe los detalles de la direccion:\n"
        "barrio, conjunto, torre, apto, referencias."
    )
    return PEDIDO_DIRECCION


def pedido_geo_ubicacion_callback(update, context):
    """Maneja confirmacion de geocoding en el flujo de pedido."""
    query = update.callback_query
    query.answer()

    if query.data == "pedido_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return PEDIDO_UBICACION
        context.user_data["dropoff_lat"] = lat
        context.user_data["dropoff_lng"] = lng
        query.edit_message_text(
            "Ubicacion confirmada.\n\n"
            "Ahora escribe los detalles de la direccion:\n"
            "barrio, conjunto, torre, apto, referencias."
        )
        return PEDIDO_DIRECCION
    else:  # pedido_geo_no
        return _geo_siguiente_o_gps(query, context, "pedido_geo_si", "pedido_geo_no", PEDIDO_UBICACION)


def pedido_ubicacion_copiar_msg_callback(update, context):
    """Envía mensaje listo para copiar y enviar al cliente."""
    query = update.callback_query
    query.answer()
    # Enviar mensaje listo para copiar (texto plano)
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "📋 Copia y envía este mensaje al cliente:\n\n"
            "Hola 👋 ¿me puedes enviar tu ubicación por WhatsApp "
            "(📍Enviar ubicación actual) o un link largo de Google Maps? "
            "Es para registrar tu dirección rápido. Gracias 🙏"
        )
    )
    return PEDIDO_UBICACION


def pedido_direccion_cliente(update, context):
    context.user_data["customer_address"] = update.message.text.strip()

    # Si hay cliente existente (recurrente), preguntar si guardar direccion
    customer_id = context.user_data.get("customer_id")
    if customer_id and not context.user_data.get("is_new_customer"):
        keyboard = [
            [InlineKeyboardButton("Si, guardar", callback_data="guardar_dir_cliente_si")],
            [InlineKeyboardButton("No, solo usar esta vez", callback_data="guardar_dir_cliente_no")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "Deseas guardar esta direccion para futuros pedidos?",
            reply_markup=reply_markup
        )
        return PEDIDO_SELECCIONAR_DIRECCION

    # Cliente nuevo o sin guardar - continuar al pickup
    return mostrar_selector_pickup(update, context, edit=False)


# ---------- PICKUP SELECTOR (PUNTO DE RECOGIDA) ----------

def mostrar_selector_pickup(query_or_update, context, edit=False):
    """Muestra selector de punto de recogida con botones.

    Args:
        query_or_update: CallbackQuery o Update
        context: Context del bot
        edit: Si True, edita el mensaje existente
    """
    ally = context.user_data.get("ally")
    ally_id = ally["id"] if ally else None

    keyboard = []
    if ally_id:
        locations = get_ally_locations(ally_id)
        default_loc = next((l for l in locations if l.get("is_default")), None)

        if default_loc:
            label = (default_loc.get("label") or "Base")[:20]
            address = (default_loc.get("address") or "")[:35]
            sin_gps = " (sin GPS)" if default_loc.get("lat") is None else ""
            keyboard.append([InlineKeyboardButton(
                "Usar base: {} - {}{}".format(label, address, sin_gps),
                callback_data="pickup_select_base"
            )])

        otros = [l for l in locations if not l.get("is_default")]
        if otros or (locations and not default_loc):
            n = len(locations)
            keyboard.append([InlineKeyboardButton(
                "Elegir otra ({})".format(n),
                callback_data="pickup_select_lista"
            )])

    keyboard.append([InlineKeyboardButton("Agregar nueva direccion", callback_data="pickup_select_nueva")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    texto = "PUNTO DE RECOGIDA\n\nDonde se recoge el pedido?"

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(texto, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)

    return PEDIDO_PICKUP_SELECTOR


def pedido_pickup_callback(update, context):
    """Maneja la seleccion del tipo de pickup."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally = context.user_data.get("ally")
    if not ally:
        query.edit_message_text("Error: no se encontro informacion del aliado. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END

    ally_id = ally["id"]
    if data != "pickup_select_fixbasecoords":
        context.user_data.pop("pickup_fix_default_loc_id", None)

    if data == "pickup_select_base":
        # Usar direccion base del aliado
        default_loc = get_default_ally_location(ally_id)
        if not default_loc:
            query.edit_message_text(
                "No tienes una direccion base configurada.\n"
                "Puedes agregar una nueva o contactar soporte."
            )
            return mostrar_selector_pickup(query, context, edit=False)

        default_lat = default_loc.get("lat")
        default_lng = default_loc.get("lng")
        if default_lat is None or default_lng is None:
            keyboard = [
                [InlineKeyboardButton("Enviar PIN ahora", callback_data="pickup_select_fixbasecoords")],
                [InlineKeyboardButton("Elegir otra recogida", callback_data="pickup_select_lista")],
                [InlineKeyboardButton("Nueva direccion", callback_data="pickup_select_nueva")],
            ]
            query.edit_message_text(
                "Tu direccion principal no tiene coordenadas.\n"
                "Para continuar, debes enviar un PIN de ubicacion de recogida.",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return PEDIDO_PICKUP_SELECTOR

        # Guardar pickup en user_data
        context.user_data["pickup_location"] = default_loc
        context.user_data["pickup_label"] = default_loc.get("label") or "Base"
        context.user_data["pickup_address"] = default_loc.get("address", "")
        context.user_data["pickup_city"] = default_loc.get("city", "")
        context.user_data["pickup_barrio"] = default_loc.get("barrio", "")
        context.user_data["pickup_lat"] = default_loc.get("lat")
        context.user_data["pickup_lng"] = default_loc.get("lng")

        # Continuar al siguiente paso
        return continuar_despues_pickup(query, context, edit=True)

    elif data == "pickup_select_lista":
        # Mostrar lista de direcciones guardadas
        return mostrar_lista_pickups(query, context)

    elif data == "pickup_select_nueva":
        # Pedir nueva direccion
        query.edit_message_text(
            "NUEVA DIRECCION DE RECOGIDA\n\n"
            "Envia la ubicacion (PIN de Telegram), "
            "pega el enlace (Google Maps/WhatsApp) "
            "o escribe coordenadas (lat,lng).\n\n"
            "La ubicacion es obligatoria para continuar."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    elif data == "pickup_select_fixbasecoords":
        default_loc = get_default_ally_location(ally_id)
        if not default_loc:
            query.edit_message_text(
                "No se encontro tu direccion principal.\n"
                "Elige otra direccion de recogida."
            )
            return mostrar_selector_pickup(query, context, edit=False)

        context.user_data["pickup_fix_default_loc_id"] = default_loc["id"]
        query.edit_message_text(
            "Envia un PIN de ubicacion de Telegram, link de Google Maps o coordenadas (lat,lng)\n"
            "para actualizar la direccion principal y continuar."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    else:
        query.edit_message_text("Opcion no valida. Usa /nuevo_pedido de nuevo.")
        return ConversationHandler.END


# =============================================================
# PANEL DE GESTIÓN DE UBICACIONES DEL ALIADO ("Mis ubicaciones")
# =============================================================

def _ally_locs_mostrar_lista(query_or_update, ally_id, edit=False, aviso=None):
    """Muestra el panel de ubicaciones del aliado con botones de gestión."""
    locations = get_ally_locations(ally_id)

    keyboard = []
    if locations:
        for loc in locations:
            label = (loc.get("label") or "Sin nombre")[:25]
            tags = []
            if loc.get("is_default"):
                tags.append("BASE")
            if loc.get("is_frequent"):
                tags.append("FRECUENTE")
            tag_str = " [{}]".format(", ".join(tags)) if tags else ""
            sin_gps = " (sin GPS)" if loc.get("lat") is None else ""
            keyboard.append([InlineKeyboardButton(
                "{}{}{}".format(label, tag_str, sin_gps),
                callback_data="ally_locs_ver_{}".format(loc["id"])
            )])
        keyboard.append([InlineKeyboardButton("+ Agregar nueva", callback_data="ally_locs_add")])
        texto_base = "MIS UBICACIONES DE RECOGIDA\n\nSelecciona una para ver opciones:"
    else:
        keyboard.append([InlineKeyboardButton("+ Agregar primera ubicacion", callback_data="ally_locs_add")])
        texto_base = "MIS UBICACIONES DE RECOGIDA\n\nAun no tienes ubicaciones guardadas."

    if aviso:
        texto = "{}\n\n{}".format(aviso, texto_base)
    else:
        texto = texto_base

    reply_markup = InlineKeyboardMarkup(keyboard)

    if edit and hasattr(query_or_update, 'edit_message_text'):
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)
    elif hasattr(query_or_update, 'message') and query_or_update.message:
        query_or_update.message.reply_text(texto, reply_markup=reply_markup)
    else:
        query_or_update.edit_message_text(texto, reply_markup=reply_markup)

    return ALLY_LOCS_MENU


def mis_ubicaciones_start(update, context):
    """Muestra el panel de gestión de ubicaciones del aliado."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)
    if not ally or ally.get("status") != "APPROVED":
        update.message.reply_text(
            "No tienes un perfil de aliado activo. Contacta al administrador."
        )
        return ConversationHandler.END
    context.user_data["ally_locs_ally_id"] = ally["id"]
    return _ally_locs_mostrar_lista(update, ally["id"], edit=False)


def ally_locs_menu_callback(update, context):
    """Maneja todas las acciones del panel de ubicaciones del aliado."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ally_locs_ally_id")

    if not ally_id:
        query.edit_message_text("Sesion expirada. Regresa al menu e intenta de nuevo.")
        return ConversationHandler.END

    if data == "ally_locs_lista" or data == "ally_locs_del_cancel":
        return _ally_locs_mostrar_lista(query, ally_id, edit=True)

    if data.startswith("ally_locs_ver_"):
        try:
            loc_id = int(data.split("ally_locs_ver_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)

        loc = get_ally_location_by_id(loc_id, ally_id)
        if not loc:
            return _ally_locs_mostrar_lista(query, ally_id, edit=True, aviso="Ubicacion no encontrada.")

        label = loc.get("label") or "Sin nombre"
        address = loc.get("address") or "-"
        gps = "{}, {}".format(round(loc["lat"], 5), round(loc["lng"], 5)) if loc.get("lat") else "Sin GPS"
        usos = loc.get("use_count") or 0
        is_base = bool(loc.get("is_default"))

        detalle = (
            "UBICACION: {}\n\n"
            "Direccion: {}\n"
            "GPS: {}\n"
            "Usos en pedidos: {}"
        ).format(label, address, gps, usos)

        keyboard = []
        if not is_base:
            keyboard.append([InlineKeyboardButton(
                "Marcar como base",
                callback_data="ally_locs_base_{}".format(loc_id)
            )])
        keyboard.append([InlineKeyboardButton(
            "Eliminar",
            callback_data="ally_locs_del_{}".format(loc_id)
        )])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="ally_locs_lista")])

        query.edit_message_text(detalle, reply_markup=InlineKeyboardMarkup(keyboard))
        return ALLY_LOCS_MENU

    if data.startswith("ally_locs_base_"):
        try:
            loc_id = int(data.split("ally_locs_base_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)
        set_default_ally_location(loc_id, ally_id)
        return _ally_locs_mostrar_lista(query, ally_id, edit=True, aviso="Base actualizada.")

    if data.startswith("ally_locs_del_confirm_"):
        try:
            loc_id = int(data.split("ally_locs_del_confirm_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)
        delete_ally_location(loc_id, ally_id)
        return _ally_locs_mostrar_lista(query, ally_id, edit=True, aviso="Ubicacion eliminada.")

    if data.startswith("ally_locs_del_"):
        try:
            loc_id = int(data.split("ally_locs_del_")[1])
        except (ValueError, IndexError):
            return _ally_locs_mostrar_lista(query, ally_id, edit=True)
        loc = get_ally_location_by_id(loc_id, ally_id)
        label = loc.get("label") or "esta ubicacion" if loc else "esta ubicacion"
        keyboard = [
            [InlineKeyboardButton(
                "Confirmar eliminacion",
                callback_data="ally_locs_del_confirm_{}".format(loc_id)
            )],
            [InlineKeyboardButton("Cancelar", callback_data="ally_locs_del_cancel")],
        ]
        query.edit_message_text(
            "Eliminar '{}'?\n\nEsta accion no se puede deshacer.".format(label),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ALLY_LOCS_MENU

    if data == "ally_locs_add":
        query.edit_message_text(
            "AGREGAR UBICACION\n\n"
            "Envia la ubicacion del punto de recogida:\n"
            "- Comparte tu ubicacion (PIN de Telegram)\n"
            "- Pega un link de Google Maps\n"
            "- Escribe coordenadas (ej: 4.81,-75.69)"
        )
        return ALLY_LOCS_ADD_COORDS

    return ALLY_LOCS_MENU


def ally_locs_add_coords(update, context):
    """Captura la ubicacion (texto/link/coords) de la nueva direccion del aliado."""
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
        return ALLY_LOCS_ADD_COORDS

    context.user_data["ally_locs_new_lat"] = loc["lat"]
    context.user_data["ally_locs_new_lng"] = loc["lng"]
    dir_encontrada = ""
    if loc.get("method") == "geocode" and loc.get("formatted_address"):
        dir_encontrada = f"Ubicacion encontrada: {loc['formatted_address']}\n\n"
    update.message.reply_text(
        f"{dir_encontrada}Dale un nombre a este punto de recogida:\n"
        "(ej: Tienda centro, Bodega norte, Casa)"
    )
    return ALLY_LOCS_ADD_LABEL


def ally_locs_add_coords_location(update, context):
    """Handler para PIN nativo de Telegram al agregar ubicacion del aliado."""
    return ally_locs_add_coords(update, context)


def ally_locs_add_label(update, context):
    """Guarda la nueva ubicacion del aliado con la etiqueta ingresada."""
    texto = (update.message.text or "").strip()
    if not texto:
        update.message.reply_text("El nombre no puede estar vacio. Escribe un nombre para la ubicacion:")
        return ALLY_LOCS_ADD_LABEL

    ally_id = context.user_data.get("ally_locs_ally_id")
    lat = context.user_data.get("ally_locs_new_lat")
    lng = context.user_data.get("ally_locs_new_lng")

    if not ally_id or lat is None:
        update.message.reply_text("Error: datos perdidos. Regresa al menu de ubicaciones.")
        return ConversationHandler.END

    label = texto[:40]
    context.user_data["ally_locs_new_label"] = label
    update.message.reply_text("Escribe la ciudad del punto de recogida:")
    return ALLY_LOCS_ADD_CITY


def ally_locs_add_city(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad del punto de recogida:",
        "ally_locs_new_city",
        ALLY_LOCS_ADD_CITY,
        ALLY_LOCS_ADD_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector del punto de recogida:",
        options_hint="",
        set_back_step=False,
    )


def ally_locs_add_barrio(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector del punto de recogida:",
        "ally_locs_new_barrio",
        ALLY_LOCS_ADD_BARRIO,
        ALLY_LOCS_MENU,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == ALLY_LOCS_ADD_BARRIO:
        return ok_state
    barrio = context.user_data.get("ally_locs_new_barrio", "")

    ally_id = context.user_data.get("ally_locs_ally_id")
    lat = context.user_data.get("ally_locs_new_lat")
    lng = context.user_data.get("ally_locs_new_lng")
    label = context.user_data.get("ally_locs_new_label", "")
    city = context.user_data.get("ally_locs_new_city", "")

    if not ally_id or lat is None:
        update.message.reply_text("Error: datos perdidos. Regresa al menu de ubicaciones.")
        return ConversationHandler.END

    new_loc_id = create_ally_location(
        ally_id=ally_id,
        label=label,
        address=label,
        city=city,
        barrio=barrio,
        lat=lat,
        lng=lng,
    )

    for key in [
        "ally_locs_new_lat",
        "ally_locs_new_lng",
        "ally_locs_new_label",
        "ally_locs_new_city",
        "ally_locs_new_barrio",
    ]:
        context.user_data.pop(key, None)

    keyboard = [
        [InlineKeyboardButton("Si, usar como base", callback_data="ally_locs_base_{}".format(new_loc_id))],
        [InlineKeyboardButton("No, solo guardarla", callback_data="ally_locs_lista")],
    ]
    update.message.reply_text(
        "Ubicacion '{}' guardada.\n\n"
        "Usar como direccion base (la que aparece primero al crear pedidos)?".format(label),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ALLY_LOCS_MENU


# =============================================================
# FIN PANEL GESTIÓN DE UBICACIONES
# =============================================================


def construir_etiqueta_pickup(loc):
    """Construye etiqueta para un pickup con info de uso."""
    label = loc.get("label") or loc.get("address", "Sin nombre")[:25]
    tags = []

    if loc.get("is_default"):
        tags.append("BASE")
    if loc.get("is_frequent"):
        tags.append("FRECUENTE")
    elif loc.get("use_count", 0) > 0:
        tags.append(f"x{loc['use_count']}")

    if tags:
        return f"{label} ({', '.join(tags)})"
    return label


def mostrar_lista_pickups(query, context):
    """Muestra lista de direcciones guardadas del aliado (max 8)."""
    ally = context.user_data.get("ally")
    if not ally:
        query.edit_message_text("Error: no se encontro informacion del aliado.")
        return ConversationHandler.END

    ally_id = ally["id"]
    locations = get_ally_locations(ally_id)  # Ya ordenadas por prioridad

    if not locations:
        query.edit_message_text(
            "No tienes direcciones guardadas.\n"
            "Agrega una nueva direccion."
        )
        return mostrar_selector_pickup(query, context, edit=False)

    # Botones directos sin submenú — un clic usa la dirección
    keyboard = []
    for loc in locations[:8]:
        label = (loc.get("label") or "Sin nombre")[:20]
        address = (loc.get("address") or "")[:28]
        tags = []
        if loc.get("is_default"):
            tags.append("BASE")
        if loc.get("is_frequent"):
            tags.append("FRECUENTE")
        elif loc.get("use_count", 0) > 0:
            tags.append("x{}".format(loc["use_count"]))
        tag_str = " [{}]".format(", ".join(tags)) if tags else ""
        sin_gps = " (sin GPS)" if loc.get("lat") is None else ""
        keyboard.append([InlineKeyboardButton(
            "{}: {}{}{}".format(label, address, tag_str, sin_gps),
            callback_data="pickup_list_usar_{}".format(loc["id"])
        )])

    keyboard.append([InlineKeyboardButton("Agregar nueva", callback_data="pickup_list_nueva")])
    keyboard.append([InlineKeyboardButton("Volver", callback_data="pickup_list_volver")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        "ELEGIR PUNTO DE RECOGIDA\n\n"
        "Selecciona una de tus direcciones:",
        reply_markup=reply_markup
    )
    return PEDIDO_PICKUP_LISTA


def pedido_pickup_lista_callback(update, context):
    """Maneja la seleccion de una direccion de la lista."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pickup_list_volver":
        return mostrar_selector_pickup(query, context, edit=True)

    if data == "pickup_list_nueva":
        query.edit_message_text(
            "NUEVA DIRECCION DE RECOGIDA\n\n"
            "Envia la ubicacion (PIN de Telegram), "
            "pega el enlace (Google Maps/WhatsApp) "
            "o escribe coordenadas (lat,lng).\n\n"
            "La ubicacion es obligatoria para continuar."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    if data.startswith("pickup_list_usar_"):
        try:
            loc_id = int(data.replace("pickup_list_usar_", ""))
        except ValueError:
            query.edit_message_text("Error: ID invalido.")
            return ConversationHandler.END

        ally = context.user_data.get("ally")
        if not ally:
            query.edit_message_text("Error: no se encontro informacion del aliado.")
            return ConversationHandler.END

        location = get_ally_location_by_id(loc_id, ally["id"])
        if not location:
            query.edit_message_text("Error: direccion no encontrada.")
            return mostrar_selector_pickup(query, context, edit=False)

        if location.get("lat") is None or location.get("lng") is None:
            query.answer("Esta direccion no tiene GPS. Selecciona otra o agrega una nueva.", show_alert=True)
            return mostrar_lista_pickups(query, context)

        context.user_data["pickup_location"] = location
        context.user_data["pickup_label"] = location.get("label") or "Recogida"
        context.user_data["pickup_address"] = location.get("address", "")
        context.user_data["pickup_city"] = location.get("city", "")
        context.user_data["pickup_barrio"] = location.get("barrio", "")
        context.user_data["pickup_lat"] = location.get("lat")
        context.user_data["pickup_lng"] = location.get("lng")

        return continuar_despues_pickup(query, context, edit=True)

    query.edit_message_text("Opcion no valida.")
    return ConversationHandler.END


def pedido_pickup_nueva_ubicacion_handler(update, context):
    """Maneja la captura de ubicacion para nueva direccion de recogida."""
    text = update.message.text.strip()
    fixing_default = bool(context.user_data.get("pickup_fix_default_loc_id"))

    if text.lower() == "omitir":
        update.message.reply_text(
            "No puedes omitir la ubicacion.\n"
            "Envia un PIN, link de Google Maps o coordenadas (lat,lng)."
        )
        return PEDIDO_PICKUP_NUEVA_UBICACION

    # Mismo pipeline de resolucion usado en cotizacion
    loc = resolve_location(text)
    if loc and loc.get("lat") is not None and loc.get("lng") is not None:
        if loc.get("method") == "geocode" and loc.get("formatted_address"):
            _mostrar_confirmacion_geocode(
                update.message, context,
                loc, text,
                "pickup_geo_si", "pickup_geo_no",
            )
            return PEDIDO_PICKUP_NUEVA_UBICACION

        lat, lng = loc["lat"], loc["lng"]
        if fixing_default:
            ally = context.user_data.get("ally")
            location_id = context.user_data.get("pickup_fix_default_loc_id")
            if not ally or not location_id:
                update.message.reply_text("No se pudo actualizar la direccion principal. Intenta /nuevo_pedido de nuevo.")
                return ConversationHandler.END

            update_ally_location_coords(location_id, lat, lng)
            context.user_data.pop("pickup_fix_default_loc_id", None)

            default_loc = get_default_ally_location(ally["id"])
            if not default_loc:
                update.message.reply_text("No se pudo cargar la direccion principal actualizada.")
                return ConversationHandler.END

            context.user_data["pickup_location"] = default_loc
            context.user_data["pickup_label"] = default_loc.get("label") or "Base"
            context.user_data["pickup_address"] = default_loc.get("address", "")
            context.user_data["pickup_city"] = default_loc.get("city", "")
            context.user_data["pickup_barrio"] = default_loc.get("barrio", "")
            context.user_data["pickup_lat"] = default_loc.get("lat")
            context.user_data["pickup_lng"] = default_loc.get("lng")

            update.message.reply_text("Ubicacion principal actualizada. Continuamos con el pedido.")
            return continuar_despues_pickup(update, context, edit=False)

        context.user_data["new_pickup_lat"] = lat
        context.user_data["new_pickup_lng"] = lng
        update.message.reply_text(
            f"Ubicacion capturada: {lat}, {lng}\n\n"
            "Ahora escribe los detalles de la direccion de recogida:\n"
            "direccion, barrio, referencias..."
        )
        return PEDIDO_PICKUP_NUEVA_DETALLES

    # No se pudo extraer - detectar si es link corto de Google
    es_link_corto_google = "maps.app.goo.gl" in text or "goo.gl/maps" in text

    if es_link_corto_google:
        keyboard = [[InlineKeyboardButton(
            "📋 Copiar mensaje para enviar al cliente",
            callback_data="pickup_copiar_msg_cliente"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "⚠️ Ese enlace no incluye coordenadas exactas.\n\n"
            "👉 Pidele al cliente una de estas opciones:\n"
            "• En WhatsApp: 📎 → Ubicacion → Enviar ubicacion actual\n"
            "• En Google Maps: tocar el punto azul → Compartir → copiar el link largo\n\n"
            "Cuando la tengas, enviala aqui para continuar.",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            "No se pudo extraer ubicacion valida.\n"
            "Envia un PIN, link de Google Maps o coordenadas (lat,lng)."
        )

    return PEDIDO_PICKUP_NUEVA_UBICACION


def pedido_pickup_geo_callback(update, context):
    """Maneja confirmacion de geocoding para nueva direccion de pickup en pedido."""
    query = update.callback_query
    query.answer()

    if query.data == "pickup_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Intenta /nuevo_pedido de nuevo.")
            return PEDIDO_PICKUP_NUEVA_UBICACION

        fixing_default = bool(context.user_data.get("pickup_fix_default_loc_id"))
        if fixing_default:
            ally = context.user_data.get("ally")
            location_id = context.user_data.get("pickup_fix_default_loc_id")
            if not ally or not location_id:
                query.edit_message_text("No se pudo actualizar la direccion principal. Intenta /nuevo_pedido de nuevo.")
                return ConversationHandler.END

            update_ally_location_coords(location_id, lat, lng)
            context.user_data.pop("pickup_fix_default_loc_id", None)

            default_loc = get_default_ally_location(ally["id"])
            if not default_loc:
                query.edit_message_text("No se pudo cargar la direccion principal actualizada.")
                return ConversationHandler.END

            context.user_data["pickup_location"] = default_loc
            context.user_data["pickup_label"] = default_loc.get("label") or "Base"
            context.user_data["pickup_address"] = default_loc.get("address", "")
            context.user_data["pickup_city"] = default_loc.get("city", "")
            context.user_data["pickup_lat"] = default_loc.get("lat")
            context.user_data["pickup_lng"] = default_loc.get("lng")

            query.edit_message_text("Ubicacion principal actualizada. Continuamos con el pedido.")
            return continuar_despues_pickup(query, context, edit=False)

        context.user_data["new_pickup_lat"] = lat
        context.user_data["new_pickup_lng"] = lng
        query.edit_message_text(
            f"Ubicacion capturada: {lat}, {lng}\n\n"
            "Ahora escribe la direccion de recogida (sin ciudad ni barrio):"
        )
        return PEDIDO_PICKUP_NUEVA_DETALLES

    return _geo_siguiente_o_gps(query, context, "pickup_geo_si", "pickup_geo_no", PEDIDO_PICKUP_NUEVA_UBICACION)


def pedido_pickup_nueva_ubicacion_location_handler(update, context):
    """Maneja ubicacion nativa de Telegram (PIN) para nueva direccion de recogida en pedido."""
    loc = update.message.location
    fixing_default = bool(context.user_data.get("pickup_fix_default_loc_id"))

    if fixing_default:
        ally = context.user_data.get("ally")
        location_id = context.user_data.get("pickup_fix_default_loc_id")
        if not ally or not location_id:
            update.message.reply_text("No se pudo actualizar la direccion principal. Intenta /nuevo_pedido de nuevo.")
            return ConversationHandler.END

        update_ally_location_coords(location_id, loc.latitude, loc.longitude)
        context.user_data.pop("pickup_fix_default_loc_id", None)

        default_loc = get_default_ally_location(ally["id"])
        if not default_loc:
            update.message.reply_text("No se pudo cargar la direccion principal actualizada.")
            return ConversationHandler.END

        context.user_data["pickup_location"] = default_loc
        context.user_data["pickup_label"] = default_loc.get("label") or "Base"
        context.user_data["pickup_address"] = default_loc.get("address", "")
        context.user_data["pickup_city"] = default_loc.get("city", "")
        context.user_data["pickup_barrio"] = default_loc.get("barrio", "")
        context.user_data["pickup_lat"] = default_loc.get("lat")
        context.user_data["pickup_lng"] = default_loc.get("lng")

        update.message.reply_text("Ubicacion principal actualizada. Continuamos con el pedido.")
        return continuar_despues_pickup(update, context, edit=False)

    context.user_data["new_pickup_lat"] = loc.latitude
    context.user_data["new_pickup_lng"] = loc.longitude
    update.message.reply_text(
        f"Ubicacion capturada: {loc.latitude}, {loc.longitude}\n\n"
        "Ahora escribe la direccion de recogida (sin ciudad ni barrio):"
    )
    return PEDIDO_PICKUP_NUEVA_DETALLES


def pickup_nueva_copiar_msg_callback(update, context):
    """Envia mensaje listo para copiar (flujo pickup nueva)."""
    query = update.callback_query
    query.answer()
    context.bot.send_message(
        chat_id=query.message.chat_id,
        text=(
            "📋 Copia y envia este mensaje al cliente:\n\n"
            "Hola 👋 ¿me puedes enviar tu ubicacion por WhatsApp "
            "(📍Enviar ubicacion actual) o un link largo de Google Maps? "
            "Es para registrar tu direccion rapido. Gracias 🙏"
        )
    )
    return PEDIDO_PICKUP_NUEVA_UBICACION


def pedido_pickup_nueva_detalles_handler(update, context):
    """Maneja la captura de detalles de nueva direccion de recogida."""
    text = update.message.text.strip()
    if not text:
        update.message.reply_text("Por favor escribe la direccion de recogida:")
        return PEDIDO_PICKUP_NUEVA_DETALLES

    context.user_data["new_pickup_address"] = text

    # Sugerir ciudad basada en la base del aliado (pero se pregunta siempre)
    ally = context.user_data.get("ally")
    default_city = "Pereira"
    if ally:
        default_loc = get_default_ally_location(ally["id"])
        if default_loc and default_loc.get("city"):
            default_city = default_loc["city"]

    update.message.reply_text(
        "Ciudad de la recogida (ej: {}).".format(default_city)
    )
    return PEDIDO_PICKUP_NUEVA_CIUDAD


def pedido_pickup_nueva_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la recogida:",
        "new_pickup_city",
        PEDIDO_PICKUP_NUEVA_CIUDAD,
        PEDIDO_PICKUP_NUEVA_BARRIO,
        flow=None,
        next_prompt="Barrio o sector de la recogida:",
        options_hint="",
        set_back_step=False,
    )


def pedido_pickup_nueva_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la recogida:",
        "new_pickup_barrio",
        PEDIDO_PICKUP_NUEVA_BARRIO,
        PEDIDO_PICKUP_GUARDAR,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == PEDIDO_PICKUP_NUEVA_BARRIO:
        return ok_state
    barrio = context.user_data.get("new_pickup_barrio", "")

    # Guardar pickup temporal
    context.user_data["pickup_label"] = "Nueva"
    context.user_data["pickup_address"] = context.user_data.get("new_pickup_address", "")
    context.user_data["pickup_city"] = context.user_data.get("new_pickup_city", "")
    context.user_data["pickup_barrio"] = barrio
    context.user_data["pickup_lat"] = context.user_data.get("new_pickup_lat")
    context.user_data["pickup_lng"] = context.user_data.get("new_pickup_lng")

    # Preguntar si quiere guardar la direccion
    keyboard = [
        [InlineKeyboardButton("Si, guardar", callback_data="pickup_guardar_si")],
        [InlineKeyboardButton("No, solo usar esta vez", callback_data="pickup_guardar_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Deseas guardar esta direccion para futuros pedidos?",
        reply_markup=reply_markup
    )
    return PEDIDO_PICKUP_GUARDAR


def pedido_pickup_guardar_callback(update, context):
    """Maneja la decision de guardar o no la nueva direccion."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally = context.user_data.get("ally")
    if not ally:
        query.edit_message_text("Error: no se encontro informacion del aliado.")
        return ConversationHandler.END

    if data == "pickup_guardar_si":
        # Guardar en BD
        new_loc_id = create_ally_location(
            ally_id=ally["id"],
            label=context.user_data.get("new_pickup_address", "")[:30],
            address=context.user_data.get("new_pickup_address", ""),
            city=context.user_data.get("new_pickup_city", "Pereira"),
            barrio=context.user_data.get("new_pickup_barrio", ""),
            phone="",
            is_default=False,
            lat=context.user_data.get("new_pickup_lat"),
            lng=context.user_data.get("new_pickup_lng"),
        )
        if new_loc_id:
            query.edit_message_text("Direccion guardada correctamente.")
        else:
            query.edit_message_text("No se pudo guardar, pero continuamos con el pedido.")

    else:
        query.edit_message_text("OK, usaremos esta direccion solo para este pedido.")

    # Continuar al siguiente paso
    return continuar_despues_pickup(query, context, edit=False)


def continuar_despues_pickup(query, context, edit=True):
    """Continua el flujo despues de seleccionar el pickup."""
    # Verificar si ya tenemos tipo de servicio
    if not context.user_data.get("service_type"):
        return mostrar_selector_tipo_servicio(query, context, edit=edit)

    # Ya tenemos tipo, preguntar por base
    return mostrar_pregunta_base(query, context, edit=edit)


def _fmt_pesos(amount: int) -> str:
    try:
        amount = int(amount or 0)
    except Exception:
        amount = 0
    return f"${amount:,}".replace(",", ".")


def _pedido_incentivo_keyboard(prefix: str = "pedido_inc_", order_id: int = None):
    """
    Botones de incentivo (pre y post oferta).
    - Pre: callback_data=pedido_inc_1000 / pedido_inc_otro
    - Post: callback_data=pedido_inc_{order_id}x{monto} / pedido_inc_otro_{order_id}
    """
    if order_id is None:
        return [
            [
                InlineKeyboardButton("+1000", callback_data=f"{prefix}1000"),
                InlineKeyboardButton("+1500", callback_data=f"{prefix}1500"),
            ],
            [
                InlineKeyboardButton("+2000", callback_data=f"{prefix}2000"),
                InlineKeyboardButton("+3000", callback_data=f"{prefix}3000"),
            ],
            [InlineKeyboardButton("Otro monto", callback_data=f"{prefix}otro")],
        ]

    return [
        [
            InlineKeyboardButton("+1000", callback_data=f"{prefix}{order_id}x1000"),
            InlineKeyboardButton("+1500", callback_data=f"{prefix}{order_id}x1500"),
        ],
        [
            InlineKeyboardButton("+2000", callback_data=f"{prefix}{order_id}x2000"),
            InlineKeyboardButton("+3000", callback_data=f"{prefix}{order_id}x3000"),
        ],
        [InlineKeyboardButton("Otro monto", callback_data=f"{prefix}otro_{order_id}")],
    ]


def _courier_earnings_group_by_date(rows: list) -> list:
    totals = {}
    for r in rows or []:
        date_key = (r.get("date_key") or "").strip()
        if not date_key:
            continue
        d = totals.setdefault(date_key, {"orders": 0, "gross": 0, "fee": 0, "net": 0})
        d["orders"] += 1
        d["gross"] += int(r.get("gross_amount") or 0)
        d["fee"] += int(r.get("platform_fee") or 0)
        d["net"] += int(r.get("net_amount") or 0)
    # Orden desc por fecha (YYYY-MM-DD)
    result = []
    for k in sorted(totals.keys(), reverse=True):
        row = totals[k]
        result.append({
            "date_key": k,
            "orders": row["orders"],
            "gross": row["gross"],
            "fee": row["fee"],
            "net": row["net"],
        })
    return result


def _courier_earnings_buttons(daily: list):
    keyboard = []
    for d in daily:
        date_key = d["date_key"]
        compact = date_key.replace("-", "")
        label = "{} ({} pedidos)".format(date_key, d["orders"])
        keyboard.append([InlineKeyboardButton(label, callback_data="courier_earn_{}".format(compact))])
    keyboard.append([InlineKeyboardButton("Actualizar", callback_data="courier_earn_refresh")])
    return InlineKeyboardMarkup(keyboard)


def courier_earnings_start(update, context):
    """Muestra resumen de ganancias del repartidor por día (según liquidaciones contables)."""
    telegram_id = update.effective_user.id
    ok, courier, rows, msg = courier_get_earnings_history(telegram_id, days=7)
    if not ok:
        update.message.reply_text(msg)
        return

    daily = _courier_earnings_group_by_date(rows)
    if not daily:
        update.message.reply_text("No hay ganancias registradas en los últimos 7 días.")
        return

    total_orders = sum(d["orders"] for d in daily)
    total_gross = sum(d["gross"] for d in daily)
    total_fee = sum(d["fee"] for d in daily)
    total_net = sum(d["net"] for d in daily)

    text = (
        "MIS GANANCIAS (ULTIMOS 7 DIAS)\n\n"
        "Pedidos entregados: {}\n"
        "Bruto: {}\n"
        "Fee plataforma cobrado: {}\n"
        "Neto estimado: {}\n\n"
        "Selecciona un día para ver el detalle:"
    ).format(total_orders, _fmt_pesos(total_gross), _fmt_pesos(total_fee), _fmt_pesos(total_net))

    update.message.reply_text(text, reply_markup=_courier_earnings_buttons(daily))


def courier_earnings_callback(update, context):
    """Callback para ver resumen/detalle de ganancias del repartidor."""
    query = update.callback_query
    query.answer()
    data = query.data or ""
    telegram_id = update.effective_user.id

    if data == "courier_earn_refresh" or data == "courier_earn_back":
        ok, courier, rows, msg = courier_get_earnings_history(telegram_id, days=7)
        if not ok:
            query.edit_message_text(msg)
            return
        daily = _courier_earnings_group_by_date(rows)
        if not daily:
            query.edit_message_text("No hay ganancias registradas en los últimos 7 días.")
            return
        total_orders = sum(d["orders"] for d in daily)
        total_gross = sum(d["gross"] for d in daily)
        total_fee = sum(d["fee"] for d in daily)
        total_net = sum(d["net"] for d in daily)
        text = (
            "MIS GANANCIAS (ULTIMOS 7 DIAS)\n\n"
            "Pedidos entregados: {}\n"
            "Bruto: {}\n"
            "Fee plataforma cobrado: {}\n"
            "Neto estimado: {}\n\n"
            "Selecciona un día para ver el detalle:"
        ).format(total_orders, _fmt_pesos(total_gross), _fmt_pesos(total_fee), _fmt_pesos(total_net))
        query.edit_message_text(text, reply_markup=_courier_earnings_buttons(daily))
        return

    if not data.startswith("courier_earn_"):
        query.edit_message_text("Accion invalida.")
        return

    compact = data[len("courier_earn_"):]
    if not compact.isdigit() or len(compact) != 8:
        query.edit_message_text("Fecha invalida.")
        return

    date_key = "{}-{}-{}".format(compact[0:4], compact[4:6], compact[6:8])
    ok, courier, rows, msg = courier_get_earnings_by_date_key(telegram_id, date_key)
    if not ok:
        query.edit_message_text(msg)
        return

    if not rows:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="courier_earn_back")]])
        query.edit_message_text("No hay registros para {}.".format(date_key), reply_markup=keyboard)
        return

    gross = sum(int(r.get("gross_amount") or 0) for r in rows)
    fee = sum(int(r.get("platform_fee") or 0) for r in rows)
    net = sum(int(r.get("net_amount") or 0) for r in rows)

    lines = [
        "DETALLE DE GANANCIAS",
        "",
        "Fecha: {}".format(date_key),
        "Pedidos: {}".format(len(rows)),
        "Bruto: {}".format(_fmt_pesos(gross)),
        "Fee plataforma cobrado: {}".format(_fmt_pesos(fee)),
        "Neto estimado: {}".format(_fmt_pesos(net)),
        "",
        "Pedidos:",
    ]
    for r in rows[:25]:
        order_id = r.get("order_id")
        hour_key = r.get("hour_key") or "--:--"
        lines.append(
            "#{} {} | Bruto {} | Fee {} | Neto {}".format(
                order_id,
                hour_key,
                _fmt_pesos(int(r.get("gross_amount") or 0)),
                _fmt_pesos(int(r.get("platform_fee") or 0)),
                _fmt_pesos(int(r.get("net_amount") or 0)),
            )
        )
    if len(rows) > 25:
        lines.append("... y {} mas.".format(len(rows) - 25))

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Volver", callback_data="courier_earn_back")]])
    query.edit_message_text("\n".join(lines), reply_markup=keyboard)


def construir_resumen_pedido(context):
    """Construye el texto del resumen del pedido."""
    tipo_servicio = context.user_data.get("service_type", "-")
    nombre = context.user_data.get("customer_name", "-")
    telefono = context.user_data.get("customer_phone", "-")
    direccion = context.user_data.get("customer_address", "-")
    pickup_label = context.user_data.get("pickup_label", "")
    pickup_address = context.user_data.get("pickup_address", "")
    distancia = context.user_data.get("quote_distance_km", 0)
    precio_base = int(context.user_data.get("quote_price", 0) or 0)
    incentivo = int(context.user_data.get("pedido_incentivo", 0) or 0)
    total = precio_base + incentivo
    requires_cash = context.user_data.get("requires_cash", False)
    cash_amount = context.user_data.get("cash_required_amount", 0)
    buy_products = context.user_data.get("buy_products_count", 0)
    buy_surcharge = context.user_data.get("buy_surcharge", 0)

    # Mostrar recogida
    if pickup_label and pickup_address:
        recogida = f"{pickup_label}: {pickup_address}"
    elif pickup_address:
        recogida = pickup_address
    else:
        recogida = "-"

    resumen = (
        "RESUMEN DEL PEDIDO\n\n"
        f"Tipo: {tipo_servicio}\n"
        f"Cliente: {nombre}\n"
        f"Telefono: {telefono}\n"
        f"Recogida: {recogida}\n"
        f"Entrega: {direccion}\n"
        f"Distancia: {distancia:.1f} km\n"
    )

    # Si es Compras, mostrar lista y desglose de precio
    if tipo_servicio == "Compras":
        buy_list = context.user_data.get("buy_products_list", "")
        if buy_list:
            resumen += f"Lista de productos:\n{buy_list}\n"
        if buy_products > 0:
            tarifa_distancia = precio_base - buy_surcharge
            resumen += "Tarifa distancia: " + _fmt_pesos(tarifa_distancia) + "\n"
            resumen += f"Total unidades: {buy_products}\n"
            if buy_surcharge > 0:
                resumen += "Recargo productos: " + _fmt_pesos(buy_surcharge) + "\n"

    resumen += "Valor base del servicio: " + _fmt_pesos(precio_base) + "\n"
    if incentivo > 0:
        resumen += "Incentivo adicional: " + _fmt_pesos(incentivo) + "\n"
    resumen += "Total a pagar: " + _fmt_pesos(total) + "\n"

    if requires_cash and cash_amount > 0:
        resumen += "Base requerida: " + _fmt_pesos(cash_amount) + "\n"

    resumen += (
        "\nSugerencia: En horas de alta demanda los repartidores toman primero los servicios mejor pagos. "
        "Si agregas incentivo, es mas probable que te tomen rapido.\n\n"
        "Confirmas este pedido?"
    )
    return resumen


def mostrar_resumen_confirmacion(query, context, edit=True):
    """Muestra resumen del pedido con botones de confirmacion (para CallbackQuery)."""
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")
    if pickup_lat is None or pickup_lng is None:
        return mostrar_selector_pickup(query, context, edit=True)
    try:
        context.bot.send_location(
            chat_id=query.message.chat_id,
            latitude=float(pickup_lat),
            longitude=float(pickup_lng),
        )
    except Exception:
        pass

    keyboard = _pedido_incentivo_keyboard() + [
        [InlineKeyboardButton("Confirmar pedido", callback_data="pedido_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    if edit:
        query.edit_message_text(resumen, reply_markup=reply_markup)
    else:
        query.message.reply_text(resumen, reply_markup=reply_markup)

    return PEDIDO_CONFIRMACION


def mostrar_resumen_confirmacion_msg(update, context):
    """Muestra resumen del pedido con botones de confirmacion (para Message)."""
    pickup_lat = context.user_data.get("pickup_lat")
    pickup_lng = context.user_data.get("pickup_lng")
    if pickup_lat is None or pickup_lng is None:
        return mostrar_selector_pickup(update, context, edit=False)
    try:
        context.bot.send_location(
            chat_id=update.effective_chat.id,
            latitude=float(pickup_lat),
            longitude=float(pickup_lng),
        )
    except Exception:
        pass

    keyboard = _pedido_incentivo_keyboard() + [
        [InlineKeyboardButton("Confirmar pedido", callback_data="pedido_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="pedido_cancelar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    resumen = construir_resumen_pedido(context)

    update.message.reply_text(resumen, reply_markup=reply_markup)
    return PEDIDO_CONFIRMACION


def pedido_confirmacion(update, context):
    """Fallback: redirige a botones si el usuario escribe texto."""
    # Mostrar resumen con botones
    return mostrar_resumen_confirmacion_msg(update, context)


def pedido_incentivo_fixed_callback(update, context):
    """Agrega incentivo (botones +1000/+1500/+2000/+3000) antes de confirmar pedido."""
    query = update.callback_query
    query.answer()
    data = query.data
    parts = data.split("_")
    if len(parts) != 3:
        return PEDIDO_CONFIRMACION
    if parts[0] != "pedido" or parts[1] != "inc":
        return PEDIDO_CONFIRMACION
    try:
        delta = int(parts[2])
    except Exception:
        return PEDIDO_CONFIRMACION
    if delta <= 0:
        return PEDIDO_CONFIRMACION

    current = int(context.user_data.get("pedido_incentivo", 0) or 0)
    context.user_data["pedido_incentivo"] = current + delta
    return mostrar_resumen_confirmacion(query, context, edit=True)


def pedido_incentivo_otro_start(update, context):
    """Pide al aliado ingresar un incentivo adicional por texto (antes de confirmar)."""
    query = update.callback_query
    query.answer()
    context.user_data.pop("pedido_incentivo_edit_order_id", None)
    query.edit_message_text(
        "Escribe el incentivo adicional en pesos (solo numeros).\n"
        "Ejemplo: 2500\n\n"
        "Escribe 'cancelar' para volver al menu."
    )
    return PEDIDO_INCENTIVO_MONTO


def pedido_incentivo_monto_handler(update, context):
    """Recibe incentivo adicional por texto antes de confirmar."""
    text = (update.message.text or "").strip()
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return PEDIDO_INCENTIVO_MONTO
    try:
        delta = int(digits)
    except Exception:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return PEDIDO_INCENTIVO_MONTO
    if delta <= 0:
        update.message.reply_text("El incentivo debe ser mayor a 0.")
        return PEDIDO_INCENTIVO_MONTO
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto.")
        return PEDIDO_INCENTIVO_MONTO

    current = int(context.user_data.get("pedido_incentivo", 0) or 0)
    context.user_data["pedido_incentivo"] = current + delta
    return mostrar_resumen_confirmacion_msg(update, context)


def _pedido_incentivo_menu_text(order):
    order_id = int(order["id"])
    incentive = int(order["additional_incentive"] or 0)
    total_fee = int(order["total_fee"] or 0)
    return (
        "INCENTIVO DEL PEDIDO\n\n"
        "Pedido: #{}\n"
        "Incentivo actual: {}\n"
        "Pago total: {}\n\n"
        "Sugerencia: En horas de alta demanda los repartidores toman primero los servicios mejor pagos. "
        "Si agregas incentivo, es mas probable que te tomen rapido."
    ).format(order_id, _fmt_pesos(incentive), _fmt_pesos(total_fee))


def pedido_incentivo_menu_callback(update, context):
    """Muestra menú para aumentar incentivo de un pedido ya creado."""
    query = update.callback_query
    query.answer()
    parts = query.data.split("_")
    if len(parts) != 4:
        query.edit_message_text("Accion invalida.")
        return
    try:
        order_id = int(parts[3])
    except Exception:
        query.edit_message_text("Accion invalida.")
        return

    telegram_id = update.effective_user.id
    ok, order, msg = ally_get_order_for_incentive(telegram_id, order_id)
    if not ok:
        query.edit_message_text(msg)
        return

    keyboard = _pedido_incentivo_keyboard(order_id=order_id)
    query.edit_message_text(_pedido_incentivo_menu_text(order), reply_markup=InlineKeyboardMarkup(keyboard))


def pedido_incentivo_existing_fixed_callback(update, context):
    """Agrega incentivo (botones +1000/+1500/+2000/+3000) a pedido existente."""
    query = update.callback_query
    query.answer()
    if not query.data.startswith("pedido_inc_"):
        query.edit_message_text("Accion invalida.")
        return
    payload = query.data[len("pedido_inc_"):]
    if "x" not in payload:
        query.edit_message_text("Accion invalida.")
        return
    chunks = payload.split("x", 1)
    try:
        order_id = int(chunks[0])
        delta = int(chunks[1])
    except Exception:
        query.edit_message_text("Accion invalida.")
        return

    telegram_id = update.effective_user.id
    ok, order, courier_telegram_id, msg = ally_increment_order_incentive(telegram_id, order_id, delta)
    if not ok:
        query.edit_message_text(msg)
        return

    if courier_telegram_id:
        try:
            incentive = int(order["additional_incentive"] or 0)
            total_fee = int(order["total_fee"] or 0)
            context.bot.send_message(
                chat_id=courier_telegram_id,
                text=(
                    "Actualizacion de pedido #{}:\n"
                    "El aliado aumento el incentivo.\n"
                    "Incentivo adicional: {}\n"
                    "Pago total: {}"
                ).format(order_id, _fmt_pesos(incentive), _fmt_pesos(total_fee)),
            )
        except Exception:
            pass

    keyboard = _pedido_incentivo_keyboard(order_id=order_id)
    query.edit_message_text(_pedido_incentivo_menu_text(order), reply_markup=InlineKeyboardMarkup(keyboard))


def pedido_incentivo_existing_otro_start(update, context):
    """Inicia captura de 'Otro monto' para un pedido existente."""
    query = update.callback_query
    query.answer()
    parts = query.data.split("_")
    if len(parts) != 4:
        query.edit_message_text("Accion invalida.")
        return ConversationHandler.END
    try:
        order_id = int(parts[3])
    except Exception:
        query.edit_message_text("Accion invalida.")
        return ConversationHandler.END

    context.user_data["pedido_incentivo_edit_order_id"] = order_id
    query.edit_message_text(
        "Escribe el incentivo adicional en pesos (solo numeros).\n"
        "Ejemplo: 2500\n\n"
        "Escribe 'cancelar' para salir."
    )
    return PEDIDO_INCENTIVO_MONTO


def pedido_incentivo_existing_monto_handler(update, context):
    """Recibe incentivo adicional por texto para un pedido existente."""
    order_id = context.user_data.get("pedido_incentivo_edit_order_id")
    if not order_id:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return PEDIDO_INCENTIVO_MONTO

    try:
        delta = int(digits)
    except Exception:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return PEDIDO_INCENTIVO_MONTO

    if delta <= 0:
        update.message.reply_text("El incentivo debe ser mayor a 0.")
        return PEDIDO_INCENTIVO_MONTO
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto.")
        return PEDIDO_INCENTIVO_MONTO

    telegram_id = update.effective_user.id
    ok, order, courier_telegram_id, msg = ally_increment_order_incentive(telegram_id, int(order_id), int(delta))
    if not ok:
        update.message.reply_text(msg)
        context.user_data.pop("pedido_incentivo_edit_order_id", None)
        return ConversationHandler.END

    context.user_data.pop("pedido_incentivo_edit_order_id", None)

    if courier_telegram_id:
        try:
            incentive = int(order["additional_incentive"] or 0)
            total_fee = int(order["total_fee"] or 0)
            context.bot.send_message(
                chat_id=courier_telegram_id,
                text=(
                    "Actualizacion de pedido #{}:\n"
                    "El aliado aumento el incentivo.\n"
                    "Incentivo adicional: {}\n"
                    "Pago total: {}"
                ).format(int(order_id), _fmt_pesos(incentive), _fmt_pesos(total_fee)),
            )
        except Exception:
            pass

    keyboard = _pedido_incentivo_keyboard(order_id=int(order_id))
    update.message.reply_text(_pedido_incentivo_menu_text(order), reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


# ── Sugerencia de incentivo T+5 (aplica a todos los pedidos: aliados y admin) ──

def offer_suggest_inc_fixed_callback(update, context):
    """Botones +1500/+2000/+3000 de la sugerencia T+5."""
    query = update.callback_query
    query.answer()
    data = query.data  # offer_inc_{order_id}x{delta}
    try:
        parts = data.replace("offer_inc_", "").split("x")
        order_id = int(parts[0])
        delta = int(parts[1])
    except Exception:
        query.edit_message_text("Error al procesar el incentivo.")
        return

    telegram_id = update.effective_user.id
    order = get_order_by_id(order_id)
    if not order:
        query.edit_message_text("Pedido no encontrado.")
        return

    # Determinar si el creador es aliado o admin
    creator_admin_id = order.get("creator_admin_id") if hasattr(order, "get") else order["creator_admin_id"]
    if creator_admin_id:
        ok, updated, courier_tid, msg = admin_increment_order_incentive(telegram_id, order_id, delta)
    else:
        ok, updated, courier_tid, msg = ally_increment_order_incentive(telegram_id, order_id, delta)

    if not ok:
        query.edit_message_text(msg)
        return

    # Re-ofertar a todos los couriers y re-programar T+5
    repost_count = repost_order_to_couriers(order_id, context)

    total_fee = int(updated["total_fee"] or 0)
    incentive = int(updated["additional_incentive"] or 0)
    query.edit_message_text(
        "Incentivo agregado: +${:,}\n"
        "Tarifa total del pedido: ${:,}\n"
        "Re-ofertando a {} repartidores activos.".format(
            delta, total_fee, repost_count
        )
    )


def offer_suggest_inc_otro_start(update, context):
    """Boton 'Otro monto' de la sugerencia T+5."""
    query = update.callback_query
    query.answer()
    data = query.data  # offer_inc_otro_{order_id}
    try:
        order_id = int(data.replace("offer_inc_otro_", ""))
    except Exception:
        query.edit_message_text("Error al procesar la solicitud.")
        return ConversationHandler.END

    order = get_order_by_id(order_id)
    if not order or order["status"] not in ("PENDING", "PUBLISHED"):
        query.edit_message_text("Este pedido ya no permite agregar incentivo.")
        return ConversationHandler.END

    context.user_data["offer_suggest_edit_order_id"] = order_id
    query.edit_message_text("Ingresa el monto del incentivo que deseas agregar (en pesos COP, solo numeros):")
    return OFFER_SUGGEST_INC_MONTO


def offer_suggest_inc_monto_handler(update, context):
    """Recibe monto libre de incentivo de la sugerencia T+5."""
    order_id = context.user_data.get("offer_suggest_edit_order_id")
    if not order_id:
        return ConversationHandler.END

    text = (update.message.text or "").strip()
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return OFFER_SUGGEST_INC_MONTO

    try:
        delta = int(digits)
    except Exception:
        update.message.reply_text("Ingresa un monto valido (solo numeros).")
        return OFFER_SUGGEST_INC_MONTO

    if delta <= 0:
        update.message.reply_text("El incentivo debe ser mayor a 0.")
        return OFFER_SUGGEST_INC_MONTO
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto (maximo $200,000).")
        return OFFER_SUGGEST_INC_MONTO

    telegram_id = update.effective_user.id
    order = get_order_by_id(order_id)
    creator_admin_id = order.get("creator_admin_id") if (order and hasattr(order, "get")) else (order["creator_admin_id"] if order else None)

    if creator_admin_id:
        ok, updated, courier_tid, msg = admin_increment_order_incentive(telegram_id, int(order_id), delta)
    else:
        ok, updated, courier_tid, msg = ally_increment_order_incentive(telegram_id, int(order_id), delta)

    context.user_data.pop("offer_suggest_edit_order_id", None)

    if not ok:
        update.message.reply_text(msg)
        return ConversationHandler.END

    repost_count = repost_order_to_couriers(int(order_id), context)
    total_fee = int(updated["total_fee"] or 0)
    incentive = int(updated["additional_incentive"] or 0)
    update.message.reply_text(
        "Incentivo agregado: +${:,}\n"
        "Tarifa total del pedido: ${:,}\n"
        "Re-ofertando a {} repartidores activos.".format(
            delta, total_fee, repost_count
        )
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────
# PEDIDO ESPECIAL ADMIN
# ─────────────────────────────────────────────────────────────────────────

def _admin_ped_preview_text(ctx):
    """Construye texto y teclado del preview del pedido especial del admin."""
    tarifa = int(ctx.get("admin_ped_tarifa") or 0)
    incentivo = int(ctx.get("admin_ped_incentivo") or 0)
    total = tarifa + incentivo
    instruc = ctx.get("admin_ped_instruc") or "Ninguna"
    text = (
        "Resumen del pedido especial:\n\n"
        "Recogida: {}\n"
        "Cliente: {} / {}\n"
        "Entrega: {}\n"
        "Tarifa al courier: ${:,}\n"
        "{}"
        "Instrucciones: {}\n\n"
        "Total oferta: ${:,}"
    ).format(
        ctx.get("admin_ped_pickup_addr", ""),
        ctx.get("admin_ped_cust_name", ""),
        ctx.get("admin_ped_cust_phone", ""),
        ctx.get("admin_ped_cust_addr", ""),
        tarifa,
        "Incentivo: +${:,}\n".format(incentivo) if incentivo else "",
        instruc,
        total,
    )
    keyboard = [
        [InlineKeyboardButton("Confirmar y publicar", callback_data="admin_pedido_confirmar")],
        [
            InlineKeyboardButton("+$1,500", callback_data="admin_pedido_inc_1500"),
            InlineKeyboardButton("+$2,000", callback_data="admin_pedido_inc_2000"),
            InlineKeyboardButton("+$3,000", callback_data="admin_pedido_inc_3000"),
        ],
        [InlineKeyboardButton("Otro incentivo", callback_data="admin_pedido_inc_otro")],
        [InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")],
    ]
    return text, InlineKeyboardMarkup(keyboard)


def admin_nuevo_pedido_start(update, context):
    """Entrada al flujo de pedido especial del admin. Verifica y muestra puntos de recogida."""
    query = update.callback_query
    query.answer()
    telegram_id = update.effective_user.id
    admin = get_admin_by_telegram_id(telegram_id)
    if not admin or (admin.get("status") or "").upper() != "APPROVED":
        query.edit_message_text("Solo los administradores aprobados pueden crear pedidos especiales.")
        return ConversationHandler.END
    admin_id = admin["id"]
    # Limpiar datos anteriores del flujo
    for key in list(context.user_data.keys()):
        if key.startswith("admin_ped_"):
            del context.user_data[key]
    context.user_data["admin_ped_admin_id"] = admin_id
    locations = get_admin_locations(admin_id)
    keyboard = []
    for loc in locations:
        label = loc["label"] if loc["label"] else loc["address"]
        keyboard.append([InlineKeyboardButton(label, callback_data="admin_pedido_pickup_{}".format(loc["id"]))])
    keyboard.append([InlineKeyboardButton("Nueva direccion de recogida", callback_data="admin_pedido_nueva_dir")])
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="admin_pedido_cancelar")])
    query.edit_message_text(
        "Pedido especial — Punto de recogida\n\nSelecciona el punto de recogida:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_PICKUP


def admin_pedido_pickup_callback(update, context):
    """Selecciona ubicacion de recogida existente y avanza a nombre del cliente."""
    query = update.callback_query
    query.answer()
    loc_id = int(query.data.split("_")[-1])
    admin_id = context.user_data.get("admin_ped_admin_id")
    loc = get_admin_location_by_id(loc_id, admin_id)
    if not loc:
        query.edit_message_text("Ubicacion no encontrada. Intenta de nuevo.")
        return ADMIN_PEDIDO_PICKUP
    context.user_data["admin_ped_pickup_id"] = loc_id
    context.user_data["admin_ped_pickup_addr"] = loc["address"]
    context.user_data["admin_ped_pickup_lat"] = loc.get("lat")
    context.user_data["admin_ped_pickup_lng"] = loc.get("lng")
    context.user_data["admin_ped_pickup_city"] = loc.get("city", "")
    context.user_data["admin_ped_pickup_barrio"] = loc.get("barrio", "")
    query.edit_message_text(
        "Recogida: {}\n\nNombre del cliente:".format(loc["address"])
    )
    return ADMIN_PEDIDO_CUST_NAME


def admin_pedido_nueva_dir_start(update, context):
    """Pide al admin que escriba la nueva direccion de recogida."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "Escribe la direccion del punto de recogida (o envia tu ubicacion GPS):"
    )
    return ADMIN_PEDIDO_PICKUP


def admin_pedido_pickup_text_handler(update, context):
    """Geocodifica el texto ingresado como nueva direccion de recogida."""
    texto = update.message.text.strip()
    geo = resolve_location(texto)
    if not geo:
        update.message.reply_text(
            "No pude encontrar esa direccion. Intentalo de nuevo o envia tu ubicacion GPS."
        )
        return ADMIN_PEDIDO_PICKUP
    context.user_data["admin_ped_geo_pickup_pending"] = {
        "address": geo.get("address", texto),
        "lat": geo.get("lat"),
        "lng": geo.get("lng"),
        "city": geo.get("city", ""),
        "barrio": geo.get("barrio", ""),
        "original_text": texto,
    }
    keyboard = [[
        InlineKeyboardButton("Si, es correcto", callback_data="admin_pedido_geo_pickup_si"),
        InlineKeyboardButton("No, buscar otro", callback_data="admin_pedido_geo_pickup_no"),
    ]]
    update.message.reply_text(
        "Encontre: {}\n\nEs esta la direccion correcta?".format(geo.get("address", texto)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_PICKUP


def admin_pedido_pickup_gps_handler(update, context):
    """Guarda la ubicacion GPS enviada como nueva direccion de recogida."""
    location = update.message.location
    lat, lng = location.latitude, location.longitude
    context.user_data["admin_ped_pickup_id"] = None
    context.user_data["admin_ped_pickup_addr"] = "GPS ({:.5f}, {:.5f})".format(lat, lng)
    context.user_data["admin_ped_pickup_lat"] = lat
    context.user_data["admin_ped_pickup_lng"] = lng
    context.user_data["admin_ped_pickup_city"] = ""
    context.user_data["admin_ped_pickup_barrio"] = ""
    update.message.reply_text("Punto de recogida guardado.\n\nNombre del cliente:")
    return ADMIN_PEDIDO_CUST_NAME


def admin_pedido_geo_pickup_callback(update, context):
    """Confirma o rechaza geocodificacion del punto de recogida."""
    query = update.callback_query
    query.answer()
    pending = context.user_data.get("admin_ped_geo_pickup_pending", {})
    if query.data == "admin_pedido_geo_pickup_si":
        context.user_data["admin_ped_pickup_id"] = None
        context.user_data["admin_ped_pickup_addr"] = pending.get("address", "")
        context.user_data["admin_ped_pickup_lat"] = pending.get("lat")
        context.user_data["admin_ped_pickup_lng"] = pending.get("lng")
        context.user_data["admin_ped_pickup_city"] = pending.get("city", "")
        context.user_data["admin_ped_pickup_barrio"] = pending.get("barrio", "")
        context.user_data.pop("admin_ped_geo_pickup_pending", None)
        query.edit_message_text(
            "Recogida: {}\n\nNombre del cliente:".format(context.user_data["admin_ped_pickup_addr"])
        )
        return ADMIN_PEDIDO_CUST_NAME
    else:
        original = pending.get("original_text", "")
        seen = [pending["address"]] if pending.get("address") else []
        next_geo = resolve_location_next(original, seen) if original else None
        if next_geo:
            context.user_data["admin_ped_geo_pickup_pending"] = {
                "address": next_geo.get("address", ""),
                "lat": next_geo.get("lat"),
                "lng": next_geo.get("lng"),
                "city": next_geo.get("city", ""),
                "barrio": next_geo.get("barrio", ""),
                "original_text": original,
            }
            keyboard = [[
                InlineKeyboardButton("Si, es correcto", callback_data="admin_pedido_geo_pickup_si"),
                InlineKeyboardButton("No, buscar otro", callback_data="admin_pedido_geo_pickup_no"),
            ]]
            query.edit_message_text(
                "Otro resultado: {}\n\nEs esta la direccion correcta?".format(next_geo.get("address", "")),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ADMIN_PEDIDO_PICKUP
        else:
            query.edit_message_text(
                "No encontre mas resultados. Escribe la direccion nuevamente o envia GPS:"
            )
            context.user_data.pop("admin_ped_geo_pickup_pending", None)
            return ADMIN_PEDIDO_PICKUP


def admin_pedido_cust_name_handler(update, context):
    """Captura nombre del cliente."""
    nombre = update.message.text.strip()
    if not nombre:
        update.message.reply_text("El nombre no puede estar vacio.")
        return ADMIN_PEDIDO_CUST_NAME
    context.user_data["admin_ped_cust_name"] = nombre
    update.message.reply_text("Telefono del cliente (minimo 7 digitos):")
    return ADMIN_PEDIDO_CUST_PHONE


def admin_pedido_cust_phone_handler(update, context):
    """Captura telefono del cliente."""
    phone = update.message.text.strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 7:
        update.message.reply_text("Telefono invalido. Ingresa minimo 7 digitos.")
        return ADMIN_PEDIDO_CUST_PHONE
    context.user_data["admin_ped_cust_phone"] = phone
    update.message.reply_text("Direccion de entrega del cliente (escribe o envia GPS):")
    return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_cust_addr_handler(update, context):
    """Geocodifica la direccion de entrega del cliente."""
    texto = update.message.text.strip()
    geo = resolve_location(texto)
    if not geo:
        update.message.reply_text(
            "No pude encontrar esa direccion. Intentalo de nuevo o envia GPS."
        )
        return ADMIN_PEDIDO_CUST_ADDR
    context.user_data["admin_ped_geo_cust_pending"] = {
        "address": geo.get("address", texto),
        "lat": geo.get("lat"),
        "lng": geo.get("lng"),
        "city": geo.get("city", ""),
        "barrio": geo.get("barrio", ""),
        "original_text": texto,
    }
    keyboard = [[
        InlineKeyboardButton("Si, es correcto", callback_data="admin_pedido_geo_si"),
        InlineKeyboardButton("No, buscar otro", callback_data="admin_pedido_geo_no"),
    ]]
    update.message.reply_text(
        "Encontre: {}\n\nEs esta la direccion de entrega correcta?".format(geo.get("address", texto)),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_cust_gps_handler(update, context):
    """Guarda la ubicacion GPS enviada como direccion de entrega."""
    location = update.message.location
    lat, lng = location.latitude, location.longitude
    context.user_data["admin_ped_cust_addr"] = "GPS ({:.5f}, {:.5f})".format(lat, lng)
    context.user_data["admin_ped_dropoff_lat"] = lat
    context.user_data["admin_ped_dropoff_lng"] = lng
    context.user_data["admin_ped_dropoff_city"] = ""
    context.user_data["admin_ped_dropoff_barrio"] = ""
    update.message.reply_text(
        "Direccion de entrega registrada.\n\nTarifa al courier (ingresa el monto en pesos):"
    )
    return ADMIN_PEDIDO_TARIFA


def admin_pedido_geo_callback(update, context):
    """Confirma o rechaza geocodificacion de la direccion de entrega del cliente."""
    query = update.callback_query
    query.answer()
    pending = context.user_data.get("admin_ped_geo_cust_pending", {})
    if query.data == "admin_pedido_geo_si":
        context.user_data["admin_ped_cust_addr"] = pending.get("address", "")
        context.user_data["admin_ped_dropoff_lat"] = pending.get("lat")
        context.user_data["admin_ped_dropoff_lng"] = pending.get("lng")
        context.user_data["admin_ped_dropoff_city"] = pending.get("city", "")
        context.user_data["admin_ped_dropoff_barrio"] = pending.get("barrio", "")
        context.user_data.pop("admin_ped_geo_cust_pending", None)
        query.edit_message_text(
            "Entrega: {}\n\nTarifa al courier (ingresa el monto en pesos):".format(
                context.user_data["admin_ped_cust_addr"]
            )
        )
        return ADMIN_PEDIDO_TARIFA
    else:
        original = pending.get("original_text", "")
        seen = [pending["address"]] if pending.get("address") else []
        next_geo = resolve_location_next(original, seen) if original else None
        if next_geo:
            context.user_data["admin_ped_geo_cust_pending"] = {
                "address": next_geo.get("address", ""),
                "lat": next_geo.get("lat"),
                "lng": next_geo.get("lng"),
                "city": next_geo.get("city", ""),
                "barrio": next_geo.get("barrio", ""),
                "original_text": original,
            }
            keyboard = [[
                InlineKeyboardButton("Si, es correcto", callback_data="admin_pedido_geo_si"),
                InlineKeyboardButton("No, buscar otro", callback_data="admin_pedido_geo_no"),
            ]]
            query.edit_message_text(
                "Otro resultado: {}\n\nEs esta la direccion de entrega correcta?".format(
                    next_geo.get("address", "")
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return ADMIN_PEDIDO_CUST_ADDR
        else:
            query.edit_message_text(
                "No encontre mas resultados. Escribe la direccion nuevamente o envia GPS:"
            )
            context.user_data.pop("admin_ped_geo_cust_pending", None)
            return ADMIN_PEDIDO_CUST_ADDR


def admin_pedido_tarifa_handler(update, context):
    """Captura la tarifa manual al courier."""
    texto = update.message.text.strip().replace(",", "").replace(".", "")
    if not texto.isdigit() or int(texto) <= 0:
        update.message.reply_text("Ingresa un monto valido en pesos (numero entero mayor que 0).")
        return ADMIN_PEDIDO_TARIFA
    tarifa = int(texto)
    if tarifa > 500000:
        update.message.reply_text("La tarifa parece muy alta (maximo $500,000). Verifica el monto.")
        return ADMIN_PEDIDO_TARIFA
    context.user_data["admin_ped_tarifa"] = tarifa
    context.user_data.setdefault("admin_ped_incentivo", 0)
    keyboard = [[InlineKeyboardButton("Sin instrucciones", callback_data="admin_pedido_sin_instruc")]]
    update.message.reply_text(
        "Tarifa: ${:,}\n\nInstrucciones adicionales para el courier (o toca 'Sin instrucciones'):".format(tarifa),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_instruc_handler(update, context):
    """Guarda instrucciones y muestra preview del pedido."""
    context.user_data["admin_ped_instruc"] = update.message.text.strip()
    text, markup = _admin_ped_preview_text(context.user_data)
    update.message.reply_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_sin_instruc_callback(update, context):
    """Sin instrucciones: guarda vacio y muestra preview."""
    query = update.callback_query
    query.answer()
    context.user_data["admin_ped_instruc"] = ""
    text, markup = _admin_ped_preview_text(context.user_data)
    query.edit_message_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_inc_fijo_callback(update, context):
    """Agrega incentivo fijo al preview del pedido especial admin."""
    query = update.callback_query
    query.answer()
    delta = int(query.data.split("_")[-1])
    actual = int(context.user_data.get("admin_ped_incentivo") or 0)
    context.user_data["admin_ped_incentivo"] = actual + delta
    text, markup = _admin_ped_preview_text(context.user_data)
    query.edit_message_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_inc_otro_callback(update, context):
    """Solicita monto libre de incentivo."""
    query = update.callback_query
    query.answer()
    query.edit_message_text("Escribe el monto del incentivo adicional (en pesos):")
    return ADMIN_PEDIDO_INC_MONTO


def admin_pedido_inc_monto_handler(update, context):
    """Captura monto libre de incentivo y regresa al preview."""
    texto = update.message.text.strip().replace(",", "").replace(".", "")
    if not texto.isdigit() or int(texto) <= 0:
        update.message.reply_text("Ingresa un monto valido mayor que 0.")
        return ADMIN_PEDIDO_INC_MONTO
    delta = int(texto)
    if delta > 200000:
        update.message.reply_text("El incentivo es demasiado alto (maximo $200,000).")
        return ADMIN_PEDIDO_INC_MONTO
    actual = int(context.user_data.get("admin_ped_incentivo") or 0)
    context.user_data["admin_ped_incentivo"] = actual + delta
    text, markup = _admin_ped_preview_text(context.user_data)
    update.message.reply_text(text, reply_markup=markup)
    return ADMIN_PEDIDO_INSTRUC


def admin_pedido_confirmar_callback(update, context):
    """Crea y publica el pedido especial del admin."""
    query = update.callback_query
    query.answer()
    admin_id = context.user_data.get("admin_ped_admin_id")
    if not admin_id:
        query.edit_message_text("Sesion expirada. Usa 'Nuevo pedido especial' de nuevo.")
        return ConversationHandler.END
    tarifa = int(context.user_data.get("admin_ped_tarifa") or 0)
    incentivo = int(context.user_data.get("admin_ped_incentivo") or 0)
    total_fee = tarifa + incentivo
    pickup_location_id = context.user_data.get("admin_ped_pickup_id")
    pickup_addr = context.user_data.get("admin_ped_pickup_addr", "")
    pickup_lat = context.user_data.get("admin_ped_pickup_lat")
    pickup_lng = context.user_data.get("admin_ped_pickup_lng")
    pickup_city = context.user_data.get("admin_ped_pickup_city", "")
    pickup_barrio = context.user_data.get("admin_ped_pickup_barrio", "")
    cust_name = context.user_data.get("admin_ped_cust_name", "")
    cust_phone = context.user_data.get("admin_ped_cust_phone", "")
    cust_addr = context.user_data.get("admin_ped_cust_addr", "")
    dropoff_lat = context.user_data.get("admin_ped_dropoff_lat")
    dropoff_lng = context.user_data.get("admin_ped_dropoff_lng")
    dropoff_city = context.user_data.get("admin_ped_dropoff_city", "")
    dropoff_barrio = context.user_data.get("admin_ped_dropoff_barrio", "")
    instruc = context.user_data.get("admin_ped_instruc", "")
    try:
        order_id = create_order(
            ally_id=None,
            creator_admin_id=admin_id,
            customer_name=cust_name,
            customer_phone=cust_phone,
            customer_address=cust_addr,
            customer_city=dropoff_city,
            customer_barrio=dropoff_barrio,
            pickup_location_id=pickup_location_id,
            pay_at_store_required=False,
            pay_at_store_amount=0,
            base_fee=tarifa,
            distance_km=0.0,
            rain_extra=0,
            high_demand_extra=0,
            night_extra=0,
            additional_incentive=incentivo,
            total_fee=total_fee,
            instructions=instruc,
            requires_cash=False,
            cash_required_amount=0,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            quote_source="admin",
            ally_admin_id_snapshot=admin_id,
        )
    except Exception as e:
        print("[ERROR] admin_pedido_confirmar_callback create_order:", e)
        query.edit_message_text("Error al crear el pedido. Intenta de nuevo.")
        return ConversationHandler.END
    if pickup_location_id:
        increment_admin_location_usage(pickup_location_id, admin_id)
    published_count = 0
    try:
        published_count = publish_order_to_couriers(
            order_id,
            None,
            context,
            admin_id_override=admin_id,
            pickup_city=pickup_city,
            pickup_barrio=pickup_barrio,
            dropoff_city=dropoff_city,
            dropoff_barrio=dropoff_barrio,
            skip_fee_check=True,
        )
    except Exception as e:
        print("[WARN] admin_pedido_confirmar_callback publish:", e)
    query.edit_message_text(
        "Pedido especial publicado.\n"
        "ID: #{}\n"
        "Tarifa: ${:,}{}\n"
        "Ofertando a {} repartidores activos.".format(
            order_id,
            total_fee,
            " (+ ${:,} incentivo)".format(incentivo) if incentivo else "",
            published_count,
        )
    )
    for key in list(context.user_data.keys()):
        if key.startswith("admin_ped_"):
            del context.user_data[key]
    return ConversationHandler.END


def admin_pedido_cancelar_callback(update, context):
    """Cancela el flujo de pedido especial del admin."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith("admin_ped_"):
            del context.user_data[key]
    query.edit_message_text("Pedido cancelado.")
    return ConversationHandler.END


def pedido_confirmacion_callback(update, context):
    """Maneja la confirmacion/cancelacion del pedido por botones."""
    query = update.callback_query
    query.answer()
    data = query.data

    # Anti doble-click: verificar si ya fue procesado
    if context.user_data.get("pedido_processed"):
        query.edit_message_text("Este pedido ya fue procesado.")
        return ConversationHandler.END

    if data == "pedido_confirmar":
        # Marcar como procesado ANTES de crear el pedido
        context.user_data["pedido_processed"] = True

        # Obtener datos del usuario y ally
        ally_id = context.user_data.get("ally_id")
        if not ally_id:
            query.edit_message_text("Error: sesion expirada. Usa /nuevo_pedido de nuevo.")
            context.user_data.clear()
            return ConversationHandler.END
        chat_id = query.message.chat_id

        admin_link = get_approved_admin_link_for_ally(ally_id)
        admin_id_for_publish = None

        if admin_link:
            admin_id_for_publish = admin_link["admin_id"]
        else:
            latest_admin_link = get_admin_link_for_ally(ally_id)
            latest_link_status = (latest_admin_link["link_status"] or "").upper() if latest_admin_link else ""

            if latest_admin_link and latest_link_status in ("PENDING", "REJECTED", "INACTIVE"):
                ok_cov, cov_msg, migrated_couriers = ensure_platform_temp_coverage_for_ally(ally_id)
                if ok_cov:
                    platform_admin = get_platform_admin()
                    admin_id_for_publish = platform_admin["id"] if platform_admin else None
                    print("[INFO] Cobertura temporal plataforma aplicada para ally_id={} couriers_migrados={}".format(
                        ally_id, migrated_couriers
                    ))
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "Tu administracion local aun no esta aprobada. "
                            "Activamos cobertura temporal con Plataforma para que puedas operar.\n"
                            "Te recomendamos solicitar migracion a un admin APPROVED desde 'Solicitar cambio'."
                        ),
                    )
                else:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text="No se pudo activar cobertura temporal: {}".format(cov_msg),
                    )
                    context.user_data.clear()
                    return ConversationHandler.END
            elif user_has_platform_admin(query.from_user.id):
                platform_admin = get_platform_admin()
                if platform_admin:
                    admin_id_for_publish = platform_admin["id"]
                    print("[INFO] Platform bypass aplicado: aliado sin link APPROVED, pedido publicado con admin plataforma.")
                else:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            "No se encontro Admin Plataforma activo para continuar.\n"
                            "Contacta soporte de plataforma."
                        ),
                    )
                    context.user_data.clear()
                    return ConversationHandler.END
            else:
                context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "No tienes un administrador APPROVED vinculado.\n"
                        "No se puede crear ni publicar el pedido hasta tener un vinculo aprobado."
                    ),
                )
                context.user_data.clear()
                return ConversationHandler.END

        # Verificacion final obligatoria de saldo ANTES de crear pedido,
        # incluyendo cobertura temporal con plataforma.
        fee_ok, fee_code = check_service_fee_available(
            target_type="ALLY",
            target_id=ally_id,
            admin_id=admin_id_for_publish,
        )
        if not fee_ok:
            if fee_code == "ADMIN_SIN_SALDO":
                context.bot.send_message(
                    chat_id=chat_id,
                    text="Tu administrador no tiene saldo suficiente para operar. "
                         "Contacta a tu administrador o recarga directamente con plataforma."
                )
                try:
                    admin_row = get_admin_by_id(admin_id_for_publish)
                    if admin_row:
                        admin_user = get_user_by_id(admin_row["user_id"])
                        if admin_user:
                            context.bot.send_message(
                                chat_id=admin_user["telegram_id"],
                                text="Tu equipo no puede operar porque no tienes saldo. "
                                     "Recarga con plataforma para que tu equipo siga generando ganancias."
                            )
                except Exception as e:
                    print("[WARN] No se pudo notificar al admin:", e)
            else:
                context.bot.send_message(
                    chat_id=chat_id,
                    text="No tienes saldo suficiente para este servicio. Recarga para continuar."
                )
            context.user_data.clear()
            return ConversationHandler.END

        # Obtener pickup del selector (o default si no existe)
        pickup_location = context.user_data.get("pickup_location")
        pickup_text = context.user_data.get("pickup_address", "")
        if pickup_location:
            pickup_location_id = pickup_location.get("id")
        else:
            # Fallback: usar default si no se selecciono ninguno
            default_location = get_default_ally_location(ally_id)
            pickup_location_id = default_location["id"] if default_location else None
            if not pickup_text and default_location:
                pickup_text = default_location.get("address", "No definida")

        if not pickup_text:
            pickup_text = "No definida"

        # Obtener datos del pedido de context.user_data
        customer_name = context.user_data.get("customer_name", "")
        customer_phone = context.user_data.get("customer_phone", "")
        customer_address = context.user_data.get("customer_address", "")
        customer_city = context.user_data.get("customer_city", "")
        customer_barrio = context.user_data.get("customer_barrio", "")
        service_type = context.user_data.get("service_type", "")

        # Obtener datos de cotizacion
        distance_km = context.user_data.get("quote_distance_km", 0.0)
        quote_price = context.user_data.get("quote_price", 0)
        requires_cash = context.user_data.get("requires_cash", False)
        cash_required_amount = context.user_data.get("cash_required_amount", 0)

        # Obtener coords y quote_source
        pickup_lat = context.user_data.get("pickup_lat")
        pickup_lng = context.user_data.get("pickup_lng")
        dropoff_lat = context.user_data.get("dropoff_lat")
        dropoff_lng = context.user_data.get("dropoff_lng")
        quote_source = context.user_data.get("quote_source", "text")

        # Preparar instrucciones (para Compras, incluir lista de productos)
        base_instructions = context.user_data.get("instructions", "")
        buy_products_list = context.user_data.get("buy_products_list", "")
        if service_type == "Compras" and buy_products_list:
            instructions_final = f"[Lista Compras: {buy_products_list}]"
            if base_instructions:
                instructions_final += f"\n{base_instructions}"
        else:
            instructions_final = base_instructions

        # Crear pedido en BD
        try:
            pedido_incentivo = int(context.user_data.get("pedido_incentivo", 0) or 0)
            if pedido_incentivo < 0:
                pedido_incentivo = 0
            total_fee = int(quote_price or 0) + pedido_incentivo
            order_id = create_order(
                ally_id=ally_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_address=customer_address,
                customer_city=customer_city,
                customer_barrio=customer_barrio,
                pickup_location_id=pickup_location_id,
                pay_at_store_required=False,
                pay_at_store_amount=0,
                base_fee=0,
                distance_km=distance_km,
                rain_extra=0,
                high_demand_extra=0,
                night_extra=0,
                additional_incentive=pedido_incentivo,
                total_fee=total_fee,
                instructions=instructions_final,
                requires_cash=requires_cash,
                cash_required_amount=cash_required_amount,
                pickup_lat=pickup_lat,
                pickup_lng=pickup_lng,
                dropoff_lat=dropoff_lat,
                dropoff_lng=dropoff_lng,
                quote_source=quote_source,
                ally_admin_id_snapshot=admin_id_for_publish,
            )
            context.user_data["order_id"] = order_id

            # Publicar pedido a couriers del equipo
            published_count = 0
            try:
                published_count = publish_order_to_couriers(
                    order_id,
                    ally_id,
                    context,
                    admin_id_override=admin_id_for_publish,
                    pickup_city=context.user_data.get("pickup_city"),
                    pickup_barrio=context.user_data.get("pickup_barrio"),
                    dropoff_city=context.user_data.get("customer_city"),
                    dropoff_barrio=context.user_data.get("customer_barrio"),
                )
            except Exception as e:
                print("[WARN] Error al publicar pedido a couriers:", e)

            # Incrementar contador de uso del pickup
            if pickup_location_id:
                increment_pickup_usage(pickup_location_id, ally_id)

            # Construir preview de oferta para repartidor
            preview = construir_preview_oferta(
                order_id, service_type, pickup_text, customer_address,
                distance_km, total_fee, requires_cash, cash_required_amount,
                products_list=context.user_data.get("buy_products_list", "")
            )

            # Preguntar guardar cliente cuando el telefono no exista en recurrentes.
            is_new_customer = context.user_data.get("is_new_customer", False)
            customer_phone = context.user_data.get("customer_phone", "")
            customer_id_ctx = context.user_data.get("customer_id")
            existing_customer = get_ally_customer_by_phone(ally_id, customer_phone) if customer_phone else None
            should_offer_save_customer = bool((is_new_customer or not customer_id_ctx) and not existing_customer)

            if should_offer_save_customer:
                keyboard = [
                    [InlineKeyboardButton("Si, guardar cliente", callback_data="pedido_guardar_si")],
                    [InlineKeyboardButton("No, solo este pedido", callback_data="pedido_guardar_no")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                query.edit_message_text(
                    f"Pedido #{order_id} creado exitosamente.\n\n"
                    + ("No hay repartidores elegibles en este momento. "
                       "El pedido quedo registrado pero sin publicar.\n\n" if published_count == 0 else "")
                    +
                    "Quieres guardar este cliente para futuros pedidos?",
                    reply_markup=reply_markup
                )
                # Enviar preview como mensaje separado
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=preview,
                    reply_markup=get_preview_buttons()
                )
                return PEDIDO_GUARDAR_CLIENTE
            else:
                # Cliente existente: éxito directo + menú
                context.user_data.clear()
                if published_count == 0:
                    show_main_menu(
                        update,
                        context,
                        f"Pedido #{order_id} creado exitosamente.\n"
                        "No hay repartidores elegibles en este momento. "
                        "El pedido quedo registrado pero sin publicar.",
                    )
                else:
                    show_main_menu(
                        update,
                        context,
                        f"Pedido #{order_id} creado exitosamente.\nPronto un repartidor sera asignado.",
                    )
                return ConversationHandler.END

        except Exception as e:
            query.edit_message_text(
                f"Error al crear el pedido: {str(e)}\n\n"
                "Por favor intenta nuevamente mas tarde."
            )
            context.user_data.clear()
            show_main_menu(update, context)
            return ConversationHandler.END

    elif data == "pedido_cancelar":
        query.edit_message_text("Pedido cancelado.")
        context.user_data.clear()
        show_main_menu(update, context)
        return ConversationHandler.END

    return PEDIDO_CONFIRMACION


def construir_preview_oferta(order_id, service_type, pickup_text, customer_address,
                              distance_km, price, requires_cash, cash_amount,
                              products_list=""):
    """Construye el preview de la oferta que vera el repartidor."""
    preview = (
        "PREVIEW: ASI VERA EL REPARTIDOR LA OFERTA\n"
        + ("=" * 35) + "\n\n"
        "OFERTA DISPONIBLE\n\n"
        f"Servicio: {service_type}\n"
        f"Recoge en: {pickup_text}\n"
        f"Entrega en: {customer_address}\n"
        f"Distancia: {distance_km:.1f} km\n"
        f"Pago: ${price:,}".replace(",", ".") + "\n"
    )

    if service_type == "Compras" and products_list:
        preview += f"Lista de productos:\n{products_list}\n"

    if requires_cash and cash_amount > 0:
        preview += f"Base requerida: ${cash_amount:,}".replace(",", ".") + "\n"
        preview += (
            "\nADVERTENCIA:\n"
            f"Si no tienes al menos ${cash_amount:,}".replace(",", ".") + " de base, "
            "NO tomes este servicio.\n"
            "Sin base, no se te entregara la orden."
        )

    return preview


def get_preview_buttons():
    """Retorna botones simulados del preview."""
    keyboard = [
        [
            InlineKeyboardButton("Aceptar (preview)", callback_data="preview_accept"),
            InlineKeyboardButton("Rechazar (preview)", callback_data="preview_reject"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def preview_callback(update, context):
    """Maneja clicks en botones del preview (solo informativo)."""
    query = update.callback_query
    query.answer("Vista previa: esto lo vera el repartidor.", show_alert=True)


def pedido_guardar_cliente_callback(update, context):
    """Maneja la decision de guardar o no el cliente nuevo."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "pedido_guardar_si":
        ally_id = context.user_data.get("active_ally_id")
        customer_name = context.user_data.get("customer_name", "")
        customer_phone = context.user_data.get("customer_phone", "")
        customer_address = context.user_data.get("customer_address", "")

        try:
            # Crear cliente si no existe uno activo por telefono.
            existing_customer = get_ally_customer_by_phone(ally_id, customer_phone)
            if existing_customer:
                customer_id = existing_customer["id"]
            else:
                customer_id = create_ally_customer(ally_id, customer_name, customer_phone)
            # Crear direccion
            create_customer_address(
                customer_id,
                "Principal",
                customer_address,
                city=context.user_data.get("customer_city", ""),
                barrio=context.user_data.get("customer_barrio", ""),
                lat=context.user_data.get("dropoff_lat"),
                lng=context.user_data.get("dropoff_lng"),
            )
            context.user_data.clear()
            show_main_menu(update, context, f"Pedido creado exitosamente.\nCliente '{customer_name}' guardado para futuros pedidos.\nPronto un repartidor sera asignado.")
            return ConversationHandler.END
        except Exception as e:
            context.user_data.clear()
            show_main_menu(update, context, f"Pedido creado exitosamente.\nError al guardar cliente: {str(e)}\nPronto un repartidor sera asignado.")
            return ConversationHandler.END

    elif data == "pedido_guardar_no":
        context.user_data.clear()
        show_main_menu(update, context, "Pedido creado exitosamente.\nPronto un repartidor sera asignado.")
        return ConversationHandler.END

    return PEDIDO_GUARDAR_CLIENTE


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
        print(f"[ERROR] get_pending_allies(): {e}")
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
            pendientes = get_pending_couriers()  # global (tabla couriers)
        else:
            pendientes = get_pending_couriers_by_admin(admin_id)  # por equipo (tabla admin_couriers)
    except Exception as e:
        print(f"[ERROR] repartidores_pendientes: {e}")
        message.reply_text("Error consultando repartidores pendientes. Revisa logs del servidor.")
        return

    if not pendientes:
        message.reply_text("No hay repartidores pendientes por aprobar.")
        return

    for c in pendientes:
        # Ideal: que ambas funciones de DB devuelvan (courier_id, full_name, phone, city, barrio)
        courier_id = c.get("courier_id") or c.get("id")
        full_name = c.get("full_name", "")
        phone = c.get("phone", "")
        city = c.get("city", "")
        barrio = c.get("barrio", "")

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
                    print(f"[WARN] No se pudieron enviar fotos del repartidor {courier_id}: {e}")

        
def soy_admin(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    existing = get_admin_by_user_id(user_db_id)
    if existing:
        status = existing["status"]
        admin_id = existing["id"]

        rejection_type = get_admin_rejection_type_by_id(admin_id)

        if status in ("PENDING", "APPROVED"):
            msg = (
                "Ya tienes un registro de administrador en revisión (PENDING). Espera aprobación o usa /menu."
                if status == "PENDING" else
                "Ya tienes un registro de administrador aprobado (APPROVED). Si necesitas cambios, contacta al administrador de plataforma."
            )
            update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END

        if status == "REJECTED" and rejection_type == "BLOCKED":
            update.message.reply_text(
                "Tu registro anterior fue rechazado y bloqueado. Si crees que es un error, contacta al administrador de plataforma.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        if status != "INACTIVE":
            update.message.reply_text(
                f"No puedes iniciar un nuevo registro con estado {status}.\n"
                "Solo se permite nuevo registro cuando el registro previo esta en INACTIVE.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        team_name = existing["team_name"] or existing["full_name"]
        doc = existing["document_number"] or "No registrado"
        full_name = existing["full_name"]
        phone = existing["phone"]
        city = existing["city"]
        barrio = existing["barrio"]

        update.message.reply_text(
            "Ya tienes un registro como Administrador Local.\n"
            f"Nombre: {full_name}\n"
            f"Documento: {doc}\n"
            f"Administración: {team_name}\n"
            f"Teléfono: {phone}\n"
            f"Ciudad: {city}\n"
            f"Barrio: {barrio}\n"
            f"Estado: {status}\n\n"
            "Si deseas actualizar tus datos, escribe SI.\n"
            "Si no, escribe NO.",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data["admin_update_prompt"] = True
        _set_flow_step(context, "admin", LOCAL_ADMIN_NAME)
        return LOCAL_ADMIN_NAME

    update.message.reply_text(
        "Registro de Administrador Local.\n\n"
        "Escribe tu nombre completo:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro",
        reply_markup=ReplyKeyboardRemove()
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_NAME)
    return LOCAL_ADMIN_NAME


def admin_name(update, context):
    text = update.message.text.strip()

    if context.user_data.get("admin_update_prompt"):
        answer = text.upper()
        context.user_data.pop("admin_update_prompt", None)
        if answer == "SI":
            update.message.reply_text(
                "Perfecto. Escribe tu nombre completo:"
                "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
            )
            _set_flow_step(context, "admin", LOCAL_ADMIN_NAME)
            return LOCAL_ADMIN_NAME
        update.message.reply_text("Entendido. No se modificó tu registro.")
        context.user_data.clear()
        return ConversationHandler.END

    if not text:
        update.message.reply_text(
            "El nombre no puede estar vacío. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return LOCAL_ADMIN_NAME

    context.user_data["admin_name"] = text
    update.message.reply_text(
        "Escribe tu número de documento (CC o equivalente):"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_DOCUMENT)
    return LOCAL_ADMIN_DOCUMENT


def admin_document(update, context):
    doc = update.message.text.strip()
    if len(doc) < 5:
        update.message.reply_text(
            "El número de documento parece muy corto. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return LOCAL_ADMIN_DOCUMENT

    context.user_data["admin_document"] = doc
    update.message.reply_text(
        "Escribe el nombre de tu administración (nombre del equipo).\n"
        "Ejemplo: Mensajeros Pereira Centro"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_TEAMNAME)
    return LOCAL_ADMIN_TEAMNAME


def admin_teamname(update, context):
    team_name = update.message.text.strip()
    if len(team_name) < 3:
        update.message.reply_text(
            "El nombre de la administración debe tener al menos 3 caracteres. Escríbelo de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return LOCAL_ADMIN_TEAMNAME

    context.user_data["admin_team_name"] = team_name
    update.message.reply_text(
        "Escribe tu número de teléfono:"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_PHONE)
    return LOCAL_ADMIN_PHONE


def admin_phone(update, context):
    return _handle_phone_input(update, context,
        storage_key="phone",
        current_state=LOCAL_ADMIN_PHONE,
        next_state=LOCAL_ADMIN_CITY,
        flow="admin",
        next_prompt="¿En qué ciudad vas a operar como Administrador Local?")


def admin_city(update, context):
    return _handle_text_field_input(update, context,
        error_msg="La ciudad no puede estar vacía. Escríbela de nuevo:",
        storage_key="admin_city",
        current_state=LOCAL_ADMIN_CITY,
        next_state=LOCAL_ADMIN_BARRIO,
        flow="admin",
        next_prompt="Escribe tu barrio o zona base de operación:")


def admin_barrio(update, context):
    return _handle_text_field_input(update, context,
        error_msg="El barrio no puede estar vacío. Escríbelo de nuevo:",
        storage_key="admin_barrio",
        current_state=LOCAL_ADMIN_BARRIO,
        next_state=LOCAL_ADMIN_RESIDENCE_ADDRESS,
        flow="admin",
        next_prompt="Escribe tu dirección de residencia (texto exacto). Ej: Calle 10 # 20-30, apto 301")


def admin_residence_address(update, context):
    address = update.message.text.strip()
    if len(address) < 6:
        update.message.reply_text(
            "La dirección debe tener al menos 6 caracteres. Escríbela de nuevo:"
            "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
        )
        return LOCAL_ADMIN_RESIDENCE_ADDRESS
    context.user_data["admin_residence_address"] = address
    update.message.reply_text(
        "Envía tu ubicación GPS (pin de Telegram) o pega un link de Google Maps."
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_RESIDENCE_LOCATION)
    return LOCAL_ADMIN_RESIDENCE_LOCATION


def admin_residence_location(update, context):
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
        else:
            # Geocoding: intentar como direccion escrita
            geo = resolve_location(text)
            if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
                _mostrar_confirmacion_geocode(
                    update.message, context,
                    geo, text,
                    "admin_geo_si", "admin_geo_no",
                )
                return LOCAL_ADMIN_RESIDENCE_LOCATION

    if lat is None or lng is None:
        update.message.reply_text(
            "No pude detectar la ubicacion. Envia un pin de Telegram o pega un link de Google Maps."
        )
        return LOCAL_ADMIN_RESIDENCE_LOCATION

    context.user_data["admin_residence_lat"] = lat
    context.user_data["admin_residence_lng"] = lng
    update.message.reply_text(
        "Ubicacion guardada.\n\n"
        "Para verificar tu identidad, necesitamos fotos de tu documento.\n\n"
        "Envia una foto del FRENTE de tu cedula:" + _OPTIONS_HINT
    )
    _set_flow_step(context, "admin", LOCAL_ADMIN_CEDULA_FRONT)
    return LOCAL_ADMIN_CEDULA_FRONT


def admin_geo_ubicacion_callback(update, context):
    """Maneja confirmacion de geocoding en el registro de admin local."""
    query = update.callback_query
    query.answer()

    if query.data == "admin_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos de ubicacion perdidos. Intenta de nuevo.")
            return LOCAL_ADMIN_RESIDENCE_LOCATION
        context.user_data["admin_residence_lat"] = lat
        context.user_data["admin_residence_lng"] = lng
        query.edit_message_text(
            "Ubicacion confirmada.\n\n"
            "Para verificar tu identidad, necesitamos fotos de tu documento.\n\n"
            "Envia una foto del FRENTE de tu cedula:" + _OPTIONS_HINT
        )
        _set_flow_step(context, "admin", LOCAL_ADMIN_CEDULA_FRONT)
        return LOCAL_ADMIN_CEDULA_FRONT
    else:  # admin_geo_no
        return _geo_siguiente_o_gps(query, context, "admin_geo_si", "admin_geo_no", LOCAL_ADMIN_RESIDENCE_LOCATION)


def admin_confirm(update, context):
    answer = update.message.text.strip().upper()
    user_db_id = get_user_db_id_from_update(update)

    if answer != "ACEPTAR":
        update.message.reply_text("Registro cancelado. Si deseas intentarlo de nuevo usa /soy_admin.")
        context.user_data.clear()
        return ConversationHandler.END

    full_name = (context.user_data.get("admin_name") or "").strip()
    document_number = (context.user_data.get("admin_document") or "").strip()
    team_name = (context.user_data.get("admin_team_name") or "").strip()
    phone = (context.user_data.get("phone") or "").strip()
    city = (context.user_data.get("admin_city") or "").strip()
    barrio = (context.user_data.get("admin_barrio") or "").strip()
    residence_address = (context.user_data.get("admin_residence_address") or "").strip()
    residence_lat = context.user_data.get("admin_residence_lat")
    residence_lng = context.user_data.get("admin_residence_lng")
    cedula_front_file_id = context.user_data.get("admin_cedula_front_file_id")
    cedula_back_file_id = context.user_data.get("admin_cedula_back_file_id")
    selfie_file_id = context.user_data.get("admin_selfie_file_id")

    try:
        admin_id, team_code = create_admin(
            user_db_id,
            full_name,
            phone,
            city,
            barrio,
            team_name,
            document_number,
            residence_address,
            residence_lat,
            residence_lng,
            cedula_front_file_id,
            cedula_back_file_id,
            selfie_file_id,
        )
    except ValueError as e:
        update.message.reply_text(str(e))
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        print("[ERROR] admin_confirm:", e)
        update.message.reply_text("Error técnico al finalizar tu registro. Intenta más tarde.")
        context.user_data.clear()
        return ConversationHandler.END

    try:
        context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                "Nuevo registro de ADMINISTRADOR LOCAL pendiente:\n\n"
                "Nombre: {}\n"
                "Documento: {}\n"
                "Equipo: {}\n"
                "Codigo de equipo: {}\n"
                "Telefono: {}\n"
                "Ciudad: {}\n"
                "Barrio: {}\n\n"
                "Usa /admin para revisarlo."
            ).format(full_name, document_number, team_name, team_code, phone, city, barrio)
        )
        _schedule_important_alerts(
            context,
            alert_key="admin_registration_{}".format(admin_id),
            chat_id=ADMIN_USER_ID,
            reminder_text=(
                "Recordatorio importante:\n"
                "El registro de administrador local #{} sigue pendiente.\n"
                "Revisa /admin."
            ).format(admin_id),
        )
    except Exception as e:
        print("[WARN] No se pudo notificar al admin plataforma:", e)

    update.message.reply_text(
        "Registro de Administrador Local recibido.\n"
        "Estado: PENDING\n\n"
        f"Dirección residencia: {residence_address}\n"
        f"Coordenadas: {residence_lat}, {residence_lng}\n\n"
        f"Tu CÓDIGO DE EQUIPO es: {team_code}\n"
        "Compártelo con los repartidores que quieras vincular a tu equipo.\n\n"
        "Recuerda: para ser aprobado debes registrar 10 repartidores con recarga mínima de 5000 cada uno."
    )

    context.user_data.clear()
    return ConversationHandler.END
    
        
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
            print("[ERROR] admins_pendientes:", e)
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
            print("[ERROR] admin_admins_registrados:", e)
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
        adm_full_name = admin_obj.get("full_name") or "-"
        adm_phone = admin_obj.get("phone") or "-"
        adm_city = admin_obj.get("city") or "-"
        adm_barrio = admin_obj.get("barrio") or "-"
        adm_team_name = admin_obj.get("team_name") or "-"
        adm_document = admin_obj.get("document_number") or "-"
        adm_team_code = admin_obj.get("team_code") or "-"
        adm_status = admin_obj.get("status") or "-"

        # Tipo de admin
        tipo_admin = "PLATAFORMA" if adm_team_code == "PLATFORM" else "ADMIN LOCAL"

        # Contadores
        num_couriers = count_admin_couriers(adm_id)
        num_couriers_balance = count_admin_couriers_with_min_balance(adm_id, 5000)
        perm = get_admin_reference_validator_permission(adm_id)
        perm_status = perm["status"] if perm else "INACTIVE"

        residence_address = admin_obj.get("residence_address")
        residence_lat = admin_obj.get("residence_lat")
        residence_lng = admin_obj.get("residence_lng")
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
            "Mensajeros con saldo >= 5000: {}"
        ).format(
            adm_id, adm_full_name, adm_team_name, adm_team_code,
            adm_city, adm_barrio, adm_phone, adm_document, adm_status, tipo_admin,
            residence_address or "No registrada",
            residence_location,
            maps_line,
            num_couriers, num_couriers_balance
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

        if admin_obj.get("team_code") == "PLATFORM":
            query.answer("No puedes modificar a un admin de plataforma")
            return

        # Aplicar cambio
        update_admin_status_by_id(adm_id, nuevo_status, changed_by=f"tg:{update.effective_user.id}")
        query.answer("Estado actualizado a {}".format(nuevo_status))

        # Recargar el detalle
        admin_obj = get_admin_by_id(adm_id)
        adm_full_name = admin_obj.get("full_name") or "-"
        adm_phone = admin_obj.get("phone") or "-"
        adm_city = admin_obj.get("city") or "-"
        adm_barrio = admin_obj.get("barrio") or "-"
        adm_team_name = admin_obj.get("team_name") or "-"
        adm_document = admin_obj.get("document_number") or "-"
        adm_team_code = admin_obj.get("team_code") or "-"
        adm_status = admin_obj.get("status") or "-"

        tipo_admin = "PLATAFORMA" if adm_team_code == "PLATFORM" else "ADMIN LOCAL"
        num_couriers = count_admin_couriers(adm_id)
        num_couriers_balance = count_admin_couriers_with_min_balance(adm_id, 5000)
        perm = get_admin_reference_validator_permission(adm_id)
        perm_status = perm["status"] if perm else "INACTIVE"

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
            "Estado actualizado a {}"
        ).format(
            adm_id, adm_full_name, adm_team_name, adm_team_code,
            adm_city, adm_barrio, adm_phone, adm_document, adm_status, tipo_admin,
            num_couriers, num_couriers_balance, nuevo_status
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
        # REJECTED: sin botones de accion (estado terminal)
        keyboard.append([InlineKeyboardButton("⬅️ Volver a la lista", callback_data="admin_admins_registrados")])
        keyboard.append([InlineKeyboardButton("⬅️ Volver al Panel", callback_data="admin_volver_panel")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
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
        texto = (
            "Aliado ID: {}\n"
            "Negocio: {}\n"
            "Propietario: {}\n"
            "Telefono: {}\n"
            "Ciudad/Barrio: {} / {}\n"
            "Saldo por vínculo: {}"
        ).format(ally_id, business_name, owner_name, phone, city, barrio, balance)
        keyboard = [
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

        adm_full_name = admin_obj.get("full_name") or "-"
        adm_team_name = admin_obj.get("team_name") or "-"
        adm_team_code = admin_obj.get("team_code") or "-"
        adm_status = admin_obj.get("status") or "-"
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

        # Notificar al administrador aprobado (pero aclarando que NO puede operar aún)
        try:
            admin = get_admin_by_id(admin_id)
            admin_user_db_id = admin["user_id"]

            u = get_user_by_id(admin_user_db_id)
            if u:
                admin_telegram_id = u["telegram_id"]

                msg = (
                    "✅ Tu cuenta de Administrador Local ha sido APROBADA.\n\n"
                    "IMPORTANTE: La aprobación no significa que ya puedas operar.\n"
                    "Para operar debes cumplir los requisitos.\n\n"
                    "Requisitos para operar:\n"
                    "1) Tener mínimo 10 repartidores vinculados a tu equipo.\n"
                    "2) Cada uno debe estar APROBADO y con saldo por vínculo >= 5000.\n"
                    "3) Mantener tu cuenta activa y cumplir las reglas de la plataforma.\n\n"
                    "Cuando intentes usar funciones operativas, el sistema validará estos requisitos."
                )
                context.bot.send_message(chat_id=admin_telegram_id, text=msg)

        except Exception as e:
            print("[WARN] No se pudo notificar al admin aprobado:", e)

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


def cancel_conversacion(update, context):
    """Cierra cualquier conversación activa y muestra menú principal."""
    try:
        context.user_data.clear()
    except Exception:
        pass

    # Responder según sea mensaje o callback
    if getattr(update, "callback_query", None):
        q = update.callback_query
        q.answer()
        q.edit_message_text("Proceso cancelado.")
    else:
        update.message.reply_text("Proceso cancelado.")

    # Mostrar menú principal
    show_main_menu(update, context, "Menu principal. Selecciona una opcion:")
    return ConversationHandler.END


def cancel_por_texto(update, context):
    """Handler para cuando el usuario escribe 'Cancelar' o 'Volver al menu'."""
    return cancel_conversacion(update, context)


def volver_menu_global(update, context):
    """Handler global para 'Cancelar' o 'Volver al menu' fuera de conversaciones."""
    try:
        context.user_data.clear()
    except Exception:
        pass
    show_main_menu(update, context, "Menu principal. Selecciona una opcion:")


# ----- COTIZADOR INTERNO -----

def cotizar_start(update, context):
    context.user_data.pop("cotizar_pickup", None)
    context.user_data.pop("cotizar_dropoff", None)
    context.user_data.pop("cotizar_ally_id", None)
    keyboard = [
        [InlineKeyboardButton("Por distancia (km)", callback_data="cotizar_modo_km")],
        [InlineKeyboardButton("Por ubicaciones", callback_data="cotizar_modo_ubi")],
    ]
    update.message.reply_text(
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
        loc = get_ally_location_by_id(loc_id)
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


def _cotizar_resolver_ubicacion(update, context):
    """Resuelve ubicacion desde texto o PIN de Telegram. Retorna dict o None."""
    # PIN de Telegram
    if update.message.location:
        loc = update.message.location
        return {"lat": loc.latitude, "lng": loc.longitude, "method": "gps"}

    texto = (update.message.text or "").strip()
    if not texto:
        return None

    return resolve_location(texto)


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

    if loc.get("method") == "geocode" and loc.get("formatted_address"):
        original_text = update.message.text.strip() if update.message and update.message.text else ""
        _mostrar_confirmacion_geocode(
            update.message, context,
            loc, original_text,
            "cotizar_recogida_geo_si", "cotizar_recogida_geo_no",
        )
        return COTIZAR_RECOGIDA

    context.user_data["cotizar_pickup"] = loc
    update.message.reply_text(
        "Recogida registrada.\n\n"
        "Ahora enviame el punto de ENTREGA.\n"
        "Puedes enviar:\n"
        "- Un PIN de ubicacion de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Una direccion de texto"
    )
    return COTIZAR_ENTREGA


def cotizar_recogida_location(update, context):
    """Handler para PIN de Telegram en recogida."""
    return cotizar_recogida(update, context)


def cotizar_recogida_geo_callback(update, context):
    """Maneja confirmacion de geocoding en recogida del cotizador."""
    query = update.callback_query
    query.answer()

    if query.data == "cotizar_recogida_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Intenta /cotizar de nuevo.")
            return COTIZAR_RECOGIDA
        context.user_data["cotizar_pickup"] = {"lat": lat, "lng": lng, "method": "geocode"}
        query.edit_message_text(
            "Recogida confirmada.\n\n"
            "Ahora enviame el punto de ENTREGA.\n"
            "Puedes enviar:\n"
            "- Un PIN de ubicacion de Telegram\n"
            "- Un link de Google Maps\n"
            "- Coordenadas (ej: 4.81,-75.69)\n"
            "- Una direccion de texto"
        )
        return COTIZAR_ENTREGA
    else:  # cotizar_recogida_geo_no
        return _geo_siguiente_o_gps(query, context, "cotizar_recogida_geo_si", "cotizar_recogida_geo_no", COTIZAR_RECOGIDA)


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

    if loc.get("method") == "geocode" and loc.get("formatted_address"):
        original_text = update.message.text.strip() if update.message and update.message.text else ""
        _mostrar_confirmacion_geocode(
            update.message, context,
            loc, original_text,
            "cotizar_entrega_geo_si", "cotizar_entrega_geo_no",
        )
        return COTIZAR_ENTREGA

    pickup = context.user_data.get("cotizar_pickup")
    if not pickup:
        update.message.reply_text("Error: no se encontro el punto de recogida. Usa /cotizar de nuevo.")
        return ConversationHandler.END

    result = get_smart_distance(pickup["lat"], pickup["lng"], loc["lat"], loc["lng"])
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
    context.user_data["cotizar_result_dropoff_lat"] = loc["lat"]
    context.user_data["cotizar_result_dropoff_lng"] = loc["lng"]
    keyboard = [
        [InlineKeyboardButton("Crear pedido con esta ruta", callback_data="cotizar_crear_pedido")],
        [InlineKeyboardButton("Varias entregas (ruta)", callback_data="cotizar_crear_ruta")],
        [InlineKeyboardButton("Solo consulta", callback_data="cotizar_cerrar")],
    ]
    update.message.reply_text(
        f"COTIZACION\n\n"
        f"Distancia: {distance_km:.1f} km\n"
        f"Precio: ${precio:,}\n\n".replace(",", ".")
        + f"{nota_fuente}\n\n"
        + "Deseas crear el pedido?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return COTIZAR_RESULTADO


def cotizar_entrega_location(update, context):
    """Handler para PIN de Telegram en entrega."""
    return cotizar_entrega(update, context)


def cotizar_entrega_geo_callback(update, context):
    """Maneja confirmacion de geocoding en entrega del cotizador."""
    query = update.callback_query
    query.answer()

    if query.data == "cotizar_entrega_geo_si":
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
        return _geo_siguiente_o_gps(query, context, "cotizar_entrega_geo_si", "cotizar_entrega_geo_no", COTIZAR_ENTREGA)


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


def courier_pick_admin_callback(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    # courier_id que acabamos de crear (guardado en courier_confirm)
    courier_id = context.user_data.get("new_courier_id")

    # Opción legacy: no elegir admin -> asignar por defecto a Plataforma
    if data == "courier_pick_admin_none":
        if not courier_id:
            query.edit_message_text(
                "No encontré tu registro reciente para vincular a un equipo.\n"
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

        platform_admin_id = platform_admin["id"]
        try:
            create_admin_courier_link(platform_admin_id, courier_id)
        except Exception as e:
            print("[ERROR] create_admin_courier_link PLATFORM:", e)
            query.edit_message_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
            context.user_data.clear()
            return

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

    if not courier_id:
        query.edit_message_text(
            "No encontré tu registro reciente para vincular a un equipo.\n"
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
        create_admin_courier_link(admin_id, courier_id)
    except Exception as e:
        print("[ERROR] create_admin_courier_link:", e)
        query.edit_message_text("Ocurrió un error creando la solicitud. Intenta más tarde.")
        context.user_data.clear()
        return

    # Notificar al admin local (sin depender de get_user_by_id)
    admin_telegram_id = None
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

    except Exception as e:
        print("[WARN] No se pudo leer admin para notificación:", e)

    if admin_telegram_id:
        try:
            context.bot.send_message(
                chat_id=admin_telegram_id,
                text=(
                    "📥 Nueva solicitud de repartidor para tu equipo.\n\n"
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
            print("[WARN] No se pudo notificar al admin local:", e)

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
        print("[ERROR] get_pending_admins:", e)
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

    residence_address = admin.get("residence_address")
    residence_lat = admin.get("residence_lat")
    residence_lng = admin.get("residence_lng")
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
    cedula_front = admin.get("cedula_front_file_id")
    cedula_back = admin.get("cedula_back_file_id")
    selfie = admin.get("selfie_file_id")
    if cedula_front or cedula_back or selfie:
        try:
            if cedula_front:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_front, caption="Cédula frente")
            if cedula_back:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_back, caption="Cédula reverso")
            if selfie:
                context.bot.send_photo(chat_id=query.message.chat_id, photo=selfie, caption="Selfie")
        except Exception as e:
            print(f"[WARN] No se pudieron enviar fotos del admin {admin_id}: {e}")

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
        try:
            update_admin_status_by_id(admin_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            print("[ERROR] update_admin_status_by_id APPROVED:", e)
            query.edit_message_text("Error aprobando administrador. Revisa logs.")
            return

        _resolve_important_alert(context, "admin_registration_{}".format(admin_id))
        query.edit_message_text("✅ Administrador aprobado (APPROVED).")
        return

    if accion == "rechazar":
        try:
            update_admin_status_by_id(admin_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            print("[ERROR] update_admin_status_by_id REJECTED:", e)
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


# ============================================================
# COMANDO /clientes - AGENDA DE CLIENTES RECURRENTES
# ============================================================

def clientes_cmd(update, context):
    """Comando /clientes - Solo para aliados aprobados."""
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)

    if not db_user:
        update.message.reply_text("Aun no estas registrado. Usa /start primero.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text(
            "Este comando es solo para aliados registrados.\n"
            "Si tienes un negocio, registrate con /soy_aliado."
        )
        return ConversationHandler.END

    if ally["status"] != "APPROVED":
        update.message.reply_text(
            "Tu registro como aliado aun no ha sido aprobado.\n"
            "Cuando tu estado sea APPROVED podras usar esta funcion."
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["active_ally_id"] = ally["id"]

    return clientes_mostrar_menu(update, context)


def clientes_mostrar_menu(update, context, edit_message=False):
    """Muestra el menu principal de clientes."""
    keyboard = [
        [InlineKeyboardButton("Nuevo cliente", callback_data="cust_nuevo")],
        [InlineKeyboardButton("Buscar cliente", callback_data="cust_buscar")],
        [InlineKeyboardButton("Mis clientes", callback_data="cust_lista")],
        [InlineKeyboardButton("Clientes archivados", callback_data="cust_archivados")],
        [InlineKeyboardButton("Cerrar", callback_data="cust_cerrar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "AGENDA DE CLIENTES\n\nSelecciona una opcion:"

    if edit_message and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text, reply_markup=reply_markup)

    return CLIENTES_MENU


def clientes_menu_callback(update, context):
    """Maneja los callbacks del menu de clientes."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("active_ally_id")

    if not ally_id:
        query.edit_message_text("No hay un aliado activo. Regresa al menu e inicia el pedido nuevamente.")
        return ConversationHandler.END

    if data == "cust_nuevo":
        query.edit_message_text("NUEVO CLIENTE\n\nEscribe el nombre del cliente:")
        return CLIENTES_NUEVO_NOMBRE

    elif data == "cust_buscar":
        query.edit_message_text("BUSCAR CLIENTE\n\nEscribe el nombre o telefono a buscar:")
        return CLIENTES_BUSCAR

    elif data == "cust_lista":
        customers = list_ally_customers(ally_id, limit=10, include_inactive=False)
        if not customers:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cust_volver_menu")]]
            query.edit_message_text(
                "No tienes clientes guardados.\n\n"
                "Usa 'Nuevo cliente' para agregar uno.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return CLIENTES_MENU

        keyboard = []
        for c in customers:
            btn_text = f"{c['name']} - {c['phone']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"cust_ver_{c['id']}")])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="cust_volver_menu")])

        query.edit_message_text(
            "MIS CLIENTES\n\nSelecciona un cliente para ver detalles:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_MENU

    elif data == "cust_archivados":
        customers = list_ally_customers(ally_id, limit=20, include_inactive=True)
        archived = [c for c in customers if c["status"] == "INACTIVE"]

        if not archived:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cust_volver_menu")]]
            query.edit_message_text(
                "No tienes clientes archivados.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return CLIENTES_MENU

        keyboard = []
        for c in archived:
            btn_text = f"{c['name']} - {c['phone']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"cust_restaurar_{c['id']}")])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="cust_volver_menu")])

        query.edit_message_text(
            "CLIENTES ARCHIVADOS\n\nSelecciona uno para restaurar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_MENU

    elif data == "cust_volver_menu":
        return clientes_mostrar_menu(update, context, edit_message=True)

    elif data == "cust_cerrar":
        query.edit_message_text("Agenda de clientes cerrada.")
        context.user_data.clear()
        return ConversationHandler.END

    elif data.startswith("cust_ver_"):
        customer_id = int(data.replace("cust_ver_", ""))
        return clientes_ver_cliente(query, context, customer_id)

    elif data.startswith("cust_restaurar_"):
        customer_id = int(data.replace("cust_restaurar_", ""))
        if restore_ally_customer(customer_id, ally_id):
            query.edit_message_text("Cliente restaurado exitosamente.")
        else:
            query.edit_message_text("No se pudo restaurar el cliente.")
        return clientes_mostrar_menu(update, context, edit_message=False)

    return CLIENTES_MENU


def clientes_ver_cliente(query, context, customer_id):
    """Muestra detalles de un cliente y sus opciones."""
    ally_id = context.user_data.get("active_ally_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if not customer:
        query.edit_message_text("Cliente no encontrado.")
        return CLIENTES_MENU

    context.user_data["current_customer_id"] = customer_id

    addresses = list_customer_addresses(customer_id)
    addr_text = ""
    if addresses:
        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            addr_text += f"- {label}: {addr['address_text'][:35]}...\n"
    else:
        addr_text = "Sin direcciones guardadas\n"

    nota_interna = customer["notes"] or "Sin notas"

    keyboard = [
        [InlineKeyboardButton("Direcciones", callback_data="cust_dirs")],
        [InlineKeyboardButton("Editar", callback_data="cust_editar")],
        [InlineKeyboardButton("Archivar", callback_data="cust_archivar")],
        [InlineKeyboardButton("Volver", callback_data="cust_volver_menu")],
    ]

    query.edit_message_text(
        f"Cliente: {customer['name']}\n"
        f"Telefono: {customer['phone']}\n\n"
        f"Nota interna:\n{nota_interna}\n\n"
        f"Direcciones guardadas:\n{addr_text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CLIENTES_VER_CLIENTE


def clientes_ver_cliente_callback(update, context):
    """Maneja callbacks de la vista de cliente."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("active_ally_id")
    customer_id = context.user_data.get("current_customer_id")

    if data == "cust_dirs":
        addresses = list_customer_addresses(customer_id)
        keyboard = []

        for addr in addresses:
            label = addr["label"] or "Sin etiqueta"
            btn_text = f"{label}: {addr['address_text'][:25]}..."
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"cust_dir_ver_{addr['id']}")])

        keyboard.append([InlineKeyboardButton("Agregar direccion", callback_data="cust_dir_nueva")])
        keyboard.append([InlineKeyboardButton("Volver", callback_data=f"cust_ver_{customer_id}")])

        query.edit_message_text(
            "DIRECCIONES DEL CLIENTE\n\nSelecciona una para editar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_VER_CLIENTE

    elif data == "cust_editar":
        keyboard = [
            [InlineKeyboardButton("Editar nombre", callback_data="cust_edit_nombre")],
            [InlineKeyboardButton("Editar telefono", callback_data="cust_edit_telefono")],
            [InlineKeyboardButton("Editar notas", callback_data="cust_edit_notas")],
            [InlineKeyboardButton("Volver", callback_data=f"cust_ver_{customer_id}")],
        ]
        query.edit_message_text(
            "Que deseas editar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_VER_CLIENTE

    elif data == "cust_edit_nombre":
        query.edit_message_text("Escribe el nuevo nombre del cliente:")
        return CLIENTES_EDITAR_NOMBRE

    elif data == "cust_edit_telefono":
        query.edit_message_text("Escribe el nuevo telefono del cliente:")
        return CLIENTES_EDITAR_TELEFONO

    elif data == "cust_edit_notas":
        query.edit_message_text("Escribe las nuevas notas del cliente (o 'ninguna' para borrar):")
        return CLIENTES_EDITAR_NOTAS

    elif data == "cust_archivar":
        if archive_ally_customer(customer_id, ally_id):
            query.edit_message_text("Cliente archivado exitosamente.")
        else:
            query.edit_message_text("No se pudo archivar el cliente.")
        context.user_data.pop("current_customer_id", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    elif data == "cust_dir_nueva":
        query.edit_message_text("NUEVA DIRECCION\n\nEscribe la etiqueta (Casa, Trabajo, Otro):")
        return CLIENTES_DIR_NUEVA_LABEL

    elif data.startswith("cust_dir_ver_"):
        address_id = int(data.replace("cust_dir_ver_", ""))
        address = get_customer_address_by_id(address_id, customer_id)
        if not address:
            query.edit_message_text("Direccion no encontrada.")
            return CLIENTES_VER_CLIENTE

        context.user_data["current_address_id"] = address_id
        label = address["label"] or "Sin etiqueta"
        nota_entrega = address["notes"] or "Sin nota"
        lat = address["lat"]
        lng = address["lng"]

        if lat is not None and lng is not None:
            try:
                context.bot.send_location(
                    chat_id=query.message.chat_id,
                    latitude=float(lat),
                    longitude=float(lng),
                )
            except Exception:
                pass
            coords_text = "Coordenadas: {:.5f}, {:.5f}".format(float(lat), float(lng))
            btn_coords = "Corregir coordenadas"
        else:
            coords_text = "Sin coordenadas"
            btn_coords = "Agregar coordenadas"

        keyboard = [
            [InlineKeyboardButton("Editar", callback_data="cust_dir_editar")],
            [InlineKeyboardButton("Editar nota entrega", callback_data="cust_dir_edit_nota")],
            [InlineKeyboardButton(btn_coords, callback_data="cust_dir_corregir_coords")],
            [InlineKeyboardButton("Archivar", callback_data="cust_dir_archivar")],
            [InlineKeyboardButton("Volver", callback_data="cust_dirs")],
        ]

        query.edit_message_text(
            f"{label}\n"
            f"{address['address_text']}\n\n"
            f"Nota para entrega:\n{nota_entrega}\n\n"
            f"{coords_text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_VER_CLIENTE

    elif data == "cust_dir_corregir_coords":
        query.edit_message_text(
            "Corregir / agregar coordenadas\n\n"
            "Envia un pin de ubicacion de Telegram, un link de Google Maps, "
            "o escribe las coordenadas (ej: 4.81,-75.69).\n\n"
            "Escribe 'cancelar' para volver."
        )
        context.user_data["clientes_geo_mode"] = "corregir_coords"
        return CLIENTES_DIR_CORREGIR_COORDS

    elif data == "cust_dir_editar":
        query.edit_message_text("Escribe la nueva etiqueta (Casa, Trabajo, Otro):")
        return CLIENTES_DIR_EDITAR_LABEL

    elif data == "cust_dir_edit_nota":
        query.edit_message_text(
            "Escribe la nota para entrega.\n"
            "Esta nota sera visible para el repartidor.\n\n"
            "Escribe 'ninguna' para borrar la nota:"
        )
        return CLIENTES_DIR_EDITAR_NOTA

    elif data == "cust_dir_archivar":
        address_id = context.user_data.get("current_address_id")
        if archive_customer_address(address_id, customer_id):
            query.edit_message_text("Direccion archivada.")
        else:
            query.edit_message_text("No se pudo archivar la direccion.")
        context.user_data.pop("current_address_id", None)
        return clientes_ver_cliente(query, context, customer_id)

    elif data.startswith("cust_ver_"):
        cid = int(data.replace("cust_ver_", ""))
        return clientes_ver_cliente(query, context, cid)

    elif data == "cust_volver_menu":
        context.user_data.pop("current_customer_id", None)
        return clientes_mostrar_menu(update, context, edit_message=True)

    return CLIENTES_VER_CLIENTE


def clientes_nuevo_nombre(update, context):
    """Recibe nombre del nuevo cliente."""
    context.user_data["new_customer_name"] = update.message.text.strip()
    update.message.reply_text("Escribe el telefono del cliente:")
    return CLIENTES_NUEVO_TELEFONO


def clientes_nuevo_telefono(update, context):
    """Recibe telefono del nuevo cliente."""
    context.user_data["new_customer_phone"] = update.message.text.strip()
    update.message.reply_text("Escribe notas del cliente (o 'ninguna' si no hay):")
    return CLIENTES_NUEVO_NOTAS


def clientes_nuevo_notas(update, context):
    """Recibe notas del nuevo cliente."""
    notas = update.message.text.strip()
    if notas.lower() == "ninguna":
        notas = None
    context.user_data["new_customer_notes"] = notas
    update.message.reply_text("Escribe la etiqueta de la direccion (Casa, Trabajo, Otro):")
    return CLIENTES_NUEVO_DIRECCION_LABEL


def clientes_nuevo_direccion_label(update, context):
    """Recibe etiqueta de direccion del nuevo cliente."""
    context.user_data["new_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return CLIENTES_NUEVO_DIRECCION_TEXT


def _clientes_resolver_direccion_para_agenda(update, context, texto, cb_si, cb_no, estado):
    """Aplica el mismo pipeline de cotizar para resolver una direccion en agenda."""
    loc = resolve_location(texto)
    if not loc or loc.get("lat") is None or loc.get("lng") is None:
        update.message.reply_text(
            "No pude encontrar esa ubicacion.\n\n"
            "Intenta con:\n"
            "- Un PIN de Telegram\n"
            "- Un link de Google Maps\n"
            "- Coordenadas (ej: 4.81,-75.69)\n"
            "- Direccion con ciudad (ej: Barrio Leningrado, Pereira)"
        )
        return None

    if loc.get("method") == "geocode" and loc.get("formatted_address"):
        context.user_data["clientes_geo_formatted"] = loc.get("formatted_address", "")
        _mostrar_confirmacion_geocode(update.message, context, loc, texto, cb_si, cb_no)
        return estado

    return loc


def clientes_nuevo_direccion_text(update, context):
    """Recibe direccion y guarda el nuevo cliente."""
    address_text = update.message.text.strip()
    ally_id = context.user_data.get("active_ally_id")
    name = context.user_data.get("new_customer_name")
    phone = context.user_data.get("new_customer_phone")
    notes = context.user_data.get("new_customer_notes")
    label = context.user_data.get("new_address_label")

    resolved = _clientes_resolver_direccion_para_agenda(
        update, context, address_text, "cust_geo_si", "cust_geo_no", CLIENTES_NUEVO_DIRECCION_TEXT
    )
    if resolved is None:
        return CLIENTES_NUEVO_DIRECCION_TEXT
    if isinstance(resolved, int):
        context.user_data["clientes_geo_mode"] = "nuevo_cliente"
        context.user_data["clientes_geo_address_input"] = address_text
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    address_to_save = resolved.get("formatted_address") or address_text
    context.user_data["clientes_pending_mode"] = "nuevo_cliente"
    context.user_data["clientes_pending_address_text"] = address_to_save
    context.user_data["clientes_pending_lat"] = lat
    context.user_data["clientes_pending_lng"] = lng
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return CLIENTES_DIR_CIUDAD


def clientes_buscar(update, context):
    """Busca clientes por nombre o telefono."""
    query_text = update.message.text.strip()
    ally_id = context.user_data.get("active_ally_id")

    results = search_ally_customers(ally_id, query_text, limit=10)
    if not results:
        keyboard = [
            [InlineKeyboardButton("Agregar nuevo cliente", callback_data="cust_nuevo")],
            [InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")],
        ]
        update.message.reply_text(
            f"No se encontraron clientes con '{query_text}'.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_MENU

    keyboard = []
    for c in results:
        btn_text = f"{c['name']} - {c['phone']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"cust_ver_{c['id']}")])
    keyboard.append([InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")])

    update.message.reply_text(
        f"Resultados para '{query_text}':",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CLIENTES_MENU


def clientes_editar_nombre(update, context):
    """Actualiza el nombre del cliente."""
    nuevo_nombre = update.message.text.strip()
    ally_id = context.user_data.get("active_ally_id")
    customer_id = context.user_data.get("current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if customer:
        update_ally_customer(customer_id, ally_id, nuevo_nombre, customer["phone"], customer["notes"])
        update.message.reply_text(f"Nombre actualizado a: {nuevo_nombre}")
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_editar_telefono(update, context):
    """Actualiza el telefono del cliente."""
    nuevo_telefono = update.message.text.strip()
    ally_id = context.user_data.get("active_ally_id")
    customer_id = context.user_data.get("current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if customer:
        update_ally_customer(customer_id, ally_id, customer["name"], nuevo_telefono, customer["notes"])
        update.message.reply_text(f"Telefono actualizado a: {nuevo_telefono}")
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_editar_notas(update, context):
    """Actualiza las notas del cliente."""
    nuevas_notas = update.message.text.strip()
    if nuevas_notas.lower() == "ninguna":
        nuevas_notas = None
    ally_id = context.user_data.get("active_ally_id")
    customer_id = context.user_data.get("current_customer_id")
    customer = get_ally_customer_by_id(customer_id, ally_id)

    if customer:
        update_ally_customer(customer_id, ally_id, customer["name"], customer["phone"], nuevas_notas)
        update.message.reply_text("Notas actualizadas.")
    else:
        update.message.reply_text("Error: cliente no encontrado.")

    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_dir_nueva_label(update, context):
    """Recibe etiqueta de nueva direccion."""
    context.user_data["new_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la direccion completa:")
    return CLIENTES_DIR_NUEVA_TEXT


def clientes_dir_nueva_text(update, context):
    """Crea nueva direccion para cliente existente."""
    address_text = update.message.text.strip()
    customer_id = context.user_data.get("current_customer_id")
    label = context.user_data.get("new_address_label")

    resolved = _clientes_resolver_direccion_para_agenda(
        update, context, address_text, "cust_geo_si", "cust_geo_no", CLIENTES_DIR_NUEVA_TEXT
    )
    if resolved is None:
        return CLIENTES_DIR_NUEVA_TEXT
    if isinstance(resolved, int):
        context.user_data["clientes_geo_mode"] = "dir_nueva"
        context.user_data["clientes_geo_address_input"] = address_text
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    address_to_save = resolved.get("formatted_address") or address_text
    context.user_data["clientes_pending_mode"] = "dir_nueva"
    context.user_data["clientes_pending_address_text"] = address_to_save
    context.user_data["clientes_pending_lat"] = lat
    context.user_data["clientes_pending_lng"] = lng
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return CLIENTES_DIR_CIUDAD


def clientes_geo_callback(update, context):
    """Confirma/rechaza geocoding de direccion en agenda de clientes."""
    query = update.callback_query
    query.answer()

    mode = context.user_data.get("clientes_geo_mode")
    if not mode:
        query.edit_message_text("Sesion de geocodificacion expirada. Escribe la direccion nuevamente.")
        return CLIENTES_MENU

    if query.data == "cust_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        context.user_data.pop("clientes_geo_formatted", None)
        if lat is None or lng is None:
            query.edit_message_text("Error: datos perdidos. Escribe la ubicacion nuevamente.")
            return CLIENTES_NUEVO_DIRECCION_TEXT if mode == "nuevo_cliente" else CLIENTES_DIR_NUEVA_TEXT

        if mode == "corregir_coords":
            context.user_data.pop("clientes_geo_mode", None)
            customer_id = context.user_data.get("current_customer_id")
            address_id = context.user_data.get("current_address_id")
            address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
            if not address:
                query.edit_message_text("Error: direccion no encontrada.")
                return clientes_mostrar_menu(update, context, edit_message=True)
            try:
                update_customer_address(
                    address_id=address_id,
                    customer_id=customer_id,
                    label=address["label"],
                    address_text=address["address_text"],
                    city=address["city"] or "",
                    barrio=address["barrio"] or "",
                    notes=address["notes"],
                    lat=lat,
                    lng=lng,
                )
                query.edit_message_text(
                    "Coordenadas actualizadas.\n"
                    "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
                )
            except Exception as e:
                query.edit_message_text("Error al actualizar: {}".format(str(e)))
            return clientes_mostrar_menu(update, context, edit_message=False)

        original_text = context.user_data.get("clientes_geo_address_input", "")
        context.user_data["clientes_pending_mode"] = mode
        context.user_data["clientes_pending_address_text"] = original_text
        context.user_data["clientes_pending_lat"] = lat
        context.user_data["clientes_pending_lng"] = lng
        query.edit_message_text("Escribe la ciudad de la direccion:")
        return CLIENTES_DIR_CIUDAD

    estado = CLIENTES_NUEVO_DIRECCION_TEXT if mode == "nuevo_cliente" else CLIENTES_DIR_NUEVA_TEXT
    return _geo_siguiente_o_gps(query, context, "cust_geo_si", "cust_geo_no", estado)


def clientes_dir_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la direccion:",
        "clientes_pending_city",
        CLIENTES_DIR_CIUDAD,
        CLIENTES_DIR_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector de la direccion:",
        options_hint="",
        set_back_step=False,
    )


def clientes_dir_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la direccion:",
        "clientes_pending_barrio",
        CLIENTES_DIR_BARRIO,
        CLIENTES_MENU,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == CLIENTES_DIR_BARRIO:
        return ok_state
    barrio = context.user_data.get("clientes_pending_barrio", "")

    mode = context.user_data.get("clientes_pending_mode")
    address_text = context.user_data.get("clientes_pending_address_text", "")
    lat = context.user_data.get("clientes_pending_lat")
    lng = context.user_data.get("clientes_pending_lng")
    city = context.user_data.get("clientes_pending_city", "")
    notes = context.user_data.get("clientes_pending_notes")

    if mode == "nuevo_cliente":
        ally_id = context.user_data.get("active_ally_id")
        name = context.user_data.get("new_customer_name")
        phone = context.user_data.get("new_customer_phone")
        customer_notes = context.user_data.get("new_customer_notes")
        label = context.user_data.get("new_address_label")
        try:
            customer_id = create_ally_customer(ally_id, name, phone, customer_notes)
            create_customer_address(customer_id, label, address_text, city=city, barrio=barrio, lat=lat, lng=lng)
            keyboard = [[InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")]]
            update.message.reply_text(
                "Cliente '{}' creado exitosamente.\n\n"
                "Telefono: {}\n"
                "Direccion ({}): {}".format(name, phone, label, address_text),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            update.message.reply_text("Error al crear cliente: {}".format(str(e)))

        for key in [
            "new_customer_name",
            "new_customer_phone",
            "new_customer_notes",
            "new_address_label",
            "clientes_geo_mode",
            "clientes_geo_address_input",
            "clientes_pending_mode",
            "clientes_pending_address_text",
            "clientes_pending_lat",
            "clientes_pending_lng",
            "clientes_pending_city",
            "clientes_pending_barrio",
            "clientes_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return CLIENTES_MENU

    if mode == "dir_nueva":
        customer_id = context.user_data.get("current_customer_id")
        label = context.user_data.get("new_address_label")
        try:
            create_customer_address(customer_id, label, address_text, city=city, barrio=barrio, lat=lat, lng=lng)
            update.message.reply_text("Direccion agregada: {} - {}".format(label, address_text))
        except Exception as e:
            update.message.reply_text("Error: {}".format(str(e)))

        for key in [
            "new_address_label",
            "clientes_geo_mode",
            "clientes_geo_address_input",
            "clientes_pending_mode",
            "clientes_pending_address_text",
            "clientes_pending_lat",
            "clientes_pending_lng",
            "clientes_pending_city",
            "clientes_pending_barrio",
            "clientes_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    if mode == "dir_editar":
        customer_id = context.user_data.get("current_customer_id")
        address_id = context.user_data.get("current_address_id")
        label = context.user_data.get("edit_address_label")
        try:
            update_customer_address(
                address_id=address_id,
                customer_id=customer_id,
                label=label,
                address_text=address_text,
                city=city,
                barrio=barrio,
                notes=notes,
                lat=lat,
                lng=lng,
            )
            update.message.reply_text("Direccion actualizada.")
        except Exception as e:
            update.message.reply_text("Error: {}".format(str(e)))

        for key in [
            "edit_address_label",
            "current_address_id",
            "clientes_pending_mode",
            "clientes_pending_address_text",
            "clientes_pending_lat",
            "clientes_pending_lng",
            "clientes_pending_city",
            "clientes_pending_barrio",
            "clientes_pending_notes",
        ]:
            context.user_data.pop(key, None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    update.message.reply_text("Error: sesion expirada. Intenta de nuevo desde el menu.")
    for key in [
        "clientes_pending_mode",
        "clientes_pending_address_text",
        "clientes_pending_lat",
        "clientes_pending_lng",
        "clientes_pending_city",
        "clientes_pending_barrio",
        "clientes_pending_notes",
    ]:
        context.user_data.pop(key, None)
    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_dir_editar_label(update, context):
    """Recibe nueva etiqueta para editar direccion."""
    context.user_data["edit_address_label"] = update.message.text.strip()
    update.message.reply_text("Escribe la nueva direccion completa:")
    return CLIENTES_DIR_EDITAR_TEXT


def clientes_dir_editar_text(update, context):
    """Actualiza direccion existente."""
    address_text = update.message.text.strip()
    customer_id = context.user_data.get("current_customer_id")
    address_id = context.user_data.get("current_address_id")
    label = context.user_data.get("edit_address_label")

    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("edit_address_label", None)
        context.user_data.pop("current_address_id", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    context.user_data["clientes_pending_mode"] = "dir_editar"
    context.user_data["clientes_pending_address_text"] = address_text
    context.user_data["clientes_pending_lat"] = address.get("lat")
    context.user_data["clientes_pending_lng"] = address.get("lng")
    context.user_data["clientes_pending_notes"] = address.get("notes")
    update.message.reply_text("Escribe la ciudad de la direccion:")
    return CLIENTES_DIR_CIUDAD


def clientes_dir_editar_nota(update, context):
    """Actualiza la nota para entrega de una direccion."""
    nota_text = update.message.text.strip()
    customer_id = context.user_data.get("current_customer_id")
    address_id = context.user_data.get("current_address_id")

    # Obtener la direccion actual para preservar los otros campos
    address = get_customer_address_by_id(address_id, customer_id)
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        return clientes_mostrar_menu(update, context, edit_message=False)

    # Si escribe "ninguna", borrar la nota
    nueva_nota = None if nota_text.lower() == "ninguna" else nota_text

    try:
        update_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"],
            barrio=address["barrio"],
            notes=nueva_nota,
            lat=address["lat"],
            lng=address["lng"]
        )
        if nueva_nota:
            update.message.reply_text("Nota para entrega actualizada.")
        else:
            update.message.reply_text("Nota para entrega eliminada.")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

    context.user_data.pop("current_address_id", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_dir_corregir_coords_handler(update, context):
    """Recibe texto/link para corregir o agregar coordenadas de una direccion de cliente."""
    text = update.message.text.strip()
    if text.lower() == "cancelar":
        context.user_data.pop("clientes_geo_mode", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    customer_id = context.user_data.get("current_customer_id")
    address_id = context.user_data.get("current_address_id")
    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("clientes_geo_mode", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    context.user_data["clientes_geo_mode"] = "corregir_coords"
    context.user_data["clientes_geo_address_input"] = text

    resolved = _clientes_resolver_direccion_para_agenda(
        update, context, text, "cust_geo_si", "cust_geo_no", CLIENTES_DIR_CORREGIR_COORDS
    )
    if resolved is None:
        return CLIENTES_DIR_CORREGIR_COORDS
    if isinstance(resolved, int):
        return resolved

    lat = resolved.get("lat")
    lng = resolved.get("lng")
    if lat is None or lng is None:
        update.message.reply_text("No se pudo obtener coordenadas. Intenta de nuevo o escribe 'cancelar'.")
        return CLIENTES_DIR_CORREGIR_COORDS

    try:
        update_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"] or "",
            barrio=address["barrio"] or "",
            notes=address["notes"],
            lat=lat,
            lng=lng,
        )
        update.message.reply_text(
            "Coordenadas actualizadas.\n"
            "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
        )
    except Exception as e:
        update.message.reply_text("Error al actualizar: {}".format(str(e)))

    context.user_data.pop("clientes_geo_mode", None)
    context.user_data.pop("clientes_geo_address_input", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


def clientes_dir_corregir_coords_location_handler(update, context):
    """Recibe pin GPS de Telegram para corregir o agregar coordenadas de una direccion."""
    loc = update.message.location
    lat = loc.latitude
    lng = loc.longitude
    customer_id = context.user_data.get("current_customer_id")
    address_id = context.user_data.get("current_address_id")
    address = get_customer_address_by_id(address_id, customer_id) if address_id and customer_id else None
    if not address:
        update.message.reply_text("Direccion no encontrada.")
        context.user_data.pop("clientes_geo_mode", None)
        return clientes_mostrar_menu(update, context, edit_message=False)

    try:
        update_customer_address(
            address_id=address_id,
            customer_id=customer_id,
            label=address["label"],
            address_text=address["address_text"],
            city=address["city"] or "",
            barrio=address["barrio"] or "",
            notes=address["notes"],
            lat=lat,
            lng=lng,
        )
        update.message.reply_text(
            "Coordenadas actualizadas.\n"
            "Lat: {:.6f}, Lng: {:.6f}".format(float(lat), float(lng))
        )
    except Exception as e:
        update.message.reply_text("Error al actualizar: {}".format(str(e)))

    context.user_data.pop("clientes_geo_mode", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


# =========================
# Panel "Agenda del aliado" (/agenda)
# =========================

def agenda_cmd(update, context):
    """Comando /agenda: panel principal del aliado."""
    user_db_id = get_user_db_id_from_update(update)
    ally = get_ally_by_user_id(user_db_id)

    if not ally:
        update.message.reply_text(
            "No tienes perfil de aliado registrado.\n"
            "Usa /soy_aliado para registrarte."
        )
        return ConversationHandler.END

    status = ally["status"]
    if status != "APPROVED":
        update.message.reply_text(
            "Tu cuenta de aliado no esta aprobada.\n"
            "Cuando tu estado sea APPROVED podras usar esta funcion."
        )
        return ConversationHandler.END

    context.user_data.clear()
    ally_id = ally["id"]
    context.user_data["active_ally_id"] = ally_id
    context.user_data["ally_locs_ally_id"] = ally_id
    context.user_data["ally"] = {"id": ally_id}

    return agenda_mostrar_menu(update, context)


def agenda_mostrar_menu(update, context, edit_message=False):
    """Muestra menu principal de la agenda del aliado."""
    keyboard = [
        [InlineKeyboardButton("Clientes", callback_data="agenda_clientes")],
        [InlineKeyboardButton("Direcciones de recogida", callback_data="agenda_pickups")],
        [InlineKeyboardButton("Cerrar", callback_data="agenda_cerrar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "Agenda del aliado\n\n"
        "Desde aqui puedes administrar tus clientes y direcciones "
        "guardadas para agilizar tus pedidos."
    )

    if edit_message and update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text, reply_markup=reply_markup)

    return DIRECCIONES_MENU


def agenda_menu_callback(update, context):
    """Maneja callbacks del menu principal de la agenda."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "agenda_pickups":
        return agenda_pickups_mostrar(query, context)

    elif data == "agenda_clientes":
        return clientes_mostrar_menu(update, context, edit_message=True)

    elif data == "agenda_cerrar":
        query.edit_message_text("Agenda cerrada.")
        return ConversationHandler.END

    elif data == "agenda_volver":
        return agenda_mostrar_menu(update, context, edit_message=True)

    return DIRECCIONES_MENU


def agenda_pickups_mostrar(query, context):
    """Muestra lista de direcciones de recogida del aliado con botones por ubicacion."""
    ally_id = context.user_data.get("active_ally_id")
    if not ally_id:
        query.edit_message_text("Error: no hay aliado activo.")
        return ConversationHandler.END

    locations = get_ally_locations(ally_id)
    keyboard = []

    if locations:
        for loc in locations[:10]:
            label = (loc.get("label") or "Sin nombre")[:25]
            tags = []
            if loc.get("is_default"):
                tags.append("BASE")
            tag_str = " [{}]".format(", ".join(tags)) if tags else ""
            keyboard.append([InlineKeyboardButton(
                "{}{}".format(label, tag_str),
                callback_data="agenda_pickup_ver_{}".format(loc["id"])
            )])
        keyboard.append([InlineKeyboardButton("+ Agregar nueva", callback_data="agenda_pickups_nueva")])
        texto = "PUNTOS DE RECOGIDA\n\nSelecciona uno para ver opciones o agregar nuevo:"
    else:
        keyboard.append([InlineKeyboardButton("+ Agregar primera ubicacion", callback_data="agenda_pickups_nueva")])
        texto = "PUNTOS DE RECOGIDA\n\nAun no tienes ubicaciones de recogida guardadas."

    keyboard.append([InlineKeyboardButton("Volver", callback_data="agenda_volver")])
    query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
    return DIRECCIONES_PICKUPS


def agenda_pickups_callback(update, context):
    """Maneja callbacks de la lista de recogidas."""
    query = update.callback_query
    query.answer()
    data = query.data

    ally_id = context.user_data.get("active_ally_id")
    if not ally_id:
        query.edit_message_text("Error: no hay aliado activo.")
        return ConversationHandler.END

    if data == "agenda_volver":
        return agenda_mostrar_menu(update, context, edit_message=True)

    elif data == "agenda_pickup_lista" or data == "agenda_pickup_del_cancel":
        return agenda_pickups_mostrar(query, context)

    elif data == "agenda_pickups_nueva":
        query.edit_message_text(
            "Nueva ubicacion de recogida\n\n"
            "Envia la ubicacion (PIN de Telegram), "
            "pega el enlace (Google Maps/WhatsApp) "
            "o escribe coordenadas (lat,lng).\n\n"
            "La ubicacion es obligatoria para continuar."
        )
        return DIRECCIONES_PICKUP_NUEVA_UBICACION

    elif data.startswith("agenda_pickup_ver_"):
        try:
            loc_id = int(data.split("agenda_pickup_ver_")[1])
        except (ValueError, IndexError):
            return agenda_pickups_mostrar(query, context)
        loc = get_ally_location_by_id(loc_id, ally_id)
        if not loc:
            return agenda_pickups_mostrar(query, context)
        label = loc.get("label") or "Sin nombre"
        address = loc.get("address") or "-"
        gps = "{}, {}".format(round(loc["lat"], 5), round(loc["lng"], 5)) if loc.get("lat") else "Sin GPS"
        is_base = bool(loc.get("is_default"))
        detalle = "{}\n\nDireccion: {}\nGPS: {}".format(label, address, gps)
        keyboard = []
        if not is_base:
            keyboard.append([InlineKeyboardButton(
                "Marcar como base",
                callback_data="agenda_pickup_base_{}".format(loc_id)
            )])
        keyboard.append([InlineKeyboardButton(
            "Eliminar",
            callback_data="agenda_pickup_del_{}".format(loc_id)
        )])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="agenda_pickup_lista")])
        query.edit_message_text(detalle, reply_markup=InlineKeyboardMarkup(keyboard))
        return DIRECCIONES_PICKUPS

    elif data.startswith("agenda_pickup_base_"):
        try:
            loc_id = int(data.split("agenda_pickup_base_")[1])
        except (ValueError, IndexError):
            return agenda_pickups_mostrar(query, context)
        set_default_ally_location(loc_id, ally_id)
        return agenda_pickups_mostrar(query, context)

    elif data.startswith("agenda_pickup_del_confirm_"):
        try:
            loc_id = int(data.split("agenda_pickup_del_confirm_")[1])
        except (ValueError, IndexError):
            return agenda_pickups_mostrar(query, context)
        delete_ally_location(loc_id, ally_id)
        return agenda_pickups_mostrar(query, context)

    elif data.startswith("agenda_pickup_del_"):
        try:
            loc_id = int(data.split("agenda_pickup_del_")[1])
        except (ValueError, IndexError):
            return agenda_pickups_mostrar(query, context)
        loc = get_ally_location_by_id(loc_id, ally_id)
        label = (loc.get("label") or "esta ubicacion") if loc else "esta ubicacion"
        keyboard = [
            [InlineKeyboardButton(
                "Confirmar eliminacion",
                callback_data="agenda_pickup_del_confirm_{}".format(loc_id)
            )],
            [InlineKeyboardButton("Cancelar", callback_data="agenda_pickup_del_cancel")],
        ]
        query.edit_message_text(
            "Eliminar '{}'?\n\nEsta accion no se puede deshacer.".format(label),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DIRECCIONES_PICKUPS

    return DIRECCIONES_PICKUPS


def direcciones_pickup_nueva_ubicacion(update, context):
    """Captura ubicacion (link o coords) para nueva recogida."""
    text = update.message.text.strip()

    if text.lower() == "omitir":
        update.message.reply_text(
            "No puedes omitir la ubicacion.\n"
            "Envia un PIN, link de Google Maps o coordenadas (lat,lng)."
        )
        return DIRECCIONES_PICKUP_NUEVA_UBICACION

    # Intentar extraer coordenadas de link de Google Maps
    lat, lng = None, None
    import re
    # Patron para Google Maps: @lat,lng o ?q=lat,lng o /lat,lng
    patterns = [
        r'@(-?\d+\.?\d*),(-?\d+\.?\d*)',
        r'\?q=(-?\d+\.?\d*),(-?\d+\.?\d*)',
        r'/(-?\d+\.?\d*),(-?\d+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
                break
            except ValueError:
                continue

    # Si no es link, intentar como coords directas
    if lat is None and ',' in text:
        try:
            parts = text.split(',')
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
        except (ValueError, IndexError):
            pass

    if lat is not None and lng is not None:
        context.user_data["new_pickup_lat"] = lat
        context.user_data["new_pickup_lng"] = lng
        update.message.reply_text(
            f"Coordenadas capturadas: {lat:.6f}, {lng:.6f}\n\n"
            "Escribe la direccion de recogida (texto):"
        )
        return DIRECCIONES_PICKUP_NUEVA_DETALLES
    else:
        update.message.reply_text(
            "No se detectaron coordenadas validas.\n"
            "Envia un PIN, link de Google Maps o coordenadas (lat,lng)."
        )
        return DIRECCIONES_PICKUP_NUEVA_UBICACION


def direcciones_pickup_nueva_ubicacion_location_handler(update, context):
    """Maneja ubicacion nativa de Telegram (PIN) para nueva recogida en /agenda."""
    loc = update.message.location
    context.user_data["new_pickup_lat"] = loc.latitude
    context.user_data["new_pickup_lng"] = loc.longitude
    update.message.reply_text(
        f"Coordenadas capturadas: {loc.latitude:.6f}, {loc.longitude:.6f}\n\n"
        "Escribe la direccion de recogida (texto):"
    )
    return DIRECCIONES_PICKUP_NUEVA_DETALLES


def direcciones_pickup_nueva_detalles(update, context):
    """Captura direccion en texto y pregunta si guardar."""
    text = update.message.text.strip()
    if not text:
        update.message.reply_text("Por favor escribe la direccion de recogida:")
        return DIRECCIONES_PICKUP_NUEVA_DETALLES

    context.user_data["new_pickup_address"] = text

    # Sugerir ciudad basada en la base del aliado (pero se pregunta siempre)
    ally_id = context.user_data.get("active_ally_id")
    default_city = "Pereira"
    if ally_id:
        default_loc = get_default_ally_location(ally_id)
        if default_loc and default_loc.get("city"):
            default_city = default_loc["city"]
    update.message.reply_text("Ciudad de la recogida (ej: {}).".format(default_city))
    return DIRECCIONES_PICKUP_NUEVA_CIUDAD


def direcciones_pickup_nueva_ciudad(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la recogida:",
        "new_pickup_city",
        DIRECCIONES_PICKUP_NUEVA_CIUDAD,
        DIRECCIONES_PICKUP_NUEVA_BARRIO,
        flow=None,
        next_prompt="Barrio o sector de la recogida:",
        options_hint="",
        set_back_step=False,
    )


def direcciones_pickup_nueva_barrio(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la recogida:",
        "new_pickup_barrio",
        DIRECCIONES_PICKUP_NUEVA_BARRIO,
        DIRECCIONES_PICKUP_GUARDAR,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == DIRECCIONES_PICKUP_NUEVA_BARRIO:
        return ok_state
    barrio = context.user_data.get("new_pickup_barrio", "")
    address = context.user_data.get("new_pickup_address", "")
    city = context.user_data.get("new_pickup_city", "")

    keyboard = [
        [InlineKeyboardButton("Si, guardar", callback_data="dir_pickup_guardar_si")],
        [InlineKeyboardButton("Cancelar", callback_data="dir_pickup_guardar_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Direccion: {}\nCiudad: {}\nBarrio o sector: {}\n\nDeseas guardar esta direccion?".format(address, city, barrio),
        reply_markup=reply_markup
    )
    return DIRECCIONES_PICKUP_GUARDAR


def direcciones_pickup_guardar_callback(update, context):
    """Guarda o cancela la nueva direccion de recogida."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "dir_pickup_guardar_si":
        ally_id = context.user_data.get("active_ally_id")
        if not ally_id:
            query.edit_message_text("Error: no hay aliado activo.")
            return ConversationHandler.END

        address = context.user_data.get("new_pickup_address", "")
        city = context.user_data.get("new_pickup_city", "Pereira")
        lat = context.user_data.get("new_pickup_lat")
        lng = context.user_data.get("new_pickup_lng")

        new_loc_id = create_ally_location(
            ally_id=ally_id,
            label=address[:30],
            address=address,
            city=city,
            barrio=context.user_data.get("new_pickup_barrio", ""),
            phone="",
            is_default=False,
            lat=lat,
            lng=lng,
        )

        if new_loc_id:
            query.edit_message_text("Direccion guardada correctamente.")
        else:
            query.edit_message_text("Error al guardar la direccion.")

        # Limpiar datos temporales
        context.user_data.pop("new_pickup_address", None)
        context.user_data.pop("new_pickup_city", None)
        context.user_data.pop("new_pickup_barrio", None)
        context.user_data.pop("new_pickup_lat", None)
        context.user_data.pop("new_pickup_lng", None)

        # Volver a mostrar lista de pickups
        return agenda_pickups_mostrar(query, context)

    else:
        query.edit_message_text("Operacion cancelada.")
        return agenda_mostrar_menu(update, context, edit_message=True)


# ConversationHandler para /agenda
agenda_conv = ConversationHandler(
    entry_points=[
        CommandHandler("agenda", agenda_cmd),
        MessageHandler(Filters.regex(r'^Agenda$'), agenda_cmd),
    ],
    states={
        DIRECCIONES_MENU: [
            CallbackQueryHandler(agenda_menu_callback, pattern=r"^agenda_(pickups|clientes|cerrar|volver)$"),
        ],
        DIRECCIONES_PICKUPS: [
            CallbackQueryHandler(
                agenda_pickups_callback,
                pattern=r"^agenda_(volver|pickups_nueva|pickup_lista|pickup_del_cancel|pickup_ver_\d+|pickup_base_\d+|pickup_del_confirm_\d+|pickup_del_\d+)$"
            )
        ],
        DIRECCIONES_PICKUP_NUEVA_UBICACION: [
            MessageHandler(Filters.location, direcciones_pickup_nueva_ubicacion_location_handler),
            MessageHandler(Filters.text & ~Filters.command, direcciones_pickup_nueva_ubicacion)
        ],
        DIRECCIONES_PICKUP_NUEVA_DETALLES: [
            MessageHandler(Filters.text & ~Filters.command, direcciones_pickup_nueva_detalles)
        ],
        DIRECCIONES_PICKUP_NUEVA_CIUDAD: [
            MessageHandler(Filters.text & ~Filters.command, direcciones_pickup_nueva_ciudad)
        ],
        DIRECCIONES_PICKUP_NUEVA_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command, direcciones_pickup_nueva_barrio)
        ],
        DIRECCIONES_PICKUP_GUARDAR: [
            CallbackQueryHandler(direcciones_pickup_guardar_callback, pattern=r"^dir_pickup_guardar_")
        ],
        CLIENTES_MENU: [
            CallbackQueryHandler(clientes_menu_callback, pattern=r"^cust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_\d+|restaurar_\d+)$")
        ],
        CLIENTES_NUEVO_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_nombre)
        ],
        CLIENTES_NUEVO_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_telefono)
        ],
        CLIENTES_NUEVO_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_notas)
        ],
        CLIENTES_NUEVO_DIRECCION_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_direccion_label)
        ],
        CLIENTES_NUEVO_DIRECCION_TEXT: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_direccion_text)
        ],
        CLIENTES_BUSCAR: [
            MessageHandler(Filters.text & ~Filters.command, clientes_buscar)
        ],
        CLIENTES_VER_CLIENTE: [
            CallbackQueryHandler(clientes_ver_cliente_callback, pattern=r"^cust_(dirs|editar|edit_nombre|edit_telefono|edit_notas|archivar|dir_nueva|dir_ver_\d+|dir_editar|dir_edit_nota|dir_archivar|dir_corregir_coords|ver_\d+|volver_menu)$")
        ],
        CLIENTES_EDITAR_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_nombre)
        ],
        CLIENTES_EDITAR_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_telefono)
        ],
        CLIENTES_EDITAR_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_notas)
        ],
        CLIENTES_DIR_NUEVA_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_nueva_label)
        ],
        CLIENTES_DIR_NUEVA_TEXT: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_nueva_text)
        ],
        CLIENTES_DIR_EDITAR_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_editar_label)
        ],
        CLIENTES_DIR_EDITAR_TEXT: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_editar_text)
        ],
        CLIENTES_DIR_CIUDAD: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_ciudad_handler)
        ],
        CLIENTES_DIR_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_barrio_handler)
        ],
        CLIENTES_DIR_EDITAR_NOTA: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_editar_nota)
        ],
        CLIENTES_DIR_CORREGIR_COORDS: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.location, clientes_dir_corregir_coords_location_handler),
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_corregir_coords_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)


# ConversationHandler para /clientes
clientes_conv = ConversationHandler(
    entry_points=[
        CommandHandler("clientes", clientes_cmd),
        MessageHandler(Filters.regex(r'^Clientes$'), clientes_cmd),
    ],
    states={
        CLIENTES_MENU: [
            CallbackQueryHandler(clientes_menu_callback, pattern=r"^cust_(nuevo|buscar|lista|archivados|cerrar|volver_menu|ver_\d+|restaurar_\d+)$")
        ],
        CLIENTES_NUEVO_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_nombre)
        ],
        CLIENTES_NUEVO_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_telefono)
        ],
        CLIENTES_NUEVO_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_notas)
        ],
        CLIENTES_NUEVO_DIRECCION_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_direccion_label)
        ],
        CLIENTES_NUEVO_DIRECCION_TEXT: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_direccion_text)
        ],
        CLIENTES_BUSCAR: [
            MessageHandler(Filters.text & ~Filters.command, clientes_buscar)
        ],
        CLIENTES_VER_CLIENTE: [
            CallbackQueryHandler(clientes_ver_cliente_callback, pattern=r"^cust_(dirs|editar|edit_nombre|edit_telefono|edit_notas|archivar|dir_nueva|dir_ver_\d+|dir_editar|dir_edit_nota|dir_archivar|dir_corregir_coords|ver_\d+|volver_menu)$")
        ],
        CLIENTES_EDITAR_NOMBRE: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_nombre)
        ],
        CLIENTES_EDITAR_TELEFONO: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_telefono)
        ],
        CLIENTES_EDITAR_NOTAS: [
            MessageHandler(Filters.text & ~Filters.command, clientes_editar_notas)
        ],
        CLIENTES_DIR_NUEVA_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_nueva_label)
        ],
        CLIENTES_DIR_NUEVA_TEXT: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_nueva_text)
        ],
        CLIENTES_DIR_EDITAR_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_editar_label)
        ],
        CLIENTES_DIR_EDITAR_TEXT: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_editar_text)
        ],
        CLIENTES_DIR_EDITAR_NOTA: [
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_editar_nota)
        ],
        CLIENTES_DIR_CORREGIR_COORDS: [
            CallbackQueryHandler(clientes_geo_callback, pattern=r"^cust_geo_(si|no)$"),
            MessageHandler(Filters.location, clientes_dir_corregir_coords_location_handler),
            MessageHandler(Filters.text & ~Filters.command, clientes_dir_corregir_coords_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)


ally_conv = ConversationHandler(
    entry_points=[CommandHandler("soy_aliado", soy_aliado)],
    states={
        ALLY_NAME: [MessageHandler(Filters.text & ~Filters.command, ally_name)],
        ALLY_OWNER: [MessageHandler(Filters.text & ~Filters.command, ally_owner)],
        ALLY_DOCUMENT: [MessageHandler(Filters.text & ~Filters.command, ally_document)],
        ALLY_PHONE: [MessageHandler(Filters.text & ~Filters.command, ally_phone)],
        ALLY_CITY: [MessageHandler(Filters.text & ~Filters.command, ally_city)],
        ALLY_BARRIO: [MessageHandler(Filters.text & ~Filters.command, ally_barrio)],
        ALLY_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, ally_address)],
        ALLY_UBICACION: [
            CallbackQueryHandler(ally_geo_ubicacion_callback, pattern=r"^ally_geo_"),
            MessageHandler(Filters.location, ally_ubicacion_location_handler),
            MessageHandler(Filters.text & ~Filters.command, ally_ubicacion_handler),
        ],
        ALLY_CONFIRM: [MessageHandler(Filters.text & ~Filters.command, ally_confirm)],
        ALLY_TEAM: [CallbackQueryHandler(ally_team_callback, pattern=r"^ally_team:")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        CommandHandler("menu", menu),
        MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)

courier_conv = ConversationHandler(
    entry_points=[CommandHandler("soy_repartidor", soy_repartidor)],
    states={
        COURIER_FULLNAME: [
            MessageHandler(Filters.text & ~Filters.command, courier_fullname)
        ],
        COURIER_IDNUMBER: [
            MessageHandler(Filters.text & ~Filters.command, courier_idnumber)
        ],
        COURIER_PHONE: [
            MessageHandler(Filters.text & ~Filters.command, courier_phone)
        ],
        COURIER_CITY: [
            MessageHandler(Filters.text & ~Filters.command, courier_city)
        ],
        COURIER_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command, courier_barrio)
        ],
        COURIER_RESIDENCE_ADDRESS: [
            MessageHandler(Filters.text & ~Filters.command, courier_residence_address)
        ],
        COURIER_RESIDENCE_LOCATION: [
            CallbackQueryHandler(courier_geo_ubicacion_callback, pattern=r"^courier_geo_"),
            MessageHandler(Filters.location, courier_residence_location),
            MessageHandler(Filters.text & ~Filters.command, courier_residence_location),
        ],
        COURIER_PLATE: [
            MessageHandler(Filters.text & ~Filters.command, courier_plate)
        ],
        COURIER_BIKETYPE: [
            MessageHandler(Filters.text & ~Filters.command, courier_biketype)
        ],
        COURIER_CEDULA_FRONT: [
            MessageHandler(Filters.photo, courier_cedula_front),
            MessageHandler(Filters.text & ~Filters.command, courier_cedula_front),
        ],
        COURIER_CEDULA_BACK: [
            MessageHandler(Filters.photo, courier_cedula_back),
            MessageHandler(Filters.text & ~Filters.command, courier_cedula_back),
        ],
        COURIER_SELFIE: [
            MessageHandler(Filters.photo, courier_selfie),
            MessageHandler(Filters.text & ~Filters.command, courier_selfie),
        ],
        COURIER_CONFIRM: [
            MessageHandler(Filters.text & ~Filters.command, courier_confirm)
        ],
        COURIER_TEAM: [
            CallbackQueryHandler(courier_team_callback, pattern=r"^courier_team:")
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        CommandHandler("menu", menu),
        MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)

# ======================================================
# FLUJO NUEVA RUTA (multi-parada)
# ======================================================

def _ruta_limpiar_temp(context):
    """Limpia datos temporales de la parada actual."""
    for k in ["ruta_temp_name", "ruta_temp_phone", "ruta_temp_address",
              "ruta_temp_city", "ruta_temp_barrio", "ruta_temp_lat", "ruta_temp_lng",
              "ruta_temp_customer_id"]:
        context.user_data.pop(k, None)


def _ruta_mostrar_selector_pickup(update_or_query, context):
    """Muestra el selector de punto de recogida para la ruta."""
    ally_id = context.user_data.get("ruta_ally_id")
    keyboard = []
    if ally_id:
        locations = get_ally_locations(ally_id)
        default_loc = next((l for l in locations if l.get("is_default")), None)
        if default_loc:
            label = (default_loc.get("label") or "Base")[:20]
            address = (default_loc.get("address") or "")[:30]
            keyboard.append([InlineKeyboardButton(
                "Usar base: {} - {}".format(label, address),
                callback_data="ruta_pickup_base"
            )])
        if locations:
            keyboard.append([InlineKeyboardButton(
                "Elegir otra ubicacion ({})".format(len(locations)),
                callback_data="ruta_pickup_lista"
            )])
    keyboard.append([InlineKeyboardButton("Nueva direccion de recogida", callback_data="ruta_pickup_nueva")])
    markup = InlineKeyboardMarkup(keyboard)
    text = "NUEVA RUTA\n\nSelecciona el punto de recogida:"
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(text, reply_markup=markup)
    else:
        update_or_query.message.reply_text(text, reply_markup=markup)
    return RUTA_PICKUP_SELECTOR


def _ruta_guardar_pickup(context, location):
    context.user_data["ruta_pickup_location_id"] = location.get("id")
    context.user_data["ruta_pickup_address"] = location.get("address", "")
    context.user_data["ruta_pickup_lat"] = location.get("lat")
    context.user_data["ruta_pickup_lng"] = location.get("lng")


def _ruta_iniciar_parada(update_or_query, context):
    """Muestra el selector de cliente para la proxima parada."""
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    ally_id = context.user_data.get("ruta_ally_id")
    clientes = list_ally_customers(ally_id) if ally_id else []
    activos = [c for c in clientes if c.get("status") == "ACTIVE"]
    keyboard = [[InlineKeyboardButton("Cliente nuevo", callback_data="ruta_cliente_nuevo")]]
    for c in activos[:8]:
        nombre = (c.get("name") or "Sin nombre")[:25]
        phone = c.get("phone") or ""
        keyboard.append([InlineKeyboardButton(
            "{} - {}".format(nombre, phone),
            callback_data="ruta_sel_cust_{}".format(c["id"])
        )])
    markup = InlineKeyboardMarkup(keyboard)
    text = "PARADA {} DE LA RUTA\n\nSelecciona el cliente:".format(n)
    _ruta_limpiar_temp(context)
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(text, reply_markup=markup)
    else:
        update_or_query.message.reply_text(text, reply_markup=markup)
    return RUTA_PARADA_SELECTOR


def _ruta_guardar_parada_actual(context):
    """Guarda los datos temporales de la parada en la lista ruta_paradas."""
    parada = {
        "name": context.user_data.get("ruta_temp_name") or "",
        "phone": context.user_data.get("ruta_temp_phone") or "",
        "address": context.user_data.get("ruta_temp_address") or "",
        "city": context.user_data.get("ruta_temp_city") or "",
        "barrio": context.user_data.get("ruta_temp_barrio") or "",
        "lat": context.user_data.get("ruta_temp_lat"),
        "lng": context.user_data.get("ruta_temp_lng"),
        "customer_id": context.user_data.get("ruta_temp_customer_id"),  # None si es cliente nuevo
    }
    paradas = context.user_data.get("ruta_paradas", [])
    paradas.append(parada)
    context.user_data["ruta_paradas"] = paradas
    _ruta_limpiar_temp(context)


def _ruta_mostrar_mas_paradas(update_or_query, context):
    """Muestra opcion de agregar mas paradas o continuar."""
    paradas = context.user_data.get("ruta_paradas", [])
    n_actual = len(paradas)
    resumen = "RUTA: {} parada(s) agregada(s)\n\n".format(n_actual)
    for i, p in enumerate(paradas, 1):
        resumen += "Parada {}: {} - {}\n".format(
            i, p.get("name") or "Sin nombre", p.get("address") or "Sin direccion"
        )
    if n_actual >= 5:
        resumen += "\nMaximo 5 paradas alcanzado."
        keyboard = [[InlineKeyboardButton("Continuar con {} paradas".format(n_actual), callback_data="ruta_mas_no")]]
    else:
        keyboard = [
            [InlineKeyboardButton("Agregar parada {}".format(n_actual + 1), callback_data="ruta_mas_si")],
            [InlineKeyboardButton("Listo, continuar con {} parada(s)".format(n_actual), callback_data="ruta_mas_no")],
        ]
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(resumen, reply_markup=markup)
    else:
        update_or_query.message.reply_text(resumen, reply_markup=markup)
    return RUTA_MAS_PARADAS


def _ruta_mostrar_confirmacion(update_or_query, context):
    """Muestra el resumen de la ruta con precio desglosado."""
    paradas = context.user_data.get("ruta_paradas", [])
    total_km = context.user_data.get("ruta_distancia_km", 0)
    pickup_address = context.user_data.get("ruta_pickup_address", "No definida")
    precio_info = calcular_precio_ruta(total_km, len(paradas))
    distance_fee = precio_info["distance_fee"]
    additional_fee = precio_info["additional_stops_fee"]
    total_fee = precio_info["total_fee"]
    context.user_data["ruta_precio"] = precio_info
    text = "RUTA DE ENTREGA\n\nRecoge en: {}\n\n".format(pickup_address)
    for i, p in enumerate(paradas, 1):
        text += "Parada {}:\n  Cliente: {} - {}\n  Direccion: {}\n".format(
            i, p.get("name") or "Sin nombre", p.get("phone") or "", p.get("address") or "Sin direccion"
        )
    text += "\nDistancia total: {:.1f} km\n".format(total_km)
    text += "Precio base (distancia): ${:,}\n".format(distance_fee)
    if additional_fee > 0:
        text += "Paradas adicionales ({} x $4,000): ${:,}\n".format(len(paradas) - 1, additional_fee)
    text += "TOTAL: ${:,}".format(total_fee)
    keyboard = [
        [InlineKeyboardButton("Confirmar ruta", callback_data="ruta_confirmar")],
        [InlineKeyboardButton("Cancelar", callback_data="ruta_cancelar")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if hasattr(update_or_query, "edit_message_text"):
        update_or_query.edit_message_text(text, reply_markup=markup)
    else:
        update_or_query.message.reply_text(text, reply_markup=markup)
    return RUTA_CONFIRMACION


def nueva_ruta_desde_menu(update, context):
    """Entry point de nueva_ruta_conv desde boton 'Varias entregas (ruta)' en nuevo_pedido."""
    query = update.callback_query
    query.answer()
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        query.edit_message_text("No estas registrado. Usa /start primero.")
        return ConversationHandler.END
    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        query.edit_message_text("No tienes perfil de aliado.")
        return ConversationHandler.END
    if ally["status"] != "APPROVED":
        query.edit_message_text("Tu registro como aliado no ha sido aprobado aun.")
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data["ruta_ally_id"] = ally["id"]
    context.user_data["ruta_ally"] = ally
    context.user_data["ruta_paradas"] = []
    show_flow_menu(update, context, "Iniciando nueva ruta...")
    return _ruta_mostrar_selector_pickup(query, context)


def nueva_ruta_start(update, context):
    user = update.effective_user
    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)
    if not db_user:
        update.message.reply_text("Aun no estas registrado. Usa /start primero.")
        return ConversationHandler.END
    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text("No tienes perfil de aliado.")
        return ConversationHandler.END
    if ally["status"] != "APPROVED":
        update.message.reply_text("Tu registro como aliado no ha sido aprobado aun.")
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data["ruta_ally_id"] = ally["id"]
    context.user_data["ruta_ally"] = ally
    context.user_data["ruta_paradas"] = []
    show_flow_menu(update, context, "Iniciando nueva ruta...")
    return _ruta_mostrar_selector_pickup(update, context)


def ruta_pickup_selector_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id")
    if data == "ruta_pickup_base":
        default_loc = get_default_ally_location(ally_id)
        if not default_loc or not default_loc.get("lat"):
            query.edit_message_text("Tu ubicacion base no tiene GPS. Elige otra.")
            return _ruta_mostrar_selector_pickup(query, context)
        _ruta_guardar_pickup(context, default_loc)
        return _ruta_iniciar_parada(query, context)
    if data == "ruta_pickup_lista":
        locations = get_ally_locations(ally_id)
        if not locations:
            query.edit_message_text("No tienes ubicaciones guardadas.")
            return _ruta_mostrar_selector_pickup(query, context)
        keyboard = []
        for loc in locations[:8]:
            label = (loc.get("label") or "Sin nombre")[:20]
            address = (loc.get("address") or "")[:25]
            sin_gps = " (sin GPS)" if not loc.get("lat") else ""
            keyboard.append([InlineKeyboardButton(
                "{}: {}{}".format(label, address, sin_gps),
                callback_data="ruta_pickup_usar_{}".format(loc["id"])
            )])
        keyboard.append([InlineKeyboardButton("Volver", callback_data="ruta_pickup_volver_lista")])
        query.edit_message_text(
            "Selecciona el punto de recogida:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return RUTA_PICKUP_LISTA
    if data == "ruta_pickup_nueva":
        query.edit_message_text(
            "NUEVA DIRECCION DE RECOGIDA\n\n"
            "Envia un PIN de ubicacion de Telegram, link de Google Maps o coordenadas (lat,lng)."
        )
        return RUTA_PICKUP_NUEVA_UBICACION
    return RUTA_PICKUP_SELECTOR


def ruta_pickup_lista_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id")
    if data == "ruta_pickup_volver_lista":
        return _ruta_mostrar_selector_pickup(query, context)
    if data.startswith("ruta_pickup_usar_"):
        try:
            loc_id = int(data.replace("ruta_pickup_usar_", ""))
        except ValueError:
            return RUTA_PICKUP_LISTA
        location = get_ally_location_by_id(loc_id, ally_id)
        if not location or not location.get("lat"):
            query.edit_message_text("Esa ubicacion no tiene GPS. Elige otra.")
            return RUTA_PICKUP_LISTA
        _ruta_guardar_pickup(context, location)
        return _ruta_iniciar_parada(query, context)
    return RUTA_PICKUP_LISTA


def ruta_pickup_nueva_ubicacion_handler(update, context):
    text = update.message.text.strip() if update.message.text else ""
    raw = text
    if "http" in text:
        raw = next((t for t in text.split() if t.startswith("http")), text)
    expanded = expand_short_url(raw) or raw
    coords = extract_lat_lng_from_text(expanded)
    if coords:
        context.user_data["ruta_pickup_lat"] = coords[0]
        context.user_data["ruta_pickup_lng"] = coords[1]
        context.user_data["ruta_pickup_location_id"] = None
        update.message.reply_text(
            "Ubicacion recibida. Ahora escribe la descripcion de la direccion de recogida:"
        )
        return RUTA_PICKUP_NUEVA_DETALLES
    geo = resolve_location(text)
    if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
        context.user_data["ruta_pickup_location_id"] = None
        context.user_data["ruta_pickup_geo_formatted"] = geo.get("formatted_address", "")
        _mostrar_confirmacion_geocode(
            update.message, context, geo, text,
            "ruta_pickup_geo_si", "ruta_pickup_geo_no",
        )
        return RUTA_PICKUP_NUEVA_UBICACION
    if geo and geo.get("lat") is not None:
        context.user_data["ruta_pickup_lat"] = geo["lat"]
        context.user_data["ruta_pickup_lng"] = geo["lng"]
        context.user_data["ruta_pickup_location_id"] = None
        update.message.reply_text(
            "Ubicacion recibida. Ahora escribe la descripcion de la direccion de recogida:"
        )
        return RUTA_PICKUP_NUEVA_DETALLES
    update.message.reply_text(
        "No pude encontrar esa ubicacion.\n\n"
        "Intenta con:\n"
        "- Un PIN de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Nombre del lugar o barrio con ciudad"
    )
    return RUTA_PICKUP_NUEVA_UBICACION


def ruta_pickup_geo_callback(update, context):
    """Confirmacion de geocoding para el punto de recogida de la ruta."""
    query = update.callback_query
    query.answer()
    if query.data == "ruta_pickup_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        formatted = context.user_data.pop("ruta_pickup_geo_formatted", "")
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        context.user_data["ruta_pickup_lat"] = lat
        context.user_data["ruta_pickup_lng"] = lng
        if formatted:
            context.user_data["ruta_pickup_address"] = formatted
        query.edit_message_text(
            "Recogida confirmada.\n\nAhora escribe la descripcion de la direccion (o confirma la sugerida):"
        )
        if formatted:
            query.message.reply_text(formatted)
        return RUTA_PICKUP_NUEVA_DETALLES
    return _geo_siguiente_o_gps(
        query, context, "ruta_pickup_geo_si", "ruta_pickup_geo_no", RUTA_PICKUP_NUEVA_UBICACION
    )


def ruta_pickup_nueva_ubicacion_location_handler(update, context):
    loc = update.message.location
    context.user_data["ruta_pickup_lat"] = loc.latitude
    context.user_data["ruta_pickup_lng"] = loc.longitude
    context.user_data["ruta_pickup_location_id"] = None
    update.message.reply_text("Ubicacion recibida. Ahora escribe la descripcion de la direccion de recogida:")
    return RUTA_PICKUP_NUEVA_DETALLES


def ruta_pickup_nueva_detalles_handler(update, context):
    address = update.message.text.strip()
    if not address:
        update.message.reply_text("Escribe la descripcion de la direccion.")
        return RUTA_PICKUP_NUEVA_DETALLES
    context.user_data["ruta_pickup_address"] = address
    update.message.reply_text("Escribe la ciudad del punto de recogida:")
    return RUTA_PICKUP_NUEVA_CIUDAD


def ruta_pickup_nueva_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad del punto de recogida:",
        "ruta_pickup_city",
        RUTA_PICKUP_NUEVA_CIUDAD,
        RUTA_PICKUP_NUEVA_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector del punto de recogida:",
        options_hint="",
        set_back_step=False,
    )


def ruta_pickup_nueva_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector del punto de recogida:",
        "ruta_pickup_barrio",
        RUTA_PICKUP_NUEVA_BARRIO,
        RUTA_PICKUP_GUARDAR,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == RUTA_PICKUP_NUEVA_BARRIO:
        return ok_state
    barrio = context.user_data.get("ruta_pickup_barrio", "")
    address = context.user_data.get("ruta_pickup_address", "")
    keyboard = [
        [InlineKeyboardButton("Si, guardar", callback_data="ruta_pickup_guardar_si")],
        [InlineKeyboardButton("No, solo para esta ruta", callback_data="ruta_pickup_guardar_no")],
    ]
    update.message.reply_text(
        "Deseas guardar '{}' como una de tus ubicaciones?".format(address[:50]),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return RUTA_PICKUP_GUARDAR


def ruta_pickup_guardar_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id")
    if data == "ruta_pickup_guardar_si":
        address = context.user_data.get("ruta_pickup_address", "")
        lat = context.user_data.get("ruta_pickup_lat")
        lng = context.user_data.get("ruta_pickup_lng")
        new_loc_id = create_ally_location(
            ally_id=ally_id,
            label=address[:30],
            address=address,
            city=context.user_data.get("ruta_pickup_city", ""),
            barrio=context.user_data.get("ruta_pickup_barrio", ""),
            phone="",
            is_default=False,
            lat=lat,
            lng=lng,
        )
        context.user_data["ruta_pickup_location_id"] = new_loc_id
        query.edit_message_text("Direccion guardada.")
    else:
        query.edit_message_text("OK, usaremos esta direccion solo para esta ruta.")
    return _ruta_iniciar_parada(query, context)


def ruta_parada_selector_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id")
    _ruta_limpiar_temp(context)
    if data == "ruta_cliente_nuevo":
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text("PARADA {} - CLIENTE NUEVO\n\nEscribe el nombre del cliente:".format(n))
        return RUTA_PARADA_NOMBRE
    if data.startswith("ruta_sel_cust_"):
        try:
            cust_id = int(data.replace("ruta_sel_cust_", ""))
        except ValueError:
            return RUTA_PARADA_SELECTOR
        customer = get_ally_customer_by_id(cust_id, ally_id)
        if not customer:
            query.edit_message_text("Cliente no encontrado.")
            return RUTA_PARADA_SELECTOR
        context.user_data["ruta_temp_customer_id"] = cust_id
        context.user_data["ruta_temp_name"] = customer.get("name") or ""
        context.user_data["ruta_temp_phone"] = customer.get("phone") or ""
        addresses = list_customer_addresses(cust_id)
        activas = [a for a in addresses if a.get("status") == "ACTIVE"]
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        if not activas:
            query.edit_message_text(
                "PARADA {} - {}\n\nNo tiene direcciones guardadas. Escribe la direccion de entrega:".format(
                    n, customer.get("name") or "Cliente"
                )
            )
            return RUTA_PARADA_DIRECCION
        keyboard = []
        for addr in activas[:6]:
            label = (addr.get("label") or addr.get("address_text") or "Direccion")[:30]
            keyboard.append([InlineKeyboardButton(label, callback_data="ruta_sel_addr_{}".format(addr["id"]))])
        keyboard.append([InlineKeyboardButton("Nueva direccion", callback_data="ruta_addr_nueva")])
        query.edit_message_text(
            "PARADA {} - {}\n\nSelecciona la direccion de entrega:".format(n, customer.get("name") or "Cliente"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return RUTA_PARADA_SEL_DIRECCION
    return RUTA_PARADA_SELECTOR


def ruta_parada_sel_direccion_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "ruta_addr_nueva":
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    if data.startswith("ruta_sel_addr_"):
        try:
            addr_id = int(data.replace("ruta_sel_addr_", ""))
        except ValueError:
            return RUTA_PARADA_SEL_DIRECCION
        cust_id = context.user_data.get("ruta_temp_customer_id")
        addr = get_customer_address_by_id(addr_id, cust_id) if cust_id else None
        if not addr:
            query.edit_message_text("Direccion no encontrada.")
            return RUTA_PARADA_SEL_DIRECCION
        context.user_data["ruta_temp_address"] = addr.get("address_text") or ""
        context.user_data["ruta_temp_city"] = addr.get("city") or ""
        context.user_data["ruta_temp_barrio"] = addr.get("barrio") or ""
        context.user_data["ruta_temp_lat"] = addr.get("lat")
        context.user_data["ruta_temp_lng"] = addr.get("lng")
        _ruta_guardar_parada_actual(context)
        return _ruta_mostrar_mas_paradas(query, context)
    return RUTA_PARADA_SEL_DIRECCION


def ruta_parada_nombre_handler(update, context):
    nombre = update.message.text.strip()
    if not nombre:
        update.message.reply_text("Escribe el nombre del cliente.")
        return RUTA_PARADA_NOMBRE
    context.user_data["ruta_temp_name"] = nombre
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    update.message.reply_text(
        "PARADA {} - {}\n\nEscribe el telefono del cliente (solo numeros):".format(n, nombre)
    )
    return RUTA_PARADA_TELEFONO


def ruta_parada_telefono_handler(update, context):
    texto = update.message.text.strip()
    digits = "".join(filter(str.isdigit, texto))
    if len(digits) < 7:
        update.message.reply_text("Ingresa un numero de telefono valido (minimo 7 digitos).")
        return RUTA_PARADA_TELEFONO
    context.user_data["ruta_temp_phone"] = digits
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    nombre = context.user_data.get("ruta_temp_name", "")
    update.message.reply_text(
        "PARADA {} - {}\n\n"
        "Envia la ubicacion GPS (PIN de Telegram o lat,lng) o escribe 'omitir' para ingresar solo la direccion.".format(n, nombre)
    )
    return RUTA_PARADA_UBICACION


def ruta_parada_ubicacion_handler(update, context):
    text = update.message.text.strip()
    if text.lower() == "omitir":
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        update.message.reply_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    raw = text
    if "http" in text:
        raw = next((t for t in text.split() if t.startswith("http")), text)
    expanded = expand_short_url(raw) or raw
    coords = extract_lat_lng_from_text(expanded)
    if coords:
        context.user_data["ruta_temp_lat"] = coords[0]
        context.user_data["ruta_temp_lng"] = coords[1]
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        update.message.reply_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    geo = resolve_location(text)
    if geo and geo.get("method") == "geocode" and geo.get("formatted_address"):
        context.user_data["ruta_parada_geo_formatted"] = geo.get("formatted_address", "")
        _mostrar_confirmacion_geocode(
            update.message, context, geo, text,
            "ruta_parada_geo_si", "ruta_parada_geo_no",
        )
        return RUTA_PARADA_UBICACION
    if geo and geo.get("lat") is not None:
        context.user_data["ruta_temp_lat"] = geo["lat"]
        context.user_data["ruta_temp_lng"] = geo["lng"]
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        update.message.reply_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    update.message.reply_text(
        "No pude encontrar esa ubicacion.\n\n"
        "Intenta con:\n"
        "- Un PIN de Telegram\n"
        "- Un link de Google Maps\n"
        "- Coordenadas (ej: 4.81,-75.69)\n"
        "- Nombre del lugar o barrio con ciudad\n"
        "- O escribe 'omitir' para ingresar solo la direccion."
    )
    return RUTA_PARADA_UBICACION


def ruta_parada_geo_callback(update, context):
    """Confirmacion de geocoding para la ubicacion de una parada de la ruta."""
    query = update.callback_query
    query.answer()
    if query.data == "ruta_parada_geo_si":
        lat = context.user_data.pop("pending_geo_lat", None)
        lng = context.user_data.pop("pending_geo_lng", None)
        formatted = context.user_data.pop("ruta_parada_geo_formatted", "")
        context.user_data.pop("pending_geo_text", None)
        context.user_data.pop("pending_geo_seen", None)
        context.user_data["ruta_temp_lat"] = lat
        context.user_data["ruta_temp_lng"] = lng
        if formatted:
            context.user_data["ruta_temp_address"] = formatted
            query.edit_message_text("Escribe la ciudad de la entrega:")
            return RUTA_PARADA_CIUDAD
        paradas = context.user_data.get("ruta_paradas", [])
        n = len(paradas) + 1
        query.edit_message_text("PARADA {}\n\nEscribe la descripcion de la direccion de entrega:".format(n))
        return RUTA_PARADA_DIRECCION
    return _geo_siguiente_o_gps(
        query, context, "ruta_parada_geo_si", "ruta_parada_geo_no", RUTA_PARADA_UBICACION
    )


def ruta_parada_ubicacion_location_handler(update, context):
    loc = update.message.location
    context.user_data["ruta_temp_lat"] = loc.latitude
    context.user_data["ruta_temp_lng"] = loc.longitude
    paradas = context.user_data.get("ruta_paradas", [])
    n = len(paradas) + 1
    update.message.reply_text("PARADA {}\n\nEscribe la direccion de entrega:".format(n))
    return RUTA_PARADA_DIRECCION


def ruta_parada_direccion_handler(update, context):
    address = update.message.text.strip()
    if not address:
        update.message.reply_text("Escribe la direccion de entrega.")
        return RUTA_PARADA_DIRECCION
    context.user_data["ruta_temp_address"] = address
    update.message.reply_text("Escribe la ciudad de la entrega:")
    return RUTA_PARADA_CIUDAD


def ruta_parada_ciudad_handler(update, context):
    return _handle_text_field_input(
        update,
        context,
        "Por favor escribe la ciudad de la entrega:",
        "ruta_temp_city",
        RUTA_PARADA_CIUDAD,
        RUTA_PARADA_BARRIO,
        flow=None,
        next_prompt="Escribe el barrio o sector de la entrega:",
        options_hint="",
        set_back_step=False,
    )


def ruta_parada_barrio_handler(update, context):
    ok_state = _handle_text_field_input(
        update,
        context,
        "Por favor escribe el barrio o sector de la entrega:",
        "ruta_temp_barrio",
        RUTA_PARADA_BARRIO,
        RUTA_MAS_PARADAS,
        flow=None,
        next_prompt=None,
        options_hint="",
        set_back_step=False,
    )
    if ok_state == RUTA_PARADA_BARRIO:
        return ok_state
    _ruta_guardar_parada_actual(context)
    return _ruta_mostrar_mas_paradas(update, context)


def ruta_mas_paradas_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "ruta_mas_si":
        return _ruta_iniciar_parada(query, context)
    if data == "ruta_mas_no":
        paradas = context.user_data.get("ruta_paradas", [])
        if len(paradas) < 2:
            query.edit_message_text("Debes agregar al menos 2 paradas para crear una ruta.")
            return _ruta_iniciar_parada(query, context)
        pickup_lat = context.user_data.get("ruta_pickup_lat")
        pickup_lng = context.user_data.get("ruta_pickup_lng")
        tiene_gps = (
            pickup_lat is not None and pickup_lng is not None
            and all(p.get("lat") is not None and p.get("lng") is not None for p in paradas)
        )
        if tiene_gps:
            query.edit_message_text("Calculando distancia de la ruta...")
            dist_result = calcular_distancia_ruta_smart(pickup_lat, pickup_lng, paradas)
            if dist_result and dist_result["total_km"] > 0:
                context.user_data["ruta_distancia_km"] = dist_result["total_km"]
                return _ruta_mostrar_confirmacion(query, context)
        query.edit_message_text(
            "DISTANCIA DE LA RUTA\n\n"
            "No tengo GPS de todas las paradas para calcular automaticamente.\n"
            "Ingresa la distancia total de la ruta en km.\n\nEjemplo: 10.5"
        )
        return RUTA_DISTANCIA_KM
    return RUTA_MAS_PARADAS


def ruta_distancia_km_handler(update, context):
    text = update.message.text.strip().replace(",", ".")
    try:
        km = float(text)
        if km <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("Ingresa un numero valido mayor a 0 (ej: 8 o 10.5).")
        return RUTA_DISTANCIA_KM
    context.user_data["ruta_distancia_km"] = round(km, 2)
    return _ruta_mostrar_confirmacion(update, context)


def ruta_confirmacion_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    if data == "ruta_cancelar":
        query.edit_message_text("Ruta cancelada.")
        context.user_data.clear()
        show_main_menu(update, context)
        return ConversationHandler.END
    if data != "ruta_confirmar":
        return RUTA_CONFIRMACION
    ally_id = context.user_data.get("ruta_ally_id")
    paradas = context.user_data.get("ruta_paradas", [])
    precio_info = context.user_data.get("ruta_precio", {})
    if not ally_id or len(paradas) < 2:
        query.edit_message_text("Error: datos incompletos. Empieza de nuevo con 'Nueva ruta'.")
        context.user_data.clear()
        show_main_menu(update, context)
        return ConversationHandler.END
    pickup_address = context.user_data.get("ruta_pickup_address", "")
    pickup_lat = context.user_data.get("ruta_pickup_lat")
    pickup_lng = context.user_data.get("ruta_pickup_lng")
    pickup_location_id = context.user_data.get("ruta_pickup_location_id")
    total_km = context.user_data.get("ruta_distancia_km", 0)
    link = get_approved_admin_link_for_ally(ally_id)
    admin_id_snapshot = link["admin_id"] if link else None
    route_id = create_route(
        ally_id=ally_id,
        pickup_location_id=pickup_location_id,
        pickup_address=pickup_address,
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        total_distance_km=total_km,
        distance_fee=precio_info.get("distance_fee", 0),
        additional_stops_fee=precio_info.get("additional_stops_fee", 0),
        total_fee=precio_info.get("total_fee", 0),
        instructions=None,
        ally_admin_id_snapshot=admin_id_snapshot,
    )
    if not route_id:
        query.edit_message_text("Error al crear la ruta. Intenta de nuevo.")
        show_main_menu(update, context)
        return ConversationHandler.END
    for i, parada in enumerate(paradas, 1):
        create_route_destination(
            route_id=route_id,
            sequence=i,
            customer_name=parada.get("name") or "",
            customer_phone=parada.get("phone") or "",
            customer_address=parada.get("address") or "",
            customer_city=parada.get("city") or "",
            customer_barrio=parada.get("barrio") or "",
            dropoff_lat=parada.get("lat"),
            dropoff_lng=parada.get("lng"),
        )
    count = publish_route_to_couriers(route_id, ally_id, context, admin_id_override=admin_id_snapshot)
    if count > 0:
        base_msg = "Ruta #{} creada exitosamente.\nPronto un repartidor sera asignado.".format(route_id)
    else:
        base_msg = "Ruta #{} creada. No hay repartidores disponibles en este momento.".format(route_id)
    query.edit_message_text(base_msg)

    # Verificar si hay clientes nuevos para ofrecer guardarlos
    nuevos = [p for p in paradas if not p.get("customer_id")]
    if nuevos:
        # Guardar referencia para el callback
        context.user_data["ruta_nuevos_clientes"] = nuevos
        context.user_data["ruta_ally_id_guardar"] = ally_id
        names_list = "\n".join("- {} ({})".format(p["name"], p["phone"]) for p in nuevos if p.get("name"))
        keyboard = [
            [InlineKeyboardButton("Si, guardar", callback_data="ruta_guardar_clientes_si")],
            [InlineKeyboardButton("No", callback_data="ruta_guardar_clientes_no")],
        ]
        query.message.reply_text(
            "Clientes nuevos en esta ruta:\n{}\n\nDeseas guardarlos para futuros pedidos?".format(names_list),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return RUTA_GUARDAR_CLIENTES

    context.user_data.clear()
    show_main_menu(update, context)
    return ConversationHandler.END


def ruta_guardar_clientes_callback(update, context):
    """Maneja la decision de guardar o no los clientes nuevos de la ruta."""
    query = update.callback_query
    query.answer()
    data = query.data
    ally_id = context.user_data.get("ruta_ally_id_guardar")
    nuevos = context.user_data.get("ruta_nuevos_clientes", [])

    if data == "ruta_guardar_clientes_si" and ally_id:
        saved = 0
        for p in nuevos:
            name = p.get("name") or ""
            phone = p.get("phone") or ""
            address = p.get("address") or ""
            if not phone:
                continue
            try:
                existing = get_ally_customer_by_phone(ally_id, phone)
                if existing:
                    customer_id = existing["id"]
                else:
                    customer_id = create_ally_customer(ally_id, name, phone)
                if address:
                    create_customer_address(
                        customer_id, "Principal", address,
                        city=p.get("city") or "",
                        barrio=p.get("barrio") or "",
                        lat=p.get("lat"), lng=p.get("lng"),
                    )
                saved += 1
            except Exception as e:
                print("[WARN] Error guardando cliente de ruta: {}".format(e))
        query.edit_message_text("Se guardaron {} cliente(s) nuevos.".format(saved))
    else:
        query.edit_message_text("Clientes no guardados.")

    context.user_data.clear()
    show_main_menu(update, context)
    return ConversationHandler.END


# Conversacion "Nueva ruta" (multi-parada)
nueva_ruta_conv = ConversationHandler(
    entry_points=[
        MessageHandler(Filters.regex(r'^Nueva ruta$'), nueva_ruta_start),
        CallbackQueryHandler(nueva_ruta_desde_cotizador, pattern=r"^cotizar_ruta_cust_(nuevo|recurrente)$"),
        CallbackQueryHandler(nueva_ruta_desde_menu, pattern=r"^pedido_a_ruta$"),
    ],
    states={
        RUTA_PICKUP_SELECTOR: [
            CallbackQueryHandler(ruta_pickup_selector_callback, pattern=r"^ruta_pickup_(base|lista|nueva)$"),
        ],
        RUTA_PICKUP_LISTA: [
            CallbackQueryHandler(ruta_pickup_lista_callback, pattern=r"^ruta_pickup_(usar_\d+|volver_lista)$"),
        ],
        RUTA_PICKUP_NUEVA_UBICACION: [
            CallbackQueryHandler(ruta_pickup_geo_callback, pattern=r"^ruta_pickup_geo_(si|no)$"),
            MessageHandler(Filters.location, ruta_pickup_nueva_ubicacion_location_handler),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_pickup_nueva_ubicacion_handler),
        ],
        RUTA_PICKUP_NUEVA_DETALLES: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_pickup_nueva_detalles_handler),
        ],
        RUTA_PICKUP_NUEVA_CIUDAD: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_pickup_nueva_ciudad_handler),
        ],
        RUTA_PICKUP_NUEVA_BARRIO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_pickup_nueva_barrio_handler),
        ],
        RUTA_PICKUP_GUARDAR: [
            CallbackQueryHandler(ruta_pickup_guardar_callback, pattern=r"^ruta_pickup_guardar_(si|no)$"),
        ],
        RUTA_PARADA_SELECTOR: [
            CallbackQueryHandler(ruta_parada_selector_callback, pattern=r"^ruta_(cliente_nuevo|sel_cust_\d+)$"),
        ],
        RUTA_PARADA_SEL_DIRECCION: [
            CallbackQueryHandler(ruta_parada_sel_direccion_callback, pattern=r"^ruta_(sel_addr_\d+|addr_nueva)$"),
        ],
        RUTA_PARADA_NOMBRE: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_parada_nombre_handler),
        ],
        RUTA_PARADA_TELEFONO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_parada_telefono_handler),
        ],
        RUTA_PARADA_UBICACION: [
            CallbackQueryHandler(ruta_parada_geo_callback, pattern=r"^ruta_parada_geo_(si|no)$"),
            MessageHandler(Filters.location, ruta_parada_ubicacion_location_handler),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_parada_ubicacion_handler),
        ],
        RUTA_PARADA_DIRECCION: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_parada_direccion_handler),
        ],
        RUTA_PARADA_CIUDAD: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_parada_ciudad_handler),
        ],
        RUTA_PARADA_BARRIO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_parada_barrio_handler),
        ],
        RUTA_MAS_PARADAS: [
            CallbackQueryHandler(ruta_mas_paradas_callback, pattern=r"^ruta_mas_(si|no)$"),
        ],
        RUTA_DISTANCIA_KM: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, ruta_distancia_km_handler),
        ],
        RUTA_CONFIRMACION: [
            CallbackQueryHandler(ruta_confirmacion_callback, pattern=r"^ruta_(confirmar|cancelar)$"),
        ],
        RUTA_GUARDAR_CLIENTES: [
            CallbackQueryHandler(ruta_guardar_clientes_callback, pattern=r"^ruta_guardar_clientes_(si|no)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)


def nuevo_pedido_tras_terms(update, context):
    """Continua el flujo de nuevo_pedido tras aceptar terminos y condiciones."""
    query = update.callback_query
    query.answer()
    telegram_id = query.from_user.id

    tv = get_active_terms_version("ALLY")
    if not tv:
        query.edit_message_text("Terminos no configurados. Contacta soporte.")
        return ConversationHandler.END

    version, url, sha256 = tv
    save_terms_acceptance(telegram_id, "ALLY", version, sha256, query.message.message_id)

    db_user = get_user_by_telegram_id(telegram_id)
    if not db_user:
        query.edit_message_text("Error: usuario no encontrado. Usa /nuevo_pedido.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally or ally["status"] != "APPROVED":
        query.edit_message_text("No se pudo continuar. Usa Nuevo pedido.")
        return ConversationHandler.END

    query.edit_message_text("Aceptacion registrada. Iniciando nuevo pedido...")
    context.user_data.clear()
    context.user_data["ally_id"] = ally["id"]
    context.user_data["active_ally_id"] = ally["id"]
    context.user_data["ally"] = ally

    keyboard = [
        [InlineKeyboardButton("Cliente recurrente", callback_data="pedido_cliente_recurrente")],
        [InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")],
    ]
    last_order = get_last_order_by_ally(ally["id"])
    if last_order:
        keyboard.append([InlineKeyboardButton("Repetir ultimo pedido", callback_data="pedido_repetir_ultimo")])
    keyboard.append([InlineKeyboardButton("Varias entregas (ruta)", callback_data="pedido_a_ruta")])

    update.effective_message.reply_text(
        "CREAR NUEVO PEDIDO\n\nSelecciona una opcion:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PEDIDO_SELECTOR_CLIENTE


# Conversacion para /nuevo_pedido (con selector de cliente recurrente)
nuevo_pedido_conv = ConversationHandler(
    entry_points=[
        CommandHandler("nuevo_pedido", nuevo_pedido),
        MessageHandler(Filters.regex(r'^Nuevo pedido$'), nuevo_pedido),
        CallbackQueryHandler(nuevo_pedido_desde_cotizador, pattern=r"^cotizar_cust_(nuevo|recurrente)$"),
        CallbackQueryHandler(nuevo_pedido_tras_terms, pattern=r"^terms_accept_ALLY$"),
    ],
    states={
        PEDIDO_SELECTOR_CLIENTE: [
            CallbackQueryHandler(pedido_selector_cliente_callback, pattern=r"^pedido_(cliente_recurrente|cliente_nuevo|repetir_ultimo|buscar_cliente|sel_cust_\d+)$")
        ],
        PEDIDO_BUSCAR_CLIENTE: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_buscar_cliente)
        ],
        PEDIDO_SELECCIONAR_DIRECCION: [
            CallbackQueryHandler(pedido_seleccionar_direccion_callback, pattern=r"^(pedido_(nueva_dir|sel_addr_\d+)|guardar_dir_cliente_(si|no))$")
        ],
        PEDIDO_INSTRUCCIONES_EXTRA: [
            CallbackQueryHandler(pedido_instrucciones_callback, pattern=r"^pedido_instr_"),
            MessageHandler(Filters.text & ~Filters.command, pedido_instrucciones_text)
        ],
        PEDIDO_TIPO_SERVICIO: [
            CallbackQueryHandler(pedido_tipo_servicio_callback, pattern=r"^pedido_tipo_"),
            MessageHandler(Filters.text & ~Filters.command, pedido_tipo_servicio)
        ],
        PEDIDO_COMPRAS_CANTIDAD: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_compras_cantidad_handler)
        ],
        PEDIDO_NOMBRE: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_nombre_cliente)
        ],
        PEDIDO_TELEFONO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_telefono_cliente)
        ],
        PEDIDO_UBICACION: [
            CallbackQueryHandler(pedido_ubicacion_copiar_msg_callback, pattern=r"^ubicacion_copiar_msg_cliente$"),
            CallbackQueryHandler(pedido_geo_ubicacion_callback, pattern=r"^pedido_geo_"),
            MessageHandler(Filters.location, pedido_ubicacion_location_handler),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_ubicacion_handler)
        ],
        PEDIDO_DIRECCION: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_direccion_cliente)
        ],
        PEDIDO_PICKUP_SELECTOR: [
            CallbackQueryHandler(pedido_pickup_callback, pattern=r"^pickup_select_")
        ],
        PEDIDO_PICKUP_LISTA: [
            CallbackQueryHandler(pedido_pickup_lista_callback, pattern=r"^pickup_list_")
        ],
        PEDIDO_PICKUP_NUEVA_UBICACION: [
            CallbackQueryHandler(pickup_nueva_copiar_msg_callback, pattern=r"^pickup_copiar_msg_cliente$"),
            CallbackQueryHandler(pedido_pickup_geo_callback, pattern=r"^pickup_geo_"),
            MessageHandler(Filters.location, pedido_pickup_nueva_ubicacion_location_handler),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_pickup_nueva_ubicacion_handler)
        ],
        PEDIDO_PICKUP_NUEVA_DETALLES: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_pickup_nueva_detalles_handler)
        ],
        PEDIDO_PICKUP_NUEVA_CIUDAD: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_pickup_nueva_ciudad_handler),
        ],
        PEDIDO_PICKUP_NUEVA_BARRIO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_pickup_nueva_barrio_handler),
        ],
        PEDIDO_PICKUP_GUARDAR: [
            CallbackQueryHandler(pedido_pickup_guardar_callback, pattern=r"^pickup_guardar_")
        ],
        PEDIDO_REQUIERE_BASE: [
            CallbackQueryHandler(pedido_requiere_base_callback, pattern=r"^pedido_base_(si|no)$")
        ],
        PEDIDO_VALOR_BASE: [
            CallbackQueryHandler(pedido_valor_base_callback, pattern=r"^pedido_base_(5000|10000|20000|50000|otro)$"),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_valor_base_texto)
        ],
        PEDIDO_CONFIRMACION: [
            CallbackQueryHandler(pedido_retry_quote_callback, pattern=r"^pedido_retry_quote$"),
            CallbackQueryHandler(pedido_incentivo_fixed_callback, pattern=r"^pedido_inc_(1000|1500|2000|3000)$"),
            CallbackQueryHandler(pedido_incentivo_otro_start, pattern=r"^pedido_inc_otro$"),
            CallbackQueryHandler(pedido_confirmacion_callback, pattern=r"^pedido_(confirmar|cancelar)$"),
            MessageHandler(Filters.text & ~Filters.command, pedido_confirmacion)
        ],
        PEDIDO_INCENTIVO_MONTO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_incentivo_monto_handler),
        ],
        PEDIDO_GUARDAR_CLIENTE: [
            CallbackQueryHandler(pedido_guardar_cliente_callback, pattern=r"^pedido_guardar_")
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)


pedido_incentivo_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(pedido_incentivo_existing_otro_start, pattern=r"^pedido_inc_otro_\d+$"),
    ],
    states={
        PEDIDO_INCENTIVO_MONTO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_incentivo_existing_monto_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)

# Conversación para "Otro monto" de la sugerencia T+5 (aplica a aliados y admins)
offer_suggest_inc_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(offer_suggest_inc_otro_start, pattern=r"^offer_inc_otro_\d+$"),
    ],
    states={
        OFFER_SUGGEST_INC_MONTO: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, offer_suggest_inc_monto_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)

# Conversación para crear pedido especial del Admin Local/Plataforma
admin_pedido_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(admin_nuevo_pedido_start, pattern=r"^admin_nuevo_pedido$"),
    ],
    states={
        ADMIN_PEDIDO_PICKUP: [
            CallbackQueryHandler(admin_pedido_pickup_callback, pattern=r"^admin_pedido_pickup_\d+$"),
            CallbackQueryHandler(admin_pedido_nueva_dir_start, pattern=r"^admin_pedido_nueva_dir$"),
            CallbackQueryHandler(admin_pedido_geo_pickup_callback, pattern=r"^admin_pedido_geo_pickup_(si|no)$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
            MessageHandler(Filters.location, admin_pedido_pickup_gps_handler),
            MessageHandler(Filters.text & ~Filters.command, admin_pedido_pickup_text_handler),
        ],
        ADMIN_PEDIDO_CUST_NAME: [
            MessageHandler(Filters.text & ~Filters.command, admin_pedido_cust_name_handler),
        ],
        ADMIN_PEDIDO_CUST_PHONE: [
            MessageHandler(Filters.text & ~Filters.command, admin_pedido_cust_phone_handler),
        ],
        ADMIN_PEDIDO_CUST_ADDR: [
            CallbackQueryHandler(admin_pedido_geo_callback, pattern=r"^admin_pedido_geo_(si|no)$"),
            MessageHandler(Filters.location, admin_pedido_cust_gps_handler),
            MessageHandler(Filters.text & ~Filters.command, admin_pedido_cust_addr_handler),
        ],
        ADMIN_PEDIDO_TARIFA: [
            MessageHandler(Filters.text & ~Filters.command, admin_pedido_tarifa_handler),
        ],
        ADMIN_PEDIDO_INSTRUC: [
            CallbackQueryHandler(admin_pedido_sin_instruc_callback, pattern=r"^admin_pedido_sin_instruc$"),
            CallbackQueryHandler(admin_pedido_inc_fijo_callback, pattern=r"^admin_pedido_inc_(1500|2000|3000)$"),
            CallbackQueryHandler(admin_pedido_inc_otro_callback, pattern=r"^admin_pedido_inc_otro$"),
            CallbackQueryHandler(admin_pedido_confirmar_callback, pattern=r"^admin_pedido_confirmar$"),
            CallbackQueryHandler(admin_pedido_cancelar_callback, pattern=r"^admin_pedido_cancelar$"),
            MessageHandler(Filters.text & ~Filters.command, admin_pedido_instruc_handler),
        ],
        ADMIN_PEDIDO_INC_MONTO: [
            MessageHandler(Filters.text & ~Filters.command, admin_pedido_inc_monto_handler),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)

# Conversación para gestión de ubicaciones del aliado ("Mis ubicaciones")
ally_locs_conv = ConversationHandler(
    entry_points=[
        MessageHandler(Filters.regex(r'^Mis ubicaciones$'), mis_ubicaciones_start),
    ],
    states={
        ALLY_LOCS_MENU: [
            CallbackQueryHandler(ally_locs_menu_callback, pattern=r"^ally_locs_"),
        ],
        ALLY_LOCS_ADD_COORDS: [
            MessageHandler(Filters.location, ally_locs_add_coords_location),
            MessageHandler(Filters.text & ~Filters.command, ally_locs_add_coords),
        ],
        ALLY_LOCS_ADD_LABEL: [
            MessageHandler(Filters.text & ~Filters.command, ally_locs_add_label),
        ],
        ALLY_LOCS_ADD_CITY: [
            MessageHandler(Filters.text & ~Filters.command, ally_locs_add_city),
        ],
        ALLY_LOCS_ADD_BARRIO: [
            MessageHandler(Filters.text & ~Filters.command, ally_locs_add_barrio),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(
            Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'),
            cancel_por_texto
        ),
    ],
    allow_reentry=True,
)


# Conversación para /cotizar
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
            MessageHandler(Filters.text & ~Filters.command, cotizar_distancia),
        ],
        COTIZAR_RECOGIDA: [
            CallbackQueryHandler(cotizar_recogida_geo_callback, pattern=r"^cotizar_recogida_geo_"),
            MessageHandler(Filters.location, cotizar_recogida_location),
            MessageHandler(Filters.text & ~Filters.command, cotizar_recogida),
        ],
        COTIZAR_ENTREGA: [
            CallbackQueryHandler(cotizar_entrega_geo_callback, pattern=r"^cotizar_entrega_geo_"),
            MessageHandler(Filters.location, cotizar_entrega_location),
            MessageHandler(Filters.text & ~Filters.command, cotizar_entrega),
        ],
        COTIZAR_RESULTADO: [
            CallbackQueryHandler(cotizar_resultado_callback, pattern=r"^cotizar_(crear_pedido|crear_ruta|cerrar)$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
    ],
)


# ----- CONFIGURACION DE TARIFAS (ADMIN PLATAFORMA) -----

def _build_tarifas_texto(config, buy_config):
    """Construye el texto con los valores actuales de ambas tarifas."""
    return (
        "CONFIGURACION DE TARIFAS\n\n"
        "TARIFAS POR DISTANCIA:\n"
        f"1. Precio 0-2 km: ${config['precio_0_2km']:,}\n"
        f"2. Precio 2-3 km: ${config['precio_2_3km']:,}\n"
        f"3. Base distancia (km): {config['base_distance_km']}\n"
        f"4. Precio km extra normal (<=10km): ${config['precio_km_extra_normal']:,}\n"
        f"5. Umbral km largo: {config['umbral_km_largo']} km\n"
        f"6. Precio km extra largo (>10km): ${config['precio_km_extra_largo']:,}\n"
        "\nTARIFAS COMPRAS (recargo por productos):\n"
        f"7. Productos incluidos gratis: {buy_config['free_threshold']}\n"
        f"8. Recargo por producto adicional: ${buy_config['extra_fee']:,} c/u\n"
        f"   (Ej: {buy_config['free_threshold']+3} productos -> ${3*buy_config['extra_fee']:,} de recargo)\n"
    )


def tarifas_start(update, context):
    """Comando /tarifas - Solo Admin Plataforma."""
    user = update.effective_user

    # Validar que es Admin de Plataforma
    if not es_admin_plataforma(user.id):
        update.message.reply_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    # Cargar configuracion actual
    config = get_pricing_config()
    buy_config = get_buy_pricing_config()

    mensaje = _build_tarifas_texto(config, buy_config)

    # Menu principal: dos secciones separadas
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

    # Validar que es Admin de Plataforma
    if not es_admin_plataforma(query.from_user.id):
        query.edit_message_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    data = query.data

    if data == "pricing_exit":
        query.edit_message_text("Configuracion de tarifas cerrada.")
        return ConversationHandler.END

    # Volver al menu principal de tarifas
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

    # Submenu: editar tarifas por distancia
    if data == "pricing_menu_distancia":
        keyboard = [
            [InlineKeyboardButton("Cambiar precio 0-2 km", callback_data="pricing_edit_precio_0_2km")],
            [InlineKeyboardButton("Cambiar precio 2-3 km", callback_data="pricing_edit_precio_2_3km")],
            [InlineKeyboardButton("Cambiar base distancia (km)", callback_data="pricing_edit_base_distance_km")],
            [InlineKeyboardButton("Cambiar km extra normal", callback_data="pricing_edit_precio_km_extra_normal")],
            [InlineKeyboardButton("Cambiar umbral km largo", callback_data="pricing_edit_umbral_km_largo")],
            [InlineKeyboardButton("Cambiar km extra largo", callback_data="pricing_edit_precio_km_extra_largo")],
            [InlineKeyboardButton("⬅️ Volver", callback_data="pricing_volver")],
        ]
        query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    # Submenu: editar tarifas compras
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

    # Extraer el campo a editar
    if not data.startswith("pricing_edit_"):
        query.edit_message_text("Opcion no valida.")
        return ConversationHandler.END

    field = data.replace("pricing_edit_", "")
    context.user_data["pricing_field"] = field

    # Mapeo de campos a nombres legibles
    field_names = {
        "precio_0_2km": "Precio 0-2 km",
        "precio_2_3km": "Precio 2-3 km",
        "base_distance_km": "Base distancia (km)",
        "precio_km_extra_normal": "Precio km extra normal",
        "umbral_km_largo": "Umbral km largo",
        "precio_km_extra_largo": "Precio km extra largo",
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

    # Validar que es Admin de Plataforma
    if not es_admin_plataforma(user.id):
        update.message.reply_text("No autorizado. Este comando es solo para el Administrador de Plataforma.")
        return ConversationHandler.END

    texto = (update.message.text or "").strip().replace(",", ".")
    field = context.user_data.get("pricing_field")

    if not field:
        update.message.reply_text("Error: no se pudo identificar el campo a editar.")
        return ConversationHandler.END

    # Validar valor numerico
    try:
        valor_float = float(texto)
    except ValueError:
        update.message.reply_text("Valor invalido. Debe ser un numero. Intenta de nuevo o usa /cancel.")
        return TARIFAS_VALOR

    # Guardar en BD - campos de compras usan prefijo 'buy_', distancia usa 'pricing_'
    try:
        save_pricing_setting(field, texto)
    except ValueError as e:
        update.message.reply_text(
            f"Valor rechazado: {e}\n\nIntenta de nuevo o usa /cancel."
        )
        return TARIFAS_VALOR

    # Recargar config y mostrar
    config = get_pricing_config()
    buy_config = get_buy_pricing_config()

    # Pruebas rapidas
    test_31 = calcular_precio_distancia(3.1)
    test_111 = calcular_precio_distancia(11.1)
    free_th = buy_config.get("free_threshold", 2)
    test_buy_3 = calc_buy_products_surcharge(free_th, buy_config)
    test_buy_8 = calc_buy_products_surcharge(free_th + 3, buy_config)
    test_buy_15 = calc_buy_products_surcharge(free_th + 8, buy_config)

    mensaje = (
        "Guardado.\n\n"
        "TARIFAS DISTANCIA:\n"
        f"- Precio 0-2 km: ${config['precio_0_2km']:,}\n"
        f"- Precio 2-3 km: ${config['precio_2_3km']:,}\n"
        f"- Base distancia: {config['base_distance_km']} km\n"
        f"- Precio km extra normal: ${config['precio_km_extra_normal']:,}\n"
        f"- Umbral largo: {config['umbral_km_largo']} km\n"
        f"- Precio km extra largo: ${config['precio_km_extra_largo']:,}\n\n"
        f"TARIFAS COMPRAS:\n"
        f"- Productos gratis: {buy_config['free_threshold']}\n"
        f"- Recargo adicional: ${buy_config['extra_fee']:,} c/u\n\n"
        f"Prueba rapida distancia:\n"
        f"3.1 km -> ${test_31:,}\n"
        f"11.1 km -> ${test_111:,}\n\n"
        f"Prueba rapida compras:\n"
        f"{buy_config['free_threshold']} productos -> ${test_buy_3:,}\n"
        f"{buy_config['free_threshold']+3} productos -> ${test_buy_8:,}\n"
        f"{buy_config['free_threshold']+8} productos -> ${test_buy_15:,}"
    )

    update.message.reply_text(mensaje)
    context.user_data.clear()
    return ConversationHandler.END


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


# Conversacion para /tarifas
tarifas_conv = ConversationHandler(
    entry_points=[CommandHandler("tarifas", tarifas_start)],
    states={
        TARIFAS_VALOR: [MessageHandler(Filters.text & ~Filters.command, tarifas_set_valor)]
    },
    fallbacks=[
        CommandHandler("cancel", cancel_conversacion),
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
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
        MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uÃº])\s*$'), cancel_por_texto),
    ],
    allow_reentry=True,
)


def mi_admin(update, context):
    user_db_id = get_user_db_id_from_update(update)

    # Validar que sea admin local registrado
    admin = None
    admin = get_admin_by_user_id(user_db_id)
 
    if not admin:
        update.message.reply_text("No tienes perfil de Administrador Local registrado.")
        return

    admin_id = admin["id"]

    # Traer detalle completo (incluye team_code)
    admin_full = get_admin_by_id(admin_id)
    if not admin_full:
        update.message.reply_text("No se pudo cargar tu perfil de administrador. Revisa BD.")
        return

    status = admin_full.get("status") or "-"
    team_name = admin_full.get("team_name") or "-"
    team_code = admin_full.get("team_code") or "-"

    header = (
        "Panel Administrador Local\n\n"
        f"Estado: {status}\n"
        f"Equipo: {team_name}\n"
        f"Código de equipo: {team_code}\n"
        "Compártelo a tus repartidores para que soliciten unirse a tu equipo.\n\n"
    )

    # Administrador de Plataforma: siempre operativo
    if team_code == "PLATFORM":
        keyboard = [
            [InlineKeyboardButton("⏳ Repartidores pendientes", callback_data=f"local_couriers_pending_{admin_id}")],
            [InlineKeyboardButton("⏳ Aliados pendientes", callback_data=f"local_allies_pending_{admin_id}")],
            [InlineKeyboardButton("👥 Mi equipo", callback_data=f"local_my_team_{admin_id}")],
            [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos_local_{}".format(admin_id))],
            [InlineKeyboardButton("📋 Nuevo pedido especial", callback_data="admin_nuevo_pedido")],
            [InlineKeyboardButton("💳 Recargas pendientes", callback_data=f"local_recargas_pending_{admin_id}")],
            [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            [InlineKeyboardButton("📝 Solicitudes de cambio", callback_data="admin_change_requests")],
        ]
        update.message.reply_text(
            header +
            "Como Administrador de Plataforma, tu operación está habilitada.\n"
            "Selecciona una opción:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # FASE 1: Mostrar estado del equipo como información, NO como bloqueo
    ok, msg, stats = admin_puede_operar(admin_id)

    # Construir mensaje de estado
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
        "• 5 repartidores con saldo >= $5,000: {}\n"
        "• Saldo master >= $60,000: {}\n\n"
    ).format(
        total_allies, allies_ok,
        total_couriers, couriers_ok,
        admin_bal,
        "OK" if allies_ok >= 5 else "Faltan {}".format(5 - allies_ok),
        "OK" if couriers_ok >= 5 else "Faltan {}".format(5 - couriers_ok),
        "OK" if admin_bal >= 60000 else "Faltan ${:,}".format(60000 - admin_bal),
    )
    # En FASE 1: panel siempre habilitado
    keyboard = [
        [InlineKeyboardButton("⏳ Repartidores pendientes", callback_data=f"local_couriers_pending_{admin_id}")],
        [InlineKeyboardButton("⏳ Aliados pendientes", callback_data=f"local_allies_pending_{admin_id}")],
        [InlineKeyboardButton("👥 Mi equipo", callback_data=f"local_my_team_{admin_id}")],
        [InlineKeyboardButton("📦 Pedidos de mi equipo", callback_data="admin_pedidos_local_{}".format(admin_id))],
        [InlineKeyboardButton("📋 Nuevo pedido especial", callback_data="admin_nuevo_pedido")],
        [InlineKeyboardButton("💳 Recargas pendientes", callback_data=f"local_recargas_pending_{admin_id}")],
        [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
        [InlineKeyboardButton("🔍 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
        [InlineKeyboardButton("📝 Solicitudes de cambio", callback_data="admin_change_requests")],
        [InlineKeyboardButton("⚙️ Configuraciones", callback_data="admin_config")],
    ]

    update.message.reply_text(
        header + estado_msg +
        "Panel de administración habilitado.\n"
        "Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def mi_perfil(update, context):
    """
    Muestra perfil consolidado del usuario: roles, estados, equipos, fecha de registro.
    """
    def get_status_icon(status):
        """Retorna ícono según estado."""
        if status == "APPROVED":
            return "🟢 "
        if status == "PENDING":
            return "🟡 "
        if status in ("REJECTED", "INACTIVE"):
            return "🔴 "
        return ""

    telegram_id = update.effective_user.id
    user_db_id = get_user_db_id_from_update(update)

    # Obtener datos base del usuario (con created_at)
    user = get_user_by_id(user_db_id)
    if not user:
        update.message.reply_text("No se encontró tu usuario en la base de datos.")
        return

    # Acceso por nombre (sqlite3.Row)
    username = user["username"] if user["username"] else "-"
    fecha_registro = user["created_at"] if user["created_at"] else "(no disponible)"

    # Encabezado
    mensaje = "👤 MI PERFIL\n\n"
    mensaje += f"📱 Telegram ID: {telegram_id}\n"
    mensaje += f"👤 Usuario: {'@' + username if username != '-' else '(sin username)'}\n"
    mensaje += f"📅 Fecha de registro: {fecha_registro}\n\n"

    # ===== ROLES Y ESTADOS =====
    mensaje += "📋 ROLES Y ESTADO\n\n"

    # Admin
    admin = get_admin_by_user_id(user_db_id)
    if admin:
        admin_id = admin["id"]
        admin_full = get_admin_by_id(admin_id)

        # Acceso por nombre (sqlite3.Row) - sin índices mágicos
        full_name = admin_full["full_name"] if admin_full["full_name"] else "-"
        phone = admin_full["phone"] if admin_full["phone"] else "-"
        status = admin_full["status"] if admin_full["status"] else "PENDING"
        team_name = admin_full["team_name"] if admin_full["team_name"] else "-"
        team_code = admin_full["team_code"] if admin_full["team_code"] else "-"

        # Construir línea de equipo (agrupar nombre y código)
        if team_name != "-" and team_code != "-":
            equipo_admin = f"{team_name} ({team_code})"
        elif team_name != "-":
            equipo_admin = team_name
        elif team_code != "-":
            equipo_admin = team_code
        else:
            equipo_admin = "-"

        mensaje += f"🔧 Administrador Local\n"
        mensaje += f"   Nombre: {full_name}\n"
        mensaje += f"   Teléfono: {phone}\n"
        mensaje += f"   Estado: {get_status_icon(status)}{status}\n"
        mensaje += f"   Equipo: {equipo_admin}\n\n"
        admin_balance = get_admin_balance(admin_id)
        mensaje += f"   Saldo master: ${admin_balance:,}\n\n"

    # Aliado
    ally = get_ally_by_user_id(user_db_id)
    if ally:
        ally_id = ally["id"]

        # Acceso por nombre (sqlite3.Row) - sin índices mágicos
        business_name = ally["business_name"] if ally["business_name"] else "-"
        phone = ally["phone"] if ally["phone"] else "-"
        status = ally["status"] if ally["status"] else "PENDING"

        # Buscar equipo vinculado
        admin_link = get_admin_link_for_ally(ally_id)
        equipo_info = "(sin equipo)"
        if admin_link:
            # Acceso por nombre (sqlite3.Row) - sin índices mágicos
            team_name = admin_link["team_name"] if admin_link["team_name"] else "-"
            team_code = admin_link["team_code"] if admin_link["team_code"] else "-"
            link_status = admin_link["link_status"] if admin_link["link_status"] else "-"
            equipo_info = f"{team_name} ({team_code}) - Vínculo: {link_status}"

        mensaje += f"🍕 Aliado\n"
        mensaje += f"   Negocio: {business_name}\n"
        mensaje += f"   Teléfono: {phone}\n"
        mensaje += f"   Estado: {get_status_icon(status)}{status}\n"
        mensaje += f"   Equipo: {equipo_info}\n\n"
        ally_links = get_all_approved_links_for_ally(ally_id)
        if ally_links:
            for alink in ally_links:
                alink_team = alink["team_name"] or "-"
                alink_code = alink["team_code"] or ""
                alink_balance = alink["balance"] if alink["balance"] else 0
                if alink_code == "PLATFORM":
                    alink_label = "Plataforma"
                else:
                    alink_label = alink_team
                mensaje += f"   Saldo ({alink_label}): ${alink_balance:,}\n"
            mensaje += "\n"

    # Repartidor
    courier = get_courier_by_user_id(user_db_id)
    if courier:
        courier_id = courier["id"]

        # Acceso por nombre (sqlite3.Row) - sin índices mágicos
        full_name = courier["full_name"] if courier["full_name"] else "-"
        code = courier["code"] if courier["code"] else "-"
        status = courier["status"] if courier["status"] else "PENDING"

        # Buscar equipo vinculado
        admin_link = get_admin_link_for_courier(courier_id)
        equipo_info = "(sin equipo)"
        if admin_link:
            # Acceso por nombre (sqlite3.Row) - sin índices mágicos
            team_name = admin_link["team_name"] if admin_link["team_name"] else "-"
            team_code = admin_link["team_code"] if admin_link["team_code"] else "-"
            link_status = admin_link["link_status"] if admin_link["link_status"] else "-"
            equipo_info = f"{team_name} ({team_code}) - Vínculo: {link_status}"

        mensaje += f"🚴 Repartidor\n"
        mensaje += f"   Nombre: {full_name}\n"
        mensaje += f"   Código interno: {code if code else 'sin asignar'}\n"
        mensaje += f"   Estado: {get_status_icon(status)}{status}\n"
        mensaje += f"   Equipo: {equipo_info}\n\n"
        courier_links = get_all_approved_links_for_courier(courier_id)
        if courier_links:
            for clink in courier_links:
                clink_team = clink["team_name"] or "-"
                clink_code = clink["team_code"] or ""
                clink_balance = clink["balance"] if clink["balance"] else 0
                if clink_code == "PLATFORM":
                    clink_label = "Plataforma"
                else:
                    clink_label = clink_team
                mensaje += f"   Saldo ({clink_label}): ${clink_balance:,}\n"
            mensaje += "\n"

    # Si no tiene roles
    if not admin and not ally and not courier:
        mensaje += "   (Sin roles registrados)\n\n"

    # ===== ESTADO OPERATIVO =====
    mensaje += "📊 ESTADO OPERATIVO\n\n"

    # Pedidos
    if ally:
        ally_status = ally["status"] if ally["status"] else "PENDING"
        if ally_status == "APPROVED":
            mensaje += f"{get_status_icon(ally_status)}Pedidos: Habilitados\n"
        else:
            mensaje += f"{get_status_icon(ally_status)}Pedidos: No habilitados\n"
    else:
        mensaje += "❌ Pedidos: Requiere rol Aliado\n"

    # Admin
    if admin:
        admin_status = admin_full["status"] if admin_full["status"] else "PENDING"
        if admin_status == "APPROVED":
            mensaje += f"{get_status_icon(admin_status)}Admin: Aprobado\n"
        elif admin_status == "PENDING":
            mensaje += f"{get_status_icon(admin_status)}Admin: Pendiente de aprobación\n"
        else:
            mensaje += f"{get_status_icon(admin_status)}Admin: {admin_status}\n"

    # Repartidor
    if courier:
        courier_status = courier["status"] if courier["status"] else "PENDING"
        if courier_status == "APPROVED":
            mensaje += f"{get_status_icon(courier_status)}Repartidor: Activo\n"
        elif courier_status == "PENDING":
            mensaje += f"{get_status_icon(courier_status)}Repartidor: Pendiente\n"
        else:
            mensaje += f"{get_status_icon(courier_status)}Repartidor: No activo\n"

        # Mostrar estado de disponibilidad (live location)
        courier_is_active = courier["is_active"] if "is_active" in courier.keys() else 0
        if courier_is_active and courier_status == "APPROVED":
            avail_status = _row_value(courier, "availability_status", "INACTIVE")
            live_active = int(_row_value(courier, "live_location_active", 0) or 0) == 1
            if avail_status == "APPROVED" and live_active:
                avail = "ONLINE"
            elif avail_status == "APPROVED":
                avail = "PAUSADO"
            else:
                avail = "OFFLINE"
            mensaje += f"   Disponibilidad: {avail}\n"
            if avail == "ONLINE":
                avail_cash = int(_row_value(courier, "available_cash", 0) or 0)
                mensaje += f"   (Compartiendo ubicacion en vivo)\n"
                mensaje += f"   Base declarada: ${avail_cash:,}\n"
            elif avail == "PAUSADO":
                mensaje += "   (Ubicacion en vivo detenida - comparte para volver a ONLINE)\n"
            else:
                mensaje += "   (Comparte tu ubicacion en vivo para estar ONLINE)\n"

    mensaje += "\n"

    # ===== ACCIONES RÁPIDAS =====
    mensaje += "⚡ ACCIONES RÁPIDAS\n\n"
    mensaje += "• /menu - Ver menú principal\n"

    if admin:
        mensaje += "• /mi_admin - Panel de administrador\n"

    if ally and status == "APPROVED":
        mensaje += "• /nuevo_pedido - Crear pedido\n"

    if admin or ally or courier:
        keyboard = [[InlineKeyboardButton("Solicitar cambio", callback_data="perfil_change_start")]]
        if courier:
            courier_buttons = []
            courier_is_active = courier["is_active"] if "is_active" in courier.keys() else 0
            if courier_is_active:
                courier_buttons.append([InlineKeyboardButton(
                    "Desactivarme",
                    callback_data="courier_deactivate",
                )])
            else:
                courier_buttons.append([InlineKeyboardButton(
                    "Activarme (declarar base)",
                    callback_data="courier_activate",
                )])
            keyboard.extend(courier_buttons)
        update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text(mensaje)


# ============================================================
# SISTEMA DE RECARGAS
# ============================================================

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
        mensaje += "   Saldo master: ${:,}\n\n".format(balance)
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
            if payment_info.get("bank_name"):
                info_text += "Banco: {}\n".format(payment_info["bank_name"])
            if payment_info.get("account_type"):
                info_text += "Tipo: {}\n".format(payment_info["account_type"])
            if payment_info.get("account_number"):
                info_text += "Cuenta: {}\n".format(payment_info["account_number"])
            if payment_info.get("nequi_number"):
                info_text += "Nequi: {}\n".format(payment_info["nequi_number"])
            if payment_info.get("daviplata_number"):
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
        print(f"[WARN] No se pudo notificar al admin: {e}")

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
        print(f"[WARN] No se pudo enviar comprobante: {e}")
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
                req_user_id = _req.get("requested_by_user_id") if _req else None
                req_user = get_user_by_id(req_user_id) if req_user_id else None
                req_chat_id = req_user.get("telegram_id") if req_user else None

                new_balance = None
                if _req and _req.get("target_type") == "COURIER":
                    link = get_approved_admin_link_for_courier(_req.get("target_id"))
                    if link:
                        new_balance = link.get("balance")
                elif _req and _req.get("target_type") == "ALLY":
                    link = get_approved_admin_link_for_ally(_req.get("target_id"))
                    if link:
                        new_balance = link.get("balance")
                elif _req and _req.get("target_type") == "ADMIN":
                    new_balance = get_admin_balance(_req.get("target_id"))

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
                print("[WARN] No se pudo notificar al solicitante de la recarga #{}: {}".format(request_id, e))

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
                req_user_id = _req.get("requested_by_user_id") if _req else None
                req_user = get_user_by_id(req_user_id) if req_user_id else None
                req_chat_id = req_user.get("telegram_id") if req_user else None
                if req_chat_id:
                    context.bot.send_message(
                        chat_id=req_chat_id,
                        text=(
                            "Tu recarga #{} fue rechazada. "
                            "Comunicate con el administrador al que solicitaste tu recarga."
                        ).format(request_id),
                    )
            except Exception as e:
                print("[WARN] No se pudo notificar rechazo al solicitante de la recarga #{}: {}".format(request_id, e))

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
            print("[WARN] plat_rec_notify admin_id={}: {}".format(admin_id, e))
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
        status = admin_full.get("status") or "-"
        team_code = admin_full.get("team_code") or "-"

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
            "• 5 repartidores con saldo >= $5,000: {}\n"
            "• Saldo master >= $60,000: {}\n\n"
        ).format(
            total_allies, allies_ok,
            total_couriers, couriers_ok,
            admin_bal,
            "OK" if allies_ok >= 5 else "Faltan {}".format(5 - allies_ok),
            "OK" if couriers_ok >= 5 else "Faltan {}".format(5 - couriers_ok),
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
        status = admin_full.get("status") or "-"
        team_code = admin_full.get("team_code") or "-"

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
            print("[ERROR] get_pending_couriers_by_admin:", e)
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

        residence_address = courier.get("residence_address")
        residence_lat = courier.get("residence_lat")
        residence_lng = courier.get("residence_lng")
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

        cedula_front = courier.get("cedula_front_file_id")
        cedula_back = courier.get("cedula_back_file_id")
        selfie = courier.get("selfie_file_id")
        if cedula_front or cedula_back or selfie:
            try:
                if cedula_front:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_front, caption="Cédula frente")
                if cedula_back:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_back, caption="Cédula reverso")
                if selfie:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=selfie, caption="Selfie")
            except Exception as e:
                print(f"[WARN] No se pudieron enviar fotos del repartidor {courier_id}: {e}")

        return

    # Bloquear acciones de aprobar/rechazar/bloquear si Admin Local no esta APPROVED
    if data.startswith(("local_courier_approve_", "local_courier_reject_", "local_courier_block_")):
        admin_full = get_admin_by_id(admin_id)
        admin_status = admin_full.get("status") if admin_full else None
        if admin_status != "APPROVED":
            query.answer("Acceso restringido: tu Admin Local no esta APPROVED.", show_alert=True)
            return

    if data.startswith("local_courier_approve_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
            deactivate_other_approved_admin_courier_links(courier_id, admin_id)
        except Exception as e:
            print("[ERROR] update_admin_courier_status APPROVED:", e)
            query.edit_message_text("Error aprobando repartidor. Revisa logs.")
            return

        _resolve_important_alert(context, "team_courier_pending_{}_{}".format(admin_id, courier_id))
        query.edit_message_text(
            "✅ Repartidor aprobado en tu equipo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_courier_reject_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            print("[ERROR] update_admin_courier_status REJECTED:", e)
            query.edit_message_text("Error rechazando repartidor. Revisa logs.")
            return

        _resolve_important_alert(context, "team_courier_pending_{}_{}".format(admin_id, courier_id))
        query.edit_message_text(
            "❌ Repartidor rechazado para tu equipo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅ Volver a pendientes", callback_data=f"local_couriers_pending_{admin_id}")]
            ])
        )
        return

    if data.startswith("local_courier_block_"):
        courier_id = int(data.split("_")[-1])
        try:
            update_admin_courier_status(admin_id, courier_id, "INACTIVE", changed_by=f"tg:{update.effective_user.id}")
        except Exception as e:
            print("[ERROR] update_admin_courier_status INACTIVE:", e)
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
            print("[ERROR] get_pending_allies_by_admin:", e)
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
            ally.get("id"),
            ally.get("business_name") or "-",
            ally.get("owner_name") or "-",
            ally.get("phone") or "-",
            ally.get("city") or "-",
            ally.get("barrio") or "-",
            ally.get("address") or "-",
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"local_ally_approve_{ally_id_val}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"local_ally_reject_{ally_id_val}"),
            ],
            [InlineKeyboardButton("⬅ Volver", callback_data=f"local_allies_pending_{admin_id}")]
        ]
        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
        cedula_front = ally.get("cedula_front_file_id")
        cedula_back = ally.get("cedula_back_file_id")
        selfie = ally.get("selfie_file_id")
        if cedula_front or cedula_back or selfie:
            try:
                if cedula_front:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_front, caption="Cédula frente")
                if cedula_back:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=cedula_back, caption="Cédula reverso")
                if selfie:
                    context.bot.send_photo(chat_id=query.message.chat_id, photo=selfie, caption="Selfie")
            except Exception as e:
                print(f"[WARN] No se pudieron enviar fotos del aliado {ally_id_val}: {e}")
        return

    if data.startswith("local_ally_approve_") or data.startswith("local_ally_reject_"):
        ally_id_val = int(data.split("_")[-1])
        admin_full = get_admin_by_id(admin_id)
        admin_status = admin_full.get("status") if admin_full else None
        if admin_status != "APPROVED":
            query.edit_message_text("Tu cuenta de administrador no está APPROVED. No puedes aprobar/rechazar aliados.")
            return

        if data.startswith("local_ally_approve_"):
            try:
                upsert_admin_ally_link(admin_id, ally_id_val, "APPROVED")
                deactivate_other_approved_admin_ally_links(ally_id_val, admin_id)
            except Exception as e:
                print("[ERROR] local_ally_approve:", e)
                query.edit_message_text("Error aprobando aliado. Revisa logs.")
                return
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
                print("[ERROR] local_ally_reject:", e)
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
            print("[ERROR] local_courier_activate:", e)
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
            print("[ERROR] local_courier_inactivate:", e)
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
            print("[ERROR] local_ally_activate:", e)
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
            print("[ERROR] local_ally_inactivate:", e)
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
    """Maneja los botones de aprobar / rechazar aliados (solo Admin Plataforma)."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador de plataforma puede usar estos botones.", show_alert=True)
        return

    partes = data.split("_")  # ally_approve_3
    if len(partes) != 3 or partes[0] != "ally":
        query.answer("Datos de botón no válidos.", show_alert=True)
        return

    accion = partes[1]
    try:
        ally_id = int(partes[2])
    except ValueError:
        query.answer("ID de aliado no válido.", show_alert=True)
        return

    if accion not in ("approve", "reject"):
        query.answer("Acción no reconocida.", show_alert=True)
        return

    nuevo_estado = "APPROVED" if accion == "approve" else "REJECTED"

    try:
        update_ally_status(ally_id, nuevo_estado, changed_by=f"tg:{update.effective_user.id}")
    except Exception as e:
        print(f"[ERROR] ally_approval_callback: {e}")
        query.answer("Error actualizando el aliado. Revisa logs.", show_alert=True)
        return
    _resolve_important_alert(context, "ally_registration_{}".format(ally_id))

    if nuevo_estado == "APPROVED":
        try:
            link = get_admin_link_for_ally(ally_id)
            if link:
                keep_admin_id = link["admin_id"]
            else:
                keep_admin_id = get_platform_admin_id()
            upsert_admin_ally_link(keep_admin_id, ally_id, "APPROVED")
            deactivate_other_approved_admin_ally_links(ally_id, keep_admin_id)
        except Exception as e:
            print(f"[ERROR] asegurar vinculo APPROVED de ally {ally_id}: {e}")

    ally = get_ally_by_id(ally_id)
    if not ally:
        query.edit_message_text("No se encontró el aliado después de actualizar.")
        return

    ally_user_id = ally["user_id"]
    business_name = ally["business_name"]

    # Notificar al aliado (si falla, no rompemos el flujo)
    try:
        u = get_user_by_id(ally_user_id)
        ally_telegram_id = u["telegram_id"]

        context.bot.send_message(
            chat_id=ally_telegram_id,
            text=(
                "Tu registro como aliado '{}' ha sido {}.\n"
                "{}"
            ).format(
                business_name,
                "APROBADO" if accion == "approve" else "RECHAZADO",
                "Ya puedes usar el bot para crear pedidos." if accion == "approve"
                else "Si crees que es un error, comunícate con el administrador."
            )
        )
    except Exception as e:
        print("Error notificando aliado:", e)


    if nuevo_estado == "APPROVED":
        query.edit_message_text("✅ El aliado '{}' ha sido APROBADO.".format(business_name))
    else:
        query.edit_message_text("❌ El aliado '{}' ha sido RECHAZADO.".format(business_name))


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
        "Registro de ingreso externo.\n\n"
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
        print("[ERROR] register_platform_income: {}".format(e))
        update.message.reply_text("Error al registrar el ingreso. Revisa los logs.")
        return ConversationHandler.END
    context.user_data.pop("ingreso_monto", None)
    context.user_data.pop("ingreso_metodo", None)
    nuevo_balance = get_admin_balance(admin_id)
    update.message.reply_text(
        "Ingreso registrado correctamente.\n\n"
        "Monto: ${:,}\n"
        "Metodo: {}\n"
        "{}Nuevo saldo disponible: ${:,}".format(
            monto,
            metodo,
            "Nota: {}\n".format(nota) if nota else "",
            nuevo_balance,
        )
    )
    return ConversationHandler.END


def pendientes_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    telegram_id = update.effective_user.id
    es_admin_plataforma_flag = es_admin_plataforma(telegram_id)

    if not es_admin_plataforma_flag:
        try:
            user_db_id = get_user_db_id_from_update(update)
            admin = get_admin_by_user_id(user_db_id)

        except Exception:
            admin = None
        if not admin:
            query.answer("No tienes permisos.", show_alert=True)
            return

    if data == "menu_aliados_pendientes":
        aliados_pendientes(update, context)
        return

    if data == "menu_repartidores_pendientes":
        repartidores_pendientes(update, context)
        return

    query.answer("Opción no reconocida.", show_alert=True)


def courier_approval_callback(update, context):
    """Aprobación / rechazo global de repartidores (solo Admin Plataforma)."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    query.answer()

    # En tu main(), este handler ^courier_(approve|reject)_\d+$ está pensado para ADMIN PLATAFORMA.
    # La aprobación por Admin Local va por admin_local_callback con local_courier_approve/reject/block.
    if user_id != ADMIN_USER_ID:
        query.answer("Solo el administrador de plataforma puede usar estos botones.", show_alert=True)
        return

    partes = data.split("_")  # courier_approve_3
    if len(partes) != 3 or partes[0] != "courier":
        query.answer("Datos de botón no válidos.", show_alert=True)
        return

    accion = partes[1]
    try:
        courier_id = int(partes[2])
    except ValueError:
        query.answer("ID de repartidor no válido.", show_alert=True)
        return

    if accion not in ("approve", "reject"):
        query.answer("Acción no reconocida.", show_alert=True)
        return

    nuevo_estado = "APPROVED" if accion == "approve" else "REJECTED"

    # Actualizar estado global del courier
    try:
        update_courier_status(courier_id, nuevo_estado, changed_by=f"tg:{update.effective_user.id}")
    except Exception as e:
        print(f"[ERROR] update_courier_status: {e}")
        query.answer("Error actualizando repartidor. Revisa logs.", show_alert=True)
        return
    _resolve_important_alert(context, "courier_registration_{}".format(courier_id))

    if nuevo_estado == "APPROVED":
        try:
            link = get_admin_link_for_courier(courier_id)
            if link:
                keep_admin_id = link["admin_id"]
            else:
                keep_admin_id = get_platform_admin_id()
                create_admin_courier_link(keep_admin_id, courier_id)

            upsert_admin_courier_link(keep_admin_id, courier_id, "APPROVED", 1)
            deactivate_other_approved_admin_courier_links(courier_id, keep_admin_id)
        except Exception as e:
            print(f"[ERROR] asegurar vínculo APPROVED de courier {courier_id}: {e}")

    courier = get_courier_by_id(courier_id)
    if not courier:
        query.edit_message_text("No se encontró el repartidor después de actualizar.")
        return

    courier_user_db_id = courier["user_id"]
    full_name = courier["full_name"]

    # Notificar al repartidor si existe get_user_by_id (recomendado).
    # Si no existe, solo omitimos notificación sin romper.
    try:
        u = get_user_by_id(courier_user_db_id)
        courier_telegram_id = u["telegram_id"]

        if accion == "approve":
            msg = "Tu registro como repartidor ha sido APROBADO. Bienvenido, {}.".format(full_name)
        else:
            msg = (
                "Tu registro como repartidor ha sido RECHAZADO, {}.\n"
                "Si crees que es un error, comunícate con el administrador."
            ).format(full_name)

        context.bot.send_message(chat_id=courier_telegram_id, text=msg)
    except Exception as e:
        print("Error notificando repartidor:", e)

    if nuevo_estado == "APPROVED":
        query.edit_message_text("✅ El repartidor '{}' ha sido APROBADO.".format(full_name))
    else:
        query.edit_message_text("❌ El repartidor '{}' ha sido RECHAZADO.".format(full_name))


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
        ally_id = int(data.split("_")[-1])
        ally = get_ally_by_id(ally_id)
        if not ally:
            query.edit_message_text("No se encontró el aliado.")
            return

        default_loc = get_default_ally_location(ally_id)
        if default_loc:
            loc_lat = default_loc.get("lat")
            loc_lng = default_loc.get("lng")
        else:
            loc_lat = None
            loc_lng = None

        if loc_lat is not None and loc_lng is not None:
            loc_text = "{}, {}".format(loc_lat, loc_lng)
            maps_text = "Maps: https://www.google.com/maps?q={},{}\n".format(loc_lat, loc_lng)
        else:
            loc_text = "No disponible"
            maps_text = ""

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
            "Ubicación: {loc}\n"
            "{maps}"
        ).format(
            id=ally["id"],
            business_name=ally["business_name"],
            owner_name=ally["owner_name"],
            phone=ally["phone"],
            address=ally["address"],
            city=ally["city"],
            barrio=ally["barrio"],
            status=ally["status"],
            loc=loc_text,
            maps=maps_text,
        )

        status = ally["status"]
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

        keyboard.append([InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")])

        query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard))
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
            "Estado: {status}"
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
        now = datetime.datetime.utcnow()
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
            print(f"[ERROR] config_ally_disable_ upsert link: {e}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")]]
        query.edit_message_text("Aliado desactivado (INACTIVE).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_ally_enable_"):
        ally_id = int(data.split("_")[-1])
        update_ally_status_by_id(ally_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
        try:
            link = get_admin_link_for_ally(ally_id)
            keep_admin_id = link["admin_id"] if link else get_platform_admin_id()
            upsert_admin_ally_link(keep_admin_id, ally_id, "APPROVED")
        except Exception as e:
            print(f"[ERROR] config_ally_enable_ upsert link: {e}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")]]
        query.edit_message_text("Aliado activado (APPROVED).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_ally_reject_"):
        ally_id = int(data.split("_")[-1])
        update_ally_status_by_id(ally_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")]]
        query.edit_message_text("Aliado rechazado (REJECTED).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_courier_disable_"):
        courier_id = int(data.split("_")[-1])
        update_courier_status_by_id(courier_id, "INACTIVE", changed_by=f"tg:{update.effective_user.id}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")]]
        query.edit_message_text("Repartidor desactivado (INACTIVE).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_courier_enable_"):
        courier_id = int(data.split("_")[-1])
        update_courier_status_by_id(courier_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")]]
        query.edit_message_text("Repartidor activado (APPROVED).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_courier_reject_"):
        courier_id = int(data.split("_")[-1])
        update_courier_status_by_id(courier_id, "REJECTED", changed_by=f"tg:{update.effective_user.id}")
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_repartidores")]]
        query.edit_message_text("Repartidor rechazado (REJECTED).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "config_cerrar":
        query.edit_message_text("Menú de configuraciones cerrado.")
        return

    query.answer("Opción no reconocida.", show_alert=True)


def ensure_terms(update, context, telegram_id: int, role: str) -> bool:
    print(
        f"[DEBUG][terms][ensure] role={role} telegram_id={telegram_id} via_callback={bool(getattr(update, 'callback_query', None))}",
        flush=True,
    )
    tv = get_active_terms_version(role)
    if not tv:
        print(f"[DEBUG][terms][ensure] no_terms_config role={role}", flush=True)
        context.bot.send_message(
            chat_id=telegram_id,
            text="Términos no configurados para este rol. Contacta al soporte de la plataforma."
        )
        return False

    version, url, sha256 = tv
    print(f"[DEBUG][terms][ensure] version={version!r} url={url!r}", flush=True)

    accepted = has_accepted_terms(telegram_id, role, version, sha256)
    print(f"[DEBUG][terms][ensure] already_accepted={accepted}", flush=True)
    if accepted:
        try:
            save_terms_session_ack(telegram_id, role, version)
        except Exception as e:
            print("[WARN] save_terms_session_ack:", e)
        return True

    text = (
        "Antes de continuar debes aceptar los Términos y Condiciones de Domiquerendona.\n\n"
        "Rol: {}\n"
        "Versión: {}\n\n"
        "Lee el documento y confirma tu aceptación para continuar."
    ).format(role, version)

    valid_terms_url = isinstance(url, str) and url.strip().lower().startswith(("http://", "https://"))
    keyboard = []
    if valid_terms_url:
        keyboard.append([InlineKeyboardButton("Leer términos", url=url)])
    else:
        print(f"[WARN][terms] URL invalida para role={role}, version={version}: {url!r}", flush=True)
    keyboard.append(
        [
            InlineKeyboardButton("Acepto", callback_data="terms_accept_{}".format(role)),
            InlineKeyboardButton("No acepto", callback_data="terms_decline_{}".format(role)),
        ]
    )

    if update.callback_query:
        print("[DEBUG][terms][ensure] prompt_sent_via=callback_edit", flush=True)
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        print("[DEBUG][terms][ensure] prompt_sent_via=send_message", flush=True)
        context.bot.send_message(chat_id=telegram_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    return False


def terms_callback(update, context):
    query = update.callback_query
    data = query.data
    telegram_id = query.from_user.id
    query.answer()
    print(
        f"[DEBUG][terms][callback] data={data!r} telegram_id={telegram_id} message_id={getattr(query.message, 'message_id', None)}",
        flush=True,
    )

    if data.startswith("terms_accept_"):
        role = data.split("_", 2)[-1]
        tv = get_active_terms_version(role)
        print(f"[DEBUG][terms][callback] accept role={role} tv_found={bool(tv)}", flush=True)
        if not tv:
            query.edit_message_text("Términos no configurados. Contacta soporte.")
            return

        version, url, sha256 = tv
        save_terms_acceptance(telegram_id, role, version, sha256, query.message.message_id)
        print(f"[DEBUG][terms][callback] acceptance_saved role={role} version={version!r}", flush=True)
        if role == "ALLY":
            query.edit_message_text("Aceptación registrada. Ya puedes continuar con Nuevo pedido.")
            print("[DEBUG][terms][callback] awaiting_manual_nuevo_pedido", flush=True)
            return
        query.edit_message_text("Aceptación registrada. Ya puedes continuar.")
        return

    if data.startswith("terms_decline_"):
        print("[DEBUG][terms][callback] decline", flush=True)
        query.edit_message_text(
            "No puedes usar la plataforma sin aceptar los Términos y Condiciones.\n"
            "Si cambias de decisión, vuelve a intentar y acepta los términos."
        )
        return

    query.answer("Opción no reconocida.", show_alert=True)


def courier_live_location_handler(update, context):
    """
    Maneja ubicaciones en vivo compartidas por repartidores.
    - Live location nueva: courier pasa a ONLINE y se guarda lat/lng.
    - Live location update (edited_message): se actualiza lat/lng.
    - Ubicacion estatica (pin): se ignora para este flujo.
    """
    # Determinar si es mensaje nuevo o editado
    message = update.edited_message or update.message
    if not message or not message.location:
        return

    telegram_id = update.effective_user.id

    # Solo procesar si es repartidor aprobado y activo
    courier = get_courier_by_telegram_id(telegram_id)
    if not courier:
        return
    if courier["status"] != "APPROVED":
        return
    if not int(_row_value(courier, "is_active", 0) or 0):
        now_ts = time.time()
        last_sent = context.user_data.get("deact_reminder_ts", 0)
        if now_ts - last_sent >= 300:
            try:
                context.bot.send_message(
                    chat_id=telegram_id,
                    text="Estas desactivado y sigues compartiendo tu ubicacion.\n"
                         "Deten el envio de ubicacion en vivo desde tu chat.\n"
                         "Si quieres activarte, presiona Activarme en tu menu."
                )
                context.user_data["deact_reminder_ts"] = now_ts
            except Exception:
                pass
        return

    location = message.location
    lat = location.latitude
    lng = location.longitude

    # Detectar si es live location (tiene live_period)
    live_period = getattr(location, 'live_period', None)

    if live_period or update.edited_message:
        # Es live location (nueva o update) -> actualizar y marcar ONLINE
        if update.message and live_period:
            update_courier_live_location(courier["id"], lat, lng, live_period_seconds=live_period)
        else:
            update_courier_live_location(courier["id"], lat, lng)

        # Verificar llegada al punto de recogida si tiene pedido activo
        try:
            check_courier_arrival_at_pickup(courier["id"], lat, lng, context)
        except Exception as e:
            print("[WARN] check_courier_arrival_at_pickup: {}".format(e))

        # Solo notificar la primera vez (cuando pasa a ONLINE visible)
        was_online = (
            _row_value(courier, "availability_status") == "APPROVED"
            and int(_row_value(courier, "live_location_active", 0) or 0) == 1
        )
        if not was_online and update.message and live_period:
            try:
                context.bot.send_message(
                    chat_id=telegram_id,
                    text="Tu ubicacion en vivo esta activa. Estas ONLINE y recibiras ofertas cercanas."
                )
            except Exception:
                pass
    # Si es ubicacion estatica (pin sin live_period), no hacemos nada


def courier_live_location_expired_check(context):
    """
    Job periodico: revisa couriers ONLINE cuya sesion de ubicacion en vivo
    ya expiro y los desactiva completamente (requieren re-activacion con base).
    """
    expired_ids = expire_stale_live_locations(stale_timeout_seconds=900)
    for cid in expired_ids:
        try:
            courier = get_courier_by_id(cid)
            if courier:
                # Evitar notificacion "antigua" si el courier ya volvio a ONLINE
                if (
                    _row_value(courier, "availability_status") == "APPROVED"
                    and int(_row_value(courier, "live_location_active", 0) or 0) == 1
                ):
                    continue
                user = get_user_by_id(courier["user_id"])
                if user:
                    tg_id = user["telegram_id"]
                    context.bot.send_message(
                        chat_id=tg_id,
                        text="Tu ubicacion en vivo expiro. Quedaste OFFLINE.\n"
                             "Para volver a recibir pedidos, ve a tu menu y presiona Activarme."
                    )
        except Exception as e:
            print(f"[WARN] No se pudo notificar expiracion a courier {cid}: {e}")


def _courier_activate_common(update, context, reply_func):
    """Inicia flujo de activacion del courier: pide declarar base."""
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        reply_func("No se encontro tu usuario.")
        return

    courier = get_courier_by_user_id(user["id"])
    if not courier or courier["status"] != "APPROVED":
        reply_func("No tienes perfil de repartidor activo.")
        return

    # Verificar que tiene equipo activo y saldo suficiente para activarse
    admin_link = get_admin_link_for_courier(courier["id"])
    if not admin_link or admin_link.get("link_status") != "APPROVED":
        reply_func(
            "No puedes activarte porque no tienes un equipo activo asignado. "
            "Contacta a tu administrador."
        )
        return

    saldo = get_courier_link_balance(courier["id"], admin_link["admin_id"])
    if saldo < 300:
        reply_func(
            "No puedes activarte porque tu saldo es insuficiente.\n\n"
            "Saldo actual: ${:,}\n"
            "Minimo requerido: $300\n\n"
            "Solicita una recarga a tu administrador para poder conectarte.".format(saldo)
        )
        return

    reply_func(
        "Para activarte, indica cuanta base (dinero en efectivo) tienes disponible.\n\n"
        "Escribe el monto en pesos (solo numeros, ej: 50000):"
    )
    context.user_data["courier_activating"] = True
    context.user_data["courier_id_activating"] = courier["id"]


def _courier_deactivate_common(update, context, reply_func):
    """Desactiva al courier."""
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        reply_func("No se encontro tu usuario.")
        return

    courier = get_courier_by_user_id(user["id"])
    if not courier:
        reply_func("No se encontro tu perfil.")
        return

    deactivate_courier(courier["id"])
    context.user_data.pop("deact_reminder_ts", None)
    courier_updated = get_courier_by_user_id(user["id"])
    updated_keyboard = get_repartidor_menu_keyboard(courier_updated)
    update.effective_message.reply_text(
        "Te has desactivado. No recibiras ofertas de pedidos.\n\n"
        "Deten el envio de ubicacion en vivo desde tu chat para "
        "dejar de compartir tu posicion y ahorrar bateria.",
        reply_markup=updated_keyboard
    )


def courier_activate_from_message(update, context):
    """Activa flujo desde boton del teclado principal."""
    return _courier_activate_common(update, context, update.message.reply_text)


def courier_deactivate_from_message(update, context):
    """Desactiva desde boton del teclado principal."""
    return _courier_deactivate_common(update, context, update.message.reply_text)


def courier_activate_callback(update, context):
    """Inicia flujo de activacion del courier desde callback."""
    query = update.callback_query
    query.answer()
    return _courier_activate_common(update, context, query.edit_message_text)


def courier_deactivate_callback(update, context):
    """Desactiva al courier desde callback."""
    query = update.callback_query
    query.answer()
    return _courier_deactivate_common(update, context, query.edit_message_text)


def courier_base_amount_handler(update, context):
    """Recibe el monto de base declarado por el courier al activarse."""
    if not context.user_data.get("courier_activating"):
        return

    text = update.message.text.strip()
    try:
        amount = int(text.replace(".", "").replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        update.message.reply_text("Por favor escribe solo numeros. Ej: 50000")
        return

    if amount < 0:
        update.message.reply_text("El monto debe ser positivo.")
        return

    courier_id = context.user_data.get("courier_id_activating")
    if not courier_id:
        update.message.reply_text("Error: sesion expirada. Ve a Mi perfil e intenta de nuevo.")
        context.user_data.pop("courier_activating", None)
        context.user_data.pop("courier_id_activating", None)
        return

    ok, msg = can_courier_activate(courier_id)
    if not ok:
        update.message.reply_text(msg)
        context.user_data.pop("courier_activating", None)
        context.user_data.pop("courier_id_activating", None)
        return

    set_courier_available_cash(courier_id, amount)

    context.user_data.pop("courier_activating", None)
    context.user_data.pop("courier_id_activating", None)

    update.message.reply_text(
        "Base registrada: ${:,}\n\n"
        "Aun no estas ONLINE.\n"
        "Comparte tu ubicacion en vivo para activarte "
        "y comenzar a recibir pedidos.".format(amount)
    )


def global_error_handler(update, context):
    """Registra errores no capturados para diagnostico en Railway."""
    print("[ERROR][telegram] Excepcion no capturada", flush=True)
    try:
        if update and getattr(update, "effective_user", None):
            print(
                f"[ERROR][telegram] user_id={update.effective_user.id} "
                f"chat_id={getattr(getattr(update, 'effective_chat', None), 'id', None)}",
                flush=True,
            )
        if update and getattr(update, "effective_message", None):
            print(
                f"[ERROR][telegram] text={getattr(update.effective_message, 'text', None)!r}",
                flush=True,
            )
    except Exception as meta_err:
        print(f"[ERROR][telegram] meta_log_failed={meta_err}", flush=True)
    print(traceback.format_exc(), flush=True)


def main():
    init_db()
    force_platform_admin(ADMIN_USER_ID)
    ensure_pricing_defaults()

    if not BOT_TOKEN:
        raise RuntimeError("Falta BOT_TOKEN en variables de entorno.")

    # Log seguro: fingerprint del token para verificar separación DEV/PROD
    token_hash = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()[:8]
    token_suffix = BOT_TOKEN[-6:] if len(BOT_TOKEN) >= 6 else "***"
    print(f"[BOT] TOKEN fingerprint: hash={token_hash} suffix=...{token_suffix}")
    print(f"[BOT] Ambiente: {ENV}")

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_error_handler(global_error_handler)

    # -------------------------
    # Comandos básicos
    # -------------------------
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("cancel", cancel_conversacion))

    # -------------------------
    # Comandos administrativos (Plataforma y/o Admin Local según tu validación interna)
    # -------------------------
    dp.add_handler(CommandHandler("id", cmd_id))
    dp.add_handler(CommandHandler("pendientes", pendientes))
    dp.add_handler(CommandHandler("aliados_pendientes", aliados_pendientes))
    dp.add_handler(CommandHandler("repartidores_pendientes", repartidores_pendientes))
    dp.add_handler(CallbackQueryHandler(courier_pick_admin_callback, pattern=r"^courier_pick_admin_"))

    # Panel de Plataforma
    dp.add_handler(CommandHandler("admin", admin_menu))
    dp.add_handler(CommandHandler("referencias", cmd_referencias))
    # comandos de los administradores
    dp.add_handler(CommandHandler("mi_admin", mi_admin))
    dp.add_handler(CommandHandler("mi_perfil", mi_perfil))

    # Sistema de recargas
    dp.add_handler(CommandHandler("saldo", cmd_saldo))
    dp.add_handler(CommandHandler("recargas_pendientes", cmd_recargas_pendientes))
    dp.add_handler(CallbackQueryHandler(recharge_proof_callback, pattern=r"^recharge_proof_\d+$"))
    dp.add_handler(CallbackQueryHandler(recharge_callback, pattern=r"^recharge_(approve|reject)_\d+$"))
    dp.add_handler(CallbackQueryHandler(plat_recargas_callback, pattern=r"^plat_rec_"))
    dp.add_handler(CallbackQueryHandler(local_recargas_pending_callback, pattern=r"^local_recargas_pending_\d+$"))
    dp.add_handler(CallbackQueryHandler(
        admin_local_callback,
        pattern=r"^local_"
    ))

    # -------------------------
    # Callbacks (ordenados por especificidad)
    # -------------------------

    # Menú de pendientes (botones menu_*)
    dp.add_handler(CallbackQueryHandler(pendientes_callback, pattern=r"^menu_"))

    # Configuraciones (botones config_*)
    dp.add_handler(CallbackQueryHandler(admin_config_callback, pattern=r"^config_(?!pagos$)"))
    dp.add_handler(CallbackQueryHandler(reference_validation_callback, pattern=r"^ref_"))

    # Aprobación / rechazo Aliados (botones ally_approve_ID / ally_reject_ID o similar)
    # Ajusta el patrón si tu callback_data exacto difiere
    dp.add_handler(CallbackQueryHandler(ally_approval_callback, pattern=r"^ally_(approve|reject)_\d+$"))

    # Aprobación / rechazo Repartidores (botones courier_approve_ID / courier_reject_ID)
    dp.add_handler(CallbackQueryHandler(courier_approval_callback, pattern=r"^courier_(approve|reject)_\d+$"))

    # -------------------------
    # Panel admin plataforma (botones admin_*)
    # -------------------------

    # 1) Admins pendientes (handlers específicos)
    dp.add_handler(CallbackQueryHandler(admins_pendientes, pattern=r"^admin_admins_pendientes$"))
    dp.add_handler(CallbackQueryHandler(admin_ver_pendiente, pattern=r"^admin_ver_pendiente_\d+$"))
    dp.add_handler(CallbackQueryHandler(admin_aprobar_rechazar_callback, pattern=r"^admin_(aprobar|rechazar)_\d+$"))
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_(accept|reject|busy|pickup|delivered|delivered_confirm|delivered_cancel|release|release_reason|release_confirm|release_abort|cancel|find_another|wait_courier|call_courier)_\d+(?:_.+)?$"))
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_pickupconfirm_(approve|reject)_\d+$"))
    dp.add_handler(CallbackQueryHandler(pedido_incentivo_menu_callback, pattern=r"^pedido_inc_menu_\d+$"))
    dp.add_handler(CallbackQueryHandler(pedido_incentivo_existing_fixed_callback, pattern=r"^pedido_inc_\d+x(1000|1500|2000|3000)$"))
    dp.add_handler(CallbackQueryHandler(offer_suggest_inc_fixed_callback, pattern=r"^offer_inc_\d+x(1500|2000|3000)$"))
    dp.add_handler(CallbackQueryHandler(courier_earnings_callback, pattern=r"^courier_earn_"))
    dp.add_handler(CallbackQueryHandler(courier_activate_callback, pattern=r"^courier_activate$"))
    dp.add_handler(CallbackQueryHandler(courier_deactivate_callback, pattern=r"^courier_deactivate$"))
    dp.add_handler(CallbackQueryHandler(admin_change_requests_callback, pattern=r"^chgreq_"))
    dp.add_handler(CallbackQueryHandler(admin_orders_callback, pattern=r"^admpedidos_"))
    dp.add_handler(CallbackQueryHandler(admin_menu_callback, pattern=r"^admin_"))

    # Configuracion de tarifas (botones pricing_*)
    dp.add_handler(CallbackQueryHandler(tarifas_edit_callback, pattern=r"^pricing_"))

    # -------------------------
    # Live location handler para repartidores (ONLINE/PAUSADO)
    # -------------------------
    # Mensajes nuevos con ubicacion (incluye live location inicial)
    dp.add_handler(MessageHandler(Filters.location, courier_live_location_handler), group=2)
    # Mensajes editados (actualizaciones de live location en tiempo real)
    dp.add_handler(MessageHandler(
        Filters.location,
        courier_live_location_handler,
        edited_updates=True,
        message_updates=False,
    ), group=3)

    # Job periodico: expirar live locations cada 60 segundos
    updater.job_queue.run_repeating(
        courier_live_location_expired_check,
        interval=60,
        first=60,
        name="expire_live_locations",
    )

    # -------------------------
    # Conversaciones completas
    # -------------------------
    dp.add_handler(ally_conv)          # /soy_aliado
    dp.add_handler(courier_conv)       # /soy_repartidor
    dp.add_handler(nueva_ruta_conv)    # Nueva ruta (multi-parada)
    dp.add_handler(nuevo_pedido_conv)  # /nuevo_pedido
    dp.add_handler(pedido_incentivo_conv)  # Incentivo adicional post-creacion (aliado)
    dp.add_handler(offer_suggest_inc_conv)  # Incentivo desde sugerencia T+5 (aliado y admin)
    dp.add_handler(admin_pedido_conv)      # Pedido especial del Admin Local/Plataforma
    dp.add_handler(CallbackQueryHandler(handle_route_callback, pattern=r"^ruta_(aceptar|rechazar|ocupado|entregar|liberar|liberar_motivo|liberar_confirmar|liberar_abort)_"))  # callbacks de rutas al courier
    dp.add_handler(CallbackQueryHandler(preview_callback, pattern=r"^preview_"))  # preview oferta
    dp.add_handler(CallbackQueryHandler(ally_block_callback, pattern=r"^ally_block_(block|unblock)_\d+$"))  # bloqueo couriers por aliado
    dp.add_handler(CallbackQueryHandler(handle_rating_callback, pattern=r"^rating_(star|block|skip)_"))  # calificacion post-entrega
    dp.add_handler(clientes_conv)      # /clientes (agenda de clientes)
    dp.add_handler(agenda_conv)        # /agenda (Agenda del aliado)
    dp.add_handler(ally_locs_conv)     # Mis ubicaciones (aliado)
    dp.add_handler(cotizar_conv)       # /cotizar
    dp.add_handler(tarifas_conv)       # /tarifas (Admin Plataforma)
    dp.add_handler(config_alertas_oferta_conv)  # /config_alertas_oferta (Admin Plataforma)
    dp.add_handler(CallbackQueryHandler(terms_callback, pattern=r"^terms_"))  # /ternimos y condiciones

    # ConversationHandler para /recargar
    recargar_conv = ConversationHandler(
        entry_points=[
            CommandHandler("recargar", cmd_recargar),
            MessageHandler(Filters.regex(r'^(Recargar|Recargar repartidor)$'), cmd_recargar),
        ],
        states={
            RECARGAR_ROL: [CallbackQueryHandler(recargar_rol_callback)],
            RECARGAR_MONTO: [MessageHandler(Filters.text & ~Filters.command, recargar_monto)],
            RECARGAR_ADMIN: [CallbackQueryHandler(recargar_admin_callback, pattern=r"^recargar_")],
            RECARGAR_COMPROBANTE: [
                MessageHandler(Filters.photo, recargar_comprobante),
                MessageHandler(Filters.text & ~Filters.command, recargar_comprobante_texto),
            ],
        },
        fallbacks=[
            CommandHandler("recargar", cmd_recargar),
            CommandHandler("cancel", cancel_conversacion),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
        ],
        allow_reentry=True,
    )
    dp.add_handler(recargar_conv)
    dp.add_handler(profile_change_conv)

    # ConversationHandler para /configurar_pagos
    configurar_pagos_conv = ConversationHandler(
        entry_points=[
            CommandHandler("configurar_pagos", cmd_configurar_pagos),
            CallbackQueryHandler(cmd_configurar_pagos_callback, pattern=r"^config_pagos$"),
        ],
        states={
            PAGO_MENU: [CallbackQueryHandler(pagos_callback, pattern=r"^pagos_")],
            PAGO_TELEFONO: [MessageHandler(Filters.text & ~Filters.command, pago_telefono)],
            PAGO_BANCO: [MessageHandler(Filters.text & ~Filters.command, pago_banco)],
            PAGO_TITULAR: [MessageHandler(Filters.text & ~Filters.command, pago_titular)],
            PAGO_INSTRUCCIONES: [MessageHandler(Filters.text & ~Filters.command, pago_instrucciones)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversacion),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
        ],
    )
    dp.add_handler(configurar_pagos_conv)

    # -------------------------
    # Registrar ingreso externo (Admin Plataforma)
    # -------------------------
    ingreso_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ingreso_iniciar_callback, pattern=r"^ingreso_iniciar$"),
        ],
        states={
            INGRESO_MONTO: [MessageHandler(Filters.text & ~Filters.command, ingreso_monto_handler)],
            INGRESO_METODO: [CallbackQueryHandler(ingreso_metodo_callback, pattern=r"^ingreso_")],
            INGRESO_NOTA: [MessageHandler(Filters.text & ~Filters.command, ingreso_nota_handler)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversacion),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
        ],
        allow_reentry=True,
    )
    dp.add_handler(ingreso_conv)

    # -------------------------
    # Registro de Administradores Locales
    # -------------------------
    admin_conv = ConversationHandler(
        entry_points=[
            CommandHandler("soy_admin", soy_admin),
            CommandHandler("soy_administrador", soy_admin),
        ],

        states={
            LOCAL_ADMIN_NAME: [MessageHandler(Filters.text & ~Filters.command, admin_name)],
            LOCAL_ADMIN_DOCUMENT: [MessageHandler(Filters.text & ~Filters.command, admin_document)],
            LOCAL_ADMIN_TEAMNAME: [MessageHandler(Filters.text & ~Filters.command, admin_teamname)],
            LOCAL_ADMIN_PHONE: [MessageHandler(Filters.text & ~Filters.command, admin_phone)],
            LOCAL_ADMIN_CITY: [MessageHandler(Filters.text & ~Filters.command, admin_city)],
            LOCAL_ADMIN_BARRIO: [MessageHandler(Filters.text & ~Filters.command, admin_barrio)],
            LOCAL_ADMIN_RESIDENCE_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, admin_residence_address)],
            LOCAL_ADMIN_RESIDENCE_LOCATION: [
                CallbackQueryHandler(admin_geo_ubicacion_callback, pattern=r"^admin_geo_"),
                MessageHandler(Filters.location, admin_residence_location),
                MessageHandler(Filters.text & ~Filters.command, admin_residence_location),
            ],
            LOCAL_ADMIN_CEDULA_FRONT: [
                MessageHandler(Filters.photo, admin_cedula_front),
                MessageHandler(Filters.text & ~Filters.command, admin_cedula_front),
            ],
            LOCAL_ADMIN_CEDULA_BACK: [
                MessageHandler(Filters.photo, admin_cedula_back),
                MessageHandler(Filters.text & ~Filters.command, admin_cedula_back),
            ],
            LOCAL_ADMIN_SELFIE: [
                MessageHandler(Filters.photo, admin_selfie),
                MessageHandler(Filters.text & ~Filters.command, admin_selfie),
            ],
            LOCAL_ADMIN_CONFIRM: [MessageHandler(Filters.text & ~Filters.command, admin_confirm)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversacion),
            CommandHandler("menu", menu),
            MessageHandler(Filters.regex(r'(?i)^\s*volver\s*$'), volver_paso_anterior),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
        ],
    )
    dp.add_handler(admin_conv)
    dp.add_handler(MessageHandler(Filters.reply & Filters.text & ~Filters.command, chgreq_reject_reason_handler))

    dp.add_handler(MessageHandler(
        Filters.text & Filters.regex(r'^\d[\d.,\$]*$') & ~Filters.command,
        courier_base_amount_handler,
    ), group=1)
    dp.add_handler(MessageHandler(Filters.location, reference_assign_location_handler), group=1)

    # -------------------------
    # Handler para botones del menú principal (ReplyKeyboard)
    # -------------------------
    dp.add_handler(MessageHandler(
        Filters.regex(r'^(Mi aliado|Mi repartidor.*|Mi perfil|Ayuda|Menu|Mis pedidos|Mis repartidores|Mi saldo aliado|Activar repartidor|Desactivarme|Actualizar|Pedidos en curso|Mis pedidos repartidor|Mis ganancias|Mi saldo repartidor|Volver al menu)$'),
        menu_button_handler
    ))

    # Handler de saludo para onboarding (sin comandos)
    dp.add_handler(MessageHandler(
        Filters.regex(r'(?i)^\s*(hola|buenas|buenos dias|buen dia|hello|hi)\s*$') & ~Filters.command,
        saludo_menu_handler
    ))

    # Handler global para "Cancelar" y "Volver al menu" (fuera de conversaciones)
    dp.add_handler(MessageHandler(
        Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'),
        volver_menu_global
    ))

    # -------------------------
    # Notificación de arranque al Administrador de Plataforma (opcional)
    # -------------------------
    if ADMIN_USER_ID:
        try:
            updater.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text="Bot iniciado correctamente."
            )
        except Exception as e:
         print(f"[WARN] No se pudo notificar al admin: {e}")
    else:
        print("[INFO] ADMIN_USER_ID=0, se omite notificación.")


    # Iniciar el bot
    updater.start_polling(drop_pending_updates=True)
    print("[BOOT] Polling iniciado. Bot activo.")
    updater.idle()


if __name__ == "__main__":
    main()





