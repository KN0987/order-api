import os
import sqlite3
from flask import current_app, g
from contextlib import contextmanager

def get_db():
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]
        conn = sqlite3.connect(db_path, isolation_level=None) 
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        db.executescript(f.read())
        
    
@contextmanager
def db_txn():
    """
    Explicit transaction context.
    Uses BEGIN IMMEDIATE to reduce race conditions on the idempotency key.
    """
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE;")
        yield db
        db.execute("COMMIT;")
    except Exception:
        db.execute("ROLLBACK;")
        raise
