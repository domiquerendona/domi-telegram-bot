import sqlite3
import os
import re

# Ruta del archivo de base de datos
DB_PATH = os.getenv("DB_PATH", "domiquerendona.db")

# ----------------- Normalización -----------------

def normalize_phone(phone: str) -> str:
    """
    Normaliza teléfono a un formato consistente.
    Recomendación: guardar en E.164 (+57XXXXXXXXXX) si tu flujo ya lo pide así.
    Si no, al menos limpia espacios y símbolos.
    """
    if phone is None:
        return ""
    phone = phone.strip()
    # Elimina espacios, guiones, paréntesis
    phone = re.sub(r"[^\d+]", "", phone)

    # Si viene sin + y es Colombia (10 dígitos), lo convertimos a +57...
    # Ajusta esta regla si tu flujo ya captura +57 siempre.
    if phone and not phone.startswith("+"):
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            phone = "+57" + digits
        else:
            phone = digits  # fallback

    return phone


def normalize_document(doc: str) -> str:
    """Normaliza documento: quita espacios/puntos, deja alfanumérico en mayúsculas."""
    if doc is None:
        return ""
    doc = doc.strip().upper()
    doc = re.sub(r"[^A-Z0-9]", "", doc)
    return doc


# ----------------- Identidad global -----------------

def get_or_create_identity(phone: str, document_number: str, full_name: str = None) -> int:
    """
    Devuelve identity_id (tabla identities) aplicando unicidad global:
    - phone único
    - document_number único
    Si existe conflicto (mismo teléfono con otra cédula, o viceversa) levanta ValueError.
    """
    phone_n = normalize_phone(phone)
    doc_n = normalize_document(document_number) if document_number else ""

    if not phone_n:
        raise ValueError("Teléfono es obligatorio.")

    # Si no hay document_number, usar placeholder único basado en teléfono
    if not doc_n:
        doc_n = f"SIN_DOC_{phone_n}"

    conn = get_connection()
    cur = conn.cursor()

    # Buscar por teléfono o por documento
    cur.execute("""
        SELECT id, phone, document_number
        FROM identities
        WHERE phone = ? OR document_number = ?
        LIMIT 1
    """, (phone_n, doc_n))
    row = cur.fetchone()

    if row:
        identity_id, existing_phone, existing_doc = row

        # Conflicto: teléfono ya existe con otra cédula
        if existing_phone == phone_n and existing_doc != doc_n:
            conn.close()
            raise ValueError("Este teléfono ya está registrado con otra cédula.")

        # Conflicto: cédula ya existe con otro teléfono
        if existing_doc == doc_n and existing_phone != phone_n:
            conn.close()
            raise ValueError("Esta cédula ya está registrada con otro teléfono.")

        # Todo coincide: retornamos la identidad existente
        conn.close()
        return identity_id

    # No existe: crear
    try:
        cur.execute("""
            INSERT INTO identities (phone, document_number, full_name)
            VALUES (?, ?, ?)
        """, (phone_n, doc_n, (full_name or "").strip() if full_name else None))
        identity_id = cur.lastrowid
        conn.commit()
        conn.close()
        return identity_id

    except sqlite3.IntegrityError:
        # Si entra aquí, alguien insertó entre la consulta y el insert.
        # Re-consultar y validar.
        cur.execute("""
            SELECT id, phone, document_number
            FROM identities
            WHERE phone = ? OR document_number = ?
            LIMIT 1
        """, (phone_n, doc_n))
        row2 = cur.fetchone()
        conn.close()
        if not row2:
            raise ValueError("No se pudo crear identidad. Intenta de nuevo.")
        identity_id, existing_phone, existing_doc = row2
        if existing_phone == phone_n and existing_doc != doc_n:
            raise ValueError("Este teléfono ya está registrado con otra cédula.")
        if existing_doc == doc_n and existing_phone != phone_n:
            raise ValueError("Esta cédula ya está registrada con otro teléfono.")
        return identity_id


