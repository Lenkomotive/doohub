import { create } from "zustand";
import { apiFetch } from "@/lib/api";

export interface Session {
  session_key: string;
  status: "idle" | "busy";
  model: string;
  project_path: string;
  claude_session_id: string | null;
  interactive: boolean;
}

export interface Pipeline {
  id: number;
  pipeline_key: string;
  repo: string;
  repo_path: string;
  issue_number: number;
  issue_title: string;
  status: "planning" | "planned" | "developing" | "developed" | "reviewing" | "done" | "failed";
  pr_number: number | null;
  branch: string | null;
  review_round: number;
  plan: string | null;
  error: string | null;
  started_at: string;
  updated_at: string;
}

interface SessionsState {
  sessions: Session[];
  sessionsTotal: number;
  pipelines: Pipeline[];
  pipelinesTotal: number;
  isLoading: boolean;
  sessionFilter: string | null;
  pipelineFilter: string | null;
  fetchSessions: (status?: string | null) => Promise<void>;
  fetchPipelines: (status?: string | null) => Promise<void>;
  deleteSession: (key: string) => Promise<void>;
  setSessionFilter: (status: string | null) => void;
  setPipelineFilter: (status: string | null) => void;
}

export const useSessionsStore = create<SessionsState>((set, get) => ({
  sessions: [],
  sessionsTotal: 0,
  pipelines: [],
  pipelinesTotal: 0,
  isLoading: false,
  sessionFilter: null,
  pipelineFilter: null,

  setSessionFilter: (status) => {
    set({ sessionFilter: status });
    get().fetchSessions(status);
  },

  setPipelineFilter: (status) => {
    set({ pipelineFilter: status });
    get().fetchPipelines(status);
  },

  deleteSession: async (key) => {
    // Optimistic removal
    set((state) => ({
      sessions: state.sessions.filter((s) => s.session_key !== key),
      sessionsTotal: state.sessionsTotal - 1,
    }));
    const res = await apiFetch(`/sessions/${key}`, { method: "DELETE" });
    if (!res.ok) {
      // Refetch if delete failed
      get().fetchSessions(get().sessionFilter);
    }
  },

  fetchSessions: async (status) => {
    set({ isLoading: true });
    const params = new URLSearchParams();
    if (status) params.set("status", status);

    const res = await apiFetch(`/sessions?${params}`);
    if (res.ok) {
      const data = await res.json();
      set({ sessions: data.sessions, sessionsTotal: data.total, isLoading: false });
    } else {
      set({ isLoading: false });
    }
  },

  fetchPipelines: async (status) => {
    set({ isLoading: true });
    const params = new URLSearchParams();
    if (status) params.set("status", status);

    const res = await apiFetch(`/pipelines?${params}`);
    if (res.ok) {
      const data = await res.json();
      set({ pipelines: data.pipelines, pipelinesTotal: data.total, isLoading: false });
    } else {
      set({ isLoading: false });
    }
  },
}));
