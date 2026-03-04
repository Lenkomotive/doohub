"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Send,
  Loader2,
  Cpu,
  FolderGit2,
  Trash2,
  XCircle,
  ImagePlus,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AuthGuard } from "@/components/auth-guard";
import { apiFetch, apiUpload } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  image_urls?: string[] | null;
  created_at: string;
}

interface PendingImage {
  file: File;
  preview: string;
  url?: string;
  uploading: boolean;
  error?: string;
}

interface SessionInfo {
  session_key: string;
  status: string;
  model: string;
  project_path: string;
  interactive: boolean;
  claude_session_id: string | null;
}

function ChatView() {
  const params = useParams();
  const router = useRouter();
  const sessionKey = params.id as string;

  const [session, setSession] = useState<SessionInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [pendingImages, setPendingImages] = useState<PendingImage[]>([]);
  const [dragging, setDragging] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);

  const fetchSession = async () => {
    const res = await apiFetch(`/sessions/${sessionKey}`);
    if (res.ok) {
      setSession(await res.json());
    }
  };

  const fetchHistory = async () => {
    const res = await apiFetch(`/sessions/${sessionKey}/history`);
    if (res.ok) {
      const data = await res.json();
      setMessages(data.messages);
    }
  };

  useEffect(() => {
    fetchSession();
    fetchHistory();
    const interval = setInterval(fetchSession, 3000);
    return () => clearInterval(interval);
  }, [sessionKey]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Cleanup object URLs on unmount
  useEffect(() => {
    const currentImages = pendingImages;
    return () => {
      currentImages.forEach((img) => URL.revokeObjectURL(img.preview));
    };
  }, [pendingImages]);

  const uploadImage = useCallback(async (file: File): Promise<void> => {
    if (file.size > 10 * 1024 * 1024) {
      setPendingImages((prev) => [
        ...prev,
        { file, preview: URL.createObjectURL(file), uploading: false, error: "File too large (max 10MB)" },
      ]);
      return;
    }

    const preview = URL.createObjectURL(file);
    const newImg: PendingImage = { file, preview, uploading: true };

    setPendingImages((prev) => [...prev, newImg]);

    const res = await apiUpload(`/sessions/${sessionKey}/upload`, file);
    if (res.ok) {
      const data = await res.json();
      setPendingImages((prev) =>
        prev.map((img) =>
          img.preview === preview ? { ...img, url: data.url, uploading: false } : img
        )
      );
    } else {
      setPendingImages((prev) =>
        prev.map((img) =>
          img.preview === preview ? { ...img, uploading: false, error: "Upload failed" } : img
        )
      );
    }
  }, [sessionKey]);

  const addFiles = useCallback((files: FileList | File[]) => {
    const imageFiles = Array.from(files).filter((f) => f.type.startsWith("image/"));
    imageFiles.forEach((f) => uploadImage(f));
  }, [uploadImage]);

  const removeImage = useCallback((preview: string) => {
    setPendingImages((prev) => {
      const img = prev.find((i) => i.preview === preview);
      if (img) URL.revokeObjectURL(img.preview);
      return prev.filter((i) => i.preview !== preview);
    });
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current++;
    if (e.dataTransfer.types.includes("Files")) {
      setDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current = 0;
    setDragging(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  }, [addFiles]);

  const handleSend = async () => {
    const hasText = input.trim().length > 0;
    const readyImages = pendingImages.filter((img) => img.url && !img.error);
    if ((!hasText && readyImages.length === 0) || sending) return;

    const message = input.trim();
    const imageUrls = readyImages.map((img) => img.url!);
    setInput("");
    // Clear pending images and revoke URLs
    pendingImages.forEach((img) => URL.revokeObjectURL(img.preview));
    setPendingImages([]);
    setSending(true);

    const optimisticMsg: Message = {
      id: Date.now(),
      role: "user",
      content: message,
      image_urls: imageUrls.length > 0 ? imageUrls : null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    const body: Record<string, unknown> = { content: message };
    if (imageUrls.length > 0) {
      body.image_urls = imageUrls;
    }

    const res = await apiFetch(`/sessions/${sessionKey}/messages`, {
      method: "POST",
      body: JSON.stringify(body),
    });

    if (res.ok) {
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          content: data.content,
          created_at: new Date().toISOString(),
        },
      ]);
    } else {
      await fetchHistory();
    }

    setSending(false);
    fetchSession();
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCancel = async () => {
    await apiFetch(`/sessions/${sessionKey}/cancel`, { method: "POST" });
    await fetchSession();
  };

  const handleDelete = async () => {
    await apiFetch(`/sessions/${sessionKey}`, { method: "DELETE" });
    router.push("/sessions");
  };

  const resolveImageUrl = (url: string) => {
    if (url.startsWith("http")) return url;
    return `${API_URL}${url}`;
  };

  if (!session) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const uploading = pendingImages.some((img) => img.uploading);
  const canSend =
    (input.trim().length > 0 || pendingImages.some((img) => img.url && !img.error)) &&
    !sending &&
    !uploading;

  return (
    <div
      className="flex h-[100dvh] flex-col bg-background relative"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {dragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/80 border-2 border-dashed border-primary rounded-lg m-2">
          <div className="text-center">
            <ImagePlus className="h-10 w-10 mx-auto text-primary mb-2" />
            <p className="text-sm font-medium text-primary">Drop images here</p>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="flex shrink-0 items-center justify-between border-b border-border/50 px-3 py-2">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => router.push("/sessions")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium">{session.session_key}</h2>
              <Badge
                variant={session.status === "busy" ? "default" : "secondary"}
                className="text-[10px] px-1.5 py-0"
              >
                {session.status}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <Cpu className="h-3 w-3" />
                {session.model}
              </span>
              <span className="flex items-center gap-1">
                <FolderGit2 className="h-3 w-3" />
                {session.project_path.split("/").pop()}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {session.status === "busy" && (
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleCancel}>
              <XCircle className="h-4 w-4" />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive" onClick={handleDelete}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3">
        <div className="mx-auto max-w-3xl space-y-3">
          {messages.length === 0 && !sending && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <p className="text-sm text-muted-foreground">
                Send a message to start
              </p>
            </div>
          )}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-foreground"
                }`}
              >
                {msg.image_urls && msg.image_urls.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-1.5">
                    {msg.image_urls.map((url, i) => (
                      <a
                        key={i}
                        href={resolveImageUrl(url)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={resolveImageUrl(url)}
                          alt=""
                          className="rounded-lg max-h-60 max-w-xs object-cover cursor-pointer hover:opacity-90 transition-opacity"
                        />
                      </a>
                    ))}
                  </div>
                )}
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="flex items-center gap-1 rounded-2xl bg-muted px-3.5 py-2.5">
                <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground" style={{ animationDelay: "0ms" }} />
                <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground" style={{ animationDelay: "200ms" }} />
                <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground" style={{ animationDelay: "400ms" }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-border/50 px-3 py-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
        <div className="mx-auto max-w-3xl">
          {/* Pending image previews */}
          {pendingImages.length > 0 && (
            <div className="flex gap-2 mb-2 overflow-x-auto pb-1">
              {pendingImages.map((img) => (
                <div key={img.preview} className="relative shrink-0 group">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.preview}
                    alt=""
                    className={`h-16 w-16 rounded-lg object-cover border border-border/50 ${
                      img.error ? "opacity-50" : ""
                    }`}
                  />
                  {img.uploading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-background/60 rounded-lg">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  )}
                  {img.error && (
                    <div className="absolute inset-0 flex items-center justify-center bg-destructive/20 rounded-lg">
                      <span className="text-[9px] text-destructive font-medium px-1 text-center">{img.error}</span>
                    </div>
                  )}
                  <button
                    onClick={() => removeImage(img.preview)}
                    className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-background border border-border flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="flex items-end gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => {
                if (e.target.files) addFiles(e.target.files);
                e.target.value = "";
              }}
            />
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 shrink-0 rounded-2xl"
              onClick={() => fileInputRef.current?.click()}
              disabled={sending}
            >
              <ImagePlus className="h-4 w-4" />
            </Button>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Send a message..."
              rows={1}
              className="flex-1 resize-none rounded-2xl border border-border/50 bg-muted/50 px-3.5 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              disabled={sending}
            />
            <Button
              size="icon"
              onClick={handleSend}
              disabled={!canSend}
              className="h-9 w-9 shrink-0 rounded-2xl"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SessionDetailPage() {
  return (
    <AuthGuard>
      <ChatView />
    </AuthGuard>
  );
}