def ensure_user_person_id(user_id: int, person_id: int) -> None:
    """Amarra users.person_id si está vacío. No sobreescribe si ya existe."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT person_id FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if row and (row[0] is None or row[0] == ""):
        cur.execute("UPDATE users SET person_id = ? WHERE id = ?", (person_id, user_id))
        conn.commit()
    conn.close()


def add_user_role(user_id: int, role: str) -> None:
    """Inserta rol múltiple (user_roles). No falla si ya existe."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT OR IGNORE INTO user_roles (user_id, role)
            VALUES (?, ?)
        """, (user_id, role))
        conn.commit()
    finally:
        conn.close()

def get_connection():
    """Devuelve una conexión a la base de datos SQLite."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # ============================================================
    # A) TABLAS BASE (crear primero)
    # ============================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            role TEXT,
            created_at TEXT DEFAULT (datetime('now'))
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
            created_at TEXT DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0,
            deleted_at TEXT
        );
    """)

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

    # ============================================================
    # B) TABLAS AUXILIARES (crear antes de usarlas)
    # ============================================================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS identities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            document_number TEXT NOT NULL,
            full_name TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, role),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # ============================================================
    # C) MIGRACIONES DE COLUMNAS (antes de UPDATE/INSERT que las usan)
    # ============================================================

    # users.person_id
    cur.execute("PRAGMA table_info(users)")
    users_cols = [r[1] for r in cur.fetchall()]
    if "person_id" not in users_cols:
        cur.execute("ALTER TABLE users ADD COLUMN person_id INTEGER")

    # allies.document_number
    cur.execute("PRAGMA table_info(allies)")
    allies_cols = [r[1] for r in cur.fetchall()]
    if "document_number" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN document_number TEXT")

    # admins: team_name, document_number, team_code, person_id
    cur.execute("PRAGMA table_info(admins)")
    admins_cols = [r[1] for r in cur.fetchall()]
    if "team_name" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN team_name TEXT")
    if "document_number" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN document_number TEXT")
    if "team_code" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN team_code TEXT")
    if "person_id" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN person_id INTEGER")

    # couriers.person_id + soft delete + free_orders_remaining
    cur.execute("PRAGMA table_info(couriers)")
    couriers_cols = [r[1] for r in cur.fetchall()]
    if "person_id" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN person_id INTEGER")
    if "is_deleted" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0")
    if "deleted_at" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN deleted_at TEXT")
    if "free_orders_remaining" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN free_orders_remaining INTEGER DEFAULT 15")

    # allies.soft delete + person_id
    cur.execute("PRAGMA table_info(allies)")
    allies_cols = [r[1] for r in cur.fetchall()]
    if "person_id" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN person_id INTEGER")
    if "is_deleted" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0")
    if "deleted_at" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN deleted_at TEXT")

    # ============================================================
    # D) ÍNDICES (después de asegurar columnas)
    # ============================================================

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_identities_phone ON identities(phone)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_identities_document ON identities(document_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_users_person_id ON users(person_id)")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_admins_person_id ON admins(person_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_couriers_person_id ON couriers(person_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_allies_person_id ON allies(person_id)")

    # team_code único
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_team_code_unique ON admins(team_code)")

    # Completar team_name y team_code si están vacíos
    cur.execute("""
        UPDATE admins
        SET team_name = COALESCE(team_name, full_name)
        WHERE team_name IS NULL OR team_name = ''
    """)
    cur.execute("""
        UPDATE admins
        SET team_code = 'TEAM' || id
        WHERE team_code IS NULL OR team_code = ''
    """)

    # Asegurar free_orders_remaining no NULL
    cur.execute("""
        UPDATE couriers
        SET free_orders_remaining = 15
        WHERE free_orders_remaining IS NULL
    """)

    # ============================================================
    # E) MIGRACIÓN DE DATOS -> identities y person_id (al final)
    # ============================================================

    cur.execute("""
        INSERT OR IGNORE INTO identities(phone, document_number, full_name)
        SELECT a.phone, a.document_number, a.full_name
        FROM admins a
        WHERE a.phone IS NOT NULL AND a.phone <> ''
          AND a.document_number IS NOT NULL AND a.document_number <> '';
    """)

    cur.execute("""
        INSERT OR IGNORE INTO identities(phone, document_number, full_name)
        SELECT c.phone, c.id_number, c.full_name
        FROM couriers c
        WHERE c.phone IS NOT NULL AND c.phone <> ''
          AND c.id_number IS NOT NULL AND c.id_number <> '';
    """)

    cur.execute("""
        INSERT OR IGNORE INTO identities(phone, document_number, full_name)
        SELECT al.phone, al.document_number, al.owner_name
        FROM allies al
        WHERE al.phone IS NOT NULL AND al.phone <> ''
          AND al.document_number IS NOT NULL AND al.document_number <> '';
    """)

    # admins.person_id
    cur.execute("""
        UPDATE admins
        SET person_id = (
            SELECT i.id FROM identities i
            WHERE i.phone = admins.phone
              AND i.document_number = admins.document_number
        )
        WHERE person_id IS NULL
          AND phone IS NOT NULL AND phone <> ''
          AND document_number IS NOT NULL AND document_number <> '';
    """)

    # couriers.person_id
    cur.execute("""
        UPDATE couriers
        SET person_id = (
            SELECT i.id FROM identities i
            WHERE i.phone = couriers.phone
              AND i.document_number = couriers.id_number
        )
        WHERE person_id IS NULL
          AND phone IS NOT NULL AND phone <> ''
          AND id_number IS NOT NULL AND id_number <> '';
    """)

    # allies.person_id
    cur.execute("""
        UPDATE allies
        SET person_id = (
            SELECT i.id FROM identities i
            WHERE i.phone = allies.phone
              AND i.document_number = allies.document_number
        )
        WHERE person_id IS NULL
          AND phone IS NOT NULL AND phone <> ''
          AND document_number IS NOT NULL AND document_number <> '';
    """)

    # users.person_id (prioridad admins -> couriers -> allies)
    cur.execute("""
        UPDATE users
        SET person_id = (SELECT a.person_id FROM admins a WHERE a.user_id = users.id)
        WHERE person_id IS NULL
          AND EXISTS (SELECT 1 FROM admins a WHERE a.user_id = users.id AND a.person_id IS NOT NULL);
    """)
    cur.execute("""
        UPDATE users
        SET person_id = (SELECT c.person_id FROM couriers c WHERE c.user_id = users.id)
        WHERE person_id IS NULL
          AND EXISTS (SELECT 1 FROM couriers c WHERE c.user_id = users.id AND c.person_id IS NOT NULL);
    """)
    cur.execute("""
        UPDATE users
        SET person_id = (SELECT al.person_id FROM allies al WHERE al.user_id = users.id)
        WHERE person_id IS NULL
          AND EXISTS (SELECT 1 FROM allies al WHERE al.user_id = users.id AND al.person_id IS NOT NULL);
    """)

    # ============================================================
    # F) TABLAS FALTANTES (orders, settings, locations, ratings, terms)
    # ============================================================

    # Tabla: settings (configuración global)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    # Tabla: ally_locations (direcciones de recogida)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ally_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            barrio TEXT NOT NULL,
            phone TEXT,
            is_default INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ally_id) REFERENCES allies(id)
        );
    """)

    # Tabla: admin_allies (relación admin-aliado)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_allies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            ally_id INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING',
            balance INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(admin_id, ally_id),
            FOREIGN KEY (admin_id) REFERENCES admins(id),
            FOREIGN KEY (ally_id) REFERENCES allies(id)
        );
    """)

    # Tabla: admin_couriers (relación admin-repartidor)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            courier_id INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING',
            balance INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(admin_id, courier_id),
            FOREIGN KEY (admin_id) REFERENCES admins(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id)
        );
    """)

    # Tabla: orders (pedidos)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            courier_id INTEGER,
            status TEXT DEFAULT 'PENDING',
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            customer_city TEXT NOT NULL,
            customer_barrio TEXT NOT NULL,
            pickup_location_id INTEGER,
            pay_at_store_required INTEGER DEFAULT 0,
            pay_at_store_amount INTEGER DEFAULT 0,
            base_fee INTEGER DEFAULT 0,
            distance_km REAL DEFAULT 0,
            rain_extra INTEGER DEFAULT 0,
            high_demand_extra INTEGER DEFAULT 0,
            night_extra INTEGER DEFAULT 0,
            additional_incentive INTEGER DEFAULT 0,
            total_fee INTEGER DEFAULT 0,
            instructions TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            published_at TEXT,
            accepted_at TEXT,
            pickup_confirmed_at TEXT,
            delivered_at TEXT,
            canceled_at TEXT,
            FOREIGN KEY (ally_id) REFERENCES allies(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id),
            FOREIGN KEY (pickup_location_id) REFERENCES ally_locations(id)
        );
    """)

    # Tabla: courier_ratings (calificaciones)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS courier_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            courier_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id)
        );
    """)

    # Tabla: terms_versions (versiones de términos)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS terms_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            version TEXT NOT NULL,
            url TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            status TEXT DEFAULT 'APPROVED',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(role, version)
        );
    """)

    # Tabla: terms_acceptances (aceptaciones de términos)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS terms_acceptances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            version TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            message_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(telegram_id, role, version, sha256)
        );
    """)

    # Tabla: terms_session_acks (confirmaciones de sesión)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS terms_session_acks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            version TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    conn.commit()
    conn.close()

