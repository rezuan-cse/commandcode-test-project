import { useState } from "react";
import { api } from "../../shared/api";
import { useAuth } from "../../shared/AuthContext";
import { useDemo } from "../../shared/DemoContext";
import { fmt } from "../../shared/format";
import { PermissionNotice } from "../../shared/PermissionNotice";
import { csvFilename } from "../../shared/csv";
import {
  Card,
  Empty,
  ErrorBox,
  ExportButton,
  Field,
  Pill,
  Spinner,
} from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type {
  OutstandingInvoice,
  Payment,
  PaymentDirection,
  PaymentPreview,
} from "../../shared/types";

interface Draft {
  direction: PaymentDirection;
  party_code: string;
  pay_date: string;
  amount: string;
  money_account: string;
  reference: string;
  memo: string;
  allocations: { sale_order_id?: number; purchase_order_id?: number; amount: string }[];
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function PaymentsPage() {
  const { user, can, level } = useAuth();
  const { refresh } = useDemo();
  const canRead = can("payments");
  const canWrite = can("payments", true);

  const payments = useAsync(() => api.payments(), []);
  const outstanding = useAsync(() => api.outstandingInvoices(), []);
  const accounts = useAsync(() => api.moneyAccounts(), []);
  const parties = useAsync(() => api.parties(), []);

  const [draft, setDraft] = useState<Draft | null>(null);
  const [settling, setSettling] = useState<OutstandingInvoice | null>(null);
  const [applying, setApplying] = useState<Payment | null>(null);
  const [reversing, setReversing] = useState<{ id: number; reason: string } | null>(null);
  const [preview, setPreview] = useState<PaymentPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!canRead) {
    return (
      <>
        <h1>Receipts &amp; Payments</h1>
        <PermissionNotice
          role={user?.role ?? ""}
          resource="payments"
          write={false}
          level={level("payments")}
        />
      </>
    );
  }

  const invoices = outstanding.data ?? [];
  const moneyAccounts = accounts.data ?? [];

  /** Open the form, optionally pre-filled to settle one invoice. */
  function start(direction: PaymentDirection, invoice?: OutstandingInvoice) {
    setError(null);
    setMessage(null);
    setPreview(null);
    setSettling(invoice ?? null);
    setDraft({
      direction,
      party_code: invoice?.party_code ?? "",
      pay_date: today(),
      amount: invoice?.outstanding ?? "",
      money_account: moneyAccounts[0] ?? "1010",
      reference: "",
      memo: "",
      allocations: invoice ? [allocFor(invoice)] : [],
    });
  }

