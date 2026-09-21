import { useMemo, useState } from "react";
import { api } from "../../shared/api";
import { ErrorBox, Card, Empty, Pill, Spinner } from "../../shared/ui";
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

export default function AccountsPage() {
  const [segment, setSegment] = useState("");
  const [accountType, setAccountType] = useState("");
  const [search, setSearch] = useState("");

  const { data, loading, error } = useAsync(
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

  return (
    <>
      <h1>Chart of Accounts</h1>
      <p className="page-intro">
        Imported directly from the client's workbook. Every account carries a segment tag, which
        is what makes segment-wise reporting possible. All other modules reference this list — no
        screen in the system accepts a free-text account.
      </p>

      <Card
        title={`${counts.total} accounts across ${counts.segments} segments`}
        subtitle="Filter by segment, type, or search by code and name"
        actions={
          <>
            <Pill tone="info">Admin / Accountant only</Pill>
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
        {error && <ErrorBox message={error} />}
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
