import { useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { Card, ErrorBox, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { AuditEntry, UserRow } from "../../shared/types";

const ACCESS_LABEL: Record<string, string> = {
  full: "Full",
  view: "View",
  none: "—",
};

export default function AccessPage() {
  const matrix = useAsync(() => api.roleMatrix(), []);
  const { user, refreshUser } = useAuth();
  const role = user?.role ?? "";
  const isAdmin = role === "Admin";

  return (
    <>
      <h1>Roles &amp; Access</h1>
      <p className="page-intro">
        Permissions are enforced on the server, in the API layer, not hidden in the
        interface. A restricted user receives a 403 even if they reach the screen.
        Menus a role cannot read are hidden, and screens it may read but not change
        open without their forms.
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
                          <Pill tone="info">you</Pill>
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
        {isAdmin && <AccountsPanel onChanged={refreshUser} currentUserId={user?.id} />}
      </div>

      {isAdmin && <AuditPanel />}
    </>
  );
}

/**
 * Account administration. Only rendered for administrators, and every action is
 * checked again by the server.
 */
function AccountsPanel({
  onChanged,
  currentUserId,
}: {
  onChanged: () => Promise<void>;
  currentUserId?: number;
}) {
  const users = useAsync(() => api.users(), []);
  const { refresh } = useDemo();
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [issued, setIssued] = useState<{ email: string; password: string } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  /** Run an action, then refresh the lists so the change is visible. */
  async function run(userId: number, action: () => Promise<string>) {
    setBusy(userId);
    setError(null);
    setNotice(null);
    setIssued(null);
    try {
      setNotice(await action());
      refresh();
      await onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(null);
    }
  }

  async function resetPassword(row: UserRow) {
    setBusy(row.id);
    setError(null);
    setNotice(null);
    setIssued(null);
    try {
      const result = await api.resetUserPassword(row.id);
      setIssued({ email: row.email, password: result.password });
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card
      title="User accounts"
      subtitle="Unlock someone who cannot get in, or turn an account off"
    >
      {error && <ErrorBox message={error} />}
      {notice && <div className="toast">✓ {notice}</div>}
      {issued && (
        <div className="notice">
          <strong>New password for {issued.email}</strong>
          <div className="issued-password">{issued.password}</div>
          Give this to them directly. It is shown once and is not stored anywhere
          readable.
        </div>
      )}

      {users.loading && <Spinner />}
      {users.error && <ErrorBox message={users.error} />}
      {users.data && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>2FA</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users.data.map((row) => {
                const self = row.id === currentUserId;
                return (
                  <tr key={row.id}>
                    <td>
                      <div className="name-cell">{row.full_name}</div>
                      <div className="muted small">{row.email}</div>
                    </td>
                    <td>{row.role}</td>
                    <td>
                      <Pill tone={row.is_2fa_enabled ? "positive" : "neutral"}>
                        {row.is_2fa_enabled ? "on" : "off"}
                      </Pill>
                    </td>
                    <td>
                      <Pill tone={row.is_active ? "positive" : "negative"}>
                        {row.is_active ? "active" : "disabled"}
                      </Pill>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          disabled={busy !== null || !row.is_2fa_enabled || self}
                          title={
                            self
                              ? "Use the Security page for your own account"
                              : "Clear their second factor so a password is enough"
                          }
                          onClick={() =>
                            run(row.id, async () => (await api.resetTwoFactor(row.id)).message)
                          }
                        >
                          Reset 2FA
                        </button>
                        <button
                          disabled={busy !== null || self}
                          title={
                            self
                              ? "Use the Security page for your own account"
                              : "Issue a new password"
                          }
                          onClick={() => resetPassword(row)}
                        >
                          Reset password
                        </button>
                        <button
                          disabled={busy !== null || self}
                          title={
                            self
                              ? "You cannot disable your own account"
                              : row.is_active
                                ? "Stop this account signing in"
                                : "Let this account sign in again"
                          }
                          onClick={() =>
                            run(
                              row.id,
                              async () =>
                                (
                                  await api.setUserActive(row.id, !row.is_active)
                                ).message,
                            )
                          }
                        >
                          {row.is_active ? "Disable" : "Enable"}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="small muted" style={{ marginTop: 10, marginBottom: 0 }}>
        Actions on your own account are disabled here — use the Security page. Every
        action below is recorded.
      </p>
    </Card>
  );
}

/** The record of administrative actions, so "who reset this" has an answer. */
function AuditPanel() {
  // useAsync already refetches when the demo revision changes, which the
  // accounts panel bumps after every action, so this list stays current.
  const entries = useAsync(() => api.auditLog(), []);

  return (
    <Card
      title="Administrative actions"
      subtitle="Clearing a second factor or issuing a password is recorded, newest first"
    >
      {entries.loading && <Spinner />}
      {entries.error && <ErrorBox message={entries.error} />}
      {entries.data && entries.data.length === 0 && (
        <p className="small muted" style={{ margin: 0 }}>
          Nothing recorded yet.
        </p>
      )}
      {entries.data && entries.data.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Action</th>
                <th>By</th>
                <th>Account</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {entries.data.map((entry: AuditEntry) => (
                <tr key={entry.id}>
                  <td className="muted small">{entry.created_at.slice(0, 19).replace("T", " ")}</td>
                  <td>{entry.action.replace(/_/g, " ")}</td>
                  <td className="muted small">{entry.actor_email}</td>
                  <td className="muted small">{entry.target_email}</td>
                  <td className="muted small">{entry.detail ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function PermissionProbe() {
  const { user } = useAuth();
  const role = user?.role ?? "";
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function probe() {
    setBusy(true);
    setResult(null);
    try {
      await api.accounts();
      setResult({ ok: true, message: `GET /api/accounts allowed for "${role}"` });
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
    <Card title="Live permission probe" subtitle="Calls the API as the signed-in user">
      <p className="small muted" style={{ marginTop: 0 }}>
        Reading the chart of accounts is permitted for Admin, Accountant, and
        Owner/Viewer, and refused for Store/Production and Sales staff. This calls
        the real endpoint with your session, so the answer comes from the server.
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
