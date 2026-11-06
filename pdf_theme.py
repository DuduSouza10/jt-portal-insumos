"""Tema visual compartilhado dos PDFs do Portal de Insumos J&T Express.

Todos os PDFs (solicitação, relatórios, ficha de ativo, entrada de materiais)
usam este módulo para ficarem com a mesma identidade: fonte Barlow (a mesma do
site), cabeçalho com logo, cartões de indicadores, tabelas limpas e rodapé com
numeração "Página X de Y".

Os ideogramas chineses continuam funcionando: o texto latino usa Barlow e
somente os trechos CJK são trocados para a fonte STSong-Light.
"""
from __future__ import annotations

import re
from html import escape as html_escape
from io import BytesIO
from pathlib import Path
from typing import Any, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import BaseDocTemplate, CondPageBreak, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle

try:  # svglib é opcional: sem ele o logo vira texto.
    from svglib.svglib import svg2rlg
except Exception:  # pragma: no cover
    svg2rlg = None  # type: ignore[assignment]

BASE_DIR = Path(__file__).resolve().parent
FONT_DIR = BASE_DIR / "static" / "fonts" / "pdf"
LOGO_PATH = BASE_DIR / "static" / "img" / "logo-jt-red.svg"

# ---------------------------------------------------------------- paleta
RED = colors.HexColor("#e60012")
RED_SOFT = colors.HexColor("#fdeced")
INK = colors.HexColor("#17171a")
TEXT = colors.HexColor("#2b2b31")
MUTED = colors.HexColor("#6c6c75")
FAINT = colors.HexColor("#a0a0a9")
LINE = colors.HexColor("#e5e5ea")
LINE_STRONG = colors.HexColor("#cfcfd6")
SOFT = colors.HexColor("#f5f5f7")
WHITE = colors.white

STATUS_COLORS = {
    "pending": "#b45309",
    "approved": "#1d4ed8",
    "awaiting_shipment": "#1d4ed8",
    "shipped": "#15803d",
    "rejected": "#b91c1c",
    "deleted": "#6c6c75",
}

# ---------------------------------------------------------------- fontes
SANS = "Helvetica"
SANS_MEDIUM = "Helvetica"
SANS_SEMIBOLD = "Helvetica-Bold"
SANS_BOLD = "Helvetica-Bold"
CJK = "Helvetica"

PAGE_W, PAGE_H = A4
MARGIN_X = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X  # 178 mm

_fonts_ready = False


