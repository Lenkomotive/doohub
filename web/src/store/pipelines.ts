import { create } from "zustand";
import { apiFetch } from "@/lib/api";
import { connectSSE } from "@/lib/sse";

export interface Pipeline {
  pipeline_key: string;
  repo_path: string;
  issue_number: number | null;
  issue_title: string | null;
  task_description: string | null;
  status: string;
  plan: string | null;
  branch: string | null;
  pr_number: number | null;
  pr_url: string | null;
  error: string | null;
  review_round: number;
  model: string;
  total_cost_usd: number;
  created_at: string;
  updated_at: string;
}

export interface MergeStatus {
  mergeable: boolean;
  has_conflicts: boolean;
  already_merged: boolean;
  checking: boolean;
  merging: boolean;
  error: string | null;
}

interface SSEConnection {
  close: () => void;
}

interface PipelinesState {
  pipelines: Pipeline[];
  total: number;
  isLoading: boolean;
  sseConnection: SSEConnection | null;
  mergeStatuses: Record<string, MergeStatus>;
  fetchPipelines: () => Promise<void>;
  createPipeline: (body: {
    repo_path: string;
    issue_number?: number | null;
    task_description?: string | null;
    model?: string;
  }) => Promise<boolean>;
  cancelPipeline: (key: string) => Promise<void>;
  deletePipeline: (key: string) => Promise<void>;
  checkMergeStatus: (key: string) => Promise<void>;
  mergePipeline: (key: string) => Promise<void>;
  connectSSE: () => void;
  disconnectSSE: () => void;
}

const ACTIVE_STATUSES = new Set(["planning", "planned", "developing", "developed", "reviewing"]);

export function isActive(status: string): boolean {
  return ACTIVE_STATUSES.has(status);
}

export const usePipelinesStore = create<PipelinesState>((set, get) => ({
  pipelines: [],
  total: 0,
  isLoading: false,
  sseConnection: null,
  mergeStatuses: {},

  fetchPipelines: async () => {
    set({ isLoading: true });
    const res = await apiFetch("/pipelines");
    if (res.ok) {
      const data = await res.json();
      set({ pipelines: data.pipelines, total: data.total, isLoading: false });
    } else {
      set({ isLoading: false });
    }
  },

  createPipeline: async (body) => {
    const res = await apiFetch("/pipelines", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      await get().fetchPipelines();
      return true;
    }
    return false;
  },

  cancelPipeline: async (key) => {
    await apiFetch(`/pipelines/${key}/cancel`, { method: "POST" });
    await get().fetchPipelines();
  },

  deletePipeline: async (key) => {
    set((state) => ({
      pipelines: state.pipelines.filter((p) => p.pipeline_key !== key),
      total: state.total - 1,
    }));
    const res = await apiFetch(`/pipelines/${key}`, { method: "DELETE" });
    if (!res.ok) {
      get().fetchPipelines();
    }
  },

  checkMergeStatus: async (key) => {
    set((state) => ({
      mergeStatuses: {
        ...state.mergeStatuses,
        [key]: { ...(state.mergeStatuses[key] || { mergeable: false, has_conflicts: false, already_merged: false, merging: false, error: null }), checking: true },
      },
    }));
    const res = await apiFetch(`/pipelines/${key}/merge-status`);
    if (res.ok) {
      const data = await res.json();
      set((state) => ({
        mergeStatuses: {
          ...state.mergeStatuses,
          [key]: { ...data, checking: false, merging: state.mergeStatuses[key]?.merging || false },
        },
      }));
    } else {
      set((state) => ({
        mergeStatuses: {
          ...state.mergeStatuses,
          [key]: { mergeable: false, has_conflicts: false, already_merged: false, checking: false, merging: false, error: "Failed to check merge status" },
        },
      }));
    }
  },

  mergePipeline: async (key) => {
    set((state) => ({
      mergeStatuses: {
        ...state.mergeStatuses,
        [key]: { ...(state.mergeStatuses[key] || { mergeable: false, has_conflicts: false, already_merged: false, checking: false, error: null }), merging: true },
      },
    }));
    const res = await apiFetch(`/pipelines/${key}/merge`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      if (data.success) {
        set((state) => {
          const idx = state.pipelines.findIndex((p) => p.pipeline_key === key);
          if (idx >= 0) {
            const pipelines = [...state.pipelines];
            pipelines[idx] = { ...pipelines[idx], status: "merged" };
            return {
              pipelines,
              mergeStatuses: { ...state.mergeStatuses, [key]: { mergeable: false, has_conflicts: false, already_merged: true, checking: false, merging: false, error: null } },
            };
          }
          return state;
        });
      } else {
        set((state) => ({
          mergeStatuses: {
            ...state.mergeStatuses,
            [key]: { ...(state.mergeStatuses[key] || { mergeable: false, has_conflicts: false, already_merged: false, checking: false }), merging: false, error: data.error || "Merge failed" },
          },
        }));
      }
    } else {
      set((state) => ({
        mergeStatuses: {
          ...state.mergeStatuses,
          [key]: { ...(state.mergeStatuses[key] || { mergeable: false, has_conflicts: false, already_merged: false, checking: false }), merging: false, error: "Merge request failed" },
        },
      }));
    }
  },

  connectSSE: () => {
    const existing = get().sseConnection;
    if (existing) existing.close();

    const conn = connectSSE("/pipelines/events", (event, data) => {
      if (event === "pipeline") {
        const update = data as { pipeline_key: string; status: string; pr_url?: string; error?: string };
        set((state) => {
          const idx = state.pipelines.findIndex((p) => p.pipeline_key === update.pipeline_key);
          if (idx >= 0) {
            const pipelines = [...state.pipelines];
            pipelines[idx] = {
              ...pipelines[idx],
              status: update.status,
              ...(update.pr_url !== undefined && { pr_url: update.pr_url }),
              ...(update.error !== undefined && { error: update.error }),
            };
            return { pipelines };
          }
          // Unknown pipeline, refetch
          get().fetchPipelines();
          return state;
        });
      }
    });

    set({ sseConnection: conn });
  },

  disconnectSSE: () => {
    const conn = get().sseConnection;
    if (conn) {
      conn.close();
      set({ sseConnection: null });
    }
  },
}));
