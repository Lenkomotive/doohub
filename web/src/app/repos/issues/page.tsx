"use client";

import { useEffect, useRef, useCallback, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, CircleDot, Loader2, Play } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { apiFetch } from "@/lib/api";
import Markdown from "react-markdown";
import { usePipelinesStore } from "@/store/pipelines";
import { SkeletonList } from "@/components/skeleton-card";
import type { PipelineTemplate } from "@/store/templates";

interface Issue {
  number: number;
  title: string;
  labels: Array<{ name: string } | string>;
  state?: string;
}

const models = [
  { value: "opus", label: "Opus" },
  { value: "sonnet", label: "Sonnet" },
  { value: "haiku", label: "Haiku" },
];

function IssuesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const repoPath = searchParams.get("repo_path") || "";
  const repoName = repoPath.split("/").pop() || repoPath;

  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Run dialog state
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [issueBody, setIssueBody] = useState<string | null>(null);
  const [loadingBody, setLoadingBody] = useState(false);
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);
  const [templateId, setTemplateId] = useState<string>("");
  const [model, setModel] = useState("opus");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const { createPipeline } = usePipelinesStore();

  const loadIssues = useCallback(async (c?: string | null) => {
    if (c) setLoadingMore(true);
    let url = `/repos/issues?repo_path=${encodeURIComponent(repoPath)}&per_page=30`;
    if (c) url += `&cursor=${encodeURIComponent(c)}`;
    const res = await apiFetch(url);
    if (res.ok) {
      const data = await res.json();
      const newIssues = data.issues || [];
      if (!c) {
        setIssues(newIssues);
      } else {
        setIssues((prev) => [...prev, ...newIssues]);
      }
      setHasMore(data.has_more ?? false);
      setCursor(data.end_cursor ?? null);
    }
    setLoading(false);
    setLoadingMore(false);
  }, [repoPath]);

  useEffect(() => {
    if (repoPath) loadIssues();
  }, [repoPath, loadIssues]);

  useEffect(() => {
    if (!hasMore || !cursor || loadingMore) return;
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadIssues(cursor); },
      { threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, cursor, loadingMore, loadIssues]);

  const openRunDialog = (issue: Issue) => {
    setSelectedIssue(issue);
    setIssueBody(null);
    setLoadingBody(true);
    setTemplateId("");
    setModel("opus");
    setError("");
    apiFetch("/pipeline-templates").then(async (res) => {
      if (res.ok) setTemplates(await res.json());
    });
    apiFetch(`/repos/issue?repo_path=${encodeURIComponent(repoPath)}&issue_number=${issue.number}`).then(async (res) => {
      if (res.ok) {
        const data = await res.json();
        setIssueBody(data.body || "");
      }
      setLoadingBody(false);
    });
  };

  const handleRun = async () => {
    if (!selectedIssue) return;
    setError("");
    setRunning(true);
    try {
      const useTemplate = templateId && templateId !== "__none__";
      await createPipeline({
        repo_path: repoPath,
        issue_number: selectedIssue.number,
        task_description: selectedIssue.title,
        ...(useTemplate ? { template_id: Number(templateId) } : { model }),
      });
      setSelectedIssue(null);
      router.push("/pipelines");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create pipeline");
    }
    setRunning(false);
  };

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center gap-2">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => router.push("/repos")}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h2 className="text-lg font-medium">Issues — {repoName}</h2>
      </div>

      {loading ? (
        <SkeletonList count={4} />
      ) : issues.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <CircleDot className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No issues</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {issues.map((issue) => (
            <Card
              key={issue.number}
              className="cursor-pointer border-border/50 bg-card/50 transition-colors hover:bg-accent/50"
              onClick={() => openRunDialog(issue)}
            >
              <CardHeader className="space-y-0 pb-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">#{issue.number}</span>
                    <h3 className="text-sm font-medium">{issue.title}</h3>
                  </div>
                  <Play className="h-3.5 w-3.5 text-muted-foreground/50" />
                </div>
              </CardHeader>
              {issue.labels && issue.labels.length > 0 && (
                <CardContent className="flex flex-wrap gap-1 pt-0">
                  {issue.labels.map((label) => {
                    const name = typeof label === "string" ? label : label.name;
                    return (
                      <Badge key={name} variant="secondary" className="text-[10px]">
                        {name}
                      </Badge>
                    );
                  })}
                </CardContent>
              )}
            </Card>
          ))}
          {hasMore && (
            <div ref={sentinelRef} className="flex justify-center py-4">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
            </div>
          )}
        </div>
      )}

      {/* Run Pipeline Dialog */}
      <Dialog open={selectedIssue !== null} onOpenChange={(open) => { if (!open) setSelectedIssue(null); }}>
        <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-base">
              <span className="text-muted-foreground font-normal">#{selectedIssue?.number}</span>{" "}
              {selectedIssue?.title}
            </DialogTitle>
            {selectedIssue?.labels && selectedIssue.labels.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {selectedIssue.labels.map((label) => {
                  const name = typeof label === "string" ? label : label.name;
                  return (
                    <Badge key={name} variant="secondary" className="text-[10px]">
                      {name}
                    </Badge>
                  );
                })}
              </div>
            )}
          </DialogHeader>

          {selectedIssue && (
            <div className="flex flex-col gap-4 overflow-hidden">
              {/* Issue body */}
              <div className="min-h-0 flex-1 overflow-y-auto rounded-lg border border-border/50 bg-muted/20 px-4 py-3">
                {loadingBody ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading...
                  </div>
                ) : issueBody ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none text-foreground/90">
                    <Markdown>{issueBody}</Markdown>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground italic">No description</p>
                )}
              </div>

              {/* Run options */}
              <div className="flex items-end gap-3">
                {templates.length > 0 && (
                  <div className="flex-1 space-y-1">
                    <Label className="text-xs">Template</Label>
                    <Select
                      value={templateId}
                      onValueChange={(v) => {
                        setTemplateId(v);
                        if (v && v !== "__none__") setModel("");
                        else setModel("opus");
                      }}
                    >
                      <SelectTrigger className="h-9">
                        <SelectValue placeholder="None (use model)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">None (use model)</SelectItem>
                        {templates.map((t) => (
                          <SelectItem key={t.id} value={String(t.id)}>
                            {t.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {(!templateId || templateId === "__none__") && (
                  <div className="flex-1 space-y-1">
                    <Label className="text-xs">Model</Label>
                    <Select value={model} onValueChange={setModel}>
                      <SelectTrigger className="h-9">
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
                )}

                <Button onClick={handleRun} disabled={running} className="h-9 shrink-0">
                  <Play className="mr-1.5 h-3.5 w-3.5" />
                  {running ? "Starting..." : "Run Pipeline"}
                </Button>
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function IssuesPage() {
  return (
    <AppShell>
      <Suspense>
        <IssuesContent />
      </Suspense>
    </AppShell>
  );
}