  async function runPreview() {
    if (!draft) return;
    setError(null);
    setBusy(true);
    try {
      setPreview(await api.previewPayment(payload(draft)));
    } catch (caught) {
      setPreview(null);
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!draft) return;
    setError(null);
    setBusy(true);
    try {
      const posted = await api.postPayment(payload(draft));
      setMessage(
        posted.on_account === "0.0000"
          ? `${posted.voucher_no} recorded against ${posted.party_name}.`
          : `${posted.voucher_no} recorded for ${posted.party_name}, with ` +
            `${fmt(posted.on_account)} held on account.`,
      );
      setDraft(null);
      setSettling(null);
      setPreview(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function applyCredit() {
    if (!applying || !draft) return;
    setError(null);
    setBusy(true);
    try {
      await api.allocatePayment(applying.id, draft.allocations);
      setMessage(`Applied to ${applying.voucher_no}.`);
      setApplying(null);
      setDraft(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function confirmReverse() {
    if (!reversing) return;
    setError(null);
    setBusy(true);
    try {
      await api.reversePayment(reversing.id, reversing.reason);
      setMessage("Reversed. The invoices it settled are outstanding again.");
      setReversing(null);
      refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
    } finally {
      setBusy(false);
    }
  }

  /** The invoices the open form may settle: this partner's, in this direction. */
  function settlableFor(current: Draft): OutstandingInvoice[] {
    const kind = current.direction === "Receipt" ? "sale" : "purchase";
    return invoices.filter(
      (row) => row.kind === kind && row.party_code === current.party_code,
    );
  }

  return (
    <>
      <h1>Receipts &amp; Payments</h1>
      <p className="page-intro">
        Money in from a customer, money out to a supplier. A receipt or payment can
        settle one invoice, several, or none at all — money with no invoice to settle
        is held <strong>on account</strong> for that customer or supplier, which is
        what a deposit is, and can be applied to an invoice later.
      </p>

      {message && <div className="toast">✓ {message}</div>}
      {error && <ErrorBox message={error} />}

      {reversing && (
        <Card
          title="Reverse this receipt or payment"
          subtitle="The money goes back and the invoices it settled become outstanding again"
          actions={<button onClick={() => setReversing(null)}>Cancel</button>}
        >
          <Field label="Reason" hint="Kept on the record — “returned cheque” is a good one">
            <input
              value={reversing.reason}
              onChange={(event) =>
                setReversing({ ...reversing, reason: event.target.value })
              }
            />
          </Field>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              className="primary"
              onClick={confirmReverse}
              disabled={busy || reversing.reason.trim().length < 3}
            >
              {busy ? "Reversing…" : "Reverse"}
            </button>
            <button onClick={() => setReversing(null)}>Cancel</button>
          </div>
        </Card>
      )}

      {canWrite && draft && (
        <Card
          title={settling ? `Settle ${settling.invoice_no}` : "New receipt or payment"}
          subtitle={
            settling
              ? `${settling.party_name} · ${fmt(settling.outstanding)} outstanding`
              : "Leave the invoice list empty to hold the money on account"
          }
          actions={
            <button
              onClick={() => {
                setDraft(null);
                setSettling(null);
                setPreview(null);
              }}
            >
              Cancel
            </button>
          }
        >
          <div className="form-row">
            <Field label="Type">
              <select
                value={draft.direction}
                disabled={Boolean(settling)}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    direction: event.target.value as PaymentDirection,
                    party_code: "",
                    allocations: [],
                  })
                }
              >
                <option value="Receipt">Receipt — money in</option>
                <option value="Payment">Payment — money out</option>
              </select>
            </Field>
            <Field label={draft.direction === "Receipt" ? "Customer" : "Supplier"}>
              <select
                value={draft.party_code}
                disabled={Boolean(settling)}
                onChange={(event) =>
                  setDraft({ ...draft, party_code: event.target.value, allocations: [] })
                }
              >
                <option value="">Choose…</option>
                {partiesFor(draft, parties.data ?? []).map((party) => (
                  <option key={party.code} value={party.code}>
                    {party.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Date">
              <input
                type="date"
                value={draft.pay_date}
                onChange={(event) => setDraft({ ...draft, pay_date: event.target.value })}
              />
            </Field>
          </div>

          <div className="form-row">
            <Field label="Amount">
              <input
                className="numeric"
                inputMode="decimal"
                value={draft.amount}
                onChange={(event) => setDraft({ ...draft, amount: event.target.value })}
              />
            </Field>
            <Field label="Account" hint="Where the money moved">
              <select
                value={draft.money_account}
                onChange={(event) =>
                  setDraft({ ...draft, money_account: event.target.value })
                }
              >
                {moneyAccounts.map((code) => (
                  <option key={code} value={code}>
                    {code}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Reference" hint="Cheque or receipt number">
              <input
                value={draft.reference}
                onChange={(event) => setDraft({ ...draft, reference: event.target.value })}
              />
            </Field>
          </div>

          <Field label="Note">
            <input
              value={draft.memo}
              onChange={(event) => setDraft({ ...draft, memo: event.target.value })}
            />
          </Field>

          <h3 style={{ margin: "18px 0 6px" }}>Invoices this settles</h3>
          <p className="small muted" style={{ marginTop: 0 }}>
            {settlableFor(draft).length === 0
              ? "Nothing outstanding for this customer or supplier, so the money will sit on account until there is an invoice to apply it to."
              : "Leave a line out and that part of the money stays on account."}
          </p>
          {draft.allocations.map((row, index) => (
            <div className="form-row" key={index} style={{ alignItems: "flex-end" }}>
              <Field label="Invoice">
                <span className="small">
                  {invoiceLabel(invoices, row) ?? "—"}
                </span>
              </Field>
              <Field label="Amount">
                <input
                  className="numeric"
                  inputMode="decimal"
                  value={row.amount}
                  onChange={(event) => {
                    const allocations = [...draft.allocations];
                    allocations[index] = { ...row, amount: event.target.value };
                    setDraft({ ...draft, allocations });
                  }}
                />
              </Field>
              <div style={{ paddingBottom: 2 }}>
                <button
                  onClick={() =>
                    setDraft({
                      ...draft,
                      allocations: draft.allocations.filter((_, i) => i !== index),
                    })
                  }
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
          {settlableFor(draft).length > draft.allocations.length && (
            <button
              onClick={() => {
                const chosen = new Set(
                  draft.allocations.map(
                    (row) => row.sale_order_id ?? row.purchase_order_id,
                  ),
                );
                const next = settlableFor(draft).find(
                  (row) => !chosen.has(row.invoice_id),
                );
                if (!next) return;
                setDraft({
                  ...draft,
                  allocations: [...draft.allocations, allocFor(next)],
                });
              }}
            >
              Add invoice
            </button>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button className="primary" onClick={save} disabled={busy || !draft.party_code}>
              {busy ? "Saving…" : "Record"}
            </button>
            <button onClick={runPreview} disabled={busy || !draft.party_code}>
              Preview entry
            </button>
          </div>

          {preview && (
            <div className="table-wrap" style={{ marginTop: 16 }}>
              <table>
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Narration</th>
                    <th className="numeric">Debit</th>
                    <th className="numeric">Credit</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.journal_lines.map((line) => (
                    <tr key={line.account_code + line.narration}>
                      <td className="name-cell">
                        {line.account_code} — {line.account_name}
                      </td>
                      <td className="muted small">{line.narration}</td>
                      <td className="numeric">{Number(line.debit) ? fmt(line.debit) : "—"}</td>
                      <td className="numeric">
                        {Number(line.credit) ? fmt(line.credit) : "—"}
                      </td>
                    </tr>
                  ))}
                  <tr className="total-row">
                    <td colSpan={2}>
                      {fmt(preview.allocated)} settles invoices ·{" "}
                      {fmt(preview.on_account)} on account
                    </td>
                    <td className="numeric">{fmt(preview.amount)}</td>
                    <td className="numeric">{fmt(preview.amount)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {canWrite && applying && (
        <Card
          title={`Apply ${fmt(applying.on_account)} held for ${applying.party_name}`}
          subtitle="The money has already been received; this decides which invoices it settles"
          actions={
            <button
              onClick={() => {
                setApplying(null);
                setDraft(null);
              }}
            >
              Cancel
            </button>
          }
        >
          {draft?.allocations.map((row, index) => (
            <div className="form-row" key={index} style={{ alignItems: "flex-end" }}>
              <Field label="Invoice">
                <span className="small">{invoiceLabel(invoices, row) ?? "—"}</span>
              </Field>
              <Field label="Amount">
                <input
                  className="numeric"
                  inputMode="decimal"
                  value={row.amount}
                  onChange={(event) => {
                    const allocations = [...draft.allocations];
                    allocations[index] = { ...row, amount: event.target.value };
                    setDraft({ ...draft, allocations });
                  }}
                />
              </Field>
              <div style={{ paddingBottom: 2 }}>
                <button
                  onClick={() =>
                    setDraft({
                      ...draft,
                      allocations: draft.allocations.filter((_, i) => i !== index),
                    })
                  }
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
          <div style={{ display: "flex", gap: 8 }}>
            <button className="primary" onClick={applyCredit} disabled={busy || !draft?.allocations.length}>
              {busy ? "Applying…" : "Apply"}
            </button>
            <button
              onClick={() => {
                const chosen = new Set(
                  draft?.allocations.map(
                    (row) => row.sale_order_id ?? row.purchase_order_id,
                  ),
                );
                const next = invoicesFor(invoices, applying).find(
                  (row) => !chosen.has(row.invoice_id),
                );
                if (!next || !draft) return;
                setDraft({ ...draft, allocations: [...draft.allocations, allocFor(next)] });
              }}
            >
              Add invoice
            </button>
          </div>
        </Card>
      )}

      <Card
        title="Outstanding invoices"
        subtitle="What customers owe you, and what you owe suppliers"
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            {canWrite && (
              <>
                <button onClick={() => start("Receipt")}>Receive money</button>
                <button className="primary" onClick={() => start("Payment")}>
                  Pay supplier
                </button>
              </>
            )}
            <ExportButton
              filename={csvFilename("outstanding-invoices")}
              rows={invoices}
              columns={[
                { header: "Type", value: (row) => row.kind },
                { header: "Date", value: (row) => row.invoice_date },
                { header: "Invoice", value: (row) => row.invoice_no },
                { header: "Customer or supplier", value: (row) => row.party_name },
                { header: "Account code", value: (row) => row.party_code },
                { header: "Total", value: (row) => row.total },
                { header: "Settled", value: (row) => row.paid },
                { header: "Outstanding", value: (row) => row.outstanding },
                { header: "Reversed", value: (row) => (row.is_reversed ? "yes" : "") },
              ]}
            />
          </div>
        }
      >
        {outstanding.loading && <Spinner />}
        {outstanding.error && <ErrorBox message={outstanding.error} />}
        {outstanding.data && invoices.length === 0 && (
          <Empty message="Every invoice is settled. Nothing is outstanding." />
        )}
        {invoices.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Invoice</th>
                  <th>Customer or supplier</th>
                  <th className="numeric">Total</th>
                  <th className="numeric">Settled</th>
                  <th className="numeric">Outstanding</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {invoices.map((row) => (
                  <tr key={`${row.kind}-${row.invoice_id}`}>
                    <td>{row.invoice_date}</td>
                    <td className="name-cell">
                      {row.invoice_no}{" "}
                      <Pill tone={row.kind === "sale" ? "neutral" : "info"}>
                        {row.kind === "sale" ? "sale" : "purchase"}
                      </Pill>{" "}
                      {row.is_reversed && <Pill tone="warn">reversed</Pill>}
                    </td>
                    <td>{row.party_name}</td>
                    <td className="numeric">{fmt(row.total)}</td>
                    <td className="numeric">{Number(row.paid) ? fmt(row.paid) : "—"}</td>
                    <td className="numeric">{fmt(row.outstanding)}</td>
                    <td>
                      {canWrite &&
                        (row.party_code ? (
                          <button
                            onClick={() =>
                              start(row.kind === "sale" ? "Receipt" : "Payment", row)
                            }
                          >
                            Settle
                          </button>
                        ) : (
                          <span className="small muted">not linked to a record</span>
                        ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card
        title="Receipts & payments"
        subtitle="Money in and out, newest first"
        actions={
          <ExportButton
            filename={csvFilename("receipts-and-payments")}
            rows={payments.data}
            columns={[
              { header: "Date", value: (row) => row.pay_date },
              { header: "Voucher", value: (row) => row.voucher_no },
              { header: "Type", value: (row) => row.direction },
              { header: "Customer or supplier", value: (row) => row.party_name },
              { header: "Amount", value: (row) => row.amount },
              { header: "On account", value: (row) => row.on_account },
              { header: "Reference", value: (row) => row.reference },
              { header: "Note", value: (row) => row.memo },
              { header: "Recorded by", value: (row) => row.posted_by },
              { header: "Reversed", value: (row) => (row.is_reversed ? "yes" : "") },
            ]}
          />
        }
      >
        {payments.loading && <Spinner />}
        {payments.error && <ErrorBox message={payments.error} />}
        {payments.data && payments.data.length === 0 && (
          <Empty message="Nothing recorded yet." />
        )}
        {payments.data && payments.data.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Voucher</th>
                  <th>Type</th>
                  <th>Customer or supplier</th>
                  <th className="numeric">Amount</th>
                  <th className="numeric">On account</th>
                  <th>Settles</th>
                  <th>Recorded by</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {payments.data.map((row) => (
                  <tr key={row.id}>
                    <td>{row.pay_date}</td>
                    <td className="name-cell">{row.voucher_no}</td>
                    <td>
                      <Pill tone={row.direction === "Receipt" ? "positive" : "info"}>
                        {row.direction === "Receipt" ? "in" : "out"}
                      </Pill>
                    </td>
                    <td>{row.party_name}</td>
                    <td className="numeric">{fmt(row.amount)}</td>
                    <td className="numeric">
                      {Number(row.on_account) ? fmt(row.on_account) : "—"}
                    </td>
                    <td className="muted small">
                      {row.allocations.length === 0
                        ? "on account"
                        : row.allocations
                            .map((a) => `${a.invoice_no} ${fmt(a.amount)}`)
                            .join(", ")}
                    </td>
                    <td className="muted small">{row.posted_by}</td>
                    <td>
                      {canWrite && (
                        <div style={{ display: "flex", gap: 6 }}>
                          {Number(row.on_account) > 0 && !row.is_reversed && (
                            <button onClick={() => openApply(row)}>Apply</button>
                          )}
                          {!row.is_reversed && (
                            <button
                              onClick={() => {
                                setError(null);
                                setReversing({ id: row.id, reason: "" });
                              }}
                            >
                              Reverse
                            </button>
                          )}
                        </div>
                      )}
                      {row.is_reversed && <Pill tone="warn">reversed</Pill>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );

  function openApply(payment: Payment) {
    setError(null);
    setMessage(null);
    setPreview(null);
    setApplying(payment);
    setDraft({
      direction: payment.direction,
      party_code: payment.party_code,
      pay_date: payment.pay_date,
      amount: payment.on_account,
      money_account: payment.money_account,
      reference: payment.reference ?? "",
      memo: "",
      allocations: [],
    });
  }
}

/** An allocations-editor row for an invoice, defaulting to its full balance. */
function allocFor(invoice: OutstandingInvoice) {
  return {
    ...(invoice.kind === "sale"
      ? { sale_order_id: invoice.invoice_id }
      : { purchase_order_id: invoice.invoice_id }),
    amount: invoice.outstanding,
  };
}

/** The parties a receipt may come from, or a payment may go to. */
function partiesFor(draft: Draft, parties: { code: string; name: string; kind: string }[]) {
  if (draft.direction === "Receipt") {
    return parties.filter((party) => party.kind !== "Supplier");
  }
  return parties.filter((party) => party.kind !== "Customer");
}

/** The outstanding invoices belonging to this payment's partner and direction. */
function invoicesFor(invoices: OutstandingInvoice[], payment: Payment) {
  const kind = payment.direction === "Receipt" ? "sale" : "purchase";
  return invoices.filter((row) => row.kind === kind && row.party_code === payment.party_code);
}

/** A readable label for a row of the allocations editor. */
function invoiceLabel(
  invoices: OutstandingInvoice[],
  row: { sale_order_id?: number; purchase_order_id?: number },
): string | null {
  const id = row.sale_order_id ?? row.purchase_order_id;
  if (!id) return null;
  const kind = row.sale_order_id ? "sale" : "purchase";
  const found = invoices.find((invoice) => invoice.kind === kind && invoice.invoice_id === id);
  if (!found) return `#${id}`;
  return `${found.invoice_no} — ${fmt(found.outstanding)} outstanding`;
}

/** The API payload for the open form. */
function payload(draft: Draft) {
  return {
    direction: draft.direction,
    party_code: draft.party_code,
    pay_date: draft.pay_date,
    amount: draft.amount || "0",
    money_account: draft.money_account,
    reference: draft.reference || null,
    memo: draft.memo || null,
    allocations: draft.allocations.map((row) => ({
      sale_order_id: row.sale_order_id ?? null,
      purchase_order_id: row.purchase_order_id ?? null,
      amount: row.amount || "0",
    })),
  };
}
