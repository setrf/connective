"use client";

import { SourceIcon } from "@/components/evidence/source-icon";
import type { Citation } from "@/lib/types";

interface EvidenceTimelineProps {
  citations: Citation[];
}

export function EvidenceTimeline({ citations }: EvidenceTimelineProps) {
  const sorted = [...citations]
    .filter((c) => c.source_created_at)
    .sort(
      (a, b) =>
        new Date(b.source_created_at!).getTime() -
        new Date(a.source_created_at!).getTime()
    );

  if (sorted.length === 0) {
    return (
      <p className="p-4 text-sm text-muted-foreground">
        No timestamped evidence available.
      </p>
    );
  }

  return (
    <div className="space-y-0 p-4">
      {sorted.map((citation, i) => (
        <div key={i} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className="flex h-6 w-6 items-center justify-center rounded-full border bg-background">
              <SourceIcon provider={citation.provider} />
            </div>
            {i < sorted.length - 1 && (
              <div className="w-px flex-1 bg-border" />
            )}
          </div>
          <div className="pb-4">
            <p className="text-xs text-muted-foreground">
              {new Date(citation.source_created_at!).toLocaleDateString(
                undefined,
                {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                }
              )}
            </p>
            {citation.title && (
              <p className="text-sm font-medium">{citation.title}</p>
            )}
            <p className="text-sm text-muted-foreground line-clamp-2">
              {citation.snippet}
            </p>
            {citation.author_name && (
              <p className="text-xs text-muted-foreground mt-1">
                {citation.author_name}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
