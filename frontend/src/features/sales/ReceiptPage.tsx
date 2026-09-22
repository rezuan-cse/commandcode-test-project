import { Link, useParams } from "react-router-dom";
import { api } from "../../shared/api";
import { fmt, fmtQty } from "../../shared/format";
import { ErrorBox, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { Item } from "../../shared/types";

/**
 * A printable receipt for a posted sale.
 *
 * Deliberately a plain document rather than a VAT tax invoice: the client asked
 * for a simple sales receipt and confirmed no tax breakdown is needed. It reads
 * from the posted sale and never recalculates anything, so what the customer is
 * handed matches what the ledger holds.
 *
 * Printing is the browser's own — no PDF service to run, nothing to store.
 */
export default function ReceiptPage() {
  const { id } = useParams<{ id: string }>();
  const sale = useAsync(() => api.sale(id ?? ""), [id]);
  const settings = useAsync(() => api.settings(), []);
  const items = useAsync(() => api.items(), []);

  if (sale.loading || settings.loading) return <Spinner label="Preparing the receipt…" />;
  if (sale.error) return <ErrorBox message={sale.error} />;
  if (!sale.data) return null;

  const order = sale.data;
  const company = readCompany(settings.data ?? []);
  const nameOf = (code: string) =>
    (items.data ?? []).find((item: Item) => item.code === code)?.name ?? code;

  return (
    <div className="receipt-page">
      <div className="receipt-toolbar">
        <Link to="/sales">
          <button>← Back to Sales</button>
        </Link>
        <button className="primary" onClick={() => window.print()}>
          Print
        </button>
      </div>

      <article className="receipt">
        <header className="receipt-head">
          <div>
            <h1>{company.name || "RPCI"}</h1>
            {company.address ? (
              <p>{company.address}</p>
            ) : (
              <p className="receipt-pending">Address to be confirmed</p>
            )}
            {company.phone && <p>{company.phone}</p>}
          </div>
          <div className="receipt-meta">
            <h2>Sales Receipt</h2>
            <dl>
              <dt>Receipt no.</dt>
              <dd>{order.order_no}</dd>
              <dt>Date</dt>
              <dd>{order.sale_date}</dd>
              {company.vatRegNo && (
                <>
                  <dt>VAT reg.</dt>
                  <dd>{company.vatRegNo}</dd>
                </>
              )}
            </dl>
          </div>
        </header>

        <section className="receipt-party">
          <span className="receipt-label">Received from</span>
          <strong>{order.customer}</strong>
        </section>

        <table className="receipt-lines">
          <thead>
            <tr>
              <th>Item</th>
              <th className="numeric">Qty</th>
              <th className="numeric">Rate</th>
              <th className="numeric">Amount</th>
            </tr>
          </thead>
          <tbody>
            {order.lines.map((line) => (
              <tr key={line.item_code}>
                <td>
                  <div>{nameOf(line.item_code)}</div>
                  <div className="receipt-code">{line.item_code}</div>
                </td>
                <td className="numeric">{fmtQty(line.qty)}</td>
                <td className="numeric">{fmt(line.sale_price)}</td>
                <td className="numeric">{fmt(line.line_revenue)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} className="receipt-total-label">
                Total
              </td>
              <td className="numeric receipt-total">{fmt(order.revenue)}</td>
            </tr>
          </tfoot>
        </table>

        <footer className="receipt-foot">
          <p>
            Recorded by {order.posted_by}. This is a sales receipt, not a VAT tax
            invoice.
          </p>
          <p className="receipt-thanks">Thank you.</p>
        </footer>
      </article>
    </div>
  );
}

interface CompanyDetails {
  name: string;
  address: string;
  phone: string;
  vatRegNo: string;
}

/** Pull the company's document details out of the settings list. */
function readCompany(settings: { key: string; value: string }[]): CompanyDetails {
  const value = (key: string) => {
    const found = settings.find((setting) => setting.key === key);
    return (found?.value ?? "").replace(/^"|"$/g, "");
  };
  return {
    name: value("company.name"),
    address: value("company.address"),
    phone: value("company.phone"),
    vatRegNo: value("company.vat_reg_no"),
  };
}
