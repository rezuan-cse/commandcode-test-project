// @vitest-environment jsdom
/**
 * Sales Entry interaction tests.
 *
 * These guard a bug reported from the deployed demo: the price box kept the
 * value of the previously selected item, so switching from a 5-taka item to one
 * costing 336.86 left the price at 5 and produced a 6,637% negative margin.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../shared/api", () => ({
  api: {
    items: vi.fn(),
    sales: vi.fn(),
    previewSale: vi.fn(),
    postSale: vi.fn(),
  },
  setActingRole: vi.fn(),
  getActingRole: () => "Admin",
}));

import { api } from "../../shared/api";
import { DemoProvider } from "../../shared/DemoContext";
import SalesPage from "./SalesPage";

const BAG = {
  code: "PKC-026",
  name: "Filler Bag C Printed",
  category: "Packaging",
  segment: "Packaging",
  uom: "Pcs.",
  qty_on_hand: "90.0000",
  avg_cost: "5.00000000",
  value_on_hand: "450.0000",
};

const FILLER = {
  code: "TRD-018",
  name: "NovaCrete PU-MF-C-Filler",
  category: "Finished Good",
  segment: "Trading",
  uom: "Nos.",
  qty_on_hand: "10.0000",
  avg_cost: "336.86047000",
  value_on_hand: "3368.6047",
};

const mocked = api as unknown as {
  items: ReturnType<typeof vi.fn>;
  sales: ReturnType<typeof vi.fn>;
  previewSale: ReturnType<typeof vi.fn>;
};

function renderPage() {
  return render(
    <DemoProvider>
      <SalesPage />
    </DemoProvider>,
  );
}

// Vitest globals are off, so testing-library cannot register its own cleanup.
afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  mocked.items.mockResolvedValue([BAG, FILLER]);
  mocked.sales.mockResolvedValue([]);
  mocked.previewSale.mockResolvedValue({
    customer: "Local Customer",
    lines: [],
    revenue: "0",
    cogs: "0",
    gross_profit: "0",
    gross_margin_pct: "0",
    journal_lines: [],
    balanced: true,
    can_post: true,
    warnings: [],
  });
});

describe("Sales Entry — the price follows the item", () => {
  it("starts on the first item in stock, priced at its cost", async () => {
    renderPage();
    const item = (await screen.findByLabelText("Item line 1")) as HTMLSelectElement;
    await waitFor(() => expect(item.value).toBe("PKC-026"));

    const price = screen.getByLabelText("Sale price line 1") as HTMLInputElement;
    expect(price.value).toBe("5.00000000");
  });

  it("re-prices the line when a different item is chosen", async () => {
    renderPage();
    const item = (await screen.findByLabelText("Item line 1")) as HTMLSelectElement;
    await waitFor(() => expect(item.value).toBe("PKC-026"));

    fireEvent.change(item, { target: { value: "TRD-018" } });

    const price = screen.getByLabelText("Sale price line 1") as HTMLInputElement;
    // The regression: this used to stay at "5", the previous item's cost.
    await waitFor(() => expect(price.value).toBe("336.86047000"));
    expect(price.value).not.toBe("5.00000000");
  });

  it("keeps the price consistent when switching back and forth", async () => {
    renderPage();
    const item = (await screen.findByLabelText("Item line 1")) as HTMLSelectElement;
    await waitFor(() => expect(item.value).toBe("PKC-026"));
    const price = screen.getByLabelText("Sale price line 1") as HTMLInputElement;

    fireEvent.change(item, { target: { value: "TRD-018" } });
    await waitFor(() => expect(price.value).toBe("336.86047000"));

    fireEvent.change(item, { target: { value: "PKC-026" } });
    await waitFor(() => expect(price.value).toBe("5.00000000"));
  });

  it("does not overwrite a price the user has typed while the item stays put", async () => {
    renderPage();
    const price = (await screen.findByLabelText("Sale price line 1")) as HTMLInputElement;
    await waitFor(() => expect(price.value).toBe("5.00000000"));

    fireEvent.change(price, { target: { value: "12.50" } });
    await waitFor(() => expect(price.value).toBe("12.50"));
  });

  it("sends the entered price to the preview", async () => {
    renderPage();
    const item = (await screen.findByLabelText("Item line 1")) as HTMLSelectElement;
    await waitFor(() => expect(item.value).toBe("PKC-026"));

    fireEvent.change(item, { target: { value: "TRD-018" } });
    const price = screen.getByLabelText("Sale price line 1") as HTMLInputElement;
    fireEvent.change(price, { target: { value: "600" } });

    await waitFor(() => {
      const lastCall = mocked.previewSale.mock.calls.at(-1)?.[0] as {
        lines: { item_code: string; sale_price: string }[];
      };
      expect(lastCall.lines[0]).toEqual(
        expect.objectContaining({ item_code: "TRD-018", sale_price: "600" }),
      );
    });
  });
});
