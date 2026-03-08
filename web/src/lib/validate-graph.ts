import type { Node, Edge } from "@xyflow/react";

export interface ValidationError {
  nodeId?: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  traversalOrder: string[];
}

export function validateGraph(nodes: Node[], edges: Edge[]): ValidationResult {
  const errors: ValidationError[] = [];
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  // Build adjacency from edges
  const outgoing = new Map<string, string[]>();
  for (const e of edges) {
    const list = outgoing.get(e.source) || [];
    list.push(e.target);
    outgoing.set(e.source, list);
  }

  // 1. Exactly one start node
  const startNodes = nodes.filter((n) => n.type === "start");
  if (startNodes.length === 0) {
    errors.push({ message: "No start node" });
    return { valid: false, errors, traversalOrder: [] };
  }
  if (startNodes.length > 1) {
    for (const s of startNodes.slice(1)) {
      errors.push({ nodeId: s.id, message: "Duplicate start node" });
    }
  }

  // 2. At least one terminal node
  const hasTerminal = nodes.some((n) => n.type === "end" || n.type === "failed");
  if (!hasTerminal) {
    errors.push({ message: "No end or failed node" });
  }

  // 3. BFS from start — reachability + traversal order
  const startId = startNodes[0].id;
  const visited = new Set<string>();
  const queue = [startId];
  const traversalOrder: string[] = [];

  while (queue.length > 0) {
    const id = queue.shift()!;
    if (visited.has(id)) continue;
    visited.add(id);
    traversalOrder.push(id);
    for (const next of outgoing.get(id) || []) {
      if (!visited.has(next)) queue.push(next);
    }
  }

  // Unreachable nodes
  for (const n of nodes) {
    if (!visited.has(n.id)) {
      errors.push({
        nodeId: n.id,
        message: `Unreachable: ${(n.data.name as string) || n.id}`,
      });
    }
  }

  // 4. Dead-end check — non-terminal nodes need outgoing edges
  for (const n of nodes) {
    if (n.type === "end" || n.type === "failed") continue;
    const outs = outgoing.get(n.id) || [];
    if (outs.length === 0) {
      errors.push({
        nodeId: n.id,
        message: `Dead end: ${(n.data.name as string) || n.id}`,
      });
    }
  }

  // 5. Condition node checks
  for (const n of nodes) {
    if (n.type !== "condition") continue;
    const name = (n.data.name as string) || n.id;

    if (!n.data.condition_field) {
      errors.push({ nodeId: n.id, message: `${name}: no condition field` });
    }

    const branches = n.data.branches;
    if (Array.isArray(branches)) {
      for (const b of branches as { value: string; target: string }[]) {
        if (!b.value) errors.push({ nodeId: n.id, message: `${name}: branch missing value` });
        if (!b.target) {
          errors.push({ nodeId: n.id, message: `${name}: branch missing target` });
        } else if (!nodeMap.has(b.target)) {
          errors.push({ nodeId: n.id, message: `${name}: target '${b.target}' not found` });
        }
      }
    }

    if ((n.data.max_iterations as number) > 0) {
      if (!n.data.max_iterations_target) {
        errors.push({ nodeId: n.id, message: `${name}: max iterations without target` });
      } else if (!nodeMap.has(n.data.max_iterations_target as string)) {
        errors.push({ nodeId: n.id, message: `${name}: max_iterations_target not found` });
      }
    }
  }

  // 6. Agent node checks
  for (const n of nodes) {
    if (n.type !== "claude_agent") continue;
    const name = (n.data.name as string) || n.id;
    if (!n.data.prompt_template) {
      errors.push({ nodeId: n.id, message: `${name}: no prompt` });
    }
  }

  // 7. Template node checks
  for (const n of nodes) {
    if (n.type !== "template") continue;
    const name = (n.data.name as string) || n.id;
    if (!n.data.template_id) {
      errors.push({ nodeId: n.id, message: `${name}: no template selected` });
    }
  }

  return { valid: errors.length === 0, errors, traversalOrder };
}