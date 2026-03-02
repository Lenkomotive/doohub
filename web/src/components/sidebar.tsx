"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  FolderGit2,
  CircleDot,
  LogOut,
  Bot,
  Settings,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/store/auth";

const navItems = [
  { href: "/sessions", label: "Sessions", icon: MessageSquare },
  { href: "/repos", label: "Repos", icon: FolderGit2, disabled: true },
  { href: "/issues", label: "Issues", icon: CircleDot, disabled: true },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuthStore();

  return (
    <>
      {/* Desktop: side bar */}
      <aside className="hidden md:flex h-full w-14 shrink-0 flex-col items-center border-r border-border/50 bg-card/30 py-3">
        <Link
          href="/"
          className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 active:scale-90 transition-transform"
        >
          <Bot className="h-5 w-5 text-primary" />
        </Link>

        <Separator className="mb-3 w-8" />

        <nav className="flex flex-1 flex-col items-center gap-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.disabled ? "#" : item.href}
                title={item.label + (item.disabled ? " (coming soon)" : "")}
                className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all ${
                  item.disabled
                    ? "cursor-not-allowed text-muted-foreground/30"
                    : isActive
                      ? "bg-accent text-accent-foreground active:scale-90"
                      : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground active:scale-90"
                }`}
              >
                <item.icon className="h-4 w-4" />
              </Link>
            );
          })}
        </nav>

        <Separator className="mb-3 w-8" />

        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 text-muted-foreground active:scale-90"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
        </Button>
      </aside>

      {/* Mobile: bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around border-t border-border/50 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 pb-[env(safe-area-inset-bottom)]">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.disabled ? "#" : item.href}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] transition-all active:scale-90 ${
                item.disabled
                  ? "cursor-not-allowed text-muted-foreground/30"
                  : isActive
                    ? "text-primary"
                    : "text-muted-foreground"
              }`}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
        <button
          onClick={logout}
          className="flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] text-muted-foreground transition-all active:scale-90"
        >
          <LogOut className="h-5 w-5" />
          Logout
        </button>
      </nav>
    </>
  );
}
