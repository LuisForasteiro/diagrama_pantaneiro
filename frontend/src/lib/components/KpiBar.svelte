<script lang="ts">
  import { formatBrl, formatPriceAge, type PriceAge } from "$lib/format";

  interface Props {
    totalValue: number;
    positionCount: number;
    offTarget: number;
    priceUpdatedAtNewest: string | null;
    masked: boolean;
  }
  let { totalValue, positionCount, offTarget, priceUpdatedAtNewest, masked }: Props = $props();
  let age = $derived<PriceAge | null>(formatPriceAge(priceUpdatedAtNewest));
</script>

<div class="kpis reveal">
  <div class="kpi">
    <span class="kpi-label">patrimônio</span>
    <span class="kpi-value tab-nums">{formatBrl(totalValue, masked)}</span>
  </div>
  <div class="kpi">
    <span class="kpi-label">posições</span>
    <span class="kpi-value tab-nums">{positionCount}</span>
  </div>
  <div class="kpi">
    <span class="kpi-label">fora da meta</span>
    <span class="kpi-value tab-nums" class:warn={offTarget > 0}>{offTarget}</span>
  </div>
  <div class="kpi">
    <span class="kpi-label">preços</span>
    <span class="kpi-value kpi-sm" class:warn={age?.stale}>{age ? age.text : "—"}</span>
  </div>
</div>

<style>
  .kpis {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
    animation: fade-up 600ms cubic-bezier(0.2, 0.9, 0.3, 1) backwards;
  }
  .kpi {
    border: 1px solid var(--hairline);
    background: var(--surface);
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .kpi-label { font-size: 11px; color: var(--ink-muted); letter-spacing: 0.04em; }
  .kpi-value { font-size: 20px; font-weight: 700; color: var(--ink); }
  .kpi-sm { font-size: 14px; font-weight: 500; color: var(--ink-dim); }
  .kpi-value.warn { color: var(--accent); }
  @keyframes fade-up {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @media (max-width: 720px) {
    .kpis { grid-template-columns: repeat(2, 1fr); }
  }
</style>
