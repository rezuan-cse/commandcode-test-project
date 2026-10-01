import { useEffect, useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { Card, ErrorBox, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import { menuLabels } from "../../shared/nav";
import type { Access, AuditEntry, UserRow } from "../../shared/types";

const ACCESS_LABEL: Record<string, string> = {
  full: "Full",
  view: "View",
  none: "—",
};

const LEVELS: Access[] = ["none", "view", "full"];

/** "2026-09-29T14:03:11" as "2026-09-29 14:03". */
function when(iso: string | null): string {
  if (!iso) return "—";
  return iso.slice(0, 16).replace("T", " ");
}

interface Draft {
  id: number | null;
  email: string;
  full_name: string;
  role: string;
  password: string;
}

const BLANK: Draft = { id: null, email: "", full_name: "", role: "", password: "" };

export default function AccessPage() {
  const matrix = useAsync(() => api.roleMatrix(), []);
  const { user, refreshUser } = useAuth();
  const role = user?.role ?? "";
  const isAdmin = role === "Admin";

  return (
    <>
      <h1>Roles &amp; Access</h1>
      <p className="page-intro">
        Each role has a default set of permissions, shown first. An administrator can
        grant or deny an area to one person on top of their role — the change applies
        from their next request, and the server enforces it whatever the menu shows.
      </p>

      {matrix.loading && <Spinner />}
      {matrix.error && <ErrorBox message={matrix.error} />}

      {matrix.data && (
        <Card
          title="Permission matrix"
          subtitle="What each role may do by default, before any per-user grant"
        >
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

      {matrix.data && (
        <Card
          title="Menus by role"
          subtitle="The menu groups each role is offered, from the same rules the sidebar uses"
        >
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Menus offered</th>
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
                    <td>{menuLabels(row.access as Record<string, Access>).join(" · ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small muted" style={{ marginTop: 12, marginBottom: 0 }}>
            Hiding a menu is a convenience only — what a person may read or change is
            enforced by the server. Granting an area below adds its menu for that person.
          </p>
        </Card>
      )}

      {isAdmin && matrix.data && (
        <AccountsPanel
          roles={matrix.data.roles.map((row) => row.role)}
          resources={matrix.data.resources}
          onChanged={refreshUser}
          currentUserId={user?.id}
        />
      )}

      {isAdmin && <AuditPanel />}
    </>
  );
}

/**
 * Account administration. Only rendered for administrators, and every action is
 * checked again by the server.
 */
function AccountsPanel({
  roles,
  resources,
  onChanged,
  currentUserId,
}: {
  roles: string[];
  resources: string[];
  onChanged: () => Promise<void>;
  currentUserId?: number;
}) {
  const users = useAsync(() => api.users(), []);
  const { refresh } = useDemo();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [accessFor, setAccessFor] = useState<UserRow | null>(null);
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

  async function saveDraft() {
    if (!draft) return;
    setBusy(-1);
    setError(null);
    setNotice(null);
    setIssued(null);
    try {
      if (draft.id === null) {
        const created = await api.createUser({
          email: draft.email,
          full_name: draft.full_name,
          role: draft.role,
          password: draft.password || undefined,
        });
        setNotice(created.message);
        if (created.password) {
          setIssued({ email: created.user.email, password: created.password });
        }
      } else {
        await api.updateUser(draft.id, {
          email: draft.email,
          full_name: draft.full_name,
          role: draft.role,
        });
        setNotice("Account updated.");
      }
      setDraft(null);
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
      subtitle="Add a colleague, change their details or role, or grant them an area their role does not cover"
      actions={
        <button
          className="primary"
          onClick={() =>
            setDraft({ ...BLANK, role: roles.includes("Sales Staff") ? "Sales Staff" : roles[0] })
          }
          disabled={busy !== null}
        >
          Add user
        </button>
      }
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

      {draft && (
        <div className="sub-card">
          <h2 style={{ marginTop: 0 }}>
            {draft.id === null ? "Add a user" : `Edit ${draft.full_name}`}
          </h2>
          <div className="form-row" style={{ marginBottom: 12 }}>
            <label className="field">
              <span className="field-label">Full name</span>
              <input
                value={draft.full_name}
                onChange={(event) => setDraft({ ...draft, full_name: event.target.value })}
              />
            </label>
            <label className="field">
              <span className="field-label">Email</span>
              <input
                type="email"
                value={draft.email}
                onChange={(event) => setDraft({ ...draft, email: event.target.value })}
              />
            </label>
            <label className="field">
              <span className="field-label">Role</span>
              <select
                value={draft.role}
                onChange={(event) => setDraft({ ...draft, role: event.target.value })}
              >
                {roles.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            {draft.id === null && (
              <label className="field">
                <span className="field-label">Password (optional)</span>
                <input
                  type="text"
                  placeholder="Leave blank to generate one"
                  value={draft.password}
                  onChange={(event) => setDraft({ ...draft, password: event.target.value })}
                />
              </label>
            )}
          </div>
          <div className="row-actions">
            <button
              className="primary"
              onClick={saveDraft}
              disabled={busy !== null || !draft.email || !draft.full_name}
            >
              {busy === -1 ? "Saving…" : draft.id === null ? "Add user" : "Save changes"}
            </button>
            <button onClick={() => setDraft(null)}>Cancel</button>
          </div>
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
                <th>Created</th>
                <th>Updated</th>
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
                    <td className="muted small">{when(row.created_at)}</td>
                    <td className="muted small">{when(row.updated_at)}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          disabled={busy !== null}
                          title="Change their name, email or role"
                          onClick={() =>
                            setDraft({
                              id: row.id,
                              email: row.email,
                              full_name: row.full_name,
                              role: row.role,
                              password: "",
                            })
                          }
                        >
                          Edit
                        </button>
                        <button
                          disabled={busy !== null || self}
                          title={
                            self
                              ? "You cannot change your own access"
                              : "Grant or deny areas on top of their role"
                          }
                          onClick={() => setAccessFor(accessFor?.id === row.id ? null : row)}
                        >
                          Access
                        </button>
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
                              async () => (await api.setUserActive(row.id, !row.is_active)).message,
                            )
                          }
                        >
                          {row.is_active ? "Disable" : "Enable"}
                        </button>
                        <button
                          disabled={busy !== null || self}
                          title={self ? "You cannot delete your own account" : "Remove this account"}
                          onClick={() =>
                            run(row.id, async () => (await api.deleteUser(row.id)).message)
                          }
                        >
                          Delete
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

      {accessFor && (
        <AccessEditor
          target={accessFor}
          resources={resources}
          onClose={() => setAccessFor(null)}
          onSaved={async (message) => {
            setNotice(message);
            refresh();
            await onChanged();
            setAccessFor(null);
          }}
        />
      )}

      <p className="small muted" style={{ marginTop: 10, marginBottom: 0 }}>
        Actions on your own account are disabled here — use the Security page. Every
        action above is recorded.
      </p>
    </Card>
  );
}

/** Grant or deny one person areas, on top of what their role already gives. */
function AccessEditor({
  target,
  resources,
  onClose,
  onSaved,
}: {
  target: UserRow;
  resources: string[];
  onClose: () => void;
  onSaved: (message: string) => Promise<void>;
}) {
  const current = useAsync(() => api.userPermissions(target.id), [target.id]);
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Start from what is recorded: an override, or "default" meaning follow the role.
  useEffect(() => {
    if (!current.data) return;
    const overrides = current.data.overrides;
    setChoice(
      Object.fromEntries(
        resources.map((resource) => [resource, overrides[resource] ?? "default"]),
      ),
    );
  }, [current.data, resources]);

  async function save() {
    if (!current.data) return;
    setBusy(true);
    setError(null);
    try {
      // "Follow the role" is sent as the role's own level, which the server reads
      // as "no exception" and removes the stored grant.
      const access = Object.fromEntries(
        resources.map((resource) => [
          resource,
          choice[resource] === "default"
            ? current.data!.role_defaults[resource]
            : choice[resource],
        ]),
      );
      await api.setUserPermissions(target.id, access);
      await onSaved(`Access updated for ${target.full_name}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sub-card">
      <h2 style={{ marginTop: 0 }}>Access for {target.full_name}</h2>
      <p className="small muted" style={{ marginTop: 0 }}>
        Their role is <strong>{target.role}</strong>. Anything left on{" "}
        <em>Follow the role</em> is not stored, so a later change to the role reaches
        them again.
      </p>
      {error && <ErrorBox message={error} />}
      {current.loading && <Spinner />}
      {current.error && <ErrorBox message={current.error} />}
      {current.data && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Area</th>
                <th>Role gives</th>
                <th>This person</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((resource) => (
                <tr key={resource}>
                  <td className="name-cell">{resource.replace(/_/g, " ")}</td>
                  <td className="muted small">
                    {ACCESS_LABEL[current.data!.role_defaults[resource]]}
                  </td>
                  <td>
                    <select
                      aria-label={`Access to ${resource}`}
                      value={choice[resource] ?? "default"}
                      onChange={(event) =>
                        setChoice({ ...choice, [resource]: event.target.value })
                      }
                    >
                      <option value="default">Follow the role</option>
                      {LEVELS.map((level) => (
                        <option key={level} value={level}>
                          {level === "none" ? "No access" : ACCESS_LABEL[level]}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="row-actions" style={{ marginTop: 12 }}>
        <button className="primary" onClick={save} disabled={busy || current.loading}>
          {busy ? "Saving…" : "Save access"}
        </button>
        <button onClick={onClose}>Cancel</button>
      </div>
    </div>
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
      subtitle="Creating, changing and removing accounts is recorded, newest first"
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
