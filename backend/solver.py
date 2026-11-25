from calendar import monthrange
from datetime import date, timedelta

import psycopg
from ortools.sat.python import cp_model

from models import DATABASE_URL


# ============================================================
# CONFIGURATION
# ============================================================

# Maximum number of process assignments an employee can receive
# on a single day.
#
# This is a scheduling capacity, NOT working hours.
DAILY_PROCESS_CAPACITY = 4

# CP-SAT time limit.
SOLVER_TIME_LIMIT_SECONDS = 60


# ============================================================
# OPERATING CALENDAR
# ============================================================

def is_operating_day(
    roster_date: date,
    operating_calendar: str,
    public_holidays: set[date],
) -> bool:
    """
    Determine whether a process operates on a given date.

    Smart Roster policy:
    - Saturday and Sunday are always employee days off.
    - Public holidays are respected according to the process calendar.
    - Weekdays are available for roster generation.

    Supported calendars:
    - 365_days
    - daily_except_public_holidays
    - sundays_public_holidays_off
    - weekdays_only
    """

    # ============================================================
    # GLOBAL EMPLOYEE WEEKEND POLICY
    # ============================================================
    # Saturday = 5
    # Sunday   = 6
    #
    # No roster assignment should ever be generated
    # on Saturday or Sunday.
    #
    if roster_date.weekday() in (5, 6):
        return False

    calendar_name = (
        operating_calendar or "365_days"
    ).strip().lower()

    # Every weekday is an operating day.
    if calendar_name == "365_days":
        return True

    # Weekdays except public holidays.
    if calendar_name == "daily_except_public_holidays":
        return roster_date not in public_holidays

    # Monday-Friday except public holidays.
    if calendar_name == "sundays_public_holidays_off":
        return roster_date not in public_holidays

    # Monday-Friday only.
    if calendar_name == "weekdays_only":
        return roster_date.weekday() < 5

    # Unknown calendar:
    # Keep the weekday available rather than silently
    # removing coverage.
    return True


# ============================================================
# ROSTER GENERATION
# ============================================================

