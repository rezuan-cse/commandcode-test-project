import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { fmt, fmtDateTime } from "../../shared/format";
import JournalPreview from "../../shared/JournalPreview";
import { PermissionNotice } from "../../shared/PermissionNotice";
import { ReversedBadge, ReverseButton } from "../../shared/ReverseButton";
import { Card, ErrorBox, Field, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { PayrollPreview, PayrollRun } from "../../shared/types";

/** First and last day of the month an ISO date falls in. */
function monthBounds(iso: string): { start: string; end: string } {
  const [year, month] = iso.split("-").map(Number);
  const padded = String(month).padStart(2, "0");
  const lastDay = new Date(year, month, 0).getDate();
  return {
    start: `${year}-${padded}-01`,
    end: `${year}-${padded}-${String(lastDay).padStart(2, "0")}`,
  };
}

export default function PayrollPage() {
  const { asOf, refresh } = useDemo();
  const { user, can, level } = useAuth();
  const canWrite = can("payroll", true);
  const canRead = can("payroll");
  const runs = useAsync(() => api.payrollRuns(), []);

  const bounds = useMemo(() => monthBounds(asOf), [asOf]);
  const [periodStart, setPeriodStart] = useState(bounds.start);
  const [periodEnd, setPeriodEnd] = useState(bounds.end);
  const [payDate, setPayDate] = useState(asOf);
  const [preview, setPreview] = useState<PayrollPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);

  const payload = useMemo(
    () => ({
      period_start: periodStart,
      period_end: periodEnd,
      pay_date: payDate,
    }),
    [periodStart, periodEnd, payDate],
  );

  useEffect(() => {
    let cancelled = false;
    if (!canWrite) {
      setPreview(null);
      return;
    }
    api
      .previewPayroll(payload)
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
    setPosting(true);
    setError(null);
    setToast(null);
    try {
      const result = await api.postPayroll(payload);
      setToast(result.message);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setPosting(false);
    }
  }

  if (!canRead) {
    return (
      <>
        <h1>Payroll</h1>
        <PermissionNotice
          role={user?.role ?? ""}
          resource="payroll"
          write={false}
          level={level("payroll")}
        />
      </>
    );
  }

  return (
    <>
      <h1>Payroll</h1>
      <p className="page-intro">
        A run pays every active employee for the period and posts one balanced entry: the
        salary expense is debited, and the deductions and net pay are credited. The structure
        and deductions come from Configuration.
      </p>

      {toast && <div className="toast">✓ {toast}</div>}
      {error && <ErrorBox message={error} />}

      {canWrite && (
        <Card title="New payroll run" subtitle="Preview before posting">
          <div className="form-row" style={{ marginBottom: 14 }}>
            <Field label="Period start">
              <input
                type="date"
                value={periodStart}
                onChange={(event) => setPeriodStart(event.target.value)}
              />
            </Field>
            <Field label="Period end">
              <input
                type="date"
                value={periodEnd}
                onChange={(event) => setPeriodEnd(event.target.value)}
              />
            </Field>
            <Field label="Pay date">
              <input
                type="date"
                value={payDate}
                onChange={(event) => setPayDate(event.target.value)}
              />
            </Field>
          </div>

          {preview && preview.lines.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th className="numeric">Gross</th>
                    <th className="numeric">Deductions</th>
                    <th className="numeric">Net pay</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.lines.map((line) => (
                    <tr key={line.employee_code}>
                      <td className="name-cell">
                        {line.employee_name}
                        <div className="muted small">{line.employee_code}</div>
                      </td>
                      <td className="numeric">{fmt(line.gross)}</td>
                      <td className="numeric">{fmt(line.deductions)}</td>
                      <td className="numeric">{fmt(line.net)}</td>
                    </tr>
                  ))}
                  <tr className="total-row">
                    <td>Total</td>
                    <td className="numeric">{fmt(preview.gross_total)}</td>
                    <td className="numeric">{fmt(preview.deductions_total)}</td>
                    <td className="numeric">{fmt(preview.net_total)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {preview && (
            <div className="grid grid-2" style={{ marginTop: 20 }}>
              <div>
                {preview.warnings.map((warning) => (
                  <div className="notice" key={warning}>
                    {warning}
                  </div>
                ))}
              </div>
              <div>
                <h2 style={{ marginBottom: 8 }}>Journal entry it will post</h2>
                <JournalPreview lines={preview.journal_lines} balanced={preview.balanced} />
              </div>
            </div>
          )}

          {preview && preview.lines.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <button className="primary" onClick={post} disabled={posting || !preview.balanced}>
                {posting ? "Posting…" : "Post payroll"}
              </button>
            </div>
          )}
        </Card>
      )}

      <Card title="Posted runs" subtitle="Newest first">
        {runs.loading && <Spinner />}
        {runs.error && <ErrorBox message={runs.error} />}
        {runs.data && runs.data.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            No payroll runs posted yet.
          </p>
        )}
        {runs.data && runs.data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Period</th>
                  <th>Pay date</th>
                  <th>Posted</th>
                  <th className="numeric">Gross</th>
                  <th className="numeric">Net</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {runs.data.map((run: PayrollRun) => (
                  <tr key={run.id}>
                    <td className="name-cell">
                      {run.run_no} {run.is_reversed && <ReversedBadge reason={run.reversal_reason} />}
                    </td>
                    <td>
                      {run.period_start} → {run.period_end}
                    </td>
                    <td>{run.pay_date}</td>
                    <td className="muted small">{fmtDateTime(run.posted_at)}</td>
                    <td className="numeric">{fmt(run.gross_total)}</td>
                    <td className="numeric">{fmt(run.net_total)}</td>
                    <td>
                      <div className="row-actions">
                        <Link to={`/payroll/runs/${run.id}`}>
                          <button>Payslips</button>
                        </Link>
                        {canWrite && !run.is_reversed && (
                          <ReverseButton
                            onReverse={async (reason) => {
                              await api.reversePayroll(run.id, reason);
                              refresh();
                            }}
                          />
                        )}
                      </div>
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
