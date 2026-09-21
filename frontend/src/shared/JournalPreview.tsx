/** Renders a proposed journal entry, with the balance check made explicit. */

import { fmt } from "./format";
import type { JournalLinePreview } from "./types";

export default function JournalPreview({
  lines,
  balanced,
}: {
  lines: JournalLinePreview[];
  balanced: boolean;
}) {
  const debits = lines.reduce((total, line) => total + Number(line.debit), 0);
  const credits = lines.reduce((total, line) => total + Number(line.credit), 0);

  return (
    <div className="journal-preview">
      <div className={`balanced-banner ${balanced ? "" : "unbalanced"}`}>
        <span>{balanced ? "✓ Balanced — debits equal credits" : "× Not balanced"}</span>
        <span className="numeric">
          {fmt(debits.toFixed(2))} / {fmt(credits.toFixed(2))}
        </span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th className="numeric">Debit</th>
              <th className="numeric">Credit</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={`${line.account_code}-${index}`}>
                <td>
                  <div>
                    {line.account_code} · {line.account_name}
                  </div>
                  <div className="muted small">{line.segment}</div>
                </td>
                <td className="numeric">{Number(line.debit) ? fmt(line.debit) : "—"}</td>
                <td className="numeric">{Number(line.credit) ? fmt(line.credit) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
