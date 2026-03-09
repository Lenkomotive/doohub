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

const models = [
  { value: "opus", label: "Opus" },
  { value: "sonnet", label: "Sonnet" },
  { value: "haiku", label: "Haiku" },
];

const modes = [
  { value: "chat", label: "Chat" },
  { value: "planning", label: "Planning" },
  { value: "interactive", label: "Interactive" },
  { value: "workflow", label: "Workflow" },
  { value: "issue_creation", label: "Issue Creation" },
];

interface Repo {
  name: string;
  path: string;
}

export function CreateSessionDialog({
  onCreated,
}: {
  onCreated: (sessionKey: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [model, setModel] = useState("opus");
  const [mode, setMode] = useState("chat");
  const [repoPath, setRepoPath] = useState("");
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
      setMode("chat");
      setRepoPath("");
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
          <div className="space-y-2">
            <Label>Mode</Label>
            <Select value={mode} onValueChange={setMode}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {modes.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
