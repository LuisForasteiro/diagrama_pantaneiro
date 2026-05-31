import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiRequest, ApiError } from "../../src/lib/api/client";
import { authStore } from "../../src/lib/stores/auth";

const originalFetch = globalThis.fetch;

describe("apiRequest", () => {
  beforeEach(() => {
    authStore.logout();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
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
    const { get } = await import("svelte/store");
    expect(get(authStore).token).toBeNull();
  });
});
