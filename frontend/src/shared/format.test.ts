/**
 * Formatting tests.
 *
 * The figures here come from the worked example in USER_MANUAL.md, which was
 * verified against the running API. Displayed values must match the manual: the
 * interface must round the same way the ledger does, never truncate.
 */

import { describe, expect, it } from "vitest";
import { fmt, fmtOrDash, fmtPct, fmtQty } from "./format";

describe("fmt — money", () => {
  it("rounds the sale figures from the manual", () => {
    // Step 3 of the worked example: sell 4 units at 600.
    expect(fmt("2400.0000")).toBe("2,400.00");
    expect(fmt("1347.4419")).toBe("1,347.44");
    expect(fmt("1052.5581")).toBe("1,052.56");
  });

  it("rounds up where truncation would lose a unit", () => {
    // The regression: 1052.5581 must not display as 1,052.55.
    expect(fmt("1052.5581")).not.toBe("1,052.55");
    expect(fmt("0.005")).toBe("0.01");
    expect(fmt("9.999")).toBe("10.00");
    expect(fmt("1.0059", 2)).toBe("1.01");
  });

  it("rounds average and unit costs at four places", () => {
    // Production step: total 3,368.6047 over 10 units.
    expect(fmt("336.86047000", 4)).toBe("336.8605");
    // Elephent Cement keeps its workbook precision.
    expect(fmt("32.27848101", 8)).toBe("32.27848101");
    expect(fmt("32.27848101", 4)).toBe("32.2785");
  });

  it("rounds a value down when it should", () => {
    expect(fmt("1.0049", 2)).toBe("1.00");
    expect(fmt("336.86044000", 4)).toBe("336.8604");
  });

  it("carries into the whole number", () => {
    expect(fmt("9.996", 2)).toBe("10.00");
    expect(fmt("99.999", 2)).toBe("100.00");
    expect(fmt("0.5", 0)).toBe("1");
    expect(fmt("0.4", 0)).toBe("0");
  });

  it("handles negatives", () => {
    expect(fmt("-1052.5581")).toBe("-1,052.56");
    expect(fmt("-474100.0000")).toBe("-474,100.00");
    expect(fmt("-0.005")).toBe("-0.01");
  });

  it("groups thousands and pads to the requested places", () => {
    expect(fmt("801600.0000")).toBe("801,600.00");
    expect(fmt("830652.5581")).toBe("830,652.56");
    expect(fmt("100")).toBe("100.00");
    expect(fmt("100", 0)).toBe("100");
  });

  it("accepts numbers as well as strings", () => {
    expect(fmt(2400)).toBe("2,400.00");
    expect(fmt(1347.4419)).toBe("1,347.44");
  });

  it("returns a dash for missing values", () => {
    expect(fmt(null)).toBe("—");
    expect(fmt(undefined)).toBe("—");
    expect(fmt("")).toBe("—");
  });
});

describe("fmtQty", () => {
  it("trims trailing zeros", () => {
    expect(fmtQty("10.0000")).toBe("10");
    expect(fmtQty("4.0000")).toBe("4");
    expect(fmtQty("790.0000")).toBe("790");
    expect(fmtQty("4.2000")).toBe("4.2");
  });

  it("groups thousands and keeps negatives", () => {
    expect(fmtQty("1,290.0000".replace(",", ""))).toBe("1,290");
    expect(fmtQty("-50.0000")).toBe("-50");
  });

  it("returns a dash for missing values", () => {
    expect(fmtQty(null)).toBe("—");
  });
});

describe("fmtPct", () => {
  it("shows the manual's margin figures", () => {
    expect(fmtPct("43.8566")).toBe("43.86%");
    expect(fmtPct("40.0000")).toBe("40%");
    expect(fmtPct("0")).toBe("0%");
  });

  it("returns a dash for missing values", () => {
    expect(fmtPct(null)).toBe("—");
  });
});

describe("fmtOrDash", () => {
  it("hides zero balances, as accounting convention expects", () => {
    expect(fmtOrDash("0.0000")).toBe("—");
    expect(fmtOrDash("2400.0000")).toBe("2,400.00");
    expect(fmtOrDash(null)).toBe("—");
  });
});
