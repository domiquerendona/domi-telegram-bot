import os
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import quote_plus  # Para URLs de Google Maps
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext,
)

# ------------- CONFIGURACIÓN BÁSICA -------------
TOKEN = os.getenv("BOT_TOKEN")

# ID del grupo de repartidores
COURIER_CHAT_ID = int(os.getenv("COURIER_CHAT_ID", "0"))

# ID del grupo de restaurantes (ALIADOS)
RESTAURANT_CHAT_ID = int(os.getenv("RESTAURANT_CHAT_ID", "0"))

# ID del administrador (tú)
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# Ruta de la base de datos
DB_PATH = os.getenv("DB_PATH", "domiquerendona.db")

# Estados de la conversación
(
    PEDIR_DIRECCION,
    PEDIR_VALOR_PEDIDO,
    PEDIR_FORMA_PAGO,
    PEDIR_ZONA,
    CONFIRMAR_PEDIDO,
    REG_REST_NOMBRE_NEGOCIO,
    REG_REST_ENCARGADO,
    REG_REST_TELEFONO,
    REG_REST_DIRECCION,
    REG_REST_CIUDAD,
    REG_REST_BARRIO,
    REG_COUR_NOMBRE,
    REG_COUR_IDENTIFICACION,
    REG_COUR_TELEFONO,
    REG_COUR_VEHICULO,
    REG_COUR_PLACA,
) = range(16)

# "Base de datos" simple en memoria para pedidos
orders = {}          # order_id -> dict con datos del pedido
next_order_id = 1    # contador de pedidos

# Bloqueos de repartidores: courier_id -> datetime de fin de bloqueo
bloqueos = {}