def register_fonts() -> None:
    """Registra Barlow (TTF) e a fonte CJK. Seguro para chamar várias vezes."""
    global SANS, SANS_MEDIUM, SANS_SEMIBOLD, SANS_BOLD, CJK, _fonts_ready
    if _fonts_ready:
        return
    _fonts_ready = True
    try:
        pdfmetrics.registerFont(TTFont("JTSans", str(FONT_DIR / "Barlow-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("JTSans-Medium", str(FONT_DIR / "Barlow-Medium.ttf")))
        pdfmetrics.registerFont(TTFont("JTSans-SemiBold", str(FONT_DIR / "Barlow-SemiBold.ttf")))
        pdfmetrics.registerFont(TTFont("JTSans-Bold", str(FONT_DIR / "Barlow-Bold.ttf")))
        registerFontFamily("JTSans", normal="JTSans", bold="JTSans-Bold", italic="JTSans", boldItalic="JTSans-Bold")
        SANS, SANS_MEDIUM, SANS_SEMIBOLD, SANS_BOLD = "JTSans", "JTSans-Medium", "JTSans-SemiBold", "JTSans-Bold"
    except Exception as exc:  # fallback: Helvetica embutida no PDF viewer
        print(f"[PDF] Aviso: Barlow indisponível, usando Helvetica: {exc}")
    try:
        if "STSong-Light" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        CJK = "STSong-Light"
    except Exception as exc:
        print(f"[PDF] Aviso: fonte chinesa indisponível: {exc}")
        CJK = SANS


register_fonts()

# ---------------------------------------------------------------- texto
_CJK_RE = re.compile(r"([㐀-䶿一-鿿豈-﫿　-〿＀-￯]+)")


# Nomes antigos de base/franquia vieram com ";" no lugar de espaços ("BASE;SP;04").
# Só trocamos quando o ";" está colado na palavra seguinte; pontuação normal fica.
_LEGACY_SEMICOLON = re.compile(r";(?=\S)")


def num(value: Any) -> str:
    """Inteiro com separador de milhar brasileiro (1.234)."""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def plain(value: Any, default: str = "-") -> str:
    """Texto limpo (sem escapar) para canvas.drawString."""
    text = str(value if value is not None else "").strip()
    text = _LEGACY_SEMICOLON.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or default


def txt(value: Any, default: str = "-") -> str:
    """Texto seguro para Paragraph: escapa HTML, preserva quebras de linha e usa
    a fonte CJK apenas nos ideogramas."""
    raw = str(value if value is not None else "").strip()
    if not raw:
        return html_escape(default)
    lines = []
    for line in raw.splitlines():
        line = re.sub(r"[ \t]+", " ", _LEGACY_SEMICOLON.sub(" ", line)).strip()
        if line:
            lines.append(line)
    if not lines:
        return html_escape(default)
    out_lines = []
    for line in lines:
        parts = []
        for part in _CJK_RE.split(line):
            if not part:
                continue
            esc = html_escape(part)
            parts.append(f'<font name="{CJK}">{esc}</font>' if _CJK_RE.fullmatch(part) else esc)
        out_lines.append("".join(parts))
    return "<br/>".join(out_lines)


# ---------------------------------------------------------------- estilos
class Styles:
    """Conjunto de estilos de parágrafo; `s(nome, align)` devolve variações."""

    def __init__(self) -> None:
        def ps(name: str, **kw: Any) -> ParagraphStyle:
            base = dict(fontName=SANS, fontSize=9, leading=12, textColor=TEXT, alignment=TA_LEFT)
            base.update(kw)
            return ParagraphStyle(name, **base)

        self.items: dict[str, ParagraphStyle] = {
            "title": ps("title", fontName=SANS_BOLD, fontSize=23, leading=26, textColor=INK),
            "subtitle": ps("subtitle", fontSize=9.4, leading=13, textColor=MUTED),
            "eyebrow": ps("eyebrow", fontName=SANS_SEMIBOLD, fontSize=7.6, leading=10, textColor=RED),
            "section": ps("section", fontName=SANS_BOLD, fontSize=12.5, leading=15, textColor=INK, spaceBefore=2, spaceAfter=6),
            "label": ps("label", fontName=SANS_MEDIUM, fontSize=7.4, leading=9.2, textColor=MUTED),
            "value": ps("value", fontName=SANS_SEMIBOLD, fontSize=10, leading=12.6, textColor=INK),
            "kpi": ps("kpi", fontName=SANS_BOLD, fontSize=17, leading=19, textColor=INK),
            "th": ps("th", fontName=SANS_SEMIBOLD, fontSize=7.6, leading=9.6, textColor=INK),
            "cell": ps("cell", fontSize=8.4, leading=10.8),
            "cell_b": ps("cell_b", fontName=SANS_SEMIBOLD, fontSize=8.4, leading=10.8, textColor=INK),
            "small": ps("small", fontSize=7.4, leading=9.4, textColor=MUTED),
            "meta": ps("meta", fontSize=8.4, leading=11.2, textColor=MUTED),
            "meta_b": ps("meta_b", fontName=SANS_SEMIBOLD, fontSize=8.4, leading=11.2, textColor=INK),
            "note": ps("note", fontSize=8.6, leading=11.8, textColor=TEXT),
        }
        self._cache: dict[tuple[str, int], ParagraphStyle] = {}

    def s(self, name: str, align: str = "L") -> ParagraphStyle:
        base = self.items[name]
        code = {"L": TA_LEFT, "R": TA_RIGHT, "C": TA_CENTER}[align]
        if code == base.alignment:
            return base
        key = (name, code)
        if key not in self._cache:
            self._cache[key] = ParagraphStyle(f"{name}_{align}", parent=base, alignment=code)
        return self._cache[key]

    def p(self, value: Any, name: str = "cell", align: str = "L", default: str = "-") -> Paragraph:
        return Paragraph(txt(value, default), self.s(name, align))

    def raw(self, markup: str, name: str = "cell", align: str = "L") -> Paragraph:
        return Paragraph(markup, self.s(name, align))


def status_markup(label: str, status_key: str) -> str:
    color = STATUS_COLORS.get(status_key, "#6c6c75")
    return f'<font color="{color}" size="11">•</font> <font color="{color}">{txt(label)}</font>'


# ---------------------------------------------------------------- logo
def logo(width: float = 32 * mm) -> Any:
    try:
        if svg2rlg is None:
            raise ValueError("svglib indisponível")
        drawing = svg2rlg(str(LOGO_PATH))
        if drawing is None or not drawing.width:
            raise ValueError("Logo SVG inválida")
        scale = width / drawing.width
        drawing.width *= scale
        drawing.height *= scale
        drawing.scale(scale, scale)
        drawing.hAlign = "LEFT"
        return drawing
    except Exception:
        return Paragraph(
            "J&amp;T EXPRESS",
            ParagraphStyle("fallback_logo", fontName=SANS_BOLD, fontSize=14, leading=16, textColor=RED),
        )


# ---------------------------------------------------------------- blocos
def _rounded(table_kwargs: dict[str, Any]) -> dict[str, Any]:
    return table_kwargs


def header_block(
    st: Styles,
    title: str,
    subtitle: str = "",
    eyebrow: str = "Portal de Insumos",
    issued_at: str = "",
    right_markup: str = "",
    logo_width: float = 32 * mm,
) -> list[Any]:
    """Cabeçalho: logo à esquerda, tipo/emissão à direita, título e subtítulo."""
    right = f'<font name="{SANS_SEMIBOLD}" color="#e60012">{txt(eyebrow.upper())}</font>'
    if right_markup:
        right += f"<br/>{right_markup}"
    if issued_at:
        right += f'<br/><font color="#6c6c75">Emitido em {txt(issued_at)}</font>'
    top = Table(
        [[logo(logo_width), Paragraph(right, st.s("meta", "R"))]],
        colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5],
    )
    top.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE_STRONG),
    ]))
    out: list[Any] = [top, Spacer(1, 6 * mm), Paragraph(txt(title), st.s("title"))]
    if subtitle:
        out += [Spacer(1, 1.2 * mm), Paragraph(txt(subtitle), st.s("subtitle"))]
    out.append(Spacer(1, 5 * mm))
    return out


