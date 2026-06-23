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
from html import escape as html_escape
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
    has_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
import requests
from werkzeug.security import check_password_hash, generate_password_hash

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from svglib.svglib import svg2rlg

from cloudflare_d1 import cloudflare_d1_connect_from_env
from cloudflare_r2 import upload_bytes_to_r2

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

# Fonte CJK para PDFs. As fontes padrão do ReportLab (Helvetica) não
# renderizam caracteres chineses, por isso o PDF acabava mostrando
# quadradinhos/caixas pretas. STSong-Light é uma fonte CID nativa do
# ReportLab/Adobe para chinês simplificado e também segura para textos mistos.
PDF_TEXT_FONT = "Helvetica"
PDF_TEXT_FONT_BOLD = "Helvetica-Bold"
try:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    registerFontFamily(
        "STSong-Light",
        normal="STSong-Light",
        bold="STSong-Light",
        italic="STSong-Light",
        boldItalic="STSong-Light",
    )
    PDF_TEXT_FONT = "STSong-Light"
    PDF_TEXT_FONT_BOLD = "STSong-Light"
except Exception as exc:
    print(f"[PDF] Aviso: não foi possível registrar fonte chinesa STSong-Light: {exc}")

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

FEISHU_STOCK_WEBHOOK_URL = os.getenv(
    "FEISHU_STOCK_WEBHOOK_URL",
    "https://open.feishu.cn/open-apis/bot/v2/hook/0759b1b1-b0ac-413b-8672-c113012c14db",
).strip()
PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    os.getenv("APP_PUBLIC_URL", os.getenv("RENDER_EXTERNAL_URL", "")),
).strip().rstrip("/")


# Lista oficial de bases/franquias para cadastro e administração de usuários.
BASE_FRANCHISE_OPTIONS_RAW = """ABC-MG
AET -MG
AFS -MG
AGF -MG
AMN -MG
AUI -MG
BCA -MG
BDA-MG
BHM-MG
BHZ 03-MG
BHZ 04-MG
BHZ 05-MG
BHZ 06-MG
BMN -MG
BTM 02-MG
BTM -MG
CAZ-MG
CGE -MG
CPA -MG
CRL -MG
CSP -MG
CTG -MG
CUV -MG
DIQ 02-MG
DIQ -MG
DMA -MG
ELD-MG
EXT -MG
F AAD-MG
F AAX-MG
F ADD-MG
F ALP 02-MG
F BCA-MG
F BCV-MG
F BDP-MG
F BHZ 08-MG
F BHZ 10-MG
F BHZ-MG
F CAR 02-MG
F CET-MG
F CGS-MG
F CLT-MG
F CMB-MG
F COG-MG
F CPA-MG
F CRT-MG
F DEL-MG
F DIV-MG
F EXT-MG
F FMG-MG
F GXP-MG
F IAJ-MG
F IAN-MG
F IMA-MG
F IRO-MG
F IRT-MG
F JDF 02-MG
F JDF 03-MG
F JDF 04-MG
F JDF-MG
F JPN-MG
F LGP-MG
F LPL-MG
F MNT-MG
F MPB-MG
F MRC-MG
F MTA-MG
F MTL-MG
F MTS-MG
F NSR-MG
F OPT-MG
F ORB-MG
F PDS-MG
F PLE-MG
F PMN-MG
F PPY 02-MG
F PSS-MG
F SAB-MG
F SGT-MG
F SJN-MG
F SSP-MG
F STD-MG
F STL-MG
F STS-MG
F TMN-MG
F TPT-MG
F TRC-MG
F UBE-MG
F UNI-MG
F VSR-MG
FAB-MG
FRT -MG
FUN-MG
GHE -MG
GVR -MG
IBR -MG
IGP-MG
IPN 02-MG
IPN -MG
IRM -MG
ITA -MG
ITU -MG
JDI-MG
JMV -MG
JNA -MG
JTB -MG
JUB -MG
LAS -MG
LGP -MG
LGS-MG
MNH -MG
MRE -MG
MTC -MG
NVL -MG
OLV -MG
OPT -MG
ORP-MG
PDE-MG
POJ -MG
POO -MG
PPR -MG
PPY -MG
PSS -MG
PTC -MG
PTN -MG
PTU -MG
QDF -MG
RDN 02-MG
RDN -MG
SAB -MG
SGF-MG
SJD -MG
SLN -MG
SON-MG
STL -MG
STZ -MG
SZD-MG
TFL -MG
UAB -MG
UBA 02-MG
UBA 03-MG
UBA -MG
UDI 02-MG
UDI -MG
VAG -MG
VCS -MG
VPS -MG
BDC-MG
JDF-MG"""
def _unit_sort_key(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).upper()


BASE_FRANCHISE_OPTIONS = sorted(
    list(dict.fromkeys(line.strip() for line in BASE_FRANCHISE_OPTIONS_RAW.splitlines() if line.strip())),
    key=_unit_sort_key,
)
# Franquias são as unidades com prefixo oficial "F " na lista.
FRANCHISE_UNIT_OPTIONS = [unit for unit in BASE_FRANCHISE_OPTIONS if unit.upper().startswith("F ")]
# Bases são todas as demais unidades da lista oficial.
BASE_UNIT_OPTIONS = [unit for unit in BASE_FRANCHISE_OPTIONS if not unit.upper().startswith("F ")]
BASE_FRANCHISE_OPTION_SET = set(BASE_FRANCHISE_OPTIONS)
BASE_UNIT_OPTION_SET = set(BASE_UNIT_OPTIONS)
FRANCHISE_UNIT_OPTION_SET = set(FRANCHISE_UNIT_OPTIONS)
ASSET_REGIONAL_OPTIONS = ["MG", "SPN", "Matriz"]
ASSET_REGIONAL_OPTION_SET = {option.upper() for option in ASSET_REGIONAL_OPTIONS}
ADMIN_ORGANIZATION_NAME = "ADMINISTRAÇÃO"
ADMIN_ORGANIZATION_OPTIONS = [ADMIN_ORGANIZATION_NAME]


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
    people_count: int | None
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by_id: int | None = None
    user: User | None = None
    items: list[RequestItem] = field(default_factory=list)

    @property
    def total_cents(self) -> int:
        return sum((item.price_cents_snapshot or 0) * item.quantity for item in self.items)


@dataclass
class AssetItem:
    id: int
    asset_id: int
    item_name: str
    product_id: int | None = None
    quantity: int = 1
    serial_number: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AssetRecord:
    id: int
    name: str
    base: str
    regional: str
    sector: str
    manager: str
    created_at: datetime
    updated_at: datetime | None = None
    created_by_id: int | None = None
    items: list[AssetItem] = field(default_factory=list)


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




def valid_organization_for_role(organization_name: str, role: str) -> bool:
    organization_name = (organization_name or "").strip()
    if role == "base":
        return organization_name in BASE_UNIT_OPTION_SET
    if role == "franchise":
        return organization_name in FRANCHISE_UNIT_OPTION_SET
    if role == "admin":
        return bool(organization_name) and len(organization_name) <= 120
    return False

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
        people_count=int(row["people_count"] or 0) if "people_count" in row.keys() and row["people_count"] is not None else None,
        created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
        reviewed_at=parse_dt(row["reviewed_at"]),
        reviewed_by_id=row["reviewed_by_id"],
    )
    if include_user:
        req.user = get_user(req.user_id)
    if include_items:
        req.items = get_request_items(req.id)
    return req


def row_to_asset_item(row: Any | None) -> AssetItem | None:
    if row is None:
        return None
    row_keys = set(row.keys()) if hasattr(row, "keys") else set()
    product_id = row["product_id"] if "product_id" in row_keys else None
    quantity = row["quantity"] if "quantity" in row_keys else 1
    return AssetItem(
        id=int(row["id"]),
        asset_id=int(row["asset_id"]),
        item_name=row["item_name"] or "",
        product_id=int(product_id) if product_id else None,
        quantity=int(quantity or 1),
        serial_number=row["serial_number"] or "",
        created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
    )


def get_asset_items(conn: Any, asset_id: int) -> list[AssetItem]:
    rows = conn.execute(
        "SELECT * FROM asset_items WHERE asset_id = ? ORDER BY id ASC",
        (asset_id,),
    ).fetchall()
    return [item for row in rows if (item := row_to_asset_item(row)) is not None]


def row_to_asset(row: Any | None, conn: Any | None = None, include_items: bool = True) -> AssetRecord | None:
    if row is None:
        return None
    asset = AssetRecord(
        id=int(row["id"]),
        name=row["name"] or "",
        base=row["base"] or "",
        regional=row["regional"] or "",
        sector=row["sector"] or "",
        manager=row["manager"] or "",
        created_by_id=row["created_by_id"],
        created_at=parse_dt(row["created_at"]) or datetime.utcnow(),
        updated_at=parse_dt(row["updated_at"]),
    )
    if include_items:
        if conn is not None:
            asset.items = get_asset_items(conn, asset.id)
        else:
            with db_connect() as local_conn:
                asset.items = get_asset_items(local_conn, asset.id)
    return asset


def list_assets(base: str = "", regional: str = "") -> list[AssetRecord]:
    sql = "SELECT * FROM assets"
    params: list[Any] = []
    clauses: list[str] = []
    if base:
        clauses.append("base = ?")
        params.append(base)
    if regional:
        clauses.append("regional = ?")
        params.append(regional)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC, id DESC"
    with db_connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [asset for row in rows if (asset := row_to_asset(row, conn=conn)) is not None]


def get_asset(asset_id: int) -> AssetRecord | None:
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM assets WHERE id = ?", (int(asset_id),)).fetchone()
        return row_to_asset(row, conn=conn)


def normalize_asset_regional(value: str) -> str:
    normalized = (value or "").strip().upper()
    if normalized == "MATRIZ":
        return "Matriz"
    if normalized in {"MG", "SPN"}:
        return normalized
    return ""


def asset_regional_for_base(base: str) -> str:
    normalized = (base or "").strip().upper()
    if "-MG" in normalized:
        return "MG"
    if "-SP" in normalized:
        return "SPN"
    return ""


def base_options_for_asset_regional(regional: str = "") -> list[str]:
    """Opções de unidade para Gestão de Ativos.

    Diferente do cadastro de usuários, a gestão de ativos deve listar bases e
    franquias. Mantemos o nome da função por compatibilidade com o restante do
    código, mas a origem correta aqui é BASE_FRANCHISE_OPTIONS.
    """
    normalized = normalize_asset_regional(regional)
    if not normalized:
        return BASE_FRANCHISE_OPTIONS
    if normalized == "Matriz":
        return []
    return [unit for unit in BASE_FRANCHISE_OPTIONS if asset_regional_for_base(unit) == normalized]


def base_unit_options_for_asset_regional(regional: str = "") -> list[str]:
    normalized = normalize_asset_regional(regional)
    options = BASE_UNIT_OPTIONS
    if normalized and normalized != "Matriz":
        options = [unit for unit in options if asset_regional_for_base(unit) == normalized]
    elif normalized == "Matriz":
        options = []
    return options


def franchise_unit_options_for_asset_regional(regional: str = "") -> list[str]:
    normalized = normalize_asset_regional(regional)
    options = FRANCHISE_UNIT_OPTIONS
    if normalized and normalized != "Matriz":
        options = [unit for unit in options if asset_regional_for_base(unit) == normalized]
    elif normalized == "Matriz":
        options = []
    return options


def validate_unit_selection(base: str, franchise: str, *, required: bool = False) -> tuple[str, str]:
    """Valida seleção separada de base/franquia.

    Retorna (unidade, tipo), onde tipo é "base", "franchise" ou "".
    """
    base = (base or "").strip()
    franchise = (franchise or "").strip()
    if base and franchise:
        raise ValueError("Selecione somente uma base ou uma franquia, não as duas.")
    if required and not base and not franchise:
        raise ValueError("Selecione obrigatoriamente uma base ou uma franquia para gerar o relatório.")
    if base:
        if base not in BASE_UNIT_OPTION_SET:
            raise ValueError("Base selecionada inválida.")
        return base, "base"
    if franchise:
        if franchise not in FRANCHISE_UNIT_OPTION_SET:
            raise ValueError("Franquia selecionada inválida.")
        return franchise, "franchise"
    return "", ""


def unit_kind_label(kind: str) -> str:
    if kind == "all":
        return "Todas as unidades"
    return "Franquia" if kind == "franchise" else "Base" if kind == "base" else "Unidade"


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

        supply_request_columns = {row["name"] for row in conn.execute("PRAGMA table_info(supply_requests)").fetchall()}
        if "people_count" not in supply_request_columns:
            conn.execute("ALTER TABLE supply_requests ADD COLUMN people_count INTEGER")

        product_columns = {row["name"] for row in conn.execute("PRAGMA table_info(products)").fetchall()}
        if "unit_measure" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN unit_measure TEXT NOT NULL DEFAULT 'un'")
        if "min_stock" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN min_stock INTEGER")
        if "max_stock" not in product_columns:
            conn.execute("ALTER TABLE products ADD COLUMN max_stock INTEGER")
        asset_item_columns = {row["name"] for row in conn.execute("PRAGMA table_info(asset_items)").fetchall()}
        if "product_id" not in asset_item_columns:
            conn.execute("ALTER TABLE asset_items ADD COLUMN product_id INTEGER")
        if "quantity" not in asset_item_columns:
            conn.execute("ALTER TABLE asset_items ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assets_base_regional ON assets(base, regional)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_items_asset_id ON asset_items(asset_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_asset_items_product_id ON asset_items(product_id)")
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


