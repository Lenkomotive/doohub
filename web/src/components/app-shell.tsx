"use client";

import { AuthGuard } from "@/components/auth-guard";
import { Sidebar } from "@/components/sidebar";
import { PageTransition } from "@/components/page-transition";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-[100dvh] bg-background pt-[env(safe-area-inset-top)] pl-[env(safe-area-inset-left)] pr-[env(safe-area-inset-right)]">
        <Sidebar />
        <main className="flex-1 overflow-auto pb-14 md:pb-0">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
    </AuthGuard>
  );
}
