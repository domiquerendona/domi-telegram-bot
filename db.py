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
