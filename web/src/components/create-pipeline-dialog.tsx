"use client";

import { useEffect, useRef, useCallback, useState } from "react";
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
  { value: "opus", label: "Opus" },
  { value: "sonnet", label: "Sonnet" },
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
  const [model, setModel] = useState("opus");
  const [repoPath, setRepoPath] = useState("");
  const [selectedIssues, setSelectedIssues] = useState<number[]>([]);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

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
      setModel("opus");
      setSelectedIssues([]);
      setIssues([]);
      setError("");
    }
  }, [open]);

  const loadIssues = useCallback(async (repo: string, cursor?: string | null) => {
    if (cursor) setLoadingMore(true);
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
    setLoadingMore(false);
  }, []);

  const handleRepoChange = (path: string) => {
    setRepoPath(path);
    setSelectedIssues([]);
    setIssues([]);
    setIssuesCursor(null);
    if (path) {
      loadIssues(path);
    }
  };

  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el || loadingMore || !hasMoreIssues || !issuesCursor) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 100) {
      loadIssues(repoPath, issuesCursor);
    }
  }, [loadingMore, hasMoreIssues, issuesCursor, repoPath, loadIssues]);

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
    if (selectedIssues.length === 0) {
      setError("Select at least one issue");
      return;
    }

    setLoading(true);

    for (const issueNum of selectedIssues) {
      const issue = issues.find((i) => i.number === issueNum);
      await createPipeline({
        repo_path: repoPath,
        issue_number: issueNum,
        task_description: issue?.title || undefined,
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
          {repoPath && (
            <div className="space-y-2">
              <Label>Issues</Label>
              <div ref={listRef} onScroll={handleScroll} className="max-h-64 overflow-y-auto rounded-lg border border-border/50">
                {issues.length === 0 ? (
                  <p className="px-3 py-4 text-center text-sm text-muted-foreground">No open issues</p>
                ) : (
                  <>
                    {issues.map((issue) => {
                      const selected = selectedIssues.includes(issue.number);
                      return (
                        <button
                          key={issue.number}
                          type="button"
                          onClick={() => toggleIssue(issue.number)}
                          className={`flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors hover:bg-accent/50 border-b border-border/30 last:border-b-0 ${selected ? "bg-primary/10" : ""}`}
                        >
                          <div className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${selected ? "border-primary bg-primary text-primary-foreground" : "border-muted-foreground/30"}`}>
                            {selected && <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
                          </div>
                          <span className="text-xs text-muted-foreground/70">#{issue.number}</span>
                          <span className="truncate">{issue.title}</span>
                        </button>
                      );
                    })}
                    {hasMoreIssues && (
                      <div className="flex justify-center py-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={handleCreate} disabled={loading} className="w-full">
            {loading ? "Creating..." : selectedIssues.length > 1 ? `Create ${selectedIssues.length} pipelines` : "Create pipeline"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
