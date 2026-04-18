import { apiRequest } from "./client";
import type {
  PresetIn,
  PresetOut,
  TargetOut,
  TargetsUpdateBody,
} from "$lib/types/api";

export const listTargets = () => apiRequest<TargetOut[]>("/targets");

export const updateTargets = (body: TargetsUpdateBody) =>
  apiRequest<TargetOut[]>("/targets", {
    method: "PUT",
    body: JSON.stringify(body),
  });

export const listPresets = () => apiRequest<PresetOut[]>("/target-presets");

export const createPreset = (body: PresetIn) =>
  apiRequest<PresetOut>("/target-presets", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const deletePreset = (id: string) =>
  apiRequest<void>(`/target-presets/${id}`, {
    method: "DELETE",
  });
