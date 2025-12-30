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
            bike_type TEXT,
            code TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'PENDING',
            balance REAL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    
    # --- Ajustes de esquema (migraciones simples) ---
    # Agregar columna para pedidos gratis globales si no existe
    cur.execute("PRAGMA table_info(couriers)")
    couriers_cols = [row[1] for row in cur.fetchall()]
    if "free_orders_remaining" not in couriers_cols:
        cur.execute(
            "ALTER TABLE couriers ADD COLUMN free_orders_remaining INTEGER DEFAULT 15"
        )
    
    # (Recomendado) Asegurar que los existentes queden con 15 si estaban NULL
    cur.execute("""
        UPDATE couriers
        SET free_orders_remaining = 15
        WHERE free_orders_remaining IS NULL
    """)

    # --- Vínculo Repartidores por Administrador Local ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            courier_id INTEGER NOT NULL,

            status TEXT DEFAULT 'PENDING',          -- PENDING / APPROVED / REJECTED / BLOCKED
            is_active INTEGER DEFAULT 0,            -- 1 = equipo activo para este repartidor (opcional)
            balance REAL DEFAULT 0,                 -- saldo del repartidor con ESTE admin
            commission_pct REAL DEFAULT NULL,       -- si quieres comisión por vínculo (opcional)

            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT,

            UNIQUE(admin_id, courier_id),
            FOREIGN KEY (admin_id) REFERENCES admins(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id)
        );
    """)

    # --- Vínculo Aliados por Administrador Local ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_allies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            ally_id INTEGER NOT NULL,

            status TEXT DEFAULT 'PENDING',          -- PENDING / APPROVED / REJECTED / ACTIVE / INACTIVE / BLOCKED
            is_active INTEGER DEFAULT 0,            -- 1 = admin activo para este aliado (opcional)
            balance REAL DEFAULT 0,                 -- saldo del aliado con ESTE admin

            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT,

            UNIQUE(admin_id, ally_id),
            FOREIGN KEY (admin_id) REFERENCES admins(id),
            FOREIGN KEY (ally_id) REFERENCES allies(id)
        );
    """)

    # Índices recomendados
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_couriers_admin_id ON admin_couriers(admin_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_couriers_courier_id ON admin_couriers(courier_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_allies_admin_id ON admin_allies(admin_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_allies_ally_id ON admin_allies(ally_id)")

    # --- Migración para bases ya existentes ---
    # Asegurar columna bike_type
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN bike_type TEXT")
        print("[DB] Columna bike_type añadida a couriers.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            pass
        else:
            raise

    # Asegurar columna code
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN code TEXT")
        print("[DB] Columna code añadida a couriers.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            pass
        else:
            raise

    # Asegurar columna balance
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN balance REAL DEFAULT 0")
        print("[DB] Columna balance añadida a couriers.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            pass
        else:
            raise

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            barrio TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            deleted_at TEXT
    )
        """)

    # --- Migraciones para admins (team_name, document_number, team_code) ---
cur.execute("PRAGMA table_info(admins)")
admins_cols = [row[1] for row in cur.fetchall()]

# team_name
if "team_name" not in admins_cols:
    cur.execute("ALTER TABLE admins ADD COLUMN team_name TEXT")

# document_number
if "document_number" not in admins_cols:
    cur.execute("ALTER TABLE admins ADD COLUMN document_number TEXT")

# team_code (código público del equipo)
if "team_code" not in admins_cols:
    cur.execute("ALTER TABLE admins ADD COLUMN team_code TEXT")

# Completar team_name si está vacío
cur.execute("""
    UPDATE admins
    SET team_name = COALESCE(team_name, full_name)
    WHERE team_name IS NULL OR team_name = ''
""")

# Completar team_code si está vacío (formato estable)
cur.execute("""
    UPDATE admins
    SET team_code = 'TEAM' || id
    WHERE team_code IS NULL OR team_code = ''
""")

# Índice único para team_code (una sola vez)
try:
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_team_code_unique
        ON admins(team_code)
    """)
except Exception:
    pass


    # --- Términos y Condiciones / Contratos (versionado por rol) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS terms_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,                 -- USER / ALLY / COURIER / ADMIN_LOCAL / ADMIN_PLATFORM
            version TEXT NOT NULL,              -- ej: 2025-12-29-v1
            url TEXT NOT NULL,                  -- URL oficial en domiquerendona.com
            sha256 TEXT NOT NULL,               -- hash del texto exacto
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(role, version)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS terms_acceptances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,       -- Telegram user id
            role TEXT NOT NULL,
            version TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            accepted_at TEXT DEFAULT (datetime('now')),
            message_id INTEGER,
            UNIQUE(telegram_id, role, version, sha256)
        );
    """)

    # Opcional: auditoría "cada vez que se conecta"
    cur.execute("""
        CREATE TABLE IF NOT EXISTS terms_session_acks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            version TEXT NOT NULL,
            acked_at TEXT DEFAULT (datetime('now'))
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_terms_versions_role_active ON terms_versions(role, is_active)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_terms_acceptances_tid_role ON terms_acceptances(telegram_id, role)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_terms_session_acks_tid_role ON terms_session_acks(telegram_id, role)")

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
    
def get_all_allies():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,
            user_id,
            business_name,
            owner_name,
            phone,
            address,
            city,
            barrio,
            status
        FROM allies
        ORDER BY id ASC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_pending_couriers():
    """Devuelve todos los repartidores con estado PENDING."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            id,
            user_id,
            full_name,
            id_number,
            phone,
            city,
            barrio,
            plate,
            bike_type,
            code,
            status
        FROM couriers
        WHERE status = 'PENDING'
        ORDER BY id ASC;
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_couriers():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,
            user_id,
            full_name,
            id_number,
            phone,
            city,
            barrio,
            plate,
            bike_type,
            code,
            status
        FROM couriers
        ORDER BY id ASC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_pending_couriers_by_admin(admin_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.id AS courier_id,
            c.full_name,
            c.phone,
            c.city,
            c.barrio
        FROM admin_couriers ac
        JOIN couriers c ON c.id = ac.courier_id
        WHERE ac.admin_id = ?
          AND ac.status = 'PENDING'
          AND c.status != 'REJECTED'
        ORDER BY ac.created_at ASC
    """, (admin_id,))

    rows = cur.fetchall()
    conn.close()
    return rows

def get_couriers_by_admin_and_status(admin_id, status):
    """
    Lista repartidores de un admin por estado del vínculo (APPROVED, BLOCKED, REJECTED, etc.)
    Devuelve: (courier_id, full_name, phone, city, barrio, balance, link_status)
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            c.id AS courier_id,
            c.full_name,
            c.phone,
            c.city,
            c.barrio,
            ac.balance,
            ac.status
        FROM admin_couriers ac
        JOIN couriers c ON c.id = ac.courier_id
        WHERE ac.admin_id = ?
          AND ac.status = ?
        ORDER BY c.full_name ASC
    """, (admin_id, status))

    rows = cur.fetchall()
    conn.close()
    return rows

def admin_puede_operar(admin_id):
    """
    Verifica si un administrador local puede operar.
    Reglas:
    - Status = APPROVED
    - Mínimo 10 repartidores vinculados
    - Cada repartidor con balance >= 5000
    """
    conn = get_connection()
    cur = conn.cursor()

    # 1. Estado del admin
    cur.execute("""
        SELECT status
        FROM admins
        WHERE id = ? AND is_deleted = 0
    """, (admin_id,))
    row = cur.fetchone()

    if not row or row[0] != "APPROVED":
        conn.close()
        return False, "Tu cuenta aún no está aprobada por la plataforma."

    # 2. Total repartidores aprobados
    cur.execute("""
        SELECT COUNT(*)
        FROM admin_couriers
        WHERE admin_id = ?
          AND status = 'APPROVED'
    """, (admin_id,))
    total = cur.fetchone()[0]

    # 3. Repartidores con saldo suficiente
    cur.execute("""
        SELECT COUNT(*)
        FROM admin_couriers
        WHERE admin_id = ?
          AND status = 'APPROVED'
          AND balance >= 5000
    """, (admin_id,))
    con_saldo = cur.fetchone()[0]

    conn.close()

    if total < 10 or con_saldo < 10:
        return False, (
            "⚠️ Aún no puedes operar.\n\n"
            f"Requisitos:\n"
            f"- Repartidores aprobados: {total}/10\n"
            f"- Con saldo ≥ 5000: {con_saldo}/10\n\n"
            "Completa los requisitos para habilitar la operación."
        )

    return True, "OK"
    

def get_admin_by_team_code(team_code: str):
    """
    Busca un Admin Local por su team_code (ej: TEAM1) y devuelve datos + telegram_id real.

    Retorna tupla:
      (admin_id, admin_user_db_id, full_name, status, team_name, team_code, telegram_id)

    Notas:
    - admin_user_db_id = admins.user_id (FK a users.id)
    - telegram_id = users.telegram_id (chat_id real para enviar mensajes)
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            a.id,
            a.user_id,
            a.full_name,
            a.status,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code,
            u.telegram_id
        FROM admins a
        JOIN users u ON u.id = a.user_id
        WHERE UPPER(TRIM(a.team_code)) = UPPER(TRIM(?))
          AND a.is_deleted = 0
        LIMIT 1
    """, (team_code,))

    row = cur.fetchone()
    conn.close()
    return row


