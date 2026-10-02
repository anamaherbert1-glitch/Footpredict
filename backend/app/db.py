import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured")


@contextmanager
def get_connection():
    with psycopg.connect(DATABASE_URL) as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
