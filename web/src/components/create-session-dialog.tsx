"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiFetch } from "@/lib/api";
import type { SessionMode } from "@/store/sessions";

const models = [
  { value: "opus", label: "Opus" },
  { value: "sonnet", label: "Sonnet" },
  { value: "haiku", label: "Haiku" },
];

// Fallback modes shown while roles API loads
const FALLBACK_MODES: { value: SessionMode; label: string }[] = [
  { value: "general", label: "General" },
  { value: "planning", label: "Planner" },
];

interface Repo {
  name: string;
  path: string;
}

interface RoleInfo {
  title: string;
  has_tool_restrictions: boolean;
}

export function CreateSessionDialog({
  onCreated,
}: {
  onCreated: (sessionKey: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [modes, setModes] = useState(FALLBACK_MODES);
  const [model, setModel] = useState("opus");
  const [repoPath, setRepoPath] = useState("");
  const [mode, setMode] = useState<SessionMode>("general");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      apiFetch("/repos").then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          setRepos(data.repos);
        }
      });
      apiFetch("/roles").then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          const roleEntries = Object.entries(data.roles as Record<string, RoleInfo>);
          // Put general first, then the rest
          const allModes = roleEntries
            .sort(([a], [b]) => (a === "general" ? -1 : b === "general" ? 1 : 0))
            .map(([key, info]) => ({
              value: key,
              label: info.title,
            }));
          setModes(allModes);
        }
      });
    }
  }, [open]);

  const handleCreate = async () => {
    setError("");

    setLoading(true);
    const res = await apiFetch("/sessions", {
      method: "POST",
      body: JSON.stringify({
        model,
        mode,
        ...(repoPath && repoPath !== "general" ? { project_path: repoPath } : {}),
      }),
    });

    if (res.ok) {
      const session = await res.json();
      setOpen(false);
      setModel("opus");
      setRepoPath("");
      setMode("general");
      onCreated(session.session_key);
    } else {
      const data = await res.json();
      setError(data.detail || "Failed to create session");
    }
    setLoading(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Plus className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>New Session</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {/* Mode */}
          <div className="space-y-2">
            <Label>Mode</Label>
            <div className="grid grid-cols-2 gap-2">
              {modes.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  onClick={() => setMode(m.value)}
                  className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    mode === m.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border/50 hover:bg-accent/50"
                  }`}
                >
                  <div className="font-medium">{m.label}</div>
                </button>
              ))}
            </div>
          </div>
          {/* Model */}
          <div className="space-y-2">
            <Label>Model</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {models.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {/* Repo */}
          <div className="space-y-2">
            <Label>Repo</Label>
            <Select value={repoPath} onValueChange={setRepoPath}>
              <SelectTrigger>
                <SelectValue placeholder="Select a repo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="general">General (no repo)</SelectItem>
                {repos.map((r) => (
                  <SelectItem key={r.path} value={r.path}>
                    {r.path.split("/").pop()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={handleCreate} disabled={loading} className="w-full">
            {loading ? "Creating..." : "Create"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
