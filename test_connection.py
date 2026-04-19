import os
import sys

import chromadb
import psycopg2
from dotenv import load_dotenv

load_dotenv()

has_error = False

try:
    chromadb.Client()
    print("ChromaDB OK")
except Exception as exc:  # pragma: no cover
    has_error = True
    print(f"ChromaDB FAIL: {exc}")

try:
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )
    print("PostgreSQL OK")
    conn.close()
except Exception as exc:  # pragma: no cover
    has_error = True
    print(f"PostgreSQL FAIL: {exc}")

sys.exit(1 if has_error else 0)
