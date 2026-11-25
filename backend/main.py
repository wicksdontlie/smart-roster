from typing import Optional
from datetime import date

from agents import (
    get_roster_analysis,
    analyze_workload,
    find_cross_skilled_employees,
    find_replacement_candidates,
    run_agent,
)

from solver import generate_roster
from validator import validate_roster

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from fastapi.middleware.cors import CORSMiddleware

from models import (
    create_tables,
    get_connection,
    list_employees,
    get_employee,
    create_employee,
    update_employee,
    delete_employee,
    list_brands,
    create_brand,
    list_processes,
    create_process,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Smart Roster Management System",
    version="0.2.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://YOUR-VERCEL-DOMAIN.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class AgentChatRequest(BaseModel):
    message: str
    year: int
    month: int


class EmployeeCreate(BaseModel):
    employee_code: str
    name: str
    email: EmailStr
    pod_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    name: str
    email: EmailStr
    active: bool = True
    pod_id: Optional[int] = None


class BrandCreate(BaseModel):
    name: str


class ProcessCreate(BaseModel):
    brand_id: int
    name: str


class RosterReassignmentRequest(BaseModel):
    roster_date: date
    old_employee_id: int
    new_employee_id: int
    brand_id: int
    process_id: int
    assignment_type: str = "PRIMARY"


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    create_tables()


# ============================================================
# ROOT / HEALTH
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Smart Roster Management System API",
        "phase": 2,
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": "postgresql",
    }


# ============================================================
# WEEKEND OFF ENFORCEMENT
# ============================================================

def ensure_weekends_are_off():
    """
    Ensure every active employee has Saturday and Sunday
    configured as weekly offs.

    Python weekday values:
        Monday    = 0
        Tuesday   = 1
        Wednesday = 2
        Thursday  = 3
        Friday    = 4
        Saturday  = 5
        Sunday    = 6

    This is intentionally done before roster generation so
    solver.py will never create Saturday/Sunday assignments
    for active employees.
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            # Get all active employees.
            cur.execute("""
                SELECT id
                FROM employees
                WHERE active = TRUE
                ORDER BY id;
            """)

            employee_ids = [
                row[0]
                for row in cur.fetchall()
            ]

            # Add Saturday and Sunday only if missing.
            for employee_id in employee_ids:

                cur.execute("""
                    INSERT INTO weekly_offs (
                        employee_id,
                        weekday
                    )
                    SELECT
                        %s,
                        %s
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM weekly_offs
                        WHERE employee_id = %s
                          AND weekday = %s
                    );
                """, (
                    employee_id,
                    5,
                    employee_id,
                    5,
                ))

                cur.execute("""
                    INSERT INTO weekly_offs (
                        employee_id,
                        weekday
                    )
                    SELECT
                        %s,
                        %s
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM weekly_offs
                        WHERE employee_id = %s
                          AND weekday = %s
                    );
                """, (
                    employee_id,
                    6,
                    employee_id,
                    6,
                ))

        conn.commit()


# ============================================================
# EMPLOYEE API
# ============================================================

@app.get("/employees")
def get_employees():
    return list_employees()


@app.get("/employees/{employee_id}")
def get_employee_by_id(employee_id: int):

    employee = get_employee(employee_id)

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return employee


@app.post("/employees", status_code=201)
def add_employee(employee: EmployeeCreate):

    try:

        return create_employee(
            employee_code=employee.employee_code,
            name=employee.name,
            email=employee.email,
            pod_id=employee.pod_id,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.put("/employees/{employee_id}")
def edit_employee(
    employee_id: int,
    employee: EmployeeUpdate,
):

    updated = update_employee(
        employee_id=employee_id,
        name=employee.name,
        email=employee.email,
        active=employee.active,
        pod_id=employee.pod_id,
    )

    if not updated:

        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return updated


@app.delete("/employees/{employee_id}")
def remove_employee(employee_id: int):

    deleted = delete_employee(employee_id)

    if not deleted:

        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    return {
        "message": "Employee deleted successfully",
    }


# ============================================================
# BRAND API
# ============================================================

@app.get("/brands")
def get_brands():
    return list_brands()


@app.post("/brands", status_code=201)
def add_brand(brand: BrandCreate):

    try:

        return create_brand(
            brand.name
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ============================================================
# PROCESS API
# ============================================================

@app.get("/processes")
def get_processes(
    brand_id: Optional[int] = None,
):
    return list_processes(brand_id)


@app.post("/processes", status_code=201)
def add_process(process: ProcessCreate):

    try:

        return create_process(
            brand_id=process.brand_id,
            name=process.name,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ============================================================
# ROSTER GENERATION
# ============================================================

@app.post("/rosters/generate")
def generate_monthly_roster(
    year: int,
    month: int,
):

    if month < 1 or month > 12:

        raise HTTPException(
            status_code=400,
            detail="Month must be between 1 and 12.",
        )

    try:

        # --------------------------------------------------------
        # IMPORTANT:
        # Make Saturday and Sunday weekly offs before
        # calling the OR-Tools solver.
        # --------------------------------------------------------

        ensure_weekends_are_off()

        # --------------------------------------------------------
        # Generate roster using solver.py
        # --------------------------------------------------------

        result = generate_roster(
            year=year,
            month=month,
        )

        # --------------------------------------------------------
        # Handle infeasible roster
        # --------------------------------------------------------

        if result.get("status") == "infeasible":

            raise HTTPException(
                status_code=422,
                detail=result,
            )

        return result

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Roster generation failed: {exc}",
        )


# ============================================================
# GET ROSTER
# ============================================================

@app.get("/rosters")
def get_roster(
    year: int,
    month: int,
):

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    r.id,
                    r.roster_date,

                    r.employee_id,
                    e.name AS employee_name,
                    e.pod_id,

                    r.brand_id,
                    b.name AS brand_name,

                    r.process_id,
                    p.name AS process_name,

                    r.assignment_type

                FROM roster_entries r

                JOIN employees e
                    ON e.id = r.employee_id

                JOIN brands b
                    ON b.id = r.brand_id

                JOIN processes p
                    ON p.id = r.process_id

                WHERE EXTRACT(
                    YEAR FROM r.roster_date
                ) = %s

                  AND EXTRACT(
                    MONTH FROM r.roster_date
                  ) = %s

                ORDER BY
                    r.roster_date,
                    e.name;
            """, (
                year,
                month,
            ))

            columns = [
                desc.name
                for desc in cur.description
            ]

            return [
                dict(zip(columns, row))
                for row in cur.fetchall()
            ]


