// @vitest-environment jsdom
/**
 * Sales Entry interaction tests.
 *
 * These guard a bug reported from the deployed demo: the price box kept the
 * value of the previously selected item, so switching from a 5-taka item to one
 * costing 336.86 left the price at 5 and produced a 6,637% negative margin.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../shared/api", () => ({
  api: {
    items: vi.fn(),
    sales: vi.fn(),
    previewSale: vi.fn(),
    postSale: vi.fn(),
  },
}));

// The page now renders according to the signed-in role's permissions, so the
// test supplies a session and a mutable permission map it can change per test.
const session = vi.hoisted(() => ({
  permissions: { sales_purchase: "full" } as Record<string, string>,
}));

vi.mock("../../shared/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: 2,
      email: "sales@rpci.demo",
      full_name: "Sales Desk",
      role: "Sales Staff",
      is_active: true,
      is_2fa_enabled: false,
      last_login_at: null,
      permissions: session.permissions,
    },
    checking: false,
    signIn: vi.fn(),
    submitCode: vi.fn(),
    signOut: vi.fn(),
    refreshUser: vi.fn(),
    level: (resource: string) => session.permissions[resource],
    can: (resource: string, write = false) => {
      const level = session.permissions[resource];
      return write ? level === "full" : level === "view" || level === "full";
    },
  }),
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
  // MemoryRouter because the posted-sales table links to each receipt.
  return render(
    <MemoryRouter>
      <DemoProvider>
        <SalesPage />
      </DemoProvider>
    </MemoryRouter>,
  );
}

// Vitest globals are off, so testing-library cannot register its own cleanup.
afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  session.permissions = { sales_purchase: "full", items_bom: "view", reports: "view" };
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

describe("Sales Entry — restricted roles", () => {
  it("hides the form and explains the restriction in plain words", async () => {
    session.permissions = { sales_purchase: "view", items_bom: "view", reports: "view" };
    renderPage();

    // The old behaviour showed a raw "Role 'Sales Staff' does not have write
    // access to 'sales_purchase'" next to a form that could never be submitted.
    expect(
      await screen.findByText(/can view the Purchase and Sales Entry screen but cannot make changes/i),
    ).toBeTruthy();
    expect(screen.queryByLabelText("Item line 1")).toBeNull();
    expect(screen.queryByRole("button", { name: /post sale/i })).toBeNull();
  });

  it("does not ask the server to price a sale the role cannot post", async () => {
    session.permissions = { sales_purchase: "view", items_bom: "view", reports: "view" };
    renderPage();

    await screen.findByText(/cannot make changes/i);
    expect(mocked.previewSale).not.toHaveBeenCalled();
  });

  it("still shows the posted list, so the screen is not empty", async () => {
    session.permissions = { sales_purchase: "view", items_bom: "view", reports: "view" };
    mocked.sales.mockResolvedValue([
      {
        id: 1,
        order_no: "SALE-002",
        sale_date: "2026-10-25",
        customer: "Karim Enterprise",
        revenue: "2400.0000",
        cogs: "1347.4419",
        journal_entry_id: 9,
        posted_by: "Sales",
      },
    ]);
    renderPage();

    // The notice tells the reader the information below is still available, so
    // there had better be some.
    expect(await screen.findByText(/can view the Purchase and Sales Entry screen/i)).toBeTruthy();
    expect(await screen.findByText("SALE-002")).toBeTruthy();
    expect(screen.queryByText(/No sales posted yet/i)).toBeNull();
  });

  it("shows the form for a role that may post", async () => {
    renderPage();

    expect(await screen.findByLabelText("Item line 1")).toBeTruthy();
    expect(screen.queryByText(/cannot make changes/i)).toBeNull();
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
