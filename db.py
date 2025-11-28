import sqlite3
import os

# Ruta del archivo de base de datos
DB_PATH = os.getenv("DB_PATH", "domiquerendona.db")


def get_connection():
    """Devuelve una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Crea las tablas básicas si no existen."""
    conn = get_connection()
    cur = conn.cursor()

    # Tabla de usuarios de Telegram
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            role TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    # Tabla de aliados (negocios)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS allies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_name TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            barrio TEXT NOT NULL,
            phone TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # Tabla de repartidores
    cur.execute("""
        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            id_number TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            barrio TEXT NOT NULL,
            plate TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'PENDING',
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # Tabla de direcciones de recogida de cada aliado (hasta 5 por aliado)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ally_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            label TEXT NOT NULL,          -- Nombre de la sede: Principal, Bodega, Sede Cuba, etc.
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            barrio TEXT NOT NULL,
            phone TEXT,                   -- Teléfono de esa sede (opcional)
            is_default INTEGER DEFAULT 0, -- 1 = dirección principal
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ally_id) REFERENCES allies(id)
        );
    """)

    # Tabla de configuración general (clave-valor)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    # Tabla de pedidos (orders)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            courier_id INTEGER,
            status TEXT NOT NULL,   -- CREATED, PUBLISHED, ACCEPTED, PICKUP_CONFIRMED, DELIVERED, CANCELED

            -- Datos del cliente
            customer_name TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            customer_city TEXT,
            customer_barrio TEXT,
    
            -- Dirección de recogida
            pickup_location_id INTEGER,   -- referencia a ally_locations

            -- Pago en el negocio
            pay_at_store_required INTEGER DEFAULT 0,  -- 0 = no, 1 = sí
            pay_at_store_amount INTEGER DEFAULT 0,

            -- Cálculos de tarifa
            base_fee INTEGER NOT NULL,           -- tarifa base del pedido (sin incentivos)
            distance_km REAL,                    -- distancia aproximada
            rain_extra INTEGER DEFAULT 0,
            high_demand_extra INTEGER DEFAULT 0,
            night_extra INTEGER DEFAULT 0,
            additional_incentive INTEGER DEFAULT 0,  -- "incentivo adicional" (antes propina)
            total_fee INTEGER NOT NULL,              -- valor total que ve el aliado / paga el cliente

            -- Instrucciones del aliado
            instructions TEXT,

            -- Tiempos del pedido
            created_at TEXT DEFAULT (datetime('now')),
            published_at TEXT,
            accepted_at TEXT,
            pickup_confirmed_at TEXT,
            delivered_at TEXT,
            canceled_at TEXT,
            cancel_reason TEXT,

            FOREIGN KEY (ally_id) REFERENCES allies(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id),
            FOREIGN KEY (pickup_location_id) REFERENCES ally_locations(id)
        );
    """)

    # Tabla de calificaciones del repartidor
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courier_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            courier_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,  -- 1 a 5
            comment TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id)
        );
    """)

    conn.commit()
    conn.close()


# ---------- USUARIOS ----------

def get_user_by_telegram_id(telegram_id: int):
    """Devuelve el usuario según su telegram_id o None si no existe."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?;", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row


def ensure_user(telegram_id: int, username: str = None):
    """
    Si el usuario no existe en la tabla users, lo crea.
    Devuelve siempre la fila del usuario.
    """
    user = get_user_by_telegram_id(telegram_id)
    if user:
        return user

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (telegram_id, username, role) VALUES (?, ?, NULL);",
        (telegram_id, username),
    )
    conn.commit()
    conn.close()
    return get_user_by_telegram_id(telegram_id)


# ---------- CONFIGURACIÓN GLOBAL (settings) ----------

def get_setting(key: str, default: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?;", (key,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return default
    return row[0]


def set_setting(key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value;
    """, (key, value))
    conn.commit()
    conn.close()


# ---------- ALIADOS ----------

