<script lang="ts">
  import { createPosition } from "$lib/api/positions";
  import DiagramChecklist from "$lib/components/DiagramChecklist.svelte";
  import AutocompleteInput from "$lib/components/AutocompleteInput.svelte";
  import type { CandidateOut, PositionOut } from "$lib/types/api";

  interface Props {
    /** Called after a position is successfully created. */
    onCreated?: (created: PositionOut) => void;
    /** Cancel action — typically closes the host modal or navigates away. */
    onCancel?: () => void;
  }

  let { onCreated, onCancel }: Props = $props();

  let name = $state("");
  let assetType = $state("acoes_nacionais");
  let amountInput = $state("");
  let currentPriceInput = $state("");
  let strengthInput = $state("0");
  let diagramResponses = $state<string[]>([]);
  let submitting = $state(false);
  let error = $state<string | null>(null);

  const TYPES = [
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

  let isRF = $derived(
    assetType === "rendafixa" || assetType === "rendafixa_internacional",
  );
  let hasDiagram = $derived(
    assetType === "acoes_nacionais" ||
      assetType === "acoes_internacionais" ||
      assetType === "fundos_imobiliarios" ||
      assetType === "reits" ||
      assetType === "etfs_nacionais" ||
      assetType === "etfs_internacionais",
  );
  let searchable = $derived(
    assetType === "acoes_nacionais" ||
      assetType === "fundos_imobiliarios" ||
      assetType === "criptomoedas" ||
      assetType === "rendafixa",
  );
  let rfHasPrice = $derived(
    isRF && currentPriceInput !== "" && Number(currentPriceInput) > 0,
  );

  function handleCandidatePick(c: CandidateOut) {
    name = c.name;
    if (c.currentPriceBrl != null) {
      currentPriceInput = String(c.currentPriceBrl);
    }
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    submitting = true;
    error = null;
    try {
      const amount = Number(amountInput);
      let currentPrice: number | null;
      if (isRF) {
        currentPrice =
          currentPriceInput !== "" && Number(currentPriceInput) > 0
            ? Number(currentPriceInput)
            : null;
      } else {
        currentPrice = Number(currentPriceInput);
      }
      const created = await createPosition({
        name,
        assetType,
        amount,
        currentPrice,
        strength: hasDiagram ? 0 : parseInt(strengthInput, 10),
        diagramResponses: hasDiagram ? diagramResponses : null,
      });
      onCreated?.(created);
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      submitting = false;
    }
  }
</script>

{#if error}
  <p class="pant-toast pant-toast-err"><span class="pant-prompt">!</span> {error}</p>
{/if}

<form onsubmit={handleSubmit} class="pant-form">
  <label class="pant-label">
    <span class="pant-label-text">Nome / ticker</span>
    {#if searchable}
      <span class="pant-label-hint">
        digite para buscar — resultados de
        {assetType === "criptomoedas"
          ? "CoinGecko"
          : assetType === "rendafixa"
            ? "Tesouro Direto"
            : "Brapi"}
      </span>
      <AutocompleteInput
        value={name}
        {assetType}
        placeholder={isRF ? "tesouro renda" : "PETR"}
        oninput={(v) => (name = v)}
        onselect={handleCandidatePick}
      />
    {:else}
      <input
        type="text"
        required
        bind:value={name}
        class="pant-input"
        placeholder={isRF ? "LCI INTER 90,00" : "VTI"}
      />
    {/if}
  </label>

  <label class="pant-label">
    <span class="pant-label-text">Classe</span>
    <select bind:value={assetType} class="pant-input">
      {#each TYPES as t (t.v)}
        <option value={t.v}>{t.l}</option>
      {/each}
    </select>
  </label>

  <label class="pant-label">
    <span class="pant-label-text">
      {#if isRF}
        {rfHasPrice ? "Quantidade (unidades)" : "Valor (R$)"}
      {:else}
        Quantidade (ações / moedas)
      {/if}
    </span>
    {#if isRF}
      <span class="pant-label-hint">
        preencha o preço à direita se for precificado por unidade (Tesouro);
        deixe em branco para RF privada acompanhada em BRL
      </span>
    {/if}
    <input
      type="number"
      step="any"
      required
      bind:value={amountInput}
      class="pant-input"
    />
  </label>

  <label class="pant-label">
    <span class="pant-label-text">Preço atual (R$ por unidade)</span>
    {#if isRF}
      <span class="pant-label-hint">opcional para RF privada</span>
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
        {assetType}
        responses={diagramResponses}
        onchange={(ids) => (diagramResponses = ids)}
      />
    </div>
  {:else}
    <label class="pant-label">
      <span class="pant-label-text">Força (manual — sem diagrama para esta classe)</span>
      <input
        type="number"
        step="1"
        required
        bind:value={strengthInput}
        class="pant-input"
      />
    </label>
  {/if}

  <div class="pant-form-actions">
    <button
      type="submit"
      disabled={submitting}
      class="pant-btn pant-btn-accent"
    >
      {submitting ? "› salvando…" : "› adicionar posição"}
    </button>
    {#if onCancel}
      <button type="button" class="pant-btn" onclick={onCancel}>
        cancelar
      </button>
    {/if}
  </div>
</form>

<style>
  .diagram-wrap { margin-bottom: 14px; }
</style>
