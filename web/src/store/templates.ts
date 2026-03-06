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

interface TemplatesState {
  templates: PipelineTemplate[];
  isLoading: boolean;
  fetchTemplates: () => Promise<void>;
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
