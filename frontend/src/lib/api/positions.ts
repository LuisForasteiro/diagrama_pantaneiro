import { apiRequest } from "./client";
import type {
  PositionOut,
  PositionCreate,
  PositionUpdate,
} from "$lib/types/api";

export const listPositions = () => apiRequest<PositionOut[]>("/positions");

export const createPosition = (body: PositionCreate) =>
  apiRequest<PositionOut>("/positions", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const updatePosition = (id: string, body: PositionUpdate) =>
  apiRequest<PositionOut>(`/positions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deletePosition = (id: string) =>
  apiRequest<void>(`/positions/${id}`, { method: "DELETE" });
