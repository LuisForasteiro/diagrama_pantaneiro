import { apiRequest } from "./client";
import type { CandidateOut } from "$lib/types/api";

export const searchCatalog = (type: string, q: string) =>
  apiRequest<CandidateOut[]>(
    `/catalog/search?type=${encodeURIComponent(type)}&q=${encodeURIComponent(q)}`,
  );
