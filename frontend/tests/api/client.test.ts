import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { get } from "svelte/store";

import { apiRequest, ApiError } from "../../src/lib/api/client";
import { authStore } from "../../src/lib/stores/auth";
import { portfolioStore } from "../../src/lib/stores/portfolio";
import { hangingFetch, track } from "../helpers/fetch";

const originalFetch = globalThis.fetch;

const TIMEOUT_MESSAGE = "o servidor demorou demais para responder";
const NETWORK_MESSAGE = "não foi possível conectar ao servidor";

describe("apiRequest", () => {
  beforeEach(() => {
    authStore.logout();
    portfolioStore.reset();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  it("sends JSON body and parses response", async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ) as typeof fetch;

    const result = await apiRequest<{ ok: boolean }>("/x", { method: "GET" });
    expect(result).toEqual({ ok: true });
  });

  it("adds Authorization header when token is set", async () => {
    authStore.login("my-token", { id: "u1", email: "a@b.c", is_active: true, is_superuser: false, is_verified: false });

    const fetchMock = vi.fn(async (..._args: Parameters<typeof fetch>) =>
      new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    globalThis.fetch = fetchMock as typeof fetch;

    await apiRequest("/x", { method: "GET" });

    const [, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer my-token");
  });

  it("throws ApiError for 4xx responses", async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify({ detail: "bad credentials" }), { status: 401 }),
    ) as typeof fetch;

    await expect(apiRequest("/x", { method: "GET" })).rejects.toThrow(ApiError);
  });

  it("logs out on 401", async () => {
    authStore.login("stale", { id: "u1", email: "a@b.c", is_active: true, is_superuser: false, is_verified: false });

    globalThis.fetch = vi.fn(async () =>
      new Response("{}", { status: 401 }),
    ) as typeof fetch;

    await expect(apiRequest("/x", { method: "GET" })).rejects.toThrow(ApiError);
    expect(get(authStore).token).toBeNull();
  });

  it("clears the portfolio list and active id on 401 (a new login must refetch them)", async () => {
    portfolioStore.setAll([{ id: "p1", name: "principal", isDefault: true, createdAt: "2026-01-01" }]);
    globalThis.fetch = vi.fn(async () => new Response("{}", { status: 401 })) as typeof fetch;

    await expect(apiRequest("/x")).rejects.toMatchObject({ status: 401 });

    expect(get(portfolioStore)).toEqual({ all: [], activeId: null });
    expect(localStorage.getItem("active_portfolio_id")).toBeNull();
  });

  it("returns undefined for 204 responses", async () => {
    globalThis.fetch = vi.fn(async () => new Response(null, { status: 204 })) as typeof fetch;

    await expect(apiRequest("/x", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("maps a non-ok response to ApiError(status, detail)", async () => {
    globalThis.fetch = vi.fn(async () =>
      new Response(JSON.stringify({ detail: "boom" }), { status: 502 }),
    ) as typeof fetch;

    await expect(apiRequest("/x")).rejects.toMatchObject({ status: 502, detail: "boom" });
  });

  it("maps a network failure (fetch TypeError) to ApiError(0)", async () => {
    globalThis.fetch = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }) as typeof fetch;

    const error = await apiRequest("/x").catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 0, detail: NETWORK_MESSAGE });
  });

  it("rejects with ApiError(0) once timeoutMs elapses on a frozen backend", async () => {
    vi.useFakeTimers();
    const fetchMock = hangingFetch();
    globalThis.fetch = fetchMock as typeof fetch;

    const outcome = track(apiRequest("/users/me", { timeoutMs: 15_000 }));

    await vi.advanceTimersByTimeAsync(14_999);
    expect(outcome.settled).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    expect(outcome.settled).toBe(true);
    expect(outcome.error).toBeInstanceOf(ApiError);
    expect(outcome.error).toMatchObject({ status: 0, detail: TIMEOUT_MESSAGE });
  });

  it("does not forward timeoutMs to fetch", async () => {
    const fetchMock = vi.fn(async (..._args: Parameters<typeof fetch>) =>
      new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    globalThis.fetch = fetchMock as typeof fetch;

    await apiRequest("/x", { timeoutMs: 5_000 });

    const [, init] = fetchMock.mock.calls[0];
    expect(init).not.toHaveProperty("timeoutMs");
    expect(init?.signal).toBeDefined();
  });

  it("has no timeout by default (long price refreshes must not be cut)", async () => {
    vi.useFakeTimers();
    globalThis.fetch = hangingFetch() as typeof fetch;

    const outcome = track(apiRequest("/prices/refresh", { method: "POST" }));
    await vi.advanceTimersByTimeAsync(10 * 60_000);

    expect(outcome.settled).toBe(false);
  });

  it("still honours a caller-provided signal when a timeout is also set", async () => {
    globalThis.fetch = hangingFetch() as typeof fetch;
    const controller = new AbortController();

    const pending = apiRequest("/x", { timeoutMs: 60_000, signal: controller.signal });
    controller.abort();

    const error = await pending.catch((e: unknown) => e);
    expect(error).not.toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ name: "AbortError" });
  });
});
