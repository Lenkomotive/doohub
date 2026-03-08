"use client";

import { useEffect, useState } from "react";

export function useLiveTimer(
  startedAt: string | null | undefined,
  isRunning: boolean,
): string | null {
  const [elapsed, setElapsed] = useState<string | null>(null);

  useEffect(() => {
    if (!isRunning || !startedAt) {
      setElapsed(null);
      return;
    }
    const start = new Date(startedAt).getTime();
    if (isNaN(start)) {
      setElapsed(null);
      return;
    }
    const tick = () => {
      const s = Math.floor((Date.now() - start) / 1000);
      setElapsed(
        s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`,
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt, isRunning]);

  return elapsed;
}
