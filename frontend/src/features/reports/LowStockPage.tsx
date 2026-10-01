import { api } from "../../shared/api";
import { useDemo } from "../../shared/DemoContext";
import { fmt, fmtQty } from "../../shared/format";
import { csvFilename } from "../../shared/csv";
import { Card, Empty, ErrorBox, ExportButton, Pill, Spinner } from "../../shared/ui";
import { useAsync } from "../../shared/useAsync";

export default function LowStockPage() {
  const { asOf } = useDemo();
  const data = useAsync(() => api.lowStock(asOf), [asOf]);

  const report = data.data;
  const rows = report?.rows ?? [];
  const out = rows.filter((row) => Number(row.qty_on_hand) <= 0).length;

  return (
    <>
      <h1>Low Stock</h1>
      <p className="page-intro">
        The items at or below the level they want reordering at, biggest gap first,
        with what it would cost to top each one back up. Set the level on an item
        under <strong>Inventory &amp; BOM → Edit</strong>.
      </p>

      <Card
        title="To reorder"
        subtitle={
          report
            ? `${rows.length} item(s)${out > 0 ? ` · ${out} with none left` : ""} · ` +
              `about ${fmt(report.total_reorder_value)} to restock`
            : undefined
        }
        actions={
          <ExportButton
            filename={csvFilename("low-stock", asOf)}
            rows={rows}
            columns={[
              { header: "Code", value: (row) => row.code },
              { header: "Item", value: (row) => row.name },
              { header: "Category", value: (row) => row.category },
              { header: "Segment", value: (row) => row.segment },
              { header: "Unit", value: (row) => row.uom },
              { header: "Quantity on hand", value: (row) => row.qty_on_hand },
              { header: "Reorder level", value: (row) => row.reorder_level },
              { header: "Shortfall", value: (row) => row.shortfall },
              { header: "Average cost", value: (row) => row.avg_cost },
              { header: "Value on hand", value: (row) => row.value_on_hand },
              { header: "Cost to restock", value: (row) => row.reorder_value },
            ]}
          />
        }
      >
        {data.loading && <Spinner />}
        {data.error && <ErrorBox message={data.error} />}

        {report && rows.length === 0 && (
          <Empty
            message={
              "Nothing is at its reorder level. Items only appear here once they carry " +
              "a reorder level — a blank level means the item is not being watched, " +
              "which is not the same as a level of zero."
            }
          />
        )}

        {rows.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Item</th>
                  <th>Unit</th>
                  <th className="numeric">On hand</th>
                  <th className="numeric">Reorder at</th>
                  <th className="numeric">Shortfall</th>
                  <th className="numeric">Avg cost</th>
                  <th className="numeric">Cost to restock</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.code}>
                    <td className="name-cell">{row.code}</td>
                    <td>{row.name}</td>
                    <td>{row.uom}</td>
                    <td className="numeric">
                      {fmtQty(row.qty_on_hand)}{" "}
                      {Number(row.qty_on_hand) <= 0 && <Pill tone="negative">none</Pill>}
                    </td>
                    <td className="numeric">{fmtQty(row.reorder_level)}</td>
                    <td className="numeric">{fmtQty(row.shortfall)}</td>
                    <td className="numeric">{fmt(row.avg_cost, 4)}</td>
                    <td className="numeric">{fmt(row.reorder_value)}</td>
                  </tr>
                ))}
                <tr className="total-row">
                  <td colSpan={7}>About, at today&apos;s average costs</td>
                  <td className="numeric">{fmt(report?.total_reorder_value ?? "0")}</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {rows.length > 0 && (
          <p className="small muted" style={{ marginBottom: 0 }}>
            The restock figure is an estimate at each item&apos;s current average cost,
            not a quotation — a supplier&apos;s price on the day will differ. It is a
            size for the order, which is what a reorder list is for.
          </p>
        )}
      </Card>
    </>
  );
}
