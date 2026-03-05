const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SSEConnection {
  close: () => void;
}

export function connectSSE(
  path: string,
  onEvent: (event: string, data: unknown) => void,
  onError?: () => void,
): SSEConnection {
  let aborted = false;
  const controller = new AbortController();

  async function connect() {
    while (!aborted) {
      try {
        const token = sessionStorage.getItem("access_token");
        const headers: Record<string, string> = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(`${API_URL}${path}`, {
          headers,
          signal: controller.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`SSE failed: ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentEvent = "";
        let currentData = "";

        while (!aborted) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              currentData = line.slice(6).trim();
            } else if (line === "" && currentEvent && currentData) {
              try {
                const parsed = JSON.parse(currentData);
                onEvent(currentEvent, parsed);
              } catch {
                // skip malformed data
              }
              currentEvent = "";
              currentData = "";
            } else if (line.startsWith(":")) {
              // keepalive comment, ignore
            }
          }
        }
      } catch {
        if (aborted) return;
        onError?.();
      }

      if (!aborted) {
        await new Promise((r) => setTimeout(r, 5000));
      }
    }
  }

  connect();

  return {
    close: () => {
      aborted = true;
      controller.abort();
    },
  };
}
