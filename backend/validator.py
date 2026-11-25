from collections import defaultdict
from calendar import monthrange
from datetime import date
from contextlib import nullcontext

import psycopg

from models import DATABASE_URL


# ================================================================
# SUMMARY
# ================================================================

def _empty_summary():
    """
    Create the standard validation summary.

    Saturday and Sunday are globally treated as non-working days.
    """

    return {
        "employees": 0,
        "active_employees": 0,
        "brands": 0,
        "processes": 0,
        "assignments": 0,
        "operating_process_days": 0,
        "required_staff_slots": 0,
        "actual_roster_entries": 0,
        "primary_entries": 0,
        "backup_entries": 0,
        "excess_assignments": 0,
        "understaffed_process_days": 0,
        "overstaffed_process_days": 0,
        "duplicate_assignments": 0,
        "weekly_off_conflicts": 0,
        "weekend_conflicts": 0,
        "availability_conflicts": 0,
        "holiday_conflicts": 0,
        "inactive_employee_assignments": 0,
        "inactive_brand_assignments": 0,
        "coverage_percentage": 0.0,
        "issue_count": 0,
    }


# ================================================================
# OPERATING DAYS
# ================================================================

def _get_operating_days(year: int, month: int) -> list[date]:
    """
    Return the dates on which the workforce roster is allowed
    to operate.

    Global Smart Roster policy:
    Saturday and Sunday are always non-working days.

    Therefore only Monday-Friday are returned.
    """

    first_day = date(year, month, 1)

    last_day = date(
        year,
        month,
        monthrange(year, month)[1],
    )

    operating_days = []

    current_day = first_day

    while current_day <= last_day:

        # Monday = 0
        # Tuesday = 1
        # Wednesday = 2
        # Thursday = 3
        # Friday = 4
        # Saturday = 5
        # Sunday = 6

        if current_day.weekday() < 5:
            operating_days.append(current_day)

        current_day = date.fromordinal(
            current_day.toordinal() + 1
        )

    return operating_days


# ================================================================
# PROCESS OPERATING CALENDAR
# ================================================================

def _is_operating_day(
    roster_date: date,
    operating_calendar: str,
    public_holidays: set[date],
) -> bool:
    """
    Determine whether a process is expected to operate
    on a particular date.

    Global policy:
    Saturday and Sunday are ALWAYS non-working days.

    Process calendar rules are applied only to Monday-Friday.
    """

    # ------------------------------------------------------------
    # GLOBAL WEEKEND RULE
    # ------------------------------------------------------------

    if roster_date.weekday() in (5, 6):
        return False

    calendar_name = (
        operating_calendar or "365_days"
    ).strip().lower()

    # ------------------------------------------------------------
    # PROCESS CALENDAR
    # ------------------------------------------------------------

    if calendar_name == "365_days":
        return True

    if calendar_name == "daily_except_public_holidays":
        return roster_date not in public_holidays

    if calendar_name == "sundays_public_holidays_off":
        # Sunday is already blocked above.
        return roster_date not in public_holidays

    if calendar_name == "weekdays_only":
        return roster_date.weekday() < 5

    # Unknown calendar:
    # Keep Monday-Friday available.
    return True


# ================================================================
# VALIDATE ROSTER
# ================================================================

