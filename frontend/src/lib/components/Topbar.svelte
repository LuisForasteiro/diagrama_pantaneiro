<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    /** Secondary segment after the brand (e.g. user email, page title). */
    subtitle?: string;
    /** Right-side nav slot — typically <a class="pant-btn"> entries. */
    nav?: Snippet;
  }

  let { subtitle, nav }: Props = $props();
</script>

<div class="pant-topbar">
  <div class="pant-brand">
    <img src="/logo.png" alt="diagrama_pantaneiro" class="pant-brand-logo" />
    <span class="pant-prompt">$</span>
    <span class="pant-brand-name">diagrama_pantaneiro</span>
    {#if subtitle}
      <span class="pant-sep">//</span>
      <span class="pant-title">{subtitle}</span>
    {/if}
  </div>
  {#if nav}
    <nav class="pant-nav">{@render nav()}</nav>
  {/if}
</div>
