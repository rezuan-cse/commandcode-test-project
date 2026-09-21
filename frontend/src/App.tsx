import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useDemo } from "./shared/DemoContext";
import DashboardPage from "./features/dashboard/DashboardPage";
import AccountsPage from "./features/accounts/AccountsPage";
import JournalPage from "./features/journal/JournalPage";
import InventoryPage from "./features/inventory/InventoryPage";
import ProductionPage from "./features/production/ProductionPage";
import SalesPage from "./features/sales/SalesPage";
import PurchasesPage from "./features/purchases/PurchasesPage";
import TrialBalancePage from "./features/reports/TrialBalancePage";
import GeneralLedgerPage from "./features/reports/GeneralLedgerPage";
import BalanceSheetPage from "./features/reports/BalanceSheetPage";
import AccessPage from "./features/access/AccessPage";
import SettingsPage from "./features/settings/SettingsPage";

const NAV_GROUPS = [
  {
    label: "Overview",
    items: [{ to: "/", text: "Dashboard", end: true }],
  },
  {
    label: "Ledger",
    items: [
      { to: "/accounts", text: "Chart of Accounts" },
      { to: "/journal", text: "Journal Entries" },
    ],
  },
  {
    label: "Operations",
    items: [
      { to: "/inventory", text: "Inventory & BOM" },
      { to: "/purchases", text: "Purchase Entry" },
      { to: "/production", text: "Production Entry" },
      { to: "/sales", text: "Sales Entry" },
    ],
  },
  {
    label: "Reports",
    items: [
      { to: "/reports/trial-balance", text: "Trial Balance" },
      { to: "/reports/general-ledger", text: "General Ledger" },
      { to: "/reports/balance-sheet", text: "Balance Sheet" },
    ],
  },
  {
    label: "Administration",
    items: [
      { to: "/access", text: "Roles & Access" },
      { to: "/settings", text: "Configuration" },
    ],
  },
];

const ROLES = [
  "Admin",
  "Accountant",
  "Store/Production Staff",
  "Sales Staff",
  "Owner/Viewer",
];

export default function App() {
  const { asOf, setAsOf, dateFrom, setDateFrom, role, setRole } = useDemo();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">RPCI</span>
          <span className="brand-sub">Accounting &amp; Production ERP</span>
        </div>
        <nav>
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={"end" in item ? item.end : false}
                  className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}
                >
                  {item.text}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
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
          <label className="inline-field role-picker">
            <span>Acting role</span>
            <select value={role} onChange={(event) => setRole(event.target.value)}>
              {ROLES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </header>

        <main className="content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/accounts" element={<AccountsPage />} />
            <Route path="/journal" element={<JournalPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/purchases" element={<PurchasesPage />} />
            <Route path="/production" element={<ProductionPage />} />
            <Route path="/sales" element={<SalesPage />} />
            <Route path="/reports/trial-balance" element={<TrialBalancePage />} />
            <Route path="/reports/general-ledger" element={<GeneralLedgerPage />} />
            <Route path="/reports/balance-sheet" element={<BalanceSheetPage />} />
            <Route path="/access" element={<AccessPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
