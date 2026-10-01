/**
 * CSV export.
 *
 * Kept as two pure-ish pieces so the part that decides what the file says can be
 * tested without a browser: `toCsv` builds the text, `downloadCsv` hands it to
 * the browser.
 *
 * Values are written as they are stored — `1234.0000`, not `1,234.00` — so the
 * columns sum in Excel. A formatted number would land in the spreadsheet as text
 * and quietly refuse to add up, which is the last thing an accountant needs.
 */

export interface CsvColumn<T> {
  header: string;
  value: (row: T) => string | number | null | undefined;
}

/**
 * Escape one cell.
 *
 * Excel splits on commas and treats a quote as the start of a quoted field, so a
 * value containing either — a customer called `Karim & Sons, Ltd`, or a narration
 * with a quotation in it — has to be wrapped and its quotes doubled. Newlines are
 * wrapped too, so a multi-line narration stays in one cell instead of spilling
 * into the rows below.
 */
function cell(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

/** Build CSV text: a header row, then one row per record. */
export function toCsv<T>(columns: CsvColumn<T>[], rows: T[]): string {
  const lines = [columns.map((column) => cell(column.header)).join(",")];
  for (const row of rows) {
    lines.push(columns.map((column) => cell(column.value(row))).join(","));
  }
  // CRLF, which is what Excel expects and what every other reader tolerates.
  return lines.join("\r\n");
}

/** `trial-balance-2026-10-31.csv`, or `accounts.csv` when no date applies. */
export function csvFilename(base: string, asOf?: string | null): string {
  return asOf ? `${base}-${asOf}.csv` : `${base}.csv`;
}

/** Save CSV text to a file, opening cleanly in Excel. */
export function downloadCsv(filename: string, csv: string): void {
  // The byte-order mark is what makes Excel read the file as UTF-8. Without it,
  // any non-ASCII text — a Bangla account name, a ৳ sign — arrives as mojibake.
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
