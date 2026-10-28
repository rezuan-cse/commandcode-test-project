import { useMemo, useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { csvFilename } from "../../shared/csv";
import { ErrorBox, Card, Empty, ExportButton, Field, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";

const SEGMENTS = ["", "Import", "Manufacturing", "Packaging", "Trading", "Application", "Shared"];
const TYPES = [
  "",
  "Asset",
  "Liability",
  "Equity",
  "Revenue",
  "COGS",
  "Expense",
  "Other Income",
];

/** What the form edits. The code is only editable while the account is new. */
interface AccountDraft {
  code: string;
  name_en: string;
  name_bn: string;
  account_type: string;
  segment: string;
  normal_balance: "Dr" | "Cr";
  is_active: boolean;
  isNew: boolean;
}

const BLANK: AccountDraft = {
  code: "",
  name_en: "",
  name_bn: "",
  account_type: "Asset",
  segment: "Shared",
  normal_balance: "Dr",
  is_active: true,
  isNew: true,
};

export default function AccountsPage() {
  const { can } = useAuth();
  const { refresh } = useDemo();
  const canWrite = can("accounts", true);
  const [segment, setSegment] = useState("");
  const [accountType, setAccountType] = useState("");
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState<AccountDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const { data, loading, error: loadError } = useAsync(
    () =>
      api.accounts({
        segment: segment || undefined,
        account_type: accountType || undefined,
        search: search || undefined,
      }),
    [segment, accountType, search],
  );

  const counts = useMemo(() => {
    if (!data) return { total: 0, segments: 0 };
    return {
      total: data.length,
      segments: new Set(data.map((account) => account.segment)).size,
    };
  }, [data]);

  function startAdd() {
    setError(null);
    setMessage(null);
    setDraft({ ...BLANK });
  }

  function startEdit(account: NonNullable<typeof data>[number]) {
    setError(null);
    setMessage(null);
    setDraft({
      code: account.code,
      name_en: account.name_en,
      name_bn: account.name_bn ?? "",
      account_type: account.account_type,
      segment: account.segment,
      normal_balance: account.normal_balance,
      is_active: account.is_active,
      isNew: false,
    });
  }

  async function save() {
    if (!draft) return;
    setBusy(true);
    setError(null);
    try {
      const details = {
        name_en: draft.name_en.trim(),
        name_bn: draft.name_bn.trim() || null,
        account_type: draft.account_type,
        segment: draft.segment,
        normal_balance: draft.normal_balance,
      };
      if (draft.isNew) {
        const created = await api.createAccount({ ...details, code: draft.code.trim() });
        setMessage(`Account ${created.code} added.`);
      } else {
        await api.updateAccount(draft.code, { ...details, is_active: draft.is_active });
        setMessage(`Account ${draft.code} saved.`);
      }
      setDraft(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Chart of Accounts</h1>
      <p className="page-intro">
        Every account carries a segment tag, which is what makes segment-wise reporting
        possible. All other modules reference this list — no screen in the system accepts a
        free-text account. A new company starts with a standard chart; add your own bank
        accounts, fixed assets and expense heads here as you need them.
      </p>

      {error && <ErrorBox message={error} />}
      {message && (
        <p className="small" style={{ color: "var(--positive)" }}>
          {message}
        </p>
      )}

      {draft && (
        <Card
          title={draft.isNew ? "New account" : `Edit ${draft.code}`}
          subtitle={
            draft.isNew
              ? "The code is the key every other record points at, so it is fixed once the account exists"
              : "The code cannot be changed; everything else can be corrected"
          }
          actions={
            <button onClick={() => setDraft(null)} disabled={busy}>
              Cancel
            </button>
          }
        >
          <div className="form-row">
            <Field label="Code">
              <input
                value={draft.code}
                disabled={!draft.isNew}
                placeholder="e.g. 1020"
                onChange={(event) => setDraft({ ...draft, code: event.target.value })}
              />
            </Field>
            <Field label="Name">
              <input
                value={draft.name_en}
                placeholder="e.g. Bank — Current Account"
                onChange={(event) => setDraft({ ...draft, name_en: event.target.value })}
              />
            </Field>
            <Field label="Name (Bangla)" hint="Optional.">
              <input
                value={draft.name_bn}
                onChange={(event) => setDraft({ ...draft, name_bn: event.target.value })}
              />
            </Field>
          </div>
          <div className="form-row">
            <Field label="Type">
              <select
                value={draft.account_type}
                onChange={(event) => setDraft({ ...draft, account_type: event.target.value })}
              >
                {TYPES.filter(Boolean).map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Segment">
              <select
                value={draft.segment}
                onChange={(event) => setDraft({ ...draft, segment: event.target.value })}
              >
                {SEGMENTS.filter(Boolean).map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Normal balance" hint="Which side increases this account.">
              <select
                value={draft.normal_balance}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    normal_balance: event.target.value as "Dr" | "Cr",
                  })
                }
              >
                <option value="Dr">Dr</option>
                <option value="Cr">Cr</option>
              </select>
            </Field>
          </div>
          {!draft.isNew && (
            <Field label="Active" hint="An inactive account keeps its history but is no longer offered.">
              <select
                value={draft.is_active ? "yes" : "no"}
                onChange={(event) =>
                  setDraft({ ...draft, is_active: event.target.value === "yes" })
                }
              >
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            </Field>
          )}
          <button
            className="primary"
            onClick={save}
            disabled={busy || !draft.code.trim() || !draft.name_en.trim()}
          >
            {busy ? "Saving…" : draft.isNew ? "Add account" : "Save changes"}
          </button>
        </Card>
      )}

      <Card
        title={`${counts.total} accounts across ${counts.segments} segments`}
        subtitle="Filter by segment, type, or search by code and name"
        actions={
          <>
            {canWrite && (
              <button onClick={startAdd} disabled={draft !== null}>
                Add account
              </button>
            )}
            <ExportButton
              filename={csvFilename("chart-of-accounts")}
              rows={data}
              columns={[
                { header: "Code", value: (row) => row.code },
                { header: "Name", value: (row) => row.name_en },
                { header: "Name (Bangla)", value: (row) => row.name_bn },
                { header: "Type", value: (row) => row.account_type },
                { header: "Segment", value: (row) => row.segment },
                { header: "Normal balance", value: (row) => row.normal_balance },
                { header: "Active", value: (row) => (row.is_active ? "yes" : "no") },
              ]}
            />
          </>
        }
      >
        <div className="form-row" style={{ marginBottom: 16 }}>
          <label className="field" style={{ marginBottom: 0 }}>
            <span className="field-label">Segment</span>
            <select value={segment} onChange={(event) => setSegment(event.target.value)}>
              {SEGMENTS.map((value) => (
                <option key={value || "all"} value={value}>
                  {value || "All segments"}
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span className="field-label">Type</span>
            <select value={accountType} onChange={(event) => setAccountType(event.target.value)}>
              {TYPES.map((value) => (
                <option key={value || "all"} value={value}>
                  {value || "All types"}
                </option>
              ))}
            </select>
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span className="field-label">Search</span>
            <input
              type="search"
              placeholder="e.g. Inventory or 1210"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>

        {loading && <Spinner />}
        {loadError && <ErrorBox message={loadError} />}
        {data && data.length === 0 && <Empty message="No accounts match those filters." />}

        {data && data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Account name</th>
                  <th>Type</th>
                  <th>Segment</th>
                  <th>Normal balance</th>
                  <th>Active</th>
                  {canWrite && <th />}
                </tr>
              </thead>
              <tbody>
                {data.map((account) => (
                  <tr key={account.code}>
                    <td className="numeric" style={{ textAlign: "left" }}>
                      {account.code}
                    </td>
                    <td className="name-cell">{account.name_en}</td>
                    <td>
                      <Pill tone={typeTone(account.account_type)}>{account.account_type}</Pill>
                    </td>
                    <td>{account.segment}</td>
                    <td>{account.normal_balance}</td>
                    <td className="muted small">{account.is_active ? "Yes" : "No"}</td>
                    {canWrite && (
                      <td className="numeric">
                        <button className="ghost" onClick={() => startEdit(account)}>
                          Edit
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}

function typeTone(type: string): "neutral" | "positive" | "negative" | "warn" | "info" {
  if (type === "Asset") return "info";
  if (type === "Liability") return "warn";
  if (type === "Equity") return "positive";
  if (type === "Revenue" || type === "Other Income") return "positive";
  if (type === "COGS" || type === "Expense") return "negative";
  return "neutral";
}