def force_platform_admin(platform_telegram_id: int):
    conn = get_connection()
    cur = conn.cursor()

    # 1) asegurar users
    cur.execute("SELECT id FROM users WHERE telegram_id = ? LIMIT 1", (platform_telegram_id,))
    row = cur.fetchone()

    if row:
        user_id = row[0] if not isinstance(row, sqlite3.Row) else row["id"]
    else:
        cur.execute(
            "INSERT INTO users (telegram_id, username, role, created_at) VALUES (?, ?, ?, datetime('now'))",
            (platform_telegram_id, "platform", "ADMIN_PLATFORM"),
        )
        user_id = cur.lastrowid

    # 2) asegurar admins
    cur.execute("""
        SELECT id FROM admins
        WHERE team_code = 'PLATFORM' AND is_deleted = 0
        LIMIT 1
    """)
    admin_row = cur.fetchone()

    if admin_row:
        admin_id = admin_row[0] if not isinstance(admin_row, sqlite3.Row) else admin_row["id"]
        cur.execute("""
            UPDATE admins
            SET team_code='PLATFORM', status='APPROVED'
            WHERE id = ?
        """, (admin_id,))
    else:
        cur.execute("""
            INSERT INTO admins (
                user_id, full_name, phone, city, barrio,
                status, created_at, team_name, document_number, team_code
            )
            VALUES (
                ?, ?, ?, ?, ?,
                'APPROVED', datetime('now'), ?, ?, 'PLATFORM'
            )
        """, (
            user_id,
            "Administrador de Plataforma",
            "+570000000000",
            "PLATAFORMA",
            "PLATAFORMA",
            "PLATAFORMA",  # team_name
            "PLATFORM",    # document_number (si no tienes cédula real, usa algo fijo)
        ))

    conn.commit()
    conn.close()


