import os
import random
import re
import smtplib
import sqlite3
import string
import subprocess
import sys
import threading
import unicodedata
import time
import webbrowser
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.message import EmailMessage
from io import BytesIO
from functools import wraps
from pathlib import Path
from typing import Any


def ensure_local_dependencies() -> None:
    """Permite abrir o app.py direto no Windows sem precisar passar pelo VS Code.

    Em produção/Render, as dependências continuam vindo do requirements.txt.
    Localmente, se o usuário der duplo clique no app.py e faltar algum pacote,
    o próprio script tenta instalar antes de continuar.
    """
    if os.getenv("RENDER") or os.getenv("DISABLE_AUTO_INSTALL", "false").lower() in {"1", "true", "yes", "sim"}:
        return

    required = {
        "flask": "Flask==3.0.3",
        "openpyxl": "openpyxl==3.1.5",
        "reportlab": "reportlab==4.2.5",
        "svglib": "svglib==1.5.1",
        "requests": "requests==2.32.3",
        "boto3": "boto3==1.35.99",
    }
    missing = []
    try:
        import importlib.util
        for module_name, package_name in required.items():
            if importlib.util.find_spec(module_name) is None:
                missing.append(package_name)
    except Exception:
        return

    if not missing:
        return

    print("\n[Portal de Insumos] Instalando dependências locais ausentes...")
    print("Pacotes:", ", ".join(missing))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])


try:
    ensure_local_dependencies()
except Exception as exc:
    print("\nNão consegui instalar as dependências automaticamente.")
    print("Erro:", exc)
    print("\nRode o arquivo ABRIR_PORTAL.bat ou execute: pip install -r requirements.txt")
    input("\nPressione Enter para fechar...")
    raise

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from svglib.svglib import svg2rlg

from cloudflare_d1 import cloudflare_d1_connect_from_env
from cloudflare_r2 import upload_bytes_to_r2

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")

DATABASE_DRIVER = os.getenv("DATABASE_DRIVER", "sqlite").strip().lower()
DATABASE_PATH = os.getenv("DATABASE_PATH", str(INSTANCE_DIR / "jt_insumos.db"))
ADMIN_CODE_MINUTES = int(os.getenv("ADMIN_CODE_MINUTES", "10"))

# SMTP opcional. Se não configurar, o código de confirmação de login aparece no terminal e em flash.
MAIL_SERVER = os.getenv("MAIL_SERVER", "").strip()
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in {"1", "true", "yes", "sim"}
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "").strip()
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME or "no-reply@jt-insumos.local").strip()


@dataclass
class User:
    id: int
    responsible_name: str
    organization_name: str
    username: str
    email: str
    password_hash: str
    role: str
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    page_permissions_configured: bool = False

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_approved(self) -> bool:
        return self.status == "approved"


@dataclass
class Product:
    id: int = 0
    name: str = ""
    category: str = ""
    unit_measure: str = "un"
    description: str = ""
    stock_quantity: int = 0
    price_cents: int = 0
    limit_base: int | None = None
    limit_franchise: int | None = None
    min_stock: int | None = None
    max_stock: int | None = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    @property
    def price_brl(self) -> float:
        return self.price_cents / 100


@dataclass
class RequestItem:
    id: int
    request_id: int
    product_id: int
    product_name_snapshot: str
    quantity: int
    price_cents_snapshot: int
    product: Product | None = None


@dataclass
class SupplyRequest:
    id: int
    user_id: int
    status: str
    user_note: str
    admin_note: str
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by_id: int | None = None
    user: User | None = None
    items: list[RequestItem] = field(default_factory=list)

    @property
    def total_cents(self) -> int:
        return sum((item.price_cents_snapshot or 0) * item.quantity for item in self.items)


# ---------- Banco SQLite sem SQLAlchemy ----------

def using_cloudflare_d1() -> bool:
    return DATABASE_DRIVER in {"cloudflare_d1", "d1"} or (
        bool(os.getenv("CLOUDFLARE_D1_DATABASE_ID")) and DATABASE_DRIVER not in {"sqlite", "local"}
    )


def db_connect():
    if using_cloudflare_d1():
        return cloudflare_d1_connect_from_env()
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_cursor_lastrowid(cursor: Any) -> int | None:
    """Retorna o ID do último INSERT de forma segura para runtime e Pylance."""
    value = cursor.lastrowid
    return value if isinstance(value, int) else None


def open_browser_when_ready(port: int) -> None:
    """Abre o navegador automaticamente quando o site roda localmente."""
    if os.getenv("AUTO_OPEN_BROWSER", "true").lower() not in {"1", "true", "yes", "sim"}:
        return

    def _open() -> None:
        time.sleep(1.2)
        url = f"http://127.0.0.1:{port}"
        print(f"\nPortal aberto em: {url}\n")
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def resolve_port() -> int:
    """Usa PORT no Render. Localmente, evita falhar se a porta 5000 estiver ocupada."""
    env_port = os.getenv("PORT")
    if env_port:
        return int(env_port)

    preferred = 5000
    if is_port_available(preferred):
        return preferred

    for port in range(5001, 5015):
        if is_port_available(port):
            print(f"Porta 5000 ocupada. Usando porta {port}.")
            return port

    return preferred


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return datetime.utcnow()


def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def normalize_username(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^a-z0-9._-]", "", value)
    return value


def valid_username(value: str) -> bool:
    username = normalize_username(value)
    return 3 <= len(username) <= 40 and bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]*", username))


def synthetic_email_for_username(username: str) -> str:
    safe = normalize_username(username) or "usuario"
    return f"{safe}@usuario.local"


def is_real_email(value: str | None) -> bool:
    value = (value or "").strip().lower()
    return "@" in value and not value.endswith("@usuario.local")


def row_to_user(row: Any | None) -> User | None:
    if row is None:
        return None
    return User(
        id=int(row["id"]),
        responsible_name=row["responsible_name"] or "",
        organization_name=row["organization_name"] or "",
        username=(row["username"] if "username" in row.keys() else "") or normalize_username((row["email"] if "email" in row.keys() else "") or row["responsible_name"] or "usuario"),
        email=(row["email"] if "email" in row.keys() else "") or "",
        password_hash=row["password_hash"] or "",
        role=row["role"] or "base",
        status=row["status"] or "pending",
        created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
        updated_at=parse_dt(row["updated_at"]),
        page_permissions_configured=bool(row["page_permissions_configured"]) if "page_permissions_configured" in row.keys() else False,
    )


def row_to_product(row: Any | None) -> Product | None:
    if row is None:
        return None
    return Product(
        id=int(row["id"]),
        name=row["name"] or "",
        category=row["category"] or "",
        unit_measure=(row["unit_measure"] if "unit_measure" in row.keys() else None) or "un",
        description=row["description"] or "",
        stock_quantity=int(row["stock_quantity"] or 0),
        price_cents=int(row["price_cents"] or 0),
        limit_base=row["limit_base"] if "limit_base" in row.keys() and row["limit_base"] is not None else None,
        limit_franchise=row["limit_franchise"] if "limit_franchise" in row.keys() and row["limit_franchise"] is not None else None,
        min_stock=row["min_stock"] if "min_stock" in row.keys() and row["min_stock"] is not None else None,
        max_stock=row["max_stock"] if "max_stock" in row.keys() and row["max_stock"] is not None else None,
        active=bool(row["active"]),
        created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
        updated_at=parse_dt(row["updated_at"]),
    )


def row_to_item(row: Any | None, load_product: bool = True) -> RequestItem | None:
    if row is None:
        return None
    item = RequestItem(
        id=int(row["id"]),
        request_id=int(row["request_id"]),
        product_id=int(row["product_id"]),
        product_name_snapshot=row["product_name_snapshot"] or "",
        quantity=int(row["quantity"] or 0),
        price_cents_snapshot=int(row["price_cents_snapshot"] or 0),
    )
    if load_product:
        item.product = get_product(item.product_id)
    return item


def row_to_supply_request(row: Any | None, include_user: bool = True, include_items: bool = True) -> SupplyRequest | None:
    if row is None:
        return None
    req = SupplyRequest(
        id=int(row["id"]),
        user_id=int(row["user_id"]),
        status=row["status"] or "pending",
        user_note=row["user_note"] or "",
        admin_note=row["admin_note"] or "",
        created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
        reviewed_at=parse_dt(row["reviewed_at"]),
        reviewed_by_id=row["reviewed_by_id"],
    )
    if include_user:
        req.user = get_user(req.user_id)
    if include_items:
        req.items = get_request_items(req.id)
    return req


