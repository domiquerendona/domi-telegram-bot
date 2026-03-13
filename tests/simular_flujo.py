#!/usr/bin/env python3
"""
Simulador de flujos del bot — sin cuenta real de Telegram.

Ejecutar desde Backend/:
    python ../tests/simular_flujo.py [flujo]

Flujos disponibles:
    registro_repartidor   (default)
    registro_aliado
    registro_admin
    start

Ejemplos:
    python ../tests/simular_flujo.py
    python ../tests/simular_flujo.py registro_aliado
"""

import os
import sys
import tempfile
import atexit

# ── 1. Configurar entorno ANTES de cualquier import del proyecto ──────────────
_fd, _DB_PATH = tempfile.mkstemp(prefix="domi_sim_", suffix=".db")
os.close(_fd)

os.environ["DB_PATH"] = _DB_PATH
os.environ.pop("DATABASE_URL", None)
os.environ["BOT_TOKEN"] = "0:fake_token_simulador"
os.environ["ADMIN_USER_ID"] = "99999"
os.environ["ENV"] = "LOCAL"

@atexit.register
def _limpiar_db():
    try:
        os.remove(_DB_PATH)
    except FileNotFoundError:
        pass

# ── 2. Imports del proyecto ───────────────────────────────────────────────────
# sys.path debe incluir Backend/ (desde donde se ejecuta este script)
sys.path.insert(0, os.getcwd())

import db
db.init_db()  # crear tablas antes de importar main

from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup


# ── 3. Clases "falsas" que imitan los objetos de Telegram ────────────────────

W = 62  # ancho de la caja visual


def _recuadro(chat_id, texto, reply_markup=None):
    """Imprime el mensaje del bot en una caja visual."""
    print(f"\n┌{'─' * W}┐")
    print(f"│  BOT  →  usuario {chat_id:<{W - 18}}│")
    print(f"├{'─' * W}┤")

    for linea in (texto or "").split("\n"):
        # partir líneas largas
        while len(linea) > W - 2:
            print(f"│ {linea[:W - 2]} │")
            linea = linea[W - 2:]
        print(f"│ {linea:<{W - 2}} │")

    # Renderizar teclado
    botones = _renderizar_teclado(reply_markup)
    if botones:
        print(f"├{'─' * W}┤")
        for fila in botones:
            print(f"│  {fila:<{W - 3}}│")

    print(f"└{'─' * W}┘")


def _renderizar_teclado(markup):
    """Convierte InlineKeyboardMarkup o ReplyKeyboardMarkup en texto."""
    if markup is None or isinstance(markup, ReplyKeyboardRemove):
        return []

    filas = []
    if isinstance(markup, InlineKeyboardMarkup):
        for fila in markup.inline_keyboard:
            filas.append("  ".join(f"[ {btn.text} ]" for btn in fila))
    elif isinstance(markup, ReplyKeyboardMarkup):
        for fila in markup.keyboard:
            items = []
            for btn in fila:
                texto_btn = btn if isinstance(btn, str) else btn.text
                items.append(f"[ {texto_btn} ]")
            filas.append("  ".join(items))

    return filas


class FakeLocation:
    def __init__(self, lat, lng):
        self.latitude = lat
        self.longitude = lng


class FakePhotoSize:
    file_id = "FOTO_SIMULADA_12345"


class FakeMessage:
    """Imita telegram.Message."""

    def __init__(self, chat_id, text=None, location=None, photo=False):
        self.chat_id = chat_id
        self.text = text
        self.location = location
        self.photo = [FakePhotoSize()] if photo else []

    def reply_text(self, text, reply_markup=None, **kwargs):
        _recuadro(self.chat_id, text, reply_markup)

    def reply_photo(self, photo=None, caption=None, reply_markup=None, **kwargs):
        _recuadro(self.chat_id, f"[IMAGEN] {caption or ''}", reply_markup)


class FakeCallbackQuery:
    """Imita telegram.CallbackQuery (botón inline presionado)."""

    def __init__(self, chat_id, data):
        self.chat_id = chat_id
        self.data = data

    def answer(self, text=None, **kwargs):
        if text:
            print(f"\n  ↳ [alerta emergente para {self.chat_id}]: {text}")

    def edit_message_text(self, text, reply_markup=None, **kwargs):
        _recuadro(self.chat_id, text, reply_markup)


