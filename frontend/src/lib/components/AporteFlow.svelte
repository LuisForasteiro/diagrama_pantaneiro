<script lang="ts">
  import { onMount, untrack } from "svelte";
  import {
    applyAllocation,
    createAporte,
    deleteAllocation,
  } from "$lib/api/aportes";
  import { listPositions } from "$lib/api/positions";
  import { CLASS_LABELS, CLASS_ORDER } from "$lib/classLabels";
  import { privacyStore } from "$lib/stores/privacy";
  import { formatBrl, formatQty } from "$lib/format";
  import type { AporteEventOut, PositionOut } from "$lib/types/api";
  import Panel from "$lib/components/Panel.svelte";

  interface Props {
    /**
     * Called whenever an action might have changed portfolio state
     * (a new event was created, an allocation was applied, or a
     * suggestion was removed/recomputed). Consumers should re-fetch
     * their own copies of positions / targets if needed.
     */
    onChanged?: () => void;
    /** Optional initial value to seed the input. Defaults to "500". */
    initialValue?: string;
  }

  let { onChanged, initialValue = "500" }: Props = $props();

  const CLASS_COLOR: Record<string, string> = {
    acoes_nacionais: "#e8822c",
    acoes_internacionais: "#b85a1d",
    etfs_nacionais: "#c97a3d",
    etfs_internacionais: "#dba35a",
    fundos_imobiliarios: "#d9b86a",
    reits: "#8a6a2e",
    criptomoedas: "#4fa8b8",
    rendafixa: "#7eb360",
    rendafixa_internacional: "#3e6b48",
  };

  // Seed the input once from the prop; later prop changes shouldn't clobber
  // what the user has typed. untrack makes that one-time intent explicit.
  let amountInput = $state(untrack(() => initialValue));
  let event = $state<AporteEventOut | null>(null);
  let positions = $state<PositionOut[]>([]);
  let calculating = $state(false);
  let applyingId = $state<string | null>(null);
  let removingId = $state<string | null>(null);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      positions = await listPositions();
    } catch {
      // non-fatal; flow still works without enrichment
    }
  });

  let masked = $derived($privacyStore);
  let fmtBRL = $derived((v: number) => formatBrl(v, masked));
  let fmtQty = $derived((v: number, digits = 6) => formatQty(v, masked, digits));

  async function handleCalcular(e: SubmitEvent) {
    e.preventDefault();
    const value = Number(amountInput);
    if (!Number.isFinite(value) || value <= 0) {
      error = "Informe um valor positivo";
      return;
    }
    error = null;
    calculating = true;
    try {
      event = await createAporte(value);
      positions = await listPositions();
      onChanged?.();
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      calculating = false;
    }
  }

  async function handleAportar(allocationId: string) {
    if (!event) return;
    applyingId = allocationId;
    error = null;
    try {
      const updated = await applyAllocation(event.id, allocationId);
      event = {
        ...event,
        allocations: event.allocations.map((a) =>
          a.id === allocationId ? { ...a, ...updated } : a,
        ),
      };
      positions = await listPositions();
      onChanged?.();
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      applyingId = null;
    }
  }

  async function handleRemove(allocationId: string, label: string) {
    if (!event) return;
    if (
      !confirm(
        `Excluir "${label}" deste aporte e redistribuir o valor entre as demais sugestões?`,
      )
    ) {
      return;
    }
    removingId = allocationId;
    error = null;
    try {
      event = await deleteAllocation(event.id, allocationId);
      onChanged?.();
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      removingId = null;
    }
  }

  let totalSuggested = $derived(
    event ? event.allocations.reduce((s, a) => s + a.suggestedValueBrl, 0) : 0,
  );
  let totalApplied = $derived(
    event
      ? event.allocations
          .filter((a) => a.applied)
          .reduce((s, a) => s + (a.appliedValueBrl ?? 0), 0)
      : 0,
  );
  let portfolioTotal = $derived(
    positions.reduce((s, p) => s + p.currentValueBrl, 0),
  );

  type EnrichedRow = {
    id: string;
    positionId: string | null;
    name: string;
    assetType: string;
    strength: number | null;
    currentValueBrl: number | null;
    priceAtAporteBrl: number | null;
    suggestedQuantity: number;
    suggestedValueBrl: number;
    totalAfterPct: number | null;
    applied: boolean;
    appliedValueBrl: number | null;
  };

  let rows = $derived<EnrichedRow[]>(
    event
      ? event.allocations
          .map((a) => {
            const pos = positions.find((p) => p.id === a.positionId);
            const newTotal = portfolioTotal + (event?.aporteValueBrl ?? 0);
            const currentValue = pos?.currentValueBrl ?? null;
            const totalAfterPct =
              pos && newTotal > 0
                ? ((pos.currentValueBrl + a.suggestedValueBrl) / newTotal) * 100
                : null;
            return {
              id: a.id,
              positionId: a.positionId,
              name: a.positionNameSnapshot,
              assetType: a.assetTypeSnapshot,
              strength: pos?.strength ?? null,
              currentValueBrl: currentValue,
              priceAtAporteBrl: a.priceAtAporteBrl,
              suggestedQuantity: a.suggestedQuantity,
              suggestedValueBrl: a.suggestedValueBrl,
              totalAfterPct,
              applied: a.applied,
              appliedValueBrl: a.appliedValueBrl,
            };
          })
          .sort((a, b) => b.suggestedValueBrl - a.suggestedValueBrl)
      : [],
  );

  type Segment = { assetType: string; pct: number; color: string; offset: number };
  let classSuggested = $derived.by(() => {
    const out: Record<string, number> = {};
    for (const c of CLASS_ORDER) out[c] = 0;
    if (event) {
      for (const a of event.allocations) {
        out[a.assetTypeSnapshot] = (out[a.assetTypeSnapshot] ?? 0) + a.suggestedValueBrl;
      }
    }
    return out;
  });
  let donutSegments = $derived.by<Segment[]>(() => {
    const aporte = event?.aporteValueBrl ?? 0;
    if (aporte <= 0) return [];
    const entries = CLASS_ORDER
      .map((c) => [c, ((classSuggested[c] ?? 0) / aporte) * 100] as const)
      .filter(([, pct]) => pct > 0.01)
      .sort((a, b) => b[1] - a[1]);
    const segs: Segment[] = [];
    let cursor = 0;
    for (const [assetType, pct] of entries) {
      segs.push({ assetType, pct, color: CLASS_COLOR[assetType] ?? "#6b7480", offset: cursor });
      cursor += pct;
    }
    return segs;
  });

  const RADIUS = 38;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
