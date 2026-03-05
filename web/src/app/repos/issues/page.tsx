"use client";

import { useEffect, useState, Suspense } from "react";
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
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const loadIssues = async (p: number) => {
    const res = await apiFetch(`/repos/issues?repo_path=${encodeURIComponent(repoPath)}&page=${p}&per_page=20`);
    if (res.ok) {
      const data = await res.json();
      const newIssues = data.issues || [];
      if (p === 1) {
        setIssues(newIssues);
      } else {
        setIssues((prev) => [...prev, ...newIssues]);
      }
      setHasMore(newIssues.length === 20);
      setPage(p);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (repoPath) loadIssues(1);
  }, [repoPath]);

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
            <Button
              variant="ghost"
              className="w-full text-muted-foreground"
              onClick={() => loadIssues(page + 1)}
            >
              Load more
            </Button>
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