class FakeBot:
    """Imita telegram.Bot — todos los envíos se imprimen, no van a Telegram."""

    def send_message(self, chat_id, text, reply_markup=None, **kwargs):
        _recuadro(chat_id, text, reply_markup)

    def send_photo(self, chat_id, photo=None, caption=None, reply_markup=None, **kwargs):
        _recuadro(chat_id, f"[IMAGEN] {caption or ''}", reply_markup)

    def forward_message(self, *args, **kwargs):
        pass  # silenciar reenvíos en la simulación

    def send_document(self, chat_id, document=None, caption=None, **kwargs):
        print(f"\n  → [documento para {chat_id}]: {caption or ''}")

    def send_audio(self, *args, **kwargs):
        pass

    def send_voice(self, *args, **kwargs):
        pass


class FakeJobQueue:
    """Imita telegram.ext.JobQueue — los jobs se ignoran en la simulación."""

    def run_once(self, *args, **kwargs):
        pass

    def run_repeating(self, *args, **kwargs):
        pass

    def get_jobs_by_name(self, name):
        return []


def _make_effective_user(telegram_id):
    from unittest.mock import MagicMock
    u = MagicMock()
    u.id = telegram_id
    u.first_name = f"Sim{telegram_id}"
    u.username = f"sim{telegram_id}"
    return u


def hacer_update(telegram_id, *, texto=None, callback=None, gps=None, foto=False):
    """
    Construye un Update falso.

    Parámetros:
        telegram_id  — ID numérico del usuario simulado
        texto        — lo que el usuario "escribe"
        callback     — callback_data del botón que "presionó"
        gps          — tupla (lat, lng) para simular pin de ubicación
        foto         — True para simular que el usuario envió una foto
    """
    from unittest.mock import MagicMock

    update = MagicMock()
    update.effective_user = _make_effective_user(telegram_id)
    update.effective_chat.id = telegram_id

    if callback:
        update.message = None
        update.callback_query = FakeCallbackQuery(telegram_id, callback)
        update.callback_query.from_user = update.effective_user
    else:
        location = FakeLocation(*gps) if gps else None
        msg = FakeMessage(telegram_id, text=texto, location=location, photo=foto)
        update.message = msg
        update.callback_query = None

    return update


def hacer_context(user_data=None, bot_data=None):
    """Construye un CallbackContext falso con FakeBot y FakeJobQueue."""
    from unittest.mock import MagicMock

    ctx = MagicMock()
    ctx.user_data = {} if user_data is None else user_data
    ctx.bot_data = {} if bot_data is None else bot_data
    ctx.bot = FakeBot()
    ctx.job_queue = FakeJobQueue()
    return ctx


# ── 4. Helpers de presentación ────────────────────────────────────────────────

def _titulo(texto):
    print(f"\n{'=' * (W + 2)}")
    print(f"  {texto}")
    print(f"{'=' * (W + 2)}")


def _paso(numero, descripcion):
    print(f"\n{'─' * (W + 2)}")
    print(f"  Paso {numero}: {descripcion}")
    print(f"{'─' * (W + 2)}")


def _usuario_escribe(telegram_id, texto):
    print(f"\n  👤 usuario {telegram_id} escribe: «{texto}»")


def _usuario_envia_foto(telegram_id, descripcion="foto"):
    print(f"\n  👤 usuario {telegram_id} envía: [📷 {descripcion}]")


def _usuario_envia_gps(telegram_id, lat, lng):
    print(f"\n  👤 usuario {telegram_id} envía: [📍 GPS {lat}, {lng}]")


def _usuario_presiona(telegram_id, texto_boton, callback_data):
    print(f"\n  👤 usuario {telegram_id} presiona botón: «{texto_boton}» ({callback_data})")


def _estado_db(descripcion, query_fn):
    """Muestra el resultado de una consulta a la DB de simulación."""
    print(f"\n  📊 DB → {descripcion}:")
    resultado = query_fn()

    def _to_dict(row):
        try:
            return dict(row)
        except Exception:
            return row

    if resultado:
        if isinstance(resultado, list):
            for row in resultado:
                row_d = _to_dict(row)
                if isinstance(row_d, dict):
                    for k, v in row_d.items():
                        print(f"       {k}: {v}")
                    print()
                else:
                    print(f"       {row_d}")
        else:
            row_d = _to_dict(resultado)
            if isinstance(row_d, dict):
                for k, v in row_d.items():
                    print(f"       {k}: {v}")
            else:
                print(f"       {row_d}")
    else:
        print("       (vacío)")


# ── 5. Flujos simulados ───────────────────────────────────────────────────────