def init_db() -> None:
    with db_connect() as conn:
        conn.executescript(
            """
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

            CREATE TABLE IF NOT EXISTS user_page_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                page_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, page_key),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "page_permissions_configured" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN page_permissions_configured INTEGER NOT NULL DEFAULT 0")

        user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "username" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
            existing_users = conn.execute("SELECT id, responsible_name, email FROM users").fetchall()
            used_usernames: set[str] = set()
            for existing_user in existing_users:
                base_username = normalize_username((existing_user["email"] or "").split("@")[0] or existing_user["responsible_name"] or f"usuario{existing_user['id']}")
                if not base_username:
                    base_username = f"usuario{existing_user['id']}"
                candidate = base_username
                suffix = 2
                while candidate in used_usernames:
                    candidate = f"{base_username}{suffix}"
                    suffix += 1
                used_usernames.add(candidate)
                conn.execute("UPDATE users SET username = ? WHERE id = ?", (candidate, existing_user["id"]))
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(username)")

        product_columns = {row["name"] for row in conn.execute("PRAGMA table_info(products)").fetchall()}
        if "unit_measure" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN unit_measure TEXT NOT NULL DEFAULT 'un'")
        if "min_stock" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN min_stock INTEGER")
        if "max_stock" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN max_stock INTEGER")
        movement_count = conn.execute("SELECT COUNT(*) AS total FROM stock_movements").fetchone()["total"]
        if int(movement_count or 0) == 0:
            existing_products = conn.execute("SELECT id, stock_quantity FROM products WHERE stock_quantity > 0").fetchall()
            for product_row in existing_products:
                initial_stock = int(product_row["stock_quantity"] or 0)
                record_stock_movement(
                    conn,
                    int(product_row["id"]),
                    initial_stock,
                    0,
                    initial_stock,
                    "product_created",
                    "Registro inicial do estoque existente.",
                )
        conn.commit()


def seed_initial_data() -> None:
    admin_username = normalize_username(os.getenv("ADMIN_USERNAME", os.getenv("SEED_ADMIN_USERNAME", "admin")))
    admin_email = os.getenv("ADMIN_EMAIL", os.getenv("SEED_ADMIN_EMAIL", synthetic_email_for_username(admin_username))).strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", os.getenv("SEED_ADMIN_PASSWORD", "Admin@123"))
    with db_connect() as conn:
        user_count = conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
        if user_count == 0:
            conn.execute(
                """
                INSERT INTO users (responsible_name, organization_name, username, email, password_hash, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'admin', 'approved', ?)
                """,
                ("Administrador", "J&T Express", admin_username, admin_email, generate_password_hash(admin_password), now_iso()),
            )

        product_count = conn.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"]
        if product_count == 0:
            samples = [
                ("Envelope de segurança P", "Embalagens", "un", "Envelope pequeno para envios leves.", 500, 45, 100, 80, 120, 600),
                ("Envelope de segurança M", "Embalagens", "un", "Envelope médio para envios padrão.", 400, 65, 80, 60, 100, 500),
                ("Lacre plástico", "Operacional", "un", "Lacre numerado para controle interno.", 1000, 18, 200, 150, 250, 1200),
                ("Etiqueta térmica", "Etiquetas", "rolo", "Rolo de etiqueta para impressora térmica.", 120, 2500, 10, 8, 30, 180),
            ]
            for item in samples:
                cursor = conn.execute(
                    """
                    INSERT INTO products (name, category, unit_measure, description, stock_quantity, price_cents, limit_base, limit_franchise, min_stock, max_stock, active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (*item, now_iso()),
                )
                row_id = get_cursor_lastrowid(cursor)
                if row_id is not None:
                    record_stock_movement(conn, row_id, int(item[4]), 0, int(item[4]), "product_created", "Estoque inicial do sistema.")
        conn.commit()


def setup_database() -> None:
    init_db()
    seed_initial_data()


# ---------- Consultas ----------

def get_user(user_id: int | None) -> User | None:
    if user_id is None:
        return None
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
    return row_to_user(row)


def get_user_by_username(username: str) -> User | None:
    username = normalize_username(username)
    if not username:
        return None
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (username,)).fetchone()
    return row_to_user(row)


def get_user_by_email(email: str) -> User | None:
    # Mantido apenas para compatibilidade com bancos antigos/rotas antigas.
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", ((email or "").strip().lower(),)).fetchone()
    return row_to_user(row)


def get_product(product_id: int | None) -> Product | None:
    if product_id is None:
        return None
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (int(product_id),)).fetchone()
    return row_to_product(row)




def get_product_by_name(name: str) -> Product | None:
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM products WHERE lower(name) = lower(?) LIMIT 1", (name.strip(),)).fetchone()
    return row_to_product(row)


def get_request_items(request_id: int) -> list[RequestItem]:
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM request_items WHERE request_id = ? ORDER BY id", (request_id,)).fetchall()
    return [item for row in rows if (item := row_to_item(row)) is not None]


def get_supply_request(request_id: int) -> SupplyRequest | None:
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM supply_requests WHERE id = ?", (request_id,)).fetchone()
    return row_to_supply_request(row)


def list_supply_requests(status: str = "", user_id: int | None = None, limit: int | None = None) -> list[SupplyRequest]:
    sql = "SELECT * FROM supply_requests"
    params: list[Any] = []
    clauses: list[str] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    with db_connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [req for row in rows if (req := row_to_supply_request(row)) is not None]


# ---------- Helpers ----------

def current_user() -> User | None:
    uid = session.get("user_id")
    if uid is None:
        return None
    try:
        return get_user(int(uid))
    except (TypeError, ValueError):
        return None


def require_current_user() -> User:
    user = current_user()
    if user is None:
        abort(401)
    return user


@app.context_processor
def inject_globals():
    return {
        "current_user": current_user(),
        "format_brl": format_brl,
        "status_label": status_label,
        "stock_status_class": stock_status_class,
        "stock_status_label": stock_status_label,
        "can_access": lambda page_key: user_has_page_access(current_user(), page_key),
        "can_access_any": lambda page_keys: user_has_any_page_access(current_user(), page_keys),
        "page_permission_options": PAGE_PERMISSION_OPTIONS,
    }


def format_brl(cents: int | None) -> str:
    value = (cents or 0) / 100
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def status_label(status: str) -> str:
    labels = {
        "pending": "Pendente",
        "approved": "Aprovado",
        "rejected": "Recusado",
        "deleted": "Excluído",
    }
    return labels.get(status, status)


PAGE_PERMISSION_OPTIONS = [
    {
        "key": "home",
        "label": "Solicitar insumos",
        "description": "Permite acessar a tela inicial e enviar solicitações de insumos.",
        "admin_only": False,
    },
    {
        "key": "my_requests",
        "label": "Minhas solicitações",
        "description": "Permite visualizar as solicitações feitas pelo próprio usuário e baixar PDFs.",
        "admin_only": False,
    },
    {
        "key": "admin_dashboard",
        "label": "Painel admin",
        "description": "Permite acessar o resumo administrativo do portal.",
        "admin_only": True,
    },
    {
        "key": "admin_products",
        "label": "Produtos",
        "description": "Permite cadastrar, editar, importar e exportar produtos.",
        "admin_only": True,
    },
    {
        "key": "admin_stock",
        "label": "Gestão de estoque",
        "description": "Permite acompanhar estoque, gráficos e movimentações.",
        "admin_only": True,
    },
    {
        "key": "admin_users",
        "label": "Usuários e acessos",
        "description": "Permite aprovar, criar, editar permissões e excluir usuários.",
        "admin_only": True,
    },
    {
        "key": "admin_requests",
        "label": "Solicitações pendentes",
        "description": "Permite analisar, editar quantidades, aprovar ou recusar pedidos pendentes.",
        "admin_only": True,
    },
    {
        "key": "admin_requests_attended",
        "label": "Solicitações atendidas",
        "description": "Permite visualizar pedidos já aprovados ou recusados.",
        "admin_only": True,
    },
]


def default_page_keys_for_role(role: str) -> set[str]:
    if role == "admin":
        return {item["key"] for item in PAGE_PERMISSION_OPTIONS}
    return {item["key"] for item in PAGE_PERMISSION_OPTIONS if not item["admin_only"]}


def permission_options_for_role(role: str) -> list[dict[str, Any]]:
    if role == "admin":
        return PAGE_PERMISSION_OPTIONS
    return [item for item in PAGE_PERMISSION_OPTIONS if not item["admin_only"]]


def get_user_page_permissions(user: User | None) -> set[str]:
    if user is None:
        return set()
    if not user.page_permissions_configured:
        return default_page_keys_for_role(user.role)
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT page_key FROM user_page_permissions WHERE user_id = ?",
            (user.id,),
        ).fetchall()
    allowed = {str(row["page_key"]) for row in rows}
    valid_for_role = default_page_keys_for_role(user.role)
    return allowed & valid_for_role


def user_has_page_access(user: User | None, page_key: str) -> bool:
    if user is None:
        return False
    return page_key in get_user_page_permissions(user)


def user_has_any_page_access(user: User | None, page_keys: list[str]) -> bool:
    if user is None:
        return False
    allowed = get_user_page_permissions(user)
    return any(key in allowed for key in page_keys)


