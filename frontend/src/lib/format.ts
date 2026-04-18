const MASK = "••••";

export function formatBrl(v: number, masked = false): string {
  if (masked) return `R$ ${MASK}`;
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatBrlCompact(v: number, masked = false): string {
  if (masked) return `R$ ${MASK}`;
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `R$ ${(v / 1_000).toFixed(1)}k`;
  return formatBrl(v);
}

export function formatQty(
  v: number,
  masked = false,
  maxDigits = 6,
): string {
  if (masked) return MASK;
  return v.toLocaleString("pt-BR", { maximumFractionDigits: maxDigits });
}
