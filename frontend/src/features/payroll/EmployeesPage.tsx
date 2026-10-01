import { useEffect, useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { fmt } from "../../shared/format";
import { PermissionNotice } from "../../shared/PermissionNotice";
import { Card, ErrorBox, Field, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { Employee } from "../../shared/types";

/** An empty draft, used to tell "adding" from "editing" apart. */
const BLANK: Employee = {
  code: "",
  name: "",
  email: "",
  designation: "",
  department: "office",
  joining_date: null,
  bank_account: "",
  mobile: "",
  gross_salary: "0",
  left_on: null,
  is_active: true,
};

/** Today on the reader's own clock, which is what they mean by "today". */
function today(): string {
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export default function EmployeesPage() {
  const { user, can, level } = useAuth();
  const { refresh } = useDemo();
  const canWrite = can("payroll", true);
  const canRead = can("payroll");
  const employees = useAsync(() => api.employees(), []);

  const [draft, setDraft] = useState<Employee>(BLANK);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeOnly, setActiveOnly] = useState(false);

  useEffect(() => {
    setError(null);
  }, [draft.code]);

  if (!canRead) {
    return (
      <>
        <h1>Employees</h1>
        <PermissionNotice
          role={user?.role ?? ""}
          resource="payroll"
          write={false}
          level={level("payroll")}
        />
      </>
    );
  }

  async function save() {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const existing = (employees.data ?? []).some((row) => row.code === draft.code);
      const payload = { ...draft, gross_salary: draft.gross_salary || "0" };
      if (existing) await api.updateEmployee(draft.code, payload);
      else await api.createEmployee(payload);
      setMessage(existing ? "Employee updated." : "Employee added.");
      setDraft(BLANK);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setSaving(false);
    }
  }

  const rows = (employees.data ?? []).filter((row) => !activeOnly || row.is_active);
  const resigned = (employees.data ?? []).filter((row) => !row.is_active).length;

  return (
    <>
      <h1>Employees</h1>
      <p className="page-intro">
        The salary structure is not stored on the employee: gross pay is split into its
        components and deductions by the rules in Configuration, so a change to the structure
        applies everywhere without editing every record.
      </p>
      <p className="page-intro">
        <strong>When someone leaves</strong>, select their row, switch the status to
        <em> Resigned</em> and save. They stay on the list with their joining and leaving
        dates and keep every payslip they were paid; payroll simply stops including them.
        Nothing is deleted, and marking them active again brings them back.
      </p>

      {message && <div className="toast">✓ {message}</div>}
      {error && <ErrorBox message={error} />}

      {canWrite && (
        <Card title={draft.code ? `Edit ${draft.code}` : "Add an employee"}>
          <div className="form-row" style={{ marginBottom: 14 }}>
            <Field label="Code">
              <input
                value={draft.code}
                disabled={Boolean(
                  (employees.data ?? []).some((row) => row.code === draft.code),
                )}
                onChange={(event) => setDraft({ ...draft, code: event.target.value })}
              />
            </Field>
            <Field label="Name">
              <input
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
              />
            </Field>
            <Field label="Department">
              <select
                value={draft.department}
                onChange={(event) =>
                  setDraft({ ...draft, department: event.target.value as Employee["department"] })
                }
              >
                <option value="office">Office</option>
                <option value="factory">Factory</option>
              </select>
            </Field>
          </div>
          <div className="form-row" style={{ marginBottom: 14 }}>
            <Field label="Designation">
              <input
                value={draft.designation ?? ""}
                onChange={(event) => setDraft({ ...draft, designation: event.target.value })}
              />
            </Field>
            <Field label="Personal email">
              <input
                value={draft.email ?? ""}
                onChange={(event) => setDraft({ ...draft, email: event.target.value })}
              />
            </Field>
            <Field label="Mobile">
              <input
                value={draft.mobile ?? ""}
                onChange={(event) => setDraft({ ...draft, mobile: event.target.value })}
              />
            </Field>
          </div>
          <div className="form-row" style={{ marginBottom: 14 }}>
            <Field label="Joining date">
              <input
                type="date"
                value={draft.joining_date ?? ""}
                onChange={(event) =>
                  setDraft({ ...draft, joining_date: event.target.value || null })
                }
              />
            </Field>
            <Field label="Bank account">
              <input
                value={draft.bank_account ?? ""}
                onChange={(event) => setDraft({ ...draft, bank_account: event.target.value })}
              />
            </Field>
            <Field label="Gross salary">
              <input
                inputMode="decimal"
                value={draft.gross_salary}
                onChange={(event) => setDraft({ ...draft, gross_salary: event.target.value })}
              />
            </Field>
          </div>
          <div className="form-row" style={{ marginBottom: 14 }}>
            <Field label="Status">
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={draft.is_active}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      is_active: event.target.checked,
                      // Leaving is dated today unless the user says otherwise, and
                      // cleared when someone comes back.
                      left_on: event.target.checked ? null : (draft.left_on ?? today()),
                    })
                  }
                />
                <span>{draft.is_active ? "Active" : "Resigned"}</span>
              </label>
            </Field>
            {!draft.is_active && (
              <Field label="Leaving date" hint="Kept on the record">
                <input
                  type="date"
                  value={draft.left_on ?? ""}
                  onChange={(event) =>
                    setDraft({ ...draft, left_on: event.target.value || null })
                  }
                />
              </Field>
            )}
          </div>
          <div className="row-actions">
            <button className="primary" onClick={save} disabled={saving || !draft.code || !draft.name}>
              {saving ? "Saving…" : "Save employee"}
            </button>
            {draft.code && (
              <button onClick={() => setDraft(BLANK)}>New</button>
            )}
          </div>
        </Card>
      )}

      <Card
        title="Staff"
        subtitle={
          resigned > 0
            ? `Select a row to edit · ${resigned} resigned`
            : "Select a row to edit"
        }
      >
        <label className="check-row" style={{ marginBottom: 12 }}>
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(event) => setActiveOnly(event.target.checked)}
          />
          <span>Show active staff only</span>
        </label>
        {employees.loading && <Spinner />}
        {employees.error && <ErrorBox message={employees.error} />}
        {employees.data && employees.data.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            No employees yet.
          </p>
        )}
        {employees.data && employees.data.length > 0 && rows.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            No active staff. Untick the box above to see everyone, including those
            who have resigned.
          </p>
        )}
        {rows.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Department</th>
                  <th>Designation</th>
                  <th>Joining date</th>
                  <th>Leaving date</th>
                  <th>Mobile</th>
                  <th className="numeric">Gross</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.code}
                    onClick={() => canWrite && setDraft(row)}
                    style={canWrite ? { cursor: "pointer" } : undefined}
                  >
                    <td className="name-cell">{row.code}</td>
                    <td>{row.name}</td>
                    <td>{row.department}</td>
                    <td className="muted small">{row.designation ?? "—"}</td>
                    <td className="muted small">{row.joining_date ?? "—"}</td>
                    <td className="muted small">{row.left_on ?? "—"}</td>
                    <td className="muted small">{row.mobile ?? "—"}</td>
                    <td className="numeric">{fmt(row.gross_salary)}</td>
                    <td>
                      <Pill tone={row.is_active ? "positive" : "warn"}>
                        {row.is_active ? "active" : "resigned"}
                      </Pill>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
