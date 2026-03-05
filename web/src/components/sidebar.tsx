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
  GitBranch,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useAuthStore } from "@/store/auth";

const navItems = [
  { href: "/sessions", label: "Sessions", icon: MessageSquare },
  { href: "/pipelines", label: "Pipelines", icon: GitBranch },
  { href: "/repos", label: "Repos", icon: FolderGit2 },
  { href: "/issues", label: "Issues", icon: CircleDot, disabled: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuthStore();

  return (
    <aside className="flex h-full w-14 shrink-0 flex-col items-center border-r border-border/50 bg-card/30 py-3">
      <Link
        href="/"
        className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 transition-transform hover:bg-primary/20"
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
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
              }`}
            >
              <item.icon className="h-4 w-4" />
            </Link>
          );
        })}
      </nav>

      <Separator className="mb-3 w-8" />

      <Link
        href="/settings"
        title="Settings"
        className={`mb-1 flex h-9 w-9 items-center justify-center rounded-lg transition-all ${
          pathname === "/settings"
            ? "bg-accent text-accent-foreground"
            : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
        }`}
      >
        <Settings className="h-4 w-4" />
      </Link>

      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 text-muted-foreground"
        onClick={logout}
      >
        <LogOut className="h-4 w-4" />
      </Button>
    </aside>
  );
}
