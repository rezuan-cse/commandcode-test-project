// @vitest-environment jsdom
/**
 * Configuration is where every fact the client has not confirmed is edited, so
 * the screen has to (a) show the company group that used to be missing, and
 * (b) only offer editing to an administrator — the server refuses everyone else.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../shared/api", () => ({
  api: { settings: vi.fn(), updateSetting: vi.fn() },
}));

const session = vi.hoisted(() => ({ role: "Admin" as string }));

vi.mock("../../shared/AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, email: "admin@rpci.demo", role: session.role, permissions: {} },
    checking: false,
    signIn: vi.fn(),
    submitCode: vi.fn(),
    signOut: vi.fn(),
    refreshUser: vi.fn(),
    level: () => undefined,
    can: () => true,
  }),
}));

import { api } from "../../shared/api";
import { DemoProvider } from "../../shared/DemoContext";
import SettingsPage from "./SettingsPage";

const mocked = api as unknown as {
  settings: ReturnType<typeof vi.fn>;
  updateSetting: ReturnType<typeof vi.fn>;
};

const SETTINGS = [
  {
    key: "company.name",
    value: '"Resinova Bangladesh"',
    description: "Registered company name on documents.",
    confirmed_by_client: true,
    group: "company",
    label: "Company name",
    value_type: "string",
    options: null,
    sort_order: 10,
  },
  {
    key: "vat.charge_vat",
    value: "false",
    description: "Whether the system adds VAT.",
    confirmed_by_client: false,
    group: "vat",
    label: "Charge VAT",
    value_type: "bool",
    options: null,
    sort_order: 10,
  },
  {
    key: "vat.return_frequency",
    value: '"monthly"',
    description: "How often a VAT return is filed.",
    confirmed_by_client: false,
    group: "vat",
    label: "Return frequency",
    value_type: "enum",
    options: ["monthly", "quarterly", "yearly"],
    sort_order: 60,
  },
];

function renderPage() {
  return render(
    <DemoProvider>
      <SettingsPage />
    </DemoProvider>,
  );
}

afterEach(cleanup);

beforeEach(() => {
  vi.clearAllMocks();
  session.role = "Admin";
  mocked.settings.mockResolvedValue(SETTINGS);
  mocked.updateSetting.mockImplementation(async (key: string, value: string, confirmed?: boolean) => ({
    ...SETTINGS.find((s) => s.key === key),
    key,
    value,
    confirmed_by_client: confirmed ?? false,
  }));
});

describe("Configuration", () => {
  it("shows the company group that used to be missing", async () => {
    renderPage();
    expect(await screen.findByText("Company details")).toBeTruthy();
    expect(screen.getByDisplayValue("Resinova Bangladesh")).toBeTruthy();
  });

  it("marks an unconfirmed value as pending and a confirmed one as confirmed", async () => {
    renderPage();
    expect(await screen.findByText("pending client")).toBeTruthy();
    expect(screen.getByText("confirmed")).toBeTruthy();
  });

  it("saves an edited value for an administrator", async () => {
    renderPage();
    const input = (await screen.findByDisplayValue("Resinova Bangladesh")) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Resinova Ltd" } });

    const row = input.closest("tr") as HTMLElement;
    fireEvent.click(row.querySelector("button") as HTMLButtonElement);

    await waitFor(() =>
      expect(mocked.updateSetting).toHaveBeenCalledWith("company.name", "Resinova Ltd", true),
    );
  });

  it("renders a checkbox for a boolean and saves it", async () => {
    renderPage();
    const checkbox = (await screen.findByRole("checkbox")) as HTMLInputElement;
    fireEvent.click(checkbox);
    const row = checkbox.closest("tr") as HTMLElement;
    fireEvent.click(row.querySelector("button") as HTMLButtonElement);

    await waitFor(() =>
      expect(mocked.updateSetting).toHaveBeenCalledWith("vat.charge_vat", "true", false),
    );
  });

  it("offers no editing to a non-administrator", async () => {
    session.role = "Accountant";
    renderPage();

    await screen.findByText("Company details");
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.queryByText("Save")).toBeNull();
    expect(screen.getByText(/only an administrator can change/i)).toBeTruthy();
  });
});
