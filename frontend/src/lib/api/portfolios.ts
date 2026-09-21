import { apiRequest } from "./client";
import type {
  PortfolioCreate,
  PortfolioOut,
  PortfolioRename,
} from "$lib/types/api";

export function listPortfolios(opts: { timeoutMs?: number } = {}): Promise<PortfolioOut[]> {
  return apiRequest<PortfolioOut[]>("/portfolios", { timeoutMs: opts.timeoutMs });
}

export function createPortfolio(name: string): Promise<PortfolioOut> {
  const body: PortfolioCreate = { name };
  return apiRequest<PortfolioOut>("/portfolios", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function renamePortfolio(id: string, name: string): Promise<PortfolioOut> {
  const body: PortfolioRename = { name };
  return apiRequest<PortfolioOut>(`/portfolios/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deletePortfolio(id: string): Promise<void> {
  return apiRequest<void>(`/portfolios/${id}`, { method: "DELETE" });
}
