"use client";

import { cn } from "@/lib/utils";

interface CitationChipProps {
  index: number;
  active?: boolean;
  onClick?: () => void;
}

export function CitationChip({ index, active, onClick }: CitationChipProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex h-5 min-w-5 items-center justify-center rounded-sm px-1 text-xs font-medium transition-colors",
        active
          ? "bg-primary text-primary-foreground"
          : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
      )}
    >
      {index}
    </button>
  );
}
