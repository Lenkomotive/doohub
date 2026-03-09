import { create } from "zustand";
import { apiFetch } from "@/lib/api";

export interface PipelineSchedule {
  id: number;
  name: string;
  repo_path: string;
  issue_number: number | null;
  task_description: string;
  model: string;
  template_id: number | null;
  schedule_type: "once" | "recurring";
  cron_expression: string | null;
  scheduled_at: string | null;
  timezone: string;
  is_active: boolean;
  skip_if_running: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  run_count: number;
  created_at: string;
  updated_at: string;
}

export interface ScheduleHistoryItem {
  pipeline_key: string;
  status: string;
  created_at: string;
  error: string | null;
}

interface SchedulesState {
  schedules: PipelineSchedule[];
  total: number;
  isLoading: boolean;
  fetchSchedules: () => Promise<void>;
  createSchedule: (body: {
    name: string;
    repo_path: string;
    issue_number?: number | null;
    task_description?: string | null;
    model?: string;
    template_id?: number | null;
    schedule_type: "once" | "recurring";
    cron_expression?: string | null;
    scheduled_at?: string | null;
    timezone?: string;
    skip_if_running?: boolean;
  }) => Promise<boolean>;
  updateSchedule: (id: number, body: Record<string, unknown>) => Promise<void>;
  deleteSchedule: (id: number) => Promise<void>;
  pauseSchedule: (id: number) => Promise<void>;
  resumeSchedule: (id: number) => Promise<void>;
  fetchHistory: (id: number) => Promise<ScheduleHistoryItem[]>;
}

export const useSchedulesStore = create<SchedulesState>((set, get) => ({
  schedules: [],
  total: 0,
  isLoading: false,

  fetchSchedules: async () => {
    set({ isLoading: true });
    const res = await apiFetch("/pipeline-schedules");
    if (res.ok) {
      const data = await res.json();
      set({ schedules: data.schedules, total: data.total, isLoading: false });
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
      return true;
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
      method: "PATCH",
      body: JSON.stringify(body),
    });
    if (res.ok) {
      await get().fetchSchedules();
    }
  },

  deleteSchedule: async (id) => {
    set((state) => ({
      schedules: state.schedules.filter((s) => s.id !== id),
      total: state.total - 1,
    }));
    const res = await apiFetch(`/pipeline-schedules/${id}`, { method: "DELETE" });
    if (!res.ok) {
      get().fetchSchedules();
    }
  },

  pauseSchedule: async (id) => {
    const res = await apiFetch(`/pipeline-schedules/${id}/pause`, { method: "POST" });
    if (res.ok) {
      const updated = await res.json();
      set((state) => ({
        schedules: state.schedules.map((s) => (s.id === id ? updated : s)),
      }));
    }
  },

  resumeSchedule: async (id) => {
    const res = await apiFetch(`/pipeline-schedules/${id}/resume`, { method: "POST" });
    if (res.ok) {
      const updated = await res.json();
      set((state) => ({
        schedules: state.schedules.map((s) => (s.id === id ? updated : s)),
      }));
    }
  },

  fetchHistory: async (id) => {
    const res = await apiFetch(`/pipeline-schedules/${id}/history`);
    if (res.ok) {
      const data = await res.json();
      return data.pipelines;
    }
    return [];
  },
}));
