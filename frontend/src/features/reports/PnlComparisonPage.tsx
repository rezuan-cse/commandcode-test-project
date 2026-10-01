import { useState } from "react";
import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt } from "../../shared/format";
import { csvFilename } from "../../shared/csv";
import { Card, ErrorBox, ExportButton, Field, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";
import type { PnlLineComparison, SegmentComparison } from "../../shared/types";

/**
 * The month containing an ISO date, and the month before it.
 *
 * Built from the date the screen is anchored to rather than from the machine's
 * clock, so the report opens on the period the rest of the system is showing. The
 * arithmetic is done in UTC on purpose: a local `Date` would shift the month
 * boundary by a day depending on where the browser is.
 */
function monthsAround(iso: string): [{ start: string; end: string }, { start: string; end: string }] {
  const [year, month] = iso.split("-").map(Number);
  const span = (y: number, m: number) => ({
    start: `${y}-${String(m).padStart(2, "0")}-01`,
    // Day zero of the next month is the last day of this one.
    end: new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10),
  });
  const previousYear = month === 1 ? year - 1 : year;
  const previousMonth = month === 1 ? 12 : month - 1;
  return [span(previousYear, previousMonth), span(year, month)];
}

export default function PnlComparisonPage() {
  const { asOf } = useDemo();
  const [previous, current] = monthsAround(asOf);

  const [period1From, setPeriod1From] = useState(previous.start);
  const [period1To, setPeriod1To] = useState(previous.end);
  const [period2From, setPeriod2From] = useState(current.start);
  const [period2To, setPeriod2To] = useState(current.end);

  const comparison = useAsync(
    () =>
      api.pnlComparison({
        period_1_from: period1From,
        period_1_to: period1To,
        period_2_from: period2From,
        period_2_to: period2To,
      }),
    [period1From, period1To, period2From, period2To],
  );

  const data = comparison.data;
  const label1 = data ? `${data.period_1.date_from} → ${data.period_1.date_to}` : "First period";
  const label2 = data ? `${data.period_2.date_from} → ${data.period_2.date_to}` : "Second period";

  // One flat sheet: segment, then each figure, so it sorts and totals in Excel.
  const exportRows = data
    ? [data.total, ...data.segments].flatMap((group) =>
        group.lines.map((line) => ({ segment: group.segment, line })),
      )
    : [];

  return (
    <>
      <h1>Period Comparison</h1>
      <p className="page-intro">
        Two periods side by side, with the movement between them. Set them to any
        dates — a month against the month before it opens by default. A percentage
        change is left blank when the earlier period had nothing in it, because there
        is no such percentage; the absolute change is always shown.
      </p>

      <Card
        title="Which periods to compare"
        subtitle="Period 1 is the earlier one, and the change is period 2 minus period 1"
        actions={
          <ExportButton
            filename={csvFilename("period-comparison")}
            rows={exportRows}
            columns={[
              { header: "Segment", value: (row) => row.segment },
              { header: "Figure", value: (row) => row.line.metric },
              { header: `Period 1 (${label1})`, value: (row) => row.line.period_1 },
              { header: `Period 2 (${label2})`, value: (row) => row.line.period_2 },
              { header: "Change", value: (row) => row.line.change },
              {
                header: row_header(label1, label2),
                value: (row) => row.line.change_pct,
              },
            ]}
          />
        }
      >
        <div className="form-row">
          <Field label="Period 1 from">
            <input
              type="date"
              value={period1From}
              onChange={(event) => setPeriod1From(event.target.value)}
            />
          </Field>
          <Field label="Period 1 to">
            <input
              type="date"
              value={period1To}
              onChange={(event) => setPeriod1To(event.target.value)}
            />
          </Field>
          <Field label="Period 2 from">
            <input
              type="date"
              value={period2From}
              onChange={(event) => setPeriod2From(event.target.value)}
            />
          </Field>
          <Field label="Period 2 to">
            <input
              type="date"
              value={period2To}
              onChange={(event) => setPeriod2To(event.target.value)}
            />
          </Field>
        </div>
      </Card>

      {comparison.loading && <Spinner />}
      {comparison.error && <ErrorBox message={comparison.error} />}

      {data && (
        <>
          <Card title="Headline" subtitle={`${label1} against ${label2}`}>
            <ComparisonTable
              groups={[data.total]}
              label1={label1}
              label2={label2}
              showSegment={false}
            />
          </Card>

          <Card title="By segment" subtitle="The same figures, split by part of the business">
            <ComparisonTable
              groups={data.segments}
              label1={label1}
              label2={label2}
              showSegment
            />
          </Card>
        </>
      )}
    </>
  );
}

/** The comparison table, used for the headline and for the per-segment breakdown. */
function ComparisonTable({
  groups,
  label1,
  label2,
  showSegment,
}: {
  groups: SegmentComparison[];
  label1: string;
  label2: string;
  showSegment: boolean;
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {showSegment && <th>Segment</th>}
            <th>Figure</th>
            <th className="numeric">{label1}</th>
            <th className="numeric">{label2}</th>
            <th className="numeric">Change</th>
            <th className="numeric">Change %</th>
          </tr>
        </thead>
        <tbody>
          {groups.map((group) =>
            group.lines.map((line) => (
              <tr key={`${group.segment}-${line.metric}`}>
                {showSegment && <td className="name-cell">{group.segment}</td>}
                <td>{line.metric}</td>
                <td className="numeric">{amount(line, line.period_1)}</td>
                <td className="numeric">{amount(line, line.period_2)}</td>
                <td className="numeric">{amount(line, line.change)}</td>
                <td className="numeric">
                  <ChangePill line={line} />
                </td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </div>
  );
}

/** A figure, formatted as a percentage when the figure is one. */
function amount(line: PnlLineComparison, value: string): string {
  return line.is_percentage ? `${fmt(value, 2)}%` : fmt(value);
}

/**
 * The movement, as a coloured percentage.
 *
 * Blank when the earlier period had nothing in it — the backend sends no
 * percentage in that case rather than inventing one — and blank for a margin,
 * where a percentage change of a percentage would mean nothing.
 */
function ChangePill({ line }: { line: PnlLineComparison }) {
  if (line.change_pct === null) {
    return <span className="muted small">—</span>;
  }
  const value = Number(line.change_pct);
  const points = line.is_percentage ? " pts" : "%";
  return (
    <Pill tone={value > 0 ? "positive" : value < 0 ? "negative" : "neutral"}>
      {value > 0 ? "+" : ""}
      {fmt(line.change_pct, 2)}
      {points}
    </Pill>
  );
}

/** The export's last heading, which has to name what the percentage means. */
function row_header(label1: string, label2: string): string {
  return `Change % (${label2} vs ${label1})`;
}
