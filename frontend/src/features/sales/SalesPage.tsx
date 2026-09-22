import { useEffect, useMemo, useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { fmt, fmtPct, fmtQty } from "../../shared/format";
import JournalPreview from "../../shared/JournalPreview";
import { PermissionNotice } from "../../shared/PermissionNotice";
import { Card, ErrorBox, Field, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { Sale, SalePreview } from "../../shared/types";

interface DraftLine {
  item_code: string;
  qty: string;
  sale_price: string;
}

export default function SalesPage() {
  const { asOf, refresh } = useDemo();
  const { user, can, level } = useAuth();
  const canWrite = can("sales_purchase", true);
  const items = useAsync(() => api.items(), []);
  const sales = useAsync(() => api.sales(), []);

  const [customer, setCustomer] = useState("Local Customer");
  const [date, setDate] = useState(asOf);
  const [lines, setLines] = useState<DraftLine[]>([
    { item_code: "", qty: "1", sale_price: "0" },
  ]);
  const [preview, setPreview] = useState<SalePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);

  const sellable = (items.data ?? []).filter((item) => Number(item.qty_on_hand) > 0);
  const options = sellable.length > 0 ? sellable : items.data ?? [];

  /**
   * Default the asking price to the item's average cost, so switching item
   * never leaves a stale price behind from a different product. The user then
   * raises it to their real selling price.
   */
  function costOf(code: string): string {
    return (items.data ?? []).find((item) => item.code === code)?.avg_cost ?? "0";
  }

  useEffect(() => {
    if (!lines[0]?.item_code && options.length > 0) {
      const first = options.find((item) => Number(item.qty_on_hand) > 0) ?? options[0];
      setLines([{ item_code: first.code, qty: "1", sale_price: first.avg_cost }]);
    }
  }, [options, lines]);

  const payload = useMemo(
    () => ({
      customer,
      sale_date: date,
      is_credit: true,
      posted_by: "Sales",
      lines: lines
        .filter((line) => line.item_code && Number(line.qty) > 0)
        .map((line) => ({
          item_code: line.item_code,
          qty: line.qty,
          sale_price: line.sale_price || "0",
        })),
    }),
    [customer, date, lines],
  );

  useEffect(() => {
    let cancelled = false;
    // Nothing to price when the role cannot post, and calling the preview would
    // only provoke a refusal the user can do nothing about.
    if (!canWrite || payload.lines.length === 0) {
      setPreview(null);
      return;
    }
    api
      .previewSale(payload)
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
  }, [payload, canWrite]);

  async function post() {
    setError(null);
    setToast(null);
    setPosting(true);
    try {
      const result = await api.postSale(payload);
      setToast(result.message);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setPosting(false);
    }
  }

  return (
    <>
      <h1>Sales Entry</h1>
      <p className="page-intro">
        One posting reduces stock at the item's current weighted-average cost and writes a single
        journal entry containing both sides: revenue (debit receivable, credit sales) and cost of
        goods sold (debit COGS, credit inventory). Both halves are enforced balanced together.
      </p>

      {toast && <div className="toast">✓ {toast}</div>}
      {error && <ErrorBox message={error} />}

      {!canWrite && (
        <PermissionNotice
          role={user?.role ?? ""}
          resource="sales_purchase"
          write
          level={level("sales_purchase")}
          readableBelow
        />
      )}

      {canWrite && (
      <Card title="New sale" subtitle="Inventory is valued at average cost automatically">
        <div className="form-row" style={{ marginBottom: 14 }}>
          <Field label="Customer">
            <input value={customer} onChange={(event) => setCustomer(event.target.value)} />
          </Field>
          <Field label="Sale date">
            <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </Field>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th className="numeric">On hand</th>
                <th className="numeric">Avg cost</th>
                <th className="numeric">Quantity</th>
                <th className="numeric">Sale price</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => {
                const item = (items.data ?? []).find((row) => row.code === line.item_code);
                const insufficient = item && Number(line.qty) > Number(item.qty_on_hand);
                const pricedLine = preview?.lines.find(
                  (row) => row.item_code === line.item_code,
                );
                return (
                  <tr key={index}>
                    <td>
                      <select
                        aria-label={`Item line ${index + 1}`}
                        value={line.item_code}
                        onChange={(event) => {
                          const code = event.target.value;
                          updateLine(index, { item_code: code, sale_price: costOf(code) });
                        }}
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
                        aria-label={`Quantity line ${index + 1}`}
                        className="numeric"
                        inputMode="decimal"
                        style={{ width: 90 }}
                        value={line.qty}
                        onChange={(event) => updateLine(index, { qty: event.target.value })}
                      />
                      {insufficient && <Pill tone="negative">short</Pill>}
                    </td>
                    <td className="numeric">
                      <input
                        aria-label={`Sale price line ${index + 1}`}
                        className="numeric"
                        inputMode="decimal"
                        style={{ width: 110 }}
                        value={line.sale_price}
                        onChange={(event) =>
                          updateLine(index, { sale_price: event.target.value })
                        }
                      />
                      {pricedLine && pricedLine.below_cost && (
                        <Pill tone="negative">below cost</Pill>
                      )}
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
            onClick={() => {
              const code = options[0]?.code ?? "";
              setLines([
                ...lines,
                { item_code: code, qty: "1", sale_price: costOf(code) },
              ]);
            }}
          >
            Add line
          </button>
        </div>

        {preview && (
          <>
            <div className="grid grid-2" style={{ marginTop: 20 }}>
              <div>
                <h2 style={{ marginBottom: 8 }}>Revenue and margin</h2>
                <table>
                  <tbody>
                    <tr>
                      <td>Revenue</td>
                      <td className="numeric">{fmt(preview.revenue)}</td>
                    </tr>
                    <tr>
                      <td>Cost of goods sold (at average cost)</td>
                      <td className="numeric">{fmt(preview.cogs)}</td>
                    </tr>
                    <tr className="total-row">
                      <td>Gross profit</td>
                      <td
                        className="numeric"
                        style={
                          Number(preview.gross_profit) < 0
                            ? { color: "var(--negative)" }
                            : undefined
                        }
                      >
                        {fmt(preview.gross_profit)}
                      </td>
                    </tr>
                    <tr>
                      <td>Gross margin</td>
                      <td className="numeric">{fmtPct(preview.gross_margin_pct)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div>
                <h2 style={{ marginBottom: 8 }}>Journal entry it will post</h2>
                <JournalPreview lines={preview.journal_lines} balanced={preview.balanced} />
              </div>
            </div>

            {preview.warnings.length > 0 && (
              <div className="notice" style={{ marginTop: 16, marginBottom: 0 }}>
                {preview.warnings.map((warning) => (
                  <div key={warning}>{warning}</div>
                ))}
              </div>
            )}

            <div style={{ marginTop: 18 }}>
              <button className="primary" onClick={post} disabled={!preview.can_post || posting}>
                {posting ? "Posting…" : "Post sale"}
              </button>
            </div>
          </>
        )}
      </Card>
      )}

      <Card title="Posted sales">
        {sales.loading && <Spinner />}
        {sales.data && sales.data.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            No sales posted yet.
          </p>
        )}
        {sales.data && sales.data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Date</th>
                  <th>Customer</th>
                  <th className="numeric">Revenue</th>
                  <th className="numeric">COGS</th>
                  <th className="numeric">Gross profit</th>
                </tr>
              </thead>
              <tbody>
                {sales.data.map((sale: Sale) => (
                  <tr key={sale.id}>
                    <td className="name-cell">{sale.order_no}</td>
                    <td>{sale.sale_date}</td>
                    <td>{sale.customer}</td>
                    <td className="numeric">{fmt(sale.revenue)}</td>
                    <td className="numeric">{fmt(sale.cogs)}</td>
                    <td className="numeric">{fmt(Number(sale.revenue) - Number(sale.cogs))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );

  function updateLine(index: number, patch: Partial<DraftLine>) {
    setLines((current) =>
      current.map((line, position) => (position === index ? { ...line, ...patch } : line)),
    );
  }
}
