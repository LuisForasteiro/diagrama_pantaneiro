<script lang="ts">
  import { onMount } from "svelte";
  import { getCategories, putCategories } from "$lib/api/categories";
  import type { CategoryTreeIn } from "$lib/types/api";

  interface Props {
    onsaved: () => void;
    onclose: () => void;
  }

  let { onsaved, onclose }: Props = $props();

  interface SubDraft { name: string; weightPct: number }
  interface GroupDraft { name: string; weightPct: number; children: SubDraft[] }

  let groups = $state<GroupDraft[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let serverError = $state<string | null>(null);

  onMount(async () => {
    try {
      const tree = await getCategories();
      groups = tree.groups.map((g) => ({
        name: g.name,
        weightPct: Math.round(g.weightPct),
        children: g.children.map((c) => ({
          name: c.name,
          weightPct: Math.round(c.weightPct),
        })),
      }));
    } catch {
      groups = [];
    } finally {
      loading = false;
    }
  });

  let groupSum = $derived(groups.reduce((s, g) => s + (g.weightPct || 0), 0));
  let groupSumOk = $derived(groups.length === 0 || groupSum === 100);

  function childSum(g: GroupDraft): number {
    return g.children.reduce((s, c) => s + (c.weightPct || 0), 0);
  }
  let allChildrenOk = $derived(
    groups.every((g) => g.children.length === 0 || childSum(g) === 100),
  );
  let canSave = $derived(groupSumOk && allChildrenOk && !saving);

  function addGroup() {
    groups = [...groups, { name: "Novo grupo", weightPct: 0, children: [] }];
  }
  function removeGroup(i: number) {
    groups = groups.filter((_, idx) => idx !== i);
  }
  function addChild(i: number) {
    groups[i].children = [
      ...groups[i].children,
      { name: "Novo subgrupo", weightPct: 0 },
    ];
  }
  function removeChild(gi: number, ci: number) {
    groups[gi].children = groups[gi].children.filter((_, idx) => idx !== ci);
  }
  function clampInt(raw: string): number {
    const n = Number(raw);
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  async function save() {
    if (!canSave) return;
    saving = true;
    serverError = null;
    const body: CategoryTreeIn = {
      groups: groups.map((g) => ({
        name: g.name.trim(),
        weightPct: g.weightPct,
        children: g.children.map((c) => ({
          name: c.name.trim(),
          weightPct: c.weightPct,
        })),
      })),
    };
    try {
      await putCategories(body);
      onsaved();
    } catch (e) {
      serverError = e instanceof Error ? e.message : String(e);
    } finally {
      saving = false;
    }
  }
</script>

<div
  class="backdrop"
  role="presentation"
  onclick={(e) => { if (e.target === e.currentTarget) onclose(); }}
>
  <div role="dialog" aria-modal="true" aria-labelledby="edit-cats-title" class="modal pant-panel">
    <div class="pant-bracket pant-bracket-tl"></div>
    <div class="pant-bracket pant-bracket-tr"></div>
    <div class="pant-bracket pant-bracket-bl"></div>
    <div class="pant-bracket pant-bracket-br"></div>

    <header class="modal-head">
      <h2 id="edit-cats-title" class="pant-panel-title">── editar_categorias ──</h2>
      <button type="button" class="close-btn" aria-label="Fechar" onclick={onclose}>×</button>
    </header>

    {#if loading}
      <p class="pant-loading">carregando…</p>
    {:else}
      <p class="hint ink-muted">
        Grupos somam 100%. Os subgrupos de cada grupo também somam 100%. Um grupo
        sem subgrupos é uma folha (recebe posições direto).
      </p>

      <div class="tree">
        {#each groups as g, gi (gi)}
          <div class="group">
            <div class="row">
              <input class="pant-input name" bind:value={g.name} maxlength="64" />
              <span class="winput">
                <input
                  class="pant-input num"
                  type="number" min="0" max="100" step="1"
                  value={g.weightPct}
                  oninput={(e) => (g.weightPct = clampInt((e.currentTarget as HTMLInputElement).value))}
                />
                <span class="ink-muted">%</span>
              </span>
              <button type="button" class="x" aria-label="remover grupo" onclick={() => removeGroup(gi)}>×</button>
            </div>

            {#each g.children as c, ci (ci)}
              <div class="row child">
                <input class="pant-input name" bind:value={c.name} maxlength="64" />
                <span class="winput">
                  <input
                    class="pant-input num"
                    type="number" min="0" max="100" step="1"
                    value={c.weightPct}
                    oninput={(e) => (c.weightPct = clampInt((e.currentTarget as HTMLInputElement).value))}
                  />
                  <span class="ink-muted">%</span>
                </span>
                <button type="button" class="x" aria-label="remover subgrupo" onclick={() => removeChild(gi, ci)}>×</button>
              </div>
            {/each}

            {#if g.children.length > 0}
              <span class="csum" class:bad={childSum(g) !== 100}>subgrupos: {childSum(g)}% / 100%</span>
            {/if}
            <button type="button" class="add-sub" onclick={() => addChild(gi)}>+ subgrupo</button>
          </div>
        {/each}
      </div>

      <button type="button" class="pant-btn add-group" onclick={addGroup}>+ grupo</button>

      <div class="pant-hr">┼──────────────────────────────</div>

      <div class="modal-foot">
        <p class="pant-tab-nums total" class:total-ok={groupSumOk} class:total-bad={!groupSumOk}>
          Grupos: {groupSum}% / 100%
        </p>
        <div class="pant-form-actions foot-actions">
          <button type="button" class="pant-btn" onclick={onclose}>cancelar</button>
          <button type="button" class="pant-btn pant-btn-accent" disabled={!canSave} onclick={save}>
            {saving ? "› salvando…" : "› salvar"}
          </button>
        </div>
      </div>

      {#if serverError}
        <p class="pant-toast pant-toast-err foot-err"><span class="pant-prompt">!</span> {serverError}</p>
      {/if}
    {/if}
  </div>
</div>

<style>
  .backdrop {
    position: fixed; inset: 0; z-index: 40; display: grid; place-items: center;
    padding: 16px; background: rgba(7, 16, 14, 0.75); backdrop-filter: blur(2px);
  }
  .modal { width: 100%; max-width: 460px; padding: 20px 22px; max-height: 90vh; overflow-y: auto; }
  .modal-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .close-btn { background: transparent; border: none; color: var(--ink-muted); font: inherit; font-size: 18px; cursor: pointer; padding: 0 6px; line-height: 1; }
  .close-btn:hover { color: var(--accent); }
  .hint { font-size: 11px; margin: 0 0 12px; }
  .tree { display: grid; gap: 10px; }
  .group { border: 1px solid var(--hairline); padding: 8px 10px; background: var(--surface-raised); }
  .row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
  .row.child { padding-left: 16px; }
  .name { flex: 1; padding: 4px 8px; font-size: 12px; }
  .winput { display: inline-flex; align-items: center; gap: 3px; }
  .num { width: 56px; padding: 4px 6px; font-size: 12px; text-align: right; }
  .x { background: transparent; border: none; color: var(--ink-muted); font: inherit; font-size: 14px; cursor: pointer; padding: 0 4px; }
  .x:hover { color: var(--negative); }
  .csum { font-size: 11px; color: var(--ink-dim); display: block; margin: 2px 0 4px 16px; }
  .csum.bad { color: var(--negative); }
  .add-sub { background: transparent; border: 1px dashed var(--hairline-strong); color: var(--ink-dim); font: inherit; font-size: 11px; padding: 2px 8px; cursor: pointer; margin-left: 16px; }
  .add-sub:hover { color: var(--accent); border-color: var(--accent-dim); }
  .add-group { margin-top: 10px; font-size: 12px; }
  .modal-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
  .total { font-size: 13px; margin: 0; font-weight: 700; }
  .total-ok { color: var(--positive); }
  .total-bad { color: var(--negative); }
  .foot-actions { margin-top: 0; }
  .foot-err { margin-top: 10px; margin-bottom: 0; }
</style>
