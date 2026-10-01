import { useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { PermissionNotice } from "../../shared/PermissionNotice";
import { csvFilename } from "../../shared/csv";
import { Card, ErrorBox, ExportButton, Field, Pill, Spinner, Toggle } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { Party, PartyKind } from "../../shared/types";

const KINDS: PartyKind[] = ["Customer", "Supplier", "Customer and Supplier"];

interface PartyDraft {
  code: string;
  name: string;
  kind: PartyKind;
  contact_person: string;
  phone: string;
  email: string;
  address: string;
  credit_days: string;
  is_active: boolean;
  isNew: boolean;
}

const BLANK: PartyDraft = {
  code: "",
  name: "",
  kind: "Customer",
  contact_person: "",
  phone: "",
  email: "",
  address: "",
  credit_days: "",
  is_active: true,
  isNew: true,
};

export default function PartiesPage() {
  const { user, can, level } = useAuth();
  const { refresh } = useDemo();
  const canRead = can("parties");
  const canWrite = can("parties", true);
  const parties = useAsync(() => api.parties(), []);

  const [search, setSearch] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [activeOnly, setActiveOnly] = useState(false);
  const [draft, setDraft] = useState<PartyDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);

  if (!canRead) {
    return (
      <>
        <h1>Customers &amp; Suppliers</h1>
        <PermissionNotice
          role={user?.role ?? ""}
          resource="parties"
          write={false}
          level={level("parties")}
        />
      </>
    );
  }

  const needle = search.trim().toLowerCase();
  const rows = (parties.data ?? []).filter((party) => {
    if (activeOnly && !party.is_active) return false;
    // A partner marked "both" answers either question, so a customer filter has
    // to include the firms that also supply.
    if (kindFilter && party.kind !== kindFilter && party.kind !== "Customer and Supplier") {
      return false;
    }
    if (!needle) return true;
    return (
      party.name.toLowerCase().includes(needle) ||
      party.code.toLowerCase().includes(needle)
    );
  });

  function startAdd() {
    setError(null);
    setMessage(null);
    setDraft({ ...BLANK });
  }

  function startEdit(party: Party) {
    setError(null);
    setMessage(null);
    setDraft({
      code: party.code,
      name: party.name,
      kind: party.kind,
      contact_person: party.contact_person ?? "",
      phone: party.phone ?? "",
      email: party.email ?? "",
      address: party.address ?? "",
      credit_days: party.credit_days === null ? "" : String(party.credit_days),
      is_active: party.is_active,
      isNew: false,
    });
  }

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const details = {
        name: draft.name,
        kind: draft.kind,
        contact_person: draft.contact_person || null,
        phone: draft.phone || null,
        email: draft.email || null,
        address: draft.address || null,
        credit_days: draft.credit_days === "" ? null : Number(draft.credit_days),
        is_active: draft.is_active,
      };
      if (draft.isNew) {
        const created = await api.createParty({ ...details, code: draft.code });
        setMessage(`${created.name} added.`);
      } else {
        await api.updateParty(draft.code, details);
        setMessage(`${draft.code} saved.`);
      }
      setDraft(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!draft || draft.isNew) return;
    setSaving(true);
    setError(null);
    try {
      const result = await api.deleteParty(draft.code);
      setMessage(result.message);
      setDraft(null);
      refresh();
    } catch (caught) {
      // Refused once a transaction names the record; the message says to
      // deactivate instead, so it is shown rather than replaced.
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setSaving(false);
    }
  }

  async function importExisting() {
    setImporting(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.importParties();
      setMessage(
        result.created === 0
          ? `Nothing new to adopt — all ${result.already_known} name(s) already have a record.`
          : `Adopted ${result.created} partner(s) from existing records and linked ` +
            `${result.linked} transaction(s).`,
      );
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setImporting(false);
    }
  }

  return (
    <>
      <h1>Customers &amp; Suppliers</h1>
      <p className="page-intro">
        One list of the firms you trade with. A partner is often both a customer and a
        supplier, which is why it is a single list with a type rather than two separate
        ones. Sales and purchases pick from here, so the same firm cannot end up
        recorded twice under two spellings of its name.
      </p>

      {message && <div className="toast">✓ {message}</div>}
      {error && <ErrorBox message={error} />}

      {canWrite && (
        <Card
          title="Already trading with these firms?"
          subtitle="Adopt the customer and supplier names already on your posted transactions"
          actions={
            <button className="primary" onClick={importExisting} disabled={importing}>
              {importing ? "Adopting…" : "Adopt existing names"}
            </button>
          }
        >
          <p className="small muted" style={{ marginTop: 0 }}>
            Names typed on sales and purchases before this list existed are your real
            trading partners, so they are adopted as records rather than retyped — and
            each one then claims the transactions that carry its name. Safe to press
            again: names that already have a record are left alone. Nothing is created
            twice.
          </p>
        </Card>
      )}

      {canWrite && draft && (
        <PartyForm
          draft={draft}
          saving={saving}
          canDelete={!draft.isNew}
          onChange={setDraft}
          onSave={save}
          onDelete={remove}
          onCancel={() => setDraft(null)}
        />
      )}

      <Card
        title="The list"
        subtitle={
          parties.data
            ? `${rows.length} shown · ${rows.filter((row) => !row.is_active).length} inactive`
            : undefined
        }
        actions={
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="search"
              placeholder="Search name or code…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              style={{ width: 190 }}
            />
            <select
              value={kindFilter}
              onChange={(event) => setKindFilter(event.target.value)}
              style={{ width: 150 }}
            >
              <option value="">All types</option>
              {KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {kind}
                </option>
              ))}
            </select>
            <label className="check-row" style={{ whiteSpace: "nowrap" }}>
              <input
                type="checkbox"
                checked={activeOnly}
                onChange={(event) => setActiveOnly(event.target.checked)}
              />
              <span>Active only</span>
            </label>
            {canWrite && (
              <button className="primary" onClick={startAdd}>
                Add customer or supplier
              </button>
            )}
            <ExportButton
              filename={csvFilename("customers-and-suppliers")}
              rows={rows}
              columns={[
                { header: "Code", value: (row) => row.code },
                { header: "Name", value: (row) => row.name },
                { header: "Type", value: (row) => row.kind },
                { header: "Contact", value: (row) => row.contact_person },
                { header: "Phone", value: (row) => row.phone },
                { header: "Email", value: (row) => row.email },
                { header: "Address", value: (row) => row.address },
                { header: "Credit days", value: (row) => row.credit_days },
                { header: "Status", value: (row) => (row.is_active ? "active" : "inactive") },
              ]}
            />
          </div>
        }
      >
        {parties.loading && <Spinner />}
        {parties.error && <ErrorBox message={parties.error} />}
        {parties.data && parties.data.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            Nothing here yet. Add your first customer or supplier above, or adopt the
            names already on your transactions.
          </p>
        )}
        {parties.data && parties.data.length > 0 && rows.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            No record matches the filter. Clear the search or set the type back to
            “All types”.
          </p>
        )}
        {rows.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Contact</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th className="numeric">Credit days</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((party) => (
                  <tr key={party.code}>
                    <td className="name-cell">{party.code}</td>
                    <td>{party.name}</td>
                    <td>
                      <Pill tone={party.kind === "Supplier" ? "info" : "neutral"}>
                        {party.kind === "Customer and Supplier" ? "both" : party.kind}
                      </Pill>
                    </td>
                    <td className="muted small">{party.contact_person ?? "—"}</td>
                    <td className="muted small">{party.phone ?? "—"}</td>
                    <td className="muted small">{party.email ?? "—"}</td>
                    <td className="numeric">
                      {party.credit_days === null ? "—" : party.credit_days}
                    </td>
                    <td>
                      <Pill tone={party.is_active ? "positive" : "warn"}>
                        {party.is_active ? "active" : "inactive"}
                      </Pill>
                    </td>
                    <td>
                      {canWrite && <button onClick={() => startEdit(party)}>Edit</button>}
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

function PartyForm({
  draft,
  saving,
  canDelete,
  onChange,
  onSave,
  onDelete,
  onCancel,
}: {
  draft: PartyDraft;
  saving: boolean;
  canDelete: boolean;
  onChange: (draft: PartyDraft) => void;
  onSave: () => void;
  onDelete: () => void;
  onCancel: () => void;
}) {
  return (
    <Card
      title={draft.isNew ? "New customer or supplier" : `Edit ${draft.code}`}
      subtitle={
        draft.isNew
          ? "The code is how transactions will refer to this firm, so choose it carefully"
          : "The code is fixed: posted transactions point at it"
      }
      actions={<button onClick={onCancel}>Cancel</button>}
    >
      <div className="form-row">
        <Field label="Code">
          <input
            value={draft.code}
            disabled={!draft.isNew}
            placeholder="e.g. CUS-004"
            onChange={(event) => onChange({ ...draft, code: event.target.value })}
          />
        </Field>
        <Field label="Name">
          <input
            value={draft.name}
            onChange={(event) => onChange({ ...draft, name: event.target.value })}
          />
        </Field>
        <Field label="Type">
          <select
            value={draft.kind}
            onChange={(event) =>
              onChange({ ...draft, kind: event.target.value as PartyKind })
            }
          >
            {KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="form-row">
        <Field label="Contact person">
          <input
            value={draft.contact_person}
            onChange={(event) => onChange({ ...draft, contact_person: event.target.value })}
          />
        </Field>
        <Field label="Phone">
          <input
            value={draft.phone}
            onChange={(event) => onChange({ ...draft, phone: event.target.value })}
          />
        </Field>
        <Field label="Email">
          <input
            value={draft.email}
            onChange={(event) => onChange({ ...draft, email: event.target.value })}
          />
        </Field>
      </div>

      <div className="form-row">
        <Field label="Address">
          <input
            value={draft.address}
            onChange={(event) => onChange({ ...draft, address: event.target.value })}
          />
        </Field>
        <Field label="Credit days" hint="Blank means no terms were agreed">
          <input
            className="numeric"
            inputMode="numeric"
            value={draft.credit_days}
            placeholder="0 = pay on delivery"
            onChange={(event) => onChange({ ...draft, credit_days: event.target.value })}
          />
        </Field>
        <Field label="Active" hint="Inactive records stay in the history but leave the pickers">
          <Toggle
            checked={draft.is_active}
            labelOn="Active"
            labelOff="Inactive"
            ariaLabel="Record active"
            onChange={(next) => onChange({ ...draft, is_active: next })}
          />
        </Field>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          className="primary"
          onClick={onSave}
          disabled={saving || !draft.code.trim() || !draft.name.trim()}
        >
          {saving ? "Saving…" : draft.isNew ? "Add record" : "Save record"}
        </button>
        {canDelete && (
          <button onClick={onDelete} disabled={saving}>
            Delete
          </button>
        )}
      </div>
    </Card>
  );
}
