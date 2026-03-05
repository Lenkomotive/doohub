"use client";

import { useEffect, useRef, useCallback, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, CircleDot } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";
import { SkeletonList } from "@/components/skeleton-card";

interface Issue {
  number: number;
  title: string;
  labels: string[];
  state?: string;
}

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
            <Card key={issue.number} className="border-border/50 bg-card/50">
              <CardHeader className="space-y-0 pb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">#{issue.number}</span>
                  <h3 className="text-sm font-medium">{issue.title}</h3>
                </div>
              </CardHeader>
              {issue.labels && issue.labels.length > 0 && (
                <CardContent className="flex flex-wrap gap-1 pt-0">
                  {issue.labels.map((label) => (
                    <Badge key={label} variant="secondary" className="text-[10px]">
                      {label}
                    </Badge>
                  ))}
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
