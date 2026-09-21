import { error, redirect } from "@sveltejs/kit";
import { get } from "svelte/store";

import { getCurrentUser } from "$lib/api/auth";
import { ApiError } from "$lib/api/client";
import { listPortfolios } from "$lib/api/portfolios";
import { authStore } from "$lib/stores/auth";
import { portfolioStore } from "$lib/stores/portfolio";

import type { LayoutLoad } from "./$types";

export const ssr = false;

// Bootstrap requests must not hang forever: while the backend is booting (or
// frozen) the SPA would otherwise render a blank page with no feedback.
const BOOTSTRAP_TIMEOUT_MS = 15_000;
const BACKEND_UNAVAILABLE_MESSAGE =
  "não foi possível falar com o servidor — ele pode estar iniciando. tente novamente em instantes.";

// Token the cached portfolio list was loaded with. A different token means a
// new session (maybe another user), so the list/activeId must be refetched.
let portfoliosLoadedFor: string | null = null;

async function ensureUser(): Promise<void> {
  if (get(authStore).user) return;
  try {
    const user = await getCurrentUser({ timeoutMs: BOOTSTRAP_TIMEOUT_MS });
    authStore.setUser(user);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      authStore.logout();
      throw redirect(307, "/login");
    }
    // Transient failure (502 while the backend restarts, timeout, network):
    // keep the session and show the error page instead of logging out.
    throw error(503, BACKEND_UNAVAILABLE_MESSAGE);
  }
}

async function ensurePortfolios(token: string): Promise<void> {
  const hasList = get(portfolioStore).all.length > 0;
  if (hasList && portfoliosLoadedFor === token) return;
  try {
    const portfolios = await listPortfolios({ timeoutMs: BOOTSTRAP_TIMEOUT_MS });
    // setAll drops an activeId that isn't in the new list.
    portfolioStore.setAll(portfolios);
    portfoliosLoadedFor = token;
  } catch {
    // Swallow: the backend has a default-portfolio fallback in the
    // get_active_portfolio dep, so the app still works even if this fails.
  }
}

export const load: LayoutLoad = async () => {
  const { token } = get(authStore);
  if (!token) {
    throw redirect(307, "/login");
  }

  await ensureUser();
  await ensurePortfolios(token);

  return {};
};