def chunked_ids(values: list[int], chunk_size: int = 80) -> list[list[int]]:
    unique_values: list[int] = []
    seen: set[int] = set()
    for value in values:
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            continue
        if int_value not in seen:
            seen.add(int_value)
            unique_values.append(int_value)
    return [unique_values[index:index + chunk_size] for index in range(0, len(unique_values), chunk_size)]


def execute_delete_ids_chunked(conn: Any, table: str, column: str, ids: list[int]) -> int:
    """Apaga IDs em blocos para funcionar bem no SQLite local e no Cloudflare D1."""
    total = 0
    allowed_tables = {"supply_requests", "request_items", "stock_movements", "admin_login_codes", "user_page_permissions"}
    allowed_columns = {"id", "request_id", "product_id", "user_id", "created_by_id"}
    if table not in allowed_tables or column not in allowed_columns:
        raise ValueError("Tabela/coluna não autorizada para exclusão em bloco.")
    for chunk in chunked_ids(ids):
        placeholders = ",".join("?" for _ in chunk)
        cursor = conn.execute(f"DELETE FROM {table} WHERE {column} IN ({placeholders})", chunk)
        if isinstance(getattr(cursor, "rowcount", None), int) and cursor.rowcount > 0:
            total += int(cursor.rowcount)
    return total


def permanently_delete_supply_request(conn: Any, request_id: int) -> bool:
    """Remove uma solicitação e vínculos diretos do banco de dados."""
    row = conn.execute("SELECT id FROM supply_requests WHERE id = ?", (request_id,)).fetchone()
    if row is None:
        return False
    conn.execute("DELETE FROM stock_movements WHERE request_id = ?", (request_id,))
    conn.execute("DELETE FROM request_items WHERE request_id = ?", (request_id,))
    conn.execute("DELETE FROM supply_requests WHERE id = ?", (request_id,))
    return True


def permanently_delete_empty_supply_requests(conn: Any, request_ids: list[int]) -> int:
    """Remove solicitações que ficaram sem itens depois da exclusão de produto."""
    empty_ids: list[int] = []
    for chunk in chunked_ids(request_ids):
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"""
            SELECT sr.id
              FROM supply_requests sr
             WHERE sr.id IN ({placeholders})
               AND NOT EXISTS (SELECT 1 FROM request_items ri WHERE ri.request_id = sr.id)
            """,
            chunk,
        ).fetchall()
        empty_ids.extend(int(row["id"]) for row in rows)
    if not empty_ids:
        return 0
    execute_delete_ids_chunked(conn, "stock_movements", "request_id", empty_ids)
    return execute_delete_ids_chunked(conn, "supply_requests", "id", empty_ids)


def permanently_delete_product(conn: Any, product_id: int) -> tuple[str, int, int]:
    """Remove definitivamente um produto, seus vínculos e movimentos de estoque.

    Retorna: (nome do produto, itens de solicitação removidos, solicitações vazias removidas).
    """
    product_row = conn.execute("SELECT id, name FROM products WHERE id = ?", (product_id,)).fetchone()
    if product_row is None:
        raise LookupError("Produto não encontrado.")

    product_name = product_row["name"] or f"Produto #{product_id}"
    request_rows = conn.execute("SELECT DISTINCT request_id FROM request_items WHERE product_id = ?", (product_id,)).fetchall()
    request_ids = [int(row["request_id"]) for row in request_rows]
    item_count_row = conn.execute("SELECT COUNT(*) AS total FROM request_items WHERE product_id = ?", (product_id,)).fetchone()
    removed_items = int(item_count_row["total"] or 0) if item_count_row is not None else 0

    conn.execute("DELETE FROM stock_movements WHERE product_id = ?", (product_id,))
    conn.execute("DELETE FROM request_items WHERE product_id = ?", (product_id,))
    removed_empty_requests = permanently_delete_empty_supply_requests(conn, request_ids)
    conn.execute("UPDATE asset_items SET product_id = NULL WHERE product_id = ?", (product_id,))
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    return product_name, removed_items, removed_empty_requests


def permanently_delete_user(conn: Any, user_id: int) -> tuple[int, int]:
    """Remove definitivamente um usuário e as solicitações feitas por ele."""
    row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise LookupError("Usuário não encontrado.")

    request_rows = conn.execute("SELECT id FROM supply_requests WHERE user_id = ?", (user_id,)).fetchall()
    request_ids = [int(row["id"]) for row in request_rows]
    if request_ids:
        execute_delete_ids_chunked(conn, "stock_movements", "request_id", request_ids)
        execute_delete_ids_chunked(conn, "request_items", "request_id", request_ids)
        execute_delete_ids_chunked(conn, "supply_requests", "id", request_ids)

    conn.execute("DELETE FROM admin_login_codes WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_page_permissions WHERE user_id = ?", (user_id,))
    conn.execute("UPDATE assets SET created_by_id = NULL WHERE created_by_id = ?", (user_id,))
    conn.execute("UPDATE stock_movements SET created_by_id = NULL WHERE created_by_id = ?", (user_id,))
    conn.execute("UPDATE supply_requests SET reviewed_by_id = NULL WHERE reviewed_by_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return len(request_ids), user_id


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
        "base_franchise_options": BASE_FRANCHISE_OPTIONS,
        "base_unit_options": BASE_UNIT_OPTIONS,
        "franchise_unit_options": FRANCHISE_UNIT_OPTIONS,
        "asset_unit_options": BASE_FRANCHISE_OPTIONS,
        "admin_organization_options": ADMIN_ORGANIZATION_OPTIONS,
        "asset_regional_options": ASSET_REGIONAL_OPTIONS,
        "asset_regional_for_base": asset_regional_for_base,
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
        "asset_allocation": "SaÃ­da para ativo",
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


FEISHU_ITEM_LIMIT = 18


def compact_text(value: Any, fallback: str = "-", limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        text = fallback
    if limit > 3 and len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text[:limit]


def feishu_md(value: Any, fallback: str = "-", limit: int = 240) -> str:
    text = compact_text(value, fallback=fallback, limit=limit)
    for char in ("\\", "*", "_", "`", "[", "]", "(", ")", "#"):
        text = text.replace(char, "\\" + char)
    return text


def feishu_line(label: str, value: Any) -> str:
    return f"**{label}:** {feishu_md(value)}"


def user_role_label(role: str | None) -> str:
    labels = {"admin": "Admin", "base": "Base", "franchise": "Franquia"}
    return labels.get(role or "", role or "-")


def format_feishu_datetime(value: datetime | None = None) -> str:
    return (value or datetime.utcnow()).strftime("%d/%m/%Y %H:%M")


def public_url_for(endpoint: str, **values: Any) -> str:
    clean_values = {key: value for key, value in values.items() if value is not None}
    if not has_request_context():
        return PUBLIC_BASE_URL
    try:
        path = url_for(endpoint, **clean_values)
        if PUBLIC_BASE_URL:
            return f"{PUBLIC_BASE_URL}{path}"
        return url_for(endpoint, _external=True, **clean_values)
    except Exception:
        app.logger.exception("Falha ao montar link publico para o Feishu")
        return PUBLIC_BASE_URL


def dispatch_feishu_webhook(payload: dict[str, Any]) -> None:
    webhook_url = FEISHU_STOCK_WEBHOOK_URL
    if not webhook_url:
        return

    def send_payload() -> None:
        try:
            response = requests.post(webhook_url, json=payload, timeout=8)
            response.raise_for_status()
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = {}
            if isinstance(response_payload, dict) and response_payload.get("code") not in (0, None):
                app.logger.warning("Feishu webhook retornou erro: %s", response_payload)
        except Exception:
            app.logger.exception("Falha ao enviar notificacao para o Feishu")

    threading.Thread(target=send_payload, daemon=True).start()


def send_feishu_card(title: str, lines: list[str], link_text: str, link_url: str) -> None:
    content = "\n".join(line for line in lines if line is not None).strip()
    if len(content) > 3500:
        content = content[:3497].rstrip() + "..."

    elements: list[dict[str, Any]] = []
    if content:
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": content}})
    if link_url:
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": compact_text(link_text, limit=50)},
                        "type": "primary",
                        "url": link_url,
                    }
                ],
            }
        )

    if not elements:
        return

    dispatch_feishu_webhook(
        {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "red",
                    "title": {"tag": "plain_text", "content": compact_text(title, limit=80)},
                },
                "elements": elements,
            },
        }
    )


def request_item_feishu_lines(items: list[RequestItem]) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(items[:FEISHU_ITEM_LIMIT], start=1):
        product = item.product
        product_name = product.name if product else item.product_name_snapshot
        unit = product.unit_measure if product and product.unit_measure else "un"
        lines.extend(
            [
                f"**{index}. {feishu_md(product_name)}**",
                f"> Quantidade: **{feishu_md(item.quantity, limit=40)} {feishu_md(unit, limit=40)}**",
                "",
            ]
        )
    remaining = len(items) - FEISHU_ITEM_LIMIT
    if remaining > 0:
        lines.append(f"+{remaining} item(ns) adicionais no portal")
    return lines or ["Sem itens"]


def notify_feishu_supply_request_created(supply_request: SupplyRequest, link_url: str) -> None:
    requester = supply_request.user
    requester_name = requester.responsible_name if requester else f"Usuario #{supply_request.user_id}"
    requester_org = requester.organization_name if requester else "-"
    requester_role = user_role_label(requester.role if requester else "")

    lines = [
        feishu_line("Solicitacao", f"#{supply_request.id}"),
        feishu_line("Pedido por", requester_name),
        feishu_line("Base/Franquia", requester_org),
        feishu_line("Tipo", requester_role),
        feishu_line("Status", "Pendente"),
        feishu_line("Data", format_feishu_datetime()),
    ]
    if supply_request.user_note:
        lines.append(feishu_line("Observacao do pedido", supply_request.user_note))
    lines.extend(["", "---", "**Itens solicitados**", "", *request_item_feishu_lines(supply_request.items)])

    send_feishu_card("Nova solicitação de insumos", lines, "Abrir solicitação", link_url)


def notify_feishu_asset_created(
    asset_id: int,
    name: str,
    base: str,
    regional: str,
    sector: str,
    manager: str,
    created_by: User,
    item_rows: list[dict[str, Any]],
    product_map: dict[int, Product],
    link_url: str,
) -> None:
    item_lines: list[str] = []
    for index, item in enumerate(item_rows[:FEISHU_ITEM_LIMIT], start=1):
        product = product_map.get(int(item["product_id"]))
        product_name = product.name if product else item.get("item_name", "Item")
        unit = product.unit_measure if product and product.unit_measure else "un"
        serial_number = compact_text(item.get("serial_number"), fallback="", limit=120)
        item_lines.extend(
            [
                f"**{index}. {feishu_md(product_name)}**",
                f"> Quantidade: **{feishu_md(item.get('quantity'), limit=40)} {feishu_md(unit, limit=40)}**",
            ]
        )
        if serial_number:
            item_lines.append(f"> Patrimônio/Série: {feishu_md(serial_number, fallback='', limit=120)}")
        item_lines.append("")
    remaining = len(item_rows) - FEISHU_ITEM_LIMIT
    if remaining > 0:
        item_lines.append(f"+{remaining} item(ns) adicionais no portal")

    lines = [
        feishu_line("Ativo", f"#{asset_id} - {name}"),
        feishu_line("Regional", regional),
        feishu_line("Base", base),
        feishu_line("Setor", sector),
        feishu_line("Gestor", manager),
        feishu_line("Cadastrado por", created_by.responsible_name),
        feishu_line("Data", format_feishu_datetime()),
        "",
        "---",
        "**Itens vinculados**",
        "",
        *(item_lines or ["Sem itens"]),
    ]

    send_feishu_card("Novo ativo cadastrado", lines, "Abrir ativo", link_url)




