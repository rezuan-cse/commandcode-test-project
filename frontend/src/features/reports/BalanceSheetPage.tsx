import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt } from "../../shared/format";
import { Card, ErrorBox, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { TrialBalanceRow } from "../../shared/types";

export default function BalanceSheetPage() {
  const { asOf } = useDemo();
  const { data, loading, error } = useAsync(() => api.balanceSheet(asOf), [asOf]);

  return (
    <>
      <h1>Balance Sheet</h1>
      <p className="page-intro">
        Assets, liabilities, and equity as of {asOf}. Current-period profit is pulled from the
        profit and loss statement rather than being posted separately, so the two statements can
        never disagree. The final check must always be zero.
      </p>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} />}

      {data && (
        <Card
          title={`As of ${data.as_of}`}
          actions={
            <Pill tone={data.is_balanced ? "positive" : "negative"}>
              {data.is_balanced ? "assets = liabilities + equity" : `out by ${fmt(data.check)}`}
            </Pill>
          }
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Segment</th>
                  <th className="numeric">Debit</th>
                  <th className="numeric">Credit</th>
                </tr>
              </thead>
              <tbody>
                <tr className="section-row">
                  <td colSpan={4}>Assets</td>
                </tr>
                {data.assets.map((row) => (
                  <AccountRow key={row.account_code} row={row} indent />
                ))}
                <tr className="subtotal-row">
                  <td colSpan={3}>Total assets</td>
                  <td className="numeric">{fmt(data.total_assets)}</td>
                </tr>

                <tr className="section-row">
                  <td colSpan={4}>Liabilities</td>
                </tr>
                {data.liabilities.length === 0 && (
                  <tr>
                    <td colSpan={4} className="muted small">
                      No liabilities outstanding
                    </td>
                  </tr>
                )}
                {data.liabilities.map((row) => (
                  <AccountRow key={row.account_code} row={row} indent />
                ))}
                <tr className="subtotal-row">
                  <td colSpan={4}>Total liabilities {fmt(data.total_liabilities)}</td>
                </tr>

                <tr className="section-row">
                  <td colSpan={4}>Equity</td>
                </tr>
                {data.equity_accounts.map((row) => (
                  <AccountRow key={row.account_code} row={row} indent />
                ))}
                <tr>
                  <td className="indent" colSpan={3}>
                    Current period net profit
                  </td>
                  <td className="numeric">{fmt(data.current_period_profit)}</td>
                </tr>
                <tr className="subtotal-row">
                  <td colSpan={3}>Total equity</td>
                  <td className="numeric">{fmt(data.total_equity)}</td>
                </tr>

                <tr className="total-row">
                  <td colSpan={3}>Total liabilities + equity</td>
                  <td className="numeric">{fmt(data.total_liabilities_and_equity)}</td>
                </tr>
                <tr className={`check-row ${data.is_balanced ? "" : "failed"}`}>
                  <td colSpan={3}>Check: assets − liabilities − equity — must be zero</td>
                  <td className="numeric">{fmt(data.check)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}

function AccountRow({ row, indent = false }: { row: TrialBalanceRow; indent?: boolean }) {
  return (
    <tr>
      <td className={indent ? "indent" : ""}>
        {row.account_code} — {row.account_name}
      </td>
      <td className="muted small">{row.segment}</td>
      <td className="numeric">{Number(row.debit) ? fmt(row.debit) : "—"}</td>
      <td className="numeric">{Number(row.credit) ? fmt(row.credit) : "—"}</td>
    </tr>
  );
}
