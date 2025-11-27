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
            bike_type TEXT,
            code TEXT UNIQUE,
            status TEXT DEFAULT 'PENDING',   -- PENDING / APPROVED / BLOCKED
            balance INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    conn.commit()
    conn.close()

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


# ---------- USUARIOS ----------

def get_user_by_telegram_id(telegram_id: int):
    """Devuelve el usuario según su telegram_id o None si no existe."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?;", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row

def get_setting(key: str, default: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?;", (key,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return default
    # row puede ser tupla o Row, usamos [0] para que sirva en ambos casos
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
    conn.close(

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

# ---------- ALIADOS ----------

def create_ally(user_id: int, business_name: str, owner_name: str,
                address: str, city: str, barrio: str):
    """Crea un aliado en estado PENDING y devuelve su id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO allies (user_id, business_name, owner_name, address, city, barrio, status)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING');
    """, (user_id, business_name, owner_name, address, city, barrio))
    conn.commit()
    ally_id = cur.lastrowid
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
    ) VALUES 
(?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0);
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
