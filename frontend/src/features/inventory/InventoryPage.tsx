import { useState } from "react";
import { api } from "../../shared/api";
import { fmt, fmtQty } from "../../shared/format";
import { Card, Empty, ErrorBox, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { BomExplosion } from "../../shared/types";

export default function InventoryPage() {
  const items = useAsync(() => api.items(), []);
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");

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

      <Card
        title="Inventory ledger"
        subtitle="Every movement, with its running balance and average cost"
        actions={
          <input
            type="search"
            placeholder="Search item…"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            style={{ width: 200 }}
          />
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
                      </td>
                      <td className="name-cell">{item.name}</td>
                      <td>{item.category}</td>
                      <td>{item.segment}</td>
                      <td>{item.uom}</td>
                      <td className="numeric">{fmtQty(item.qty_on_hand)}</td>
                      <td className="numeric">{fmt(item.avg_cost, 4)}</td>
                      <td className="numeric">{fmt(item.value_on_hand)}</td>
                      <td>
                        <button onClick={() => setSelected(item.code)}>Ledger</button>
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
      subtitle="Movements in order, showing how the running balance is built"
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
