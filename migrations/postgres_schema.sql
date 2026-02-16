-- ============================================================
-- POSTGRES SCHEMA FOR DOMIQUERENDONA BOT
-- Completo: todas las tablas, columnas e índices de init_db()
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
    balance INTEGER DEFAULT 0 CHECK(balance >= 0),
    status TEXT NOT NULL DEFAULT 'PENDING',
    team_name TEXT,
    document_number TEXT,
    team_code TEXT,
    residence_address TEXT,
    residence_lat REAL,
    residence_lng REAL,
    payment_phone TEXT,
    payment_bank TEXT,
    payment_holder TEXT,
    payment_instructions TEXT,
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
    available_cash INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 0,
    residence_address TEXT,
    residence_lat REAL,
    residence_lng REAL,
    live_lat REAL,
    live_lng REAL,
    live_location_active INTEGER DEFAULT 0,
    live_location_updated_at TIMESTAMP,
    availability_status TEXT DEFAULT 'INACTIVE',
    rejection_type TEXT,
    rejection_reason TEXT,
    rejected_at TIMESTAMP,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TIMESTAMP,
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

CREATE TABLE IF NOT EXISTS map_link_cache (
    id BIGSERIAL PRIMARY KEY,
    raw_link TEXT UNIQUE,
    expanded_link TEXT,
    lat REAL,
    lng REAL,
    formatted_address TEXT,
    provider TEXT,
    place_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_usage_daily (
    id BIGSERIAL PRIMARY KEY,
    api_name TEXT NOT NULL,
    usage_date TEXT NOT NULL,
    call_count INTEGER DEFAULT 0,
    UNIQUE(api_name, usage_date)
);

CREATE TABLE IF NOT EXISTS map_distance_cache (
    id BIGSERIAL PRIMARY KEY,
    origin_key TEXT NOT NULL,
    destination_key TEXT NOT NULL,
    mode TEXT NOT NULL,
    distance_km REAL NOT NULL,
    provider TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(origin_key, destination_key, mode)
);

CREATE TABLE IF NOT EXISTS status_audit_log (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id BIGINT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    reason TEXT,
    source TEXT,
    changed_by TEXT DEFAULT 'UNKNOWN',
    created_at TIMESTAMP DEFAULT NOW()
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
    lat REAL,
    lng REAL,
    is_default INTEGER DEFAULT 0,
    use_count INTEGER DEFAULT 0,
    is_frequent INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_allies (
    id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL,
    ally_id BIGINT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    balance INTEGER DEFAULT 0 CHECK(balance >= 0),
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
    balance INTEGER DEFAULT 0 CHECK(balance >= 0),
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(admin_id, courier_id)
);

CREATE TABLE IF NOT EXISTS ally_courier_blocks (
    id BIGSERIAL PRIMARY KEY,
    ally_id BIGINT NOT NULL,
    courier_id BIGINT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(ally_id, courier_id)
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
    requires_cash INTEGER DEFAULT 0,
    cash_required_amount INTEGER DEFAULT 0,
    pickup_lat REAL,
    pickup_lng REAL,
    dropoff_lat REAL,
    dropoff_lng REAL,
    quote_source TEXT,
    canceled_by TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,
    accepted_at TIMESTAMP,
    pickup_confirmed_at TIMESTAMP,
    delivered_at TIMESTAMP,
    canceled_at TIMESTAMP,
    ally_admin_id_snapshot BIGINT,
    courier_admin_id_snapshot BIGINT
);

CREATE TABLE IF NOT EXISTS order_offer_queue (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    courier_id BIGINT NOT NULL,
    position INTEGER NOT NULL,
    status TEXT DEFAULT 'PENDING',
    offered_at TIMESTAMP,
    responded_at TIMESTAMP,
    response TEXT
);

CREATE TABLE IF NOT EXISTS order_pickup_confirmations (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL UNIQUE,
    courier_id BIGINT NOT NULL,
    ally_id BIGINT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    requested_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewed_by_ally_id BIGINT
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
-- G) TABLAS PARA AGENDA DE CLIENTES RECURRENTES
-- ============================================================

CREATE TABLE IF NOT EXISTS ally_customers (
    id BIGSERIAL PRIMARY KEY,
    ally_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ally_customer_addresses (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    label TEXT,
    address_text TEXT NOT NULL,
    city TEXT,
    barrio TEXT,
    notes TEXT,
    lat REAL,
    lng REAL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- H) TABLAS DE RECARGAS Y CONTABILIDAD
-- ============================================================

CREATE TABLE IF NOT EXISTS recharge_requests (
    id BIGSERIAL PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id BIGINT NOT NULL,
    admin_id BIGINT NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    requested_by_user_id BIGINT NOT NULL,
    decided_by_admin_id BIGINT,
    method TEXT,
    note TEXT,
    proof_file_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    decided_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ledger (
    id BIGSERIAL PRIMARY KEY,
    kind TEXT NOT NULL,
    from_type TEXT,
    from_id BIGINT,
    to_type TEXT NOT NULL,
    to_id BIGINT NOT NULL,
    amount INTEGER NOT NULL,
    ref_type TEXT,
    ref_id BIGINT,
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_payment_methods (
    id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL,
    method_name TEXT NOT NULL,
    account_number TEXT NOT NULL,
    account_holder TEXT NOT NULL,
    instructions TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- I) TABLAS DE REFERENCIAS Y PERMISOS
-- ============================================================

CREATE TABLE IF NOT EXISTS reference_alias_candidates (
    id BIGSERIAL PRIMARY KEY,
    raw_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL UNIQUE,
    suggested_lat REAL,
    suggested_lng REAL,
    source TEXT,
    seen_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'PENDING',
    reviewed_by_admin_id BIGINT,
    reviewed_at TIMESTAMP,
    review_note TEXT
);

CREATE TABLE IF NOT EXISTS admin_reference_validator_permissions (
    id BIGSERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'INACTIVE',
    granted_by_admin_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile_change_requests (
    id BIGSERIAL PRIMARY KEY,
    requester_user_id BIGINT NOT NULL,
    target_role TEXT NOT NULL,
    target_role_id BIGINT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    new_lat REAL,
    new_lng REAL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    team_admin_id BIGINT,
    team_code TEXT,
    reviewed_by_user_id BIGINT,
    reviewed_by_admin_id BIGINT,
    reviewed_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================
-- J) ÍNDICES
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

-- Order confirmations
CREATE INDEX IF NOT EXISTS idx_order_pickup_confirmations_status ON order_pickup_confirmations(status);
CREATE INDEX IF NOT EXISTS idx_order_pickup_confirmations_ally ON order_pickup_confirmations(ally_id);

-- Terms
CREATE INDEX IF NOT EXISTS idx_terms_versions_role ON terms_versions(role);
CREATE INDEX IF NOT EXISTS idx_terms_acceptances_telegram_id ON terms_acceptances(telegram_id);

-- Ally customers
CREATE INDEX IF NOT EXISTS idx_ally_customers_ally_id ON ally_customers(ally_id);
CREATE INDEX IF NOT EXISTS idx_ally_customers_ally_phone ON ally_customers(ally_id, phone);
CREATE INDEX IF NOT EXISTS idx_ally_customer_addresses_customer_id ON ally_customer_addresses(customer_id);

-- Recharges / Ledger
CREATE INDEX IF NOT EXISTS idx_recharge_requests_admin_status ON recharge_requests(admin_id, status);
CREATE INDEX IF NOT EXISTS idx_recharge_requests_target ON recharge_requests(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_ledger_from ON ledger(from_type, from_id);
CREATE INDEX IF NOT EXISTS idx_ledger_to ON ledger(to_type, to_id);
CREATE INDEX IF NOT EXISTS idx_ledger_ref ON ledger(ref_type, ref_id);
CREATE INDEX IF NOT EXISTS idx_admin_payment_methods_admin ON admin_payment_methods(admin_id, is_active);

-- References
CREATE INDEX IF NOT EXISTS idx_ref_alias_candidates_status ON reference_alias_candidates(status);
CREATE INDEX IF NOT EXISTS idx_ref_alias_candidates_last_seen ON reference_alias_candidates(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_ref_validator_perm_status ON admin_reference_validator_permissions(status);

-- Profile change requests
CREATE INDEX IF NOT EXISTS idx_pcr_status ON profile_change_requests(status);
CREATE INDEX IF NOT EXISTS idx_pcr_team_admin ON profile_change_requests(team_admin_id);
CREATE INDEX IF NOT EXISTS idx_pcr_team_code ON profile_change_requests(team_code);