def create_admin_courier_link(admin_id: int, courier_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO admin_couriers (admin_id, courier_id, status, is_active, balance, created_at)
        VALUES (?, ?, 'PENDING', 0, 0, datetime('now'))
    """, (admin_id, courier_id))
    conn.commit()
    conn.close()
    

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
    
def get_courier_by_id(courier_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,
            user_id,
            full_name,
            id_number,
            phone,
            city,
            barrio,
            plate,
            bike_type,
            code,
            status
        FROM couriers
        WHERE id = ?;
    """, (courier_id,))
    row = cur.fetchone()
    conn.close()
    return row

def update_courier_status(courier_id: int, new_status: str):
    """Actualiza el estado de un repartidor (APPROVED / REJECTED)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE couriers SET status = ? WHERE id = ?;",
        (new_status, courier_id),
    )
    conn.commit()
    conn.close()

def get_totales_registros():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM allies;")
    total_allies = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM couriers;")
    total_couriers = cur.fetchone()[0]

    conn.close()
    return total_allies, total_couriers


def delete_ally(ally_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM allies WHERE id = ?;", (ally_id,))
    conn.commit()
    conn.close()


def delete_courier(courier_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM couriers WHERE id = ?;", (courier_id,))
    conn.commit()
    conn.close()


def update_ally(ally_id, business_name, owner_name, phone, address, city, barrio, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE allies
        SET business_name = ?, owner_name = ?, phone = ?, address = ?, city = ?, barrio = ?, status = ?
        WHERE id = ?
    """, (business_name, owner_name, phone, address, city, barrio, status, ally_id))
    conn.commit()
    conn.close()


