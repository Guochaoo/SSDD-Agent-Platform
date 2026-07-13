import { mockModels, mockScenes } from "./mockData";
import request from "@/utils/request";

export const isFrontendBMockMode = import.meta.env.VITE_USE_MOCK !== "false";

function unwrap(payload) {
  return payload?.data ?? payload;
}

export async function getScenesApi() {
  if (isFrontendBMockMode) return mockScenes;
  const response = unwrap(await request.get("/scenes"));
  return (response?.items ?? response ?? []).map((scene) => ({
    id: String(scene.id),
    name: scene.name,
    displayName: scene.display_name ?? scene.displayName ?? scene.name,
    classNames: scene.class_names ?? scene.classNames ?? [],
  }));
}

export async function getModelsApi(sceneId) {
  if (isFrontendBMockMode) return mockModels;
  // The current backend exposes the active default model on the scene detail.
  // Keep this adapter so a future /models endpoint can be added without changing
  // page components.
  const scene = unwrap(await request.get(`/scenes/${sceneId}`));
  const models = scene?.default_model ? [scene.default_model] : [];
  return models.map((model) => ({
    id: String(model.id),
    version: model.version,
    modelName: model.model_name ?? model.modelName,
    modelType: model.model_type ?? model.modelType,
    map50: model.map50,
    precision: model.precision,
    recall: model.recall,
    isDefault: model.is_default ?? model.isDefault ?? false,
    status: model.status ?? "active",
  }));
}
