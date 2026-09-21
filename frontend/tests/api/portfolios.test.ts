import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../src/lib/api/client";
import { listPortfolios } from "../../src/lib/api/portfolios";
import { hangingFetch, track } from "../helpers/fetch";

const originalFetch = globalThis.fetch;

describe("portfolios api", () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  it("listPortfolios GETs /api/portfolios", async () => {
    const fetchMock = vi.fn(async (..._args: Parameters<typeof fetch>) =>
      new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    globalThis.fetch = fetchMock as typeof fetch;

    await expect(listPortfolios()).resolves.toEqual([]);
    expect(String(fetchMock.mock.calls[0][0])).toContain("/api/portfolios");
  });

  it("listPortfolios forwards timeoutMs", async () => {
    vi.useFakeTimers();
    globalThis.fetch = hangingFetch() as typeof fetch;

    const outcome = track(listPortfolios({ timeoutMs: 15_000 }));
    await vi.advanceTimersByTimeAsync(15_000);

    expect(outcome.settled).toBe(true);
    expect(outcome.error).toBeInstanceOf(ApiError);
    expect(outcome.error).toMatchObject({ status: 0 });
  });
});
