"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Send,
  Loader2,
  Cpu,
  FolderGit2,
  Trash2,
  XCircle,
  Paperclip,
  X,
  FileIcon,
  Download,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AuthGuard } from "@/components/auth-guard";
import { apiFetch, apiUpload } from "@/lib/api";

interface Attachment {
  id: number;
  filename: string;
  mime_type: string;
  file_size: number;
  url: string;
}

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  attachments?: Attachment[];
}

interface SessionInfo {
  session_key: string;
  name: string;
  status: string;
  model: string;
  project_path: string;
  claude_session_id: string | null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ChatView() {
  const params = useParams();
  const router = useRouter();
  const sessionKey = params.id as string;

  const [session, setSession] = useState<SessionInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleSend = async () => {
    if ((!input.trim() && pendingFiles.length === 0) || sending) return;

    const message = input.trim();
    setInput("");
    setSending(true);
    const filesToSend = [...pendingFiles];
    setPendingFiles([]);

    const optimisticMsg: Message = {
      id: Date.now(),
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    let res: Response;
    if (filesToSend.length > 0) {
      const formData = new FormData();
      formData.append("content", message);
      for (const file of filesToSend) {
        formData.append("files", file);
      }
      res = await apiUpload(`/sessions/${sessionKey}/messages`, formData);
    } else {
      res = await apiFetch(`/sessions/${sessionKey}/messages`, {
        method: "POST",
        body: JSON.stringify({ content: message }),
      });
    }

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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setPendingFiles((prev) => [...prev, ...files].slice(0, 5));
    e.target.value = "";
  };

  const removePendingFile = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  if (!session) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-background">
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
              <h2 className="text-sm font-medium">{session.name || session.session_key}</h2>
              <span
                className={`inline-flex items-center rounded-full px-1.5 py-0 text-[10px] font-medium ${
                  session.status === "busy"
                    ? "bg-red-500/15 text-red-500"
                    : "bg-green-500/15 text-green-500"
                }`}
              >
                {session.status}
              </span>
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
                <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                {msg.attachments && msg.attachments.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {msg.attachments.map((att) => (
                      <a
                        key={att.id}
                        href={att.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 rounded-lg bg-background/20 px-2 py-1 text-xs hover:bg-background/30"
                      >
                        <Download className="h-3 w-3" />
                        <span className="truncate">{att.filename}</span>
                        <span className="text-[10px] opacity-70">{formatFileSize(att.file_size)}</span>
                      </a>
                    ))}
                  </div>
                )}
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

      {/* Pending files */}
      {pendingFiles.length > 0 && (
        <div className="shrink-0 border-t border-border/50 px-3 py-2">
          <div className="mx-auto flex max-w-3xl flex-wrap gap-2">
            {pendingFiles.map((file, i) => (
              <div key={i} className="flex items-center gap-1.5 rounded-lg bg-muted px-2.5 py-1 text-xs">
                <FileIcon className="h-3 w-3 text-muted-foreground" />
                <span className="max-w-32 truncate">{file.name}</span>
                <span className="text-muted-foreground">{formatFileSize(file.size)}</span>
                <button onClick={() => removePendingFile(i)} className="ml-0.5 text-muted-foreground hover:text-foreground">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="shrink-0 border-t border-border/50 px-3 py-2">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 shrink-0 text-muted-foreground"
            onClick={() => fileInputRef.current?.click()}
            disabled={sending}
          >
            <Paperclip className="h-4 w-4" />
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
            disabled={(!input.trim() && pendingFiles.length === 0) || sending}
            className="h-9 w-9 shrink-0 rounded-2xl"
          >
            <Send className="h-4 w-4" />
          </Button>
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
