<script lang="ts">
  import { onMount } from "svelte";
  import { deleteAporte, listAportes } from "$lib/api/aportes";
  import { privacyStore } from "$lib/stores/privacy";
  import { formatBrl } from "$lib/format";
  import type { AporteEventOut } from "$lib/types/api";
  import Panel from "$lib/components/Panel.svelte";
  import Topbar from "$lib/components/Topbar.svelte";

  let events = $state<AporteEventOut[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let deletingId = $state<string | null>(null);

  onMount(async () => {
    try {
      events = await listAportes();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  let masked = $derived($privacyStore);
  let fmtBRL = $derived((v: number) => formatBrl(v, masked));

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleString("pt-BR", {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  function appliedCount(e: AporteEventOut): number {
    return e.allocations.filter((a) => a.applied).length;
  }

  function totalApplied(e: AporteEventOut): number {
    return e.allocations
      .filter((a) => a.applied)
      .reduce((s, a) => s + (a.appliedValueBrl ?? 0), 0);
  }

  function canDelete(e: AporteEventOut): boolean {
    return e.allocations.every((a) => !a.applied);
  }

  async function handleDelete(e: AporteEventOut) {
    if (!canDelete(e)) return;
    if (!confirm(`Excluir o aporte de ${fmtBRL(e.aporteValueBrl)} do histórico?`)) {
      return;
    }
    deletingId = e.id;
    try {
      await deleteAporte(e.id);
      events = events.filter((x) => x.id !== e.id);
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      deletingId = null;
    }
  }
</script>

<section class="pant-wrap">
  <Topbar subtitle="histórico_de_aportes">
    {#snippet nav()}
      <a class="pant-btn" href="/home">› voltar</a>
      <a class="pant-btn pant-btn-accent" href="/aporte">› novo aporte ▸</a>
    {/snippet}
  </Topbar>

  {#if error}
    <p class="pant-toast pant-toast-err"><span class="pant-prompt">!</span> {error}</p>
  {/if}

  {#if loading}
    <p class="pant-loading"><span class="pant-blink">█</span> carregando histórico</p>
  {:else if events.length === 0}
    <Panel delay={0}>
      <div class="empty">
        <p class="empty-line"><span class="pant-prompt">»</span> nenhum aporte registrado.</p>
        <a href="/aporte" class="pant-btn pant-btn-accent">› criar primeiro aporte</a>
      </div>
    </Panel>
  {:else}
    <Panel title="── aportes [{events.length}] ──" sub="ordenados do mais recente" delay={0}>
      <table class="pant-grid hist-grid">
        <thead>
          <tr>
            <th class="col-when">Quando</th>
            <th class="pant-col-num">Valor</th>
            <th class="pant-col-num">Sugest.</th>
            <th class="pant-col-num">Aplicado</th>
            <th class="col-actions"></th>
          </tr>
        </thead>
        <tbody>
          {#each events as e (e.id)}
            {@const applied = appliedCount(e)}
            {@const total = e.allocations.length}
            <tr>
              <td class="col-when">{fmtDate(e.createdAt)}</td>
              <td class="pant-col-num pant-tab-nums pant-val">
                {fmtBRL(e.aporteValueBrl)}
              </td>
              <td class="pant-col-num pant-tab-nums ink-dim">{total}</td>
              <td
                class="pant-col-num pant-tab-nums"
                class:ink-pos={applied > 0}
                class:ink-muted={applied === 0}
              >
                {applied}/{total}{#if applied > 0}
                  · {fmtBRL(totalApplied(e))}{/if}
              </td>
              <td class="col-actions">
                <div class="actions">
                  <a class="pant-btn" href="/history/{e.id}">› detalhes</a>
                  {#if canDelete(e)}
                    <button
                      type="button"
                      class="pant-btn pant-btn-danger"
                      title="Excluir este aporte do histórico"
                      disabled={deletingId === e.id}
                      onclick={() => handleDelete(e)}
                    >
                      {deletingId === e.id ? "…" : "× excluir"}
                    </button>
                  {/if}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </Panel>
  {/if}
</section>

<style>
  .empty {
    text-align: center;
    padding: 24px 12px;
    display: grid;
    gap: 14px;
    justify-items: center;
  }
  .empty-line { color: var(--ink-dim); font-size: 13px; margin: 0; }

  .hist-grid .col-when { width: 28%; }
  .hist-grid .col-actions { width: 220px; }
  .actions {
    display: flex;
    gap: 4px;
    justify-content: flex-end;
    flex-wrap: nowrap;
  }
</style>
