"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { ScanButton } from "@/components/chat/scan-button";
import { EvidencePanel } from "@/components/evidence/evidence-panel";
import { useChat } from "@/lib/hooks/use-chat";
import type { Citation } from "@/lib/types";

export default function ChatPage() {
  const { messages, isStreaming, activeCitations, sendMessage, clearChat } =
    useChat();
  const [highlightedCitation, setHighlightedCitation] = useState<number | null>(
    null
  );

  const handleCitationClick = (citation: Citation) => {
    setHighlightedCitation(citation.index);
    // Auto-clear highlight after 3 seconds
    setTimeout(() => setHighlightedCitation(null), 3000);
  };

  return (
    <div className="flex h-full">
      {/* Left panel: Chat */}
      <div className="flex flex-1 flex-col border-r">
        <ChatMessageList
          messages={messages}
          onCitationClick={handleCitationClick}
        />

        <div className="flex items-center gap-2 px-4 pb-2">
          <ScanButton />
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              disabled={isStreaming}
              className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs text-muted-foreground hover:text-destructive hover:border-destructive transition-colors disabled:opacity-50"
              title="Clear chat"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear
            </button>
          )}
        </div>

        <ChatInput onSend={sendMessage} disabled={isStreaming} />
      </div>

      {/* Right panel: Evidence */}
      <div className="hidden w-96 lg:block">
        <EvidencePanel
          citations={activeCitations}
          highlightedIndex={highlightedCitation}
        />
      </div>
    </div>
  );
}