def normalize_header(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    for char in [".", ":", ";", "-", "_", "/", "\\", "(", ")"]:
        text = text.replace(char, " ")
    return " ".join(text.split())


def parse_money_to_cents(value: Any) -> int:
    if value is None or str(value).strip() == "":
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        try:
            return int(round(float(value) * 100))
        except (TypeError, ValueError, OverflowError):
            return 0
    text_value = str(value).strip()
    for token in ["R$", "BRL", "￥", "¥"]:
        text_value = text_value.replace(token, "")
    text_value = text_value.replace(" ", "")
    text_value = re.sub(r"[^0-9,.-]", "", text_value)
    if not text_value:
        return 0
    if "," in text_value and "." in text_value:
        if text_value.rfind(",") > text_value.rfind("."):
            text_value = text_value.replace(".", "").replace(",", ".")
        else:
            text_value = text_value.replace(",", "")
    elif "," in text_value:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", text_value):
            text_value = text_value.replace(",", "")
        else:
            text_value = text_value.replace(".", "").replace(",", ".")
    elif "." in text_value:
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", text_value):
            text_value = text_value.replace(".", "")
    try:
        return max(0, int(round(float(text_value or "0") * 100)))
    except (TypeError, ValueError, OverflowError):
        return 0


def parse_bool_value(value: Any, default: bool = True) -> bool:
    if value is None or str(value).strip() == "":
        return default
    text_raw = str(value).strip().lower()
    text = normalize_header(value)
    true_values = {"1", "sim", "s", "yes", "y", "true", "ativo", "ativado", "active", "habilitado", "enabled", "enable", "是", "启用", "啟用", "正常"}
    false_values = {"0", "nao", "não", "n", "no", "false", "inativo", "desativado", "inactive", "disabled", "disable", "否", "停用", "禁用"}
    if text in true_values or text_raw in true_values:
        return True
    if text in false_values or text_raw in false_values:
        return False
    return default


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
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        try:
            number = int(round(float(value)))
            return number if number >= 0 else None
        except (TypeError, ValueError, OverflowError):
            return None
    text_value = str(value).strip()
    text_value = re.sub(r"[^0-9,.-]", "", text_value)
    if not text_value:
        return None
    if "," in text_value and "." in text_value:
        if text_value.rfind(",") > text_value.rfind("."):
            text_value = text_value.replace(".", "").replace(",", ".")
        else:
            text_value = text_value.replace(",", "")
    elif "," in text_value:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", text_value):
            text_value = text_value.replace(",", "")
        else:
            text_value = text_value.replace(",", ".")
    elif "." in text_value:
        if text_value.count(".") > 1 or re.fullmatch(r"\d{1,3}(\.\d{3})+", text_value):
            text_value = text_value.replace(".", "")
    try:
        number = int(round(float(text_value)))
    except (TypeError, ValueError, OverflowError):
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


def pdf_clean_text(value: Any, default: str = "-") -> str:
    """Texto seguro para Paragraph do ReportLab.

    Alguns nomes antigos de base/franquia chegaram ao PDF com ponto e vírgula
    no lugar de espaços. Aqui normalizamos só para exibição, mantendo o valor
    salvo no banco intacto.
    """
    text_value = str(value if value is not None else "").strip()
    if not text_value:
        text_value = default
    text_value = text_value.replace(";", " ")
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return html_escape(text_value or default)


def pdf_clean_plain_text(value: Any, default: str = "-") -> str:
    """Texto limpo para canvas.drawString, sem escapar HTML."""
    text_value = str(value if value is not None else "").strip()
    if not text_value:
        text_value = default
    text_value = text_value.replace(";", " ")
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value or default


def people_count_label(value: int | None) -> str:
    if value is None or int(value or 0) <= 0:
        return "-"
    number = int(value)
    return f"{number} pessoa" if number == 1 else f"{number} pessoas"


def build_request_pdf(supply_request: SupplyRequest, viewer: User) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=17 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="JTTitle", fontName=PDF_TEXT_FONT_BOLD, fontSize=18, leading=22, textColor=colors.HexColor("#151515"), spaceAfter=3))
    styles.add(ParagraphStyle(name="JTSubtitle", fontName=PDF_TEXT_FONT, fontSize=8.8, leading=12, textColor=colors.HexColor("#666666")))
    styles.add(ParagraphStyle(name="JTSection", fontName=PDF_TEXT_FONT_BOLD, fontSize=11.5, leading=14, textColor=colors.HexColor("#151515"), spaceBefore=4, spaceAfter=6))
    styles.add(ParagraphStyle(name="JTMeta", fontName=PDF_TEXT_FONT, fontSize=8.7, leading=11, textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="JTMetaLabel", fontName=PDF_TEXT_FONT_BOLD, fontSize=7.4, leading=9, textColor=colors.HexColor("#e60012")))
    styles.add(ParagraphStyle(name="JTCell", fontName=PDF_TEXT_FONT, fontSize=8.4, leading=10.8, textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="JTCellBold", fontName=PDF_TEXT_FONT_BOLD, fontSize=8.4, leading=10.8, textColor=colors.HexColor("#111111")))
    styles.add(ParagraphStyle(name="JTSmall", fontName=PDF_TEXT_FONT, fontSize=7.8, leading=10.3, textColor=colors.HexColor("#666666")))

    story: list[Any] = []

    logo_path = BASE_DIR / "static" / "img" / "logo-jt-red.svg"
    logo_cell: Any
    try:
        drawing = svg2rlg(str(logo_path))
        if drawing is not None and drawing.width:
            scale = (38 * mm) / drawing.width
            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)
            logo_cell = drawing
        else:
            raise ValueError("Logo SVG inválida")
    except Exception:
        logo_cell = Paragraph("J&amp;T EXPRESS", ParagraphStyle(name="FallbackLogoPDF", fontName=PDF_TEXT_FONT_BOLD, fontSize=14, textColor=colors.HexColor("#e60012")))

    requester = supply_request.user
    requester_name = requester.responsible_name if requester else "-"
    requester_org = requester.organization_name if requester else "-"
    requester_username = requester.username if requester else "-"
    requester_role = requester.role if requester else "base"
    show_prices = viewer.is_admin or viewer.role == "franchise"
    role_label = "Administrador" if requester_role == "admin" else ("Base" if requester_role == "base" else "Franquia")

    header_table = Table(
        [[
            logo_cell,
            Paragraph(f"Solicitação de Insumos #{supply_request.id}", styles["JTTitle"]),
            Paragraph(f"<b>Status</b><br/>{pdf_clean_text(status_label(supply_request.status))}<br/><font color='#777777'>Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</font>", styles["JTMeta"]),
        ]],
        colWidths=[43 * mm, 78 * mm, 53 * mm],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7f8")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#f0d6d9")),
        ("LINEBELOW", (0, 0), (-1, -1), 2.0, colors.HexColor("#e60012")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Documento gerado automaticamente pelo Portal de Solicitação de Insumos J&amp;T Express Brazil.", styles["JTSubtitle"]))
    story.append(Spacer(1, 7 * mm))

    meta_data = [
        [Paragraph("SOLICITANTE", styles["JTMetaLabel"]), Paragraph("BASE / FRANQUIA", styles["JTMetaLabel"]), Paragraph("TIPO", styles["JTMetaLabel"])],
        [Paragraph(pdf_clean_text(requester_name), styles["JTMeta"]), Paragraph(pdf_clean_text(requester_org), styles["JTMeta"]), Paragraph(pdf_clean_text(role_label), styles["JTMeta"])],
        [Paragraph("USUÁRIO", styles["JTMetaLabel"]), Paragraph("PESSOAS NA BASE", styles["JTMetaLabel"]), Paragraph("DATA DA SOLICITAÇÃO", styles["JTMetaLabel"])],
        [Paragraph(pdf_clean_text(requester_username), styles["JTMeta"]), Paragraph(pdf_clean_text(people_count_label(supply_request.people_count)), styles["JTMeta"]), Paragraph(supply_request.created_at.strftime("%d/%m/%Y %H:%M"), styles["JTMeta"])],
    ]
    meta_table = Table(meta_data, colWidths=[58 * mm, 58 * mm, 58 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fcfcfc")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff3f4")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fff3f4")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#eeeeee")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))

    headers = [Paragraph("Produto solicitado", styles["JTCellBold"]), Paragraph("Qtd.", styles["JTCellBold"])]
    col_widths = [126 * mm, 28 * mm]
    if show_prices:
        headers.extend([Paragraph("Valor unit.", styles["JTCellBold"]), Paragraph("Subtotal", styles["JTCellBold"])])
        col_widths = [86 * mm, 23 * mm, 30 * mm, 35 * mm]

    item_rows: list[list[Any]] = [headers]
    for item in supply_request.items:
        unit_label = item.product.unit_measure if item.product and item.product.unit_measure else "un"
        row: list[Any] = [
            Paragraph(pdf_clean_text(item.product_name_snapshot), styles["JTCell"]),
            Paragraph(pdf_clean_text(f"{item.quantity} {unit_label}"), styles["JTCellBold"]),
        ]
        if show_prices:
            row.extend([
                Paragraph(format_brl(item.price_cents_snapshot), styles["JTCell"]),
                Paragraph(format_brl(item.price_cents_snapshot * item.quantity), styles["JTCellBold"]),
            ])
        item_rows.append(row)

    if show_prices:
        item_rows.append(["", "", Paragraph("TOTAL", styles["JTCellBold"]), Paragraph(format_brl(supply_request.total_cents), styles["JTCellBold"])])

    story.append(Paragraph("Itens solicitados", styles["JTSection"]))
    items_table = Table(item_rows, colWidths=col_widths, repeatRows=1)
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e60012")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dddddd")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#e8e8e8")),
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
    story.append(items_table)
    story.append(Spacer(1, 8 * mm))

    info_blocks: list[list[Any]] = []
    if supply_request.user_note:
        info_blocks.append([Paragraph("Observação do solicitante", styles["JTCellBold"]), Paragraph(pdf_clean_text(supply_request.user_note), styles["JTSmall"])])
    if supply_request.admin_note:
        info_blocks.append([Paragraph("Observação administrativa", styles["JTCellBold"]), Paragraph(pdf_clean_text(supply_request.admin_note), styles["JTSmall"])])
    if supply_request.reviewed_at:
        info_blocks.append([Paragraph("Revisão", styles["JTCellBold"]), Paragraph(f"Revisado em {supply_request.reviewed_at.strftime('%d/%m/%Y %H:%M')}", styles["JTSmall"])])
    if info_blocks:
        story.append(Paragraph("Informações complementares", styles["JTSection"]))
        info_table = Table(info_blocks, colWidths=[52 * mm, 122 * mm])
        info_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
            ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#eeeeee")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fff8f8")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(info_table)

    def footer(canvas, document):
        canvas.saveState()
        width, _height = A4
        canvas.setStrokeColor(colors.HexColor("#e60012"))
        canvas.setLineWidth(0.7)
        canvas.line(16 * mm, 14 * mm, width - 16 * mm, 14 * mm)
        canvas.setFont(PDF_TEXT_FONT, 7.5)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(16 * mm, 9 * mm, "J&T Express Brazil • CNPJ: 42.584.754/0092-13")
        canvas.drawRightString(width - 16 * mm, 9 * mm, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer



def parse_report_date(value: str, field_label: str) -> datetime:
    """Converte data yyyy-mm-dd do formulário em datetime.

    Mantemos a filtragem por texto/UTC do banco, mas o usuário escolhe datas
    simples no formulário. O intervalo final é tratado como inclusivo na rota.
    """
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field_label} inválida. Use uma data válida.") from exc


def list_supply_requests_between(start_dt: datetime, end_dt: datetime, organization_name: str = "") -> list[SupplyRequest]:
    start_sql = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_sql = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    params: list[Any] = [start_sql, end_sql]
    unit_filter = (organization_name or "").strip()
    unit_clause = ""
    if unit_filter:
        unit_clause = " AND u.organization_name = ?"
        params.append(unit_filter)
    with db_connect() as conn:
        rows = conn.execute(
            f"""
            SELECT sr.*
              FROM supply_requests sr
              LEFT JOIN users u ON u.id = sr.user_id
             WHERE sr.created_at >= ?
               AND sr.created_at <= ?
               {unit_clause}
             ORDER BY sr.created_at ASC, sr.id ASC
            """,
            params,
        ).fetchall()
    return [req for row in rows if (req := row_to_supply_request(row)) is not None]


def list_assets_between(start_dt: datetime, end_dt: datetime, unit_name: str = "") -> list[AssetRecord]:
    start_sql = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_sql = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    unit_filter = (unit_name or "").strip()
    unit_clause = ""
    params: list[Any] = [start_sql, end_sql]
    if unit_filter:
        unit_clause = " AND base = ?"
        params.append(unit_filter)
    with db_connect() as conn:
        rows = conn.execute(
            f"""
            SELECT *
              FROM assets
             WHERE created_at >= ?
               AND created_at <= ?
               {unit_clause}
             ORDER BY created_at ASC, id ASC
            """,
            params,
        ).fetchall()
        return [asset for row in rows if (asset := row_to_asset(row, conn=conn)) is not None]


