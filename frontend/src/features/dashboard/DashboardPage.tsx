import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt, fmtPct } from "../../shared/format";
import { Card, ErrorBox, Pill, Spinner, Stat } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";

const SEGMENT_BLURB: Record<string, string> = {
  Import: "Imported finished and trading goods",
  Manufacturing: "Multi-stage production",
  Packaging: "Packaging materials",
  Trading: "Locally traded goods",
  Application: "Service and application income",
};

export default function DashboardPage() {
  const { asOf, dateFrom, refresh } = useDemo();
  const pnl = useAsync(() => api.pnl(dateFrom, asOf), [dateFrom, asOf]);
  const bs = useAsync(() => api.balanceSheet(asOf), [asOf]);
  const integrity = useAsync(() => api.integrity(asOf), [asOf]);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);

  async function resetDemo() {
    if (!window.confirm("Restore the demo to the original workbook data? Anything you posted will be removed.")) {
      return;
    }
    setResetting(true);
    setResetMessage(null);
    try {
      const result = await api.resetDemo();
      setResetMessage(result.message);
      refresh();
    } catch (error) {
      setResetMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setResetting(false);
    }
  }

  if (pnl.loading || bs.loading || integrity.loading) return <Spinner />;
  if (pnl.error || bs.error || integrity.error) {
    return <ErrorBox message={pnl.error ?? bs.error ?? integrity.error ?? "Failed to load"} />;
  }

  const profit = pnl.data!;
  const balance = bs.data!;
  const checks = integrity.data!;

  return (
    <>
      <h1>Dashboard</h1>
      <p className="page-intro">
        Live position for {dateFrom} to {asOf}, computed from the chart of accounts, opening
        balances, and posted journal entries. Nothing on this page is stored separately — every
        figure is derived on request.
      </p>

      {resetMessage && <div className="toast">✓ {resetMessage}</div>}

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button onClick={resetDemo} disabled={resetting}>
          {resetting ? "Restoring…" : "Reset demo data"}
        </button>
      </div>

      <div className="grid grid-5" style={{ marginBottom: 20 }}>
        <Stat
          label="Revenue"
          value={fmt(profit.total_revenue)}
          hint={`${dateFrom} → ${asOf}`}
        />
        <Stat label="COGS" value={fmt(profit.total_cogs)} />
        <Stat label="Gross profit" value={fmt(profit.total_gross_profit)} tone="positive" />
        <Stat label="Gross margin" value={fmtPct(profit.gross_margin_pct)} />
        <Stat
          label="Net profit"
          value={fmt(profit.net_profit)}
          tone={Number(profit.net_profit) >= 0 ? "positive" : "negative"}
        />
      </div>

      <Card
        title="Profit & loss by segment"
        subtitle="Each segment's revenue, cost of goods sold, and margin"
        actions={
          <Link to="/reports/trial-balance">
            <button>Open reports</button>
          </Link>
        }
      >
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Segment</th>
                <th>Description</th>
                <th className="numeric">Revenue</th>
                <th className="numeric">COGS</th>
                <th className="numeric">Gross profit</th>
                <th className="numeric">Margin</th>
              </tr>
            </thead>
            <tbody>
              {profit.segments.map((row) => (
                <tr key={row.segment}>
                  <td className="name-cell">
                    <strong>{row.segment}</strong>
                  </td>
                  <td className="muted">{SEGMENT_BLURB[row.segment] ?? "—"}</td>
                  <td className="numeric">{fmt(row.revenue)}</td>
                  <td className="numeric">{fmt(row.cogs)}</td>
                  <td className="numeric">{fmt(row.gross_profit)}</td>
                  <td className="numeric">{fmtPct(row.gross_margin_pct)}</td>
                </tr>
              ))}
              <tr className="total-row">
                <td colSpan={2}>Total</td>
                <td className="numeric">{fmt(profit.total_revenue)}</td>
                <td className="numeric">{fmt(profit.total_cogs)}</td>
                <td className="numeric">{fmt(profit.total_gross_profit)}</td>
                <td className="numeric">{fmtPct(profit.gross_margin_pct)}</td>
              </tr>
              <tr className="subtotal-row">
                <td colSpan={5}>Less: shared operating expenses</td>
                <td className="numeric">{fmt(profit.operating_expenses)}</td>
              </tr>
              <tr className="subtotal-row">
                <td colSpan={5}>Add: other income</td>
                <td className="numeric">{fmt(profit.other_income)}</td>
              </tr>
              <tr className="total-row">
                <td colSpan={5}>Net profit</td>
                <td className="numeric">{fmt(profit.net_profit)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-2">
        <Card title="Position at a glance" subtitle={`As of ${asOf}`}>
          <div className="grid grid-2">
            <Stat label="Total assets" value={fmt(balance.total_assets)} />
            <Stat label="Total liabilities" value={fmt(balance.total_liabilities)} />
            <Stat label="Owner's equity" value={fmt(balance.equity_per_gl)} />
            <Stat
              label="Current period profit"
              value={fmt(balance.current_period_profit)}
              tone="positive"
            />
          </div>
          <p className="small muted" style={{ marginTop: 14, marginBottom: 0 }}>
            Assets {fmt(balance.total_assets)} = Liabilities + Equity{" "}
            {fmt(balance.total_liabilities_and_equity)} —{" "}
            <Pill tone={balance.is_balanced ? "positive" : "negative"}>
              {balance.is_balanced ? "balanced" : "out of balance"}
            </Pill>
          </p>
        </Card>

        <Card
          title="Data integrity"
          subtitle="Checked live against the ledger, not asserted by the UI"
        >
          <div className="check-list">
            {checks.checks.map((check) => (
              <div className={`check-item ${check.passed ? "pass" : "fail"}`} key={check.name}>
                <span className="check-icon">{check.passed ? "✓" : "!"}</span>
                <div>
                  <div className="check-name">{check.name}</div>
                  <div className="check-detail">{check.detail}</div>
                </div>
              </div>
            ))}
          </div>
          {!checks.all_passed && (
            <p className="small muted" style={{ marginTop: 12, marginBottom: 0 }}>
              The last check compares the general ledger's inventory accounts against the stock
              ledger. They disagree because the original workbook's stock sheet was a memo record
              that never posted journals — see the Inventory screen for the detail.
            </p>
          )}
        </Card>
      </div>
    </>
  );
}