def generate_roster(year: int, month: int):

    # --------------------------------------------------------
    # Validate month
    # --------------------------------------------------------

    if month < 1 or month > 12:
        raise ValueError(
            "Month must be between 1 and 12."
        )

    first_day = date(year, month, 1)

    last_day = date(
        year,
        month,
        monthrange(year, month)[1],
    )

    days_in_month = last_day.day

    # --------------------------------------------------------
    # Database connection
    # --------------------------------------------------------

    with psycopg.connect(
        DATABASE_URL,
        prepare_threshold=None,
    ) as conn:

        with conn.cursor() as cur:

            # =================================================
            # 1. ACTIVE EMPLOYEES
            # =================================================

            cur.execute(
                """
                SELECT
                    id
                FROM employees
                WHERE active = TRUE
                ORDER BY id;
                """
            )

            employees = [
                row[0]
                for row in cur.fetchall()
            ]

            if not employees:
                raise ValueError(
                    "No active employees found."
                )

            # =================================================
            # 2. ACTIVE EMPLOYEE ASSIGNMENTS
            # =================================================

            cur.execute(
                """
                SELECT
                    employee_id,
                    brand_id,
                    process_id,
                    assignment_type
                FROM assignments
                WHERE active = TRUE
                ORDER BY employee_id, brand_id, process_id;
                """
            )

            assignments = cur.fetchall()

            if not assignments:
                raise ValueError(
                    "No active assignments found."
                )

            # =================================================
            # 3. PROCESSES + OPERATING RULES
            # =================================================
            #
            # Rule priority:
            #
            # 1. Process-specific rule
            # 2. Brand-level rule
            # 3. Default
            #
            # This is important because operating_rules.process_id
            # is nullable in your database.
            # =================================================

            cur.execute(
                """
                SELECT
                    p.id,
                    p.brand_id,

                    COALESCE(
                        (
                            SELECT
                                r1.minimum_staff_per_day
                            FROM operating_rules r1
                            WHERE r1.active = TRUE
                              AND r1.process_id = p.id
                            ORDER BY r1.id DESC
                            LIMIT 1
                        ),
                        (
                            SELECT
                                r2.minimum_staff_per_day
                            FROM operating_rules r2
                            WHERE r2.active = TRUE
                              AND r2.brand_id = p.brand_id
                              AND r2.process_id IS NULL
                            ORDER BY r2.id DESC
                            LIMIT 1
                        ),
                        1
                    ) AS minimum_staff,

                    COALESCE(
                        (
                            SELECT
                                r1.operating_calendar
                            FROM operating_rules r1
                            WHERE r1.active = TRUE
                              AND r1.process_id = p.id
                            ORDER BY r1.id DESC
                            LIMIT 1
                        ),
                        (
                            SELECT
                                r2.operating_calendar
                            FROM operating_rules r2
                            WHERE r2.active = TRUE
                              AND r2.brand_id = p.brand_id
                              AND r2.process_id IS NULL
                            ORDER BY r2.id DESC
                            LIMIT 1
                        ),
                        '365_days'
                    ) AS operating_calendar

                FROM processes p
                ORDER BY p.id;
                """
            )

            processes = cur.fetchall()

            if not processes:
                raise ValueError(
                    "No processes found."
                )

            # =================================================
            # 4. WEEKLY OFFS
            # =================================================

            cur.execute(
                """
                SELECT
                    employee_id,
                    weekday
                FROM weekly_offs
                ORDER BY employee_id, weekday;
                """
            )

            weekly_offs = {}

            for employee_id, weekday in cur.fetchall():

                weekly_offs.setdefault(
                    employee_id,
                    set(),
                ).add(weekday)

            # =================================================
            # 5. EMPLOYEE AVAILABILITY
            # =================================================

            cur.execute(
                """
                SELECT
                    employee_id,
                    availability_type,
                    start_date,
                    end_date
                FROM availabilities
                WHERE availability_type IN (
                    'LEAVE',
                    'UNAVAILABLE',
                    'COMP_OFF'
                )
                ORDER BY employee_id, start_date;
                """
            )

            unavailable_dates = {}

            for (
                employee_id,
                availability_type,
                start_date,
                end_date,
            ) in cur.fetchall():

                current_date = max(
                    start_date,
                    first_day,
                )

                effective_end_date = min(
                    end_date,
                    last_day,
                )

                while (
                    current_date
                    <= effective_end_date
                ):

                    unavailable_dates.setdefault(
                        employee_id,
                        set(),
                    ).add(current_date)

                    current_date += timedelta(
                        days=1
                    )

            # =================================================
            # 6. PUBLIC HOLIDAYS
            # =================================================

            cur.execute(
                """
                SELECT
                    holiday_date
                FROM public_holidays
                WHERE holiday_date >= %s
                  AND holiday_date <= %s;
                """,
                (
                    first_day,
                    last_day,
                ),
            )

            public_holidays = {
                row[0]
                for row in cur.fetchall()
            }

            # =================================================
            # 7. BUILD ELIGIBILITY LOOKUP
            # =================================================
            #
            # eligible[(brand_id, process_id)]
            #     = set(employee_ids)
            #
            # A set prevents duplicate assignment rows from
            # creating duplicate solver variables.
            # =================================================

            eligible = {}

            # Also store assignment type by employee/brand/process.
            assignment_types = {}

            for (
                employee_id,
                brand_id,
                process_id,
                assignment_type,
            ) in assignments:

                process_key = (
                    brand_id,
                    process_id,
                )

                eligible.setdefault(
                    process_key,
                    set(),
                ).add(employee_id)

                assignment_key = (
                    employee_id,
                    brand_id,
                    process_id,
                )

                existing_type = assignment_types.get(
                    assignment_key
                )

                # If an employee somehow has both PRIMARY
                # and BACKUP rows for the same assignment,
                # PRIMARY wins.
                if (
                    existing_type != "PRIMARY"
                    and str(assignment_type).upper()
                    == "PRIMARY"
                ):
                    assignment_types[
                        assignment_key
                    ] = "PRIMARY"
                else:
                    assignment_types.setdefault(
                        assignment_key,
                        str(
                            assignment_type
                        ).upper(),
                    )

            # =================================================
            # 8. CP-SAT MODEL
            # =================================================

            model = cp_model.CpModel()

            variables = {}

            static_conflicts = []

            # =================================================
            # 9. CREATE DECISION VARIABLES
            # =================================================

            for (
                process_id,
                brand_id,
                minimum_staff,
                operating_calendar,
            ) in processes:

                process_key = (
                    brand_id,
                    process_id,
                )

                candidates = sorted(
                    eligible.get(
                        process_key,
                        set(),
                    )
                )

                # No employee is assigned to this process.
                if not candidates:
                    continue

                for day_number in range(
                    1,
                    days_in_month + 1,
                ):

                    roster_date = date(
                        year,
                        month,
                        day_number,
                    )

                    # Process is not operating today.
                    if not is_operating_day(
                        roster_date,
                        operating_calendar,
                        public_holidays,
                    ):
                        continue

                    for employee_id in candidates:

                        # -------------------------------------
                        # Employee unavailable
                        # -------------------------------------

                        if (
                            roster_date
                            in unavailable_dates.get(
                                employee_id,
                                set(),
                            )
                        ):
                            continue

                        # -------------------------------------
                        # Weekly off
                        # -------------------------------------

                        if (
                            roster_date.weekday()
                            in weekly_offs.get(
                                employee_id,
                                set(),
                            )
                        ):
                            continue

                        key = (
                            roster_date,
                            employee_id,
                            brand_id,
                            process_id,
                        )

                        variables[key] = (
                            model.NewBoolVar(
                                (
                                    f"x_"
                                    f"{roster_date}_"
                                    f"{employee_id}_"
                                    f"{brand_id}_"
                                    f"{process_id}"
                                )
                            )
                        )

            # =================================================
            # 10. COVERAGE CONSTRAINTS
            # =================================================
            #
            # Every operating process-day must have at least
            # minimum_staff employees.
            #
            # This is a MANDATORY constraint.
            # =================================================

            for (
                process_id,
                brand_id,
                minimum_staff,
                operating_calendar,
            ) in processes:

                process_key = (
                    brand_id,
                    process_id,
                )

                candidates = sorted(
                    eligible.get(
                        process_key,
                        set(),
                    )
                )

                for day_number in range(
                    1,
                    days_in_month + 1,
                ):

                    roster_date = date(
                        year,
                        month,
                        day_number,
                    )

                    if not is_operating_day(
                        roster_date,
                        operating_calendar,
                        public_holidays,
                    ):
                        continue

                    day_variables = []

                    for employee_id in candidates:

                        key = (
                            roster_date,
                            employee_id,
                            brand_id,
                            process_id,
                        )

                        variable = variables.get(
                            key
                        )

                        if variable is not None:
                            day_variables.append(
                                variable
                            )

                    if not day_variables:

                        static_conflicts.append({
                            "date": (
                                roster_date.isoformat()
                            ),
                            "brand_id": brand_id,
                            "process_id": process_id,
                            "minimum_staff": (
                                minimum_staff
                            ),
                            "reason": (
                                "No eligible employee "
                                "is available for this "
                                "operating process-day."
                            ),
                        })

                        # Force model infeasibility.
                        model.Add(
                            0 >= minimum_staff
                        )

                    else:

                        model.Add(
                            sum(
                                day_variables
                            )
                            >= minimum_staff
                        )

            # =================================================
            # 11. EMPLOYEE DAILY CAPACITY
            # =================================================
            #
            # An employee can work on multiple processes in
            # one day, but not more than the configured capacity.
            #
            # This is NOT an hours/overtime calculation.
            # =================================================

            for employee_id in employees:

                for day_number in range(
                    1,
                    days_in_month + 1,
                ):

                    roster_date = date(
                        year,
                        month,
                        day_number,
                    )

                    employee_day_variables = [
                        variable
                        for (
                            variable_date,
                            variable_employee,
                            _variable_brand,
                            _variable_process,
                        ), variable in variables.items()
                        if (
                            variable_date
                            == roster_date
                            and variable_employee
                            == employee_id
                        )
                    ]

                    if employee_day_variables:

                        model.Add(
                            sum(
                                employee_day_variables
                            )
                            <= DAILY_PROCESS_CAPACITY
                        )

            # =================================================
            # 12. EMPLOYEE WORKLOAD VARIABLES
            # =================================================
            #
            # Only employees who have at least one valid
            # candidate assignment in this month participate
            # in workload balancing.
            #
            # This is important:
            #
            # We DO NOT force employees with no eligible work
            # to receive assignments.
            # =================================================

            employee_variables = {}

            for (
                roster_date,
                employee_id,
                brand_id,
                process_id,
            ), variable in variables.items():

                employee_variables.setdefault(
                    employee_id,
                    [],
                ).append(variable)

            eligible_month_employees = sorted(
                employee_variables.keys()
            )

            if not eligible_month_employees:
                return {
                    "status": "infeasible",
                    "year": year,
                    "month": month,
                    "message": (
                        "No eligible employee can "
                        "receive any roster assignment "
                        "for this month."
                    ),
                    "conflicts": (
                        static_conflicts[:50]
                    ),
                }

            # =================================================
            # 13. EMPLOYEE LOAD VARIABLES
            # =================================================

            employee_load_variables = {}

            for employee_id in (
                eligible_month_employees
            ):

                employee_vars = (
                    employee_variables[
                        employee_id
                    ]
                )

                max_employee_possible_load = (
                    len(employee_vars)
                )

                load_variable = (
                    model.NewIntVar(
                        0,
                        max_employee_possible_load,
                        (
                            f"employee_load_"
                            f"{employee_id}"
                        ),
                    )
                )

                model.Add(
                    load_variable
                    == sum(employee_vars)
                )

                employee_load_variables[
                    employee_id
                ] = load_variable

            # =================================================
            # 14. TOTAL ASSIGNMENT VARIABLE
            # =================================================
            #
            # This allows the objective to first minimize
            # unnecessary roster entries.
            # =================================================

            total_assignment_variable = (
                model.NewIntVar(
                    0,
                    len(variables),
                    "total_roster_assignments",
                )
            )

            model.Add(
                total_assignment_variable
                == sum(variables.values())
            )

            # =================================================
            # 15. MAXIMUM EMPLOYEE WORKLOAD
            # =================================================

            max_possible_load = max(
                len(employee_variables[eid])
                for eid in eligible_month_employees
            )

            max_employee_load = (
                model.NewIntVar(
                    0,
                    max_possible_load,
                    "max_employee_load",
                )
            )

            for employee_id in (
                eligible_month_employees
            ):

                model.Add(
                    employee_load_variables[
                        employee_id
                    ]
                    <= max_employee_load
                )

            # =================================================
            # 16. CALCULATE REQUIRED STAFFING SLOTS
            # =================================================

            required_staff_slots = 0

            for (
                process_id,
                brand_id,
                minimum_staff,
                operating_calendar,
            ) in processes:

                for day_number in range(
                    1,
                    days_in_month + 1,
                ):

                    roster_date = date(
                        year,
                        month,
                        day_number,
                    )

                    if is_operating_day(
                        roster_date,
                        operating_calendar,
                        public_holidays,
                    ):

                        required_staff_slots += (
                            minimum_staff
                        )

            # =================================================
            # 17. TARGET WORKLOAD
            # =================================================
            #
            # Example:
            #
            # Required slots = 1123
            # Eligible employees = 22
            #
            # Target ≈ 51 assignments per employee.
            #
            # This does NOT force every employee to receive
            # exactly 51 assignments. Eligibility and capacity
            # constraints still control the solution.
            # =================================================

            eligible_employee_count = len(
                eligible_month_employees
            )

            target_workload = (
                required_staff_slots
                + eligible_employee_count
                - 1
            ) // eligible_employee_count

            # =================================================
            # 18. WORKLOAD DEVIATION VARIABLES
            # =================================================
            #
            # For each eligible employee:
            #
            # deviation =
            #     abs(actual workload - target workload)
            #
            # The solver minimizes total deviation.
            # =================================================

            workload_deviation_variables = []

            max_deviation = max(
                max_possible_load,
                target_workload,
            )

            for employee_id in (
                eligible_month_employees
            ):

                deviation = (
                    model.NewIntVar(
                        0,
                        max_deviation,
                        (
                            f"workload_deviation_"
                            f"{employee_id}"
                        ),
                    )
                )

                model.AddAbsEquality(
                    deviation,
                    (
                        employee_load_variables[
                            employee_id
                        ]
                        - target_workload
                    ),
                )

                workload_deviation_variables.append(
                    deviation
                )

            total_workload_deviation = (
                model.NewIntVar(
                    0,
                    (
                        max_deviation
                        * eligible_employee_count
                    ),
                    "total_workload_deviation",
                )
            )

            model.Add(
                total_workload_deviation
                == sum(
                    workload_deviation_variables
                )
            )

            # =================================================
            # 19. PRIMARY / BACKUP VARIABLES
            # =================================================

            primary_variables = []

            backup_variables = []

            for (
                roster_date,
                employee_id,
                brand_id,
                process_id,
            ), variable in variables.items():

                assignment_key = (
                    employee_id,
                    brand_id,
                    process_id,
                )

                assignment_type = (
                    assignment_types.get(
                        assignment_key,
                        "BACKUP",
                    )
                )

                if assignment_type == "PRIMARY":

                    primary_variables.append(
                        variable
                    )

                else:

                    backup_variables.append(
                        variable
                    )

            # =================================================
            # 20. OBJECTIVE
            # =================================================
            #
            # Priority order:
            #
            # 1. MINIMIZE total roster entries.
            #
            #    We do not want the solver creating unnecessary
            #    assignments just to use more employees.
            #
            # 2. MINIMIZE workload deviation from the target.
            #
            #    This distributes work across eligible employees.
            #
            # 3. MINIMIZE maximum employee workload.
            #
            #    This prevents a few employees from carrying
            #    extremely high workloads.
            #
            # 4. PREFER PRIMARY assignments.
            #
            # 5. AVOID BACKUP assignments when possible.
            #
            # Large integer weights create a lexicographic-style
            # priority while keeping the objective CP-SAT compatible.
            #
            # CP-SAT works with integer objectives.
            # =================================================

            if variables:

                # Upper bound for secondary objective terms.
                max_secondary_score = (
                    (
                        max_deviation
                        * eligible_employee_count
                    )
                    * 100_000
                    + (
                        max_possible_load
                        * 1_000
                    )
                    + len(variables)
                    + len(variables)
                )

                total_weight = (
                    max_secondary_score
                    + 1
                )

                model.Minimize(
                    (
                        total_weight
                        * total_assignment_variable
                    )
                    + (
                        100_000
                        * total_workload_deviation
                    )
                    + (
                        1_000
                        * max_employee_load
                    )
                    - (
                        10
                        * sum(primary_variables)
                    )
                    + (
                        1
                        * sum(backup_variables)
                    )
                )

            # =================================================
            # 21. SOLVE
            # =================================================

            solver = cp_model.CpSolver()

            solver.parameters.max_time_in_seconds = (
                SOLVER_TIME_LIMIT_SECONDS
            )

            # Keep the solver deterministic.
            solver.parameters.num_search_workers = 1

            status = solver.Solve(
                model
            )

            # =================================================
            # 22. HANDLE SOLVER RESULT
            # =================================================

            if status not in (
                cp_model.OPTIMAL,
                cp_model.FEASIBLE,
            ):

                return {
                    "status": "infeasible",
                    "year": year,
                    "month": month,
                    "message": (
                        "No feasible roster could "
                        "be generated."
                    ),
                    "conflicts": (
                        static_conflicts[:50]
                    ),
                    "required_staff_slots": (
                        required_staff_slots
                    ),
                }

            # =================================================
            # 23. DELETE EXISTING MONTH ROSTER
            # =================================================
            #
            # Regenerating November automatically replaces
            # the previous November roster.
            # =================================================

            cur.execute(
                """
                DELETE FROM roster_entries
                WHERE roster_date >= %s
                  AND roster_date <= %s;
                """,
                (
                    first_day,
                    last_day,
                ),
            )

            # =================================================
            # 24. INSERT GENERATED ROSTER
            # =================================================

            generated = []

            for (
                roster_date,
                employee_id,
                brand_id,
                process_id,
            ), variable in variables.items():

                if solver.Value(variable) != 1:
                    continue

                assignment_key = (
                    employee_id,
                    brand_id,
                    process_id,
                )

                assignment_type = (
                    assignment_types.get(
                        assignment_key,
                        "BACKUP",
                    )
                )

                if assignment_type == "PRIMARY":
                    final_assignment_type = (
                        "PRIMARY"
                    )
                else:
                    final_assignment_type = (
                        "BACKUP"
                    )

                cur.execute(
                    """
                    INSERT INTO roster_entries (
                        roster_date,
                        employee_id,
                        brand_id,
                        process_id,
                        assignment_type
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    );
                    """,
                    (
                        roster_date,
                        employee_id,
                        brand_id,
                        process_id,
                        final_assignment_type,
                    ),
                )

                generated.append({
                    "date": (
                        roster_date.isoformat()
                    ),
                    "employee_id": employee_id,
                    "brand_id": brand_id,
                    "process_id": process_id,
                    "assignment_type": (
                        final_assignment_type
                    ),
                })

            # =================================================
            # 25. BUILD WORKLOAD SUMMARY
            # =================================================

            workload_summary = []

            for employee_id in employees:

                if employee_id in (
                    employee_load_variables
                ):

                    workload = solver.Value(
                        employee_load_variables[
                            employee_id
                        ]
                    )

                    possible_assignments = len(
                        employee_variables.get(
                            employee_id,
                            [],
                        )
                    )

                    workload_summary.append({
                        "employee_id": employee_id,
                        "assignments": workload,
                        "possible_assignments": (
                            possible_assignments
                        ),
                    })

                else:

                    workload_summary.append({
                        "employee_id": employee_id,
                        "assignments": 0,
                        "possible_assignments": 0,
                    })

            workload_summary.sort(
                key=lambda item: (
                    -item["assignments"],
                    item["employee_id"],
                )
            )

            # =================================================
            # 26. COMMIT
            # =================================================

            conn.commit()

            # =================================================
            # 27. RETURN RESULT
            # =================================================

            return {
                "status": "generated",
                "year": year,
                "month": month,

                "assignments_created": len(
                    generated
                ),

                "required_staff_slots": (
                    required_staff_slots
                ),

                "extra_assignments": max(
                    0,
                    len(generated)
                    - required_staff_slots,
                ),

                "eligible_employees": (
                    len(
                        eligible_month_employees
                    )
                ),

                "target_workload": (
                    target_workload
                ),

                "maximum_employee_workload": (
                    solver.Value(
                        max_employee_load
                    )
                ),

                "total_workload_deviation": (
                    solver.Value(
                        total_workload_deviation
                    )
                ),

                "workload": workload_summary,

                "static_conflicts": (
                    static_conflicts[:50]
                ),

                "roster": generated,
            }