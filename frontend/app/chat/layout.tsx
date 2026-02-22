import Link from "next/link";
import { UserMenu } from "@/components/auth/user-menu";
import { NotificationBell } from "@/components/notifications/notification-bell";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen flex-col">
      <header className="border-b shrink-0">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="mono text-xs opacity-60 hover:opacity-100 transition-opacity">
              [ CONNECTIVE ]
            </Link>
            <nav className="flex gap-4 mono text-xs">
              <Link
                href="/dashboard"
                className="text-muted-foreground hover:text-foreground transition-colors uppercase tracking-wider"
              >
                Connectors
              </Link>
              <Link
                href="/chat"
                className="text-foreground uppercase tracking-wider"
              >
                Chat
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="mono text-xs text-muted-foreground hidden md:block">SYSTEM: ACTIVE</span>
            <NotificationBell />
            <UserMenu />
          </div>
        </div>
      </header>
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
