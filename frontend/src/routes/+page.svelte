<script lang="ts">
</script>

<section class="pant-wrap--center">
  <div class="landing">
    <img src="/logo.png" alt="diagrama_pantaneiro" class="logo" />
    <h1 class="brand">
      <span class="pant-prompt">$</span>
      diagrama_pantaneiro
    </h1>
    <p class="tagline ink-dim">sua carteira no ritmo do pantanal.</p>
    <div class="actions">
      <a href="/login" class="pant-btn pant-btn-accent">› entrar</a>
      <a href="/register" class="pant-btn">cadastre-se</a>
    </div>
  </div>
</section>

<style>
  .landing {
    text-align: center;
    display: grid;
    justify-items: center;
    gap: 14px;
  }
  .logo {
    height: 96px;
    width: auto;
  }
  .brand {
    margin: 0;
    color: var(--accent);
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0.06em;
  }
  .tagline {
    margin: 0;
    font-size: 13px;
  }
  .actions {
    display: flex;
    gap: 10px;
    margin-top: 8px;
  }
</style>
