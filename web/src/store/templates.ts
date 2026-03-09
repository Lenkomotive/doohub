import { create } from "zustand";
import { apiFetch } from "@/lib/api";

export interface PipelineTemplate {
  id: number;
  name: string;
  description: string | null;
  definition: {
    version: number;
    name: string;
    nodes: Array<{ id: string; type: string; [key: string]: unknown }>;
    edges: Array<{ from: string; to: string }>;
  };
  created_at: string;
  updated_at: string;
}

interface CreateTemplateBody {
  name: string;
  description?: string | null;
  definition: PipelineTemplate["definition"];
}

interface UpdateTemplateBody {
  name?: string;
  description?: string | null;
  definition?: PipelineTemplate["definition"];
}

interface TemplatesState {
  templates: PipelineTemplate[];
  isLoading: boolean;
  fetchTemplates: () => Promise<void>;
  createTemplate: (body: CreateTemplateBody) => Promise<PipelineTemplate | null>;
  updateTemplate: (id: number, body: UpdateTemplateBody) => Promise<PipelineTemplate | null>;
  deleteTemplate: (id: number) => Promise<boolean>;
  duplicateTemplate: (id: number) => Promise<PipelineTemplate | null>;
}

export const useTemplatesStore = create<TemplatesState>((set, get) => ({
  templates: [],
  isLoading: false,

  fetchTemplates: async () => {
    set({ isLoading: true });
    const res = await apiFetch("/pipeline-templates");
    if (res.ok) {
      const data = await res.json();
      set({ templates: data, isLoading: false });
    } else {
      set({ isLoading: false });
    }
  },

  createTemplate: async (body) => {
    const res = await apiFetch("/pipeline-templates", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      const template = await res.json();
      set((state) => ({ templates: [template, ...state.templates] }));
      return template;
    }
    return null;
  },

  updateTemplate: async (id, body) => {
    const res = await apiFetch(`/pipeline-templates/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      const updated = await res.json();
      set((state) => ({
        templates: state.templates.map((t) => (t.id === id ? updated : t)),
      }));
      return updated;
    }
    let detail = `Save failed (${res.status})`;
    try {
      const err = await res.json();
      if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(detail);
  },

  deleteTemplate: async (id) => {
    const res = await apiFetch(`/pipeline-templates/${id}`, { method: "DELETE" });
    if (res.ok) {
      set((state) => ({
        templates: state.templates.filter((t) => t.id !== id),
      }));
      return true;
    }
    return false;
  },

  duplicateTemplate: async (id) => {
    const source = get().templates.find((t) => t.id === id);
    if (!source) return null;

    const maxNameLen = 200;
    const baseName = `Copy of ${source.name}`.slice(0, maxNameLen);

    for (let attempt = 0; attempt < 4; attempt++) {
      const name =
        attempt === 0 ? baseName : `${baseName} (${attempt + 1})`.slice(0, maxNameLen);
      const result = await get().createTemplate({
        name,
        description: source.description,
        definition: JSON.parse(JSON.stringify(source.definition)),
      });
      if (result) return result;
    }
    return null;
  },
}));
