<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/state";
  import { getAporte } from "$lib/api/aportes";
  import { privacyStore } from "$lib/stores/privacy";
  import { formatBrl, formatQty } from "$lib/format";
  import { CLASS_LABELS } from "$lib/classLabels";
  import type { AporteEventOut } from "$lib/types/api";
  import Panel from "$lib/components/Panel.svelte";
  import Topbar from "$lib/components/Topbar.svelte";

  let eventId = $derived(page.params.id);

  let event = $state<AporteEventOut | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      event = await getAporte(eventId as string);
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  let masked = $derived($privacyStore);
  let fmtBRL = $derived((v: number) => formatBrl(v, masked));
  let fmtQty = $derived((v: number, digits = 4) => formatQty(v, masked, digits));

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleString("pt-BR", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }
</script>

<section class="pant-wrap">
  <Topbar subtitle="detalhe_do_aporte">
    {#snippet nav()}
      <a class="pant-btn" href="/history">› histórico</a>
      <a class="pant-btn" href="/home">› carteira</a>
    {/snippet}
  </Topbar>

  {#if loading}
    <p class="pant-loading"><span class="pant-blink">█</span> carregando aporte</p>
  {:else if error}
    <p class="pant-toast pant-toast-err"><span class="pant-prompt">!</span> {error}</p>
  {:else if event}
    <Panel delay={0}>
      <div class="head">
        <div>
          <span class="pant-label-text">── quando ──</span>
          <p class="head-date">{fmtDate(event.createdAt)}</p>
        </div>
        <div>
          <span class="pant-label-text">── valor ──</span>
          <p class="head-val pant-tab-nums">{fmtBRL(event.aporteValueBrl)}</p>
        </div>
        <div>
          <span class="pant-label-text">── progresso ──</span>
          <p class="head-progress">
            {event.allocations.filter((a) => a.applied).length}
            <span class="ink-muted">/ {event.allocations.length} aplicadas</span>
          </p>
        </div>
      </div>
    </Panel>

    <Panel title="── alocações ──" delay={120}>
      <table class="pant-grid det-grid">
        <thead>
          <tr>
            <th class="col-name">Ativo</th>
            <th class="col-class">Classe</th>
            <th class="pant-col-num">Qtd sugerida</th>
            <th class="pant-col-num">BRL sugerido</th>
            <th class="pant-col-num">Status</th>
          </tr>
        </thead>
        <tbody>
          {#each event.allocations as a (a.id)}
            <tr class:applied={a.applied}>
              <td class="col-name"><span class="pant-val">{a.positionNameSnapshot}</span></td>
              <td class="col-class ink-dim">
                {CLASS_LABELS[a.assetTypeSnapshot] ?? a.assetTypeSnapshot}
              </td>
              <td class="pant-col-num pant-tab-nums">{fmtQty(a.suggestedQuantity)}</td>
              <td class="pant-col-num pant-tab-nums pant-val">{fmtBRL(a.suggestedValueBrl)}</td>
              <td class="pant-col-num">
                {#if a.applied}
                  <span class="applied-tag">
                    ✓ aplicado
                    {#if a.appliedValueBrl != null}
                      · {fmtBRL(a.appliedValueBrl)}
                    {/if}
                  </span>
                {:else}
                  <span class="ink-muted">ignorado</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </Panel>
  {/if}
</section>

<style>
  .head {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 24px;
  }
  .head-date {
    margin: 4px 0 0;
    font-size: 13px;
    color: var(--ink);
  }
  .head-val {
    margin: 4px 0 0;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: var(--ink);
    font-variant-numeric: tabular-nums;
  }
  .head-progress {
    margin: 4px 0 0;
    font-size: 18px;
    font-weight: 700;
    color: var(--positive);
  }

  .det-grid .col-name { width: 25%; word-break: break-word; }
  .det-grid .col-class { width: 25%; }
  .det-grid tbody tr.applied td { background: rgba(126, 179, 96, 0.06); }
  .applied-tag {
    color: var(--positive);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
</style>
