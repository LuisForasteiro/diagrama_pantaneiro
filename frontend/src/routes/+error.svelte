<script lang="ts">
  import { page } from "$app/state";
  import Panel from "$lib/components/Panel.svelte";

  const status = $derived(page.status);
  const message = $derived(
    status === 404
      ? "página não encontrada"
      : (page.error?.message ?? "algo deu errado — tente novamente."),
  );

  function retry() {
    location.reload();
  }
</script>

<svelte:head>
  <title>erro {status} · diagrama_pantaneiro</title>
</svelte:head>

<section class="pant-wrap--center">
  <div class="error-frame">
    <header class="error-brand">
      <img src="/logo.png" alt="diagrama_pantaneiro" class="brand-logo" />
      <p class="brand-name">
        <span class="pant-prompt">$</span>
        diagrama_pantaneiro
      </p>
    </header>

    <Panel title="── erro {status} ──" delay={0}>
      <p class="pant-toast pant-toast-err" role="alert">
        <span class="pant-prompt">!</span> {message}
      </p>

      <div class="error-actions">
        <button type="button" class="pant-btn pant-btn-accent pant-btn-wide" onclick={retry}>
          › tentar novamente
        </button>
        <a href="/login" class="error-link">› ir para o login</a>
      </div>
    </Panel>
  </div>
</section>

<style>
  .error-frame {
    width: 100%;
    max-width: 420px;
  }
  .error-brand {
    text-align: center;
    margin-bottom: 20px;
  }
  .brand-logo {
    height: 64px;
    margin: 0 auto 8px;
    display: block;
  }
  .brand-name {
    margin: 0;
    color: var(--accent);
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.06em;
  }
  .error-actions {
    display: grid;
    gap: 14px;
    justify-items: center;
  }
  .error-link {
    color: var(--accent);
    font-size: 12px;
    text-decoration: none;
  }
  .error-link:hover,
  .error-link:focus-visible {
    text-decoration: underline;
  }
</style>
