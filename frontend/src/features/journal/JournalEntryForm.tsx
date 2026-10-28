import { useMemo, useState } from "react";
import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt } from "../../shared/format";
import { Card, ErrorBox } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { Account, JournalEntry } from "../../shared/types";

/**
 * A manual journal entry.
 *
 * This is how a company records things no document produces: opening capital on
 * the first day, depreciation, an adjustment, a reclassification. Without it a
 * brand-new company could not enter its share capital at all, because opening
 * balances otherwise only arrive from an imported workbook.
 *
 * The segment is taken from the account rather than asked for separately: an
 * account already belongs to one segment, and letting the two disagree would put
 * the same money in two different columns of the segment reports.
 */
interface DraftLine {
  key: number;
  account_code: string;
  debit: string;
  credit: string;
}

let nextKey = 1;

function blankLine(): DraftLine {
  return { key: nextKey++, account_code: "", debit: "", credit: "" };
}

/** The next free JV- number, so a duplicate is the exception rather than the rule. */
function suggestVoucher(existing: { voucher_no: string }[]): string {
  const used = new Set(existing.map((entry) => entry.voucher_no));
  let n = 1;
  while (used.has(`JV-${String(n).padStart(4, "0")}`)) n += 1;
  return `JV-${String(n).padStart(4, "0")}`;
}

function asAmount(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.round(parsed * 10000) / 10000 : 0;
}

export default function JournalEntryForm({
  existing,
  defaultDate,
}: {
  existing: JournalEntry[];
  defaultDate: string;
}) {
  const accounts = useAsync(() => api.accounts(), []);
  const { refresh } = useDemo();
  const [voucher, setVoucher] = useState(() => suggestVoucher(existing));
  const [date, setDate] = useState(defaultDate);
  const [narration, setNarration] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([blankLine(), blankLine()]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const debitTotal = lines.reduce((sum, line) => sum + asAmount(line.debit), 0);
  const creditTotal = lines.reduce((sum, line) => sum + asAmount(line.credit), 0);
  const balanced = debitTotal > 0 && Math.abs(debitTotal - creditTotal) < 0.0001;

  // Only active accounts can be posted to, and each line needs exactly one side.
  const options = (accounts.data ?? []).filter((account: Account) => account.is_active);
  const usableLines = lines.filter(
    (line) => line.account_code && (asAmount(line.debit) > 0 || asAmount(line.credit) > 0),
  );
  const canPost =
    balanced && usableLines.length >= 2 && voucher.trim().length > 0 && !busy;

  const segmentOf = useMemo(() => {
    const map = new Map<string, string>();
    for (const account of accounts.data ?? []) map.set(account.code, account.segment);
    return map;
  }, [accounts.data]);

  function update(key: number, patch: Partial<DraftLine>) {
    setLines((current) =>
      current.map((line) => (line.key === key ? { ...line, ...patch } : line)),
    );
  }

  async function post() {
    if (!canPost) return;
    setBusy(true);
    setError(null);
    try {
      await api.postJournalEntry({
        voucher_no: voucher.trim(),
        entry_date: date,
        narration: narration.trim() || null,
        lines: usableLines.map((line) => ({
          account_code: line.account_code,
          segment: segmentOf.get(line.account_code) ?? "Shared",
          debit: asAmount(line.debit) > 0 ? line.debit : "0",
          credit: asAmount(line.credit) > 0 ? line.credit : "0",
        })),
      });
      refresh();
      setVoucher(suggestVoucher([...existing, { voucher_no: voucher.trim() }]));
      setNarration("");
      setLines([blankLine(), blankLine()]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title="New journal entry"
      subtitle="A balanced entry posted directly to the ledger — opening capital, depreciation, an adjustment"
    >
      <p className="small muted" style={{ marginTop: 0 }}>
        A new company's first entry is usually the capital introduced: debit{" "}
        <strong>1010 Cash and Bank</strong> and credit <strong>3000 Share Capital</strong>{" "}
        for the same amount, dated the first day of trading. Debits must equal credits
        before it can be posted, and a posted entry is never edited — a mistake is
        reversed.
      </p>

      {error && <ErrorBox message={error} />}

      <div className="form-row" style={{ marginBottom: 12 }}>
        <label className="field">
          <span className="field-label">Date</span>
          <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Voucher</span>
          <input value={voucher} onChange={(event) => setVoucher(event.target.value)} />
        </label>
        <label className="field" style={{ flex: 1 }}>
          <span className="field-label">Narration</span>
          <input
            placeholder="Share capital introduced"
            value={narration}
            onChange={(event) => setNarration(event.target.value)}
          />
        </label>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th className="numeric">Debit</th>
              <th className="numeric">Credit</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {lines.map((line) => (
              <tr key={line.key}>
                <td>
                  <select
                    value={line.account_code}
                    onChange={(event) => update(line.key, { account_code: event.target.value })}
                  >
                    <option value="">Choose an account…</option>
                    {options.map((account) => (
                      <option key={account.code} value={account.code}>
                        {account.code} — {account.name_en}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="numeric">
                  <input
                    className="numeric"
                    inputMode="decimal"
                    placeholder="0.00"
                    value={line.debit}
                    // A line is one side or the other, never both; the server
                    // rejects both, so the form prevents it rather than explaining it.
                    onChange={(event) => update(line.key, { debit: event.target.value, credit: "" })}
                  />
                </td>
                <td className="numeric">
                  <input
                    className="numeric"
                    inputMode="decimal"
                    placeholder="0.00"
                    value={line.credit}
                    onChange={(event) => update(line.key, { credit: event.target.value, debit: "" })}
                  />
                </td>
                <td className="numeric">
                  <button
                    type="button"
                    className="ghost"
                    disabled={lines.length <= 2}
                    onClick={() =>
                      setLines((current) => current.filter((row) => row.key !== line.key))
                    }
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>
                <strong>Total</strong>
              </td>
              <td className="numeric">{fmt(debitTotal.toFixed(4))}</td>
              <td className="numeric">{fmt(creditTotal.toFixed(4))}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>

      <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 12 }}>
        <button
          type="button"
          onClick={() => setLines((current) => [...current, blankLine()])}
        >
          Add line
        </button>
        <button className="primary" type="button" onClick={post} disabled={!canPost}>
          {busy ? "Posting…" : "Post entry"}
        </button>
        <span className="small muted">
          {balanced
            ? "Debits equal credits."
            : `Difference ${fmt(Math.abs(debitTotal - creditTotal).toFixed(4))} — the entry must balance before it can be posted.`}
        </span>
      </div>
    </Card>
  );
}
