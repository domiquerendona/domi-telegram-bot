import sqlite3
import os
import re
import json
import time

# Detectar motor de base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
DB_ENGINE = "postgres" if DATABASE_URL else "sqlite"

# Importar Postgres solo si aplica
if DB_ENGINE == "postgres":
    import psycopg2
    from psycopg2.extras import RealDictCursor

# Placeholder unificado: %s para Postgres, ? para SQLite
P = "%s" if DB_ENGINE == "postgres" else "?"

# IntegrityError compatible multi-motor
_IntegrityError = psycopg2.IntegrityError if DB_ENGINE == "postgres" else sqlite3.IntegrityError

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


# ----------------- Helpers multi-motor -----------------

def _insert_returning_id(cur, sql, params=()):
    """INSERT y devuelve el id generado. Usa RETURNING id en Postgres."""
    if DB_ENGINE == "postgres":
        sql_s = sql.rstrip().rstrip(';')
        cur.execute(sql_s + ' RETURNING id', params)
        return cur.fetchone()["id"]
    cur.execute(sql, params)
    return cur.lastrowid


def _row_value(row, key, index=0, default=None):
    """Lee un campo por clave (dict/Row) y fallback por índice."""
    if row is None:
        return default
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        return row[key]
    except Exception:
        try:
            return row[index]
        except Exception:
            return default


# ----------------- Identidad global -----------------

def get_or_create_identity(phone: str, document_number: str, full_name: str = None) -> int:
    """
    Devuelve identity_id (tabla identities) aplicando unicidad global:
    - phone único
    - document_number único
    Si existe conflicto (mismo teléfono con otra cédula, o viceversa) levanta ValueError.

    Soporta upgrade: si existe identity con placeholder SIN_DOC_{phone} y luego llega
    documento real, actualiza el placeholder en lugar de crear nueva identity.
    """
    phone_n = normalize_phone(phone)

    if not phone_n:
        raise ValueError("Teléfono es obligatorio.")

    doc_n = normalize_document(document_number) if document_number else ""
    placeholder = f"SIN_DOC_{phone_n}"

    conn = get_connection()
    cur = conn.cursor()

    # 1) Buscar si ya existe identidad con este teléfono
    cur.execute(f"""
        SELECT id, phone, document_number
        FROM identities
        WHERE phone = {P}
        LIMIT 1
    """, (phone_n,))
    row = cur.fetchone()

    if row:
        identity_id = row["id"]
        existing_phone = row["phone"]
        existing_doc = row["document_number"]

        # CASO A: Viene documento real y el actual es placeholder → UPGRADE
        if doc_n and existing_doc.startswith("SIN_DOC_"):
            # Verificar que el documento real no esté usado por otra identidad
            cur.execute(f"""
                SELECT id FROM identities
                WHERE document_number = {P} AND id != {P}
                LIMIT 1
            """, (doc_n, identity_id))
            conflict = cur.fetchone()
            if conflict:
                conn.close()
                raise ValueError("Esta cédula ya está registrada con otro teléfono.")

            # Actualizar placeholder a documento real
            try:
                cur.execute(f"""
                    UPDATE identities
                    SET document_number = {P}
                    WHERE id = {P}
                """, (doc_n, identity_id))
                conn.commit()
                conn.close()
                return identity_id
            except _IntegrityError as e:
                conn.rollback()
                conn.close()
                raise ValueError("Error al actualizar documento.") from e

        # CASO B: Viene documento real pero ya tiene otro documento (no placeholder) → ERROR
        elif doc_n and existing_doc != doc_n and not existing_doc.startswith("SIN_DOC_"):
            conn.close()
            raise ValueError("Este teléfono ya está registrado con otra cédula.")

        # CASO C: No viene documento o el documento coincide → retornar identidad existente
        conn.close()
        return identity_id

    # 2) No existe identidad con este teléfono
    # Si viene documento real, verificar que no esté usado por otro teléfono
    if doc_n:
        cur.execute(f"""
            SELECT id FROM identities
            WHERE document_number = {P}
            LIMIT 1
        """, (doc_n,))
        conflict = cur.fetchone()
        if conflict:
            conn.close()
            raise ValueError("Esta cédula ya está registrada con otro teléfono.")

    # 3) Crear nueva identidad con documento real o placeholder
    final_doc = doc_n if doc_n else placeholder
    try:
        identity_id = _insert_returning_id(cur, f"""
            INSERT INTO identities (phone, document_number, full_name)
            VALUES ({P}, {P}, {P})
        """, (phone_n, final_doc, (full_name or "").strip() if full_name else None))
        conn.commit()
        conn.close()
        return identity_id
    except _IntegrityError as e:
        conn.rollback()
        conn.close()
        raise ValueError("Error al crear identidad.") from e


def ensure_user_person_id(user_id: int, person_id: int) -> None:
    """Amarra users.person_id si está vacío. No sobreescribe si ya existe."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT person_id FROM users WHERE id = {P}", (user_id,))
    row = cur.fetchone()
    if row and (row["person_id"] is None or row["person_id"] == ""):
        cur.execute(f"UPDATE users SET person_id = {P} WHERE id = {P}", (person_id, user_id))
        conn.commit()
    conn.close()


def add_user_role(user_id: int, role: str) -> None:
    """Inserta rol múltiple (user_roles). No falla si ya existe."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        if DB_ENGINE == "postgres":
            cur.execute(f"""
                INSERT INTO user_roles (user_id, role)
                VALUES ({P}, {P})
                ON CONFLICT DO NOTHING
            """, (user_id, role))
        else:
            cur.execute(f"""
                INSERT OR IGNORE INTO user_roles (user_id, role)
                VALUES ({P}, {P})
            """, (user_id, role))
        conn.commit()
    finally:
        conn.close()

def get_connection():
    """
    Devuelve una conexión a la base de datos.
    - SQLite si NO existe DATABASE_URL.
    - PostgreSQL si existe DATABASE_URL.
    """
    if DB_ENGINE == "postgres":
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

    db_path = os.getenv("DB_PATH", "domiquerendona.db")
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


STANDARD_ROLE_STATUSES = {"PENDING", "APPROVED", "REJECTED", "INACTIVE"}


def normalize_role_status(status: str) -> str:
    """
    Normaliza y valida estados estándar de roles.
    Estados válidos: PENDING, APPROVED, REJECTED, INACTIVE.
    """
    normalized = (status or "").strip().upper()
    if normalized not in STANDARD_ROLE_STATUSES:
        raise ValueError(f"Estado inválido: {status}. Use uno de: {', '.join(sorted(STANDARD_ROLE_STATUSES))}.")
    return normalized


def _audit_status_change(cur, entity_type: str, entity_id: int, old_status: str, new_status: str,
                         reason: str = None, source: str = None, changed_by: str = None):
    """
    Registra cambios de estado en status_audit_log sin romper el flujo principal.
    """
    try:
        cur.execute(f"""
            INSERT INTO status_audit_log (
                entity_type, entity_id, old_status, new_status, reason, source, changed_by
            ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P});
        """, (
            entity_type,
            entity_id,
            old_status,
            new_status,
            reason,
            source,
            changed_by or "UNKNOWN",
        ))
    except Exception as e:
        print("[WARN] No se pudo registrar status_audit_log:", e)


