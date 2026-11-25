import os
from dotenv import load_dotenv
import psycopg

load_dotenv("../.env")

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL not found")

tables = [
    "employees",
    "pods",
    "brands",
    "processes",
    "assignments",
    "operating_rules",
    "weekly_offs",
    "availabilities",
    "public_holidays",
    "constraints_config",
    "roster_entries",
]

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:

        for table in tables:
            print()
            print("=" * 60)
            print(f"TABLE: {table}")
            print("=" * 60)

            cur.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table,),
            )

            rows = cur.fetchall()

            if not rows:
                print("TABLE NOT FOUND")
                continue

            for row in rows:
                print(row)