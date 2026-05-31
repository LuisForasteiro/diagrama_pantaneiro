<script lang="ts">
  import { searchCatalog } from "$lib/api/catalog";
  import type { CandidateOut } from "$lib/types/api";

  interface Props {
    value: string;
    assetType: string;
    placeholder?: string;
    onselect: (candidate: CandidateOut) => void;
    oninput: (value: string) => void;
  }

  let { value, assetType, placeholder, onselect, oninput }: Props = $props();

  let suggestions = $state<CandidateOut[]>([]);
  let open = $state(false);
  let highlighted = $state(-1);
  let loading = $state(false);
  let timer: ReturnType<typeof setTimeout> | null = null;

  function debouncedSearch(q: string) {
    if (timer) clearTimeout(timer);
    if (!q.trim()) {
      suggestions = [];
      open = false;
      return;
    }
    timer = setTimeout(async () => {
      loading = true;
      try {
        suggestions = await searchCatalog(assetType, q);
        open = suggestions.length > 0;
        highlighted = -1;
      } catch {
        suggestions = [];
        open = false;
      } finally {
        loading = false;
      }
    }, 250);
  }

  function handleInput(e: Event) {
    const v = (e.currentTarget as HTMLInputElement).value;
    oninput(v);
    debouncedSearch(v);
  }

  function pick(c: CandidateOut) {
    onselect(c);
    suggestions = [];
    open = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      highlighted = Math.min(highlighted + 1, suggestions.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      highlighted = Math.max(highlighted - 1, 0);
    } else if (e.key === "Enter" && highlighted >= 0) {
      e.preventDefault();
      pick(suggestions[highlighted]);
    } else if (e.key === "Escape") {
      open = false;
    }
  }

  function handleBlur() {
    // Delay so click on a suggestion registers first
    setTimeout(() => {
      open = false;
    }, 150);
  }

  function handleFocus() {
    if (suggestions.length > 0) open = true;
  }
</script>

<div class="ac-wrap">
  <input
    type="text"
    {value}
    {placeholder}
    autocomplete="off"
    oninput={handleInput}
    onkeydown={handleKeydown}
    onblur={handleBlur}
    onfocus={handleFocus}
    class="pant-input"
  />

  {#if loading}
    <span class="ac-loading">…</span>
  {/if}

  {#if open && suggestions.length > 0}
    <ul class="ac-list">
      {#each suggestions as c, i (c.name + i)}
        <li>
          <button
            type="button"
            onmousedown={() => pick(c)}
            class="ac-item"
            class:hl={i === highlighted}
          >
            <span class="ac-name">
              <strong>{c.name}</strong>
              {#if c.label && c.label !== c.name}
                <span class="ink-dim"> — {c.label}</span>
              {/if}
            </span>
            {#if c.currentPriceBrl != null}
              <span class="ac-price pant-tab-nums">
                {c.currentPriceBrl.toLocaleString("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                })}
              </span>
            {/if}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .ac-wrap { position: relative; }
  .ac-loading {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 11px;
    color: var(--ink-muted);
  }
  .ac-list {
    position: absolute;
    top: calc(100% + 2px);
    left: 0;
    right: 0;
    z-index: 10;
    max-height: 260px;
    overflow-y: auto;
    list-style: none;
    margin: 0;
    padding: 0;
    background: var(--surface);
    border: 1px solid var(--hairline-strong);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.6);
  }
  .ac-item {
    display: flex;
    width: 100%;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
    padding: 8px 12px;
    background: transparent;
    border: none;
    border-bottom: 1px solid var(--hairline);
    color: var(--ink-dim);
    font: inherit;
    font-size: 12px;
    cursor: pointer;
    text-align: left;
    letter-spacing: 0.02em;
  }
  .ac-item:last-child { border-bottom: none; }
  .ac-item:hover, .ac-item.hl {
    color: var(--accent);
    background: #14201a;
  }
  .ac-name strong { color: var(--ink); }
  .ac-item:hover .ac-name strong,
  .ac-item.hl .ac-name strong { color: var(--accent); }
  .ac-price { color: var(--ink-muted); font-size: 11px; flex-shrink: 0; }
</style>