def init_db():
    # Postgres: usar schema dedicado (sin AUTOINCREMENT ni PRAGMA)
    if DB_ENGINE == "postgres":
        _init_db_postgres()
        return

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
            balance INTEGER DEFAULT 0 CHECK(balance >= 0),
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS map_link_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_link TEXT UNIQUE,
            expanded_link TEXT,
            lat REAL,
            lng REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS api_usage_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT NOT NULL,
            usage_date TEXT NOT NULL,
            call_count INTEGER DEFAULT 0,
            UNIQUE(api_name, usage_date)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS map_distance_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin_key TEXT NOT NULL,
            destination_key TEXT NOT NULL,
            mode TEXT NOT NULL,
            distance_km REAL NOT NULL,
            provider TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(origin_key, destination_key, mode)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS status_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            reason TEXT,
            source TEXT,
            changed_by TEXT DEFAULT 'UNKNOWN',
            created_at TEXT DEFAULT (datetime('now'))
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

    # map_link_cache: formatted_address, provider, place_id
    cur.execute("PRAGMA table_info(map_link_cache)")
    cache_cols = [r[1] for r in cur.fetchall()]
    if "formatted_address" not in cache_cols:
        cur.execute("ALTER TABLE map_link_cache ADD COLUMN formatted_address TEXT")
    if "provider" not in cache_cols:
        cur.execute("ALTER TABLE map_link_cache ADD COLUMN provider TEXT")
    if "place_id" not in cache_cols:
        cur.execute("ALTER TABLE map_link_cache ADD COLUMN place_id TEXT")

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
    if "residence_address" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN residence_address TEXT")
    if "residence_lat" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN residence_lat REAL")
    if "residence_lng" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN residence_lng REAL")

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
    if "residence_address" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN residence_address TEXT")
    if "residence_lat" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN residence_lat REAL")
    if "residence_lng" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN residence_lng REAL")

    # allies.soft delete + person_id
    cur.execute("PRAGMA table_info(allies)")
    allies_cols = [r[1] for r in cur.fetchall()]
    if "person_id" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN person_id INTEGER")
    if "is_deleted" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0")
    if "deleted_at" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN deleted_at TEXT")

    # admins: rejection_type, rejection_reason, rejected_at
    cur.execute("PRAGMA table_info(admins)")
    admins_cols = [r[1] for r in cur.fetchall()]
    if "rejection_type" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN rejection_type TEXT")
    if "rejection_reason" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN rejection_reason TEXT")
    if "rejected_at" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN rejected_at TEXT")

    # allies: rejection_type, rejection_reason, rejected_at
    cur.execute("PRAGMA table_info(allies)")
    allies_cols = [r[1] for r in cur.fetchall()]
    if "rejection_type" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN rejection_type TEXT")
    if "rejection_reason" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN rejection_reason TEXT")
    if "rejected_at" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN rejected_at TEXT")

    # couriers: rejection_type, rejection_reason, rejected_at
    cur.execute("PRAGMA table_info(couriers)")
    couriers_cols = [r[1] for r in cur.fetchall()]
    if "rejection_type" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN rejection_type TEXT")
    if "rejection_reason" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN rejection_reason TEXT")
    if "rejected_at" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN rejected_at TEXT")

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

    # Tabla: reference_alias_candidates (cola de referencias para validacion humana)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reference_alias_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_text TEXT NOT NULL,
            normalized_text TEXT NOT NULL UNIQUE,
            suggested_lat REAL,
            suggested_lng REAL,
            source TEXT,
            seen_count INTEGER NOT NULL DEFAULT 1,
            first_seen_at TEXT DEFAULT (datetime('now')),
            last_seen_at TEXT DEFAULT (datetime('now')),
            status TEXT NOT NULL DEFAULT 'PENDING',
            reviewed_by_admin_id INTEGER,
            reviewed_at TEXT,
            review_note TEXT,
            FOREIGN KEY (reviewed_by_admin_id) REFERENCES admins(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_alias_candidates_status ON reference_alias_candidates(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_alias_candidates_last_seen ON reference_alias_candidates(last_seen_at)")

    # Tabla: permisos para validar referencias (delegables por Admin Plataforma)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_reference_validator_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'INACTIVE',
            granted_by_admin_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (admin_id) REFERENCES admins(id),
            FOREIGN KEY (granted_by_admin_id) REFERENCES admins(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ref_validator_perm_status ON admin_reference_validator_permissions(status)")

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
            lat REAL,
            lng REAL,
            is_default INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ally_id) REFERENCES allies(id)
        );
    """)

    # Tabla: profile_change_requests (solicitudes de cambio de perfil)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS profile_change_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_user_id INTEGER NOT NULL,
            target_role TEXT NOT NULL,
            target_role_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            new_lat REAL,
            new_lng REAL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            team_admin_id INTEGER,
            team_code TEXT,
            reviewed_by_user_id INTEGER,
            reviewed_by_admin_id INTEGER,
            reviewed_at TEXT,
            rejection_reason TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pcr_status ON profile_change_requests(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pcr_team_admin ON profile_change_requests(team_admin_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pcr_team_code ON profile_change_requests(team_code)")

    # Tabla: admin_allies (relación admin-aliado)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_allies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            ally_id INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING',
            balance INTEGER DEFAULT 0 CHECK(balance >= 0),
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
            balance INTEGER DEFAULT 0 CHECK(balance >= 0),
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
            ally_admin_id_snapshot INTEGER,
            courier_admin_id_snapshot INTEGER,
            FOREIGN KEY (ally_id) REFERENCES allies(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id),
            FOREIGN KEY (pickup_location_id) REFERENCES ally_locations(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ally_courier_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            courier_id INTEGER NOT NULL,
            reason TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ally_id) REFERENCES allies(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id),
            UNIQUE(ally_id, courier_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_offer_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            courier_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING',
            offered_at TEXT,
            responded_at TEXT,
            response TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_pickup_confirmations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL UNIQUE,
            courier_id INTEGER NOT NULL,
            ally_id INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING',
            requested_at TEXT DEFAULT (datetime('now')),
            reviewed_at TEXT,
            reviewed_by_ally_id INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (courier_id) REFERENCES couriers(id),
            FOREIGN KEY (ally_id) REFERENCES allies(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_order_pickup_confirmations_status ON order_pickup_confirmations(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_order_pickup_confirmations_ally ON order_pickup_confirmations(ally_id)")

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
            is_active INTEGER DEFAULT 1,
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

    # ============================================================
    # G) TABLAS PARA AGENDA DE CLIENTES RECURRENTES (ally_customers)
    # ============================================================

    # Tabla: ally_customers (clientes recurrentes de cada aliado)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ally_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ally_id) REFERENCES allies(id)
        );
    """)

    # Índice para búsqueda rápida por aliado y teléfono
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ally_customers_ally_id ON ally_customers(ally_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ally_customers_ally_phone ON ally_customers(ally_id, phone)")

    # Tabla: ally_customer_addresses (direcciones de clientes recurrentes)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ally_customer_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            label TEXT,
            address_text TEXT NOT NULL,
            city TEXT,
            barrio TEXT,
            notes TEXT,
            lat REAL,
            lng REAL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (customer_id) REFERENCES ally_customers(id)
        );
    """)

    # Índice para búsqueda por cliente
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ally_customer_addresses_customer_id ON ally_customer_addresses(customer_id)")

    # Migración: agregar campos para base requerida en orders
    cur.execute("PRAGMA table_info(orders)")
    order_columns = [col[1] for col in cur.fetchall()]
    if 'requires_cash' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN requires_cash INTEGER DEFAULT 0")
    if 'cash_required_amount' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN cash_required_amount INTEGER DEFAULT 0")

    # Migración: agregar columna is_active si no existe
    cur.execute("PRAGMA table_info(terms_versions)")
    columns = [col[1] for col in cur.fetchall()]
    if 'is_active' not in columns:
        cur.execute("ALTER TABLE terms_versions ADD COLUMN is_active INTEGER DEFAULT 1")

    # Migración: agregar lat/lng a ally_locations
    cur.execute("PRAGMA table_info(ally_locations)")
    location_columns = [col[1] for col in cur.fetchall()]
    if 'lat' not in location_columns:
        cur.execute("ALTER TABLE ally_locations ADD COLUMN lat REAL")
    if 'lng' not in location_columns:
        cur.execute("ALTER TABLE ally_locations ADD COLUMN lng REAL")

    # Migración: agregar métricas de uso a ally_locations
    cur.execute("PRAGMA table_info(ally_locations)")
    location_columns = [col[1] for col in cur.fetchall()]
    if 'use_count' not in location_columns:
        cur.execute("ALTER TABLE ally_locations ADD COLUMN use_count INTEGER DEFAULT 0")
    if 'is_frequent' not in location_columns:
        cur.execute("ALTER TABLE ally_locations ADD COLUMN is_frequent INTEGER DEFAULT 0")
    if 'last_used_at' not in location_columns:
        cur.execute("ALTER TABLE ally_locations ADD COLUMN last_used_at TEXT")

    # Migración: agregar coords y quote_source a orders
    cur.execute("PRAGMA table_info(orders)")
    order_cols = [col[1] for col in cur.fetchall()]
    if 'pickup_lat' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN pickup_lat REAL")
    if 'pickup_lng' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN pickup_lng REAL")
    if 'dropoff_lat' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN dropoff_lat REAL")
    if 'dropoff_lng' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN dropoff_lng REAL")
    if 'quote_source' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN quote_source TEXT")
    if 'ally_admin_id_snapshot' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN ally_admin_id_snapshot INTEGER")
    if 'courier_admin_id_snapshot' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN courier_admin_id_snapshot INTEGER")

    try:
        cur.execute("ALTER TABLE orders ADD COLUMN canceled_by TEXT;")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN available_cash INTEGER DEFAULT 0;")
    except Exception:
        pass

    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN is_active INTEGER DEFAULT 0;")
    except Exception:
        pass

    # Columnas para live location y estado de disponibilidad
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN live_lat REAL;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN live_lng REAL;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN live_location_active INTEGER DEFAULT 0;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN live_location_updated_at TEXT;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN availability_status TEXT DEFAULT 'INACTIVE';")
    except Exception:
        pass
    # Normalizacion: availability_status debe usar estados estandar.
    try:
        cur.execute("UPDATE couriers SET availability_status = 'APPROVED' WHERE availability_status = 'ONLINE';")
        cur.execute("UPDATE couriers SET availability_status = 'INACTIVE' WHERE availability_status IN ('PAUSADO', 'OFFLINE') OR availability_status IS NULL;")
    except Exception:
        pass

    # Bootstrap: insertar términos por defecto para ALLY si no existen
    cur.execute("SELECT 1 FROM terms_versions WHERE role = 'ALLY' LIMIT 1")
    if not cur.fetchone():
        import hashlib
        terms_text = "Términos y Condiciones Domiquerendona - Rol ALLY v1.0"
        sha256_hash = hashlib.sha256(terms_text.encode()).hexdigest()
        cur.execute(
            "INSERT INTO terms_versions (role, version, url, sha256, is_active) VALUES (?, ?, ?, ?, ?)",
            ('ALLY', 'ALLY_V1', 'https://domiquerendona.com/terms/ally', sha256_hash, 1)
        )

    # ============================================================
    # H) TABLAS PARA SISTEMA DE RECARGAS
    # ============================================================

    # Migración: agregar balance a admins si no existe
    cur.execute("PRAGMA table_info(admins)")
    admins_cols = [r[1] for r in cur.fetchall()]
    if "balance" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN balance INTEGER DEFAULT 0")

    # Guardas no-negativos para DB existente (SQLite no permite agregar CHECK facil post-creacion)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_admins_balance_non_negative_insert
        BEFORE INSERT ON admins
        FOR EACH ROW
        WHEN COALESCE(NEW.balance, 0) < 0
        BEGIN
            SELECT RAISE(ABORT, 'admins.balance cannot be negative');
        END;
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_admins_balance_non_negative_update
        BEFORE UPDATE OF balance ON admins
        FOR EACH ROW
        WHEN COALESCE(NEW.balance, 0) < 0
        BEGIN
            SELECT RAISE(ABORT, 'admins.balance cannot be negative');
        END;
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_admin_couriers_balance_non_negative_insert
        BEFORE INSERT ON admin_couriers
        FOR EACH ROW
        WHEN COALESCE(NEW.balance, 0) < 0
        BEGIN
            SELECT RAISE(ABORT, 'admin_couriers.balance cannot be negative');
        END;
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_admin_couriers_balance_non_negative_update
        BEFORE UPDATE OF balance ON admin_couriers
        FOR EACH ROW
        WHEN COALESCE(NEW.balance, 0) < 0
        BEGIN
            SELECT RAISE(ABORT, 'admin_couriers.balance cannot be negative');
        END;
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_admin_allies_balance_non_negative_insert
        BEFORE INSERT ON admin_allies
        FOR EACH ROW
        WHEN COALESCE(NEW.balance, 0) < 0
        BEGIN
            SELECT RAISE(ABORT, 'admin_allies.balance cannot be negative');
        END;
    """)
    cur.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_admin_allies_balance_non_negative_update
        BEFORE UPDATE OF balance ON admin_allies
        FOR EACH ROW
        WHEN COALESCE(NEW.balance, 0) < 0
        BEGIN
            SELECT RAISE(ABORT, 'admin_allies.balance cannot be negative');
        END;
    """)

    # Tabla: recharge_requests (solicitudes de recarga)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recharge_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            requested_by_user_id INTEGER NOT NULL,
            decided_by_admin_id INTEGER,
            method TEXT,
            note TEXT,
            proof_file_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            decided_at TEXT,
            FOREIGN KEY (admin_id) REFERENCES admins(id),
            FOREIGN KEY (requested_by_user_id) REFERENCES users(id),
            FOREIGN KEY (decided_by_admin_id) REFERENCES admins(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recharge_requests_admin_status ON recharge_requests(admin_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_recharge_requests_target ON recharge_requests(target_type, target_id)")

    # Migración: agregar proof_file_id a recharge_requests si no existe
    cur.execute("PRAGMA table_info(recharge_requests)")
    rr_cols = [r[1] for r in cur.fetchall()]
    if "proof_file_id" not in rr_cols:
        cur.execute("ALTER TABLE recharge_requests ADD COLUMN proof_file_id TEXT")

    # Migración: agregar campos de pago a admins si no existen
    cur.execute("PRAGMA table_info(admins)")
    admins_pay_cols = [r[1] for r in cur.fetchall()]
    if "payment_phone" not in admins_pay_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN payment_phone TEXT")
    if "payment_bank" not in admins_pay_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN payment_bank TEXT")
    if "payment_holder" not in admins_pay_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN payment_holder TEXT")
    if "payment_instructions" not in admins_pay_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN payment_instructions TEXT")

    # Tabla: ledger (movimientos contables)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            from_type TEXT,
            from_id INTEGER,
            to_type TEXT NOT NULL,
            to_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            ref_type TEXT,
            ref_id INTEGER,
            note TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ledger_from ON ledger(from_type, from_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ledger_to ON ledger(to_type, to_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ledger_ref ON ledger(ref_type, ref_id)")

    # Tabla: admin_payment_methods (metodos de pago de admins)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            method_name TEXT NOT NULL,
            account_number TEXT NOT NULL,
            account_holder TEXT NOT NULL,
            instructions TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (admin_id) REFERENCES admins(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_payment_methods_admin ON admin_payment_methods(admin_id, is_active)")

    conn.commit()
    conn.close()


def _init_db_postgres():
    """Crea/migra tablas en Postgres usando postgres_schema.sql."""
    conn = get_connection()
    cur = conn.cursor()

    # 1) Ejecutar schema completo (CREATE TABLE IF NOT EXISTS + índices)
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "migrations", "postgres_schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        cur.execute(f.read())

    # 2) Migraciones de columnas para despliegues previos
    #    (si la tabla ya existía con schema viejo, agregar columnas faltantes)
    def _pg_add_col(table, column, col_type):
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = %s",
            (table, column),
        )
        if not cur.fetchone():
            cur.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}'
            )

    # admins
    for col, ctype in [
        ("balance", "INTEGER DEFAULT 0"),
        ("residence_address", "TEXT"),
        ("residence_lat", "REAL"),
        ("residence_lng", "REAL"),
        ("payment_phone", "TEXT"),
        ("payment_bank", "TEXT"),
        ("payment_holder", "TEXT"),
        ("payment_instructions", "TEXT"),
    ]:
        _pg_add_col("admins", col, ctype)

    # couriers
    for col, ctype in [
        ("available_cash", "INTEGER DEFAULT 0"),
        ("is_active", "INTEGER DEFAULT 0"),
        ("residence_address", "TEXT"),
        ("residence_lat", "REAL"),
        ("residence_lng", "REAL"),
    ]:
        _pg_add_col("couriers", col, ctype)

    # ally_locations
    for col, ctype in [
        ("lat", "REAL"),
        ("lng", "REAL"),
        ("use_count", "INTEGER DEFAULT 0"),
        ("is_frequent", "INTEGER DEFAULT 0"),
        ("last_used_at", "TIMESTAMP"),
    ]:
        _pg_add_col("ally_locations", col, ctype)

    # orders
    for col, ctype in [
        ("requires_cash", "INTEGER DEFAULT 0"),
        ("cash_required_amount", "INTEGER DEFAULT 0"),
        ("pickup_lat", "REAL"),
        ("pickup_lng", "REAL"),
        ("dropoff_lat", "REAL"),
        ("dropoff_lng", "REAL"),
        ("quote_source", "TEXT"),
        ("canceled_by", "TEXT"),
    ]:
        _pg_add_col("orders", col, ctype)

    # map_link_cache
    for col, ctype in [
        ("formatted_address", "TEXT"),
        ("provider", "TEXT"),
        ("place_id", "TEXT"),
    ]:
        _pg_add_col("map_link_cache", col, ctype)

    # recharge_requests
    _pg_add_col("recharge_requests", "proof_file_id", "TEXT")

    # terms_versions
    _pg_add_col("terms_versions", "is_active", "INTEGER DEFAULT 1")

    # 3) Migraciones de datos (idempotentes)

    # team_name / team_code bootstrap
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

    # free_orders_remaining cleanup
    cur.execute("""
        UPDATE couriers SET free_orders_remaining = 15
        WHERE free_orders_remaining IS NULL
    """)

    # availability_status normalización
    cur.execute("UPDATE couriers SET availability_status = 'APPROVED' WHERE availability_status = 'ONLINE'")
    cur.execute("UPDATE couriers SET availability_status = 'INACTIVE' WHERE availability_status IN ('PAUSADO', 'OFFLINE') OR availability_status IS NULL")

    # identities bootstrap (ON CONFLICT DO NOTHING = INSERT OR IGNORE)
    cur.execute("""
        INSERT INTO identities(phone, document_number, full_name)
        SELECT a.phone, a.document_number, a.full_name
        FROM admins a
        WHERE a.phone IS NOT NULL AND a.phone <> ''
          AND a.document_number IS NOT NULL AND a.document_number <> ''
        ON CONFLICT DO NOTHING
    """)
    cur.execute("""
        INSERT INTO identities(phone, document_number, full_name)
        SELECT c.phone, c.id_number, c.full_name
        FROM couriers c
        WHERE c.phone IS NOT NULL AND c.phone <> ''
          AND c.id_number IS NOT NULL AND c.id_number <> ''
        ON CONFLICT DO NOTHING
    """)
    cur.execute("""
        INSERT INTO identities(phone, document_number, full_name)
        SELECT al.phone, al.document_number, al.owner_name
        FROM allies al
        WHERE al.phone IS NOT NULL AND al.phone <> ''
          AND al.document_number IS NOT NULL AND al.document_number <> ''
        ON CONFLICT DO NOTHING
    """)

    # person_id linking
    cur.execute("""
        UPDATE admins SET person_id = (
            SELECT i.id FROM identities i
            WHERE i.phone = admins.phone AND i.document_number = admins.document_number
        )
        WHERE person_id IS NULL
          AND phone IS NOT NULL AND phone <> ''
          AND document_number IS NOT NULL AND document_number <> ''
    """)
    cur.execute("""
        UPDATE couriers SET person_id = (
            SELECT i.id FROM identities i
            WHERE i.phone = couriers.phone AND i.document_number = couriers.id_number
        )
        WHERE person_id IS NULL
          AND phone IS NOT NULL AND phone <> ''
          AND id_number IS NOT NULL AND id_number <> ''
    """)
    cur.execute("""
        UPDATE allies SET person_id = (
            SELECT i.id FROM identities i
            WHERE i.phone = allies.phone AND i.document_number = allies.document_number
        )
        WHERE person_id IS NULL
          AND phone IS NOT NULL AND phone <> ''
          AND document_number IS NOT NULL AND document_number <> ''
    """)

    # users.person_id (prioridad admins -> couriers -> allies)
    cur.execute("""
        UPDATE users SET person_id = (SELECT a.person_id FROM admins a WHERE a.user_id = users.id)
        WHERE person_id IS NULL
          AND EXISTS (SELECT 1 FROM admins a WHERE a.user_id = users.id AND a.person_id IS NOT NULL)
    """)
    cur.execute("""
        UPDATE users SET person_id = (SELECT c.person_id FROM couriers c WHERE c.user_id = users.id)
        WHERE person_id IS NULL
          AND EXISTS (SELECT 1 FROM couriers c WHERE c.user_id = users.id AND c.person_id IS NOT NULL)
    """)
    cur.execute("""
        UPDATE users SET person_id = (SELECT al.person_id FROM allies al WHERE al.user_id = users.id)
        WHERE person_id IS NULL
          AND EXISTS (SELECT 1 FROM allies al WHERE al.user_id = users.id AND al.person_id IS NOT NULL)
    """)

    # Terms bootstrap
    cur.execute("SELECT 1 FROM terms_versions WHERE role = 'ALLY' LIMIT 1")
    if not cur.fetchone():
        import hashlib
        terms_text = "Términos y Condiciones Domiquerendona - Rol ALLY v1.0"
        sha256_hash = hashlib.sha256(terms_text.encode()).hexdigest()
        cur.execute(
            "INSERT INTO terms_versions (role, version, url, sha256, is_active) VALUES (%s, %s, %s, %s, %s)",
            ('ALLY', 'ALLY_V1', 'https://domiquerendona.com/terms/ally', sha256_hash, 1),
        )

    conn.commit()
    conn.close()


def force_platform_admin(platform_telegram_id: int):
    """
    Asegura que el telegram_id tenga un admin PLATFORM aprobado en BD.
    - Crea user si no existe
    - Solo puede existir UN admin con team_code='PLATFORM' (UNIQUE constraint)
    - Si ya existe → reasigna user_id y pone status='APPROVED'
    - Si no existe → INSERT
    """
    conn = get_connection()
    cur = conn.cursor()
    _pg = DB_ENGINE == "postgres"
    NOW = "NOW()" if _pg else "datetime('now')"

    # 1) asegurar users
    cur.execute(f"SELECT id FROM users WHERE telegram_id = {P} LIMIT 1", (platform_telegram_id,))
    row = cur.fetchone()

    if row:
        user_id = row["id"]
    else:
        user_id = _insert_returning_id(
            cur,
            f"INSERT INTO users (telegram_id, username, role, created_at) VALUES ({P}, {P}, {P}, {NOW})",
            (platform_telegram_id, "platform", "ADMIN_PLATFORM"),
        )

    # 2) asegurar admins - buscar por team_code='PLATFORM' (UNIQUE, solo puede haber uno)
    cur.execute("""
        SELECT id FROM admins
        WHERE team_code = 'PLATFORM'
        LIMIT 1
    """)
    admin_row = cur.fetchone()

    if admin_row:
        # Ya existe PLATFORM, reasignar al user_id correcto y aprobar
        admin_id = admin_row["id"]
        cur.execute(f"""
            UPDATE admins
            SET user_id = {P}, status = 'APPROVED', is_deleted = 0
            WHERE id = {P}
        """, (user_id, admin_id))
    else:
        # No existe, crear nuevo
        cur.execute(f"""
            INSERT INTO admins (
                user_id, full_name, phone, city, barrio,
                status, created_at, team_name, document_number, team_code
            )
            VALUES (
                {P}, {P}, {P}, {P}, {P},
                'APPROVED', {NOW}, {P}, {P}, 'PLATFORM'
            )
        """, (
            user_id,
            "Administrador de Plataforma",
            "+570000000000",
            "PLATAFORMA",
            "PLATAFORMA",
            "PLATAFORMA",  # team_name
            "PLATFORM",    # document_number
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


def user_has_platform_admin(telegram_id: int) -> bool:
    """
    Retorna True si el usuario (telegram_id) tiene un admin en admins con:
    team_code='PLATFORM' y status='APPROVED' (is_deleted=0).
    """
    user_id = get_user_id_from_telegram_id(telegram_id)
    if not user_id:
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT 1 FROM admins
        WHERE user_id = {P} AND team_code = 'PLATFORM' AND status = 'APPROVED' AND is_deleted = 0
        LIMIT 1;
    """, (user_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_admin_by_user_id(user_id: int):
    """
    user_id = users.id (interno).
    Devuelve el admin más reciente asociado a esa cuenta.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            id, user_id, person_id, full_name, phone, city, barrio,
            status, created_at, team_name, document_number, team_code
        FROM admins
        WHERE user_id = {P} AND is_deleted = 0
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
    cur.execute(f"""
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
            created_at,         -- 10
            residence_address,  -- 11
            residence_lat,      -- 12
            residence_lng       -- 13
        FROM admins
        WHERE id = {P}
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

    cur.execute(f"""
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
        WHERE UPPER(TRIM(a.team_code)) = UPPER(TRIM({P}))
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
    cur.execute(f"SELECT * FROM users WHERE telegram_id = {P};", (telegram_id,))
    row = cur.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, telegram_id, username, created_at FROM users WHERE id = {P}",
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
        f"INSERT INTO users (telegram_id, username, role) VALUES ({P}, {P}, NULL);",
        (telegram_id, username),
    )
    conn.commit()
    conn.close()
    return get_user_by_telegram_id(telegram_id)


# ---------- CONFIGURACIÓN GLOBAL (settings) ----------
def get_setting(key: str, default=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT value FROM settings WHERE key = {P} LIMIT 1", (key,))
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
    FASE 1: Incluye admins PENDING y APPROVED para permitir migración desde WhatsApp.
    Retorna filas con: (admin_id, team_name, team_code, status)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            a.id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code,
            a.status
        FROM admins a
        WHERE a.status IN ('PENDING', 'APPROVED')
          AND a.is_deleted = 0
          AND a.team_code IS NOT NULL
          AND TRIM(a.team_code) <> ''
        ORDER BY a.id ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def list_approved_admin_teams(include_platform: bool = True):
    """
    Devuelve equipos aprobados para vistas de plataforma.
    Retorna filas con: (id, team_name, team_code, status, balance)
    """
    conn = get_connection()
    cur = conn.cursor()
    where_platform = ""
    if not include_platform:
        where_platform = "AND a.team_code != 'PLATFORM'"
    cur.execute(f"""
        SELECT
            a.id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code,
            a.status,
            a.balance
        FROM admins a
        WHERE a.status = 'APPROVED'
          AND a.is_deleted = 0
          AND a.team_code IS NOT NULL
          AND TRIM(a.team_code) <> ''
          {where_platform}
        ORDER BY a.id ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def list_courier_links_by_admin(admin_id: int, limit: int = 20, offset: int = 0):
    """
    Lista vínculos APPROVED admin_couriers con saldo por vínculo.
    Retorna: (link_id, courier_id, full_name, phone, city, barrio, balance)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            ac.id AS link_id,
            c.id AS courier_id,
            c.full_name,
            c.phone,
            c.city,
            c.barrio,
            ac.balance
        FROM admin_couriers ac
        JOIN couriers c ON c.id = ac.courier_id
        WHERE ac.admin_id = {P}
          AND ac.status = 'APPROVED'
        ORDER BY c.full_name ASC
        LIMIT {P} OFFSET {P}
    """, (admin_id, limit, offset))
    rows = cur.fetchall()
    conn.close()
    return rows


def block_courier_for_ally(ally_id: int, courier_id: int, reason: str = None):
    """Aliado bloquea/veta a un courier."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT OR IGNORE INTO ally_courier_blocks (ally_id, courier_id, reason)
        VALUES ({P}, {P}, {P});
    """, (ally_id, courier_id, reason))
    conn.commit()
    conn.close()


