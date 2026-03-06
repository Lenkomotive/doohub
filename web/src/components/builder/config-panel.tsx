"use client";

import type { Node } from "@xyflow/react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

interface ConfigPanelProps {
  node: Node;
  onUpdate: (id: string, data: Record<string, unknown>) => void;
  onClose: () => void;
}

export function ConfigPanel({ node, onUpdate, onClose }: ConfigPanelProps) {
  const { data } = node;
  const nodeType = node.type || data.type;

  function update(field: string, value: unknown) {
    onUpdate(node.id, { ...data, [field]: value });
  }

  return (
    <div className="flex h-full w-72 flex-col border-l border-border/50 bg-card/30">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
        <span className="text-xs font-medium">Configure: {(data.name as string) || node.id}</span>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Name — all types except start */}
        {nodeType !== "start" && (
          <Field label="Name">
            <Input
              value={(data.name as string) || ""}
              onChange={(e) => update("name", e.target.value)}
              className="h-7 text-xs"
            />
          </Field>
        )}

        {/* End node */}
        {nodeType === "end" && (
          <Field label="Status">
            <select
              value={(data.status as string) || "done"}
              onChange={(e) => update("status", e.target.value)}
              className="h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
            >
              <option value="done">done</option>
              <option value="failed">failed</option>
            </select>
          </Field>
        )}

        {/* Claude Agent node */}
        {nodeType === "claude_agent" && (
          <>
            <Field label="Prompt Template">
              <textarea
                value={(data.prompt_template as string) || ""}
                onChange={(e) => update("prompt_template", e.target.value)}
                rows={8}
                className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs font-mono resize-y"
              />
            </Field>

            <Field label="Model">
              <select
                value={(data.model as string) || ""}
                onChange={(e) => update("model", e.target.value || null)}
                className="h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
              >
                <option value="">Default (from pipeline)</option>
                <option value="claude-opus-4-6">claude-opus-4-6</option>
                <option value="claude-sonnet-4-6">claude-sonnet-4-6</option>
                <option value="claude-haiku-4-5-20251001">claude-haiku-4-5</option>
              </select>
            </Field>

            <Field label="Timeout (seconds)">
              <Input
                type="number"
                value={(data.timeout as number) || 600}
                onChange={(e) => update("timeout", Number(e.target.value))}
                className="h-7 text-xs"
              />
            </Field>

            <Field label="Max Retry Attempts">
              <Input
                type="number"
                value={((data.retry as Record<string, number>)?.max_attempts) || 1}
                onChange={(e) => update("retry", { max_attempts: Number(e.target.value) })}
                className="h-7 text-xs"
                min={1}
                max={5}
              />
            </Field>

            <Field label="Status Label">
              <Input
                value={(data.status_label as string) || ""}
                onChange={(e) => update("status_label", e.target.value)}
                className="h-7 text-xs"
                placeholder="e.g. planning, developing"
              />
            </Field>

            <Separator />

            <Field label="Outputs (comma-separated)">
              <Input
                value={((data.outputs as string[]) || []).join(", ")}
                onChange={(e) =>
                  update(
                    "outputs",
                    e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  )
                }
                className="h-7 text-xs"
                placeholder="e.g. plan, pr_url"
              />
            </Field>

            <Field label="Extract Rules (field:rule per line)">
              <textarea
                value={Object.entries((data.extract as Record<string, string>) || {})
                  .map(([k, v]) => `${k}:${v}`)
                  .join("\n")}
                onChange={(e) => {
                  const extract: Record<string, string> = {};
                  e.target.value.split("\n").forEach((line) => {
                    const idx = line.indexOf(":");
                    if (idx > 0) {
                      extract[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
                    }
                  });
                  update("extract", extract);
                }}
                rows={3}
                className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs font-mono resize-y"
                placeholder={"pr_url:regex:https://github\\.com/...\nverdict:keyword:APPROVED|CHANGES_REQUESTED"}
              />
            </Field>
          </>
        )}

        {/* Condition node */}
        {nodeType === "condition" && (
          <>
            <Field label="Condition Field">
              <Input
                value={(data.condition_field as string) || ""}
                onChange={(e) => update("condition_field", e.target.value)}
                className="h-7 text-xs"
                placeholder="e.g. verdict"
              />
            </Field>

            <Field label="Branches (value:target per line)">
              <textarea
                value={Object.entries((data.branches as Record<string, string>) || {})
                  .map(([k, v]) => `${k}:${v}`)
                  .join("\n")}
                onChange={(e) => {
                  const branches: Record<string, string> = {};
                  e.target.value.split("\n").forEach((line) => {
                    const idx = line.indexOf(":");
                    if (idx > 0) {
                      branches[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
                    }
                  });
                  update("branches", branches);
                }}
                rows={3}
                className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs font-mono resize-y"
                placeholder={"APPROVED:done\nCHANGES_REQUESTED:developer"}
              />
            </Field>

            <Field label="Default Branch">
              <Input
                value={(data.default_branch as string) || ""}
                onChange={(e) => update("default_branch", e.target.value)}
                className="h-7 text-xs"
                placeholder="e.g. fail"
              />
            </Field>

            <Field label="Max Iterations">
              <Input
                type="number"
                value={(data.max_iterations as number) || ""}
                onChange={(e) =>
                  update("max_iterations", e.target.value ? Number(e.target.value) : null)
                }
                className="h-7 text-xs"
                placeholder="unlimited"
              />
            </Field>

            <Field label="Iteration Counter">
              <Input
                value={(data.iteration_counter as string) || ""}
                onChange={(e) => update("iteration_counter", e.target.value)}
                className="h-7 text-xs"
                placeholder="e.g. review_round"
              />
            </Field>
          </>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <Label className="text-[10px] text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}
