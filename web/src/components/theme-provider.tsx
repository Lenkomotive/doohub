"use client";

import { useEffect } from "react";
import { useThemeStore } from "@/store/theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const loadTheme = useThemeStore((s) => s.loadTheme);

  useEffect(() => {
    loadTheme();
  }, [loadTheme]);

  return <>{children}</>;
}
