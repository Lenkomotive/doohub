"use client";

import { useRef } from "react";
import type { Node } from "@xyflow/react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

const PIPELINE_VARS = [
  "issue_number",
  "issue_title",
  "issue_body",
  "repo_path",
  "branch",
  "model",
];

interface ConfigPanelProps {
  node: Node;
  allNodes: Node[];
  onUpdate: (id: string, data: Record<string, unknown>) => void;
  onClose: () => void;
}

type OutputDef = { name: string; values: string[] };
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
  const promptRef = useRef<HTMLTextAreaElement>(null);

  function update(field: string, value: unknown) {
    onUpdate(node.id, { ...data, [field]: value });
  }

  function insertVar(varName: string) {
    const ta = promptRef.current;
    if (!ta) return;
    const tag = `{{${varName}}}`;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const current = (data.prompt_template as string) || "";
    const updated = current.slice(0, start) + tag + current.slice(end);
    update("prompt_template", updated);
    requestAnimationFrame(() => {
      ta.focus();
      ta.selectionStart = ta.selectionEnd = start + tag.length;
    });
  }

  // Collect outputs from agent nodes that appear before this node in the graph
  const agentVars = [
    ...allNodes
      .filter((n) => n.type === "claude_agent" && n.id !== node.id)
      .flatMap((n) => {
        const name = (n.data.name as string) || n.id;
        const outputs = (n.data.outputs as OutputDef[]) || [];
        return outputs.filter((o) => o.name).map((o) => ({ source: name, var: o.name }));
      }),
    ...allNodes
      .filter((n) => (n.type === "read_file" || n.type === "http_request") && n.id !== node.id && n.data.store_as)
      .map((n) => ({ source: (n.data.name as string) || n.id, var: n.data.store_as as string })),
  ];

  return (
    <div className="flex h-full w-[28rem] flex-col border-l border-border/50 bg-card/30">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
        <span className="text-xs font-medium">Configure: {(data.name as string) || node.id}</span>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 pb-6 space-y-3">
        {/* Name — all types except start and end */}
        {nodeType !== "start" && (
          <Field label="Name">
            <Input
              value={(data.name as string) || ""}
              onChange={(e) => update("name", e.target.value)}
              className="h-7 text-xs"
            />
          </Field>
        )}

        {/* Start node */}
        {nodeType === "start" && (
          <NextNodes
            targets={(data.targets as string[]) || []}
            allNodes={allNodes}
            currentNodeId={node.id}
            onUpdate={(targets) => update("targets", targets)}
          />
        )}

        {/* End node */}
        {nodeType === "end" && (
          <TemplateField
            label="Result"
            placeholder="e.g. {{plan}}"
            value={(data.result_template as string) || ""}
            onChange={(v) => update("result_template", v)}
            pipelineVars={PIPELINE_VARS}
            agentVars={agentVars}
          />
        )}

        {/* Failed node */}
        {nodeType === "failed" && (
          <>
            <TemplateField
              label="Reason"
              placeholder="e.g. {{issue_good}}"
              value={(data.reason_template as string) || ""}
              onChange={(v) => update("reason_template", v)}
              pipelineVars={PIPELINE_VARS}
              agentVars={agentVars}
            />
            <NextNodes
              targets={(data.targets as string[]) || []}
              allNodes={allNodes}
              currentNodeId={node.id}
              onUpdate={(targets) => update("targets", targets)}
            />
          </>
        )}

        {/* Claude Agent node */}
        {nodeType === "claude_agent" && (
          <>
            <div className="space-y-1.5">
              <Label className="text-[10px] text-muted-foreground">Prompt Template</Label>
              <div className="space-y-1">
                <div className="flex flex-wrap gap-1">
                  <span className="text-[9px] text-muted-foreground/70 w-full">Pipeline:</span>
                  {PIPELINE_VARS.map((v) => (
                    <Badge
                      key={v}
                      variant="outline"
                      className="text-[9px] px-1 py-0 font-mono cursor-pointer hover:bg-accent"
                      onClick={() => insertVar(v)}
                    >
                      {v}
                    </Badge>
                  ))}
                </div>
                {agentVars.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    <span className="text-[9px] text-muted-foreground/70 w-full">Agents:</span>
                    {agentVars.map((av) => (
                      <Badge
                        key={`${av.source}-${av.var}`}
                        variant="outline"
                        className="text-[9px] px-1 py-0 font-mono cursor-pointer hover:bg-accent"
                        onClick={() => insertVar(av.var)}
                        title={`from ${av.source}`}
                      >
                        {av.var}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              <textarea
                ref={promptRef}
                value={(data.prompt_template as string) || ""}
                onChange={(e) => update("prompt_template", e.target.value)}
                rows={8}
                className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs font-mono resize-y"
              />
            </div>

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

            <div className="space-y-3">
              <Label className="text-[10px] text-muted-foreground">Outputs</Label>
              {((data.outputs as OutputDef[]) || []).map((output, i) => (
                <div key={i} className="space-y-1 rounded-md border border-border/50 p-2">
                  <div className="flex items-center gap-1.5">
                    <Input
                      value={output.name}
                      onChange={(e) => {
                        const outputs = [...((data.outputs as OutputDef[]) || [])];
                        outputs[i] = { ...outputs[i], name: e.target.value };
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
                        const outputs = ((data.outputs as OutputDef[]) || []).filter((_, j) => j !== i);
                        update("outputs", outputs);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {(output.values || []).map((v, vi) => (
                      <Badge
                        key={vi}
                        variant="secondary"
                        className="text-[9px] px-1.5 py-0 font-mono cursor-pointer hover:bg-destructive/20"
                        onClick={() => {
                          const outputs = [...((data.outputs as OutputDef[]) || [])];
                          outputs[i] = { ...outputs[i], values: output.values.filter((_, j) => j !== vi) };
                          update("outputs", outputs);
                        }}
                      >
                        {v} <X className="ml-0.5 h-2 w-2" />
                      </Badge>
                    ))}
                    <Input
                      className="h-6 text-[10px] w-full"
                      placeholder="+ value (enter to add)"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          const val = e.currentTarget.value.trim();
                          if (!val) return;
                          const outputs = [...((data.outputs as OutputDef[]) || [])];
                          outputs[i] = { ...outputs[i], values: [...(output.values || []), val] };
                          update("outputs", outputs);
                          e.currentTarget.value = "";
                        }
                      }}
                    />
                  </div>
                </div>
              ))}
              <Button
                variant="outline"
                size="sm"
                className="h-7 w-full text-xs"
                onClick={() => {
                  const outputs = [...((data.outputs as OutputDef[]) || []), { name: "", values: [] }];
                  update("outputs", outputs);
                }}
              >
                Add output
              </Button>
            </div>

            <Separator />

            <NextNodes
              targets={(data.targets as string[]) || []}
              allNodes={allNodes}
              currentNodeId={node.id}
              onUpdate={(targets) => update("targets", targets)}
            />
          </>
        )}

        {/* Read File node */}
        {nodeType === "read_file" && (
          <>
            <TemplateField
              label="File Path"
              placeholder="e.g. src/config.json"
              value={(data.file_path as string) || ""}
              onChange={(v) => update("file_path", v)}
              pipelineVars={PIPELINE_VARS}
              agentVars={agentVars}
            />

            <Field label="Store Result As">
              <Input
                value={(data.store_as as string) || ""}
                onChange={(e) => update("store_as", e.target.value)}
                className="h-7 text-xs"
                placeholder="e.g. file_contents"
              />
            </Field>

            <Field label="Status Label">
              <Input
                value={(data.status_label as string) || ""}
                onChange={(e) => update("status_label", e.target.value)}
                className="h-7 text-xs"
                placeholder="e.g. reading config"
              />
            </Field>

            <Separator />

            <NextNodes
              targets={(data.targets as string[]) || []}
              allNodes={allNodes}
              currentNodeId={node.id}
              onUpdate={(targets) => update("targets", targets)}
            />
          </>
        )}

        {/* HTTP Request node */}
        {nodeType === "http_request" && (
          <>
            <Field label="Method">
              <select
                value={(data.method as string) || "GET"}
                onChange={(e) => update("method", e.target.value)}
                className="h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="PATCH">PATCH</option>
                <option value="DELETE">DELETE</option>
              </select>
            </Field>

            <TemplateField
              label="URL"
              placeholder="e.g. https://api.example.com/data"
              value={(data.url as string) || ""}
              onChange={(v) => update("url", v)}
              pipelineVars={PIPELINE_VARS}
              agentVars={agentVars}
            />

            <TemplateField
              label="Headers (JSON)"
              placeholder='e.g. {"Authorization": "Bearer {{token}}"}'
              value={(data.headers as string) || ""}
              onChange={(v) => update("headers", v)}
              pipelineVars={PIPELINE_VARS}
              agentVars={agentVars}
            />

            <TemplateField
              label="Body"
              placeholder="Request body"
              value={(data.body as string) || ""}
              onChange={(v) => update("body", v)}
              pipelineVars={PIPELINE_VARS}
              agentVars={agentVars}
            />

            <Field label="Timeout (seconds)">
              <Input
                type="number"
                value={(data.timeout as number) || 30}
                onChange={(e) => update("timeout", Number(e.target.value))}
                className="h-7 text-xs"
                min={1}
                max={120}
              />
            </Field>

            <Field label="Store Result As">
              <Input
                value={(data.store_as as string) || ""}
                onChange={(e) => update("store_as", e.target.value)}
                className="h-7 text-xs"
                placeholder="e.g. api_response"
              />
            </Field>

            <Field label="Status Label">
              <Input
                value={(data.status_label as string) || ""}
                onChange={(e) => update("status_label", e.target.value)}
                className="h-7 text-xs"
                placeholder="e.g. calling API"
              />
            </Field>

            <Separator />

            <NextNodes
              targets={(data.targets as string[]) || []}
              allNodes={allNodes}
              currentNodeId={node.id}
              onUpdate={(targets) => update("targets", targets)}
            />
          </>
        )}

        {/* Condition node */}
        {nodeType === "condition" && (() => {
          const targetNodes = allNodes.filter((n) => n.id !== node.id);
          const branches = branchesToArray(
            (data.branches as Record<string, string> | Branch[]) || [],
          );

          // Collect all available context variables (pipeline + agent outputs)
          const allOutputDefs = allNodes
            .filter((n) => n.type === "claude_agent")
            .flatMap((n) => (n.data.outputs as OutputDef[]) || [])
            .filter((o) => o.name?.trim());
          const agentOutputVars = allOutputDefs.map((o) => o.name);
          const availableVars = [...PIPELINE_VARS, ...agentOutputVars];

          // Get allowed values for the selected condition field
          const selectedField = (data.condition_field as string) || "";
          const selectedOutputDef = allOutputDefs.find((o) => o.name === selectedField);
          const allowedValues = selectedOutputDef?.values || [];

          function updateBranches(updated: Branch[]) {
            update("branches", updated);
          }

          return (
            <>
              <Field label="Status Label">
                <Input
                  value={(data.status_label as string) || ""}
                  onChange={(e) => update("status_label", e.target.value)}
                  className="h-7 text-xs"
                  placeholder="e.g. checking issue"
                />
              </Field>

              <Field label="Condition Field">
                <select
                  value={(data.condition_field as string) || ""}
                  onChange={(e) => update("condition_field", e.target.value)}
                  className="h-7 w-full rounded-md border border-input bg-background px-2 text-xs"
                >
                  <option value="">Select variable…</option>
                  {availableVars.map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </Field>

              <Separator />

              <div className="space-y-2">
                <Label className="text-[10px] text-muted-foreground">Branches</Label>
                {branches.map((branch, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    {allowedValues.length > 0 ? (
                      <select
                        value={branch.value}
                        onChange={(e) => {
                          const updated = [...branches];
                          updated[i] = { ...updated[i], value: e.target.value };
                          updateBranches(updated);
                        }}
                        className="h-7 flex-1 rounded-md border border-input bg-background px-1.5 text-xs"
                      >
                        <option value="">select value</option>
                        {allowedValues.map((v) => (
                          <option key={v} value={v}>{v}</option>
                        ))}
                      </select>
                    ) : (
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
                    )}
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

function NextNodes({
  targets,
  allNodes,
  currentNodeId,
  onUpdate,
}: {
  targets: string[];
  allNodes: Node[];
  currentNodeId: string;
  onUpdate: (targets: string[]) => void;
}) {
  const targetNodes = allNodes.filter((n) => n.id !== currentNodeId);
  return (
    <div className="space-y-2">
      <Label className="text-[10px] text-muted-foreground">Next Nodes</Label>
      {targets.map((target, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <select
            value={target}
            onChange={(e) => {
              const updated = [...targets];
              updated[i] = e.target.value;
              onUpdate(updated);
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
            onClick={() => onUpdate(targets.filter((_, j) => j !== i))}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      ))}
      <Button
        variant="outline"
        size="sm"
        className="h-7 w-full text-xs"
        onClick={() => onUpdate([...targets, ""])}
      >
        Add connection
      </Button>
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

function TemplateField({
  label,
  placeholder,
  value,
  onChange,
  pipelineVars,
  agentVars,
}: {
  label: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  pipelineVars: string[];
  agentVars: { source: string; var: string }[];
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function insert(varName: string) {
    const ta = ref.current;
    if (!ta) return;
    const tag = `{{${varName}}}`;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const updated = value.slice(0, start) + tag + value.slice(end);
    onChange(updated);
    requestAnimationFrame(() => {
      ta.focus();
      ta.selectionStart = ta.selectionEnd = start + tag.length;
    });
  }

  return (
    <div className="space-y-1.5">
      <Label className="text-[10px] text-muted-foreground">{label}</Label>
      <div className="flex flex-wrap gap-1">
        {pipelineVars.map((v) => (
          <Badge
            key={v}
            variant="outline"
            className="text-[9px] px-1 py-0 font-mono cursor-pointer hover:bg-accent"
            onClick={() => insert(v)}
          >
            {v}
          </Badge>
        ))}
        {agentVars.map((av) => (
          <Badge
            key={`${av.source}-${av.var}`}
            variant="outline"
            className="text-[9px] px-1 py-0 font-mono cursor-pointer hover:bg-accent"
            onClick={() => insert(av.var)}
            title={`from ${av.source}`}
          >
            {av.var}
          </Badge>
        ))}
      </div>
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        placeholder={placeholder}
        className="w-full rounded-md border border-input bg-background px-2 py-1.5 text-xs font-mono resize-y"
      />
    </div>
  );
}
