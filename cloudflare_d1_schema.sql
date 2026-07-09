-- Schema Cloudflare D1 / SQLite para Portal de Insumos J&T
-- O app cria automaticamente as tabelas ao iniciar com token D1 Write.
-- Este arquivo serve para executar manualmente no painel do Cloudflare D1, se preferir.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    responsible_name TEXT NOT NULL,
    organization_name TEXT NOT NULL,
    franchise_name TEXT NOT NULL DEFAULT '',
    franchise_number TEXT NOT NULL DEFAULT '',
    cnpj TEXT NOT NULL DEFAULT '',
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
    category_emoji TEXT,
    image_name TEXT,
    image_key TEXT,
    image_content_type TEXT,
    unit_measure TEXT NOT NULL DEFAULT 'un',
    is_kit INTEGER NOT NULL DEFAULT 0,
    kit_quantity INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    price_cents INTEGER NOT NULL DEFAULT 0,
    limit_base INTEGER,
    limit_franchise INTEGER,
    limit_block_days INTEGER NOT NULL DEFAULT 60,
    min_order_quantity INTEGER,
    min_stock INTEGER,
    max_stock INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    catalog_archived INTEGER NOT NULL DEFAULT 0,
    visible_base INTEGER NOT NULL DEFAULT 1,
    visible_franchise INTEGER NOT NULL DEFAULT 1,
    internal INTEGER NOT NULL DEFAULT 0,
    stock_tag TEXT NOT NULL DEFAULT 'insumos',
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


CREATE TABLE IF NOT EXISTS product_request_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    blocked_until TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_by_request_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    revoked_at TEXT,
    updated_by_id INTEGER,
    UNIQUE(user_id, product_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY(created_by_request_id) REFERENCES supply_requests(id),
    FOREIGN KEY(updated_by_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_product_request_blocks_user_product ON product_request_blocks(user_id, product_id);
CREATE INDEX IF NOT EXISTS idx_product_request_blocks_blocked_until ON product_request_blocks(blocked_until);

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

CREATE TABLE IF NOT EXISTS access_role_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    permissions_json TEXT NOT NULL DEFAULT '[]',
    action_permissions_json TEXT NOT NULL DEFAULT '[]',
    editable_roles_json TEXT NOT NULL DEFAULT '[]',
    editable_user_fields_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_access_role_types_name ON access_role_types(name COLLATE NOCASE);

-- v65 - Entrada de Materiais
CREATE TABLE IF NOT EXISTS material_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    unit_measure TEXT NOT NULL DEFAULT 'un',
    unit_price_cents INTEGER NOT NULL DEFAULT 0,
    invoice_file_name TEXT,
    invoice_file_key TEXT,
    invoice_number TEXT,
    invoice_date TEXT,
    invoice_value_cents INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_by_id INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(created_by_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_material_entries_created_at ON material_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_material_entries_product_id ON material_entries(product_id);


CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT '',
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_users_responsible_name ON users(responsible_name COLLATE NOCASE);
