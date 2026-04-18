<script lang="ts">
  import type { Snippet } from "svelte";
  import PrivacyToggle from "$lib/components/PrivacyToggle.svelte";

  let { children }: { children: Snippet } = $props();
</script>

<PrivacyToggle />
{@render children()}