def create_ally(
    user_id: int,
    business_name: str,
    owner_name: str,
    address: str,
    city: str,
    barrio: str,
    phone: str,
) -> int:
    """Crea un aliado en la tabla allies y devuelve su id."""
    conn = get_connection()
    cur = conn.cursor()

    # DEBUG: ver qué datos se están guardando
    print("[DEBUG] create_ally() datos recibidos:")
    print(f"  user_id={user_id}")
    print(f"  business_name={business_name!r}")
    print(f"  owner_name={owner_name!r}")
    print(f"  address={address!r}")
    print(f"  city={city!r}")
    print(f"  barrio={barrio!r}")
    print(f"  phone={phone!r}")

    cur.execute(
        """
        INSERT INTO allies (
            user_id,
            business_name,
            owner_name,
            address,
            city,
            barrio,
            phone
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (user_id, business_name, owner_name, address, city, barrio, phone),
    )

    ally_id = cur.lastrowid
    conn.commit()
    conn.close()
    return ally_id

def get_ally_by_user_id(user_id: int):
    """Devuelve el aliado más reciente asociado a un user_id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM allies WHERE user_id = ? ORDER BY id DESC LIMIT 1;",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row
    
def get_ally_by_id(ally_id: int):
    """Devuelve un aliado por su ID (o None si no existe)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM allies WHERE id = ? LIMIT 1;",
        (ally_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row

def get_pending_allies():
    """Devuelve todos los aliados con estado PENDING."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,
            business_name,
            owner_name,
            address,
            city,
            barrio,
            phone,
            status
        FROM allies
        WHERE status = 'PENDING'
        ORDER BY created_at ASC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def update_ally_status(ally_id: int, status: str):
    """Actualiza el estado de un aliado (PENDING, APPROVED, REJECTED)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE allies
        SET status = ?
        WHERE id = ?;
        """,
        (status, ally_id),
    )
    conn.commit()
    conn.close()

# ---------- DIRECCIONES DE ALIADOS (ally_locations) ----------

def create_ally_location(
    ally_id: int,
    label: str,
    address: str,
    city: str,
    barrio: str,
    phone: str = None,
    is_default: bool = False,
):
    """Crea una dirección de recogida para un aliado."""
    conn = get_connection()
    cur = conn.cursor()

    if is_default:
        # Si esta será la principal, poner las demás en 0
        cur.execute(
            "UPDATE ally_locations SET is_default = 0 WHERE ally_id = ?;",
            (ally_id,),
        )

    cur.execute("""
        INSERT INTO ally_locations (
            ally_id, label, address, city, barrio, phone, is_default
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (ally_id, label, address, city, barrio, phone, 1 if is_default else 0))

    conn.commit()
    location_id = cur.lastrowid
    conn.close()
    return location_id


def get_ally_locations(ally_id: int):
    """Devuelve todas las direcciones de un aliado, principal primero."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, ally_id, label, address, city, barrio, phone, is_default, created_at
        FROM ally_locations
        WHERE ally_id = ?
        ORDER BY is_default DESC, id ASC;
    """, (ally_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_default_ally_location(ally_id: int):
    """Devuelve la dirección principal de un aliado (o None)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, ally_id, label, address, city, barrio, phone, is_default, created_at
        FROM ally_locations
        WHERE ally_id = ? AND is_default = 1
        ORDER BY id ASC
        LIMIT 1;
    """, (ally_id,))
    row = cur.fetchone()
    conn.close()
    return row


def set_default_ally_location(location_id: int, ally_id: int):
    """Marca una dirección como principal para ese aliado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE ally_locations SET is_default = 0 WHERE ally_id = ?;",
        (ally_id,),
    )
    cur.execute(
        "UPDATE ally_locations SET is_default = 1 WHERE id = ? AND ally_id = ?;",
        (location_id, ally_id),
    )
    conn.commit()
    conn.close()


def update_ally_location(location_id: int, address: str, city: str, barrio: str, phone: str = None):
    """Actualiza los datos de una dirección."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE ally_locations
        SET address = ?, city = ?, barrio = ?, phone = ?
        WHERE id = ?;
    """, (address, city, barrio, phone, location_id))
    conn.commit()
    conn.close()


