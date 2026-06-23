-- Schema Cloudflare D1 / SQLite para Portal de Insumos J&T
-- O app cria automaticamente as tabelas ao iniciar com token D1 Write.
-- Este arquivo serve para executar manualmente no painel do Cloudflare D1, se preferir.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    responsible_name TEXT NOT NULL,
    organization_name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'base',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    page_permissions_configured INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    unit_measure TEXT NOT NULL DEFAULT 'un',
    description TEXT,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    price_cents INTEGER NOT NULL DEFAULT 0,
    limit_base INTEGER,
    limit_franchise INTEGER,
    min_stock INTEGER,
    max_stock INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS supply_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    user_note TEXT,
    admin_note TEXT,
    people_count INTEGER,
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    reviewed_by_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(reviewed_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS request_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_name_snapshot TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price_cents_snapshot INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(request_id) REFERENCES supply_requests(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS admin_login_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    request_id INTEGER,
    created_by_id INTEGER,
    movement_type TEXT NOT NULL,
    quantity_delta INTEGER NOT NULL,
    stock_before INTEGER NOT NULL,
    stock_after INTEGER NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(request_id) REFERENCES supply_requests(id),
    FOREIGN KEY(created_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    base TEXT NOT NULL,
    regional TEXT NOT NULL,
    sector TEXT NOT NULL,
    manager TEXT NOT NULL,
    created_by_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY(created_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS asset_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    product_id INTEGER,
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    serial_number TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

CREATE INDEX IF NOT EXISTS idx_assets_base_regional ON assets(base, regional);
CREATE INDEX IF NOT EXISTS idx_asset_items_asset_id ON asset_items(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_items_product_id ON asset_items(product_id);

CREATE TABLE IF NOT EXISTS user_page_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    page_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, page_key),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
