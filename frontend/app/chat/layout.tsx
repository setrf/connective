import Link from "next/link";
import { UserMenu } from "@/components/auth/user-menu";

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen flex-col">
      <header className="border-b shrink-0">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-6">
            <Link href="/dashboard" className="text-lg font-bold">
              Connective
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link
                href="/dashboard"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                Connectors
              </Link>
              <Link
                href="/chat"
                className="text-foreground font-medium"
              >
                Chat
              </Link>
            </nav>
          </div>
          <UserMenu />
        </div>
      </header>
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
