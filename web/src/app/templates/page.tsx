"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Workflow } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { TemplateCard } from "@/components/template-card";
import { SkeletonList } from "@/components/skeleton-card";
import { useTemplatesStore } from "@/store/templates";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function TemplatesContent() {
  const router = useRouter();
  const { templates, isLoading, fetchTemplates, deleteTemplate, createTemplate, duplicateTemplate } =
    useTemplatesStore();
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleDelete = async () => {
    if (deleteId === null) return;
    await deleteTemplate(deleteId);
    setDeleteId(null);
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    const template = await createTemplate({
      name: newName.trim(),
      description: newDescription.trim() || null,
      definition: {
        name: newName.trim(),
        nodes: [
          { id: "start", type: "start" },
          { id: "end", type: "end", status: "done" },
        ],
        edges: [],
      },
    });
    setCreating(false);
    if (template) {
      setShowCreate(false);
      setNewName("");
      setNewDescription("");
      router.push(`/templates/${template.id}`);
    }
  };

  const deleteTarget = templates.find((t) => t.id === deleteId);

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-medium">Templates</h2>
          <span className="text-sm text-muted-foreground">
            ({templates.length})
          </span>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="mr-1 h-3.5 w-3.5" />
          New Template
        </Button>
      </div>

      {isLoading && templates.length === 0 ? (
        <SkeletonList count={3} />
      ) : templates.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Workflow className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No templates yet</p>
        </div>
      ) : (
        <div className="grid gap-2">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onClick={() => router.push(`/templates/${template.id}`)}
              onDuplicate={() => duplicateTemplate(template.id)}
              onDelete={() => setDeleteId(template.id)}
            />
          ))}
        </div>
      )}

      <Dialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete template</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{deleteTarget?.name}
              &rdquo;? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteId(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New template</DialogTitle>
            <DialogDescription>
              Create a pipeline template with a start and end node. You can add
              more nodes in the visual builder.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1">
              <Label className="text-xs">Name</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Code Review Pipeline"
                className="h-8 text-sm"
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Description (optional)</Label>
              <Input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="What does this pipeline do?"
                className="h-8 text-sm"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={!newName.trim() || creating}>
              {creating ? "Creating…" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function TemplatesPage() {
  return (
    <AppShell>
      <TemplatesContent />
    </AppShell>
  );
}
