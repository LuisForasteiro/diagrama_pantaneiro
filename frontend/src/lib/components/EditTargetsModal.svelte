<script lang="ts">
  import { onMount } from "svelte";
  import {
    createPreset,
    deletePreset,
    listPresets,
    updateTargets,
  } from "$lib/api/targets";
  import { CLASS_LABELS, CLASS_ORDER } from "$lib/classLabels";
  import type {
    PresetOut,
    TargetOut,
    TargetsUpdateBody,
  } from "$lib/types/api";

  interface Props {
    initialTargets: TargetOut[];
    onsaved: (updated: TargetOut[]) => void;
    onclose: () => void;
  }

  let { initialTargets, onsaved, onclose }: Props = $props();

  function seedValues(): Record<string, number> {
    const out: Record<string, number> = {};
    for (const c of CLASS_ORDER) out[c] = 0;
    for (const t of initialTargets) {
      out[t.assetType] = Math.round(t.targetPercentage);
    }
    return out;
  }

  let values = $state<Record<string, number>>(seedValues());
  let sum = $derived(CLASS_ORDER.reduce((s, c) => s + (values[c] ?? 0), 0));
  let sumOk = $derived(sum === 100);

  let saving = $state(false);
  let serverError = $state<string | null>(null);

  let presets = $state<PresetOut[]>([]);
  let presetsLoading = $state(true);

  let addingPreset = $state(false);
  let newName = $state("");
  let newError = $state<string | null>(null);

  let confirmRemoveId = $state<string | null>(null);
  let confirmTimer: ReturnType<typeof setTimeout> | null = null;

  onMount(() => {
    listPresets()
      .then((list) => {
        presets = list;
      })
      .catch(() => {
        presets = [];
      })
      .finally(() => {
        presetsLoading = false;
      });
  });

  function handleInput(cls: string, raw: string) {
    const n = Number(raw);
    if (!Number.isFinite(n)) return;
    values[cls] = Math.max(0, Math.min(100, Math.round(n)));
  }

  function applyPreset(p: PresetOut) {
    for (const c of CLASS_ORDER) {
      values[c] = Math.round(p.values[c] ?? 0);
    }
  }

  function startRemove(id: string) {
    if (confirmRemoveId === id) return;
    confirmRemoveId = id;
    if (confirmTimer) clearTimeout(confirmTimer);
    confirmTimer = setTimeout(() => {
      confirmRemoveId = null;
    }, 3000);
  }

  async function confirmRemove(id: string) {
    if (confirmTimer) clearTimeout(confirmTimer);
    confirmTimer = null;
    confirmRemoveId = null;
    try {
      await deletePreset(id);
      presets = presets.filter((p) => p.id !== id);
    } catch (e) {
      serverError = e instanceof Error ? e.message : String(e);
    }
  }

  async function saveNewPreset() {
    newError = null;
    if (!newName.trim()) {
      newError = "Nome obrigatório";
      return;
    }
    try {
      const created = await createPreset({
        name: newName.trim(),
        values: { ...values },
      });
      presets = [...presets, created];
      newName = "";
      addingPreset = false;
    } catch (e) {
      newError = e instanceof Error ? e.message : String(e);
    }
  }

  async function save() {
    if (!sumOk) return;
    saving = true;
    serverError = null;
    const body: TargetsUpdateBody = {
      targets: CLASS_ORDER.map((c) => ({
        assetType: c,
        targetPercentage: values[c],
      })),
    };
    try {
      const updated = await updateTargets(body);
      onsaved(updated);
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
  onclick={(e) => {
    if (e.target === e.currentTarget) onclose();
  }}
>
  <div
    role="dialog"
    aria-modal="true"
    aria-labelledby="edit-targets-title"
    class="modal pant-panel"
  >
    <div class="pant-bracket pant-bracket-tl"></div>
    <div class="pant-bracket pant-bracket-tr"></div>
    <div class="pant-bracket pant-bracket-bl"></div>
    <div class="pant-bracket pant-bracket-br"></div>

    <header class="modal-head">
      <h2 id="edit-targets-title" class="pant-panel-title">── editar_metas ──</h2>
      <button
        type="button"
        class="close-btn"
        aria-label="Fechar"
        onclick={onclose}
      >×</button>
    </header>

    <div class="section">
      <span class="pant-label-text">── presets ──</span>
      {#if presetsLoading}
        <p class="pant-loading">carregando…</p>
      {:else}
        {#if presets.length === 0 && !addingPreset}
          <p class="ink-muted preset-empty">› nenhum preset salvo.</p>
        {/if}
        <div class="preset-chips">
          {#each presets as p (p.id)}
            <div class="chip">
              <button
                type="button"
                class="chip-apply"
                title={p.name}
                onclick={() => applyPreset(p)}
              >{p.name}</button>
              {#if confirmRemoveId === p.id}
                <button
                  type="button"
                  class="chip-confirm"
                  onclick={() => confirmRemove(p.id)}
                >remover?</button>
              {:else}
                <button
                  type="button"
                  class="chip-x"
                  aria-label="Remover preset {p.name}"
                  onclick={() => startRemove(p.id)}
                >×</button>
              {/if}
            </div>
          {/each}
          {#if !addingPreset}
            <button
              type="button"
              class="chip-add"
              onclick={() => {
                addingPreset = true;
                newError = null;
              }}
            >+ novo</button>
          {/if}
        </div>
      {/if}

      {#if addingPreset}
        <div class="preset-add">
          <input
            type="text"
            maxlength="48"
            placeholder="nome do preset"
            bind:value={newName}
            class="pant-input"
          />
          <button
            type="button"
            class="pant-btn pant-btn-accent"
            disabled={!sumOk || !newName.trim()}
            title={!sumOk ? "Os valores precisam somar 100%" : ""}
            onclick={saveNewPreset}
          >salvar</button>
          <button
            type="button"
            class="pant-btn"
            onclick={() => {
              addingPreset = false;
              newName = "";
              newError = null;
            }}
          >cancelar</button>
        </div>
        {#if newError}
          <p class="pant-toast pant-toast-err">
            <span class="pant-prompt">!</span> {newError}
          </p>
        {/if}
      {/if}
    </div>

    <div class="pant-hr">┼──────────────────────────────</div>

    <div class="targets-grid">
      {#each CLASS_ORDER as cls (cls)}
        <label class="trow">
          <span class="trow-label">{CLASS_LABELS[cls]}</span>
          <span class="trow-input">
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              inputmode="numeric"
              value={values[cls]}
              oninput={(e) => handleInput(cls, (e.currentTarget as HTMLInputElement).value)}
              class="pant-input pant-tab-nums target-num"
              data-testid="target-input-{cls}"
            />
            <span class="ink-muted">%</span>
          </span>
        </label>
      {/each}
    </div>

    <div class="pant-hr">┼──────────────────────────────</div>

    <div class="modal-foot">
      <p
        class="pant-tab-nums total"
        class:total-ok={sumOk}
        class:total-bad={!sumOk}
        data-testid="total-indicator"
      >
        Total: {sum}% / 100%
      </p>
      <div class="pant-form-actions foot-actions">
        <button type="button" class="pant-btn" onclick={onclose}>cancelar</button>
        <button
          type="button"
          class="pant-btn pant-btn-accent"
          disabled={!sumOk || saving}
          onclick={save}
          data-testid="save-button"
        >{saving ? "› salvando…" : "› salvar"}</button>
      </div>
    </div>

    {#if serverError}
      <p class="pant-toast pant-toast-err foot-err">
        <span class="pant-prompt">!</span> {serverError}
      </p>
    {/if}
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 40;
    display: grid;
    place-items: center;
    padding: 16px;
    background: rgba(7, 16, 14, 0.75); /* var(--bg) with alpha */
    backdrop-filter: blur(2px);
  }
  .modal {
    width: 100%;
    max-width: 420px;
    margin: 0;
    padding: 20px 22px;
    max-height: 90vh;
    overflow-y: auto;
  }
  .modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }
  .close-btn {
    background: transparent;
    border: none;
    color: var(--ink-muted);
    font: inherit;
    font-size: 18px;
    cursor: pointer;
    padding: 0 6px;
    line-height: 1;
  }
  .close-btn:hover { color: var(--accent); }

  .section { margin-bottom: 8px; }
  .preset-empty {
    margin: 6px 0 0;
    font-size: 12px;
  }
  .preset-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--hairline);
    background: var(--surface-raised);
    font-size: 12px;
    letter-spacing: 0.02em;
  }
  .chip-apply {
    background: transparent;
    border: none;
    color: var(--ink);
    font: inherit;
    font-size: 12px;
    padding: 3px 8px;
    cursor: pointer;
    max-width: 10rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .chip-apply:hover { color: var(--accent); }
  .chip-x {
    background: transparent;
    border: none;
    color: var(--ink-muted);
    font: inherit;
    font-size: 14px;
    padding: 3px 8px;
    cursor: pointer;
    line-height: 1;
  }
  .chip-x:hover { color: var(--negative); }
  .chip-confirm {
    background: transparent;
    border: none;
    color: var(--negative);
    font: inherit;
    font-size: 11px;
    padding: 3px 8px;
    cursor: pointer;
    letter-spacing: 0.02em;
  }
  .chip-confirm:hover { text-decoration: underline; }
  .chip-add {
    background: transparent;
    border: 1px dashed var(--hairline-strong);
    color: var(--ink-dim);
    font: inherit;
    font-size: 12px;
    padding: 3px 10px;
    cursor: pointer;
    letter-spacing: 0.02em;
  }
  .chip-add:hover {
    color: var(--accent);
    border-color: var(--accent-dim);
  }

  .preset-add {
    display: flex;
    gap: 6px;
    margin-top: 8px;
    align-items: center;
  }
  .preset-add .pant-input { flex: 1; padding: 5px 8px; font-size: 12px; }

  .targets-grid {
    display: grid;
    gap: 6px;
  }
  .trow {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    font-size: 12px;
  }
  .trow-label { color: var(--ink); }
  .trow-input {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .target-num {
    width: 64px;
    padding: 4px 8px;
    font-size: 12px;
    text-align: right;
  }

  .modal-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
  }
  .total {
    font-size: 13px;
    margin: 0;
    font-weight: 700;
  }
  .total-ok { color: var(--positive); }
  .total-bad { color: var(--negative); }
  .foot-actions { margin-top: 0; }
  .foot-err { margin-top: 10px; margin-bottom: 0; }
</style>
