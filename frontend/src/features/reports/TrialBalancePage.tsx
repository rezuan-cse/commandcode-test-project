import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt } from "../../shared/format";
import { Card, ErrorBox, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";

export default function TrialBalancePage() {
  const { asOf } = useDemo();
  const { data, loading, error } = useAsync(() => api.trialBalance(asOf), [asOf]);

  return (
    <>
      <h1>Trial Balance</h1>
      <p className="page-intro">
        Every account with a non-zero balance as of {asOf}, derived live from opening balances plus
        posted entries. The bottom line must always be zero — if it is not, the books are broken.
      </p>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} />}

      {data && (
        <Card
          title={`As of ${data.as_of}`}
          actions={
            <Pill tone={data.balanced ? "positive" : "negative"}>
              {data.balanced ? "balanced" : `out by ${fmt(data.difference)}`}
            </Pill>
          }
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Account</th>
                  <th>Type</th>
                  <th>Segment</th>
                  <th className="numeric">Debit</th>
                  <th className="numeric">Credit</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={row.account_code}>
                    <td className="numeric" style={{ textAlign: "left" }}>
                      {row.account_code}
                    </td>
                    <td className="name-cell">{row.account_name}</td>
                    <td className="muted small">{row.account_type}</td>
                    <td className="muted small">{row.segment}</td>
                    <td className="numeric">{Number(row.debit) ? fmt(row.debit) : "—"}</td>
                    <td className="numeric">{Number(row.credit) ? fmt(row.credit) : "—"}</td>
                  </tr>
                ))}
                <tr className="total-row">
                  <td colSpan={4}>Total</td>
                  <td className="numeric">{fmt(data.total_debit)}</td>
                  <td className="numeric">{fmt(data.total_credit)}</td>
                </tr>
                <tr className={`check-row ${data.balanced ? "" : "failed"}`}>
                  <td colSpan={5}>Difference — must be zero</td>
                  <td className="numeric">{fmt(data.difference)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}
