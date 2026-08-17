import os
from sqlcipher3 import dbapi2 as sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arnob_bank.db")

DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_conn():
    conn = sqlite3.connect(DB_PATH)

    if DB_PASSWORD:
        conn.execute(
            "PRAGMA key = ?",
            (DB_PASSWORD,)
        )

    conn.execute("PRAGMA foreign_keys = ON")

    return conn