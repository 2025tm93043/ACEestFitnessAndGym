"""SQLite persistence layer (introduced in ACEest v2.0.1)."""
import os
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        age INTEGER,
        height REAL,
        weight REAL,
        program TEXT,
        calories INTEGER,
        target_weight REAL,
        target_adherence INTEGER,
        membership_status TEXT DEFAULT 'Active',
        membership_end TEXT
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
    """
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        date TEXT,
        workout_type TEXT,
        duration_min INTEGER,
        notes TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER,
        name TEXT,
        sets INTEGER,
        reps INTEGER,
        weight REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        date TEXT,
        weight REAL,
        waist REAL,
        bodyfat REAL
    )
    """,
]

# Columns added after a table's first release: {table: {column: ddl}}.
MIGRATIONS = {
    "clients": {
        "height": "REAL",
        "target_weight": "REAL",
        "target_adherence": "INTEGER",
        "membership_status": "TEXT DEFAULT 'Active'",
        "membership_end": "TEXT",
    },
}


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
    migrate_membership(conn)
    seed_admin(conn)
    conn.commit()
    conn.close()


def migrate_membership(conn):
    """3.2.4 renamed membership_expiry -> membership_end and added membership_status."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(clients)")}
    if "membership_expiry" in cols:
        conn.execute("UPDATE clients SET membership_end = membership_expiry "
                     "WHERE membership_end IS NULL AND membership_expiry IS NOT NULL")
    conn.execute("UPDATE clients SET membership_status = 'Active' "
                 "WHERE membership_status IS NULL")


def seed_admin(conn):
    """Create the default admin user (password from ACEEST_ADMIN_PASSWORD, default 'admin')."""
    password = os.environ.get("ACEEST_ADMIN_PASSWORD", "admin")
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", generate_password_hash(password), "Admin"))


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
