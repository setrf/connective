"use client";

import { Suspense } from "react";
import { ConnectorGrid } from "@/components/connectors/connector-grid";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Connectors</h1>
        <p className="text-muted-foreground">
          Connect your work tools to discover overlaps and get answers.
        </p>
      </div>
      <Suspense
        fallback={
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-48 animate-pulse rounded-lg border bg-muted"
              />
            ))}
          </div>
        }
      >
        <ConnectorGrid />
      </Suspense>
    </div>
  );
}
