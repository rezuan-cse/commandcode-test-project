import { useEffect, useMemo, useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { fmt, fmtQty } from "../../shared/format";
import JournalPreview from "../../shared/JournalPreview";
import { PermissionNotice } from "../../shared/PermissionNotice";
import { ReversedBadge, ReverseButton } from "../../shared/ReverseButton";
import { Card, ErrorBox, Field, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { ProductionPreview, ProductionRun } from "../../shared/types";

export default function ProductionPage() {
  const { asOf, refresh } = useDemo();
  const { user, can, level } = useAuth();
  const canWrite = can("production", true);
  const items = useAsync(() => api.items(), []);
  const runs = useAsync(() => api.productionRuns(), []);

  const [outputItem, setOutputItem] = useState("TRD-018");
  const [qty, setQty] = useState("50");
  const [date, setDate] = useState(asOf);
  const [labor, setLabor] = useState("100");
  const [overhead, setOverhead] = useState("0");
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [simulateFailure, setSimulateFailure] = useState(false);

  const [preview, setPreview] = useState<ProductionPreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [postError, setPostError] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);

  const payload = useMemo(() => {
    const lines = Object.entries(overrides)
      .filter(([, value]) => value.trim() !== "" && Number(value) > 0)
      .map(([component_code, value]) => ({ component_code, qty_consumed: value }));
    return {
      output_item_code: outputItem,
      qty_produced: qty,
      production_date: date,
      labor_cost: labor,
      overhead_cost: overhead,
      posted_by: "Store",
      lines: lines.length > 0 ? lines : null,
      simulate_failure: false,
    };
  }, [outputItem, qty, date, labor, overhead, overrides]);

  useEffect(() => {
    let cancelled = false;
    // Nothing to price when the role cannot post, and calling the preview would
    // only provoke a refusal the user can do nothing about.
    if (!canWrite || !outputItem || !qty || Number(qty) <= 0) {
      setPreview(null);
      return;
    }
    setPreviewing(true);
    setPreviewError(null);
    api
      .previewProduction(payload)
      .then((result) => {
        if (!cancelled) setPreview(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setPreview(null);
          setPreviewError(error instanceof Error ? error.message : String(error));
        }
      })
      .finally(() => {
        if (!cancelled) setPreviewing(false);
      });
    return () => {
      cancelled = true;
    };
  }, [payload, canWrite]);

  async function post() {
    setPostError(null);
    setToast(null);
    setPosting(true);
    try {
      const result = await api.postProduction({ ...payload, simulate_failure: simulateFailure });
      setToast(result.message);
      setOverrides({});
      refresh();
    } catch (error) {
      setPostError(error instanceof Error ? error.message : String(error));
    } finally {
      setPosting(false);
    }
  }

  return (
    <>
      <h1>Production Entry</h1>
      <p className="page-intro">
        One posting does five things in a single database transaction: consume each component at
        its current average cost, total the material plus labor and overhead, divide by the
        quantity produced, receipt the output at that unit cost, and write a balanced journal
        entry. If any step fails, none of it commits.
      </p>

      {toast && <div className="toast">✓ {toast}</div>}
      {postError && <ErrorBox message={postError} />}

      {!canWrite && (
        <PermissionNotice
          role={user?.role ?? ""}
          resource="production"
          write
          level={level("production")}
          readableBelow
        />
      )}

      {canWrite && (
      <Card title="New production run" subtitle="Components are suggested from the BOM and scaled automatically">
        <div className="form-row" style={{ marginBottom: 6 }}>
          <Field label="Item to produce">
            <select value={outputItem} onChange={(event) => { setOutputItem(event.target.value); setOverrides({}); }}>
              {(items.data ?? []).map((item) => (
                <option key={item.code} value={item.code}>
                  {item.code} — {item.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Quantity produced">
            <input
              className="numeric"
              inputMode="decimal"
              value={qty}
              onChange={(event) => setQty(event.target.value)}
            />
          </Field>
          <Field label="Production date">
            <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </Field>
          <Field label="Labor cost">
            <input
              className="numeric"
              inputMode="decimal"
              value={labor}
              onChange={(event) => setLabor(event.target.value)}
            />
          </Field>
          <Field label="Overhead cost">
            <input
              className="numeric"
              inputMode="decimal"
              value={overhead}
              onChange={(event) => setOverhead(event.target.value)}
            />
          </Field>
        </div>

        {previewing && <Spinner label="Building the cost sheet…" />}
        {previewError && <ErrorBox message={previewError} />}

        {preview && (
          <>
            <h2 style={{ margin: "18px 0 8px" }}>Components consumed</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Component</th>
                    <th>On hand</th>
                    <th className="numeric">Per unit</th>
                    <th className="numeric">Quantity consumed</th>
                    <th className="numeric">Avg cost</th>
                    <th className="numeric">Line cost</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.components.map((component) => {
                    const effective = overrides[component.component_code] ?? component.qty_consumed;
                    return (
                      <tr key={component.component_code}>
                        <td className="name-cell">
                          {component.component_code} — {component.component_name}
                        </td>
                        <td>
                          <span className="numeric" style={{ textAlign: "left" }}>
                            {fmtQty(component.on_hand)} {component.uom}
                          </span>{" "}
                          {component.sufficient ? (
                            <Pill tone="positive">ok</Pill>
                          ) : (
                            <Pill tone="negative">short</Pill>
                          )}
                        </td>
                        <td className="numeric">{fmtQty(component.qty_per_unit)}</td>
                        <td className="numeric">
                          <input
                            className="numeric"
                            inputMode="decimal"
                            style={{ width: 100 }}
                            value={effective}
                            onChange={(event) =>
                              setOverrides((current) => ({
                                ...current,
                                [component.component_code]: event.target.value,
                              }))
                            }
                          />
                        </td>
                        <td className="numeric">{fmt(component.unit_cost, 4)}</td>
                        <td className="numeric">{fmt(component.line_cost)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="grid grid-2" style={{ marginTop: 18 }}>
              <div>
                <h2 style={{ marginBottom: 8 }}>Cost build-up</h2>
                <table>
                  <tbody>
                    <tr>
                      <td>Material cost</td>
                      <td className="numeric">{fmt(preview.material_cost)}</td>
                    </tr>
                    <tr>
                      <td>Labor</td>
                      <td className="numeric">{fmt(preview.labor_cost)}</td>
                    </tr>
                    <tr>
                      <td>Overhead</td>
                      <td className="numeric">{fmt(preview.overhead_cost)}</td>
                    </tr>
                    <tr className="subtotal-row">
                      <td>Total production cost</td>
                      <td className="numeric">{fmt(preview.total_cost)}</td>
                    </tr>
                    <tr>
                      <td>Quantity produced</td>
                      <td className="numeric">{fmtQty(preview.qty_produced)}</td>
                    </tr>
                    <tr className="total-row">
                      <td>Unit cost of output</td>
                      <td className="numeric">{fmt(preview.unit_cost, 4)}</td>
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
              <div className="notice" style={{ marginTop: 14, marginBottom: 0 }}>
                {preview.warnings.join(" · ")}
              </div>
            )}

            <div
              style={{
                display: "flex",
                gap: 14,
                alignItems: "center",
                marginTop: 18,
                flexWrap: "wrap",
              }}
            >
              <button
                className="primary"
                onClick={post}
                disabled={!preview.can_post || posting}
              >
                {posting ? "Posting…" : "Post production"}
              </button>
              <label className="small muted" style={{ display: "flex", gap: 7, alignItems: "center" }}>
                <input
                  type="checkbox"
                  style={{ width: "auto" }}
                  checked={simulateFailure}
                  onChange={(event) => setSimulateFailure(event.target.checked)}
                />
                Inject a failure mid-transaction, to show the rollback
              </label>
            </div>
          </>
        )}
      </Card>
      )}

      <Card title="Posted production runs" subtitle="Newest first">
        {runs.loading && <Spinner />}
        {runs.data && runs.data.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            No production runs posted yet.
          </p>
        )}
        {runs.data && runs.data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Order</th>
                  <th>Date</th>
                  <th>Output item</th>
                  <th className="numeric">Qty</th>
                  <th className="numeric">Material</th>
                  <th className="numeric">Labor + OH</th>
                  <th className="numeric">Total cost</th>
                  <th className="numeric">Unit cost</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {runs.data.map((run: ProductionRun) => (
                  <tr key={run.id}>
                    <td className="name-cell">
                      {run.order_no}{" "}
                      {run.is_reversed && <ReversedBadge reason={run.reversal_reason} />}
                    </td>
                    <td>{run.production_date}</td>
                    <td>{run.output_item_code}</td>
                    <td className="numeric">{fmtQty(run.qty_produced)}</td>
                    <td className="numeric">{fmt(run.material_cost)}</td>
                    <td className="numeric">
                      {fmt(Number(run.labor_cost) + Number(run.overhead_cost))}
                    </td>
                    <td className="numeric">{fmt(run.total_cost)}</td>
                    <td className="numeric">{fmt(run.unit_cost, 4)}</td>
                    <td>
                      {canWrite && !run.is_reversed && (
                        <ReverseButton
                          onReverse={async (reason) => {
                            await api.reverseProduction(run.id, reason);
                            refresh();
                          }}
                        />
                      )}
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

