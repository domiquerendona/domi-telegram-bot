-- ============================================================
-- POSTGRES SCHEMA FOR DOMIQUERENDONA BOT
-- Migración desde SQLite - Fase 2.1
-- ============================================================

-- ============================================================
-- A) TABLAS BASE
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    role TEXT,
    person_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admins (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    person_id BIGINT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    city TEXT NOT NULL,
    barrio TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    team_name TEXT,
    document_number TEXT,
    team_code TEXT,
    rejection_type TEXT,
    rejection_reason TEXT,
    rejected_at TIMESTAMP,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS couriers (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    person_id BIGINT,
    full_name TEXT NOT NULL,
    id_number TEXT NOT NULL,
    phone TEXT NOT NULL,
    city TEXT NOT NULL,
    barrio TEXT NOT NULL,
    plate TEXT,
    bike_type TEXT,
    code TEXT,
    status TEXT DEFAULT 'PENDING',
    balance NUMERIC DEFAULT 0,
    free_orders_remaining INTEGER DEFAULT 15,
    rejection_type TEXT,
    rejection_reason TEXT,
    rejected_at TIMESTAMP,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TIMESTAMP,
    live_lat REAL,
    live_lng REAL,
    live_location_active INTEGER DEFAULT 0,
    live_location_updated_at TIMESTAMP,
    availability_status TEXT DEFAULT 'OFFLINE',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS allies (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    person_id BIGINT,
    business_name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    barrio TEXT NOT NULL,
    phone TEXT NOT NULL,
    document_number TEXT,
    status TEXT DEFAULT 'PENDING',
    rejection_type TEXT,
    rejection_reason TEXT,
    rejected_at TIMESTAMP,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- B) TABLAS AUXILIARES
-- ============================================================

CREATE TABLE IF NOT EXISTS identities (
    id BIGSERIAL PRIMARY KEY,
    phone TEXT NOT NULL,
    document_number TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, role)
);

-- ============================================================
-- C) TABLAS DE CONFIGURACIÓN
-- ============================================================

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- D) TABLAS DE RELACIONES
-- ============================================================

CREATE TABLE IF NOT EXISTS ally_locations (
    id BIGSERIAL PRIMARY KEY,
    ally_id BIGINT NOT NULL,
    label TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    barrio TEXT NOT NULL,
    phone TEXT,
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_allies (
    id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL,
    ally_id BIGINT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    balance INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(admin_id, ally_id)
);

CREATE TABLE IF NOT EXISTS admin_couriers (
    id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL,
    courier_id BIGINT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    balance INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(admin_id, courier_id)
);

-- ============================================================
-- E) TABLAS DE PEDIDOS
-- ============================================================

CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    ally_id BIGINT NOT NULL,
    courier_id BIGINT,
    status TEXT DEFAULT 'PENDING',
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_address TEXT NOT NULL,
    customer_city TEXT NOT NULL,
    customer_barrio TEXT NOT NULL,
    pickup_location_id BIGINT,
    pay_at_store_required INTEGER DEFAULT 0,
    pay_at_store_amount INTEGER DEFAULT 0,
    base_fee INTEGER DEFAULT 0,
    distance_km NUMERIC DEFAULT 0,
    rain_extra INTEGER DEFAULT 0,
    high_demand_extra INTEGER DEFAULT 0,
    night_extra INTEGER DEFAULT 0,
    additional_incentive INTEGER DEFAULT 0,
    total_fee INTEGER DEFAULT 0,
    instructions TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,
    accepted_at TIMESTAMP,
    pickup_confirmed_at TIMESTAMP,
    delivered_at TIMESTAMP,
    canceled_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courier_ratings (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    courier_id BIGINT NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- F) TABLAS DE TÉRMINOS Y CONDICIONES
-- ============================================================

CREATE TABLE IF NOT EXISTS terms_versions (
    id BIGSERIAL PRIMARY KEY,
    role TEXT NOT NULL,
    version TEXT NOT NULL,
    url TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    status TEXT DEFAULT 'APPROVED',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(role, version)
);

CREATE TABLE IF NOT EXISTS terms_acceptances (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    role TEXT NOT NULL,
    version TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    message_id BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(telegram_id, role, version, sha256)
);

CREATE TABLE IF NOT EXISTS terms_session_acks (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    role TEXT NOT NULL,
    version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- G) ÍNDICES
-- ============================================================

-- Identities
CREATE UNIQUE INDEX IF NOT EXISTS ux_identities_phone ON identities(phone);
CREATE UNIQUE INDEX IF NOT EXISTS ux_identities_document ON identities(document_number);

-- Users
CREATE INDEX IF NOT EXISTS idx_users_person_id ON users(person_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- Admins
CREATE UNIQUE INDEX IF NOT EXISTS ux_admins_person_id ON admins(person_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_admins_team_code_unique ON admins(team_code);
CREATE INDEX IF NOT EXISTS idx_admins_status ON admins(status);
CREATE INDEX IF NOT EXISTS idx_admins_user_id ON admins(user_id);

-- Couriers
CREATE UNIQUE INDEX IF NOT EXISTS ux_couriers_person_id ON couriers(person_id);
CREATE INDEX IF NOT EXISTS idx_couriers_status ON couriers(status);
CREATE INDEX IF NOT EXISTS idx_couriers_user_id ON couriers(user_id);

-- Allies
CREATE UNIQUE INDEX IF NOT EXISTS ux_allies_person_id ON allies(person_id);
CREATE INDEX IF NOT EXISTS idx_allies_status ON allies(status);
CREATE INDEX IF NOT EXISTS idx_allies_user_id ON allies(user_id);

-- User roles
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);

-- Admin relationships
CREATE INDEX IF NOT EXISTS idx_admin_allies_admin_id ON admin_allies(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_allies_ally_id ON admin_allies(ally_id);
CREATE INDEX IF NOT EXISTS idx_admin_couriers_admin_id ON admin_couriers(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_couriers_courier_id ON admin_couriers(courier_id);

-- Orders
CREATE INDEX IF NOT EXISTS idx_orders_ally_id ON orders(ally_id);
CREATE INDEX IF NOT EXISTS idx_orders_courier_id ON orders(courier_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Terms
CREATE INDEX IF NOT EXISTS idx_terms_versions_role ON terms_versions(role);
CREATE INDEX IF NOT EXISTS idx_terms_acceptances_telegram_id ON terms_acceptances(telegram_id);

-- ============================================================
-- NOTAS DE MIGRACIÓN:
--
-- 1. Este schema refleja la estructura completa de SQLite según init_db()
-- 2. Se incluyen todas las columnas agregadas vía ALTER TABLE
-- 3. Se incluyen columnas is_active en admin_allies y admin_couriers (usadas en código)
-- 4. Foreign Keys omitidas intencionalmente para evitar bloqueos en migración inicial
-- 5. Los tipos se adaptaron:
--    - INTEGER AUTOINCREMENT → BIGSERIAL
--    - INTEGER (IDs) → BIGINT
--    - INTEGER (flags) → INTEGER
--    - TEXT → TEXT
--    - REAL → NUMERIC
--    - datetime('now') → NOW()
-- 6. Para agregar FKs en fase posterior, usar:
--    ALTER TABLE <tabla> ADD CONSTRAINT fk_<nombre>
--    FOREIGN KEY (<columna>) REFERENCES <tabla_ref>(id);
-- ============================================================
