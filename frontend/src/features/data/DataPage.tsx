import { useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { Card, ErrorBox } from "../../shared/ui";

/**
 * Import the client's existing workbook, or start over.
 *
 * Importing replaces the books, so it is deliberately a deliberate act with a
 * confirmation step — not something a stray click can do.
 */
export default function DataPage() {
  const { user } = useAuth();
  const { refresh } = useDemo();
  const [file, setFile] = useState<File | null>(null);
  const [replace, setReplace] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const isAdmin = user?.role === "Admin";

  if (!isAdmin) {
    return (
      <>
        <h1>Data</h1>
        <p className="page-intro">
          Only an administrator can import a workbook or reset the books.
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
        The books start from a standard starter chart of accounts. Import the client's existing
        workbook to replace them, or start over at any time. Importing and resetting are
        irreversible.
      </p>

      {message && <div className="toast">✓ {message}</div>}
      {error && <ErrorBox message={error} />}

      <Card
        title="Import an existing workbook"
        subtitle="An .xlsx with the same sheets as the sample — Chart of Accounts, Item Master, and so on"
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
          <label className="inline-field">
            <input
              type="checkbox"
              checked={replace}
              onChange={(event) => setReplace(event.target.checked)}
            />
            <span>Replace the books (empty them first)</span>
          </label>
        </div>

        <div className="notice">
          Importing replaces every account, item, opening balance, journal entry and stock
          movement. Users and configuration are kept.
        </div>

        <div style={{ marginTop: 14 }}>
          <button
            className="primary"
            disabled={!file || busy}
            onClick={() => run(async () => (await api.importData(file as File, replace)).message)}
          >
            {busy ? "Working…" : "Import workbook"}
          </button>
        </div>
      </Card>

      <Card title="Start over" subtitle="These actions cannot be undone">
        <div className="row-actions">
          <button
            disabled={busy}
            onClick={() => run(async () => (await api.resetData("fresh")).message)}
          >
            Start fresh (starter accounts)
          </button>
          <button
            disabled={busy}
            onClick={() => run(async () => (await api.resetData("workbook")).message)}
          >
            Restore sample workbook
          </button>
          <button
            disabled={busy}
            onClick={() => run(async () => (await api.resetData("none")).message)}
          >
            Empty everything
          </button>
        </div>
      </Card>
    </>
  );
}
