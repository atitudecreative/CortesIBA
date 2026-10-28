"""SQLite com duas tabelas: cultos e clips. Uma conexão por operação."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS cultos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT NOT NULL,            -- 'youtube' ou 'upload'
    url        TEXT,
    titulo     TEXT,
    status     TEXT NOT NULL DEFAULT 'pendente',
    erro       TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clips (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    culto_id       INTEGER NOT NULL REFERENCES cultos(id),
    idx            INTEGER NOT NULL,
    inicio         REAL NOT NULL,
    fim            REAL NOT NULL,
    titulo         TEXT NOT NULL,
    gancho         TEXT NOT NULL,
    nota           REAL NOT NULL,
    motivo         TEXT NOT NULL,
    depende_contexto INTEGER NOT NULL DEFAULT 0,
    arquivo        TEXT
);
"""

# Status em ordem; o worker avança por eles.
STATUS = ["pendente", "baixando", "transcrevendo", "selecionando", "renderizando", "pronto"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)


def criar_culto(source: str, url: str | None = None) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO cultos (source, url, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (source, url, _now(), _now()),
        )
        return cur.lastrowid


def get_culto(culto_id: int) -> sqlite3.Row | None:
    with conn() as c:
        return c.execute("SELECT * FROM cultos WHERE id = ?", (culto_id,)).fetchone()


def listar_cultos(limit: int = 20) -> list[sqlite3.Row]:
    with conn() as c:
        return c.execute("SELECT * FROM cultos ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def cultos_inacabados() -> list[int]:
    with conn() as c:
        rows = c.execute("SELECT id FROM cultos WHERE status NOT IN ('pronto', 'erro')").fetchall()
        return [r["id"] for r in rows]


def set_status(culto_id: int, status: str, erro: str | None = None) -> None:
    with conn() as c:
        c.execute(
            "UPDATE cultos SET status = ?, erro = ?, updated_at = ? WHERE id = ?",
            (status, erro, _now(), culto_id),
        )


def set_titulo(culto_id: int, titulo: str) -> None:
    with conn() as c:
        c.execute("UPDATE cultos SET titulo = ? WHERE id = ?", (titulo, culto_id))


def salvar_clips(culto_id: int, clips: list[dict]) -> None:
    """Substitui os cortes do culto (a seleção pode ser refeita)."""
    with conn() as c:
        c.execute("DELETE FROM clips WHERE culto_id = ?", (culto_id,))
        c.executemany(
            """INSERT INTO clips (culto_id, idx, inicio, fim, titulo, gancho, nota, motivo, depende_contexto)
               VALUES (:culto_id, :idx, :inicio, :fim, :titulo, :gancho, :nota, :motivo, :depende_contexto)""",
            [{**clip, "culto_id": culto_id} for clip in clips],
        )


def set_clip_arquivo(clip_id: int, arquivo: str) -> None:
    with conn() as c:
        c.execute("UPDATE clips SET arquivo = ? WHERE id = ?", (arquivo, clip_id))


def listar_clips(culto_id: int) -> list[sqlite3.Row]:
    with conn() as c:
        return c.execute(
            "SELECT * FROM clips WHERE culto_id = ? ORDER BY nota DESC, idx", (culto_id,)
        ).fetchall()