def kpi_row(st: Styles, items: Sequence[tuple[str, Any]], width: float = CONTENT_W, gap: float = 2.2 * mm) -> Table:
    """Cartões de indicadores: valor grande + legenda, com filete vermelho no topo."""
    n = len(items)
    cell_w = (width - gap * (n - 1)) / n
    row: list[Any] = []
    col_widths: list[float] = []
    for index, (label, value) in enumerate(items):
        value_text = num(value) if isinstance(value, int) else str(value)
        size = 17.0
        avail = cell_w - 15
        while size > 10 and pdfmetrics.stringWidth(value_text, SANS_BOLD, size) > avail:
            size -= 0.5
        value_par = Paragraph(
            txt(value_text),
            ParagraphStyle(f"kpi_{index}", parent=st.items["kpi"], fontSize=size, leading=size + 2),
        )
        inner = Table(
            [[value_par], [st.p(label, "label")]],
            colWidths=[cell_w],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT),
            ("LINEABOVE", (0, 0), (-1, 0), 1.6, RED),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (0, 0), 8),
            ("BOTTOMPADDING", (0, 0), (0, 0), 1),
            ("TOPPADDING", (0, 1), (0, 1), 0),
            ("BOTTOMPADDING", (0, 1), (0, 1), 8),
        ]))
        row.append(inner)
        col_widths.append(cell_w)
        if index < n - 1:
            row.append("")
            col_widths.append(gap)
    outer = Table([row], colWidths=col_widths)
    outer.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return outer


def section_title(st: Styles, text: str, hint: str = "") -> list[Any]:
    markup = txt(text)
    if hint:
        markup += f' <font name="{SANS}" size="8.4" color="#a0a0a9">&nbsp; {txt(hint)}</font>'
    # evita título órfão no pé da página (precisa de ~38 mm livres para o início da tabela)
    return [CondPageBreak(38 * mm), Paragraph(markup, st.s("section"))]


