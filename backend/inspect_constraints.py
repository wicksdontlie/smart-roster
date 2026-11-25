import os
from dotenv import load_dotenv
import psycopg

load_dotenv("../.env")

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL not found")

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:

        print("=" * 70)
        print("CHECK CONSTRAINTS ON constraints_config")
        print("=" * 70)

        cur.execute(
            """
            SELECT
                conname,
                pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'public.constraints_config'::regclass
            ORDER BY conname
            """
        )

        rows = cur.fetchall()

        for name, definition in rows:
            print()
            print(f"NAME: {name}")
            print(f"RULE: {definition}")