def save_user_page_permissions(conn: Any, user_id: int, role: str, selected_keys: list[str] | set[str]) -> None:
    allowed_for_role = default_page_keys_for_role(role)
    normalized = {key for key in selected_keys if key in allowed_for_role}
    conn.execute("DELETE FROM user_page_permissions WHERE user_id = ?", (user_id,))
    for key in sorted(normalized):
        conn.execute(
            "INSERT OR IGNORE INTO user_page_permissions (user_id, page_key, created_at) VALUES (?, ?, ?)",
            (user_id, key, now_iso()),
        )
    conn.execute(
        "UPDATE users SET page_permissions_configured = 1, updated_at = ? WHERE id = ?",
        (now_iso(), user_id),
    )


def selected_permissions_for_form(user: User | None, role: str | None = None) -> set[str]:
    if user is not None:
        return get_user_page_permissions(user)
    return default_page_keys_for_role(role or "base")


def page_access_required(page_key: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                abort(401)
            if not user_has_page_access(user, page_key):
                flash("Seu usuário não possui acesso a esta página.", "warning")
                if user.is_admin and user_has_page_access(user, "admin_dashboard"):
                    return redirect(url_for("admin_dashboard"))
                if user_has_page_access(user, "home"):
                    return redirect(url_for("home"))
                if user_has_page_access(user, "my_requests"):
                    return redirect(url_for("my_requests"))
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def page_access_any_required(page_keys: list[str]):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                abort(401)
            if not user_has_any_page_access(user, page_keys):
                flash("Seu usuário não possui acesso a esta página.", "warning")
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def stock_status_class(product: Product) -> str:
    minimum = product.min_stock
    maximum = product.max_stock
    stock = product.stock_quantity
    if minimum is None and maximum is None:
        return "normal"
    if minimum is not None:
        alert_limit = minimum
        if maximum is not None and maximum > minimum:
            alert_limit = minimum + max(1, int((maximum - minimum) * 0.15))
        if stock <= alert_limit:
            return "critical"
    if maximum is not None:
        return "good" if stock >= maximum else "normal"
    if minimum is not None and stock > minimum:
        return "good"
    return "normal"


def stock_status_label(product: Product) -> str:
    status = stock_status_class(product)
    if status == "critical":
        return "Atenção"
    if status == "good":
        return "Saudável"
    return "Normal"


def movement_type_label(movement_type: str) -> str:
    labels = {
        "request_approved": "Saída por solicitação",
        "manual_adjustment": "Ajuste manual",
        "product_created": "Cadastro de produto",
        "import_adjustment": "Ajuste por importação",
    }
    return labels.get(movement_type, movement_type)


def record_stock_movement(
    conn: Any,
    product_id: int,
    quantity_delta: int,
    stock_before: int,
    stock_after: int,
    movement_type: str,
    note: str = "",
    request_id: int | None = None,
    created_by_id: int | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO stock_movements (product_id, request_id, created_by_id, movement_type, quantity_delta, stock_before, stock_after, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (product_id, request_id, created_by_id, movement_type, quantity_delta, stock_before, stock_after, note, now_iso()),
    )





def normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    for char in [".", ":", ";", "-", "_", "/", "\\", "(", ")"]:
        text = text.replace(char, " ")
    return " ".join(text.split())


def parse_money_to_cents(value: Any) -> int:
    if value is None or str(value).strip() == "":
        return 0
    if isinstance(value, (int, float)):
        return int(round(float(value) * 100))
    text_value = str(value).strip().replace("R$", "").replace(" ", "")
    if "," in text_value:
        text_value = text_value.replace(".", "").replace(",", ".")
    try:
        return int(round(float(text_value or "0") * 100))
    except ValueError:
        return 0


def parse_bool_value(value: Any, default: bool = True) -> bool:
    if value is None or str(value).strip() == "":
        return default
    text = normalize_header(value)
    return text in {"1", "sim", "s", "yes", "y", "true", "ativo", "ativado", "active"}


def safe_filename(text_value: str) -> str:
    normalized = normalize_header(text_value).replace(" ", "_")
    allowed = "".join(ch for ch in normalized if ch.isalnum() or ch in {"_", "-"})
    return allowed[:70] or "arquivo"


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("login"))
        if not user.is_admin and not user.is_approved:
            session.clear()
            flash("Seu cadastro ainda não foi aprovado por um administrador.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None or not user.is_admin or not user.is_approved:
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


def generate_code(length: int = 6) -> str:
    return "".join(random.choice(string.digits) for _ in range(length))


def email_is_configured() -> bool:
    return bool(MAIL_SERVER and MAIL_USERNAME and MAIL_PASSWORD)


def send_admin_login_code(user: User, code: str) -> bool:
    subject = "Código de confirmação de login - Portal de Insumos J&T"
    body = (
        f"Olá, {user.responsible_name}.\n\n"
        f"Seu código de confirmação de login é: {code}\n"
        f"Validade: {ADMIN_CODE_MINUTES} minutos.\n\n"
        "Caso não tenha solicitado, ignore este e-mail."
    )

    if email_is_configured() and is_real_email(user.email):
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = MAIL_DEFAULT_SENDER
        msg["To"] = user.email
        msg.set_content(body)
        try:
            if MAIL_USE_SSL:
                smtp_context = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT, timeout=20)
            else:
                smtp_context = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=20)
            with smtp_context as smtp:
                if MAIL_USE_TLS and not MAIL_USE_SSL:
                    smtp.starttls()
                smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
                smtp.send_message(msg)
            return True
        except Exception as exc:
            print("=" * 80)
            print("ERRO AO ENVIAR CÓDIGO DE CONFIRMAÇÃO DE LOGIN POR E-MAIL")
            print(f"Destino: {user.email}")
            print(f"SMTP: {MAIL_SERVER}:{MAIL_PORT} | TLS={MAIL_USE_TLS} | SSL={MAIL_USE_SSL}")
            print(f"Erro: {type(exc).__name__} - {exc}")
            print("=" * 80)
            flash("Não consegui enviar o código de confirmação por e-mail. Confira as variáveis SMTP no Render e tente novamente.", "danger")
            return False

    print("=" * 80)
    print(f"CÓDIGO DE CONFIRMAÇÃO DE LOGIN DEV para {user.username}: {code}")
    print("=" * 80)
    flash(f"Insira o código para confirmar o seu login: {code}", "info")
    return True


def product_limit_for(product: Product, user: User) -> int | None:
    if user.role == "franchise":
        return product.limit_franchise
    if user.role == "base":
        return product.limit_base
    return None


def parse_required_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        number = int(text_value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def parse_optional_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = int(str(value).strip())
    except ValueError:
        return None
    return number if number >= 0 else None


def validate_items_for_user(items_payload: Any, user: User) -> tuple[list[tuple[Product, int]], str | None]:
    if not isinstance(items_payload, list):
        return [], "Lista de itens inválida."
    if not items_payload:
        return [], "Adicione pelo menos um insumo ao pedido."

    seen: dict[int, int] = {}
    for raw in items_payload:
        if not isinstance(raw, dict):
            return [], "Item inválido no pedido."
        product_id = parse_required_positive_int(raw.get("product_id"))
        quantity = parse_required_positive_int(raw.get("quantity"))
        if product_id is None or quantity is None:
            return [], "Item inválido no pedido."
        seen[product_id] = seen.get(product_id, 0) + quantity

    normalized: list[tuple[Product, int]] = []
    for product_id, quantity in seen.items():
        product = get_product(product_id)
        if product is None or not product.active:
            return [], "Um dos insumos selecionados não está disponível."

        if not user.is_admin:
            limit = product_limit_for(product, user)
            if limit is not None and quantity > limit:
                return [], f"Limite de insumos excedido para {product.name}. Limite permitido: {limit}."

        normalized.append((product, quantity))
    return normalized, None


def fill_product_from_form(product: Product) -> Product:
    product.name = request.form.get("name", "").strip()
    product.category = request.form.get("category", "").strip()
    product.unit_measure = request.form.get("unit_measure", "").strip() or "un"
    product.description = request.form.get("description", "").strip()
    product.stock_quantity = parse_required_positive_int(request.form.get("stock_quantity")) or 0
    price_raw = (request.form.get("price") or "0").strip()
    if "," in price_raw:
        price_raw = price_raw.replace(".", "").replace(",", ".")
    try:
        product.price_cents = int(round(float(price_raw or "0") * 100))
    except ValueError:
        product.price_cents = 0
    product.limit_base = parse_optional_int(request.form.get("limit_base"))
    product.limit_franchise = parse_optional_int(request.form.get("limit_franchise"))
    product.min_stock = parse_optional_int(request.form.get("min_stock"))
    product.max_stock = parse_optional_int(request.form.get("max_stock"))
    product.active = request.form.get("active") == "on"
    return product


def product_to_api(product: Product, user: User) -> dict[str, Any]:
    show_stock = user.is_admin
    show_price = user.is_admin or user.role == "franchise"
    limit = product_limit_for(product, user)
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category or "Sem categoria",
        "unit_measure": product.unit_measure or "un",
        "description": product.description or "",
        "price": format_brl(product.price_cents),
        "stock_quantity": product.stock_quantity if show_stock else None,
        "limit": limit,
        "show_stock": show_stock,
        "show_price": show_price,
    }





