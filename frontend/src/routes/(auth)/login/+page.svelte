<script lang="ts">
  import { goto } from "$app/navigation";

  import { login, getCurrentUser } from "$lib/api/auth";
  import { authStore } from "$lib/stores/auth";

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

<section class="mx-auto mt-16 max-w-sm p-6">
  <h1 class="mb-6 text-2xl font-bold">Entrar</h1>

  <form onsubmit={handleSubmit} class="space-y-4">
    <label class="block">
      <span class="text-sm text-slate-700">E-mail</span>
      <input
        type="email"
        required
        bind:value={email}
        class="mt-1 block w-full rounded border-slate-300 px-3 py-2"
      />
    </label>
    <label class="block">
      <span class="text-sm text-slate-700">Senha</span>
      <input
        type="password"
        required
        bind:value={password}
        class="mt-1 block w-full rounded border-slate-300 px-3 py-2"
      />
    </label>

    {#if error}
      <p class="text-sm text-red-600">{error}</p>
    {/if}

    <button
      type="submit"
      disabled={submitting}
      class="w-full rounded bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-50"
    >
      {submitting ? "Entrando…" : "Entrar"}
    </button>
  </form>

  <p class="mt-6 text-center text-sm text-slate-600">
    Sem conta? <a href="/register" class="underline">Cadastre-se</a>
  </p>
</section>
