import { useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { Card, ErrorBox, Field, Pill } from "../../shared/ui";
import type { TotpSetupResponse } from "../../shared/types";

/**
 * Account security: two-factor enrolment and password change.
 *
 * Enrolment is deliberately two steps — scan, then prove the app works — so
 * nobody can lock themselves out by switching 2FA on with a secret their
 * authenticator never actually accepted.
 */
export default function SecurityPage() {
  const { user, refreshUser } = useAuth();
  const [setup, setSetup] = useState<TotpSetupResponse | null>(null);
  const [code, setCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [password, setPassword] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!user) return null;

  function reset() {
    setError(null);
    setNotice(null);
  }

  async function begin() {
    reset();
    setBusy(true);
    try {
      setSetup(await api.setupTwoFactor());
      setRecoveryCodes(null);
      setCode("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    reset();
    setBusy(true);
    try {
      const result = await api.enableTwoFactor(code.trim());
      setRecoveryCodes(result.recovery_codes);
      setSetup(null);
      setNotice(result.message);
      await refreshUser();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    reset();
    setBusy(true);
    try {
      await api.disableTwoFactor(password);
      setPassword("");
      setRecoveryCodes(null);
      setNotice("Two-factor authentication is off.");
      await refreshUser();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function changePassword() {
    reset();
    setBusy(true);
    try {
      await api.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setNotice("Password changed.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Security</h1>
      <p className="page-intro">
        Your account, {user.full_name} ({user.email}), signed in as {user.role}.
        Passwords are stored hashed, and the second factor is verified on the
        server before any session is issued.
      </p>

      {error && <ErrorBox message={error} />}
      {notice && <div className="toast">✓ {notice}</div>}

      <Card
        title="Two-factor authentication"
        subtitle="A six-digit code from an authenticator app, in addition to your password"
        actions={
          <Pill tone={user.is_2fa_enabled ? "positive" : "warn"}>
            {user.is_2fa_enabled ? "on" : "off"}
          </Pill>
        }
      >
        {user.is_2fa_enabled && !recoveryCodes && (
          <>
            <p className="small muted" style={{ marginTop: 0 }}>
              Two-factor authentication is protecting this account. Turning it off
              requires your password.
            </p>
            <Field label="Confirm your password to turn it off">
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            <button onClick={disable} disabled={busy || !password}>
              Turn off two-factor authentication
            </button>
          </>
        )}

        {!user.is_2fa_enabled && !setup && !recoveryCodes && (
          <>
            <p className="small muted" style={{ marginTop: 0 }}>
              You will need an authenticator app — Google Authenticator, Authy, or
              any app that reads QR codes.
            </p>
            <button className="primary" onClick={begin} disabled={busy}>
              {busy ? "Preparing…" : "Set up two-factor authentication"}
            </button>
          </>
        )}

        {setup && (
          <>
            <p className="small muted" style={{ marginTop: 0 }}>
              Scan this with your authenticator app, then enter the code it shows to
              prove it worked.
            </p>
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
              <img
                src={setup.qr_png_data_uri}
                alt="Two-factor enrolment QR code"
                width={180}
                height={180}
                style={{ border: "1px solid var(--line)", borderRadius: 8 }}
              />
              <div style={{ minWidth: 260 }}>
                <Field label="Or type this key into the app">
                  <input readOnly value={setup.secret} style={{ fontFamily: "var(--mono)" }} />
                </Field>
                <Field label="Code from the app">
                  <input
                    inputMode="numeric"
                    placeholder="123456"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                  />
                </Field>
                <div style={{ display: "flex", gap: 10 }}>
                  <button className="primary" onClick={confirm} disabled={busy || code.trim().length !== 6}>
                    Turn on
                  </button>
                  <button onClick={() => setSetup(null)}>Cancel</button>
                </div>
              </div>
            </div>
          </>
        )}

        {recoveryCodes && (
          <>
            <p className="small muted" style={{ marginTop: 0 }}>
              <strong>Save these now.</strong> They are shown once and are the only
              way back in if you lose your authenticator.
            </p>
            <div className="recovery-codes">
              {recoveryCodes.map((value) => (
                <span key={value}>{value}</span>
              ))}
            </div>
          </>
        )}
      </Card>

      <Card title="Change password" subtitle="At least eight characters">
        <div className="form-row">
          <Field label="Current password">
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
            />
          </Field>
          <Field label="New password">
            <input
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </Field>
        </div>
        <button
          className="primary"
          onClick={changePassword}
          disabled={busy || !currentPassword || newPassword.length < 8}
        >
          Change password
        </button>
      </Card>
    </>
  );
}
