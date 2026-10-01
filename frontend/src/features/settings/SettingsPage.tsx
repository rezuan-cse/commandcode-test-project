import { useEffect, useMemo, useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { Card, ErrorBox, Pill, Spinner, Toggle } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { Setting } from "../../shared/types";

/**
 * Headings and notes for each configuration group. The group keys come from the
 * server; these strings only name them. Mirrors GROUP_TITLES in the backend's
 * settings/catalog.py.
 */
const GROUP_META: Record<string, { title: string; note: string }> = {
  company: {
    title: "Company details",
    note: "Printed on the documents the system produces.",
  },
  vat: { title: "VAT", note: "Rate and scope. Left off until the rules are confirmed." },
  tax: {
    title: "AIT, TDS and VDS",
    note: "Withholding rates, pending the client's tax adviser.",
  },
  payroll: {
    title: "Payroll",
    note: "Salary structure and deductions, editable without a redeploy.",
  },
  posting: {
    title: "Posting controls",
    note: "Whether a second person must approve an action before it commits.",
  },
  security: { title: "Security", note: "Login hardening options." },
  inventory: { title: "Inventory", note: "Costing method used by the stock ledger." },
  sales: { title: "Sales documents", note: "What a sales document looks like." },
  other: { title: "Other", note: "" },
};

/** Strip the JSON quotes the store keeps around scalar values. */
function displayValue(setting: Setting): string {
  if (setting.value_type === "json") {
    try {
      return JSON.stringify(JSON.parse(setting.value), null, 2);
    } catch {
      return setting.value;
    }
  }
  return setting.value.replace(/^"|"$/g, "");
}

function SettingRow({
  setting,
  canEdit,
  onSaved,
}: {
  setting: Setting;
  canEdit: boolean;
  onSaved: (updated: Setting) => void;
}) {
  const [draft, setDraft] = useState(() => displayValue(setting));
  const [confirmed, setConfirmed] = useState(setting.confirmed_by_client);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(displayValue(setting));
    setConfirmed(setting.confirmed_by_client);
  }, [setting]);

  const save = async (confirm?: boolean) => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const nextConfirmed = confirm === undefined ? confirmed : confirm;
      const updated = await api.updateSetting(setting.key, draft, nextConfirmed);
      setConfirmed(updated.confirmed_by_client);
      setSaved(true);
      onSaved(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const dirty = draft !== displayValue(setting) || confirmed !== setting.confirmed_by_client;

  return (
    <tr>
      <td className="name-cell">
        <span style={{ fontFamily: "var(--mono)" }}>{setting.key}</span>
        <div className="muted small">{setting.label}</div>
      </td>
      <td>
        {canEdit ? (
          <SettingInput setting={setting} value={draft} onChange={setDraft} />
        ) : (
          <span style={{ fontFamily: "var(--mono)" }}>{displayValue(setting)}</span>
        )}
        {error && <div className="error-box small">{error}</div>}
      </td>
      <td>
        <Pill tone={confirmed ? "positive" : "warn"}>
          {confirmed ? "confirmed" : "pending client"}
        </Pill>
      </td>
      <td className="muted small">{setting.description ?? "—"}</td>
      {canEdit && (
        <td>
          <div className="row-actions">
            <button onClick={() => save()} disabled={saving || !dirty}>
              {saving ? "Saving…" : "Save"}
            </button>
            {!confirmed && (
              <button
                className="link"
                onClick={() => save(true)}
                disabled={saving}
                title="Mark this value as confirmed by the client"
              >
                Confirm
              </button>
            )}
            {saved && <span className="muted small">saved</span>}
          </div>
        </td>
      )}
    </tr>
  );
}

function SettingInput({
  setting,
  value,
  onChange,
}: {
  setting: Setting;
  value: string;
  onChange: (value: string) => void;
}) {
  if (setting.value_type === "bool") {
    return (
      <Toggle
        checked={value === "true"}
        onChange={(next) => onChange(next ? "true" : "false")}
        ariaLabel={setting.label}
      />
    );
  }
  if (setting.value_type === "enum") {
    return (
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {(setting.options ?? []).map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }
  if (setting.value_type === "number") {
    return (
      <input
        type="text"
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }
  if (setting.value_type === "json") {
    return (
      <textarea
        rows={4}
        style={{ fontFamily: "var(--mono)", width: "100%" }}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }
  return (
    <input
      type="text"
      style={{ width: "100%" }}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const canEdit = user?.role === "Admin";
  const { data, loading, error } = useAsync(() => api.settings(), []);
  const [items, setItems] = useState<Setting[] | null>(null);

  useEffect(() => {
    if (data) setItems(data);
  }, [data]);

  const groups = useMemo(() => {
    const map = new Map<string, Setting[]>();
    for (const setting of items ?? []) {
      const bucket = map.get(setting.group);
      if (bucket) bucket.push(setting);
      else map.set(setting.group, [setting]);
    }
    return Array.from(map.entries());
  }, [items]);

  const onSaved = (updated: Setting) =>
    setItems((current) =>
      current ? current.map((item) => (item.key === updated.key ? updated : item)) : current,
    );

  return (
    <>
      <h1>Configuration</h1>
      <p className="page-intro">
        Nothing the client has not yet confirmed is hardcoded. Rates, structures and control
        switches live in this table and can be changed here without a code change or a
        redeploy. Entries marked <em>pending client</em> are the open questions from the
        specification.
        {!canEdit && " Only an administrator can change these values."}
      </p>

      {loading && <Spinner />}
      {error && <ErrorBox message={error} />}

      {groups.map(([group, rows]) => {
        const meta = GROUP_META[group] ?? { title: group, note: "" };
        return (
          <Card key={group} title={meta.title} subtitle={meta.note}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Setting</th>
                    <th>Value</th>
                    <th>Status</th>
                    <th>Description</th>
                    {canEdit && <th />}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((setting) => (
                    <SettingRow
                      key={setting.key}
                      setting={setting}
                      canEdit={canEdit}
                      onSaved={onSaved}
                    />
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