# ============================================================
# MANUAL ROSTER REASSIGNMENT
# ============================================================

@app.put("/rosters/reassign")
def reassign_roster(
    request: RosterReassignmentRequest,
):

    # ----------------------------------------------------------
    # Validate assignment type
    # ----------------------------------------------------------

    if request.assignment_type not in {
        "PRIMARY",
        "BACKUP",
    }:

        raise HTTPException(
            status_code=400,
            detail=(
                "assignment_type must be "
                "PRIMARY or BACKUP."
            ),
        )

    try:

        with get_connection() as conn:

            with conn.cursor() as cur:

                # ==================================================
                # 1. FIND EXISTING ROSTER ENTRY
                # ==================================================

                cur.execute(
                    """
                    SELECT id
                    FROM roster_entries

                    WHERE roster_date = %s
                      AND employee_id = %s
                      AND brand_id = %s
                      AND process_id = %s

                    LIMIT 1
                    """,
                    (
                        request.roster_date,
                        request.old_employee_id,
                        request.brand_id,
                        request.process_id,
                    ),
                )

                existing_entry = cur.fetchone()

                if not existing_entry:

                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "Original roster entry "
                            "not found."
                        ),
                    )

                roster_entry_id = existing_entry[0]

                # ==================================================
                # 2. SATURDAY / SUNDAY HARD BLOCK
                # ==================================================

                weekday = request.roster_date.weekday()

                if weekday == 5:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Saturday is a weekly off. "
                            "Employees cannot be assigned "
                            "to roster entries on Saturday."
                        ),
                    )

                if weekday == 6:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Sunday is a weekly off. "
                            "Employees cannot be assigned "
                            "to roster entries on Sunday."
                        ),
                    )

                # ==================================================
                # 3. CHECK REPLACEMENT EMPLOYEE
                # ==================================================

                cur.execute(
                    """
                    SELECT
                        id,
                        name,
                        active

                    FROM employees

                    WHERE id = %s
                    """,
                    (
                        request.new_employee_id,
                    ),
                )

                employee = cur.fetchone()

                if not employee:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Replacement employee "
                            "not found."
                        ),
                    )

                (
                    new_employee_id,
                    new_employee_name,
                    active,
                ) = employee

                if not active:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{new_employee_name} "
                            "is inactive."
                        ),
                    )

                # ==================================================
                # 4. CHECK ASSIGNMENT ELIGIBILITY
                # ==================================================

                cur.execute(
                    """
                    SELECT 1
                    FROM assignments

                    WHERE employee_id = %s
                      AND brand_id = %s
                      AND process_id = %s
                      AND active = TRUE

                    LIMIT 1
                    """,
                    (
                        request.new_employee_id,
                        request.brand_id,
                        request.process_id,
                    ),
                )

                if not cur.fetchone():

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{new_employee_name} "
                            "is not eligible for this "
                            "brand/process."
                        ),
                    )
                # ====================================================
                # 4. Global weekend check
                # ====================================================

                if request.roster_date.weekday() in (5, 6):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Roster assignments are not allowed on "
                            "Saturday or Sunday."
                        ),
                    )
                # ==================================================
                # 5. CHECK WEEKLY OFF
                # ==================================================

                cur.execute(
                    """
                    SELECT 1
                    FROM weekly_offs

                    WHERE employee_id = %s
                      AND weekday = %s

                    LIMIT 1
                    """,
                    (
                        request.new_employee_id,
                        weekday,
                    ),
                )

                if cur.fetchone():

                    day_name = (
                        "Saturday"
                        if weekday == 5
                        else "Sunday"
                        if weekday == 6
                        else request.roster_date.strftime("%A")
                    )

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{new_employee_name} "
                            f"has a weekly off on "
                            f"{day_name}."
                        ),
                    )

                # ==================================================
                # 6. CHECK AVAILABILITY
                # ==================================================

                cur.execute(
                    """
                    SELECT
                        availability_type,
                        reason

                    FROM availabilities

                    WHERE employee_id = %s
                      AND start_date <= %s
                      AND end_date >= %s
                    """,
                    (
                        request.new_employee_id,
                        request.roster_date,
                        request.roster_date,
                    ),
                )

                availability_rows = cur.fetchall()

                blocked_types = {
                    "LEAVE",
                    "UNAVAILABLE",
                    "COMP_OFF",
                }

                for (
                    availability_type,
                    reason,
                ) in availability_rows:

                    if (
                        str(
                            availability_type
                        ).upper()
                        in blocked_types
                    ):

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"{new_employee_name} "
                                f"is {availability_type} "
                                f"on {request.roster_date}."
                            ),
                        )

                # ==================================================
                # 7. CHECK DAILY CAPACITY
                # ==================================================

                cur.execute(
                    """
                    SELECT COUNT(*)

                    FROM roster_entries

                    WHERE roster_date = %s
                      AND employee_id = %s
                      AND id <> %s
                    """,
                    (
                        request.roster_date,
                        request.new_employee_id,
                        roster_entry_id,
                    ),
                )

                daily_assignments = cur.fetchone()[0]

                DAILY_PROCESS_CAPACITY = 4

                if (
                    daily_assignments
                    >= DAILY_PROCESS_CAPACITY
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{new_employee_name} "
                            f"already has "
                            f"{daily_assignments} "
                            f"assignments on "
                            f"{request.roster_date}. "
                            "Daily capacity is 4."
                        ),
                    )

                # ==================================================
                # 8. PREVENT DUPLICATE ASSIGNMENT
                # ==================================================

                cur.execute(
                    """
                    SELECT 1

                    FROM roster_entries

                    WHERE roster_date = %s
                      AND employee_id = %s
                      AND brand_id = %s
                      AND process_id = %s
                      AND id <> %s

                    LIMIT 1
                    """,
                    (
                        request.roster_date,
                        request.new_employee_id,
                        request.brand_id,
                        request.process_id,
                        roster_entry_id,
                    ),
                )

                if cur.fetchone():

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{new_employee_name} "
                            "is already assigned "
                            "to this process on "
                            "this date."
                        ),
                    )

                # ==================================================
                # 9. APPLY TEMPORARY CHANGE
                # ==================================================

                cur.execute(
                    """
                    UPDATE roster_entries

                    SET employee_id = %s,
                        assignment_type = %s

                    WHERE id = %s
                    """,
                    (
                        request.new_employee_id,
                        request.assignment_type,
                        roster_entry_id,
                    ),
                )

                # ==================================================
                # 10. VALIDATE WHOLE MONTH
                # ==================================================

                validation = validate_roster(
                    year=request.roster_date.year,
                    month=request.roster_date.month,
                    conn=conn,
                )

                # ==================================================
                # 11. ROLLBACK IF INVALID
                # ==================================================

                if validation["status"] != "valid":

                    conn.rollback()

                    return {
                        "status": "rejected",
                        "message": (
                            "Roster change rejected "
                            "because the resulting "
                            "roster is invalid."
                        ),
                        "validation": validation,
                    }

                # ==================================================
                # 12. COMMIT
                # ==================================================

                conn.commit()

                return {
                    "status": "success",
                    "message": (
                        "Roster reassignment "
                        "completed successfully."
                    ),
                    "roster_entry_id": (
                        roster_entry_id
                    ),
                    "new_employee_id": (
                        request.new_employee_id
                    ),
                    "new_employee_name": (
                        new_employee_name
                    ),
                    "validation": validation,
                }

    except HTTPException:

        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Roster reassignment failed: "
                f"{exc}"
            ),
        )


