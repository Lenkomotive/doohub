"use client";

import { useRef, useState } from "react";
import { Trash2 } from "lucide-react";

interface SwipeableProps {
  children: React.ReactNode;
  onDelete: () => void;
}

const THRESHOLD = 80;

export function Swipeable({ children, onDelete }: SwipeableProps) {
  const startX = useRef(0);
  const currentX = useRef(0);
  const [offset, setOffset] = useState(0);
  const [swiping, setSwiping] = useState(false);

  const handleTouchStart = (e: React.TouchEvent) => {
    startX.current = e.touches[0].clientX;
    currentX.current = e.touches[0].clientX;
    setSwiping(true);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!swiping) return;
    currentX.current = e.touches[0].clientX;
    const diff = startX.current - currentX.current;
    // Only allow swiping left, cap at 100px
    const clamped = Math.max(0, Math.min(diff, 100));
    setOffset(clamped);
  };

  const handleTouchEnd = () => {
    setSwiping(false);
    if (offset >= THRESHOLD) {
      // Snap open to show delete
      setOffset(80);
    } else {
      setOffset(0);
    }
  };

  const handleDelete = () => {
    setOffset(0);
    onDelete();
  };

  return (
    <div className="relative overflow-hidden rounded-xl">
      {/* Delete button behind */}
      <div
        className="absolute inset-y-0 right-0 flex w-20 items-center justify-center bg-destructive"
        onClick={handleDelete}
      >
        <Trash2 className="h-5 w-5 text-white" />
      </div>

      {/* Swipeable content */}
      <div
        className={`relative bg-background ${!swiping ? "transition-transform duration-200" : ""}`}
        style={{ transform: `translateX(-${offset}px)` }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {children}
      </div>
    </div>
  );
}
