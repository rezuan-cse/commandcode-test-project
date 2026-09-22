import { useState } from "react";
import { ErrorBox } from "./ui";

/**
 * Undo a posted transaction.
 *
 * Deliberately not a one-click action, and deliberately not a prompt() dialog.
 * Reversing changes the accounts and the stock, so the reason is asked for in
 * the page itself and required before the button becomes available.
 */
export function ReverseButton({
  label = "Reverse",
  onReverse,
  disabled = false,
}: {
  label?: string;
  onReverse: (reason: string) => Promise<void>;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} disabled={disabled} title="Undo this posting">
        {label}
      </button>
    );
  }

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await onReverse(reason.trim());
      setOpen(false);
      setReason("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="reverse-form">
      <p className="small muted" style={{ margin: "0 0 6px" }}>
        This posts a mirror entry and puts the stock back. The original stays on the
        record, marked as reversed. Nothing is deleted.
      </p>
      <input
        autoFocus
        placeholder="Why is this being reversed?"
        value={reason}
        onChange={(event) => setReason(event.target.value)}
      />
      {error && <ErrorBox message={error} />}
      <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
        <button
          className="primary"
          onClick={confirm}
          disabled={busy || reason.trim().length < 3}
        >
          {busy ? "Reversing…" : "Confirm reversal"}
        </button>
        <button
          onClick={() => {
            setOpen(false);
            setReason("");
            setError(null);
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

/** The badge shown on a transaction that has been undone. */
export function ReversedBadge({ reason }: { reason?: string | null }) {
  return (
    <span className="pill pill-negative" title={reason ?? undefined}>
      reversed
    </span>
  );
}
