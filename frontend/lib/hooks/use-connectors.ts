"use client";

import { useCallback, useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/providers/auth-provider";
import type { Connector } from "@/lib/types";

export function useConnectors() {
  const { isReady } = useAuth();
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = useCallback(async () => {
    try {
      const data = await apiClient.getConnectors();
      setConnectors(data);
    } catch {
      // Handle error silently
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isReady) {
      fetch();
    }
  }, [isReady, fetch]);

  const connect = useCallback(async (provider: string) => {
    const { url } = await apiClient.getOAuthUrl(provider);
    window.location.href = url;
  }, []);

  const disconnect = useCallback(
    async (provider: string) => {
      await apiClient.disconnectConnector(provider);
      await fetch();
    },
    [fetch]
  );

  const sync = useCallback(
    async (provider: string) => {
      await apiClient.triggerIngest(provider);
      await fetch();
    },
    [fetch]
  );

  return { connectors, loading, connect, disconnect, sync, refresh: fetch };
}
