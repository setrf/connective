"use client";

import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { ChatMessage, Citation } from "@/lib/types";

let messageIdCounter = 0;

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);

  // Load chat history on mount
  useEffect(() => {
    let cancelled = false;
    async function loadHistory() {
      try {
        const data = await apiClient.getChatHistory();
        if (cancelled) return;
        const history: ChatMessage[] = data.messages.map(
          (m: {
            id: string;
            role: "user" | "assistant" | "system";
            content: string;
            citations?: Citation[];
            confidence?: number;
            metadata?: Record<string, unknown> | null;
            created_at?: string;
          }) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            citations: m.citations,
            confidence: m.confidence,
            metadata: m.metadata,
            created_at: m.created_at,
          })
        );
        setMessages(history);
      } catch {
        // History load failed — start fresh
      } finally {
        if (!cancelled) setIsLoadingHistory(false);
      }
    }
    loadHistory();
    return () => {
      cancelled = true;
    };
  }, []);

  const sendMessage = useCallback(
    async (query: string) => {
      const tempUserMsgId = `temp-${++messageIdCounter}`;
      const tempAsstMsgId = `temp-${++messageIdCounter}`;

      const userMessage: ChatMessage = {
        id: tempUserMsgId,
        role: "user",
        content: query,
      };

      const assistantMessage: ChatMessage = {
        id: tempAsstMsgId,
        role: "assistant",
        content: "",
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsStreaming(true);

      try {
        const API_URL =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${(apiClient as any).token}`,
          },
          body: JSON.stringify({ query }),
        });

        if (!res.ok) throw new Error("Chat failed");
        if (!res.body) throw new Error("No body");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentEvent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const data = line.startsWith("data: ") ? line.slice(6) : line.slice(5);

              if (currentEvent === "token") {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === tempAsstMsgId
                      ? { ...m, content: m.content + data }
                      : m
                  )
                );
              } else if (currentEvent === "result") {
                try {
                  const result = JSON.parse(data);
                  setMessages((prev) =>
                    prev.map((m) => {
                      if (m.id === tempUserMsgId && result.user_message_id) {
                        return { ...m, id: result.user_message_id };
                      }
                      if (m.id === tempAsstMsgId) {
                        return {
                          ...m,
                          id: result.assistant_message_id || m.id,
                          content: result.answer,
                          citations: result.citations,
                          confidence: result.confidence,
                        };
                      }
                      return m;
                    })
                  );
                  setActiveCitations(result.citations || []);
                } catch {
                  // Ignore parse errors
                }
              }
            }
          }
        }
      } catch (error) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === tempAsstMsgId
              ? {
                  ...m,
                  content:
                    "Sorry, something went wrong. Please try again.",
                }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
      }
    },
    []
  );

  return { messages, isStreaming, isLoadingHistory, activeCitations, sendMessage, setActiveCitations };
}
