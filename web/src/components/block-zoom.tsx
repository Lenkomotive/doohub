"use client";

import { useEffect } from "react";

export function BlockZoom() {
  useEffect(() => {
    // Block pinch-to-zoom on touchmove
    const preventTouch = (e: TouchEvent) => {
      if (e.touches.length > 1) {
        e.preventDefault();
      }
    };

    // Block Safari gesture zoom (pinch/rotate)
    const preventGesture = (e: Event) => {
      e.preventDefault();
    };

    document.addEventListener("touchmove", preventTouch, { passive: false });
    document.addEventListener("gesturestart", preventGesture, { passive: false });
    document.addEventListener("gesturechange", preventGesture, { passive: false });
    document.addEventListener("gestureend", preventGesture, { passive: false });

    return () => {
      document.removeEventListener("touchmove", preventTouch);
      document.removeEventListener("gesturestart", preventGesture);
      document.removeEventListener("gesturechange", preventGesture);
      document.removeEventListener("gestureend", preventGesture);
    };
  }, []);

  return null;
}
