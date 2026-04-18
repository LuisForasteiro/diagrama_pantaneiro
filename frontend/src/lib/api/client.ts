import { get } from "svelte/store";

import { authStore } from "$lib/stores/auth";
import { portfolioStore } from "$lib/stores/portfolio";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`API error ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
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

  const response = await fetch(`${BASE_URL}/api${path}`, { ...init, headers });

  if (response.status === 401) {
    authStore.logout();
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
