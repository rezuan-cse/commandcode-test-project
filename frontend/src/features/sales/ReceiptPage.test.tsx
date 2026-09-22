// @vitest-environment jsdom
/**
 * The receipt is a document handed to a customer, so what it shows has to match
 * the posted sale exactly. It reads the stored lines and totals rather than
 * recalculating, and these tests check it does not drift.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../shared/api", () => ({
  api: { sale: vi.fn(), settings: vi.fn(), items: vi.fn() },
}));

import { api } from "../../shared/api";
import { DemoProvider } from "../../shared/DemoContext";
import ReceiptPage from "./ReceiptPage";

const mocked = api as unknown as {
  sale: ReturnType<typeof vi.fn>;
  settings: ReturnType<typeof vi.fn>;
  items: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.clearAllMocks();

  mocked.sale.mockResolvedValue({
    id: 1,
    order_no: "SALE-002",
    sale_date: "2026-10-25",
    customer: "Karim Enterprise",
    revenue: "2400.0000",
    cogs: "1347.4419",
    journal_entry_id: 9,
    posted_by: "Sales",
    lines: [
      {
        item_code: "TRD-018",
        qty: "4.0000",
        sale_price: "600.000000",
        line_revenue: "2400.0000",
      },
    ],
  });

  mocked.settings.mockResolvedValue([
    { key: "company.name", value: '"RPCI"' },
    { key: "company.address", value: '""' },
    { key: "company.vat_reg_no", value: '""' },
    { key: "company.phone", value: '""' },
  ]);

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

    expect(
      await screen.findByText(/not a VAT tax invoice/i),
    ).toBeTruthy();
  });

  it("says the address is unconfirmed rather than leaving a blank", async () => {
    renderReceipt();

    expect(await screen.findByText(/address to be confirmed/i)).toBeTruthy();
  });
});
