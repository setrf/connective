"use client";

import { useState } from "react";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import { EvidenceTimeline } from "@/components/evidence/evidence-timeline";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

interface EvidencePanelProps {
  citations: Citation[];
  highlightedIndex?: number | null;
}

export function EvidencePanel({
  citations,
  highlightedIndex,
}: EvidencePanelProps) {
  const [tab, setTab] = useState<"citations" | "timeline">("citations");

  if (citations.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-center">
        <p className="text-sm text-muted-foreground">
          Evidence from your connected tools will appear here when you ask a
          question.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex border-b">
        <button
          onClick={() => setTab("citations")}
          className={cn(
            "flex-1 px-4 py-2 text-sm font-medium transition-colors",
            tab === "citations"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          Citations ({citations.length})
        </button>
        <button
          onClick={() => setTab("timeline")}
          className={cn(
            "flex-1 px-4 py-2 text-sm font-medium transition-colors",
            tab === "timeline"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          Timeline
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {tab === "citations" ? (
          <div className="space-y-2 p-4">
            {citations.map((citation) => (
              <EvidenceCard
                key={citation.index}
                citation={citation}
                highlighted={citation.index === highlightedIndex}
              />
            ))}
          </div>
        ) : (
          <EvidenceTimeline citations={citations} />
        )}
      </div>
    </div>
  );
}
