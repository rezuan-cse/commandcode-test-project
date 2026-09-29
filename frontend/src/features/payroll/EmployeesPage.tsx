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
  is_active: true,
};

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

  return (
    <>
      <h1>Employees</h1>
      <p className="page-intro">
        The salary structure is not stored on the employee: gross pay is split into its
        components and deductions by the rules in Configuration, so a change to the structure
        applies everywhere without editing every record.
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

      <Card title="Staff" subtitle="Select a row to edit">
        {employees.loading && <Spinner />}
        {employees.error && <ErrorBox message={employees.error} />}
        {employees.data && employees.data.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            No employees yet.
          </p>
        )}
        {employees.data && employees.data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Department</th>
                  <th>Designation</th>
                  <th className="numeric">Gross</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {employees.data.map((row) => (
                  <tr
                    key={row.code}
                    onClick={() => canWrite && setDraft(row)}
                    style={canWrite ? { cursor: "pointer" } : undefined}
                  >
                    <td className="name-cell">{row.code}</td>
                    <td>{row.name}</td>
                    <td>{row.department}</td>
                    <td className="muted small">{row.designation ?? "—"}</td>
                    <td className="numeric">{fmt(row.gross_salary)}</td>
                    <td>
                      <Pill tone={row.is_active ? "positive" : "warn"}>
                        {row.is_active ? "active" : "inactive"}
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
