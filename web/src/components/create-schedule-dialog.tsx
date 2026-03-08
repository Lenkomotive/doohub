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
import type { PipelineSchedule } from "@/store/schedules";
import { useTemplatesStore, type PipelineTemplate } from "@/store/templates";
import { buildCron, cronToHuman } from "@/lib/cron-helpers";

const models = [
  { value: "opus", label: "Opus" },
  { value: "sonnet", label: "Sonnet" },
  { value: "haiku", label: "Haiku" },
];

const weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

interface Repo {
  name: string;
  path: string;
}

export function CreateScheduleDialog({ schedule }: { schedule?: PipelineSchedule }) {
  const isEdit = !!schedule;
  const [open, setOpen] = useState(false);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [templates, setTemplates] = useState<PipelineTemplate[]>([]);

  const [name, setName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [issueNumber, setIssueNumber] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [templateId, setTemplateId] = useState("");
  const [model, setModel] = useState("opus");
  const [scheduleType, setScheduleType] = useState<"once" | "recurring">("recurring");
  const [scheduledAt, setScheduledAt] = useState("");
  const [preset, setPreset] = useState("daily");
  const [time, setTime] = useState("09:00");
  const [day, setDay] = useState(1);
  const [customCron, setCustomCron] = useState("");
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone
  );

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { createSchedule, updateSchedule } = useSchedulesStore();

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

      if (isEdit && schedule) {
        setName(schedule.name);
        setRepoPath(schedule.repo_path);
        setIssueNumber(schedule.issue_number?.toString() || "");
        setTaskDescription(schedule.task_description || "");
        setTemplateId(schedule.template_id?.toString() || "");
        setModel(schedule.model || "opus");
        setScheduleType(schedule.schedule_type);
        setScheduledAt(schedule.scheduled_at || "");
        setTimezone(schedule.timezone);
        if (schedule.cron_expression) {
          // Try to detect preset from cron
          const parts = schedule.cron_expression.split(" ");
          if (parts.length === 5) {
            const [min, hour, dom, , dow] = parts;
            setTime(`${hour.padStart(2, "0")}:${min.padStart(2, "0")}`);
            if (dom === "*" && dow === "*") {
              setPreset("daily");
            } else if (dom === "*" && dow !== "*") {
              setPreset("weekly");
              setDay(Number(dow));
            } else if (dom !== "*" && dow === "*") {
              setPreset("monthly");
              setDay(Number(dom));
            } else {
              setPreset("custom");
              setCustomCron(schedule.cron_expression);
            }
          } else {
            setPreset("custom");
            setCustomCron(schedule.cron_expression);
          }
        }
      }
    } else {
      setName("");
      setRepoPath("");
      setIssueNumber("");
      setTaskDescription("");
      setTemplateId("");
      setModel("opus");
      setScheduleType("recurring");
      setScheduledAt("");
      setPreset("daily");
      setTime("09:00");
      setDay(1);
      setCustomCron("");
      setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone);
      setError("");
    }
  }, [open, isEdit, schedule]);

  const cronExpression = preset === "custom" ? customCron : buildCron(preset, time, day);
  const cronPreview = cronExpression ? cronToHuman(cronExpression) : "";

  const handleSubmit = async () => {
    setError("");
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    if (!repoPath) {
      setError("Repo is required");
      return;
    }
    if (scheduleType === "once" && !scheduledAt) {
      setError("Scheduled date/time is required");
      return;
    }
    if (scheduleType === "recurring" && !cronExpression) {
      setError("Cron expression is required");
      return;
    }

    setLoading(true);
    try {
      const useTemplate = templateId && templateId !== "__none__";
      const body = {
        name: name.trim(),
        repo_path: repoPath,
        issue_number: issueNumber ? Number(issueNumber) : null,
        task_description: taskDescription.trim() || null,
        ...(useTemplate
          ? { template_id: Number(templateId) }
          : { model }),
        schedule_type: scheduleType,
        scheduled_at: scheduleType === "once" ? scheduledAt : null,
        cron_expression: scheduleType === "recurring" ? cronExpression : null,
        timezone,
      };

      if (isEdit && schedule) {
        await updateSchedule(schedule.id, body);
      } else {
        await createSchedule(body);
      }
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save schedule");
    }
    setLoading(false);
  };

  const timezones = (() => {
    try {
      return Intl.supportedValuesOf("timeZone");
    } catch {
      return [Intl.DateTimeFormat().resolvedOptions().timeZone];
    }
  })();

  const dialogContent = (
    <DialogContent className="sm:max-w-xl max-h-[85vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>{isEdit ? "Edit Schedule" : "New Schedule"}</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label>Name</Label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Nightly build"
          />
        </div>

        <div className="space-y-2">
          <Label>Repo</Label>
          <Select value={repoPath} onValueChange={setRepoPath}>
            <SelectTrigger>
              <SelectValue placeholder="Select a repo" />
            </SelectTrigger>
            <SelectContent>
              {repos.map((r) => (
                <SelectItem key={r.path} value={r.path}>
                  {r.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {repoPath && (
          <div className="space-y-2">
            <Label>Issue number (optional)</Label>
            <Input
              type="number"
              value={issueNumber}
              onChange={(e) => setIssueNumber(e.target.value)}
              placeholder="e.g. 42"
            />
          </div>
        )}

        <div className="space-y-2">
          <Label>Task description</Label>
          <textarea
            className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            value={taskDescription}
            onChange={(e) => setTaskDescription(e.target.value)}
            placeholder="Describe what the pipeline should do..."
          />
        </div>

        {templates.length > 0 && (
          <div className="space-y-2">
            <Label>Template</Label>
            <Select
              value={templateId}
              onValueChange={(v) => {
                setTemplateId(v);
                if (v && v !== "__none__") setModel("");
                else setModel("opus");
              }}
            >
              <SelectTrigger>
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
          <div className="space-y-2">
            <Label>Model</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger>
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

        <div className="space-y-2">
          <Label>Schedule type</Label>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={scheduleType === "once" ? "default" : "outline"}
              size="sm"
              onClick={() => setScheduleType("once")}
            >
              Once
            </Button>
            <Button
              type="button"
              variant={scheduleType === "recurring" ? "default" : "outline"}
              size="sm"
              onClick={() => setScheduleType("recurring")}
            >
              Recurring
            </Button>
          </div>
        </div>

        {scheduleType === "once" && (
          <div className="space-y-2">
            <Label>Run at</Label>
            <Input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
            />
          </div>
        )}

        {scheduleType === "recurring" && (
          <>
            <div className="space-y-2">
              <Label>Frequency</Label>
              <Select value={preset} onValueChange={setPreset}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="monthly">Monthly</SelectItem>
                  <SelectItem value="custom">Custom cron</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {preset === "weekly" && (
              <div className="space-y-2">
                <Label>Day of week</Label>
                <Select value={String(day)} onValueChange={(v) => setDay(Number(v))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {weekdays.map((name, i) => (
                      <SelectItem key={i} value={String(i)}>
                        {name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {preset === "monthly" && (
              <div className="space-y-2">
                <Label>Day of month</Label>
                <Select value={String(day)} onValueChange={(v) => setDay(Number(v))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Array.from({ length: 31 }, (_, i) => i + 1).map((d) => (
                      <SelectItem key={d} value={String(d)}>
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {preset !== "custom" && (
              <div className="space-y-2">
                <Label>Time</Label>
                <Input
                  type="time"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                />
              </div>
            )}

            {preset === "custom" && (
              <div className="space-y-2">
                <Label>Cron expression</Label>
                <Input
                  value={customCron}
                  onChange={(e) => setCustomCron(e.target.value)}
                  placeholder="0 9 * * *"
                />
              </div>
            )}

            {cronPreview && (
              <p className="text-sm text-muted-foreground">{cronPreview}</p>
            )}
          </>
        )}

        <div className="space-y-2">
          <Label>Timezone</Label>
          <Select value={timezone} onValueChange={setTimezone}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {timezones.map((tz) => (
                <SelectItem key={tz} value={tz}>
                  {tz}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button onClick={handleSubmit} disabled={loading} className="w-full">
          {loading ? "Saving..." : isEdit ? "Update schedule" : "Create schedule"}
        </Button>
      </div>
    </DialogContent>
  );

  if (isEdit) {
    return (
      <Dialog open={open} onOpenChange={setOpen}>
        <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
          Edit
        </Button>
        {dialogContent}
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-9 w-9">
          <Plus className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      {dialogContent}
    </Dialog>
  );
}
