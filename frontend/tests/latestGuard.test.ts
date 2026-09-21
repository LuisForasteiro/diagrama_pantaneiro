import { describe, expect, it } from "vitest";

import { createLatestGuard } from "../src/lib/latestGuard";

describe("createLatestGuard", () => {
  it("considers the only ticket current", () => {
    const guard = createLatestGuard();

    const isLatest = guard.begin();

    expect(isLatest()).toBe(true);
  });

  it("invalidates earlier tickets when a newer one begins (A then B: A's late response is dropped)", () => {
    const guard = createLatestGuard();

    const isA = guard.begin();
    const isB = guard.begin();

    expect(isA()).toBe(false);
    expect(isB()).toBe(true);
  });

  it("keeps separate guards independent", () => {
    const first = createLatestGuard();
    const second = createLatestGuard();

    const isFirst = first.begin();
    second.begin();

    expect(isFirst()).toBe(true);
  });
});