# ---------- USUARIOS ----------

def get_user_id_from_telegram_id(telegram_id: int) -> int:
    """Devuelve users.id (interno) a partir de telegram_id. Crea user si no existe."""
    user = ensure_user(telegram_id)
    return user["id"] if isinstance(user, dict) else user[0]


def get_admin_by_telegram_id(telegram_id: int):
    """
    Devuelve el admin (último) asociado a esta cuenta de Telegram.
    Internamente convierte telegram_id -> users.id.
    """
    user_id = get_user_id_from_telegram_id(telegram_id)
    if not user_id:
        return None
    return get_admin_by_user_id(user_id)


def get_admin_by_user_id(user_id: int):
    """
    user_id = users.id (interno).
    Devuelve el admin más reciente asociado a esa cuenta.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id, user_id, person_id, full_name, phone, city, barrio,
            status, created_at, team_name, document_number, team_code
        FROM admins
        WHERE user_id = ? AND is_deleted = 0
        ORDER BY id DESC
        LIMIT 1;
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return None
        
    return dict(row)


def get_admin_by_id(admin_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id,                 -- 0
            user_id,            -- 1
            full_name,          -- 2
            phone,              -- 3
            city,               -- 4
            barrio,             -- 5
            team_name,          -- 6
            document_number,    -- 7
            team_code,          -- 8
            status,             -- 9
            created_at          -- 10
        FROM admins
        WHERE id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (admin_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_admin_by_team_code(team_code: str):
    """
    Busca un Admin Local por su team_code (ej: TEAM1) y devuelve datos + telegram_id real.

    Retorna:
      (admin_id, admin_user_db_id, full_name, status, team_name, team_code, telegram_id)
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
        ORDER BY a.id DESC
        LIMIT 1;
    """, (team_code,))

    row = cur.fetchone()
    conn.close()
    return row


def get_courier_by_telegram_id(telegram_id: int):
    user_id = get_user_id_from_telegram_id(telegram_id)
    return get_courier_by_user_id(user_id)


def get_ally_by_telegram_id(telegram_id: int):
    user_id = get_user_id_from_telegram_id(telegram_id)
    return get_ally_by_user_id(user_id)


def get_user_by_telegram_id(telegram_id: int):
    """Devuelve el usuario según su telegram_id o None si no existe."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE telegram_id = ?;", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, telegram_id, username, created_at FROM users WHERE id = ?",
        (user_id,)
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    if isinstance(row, dict):
        return row

    return {
        "id": row[0],
        "telegram_id": row[1],
        "username": row[2],
        "created_at": row[3],
    }


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
def get_setting(key: str, default=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ? LIMIT 1", (key,))
    row = cur.fetchone()
    conn.close()
    return row["value"] if row else default


def get_platform_admin_id() -> int:
    """
    Retorna admins.id del Administrador de Plataforma.
    REQUISITO: guardar en settings la clave 'platform_admin_id' con el admins.id.
    """
    val = get_setting("platform_admin_id")
    if val:
        try:
            return int(val)
        except Exception:
            pass

    # Fallback seguro (para que no reviente): usa el admin id más pequeño APPROVED
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id
        FROM admins
        WHERE is_deleted = 0
          AND status = 'APPROVED'
        ORDER BY id ASC
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()
    return int(row["id"]) if row else 1
    

def get_available_admin_teams():
    """
    Devuelve lista de equipos disponibles para que un aliado elija.
    Solo admins aprobados y no borrados.
    Retorna filas con: (admin_id, team_name, team_code)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            a.id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code
        FROM admins a
        WHERE a.status = 'APPROVED'
          AND a.is_deleted = 0
          AND a.team_code IS NOT NULL
          AND TRIM(a.team_code) <> ''
        ORDER BY a.id ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def upsert_admin_ally_link(admin_id: int, ally_id: int, status: str = "PENDING", is_active: int = 0):
    """
    Crea o actualiza el vínculo admin_allies para este aliado con este admin.
    Por defecto queda PENDING hasta aprobación, y is_active=0.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Inserta si no existe
    cur.execute("""
        INSERT OR IGNORE INTO admin_allies (admin_id, ally_id, status, is_active, balance, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, datetime('now'), datetime('now'))
    """, (admin_id, ally_id, status, is_active))

    # Si ya existía, actualiza status/is_active y updated_at
    cur.execute("""
        UPDATE admin_allies
        SET status = ?,
            is_active = ?,
            updated_at = datetime('now')
        WHERE admin_id = ? AND ally_id = ?
    """, (status, is_active, admin_id, ally_id))

    conn.commit()
    conn.close()


def upsert_admin_courier_link(admin_id: int, courier_id: int, status: str = "PENDING", is_active: int = 1):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO admin_couriers (admin_id, courier_id, status, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(admin_id, courier_id)
        DO UPDATE SET
            status=excluded.status,
            is_active=excluded.is_active,
            updated_at=datetime('now')
    """, (admin_id, courier_id, status, is_active))
    conn.commit()
    conn.close()


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
    document_number: str = "",
) -> int:
    """Crea un aliado en la tabla allies y devuelve su id."""

    # 1) Identidad global (usamos teléfono + cédula del propietario/representante)
    person_id = get_or_create_identity(phone, document_number, full_name=owner_name)
    ensure_user_person_id(user_id, person_id)

    conn = get_connection()
    cur = conn.cursor()

    # DEBUG opcional (puedes dejarlo)
    print("[DEBUG] create_ally() datos recibidos:")
    print(f"  user_id={user_id}")
    print(f"  business_name={business_name!r}")
    print(f"  owner_name={owner_name!r}")
    print(f"  address={address!r}")
    print(f"  city={city!r}")
    print(f"  barrio={barrio!r}")
    print(f"  phone={phone!r}")
    print(f"  document_number={document_number!r}")

    try:
        cur.execute("""
            INSERT INTO allies (
                user_id,
                person_id,
                business_name,
                owner_name,
                address,
                city,
                barrio,
                phone,
                document_number
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            user_id,
            person_id,
            business_name,
            owner_name,
            address,
            city,
            barrio,
            normalize_phone(phone),
            normalize_document(document_number),
        ))

        ally_id = cur.lastrowid
        conn.commit()

    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError("Ya existe un registro de Aliado para esta cuenta o identidad.") from e
    finally:
        conn.close()

    add_user_role(user_id, "ALLY")

    return ally_id


def get_courier_by_user_id(user_id: int):
    """Devuelve el repartidor más reciente asociado a un user_id (no eliminado)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM couriers
        WHERE user_id = ? AND (is_deleted IS NULL OR is_deleted = 0)
        ORDER BY id DESC
        LIMIT 1;
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_ally_by_user_id(user_id: int):
    """Devuelve el aliado más reciente asociado a un user_id (no eliminado)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM allies
        WHERE user_id = ? AND (is_deleted IS NULL OR is_deleted = 0)
        ORDER BY id DESC
        LIMIT 1;
    """, (user_id,))
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
    

def get_all_admins():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            id, user_id, full_name, phone, city, barrio,
            status, created_at, team_name, document_number
        FROM admins
        WHERE is_deleted = 0
        ORDER BY id DESC;
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def update_admin_status_by_id(admin_id: int, new_status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE admins
        SET status = ?
        WHERE id = ? AND is_deleted = 0;
    """, (new_status, admin_id))
    conn.commit()
    conn.close()