def build_supply_requests_period_report_pdf(
    requests_list: list[SupplyRequest],
    start_dt: datetime,
    end_dt: datetime,
    viewer: User,
    unit_name: str = "",
    unit_kind: str = "",
) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", fontName=PDF_TEXT_FONT_BOLD, fontSize=18.5, leading=22.5, textColor=colors.HexColor("#151515"), spaceAfter=3))
    styles.add(ParagraphStyle(name="ReportSubtitle", fontName=PDF_TEXT_FONT, fontSize=9.0, leading=12.2, textColor=colors.HexColor("#666666")))
    styles.add(ParagraphStyle(name="ReportSection", fontName=PDF_TEXT_FONT_BOLD, fontSize=12.0, leading=15, textColor=colors.HexColor("#151515"), spaceBefore=6, spaceAfter=7))
    styles.add(ParagraphStyle(name="ReportLabel", fontName=PDF_TEXT_FONT_BOLD, fontSize=7.2, leading=9, textColor=colors.HexColor("#e60012")))
    styles.add(ParagraphStyle(name="ReportMeta", fontName=PDF_TEXT_FONT, fontSize=8.0, leading=10.2, textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="ReportCell", fontName=PDF_TEXT_FONT, fontSize=7.4, leading=9.5, textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="ReportCellBold", fontName=PDF_TEXT_FONT_BOLD, fontSize=7.4, leading=9.5, textColor=colors.HexColor("#111111")))
    styles.add(ParagraphStyle(name="ReportSmall", fontName=PDF_TEXT_FONT, fontSize=6.8, leading=8.6, textColor=colors.HexColor("#666666")))

    def p(value: Any, style_name: str = "ReportCell") -> Paragraph:
        return Paragraph(pdf_clean_text(value), styles[style_name])

    def status_name(status: str) -> str:
        return status_label(status)

    logo_path = BASE_DIR / "static" / "img" / "logo-jt-red.svg"
    try:
        drawing = svg2rlg(str(logo_path))
        if drawing is not None and drawing.width:
            scale = (34 * mm) / drawing.width
            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)
            logo_cell: Any = drawing
        else:
            raise ValueError("Logo SVG inválida")
    except Exception:
        logo_cell = Paragraph("J&amp;T EXPRESS", ParagraphStyle(name="ReportFallbackLogo", fontName=PDF_TEXT_FONT_BOLD, fontSize=13, textColor=colors.HexColor("#e60012")))

    period_label = f"{start_dt.strftime('%d/%m/%Y')} a {end_dt.strftime('%d/%m/%Y')}"
    unit_label = f"{unit_kind_label(unit_kind)}: {unit_name}" if unit_name else "Todas as unidades"
    generated_label = datetime.now().strftime("%d/%m/%Y %H:%M")
    story: list[Any] = []
    header = Table(
        [[
            logo_cell,
            Paragraph("Relatório de Solicitações de Insumos", styles["ReportTitle"]),
            Paragraph(f"<b>Período</b><br/>{pdf_clean_text(period_label)}<br/><b>Unidade</b><br/>{pdf_clean_text(unit_label)}<br/><font color='#777777'>Gerado em {generated_label}</font>", styles["ReportMeta"]),
        ]],
        colWidths=[36 * mm, 92 * mm, 50 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
        ("LINEBELOW", (0, 0), (-1, -1), 2.0, colors.HexColor("#e60012")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph(f"Relatório consolidado das solicitações registradas no intervalo selecionado para {pdf_clean_text(unit_label)}, incluindo solicitante, status, número de pessoas, itens, quantidades, valores e observações.", styles["ReportSubtitle"]))
    story.append(Spacer(1, 6 * mm))

    status_counts: dict[str, int] = {}
    total_items = 0
    total_units = 0
    total_people = 0
    total_value = 0
    requester_units: set[str] = set()
    product_totals: dict[str, dict[str, Any]] = {}
    for req in requests_list:
        status_counts[req.status] = status_counts.get(req.status, 0) + 1
        total_people += int(req.people_count or 0)
        if req.user and req.user.organization_name:
            requester_units.add(pdf_clean_plain_text(req.user.organization_name))
        for item in req.items:
            total_items += 1
            total_units += int(item.quantity or 0)
            total_value += int(item.price_cents_snapshot or 0) * int(item.quantity or 0)
            product_key = item.product_name_snapshot or f"Produto #{item.product_id}"
            bucket = product_totals.setdefault(product_key, {"name": product_key, "quantity": 0, "value": 0, "unit": "un"})
            bucket["quantity"] += int(item.quantity or 0)
            bucket["value"] += int(item.price_cents_snapshot or 0) * int(item.quantity or 0)
            if item.product and item.product.unit_measure:
                bucket["unit"] = item.product.unit_measure

    summary_data = [
        [Paragraph("SOLICITAÇÕES", styles["ReportLabel"]), Paragraph("BASES/FRANQUIAS", styles["ReportLabel"]), Paragraph("ITENS", styles["ReportLabel"]), Paragraph("VALOR TOTAL", styles["ReportLabel"])],
        [p(len(requests_list), "ReportMeta"), p(len(requester_units), "ReportMeta"), p(f"{total_items} linhas / {total_units} un.", "ReportMeta"), p(format_brl(total_value), "ReportMeta")],
        [Paragraph("PENDENTES", styles["ReportLabel"]), Paragraph("APROVADAS", styles["ReportLabel"]), Paragraph("REJEITADAS", styles["ReportLabel"]), Paragraph("PESSOAS INFORMADAS", styles["ReportLabel"])],
        [p(status_counts.get("pending", 0), "ReportMeta"), p(status_counts.get("approved", 0), "ReportMeta"), p(status_counts.get("rejected", 0), "ReportMeta"), p(total_people if total_people else "-", "ReportMeta")],
    ]
    summary_table = Table(summary_data, colWidths=[44.5 * mm, 44.5 * mm, 44.5 * mm, 44.5 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff3f4")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fff3f4")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#eeeeee")),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 6 * mm))

    if product_totals:
        top_products = sorted(product_totals.values(), key=lambda row: row["quantity"], reverse=True)[:12]
        story.append(Paragraph("Resumo por produto", styles["ReportSection"]))
        product_rows = [[p("Produto", "ReportCellBold"), p("Quantidade", "ReportCellBold"), p("Valor", "ReportCellBold")]]
        for product in top_products:
            product_rows.append([
                p(product["name"]),
                p(f"{product['quantity']} {product.get('unit') or 'un'}", "ReportCellBold"),
                p(format_brl(product["value"]), "ReportCellBold"),
            ])
        product_table = Table(product_rows, colWidths=[108 * mm, 34 * mm, 36 * mm], repeatRows=1)
        product_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e60012")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff8f8")]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dddddd")),
            ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#eeeeee")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(product_table)
        story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Solicitações do período", styles["ReportSection"]))
    if not requests_list:
        empty = Table([[Paragraph("Nenhuma solicitação encontrada para o período selecionado.", styles["ReportMeta"])]], colWidths=[178 * mm])
        empty.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff8f8")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(empty)
    else:
        for req in requests_list:
            requester = req.user
            requester_name = requester.responsible_name if requester else "-"
            requester_org = requester.organization_name if requester else "-"
            requester_username = requester.username if requester else "-"
            requester_role = user_role_label(requester.role if requester else "")
            item_text_parts = []
            for item in req.items:
                unit = item.product.unit_measure if item.product and item.product.unit_measure else "un"
                subtotal = int(item.price_cents_snapshot or 0) * int(item.quantity or 0)
                item_text_parts.append(f"{item.quantity} {unit} - {item.product_name_snapshot} ({format_brl(subtotal)})")
            if not item_text_parts:
                item_text_parts.append("Sem itens")
            notes_html = "-"
            if req.user_note and req.admin_note:
                notes_html = f"Solicitante: {pdf_clean_text(req.user_note)}<br/>Admin: {pdf_clean_text(req.admin_note)}"
            elif req.user_note:
                notes_html = pdf_clean_text(req.user_note)
            elif req.admin_note:
                notes_html = pdf_clean_text(req.admin_note)

            detail_rows = [
                [Paragraph(f"Solicitação #{req.id}", styles["ReportCellBold"]), Paragraph(pdf_clean_text(status_name(req.status)), styles["ReportCellBold"]), Paragraph(req.created_at.strftime("%d/%m/%Y %H:%M"), styles["ReportCellBold"])],
                [Paragraph("Solicitante", styles["ReportLabel"]), Paragraph("Base/Franquia", styles["ReportLabel"]), Paragraph("Tipo / Pessoas", styles["ReportLabel"])],
                [p(f"{requester_name} ({requester_username})"), p(requester_org), p(f"{requester_role} • {people_count_label(req.people_count)}")],
                [Paragraph("Itens", styles["ReportLabel"]), Paragraph("Observações", styles["ReportLabel"]), Paragraph("Total", styles["ReportLabel"])],
                [Paragraph("<br/>".join(pdf_clean_text(part) for part in item_text_parts), styles["ReportSmall"]), Paragraph(notes_html, styles["ReportSmall"]), p(format_brl(req.total_cents), "ReportCellBold")],
            ]
            if req.reviewed_at:
                detail_rows.append([Paragraph("Revisão", styles["ReportLabel"]), Paragraph(req.reviewed_at.strftime("%d/%m/%Y %H:%M"), styles["ReportSmall"]), Paragraph("", styles["ReportSmall"])])
            detail = Table(detail_rows, colWidths=[68 * mm, 66 * mm, 44 * mm], repeatRows=0)
            detail.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff3f4")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fffafa")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#fffafa")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e6d6d8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#eeeeee")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(detail)
            story.append(Spacer(1, 3.5 * mm))

    def footer(canvas, document):
        canvas.saveState()
        width, _height = A4
        canvas.setStrokeColor(colors.HexColor("#e60012"))
        canvas.setLineWidth(0.7)
        canvas.line(16 * mm, 13 * mm, width - 16 * mm, 13 * mm)
        canvas.setFont(PDF_TEXT_FONT, 7.2)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(16 * mm, 8.5 * mm, "J&T Express Brazil • Relatório mensal de solicitações")
        canvas.drawRightString(width - 16 * mm, 8.5 * mm, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer

def build_assets_period_report_pdf(
    assets: list[AssetRecord],
    start_dt: datetime,
    end_dt: datetime,
    viewer: User,
    unit_name: str,
    unit_kind: str,
) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="AssetReportTitle", fontName=PDF_TEXT_FONT_BOLD, fontSize=18.5, leading=22, textColor=colors.HexColor("#141414"), spaceAfter=2))
    styles.add(ParagraphStyle(name="AssetReportSubtitle", fontName=PDF_TEXT_FONT, fontSize=8.8, leading=12, textColor=colors.HexColor("#666666")))
    styles.add(ParagraphStyle(name="AssetReportLabel", fontName=PDF_TEXT_FONT_BOLD, fontSize=7.2, leading=9, textColor=colors.HexColor("#e60012")))
    styles.add(ParagraphStyle(name="AssetReportCell", fontName=PDF_TEXT_FONT, fontSize=7.5, leading=9.8, textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="AssetReportCellBold", fontName=PDF_TEXT_FONT_BOLD, fontSize=7.6, leading=9.8, textColor=colors.HexColor("#111111")))
    styles.add(ParagraphStyle(name="AssetReportSection", fontName=PDF_TEXT_FONT_BOLD, fontSize=12.0, leading=15, textColor=colors.HexColor("#111111"), spaceBefore=7, spaceAfter=7))
    styles.add(ParagraphStyle(name="AssetReportSmall", fontName=PDF_TEXT_FONT, fontSize=6.8, leading=8.8, textColor=colors.HexColor("#666666")))

    def p(value: Any, style_name: str = "AssetReportCell") -> Paragraph:
        return Paragraph(pdf_clean_text(value), styles[style_name])

    logo_path = BASE_DIR / "static" / "img" / "logo-jt-red.svg"
    try:
        drawing = svg2rlg(str(logo_path))
        if drawing is not None and drawing.width:
            scale = (34 * mm) / drawing.width
            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)
            logo_cell: Any = drawing
        else:
            raise ValueError("Logo SVG inválida")
    except Exception:
        logo_cell = Paragraph("J&amp;T EXPRESS", ParagraphStyle(name="AssetReportFallbackLogo", fontName=PDF_TEXT_FONT_BOLD, fontSize=13, textColor=colors.HexColor("#e60012")))

    period_label = f"{start_dt.strftime('%d/%m/%Y')} a {end_dt.strftime('%d/%m/%Y')}"
    unit_label = f"{unit_kind_label(unit_kind)}: {unit_name}" if unit_name else "Todas as unidades"
    generated_label = datetime.now().strftime("%d/%m/%Y %H:%M")
    total_assets = len(assets)
    total_item_lines = sum(len(asset.items) for asset in assets)
    total_quantity = sum(sum(max(0, int(item.quantity or 0)) for item in asset.items) for asset in assets)
    sectors = len({asset.sector for asset in assets if asset.sector})
    managers = len({asset.manager for asset in assets if asset.manager})

    story: list[Any] = []
    header = Table(
        [[
            logo_cell,
            Paragraph("Relatório de Ativos", styles["AssetReportTitle"]),
            Paragraph(f"<b>Período</b><br/>{pdf_clean_text(period_label)}<br/><b>Unidade</b><br/>{pdf_clean_text(unit_label)}<br/><font color='#777777'>Gerado em {generated_label}</font>", styles["AssetReportCell"]),
        ]],
        colWidths=[36 * mm, 90 * mm, 52 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
        ("LINEBELOW", (0, 0), (-1, -1), 2.0, colors.HexColor("#e60012")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Relatório consolidado dos ativos cadastrados no período selecionado, com dados da unidade, setor, gestor e itens vinculados.", styles["AssetReportSubtitle"]))
    story.append(Spacer(1, 6 * mm))

    summary = Table([
        [p("ATIVOS", "AssetReportLabel"), p("LINHAS DE ITENS", "AssetReportLabel"), p("QUANTIDADE TOTAL", "AssetReportLabel"), p("SETORES", "AssetReportLabel"), p("GESTORES", "AssetReportLabel")],
        [p(total_assets, "AssetReportCellBold"), p(total_item_lines, "AssetReportCellBold"), p(total_quantity, "AssetReportCellBold"), p(sectors, "AssetReportCellBold"), p(managers, "AssetReportCellBold")],
    ], colWidths=[35.6 * mm] * 5)
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff3f4")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#eeeeee")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(summary)
    story.append(Spacer(1, 7 * mm))

    story.append(Paragraph("Ativos do período", styles["AssetReportSection"]))
    if not assets:
        empty = Table([[Paragraph("Nenhum ativo encontrado para o período e unidade selecionados.", styles["AssetReportCell"])]], colWidths=[178 * mm])
        empty.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#eeeeee")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff8f8")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(empty)
    else:
        for asset in assets:
            item_parts = []
            for item in asset.items:
                product = get_product(item.product_id) if item.product_id else None
                unit = product.unit_measure if product and product.unit_measure else "un"
                serial = item.serial_number or "Sem patrimônio/série"
                item_parts.append(f"{item.quantity} {unit} - {item.item_name} • {serial}")
            if not item_parts:
                item_parts.append("Sem itens")
            detail_rows = [
                [p(f"Ativo #{asset.id}", "AssetReportCellBold"), p(asset.name, "AssetReportCellBold"), p(asset.created_at.strftime("%d/%m/%Y %H:%M"), "AssetReportCellBold")],
                [p("Base/Franquia", "AssetReportLabel"), p("Setor", "AssetReportLabel"), p("Gestor", "AssetReportLabel")],
                [p(asset.base), p(asset.sector), p(asset.manager)],
                [p("Itens vinculados", "AssetReportLabel"), p("Regional", "AssetReportLabel"), p("Total do ativo", "AssetReportLabel")],
                [Paragraph("<br/>".join(pdf_clean_text(part) for part in item_parts), styles["AssetReportSmall"]), p(asset.regional), p(str(sum(max(0, int(item.quantity or 0)) for item in asset.items)), "AssetReportCellBold")],
            ]
            detail = Table(detail_rows, colWidths=[82 * mm, 54 * mm, 42 * mm])
            detail.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff3f4")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fffafa")),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#fffafa")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e6d6d8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#eeeeee")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(detail)
            story.append(Spacer(1, 3.5 * mm))

    def footer(canvas, document):
        canvas.saveState()
        width, _height = A4
        canvas.setStrokeColor(colors.HexColor("#e60012"))
        canvas.setLineWidth(0.7)
        canvas.line(16 * mm, 13 * mm, width - 16 * mm, 13 * mm)
        canvas.setFont(PDF_TEXT_FONT, 7.2)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(16 * mm, 8.5 * mm, "J&T Express Brazil • Relatório mensal de ativos")
        canvas.drawRightString(width - 16 * mm, 8.5 * mm, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer


def build_asset_pdf(asset: AssetRecord, viewer: User) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="AssetTitle", fontName=PDF_TEXT_FONT_BOLD, fontSize=20, leading=24, textColor=colors.HexColor("#111111"), spaceAfter=2))
    styles.add(ParagraphStyle(name="AssetSubtitle", fontName=PDF_TEXT_FONT, fontSize=8.7, leading=11.5, textColor=colors.HexColor("#666666")))
    styles.add(ParagraphStyle(name="AssetLabel", fontName=PDF_TEXT_FONT_BOLD, fontSize=7.2, leading=8.6, textColor=colors.HexColor("#e60012"), uppercase=True))
    styles.add(ParagraphStyle(name="AssetValue", fontName=PDF_TEXT_FONT_BOLD, fontSize=9.4, leading=12, textColor=colors.HexColor("#141414")))
    styles.add(ParagraphStyle(name="AssetCell", fontName=PDF_TEXT_FONT, fontSize=8.6, leading=11.2, textColor=colors.HexColor("#252525")))
    styles.add(ParagraphStyle(name="AssetCellBold", fontName=PDF_TEXT_FONT_BOLD, fontSize=8.6, leading=11.2, textColor=colors.HexColor("#111111")))
    styles.add(ParagraphStyle(name="AssetSmall", fontName=PDF_TEXT_FONT, fontSize=7.5, leading=9.6, textColor=colors.HexColor("#777777")))
    styles.add(ParagraphStyle(name="AssetSection", fontName=PDF_TEXT_FONT_BOLD, fontSize=12, leading=14.5, textColor=colors.HexColor("#111111"), spaceBefore=2, spaceAfter=6))

    story: list[Any] = []

    logo_path = BASE_DIR / "static" / "img" / "logo-jt-red.svg"
    try:
        drawing = svg2rlg(str(logo_path))
        if drawing is None or not drawing.width:
            raise ValueError("Logo SVG invalida")
        scale = (38 * mm) / drawing.width
        drawing.width *= scale
        drawing.height *= scale
        drawing.scale(scale, scale)
        logo_cell: Any = drawing
    except Exception:
        logo_cell = Paragraph("J&amp;T EXPRESS", ParagraphStyle(name="AssetFallbackLogo", fontName=PDF_TEXT_FONT_BOLD, fontSize=15, textColor=colors.HexColor("#e60012")))

    total_quantity = sum(max(0, int(item.quantity or 0)) for item in asset.items)
    total_lines = len(asset.items)
    created_by = get_user(asset.created_by_id) if asset.created_by_id else None
    created_by_name = created_by.responsible_name if created_by else "Portal de Insumos"
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    header = Table(
        [[
            logo_cell,
            Paragraph(f"Ficha de Ativo #{asset.id}", styles["AssetTitle"]),
            Paragraph(f"<b>Gerado em</b><br/>{generated_at}<br/><font color='#777777'>Portal de Insumos J&amp;T Express</font>", styles["AssetCell"]),
        ]],
        colWidths=[43 * mm, 82 * mm, 55 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#eeeeee")),
        ("LINEBELOW", (0, 0), (-1, -1), 2.2, colors.HexColor("#e60012")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(header)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Documento patrimonial gerado automaticamente para controle interno de ativos vinculados a bases e franquias.", styles["AssetSubtitle"]))
    story.append(Spacer(1, 7 * mm))

    def label_cell(text: str) -> Paragraph:
        return Paragraph(pdf_clean_text(text), styles["AssetLabel"])

    def value_cell(value: Any) -> Paragraph:
        return Paragraph(pdf_clean_text(value), styles["AssetValue"])

    info_data = [
        [label_cell("ATIVO"), label_cell("BASE / FRANQUIA"), label_cell("REGIONAL")],
        [value_cell(asset.name), value_cell(asset.base), value_cell(asset.regional)],
        [label_cell("SETOR"), label_cell("GESTOR RESPONSAVEL"), label_cell("CADASTRADO POR")],
        [value_cell(asset.sector), value_cell(asset.manager), value_cell(created_by_name)],
        [label_cell("DATA DO CADASTRO"), label_cell("TOTAL DE ITENS"), label_cell("LINHAS DE ITENS")],
        [value_cell(asset.created_at.strftime("%d/%m/%Y %H:%M")), value_cell(str(total_quantity)), value_cell(str(total_lines))],
    ]
    info_table = Table(info_data, colWidths=[60 * mm, 60 * mm, 60 * mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fcfcfc")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff1f2")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fff1f2")),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#fff1f2")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e6e6e6")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#e9e9e9")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6.2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Itens vinculados ao ativo", styles["AssetSection"]))
    item_rows: list[list[Any]] = [[
        Paragraph("#", styles["AssetCellBold"]),
        Paragraph("Item", styles["AssetCellBold"]),
        Paragraph("Quantidade", styles["AssetCellBold"]),
        Paragraph("Patrimonio / Serie", styles["AssetCellBold"]),
    ]]
    for index, item in enumerate(asset.items, start=1):
        product = get_product(item.product_id) if item.product_id else None
        unit = product.unit_measure if product and product.unit_measure else "un"
        quantity_text = f"{item.quantity} {unit}"
        item_rows.append([
            Paragraph(str(index), styles["AssetCellBold"]),
            Paragraph(pdf_clean_text(item.item_name), styles["AssetCell"]),
            Paragraph(pdf_clean_text(quantity_text), styles["AssetCellBold"]),
            Paragraph(pdf_clean_text(item.serial_number or "Sem patrimonio/serie"), styles["AssetCell"]),
        ])
    if len(item_rows) == 1:
        item_rows.append(["", Paragraph("Nenhum item cadastrado.", styles["AssetCell"]), "", ""])

    items_table = Table(item_rows, colWidths=[13 * mm, 87 * mm, 29 * mm, 51 * mm], repeatRows=1)
    item_styles = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e60012")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dddddd")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#e8e8e8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
    ]
    for row_index in range(1, len(item_rows), 2):
        item_styles.append(("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#fbfbfb")))
    items_table.setStyle(TableStyle(item_styles))
    story.append(items_table)
    story.append(Spacer(1, 10 * mm))

    signature_table = Table(
        [[
            Paragraph("Responsavel pela unidade", styles["AssetSmall"]),
            Paragraph("Conferencia administrativa", styles["AssetSmall"]),
        ], [
            Paragraph("__________________________________________", styles["AssetCell"]),
            Paragraph("__________________________________________", styles["AssetCell"]),
        ]],
        colWidths=[87 * mm, 87 * mm],
    )
    signature_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(signature_table)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#e60012"))
        canvas.setLineWidth(0.6)
        canvas.line(15 * mm, 13 * mm, A4[0] - 15 * mm, 13 * mm)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.setFont(PDF_TEXT_FONT, 7.5)
        canvas.drawString(15 * mm, 8.7 * mm, f"Ativo #{asset.id} - {pdf_clean_plain_text(asset.base)}")
        canvas.drawRightString(A4[0] - 15 * mm, 8.7 * mm, f"Pagina {document.page}")
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


