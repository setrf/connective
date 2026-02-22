"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "@/components/chat/chat-message";
import type { ChatMessage as ChatMessageType, Citation } from "@/lib/types";

interface ChatMessageListProps {
  messages: ChatMessageType[];
  onCitationClick?: (citation: Citation) => void;
}

export function ChatMessageList({
  messages,
  onCitationClick,
}: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-center">
        <div className="space-y-2">
          <p className="mono text-sm uppercase tracking-wider">[ Query ]</p>
          <p className="text-sm text-muted-foreground">
            Try &quot;Has someone worked on authentication?&quot; or &quot;Who
            is working on the API redesign?&quot;
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg) => (
        <ChatMessage
          key={msg.id}
          message={msg}
          onCitationClick={onCitationClick}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
