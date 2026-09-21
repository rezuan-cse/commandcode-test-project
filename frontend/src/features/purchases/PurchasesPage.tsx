import { useEffect, useMemo, useState } from "react";
import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt, fmtQty } from "../../shared/format";
import JournalPreview from "../../shared/JournalPreview";
import { Card, ErrorBox, Field, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { PurchasePreview } from "../../shared/types";

interface DraftLine {
  item_code: string;
  qty: string;
  unit_cost: string;
}

/**
 * Purchase entry. The workbook never defined this screen, but production needs
 * a source of raw material, so it is built as the mirror image of sales: stock
 * rises at cost and a balanced entry debits inventory while crediting payable.
 */
export default function PurchasesPage() {
  const { asOf, refresh } = useDemo();
  const items = useAsync(() => api.items(), []);

  const [supplier, setSupplier] = useState("Raw Material Supplier");
  const [date, setDate] = useState(asOf);
  const [onCredit, setOnCredit] = useState(true);
  const [lines, setLines] = useState<DraftLine[]>([
    { item_code: "", qty: "100", unit_cost: "0" },
  ]);
  const [preview, setPreview] = useState<PurchasePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);

  const options = items.data ?? [];

  useEffect(() => {
    if (!lines[0]?.item_code && options.length > 0) {
      setLines([{ item_code: options[0].code, qty: "100", unit_cost: options[0].avg_cost }]);
    }
  }, [options, lines]);

  const payload = useMemo(
    () => ({
      supplier,
      purchase_date: date,
      is_credit: onCredit,
      posted_by: "Store",
      lines: lines
        .filter((line) => line.item_code && Number(line.qty) > 0)
        .map((line) => ({
          item_code: line.item_code,
          qty: line.qty,
          unit_cost: line.unit_cost || "0",
        })),
    }),
    [supplier, date, onCredit, lines],
  );

  useEffect(() => {
    let cancelled = false;
    if (payload.lines.length === 0) {
      setPreview(null);
      return;
    }
    api
      .previewPurchase(payload)
      .then((result) => {
        if (!cancelled) {
          setPreview(result);
          setError(null);
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setPreview(null);
          setError(caught instanceof Error ? caught.message : String(caught));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [payload]);

  async function post() {
    setError(null);
    setToast(null);
    setPosting(true);
    try {
      const result = await api.postPurchase(payload);
      setToast(result.message);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setPosting(false);
    }
  }

  /** Fill the line up with every component the TRD-018 BOM needs. */
  async function loadFillerRequirements() {
    try {
      const explosion = await api.explode("TRD-018", "50");
      setLines(
        explosion.lines.map((line) => ({
          item_code: line.item_code,
          qty: String(Math.max(Number(line.qty_required), 1)),
          unit_cost: line.avg_cost === "0.00000000" ? "20" : line.avg_cost,
        })),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    }
  }

  return (
    <>
      <h1>Purchase Entry</h1>
      <p className="page-intro">
        Purchases are the mirror image of sales: stock rises at the price paid, the item's
        weighted-average cost is recalculated, and a balanced entry debits inventory while
        crediting either the supplier payable or the bank.
      </p>

      {toast && <div className="toast">✓ {toast}</div>}
      {error && <ErrorBox message={error} />}

      <Card
        title="New purchase"
        subtitle="Receiving stock updates the average cost used by every later movement"
        actions={<button onClick={loadFillerRequirements}>Load TRD-018 requirements</button>}
      >
        <div className="form-row" style={{ marginBottom: 14 }}>
          <Field label="Supplier">
            <input value={supplier} onChange={(event) => setSupplier(event.target.value)} />
          </Field>
          <Field label="Purchase date">
            <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </Field>
          <Field label="Settlement">
            <select
              value={onCredit ? "credit" : "cash"}
              onChange={(event) => setOnCredit(event.target.value === "credit")}
            >
              <option value="credit">On credit (supplier payable)</option>
              <option value="cash">Paid immediately (bank)</option>
            </select>
          </Field>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th className="numeric">On hand</th>
                <th className="numeric">Current avg cost</th>
                <th className="numeric">Quantity</th>
                <th className="numeric">Unit cost</th>
                <th className="numeric">Line value</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => {
                const item = options.find((row) => row.code === line.item_code);
                const lineValue = Number(line.qty) * Number(line.unit_cost);
                return (
                  <tr key={index}>
                    <td>
                      <select
                        value={line.item_code}
                        onChange={(event) =>
                          updateLine(index, { item_code: event.target.value })
                        }
                      >
                        {options.map((option) => (
                          <option key={option.code} value={option.code}>
                            {option.code} — {option.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="numeric">{item ? fmtQty(item.qty_on_hand) : "—"}</td>
                    <td className="numeric">{item ? fmt(item.avg_cost, 4) : "—"}</td>
                    <td className="numeric">
                      <input
                        className="numeric"
                        inputMode="decimal"
                        style={{ width: 90 }}
                        value={line.qty}
                        onChange={(event) => updateLine(index, { qty: event.target.value })}
                      />
                    </td>
                    <td className="numeric">
                      <input
                        className="numeric"
                        inputMode="decimal"
                        style={{ width: 100 }}
                        value={line.unit_cost}
                        onChange={(event) => updateLine(index, { unit_cost: event.target.value })}
                      />
                    </td>
                    <td className="numeric">
                      {Number.isFinite(lineValue) ? fmt(lineValue.toFixed(4)) : "—"}
                    </td>
                    <td>
                      {lines.length > 1 && (
                        <button onClick={() => setLines(lines.filter((_, i) => i !== index))}>
                          Remove
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: 12 }}>
          <button
            onClick={() =>
              setLines([...lines, { item_code: options[0]?.code ?? "", qty: "1", unit_cost: "0" }])
            }
          >
            Add line
          </button>
        </div>

        {preview && (
          <div className="grid grid-2" style={{ marginTop: 20 }}>
            <div>
              <h2 style={{ marginBottom: 8 }}>Receipt summary</h2>
              <table>
                <tbody>
                  <tr>
                    <td>Purchase value</td>
                    <td className="numeric">{fmt(preview.total_value)}</td>
                  </tr>
                  <tr>
                    <td>Settlement</td>
                    <td className="numeric">{onCredit ? "Supplier payable" : "Bank"}</td>
                  </tr>
                </tbody>
              </table>
              <h2 style={{ margin: "16px 0 8px" }}>Effect on average cost</h2>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th className="numeric">Before</th>
                      <th className="numeric">After</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.lines.map((line) => (
                      <tr key={line.item_code}>
                        <td className="name-cell">{line.item_code}</td>
                        <td className="numeric">{fmt(line.avg_cost_before, 4)}</td>
                        <td className="numeric">{fmt(line.avg_cost_after, 4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div>
              <h2 style={{ marginBottom: 8 }}>Journal entry it will post</h2>
              <JournalPreview lines={preview.journal_lines} balanced={preview.balanced} />
            </div>
          </div>
        )}

        {preview && (
          <div style={{ marginTop: 18 }}>
            <button className="primary" onClick={post} disabled={!preview.can_post || posting}>
              {posting ? "Posting…" : "Post purchase"}
            </button>
          </div>
        )}

        {items.loading && <Spinner />}
      </Card>
    </>
  );

  function updateLine(index: number, patch: Partial<DraftLine>) {
    setLines((current) =>
      current.map((line, position) => (position === index ? { ...line, ...patch } : line)),
    );
  }
}