def unblock_courier_for_ally(ally_id: int, courier_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM ally_courier_blocks WHERE ally_id = {P} AND courier_id = {P};",
                (ally_id, courier_id))
    conn.commit()
    conn.close()


def get_blocked_courier_ids_for_ally(ally_id: int) -> set:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT courier_id FROM ally_courier_blocks WHERE ally_id = {P};", (ally_id,))
    rows = cur.fetchall()
    conn.close()
    return {row[0] for row in rows}


def create_offer_queue(order_id: int, courier_ids: list):
    """Crea la cola de ofertas para un pedido. courier_ids ya viene ordenado por prioridad."""
    conn = get_connection()
    cur = conn.cursor()
    for position, courier_id in enumerate(courier_ids):
        cur.execute(f"""
            INSERT INTO order_offer_queue (order_id, courier_id, position, status)
            VALUES ({P}, {P}, {P}, 'PENDING');
        """, (order_id, courier_id, position))
    conn.commit()
    conn.close()


def get_next_pending_offer(order_id: int):
    """Devuelve el siguiente courier en cola con status PENDING."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT oq.id, oq.courier_id, oq.position, c.full_name, u.telegram_id
        FROM order_offer_queue oq
        JOIN couriers c ON c.id = oq.courier_id
        JOIN users u ON u.id = c.user_id
        WHERE oq.order_id = {P} AND oq.status = 'PENDING'
        ORDER BY oq.position ASC
        LIMIT 1;
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "queue_id": row[0],
        "courier_id": row[1],
        "position": row[2],
        "full_name": row[3],
        "telegram_id": row[4],
    }


def mark_offer_as_offered(queue_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE order_offer_queue
        SET status = 'OFFERED', offered_at = datetime('now')
        WHERE id = {P};
    """, (queue_id,))
    conn.commit()
    conn.close()


def mark_offer_response(queue_id: int, response: str):
    """response: 'ACCEPTED', 'REJECTED', o 'EXPIRED'"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE order_offer_queue
        SET status = {P}, response = {P}, responded_at = datetime('now')
        WHERE id = {P};
    """, (response, response, queue_id))
    conn.commit()
    conn.close()


def get_current_offer_for_order(order_id: int):
    """Devuelve la oferta actualmente en status OFFERED para un pedido."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT oq.id, oq.courier_id, oq.position, u.telegram_id
        FROM order_offer_queue oq
        JOIN couriers c ON c.id = oq.courier_id
        JOIN users u ON u.id = c.user_id
        WHERE oq.order_id = {P} AND oq.status = 'OFFERED'
        LIMIT 1;
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "queue_id": row[0],
        "courier_id": row[1],
        "position": row[2],
        "telegram_id": row[3],
    }


def reset_offer_queue(order_id: int):
    """Resetea toda la cola a PENDING para reiniciar el ciclo."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE order_offer_queue
        SET status = 'PENDING', offered_at = NULL, responded_at = NULL, response = NULL
        WHERE order_id = {P} AND status IN ('REJECTED', 'EXPIRED');
    """, (order_id,))
    conn.commit()
    conn.close()


def delete_offer_queue(order_id: int):
    """Elimina la cola de ofertas de un pedido (al cancelar o completar)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM order_offer_queue WHERE order_id = {P};", (order_id,))
    conn.commit()
    conn.close()


def upsert_order_pickup_confirmation(order_id: int, courier_id: int, ally_id: int, status: str = "PENDING"):
    status = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO order_pickup_confirmations (
            order_id, courier_id, ally_id, status, requested_at, reviewed_at, reviewed_by_ally_id
        )
        VALUES ({P}, {P}, {P}, {P}, datetime('now'), NULL, NULL)
        ON CONFLICT(order_id)
        DO UPDATE SET
            courier_id=excluded.courier_id,
            ally_id=excluded.ally_id,
            status=excluded.status,
            requested_at=datetime('now'),
            reviewed_at=NULL,
            reviewed_by_ally_id=NULL;
    """, (order_id, courier_id, ally_id, status))
    conn.commit()
    conn.close()


def get_order_pickup_confirmation(order_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, order_id, courier_id, ally_id, status, requested_at, reviewed_at, reviewed_by_ally_id
        FROM order_pickup_confirmations
        WHERE order_id = {P}
        LIMIT 1;
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    return row


def review_order_pickup_confirmation(order_id: int, new_status: str, reviewed_by_ally_id: int):
    new_status = normalize_role_status(new_status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE order_pickup_confirmations
        SET status = {P},
            reviewed_by_ally_id = {P},
            reviewed_at = datetime('now')
        WHERE order_id = {P}
          AND status = 'PENDING';
    """, (new_status, reviewed_by_ally_id, order_id))
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def set_courier_available_cash(courier_id: int, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE couriers SET available_cash = {P}, is_active = 1 WHERE id = {P};",
                (amount, courier_id))
    conn.commit()
    conn.close()


def deactivate_courier(courier_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE couriers SET is_active = 0, available_cash = 0, "
        f"availability_status = 'INACTIVE', live_location_active = 0 WHERE id = {P};",
        (courier_id,))
    conn.commit()
    conn.close()


def update_courier_live_location(courier_id: int, lat: float, lng: float):
    """Actualiza ubicacion en vivo y mantiene availability_status en estado estandar."""
    retries = 5
    for attempt in range(retries):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE couriers SET live_lat = {P}, live_lng = {P}, "
                "live_location_active = 1, live_location_updated_at = datetime('now'), "
                f"availability_status = 'APPROVED' WHERE id = {P};",
                (lat, lng, courier_id))
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "database is locked" in message and attempt < retries - 1:
                time.sleep(0.15 * (attempt + 1))
                continue
            if "database is locked" in message:
                print("[WARN] update_courier_live_location: database is locked tras reintentos")
                return False
            raise
        finally:
            conn.close()
    return False


def set_courier_availability(courier_id: int, status: str):
    """Cambia availability_status usando estados estandar (APPROVED/INACTIVE)."""
    conn = get_connection()
    cur = conn.cursor()
    normalized = normalize_role_status(status)
    if normalized == 'INACTIVE':
        cur.execute(
            "UPDATE couriers SET availability_status = 'INACTIVE', "
            f"live_location_active = 0 WHERE id = {P};",
            (courier_id,))
    else:
        cur.execute(
            f"UPDATE couriers SET availability_status = {P} WHERE id = {P};",
            (normalized, courier_id))
    conn.commit()
    conn.close()