def info_grid(st: Styles, fields: Sequence[tuple[str, Any]], cols: int = 3, width: float = CONTENT_W) -> Table:
    """Grade de campos rótulo/valor com filetes finos (sem fundo pesado)."""
    cols = max(1, min(cols, len(fields))) if fields else 1
    cell_w = width / cols
    rows: list[list[Any]] = []
    for start in range(0, len(fields), cols):
        chunk = list(fields[start:start + cols])
        cells: list[Any] = []
        for label, value in chunk:
            markup_value = value if isinstance(value, _Markup) else None
            value_par = st.raw(value.html, "value") if markup_value else st.p(value, "value")
            inner = Table([[st.p(label, "label")], [value_par]], colWidths=[cell_w])
            inner.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (0, 0), 8),
                ("BOTTOMPADDING", (0, 0), (0, 0), 1),
                ("TOPPADDING", (0, 1), (0, 1), 0),
                ("BOTTOMPADDING", (0, 1), (0, 1), 9),
            ]))
            cells.append(inner)
        while len(cells) < cols:
            cells.append("")
        rows.append(cells)
    grid = Table(rows, colWidths=[cell_w] * cols)
    grid.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE_STRONG),
        ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    grid.hAlign = "LEFT"
    return grid


class _Markup:
    """Marca um valor já formatado em markup de Paragraph (não escapar)."""

    def __init__(self, html: str) -> None:
        self.html = html


def markup(html: str) -> _Markup:
    return _Markup(html)


def data_table(
    st: Styles,
    header: Sequence[str],
    rows: Sequence[Sequence[Any]],
    col_widths: Sequence[float],
    align: Sequence[str] | None = None,
    total: Sequence[Any] | None = None,
    empty_message: str = "",
    zebra: bool = False,
    extra_style: Sequence[tuple[Any, ...]] = (),
) -> Table:
    """Tabela limpa: cabeçalho cinza claro, filetes horizontais, números à direita.

    Células de `rows` podem ser texto simples (vira Paragraph) ou flowables prontos.
    """
    ncols = len(header)
    align = list(align or ["L"] * ncols)
    data: list[list[Any]] = [[st.p(h, "th", align[i]) for i, h in enumerate(header)]]
    for row in rows:
        out: list[Any] = []
        for i, cell in enumerate(row):
            if isinstance(cell, _Markup):
                out.append(st.raw(cell.html, "cell", align[i]))
            elif isinstance(cell, (str, int, float)) or cell is None:
                out.append(st.p(cell, "cell", align[i]))
            else:
                out.append(cell)
        data.append(out)
    if not rows and empty_message:
        data.append([st.p(empty_message, "meta")] + [""] * (ncols - 1))
    total_index = None
    if total is not None:
        total_index = len(data)
        data.append([
            (st.raw(c.html, "cell_b", align[i]) if isinstance(c, _Markup) else st.p(c, "cell_b", align[i], default=""))
            for i, c in enumerate(total)
        ])
    table = Table(data, colWidths=list(col_widths), repeatRows=1)
    style: list[tuple[Any, ...]] = [
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINE_STRONG),
        ("LINEBELOW", (0, 1), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5.2),
        ("TOPPADDING", (0, 0), (-1, 0), 5.6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5.6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
    ]
    if not rows and empty_message:
        style += [("SPAN", (0, 1), (-1, 1)), ("TOPPADDING", (0, 1), (-1, 1), 12), ("BOTTOMPADDING", (0, 1), (-1, 1), 12)]
    if zebra and rows:
        for r in range(2, 1 + len(rows), 2):
            style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#fafafb")))
    if total_index is not None:
        style += [
            ("LINEABOVE", (0, total_index), (-1, total_index), 1.0, INK),
            ("LINEBELOW", (0, total_index), (-1, total_index), 0, WHITE),
            ("BACKGROUND", (0, total_index), (-1, total_index), SOFT),
            ("TOPPADDING", (0, total_index), (-1, total_index), 7),
            ("BOTTOMPADDING", (0, total_index), (-1, total_index), 7),
        ]
    style += list(extra_style)
    table.setStyle(TableStyle(style))
    return table


