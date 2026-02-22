"use client";

import { Bell } from "lucide-react";
import { useNotifications } from "@/lib/hooks/use-notifications";
import { NotificationDropdown } from "@/components/notifications/notification-dropdown";

export function NotificationBell() {
  const { alerts, unreadCount, isOpen, setIsOpen, markRead, markAllRead } =
    useNotifications();

  return (
    <div className="relative">
      <button
        onClick={() => {
          if (
            typeof Notification !== "undefined" &&
            Notification.permission === "default"
          ) {
            Notification.requestPermission();
          }
          setIsOpen(!isOpen);
        }}
        className="relative rounded-md p-1.5 text-muted-foreground hover:text-foreground transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <NotificationDropdown
          alerts={alerts}
          onMarkRead={markRead}
          onMarkAllRead={markAllRead}
          onClose={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}
