"use client";

import { SourceIcon } from "@/components/evidence/source-icon";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ExternalLink } from "lucide-react";

interface EvidenceCardProps {
  citation: Citation;
  highlighted?: boolean;
}

export function EvidenceCard({ citation, highlighted }: EvidenceCardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border p-3 transition-colors",
        highlighted ? "border-primary bg-primary/5" : "hover:bg-muted/50"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-5 min-w-5 items-center justify-center rounded-sm bg-secondary px-1 text-xs font-medium">
            {citation.index}
          </span>
          <SourceIcon provider={citation.provider} />
        </div>
        {citation.url && (
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>

      {citation.title && (
        <p className="mt-2 text-sm font-medium">{citation.title}</p>
      )}
      <p className="mt-1 text-sm text-muted-foreground line-clamp-3">
        {citation.snippet}
      </p>

      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
        {citation.author_name && <span>{citation.author_name}</span>}
        {citation.source_created_at && (
          <>
            <span>&middot;</span>
            <span>
              {new Date(citation.source_created_at).toLocaleDateString(
                undefined,
                { month: "short", day: "numeric" }
              )}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