def update_courier(courier_id, full_name, phone, bike_type, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE couriers
        SET full_name = ?, phone = ?, bike_type = ?, status = ?
        WHERE id = ?
    """, (full_name, phone, bike_type, status, courier_id))
    conn.commit()
    conn.close()

import sqlite3
from datetime import datetime

def create_admin(user_id, full_name, phone, city, barrio, team_name, document_number):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO admins (user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number)
        VALUES (?, ?, ?, ?, ?, 'PENDING', datetime('now'), ?, ?)
    """, (user_id, full_name, phone, city, barrio, team_name, document_number))

    admin_id = cur.lastrowid

    # TEAM_CODE automático y único
    team_code = f"TEAM{admin_id}"
    cur.execute("UPDATE admins SET team_code = ? WHERE id = ?", (team_code, admin_id))

    conn.commit()
    conn.close()

    return admin_id, team_code


def get_admin_by_user_id(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number
        FROM admins
        WHERE user_id=? AND is_deleted=0
    """, (user_id,))

    row = cur.fetchone()
    conn.close()
    return row


def get_pending_admins():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number
        FROM admins
        WHERE status='PENDING' AND is_deleted=0
        ORDER BY id ASC
    """)

    rows = cur.fetchall()
    conn.close()
    return rows


def update_admin_status(user_id: int, new_status: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE admins
        SET status=?
        WHERE user_id=? AND is_deleted=0
    """, (new_status, user_id))
    conn.commit()
    conn.close()


def soft_delete_admin_by_id(admin_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
        UPDATE admins
        SET is_deleted=1, deleted_at=?, status='INACTIVE'
        WHERE id=?
    """, (now, admin_id))
    conn.commit()
    conn.close()


