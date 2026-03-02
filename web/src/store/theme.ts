import { create } from "zustand";

type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  toggleTheme: () => void;
  loadTheme: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: "dark",

  toggleTheme: () => {
    const next = get().theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", next);
    document.documentElement.classList.toggle("dark", next === "dark");
    set({ theme: next });
  },

  loadTheme: () => {
    const saved = localStorage.getItem("theme") as Theme | null;
    const theme = saved ?? "dark";
    document.documentElement.classList.toggle("dark", theme === "dark");
    set({ theme });
  },
}));
