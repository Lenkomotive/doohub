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
  Paperclip,
  X,
  FileIcon,
  Download,
  Terminal,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { AuthGuard } from "@/components/auth-guard";
import { apiFetch, apiUpload, apiStream } from "@/lib/api";
import type { SessionMode } from "@/store/sessions";
import Markdown from "react-markdown";

interface Attachment {
  id: number;
  filename: string;
  mime_type: string;
  file_size: number;
  url: string;
}

interface ToolEvent {
  type: "tool_use" | "tool_result";
  tool: string;
  input?: Record<string, unknown>;
  output?: string;
}

interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  attachments?: Attachment[];
  toolEvents?: ToolEvent[];
}

interface SessionInfo {
  session_key: string;
  name: string;
  status: string;
  model: string;
  project_path: string;
  mode: SessionMode;
  claude_session_id: string | null;
}

const STREAMING_MODES = new Set<SessionMode>(["planning", "analysis", "freeform"]);

const MODE_LABELS: Record<SessionMode, { label: string; color: string }> = {
  oneshot: { label: "oneshot", color: "bg-blue-500/15 text-blue-500" },
  freeform: { label: "freeform", color: "bg-violet-500/15 text-violet-500" },
  planning: { label: "planning", color: "bg-amber-500/15 text-amber-500" },
  analysis: { label: "analysis", color: "bg-teal-500/15 text-teal-500" },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ToolEventCard({ event }: { event: ToolEvent }) {
  const [expanded, setExpanded] = useState(false);
  const isUse = event.type === "tool_use";

  return (
    <div className="my-1.5 rounded-lg border border-border/50 bg-background/50 text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-1.5 px-2.5 py-1.5 text-left hover:bg-accent/30 rounded-lg"
      >
        {expanded ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
        <Terminal className="h-3 w-3 shrink-0 text-muted-foreground" />
        <span className="font-mono font-medium">{event.tool}</span>
        <span className="text-muted-foreground">
          {isUse ? "called" : "result"}
        </span>
      </button>
      {expanded && (
        <div className="border-t border-border/30 px-2.5 py-2">
          <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[11px] text-muted-foreground">
            {isUse
              ? JSON.stringify(event.input, null, 2)
              : typeof event.output === "string"
                ? event.output.slice(0, 2000)
                : JSON.stringify(event.output, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function StreamingBubble({
  text,
  toolEvents,
}: {
  text: string;
  toolEvents: ToolEvent[];
}) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] rounded-2xl bg-muted px-3.5 py-2 text-sm text-foreground">
        {toolEvents.map((evt, i) => (
          <ToolEventCard key={i} event={evt} />
        ))}
        {text ? (
          <div className="prose prose-sm dark:prose-invert max-w-none chat-prose">
            <Markdown>{text}</Markdown>
          </div>
        ) : toolEvents.length === 0 ? (
          <div className="flex items-center gap-1">
            <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground" style={{ animationDelay: "0ms" }} />
            <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground" style={{ animationDelay: "200ms" }} />
            <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground" style={{ animationDelay: "400ms" }} />
          </div>
        ) : null}
        {text && (
          <span className="inline-block h-3 w-0.5 animate-pulse bg-foreground/50 align-text-bottom ml-0.5" />
        )}
      </div>
    </div>
  );
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

  // Streaming state
  const [streamingText, setStreamingText] = useState("");
  const [streamingTools, setStreamingTools] = useState<ToolEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isStreamingMode = session ? STREAMING_MODES.has(session.mode) : false;

  const fetchSession = useCallback(async () => {
    const res = await apiFetch(`/sessions/${sessionKey}`);
    if (res.ok) {
      setSession(await res.json());
    }
  }, [sessionKey]);

  const fetchHistory = useCallback(async () => {
    const res = await apiFetch(`/sessions/${sessionKey}/history`);
    if (res.ok) {
      const data = await res.json();
      setMessages(data.messages);
    }
  }, [sessionKey]);

  useEffect(() => {
    fetchSession();
    fetchHistory();
    const interval = setInterval(fetchSession, 3000);
    return () => clearInterval(interval);
  }, [fetchSession, fetchHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, streamingTools]);

  const handleStreamingSend = async (message: string) => {
    setSending(true);
    setIsStreaming(true);
    setStreamingText("");
    setStreamingTools([]);

    const controller = new AbortController();
    abortRef.current = controller;

    const formData = new FormData();
    formData.append("content", message);

    try {
      for await (const { event, data } of apiStream(
        `/sessions/${sessionKey}/messages`,
        formData,
        controller.signal,
      )) {
        if (event === "token") {
          setStreamingText((prev) => prev + (data.token as string));
        } else if (event === "tool_use") {
          setStreamingTools((prev) => [
            ...prev,
            { type: "tool_use", tool: data.tool as string, input: data.input as Record<string, unknown> },
          ]);
        } else if (event === "tool_result") {
          setStreamingTools((prev) => [
            ...prev,
            { type: "tool_result", tool: data.tool as string, output: data.output as string },
          ]);
        } else if (event === "done") {
          const finalText = (data.result as string) || "";
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + 1,
              role: "assistant",
              content: finalText,
              created_at: new Date().toISOString(),
              toolEvents: [...streamingTools],
            },
          ]);
          break;
        } else if (event === "error") {
          setMessages((prev) => [
            ...prev,
            {
              id: Date.now() + 1,
              role: "assistant",
              content: `Error: ${data.error as string}`,
              created_at: new Date().toISOString(),
            },
          ]);
          break;
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: "assistant",
            content: `Stream error: ${(err as Error).message}`,
            created_at: new Date().toISOString(),
          },
        ]);
      }
    } finally {
      setIsStreaming(false);
      setStreamingText("");
      setStreamingTools([]);
      setSending(false);
      abortRef.current = null;
      fetchSession();
      textareaRef.current?.focus();
    }
  };

  const handleOneshotSend = async (message: string, filesToSend: File[]) => {
    setSending(true);

    const formData = new FormData();
    formData.append("content", message);
    for (const file of filesToSend) {
      formData.append("files", file);
    }
    const res = await apiUpload(`/sessions/${sessionKey}/messages`, formData);

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

  const handleSend = async () => {
    if ((!input.trim() && pendingFiles.length === 0) || sending) return;

    const message = input.trim();
    setInput("");
    const filesToSend = [...pendingFiles];
    setPendingFiles([]);

    const optimisticMsg: Message = {
      id: Date.now(),
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);

    if (isStreamingMode) {
      await handleStreamingSend(message);
    } else {
      await handleOneshotSend(message, filesToSend);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCancel = async () => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
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

  const modeInfo = MODE_LABELS[session.mode] || MODE_LABELS.oneshot;

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
              <span className={`inline-flex items-center rounded-full px-1.5 py-0 text-[10px] font-medium ${modeInfo.color}`}>
                {modeInfo.label}
              </span>
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
                {session.project_path?.split("/").pop() || "general"}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {(session.status === "busy" || isStreaming) && (
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
          {messages.length === 0 && !sending && !isStreaming && (
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
                {msg.role === "user" ? (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <>
                    {msg.toolEvents?.map((evt, i) => (
                      <ToolEventCard key={i} event={evt} />
                    ))}
                    <div className="prose prose-sm dark:prose-invert max-w-none chat-prose">
                      <Markdown>{msg.content}</Markdown>
                    </div>
                  </>
                )}
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

          {/* Streaming bubble */}
          {isStreaming && (
            <StreamingBubble text={streamingText} toolEvents={streamingTools} />
          )}

          {/* Oneshot typing indicator */}
          {sending && !isStreaming && (
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
          {!isStreamingMode && (
            <Button
              variant="ghost"
              size="icon"
              className="h-9 w-9 shrink-0 text-muted-foreground"
              onClick={() => fileInputRef.current?.click()}
              disabled={sending}
            >
              <Paperclip className="h-4 w-4" />
            </Button>
          )}
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
