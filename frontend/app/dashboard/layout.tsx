import Link from "next/link";
import { UserMenu } from "@/components/auth/user-menu";
import { NotificationBell } from "@/components/notifications/notification-bell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen">
      <header className="border-b">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="mono text-xs opacity-60 hover:opacity-100 transition-opacity">
              [ CONNECTIVE ]
            </Link>
            <nav className="flex gap-4 mono text-xs">
              <Link
                href="/dashboard"
                className="text-foreground uppercase tracking-wider"
              >
                Connectors
              </Link>
              <Link
                href="/chat"
                className="text-muted-foreground hover:text-foreground transition-colors uppercase tracking-wider"
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
      <main className="mx-auto max-w-5xl p-4">{children}</main>
    </div>
  );
}
