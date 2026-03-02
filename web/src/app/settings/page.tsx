"use client";

import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/app-shell";
import { useThemeStore } from "@/store/theme";

function SettingsContent() {
  const { theme, toggleTheme } = useThemeStore();
  const isDark = theme === "dark";

  return (
    <div className="p-5 md:p-6">
      <h2 className="mb-4 text-lg font-medium">Settings</h2>

      <div className="rounded-lg border border-border/50 bg-card/30 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {isDark ? (
              <Moon className="h-5 w-5 text-muted-foreground" />
            ) : (
              <Sun className="h-5 w-5 text-muted-foreground" />
            )}
            <div>
              <p className="text-sm font-medium">Dark Mode</p>
              <p className="text-xs text-muted-foreground">
                Use dark color scheme
              </p>
            </div>
          </div>
          <Button
            variant={isDark ? "secondary" : "outline"}
            size="sm"
            onClick={toggleTheme}
          >
            {isDark ? "On" : "Off"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <AppShell>
      <SettingsContent />
    </AppShell>
  );
}
