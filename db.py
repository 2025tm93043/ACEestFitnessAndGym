"""SQLite persistence layer (introduced in ACEest v2.0.1)."""
import sqlite3

from flask import current_app, g

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        age INTEGER,
        weight REAL,
        program TEXT,
        calories INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        week TEXT,
        adherence INTEGER
    )
    """,
]

# Columns added after a table's first release: {table: {column: ddl}}.
MIGRATIONS = {}


def ensure_columns(conn, table, columns):
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    for column, ddl in columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db(path):
    conn = sqlite3.connect(path)
    for statement in SCHEMA:
        conn.execute(statement)
    for table, columns in MIGRATIONS.items():
        ensure_columns(conn, table, columns)
    conn.commit()
    conn.close()


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app):
    init_db(app.config["DATABASE"])
    app.teardown_appcontext(close_db)
