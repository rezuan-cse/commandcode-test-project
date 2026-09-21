/**
 * Display helpers.
 *
 * Money arrives from the API as decimal strings (for example "1052.5581").
 * Formatting must round the way the ledger does, and must never pass through a
 * JavaScript number — a float would reintroduce exactly the drift the backend
 * avoids by using Decimal. Rounding is therefore done on the digit string.
 */

/** Round a decimal magnitude to `decimals` places, half-up, carrying leftwards. */
function roundMagnitude(
  whole: string,
  fraction: string,
  decimals: number,
): { whole: string; fraction: string } {
  const digits = fraction.padEnd(decimals + 1, "0");
  const kept = digits.slice(0, decimals);
  const nextDigit = digits.charAt(decimals);

  if (nextDigit < "5") {
    return { whole: whole || "0", fraction: kept };
  }

  const places = kept.split("");
  let carry = 1;
  for (let index = places.length - 1; index >= 0 && carry; index -= 1) {
    const digit = Number(places[index]) + carry;
    if (digit >= 10) {
      places[index] = "0";
    } else {
      places[index] = String(digit);
      carry = 0;
    }
  }

  let wholeOut = whole || "0";
  if (carry) {
    const wholeDigits = wholeOut.split("");
    let wholeCarry = 1;
    for (let index = wholeDigits.length - 1; index >= 0 && wholeCarry; index -= 1) {
      const digit = Number(wholeDigits[index]) + wholeCarry;
      if (digit >= 10) {
        wholeDigits[index] = "0";
      } else {
        wholeDigits[index] = String(digit);
        wholeCarry = 0;
      }
    }
    wholeOut = wholeCarry ? `1${wholeDigits.join("")}` : wholeDigits.join("");
  }

  return { whole: wholeOut, fraction: places.join("") };
}

/** Split a decimal value into its sign, whole part, and fraction. */
function splitValue(value: string): { negative: boolean; whole: string; fraction: string } {
  const text = value.trim();
  const negative = text.startsWith("-");
  const unsigned = negative ? text.slice(1) : text;
  const [whole = "0", fraction = ""] = unsigned.split(".");
  return { negative, whole: whole || "0", fraction };
}

/** Insert thousands separators. */
function group(digits: string): string {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** True when every digit is zero, so a minus sign would be misleading. */
function isZero(whole: string, fraction: string): boolean {
  return /^0*$/.test(whole) && /^0*$/.test(fraction);
}

/** Format a decimal value as a grouped number with fixed decimal places. */
export function fmt(value: string | number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || value === "") return "—";
  const { negative, whole, fraction } = splitValue(String(value));
  const rounded = roundMagnitude(whole, fraction, decimals);
  const sign = negative && !isZero(rounded.whole, rounded.fraction) ? "-" : "";
  const tail = rounded.fraction ? `.${rounded.fraction}` : "";
  return `${sign}${group(rounded.whole)}${tail}`;
}

/** Format a quantity, trimming trailing zeros so 10.0000 reads as 10. */
export function fmtQty(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const { negative, whole, fraction } = splitValue(String(value));
  const trimmed = fraction.replace(/0+$/, "");
  const body = trimmed ? `${group(whole)}.${trimmed}` : group(whole);
  return negative && !isZero(whole, fraction) ? `-${body}` : body;
}

/** Format a decimal value as a percentage, with at most two decimal places. */
export function fmtPct(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const { negative, whole, fraction } = splitValue(String(value));
  const rounded = roundMagnitude(whole, fraction, 2);
  const trimmed = rounded.fraction.replace(/0+$/, "");
  const body = trimmed ? `${group(rounded.whole)}.${trimmed}` : group(rounded.whole);
  return negative && !isZero(rounded.whole, rounded.fraction) ? `-${body}%` : `${body}%`;
}

/** Show a dash instead of a zero, matching accounting convention. */
export function fmtOrDash(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const { whole, fraction } = splitValue(String(value));
  if (isZero(whole, fraction)) return "—";
  return fmt(value);
}
