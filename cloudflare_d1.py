import os
import re
import sqlite3
from collections.abc import Iterable
from typing import Any

import requests


class D1Error(RuntimeError):
    pass


class D1Row(dict):
    """SQLite Row-like object backed by a dict returned from Cloudflare D1."""

    def keys(self):  # keep same interface used by sqlite3.Row
        return super().keys()


class D1Cursor:
    def __init__(self, rows: list[dict[str, Any]] | None = None, lastrowid: int | None = None, changes: int | None = None):
        self._rows = [D1Row(row or {}) for row in (rows or [])]
        self.lastrowid = lastrowid
        self.rowcount = changes if isinstance(changes, int) else -1

    def fetchone(self) -> D1Row | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[D1Row]:
        return list(self._rows)


class D1Connection:
    """Tiny sqlite3-compatible adapter for Cloudflare D1 HTTP API.

    It implements only the methods used by this Flask app: execute, executescript,
    commit, rollback and context-manager methods. D1 persists data in Cloudflare,
    while local development can keep using sqlite3.
    """

    def __init__(self, account_id: str, database_id: str, api_token: str, timeout: int = 30):
        if not account_id or not database_id or not api_token:
            raise D1Error(
                "Cloudflare D1 não configurado. Defina CLOUDFLARE_ACCOUNT_ID, "
                "CLOUDFLARE_D1_DATABASE_ID e CLOUDFLARE_API_TOKEN."
            )
        self.account_id = account_id
        self.database_id = database_id
        self.api_token = api_token
        self.timeout = timeout
        self.endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"

    def __enter__(self) -> "D1Connection":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> D1Cursor:
        return self._query(sql, list(params or []))

    def executescript(self, script: str) -> D1Cursor:
        last_cursor = D1Cursor()
        for statement in split_sql_script(script):
            last_cursor = self.execute(statement)
        return last_cursor

    def _query(self, sql: str, params: list[Any] | None = None) -> D1Cursor:
        sql = sql.strip()
        if not sql:
            return D1Cursor()
        payload: dict[str, Any] = {"sql": sql}
        if params:
            payload["params"] = [normalize_param(value) for value in params]
        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise D1Error(f"Resposta inválida do Cloudflare D1: HTTP {response.status_code} - {response.text[:300]}") from exc
        if not response.ok or not data.get("success", False):
            raise D1Error(format_d1_error(data, response.status_code, sql))

        result_list = data.get("result") or []
        # Cloudflare returns a list, even for one query.
        result = result_list[-1] if isinstance(result_list, list) and result_list else {}
        rows = result.get("results") or []
        meta = result.get("meta") or {}
        lastrowid = meta.get("last_row_id")
        changes = meta.get("changes")
        return D1Cursor(rows=rows if isinstance(rows, list) else [], lastrowid=lastrowid if isinstance(lastrowid, int) else None, changes=changes if isinstance(changes, int) else None)


def normalize_param(value: Any) -> Any:
    if value is True:
        return 1
    if value is False:
        return 0
    return value


def format_d1_error(data: dict[str, Any], status_code: int, sql: str) -> str:
    errors = data.get("errors") or []
    if errors:
        messages = "; ".join(str(err.get("message", err)) for err in errors)
    else:
        messages = str(data)[:500]
    compact_sql = " ".join(sql.split())[:250]
    return f"Erro Cloudflare D1 HTTP {status_code}: {messages}. SQL: {compact_sql}"


def split_sql_script(script: str) -> list[str]:
    """Split SQL script safely enough for schema migrations.

    Uses sqlite3.complete_statement so semicolons inside strings do not break
    ordinary CREATE/ALTER/INSERT statements.
    """
    statements: list[str] = []
    buffer: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        current = "\n".join(buffer).strip()
        if sqlite3.complete_statement(current):
            stmt = current.rstrip(";\n ")
            if stmt:
                statements.append(stmt)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail.rstrip(";\n "))
    return statements


def cloudflare_d1_connect_from_env() -> D1Connection:
    return D1Connection(
        account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip(),
        database_id=os.getenv("CLOUDFLARE_D1_DATABASE_ID", "").strip(),
        api_token=os.getenv("CLOUDFLARE_API_TOKEN", "").strip(),
        timeout=int(os.getenv("CLOUDFLARE_D1_TIMEOUT", "30")),
    )