def store_generated_file(key: str, buffer: BytesIO, content_type: str, metadata: dict[str, str] | None = None) -> str | None:
    """Stores a generated file in Cloudflare R2 when configured.

    The buffer position is preserved for send_file downloads.
    """
    try:
        position = buffer.tell()
        buffer.seek(0)
        data = buffer.read()
        buffer.seek(position)
        return upload_bytes_to_r2(key, data, content_type, metadata or {})
    except Exception as exc:
        print(f"[R2] Não foi possível armazenar {key}: {exc}")
        try:
            buffer.seek(0)
        except Exception:
            pass
        return None


def storage_key(*parts: Any) -> str:
    clean_parts = [safe_filename(str(part)).strip("_") for part in parts if str(part or "").strip()]
    return "/".join(clean_parts)


def build_request_pdf(supply_request: SupplyRequest, viewer: User) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=17 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="JTTitle", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#111111"), spaceAfter=8))
    styles.add(ParagraphStyle(name="JTSub", fontName="Helvetica", fontSize=9.5, leading=13, textColor=colors.HexColor("#555555")))
    styles.add(ParagraphStyle(name="JTMeta", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="JTMetaLabel", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.HexColor("#e60012"), uppercase=True))
    styles.add(ParagraphStyle(name="JTCell", fontName="Helvetica", fontSize=8.6, leading=11, textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="JTCellBold", fontName="Helvetica-Bold", fontSize=8.6, leading=11, textColor=colors.HexColor("#111111")))

    story: list[Any] = []

    logo_path = BASE_DIR / "static" / "img" / "logo-jt-red.svg"
    try:
        drawing = svg2rlg(str(logo_path))
        if drawing is not None and drawing.width:
            scale = (50 * mm) / drawing.width
            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)
            story.append(drawing)
            story.append(Spacer(1, 7 * mm))
        else:
            raise ValueError("Logo SVG inválida")
    except Exception:
        logo_table = Table([[Paragraph("J&amp;T EXPRESS", ParagraphStyle(name="FallbackLogo", fontName="Helvetica-Bold", fontSize=18, textColor=colors.white))]], colWidths=[52 * mm])
        logo_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e60012")),
            ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#e60012")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(logo_table)
        story.append(Spacer(1, 7 * mm))

    requester = supply_request.user
    requester_name = requester.responsible_name if requester else "-"
    requester_org = requester.organization_name if requester else "-"
    requester_username = requester.username if requester else "-"
    requester_role = requester.role if requester else "base"
    show_prices = viewer.is_admin or viewer.role == "franchise"

    story.append(Paragraph(f"Solicitação de Insumos #{supply_request.id}", styles["JTTitle"]))
    story.append(Paragraph("Documento gerado automaticamente pelo Portal de Solicitação de Insumos J&amp;T Express Brazil.", styles["JTSub"]))
    story.append(Spacer(1, 7 * mm))

    meta_data = [
        [Paragraph("SOLICITANTE", styles["JTMetaLabel"]), Paragraph("BASE / FRANQUIA", styles["JTMetaLabel"]), Paragraph("STATUS ATUAL", styles["JTMetaLabel"])],
        [Paragraph(requester_name, styles["JTMeta"]), Paragraph(requester_org, styles["JTMeta"]), Paragraph(status_label(supply_request.status), styles["JTCellBold"])],
        [Paragraph("E-MAIL", styles["JTMetaLabel"]), Paragraph("TIPO DE ACESSO", styles["JTMetaLabel"]), Paragraph("DATA DA SOLICITAÇÃO", styles["JTMetaLabel"])],
        [Paragraph(requester_username, styles["JTMeta"]), Paragraph("Administrador" if requester_role == "admin" else ("Base" if requester_role == "base" else "Franquia"), styles["JTMeta"]), Paragraph(supply_request.created_at.strftime("%d/%m/%Y %H:%M"), styles["JTMeta"])],
    ]
    meta_table = Table(meta_data, colWidths=[57 * mm, 57 * mm, 57 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f8f8")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#eeeeee")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))

    headers = [Paragraph("Produto solicitado", styles["JTCellBold"]), Paragraph("Qtd.", styles["JTCellBold"])]
    col_widths = [118 * mm, 22 * mm]
    if show_prices:
        headers.extend([Paragraph("Valor unit.", styles["JTCellBold"]), Paragraph("Subtotal", styles["JTCellBold"])])
        col_widths = [88 * mm, 19 * mm, 30 * mm, 34 * mm]

    item_rows: list[list[Any]] = [headers]
    for item in supply_request.items:
        unit_label = item.product.unit_measure if item.product and item.product.unit_measure else "un"
        row: list[Any] = [Paragraph(item.product_name_snapshot, styles["JTCell"]), Paragraph(f"{item.quantity} {unit_label}", styles["JTCell"])]
        if show_prices:
            row.extend([
                Paragraph(format_brl(item.price_cents_snapshot), styles["JTCell"]),
                Paragraph(format_brl(item.price_cents_snapshot * item.quantity), styles["JTCellBold"]),
            ])
        item_rows.append(row)

    if show_prices:
        item_rows.append(["", "", Paragraph("TOTAL", styles["JTCellBold"]), Paragraph(format_brl(supply_request.total_cents), styles["JTCellBold"])])

    items_table = Table(item_rows, colWidths=col_widths, repeatRows=1)
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e60012")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dddddd")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e8e8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
    ]
    if show_prices:
        style_commands.extend([
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fff3f4")),
            ("SPAN", (0, -1), (1, -1)),
        ])
    for row_index in range(1, len(item_rows), 2):
        style_commands.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#fbfbfb")))
    items_table.setStyle(TableStyle(style_commands))
    story.append(Paragraph("Itens solicitados", ParagraphStyle(name="SectionTitle", fontName="Helvetica-Bold", fontSize=12, textColor=colors.HexColor("#111111"), spaceAfter=6)))
    story.append(items_table)
    story.append(Spacer(1, 8 * mm))

    if supply_request.user_note:
        story.append(Paragraph("Observação do solicitante", styles["JTCellBold"]))
        story.append(Paragraph(supply_request.user_note, styles["JTSub"]))
        story.append(Spacer(1, 5 * mm))
    if supply_request.admin_note:
        story.append(Paragraph("Observação administrativa", styles["JTCellBold"]))
        story.append(Paragraph(supply_request.admin_note, styles["JTSub"]))
        story.append(Spacer(1, 5 * mm))
    if supply_request.reviewed_at:
        story.append(Paragraph(f"Revisado em: {supply_request.reviewed_at.strftime('%d/%m/%Y %H:%M')}", styles["JTSub"]))

    def footer(canvas, document):
        canvas.saveState()
        width, _height = A4
        canvas.setStrokeColor(colors.HexColor("#e60012"))
        canvas.setLineWidth(0.7)
        canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(18 * mm, 9 * mm, "J&T Express Brazil • CNPJ: 42.584.754/0092-13")
        canvas.drawRightString(width - 18 * mm, 9 * mm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} • Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer



PRODUCT_EXPORT_HEADERS_PT = [
    "ID",
    "Nome do produto",
    "Categoria",
    "Unidade de medida",
    "Descrição",
    "Estoque disponível",
    "Valor unitário",
    "Limite para bases",
    "Limite para franquias",
    "Estoque mínimo",
    "Estoque máximo",
    "Ativo",
]

PRODUCT_EXPORT_HEADERS_ZH = [
    "ID",
    "产品名称 / Nome do produto",
    "类别 / Categoria",
    "计量单位 / Unidade de medida",
    "描述 / Descrição",
    "可用库存 / Estoque disponível",
    "单价 / Valor unitário",
    "基地限制 / Limite para bases",
    "加盟店限制 / Limite para franquias",
    "最低库存 / Estoque mínimo",
    "最高库存 / Estoque máximo",
    "启用 / Ativo",
]

EXCEL_ZH_TRANSLATIONS = {
    "Envelope de segurança M": "M 型安全信封",
    "Envelope de segurança P": "P 型安全信封",
    "Envelope médio para envios padrão.": "用于标准寄件的中型信封。",
    "Envelope pequeno para envios leves.": "用于轻量寄件的小型信封。",
    "Etiqueta térmica": "热敏标签",
    "Rolo de etiqueta para impressora térmica.": "热敏打印机用标签卷。",
    "Lacre plástico": "塑料封条",
    "Lacre numerado para controle interno.": "用于内部管控的编号封条。",
    "Embalagens": "包装用品",
    "Etiquetas": "标签",
    "Operacional": "运营用品",
    "un": "个",
    "unidade": "个",
    "unidades": "个",
    "rolo": "卷",
    "rolos": "卷",
    "caixa": "箱",
    "caixas": "箱",
    "pacote": "包",
    "pacotes": "包",
    "metro": "米",
    "metros": "米",
    "kg": "公斤",
    "Sim": "是",
    "Não": "否",
    "Ativo": "启用",
    "Inativo": "停用",
    "Sem limite": "无限制",
}


def translate_excel_value_to_zh(value: Any) -> Any:
    if value is None:
        return ""
    text_value = str(value).strip()
    if not text_value:
        return ""
    return EXCEL_ZH_TRANSLATIONS.get(text_value, text_value)


