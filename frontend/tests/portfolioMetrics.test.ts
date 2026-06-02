import { describe, expect, it } from "vitest";
import { offTargetCount } from "../src/lib/portfolioMetrics";

describe("offTargetCount", () => {
  it("counts entries whose |current - target| exceeds the tolerance", () => {
    const rows = [
      { current: 68, target: 40 }, // +28 -> fora
      { current: 12, target: 12.5 }, // -0.5 -> dentro (tol 1)
      { current: 7, target: 17.5 }, // -10.5 -> fora
      { current: 20, target: 20 }, // 0 -> dentro
    ];
    expect(offTargetCount(rows, 1)).toBe(2);
  });

  it("returns 0 for empty input", () => {
    expect(offTargetCount([], 1)).toBe(0);
  });
});
