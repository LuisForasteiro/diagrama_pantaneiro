<script lang="ts">
  import "../app.css";
  import type { Snippet } from "svelte";

  let { children }: { children: Snippet } = $props();
</script>

<main class="min-h-screen" style="background: var(--bg); color: var(--ink);">
  {@render children()}
</main>
