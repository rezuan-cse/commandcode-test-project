import { Link, useParams } from "react-router-dom";
import { api } from "../../shared/api";
import { fmt } from "../../shared/format";
import { ErrorBox, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";

/**
 * A printable payslip summary for a posted run. It reads the stored lines, so
 * what is printed matches what the ledger holds and never drifts.
 */
export default function PayslipPage() {
  const { id } = useParams<{ id: string }>();
  const run = useAsync(() => api.payrollRun(id ?? ""), [id]);

  if (run.loading) return <Spinner label="Preparing the payslips…" />;
  if (run.error) return <ErrorBox message={run.error} />;
  if (!run.data) return null;

  const detail = run.data;

  return (
    <div className="receipt-page">
      <div className="receipt-toolbar">
        <Link to="/payroll">
          <button>← Back to Payroll</button>
        </Link>
        <button className="primary" onClick={() => window.print()}>
          Print
        </button>
      </div>

      <article className="receipt">
        <header className="receipt-head">
          <div>
            <h1>Payslips</h1>
            <p>
              Period {detail.period_start} to {detail.period_end}
            </p>
          </div>
          <div className="receipt-meta">
            <h2>{detail.run_no}</h2>
            <dl>
              <dt>Pay date</dt>
              <dd>{detail.pay_date}</dd>
              <dt>Recorded by</dt>
              <dd>{detail.posted_by}</dd>
            </dl>
          </div>
        </header>

        <table className="receipt-lines">
          <thead>
            <tr>
              <th>Employee</th>
              <th className="numeric">Gross</th>
              <th className="numeric">Deductions</th>
              <th className="numeric">Net pay</th>
            </tr>
          </thead>
          <tbody>
            {detail.lines.map((line) => (
              <tr key={line.employee_code}>
                <td>
                  <div>{line.employee_name}</div>
                  <div className="receipt-code">{line.employee_code}</div>
                  <div className="muted small">
                    {Object.entries(line.components)
                      .map(([name, amount]) => `${name} ${fmt(amount)}`)
                      .join(" · ")}
                  </div>
                  {Object.keys(line.deductions_detail).length > 0 && (
                    <div className="muted small">
                      {Object.entries(line.deductions_detail)
                        .map(([name, amount]) => `${name} −${fmt(amount)}`)
                        .join(" · ")}
                    </div>
                  )}
                </td>
                <td className="numeric">{fmt(line.gross)}</td>
                <td className="numeric">{fmt(line.deductions)}</td>
                <td className="numeric">{fmt(line.net)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td className="receipt-total-label">Total</td>
              <td className="numeric">{fmt(detail.gross_total)}</td>
              <td className="numeric">{fmt(detail.deductions_total)}</td>
              <td className="numeric receipt-total">{fmt(detail.net_total)}</td>
            </tr>
          </tfoot>
        </table>

        {detail.is_reversed && (
          <div className="receipt-reversed-banner">
            Reversed — this run has been undone
            {detail.reversal_reason ? `: ${detail.reversal_reason}` : ""}
          </div>
        )}
      </article>
    </div>
  );
}