def update_courier_status_by_id(courier_id: int, new_status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE couriers
        SET status = ?
        WHERE id = ? AND (is_deleted IS NULL OR is_deleted = 0);
    """, (new_status, courier_id))
    conn.commit()
    conn.close()

def update_ally_status_by_id(ally_id: int, new_status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE allies
        SET status = ?
        WHERE id = ? AND (is_deleted IS NULL OR is_deleted = 0);
    """, (new_status, ally_id))
    conn.commit()
    conn.close()
    

def get_local_admins_count():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM admins
        WHERE is_deleted = 0
          AND team_code IS NOT NULL
          AND TRIM(team_code) <> ''
    """)

    count = cur.fetchone()[0]
    conn.close()
    return count
    

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

    # 1) Identidad global (usa cédula del courier)
    person_id = get_or_create_identity(phone, id_number, full_name=full_name)
    ensure_user_person_id(user_id, person_id)

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO couriers (
                user_id,
                person_id,
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0);
        """, (
            user_id,
            person_id,
            full_name,
            normalize_document(id_number),
            normalize_phone(phone),
            city,
            barrio,
            plate,
            bike_type,
            code,
        ))
        conn.commit()
        courier_id = cur.lastrowid

    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError("Ya existe un registro de Repartidor para esta cuenta o identidad.") from e
    finally:
        conn.close()

    add_user_role(user_id, "COURIER")

    return courier_id


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


