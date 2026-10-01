import { describe, expect, it } from "vitest";

import { csvFilename, toCsv, type CsvColumn } from "./csv";

interface Row {
  name: string;
  amount: string;
  note: string | null;
}

const COLUMNS: CsvColumn<Row>[] = [
  { header: "Customer", value: (row) => row.name },
  { header: "Amount", value: (row) => row.amount },
  { header: "Note", value: (row) => row.note },
];

function build(rows: Row[]): string {
  return toCsv(COLUMNS, rows);
}

describe("toCsv", () => {
  it("writes a header row even when there is nothing to export", () => {
    // An empty export should still open as a file with headings, so the reader can
    // see that there was nothing found rather than getting a surprise.
    expect(build([])).toBe("Customer,Amount,Note");
  });

  it("writes one line per record, in the order given", () => {
    const csv = build([
      { name: "Karim Enterprise", amount: "3000.0000", note: "paid" },
      { name: "Other Firm", amount: "10.0000", note: null },
    ]);
    expect(csv).toBe(
      "Customer,Amount,Note\r\n" +
        "Karim Enterprise,3000.0000,paid\r\n" +
        "Other Firm,10.0000,",
    );
  });

  it("quotes a value containing a comma, so the columns do not shift", () => {
    // "Karim & Sons, Ltd" would otherwise become two columns and every figure on
    // the row would be read against the wrong heading.
    const csv = build([{ name: "Karim & Sons, Ltd", amount: "5.0000", note: null }]);
    expect(csv).toContain('"Karim & Sons, Ltd",5.0000,');
  });

  it("doubles a quote inside a quoted value", () => {
    const csv = build([{ name: 'The "Big" Firm', amount: "1.0000", note: null }]);
    expect(csv).toContain('"The ""Big"" Firm",1.0000,');
  });

  it("keeps a newline inside one cell rather than starting a new row", () => {
    const csv = build([{ name: "Two\nlines", amount: "1.0000", note: null }]);
    expect(csv).toContain('"Two\nlines"');
  });

  it("leaves a stored amount alone so the column still sums", () => {
    // The figure is written as stored, not as displayed: "1,234.0000" would be
    // text to Excel and would not add up.
    const csv = build([{ name: "X", amount: "1234.0000", note: null }]);
    expect(csv).toContain(",1234.0000,");
    expect(csv).not.toContain("1,234");
  });

  it("writes a number value without quoting it", () => {
    const csv = toCsv<{ qty: number }>(
      [{ header: "Qty", value: (row) => row.qty }],
      [{ qty: 12 }],
    );
    expect(csv).toBe("Qty\r\n12");
  });

  it("writes an absent value as an empty cell", () => {
    const csv = toCsv<{ note: string | null }>(
      [{ header: "Note", value: (row) => row.note }],
      [{ note: null }],
    );
    expect(csv).toBe("Note\r\n");
  });
});

describe("csvFilename", () => {
  it("names a report after the date it covers", () => {
    expect(csvFilename("trial-balance", "2026-10-31")).toBe(
      "trial-balance-2026-10-31.csv",
    );
  });

  it("leaves the date out when the screen has no single date", () => {
    expect(csvFilename("customers")).toBe("customers.csv");
    expect(csvFilename("customers", null)).toBe("customers.csv");
  });
});
