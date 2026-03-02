"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  { value: "sonnet", label: "Sonnet" },
  { value: "opus", label: "Opus" },
  { value: "haiku", label: "Haiku" },
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
  const [sessionKey, setSessionKey] = useState("");
  const [model, setModel] = useState("sonnet");
  const [repoPath, setRepoPath] = useState("");
  const [interactive, setInteractive] = useState(false);
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
    if (!sessionKey.trim() || !repoPath) {
      setError("Session name and repo are required");
      return;
    }

    setLoading(true);
    const res = await apiFetch("/sessions", {
      method: "POST",
      body: JSON.stringify({
        session_key: sessionKey.trim(),
        model,
        project_path: repoPath,
        interactive,
      }),
    });

    if (res.ok) {
      const session = await res.json();
      setOpen(false);
      setSessionKey("");
      setModel("sonnet");
      setRepoPath("");
      setInteractive(false);
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
            <Label>Name</Label>
            <Input
              value={sessionKey}
              onChange={(e) => setSessionKey(e.target.value)}
              placeholder="e.g. a, bugfix, feature"
            />
          </div>
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
            <Label>Repo</Label>
            <Select value={repoPath} onValueChange={setRepoPath}>
              <SelectTrigger>
                <SelectValue placeholder="Select a repo" />
              </SelectTrigger>
              <SelectContent>
                {repos.map((r) => (
                  <SelectItem key={r.path} value={r.path}>
                    {r.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="interactive"
              checked={interactive}
              onChange={(e) => setInteractive(e.target.checked)}
              className="h-4 w-4 rounded border-border"
            />
            <Label htmlFor="interactive" className="text-sm font-normal">
              Interactive mode
            </Label>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={handleCreate} disabled={loading} className="w-full">
            {loading ? "Creating..." : "Create session"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
