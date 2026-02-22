"use client";

import { CitationChip } from "@/components/chat/citation-chip";
import type { ChatMessage as ChatMessageType, Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick?: (citation: Citation) => void;
}

function renderContentWithCitations(
  content: string,
  citations: Citation[] | undefined,
  onCitationClick?: (citation: Citation) => void
) {
  if (!citations?.length) return content;

  // Replace [N] with clickable citation chips
  const parts = content.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      const index = parseInt(match[1], 10);
      const citation = citations.find((c) => c.index === index);
      if (citation) {
        return (
          <CitationChip
            key={i}
            index={index}
            onClick={() => onCitationClick?.(citation)}
          />
        );
      }
    }
    return <span key={i}>{part}</span>;
  });
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const label =
    confidence >= 0.7 ? "High" : confidence >= 0.4 ? "Medium" : "Low";
  const color =
    confidence >= 0.7
      ? "text-green-600"
      : confidence >= 0.4
        ? "text-yellow-600"
        : "text-red-500";
  return (
    <span className={cn("text-xs font-medium", color)}>
      {label} confidence
    </span>
  );
}

function SystemMessage({ message }: { message: ChatMessageType }) {
  const isOverlapAlert = message.metadata?.type === "overlap_alert";

  return (
    <div className="flex w-full justify-center px-4">
      <div
        className={cn(
          "max-w-[90%] rounded-lg border px-4 py-3 text-sm",
          isOverlapAlert
            ? "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/30"
            : "border-border bg-muted"
        )}
      >
        {isOverlapAlert && (
          <div className="mb-1.5 flex items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-amber-200 px-2 py-0.5 text-xs font-semibold text-amber-800 dark:bg-amber-800 dark:text-amber-200">
              Overlap detected
            </span>
            {message.created_at && (
              <span className="text-xs text-muted-foreground">
                {new Date(message.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>
        )}
        <div className="whitespace-pre-wrap leading-relaxed">
          {message.content}
        </div>
      </div>
    </div>
  );
}

export function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  if (message.role === "system") {
    return <SystemMessage message={message} />;
  }

  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-2.5 text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}
      >
        <div className="whitespace-pre-wrap leading-relaxed">
          {renderContentWithCitations(
            message.content,
            message.citations,
            onCitationClick
          )}
        </div>
        {!isUser && message.confidence != null && (
          <div className="mt-1.5 border-t border-border/50 pt-1.5">
            <ConfidenceBadge confidence={message.confidence} />
          </div>
        )}
      </div>
    </div>
  );
}
