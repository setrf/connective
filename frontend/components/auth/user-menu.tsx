"use client";

import { signOut, useSession } from "next-auth/react";

export function UserMenu() {
  const { data: session } = useSession();

  if (!session?.user) return null;

  return (
    <div className="flex items-center gap-3">
      {session.user.image && (
        <img
          src={session.user.image}
          alt=""
          className="h-8 w-8 rounded-full"
        />
      )}
      <span className="mono text-xs text-muted-foreground">{session.user.name}</span>
      <button
        onClick={() => signOut({ callbackUrl: "/" })}
        className="mono text-xs text-muted-foreground hover:text-foreground transition-colors uppercase tracking-wider"
      >
        Sign out
      </button>
    </div>
  );
}
