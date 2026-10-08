import { useEffect, useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { fmt } from "../../shared/format";
import { PermissionNotice } from "../../shared/PermissionNotice";
import { csvFilename } from "../../shared/csv";
import { Card, ErrorBox, ExportButton, Field, Pill, Spinner, Toggle } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { Employee, PayrollOptions } from "../../shared/types";

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
  const options = useAsync(() => api.payrollOptions(), []);
  const expenseAccounts = useAsync(() => api.accounts({ account_type: "Expense" }), []);

  const [draft, setDraft] = useState<Employee | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeOnly, setActiveOnly] = useState(false);
  const [managing, setManaging] = useState(false);
  const [optDraft, setOptDraft] = useState<PayrollOptions | null>(null);
  const [savingOptions, setSavingOptions] = useState(false);

  const departments = options.data?.departments ?? [];
  const designations = options.data?.designations ?? [];

  /**
   * Match a stored department value to a current option, case-insensitively.
   * Old records say "office"; the option says "Office" — both mean the same.
   */
  const deptName = (value: string): string => {
    const found = departments.find((d) => d.name.toLowerCase() === value.toLowerCase());
    return found ? found.name : (departments[0]?.name ?? value);
  };

  useEffect(() => {
    setError(null);
  }, [draft]);

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
    if (!draft) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const existing = (employees.data ?? []).some((row) => row.code === draft.code);
      const payload = { ...draft, gross_salary: draft.gross_salary || "0" };
      if (existing) await api.updateEmployee(draft.code, payload);
      else await api.createEmployee(payload);
      setMessage(existing ? "Employee updated." : "Employee added.");
      setDraft(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setSaving(false);
    }
  }

  /** Open the options editor with a private copy of the current lists. */
  function openManage() {
    if (!options.data) return;
    setOptDraft(JSON.parse(JSON.stringify(options.data)) as PayrollOptions);
    setManaging(true);
    setError(null);
  }

  async function saveOptions() {
    if (!optDraft) return;
    setSavingOptions(true);
    setError(null);
    setMessage(null);
    try {
      const departments = optDraft.departments
        .map((d) => ({ name: d.name.trim(), salary_account: d.salary_account }))
        .filter((d) => d.name);
      const designations = optDraft.designations
        .map((name) => name.trim())
        .filter(Boolean);
      if (departments.length === 0) throw new Error("At least one department is required.");
      if (designations.length === 0) throw new Error("At least one designation is required.");
      await api.updatePayrollOptions({ departments, designations });
      setManaging(false);
      setOptDraft(null);
      setMessage("Options updated.");
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setSavingOptions(false);
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

      {canWrite && draft && (
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
                value={deptName(draft.department)}
                onChange={(event) =>
                  setDraft({ ...draft, department: event.target.value })
                }
              >
                {departments.map((d) => (
                  <option key={d.name} value={d.name}>
                    {d.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="form-row" style={{ marginBottom: 14 }}>
            <Field label="Designation">
              <select
                value={draft.designation ?? ""}
                onChange={(event) =>
                  setDraft({ ...draft, designation: event.target.value || null })
                }
              >
                <option value="">—</option>
                {designations.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
                {draft.designation &&
                  !designations.some(
                    (name) => name.toLowerCase() === draft.designation!.toLowerCase(),
                  ) && (
                    <option value={draft.designation}>
                      {draft.designation} (no longer listed)
                    </option>
                  )}
              </select>
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
              <Toggle
                checked={draft.is_active}
                labelOn="Active"
                labelOff="Resigned"
                ariaLabel="Employment status"
                onChange={(next) =>
                  setDraft({
                    ...draft,
                    is_active: next,
                    // Leaving is dated today unless the user says otherwise, and
                    // cleared when someone comes back.
                    left_on: next ? null : (draft.left_on ?? today()),
                  })
                }
              />
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
            <button onClick={() => setDraft(null)}>Cancel</button>
          </div>
        </Card>
      )}

      {canWrite && managing && optDraft && (
        <Card
          title="Department and designation options"
          subtitle="These fill the dropdowns on the employee form. Each department carries the account its salaries are charged to."
        >
          {options.loading && <Spinner />}
          {options.error && <ErrorBox message={options.error} />}
          <h3 className="small muted" style={{ margin: "0 0 8px" }}>
            Departments
          </h3>
          {optDraft.departments.map((dept, index) => (
            <div className="form-row" style={{ marginBottom: 8 }} key={index}>
              <Field label="Name">
                <input
                  value={dept.name}
                  onChange={(event) => {
                    const next = [...optDraft.departments];
                    next[index] = { ...next[index], name: event.target.value };
                    setOptDraft({ ...optDraft, departments: next });
                  }}
                />
              </Field>
              <Field label="Salary account">
                <select
                  value={dept.salary_account}
                  onChange={(event) => {
                    const next = [...optDraft.departments];
                    next[index] = { ...next[index], salary_account: event.target.value };
                    setOptDraft({ ...optDraft, departments: next });
                  }}
                >
                  {(expenseAccounts.data ?? []).map((account) => (
                    <option key={account.code} value={account.code}>
                      {account.code} — {account.name_en}
                    </option>
                  ))}
                  {!(expenseAccounts.data ?? []).some(
                    (account) => account.code === dept.salary_account,
                  ) && (
                    <option value={dept.salary_account}>
                      {dept.salary_account} (not an expense account)
                    </option>
                  )}
                </select>
              </Field>
              <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 2 }}>
                <button
                  onClick={() =>
                    setOptDraft({
                      ...optDraft,
                      departments: optDraft.departments.filter((_, i) => i !== index),
                    })
                  }
                  disabled={optDraft.departments.length <= 1}
                  title={
                    optDraft.departments.length <= 1
                      ? "At least one department is required"
                      : "Remove this department"
                  }
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
          <button
            style={{ marginBottom: 16 }}
            onClick={() =>
              setOptDraft({
                ...optDraft,
                departments: [
                  ...optDraft.departments,
                  { name: "", salary_account: expenseAccounts.data?.[0]?.code ?? "" },
                ],
              })
            }
          >
            Add department
          </button>

          <h3 className="small muted" style={{ margin: "0 0 8px" }}>
            Designations
          </h3>
          {optDraft.designations.map((name, index) => (
            <div className="form-row" style={{ marginBottom: 8 }} key={index}>
              <Field label="Title">
                <input
                  value={name}
                  onChange={(event) => {
                    const next = [...optDraft.designations];
                    next[index] = event.target.value;
                    setOptDraft({ ...optDraft, designations: next });
                  }}
                />
              </Field>
              <div style={{ display: "flex", alignItems: "flex-end", paddingBottom: 2 }}>
                <button
                  onClick={() =>
                    setOptDraft({
                      ...optDraft,
                      designations: optDraft.designations.filter((_, i) => i !== index),
                    })
                  }
                  disabled={optDraft.designations.length <= 1}
                  title={
                    optDraft.designations.length <= 1
                      ? "At least one designation is required"
                      : "Remove this designation"
                  }
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
          <button
            style={{ marginBottom: 16 }}
            onClick={() =>
              setOptDraft({ ...optDraft, designations: [...optDraft.designations, ""] })
            }
          >
            Add designation
          </button>

          <div className="row-actions">
            <button className="primary" onClick={saveOptions} disabled={savingOptions}>
              {savingOptions ? "Saving…" : "Save options"}
            </button>
            <button
              onClick={() => {
                setManaging(false);
                setOptDraft(null);
              }}
            >
              Cancel
            </button>
          </div>
        </Card>
      )}

      <Card
        title="Staff"
        subtitle={
          resigned > 0
            ? `${resigned} resigned · select a row to edit`
            : "Select a row to edit"
        }
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            {canWrite && (
              <button className="primary" onClick={() => setDraft({ ...BLANK, department: deptName(BLANK.department) })}>
                Add employee
              </button>
            )}
            {canWrite && options.data && (
              <button onClick={openManage}>Manage options</button>
            )}
            <ExportButton
              filename={csvFilename("staff")}
              rows={rows}
              columns={[
                { header: "Code", value: (row) => row.code },
                { header: "Name", value: (row) => row.name },
                { header: "Designation", value: (row) => row.designation },
                { header: "Department", value: (row) => row.department },
                { header: "Joining date", value: (row) => row.joining_date },
                { header: "Leaving date", value: (row) => row.left_on },
                { header: "Mobile", value: (row) => row.mobile },
                { header: "Personal email", value: (row) => row.email },
                { header: "Gross salary", value: (row) => row.gross_salary },
                { header: "Status", value: (row) => (row.is_active ? "active" : "resigned") },
              ]}
            />
          </div>
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
                  <th />
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
                    <td>
                      {canWrite && <button onClick={() => setDraft(row)}>Edit</button>}
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
