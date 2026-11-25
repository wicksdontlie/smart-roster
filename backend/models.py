import os
from datetime import date
from typing import Optional

import psycopg
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured.")


def get_connection():
    return psycopg.connect(
        DATABASE_URL,
        prepare_threshold=None,
    )

def create_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pods (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    lead_employee_id INTEGER NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS roster_entries (
                    id SERIAL PRIMARY KEY,
                    roster_date DATE NOT NULL,
                    employee_id INTEGER NOT NULL REFERENCES employees(id),
                    brand_id INTEGER NOT NULL REFERENCES brands(id),
                    process_id INTEGER NOT NULL REFERENCES processes(id),
                    assignment_type VARCHAR(20) NOT NULL
                        CHECK (
                            assignment_type IN ('PRIMARY', 'BACKUP')
                        ),
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    employee_code VARCHAR(50) NOT NULL UNIQUE,
                    name VARCHAR(150) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    pod_id INTEGER REFERENCES pods(id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS brands (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(150) NOT NULL UNIQUE,
                    active BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS processes (
                    id SERIAL PRIMARY KEY,
                    brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
                    name VARCHAR(150) NOT NULL,
                    UNIQUE(brand_id, name)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS assignments (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                    brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
                    process_id INTEGER NOT NULL REFERENCES processes(id) ON DELETE CASCADE,
                    assignment_type VARCHAR(20) NOT NULL
                        CHECK (assignment_type IN ('PRIMARY', 'BACKUP')),
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    UNIQUE(employee_id, brand_id, process_id, assignment_type)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS operating_rules (
                    id SERIAL PRIMARY KEY,
                    brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
                    process_id INTEGER NULL REFERENCES processes(id) ON DELETE CASCADE,
                    rule_name VARCHAR(150) NOT NULL,
                    operating_calendar VARCHAR(100) NOT NULL,
                    minimum_staff_per_day INTEGER NOT NULL DEFAULT 1,
                    active BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS availabilities (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                    availability_type VARCHAR(30) NOT NULL
                        CHECK (
                            availability_type IN (
                                'LEAVE',
                                'COMP_OFF',
                                'UNAVAILABLE'
                            )
                        ),
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    reason TEXT
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS weekly_offs (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),
                    UNIQUE(employee_id, weekday)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS public_holidays (
                    id SERIAL PRIMARY KEY,
                    holiday_date DATE NOT NULL UNIQUE,
                    name VARCHAR(150) NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS constraints_config (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    constraint_type VARCHAR(30) NOT NULL
                        CHECK (
                            constraint_type IN (
                                'MANDATORY',
                                'PREFERENCE'
                            )
                        ),
                    description TEXT,
                    active BOOLEAN NOT NULL DEFAULT TRUE
                );
            """)

            conn.commit()


# -------------------------
# Employee CRUD
# -------------------------

def list_employees():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    e.id,
                    e.employee_code,
                    e.name,
                    e.email,
                    e.active,
                    e.pod_id,
                    p.name AS pod_name
                FROM employees e
                LEFT JOIN pods p ON p.id = e.pod_id
                ORDER BY e.id;
            """)

            columns = [desc.name for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def get_employee(employee_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    e.id,
                    e.employee_code,
                    e.name,
                    e.email,
                    e.active,
                    e.pod_id,
                    p.name AS pod_name
                FROM employees e
                LEFT JOIN pods p ON p.id = e.pod_id
                WHERE e.id = %s;
            """, (employee_id,))

            row = cur.fetchone()

            if not row:
                return None

            columns = [desc.name for desc in cur.description]
            return dict(zip(columns, row))


def create_employee(
    employee_code: str,
    name: str,
    email: str,
    pod_id: Optional[int] = None,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO employees (
                    employee_code,
                    name,
                    email,
                    pod_id
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (employee_code, name, email, pod_id))

            employee_id = cur.fetchone()[0]
            conn.commit()

            return get_employee(employee_id)


def update_employee(
    employee_id: int,
    name: str,
    email: str,
    active: bool,
    pod_id: Optional[int],
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE employees
                SET
                    name = %s,
                    email = %s,
                    active = %s,
                    pod_id = %s
                WHERE id = %s;
            """, (
                name,
                email,
                active,
                pod_id,
                employee_id,
            ))

            if cur.rowcount == 0:
                return None

            conn.commit()

            return get_employee(employee_id)


def delete_employee(employee_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM employees
                WHERE id = %s;
            """, (employee_id,))

            deleted = cur.rowcount > 0
            conn.commit()

            return deleted


# -------------------------
# Brand CRUD
# -------------------------

def list_brands():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    name,
                    active
                FROM brands
                ORDER BY id;
            """)

            columns = [desc.name for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def create_brand(name: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO brands (name)
                VALUES (%s)
                RETURNING id, name, active;
            """, (name,))

            row = cur.fetchone()
            conn.commit()

            columns = [desc.name for desc in cur.description]
            return dict(zip(columns, row))


# -------------------------
# Process CRUD
# -------------------------

def list_processes(brand_id: Optional[int] = None):
    with get_connection() as conn:
        with conn.cursor() as cur:

            if brand_id:
                cur.execute("""
                    SELECT
                        p.id,
                        p.name,
                        p.brand_id,
                        b.name AS brand_name
                    FROM processes p
                    JOIN brands b ON b.id = p.brand_id
                    WHERE p.brand_id = %s
                    ORDER BY p.id;
                """, (brand_id,))
            else:
                cur.execute("""
                    SELECT
                        p.id,
                        p.name,
                        p.brand_id,
                        b.name AS brand_name
                    FROM processes p
                    JOIN brands b ON b.id = p.brand_id
                    ORDER BY p.id;
                """)

            columns = [desc.name for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def create_process(brand_id: int, name: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO processes (brand_id, name)
                VALUES (%s, %s)
                RETURNING id, brand_id, name;
            """, (brand_id, name))

            row = cur.fetchone()
            conn.commit()

            columns = [desc.name for desc in cur.description]
            return dict(zip(columns, row))