def delete_courier(courier_id: int) -> None:
    """Desactiva (soft delete) un repartidor sin borrar datos."""
    conn = get_connection()
    cur = conn.cursor()

    # Desactivar perfil
    cur.execute("""
        UPDATE couriers
        SET status = 'INACTIVE',
            is_deleted = 1,
            deleted_at = datetime('now')
        WHERE id = ?
    """, (courier_id,))

    # Desactivar vínculos con admins (no borrar, solo inactivar)
    cur.execute("""
        UPDATE admin_couriers
        SET status = 'INACTIVE',
            is_active = 0,
            updated_at = datetime('now')
        WHERE courier_id = ?
    """, (courier_id,))

    conn.commit()
    conn.close()


def delete_ally(ally_id: int) -> None:
    """Desactiva (soft delete) un aliado sin borrar datos."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE allies
        SET status = 'INACTIVE',
            is_deleted = 1,
            created_at = created_at, -- no cambia, solo explícito
            deleted_at = datetime('now')
        WHERE id = ?
    """, (ally_id,))

    # Desactivar vínculos con admins
    cur.execute("""
        UPDATE admin_allies
        SET status = 'INACTIVE',
            is_active = 0,
            updated_at = datetime('now')
        WHERE ally_id = ?
    """, (ally_id,))

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
    # 1) Identidad global
    person_id = get_or_create_identity(phone, document_number, full_name=full_name)
    ensure_user_person_id(user_id, person_id)

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO admins (
                user_id, person_id, full_name, phone, city, barrio,
                status, created_at, team_name, document_number
            )
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING', datetime('now'), ?, ?)
        """, (user_id, person_id, full_name, normalize_phone(phone), city, barrio, team_name, normalize_document(document_number)))

        admin_id = cur.lastrowid

        # TEAM_CODE automático y único
        team_code = f"TEAM{admin_id}"
        cur.execute("UPDATE admins SET team_code = ? WHERE id = ?", (team_code, admin_id))

        conn.commit()

    except sqlite3.IntegrityError as e:
        # Si ya existe admin para esa identidad o ese user_id, informamos de forma controlada
        conn.rollback()
        raise ValueError("Ya existe un registro de Administrador Local para esta cuenta o identidad.") from e
    finally:
        conn.close()

    # Rol múltiple
    add_user_role(user_id, "ADMIN_LOCAL")

    return admin_id, team_code


def get_pending_admins():
    conn = conn = get_connection()
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
    conn = conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE admins
        SET status=?
        WHERE user_id=? AND is_deleted=0
    """, (new_status, user_id))
    conn.commit()
    conn.close()


def soft_delete_admin_by_id(admin_id: int):
    conn = conn = get_connection()
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
    conn = conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM admins WHERE is_deleted=0")
    n = cur.fetchone()[0]
    conn.close()
    return n
    
# =========================
# ADMINISTRADORES (POR admin_id) - Panel/Config
# =========================

def get_admin_status_by_id(admin_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status FROM admins WHERE id=? AND is_deleted=0", (admin_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    # row puede ser sqlite3.Row; si ya usas dict(row), ajusta:
    return row["status"] if hasattr(row, "keys") else row[0]


def count_admin_couriers(admin_id: int):
    conn = conn = get_connection()
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
    conn = conn = get_connection()
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

def get_available_admins(limit=10, offset=0):
    """
    Lista admins locales disponibles para que un repartidor elija.
    Retorna: [(admin_id, team_name, team_code, city), ...]
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            COALESCE(team_name, full_name) AS team_name,
            team_code,
            city
        FROM admins
        WHERE status = 'APPROVED'
          AND is_deleted = 0
          AND team_code IS NOT NULL
          AND TRIM(team_code) != ''
        ORDER BY id ASC
        LIMIT ? OFFSET ?
    """, (limit, offset))

    rows = cur.fetchall()
    conn.close()
    return rows 









