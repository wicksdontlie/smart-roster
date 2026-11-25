import { useEffect, useMemo, useState } from "react";
import AgentPanel from "./AgentPanel";
import RosterTable from "./RosterTable";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock3,
  Database,
  FileText,
  Grid3X3,
  Layers3,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Users,
  X,
  Zap,
} from "lucide-react";
import "./App.css";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/* =========================================================
   API
   ========================================================= */

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail
          ? JSON.stringify(data.detail)
          : `Request failed with status ${response.status}`;

    throw new Error(message);
  }

  return data;
}

/* =========================================================
   HELPERS
   ========================================================= */

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

function formatMonth(year, month) {
  return `${MONTH_NAMES[month - 1]} ${year}`;
}

function getMonthDays(year, month) {
  const count = new Date(year, month, 0).getDate();

  return Array.from({ length: count }, (_, index) => {
    const day = index + 1;
    const date = new Date(year, month - 1, day);

    return {
      day,
      date,
      key: formatDate(date),
      weekday: WEEKDAYS[date.getDay()],
      isWeekend: date.getDay() === 0 || date.getDay() === 6,
    };
  });
}

function formatDate(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function getInitials(name = "") {
  const parts = name.trim().split(/\s+/).filter(Boolean);

  if (!parts.length) {
    return "?";
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function shortCode(value = "") {
  const words = value
    .replace(/[^a-zA-Z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(Boolean);

  if (!words.length) {
    return "--";
  }

  if (words.length === 1) {
    return words[0].slice(0, 3).toUpperCase();
  }

  return words
    .slice(0, 3)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

function getBrandCode(brandName = "") {
  const normalized = brandName.trim().toLowerCase();

  const known = {
    facebook: "FB",
    urbancart: "UC",
    amazon: "AMZ",
    flipkart: "FK",
    myntra: "MYN",
    meesho: "MS",
    swiggy: "SW",
    zomato: "ZM",
  };

  if (known[normalized]) {
    return known[normalized];
  }

  return shortCode(brandName);
}

function getProcessCode(processName = "") {
  const normalized = processName.trim().toLowerCase();

  const known = {
    "customer support": "CS",
    accounting: "ACC",
    returns: "RET",
    return: "RET",
    "non delivery": "NDR",
    "non-delivery": "NDR",
    sales: "SAL",
    support: "SUP",
    operations: "OPS",
    logistics: "LOG",
  };

  if (known[normalized]) {
    return known[normalized];
  }

  return shortCode(processName);
}

function assignmentKey(employeeId, dateKey) {
  return `${employeeId}-${dateKey}`;
}

function buildRosterMap(roster) {
  const map = new Map();

  roster.forEach((entry) => {
    const key = assignmentKey(entry.employee_id, entry.roster_date);

    if (!map.has(key)) {
      map.set(key, []);
    }

    map.get(key).push(entry);
  });

  return map;
}

/* =========================================================
   BRAND COLOR
   ========================================================= */

const BRAND_TONES = [
  "brand-tone-1",
  "brand-tone-2",
  "brand-tone-3",
  "brand-tone-4",
  "brand-tone-5",
  "brand-tone-6",
];

function getBrandTone(brandName = "") {
  let hash = 0;

  for (let i = 0; i < brandName.length; i += 1) {
    hash = (hash << 5) - hash + brandName.charCodeAt(i);
    hash |= 0;
  }

  return BRAND_TONES[Math.abs(hash) % BRAND_TONES.length];
}

/* =========================================================
   SHARED COMPONENTS
   ========================================================= */

function Avatar({ name, size = "md" }) {
  return (
    <div className={`avatar avatar-${size}`} title={name}>
      {getInitials(name)}
    </div>
  );
}

function Chip({ children, tone = "neutral" }) {
  return <span className={`chip chip-${tone}`}>{children}</span>;
}

function Button({
  children,
  variant = "secondary",
  icon,
  onClick,
  disabled = false,
  type = "button",
  className = "",
}) {
  return (
    <button
      type={type}
      className={`button button-${variant} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}

function Card({ children, className = "" }) {
  return <section className={`card ${className}`}>{children}</section>;
}

function StatCard({
  icon,
  label,
  value,
  subtext,
  tone = "purple",
}) {
  return (
    <Card className="stat-card">
      <div className={`stat-icon stat-icon-${tone}`}>{icon}</div>

      <div className="stat-content">
        <div className="stat-label">{label}</div>

        <div className="stat-value">
          {typeof value === "number" ? value.toLocaleString() : value}
        </div>

        {subtext && <div className="stat-subtext">{subtext}</div>}
      </div>
    </Card>
  );
}

function EmptyState({
  icon = <Database size={22} />,
  title,
  description,
  action,
}) {
  return (
    <div className="empty-state">
      <div className="empty-illustration">{icon}</div>

      <h3>{title}</h3>

      <p>{description}</p>

      {action}
    </div>
  );
}

function Skeleton({ width = "100%", height = 16 }) {
  return (
    <div
      className="skeleton"
      style={{
        width,
        height,
      }}
    />
  );
}

/* =========================================================
   NAVIGATION
   ========================================================= */

function AppShell({
  activePage,
  onNavigate,
  children,
  employeeCount,
}) {
  const [menuOpen, setMenuOpen] = useState(false);

  const navigation = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: <Grid3X3 size={16} />,
    },
    {
      id: "roster",
      label: "Roster",
      icon: <CalendarDays size={16} />,
    },
    {
      id: "employees",
      label: "Employees",
      icon: <Users size={16} />,
    },
    {
      id: "brands",
      label: "Brands & Processes",
      icon: <Layers3 size={16} />,
    },
  ];

  return (
    <div className="app">
      <header className="navbar">
        <div className="navbar-inner">
          <div
            className="brand"
            onClick={() => onNavigate("dashboard")}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                onNavigate("dashboard");
              }
            }}
          >
            <div className="brand-mark">
              <CalendarDays size={20} />
            </div>

            <div className="brand-copy">
              <div className="brand-name">Smart Roster</div>

              <div className="brand-caption">
                Workforce Management
              </div>
            </div>
          </div>

          <nav className="nav-tabs">
            {navigation.map((item) => (
              <button
                key={item.id}
                className={`nav-tab ${
                  activePage === item.id ? "active" : ""
                }`}
                onClick={() => onNavigate(item.id)}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="navbar-actions">
            <div className="workspace-status">
              <span className="status-dot" />
              <span>Live workspace</span>
            </div>

            <div className="user-menu">
              <button
                className="user-button"
                onClick={() => setMenuOpen((value) => !value)}
                aria-label="Open user menu"
              >
                <Avatar name="Operations Manager" size="sm" />

                <span className="user-name">
                  Operations
                </span>

                <ChevronDown size={14} />
              </button>

              {menuOpen && (
                <div className="user-dropdown">
                  <div className="user-dropdown-title">
                    Operations Manager
                  </div>

                  <div className="user-dropdown-subtitle">
                    {employeeCount} active employees
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="main-content">{children}</main>
    </div>
  );
}

/* =========================================================
   PAGE HEADER
   ========================================================= */

function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}

        <h1>{title}</h1>

        {subtitle && <p>{subtitle}</p>}
      </div>

      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

/* =========================================================
   DASHBOARD
   ========================================================= */

function Dashboard({
  employees,
  roster,
  year,
  month,
  onGenerate,
  generating,
  onNavigate,
}) {
  const activeEmployees = employees.filter(
    (employee) => employee.active !== false
  );

  const primaryCount = roster.filter(
    (entry) =>
      entry.assignment_type?.toUpperCase() === "PRIMARY"
  ).length;

  const backupCount = roster.filter(
    (entry) =>
      entry.assignment_type?.toUpperCase() === "BACKUP"
  ).length;

  const totalAssignments = roster.length;

  const days = getMonthDays(year, month);

  const coverageByDay = days.map((day) => {
    const count = roster.filter(
      (entry) => entry.roster_date === day.key
    ).length;

    return {
      ...day,
      count,
    };
  });

  const maxCoverage = Math.max(
    ...coverageByDay.map((day) => day.count),
    1
  );

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Operations overview"
        title="Workforce command center"
        subtitle={`Monitor your ${formatMonth(
          year,
          month
        )} roster, workforce coverage and assignment health.`}
        actions={
          <Button
            variant="cta"
            icon={
              generating ? (
                <RefreshCw size={16} className="spin" />
              ) : (
                <Zap size={16} />
              )
            }
            onClick={onGenerate}
            disabled={generating}
          >
            {generating ? "Generating..." : "Generate Roster"}
          </Button>
        }
      />

      <div className="stats-grid">
        <StatCard
          icon={<Users size={19} />}
          label="Active employees"
          value={activeEmployees.length}
          subtext="Current workforce"
          tone="purple"
        />

        <StatCard
          icon={<CalendarDays size={19} />}
          label="Roster entries"
          value={totalAssignments}
          subtext={`${formatMonth(
            year,
            month
          )} generated assignments`}
          tone="lavender"
        />

        <StatCard
          icon={<CheckCircle2 size={19} />}
          label="Primary assignments"
          value={primaryCount}
          subtext={
            totalAssignments
              ? `${Math.round(
                  (primaryCount / totalAssignments) * 100
                )}% of roster`
              : "No roster generated"
          }
          tone="green"
        />

        <StatCard
          icon={<Layers3 size={19} />}
          label="Backup assignments"
          value={backupCount}
          subtext={
            totalAssignments
              ? `${Math.round(
                  (backupCount / totalAssignments) * 100
                )}% of roster`
              : "No roster generated"
          }
          tone="amber"
        />
      </div>

      <div className="dashboard-grid">
        <Card className="coverage-card">
          <div className="card-header">
            <div>
              <div className="card-kicker">Coverage</div>

              <h2>Daily roster activity</h2>

              <p>Assignment volume across the month.</p>
            </div>

            <Chip tone="neutral">
              {roster.length
                ? `${roster.length.toLocaleString()} entries`
                : "Not generated"}
            </Chip>
          </div>

          {roster.length ? (
            <div className="coverage-chart">
              {coverageByDay.map((day) => {
                const height =
                  day.count === 0
                    ? 4
                    : Math.max(
                        10,
                        Math.round(
                          (day.count / maxCoverage) * 150
                        )
                      );

                return (
                  <div
                    className="coverage-column"
                    key={day.key}
                  >
                    <div className="coverage-value">
                      {day.count}
                    </div>

                    <div
                      className={`coverage-bar ${
                        day.isWeekend ? "weekend-bar" : ""
                      }`}
                      style={{ height }}
                      title={`${day.key}: ${day.count} assignments`}
                    />

                    <div className="coverage-day">
                      {day.day}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              icon={<CalendarDays size={22} />}
              title="No roster generated"
              description="Generate the monthly roster to see daily workforce coverage here."
              action={
                <Button
                  variant="cta"
                  icon={<Zap size={15} />}
                  onClick={onGenerate}
                  disabled={generating}
                >
                  Generate Roster
                </Button>
              }
            />
          )}
        </Card>

        <Card className="health-card">
          <div className="card-header">
            <div>
              <div className="card-kicker">Roster health</div>

              <h2>Validation status</h2>

              <p>Current API-supported roster status.</p>
            </div>

            <ShieldCheck
              size={20}
              className="header-icon-success"
            />
          </div>

          <div className="health-list">
            <div className="health-row">
              <div className="health-icon success">
                <Check size={15} />
              </div>

              <div>
                <strong>Roster generation</strong>

                <span>
                  {roster.length
                    ? "Roster entries are available."
                    : "Waiting for monthly generation."}
                </span>
              </div>
            </div>

            <div className="health-row">
              <div className="health-icon neutral">
                <Settings2 size={15} />
              </div>

              <div>
                <strong>Constraint validation</strong>

                <span>
                  Use the roster validation endpoint for detailed
                  conflict checking.
                </span>
              </div>
            </div>

            <div className="health-row">
              <div className="health-icon neutral">
                <Clock3 size={15} />
              </div>

              <div>
                <strong>Monthly planning</strong>

                <span>
                  {formatMonth(year, month)} is the active planning
                  period.
                </span>
              </div>
            </div>
          </div>

          <button
            className="text-action"
            onClick={() => onNavigate("roster")}
          >
            Open roster
            <ArrowRight size={15} />
          </button>
        </Card>
      </div>

      <div className="quick-actions">
        <Card className="quick-action-card">
          <div className="quick-action-icon">
            <Users size={19} />
          </div>

          <div>
            <h3>Manage employees</h3>

            <p>
              Add, update and review workforce records.
            </p>
          </div>

          <button
            className="icon-button"
            onClick={() => onNavigate("employees")}
          >
            <ArrowRight size={16} />
          </button>
        </Card>

        <Card className="quick-action-card">
          <div className="quick-action-icon">
            <Layers3 size={19} />
          </div>

          <div>
            <h3>Brands & processes</h3>

            <p>
              Review operating processes and staffing rules.
            </p>
          </div>

          <button
            className="icon-button"
            onClick={() => onNavigate("brands")}
          >
            <ArrowRight size={16} />
          </button>
        </Card>

        <Card className="quick-action-card">
          <div className="quick-action-icon">
            <FileText size={19} />
          </div>

          <div>
            <h3>Roster workspace</h3>

            <p>
              Inspect daily employee assignments in detail.
            </p>
          </div>

          <button
            className="icon-button"
            onClick={() => onNavigate("roster")}
          >
            <ArrowRight size={16} />
          </button>
        </Card>
      </div>

      {/* =====================================================
          AI ROSTER COPILOT
          ===================================================== */}

      <AgentPanel />
    </div>
  );
}

/* =========================================================
   ROSTER
   ========================================================= */

function RosterPage({
  employees,
  roster,
  brands,
  year,
  month,
  setYear,
  setMonth,
  onGenerate,
  generating,
  onRefresh,
  onRosterUpdated,
}) {
  const [search, setSearch] = useState("");
  const [brandFilter, setBrandFilter] = useState("all");
  const [processFilter, setProcessFilter] = useState("all");
  const [podFilter, setPodFilter] = useState("all");
  const [zoom, setZoom] = useState("compact");
  const [selectedAssignment, setSelectedAssignment] =
    useState(null);

  const days = getMonthDays(year, month);

  const processes = useMemo(() => {
    const map = new Map();

    roster.forEach((entry) => {
      map.set(entry.process_id, {
        id: entry.process_id,
        name: entry.process_name,
        brandId: entry.brand_id,
        brandName: entry.brand_name,
      });
    });

    return Array.from(map.values()).sort((a, b) =>
      a.name.localeCompare(b.name)
    );
  }, [roster]);

  const rosterEmployees = useMemo(() => {
    const employeeMap = new Map();

    employees.forEach((employee) => {
      employeeMap.set(employee.id, employee);
    });

    roster.forEach((entry) => {
      if (!employeeMap.has(entry.employee_id)) {
        employeeMap.set(entry.employee_id, {
          id: entry.employee_id,
          name: entry.employee_name,
          employee_code: "",
          active: true,
          pod_id: entry.pod_id ?? null,
        });
      }
    });

    return Array.from(employeeMap.values());
  }, [employees, roster]);

  const podOptions = useMemo(() => {
    const values = new Map();

    employees.forEach((employee) => {
      if (
        employee.pod_id !== null &&
        employee.pod_id !== undefined
      ) {
        values.set(String(employee.pod_id), employee.pod_id);
      }
    });

    return Array.from(values.values()).sort(
      (a, b) => a - b
    );
  }, [employees]);

  const rosterMap = useMemo(
    () => buildRosterMap(roster),
    [roster]
  );

  const filteredEmployees = useMemo(() => {
    const query = search.trim().toLowerCase();

    return rosterEmployees.filter((employee) => {
      const matchesSearch =
        !query ||
        employee.name?.toLowerCase().includes(query) ||
        employee.employee_code
          ?.toLowerCase()
          .includes(query);

      const matchesPod =
        podFilter === "all" ||
        String(employee.pod_id) === podFilter;

      return matchesSearch && matchesPod;
    });
  }, [rosterEmployees, search, podFilter]);

  const filteredEntry = (entry) => {
    const matchesBrand =
      brandFilter === "all" ||
      String(entry.brand_id) === brandFilter;

    const matchesProcess =
      processFilter === "all" ||
      String(entry.process_id) === processFilter;

    return matchesBrand && matchesProcess;
  };

  function moveMonth(delta) {
    let nextMonth = month + delta;
    let nextYear = year;

    if (nextMonth < 1) {
      nextMonth = 12;
      nextYear -= 1;
    }

    if (nextMonth > 12) {
      nextMonth = 1;
      nextYear += 1;
    }

    setMonth(nextMonth);
    setYear(nextYear);
  }

  function goToday() {
    const today = new Date();

    setYear(today.getFullYear());
    setMonth(today.getMonth() + 1);
  }

  const primaryCount = roster.filter(
    (entry) =>
      entry.assignment_type?.toUpperCase() === "PRIMARY"
  ).length;

  const backupCount = roster.filter(
    (entry) =>
      entry.assignment_type?.toUpperCase() === "BACKUP"
  ).length;

  return (
    <div className="page-container roster-page">
      <PageHeader
        eyebrow="Operations"
        title="Monthly roster"
        subtitle="Plan and manage employee assignments across brands and processes."
        actions={
          <Button
            variant="cta"
            icon={
              generating ? (
                <RefreshCw size={16} className="spin" />
              ) : (
                <Zap size={16} />
              )
            }
            onClick={onGenerate}
            disabled={generating}
          >
            {generating
              ? "Generating..."
              : "Generate Roster"}
          </Button>
        }
      />

      <Card className="roster-toolbar">
        <div className="month-control">
          <button
            className="icon-button"
            onClick={() => moveMonth(-1)}
            title="Previous month"
          >
            <ArrowLeft size={16} />
          </button>

          <div className="month-display">
            <CalendarDays size={16} />
            <strong>
              {formatMonth(year, month)}
            </strong>
          </div>

          <button
            className="icon-button"
            onClick={() => moveMonth(1)}
            title="Next month"
          >
            <ArrowRight size={16} />
          </button>

          <Button
            variant="ghost"
            onClick={goToday}
          >
            Today
          </Button>
        </div>

        <div className="toolbar-divider" />

        <div className="filter-control search-control">
          <Search size={15} />

          <input
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
            placeholder="Search employee..."
          />
        </div>

        <select
          className="select-control"
          value={brandFilter}
          onChange={(event) =>
            setBrandFilter(event.target.value)
          }
        >
          <option value="all">All brands</option>

          {brands.map((brand) => (
            <option key={brand.id} value={brand.id}>
              {brand.name}
            </option>
          ))}
        </select>

        <select
          className="select-control"
          value={processFilter}
          onChange={(event) =>
            setProcessFilter(event.target.value)
          }
        >
          <option value="all">All processes</option>

          {processes.map((process) => (
            <option
              key={process.id}
              value={process.id}
            >
              {process.name}
            </option>
          ))}
        </select>

        <select
          className="select-control"
          value={podFilter}
          onChange={(event) =>
            setPodFilter(event.target.value)
          }
        >
          <option value="all">All pods</option>

          {podOptions.map((podId) => (
            <option key={podId} value={podId}>
              Pod {podId}
            </option>
          ))}
        </select>

        <div className="toolbar-spacer" />

        <div className="zoom-toggle">
          <button
            className={
              zoom === "compact" ? "active" : ""
            }
            onClick={() => setZoom("compact")}
          >
            Compact
          </button>

          <button
            className={
              zoom === "comfortable"
                ? "active"
                : ""
            }
            onClick={() => setZoom("comfortable")}
          >
            Comfortable
          </button>
        </div>

        <button
          className="refresh-button"
          onClick={onRefresh}
          title="Refresh roster"
        >
          <RefreshCw size={15} />
        </button>
      </Card>

      <div className="roster-summary">
        <div className="summary-left">
          <span>
            <strong>
              {filteredEmployees.length}
            </strong>{" "}
            employees
          </span>

          <span className="summary-separator">
            •
          </span>

          <span>
            <strong>{days.length}</strong> days
          </span>

          <span className="summary-separator">
            •
          </span>

          <span>
            <strong>
              {roster.length.toLocaleString()}
            </strong>{" "}
            roster entries
          </span>
        </div>

        <div className="summary-right">
          <div className="legend">
            <LegendDot
              tone="primary"
              label="Primary"
            />

            <LegendDot
              tone="backup"
              label="Backup"
            />

            <LegendDot
              tone="off"
              label="Off"
            />

            <LegendDot
              tone="leave"
              label="Leave"
            />

            <LegendDot
              tone="unavailable"
              label="Unavailable"
            />

            <LegendDot
              tone="holiday"
              label="Holiday"
            />
          </div>

          <Chip tone="success">
            {primaryCount.toLocaleString()} Primary
          </Chip>

          <Chip tone="lavender">
            {backupCount.toLocaleString()} Backup
          </Chip>
        </div>
      </div>

      <Card className="roster-container">
        {!filteredEmployees.length ? (
          <EmptyState
            icon={<Users size={22} />}
            title="No employees match these filters"
            description="Try clearing the search or changing the brand, process or pod filters."
            action={
              <Button
                variant="secondary"
                onClick={() => {
                  setSearch("");
                  setBrandFilter("all");
                  setProcessFilter("all");
                  setPodFilter("all");
                }}
              >
                Clear filters
              </Button>
            }
          />
        ) : (
          <div className="roster-scroll">
            <table
              className={`roster-table roster-${zoom}`}
            >
              <thead>
                <tr>
                  <th className="employee-header">
                    <div className="header-title">
                      Employee
                    </div>

                    <div className="header-subtitle">
                      Assignment
                    </div>
                  </th>

                  {days.map((day) => (
                    <th
                      key={day.key}
                      className={
                        day.isWeekend
                          ? "weekend-header"
                          : ""
                      }
                    >
                      <div className="day-header">
                        <span className="weekday">
                          {day.weekday}
                        </span>

                        <span className="day-number">
                          {day.day}
                        </span>

                        {day.isWeekend && (
                          <span className="day-status">
                            Weekend
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {filteredEmployees.map((employee) => (
                  <tr key={employee.id}>
                    <td className="employee-column">
                      <div className="employee-profile">
                        <Avatar
                          name={employee.name}
                          size="md"
                        />

                        <div className="employee-meta">
                          <div className="employee-name">
                            {employee.name}
                          </div>

                          <div className="employee-secondary">
                            <span className="employee-code">
                              {employee.employee_code ||
                                `E${String(
                                  employee.id
                                ).padStart(
                                  3,
                                  "0"
                                )}`}
                            </span>

                            <span>·</span>

                            <span>
                              {employee.pod_id
                                ? `Pod ${employee.pod_id}`
                                : "Unassigned"}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>

                    {days.map((day) => {
                      const entries =
                        rosterMap.get(
                          assignmentKey(
                            employee.id,
                            day.key
                          )
                        ) || [];

                      const visibleEntries =
                        entries.filter(
                          filteredEntry
                        );

                      return (
                        <td
                          key={day.key}
                          className={
                            day.isWeekend
                              ? "weekend-cell"
                              : ""
                          }
                        >
                          <RosterCell
                            entries={visibleEntries}
                            originalEntries={entries}
                            employee={employee}
                            date={day}
                            onClick={
                              setSelectedAssignment
                            }
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* =====================================================
          MANUAL ROSTER EDITING
          ===================================================== */}

      {roster.length > 0 && (
        <Card className="manual-edit-card">
          <div className="card-header">
            <div>
              <div className="card-kicker">
                Manual editing
              </div>

              <h2>Edit roster assignments</h2>

              <p>
                Change an assigned employee and let the backend
                validate the change before it is committed.
              </p>
            </div>
          </div>

          <RosterTable
            roster={roster}
            employees={employees}
            onRosterUpdated={onRosterUpdated}
          />
        </Card>
      )}

      {selectedAssignment && (
        <AssignmentDrawer
          assignment={selectedAssignment}
          onClose={() =>
            setSelectedAssignment(null)
          }
        />
      )}
    </div>
  );
}

/* =========================================================
   LEGEND
   ========================================================= */

function LegendDot({ tone, label }) {
  return (
    <div className="legend-item">
      <span
        className={`legend-dot legend-${tone}`}
      />

      <span>{label}</span>
    </div>
  );
}

/* =========================================================
   ROSTER CELL
   ========================================================= */

function RosterCell({
  entries,
  originalEntries,
  employee,
  date,
  onClick,
}) {
  if (!entries.length) {
    if (originalEntries.length) {
      return (
        <button
          className="roster-cell filtered-out"
          onClick={() =>
            onClick({
              employee,
              date,
              entries: originalEntries,
            })
          }
        >
          <span className="filtered-marker">
            —
          </span>
        </button>
      );
    }

    return (
      <div
        className={`roster-cell empty-roster-cell ${
          date.isWeekend
            ? "weekend-roster-cell"
            : ""
        }`}
      >
        <span className="off-label">
          {date.isWeekend ? "OFF" : ""}
        </span>
      </div>
    );
  }

  return (
    <button
      className="roster-cell assigned-cell"
      onClick={() =>
        onClick({
          employee,
          date,
          entries,
        })
      }
      title="Open assignment details"
    >
      {entries.slice(0, 2).map((entry) => {
        const isBackup =
          entry.assignment_type?.toUpperCase() ===
          "BACKUP";

        const brandCode = getBrandCode(
          entry.brand_name
        );

        const processCode = getProcessCode(
          entry.process_name
        );

        return (
          <div
            className="compact-assignment"
            key={entry.id}
          >
            <span
              className={`brand-chip ${getBrandTone(
                entry.brand_name
              )}`}
            >
              {brandCode}
            </span>

            <span className="process-code">
              {processCode}
            </span>

            {isBackup && (
              <span className="backup-marker">
                B
              </span>
            )}
          </div>
        );
      })}

      {entries.length > 2 && (
        <span className="more-assignment">
          +{entries.length - 2}
        </span>
      )}
    </button>
  );
}

/* =========================================================
   ASSIGNMENT DRAWER
   ========================================================= */

function AssignmentDrawer({
  assignment,
  onClose,
}) {
  return (
    <>
      <div
        className="drawer-overlay"
        onClick={onClose}
      />

      <aside className="drawer">
        <div className="drawer-header">
          <div>
            <div className="drawer-kicker">
              Assignment details
            </div>

            <h2>
              {assignment.employee?.name ||
                "Employee"}
            </h2>
          </div>

          <button
            className="drawer-close"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <div className="drawer-body">
          <div className="drawer-employee">
            <Avatar
              name={assignment.employee?.name}
              size="lg"
            />

            <div>
              <strong>
                {assignment.employee?.name}
              </strong>

              <span>
                {assignment.employee
                  ?.employee_code ||
                  `E${String(
                    assignment.employee?.id ||
                      ""
                  ).padStart(3, "0")}`}
              </span>
            </div>
          </div>

          <div className="drawer-date">
            <CalendarDays size={16} />

            <div>
              <span>Date</span>

              <strong>
                {assignment.date?.key}
              </strong>
            </div>
          </div>

          <div className="drawer-section">
            <div className="drawer-section-title">
              Assigned work
            </div>

            {assignment.entries?.map(
              (entry) => (
                <div
                  className="assignment-detail-card"
                  key={entry.id}
                >
                  <div className="assignment-detail-top">
                    <span
                      className={`brand-chip ${getBrandTone(
                        entry.brand_name
                      )}`}
                    >
                      {getBrandCode(
                        entry.brand_name
                      )}
                    </span>

                    <Chip
                      tone={
                        entry.assignment_type?.toUpperCase() ===
                        "BACKUP"
                          ? "lavender"
                          : "success"
                      }
                    >
                      {entry.assignment_type}
                    </Chip>
                  </div>

                  <div className="assignment-brand">
                    {entry.brand_name}
                  </div>

                  <div className="assignment-process">
                    {entry.process_name}
                  </div>
                </div>
              )
            )}
          </div>

          <div className="drawer-warning">
            <AlertTriangle size={16} />

            <div>
              <strong>Manual changes</strong>

              <p>
                Use the Manual Editing section on the
                roster page to change an employee.
                The backend checks eligibility,
                weekly offs, availability,
                daily capacity and roster validity
                before committing the change.
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

/* =========================================================
   EMPLOYEES
   ========================================================= */

function EmployeesPage({
  employees,
  onRefresh,
  onCreate,
  onUpdate,
  onDelete,
}) {
  const [search, setSearch] = useState("");
  const [podFilter, setPodFilter] = useState("all");
  const [editingEmployee, setEditingEmployee] =
    useState(null);
  const [showCreate, setShowCreate] =
    useState(false);

  const podOptions = useMemo(() => {
    return Array.from(
      new Set(
        employees
          .map((employee) => employee.pod_id)
          .filter(
            (podId) =>
              podId !== null &&
              podId !== undefined
          )
      )
    ).sort((a, b) => a - b);
  }, [employees]);

  const filteredEmployees = employees.filter(
    (employee) => {
      const query = search.trim().toLowerCase();

      const matchesSearch =
        !query ||
        employee.name
          ?.toLowerCase()
          .includes(query) ||
        employee.employee_code
          ?.toLowerCase()
          .includes(query) ||
        employee.email
          ?.toLowerCase()
          .includes(query);

      const matchesPod =
        podFilter === "all" ||
        String(employee.pod_id) ===
          podFilter;

      return matchesSearch && matchesPod;
    }
  );

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Workforce"
        title="Employees"
        subtitle="Manage employee records and workforce structure."
        actions={
          <Button
            variant="cta"
            icon={<Plus size={16} />}
            onClick={() =>
              setShowCreate(true)
            }
          >
            Add employee
          </Button>
        }
      />

      <Card className="table-card">
        <div className="table-toolbar">
          <div className="search-control large">
            <Search size={15} />

            <input
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              placeholder="Search employees..."
            />
          </div>

          <select
            className="select-control"
            value={podFilter}
            onChange={(event) =>
              setPodFilter(
                event.target.value
              )
            }
          >
            <option value="all">
              All pods
            </option>

            {podOptions.map((podId) => (
              <option
                key={podId}
                value={podId}
              >
                Pod {podId}
              </option>
            ))}
          </select>

          <div className="toolbar-spacer" />

          <div className="result-count">
            {filteredEmployees.length} employees
          </div>

          <button
            className="refresh-button"
            onClick={onRefresh}
            title="Refresh employees"
          >
            <RefreshCw size={15} />
          </button>
        </div>

        {filteredEmployees.length ? (
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Employee code</th>
                  <th>Email</th>
                  <th>Pod</th>
                  <th>Status</th>
                  <th className="actions-column">
                    Actions
                  </th>
                </tr>
              </thead>

              <tbody>
                {filteredEmployees.map(
                  (employee) => (
                    <tr key={employee.id}>
                      <td>
                        <div className="employee-profile">
                          <Avatar
                            name={
                              employee.name
                            }
                            size="md"
                          />

                          <div className="employee-meta">
                            <div className="employee-name">
                              {
                                employee.name
                              }
                            </div>

                            <div className="employee-secondary">
                              Employee #
                              {
                                employee.id
                              }
                            </div>
                          </div>
                        </div>
                      </td>

                      <td>
                        <span className="mono-text">
                          {
                            employee.employee_code
                          }
                        </span>
                      </td>

                      <td>
                        {employee.email}
                      </td>

                      <td>
                        {employee.pod_id ? (
                          <Chip tone="lavender">
                            Pod{" "}
                            {
                              employee.pod_id
                            }
                          </Chip>
                        ) : (
                          <span className="muted">
                            Unassigned
                          </span>
                        )}
                      </td>

                      <td>
                        {employee.active ===
                        false ? (
                          <Chip tone="neutral">
                            Inactive
                          </Chip>
                        ) : (
                          <Chip tone="success">
                            Active
                          </Chip>
                        )}
                      </td>

                      <td className="actions-column">
                        <div className="row-actions">
                          <button
                            className="table-action"
                            onClick={() =>
                              setEditingEmployee(
                                employee
                              )
                            }
                          >
                            Edit
                          </button>

                          <button
                            className="table-action danger"
                            onClick={() =>
                              onDelete(
                                employee.id
                              )
                            }
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<Users size={22} />}
            title="No employees found"
            description="No employee records match the current filters."
            action={
              <Button
                variant="secondary"
                onClick={() => {
                  setSearch("");
                  setPodFilter("all");
                }}
              >
                Clear filters
              </Button>
            }
          />
        )}
      </Card>

      {(showCreate || editingEmployee) && (
        <EmployeeModal
          employee={editingEmployee}
          onClose={() => {
            setShowCreate(false);
            setEditingEmployee(null);
          }}
          onSave={async (payload) => {
            if (editingEmployee) {
              await onUpdate(
                editingEmployee.id,
                payload
              );
            } else {
              await onCreate(payload);
            }

            setShowCreate(false);
            setEditingEmployee(null);
          }}
        />
      )}
    </div>
  );
}

/* =========================================================
   EMPLOYEE MODAL
   ========================================================= */

function EmployeeModal({
  employee,
  onClose,
  onSave,
}) {
  const [form, setForm] = useState({
    employee_code:
      employee?.employee_code || "",
    name: employee?.name || "",
    email: employee?.email || "",
    pod_id:
      employee?.pod_id === null ||
      employee?.pod_id === undefined
        ? ""
        : String(employee.pod_id),
    active:
      employee?.active === undefined
        ? true
        : employee.active,
  });

  const [saving, setSaving] =
    useState(false);

  const [error, setError] =
    useState("");

  async function submit(event) {
    event.preventDefault();

    setSaving(true);
    setError("");

    try {
      await onSave({
        employee_code:
          form.employee_code,
        name: form.name,
        email: form.email,
        pod_id: form.pod_id
          ? Number(form.pod_id)
          : null,
        active: form.active,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div
        className="modal-overlay"
        onClick={onClose}
      />

      <div className="modal">
        <div className="modal-header">
          <div>
            <div className="drawer-kicker">
              Workforce record
            </div>

            <h2>
              {employee
                ? "Edit employee"
                : "Add employee"}
            </h2>
          </div>

          <button
            className="drawer-close"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="modal-body">
            {error && (
              <div className="form-error">
                <AlertTriangle size={15} />
                {error}
              </div>
            )}

            {!employee && (
              <label className="form-field">
                <span>
                  Employee code
                </span>

                <input
                  value={
                    form.employee_code
                  }
                  onChange={(event) =>
                    setForm({
                      ...form,
                      employee_code:
                        event.target.value,
                    })
                  }
                  required
                  placeholder="E011"
                />
              </label>
            )}

            <label className="form-field">
              <span>Name</span>

              <input
                value={form.name}
                onChange={(event) =>
                  setForm({
                    ...form,
                    name:
                      event.target.value,
                  })
                }
                required
                placeholder="Employee name"
              />
            </label>

            <label className="form-field">
              <span>Email</span>

              <input
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm({
                    ...form,
                    email:
                      event.target.value,
                  })
                }
                required
                placeholder="employee@example.com"
              />
            </label>

            <label className="form-field">
              <span>Pod ID</span>

              <input
                type="number"
                value={form.pod_id}
                onChange={(event) =>
                  setForm({
                    ...form,
                    pod_id:
                      event.target.value,
                  })
                }
                placeholder="Optional"
              />
            </label>

            {employee && (
              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={form.active}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      active:
                        event.target
                          .checked,
                    })
                  }
                />

                <span>
                  Employee is active
                </span>
              </label>
            )}
          </div>

          <div className="modal-footer">
            <Button
              variant="ghost"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </Button>

            <Button
              type="submit"
              variant="cta"
              disabled={saving}
            >
              {saving
                ? "Saving..."
                : "Save employee"}
            </Button>
          </div>
        </form>
      </div>
    </>
  );
}

/* =========================================================
   BRANDS & PROCESSES
   ========================================================= */

function BrandsPage({
  brands,
  processes,
  onRefresh,
}) {
  const [expandedBrand, setExpandedBrand] =
    useState(null);

  const processesByBrand = useMemo(() => {
    const map = new Map();

    processes.forEach((process) => {
      if (!map.has(process.brand_id)) {
        map.set(process.brand_id, []);
      }

      map
        .get(process.brand_id)
        .push(process);
    });

    return map;
  }, [processes]);

  return (
    <div className="page-container">
      <PageHeader
        eyebrow="Configuration"
        title="Brands & processes"
        subtitle="Review brands, processes and their operating structure."
        actions={
          <Button
            variant="secondary"
            icon={
              <RefreshCw size={15} />
            }
            onClick={onRefresh}
          >
            Refresh
          </Button>
        }
      />

      {brands.length ? (
        <div className="brand-grid">
          {brands.map((brand) => {
            const brandProcesses =
              processesByBrand.get(
                brand.id
              ) || [];

            const expanded =
              expandedBrand ===
              brand.id;

            return (
              <Card
                className={`brand-card ${
                  expanded
                    ? "expanded"
                    : ""
                }`}
                key={brand.id}
              >
                <button
                  className="brand-card-header"
                  onClick={() =>
                    setExpandedBrand(
                      expanded
                        ? null
                        : brand.id
                    )
                  }
                >
                  <div className="brand-card-main">
                    <div
                      className={`brand-large-chip ${getBrandTone(
                        brand.name
                      )}`}
                    >
                      {getBrandCode(
                        brand.name
                      )}
                    </div>

                    <div>
                      <h3>
                        {brand.name}
                      </h3>

                      <p>
                        {
                          brandProcesses.length
                        }{" "}
                        processes
                      </p>
                    </div>
                  </div>

                  <div className="brand-expand">
                    {expanded ? (
                      <ChevronDown
                        size={18}
                      />
                    ) : (
                      <ChevronRight
                        size={18}
                      />
                    )}
                  </div>
                </button>

                {expanded && (
                  <div className="process-list">
                    {brandProcesses.length ? (
                      brandProcesses.map(
                        (process) => (
                          <div
                            className="process-row"
                            key={
                              process.id
                            }
                          >
                            <div className="process-code-box">
                              {getProcessCode(
                                process.name
                              )}
                            </div>

                            <div className="process-info">
                              <strong>
                                {
                                  process.name
                                }
                              </strong>

                              <span>
                                Process ID #
                                {
                                  process.id
                                }
                              </span>
                            </div>

                            <Chip tone="neutral">
                              Active
                            </Chip>
                          </div>
                        )
                      )
                    ) : (
                      <div className="process-empty">
                        No processes
                        configured.
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <EmptyState
            icon={
              <Layers3 size={22} />
            }
            title="No brands configured"
            description="Create brands and processes in the backend configuration to populate this workspace."
          />
        </Card>
      )}
    </div>
  );
}

/* =========================================================
   TOAST
   ========================================================= */

function Toast({
  toast,
  onClose,
}) {
  if (!toast) {
    return null;
  }

  return (
    <div
      className={`toast toast-${toast.type}`}
    >
      <div className="toast-icon">
        {toast.type === "success" ? (
          <CheckCircle2 size={17} />
        ) : (
          <AlertTriangle size={17} />
        )}
      </div>

      <div className="toast-content">
        <strong>
          {toast.title}
        </strong>

        <span>
          {toast.message}
        </span>
      </div>

      <button onClick={onClose}>
        <X size={15} />
      </button>
    </div>
  );
}

/* =========================================================
   APP
   ========================================================= */

export default function App() {
  const [activePage, setActivePage] =
    useState("roster");

  const [employees, setEmployees] =
    useState([]);

  const [brands, setBrands] =
    useState([]);

  const [processes, setProcesses] =
    useState([]);

  const [roster, setRoster] =
    useState([]);

  const today = new Date();

  const [year, setYear] =
    useState(today.getFullYear());

  const [month, setMonth] =
    useState(today.getMonth() + 1);

  const [loading, setLoading] =
    useState(true);

  const [generating, setGenerating] =
    useState(false);

  const [error, setError] =
    useState("");

  const [toast, setToast] =
    useState(null);

  /* =======================================================
     TOAST
     ======================================================= */

  function showToast(
    type,
    title,
    message
  ) {
    setToast({
      type,
      title,
      message,
    });

    window.setTimeout(() => {
      setToast(null);
    }, 4500);
  }

  /* =======================================================
     FETCH FUNCTIONS
     ======================================================= */

  async function fetchEmployees() {
    const data =
      await apiRequest("/employees");

    setEmployees(
      Array.isArray(data)
        ? data
        : []
    );
  }

  async function fetchBrands() {
    const data =
      await apiRequest("/brands");

    setBrands(
      Array.isArray(data)
        ? data
        : []
    );
  }

  async function fetchProcesses() {
    const data =
      await apiRequest("/processes");

    setProcesses(
      Array.isArray(data)
        ? data
        : []
    );
  }

  async function fetchRoster() {
    const data =
      await apiRequest(
        `/rosters?year=${year}&month=${month}`
      );

    setRoster(
      Array.isArray(data)
        ? data
        : []
    );
  }

  async function loadInitialData() {
    setLoading(true);
    setError("");

    try {
      await Promise.all([
        fetchEmployees(),
        fetchBrands(),
        fetchProcesses(),
        fetchRoster(),
      ]);
    } catch (err) {
      setError(
        err.message ||
          "Failed to fetch"
      );
    } finally {
      setLoading(false);
    }
  }

  async function refreshAll() {
    setError("");

    try {
      await Promise.all([
        fetchEmployees(),
        fetchBrands(),
        fetchProcesses(),
        fetchRoster(),
      ]);

      showToast(
        "success",
        "Workspace refreshed",
        "Latest data has been loaded."
      );
    } catch (err) {
      setError(
        err.message ||
          "Failed to refresh"
      );
    }
  }

  async function generateRoster() {
    setGenerating(true);
    setError("");

    try {
      const result =
        await apiRequest(
          `/rosters/generate?year=${year}&month=${month}`,
          {
            method: "POST",
          }
        );

      await fetchRoster();

      showToast(
        "success",
        "Roster generated",
        `${
          result?.assignments_created ||
          0
        } assignments created for ${formatMonth(
          year,
          month
        )}.`
      );
    } catch (err) {
      const message =
        err.message ||
        "Roster generation failed.";

      setError(message);

      showToast(
        "error",
        "Roster generation failed",
        message
      );
    } finally {
      setGenerating(false);
    }
  }

  /* =======================================================
     EMPLOYEE CRUD
     ======================================================= */

  async function createEmployee(
    payload
  ) {
    await apiRequest(
      "/employees",
      {
        method: "POST",
        body: JSON.stringify(
          payload
        ),
      }
    );

    await fetchEmployees();

    showToast(
      "success",
      "Employee created",
      "The employee was added successfully."
    );
  }

  async function updateEmployee(
    id,
    payload
  ) {
    await apiRequest(
      `/employees/${id}`,
      {
        method: "PUT",
        body: JSON.stringify(
          payload
        ),
      }
    );

    await fetchEmployees();

    showToast(
      "success",
      "Employee updated",
      "Employee details were saved."
    );
  }

  async function deleteEmployee(
    id
  ) {
    const confirmed =
      window.confirm(
        "Delete this employee?"
      );

    if (!confirmed) {
      return;
    }

    try {
      await apiRequest(
        `/employees/${id}`,
        {
          method: "DELETE",
        }
      );

      await fetchEmployees();

      showToast(
        "success",
        "Employee deleted",
        "The employee was removed successfully."
      );
    } catch (err) {
      showToast(
        "error",
        "Delete failed",
        err.message
      );
    }
  }

  /* =======================================================
     INITIAL LOAD
     ======================================================= */

  useEffect(() => {
    loadInitialData();
  }, []);

  /* =======================================================
     MONTH CHANGE
     ======================================================= */

  useEffect(() => {
    if (!loading) {
      fetchRoster().catch(
        (err) => {
          setError(
            err.message ||
              "Failed to fetch roster"
          );
        }
      );
    }
  }, [year, month]);

  /* =======================================================
     RENDER
     ======================================================= */

  return (
    <AppShell
      activePage={activePage}
      onNavigate={setActivePage}
      employeeCount={
        employees.filter(
          (employee) =>
            employee.active !== false
        ).length
      }
    >
      {error && (
        <div className="global-error">
          <div className="global-error-inner">
            <AlertTriangle size={17} />

            <span>{error}</span>

            <button
              onClick={() =>
                setError("")
              }
              aria-label="Dismiss error"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="page-container">
          <PageHeader
            eyebrow="Smart Roster"
            title="Loading workspace"
            subtitle="Preparing your workforce management workspace."
          />

          <div className="stats-grid">
            <Card className="stat-card">
              <Skeleton
                width={44}
                height={44}
              />

              <div className="stat-content">
                <Skeleton
                  width={90}
                  height={12}
                />

                <div
                  style={{
                    height: 8,
                  }}
                />

                <Skeleton
                  width={60}
                  height={25}
                />
              </div>
            </Card>

            <Card className="stat-card">
              <Skeleton
                width={44}
                height={44}
              />

              <div className="stat-content">
                <Skeleton
                  width={90}
                  height={12}
                />

                <div
                  style={{
                    height: 8,
                  }}
                />

                <Skeleton
                  width={60}
                  height={25}
                />
              </div>
            </Card>

            <Card className="stat-card">
              <Skeleton
                width={44}
                height={44}
              />

              <div className="stat-content">
                <Skeleton
                  width={90}
                  height={12}
                />

                <div
                  style={{
                    height: 8,
                  }}
                />

                <Skeleton
                  width={60}
                  height={25}
                />
              </div>
            </Card>

            <Card className="stat-card">
              <Skeleton
                width={44}
                height={44}
              />

              <div className="stat-content">
                <Skeleton
                  width={90}
                  height={12}
                />

                <div
                  style={{
                    height: 8,
                  }}
                />

                <Skeleton
                  width={60}
                  height={25}
                />
              </div>
            </Card>
          </div>

          <Card className="loading-card">
            <Skeleton
              width="100%"
              height={380}
            />
          </Card>
        </div>
      ) : (
        <>
          {activePage ===
            "dashboard" && (
            <Dashboard
              employees={employees}
              roster={roster}
              year={year}
              month={month}
              onGenerate={
                generateRoster
              }
              generating={
                generating
              }
              onNavigate={
                setActivePage
              }
            />
          )}

          {activePage === "roster" && (
            <RosterPage
              employees={employees}
              roster={roster}
              brands={brands}
              year={year}
              month={month}
              setYear={setYear}
              setMonth={setMonth}
              onGenerate={
                generateRoster
              }
              generating={
                generating
              }
              onRefresh={
                fetchRoster
              }
              onRosterUpdated={
                fetchRoster
              }
            />
          )}

          {activePage ===
            "employees" && (
            <EmployeesPage
              employees={employees}
              onRefresh={
                fetchEmployees
              }
              onCreate={
                createEmployee
              }
              onUpdate={
                updateEmployee
              }
              onDelete={
                deleteEmployee
              }
            />
          )}

          {activePage ===
            "brands" && (
            <BrandsPage
              brands={brands}
              processes={processes}
              onRefresh={
                refreshAll
              }
            />
          )}
        </>
      )}

      <Toast
        toast={toast}
        onClose={() =>
          setToast(null)
        }
      />
    </AppShell>
  );
}