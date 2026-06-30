import { apiRequest } from "./client";
import type { AporteAllocationOut, AporteEventOut } from "$lib/types/api";

export const createAporte = (value: number) =>
  apiRequest<AporteEventOut>("/aportes", {
    method: "POST",
    body: JSON.stringify({ value }),
  });

export const listAportes = () => apiRequest<AporteEventOut[]>("/aportes");

export const getAporte = (id: string) =>
  apiRequest<AporteEventOut>(`/aportes/${id}`);

export const applyAllocation = (
  eventId: string,
  allocationId: string,
  body: { appliedValueBrl?: number; appliedQuantity?: number } = {},
) =>
  apiRequest<AporteAllocationOut>(
    `/aportes/${eventId}/allocations/${allocationId}/apply`,
    { method: "POST", body: JSON.stringify(body) },
  );

export const recomputeAporte = (eventId: string) =>
  apiRequest<AporteEventOut>(`/aportes/${eventId}/recompute`, {
    method: "POST",
  });

export const deleteAporte = (eventId: string) =>
  apiRequest<void>(`/aportes/${eventId}`, { method: "DELETE" });

export const deleteAllocation = (eventId: string, allocationId: string) =>
  apiRequest<AporteEventOut>(
    `/aportes/${eventId}/allocations/${allocationId}`,
    { method: "DELETE" },
  );
