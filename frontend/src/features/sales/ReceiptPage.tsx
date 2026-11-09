import { Link, useParams } from "react-router-dom";
import { api } from "../../shared/api";
import { fmt, fmtPct, fmtQty } from "../../shared/format";
import { ErrorBox, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { Item, Party, SaleDetail } from "../../shared/types";

/**
 * A printable document for a posted sale.
 *
 * Two layouts, chosen by the Administration → Configuration setting
 * `sales.receipt_style`:
 *
 * - `plain` — a simple sales receipt, for a walk-in customer.
 * - `tax_invoice` — a VAT-compliant Mushak 6.3 tax invoice, modelled on the
 *   sample the client supplied. It prints the seller's BIN and the buyer's
 *   address and BIN, a per-line VAT rate, and the amount in words.
 *
 * Either way it reads the posted sale and never recalculates anything, so what
 * the customer is handed matches what the ledger holds. Discounts, coupons and
 * delivery charges have no place here: RPCI's sales carry none, and a field
 * that is always blank would be read as a promise.
 *
 * Printing is the browser's own — no PDF service to run, nothing to store.
 */
export default function ReceiptPage() {
  const { id } = useParams<{ id: string }>();
  const sale = useAsync(() => api.sale(id ?? ""), [id]);
  const settings = useAsync(() => api.settings(), []);
  const items = useAsync(() => api.items(), []);
  // Only needed for the tax invoice, where the buyer is a record with an
  // address and a BIN — but the fetch is cheap and keeps the page to one flow.
  const parties = useAsync(() => api.parties(), []);

  if (sale.loading || settings.loading) return <Spinner label="Preparing the document…" />;
  if (sale.error) return <ErrorBox message={sale.error} />;
  if (!sale.data) return null;

  const order = sale.data;
  const company = readCompany(settings.data ?? []);
  const receiptStyle = readSetting(settings.data ?? [], "sales.receipt_style");
  const showVat = Number(order.vat_total) > 0;
  const isTaxInvoice = showVat && receiptStyle === "tax_invoice";
  const nameOf = (code: string) =>
    (items.data ?? []).find((item: Item) => item.code === code)?.name ?? code;
  const buyer =
    (parties.data ?? []).find((party: Party) => party.code === order.party_code) ?? null;

  return (
    <div className="receipt-page">
      {order.is_reversed && (
        <div className="receipt-reversed-banner">
          Reversed — this sale has been undone
          {order.reversal_reason ? `: ${order.reversal_reason}` : ""}
        </div>
      )}
      <div className="receipt-toolbar">
        <Link to="/sales">
          <button>← Back to Sales</button>
        </Link>
        <button className="primary" onClick={() => window.print()}>
          Print
        </button>
      </div>

      {isTaxInvoice ? (
        <TaxInvoice order={order} company={company} buyer={buyer} nameOf={nameOf} />
      ) : (
        <PlainReceipt order={order} company={company} nameOf={nameOf} />
      )}
    </div>
  );
}

// ------------------------------------------------------------------ plain ---

function PlainReceipt({
  order,
  company,
  nameOf,
}: {
  order: SaleDetail;
  company: CompanyDetails;
  nameOf: (code: string) => string;
}) {
  const showVat = Number(order.vat_total) > 0;
  const grandTotal = (Number(order.revenue) + Number(order.vat_total)).toFixed(4);

  return (
    <article className={`receipt ${order.is_reversed ? "receipt-reversed" : ""}`}>
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
          {showVat && (
            <>
              <tr>
                <td colSpan={3} className="receipt-total-label">
                  Subtotal
                </td>
                <td className="numeric">{fmt(order.revenue)}</td>
              </tr>
              <tr>
                <td colSpan={3} className="receipt-total-label">
                  VAT
                </td>
                <td className="numeric">{fmt(order.vat_total)}</td>
              </tr>
            </>
          )}
          <tr>
            <td colSpan={3} className="receipt-total-label">
              Total
            </td>
            <td className="numeric receipt-total">
              {fmt(showVat ? grandTotal : order.revenue)}
            </td>
          </tr>
        </tfoot>
      </table>

      <footer className="receipt-foot">
        <p>
          Recorded by {order.posted_by}. This is a sales receipt, not a VAT tax invoice.
        </p>
        <p className="receipt-thanks">Thank you.</p>
      </footer>
    </article>
  );
}

// ----------------------------------------------------------------- mushak ---

function TaxInvoice({
  order,
  company,
  buyer,
  nameOf,
}: {
  order: SaleDetail;
  company: CompanyDetails;
  buyer: Party | null;
  nameOf: (code: string) => string;
}) {
  const payable = (Number(order.revenue) + Number(order.vat_total)).toFixed(4);
  const rates = new Set(
    order.lines
      .map((line) => line.vat_rate_pct)
      .filter((rate): rate is string => rate !== null && Number(rate) > 0),
  );

  return (
    <article className={`receipt mushak ${order.is_reversed ? "receipt-reversed" : ""}`}>
      <header className="mushak-title">
        <h1>TAX INVOICE</h1>
        <p>Mushak - 6.3</p>
      </header>

      <dl className="mushak-ids">
        <div>
          <dt>Invoice No.</dt>
          <dd>{order.order_no}</dd>
        </div>
        <div>
          <dt>Invoice Date</dt>
          <dd>{order.sale_date}</dd>
        </div>
      </dl>

      <section className="mushak-parties">
        <div>
          <h3>Bill From</h3>
          <p className="mushak-name">{company.name || "RPCI"}</p>
          {company.address ? (
            <p>{company.address}</p>
          ) : (
            <p className="receipt-pending">Address to be confirmed</p>
          )}
          {company.phone && <p>{company.phone}</p>}
          <p>
            BIN Number:{" "}
            {company.vatRegNo ? (
              <span className="mushak-bin">{company.vatRegNo}</span>
            ) : (
              <span className="receipt-pending">to be confirmed</span>
            )}
          </p>
        </div>
        <div>
          <h3>Billed To</h3>
          <p className="mushak-name">{order.customer}</p>
          {buyer?.contact_person && <p>{buyer.contact_person}</p>}
          {buyer?.phone && <p>{buyer.phone}</p>}
          {buyer?.address ? (
            <p>{buyer.address}</p>
          ) : (
            <p className="receipt-pending">Address to be confirmed</p>
          )}
          <p>
            BIN Number:{" "}
            {buyer?.vat_reg_no ? (
              <span className="mushak-bin">{buyer.vat_reg_no}</span>
            ) : (
              <span className="receipt-pending">to be confirmed</span>
            )}
          </p>
        </div>
      </section>

      <table className="mushak-lines">
        <thead>
          <tr>
            <th>SL No.</th>
            <th>Description</th>
            <th className="numeric">Quantity</th>
            <th className="numeric">MRP</th>
            <th className="numeric">VAT Rate (%)</th>
            <th className="numeric">Amount</th>
          </tr>
        </thead>
        <tbody>
          {order.lines.map((line, index) => (
            <tr key={`${line.item_code}-${index}`}>
              <td>{index + 1}</td>
              <td>
                <div>{nameOf(line.item_code)}</div>
                <div className="receipt-code">{line.item_code}</div>
              </td>
              <td className="numeric">{fmtQty(line.qty)}</td>
              <td className="numeric">{fmt(line.sale_price)}</td>
              <td className="numeric">
                {line.vat_rate_pct !== null && Number(line.vat_rate_pct) > 0
                  ? fmtPct(line.vat_rate_pct)
                  : "—"}
              </td>
              <td className="numeric">{fmt(line.line_revenue)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <section className="mushak-totals">
        <dl>
          <div>
            <dt>Subtotal</dt>
            <dd>{fmt(order.revenue)}</dd>
          </div>
          <div>
            <dt>VAT{rates.size === 1 ? ` (${[...rates].map(fmtPct).join(", ")})` : ""}</dt>
            <dd>{fmt(order.vat_total)}</dd>
          </div>
          <div className="mushak-payable">
            <dt>Amount Payable</dt>
            <dd>{fmt(payable)}</dd>
          </div>
        </dl>
        <p className="mushak-words">In words: {amountInWords(payable)}</p>
      </section>

      <footer className="receipt-foot">
        <p>
          Recorded by {order.posted_by}. This is a computer generated invoice, does
          not require any signature.
        </p>
        <p className="receipt-thanks">Thank you.</p>
      </footer>
    </article>
  );
}

// ----------------------------------------------------------- amount words ---

const UNITS = [
  "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
  "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
  "Seventeen", "Eighteen", "Nineteen",
];
const TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

/** Words for a number below a thousand, e.g. 705 -> "Seven Hundred Five". */
function belowThousand(n: number): string {
  const hundreds = Math.floor(n / 100);
  const rest = n % 100;
  const parts: string[] = [];
  if (hundreds > 0) parts.push(`${UNITS[hundreds]} Hundred`);
  if (rest >= 20) {
    const tens = Math.floor(rest / 10);
    const ones = rest % 10;
    parts.push(ones > 0 ? `${TENS[tens]} ${UNITS[ones]}` : TENS[tens]);
  } else if (rest > 0) {
    parts.push(UNITS[rest]);
  }
  return parts.join(" ");
}

/**
 * An invoice amount in words, on the South Asian count (crore/lakh), because a
 * ledger written for Bangladesh that read out an Indian-style grouping would be
 * read back as wrong. Figures are taken from the stored decimal string and cut
 * into digit groups by hand — no float ever sees them.
 */
export function amountInWords(value: string): string {
  const [whole = "0", fraction = ""] = value.replace(/,/g, "").split(".");
  const digits = whole.replace(/^0+(?=\d)/, "") || "0";
  const paisa = (fraction + "00").slice(0, 2);

  let taka: string;
  if (digits === "0") {
    taka = "Zero";
  } else {
    const crores = Number(digits.slice(0, -7) || "0");
    const lakhs = Number(digits.slice(-7, -5) || "0");
    const thousands = Number(digits.slice(-5, -3) || "0");
    const hundreds = Number(digits.slice(-3) || "0");
    const parts: string[] = [];
    if (crores > 0) parts.push(`${crores >= 100 ? amountInWords(String(crores)) : belowThousand(crores)} Crore`);
    if (lakhs > 0) parts.push(`${belowThousand(lakhs)} Lakh`);
    if (thousands > 0) parts.push(`${thousands} Thousand`);
    if (hundreds > 0) parts.push(belowThousand(hundreds));
    taka = parts.join(" ");
  }

  return paisa !== "00"
    ? `Taka ${taka} and ${Number(paisa)} Paisa Only`
    : `Taka ${taka} Only`;
}

// -------------------------------------------------------------- settings ---

interface CompanyDetails {
  name: string;
  address: string;
  phone: string;
  vatRegNo: string;
}

/** Pull the company's document details out of the settings list. */
function readCompany(settings: { key: string; value: string }[]): CompanyDetails {
  const value = (key: string) => readSetting(settings, key);
  return {
    name: value("company.name"),
    address: value("company.address"),
    phone: value("company.phone"),
    vatRegNo: value("company.vat_reg_no"),
  };
}

/** Read one setting's plain-string value, stripping the JSON quotes. */
function readSetting(settings: { key: string; value: string }[], key: string): string {
  const found = settings.find((setting) => setting.key === key);
  return (found?.value ?? "").replace(/^"|"$/g, "");
}
