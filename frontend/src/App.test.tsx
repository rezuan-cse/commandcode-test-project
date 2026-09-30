// @vitest-environment jsdom
/**
 * The shell on a narrow screen.
 *
 * Below 900px the menu is a drawer behind a hamburger button, so these check the
 * button opens and closes it and that picking a screen closes it again. The
 * stylesheet does the sliding; this covers the state that drives it.
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

// Any API call resolves to an empty list; these tests are about the shell.
vi.mock("./shared/api", () => ({
  api: new Proxy({}, { get: () => vi.fn().mockResolvedValue([]) }),
  getAccessToken: () => "test-token",
  setAccessToken: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}));

const ACCESS: Record<string, string> = {
  accounts: "none",
  journal_entries: "none",
  items_bom: "full",
  production: "full",
  sales_purchase: "none",
  payroll: "none",
  reports: "none",
};

vi.mock("./shared/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: 3,
      full_name: "Store Person",
      role: "Store/Production Staff",
      permissions: ACCESS,
    },
    checking: false,
    signOut: vi.fn(),
    level: (resource: string) => ACCESS[resource],
    can: (resource: string, write = false) => {
      const level = ACCESS[resource];
      return write ? level === "full" : level === "view" || level === "full";
    },
  }),
}));

import App from "./App";
import { DemoProvider } from "./shared/DemoContext";

function renderShell() {
  return render(
    <MemoryRouter>
      <DemoProvider>
        <App />
      </DemoProvider>
    </MemoryRouter>,
  );
}

afterEach(cleanup);

describe("The menu on a narrow screen", () => {
  it("starts closed, behind a button", () => {
    const { container } = renderShell();
    expect(screen.getByRole("button", { name: /open the menu/i })).toBeTruthy();
    expect(container.querySelector(".sidebar")?.className).not.toContain("open");
  });

  it("opens the drawer when the button is tapped", () => {
    const { container } = renderShell();
    fireEvent.click(screen.getByRole("button", { name: /open the menu/i }));

    expect(container.querySelector(".sidebar")?.className).toContain("open");
    expect(container.querySelector(".nav-backdrop")?.className).toContain("open");
    // The button now offers the opposite action.
    expect(screen.getByRole("button", { name: /close the menu/i })).toBeTruthy();
  });

  it("closes when a menu item is chosen", () => {
    const { container } = renderShell();
    fireEvent.click(screen.getByRole("button", { name: /open the menu/i }));
    fireEvent.click(screen.getByRole("link", { name: "Production Entry" }));

    expect(container.querySelector(".sidebar")?.className).not.toContain("open");
  });

  it("closes when the backdrop is tapped", () => {
    const { container } = renderShell();
    fireEvent.click(screen.getByRole("button", { name: /open the menu/i }));
    fireEvent.click(container.querySelector(".nav-backdrop") as Element);

    expect(container.querySelector(".sidebar")?.className).not.toContain("open");
  });

  it("shows a store user only their own work", () => {
    renderShell();
    const menu = screen.getByRole("navigation");
    expect(menu.textContent).toContain("Inventory & BOM");
    expect(menu.textContent).toContain("Production Entry");
    expect(menu.textContent).not.toContain("Dashboard");
    expect(menu.textContent).not.toContain("Trial Balance");
    expect(menu.textContent).not.toContain("Configuration");
    expect(menu.textContent).toContain("Security");
  });
});
