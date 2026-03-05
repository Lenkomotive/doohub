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
import { usePipelinesStore } from "@/store/pipelines";

const models = [
  { value: "sonnet", label: "Sonnet" },
  { value: "opus", label: "Opus" },
  { value: "haiku", label: "Haiku" },
];

interface Repo {
  name: string;
  path: string;
}

interface Issue {
  number: number;
  title: string;
  labels: string[];
}

export function CreatePipelineDialog() {
  const [open, setOpen] = useState(false);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [issuesCursor, setIssuesCursor] = useState<string | null>(null);
  const [hasMoreIssues, setHasMoreIssues] = useState(false);
  const [model, setModel] = useState("sonnet");
  const [repoPath, setRepoPath] = useState("");
  const [selectedIssues, setSelectedIssues] = useState<number[]>([]);
  const [taskDescription, setTaskDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { createPipeline } = usePipelinesStore();

  useEffect(() => {
    if (open) {
      apiFetch("/repos").then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          setRepos(data.repos);
        }
      });
    } else {
      setRepoPath("");
      setModel("sonnet");
      setSelectedIssues([]);
      setTaskDescription("");
      setIssues([]);
      setError("");
    }
  }, [open]);

  const loadIssues = async (repo: string, cursor?: string | null) => {
    let url = `/repos/issues?repo_path=${encodeURIComponent(repo)}&per_page=30`;
    if (cursor) url += `&cursor=${encodeURIComponent(cursor)}`;
    const res = await apiFetch(url);
    if (res.ok) {
      const data = await res.json();
      const newIssues = data.issues || [];
      if (!cursor) {
        setIssues(newIssues);
      } else {
        setIssues((prev) => [...prev, ...newIssues]);
      }
      setHasMoreIssues(data.has_more ?? false);
      setIssuesCursor(data.end_cursor ?? null);
    }
  };

  const handleRepoChange = (path: string) => {
    setRepoPath(path);
    setSelectedIssues([]);
    setIssues([]);
    setIssuesCursor(null);
    if (path) {
      loadIssues(path);
    }
  };

  const toggleIssue = (num: number) => {
    setSelectedIssues((prev) =>
      prev.includes(num) ? prev.filter((n) => n !== num) : [...prev, num]
    );
  };

  const handleCreate = async () => {
    setError("");
    if (!repoPath) {
      setError("Repo is required");
      return;
    }
    if (selectedIssues.length === 0 && !taskDescription.trim()) {
      setError("Select at least one issue or provide a task description");
      return;
    }

    setLoading(true);

    if (selectedIssues.length > 0) {
      for (const issueNum of selectedIssues) {
        const issue = issues.find((i) => i.number === issueNum);
        await createPipeline({
          repo_path: repoPath,
          issue_number: issueNum,
          task_description: issue?.title || undefined,
          model,
        });
      }
    } else {
      await createPipeline({
        repo_path: repoPath,
        task_description: taskDescription.trim(),
        model,
      });
    }

    setLoading(false);
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Plus className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New Pipeline</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Repo</Label>
            <Select value={repoPath} onValueChange={handleRepoChange}>
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
          {repoPath && issues.length > 0 && (
            <div className="space-y-2">
              <Label>Issues (optional)</Label>
              <div className="max-h-48 overflow-y-auto rounded-md border border-border/50 divide-y divide-border/30">
                {issues.map((issue) => (
                  <label
                    key={issue.number}
                    className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent/50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIssues.includes(issue.number)}
                      onChange={() => toggleIssue(issue.number)}
                      className="h-3.5 w-3.5 rounded border-border"
                    />
                    <span className="text-muted-foreground">#{issue.number}</span>
                    <span className="truncate">{issue.title}</span>
                  </label>
                ))}
                {hasMoreIssues && (
                  <button
                    className="w-full px-3 py-2 text-xs text-muted-foreground hover:bg-accent/50"
                    onClick={() => loadIssues(repoPath, issuesCursor)}
                  >
                    Load more...
                  </button>
                )}
              </div>
            </div>
          )}
          <div className="space-y-2">
            <Label>Task description {selectedIssues.length > 0 ? "(optional)" : ""}</Label>
            <textarea
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              placeholder="Describe the task..."
              rows={3}
              className="w-full resize-none rounded-md border border-border/50 bg-muted/50 px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={handleCreate} disabled={loading} className="w-full">
            {loading ? "Creating..." : "Create pipeline"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
