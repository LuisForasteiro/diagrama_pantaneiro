import { apiRequest } from "./client";
import type { CategoryTree, CategoryTreeIn } from "$lib/types/api";

export const getCategories = () => apiRequest<CategoryTree>("/categories");

export const putCategories = (body: CategoryTreeIn) =>
  apiRequest<CategoryTree>("/categories", {
    method: "PUT",
    body: JSON.stringify(body),
  });
