import { create } from "zustand";
import { apiFetch } from "@/lib/api";
import { connectSSE } from "@/lib/sse";

export interface Session {
  session_key: string;
  status: "idle" | "busy";
  model: string;
  project_path: string;
  claude_session_id: string | null;
  interactive: boolean;
}

interface SSEConnection {
  close: () => void;
}

interface SessionsState {
  sessions: Session[];
  sessionsTotal: number;
  isLoading: boolean;
  sessionFilter: string | null;
  sseConnection: SSEConnection | null;
  fetchSessions: (status?: string | null) => Promise<void>;
  deleteSession: (key: string) => Promise<void>;
  setSessionFilter: (status: string | null) => void;
  connectSSE: () => void;
  disconnectSSE: () => void;
}

export const useSessionsStore = create<SessionsState>((set, get) => ({
  sessions: [],
  sessionsTotal: 0,
  isLoading: false,
  sessionFilter: null,
  sseConnection: null,

  setSessionFilter: (status) => {
    set({ sessionFilter: status });
    get().fetchSessions(status);
  },

  deleteSession: async (key) => {
    set((state) => ({
      sessions: state.sessions.filter((s) => s.session_key !== key),
      sessionsTotal: state.sessionsTotal - 1,
    }));
    const res = await apiFetch(`/sessions/${key}`, { method: "DELETE" });
    if (!res.ok) {
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

  connectSSE: () => {
    const existing = get().sseConnection;
    if (existing) existing.close();

    const conn = connectSSE("/sessions/events", (event, data) => {
      if (event === "snapshot") {
        const sessionsMap = (data as { sessions: Record<string, Session> }).sessions;
        const sessions = Object.entries(sessionsMap).map(([key, s]) => ({
          ...s,
          session_key: key,
        }));
        const filter = get().sessionFilter;
        const filtered = filter ? sessions.filter((s) => s.status === filter) : sessions;
        set({ sessions: filtered, sessionsTotal: filtered.length });
      } else if (event === "status") {
        const update = data as { session_key: string; status: string };
        set((state) => {
          const sessions = state.sessions.map((s) =>
            s.session_key === update.session_key
              ? { ...s, status: update.status as "idle" | "busy" }
              : s
          );
          return { sessions };
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
