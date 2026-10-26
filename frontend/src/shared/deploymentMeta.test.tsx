// @vitest-environment jsdom
/**
 * What the interface offers must match what the deployment actually provides.
 *
 * Two screens used to show controls that could only fail:
 *
 *   * the sign-in screen listed five demo accounts on a deployment that seeds
 *     none, so clicking a row filled the form with credentials the server would
 *     never accept;
 *   * the Data screen offered "Start over" when RPCI_ALLOW_DATA_RESET was off and
 *     the server answered 403.
 *
 * Both now read `GET /api/meta` first. Neither is a cosmetic detail — a login
 * screen advertising accounts that do not exist reads as a broken system, and the
 * person testing it has no way to tell the difference.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

const meta = vi.hoisted(() => ({
  value: { demo_accounts: false, data_reset: false, api_docs: false },
}));

vi.mock("./api", () => ({
  api: new Proxy(
    { meta: () => Promise.resolve(meta.value) },
    { get: (_target, prop) => (prop === "meta" ? () => Promise.resolve(meta.value) : vi.fn().mockResolvedValue([])) },
  ),
  getAccessToken: () => null,
  setAccessToken: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}));

vi.mock("./AuthContext", () => ({
  useAuth: () => ({
    user: { id: 1, full_name: "Administrator", role: "Admin", permissions: {} },
    checking: false,
    signIn: vi.fn(),
    submitCode: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

vi.mock("./DemoContext", () => ({
  useDemo: () => ({ revision: 0, refresh: vi.fn() }),
}));

import LoginPage from "../features/auth/LoginPage";
import DataPage from "../features/data/DataPage";

afterEach(cleanup);

describe("the sign-in screen", () => {
  it("hides the demo accounts when the deployment seeds none", async () => {
    meta.value = { demo_accounts: false, data_reset: false, api_docs: false };

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    // The card is absent, so no email address can be offered that would fail.
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
    expect(screen.queryByText("Demo accounts")).toBeNull();
    expect(screen.queryByText("admin@rpci.demo")).toBeNull();
  });

  it("shows the demo accounts where they really exist", async () => {
    meta.value = { demo_accounts: true, data_reset: false, api_docs: false };

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Demo accounts")).toBeTruthy();
    expect(await screen.findByText("admin@rpci.demo")).toBeTruthy();
  });

  it("does not prefill credentials that may not exist", async () => {
    meta.value = { demo_accounts: false, data_reset: false, api_docs: false };

    const { container } = render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    await screen.findByRole("heading", { name: "Sign in" });
    const email = container.querySelector('input[type="email"]') as HTMLInputElement;
    const password = container.querySelector('input[type="password"]') as HTMLInputElement;

    // An empty form is honest; a prefilled one silently promises an account.
    expect(email.value).toBe("");
    expect(password.value).toBe("");
  });
});

describe("the Data screen", () => {
  it("hides Start over when the server would refuse it", async () => {
    meta.value = { demo_accounts: false, data_reset: false, api_docs: false };

    render(
      <MemoryRouter>
        <DataPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Import an existing workbook")).toBeTruthy();
    expect(screen.queryByText("Start over")).toBeNull();
    expect(screen.queryByText("Restore sample workbook")).toBeNull();
  });

  it("keeps Import available even when reset is switched off", async () => {
    meta.value = { demo_accounts: false, data_reset: false, api_docs: false };

    render(
      <MemoryRouter>
        <DataPage />
      </MemoryRouter>,
    );

    // Import is the supported way to load data, so it must survive the same
    // setting that disables "start over".
    expect(await screen.findByText("Import workbook")).toBeTruthy();
  });

  it("offers Start over where it is permitted", async () => {
    meta.value = { demo_accounts: false, data_reset: true, api_docs: false };

    render(
      <MemoryRouter>
        <DataPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Start over")).toBeTruthy();
    expect(await screen.findByText("Restore sample workbook")).toBeTruthy();
  });
});
