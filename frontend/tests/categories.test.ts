import { describe, expect, it } from "vitest";
import { leafEffectiveTargets } from "../src/lib/categories";
import type { CategoryTree } from "../src/lib/types/api";

const tree: CategoryTree = {
  groups: [
    { id: "g_btc", name: "Bitcoin", weightPct: 40, children: [] },
    {
      id: "g_br",
      name: "Brasil",
      weightPct: 25,
      children: [
        { id: "s_acoes", name: "Ações", weightPct: 50 },
        { id: "s_rf", name: "Renda Fixa", weightPct: 50 },
      ],
    },
    {
      id: "g_int",
      name: "Internacional",
      weightPct: 35,
      children: [{ id: "s_us", name: "Ações americanas", weightPct: 100 }],
    },
  ],
};

describe("leafEffectiveTargets", () => {
  it("computes path products; group-leaf keeps its weight", () => {
    const eff = leafEffectiveTargets(tree);
    expect(eff["g_btc"]).toBeCloseTo(40);
    expect(eff["s_acoes"]).toBeCloseTo(12.5);
    expect(eff["s_rf"]).toBeCloseTo(12.5);
    expect(eff["s_us"]).toBeCloseTo(35);
    expect(eff["g_br"]).toBeUndefined();
    const total = Object.values(eff).reduce((a, b) => a + b, 0);
    expect(total).toBeCloseTo(100);
  });
});
