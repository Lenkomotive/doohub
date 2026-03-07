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
  duplicateTemplate: (id: number) => Promise<PipelineTemplate | null>;
  deleteTemplate: (id: number) => Promise<boolean>;
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

  duplicateTemplate: async (id) => {
    const res = await apiFetch(`/pipeline-templates/${id}/duplicate`, {
      method: "POST",
    });
    if (res.ok) {
      const template = await res.json();
      set((state) => ({ templates: [template, ...state.templates] }));
      return template;
    }
    return null;
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
}));
