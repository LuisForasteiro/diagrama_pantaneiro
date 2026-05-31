<script lang="ts">
  import { goto } from "$app/navigation";
  import { page } from "$app/state";
  import { onMount } from "svelte";
  import {
    listPositions,
    updatePosition,
    deletePosition,
  } from "$lib/api/positions";
  import DiagramChecklist from "$lib/components/DiagramChecklist.svelte";
  import Panel from "$lib/components/Panel.svelte";
  import Topbar from "$lib/components/Topbar.svelte";
  import { CLASS_LABELS } from "$lib/classLabels";
  import type { PositionOut } from "$lib/types/api";

  let positionId = $derived(page.params.id);

  // Sentinel used by the "Classe efetiva" select to represent "no override".
  const EFFECTIVE_NONE = "__none__";
  const CLASSES = [
    { v: "acoes_nacionais", l: "Ações Nacionais" },
    { v: "acoes_internacionais", l: "Ações Internacionais" },
    { v: "etfs_nacionais", l: "ETFs Nacionais" },
    { v: "etfs_internacionais", l: "ETFs Internacionais" },
    { v: "fundos_imobiliarios", l: "Fundos Imobiliários" },
    { v: "reits", l: "REITs" },
    { v: "criptomoedas", l: "Criptomoedas" },
    { v: "rendafixa", l: "Renda Fixa" },
    { v: "rendafixa_internacional", l: "Renda Fixa Internacional" },
  ];

  let position = $state<PositionOut | null>(null);
  let amountInput = $state("");
  let currentPriceInput = $state("");
  let strengthInput = $state("");
  let diagramResponses = $state<string[]>([]);
  let effectiveClassInput = $state<string>(EFFECTIVE_NONE);
  let submitting = $state(false);
  let deleting = $state(false);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      const all = await listPositions();
      const p = all.find((x) => x.id === positionId);
      if (!p) {
        error = "posição não encontrada";
        return;
      }
      position = p;
      amountInput = String(p.amount);
      currentPriceInput = p.currentPrice != null ? String(p.currentPrice) : "";
      strengthInput = String(p.strength);
      diagramResponses = p.diagramResponses ?? [];
      effectiveClassInput = p.effectiveClass ?? EFFECTIVE_NONE;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  });

  let isRF = $derived(
    position?.assetType === "rendafixa" ||
      position?.assetType === "rendafixa_internacional",
  );
  let hasDiagram = $derived(
    position?.assetType === "acoes_nacionais" ||
      position?.assetType === "acoes_internacionais" ||
      position?.assetType === "fundos_imobiliarios" ||
      position?.assetType === "reits" ||
      position?.assetType === "etfs_nacionais" ||
      position?.assetType === "etfs_internacionais",
  );
  let rfHasPrice = $derived(
    isRF && currentPriceInput !== "" && Number(currentPriceInput) > 0,
  );

  async function handleSave(e: SubmitEvent) {
    e.preventDefault();
    if (!position) return;
    submitting = true;
    error = null;
    try {
      let currentPrice: number | null;
      if (isRF) {
        currentPrice =
          currentPriceInput !== "" && Number(currentPriceInput) > 0
            ? Number(currentPriceInput)
            : null;
      } else {
        currentPrice = Number(currentPriceInput);
      }
      const body: {
        amount: number;
        currentPrice: number | null;
        strength?: number;
        diagramResponses?: string[] | null;
        effectiveClass?: string | null;
      } = {
        amount: Number(amountInput),
        currentPrice,
        effectiveClass:
          effectiveClassInput === EFFECTIVE_NONE ? null : effectiveClassInput,
      };
      if (hasDiagram) {
        body.diagramResponses = diagramResponses;
      } else {
        body.strength = parseInt(strengthInput, 10);
      }
      await updatePosition(position.id, body);
      await goto("/home");
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      submitting = false;
    }
  }

  async function handleDelete() {
    if (!position) return;
    if (!confirm(`Deletar ${position.name}? Esta ação não pode ser desfeita.`)) return;
    deleting = true;
    error = null;
    try {
      await deletePosition(position.id);
      await goto("/home");
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
      deleting = false;
    }
  }
