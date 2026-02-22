"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { OverlapAlert } from "@/lib/types";
import { useAuth } from "@/providers/auth-provider";

const POLL_INTERVAL = 30_000; // 30 seconds

// Module-level so the count survives component remounts (layout transitions
// between /dashboard and /chat unmount and remount NotificationBell).
// -1 = not yet initialized (skip the very first fetch to avoid spam on load).
let prevCount = -1;
// Snapshot of prevCount taken when the tab becomes hidden. Used on visibility
// restore to catch alerts that arrived while the tab was in the background
// (some browsers suppress `new Notification()` from background tabs).
let countWhenHidden = -1;

function showBrowserNotification(alert: OverlapAlert) {
  if (typeof Notification === "undefined") return;
  if (Notification.permission !== "granted") return;

  const n = new Notification("Overlap detected", {
    body: alert.summary,
    icon: "/favicon.ico",
    tag: alert.id,
  });

  n.onclick = () => {
    window.focus();
    window.location.href = "/chat";
    n.close();
  };
}

export function useNotifications() {
  const { isReady } = useAuth();
  const [alerts, setAlerts] = useState<OverlapAlert[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  // Poll unread count
  useEffect(() => {
    if (!isReady) return;

    async function fetchAndNotify(baseline: number) {
      const data = await apiClient.getUnreadCount();
      setUnreadCount(data.unread_count);

      if (baseline >= 0 && data.unread_count > baseline) {
        const notifs = await apiClient.getNotifications();
        const latest = notifs.alerts.find(
          (a: OverlapAlert) => !a.is_read
        );
        if (latest) showBrowserNotification(latest);
      }

      prevCount = data.unread_count;
    }

    async function fetchCount() {
      try {
        await fetchAndNotify(prevCount);
      } catch {
        // Silently fail
      }
    }

    // When the tab becomes visible again, compare against the count we
    // captured when the tab was hidden. This catches alerts that arrived
    // in the background on browsers that suppress `new Notification()`
    // from non-visible tabs (e.g. Safari). The `tag` on each Notification
    // deduplicates, so browsers that DID show it in the background (Chrome)
    // won't produce a double.
    function onVisibilityChange() {
      if (document.hidden) {
        countWhenHidden = prevCount;
      } else if (countWhenHidden >= 0) {
        const baseline = countWhenHidden;
        countWhenHidden = -1;
        fetchAndNotify(baseline).catch(() => {});
      }
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    fetchCount();
    pollRef.current = setInterval(fetchCount, POLL_INTERVAL);
    return () => {
      document.removeEventListener("visibilitychange", onVisibilityChange);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isReady]);

  // Fetch full notifications when dropdown opens
  useEffect(() => {
    if (!isOpen || !isReady) return;

    async function fetchAll() {
      try {
        const data = await apiClient.getNotifications();
        setAlerts(data.alerts);
        setUnreadCount(data.unread_count);
      } catch {
        // Silently fail
      }
    }

    fetchAll();
  }, [isOpen, isReady]);

  const markRead = useCallback(async (alertIds: string[]) => {
    try {
      await apiClient.markNotificationsRead(alertIds);
      setAlerts((prev) =>
        prev.map((a) =>
          alertIds.includes(a.id) ? { ...a, is_read: true } : a
        )
      );
      setUnreadCount((prev) => Math.max(0, prev - alertIds.length));
    } catch {
      // Silently fail
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await apiClient.markAllNotificationsRead();
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
      setUnreadCount(0);
    } catch {
      // Silently fail
    }
  }, []);

  return {
    alerts,
    unreadCount,
    isOpen,
    setIsOpen,
    markRead,
    markAllRead,
  };
}