def get_courier_availability(courier_id: int) -> str:
    """Retorna el availability_status del courier."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT availability_status FROM couriers WHERE id = {P};", (courier_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row["availability_status"] if isinstance(row, dict) else row[0]
    return "INACTIVE"


def expire_stale_live_locations(timeout_seconds: int = 120):
    """
    Marca como INACTIVE a couriers con live_location vencida.
    Retorna la lista de courier_ids afectados.
    """
    retries = 5
    for attempt in range(retries):
        conn = get_connection()
        try:
            cur = conn.cursor()

            # Primero obtener los que van a expirar
            cur.execute(f"""
                SELECT id FROM couriers
                WHERE availability_status = 'APPROVED'
                  AND live_location_active = 1
                  AND live_location_updated_at < datetime('now', {P} || ' seconds')
            """, ('-' + str(timeout_seconds),))
            expired = [row[0] if not isinstance(row, dict) else row["id"] for row in cur.fetchall()]

            if expired:
                cur.execute(f"""
                    UPDATE couriers
                    SET availability_status = 'INACTIVE', live_location_active = 0
                    WHERE availability_status = 'APPROVED'
                      AND live_location_active = 1
                      AND live_location_updated_at < datetime('now', {P} || ' seconds')
                """, ('-' + str(timeout_seconds),))
                conn.commit()

            return expired
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "database is locked" in message and attempt < retries - 1:
                time.sleep(0.15 * (attempt + 1))
                continue
            if "database is locked" in message:
                print("[WARN] expire_stale_live_locations: database is locked tras reintentos")
                return []
            raise
        finally:
            conn.close()
    return []


def get_active_courier_cash(courier_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT available_cash FROM couriers WHERE id = {P};", (courier_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def get_active_orders_by_ally(ally_id: int):
    """Devuelve pedidos activos de un aliado (no entregados ni cancelados)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT * FROM orders
        WHERE ally_id = {P}
          AND status NOT IN ('DELIVERED', 'CANCELLED')
        ORDER BY created_at DESC;
    """, (ally_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def cancel_order(order_id: int, canceled_by: str):
    """Cancela un pedido. canceled_by: 'ALLY', 'COURIER', 'ADMIN', 'SYSTEM'."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE orders
        SET status = 'CANCELLED', canceled_at = datetime('now'), canceled_by = {P}
        WHERE id = {P};
    """, (canceled_by, order_id))
    conn.commit()
    conn.close()


def release_order_from_courier(order_id: int):
    """Courier libera el pedido. Vuelve a PUBLISHED y limpia courier_id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE orders
        SET status = 'PUBLISHED', courier_id = NULL, accepted_at = NULL
        WHERE id = {P};
    """, (order_id,))
    conn.commit()
    conn.close()


def get_eligible_couriers_for_order(admin_id: int, ally_id: int = None,
                                      requires_cash: bool = False,
                                      cash_required_amount: int = 0,
                                      pickup_lat: float = None,
                                      pickup_lng: float = None):
    """
    Devuelve couriers elegibles para un pedido, filtrados por:
    - Aprobados y activos en el equipo
    - No eliminados
    - is_active = 1 (courier se activo y declaro base)
    - No vetados por el aliado (si ally_id dado)
    - Con base suficiente (si requires_cash)

    Ordenamiento inteligente:
    1. APPROVED + live_location_active=1 primero, por distancia al pickup
    2. APPROVED + live_location_active=0 segundo, por distancia
    3. INACTIVE al final por available_cash DESC (fallback)

    Si no hay pickup_lat/lng, usa el orden por available_cash DESC como antes.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = f"""
        SELECT c.id AS courier_id, c.full_name, u.telegram_id, c.available_cash,
               c.availability_status, c.live_lat, c.live_lng, c.live_location_active,
               c.residence_lat, c.residence_lng
        FROM admin_couriers ac
        JOIN couriers c ON c.id = ac.courier_id
        JOIN users u ON u.id = c.user_id
        WHERE ac.admin_id = {P}
          AND ac.status = 'APPROVED'
          AND c.status = 'APPROVED'
          AND (c.is_deleted IS NULL OR c.is_deleted = 0)
          AND c.is_active = 1
    """
    params = [admin_id]

    if ally_id:
        query += f"""
          AND c.id NOT IN (
              SELECT courier_id FROM ally_courier_blocks WHERE ally_id = {P}
          )
        """
        params.append(ally_id)

    if requires_cash and cash_required_amount > 0:
        query += f" AND c.available_cash >= {P}"
        params.append(cash_required_amount)

    query += " ORDER BY c.available_cash DESC;"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    result = []
    for row in rows:
        if isinstance(row, dict):
            item = {
                "courier_id": row["courier_id"],
                "full_name": row["full_name"],
                "telegram_id": row["telegram_id"],
                "available_cash": row["available_cash"],
                "availability_status": row.get("availability_status", "INACTIVE"),
                "live_location_active": row.get("live_location_active", 0),
                "live_lat": row.get("live_lat"),
                "live_lng": row.get("live_lng"),
                "residence_lat": row.get("residence_lat"),
                "residence_lng": row.get("residence_lng"),
            }
        else:
            item = {
                "courier_id": row[0],
                "full_name": row[1],
                "telegram_id": row[2],
                "available_cash": row[3],
                "availability_status": row[4] if len(row) > 4 else "INACTIVE",
                "live_lat": row[5] if len(row) > 5 else None,
                "live_lng": row[6] if len(row) > 6 else None,
                "live_location_active": row[7] if len(row) > 7 else 0,
                "residence_lat": row[8] if len(row) > 8 else None,
                "residence_lng": row[9] if len(row) > 9 else None,
            }
        result.append(item)

    # Ordenamiento inteligente si tenemos coordenadas de pickup
    if pickup_lat is not None and pickup_lng is not None:
        import math

        def _haversine(lat1, lng1, lat2, lng2):
            r = 6371.0
            p1, p2 = math.radians(lat1), math.radians(lat2)
            dlat = math.radians(lat2 - lat1)
            dlng = math.radians(lng2 - lng1)
            a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
            return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        def _sort_key(c):
            status = c.get("availability_status", "INACTIVE")
            is_live = int(c.get("live_location_active") or 0) == 1
            if status == "APPROVED" and is_live:
                priority = 0
            elif status == "APPROVED":
                priority = 1
            else:
                priority = 2

            # Mejor ubicacion disponible: live > residence
            clat = c.get("live_lat") or c.get("residence_lat")
            clng = c.get("live_lng") or c.get("residence_lng")

            if clat is not None and clng is not None:
                dist = _haversine(pickup_lat, pickup_lng, clat, clng)
            else:
                dist = 9999  # Sin ubicacion, al final

            return (priority, dist, -int(c.get("available_cash") or 0))

        result.sort(key=_sort_key)

    return result


def list_ally_links_by_admin(admin_id: int, limit: int = 20, offset: int = 0):
    """
    Lista vínculos APPROVED admin_allies con saldo por vínculo.
    Retorna: (link_id, ally_id, business_name, owner_name, phone, city, barrio, balance)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            aa.id AS link_id,
            al.id AS ally_id,
            al.business_name,
            al.owner_name,
            al.phone,
            al.city,
            al.barrio,
            aa.balance
        FROM admin_allies aa
        JOIN allies al ON al.id = aa.ally_id
        WHERE aa.admin_id = {P}
          AND aa.status = 'APPROVED'
        ORDER BY al.business_name ASC
        LIMIT {P} OFFSET {P}
    """, (admin_id, limit, offset))
    rows = cur.fetchall()
    conn.close()
    return rows


def upsert_admin_ally_link(admin_id: int, ally_id: int, status: str = "PENDING"):
    """
    Crea o actualiza el vínculo admin_allies para este aliado con este admin.
    Por defecto queda PENDING hasta aprobación.
    Solo usa estados válidos: PENDING, APPROVED, REJECTED, INACTIVE.
    """
    status = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()

    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        INSERT INTO admin_allies (admin_id, ally_id, status, balance, created_at, updated_at)
        VALUES ({P}, {P}, {P}, 0, {now_sql}, {now_sql})
        ON CONFLICT(admin_id, ally_id)
        DO UPDATE SET
            status = excluded.status,
            updated_at = {now_sql}
    """, (admin_id, ally_id, status))

    conn.commit()
    conn.close()


def deactivate_other_approved_admin_courier_links(courier_id: int, keep_admin_id: int):
    """
    Inactiva vÃ­nculos APPROVED para este courier con otros admins.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admin_couriers
        SET status='INACTIVE', updated_at=datetime('now')
        WHERE courier_id={P}
          AND status='APPROVED'
          AND admin_id<>{P};
    """, (courier_id, keep_admin_id))
    conn.commit()
    conn.close()


def deactivate_other_approved_admin_ally_links(ally_id: int, keep_admin_id: int):
    """
    Inactiva vÃ­nculos APPROVED para este aliado con otros admins.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admin_allies
        SET status='INACTIVE', updated_at=datetime('now')
        WHERE ally_id={P}
          AND status='APPROVED'
          AND admin_id<>{P};
    """, (ally_id, keep_admin_id))
    conn.commit()
    conn.close()


def upsert_admin_courier_link(admin_id: int, courier_id: int, status: str = "PENDING", is_active: int = 1):
    status = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    has_is_active = DB_ENGINE == "postgres"
    if DB_ENGINE != "postgres":
        cur.execute("PRAGMA table_info(admin_couriers)")
        cols = {row["name"] for row in cur.fetchall()}
        has_is_active = "is_active" in cols

    if has_is_active:
        cur.execute(f"""
            INSERT INTO admin_couriers (admin_id, courier_id, status, is_active, created_at, updated_at)
            VALUES ({P}, {P}, {P}, {P}, {now_sql}, {now_sql})
            ON CONFLICT(admin_id, courier_id)
            DO UPDATE SET
                status=excluded.status,
                is_active=excluded.is_active,
                updated_at={now_sql}
        """, (admin_id, courier_id, status, is_active))
    else:
        cur.execute(f"""
            INSERT INTO admin_couriers (admin_id, courier_id, status, created_at, updated_at)
            VALUES ({P}, {P}, {P}, {now_sql}, {now_sql})
            ON CONFLICT(admin_id, courier_id)
            DO UPDATE SET
                status=excluded.status,
                updated_at={now_sql}
        """, (admin_id, courier_id, status))
    conn.commit()
    conn.close()


def set_setting(key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO settings (key, value)
        VALUES ({P}, {P})
        ON CONFLICT(key) DO UPDATE SET value = excluded.value;
    """, (key, value))
    conn.commit()
    conn.close()


def ensure_pricing_defaults():
    """
    Inicializa valores por defecto de tarifas de precio en settings.
    Solo inserta si no existen (idempotente).
    """
    defaults = {
        "pricing_precio_0_2km": "5000",
        "pricing_precio_2_3km": "6000",
        "pricing_base_distance_km": "3.0",
        "pricing_km_extra_normal": "1200",
        "pricing_umbral_km_largo": "10.0",
        "pricing_km_extra_largo": "1000",
    }
    for k, v in defaults.items():
        existing = get_setting(k)
        if existing is None:
            set_setting(k, v)


# ---------- REFERENCIAS LOCALES (CATALOGO + VALIDACION) ----------

