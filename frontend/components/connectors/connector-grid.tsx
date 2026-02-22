"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ConnectorCard } from "@/components/connectors/connector-card";
import { RepoSelectDialog } from "@/components/connectors/repo-select-dialog";
import { FolderSelectDialog } from "@/components/connectors/folder-select-dialog";
import { useConnectors } from "@/lib/hooks/use-connectors";
import { apiClient } from "@/lib/api-client";
import type { GoogleDriveFolder } from "@/lib/types";

export function ConnectorGrid() {
  const { connectors, loading, connect, disconnect, sync, refresh } =
    useConnectors();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [repoDialogOpen, setRepoDialogOpen] = useState(false);
  const [folderDialogOpen, setFolderDialogOpen] = useState(false);

  // Open selection dialog when redirected back after OAuth
  useEffect(() => {
    const connected = searchParams.get("connected");
    if (connected === "github") {
      setRepoDialogOpen(true);
      router.replace("/dashboard");
    } else if (connected === "google_drive") {
      setFolderDialogOpen(true);
      router.replace("/dashboard");
    }
  }, [searchParams, router]);

  const handleSync = useCallback(
    async (provider: string) => {
      if (provider === "github") {
        const ghConnector = connectors.find((c) => c.provider === "github");
        const repos = (ghConnector?.config as Record<string, unknown> | null)?.repos as string[] | undefined;
        if (!repos || repos.length === 0) {
          setRepoDialogOpen(true);
          return;
        }
      }
      if (provider === "google_drive") {
        const gdConnector = connectors.find((c) => c.provider === "google_drive");
        const folders = (gdConnector?.config as Record<string, unknown> | null)?.folders as GoogleDriveFolder[] | undefined;
        if (!folders || folders.length === 0) {
          setFolderDialogOpen(true);
          return;
        }
      }
      await sync(provider);
    },
    [connectors, sync]
  );

  const handleRepoConfirm = useCallback(
    async (repos: string[]) => {
      await apiClient.updateConnectorConfig("github", { repos });
      setRepoDialogOpen(false);
      await refresh();
      await sync("github");
    },
    [refresh, sync]
  );

  const handleFolderConfirm = useCallback(
    async (folders: GoogleDriveFolder[]) => {
      await apiClient.updateConnectorConfig("google_drive", {
        folders: folders.map((f) => ({ id: f.id, name: f.name })),
      });
      setFolderDialogOpen(false);
      await refresh();
      await sync("google_drive");
    },
    [refresh, sync]
  );

  const githubConnector = connectors.find((c) => c.provider === "github");
  const initialSelected =
    ((githubConnector?.config as Record<string, unknown> | null)?.repos as string[] | undefined) ?? [];

  const gdConnector = connectors.find((c) => c.provider === "google_drive");
  const initialFolders =
    ((gdConnector?.config as Record<string, unknown> | null)?.folders as GoogleDriveFolder[] | undefined) ?? [];

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-48 animate-pulse rounded-lg border bg-muted"
          />
        ))}
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {connectors.map((connector) => (
          <ConnectorCard
            key={connector.provider}
            connector={connector}
            onConnect={connect}
            onDisconnect={disconnect}
            onSync={handleSync}
            onStatusChange={refresh}
          />
        ))}
      </div>
      <RepoSelectDialog
        open={repoDialogOpen}
        onOpenChange={setRepoDialogOpen}
        onConfirm={handleRepoConfirm}
        initialSelected={initialSelected}
      />
      <FolderSelectDialog
        open={folderDialogOpen}
        onOpenChange={setFolderDialogOpen}
        onConfirm={handleFolderConfirm}
        initialSelected={initialFolders}
      />
    </>
  );
}