def validate_roster(
    year: int,
    month: int,
    conn=None,
):
    """
    Deterministically validate the roster stored in roster_entries.

    The validator does not use an LLM.

    It checks the actual database state against:

    - employees
    - brands
    - processes
    - assignments
    - operating rules
    - weekly offs
    - availability
    - public holidays
    - roster entries

    Global policy:
    Saturday and Sunday are always non-working days.
    """

    # ------------------------------------------------------------
    # Validate month
    # ------------------------------------------------------------

    if month < 1 or month > 12:
        raise ValueError(
            "Month must be between 1 and 12."
        )

    # ------------------------------------------------------------
    # Get Monday-Friday dates only
    # ------------------------------------------------------------

    days = _get_operating_days(
        year,
        month,
    )

    # ------------------------------------------------------------
    # Database connection
    # ------------------------------------------------------------

    connection_context = (
        nullcontext(conn)
        if conn is not None
        else psycopg.connect(
            DATABASE_URL,
            prepare_threshold=None,
        )
    )

    with connection_context as conn:

        with conn.cursor() as cur:

            # ====================================================
            # 1. EMPLOYEES
            # ====================================================

            cur.execute(
                """
                SELECT
                    id,
                    employee_code,
                    name,
                    active,
                    pod_id
                FROM employees
                ORDER BY id
                """
            )

            employee_rows = cur.fetchall()

            employees = {}

            for row in employee_rows:

                (
                    employee_id,
                    employee_code,
                    name,
                    active,
                    pod_id,
                ) = row

                employees[employee_id] = {
                    "id": employee_id,
                    "employee_code": employee_code,
                    "name": name,
                    "active": active,
                    "pod_id": pod_id,
                }

            # ====================================================
            # 2. BRANDS
            # ====================================================

            cur.execute(
                """
                SELECT
                    id,
                    name,
                    active
                FROM brands
                ORDER BY id
                """
            )

            brand_rows = cur.fetchall()

            brands = {}

            for row in brand_rows:

                brand_id, name, active = row

                brands[brand_id] = {
                    "id": brand_id,
                    "name": name,
                    "active": active,
                }

            # ====================================================
            # 3. PROCESSES
            # ====================================================

            cur.execute(
                """
                SELECT
                    id,
                    brand_id,
                    name
                FROM processes
                ORDER BY id
                """
            )

            process_rows = cur.fetchall()

            processes = {}

            for row in process_rows:

                (
                    process_id,
                    brand_id,
                    name,
                ) = row

                processes[process_id] = {
                    "id": process_id,
                    "brand_id": brand_id,
                    "name": name,
                }

            # ====================================================
            # 4. ASSIGNMENTS
            # ====================================================

            cur.execute(
                """
                SELECT
                    id,
                    employee_id,
                    brand_id,
                    process_id,
                    assignment_type,
                    active
                FROM assignments
                ORDER BY id
                """
            )

            assignment_rows = cur.fetchall()

            assignments = []

            assignment_lookup = defaultdict(list)

            for row in assignment_rows:

                (
                    assignment_id,
                    employee_id,
                    brand_id,
                    process_id,
                    assignment_type,
                    active,
                ) = row

                record = {
                    "id": assignment_id,
                    "employee_id": employee_id,
                    "brand_id": brand_id,
                    "process_id": process_id,
                    "assignment_type": assignment_type,
                    "active": active,
                }

                assignments.append(record)

                assignment_lookup[
                    (
                        employee_id,
                        brand_id,
                        process_id,
                    )
                ].append(record)

            # ====================================================
            # 5. OPERATING RULES
            # ====================================================

            cur.execute(
                """
                SELECT
                    id,
                    brand_id,
                    process_id,
                    rule_name,
                    operating_calendar,
                    minimum_staff_per_day,
                    active
                FROM operating_rules
                WHERE active = TRUE
                ORDER BY id
                """
            )

            rule_rows = cur.fetchall()

            rules = []

            for row in rule_rows:

                (
                    rule_id,
                    brand_id,
                    process_id,
                    rule_name,
                    operating_calendar,
                    minimum_staff_per_day,
                    active,
                ) = row

                rules.append(
                    {
                        "id": rule_id,
                        "brand_id": brand_id,
                        "process_id": process_id,
                        "rule_name": rule_name,
                        "operating_calendar": operating_calendar,
                        "minimum_staff_per_day": minimum_staff_per_day,
                        "active": active,
                    }
                )

            # ----------------------------------------------------
            # Process calendar lookup
            # ----------------------------------------------------

            process_calendar_lookup = {}

            for rule in rules:

                if rule["process_id"] is not None:

                    process_calendar_lookup[
                        (
                            rule["brand_id"],
                            rule["process_id"],
                        )
                    ] = rule["operating_calendar"]

            # ====================================================
            # 6. WEEKLY OFFS
            # ====================================================

            cur.execute(
                """
                SELECT
                    employee_id,
                    weekday
                FROM weekly_offs
                """
            )

            weekly_off_rows = cur.fetchall()

            weekly_offs = defaultdict(set)

            for employee_id, weekday in weekly_off_rows:

                weekly_offs[employee_id].add(
                    weekday
                )

            # ====================================================
            # 7. AVAILABILITY
            # ====================================================

            cur.execute(
                """
                SELECT
                    employee_id,
                    availability_type,
                    start_date,
                    end_date,
                    reason
                FROM availabilities
                """
            )

            availability_rows = cur.fetchall()

            availability_records = []

            for row in availability_rows:

                (
                    employee_id,
                    availability_type,
                    start_date,
                    end_date,
                    reason,
                ) = row

                availability_records.append(
                    {
                        "employee_id": employee_id,
                        "availability_type": availability_type,
                        "start_date": start_date,
                        "end_date": end_date,
                        "reason": reason,
                    }
                )

            # ====================================================
            # 8. PUBLIC HOLIDAYS
            # ====================================================

            cur.execute(
                """
                SELECT
                    holiday_date,
                    name
                FROM public_holidays
                """
            )

            holiday_rows = cur.fetchall()

            public_holidays = {
                holiday_date
                for holiday_date, _ in holiday_rows
            }

            # ====================================================
            # 9. ACTUAL ROSTER ENTRIES
            # ====================================================

            cur.execute(
                """
                SELECT
                    r.id,
                    r.roster_date,
                    r.employee_id,
                    r.brand_id,
                    r.process_id,
                    r.assignment_type
                FROM roster_entries r
                WHERE EXTRACT(YEAR FROM r.roster_date) = %s
                  AND EXTRACT(MONTH FROM r.roster_date) = %s
                ORDER BY
                    r.roster_date,
                    r.employee_id,
                    r.brand_id,
                    r.process_id,
                    r.id
                """,
                (
                    year,
                    month,
                ),
            )

            roster_rows = cur.fetchall()

    # ================================================================
    # BUILD VALIDATION STRUCTURES
    # ================================================================

    summary = _empty_summary()

    summary["employees"] = len(employees)

    summary["active_employees"] = sum(
        1
        for employee in employees.values()
        if employee["active"]
    )

    summary["brands"] = len(brands)

    summary["processes"] = len(processes)

    summary["assignments"] = len(assignments)

    summary["actual_roster_entries"] = len(
        roster_rows
    )

    issues = []

    # ================================================================
    # PRIMARY / BACKUP COUNT
    # ================================================================

    primary_entries = 0
    backup_entries = 0

    for row in roster_rows:

        assignment_type = str(
            row[5]
        ).upper()

        if assignment_type == "PRIMARY":
            primary_entries += 1

        elif assignment_type == "BACKUP":
            backup_entries += 1

    summary["primary_entries"] = (
        primary_entries
    )

    summary["backup_entries"] = (
        backup_entries
    )

    # ================================================================
    # DUPLICATE DETECTION
    # ================================================================

    duplicate_groups = defaultdict(list)

    for row in roster_rows:

        (
            roster_id,
            roster_date,
            employee_id,
            brand_id,
            process_id,
            assignment_type,
        ) = row

        key = (
            roster_date,
            employee_id,
            brand_id,
            process_id,
        )

        duplicate_groups[key].append(
            {
                "roster_id": roster_id,
                "assignment_type": assignment_type,
            }
        )

    for key, records in duplicate_groups.items():

        if len(records) > 1:

            summary["duplicate_assignments"] += (
                len(records) - 1
            )

            (
                roster_date,
                employee_id,
                brand_id,
                process_id,
            ) = key

            issues.append(
                {
                    "type": "DUPLICATE_ASSIGNMENT",
                    "severity": "HIGH",
                    "date": str(roster_date),
                    "employee_id": employee_id,
                    "brand_id": brand_id,
                    "process_id": process_id,
                    "message": (
                        f"Employee {employee_id} has "
                        f"{len(records)} roster entries for "
                        "the same date, brand and process."
                    ),
                }
            )

    # ================================================================
    # EMPLOYEE / PROCESS DAY STRUCTURES
    # ================================================================

    employee_day_entries = defaultdict(list)

    process_day_entries = defaultdict(list)

    # ================================================================
    # VALIDATE EACH ROSTER ENTRY
    # ================================================================

    for row in roster_rows:

        (
            roster_id,
            roster_date,
            employee_id,
            brand_id,
            process_id,
            assignment_type,
        ) = row

        employee_day_entries[
            (
                employee_id,
                roster_date,
            )
        ].append(row)

        process_day_entries[
            (
                roster_date,
                brand_id,
                process_id,
            )
        ].append(row)

        # ============================================================
        # WEEKEND CONFLICT
        # ============================================================

        if roster_date.weekday() in (5, 6):

            summary["weekend_conflicts"] += 1

            day_name = roster_date.strftime(
                "%A"
            )

            issues.append(
                {
                    "type": "WEEKEND_CONFLICT",
                    "severity": "HIGH",
                    "date": str(roster_date),
                    "employee_id": employee_id,
                    "brand_id": brand_id,
                    "process_id": process_id,
                    "message": (
                        f"Employee {employee_id} is "
                        f"rostered on {day_name}. "
                        "Saturday and Sunday are "
                        "non-working days."
                    ),
                }
            )

        # ============================================================
        # EMPLOYEE EXISTENCE / ACTIVE STATUS
        # ============================================================

        employee = employees.get(
            employee_id
        )

        if employee is None:

            issues.append(
                {
                    "type": "UNKNOWN_EMPLOYEE",
                    "severity": "HIGH",
                    "date": str(roster_date),
                    "employee_id": employee_id,
                    "message": (
                        "Roster entry references an "
                        "employee that does not exist."
                    ),
                }
            )

        elif not employee["active"]:

            summary[
                "inactive_employee_assignments"
            ] += 1

            issues.append(
                {
                    "type": "INACTIVE_EMPLOYEE",
                    "severity": "HIGH",
                    "date": str(roster_date),
                    "employee_id": employee_id,
                    "message": (
                        f"Inactive employee "
                        f"{employee['name']} is rostered."
                    ),
                }
            )

        # ============================================================
        # BRAND EXISTENCE / ACTIVE STATUS
        # ============================================================

        brand = brands.get(
            brand_id
        )

        if brand is None:

            issues.append(
                {
                    "type": "UNKNOWN_BRAND",
                    "severity": "HIGH",
                    "date": str(roster_date),
                    "brand_id": brand_id,
                    "message": (
                        "Roster entry references a "
                        "brand that does not exist."
                    ),
                }
            )

        elif not brand["active"]:

            summary[
                "inactive_brand_assignments"
            ] += 1

            issues.append(
                {
                    "type": "INACTIVE_BRAND",
                    "severity": "HIGH",
                    "date": str(roster_date),
                    "brand_id": brand_id,
                    "message": (
                        f"Inactive brand "
                        f"{brand['name']} is used "
                        "in the roster."
                    ),
                }
            )

        # ============================================================
        # PROCESS EXISTENCE / BRAND CONSISTENCY
        # ============================================================

        process = processes.get(
            process_id
        )

        if process is None:

            issues.append(
                {
                    "type": "UNKNOWN_PROCESS",
                    "severity": "HIGH",
                    "date": str(roster_date),
                    "process_id": process_id,
                    "message": (
                        "Roster entry references a "
                        "process that does not exist."
                    ),
                }
            )

        else:

            if process["brand_id"] != brand_id:

                issues.append(
                    {
                        "type": "BRAND_PROCESS_MISMATCH",
                        "severity": "HIGH",
                        "date": str(roster_date),
                        "brand_id": brand_id,
                        "process_id": process_id,
                        "message": (
                            "Roster entry uses a process "
                            "belonging to a different brand."
                        ),
                    }
                )

        # ============================================================
        # ASSIGNMENT ELIGIBILITY
        # ============================================================

        assignment_key = (
            employee_id,
            brand_id,
            process_id,
        )

        if not any(
            record["active"]
            for record in assignment_lookup.get(
                assignment_key,
                [],
            )
        ):

            issues.append(
                {
                    "type": "INELIGIBLE_ASSIGNMENT",
                    "severity": "HIGH",
                    "date": str(roster_date),
                    "employee_id": employee_id,
                    "brand_id": brand_id,
                    "process_id": process_id,
                    "message": (
                        "Employee is not actively assigned "
                        "to this brand/process."
                    ),
                }
            )

        # ============================================================
        # WEEKLY OFF
        # ============================================================

        if employee_id in employees:

            weekday = roster_date.weekday()

            if weekday in weekly_offs.get(
                employee_id,
                set(),
            ):

                summary[
                    "weekly_off_conflicts"
                ] += 1

                issues.append(
                    {
                        "type": "WEEKLY_OFF_CONFLICT",
                        "severity": "HIGH",
                        "date": str(roster_date),
                        "employee_id": employee_id,
                        "message": (
                            f"Employee {employee_id} is "
                            "rostered on their weekly off."
                        ),
                    }
                )

        # ============================================================
        # AVAILABILITY CONFLICT
        # ============================================================

        for availability in availability_records:

            if (
                availability["employee_id"]
                != employee_id
            ):
                continue

            if (
                availability["start_date"]
                <= roster_date
                <= availability["end_date"]
            ):

                availability_type = str(
                    availability["availability_type"]
                ).upper()

                normalized_type = (
                    availability_type
                    .replace("-", "_")
                    .replace(" ", "_")
                )

                if normalized_type in {
                    "LEAVE",
                    "UNAVAILABLE",
                    "COMP_OFF",
                    "UNAVAILABLE_DATE",
                }:

                    summary[
                        "availability_conflicts"
                    ] += 1

                    issues.append(
                        {
                            "type": "AVAILABILITY_CONFLICT",
                            "severity": "HIGH",
                            "date": str(roster_date),
                            "employee_id": employee_id,
                            "availability_type": availability_type,
                            "message": (
                                f"Employee {employee_id} "
                                f"is rostered during "
                                f"{availability_type.lower()}."
                            ),
                        }
                    )

        # ============================================================
        # PUBLIC HOLIDAY CONFLICT
        # ============================================================

        if roster_date in public_holidays:

            operating_calendar = (
                process_calendar_lookup.get(
                    (
                        brand_id,
                        process_id,
                    ),
                    "365_days",
                )
            )

            if operating_calendar in {
                "daily_except_public_holidays",
                "sundays_public_holidays_off",
            }:

                summary[
                    "holiday_conflicts"
                ] += 1

                issues.append(
                    {
                        "severity": "HIGH",
                        "type": "PUBLIC_HOLIDAY_CONFLICT",
                        "date": roster_date.isoformat(),
                        "employee_id": employee_id,
                        "brand_id": brand_id,
                        "process_id": process_id,
                        "message": (
                            "Employee is assigned to a "
                            "process that does not operate "
                            "on public holidays."
                        ),
                    }
                )

    # ================================================================
    # COVERAGE ANALYSIS
    # ================================================================

    required_staff_slots = 0
    operating_process_days = 0

    for rule in rules:

        brand_id = rule["brand_id"]
        process_id = rule["process_id"]

        # ============================================================
        # PROCESS-SPECIFIC RULE
        # ============================================================

        if process_id is not None:

            if process_id not in processes:
                continue

            process = processes[
                process_id
            ]

            if process["brand_id"] != brand_id:
                continue

            for roster_date in days:

                if not _is_operating_day(
                    roster_date,
                    rule["operating_calendar"],
                    public_holidays,
                ):
                    continue

                operating_process_days += 1

                required = max(
                    0,
                    int(
                        rule[
                            "minimum_staff_per_day"
                        ]
                    ),
                )

                required_staff_slots += (
                    required
                )

                actual = len(
                    process_day_entries.get(
                        (
                            roster_date,
                            brand_id,
                            process_id,
                        ),
                        [],
                    )
                )

                # ------------------------------------------------
                # UNDERSTAFFED
                # ------------------------------------------------

                if actual < required:

                    summary[
                        "understaffed_process_days"
                    ] += 1

                    issues.append(
                        {
                            "type": "UNDERSTAFFED",
                            "severity": "CRITICAL",
                            "date": str(roster_date),
                            "brand_id": brand_id,
                            "process_id": process_id,
                            "required": required,
                            "assigned": actual,
                            "message": (
                                f"Process requires "
                                f"{required} staff but "
                                f"only {actual} "
                                "are assigned."
                            ),
                        }
                    )

                # ------------------------------------------------
                # OVERSTAFFED
                # ------------------------------------------------

                elif actual > required:

                    excess = (
                        actual - required
                    )

                    summary[
                        "overstaffed_process_days"
                    ] += 1

                    summary[
                        "excess_assignments"
                    ] += excess

                    issues.append(
                        {
                            "type": "OVERSTAFFED",
                            "severity": "MEDIUM",
                            "date": str(roster_date),
                            "brand_id": brand_id,
                            "process_id": process_id,
                            "required": required,
                            "assigned": actual,
                            "excess": excess,
                            "message": (
                                f"Process requires "
                                f"{required} staff "
                                f"but {actual} "
                                "are assigned."
                            ),
                        }
                    )

        # ============================================================
        # BRAND-LEVEL RULE
        # ============================================================

        else:

            brand_processes = [
                process
                for process in processes.values()
                if process["brand_id"]
                == brand_id
            ]

            for process in brand_processes:

                for roster_date in days:

                    if not _is_operating_day(
                        roster_date,
                        rule["operating_calendar"],
                        public_holidays,
                    ):
                        continue

                    operating_process_days += 1

                    required = max(
                        0,
                        int(
                            rule[
                                "minimum_staff_per_day"
                            ]
                        ),
                    )

                    required_staff_slots += (
                        required
                    )

                    actual = len(
                        process_day_entries.get(
                            (
                                roster_date,
                                brand_id,
                                process["id"],
                            ),
                            [],
                        )
                    )

                    # ------------------------------------------------
                    # UNDERSTAFFED
                    # ------------------------------------------------

                    if actual < required:

                        summary[
                            "understaffed_process_days"
                        ] += 1

                        issues.append(
                            {
                                "type": "UNDERSTAFFED",
                                "severity": "CRITICAL",
                                "date": str(roster_date),
                                "brand_id": brand_id,
                                "process_id": process["id"],
                                "required": required,
                                "assigned": actual,
                                "message": (
                                    f"Process requires "
                                    f"{required} staff "
                                    f"but only {actual} "
                                    "are assigned."
                                ),
                            }
                        )

                    # ------------------------------------------------
                    # OVERSTAFFED
                    # ------------------------------------------------

                    elif actual > required:

                        excess = (
                            actual - required
                        )

                        summary[
                            "overstaffed_process_days"
                        ] += 1

                        summary[
                            "excess_assignments"
                        ] += excess

                        issues.append(
                            {
                                "type": "OVERSTAFFED",
                                "severity": "MEDIUM",
                                "date": str(roster_date),
                                "brand_id": brand_id,
                                "process_id": process["id"],
                                "required": required,
                                "assigned": actual,
                                "excess": excess,
                                "message": (
                                    f"Process requires "
                                    f"{required} staff "
                                    f"but {actual} "
                                    "are assigned."
                                ),
                            }
                        )

    # ================================================================
    # COVERAGE SUMMARY
    # ================================================================

    summary[
        "operating_process_days"
    ] = operating_process_days

    summary[
        "required_staff_slots"
    ] = required_staff_slots

    # ================================================================
    # EMPLOYEE WORKLOAD
    # ================================================================

    workload = []

    for employee_id, employee in employees.items():

        total = 0
        primary = 0
        backup = 0
        working_days = set()

        for row in roster_rows:

            (
                roster_id,
                roster_date,
                row_employee_id,
                brand_id,
                process_id,
                assignment_type,
            ) = row

            if row_employee_id != employee_id:
                continue

            total += 1

            working_days.add(
                roster_date
            )

            if (
                str(
                    assignment_type
                ).upper()
                == "PRIMARY"
            ):
                primary += 1

            elif (
                str(
                    assignment_type
                ).upper()
                == "BACKUP"
            ):
                backup += 1

        workload.append(
            {
                "employee_id": employee_id,
                "employee_code": employee[
                    "employee_code"
                ],
                "name": employee[
                    "name"
                ],
                "total_assignments": total,
                "primary_assignments": primary,
                "backup_assignments": backup,
                "working_days": len(
                    working_days
                ),
            }
        )

    workload.sort(
        key=lambda item: item[
            "total_assignments"
        ],
        reverse=True,
    )

    zero_assignment_employees = [
        employee
        for employee in workload
        if employee[
            "total_assignments"
        ] == 0
    ]

    # ================================================================
    # OVERALL STATUS
    # ================================================================

    critical_count = sum(
        1
        for issue in issues
        if issue["severity"]
        == "CRITICAL"
    )

    high_count = sum(
        1
        for issue in issues
        if issue["severity"]
        == "HIGH"
    )

    medium_count = sum(
        1
        for issue in issues
        if issue["severity"]
        == "MEDIUM"
    )

    if critical_count > 0:

        status = "infeasible"

    elif high_count > 0:

        status = "invalid"

    elif medium_count > 0:

        status = "warning"

    else:

        status = "valid"

    # ================================================================
    # COVERAGE PERCENTAGE
    # ================================================================

    coverage_percentage = 0.0

    if operating_process_days > 0:

        covered = (
            operating_process_days
            - summary[
                "understaffed_process_days"
            ]
        )

        coverage_percentage = round(
            (
                covered
                / operating_process_days
            )
            * 100,
            2,
        )

    summary[
        "coverage_percentage"
    ] = coverage_percentage

    summary[
        "issue_count"
    ] = len(issues)

    # ================================================================
    # RETURN VALIDATION REPORT
    # ================================================================

    return {
        "status": status,
        "year": year,
        "month": month,
        "summary": summary,
        "workload": workload,
        "zero_assignment_employees": (
            zero_assignment_employees
        ),
        "issues": issues,
    }