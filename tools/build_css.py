#!/usr/bin/env python3
"""Gera static/css/jt-ui.css a partir de static/css/src/jt-ui.src.css.

Por que existe: o styles.css antigo tem ~4.800 declarações !important. Para a nova
camada visual vencer sem briga de especificidade, o build:
  1. isola o styles.css antigo em  @layer legacy  (via @import ... layer(legacy));
  2. coloca o CSS novo em  @layer jt  (declarada antes) e marca cada declaração como
     !important. Em camadas, !important de camada anterior vence !important de
     camada posterior, então o novo estilo sempre ganha onde ele define algo.

@font-face e @keyframes ficam fora da camada (não aceitam !important).
Uso:  python tools/build_css.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "static" / "css" / "src" / "jt-ui.src.css"
OUT = ROOT / "static" / "css" / "jt-ui.css"
LEGACY_IMPORT = '@import url("styles.css?v=227") layer(legacy);'

VERBATIM_AT = ("@font-face", "@keyframes", "@-webkit-keyframes")
NESTING_AT = ("@media", "@supports", "@container")


def strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def match_brace(text: str, i: int) -> int:
    """i aponta para '{'. Retorna índice do '}' correspondente."""
    depth, quote = 0, None
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("chaves desbalanceadas")


def split_decls(body: str):
    parts, buf, depth, quote = [], [], 0, None
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if "".join(buf).strip():
        parts.append("".join(buf))
    return parts


def important(body: str) -> str:
    out = []
    for decl in split_decls(body):
        d = decl.strip()
        if not d:
            continue
        if ":" not in d:
            out.append(d)
            continue
        if "!important" not in d:
            d += " !important"
        out.append(d)
    return "; ".join(out) + ";"


def transform(css: str) -> str:
    out, i = [], 0
    while i < len(css):
        j = css.find("{", i)
        if j == -1:
            out.append(css[i:])
            break
        prelude = css[i:j].strip()
        k = match_brace(css, j)
        inner = css[j + 1 : k]
        if prelude.startswith(VERBATIM_AT):
            out.append(f"{prelude} {{{inner}}}")  # tratado fora; ver split abaixo
        elif prelude.startswith(NESTING_AT):
            out.append(f"{prelude} {{\n{transform(inner)}\n}}")
        else:
            out.append(f"{prelude} {{ {important(inner)} }}")
        i = k + 1
    return "\n".join(out)


def main() -> int:
    css = strip_comments(SRC.read_text(encoding="utf-8"))
    # separa blocos que não podem ir para a camada
    verbatim, rest, i = [], [], 0
    while i < len(css):
        j = css.find("{", i)
        if j == -1:
            rest.append(css[i:])
            break
        prelude = css[i:j].strip()
        k = match_brace(css, j)
        block = css[i : k + 1].strip()
        (verbatim if prelude.startswith(VERBATIM_AT) else rest).append(block)
        i = k + 1
    layered = transform("\n".join(rest))
    header = (
        "/* ARQUIVO GERADO por tools/build_css.py a partir de static/css/src/jt-ui.src.css — não edite aqui. */\n"
        "@layer jt, legacy;\n"
        f"{LEGACY_IMPORT}\n"
    )
    OUT.write_text(header + "\n".join(verbatim) + "\n@layer jt {\n" + layered + "\n}\n", encoding="utf-8")
    print(f"ok: {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
