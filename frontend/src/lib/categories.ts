import type { CategoryTree } from "$lib/types/api";

/** Leaf category id -> effective target in percentage points.
 * Mirror of the backend leaf_effective_targets: a group with no children is a
 * leaf (its weight stands); a subgroup leaf is group% / 100 * subgroup%. */
export function leafEffectiveTargets(tree: CategoryTree): Record<string, number> {
  const out: Record<string, number> = {};
  for (const g of tree.groups) {
    if (g.children.length === 0) {
      out[g.id] = g.weightPct;
    } else {
      for (const c of g.children) {
        out[c.id] = (g.weightPct / 100) * c.weightPct;
      }
    }
  }
  return out;
}
