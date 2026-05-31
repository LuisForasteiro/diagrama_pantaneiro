<script lang="ts">
  import { onMount } from "svelte";
  import type { Snippet } from "svelte";

  interface Props {
    /** Required: a title string shown in the modal header. */
    title: string;
    /** Optional sub-label under the title. */
    sub?: string;
    onClose: () => void;
    /** "centered" (default) for forms; "fullscreen" for wide content like aporte. */
    variant?: "centered" | "fullscreen";
    /** Maximum width when variant=centered. Default 480px. */
    maxWidth?: string;
    children: Snippet;
    /** Optional slot for right-side actions in the header. */
    actions?: Snippet;
  }

  let {
    title,
    sub,
    onClose,
    variant = "centered",
    maxWidth = "480px",
    children,
    actions,
  }: Props = $props();

  // Close on Escape; restore body scroll on unmount.
  onMount(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = prevOverflow;
    };
  });
</script>

<div
  class="backdrop"
  role="presentation"
  onclick={(e) => {
    if (e.target === e.currentTarget) onClose();
  }}
>
  <div
    role="dialog"
    aria-modal="true"
    aria-labelledby="modal-title"
    class="modal pant-panel"
    class:fullscreen={variant === "fullscreen"}
    style:max-width={variant === "centered" ? maxWidth : undefined}
  >
    <div class="pant-bracket pant-bracket-tl"></div>
    <div class="pant-bracket pant-bracket-tr"></div>
    <div class="pant-bracket pant-bracket-bl"></div>
    <div class="pant-bracket pant-bracket-br"></div>

    <header class="modal-head">
      <div>
        <h2 id="modal-title" class="pant-panel-title">{title}</h2>
        {#if sub}
          <span class="pant-panel-sub">{sub}</span>
        {/if}
      </div>
      <div class="head-right">
        {#if actions}
          {@render actions()}
        {/if}
        <button
          type="button"
          class="close-btn"
          aria-label="Fechar"
          onclick={onClose}
        >×</button>
      </div>
    </header>

    <div class="body">
      {@render children()}
    </div>
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
    background: rgba(7, 16, 14, 0.75);
    backdrop-filter: blur(2px);
    animation: backdrop-in 180ms ease-out;
  }
  @keyframes backdrop-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  .modal {
    width: 100%;
    padding: 20px 22px;
    max-height: calc(100vh - 32px);
    overflow-y: auto;
    animation: modal-in 220ms cubic-bezier(0.2, 0.9, 0.3, 1);
  }
  .modal.fullscreen {
    max-width: 1180px;
    width: 100%;
    padding: 24px;
  }
  @keyframes modal-in {
    from { opacity: 0; transform: translateY(12px) scale(0.985); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }
  .modal-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    gap: 12px;
  }
  .head-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .close-btn {
    background: transparent;
    border: 1px solid var(--hairline);
    color: var(--ink-muted);
    font: inherit;
    font-size: 16px;
    cursor: pointer;
    padding: 2px 10px;
    line-height: 1;
    letter-spacing: 0;
  }
  .close-btn:hover { color: var(--accent); border-color: var(--accent-dim); }
</style>