</script>

<Panel title="── valor_do_aporte ──" delay={0}>
  <form onsubmit={handleCalcular} class="calc-form">
    <label class="pant-label calc-input">
      <span class="pant-label-text">Valor (R$)</span>
      <input
        type="number"
        step="0.01"
        min="0"
        required
        bind:value={amountInput}
        class="pant-input"
      />
    </label>
    <button
      type="submit"
      disabled={calculating}
      class="pant-btn pant-btn-accent calc-submit"
    >
      {calculating ? "› calculando…" : "› calcular"}
    </button>
  </form>
</Panel>

{#if error}
  <p class="pant-toast pant-toast-err"><span class="pant-prompt">!</span> {error}</p>
{/if}

{#if event}
  <Panel delay={120}>
    <div class="summary">
      <div>
        <span class="pant-label-text">── aporte ──</span>
        <p class="summary-val pant-tab-nums">{fmtBRL(event.aporteValueBrl)}</p>
      </div>
      <div>
        <span class="pant-label-text">── total_sugerido ──</span>
        <p class="summary-val pant-tab-nums">{fmtBRL(totalSuggested)}</p>
      </div>
      {#if totalApplied > 0}
        <div>
          <span class="pant-label-text">── aplicado ──</span>
          <p class="summary-val summary-val--pos pant-tab-nums">{fmtBRL(totalApplied)}</p>
        </div>
      {/if}
    </div>
  </Panel>

  <Panel title="── distribuição_do_aporte ──" delay={240}>
    <div class="distrib">
      <svg viewBox="0 0 100 100" class="distrib-donut">
        <circle cx="50" cy="50" r={RADIUS} fill="none" stroke="var(--hairline)" stroke-width="1" />
        {#each donutSegments as s (s.assetType)}
          {@const len = (s.pct / 100) * CIRCUMFERENCE}
          {@const dashOffset = -((s.offset / 100) * CIRCUMFERENCE)}
          <circle
            cx="50"
            cy="50"
            r={RADIUS}
            fill="none"
            stroke={s.color}
            stroke-width="12"
            stroke-dasharray="{len} {CIRCUMFERENCE - len}"
            stroke-dashoffset={dashOffset}
            transform="rotate(-90 50 50)"
          />
        {/each}
        <circle cx="50" cy="50" r={RADIUS - 7} fill="none" stroke="var(--hairline)" stroke-width="0.5" />
        <text x="50" y="47" text-anchor="middle" class="donut-label-sm">aporte</text>
        <text x="50" y="56" text-anchor="middle" class="donut-label-lg">{fmtBRL(event.aporteValueBrl)}</text>
      </svg>
      <ul class="distrib-legend">
        {#each CLASS_ORDER as cls (cls)}
          {@const pct = event.aporteValueBrl > 0 ? (classSuggested[cls] / event.aporteValueBrl) * 100 : 0}
          <li class="distrib-row" class:zero={pct === 0}>
            <span class="swatch" style="background: {CLASS_COLOR[cls]}"></span>
            <span class="distrib-label">{CLASS_LABELS[cls]}</span>
            <span class="pant-tab-nums distrib-pct">{pct.toFixed(pct < 1 && pct > 0 ? 2 : 0)}%</span>
          </li>
        {/each}
      </ul>
    </div>
  </Panel>

  <Panel title="── sugestões [{rows.length}] ──" sub="× exclui e redistribui" delay={360}>
    <table class="pant-grid sugg-grid">
      <thead>
        <tr>
          <th class="col-tipo">Tipo</th>
          <th class="col-name">Ticker</th>
          <th class="pant-col-num">Atual</th>
          <th class="pant-col-num">Preço</th>
          <th class="pant-col-num">Nota</th>
          <th class="pant-col-num">Pós-aporte</th>
          <th class="pant-col-num">Sugest.</th>
          <th class="pant-col-num">Qtd</th>
          <th class="pant-col-num">Ação</th>
          <th class="col-rm"></th>
        </tr>
      </thead>
      <tbody>
        {#each rows as r (r.id)}
          <tr class:applied={r.applied}>
            <td class="col-tipo">
              <span
                class="class-chip"
                style="background: {CLASS_COLOR[r.assetType]}1a; color: {CLASS_COLOR[r.assetType]}; border-color: {CLASS_COLOR[r.assetType]}66"
              >
                {CLASS_LABELS[r.assetType] ?? r.assetType}
              </span>
            </td>
            <td class="col-name"><span class="pant-val">{r.name}</span></td>
            <td class="pant-col-num pant-tab-nums ink-dim">
              {r.currentValueBrl !== null ? fmtBRL(r.currentValueBrl) : "—"}
            </td>
            <td class="pant-col-num pant-tab-nums ink-dim">
              {r.priceAtAporteBrl !== null ? fmtBRL(r.priceAtAporteBrl) : "—"}
            </td>
            <td class="pant-col-num pant-tab-nums">
              {#if r.strength !== null}
                <span
                  class:ink-pos={r.strength > 0}
                  class:ink-neg={r.strength < 0}
                  class:ink-muted={r.strength === 0}
                >{r.strength > 0 ? "+" : ""}{r.strength}</span>
              {:else}<span class="ink-muted">—</span>{/if}
            </td>
            <td class="pant-col-num pant-tab-nums ink-dim">
              {r.totalAfterPct !== null ? `${r.totalAfterPct.toFixed(2)}%` : "—"}
            </td>
            <td class="pant-col-num pant-tab-nums pant-val">{fmtBRL(r.suggestedValueBrl)}</td>
            <td class="pant-col-num pant-tab-nums">{fmtQty(r.suggestedQuantity, 4)}</td>
            <td class="pant-col-num">
              {#if r.applied}
                <span class="applied-tag">✓ aplicado</span>
              {:else}
                <button
                  onclick={() => handleAportar(r.id)}
                  disabled={applyingId !== null || removingId !== null}
                  class="pant-btn pant-btn-accent"
                >
                  {applyingId === r.id ? "…" : "$ aportar"}
                </button>
              {/if}
            </td>
            <td class="col-rm">
              {#if !r.applied}
                <button
                  type="button"
                  onclick={() => handleRemove(r.id, r.name)}
                  disabled={removingId !== null || applyingId !== null}
                  title="Excluir esta sugestão e recalcular as restantes"
                  class="remove-btn"
                >
                  {removingId === r.id ? "…" : "×"}
                </button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </Panel>
{:else}
  <p class="pant-loading"><span class="pant-prompt">»</span> informe o valor do aporte e clique em <strong>calcular</strong> para ver onde alocar.</p>
{/if}

<style>
  .calc-form {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
    align-items: end;
  }
  .calc-input { max-width: 240px; margin: 0; }
  .calc-submit { padding: 8px 16px; font-size: 13px; }

  .summary {
    display: flex;
    gap: 40px;
    flex-wrap: wrap;
  }
  .summary-val {
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 4px 0 0;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
  }
  .summary-val--pos { color: var(--positive); }

  .distrib {
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 32px;
    align-items: center;
  }
  .distrib-donut { width: 100%; max-width: 220px; aspect-ratio: 1; }
  .donut-label-sm {
    font-size: 4px;
    fill: var(--ink-muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-family: "JetBrains Mono", monospace;
  }
  .donut-label-lg {
    font-size: 8px;
    fill: var(--accent);
    font-weight: 800;
    letter-spacing: 0.04em;
    font-family: "JetBrains Mono", monospace;
  }
  .distrib-legend {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 4px;
  }
  .distrib-row {
    display: grid;
    grid-template-columns: 14px 1fr auto;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    padding: 4px 6px;
  }
  .distrib-row.zero { color: var(--ink-muted); }
  .distrib-row.zero .distrib-pct { color: var(--ink-muted); }
  .swatch { width: 10px; height: 10px; display: inline-block; }
  .distrib-label { color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .distrib-pct { color: var(--ink); font-weight: 700; }

  .sugg-grid .col-tipo { width: 16%; }
  .sugg-grid .col-name { width: 12%; word-break: break-word; }
  .sugg-grid .col-rm { width: 32px; }
  .sugg-grid tbody tr.applied td { opacity: 0.5; }
  .class-chip {
    display: inline-block;
    padding: 2px 8px;
    border: 1px solid transparent;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }
  .applied-tag {
    color: var(--positive);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .remove-btn {
    background: transparent;
    border: none;
    color: var(--ink-muted);
    font: inherit;
    font-size: 14px;
    cursor: pointer;
    padding: 2px 6px;
    line-height: 1;
    transition: color 120ms;
  }
  .remove-btn:hover:not(:disabled) { color: var(--negative); }
  .remove-btn:disabled { opacity: 0.3; cursor: not-allowed; }

  @media (max-width: 720px) {
    .distrib { grid-template-columns: 1fr; }
    .distrib-donut { max-width: 200px; margin: 0 auto; }
    .calc-form { grid-template-columns: 1fr; }
    .calc-input { max-width: none; }
  }
</style>
