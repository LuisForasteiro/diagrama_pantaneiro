import { apiRequest } from "./client";
import type { RefreshSummaryOut } from "$lib/types/api";

export const refreshPrices = () =>
  apiRequest<RefreshSummaryOut>("/prices/refresh", { method: "POST" });
