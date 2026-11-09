// @vitest-environment jsdom
/**
 * A document handed to a customer has to match the posted sale exactly, so the
 * receipt (and, when the client asks for it, the Mushak 6.3 tax invoice) reads
 * the stored lines and totals rather than recalculating. These tests pin that
 * down, and check the tax invoice prints the VAT registration numbers a VAT
 * office would ask for.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../shared/api", () => ({
  api: {
    // The period provider asks this on mount for the dates to open on.
    meta: vi.fn().mockResolvedValue({
      demo_accounts: false,
      data_reset: true,
      api_docs: false,
      needs_setup: false,
      company_name: "Resinova Bangladesh",
      suggested_from: "2026-07-01",
      suggested_as_of: "2026-10-31",
    }),
    sale: vi.fn(),
    settings: vi.fn(),
    items: vi.fn(),
    parties: vi.fn(),
  },
}));

import { api } from "../../shared/api";
import { DemoProvider } from "../../shared/DemoContext";
import ReceiptPage from "./ReceiptPage";

const mocked = api as unknown as {
  sale: ReturnType<typeof vi.fn>;
  settings: ReturnType<typeof vi.fn>;
  items: ReturnType<typeof vi.fn>;
  parties: ReturnType<typeof vi.fn>;
};

const CUSTOMER = {
  code: "CUS-001",
  name: "Karim Enterprise",
  kind: "Customer",
  contact_person: "Md Karim",
  phone: "+880 1711 111111",
  email: null,
  address: "13/2, West Panthapath, Dhaka",
  vat_reg_no: "003142567-0202",
  credit_days: null,
  is_active: true,
};

function settingsWith(receiptStyle: string) {
  return [
    { key: "company.name", value: '"Resinova Bangladesh"' },
    {
      key: "company.address",
      value: '"10, Shanti Niketon, Road-05, Block-D, Dhaka-1212"',
    },
    { key: "company.vat_reg_no", value: '"002016027-0208"' },
    { key: "company.phone", value: '"+880 1735-536678"' },
    { key: "sales.receipt_style", value: JSON.stringify(receiptStyle) },
  ];
}

beforeEach(() => {
  vi.clearAllMocks();

  mocked.sale.mockResolvedValue({
    id: 1,
    order_no: "SALE-002",
    sale_date: "2026-10-25",
    customer: "Karim Enterprise",
    party_code: CUSTOMER.code,
    revenue: "2400.0000",
    vat_total: "360.0000",
    cogs: "1347.4419",
    journal_entry_id: 9,
    posted_by: "Sales",
    is_reversed: false,
    reversed_by: null,
    reversal_reason: null,
    lines: [
      {
        item_code: "TRD-018",
        qty: "4.0000",
        sale_price: "600.000000",
        line_revenue: "2400.0000",
        vat_amount: "360.0000",
        vat_rate_pct: "15.0000",
      },
    ],
  });

  mocked.settings.mockResolvedValue(settingsWith("plain"));

  mocked.items.mockResolvedValue([
    {
      code: "TRD-018",
      name: "NovaCrete PU-MF-C-Filler",
      category: "Finished Good",
      segment: "Trading",
      uom: "Nos.",
      qty_on_hand: "10.0000",
      avg_cost: "336.86047000",
      value_on_hand: "3368.6047",
    },
  ]);

  mocked.parties.mockResolvedValue([CUSTOMER]);
});

afterEach(cleanup);

function renderReceipt() {
  return render(
    <MemoryRouter initialEntries={["/sales/1/receipt"]}>
      {/* useAsync reads the demo revision, so the provider is required. */}
      <DemoProvider>
        <Routes>
          <Route path="/sales/:id/receipt" element={<ReceiptPage />} />
        </Routes>
      </DemoProvider>
    </MemoryRouter>,
  );
}

describe("Sales receipt", () => {
  it("shows the sale it is for", async () => {
    renderReceipt();

    expect(await screen.findByText("SALE-002")).toBeTruthy();
    expect(screen.getByText("Karim Enterprise")).toBeTruthy();
    expect(screen.getByText("2026-10-25")).toBeTruthy();
  });

  it("itemises the posted lines rather than just the total", async () => {
    renderReceipt();

    expect(await screen.findByText("NovaCrete PU-MF-C-Filler")).toBeTruthy();
    expect(screen.getByText("TRD-018")).toBeTruthy();
    // Quantity, rate and amount, straight from the stored line.
    expect(screen.getByText("4")).toBeTruthy();
    expect(screen.getByText("600.00")).toBeTruthy();
    expect(screen.getAllByText("2,400.00").length).toBeGreaterThan(0);
  });

  it("does not claim to be a VAT invoice", async () => {
    renderReceipt();

    expect(await screen.findByText(/not a VAT tax invoice/i)).toBeTruthy();
  });

  it("says the address is unconfirmed rather than leaving a blank", async () => {
    mocked.settings.mockResolvedValue([
      { key: "company.name", value: '"RPCI"' },
      { key: "company.address", value: '""' },
      { key: "company.vat_reg_no", value: '""' },
      { key: "company.phone", value: '""' },
    ]);
    renderReceipt();

    expect(await screen.findByText(/address to be confirmed/i)).toBeTruthy();
  });
});

describe("Mushak 6.3 tax invoice", () => {
  beforeEach(() => {
    mocked.settings.mockResolvedValue(settingsWith("tax_invoice"));
  });

  it("is headed as a Mushak 6.3 and names the seller's BIN", async () => {
    renderReceipt();

    expect(await screen.findByText("Mushak - 6.3")).toBeTruthy();
    expect(screen.getByText("TAX INVOICE")).toBeTruthy();
    expect(screen.getByText("002016027-0208")).toBeTruthy();
  });

  it("prints the buyer's address and BIN from their record", async () => {
    renderReceipt();

    expect(await screen.findByText("Billed To")).toBeTruthy();
    expect(screen.getByText("13/2, West Panthapath, Dhaka")).toBeTruthy();
    expect(screen.getByText("003142567-0202")).toBeTruthy();
    expect(screen.getByText("Md Karim")).toBeTruthy();
  });

  it("shows the rate each line was taxed at, and the amount in words", async () => {
    renderReceipt();

    expect(await screen.findByText("Amount Payable")).toBeTruthy();
    expect(screen.getAllByText("15%").length).toBeGreaterThan(0);
    expect(screen.getByText(/In words:/)).toBeTruthy();
    expect(screen.getByText(/does not require any signature/i)).toBeTruthy();
  });

  it("says the buyer's details are unconfirmed when there is no record", async () => {
    mocked.parties.mockResolvedValue([]);
    renderReceipt();

    expect(await screen.findByText("Billed To")).toBeTruthy();
    expect(screen.getAllByText(/BIN Number:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/to be confirmed/).length).toBeGreaterThan(0);
  });
});