# ============================================================
# ROSTER VALIDATION
# ============================================================

@app.get("/rosters/validate")
def validate_monthly_roster(
    year: int,
    month: int,
):

    if month < 1 or month > 12:

        raise HTTPException(
            status_code=400,
            detail=(
                "Month must be between 1 and 12."
            ),
        )

    try:

        return validate_roster(
            year=year,
            month=month,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Roster validation failed: "
                f"{exc}"
            ),
        )


# ============================================================
# AGENT - ROSTER ANALYSIS
# ============================================================

@app.get("/agent/roster-analysis")
def agent_roster_analysis(
    year: int,
    month: int,
):

    try:

        return get_roster_analysis(
            year=year,
            month=month,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Agent analysis failed: "
                f"{exc}"
            ),
        )


# ============================================================
# AGENT - WORKLOAD
# ============================================================

@app.get("/agent/workload")
def agent_workload(
    year: int,
    month: int,
):

    try:

        return analyze_workload(
            year=year,
            month=month,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Workload analysis failed: "
                f"{exc}"
            ),
        )


# ============================================================
# AGENT - CROSS SKILLED
# ============================================================

@app.get("/agent/cross-skilled")
def agent_cross_skilled():

    try:

        return find_cross_skilled_employees()

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Cross-skill analysis failed: "
                f"{exc}"
            ),
        )


# ============================================================
# AGENT - REPLACEMENT CANDIDATES
# ============================================================

@app.get("/agent/replacement-candidates")
def agent_replacement_candidates(
    employee_id: int,
    roster_date: str,
    process_id: int,
):

    try:

        return find_replacement_candidates(
            employee_id=employee_id,
            roster_date=roster_date,
            process_id=process_id,
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid roster date. "
                "Use YYYY-MM-DD."
            ),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Replacement analysis failed: "
                f"{exc}"
            ),
        )


# ============================================================
# AGENT CHAT
# ============================================================

@app.post("/agent/chat")
def agent_chat(
    request: AgentChatRequest,
):

    if request.month < 1 or request.month > 12:

        raise HTTPException(
            status_code=400,
            detail=(
                "Month must be between 1 and 12."
            ),
        )

    try:

        response = run_agent(
            user_message=request.message,
            year=request.year,
            month=request.month,
        )

        return {
            "message": response,
            "year": request.year,
            "month": request.month,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Agent request failed: "
                f"{exc}"
            ),
        )