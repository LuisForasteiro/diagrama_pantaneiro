<script lang="ts">
  import AporteFlow from "$lib/components/AporteFlow.svelte";
  import Topbar from "$lib/components/Topbar.svelte";
</script>

<section class="pant-wrap">
  <Topbar subtitle="novo_aporte">
    {#snippet nav()}
      <a class="pant-btn" href="/home">› voltar</a>
    {/snippet}
  </Topbar>

  <AporteFlow />
</section>
