<script lang="ts">
  import type { Snippet } from "svelte";
  import { goto } from "$app/navigation";
  import PrivacyToggle from "$lib/components/PrivacyToggle.svelte";
  import { authStore } from "$lib/stores/auth";

  let { children }: { children: Snippet } = $props();

  // The token can vanish mid-session (401 in apiRequest, logout elsewhere);
  // without this the user would be left on a page whose requests all fail.
  $effect(() => {
    if (!$authStore.token) {
      void goto("/login", { replaceState: true });
    }
  });
</script>

<PrivacyToggle />
{@render children()}
