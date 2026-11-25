import { useMemo, useState } from "react";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Pencil,
  X,
  Check,
} from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const PAGE_SIZE = 20;

export default function RosterTable({
  roster,
  employees,
  onRosterUpdated,
}) {
  const [editingId, setEditingId] = useState(null);
  const [selectedEmployee, setSelectedEmployee] = useState("");
  const [saving, setSaving] = useState(false);

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const filteredRoster = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return roster;
    }

    return roster.filter((row) => {
      return (
        String(row.roster_date || "")
          .toLowerCase()
          .includes(query) ||
        String(row.employee_name || "")
          .toLowerCase()
          .includes(query) ||
        String(row.brand_name || "")
          .toLowerCase()
          .includes(query) ||
        String(row.process_name || "")
          .toLowerCase()
          .includes(query) ||
        String(row.assignment_type || "")
          .toLowerCase()
          .includes(query)
      );
    });
  }, [roster, search]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredRoster.length / PAGE_SIZE)
  );

  const safePage = Math.min(page, totalPages);

  const paginatedRoster = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE;

    return filteredRoster.slice(
      start,
      start + PAGE_SIZE
    );
  }, [filteredRoster, safePage]);

  const startIndex =
    filteredRoster.length === 0
      ? 0
      : (safePage - 1) * PAGE_SIZE + 1;

  const endIndex = Math.min(
    safePage * PAGE_SIZE,
    filteredRoster.length
  );

  const startEdit = (row) => {
    setEditingId(row.id);
    setSelectedEmployee(String(row.employee_id));
  };

  const cancelEdit = () => {
    setEditingId(null);
    setSelectedEmployee("");
  };

  const saveEdit = async (row) => {
    if (!selectedEmployee) {
      alert("Please select an employee.");
      return;
    }

    if (
      Number(selectedEmployee) ===
      Number(row.employee_id)
    ) {
      cancelEdit();
      return;
    }

    setSaving(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/rosters/reassign`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            roster_date: row.roster_date,
            old_employee_id: row.employee_id,
            new_employee_id: Number(
              selectedEmployee
            ),
            brand_id: row.brand_id,
            process_id: row.process_id,
            assignment_type:
              row.assignment_type,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Unable to update roster."
        );
      }

      if (data.status !== "success") {
        throw new Error(
          data.message ||
            "Roster change was rejected."
        );
      }

      cancelEdit();

      if (onRosterUpdated) {
        await onRosterUpdated();
      }

      alert(
        "Roster updated and validated successfully."
      );
    } catch (error) {
      alert(error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleSearchChange = (event) => {
    setSearch(event.target.value);
    setPage(1);
  };

  const goPrevious = () => {
    setPage((current) =>
      Math.max(1, current - 1)
    );
  };

  const goNext = () => {
    setPage((current) =>
      Math.min(totalPages, current + 1)
    );
  };

  return (
    <div className="manual-roster-editor">
      {/* Header */}
      <div className="manual-editor-header">
        <div>
          <div className="manual-editor-eyebrow">
            MANUAL EDITING
          </div>

          <h2>Edit roster assignments</h2>

          <p>
            Reassign an employee and let the backend
            validate the change before it is committed.
          </p>
        </div>

        <div className="manual-editor-count">
          {filteredRoster.length.toLocaleString()} records
        </div>
      </div>

      {/* Search */}
      <div className="manual-editor-toolbar">
        <div className="manual-search">
          <Search size={17} />

          <input
            value={search}
            onChange={handleSearchChange}
            placeholder="Search employee, brand, process or date..."
          />

          {search && (
            <button
              className="manual-search-clear"
              onClick={() => {
                setSearch("");
                setPage(1);
              }}
              aria-label="Clear search"
            >
              <X size={15} />
            </button>
          )}
        </div>

        <div className="manual-editor-info">
          Showing{" "}
          <strong>
            {startIndex}-{endIndex}
          </strong>{" "}
          of{" "}
          <strong>
            {filteredRoster.length.toLocaleString()}
          </strong>
        </div>
      </div>

      {/* Table */}
      <div className="manual-table-wrapper">
        <table className="manual-roster-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Employee</th>
              <th>Pod</th>
              <th>Brand</th>
              <th>Process</th>
              <th>Type</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {paginatedRoster.length === 0 ? (
              <tr>
                <td
                  colSpan="7"
                  className="manual-empty"
                >
                  No roster records match your search.
                </td>
              </tr>
            ) : (
              paginatedRoster.map((row) => (
                <tr key={row.id}>
                  <td className="date-cell">
                    {row.roster_date}
                  </td>

                  <td className="employee-cell">
                    {editingId === row.id ? (
                      <select
                        value={selectedEmployee}
                        onChange={(event) =>
                          setSelectedEmployee(
                            event.target.value
                          )
                        }
                        disabled={saving}
                        className="employee-select"
                      >
                        <option value="">
                          Select employee
                        </option>

                        {employees.map(
                          (employee) => (
                            <option
                              key={employee.id}
                              value={employee.id}
                            >
                              {employee.employee_code}
                              {" — "}
                              {employee.name}
                            </option>
                          )
                        )}
                      </select>
                    ) : (
                      <div className="employee-name">
                        {row.employee_name}
                      </div>
                    )}
                  </td>

                  <td>
                    {row.pod_id ?? "-"}
                  </td>

                  <td>
                    <span className="brand-text">
                      {row.brand_name}
                    </span>
                  </td>

                  <td>
                    <span className="process-text">
                      {row.process_name}
                    </span>
                  </td>

                  <td>
                    <span
                      className={`assignment-badge ${
                        row.assignment_type ===
                        "PRIMARY"
                          ? "primary"
                          : "backup"
                      }`}
                    >
                      {row.assignment_type}
                    </span>
                  </td>

                  <td className="action-cell">
                    {editingId === row.id ? (
                      <div className="edit-actions">
                        <button
                          className="save-edit-button"
                          onClick={() =>
                            saveEdit(row)
                          }
                          disabled={saving}
                        >
                          <Check size={14} />

                          {saving
                            ? "Saving..."
                            : "Save"}
                        </button>

                        <button
                          className="cancel-edit-button"
                          onClick={cancelEdit}
                          disabled={saving}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        className="edit-row-button"
                        onClick={() =>
                          startEdit(row)
                        }
                      >
                        <Pencil size={14} />
                        Edit
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {filteredRoster.length > 0 && (
        <div className="manual-pagination">
          <button
            onClick={goPrevious}
            disabled={safePage === 1}
          >
            <ChevronLeft size={16} />
            Previous
          </button>

          <div className="page-indicator">
            Page{" "}
            <strong>{safePage}</strong>{" "}
            of{" "}
            <strong>{totalPages}</strong>
          </div>

          <button
            onClick={goNext}
            disabled={safePage === totalPages}
          >
            Next
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}