# ------------- BASE DE DATOS (SQLite) -------------
def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Tabla de restaurantes
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS restaurantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL UNIQUE,
            telegram_chat_id INTEGER NOT NULL,
            business_name TEXT NOT NULL,
            manager_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            barrio TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendiente',
            created_at TEXT NOT NULL
        )
        """
    )

    # Tabla de repartidores
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS repartidores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL UNIQUE,
            telegram_chat_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            document_number TEXT NOT NULL,
            phone TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            plate TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendiente',
            created_at TEXT NOT NULL
        )
        """
    )

    # Tabla de pedidos (historial)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY,
            restaurante_user_id INTEGER NOT NULL,
            courier_user_id INTEGER,
            direccion_entrega TEXT NOT NULL,
            valor INTEGER NOT NULL,
            forma_pago TEXT NOT NULL,
            zona TEXT NOT NULL,
            estado TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def get_restaurant_by_user_id(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, business_name, status FROM restaurantes WHERE telegram_user_id = ?",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    return row


def get_courier_by_user_id(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, full_name, status FROM repartidores WHERE telegram_user_id = ?",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    return row


def listar_restaurantes_por_estado(estado):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, business_name, manager_name, phone, city, barrio, status
        FROM restaurantes
        WHERE status = ?
        ORDER BY created_at ASC
        LIMIT 30
        """,
        (estado,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


def listar_repartidores_por_estado(estado):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT id, full_name, document_number, phone, vehicle_type, plate, status
        FROM repartidores
        WHERE status = ?
        ORDER BY created_at ASC
        LIMIT 30
        """,
        (estado,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


def crear_restaurante(telegram_user_id, telegram_chat_id, data):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO restaurantes (
            telegram_user_id, telegram_chat_id,
            business_name, manager_name, phone,
            address, city, barrio, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)
        """,
        (
            telegram_user_id,
            telegram_chat_id,
            data["nombre_negocio"],
            data["encargado"],
            data["telefono"],
            data["direccion"],
            data["ciudad"],
            data["barrio"],
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    rest_id = c.lastrowid
    conn.close()
    return rest_id


def crear_repartidor(telegram_user_id, telegram_chat_id, data):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO repartidores (
            telegram_user_id, telegram_chat_id,
            full_name, document_number, phone,
            vehicle_type, plate, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)
        """,
        (
            telegram_user_id,
            telegram_chat_id,
            data["nombre"],
            data["identificacion"],
            data["telefono"],
            data["vehiculo"],
            data["placa"],
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    cour_id = c.lastrowid
    conn.close()
    return cour_id


def actualizar_estado_restaurante(rest_id, nuevo_estado):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE restaurantes SET status = ? WHERE id = ?",
        (nuevo_estado, rest_id),
    )
    conn.commit()
    conn.close()


def actualizar_estado_repartidor(cour_id, nuevo_estado):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE repartidores SET status = ? WHERE id = ?",
        (nuevo_estado, cour_id),
    )
    conn.commit()
    conn.close()


def obtener_restaurante_por_id(rest_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, telegram_user_id, business_name, status FROM restaurantes WHERE id = ?",
        (rest_id,),
    )
    row = c.fetchone()
    conn.close()
    return row


def obtener_repartidor_por_id(cour_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, telegram_user_id, full_name, status FROM repartidores WHERE id = ?",
        (cour_id,),
    )
    row = c.fetchone()
    conn.close()
    return row


def restaurante_aprobado(user_id):
    row = get_restaurant_by_user_id(user_id)
    if not row:
        return False, "no_registrado"
    _, _, status = row
    return status == "aprobado", status


def repartidor_aprobado(user_id):
    row = get_courier_by_user_id(user_id)
    if not row:
        return False, "no_registrado"
    _, _, status = row
    return status == "aprobado", status


# ------------- FUNCIONES AUXILIARES (PEDIDOS) -------------
def esta_bloqueado(courier_id: int) -> bool:
    """Devuelve True si el repartidor sigue bloqueado, False si no."""
    if courier_id in bloqueos:
        if datetime.now() < bloqueos[courier_id]:
            return True
        del bloqueos[courier_id]
    return False


def obtener_direccion_recogida(restaurante_user_id: int) -> str:
    """
    Devuelve la dirección de recogida (restaurante) como
    'address, barrio, city' o 'No registrada' si no se encuentra.
    """
    rest = get_restaurant_by_user_id(restaurante_user_id)
    if not rest:
        return "No registrada"

    rest_id, business_name, status = rest

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT address, city, barrio
        FROM restaurantes
        WHERE id = ?
        """,
        (rest_id,),
    )
    row = c.fetchone()
    conn.close()

    if not row:
        return "No registrada"

    address, city, barrio = row
    return f"{address}, {barrio}, {city}"


def guardar_pedido_en_db(order_id: int) -> None:
    """Sincroniza el pedido en memoria con la tabla pedidos (historial)."""
    order = orders.get(order_id)
    if not order:
        return

    conn = get_connection()
    c = conn.cursor()
    now = datetime.utcnow().isoformat()

    c.execute("SELECT created_at FROM pedidos WHERE id = ?", (order_id,))
    row = c.fetchone()
    if row:
        created_at = row[0]
    else:
        created_at = now

    c.execute(
        """
        INSERT OR REPLACE INTO pedidos (
            id, restaurante_user_id, courier_user_id, direccion_entrega,
            valor, forma_pago, zona, estado, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            order["restaurante_user_id"],
            order.get("courier_id"),
            order["direccion"],
            order["valor"],
            order["forma_pago"],
            order["zona"],
            order["estado"],
            created_at,
            now,
        ),
    )
    conn.commit()
    conn.close()


def enviar_pedido_a_repartidores(order_id: int, context: CallbackContext) -> None:
    """Publica o republica un pedido en el grupo de repartidores incluyendo dirección de recogida."""
    order = orders.get(order_id)
    if not order:
        return

    if COURIER_CHAT_ID == 0:
        return

    # Obtener dirección de recogida desde el registro del restaurante
    pickup_address = obtener_direccion_recogida(order["restaurante_user_id"])

    texto = (
        f"🚨 Nuevo domicilio disponible #{order_id}\n\n"
        f"🏪 Recoger en:\n{pickup_address}\n\n"
        f"📍 Entregar en:\n{order['direccion']}\n\n"
        f"💰 Valor productos: {order['valor']}\n"
        f"💳 Forma de pago: {order['forma_pago']}\n"
        f"📌 Zona: {order['zona']}\n\n"
        "El primero que toque el botón se queda con la carrera."
    )

    keyboard = [[InlineKeyboardButton("🛵 Tomar pedido", callback_data=f"tomar_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=COURIER_CHAT_ID,
        text=texto,
        reply_markup=reply_markup,
    )


# ------------- /MI_PERFIL -------------
def mi_perfil(update: Update, context: CallbackContext):
    user = update.effective_user
    texto = ["👤 Tu perfil en DOMIQUERENDONA\n"]
    rest = get_restaurant_by_user_id(user.id)
    cour = get_courier_by_user_id(user.id)

    if not rest and not cour:
        update.message.reply_text(
            "Aún no tienes ningún perfil registrado.\n\n"
            "▫ Si eres aliado, usa /registro_restaurante.\n"
            "▫ Si eres repartidor, usa /registro_repartidor.",
        )
        return

    if rest:
        rest_id, business_name, status = rest
        texto.append(
            "🏪 Restaurante / Aliado\n"
            f"ID interno: {rest_id}\n"
            f"Nombre del negocio: {business_name}\n"
            f"Estado: {status}\n"
        )

    if cour:
        cour_id, full_name, status = cour
        texto.append(
            "🛵 Repartidor\n"
            f"ID interno: {cour_id}\n"
            f"Nombre: {full_name}\n"
            f"Estado: {status}\n"
        )

    update.message.reply_text("\n".join(texto))


# ------------- /ADMIN_PANEL -------------
def admin_panel(update: Update, context: CallbackContext):
    user = update.effective_user
    if user.id != ADMIN_USER_ID:
        update.message.reply_text("⛔ No estás autorizado para ver el panel de administración.")
        return

    rest_pend = listar_restaurantes_por_estado("pendiente")
    cour_pend = listar_repartidores_por_estado("pendiente")

    texto = (
        "🛠 Panel de administración DOMIQUERENDONA\n\n"
        f"🏪 Aliados pendientes: {len(rest_pend)}\n"
        f"🛵 Repartidores pendientes: {len(cour_pend)}\n\n"
        "Usa los botones para ver los detalles."
    )

    keyboard = [
        [InlineKeyboardButton("📋 Ver aliados pendientes", callback_data="admin_rest_pend")],
        [InlineKeyboardButton("📋 Ver repartidores pendientes", callback_data="admin_cour_pend")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(texto, reply_markup=reply_markup)


def admin_ver_rest_pend(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    if user.id != ADMIN_USER_ID:
        query.answer("No estás autorizado.", show_alert=True)
        return

    rest_pend = listar_restaurantes_por_estado("pendiente")
    if not rest_pend:
        query.edit_message_text("No hay aliados pendientes de aprobación en este momento.")
        return

    lineas = ["🏪 Aliados pendientes de aprobación:\n"]
    for (rid, business_name, manager_name, phone, city, barrio, status) in rest_pend:
        lineas.append(
            f"ID {rid} – {business_name}\n"
            f"  Encargado: {manager_name}\n"
            f"  Tel: {phone}\n"
            f"  {city} – {barrio}\n"
        )

    texto = "\n".join(lineas)
    query.edit_message_text(texto)


def admin_ver_cour_pend(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    if user.id != ADMIN_USER_ID:
        query.answer("No estás autorizado.", show_alert=True)
        return

    cour_pend = listar_repartidores_por_estado("pendiente")
    if not cour_pend:
        query.edit_message_text("No hay repartidores pendientes de aprobación en este momento.")
        return

    lineas = ["🛵 Repartidores pendientes de aprobación:\n"]
    for (cid, full_name, document_number, phone, vehicle_type, plate, status) in cour_pend:
        lineas.append(
            f"ID {cid} – {full_name}\n"
            f"  Doc: {document_number}\n"
            f"  Tel: {phone}\n"
            f"  Vehículo: {vehicle_type} – Placa: {plate}\n"
        )

    texto = "\n".join(lineas)
    query.edit_message_text(texto)


# ------------- MANEJADORES DE COMANDOS -------------
def start(update: Update, context: CallbackContext):
    chat = update.effective_chat
    msg = (
        "Hola, soy el bot de domicilios DOMIQUERENDONA 🚀\n\n"
        "Comandos principales:\n"
        "▫ /registro_restaurante – registrar un aliado (solo por privado)\n"
        "▫ /registro_repartidor – registrar un repartidor (solo por privado)\n"
        "▫ /mi_perfil – ver tu estado como aliado/repartidor\n"
        "▫ /nuevo_pedido – crear pedido (solo aliados aprobados en el grupo de ALIADOS)\n"
    )
    if chat.type != "private":
        msg += "\nPara registro usa estos comandos escribiéndome en privado."

    update.message.reply_text(msg)
    return ConversationHandler.END


# ------------- REGISTRO DE RESTAURANTES -------------
def registro_restaurante(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type != "private":
        update.message.reply_text(
            "Por seguridad, el registro de restaurantes solo se hace en chat privado.\n"
            "Envíame un mensaje directo y usa /registro_restaurante.",
        )
        return ConversationHandler.END

    existente = get_restaurant_by_user_id(user.id)
    if existente:
        rest_id, nombre, estado = existente
        update.message.reply_text(
            f"Ya tienes un registro como restaurante:\n"
            f"🏪 {nombre} (ID interno: {rest_id})\n"
            f"Estado actual: {estado}.\n\n"
            "Si necesitas cambios, contacta al administrador.",
        )
        return ConversationHandler.END

    update.message.reply_text(
        "🧾 Registro de restaurante\n\n"
        "Primero dime el nombre del negocio: "
    )
    return REG_REST_NOMBRE_NEGOCIO


def reg_rest_nombre_negocio(update: Update, context: CallbackContext):
    context.user_data["rest_reg"] = {}
    context.user_data["rest_reg"]["nombre_negocio"] = update.message.text.strip()
    update.message.reply_text("Ahora dime el nombre del encargado:")
    return REG_REST_ENCARGADO


def reg_rest_encargado(update: Update, context: CallbackContext):
    context.user_data["rest_reg"]["encargado"] = update.message.text.strip()
    update.message.reply_text("📞 Escribe el teléfono de contacto (solo números si es posible):")
    return REG_REST_TELEFONO


def reg_rest_telefono(update: Update, context: CallbackContext):
    context.user_data["rest_reg"]["telefono"] = update.message.text.strip()
    update.message.reply_text("🧭 Escribe la dirección del negocio:")
    return REG_REST_DIRECCION


def reg_rest_direccion(update: Update, context: CallbackContext):
    context.user_data["rest_reg"]["direccion"] = update.message.text.strip()
    update.message.reply_text("🏙️ Escribe la ciudad donde está el negocio:")
    return REG_REST_CIUDAD


def reg_rest_ciudad(update: Update, context: CallbackContext):
    context.user_data["rest_reg"]["ciudad"] = update.message.text.strip()
    update.message.reply_text("📌 Finalmente, escribe el barrio del negocio:")
    return REG_REST_BARRIO


def reg_rest_barrio(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    context.user_data["rest_reg"]["barrio"] = update.message.text.strip()
    data = context.user_data["rest_reg"]

    rest_id = crear_restaurante(user.id, chat.id, data)

    resumen = (
        "✅ Tu solicitud de registro como restaurante fue enviada para verificación.\n\n"
        "Estos son los datos que registraste:\n"
        f"🏪 Negocio: {data['nombre_negocio']}\n"
        f"👤 Encargado: {data['encargado']}\n"
        f"📞 Teléfono: {data['telefono']}\n"
        f"📍 Dirección: {data['direccion']}\n"
        f"🏙️ Ciudad: {data['ciudad']}\n"
        f"📌 Barrio: {data['barrio']}\n\n"
        "El administrador revisará la información y te notificará si eres aprobado."
    )
    update.message.reply_text(resumen)

    if ADMIN_USER_ID != 0:
        keyboard = [[
            InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_rest_{rest_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_rest_{rest_id}"),
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                "🧾 Nuevo registro de restaurante pendiente:\n\n"
                f"ID interno: {rest_id}\n"
                f"🏪 Negocio: {data['nombre_negocio']}\n"
                f"👤 Encargado: {data['encargado']}\n"
                f"📞 Teléfono: {data['telefono']}\n"
                f"📍 Dirección: {data['direccion']}\n"
                f"🏙️ Ciudad: {data['ciudad']}\n"
                f"📌 Barrio: {data['barrio']}\n\n"
                "¿Aprobar este restaurante?"
            ),
            reply_markup=reply_markup,
        )

    return ConversationHandler.END


# ------------- REGISTRO DE REPARTIDORES -------------
def registro_repartidor(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type != "private":
        update.message.reply_text(
            "El registro de repartidores también se hace solo en chat privado.\n"
            "Envíame un mensaje directo y usa /registro_repartidor.",
        )
        return ConversationHandler.END

    existente = get_courier_by_user_id(user.id)
    if existente:
        cour_id, nombre, estado = existente
        update.message.reply_text(
            f"Ya tienes un registro como repartidor:\n"
            f"👤 {nombre} (ID interno: {cour_id})\n"
            f"Estado actual: {estado}.\n\n"
            "Si necesitas cambios, contacta al administrador.",
        )
        return ConversationHandler.END

    update.message.reply_text(
        "🛵 Registro de repartidor\n\n"
        "Escribe tu nombre completo: "
    )
    return REG_COUR_NOMBRE


def reg_cour_nombre(update: Update, context: CallbackContext):
    context.user_data["cour_reg"] = {}
    context.user_data["cour_reg"]["nombre"] = update.message.text.strip()
    update.message.reply_text("🪪 Escribe tu número de identificación (cédula u otro):")
    return REG_COUR_IDENTIFICACION


def reg_cour_identificacion(update: Update, context: CallbackContext):
    context.user_data["cour_reg"]["identificacion"] = update.message.text.strip()
    update.message.reply_text("📞 Escribe tu teléfono de contacto:")
    return REG_COUR_TELEFONO


def reg_cour_telefono(update: Update, context: CallbackContext):
    context.user_data["cour_reg"]["telefono"] = update.message.text.strip()
    update.message.reply_text(
        "🚘 Escribe el tipo de vehículo que usas (por ejemplo: moto, bicicleta, carro):"
    )
    return REG_COUR_VEHICULO


def reg_cour_vehiculo(update: Update, context: CallbackContext):
    context.user_data["cour_reg"]["vehiculo"] = update.message.text.strip()
    update.message.reply_text("🔢 Escribe la placa del vehículo (si aplica, ej: ABC123):")
    return REG_COUR_PLACA


def reg_cour_placa(update: Update, context: CallbackContext):
    user = update.effective_user
    chat = update.effective_chat

    context.user_data["cour_reg"]["placa"] = update.message.text.strip()
    data = context.user_data["cour_reg"]

    cour_id = crear_repartidor(user.id, chat.id, data)

    resumen = (
        "✅ Tu solicitud de registro como repartidor fue enviada para verificación.\n\n"
        "Datos registrados:\n"
        f"👤 Nombre completo: {data['nombre']}\n"
        f"🪪 Identificación: {data['identificacion']}\n"
        f"📞 Teléfono: {data['telefono']}\n"
        f"🚘 Vehículo: {data['vehiculo']}\n"
        f"🔢 Placa: {data['placa']}\n\n"
        "El administrador revisará la información y te notificará si eres aprobado."
    )
    update.message.reply_text(resumen)

    if ADMIN_USER_ID != 0:
        keyboard = [[
            InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_cour_{cour_id}"),
            InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_cour_{cour_id}"),
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=(
                "🛵 Nuevo registro de repartidor pendiente:\n\n"
                f"ID interno: {cour_id}\n"
                f"👤 Nombre: {data['nombre']}\n"
                f"🪪 Identificación: {data['identificacion']}\n"
                f"📞 Teléfono: {data['telefono']}\n"
                f"🚘 Vehículo: {data['vehiculo']}\n"
                f"🔢 Placa: {data['placa']}\n\n"
                "¿Aprobar este repartidor?"
            ),
            reply_markup=reply_markup,
        )

    return ConversationHandler.END


# ------------- APROBACIÓN / RECHAZO (ADMIN) -------------
def manejar_aprobacion_restaurante(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    if user.id != ADMIN_USER_ID:
        query.answer("No estás autorizado para hacer esta acción.", show_alert=True)
        return

    data = query.data
    accion, _, id_str = data.partition("_rest_")
    rest_id = int(id_str)

    row = obtener_restaurante_por_id(rest_id)
    if not row:
        query.edit_message_text("Este registro de restaurante ya no existe.")
        return

    _, telegram_user_id, business_name, _ = row

    if accion == "aprobar":
        actualizar_estado_restaurante(rest_id, "aprobado")
        texto_admin = f"✅ Restaurante {business_name} (ID {rest_id}) fue APROBADO."
        texto_usuario = (
            "✅ Tu registro como restaurante aliado fue APROBADO.\n\n"
            f"🏪 Negocio: {business_name}\n"
            "Ya puedes usar /nuevo_pedido en el grupo de ALIADOS."
        )
    else:
        actualizar_estado_restaurante(rest_id, "rechazado")
        texto_admin = f"❌ Restaurante {business_name} (ID {rest_id}) fue RECHAZADO."
        texto_usuario = (
            "❌ Tu registro como restaurante aliado fue RECHAZADO.\n\n"
            "Si crees que es un error, contacta al administrador."
        )

    query.edit_message_text(texto_admin)
    context.bot.send_message(
        chat_id=telegram_user_id,
        text=texto_usuario,
    )


def manejar_aprobacion_repartidor(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    if user.id != ADMIN_USER_ID:
        query.answer("No estás autorizado para hacer esta acción.", show_alert=True)
        return

    data = query.data
    accion, _, id_str = data.partition("_cour_")
    cour_id = int(id_str)

    row = obtener_repartidor_por_id(cour_id)
    if not row:
        query.edit_message_text("Este registro de repartidor ya no existe.")
        return

    _, telegram_user_id, full_name, _ = row

    if accion == "aprobar":
        actualizar_estado_repartidor(cour_id, "aprobado")
        texto_admin = f"✅ Repartidor {full_name} (ID {cour_id}) fue APROBADO."
        texto_usuario = (
            "✅ Tu registro como repartidor fue APROBADO.\n\n"
            "Ya puedes tomar pedidos desde el grupo de repartidores."
        )
    else:
        actualizar_estado_repartidor(cour_id, "rechazado")
        texto_admin = f"❌ Repartidor {full_name} (ID {cour_id}) fue RECHAZADO."
        texto_usuario = (
            "❌ Tu registro como repartidor fue RECHAZADO.\n\n"
            "Si crees que es un error, contacta al administrador."
        )

    query.edit_message_text(texto_admin)
    context.bot.send_message(
        chat_id=telegram_user_id,
        text=texto_usuario,
    )


# ------------- FLUJO /nuevo_pedido (REST. APROBADOS) -------------
def nuevo_pedido(update: Update, context: CallbackContext):
    global next_order_id

    chat = update.effective_chat
    user = update.effective_user

    if RESTAURANT_CHAT_ID != 0 and chat.id != RESTAURANT_CHAT_ID:
        update.message.reply_text(
            "Este comando solo funciona en el grupo de restaurantes aliados.",
        )
        return ConversationHandler.END

    ok, estado = restaurante_aprobado(user.id)
    if not ok:
        if estado == "no_registrado":
            txt = (
                "❌ No estás registrado como restaurante.\n\n"
                "Regístrate primero usando /registro_restaurante en un chat privado conmigo."
            )
        elif estado == "pendiente":
            txt = (
                "⏳ Tu registro como restaurante aún está pendiente de aprobación.\n"
                "Espera a que el administrador lo revise."
            )
        else:
            txt = "❌ Tu registro como restaurante está rechazado. Contacta al administrador."
        update.message.reply_text(txt)
        return ConversationHandler.END

    order_id = next_order_id
    next_order_id += 1

    orders[order_id] = {
        "restaurante_chat_id": chat.id,
        "restaurante_user_id": user.id,
        "direccion": "",
        "valor": 0,
        "forma_pago": "",
        "zona": "",
        "courier_id": None,
        "estado": "creando",
    }

    context.user_data["order_id"] = order_id

    update.message.reply_text(
        "📍 Envíame la dirección del cliente:"
    )
    return PEDIR_DIRECCION


def pedir_valor(update: Update, context: CallbackContext):
    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        update.message.reply_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    orders[order_id]["direccion"] = update.message.text.strip()

    update.message.reply_text(
        "💰 ¿Cuál es el valor de los productos? (solo números)"
    )
    return PEDIR_VALOR_PEDIDO


def pedir_forma_pago(update: Update, context: CallbackContext):
    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        update.message.reply_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    texto = update.message.text.strip()
    try:
        valor = int(texto)
    except ValueError:
        update.message.reply_text(
            "Por favor envíame solo números para el valor de los productos."
        )
        return PEDIR_VALOR_PEDIDO

    orders[order_id]["valor"] = valor

    keyboard = [[
        InlineKeyboardButton("💵 Efectivo", callback_data="pago_efectivo"),
        InlineKeyboardButton("💳 Transferencia", callback_data="pago_transferencia"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Selecciona la forma de pago:",
        reply_markup=reply_markup,
    )
    return PEDIR_FORMA_PAGO


def recibir_forma_pago(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        query.edit_message_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    data = query.data
    forma = "efectivo" if data == "pago_efectivo" else "transferencia"
    orders[order_id]["forma_pago"] = forma

    query.edit_message_text(
        f"✅ Forma de pago: {forma.capitalize()}\n\n"
        "Ahora escribe la zona/barrio:"
    )
    return PEDIR_ZONA


def pedir_confirmacion(update: Update, context: CallbackContext):
    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        update.message.reply_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    orders[order_id]["zona"] = update.message.text.strip()
    order = orders[order_id]

    resumen = (
        f"🧾 Resumen del pedido #{order_id}:\n"
        f"📍 Dirección: {order['direccion']}\n"
        f"💰 Valor productos: {order['valor']}\n"
        f"💳 Forma de pago: {order['forma_pago']}\n"
        f"📌 Zona: {order['zona']}\n\n"
        "¿Confirmas este pedido?"
    )

    keyboard = [[
        InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_pedido"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_pedido"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(resumen, reply_markup=reply_markup)
    return CONFIRMAR_PEDIDO


def confirmar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if not order_id or order_id not in orders:
        query.edit_message_text("No encuentro el pedido. Usa /nuevo_pedido para empezar de nuevo.")
        return ConversationHandler.END

    # Cambiamos estado y guardamos en historial
    orders[order_id]["estado"] = "publicado"
    guardar_pedido_en_db(order_id)

    query.edit_message_text("✅ Pedido confirmado. Buscando domiciliario...")
    enviar_pedido_a_repartidores(order_id, context)
    return ConversationHandler.END


def cancelar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = context.user_data.get("order_id")
    if order_id in orders:
        orders[order_id]["estado"] = "cancelado"
        guardar_pedido_en_db(order_id)
        del orders[order_id]

    query.edit_message_text("❌ Pedido cancelado.")
    return ConversationHandler.END


def cancelar_conversacion(update: Update, context: CallbackContext):
    update.message.reply_text("Conversación cancelada. Puedes empezar de nuevo con /nuevo_pedido.")
    return ConversationHandler.END


# ------------- TOMAR PEDIDO (REPARTIDOR) -------------
def tomar_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    data = query.data
    order_id = int(data.split("_")[1])
    order = orders.get(order_id)
    if not order:
        query.edit_message_text("Este pedido ya no está disponible.")
        return

    courier = update.effective_user
    courier_id = courier.id

    ok, estado = repartidor_aprobado(courier_id)
    if not ok:
        if estado == "no_registrado":
            query.answer(
                "No estás registrado como repartidor. Regístrate en privado con /registro_repartidor.",
                show_alert=True,
            )
        elif estado == "pendiente":
            query.answer(
                "Tu registro como repartidor aún está pendiente de aprobación.",
                show_alert=True,
            )
        else:
            query.answer(
                "Tu registro como repartidor fue rechazado. Contacta al administrador.",
                show_alert=True,
            )
        return

    if esta_bloqueado(courier_id):
        desbloqueo = bloqueos[courier_id].strftime("%H:%M")
        query.answer(f"No puedes tomar pedidos hasta las {desbloqueo}.", show_alert=True)
        return

    if order["courier_id"] is not None:
        query.edit_message_text("⚠️ Otro repartidor ya tomó este pedido.")
        return

    order["courier_id"] = courier_id
    order["hora_tomado"] = datetime.now()
    order["estado"] = "tomado"

    # Guardar cambio en historial
    guardar_pedido_en_db(order_id)

    query.edit_message_text(
        "🛵 Pedido tomado por un repartidor.\n\n"
        "⏱ Recuerda: tiene máximo 15 minutos para llegar."
    )

    # Obtener dirección de recogida (restaurante)
    pickup_address = obtener_direccion_recogida(order["restaurante_user_id"])

    # URLs de Google Maps
    pickup_query = quote_plus(pickup_address)
    delivery_query = quote_plus(order["direccion"])
    maps_url_pickup = f"https://www.google.com/maps/search/?api=1&query={pickup_query}"
    maps_url_delivery = f"https://www.google.com/maps/search/?api=1&query={delivery_query}"

    # Enviar al repartidor la información completa + botones GPS
    keyboard = [
        [InlineKeyboardButton("🏪 Ruta al restaurante", url=maps_url_pickup)],
        [InlineKeyboardButton("📍 Ruta al cliente", url=maps_url_delivery)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=courier_id,
        text=(
            "✅ Pedido asignado\n\n"
            f"🏪 Recoger en:\n{pickup_address}\n\n"
            f"📍 Entregar en:\n{order['direccion']}\n\n"
            f"💰 Valor productos: {order['valor']}\n"
            f"💳 Pago: {order['forma_pago']}\n"
            f"📌 Zona: {order['zona']}\n\n"
            "Tienes máximo 15 minutos para llegar.\n"
            "Cuando estés en el restaurante, el aliado confirmará tu llegada."
        ),
        reply_markup=reply_markup,
    )

    rest_user_id = order.get("restaurante_user_id")
    if rest_user_id:
        nombre = courier.full_name
        user_link = f"@{courier.username}" if courier.username else ""
        texto_rest = (
            f"🛵 Tu pedido #{order_id} fue tomado por {nombre} {user_link}.\n\n"
            "Cuando el repartidor llegue a tu negocio, toca el botón de abajo:"
        )
        keyboard_rest = [[InlineKeyboardButton("✅ Repartidor llegó", callback_data=f"llego_{order_id}")]]
        reply_markup_rest = InlineKeyboardMarkup(keyboard_rest)
        context.bot.send_message(
            chat_id=rest_user_id,
            text=texto_rest,
            reply_markup=reply_markup_rest,
        )

    context.job_queue.run_once(
        revisar_llegada,
        15 * 60,
        context={"order_id": order_id},
    )


# ------------- LLEGADA A LA TIENDA -------------
def confirmar_llegada_repartidor(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    order = orders.get(order_id)
    if not order:
        query.edit_message_text("Este pedido ya no está disponible.")
        return

    courier_id = order.get("courier_id")
    if not courier_id:
        query.edit_message_text("Aún no hay repartidor asignado para este pedido.")
        return

    order["estado"] = "en_tienda"
    guardar_pedido_en_db(order_id)

    query.edit_message_text(
        "✅ Marcaste que el repartidor ya llegó a tu negocio."
    )

    keyboard = [[InlineKeyboardButton("✅ Ya tengo el pedido", callback_data=f"tengo_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(
        chat_id=courier_id,
        text=(
            f"ℹ️ El aliado confirmó que ya llegaste para el pedido #{order_id}.\n\n"
            "Cuando el aliado te entregue el pedido, toca el botón de abajo:"
        ),
        reply_markup=reply_markup,
    )


# ------------- FLUJO DEL REPARTIDOR: TENGO PEDIDO / ENTREGADO -------------
def tengo_pedido(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    order = orders.get(order_id)
    courier_id = query.from_user.id

    if not order or order.get("courier_id") != courier_id:
        query.answer("No encuentro este pedido o ya no está asignado a ti.", show_alert=True)
        return

    order["estado"] = "con_pedido"
    guardar_pedido_en_db(order_id)

    keyboard = [[InlineKeyboardButton("📦 Pedido entregado", callback_data=f"entregado_{order_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "👌 Marcaste que ya tienes el pedido.\n\n"
        "Cuando lo entregues al cliente, toca el botón de abajo:",
        reply_markup=reply_markup,
    )


def pedido_entregado(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    order = orders.get(order_id)
    courier_id = query.from_user.id

    if not order or order.get("courier_id") != courier_id:
        query.answer("No encuentro este pedido o ya no está asignado a ti.", show_alert=True)
        return

    order["estado"] = "entregado"
    guardar_pedido_en_db(order_id)

    query.edit_message_text(
        "✅ Marcaste este pedido como ENTREGADO. Gracias por tu servicio. 🛵"
    )

    rest_user_id = order.get("restaurante_user_id")
    if rest_user_id:
        courier = query.from_user
        nombre = courier.full_name
        user_link = f"@{courier.username}" if courier.username else ""
        context.bot.send_message(
            chat_id=rest_user_id,
            text=f"✅ Tu pedido #{order_id} fue marcado como ENTREGADO por {nombre} {user_link}.",
        )


# ------------- REVISIÓN DE LLEGADA (15 MIN) -------------
def revisar_llegada(context: CallbackContext):
    data = context.job.context
    order_id = data["order_id"]
    order = orders.get(order_id)
    if not order:
        return

    if order["estado"] != "tomado":
        return

    rest_user_id = order.get("restaurante_user_id")
    if not rest_user_id:
        return

    botones = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Repartidor llegó", callback_data=f"llego_{order_id}")],
        [
            InlineKeyboardButton("🔄 Seguir esperando", callback_data=f"esperar_{order_id}"),
            InlineKeyboardButton("❌ Buscar otro repartidor", callback_data=f"cancelar_{order_id}"),
        ],
    ])

    context.bot.send_message(
        chat_id=rest_user_id,
        text=(
            "⚠️ Han pasado 15 minutos y el repartidor aún no reporta llegada.\n\n"
            "¿Qué deseas hacer?"
        ),
        reply_markup=botones,
    )


def seguir_esperando(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    if order_id in orders:
        orders[order_id]["estado"] = "esperando"
        guardar_pedido_en_db(order_id)

    query.edit_message_text("👌 Seguirás esperando al repartidor.")


def cancelar_repartidor(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    order_id = int(query.data.split("_")[1])
    order = orders.get(order_id)
    if not order:
        query.edit_message_text("Este pedido ya no está disponible.")
        return

    courier_id = order.get("courier_id")
    if courier_id:
        bloqueos[courier_id] = datetime.now() + timedelta(hours=2)
        context.bot.send_message(
            chat_id=courier_id,
            text="⛔ Has sido suspendido 2 horas por incumplir el tiempo máximo de llegada.",
        )

    order["courier_id"] = None
    order["estado"] = "pendiente"
    guardar_pedido_en_db(order_id)

    query.edit_message_text("❌ El repartidor fue rechazado. Buscando uno nuevo...")
    enviar_pedido_a_repartidores(order_id, context)


# ------------- FUNCIÓN PRINCIPAL -------------
def main():
    init_db()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Comandos generales
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("mi_perfil", mi_perfil))
    dp.add_handler(CommandHandler("admin_panel", admin_panel))

    # Registro restaurantes
    rest_conv = ConversationHandler(
        entry_points=[CommandHandler("registro_restaurante", registro_restaurante)],
        states={
            REG_REST_NOMBRE_NEGOCIO: [MessageHandler(Filters.text & ~Filters.command, reg_rest_nombre_negocio)],
            REG_REST_ENCARGADO: [MessageHandler(Filters.text & ~Filters.command, reg_rest_encargado)],
            REG_REST_TELEFONO: [MessageHandler(Filters.text & ~Filters.command, reg_rest_telefono)],
            REG_REST_DIRECCION: [MessageHandler(Filters.text & ~Filters.command, reg_rest_direccion)],
            REG_REST_CIUDAD: [MessageHandler(Filters.text & ~Filters.command, reg_rest_ciudad)],
            REG_REST_BARRIO: [MessageHandler(Filters.text & ~Filters.command, reg_rest_barrio)],
        ],
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)],
        allow_reentry=True,
    )
    dp.add_handler(rest_conv)

    # Registro repartidores
    cour_conv = ConversationHandler(
        entry_points=[CommandHandler("registro_repartidor", registro_repartidor)],
        states={
            REG_COUR_NOMBRE: [MessageHandler(Filters.text & ~Filters.command, reg_cour_nombre)],
            REG_COUR_IDENTIFICACION: [MessageHandler(Filters.text & ~Filters.command, reg_cour_identificacion)],
            REG_COUR_TELEFONO: [MessageHandler(Filters.text & ~Filters.command, reg_cour_telefono)],
            REG_COUR_VEHICULO: [MessageHandler(Filters.text & ~Filters.command, reg_cour_vehiculo)],
            REG_COUR_PLACA: [MessageHandler(Filters.text & ~Filters.command, reg_cour_placa)],
        ],
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)],
        allow_reentry=True,
    )
    dp.add_handler(cour_conv)

    # # Flujo /nuevo_pedido
    pedido_conv = ConversationHandler(
        entry_points=[CommandHandler("nuevo_pedido", nuevo_pedido)],
        states={
            PEDIR_DIRECCION: [
                MessageHandler(Filters.text & ~Filters.command, pedir_valor)
            ],
            PEDIR_VALOR_PEDIDO: [
                MessageHandler(Filters.text & ~Filters.command, pedir_forma_pago)
            ],
            PEDIR_FORMA_PAGO: [
                CallbackQueryHandler(recibir_forma_pago)
            ],
            PEDIR_ZONA: [
                MessageHandler(Filters.text & ~Filters.command, pedir_confirmacion)
            ],
            CONFIRMAR_PEDIDO: [
                CallbackQueryHandler(
                    confirmar_pedido,
                    pattern="^confirmar_pedido$"
                ),
                CallbackQueryHandler(
                    cancelar_pedido,
                    pattern="^cancelar_pedido$"
                ),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_conversacion)],
        allow_reentry=True,
    )
    dp.add_handler(pedido_conv)

    # Acciones de repartidores y aliados
    dp.add_handler(CallbackQueryHandler(tomar_pedido, pattern=r"^tomar_\d+$"))
    dp.add_handler(CallbackQueryHandler(confirmar_llegada_repartidor, pattern=r"^llego_\d+$"))
    dp.add_handler(CallbackQueryHandler(tengo_pedido, pattern=r"^tengo_\d+$"))
    dp.add_handler(CallbackQueryHandler(pedido_entregado, pattern=r"^entregado_\d+$"))
    dp.add_handler(CallbackQueryHandler(seguir_esperando, pattern=r"^esperar_\d+$"))
    dp.add_handler(CallbackQueryHandler(cancelar_repartidor, pattern=r"^cancelar_\d+$"))

    # Aprobaciones del admin
    dp.add_handler(
        CallbackQueryHandler(
            manejar_aprobacion_restaurante,
            pattern=r"^(aprobar_rest_|rechazar_rest_)\d+$"
        )
    )
    dp.add_handler(
        CallbackQueryHandler(
            manejar_aprobacion_repartidor,
            pattern=r"^(aprobar_cour_|rechazar_cour_)\d+$"
        )
    )

    # Panel admin: ver listas
    dp.add_handler(CallbackQueryHandler(admin_ver_rest_pend, pattern=r"^admin_rest_pend$"))
    dp.add_handler(CallbackQueryHandler(admin_ver_cour_pend, pattern=r"^admin_cour_pend$"))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
