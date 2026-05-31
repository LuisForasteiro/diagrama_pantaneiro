<script lang="ts">
  import { onMount } from "svelte";
  import {
    listPortfolios,
    createPortfolio,
    renamePortfolio,
    deletePortfolio,
  } from "$lib/api/portfolios";
  import { portfolioStore } from "$lib/stores/portfolio";
  import Panel from "$lib/components/Panel.svelte";
  import Topbar from "$lib/components/Topbar.svelte";
  import type { PortfolioOut } from "$lib/types/api";

  let portfolios = $state<PortfolioOut[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  let newName = $state("");
  let creating = $state(false);

  let editingId = $state<string | null>(null);
  let editingName = $state("");

  let deletingId = $state<string | null>(null);

  async function reload() {
    const list = await listPortfolios();
    portfolios = list;
    portfolioStore.setAll(list);
  }

  onMount(async () => {
    try {
      await reload();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  });

  async function handleCreate(e: SubmitEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    creating = true;
    error = null;
    try {
      await createPortfolio(name);
      newName = "";
      await reload();
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      creating = false;
    }
  }

  function beginEdit(p: PortfolioOut) {
    editingId = p.id;
    editingName = p.name;
  }

  async function commitRename(id: string) {
    const name = editingName.trim();
    if (!name) {
      editingId = null;
      return;
    }
    error = null;
    try {
      await renamePortfolio(id, name);
      editingId = null;
      await reload();
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    }
  }

  async function handleDelete(p: PortfolioOut) {
    if (portfolios.length <= 1) return;
    const ok = confirm(
      `Deletar "${p.name}"? Todas as posições, targets e histórico desta carteira serão perdidos. Esta ação não pode ser desfeita.`,
    );
    if (!ok) return;
    deletingId = p.id;
    error = null;
    try {
      await deletePortfolio(p.id);
      await reload();
    } catch (err) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      deletingId = null;
    }
  }
</script>

<section class="pant-wrap pant-wrap--narrow">
  <Topbar subtitle="gerenciar_carteiras">
    {#snippet nav()}
      <a class="pant-btn" href="/home">› voltar</a>
    {/snippet}
  </Topbar>

  {#if error}
    <p class="pant-toast pant-toast-err"><span class="pant-prompt">!</span> {error}</p>
  {/if}

  <Panel title="── carteiras ──" sub="{portfolios.length} total" delay={0}>
    {#if loading}
      <p class="pant-loading"><span class="pant-blink">█</span> carregando carteiras</p>
    {:else}
      <ul class="list">
        {#each portfolios as p (p.id)}
          <li class="row">
            <span class="pant-prompt">›</span>
            {#if editingId === p.id}
              <input
                type="text"
                class="pant-input row-input"
                bind:value={editingName}
                onblur={() => commitRename(p.id)}
                onkeydown={(e) => {
                  if (e.key === "Enter") commitRename(p.id);
                  if (e.key === "Escape") (editingId = null);
                }}
                aria-label="Renomear carteira"
              />
            {:else}
              <button
                type="button"
                class="row-name"
                onclick={() => beginEdit(p)}
                title="clique para renomear"
              >
                {p.name}
              </button>
            {/if}
            {#if p.isDefault}
              <span class="tag">padrão</span>
            {/if}
            <span class="row-date ink-muted">
              {new Date(p.createdAt).toLocaleDateString("pt-BR")}
            </span>
            <button
              type="button"
              class="pant-btn pant-btn-danger"
              onclick={() => handleDelete(p)}
              disabled={portfolios.length <= 1 || deletingId === p.id}
              title={portfolios.length <= 1
                ? "não é possível deletar a última carteira"
                : "deletar carteira"}
            >
              {deletingId === p.id ? "deletando…" : "× deletar"}
            </button>
          </li>
        {/each}
      </ul>

      <div class="pant-hr">┼──────────────────────────────</div>

      <form class="new-form" onsubmit={handleCreate}>
        <span class="pant-prompt">+</span>
        <input
          type="text"
          class="pant-input grow"
          placeholder="nome da nova carteira (ex: carteira do meu pai)"
          bind:value={newName}
          maxlength="64"
          required
        />
        <button
          type="submit"
          class="pant-btn pant-btn-accent"
          disabled={creating || newName.trim().length === 0}
        >
          {creating ? "criando…" : "› criar"}
        </button>
      </form>
    {/if}
  </Panel>
</section>

<style>
  .list { list-style: none; margin: 0; padding: 0; }
  .row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 4px;
    border-bottom: 1px solid var(--hairline);
    font-size: 13px;
  }
  .row:last-child { border-bottom: none; }
  .row-name {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--ink);
    font: inherit;
    font-weight: 500;
    text-align: left;
    cursor: text;
    padding: 2px 0;
    letter-spacing: 0.02em;
  }
  .row-name:hover { color: var(--accent); }
  .row-input { flex: 1; padding: 4px 8px; font-size: 13px; }
  .tag {
    padding: 2px 8px;
    font-size: 10px;
    color: var(--bg);
    background: var(--accent-dim);
    letter-spacing: 0.05em;
  }
  .row-date { font-size: 11px; }

  .new-form {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .grow { flex: 1; }
</style>
