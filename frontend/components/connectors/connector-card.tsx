"use client";

import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SourceIcon } from "@/components/connectors/source-icon";
import { apiClient } from "@/lib/api-client";
import type { Connector } from "@/lib/types";

const statusBadgeVariant: Record<string, "default" | "secondary" | "destructive" | "success" | "warning"> = {
  disconnected: "secondary",
  connected: "default",
  syncing: "warning",
  ready: "success",
  error: "destructive",
};

interface ConnectorCardProps {
  connector: Connector;
  onConnect: (provider: string) => void;
  onDisconnect: (provider: string) => void;
  onSync: (provider: string) => void;
  onStatusChange?: () => void;
}

export function ConnectorCard({
  connector,
  onConnect,
  onDisconnect,
  onSync,
  onStatusChange,
}: ConnectorCardProps) {
  const { provider, status, last_synced_at, error_message } = connector;
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll for status updates while syncing (max 2 minutes)
  useEffect(() => {
    if (status === "syncing") {
      let elapsed = 0;
      pollRef.current = setInterval(async () => {
        elapsed += 3000;
        if (elapsed > 120_000) {
          if (pollRef.current) clearInterval(pollRef.current);
          onStatusChange?.();
          return;
        }
        try {
          const data = await apiClient.getIngestStatus(provider);
          if (data.status !== "syncing") {
            onStatusChange?.();
            if (pollRef.current) clearInterval(pollRef.current);
          }
        } catch {
          // Ignore polling errors
        }
      }, 3000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [status, provider, onStatusChange]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-base">
          <SourceIcon provider={provider} />
        </CardTitle>
        <Badge variant={statusBadgeVariant[status] || "secondary"}>
          {status}
        </Badge>
      </CardHeader>
      <CardContent>
        {last_synced_at && (
          <p className="text-sm text-muted-foreground">
            Last synced:{" "}
            {new Date(last_synced_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
        {error_message && (
          <p className="text-sm text-destructive mt-1">{error_message}</p>
        )}
        {status === "syncing" && (
          <p className="text-sm text-muted-foreground animate-pulse">
            Syncing documents...
          </p>
        )}
        {status === "disconnected" && (
          <p className="text-sm text-muted-foreground">Not connected</p>
        )}
      </CardContent>
      <CardFooter className="gap-2">
        {status === "disconnected" ? (
          <Button size="sm" onClick={() => onConnect(provider)}>
            Connect
          </Button>
        ) : (
          <>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onSync(provider)}
              disabled={status === "syncing"}
            >
              {status === "syncing" ? "Syncing..." : "Sync"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onDisconnect(provider)}
            >
              Disconnect
            </Button>
          </>
        )}
      </CardFooter>
    </Card>
  );
}
