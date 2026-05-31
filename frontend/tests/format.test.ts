import { describe, expect, it } from "vitest";
import { formatPriceAge } from "../src/lib/format";

describe("formatPriceAge", () => {
  it("returns null for null input", () => {
    expect(formatPriceAge(null, Date.now())).toBeNull();
  });

  it("formats minutes / hours / days and flags staleness", () => {
    const now = Date.parse("2026-05-31T12:00:00Z");
    const min30 = "2026-05-31T11:30:00Z";
    const h5 = "2026-05-31T07:00:00Z";
    const d2 = "2026-05-29T12:00:00Z";

    expect(formatPriceAge(min30, now)).toEqual({ text: "há 30 min", stale: false });
    expect(formatPriceAge(h5, now)).toEqual({ text: "há 5 h", stale: false });
    expect(formatPriceAge(d2, now)).toEqual({ text: "há 2 d", stale: true });
  });
});