def _normalize_reference_text(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def upsert_reference_alias_candidate(raw_text: str, normalized_text: str, suggested_lat=None,
                                     suggested_lng=None, source: str = None):
    """
    Registra o incrementa un candidato de referencia local.
    No elimina registros; solo actualiza contador y ultima vez visto.
    """
    if not raw_text:
        return

    normalized = _normalize_reference_text(normalized_text or raw_text)
    if not normalized:
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO reference_alias_candidates
            (raw_text, normalized_text, suggested_lat, suggested_lng, source, status)
        VALUES ({P}, {P}, {P}, {P}, {P}, 'PENDING')
        ON CONFLICT(normalized_text) DO UPDATE SET
            raw_text = excluded.raw_text,
            suggested_lat = COALESCE(reference_alias_candidates.suggested_lat, excluded.suggested_lat),
            suggested_lng = COALESCE(reference_alias_candidates.suggested_lng, excluded.suggested_lng),
            source = COALESCE(excluded.source, reference_alias_candidates.source),
            seen_count = reference_alias_candidates.seen_count + 1,
            last_seen_at = datetime('now'),
            status = CASE
                WHEN reference_alias_candidates.status = 'REJECTED' THEN 'REJECTED'
                ELSE reference_alias_candidates.status
            END
    """, (raw_text.strip(), normalized, suggested_lat, suggested_lng, source))
    conn.commit()
    conn.close()


def list_reference_alias_candidates(status: str = "PENDING", limit: int = 20, offset: int = 0):
    wanted = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            id, raw_text, normalized_text, suggested_lat, suggested_lng, source,
            seen_count, first_seen_at, last_seen_at, status
        FROM reference_alias_candidates
        WHERE status = {P}
        ORDER BY last_seen_at DESC, id DESC
        LIMIT {P} OFFSET {P}
    """, (wanted, int(limit), int(offset)))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_reference_alias_candidate_by_id(candidate_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            id, raw_text, normalized_text, suggested_lat, suggested_lng, source,
            seen_count, first_seen_at, last_seen_at, status,
            reviewed_by_admin_id, reviewed_at, review_note
        FROM reference_alias_candidates
        WHERE id = {P}
        LIMIT 1
    """, (candidate_id,))
    row = cur.fetchone()
    conn.close()
    return row


def set_reference_alias_candidate_coords(candidate_id: int, lat: float, lng: float,
                                         source: str = "manual_pin") -> bool:
    """
    Asigna coordenadas manuales a una referencia candidata.
    Mantiene el estado actual; solo actualiza coordenadas/fuente y timestamps.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE reference_alias_candidates
        SET suggested_lat = {P},
            suggested_lng = {P},
            source = COALESCE({P}, source),
            last_seen_at = datetime('now')
        WHERE id = {P}
    """, (float(lat), float(lng), source, int(candidate_id)))
    changed = cur.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def _upsert_location_reference_alias(alias_text: str, lat: float, lng: float, label: str = ""):
    raw = get_setting("location_reference_aliases_json", "")
    aliases = {}
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                aliases = parsed
        except Exception:
            aliases = {}

    key = _normalize_reference_text(alias_text)
    if not key:
        return

    aliases[key] = {"lat": float(lat), "lng": float(lng), "label": (label or alias_text or "").strip()}
    set_setting("location_reference_aliases_json", json.dumps(aliases, ensure_ascii=True))


def review_reference_alias_candidate(candidate_id: int, new_status: str, reviewed_by_admin_id: int,
                                     note: str = None):
    status = normalize_role_status(new_status)
    if status not in {"APPROVED", "REJECTED", "INACTIVE"}:
        raise ValueError("Estado invalido para revision de referencia.")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, raw_text, normalized_text, suggested_lat, suggested_lng, status
        FROM reference_alias_candidates
        WHERE id = {P}
        LIMIT 1
    """, (candidate_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Referencia no encontrada."

    if row["status"] == "APPROVED":
        conn.close()
        return False, "La referencia ya estaba APPROVED."

    if status == "APPROVED":
        lat = row["suggested_lat"]
        lng = row["suggested_lng"]
        if lat is None or lng is None:
            conn.close()
            return False, "No se puede aprobar sin coordenadas sugeridas."

    conn.close()

    if status == "APPROVED":
        _upsert_location_reference_alias(row["normalized_text"], float(lat), float(lng), row["raw_text"])

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        UPDATE reference_alias_candidates
        SET status = {P}, reviewed_by_admin_id = {P}, reviewed_at = datetime('now'), review_note = {P}
        WHERE id = {P}
    """, (status, reviewed_by_admin_id, (note or "").strip() or None, candidate_id))
    conn.commit()
    conn.close()
    return True, "Referencia actualizada a {}.".format(status)


def get_admin_reference_validator_permission(admin_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, admin_id, status, granted_by_admin_id, created_at, updated_at
        FROM admin_reference_validator_permissions
        WHERE admin_id = {P}
        LIMIT 1
    """, (admin_id,))
    row = cur.fetchone()
    conn.close()
    return row


def set_admin_reference_validator_permission(admin_id: int, new_status: str, granted_by_admin_id: int):
    status = normalize_role_status(new_status)
    if status not in {"APPROVED", "INACTIVE"}:
        raise ValueError("Estado invalido para permiso de validador.")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO admin_reference_validator_permissions
            (admin_id, status, granted_by_admin_id)
        VALUES ({P}, {P}, {P})
        ON CONFLICT(admin_id) DO UPDATE SET
            status = excluded.status,
            granted_by_admin_id = excluded.granted_by_admin_id,
            updated_at = datetime('now')
    """, (admin_id, status, granted_by_admin_id))
    conn.commit()
    conn.close()


def can_admin_validate_references(admin_id: int) -> bool:
    perm = get_admin_reference_validator_permission(admin_id)
    return bool(perm and perm["status"] == "APPROVED")


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
        ally_id = _insert_returning_id(cur, f"""
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
            VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P});
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
        conn.commit()

    except _IntegrityError as e:
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
    cur.execute(f"""
        SELECT *
        FROM couriers
        WHERE user_id = {P} AND (is_deleted IS NULL OR is_deleted = 0)
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
    cur.execute(f"""
        SELECT *
        FROM allies
        WHERE user_id = {P} AND (is_deleted IS NULL OR is_deleted = 0)
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
        f"SELECT * FROM allies WHERE id = {P} LIMIT 1;",
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
            status,
            residence_address,
            residence_lat,
            residence_lng
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

def update_admin_status_by_id(admin_id: int, new_status: str, rejection_type: str = None,
                              rejection_reason: str = None, changed_by: str = None):
    new_status = normalize_role_status(new_status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT status FROM admins WHERE id = {P} AND is_deleted = 0", (admin_id,))
    row_old = cur.fetchone()
    old_status = _row_value(row_old, "status", 0)

    if new_status == "REJECTED" and rejection_type:
        # Rechazo tipificado: actualizar status + rejection fields + rejected_at
        cur.execute(f"""
            UPDATE admins
            SET status = {P},
                rejection_type = {P},
                rejection_reason = {P},
                rejected_at = datetime('now')
            WHERE id = {P} AND is_deleted = 0;
        """, (new_status, rejection_type, rejection_reason, admin_id))
    else:
        # Actualizar solo status (compatible con llamadas existentes)
        cur.execute(f"""
            UPDATE admins
            SET status = {P}
            WHERE id = {P} AND is_deleted = 0;
        """, (new_status, admin_id))

    if cur.rowcount > 0:
        reason = rejection_reason if rejection_reason else rejection_type
        _audit_status_change(
            cur,
            entity_type="ADMIN",
            entity_id=admin_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            source="update_admin_status_by_id",
            changed_by=changed_by,
        )

    conn.commit()
    conn.close()

def update_courier_status_by_id(courier_id: int, new_status: str, rejection_type: str = None,
                                rejection_reason: str = None, changed_by: str = None):
    new_status = normalize_role_status(new_status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT status FROM couriers WHERE id = {P} AND (is_deleted IS NULL OR is_deleted = 0)", (courier_id,))
    row_old = cur.fetchone()
    old_status = _row_value(row_old, "status", 0)

    if new_status == "REJECTED" and rejection_type:
        # Rechazo tipificado: actualizar status + rejection fields + rejected_at
        cur.execute(f"""
            UPDATE couriers
            SET status = {P},
                rejection_type = {P},
                rejection_reason = {P},
                rejected_at = datetime('now')
            WHERE id = {P} AND (is_deleted IS NULL OR is_deleted = 0);
        """, (new_status, rejection_type, rejection_reason, courier_id))
    else:
        # Actualizar solo status (compatible con llamadas existentes)
        cur.execute(f"""
            UPDATE couriers
            SET status = {P}
            WHERE id = {P} AND (is_deleted IS NULL OR is_deleted = 0);
        """, (new_status, courier_id))

    if cur.rowcount > 0:
        reason = rejection_reason if rejection_reason else rejection_type
        _audit_status_change(
            cur,
            entity_type="COURIER",
            entity_id=courier_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            source="update_courier_status_by_id",
            changed_by=changed_by,
        )

    conn.commit()
    conn.close()

def update_ally_status_by_id(ally_id: int, new_status: str, rejection_type: str = None,
                             rejection_reason: str = None, changed_by: str = None):
    new_status = normalize_role_status(new_status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT status FROM allies WHERE id = {P} AND (is_deleted IS NULL OR is_deleted = 0)", (ally_id,))
    row_old = cur.fetchone()
    old_status = _row_value(row_old, "status", 0)

    if new_status == "REJECTED" and rejection_type:
        # Rechazo tipificado: actualizar status + rejection fields + rejected_at
        cur.execute(f"""
            UPDATE allies
            SET status = {P},
                rejection_type = {P},
                rejection_reason = {P},
                rejected_at = datetime('now')
            WHERE id = {P} AND (is_deleted IS NULL OR is_deleted = 0);
        """, (new_status, rejection_type, rejection_reason, ally_id))
    else:
        # Actualizar solo status (compatible con llamadas existentes)
        cur.execute(f"""
            UPDATE allies
            SET status = {P}
            WHERE id = {P} AND (is_deleted IS NULL OR is_deleted = 0);
        """, (new_status, ally_id))

    if cur.rowcount > 0:
        reason = rejection_reason if rejection_reason else rejection_type
        _audit_status_change(
            cur,
            entity_type="ALLY",
            entity_id=ally_id,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            source="update_ally_status_by_id",
            changed_by=changed_by,
        )

    conn.commit()
    conn.close()


def get_admin_rejection_type_by_id(admin_id: int):
    """Devuelve el rejection_type del admin especificado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT rejection_type FROM admins WHERE id = {P}", (admin_id,))
    row = cur.fetchone()
    conn.close()
    return _row_value(row, "rejection_type", 0)


def get_ally_rejection_type_by_id(ally_id: int):
    """Devuelve el rejection_type del aliado especificado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT rejection_type FROM allies WHERE id = {P}", (ally_id,))
    row = cur.fetchone()
    conn.close()
    return _row_value(row, "rejection_type", 0)


def get_courier_rejection_type_by_id(courier_id: int):
    """Devuelve el rejection_type del repartidor especificado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT rejection_type FROM couriers WHERE id = {P}", (courier_id,))
    row = cur.fetchone()
    conn.close()
    return _row_value(row, "rejection_type", 0)


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

    cur.execute(f"""
        SELECT
            c.id AS courier_id,
            c.full_name,
            c.phone,
            c.city,
            c.barrio
        FROM admin_couriers ac
        JOIN couriers c ON c.id = ac.courier_id
        WHERE ac.admin_id = {P}
          AND ac.status = 'PENDING'
          AND c.status != 'REJECTED'
        ORDER BY ac.created_at ASC
    """, (admin_id,))

    rows = cur.fetchall()
    conn.close()
    return rows

def get_couriers_by_admin_and_status(admin_id, status):
    """
    Lista repartidores de un admin por estado del vínculo (APPROVED, INACTIVE, REJECTED, etc.)
    Devuelve: (courier_id, full_name, phone, city, barrio, balance, link_status)
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
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
        WHERE ac.admin_id = {P}
          AND ac.status = {P}
        ORDER BY c.full_name ASC
    """, (admin_id, status))

    rows = cur.fetchall()
    conn.close()
    return rows
    

def create_admin_courier_link(admin_id: int, courier_id: int):
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    has_is_active = DB_ENGINE == "postgres"
    if DB_ENGINE != "postgres":
        cur.execute("PRAGMA table_info(admin_couriers)")
        cols = {row["name"] for row in cur.fetchall()}
        has_is_active = "is_active" in cols

    if has_is_active:
        if DB_ENGINE == "postgres":
            cur.execute(f"""
                INSERT INTO admin_couriers (admin_id, courier_id, status, is_active, balance, created_at)
                VALUES ({P}, {P}, 'PENDING', 0, 0, {now_sql})
                ON CONFLICT(admin_id, courier_id) DO NOTHING
            """, (admin_id, courier_id))
        else:
            cur.execute(f"""
                INSERT OR IGNORE INTO admin_couriers (admin_id, courier_id, status, is_active, balance, created_at)
                VALUES ({P}, {P}, 'PENDING', 0, 0, {now_sql})
            """, (admin_id, courier_id))
    else:
        if DB_ENGINE == "postgres":
            cur.execute(f"""
                INSERT INTO admin_couriers (admin_id, courier_id, status, balance, created_at)
                VALUES ({P}, {P}, 'PENDING', 0, {now_sql})
                ON CONFLICT(admin_id, courier_id) DO NOTHING
            """, (admin_id, courier_id))
        else:
            cur.execute(f"""
                INSERT OR IGNORE INTO admin_couriers (admin_id, courier_id, status, balance, created_at)
                VALUES ({P}, {P}, 'PENDING', 0, {now_sql})
            """, (admin_id, courier_id))
    conn.commit()
    conn.close()
    

def update_ally_status(ally_id: int, status: str, changed_by: str = None):
    """Actualiza el estado de un aliado (PENDING, APPROVED, REJECTED)."""
    status = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT status FROM allies WHERE id = {P}", (ally_id,))
    row_old = cur.fetchone()
    old_status = _row_value(row_old, "status", 0)
    cur.execute(
        f"""
        UPDATE allies
        SET status = {P}
        WHERE id = {P};
        """,
        (status, ally_id),
    )
    if cur.rowcount > 0:
        _audit_status_change(
            cur,
            entity_type="ALLY",
            entity_id=ally_id,
            old_status=old_status,
            new_status=status,
            source="update_ally_status",
            changed_by=changed_by,
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
    lat: float = None,
    lng: float = None,
):
    """Crea una dirección de recogida para un aliado."""
    conn = get_connection()
    cur = conn.cursor()

    if is_default:
        # Si esta será la principal, poner las demás en 0
        cur.execute(
            f"UPDATE ally_locations SET is_default = 0 WHERE ally_id = {P};",
            (ally_id,),
        )

    location_id = _insert_returning_id(cur, f"""
        INSERT INTO ally_locations (
            ally_id, label, address, city, barrio, phone, is_default, lat, lng
        ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P});
    """, (ally_id, label, address, city, barrio, phone, 1 if is_default else 0, lat, lng))

    conn.commit()
    conn.close()
    return location_id


def get_ally_locations(ally_id: int):
    """Devuelve todas las direcciones de un aliado ordenadas por prioridad.

    Orden: is_default DESC, is_frequent DESC, use_count DESC, id ASC
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, ally_id, label, address, city, barrio, phone, is_default, created_at,
               lat, lng, use_count, is_frequent, last_used_at
        FROM ally_locations
        WHERE ally_id = {P}
        ORDER BY is_default DESC, is_frequent DESC, use_count DESC, id ASC;
    """, (ally_id,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "ally_id": row[1],
            "label": row[2],
            "address": row[3],
            "city": row[4],
            "barrio": row[5],
            "phone": row[6],
            "is_default": row[7],
            "created_at": row[8],
            "lat": row[9],
            "lng": row[10],
            "use_count": row[11] or 0,
            "is_frequent": row[12] or 0,
            "last_used_at": row[13],
        }
        for row in rows
    ]


# Alias para claridad semántica
get_ally_pickups = get_ally_locations


def get_default_ally_location(ally_id: int):
    """Devuelve la dirección principal de un aliado como dict (o None)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, ally_id, label, address, city, barrio, phone, is_default, created_at,
               lat, lng, use_count, is_frequent, last_used_at
        FROM ally_locations
        WHERE ally_id = {P} AND is_default = 1
        ORDER BY id ASC
        LIMIT 1;
    """, (ally_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "ally_id": row[1],
        "label": row[2],
        "address": row[3],
        "city": row[4],
        "barrio": row[5],
        "phone": row[6],
        "is_default": row[7],
        "created_at": row[8],
        "lat": row[9],
        "lng": row[10],
        "use_count": row[11] or 0,
        "is_frequent": row[12] or 0,
        "last_used_at": row[13],
    }


def set_default_ally_location(location_id: int, ally_id: int):
    """Marca una dirección como principal para ese aliado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE ally_locations SET is_default = 0 WHERE ally_id = {P};",
        (ally_id,),
    )
    cur.execute(
        f"UPDATE ally_locations SET is_default = 1 WHERE id = {P} AND ally_id = {P};",
        (location_id, ally_id),
    )
    conn.commit()
    conn.close()


def get_ally_location_by_id(location_id: int, ally_id: int):
    """Devuelve una dirección específica de un aliado como dict (o None)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, ally_id, label, address, city, barrio, phone, is_default, created_at,
               lat, lng, use_count, is_frequent, last_used_at
        FROM ally_locations
        WHERE id = {P} AND ally_id = {P}
        LIMIT 1;
    """, (location_id, ally_id))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "ally_id": row[1],
        "label": row[2],
        "address": row[3],
        "city": row[4],
        "barrio": row[5],
        "phone": row[6],
        "is_default": row[7],
        "created_at": row[8],
        "lat": row[9],
        "lng": row[10],
        "use_count": row[11] or 0,
        "is_frequent": row[12] or 0,
        "last_used_at": row[13],
    }


def update_ally_location(location_id: int, address: str, city: str, barrio: str, phone: str = None):
    """Actualiza los datos de una dirección."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_locations
        SET address = {P}, city = {P}, barrio = {P}, phone = {P}
        WHERE id = {P};
    """, (address, city, barrio, phone, location_id))
    conn.commit()
    conn.close()


def delete_ally_location(location_id: int, ally_id: int):
    """Elimina una dirección de un aliado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"DELETE FROM ally_locations WHERE id = {P} AND ally_id = {P};",
        (location_id, ally_id),
    )
    conn.commit()
    conn.close()


def update_ally_location_coords(location_id: int, lat: float, lng: float):
    """Actualiza las coordenadas de una dirección de aliado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE ally_locations SET lat = {P}, lng = {P} WHERE id = {P};",
        (lat, lng, location_id),
    )
    conn.commit()
    conn.close()


def increment_pickup_usage(location_id: int, ally_id: int):
    """Incrementa use_count y actualiza last_used_at para una pickup."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_locations
        SET use_count = COALESCE(use_count, 0) + 1,
            last_used_at = datetime('now')
        WHERE id = {P} AND ally_id = {P};
    """, (location_id, ally_id))
    conn.commit()
    conn.close()