PRODUCT_IMPORT_HEADER_ALIASES = {
    "id": ["ID", "Código", "Codigo", "Cod", "编号", "編號"],
    "name": ["Nome do produto", "Nome", "Produto", "Insumo", "Item", "Descrição do item", "Descricao do item", "产品名称", "產品名稱", "商品名称", "产品", "品名"],
    "category": ["Categoria", "Categoria do produto", "Grupo", "Tipo", "类别", "類別", "分类", "分類"],
    "unit_measure": ["Unidade de medida", "Unidade", "Unid.", "Unid", "UM", "U.M.", "Medida", "计量单位", "計量單位", "单位", "單位"],
    "description": ["Descrição", "Descricao", "Descrição do produto", "Descricao do produto", "Observação", "Observacao", "Detalhes", "描述", "说明", "說明", "备注", "備註"],
    "stock_quantity": ["Estoque disponível", "Estoque disponivel", "Estoque", "Quantidade", "Qtd", "Qtde", "Saldo", "可用库存", "可用庫存", "库存", "庫存", "数量", "數量"],
    "price_cents": ["Valor unitário", "Valor unitario", "Valor", "Preço", "Preco", "Preço unitário", "Preco unitario", "Custo", "单价", "單價", "价格", "價格"],
    "limit_base": ["Limite para bases", "Limite base", "Base", "基地限制", "网点限制"],
    "limit_franchise": ["Limite para franquias", "Limite franquia", "Franquia", "加盟店限制", "加盟限制"],
    "min_stock": ["Estoque mínimo", "Estoque minimo", "Mínimo", "Minimo", "Min stock", "Min", "最低库存", "最低庫存"],
    "max_stock": ["Estoque máximo", "Estoque maximo", "Máximo", "Maximo", "Max stock", "Max", "最高库存", "最高庫存"],
    "active": ["Ativo", "Status", "Produto ativo", "启用", "啟用", "状态", "狀態"],
}


def normalize_product_lookup_key(value: Any) -> str:
    text_value = str(value or "").strip().casefold()
    text_value = "".join(ch for ch in unicodedata.normalize("NFD", text_value) if unicodedata.category(ch) != "Mn")
    return " ".join(text_value.split())


def clean_import_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text_value = str(value).strip()
    if text_value.lower() in {"none", "nan", "null"}:
        return default
    return text_value


def get_import_value(row_values: list[Any], header_map: dict[str, int], field_key: str) -> Any:
    return get_header_value(row_values, header_map, PRODUCT_IMPORT_HEADER_ALIASES.get(field_key, []))


def excel_row_is_empty(row_values: list[Any]) -> bool:
    return not any(value is not None and str(value).strip() for value in row_values)


@dataclass
class ProductImportRecord:
    source_row: int
    product_id: int | None
    name: str
    category: str
    unit_measure: str
    description: str
    stock_quantity: int
    price_cents: int
    limit_base: int | None
    limit_franchise: int | None
    min_stock: int | None
    max_stock: int | None
    active: bool


def parse_product_import_record(row_number: int, row_values: list[Any], header_map: dict[str, int]) -> ProductImportRecord | None:
    name = clean_import_text(get_import_value(row_values, header_map, "name"))
    if not name:
        return None
    return ProductImportRecord(
        source_row=row_number,
        product_id=parse_optional_int(get_import_value(row_values, header_map, "id")),
        name=name,
        category=clean_import_text(get_import_value(row_values, header_map, "category")),
        unit_measure=clean_import_text(get_import_value(row_values, header_map, "unit_measure"), "un") or "un",
        description=clean_import_text(get_import_value(row_values, header_map, "description")),
        stock_quantity=parse_optional_int(get_import_value(row_values, header_map, "stock_quantity")) or 0,
        price_cents=parse_money_to_cents(get_import_value(row_values, header_map, "price_cents")),
        limit_base=parse_optional_int(get_import_value(row_values, header_map, "limit_base")),
        limit_franchise=parse_optional_int(get_import_value(row_values, header_map, "limit_franchise")),
        min_stock=parse_optional_int(get_import_value(row_values, header_map, "min_stock")),
        max_stock=parse_optional_int(get_import_value(row_values, header_map, "max_stock")),
        active=parse_bool_value(get_import_value(row_values, header_map, "active"), default=True),
    )



