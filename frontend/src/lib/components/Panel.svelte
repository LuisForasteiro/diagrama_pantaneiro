<script lang="ts">
  import type { Snippet } from "svelte";

  interface Props {
    title?: string;
    sub?: string;
    delay?: number;
    /** Add the brackets decoration. Defaults to true. */
    brackets?: boolean;
    /** Optional extra class on the wrapping <section>. */
    class?: string;
    /** Right-side slot in the panel head (e.g. action buttons). */
    actions?: Snippet;
    children: Snippet;
  }

  let {
    title,
    sub,
    delay = 0,
    brackets = true,
    class: extraClass = "",
    actions,
    children,
  }: Props = $props();
</script>

<section
  class="pant-panel pant-reveal {extraClass}"
  style="--delay: {delay}ms"
>
  {#if brackets}
    <div class="pant-bracket pant-bracket-tl"></div>
    <div class="pant-bracket pant-bracket-tr"></div>
    <div class="pant-bracket pant-bracket-bl"></div>
    <div class="pant-bracket pant-bracket-br"></div>
  {/if}

  {#if title || sub || actions}
    <header class="pant-panel-head">
      <div>
        {#if title}
          <h2 class="pant-panel-title">{title}</h2>
        {/if}
        {#if sub}
          <span class="pant-panel-sub">{sub}</span>
        {/if}
      </div>
      {#if actions}
        <div class="panel-actions">{@render actions()}</div>
      {/if}
    </header>
  {/if}

  {@render children()}
</section>

<style>
  .panel-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }
</style>