def set_frequent_pickup(location_id: int, ally_id: int, is_frequent: bool):
    """Marca o desmarca una pickup como frecuente."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_locations
        SET is_frequent = {P}
        WHERE id = {P} AND ally_id = {P};
    """, (1 if is_frequent else 0, location_id, ally_id))
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
    requires_cash: bool = False,
    cash_required_amount: int = 0,
    pickup_lat: float = None,
    pickup_lng: float = None,
    dropoff_lat: float = None,
    dropoff_lng: float = None,
    quote_source: str = None,
    ally_admin_id_snapshot: int = None,
):
    """Crea un pedido en estado PENDING y devuelve su id."""
    conn = get_connection()
    cur = conn.cursor()
    order_id = _insert_returning_id(cur, f"""
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
            instructions,
            requires_cash,
            cash_required_amount,
            pickup_lat,
            pickup_lng,
            dropoff_lat,
            dropoff_lng,
            quote_source,
            ally_admin_id_snapshot,
            courier_admin_id_snapshot
        ) VALUES ({P}, NULL, 'PENDING', {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P});
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
        1 if requires_cash else 0,
        cash_required_amount,
        pickup_lat,
        pickup_lng,
        dropoff_lat,
        dropoff_lng,
        quote_source,
        ally_admin_id_snapshot,
        None,
    ))
    conn.commit()
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
        query = f"UPDATE orders SET status = {P}, {timestamp_field} = datetime('now') WHERE id = {P};"
        cur.execute(query, (status, order_id))
    else:
        cur.execute(f"UPDATE orders SET status = {P} WHERE id = {P};", (status, order_id))

    conn.commit()
    conn.close()


def assign_order_to_courier(order_id: int, courier_id: int, courier_admin_id_snapshot: int = None):
    """Asigna un pedido a un repartidor y marca accepted_at."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE orders
        SET courier_id = {P}, status = 'ACCEPTED', accepted_at = datetime('now'),
            courier_admin_id_snapshot = {P}
        WHERE id = {P};
    """, (courier_id, courier_admin_id_snapshot, order_id))
    conn.commit()
    conn.close()


def get_order_by_id(order_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT *
        FROM orders
        WHERE id = {P};
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_orders_by_ally(ally_id: int, limit: int = 50):
    """Devuelve los últimos pedidos de un aliado (para historial)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT *
        FROM orders
        WHERE ally_id = {P}
        ORDER BY id DESC
        LIMIT {P};
    """, (ally_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_orders_by_courier(courier_id: int, limit: int = 50):
    """Devuelve los últimos pedidos de un repartidor."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT *
        FROM orders
        WHERE courier_id = {P}
        ORDER BY id DESC
        LIMIT {P};
    """, (courier_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_orders_by_admin_team(admin_id: int, status_filter: str = None, limit: int = 20):
    """
    Devuelve pedidos de aliados vinculados al admin.
    status_filter: 'ACTIVE' (no DELIVERED/CANCELLED), 'DELIVERED', 'CANCELLED', o None (todos).
    """
    conn = get_connection()
    cur = conn.cursor()

    query = f"""
        SELECT o.* FROM orders o
        JOIN admin_allies aa ON aa.ally_id = o.ally_id
        WHERE aa.admin_id = {P} AND aa.status = 'APPROVED'
    """
    params = [admin_id]

    if status_filter == "ACTIVE":
        query += " AND o.status NOT IN ('DELIVERED', 'CANCELLED')"
    elif status_filter == "DELIVERED":
        query += " AND o.status = 'DELIVERED'"
    elif status_filter == "CANCELLED":
        query += " AND o.status = 'CANCELLED'"

    query += f" ORDER BY o.created_at DESC LIMIT {P};"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_orders(status_filter: str = None, limit: int = 20):
    """
    Devuelve todos los pedidos del sistema (para admin plataforma).
    status_filter: 'ACTIVE', 'DELIVERED', 'CANCELLED', o None (todos).
    """
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM orders"
    params = []

    if status_filter == "ACTIVE":
        query += " WHERE status NOT IN ('DELIVERED', 'CANCELLED')"
    elif status_filter == "DELIVERED":
        query += " WHERE status = 'DELIVERED'"
    elif status_filter == "CANCELLED":
        query += " WHERE status = 'CANCELLED'"

    query += f" ORDER BY created_at DESC LIMIT {P};"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- CALIFICACIONES DEL REPARTIDOR ----------

def add_courier_rating(order_id: int, courier_id: int, rating: int, comment: str = None):
    """Registra una calificación para un repartidor."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO courier_ratings (order_id, courier_id, rating, comment)
        VALUES ({P}, {P}, {P}, {P});
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
    residence_address=None,
    residence_lat=None,
    residence_lng=None,
):
    """Crea un repartidor en estado PENDING y devuelve su id."""

    # 1) Identidad global (usa cédula del courier)
    person_id = get_or_create_identity(phone, id_number, full_name=full_name)
    ensure_user_person_id(user_id, person_id)

    conn = get_connection()
    cur = conn.cursor()
    try:
        courier_id = _insert_returning_id(cur, f"""
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
                balance,
                residence_address,
                residence_lat,
                residence_lng
            ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'PENDING', 0, {P}, {P}, {P});
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
            residence_address,
            residence_lat,
            residence_lng,
        ))
        conn.commit()

    except _IntegrityError as e:
        conn.rollback()
        raise ValueError("Ya existe un registro de Repartidor para esta cuenta o identidad.") from e
    finally:
        conn.close()

    add_user_role(user_id, "COURIER")

    return courier_id


def get_courier_by_id(courier_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            id,                -- 0
            user_id,           -- 1
            full_name,         -- 2
            id_number,         -- 3
            phone,             -- 4
            city,              -- 5
            barrio,            -- 6
            plate,             -- 7
            bike_type,         -- 8
            code,              -- 9
            status,            -- 10
            residence_address, -- 11
            residence_lat,     -- 12
            residence_lng,     -- 13
            is_active,         -- 14
            available_cash,    -- 15
            live_lat,          -- 16
            live_lng,          -- 17
            live_location_active, -- 18
            live_location_updated_at, -- 19
            COALESCE(availability_status, 'INACTIVE') AS availability_status -- 20
        FROM couriers
        WHERE id = {P};
    """, (courier_id,))
    row = cur.fetchone()
    conn.close()
    return row

def update_courier_status(courier_id: int, new_status: str, changed_by: str = None):
    """Actualiza el estado de un repartidor (APPROVED / REJECTED)."""
    new_status = normalize_role_status(new_status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT status FROM couriers WHERE id = {P}", (courier_id,))
    row_old = cur.fetchone()
    old_status = _row_value(row_old, "status", 0)
    cur.execute(
        f"UPDATE couriers SET status = {P} WHERE id = {P};",
        (new_status, courier_id),
    )
    if cur.rowcount > 0:
        _audit_status_change(
            cur,
            entity_type="COURIER",
            entity_id=courier_id,
            old_status=old_status,
            new_status=new_status,
            source="update_courier_status",
            changed_by=changed_by,
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
    cur.execute(f"""
        UPDATE couriers
        SET status = 'INACTIVE',
            is_deleted = 1,
            deleted_at = datetime('now')
        WHERE id = {P}
    """, (courier_id,))

    # Desactivar vínculos con admins (no borrar, solo inactivar)
    cur.execute(f"""
        UPDATE admin_couriers
        SET status = 'INACTIVE',
            is_active = 0,
            updated_at = datetime('now')
        WHERE courier_id = {P}
    """, (courier_id,))

    conn.commit()
    conn.close()


def delete_ally(ally_id: int) -> None:
    """Desactiva (soft delete) un aliado sin borrar datos."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        UPDATE allies
        SET status = 'INACTIVE',
            is_deleted = 1,
            created_at = created_at, -- no cambia, solo explícito
            deleted_at = datetime('now')
        WHERE id = {P}
    """, (ally_id,))

    # Desactivar vínculos con admins
    cur.execute(f"""
        UPDATE admin_allies
        SET status = 'INACTIVE',
            is_active = 0,
            updated_at = datetime('now')
        WHERE ally_id = {P}
    """, (ally_id,))

    conn.commit()
    conn.close()


def update_ally(ally_id, business_name, owner_name, phone, address, city, barrio, status):
    status = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE allies
        SET business_name = {P}, owner_name = {P}, phone = {P}, address = {P}, city = {P}, barrio = {P}, status = {P}
        WHERE id = {P}
    """, (business_name, owner_name, phone, address, city, barrio, status, ally_id))
    conn.commit()
    conn.close()


def update_courier(courier_id, full_name, phone, bike_type, status):
    status = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE couriers
        SET full_name = {P}, phone = {P}, bike_type = {P}, status = {P}
        WHERE id = {P}
    """, (full_name, phone, bike_type, status, courier_id))
    conn.commit()
    conn.close()

from datetime import datetime

def create_admin(
    user_id,
    full_name,
    phone,
    city,
    barrio,
    team_name,
    document_number,
    residence_address=None,
    residence_lat=None,
    residence_lng=None,
):
    # 1) Identidad global
    person_id = get_or_create_identity(phone, document_number, full_name=full_name)
    ensure_user_person_id(user_id, person_id)
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"

    conn = get_connection()
    cur = conn.cursor()

    try:
        admin_id = _insert_returning_id(cur, f"""
            INSERT INTO admins (
                user_id, person_id, full_name, phone, city, barrio,
                status, created_at, team_name, document_number,
                residence_address, residence_lat, residence_lng
            )
            VALUES ({P}, {P}, {P}, {P}, {P}, {P}, 'PENDING', {now_sql}, {P}, {P}, {P}, {P}, {P})
        """, (
            user_id,
            person_id,
            full_name,
            normalize_phone(phone),
            city,
            barrio,
            team_name,
            normalize_document(document_number),
            residence_address,
            residence_lat,
            residence_lng,
        ))

        # TEAM_CODE automático y único
        team_code = f"TEAM{admin_id}"
        cur.execute(f"UPDATE admins SET team_code = {P} WHERE id = {P}", (team_code, admin_id))

        conn.commit()

    except _IntegrityError as e:
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
    new_status = normalize_role_status(new_status)
    conn = conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admins
        SET status={P}
        WHERE user_id={P} AND is_deleted=0
    """, (new_status, user_id))
    conn.commit()
    conn.close()


def soft_delete_admin_by_id(admin_id: int):
    conn = conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(f"""
        UPDATE admins
        SET is_deleted=1, deleted_at={P}, status='INACTIVE'
        WHERE id={P}
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
    cur.execute(f"SELECT status FROM admins WHERE id={P} AND is_deleted=0", (admin_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    # row puede ser sqlite3.Row; si ya usas dict(row), ajusta:
    return row["status"] if hasattr(row, "keys") else row[0]


def count_admin_couriers(admin_id: int):
    conn = conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*)
        FROM admin_couriers
        WHERE admin_id={P}
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
    cur.execute(f"""
        SELECT COUNT(*)
        FROM admin_couriers
        WHERE admin_id={P}
          AND balance >= {P}
    """, (admin_id, min_balance))
    n = cur.fetchone()[0]
    conn.close()
    return n


def count_admin_allies(admin_id: int):
    """Cuenta el total de aliados vinculados al admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*)
        FROM admin_allies
        WHERE admin_id = {P}
    """, (admin_id,))
    n = cur.fetchone()[0]
    conn.close()
    return n


def count_admin_allies_with_min_balance(admin_id: int, min_balance: int = 5000):
    """Cuenta aliados del admin con saldo >= min_balance."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*)
        FROM admin_allies
        WHERE admin_id = {P}
          AND balance >= {P}
    """, (admin_id, min_balance))
    n = cur.fetchone()[0]
    conn.close()
    return n


def get_active_terms_version(role: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT version, url, sha256
        FROM terms_versions
        WHERE role = {P} AND is_active = 1
        ORDER BY id DESC
        LIMIT 1
    """, (role,))
    row = cur.fetchone()
    conn.close()
    return row  # (version, url, sha256) o None

def has_accepted_terms(telegram_id: int, role: str, version: str, sha256: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT 1
        FROM terms_acceptances
        WHERE telegram_id = {P} AND role = {P} AND version = {P} AND sha256 = {P}
        LIMIT 1
    """, (telegram_id, role, version, sha256))
    ok = cur.fetchone() is not None
    conn.close()
    return ok

def save_terms_acceptance(telegram_id: int, role: str, version: str, sha256: str, message_id: int = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT OR IGNORE INTO terms_acceptances (telegram_id, role, version, sha256, message_id)
        VALUES ({P}, {P}, {P}, {P}, {P})
    """, (telegram_id, role, version, sha256, message_id))
    conn.commit()
    conn.close()

def save_terms_session_ack(telegram_id: int, role: str, version: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO terms_session_acks (telegram_id, role, version)
        VALUES ({P}, {P}, {P})
    """, (telegram_id, role, version))
    conn.commit()
    conn.close()

def update_admin_courier_status(admin_id, courier_id, status, changed_by: str = None):
    status = normalize_role_status(status)
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT status
        FROM admin_couriers
        WHERE admin_id = {P} AND courier_id = {P}
        LIMIT 1
    """, (admin_id, courier_id))
    row_old = cur.fetchone()
    old_status = _row_value(row_old, "status", 0)
    cur.execute(f"""
        UPDATE admin_couriers
        SET status = {P}, updated_at = {now_sql}
        WHERE admin_id = {P} AND courier_id = {P}
    """, (status, admin_id, courier_id))
    if cur.rowcount > 0:
        _audit_status_change(
            cur,
            entity_type="ADMIN_COURIER_LINK",
            entity_id=courier_id,
            old_status=old_status,
            new_status=status,
            reason=f"admin_id={admin_id}",
            source="update_admin_courier_status",
            changed_by=changed_by,
        )
    conn.commit()
    conn.close()


def set_admin_team_code(admin_id: int, team_code: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admins
        SET team_code = {P}
        WHERE id = {P}
    """, (team_code, admin_id))
    conn.commit()
    conn.close()

def get_available_admins(limit=10, offset=0):
    """
    Lista admins locales disponibles para que un repartidor elija.
    FASE 1: Incluye admins PENDING y APPROVED para permitir migración desde WhatsApp.
    Retorna: [(admin_id, team_name, team_code, city, status), ...]
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT
            id,
            COALESCE(team_name, full_name) AS team_name,
            team_code,
            city,
            status
        FROM admins
        WHERE status IN ('PENDING', 'APPROVED')
          AND is_deleted = 0
          AND team_code IS NOT NULL
          AND TRIM(team_code) != ''
        ORDER BY id ASC
        LIMIT {P} OFFSET {P}
    """, (limit, offset))

    rows = cur.fetchall()
    conn.close()
    return rows


def get_admin_link_for_courier(courier_id: int):
    """
    Obtiene el admin vinculado más reciente a un courier_id.
    Retorna: sqlite3.Row con campos: admin_id, team_name, team_code, link_status
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            a.id AS admin_id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code AS team_code,
            ac.status AS link_status
        FROM admin_couriers ac
        JOIN admins a ON a.id = ac.admin_id
        WHERE ac.courier_id = {P}
          AND a.is_deleted = 0
        ORDER BY ac.created_at DESC
        LIMIT 1;
    """, (courier_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_admin_link_for_ally(ally_id: int):
    """
    Obtiene el admin vinculado más reciente a un ally_id.
    Retorna: sqlite3.Row con campos: admin_id, team_name, team_code, link_status
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            a.id AS admin_id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code AS team_code,
            aa.status AS link_status
        FROM admin_allies aa
        JOIN admins a ON a.id = aa.admin_id
        WHERE aa.ally_id = {P}
          AND a.is_deleted = 0
        ORDER BY aa.created_at DESC
        LIMIT 1;
    """, (ally_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_approved_admin_link_for_courier(courier_id: int):
    """
    Obtiene el admin con vínculo APPROVED más reciente para un courier.
    Retorna: sqlite3.Row con campos: admin_id, team_name, team_code, balance, link_id
    o None si no hay vínculo APPROVED.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            a.id AS admin_id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code AS team_code,
            ac.balance AS balance,
            ac.id AS link_id
        FROM admin_couriers ac
        JOIN admins a ON a.id = ac.admin_id
        WHERE ac.courier_id = {P}
          AND ac.status = 'APPROVED'
          AND a.is_deleted = 0
        ORDER BY ac.created_at DESC
        LIMIT 1;
    """, (courier_id,))
    row = cur.fetchone()
    conn.close()
    return row


def get_approved_admin_link_for_ally(ally_id: int):
    """
    Obtiene el admin con vínculo APPROVED más reciente para un aliado.
    Retorna: sqlite3.Row con campos: admin_id, team_name, team_code, balance, link_id
    o None si no hay vínculo APPROVED.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            a.id AS admin_id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code AS team_code,
            aa.balance AS balance,
            aa.id AS link_id
        FROM admin_allies aa
        JOIN admins a ON a.id = aa.admin_id
        WHERE aa.ally_id = {P}
          AND aa.status = 'APPROVED'
          AND a.is_deleted = 0
        ORDER BY aa.created_at DESC
        LIMIT 1;
    """, (ally_id,))
    row = cur.fetchone()
    conn.close()
    return row


