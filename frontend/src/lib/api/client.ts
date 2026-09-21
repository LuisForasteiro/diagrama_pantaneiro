import { get } from "svelte/store";

import { authStore } from "$lib/stores/auth";
import { portfolioStore } from "$lib/stores/portfolio";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export const TIMEOUT_ERROR_MESSAGE = "o servidor demorou demais para responder";
export const NETWORK_ERROR_MESSAGE = "não foi possível conectar ao servidor";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`API error ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

/**
 * `timeoutMs` is opt-in: there is no default because some calls (price
 * refresh) legitimately take ~30 s. Status 0 in ApiError means the request
 * never got an HTTP answer (timeout or network failure).
 */
export type ApiRequestInit = RequestInit & { timeoutMs?: number };

async function fetchOrNetworkError(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (e) {
    // fetch rejects with TypeError when the server is unreachable (DNS,
    // connection refused, CORS); aborts surface as AbortError and pass through.
    if (e instanceof TypeError) throw new ApiError(0, NETWORK_ERROR_MESSAGE);
    throw e;
  }
}

function followSignal(controller: AbortController, external?: AbortSignal | null): () => void {
  if (!external) return () => {};
  const onAbort = () => controller.abort(external.reason);
  if (external.aborted) onAbort();
  else external.addEventListener("abort", onAbort, { once: true });
  return () => external.removeEventListener("abort", onAbort);
}

/**
 * Runs fetch + `handle(response)` under one deadline, so a backend that sends
 * headers and then stalls the body is also cut off. Shared by `apiRequest`
 * and the form-encoded `login()`.
 */
export async function guardedFetch<T>(
  url: string,
  init: ApiRequestInit,
  handle: (response: Response) => Promise<T>,
): Promise<T> {
  const { timeoutMs, ...requestInit } = init;
  if (timeoutMs === undefined) {
    return handle(await fetchOrNetworkError(url, requestInit));
  }

  const controller = new AbortController();
  const unfollow = followSignal(controller, requestInit.signal);
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetchOrNetworkError(url, { ...requestInit, signal: controller.signal });
    return await handle(response);
  } catch (e) {
    const isHttpAnswer = e instanceof ApiError && e.status > 0;
    if (timedOut && !isHttpAnswer) throw new ApiError(0, TIMEOUT_ERROR_MESSAGE);
    throw e;
  } finally {
    clearTimeout(timer);
    unfollow();
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    // Session is gone: drop the portfolio context too, otherwise the next
    // login (possibly another user) would send a stale X-Portfolio-Id.
    authStore.logout();
    portfolioStore.reset();
    throw new ApiError(401, "unauthorized");
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // response had no JSON body
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return (await response.json()) as T;
}

export async function apiRequest<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const token = get(authStore).token;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const activePortfolioId = get(portfolioStore).activeId;
  if (activePortfolioId) {
    headers["X-Portfolio-Id"] = activePortfolioId;
  }

  return guardedFetch(`${BASE_URL}/api${path}`, { ...init, headers }, (response) =>
    parseResponse<T>(response),
  );
}
