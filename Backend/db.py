import sqlite3
import os
import re
import json
import time
import logging
import uuid
from typing import Tuple
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

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


def has_valid_coords(lat, lng) -> bool:
    """Valida que lat/lng existan y esten en rangos geograficos validos."""
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return False
    return -90 <= lat_f <= 90 and -180 <= lng_f <= 180


# ----------------- Helpers multi-motor -----------------

def _insert_returning_id(cur, sql, params=()):
    """INSERT y devuelve el id generado. Usa RETURNING id en Postgres."""
    if DB_ENGINE == "postgres":
        sql_s = sql.rstrip().rstrip(';')
        cur.execute(sql_s + ' RETURNING id', params)
        return cur.fetchone()["id"]
    cur.execute(sql, params)
    return cur.lastrowid


def _sync_ally_link_status(cur, ally_id: int, status: str, now_sql: str):
    """Sincroniza admin_allies.status con el nuevo estado del aliado."""
    if status == "APPROVED":
        cur.execute(
            f"SELECT id FROM admin_allies WHERE ally_id = {P} ORDER BY updated_at DESC LIMIT 1",
            (ally_id,),
        )
        link_row = cur.fetchone()
        if link_row:
            link_id = _row_value(link_row, "id", 0)
            cur.execute(
                f"UPDATE admin_allies SET status = 'APPROVED', updated_at = {now_sql} WHERE id = {P}",
                (link_id,),
            )
            cur.execute(
                f"UPDATE admin_allies SET status = 'INACTIVE', updated_at = {now_sql}"
                f" WHERE ally_id = {P} AND id != {P}",
                (ally_id, link_id),
            )
    else:
        cur.execute(
            f"UPDATE admin_allies SET status = 'INACTIVE', updated_at = {now_sql} WHERE ally_id = {P}",
            (ally_id,),
        )


