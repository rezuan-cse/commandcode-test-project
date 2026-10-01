import { useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { fmt, fmtQty } from "../../shared/format";
import { csvFilename } from "../../shared/csv";
import { Card, Empty, ErrorBox, ExportButton, Field, Pill, Spinner, Toggle } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { BomExplosion, Item } from "../../shared/types";

/** The item classifications the system understands, in the order a user expects. */
const CATEGORIES = [
  "Raw Material",
  "WIP",
  "Finished Good",
  "Packaging",
  "Trading Stock",
  "Imported Goods",
];

/** Business segments carried by every item and account. */
const SEGMENTS = [
  "Import",
  "Manufacturing",
  "Packaging",
  "Trading",
  "Application",
  "Shared",
];

interface ItemDraft {
  code: string;
  name: string;
  category: string;
  segment: string;
  uom: string;
  reorder_level: string;
  is_active: boolean;
  isNew: boolean;
}

const BLANK: ItemDraft = {
  code: "",
  name: "",
  category: "Raw Material",
  segment: "Shared",
  uom: "kg",
  reorder_level: "",
  is_active: true,
  isNew: true,
};

export default function InventoryPage() {
  const { can } = useAuth();
  const { refresh } = useDemo();
  const canWrite = can("items_bom", true);
  const items = useAsync(() => api.items(), []);
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState<ItemDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function startAdd() {
    setError(null);
    setMessage(null);
    setDraft({ ...BLANK });
  }

  function startEdit(item: Item) {
    setError(null);
    setMessage(null);
    setDraft({
      code: item.code,
      name: item.name,
      category: item.category,
      segment: item.segment,
      uom: item.uom,
      reorder_level: item.reorder_level ?? "",
      is_active: item.is_active,
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
        category: draft.category,
        segment: draft.segment,
        uom: draft.uom,
        // Blank stays blank: "not watched" is a real answer, and is not a level of
        // zero, which would put the item on the reorder list as soon as it emptied.
        reorder_level: draft.reorder_level === "" ? null : draft.reorder_level,
        is_active: draft.is_active,
      };
      if (draft.isNew) {
        const created = await api.createItem({ ...details, code: draft.code });
        setMessage(`Item ${created.code} added.`);
      } else {
        await api.updateItem(draft.code, details);
        setMessage(`Item ${draft.code} saved.`);
      }
      setDraft(null);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!draft || draft.isNew) return;
    setSaving(true);
    setError(null);
    try {
      const result = await api.deleteItem(draft.code);
      setMessage(result.message);
      setDraft(null);
      refresh();
    } catch (e) {
      // The server refuses once the item has any history, and its message says
      // to deactivate instead — so it is shown rather than replaced.
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  const filtered = (items.data ?? []).filter((item) => {
    if (!search) return true;
    const needle = search.toLowerCase();
    return item.code.toLowerCase().includes(needle) || item.name.toLowerCase().includes(needle);
  });

  const stockValue = filtered.reduce((total, item) => total + Number(item.value_on_hand), 0);

  return (
    <>
      <h1>Inventory &amp; BOM</h1>
      <p className="page-intro">
        Quantity on hand and average cost are computed fields, derived from the stock ledger.
        They are never typed in by a user, which is what stops the stock sheet drifting away
        from the accounts.
      </p>

      {(error || message) && (
        <div style={{ marginBottom: 16 }}>
          {error && <ErrorBox message={error} />}
          {message && !error && <div className="notice">{message}</div>}
        </div>
      )}

      {draft && (
        <ItemForm
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
        title="Inventory ledger"
        subtitle="Every movement, with its running balance and average cost"
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="search"
              placeholder="Search item…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              style={{ width: 200 }}
            />
            {canWrite && (
              <button className="primary" onClick={startAdd}>
                Add item
              </button>
            )}
            <ExportButton
              filename={csvFilename("inventory")}
              rows={filtered}
              columns={[
                { header: "Code", value: (row) => row.code },
                { header: "Item", value: (row) => row.name },
                { header: "Category", value: (row) => row.category },
                { header: "Segment", value: (row) => row.segment },
                { header: "Unit", value: (row) => row.uom },
                { header: "Qty on hand", value: (row) => row.qty_on_hand },
                { header: "Avg cost", value: (row) => row.avg_cost },
                { header: "Value", value: (row) => row.value_on_hand },
                { header: "Active", value: (row) => (row.is_active ? "yes" : "no") },
              ]}
            />
          </div>
        }
      >
        {items.loading && <Spinner />}
        {items.error && <ErrorBox message={items.error} />}
        {items.data && (
          <>
            <p className="small muted" style={{ marginTop: 0 }}>
              {filtered.length} items shown · total stock value {fmt(stockValue.toFixed(2))}
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Item</th>
                    <th>Category</th>
                    <th>Segment</th>
                    <th>Unit</th>
                    <th className="numeric">Qty on hand</th>
                    <th className="numeric">Avg cost</th>
                    <th className="numeric">Value</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((item) => (
                    <tr key={item.code}>
                      <td className="numeric" style={{ textAlign: "left" }}>
                        {item.code}
                        {!item.is_active && (
                          <>
                            {" "}
                            <Pill tone="warn">inactive</Pill>
                          </>
                        )}
                        {item.reorder_level !== null &&
                          Number(item.qty_on_hand) <= Number(item.reorder_level) && (
                            <>
                              {" "}
                              <Pill tone="negative">reorder</Pill>
                            </>
                          )}
                      </td>
                      <td className="name-cell">{item.name}</td>
                      <td>{item.category}</td>
                      <td>{item.segment}</td>
                      <td>{item.uom}</td>
                      <td className="numeric">{fmtQty(item.qty_on_hand)}</td>
                      <td className="numeric">{fmt(item.avg_cost, 4)}</td>
                      <td className="numeric">{fmt(item.value_on_hand)}</td>
                      <td>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button onClick={() => setSelected(item.code)}>Ledger</button>
                          {canWrite && <button onClick={() => startEdit(item)}>Edit</button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>

      {selected && <ItemDetail code={selected} onClose={() => setSelected(null)} />}
    </>
  );
}

function ItemForm({
  draft,
  saving,
  canDelete,
  onChange,
  onSave,
  onDelete,
  onCancel,
}: {
  draft: ItemDraft;
  saving: boolean;
  canDelete: boolean;
  onChange: (draft: ItemDraft) => void;
  onSave: () => void;
  onDelete: () => void;
  onCancel: () => void;
}) {
  return (
    <Card
      title={draft.isNew ? "New item" : `Edit ${draft.code}`}
      subtitle={
        draft.isNew
          ? "The code is how every other record refers to this item, so choose it carefully"
          : "Quantity and average cost are not edited here — they come from the stock ledger"
      }
      actions={<button onClick={onCancel}>Cancel</button>}
    >
      <div className="form-row">
        <Field label="Code">
          <input
            value={draft.code}
            disabled={!draft.isNew}
            placeholder="e.g. RMC-004"
            onChange={(event) => onChange({ ...draft, code: event.target.value })}
          />
        </Field>
        <Field label="Name">
          <input
            value={draft.name}
            onChange={(event) => onChange({ ...draft, name: event.target.value })}
          />
        </Field>
        <Field label="Unit">
          <input
            value={draft.uom}
            placeholder="kg, litre, pcs"
            onChange={(event) => onChange({ ...draft, uom: event.target.value })}
          />
        </Field>
      </div>

      <div className="form-row">
        <Field label="Category">
          <select
            value={draft.category}
            onChange={(event) => onChange({ ...draft, category: event.target.value })}
          >
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Segment">
          <select
            value={draft.segment}
            onChange={(event) => onChange({ ...draft, segment: event.target.value })}
          >
            {SEGMENTS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Reorder level"
          hint="Leave blank not to watch this item; it appears on the Low Stock report at or below the level"
        >
          <input
            className="numeric"
            inputMode="decimal"
            value={draft.reorder_level}
            placeholder="blank = not watched"
            onChange={(event) =>
              onChange({ ...draft, reorder_level: event.target.value })
            }
          />
        </Field>
        <Field label="Active" hint="Inactive items stay in the history but leave the pickers">
          <Toggle
            checked={draft.is_active}
            labelOn="Active"
            labelOff="Inactive"
            ariaLabel="Item active"
            onChange={(next) => onChange({ ...draft, is_active: next })}
          />
        </Field>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          className="primary"
          onClick={onSave}
          disabled={
            saving || !draft.code.trim() || !draft.name.trim() || !draft.uom.trim()
          }
        >
          {saving ? "Saving…" : draft.isNew ? "Add item" : "Save item"}
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

function ItemDetail({ code, onClose }: { code: string; onClose: () => void }) {
  const ledger = useAsync(() => api.inventory(code), [code]);
  const [qty, setQty] = useState("50");
  const [explosion, setExplosion] = useState<BomExplosion | null>(null);
  const [explodeError, setExplodeError] = useState<string | null>(null);

  async function runExplode() {
    setExplodeError(null);
    try {
      setExplosion(await api.explode(code, qty));
    } catch (error) {
      setExplosion(null);
      setExplodeError(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <Card
      title={`${code} — stock ledger`}
      subtitle="Movements in the order they were recorded, showing how the running balance is built"
      actions={<button onClick={onClose}>Close</button>}
    >
      {ledger.loading && <Spinner />}
      {ledger.error && <ErrorBox message={ledger.error} />}
      {ledger.data && ledger.data.length === 0 && (
        <Empty message="No stock movements recorded for this item." />
      )}
      {ledger.data && ledger.data.length > 0 && (
        <div className="table-wrap" style={{ marginBottom: 20 }}>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Reference</th>
                <th className="numeric">In qty</th>
                <th className="numeric">In value</th>
                <th className="numeric">Out qty</th>
                <th className="numeric">Out value</th>
                <th className="numeric">Balance qty</th>
                <th className="numeric">Balance value</th>
                <th className="numeric">Avg cost</th>
              </tr>
            </thead>
            <tbody>
              {ledger.data.map((row) => (
                <tr key={row.id}>
                  <td>{row.movement_date}</td>
                  <td>
                    <Pill tone={row.in_qty !== "0.0000" ? "positive" : "warn"}>
                      {row.movement_type}
                    </Pill>
                  </td>
                  <td className="muted small">{row.reference ?? "—"}</td>
                  <td className="numeric">{Number(row.in_qty) ? fmtQty(row.in_qty) : "—"}</td>
                  <td className="numeric">{Number(row.in_value) ? fmt(row.in_value) : "—"}</td>
                  <td className="numeric">{Number(row.out_qty) ? fmtQty(row.out_qty) : "—"}</td>
                  <td className="numeric">{Number(row.out_value) ? fmt(row.out_value) : "—"}</td>
                  <td className="numeric">{fmtQty(row.balance_qty)}</td>
                  <td className="numeric">{fmt(row.balance_value)}</td>
                  <td className="numeric">{fmt(row.avg_cost, 8)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 style={{ marginBottom: 8 }}>BOM explosion</h2>
      <p className="small muted" style={{ marginTop: 0 }}>
        Flattens the multi-stage bill of materials for a target production quantity. Components
        that are themselves manufactured are expanded through every stage down to purchased
        materials.
      </p>
      <div className="form-row" style={{ marginBottom: 12 }}>
        <label className="field" style={{ marginBottom: 0 }}>
          <span className="field-label">Target quantity</span>
          <input
            className="numeric"
            inputMode="decimal"
            value={qty}
            onChange={(event) => setQty(event.target.value)}
          />
        </label>
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button className="primary" onClick={runExplode}>
            Explode BOM
          </button>
        </div>
      </div>

      {explodeError && <ErrorBox message={explodeError} />}
      {explosion && <ExplosionTable explosion={explosion} />}
    </Card>
  );
}

function ExplosionTable({ explosion }: { explosion: BomExplosion }) {
  if (explosion.lines.length === 0) {
    return (
      <Empty
        message={`${explosion.parent_code} has no bill of materials defined, so there is nothing to explode.`}
      />
    );
  }
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Level</th>
            <th>Component</th>
            <th>Category</th>
            <th className="numeric">Per unit</th>
            <th className="numeric">Required</th>
            <th className="numeric">Avg cost</th>
            <th className="numeric">Estimated cost</th>
          </tr>
        </thead>
        <tbody>
          {explosion.lines.map((line) => (
            <tr key={`${line.item_code}-${line.level}`}>
              <td>{line.level}</td>
              <td className="name-cell">
                {line.item_code} — {line.item_name}
              </td>
              <td>{line.category}</td>
              <td className="numeric">{fmtQty(line.qty_per_unit)}</td>
              <td className="numeric">{fmtQty(line.qty_required)}</td>
              <td className="numeric">{fmt(line.avg_cost, 4)}</td>
              <td className="numeric">{fmt(line.est_cost)}</td>
            </tr>
          ))}
          <tr className="total-row">
            <td colSpan={6}>Estimated material cost</td>
            <td className="numeric">{fmt(explosion.total_estimated_cost)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
