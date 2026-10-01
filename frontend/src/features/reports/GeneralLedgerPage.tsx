import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt } from "../../shared/format";
import { csvFilename } from "../../shared/csv";
import { Card, ErrorBox, ExportButton, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";

export default function GeneralLedgerPage() {
  const { asOf, dateFrom } = useDemo();
  const { data, loading, error } = useAsync(
    () => api.generalLedger(dateFrom, asOf),
    [dateFrom, asOf],
  );

  return (
    <>
      <h1>General Ledger</h1>
      <p className="page-intro">
        Opening balance, period movement, and closing balance for every account, for {dateFrom} to{" "}
        {asOf}. This is the same layout as the client's workbook, but computed rather than
        maintained by hand.
      </p>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} />}

      {data && (
        <Card
          title={`${data.date_from} → ${data.date_to}`}
          actions={
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <Pill
                tone={
                  data.total_period_debit === data.total_period_credit ? "positive" : "negative"
                }
              >
                period debits {fmt(data.total_period_debit)} = credits{" "}
                {fmt(data.total_period_credit)}
              </Pill>
              <ExportButton
                filename={csvFilename(`general-ledger-${data.date_from}-to-${data.date_to}`)}
                rows={data.accounts}
                columns={[
                  { header: "Account", value: (row) => row.account_code },
                  { header: "Name", value: (row) => row.account_name },
                  { header: "Type", value: (row) => row.account_type },
                  { header: "Segment", value: (row) => row.segment },
                  { header: "Opening Dr", value: (row) => row.opening_debit },
                  { header: "Opening Cr", value: (row) => row.opening_credit },
                  { header: "Period Dr", value: (row) => row.period_debit },
                  { header: "Period Cr", value: (row) => row.period_credit },
                  { header: "Closing Dr", value: (row) => row.closing_debit },
                  { header: "Closing Cr", value: (row) => row.closing_credit },
                ]}
              />
            </div>
          }
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Account</th>
                  <th>Segment</th>
                  <th className="numeric">Opening Dr</th>
                  <th className="numeric">Opening Cr</th>
                  <th className="numeric">Period Dr</th>
                  <th className="numeric">Period Cr</th>
                  <th className="numeric">Closing Dr</th>
                  <th className="numeric">Closing Cr</th>
                </tr>
              </thead>
              <tbody>
                {data.accounts
                  .filter(
                    (account) =>
                      Number(account.opening_debit) ||
                      Number(account.opening_credit) ||
                      Number(account.period_debit) ||
                      Number(account.period_credit),
                  )
                  .map((account) => (
                    <tr key={account.account_code}>
                      <td className="numeric" style={{ textAlign: "left" }}>
                        {account.account_code}
                      </td>
                      <td className="name-cell">{account.account_name}</td>
                      <td className="muted small">{account.segment}</td>
                      <td className="numeric">{Number(account.opening_debit) ? fmt(account.opening_debit) : "—"}</td>
                      <td className="numeric">{Number(account.opening_credit) ? fmt(account.opening_credit) : "—"}</td>
                      <td className="numeric">{Number(account.period_debit) ? fmt(account.period_debit) : "—"}</td>
                      <td className="numeric">{Number(account.period_credit) ? fmt(account.period_credit) : "—"}</td>
                      <td className="numeric">{Number(account.closing_debit) ? fmt(account.closing_debit) : "—"}</td>
                      <td className="numeric">{Number(account.closing_credit) ? fmt(account.closing_credit) : "—"}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  );
}