def product_row_for_excel_language(product: Product, language: str = "pt") -> list[Any]:
    if language == "zh":
        return [
            product.id,
            translate_excel_value_to_zh(product.name),
            translate_excel_value_to_zh(product.category),
            translate_excel_value_to_zh(product.unit_measure),
            translate_excel_value_to_zh(product.description),
            product.stock_quantity,
            product.price_brl,
            product.limit_base,
            product.limit_franchise,
            product.min_stock,
            product.max_stock,
            translate_excel_value_to_zh("Sim" if product.active else "Não"),
        ]
    return product_row_for_excel(product)

def product_row_for_excel(product: Product) -> list[Any]:
    return [
        product.id,
        product.name,
        product.category,
        product.unit_measure,
        product.description,
        product.stock_quantity,
        product.price_brl,
        product.limit_base,
        product.limit_franchise,
        product.min_stock,
        product.max_stock,
        "Sim" if product.active else "Não",
    ]


def get_header_value(row_values: list[Any], header_map: dict[str, int], names: list[str]) -> Any:
    normalized_names = [normalize_header(name) for name in names]
    for key in normalized_names:
        if key in header_map:
            idx = header_map[key]
            return row_values[idx] if idx < len(row_values) else None
    for key in normalized_names:
        if not key:
            continue
        for header_key, idx in header_map.items():
            if not header_key:
                continue
            if key in header_key or header_key in key:
                return row_values[idx] if idx < len(row_values) else None
    return None


# ---------- Autenticação ----------

