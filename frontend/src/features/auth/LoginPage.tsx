import { useState } from "react";
import { useAuth } from "../../shared/AuthContext";
import { Card, ErrorBox, Field } from "../../shared/ui";

/** The demo accounts, shown so a reviewer can switch roles without guesswork. */
const DEMO_ACCOUNTS = [
  { email: "admin@rpci.demo", role: "Admin", can: "everything" },
  { email: "accountant@rpci.demo", role: "Accountant", can: "journals, reports" },
  { email: "store@rpci.demo", role: "Store / Production", can: "items, production" },
  { email: "sales@rpci.demo", role: "Sales Staff", can: "purchases, sales" },
  { email: "owner@rpci.demo", role: "Owner / Viewer", can: "read only" },
];

export default function LoginPage() {
  const { signIn, submitCode } = useAuth();
  const [email, setEmail] = useState("admin@rpci.demo");
  const [password, setPassword] = useState("rpci");
  const [code, setCode] = useState("");
  const [challengeToken, setChallengeToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePassword(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await signIn(email.trim(), password);
      if (result.needsTwoFactor && result.challengeToken) {
        setChallengeToken(result.challengeToken);
        setCode("");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function handleCode(event: React.FormEvent) {
    event.preventDefault();
    if (!challengeToken) return;
    setError(null);
    setBusy(true);
    try {
      await submitCode(challengeToken, code.trim());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-panel">
        <div className="login-brand">
          <span className="brand-mark">RPCI</span>
          <span className="brand-sub">Accounting &amp; Production ERP</span>
        </div>

        {error && <ErrorBox message={error} />}

        {challengeToken === null ? (
          <Card title="Sign in" subtitle="Enter your email and password">
            <form onSubmit={handlePassword}>
              <Field label="Email">
                <input
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </Field>
              <Field label="Password">
                <input
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Field>
              <button className="primary" type="submit" disabled={busy}>
                {busy ? "Signing in…" : "Sign in"}
              </button>
            </form>
          </Card>
        ) : (
          <Card
            title="Two-factor authentication"
            subtitle="Enter the six-digit code from your authenticator app"
          >
            <form onSubmit={handleCode}>
              <Field
                label="Code"
                hint="Or one of your recovery codes, if you cannot use the app."
              >
                <input
                  inputMode="text"
                  autoComplete="one-time-code"
                  autoFocus
                  placeholder="123456"
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                />
              </Field>
              <div style={{ display: "flex", gap: 10 }}>
                <button className="primary" type="submit" disabled={busy || !code.trim()}>
                  {busy ? "Checking…" : "Verify"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setChallengeToken(null);
                    setError(null);
                  }}
                >
                  Back
                </button>
              </div>
            </form>
          </Card>
        )}

        <Card title="Demo accounts" subtitle="All use the password rpci">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Can do</th>
                </tr>
              </thead>
              <tbody>
                {DEMO_ACCOUNTS.map((account) => (
                  <tr
                    key={account.email}
                    onClick={() => {
                      setEmail(account.email);
                      setPassword("rpci");
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <td style={{ fontFamily: "var(--mono)", fontSize: 12 }}>
                      {account.email}
                    </td>
                    <td>{account.role}</td>
                    <td className="muted small">{account.can}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small muted" style={{ marginTop: 10, marginBottom: 0 }}>
            Click a row to fill the form. Signing in as different people is how you
            see the permission rules applied — the server refuses a restricted
            action regardless of what the screen shows.
          </p>
        </Card>
      </div>
    </div>
  );
}