def flujo_registro_repartidor():
    """
    Simula el flujo completo de registro de un repartidor nuevo.
    El usuario con telegram_id=10001 hace /soy_repartidor y completa todo.
    """
    import main  # importar aquí: la DB ya existe y las env vars están listas

    _titulo("FLUJO: Registro de Repartidor  (/soy_repartidor)")

    TID = 10001       # telegram_id del repartidor simulado
    ctx = hacer_context()

    # ── Paso 1: /soy_repartidor ───────────────────────────────────────────────
    _paso(1, "/soy_repartidor — inicio del flujo")
    _usuario_escribe(TID, "/soy_repartidor")
    estado = main.soy_repartidor(hacer_update(TID, texto="/soy_repartidor"), ctx)
    print(f"\n  → estado de conversación devuelto: {estado} (COURIER_FULLNAME = {main.COURIER_FULLNAME})")

    # ── Paso 2: nombre completo ───────────────────────────────────────────────
    _paso(2, "Usuario escribe su nombre completo")
    _usuario_escribe(TID, "Carlos Pérez López")
    estado = main.courier_fullname(hacer_update(TID, texto="Carlos Pérez López"), ctx)
    print(f"  → user_data['full_name'] = {ctx.user_data.get('full_name')}")

    # ── Paso 2b: validación — nombre vacío ────────────────────────────────────
    _paso("2b", "Validación: nombre vacío → el bot pide corregir")
    ctx2 = hacer_context()  # contexto limpio para mostrar la validación
    _usuario_escribe(TID, "")
    main.soy_repartidor(hacer_update(TID, texto="/soy_repartidor"), ctx2)
    main.courier_fullname(hacer_update(TID, texto="   "), ctx2)  # espacios = vacío

    # ── Paso 3: número de cédula ──────────────────────────────────────────────
    _paso(3, "Usuario escribe su número de cédula")
    _usuario_escribe(TID, "1234567890")
    estado = main.courier_idnumber(hacer_update(TID, texto="1234567890"), ctx)
    print(f"  → user_data['id_number'] = {ctx.user_data.get('id_number')}")

    # ── Paso 4: teléfono ──────────────────────────────────────────────────────
    _paso(4, "Usuario escribe su teléfono")
    _usuario_escribe(TID, "3001234567")
    estado = main.courier_phone(hacer_update(TID, texto="3001234567"), ctx)
    print(f"  → user_data['phone'] = {ctx.user_data.get('phone')}")

    # ── Paso 5: ciudad ────────────────────────────────────────────────────────
    _paso(5, "Usuario escribe la ciudad")
    _usuario_escribe(TID, "Pereira")
    estado = main.courier_city(hacer_update(TID, texto="Pereira"), ctx)

    # ── Paso 6: barrio ────────────────────────────────────────────────────────
    _paso(6, "Usuario escribe el barrio")
    _usuario_escribe(TID, "Cuba")
    estado = main.courier_barrio(hacer_update(TID, texto="Cuba"), ctx)

    # ── Paso 7: dirección de residencia ───────────────────────────────────────
    _paso(7, "Usuario escribe su dirección")
    _usuario_escribe(TID, "Calle 15 # 8-40, Cuba")
    estado = main.courier_residence_address(hacer_update(TID, texto="Calle 15 # 8-40, Cuba"), ctx)

    # ── Paso 8: ubicación GPS ─────────────────────────────────────────────────
    _paso(8, "Usuario envía pin GPS de su residencia")
    LAT, LNG = 4.8133, -75.6961   # coordenadas de prueba (Pereira)
    _usuario_envia_gps(TID, LAT, LNG)
    estado = main.courier_residence_location(hacer_update(TID, gps=(LAT, LNG)), ctx)
    print(f"  → user_data['residence_lat'] = {ctx.user_data.get('residence_lat')}")

    # ── Paso 9: placa ─────────────────────────────────────────────────────────
    _paso(9, "Usuario escribe la placa de su moto")
    _usuario_escribe(TID, "ABC123")
    estado = main.courier_plate(hacer_update(TID, texto="ABC123"), ctx)

    # ── Paso 10: tipo de moto ─────────────────────────────────────────────────
    _paso(10, "Usuario escribe el tipo de moto")
    _usuario_escribe(TID, "Honda CB125F")
    estado = main.courier_biketype(hacer_update(TID, texto="Honda CB125F"), ctx)

    # ── Paso 11: foto cédula frente ───────────────────────────────────────────
    _paso(11, "Usuario envía foto del frente de la cédula")
    _usuario_envia_foto(TID, "cédula frente")
    estado = main.courier_cedula_front(hacer_update(TID, foto=True), ctx)
    print(f"  → user_data['cedula_front_file_id'] = {ctx.user_data.get('cedula_front_file_id')}")

    # ── Paso 12: foto cédula reverso ──────────────────────────────────────────
    _paso(12, "Usuario envía foto del reverso de la cédula")
    _usuario_envia_foto(TID, "cédula reverso")
    estado = main.courier_cedula_back(hacer_update(TID, foto=True), ctx)

    # ── Paso 13: selfie ───────────────────────────────────────────────────────
    _paso(13, "Usuario envía selfie → bot muestra resumen para confirmar")
    _usuario_envia_foto(TID, "selfie")
    estado = main.courier_selfie(hacer_update(TID, foto=True), ctx)

    # ── Paso 14: confirmación ─────────────────────────────────────────────────
    _paso(14, "Usuario escribe SI para confirmar")
    _usuario_escribe(TID, "SI")
    estado = main.courier_confirm(hacer_update(TID, texto="SI"), ctx)

    # ── Verificar resultado en DB ─────────────────────────────────────────────
    print(f"\n  {'─' * W}")
    print(f"  RESULTADO EN BASE DE DATOS:")

    _estado_db(
        "registro del repartidor",
        lambda: db.get_courier_by_telegram_id(TID)
    )

    print(f"\n  {'─' * W}")
    print("  Flujo completado.\n")
    print("  Lo que viste arriba es EXACTAMENTE lo que el usuario vería en Telegram,")
    print("  incluyendo los botones. No se conectó a ningún servidor externo.\n")


