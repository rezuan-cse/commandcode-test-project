import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./shared/AuthContext";
import { useDemo } from "./shared/DemoContext";
import { Logo, Spinner } from "./shared/ui";
import DashboardPage from "./features/dashboard/DashboardPage";
import AccountsPage from "./features/accounts/AccountsPage";
import JournalPage from "./features/journal/JournalPage";
import InventoryPage from "./features/inventory/InventoryPage";
import PartiesPage from "./features/parties/PartiesPage";
import ProductionPage from "./features/production/ProductionPage";
import SalesPage from "./features/sales/SalesPage";
import ReceiptPage from "./features/sales/ReceiptPage";
import PurchasesPage from "./features/purchases/PurchasesPage";
import EmployeesPage from "./features/payroll/EmployeesPage";
import PayrollPage from "./features/payroll/PayrollPage";
import PayslipPage from "./features/payroll/PayslipPage";
import TrialBalancePage from "./features/reports/TrialBalancePage";
import GeneralLedgerPage from "./features/reports/GeneralLedgerPage";
import BalanceSheetPage from "./features/reports/BalanceSheetPage";
import AccessPage from "./features/access/AccessPage";
import ApprovalsPage from "./features/approvals/ApprovalsPage";
import DataPage from "./features/data/DataPage";
import SettingsPage from "./features/settings/SettingsPage";
import LoginPage from "./features/auth/LoginPage";
import SecurityPage from "./features/auth/SecurityPage";
import { landingRoute, visibleGroups as visibleNavGroups } from "./shared/nav";

export default function App() {
  const { user, checking, signOut, can } = useAuth();
  const { asOf, setAsOf, dateFrom, setDateFrom } = useDemo();

  // On a narrow screen the menu is a drawer behind a hamburger button.
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    if (!navOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen]);

  // A stored token is verified against the server before anything renders, so
  // an expired session shows the sign-in screen rather than a broken dashboard.
  if (checking) {
    return (
      <div className="login-shell">
        <div className="login-panel">
          <Spinner label="Checking your session…" />
        </div>
      </div>
    );
  }

  if (!user) return <LoginPage />;

  // The menu this person is offered, from the access that actually applies to
  // them: their role's defaults plus any grant an administrator has recorded.
  const visibleGroups = visibleNavGroups(can);

  // The Dashboard is not open to every role, so anyone who cannot see it lands on
  // the first screen they can. Every role has "My account", so this always resolves.
  const landing = landingRoute(user.role, can);
  const dashboardVisible = visibleGroups.some((group) =>
    group.items.some((item) => item.to === "/"),
  );

  return (
    <div className="shell">
      <aside className={`sidebar ${navOpen ? "open" : ""}`}>
        <div className="brand">
          <Logo variant="dark" />
          <span className="brand-sub">Accounting &amp; Production ERP</span>
        </div>
        <nav>
          {visibleGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end ?? false}
                  className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
                  onClick={() => setNavOpen(false)}
                >
                  {item.text}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      {/* Tapping outside the drawer closes it. */}
      <div
        className={`nav-backdrop ${navOpen ? "open" : ""}`}
        onClick={() => setNavOpen(false)}
        aria-hidden="true"
      />

      <div className="main">
        <header className="topbar">
          <button
            type="button"
            className="nav-toggle"
            aria-label={navOpen ? "Close the menu" : "Open the menu"}
            aria-expanded={navOpen}
            onClick={() => setNavOpen((open) => !open)}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
              <path
                d="M2 5h16M2 10h16M2 15h16"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
          </button>

          <div className="topbar-dates">
            <label className="inline-field">
              <span>Period from</span>
              <input
                type="date"
                value={dateFrom}
                onChange={(event) => setDateFrom(event.target.value)}
              />
            </label>
            <label className="inline-field">
              <span>As of</span>
              <input
                type="date"
                value={asOf}
                onChange={(event) => setAsOf(event.target.value)}
              />
            </label>
          </div>

          <div className="user-chip">
            <div>
              <span className="user-name">{user.full_name}</span>
              <span className="user-role">
                {user.role}
                {user.is_2fa_enabled ? " · 2FA on" : ""}
              </span>
            </div>
            <button onClick={signOut}>Sign out</button>
          </div>
        </header>

        <main className="content">
          <Routes>
            <Route
              path="/"
              element={dashboardVisible ? <DashboardPage /> : <Navigate to={landing} replace />}
            />
            <Route path="/accounts" element={<AccountsPage />} />
            <Route path="/journal" element={<JournalPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/parties" element={<PartiesPage />} />
            <Route path="/purchases" element={<PurchasesPage />} />
            <Route path="/production" element={<ProductionPage />} />
            <Route path="/sales" element={<SalesPage />} />
            <Route path="/sales/:id/receipt" element={<ReceiptPage />} />
            <Route path="/payroll/employees" element={<EmployeesPage />} />
            <Route path="/payroll" element={<PayrollPage />} />
            <Route path="/payroll/runs/:id" element={<PayslipPage />} />
            <Route path="/reports/trial-balance" element={<TrialBalancePage />} />
            <Route path="/reports/general-ledger" element={<GeneralLedgerPage />} />
            <Route path="/reports/balance-sheet" element={<BalanceSheetPage />} />
            <Route path="/access" element={<AccessPage />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/data" element={<DataPage />} />
            <Route path="/security" element={<SecurityPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to={landing} replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