@app.route("/")
@login_required
@page_access_required("home")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = normalize_username(request.form.get("username", ""))
        password = request.form.get("password", "")
        user = get_user_by_username(username)

        if user is None or not check_password_hash(user.password_hash, password):
            flash("Nome de usuário ou senha inválidos.", "danger")
            return redirect(url_for("login"))

        if not user.is_approved:
            flash("Seu cadastro ainda não foi aprovado por um administrador.", "warning")
            return redirect(url_for("login"))

        if user.is_admin:
            code = generate_code()
            expires_at = (datetime.utcnow() + timedelta(minutes=ADMIN_CODE_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
            with db_connect() as conn:
                conn.execute(
                    """
                    INSERT INTO admin_login_codes (user_id, code_hash, expires_at, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user.id, generate_password_hash(code), expires_at, now_iso()),
                )
                conn.commit()
            session["pending_admin_user_id"] = user.id
            if not send_admin_login_code(user, code):
                session.pop("pending_admin_user_id", None)
                return redirect(url_for("login"))
            return redirect(url_for("verify_admin"))

        session["user_id"] = user.id
        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/verify-admin", methods=["GET", "POST"])
def verify_admin():
    pending_id = session.get("pending_admin_user_id")
    user = get_user(int(pending_id)) if pending_id is not None else None
    if user is None:
        flash("Faça login novamente.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        with db_connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM admin_login_codes
                WHERE user_id = ? AND used_at IS NULL
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (user.id,),
            ).fetchall()
            for row in rows:
                expires = parse_dt(row["expires_at"]) or datetime.utcnow()
                if expires < datetime.utcnow():
                    continue
                if check_password_hash(row["code_hash"], code):
                    conn.execute("UPDATE admin_login_codes SET used_at = ? WHERE id = ?", (now_iso(), row["id"]))
                    conn.commit()
                    session.pop("pending_admin_user_id", None)
                    session["user_id"] = user.id
                    flash("Login confirmado com sucesso.", "success")
                    return redirect(url_for("admin_dashboard"))

        flash("Código inválido ou expirado.", "danger")
        return redirect(url_for("verify_admin"))

    return render_template("verify_admin.html", username=user.username, minutes=ADMIN_CODE_MINUTES)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        responsible_name = request.form.get("responsible_name", "").strip()
        organization_name = request.form.get("organization_name", "").strip()
        role = request.form.get("role", "base").strip()
        username = normalize_username(request.form.get("username", ""))
        email = synthetic_email_for_username(username)
        password = request.form.get("password", "")

        if role not in ["base", "franchise"]:
            role = "base"
        if not responsible_name or not organization_name or not username or not password:
            flash("Preencha todos os campos obrigatórios.", "warning")
            return redirect(url_for("register"))
        if not valid_username(username):
            flash("Use um nome de usuário com 3 a 40 caracteres: letras, números, ponto, hífen ou underline.", "warning")
            return redirect(url_for("register"))
        if get_user_by_username(username) is not None:
            flash("Já existe cadastro com esse nome de usuário.", "warning")
            return redirect(url_for("register"))

        try:
            with db_connect() as conn:
                conn.execute(
                    """
                    INSERT INTO users (responsible_name, organization_name, username, email, password_hash, role, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (responsible_name, organization_name, username, email, generate_password_hash(password), role, now_iso()),
                )
                conn.commit()
            flash("Cadastro enviado. Aguarde aprovação de um administrador.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Já existe cadastro com esse nome de usuário.", "warning")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do portal.", "success")
    return redirect(url_for("login"))


# ---------- API Usuário ----------

@app.get("/api/products")
@login_required
@page_access_required("home")
def api_products():
    user = require_current_user()
    q = request.args.get("q", "").strip()
    sql = "SELECT * FROM products WHERE active = 1"
    params: list[Any] = []
    if q:
        like = f"%{q}%"
        sql += " AND (name LIKE ? OR category LIKE ? OR description LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY category ASC, name ASC"
    with db_connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    products = [product for row in rows if (product := row_to_product(row)) is not None]
    return jsonify([product_to_api(product, user) for product in products])


@app.post("/api/requests")
@login_required
@page_access_required("home")
def api_create_request():
    user = require_current_user()
    payload = request.get_json(silent=True) or {}
    normalized, error = validate_items_for_user(payload.get("items"), user)
    if error:
        return jsonify({"ok": False, "message": error}), 400

    user_note = str(payload.get("user_note") or "").strip()
    with db_connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO supply_requests (user_id, status, user_note, admin_note, created_at)
            VALUES (?, 'pending', ?, '', ?)
            """,
            (user.id, user_note, now_iso()),
        )
        request_id = get_cursor_lastrowid(cursor)
        if request_id is None:
            conn.rollback()
            return jsonify({"ok": False, "message": "Não foi possível registrar a solicitação."}), 500

        for product, quantity in normalized:
            conn.execute(
                """
                INSERT INTO request_items (request_id, product_id, product_name_snapshot, quantity, price_cents_snapshot)
                VALUES (?, ?, ?, ?, ?)
                """,
                (request_id, product.id, product.name, quantity, product.price_cents),
            )
        conn.commit()

    return jsonify({"ok": True, "message": "Solicitação enviada para aprovação.", "request_id": request_id})


@app.get("/minhas-solicitacoes")
@login_required
@page_access_required("my_requests")
def my_requests():
    user = require_current_user()
    requests_list = list_supply_requests(user_id=user.id)
    return render_template("my_requests.html", requests_list=requests_list)




@app.get("/solicitacoes/<int:request_id>/pdf")
@login_required
def request_pdf(request_id: int):
    viewer = require_current_user()
    supply_request = get_supply_request(request_id)
    if supply_request is None:
        abort(404)
    if not viewer.is_admin and supply_request.user_id != viewer.id:
        abort(403)

    requester = supply_request.user
    org_name = requester.organization_name if requester else "solicitacao"
    filename = f"solicitacao_{supply_request.id}_{safe_filename(org_name)}.pdf"
    buffer = build_request_pdf(supply_request, viewer)
    store_generated_file(
        storage_key("pdfs", str(supply_request.id), filename),
        buffer,
        "application/pdf",
        {"request_id": str(supply_request.id), "organization": org_name},
    )
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


# ---------- Admin ----------

@app.route("/admin")
@admin_required
@page_access_required("admin_dashboard")
def admin_dashboard():
    with db_connect() as conn:
        counts = {
            "users_pending": conn.execute("SELECT COUNT(*) AS total FROM users WHERE status = 'pending'").fetchone()["total"],
            "requests_pending": conn.execute("SELECT COUNT(*) AS total FROM supply_requests WHERE status = 'pending'").fetchone()["total"],
            "products": conn.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"],
            "stock_total": conn.execute("SELECT COALESCE(SUM(stock_quantity), 0) AS total FROM products").fetchone()["total"],
        }
        low_rows = conn.execute("SELECT * FROM products WHERE stock_quantity <= 20 ORDER BY stock_quantity ASC LIMIT 8").fetchall()
    low_stock = [product for row in low_rows if (product := row_to_product(row)) is not None]
    latest_requests = list_supply_requests(limit=8)
    return render_template("admin/dashboard.html", counts=counts, low_stock=low_stock, latest_requests=latest_requests)


@app.route("/admin/users")
@admin_required
@page_access_required("admin_users")
def admin_users():
    selected_status = request.args.get("status", "")
    sql = "SELECT * FROM users"
    params: list[Any] = []
    if selected_status:
        sql += " WHERE status = ?"
        params.append(selected_status)
    sql += " ORDER BY created_at DESC"
    with db_connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    users = [user for row in rows if (user := row_to_user(row)) is not None]
    return render_template("admin/users.html", users=users, selected_status=selected_status)


@app.route("/admin/users/new", methods=["GET", "POST"])
@admin_required
@page_access_required("admin_users")
def admin_user_new():
    if request.method == "POST":
        responsible_name = request.form.get("responsible_name", "").strip()
        organization_name = request.form.get("organization_name", "").strip()
        username = normalize_username(request.form.get("username", ""))
        email = synthetic_email_for_username(username)
        password = request.form.get("password", "")
        role = request.form.get("role", "base").strip()
        status = request.form.get("status", "approved").strip()
        selected_pages = request.form.getlist("page_permissions") or list(default_page_keys_for_role(role))

        if role not in ["base", "franchise", "admin"]:
            role = "base"
        if status not in ["pending", "approved", "rejected"]:
            status = "approved"
        selected_pages = [key for key in selected_pages if key in default_page_keys_for_role(role)]
        if not selected_pages:
            selected_pages = list(default_page_keys_for_role(role))
        if not responsible_name or not organization_name or not username or not password:
            flash("Preencha responsável, unidade, nome de usuário e senha.", "danger")
            return render_template("admin/user_form.html", user=None, is_new=True, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))
        if not valid_username(username):
            flash("Use um nome de usuário com 3 a 40 caracteres: letras, números, ponto, hífen ou underline.", "danger")
            return render_template("admin/user_form.html", user=None, is_new=True, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))
        if get_user_by_username(username) is not None:
            flash("Já existe usuário cadastrado com este nome de usuário.", "danger")
            return render_template("admin/user_form.html", user=None, is_new=True, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))

        with db_connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (responsible_name, organization_name, username, email, password_hash, role, status, created_at, page_permissions_configured)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (responsible_name, organization_name, username, email, generate_password_hash(password), role, status, now_iso()),
            )
            new_user_id = get_cursor_lastrowid(cursor)
            if new_user_id is None:
                conn.rollback()
                flash("Não foi possível adicionar o usuário.", "danger")
                return render_template("admin/user_form.html", user=None, is_new=True, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))
            save_user_page_permissions(conn, new_user_id, role, selected_pages)
            conn.commit()

        flash("Usuário adicionado com sucesso.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin/user_form.html", user=None, is_new=True, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=default_page_keys_for_role("base"))


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
@page_access_required("admin_users")
def admin_user_edit(user_id: int):
    target = get_user(user_id)
    if target is None:
        abort(404)

    current = require_current_user()

    if request.method == "POST":
        responsible_name = request.form.get("responsible_name", "").strip()
        organization_name = request.form.get("organization_name", "").strip()
        username = normalize_username(request.form.get("username", ""))
        email = synthetic_email_for_username(username)
        role = request.form.get("role", "base").strip()
        status = request.form.get("status", "approved").strip()
        password = request.form.get("password", "")
        selected_pages = request.form.getlist("page_permissions")

        if role not in ["base", "franchise", "admin"]:
            role = "base"
        if status not in ["pending", "approved", "rejected"]:
            status = "approved"

        # Segurança: o admin logado não pode remover o próprio acesso administrativo
        # nem bloquear a própria conta sem querer.
        if target.id == current.id:
            role = "admin"
            status = "approved"
            selected_pages = list(default_page_keys_for_role("admin"))

        selected_pages = [key for key in selected_pages if key in default_page_keys_for_role(role)]
        if not selected_pages:
            selected_pages = list(default_page_keys_for_role(role))

        if not responsible_name or not organization_name or not username:
            flash("Preencha responsável, unidade e nome de usuário.", "danger")
            return render_template("admin/user_form.html", user=target, is_new=False, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))
        if not valid_username(username):
            flash("Use um nome de usuário com 3 a 40 caracteres: letras, números, ponto, hífen ou underline.", "danger")
            return render_template("admin/user_form.html", user=target, is_new=False, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))

        with db_connect() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE lower(username) = lower(?) AND id <> ?",
                (username, user_id),
            ).fetchone()
            if existing is not None:
                flash("Já existe outro usuário cadastrado com este nome de usuário.", "danger")
                return render_template("admin/user_form.html", user=target, is_new=False, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))

            if password:
                conn.execute(
                    """
                    UPDATE users
                       SET responsible_name = ?, organization_name = ?, username = ?, email = ?, password_hash = ?, role = ?, status = ?, updated_at = ?
                     WHERE id = ?
                    """,
                    (responsible_name, organization_name, username, email, generate_password_hash(password), role, status, now_iso(), user_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE users
                       SET responsible_name = ?, organization_name = ?, username = ?, email = ?, role = ?, status = ?, updated_at = ?
                     WHERE id = ?
                    """,
                    (responsible_name, organization_name, username, email, role, status, now_iso(), user_id),
                )
            save_user_page_permissions(conn, user_id, role, selected_pages)
            conn.commit()

        flash("Acesso do usuário atualizado.", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin/user_form.html", user=target, is_new=False, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=selected_permissions_for_form(target))


@app.post("/admin/users/<int:user_id>/status")
@admin_required
@page_access_required("admin_users")
def admin_user_status(user_id: int):
    target = get_user(user_id)
    if target is None:
        abort(404)
    action = request.form.get("action")
    current = require_current_user()
    if target.is_admin and target.id == current.id and action != "approved":
        flash("Você não pode bloquear seu próprio usuário admin.", "warning")
        return redirect(url_for("admin_users"))
    if action not in ["approved", "rejected", "pending"]:
        abort(400)
    with db_connect() as conn:
        conn.execute("UPDATE users SET status = ?, updated_at = ? WHERE id = ?", (action, now_iso(), user_id))
        conn.commit()
    flash("Status do usuário atualizado.", "success")
    return redirect(request.referrer or url_for("admin_users"))


@app.post("/admin/users/<int:user_id>/delete")
@admin_required
@page_access_required("admin_users")
def admin_user_delete(user_id: int):
    target = get_user(user_id)
    if target is None:
        abort(404)
    current = require_current_user()
    if target.is_admin and target.id == current.id:
        flash("Você não pode excluir seu próprio usuário admin.", "warning")
        return redirect(url_for("admin_users"))
    with db_connect() as conn:
        if target.is_admin:
            approved_admins = conn.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin' AND status = 'approved'").fetchone()["total"]
            if approved_admins <= 1 and target.status == "approved":
                flash("Não é possível excluir o último administrador aprovado.", "warning")
                return redirect(url_for("admin_users"))
        total = conn.execute("SELECT COUNT(*) AS total FROM supply_requests WHERE user_id = ?", (user_id,)).fetchone()["total"]
        if total:
            conn.execute("UPDATE users SET status = 'rejected', updated_at = ? WHERE id = ?", (now_iso(), user_id))
            conn.commit()
            flash("Usuário possui solicitações vinculadas; o cadastro foi recusado/desativado em vez de excluído.", "warning")
        else:
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            flash("Usuário excluído.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/products")
@admin_required
@page_access_required("admin_products")
def admin_products():
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY active DESC, category ASC, name ASC").fetchall()
    products = [product for row in rows if (product := row_to_product(row)) is not None]
    return render_template("admin/products.html", products=products)




@app.get("/admin/products/export")
@admin_required
@page_access_required("admin_products")
def admin_products_export():
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY active DESC, category ASC, name ASC").fetchall()
    products = [product for row in rows if (product := row_to_product(row)) is not None]

    export_language = (request.args.get("lang") or "pt").strip().lower()
    if export_language in {"zh", "zh-cn", "zh-hans", "zh-tw", "mandarin", "mandarim", "chinese", "simplified"}:
        export_language = "zh"
    else:
        export_language = "pt"

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "产品" if export_language == "zh" else "Produtos"
    headers = PRODUCT_EXPORT_HEADERS_ZH if export_language == "zh" else PRODUCT_EXPORT_HEADERS_PT
    worksheet.append(headers)
    for product in products:
        worksheet.append(product_row_for_excel_language(product, export_language))

    header_fill = PatternFill("solid", fgColor="E60012")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="DDDDDD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="center")
        if len(row) >= 7:
            row[6].number_format = 'R$ #,##0.00'
    widths = [10, 38, 24, 24, 48, 18, 18, 22, 24, 18, 18, 14]
    for idx, width in enumerate(widths, start=1):
        worksheet.column_dimensions[get_column_letter(idx)].width = width
    worksheet.freeze_panes = "A2"

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    language_label = "chines_simplificado" if export_language == "zh" else "portugues"
    filename = f"produtos_jt_insumos_{language_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    store_generated_file(
        storage_key("exports", filename),
        buffer,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        {"type": "products_export"},
    )
    buffer.seek(0)
    return send_file(buffer, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=filename)


@app.post("/admin/products/import")
@admin_required
@page_access_required("admin_products")
def admin_products_import():
    uploaded = request.files.get("spreadsheet")
    if uploaded is None or not uploaded.filename:
        flash("Selecione uma planilha .xlsx para importar.", "warning")
        return redirect(url_for("admin_products"))
    if not uploaded.filename.lower().endswith(".xlsx"):
        flash("Importe apenas arquivos .xlsx.", "warning")
        return redirect(url_for("admin_products"))

    try:
        uploaded_bytes = uploaded.read()
        if uploaded_bytes:
            upload_bytes_to_r2(
                storage_key("imports", datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + safe_filename(uploaded.filename)),
                uploaded_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                {"type": "products_import"},
            )
        workbook = load_workbook(BytesIO(uploaded_bytes), data_only=True)
        worksheet = workbook.active
    except Exception:
        flash("Não foi possível ler a planilha. Verifique se o arquivo está em formato .xlsx válido.", "danger")
        return redirect(url_for("admin_products"))

    first_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not first_row:
        flash("A planilha está vazia.", "warning")
        return redirect(url_for("admin_products"))
    header_map = {normalize_header(value): index for index, value in enumerate(first_row) if value is not None}

    created = 0
    updated = 0
    skipped = 0
    with db_connect() as conn:
        for row_values_tuple in worksheet.iter_rows(min_row=2, values_only=True):
            row_values = list(row_values_tuple)
            if not any(value is not None and str(value).strip() for value in row_values):
                continue

            product_id = parse_optional_int(get_header_value(row_values, header_map, ["ID", "Código", "Codigo"]))
            name = str(get_header_value(row_values, header_map, ["Nome do produto", "Nome", "Produto", "Insumo", "产品名称", "产品名称"]) or "").strip()
            if not name:
                skipped += 1
                continue

            category = str(get_header_value(row_values, header_map, ["Categoria", "类别", "类别"]) or "").strip()
            unit_measure = str(get_header_value(row_values, header_map, ["Unidade de medida", "Unidade", "Unid.", "Unid", "UM", "Medida", "计量单位", "计量单位", "单位", "单位"]) or "un").strip() or "un"
            description = str(get_header_value(row_values, header_map, ["Descrição", "Descricao", "描述", "说明", "说明"]) or "").strip()
            stock_quantity = parse_optional_int(get_header_value(row_values, header_map, ["Estoque disponível", "Estoque disponivel", "Estoque", "Quantidade", "可用库存", "可用库存", "库存", "库存"])) or 0
            price_cents = parse_money_to_cents(get_header_value(row_values, header_map, ["Valor unitário", "Valor unitario", "Valor", "Preço", "Preco", "单价", "单价", "价格", "价格"]))
            limit_base = parse_optional_int(get_header_value(row_values, header_map, ["Limite para bases", "Limite base", "Base", "基地限制"]))
            limit_franchise = parse_optional_int(get_header_value(row_values, header_map, ["Limite para franquias", "Limite franquia", "Franquia", "加盟店限制"]))
            min_stock = parse_optional_int(get_header_value(row_values, header_map, ["Estoque mínimo", "Estoque minimo", "Mínimo", "Minimo", "Min stock", "最低库存", "最低库存"]))
            max_stock = parse_optional_int(get_header_value(row_values, header_map, ["Estoque máximo", "Estoque maximo", "Máximo", "Maximo", "Max stock", "最高库存", "最高库存"]))
            active = parse_bool_value(get_header_value(row_values, header_map, ["Ativo", "Status", "Produto ativo", "启用", "启用"]), default=True)

            existing_row = None
            if product_id is not None:
                existing_row = conn.execute("SELECT id, stock_quantity FROM products WHERE id = ?", (product_id,)).fetchone()
            if existing_row is None:
                existing_row = conn.execute("SELECT id, stock_quantity FROM products WHERE lower(name) = lower(?)", (name,)).fetchone()

            if existing_row is not None:
                conn.execute(
                    """
                    UPDATE products
                       SET name = ?, category = ?, unit_measure = ?, description = ?, stock_quantity = ?, price_cents = ?,
                           limit_base = ?, limit_franchise = ?, min_stock = ?, max_stock = ?, active = ?, updated_at = ?
                     WHERE id = ?
                    """,
                    (name, category, unit_measure, description, stock_quantity, price_cents, limit_base, limit_franchise, min_stock, max_stock, 1 if active else 0, now_iso(), int(existing_row["id"])),
                )
                old_stock = int(existing_row["stock_quantity"] or 0)
                if old_stock != stock_quantity:
                    record_stock_movement(
                        conn,
                        product_id=int(existing_row["id"]),
                        quantity_delta=stock_quantity - old_stock,
                        stock_before=old_stock,
                        stock_after=stock_quantity,
                        movement_type="import_adjustment",
                        note="Estoque atualizado por importação de planilha.",
                        created_by_id=require_current_user().id,
                    )
                updated += 1
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO products (name, category, unit_measure, description, stock_quantity, price_cents, limit_base, limit_franchise, min_stock, max_stock, active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (name, category, unit_measure, description, stock_quantity, price_cents, limit_base, limit_franchise, min_stock, max_stock, 1 if active else 0, now_iso()),
                )
                if stock_quantity > 0:
                    row_id = get_cursor_lastrowid(cursor)
                    if row_id is not None:
                        record_stock_movement(conn, int(row_id), stock_quantity, 0, stock_quantity, "product_created", "Produto criado por importação.", created_by_id=require_current_user().id)
                created += 1
        conn.commit()

    flash(f"Importação concluída: {created} criado(s), {updated} atualizado(s), {skipped} ignorado(s).", "success")
    return redirect(url_for("admin_products"))


@app.route("/admin/products/new", methods=["GET", "POST"])
@admin_required
@page_access_required("admin_products")
def admin_product_new():
    if request.method == "POST":
        product = fill_product_from_form(Product())
        if not product.name:
            flash("Informe o nome do produto.", "warning")
            return redirect(url_for("admin_product_new"))
        with db_connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO products (name, category, unit_measure, description, stock_quantity, price_cents, limit_base, limit_franchise, min_stock, max_stock, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.name,
                    product.category,
                    product.unit_measure,
                    product.description,
                    product.stock_quantity,
                    product.price_cents,
                    product.limit_base,
                    product.limit_franchise,
                    product.min_stock,
                    product.max_stock,
                    1 if product.active else 0,
                    now_iso(),
                ),
            )
            new_id = get_cursor_lastrowid(cursor)
            if product.stock_quantity > 0 and new_id is not None:
                record_stock_movement(conn, int(new_id), product.stock_quantity, 0, product.stock_quantity, "product_created", "Produto cadastrado manualmente.", created_by_id=require_current_user().id)
            conn.commit()
        flash("Produto cadastrado.", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=None)


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
@page_access_required("admin_products")
def admin_product_edit(product_id: int):
    product = get_product(product_id)
    if product is None:
        abort(404)
    if request.method == "POST":
        old_stock_quantity = product.stock_quantity
        fill_product_from_form(product)
        if not product.name:
            flash("Informe o nome do produto.", "warning")
            return redirect(url_for("admin_product_edit", product_id=product_id))
        with db_connect() as conn:
            conn.execute(
                """
                UPDATE products
                SET name = ?, category = ?, unit_measure = ?, description = ?, stock_quantity = ?, price_cents = ?,
                    limit_base = ?, limit_franchise = ?, min_stock = ?, max_stock = ?, active = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    product.name,
                    product.category,
                    product.unit_measure,
                    product.description,
                    product.stock_quantity,
                    product.price_cents,
                    product.limit_base,
                    product.limit_franchise,
                    product.min_stock,
                    product.max_stock,
                    1 if product.active else 0,
                    now_iso(),
                    product_id,
                ),
            )
            if old_stock_quantity != product.stock_quantity:
                record_stock_movement(conn, product_id, product.stock_quantity - old_stock_quantity, old_stock_quantity, product.stock_quantity, "manual_adjustment", "Estoque alterado na edição do produto.", created_by_id=require_current_user().id)
            conn.commit()
        flash("Produto atualizado.", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=product)


@app.post("/admin/products/<int:product_id>/delete")
@admin_required
@page_access_required("admin_products")
def admin_product_delete(product_id: int):
    if get_product(product_id) is None:
        abort(404)
    with db_connect() as conn:
        conn.execute("UPDATE products SET active = 0, updated_at = ? WHERE id = ?", (now_iso(), product_id))
        conn.commit()
    flash("Produto desativado.", "success")
    return redirect(url_for("admin_products"))


@app.route("/admin/requests")
@admin_required
@page_access_required("admin_requests")
def admin_requests():
    selected_status = request.args.get("status", "")
    requests_list = list_supply_requests(status=selected_status)
    return render_template("admin/requests.html", requests_list=requests_list, selected_status=selected_status)


@app.route("/admin/requests/attended")
@admin_required
@page_access_required("admin_requests_attended")
def admin_requests_attended():
    requests_list = list_supply_requests(status="approved")
    return render_template("admin/requests_attended.html", requests_list=requests_list, selected_status="approved")


@app.route("/admin/stock")
@admin_required
@page_access_required("admin_stock")
def admin_stock():
    with db_connect() as conn:
        product_rows = conn.execute("SELECT * FROM products ORDER BY active DESC, category ASC, name ASC").fetchall()
        movement_rows = conn.execute(
            """
            SELECT sm.*, p.name AS product_name, p.category AS product_category, u.responsible_name AS created_by_name
              FROM stock_movements sm
              LEFT JOIN products p ON p.id = sm.product_id
              LEFT JOIN users u ON u.id = sm.created_by_id
             ORDER BY sm.created_at DESC, sm.id DESC
             LIMIT 200
            """
        ).fetchall()
        totals = {
            "products": conn.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"],
            "stock_total": conn.execute("SELECT COALESCE(SUM(stock_quantity), 0) AS total FROM products").fetchone()["total"],
            "critical": conn.execute("SELECT COUNT(*) AS total FROM products WHERE min_stock IS NOT NULL AND stock_quantity <= min_stock").fetchone()["total"],
            "movements": conn.execute("SELECT COUNT(*) AS total FROM stock_movements").fetchone()["total"],
        }

    products = [product for row in product_rows if (product := row_to_product(row)) is not None]

    stock_rows: list[dict[str, Any]] = []
    for product in products:
        status = stock_status_class(product)
        maximum = product.max_stock if product.max_stock and product.max_stock > 0 else None
        minimum = product.min_stock if product.min_stock and product.min_stock > 0 else None
        reference = maximum or max(product.stock_quantity, minimum or 0, 1)
        percent = int(min(100, max(0, (product.stock_quantity / reference) * 100)))
        stock_rows.append({
            "product": product,
            "status": status,
            "label": stock_status_label(product),
            "percent": percent,
            "min": product.min_stock,
            "max": product.max_stock,
        })

    totals["healthy"] = sum(1 for row in stock_rows if row["status"] == "good")
    totals["normal"] = sum(1 for row in stock_rows if row["status"] == "normal")

    risk_rows = [row for row in stock_rows if row["status"] == "critical"]
    if not risk_rows:
        risk_rows = stock_rows[:6]

    chart_products = []
    category_map: dict[str, dict[str, Any]] = {}
    for row in stock_rows:
        product = row["product"]
        category = product.category or "Sem categoria"
        chart_products.append({
            "id": product.id,
            "name": product.name,
            "category": category,
            "stock": product.stock_quantity,
            "min": product.min_stock or 0,
            "max": product.max_stock or 0,
            "status": row["status"],
            "label": row["label"],
        })
        bucket = category_map.setdefault(category, {
            "category": category,
            "stock": 0,
            "min": 0,
            "max": 0,
            "products": 0,
            "critical": 0,
            "good": 0,
            "normal": 0,
        })
        bucket["stock"] += product.stock_quantity
        bucket["min"] += product.min_stock or 0
        bucket["max"] += product.max_stock or 0
        bucket["products"] += 1
        bucket[row["status"]] += 1

    chart_categories = sorted(category_map.values(), key=lambda item: item["category"].lower())

    return render_template(
        "admin/stock.html",
        products=products,
        stock_rows=stock_rows,
        risk_rows=risk_rows[:8],
        movement_rows=movement_rows,
        totals=totals,
        chart_products=chart_products,
        chart_categories=chart_categories,
        movement_type_label=movement_type_label,
    )


@app.route("/admin/requests/<int:request_id>")
@admin_required
@page_access_any_required(["admin_requests", "admin_requests_attended"])
def admin_request_detail(request_id: int):
    supply_request = get_supply_request(request_id)
    if supply_request is None:
        abort(404)
    return render_template("admin/request_detail.html", supply_request=supply_request)




@app.post("/admin/requests/<int:request_id>/items")
@admin_required
@page_access_required("admin_requests")
def admin_request_update_items(request_id: int):
    supply_request = get_supply_request(request_id)
    if supply_request is None:
        abort(404)
    if supply_request.status != "pending":
        flash("Apenas solicitações pendentes podem ter quantidades editadas.", "warning")
        return redirect(url_for("admin_request_detail", request_id=request_id))

    updated = 0
    with db_connect() as conn:
        for item in supply_request.items:
            quantity = parse_required_positive_int(request.form.get(f"quantity_{item.id}"))
            if quantity is None:
                flash("Todas as quantidades precisam ser maiores que zero.", "warning")
                return redirect(url_for("admin_request_detail", request_id=request_id))
            if quantity != item.quantity:
                conn.execute("UPDATE request_items SET quantity = ? WHERE id = ? AND request_id = ?", (quantity, item.id, request_id))
                updated += 1
        conn.commit()

    flash("Quantidades atualizadas." if updated else "Nenhuma quantidade foi alterada.", "success")
    return redirect(url_for("admin_request_detail", request_id=request_id))


@app.post("/admin/requests/<int:request_id>/approve")
@admin_required
@page_access_required("admin_requests")
def admin_request_approve(request_id: int):
    supply_request = get_supply_request(request_id)
    if supply_request is None:
        abort(404)
    if supply_request.status != "pending":
        flash("Apenas solicitações pendentes podem ser aprovadas.", "warning")
        return redirect(url_for("admin_request_detail", request_id=request_id))

    insufficient: list[str] = []
    for item in supply_request.items:
        product = get_product(item.product_id)
        if product is None or not product.active:
            insufficient.append(item.product_name_snapshot)
        elif item.quantity > product.stock_quantity:
            insufficient.append(f"{product.name} (solicitado {item.quantity}, estoque {product.stock_quantity})")

    if insufficient:
        flash("Estoque insuficiente para aprovar: " + "; ".join(insufficient), "danger")
        return redirect(url_for("admin_request_detail", request_id=request_id))

    admin_note = request.form.get("admin_note", "").strip()
    current = require_current_user()
    with db_connect() as conn:
        for item in supply_request.items:
            product = get_product(item.product_id)
            stock_before = product.stock_quantity if product else 0
            stock_after = stock_before - item.quantity
            conn.execute("UPDATE products SET stock_quantity = ?, updated_at = ? WHERE id = ?", (stock_after, now_iso(), item.product_id))
            record_stock_movement(
                conn,
                product_id=item.product_id,
                request_id=request_id,
                created_by_id=current.id,
                movement_type="request_approved",
                quantity_delta=-item.quantity,
                stock_before=stock_before,
                stock_after=stock_after,
                note=f"Solicitação #{request_id} aprovada.",
            )
        conn.execute(
            """
            UPDATE supply_requests
            SET status = 'approved', reviewed_at = ?, reviewed_by_id = ?, admin_note = ?
            WHERE id = ?
            """,
            (now_iso(), current.id, admin_note, request_id),
        )
        conn.commit()

    flash("Solicitação aprovada e estoque descontado.", "success")
    return redirect(url_for("admin_request_detail", request_id=request_id))


@app.post("/admin/requests/<int:request_id>/reject")
@admin_required
@page_access_required("admin_requests")
def admin_request_reject(request_id: int):
    supply_request = get_supply_request(request_id)
    if supply_request is None:
        abort(404)
    if supply_request.status != "pending":
        flash("Apenas solicitações pendentes podem ser recusadas.", "warning")
        return redirect(url_for("admin_request_detail", request_id=request_id))

    admin_note = request.form.get("admin_note", "").strip()
    current = require_current_user()
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE supply_requests
            SET status = 'rejected', reviewed_at = ?, reviewed_by_id = ?, admin_note = ?
            WHERE id = ?
            """,
            (now_iso(), current.id, admin_note, request_id),
        )
        conn.commit()
    flash("Solicitação recusada.", "success")
    return redirect(url_for("admin_request_detail", request_id=request_id))


@app.post("/admin/requests/<int:request_id>/delete")
@admin_required
@page_access_any_required(["admin_requests", "admin_requests_attended"])
def admin_request_delete(request_id: int):
    if get_supply_request(request_id) is None:
        abort(404)
    current = require_current_user()
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE supply_requests
            SET status = 'deleted', reviewed_at = ?, reviewed_by_id = ?
            WHERE id = ?
            """,
            (now_iso(), current.id, request_id),
        )
        conn.commit()
    flash("Solicitação marcada como excluída.", "success")
    return redirect(url_for("admin_requests"))


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", title="Acesso negado", message="Você não possui permissão para acessar esta página."), 403


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", title="Página não encontrada", message="A página solicitada não existe."), 404


@app.errorhandler(401)
def unauthorized(_):
    return redirect(url_for("login"))


setup_database()


def run_local_server() -> None:
    port = resolve_port()
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    open_browser_when_ready(port)
    print("==============================================")
    print(" Portal de Insumos J&T Express")
    print(f" Endereço local: http://127.0.0.1:{port}")
    print(" Para encerrar, feche esta janela ou pressione CTRL+C.")
    print("==============================================")
    app.run(host="127.0.0.1", port=port, debug=debug_mode, use_reloader=False)


if __name__ == "__main__":
    try:
        run_local_server()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    except Exception as exc:
        print("\nERRO AO ABRIR O PORTAL:")
        print(type(exc).__name__, "-", exc)
        print("\nTente rodar o arquivo ABRIR_PORTAL.bat para instalar dependências e abrir o sistema.")
        input("\nPressione Enter para fechar...")
        raise
