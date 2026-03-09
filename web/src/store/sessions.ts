import { create } from "zustand";
import { apiFetch } from "@/lib/api";
import { connectSSE } from "@/lib/sse";

export type SessionMode = "oneshot" | "planning" | "analysis" | "freeform";

export interface Session {
  session_key: string;
  name: string;
  status: "idle" | "busy";
  model: string;
  project_path: string;
  mode: SessionMode;
  claude_session_id: string | null;
}

interface SSEConnection {
  close: () => void;
}

interface SessionsState {
  sessions: Session[];
  isLoading: boolean;
  sseConnection: SSEConnection | null;
  fetchSessions: () => Promise<void>;
  deleteSession: (key: string) => Promise<void>;
  connectSSE: () => void;
  disconnectSSE: () => void;
}

export const useSessionsStore = create<SessionsState>((set, get) => ({
  sessions: [],
  isLoading: false,
  sseConnection: null,

  deleteSession: async (key) => {
    set((state) => ({
      sessions: state.sessions.filter((s) => s.session_key !== key),
    }));
    const res = await apiFetch(`/sessions/${key}`, { method: "DELETE" });
    if (!res.ok) {
      get().fetchSessions();
    }
  },

  fetchSessions: async () => {
    set({ isLoading: true });
    const res = await apiFetch("/sessions");
    if (res.ok) {
      const data = await res.json();
      set({ sessions: data.sessions, isLoading: false });
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
        set({ sessions });
      } else if (event === "status") {
        const update = data as { session_key: string; status: string };
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.session_key === update.session_key
              ? { ...s, status: update.status as "idle" | "busy" }
              : s
          ),
        }));
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