def ensure_platform_temp_coverage_for_ally(ally_id: int):
    """
    Cobertura temporal:
    - Asegura vínculo APPROVED del aliado con plataforma.
    - Replica vínculo APPROVED en plataforma para couriers del admin actual del aliado.
    Retorna: (ok: bool, message: str, migrated_couriers: int)
    """
    platform = get_platform_admin()
    if not platform:
        return False, "No existe admin plataforma activo.", 0

    platform_admin_id = platform["id"] if isinstance(platform, dict) else platform[0]
    current_link = get_admin_link_for_ally(ally_id)
    if not current_link:
        return False, "El aliado no tiene vinculo de administracion para cobertura temporal.", 0

    source_admin_id = current_link["admin_id"] if "admin_id" in current_link.keys() else None
    source_link_status = (current_link["link_status"] or "").upper() if "link_status" in current_link.keys() else ""

    if source_link_status == "APPROVED":
        return False, "El aliado ya tiene un vinculo APPROVED; no requiere cobertura temporal.", 0

    upsert_admin_ally_link(platform_admin_id, ally_id, status="APPROVED")

    migrated = 0
    if source_admin_id and source_admin_id != platform_admin_id:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"""
            SELECT DISTINCT courier_id
            FROM admin_couriers
            WHERE admin_id = {P}
              AND status IN ('APPROVED', 'PENDING')
        """, (source_admin_id,))
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            courier_id = row["courier_id"] if isinstance(row, dict) else row[0]
            if courier_id:
                upsert_admin_courier_link(platform_admin_id, courier_id, status="APPROVED", is_active=1)
                migrated += 1

    return True, "Cobertura temporal plataforma aplicada.", migrated