def delete_ally_location(location_id: int, ally_id: int):
    """Elimina una dirección de un aliado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM ally_locations WHERE id = ? AND ally_id = ?;",
        (location_id, ally_id),
    )
    conn.commit()
    conn.close()


# ---------- PEDIDOS (orders) ----------

def create_order(
    ally_id: int,
    customer_name: str,
    customer_phone: str,
    customer_address: str,
    customer_city: str,
    customer_barrio: str,
    pickup_location_id: int,
    pay_at_store_required: bool,
    pay_at_store_amount: int,
    base_fee: int,
    distance_km: float,
    rain_extra: int,
    high_demand_extra: int,
    night_extra: int,
    additional_incentive: int,
    total_fee: int,
    instructions: str,
):
    """Crea un pedido en estado CREATED y devuelve su id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (
            ally_id,
            courier_id,
            status,
            customer_name,
            customer_phone,
            customer_address,
            customer_city,
            customer_barrio,
            pickup_location_id,
            pay_at_store_required,
            pay_at_store_amount,
            base_fee,
            distance_km,
            rain_extra,
            high_demand_extra,
            night_extra,
            additional_incentive,
            total_fee,
            instructions
        ) VALUES (?, NULL, 'CREATED', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        ally_id,
        customer_name,
        customer_phone,
        customer_address,
        customer_city,
        customer_barrio,
        pickup_location_id,
        1 if pay_at_store_required else 0,
        pay_at_store_amount,
        base_fee,
        distance_km,
        rain_extra,
        high_demand_extra,
        night_extra,
        additional_incentive,
        total_fee,
        instructions,
    ))
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    return order_id


def set_order_status(order_id: int, status: str, timestamp_field: str = None):
    """
    Actualiza el estado de un pedido.
    Si timestamp_field no es None, también actualiza ese campo de tiempo con datetime('now').
    Ejemplos de timestamp_field: 'published_at', 'accepted_at', 'pickup_confirmed_at', 'delivered_at', 'canceled_at'
    """
    conn = get_connection()
    cur = conn.cursor()

    if timestamp_field:
        query = f"UPDATE orders SET status = ?, {timestamp_field} = datetime('now') WHERE id = ?;"
        cur.execute(query, (status, order_id))
    else:
        cur.execute("UPDATE orders SET status = ? WHERE id = ?;", (status, order_id))

    conn.commit()
    conn.close()


def assign_order_to_courier(order_id: int, courier_id: int):
    """Asigna un pedido a un repartidor y marca accepted_at."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE orders
        SET courier_id = ?, status = 'ACCEPTED', accepted_at = datetime('now')
        WHERE id = ?;
    """, (courier_id, order_id))
    conn.commit()
    conn.close()


def get_order_by_id(order_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM orders
        WHERE id = ?;
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_orders_by_ally(ally_id: int, limit: int = 50):
    """Devuelve los últimos pedidos de un aliado (para historial)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM orders
        WHERE ally_id = ?
        ORDER BY id DESC
        LIMIT ?;
    """, (ally_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_orders_by_courier(courier_id: int, limit: int = 50):
    """Devuelve los últimos pedidos de un repartidor."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM orders
        WHERE courier_id = ?
        ORDER BY id DESC
        LIMIT ?;
    """, (courier_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- CALIFICACIONES DEL REPARTIDOR ----------

def add_courier_rating(order_id: int, courier_id: int, rating: int, comment: str = None):
    """Registra una calificación para un repartidor."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO courier_ratings (order_id, courier_id, rating, comment)
        VALUES (?, ?, ?, ?);
    """, (order_id, courier_id, rating, comment))
    conn.commit()
    conn.close()


# ---------- REPARTIDORES ----------

def create_courier(
    user_id: int,
    full_name: str,
    id_number: str,
    phone: str,
    city: str,
    barrio: str,
    plate: str,
    bike_type: str,
    code: str,
):
    """Crea un repartidor en estado PENDING y devuelve su id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO couriers (
            user_id,
            full_name,
            id_number,
            phone,
            city,
            barrio,
            plate,
            bike_type,
            code,
            status,
            balance
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0);
    """, (
        user_id,
        full_name,
        id_number,
        phone,
        city,
        barrio,
        plate,
        bike_type,
        code,
    ))
    conn.commit()
    courier_id = cur.lastrowid
    conn.close()
    return courier_id


def get_courier_by_user_id(user_id: int):
    """Devuelve el repartidor más reciente asociado a un user_id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM couriers WHERE user_id = ? ORDER BY id DESC LIMIT 1;",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row