def _sync_courier_link_status(cur, courier_id: int, status: str, now_sql: str):
    """Sincroniza admin_couriers.status con el nuevo estado del repartidor."""
    if status == "APPROVED":
        cur.execute(
            f"SELECT id FROM admin_couriers WHERE courier_id = {P} ORDER BY updated_at DESC LIMIT 1",
            (courier_id,),
        )
        link_row = cur.fetchone()
        if link_row:
            link_id = _row_value(link_row, "id", 0)
            cur.execute(
                f"UPDATE admin_couriers SET status = 'APPROVED', updated_at = {now_sql} WHERE id = {P}",
                (link_id,),
            )
            cur.execute(
                f"UPDATE admin_couriers SET status = 'INACTIVE', updated_at = {now_sql}"
                f" WHERE courier_id = {P} AND id != {P}",
                (courier_id, link_id),
            )
    else:
        cur.execute(
            f"UPDATE admin_couriers SET status = 'INACTIVE', updated_at = {now_sql} WHERE courier_id = {P}",
            (courier_id,),
        )


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
            return _row_value(conflict, "id", 0)

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
    except _IntegrityError:
        # Race condition: otro proceso insertó la misma identidad concurrentemente.
        # Releer determinísticamente en lugar de fallar.
        conn.rollback()
        cur.execute(f"SELECT id FROM identities WHERE phone = {P} LIMIT 1", (phone_n,))
        row_retry = cur.fetchone()
        conn.close()
        if row_retry:
            return _row_value(row_retry, "id", 0)
        raise ValueError("Error al crear identidad: conflicto de unicidad no recuperable.")


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
        logger.error(
            "[AUDIT] status_audit_log falló: entity_type=%s entity_id=%s %s→%s source=%s changed_by=%s error=%s",
            entity_type, entity_id, old_status, new_status, source, changed_by, e,
        )


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
        CREATE TABLE IF NOT EXISTS api_usage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT NOT NULL,
            api_operation TEXT NOT NULL,
            usage_date TEXT NOT NULL,
            success INTEGER DEFAULT 1,
            blocked INTEGER DEFAULT 0,
            units INTEGER DEFAULT 1,
            units_kind TEXT DEFAULT 'call',
            cost_usd REAL DEFAULT 0,
            http_status INTEGER,
            provider_status TEXT,
            error_message TEXT,
            meta_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_events_api_date ON api_usage_events(api_name, usage_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_api_usage_events_api_op_date ON api_usage_events(api_name, api_operation, usage_date)")

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
        CREATE TABLE IF NOT EXISTS geocoding_text_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text_key TEXT NOT NULL UNIQUE,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            formatted_address TEXT,
            place_id TEXT,
            source TEXT,
            hit_count INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_geocoding_text_cache_key ON geocoding_text_cache(text_key)")

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS registration_reset_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_type TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            person_id INTEGER,
            user_id INTEGER,
            previous_status TEXT,
            previous_payload_json TEXT NOT NULL,
            reset_note TEXT,
            authorized_by_admin_id INTEGER,
            authorized_at TEXT,
            consumed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_registration_reset_audit_role ON registration_reset_audit(role_type, role_id)")

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
    if "registration_reset_enabled_at" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN registration_reset_enabled_at TEXT")
    if "registration_reset_by_admin_id" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN registration_reset_by_admin_id INTEGER")
    if "registration_reset_note" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN registration_reset_note TEXT")
    if "registration_reset_consumed_at" not in admins_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN registration_reset_consumed_at TEXT")

    # allies: rejection_type, rejection_reason, rejected_at
    cur.execute("PRAGMA table_info(allies)")
    allies_cols = [r[1] for r in cur.fetchall()]
    if "rejection_type" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN rejection_type TEXT")
    if "rejection_reason" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN rejection_reason TEXT")
    if "rejected_at" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN rejected_at TEXT")
    if "registration_reset_enabled_at" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN registration_reset_enabled_at TEXT")
    if "registration_reset_by_admin_id" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN registration_reset_by_admin_id INTEGER")
    if "registration_reset_note" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN registration_reset_note TEXT")
    if "registration_reset_consumed_at" not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN registration_reset_consumed_at TEXT")

    # couriers: rejection_type, rejection_reason, rejected_at
    cur.execute("PRAGMA table_info(couriers)")
    couriers_cols = [r[1] for r in cur.fetchall()]
    if "rejection_type" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN rejection_type TEXT")
    if "rejection_reason" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN rejection_reason TEXT")
    if "rejected_at" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN rejected_at TEXT")
    if "registration_reset_enabled_at" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN registration_reset_enabled_at TEXT")
    if "registration_reset_by_admin_id" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN registration_reset_by_admin_id INTEGER")
    if "registration_reset_note" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN registration_reset_note TEXT")
    if "registration_reset_consumed_at" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN registration_reset_consumed_at TEXT")
    if "cedula_front_file_id" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN cedula_front_file_id TEXT")
    if "cedula_back_file_id" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN cedula_back_file_id TEXT")
    if "selfie_file_id" not in couriers_cols:
        cur.execute("ALTER TABLE couriers ADD COLUMN selfie_file_id TEXT")

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

    # Tabla: admin_locations (direcciones de recogida del admin)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            barrio TEXT NOT NULL,
            phone TEXT,
            lat REAL,
            lng REAL,
            is_default INTEGER DEFAULT 0,
            use_count INTEGER DEFAULT 0,
            is_frequent INTEGER DEFAULT 0,
            last_used_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (admin_id) REFERENCES admins(id)
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

    # Tabla: ally_subscriptions (suscripciones mensuales de aliados)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ally_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            platform_share INTEGER NOT NULL,
            admin_share INTEGER NOT NULL,
            starts_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ally_id) REFERENCES allies(id),
            FOREIGN KEY (admin_id) REFERENCES admins(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ally_subscriptions_ally ON ally_subscriptions(ally_id, status)")

    # admin_allies: columnas de migracion
    cur.execute("PRAGMA table_info(admin_allies)")
    admin_allies_cols = [r[1] for r in cur.fetchall()]
    if "subscription_price" not in admin_allies_cols:
        cur.execute("ALTER TABLE admin_allies ADD COLUMN subscription_price INTEGER DEFAULT NULL")

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
            ally_id INTEGER,
            creator_admin_id INTEGER,
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
            buy_surcharge INTEGER DEFAULT 0,
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

    # H) TABLAS PARA AGENDA DEL ADMIN (admin_customers)
    # ============================================================

    # Tabla: admin_customers (clientes recurrentes del admin)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (admin_id) REFERENCES admins(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_customers_admin_id ON admin_customers(admin_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_customers_admin_phone ON admin_customers(admin_id, phone)")

    # Tabla: admin_customer_addresses (direcciones de clientes del admin)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_customer_addresses (
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
            FOREIGN KEY (customer_id) REFERENCES admin_customers(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_customer_addresses_cid ON admin_customer_addresses(customer_id)")

    # Tabla: ally_form_requests (bandeja temporal de solicitudes desde enlace público del aliado)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ally_form_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            delivery_address TEXT,
            delivery_city TEXT,
            delivery_barrio TEXT,
            notes TEXT,
            lat REAL,
            lng REAL,
            status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ally_id) REFERENCES allies(id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ally_form_requests_ally ON ally_form_requests(ally_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ally_form_requests_status ON ally_form_requests(status)")

    # Tabla: order_support_requests (solicitudes de ayuda por pin mal ubicado)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_support_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            route_id INTEGER,
            route_seq INTEGER,
            courier_id INTEGER NOT NULL,
            admin_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            resolution TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            resolved_at TEXT,
            resolved_by INTEGER
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_order_support_requests_order ON order_support_requests(order_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_order_support_requests_status ON order_support_requests(status)")

    # Migración: agregar campos para base requerida en orders
    cur.execute("PRAGMA table_info(orders)")
    order_columns = [col[1] for col in cur.fetchall()]
    if 'requires_cash' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN requires_cash INTEGER DEFAULT 0")
    if 'cash_required_amount' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN cash_required_amount INTEGER DEFAULT 0")
    if 'payment_method' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'UNCONFIRMED'")
    if 'payment_confirmed_at' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN payment_confirmed_at TEXT DEFAULT NULL")
    if 'payment_confirmed_by' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN payment_confirmed_by INTEGER DEFAULT NULL")
    if 'payment_changed_at' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN payment_changed_at TEXT DEFAULT NULL")
    if 'payment_changed_by' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN payment_changed_by INTEGER DEFAULT NULL")
    if 'payment_prev_method' not in order_columns:
        cur.execute("ALTER TABLE orders ADD COLUMN payment_prev_method TEXT DEFAULT NULL")

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
    if 'buy_surcharge' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN buy_surcharge INTEGER DEFAULT 0")
    if 'ally_admin_id_snapshot' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN ally_admin_id_snapshot INTEGER")
    if 'courier_admin_id_snapshot' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN courier_admin_id_snapshot INTEGER")
    if 'courier_arrived_at' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN courier_arrived_at TEXT")
    if 'courier_accepted_lat' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN courier_accepted_lat REAL")
    if 'courier_accepted_lng' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN courier_accepted_lng REAL")
    if 'creator_admin_id' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN creator_admin_id INTEGER")
    if 'purchase_amount' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN purchase_amount INTEGER DEFAULT NULL")
    if 'delivery_subsidy_applied' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery_subsidy_applied INTEGER DEFAULT 0")
    if 'customer_delivery_fee' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN customer_delivery_fee INTEGER DEFAULT NULL")
    if 'parking_fee' not in order_cols:
        cur.execute("ALTER TABLE orders ADD COLUMN parking_fee INTEGER DEFAULT 0")

    try:
        cur.execute("ALTER TABLE orders ADD COLUMN canceled_by TEXT;")
    except Exception:
        pass

    # Migración: agregar additional_incentive a routes
    try:
        cur.execute("PRAGMA table_info(routes)")
        route_cols = [col[1] for col in cur.fetchall()]
        if 'additional_incentive' not in route_cols:
            cur.execute("ALTER TABLE routes ADD COLUMN additional_incentive INTEGER DEFAULT 0")
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
        cur.execute("ALTER TABLE couriers ADD COLUMN live_location_expires_at TEXT;")
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

    # Migración: agregar status a admin_locations (soft delete)
    cur.execute("PRAGMA table_info(admin_locations)")
    admin_loc_cols = [col[1] for col in cur.fetchall()]
    if 'status' not in admin_loc_cols:
        cur.execute("ALTER TABLE admin_locations ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVE'")

    # Migración: agregar public_token a allies (enlace público del aliado)
    cur.execute("PRAGMA table_info(allies)")
    allies_cols = [col[1] for col in cur.fetchall()]
    if 'public_token' not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN public_token TEXT")

    # Migración: agregar delivery_subsidy a allies
    if 'delivery_subsidy' not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN delivery_subsidy INTEGER DEFAULT 0")

    # Migración: agregar min_purchase_for_subsidy a allies
    if 'min_purchase_for_subsidy' not in allies_cols:
        cur.execute("ALTER TABLE allies ADD COLUMN min_purchase_for_subsidy INTEGER DEFAULT NULL")

    # Migración: agregar columnas de cotización a ally_form_requests
    cur.execute("PRAGMA table_info(ally_form_requests)")
    afr_cols = [col[1] for col in cur.fetchall()]
    if 'quoted_price' not in afr_cols:
        cur.execute("ALTER TABLE ally_form_requests ADD COLUMN quoted_price REAL DEFAULT NULL")
    if 'subsidio_aliado' not in afr_cols:
        cur.execute("ALTER TABLE ally_form_requests ADD COLUMN subsidio_aliado INTEGER DEFAULT 0")
    if 'incentivo_cliente' not in afr_cols:
        cur.execute("ALTER TABLE ally_form_requests ADD COLUMN incentivo_cliente INTEGER DEFAULT 0")
    if 'total_cliente' not in afr_cols:
        cur.execute("ALTER TABLE ally_form_requests ADD COLUMN total_cliente INTEGER DEFAULT NULL")
    if 'order_id' not in afr_cols:
        cur.execute("ALTER TABLE ally_form_requests ADD COLUMN order_id INTEGER DEFAULT NULL")
    if 'purchase_amount_declared' not in afr_cols:
        cur.execute("ALTER TABLE ally_form_requests ADD COLUMN purchase_amount_declared INTEGER DEFAULT NULL")

    # Migración: agregar use_count a ally_customer_addresses (orden por uso)
    cur.execute("PRAGMA table_info(ally_customer_addresses)")
    aca_cols = [col[1] for col in cur.fetchall()]
    if 'use_count' not in aca_cols:
        cur.execute("ALTER TABLE ally_customer_addresses ADD COLUMN use_count INTEGER DEFAULT 0")
    if 'parking_status' not in aca_cols:
        cur.execute("ALTER TABLE ally_customer_addresses ADD COLUMN parking_status TEXT DEFAULT 'NOT_ASKED'")
    if 'parking_reviewed_by' not in aca_cols:
        cur.execute("ALTER TABLE ally_customer_addresses ADD COLUMN parking_reviewed_by INTEGER DEFAULT NULL")
    if 'parking_reviewed_at' not in aca_cols:
        cur.execute("ALTER TABLE ally_customer_addresses ADD COLUMN parking_reviewed_at TEXT DEFAULT NULL")

    # Migración: agregar use_count a admin_customer_addresses (orden por uso)
    cur.execute("PRAGMA table_info(admin_customer_addresses)")
    adca_cols = [col[1] for col in cur.fetchall()]
    if 'use_count' not in adca_cols:
        cur.execute("ALTER TABLE admin_customer_addresses ADD COLUMN use_count INTEGER DEFAULT 0")
    if 'parking_status' not in adca_cols:
        cur.execute("ALTER TABLE admin_customer_addresses ADD COLUMN parking_status TEXT DEFAULT 'NOT_ASKED'")
    if 'parking_reviewed_by' not in adca_cols:
        cur.execute("ALTER TABLE admin_customer_addresses ADD COLUMN parking_reviewed_by INTEGER DEFAULT NULL")
    if 'parking_reviewed_at' not in adca_cols:
        cur.execute("ALTER TABLE admin_customer_addresses ADD COLUMN parking_reviewed_at TEXT DEFAULT NULL")

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

    # Migración: agregar columnas de fotos a admins si no existen
    cur.execute("PRAGMA table_info(admins)")
    admins_photo_cols = [r[1] for r in cur.fetchall()]
    if "cedula_front_file_id" not in admins_photo_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN cedula_front_file_id TEXT")
    if "cedula_back_file_id" not in admins_photo_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN cedula_back_file_id TEXT")
    if "selfie_file_id" not in admins_photo_cols:
        cur.execute("ALTER TABLE admins ADD COLUMN selfie_file_id TEXT")

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS welcome_bonus_grants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_type TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            granted_by_admin_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            ledger_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(role_type, role_id)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_welcome_bonus_role ON welcome_bonus_grants(role_type, role_id)")

    # Tabla: accounting_weeks (cortes semanales)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounting_weeks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_key TEXT NOT NULL UNIQUE,
            week_start_at TEXT NOT NULL,
            week_end_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            closed_at TEXT,
            closed_by TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_weeks_status ON accounting_weeks(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_weeks_start ON accounting_weeks(week_start_at)")

    # Tabla: accounting_events (eventos contables normalizados)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounting_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_key TEXT NOT NULL,
            event_type TEXT NOT NULL,
            from_type TEXT,
            from_id INTEGER,
            to_type TEXT,
            to_id INTEGER,
            entity_type TEXT,
            entity_id INTEGER,
            admin_id INTEGER,
            order_id INTEGER,
            ledger_id INTEGER,
            amount INTEGER NOT NULL CHECK(amount >= 0),
            note TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_events_week ON accounting_events(week_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_events_type ON accounting_events(event_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_events_entity ON accounting_events(entity_type, entity_id)")

    # Tabla: order_accounting_settlements (devengado/cobrado por pedido)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_accounting_settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL UNIQUE,
            week_key TEXT NOT NULL,
            admin_id INTEGER,
            ally_id INTEGER,
            courier_id INTEGER,
            order_total_fee INTEGER NOT NULL DEFAULT 0,
            ally_fee_expected INTEGER NOT NULL DEFAULT 0,
            ally_fee_charged INTEGER NOT NULL DEFAULT 0,
            courier_fee_expected INTEGER NOT NULL DEFAULT 0,
            courier_fee_charged INTEGER NOT NULL DEFAULT 0,
            settlement_status TEXT NOT NULL DEFAULT 'OPEN',
            note TEXT,
            delivered_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_order_accounting_week ON order_accounting_settlements(week_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_order_accounting_courier ON order_accounting_settlements(courier_id, week_key)")

    # Tabla: accounting_week_snapshots (resumen congelado por semana)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounting_week_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_key TEXT NOT NULL,
            scope_type TEXT NOT NULL,
            scope_id INTEGER NOT NULL DEFAULT 0,
            metric_key TEXT NOT NULL,
            metric_value INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(week_key, scope_type, scope_id, metric_key)
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_snapshots_week ON accounting_week_snapshots(week_key)")

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

    # Tablas: rutas multi-parada
    cur.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ally_id INTEGER NOT NULL,
            ally_admin_id_snapshot INTEGER,
            courier_id INTEGER,
            courier_admin_id_snapshot INTEGER,
            status TEXT DEFAULT 'PENDING',
            pickup_location_id INTEGER,
            pickup_address TEXT NOT NULL,
            pickup_lat REAL,
            pickup_lng REAL,
            total_distance_km REAL DEFAULT 0,
            distance_fee INTEGER DEFAULT 0,
            additional_stops_fee INTEGER DEFAULT 0,
            additional_incentive INTEGER DEFAULT 0,
            total_fee INTEGER DEFAULT 0,
            instructions TEXT,
            canceled_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            published_at TEXT,
            accepted_at TEXT,
            delivered_at TEXT,
            canceled_at TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS route_destinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            customer_city TEXT NOT NULL,
            customer_barrio TEXT NOT NULL,
            dropoff_lat REAL,
            dropoff_lng REAL,
            status TEXT DEFAULT 'PENDING',
            delivered_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS route_offer_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            courier_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            status TEXT DEFAULT 'PENDING',
            offered_at TEXT,
            responded_at TEXT,
            response TEXT
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_routes_ally_id ON routes(ally_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_routes_status ON routes(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_route_destinations_route_id ON route_destinations(route_id, sequence)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_route_offer_queue_route_id ON route_offer_queue(route_id, status)")

    # Tabla: web_users (usuarios del panel web con soporte multiusuario)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS web_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'ADMIN_LOCAL',
            status TEXT NOT NULL DEFAULT 'APPROVED',
            admin_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_web_users_username ON web_users(username)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_web_users_status ON web_users(status)")
    # Migración: agregar admin_id a web_users si no existe
    cur.execute("PRAGMA table_info(web_users)")
    _wu_cols = [col[1] for col in cur.fetchall()]
    if "admin_id" not in _wu_cols:
        cur.execute("ALTER TABLE web_users ADD COLUMN admin_id INTEGER")

    # Migración: agregar vehicle_type a couriers (MOTO por defecto para registros previos)
    try:
        cur.execute("ALTER TABLE couriers ADD COLUMN vehicle_type TEXT DEFAULT 'MOTO';")
    except Exception:
        pass

    # Tabla: scheduled_jobs (persistencia de timers del bot)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            job_name TEXT PRIMARY KEY,
            callback_name TEXT NOT NULL,
            fire_at TEXT NOT NULL,
            job_data TEXT DEFAULT '{}',
            status TEXT DEFAULT 'PENDING',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)

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
        ("cedula_front_file_id", "TEXT"),
        ("cedula_back_file_id", "TEXT"),
        ("selfie_file_id", "TEXT"),
        ("registration_reset_enabled_at", "TIMESTAMP"),
        ("registration_reset_by_admin_id", "BIGINT"),
        ("registration_reset_note", "TEXT"),
        ("registration_reset_consumed_at", "TIMESTAMP"),
    ]:
        _pg_add_col("admins", col, ctype)

    # couriers
    for col, ctype in [
        ("available_cash", "INTEGER DEFAULT 0"),
        ("is_active", "INTEGER DEFAULT 0"),
        ("residence_address", "TEXT"),
        ("residence_lat", "REAL"),
        ("residence_lng", "REAL"),
        ("live_location_expires_at", "TIMESTAMP"),
        ("cedula_front_file_id", "TEXT"),
        ("cedula_back_file_id", "TEXT"),
        ("selfie_file_id", "TEXT"),
        ("registration_reset_enabled_at", "TIMESTAMP"),
        ("registration_reset_by_admin_id", "BIGINT"),
        ("registration_reset_note", "TEXT"),
        ("registration_reset_consumed_at", "TIMESTAMP"),
        ("vehicle_type", "TEXT DEFAULT 'MOTO'"),
    ]:
        _pg_add_col("couriers", col, ctype)

    # allies
    for col, ctype in [
        ("public_token", "TEXT"),
        ("delivery_subsidy", "INTEGER DEFAULT 0"),
        ("min_purchase_for_subsidy", "INTEGER DEFAULT NULL"),
        ("registration_reset_enabled_at", "TIMESTAMP"),
        ("registration_reset_by_admin_id", "BIGINT"),
        ("registration_reset_note", "TEXT"),
        ("registration_reset_consumed_at", "TIMESTAMP"),
    ]:
        _pg_add_col("allies", col, ctype)

    # ally_locations
    for col, ctype in [
        ("lat", "REAL"),
        ("lng", "REAL"),
        ("use_count", "INTEGER DEFAULT 0"),
        ("is_frequent", "INTEGER DEFAULT 0"),
        ("last_used_at", "TIMESTAMP"),
    ]:
        _pg_add_col("ally_locations", col, ctype)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS registration_reset_audit (
            id BIGSERIAL PRIMARY KEY,
            role_type TEXT NOT NULL,
            role_id BIGINT NOT NULL,
            person_id BIGINT,
            user_id BIGINT,
            previous_status TEXT,
            previous_payload_json TEXT NOT NULL,
            reset_note TEXT,
            authorized_by_admin_id BIGINT,
            authorized_at TIMESTAMP,
            consumed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_registration_reset_audit_role
        ON registration_reset_audit(role_type, role_id)
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS welcome_bonus_grants (
            id BIGSERIAL PRIMARY KEY,
            role_type TEXT NOT NULL,
            role_id BIGINT NOT NULL,
            granted_by_admin_id BIGINT NOT NULL,
            amount INTEGER NOT NULL,
            ledger_id BIGINT,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(role_type, role_id)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_welcome_bonus_role
        ON welcome_bonus_grants(role_type, role_id)
    """)

    # orders
    for col, ctype in [
        ("requires_cash", "INTEGER DEFAULT 0"),
        ("cash_required_amount", "INTEGER DEFAULT 0"),
        ("pickup_lat", "REAL"),
        ("pickup_lng", "REAL"),
        ("dropoff_lat", "REAL"),
        ("dropoff_lng", "REAL"),
        ("quote_source", "TEXT"),
        ("buy_surcharge", "INTEGER DEFAULT 0"),
        ("ally_admin_id_snapshot", "BIGINT"),
        ("courier_admin_id_snapshot", "BIGINT"),
        ("courier_arrived_at", "TIMESTAMP"),
        ("courier_accepted_lat", "REAL"),
        ("courier_accepted_lng", "REAL"),
        ("canceled_by", "TEXT"),
        ("creator_admin_id", "BIGINT"),
        ("purchase_amount", "INTEGER DEFAULT NULL"),
        ("delivery_subsidy_applied", "INTEGER DEFAULT 0"),
        ("customer_delivery_fee", "INTEGER DEFAULT NULL"),
        ("payment_method", "TEXT DEFAULT 'UNCONFIRMED'"),
        ("payment_confirmed_at", "TIMESTAMP DEFAULT NULL"),
        ("payment_confirmed_by", "BIGINT DEFAULT NULL"),
        ("payment_changed_at", "TIMESTAMP DEFAULT NULL"),
        ("payment_changed_by", "BIGINT DEFAULT NULL"),
        ("payment_prev_method", "TEXT DEFAULT NULL"),
    ]:
        _pg_add_col("orders", col, ctype)

    # ally_id en orders: permite NULL para pedidos creados por admin
    cur.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'orders' AND column_name = 'ally_id' AND is_nullable = 'NO'"
    )
    if cur.fetchone():
        cur.execute("ALTER TABLE orders ALTER COLUMN ally_id DROP NOT NULL")

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

    # admin_locations: agregar status para soft delete
    _pg_add_col("admin_locations", "status", "TEXT NOT NULL DEFAULT 'ACTIVE'")

    # ally_customer_addresses / admin_customer_addresses: use_count para orden por uso
    _pg_add_col("ally_customer_addresses", "use_count", "INTEGER DEFAULT 0")
    _pg_add_col("admin_customer_addresses", "use_count", "INTEGER DEFAULT 0")

    # Parqueadero: estado de revision y columna en orders
    _pg_add_col("ally_customer_addresses", "parking_status", "TEXT DEFAULT 'NOT_ASKED'")
    _pg_add_col("ally_customer_addresses", "parking_reviewed_by", "INTEGER DEFAULT NULL")
    _pg_add_col("ally_customer_addresses", "parking_reviewed_at", "TIMESTAMP")
    _pg_add_col("admin_customer_addresses", "parking_status", "TEXT DEFAULT 'NOT_ASKED'")
    _pg_add_col("admin_customer_addresses", "parking_reviewed_by", "INTEGER DEFAULT NULL")
    _pg_add_col("admin_customer_addresses", "parking_reviewed_at", "TIMESTAMP")
    _pg_add_col("orders", "parking_fee", "INTEGER DEFAULT 0")

    # routes: additional_incentive para incentivos agregados por el aliado
    _pg_add_col("routes", "additional_incentive", "INTEGER DEFAULT 0")

    # web_users: tabla de usuarios del panel web (multiusuario real)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS web_users (
            id BIGSERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'ADMIN_LOCAL',
            status TEXT NOT NULL DEFAULT 'APPROVED',
            admin_id BIGINT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    _pg_add_col("web_users", "admin_id", "BIGINT")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_web_users_username ON web_users(username)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_web_users_status ON web_users(status)")

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
            id,                    -- 0
            user_id,               -- 1
            full_name,             -- 2
            phone,                 -- 3
            city,                  -- 4
            barrio,                -- 5
            team_name,             -- 6
            document_number,       -- 7
            team_code,             -- 8
            status,                -- 9
            created_at,            -- 10
            residence_address,     -- 11
            residence_lat,         -- 12
            residence_lng,         -- 13
            cedula_front_file_id,  -- 14
            cedula_back_file_id,   -- 15
            selfie_file_id         -- 16
        FROM admins
        WHERE id = {P} AND is_deleted = 0
        ORDER BY id DESC
        LIMIT 1
    """, (admin_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


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


def get_courier_telegram_id(courier_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT u.telegram_id
        FROM users u
        JOIN couriers c ON c.user_id = u.id
        WHERE c.id = {P}
        LIMIT 1
    """, (courier_id,))
    row = cur.fetchone()
    conn.close()
    return _row_value(row, "telegram_id", 0) if row else None


def get_ally_telegram_id(ally_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT u.telegram_id
        FROM users u
        JOIN allies a ON a.user_id = u.id
        WHERE a.id = {P}
        LIMIT 1
    """, (ally_id,))
    row = cur.fetchone()
    conn.close()
    return _row_value(row, "telegram_id", 0) if row else None


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


def ensure_platform_sociedad():
    """
    Asegura que exista la entidad contable de la Sociedad en admins (team_code='SOCIEDAD').
    - Usuario sistema con telegram_id=0 (reservado, nunca un Telegram real).
    - Solo puede existir UNA fila SOCIEDAD (UNIQUE en team_code).
    - Idempotente: no modifica si ya existe.
    Retorna el admins.id de la sociedad.
    """
    conn = get_connection()
    cur = conn.cursor()
    NOW = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"

    # 1) Asegurar users fila para el sistema (telegram_id=0)
    cur.execute(f"SELECT id FROM users WHERE telegram_id = 0 LIMIT 1")
    row = cur.fetchone()
    if row:
        system_user_id = _row_value(row, "id", 0)
    else:
        system_user_id = _insert_returning_id(
            cur,
            f"INSERT INTO users (telegram_id, username, role, created_at)"
            f" VALUES (0, 'sociedad_sistema', NULL, {NOW})",
            (),
        )

    # 2) Asegurar admins fila SOCIEDAD
    cur.execute("SELECT id FROM admins WHERE team_code = 'SOCIEDAD' LIMIT 1")
    admin_row = cur.fetchone()
    if admin_row:
        sociedad_id = _row_value(admin_row, "id", 0)
    else:
        sociedad_id = _insert_returning_id(
            cur,
            f"INSERT INTO admins"
            f" (user_id, full_name, phone, city, barrio,"
            f"  status, created_at, team_name, document_number, team_code)"
            f" VALUES ({P},{P},{P},{P},{P},'APPROVED',{NOW},{P},{P},'SOCIEDAD')",
            (
                system_user_id,
                "Sociedad Domiquerendona",
                "+570000000000",
                "SISTEMA",
                "SISTEMA",
                "Domiquerendona Sociedad",
                "SOCIEDAD",
            ),
        )
        # Guardar en settings para lookup rápido
        cur.execute(
            f"INSERT INTO settings (key, value) VALUES ({P},{P})"
            f" ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            ("platform_sociedad_id", str(sociedad_id)),
        ) if DB_ENGINE == "postgres" else cur.execute(
            f"INSERT OR REPLACE INTO settings (key, value) VALUES ({P},{P})",
            ("platform_sociedad_id", str(sociedad_id)),
        )

    conn.commit()
    conn.close()
    logger.info("ensure_platform_sociedad: sociedad_id=%s", sociedad_id)
    return sociedad_id


def get_platform_sociedad_id() -> int:
    """
    Retorna admins.id de la cuenta contable de la Sociedad (team_code='SOCIEDAD').
    Usa settings como cache; fallback a query directa.
    """
    val = get_setting("platform_sociedad_id")
    if val:
        try:
            return int(val)
        except Exception:
            pass
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM admins WHERE team_code = 'SOCIEDAD' AND is_deleted = 0 LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row:
        return _row_value(row, "id", 0)
    return 0


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
        JOIN users u ON u.id = a.user_id
        WHERE a.status = 'APPROVED'
          AND a.is_deleted = 0
          AND a.team_code IS NOT NULL
          AND TRIM(a.team_code) <> ''
          AND u.telegram_id IS NOT NULL
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
    return {row["courier_id"] for row in rows}


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
        "queue_id": row["id"],
        "courier_id": row["courier_id"],
        "position": row["position"],
        "full_name": row["full_name"],
        "telegram_id": row["telegram_id"],
    }


def mark_offer_as_offered(queue_id: int):
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE order_offer_queue
        SET status = 'OFFERED', offered_at = {now_sql}
        WHERE id = {P};
    """, (queue_id,))
    conn.commit()
    conn.close()


def mark_offer_response(queue_id: int, response: str):
    """response: 'ACCEPTED', 'REJECTED', o 'EXPIRED'"""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE order_offer_queue
        SET status = {P}, response = {P}, responded_at = {now_sql}
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
        "queue_id": row["id"],
        "courier_id": row["courier_id"],
        "position": row["position"],
        "telegram_id": row["telegram_id"],
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


def clear_offer_queue(order_id: int):
    """Elimina todos los registros de la cola de ofertas de un pedido para permitir re-oferta completa."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM order_offer_queue WHERE order_id = {P};", (order_id,))
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        INSERT INTO order_pickup_confirmations (
            order_id, courier_id, ally_id, status, requested_at, reviewed_at, reviewed_by_ally_id
        )
        VALUES ({P}, {P}, {P}, {P}, {now_sql}, NULL, NULL)
        ON CONFLICT(order_id)
        DO UPDATE SET
            courier_id=excluded.courier_id,
            ally_id=excluded.ally_id,
            status=excluded.status,
            requested_at={now_sql},
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE order_pickup_confirmations
        SET status = {P},
            reviewed_by_ally_id = {P},
            reviewed_at = {now_sql}
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


def update_courier_live_location(courier_id: int, lat: float, lng: float, live_period_seconds: int = None):
    """Actualiza ubicacion en vivo y mantiene availability_status en estado estandar."""
    retries = 5
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    for attempt in range(retries):
        conn = get_connection()
        try:
            cur = conn.cursor()
            set_clauses = [
                f"live_lat = {P}",
                f"live_lng = {P}",
                "live_location_active = 1",
                f"live_location_updated_at = {now_sql}",
                "availability_status = 'APPROVED'",
            ]
            params = [lat, lng]

            if live_period_seconds is not None:
                try:
                    seconds = int(live_period_seconds)
                except Exception:
                    seconds = None
                if seconds and seconds > 0:
                    if DB_ENGINE == "postgres":
                        set_clauses.append(
                            f"live_location_expires_at = NOW() + ({P} * INTERVAL '1 second')"
                        )
                        params.append(seconds)
                    else:
                        set_clauses.append(
                            f"live_location_expires_at = datetime('now', {P})"
                        )
                        params.append(f"+{seconds} seconds")

            params.append(courier_id)
            cur.execute(
                f"UPDATE couriers SET {', '.join(set_clauses)} WHERE id = {P};",
                tuple(params),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "database is locked" in message and attempt < retries - 1:
                time.sleep(0.15 * (attempt + 1))
                continue
            if "database is locked" in message:
                logger.warning("update_courier_live_location: database is locked tras reintentos")
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


def expire_stale_live_locations(stale_timeout_seconds: int = 900):
    """
    Desactiva completamente couriers con live_location vencida.
    - Regla principal: si live_location_expires_at ya paso.
    - Regla secundaria (fallback): si expires_at IS NULL y no hay updates en stale_timeout_seconds.
      El fallback NO aplica cuando expires_at esta definido y aun es futuro.
    Retorna la lista de courier_ids afectados.
    """
    retries = 5
    if DB_ENGINE == "postgres":
        stale_threshold_sql = f"NOW() - ({P} * INTERVAL '1 second')"
        condition_sql = (
            f"((live_location_expires_at IS NOT NULL AND live_location_expires_at < NOW()) "
            f"OR (live_location_expires_at IS NULL AND "
            f"(live_location_updated_at IS NULL OR live_location_updated_at < {stale_threshold_sql})))"
        )
        condition_params = (stale_timeout_seconds,)
    else:
        condition_sql = (
            f"((live_location_expires_at IS NOT NULL AND live_location_expires_at < datetime('now')) "
            f"OR (live_location_expires_at IS NULL AND "
            f"(live_location_updated_at IS NULL OR live_location_updated_at < datetime('now', {P}))))"
        )
        condition_params = (f"-{stale_timeout_seconds} seconds",)
    for attempt in range(retries):
        conn = get_connection()
        try:
            cur = conn.cursor()

            # Primero obtener los que van a expirar
            cur.execute(f"""
                SELECT id FROM couriers
                WHERE availability_status = 'APPROVED'
                  AND live_location_active = 1
                  AND {condition_sql}
            """, condition_params)
            expired = [row[0] if not isinstance(row, dict) else row["id"] for row in cur.fetchall()]

            if expired:
                cur.execute(f"""
                    UPDATE couriers
                    SET availability_status = 'INACTIVE', live_location_active = 0,
                        is_active = 0, available_cash = 0
                    WHERE availability_status = 'APPROVED'
                      AND live_location_active = 1
                      AND {condition_sql}
                """, condition_params)
                conn.commit()

            return expired
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "database is locked" in message and attempt < retries - 1:
                time.sleep(0.15 * (attempt + 1))
                continue
            if "database is locked" in message:
                logger.warning("expire_stale_live_locations: database is locked tras reintentos")
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
    return row["available_cash"] if row else 0


def get_all_online_couriers():
    """
    Retorna todos los repartidores ONLINE (live_location_active=1) de cualquier equipo.
    Incluye datos de ubicación en vivo, residencia y equipo para calcular distancias.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            c.id AS courier_id,
            c.full_name,
            c.telegram_id,
            c.phone,
            c.live_lat,
            c.live_lng,
            c.live_location_updated_at,
            c.residence_lat,
            c.residence_lng,
            c.available_cash,
            c.availability_status,
            a.city AS admin_city,
            ac.admin_id
        FROM couriers c
        JOIN admin_couriers ac ON ac.courier_id = c.id AND ac.status = 'APPROVED'
        JOIN admins a ON a.id = ac.admin_id
        WHERE c.live_location_active = 1
          AND c.availability_status = 'APPROVED'
          AND c.is_deleted = 0
        ORDER BY c.live_location_updated_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_active_orders_without_courier(limit: int = 20):
    """
    Retorna pedidos activos sin courier asignado, con coordenadas de pickup.
    Usado por el admin de plataforma para buscar repartidores cercanos.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            o.id,
            o.status,
            o.pickup_address,
            o.pickup_lat,
            o.pickup_lng,
            o.customer_name,
            o.created_at,
            al.name AS ally_name
        FROM orders o
        LEFT JOIN allies al ON al.id = o.ally_id
        WHERE o.status NOT IN ('DELIVERED', 'CANCELLED')
          AND (o.courier_id IS NULL OR o.courier_id = 0)
          AND o.pickup_lat IS NOT NULL
          AND o.pickup_lng IS NOT NULL
        ORDER BY o.created_at ASC
        LIMIT {P}
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE orders
        SET status = 'CANCELLED', canceled_at = {now_sql}, canceled_by = {P}
        WHERE id = {P};
    """, (canceled_by, order_id))
    conn.commit()
    conn.close()


def get_order_status_by_id(order_id: int):
    """Retorna el status de un pedido por id, o None si no existe."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT status FROM orders WHERE id = {P} LIMIT 1", (order_id,))
    row = cur.fetchone()
    conn.close()
    return _row_value(row, "status", 0) if row else None


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


def set_courier_arrived(order_id: int):
    """Marca la llegada GPS del courier al punto de recogida. Idempotente."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"UPDATE orders SET courier_arrived_at = {now_sql} WHERE id = {P} AND courier_arrived_at IS NULL;",
        (order_id,),
    )
    conn.commit()
    conn.close()


def set_courier_accepted_location(order_id: int, lat: float, lng: float):
    """Guarda la posición del courier en el momento de aceptar (base para T+5)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE orders SET courier_accepted_lat = {P}, courier_accepted_lng = {P} WHERE id = {P};",
        (lat, lng, order_id),
    )
    conn.commit()
    conn.close()


def get_active_order_for_courier(courier_id: int):
    """Retorna el pedido activo asignado a este courier (ACCEPTED/PICKED_UP), o None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT *
        FROM orders
        WHERE courier_id = {P}
          AND status IN ('ACCEPTED', 'PICKED_UP')
        ORDER BY accepted_at DESC
        LIMIT 1;
        """,
        (courier_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_active_route_for_courier(courier_id: int):
    """Retorna la ruta activa asignada a este courier (ACCEPTED), o None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT *
        FROM routes
        WHERE courier_id = {P}
          AND status = 'ACCEPTED'
        ORDER BY accepted_at DESC
        LIMIT 1;
        """,
        (courier_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_eligible_couriers_for_order(admin_id: int = None, ally_id: int = None,
                                      requires_cash: bool = False,
                                      cash_required_amount: int = 0,
                                      pickup_lat: float = None,
                                      pickup_lng: float = None,
                                      order_distance_km: float = None):
    """
    Devuelve couriers elegibles para un pedido en la red cooperativa.
    Busca TODOS los couriers activos sin restriccion de equipo/admin.
    Cada courier opera bajo su propio admin (cuya comision se cobra por separado).

    Filtros:
    - Vinculo APPROVED con cualquier admin (is_active garantizado por el vinculo)
    - No eliminados
    - is_active = 1 (courier declaro base)
    - live_location_active = 1 (courier compartiendo GPS en vivo)
    - No vetados por el aliado (si ally_id dado)
    - Con base suficiente (si requires_cash)
    - Bicicletas excluidas si order_distance_km > 3.0

    Ordenamiento inteligente:
    1. Por distancia al pickup si hay coordenadas (max 7 km)
    2. Por available_cash DESC como fallback

    admin_id: ignorado (conservado por compatibilidad de llamadas existentes).
    """
    conn = get_connection()
    cur = conn.cursor()

    query = f"""
        SELECT c.id AS courier_id, c.full_name, u.telegram_id, c.available_cash,
               c.availability_status, c.live_lat, c.live_lng, c.live_location_active,
               c.residence_lat, c.residence_lng, c.vehicle_type
        FROM admin_couriers ac
        JOIN couriers c ON c.id = ac.courier_id
        JOIN users u ON u.id = c.user_id
        WHERE ac.status = 'APPROVED'
          AND c.status = 'APPROVED'
          AND (c.is_deleted IS NULL OR c.is_deleted = 0)
          AND c.is_active = 1
          AND c.live_location_active = 1
    """
    params = []

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
                "vehicle_type": row.get("vehicle_type") or "MOTO",
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
                "vehicle_type": row[10] if len(row) > 10 else "MOTO",
            }
        result.append(item)

    # Excluir bicicletas si la distancia del pedido supera 3 km
    if order_distance_km is not None and order_distance_km > 3.0:
        result = [c for c in result if (c.get("vehicle_type") or "MOTO") != "BICICLETA"]

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

        # Filtrar por radio maximo de 7 km desde el punto de recogida.
        # Repartidores sin coordenadas conocidas quedan excluidos del radio.
        MAX_OFFER_RADIUS_KM = 7.0
        within = []
        for c in result:
            clat = c.get("live_lat") or c.get("residence_lat")
            clng = c.get("live_lng") or c.get("residence_lng")
            if clat is not None and clng is not None:
                if _haversine(pickup_lat, pickup_lng, clat, clng) <= MAX_OFFER_RADIUS_KM:
                    within.append(c)
        result = within

    return result


def get_approved_admin_id_for_courier(courier_id: int):
    """Retorna el admin_id del vínculo APPROVED activo del repartidor, o None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT admin_id FROM admin_couriers
        WHERE courier_id = {P} AND status = 'APPROVED'
        ORDER BY updated_at DESC
        LIMIT 1;
    """, (courier_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return int(_row_value(row, "admin_id", 0))


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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_couriers
        SET status='INACTIVE', updated_at={now_sql}
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_allies
        SET status='INACTIVE', updated_at={now_sql}
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


def get_all_local_admins():
    """Lista todos los administradores aprobados (incluye plataforma)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, full_name, city, team_name
        FROM admins
        WHERE status = 'APPROVED'
          AND (is_deleted IS NULL OR is_deleted = 0)
        ORDER BY city, full_name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


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


def sync_all_courier_link_statuses():
    """
    Sincroniza admin_couriers.status para todos los repartidores.
    - APPROVED courier: el vinculo con updated_at mas reciente queda APPROVED, el resto INACTIVE.
    - No-APPROVED courier: todos sus vinculos quedan INACTIVE.
    Idempotente. Se llama al arranque del bot para reparar datos historicos.
    """
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute("SELECT id, status FROM couriers WHERE is_deleted IS NULL OR is_deleted = 0")
    couriers = cur.fetchall()
    fixed = 0
    for c in couriers:
        cid = _row_value(c, "id", 0)
        cstatus = _row_value(c, "status", default="")
        _sync_courier_link_status(cur, cid, cstatus if cstatus == "APPROVED" else "INACTIVE", now_sql)
        fixed += 1
    conn.commit()
    conn.close()
    logger.info("sync_all_courier_link_statuses: %s couriers procesados", fixed)


def ensure_pricing_defaults():
    """
    Inicializa valores por defecto de tarifas de precio en settings.
    Solo inserta si no existen (idempotente).
    """
    defaults = {
        # Tarifas de distancia (pago al courier)
        "pricing_precio_0_2km": "5000",
        "pricing_precio_2_3km": "6000",
        "pricing_tier1_max_km": "1.5",
        "pricing_tier2_max_km": "2.5",
        "pricing_base_distance_km": "2.5",
        "pricing_km_extra_normal": "1200",
        "pricing_umbral_km_largo": "10.0",
        "pricing_km_extra_largo": "1000",
        "pricing_tarifa_parada_adicional": "4000",
        # Fees de servicio (cobro al saldo del miembro por entrega)
        # Invariante: fee_admin_share + fee_platform_share == fee_service_total
        "fee_service_total": "300",
        "fee_admin_share": "200",
        "fee_platform_share": "100",
        # Comision adicional al aliado: % sobre tarifa de domicilio, va 100% a plataforma
        # 0 = desactivado (default). Activar subiendo a 3 (= 3%) cuando el modelo lo requiera.
        "fee_ally_commission_pct": "2",
        # Suscripciones mensuales de aliados
        # Piso minimo que la plataforma recibe por cada suscripcion, independiente del precio total.
        # El admin retiene: precio_total - subscription_platform_share
        "subscription_platform_share": "20000",
    }
    for k, v in defaults.items():
        existing = get_setting(k)
        if existing is None:
            set_setting(k, v)
    tier2_value = get_setting("pricing_tier2_max_km")
    if tier2_value is not None:
        base_distance = get_setting("pricing_base_distance_km")
        if base_distance in (None, "", "3", "3.0", "2", "2.0", "2.5"):
            set_setting("pricing_base_distance_km", tier2_value)
    # Migración: corregir DBs existentes que tenían 200 (fee de servicio, no pago al courier)
    stop_fee = get_setting("pricing_tarifa_parada_adicional")
    if stop_fee in (None, "", "200"):
        set_setting("pricing_tarifa_parada_adicional", "4000")


# ---------- WEB USERS (PANEL WEB MULTIUSUARIO) ----------

def create_web_user(username: str, password_hash: str, role: str = "ADMIN_LOCAL", admin_id: int = None) -> int:
    """Crea un usuario del panel web. Retorna el id generado."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    try:
        new_id = _insert_returning_id(
            cur,
            f"INSERT INTO web_users (username, password_hash, role, status, admin_id, created_at, updated_at)"
            f" VALUES ({P}, {P}, {P}, 'APPROVED', {P}, {now_sql}, {now_sql})",
            (username, password_hash, role, admin_id),
        )
        conn.commit()
        return new_id
    finally:
        conn.close()


def get_web_user_by_username(username: str):
    """Retorna el web_user con ese username o None."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT id, username, password_hash, role, status, admin_id FROM web_users WHERE username = {P}",
            (username,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def get_web_user_by_id(user_id: int):
    """Retorna el web_user con ese id o None."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT id, username, password_hash, role, status, admin_id FROM web_users WHERE id = {P}",
            (user_id,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def list_web_users():
    """Lista todos los usuarios del panel web."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, role, status, created_at FROM web_users ORDER BY id")
        return cur.fetchall()
    finally:
        conn.close()


def update_web_user_status(user_id: int, status: str):
    """Actualiza el status de un web_user."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    try:
        cur.execute(
            f"UPDATE web_users SET status = {P}, updated_at = {now_sql} WHERE id = {P}",
            (status, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_web_user_password(user_id: int, password_hash: str):
    """Actualiza el hash de contraseña de un web_user."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    try:
        cur.execute(
            f"UPDATE web_users SET password_hash = {P}, updated_at = {now_sql} WHERE id = {P}",
            (password_hash, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def ensure_web_admin():
    """
    Seed idempotente: crea el usuario PLATFORM_ADMIN del panel web
    desde WEB_ADMIN_USER / WEB_ADMIN_PASSWORD si no existe aún.
    Usa bcrypt para hashear la contraseña.
    Llamar desde web_app.py al arrancar.
    """
    import bcrypt
    username = os.getenv("WEB_ADMIN_USER", "admin").strip()
    password = os.getenv("WEB_ADMIN_PASSWORD", "changeme").strip()
    existing = get_web_user_by_username(username)
    if existing:
        return
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    create_web_user(username, hashed, role="ADMIN_PLATFORM")
    logger.info("web_user creado: %s (ADMIN_PLATFORM)", username)


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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
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
            last_seen_at = {now_sql},
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE reference_alias_candidates
        SET suggested_lat = {P},
            suggested_lng = {P},
            source = COALESCE({P}, source),
            last_seen_at = {now_sql}
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

    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE reference_alias_candidates
        SET status = {P}, reviewed_by_admin_id = {P}, reviewed_at = {now_sql}, review_note = {P}
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        INSERT INTO admin_reference_validator_permissions
            (admin_id, status, granted_by_admin_id)
        VALUES ({P}, {P}, {P})
        ON CONFLICT(admin_id) DO UPDATE SET
            status = excluded.status,
            granted_by_admin_id = excluded.granted_by_admin_id,
            updated_at = {now_sql}
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
    logger.debug(
        "create_ally() datos: user_id=%s business_name=%r owner_name=%r address=%r city=%r barrio=%r phone=%r document_number=%r",
        user_id, business_name, owner_name, address, city, barrio, phone, document_number,
    )

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
    """Devuelve un aliado por su ID (no eliminado, o None si no existe)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM allies WHERE id = {P} AND (is_deleted IS NULL OR is_deleted = 0) LIMIT 1;",
        (ally_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row

def get_pending_allies():
    """Devuelve todos los aliados con estado PENDING (no eliminados)."""
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
          AND (is_deleted IS NULL OR is_deleted = 0)
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
        WHERE (is_deleted IS NULL OR is_deleted = 0)
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
        WHERE (is_deleted IS NULL OR is_deleted = 0)
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

    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    if new_status == "REJECTED" and rejection_type:
        # Rechazo tipificado: actualizar status + rejection fields + rejected_at
        cur.execute(f"""
            UPDATE admins
            SET status = {P},
                rejection_type = {P},
                rejection_reason = {P},
                rejected_at = {now_sql}
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

    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    if new_status == "REJECTED" and rejection_type:
        # Rechazo tipificado: actualizar status + rejection fields + rejected_at
        cur.execute(f"""
            UPDATE couriers
            SET status = {P},
                rejection_type = {P},
                rejection_reason = {P},
                rejected_at = {now_sql}
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
    _sync_courier_link_status(cur, courier_id, new_status, now_sql)
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

    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    if new_status == "REJECTED" and rejection_type:
        # Rechazo tipificado: actualizar status + rejection fields + rejected_at
        cur.execute(f"""
            UPDATE allies
            SET status = {P},
                rejection_type = {P},
                rejection_reason = {P},
                rejected_at = {now_sql}
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
    _sync_ally_link_status(cur, ally_id, new_status, now_sql)
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


def _get_registration_reset_state(table: str, entity_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            id,
            status,
            registration_reset_enabled_at,
            registration_reset_by_admin_id,
            registration_reset_note,
            registration_reset_consumed_at
        FROM {table}
        WHERE id = {P}
          AND (is_deleted IS NULL OR is_deleted = 0)
        LIMIT 1
    """, (entity_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    enabled_at = _row_value(row, "registration_reset_enabled_at", default=None)
    consumed_at = _row_value(row, "registration_reset_consumed_at", default=None)
    return {
        "id": _row_value(row, "id", default=entity_id),
        "status": _row_value(row, "status", default=None),
        "registration_reset_enabled_at": enabled_at,
        "registration_reset_by_admin_id": _row_value(row, "registration_reset_by_admin_id", default=None),
        "registration_reset_note": _row_value(row, "registration_reset_note", default=None),
        "registration_reset_consumed_at": consumed_at,
        "registration_reset_active": bool(enabled_at is not None and consumed_at is None),
    }


def _enable_registration_reset(table: str, entity_id: int, platform_admin_id: int, note: str = None) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE {table}
        SET registration_reset_enabled_at = {now_sql},
            registration_reset_by_admin_id = {P},
            registration_reset_note = {P},
            registration_reset_consumed_at = NULL
        WHERE id = {P}
          AND (is_deleted IS NULL OR is_deleted = 0)
    """, (platform_admin_id, note, entity_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def _clear_registration_reset(table: str, entity_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE {table}
        SET registration_reset_enabled_at = NULL,
            registration_reset_by_admin_id = NULL,
            registration_reset_note = NULL,
            registration_reset_consumed_at = NULL
        WHERE id = {P}
          AND (is_deleted IS NULL OR is_deleted = 0)
    """, (entity_id,))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_admin_reset_state_by_id(admin_id: int):
    return _get_registration_reset_state("admins", admin_id)


def get_ally_reset_state_by_id(ally_id: int):
    return _get_registration_reset_state("allies", ally_id)


def get_courier_reset_state_by_id(courier_id: int):
    return _get_registration_reset_state("couriers", courier_id)


def enable_admin_registration_reset(admin_id: int, platform_admin_id: int, note: str = None) -> bool:
    return _enable_registration_reset("admins", admin_id, platform_admin_id, note=note)


def enable_ally_registration_reset(ally_id: int, platform_admin_id: int, note: str = None) -> bool:
    return _enable_registration_reset("allies", ally_id, platform_admin_id, note=note)


def enable_courier_registration_reset(courier_id: int, platform_admin_id: int, note: str = None) -> bool:
    return _enable_registration_reset("couriers", courier_id, platform_admin_id, note=note)


def clear_admin_registration_reset(admin_id: int) -> bool:
    return _clear_registration_reset("admins", admin_id)


def clear_ally_registration_reset(ally_id: int) -> bool:
    return _clear_registration_reset("allies", ally_id)


def clear_courier_registration_reset(courier_id: int) -> bool:
    return _clear_registration_reset("couriers", courier_id)


def admin_has_active_registration_reset(admin_id: int) -> bool:
    state = get_admin_reset_state_by_id(admin_id)
    return bool(state and state["registration_reset_active"])


def ally_has_active_registration_reset(ally_id: int) -> bool:
    state = get_ally_reset_state_by_id(ally_id)
    return bool(state and state["registration_reset_active"])


def courier_has_active_registration_reset(courier_id: int) -> bool:
    state = get_courier_reset_state_by_id(courier_id)
    return bool(state and state["registration_reset_active"])


def _require_inactive_active_registration_reset(
    table: str,
    entity_id: int,
    entity_label: str,
    allowed_statuses=("INACTIVE",),
):
    state = _get_registration_reset_state(table, entity_id)
    if not state:
        raise ValueError(f"{entity_label} no encontrado.")
    if state["status"] not in allowed_statuses:
        allowed_text = " o ".join(allowed_statuses)
        raise ValueError(f"El registro de {entity_label.lower()} debe estar {allowed_text} para reiniciarse.")
    if not state["registration_reset_active"]:
        raise ValueError(f"El registro de {entity_label.lower()} no tiene un reinicio autorizado activo.")
    return state


def _fetch_registration_reset_row_for_update(cur, table: str, entity_id: int):
    deleted_filter = "is_deleted = 0" if table == "admins" else "(is_deleted IS NULL OR is_deleted = 0)"
    cur.execute(f"SELECT * FROM {table} WHERE id = {P} AND {deleted_filter} LIMIT 1", (entity_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def _serialize_registration_reset_payload(previous_row: dict) -> str:
    return json.dumps(previous_row, ensure_ascii=False, default=str)


def _insert_registration_reset_audit(
    cur,
    role_type: str,
    previous_row: dict,
    reset_note: str,
    authorized_by_admin_id,
    authorized_at,
    consumed_at,
):
    cur.execute(f"""
        INSERT INTO registration_reset_audit (
            role_type,
            role_id,
            person_id,
            user_id,
            previous_status,
            previous_payload_json,
            reset_note,
            authorized_by_admin_id,
            authorized_at,
            consumed_at
        )
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P})
    """, (
        role_type,
        previous_row.get("id"),
        previous_row.get("person_id"),
        previous_row.get("user_id"),
        previous_row.get("status"),
        _serialize_registration_reset_payload(previous_row),
        reset_note,
        authorized_by_admin_id,
        authorized_at,
        consumed_at,
    ))
    return cur.lastrowid


def create_registration_reset_audit(
    role_type: str,
    previous_row: dict,
    reset_note: str = None,
    authorized_by_admin_id=None,
    authorized_at=None,
    consumed_at=None,
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        audit_id = _insert_registration_reset_audit(
            cur,
            role_type=role_type,
            previous_row=previous_row,
            reset_note=reset_note,
            authorized_by_admin_id=authorized_by_admin_id,
            authorized_at=authorized_at,
            consumed_at=consumed_at,
        )
        conn.commit()
        return audit_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_admin_registration_in_place(
    admin_id: int,
    full_name: str,
    phone: str,
    city: str,
    barrio: str,
    team_name: str,
    document_number: str,
    residence_address=None,
    residence_lat=None,
    residence_lng=None,
    cedula_front_file_id=None,
    cedula_back_file_id=None,
    selfie_file_id=None,
):
    _require_inactive_active_registration_reset("admins", admin_id, "Administrador")
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    try:
        previous_row = _fetch_registration_reset_row_for_update(cur, "admins", admin_id)
        if not previous_row:
            raise ValueError("Administrador no encontrado.")
        if previous_row.get("status") != "INACTIVE":
            raise ValueError("El registro de administrador debe estar INACTIVE para reiniciarse.")
        if not previous_row.get("registration_reset_enabled_at") or previous_row.get("registration_reset_consumed_at"):
            raise ValueError("El registro de administrador no tiene un reinicio autorizado activo.")

        cur.execute(f"SELECT {now_sql} AS consumed_at")
        consumed_at = _row_value(cur.fetchone(), "consumed_at", 0)
        _insert_registration_reset_audit(
            cur,
            role_type="ADMIN",
            previous_row=previous_row,
            reset_note=previous_row.get("registration_reset_note"),
            authorized_by_admin_id=previous_row.get("registration_reset_by_admin_id"),
            authorized_at=previous_row.get("registration_reset_enabled_at"),
            consumed_at=consumed_at,
        )

        cur.execute(f"""
            UPDATE admins
            SET full_name = {P},
                phone = {P},
                city = {P},
                barrio = {P},
                team_name = {P},
                document_number = {P},
                residence_address = {P},
                residence_lat = {P},
                residence_lng = {P},
                cedula_front_file_id = {P},
                cedula_back_file_id = {P},
                selfie_file_id = {P},
                status = 'PENDING',
                rejection_type = 0,
                rejection_reason = NULL,
                rejected_at = NULL,
                registration_reset_enabled_at = NULL,
                registration_reset_by_admin_id = NULL,
                registration_reset_note = NULL,
                registration_reset_consumed_at = {P}
            WHERE id = {P}
              AND is_deleted = 0
        """, (
            full_name,
            normalize_phone(phone),
            city,
            barrio,
            team_name,
            normalize_document(document_number),
            residence_address,
            residence_lat,
            residence_lng,
            cedula_front_file_id,
            cedula_back_file_id,
            selfie_file_id,
            consumed_at,
            admin_id,
        ))
        updated = cur.rowcount > 0
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()
    if not updated:
        raise ValueError("No se pudo reiniciar el registro de administrador.")
    return get_admin_by_id(admin_id)


def reset_ally_registration_in_place(
    ally_id: int,
    business_name: str,
    owner_name: str,
    address: str,
    city: str,
    barrio: str,
    phone: str,
    document_number: str,
):
    state = _get_registration_reset_state("allies", ally_id)
    if not state:
        raise ValueError("Aliado no encontrado.")
    if state["status"] not in ("INACTIVE", "REJECTED"):
        raise ValueError("El registro de aliado debe estar INACTIVE o REJECTED para reiniciarse.")
    if not state["registration_reset_active"]:
        raise ValueError("El registro de aliado no tiene un reinicio autorizado activo.")
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    try:
        previous_row = _fetch_registration_reset_row_for_update(cur, "allies", ally_id)
        if not previous_row:
            raise ValueError("Aliado no encontrado.")
        if previous_row.get("status") not in ("INACTIVE", "REJECTED"):
            raise ValueError("El registro de aliado debe estar INACTIVE o REJECTED para reiniciarse.")
        if not previous_row.get("registration_reset_enabled_at") or previous_row.get("registration_reset_consumed_at"):
            raise ValueError("El registro de aliado no tiene un reinicio autorizado activo.")

        cur.execute(f"SELECT {now_sql} AS consumed_at")
        consumed_at = _row_value(cur.fetchone(), "consumed_at", 0)
        _insert_registration_reset_audit(
            cur,
            role_type="ALLY",
            previous_row=previous_row,
            reset_note=previous_row.get("registration_reset_note"),
            authorized_by_admin_id=previous_row.get("registration_reset_by_admin_id"),
            authorized_at=previous_row.get("registration_reset_enabled_at"),
            consumed_at=consumed_at,
        )

        cur.execute(f"""
            UPDATE allies
            SET business_name = {P},
                owner_name = {P},
                address = {P},
                city = {P},
                barrio = {P},
                phone = {P},
                document_number = {P},
                status = 'PENDING',
                rejection_type = 0,
                rejection_reason = NULL,
                rejected_at = NULL,
                registration_reset_enabled_at = NULL,
                registration_reset_by_admin_id = NULL,
                registration_reset_note = NULL,
                registration_reset_consumed_at = {P}
            WHERE id = {P}
              AND (is_deleted IS NULL OR is_deleted = 0)
        """, (
            business_name,
            owner_name,
            address,
            city,
            barrio,
            normalize_phone(phone),
            normalize_document(document_number),
            consumed_at,
            ally_id,
        ))
        updated = cur.rowcount > 0
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()
    if not updated:
        raise ValueError("No se pudo reiniciar el registro de aliado.")
    return get_ally_by_id(ally_id)


def reset_courier_registration_in_place(
    courier_id: int,
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
    cedula_front_file_id=None,
    cedula_back_file_id=None,
    selfie_file_id=None,
    vehicle_type="MOTO",
):
    _require_inactive_active_registration_reset(
        "couriers",
        courier_id,
        "Repartidor",
        allowed_statuses=("INACTIVE", "REJECTED"),
    )
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    try:
        previous_row = _fetch_registration_reset_row_for_update(cur, "couriers", courier_id)
        if not previous_row:
            raise ValueError("Repartidor no encontrado.")
        if previous_row.get("status") not in ("INACTIVE", "REJECTED"):
            raise ValueError("El registro de repartidor debe estar INACTIVE o REJECTED para reiniciarse.")
        if not previous_row.get("registration_reset_enabled_at") or previous_row.get("registration_reset_consumed_at"):
            raise ValueError("El registro de repartidor no tiene un reinicio autorizado activo.")

        cur.execute(f"SELECT {now_sql} AS consumed_at")
        consumed_at = _row_value(cur.fetchone(), "consumed_at", 0)
        _insert_registration_reset_audit(
            cur,
            role_type="COURIER",
            previous_row=previous_row,
            reset_note=previous_row.get("registration_reset_note"),
            authorized_by_admin_id=previous_row.get("registration_reset_by_admin_id"),
            authorized_at=previous_row.get("registration_reset_enabled_at"),
            consumed_at=consumed_at,
        )

        cur.execute(f"""
            UPDATE couriers
            SET full_name = {P},
                id_number = {P},
                phone = {P},
                city = {P},
                barrio = {P},
                plate = {P},
                bike_type = {P},
                code = {P},
                residence_address = {P},
                residence_lat = {P},
                residence_lng = {P},
                cedula_front_file_id = {P},
                cedula_back_file_id = {P},
                selfie_file_id = {P},
                vehicle_type = {P},
                status = 'PENDING',
                rejection_type = 0,
                rejection_reason = NULL,
                rejected_at = NULL,
                registration_reset_enabled_at = NULL,
                registration_reset_by_admin_id = NULL,
                registration_reset_note = NULL,
                registration_reset_consumed_at = {P}
            WHERE id = {P}
              AND (is_deleted IS NULL OR is_deleted = 0)
        """, (
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
            cedula_front_file_id,
            cedula_back_file_id,
            selfie_file_id,
            vehicle_type,
            consumed_at,
            courier_id,
        ))
        updated = cur.rowcount > 0
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    conn.close()
    if not updated:
        raise ValueError("No se pudo reiniciar el registro de repartidor.")
    return get_courier_by_id(courier_id)


def get_local_admins_count():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS total
        FROM admins
        WHERE is_deleted = 0
          AND team_code IS NOT NULL
          AND TRIM(team_code) <> ''
    """)

    count = cur.fetchone()["total"]
    conn.close()
    return count
    

def get_pending_couriers():
    """Devuelve todos los repartidores con estado PENDING (no eliminados)."""
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
          AND (is_deleted IS NULL OR is_deleted = 0)
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
          AND (c.is_deleted IS NULL OR c.is_deleted = 0)
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
          AND (c.is_deleted IS NULL OR c.is_deleted = 0)
        ORDER BY c.full_name ASC
    """, (admin_id, status))

    rows = cur.fetchall()
    conn.close()
    return rows
    

def get_pending_allies_by_admin(admin_id):
    """Devuelve aliados con vínculo PENDING para un admin (espejo de get_pending_couriers_by_admin)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            a.id AS ally_id,
            a.business_name,
            a.owner_name,
            a.phone,
            a.city,
            a.barrio
        FROM admin_allies aa
        JOIN allies a ON a.id = aa.ally_id
        WHERE aa.admin_id = {P}
          AND aa.status = 'PENDING'
          AND a.status != 'REJECTED'
          AND (a.is_deleted IS NULL OR a.is_deleted = 0)
        ORDER BY aa.created_at ASC
    """, (admin_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_allies_by_admin_and_status(admin_id, status):
    """Lista aliados de un admin por estado del vínculo (espejo de get_couriers_by_admin_and_status)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            a.id AS ally_id,
            a.business_name,
            a.owner_name,
            a.phone,
            a.city,
            a.barrio,
            aa.balance,
            aa.status
        FROM admin_allies aa
        JOIN allies a ON a.id = aa.ally_id
        WHERE aa.admin_id = {P}
          AND aa.status = {P}
          AND (a.is_deleted IS NULL OR a.is_deleted = 0)
        ORDER BY a.business_name ASC
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
                INSERT INTO admin_couriers (admin_id, courier_id, status, is_active, balance, created_at, updated_at)
                VALUES ({P}, {P}, 'PENDING', 0, 0, {now_sql}, {now_sql})
                ON CONFLICT(admin_id, courier_id) DO UPDATE SET
                    status='PENDING',
                    is_active=0,
                    updated_at={now_sql}
            """, (admin_id, courier_id))
        else:
            cur.execute(f"""
                INSERT INTO admin_couriers (admin_id, courier_id, status, is_active, balance, created_at, updated_at)
                VALUES ({P}, {P}, 'PENDING', 0, 0, {now_sql}, {now_sql})
                ON CONFLICT(admin_id, courier_id) DO UPDATE SET
                    status='PENDING',
                    is_active=0,
                    updated_at={now_sql}
            """, (admin_id, courier_id))
    else:
        if DB_ENGINE == "postgres":
            cur.execute(f"""
                INSERT INTO admin_couriers (admin_id, courier_id, status, balance, created_at, updated_at)
                VALUES ({P}, {P}, 'PENDING', 0, {now_sql}, {now_sql})
                ON CONFLICT(admin_id, courier_id) DO UPDATE SET
                    status='PENDING',
                    updated_at={now_sql}
            """, (admin_id, courier_id))
        else:
            cur.execute(f"""
                INSERT INTO admin_couriers (admin_id, courier_id, status, balance, created_at, updated_at)
                VALUES ({P}, {P}, 'PENDING', 0, {now_sql}, {now_sql})
                ON CONFLICT(admin_id, courier_id) DO UPDATE SET
                    status='PENDING',
                    updated_at={now_sql}
            """, (admin_id, courier_id))
    # Si el courier ya está APPROVED, sincronizar el nuevo vínculo inmediatamente
    cur.execute(f"SELECT status FROM couriers WHERE id = {P}", (courier_id,))
    c_row = cur.fetchone()
    if _row_value(c_row, "status", default="") == "APPROVED":
        _sync_courier_link_status(cur, courier_id, "APPROVED", now_sql)

    conn.commit()
    conn.close()


def update_ally_status(ally_id: int, status: str, changed_by: str = None):
    """Actualiza el estado de un aliado (PENDING, APPROVED, REJECTED) y sincroniza admin_allies."""
    status = normalize_role_status(status)
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
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
    _sync_ally_link_status(cur, ally_id, status, now_sql)
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
    if not has_valid_coords(lat, lng):
        raise ValueError("La direccion de recogida requiere ubicacion confirmada.")
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
            "id": row["id"],
            "ally_id": row["ally_id"],
            "label": row["label"],
            "address": row["address"],
            "city": row["city"],
            "barrio": row["barrio"],
            "phone": row["phone"],
            "is_default": row["is_default"],
            "created_at": row["created_at"],
            "lat": row["lat"],
            "lng": row["lng"],
            "use_count": row["use_count"] or 0,
            "is_frequent": row["is_frequent"] or 0,
            "last_used_at": row["last_used_at"],
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
        "id": row["id"],
        "ally_id": row["ally_id"],
        "label": row["label"],
        "address": row["address"],
        "city": row["city"],
        "barrio": row["barrio"],
        "phone": row["phone"],
        "is_default": row["is_default"],
        "created_at": row["created_at"],
        "lat": row["lat"],
        "lng": row["lng"],
        "use_count": row["use_count"] or 0,
        "is_frequent": row["is_frequent"] or 0,
        "last_used_at": row["last_used_at"],
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
        "id": row["id"],
        "ally_id": row["ally_id"],
        "label": row["label"],
        "address": row["address"],
        "city": row["city"],
        "barrio": row["barrio"],
        "phone": row["phone"],
        "is_default": row["is_default"],
        "created_at": row["created_at"],
        "lat": row["lat"],
        "lng": row["lng"],
        "use_count": row["use_count"] or 0,
        "is_frequent": row["is_frequent"] or 0,
        "last_used_at": row["last_used_at"],
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
    if not has_valid_coords(lat, lng):
        raise ValueError("La direccion de recogida requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE ally_locations SET lat = {P}, lng = {P} WHERE id = {P};",
        (lat, lng, location_id),
    )
    conn.commit()
    conn.close()


# ---------- DIRECCIONES DE ADMIN (admin_locations) ----------

def create_admin_location(
    admin_id: int,
    label: str,
    address: str,
    city: str,
    barrio: str,
    phone: str = None,
    lat: float = None,
    lng: float = None,
    is_default: bool = False,
):
    """Crea una dirección de recogida para un admin."""
    if not has_valid_coords(lat, lng):
        raise ValueError("La direccion de recogida requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    if is_default:
        cur.execute(
            f"UPDATE admin_locations SET is_default = 0 WHERE admin_id = {P};",
            (admin_id,),
        )
    location_id = _insert_returning_id(cur, f"""
        INSERT INTO admin_locations (
            admin_id, label, address, city, barrio, phone, is_default, lat, lng
        ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P});
    """, (admin_id, label, address, city, barrio, phone, 1 if is_default else 0, lat, lng))
    conn.commit()
    conn.close()
    return location_id


def get_admin_locations(admin_id: int):
    """Devuelve todas las direcciones de un admin ordenadas por prioridad."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, admin_id, label, address, city, barrio, phone, is_default,
               lat, lng, use_count, is_frequent, last_used_at, created_at
        FROM admin_locations
        WHERE admin_id = {P} AND (status IS NULL OR status = 'ACTIVE')
        ORDER BY is_default DESC, is_frequent DESC, use_count DESC, id ASC;
    """, (admin_id,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": _row_value(row, "id"),
            "admin_id": _row_value(row, "admin_id"),
            "label": _row_value(row, "label"),
            "address": _row_value(row, "address"),
            "city": _row_value(row, "city"),
            "barrio": _row_value(row, "barrio"),
            "phone": _row_value(row, "phone"),
            "is_default": _row_value(row, "is_default"),
            "lat": _row_value(row, "lat"),
            "lng": _row_value(row, "lng"),
            "use_count": _row_value(row, "use_count") or 0,
            "is_frequent": _row_value(row, "is_frequent") or 0,
            "last_used_at": _row_value(row, "last_used_at"),
        }
        for row in rows
    ]


def get_admin_location_by_id(location_id: int, admin_id: int):
    """Devuelve una dirección específica de un admin como dict (o None)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, admin_id, label, address, city, barrio, phone, is_default,
               lat, lng, use_count, is_frequent, last_used_at, created_at
        FROM admin_locations
        WHERE id = {P} AND admin_id = {P}
        LIMIT 1;
    """, (location_id, admin_id))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": _row_value(row, "id"),
        "admin_id": _row_value(row, "admin_id"),
        "label": _row_value(row, "label"),
        "address": _row_value(row, "address"),
        "city": _row_value(row, "city"),
        "barrio": _row_value(row, "barrio"),
        "phone": _row_value(row, "phone"),
        "is_default": _row_value(row, "is_default"),
        "lat": _row_value(row, "lat"),
        "lng": _row_value(row, "lng"),
        "use_count": _row_value(row, "use_count") or 0,
        "is_frequent": _row_value(row, "is_frequent") or 0,
        "last_used_at": _row_value(row, "last_used_at"),
    }


def get_default_admin_location(admin_id: int):
    """Devuelve la dirección principal de un admin como dict (o None)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, admin_id, label, address, city, barrio, phone, is_default,
               lat, lng, use_count, is_frequent, last_used_at, created_at
        FROM admin_locations
        WHERE admin_id = {P} AND is_default = 1
        ORDER BY id ASC
        LIMIT 1;
    """, (admin_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": _row_value(row, "id"),
        "admin_id": _row_value(row, "admin_id"),
        "label": _row_value(row, "label"),
        "address": _row_value(row, "address"),
        "city": _row_value(row, "city"),
        "barrio": _row_value(row, "barrio"),
        "phone": _row_value(row, "phone"),
        "is_default": _row_value(row, "is_default"),
        "lat": _row_value(row, "lat"),
        "lng": _row_value(row, "lng"),
        "use_count": _row_value(row, "use_count") or 0,
        "is_frequent": _row_value(row, "is_frequent") or 0,
        "last_used_at": _row_value(row, "last_used_at"),
    }


def set_default_admin_location(location_id: int, admin_id: int):
    """Marca una dirección como principal para ese admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE admin_locations SET is_default = 0 WHERE admin_id = {P};",
        (admin_id,),
    )
    cur.execute(
        f"UPDATE admin_locations SET is_default = 1 WHERE id = {P} AND admin_id = {P};",
        (location_id, admin_id),
    )
    conn.commit()
    conn.close()


def increment_admin_location_usage(location_id: int, admin_id: int):
    """Incrementa use_count y actualiza last_used_at para una admin location."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_locations
        SET use_count = COALESCE(use_count, 0) + 1,
            last_used_at = {now_sql}
        WHERE id = {P} AND admin_id = {P};
    """, (location_id, admin_id))
    conn.commit()
    conn.close()


def increment_pickup_usage(location_id: int, ally_id: int):
    """Incrementa use_count y actualiza last_used_at para una pickup."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_locations
        SET use_count = COALESCE(use_count, 0) + 1,
            last_used_at = {now_sql}
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
    ally_id: int = None,
    customer_name: str = None,
    customer_phone: str = None,
    customer_address: str = None,
    customer_city: str = None,
    customer_barrio: str = None,
    pickup_location_id: int = None,
    pay_at_store_required: bool = False,
    pay_at_store_amount: int = 0,
    base_fee: int = 0,
    distance_km: float = 0,
    buy_surcharge: int = 0,
    rain_extra: int = 0,
    high_demand_extra: int = 0,
    night_extra: int = 0,
    additional_incentive: int = 0,
    total_fee: int = 0,
    instructions: str = None,
    requires_cash: bool = False,
    cash_required_amount: int = 0,
    pickup_lat: float = None,
    pickup_lng: float = None,
    dropoff_lat: float = None,
    dropoff_lng: float = None,
    quote_source: str = None,
    ally_admin_id_snapshot: int = None,
    creator_admin_id: int = None,
    purchase_amount: int = None,
    delivery_subsidy_applied: int = 0,
    customer_delivery_fee: int = None,
    payment_method: str = "UNCONFIRMED",
    payment_confirmed_at: str = None,
    payment_confirmed_by: int = None,
    parking_fee: int = 0,
):
    """Crea un pedido en estado PENDING y devuelve su id.

    Para pedidos de aliados: ally_id requerido, creator_admin_id=None.
    Para pedidos especiales de admin: ally_id=None, creator_admin_id requerido.
    parking_fee: tarifa de parqueadero incluida en este pedido (0 si no aplica).
    """
    if not has_valid_coords(pickup_lat, pickup_lng):
        raise ValueError("El punto de recogida requiere ubicacion confirmada.")
    if not has_valid_coords(dropoff_lat, dropoff_lng):
        raise ValueError("La direccion de entrega requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    order_id = _insert_returning_id(cur, f"""
        INSERT INTO orders (
            ally_id,
            creator_admin_id,
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
            buy_surcharge,
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
            courier_admin_id_snapshot,
            purchase_amount,
            delivery_subsidy_applied,
            customer_delivery_fee,
            payment_method,
            payment_confirmed_at,
            payment_confirmed_by,
            parking_fee
        ) VALUES ({P}, {P}, NULL, 'PENDING', {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P});
    """, (
        ally_id,
        creator_admin_id,
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
        buy_surcharge,
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
        purchase_amount,
        delivery_subsidy_applied if delivery_subsidy_applied is not None else 0,
        customer_delivery_fee,
        payment_method,
        payment_confirmed_at,
        payment_confirmed_by,
        parking_fee if parking_fee else 0,
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
        now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
        query = f"UPDATE orders SET status = {P}, {timestamp_field} = {now_sql} WHERE id = {P};"
        cur.execute(query, (status, order_id))
    else:
        cur.execute(f"UPDATE orders SET status = {P} WHERE id = {P};", (status, order_id))

    conn.commit()
    conn.close()


def add_order_incentive(order_id: int, delta: int):
    """Incrementa additional_incentive y total_fee de un pedido por delta."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE orders
        SET additional_incentive = COALESCE(additional_incentive, 0) + {P},
            total_fee = COALESCE(total_fee, 0) + {P}
        WHERE id = {P};
        """,
        (delta, delta, order_id),
    )
    conn.commit()
    conn.close()


def add_route_incentive(route_id: int, delta: int):
    """Incrementa additional_incentive y total_fee de una ruta por delta."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE routes
        SET additional_incentive = COALESCE(additional_incentive, 0) + {P},
            total_fee = COALESCE(total_fee, 0) + {P}
        WHERE id = {P};
        """,
        (delta, delta, route_id),
    )
    conn.commit()
    conn.close()


def update_order_payment(order_id, payment_method, cash_required_amount,
                         changed_by, conn=None):
    """Actualiza el medio de pago de un pedido existente."""
    requires_cash = 1 if payment_method == "CASH_CONFIRMED" else 0
    import datetime
    changed_at = datetime.datetime.now().isoformat()

    with get_connection(conn) as c:
        c.execute("""
            UPDATE orders
            SET payment_method = ?,
                payment_confirmed_at = ?,
                payment_confirmed_by = ?,
                payment_changed_at = ?,
                payment_changed_by = ?,
                payment_prev_method = payment_method,
                requires_cash = ?,
                cash_required_amount = ?
            WHERE id = ?
        """, (
            payment_method,
            changed_at,
            changed_by,
            changed_at,
            changed_by,
            requires_cash,
            cash_required_amount,
            order_id,
        ))


def assign_order_to_courier(order_id: int, courier_id: int, courier_admin_id_snapshot: int = None):
    """Asigna un pedido a un repartidor y marca accepted_at."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE orders
        SET courier_id = {P}, status = 'ACCEPTED', accepted_at = {now_sql},
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


def get_ally_orders_between(ally_id: int, start_s: str, end_s: str):
    """Pedidos de un aliado (DELIVERED o CANCELLED) creados entre start_s y end_s."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT *
        FROM orders
        WHERE ally_id = {P}
          AND status IN ('DELIVERED', 'CANCELLED')
          AND created_at >= {P}
          AND created_at < {P}
        ORDER BY created_at DESC
    """, (ally_id, start_s, end_s))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_ally_routes_between(ally_id: int, start_s: str, end_s: str):
    """Rutas de un aliado (DELIVERED o CANCELLED) creadas entre start_s y end_s."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT *
        FROM routes
        WHERE ally_id = {P}
          AND status IN ('DELIVERED', 'CANCELLED')
          AND created_at >= {P}
          AND created_at < {P}
        ORDER BY created_at DESC
    """, (ally_id, start_s, end_s))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


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


def get_admin_panel_balances_data(admin_id=None):
    """Retorna saldos de admins, repartidores y aliados para el panel web.
    Si admin_id no es None, filtra solo el equipo de ese admin (ADMIN_LOCAL).
    """
    conn = get_connection()
    cur = conn.cursor()

    if admin_id is None:
        cur.execute("""
            SELECT a.id, a.full_name, a.balance, a.status, a.city
            FROM admins a
            ORDER BY a.balance DESC
        """)
    else:
        cur.execute(
            f"SELECT a.id, a.full_name, a.balance, a.status, a.city"
            f" FROM admins a WHERE a.id = {P}",
            (admin_id,),
        )
    admins_rows = cur.fetchall()

    courier_filter = f"AND ac.admin_id = {P}" if admin_id is not None else ""
    courier_params = (admin_id,) if admin_id is not None else ()
    cur.execute(f"""
        SELECT c.id, c.full_name, ac.balance, ac.status AS link_status,
               c.status AS courier_status, c.city, a.full_name AS admin_name
        FROM admin_couriers ac
        JOIN couriers c ON c.id = ac.courier_id
        JOIN admins a ON a.id = ac.admin_id
        WHERE ac.status = 'APPROVED' {courier_filter}
        ORDER BY ac.balance DESC
    """, courier_params)
    couriers_rows = cur.fetchall()

    ally_filter = f"AND aa.admin_id = {P}" if admin_id is not None else ""
    ally_params = (admin_id,) if admin_id is not None else ()
    cur.execute(f"""
        SELECT al.id, al.business_name, aa.balance, aa.status AS link_status,
               al.status AS ally_status, al.city, a.full_name AS admin_name
        FROM admin_allies aa
        JOIN allies al ON al.id = aa.ally_id
        JOIN admins a ON a.id = aa.admin_id
        WHERE aa.status = 'APPROVED' {ally_filter}
        ORDER BY aa.balance DESC
    """, ally_params)
    allies_rows = cur.fetchall()
    conn.close()

    return {
        "admins": [
            {
                "id": _row_value(r, "id", 0, 0),
                "nombre": _row_value(r, "full_name", 1, "") or "",
                "balance": _row_value(r, "balance", 2, 0) or 0,
                "status": _row_value(r, "status", 3, "") or "",
                "ciudad": _row_value(r, "city", 4, "") or "",
            }
            for r in admins_rows
        ],
        "couriers": [
            {
                "id": _row_value(r, "id", 0, 0),
                "nombre": _row_value(r, "full_name", 1, "") or "",
                "balance": _row_value(r, "balance", 2, 0) or 0,
                "status": _row_value(r, "courier_status", 4, "") or "",
                "ciudad": _row_value(r, "city", 5, "") or "",
                "admin_nombre": _row_value(r, "admin_name", 6, "") or "",
            }
            for r in couriers_rows
        ],
        "aliados": [
            {
                "id": _row_value(r, "id", 0, 0),
                "nombre": _row_value(r, "business_name", 1, "") or "",
                "balance": _row_value(r, "balance", 2, 0) or 0,
                "status": _row_value(r, "ally_status", 4, "") or "",
                "ciudad": _row_value(r, "city", 5, "") or "",
                "admin_nombre": _row_value(r, "admin_name", 6, "") or "",
            }
            for r in allies_rows
        ],
    }


def get_admin_panel_users_data(admin_id=None):
    """Retorna el consolidado de usuarios del panel web.
    Si admin_id no es None, filtra solo couriers/allies del equipo de ese admin.
    """
    conn = get_connection()
    cur = conn.cursor()

    if admin_id is None:
        cur.execute("""
            SELECT
                u.id, u.telegram_id, u.username, u.created_at,
                COALESCE(a.full_name, c.full_name, al.business_name, u.username, '') AS nombre,
                COALESCE(a.phone, c.phone, al.phone, '') AS phone,
                COALESCE(a.city, c.city, al.city, '') AS ciudad,
                COALESCE(a.status, c.status, al.status, '') AS status,
                CASE
                    WHEN a.id IS NOT NULL AND (a.team_name = 'PLATAFORMA' OR u.role IN ('PLATFORM_ADMIN','ADMIN_PLATFORM'))
                        THEN 'PLATFORM_ADMIN'
                    WHEN a.id IS NOT NULL THEN 'ADMIN_LOCAL'
                    WHEN c.id IS NOT NULL THEN 'COURIER'
                    WHEN al.id IS NOT NULL THEN 'ALLY'
                    WHEN u.role IN ('PLATFORM_ADMIN','ADMIN_PLATFORM') THEN 'PLATFORM_ADMIN'
                    ELSE COALESCE(u.role, '')
                END AS rol_inferido
            FROM users u
            LEFT JOIN admins a ON a.user_id = u.id AND a.is_deleted = 0
            LEFT JOIN couriers c ON c.user_id = u.id
            LEFT JOIN allies al ON al.user_id = u.id AND (al.is_deleted IS NULL OR al.is_deleted = 0)
            ORDER BY u.id DESC
        """)
        telegram_users = cur.fetchall()

        cur.execute("SELECT id, full_name, phone, city, status, created_at FROM couriers ORDER BY id")
        all_couriers = cur.fetchall()

        cur.execute("""
            SELECT id, business_name, phone, city, status, created_at
            FROM allies
            WHERE is_deleted IS NULL OR is_deleted = 0
            ORDER BY id
        """)
        all_allies = cur.fetchall()
    else:
        # Solo couriers y aliados vinculados al admin
        cur.execute(f"""
            SELECT
                u.id, u.telegram_id, u.username, u.created_at,
                c.full_name AS nombre, c.phone AS phone, c.city AS ciudad,
                c.status AS status, 'COURIER' AS rol_inferido
            FROM admin_couriers ac
            JOIN couriers c ON c.id = ac.courier_id
            JOIN users u ON u.id = c.user_id
            WHERE ac.admin_id = {P}
            UNION ALL
            SELECT
                u.id, u.telegram_id, u.username, u.created_at,
                al.business_name AS nombre, al.phone AS phone, al.city AS ciudad,
                al.status AS status, 'ALLY' AS rol_inferido
            FROM admin_allies aa
            JOIN allies al ON al.id = aa.ally_id
            JOIN users u ON u.id = al.user_id
            WHERE aa.admin_id = {P} AND (al.is_deleted IS NULL OR al.is_deleted = 0)
            ORDER BY id DESC
        """, (admin_id, admin_id))
        telegram_users = cur.fetchall()
        all_couriers = []
        all_allies = []
    conn.close()

    result = []
    for r in telegram_users:
        result.append({
            "id": _row_value(r, "id", 0, 0),
            "telegram_id": _row_value(r, "telegram_id", 1, 0),
            "username": _row_value(r, "username", 2, "") or "",
            "role": _row_value(r, "rol_inferido", 8, "") or "",
            "created_at": str(_row_value(r, "created_at", 3, "")) or "",
            "nombre": _row_value(r, "nombre", 4, "") or "",
            "phone": _row_value(r, "phone", 5, "") or "",
            "ciudad": _row_value(r, "ciudad", 6, "") or "",
            "status": _row_value(r, "status", 7, "") or "",
        })

    courier_ids_seen = {
        _row_value(r, "id", 0, 0)
        for r in telegram_users
        if _row_value(r, "rol_inferido", 8, "") == "COURIER"
    }
    ally_ids_seen = {
        _row_value(r, "id", 0, 0)
        for r in telegram_users
        if _row_value(r, "rol_inferido", 8, "") == "ALLY"
    }

    for c in all_couriers:
        cid = _row_value(c, "id", 0, 0)
        if cid not in courier_ids_seen:
            result.append({
                "id": cid,
                "telegram_id": 0,
                "username": "",
                "role": "COURIER",
                "created_at": str(_row_value(c, "created_at", 5, "")) or "",
                "nombre": _row_value(c, "full_name", 1, "") or "",
                "phone": _row_value(c, "phone", 2, "") or "",
                "ciudad": _row_value(c, "city", 3, "") or "",
                "status": _row_value(c, "status", 4, "") or "",
            })

    for a in all_allies:
        aid = _row_value(a, "id", 0, 0)
        if aid not in ally_ids_seen:
            result.append({
                "id": aid,
                "telegram_id": 0,
                "username": "",
                "role": "ALLY",
                "created_at": str(_row_value(a, "created_at", 5, "")) or "",
                "nombre": _row_value(a, "business_name", 1, "") or "",
                "phone": _row_value(a, "phone", 2, "") or "",
                "ciudad": _row_value(a, "city", 3, "") or "",
                "status": _row_value(a, "status", 4, "") or "",
            })

    return result


def get_admin_panel_earnings_data(admin_id=None):
    """Retorna resumen e historial de ganancias para el panel web.
    Si admin_id no es None, filtra ganancias solo del equipo de ese admin.
    """
    conn = get_connection()
    cur = conn.cursor()

    admin_where = f"AND l.to_id = {P} AND l.to_type = 'ADMIN'" if admin_id is not None else ""
    admin_params = (admin_id,) if admin_id is not None else ()

    cur.execute(f"""
        SELECT
            SUM(CASE WHEN date(created_at) = date('now') THEN amount ELSE 0 END) AS hoy,
            SUM(CASE WHEN created_at >= date('now', 'weekday 0', '-7 days') THEN amount ELSE 0 END) AS semana,
            SUM(CASE WHEN strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now') THEN amount ELSE 0 END) AS mes,
            SUM(amount) AS total
        FROM ledger l
        WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE') {admin_where}
    """, admin_params)
    resumen_row = cur.fetchone()

    if admin_id is None:
        cur.execute("""
            SELECT a.full_name, SUM(l.amount) AS total
            FROM ledger l
            JOIN admins a ON a.id = l.to_id
            WHERE l.kind IN ('FEE_INCOME', 'PLATFORM_FEE') AND l.to_type = 'ADMIN'
            GROUP BY l.to_id, a.full_name
            ORDER BY total DESC
        """)
    else:
        cur.execute(
            f"SELECT a.full_name, SUM(l.amount) AS total"
            f" FROM ledger l JOIN admins a ON a.id = l.to_id"
            f" WHERE l.kind IN ('FEE_INCOME', 'PLATFORM_FEE') AND l.to_type = 'ADMIN' AND l.to_id = {P}"
            f" GROUP BY l.to_id, a.full_name ORDER BY total DESC",
            (admin_id,),
        )
    por_admin_rows = cur.fetchall()

    cur.execute(f"""
        SELECT l.id, l.kind, l.amount, l.from_type, l.from_id, l.note, l.created_at,
               a.full_name AS admin_nombre
        FROM ledger l
        LEFT JOIN admins a ON a.id = l.to_id AND l.to_type = 'ADMIN'
        WHERE l.kind IN ('FEE_INCOME', 'PLATFORM_FEE', 'INCOME') {admin_where}
        ORDER BY l.created_at DESC
        LIMIT 50
    """, admin_params)
    historial_rows = cur.fetchall()
    conn.close()

    return {
        "resumen": {
            "hoy": _row_value(resumen_row, "hoy", 0, 0) or 0,
            "semana": _row_value(resumen_row, "semana", 1, 0) or 0,
            "mes": _row_value(resumen_row, "mes", 2, 0) or 0,
            "total": _row_value(resumen_row, "total", 3, 0) or 0,
        },
        "por_admin": [
            {
                "nombre": _row_value(r, "full_name", 0, "") or "",
                "total": _row_value(r, "total", 1, 0) or 0,
            }
            for r in por_admin_rows
        ],
        "historial": [
            {
                "id": _row_value(r, "id", 0),
                "kind": _row_value(r, "kind", 1, "") or "",
                "amount": _row_value(r, "amount", 2, 0) or 0,
                "from_type": _row_value(r, "from_type", 3, "") or "",
                "note": _row_value(r, "note", 5, "") or "",
                "created_at": str(_row_value(r, "created_at", 6, "")) or "",
                "admin_nombre": _row_value(r, "admin_nombre", 7, "") or "",
            }
            for r in historial_rows
        ],
    }


def get_dashboard_stats_data(admin_id=None):
    """Retorna las metricas agregadas del dashboard web.
    Si admin_id no es None, filtra contadores al equipo de ese admin (ADMIN_LOCAL).
    """
    conn = get_connection()
    cur = conn.cursor()

    if admin_id is None:
        cur.execute("""
            SELECT COUNT(*) FROM admins a
            LEFT JOIN users u ON u.id = a.user_id
            WHERE u.role NOT IN ('PLATFORM_ADMIN', 'ADMIN_PLATFORM') OR u.role IS NULL
        """)
        total_admins = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute("""
            SELECT COUNT(*) FROM admins a
            LEFT JOIN users u ON u.id = a.user_id
            WHERE (u.role NOT IN ('PLATFORM_ADMIN', 'ADMIN_PLATFORM') OR u.role IS NULL)
              AND a.status = 'APPROVED'
        """)
        admins_activos = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute("""
            SELECT COUNT(*) FROM admins a
            LEFT JOIN users u ON u.id = a.user_id
            WHERE (u.role NOT IN ('PLATFORM_ADMIN', 'ADMIN_PLATFORM') OR u.role IS NULL)
              AND a.status = 'PENDING'
        """)
        admins_pendientes = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute("SELECT COUNT(*) FROM couriers")
        total_couriers = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute("SELECT COUNT(*) FROM couriers WHERE status = 'APPROVED'")
        couriers_activos = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute("SELECT COUNT(*) FROM couriers WHERE status = 'PENDING'")
        couriers_pendientes = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute("SELECT COUNT(*) FROM allies")
        total_aliados = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute("SELECT COUNT(*) FROM allies WHERE status = 'APPROVED'")
        aliados_activos = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute("SELECT COUNT(*) FROM allies WHERE status = 'PENDING'")
        aliados_pendientes = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute("SELECT COUNT(*) FROM orders WHERE status IN ('PUBLISHED','ACCEPTED','PICKED_UP')")
        pedidos_activos = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'DELIVERED' AND DATE(delivered_at) = DATE('now')")
        pedidos_entregados_hoy = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'DELIVERED'")
        pedidos_total_entregados = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute("""
            SELECT a.balance FROM admins a
            JOIN users u ON u.id = a.user_id
            WHERE u.role IN ('PLATFORM_ADMIN', 'ADMIN_PLATFORM')
            LIMIT 1
        """)
        saldo_row = cur.fetchone()
        saldo_plataforma = _row_value(saldo_row, "balance", 0, 0) if saldo_row else 0

        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM ledger
            WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE')
              AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
        """)
        ganancias_mes = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0
        cur.execute("SELECT COALESCE(SUM(amount), 0) FROM ledger WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE')")
        ganancias_total = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0
    else:
        # Contadores del equipo del admin
        total_admins = admins_activos = admins_pendientes = 0  # ADMIN_LOCAL no gestiona otros admins

        cur.execute(f"SELECT COUNT(*) FROM admin_couriers WHERE admin_id = {P}", (admin_id,))
        total_couriers = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute(
            f"SELECT COUNT(*) FROM admin_couriers ac JOIN couriers c ON c.id = ac.courier_id"
            f" WHERE ac.admin_id = {P} AND c.status = 'APPROVED'", (admin_id,),
        )
        couriers_activos = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute(
            f"SELECT COUNT(*) FROM admin_couriers ac JOIN couriers c ON c.id = ac.courier_id"
            f" WHERE ac.admin_id = {P} AND c.status = 'PENDING'", (admin_id,),
        )
        couriers_pendientes = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute(f"SELECT COUNT(*) FROM admin_allies WHERE admin_id = {P}", (admin_id,))
        total_aliados = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute(
            f"SELECT COUNT(*) FROM admin_allies aa JOIN allies al ON al.id = aa.ally_id"
            f" WHERE aa.admin_id = {P} AND al.status = 'APPROVED'", (admin_id,),
        )
        aliados_activos = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute(
            f"SELECT COUNT(*) FROM admin_allies aa JOIN allies al ON al.id = aa.ally_id"
            f" WHERE aa.admin_id = {P} AND al.status = 'PENDING'", (admin_id,),
        )
        aliados_pendientes = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute(
            f"SELECT COUNT(*) FROM orders WHERE status IN ('PUBLISHED','ACCEPTED','PICKED_UP')"
            f" AND (ally_admin_id_snapshot = {P} OR courier_admin_id_snapshot = {P} OR creator_admin_id = {P})",
            (admin_id, admin_id, admin_id),
        )
        pedidos_activos = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute(
            f"SELECT COUNT(*) FROM orders WHERE status = 'DELIVERED' AND DATE(delivered_at) = DATE('now')"
            f" AND (ally_admin_id_snapshot = {P} OR courier_admin_id_snapshot = {P} OR creator_admin_id = {P})",
            (admin_id, admin_id, admin_id),
        )
        pedidos_entregados_hoy = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0
        cur.execute(
            f"SELECT COUNT(*) FROM orders WHERE status = 'DELIVERED'"
            f" AND (ally_admin_id_snapshot = {P} OR courier_admin_id_snapshot = {P} OR creator_admin_id = {P})",
            (admin_id, admin_id, admin_id),
        )
        pedidos_total_entregados = _row_value(cur.fetchone(), "COUNT(*)", 0, 0) or 0

        cur.execute(f"SELECT balance FROM admins WHERE id = {P}", (admin_id,))
        saldo_row = cur.fetchone()
        saldo_plataforma = _row_value(saldo_row, "balance", 0, 0) if saldo_row else 0

        cur.execute(
            f"SELECT COALESCE(SUM(amount), 0) FROM ledger"
            f" WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE') AND to_type = 'ADMIN' AND to_id = {P}"
            f" AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')", (admin_id,),
        )
        ganancias_mes = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0
        cur.execute(
            f"SELECT COALESCE(SUM(amount), 0) FROM ledger"
            f" WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE') AND to_type = 'ADMIN' AND to_id = {P}",
            (admin_id,),
        )
        ganancias_total = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0

    conn.close()

    return {
        "admins": {
            "total": total_admins,
            "activos": admins_activos,
            "pendientes": admins_pendientes,
        },
        "couriers": {
            "total": total_couriers,
            "activos": couriers_activos,
            "pendientes": couriers_pendientes,
        },
        "aliados": {
            "total": total_aliados,
            "activos": aliados_activos,
            "pendientes": aliados_pendientes,
        },
        "pedidos": {
            "activos": pedidos_activos,
            "entregados_hoy": pedidos_entregados_hoy,
            "total_entregados": pedidos_total_entregados,
        },
        "saldo_plataforma": saldo_plataforma,
        "ganancias_mes": ganancias_mes,
        "ganancias_total": ganancias_total,
    }


# ---------- ESTADÍSTICAS DE TIEMPOS DE ENTREGA ----------

def get_courier_delivery_time_stats(admin_id=None, courier_id=None, days=30):
    """
    Devuelve estadísticas de tiempos de entrega por repartidor.
    admin_id: si se provee, filtra al equipo actual del admin (admin_couriers APPROVED).
    courier_id: si se provee, filtra a ese repartidor específico.
    days: ventana de tiempo en días hacia atrás desde hoy (default 30).
    Retorna lista de filas con: courier_id, full_name, total_entregados,
    avg_llegada_seg, avg_entrega_seg, avg_total_seg.
    """
    conn = get_connection()
    cur = conn.cursor()

    if DB_ENGINE == "postgres":
        time_filter = f"o.delivered_at >= NOW() - INTERVAL '{days} days'"
        avg_llegada = "AVG(EXTRACT(EPOCH FROM (o.courier_arrived_at - o.accepted_at)))"
        avg_entrega = "AVG(EXTRACT(EPOCH FROM (o.delivered_at - o.pickup_confirmed_at)))"
        avg_total   = "AVG(EXTRACT(EPOCH FROM (o.delivered_at - o.accepted_at)))"
    else:
        time_filter = f"o.delivered_at >= datetime('now', '-{days} days')"
        avg_llegada = "AVG(CAST(strftime('%s', o.courier_arrived_at) AS INTEGER) - CAST(strftime('%s', o.accepted_at) AS INTEGER))"
        avg_entrega = "AVG(CAST(strftime('%s', o.delivered_at) AS INTEGER) - CAST(strftime('%s', o.pickup_confirmed_at) AS INTEGER))"
        avg_total   = "AVG(CAST(strftime('%s', o.delivered_at) AS INTEGER) - CAST(strftime('%s', o.accepted_at) AS INTEGER))"

    query = f"""
        SELECT
            o.courier_id,
            c.full_name,
            COUNT(*) AS total_entregados,
            {avg_llegada} AS avg_llegada_seg,
            {avg_entrega} AS avg_entrega_seg,
            {avg_total}   AS avg_total_seg
        FROM orders o
        JOIN couriers c ON c.id = o.courier_id
    """
    params = []

    if admin_id is not None:
        query += f" JOIN admin_couriers ac ON ac.courier_id = o.courier_id AND ac.admin_id = {P} AND ac.status = 'APPROVED'"
        params.append(admin_id)

    query += f" WHERE o.status = 'DELIVERED' AND {time_filter} AND o.accepted_at IS NOT NULL AND o.delivered_at IS NOT NULL"

    if courier_id is not None:
        query += f" AND o.courier_id = {P}"
        params.append(courier_id)

    query += " GROUP BY o.courier_id, c.full_name ORDER BY avg_total_seg ASC"

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
    cedula_front_file_id=None,
    cedula_back_file_id=None,
    selfie_file_id=None,
    vehicle_type="MOTO",
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
                residence_lng,
                cedula_front_file_id,
                cedula_back_file_id,
                selfie_file_id,
                vehicle_type
            ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'PENDING', 0, {P}, {P}, {P}, {P}, {P}, {P}, {P});
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
            cedula_front_file_id,
            cedula_back_file_id,
            selfie_file_id,
            vehicle_type,
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
            COALESCE(availability_status, 'INACTIVE') AS availability_status, -- 20
            cedula_front_file_id,  -- 21
            cedula_back_file_id,   -- 22
            selfie_file_id         -- 23
        FROM couriers
        WHERE id = {P}
          AND (is_deleted IS NULL OR is_deleted = 0);
    """, (courier_id,))
    row = cur.fetchone()
    conn.close()
    return row

def update_courier_status(courier_id: int, new_status: str, changed_by: str = None):
    """Actualiza el estado de un repartidor (APPROVED / REJECTED) y sincroniza admin_couriers."""
    new_status = normalize_role_status(new_status)
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
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
    _sync_courier_link_status(cur, courier_id, new_status, now_sql)
    conn.commit()
    conn.close()

def get_totales_registros():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS total FROM allies WHERE (is_deleted IS NULL OR is_deleted = 0);")
    total_allies = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS total FROM couriers WHERE (is_deleted IS NULL OR is_deleted = 0);")
    total_couriers = cur.fetchone()["total"]

    conn.close()
    return total_allies, total_couriers


def delete_courier(courier_id: int) -> None:
    """Desactiva (soft delete) un repartidor sin borrar datos."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"

    # Desactivar perfil
    cur.execute(f"""
        UPDATE couriers
        SET status = 'INACTIVE',
            is_deleted = 1,
            deleted_at = {now_sql}
        WHERE id = {P}
    """, (courier_id,))

    # Desactivar vínculos con admins (no borrar, solo inactivar)
    cur.execute(f"""
        UPDATE admin_couriers
        SET status = 'INACTIVE',
            is_active = 0,
            updated_at = {now_sql}
        WHERE courier_id = {P}
    """, (courier_id,))

    conn.commit()
    conn.close()


def delete_ally(ally_id: int) -> None:
    """Desactiva (soft delete) un aliado sin borrar datos."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"

    cur.execute(f"""
        UPDATE allies
        SET status = 'INACTIVE',
            is_deleted = 1,
            created_at = created_at, -- no cambia, solo explícito
            deleted_at = {now_sql}
        WHERE id = {P}
    """, (ally_id,))

    # Desactivar vínculos con admins
    cur.execute(f"""
        UPDATE admin_allies
        SET status = 'INACTIVE',
            is_active = 0,
            updated_at = {now_sql}
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


def update_ally_delivery_subsidy(ally_id: int, amount: int):
    """Actualiza el subsidio de domicilio del aliado (entero >= 0)."""
    if amount < 0:
        raise ValueError("delivery_subsidy no puede ser negativo")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE allies SET delivery_subsidy = {P} WHERE id = {P}", (amount, ally_id))
    conn.commit()
    conn.close()


def update_ally_min_purchase_for_subsidy(ally_id: int, amount):
    """Actualiza el monto mínimo de compra para aplicar subsidio. None = subsidio incondicional."""
    if amount is not None and amount < 0:
        raise ValueError("min_purchase_for_subsidy no puede ser negativo")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE allies SET min_purchase_for_subsidy = {P} WHERE id = {P}", (amount, ally_id))
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

from datetime import datetime, timezone

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
    cedula_front_file_id=None,
    cedula_back_file_id=None,
    selfie_file_id=None,
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
                residence_address, residence_lat, residence_lng,
                cedula_front_file_id, cedula_back_file_id, selfie_file_id
            )
            VALUES ({P}, {P}, {P}, {P}, {P}, {P}, 'PENDING', {now_sql}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P})
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
            cedula_front_file_id,
            cedula_back_file_id,
            selfie_file_id,
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
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
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
    cur.execute("SELECT COUNT(*) AS n FROM admins WHERE is_deleted=0")
    n = cur.fetchone()["n"]
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
        SELECT COUNT(*) AS n
        FROM admin_couriers
        WHERE admin_id={P}
    """, (admin_id,))
    n = cur.fetchone()["n"]
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
        SELECT COUNT(*) AS n
        FROM admin_couriers
        WHERE admin_id={P}
          AND balance >= {P}
    """, (admin_id, min_balance))
    n = cur.fetchone()["n"]
    conn.close()
    return n


def count_admin_allies(admin_id: int):
    """Cuenta el total de aliados vinculados al admin."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*) AS n
        FROM admin_allies
        WHERE admin_id = {P}
    """, (admin_id,))
    n = cur.fetchone()["n"]
    conn.close()
    return n


def count_admin_allies_with_min_balance(admin_id: int, min_balance: int = 5000):
    """Cuenta aliados del admin con saldo >= min_balance."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*) AS n
        FROM admin_allies
        WHERE admin_id = {P}
          AND balance >= {P}
    """, (admin_id, min_balance))
    n = cur.fetchone()["n"]
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
    if DB_ENGINE == "postgres":
        cur.execute(f"""
            INSERT INTO terms_acceptances (telegram_id, role, version, sha256, message_id)
            VALUES ({P}, {P}, {P}, {P}, {P})
            ON CONFLICT (telegram_id, role, version, sha256) DO NOTHING
        """, (telegram_id, role, version, sha256, message_id))
    else:
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
            ac.status AS link_status,
            ac.balance
        FROM admin_couriers ac
        JOIN admins a ON a.id = ac.admin_id
        WHERE ac.courier_id = {P}
          AND a.is_deleted = 0
        ORDER BY CASE WHEN ac.status = 'APPROVED' THEN 0 ELSE 1 END,
                 ac.updated_at DESC,
                 ac.created_at DESC,
                 ac.id DESC
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
            aa.status AS link_status,
            aa.balance
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    customer_id = _insert_returning_id(cur, f"""
        INSERT INTO ally_customers (ally_id, name, phone, notes, status, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, 'ACTIVE', {now_sql}, {now_sql})
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_customers
        SET name = {P}, phone = {P}, notes = {P}, updated_at = {now_sql}
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_customers
        SET status = 'INACTIVE', updated_at = {now_sql}
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_customers
        SET status = 'ACTIVE', updated_at = {now_sql}
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
    lng: float = None,
    require_coords: bool = True,
) -> int:
    """
    Crea una dirección para un cliente recurrente.
    Retorna el address_id creado.
    require_coords=False permite guardar sin coordenadas (ej. bandeja de formulario).
    """
    if require_coords and not has_valid_coords(lat, lng):
        raise ValueError("La direccion del cliente requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    address_id = _insert_returning_id(cur, f"""
        INSERT INTO ally_customer_addresses
        (customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'ACTIVE', {now_sql}, {now_sql})
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
    if not has_valid_coords(lat, lng):
        raise ValueError("La direccion del cliente requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_customer_addresses
        SET label = {P}, address_text = {P}, city = {P}, barrio = {P}, notes = {P}, lat = {P}, lng = {P},
            updated_at = {now_sql}
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_customer_addresses
        SET status = 'INACTIVE', updated_at = {now_sql}
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_customer_addresses
        SET status = 'ACTIVE', updated_at = {now_sql}
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
            ORDER BY COALESCE(use_count, 0) DESC, created_at DESC
        """, (customer_id,))
    else:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM ally_customer_addresses
            WHERE customer_id = {P} AND status = 'ACTIVE'
            ORDER BY COALESCE(use_count, 0) DESC, created_at DESC
        """, (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def increment_customer_address_usage(address_id: int, customer_id: int):
    """Incrementa use_count en ally_customer_addresses al seleccionar una direccion."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_customer_addresses
        SET use_count = COALESCE(use_count, 0) + 1, updated_at = {now_sql}
        WHERE id = {P} AND customer_id = {P} AND status = 'ACTIVE'
    """, (address_id, customer_id))
    conn.commit()
    conn.close()


def find_matching_customer_address(customer_id: int, address_text: str, city: str = None, barrio: str = None):
    """
    Busca una dirección activa del cliente que coincida tras normalización mínima
    (strip + lower + colapso de espacios). Compara address_text, city y barrio.
    Retorna dict de la dirección si hay match, None si no.
    """
    def _norm(v):
        if not v:
            return ""
        return re.sub(r'\s+', ' ', v.strip().lower())

    needle_addr = _norm(address_text)
    needle_city = _norm(city)
    needle_barrio = _norm(barrio)

    rows = list_customer_addresses(customer_id)
    for row in rows:
        if (
            _norm(row["address_text"]) == needle_addr
            and _norm(row["city"]) == needle_city
            and _norm(row["barrio"]) == needle_barrio
        ):
            return dict(row)
    return None


PARKING_FEE_AMOUNT = 1200  # Tarifa fija de parqueadero en COP


def set_address_parking_status(address_id: int, status: str, reviewed_by: int = None) -> bool:
    """Actualiza el estado de parqueadero de una direccion de cliente aliado.

    status validos: NOT_ASKED | ALLY_YES | PENDING_REVIEW | ADMIN_YES | ADMIN_NO
    reviewed_by: admins.id (solo cuando el admin hace la revision).
    """
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    if reviewed_by is not None:
        cur.execute(f"""
            UPDATE ally_customer_addresses
            SET parking_status = {P}, parking_reviewed_by = {P}, parking_reviewed_at = {now_sql},
                updated_at = {now_sql}
            WHERE id = {P} AND status = 'ACTIVE'
        """, (status, reviewed_by, address_id))
    else:
        cur.execute(f"""
            UPDATE ally_customer_addresses
            SET parking_status = {P}, updated_at = {now_sql}
            WHERE id = {P} AND status = 'ACTIVE'
        """, (status, address_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_addresses_pending_parking_review(admin_id) -> list:
    """Retorna direcciones de clientes aliados que necesitan revision de parqueadero.

    admin_id=None: admin de plataforma — retorna todos los aliados sin filtro de equipo.
    admin_id=int: admin local — solo aliados de su equipo (admin_allies.status=APPROVED).

    IMPORTANTE PRIVACIDAD: solo retorna datos geograficos (direccion, ciudad, barrio)
    y nombre del aliado. NO incluye nombre ni telefono del cliente.
    Incluye registros con parking_status: NOT_ASKED, ALLY_YES, PENDING_REVIEW.
    """
    conn = get_connection()
    cur = conn.cursor()
    if admin_id is None:
        cur.execute(f"""
            SELECT aca.id, aca.address_text, aca.city, aca.barrio, aca.parking_status,
                   aca.parking_reviewed_by, aca.parking_reviewed_at,
                   al.business_name AS ally_name
            FROM ally_customer_addresses aca
            JOIN ally_customers ac ON aca.customer_id = ac.id
            JOIN allies al ON ac.ally_id = al.id
            WHERE aca.status = 'ACTIVE'
              AND aca.parking_status IN ('NOT_ASKED', 'ALLY_YES', 'PENDING_REVIEW')
            ORDER BY aca.created_at DESC
            LIMIT 30
        """)
    else:
        cur.execute(f"""
            SELECT aca.id, aca.address_text, aca.city, aca.barrio, aca.parking_status,
                   aca.parking_reviewed_by, aca.parking_reviewed_at,
                   al.business_name AS ally_name
            FROM ally_customer_addresses aca
            JOIN ally_customers ac ON aca.customer_id = ac.id
            JOIN allies al ON ac.ally_id = al.id
            JOIN admin_allies aa ON aa.ally_id = al.id
                AND aa.admin_id = {P} AND aa.status = 'APPROVED'
            WHERE aca.status = 'ACTIVE'
              AND aca.parking_status IN ('NOT_ASKED', 'ALLY_YES', 'PENDING_REVIEW')
            ORDER BY aca.created_at DESC
            LIMIT 30
        """, (admin_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_addresses_parking_review(admin_id) -> list:
    """Retorna todas las direcciones (pendientes y revisadas) para consulta y correccion.

    admin_id=None: admin de plataforma — todos los aliados sin filtro de equipo.
    admin_id=int: admin local — solo aliados de su equipo.

    IMPORTANTE PRIVACIDAD: solo datos geograficos y nombre del aliado. Sin PII del cliente.
    """
    conn = get_connection()
    cur = conn.cursor()
    order_case = """
        ORDER BY
            CASE aca.parking_status
                WHEN 'ALLY_YES' THEN 1
                WHEN 'PENDING_REVIEW' THEN 2
                WHEN 'NOT_ASKED' THEN 3
                ELSE 4
            END,
            aca.created_at DESC
        LIMIT 50
    """
    if admin_id is None:
        cur.execute(f"""
            SELECT aca.id, aca.address_text, aca.city, aca.barrio, aca.parking_status,
                   aca.parking_reviewed_by, aca.parking_reviewed_at,
                   al.business_name AS ally_name
            FROM ally_customer_addresses aca
            JOIN ally_customers ac ON aca.customer_id = ac.id
            JOIN allies al ON ac.ally_id = al.id
            WHERE aca.status = 'ACTIVE'
            {order_case}
        """)
    else:
        cur.execute(f"""
            SELECT aca.id, aca.address_text, aca.city, aca.barrio, aca.parking_status,
                   aca.parking_reviewed_by, aca.parking_reviewed_at,
                   al.business_name AS ally_name
            FROM ally_customer_addresses aca
            JOIN ally_customers ac ON aca.customer_id = ac.id
            JOIN allies al ON ac.ally_id = al.id
            JOIN admin_allies aa ON aa.ally_id = al.id
                AND aa.admin_id = {P} AND aa.status = 'APPROVED'
            WHERE aca.status = 'ACTIVE'
            {order_case}
        """, (admin_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_customer_address_coords(address_id: int, customer_id: int, lat: float, lng: float) -> bool:
    """
    Actualiza solo las coordenadas de una dirección de cliente existente.
    Retorna True si se actualizó. No hace nada si las coords no son válidas.
    """
    if not has_valid_coords(lat, lng):
        return False
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE ally_customer_addresses
        SET lat = {P}, lng = {P}, updated_at = {now_sql}
        WHERE id = {P} AND customer_id = {P} AND status = 'ACTIVE'
    """, (lat, lng, address_id, customer_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# ============================================================
# CLIENTES RECURRENTES DEL ADMIN (admin_customers)
# ============================================================

def create_admin_customer(admin_id: int, name: str, phone: str, notes: str = None) -> int:
    """Crea un cliente recurrente para un admin. Retorna el customer_id creado."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    customer_id = _insert_returning_id(cur, f"""
        INSERT INTO admin_customers (admin_id, name, phone, notes, status, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, 'ACTIVE', {now_sql}, {now_sql})
    """, (admin_id, name.strip(), normalize_phone(phone), notes))
    conn.commit()
    conn.close()
    return customer_id


def update_admin_customer(customer_id: int, admin_id: int, name: str, phone: str, notes: str = None) -> bool:
    """Actualiza un cliente recurrente del admin (validando ownership). Retorna True si se actualizó."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_customers
        SET name = {P}, phone = {P}, notes = {P}, updated_at = {now_sql}
        WHERE id = {P} AND admin_id = {P} AND status = 'ACTIVE'
    """, (name.strip(), normalize_phone(phone), notes, customer_id, admin_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def archive_admin_customer(customer_id: int, admin_id: int) -> bool:
    """Archiva (soft delete) un cliente recurrente del admin. Retorna True si se archivó."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_customers
        SET status = 'INACTIVE', updated_at = {now_sql}
        WHERE id = {P} AND admin_id = {P} AND status = 'ACTIVE'
    """, (customer_id, admin_id))
    archived = cur.rowcount > 0
    conn.commit()
    conn.close()
    return archived


def restore_admin_customer(customer_id: int, admin_id: int) -> bool:
    """Restaura un cliente archivado del admin. Retorna True si se restauró."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_customers
        SET status = 'ACTIVE', updated_at = {now_sql}
        WHERE id = {P} AND admin_id = {P} AND status = 'INACTIVE'
    """, (customer_id, admin_id))
    restored = cur.rowcount > 0
    conn.commit()
    conn.close()
    return restored


def get_admin_customer_by_id(customer_id: int, admin_id: int = None):
    """Obtiene un cliente del admin por ID. Si se pasa admin_id, valida ownership."""
    conn = get_connection()
    cur = conn.cursor()
    if admin_id:
        cur.execute(f"""
            SELECT id, admin_id, name, phone, notes, status, created_at, updated_at
            FROM admin_customers
            WHERE id = {P} AND admin_id = {P}
        """, (customer_id, admin_id))
    else:
        cur.execute(f"""
            SELECT id, admin_id, name, phone, notes, status, created_at, updated_at
            FROM admin_customers
            WHERE id = {P}
        """, (customer_id,))
    row = cur.fetchone()
    conn.close()
    return row


def list_admin_customers(admin_id: int, limit: int = 20, include_inactive: bool = False):
    """Lista los clientes recurrentes de un admin (últimos primero)."""
    conn = get_connection()
    cur = conn.cursor()
    if include_inactive:
        cur.execute(f"""
            SELECT id, admin_id, name, phone, notes, status, created_at, updated_at
            FROM admin_customers
            WHERE admin_id = {P}
            ORDER BY updated_at DESC
            LIMIT {P}
        """, (admin_id, limit))
    else:
        cur.execute(f"""
            SELECT id, admin_id, name, phone, notes, status, created_at, updated_at
            FROM admin_customers
            WHERE admin_id = {P} AND status = 'ACTIVE'
            ORDER BY updated_at DESC
            LIMIT {P}
        """, (admin_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def search_admin_customers(admin_id: int, query: str, limit: int = 10):
    """Busca clientes del admin por nombre o teléfono (solo activos)."""
    conn = get_connection()
    cur = conn.cursor()
    search_term = f"%{query.strip()}%"
    cur.execute(f"""
        SELECT id, admin_id, name, phone, notes, status, created_at, updated_at
        FROM admin_customers
        WHERE admin_id = {P} AND status = 'ACTIVE'
          AND (name LIKE {P} OR phone LIKE {P})
        ORDER BY updated_at DESC
        LIMIT {P}
    """, (admin_id, search_term, search_term, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_admin_customer_by_phone(admin_id: int, phone: str):
    """Busca un cliente ACTIVO del admin por teléfono exacto (normalizado)."""
    phone_norm = normalize_phone(phone or "")
    if not phone_norm:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, admin_id, name, phone, notes, status, created_at, updated_at
        FROM admin_customers
        WHERE admin_id = {P} AND status = 'ACTIVE' AND phone = {P}
        LIMIT 1
    """, (admin_id, phone_norm))
    row = cur.fetchone()
    conn.close()
    return row


# ============================================================
# DIRECCIONES DE CLIENTES DEL ADMIN (admin_customer_addresses)
# ============================================================

def create_admin_customer_address(
    customer_id: int,
    label: str,
    address_text: str,
    city: str = None,
    barrio: str = None,
    notes: str = None,
    lat: float = None,
    lng: float = None,
) -> int:
    """Crea una dirección para un cliente del admin. Retorna el address_id creado."""
    if not has_valid_coords(lat, lng):
        raise ValueError("La direccion del cliente requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    address_id = _insert_returning_id(cur, f"""
        INSERT INTO admin_customer_addresses
        (customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'ACTIVE', {now_sql}, {now_sql})
    """, (customer_id, label, address_text.strip(), city, barrio, notes, lat, lng))
    conn.commit()
    conn.close()
    return address_id


def update_admin_customer_address(
    address_id: int,
    customer_id: int,
    label: str,
    address_text: str,
    city: str = None,
    barrio: str = None,
    notes: str = None,
    lat: float = None,
    lng: float = None,
) -> bool:
    """Actualiza una dirección de cliente del admin (validando ownership). Retorna True si se actualizó."""
    if not has_valid_coords(lat, lng):
        raise ValueError("La direccion del cliente requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_customer_addresses
        SET label = {P}, address_text = {P}, city = {P}, barrio = {P}, notes = {P},
            lat = {P}, lng = {P}, updated_at = {now_sql}
        WHERE id = {P} AND customer_id = {P} AND status = 'ACTIVE'
    """, (label, address_text.strip(), city, barrio, notes, lat, lng, address_id, customer_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def archive_admin_customer_address(address_id: int, customer_id: int) -> bool:
    """Archiva (soft delete) una dirección de cliente del admin. Retorna True si se archivó."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_customer_addresses
        SET status = 'INACTIVE', updated_at = {now_sql}
        WHERE id = {P} AND customer_id = {P} AND status = 'ACTIVE'
    """, (address_id, customer_id))
    archived = cur.rowcount > 0
    conn.commit()
    conn.close()
    return archived


def restore_admin_customer_address(address_id: int, customer_id: int) -> bool:
    """Restaura una dirección archivada de cliente del admin."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_customer_addresses
        SET status = 'ACTIVE', updated_at = {now_sql}
        WHERE id = {P} AND customer_id = {P} AND status = 'INACTIVE'
    """, (address_id, customer_id))
    restored = cur.rowcount > 0
    conn.commit()
    conn.close()
    return restored


def get_admin_customer_address_by_id(address_id: int, customer_id: int = None):
    """Obtiene una dirección de cliente del admin por ID. Si se pasa customer_id, valida ownership."""
    conn = get_connection()
    cur = conn.cursor()
    if customer_id:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM admin_customer_addresses
            WHERE id = {P} AND customer_id = {P}
        """, (address_id, customer_id))
    else:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM admin_customer_addresses
            WHERE id = {P}
        """, (address_id,))
    row = cur.fetchone()
    conn.close()
    return row


def list_admin_customer_addresses(customer_id: int, include_inactive: bool = False):
    """Lista las direcciones de un cliente del admin."""
    conn = get_connection()
    cur = conn.cursor()
    if include_inactive:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM admin_customer_addresses
            WHERE customer_id = {P}
            ORDER BY COALESCE(use_count, 0) DESC, created_at DESC
        """, (customer_id,))
    else:
        cur.execute(f"""
            SELECT id, customer_id, label, address_text, city, barrio, notes, lat, lng, status, created_at, updated_at
            FROM admin_customer_addresses
            WHERE customer_id = {P} AND status = 'ACTIVE'
            ORDER BY COALESCE(use_count, 0) DESC, created_at DESC
        """, (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def increment_admin_customer_address_usage(address_id: int, customer_id: int):
    """Incrementa use_count en admin_customer_addresses al seleccionar una direccion."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_customer_addresses
        SET use_count = COALESCE(use_count, 0) + 1, updated_at = {now_sql}
        WHERE id = {P} AND customer_id = {P} AND status = 'ACTIVE'
    """, (address_id, customer_id))
    conn.commit()
    conn.close()


# ============================================================
# GESTIÓN DE admin_locations (soft delete y edición)
# ============================================================

def archive_admin_location(location_id: int, admin_id: int) -> bool:
    """Archiva (soft delete) una dirección de recogida del admin. Retorna True si se archivó."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admin_locations
        SET status = 'INACTIVE'
        WHERE id = {P} AND admin_id = {P} AND status = 'ACTIVE'
    """, (location_id, admin_id))
    archived = cur.rowcount > 0
    conn.commit()
    conn.close()
    return archived


def update_admin_location(
    location_id: int,
    admin_id: int,
    label: str,
    address: str,
    city: str,
    barrio: str,
    phone: str = None,
    lat: float = None,
    lng: float = None,
) -> bool:
    """Actualiza una dirección de recogida del admin. Retorna True si se actualizó."""
    if not has_valid_coords(lat, lng):
        raise ValueError("La direccion de recogida requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE admin_locations
        SET label = {P}, address = {P}, city = {P}, barrio = {P}, phone = {P}, lat = {P}, lng = {P}
        WHERE id = {P} AND admin_id = {P} AND status = 'ACTIVE'
    """, (label, address, city, barrio, phone, lat, lng, location_id, admin_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


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


def get_recent_delivery_addresses_for_ally(ally_id: int, limit: int = 5):
    """
    Retorna las últimas N direcciones de entrega únicas usadas por el aliado,
    desde pedidos completados o activos. Útil para sugerir reutilización.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT customer_address, customer_city, customer_barrio, dropoff_lat, dropoff_lng
        FROM orders
        WHERE ally_id = {P}
          AND customer_address IS NOT NULL
          AND customer_address != ''
          AND dropoff_lat IS NOT NULL
          AND dropoff_lng IS NOT NULL
        GROUP BY customer_address, customer_city, customer_barrio
        ORDER BY MAX(id) DESC
        LIMIT {P}
    """, (ally_id, limit))
    rows = cur.fetchall()
    conn.close()
    return rows


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
            "raw_link": row["raw_link"],
            "expanded_link": row["expanded_link"],
            "lat": row["lat"],
            "lng": row["lng"],
            "formatted_address": row["formatted_address"],
            "provider": row["provider"],
            "place_id": row["place_id"],
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
        "distance_km": row["distance_km"],
        "provider": row["provider"],
    }


def upsert_distance_cache(origin_key: str, destination_key: str, mode: str, distance_km: float, provider: str):
    """Inserta/actualiza distancia cacheada por origen/destino y modo."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        INSERT INTO map_distance_cache (origin_key, destination_key, mode, distance_km, provider, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, {P}, {now_sql}, {now_sql})
        ON CONFLICT(origin_key, destination_key, mode) DO UPDATE SET
          distance_km = excluded.distance_km,
          provider = COALESCE(excluded.provider, map_distance_cache.provider),
          updated_at = {now_sql}
    """, (origin_key, destination_key, mode, distance_km, provider))
    conn.commit()
    conn.close()


# ---------- GEOCODING TEXT CACHE ----------

def get_geocoding_text_cache(text_key: str):
    """
    Busca coordenadas cacheadas para un texto normalizado de dirección.
    Retorna dict con lat/lng/formatted_address/place_id/source o None si no hay hit.
    También incrementa hit_count para poder auditar qué entradas se usan más.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT lat, lng, formatted_address, place_id, source
        FROM geocoding_text_cache
        WHERE text_key = {P}
        LIMIT 1
    """, (text_key,))
    row = cur.fetchone()
    if row:
        now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
        try:
            cur.execute(f"""
                UPDATE geocoding_text_cache
                SET hit_count = hit_count + 1, updated_at = {now_sql}
                WHERE text_key = {P}
            """, (text_key,))
            conn.commit()
        except Exception:
            pass
    conn.close()
    if not row:
        return None
    return {
        "lat": row["lat"],
        "lng": row["lng"],
        "formatted_address": row["formatted_address"],
        "place_id": row["place_id"],
        "source": row["source"],
    }


def upsert_geocoding_text_cache(text_key: str, lat: float, lng: float,
                                formatted_address: str = None, place_id: str = None,
                                source: str = None):
    """
    Inserta o actualiza la entrada de caché para un texto de dirección.
    Idempotente: si ya existe, actualiza lat/lng y metadata.
    """
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        INSERT INTO geocoding_text_cache
            (text_key, lat, lng, formatted_address, place_id, source, hit_count, created_at, updated_at)
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, 1, {now_sql}, {now_sql})
        ON CONFLICT(text_key) DO UPDATE SET
            lat = excluded.lat,
            lng = excluded.lng,
            formatted_address = COALESCE(excluded.formatted_address, geocoding_text_cache.formatted_address),
            place_id = COALESCE(excluded.place_id, geocoding_text_cache.place_id),
            source = COALESCE(excluded.source, geocoding_text_cache.source),
            updated_at = {now_sql}
    """, (text_key, lat, lng, formatted_address, place_id, source))
    conn.commit()
    conn.close()


# ---------- API USAGE DAILY (FUSIBLE) ----------

def get_api_usage_today(api_name: str) -> int:
    """Retorna el número de llamadas hoy para una API."""
    today_sql = "CURRENT_DATE::text" if DB_ENGINE == "postgres" else "date('now')"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT call_count FROM api_usage_daily
        WHERE api_name = {P} AND usage_date = {today_sql}
    """, (api_name,))
    row = cur.fetchone()
    conn.close()
    return int(_row_value(row, "call_count", 0, 0) or 0)


def increment_api_usage(api_name: str):
    """Incrementa el contador de uso diario para una API."""
    today_sql = "CURRENT_DATE::text" if DB_ENGINE == "postgres" else "date('now')"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO api_usage_daily (api_name, usage_date, call_count)
        VALUES ({P}, {today_sql}, 1)
        ON CONFLICT(api_name, usage_date) DO UPDATE SET
          call_count = api_usage_daily.call_count + 1
    """, (api_name,))
    conn.commit()
    conn.close()


# ---------- API USAGE EVENTS (COST TRACKING) ----------
def record_api_usage_event(
    api_name: str,
    api_operation: str,
    *,
    success: bool = True,
    blocked: bool = False,
    units: int = 1,
    units_kind: str = "call",
    cost_usd: float = 0.0,
    http_status: int = None,
    provider_status: str = None,
    error_message: str = None,
    meta: dict = None,
):
    """
    Registra un evento de uso de API (con estimación de costo) y también incrementa api_usage_daily
    de forma atómica.
    """
    if not api_name or not api_operation:
        return
    today_sql = "CURRENT_DATE::text" if DB_ENGINE == "postgres" else "date('now')"
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    meta_json = None
    if meta is not None:
        try:
            import json
            meta_json = json.dumps(meta, ensure_ascii=False)
        except Exception:
            meta_json = None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("BEGIN")
    try:
        cur.execute(
            f"""
                INSERT INTO api_usage_events
                    (api_name, api_operation, usage_date, success, blocked, units, units_kind,
                     cost_usd, http_status, provider_status, error_message, meta_json, created_at)
                VALUES
                    ({P}, {P}, {today_sql}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {now_sql})
            """,
            (
                api_name,
                api_operation,
                1 if success else 0,
                1 if blocked else 0,
                int(units or 0),
                units_kind or "call",
                float(cost_usd or 0.0),
                http_status,
                provider_status,
                error_message,
                meta_json,
            ),
        )

        cur.execute(
            f"""
                INSERT INTO api_usage_daily (api_name, usage_date, call_count)
                VALUES ({P}, {today_sql}, 1)
                ON CONFLICT(api_name, usage_date) DO UPDATE SET
                  call_count = api_usage_daily.call_count + 1
            """,
            (api_name,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_api_usage_cost_summary(api_name: str, date_from: str, date_to: str):
    """
    Resumen por operación (count, total_cost_usd, avg_cost_usd) entre fechas inclusivas (YYYY-MM-DD).
    """
    if not api_name or not date_from or not date_to:
        return []
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
            SELECT
              api_operation,
              COUNT(*) AS events,
              SUM(cost_usd) AS total_cost_usd,
              AVG(cost_usd) AS avg_cost_usd,
              SUM(CASE WHEN blocked = 1 THEN 1 ELSE 0 END) AS blocked_events,
              SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS success_events
            FROM api_usage_events
            WHERE api_name = {P}
              AND usage_date >= {P}
              AND usage_date <= {P}
            GROUP BY api_operation
            ORDER BY events DESC
        """,
        (api_name, date_from, date_to),
    )
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows or []:
        results.append(
            {
                "api_operation": _row_value(r, "api_operation", None, 0),
                "events": int(_row_value(r, "events", 0, 1) or 0),
                "total_cost_usd": float(_row_value(r, "total_cost_usd", 0.0, 2) or 0.0),
                "avg_cost_usd": float(_row_value(r, "avg_cost_usd", 0.0, 3) or 0.0),
                "blocked_events": int(_row_value(r, "blocked_events", 0, 4) or 0),
                "success_events": int(_row_value(r, "success_events", 0, 5) or 0),
            }
        )
    return results


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
    return int(_row_value(row, "balance", 0, 0) or 0)




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


def register_platform_income(admin_id: int, amount: int, method: str, note: str = None) -> int:
    """
    Registra un ingreso externo recibido por el Admin de Plataforma
    (efectivo, Nequi, transferencia bancaria, etc.).
    Incrementa admins.balance y genera entrada en ledger:
        kind=INCOME, from_type=EXTERNAL, from_id=0, to_type=ADMIN, to_id=admin_id
    Retorna: ledger_id
    """
    full_note = "Ingreso externo registrado manualmente. Metodo: {}".format(method)
    if note:
        full_note += ". Nota: {}".format(note)
    return update_admin_balance_with_ledger(
        admin_id=admin_id,
        delta=amount,
        kind="INCOME",
        note=full_note,
        ref_type=None,
        ref_id=None,
        from_type="EXTERNAL",
        from_id=0,
    )


def settle_route_additional_stops_fee(
    route_id: int,
    ally_id: int,
    admin_id: int,
    platform_admin_id: int,
    amount: int,
) -> Tuple[bool, str]:
    """
    Liquida el additional_stops_fee de una ruta cobrando al saldo operativo del aliado
    y acreditando el ingreso a admin/plataforma en una sola transaccion.
    """
    amount_int = int(amount or 0)
    if amount_int <= 0:
        return False, "La ruta no tiene additional_stops_fee para liquidar."

    note_prefix = "Ruta additional_stops_fee"
    is_platform_owner = admin_id == platform_admin_id
    admin_share = 0 if is_platform_owner else amount_int // 2
    platform_share = amount_int if is_platform_owner else amount_int - admin_share

    conn = get_connection()
    cur = conn.cursor()
    try:
        if DB_ENGINE == "sqlite":
            cur.execute("BEGIN IMMEDIATE")
        else:
            cur.execute("BEGIN")

        cur.execute(
            f"""
            SELECT 1
            FROM ledger
            WHERE ref_type = {P}
              AND ref_id = {P}
              AND note LIKE {P}
            LIMIT 1
            """,
            ("ROUTE", route_id, note_prefix + "%"),
        )
        if cur.fetchone():
            conn.rollback()
            return False, "La ruta ya tenia liquidado el additional_stops_fee."

        cur.execute(
            f"""
            SELECT balance
            FROM admin_allies
            WHERE ally_id = {P} AND admin_id = {P}
            """,
            (ally_id, admin_id),
        )
        row = cur.fetchone()
        current_balance = int(_row_value(row, "balance", 0, 0) or 0)
        if current_balance < amount_int:
            conn.rollback()
            return False, "Saldo insuficiente. Balance: ${:,}, requerido: ${:,}.".format(current_balance, amount_int)

        cur.execute(
            f"""
            UPDATE admin_allies
            SET balance = balance - {P}, updated_at = {"NOW()" if DB_ENGINE == "postgres" else "datetime('now')"}
            WHERE ally_id = {P} AND admin_id = {P}
              AND balance >= {P}
            """,
            (amount_int, ally_id, admin_id, amount_int),
        )
        if cur.rowcount != 1:
            conn.rollback()
            return False, "Saldo insuficiente. Balance: ${:,}, requerido: ${:,}.".format(current_balance, amount_int)

        for target_admin_id, share, kind, note in (
            (
                admin_id,
                admin_share,
                "FEE_INCOME",
                "{} admin ruta #{}".format(note_prefix, route_id),
            ),
            (
                platform_admin_id,
                platform_share,
                "PLATFORM_FEE",
                "{} plataforma ruta #{}".format(note_prefix, route_id),
            ),
        ):
            if share <= 0:
                continue

            cur.execute(f"SELECT id FROM admins WHERE id = {P}", (target_admin_id,))
            if not cur.fetchone():
                conn.rollback()
                raise ValueError(f"Admin id={target_admin_id} no existe.")

            cur.execute(
                f"UPDATE admins SET balance = balance + {P} WHERE id = {P}",
                (share, target_admin_id),
            )
            _insert_returning_id(
                cur,
                f"""
                INSERT INTO ledger
                    (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note)
                VALUES ({P}, 'ALLY', {P}, 'ADMIN', {P}, {P}, {P}, {P}, {P})
                """,
                (kind, ally_id, target_admin_id, share, "ROUTE", route_id, note),
            )

        conn.commit()
        return True, "Liquidacion de ruta aplicada."
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
    return int(_row_value(row, "balance", 0, 0) or 0)


def update_courier_link_balance(courier_id: int, admin_id: int, delta: int):
    """Actualiza el saldo del vínculo courier-admin."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_couriers SET balance = balance + {P}, updated_at = {now_sql}
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
    return int(_row_value(row, "balance", 0, 0) or 0)


def update_ally_link_balance(ally_id: int, admin_id: int, delta: int):
    """Actualiza el saldo del vínculo ally-admin."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE admin_allies SET balance = balance + {P}, updated_at = {now_sql}
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


def credit_welcome_balance(user_type: str, target_id: int, admin_id: int, amount: int = 5000) -> bool:
    """
    Acredita saldo de bienvenida a un COURIER o ALLY (en su vínculo con admin)
    y registra el movimiento en ledger de forma atómica.

    Retorna True si fue exitoso, False si falló.
    """
    user_type = (user_type or "").strip().upper()
    if user_type not in ("COURIER", "ALLY"):
        return False
    if not target_id or not admin_id:
        return False
    if amount is None or int(amount) <= 0:
        return False

    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    conn = get_connection()
    cur = conn.cursor()
    try:
        if DB_ENGINE == "sqlite":
            cur.execute("BEGIN IMMEDIATE")
        else:
            cur.execute("BEGIN")

        grant_id = None
        try:
            grant_id = _insert_returning_id(
                cur,
                f"""
                    INSERT INTO welcome_bonus_grants (
                        role_type, role_id, granted_by_admin_id, amount
                    ) VALUES ({P}, {P}, {P}, {P})
                """,
                (user_type, int(target_id), int(admin_id), int(amount)),
            )
        except _IntegrityError:
            conn.rollback()
            return False

        if user_type == "COURIER":
            cur.execute(
                f"UPDATE admin_couriers SET balance = balance + {P}, updated_at = {now_sql} "
                f"WHERE courier_id = {P} AND admin_id = {P}",
                (int(amount), int(target_id), int(admin_id)),
            )
        else:
            cur.execute(
                f"UPDATE admin_allies SET balance = balance + {P}, updated_at = {now_sql} "
                f"WHERE ally_id = {P} AND admin_id = {P}",
                (int(amount), int(target_id), int(admin_id)),
            )

        if cur.rowcount != 1:
            conn.rollback()
            return False

        ledger_id = _insert_returning_id(
            cur,
            "INSERT INTO ledger (kind, from_type, from_id, to_type, to_id, amount, ref_type, ref_id, note) "
            "VALUES (" + ", ".join([P] * 9) + ")",
            (
                "WELCOME_BONUS",
                "PLATFORM",
                0,
                user_type,
                int(target_id),
                int(amount),
                "WELCOME_BONUS",
                int(grant_id),
                "Bienvenida: recarga inicial de regalo",
            ),
        )

        cur.execute(
            f"UPDATE welcome_bonus_grants SET ledger_id = {P} WHERE id = {P}",
            (int(ledger_id), int(grant_id)),
        )

        conn.commit()
        return True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error("credit_welcome_balance: %s", e)
        return False
    finally:
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


def list_all_pending_recharges(limit=50):
    """Lista todas las solicitudes PENDING de todos los admins con nombre de admin y destinatario."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT rr.id, rr.target_type, rr.target_id, rr.amount, rr.method, rr.created_at,
               COALESCE(a.team_name, a.full_name) AS admin_name,
               rr.admin_id,
               CASE
                   WHEN rr.target_type = 'COURIER' THEN c.full_name
                   WHEN rr.target_type = 'ALLY'    THEN al.business_name
                   WHEN rr.target_type = 'ADMIN'   THEN COALESCE(ad2.team_name, ad2.full_name)
                   ELSE 'Desconocido'
               END AS target_name,
               rr.proof_file_id
        FROM recharge_requests rr
        JOIN admins a ON a.id = rr.admin_id
        LEFT JOIN couriers c  ON rr.target_type = 'COURIER' AND rr.target_id = c.id
        LEFT JOIN allies al   ON rr.target_type = 'ALLY'    AND rr.target_id = al.id
        LEFT JOIN admins ad2  ON rr.target_type = 'ADMIN'   AND rr.target_id = ad2.id
        WHERE rr.status = 'PENDING'
        ORDER BY rr.created_at ASC
        LIMIT {P}
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_admins_with_pending_count():
    """
    Retorna todos los admins locales APPROVED con su conteo de solicitudes PENDING
    y su balance. Incluye telegram_id del usuario para poder notificarlos.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT a.id AS admin_id,
               COALESCE(a.team_name, a.full_name) AS admin_name,
               a.status,
               a.balance,
               u.telegram_id,
               COUNT(rr.id) AS pending_count
        FROM admins a
        JOIN users u ON u.id = a.user_id
        LEFT JOIN recharge_requests rr ON rr.admin_id = a.id AND rr.status = 'PENDING'
        WHERE a.is_deleted = 0
          AND a.team_code != 'PLATFORM'
          AND a.status = 'APPROVED'
        GROUP BY a.id, a.full_name, a.team_name, a.status, a.balance, u.telegram_id
        ORDER BY pending_count DESC, a.balance ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def list_recharge_ledger(limit=20, offset=0):
    """Ultimas entradas del ledger tipo RECHARGE con nombres de origen y destino."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT l.id, l.from_type, l.from_id, l.to_type, l.to_id,
               l.amount, l.ref_id, l.note, l.created_at,
               CASE l.from_type
                   WHEN 'PLATFORM' THEN (SELECT COALESCE(team_name, full_name) FROM admins WHERE id = l.from_id)
                   WHEN 'ADMIN'    THEN (SELECT COALESCE(team_name, full_name) FROM admins WHERE id = l.from_id)
                   WHEN 'EXTERNAL' THEN 'Externo'
                   ELSE l.from_type
               END AS from_name,
               CASE l.to_type
                   WHEN 'COURIER'  THEN (SELECT full_name      FROM couriers WHERE id = l.to_id)
                   WHEN 'ALLY'     THEN (SELECT business_name  FROM allies   WHERE id = l.to_id)
                   WHEN 'ADMIN'    THEN (SELECT COALESCE(team_name, full_name) FROM admins WHERE id = l.to_id)
                   WHEN 'PLATFORM' THEN (SELECT COALESCE(team_name, full_name) FROM admins WHERE id = l.to_id)
                   ELSE l.to_type
               END AS to_name
        FROM ledger l
        WHERE l.kind = 'RECHARGE'
        ORDER BY l.created_at DESC
        LIMIT {P} OFFSET {P}
    """, (limit, offset))
    rows = cur.fetchall()
    conn.close()
    return rows


def update_recharge_status(request_id: int, status: str, decided_by_admin_id: int):
    """Actualiza el status de una solicitud (APPROVED/REJECTED)."""
    status = normalize_role_status(status)
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE recharge_requests
        SET status = {P}, decided_by_admin_id = {P}, decided_at = {now_sql}
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


def _coerce_datetime(value=None) -> datetime:
    """Convierte timestamp DB/ISO a datetime naive UTC."""
    if value is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(value, datetime):
        return value
    raw = str(value).strip()
    if not raw:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    raw = raw.replace("T", " ").replace("Z", "")
    raw = raw.split("+")[0]
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _week_window_from_datetime(reference_at=None):
    ref = _coerce_datetime(reference_at)
    week_start = (ref - timedelta(days=ref.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    iso_year, iso_week, _ = week_start.isocalendar()
    week_key = f"{iso_year}-W{iso_week:02d}"
    return week_key, week_start, week_end


def _week_window_from_key(week_key: str):
    try:
        year_part, week_part = week_key.split("-W")
        iso_year = int(year_part)
        iso_week = int(week_part)
    except Exception as exc:
        raise ValueError(f"week_key invalido: {week_key}. Formato esperado: YYYY-Www") from exc
    week_start = datetime.fromisocalendar(iso_year, iso_week, 1)
    week_end = week_start + timedelta(days=7)
    normalized_key = f"{iso_year}-W{iso_week:02d}"
    return normalized_key, week_start, week_end


def get_or_create_accounting_week(reference_at=None, week_key: str = None):
    """
    Obtiene o crea semana contable.
    - week_key esperado: YYYY-Www
    - si no se envía week_key, se calcula por referencia (UTC naive)
    """
    if week_key:
        normalized_key, week_start, week_end = _week_window_from_key(week_key)
    else:
        normalized_key, week_start, week_end = _week_window_from_datetime(reference_at)

    week_start_s = week_start.strftime("%Y-%m-%d %H:%M:%S")
    week_end_s = week_end.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO accounting_weeks (week_key, week_start_at, week_end_at, status)
        VALUES ({P}, {P}, {P}, 'OPEN')
        ON CONFLICT(week_key) DO NOTHING
    """, (normalized_key, week_start_s, week_end_s))
    conn.commit()
    cur.execute(f"""
        SELECT id, week_key, week_start_at, week_end_at, status, closed_at, closed_by
        FROM accounting_weeks
        WHERE week_key = {P}
        LIMIT 1
    """, (normalized_key,))
    row = cur.fetchone()
    conn.close()
    return row


def list_accounting_weeks(limit: int = 12, offset: int = 0):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, week_key, week_start_at, week_end_at, status, closed_at, closed_by, created_at
        FROM accounting_weeks
        ORDER BY week_start_at DESC
        LIMIT {P} OFFSET {P}
    """, (limit, offset))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_courier_daily_earnings_history(courier_id: int, days: int = 7):
    """
    Historial diario de ganancias del repartidor usando liquidaciones contables.
    Retorna lista con:
    - date_key (YYYY-MM-DD), order_id, delivered_at, customer_name,
      gross_amount, platform_fee, net_amount
    """
    if days < 1:
        days = 1
    end_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    start_dt = (end_dt - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    start_s = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_s = (end_dt + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

    return _get_courier_earnings_between(courier_id, start_s, end_s)


def _get_courier_earnings_between(courier_id: int, start_s: str, end_s: str):
    platform_fee = int(get_setting("fee_service_total", "300") or 300)

    conn = get_connection()
    cur = conn.cursor()

    # Pedidos individuales entregados
    cur.execute(f"""
        SELECT
            id AS order_id,
            delivered_at,
            customer_name,
            COALESCE(total_fee, 0) AS gross_amount,
            'order' AS kind
        FROM orders
        WHERE courier_id = {P}
          AND status = 'DELIVERED'
          AND delivered_at IS NOT NULL
          AND delivered_at >= {P}
          AND delivered_at < {P}
    """, (courier_id, start_s, end_s))
    order_rows = cur.fetchall()

    # Rutas entregadas
    cur.execute(f"""
        SELECT
            id AS order_id,
            delivered_at,
            NULL AS customer_name,
            COALESCE(total_fee, 0) AS gross_amount,
            'route' AS kind
        FROM routes
        WHERE courier_id = {P}
          AND status = 'DELIVERED'
          AND delivered_at IS NOT NULL
          AND delivered_at >= {P}
          AND delivered_at < {P}
    """, (courier_id, start_s, end_s))
    route_rows = cur.fetchall()

    conn.close()

    result = []
    for row in list(order_rows) + list(route_rows):
        kind = _row_value(row, "kind", 4, "order") or "order"
        order_id = int(_row_value(row, "order_id", 0, 0) or 0)
        delivered_at = _row_value(row, "delivered_at", 1, "") or ""
        raw_name = _row_value(row, "customer_name", 2, None)
        if kind == "route":
            customer_name = "Ruta #{}".format(order_id)
        else:
            customer_name = raw_name or "N/A"
        gross_amount = int(_row_value(row, "gross_amount", 3, 0) or 0)
        net_amount = gross_amount - platform_fee
        date_key = str(delivered_at)[:10] if delivered_at else "-"
        hour_key = str(delivered_at)[11:16] if delivered_at else "--:--"

        result.append({
            "date_key": date_key,
            "hour_key": hour_key,
            "order_id": order_id,
            "delivered_at": delivered_at,
            "customer_name": customer_name,
            "gross_amount": gross_amount,
            "platform_fee": platform_fee,
            "net_amount": net_amount,
        })

    result.sort(key=lambda r: r["delivered_at"] or "", reverse=True)
    return result


def get_courier_earnings_by_date(courier_id: int, date_key: str):
    """
    Ganancias del repartidor para una fecha exacta (YYYY-MM-DD).
    """
    try:
        dt = datetime.strptime((date_key or "").strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Fecha inválida. Usa formato YYYY-MM-DD.") from exc

    start_s = dt.strftime("%Y-%m-%d 00:00:00")
    end_s = (dt + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    return _get_courier_earnings_between(courier_id, start_s, end_s)


def get_courier_earnings_between(courier_id: int, start_s: str, end_s: str):
    """Ganancias del repartidor en un rango de timestamps arbitrario."""
    return _get_courier_earnings_between(courier_id, start_s, end_s)


def get_admin_balance_breakdown(admin_id: int) -> dict:
    """
    Desglose del saldo master del admin para el mes en curso.
    Retorna: fees_mes, fees_total, ingresos_mes, recargas_mes, subs_mes, mes_inicio.
    Compatible SQLite y PostgreSQL (usa comparación de strings para fechas).
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    mes_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    mes_start_s = mes_start.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()

    # Fees del mes (FEE_INCOME + PLATFORM_FEE como receptor)
    cur.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM ledger"
        f" WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE') AND to_type = 'ADMIN' AND to_id = {P}"
        f" AND created_at >= {P}",
        (admin_id, mes_start_s),
    )
    fees_mes = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0

    # Fees acumulados totales
    cur.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM ledger"
        f" WHERE kind IN ('FEE_INCOME', 'PLATFORM_FEE') AND to_type = 'ADMIN' AND to_id = {P}",
        (admin_id,),
    )
    fees_total = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0

    # Ingresos externos del mes
    cur.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM ledger"
        f" WHERE kind = 'INCOME' AND to_type = 'ADMIN' AND to_id = {P}"
        f" AND created_at >= {P}",
        (admin_id, mes_start_s),
    )
    ingresos_mes = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0

    # Recargas aprobadas salidas del mes (el admin es el origen)
    cur.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM ledger"
        f" WHERE kind = 'RECHARGE' AND from_type IN ('ADMIN', 'PLATFORM') AND from_id = {P}"
        f" AND created_at >= {P}",
        (admin_id, mes_start_s),
    )
    recargas_mes = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0

    # Ganancias por suscripciones del mes
    cur.execute(
        f"SELECT COALESCE(SUM(amount), 0) FROM ledger"
        f" WHERE kind IN ('SUBSCRIPTION_PLATFORM_SHARE', 'SUBSCRIPTION_ADMIN_SHARE')"
        f" AND to_type = 'ADMIN' AND to_id = {P} AND created_at >= {P}",
        (admin_id, mes_start_s),
    )
    subs_mes = _row_value(cur.fetchone(), "COALESCE(SUM(amount), 0)", 0, 0) or 0

    conn.close()
    return {
        "fees_mes": fees_mes,
        "fees_total": fees_total,
        "ingresos_mes": ingresos_mes,
        "recargas_mes": recargas_mes,
        "subs_mes": subs_mes,
        "mes_inicio": mes_start_s[:7],
    }


def get_admin_ledger_movements(admin_id: int, start_s: str = None, end_s: str = None, limit: int = 30) -> list:
    """
    Movimientos del ledger del admin: entradas donde el admin recibe (to_id)
    o envía (from_id) dinero. Ordenados por fecha DESC.
    """
    conn = get_connection()
    cur = conn.cursor()

    date_filter = ""
    date_params = []
    if start_s:
        date_filter += f" AND created_at >= {P}"
        date_params.append(start_s)
    if end_s:
        date_filter += f" AND created_at < {P}"
        date_params.append(end_s)

    params = [admin_id, admin_id] + date_params + [limit]
    cur.execute(
        f"SELECT id, kind, amount, from_type, from_id, to_type, to_id, note, created_at"
        f" FROM ledger"
        f" WHERE ("
        f"   (to_type = 'ADMIN' AND to_id = {P})"
        f"   OR (from_type IN ('ADMIN', 'PLATFORM') AND from_id = {P})"
        f" ){date_filter}"
        f" ORDER BY created_at DESC"
        f" LIMIT {P}",
        params,
    )
    rows = cur.fetchall()
    conn.close()

    result = []
    for r in rows:
        to_type = _row_value(r, "to_type", 5, "") or ""
        to_id_val = _row_value(r, "to_id", 6, 0) or 0
        direction = "IN" if (to_type == "ADMIN" and to_id_val == admin_id) else "OUT"
        result.append({
            "id": _row_value(r, "id", 0),
            "kind": _row_value(r, "kind", 1, "") or "",
            "amount": _row_value(r, "amount", 2, 0) or 0,
            "from_type": _row_value(r, "from_type", 3, "") or "",
            "from_id": _row_value(r, "from_id", 4, 0) or 0,
            "to_type": to_type,
            "to_id": to_id_val,
            "note": _row_value(r, "note", 7, "") or "",
            "created_at": str(_row_value(r, "created_at", 8, "")) or "",
            "direction": direction,
        })
    return result


def close_accounting_week(week_key: str, closed_by: str = "SYSTEM") -> bool:
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE accounting_weeks
        SET status = 'CLOSED', closed_at = {now_sql}, closed_by = {P}
        WHERE week_key = {P} AND status = 'OPEN'
    """, (closed_by, week_key))
    changed = cur.rowcount > 0
    conn.commit()
    conn.close()
    return changed


def record_accounting_event(
    event_type: str,
    amount: int,
    from_type: str = None,
    from_id: int = None,
    to_type: str = None,
    to_id: int = None,
    entity_type: str = None,
    entity_id: int = None,
    admin_id: int = None,
    order_id: int = None,
    ledger_id: int = None,
    created_at=None,
    note: str = None,
) -> int:
    """
    Registra evento contable normalizado y lo asigna a semana contable.
    amount debe ser positivo.
    """
    if amount is None or int(amount) < 0:
        raise ValueError("amount debe ser >= 0")
    amount_int = int(amount)
    week = get_or_create_accounting_week(reference_at=created_at)
    week_key = week["week_key"] if hasattr(week, "keys") else week[1]
    event_created_at = _coerce_datetime(created_at).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()
    event_id = _insert_returning_id(cur, f"""
        INSERT INTO accounting_events (
            week_key, event_type, from_type, from_id, to_type, to_id,
            entity_type, entity_id, admin_id, order_id, ledger_id, amount, note, created_at
        )
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P})
    """, (
        week_key, event_type, from_type, from_id, to_type, to_id,
        entity_type, entity_id, admin_id, order_id, ledger_id, amount_int, note, event_created_at
    ))
    conn.commit()
    conn.close()
    return event_id


def upsert_order_accounting_settlement(
    order_id: int,
    admin_id: int,
    ally_id: int,
    courier_id: int,
    order_total_fee: int,
    ally_fee_expected: int,
    ally_fee_charged: int,
    courier_fee_expected: int,
    courier_fee_charged: int,
    note: str = None,
    delivered_at=None,
):
    """
    Guarda liquidacion por pedido para separar devengado vs cobrado.
    settlement_status: OPEN | PARTIAL | SETTLED
    """
    delivered_dt = _coerce_datetime(delivered_at)
    week = get_or_create_accounting_week(reference_at=delivered_dt)
    week_key = week["week_key"] if hasattr(week, "keys") else week[1]
    delivered_at_s = delivered_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"

    ally_expected = int(ally_fee_expected or 0)
    courier_expected = int(courier_fee_expected or 0)
    ally_charged = int(ally_fee_charged or 0)
    courier_charged = int(courier_fee_charged or 0)
    total_expected = ally_expected + courier_expected
    total_charged = ally_charged + courier_charged
    if total_charged >= total_expected and total_expected > 0:
        status = "SETTLED"
    elif total_charged > 0:
        status = "PARTIAL"
    else:
        status = "OPEN"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO order_accounting_settlements (
            order_id, week_key, admin_id, ally_id, courier_id, order_total_fee,
            ally_fee_expected, ally_fee_charged, courier_fee_expected, courier_fee_charged,
            settlement_status, note, delivered_at, created_at, updated_at
        )
        VALUES (
            {P}, {P}, {P}, {P}, {P}, {P},
            {P}, {P}, {P}, {P},
            {P}, {P}, {P}, {now_sql}, {now_sql}
        )
        ON CONFLICT(order_id) DO UPDATE SET
            week_key = excluded.week_key,
            admin_id = excluded.admin_id,
            ally_id = excluded.ally_id,
            courier_id = excluded.courier_id,
            order_total_fee = excluded.order_total_fee,
            ally_fee_expected = excluded.ally_fee_expected,
            ally_fee_charged = excluded.ally_fee_charged,
            courier_fee_expected = excluded.courier_fee_expected,
            courier_fee_charged = excluded.courier_fee_charged,
            settlement_status = excluded.settlement_status,
            note = excluded.note,
            delivered_at = excluded.delivered_at,
            updated_at = {now_sql}
    """, (
        order_id, week_key, admin_id, ally_id, courier_id, int(order_total_fee or 0),
        ally_expected, ally_charged, courier_expected, courier_charged,
        status, note, delivered_at_s
    ))
    conn.commit()
    conn.close()


def get_weekly_platform_accounting_summary(week_key: str, platform_admin_id: int):
    """Resumen semanal de ingresos plataforma."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN event_type = 'SERVICE_FEE_CHARGED' AND to_type = 'ADMIN' AND to_id = {P}
                    THEN amount ELSE 0
                END
            ), 0) AS platform_direct_fee_income,
            COALESCE(SUM(
                CASE
                    WHEN event_type = 'PLATFORM_COMMISSION_CHARGED' AND to_type = 'ADMIN' AND to_id = {P}
                    THEN amount ELSE 0
                END
            ), 0) AS platform_commission_income
        FROM accounting_events
        WHERE week_key = {P}
    """, (platform_admin_id, platform_admin_id, week_key))
    row = cur.fetchone()
    conn.close()
    return row


def get_weekly_courier_settlement_summary(week_key: str, courier_id: int = None):
    """Resumen semanal por repartidor desde liquidacion de pedidos."""
    conn = get_connection()
    cur = conn.cursor()
    query = f"""
        SELECT
            courier_id,
            COUNT(*) AS delivered_orders,
            COALESCE(SUM(order_total_fee), 0) AS gross_income,
            COALESCE(SUM(courier_fee_charged), 0) AS platform_fee_charged,
            COALESCE(SUM(order_total_fee), 0) - COALESCE(SUM(courier_fee_charged), 0) AS net_estimated_income,
            COALESCE(SUM(CASE WHEN settlement_status = 'SETTLED' THEN 1 ELSE 0 END), 0) AS settled_orders,
            COALESCE(SUM(CASE WHEN settlement_status = 'PARTIAL' THEN 1 ELSE 0 END), 0) AS partial_orders,
            COALESCE(SUM(CASE WHEN settlement_status = 'OPEN' THEN 1 ELSE 0 END), 0) AS open_orders
        FROM order_accounting_settlements
        WHERE week_key = {P}
    """
    params = [week_key]
    if courier_id is not None:
        query += f" AND courier_id = {P}"
        params.append(courier_id)
    query += " GROUP BY courier_id ORDER BY gross_income DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def upsert_accounting_week_snapshot_metric(
    week_key: str,
    scope_type: str,
    scope_id: int,
    metric_key: str,
    metric_value: int,
):
    """Guarda/actualiza metrica congelada de semana."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO accounting_week_snapshots (week_key, scope_type, scope_id, metric_key, metric_value)
        VALUES ({P}, {P}, {P}, {P}, {P})
        ON CONFLICT(week_key, scope_type, scope_id, metric_key)
        DO UPDATE SET metric_value = excluded.metric_value
    """, (week_key, scope_type, int(scope_id), metric_key, int(metric_value)))
    conn.commit()
    conn.close()


def list_accounting_week_snapshots(week_key: str, scope_type: str = None, scope_id: int = None):
    conn = get_connection()
    cur = conn.cursor()
    query = f"""
        SELECT id, week_key, scope_type, scope_id, metric_key, metric_value, created_at
        FROM accounting_week_snapshots
        WHERE week_key = {P}
    """
    params = [week_key]
    if scope_type is not None:
        query += f" AND scope_type = {P}"
        params.append(scope_type)
    if scope_id is not None:
        query += f" AND scope_id = {P}"
        params.append(int(scope_id))
    query += " ORDER BY scope_type ASC, scope_id ASC, metric_key ASC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


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


def get_platform_sociedad():
    """Obtiene la entidad contable de la Sociedad (team_code='SOCIEDAD')."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, full_name, team_name, team_code, balance
        FROM admins
        WHERE team_code = 'SOCIEDAD' AND is_deleted = 0
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
            "payment_phone": row["payment_phone"],
            "payment_bank": row["payment_bank"],
            "payment_holder": row["payment_holder"],
            "payment_instructions": row["payment_instructions"],
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
        ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'PENDING', {P}, {P}, {"NOW()" if DB_ENGINE == "postgres" else "datetime('now')"});
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
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE profile_change_requests
        SET status = 'APPROVED',
            reviewed_by_user_id = {P},
            reviewed_by_admin_id = {P},
            reviewed_at = {now_sql}
        WHERE id = {P}
    """, (reviewer_user_id, reviewer_admin_id, request_id))
    conn.commit()
    conn.close()


def mark_profile_change_request_rejected(request_id, reviewer_user_id, reviewer_admin_id, reason):
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        UPDATE profile_change_requests
        SET status = 'REJECTED',
            reviewed_by_user_id = {P},
            reviewed_by_admin_id = {P},
            reviewed_at = {now_sql},
            rejection_reason = {P}
        WHERE id = {P}
    """, (reviewer_user_id, reviewer_admin_id, reason, request_id))
    conn.commit()
    conn.close()


def _upsert_default_ally_location_for_profile_change(cur, ally_id, address, lat, lng):
    cur.execute(f"""
        UPDATE ally_locations
        SET lat = {P}, lng = {P}, address = {P}
        WHERE ally_id = {P} AND is_default = 1
    """, (lat, lng, address, ally_id))
    if cur.rowcount > 0:
        return

    cur.execute(f"""
        SELECT city, barrio
        FROM allies
        WHERE id = {P}
    """, (ally_id,))
    ally = cur.fetchone()
    city = ally["city"] if ally and ally["city"] else ""
    barrio = ally["barrio"] if ally and ally["barrio"] else ""
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(f"""
        INSERT INTO ally_locations (
            ally_id, label, address, city, barrio, is_default, lat, lng, created_at
        )
        VALUES ({P}, 'Principal', {P}, {P}, {P}, 1, {P}, {P}, {now_sql})
    """, (ally_id, address, city, barrio, lat, lng))


def apply_profile_change_request_data(target_role, target_role_id, field_name, new_value, new_lat, new_lng):
    conn = get_connection()
    cur = conn.cursor()

    if target_role == "admin":
        if field_name == "phone":
            cur.execute(f"UPDATE admins SET phone = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "city":
            cur.execute(f"UPDATE admins SET city = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "barrio":
            cur.execute(f"UPDATE admins SET barrio = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "residence_address":
            cur.execute(f"UPDATE admins SET residence_address = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "residence_location":
            cur.execute(
                f"UPDATE admins SET residence_lat = {P}, residence_lng = {P} WHERE id = {P}",
                (new_lat, new_lng, target_role_id),
            )
    elif target_role == "courier":
        if field_name == "phone":
            cur.execute(f"UPDATE couriers SET phone = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "city":
            cur.execute(f"UPDATE couriers SET city = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "barrio":
            cur.execute(f"UPDATE couriers SET barrio = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "plate":
            cur.execute(f"UPDATE couriers SET plate = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "bike_type":
            cur.execute(f"UPDATE couriers SET bike_type = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "residence_address":
            cur.execute(f"UPDATE couriers SET residence_address = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "residence_location":
            cur.execute(
                f"UPDATE couriers SET residence_lat = {P}, residence_lng = {P} WHERE id = {P}",
                (new_lat, new_lng, target_role_id),
            )
    elif target_role == "ally":
        if field_name == "phone":
            cur.execute(f"UPDATE allies SET phone = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "city":
            cur.execute(f"UPDATE allies SET city = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "barrio":
            cur.execute(f"UPDATE allies SET barrio = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "address":
            cur.execute(f"UPDATE allies SET address = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "business_name":
            cur.execute(f"UPDATE allies SET business_name = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "owner_name":
            cur.execute(f"UPDATE allies SET owner_name = {P} WHERE id = {P}", (new_value, target_role_id))
        elif field_name == "ally_default_location":
            _upsert_default_ally_location_for_profile_change(
                cur,
                ally_id=target_role_id,
                address=new_value,
                lat=new_lat,
                lng=new_lng,
            )

    conn.commit()
    conn.close()


# ===== RUTAS MULTI-PARADA =====


def create_route(ally_id, pickup_location_id, pickup_address, pickup_lat, pickup_lng,
                 total_distance_km, distance_fee, additional_stops_fee, total_fee,
                 instructions, ally_admin_id_snapshot):
    """Crea una ruta. Retorna el route_id."""
    if not has_valid_coords(pickup_lat, pickup_lng):
        raise ValueError("La recogida de la ruta requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    route_id = _insert_returning_id(
        cur,
        f"""
        INSERT INTO routes (
            ally_id, pickup_location_id, pickup_address, pickup_lat, pickup_lng,
            total_distance_km, distance_fee, additional_stops_fee, total_fee,
            instructions, ally_admin_id_snapshot, status
        ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'PENDING')
        """,
        (ally_id, pickup_location_id, pickup_address, pickup_lat, pickup_lng,
         total_distance_km, distance_fee, additional_stops_fee, total_fee,
         instructions, ally_admin_id_snapshot),
    )
    conn.commit()
    conn.close()
    return route_id


def create_route_destination(route_id, sequence, customer_name, customer_phone,
                              customer_address, customer_city, customer_barrio,
                              dropoff_lat=None, dropoff_lng=None):
    """Inserta una parada de ruta. Retorna el destination_id."""
    if not has_valid_coords(dropoff_lat, dropoff_lng):
        raise ValueError("La parada de la ruta requiere ubicacion confirmada.")
    conn = get_connection()
    cur = conn.cursor()
    dest_id = _insert_returning_id(
        cur,
        f"""
        INSERT INTO route_destinations (
            route_id, sequence, customer_name, customer_phone,
            customer_address, customer_city, customer_barrio,
            dropoff_lat, dropoff_lng, status
        ) VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, 'PENDING')
        """,
        (route_id, sequence, customer_name, customer_phone,
         customer_address, customer_city, customer_barrio,
         dropoff_lat, dropoff_lng),
    )
    conn.commit()
    conn.close()
    return dest_id


def get_route_by_id(route_id):
    """Retorna la ruta o None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM routes WHERE id = {P}", (route_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_routes_by_ally(ally_id):
    """Retorna rutas activas (PUBLISHED o ACCEPTED) del aliado."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM routes WHERE ally_id = {P} AND status IN ('PUBLISHED', 'ACCEPTED') ORDER BY created_at DESC",
        (ally_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_route_destinations(route_id):
    """Lista todas las paradas de la ruta ordenadas por sequence."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM route_destinations WHERE route_id = {P} ORDER BY sequence ASC",
        (route_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def reorder_route_destinations(route_id, ordered_ids):
    """Reasigna sequence 1..N a las paradas segun la lista ordered_ids.

    ordered_ids: lista de destination.id en el nuevo orden deseado.
    """
    conn = get_connection()
    cur = conn.cursor()
    for new_seq, dest_id in enumerate(ordered_ids, 1):
        cur.execute(
            f"UPDATE route_destinations SET sequence = {P} WHERE id = {P} AND route_id = {P}",
            (new_seq, dest_id, route_id),
        )
    conn.commit()
    conn.close()


def get_pending_route_stops(route_id):
    """Lista las paradas PENDING de la ruta, ordenadas por sequence."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM route_destinations WHERE route_id = {P} AND status = 'PENDING' ORDER BY sequence ASC",
        (route_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_route_status(route_id, status, timestamp_field=None):
    """Actualiza el status de una ruta y opcionalmente un campo timestamp."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    if timestamp_field:
        cur.execute(
            f"UPDATE routes SET status = {P}, {timestamp_field} = {now_sql} WHERE id = {P}",
            (status, route_id)
        )
    else:
        cur.execute(f"UPDATE routes SET status = {P} WHERE id = {P}", (status, route_id))
    conn.commit()
    conn.close()


def assign_route_to_courier(route_id, courier_id, courier_admin_id_snapshot):
    """Asigna un courier a la ruta y la marca como ACCEPTED."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"""
        UPDATE routes
        SET courier_id = {P}, courier_admin_id_snapshot = {P},
            status = 'ACCEPTED', accepted_at = {now_sql}
        WHERE id = {P}
        """,
        (courier_id, courier_admin_id_snapshot, route_id)
    )
    conn.commit()
    conn.close()


def release_route_from_courier(route_id):
    """Libera una ruta aceptada: limpia courier y la vuelve a publicar (PUBLISHED)."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"""
        UPDATE routes
        SET courier_id = NULL,
            courier_admin_id_snapshot = NULL,
            status = 'PUBLISHED',
            accepted_at = NULL,
            published_at = {now_sql}
        WHERE id = {P}
        """,
        (route_id,),
    )
    conn.commit()
    conn.close()


def deliver_route_stop(route_id, sequence):
    """Marca una parada como DELIVERED."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"""
        UPDATE route_destinations
        SET status = 'DELIVERED', delivered_at = {now_sql}
        WHERE route_id = {P} AND sequence = {P}
        """,
        (route_id, sequence)
    )
    conn.commit()
    conn.close()


def cancel_route(route_id, canceled_by):
    """Cancela una ruta."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"""
        UPDATE routes
        SET status = 'CANCELLED', canceled_at = {now_sql}, canceled_by = {P}
        WHERE id = {P}
        """,
        (canceled_by, route_id)
    )
    conn.commit()
    conn.close()


def create_route_offer_queue(route_id, courier_ids):
    """Crea entradas en la cola de ofertas de la ruta."""
    conn = get_connection()
    cur = conn.cursor()
    for pos, courier_id in enumerate(courier_ids, start=1):
        cur.execute(
            f"""
            INSERT INTO route_offer_queue (route_id, courier_id, position, status)
            VALUES ({P}, {P}, {P}, 'PENDING')
            """,
            (route_id, courier_id, pos)
        )
    conn.commit()
    conn.close()


def get_next_pending_route_offer(route_id):
    """Retorna el proximo courier pendiente en la cola de la ruta."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT q.id AS queue_id, q.courier_id, q.position, u.telegram_id
        FROM route_offer_queue q
        JOIN couriers c ON c.id = q.courier_id
        JOIN users u ON u.id = c.user_id
        WHERE q.route_id = {P} AND q.status = 'PENDING'
        ORDER BY q.position ASC
        LIMIT 1
        """,
        (route_id,)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def mark_route_offer_as_offered(queue_id):
    """Marca una oferta de ruta como enviada."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"UPDATE route_offer_queue SET status = 'OFFERED', offered_at = {now_sql} WHERE id = {P}",
        (queue_id,)
    )
    conn.commit()
    conn.close()


def mark_route_offer_response(queue_id, response):
    """Marca la respuesta de una oferta de ruta (ACCEPTED, REJECTED, EXPIRED, BUSY)."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"""
        UPDATE route_offer_queue
        SET status = {P}, response = {P}, responded_at = {now_sql}
        WHERE id = {P}
        """,
        (response, response, queue_id)
    )
    conn.commit()
    conn.close()


def get_current_route_offer(route_id):
    """Retorna la oferta activa (OFFERED) de la ruta."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT q.id AS queue_id, q.courier_id, q.position, u.telegram_id
        FROM route_offer_queue q
        JOIN couriers c ON c.id = q.courier_id
        JOIN users u ON u.id = c.user_id
        WHERE q.route_id = {P} AND q.status = 'OFFERED'
        LIMIT 1
        """,
        (route_id,)
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_route_offer_queue(route_id):
    """Borra toda la cola de ofertas de una ruta."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM route_offer_queue WHERE route_id = {P}", (route_id,))
    conn.commit()
    conn.close()


def reset_route_offer_queue(route_id):
    """Reinicia todos los estados de la cola a PENDING para un nuevo ciclo."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE route_offer_queue
        SET status = 'PENDING', offered_at = NULL, responded_at = NULL, response = NULL
        WHERE route_id = {P}
        """,
        (route_id,)
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# order_support_requests — solicitudes de ayuda por pin mal ubicado
# ---------------------------------------------------------------------------

def create_order_support_request(courier_id: int, admin_id: int,
                                  order_id: int = None, route_id: int = None,
                                  route_seq: int = None) -> int:
    """Crea una solicitud de ayuda. Retorna el id generado."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    support_id = _insert_returning_id(
        cur,
        f"""
        INSERT INTO order_support_requests
            (order_id, route_id, route_seq, courier_id, admin_id, status, created_at)
        VALUES ({P}, {P}, {P}, {P}, {P}, 'PENDING', {now_sql})
        """,
        (order_id, route_id, route_seq, courier_id, admin_id),
    )
    conn.commit()
    conn.close()
    return support_id


def get_pending_support_request(order_id: int = None, route_id: int = None,
                                 route_seq: int = None):
    """Retorna la solicitud PENDING para un pedido o parada de ruta."""
    conn = get_connection()
    cur = conn.cursor()
    if order_id is not None:
        cur.execute(
            f"SELECT * FROM order_support_requests WHERE order_id = {P} AND status = 'PENDING' LIMIT 1",
            (order_id,)
        )
    else:
        cur.execute(
            f"""SELECT * FROM order_support_requests
                WHERE route_id = {P} AND route_seq = {P} AND status = 'PENDING' LIMIT 1""",
            (route_id, route_seq)
        )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def resolve_support_request(support_id: int, resolution: str, resolved_by: int) -> bool:
    """Marca la solicitud como resuelta. Retorna True si se actualizó."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"""
        UPDATE order_support_requests
        SET status = 'RESOLVED', resolution = {P}, resolved_at = {now_sql}, resolved_by = {P}
        WHERE id = {P} AND status = 'PENDING'
        """,
        (resolution, resolved_by, support_id)
    )
    ok = cur.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def cancel_route_stop(route_id: int, seq: int, resolution: str):
    """Marca una parada de ruta como cancelada (CANCELLED_COURIER o CANCELLED_ALLY)."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"""
        UPDATE route_destinations
        SET status = {P}, delivered_at = {now_sql}
        WHERE route_id = {P} AND sequence = {P} AND status = 'PENDING'
        """,
        (resolution, route_id, seq)
    )
    conn.commit()
    conn.close()


def get_all_pending_support_requests():
    """Retorna todas las solicitudes PENDING con datos JOIN para panel web."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            sr.id, sr.order_id, sr.route_id, sr.route_seq,
            sr.courier_id, sr.admin_id, sr.status, sr.resolution,
            sr.created_at, sr.resolved_at,
            c.full_name  AS courier_name,
            c.phone      AS courier_phone,
            u.telegram_id AS courier_telegram_id,
            c.live_lat   AS courier_lat,
            c.live_lng   AS courier_lng,
            o.customer_address AS delivery_address,
            o.customer_name    AS customer_name,
            o.customer_phone   AS customer_phone,
            o.status           AS order_status,
            o.dropoff_lat,
            o.dropoff_lng,
            a.full_name  AS admin_name
        FROM order_support_requests sr
        LEFT JOIN couriers c ON c.id = sr.courier_id
        LEFT JOIN users u ON u.id = c.user_id
        LEFT JOIN orders o ON o.id = sr.order_id
        LEFT JOIN admins a ON a.id = sr.admin_id
        WHERE sr.status = 'PENDING'
        ORDER BY sr.created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_support_request_full(support_id: int):
    """Retorna una solicitud con todos sus datos JOIN para panel web."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            sr.id, sr.order_id, sr.route_id, sr.route_seq,
            sr.courier_id, sr.admin_id, sr.status, sr.resolution,
            sr.created_at, sr.resolved_at, sr.resolved_by,
            c.full_name  AS courier_name,
            c.phone      AS courier_phone,
            u.telegram_id AS courier_telegram_id,
            c.live_lat   AS courier_lat,
            c.live_lng   AS courier_lng,
            o.customer_address AS delivery_address,
            o.customer_name    AS customer_name,
            o.customer_phone   AS customer_phone,
            o.status           AS order_status,
            o.dropoff_lat,
            o.dropoff_lng,
            a.full_name  AS admin_name
        FROM order_support_requests sr
        LEFT JOIN couriers c ON c.id = sr.courier_id
        LEFT JOIN users u ON u.id = c.user_id
        LEFT JOIN orders o ON o.id = sr.order_id
        LEFT JOIN admins a ON a.id = sr.admin_id
        WHERE sr.id = {P}
    """, (support_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# Funciones: ally_form_requests (enlace público del aliado)
# ============================================================

def get_or_create_ally_public_token(ally_id: int) -> str:
    """Retorna el public_token del aliado, creándolo si no existe."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT public_token FROM allies WHERE id = {P}", (ally_id,))
    row = cur.fetchone()
    if row:
        token = _row_value(row, 'public_token')
        if token:
            conn.close()
            return token
    token = str(uuid.uuid4())
    cur.execute(f"UPDATE allies SET public_token = {P} WHERE id = {P}", (token, ally_id))
    conn.commit()
    conn.close()
    return token


def get_ally_by_public_token(token: str):
    """Retorna el aliado APPROVED asociado al token público."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT id, user_id, business_name, owner_name, address, city, barrio, phone, status,
               public_token, delivery_subsidy, min_purchase_for_subsidy
        FROM allies
        WHERE public_token = {P} AND status = 'APPROVED'
    """, (token,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


_ALLY_FORM_REQUEST_VALID_STATUSES = {
    'PENDING_REVIEW', 'PENDING_LOCATION', 'SAVED_CONTACT', 'CONVERTED_ORDER', 'DISMISSED'
}


def create_ally_form_request(ally_id: int, customer_name: str, customer_phone: str,
                              delivery_address: str = None, delivery_city: str = None,
                              delivery_barrio: str = None, notes: str = None,
                              lat: float = None, lng: float = None,
                              status: str = 'PENDING_REVIEW',
                              quoted_price: float = None,
                              subsidio_aliado: int = None,
                              incentivo_cliente: int = None,
                              total_cliente: int = None,
                              purchase_amount_declared: int = None) -> int:
    """Crea una solicitud en la bandeja temporal del aliado. Retorna el ID."""
    if status not in _ALLY_FORM_REQUEST_VALID_STATUSES:
        raise ValueError(f"status inválido: {status!r}. Válidos: {_ALLY_FORM_REQUEST_VALID_STATUSES}")
    conn = get_connection()
    cur = conn.cursor()
    sql = f"""
        INSERT INTO ally_form_requests
            (ally_id, customer_name, customer_phone, delivery_address, delivery_city,
             delivery_barrio, notes, lat, lng, status, quoted_price,
             subsidio_aliado, incentivo_cliente, total_cliente, purchase_amount_declared)
        VALUES ({P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P}, {P})
    """
    row_id = _insert_returning_id(cur, sql, (
        ally_id, customer_name, customer_phone,
        delivery_address, delivery_city, delivery_barrio,
        notes, lat, lng, status, quoted_price,
        subsidio_aliado, incentivo_cliente, total_cliente,
        purchase_amount_declared
    ))
    conn.commit()
    conn.close()
    return row_id


def get_ally_form_request_by_id(request_id: int, ally_id: int = None):
    """Retorna una solicitud por ID. Si se pasa ally_id, valida ownership."""
    conn = get_connection()
    cur = conn.cursor()
    if ally_id:
        cur.execute(f"""
            SELECT id, ally_id, customer_name, customer_phone, delivery_address,
                   delivery_city, delivery_barrio, notes, lat, lng, status,
                   quoted_price, subsidio_aliado, incentivo_cliente, total_cliente,
                   purchase_amount_declared, order_id, created_at, updated_at
            FROM ally_form_requests
            WHERE id = {P} AND ally_id = {P}
        """, (request_id, ally_id))
    else:
        cur.execute(f"""
            SELECT id, ally_id, customer_name, customer_phone, delivery_address,
                   delivery_city, delivery_barrio, notes, lat, lng, status,
                   quoted_price, subsidio_aliado, incentivo_cliente, total_cliente,
                   purchase_amount_declared, order_id, created_at, updated_at
            FROM ally_form_requests
            WHERE id = {P}
        """, (request_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_ally_form_request_status(request_id: int, ally_id: int, status: str) -> bool:
    """
    Actualiza el estado de una solicitud de formulario.
    status: PENDING_REVIEW | PENDING_LOCATION | SAVED_CONTACT | CONVERTED_ORDER | DISMISSED
    """
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_form_requests
        SET status = {P}, updated_at = {now_sql}
        WHERE id = {P} AND ally_id = {P}
    """, (status, request_id, ally_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def mark_ally_form_request_converted(request_id: int, ally_id: int, order_id: int) -> bool:
    """
    Marca una solicitud de formulario como CONVERTED_ORDER y guarda el order_id del pedido creado.
    Valida ownership por ally_id. Idempotente: no sobreescribe si ya está CONVERTED_ORDER.
    Retorna True si actualizó algo.
    """
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE ally_form_requests
        SET status = 'CONVERTED_ORDER', order_id = {P}, updated_at = {now_sql}
        WHERE id = {P} AND ally_id = {P} AND status != 'CONVERTED_ORDER'
    """, (order_id, request_id, ally_id))
    updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def list_ally_form_requests_for_ally(ally_id: int, status=None, limit: int = 20):
    """
    Lista las solicitudes de bandeja del aliado (más recientes primero).
    status: None → todos | str → un estado | list → varios estados (IN)
    """
    conn = get_connection()
    cur = conn.cursor()
    select = f"""
        SELECT id, ally_id, customer_name, customer_phone, delivery_address,
               delivery_city, delivery_barrio, notes, lat, lng, status,
               quoted_price, subsidio_aliado, incentivo_cliente, total_cliente,
               purchase_amount_declared, order_id, created_at, updated_at
        FROM ally_form_requests
    """
    if status is None:
        cur.execute(select + f"WHERE ally_id = {P} ORDER BY created_at DESC LIMIT {P}", (ally_id, limit))
    elif isinstance(status, list):
        placeholders = ", ".join([P] * len(status))
        cur.execute(
            select + f"WHERE ally_id = {P} AND status IN ({placeholders}) ORDER BY created_at DESC LIMIT {P}",
            tuple([ally_id] + status + [limit])
        )
    else:
        cur.execute(
            select + f"WHERE ally_id = {P} AND status = {P} ORDER BY created_at DESC LIMIT {P}",
            (ally_id, status, limit)
        )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_ally_form_requests_by_status(ally_id: int) -> dict:
    """Retorna {status: count} para todas las solicitudes del aliado. Statuses sin registros no aparecen."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT status, COUNT(*) as cnt FROM ally_form_requests WHERE ally_id = {P} GROUP BY status",
        (ally_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return {_row_value(r, 'status'): int(_row_value(r, 'cnt')) for r in rows}

# ============================================================
# SUSCRIPCIONES MENSUALES DE ALIADOS
# ============================================================

def set_ally_subscription_price(admin_id: int, ally_id: int, price: int):
    """Configura el precio mensual de suscripcion para un aliado gestionado por este admin."""
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"UPDATE admin_allies SET subscription_price = {P}, updated_at = {now_sql}"
        f" WHERE admin_id = {P} AND ally_id = {P}",
        (price, admin_id, ally_id),
    )
    conn.commit()
    conn.close()


def get_ally_subscription_price(admin_id: int, ally_id: int):
    """Retorna el precio de suscripcion configurado para este aliado, o None si no tiene."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT subscription_price FROM admin_allies WHERE admin_id = {P} AND ally_id = {P}",
        (admin_id, ally_id),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return _row_value(row, "subscription_price")


def create_ally_subscription(ally_id: int, admin_id: int, price: int,
                              platform_share: int, admin_share: int):
    """
    Crea un nuevo ciclo de suscripcion de 30 dias para el aliado.
    Retorna el id generado.
    """
    conn = get_connection()
    cur = conn.cursor()
    if DB_ENGINE == "postgres":
        starts_sql = "NOW()"
        expires_sql = "NOW() + INTERVAL '30 days'"
        cur.execute(
            f"INSERT INTO ally_subscriptions"
            f" (ally_id, admin_id, price, platform_share, admin_share, starts_at, expires_at, status)"
            f" VALUES ({P}, {P}, {P}, {P}, {P}, {starts_sql}, {expires_sql}, 'ACTIVE')"
            f" RETURNING id",
            (ally_id, admin_id, price, platform_share, admin_share),
        )
        row = cur.fetchone()
        new_id = _row_value(row, "id")
    else:
        cur.execute(
            f"INSERT INTO ally_subscriptions"
            f" (ally_id, admin_id, price, platform_share, admin_share,"
            f"  starts_at, expires_at, status)"
            f" VALUES ({P}, {P}, {P}, {P}, {P},"
            f"  datetime('now'), datetime('now', '+30 days'), 'ACTIVE')",
            (ally_id, admin_id, price, platform_share, admin_share),
        )
        new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def get_active_ally_subscription(ally_id: int):
    """
    Retorna la suscripcion ACTIVE del aliado si existe y no ha expirado, o None.
    """
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"SELECT * FROM ally_subscriptions"
        f" WHERE ally_id = {P} AND status = 'ACTIVE' AND expires_at > {now_sql}"
        f" ORDER BY expires_at DESC LIMIT 1",
        (ally_id,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def expire_old_ally_subscriptions():
    """
    Marca como EXPIRED las suscripciones ACTIVE cuya expires_at ya paso.
    Llamar al arranque del bot (en main()).
    """
    conn = get_connection()
    cur = conn.cursor()
    now_sql = "NOW()" if DB_ENGINE == "postgres" else "datetime('now')"
    cur.execute(
        f"UPDATE ally_subscriptions SET status = 'EXPIRED'"
        f" WHERE status = 'ACTIVE' AND expires_at <= {now_sql}",
    )
    changed = cur.rowcount
    conn.commit()
    conn.close()
    if changed:
        logger.info("%s suscripcion(es) marcadas como EXPIRED.", changed)
    return changed


def get_ally_subscription_info(ally_id: int):
    """
    Retorna la suscripcion mas reciente del aliado (activa o no), o None.
    Util para mostrar estado en el bot.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM ally_subscriptions WHERE ally_id = {P}"
        f" ORDER BY created_at DESC LIMIT 1",
        (ally_id,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# SCHEDULED JOBS — persistencia de timers del bot
# ============================================================

def upsert_scheduled_job(job_name: str, callback_name: str, fire_at: str, job_data_json: str):
    """Inserta o reemplaza un job programado. fire_at es ISO timestamp string."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    if DB_ENGINE == "postgres":
        cur.execute(
            """
            INSERT INTO scheduled_jobs (job_name, callback_name, fire_at, job_data, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 'PENDING', %s, %s)
            ON CONFLICT (job_name) DO UPDATE SET
                callback_name = EXCLUDED.callback_name,
                fire_at = EXCLUDED.fire_at,
                job_data = EXCLUDED.job_data,
                status = 'PENDING',
                updated_at = EXCLUDED.updated_at
            """,
            (job_name, callback_name, fire_at, job_data_json, now, now),
        )
    else:
        cur.execute(
            """
            INSERT OR REPLACE INTO scheduled_jobs
                (job_name, callback_name, fire_at, job_data, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
            """,
            (job_name, callback_name, fire_at, job_data_json, now, now),
        )
    conn.commit()
    conn.close()


def cancel_scheduled_job(job_name: str):
    """Marca un job como CANCELLED en la BD."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    cur.execute(
        f"UPDATE scheduled_jobs SET status = 'CANCELLED', updated_at = {P} WHERE job_name = {P}",
        (now, job_name),
    )
    conn.commit()
    conn.close()


def mark_job_executed(job_name: str):
    """Marca un job como EXECUTED en la BD."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    cur.execute(
        f"UPDATE scheduled_jobs SET status = 'EXECUTED', updated_at = {P} WHERE job_name = {P}",
        (now, job_name),
    )
    conn.commit()
    conn.close()


def get_pending_scheduled_jobs():
    """Retorna todos los jobs en estado PENDING para reprogramar tras reinicio."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM scheduled_jobs WHERE status = 'PENDING'")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
