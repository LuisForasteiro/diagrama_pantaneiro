<script lang="ts">
  import { goto } from "$app/navigation";

  import { login, getCurrentUser } from "$lib/api/auth";
  import { authStore } from "$lib/stores/auth";
  import Panel from "$lib/components/Panel.svelte";

  let email = $state("");
  let password = $state("");
  let error = $state<string | null>(null);
  let submitting = $state(false);

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    error = null;
    submitting = true;
    try {
      const { access_token } = await login(email, password);
      authStore.login(access_token, { id: "", email, is_active: true, is_superuser: false, is_verified: false });
      const user = await getCurrentUser();
      authStore.setUser(user);
      await goto("/home");
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      submitting = false;
    }
  }
</script>

<section class="pant-wrap--center">
  <div class="auth-frame">
    <header class="auth-brand">
      <img src="/logo.png" alt="diagrama_pantaneiro" class="brand-logo" />
      <p class="brand-name">
        <span class="pant-prompt">$</span>
        diagrama_pantaneiro
      </p>
    </header>

    <Panel title="── entrar ──" delay={0}>
      <form onsubmit={handleSubmit} class="pant-form">
        <label class="pant-label">
          <span class="pant-label-text">E-mail</span>
          <input
            type="email"
            required
            bind:value={email}
            class="pant-input"
            autocomplete="email"
          />
        </label>
        <label class="pant-label">
          <span class="pant-label-text">Senha</span>
          <input
            type="password"
            required
            bind:value={password}
            class="pant-input"
            autocomplete="current-password"
          />
        </label>

        {#if error}
          <p class="pant-toast pant-toast-err">
            <span class="pant-prompt">!</span> {error}
          </p>
        {/if}

        <button
          type="submit"
          disabled={submitting}
          class="pant-btn pant-btn-accent pant-btn-wide"
        >
          {submitting ? "› entrando…" : "› entrar"}
        </button>
      </form>
    </Panel>

    <p class="auth-foot">
      <span class="ink-dim">sem conta?</span>
      <a href="/register" class="auth-link">› cadastre-se</a>
    </p>
  </div>
</section>

<style>
  .auth-frame {
    width: 100%;
    max-width: 380px;
  }
  .auth-brand {
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
  .auth-foot {
    margin-top: 18px;
    text-align: center;
    font-size: 12px;
  }
  .auth-link {
    color: var(--accent);
    text-decoration: none;
    margin-left: 6px;
  }
  .auth-link:hover { text-decoration: underline; }
</style>
