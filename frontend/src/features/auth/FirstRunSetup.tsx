import { useState } from "react";
import { useAuth } from "../../shared/AuthContext";
import { api } from "../../shared/api";
import { Card, ErrorBox, Field } from "../../shared/ui";

/**
 * First-run setup: create the one account the system cannot start without.
 *
 * A hosted deployment seeds no demo accounts, so a brand-new database has nobody
 * who can sign in and the sign-in form had nothing to accept. This is shown
 * instead, and only while the server reports that the user table is empty.
 *
 * The server refuses a second call once an account exists, so this cannot be used
 * later to mint an administrator — from then on they are made from Roles & Access.
 */
export default function FirstRunSetup({ companyName }: { companyName?: string }) {
  const { adoptSession } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const longEnough = password.length >= 8;
  const matches = password === confirm;
  const canSubmit =
    fullName.trim().length > 0 &&
    email.trim().length > 2 &&
    longEnough &&
    matches &&
    !busy;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setBusy(true);
    try {
      const session = await api.createFirstAdmin({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
      });
      adoptSession(session.access_token, session.user);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
      setBusy(false);
    }
  }

  return (
    <Card
      title="Create your administrator"
      subtitle={
        companyName
          ? `First run for ${companyName}. This account can do everything.`
          : "First run. This account can do everything."
      }
    >
      {error && <ErrorBox message={error} />}
      <p className="small muted" style={{ marginTop: 0 }}>
        There are no accounts yet, so this is the one that gets in. Add your
        colleagues afterwards from Administration → Roles &amp; Access, each with
        the role that matches their job.
      </p>
      <form onSubmit={submit}>
        <Field label="Your name">
          <input
            autoFocus
            autoComplete="name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
          />
        </Field>
        <Field label="Email" hint="This is the address you will sign in with.">
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </Field>
        <Field label="Password" hint="At least 8 characters.">
          <input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <Field
          label="Confirm password"
          hint={
            confirm.length > 0 && !matches ? "The two passwords do not match." : undefined
          }
        >
          <input
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
          />
        </Field>
        <button className="primary" type="submit" disabled={!canSubmit}>
          {busy ? "Creating…" : "Create administrator"}
        </button>
      </form>
    </Card>
  );
}
