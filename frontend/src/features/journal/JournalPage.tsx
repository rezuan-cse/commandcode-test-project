import { useState } from "react";
import { api } from "../../shared/api";
import { fmt } from "../../shared/format";
import { Card, Empty, Pill, Spinner, ErrorBox } from "../../shared/ui";
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
      ) : (
        <p className="small muted" style={{ margin: 0 }}>
          {entry.lines.length} lines · entered by {entry.posted_by}
        </p>
      )}
    </Card>
  );
}
