"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useThemeStore } from "@/store/theme";

const themes = [
  { value: "light" as const, label: "Light", icon: Sun },
  { value: "dark" as const, label: "Dark", icon: Moon },
  { value: "system" as const, label: "System", icon: Monitor },
];

function SettingsContent() {
  const { theme, setTheme } = useThemeStore();

  return (
    <div className="p-5 md:p-6">
      <h2 className="mb-4 text-lg font-medium">Settings</h2>

      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Choose how DooHub looks to you.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            {themes.map((t) => (
              <button
                key={t.value}
                onClick={() => setTheme(t.value)}
                className={`flex flex-1 flex-col items-center gap-1.5 rounded-lg border p-3 text-sm transition-colors ${
                  theme === t.value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/50"
                }`}
              >
                <t.icon className="h-5 w-5" />
                {t.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>
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
