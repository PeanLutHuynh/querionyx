import os
import sys

import chromadb
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv(override=True)

has_error = False


def _connect_pg(database_name: str):
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=database_name,
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )

try:
    chromadb.Client()
    print("ChromaDB OK")
except Exception as exc:  # pragma: no cover
    has_error = True
    print(f"ChromaDB FAIL: {exc}")

try:
    target_db = os.getenv("PG_DB", "northwind")

    try:
        conn = _connect_pg(target_db)
    except psycopg2.OperationalError as exc:
        error_message = str(exc)
        if f'database "{target_db}" does not exist' not in error_message:
            raise

        admin_conn = _connect_pg("postgres")
        admin_conn.autocommit = True
        with admin_conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(target_db)))
        admin_conn.close()

        conn = _connect_pg(target_db)

    print("PostgreSQL OK")
    conn.close()
except Exception as exc:  # pragma: no cover
    has_error = True
    print(f"PostgreSQL FAIL: {exc}")

sys.exit(1 if has_error else 0)
