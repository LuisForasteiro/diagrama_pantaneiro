import { beforeEach, describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";
import { isHttpError, isRedirect } from "@sveltejs/kit";

import type { PortfolioOut, UserRead } from "../../src/lib/types/api";

vi.mock("$lib/api/auth", () => ({ getCurrentUser: vi.fn() }));
vi.mock("$lib/api/portfolios", () => ({ listPortfolios: vi.fn() }));

const USER_A: UserRead = { id: "ua", email: "a@x.y", is_active: true, is_superuser: false, is_verified: true };
const USER_B: UserRead = { id: "ub", email: "b@x.y", is_active: true, is_superuser: false, is_verified: true };
const PORTFOLIOS_A: PortfolioOut[] = [{ id: "pa", name: "carteira a", isDefault: true, createdAt: "2026-01-01" }];
const PORTFOLIOS_B: PortfolioOut[] = [{ id: "pb", name: "carteira b", isDefault: true, createdAt: "2026-01-01" }];

/**
 * Simulates a full page load (F5 / first open): module state is re-evaluated,
 * so the auth store starts with the token from localStorage and no user —
 * exactly the situation in which the (app) layout has to call /users/me.
 */
async function boot(token: string | null) {
  vi.resetModules();
  localStorage.clear();
  if (token) localStorage.setItem("auth_token", token);

  const layout = await import("../../src/routes/(app)/+layout");
  const authApi = await import("$lib/api/auth");
  const portfoliosApi = await import("$lib/api/portfolios");
  const { ApiError } = await import("../../src/lib/api/client");
  const { authStore } = await import("../../src/lib/stores/auth");
  const { portfolioStore } = await import("../../src/lib/stores/portfolio");

  const getCurrentUser = vi.mocked(authApi.getCurrentUser);
  const listPortfolios = vi.mocked(portfoliosApi.listPortfolios);
  getCurrentUser.mockReset();
  listPortfolios.mockReset();

  async function runLoad(): Promise<unknown> {
    try {
      await layout.load({} as Parameters<typeof layout.load>[0]);
      return null;
    } catch (e) {
      return e;
    }
  }

  return { runLoad, getCurrentUser, listPortfolios, ApiError, authStore, portfolioStore };
}

describe("(app)/+layout load", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("redirects to /login when there is no token", async () => {
    const { runLoad, getCurrentUser } = await boot(null);

    const outcome = await runLoad();

    expect(isRedirect(outcome)).toBe(true);
    expect(outcome).toMatchObject({ status: 307, location: "/login" });
    expect(getCurrentUser).not.toHaveBeenCalled();
  });

  it("loads the user and portfolios with a bootstrap timeout", async () => {
    const { runLoad, getCurrentUser, listPortfolios, authStore, portfolioStore } = await boot("tok");
    getCurrentUser.mockResolvedValue(USER_A);
    listPortfolios.mockResolvedValue(PORTFOLIOS_A);

    expect(await runLoad()).toBeNull();

    expect(getCurrentUser).toHaveBeenCalledWith({ timeoutMs: 15_000 });
    expect(listPortfolios).toHaveBeenCalledWith({ timeoutMs: 15_000 });
    expect(get(authStore).user).toEqual(USER_A);
    expect(get(portfolioStore).activeId).toBe("pa");
  });

  it("keeps the session and shows the error page (503) when the backend answers 502", async () => {
    const { runLoad, getCurrentUser, ApiError, authStore } = await boot("tok");
    getCurrentUser.mockRejectedValue(new ApiError(502, "Bad Gateway"));

    const outcome = await runLoad();

    expect(isHttpError(outcome, 503)).toBe(true);
    expect(get(authStore).token).toBe("tok");
    expect(localStorage.getItem("auth_token")).toBe("tok");
  });

  it("keeps the session and shows the error page (503) on network failure / timeout", async () => {
    const { runLoad, getCurrentUser, ApiError, authStore } = await boot("tok");
    getCurrentUser.mockRejectedValue(new ApiError(0, "o servidor demorou demais para responder"));

    const outcome = await runLoad();

    expect(isHttpError(outcome, 503)).toBe(true);
    expect(get(authStore).token).toBe("tok");
    expect(localStorage.getItem("auth_token")).toBe("tok");
  });

  it("logs out and redirects to /login when the token is rejected (401)", async () => {
    const { runLoad, getCurrentUser, ApiError, authStore } = await boot("expired");
    getCurrentUser.mockRejectedValue(new ApiError(401, "unauthorized"));

    const outcome = await runLoad();

    expect(isRedirect(outcome)).toBe(true);
    expect(outcome).toMatchObject({ location: "/login" });
    expect(get(authStore).token).toBeNull();
    expect(localStorage.getItem("auth_token")).toBeNull();
  });

  it("treats the portfolio fetch as best-effort", async () => {
    const { runLoad, getCurrentUser, listPortfolios, ApiError } = await boot("tok");
    getCurrentUser.mockResolvedValue(USER_A);
    listPortfolios.mockRejectedValue(new ApiError(0, "não foi possível conectar ao servidor"));

    expect(await runLoad()).toBeNull();
  });

  it("does not refetch user or portfolios on later loads of the same session", async () => {
    const { runLoad, getCurrentUser, listPortfolios } = await boot("tok");
    getCurrentUser.mockResolvedValue(USER_A);
    listPortfolios.mockResolvedValue(PORTFOLIOS_A);

    await runLoad();
    await runLoad();

    expect(getCurrentUser).toHaveBeenCalledTimes(1);
    expect(listPortfolios).toHaveBeenCalledTimes(1);
  });

  it("refetches portfolios after logging in as another user (no stale X-Portfolio-Id)", async () => {
    const { runLoad, getCurrentUser, listPortfolios, authStore, portfolioStore } = await boot("tok-a");
    getCurrentUser.mockResolvedValue(USER_A);
    listPortfolios.mockResolvedValue(PORTFOLIOS_A);
    await runLoad();
    expect(get(portfolioStore).activeId).toBe("pa");

    // Session ends without the portfolio store being reset, then the login
    // page stores the new token + user before navigating back into (app).
    authStore.logout();
    authStore.login("tok-b", USER_B);
    listPortfolios.mockResolvedValue(PORTFOLIOS_B);

    expect(await runLoad()).toBeNull();

    expect(listPortfolios).toHaveBeenCalledTimes(2);
    expect(get(portfolioStore).all).toEqual(PORTFOLIOS_B);
    expect(get(portfolioStore).activeId).toBe("pb");
  });
});
