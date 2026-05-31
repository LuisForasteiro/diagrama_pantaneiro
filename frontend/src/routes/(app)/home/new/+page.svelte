<script lang="ts">
  import { goto } from "$app/navigation";
  import Panel from "$lib/components/Panel.svelte";
  import PositionForm from "$lib/components/PositionForm.svelte";
  import Topbar from "$lib/components/Topbar.svelte";
</script>

<section class="pant-wrap pant-wrap--narrow">
  <Topbar subtitle="adicionar_posição">
    {#snippet nav()}
      <a class="pant-btn" href="/home">› voltar</a>
    {/snippet}
  </Topbar>

  <Panel title="── nova_posição ──" delay={0}>
    <PositionForm
      onCreated={() => goto("/home")}
      onCancel={() => goto("/home")}
    />
  </Panel>
</section>
