"""
Smart Roster Management System - development seed data.

Usage:
    python seed.py            # seed (skips if employees already exist)
    python seed.py --reset    # clear development roster data, then seed
    python seed.py --check    # only run feasibility check (no DB write)

This seed is designed to be feasible for November 2026.

The solver is NOT modified or weakened.

The dataset contains:
- 32 employees
- 4 pods
- 10 brands
- 40 processes
- 8 dedicated brands
- 2 shared brands
- primary + backup assignments
- different operating calendars
- weekly offs
- leave
- unavailable dates
- comp-off
- public holidays
- mandatory + preference constraints
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import sys
from calendar import monthrange
from datetime import date, timedelta


# ============================================================================
# CONFIGURATION
# ============================================================================

YEAR = 2026
MONTH = 11

PODS = [
    "Alpha",
    "Beta",
    "Gamma",
    "Delta",
]


# ============================================================================
# EMPLOYEES
# ============================================================================
#
# Format:
# employee_code, name, pod, is_pod_lead, weekly_off
#
# Python weekday:
# Monday    = 0
# Tuesday   = 1
# Wednesday = 2
# Thursday  = 3
# Friday    = 4
# Saturday  = 5
# Sunday    = 6
#
# ============================================================================

EMPLOYEES = [
    # Alpha
    ("E001", "Aarav Mehta",       "Alpha", True,  2),
    ("E002", "Priya Nair",        "Alpha", False, 6),
    ("E003", "Rohan Iyer",        "Alpha", False, 5),
    ("E004", "Sneha Kulkarni",    "Alpha", False, 4),
    ("E005", "Vikram Singh",      "Alpha", False, 6),
    ("E006", "Ananya Reddy",      "Alpha", False, 6),
    ("E007", "Karan Malhotra",    "Alpha", False, 5),
    ("E008", "Divya Menon",       "Alpha", False, 0),

    # Beta
    ("E009", "Rahul Verma",       "Beta", True,  3),
    ("E010", "Pooja Sharma",      "Beta", False, 2),
    ("E011", "Arjun Das",         "Beta", False, 0),
    ("E012", "Neha Gupta",        "Beta", False, 6),
    ("E013", "Siddharth Rao",     "Beta", False, 1),
    ("E014", "Kavya Pillai",      "Beta", False, 3),
    ("E015", "Manish Joshi",      "Beta", False, 1),
    ("E016", "Ritu Bansal",       "Beta", False, 6),

    # Gamma
    ("E017", "Amit Chauhan",      "Gamma", True,  4),
    ("E018", "Shreya Desai",      "Gamma", False, 4),
    ("E019", "Nikhil Patil",      "Gamma", False, 4),
    ("E020", "Isha Kapoor",       "Gamma", False, 2),
    ("E021", "Varun Khanna",      "Gamma", False, 5),
    ("E022", "Meera Krishnan",    "Gamma", False, 6),
    ("E023", "Tarun Saxena",      "Gamma", False, 3),
    ("E024", "Lakshmi Narayanan", "Gamma", False, 6),

    # Delta
    ("E025", "Sanjay Bhatia",     "Delta", True,  0),
    ("E026", "Aditi Banerjee",    "Delta", False, 2),
    ("E027", "Harsh Agarwal",     "Delta", False, 5),
    ("E028", "Tanvi Shetty",      "Delta", False, 1),
    ("E029", "Deepak Yadav",      "Delta", False, 6),
    ("E030", "Simran Kaur",       "Delta", False, 0),
    ("E031", "Gaurav Mishra",     "Delta", False, 4),
    ("E032", "Fatima Sheikh",     "Delta", False, 5),
]


# ============================================================================
# PROCESSES
# ============================================================================

PROCESS_NAMES = [
    "Customer Support",
    "Abandoned Cart Conversion",
    "Retention",
    "Non-Delivery Report",
]


# ============================================================================
# OPERATING CALENDARS
# ============================================================================

C365 = "365_days"
CDPH = "daily_except_public_holidays"
CSUN = "sundays_public_holidays_off"
CWKD = "weekdays_only"


# ============================================================================
# BRANDS
# ============================================================================
#
# Approximately 80% dedicated:
#   8 dedicated brands
#   2 shared brands
#
# Each process:
#
#   (
#       process_name,
#       operating_calendar,
#       minimum_staff,
#       backup_employee_codes
#   )
#
# ============================================================================

BRANDS = {

    # ------------------------------------------------------------------------
    # DEDICATED BRANDS
    # ------------------------------------------------------------------------

    "UrbanCart": {
        "kind": "dedicated",
        "primary": ["E002"],
        "processes": [
            (
                "Customer Support",
                C365,
                1,
                ["E010", "E001"],
            ),
            (
                "Abandoned Cart Conversion",
                CDPH,
                1,
                ["E010", "E001"],
            ),
            (
                "Retention",
                CWKD,
                1,
                [],
            ),
            (
                "Non-Delivery Report",
                CSUN,
                1,
                [],
            ),
        ],
    },

    "FreshBasket": {
        "kind": "dedicated",
        "primary": ["E003"],
        "processes": [
            (
                "Customer Support",
                C365,
                1,
                ["E011", "E019"],
            ),
            (
                "Abandoned Cart Conversion",
                CDPH,
                1,
                ["E011"],
            ),
            (
                "Retention",
                CWKD,
                1,
                [],
            ),
            (
                "Non-Delivery Report",
                C365,
                1,
                ["E011", "E032"],
            ),
        ],
    },

    "StyleHub": {
        "kind": "dedicated",
        "primary": ["E005"],
        "processes": [
            (
                "Customer Support",
                CDPH,
                1,
                ["E013"],
            ),
            (
                "Abandoned Cart Conversion",
                CWKD,
                1,
                [],
            ),
            (
                "Retention",
                CWKD,
                1,
                [],
            ),
            (
                "Non-Delivery Report",
                CSUN,
                1,
                [],
            ),
        ],
    },

    "HomeNest": {
        "kind": "dedicated",
        "primary": ["E006"],
        "processes": [
            (
                "Customer Support",
                CSUN,
                1,
                [],
            ),
            (
                "Abandoned Cart Conversion",
                CWKD,
                1,
                [],
            ),
            (
                "Retention",
                CWKD,
                1,
                [],
            ),
            (
                "Non-Delivery Report",
                CSUN,
                1,
                [],
            ),
        ],
    },

    "GlowCare": {
        "kind": "dedicated",
        "primary": ["E007"],
        "processes": [
            (
                "Customer Support",
                C365,
                1,
                ["E018"],
            ),
            (
                "Abandoned Cart Conversion",
                CWKD,
                1,
                [],
            ),
            (
                "Retention",
                CWKD,
                1,
                [],
            ),
            (
                "Non-Delivery Report",
                CWKD,
                1,
                [],
            ),
        ],
    },

    "TechZone": {
        "kind": "dedicated",
        "primary": ["E012"],
        "processes": [
            (
                "Customer Support",
                CDPH,
                1,
                ["E020", "E014"],
            ),
            (
                "Abandoned Cart Conversion",
                CSUN,
                1,
                [],
            ),
            (
                "Retention",
                CWKD,
                1,
                [],
            ),
            (
                "Non-Delivery Report",
                CSUN,
                1,
                [],
            ),
        ],
    },

    "DailyNeeds": {
        "kind": "dedicated",
        "primary": ["E015"],
        "processes": [
            (
                "Customer Support",
                C365,
                1,
                ["E021", "E022"],
            ),
            (
                "Abandoned Cart Conversion",
                C365,
                1,
                ["E021", "E022"],
            ),
            (
                "Retention",
                CDPH,
                1,
                ["E021", "E022"],
            ),
            (
                "Non-Delivery Report",
                C365,
                1,
                ["E021", "E022"],
            ),
        ],
    },

    "FitLife": {
        "kind": "dedicated",
        "primary": ["E016"],
        "processes": [
            (
                "Customer Support",
                CDPH,
                1,
                ["E023"],
            ),
            (
                "Abandoned Cart Conversion",
                CSUN,
                1,
                [],
            ),
            (
                "Retention",
                CWKD,
                1,
                [],
            ),
            (
                "Non-Delivery Report",
                CSUN,
                1,
                [],
            ),
        ],
    },

    # ------------------------------------------------------------------------
    # SHARED BRANDS
    # ------------------------------------------------------------------------

    "PureKitchen": {
        "kind": "shared",
        "primary": ["E004", "E008", "E024"],
        "processes": [
            (
                "Customer Support",
                C365,
                2,
                ["E026", "E017"],
            ),
            (
                "Abandoned Cart Conversion",
                CDPH,
                2,
                ["E026", "E017"],
            ),
            (
                "Retention",
                CWKD,
                1,
                [],
            ),
            (
                "Non-Delivery Report",
                CSUN,
                1,
                [],
            ),
        ],
    },

    "QuickShop": {
        "kind": "shared",
        "primary": ["E027", "E028", "E029"],
        "processes": [
            (
                "Customer Support",
                C365,
                2,
                ["E030", "E031", "E009"],
            ),
            (
                "Abandoned Cart Conversion",
                CDPH,
                2,
                ["E030", "E031", "E025"],
            ),
            (
                "Retention",
                CSUN,
                1,
                ["E030"],
            ),
            (
                "Non-Delivery Report",
                CWKD,
                1,
                ["E031"],
            ),
        ],
    },
}


# ============================================================================
# PUBLIC HOLIDAYS
# ============================================================================

PUBLIC_HOLIDAYS = [
    (date(2026, 1, 26), "Republic Day"),
    (date(2026, 3, 4), "Holi"),
    (date(2026, 4, 3), "Good Friday"),
    (date(2026, 5, 1), "Labour Day"),
    (date(2026, 8, 15), "Independence Day"),
    (date(2026, 10, 2), "Gandhi Jayanti"),
    (date(2026, 10, 20), "Dussehra"),
    (date(2026, 11, 8), "Diwali"),
    (date(2026, 11, 24), "Guru Nanak Jayanti"),
    (date(2026, 12, 25), "Christmas Day"),
]


# ============================================================================
# EMPLOYEE AVAILABILITY
# ============================================================================
#
# Format:
#
# employee_code,
# start_date,
# end_date,
# availability_type,
# reason
#
# ============================================================================

AVAILABILITY = [
    (
        "E010",
        date(2026, 11, 17),
        date(2026, 11, 18),
        "LEAVE",
        "Family function",
    ),
    (
        "E011",
        date(2026, 11, 9),
        date(2026, 11, 10),
        "LEAVE",
        "Personal leave",
    ),
    (
        "E018",
        date(2026, 11, 5),
        date(2026, 11, 6),
        "LEAVE",
        "Medical appointment",
    ),
    (
        "E004",
        date(2026, 11, 12),
        date(2026, 11, 13),
        "LEAVE",
        "Annual leave",
    ),
    (
        "E015",
        date(2026, 11, 25),
        date(2026, 11, 26),
        "LEAVE",
        "Annual leave",
    ),
    (
        "E030",
        date(2026, 11, 16),
        date(2026, 11, 17),
        "LEAVE",
        "Personal leave",
    ),
    (
        "E020",
        date(2026, 11, 11),
        date(2026, 11, 11),
        "UNAVAILABLE",
        "Training session",
    ),
    (
        "E028",
        date(2026, 11, 19),
        date(2026, 11, 19),
        "UNAVAILABLE",
        "Client visit",
    ),
    (
        "E026",
        date(2026, 11, 12),
        date(2026, 11, 12),
        "COMP_OFF",
        "Worked on 2026-10-20 holiday",
    ),
]


# ============================================================================
# CONSTRAINT CONFIGURATION
# ============================================================================

CONSTRAINTS = [
    (
        "Employee leave",
        "MANDATORY",
        "Employee on approved leave can never be rostered.",
    ),
    (
        "Employee unavailable dates",
        "MANDATORY",
        "Employee on unavailable dates can never be rostered.",
    ),
    (
        "Comp-off",
        "MANDATORY",
        "Employee on comp-off can never be rostered.",
    ),
    (
        "Weekly off",
        "MANDATORY",
        "Employee is never rostered on their weekly off.",
    ),
    (
        "Minimum process staffing",
        "MANDATORY",
        "Each operating process-day needs at least minimum staff.",
    ),
    (
        "Fair weekly-off distribution",
        "PREFERENCE",
        "Spread workload and days worked evenly across employees.",
    ),
    (
        "Prefer primary over backup",
        "PREFERENCE",
        "Use primary assignees before backup assignees where possible.",
    ),
]


# ============================================================================
# FEASIBILITY CHECK
# ============================================================================

HOLIDAYS = {
    holiday_date
    for holiday_date, _ in PUBLIC_HOLIDAYS
}


def operates(calendar, roster_date):
    """
    Determine whether a process operates on a particular date.
    """

    if calendar == C365:
        return True

    if calendar == CDPH:
        return roster_date not in HOLIDAYS

    if calendar == CSUN:
        return (
            roster_date.weekday() != 6
            and roster_date not in HOLIDAYS
        )

    if calendar == CWKD:
        return roster_date.weekday() < 5

    raise ValueError(
        f"Unknown operating calendar: {calendar}"
    )


def verify_feasibility(verbose=False):
    """
    Pure Python pre-check.

    This checks the same important availability/coverage conditions
    before anything is written to PostgreSQL.
    """

    employee_codes = [
        employee[0]
        for employee in EMPLOYEES
    ]

    assert len(employee_codes) == len(set(employee_codes)), (
        "Duplicate employee codes detected."
    )

    weekly_off = {
        employee[0]: employee[4]
        for employee in EMPLOYEES
    }

    unavailable_dates = {}

    for (
        employee_code,
        start_date,
        end_date,
        availability_type,
        reason,
    ) in AVAILABILITY:

        assert employee_code in weekly_off, (
            f"Availability references unknown employee: {employee_code}"
        )

        assert start_date <= end_date, (
            f"Invalid availability range for {employee_code}"
        )

        current_date = start_date

        while current_date <= end_date:

            unavailable_dates.setdefault(
                employee_code,
                set(),
            ).add(current_date)

            current_date += timedelta(days=1)

    problems = []

    tightest_slack = (
        999,
        None,
    )

    number_of_days = monthrange(
        YEAR,
        MONTH,
    )[1]

    days = [
        date(YEAR, MONTH, day_number)
        for day_number in range(1, number_of_days + 1)
    ]

    for brand_name, brand_config in BRANDS.items():

        for (
            process_name,
            calendar,
            minimum_staff,
            backups,
        ) in brand_config["processes"]:

            eligible_employees = (
                brand_config["primary"]
                + backups
            )

            assert len(eligible_employees) == len(
                set(eligible_employees)
            ), (
                f"Duplicate assignment detected: "
                f"{brand_name}/{process_name}"
            )

            for employee_code in eligible_employees:

                assert employee_code in weekly_off, (
                    f"Unknown employee {employee_code} "
                    f"in {brand_name}/{process_name}"
                )

            for roster_date in days:

                if not operates(
                    calendar,
                    roster_date,
                ):
                    continue

                available_employees = [
                    employee_code
                    for employee_code in eligible_employees
                    if (
                        weekly_off[employee_code]
                        != roster_date.weekday()
                        and roster_date
                        not in unavailable_dates.get(
                            employee_code,
                            set(),
                        )
                    )
                ]

                available_count = len(
                    available_employees
                )

                if available_count < minimum_staff:

                    problems.append(
                        f"{roster_date} "
                        f"{brand_name}/{process_name}: "
                        f"need {minimum_staff}, "
                        f"available {available_count} "
                        f"of {eligible_employees}"
                    )

                slack = (
                    available_count
                    - minimum_staff
                )

                if slack < tightest_slack[0]:

                    tightest_slack = (
                        slack,
                        f"{roster_date} "
                        f"{brand_name}/{process_name}",
                    )

    if problems:

        raise SystemExit(
            "INFEASIBLE DATA:\n  "
            + "\n  ".join(problems)
        )

    if verbose:

        print(
            f"Feasibility OK for "
            f"{YEAR}-{MONTH:02d}."
        )

        print(
            f"Tightest staffing slack: "
            f"{tightest_slack[0]} "
            f"spare at {tightest_slack[1]}"
        )


# ============================================================================
# COUNTS
# ============================================================================

def counts():

    assignment_count = 0

    for brand_config in BRANDS.values():

        assignment_count += (
            len(brand_config["primary"])
            * len(brand_config["processes"])
        )

        assignment_count += sum(
            len(process_config[3])
            for process_config
            in brand_config["processes"]
        )

    return {
        "Employees": len(EMPLOYEES),
        "Pods": len(PODS),
        "Brands": len(BRANDS),
        "Processes": sum(
            len(config["processes"])
            for config in BRANDS.values()
        ),
        "Assignments": assignment_count,
        "Operating rules": sum(
            len(config["processes"])
            for config in BRANDS.values()
        ),
        "Weekly offs": len(EMPLOYEES),
        "Availability records": len(AVAILABILITY),
        "Public holidays": len(PUBLIC_HOLIDAYS),
        "Constraints": len(CONSTRAINTS),
    }


# ============================================================================
# DATABASE RESET
# ============================================================================

RESET_TABLES = [
    "roster_entries",
    "constraints_config",
    "public_holidays",
    "availabilities",
    "weekly_offs",
    "operating_rules",
    "assignments",
    "processes",
    "brands",
    "employees",
    "pods",
]


def reset_database(conn):

    with conn.cursor() as cur:

        cur.execute(
            "TRUNCATE TABLE "
            + ", ".join(RESET_TABLES)
            + " RESTART IDENTITY CASCADE"
        )

    conn.commit()

    print("Development database reset successfully.")


# ============================================================================
# DATABASE SEED
# ============================================================================

def seed(conn):

    with conn.cursor() as cur:

        cur.execute(
            "SELECT COUNT(*) FROM employees"
        )

        if cur.fetchone()[0] > 0:

            print(
                "Employees already exist - "
                "skipping seed."
            )

            return False

        # ------------------------------------------------------------
        # PODS
        # ------------------------------------------------------------

        pod_ids = {}

        for pod_name in PODS:

            cur.execute(
                """
                INSERT INTO pods (name)
                VALUES (%s)
                RETURNING id
                """,
                (pod_name,),
            )

            pod_ids[pod_name] = cur.fetchone()[0]

        # ------------------------------------------------------------
        # EMPLOYEES
        # ------------------------------------------------------------

        employee_ids = {}

        for (
            employee_code,
            employee_name,
            pod_name,
            is_pod_lead,
            weekly_off,
        ) in EMPLOYEES:

            email = (
                employee_name
                .lower()
                .replace(" ", ".")
                + "@smartroster.example"
            )

            cur.execute(
                """
                INSERT INTO employees (
                    employee_code,
                    name,
                    email,
                    active,
                    pod_id
                )
                VALUES (%s, %s, %s, TRUE, %s)
                RETURNING id
                """,
                (
                    employee_code,
                    employee_name,
                    email,
                    pod_ids[pod_name],
                ),
            )

            employee_ids[employee_code] = (
                cur.fetchone()[0]
            )

        # ------------------------------------------------------------
        # POD LEADS
        # ------------------------------------------------------------

        for (
            employee_code,
            _employee_name,
            pod_name,
            is_pod_lead,
            _weekly_off,
        ) in EMPLOYEES:

            if is_pod_lead:

                cur.execute(
                    """
                    UPDATE pods
                    SET lead_employee_id = %s
                    WHERE id = %s
                    """,
                    (
                        employee_ids[employee_code],
                        pod_ids[pod_name],
                    ),
                )

        # ------------------------------------------------------------
        # WEEKLY OFFS
        # ------------------------------------------------------------

        for (
            employee_code,
            _employee_name,
            _pod_name,
            _is_pod_lead,
            weekly_off,
        ) in EMPLOYEES:

            cur.execute(
                """
                INSERT INTO weekly_offs (
                    employee_id,
                    weekday
                )
                VALUES (%s, %s)
                """,
                (
                    employee_ids[employee_code],
                    weekly_off,
                ),
            )

        # ------------------------------------------------------------
        # BRANDS + PROCESSES + RULES + ASSIGNMENTS
        # ------------------------------------------------------------

        for brand_name, brand_config in BRANDS.items():

            cur.execute(
                """
                INSERT INTO brands (name)
                VALUES (%s)
                RETURNING id
                """,
                (brand_name,),
            )

            brand_id = cur.fetchone()[0]

            for (
                process_name,
                operating_calendar,
                minimum_staff,
                backups,
            ) in brand_config["processes"]:

                cur.execute(
                    """
                    INSERT INTO processes (
                        brand_id,
                        name
                    )
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (
                        brand_id,
                        process_name,
                    ),
                )

                process_id = cur.fetchone()[0]

                # IMPORTANT:
                # These column names match the current solver:
                # operating_calendar
                # minimum_staff_per_day

                cur.execute(
                    """
                    INSERT INTO operating_rules (
                        brand_id,
                        process_id,
                        rule_name,
                        operating_calendar,
                        minimum_staff_per_day,
                        active
                    )
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    """,
                    (
                        brand_id,
                        process_id,
                        f"{brand_name} - {process_name}",
                        operating_calendar,
                        minimum_staff,
                    ),
                )

                # PRIMARY assignments

                for employee_code in brand_config["primary"]:

                    cur.execute(
                        """
                        INSERT INTO assignments (
                            employee_id,
                            brand_id,
                            process_id,
                            assignment_type,
                            active
                        )
                        VALUES (%s, %s, %s, 'PRIMARY', TRUE)
                        """,
                        (
                            employee_ids[employee_code],
                            brand_id,
                            process_id,
                        ),
                    )

                # BACKUP assignments

                for employee_code in backups:

                    cur.execute(
                        """
                        INSERT INTO assignments (
                            employee_id,
                            brand_id,
                            process_id,
                            assignment_type,
                            active
                        )
                        VALUES (%s, %s, %s, 'BACKUP', TRUE)
                        """,
                        (
                            employee_ids[employee_code],
                            brand_id,
                            process_id,
                        ),
                    )

        # ------------------------------------------------------------
        # AVAILABILITY
        # ------------------------------------------------------------
        #
        # Store the date range as one availability record.
        #
        # The current solver reads:
        # employee_id
        # start_date
        # end_date
        # availability_type
        #
        # ------------------------------------------------------------

        for (
            employee_code,
            start_date,
            end_date,
            availability_type,
            reason,
        ) in AVAILABILITY:

            cur.execute(
                """
                INSERT INTO availabilities (
                    employee_id,
                    start_date,
                    end_date,
                    availability_type,
                    reason
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    employee_ids[employee_code],
                    start_date,
                    end_date,
                    availability_type,
                    reason,
                ),
            )

        # ------------------------------------------------------------
        # PUBLIC HOLIDAYS
        # ------------------------------------------------------------

        for holiday_date, holiday_name in PUBLIC_HOLIDAYS:

            cur.execute(
                """
                INSERT INTO public_holidays (
                    holiday_date,
                    name
                )
                VALUES (%s, %s)
                """,
                (
                    holiday_date,
                    holiday_name,
                ),
            )

        # ------------------------------------------------------------
        # CONSTRAINT CONFIGURATION
        # ------------------------------------------------------------

        for (
            constraint_name,
            constraint_type,
            description,
        ) in CONSTRAINTS:
            cur.execute(
                """
                INSERT INTO constraints_config (
                    name,
                    constraint_type,
                    description,
                    active
                )
                VALUES (%s, %s, %s, TRUE)
                """,
                (
                    constraint_name,
                    constraint_type,
                    description,
                ),
            )

    conn.commit()

    return True


# ============================================================================
# MAIN
# ============================================================================

def main():

    # Always validate the dataset first.
    verify_feasibility(verbose=True)

    # Check-only mode does not require DATABASE_URL.
    if "--check" in sys.argv:

        print()
        print("Dataset summary:")

        for key, value in counts().items():
            print(f"{key}: {value}")

        return

    database_url = os.getenv("DATABASE_URL")

    if not database_url:

        raise RuntimeError(
            "DATABASE_URL environment variable is not set."
        )

    import psycopg

    with psycopg.connect(database_url) as conn:

        if "--reset" in sys.argv:
            reset_database(conn)

        seeded = seed(conn)

        if seeded:

            print()
            print("Seed completed successfully.")
            print()
            print("Dataset summary:")

            for key, value in counts().items():
                print(f"{key}: {value}")


if __name__ == "__main__":
    main()