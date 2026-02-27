# src/db.py

import sqlite3
from pathlib import Path
from datetime import datetime

# Caminho do banco
DB_PATH = Path("data/prices.db")


def get_conn() -> sqlite3.Connection:
    """
    Garante que a pasta exista e retorna conexão com SQLite.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """
    Cria a tabela se não existir e faz migração simples
    para adicionar a coluna image_url caso o banco seja antigo.
    """
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            site TEXT NOT NULL,
            url TEXT NOT NULL,
            title TEXT,
            seller TEXT,
            price REAL,
            shipping REAL,
            available INTEGER,
            image_url TEXT,
            raw TEXT
        );
        """)

        # Migração para bancos antigos (se não tiver image_url)
        try:
            conn.execute("ALTER TABLE price_history ADD COLUMN image_url TEXT;")
        except Exception:
            pass

        conn.commit()


def insert_row(
    site: str,
    url: str,
    title: str | None,
    seller: str | None,
    price: float | None,
    shipping: float | None,
    available: bool,
    image_url: str | None,
    raw: str | None,
) -> None:
    """
    Insere uma nova linha no histórico de preços.
    """
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO price_history
            (ts, site, url, title, seller, price, shipping, available, image_url, raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                site,
                url,
                title,
                seller,
                price,
                shipping,
                1 if available else 0,
                image_url,
                raw,
            ),
        )
        conn.commit()