def count_admins():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM admins WHERE is_deleted=0")
    n = cur.fetchone()[0]
    conn.close()
    return n
    
# =========================
# ADMINISTRADORES (POR admin_id) - Panel/Config
# =========================

def get_all_admins():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number
        FROM admins
        WHERE is_deleted=0
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_admin_by_id(admin_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, full_name, phone, city, barrio, status, created_at, team_name, document_number, team_code
        FROM admins
        WHERE id=? AND is_deleted=0
        LIMIT 1
    """, (admin_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_admin_status_by_id(admin_id: int, new_status: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE admins
        SET status=?
        WHERE id=? AND is_deleted=0
    """, (new_status, admin_id))
    conn.commit()
    conn.close()


def count_admin_couriers(admin_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM admin_couriers
        WHERE admin_id=?
    """, (admin_id,))
    n = cur.fetchone()[0]
    conn.close()
    return n


def count_admin_couriers_with_min_balance(admin_id: int, min_balance: int = 5000):
    """
    Regla: contar repartidores del admin con saldo >= min_balance
    usando admin_couriers.balance (saldo por vínculo).
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM admin_couriers
        WHERE admin_id=?
          AND balance >= ?
    """, (admin_id, min_balance))
    n = cur.fetchone()[0]
    conn.close()
    return n

def get_active_terms_version(role: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT version, url, sha256
        FROM terms_versions
        WHERE role = ? AND is_active = 1
        ORDER BY id DESC
        LIMIT 1
    """, (role,))
    row = cur.fetchone()
    conn.close()
    return row  # (version, url, sha256) o None

def has_accepted_terms(telegram_id: int, role: str, version: str, sha256: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 1
        FROM terms_acceptances
        WHERE telegram_id = ? AND role = ? AND version = ? AND sha256 = ?
        LIMIT 1
    """, (telegram_id, role, version, sha256))
    ok = cur.fetchone() is not None
    conn.close()
    return ok

def save_terms_acceptance(telegram_id: int, role: str, version: str, sha256: str, message_id: int = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO terms_acceptances (telegram_id, role, version, sha256, message_id)
        VALUES (?, ?, ?, ?, ?)
    """, (telegram_id, role, version, sha256, message_id))
    conn.commit()
    conn.close()

def save_terms_session_ack(telegram_id: int, role: str, version: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO terms_session_acks (telegram_id, role, version)
        VALUES (?, ?, ?)
    """, (telegram_id, role, version))
    conn.commit()
    conn.close()

def update_admin_courier_status(admin_id, courier_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE admin_couriers
        SET status = ?, updated_at = datetime('now')
        WHERE admin_id = ? AND courier_id = ?
    """, (status, admin_id, courier_id))
    conn.commit()
    conn.close()


def set_admin_team_code(admin_id: int, team_code: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE admins
        SET team_code = ?
        WHERE id = ?
    """, (team_code, admin_id))
    conn.commit()
    conn.close()






