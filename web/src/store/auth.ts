import { create } from "zustand";

interface User {
  id: number;
  username: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  setUser: (user) => set({ user }),

  login: async (username, password) => {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) return false;

    const data = await res.json();
    sessionStorage.setItem("access_token", data.access_token);
    sessionStorage.setItem("refresh_token", data.refresh_token);

    const meRes = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });

    if (meRes.ok) {
      const user = await meRes.json();
      set({ user });
    }

    return true;
  },

  logout: () => {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    set({ user: null });
  },

  checkAuth: async () => {
    const token = sessionStorage.getItem("access_token");
    if (!token) {
      set({ isLoading: false });
      return;
    }

    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (res.ok) {
      const user = await res.json();
      set({ user, isLoading: false });
    } else {
      sessionStorage.removeItem("access_token");
      sessionStorage.removeItem("refresh_token");
      set({ user: null, isLoading: false });
    }
  },
}));