</script>

<section class="pant-wrap pant-wrap--narrow">
  <Topbar subtitle={position ? `editar // ${position.name}` : "carregando…"}>
    {#snippet nav()}
      <a class="pant-btn" href="/home">› voltar</a>
    {/snippet}
  </Topbar>

  {#if error}
    <p class="pant-toast pant-toast-err"><span class="pant-prompt">!</span> {error}</p>
  {/if}

  {#if position}
    <Panel delay={0}>
      <div class="info">
        <span class="pant-prompt">›</span>
        <strong class="info-name">{position.name}</strong>
        <span class="pant-sep">//</span>
        <span class="ink-dim">{CLASS_LABELS[position.assetType] ?? position.assetType}</span>
        <span class="pant-sep">//</span>
        <span class="ink-muted">origem: {position.source}</span>
      </div>
    </Panel>

    <Panel title="── editar ──" delay={120}>
      <form onsubmit={handleSave} class="pant-form">
        <label class="pant-label">
          <span class="pant-label-text">Classe efetiva (override semântico)</span>
          <span class="pant-label-hint">
            Algoritmo, donut e metas usam a classe efetiva quando setada. A
            busca de preço continua usando a classe original
            (<code>{position.assetType}</code>) — útil para OBTC3, IVVB11 e
            similares.
          </span>
          <select
            bind:value={effectiveClassInput}
            class="pant-input"
          >
            <option value={EFFECTIVE_NONE}>— usar classe original —</option>
            {#each CLASSES as c (c.v)}
              <option value={c.v}>{c.l}</option>
            {/each}
          </select>
        </label>

        <label class="pant-label">
          <span class="pant-label-text">
            {#if isRF}
              {rfHasPrice ? "Quantidade (unidades)" : "Valor (R$)"}
            {:else}
              Quantidade
            {/if}
          </span>
          <input
            type="number"
            step="any"
            required
            bind:value={amountInput}
            class="pant-input"
          />
        </label>

        <label class="pant-label">
          <span class="pant-label-text">Preço atual</span>
          {#if isRF}
            <span class="pant-label-hint">deixe em branco para RF privada</span>
          {/if}
          <input
            type="number"
            step="any"
            required={!isRF}
            bind:value={currentPriceInput}
            class="pant-input"
          />
        </label>

        {#if hasDiagram}
          <div class="diagram-wrap">
            <DiagramChecklist
              assetType={position.assetType}
              responses={diagramResponses}
              onchange={(ids) => (diagramResponses = ids)}
            />
          </div>
        {:else}
          <label class="pant-label">
            <span class="pant-label-text">Força (manual — sem diagrama)</span>
            <input
              type="number"
              step="1"
              required
              bind:value={strengthInput}
              class="pant-input"
            />
          </label>
        {/if}

        <div class="actions-row">
          <div class="pant-form-actions">
            <button
              type="submit"
              disabled={submitting || deleting}
              class="pant-btn pant-btn-accent"
            >
              {submitting ? "› salvando…" : "› salvar"}
            </button>
            <a href="/home" class="pant-btn">cancelar</a>
          </div>
          <button
            type="button"
            onclick={handleDelete}
            disabled={submitting || deleting}
            class="pant-btn pant-btn-danger"
          >
            {deleting ? "deletando…" : "× deletar"}
          </button>
        </div>
      </form>
    </Panel>
  {/if}
</section>

<style>
  .info {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 13px;
    letter-spacing: 0.02em;
  }
  .info-name { color: var(--ink); font-weight: 700; }
  .diagram-wrap { margin-bottom: 14px; }
  .actions-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }
</style>
