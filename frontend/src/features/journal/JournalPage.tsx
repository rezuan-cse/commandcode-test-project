import { useState } from "react";
import { api } from "../../shared/api";
import { fmt, fmtDateTime } from "../../shared/format";
import { csvFilename } from "../../shared/csv";
import { Card, Empty, ExportButton, Pill, Spinner, ErrorBox } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { JournalEntry } from "../../shared/types";

const SOURCE_TONE: Record<string, "neutral" | "positive" | "info" | "warn"> = {
  Manual: "neutral",
  Production: "info",
  Sales: "positive",
  Purchase: "warn",
};

export default function JournalPage() {
  const { data, loading, error } = useAsync(() => api.journalEntries(), []);
  const [openId, setOpenId] = useState<number | null>(null);

  return (
    <>
      <h1>Journal Entries</h1>
      <p className="page-intro">
        Every voucher in the system, whether typed by hand or generated automatically by a
        production or sales posting. Each one is enforced balanced before it can be stored —
        the API refuses an unbalanced entry and the database would reject it too.
      </p>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} />}
      {data && data.length === 0 && <Empty message="No journal entries yet." />}

      {data && data.length > 0 && (
        <Card
          title={`${data.length} vouchers`}
          subtitle="Every entry, newest first"
          actions={
            <ExportButton
              filename={csvFilename("journal-entries")}
              // One row per *line*, not per voucher: flattened, this is the
              // account-by-account listing that reconciles against the ledger.
              rows={data.flatMap((entry) =>
                entry.lines.map((line) => ({ entry, line })),
              )}
              columns={[
                { header: "Voucher", value: (row) => row.entry.voucher_no },
                { header: "Date", value: (row) => row.entry.entry_date },
                { header: "Source", value: (row) => row.entry.source },
                { header: "Account", value: (row) => row.line.account_code },
                { header: "Segment", value: (row) => row.line.segment },
                { header: "Line narration", value: (row) => row.line.narration },
                { header: "Voucher narration", value: (row) => row.entry.narration },
                { header: "Debit", value: (row) => row.line.debit },
                { header: "Credit", value: (row) => row.line.credit },
                { header: "Entered by", value: (row) => row.entry.posted_by },
                { header: "Posted at", value: (row) => row.entry.posted_at },
              ]}
            />
          }
        >
          <p className="small muted" style={{ margin: 0 }}>
            The export writes <strong>one row per journal line</strong>, not one per
            voucher. Flattened that way it is the general-ledger listing: every debit
            and credit, with the voucher and account it belongs to, ready to sort and
            total in Excel.
          </p>
        </Card>
      )}

      {data && data.map((entry) => (
        <EntryCard
          key={entry.id}
          entry={entry}
          open={openId === entry.id}
          onToggle={() => setOpenId(openId === entry.id ? null : entry.id)}
        />
      ))}
    </>
  );
}

function EntryCard({
  entry,
  open,
  onToggle,
}: {
  entry: JournalEntry;
  open: boolean;
  onToggle: () => void;
}) {
  const debits = entry.lines.reduce((total, line) => total + Number(line.debit), 0);
  const credits = entry.lines.reduce((total, line) => total + Number(line.credit), 0);
  const balanced = Math.abs(debits - credits) < 0.005;

  return (
    <Card
      title={`${entry.voucher_no} · ${entry.entry_date}`}
      subtitle={entry.narration ?? undefined}
      actions={
        <>
          <Pill tone={SOURCE_TONE[entry.source] ?? "neutral"}>{entry.source}</Pill>
          <Pill tone={balanced ? "positive" : "negative"}>
            {balanced ? "balanced" : "unbalanced"}
          </Pill>
          <button onClick={onToggle}>{open ? "Hide lines" : "Show lines"}</button>
        </>
      }
    >
      <p className="small muted" style={{ marginTop: 0 }}>
        {entry.lines.length} lines · entered by {entry.posted_by} ·{" "}
        {fmtDateTime(entry.posted_at)}
      </p>
      {open ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Account</th>
                <th>Segment</th>
                <th>Narration</th>
                <th className="numeric">Debit</th>
                <th className="numeric">Credit</th>
              </tr>
            </thead>
            <tbody>
              {entry.lines.map((line, index) => (
                <tr key={`${entry.id}-${index}`}>
                  <td className="numeric" style={{ textAlign: "left" }}>
                    {line.account_code}
                  </td>
                  <td>{line.segment}</td>
                  <td className="muted small">{line.narration ?? "—"}</td>
                  <td className="numeric">{Number(line.debit) ? fmt(line.debit) : "—"}</td>
                  <td className="numeric">{Number(line.credit) ? fmt(line.credit) : "—"}</td>
                </tr>
              ))}
              <tr className="total-row">
                <td colSpan={3}>Total</td>
                <td className="numeric">{fmt(debits.toFixed(4))}</td>
                <td className="numeric">{fmt(credits.toFixed(4))}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : null}
    </Card>
  );
}