def flujo_start():
    """Simula /start para un usuario nuevo y uno ya registrado como repartidor."""
    import main

    _titulo("FLUJO: /start — bienvenida")

    # ── Usuario completamente nuevo ───────────────────────────────────────────
    _paso(1, "Usuario nuevo (nunca ha usado el bot)")
    TID_NUEVO = 20001
    _usuario_escribe(TID_NUEVO, "/start")
    main.start(hacer_update(TID_NUEVO, texto="/start"), hacer_context())

    # ── Admin de plataforma ───────────────────────────────────────────────────
    _paso(2, "Admin de plataforma (ADMIN_USER_ID=99999)")
    TID_ADMIN = 99999
    _usuario_escribe(TID_ADMIN, "/start")
    main.start(hacer_update(TID_ADMIN, texto="/start"), hacer_context())


def flujo_registro_aliado():
    """
    Simula el flujo completo de registro de un aliado.
    Muestra también la selección de equipo con botones.
    """
    import main

    _titulo("FLUJO: Registro de Aliado  (/soy_aliado)")

    TID = 30001
    ctx = hacer_context()

    _paso(1, "/soy_aliado — inicio")
    _usuario_escribe(TID, "/soy_aliado")
    main.soy_aliado(hacer_update(TID, texto="/soy_aliado"), ctx)

    _paso(2, "Nombre del negocio")
    _usuario_escribe(TID, "Restaurante El Sabor")
    main.ally_name(hacer_update(TID, texto="Restaurante El Sabor"), ctx)

    _paso(3, "Nombre del dueño")
    _usuario_escribe(TID, "María González")
    main.ally_owner(hacer_update(TID, texto="María González"), ctx)

    _paso(4, "Número de documento")
    _usuario_escribe(TID, "40123456")
    main.ally_document(hacer_update(TID, texto="40123456"), ctx)

    _paso(5, "Teléfono del negocio")
    _usuario_escribe(TID, "3109876543")
    main.ally_phone(hacer_update(TID, texto="3109876543"), ctx)

    _paso(6, "Ciudad")
    _usuario_escribe(TID, "Pereira")
    main.ally_city(hacer_update(TID, texto="Pereira"), ctx)

    _paso(7, "Barrio")
    _usuario_escribe(TID, "Centro")
    main.ally_barrio(hacer_update(TID, texto="Centro"), ctx)

    _paso(8, "Dirección del negocio")
    _usuario_escribe(TID, "Carrera 8 # 19-20, Centro")
    main.ally_address(hacer_update(TID, texto="Carrera 8 # 19-20, Centro"), ctx)

    _paso(9, "Ubicación GPS del negocio")
    LAT, LNG = 4.8141, -75.6952
    _usuario_envia_gps(TID, LAT, LNG)
    main.ally_ubicacion(hacer_update(TID, gps=(LAT, LNG)), ctx)

    _paso(10, "Usuario confirma con SI")
    _usuario_escribe(TID, "SI")
    main.ally_confirm(hacer_update(TID, texto="SI"), ctx)

    _paso(11, "Selección de equipo (botones inline) — elige Admin de Plataforma")
    # La plataforma siempre aparece. Simular que elige el botón de plataforma:
    pid = db.get_platform_admin_id()
    cb = f"ally_team_{pid}" if pid else "ally_team_0"
    _usuario_presiona(TID, "Ninguno (Admin de Plataforma)", cb)
    main.ally_team_callback(hacer_update(TID, callback=cb), ctx)

    _estado_db("registro del aliado", lambda: db.get_ally_by_telegram_id(TID))
    print()