def get_all_approved_links_for_courier(courier_id: int):
    """
    Devuelve TODOS los vínculos APPROVED de un courier con admins.
    Retorna lista de Row con: admin_id, team_name, team_code, balance, link_id, last_movement_at
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            a.id AS admin_id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code AS team_code,
            ac.balance AS balance,
            ac.id AS link_id,
            ac.updated_at AS last_movement_at
        FROM admin_couriers ac
        JOIN admins a ON a.id = ac.admin_id
        WHERE ac.courier_id = {P}
          AND ac.status = 'APPROVED'
          AND a.is_deleted = 0
        ORDER BY a.team_code ASC;
    """, (courier_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_approved_links_for_ally(ally_id: int):
    """
    Devuelve TODOS los vínculos APPROVED de un aliado con admins.
    Retorna lista de Row con: admin_id, team_name, team_code, balance, link_id, last_movement_at
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            a.id AS admin_id,
            COALESCE(a.team_name, a.full_name) AS team_name,
            a.team_code AS team_code,
            aa.balance AS balance,
            aa.id AS link_id,
            aa.updated_at AS last_movement_at
        FROM admin_allies aa
        JOIN admins a ON a.id = aa.admin_id
        WHERE aa.ally_id = {P}
          AND aa.status = 'APPROVED'
          AND a.is_deleted = 0
        ORDER BY a.team_code ASC;
    """, (ally_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ============================================================
# CLIENTES RECURRENTES DE ALIADOS (ally_customers)
# ============================================================

def create_ally_customer(ally_id: int, name: str, phone: str, notes: str = None) -> int:
    """
    Crea un cliente recurrente para un aliado.
    Retorna el customer_id creado.
    """
    conn = get_connection()
    cur = conn.cursor()
    customer_id = _insert_returning_id(cur, f"""
        INSERT INTO ally_customers (ally_id, name, phone, notes, status, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, 'ACTIVE', datetime('now'), datetime('now'))
    """, (ally_id, name.strip(), normalize_phone(phone), notes))
    conn.commit()
    conn.close()
    return customer_id


def update_ally_customer(customer_id: int, ally_id: int, name: str, phone: str, notes: str = None) -> bool:
    """
    Actualiza un cliente recurrente (validando ownership por ally_id).
    Retorna True si se actualizó, False si no existe o no pertenece al aliado.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_customers
        SET name = {P}, phone = {P}, notes = {P}, updated_at = datetime('now')
        WHERE id = {P} AND ally_id = {P} AND status = 'ACTIVE'
    """, (name.strip(), normalize_phone(phone), notes, customer_id, ally_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def archive_ally_customer(customer_id: int, ally_id: int) -> bool:
    """
    Archiva (soft delete) un cliente recurrente.
    Retorna True si se archivó, False si no existe o no pertenece al aliado.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_customers
        SET status = 'INACTIVE', updated_at = datetime('now')
        WHERE id = {P} AND ally_id = {P} AND status = 'ACTIVE'
    """, (customer_id, ally_id))
    archived = cur.rowcount > 0
    conn.commit()
    conn.close()
    return archived


def restore_ally_customer(customer_id: int, ally_id: int) -> bool:
    """
    Restaura un cliente archivado.
    Retorna True si se restauró, False si no existe o no pertenece al aliado.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_customers
        SET status = 'ACTIVE', updated_at = datetime('now')
        WHERE id = {P} AND ally_id = {P} AND status = 'INACTIVE'
    """, (customer_id, ally_id))
    restored = cur.rowcount > 0
    conn.commit()
    conn.close()
    return restored


def get_ally_customer_by_id(customer_id: int, ally_id: int = None):
    """
    Obtiene un cliente por ID. Si se pasa ally_id, valida ownership.
    """
    conn = get_connection()
    cur = conn.cursor()
    if ally_id:
        cur.execute(f"""
            SELECT id, ally_id, name, phone, notes, status, created_at, updated_at
            FROM ally_customers
            WHERE id = {P} AND ally_id = {P}
        """, (customer_id, ally_id))
    else:
        cur.execute(f"""
            SELECT id, ally_id, name, phone, notes, status, created_at, updated_at
            FROM ally_customers
            WHERE id = {P}
        """, (customer_id,))
    row = cur.fetchone()
    conn.close()
    return row


def list_ally_customers(ally_id: int, limit: int = 10, include_inactive: bool = False):
    """
    Lista los clientes recurrentes de un aliado (últimos primero).
    """
    conn = get_connection()
    cur = conn.cursor()
    if include_inactive:
        cur.execute(f"""
            SELECT id, ally_id, name, phone, notes, status, created_at, updated_at
            FROM ally_customers
            WHERE ally_id = {P}
            ORDER BY updated_at DESC
            LIMIT {P}
        """, (ally_id, limit))
    else:
        cur.execute(f"""
            SELECT id, ally_id, name, phone, notes, status, created_at, updated_at
            FROM ally_customers
            WHERE ally_id = {P} AND status = 'ACTIVE'
            ORDER BY updated_at DESC
            LIMIT {P}
        """, (ally_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def search_ally_customers(ally_id: int, query: str, limit: int = 10):
    """
    Busca clientes por nombre o teléfono (solo activos).
    """
    conn = get_connection()
    cur = conn.cursor()
    search_term = f"%{query.strip()}%"
    cur.execute(f"""
        SELECT id, ally_id, name, phone, notes, status, created_at, updated_at
        FROM ally_customers
        WHERE ally_id = {P} AND status = 'ACTIVE'
          AND (name LIKE {P} OR phone LIKE {P})
        ORDER BY updated_at DESC
        LIMIT {P}
    """, (ally_id, search_term, search_term, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_ally_customer_by_phone(ally_id: int, phone: str):
    """
    Busca un cliente ACTIVO por telefono exacto (normalizado) dentro del aliado.
    """
    phone_norm = normalize_phone(phone or "")
    if not phone_norm:
        return None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, ally_id, name, phone, notes, status, created_at, updated_at
        FROM ally_customers
        WHERE ally_id = {P} AND status = 'ACTIVE' AND phone = {P}
        LIMIT 1
    """, (ally_id, phone_norm))
    row = cur.fetchone()
    conn.close()
    return row


# ============================================================
# DIRECCIONES DE CLIENTES RECURRENTES (ally_customer_addresses)
# ============================================================

def create_customer_address(
    customer_id: int,
    label: str,
    address_text: str,
    city: str = None,
    barrio: str = None,
    notes: str = None,
    lat: float = None,
    lng: float = None
) -> int:
    """
    Crea una dirección para un cliente recurrente.
    Retorna el address_id creado.
    """
    conn = get_connection()
    cur = conn.cursor()
    address_id = _insert_returning_id(cur, f"""
        INSERT INTO ally_customer_addresses
        (customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'ACTIVE', datetime('now'), datetime('now'))
    """, (customer_id, label, address_text.strip(), city, barrio, notes, lat, lng))
    conn.commit()
    conn.close()
    return address_id


def update_customer_address(
    address_id: int,
    customer_id: int,
    label: str,
    address_text: str,
    city: str = None,
    barrio: str = None,
    notes: str = None,
    lat: float = None,
    lng: float = None
) -> bool:
    """
    Actualiza una dirección (validando ownership por customer_id).
    Retorna True si se actualizó.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_customer_addresses
        SET label = {P}, address_text = {P}, city = {P}, barrio = {P}, notes = {P}, lat = {P}, lng = {P},
            updated_at = datetime('now')
        WHERE id = {P} AND customer_id = {P} AND status = 'ACTIVE'
    """, (label, address_text.strip(), city, barrio, notes, lat, lng, address_id, customer_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def archive_customer_address(address_id: int, customer_id: int) -> bool:
    """
    Archiva (soft delete) una dirección de cliente.
    Retorna True si se archivó.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_customer_addresses
        SET status = 'INACTIVE', updated_at = datetime('now')
        WHERE id = {P} AND customer_id = {P} AND status = 'ACTIVE'
    """, (address_id, customer_id))
    archived = cur.rowcount > 0
    conn.commit()
    conn.close()
    return archived


def restore_customer_address(address_id: int, customer_id: int) -> bool:
    """
    Restaura una dirección archivada.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_customer_addresses
        SET status = 'ACTIVE', updated_at = datetime('now')
        WHERE id = {P} AND customer_id = {P} AND status = 'INACTIVE'
    """, (address_id, customer_id))
    restored = cur.rowcount > 0
    conn.commit()
    conn.close()
    return restored


def get_customer_address_by_id(address_id: int, customer_id: int = None):
    """
    Obtiene una dirección por ID. Si se pasa customer_id, valida ownership.
    """
    conn = get_connection()
    cur = conn.cursor()
    if customer_id:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM ally_customer_addresses
            WHERE id = {P} AND customer_id = {P}
        """, (address_id, customer_id))
    else:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM ally_customer_addresses
            WHERE id = {P}
        """, (address_id,))
    row = cur.fetchone()
    conn.close()
    return row


def list_customer_addresses(customer_id: int, include_inactive: bool = False):
    """
    Lista las direcciones de un cliente recurrente.
    """
    conn = get_connection()
    cur = conn.cursor()
    if include_inactive:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM ally_customer_addresses
            WHERE customer_id = {P}
            ORDER BY created_at DESC
        """, (customer_id,))
    else:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM ally_customer_addresses
            WHERE customer_id = {P} AND status = 'ACTIVE'
            ORDER BY created_at DESC
        """, (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_last_order_by_ally(ally_id: int):
    """
    Obtiene el último pedido creado por un aliado (para repetir pedido).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, customer_name, customer_phone, customer_address, customer_city, customer_barrio
        FROM orders
        WHERE ally_id = {P}
        ORDER BY id DESC
        LIMIT 1
    """, (ally_id,))
    row = cur.fetchone()
    conn.close()
    return row


# ---------- CACHE DE LINKS DE UBICACIÓN ----------

def get_link_cache(raw_link: str):
    """Busca un link en cache. Retorna dict o None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT raw_link, expanded_link, lat, lng, formatted_address, provider, place_id
        FROM map_link_cache WHERE raw_link = {P}
    """, (raw_link,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "raw_link": row[0],
            "expanded_link": row[1],
            "lat": row[2],
            "lng": row[3],
            "formatted_address": row[4],
            "provider": row[5],
            "place_id": row[6],
        }
    return None


def upsert_link_cache(raw_link: str, expanded_link: str = None, lat: float = None, lng: float = None,
                      formatted_address: str = None, provider: str = None, place_id: str = None):
    """Inserta o actualiza un link en cache."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO map_link_cache (raw_link, expanded_link, lat, lng, formatted_address, provider, place_id)
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P})
        ON CONFLICT(raw_link) DO UPDATE SET
          expanded_link = COALESCE(excluded.expanded_link, map_link_cache.expanded_link),
          lat = COALESCE(excluded.lat, map_link_cache.lat),
          lng = COALESCE(excluded.lng, map_link_cache.lng),
          formatted_address = COALESCE(excluded.formatted_address, map_link_cache.formatted_address),
          provider = COALESCE(excluded.provider, map_link_cache.provider),
          place_id = COALESCE(excluded.place_id, map_link_cache.place_id)
    """, (raw_link, expanded_link, lat, lng, formatted_address, provider, place_id))
    conn.commit()
    conn.close()


def get_distance_cache(origin_key: str, destination_key: str, mode: str):
    """Busca distancia cacheada por origen/destino y modo. Retorna dict o None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT distance_km, provider
        FROM map_distance_cache
        WHERE origin_key = {P} AND destination_key = {P} AND mode = {P}
        LIMIT 1
    """, (origin_key, destination_key, mode))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "distance_km": row[0],
        "provider": row[1],
    }


def upsert_distance_cache(origin_key: str, destination_key: str, mode: str, distance_km: float, provider: str):
    """Inserta/actualiza distancia cacheada por origen/destino y modo."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO map_distance_cache (origin_key, destination_key, mode, distance_km, provider, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, {P}, datetime('now'), datetime('now'))
        ON CONFLICT(origin_key, destination_key, mode) DO UPDATE SET
          distance_km = excluded.distance_km,
          provider = COALESCE(excluded.provider, map_distance_cache.provider),
          updated_at = datetime('now')
    """, (origin_key, destination_key, mode, distance_km, provider))
    conn.commit()
    conn.close()


# ---------- API USAGE DAILY (FUSIBLE) ----------

def get_api_usage_today(api_name: str) -> int:
    """Retorna el número de llamadas hoy para una API."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT call_count FROM api_usage_daily
        WHERE api_name = {P} AND usage_date = date('now')
    """, (api_name,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0




def increment_api_usage(api_name: str):
    """Incrementa el contador de uso diario para una API."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO api_usage_daily (api_name, usage_date, call_count)
        VALUES ({P}, date('now'), 1)
        ON CONFLICT(api_name, usage_date) DO UPDATE SET
          call_count = api_usage_daily.call_count + 1
    """, (api_name,))
    conn.commit()
    conn.close()


# ============================================================
# SISTEMA DE RECARGAS (recharge_requests, ledger)
# ============================================================

def get_admin_balance(admin_id: int) -> int:
    """Retorna el saldo actual de un admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT balance FROM admins WHERE id = {P}", (admin_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0




def update_admin_balance_with_ledger(
    admin_id: int,
    delta: int,
    kind: str,
    note: str,
    ref_type: str = None,
    ref_id: int = None,
    from_type: str = None,
    from_id: int = None,
) -> int:
    """
    Actualiza el saldo de un admin y registra el movimiento en ledger
    en la misma transaccion (atomico).
    amount en ledger siempre es positivo; la direccion se indica con from/to.
    Retorna: ledger_id
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("BEGIN")
    try:
        cur.execute(f"SELECT balance FROM admins WHERE id = {P}", (admin_id,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            raise ValueError(f"Admin id={admin_id} no existe.")
        current_balance = row["balance"] if hasattr(row, "keys") else row[0]
        if current_balance + delta < 0:
            conn.rollback()
            raise ValueError(
                f"Saldo insuficiente en admin id={admin_id}. Balance actual={current_balance}, delta={delta}."
            )
        cur.execute(
            f"UPDATE admins SET balance = balance + {P} WHERE id = {P}",
            (delta, admin_id),
        )
        ledger_id = _insert_returning_id(cur, f"""
            INSERT INTO ledger
                (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
            VALUES ({P}, {P}, {P}, 'ADMIN', {P}, {P}, {P}, {P}, {P})
        """, (kind, from_type, from_id, admin_id, abs(delta), ref_type, ref_id, note))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return ledger_id


def get_courier_link_balance(courier_id: int, admin_id: int) -> int:
    """Retorna el saldo del vínculo courier-admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT balance FROM admin_couriers
        WHERE courier_id = {P} AND admin_id = {P}
    """, (courier_id, admin_id))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def update_courier_link_balance(courier_id: int, admin_id: int, delta: int):
    """Actualiza el saldo del vínculo courier-admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admin_couriers SET balance = balance + {P}, updated_at = datetime('now')
        WHERE courier_id = {P} AND admin_id = {P}
          AND balance + {P} >= 0
    """, (delta, courier_id, admin_id, delta))
    if cur.rowcount != 1:
        conn.rollback()
        conn.close()
        raise ValueError(
            f"No se pudo actualizar saldo de vínculo courier-admin (courier_id={courier_id}, admin_id={admin_id}, delta={delta})."
        )
    conn.commit()
    conn.close()


def get_ally_link_balance(ally_id: int, admin_id: int) -> int:
    """Retorna el saldo del vínculo ally-admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT balance FROM admin_allies
        WHERE ally_id = {P} AND admin_id = {P}
    """, (ally_id, admin_id))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def update_ally_link_balance(ally_id: int, admin_id: int, delta: int):
    """Actualiza el saldo del vínculo ally-admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admin_allies SET balance = balance + {P}, updated_at = datetime('now')
        WHERE ally_id = {P} AND admin_id = {P}
          AND balance + {P} >= 0
    """, (delta, ally_id, admin_id, delta))
    if cur.rowcount != 1:
        conn.rollback()
        conn.close()
        raise ValueError(
            f"No se pudo actualizar saldo de vínculo ally-admin (ally_id={ally_id}, admin_id={admin_id}, delta={delta})."
        )
    conn.commit()
    conn.close()


def exists_pending_recharge_by_proof(proof_file_id: str) -> bool:
    """Retorna True si existe una solicitud PENDING con el mismo comprobante."""
    if not proof_file_id:
        return False
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT 1 FROM recharge_requests
        WHERE proof_file_id = {P} AND status = 'PENDING'
        LIMIT 1
    """, (proof_file_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def create_recharge_request(target_type: str, target_id: int, admin_id: int,
                            amount: int, requested_by_user_id: int,
                            method: str = None, note: str = None,
                            proof_file_id: str = None) -> int:
    """
    Crea una solicitud de recarga PENDING.
    target_type: 'COURIER' o 'ALLY'
    Retorna: request_id
    """
    if exists_pending_recharge_by_proof(proof_file_id):
        return None
    conn = get_connection()
    cur = conn.cursor()
    request_id = _insert_returning_id(cur, f"""
        INSERT INTO recharge_requests
            (target_type, target_id, admin_id, amount, status, requested_by_user_id, method, note, proof_file_id)
        VALUES ({P}, {P}, {P}, {P}, 'PENDING', {P}, {P}, {P}, {P})
    """, (target_type, target_id, admin_id, amount, requested_by_user_id, method, note, proof_file_id))
    conn.commit()
    conn.close()
    return request_id


def get_recharge_request(request_id: int):
    """Obtiene una solicitud de recarga por ID (dict homogéneo)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, target_type, target_id, admin_id, amount, status,
               requested_by_user_id, decided_by_admin_id, method, note,
               created_at, decided_at, proof_file_id
        FROM recharge_requests WHERE id = {P}
    """, (request_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    if hasattr(row, "keys"):
        return {k: row[k] for k in row.keys()}
    return {
        "id": row[0],
        "target_type": row[1],
        "target_id": row[2],
        "admin_id": row[3],
        "amount": row[4],
        "status": row[5],
        "requested_by_user_id": row[6],
        "decided_by_admin_id": row[7],
        "method": row[8],
        "note": row[9],
        "created_at": row[10],
        "decided_at": row[11],
        "proof_file_id": row[12],
    }


def list_pending_recharges_for_admin(admin_id: int):
    """Lista las solicitudes PENDING asignadas a un admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT rr.id, rr.target_type, rr.target_id, rr.amount, rr.method, rr.note, rr.created_at,
               CASE
                   WHEN rr.target_type = 'COURIER' THEN c.full_name
                   WHEN rr.target_type = 'ALLY' THEN al.business_name
                   ELSE 'Desconocido'
               END AS target_name,
               rr.proof_file_id
        FROM recharge_requests rr
        LEFT JOIN couriers c ON rr.target_type = 'COURIER' AND rr.target_id = c.id
        LEFT JOIN allies al ON rr.target_type = 'ALLY' AND rr.target_id = al.id
        WHERE rr.admin_id = {P} AND rr.status = 'PENDING'
        ORDER BY rr.created_at ASC
    """, (admin_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_recharge_status(request_id: int, status: str, decided_by_admin_id: int):
    """Actualiza el status de una solicitud (APPROVED/REJECTED)."""
    status = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE recharge_requests
        SET status = {P}, decided_by_admin_id = {P}, decided_at = datetime('now')
        WHERE id = {P}
    """, (status, decided_by_admin_id, request_id))
    conn.commit()
    conn.close()


def insert_ledger_entry(kind: str, from_type: str, from_id: int, to_type: str, to_id: int,
                        amount: int, ref_type: str = None, ref_id: int = None, note: str = None) -> int:
    """
    Inserta un movimiento en el ledger.
    kind: RECHARGE, FEE, ADJUST
    Retorna: ledger_id
    """
    conn = get_connection()
    cur = conn.cursor()
    ledger_id = _insert_returning_id(cur, f"""
        INSERT INTO ledger (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P})
    """, (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note))
    conn.commit()
    conn.close()
    return ledger_id


def get_platform_admin():
    """Obtiene el admin de plataforma (team_code='PLATFORM')."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_id, full_name, team_name, team_code, balance
        FROM admins
        WHERE team_code = 'PLATFORM' AND is_deleted = 0
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()
    return row


# ============================================================
# DATOS DE PAGO DE ADMINS
# ============================================================

def get_admin_payment_info(admin_id: int):
    """
    Obtiene los datos de pago de un admin.
    Retorna dict con: payment_phone, payment_bank, payment_holder, payment_instructions
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT payment_phone, payment_bank, payment_holder, payment_instructions
        FROM admins WHERE id = {P}
    """, (admin_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "payment_phone": row[0],
            "payment_bank": row[1],
            "payment_holder": row[2],
            "payment_instructions": row[3]
        }
    return None


def update_admin_payment_info(admin_id: int, payment_phone: str = None, payment_bank: str = None,
                               payment_holder: str = None, payment_instructions: str = None):
    """
    Actualiza los datos de pago de un admin.
    Solo actualiza los campos que no son None.
    """
    conn = get_connection()
    cur = conn.cursor()

    updates = []
    params = []

    if payment_phone is not None:
        updates.append(f"payment_phone = {P}")
        params.append(payment_phone)
    if payment_bank is not None:
        updates.append(f"payment_bank = {P}")
        params.append(payment_bank)
    if payment_holder is not None:
        updates.append(f"payment_holder = {P}")
        params.append(payment_holder)
    if payment_instructions is not None:
        updates.append(f"payment_instructions = {P}")
        params.append(payment_instructions)

    if updates:
        params.append(admin_id)
        cur.execute(f"""
            UPDATE admins SET {', '.join(updates)} WHERE id = {P}
        """, params)
        conn.commit()

    conn.close()


def update_recharge_proof(request_id: int, proof_file_id: str):
    """Actualiza el comprobante de una solicitud de recarga."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE recharge_requests SET proof_file_id = {P} WHERE id = {P}
    """, (proof_file_id, request_id))
    conn.commit()
    conn.close()


# ============================================================
# METODOS DE PAGO DE ADMINS (admin_payment_methods)
# ============================================================

def create_payment_method(admin_id: int, method_name: str, account_number: str,
                          account_holder: str, instructions: str = None) -> int:
    """
    Crea un nuevo metodo de pago para un admin.
    Retorna el ID del metodo creado.
    """
    conn = get_connection()
    cur = conn.cursor()
    method_id = _insert_returning_id(cur, f"""
        INSERT INTO admin_payment_methods
            (admin_id, method_name, account_number, account_holder, instructions, is_active)
        VALUES ({P}, {P}, {P}, {P}, {P}, 1)
    """, (admin_id, method_name.strip(), account_number.strip(), account_holder.strip(), instructions))
    conn.commit()
    conn.close()
    return method_id


def get_payment_method_by_id(method_id: int):
    """Obtiene un metodo de pago por ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, admin_id, method_name, account_number, account_holder, instructions, is_active, created_at
        FROM admin_payment_methods WHERE id = {P}
    """, (method_id,))
    row = cur.fetchone()
    conn.close()
    return row


def list_payment_methods(admin_id: int, only_active: bool = False):
    """
    Lista los metodos de pago de un admin.
    Si only_active=True, solo retorna los activos.
    """
    conn = get_connection()
    cur = conn.cursor()
    if only_active:
        cur.execute(f"""
            SELECT id, admin_id, method_name, account_number, account_holder, instructions, is_active, created_at
            FROM admin_payment_methods
            WHERE admin_id = {P} AND is_active = 1
            ORDER BY created_at DESC
        """, (admin_id,))
    else:
        cur.execute(f"""
            SELECT id, admin_id, method_name, account_number, account_holder, instructions, is_active, created_at
            FROM admin_payment_methods
            WHERE admin_id = {P}
            ORDER BY is_active DESC, created_at DESC
        """, (admin_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def toggle_payment_method(method_id: int, is_active: int):
    """Activa o desactiva un metodo de pago."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admin_payment_methods SET is_active = {P} WHERE id = {P}
    """, (is_active, method_id))
    conn.commit()
    conn.close()


def deactivate_payment_method(method_id: int):
    """Desactiva un metodo de pago (sin borrado fisico)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admin_payment_methods
        SET is_active = 0
        WHERE id = {P}
    """, (method_id,))
    conn.commit()
    conn.close()


# ============================================================
# SOLICITUDES DE CAMBIO DE PERFIL
# ============================================================

def create_profile_change_request(
    requester_user_id,
    target_role,
    target_role_id,
    field_name,
    old_value,
    new_value,
    new_lat,
    new_lng,
    team_admin_id,
    team_code,
):
    conn = get_connection()
    cur = conn.cursor()
    req_id = _insert_returning_id(cur, f"""
        INSERT INTO profile_change_requests (
            requester_user_id,
            target_role,
            target_role_id,
            field_name,
            old_value,
            new_value,
            new_lat,
            new_lng,
            status,
            team_admin_id,
            team_code,
            created_at
        ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'PENDING', {P}, {P}, datetime('now'));
    """, (
        requester_user_id,
        target_role,
        target_role_id,
        field_name,
        old_value,
        new_value,
        new_lat,
        new_lng,
        team_admin_id,
        team_code,
    ))
    conn.commit()
    conn.close()
    return req_id


def has_pending_profile_change_request(requester_user_id, target_role, target_role_id, field_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*) AS total
        FROM profile_change_requests
        WHERE status = 'PENDING'
          AND requester_user_id = {P}
          AND target_role = {P}
          AND target_role_id = {P}
          AND field_name = {P}
    """, (requester_user_id, target_role, target_role_id, field_name))
    row = cur.fetchone()
    conn.close()
    return (row["total"] if row else 0) > 0


def list_pending_profile_change_requests(is_platform: bool, admin_id: int):
    conn = get_connection()
    cur = conn.cursor()
    if is_platform:
        cur.execute("""
            SELECT * FROM profile_change_requests
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
        """)
    else:
        cur.execute(f"""
            SELECT * FROM profile_change_requests
            WHERE status = 'PENDING'
              AND team_admin_id = {P}
              AND (team_code IS NULL OR team_code != 'PLATFORM')
            ORDER BY created_at ASC
        """, (admin_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_profile_change_request_by_id(request_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT * FROM profile_change_requests WHERE id = {P}
    """, (request_id,))
    row = cur.fetchone()
    conn.close()
    return row


def mark_profile_change_request_approved(request_id, reviewer_user_id, reviewer_admin_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE profile_change_requests
        SET status = 'APPROVED',
            reviewed_by_user_id = {P},
            reviewed_by_admin_id = {P},
            reviewed_at = datetime('now')
        WHERE id = {P}
    """, (reviewer_user_id, reviewer_admin_id, request_id))
    conn.commit()
    conn.close()


def mark_profile_change_request_rejected(request_id, reviewer_user_id, reviewer_admin_id, reason):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE profile_change_requests
        SET status = 'REJECTED',
            reviewed_by_user_id = {P},
            reviewed_by_admin_id = {P},
            reviewed_at = datetime('now'),
            rejection_reason = {P}
        WHERE id = {P}
    """, (reviewer_user_id, reviewer_admin_id, reason, request_id))
    conn.commit()
    conn.close()


