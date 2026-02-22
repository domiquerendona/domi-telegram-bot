import os
import hashlib
import os
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
    create_courier,
    get_courier_by_user_id,
    get_courier_by_id,
    get_courier_by_telegram_id,
    set_courier_available_cash,
    deactivate_courier,
    update_courier_live_location,
    set_courier_availability,
    expire_stale_live_locations,
    get_pending_couriers,
    get_pending_couriers_by_admin,
    update_courier_status,
    update_courier_status_by_id,
    get_all_couriers,
    update_courier,
    delete_courier,
    get_admin_link_for_courier,
    get_admin_link_for_ally,
    create_order,
    set_order_status,
    assign_order_to_courier,
    get_order_by_id,
    get_orders_by_ally,
    get_orders_by_courier,
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
)
from order_delivery import publish_order_to_couriers, order_courier_callback, ally_active_orders, admin_orders_panel, admin_orders_callback
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
    COURIER_CONFIRM,
    COURIER_TEAM,
) = range(100, 111)


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
    LOCAL_ADMIN_CONFIRM,
) = range(300, 309)


FLOW_STATE_ORDER = {
    "ally": [
        ALLY_NAME, ALLY_OWNER, ALLY_DOCUMENT, ALLY_PHONE,
        ALLY_CITY, ALLY_BARRIO, ALLY_ADDRESS, ALLY_UBICACION, ALLY_CONFIRM,
    ],
    "courier": [
        COURIER_FULLNAME, COURIER_IDNUMBER, COURIER_PHONE,
        COURIER_CITY, COURIER_BARRIO, COURIER_RESIDENCE_ADDRESS,
        COURIER_RESIDENCE_LOCATION, COURIER_PLATE, COURIER_BIKETYPE,
        COURIER_CONFIRM,
    ],
    "admin": [
        LOCAL_ADMIN_NAME, LOCAL_ADMIN_DOCUMENT, LOCAL_ADMIN_TEAMNAME,
        LOCAL_ADMIN_PHONE, LOCAL_ADMIN_CITY, LOCAL_ADMIN_BARRIO,
        LOCAL_ADMIN_RESIDENCE_ADDRESS, LOCAL_ADMIN_RESIDENCE_LOCATION,
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


def _handle_text_field_input(update, context, error_msg, storage_key, current_state, next_state, flow, next_prompt):
    """Helper para validar y almacenar campos de texto simple en flujos de registro."""
    texto = (update.message.text or "").strip()
    if not texto:
        update.message.reply_text(error_msg + _OPTIONS_HINT)
        return current_state
    context.user_data[storage_key] = texto
    update.message.reply_text(next_prompt + _OPTIONS_HINT)
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


# =========================
# Estados para cotizador interno
# =========================
COTIZAR_DISTANCIA = 901
COTIZAR_MODO = 903
COTIZAR_RECOGIDA = 904
COTIZAR_ENTREGA = 905


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
        if isinstance(admin_local, dict):
            admin_status = admin_local.get("status", "PENDING")
            team_name = admin_local.get("team_name") or "-"
            team_code = admin_local.get("team_code") or "-"
        else:
            # id, user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number, team_code
            admin_status = admin_local[6]
            team_name = admin_local[8] or "-"
            team_code = admin_local[10] if len(admin_local) > 10 and admin_local[10] else "-"

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
        admin_status = admin_local["status"] if isinstance(admin_local, dict) else admin_local[6]
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
        return "Pausar repartidor"
    return "Activar repartidor"


def get_main_menu_keyboard(missing_cmds, courier=None, ally=None):
    """Retorna el teclado principal para usuarios fuera de flujos."""
    keyboard = []
    # Fila de roles: mostrar botones de seccion segun roles del usuario
    role_row = []
    if ally:
        role_row.append('Mi aliado')
    if courier and _row_value(courier, "status") == "APPROVED":
        role_row.append('Mi repartidor')
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
        ['Nuevo pedido', 'Mis pedidos'],
        ['Clientes', 'Agenda'],
        ['Cotizar envio', 'Recargar'],
        ['Mi saldo aliado'],
        ['Volver al menu']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_repartidor_menu_keyboard(courier):
    """Retorna el teclado de seccion Repartidor."""
    courier_toggle = _get_courier_toggle_button_label(courier)
    keyboard = []
    if courier_toggle:
        keyboard.append([courier_toggle])
    keyboard.append(['Mis pedidos repartidor'])
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
    status = ally["status"] if isinstance(ally, dict) else ally[8]
    business_name = ally["business_name"] if isinstance(ally, dict) else ally[2]
    msg = (
        "🍕 GESTION DE ALIADO\n\n"
        f"Negocio: {business_name}\n"
        f"Estado: {status}\n\n"
        "Selecciona una opcion:"
    )
    reply_markup = get_ally_menu_keyboard()
    update.message.reply_text(msg, reply_markup=reply_markup)


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
    msg = (
        "🚴 GESTION DE REPARTIDOR\n\n"
        f"Nombre: {full_name}\n"
        f"Estado: {status}\n"
        f"Disponibilidad: {disp}\n\n"
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
    elif text == "Mi repartidor":
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
    elif text == "Mi saldo aliado":
        return cmd_saldo(update, context)

    # --- Botones del submenú Repartidor ---
    elif text == "Activar repartidor":
        return courier_activate_from_message(update, context)
    elif text == "Pausar repartidor":
        return courier_deactivate_from_message(update, context)
    elif text == "Mis pedidos repartidor":
        return courier_orders_history(update, context)
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
        status = existing["status"] if isinstance(existing, dict) else existing[8]
        ally_id = existing["id"] if isinstance(existing, dict) else existing[0]

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
        update.message.reply_text("Ubicación guardada.")
    else:
        update.message.reply_text(
            "No se pudo extraer la ubicación del texto.\n"
            "Envía un pin de Telegram o pega un link de Google Maps."
        )
        return ALLY_UBICACION

    return _show_ally_confirm(update, context)


def ally_ubicacion_location_handler(update, context):
    """Maneja ubicación nativa de Telegram (PIN) para registro de aliado."""
    loc = update.message.location
    context.user_data["ally_lat"] = loc.latitude
    context.user_data["ally_lng"] = loc.longitude
    update.message.reply_text("Ubicación guardada.")
    return _show_ally_confirm(update, context)


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

    if lat is None or lng is None:
        update.message.reply_text(
            "No pude detectar la ubicación. Envía un pin de Telegram o pega un link de Google Maps."
        )
        return COURIER_RESIDENCE_LOCATION

    context.user_data["residence_lat"] = lat
    context.user_data["residence_lng"] = lng
    update.message.reply_text(
        "Ubicación guardada.\n\n"
        "Escribe la placa de tu moto (o escribe 'ninguna' si no tienes):"
        "\n\nOpciones:\n- Escribe /menu para ver opciones\n- Escribe /cancel para cancelar el registro"
    )
    _set_flow_step(context, "courier", COURIER_PLATE)
    return COURIER_PLATE


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
        "Verifica tus datos de repartidor:\n\n"
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

    code = f"R-{db_user['id']:04d}"

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
    )

    courier = get_courier_by_user_id(db_user["id"])
    if not courier:
        update.message.reply_text(
            "Se registró tu usuario, pero ocurrió un error obteniendo tu perfil de repartidor.\n"
            "Intenta de nuevo."
        )
        context.user_data.clear()
        return ConversationHandler.END

    courier_id = courier["id"] if isinstance(courier, dict) else courier[0]

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

def nuevo_pedido(update, context):
    user = update.effective_user

    ensure_user(user.id, user.username)
    db_user = get_user_by_telegram_id(user.id)

    if not db_user:
        update.message.reply_text("Aun no estas registrado en el sistema. Usa /start primero.")
        return ConversationHandler.END

    ally = get_ally_by_user_id(db_user["id"])
    if not ally:
        update.message.reply_text(
            "Aun no estas registrado como aliado.\n"
            "Si tienes un negocio, registrate con /soy_aliado."
        )
        return ConversationHandler.END

    if ally["status"] != "APPROVED":
        update.message.reply_text(
            "Tu registro como aliado todavia no ha sido aprobado por el administrador.\n"
            "Cuando tu estado sea APPROVED podras crear pedidos con /nuevo_pedido."
        )
        return ConversationHandler.END

    # Si tienes ensure_terms implementado y quieres exigirlo, dejalo.
    # Si NO lo tienes, comenta estas 2 lineas.
    if not ensure_terms(update, context, user.id, role="ALLY"):
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["ally_id"] = ally["id"]
    context.user_data["active_ally_id"] = ally["id"]
    context.user_data["ally"] = ally

    # Mostrar menú reducido de flujo
    show_flow_menu(update, context, "Iniciando nuevo pedido...")

    # Mostrar selector de cliente recurrente/nuevo
    keyboard = [
        [InlineKeyboardButton("Cliente recurrente", callback_data="pedido_cliente_recurrente")],
        [InlineKeyboardButton("Cliente nuevo", callback_data="pedido_cliente_nuevo")],
    ]

    # Verificar si hay ultimo pedido para ofrecer repetir
    last_order = get_last_order_by_ally(ally["id"])
    if last_order:
        keyboard.append([InlineKeyboardButton("Repetir ultimo pedido", callback_data="pedido_repetir_ultimo")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "CREAR NUEVO PEDIDO\n\n"
        "Selecciona una opcion:",
        reply_markup=reply_markup
    )
    return PEDIDO_SELECTOR_CLIENTE


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
        query.edit_message_text("Escribe la nueva direccion de entrega:")
        return PEDIDO_DIRECCION

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
            query.edit_message_text("Direccion no encontrada. Escribe la direccion de entrega:")
            return PEDIDO_DIRECCION

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
        [InlineKeyboardButton("Recogida en tienda", callback_data="pedido_tipo_recogida")],
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

    # Verificar si ya tenemos todos los datos del cliente
    has_name = context.user_data.get("customer_name")
    has_phone = context.user_data.get("customer_phone")
    has_address = context.user_data.get("customer_address")

    if has_name and has_phone and has_address:
        # Ya tenemos datos del cliente, preguntar por base requerida
        return mostrar_pregunta_base(query, context, edit=True)
    else:
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
            items.append((qty, name))
            total += qty
            continue
        # Cantidad al final con x opcional: "platanos x3" o "platanos 3"
        m = re.match(r'^(.+?)\s+[xX]?(\d+)$', parte)
        if m:
            name = m.group(1).strip()
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
    # Preguntar por ubicación (obligatoria)
    update.message.reply_text(
        "UBICACION (obligatoria)\n\n"
        "Envia la ubicacion (PIN de Telegram), "
        "pega el enlace (Google Maps/WhatsApp) "
        "o escribe coordenadas (lat,lng).\n\n"
        "No se puede continuar sin una ubicacion valida."
    )
    return PEDIDO_UBICACION


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

    # 5) No se pudo resolver: la ubicacion es obligatoria
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
    keyboard = [
        [InlineKeyboardButton("Mi direccion base", callback_data="pickup_select_base")],
        [InlineKeyboardButton("Elegir otra", callback_data="pickup_select_lista")],
        [InlineKeyboardButton("Agregar nueva", callback_data="pickup_select_nueva")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    texto = (
        "PUNTO DE RECOGIDA\n\n"
        "Donde se recoge el pedido?"
    )

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

    # Construir botones con etiquetas (max 8)
    keyboard = []
    for loc in locations[:8]:
        btn_text = construir_etiqueta_pickup(loc)
        callback = f"pickup_list_loc_{loc['id']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback)])

    keyboard.append([InlineKeyboardButton("Agregar nueva", callback_data="pickup_list_nueva")])
    keyboard.append([InlineKeyboardButton("Volver", callback_data="pickup_list_volver")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        "ELEGIR PUNTO DE RECOGIDA\n\n"
        "Selecciona una de tus direcciones guardadas:",
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

    if data == "pickup_list_back":
        return mostrar_lista_pickups(query, context)

    # Manejar marcar/desmarcar frecuente
    if data.startswith("pickup_list_freq_"):
        parts = data.replace("pickup_list_freq_", "").split("_")
        if len(parts) == 2:
            loc_id = int(parts[0])
            new_freq = int(parts[1])
            ally = context.user_data.get("ally")
            if ally:
                set_frequent_pickup(loc_id, ally["id"], new_freq == 1)
                msg = "Marcada como frecuente" if new_freq == 1 else "Desmarcada como frecuente"
                query.answer(msg)
            return mostrar_lista_pickups(query, context)

    # Usar pickup seleccionado
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

        # Guardar pickup en user_data
        context.user_data["pickup_location"] = location
        context.user_data["pickup_label"] = location.get("label") or "Recogida"
        context.user_data["pickup_address"] = location.get("address", "")
        context.user_data["pickup_city"] = location.get("city", "")
        context.user_data["pickup_lat"] = location.get("lat")
        context.user_data["pickup_lng"] = location.get("lng")

        return continuar_despues_pickup(query, context, edit=True)

    # Seleccionar pickup - mostrar submenú
    if data.startswith("pickup_list_loc_"):
        try:
            loc_id = int(data.replace("pickup_list_loc_", ""))
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
            return mostrar_lista_pickups(query, context)

        # Mostrar submenú para esta pickup
        label = construir_etiqueta_pickup(location)
        is_freq = location.get("is_frequent", 0)

        keyboard = [
            [InlineKeyboardButton("Usar para este pedido", callback_data=f"pickup_list_usar_{loc_id}")],
        ]

        if is_freq:
            keyboard.append([InlineKeyboardButton("Quitar de frecuentes", callback_data=f"pickup_list_freq_{loc_id}_0")])
        else:
            keyboard.append([InlineKeyboardButton("Marcar como frecuente", callback_data=f"pickup_list_freq_{loc_id}_1")])

        keyboard.append([InlineKeyboardButton("Volver a lista", callback_data="pickup_list_back")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"PICKUP SELECCIONADO\n\n"
            f"{label}\n"
            f"Direccion: {location.get('address', '-')}\n"
            f"Usos: {location.get('use_count', 0)}",
            reply_markup=reply_markup
        )
        return PEDIDO_PICKUP_LISTA

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

    # Normalizar: tomar primer URL si hay varios tokens
    raw_link = text
    if "http" in text:
        raw_link = next((t for t in text.split() if t.startswith("http")), text)

    # Expandir link corto si aplica
    expanded = expand_short_url(raw_link) or raw_link

    coords = extract_lat_lng_from_text(expanded)
    if coords:
        lat, lng = coords
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
    es_link_corto_google = "maps.app.goo.gl" in raw_link or "goo.gl/maps" in raw_link

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
        context.user_data["pickup_lat"] = default_loc.get("lat")
        context.user_data["pickup_lng"] = default_loc.get("lng")

        update.message.reply_text("Ubicacion principal actualizada. Continuamos con el pedido.")
        return continuar_despues_pickup(update, context, edit=False)

    context.user_data["new_pickup_lat"] = loc.latitude
    context.user_data["new_pickup_lng"] = loc.longitude
    update.message.reply_text(
        f"Ubicacion capturada: {loc.latitude}, {loc.longitude}\n\n"
        "Ahora escribe los detalles de la direccion de recogida:\n"
        "direccion, barrio, referencias..."
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

    # Usar pickup temporal en user_data
    ally = context.user_data.get("ally")
    default_city = "Pereira"
    if ally:
        default_loc = get_default_ally_location(ally["id"])
        if default_loc and default_loc.get("city"):
            default_city = default_loc["city"]

    context.user_data["new_pickup_city"] = default_city

    # Guardar pickup temporal
    context.user_data["pickup_label"] = "Nueva"
    context.user_data["pickup_address"] = text
    context.user_data["pickup_city"] = default_city
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
            barrio="",
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


def construir_resumen_pedido(context):
    """Construye el texto del resumen del pedido."""
    tipo_servicio = context.user_data.get("service_type", "-")
    nombre = context.user_data.get("customer_name", "-")
    telefono = context.user_data.get("customer_phone", "-")
    direccion = context.user_data.get("customer_address", "-")
    pickup_label = context.user_data.get("pickup_label", "")
    pickup_address = context.user_data.get("pickup_address", "")
    distancia = context.user_data.get("quote_distance_km", 0)
    precio = context.user_data.get("quote_price", 0)
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
            tarifa_distancia = precio - buy_surcharge
            resumen += f"Tarifa distancia: ${tarifa_distancia:,}".replace(",", ".") + "\n"
            resumen += f"Total unidades: {buy_products}\n"
            if buy_surcharge > 0:
                resumen += f"Recargo productos: ${buy_surcharge:,}".replace(",", ".") + "\n"

    resumen += f"Valor del servicio: ${precio:,}".replace(",", ".") + "\n"

    if requires_cash and cash_amount > 0:
        resumen += f"Base requerida: ${cash_amount:,}".replace(",", ".") + "\n"

    resumen += "\nConfirmas este pedido?"
    return resumen


def mostrar_resumen_confirmacion(query, context, edit=True):
    """Muestra resumen del pedido con botones de confirmacion (para CallbackQuery)."""
    keyboard = [
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
    keyboard = [
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
                additional_incentive=0,
                total_fee=quote_price,
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
                )
            except Exception as e:
                print("[WARN] Error al publicar pedido a couriers:", e)

            # Incrementar contador de uso del pickup
            if pickup_location_id:
                increment_pickup_usage(pickup_location_id, ally_id)

            # Construir preview de oferta para repartidor
            preview = construir_preview_oferta(
                order_id, service_type, pickup_text, customer_address,
                distance_km, quote_price, requires_cash, cash_required_amount,
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
        ally_id, business_name, owner_name, address, city, barrio, phone, status = ally

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

        admin_id = admin["id"] if isinstance(admin, dict) else admin[0]
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
        if isinstance(c, dict):
            courier_id = c.get("courier_id") or c.get("id")
            full_name = c.get("full_name", "")
            phone = c.get("phone", "")
            city = c.get("city", "")
            barrio = c.get("barrio", "")
        else:
            courier_id = c[0]
            full_name = c[1] if len(c) > 1 else ""
            phone = c[2] if len(c) > 2 else ""
            city = c[3] if len(c) > 3 else ""
            barrio = c[4] if len(c) > 4 else ""

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

        
def soy_admin(update, context):
    user_db_id = get_user_db_id_from_update(update)
    context.user_data.clear()

    existing = get_admin_by_user_id(user_db_id)
    if existing:
        status = existing.get("status") if isinstance(existing, dict) else existing[7]
        admin_id = existing.get("id") if isinstance(existing, dict) else existing[0]

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

        team_name = existing.get("team_name") if isinstance(existing, dict) else (existing[9] if len(existing) > 9 and existing[9] else existing[3])
        doc = existing.get("document_number") if isinstance(existing, dict) else (existing[10] if len(existing) > 10 and existing[10] else "No registrado")
        full_name = existing.get("full_name") if isinstance(existing, dict) else existing[3]
        phone = existing.get("phone") if isinstance(existing, dict) else existing[4]
        city = existing.get("city") if isinstance(existing, dict) else existing[5]
        barrio = existing.get("barrio") if isinstance(existing, dict) else existing[6]

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

    if lat is None or lng is None:
        update.message.reply_text(
            "No pude detectar la ubicación. Envía un pin de Telegram o pega un link de Google Maps."
        )
        return LOCAL_ADMIN_RESIDENCE_LOCATION

    context.user_data["admin_residence_lat"] = lat
    context.user_data["admin_residence_lng"] = lng
    update.message.reply_text("Ubicación guardada.")

    # Mostrar resumen completo + requisitos + pedir ACEPTAR
    full_name = context.user_data.get("admin_name", "")
    document_number = context.user_data.get("admin_document", "")
    team_name = context.user_data.get("admin_team_name", "")
    phone = context.user_data.get("phone", "")
    city = context.user_data.get("admin_city", "")
    barrio = context.user_data.get("admin_barrio", "")
    residence_address = context.user_data.get("admin_residence_address", "")

    resumen = (
        "Verifica tus datos de Administrador Local:\n\n"
        f"Nombre: {full_name}\n"
        f"Cédula: {document_number}\n"
        f"Equipo: {team_name}\n"
        f"Teléfono: {phone}\n"
        f"Ciudad: {city}\n"
        f"Barrio: {barrio}\n"
        f"Dirección: {residence_address}\n"
        f"Ubicación: {lat}, {lng}\n\n"
        "Condiciones para Administrador Local:\n"
        "1) Para ser aprobado debes registrar al menos 10 repartidores.\n"
        "2) Cada repartidor debe tener recarga mínima de 5000.\n"
        "3) Si tu administrador local no tiene saldo activo con la plataforma, su operación queda suspendida.\n\n"
        "Si todo está correcto, escribe ACEPTAR para finalizar.\n"
        "Si quieres corregir, escribe 'volver' o usa /cancel."
    )
    update.message.reply_text(resumen)
    _set_flow_step(context, "admin", LOCAL_ADMIN_CONFIRM)
    return LOCAL_ADMIN_CONFIRM


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
        # get_admin_by_id: id[0], user_id[1], full_name[2], phone[3], city[4], barrio[5],
        #                  team_name[6], document_number[7], team_code[8], status[9], created_at[10],
        #                  residence_address[11], residence_lat[12], residence_lng[13]
        adm_full_name = admin_obj[2] or "-"
        adm_phone = admin_obj[3] or "-"
        adm_city = admin_obj[4] or "-"
        adm_barrio = admin_obj[5] or "-"
        adm_team_name = admin_obj[6] or "-"
        adm_document = admin_obj[7] or "-"
        adm_team_code = admin_obj[8] or "-"
        adm_status = admin_obj[9] or "-"

        # Tipo de admin
        tipo_admin = "PLATAFORMA" if adm_team_code == "PLATFORM" else "ADMIN LOCAL"

        # Contadores
        num_couriers = count_admin_couriers(adm_id)
        num_couriers_balance = count_admin_couriers_with_min_balance(adm_id, 5000)
        perm = get_admin_reference_validator_permission(adm_id)
        perm_status = perm["status"] if perm else "INACTIVE"

        residence_address = admin_obj[11] if len(admin_obj) > 11 else None
        residence_lat = admin_obj[12] if len(admin_obj) > 12 else None
        residence_lng = admin_obj[13] if len(admin_obj) > 13 else None
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
        if target[8] == "PLATFORM":
            query.answer("No aplica para Admin Plataforma", show_alert=True)
            return
        if new_status == "APPROVED" and target[9] != "APPROVED":
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

        if admin_obj[8] == "PLATFORM":
            query.answer("No puedes modificar a un admin de plataforma")
            return

        # Aplicar cambio
        update_admin_status_by_id(adm_id, nuevo_status, changed_by=f"tg:{update.effective_user.id}")
        query.answer("Estado actualizado a {}".format(nuevo_status))

        # Recargar el detalle
        admin_obj = get_admin_by_id(adm_id)
        adm_full_name = admin_obj[2] or "-"
        adm_phone = admin_obj[3] or "-"
        adm_city = admin_obj[4] or "-"
        adm_barrio = admin_obj[5] or "-"
        adm_team_name = admin_obj[6] or "-"
        adm_document = admin_obj[7] or "-"
        adm_team_code = admin_obj[8] or "-"
        adm_status = admin_obj[9] or "-"

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
            admin_id = t[0]
            team_name = t[1] or "-"
            team_code = t[2] or "-"
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
            admin_id = t[0]
            team_name = t[1] or "-"
            team_code = t[2] or "-"
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
            admin_id = t[0]
            team_name = t[1] or "-"
            team_code = t[2] or "-"
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
            courier_id = r[1]
            courier_name = r[2] or "-"
            balance = r[6] or 0
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
            ally_id = r[1]
            business_name = r[2] or "-"
            balance = r[7] or 0
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
        courier_id = r[1]
        courier_name = r[2] or "-"
        phone = r[3] or "-"
        city = r[4] or "-"
        barrio = r[5] or "-"
        balance = r[6] or 0
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
        ally_id = r[1]
        business_name = r[2] or "-"
        owner_name = r[3] or "-"
        phone = r[4] or "-"
        city = r[5] or "-"
        barrio = r[6] or "-"
        balance = r[7] or 0
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

        adm_full_name = admin_obj[2] or "-"
        adm_team_name = admin_obj[6] or "-"
        adm_team_code = admin_obj[8] or "-"
        adm_status = admin_obj[9] or "-"
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
            admin_id = admin["id"] if isinstance(admin, dict) else admin[0]
            return admin_orders_panel(update, context, admin_id, is_platform=True)
        query.answer("No se encontro tu perfil de admin.", show_alert=True)
        return


    if data == "admin_finanzas":
        query.answer("La sección de finanzas aún no está implementada.")
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
            admin_user_db_id = admin[1]  # users.id interno

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
            "No pude obtener la ubicacion.\n"
            "Intenta con un PIN, link de Google Maps, o coordenadas."
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


def cotizar_entrega(update, context):
    loc = _cotizar_resolver_ubicacion(update, context)
    if not loc:
        update.message.reply_text(
            "No pude obtener la ubicacion.\n"
            "Intenta con un PIN, link de Google Maps, o coordenadas."
        )
        return COTIZAR_ENTREGA

    context.user_data["cotizar_dropoff"] = loc
    pickup = context.user_data.get("cotizar_pickup")

    if not pickup:
        update.message.reply_text("Error: no se encontro el punto de recogida. Usa /cotizar de nuevo.")
        return ConversationHandler.END

    # Calcular distancia con estrategia inteligente
    result = get_smart_distance(
        pickup["lat"], pickup["lng"],
        loc["lat"], loc["lng"]
    )

    distance_km = result["distance_km"]
    config = get_pricing_config()
    precio = calcular_precio_distancia(distance_km, config)

    # Indicar fuente de distancia
    source = result["source"]
    if "google" in source:
        nota_fuente = "Distancia por ruta (Google Maps)"
    elif "haversine" in source:
        nota_fuente = "Distancia estimada (calculo local)"
    else:
        nota_fuente = f"Distancia desde cache ({source})"

    update.message.reply_text(
        f"COTIZACION\n\n"
        f"Distancia: {distance_km:.1f} km\n"
        f"Precio: ${precio:,}\n\n".replace(",", ".")
        + f"{nota_fuente}"
    )

    # Limpiar datos
    context.user_data.pop("cotizar_pickup", None)
    context.user_data.pop("cotizar_dropoff", None)
    return ConversationHandler.END


def cotizar_entrega_location(update, context):
    """Handler para PIN de Telegram en entrega."""
    return cotizar_entrega(update, context)


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

        platform_admin_id = platform_admin["id"] if isinstance(platform_admin, dict) else platform_admin[0]
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
        admin_user_field = None
        if isinstance(admin, dict):
            admin_user_field = admin.get("user_id")
        else:
            admin_user_field = admin[1] if len(admin) > 1 else None

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
        admin_id = admin[0]
        full_name = admin[2]
        city = admin[4]

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

    # id, user_id, full_name, phone, city, barrio, team_name, document_number, team_code, status, created_at, residence_address, residence_lat, residence_lng
    residence_address = admin[11] if len(admin) > 11 else None
    residence_lat = admin[12] if len(admin) > 12 else None
    residence_lng = admin[13] if len(admin) > 13 else None
    if residence_lat is not None and residence_lng is not None:
        residence_location = "{}, {}".format(residence_lat, residence_lng)
        maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(residence_lat, residence_lng)
    else:
        residence_location = "No disponible"
        maps_line = ""

    texto = (
        "Administrador pendiente:\n\n"
        f"ID: {admin[0]}\n"
        f"Nombre: {admin[2]}\n"
        f"Teléfono: {admin[3]}\n"
        f"Ciudad: {admin[4]}\n"
        f"Barrio: {admin[5]}\n"
        f"Equipo: {admin[8] or '-'}\n"
        f"Documento: {admin[7] or '-'}\n"
        f"Estado: {admin[9]}\n"
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

        keyboard = [
            [InlineKeyboardButton("Editar", callback_data="cust_dir_editar")],
            [InlineKeyboardButton("Editar nota entrega", callback_data="cust_dir_edit_nota")],
            [InlineKeyboardButton("Archivar", callback_data="cust_dir_archivar")],
            [InlineKeyboardButton("Volver", callback_data="cust_dirs")],
        ]

        query.edit_message_text(
            f"{label}\n"
            f"{address['address_text']}\n\n"
            f"Nota para entrega:\n{nota_entrega}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CLIENTES_VER_CLIENTE

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


def clientes_nuevo_direccion_text(update, context):
    """Recibe direccion y guarda el nuevo cliente."""
    address_text = update.message.text.strip()
    ally_id = context.user_data.get("active_ally_id")
    name = context.user_data.get("new_customer_name")
    phone = context.user_data.get("new_customer_phone")
    notes = context.user_data.get("new_customer_notes")
    label = context.user_data.get("new_address_label")

    try:
        customer_id = create_ally_customer(ally_id, name, phone, notes)
        create_customer_address(customer_id, label, address_text)

        keyboard = [[InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")]]
        update.message.reply_text(
            f"Cliente '{name}' creado exitosamente.\n\n"
            f"Telefono: {phone}\n"
            f"Direccion ({label}): {address_text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        update.message.reply_text(f"Error al crear cliente: {str(e)}")

    # Limpiar datos temporales
    for key in ["new_customer_name", "new_customer_phone", "new_customer_notes", "new_address_label"]:
        context.user_data.pop(key, None)

    return CLIENTES_MENU


def clientes_buscar(update, context):
    """Busca clientes por nombre o telefono."""
    query_text = update.message.text.strip()
    ally_id = context.user_data.get("active_ally_id")

    results = search_ally_customers(ally_id, query_text, limit=10)
    if not results:
        keyboard = [[InlineKeyboardButton("Volver al menu", callback_data="cust_volver_menu")]]
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

    try:
        create_customer_address(customer_id, label, address_text)
        update.message.reply_text(f"Direccion agregada: {label} - {address_text}")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

    context.user_data.pop("new_address_label", None)
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

    try:
        update_customer_address(address_id, customer_id, label, address_text)
        update.message.reply_text("Direccion actualizada.")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

    context.user_data.pop("edit_address_label", None)
    context.user_data.pop("current_address_id", None)
    return clientes_mostrar_menu(update, context, edit_message=False)


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

    status = ally[8] if isinstance(ally, (list, tuple)) else ally.get("status")
    if status != "APPROVED":
        update.message.reply_text(
            "Tu cuenta de aliado no esta aprobada.\n"
            "Cuando tu estado sea APPROVED podras usar esta funcion."
        )
        return ConversationHandler.END

    context.user_data.clear()
    ally_id = ally[0] if isinstance(ally, (list, tuple)) else ally.get("id")
    context.user_data["active_ally_id"] = ally_id
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
        query.edit_message_text("Agenda de clientes: usa /clientes para abrirla.")
        return ConversationHandler.END

    elif data == "agenda_cerrar":
        query.edit_message_text("Agenda cerrada.")
        return ConversationHandler.END

    elif data == "agenda_volver":
        return agenda_mostrar_menu(update, context, edit_message=True)

    return DIRECCIONES_MENU


def agenda_pickups_mostrar(query, context):
    """Muestra lista de direcciones de recogida del aliado."""
    ally_id = context.user_data.get("active_ally_id")
    if not ally_id:
        query.edit_message_text("Error: no hay aliado activo.")
        return ConversationHandler.END

    locations = get_ally_locations(ally_id)

    if not locations:
        keyboard = [
            [InlineKeyboardButton("Agregar nueva recogida", callback_data="agenda_pickups_nueva")],
            [InlineKeyboardButton("Volver", callback_data="agenda_volver")],
        ]
        query.edit_message_text(
            "Direcciones de recogida\n\n"
            "Estas son las direcciones desde donde normalmente recoges pedidos.\n\n"
            "No tienes direcciones de recogida guardadas.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DIRECCIONES_PICKUPS

    # Construir lista con botones
    lines = [
        "Direcciones de recogida\n\n"
        "Estas son las direcciones desde donde normalmente recoges pedidos.\n"
    ]

    keyboard = []
    for loc in locations[:10]:
        label = loc.get("label") or "Sin nombre"
        tags = []
        if loc.get("is_default"):
            tags.append("BASE")
        if loc.get("is_frequent"):
            tags.append("FRECUENTE")
        use_count = loc.get("use_count", 0)
        if use_count > 0:
            tags.append(f"x{use_count}")

        tag_str = f" ({' - '.join(tags)})" if tags else ""
        btn_text = f"{label}{tag_str}"
        lines.append(f"- {btn_text}")

    text = "\n".join(lines)

    keyboard.append([InlineKeyboardButton("Agregar nueva recogida", callback_data="agenda_pickups_nueva")])
    keyboard.append([InlineKeyboardButton("Volver", callback_data="agenda_volver")])

    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return DIRECCIONES_PICKUPS


def agenda_pickups_callback(update, context):
    """Maneja callbacks de la lista de recogidas."""
    query = update.callback_query
    query.answer()
    data = query.data

    if data == "agenda_volver":
        return agenda_mostrar_menu(update, context, edit_message=True)

    elif data == "agenda_pickups_nueva":
        query.edit_message_text(
            "Nueva direccion de recogida\n\n"
            "Envia la ubicacion (PIN de Telegram), "
            "pega el enlace (Google Maps/WhatsApp) "
            "o escribe coordenadas (lat,lng).\n\n"
            "La ubicacion es obligatoria para continuar."
        )
        return DIRECCIONES_PICKUP_NUEVA_UBICACION

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

    # Ciudad por defecto
    ally_id = context.user_data.get("active_ally_id")
    default_city = "Pereira"
    if ally_id:
        default_loc = get_default_ally_location(ally_id)
        if default_loc and default_loc.get("city"):
            default_city = default_loc["city"]
    context.user_data["new_pickup_city"] = default_city

    keyboard = [
        [InlineKeyboardButton("Si, guardar", callback_data="dir_pickup_guardar_si")],
        [InlineKeyboardButton("Cancelar", callback_data="dir_pickup_guardar_no")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"Direccion: {text}\n"
        f"Ciudad: {default_city}\n\n"
        "Deseas guardar esta direccion?",
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
            barrio="",
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
            CallbackQueryHandler(agenda_pickups_callback, pattern=r"^agenda_(volver|pickups_nueva)$")
        ],
        DIRECCIONES_PICKUP_NUEVA_UBICACION: [
            MessageHandler(Filters.location, direcciones_pickup_nueva_ubicacion_location_handler),
            MessageHandler(Filters.text & ~Filters.command, direcciones_pickup_nueva_ubicacion)
        ],
        DIRECCIONES_PICKUP_NUEVA_DETALLES: [
            MessageHandler(Filters.text & ~Filters.command, direcciones_pickup_nueva_detalles)
        ],
        DIRECCIONES_PICKUP_GUARDAR: [
            CallbackQueryHandler(direcciones_pickup_guardar_callback, pattern=r"^dir_pickup_guardar_")
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
            MessageHandler(Filters.text & ~Filters.command, clientes_nuevo_direccion_text)
        ],
        CLIENTES_BUSCAR: [
            MessageHandler(Filters.text & ~Filters.command, clientes_buscar)
        ],
        CLIENTES_VER_CLIENTE: [
            CallbackQueryHandler(clientes_ver_cliente_callback, pattern=r"^cust_(dirs|editar|edit_nombre|edit_telefono|edit_notas|archivar|dir_nueva|dir_ver_\d+|dir_editar|dir_edit_nota|dir_archivar|ver_\d+|volver_menu)$")
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
            MessageHandler(Filters.location, courier_residence_location),
            MessageHandler(Filters.text & ~Filters.command, courier_residence_location),
        ],
        COURIER_PLATE: [
            MessageHandler(Filters.text & ~Filters.command, courier_plate)
        ],
        COURIER_BIKETYPE: [
            MessageHandler(Filters.text & ~Filters.command, courier_biketype)
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

# Conversacion para /nuevo_pedido (con selector de cliente recurrente)
nuevo_pedido_conv = ConversationHandler(
    entry_points=[
        CommandHandler("nuevo_pedido", nuevo_pedido),
        MessageHandler(Filters.regex(r'^Nuevo pedido$'), nuevo_pedido),
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
            MessageHandler(Filters.location, pedido_pickup_nueva_ubicacion_location_handler),
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_pickup_nueva_ubicacion_handler)
        ],
        PEDIDO_PICKUP_NUEVA_DETALLES: [
            MessageHandler(Filters.regex(r'(?i)^\s*[\W_]*\s*(cancelar|volver al men[uú])\s*$'), cancel_por_texto),
            MessageHandler(Filters.text & ~Filters.command, pedido_pickup_nueva_detalles_handler)
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
            CallbackQueryHandler(pedido_confirmacion_callback, pattern=r"^pedido_(confirmar|cancelar)$"),
            MessageHandler(Filters.text & ~Filters.command, pedido_confirmacion)
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
        COTIZAR_DISTANCIA: [
            MessageHandler(Filters.text & ~Filters.command, cotizar_distancia),
        ],
        COTIZAR_RECOGIDA: [
            MessageHandler(Filters.location, cotizar_recogida_location),
            MessageHandler(Filters.text & ~Filters.command, cotizar_recogida),
        ],
        COTIZAR_ENTREGA: [
            MessageHandler(Filters.location, cotizar_entrega_location),
            MessageHandler(Filters.text & ~Filters.command, cotizar_entrega),
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
    save_pricing_setting(field, texto)

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

    # Soportar dict/tupla
    admin_id = admin["id"] if isinstance(admin, dict) else admin[0]

    # Traer detalle completo (incluye team_code)
    admin_full = get_admin_by_id(admin_id)
    if not admin_full:
        update.message.reply_text("No se pudo cargar tu perfil de administrador. Revisa BD.")
        return

    status = admin_full[6]
    team_name = admin_full[8] or "-"
    team_code = "-"
    if isinstance(admin_full, dict):
        team_code = admin_full.get("team_code") or "-"
    else:
        team_code = admin_full[10] if len(admin_full) > 10 and admin_full[10] else "-"

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
            [InlineKeyboardButton("⏳ Repartidores pendientes (mi equipo)", callback_data=f"local_couriers_pending_{admin_id}")],
            [InlineKeyboardButton("📦 Pedidos", callback_data="admin_pedidos_local_{}".format(admin_id))],
            [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
            [InlineKeyboardButton("Solicitudes de cambio", callback_data="admin_change_requests")],
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
        [InlineKeyboardButton("⏳ Repartidores pendientes (mi equipo)", callback_data=f"local_couriers_pending_{admin_id}")],
        [InlineKeyboardButton("📦 Pedidos de mi equipo", callback_data="admin_pedidos_local_{}".format(admin_id))],
        [InlineKeyboardButton("📋 Ver mi estado", callback_data=f"local_status_{admin_id}")],
        [InlineKeyboardButton("🔄 Verificar requisitos", callback_data=f"local_check_{admin_id}")],
        [InlineKeyboardButton("Solicitudes de cambio", callback_data="admin_change_requests")],
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
                mensaje += "   (Compartiendo ubicacion en vivo)\n"
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
        if platform_id in approved_admin_ids and (not link or link["admin_id"] != platform_id):
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

    if admin_id not in allowed_admin_ids:
        query.edit_message_text("Seleccion invalida. Usa /recargar nuevamente.")
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
            pago_texto += f"{m[2]}: {m[3]}\n"
            pago_texto += f"   Titular: {m[4]}\n"
            if m[5]:
                pago_texto += f"   {m[5]}\n"
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

    admin_id = admin["id"] if isinstance(admin, dict) else admin[0]
    context.user_data["pago_admin_id"] = admin_id

    return mostrar_menu_pagos(update, context, admin_id, es_mensaje=True)


def mostrar_menu_pagos(update, context, admin_id, es_mensaje=False):
    """Muestra el menu de cuentas de pago."""
    methods = list_payment_methods(admin_id, only_active=False)

    texto = "Tus cuentas de pago:\n\n"

    if methods:
        for m in methods:
            estado = "ON" if m[6] == 1 else "OFF"
            texto += f"{'🟢' if m[6] == 1 else '🔴'} {m[2]} - {m[3]} ({estado})\n"
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

    admin_id = admin["id"] if isinstance(admin, dict) else admin[0]
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
            estado = "ON" if m[6] == 1 else "OFF"
            emoji = "🟢" if m[6] == 1 else "🔴"
            buttons.append([InlineKeyboardButton(
                f"{emoji} {m[2]} - {m[3]} ({estado})",
                callback_data=f"pagos_ver_{m[0]}"
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

        estado = "ACTIVA" if method[6] == 1 else "INACTIVA"
        emoji = "🟢" if method[6] == 1 else "🔴"

        texto = (
            f"{emoji} Cuenta {estado}\n\n"
            f"Banco/Billetera: {method[2]}\n"
            f"Numero: {method[3]}\n"
            f"Titular: {method[4]}\n"
            f"Instrucciones: {method[5] or '-'}\n"
        )

        buttons = []
        if method[6] == 1:
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
            estado = "ACTIVA" if method[6] == 1 else "INACTIVA"
            emoji = "🟢" if method[6] == 1 else "🔴"

            texto = (
                f"{emoji} Cuenta {estado}\n\n"
                f"Banco/Billetera: {method[2]}\n"
                f"Numero: {method[3]}\n"
                f"Titular: {method[4]}\n"
                f"Instrucciones: {method[5] or '-'}\n"
            )

            buttons = []
            if method[6] == 1:
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
            estado = "ON" if m[6] == 1 else "OFF"
            emoji = "🟢" if m[6] == 1 else "🔴"
            buttons.append([InlineKeyboardButton(
                f"{emoji} {m[2]} - {m[3]} ({estado})",
                callback_data=f"pagos_ver_{m[0]}"
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

    admin_id = admin["id"] if isinstance(admin, dict) else admin[0]


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
        status = admin_full[6]
        team_code = "-"
        if isinstance(admin_full, dict):
            team_code = admin_full.get("team_code") or "-"
        else:
            team_code = admin_full[10] if len(admin_full) > 10 and admin_full[10] else "-"

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
        status = admin_full[6]
        team_code = "-"
        if isinstance(admin_full, dict):
            team_code = admin_full.get("team_code") or "-"
        else:
            team_code = admin_full[10] if len(admin_full) > 10 and admin_full[10] else "-"

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
            courier_id = c[0]
            full_name = c[1] if len(c) > 1 else ""
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

        residence_address = courier[11] if len(courier) > 11 else None
        residence_lat = courier[12] if len(courier) > 12 else None
        residence_lng = courier[13] if len(courier) > 13 else None
        if residence_lat is not None and residence_lng is not None:
            residence_location = "{}, {}".format(residence_lat, residence_lng)
            maps_line = "Maps: https://www.google.com/maps?q={},{}\n".format(residence_lat, residence_lng)
        else:
            residence_location = "No disponible"
            maps_line = ""

        texto = (
            "REPARTIDOR (pendiente de tu equipo)\n\n"
            f"ID: {courier[0]}\n"
            f"Nombre: {courier[2]}\n"
            f"Documento: {courier[3]}\n"
            f"Teléfono: {courier[4]}\n"
            f"Ciudad: {courier[5]}\n"
            f"Barrio: {courier[6]}\n"
            "Dirección residencia: {}\n"
            "Ubicación residencia: {}\n"
            "{}"
            f"Placa: {courier[7] or '-'}\n"
            f"Moto: {courier[8] or '-'}\n"
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
        return

    # Bloquear acciones de aprobar/rechazar/bloquear si Admin Local no esta APPROVED
    if data.startswith(("local_courier_approve_", "local_courier_reject_", "local_courier_block_")):
        admin_full = get_admin_by_id(admin_id)
        admin_status = admin_full[9] if admin_full else None
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
        link = get_admin_link_for_ally(ally_id)
        if link:
            keep_admin_id = link["admin_id"] if isinstance(link, dict) else link[0]
            deactivate_other_approved_admin_ally_links(ally_id, keep_admin_id)

    ally = get_ally_by_id(ally_id)
    if not ally:
        query.edit_message_text("No se encontró el aliado después de actualizar.")
        return

    # Estructura esperada: id, user_id(telegram_id), business_name, owner_name, phone, address, city, barrio, status
    ally_user_id = ally[1]       # EN TU DISEÑO ACTUAL ESTO ES telegram_id (porque create_ally usa user_id=telegram_id)
    business_name = ally[2]

    # Notificar al aliado (si falla, no rompemos el flujo)
    try:
        u = get_user_by_id(ally_user_id)
        ally_telegram_id = u["telegram_id"] if isinstance(u, dict) else u[1]

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
                keep_admin_id = link["admin_id"] if isinstance(link, dict) else link[0]
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

    # courier esperado: id, user_id(users.id), full_name, id_number, phone, city, barrio, plate, bike_type, code, status
    courier_user_db_id = courier[1]   # users.id
    full_name = courier[2]

    # Notificar al repartidor si existe get_user_by_id (recomendado).
    # Si no existe, solo omitimos notificación sin romper.
    try:
        u = get_user_by_id(courier_user_db_id)
        courier_telegram_id = u["telegram_id"] if isinstance(u, dict) else u[1]

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

    # Configurar pagos: accesible para admin plataforma y admin local
    if data == "config_pagos":
        user_tg = query.from_user
        user_row = ensure_user(user_tg.id, user_tg.username)
        user_db_id = user_row["id"] if isinstance(user_row, dict) else user_row[0]
        admin = get_admin_by_user_id(user_db_id)
        if not admin:
            query.answer("No tienes perfil de administrador.", show_alert=True)
            return
        admin_id = admin["id"] if isinstance(admin, dict) else admin[0]
        context.user_data["pago_admin_id"] = admin_id
        mostrar_menu_pagos(update, context, admin_id, es_mensaje=False)
        return

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
            ally_id = ally[0]
            business_name = ally[2]
            status = ally[8]
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
            id=ally[0],
            business_name=ally[2],
            owner_name=ally[3],
            phone=ally[4],
            address=ally[5],
            city=ally[6],
            barrio=ally[7],
            status=ally[8],
            loc=loc_text,
            maps=maps_text,
        )

        status = ally[8]
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
            courier_id = courier[0]
            full_name = courier[2]
            status = courier[10]
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
            id=courier[0],
            full_name=courier[2],
            id_number=courier[3],
            phone=courier[4],
            city=courier[5],
            barrio=courier[6],
            plate=courier[7],
            bike_type=courier[8],
            status=courier[10],
        )

        status = courier[10]
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
            courier_id = courier[0]
            full_name = courier[2]
            status = courier[10]
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
        kb = [[InlineKeyboardButton("⬅ Volver", callback_data="config_gestion_aliados")]]
        query.edit_message_text("Aliado desactivado (INACTIVE).", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("config_ally_enable_"):
        ally_id = int(data.split("_")[-1])
        update_ally_status_by_id(ally_id, "APPROVED", changed_by=f"tg:{update.effective_user.id}")
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
    tv = get_active_terms_version(role)
    if not tv:
        context.bot.send_message(
            chat_id=telegram_id,
            text="Términos no configurados para este rol. Contacta al soporte de la plataforma."
        )
        return False

    version, url, sha256 = tv

    if has_accepted_terms(telegram_id, role, version, sha256):
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

    keyboard = [
        [InlineKeyboardButton("Leer términos", url=url)],
        [
            InlineKeyboardButton("Acepto", callback_data="terms_accept_{}".format(role)),
            InlineKeyboardButton("No acepto", callback_data="terms_decline_{}".format(role)),
        ],
    ]

    if update.callback_query:
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        context.bot.send_message(chat_id=telegram_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))

    return False


def terms_callback(update, context):
    query = update.callback_query
    data = query.data
    telegram_id = query.from_user.id
    query.answer()

    if data.startswith("terms_accept_"):
        role = data.split("_", 2)[-1]
        tv = get_active_terms_version(role)
        if not tv:
            query.edit_message_text("Términos no configurados. Contacta soporte.")
            return

        version, url, sha256 = tv
        save_terms_acceptance(telegram_id, role, version, sha256, query.message.message_id)
        query.edit_message_text("Aceptación registrada. Ya puedes continuar.")
        return

    if data.startswith("terms_decline_"):
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

    location = message.location
    lat = location.latitude
    lng = location.longitude

    # Detectar si es live location (tiene live_period)
    live_period = getattr(location, 'live_period', None)

    if live_period or update.edited_message:
        # Es live location (nueva o update) -> actualizar y marcar ONLINE
        update_courier_live_location(courier["id"], lat, lng)

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
    Job periodico: revisa couriers ONLINE cuya ubicacion
    no se actualiza hace mas de 2 minutos y los pasa a PAUSADO.
    """
    expired_ids = expire_stale_live_locations(timeout_seconds=120)
    for cid in expired_ids:
        try:
            courier = get_courier_by_id(cid)
            if courier:
                user = get_user_by_id(courier["user_id"])
                if user:
                    tg_id = user["telegram_id"]
                    context.bot.send_message(
                        chat_id=tg_id,
                        text="Tu ubicacion en vivo expiro. Estas PAUSADO.\n"
                             "Comparte tu ubicacion en vivo para volver a ONLINE."
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
    reply_func("Te has desactivado. No recibiras ofertas de pedidos.")


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

    set_courier_available_cash(courier_id, amount)

    context.user_data.pop("courier_activating", None)
    context.user_data.pop("courier_id_activating", None)

    update.message.reply_text(
        "Te has activado exitosamente.\n"
        "Base declarada: ${:,}\n\n"
        "Ahora recibiras ofertas de pedidos.\n\n"
        "Comparte tu ubicacion en vivo para estar ONLINE "
        "y recibir ofertas mas cercanas.".format(amount)
    )


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
    dp.add_handler(CallbackQueryHandler(
        admin_local_callback,
        pattern=r"^local_(check|status|couriers_pending|courier_view|courier_approve|courier_reject|courier_block)_\d+$"
    ))

    # -------------------------
    # Callbacks (ordenados por especificidad)
    # -------------------------

    # Menú de pendientes (botones menu_*)
    dp.add_handler(CallbackQueryHandler(pendientes_callback, pattern=r"^menu_"))

    # Configuraciones (botones config_*)
    dp.add_handler(CallbackQueryHandler(admin_config_callback, pattern=r"^config_"))
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
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_(accept|reject|busy|pickup|delivered|release|cancel)_\d+$"))
    dp.add_handler(CallbackQueryHandler(order_courier_callback, pattern=r"^order_pickupconfirm_(approve|reject)_\d+$"))
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
    dp.add_handler(nuevo_pedido_conv)  # /nuevo_pedido
    dp.add_handler(CallbackQueryHandler(preview_callback, pattern=r"^preview_"))  # preview oferta
    dp.add_handler(clientes_conv)      # /clientes (agenda de clientes)
    dp.add_handler(agenda_conv)        # /agenda (Agenda del aliado)
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
        entry_points=[CommandHandler("configurar_pagos", cmd_configurar_pagos)],
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
                MessageHandler(Filters.location, admin_residence_location),
                MessageHandler(Filters.text & ~Filters.command, admin_residence_location),
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
        Filters.regex(r'^(Mi aliado|Mi repartidor|Mi perfil|Ayuda|Menu|Mis pedidos|Mi saldo aliado|Activar repartidor|Pausar repartidor|Mis pedidos repartidor|Mi saldo repartidor|Volver al menu)$'),
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
