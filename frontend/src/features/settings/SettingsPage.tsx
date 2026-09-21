import { api } from "../../shared/api";
import { Card, ErrorBox, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";

const GROUPS: { prefix: string; title: string; note: string }[] = [
  {
    prefix: "vat.",
    title: "VAT",
    note: "Rate and accounts are configurable. The exact rules are still open with the client.",
  },
  {
    prefix: "tax.",
    title: "Tax",
    note: "AIT and TDS rates are configurable pending the client's confirmation.",
  },
  {
    prefix: "payroll.",
    title: "Payroll",
    note: "Salary structure and statutory deductions are configurable placeholders.",
  },
  {
    prefix: "inventory.",
    title: "Inventory",
    note: "Costing method used by the stock ledger.",
  },
  {
    prefix: "posting.",
    title: "Posting controls",
    note: "Whether a second person must approve a posting before it commits.",
  },
  {
    prefix: "security.",
    title: "Security",
    note: "Login hardening options held for a later phase.",
  },
];

export default function SettingsPage() {
  const { data, loading, error } = useAsync(() => api.settings(), []);

  return (
    <>
      <h1>Configuration</h1>
      <p className="page-intro">
        Nothing the client has not yet confirmed is hardcoded. Rates, structures, and control
        switches live in this table and can be changed without a code change or a redeploy. Items
        marked as unconfirmed are the open questions from the specification.
      </p>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} />}

      {data &&
        GROUPS.map((group) => {
          const rows = data.filter((setting) => setting.key.startsWith(group.prefix));
          if (rows.length === 0) return null;
          return (
            <Card key={group.prefix} title={group.title} subtitle={group.note}>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Key</th>
                      <th>Value</th>
                      <th>Status</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((setting) => (
                      <tr key={setting.key}>
                        <td className="name-cell" style={{ fontFamily: "var(--mono)" }}>
                          {setting.key}
                        </td>
                        <td style={{ fontFamily: "var(--mono)" }}>
                          {setting.value.replace(/^"|"$/g, "")}
                        </td>
                        <td>
                          <Pill tone={setting.confirmed_by_client ? "positive" : "warn"}>
                            {setting.confirmed_by_client ? "confirmed" : "pending client"}
                          </Pill>
                        </td>
                        <td className="muted small">{setting.description ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          );
        })}
    </>
  );
}
