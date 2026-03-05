"use client";

import { AuthGuard } from "@/components/auth-guard";
import { Sidebar } from "@/components/sidebar";
import { PageTransition } from "@/components/page-transition";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-[100dvh] bg-background">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <PageTransition>{children}</PageTransition>
        </main>
      </div>
    </AuthGuard>
  );
}
