import { apiRequest } from "./client";
import type {
  DiagramQuestionOut,
  DiagramQuestionCreate,
  DiagramQuestionUpdate,
} from "$lib/types/api";

export const listDiagramQuestions = (diagram?: string) => {
  const q = diagram ? `?diagram=${encodeURIComponent(diagram)}` : "";
  return apiRequest<DiagramQuestionOut[]>(`/diagram-questions${q}`);
};

export const createDiagramQuestion = (body: DiagramQuestionCreate) =>
  apiRequest<DiagramQuestionOut>("/diagram-questions", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const updateDiagramQuestion = (
  id: string,
  body: DiagramQuestionUpdate,
) =>
  apiRequest<DiagramQuestionOut>(`/diagram-questions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

export const deleteDiagramQuestion = (id: string) =>
  apiRequest<void>(`/diagram-questions/${id}`, { method: "DELETE" });
