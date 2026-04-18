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

<div class="relative">
  <input
    type="text"
    {value}
    {placeholder}
    autocomplete="off"
    oninput={handleInput}
    onkeydown={handleKeydown}
    onblur={handleBlur}
    onfocus={handleFocus}
    class="mt-1 block w-full rounded border-slate-300 px-3 py-2"
  />

  {#if loading}
    <span
      class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400"
    >
      …
    </span>
  {/if}

  {#if open && suggestions.length > 0}
    <ul
      class="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded border border-slate-200 bg-white shadow-md"
    >
      {#each suggestions as c, i (c.name + i)}
        <li>
          <button
            type="button"
            onmousedown={() => pick(c)}
            class="flex w-full items-start justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-slate-50"
            class:bg-slate-100={i === highlighted}
          >
            <span class="flex-1">
              <strong>{c.name}</strong>
              {#if c.label && c.label !== c.name}
                <span class="text-slate-500"> — {c.label}</span>
              {/if}
            </span>
            {#if c.currentPriceBrl != null}
              <span class="shrink-0 tabular-nums text-xs text-slate-500">
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
