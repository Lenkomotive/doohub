import { create } from "zustand";
import { apiFetch } from "@/lib/api";
import { connectSSE } from "@/lib/sse";
import type { Pipeline } from "@/store/pipelines";

export interface PipelineSchedule {
  id: number;
  name: string;
  repo_path: string;
  issue_number: number | null;
  task_description: string | null;
  model: string;
  template_id: number | null;
  schedule_type: "once" | "recurring";
  scheduled_at: string | null;
  cron_expression: string | null;
  timezone: string;
  is_active: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  last_run_status: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateScheduleBody {
  name: string;
  repo_path: string;
  issue_number?: number | null;
  task_description?: string | null;
  model?: string;
  template_id?: number | null;
  schedule_type: "once" | "recurring";
  scheduled_at?: string | null;
  cron_expression?: string | null;
  timezone: string;
}

interface SSEConnection {
  close: () => void;
}

interface SchedulesState {
  schedules: PipelineSchedule[];
  runs: Record<number, Pipeline[]>;
  isLoading: boolean;
  sseConnection: SSEConnection | null;

  fetchSchedules: () => Promise<void>;
  createSchedule: (body: CreateScheduleBody) => Promise<void>;
  updateSchedule: (id: number, body: Partial<CreateScheduleBody>) => Promise<void>;
  deleteSchedule: (id: number) => Promise<void>;
  toggleSchedule: (id: number) => Promise<void>;
  fetchScheduleRuns: (id: number) => Promise<void>;
  connectSSE: () => void;
  disconnectSSE: () => void;
}

export const useSchedulesStore = create<SchedulesState>((set, get) => ({
  schedules: [],
  runs: {},
  isLoading: false,
  sseConnection: null,

  fetchSchedules: async () => {
    set({ isLoading: true });
    const res = await apiFetch("/pipeline-schedules");
    if (res.ok) {
      const data = await res.json();
      set({ schedules: data, isLoading: false });
    } else {
      set({ isLoading: false });
    }
  },

  createSchedule: async (body) => {
    const res = await apiFetch("/pipeline-schedules", {
      method: "POST",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      await get().fetchSchedules();
      return;
    }
    let detail = `Failed to create schedule (${res.status})`;
    try {
      const err = await res.json();
      if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(detail);
  },

  updateSchedule: async (id, body) => {
    const res = await apiFetch(`/pipeline-schedules/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      const updated = await res.json();
      set((state) => ({
        schedules: state.schedules.map((s) => (s.id === id ? updated : s)),
      }));
      return;
    }
    let detail = `Failed to update schedule (${res.status})`;
    try {
      const err = await res.json();
      if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(detail);
  },

  deleteSchedule: async (id) => {
    set((state) => ({
      schedules: state.schedules.filter((s) => s.id !== id),
    }));
    const res = await apiFetch(`/pipeline-schedules/${id}`, { method: "DELETE" });
    if (!res.ok) {
      get().fetchSchedules();
    }
  },

  toggleSchedule: async (id) => {
    const schedule = get().schedules.find((s) => s.id === id);
    if (!schedule) return;
    const endpoint = schedule.is_active ? "pause" : "resume";
    // Optimistic update
    set((state) => ({
      schedules: state.schedules.map((s) =>
        s.id === id ? { ...s, is_active: !s.is_active } : s
      ),
    }));
    const res = await apiFetch(`/pipeline-schedules/${id}/${endpoint}`, { method: "POST" });
    if (!res.ok) {
      get().fetchSchedules();
    }
  },

  fetchScheduleRuns: async (id) => {
    const res = await apiFetch(`/pipeline-schedules/${id}/runs`);
    if (res.ok) {
      const data = await res.json();
      set((state) => ({
        runs: { ...state.runs, [id]: data },
      }));
    }
  },

  connectSSE: () => {
    const existing = get().sseConnection;
    if (existing) existing.close();

    const conn = connectSSE("/pipeline-schedules/events", (event, data) => {
      if (event === "snapshot") {
        set({ schedules: data as PipelineSchedule[] });
      } else if (event === "status") {
        const update = data as Partial<PipelineSchedule> & { id: number };
        set((state) => {
          const idx = state.schedules.findIndex((s) => s.id === update.id);
          if (idx >= 0) {
            const schedules = [...state.schedules];
            schedules[idx] = { ...schedules[idx], ...update };
            return { schedules };
          }
          get().fetchSchedules();
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
