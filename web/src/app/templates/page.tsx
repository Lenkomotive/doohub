"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Workflow } from "lucide-react";
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

function TemplatesContent() {
  const router = useRouter();
  const { templates, isLoading, fetchTemplates, deleteTemplate } =
    useTemplatesStore();
  const [deleteId, setDeleteId] = useState<number | null>(null);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleDelete = async () => {
    if (deleteId === null) return;
    await deleteTemplate(deleteId);
    setDeleteId(null);
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
      </div>

      {isLoading && templates.length === 0 ? (
        <SkeletonList count={3} />
      ) : templates.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Workflow className="mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No templates yet</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              onClick={() => router.push(`/templates/${template.id}`)}
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
