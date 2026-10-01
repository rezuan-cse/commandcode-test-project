import { useState } from "react";
import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt, fmtDateTime } from "../../shared/format";
import { Card, ErrorBox, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { ApprovalRequest } from "../../shared/types";

const SOURCE_LABELS: Record<string, string> = {
  sale: "Sale",
  purchase: "Purchase",
  production: "Production run",
  payroll: "Payroll run",
};

const STATUS_TONE: Record<string, "warn" | "positive" | "negative"> = {
  pending: "warn",
  approved: "positive",
  rejected: "negative",
};

export default function ApprovalsPage() {
  const { refresh } = useDemo();
  const requests = useAsync(() => api.approvals(), []);

  const [notes, setNotes] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(id: number, decision: "approve" | "reject") {
    setBusy(id);
    setError(null);
    try {
      if (decision === "approve") await api.approveApproval(id, notes[id]);
      else await api.rejectApproval(id, notes[id]);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(null);
    }
  }

  const rows = requests.data ?? [];
  const pending = rows.filter((row) => row.status === "pending");

  return (
    <>
      <h1>Approvals</h1>
      <p className="page-intro">
        Actions that need a second person are held here. Approving carries the action out as
        you; a request you raised yourself cannot be approved by you. Only an area you have
        write access to is shown.
      </p>

      {error && <ErrorBox message={error} />}

      <Card title="Pending" subtitle={`${pending.length} waiting`}>
        {requests.loading && <Spinner />}
        {requests.error && <ErrorBox message={requests.error} />}
        {!requests.loading && pending.length === 0 && (
          <p className="small muted" style={{ margin: 0 }}>
            Nothing is waiting for approval.
          </p>
        )}
        {pending.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Raised</th>
                  <th className="numeric">Amount</th>
                  <th>Requested by</th>
                  <th>Reason</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {pending.map((row: ApprovalRequest) => (
                  <tr key={row.id}>
                    <td className="name-cell">
                      Reverse {SOURCE_LABELS[row.source_type] ?? row.source_type} #{row.source_id}
                    </td>
                    <td className="muted small">{fmtDateTime(row.created_at)}</td>
                    <td className="numeric">{row.amount ? fmt(row.amount) : "—"}</td>
                    <td>{row.requested_by}</td>
                    <td className="muted small">{row.reason}</td>
                    <td>
                      <div className="row-actions">
                        <input
                          placeholder="note (optional)"
                          value={notes[row.id] ?? ""}
                          onChange={(event) =>
                            setNotes({ ...notes, [row.id]: event.target.value })
                          }
                          style={{ width: 140 }}
                        />
                        <button
                          className="primary"
                          disabled={busy === row.id}
                          onClick={() => decide(row.id, "approve")}
                        >
                          Approve
                        </button>
                        <button disabled={busy === row.id} onClick={() => decide(row.id, "reject")}>
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="History">
        {requests.data && rows.length === pending.length && (
          <p className="small muted" style={{ margin: 0 }}>
            No decided requests yet.
          </p>
        )}
        {rows.length > pending.length && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Raised</th>
                  <th className="numeric">Amount</th>
                  <th>Requested by</th>
                  <th>Status</th>
                  <th>Decided</th>
                  <th>Decided by</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {rows
                  .filter((row) => row.status !== "pending")
                  .map((row) => (
                    <tr key={row.id}>
                      <td className="name-cell">
                        Reverse {SOURCE_LABELS[row.source_type] ?? row.source_type} #{row.source_id}
                      </td>
                      <td className="muted small">{fmtDateTime(row.created_at)}</td>
                      <td className="numeric">{row.amount ? fmt(row.amount) : "—"}</td>
                      <td>{row.requested_by}</td>
                      <td>
                        <Pill tone={STATUS_TONE[row.status] ?? "neutral"}>{row.status}</Pill>
                      </td>
                      <td className="muted small">{fmtDateTime(row.decided_at)}</td>
                      <td className="muted small">{row.decided_by ?? "—"}</td>
                      <td className="muted small">{row.note ?? "—"}</td>
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