def flujo_registro_admin():
    """Simula el flujo de registro de Administrador Local."""
    import main

    _titulo("FLUJO: Registro de Administrador Local  (/soy_admin)")

    TID = 40001
    ctx = hacer_context()

    _paso(1, "/soy_admin — inicio")
    _usuario_escribe(TID, "/soy_admin")
    main.soy_admin(hacer_update(TID, texto="/soy_admin"), ctx)

    _paso(2, "Nombre completo")
    _usuario_escribe(TID, "Luis Felipe Torres")
    main.admin_name(hacer_update(TID, texto="Luis Felipe Torres"), ctx)

    _paso(3, "Número de documento")
    _usuario_escribe(TID, "88012345")
    main.admin_document(hacer_update(TID, texto="88012345"), ctx)

    _paso(4, "Nombre del equipo")
    _usuario_escribe(TID, "Equipo Risaralda")
    main.admin_teamname(hacer_update(TID, texto="Equipo Risaralda"), ctx)

    _paso(5, "Teléfono")
    _usuario_escribe(TID, "3005551234")
    main.admin_phone(hacer_update(TID, texto="3005551234"), ctx)

    _paso(6, "Ciudad")
    _usuario_escribe(TID, "Pereira")
    main.admin_city(hacer_update(TID, texto="Pereira"), ctx)

    _paso(7, "Barrio")
    _usuario_escribe(TID, "Circunvalar")
    main.admin_barrio(hacer_update(TID, texto="Circunvalar"), ctx)

    _paso(8, "Dirección de residencia")
    _usuario_escribe(TID, "Avenida 30 de Agosto # 40-10")
    main.admin_residence_address(hacer_update(TID, texto="Avenida 30 de Agosto # 40-10"), ctx)

    _paso(9, "Ubicación GPS")
    LAT, LNG = 4.8119, -75.6900
    _usuario_envia_gps(TID, LAT, LNG)
    main.admin_residence_location(hacer_update(TID, gps=(LAT, LNG)), ctx)

    _paso(10, "Foto cédula frente")
    _usuario_envia_foto(TID, "cédula frente")
    main.admin_cedula_front(hacer_update(TID, foto=True), ctx)

    _paso(11, "Foto cédula reverso")
    _usuario_envia_foto(TID, "cédula reverso")
    main.admin_cedula_back(hacer_update(TID, foto=True), ctx)

    _paso(12, "Selfie")
    _usuario_envia_foto(TID, "selfie")
    main.admin_selfie(hacer_update(TID, foto=True), ctx)

    _paso(13, "Acepta condiciones escribiendo ACEPTAR")
    _usuario_escribe(TID, "ACEPTAR")
    main.admin_confirm(hacer_update(TID, texto="ACEPTAR"), ctx)

    _estado_db("registro del admin local", lambda: db.get_admin_by_telegram_id(TID))
    print()


# ── 6. Entry point ────────────────────────────────────────────────────────────

FLUJOS = {
    "registro_repartidor": flujo_registro_repartidor,
    "registro_aliado":     flujo_registro_aliado,
    "registro_admin":      flujo_registro_admin,
    "start":               flujo_start,
}

if __name__ == "__main__":
    nombre = sys.argv[1] if len(sys.argv) > 1 else "registro_repartidor"

    if nombre not in FLUJOS:
        print(f"Flujo '{nombre}' no encontrado.")
        print(f"Disponibles: {', '.join(FLUJOS)}")
        sys.exit(1)

    print(f"\nSimulando: {nombre}")
    print(f"DB temporal: {_DB_PATH}")

    try:
        FLUJOS[nombre]()
    except Exception as exc:
        import traceback
        print(f"\n[ERROR en simulación] {exc}")
        traceback.print_exc()
        sys.exit(1)
