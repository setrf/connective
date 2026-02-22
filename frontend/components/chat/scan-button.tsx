"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiClient } from "@/lib/api-client";
import type { ScanResult } from "@/lib/types";
import { Radar, X, Copy, Check } from "lucide-react";

interface ScanButtonProps {
  onResults?: (results: ScanResult) => void;
}

export function ScanButton({ onResults }: ScanButtonProps) {
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ScanResult | null>(null);
  const [copied, setCopied] = useState(false);

  const handleScan = async () => {
    if (!content.trim()) return;
    setLoading(true);
    try {
      const res = await apiClient.scan(content);
      setResults(res);
      onResults?.(res);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (results?.draft_message) {
      await navigator.clipboard.writeText(results.draft_message);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!open) {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="gap-2"
      >
        <Radar className="h-4 w-4" />
        Scan my current work
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-lg rounded-lg border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="mono text-sm uppercase tracking-wider">[ Scan for overlaps ]</h2>
          <button
            onClick={() => {
              setOpen(false);
              setResults(null);
            }}
          >
            <X className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>

        {!results ? (
          <>
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste a description of what you're working on, or a URL..."
              rows={4}
              className="mb-4"
            />
            <Button onClick={handleScan} disabled={loading || !content.trim()}>
              {loading ? "Scanning..." : "Find overlaps"}
            </Button>
          </>
        ) : (
          <div className="space-y-4 max-h-96 overflow-y-auto">
            <div>
              <h3 className="text-sm font-medium mb-1">Summary</h3>
              <p className="text-sm text-muted-foreground">{results.summary}</p>
            </div>

            {results.people.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-1">People</h3>
                <div className="space-y-1">
                  {results.people.map((p, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between text-sm"
                    >
                      <span>{p.name || p.email}</span>
                      <span className="text-muted-foreground">
                        {p.overlap_count} overlaps across{" "}
                        {p.providers.join(", ")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {results.overlaps.length > 0 && (
              <div>
                <h3 className="text-sm font-medium mb-1">Overlaps</h3>
                <div className="space-y-2">
                  {results.overlaps.slice(0, 5).map((o, i) => (
                    <div key={i} className="rounded border p-2 text-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-medium uppercase text-muted-foreground">
                          {o.provider}
                        </span>
                        {o.author_name && (
                          <span className="text-xs text-muted-foreground">
                            by {o.author_name}
                          </span>
                        )}
                      </div>
                      {o.title && (
                        <p className="font-medium">{o.title}</p>
                      )}
                      <p className="text-muted-foreground">{o.snippet}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {results.draft_message && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-medium">Draft check-in</h3>
                  <Button variant="ghost" size="sm" onClick={handleCopy}>
                    {copied ? (
                      <Check className="h-3 w-3" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                  </Button>
                </div>
                <div className="rounded border bg-muted p-3 text-sm">
                  {results.draft_message}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