def product_import_signature(record: ProductImportRecord) -> tuple[Any, ...]:
    """Assinatura exata da linha. Não junta produtos só pelo nome para não sumir item da planilha."""
    return (
        record.product_id,
        normalize_product_lookup_key(record.name),
        normalize_product_lookup_key(record.category),
        normalize_product_lookup_key(record.unit_measure),
        normalize_product_lookup_key(record.description),
        int(record.stock_quantity or 0),
        int(record.price_cents or 0),
        record.limit_base,
        record.limit_franchise,
        record.min_stock,
        record.max_stock,
        bool(record.active),
    )


def dedupe_import_records(records: list[ProductImportRecord]) -> tuple[list[ProductImportRecord], int]:
    """Remove somente linhas 100% iguais.

    Versões anteriores juntavam tudo pelo nome do produto. Isso fazia produto desaparecer
    quando a planilha tinha itens parecidos, variações ou o mesmo nome em categorias diferentes.
    """
    seen: set[tuple[Any, ...]] = set()
    result: list[ProductImportRecord] = []
    duplicates = 0
    for record in records:
        signature = product_import_signature(record)
        if signature in seen:
            duplicates += 1
            continue
        seen.add(signature)
        result.append(record)
    return result, duplicates


def flash_import_errors(row_errors: list[str]) -> None:
    if not row_errors:
        return
    preview = "; ".join(row_errors[:5])
    suffix = "" if len(row_errors) <= 5 else f"; +{len(row_errors) - 5} outro(s) erro(s) nos logs."
    flash(f"Algumas linhas não foram importadas: {preview}{suffix}", "warning")



def worksheet_values(row: Any) -> list[Any]:
    return list(row or [])


def header_map_contains_alias(header_map: dict[str, int], aliases: list[str]) -> bool:
    normalized_aliases = [normalize_header(alias) for alias in aliases]
    for alias in normalized_aliases:
        if alias in header_map:
            return True
    for alias in normalized_aliases:
        if not alias:
            continue
        for header_key in header_map.keys():
            if not header_key:
                continue
            if alias in header_key or header_key in alias:
                return True
    return False


def header_map_score(header_map: dict[str, int]) -> int:
    required = 0
    if header_map_contains_alias(header_map, PRODUCT_IMPORT_HEADER_ALIASES["name"]):
        required += 5
    for key in ["category", "unit_measure", "description", "stock_quantity", "price_cents", "active"]:
        if header_map_contains_alias(header_map, PRODUCT_IMPORT_HEADER_ALIASES[key]):
            required += 1
    return required


def detect_product_header_row(worksheet: Any, max_scan_rows: int = 40) -> tuple[int, dict[str, int]]:
    """Encontra a linha de cabeçalho mesmo quando a planilha tem título antes da tabela."""
    best_row_number = 1
    best_map: dict[str, int] = {}
    best_score = -1
    max_row = min(int(getattr(worksheet, "max_row", 1) or 1), max_scan_rows)
    for row_number, row_values_tuple in enumerate(worksheet.iter_rows(min_row=1, max_row=max_row, values_only=True), start=1):
        row_values = worksheet_values(row_values_tuple)
        header_map = {normalize_header(value): index for index, value in enumerate(row_values) if value is not None and str(value).strip()}
        score = header_map_score(header_map)
        if score > best_score:
            best_row_number = row_number
            best_map = header_map
            best_score = score
        # Nome do produto achado e pelo menos mais um campo: já é cabeçalho confiável.
        if score >= 6:
            return row_number, header_map
    return best_row_number, best_map


