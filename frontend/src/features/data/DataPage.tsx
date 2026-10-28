import { useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { useAsync } from "../../shared/useAsync";
import { Card, ErrorBox } from "../../shared/ui";

/**
 * Two ways to begin: a new company, or one that already has books.
 *
 * They are presented as equals. Import used to be the only card with a primary
 * button, which read as "this is the real path" — wrong for a company that has no
 * existing data at all, and has no workbook to bring.
 *
 * Both are deliberate acts with a confirmation, because both replace the books.
 */
export default function DataPage() {
  const { user } = useAuth();
  const { refresh } = useDemo();
  const meta = useAsync(() => api.meta(), []);
  const [file, setFile] = useState<File | null>(null);
  const [replace, setReplace] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const isAdmin = user?.role === "Admin";
  // The server refuses a reset when RPCI_ALLOW_DATA_RESET is off. Showing buttons
  // that always fail is worse than not showing them, so "Start over" is hidden in
  // that case. Importing a workbook is unaffected — it is the supported way to load
  // data, and stays available even there.
  const canReset = meta.data?.data_reset !== false;

  if (!isAdmin) {
    return (
      <>
        <h1>Data</h1>
        <p className="page-intro">
          Only an administrator can import a workbook or start the books over.
        </p>
      </>
    );
  }

  async function run(work: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setMessage(await work());
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Data</h1>
      <p className="page-intro">
        Two ways to begin. Start a new company from the standard chart of accounts, or bring
        existing books in from a workbook. Either action replaces what is here now, so neither
        is offered as the default.
      </p>

      {message && <div className="toast">✓ {message}</div>}
      {error && <ErrorBox message={error} />}

      <div className="grid grid-2">
        <Card
          title="Starting a new company"
          subtitle="Begins with no transactions — you enter the opening figures yourself"
        >
          <p className="small muted" style={{ marginTop: 0 }}>
            The books open with a standard chart of accounts covering every automatic posting,
            plus bank accounts, fixed assets, loans and the usual expense heads. Add your own
            accounts, items and recipes, record the capital introduced as a journal entry, then
            start trading. Nothing is pre-filled, so nothing has to be cleared out later.
          </p>
          <ul className="small muted" style={{ marginTop: 0, paddingLeft: 18 }}>
            <li>Keep the standard chart, or edit it under Chart of Accounts.</li>
            <li>Your first entry is usually Dr Cash and Bank / Cr Share Capital.</li>
            <li>The Dashboard checklist tracks what is left to set up.</li>
          </ul>
          {canReset ? (
            <button
              disabled={busy}
              onClick={() => run(async () => (await api.resetData("fresh")).message)}
            >
              {busy ? "Working…" : "Start fresh"}
            </button>
          ) : (
            <p className="small muted" style={{ marginBottom: 0 }}>
              This deployment is already configured. Starting over is disabled here
              (<code>RPCI_ALLOW_DATA_RESET=false</code>).
            </p>
          )}
        </Card>

        <Card
          title="Coming from an existing system"
          subtitle="Import a workbook with the same sheets as the sample"
        >
          <div className="form-row" style={{ marginBottom: 14 }}>
            <label className="field">
              <span className="field-label">Workbook (.xlsx)</span>
              <input
                type="file"
                accept=".xlsx"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>
          </div>
          <label className="check-row" style={{ marginBottom: 14 }}>
            <input
              type="checkbox"
              checked={replace}
              onChange={(event) => setReplace(event.target.checked)}
            />
            <span>Replace the books (empty them first)</span>
          </label>

          <div className="notice">
            Importing replaces every account, item, opening balance, journal entry and stock
            movement. Users and configuration are kept.
          </div>

          <div style={{ marginTop: 14 }}>
            <button
              disabled={!file || busy}
              onClick={() =>
                run(async () => (await api.importData(file as File, replace)).message)
              }
            >
              {busy ? "Working…" : "Import workbook"}
            </button>
          </div>
        </Card>
      </div>

      {canReset && (
        <Card title="Other" subtitle="These actions cannot be undone">
          <div className="row-actions">
            <button
              disabled={busy}
              onClick={() => run(async () => (await api.resetData("workbook")).message)}
            >
              Restore sample workbook
            </button>
          </div>
          <p className="small muted" style={{ marginTop: 10, marginBottom: 0 }}>
            Loads the demonstration workbook, replacing what is here — useful for training or for
            checking the screens against known figures. There is deliberately no "empty
            everything": a system with no chart of accounts cannot post anything, and rebuilding
            it by hand is an accident waiting to happen.
          </p>
        </Card>
      )}
    </>
  );
}
