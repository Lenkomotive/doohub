"use client";

import type { Node } from "@xyflow/react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

interface ConfigPanelProps {
  node: Node;
  allNodes: Node[];
  onUpdate: (id: string, data: Record<string, unknown>) => void;
  onClose: () => void;
}

type Branch = { value: string; target: string };

function branchesToArray(branches: Record<string, string> | Branch[]): Branch[] {
  if (Array.isArray(branches)) return branches;
  return Object.entries(branches).map(([value, target]) => ({ value, target }));
}

function branchesToRecord(branches: Branch[]): Record<string, string> {
  const record: Record<string, string> = {};
  for (const b of branches) {
    if (b.value.trim()) record[b.value.trim()] = b.target;
  }
  return record;
}

export function ConfigPanel({ node, allNodes, onUpdate, onClose }: ConfigPanelProps) {
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
        {/* Name — all types except start and end */}
        {nodeType !== "start" && nodeType !== "end" && (
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

            <div className="space-y-2">
              <Label className="text-[10px] text-muted-foreground">Outputs</Label>
              {((data.outputs as string[]) || []).map((output, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <Input
                    value={output}
                    onChange={(e) => {
                      const outputs = [...((data.outputs as string[]) || [])];
                      outputs[i] = e.target.value;
                      update("outputs", outputs);
                    }}
                    className="h-7 text-xs flex-1"
                    placeholder="variable name"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
                    onClick={() => {
                      const outputs = ((data.outputs as string[]) || []).filter((_, j) => j !== i);
                      update("outputs", outputs);
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                className="h-7 w-full text-xs"
                onClick={() => {
                  const outputs = [...((data.outputs as string[]) || []), ""];
                  update("outputs", outputs);
                }}
              >
                Add output
              </Button>
            </div>

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
        {nodeType === "condition" && (() => {
          const targetNodes = allNodes.filter((n) => n.id !== node.id);
          const branches = branchesToArray(
            (data.branches as Record<string, string> | Branch[]) || [],
          );

          function updateBranches(updated: Branch[]) {
            update("branches", branchesToRecord(updated));
          }

          return (
            <>
              <Field label="Condition Field">
                <Input
                  value={(data.condition_field as string) || ""}
                  onChange={(e) => update("condition_field", e.target.value)}
                  className="h-7 text-xs"
                  placeholder="e.g. verdict"
                />
              </Field>

              <Separator />

              <div className="space-y-2">
                <Label className="text-[10px] text-muted-foreground">Branches</Label>
                {branches.map((branch, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <Input
                      value={branch.value}
                      onChange={(e) => {
                        const updated = [...branches];
                        updated[i] = { ...updated[i], value: e.target.value };
                        updateBranches(updated);
                      }}
                      className="h-7 text-xs flex-1"
                      placeholder="value"
                    />
                    <select
                      value={branch.target}
                      onChange={(e) => {
                        const updated = [...branches];
                        updated[i] = { ...updated[i], target: e.target.value };
                        updateBranches(updated);
                      }}
                      className="h-7 flex-1 rounded-md border border-input bg-background px-1.5 text-xs"
                    >
                      <option value="">→ select node</option>
                      {targetNodes.map((n) => (
                        <option key={n.id} value={n.id}>
                          {(n.data.name as string) || n.id}
                        </option>
                      ))}
                    </select>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
                      onClick={() => {
                        updateBranches(branches.filter((_, j) => j !== i));
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 w-full text-xs"
                  onClick={() => {
                    updateBranches([...branches, { value: "", target: "" }]);
                  }}
                >
                  Add branch
                </Button>
              </div>
            </>
          );
        })()}
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
