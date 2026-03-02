"use client";

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border/50 bg-card/50 py-6">
      <div className="px-6 pb-4">
        <div className="flex items-center justify-between">
          <div className="h-4 w-32 animate-pulse rounded bg-muted" />
          <div className="h-5 w-14 animate-pulse rounded-full bg-muted" />
        </div>
      </div>
      <div className="space-y-2 px-6">
        <div className="h-3 w-40 animate-pulse rounded bg-muted/60" />
        <div className="h-3 w-28 animate-pulse rounded bg-muted/60" />
      </div>
    </div>
  );
}

export function SkeletonList({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
