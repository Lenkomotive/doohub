"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FolderGit2 } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Card, CardHeader } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import { SkeletonList } from "@/components/skeleton-card";

interface Repo {
  name: string;
  path: string;
}

function ReposContent() {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    apiFetch("/repos").then(async (res) => {
      if (res.ok) {
        const data = await res.json();
        setRepos(data.repos);
      }
      setLoading(false);
    });
  }, []);

  return (
    <div className="p-6">
      <div className="mb-4">
        <h2 className="text-lg font-medium">Repos</h2>
      </div>

      {loading ? (
        <SkeletonList count={4} />
      ) : repos.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <FolderGit2 className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No repos</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {repos.map((repo) => (
            <Card
              key={repo.path}
              className="cursor-pointer border-border/50 bg-card/50 transition-colors hover:bg-accent/50"
              onClick={() => router.push(`/repos/issues?repo_path=${encodeURIComponent(repo.path)}`)}
            >
              <CardHeader className="flex flex-row items-center gap-3 space-y-0">
                <FolderGit2 className="h-4 w-4 text-muted-foreground" />
                <div>
                  <h3 className="text-sm font-medium">{repo.name}</h3>
                  <p className="text-xs text-muted-foreground">{repo.path}</p>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ReposPage() {
  return (
    <AppShell>
      <ReposContent />
    </AppShell>
  );
}
