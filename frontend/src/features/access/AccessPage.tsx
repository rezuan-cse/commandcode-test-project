import { useState } from "react";
import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { Card, ErrorBox, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";

const ACCESS_LABEL: Record<string, string> = {
  full: "Full",
  view: "View",
  none: "—",
};

export default function AccessPage() {
  const matrix = useAsync(() => api.roleMatrix(), []);
  const users = useAsync(() => api.users(), []);
  const { role } = useDemo();

  return (
    <>
      <h1>Roles &amp; Access</h1>
      <p className="page-intro">
        Permissions are enforced on the server, in the API layer, not hidden in the interface. A
        restricted user receives a 403 even if they reach the screen. Switch the acting role in the
        top bar, then try the probe below to see the enforcement for yourself.
      </p>

      {matrix.loading && <Spinner />}
      {matrix.error && <ErrorBox message={matrix.error} />}

      {matrix.data && (
        <Card title="Permission matrix" subtitle="Transcribed from the agreed specification">
          <div className="table-wrap">
            <table className="matrix">
              <thead>
                <tr>
                  <th>Role</th>
                  {matrix.data.resources.map((resource) => (
                    <th key={resource}>{resource.replace(/_/g, " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.data.roles.map((row) => (
                  <tr key={row.role}>
                    <td className="name-cell">
                      {row.role}
                      {row.role === role && (
                        <>
                          {" "}
                          <Pill tone="info">acting</Pill>
                        </>
                      )}
                    </td>
                    {matrix.data!.resources.map((resource) => (
                      <td key={resource} className={`access-${row.access[resource]}`}>
                        {ACCESS_LABEL[row.access[resource]]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <div className="grid grid-2">
        <PermissionProbe />

        <Card title="Users" subtitle="One demo account per role">
          {users.loading && <Spinner />}
          {users.error && <ErrorBox message={users.error} />}
          {users.data && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                  </tr>
                </thead>
                <tbody>
                  {users.data.map((user) => (
                    <tr key={user.id}>
                      <td className="name-cell">{user.full_name}</td>
                      <td className="muted small">{user.email}</td>
                      <td>{user.role}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}

function PermissionProbe() {
  const { role } = useDemo();
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function probe() {
    setBusy(true);
    setResult(null);
    try {
      await api.accounts();
      setResult({
        ok: true,
        message: `GET /api/accounts allowed for "${role}"`,
      });
    } catch (error) {
      setResult({
        ok: false,
        message: `GET /api/accounts blocked for "${role}": ${
          error instanceof Error ? error.message : String(error)
        }`,
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Live permission probe" subtitle="Calls the API as the acting role">
      <p className="small muted" style={{ marginTop: 0 }}>
        Reading the chart of accounts is permitted for Admin, Accountant, and Owner/Viewer, and
        refused for Store/Production and Sales staff. This calls the real endpoint.
      </p>
      <button className="primary" onClick={probe} disabled={busy}>
        {busy ? "Calling…" : `Call the API as "${role}"`}
      </button>
      {result && (
        <div className={result.ok ? "toast" : "error-box"} style={{ marginTop: 14, marginBottom: 0 }}>
          {result.message}
        </div>
      )}
    </Card>
  );
}
