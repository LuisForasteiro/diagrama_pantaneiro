/** Quantas linhas meta-vs-atual estão fora da meta além da tolerância (pp). */
export function offTargetCount(
  rows: { current: number; target: number }[],
  tolerancePp = 1,
): number {
  return rows.filter((r) => Math.abs(r.current - r.target) > tolerancePp).length;
}
