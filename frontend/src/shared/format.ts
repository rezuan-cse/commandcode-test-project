/** Display helpers. Money is formatted from decimal strings, never from floats. */

/** Format a decimal string as a grouped number with fixed decimals. */
export function fmt(value: string | number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || value === "") return "—";
  const raw = typeof value === "number" ? value.toFixed(decimals) : value;
  const negative = raw.startsWith("-");
  const [whole, fraction = ""] = (negative ? raw.slice(1) : raw).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const padded = fractions(fraction, decimals);
  return `${negative ? "-" : ""}${grouped}${padded ? `.${padded}` : ""}`;
}

/** Format a quantity, trimming trailing zeros so 10.0000 reads as 10. */
export function fmtQty(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const raw = typeof value === "number" ? String(value) : value;
  const negative = raw.startsWith("-");
  const [whole, fraction = ""] = (negative ? raw.slice(1) : raw).split(".");
  const trimmed = fraction.replace(/0+$/, "");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const body = trimmed ? `${grouped}.${trimmed}` : grouped;
  return negative ? `-${body}` : body;
}

/** Format a decimal string as a percentage with at most two decimals. */
export function fmtPct(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(numeric)) return "—";
  return `${numeric.toFixed(numeric % 1 === 0 ? 0 : 2)}%`;
}

/** Show a dash instead of a zero, matching accounting convention. */
export function fmtOrDash(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (Number(value) === 0) return "—";
  return fmt(value);
}

function fractions(fraction: string, decimals: number): string {
  if (decimals === 0) return "";
  const padded = (fraction + "0".repeat(decimals)).slice(0, decimals);
  return padded;
}