def note_box(st: Styles, label: str, text: str, width: float = CONTENT_W) -> Table:
    """Observação com filete vermelho à esquerda."""
    box = Table([[st.p(label, "label")], [st.p(text, "note")]], colWidths=[width])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, RED),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (0, 0), 8),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
        ("TOPPADDING", (0, 1), (0, 1), 0),
        ("BOTTOMPADDING", (0, 1), (0, 1), 9),
    ]))
    return box


def signature_block(st: Styles, labels: Sequence[str], width: float = CONTENT_W) -> Table:
    n = len(labels)
    gap = 14 * mm
    col_w = (width - gap * (n - 1)) / n
    widths: list[float] = []
    top: list[Any] = []
    bottom: list[Any] = []
    for i, label in enumerate(labels):
        top.append("")
        bottom.append(st.p(label, "small", "C"))
        widths.append(col_w)
        if i < n - 1:
            top.append("")
            bottom.append("")
            widths.append(gap)
    table = Table([top, bottom], colWidths=widths, rowHeights=[16 * mm, None])
    cmds: list[tuple[Any, ...]] = [
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 0),
    ]
    for i in range(n):
        col = i * 2
        cmds.append(("LINEBELOW", (col, 0), (col, 0), 0.7, INK))
    table.setStyle(TableStyle(cmds))
    return table


def spacer(mm_height: float) -> Spacer:
    return Spacer(1, mm_height * mm)


# ---------------------------------------------------------------- documento
def _canvas_class(footer_left: str, running_title: str):
    class JTCanvas(rl_canvas.Canvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._saved_pages: list[dict[str, Any]] = []

        def showPage(self) -> None:  # noqa: N802 (API do reportlab)
            self._saved_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            total = len(self._saved_pages)
            for index, state in enumerate(self._saved_pages, start=1):
                self.__dict__.update(state)
                self._decorate(index, total)
                super().showPage()
            super().save()

        def _decorate(self, page: int, total: int) -> None:
            self.saveState()
            # faixa vermelha no topo
            self.setFillColor(RED)
            self.rect(0, PAGE_H - 2.6 * mm, PAGE_W, 2.6 * mm, stroke=0, fill=1)
            # cabeçalho corrido nas páginas seguintes
            if page > 1 and running_title:
                self.setFont(SANS_SEMIBOLD, 7.8)
                self.setFillColor(INK)
                self.drawString(MARGIN_X, PAGE_H - 9.5 * mm, "J&T Express")
                self.setFont(SANS, 7.8)
                self.setFillColor(MUTED)
                self.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 9.5 * mm, plain(running_title))
                self.setStrokeColor(LINE)
                self.setLineWidth(0.5)
                self.line(MARGIN_X, PAGE_H - 11.6 * mm, PAGE_W - MARGIN_X, PAGE_H - 11.6 * mm)
            # rodapé
            self.setStrokeColor(LINE_STRONG)
            self.setLineWidth(0.5)
            self.line(MARGIN_X, 14 * mm, PAGE_W - MARGIN_X, 14 * mm)
            self.setFont(SANS, 7.6)
            self.setFillColor(MUTED)
            self.drawString(MARGIN_X, 9.4 * mm, plain(footer_left))
            self.setFont(SANS_SEMIBOLD, 7.6)
            self.setFillColor(INK)
            self.drawRightString(PAGE_W - MARGIN_X, 9.4 * mm, f"Página {page} de {total}")
            self.restoreState()

    return JTCanvas


def build_document(
    story: list[Any],
    footer_left: str,
    running_title: str = "",
    title: str = "",
    top_margin: float = 17 * mm,
    bottom_margin: float = 20 * mm,
) -> BytesIO:
    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=title or running_title or "J&T Express",
        author="Portal de Insumos J&T Express",
    )
    frame = Frame(
        MARGIN_X, bottom_margin, CONTENT_W, PAGE_H - top_margin - bottom_margin,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="main",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])
    doc.build(story, canvasmaker=_canvas_class(footer_left, running_title))
    buffer.seek(0)
    return buffer


__all__ = [
    "Styles", "KeepTogether", "num", "build_document", "data_table", "header_block", "info_grid",
    "kpi_row", "markup", "note_box", "plain", "section_title", "signature_block", "spacer",
    "status_markup", "txt", "CONTENT_W", "SANS", "SANS_BOLD", "SANS_SEMIBOLD", "CJK",
]
