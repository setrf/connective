"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function CallbackPage({
  params,
}: {
  params: { provider: string };
}) {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    // The OAuth callback is handled by the backend.
    // This page is shown briefly while redirecting.
    const error = searchParams.get("error");
    if (error) {
      // Show error and redirect
      console.error("OAuth error:", error);
    }
    router.push("/dashboard");
  }, [router, searchParams]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <p className="text-muted-foreground">Connecting {params.provider}...</p>
    </div>
  );
}
