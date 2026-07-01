<script lang="ts">
  import { privacyStore } from "$lib/stores/privacy";

  let masked = $derived($privacyStore);
</script>

<button
  type="button"
  onclick={() => privacyStore.toggle()}
  aria-label={masked ? "Mostrar valores" : "Ocultar valores"}
  aria-pressed={masked}
  title={masked ? "Mostrar valores" : "Ocultar valores"}
  class="privacy-toggle"
>
  {#if masked}
    <!-- eye-off -->
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a19.78 19.78 0 0 1 5.17-6.06" />
      <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a19.86 19.86 0 0 1-3.18 4.39" />
      <path d="M9.88 9.88A3 3 0 1 0 14.12 14.12" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  {:else}
    <!-- eye -->
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  {/if}
</button>

<style>
  .privacy-toggle {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 60;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 38px;
    width: 38px;
    padding: 0;
    background: var(--surface);
    border: 1px solid var(--hairline-strong);
    color: var(--ink-dim);
    cursor: pointer;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.4);
    transition: color 120ms, border-color 120ms, background 120ms;
  }
  .privacy-toggle:hover {
    color: var(--accent);
    border-color: var(--accent-dim);
    background: #14201a;
  }
  .privacy-toggle:active { transform: translateY(1px); }
  /* When values are hidden, mark the control as "armed" with the accent tint. */
  .privacy-toggle[aria-pressed="true"] { color: var(--accent); }
</style>
