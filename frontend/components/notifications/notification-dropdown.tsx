"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import type { OverlapAlert } from "@/lib/types";
import { cn } from "@/lib/utils";

interface NotificationDropdownProps {
  alerts: OverlapAlert[];
  onMarkRead: (alertIds: string[]) => void;
  onMarkAllRead: () => void;
  onClose: () => void;
}

function formatTime(dateStr: string) {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function NotificationDropdown({
  alerts,
  onMarkRead,
  onMarkAllRead,
  onClose,
}: NotificationDropdownProps) {
  const router = useRouter();
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="absolute right-0 top-full z-50 mt-2 w-80 rounded-lg border bg-background shadow-lg"
    >
      <div className="flex items-center justify-between border-b px-4 py-2.5">
        <h3 className="text-sm font-semibold">Notifications</h3>
        {alerts.some((a) => !a.is_read) && (
          <button
            onClick={onMarkAllRead}
            className="text-xs text-primary hover:underline"
          >
            Mark all read
          </button>
        )}
      </div>

      <div className="max-h-80 overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No notifications yet
          </div>
        ) : (
          alerts.map((alert) => (
            <button
              key={alert.id}
              onClick={() => {
                if (!alert.is_read) {
                  onMarkRead([alert.id]);
                }
                onClose();
                router.push("/chat");
              }}
              className={cn(
                "flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50",
                !alert.is_read && "bg-primary/5"
              )}
            >
              {!alert.is_read && (
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
              )}
              <div className={cn("min-w-0 flex-1", alert.is_read && "ml-5")}>
                <p className="text-sm leading-snug">
                  {alert.summary || "Work overlap detected"}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Overlap with {alert.other_user_name || alert.other_user_email || "someone"}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {formatTime(alert.created_at)}
                </p>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