def chunk_list(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def product_record_db_values(record: ProductImportRecord) -> tuple[Any, ...]:
    return (
        record.name,
        record.category,
        record.unit_measure,
        record.description,
        int(record.stock_quantity or 0),
        int(record.price_cents or 0),
        record.limit_base,
        record.limit_franchise,
        record.min_stock,
        record.max_stock,
        1 if record.active else 0,
    )


def sql_literal(value: Any) -> str:
    """Literal SQL seguro para reduzir centenas de chamadas HTTP ao D1 sem limite de parâmetros."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value:
            return "NULL"
        return str(value)
    text_value = str(value)
    # Remove caracteres de controle que podem quebrar SQL/planilha.
    text_value = "".join(ch for ch in text_value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return "'" + text_value.replace("'", "''") + "'"


def product_upsert_sql_rows(rows: list[tuple[int | None, ProductImportRecord]], created_at: str, updated_at: str) -> str:
    values_sql: list[str] = []
    for target_id, record in rows:
        values = [
            target_id,
            record.name,
            record.category,
            record.unit_measure,
            record.description,
            int(record.stock_quantity or 0),
            int(record.price_cents or 0),
            record.limit_base,
            record.limit_franchise,
            record.min_stock,
            record.max_stock,
            1 if record.active else 0,
            created_at,
            updated_at,
        ]
        values_sql.append("(" + ", ".join(sql_literal(value) for value in values) + ")")
    return ",\n".join(values_sql)


def execute_upsert_products_chunked(conn: Any, rows: list[tuple[int | None, ProductImportRecord]], row_errors: list[str]) -> tuple[int, int, int]:
    """Cria/atualiza produtos em poucos comandos, sem explodir a página em timeout/500.

    A versão anterior caía para centenas de requisições linha a linha no Cloudflare D1.
    Isso fazia o Render estourar tempo, abrir Internal Server Error e deixar a importação pela metade.
    """
    created = sum(1 for target_id, _record in rows if target_id is None)
    updated = len(rows) - created
    skipped = 0
    fields = "id, name, category, unit_measure, description, stock_quantity, price_cents, limit_base, limit_franchise, min_stock, max_stock, active, created_at, updated_at"
    update_set = """
        name = excluded.name,
        category = excluded.category,
        unit_measure = excluded.unit_measure,
        description = excluded.description,
        stock_quantity = excluded.stock_quantity,
        price_cents = excluded.price_cents,
        limit_base = excluded.limit_base,
        limit_franchise = excluded.limit_franchise,
        min_stock = excluded.min_stock,
        max_stock = excluded.max_stock,
        active = excluded.active,
        updated_at = excluded.updated_at
    """
    # 60 linhas por SQL mantém o payload pequeno e evita timeout; ainda reduz muito as chamadas ao D1.
    for chunk in chunk_list(rows, 60):
        if not chunk:
            continue
        created_at = now_iso()
        updated_at = now_iso()
        sql = f"""
        INSERT INTO products ({fields})
        VALUES {product_upsert_sql_rows(chunk, created_at, updated_at)}
        ON CONFLICT(id) DO UPDATE SET {update_set}
        """
        try:
            conn.execute(sql)
        except Exception as chunk_exc:
            print(f"[IMPORTAÇÃO PRODUTOS] Upsert em bloco falhou; tentando bloco menor: {chunk_exc}")
            # Divide novamente para impedir que uma célula problemática derrube 60 produtos.
            if len(chunk) > 1:
                for small in chunk_list(chunk, 10):
                    try:
                        small_sql = f"""
                        INSERT INTO products ({fields})
                        VALUES {product_upsert_sql_rows(small, now_iso(), now_iso())}
                        ON CONFLICT(id) DO UPDATE SET {update_set}
                        """
                        conn.execute(small_sql)
                    except Exception as small_exc:
                        print(f"[IMPORTAÇÃO PRODUTOS] Upsert em sub-bloco falhou; tentando linha a linha: {small_exc}")
                        for target_id, record in small:
                            try:
                                one_sql = f"""
                                INSERT INTO products ({fields})
                                VALUES {product_upsert_sql_rows([(target_id, record)], now_iso(), now_iso())}
                                ON CONFLICT(id) DO UPDATE SET {update_set}
                                """
                                conn.execute(one_sql)
                            except Exception as exc:
                                skipped += 1
                                if target_id is None:
                                    created -= 1
                                else:
                                    updated -= 1
                                msg = f"linha {record.source_row}: {type(exc).__name__} - {str(exc)[:180]}"
                                row_errors.append(msg)
                                print(f"[IMPORTAÇÃO PRODUTOS] Erro ao importar linha {record.source_row} ({record.name}): {exc}")
            else:
                target_id, record = chunk[0]
                skipped += 1
                if target_id is None:
                    created -= 1
                else:
                    updated -= 1
                msg = f"linha {record.source_row}: {type(chunk_exc).__name__} - {str(chunk_exc)[:180]}"
                row_errors.append(msg)
                print(f"[IMPORTAÇÃO PRODUTOS] Erro ao importar linha {record.source_row} ({record.name}): {chunk_exc}")
    return max(0, created), max(0, updated), skipped


def ensure_product_import_columns(conn: Any) -> None:
    """Garante colunas novas antes da importação, inclusive em banco D1 já criado."""
    try:
        supply_request_columns = {row["name"] for row in conn.execute("PRAGMA table_info(supply_requests)").fetchall()}
        if "people_count" not in supply_request_columns:
            conn.execute("ALTER TABLE supply_requests ADD COLUMN people_count INTEGER")

        product_columns = {row["name"] for row in conn.execute("PRAGMA table_info(products)").fetchall()}
    except Exception as exc:
        print(f"[IMPORTAÇÃO PRODUTOS] Não foi possível verificar colunas por PRAGMA: {exc}")
        return
    migrations = [
        ("unit_measure", "ALTER TABLE products ADD COLUMN unit_measure TEXT NOT NULL DEFAULT 'un'"),
        ("min_stock", "ALTER TABLE products ADD COLUMN min_stock INTEGER"),
        ("max_stock", "ALTER TABLE products ADD COLUMN max_stock INTEGER"),
    ]
    for column_name, sql in migrations:
        if column_name not in product_columns:
            try:
                conn.execute(sql)
            except Exception as exc:
                print(f"[IMPORTAÇÃO PRODUTOS] Migração ignorada para {column_name}: {exc}")


def import_products_from_workbook_bytes(uploaded_bytes: bytes) -> tuple[int, int, int, list[str]]:
    workbook = load_workbook(BytesIO(uploaded_bytes), data_only=True, read_only=True)
    worksheet = workbook.active
    if not worksheet or int(getattr(worksheet, "max_row", 0) or 0) < 1:
        return 0, 0, 0, ["planilha vazia"]

    header_row_number, header_map = detect_product_header_row(worksheet)
    if not header_map_contains_alias(header_map, PRODUCT_IMPORT_HEADER_ALIASES["name"]):
        try:
            workbook.close()
        except Exception:
            pass
        return 0, 0, 0, ["não encontrei a coluna Nome do produto / 产品名称 na planilha"]

    parsed_records: list[ProductImportRecord] = []
    skipped = 0
    row_errors: list[str] = []

    for row_number, row_values_tuple in enumerate(worksheet.iter_rows(min_row=header_row_number + 1, values_only=True), start=header_row_number + 1):
        row_values = worksheet_values(row_values_tuple)
        if excel_row_is_empty(row_values):
            continue
        try:
            record = parse_product_import_record(row_number, row_values, header_map)
            if record is None:
                skipped += 1
                continue
            parsed_records.append(record)
        except Exception as exc:
            skipped += 1
            row_errors.append(f"linha {row_number}: {type(exc).__name__} - {str(exc)[:180]}")
            print(f"[IMPORTAÇÃO PRODUTOS] Erro ao interpretar linha {row_number}: {exc}")

    parsed_records, duplicates_merged = dedupe_import_records(parsed_records)
    skipped += duplicates_merged
    if not parsed_records:
        try:
            workbook.close()
        except Exception:
            pass
        return 0, 0, skipped, row_errors

    with db_connect() as conn:
        ensure_product_import_columns(conn)
        existing_rows = conn.execute("SELECT id, name FROM products").fetchall()
        existing_by_id = {int(row["id"]): row for row in existing_rows if row["id"] is not None}
        existing_by_name = {normalize_product_lookup_key(row["name"]): row for row in existing_rows if row["name"] is not None}

        upsert_rows: list[tuple[int | None, ProductImportRecord]] = []
        for record in parsed_records:
            target_id: int | None = None
            if record.product_id is not None:
                # Se a planilha exportada do sistema tem ID, usa o ID para atualizar o produto certo.
                target_id = int(record.product_id)
            else:
                existing_row = existing_by_name.get(normalize_product_lookup_key(record.name))
                if existing_row is not None:
                    target_id = int(existing_row["id"])
            upsert_rows.append((target_id, record))

        created, updated, skipped_upsert = execute_upsert_products_chunked(conn, upsert_rows, row_errors)
        skipped += skipped_upsert
        conn.commit()
    try:
        workbook.close()
    except Exception:
        pass
    return created, updated, skipped, row_errors


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
        if not valid_organization_for_role(organization_name, role):
            flash("Selecione uma unidade válida conforme o tipo escolhido.", "warning")
            return redirect(url_for("register"))
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
    people_count_raw = str(payload.get("people_count") or "").strip()
    try:
        people_count = int(people_count_raw)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Informe o número de pessoas na base."}), 400
    if people_count <= 0 or people_count > 99999:
        return jsonify({"ok": False, "message": "Informe um número de pessoas válido."}), 400

    with db_connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO supply_requests (user_id, status, user_note, admin_note, people_count, created_at)
            VALUES (?, 'pending', ?, '', ?, ?)
            """,
            (user.id, user_note, people_count, now_iso()),
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

    try:
        created_request = get_supply_request(int(request_id))
        if created_request is not None:
            request_link = public_url_for("admin_request_detail", request_id=int(request_id))
            notify_feishu_supply_request_created(created_request, request_link)
    except Exception:
        app.logger.exception("Falha ao preparar notificacao Feishu da solicitacao")

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
    org_name = (requester.organization_name if requester else "solicitacao").replace(";", " ")
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


@app.get("/admin/assets/<int:asset_id>/pdf")
@admin_required
@page_access_required("admin_stock")
def asset_pdf(asset_id: int):
    viewer = require_current_user()
    asset = get_asset(asset_id)
    if asset is None:
        abort(404)

    unit_name = asset.base.replace(";", " ")
    filename = f"ativo_{asset.id}_{safe_filename(unit_name)}.pdf"
    buffer = build_asset_pdf(asset, viewer)
    store_generated_file(
        storage_key("pdfs", "ativos", str(asset.id), filename),
        buffer,
        "application/pdf",
        {"asset_id": str(asset.id), "unit": unit_name, "regional": asset.regional},
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
        username = normalize_username(request.form.get("username", ""))
        email = synthetic_email_for_username(username)
        password = request.form.get("password", "")
        role = request.form.get("role", "base").strip()
        status = request.form.get("status", "approved").strip()

        if role not in ["base", "franchise", "admin"]:
            role = "base"
        organization_name = request.form.get("admin_position" if role == "admin" else "organization_name", "").strip()
        selected_pages = request.form.getlist("page_permissions") or list(default_page_keys_for_role(role))

        if status not in ["pending", "approved", "rejected"]:
            status = "approved"
        if not valid_organization_for_role(organization_name, role):
            flash("Selecione uma unidade válida conforme o tipo escolhido. Para administradores, informe o cargo.", "danger")
            return render_template("admin/user_form.html", user=None, is_new=True, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))
        selected_pages = [key for key in selected_pages if key in default_page_keys_for_role(role)]
        if not selected_pages:
            selected_pages = list(default_page_keys_for_role(role))
        if not responsible_name or not organization_name or not username or not password:
            flash("Preencha responsável, unidade/cargo, nome de usuário e senha.", "danger")
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
        username = normalize_username(request.form.get("username", ""))
        email = synthetic_email_for_username(username)
        role = request.form.get("role", "base").strip()
        status = request.form.get("status", "approved").strip()
        password = request.form.get("password", "")
        selected_pages = request.form.getlist("page_permissions")

        if role not in ["base", "franchise", "admin"]:
            role = "base"
        organization_name = request.form.get("admin_position" if role == "admin" else "organization_name", "").strip()
        if status not in ["pending", "approved", "rejected"]:
            status = "approved"
        if not valid_organization_for_role(organization_name, role):
            flash("Selecione uma unidade válida conforme o tipo escolhido. Para administradores, informe o cargo.", "danger")
            return render_template("admin/user_form.html", user=target, is_new=False, permission_options=PAGE_PERMISSION_OPTIONS, selected_permissions=set(selected_pages))

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
            flash("Preencha responsável, unidade/cargo e nome de usuário.", "danger")
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

    try:
        with db_connect() as conn:
            if target.is_admin:
                approved_admins = conn.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin' AND status = 'approved'").fetchone()["total"]
                if approved_admins <= 1 and target.status == "approved":
                    flash("Não é possível excluir o último administrador aprovado.", "warning")
                    return redirect(url_for("admin_users"))
            removed_requests, _ = permanently_delete_user(conn, user_id)
            conn.commit()
        if removed_requests:
            flash(f"Usuário excluído definitivamente. {removed_requests} solicitação(ões) vinculada(s) também foram removidas do banco.", "success")
        else:
            flash("Usuário excluído definitivamente do banco de dados.", "success")
    except Exception as exc:
        app.logger.exception("Falha ao excluir usuário definitivamente")
        flash(f"Não consegui excluir o usuário do banco. Erro: {type(exc).__name__}.", "danger")
    return redirect(url_for("admin_users"))


@app.route("/admin/products")
@admin_required
@page_access_required("admin_products")
def admin_products():
    search = (request.args.get("q") or "").strip()
    status_filter = (request.args.get("status") or "all").strip().lower()
    sort_filter = (request.args.get("sort") or "default").strip().lower()

    where_clauses: list[str] = []
    params: list[Any] = []

    if search:
        like = f"%{search.lower()}%"
        where_clauses.append(
            "("
            "lower(COALESCE(name, '')) LIKE ? OR "
            "lower(COALESCE(category, '')) LIKE ? OR "
            "lower(COALESCE(description, '')) LIKE ? OR "
            "lower(COALESCE(unit_measure, '')) LIKE ?"
            ")"
        )
        params.extend([like, like, like, like])

    if status_filter == "active":
        where_clauses.append("active = 1")
    elif status_filter == "inactive":
        where_clauses.append("active = 0")
    else:
        status_filter = "all"

    sort_map = {
        "default": "active DESC, category ASC, name ASC",
        "category": "category ASC, name ASC",
        "category_desc": "category DESC, name ASC",
        "value_asc": "price_cents ASC, name ASC",
        "value_desc": "price_cents DESC, name ASC",
        "stock_asc": "stock_quantity ASC, name ASC",
        "stock_desc": "stock_quantity DESC, name ASC",
    }
    order_by = sort_map.get(sort_filter)
    if order_by is None:
        sort_filter = "default"
        order_by = sort_map[sort_filter]

    sql = "SELECT * FROM products"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    sql += " ORDER BY " + order_by

    with db_connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
        total_products = conn.execute("SELECT COUNT(*) AS total FROM products").fetchone()["total"]
        active_products = conn.execute("SELECT COUNT(*) AS total FROM products WHERE active = 1").fetchone()["total"]
        inactive_products = conn.execute("SELECT COUNT(*) AS total FROM products WHERE active = 0").fetchone()["total"]
    products = [product for row in rows if (product := row_to_product(row)) is not None]
    return render_template(
        "admin/products.html",
        products=products,
        product_filters={"q": search, "status": status_filter, "sort": sort_filter},
        product_counts={"total": total_products, "active": active_products, "inactive": inactive_products, "shown": len(products)},
    )




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
    try:
        uploaded = request.files.get("spreadsheet")
        if uploaded is None or not uploaded.filename:
            flash("Selecione uma planilha .xlsx para importar.", "warning")
            return redirect(url_for("admin_products"))
        if not uploaded.filename.lower().endswith(".xlsx"):
            flash("Importe apenas arquivos .xlsx.", "warning")
            return redirect(url_for("admin_products"))

        try:
            uploaded_bytes = uploaded.read()
        except Exception as exc:
            print(f"[IMPORTAÇÃO PRODUTOS] Falha ao ler upload: {exc}")
            flash("Não foi possível ler o arquivo enviado.", "danger")
            return redirect(url_for("admin_products"))

        if not uploaded_bytes:
            flash("A planilha enviada está vazia.", "warning")
            return redirect(url_for("admin_products"))

        # Salvar cópia no R2 é opcional e nunca pode derrubar a importação.
        try:
            upload_bytes_to_r2(
                storage_key("imports", datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + safe_filename(uploaded.filename)),
                uploaded_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                {"type": "products_import"},
            )
        except Exception as exc:
            print(f"[R2] Não foi possível salvar cópia da planilha importada: {exc}")

        try:
            created, updated, skipped, row_errors = import_products_from_workbook_bytes(uploaded_bytes)
        except Exception as exc:
            try:
                import traceback
                traceback.print_exc()
            except Exception:
                pass
            print(f"[IMPORTAÇÃO PRODUTOS] Erro geral tratado: {type(exc).__name__} - {exc}")
            flash("Não consegui importar essa planilha. O erro foi registrado nos logs do Render; envie o trecho vermelho se continuar acontecendo.", "danger")
            return redirect(url_for("admin_products"))

        flash_import_errors(row_errors)
        if created or updated:
            flash(f"Importação concluída: {created} criado(s), {updated} atualizado(s), {skipped} ignorado(s).", "success")
        elif skipped or row_errors:
            flash(f"Nenhum produto foi criado ou atualizado. {skipped} linha(s) ignorada(s).", "warning")
        else:
            flash("Nenhum produto válido foi encontrado na planilha. Confira se a primeira linha contém os cabeçalhos corretos.", "warning")
        return redirect(url_for("admin_products"))
    except Exception as exc:
        # Última barreira para impedir Internal Server Error branco na tela.
        try:
            import traceback
            traceback.print_exc()
        except Exception:
            pass
        print(f"[IMPORTAÇÃO PRODUTOS] Falha inesperada capturada: {type(exc).__name__} - {exc}")
        flash("A importação falhou, mas o site não quebrou. Veja os logs do Render para o detalhe do erro.", "danger")
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


@app.post("/admin/products/<int:product_id>/toggle-active")
@admin_required
@page_access_required("admin_products")
def admin_product_toggle_active(product_id: int):
    product = get_product(product_id)
    if product is None:
        abort(404)

    new_active = 0 if product.active else 1
    try:
        with db_connect() as conn:
            conn.execute(
                "UPDATE products SET active = ?, updated_at = ? WHERE id = ?",
                (new_active, now_iso(), product_id),
            )
            conn.commit()
        if new_active:
            flash(f"Produto '{product.name}' ativado para solicitação.", "success")
        else:
            flash(f"Produto '{product.name}' inativado para solicitação. Ele continua salvo no banco de dados.", "success")
    except Exception as exc:
        app.logger.exception("Falha ao alterar status do produto")
        flash(f"Não consegui alterar o status do produto. Erro: {type(exc).__name__}.", "danger")
    return redirect(url_for("admin_products"))


@app.post("/admin/products/<int:product_id>/delete")
@admin_required
@page_access_required("admin_products")
def admin_product_delete(product_id: int):
    try:
        with db_connect() as conn:
            product_name, removed_items, removed_requests = permanently_delete_product(conn, product_id)
            conn.commit()
        details: list[str] = []
        if removed_items:
            details.append(f"{removed_items} vínculo(s) em solicitações")
        if removed_requests:
            details.append(f"{removed_requests} solicitação(ões) vazia(s)")
        suffix = f" Removidos também: {', '.join(details)}." if details else ""
        flash(f"Produto '{product_name}' excluído definitivamente do banco de dados.{suffix}", "success")
    except LookupError:
        abort(404)
    except Exception as exc:
        app.logger.exception("Falha ao excluir produto definitivamente")
        flash(f"Não consegui excluir o produto do banco. Erro: {type(exc).__name__}.", "danger")
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


@app.route("/admin/assets")
@admin_required
@page_access_required("admin_stock")
def admin_assets():
    selected_base = (request.args.get("base") or "").strip()
    selected_franchise = (request.args.get("franchise") or "").strip()
    selected_regional = normalize_asset_regional(request.args.get("regional", ""))
    filtered_asset_base_options = base_unit_options_for_asset_regional(selected_regional)
    filtered_asset_franchise_options = franchise_unit_options_for_asset_regional(selected_regional)

    if selected_base and selected_base not in filtered_asset_base_options:
        selected_base = ""
    if selected_franchise and selected_franchise not in filtered_asset_franchise_options:
        selected_franchise = ""
    if selected_base and selected_franchise:
        flash("Selecione somente uma base ou uma franquia para filtrar.", "warning")
        selected_franchise = ""

    selected_unit = selected_base or selected_franchise
    assets = list_assets(base=selected_unit, regional=selected_regional)
    with db_connect() as conn:
        product_rows = conn.execute("SELECT * FROM products WHERE active = 1 ORDER BY category ASC, name ASC").fetchall()
    asset_product_options = [
        {
            "id": product.id,
            "name": product.name,
            "category": product.category or "Sem categoria",
            "stock_quantity": product.stock_quantity,
            "unit_measure": product.unit_measure or "un",
        }
        for row in product_rows
        if (product := row_to_product(row)) is not None
    ]
    totals = {
        "assets": len(assets),
        "items": sum(sum(item.quantity for item in asset.items) for asset in assets),
        "bases": len({asset.base for asset in assets if asset.base}),
        "mg": sum(1 for asset in assets if asset.regional == "MG"),
        "spn": sum(1 for asset in assets if asset.regional == "SPN"),
        "matriz": sum(1 for asset in assets if asset.regional == "Matriz"),
    }
    return render_template(
        "admin/assets.html",
        assets=assets,
        totals=totals,
        selected_base=selected_base,
        selected_franchise=selected_franchise,
        selected_regional=selected_regional,
        filtered_asset_base_options=filtered_asset_base_options,
        filtered_asset_franchise_options=filtered_asset_franchise_options,
        filtered_base_options=base_options_for_asset_regional(selected_regional),
        asset_product_options=asset_product_options,
    )


@app.post("/admin/assets/new")
@admin_required
@page_access_required("admin_stock")
def admin_asset_new():
    name = request.form.get("name", "").strip()
    base = request.form.get("base", "").strip()
    regional = request.form.get("regional", "").strip().upper()
    sector = request.form.get("sector", "").strip()
    manager = request.form.get("manager", "").strip()
    item_names = request.form.getlist("item_name")
    serial_numbers = request.form.getlist("serial_number")

    item_rows: list[tuple[str, str]] = []
    for index, raw_item_name in enumerate(item_names):
        item_name = (raw_item_name or "").strip()
        if not item_name:
            continue
        serial_number = (serial_numbers[index] if index < len(serial_numbers) else "").strip()
        item_rows.append((item_name[:180], serial_number[:120]))

    if not name or not base or not regional or not sector or not manager:
        flash("Preencha nome, base/franquia, regional, setor e gestor para adicionar o ativo.", "warning")
        return redirect(url_for("admin_assets"))
    if base not in BASE_FRANCHISE_OPTION_SET:
        flash("Selecione uma base ou franquia válida para o ativo.", "warning")
        return redirect(url_for("admin_assets"))
    if regional not in ASSET_REGIONAL_OPTION_SET:
        flash("Selecione uma regional válida para o ativo.", "warning")
        return redirect(url_for("admin_assets"))
    if asset_regional_for_base(base) != regional:
        flash("A base/franquia selecionada não pertence à regional informada.", "warning")
        return redirect(url_for("admin_assets", regional=regional))
    if not item_rows:
        flash("Adicione pelo menos um item ao ativo.", "warning")
        return redirect(url_for("admin_assets"))

    try:
        with db_connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO assets (name, base, regional, sector, manager, created_by_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name[:180], base, regional, sector[:120], manager[:120], require_current_user().id, now_iso()),
            )
            asset_id = get_cursor_lastrowid(cursor)
            if asset_id is None:
                raise RuntimeError("Não foi possível identificar o ativo criado.")
            for item_name, serial_number in item_rows:
                conn.execute(
                    """
                    INSERT INTO asset_items (asset_id, item_name, serial_number, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (int(asset_id), item_name, serial_number, now_iso()),
                )
            conn.commit()
        flash("Ativo adicionado ao relatório.", "success")
    except Exception as exc:
        app.logger.exception("Falha ao adicionar ativo")
        flash(f"Não consegui adicionar o ativo. Erro: {type(exc).__name__}.", "danger")
    return redirect(url_for("admin_assets", base=base, regional=regional))


def admin_asset_new_with_stock():
    name = request.form.get("name", "").strip()
    base = request.form.get("base", "").strip()
    regional = normalize_asset_regional(request.form.get("regional", ""))
    sector = request.form.get("sector", "").strip()
    manager = request.form.get("manager", "").strip()
    item_names = request.form.getlist("item_name")
    product_ids = request.form.getlist("product_id")
    quantities = request.form.getlist("quantity")
    serial_numbers = request.form.getlist("serial_number")

    item_rows: list[dict[str, Any]] = []
    missing_product = False
    invalid_quantity = False
    for index, raw_item_name in enumerate(item_names):
        item_name = (raw_item_name or "").strip()
        product_id = parse_required_positive_int(product_ids[index] if index < len(product_ids) else "")
        quantity = parse_required_positive_int(quantities[index] if index < len(quantities) else "")
        if not item_name and product_id is None:
            continue
        if product_id is None:
            missing_product = True
            continue
        if quantity is None:
            invalid_quantity = True
            continue
        serial_number = (serial_numbers[index] if index < len(serial_numbers) else "").strip()
        item_rows.append({"product_id": product_id, "quantity": quantity, "serial_number": serial_number[:120]})

    if regional == "Matriz":
        base = "Matriz"

    redirect_args = {"regional": regional}
    if regional != "Matriz" and base:
        redirect_args["base"] = base

    if not name or not regional or not sector or not manager or (regional != "Matriz" and not base):
        flash("Preencha nome, base/franquia, regional, setor e gestor para adicionar o ativo.", "warning")
        return redirect(url_for("admin_assets"))
    if not regional:
        flash("Selecione uma regional valida para o ativo.", "warning")
        return redirect(url_for("admin_assets"))
    if regional != "Matriz" and base not in BASE_FRANCHISE_OPTION_SET:
        flash("Selecione uma base ou franquia valida para o ativo.", "warning")
        return redirect(url_for("admin_assets", regional=regional))
    if regional != "Matriz" and asset_regional_for_base(base) != regional:
        flash("A base/franquia selecionada nao pertence a regional informada.", "warning")
        return redirect(url_for("admin_assets", regional=regional))
    if missing_product:
        flash("Selecione cada item pela lista de produtos do portal.", "warning")
        return redirect(url_for("admin_assets", **redirect_args))
    if invalid_quantity:
        flash("Informe uma quantidade valida para cada item.", "warning")
        return redirect(url_for("admin_assets", **redirect_args))
    if not item_rows:
        flash("Adicione pelo menos um item ao ativo.", "warning")
        return redirect(url_for("admin_assets", **redirect_args))

    try:
        with db_connect() as conn:
            requested_by_product: dict[int, int] = {}
            for item in item_rows:
                requested_by_product[item["product_id"]] = requested_by_product.get(item["product_id"], 0) + item["quantity"]

            product_ids_unique = sorted(requested_by_product)
            placeholders = ", ".join(["?"] * len(product_ids_unique))
            product_rows = conn.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", product_ids_unique).fetchall()
            product_map = {
                int(row["id"]): product
                for row in product_rows
                if (product := row_to_product(row)) is not None
            }
            missing_ids = [product_id for product_id in product_ids_unique if product_id not in product_map]
            inactive = [product.name for product in product_map.values() if not product.active]
            insufficient = [
                f"{product_map[product_id].name} (solicitado {quantity}, estoque {product_map[product_id].stock_quantity})"
                for product_id, quantity in requested_by_product.items()
                if product_id in product_map and product_map[product_id].stock_quantity < quantity
            ]
            if missing_ids:
                flash("Um ou mais produtos selecionados nao existem mais no cadastro.", "warning")
                return redirect(url_for("admin_assets", **redirect_args))
            if inactive:
                flash("Produto(s) inativo(s) nao podem ser vinculados a ativos: " + ", ".join(inactive), "warning")
                return redirect(url_for("admin_assets", **redirect_args))
            if insufficient:
                flash("Estoque insuficiente para: " + "; ".join(insufficient), "warning")
                return redirect(url_for("admin_assets", **redirect_args))

            current = require_current_user()
            cursor = conn.execute(
                """
                INSERT INTO assets (name, base, regional, sector, manager, created_by_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name[:180], base, regional, sector[:120], manager[:120], current.id, now_iso()),
            )
            asset_id = get_cursor_lastrowid(cursor)
            if asset_id is None:
                raise RuntimeError("Nao foi possivel identificar o ativo criado.")
            for item in item_rows:
                product = product_map[item["product_id"]]
                quantity = item["quantity"]
                stock_before = product.stock_quantity
                stock_after = stock_before - quantity
                conn.execute(
                    "UPDATE products SET stock_quantity = ?, updated_at = ? WHERE id = ?",
                    (stock_after, now_iso(), product.id),
                )
                conn.execute(
                    """
                    INSERT INTO asset_items (asset_id, product_id, item_name, quantity, serial_number, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (int(asset_id), product.id, product.name, quantity, item["serial_number"], now_iso()),
                )
                record_stock_movement(
                    conn,
                    product.id,
                    -quantity,
                    stock_before,
                    stock_after,
                    "asset_allocation",
                    f"Saida para ativo #{asset_id} - {name}.",
                    created_by_id=current.id,
                )
                product.stock_quantity = stock_after
            conn.commit()
            try:
                asset_link = public_url_for(
                    "admin_assets",
                    regional=regional,
                    base=base,
                    _anchor=f"asset-{asset_id}",
                )
                notify_feishu_asset_created(
                    int(asset_id),
                    name,
                    base,
                    regional,
                    sector,
                    manager,
                    current,
                    item_rows,
                    product_map,
                    asset_link,
                )
            except Exception:
                app.logger.exception("Falha ao preparar notificacao Feishu do ativo")
        flash("Ativo adicionado ao relatorio e estoque baixado.", "success")
    except Exception as exc:
        app.logger.exception("Falha ao adicionar ativo")
        flash(f"Nao consegui adicionar o ativo. Erro: {type(exc).__name__}.", "danger")
    return redirect(url_for("admin_assets", **redirect_args))


app.view_functions["admin_asset_new"] = admin_required(page_access_required("admin_stock")(admin_asset_new_with_stock))


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
        base_unit_options=BASE_UNIT_OPTIONS,
        franchise_unit_options=FRANCHISE_UNIT_OPTIONS,
    )


@app.get("/admin/stock/requests-report")
@admin_required
@page_access_required("admin_stock")
def admin_stock_requests_report():
    start_raw = (request.args.get("start_date") or "").strip()
    end_raw = (request.args.get("end_date") or "").strip()
    base_raw = (request.args.get("base") or "").strip()
    franchise_raw = (request.args.get("franchise") or "").strip()
    all_units = (request.args.get("all_units") or "").strip().lower() in {"1", "true", "on", "all", "todos"}
    if not start_raw or not end_raw:
        flash("Informe a data inicial e a data final para gerar o relatório.", "warning")
        return redirect(url_for("admin_stock"))

    try:
        if all_units:
            selected_unit, selected_kind = "", "all"
        else:
            selected_unit, selected_kind = validate_unit_selection(base_raw, franchise_raw, required=True)
        start_dt = parse_report_date(start_raw, "Data inicial")
        end_base = parse_report_date(end_raw, "Data final")
        end_dt = end_base + timedelta(days=1) - timedelta(seconds=1)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin_stock"))

    if end_dt < start_dt:
        flash("A data final não pode ser menor que a data inicial.", "warning")
        return redirect(url_for("admin_stock"))

    requests_list = list_supply_requests_between(start_dt, end_dt, selected_unit)
    buffer = build_supply_requests_period_report_pdf(requests_list, start_dt, end_dt, require_current_user(), selected_unit, selected_kind)
    unit_slug = "todas_unidades" if selected_kind == "all" else (re.sub(r"[^A-Za-z0-9]+", "_", selected_unit).strip("_").lower() or "unidade")
    filename = f"relatorio_solicitacoes_insumos_{unit_slug}_{start_dt.strftime('%Y%m%d')}_{end_base.strftime('%Y%m%d')}.pdf"
    store_generated_file(
        storage_key("reports", "supply_requests", filename),
        buffer,
        "application/pdf",
        {"type": "supply_requests_period_report", "start_date": start_raw, "end_date": end_raw, "unit": selected_unit, "unit_kind": selected_kind},
    )
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


@app.get("/admin/assets/period-report")
@admin_required
@page_access_required("admin_stock")
def admin_assets_period_report():
    start_raw = (request.args.get("start_date") or "").strip()
    end_raw = (request.args.get("end_date") or "").strip()
    base_raw = (request.args.get("base") or "").strip()
    franchise_raw = (request.args.get("franchise") or "").strip()
    all_units = (request.args.get("all_units") or "").strip().lower() in {"1", "true", "on", "all", "todos"}
    if not start_raw or not end_raw:
        flash("Informe a data inicial e a data final para gerar o relatório de ativos.", "warning")
        return redirect(url_for("admin_assets"))

    try:
        if all_units:
            selected_unit, selected_kind = "", "all"
        else:
            selected_unit, selected_kind = validate_unit_selection(base_raw, franchise_raw, required=True)
        start_dt = parse_report_date(start_raw, "Data inicial")
        end_base = parse_report_date(end_raw, "Data final")
        end_dt = end_base + timedelta(days=1) - timedelta(seconds=1)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin_assets"))

    if end_dt < start_dt:
        flash("A data final não pode ser menor que a data inicial.", "warning")
        return redirect(url_for("admin_assets"))

    assets = list_assets_between(start_dt, end_dt, selected_unit)
    buffer = build_assets_period_report_pdf(assets, start_dt, end_dt, require_current_user(), selected_unit, selected_kind)
    unit_slug = "todas_unidades" if selected_kind == "all" else (re.sub(r"[^A-Za-z0-9]+", "_", selected_unit).strip("_").lower() or "unidade")
    filename = f"relatorio_ativos_{unit_slug}_{start_dt.strftime('%Y%m%d')}_{end_base.strftime('%Y%m%d')}.pdf"
    store_generated_file(
        storage_key("reports", "assets", filename),
        buffer,
        "application/pdf",
        {"type": "assets_period_report", "start_date": start_raw, "end_date": end_raw, "unit": selected_unit, "unit_kind": selected_kind},
    )
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


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
    try:
        with db_connect() as conn:
            deleted = permanently_delete_supply_request(conn, request_id)
            if not deleted:
                raise LookupError("Solicitação não encontrada.")
            conn.commit()
        flash("Solicitação excluída definitivamente do banco de dados.", "success")
    except LookupError:
        abort(404)
    except Exception as exc:
        app.logger.exception("Falha ao excluir solicitação definitivamente")
        flash(f"Não consegui excluir a solicitação do banco. Erro: {type(exc).__name__}.", "danger")
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
