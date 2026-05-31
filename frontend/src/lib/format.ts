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

const STALE_AFTER_MS = 36 * 60 * 60 * 1000; // 36h

export interface PriceAge {
  text: string;
  stale: boolean;
}

/** Human "há X" label for a price timestamp. `now` is injectable for tests. */
export function formatPriceAge(
  iso: string | null,
  now: number = Date.now(),
): PriceAge | null {
  if (!iso) return null;
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return null;
  const diff = now - ts;
  const stale = diff >= STALE_AFTER_MS;
  const min = Math.floor(diff / 60000);
  let text: string;
  if (min < 60) text = `há ${min} min`;
  else if (min < 60 * 24) text = `há ${Math.floor(min / 60)} h`;
  else text = `há ${Math.floor(min / (60 * 24))} d`;
  return { text, stale };
}
