"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { useSchedulesStore } from "@/store/schedules";
import type { PipelineTemplate } from "@/store/templates";

interface Repo {
  name: string;
  path: string;
}

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

type FreqType = "hourly" | "daily" | "weekly" | "once";

function buildCron(type: FreqType, hours: string, weekday: string): string | null {
  switch (type) {
    case "hourly": return `0 */${hours || "1"} * * *`;
    case "daily": return `0 ${hours || "0"} * * *`;
    case "weekly": return `0 ${hours || "9"} * * ${weekday}`;
    default: return null;
  }
}

function buildName(repoPath: string, type: FreqType, hours: string, weekday: string): string {
  const repo = repoPath.split("/").pop() || repoPath;
  switch (type) {
    case "hourly": return `${repo} — every ${hours || "1"}h`;
    case "daily": return `${repo} — daily at ${hours || "0"}:00`;
    case "weekly": return `${repo} — ${WEEKDAYS[Number(weekday) - 1] || "Monday"} at ${hours || "9"}:00`;
    case "once": return `${repo} — one-time`;
  }
}

export function CreateScheduleDialog() {
  const [open, setOpen] = useState(false);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);
  const [repoPath, setRepoPath] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [freqType, setFreqType] = useState<FreqType>("daily");
  const [hours, setHours] = useState("9");
  const [weekday, setWeekday] = useState("1");
  const [scheduledAt, setScheduledAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { createSchedule } = useSchedulesStore();

  useEffect(() => {
    if (open) {
      apiFetch("/repos").then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          setRepos(data.repos);
        }
      });
      apiFetch("/pipeline-templates").then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          setTemplates(data);
        }
      });
    } else {
      setRepoPath("");
      setTemplateId("");
      setFreqType("daily");
      setHours("9");
      setWeekday("1");
      setScheduledAt("");
      setError("");
    }
  }, [open]);

  const handleCreate = async () => {
    setError("");
    if (!repoPath) { setError("Select a repo"); return; }
    if (freqType === "once" && !scheduledAt) { setError("Pick a time"); return; }

    const isOnce = freqType === "once";
    const cron = buildCron(freqType, hours, weekday);
    const name = buildName(repoPath, freqType, hours, weekday);

    setLoading(true);
    try {
      await createSchedule({
        name,
        repo_path: repoPath,
        template_id: templateId && templateId !== "__none__" ? Number(templateId) : null,
        schedule_type: isOnce ? "once" : "recurring",
        cron_expression: cron,
        scheduled_at: isOnce ? new Date(scheduledAt).toISOString() : null,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create schedule");
    }
    setLoading(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Plus className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>New Schedule</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Repo</Label>
            <Select value={repoPath} onValueChange={setRepoPath}>
              <SelectTrigger>
                <SelectValue placeholder="Select a repo" />
              </SelectTrigger>
              <SelectContent>
                {repos.map((r) => (
                  <SelectItem key={r.path} value={r.path}>{r.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {templates.length > 0 && (
            <div className="space-y-2">
              <Label>Template</Label>
              <Select value={templateId} onValueChange={setTemplateId}>
                <SelectTrigger>
                  <SelectValue placeholder="Default" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">Default</SelectItem>
                  {templates.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>{t.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-2">
            <Label>When</Label>
            <Select value={freqType} onValueChange={(v) => setFreqType(v as FreqType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hourly">Every X hours</SelectItem>
                <SelectItem value="daily">Daily at</SelectItem>
                <SelectItem value="weekly">Weekly on</SelectItem>
                <SelectItem value="once">One-time</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {freqType === "hourly" && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Every</span>
              <Input type="number" min="1" max="23" value={hours} onChange={(e) => setHours(e.target.value)} className="w-16 text-center" />
              <span className="text-sm text-muted-foreground">hours</span>
            </div>
          )}

          {freqType === "daily" && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">At</span>
              <Input type="number" min="0" max="23" value={hours} onChange={(e) => setHours(e.target.value)} className="w-16 text-center" />
              <span className="text-sm text-muted-foreground">:00</span>
            </div>
          )}

          {freqType === "weekly" && (
            <div className="flex items-center gap-2">
              <Select value={weekday} onValueChange={setWeekday}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WEEKDAYS.map((d, i) => (
                    <SelectItem key={d} value={String(i + 1)}>{d}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground">at</span>
              <Input type="number" min="0" max="23" value={hours} onChange={(e) => setHours(e.target.value)} className="w-16 text-center" />
              <span className="text-sm text-muted-foreground">:00</span>
            </div>
          )}

          {freqType === "once" && (
            <Input type="datetime-local" value={scheduledAt} onChange={(e) => setScheduledAt(e.target.value)} />
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={handleCreate} disabled={loading} className="w-full">
            {loading ? "Creating..." : "Create"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
