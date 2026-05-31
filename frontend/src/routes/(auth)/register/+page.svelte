<script lang="ts">
  import { goto } from "$app/navigation";

  import { register } from "$lib/api/auth";
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
      await register(email, password);
      await goto("/login");
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

    <Panel title="── criar_conta ──" delay={0}>
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
          <span class="pant-label-hint">mínimo 8 caracteres</span>
          <input
            type="password"
            required
            minlength="8"
            bind:value={password}
            class="pant-input"
            autocomplete="new-password"
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
          {submitting ? "› criando…" : "› criar conta"}
        </button>
      </form>
    </Panel>

    <p class="auth-foot">
      <span class="ink-dim">já tem uma?</span>
      <a href="/login" class="auth-link">› entrar</a>
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
